"""Tiered Ranker"""
from typing import Any, Optional, Callable
from dataclasses import dataclass
from normalize import *


@dataclass
class UpdateResult:
    """Result of an insertion operation"""
    bucket_idx: int | None
    shifted: list[tuple[Any, int]]  # (item, new_bucket_idx) pairs


class GlobalTieredRanking:
    # bradley-terry rank aggregation over multiple individual tiered rankings
    pass


class IndividualTieredRanking:
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
        """Move item to new linear position in tiered rank list
        :param item: item to be moved
        :param new_position: new linear position in tiered rank list
        """
        new_tier, new_tier_position = self._get_tier_position(new_position)

        current_tier, current_bucket = self.registry[item]

        # if within same tier: bucketedbinaryranking.moveitem
        if current_tier == new_tier:
            result = self.items[new_tier].move_item(item, current_bucket, new_tier_position)
            if result:
                self.registry[item] = [new_tier, result.bucket_idx]
                for shifted_item, idx in result.shifted:
                    self.registry[shifted_item][1] = idx
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

        self.normalize(self.scale)

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

    def move_item(self, item: Any, bucket: int, new_position: int) -> UpdateResult | None:
        """
        :param item: item to be moved
        :param bucket: current bucket index of the item"""

        if bucket >= len(self.items):
            return None

        if item not in self.items[bucket]:
            return None

        # get current linear position of item
        old_linear_position = self._get_linear_position(item, bucket)

        if old_linear_position == new_position:
            return UpdateResult(bucket_idx=bucket, shifted=[])

        # remove item from current position, then re-insert at adjusted new position
        self.remove(item, bucket)
        adjusted_position = new_position if new_position < old_linear_position else new_position - 1
        self.direct_insert(item, adjusted_position)

        new_bucket, _ = self._get_coords(adjusted_position)
        start = min(bucket, new_bucket)
        shifted = [
            (itm, i)
            for i in range(start, len(self.items))
            for itm in self.items[i]
        ]
        return UpdateResult(bucket_idx=new_bucket, shifted=shifted)

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
        """Find index of item in bucketed ranking
        :param linear_index: linear index in rank list
        :return: (bucket index, index within bucket)
        """
        current_idx = linear_index
        for bucket_idx, bucket in enumerate(self.items):
            bucket_len = len(bucket)
            if current_idx < bucket_len:
                return bucket_idx, current_idx
            current_idx -= bucket_len
        raise IndexError("Linear index out of range")

    def _get_linear_position(self, item: Any, bucket: int) -> int:
        """Get linear position from bucket index and index within bucket"""
        linear = sum(len(self.items[i]) for i in range(bucket))
        linear += self.items[bucket].index(item)
        return linear

    def _split_bucket(self, bucket_idx: int, split_idx: int):
        """Split a bucket into two at the specified index"""
        bucket = self.items[bucket_idx]
        new_bucket = bucket[split_idx:]
        self.items[bucket_idx] = bucket[:split_idx]
        self.items.insert(bucket_idx + 1, new_bucket)
