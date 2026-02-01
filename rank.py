"""Tiered Ranker"""
from typing import Any, Optional, Callable
from dataclasses import dataclass
from normalize import *


@dataclass
class UpdateResult:
    """Result of an insertion operation"""
    bucket_idx: int | None
    shifted: list[tuple[Any, int]]  # (item, new_bucket_idx) pairs


class GlobalBeliRanking:
    # bradley-terry rank aggregation over multiple individual beli rankings
    pass


class IndividualBeliRanking:
    """Beli Ranking Algorithm"""
    def __init__(self, tiers: int, scale: int, normalize_fn: Callable, tier_thresholds: list[int] = None) -> None:
        """
        :param tiers:
        :param scale:
        :param normalize_fn: normalization function to be used
        :param tier_thresholds: the upper thresholds for each tier
        """
        self.tiers: int = tiers
        self.scale: int = scale
        self.normalize_fn = normalize_fn
        self.tier_thresholds: list[int] = tier_thresholds or [i * (scale/tiers) for i in range(1, tiers+1)]
        self.history: str = ""
        self.items: dict[int, BucketedRanking] = {i: BucketedRanking() for i in range(tiers)}
        self.registry: dict[Any, list[int]] = {} # [tier id, bucket idx]
        self.scores: dict[Any, float] = {}

    def __len__(self):
        """Get total number of items in the ranking"""
        return len(self.registry)

    def normalize(self, scale: int):
        """Cardinal scoring"""
        # linearize tiers, cdf to handle buckets
        self.normalize_fn(scale)
        # update self.scores
        pass

    def insert(self, new_item: Any, tier: int):
        """Insert new item into appropriate tiered binrank"""
        # update registry tier
        result = self.items[tier].binary_insert(new_item)
        self.registry[new_item] = [tier, result.bucket_idx]

        for item, idx in result.shifted:
            self.registry[item][1] = idx

        self.normalize(self.scale)

    def remove(self, del_item: Any):
        """Remove item from appropriate tiered binrank"""
        tier, bucket = self.registry[del_item]
        result = self.items[tier].remove(del_item, bucket)

        if result:
            del self.registry[del_item]
            for item, idx in result.shifted:
                self.registry[item][1] = idx

        self.normalize(self.scale)

    def rerank(self, item: Any, new_position: int):
        new_tier, new_tier_position = self._get_tier_position(new_position)

        current_tier, current_bucket = self.registry[item]

        # if within same tier: bucketedbinaryranking.moveitem
        if current_tier == new_tier:
            # bucketedbinaryranking.moveitem
            pass
        else:
            # if across tiers: remove from bucketedrank, direct insert into new tier bucketedrank
            result = self.items[current_tier].remove(item, current_bucket)

            if result:
                for shifted_item, idx in result.shifted:
                    self.registry[shifted_item][1] = idx

            result = self.items[new_tier].direct_insert(item, new_tier_position)

            self.registry[item] = [new_tier, result.bucket_idx]
            for shifted_item, idx in result.shifted:
                self.registry[shifted_item][1] = idx

    def _get_tier_position(self, position: int) -> tuple[int, int]:
        """Get tier for new item based on linear position in rank list"""
        for tier in range(self.tiers):
            tier_len = len(self.items[tier])
            if position < tier_len:
                return tier, position
            position -= tier_len
        raise IndexError("Linear index out of range")


class BucketedRanking:
    """Bucketed Ranked List"""

    def __init__(self, items: list[list[Any]] = None):
        self.items = items or []
        self._length = sum(len(bucket) for bucket in self.items)

    def __len__(self):
        """Get total number of items in the bucketed ranking"""
        return self._length

    def binary_insert(self, new_item: Any) -> UpdateResult:
        """
        :param self: bucketed ranking
        :param new_item: item to be inserted
        """
        low = 0
        high = len(self.items) - 1

        while low <= high:
            mid = (low + high) // 2
            c = self.compare(new_item, self.items[mid][0])
            if c == 0:  # no preference
                self.items[mid].append(new_item)
                return UpdateResult(bucket_idx=mid, shifted=[])
            elif c == 1:  # new item preferred
                low = mid + 1
            else:  # existing item preferred
                high = mid - 1

        # Low is the correct insertion index at loop termination
        self.items.insert(low, [new_item])
        self._length += 1

        shifted = [
            (item, i)
            for i in range(low + 1, len(self.items))
            for item in self.items[i]
        ]

        return UpdateResult(bucket_idx=low, shifted=shifted)

        # TODO: implement history tracing

    def direct_insert(self, new_item: Any, lin_position: int) -> UpdateResult | None:
        """
        :param new_item: item to be inserted
        :param lin_position: linear position in rank list
        """
        # position: linear position in rank list: number of elements to the left of new position
        bucket_idx, current_idx = self._get_coords(lin_position)

        if current_idx == 0:
            self.items.insert(bucket_idx, [new_item])

            shifted = [
                (item, i)
                for i in range(bucket_idx + 1, len(self.items))
                for item in self.items[i]
            ]

            self._length += 1
            return UpdateResult(bucket_idx=bucket_idx, shifted=shifted)
        else:
            # split bucket and insert item between the two splits
            self._split_bucket(bucket_idx, current_idx)
            self.items.insert(bucket_idx + 1, [new_item])

            shifted = [
                (item, i)
                for i in range(bucket_idx + 1, len(self.items))
                for item in self.items[i]
            ]

            self._length += 1
            return UpdateResult(bucket_idx=bucket_idx + 1, shifted=shifted)

    def move_item(self, item: Any, new_position: int) -> UpdateResult | None:
        # bubble elements between previous and new position
        # if added into middle of bucket, split bucket
        # if added between buckets, remove from previous bucket and create new bucket

        # updateresult: shift between item position and new position, inclusive
        pass

    def remove(self, del_item: Any, bucket: int) -> UpdateResult | None:
        """
        :param del_item: item to be deleted
        :param bucket: bucket index where item is located
        """
        if bucket >= len(self.items):
            return None

        if del_item not in self.items[bucket]:
            return None

        self.items[bucket].remove(del_item)
        self._length -= 1

        if not self.items[bucket]:
            self.items.pop(bucket)
            shifted = [
                (item, i)
                for i in range(bucket, len(self.items))
                for item in self.items[i]
            ]
            return UpdateResult(bucket_idx=None, shifted=shifted)

        return UpdateResult(bucket_idx=bucket, shifted=[])

    def compare(self, new_item: Any, comparator: Any) -> Optional[int]:
        """
        :param new_item: item to be ranked
        :param comparator: item in the rank list to compare against
        :return: integers -1, 0, or 1 denoting ranking
        """
        # TODO: implement input listeners
        if new_item > comparator:
            return 1
        elif new_item < comparator:
            return -1
        elif new_item == comparator:
            return 0
        return None

    def _get_coords(self, linear_index) -> tuple[int, int]:
        """Find index of item in bucketed ranking from linear index"""
        current_idx = linear_index
        for bucket_idx, bucket in enumerate(self.items):
            bucket_len = len(bucket)
            if current_idx < bucket_len:
                return bucket_idx, current_idx
            current_idx -= bucket_len
        raise IndexError("Linear index out of range")

    def _split_bucket(self, bucket_idx: int, split_idx: int):
        """Split a bucket into two at the specified index"""
        bucket = self.items[bucket_idx]
        new_bucket = bucket[split_idx:]
        self.items[bucket_idx] = bucket[:split_idx]
        self.items.insert(bucket_idx + 1, new_bucket)
