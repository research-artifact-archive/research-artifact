# Rebuilding the fixed Deephaven studies

The standard `reproduce.py deephaven` stage checks saved records and requires Python only. The optional command below creates a new upstream checkout, builds the instrumented Java studies and checks new records. It is a replay of fixed source configurations, not a new evaluation population.

Install JDK 21 separately, then run from the repository root:

```sh
python3 charged/deephaven_native.py all --out work/deephaven-native --java /absolute/path/to/jdk-21/bin/java --timeout 900
```

The driver fetches the archive for upstream commit `6367313a319b79437d4d2116c77836ad56d5138d` from GitHub and requires SHA-256 `b748965bdf42c66092a99b919115592c125ef584832b4e428e236bfc6b30bd1f`. Alternatively supply that exact archive with `--archive /absolute/path/to/archive.tar.gz`. Archive members and internal symbolic links are checked before extraction. The modified production files, authored test class and fixed profile resources come from each preserved study snapshot.

The pinned Gradle wrapper builds `:engine-table:testOutOfBand` with two workers, a 2 GiB test heap, no daemon and no build scan. A fresh dependency cache is used by default; `--gradle-cache /absolute/path/to/cache` can reuse a local cache. Fetching build dependencies requires network access. Original runtime binaries and downloaded dependencies are not bundled, and a cache-assisted replay is not a measurement of a clean first-time dependency installation.

| Selection | Native records |
|---|---:|
| `prefix` | 216 |
| `event` | 12 |
| `phase` | 108 |
| `key` | 36 |
| `all` | All 372 across the four studies |

Each selected study runs into its own output directory. A current JUnit XML record must have the complete expected ID set. The driver writes new JSONL records and applies the corresponding separate trace checker; changing-Action records also pass the strengthened checker. The XML, logs, source hashes, command, elapsed replay time and complete outcome remain in the output. Failed or timed-out replay stages are not silently retried.

This uses the fixed 31-row hierarchy, fixed ID/Parent structure, specified directives/Actions, selected operation counters and caller-owned synchronized refresh contract described in the paper. It does not offer arbitrary input-table schemas. The operation bound is distinct from whole-program work or elapsed time. Partially notified interleavings and arbitrary live writer populations are outside the stated guarantee.

Deephaven engine source and these modified upstream files remain under the full [Deephaven Community License Agreement 1.0](licenses/deephaven/LICENSE.md) and [notice](licenses/deephaven/NOTICE.md). Its Section 4 includes schema-related restrictions. The full license governs use and redistribution; the repository MIT license does not replace it. The fetched archive contains additional components with their own notices, retained in that checkout.
