"""Author implementation of PROOF02; positive integer whole-kernel weights.

Queries take O(1) heap accesses. Each completing action updates in O(log n)
heap operations. No unfinished-job list, future weights or DAG is stored here.
This component enforces the explicit residual contract, not W-optimal choices.
"""
from heapq import heappush, heappop, heapreplace

class ResidualFilter:
    def __init__(self, completed=(), k=0, protected=0):
        if not isinstance(k, int) or k < 0:
            raise ValueError('credit must be a nonnegative integer')
        if not isinstance(protected, int) or protected < 0:
            raise ValueError('protected work must be a nonnegative integer')
        self.k = k
        self.protected = protected
        self.high = []
        self.low = []  # negative weights, max-heap
        self.top_sum = 0
        self.completed_count = 0
        for weight in completed:
            self._insert(weight)
        if self.protected > self.top_sum:
            raise ValueError('nonviable residual state')

    @staticmethod
    def _check_weight(weight):
        if not isinstance(weight, int) or isinstance(weight, bool) or weight <= 0:
            raise ValueError('weight must be a positive integer')

    def _insert(self, weight):
        self._check_weight(weight)
        self.completed_count += 1
        if len(self.high) < self.k:
            heappush(self.high, weight)
            self.top_sum += weight
        elif self.high and weight > self.high[0]:
            removed = heapreplace(self.high, weight)
            self.top_sum += weight - removed
            heappush(self.low, -removed)
        else:
            heappush(self.low, -weight)

    def prospective_top(self, weight):
        self._check_weight(weight)
        if self.k == 0:
            return 0
        if len(self.high) < self.k:
            return self.top_sum + weight
        return self.top_sum + max(0, weight - self.high[0])

    def permits_fresh(self, weight):
        return self.protected + weight <= self.prospective_top(weight)

    def complete(self, weight, outcome):
        self._check_weight(weight)
        if outcome not in ('fresh', 'match', 'mismatch'):
            raise ValueError('unknown completing outcome')
        if outcome == 'fresh' and not self.permits_fresh(weight):
            raise ValueError('fresh completion would violate residual contract')
        if outcome == 'mismatch':
            self.k += 1
            if self.low:
                promoted = -heappop(self.low)
                heappush(self.high, promoted)
                self.top_sum += promoted
        if outcome in ('fresh', 'mismatch'):
            self.protected += weight
        self._insert(weight)
        if self.protected > self.top_sum:
            raise AssertionError('implementation invariant failed')
