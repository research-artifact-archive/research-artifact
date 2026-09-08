"""Persistent AVL slope profiles for an arbitrary prescribed serial order.

Pure Python integer arithmetic; no iteration over a numerical budget/price.
Forced-order DAG optimality uses the separately proved primitive abstraction.
"""
from dataclasses import dataclass


@dataclass(frozen=True, slots=True, eq=False)
class Node:
    h: int
    count: int
    left: object
    right: object
    height: int
    length: int
    area: int
    first: int
    last: int
    runs: int


def height(t): return 0 if t is None else t.height
def length(t): return 0 if t is None else t.length
def area(t): return 0 if t is None else t.area
def runs(t): return 0 if t is None else t.runs


class Builder:
    def __init__(self):
        self.allocated = 0
        self.steps = 0

    def node(self, left, h, count, right):
        assert type(h) is int and h > 0 and type(count) is int and count > 0
        assert left is None or left.last > h
        assert right is None or h > right.first
        self.allocated += 1
        return Node(h, count, left, right,
                    1 + max(height(left), height(right)),
                    length(left) + count + length(right),
                    area(left) + h * count + area(right),
                    h if left is None else left.first,
                    h if right is None else right.last,
                    runs(left) + 1 + runs(right))

    def balanced(self, left, h, count, right):
        """Balance one AVL splice whose child heights differ by at most two."""
        if height(left) > height(right) + 1:
            assert height(left) == height(right) + 2
            if height(left.left) >= height(left.right):
                return self.node(left.left, left.h, left.count,
                                 self.node(left.right, h, count, right))
            pivot = left.right
            return self.node(self.node(left.left, left.h, left.count, pivot.left),
                             pivot.h, pivot.count,
                             self.node(pivot.right, h, count, right))
        if height(right) > height(left) + 1:
            assert height(right) == height(left) + 2
            if height(right.right) >= height(right.left):
                return self.node(self.node(left, h, count, right.left),
                                 right.h, right.count, right.right)
            pivot = right.left
            return self.node(self.node(left, h, count, pivot.left),
                             pivot.h, pivot.count,
                             self.node(pivot.right, right.h, right.count, right.right))
        return self.node(left, h, count, right)

    def join(self, left, h, count, right):
        self.steps += 1
        if height(left) > height(right) + 1:
            middle = self.join(left.right, h, count, right)
            return self.balanced(left.left, left.h, left.count, middle)
        if height(right) > height(left) + 1:
            middle = self.join(left, h, count, right.left)
            return self.balanced(middle, right.h, right.count, right.right)
        return self.node(left, h, count, right)

    def split(self, tree, count):
        """Return first count slope positions and the remainder, sharing nodes."""
        self.steps += 1
        assert 0 <= count <= length(tree)
        if count == 0: return None, tree
        if count == length(tree): return tree, None
        left_length = length(tree.left)
        if count < left_length:
            a, b = self.split(tree.left, count)
            return a, self.join(b, tree.h, tree.count, tree.right)
        if count > left_length + tree.count:
            a, b = self.split(tree.right, count-left_length-tree.count)
            return self.join(tree.left, tree.h, tree.count, a), b
        take = count-left_length
        a = tree.left if take == 0 else self.join(tree.left, tree.h, take, None)
        b = tree.right if take == tree.count else self.join(None, tree.h, tree.count-take, tree.right)
        return a, b

    def concatenate(self, left, right):
        if left is None: return right
        if right is None: return left
        assert left.last >= right.first
        # Pop only the boundary run. Each split/join is logarithmic.
        cursor = left
        while cursor.right is not None:
            self.steps += 1
            cursor = cursor.right
        h, m = cursor.h, cursor.count
        prefix, _ = self.split(left, left.length-m)
        if h == right.first:
            cursor = right
            while cursor.left is not None:
                self.steps += 1
                cursor = cursor.left
            m += cursor.count
            _, right = self.split(right, cursor.count)
        return self.join(prefix, h, m, right)

    def prefix_at_least(self, tree, c):
        count = 0
        while tree is not None:
            self.steps += 1
            if tree.h >= c:
                count += length(tree.left) + tree.count
                tree = tree.right
            else:
                tree = tree.left
        return count

    def crossing(self, tree, c, premium):
        """First low-slope position t with deficit>=premium, and its increment."""
        assert premium > 0 and (tree is None or tree.first < c)
        capacity = c*length(tree)-area(tree)
        if premium > capacity:
            residual = premium-capacity
            steps = (residual+c-1)//c
            return length(tree)+steps, 0, residual-c*(steps-1)
        offset = 0
        while tree is not None:
            self.steps += 1
            before = c*length(tree.left)-area(tree.left)
            if premium <= before:
                tree = tree.left
                continue
            premium -= before
            offset += length(tree.left)
            capacity = (c-tree.h)*tree.count
            if premium <= capacity:
                steps = (premium+c-tree.h-1)//(c-tree.h)
                return offset+steps, tree.h, premium-(c-tree.h)*(steps-1)
            premium -= capacity
            offset += tree.count
            tree = tree.right
        raise AssertionError('finite crossing disappeared')

    def prepend(self, suffix, c, premium):
        if premium == 0: return suffix, 0
        start = self.prefix_at_least(suffix, c)
        prefix, low = self.split(suffix, start)
        t, h, increment = self.crossing(low, c, premium)
        _, remainder = self.split(low, min(t, length(low)))
        replacement = None if t == 1 else self.node(None, c, t-1, None)
        replacement = self.concatenate(replacement, self.node(None, h+increment, 1, None))
        result = self.concatenate(self.concatenate(prefix, replacement), remainder)
        assert area(result) == area(suffix)+premium
        assert runs(result) <= runs(suffix)+2
        return result, start+t


