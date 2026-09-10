# Post-outcome action control and protocol deviation

The original PLAN.md requested a policy-action corruption; run01 instead corrupted a policy cost. This is a control implementation deviation. The original four controls and all numerical outcomes remain unchanged. The paper and supplement accurately call them changed-output/cap controls.

After reading the original outcomes, this separate check selects the existing w=5, kappa=1, r=2, B=0 row. It changes a zero-cheap-failure cached finish to a fresh finish, retaining the old cost. The expected-cost gap is5. The validator must reject that action mutation and accept the unchanged original. Record both hashes and results. This supplemental check is explicitly post-outcome, not an original preregistered control or new experimental sample. No rerun of run01 and no change to its SUCCESS denominator or original four controls.
