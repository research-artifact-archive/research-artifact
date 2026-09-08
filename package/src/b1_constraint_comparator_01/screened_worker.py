from pathlib import Path
import json,sys,time,traceback
start=time.perf_counter()
try:
    import screened_dp
    case=json.loads(Path(sys.argv[1]).read_text())['case'];row=screened_dp.solve(case)
except AssertionError:row=dict(status='FAILURE',error=traceback.format_exc())
except Exception:row=dict(status='INVALID',error=traceback.format_exc())
row['worker_seconds']=time.perf_counter()-start
with (Path(sys.argv[2])/'RESULT.json').open('x') as f:json.dump(row,f,sort_keys=True);f.write('\n')