def validate_order(case, order=None):
    cp = case['cp']; n = len(cp)
    if any(type(row) not in (list, tuple) or len(row) != 2
           or type(row[0]) is not int or row[0] <= 0
           or type(row[1]) is not int or row[1] < 0 for row in cp):
        raise ValueError('integer c>0,p>=0 required')
    children = [[] for _ in cp]; indegree = [0]*n; seen = set()
    for edge in case['edges']:
        if len(edge) != 2 or any(type(i) is not int or not 0 <= i < n for i in edge):
            raise ValueError('bad dependency')
        a, b = edge
        if a == b or (a, b) in seen: raise ValueError('self/duplicate dependency')
        seen.add((a, b)); children[a].append(b); indegree[b] += 1
    ready = [i for i in range(n) if not indegree[i]]
    found = []; unique = True
    while ready:
        unique &= len(ready) == 1
        i = ready.pop(); found.append(i)
        for j in children[i]:
            indegree[j] -= 1
            if not indegree[j]: ready.append(j)
    if len(found) != n: raise ValueError('cyclic dependencies')
    if order is None:
        if not unique: raise ValueError('DAG has multiple topological orders; supply a prescribed order')
        return found, True
    if (len(order) != n or any(type(i) is not int for i in order)
            or sorted(order) != list(range(n))): raise ValueError('bad order permutation')
    positions = [0]*n
    for k, i in enumerate(order): positions[i] = k
    if any(positions[a] >= positions[b] for a, b in seen): raise ValueError('non-topological order')
    return list(order), unique


def serialize(roots):
    rows = []; identifiers = {}
    def visit(node):
        if node is None: return -1
        if node in identifiers: return identifiers[node]
        left = visit(node.left); right = visit(node.right)
        index = len(rows); identifiers[node] = index
        rows.append([node.h, node.count, left, right, node.height, node.length,
                     node.area, node.first, node.last, node.runs])
        return index
    root_ids = [visit(root) for root in roots]
    return rows, root_ids


def compile_case(case, order=None):
    order, unique = validate_order(case, order)
    builder = Builder(); roots = [None]*(len(order)+1); thresholds = [0]*len(order)
    for k in range(len(order)-1, -1, -1):
        c, premium = case['cp'][order[k]]
        roots[k], thresholds[k] = builder.prepend(roots[k+1], c, premium)
    nodes, root_ids = serialize(roots)
    return dict(schema='retry-persistent-order-v1', route='persistent_order', input=case,
                order=order, unique_topological_order=unique, nodes=nodes, roots=root_ids,
                protect_at_budget=thresholds, normal_cost=sum(c for c, _ in case['cp']),
                stats=dict(allocated_nodes=builder.allocated, construction_steps=builder.steps,
                           serialized_nodes=len(nodes), root_runs=runs(roots[0])))


def value(data, budget, cursor=0):
    if type(budget) is not int or budget < 0: raise ValueError('budget')
    if type(cursor) is not int or not 0 <= cursor <= len(data['order']): raise ValueError('cursor')
    nodes = data['nodes']; index = data['roots'][cursor]; total = 0
    while index != -1 and budget:
        h, count, left, right, _, size, mass, _, _, _ = nodes[index]
        if budget >= size: return total+mass
        left_size = 0 if left == -1 else nodes[left][5]
        if budget < left_size:
            index = left
            continue
        total += 0 if left == -1 else nodes[left][6]
        budget -= left_size
        take = min(count, budget); total += h*take; budget -= take
        index = right
    return total


def choose(data, cursor, budget):
    if type(budget) is not int or budget < 0: raise ValueError('budget')
    if type(cursor) is not int or not 0 <= cursor < len(data['order']): raise ValueError('cursor')
    return data['order'][cursor], ('protected' if budget >= data['protect_at_budget'][cursor] else 'fast')
