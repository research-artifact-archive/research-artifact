#!/usr/bin/env python3
"""Build a private delta package without modifying either source tree or JAR."""
from pathlib import Path
import csv,difflib,hashlib,json,re,shutil,subprocess,sys
HERE=Path(__file__).resolve().parent
SUB=HERE.parents[1]
XEON=HERE.parent/'rq3_xeon'
PUBLIC=HERE.parent/'mtsa/maven-root/mtsa'
DELTA=HERE/'bundle_delta'
PUBLIC_HASH='4ab198ba14c9f0f829c36808025aefc063e2a3a0836679490179cc407e6133e5'
FORK_HASH='fbdc25f58d5441ed906d408a94b7414c9d9c3ed35e2ebce22d9751729967ba07'
NAMES=['GSM','Industry','MetaSocket','PowerPlant','ProductionCell','Railcab','Surveillance','Workflow']
EMPTY={'GSM':'T_NO_TP','Industry':'T_Empty','ProductionCell':'T_NO_TP','Railcab':'T_NO_TP','Surveillance':'T_NO_TP','Workflow':'NO_TP'}
META=['UPD64_128','UPD64_64COM','UPD128_64','UPD128_128COM','UPD64COM_64','UPD64COM_128COM','UPD128COM_128','UPD128COM_64COM']
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
def write_csv(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def diff(a,b,old,new):return ''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile=old,tofile=new))
def transform(text,name,condition,fork=False):
    changes=0
    if condition=='empty':
        wanted=EMPTY[name]; lines=text.splitlines(True); enabled=0
        for i,line in enumerate(lines):
            # Only the single designated transition assignment is uncommented.
            if re.match(r'^\s*//\s*transition\s*=\s*'+re.escape(wanted)+r'\s*,?\s*(?:\r?\n)?$',line):
                lines[i]=re.sub(r'^(\s*)//',r'\1',line);enabled+=1;changes+=1
            elif re.match(r'^\s*transition\s*=',line):
                lines[i]=re.sub(r'^(\s*)',r'\1//',line,count=1);changes+=1
        assert enabled==1,(name,enabled)
        text=''.join(lines)
    fluent_changes=0
    if fork:
        lines=text.splitlines(True)
        for i,line in enumerate(lines):
            if re.match(r'^\s*fluent\s+',line) and 'beginUpdate' in line:
                lines[i]=line.replace('beginUpdate','hotSwapIn');fluent_changes+=1
        assert fluent_changes==3,(name,fluent_changes)
        text=''.join(lines)
    return text,changes,fluent_changes

