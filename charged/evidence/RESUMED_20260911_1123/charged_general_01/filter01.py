"""Exact heterogeneous-premium residual filter; no future bodies, edges or B."""


def integer(value, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError('expected integer in declared domain')
    return value


class ChargedFilter:
    def __init__(self, future_fees, completed_q, k=0, incurred=0):
        self.n = len(future_fees) + len(completed_q)
        if set(future_fees) & set(completed_q) or set(future_fees) | set(completed_q) != set(range(self.n)):
            raise ValueError('job IDs must partition 0..n-1')
        self.k = integer(k)
        self.incurred = integer(incurred)
        if k > len(completed_q):
            raise ValueError('mismatch count exceeds completed jobs')
        self.values = [0] * self.n
        self.done = [False] * self.n
        for i, h in future_fees.items():
            integer(i)
            self.values[i] = integer(h)
        for i, q in completed_q.items():
            integer(i)
            self.values[i] = integer(q, 1)
            self.done[i] = True
        self.heaps = [[-1] * self.n, [-1] * self.n]
        self.sizes = [self.n, 0]
        self.side = [0] * self.n
        self.pos = list(range(self.n))
        self.heaps[0][:] = range(self.n)
        self.total = 0
        self.comparisons = 0
        self.swaps = 0
        for at in range(self.n // 2 - 1, -1, -1):
            self._down(0, at)
        for _ in range(k):
            self._push(1, self._pop(0))

    def _better(self, side, a, b):
        self.comparisons += 1
        va, vb = self.values[a], self.values[b]
        return (va, a) < (vb, b) if side else (va, a) > (vb, b)

    def _swap(self, side, a, b):
        arr = self.heaps[side]
        arr[a], arr[b] = arr[b], arr[a]
        self.pos[arr[a]], self.pos[arr[b]] = a, b
        self.swaps += 1

    def _up(self, side, at):
        while at:
            parent = (at - 1) // 2
            if not self._better(side, self.heaps[side][at], self.heaps[side][parent]):
                break
            self._swap(side, at, parent)
            at = parent

    def _down(self, side, at):
        while 2 * at + 1 < self.sizes[side]:
            child = 2 * at + 1
            if child + 1 < self.sizes[side] and self._better(side, self.heaps[side][child + 1], self.heaps[side][child]):
                child += 1
            if not self._better(side, self.heaps[side][child], self.heaps[side][at]):
                break
            self._swap(side, at, child)
            at = child

    def _pop(self, side):
        if not self.sizes[side]:
            raise ValueError('empty heap')
        arr = self.heaps[side]
        result = arr[0]
        self.sizes[side] -= 1
        size = self.sizes[side]
        if size:
            arr[0] = arr[size]
            self.pos[arr[0]] = 0
        arr[size] = -1
        self.pos[result] = -1
        if size:
            self._down(side, 0)
        if side:
            self.total -= self.values[result]
        return result

    def _push(self, side, job):
        at = self.sizes[side]
        if at >= self.n:
            raise ValueError('fixed capacity exceeded')
        self.heaps[side][at] = job
        self.sizes[side] += 1
        self.side[job], self.pos[job] = side, at
        if side:
            self.total += self.values[job]
        self._up(side, at)

    def limits(self, job, body):
        integer(job)
        integer(body, 1)
        if job >= self.n or self.done[job]:
            raise ValueError('job must be unfinished')
        h = self.values[job]
        sigma = self.values[self.heaps[0][0]] if self.sizes[0] else 0
        cached = self.total - max(0, h - sigma)
        if self.k:
            tau = self.values[self.heaps[1][0]]
            fresh = self.total - min(body, max(0, tau - h))
        else:
            fresh = -body
        return {'cached': cached, 'fresh': fresh}

    def permissions(self, job, body):
        return {mode: self.incurred <= limit for mode, limit in self.limits(job, body).items()}

    def complete(self, job, body, mode, mismatch=None):
        if mode not in ('fresh', 'cached'):
            raise ValueError('unknown mode')
        limits = self.limits(job, body)
        if mode not in limits or self.incurred > limits[mode]:
            raise ValueError('unsafe or unknown mode')
        if (mode == 'fresh' and mismatch is not None) or (mode == 'cached' and type(mismatch) is not bool):
            raise ValueError('outcome must follow mode contract')
        h = self.values[job]
        self.values[job] += body
        self.done[job] = True
        side = self.side[job]
        if side:
            self.total += body
            self._down(1, self.pos[job])
        else:
            self._up(0, self.pos[job])
        if self.sizes[0] and self.sizes[1] and self.values[self.heaps[0][0]] > self.values[self.heaps[1][0]]:
            low, high = self._pop(0), self._pop(1)
            self._push(0, high)
            self._push(1, low)
        if mode == 'fresh':
            self.incurred += body
        elif mismatch:
            self.incurred += body + h
            self.k += 1
            self._push(1, self._pop(0))

    def viable(self):
        return self.incurred <= self.total

    def inspect(self):
        """Author verification only: not a scheduler-observation interface."""
        return {'values': tuple(self.values), 'done': tuple(self.done), 'k': self.k,
                'incurred': self.incurred, 'top_sum': self.total,
                'heap_sizes': tuple(self.sizes), 'comparisons': self.comparisons,
                'swaps': self.swaps}
