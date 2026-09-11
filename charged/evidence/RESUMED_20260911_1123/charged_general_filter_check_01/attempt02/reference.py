"""Dictionary + explicit sorting oracle; no optimized query algebra or theorem DP."""
from dataclasses import dataclass


def top(entries, k):
    return sum(sorted(entries, reverse=True)[:k])


@dataclass
class SortingReference:
    future: dict
    completed: dict
    k: int = 0
    incurred: int = 0

    @classmethod
    def from_case(cls, case):
        return cls(dict(case['future']), dict(case['completed']), case['k'], case['incurred'])

    def ceiling(self):
        return top(list(self.completed.values()) + list(self.future.values()), self.k)

    def viable(self):
        return self.incurred <= self.ceiling()

    def limits(self, job, body):
        x = list(self.completed.values()) + [h for i, h in self.future.items() if i != job]
        return {'cached': top(x, self.k),
                'fresh': top(x + [self.future[job] + body], self.k) - body}

    def permissions(self, job, body):
        return {m: self.incurred <= v for m, v in self.limits(job, body).items()}

    def complete(self, job, body, mode, mismatch):
        if not self.permissions(job, body)[mode]:
            raise ValueError('oracle forbids this action')
        q = self.future.pop(job) + body
        self.completed[job] = q
        if mode == 'fresh':
            self.incurred += body
        elif mismatch:
            self.incurred += q
            self.k += 1

    def state(self):
        return {'future': sorted(self.future.items()), 'completed': sorted(self.completed.items()),
                'k': self.k, 'incurred': self.incurred}
