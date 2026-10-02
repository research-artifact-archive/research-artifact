#!/usr/bin/env python3
"""Read-only, per-key QA of the saved outcome grid.

This reads explicit TikZ nodes; it neither imports the figure generator nor
executes TeX or a solver. Column and row identities come from displayed labels
and their coordinates, not from node order or a hard-coded coordinate table.
The deliberately narrow parser rejects unsupported/unparsed nodes.

Run: python3 -B reproduce/check_outcome_grid.py --self-test
Only this program's stdout is written. Negative cases are in-memory strings.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from dataclasses import dataclass
from decimal import Decimal
from itertools import product
from pathlib import Path
import re


HERE = Path(__file__).resolve().parent
METHOD_LABELS = {
    'Lazy': 'fg_ducs_otf',
    'Eager': 'fg_ducs_otf_eager_controllable',
    'Update-first': 'fg_ducs_otf_update_first',
    'Direct-Full': 'direct_full',
}
ROW_LABELS = {
    'GSM': 'gsm', 'Industry': 'industry', 'MetaSocket': 'metasocket',
    'PowerPlant': 'powerplant', 'PC1': 'productioncell_arms1',
    'PC2': 'productioncell_arms2', 'Railcab': 'railcab',
    'Surveillance': 'surveillance', 'Workflow': 'workflow',
}
COLUMN_LABELS = {'B': 'base', 'R1': 'r1', 'R2': 'r2'}
CSV_STATUS = {'SUCCESS': 'W', 'UNREALIZABLE': 'L', 'TIMEOUT': 'T'}
CELL_STYLE = {'win': 'W', 'loss': 'L', 'timeout': 'T'}
NUMBER = r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)'
NODE = re.compile(
    r'\\node\s*\[(?P<options>[^\]]*)\]\s*at\s*'
    r'\(\s*(?P<x>' + NUMBER + r')\s*,\s*(?P<y>' + NUMBER + r')\s*\)\s*'
    r'\{(?P<label>[^{}]*)\}\s*;', re.S)


class InvalidGrid(ValueError):
    pass


def require(condition, kind, message):
    if not condition:
        raise InvalidGrid(kind + ': ' + message)


@dataclass(frozen=True)
class Node:
    options: str
    x: Decimal
    y: Decimal
    label: str
    source: str


def nodes(source):
    text = re.sub(r'(?<!\\)%[^\n]*', '', source)
    pictures = re.findall(r'\\begin\{tikzpicture\}(.*?)\\end\{tikzpicture\}', text, re.S)
    require(len(pictures) == 1, 'picture', 'Exactly one explicit TikZ picture is required')
    picture = pictures[0]
    require(not re.search(r'\\(?:if\w*|else|fi|foreach|pgftransform\w*|tikzset)\b'
                          r'|\\begin\{scope\}|(?:xshift|yshift|rotate|xscale|yscale)\s*=', picture),
            'unsupported', 'Conditional, generated or transformed node positions are unsupported')
    matches = list(NODE.finditer(picture))
    require(len(matches) == len(re.findall(r'\\node\b', picture)),
            'parser', 'Some visible-node declarations could not be parsed')
    return [Node(m['options'].strip(), Decimal(m['x']), Decimal(m['y']),
                 m['label'].strip(), m[0]) for m in matches]


def inventory(items, expected, kind):
    labels = Counter(n.label for n in items)
    require(labels == Counter(list(expected)), kind, 'Expected each displayed label once: ' + str(labels))


def decode(source):
    parsed = nodes(source)
    methods = [n for n in parsed if n.label in METHOD_LABELS]
    rows = [n for n in parsed if n.label in ROW_LABELS]
    columns = [n for n in parsed if n.label in COLUMN_LABELS]
    cells = [n for n in parsed if n.options in CELL_STYLE]
    inventory(methods, METHOD_LABELS, 'method_inventory')
    inventory(rows, ROW_LABELS, 'row_inventory')
    require(Counter(n.label for n in columns) == Counter({k: 4 for k in COLUMN_LABELS}),
            'column_inventory', 'Each method needs displayed B, R1 and R2 columns')
    known = set(methods + rows + columns + cells)
    other = [n for n in parsed if n not in known]
    normalized = lambda s: re.sub(r'\s+', ' ', re.sub(r'\\(?:qquad|quad)\b', ' ', s)).strip()
    expected_legend = 'W: WIN L: LOSS T: timeout B: Base; R1/R2: interval variants'
    require(len(other) == 2 and {normalized(n.label) for n in other} == {'Adapted input', expected_legend},
            'legend', 'Unexpected nodes or an altered status/variant legend')
    require(len({n.x for n in methods}) == 4 and len({n.y for n in methods}) == 1,
            'method_geometry', 'Distinct method headings must share a horizontal line')
    require(len({n.x for n in columns}) == 12 and len({n.y for n in columns}) == 1,
            'column_geometry', 'Twelve distinct columns must share a header line')
    require(len({n.y for n in rows}) == 9 and len({n.x for n in rows}) == 1,
            'row_geometry', 'Nine distinct row labels must share a left margin')
    require(rows[0].x < min(n.x for n in columns)
            and max(n.y for n in rows) < columns[0].y < methods[0].y,
            'header_geometry', 'Rows must be left of cells and headers above cells')

    column_identity, grouped = {}, {n.label: [] for n in methods}
    for column in columns:
        distance = min(abs(column.x - method.x) for method in methods)
        closest = [method for method in methods if abs(column.x - method.x) == distance]
        require(len(closest) == 1, 'method_geometry', 'A column is ambiguous between method headings')
        method = closest[0]
        grouped[method.label].append(column)
        column_identity[column.x] = (METHOD_LABELS[method.label], COLUMN_LABELS[column.label])
    for method in methods:
        group = grouped[method.label]
        inventory(group, COLUMN_LABELS, 'column_inventory')
        require(sorted(n.x for n in group)[1] == method.x,
                'method_geometry', 'The method heading must center its three columns')
    row_identity = {n.y: ROW_LABELS[n.label] for n in rows}
    result = {}
    for cell in cells:
        require(cell.label == CELL_STYLE[cell.options], 'style_label', 'Cell color/style and W/L/T disagree')
        require(cell.x in column_identity and cell.y in row_identity,
                'cell_position', 'A cell has no matching row/column heading')
        method, variant = column_identity[cell.x]
        key = (method, row_identity[cell.y], variant)
        require(key not in result, 'duplicate_cell', 'Duplicate key: ' + repr(key))
        result[key] = cell
    expected_keys = set(product(METHOD_LABELS.values(), ROW_LABELS.values(), COLUMN_LABELS.values()))
    require(set(result) == expected_keys, 'cell_coverage',
            'Missing or extra cells: ' + repr(sorted(expected_keys ^ set(result))))
    return result, parsed


def csv_expected(source):
    rows = list(csv.DictReader(source.splitlines()))
    require(bool(rows), 'csv', 'The saved CSV is empty')
    require({'method_id', 'model_id', 'target_id', 'effective_stage1_status'} <= set(rows[0]),
            'csv', 'Required saved result columns are absent')
    selected = {}
    for row in rows:
        if row['method_id'] not in METHOD_LABELS.values():
            continue  # Legacy is outside this four-procedure figure.
        key = (row['method_id'], row['model_id'], row['target_id'])
        require(key not in selected, 'csv_duplicate', 'Duplicate saved result: ' + repr(key))
        require(row['effective_stage1_status'] in CSV_STATUS, 'csv_status', 'Unsupported outcome at ' + repr(key))
        selected[key] = CSV_STATUS[row['effective_stage1_status']]
    expected_keys = set(product(METHOD_LABELS.values(), ROW_LABELS.values(), COLUMN_LABELS.values()))
    require(set(selected) == expected_keys, 'csv_coverage', 'The saved CSV does not cover exactly 108 selected keys')
    return selected


def verify(tex, expected):
    displayed, _ = decode(tex)
    mismatches = [(key, displayed[key].label, expected[key]) for key in expected
                  if displayed[key].label != expected[key]]
    require(not mismatches, 'cell_mismatch', repr(mismatches[:8]))
    return len(displayed)


def replace_nodes(source, replacements):
    # All replacements are decided before mutation; no temporary TeX is saved.
    require(all(source.count(old) == 1 for old in replacements), 'fixture', 'A mutation target is not unique')
    pattern = re.compile('|'.join(re.escape(old) for old in replacements))
    return pattern.sub(lambda m: replacements[m[0]], source)


def swap_labels(source, first, second):
    replace_label = lambda node, label: node.source.replace('{' + node.label + '}', '{' + label + '}')
    return replace_nodes(source, {first.source: replace_label(first, second.label),
                                  second.source: replace_label(second, first.label)})


def negative_cases(tex, expected):
    cells, parsed = decode(tex)
    a = cells[('fg_ducs_otf', 'gsm', 'base')]
    b = cells[('fg_ducs_otf', 'industry', 'r1')]
    def restatus(node, other):
        return node.source.replace('[' + node.options + ']', '[' + other.options + ']') \
            .replace('{' + node.label + '}', '{' + other.label + '}')
    swapped = replace_nodes(tex, {a.source: restatus(a, b), b.source: restatus(b, a)})
    swapped_cells, _ = decode(swapped)
    original_counts = Counter((key[0], node.label) for key, node in cells.items())
    require(Counter((key[0], node.label) for key, node in swapped_cells.items()) == original_counts,
            'fixture', 'The cell-swap negative must preserve every per-method W/L/T total')
    methods = {n.label: n for n in parsed if n.label in METHOD_LABELS}
    columns = [n for n in parsed if n.label in COLUMN_LABELS]
    lazy_columns = sorted(columns, key=lambda n: abs(n.x - methods['Lazy'].x))[:3]
    variants = {n.label: n for n in lazy_columns}
    industry_row = next(n for n in parsed if n.label == 'Industry')
    row_removed = replace_nodes(tex, {n.source: '' for n in parsed
                                      if n == industry_row or (n.options in CELL_STYLE and n.y == industry_row.y)})
    cases = [
        ('same_totals_cell_exchange', swapped, 'cell_mismatch'),
        ('method_heading_exchange', swap_labels(tex, methods['Lazy'], methods['Eager']), 'cell_mismatch'),
        ('variant_heading_exchange', swap_labels(tex, variants['B'], variants['R1']), 'cell_mismatch'),
        ('whole_row_missing', row_removed, 'row_inventory'),
    ]
    for name, altered, reason in cases:
        try:
            verify(altered, expected)
        except InvalidGrid as error:
            require(str(error).startswith(reason + ':'), 'fixture', name + ' failed for an unintended reason: ' + str(error))
        else:
            raise InvalidGrid('fixture: Negative case was accepted: ' + name)
    return [name for name, _, _ in cases]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tex', type=Path, default=HERE.parent / 'paper/source/figures/rq3_outcome_grid.tex')
    parser.add_argument('--csv', type=Path, default=HERE.parent / 'paper/source/build/generated/rq3-cells.csv')
    parser.add_argument('--self-test', action='store_true', help='Also reject four in-memory semantic mutations')
    args = parser.parse_args()
    tex_bytes, csv_bytes = args.tex.read_bytes(), args.csv.read_bytes()
    try:
        expected = csv_expected(csv_bytes.decode('utf-8'))
        count = verify(tex_bytes.decode('utf-8'), expected)
        rejected = negative_cases(tex_bytes.decode('utf-8'), expected) if args.self_test else []
        require(args.tex.read_bytes() == tex_bytes and args.csv.read_bytes() == csv_bytes,
                'input_changed', 'An input changed during verification')
    except InvalidGrid as error:
        parser.exit(1, 'FAIL: ' + str(error) + '\n')
    print(f'PASS: {count} displayed keys match saved CSV (4 methods × 9 rows × 3 variants).')
    if rejected:
        print('PASS: rejected in-memory negatives: ' + ', '.join(rejected))


if __name__ == '__main__':
    main()