def main():
    source=PUBLIC/'target/classes/UnpackagedExamples/Update-TSEcaseStudies'
    rows=[];conditions=[]
    for name in NAMES:
        original=(source/f'2017-TSE-{name}.lts').read_bytes().decode('utf-8')
        for condition in ['supplied']+(['empty'] if name in EMPTY else []):
            targets=META if name=='MetaSocket' else ['UPDATE_CONTROLLER']
            for tool in ['published','fork']:
                changed,nc,nf=transform(original,name,condition,tool=='fork')
                path=DELTA/'legacy-fidelity/inputs'/tool/f'{name}_{condition}.lts';path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(changed.encode('utf-8'))
                path.with_suffix('.diff').write_text(diff(original,changed,f'2017-TSE-{name}.lts',path.name))
                for target in targets:
                    conditions.append(dict(model=name.lower()+'_'+condition+('' if name!='MetaSocket' else '_'+target.lower()),source_model=name,condition=condition,target=target,tool=tool,path=path.relative_to(DELTA).as_posix()))
                rows.append(dict(model=name,condition=condition,tool=tool,targets=';'.join(targets),transition_assignment_lines_changed=nc,fluent_reset_lines_changed=nf,source_sha256=hashlib.sha256(original.encode()).hexdigest(),generated_sha256=digest(path),input_path=path.relative_to(DELTA).as_posix(),missing_reason=''))
        if name not in EMPTY:
            for tool in ['published','fork']:
                rows.append(dict(model=name,condition='empty',tool=tool,targets='',transition_assignment_lines_changed=0,fluent_reset_lines_changed=0,source_sha256=hashlib.sha256(original.encode()).hexdigest(),generated_sha256='',input_path='',missing_reason='No T_NO_TP / T_Empty / NO_TP definition; no model invented'))
    write_csv(HERE/'inputs.csv',rows);write_csv(DELTA/'legacy-fidelity/inputs.csv',rows)
    base=json.loads((XEON/'configs/rq3.json').read_text())
    methods=[dict(id='legacy_ducs',target_template='{suffix}',analysis_role='fork_legacy_on_original_monolithic_input',jvm_properties={'mtsa.evaluation.enabled':'true'}),dict(id='published_mtsa',target_template='{suffix}',analysis_role='lab_maintained_original_ducs_reference',jvm_properties={})]
    for tool in ['published','fork']:
        cfg=dict(base);cfg.update(experiment_id='legacy-fidelity-'+tool,backend='published_mtsa' if tool=='published' else 'lts',reference_campaign=True,methods=methods,
            classpath='legacy-fidelity/lib/original-mtsa-1.0-SNAPSHOT.jar' if tool=='published' else base['classpath'],
            main_class='fidelity.PublishedMtsaRunner' if tool=='published' else base['main_class'],
            required_classpath_sha256=PUBLIC_HASH if tool=='published' else FORK_HASH)
        if tool=='published':cfg.update(runner_classpath='legacy-fidelity/cli/published-mtsa-runner.jar')
        targets=sorted(set(c['target'] for c in conditions));cfg['targets']=[dict(id=t.lower(),suffix=t) for t in targets]
        cfg['models']=[dict(id=c['model'],path=c['path'],target_ids=[c['target'].lower()],method_ids=['published_mtsa' if tool=='published' else 'legacy_ducs'],family=c['source_model'],factors={'condition':c['condition']}) for c in conditions if c['tool']==tool]
        out=DELTA/'configs'/f'legacy_fidelity_{tool}.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(cfg,indent=2)+'\n')
    jar=PUBLIC/'target/mtsa-1.0-SNAPSHOT.jar';assert digest(jar)==PUBLIC_HASH
    destination=DELTA/'legacy-fidelity/lib/original-mtsa-1.0-SNAPSHOT.jar';destination.parent.mkdir(parents=True,exist_ok=True)
    if not destination.exists():shutil.copyfile(jar,destination)
    assert digest(destination)==PUBLIC_HASH
    cli=DELTA/'legacy-fidelity/cli';cli.mkdir(parents=True,exist_ok=True);shutil.copyfile(HERE/'cli/PublishedMtsaRunner.java',cli/'PublishedMtsaRunner.java')
    java_home=subprocess.check_output(['/usr/libexec/java_home','-v','17'],text=True).strip()
    classes=HERE/'build/classes';classes.mkdir(parents=True,exist_ok=True)
    if '--reuse-adapter' not in sys.argv:
        subprocess.run([java_home+'/bin/javac','--release','17','-cp',str(jar),'-d',str(classes),str(HERE/'cli/PublishedMtsaRunner.java')],check=True)
        subprocess.run([java_home+'/bin/jar','--create','--file',str(cli/'published-mtsa-runner.jar'),'-C',str(classes),'.'],check=True)
    cfgpath=DELTA/'configs/legacy_fidelity_published.json';cfg=json.loads(cfgpath.read_text());cfg['required_runner_sha256']=digest(cli/'published-mtsa-runner.jar');cfgpath.write_text(json.dumps(cfg,indent=2)+'\n')
    print('Generated 21 conditions per tool; 42 first trials, maximum 210 trials. Originals untouched.')
if __name__=='__main__':main()
