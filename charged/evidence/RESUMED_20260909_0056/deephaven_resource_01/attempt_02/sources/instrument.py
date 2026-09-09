from pathlib import Path
import difflib
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
CHECKOUT = next((HERE.parent / 'deephaven_source_01/checkout').iterdir())
BASE = Path('engine/table/src/main/java/io/deephaven/engine/table/impl')
HOOK = 'io.deephaven.engine.table.impl.remote.RetryStudyHooks'


def change_once(text, old, new):
    assert text.count(old) == 1, (old[:90], text.count(old))
    return text.replace(old, new)


def instrument():
    originals = HERE / 'originals'
    originals.mkdir(exist_ok=False)
    receipts = []
    for rel in (BASE / 'remote/ConstructSnapshot.java', BASE / 'hierarchical/HierarchicalTableImpl.java'):
        source = CHECKOUT / rel
        old = source.read_text()
        before = originals / source.name
        before.write_bytes(source.read_bytes())
        text = old
        if source.name == 'ConstructSnapshot.java':
            text = change_once(text,
                '        return callDataSnapshotFunction((final LogOutput logOutput) -> logOutput.append(logPrefix), control, function);',
                '        try (final RetryStudyHooks.Scope studyScope = RetryStudyHooks.scope(logPrefix, control)) {\n'
                '            return callDataSnapshotFunction((final LogOutput logOutput) -> logOutput.append(logPrefix), control, function);\n'
                '        }')
            text = change_once(text,
                '                    functionSuccessful = function.call(usePrev, beforeClockValue);',
                '                    functionSuccessful = RetryStudyHooks.call(control, function, usePrev, beforeClockValue, false);')
            text = change_once(text,
                '                functionSuccessful = function.call(false, beforeClockValue);',
                '                functionSuccessful = RetryStudyHooks.call(control, function, false, beforeClockValue, true);')
            text = change_once(text,
                '                attemptDurationMillis = System.currentTimeMillis() - attemptStart;',
                '                RetryStudyHooks.outcome(control, beforeClockValue, afterClockValue, usePrev, functionSuccessful, snapshotSuccessful);\n'
                '                attemptDurationMillis = System.currentTimeMillis() - attemptStart;')
        else:
            text = change_once(text,
                '        final KeyTableDirective newDirectiveForKey = new KeyTableDirective(nodeKey, visitAction, expandToDepth);',
                f'        {HOOK}.work("K_DIR", 1);\n'
                '        final KeyTableDirective newDirectiveForKey = new KeyTableDirective(nodeKey, visitAction, expandToDepth);')
            text = change_once(text,
                '        public LinkedDirective newValue(@Nullable final Object nodeKey) {\n',
                '        public LinkedDirective newValue(@Nullable final Object nodeKey) {\n'
                f'            {HOOK}.work("V_LINK", 1);\n')
            text = change_once(text,
                '                final Boolean parentNodeKeyFound =\n',
                f'                {HOOK}.work("V_PARENT", 1);\n'
                '                final Boolean parentNodeKeyFound =\n')
            text = change_once(text,
                '        removed.getChildren().forEach((final LinkedDirective childDirective) -> {\n',
                '        removed.getChildren().forEach((final LinkedDirective childDirective) -> {\n'
                f'            {HOOK}.work("V_UNLINK", 1);\n')
            text = change_once(text,
                '            @Nullable final List<LinkedDirective> childDirectives) {\n        try {\n',
                '            @Nullable final List<LinkedDirective> childDirectives) {\n'
                f'        {HOOK}.work("V_NODE", 1);\n        try {{\n')
            text = change_once(text,
                '                        if (snapshotState.usePrev()) {\n                            chunkSource.fillPrevChunk',
                f'                        {HOOK}.work("V_CELL", chunkRowsSize);\n'
                '                        if (snapshotState.usePrev()) {\n                            chunkSource.fillPrevChunk')
        output = HERE / source.name
        output.write_text(text)
        diff = ''.join(difflib.unified_diff(old.splitlines(True), text.splitlines(True),
            fromfile='pinned/' + str(rel), tofile='instrumented/' + str(rel)))
        (HERE / (source.name + '.patch')).write_text(diff)
        source.write_text(text)
        receipts.append({'path': str(rel), 'before_sha256': hashlib.sha256(before.read_bytes()).hexdigest(),
            'after_sha256': hashlib.sha256(output.read_bytes()).hexdigest()})
    target = CHECKOUT / BASE / 'remote/RetryStudyHooks.java'
    assert not target.exists()
    shutil.copyfile(HERE / 'RetryStudyHooks.java', target)
    receipts.append({'path': str(target.relative_to(CHECKOUT)), 'before': 'ABSENT',
        'after_sha256': hashlib.sha256(target.read_bytes()).hexdigest()})
    (HERE / 'INSTRUMENTATION_RECEIPT.json').write_text(json.dumps(receipts, indent=2) + '\n')
    print(json.dumps(receipts, indent=2))


if __name__ == '__main__':
    instrument()
