#!/usr/bin/env python3
"""Read-only source-domain audit; no solver calls or model alterations."""
from pathlib import Path
import csv
import hashlib
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def relation_domain(text, name):
    match = re.search(r"relation\s+" + re.escape(name) + r"\s*=\s*\{(.*?)\}", text, re.S)
    if not match:
        raise ValueError(name)
    # PC1 fixes K=1, so its only indexed local state has index 1.
    return {x.replace('[k]', '[1]') for x in re.findall(r"([A-Z][A-Z_0-9]*(?:\[k\])?)@[^=,\n]+\s*=", match[1])}


def main():
    definitions = [
        ('PC1', 'ProductionCell_Arms=1_FG.lts', 'R_PRODUCTION_CELL_1_FG',
         {'PRODUCTION_CELL_OLD', 'ARM', 'OUT', 'TRASHED', 'DRILLED[1]', 'POLISHED[1]', 'CLEANED[1]'},
         'one replaced component; transfer merging only renames its event'),
        ('Railcab', 'Railcab_FG.lts', 'R_MILESTONES_FG',
         {'MILESTONES_OLD', 'ENDOFTS', 'LB', 'LEB', 'NR'}, 'total local domain'),
        ('Railcab', 'Railcab_FG.lts', 'R_REQUEST_ATOMIC_FG',
         {'REQUEST_ATOMIC_OLD', 'RESPONSE'}, 'total local domain'),
        ('Railcab', 'Railcab_FG.lts', 'R_TURNS_FG',
         {'TURNS_OLD', 'TURNS2'}, 'total local domain'),
        ('Railcab', 'Railcab_FG.lts', 'R_ANOTHER_REQUEST_FG',
         {'ANOTHER_REQUEST_OLD'}, 'total local domain'),
    ]
    rows = []
    for model, filename, relation, states, reason in definitions:
        path = ROOT / 'Implementation/Experiment/Models' / filename
        payload = path.read_bytes()
        text = payload.decode()
        if model == 'PC1':
            assert re.search(r'const N = 1\b', text)
            assert re.search(r'const K = 1\b', text)
        domain = relation_domain(text, relation)
        assert states == domain, (relation, states, domain)
        rows.append(dict(model=model, relation=relation, source_path=path.relative_to(ROOT).as_posix(),
                         source_sha256=hashlib.sha256(payload).hexdigest(),
                         source_local_states=';'.join(sorted(states)),
                         transfer_domain=';'.join(sorted(domain)),
                         local_state_count=len(states), domain_count=len(domain),
                         coverage='TOTAL_SOURCE_DOMAIN', evidence_type='SOURCE_INSPECTION_NOT_SOLVER_RESULT',
                         note=reason))
    with (HERE / 'relation_domains.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print('PASS:', len(rows), 'source relations cover every listed local state; no solver invoked')


if __name__ == '__main__':
    main()
