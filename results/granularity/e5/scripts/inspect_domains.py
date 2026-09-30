#!/usr/bin/env python3
"""Independent source-level relation audit; no compiler or synthesis invocation.

Physical state inventories are read from the copied old-process declarations, with
aliases resolved and indexed declarations expanded. Relation pairs are independently
parsed below. Compiled augmented-state metrics are never inferred from these counts.
"""
import sys
sys.dont_write_bytecode=True
from e5_common import *
# (relation, initial physical state label, old-process local state inventory).
SPECS={
'gsm':[('R_ENV_FG','SENDER','SENDER X Y Z ENCODED SENT RECEIVED DECODED')],
'industry':[('R_TOR_FG','TOR_OLD','TOR_OLD RECEIVED RESPONSE TOROK0 TOROK1'),('R_DSD1_FG','DSD1_OLD','DSD1_OLD RECEIVED DSD1RESPONSE DSD1OK0 DSD1OK1 QARESPONSE QAOK0 QAOK1'),('R_GATEFORM1_FG','GATEFORM1_OLD','GATEFORM1_OLD RECEIVED GF1RESPONSE')],
'metasocket':[('R_IO_FG','IO_OLD','IO_OLD PROCESS'),('R_64_128_FG','DES64','DES64')],
'powerplant':[('R_MAINTENANCE_FG','MAINTENANCE_OLD','MAINTENANCE_OLD REQUESTED'),('R_ENV_FG','STARTED','STARTED STOPPED')],
'productioncell_arms1':[('R_PRODUCTION_CELL_1_FG','PRODUCTION_CELL_OLD','PRODUCTION_CELL_OLD ARM OUT TRASHED DRILLED[1] POLISHED[1] CLEANED[1]')],
'productioncell_arms2':[('R_PRODUCTION_CELL_1_FG','PRODUCTION_CELL_OLD','PRODUCTION_CELL_OLD ARM OUT TRASHED DRILLED[1] POLISHED[1] CLEANED[1]'),('R_PRODUCTION_CELL_2_FG','PRODUCTION_CELL_OLD','PRODUCTION_CELL_OLD ARM OUT TRASHED DRILLED[1] POLISHED[1] CLEANED[1]')],
'railcab':[('R_MILESTONES_FG','MILESTONES_OLD','MILESTONES_OLD ENDOFTS LB LEB NR'),('R_REQUEST_ATOMIC_FG','REQUEST_ATOMIC_OLD','REQUEST_ATOMIC_OLD RESPONSE'),('R_TURNS_FG','TURNS_OLD','TURNS_OLD TURNS2'),('R_ANOTHER_REQUEST_FG','ANOTHER_REQUEST_OLD','ANOTHER_REQUEST_OLD')],
'surveillance':[('R_MISSION_FG','MISSION','MISSION HEIGHT UAV TAKING_PICTURE SCANING'),('R_BATTERY_COUNTER_FG','BAT[10]',' '.join(f'BAT[{i}]' for i in range(11)))],
'workflow':[('R_ENTRY_FG','ENTRY_OLD','ENTRY_OLD PROCESSING1 EVAL_RESPONSE PROCESSING2')]+[(f'R_{name}_FG',f'{name}_OLD',f'{name}_OLD AT_{name}') for name in ('INVENTORY','CREDIT','SHIPPING','BILLING')]
}

def parse_pairs(body,constants):
    result=set()
    for item in body.split(','):
        item=item.strip();items=[item]
        if item.startswith('forall'):
            m=re.fullmatch(r'forall\s*\[(\w+):(\d+)\.\.(\w+)\]\s*(.*)',item,re.S);assert m,item
            v,lo,hi,tail=m.groups();hi=int(hi) if hi.isdigit() else constants[hi]
            items=[tail.replace('['+v+']','['+str(i)+']') for i in range(int(lo),hi+1)]
        for entry in items:
            m=re.fullmatch(r'([\w\[\]]+)@([\w()]+)\s*=\s*([\w]+)\s*->\s*([\w\[\]]+)@([\w()]+)',entry,re.S);assert m,entry
            old,oldproc,action,new,newproc=m.groups();result.add((old,new,oldproc,newproc,action))
    return sorted(result)

def main():
    rows=[]
    for inp in read_json(E5/'inputs/input_manifest.json'):
        source=ROOT/inp['source_path'];copy=ROOT/inp['copy_path'];assert sha256(source)==sha256(copy)==inp['source_sha256']
        text=re.sub(r'/\*.*?\*/','',copy.read_text(),flags=re.S);text=re.sub(r'//[^\n]*','',text)
        constants={k:int(v) for k,v in re.findall(r'\bconst\s+(\w+)\s*=\s*(\d+)',text)}
        for index,(relation,initial,inventory) in enumerate(SPECS[inp['model_id']]):
            m=re.search(r'\brelation\s+'+relation+r'\s*=\s*\{([^}]+)\}',text,re.S);assert m,relation
            pairs=parse_pairs(m.group(1),constants);domain={p[0] for p in pairs};states=set(inventory.split())
            # Inventory is explicit for the frozen source, not a reachability estimate.
            assert domain<=states,(relation,domain-states)
            for state in states:
                assert re.search(r'\b'+re.escape(state.split('[')[0])+r'\b',text),state
            retained=[p for p in pairs if p[0]==initial]
            rows.append(dict(model_id=inp['model_id'],component_index=index,relation=relation,old_initial_label=initial,source_old_physical_states=len(states),source_original_physical_domain_states=len(domain),source_original_physical_pairs=len(pairs),source_retained_physical_domain_states=int(bool(retained)),source_retained_physical_pairs=len(retained),source_domain_total=domain==states,source_relation_functional=len(pairs)==len(domain),old_state_labels=';'.join(sorted(states)),relation_pairs=json.dumps(pairs),source_path=inp['source_path'],input_sha256=inp['source_sha256']))
    csv_write(E5/'tables/source_domains.csv',rows)
    summary=dict(components=len(rows),physical_old_states=sum(r['source_old_physical_states'] for r in rows),original_physical_pairs=sum(r['source_original_physical_pairs'] for r in rows),retained_physical_pairs=sum(r['source_retained_physical_pairs'] for r in rows),all_source_domains_total=all(r['source_domain_total'] for r in rows),nonfunctional_relations=[r['model_id']+'/'+r['relation'] for r in rows if not r['source_relation_functional']],scope='Source-level old-process inventory and parsed relation pairs. Does not prove Post safety, uncontrollable progress, winningness, or quiescence. Actual augmented counts come only from compiled metrics.')
    write_json(E5/'tables/source_domain_summary.json',summary);print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
