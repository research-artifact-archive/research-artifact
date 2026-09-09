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

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / 'deephaven_source_01'
CHECKOUT = next((SOURCE / 'checkout').iterdir())


def run(class_name, directory, prefix, denominator, reason):
    output = HERE / directory
    output.mkdir(exist_ok=False)
    snapshot = output / 'sources'
    snapshot.mkdir()
    java_file = HERE / (class_name + '.java')
    shutil.copyfile(java_file, CHECKOUT / 'engine/table/src/test/java/io/deephaven/engine/table/impl' / java_file.name)
    for path in HERE.iterdir():
        if path.is_file():
            shutil.copyfile(path, snapshot / path.name)
    previous = json.loads((SOURCE / 'baseline_02/PLAN.json').read_text())
    argv = previous['argv'][:previous['argv'].index(':engine-table:test')] + [
        ':engine-table:testOutOfBand', '--tests', 'io.deephaven.engine.table.impl.' + class_name]
    started = time.time()
    receipt = {'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'argv': argv, 'cwd': str(CHECKOUT), 'class': class_name, 'denominator': int(denominator),
               'timeout_seconds': 180, 'reason': reason,
               'source_files': [{'name': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
                                for path in sorted(snapshot.iterdir())]}
    for relative in ('engine/table/src/main/java/io/deephaven/engine/table/impl/remote/ConstructSnapshot.java',
                     'engine/table/src/main/java/io/deephaven/engine/table/impl/remote/RetryStudyHooks.java',
                     'engine/table/src/main/java/io/deephaven/engine/table/impl/hierarchical/HierarchicalTableImpl.java'):
        receipt['source_files'].append({'checkout_path': relative,
            'sha256': hashlib.sha256((CHECKOUT / relative).read_bytes()).hexdigest()})
    (output / 'MANIFEST.json').write_text(json.dumps(receipt, indent=2) + '\n')
    with (output / 'BUILD.log').open('xb') as log:
        process = subprocess.Popen(argv, cwd=CHECKOUT, stdout=log, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        (output / 'PROCESS.json').write_text(json.dumps({'pid': process.pid, 'pgid': process.pid}) + '\n')
        try:
            code = process.wait(timeout=180)
            receipt.update(exit_code=code, status='SUCCESS' if code == 0 else 'FAILURE')
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            receipt['status'] = 'TIMEOUT'
    xml = CHECKOUT / ('engine/table/build/test-results/testOutOfBand/TEST-io.deephaven.engine.table.impl.'
                      + class_name + '.xml')
    rows = []
    if xml.exists() and xml.stat().st_mtime >= started:
        shutil.copyfile(xml, output / 'TEST.xml')
        root = ET.parse(xml).getroot()
        receipt['fresh_test_result'] = {key: root.get(key) for key in ('tests', 'failures', 'errors', 'skipped')}
        for line in (root.findtext('system-out') or '').splitlines():
            if line.startswith(prefix + ' '):
                rows.append(json.loads(line[len(prefix) + 1:]))
    raw = output / 'RAW.jsonl'
    raw.write_text(''.join(json.dumps(row, separators=(',', ':')) + '\n' for row in rows))
    receipt.update(observed_rows=len(rows), raw_sha256=hashlib.sha256(raw.read_bytes()).hexdigest(),
                   ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    (output / 'RESULT.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({key: receipt[key] for key in
        ('status', 'observed_rows', 'started_utc', 'ended_utc')}, indent=2))


if __name__ == '__main__':
    run(*sys.argv[1:])
