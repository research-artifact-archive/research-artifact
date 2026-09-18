# Distribution identities and raw assets

All paths are relative to the package root.

## Key distribution identities

| File | SHA-256 |
|---|---|
| `paper/main.pdf` | `32e819314f599b976bf58e08c7699dc1e21648fc9c3aaa7301cab5a33eca12ac` |
| `paper/supplement.pdf` | `196d55e721086bfbd89178d98678ae238595f7bb16632830e9d22ab8df1a34a4` |
| `fetch_assets.py` | `5dff4b083c15ee7de348625d1da8cf0ae325453c1dfa39b7956f7e07fb3225d5` |
| `restore_results.py` | `283066e8512101a6f41cf2e1bad5311f3e1cf90cb0eb77c607113f6964cdbfcd` |
| `result-assets.json` | `97bc32f4f2f611e44927d72b55550046603184e5ea15775d1d4abc450de86fa7` |
| `FSE2027_SUBMISSION_20260914/experiments/rs_coverage/summary.csv` | `a3de15da4fc92884d1f3a0095b7781390449c78cfe54ab93f360a605751d0f4d` |
| `FSE2027_SUBMISSION_20260914/experiments/rq3_xeon/scripts/render_results.py` | `20627c81821d59523152e8de84f7a2b7122ac691daded3bfe0fb461da9dcc6ad` |
| `Implementation/Source Code/maven-root/mtsa/pom.xml` | `3fdc4272800b699fc4fa3e6916321d5d4a17302f22a5941f2c23fabf97a68e54` |

## Result release assets

The repository keeps RQ1/RQ2 saved evidence, source, models, configs and generated paper outputs. Complete RQ3/RQ4, legacy-reference and Industry-variant raw are in the parts below. Download **every part**, preserve its name, and run the restoration command; the parts form one gzip/tar stream. The script checks every part and file and refuses to replace different existing data.

```sh
python restore_results.py --assets /path/to/downloaded-assets --verify-only
python restore_results.py --assets /path/to/downloaded-assets
```

| Asset | Bytes | SHA-256 |
|---|---:|---|
| `fgducs-results.tar.gz.part001` | 90000000 | `7b471f6ae6e13c9a25c44f32e0f132493e4398434624be85c9a3009e63a3c691` |
| `fgducs-results.tar.gz.part002` | 2850581 | `bc5565f3a84129beb685654380fbf3c526bdce52ef3389f74748400e9e0f58fd` |

`result-assets.json` lists every archived path, size and digest. No solver/dependency JAR, lib/ tree, private decisions or private runbook is included.
