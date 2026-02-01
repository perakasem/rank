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
    """Beli Ranking Algorithm Reimplementation"""
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
        self.items: dict[int, BucketedRanking] = {i: BucketedRanking() for i in range(1, tiers+1)}
        self.registry: dict[Any, list[int]] = {} # [tier id, bucket idx]
        self.scores: dict[Any, float] = {}

    def normalize(self, scale: int):
        """Cardinal scoring"""
        # linearize tiers, cdf to handle buckets
        self.normalize_fn(scale)
        # update self.scores
        pass

    def getrankbyitem(self):
        pass

    def getitemsbyrank(self):
        pass

    def insert(self, new_item: Any, tier: int):
        """Insert new item into appropriate tiered binrank"""
        # update registry tier
        result = self.items[tier].binary_insert(new_item, self.registry)
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

    def rerank(self):
        # if within same bucket: bucketedbinaryrank.rerank
        # if across tiers: remove from binrank, direct insert into new tier binrank
        pass


class BucketedRanking:
    """Bucketed Ranked List"""

    def __init__(self, items: list[list[Any]] = None):
        self.items = items or []

    def binary_insert(self, new_item: Any) -> UpdateResult:
        """
        :param self:
        :param new_item:
        """
        low = 0
        high = len(self.items) - 1

        while low <= high:
            mid = (low + high) // 2
            c = self.compare(new_item, self.items[mid][0])
            if c == 0:
                self.items[mid].append(new_item)
                return UpdateResult(bucket_idx=mid, shifted=[])
            elif c == 1:
                # Better than mid
                low = mid + 1
            else:
                # Worse than mid
                high = mid - 1

        # If we exit the loop low is the correct insertion index
        self.items.insert(low, [new_item])

        shifted = [
            (item, i)
            for i in range(low + 1, len(self.items))
            for item in self.items[i]
        ]

        return UpdateResult(bucket_idx=low, shifted=shifted)

        # TODO: implement history tracing

    def direct_insert(self, new_item: Any, position: int, registry: Optional[dict]) -> None:
        pass

    def remove(self, del_item: Any, bucket: int) -> UpdateResult | None:
        if bucket >= len(self.items):
            return None

        if del_item not in self.items[bucket]:
            return None

        self.items[bucket].remove(del_item)

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


