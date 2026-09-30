# Granularity families and certificates (E6)

Start with the [main result narrative](../../../README.md#why-fine-granularity-can-matter) and the [portable runner](../../../tool/README.md). This directory contains scientific inputs, generators, raw trials, serialized certificates, independent checkers, failed checker/model versions and controls. Editorial coordination notes are excluded.

| Family | Canonical location | Role |
|---|---|---|
| Rolling | `rolling/v1/` | startup availability and group-size threshold |
| Canary | `canary/v1/` | all-outcome transfer reports and recovery |
| Policy | `policy/v2/` | opposing audit/role boundary orders |
| DB-Rolling | `db_rolling/v2/` | secondary-first maintenance and no-slack controls |
| Rolling-Audit | `rolling_audit/v1/` | readiness and audit interaction |
| Threads | `threads/v1/` | barrier/backpressure controls, including null results |
| PC2-Rolling | `pc2_rolling/` | unresolved measured merged comparison; separate structural argument |

`results_index.csv` and `integration/status.json` define the main 55-pair denominator (33 separations, 11 both-LOSS, 10 both-WIN, 1 incomplete). `rolling_scale/`, `canary_controls/` and Cell references remain separate. PC2 extended-budget trials are additional attempts, not extra main pairs. Original failed/earlier versions are retained.

`common/SCHEMA.md` documents finite JSON inputs. `common/` also supplies the frozen Java adapter; its historical measured-JAR constant is preserved. The portable public runner compiles a copy and records the actual rebuilt JAR digest. No measured JAR download is offered. `tools/` contains the original scientific runner; use the portable root command for new local runs.

`independent/` reconstructs finite games and endpoint products without invoking Java. Saved checker attempts and corrupt-certificate controls are retained; the current public checker also invokes the strict checker on 22 small canonical jobs. `integration/generator_reproduction/` records exact generator reproduction and its initial harness failure. Family READMEs and historical design notes provide detailed assumptions; pre-run/finalization comments there do not supersede the final indexes.
