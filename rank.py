"""Tiered Ranker"""
from typing import Any, Optional, Callable
from normalize import *


class GlobalBeliRank:
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
        # add log-normal tier skew support
        self.tier_thresholds: list[int] = tier_thresholds or [i * (scale/tiers) for i in range(1, tiers+1)]
        self.history: str = ""
        self.items: dict[int, BucketedBinaryRanking] = {i: BucketedBinaryRanking() for i in range(1, tiers+1)}
        self.registry: dict[Any, list[int]] = {} # [tier id, bucket id]
        self.scores: dict[Any, float] = {}

    def normalize(self, scale: int):
        """Cardinal scoring"""
        # linearize tiers, cdf to handle buckets
        self.normalize_fn(scale)
        # update rankmap
        pass

    def getrankbyitem(self):
        pass

    def getitemsbyrank(self):
        pass

    def insert(self, new_item: Any, tier: int):
        """Insert new item into appropriate tiered binrank"""
        worker = self.items[tier]
        worker.binary_insert(new_item)
        self.normalize(self.scale)

    def remove(self, del_item: Any):
        """Remove item from appropriate tiered binrank"""
        for tier in self.items:
            self.items[tier].remove(del_item)
        self.normalize(self.scale)

    def rerank(self):
        # if within same bucket: bucketedbinaryrank.rerank
        # if across tiers: remove from binrank, direct insert into new tier binrank
        pass


class BucketedBinaryRanking:
    """Bucketed Binary Ranked List"""

    def __init__(self, items: list[list[Any]] = None):
        self.items = items or []

    def binary_insert(self, new_item) -> None:
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
                return
            elif c == 1:
                # Better than mid
                low = mid + 1
            else:
                # Worse than mid
                high = mid - 1

        # If we exit the loop low is the correct insertion index
        self.items.insert(low, [new_item])

        # TODO: implement history tracing

    def direct_insert(self, new_item: Any, position: int) -> None:
        pass

    def remove(self, del_item: Any) -> None:
        for bucket in self.items:
            for item in bucket:
                if del_item == item:
                    bucket.remove(item)
                    if not bucket:
                        self.items.remove(bucket)
                    return
        # re-implement using rankmap for efficiency

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


