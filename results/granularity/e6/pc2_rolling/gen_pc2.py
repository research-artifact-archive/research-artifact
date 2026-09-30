#!/usr/bin/env python3
"""Append-only calibration-setting variant. Existing PC2 bytes remain the prefix."""
import hashlib,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
ORIGINAL=ROOT/'Implementation/Experiment/Models/ProductionCell_Arms=2_FG.lts'
EXPECTED='117210fa93185f5a814ad7debbdfcde00720019312c4ef68446a844700084e43'
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    source=ORIGINAL.read_bytes();assert sha(source)==EXPECTED
    text=source.decode();original=re.search(r'PRODUCTION_CELL_NEW\(I=1\) = .*?TRASHED = \(stampOk\[I\] -> ARM\)\.',text,re.S).group()
    block=original.replace('PRODUCTION_CELL_NEW','PRODUCTION_CELL_NEW_CAL')
    lines=block.splitlines();out=[]
    labels=[]
    for line in lines:
        if ' = (' in line:
            label=line.split(' = (')[0];labels.append(label)
            if label.startswith('PRODUCTION_CELL'): dest='CAL_INITIAL'
            else:dest='CAL_'+label.split('[')[0]+('[k]' if '[k:Stages]' in label else '')
            line=line.replace(' = (',' = (beginCalibration[I] -> '+dest+' | ',1)
        out.append(line)
    block='\n'.join(out)[:-1]+',\n'
    block+='CAL_INITIAL = (calibrated[I] -> PRODUCTION_CELL_NEW_CAL),\n'
    block+='CAL_ARM = (calibrated[I] -> ARM),\nCAL_OUT = (calibrated[I] -> OUT),\n'
    for s in ['DRILLED','PAINTED','CLEANED']:block+=f'CAL_{s}[k:Stages] = (calibrated[I] -> {s}[k]),\n'
    block+='CAL_TRASHED = (calibrated[I] -> TRASHED).\n'
    # Independent text erasure: remove only added requests and added CAL state declarations.
    erased=block[:block.index('\nCAL_INITIAL')].rstrip(',')+'.'
    erased=re.sub(r'beginCalibration\[I\] -> CAL_[A-Z]+(?:\[k\])? \| ','',erased).replace('PRODUCTION_CELL_NEW_CAL','PRODUCTION_CELL_NEW')
    assert erased==original
    added='\n\n// E6 PC2 calibration-setting update variant. Original source above is byte-preserved.\n'+block
    added+='\nset CalControllableActions = {NewControllableActions, beginCalibration[Arms]}\n'
    added+='||NEW_CAL_ENV = (forall[i:Arms] PRODUCTION_CELL_NEW_CAL(i)).\n'
    added+='fluent Calibrating[i:Arms] = <beginCalibration[i],calibrated[i]>\n'
    added+='ltl_property P_CAL_AVAILABILITY = [](!Calibrating[1] || !Calibrating[2])\n'
    added+='fluent CalReady1 = <calibrated[1],{reconfigure_PRODUCTION_CELL_1,beginCalibration[1]}> initially 1\n'
    added+='fluent CalReady2 = <calibrated[2],{reconfigure_PRODUCTION_CELL_2,beginCalibration[2]}> initially 1\n'
    added+='ltl_property R_CAL_READY = [](CalReady1 || CalReady2)\n'
    goal=re.search(r'controllerSpec CLEAN_PAINT_DRILL = \{.*?\n\}(?=\ncontroller)' ,text,re.S).group()
    goal=goal.replace('CLEAN_PAINT_DRILL','CLEAN_PAINT_DRILL_CAL').replace('safety = {','safety = {\nP_CAL_AVAILABILITY,').replace('{NewControllableActions}','{CalControllableActions}')
    added+='\n'+goal+'\ncontroller ||C_CLEAN_PAINT_DRILL_CAL = (NEW_CAL_ENV)~{CLEAN_PAINT_DRILL_CAL}.\n'
    for i in [1,2]:
        rel=re.search(r'relation R_PRODUCTION_CELL_'+str(i)+r'_FG = \{.*?\}',text,re.S).group()
        rel=rel.replace(f'R_PRODUCTION_CELL_{i}_FG',f'R_PRODUCTION_CELL_{i}_CAL')
        rel=re.sub(r'-> ([A-Z_]+)(\[k\])?@PRODUCTION_CELL_NEW',lambda m:'-> '+('CAL_INITIAL' if m[1]=='PRODUCTION_CELL_NEW' else 'CAL_'+m[1])+(m[2] or '')+'@PRODUCTION_CELL_NEW_CAL',rel)
        added+='\n'+rel+'\n'
    added+='''
updatingController UpdCont_PC2_CAL = {
oldController = C_DRILL_POLISH_CLEAN,
newController = C_CLEAN_PAINT_DRILL_CAL,
oldEnvironment = {PRODUCTION_CELL_OLD(1), PRODUCTION_CELL_OLD(2)},
newEnvironment = {PRODUCTION_CELL_NEW_CAL(1), PRODUCTION_CELL_NEW_CAL(2)},
mapRelation = {R_PRODUCTION_CELL_1_CAL, R_PRODUCTION_CELL_2_CAL},
oldGoal = DRILL_POLISH_CLEAN,
newGoal = CLEAN_PAINT_DRILL_CAL,
transition = R_CAL_READY,
nonblocking,
revised_on_the_fly,
fine_grained
}
||UPDATE_CONTROLLER_PC2_CAL = UpdCont_PC2_CAL.
||PC2_NEW_ORIGINAL_1 = PRODUCTION_CELL_NEW(1).
||PC2_NEW_CALIBRATION_1 = PRODUCTION_CELL_NEW_CAL(1).
'''
    target=HERE/'v2/inputs/ProductionCell_Arms2_Calibration.lts';target.parent.mkdir(parents=True,exist_ok=True)
    data=source+added.encode()
    with target.open('xb') as f:f.write(data)
    report={'status':'PASS','original_sha256':EXPECTED,'input_sha256':sha(data),'original_prefix_bytes':len(source),'old_new_original_declarations':'byte-preserved prefix','operational_projection_erasure':'exact original NEW process','old_requirements':12,'new_original_requirements':12,'new_added_requirements':['P_CAL_AVAILABILITY'],'interval_requirements':['R_CAL_READY'],'new_states_per_arm':14,'transfer_pairs_per_arm':7,'transfer_projection':'original destinations each wrapped in corresponding CAL state','expected':'fine WIN / transfers LOSS; unmeasured expectation only','observer_note':'new endpoint Calibrating observes ordinary begin/calibrated; interval CalReady additionally observes transfer actions. Transfer retains ordinary observer history; endpoint compatibility is checked by E1.'}
    p=HERE/'v2/validation/source_projection.json';p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
