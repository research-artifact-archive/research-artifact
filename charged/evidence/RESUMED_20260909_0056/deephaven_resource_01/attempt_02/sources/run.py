from pathlib import Path
import datetime
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / 'deephaven_source_01'
CHECKOUT = next((SOURCE / 'checkout').iterdir())


def run(name, reason):
    output = ROOT / name
    output.mkdir(exist_ok=False)
    test = CHECKOUT / 'engine/table/src/test/java/io/deephaven/engine/table/impl/TestRetryResourceStudy.java'
    shutil.copyfile(ROOT / 'TestRetryResourceStudy.java', test)
    snapshot = output / 'sources'
    snapshot.mkdir()
    files = []
    for path in sorted(ROOT.iterdir()):
        if path.is_file():
            shutil.copyfile(path, snapshot / path.name)
            files.append({'name': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    plan = json.loads((ROOT / 'attempt_01/MANIFEST.json').read_text())
    started = time.time()
    receipt = {**plan, 'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'change_reason': reason, 'files': files}
    (output / 'MANIFEST.json').write_text(json.dumps(receipt, indent=2) + '\n')
    with (output / 'BUILD.log').open('xb') as log:
        process = subprocess.Popen(plan['argv'], cwd=CHECKOUT, stdout=log, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        (output / 'PROCESS.json').write_text(json.dumps({'pid': process.pid, 'pgid': process.pid,
            'started_utc': receipt['started_utc']}) + '\n')
        try:
            code = process.wait(timeout=600)
            receipt.update(exit_code=code, status='SUCCESS' if code == 0 else 'FAILURE')
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            receipt['status'] = 'TIMEOUT'
    xml_dir = output / 'xml'
    xml_dir.mkdir()
    rows = []
    suites = []
    for path in sorted((CHECKOUT / 'engine/table/build/test-results').glob('*/TEST-*.xml')):
        if not any(x in path.name for x in ('TestRetryResourceStudy', 'TestTreeTable', 'TestConstructSnapshot')):
            continue
        if path.stat().st_mtime < started:
            continue
        destination = xml_dir / (path.parent.name + '-' + path.name)
        shutil.copyfile(path, destination)
        tree = ET.parse(path).getroot()
        suites.append({'name': tree.get('name'), 'tests': tree.get('tests'),
                       'failures': tree.get('failures'), 'errors': tree.get('errors'),
                       'skipped': tree.get('skipped'),
                       'sha256': hashlib.sha256(destination.read_bytes()).hexdigest()})
        if 'TestRetryResourceStudy' in path.name:
            for line in (tree.findtext('system-out') or '').splitlines():
                if line.startswith('RETRY_STUDY '):
                    rows.append(json.loads(line[len('RETRY_STUDY '):]))
    raw = output / 'RAW.jsonl'
    raw.write_text(''.join(json.dumps(row, separators=(',', ':')) + '\n' for row in rows))
    receipt.update(observed_scientific_rows=len(rows), fresh_suites=suites,
                   raw_sha256=hashlib.sha256(raw.read_bytes()).hexdigest(),
                   ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    (output / 'RESULT.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({key: receipt[key] for key in
        ('status', 'observed_scientific_rows', 'fresh_suites', 'started_utc', 'ended_utc')}, indent=2))


if __name__ == '__main__':
    run(sys.argv[1], sys.argv[2])
