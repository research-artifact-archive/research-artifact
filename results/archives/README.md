# Large raw evidence

The three `raw-results.tar.gz.partNNN` files form one lossless gzip-compressed tar archive. They contain the large fixed/scaling raw logs, legacy-fidelity raw data and separate contract-repair raw data, including negative and censored trials. Smaller ext1–7 raw and all finite-family inputs/certificates can be browsed directly in the sibling folders.

Do not manually rename or edit the parts. From the repository root run:

```sh
python3 reproduce/materialize.py --output work/full-workspace
```

The manifest verifies every part and every member, restores original relative paths in a new workspace, and decompresses the two large CSVs. No external asset host, Git LFS or release is required.
