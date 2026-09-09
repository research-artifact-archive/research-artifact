"""Pre-specified average-cost fitting and full price-sensitivity grid.

Small nonnegative least squares is solved by enumerating all16 active sets,
using exact rational arithmetic on the decimal representations of JMH samples.
"""
from pathlib import Path
from fractions import Fraction as Q
from functools import lru_cache
import collections
import hashlib
import itertools
import json

HERE = Path(__file__).resolve().parent
PATHS = ('prepare', 'replaceMatch', 'replaceMismatch',
         'validateCallbackMatch', 'validateCallbackMismatch', 'freshCallback')
DESIGN = ((1, 0, 0, 0), (0, 1, 0, 0), (0, 1, 0, 0),
          (0, 0, 1, 0), (0, 0, 1, 0), (1, 0, 1, 1))


def solve_linear(matrix, vector):
    n = len(vector)
    rows = [list(map(Q, row)) + [Q(value)] for row, value in zip(matrix, vector)]
    for i in range(n):
        pivot = next(j for j in range(i, n) if rows[j][i])
        rows[i], rows[pivot] = rows[pivot], rows[i]
        coefficient = rows[i][i]
        rows[i] = [value / coefficient for value in rows[i]]
        for j in range(n):
            if j == i:
                continue
            coefficient = rows[j][i]
            rows[j] = [value - coefficient * pivot_value for value, pivot_value in zip(rows[j], rows[i])]
    return [row[-1] for row in rows]


def fit(observed):
    candidates = []
    for mask in range(16):
        columns = [i for i in range(4) if mask & (1 << i)]
        gram = [[sum(row[i] * row[j] for row in DESIGN) for j in columns] for i in columns]
        rhs = [sum(row[i] * y for row, y in zip(DESIGN, observed)) for i in columns]
        values = solve_linear(gram, rhs)
        if any(value < 0 for value in values):
            continue
        prices = [Q(0)] * 4
        for column, value in zip(columns, values):
            prices[column] = value
        prediction = [sum(Q(a) * b for a, b in zip(row, prices)) for row in DESIGN]
        squared_error = sum((actual - pred) ** 2 for actual, pred in zip(observed, prediction))
        candidates.append((squared_error, mask, prices, prediction))
    error, mask, prices, prediction = min(candidates)
    relative = [abs(actual - pred) / actual for actual, pred in zip(observed, prediction)]
    # Normal equation active-set enumeration reaches the NNLS minimum; also
    # independently verify its first-order conditions under x>=0.
    gradient = [sum(Q(row[i]) * (pred - actual) for row, actual, pred in zip(DESIGN, observed, prediction))
                for i in range(4)]
    assert all(g == 0 if x > 0 else g >= 0 for x, g in zip(prices, gradient))
    return dict(prices_ns={name: float(value) for name, value in zip(('w', 'v', 'k', 'p'), prices)},
                exact_prices_ns={name: str(value) for name, value in zip(('w', 'v', 'k', 'p'), prices)},
                prediction_ns=list(map(float, prediction)), squared_error_ns2=float(error),
                relative_absolute_errors=list(map(float, relative)),
                max_relative_error=float(max(relative)),
                representable=prices[0] > 0 and max(relative) <= Q(1, 5))


def value(prices, budget, allow_cached):
    @lru_cache(None)
    def solve(mask, b):
        if not mask or not b:
            return 0
        choices = []
        for i, job in enumerate(prices):
            if not mask & (1 << i):
                continue
            w, p, v, k = (job[key] for key in ('w', 'p', 'v', 'k'))
            m = min(v, k)
            delta = k - m
            child = solve(mask ^ (1 << i), b)
            choices.append(p + delta + child)
            choices.append(max(child, w + m + solve(mask, b - 1)))
            if allow_cached:
                choices.append(delta + max(child, w + p + solve(mask ^ (1 << i), b - 1)))
        return min(choices)
    baseline = sum(job['w'] + min(job['v'], job['k']) for job in prices)
    return baseline + solve((1 << len(prices)) - 1, budget)


def main():
    attempt = HERE / 'attempt01'
    rows = json.loads((attempt / 'RESULTS.json').read_text())
    indexed = {(row['layout'], row['length'], row['method']): row for row in rows}
    fits = {}
    for layout, length in itertools.product(('distinct', 'colliding'), (1, 8, 64, 512)):
        records = {method: indexed[(layout, length, method)] for method in PATHS}
        identifier = f'{layout}-{length}'
        if any(row['status'] != 'SUCCESS' for row in records.values()):
            fits[identifier] = dict(status='MISSING_MEASUREMENT', representable=False,
                                    methods={method: row['status'] for method, row in records.items()})
            continue
        samples = {}
        files = {}
        for method, row in records.items():
            path = attempt / row['id'] / 'JMH.json'
            data = json.loads(path.read_text())[0]
            samples[method] = [[Q(str(value)) for value in fork] for fork in data['primaryMetric']['rawData']]
            files[method] = hashlib.sha256(path.read_bytes()).hexdigest()
        means = [sum((sum(fork) for fork in samples[method]), Q(0)) / 10 for method in PATHS]
        result = fit(means)
        result.update(status='FIT', observed_means_ns={method: float(y) for method, y in zip(PATHS, means)},
                      raw_protection_residual_ns=float(means[5] - max(means[3], means[4]) - means[0]),
                      raw_hashes=files, fork_fits=[])
        for index in range(2):
            result['fork_fits'].append(fit([sum(samples[method][index], Q(0)) / 5 for method in PATHS]))
        fits[identifier] = result
    grid = []
    for layout, left, right, weight, budget in itertools.product(
            ('distinct', 'colliding'), (1, 8, 64, 512), (1, 8, 64, 512),
            (Q(0), Q(1, 4), Q(1), Q(4)), range(9)):
        row = dict(layout=layout, lengths=[left, right], protected_weight=str(weight), budget=budget)
        selected = [fits[f'{layout}-{length}'] for length in (left, right)]
        if not all(result['representable'] for result in selected):
            row.update(status='OUTSIDE_CALIBRATED_MODEL')
        else:
            prices = []
            for result in selected:
                exact = {key: Q(number) for key, number in result['exact_prices_ns'].items()}
                exact['p'] += weight * exact['w']
                rounded = {key: round(number * 1000) for key, number in exact.items()}
                assert rounded['w'] > 0
                prices.append(rounded)
            two = value(prices, budget, False)
            three = value(prices, budget, True)
            assert three <= two
            row.update(status='SUCCESS', prices_picoseconds=prices,
                       two_mode_total=two, three_mode_total=three, strict_improvement=three < two,
                       relative_improvement=(two - three) / two)
        grid.append(row)
    assert len(grid) == 1152
    output = dict(classification='Exploratory average-price sensitivity; positive protected weights are declared, not timing predictions',
                  fit_denominator=8, fits=fits, sensitivity_denominator=1152, grid=grid,
                  grid_partition=dict(collections.Counter(row['status'] for row in grid)),
                  strict_by_weight={str(weight): sum(row.get('strict_improvement', False) and row['protected_weight'] == str(weight)
                                                    for row in grid) for weight in (Q(0), Q(1, 4), Q(1), Q(4))})
    with (attempt / 'ANALYSIS01.json').open('x') as stream:
        json.dump(output, stream, indent=2)
        stream.write('\n')
    print(json.dumps({key: output[key] for key in ('fit_denominator', 'grid_partition', 'strict_by_weight')}, indent=2))


if __name__ == '__main__':
    main()
