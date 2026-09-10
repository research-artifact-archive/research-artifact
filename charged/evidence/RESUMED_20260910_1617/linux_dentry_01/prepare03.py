from pathlib import Path
import shutil,hashlib,json,datetime,difflib
D=Path(__file__).resolve().parent
shutil.copyfile(D/'INPUTS02.json',D/'INPUTS03.json')
shutil.copytree(D/'implementation02',D/'implementation03')
f=D/'implementation03/d_path_retry_test.c';s=f.read_text();before=s
def rep(a,b):
 global s
 assert s.count(a)==1,a[:90]
 s=s.replace(a,b)
rep('\tunsigned int i, writes, before_writes, total_writes, expected_len = 0;', '\tunsigned int i, writes, before_writes, total_writes, expected_len = 0;\n\tunsigned int global_begin, global_end, global_writes;\n\tbool global_ok;')
rep('\tbefore_writes = READ_ONCE(c->writes);\n\tswitch (input->policy)', '\tbefore_writes = READ_ONCE(c->writes);\n\tglobal_begin = read_seqbegin(&rename_lock);\n\tswitch (input->policy)')
rep('\tWRITE_ONCE(c->enabled, false);\n\twrites = READ_ONCE(c->writes) - before_writes;', '\t/* Attribution probes are outside every policy resource counter. */\n\tsmp_mb();\n\tglobal_end = read_seqbegin(&rename_lock);\n\tWRITE_ONCE(c->enabled, false);\n\twrites = READ_ONCE(c->writes) - before_writes;\n\tglobal_writes = (global_end - global_begin) / 2;\n\tglobal_ok = !(global_begin & 1) && !(global_end & 1) &&\n\t\tglobal_end >= global_begin && global_writes == writes;')
rep('\thealthy = !READ_ONCE(c->error) && reference_ok && canary && persistent;', '\thealthy = !READ_ONCE(c->error) && reference_ok && canary && persistent && global_ok;')
needle='\tKUNIT_EXPECT_TRUE_MSG(test, healthy, "row %u environment/oracle", input->id);'
rep(needle,r'''	pr_info("DPGLOBAL {\"id\":%u,\"begin\":%u,\"end\":%u,"
		"\"global_writes\":%u,\"designated_writes\":%u,\"valid\":%u}\n",
		input->id, global_begin, global_end, global_writes, writes, global_ok);
'''.replace('\\t','\t')+needle)
f.write_text(s)
(D/'implementation03/attribution.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),s.splitlines(True),fromfile='implementation02/d_path_retry_test.c',tofile='implementation03/d_path_retry_test.c')))
r=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),inputs_identical_02_03=(D/'INPUTS03.json').read_bytes()==(D/'INPUTS02.json').read_bytes(),files=[dict(path=str(p.relative_to(D)),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in [D/'INPUTS03.json',D/'PROTOCOL03.md']+sorted((D/'implementation03').iterdir())])
with(D/'PREPARATION03.json').open('x') as out:json.dump(r,out,indent=2);out.write('\n')
print(json.dumps(dict(inputs=r['inputs_identical_02_03'],changed_source='d_path_retry_test.c',files=len(r['files']))))
