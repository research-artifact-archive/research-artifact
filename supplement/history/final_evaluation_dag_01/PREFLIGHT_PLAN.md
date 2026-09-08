# Development preflight 01

Author-side implementation preflight, not final evaluation or application evidence.
Ten fixed inputs: empty; singleton zero premium; singleton positive premium;
two independent jobs; ascending-cost chain; descending-cost chain; equal-cost
reverse-labelled chain; three-job fork; three-job join; four-job diamond.
All budgets 0..4. The complete admissible primitive game includes zero-cost
cycles, retained preparation, every batch guard subset, and all failures allowed
by the remaining budget. Compare all roots with scalar DP and serialized hybrid
policy; verify every state potential, every action inequality, all Bellman minima,
and a goal-reaching rank for the selected full primitive policy.

Before execution save the inputs, this plan, source hashes and unchanged imported
source hashes. No exclusion or silent retry. Unexpected exceptions are INVALID;
value/potential/policy counterexamples are FAILURE. The preflight has a total
60-second soft deadline; no final corpus values are observed here. Malformed
general-certificate checks are separate development controls added and frozen
before their own run. All attempts and changes remain saved.
