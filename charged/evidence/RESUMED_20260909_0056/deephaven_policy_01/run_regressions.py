from pathlib import Path
import datetime
import hashlib
import json
import os
import shutil
import signal
import subprocess
import time
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / 'deephaven_source_01'
CHECKOUT = next((SOURCE / 'checkout').iterdir())
output = HERE / 'regressions01'
output.mkdir(exist_ok=False)
plan = json.loads((SOURCE / 'baseline_02/PLAN.json').read_text())
plan.update(started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            timeout_seconds=180, purpose='Four unchanged upstream regression tests after opt-in policy integration',
            predecessor='deephaven_policy_01/attempt01', change='Source bytes now include optional policy hooks')
plan['source_files'] = []
for name in ('ConstructSnapshot.java', 'RetryStudyHooks.java', 'HierarchicalTableImpl.java'):
    path = HERE / name
    plan['source_files'].append({'name': name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
(output / 'PLAN.json').write_text(json.dumps(plan, indent=2) + '\n')
started = time.time()
with (output / 'BUILD.log').open('xb') as log:
    process = subprocess.Popen(plan['argv'], cwd=CHECKOUT, stdout=log, stderr=subprocess.STDOUT,
                               start_new_session=True)
    (output / 'PROCESS.json').write_text(json.dumps({'pid': process.pid, 'pgid': process.pid}) + '\n')
    try:
        code = process.wait(timeout=180)
        status = 'SUCCESS' if code == 0 else 'FAILURE'
    except subprocess.TimeoutExpired:
        status = 'TIMEOUT'
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
        code = process.returncode
tests = []
for task, name in (('test', 'remote.TestConstructSnapshot'), ('testOutOfBand', 'TestTreeTable')):
    xml = CHECKOUT / f'engine/table/build/test-results/{task}/TEST-io.deephaven.engine.table.impl.{name}.xml'
    if xml.exists() and xml.stat().st_mtime >= started:
        shutil.copyfile(xml, output / (task + '.xml'))
        root = ET.parse(xml).getroot()
        tests.append({'task': task, 'sha256': hashlib.sha256(xml.read_bytes()).hexdigest(),
                      'attributes': root.attrib,
                      'cases': [{'name': t.get('name'), 'failure': t.find('failure') is not None,
                                 'error': t.find('error') is not None, 'skipped': t.find('skipped') is not None}
                                for t in root.findall('testcase')]})
receipt = {'status': status, 'exit_code': code, 'denominator': 4, 'xml': tests,
           'ended_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'elapsed_seconds': time.time() - started}
(output / 'RESULT.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt, indent=2))
