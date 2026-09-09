"""Compressed elementary lower/upper bounds; no exact cached-value shortcut."""
from functools import lru_cache


def prepare(jobs):
    prices = [(w + min(v, g + r), p + g + r - min(v, g + r)) for w, p, g, v, r in jobs]

    @lru_cache(None)
    def state(mask):
        selected = [prices[i] for i in range(len(prices)) if mask & (1 << i)]
        increments = {}
        threshold = 0
        for cost, premium in selected:
            count, rest = divmod(premium, cost)
            threshold += count + bool(rest)
            if count:
                increments[cost] = increments.get(cost, 0) + count
            if rest:
                increments[rest] = increments.get(rest, 0) + 1
        grouped = {}
        for cost,premium in selected:grouped[cost]=grouped.get(cost,0)+premium
        tail=sum(grouped.values());lines=[(0,tail)]
        for cost in sorted(grouped):
            tail-=grouped[cost];lines.append((cost,tail))
        return sorted(increments.items(), reverse=True), lines, threshold

    def evaluate(mask, budget):
        increments, lines, _ = state(mask)
        left, lower = budget, 0
        for increment, count in increments:
            used = min(left, count)
            lower += used * increment
            left -= used
            if not left:
                break
        upper = min(intercept + slope * budget for slope, intercept in lines)
        assert lower <= upper
        return lower, upper

    def threshold(mask):
        return state(mask)[2]

    return evaluate, threshold
