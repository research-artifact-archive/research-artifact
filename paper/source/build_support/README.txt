Building this candidate

The accompanying build tools package the current section titles and hyperlinks.
They do not update the public replication archive. With XeLaTeX and latexmk on
PATH and Python 3 packages pypdf and reportlab installed, run from this source
directory, choosing a fresh output path:

  python3 build_support/build_paper.py --source . --output /tmp/fgducs-candidate-build

Outputs are main.pdf, technical_appendix.pdf, supplement.pdf and
supplementary_material.pdf. The last file has the linked reading guide, complete
contents and continuous page numbering. The command builds in an output copy
and leaves the manuscript source unchanged. The source includes the saved-
evidence analyses and copied inputs described in evidence/README.txt.
