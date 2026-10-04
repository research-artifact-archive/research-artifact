#!/usr/bin/env python3
"""Build the main paper, integrated supplement and component PDFs with stable links."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from pypdf import PdfReader
from package_supporting_pdfs import package


def auxiliary_signature(build):
    paths = [build/(name+'.aux') for name in ('main', 'technical_appendix', 'supplement')]
    return tuple(hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None for p in paths)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='A new build directory')
    parser.add_argument('--source', type=Path, help='Manuscript source directory')
    parser.add_argument('--artifact-root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists():
        parser.error('Choose a new build directory')
    latexmk = shutil.which('latexmk')
    if latexmk is None or shutil.which('xelatex') is None:
        parser.error('Building these multi-file sources requires latexmk and XeLaTeX on PATH')
    root = args.artifact_root.resolve()
    source = args.source.resolve() if args.source else root/'paper/source'
    out.mkdir(parents=True)
    work = out/'source'
    shutil.copytree(source, work)
    logs = out/'logs'; logs.mkdir()
    build = work/'build'

    def compile_document(name, round_number):
        log = logs/f'{name}-{round_number}.log'
        with log.open('w') as stream:
            result = subprocess.run([latexmk, '-g', '-xelatex', '-interaction=nonstopmode',
                                     '-halt-on-error', '-outdir=build', name+'.tex'],
                                    cwd=work, stdout=stream, stderr=subprocess.STDOUT)
        if result.returncode:
            raise SystemExit('Compilation failed; inspect ' + str(log))

    previous = auxiliary_signature(build)
    for round_number in range(1, 5):
        for name in ('main', 'technical_appendix', 'supplement'):
            compile_document(name, round_number)
        current = auxiliary_signature(build)
        if current == previous and all(current):
            break
        previous = current
    else:
        raise SystemExit('Cross-references did not stabilize within four rounds')
    documents = ('main', 'technical_appendix', 'supplement')
    for name in documents:
        log = (build/(name+'.log')).read_text(errors='replace')
        unresolved = ('There were undefined references', 'There were undefined citations',
                      'Reference `', 'Citation `')
        if any(token in log for token in unresolved):
            raise SystemExit('Inspect unresolved-reference warnings in ' + name + '.log')
        shutil.copy2(build/(name+'.pdf'), out/(name+'.pdf'))
    title = ' '.join((PdfReader(build/'main.pdf').metadata.title or
                      'Fine-Grained Dynamic Update Controller Synthesis').replace(':', ': ').split())
    packaged = package(build/'main.pdf', build/'technical_appendix.pdf',
                       build/'supplement.pdf', out/'submission', auto_guide=True,
                       visible_page_numbers=True, title=title)
    for name in ('main', 'supplementary_material', 'technical_appendix'):
        shutil.copy2(packaged/(name+'.pdf'), out/(name+'.pdf'))
    documents = ('main', 'supplementary_material', 'technical_appendix', 'supplement')
    print(json.dumps({'status': 'PASS', 'cross_reference_rounds': round_number,
                      'outputs': [str(out/(name+'.pdf')) for name in documents],
                      'source_unchanged': True}))


if __name__ == '__main__':
    main()
