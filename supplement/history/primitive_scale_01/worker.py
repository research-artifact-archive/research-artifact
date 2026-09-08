import hashlib,importlib.util,json,os,re,resource,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
PARENT=HERE.parent
GRAPH=PARENT/'guaranteed_guards_01/explore.py'
CODEC=PARENT/'prism_guard_compact_01/codec.py'
COMP=HERE.parents[1]/'quantitative_progress/adaptive_retry_control/compiler.py'
PRISM=HERE.parents[1]/'quantitative_progress/external_tools/prism-games-3.2.4-mac64-arm/bin/prism'
ENV=dict(PRISM_JAVA='/opt/homebrew/opt/openjdk@17/bin/java',PRISM_JAVA_PARAMS='-XX:ActiveProcessorCount=1')
def module(p,name):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def model_text(jobs,B,objects_first=False):
    text=module(CODEC,'compact_codec').export(jobs,B)
    if objects_first:
        header,body=text.split('module protocol\n',1);declarations,separator,commands=body.partition(' [c]')
        lines=declarations.splitlines();assert len(lines)==4+2*len(jobs)
        text=header+'module protocol\n'+'\n'.join(lines[4:]+lines[:4])+'\n'+separator+commands
    return text

def main():
    method,source,dest=sys.argv[1:];start=time.perf_counter();case=json.loads(Path(source).read_text());out=Path(dest)
    jobs=case['jobs'];B=case['budget'];row=dict(method=method,status='SUCCESS')
    try:
        if method=='packed':
            compiler=module(COMP,'packed_compiler');g=dict(jobs=[[p,w] for w,p in jobs],budget=B,normal_costs=[w for w,p in jobs])
            ctrl=compiler.compile_controller(g);data=compiler.canonical(ctrl);(out/'controller.json').write_bytes(data)
            row.update(value=ctrl['value'],controller_bytes=len(data),thresholds=len(ctrl['protect_at_budget']),slope_runs=len(ctrl['value_slopes']))
        elif method=='full_andor':
            graph=module(GRAPH,'original_graph');g=graph.graph(jobs,B);value,policy=graph.reuse.solve(g)
            row.update(value=value[((graph.U,)*len(jobs),B)],normal_graph_states=len(g[0]),macro_actions=len(g[1]),policy_states=len(policy))
        else:
            text=model_text(jobs,B,method=='prism_mtbdd_objects');model=out/'model.prism';model.write_text(text)
            explicit=method=='prism_explicit_phase';engine='explicit' if explicit else 'mtbdd'
            argv=[str(PRISM),str(model),'-pf','<<controller>> R{"work"}min=? [ F "goal" ]','-'+engine,
                  '-epsilon','1e-10','-maxiters','100000','-javamaxmem','512m','-cuddmaxmem','256m']
            (out/'PRISM_COMMAND.json').write_text(json.dumps(dict(argv=argv,env_overrides=ENV),indent=2)+'\n')
            env=dict(os.environ);env.update(ENV)
            with (out/'prism_stdout.txt').open('xb') as so,(out/'prism_stderr.txt').open('xb') as se:result=subprocess.run(argv,stdout=so,stderr=se,env=env)
            log=(out/'prism_stdout.txt').read_text(errors='replace');hits=re.findall(r'^Result:\s+(\S+)',log,re.M)
            row.update(prism_exit_code=result.returncode,model_bytes=model.stat().st_size,model_sha256=hashlib.sha256(model.read_bytes()).hexdigest(),
                actual_engine='symbolic' if 'Building model (engine:symbolic)' in log else ('explicit' if 'Building model (engine:explicit)' in log else None))
            if result.returncode or not hits:row.update(status='INVALID',reason='tool_result_or_process_error')
            else:
                row['value']=float(hits[-1])
                if row['actual_engine']!=('explicit' if explicit else 'symbolic'):row.update(status='INVALID',reason='engine_fallback_or_unknown')
            for key,pattern in [('native_states',r'^States:\s+(\d+)'),('native_transitions',r'^Transitions:\s+(\d+)')]:
                found=re.search(pattern,log,re.M)
                if found:row[key]=int(found.group(1))
    except Exception as e:row.update(status='INVALID',error=repr(e))
    row.update(worker_seconds=time.perf_counter()-start,worker_peak_rss_native=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
               worker_peak_rss_units='bytes' if sys.platform=='darwin' else 'KiB')
    (out/'RESULT.json').write_text(json.dumps(row,sort_keys=True)+'\n');print(json.dumps(row,sort_keys=True))
if __name__=='__main__':main()
