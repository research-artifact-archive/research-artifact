# Fixed-before-run author-side three-actual-cost check, attempt01

Route: SCIENTIFIC. Scope: the supplied THREE_COSTS_HYPOTHESIS03 only, including the model translation in PROOF02. This is author-side algebra/model scrutiny, not blind review or an acceptance assessment. This folder is the only write destination. No paper/public/shared-state edits, child agents, Claude, human evaluation, reset, credit, purchase or paid API. Stop no later than 2026-09-11 14:00 JST (05:00 UTC). The process has a 180-second CPU/wall execution bound, additionally capped at 04:55 UTC, leaving time for a report.

## Population, fixed before executing any costs or candidate outcomes

One complete, deliberately small integer population: n=0,1,2,3; every labeled simple directed acyclic graph (include transitively redundant edges as distinct inputs); every assignment, with repetition, of the following eight actual (match a, fresh f, bad b) price triples; every completed ideal D; every physical integer k=0,...,|D|. No symmetry reduction, randomness, adaptive enlargement, retries or exclusions. The empty graph and terminal states are included. Triples are:

| ID | a | f | b | Selected boundary |
|---|---:|---:|---:|---|
| Z | 0 | 0 | 0 | all zero, zero mismatch increment |
| E | 2 | 2 | 2 | positive baseline, all modes same cost |
| N0 | 2 | 0 | 2 | f<a, b=a, zero mismatch increment |
| N1 | 3 | 1 | 4 | source w=1,g=0,c=3; comparison exceeds body |
| T | 2 | 2 | 3 | source w=c=1,g=1; equal fresh and match |
| P0 | 0 | 2 | 2 | f>a, b=f, zero match cost |
| P1 | 1 | 2 | 3 | strict a<f<b |
| P2 | 2 | 4 | 4 | source w=2,g=2,c=0; b=f |

All prices satisfy 0<=a,f<=b. Repeated price assignments include ties. General zero prices are valid because every call completes one job; a zero charge is not a zero progress step. No assertion that all triples are physically measured software prices is made.

freeze01.py writes an explicit population.jsonl (actual prices per state), a cost-independent full policy catalog, graph/count metadata, source snapshots, and a SHA-256 FREEZE01.json binding every implementation file and all inputs. It does not execute prices, the oracle or candidate comparisons. The catalog contains every deterministic completing policy tree: for each ready root i, all fresh continuation policies, and the Cartesian product of all matching and mismatching continuation policies for cached i. It also saves every leaf's complete sequence of (job, outcome), without cost/dominance pruning or identical-outcome deduplication. The catalog is a compact representation of full trees via exact successor policy IDs, not a value-function recurrence. Only the freeze phase may create these inputs; the evaluation phase verifies their hashes and refuses to overwrite a run.

## Independent actual-cost oracle, then candidate comparison

For each game, the oracle builds the all-cache benchmark independently: enumerate all mismatch subsets of J, add actual b_i on those jobs and actual a_i on the others, then take the maximum actual sum over subsets with cardinality <=r for r=0,...,n+2. This uses no candidate normalization or Top formula. Every subset and its sum is raw-recorded. Since at most n mismatches are possible, r>=n saturates, so these finite benchmarks also cover all larger budgets.

For every complete policy and every leaf, add the selected actual a_i/f_i/b_i charges along that leaf. With c future cached mismatches, record actual future charge t, c, benchmark B(k+c), and the implied permissible actual-prefix margin B(k+c)-t. A policy's threshold is the minimum of its leaf margins. The state oracle is the maximum across ALL policy thresholds; each exact mode oracle is the maximum across all policies with that specific ready job and root mode. This evaluator imports no candidate formula or existing filter implementation and never subtracts the candidate baseline. No pruning by candidate viability or by outcome cost is permitted.

All per-game, per-policy, per-leaf raw records are written and flushed before the game's comparison is run. The full raw stream is closed and hashed before any aggregate comparisons are reported. The fixed run log retains start, success, exceptions and timeouts; on failure no trial is silently repeated. Partial raw is retained; uncompleted inputs are recorded, never removed from the denominator.

Only the separate comparison module uses q=b-a, p=f-a, d=(a-f)+, t=b-max(a,f), and the candidate formulas. Check the actual benchmark against sum_J a+Top_r(q_J); then exact oracle state threshold against sum_D a+sum_S d+Top_k(q_D union t_S). For each ready i check cached against sum_D a+sum_(S-i)d+Top_k(q_D union t_(S-i)), and fresh against that same constant plus Top_k(q_D union t_(S-i) union {q_i})-p_i. Check each ready job's best mode attains the state threshold. Probe actual prefix costs 0 and nonnegative integer points immediately below/at/above every state and mode threshold; compare permissions and state viability to the already-recorded full-policy leaf inequalities. Count negative normalized prefix values explicitly; do not require normalized ell>=0. Exact thresholds, not a finite lambda grid, establish the finite model's permission equivalence.

## Falsifiers and limits

Any benchmark, state or mode mismatch; missing/duplicate structural policy; invalid DAG/ideal/price; wrong raw denominator; source/code/hash change; or incomplete run is retained as a failure or incomplete result. Expected structural counts are frozen without candidate evaluation. A zero-disagreement run corroborates ONLY this population. The general proof is a separate analytic argument over real nonnegative actual prices and integer k>=0; surplus k is algebraic, not an observed physical mismatch count. No old 130,832-game run or positive-p heap test is rerun, imported as new evidence, or included in this denominator. Implementation independence means this oracle has its own complete policy/leaf and actual-price construction; author/context independence is not claimed.

Raw files are append-only new outputs in run01. A timeout or programming error gets an immutable error/attempt receipt; no code repair and rerun is part of this single attempt. Final REPORT.md states the analytic finding, actual frozen counts, every failure/timeout/incomplete category, implementation exclusions, and local stop status.
