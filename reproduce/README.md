# Reproduce and verify

Start with [the main reproduction instructions](../README.md#reproduce-the-study), then the [detailed guide](../docs/REPRODUCTION.md).

`check.py` runs saved-evidence validation in a fresh restored workspace. `materialize.py` verifies and restores files using `layout.json`. `check_extensions.py` checks E-series/ext1–7 data and small independent finite games. `scripts/` preserves earlier helpers plus the portable finite runner. `solver-variants/` gives measured source identities and baseline-relative patches. `campaign/` and `validation-protocol/` preserve original experimental programs/configurations; dated protocol status text may describe pre-run plans. `previous-validation/` is explicitly historical validation from the preceding artifact version, not the result of this update.

New runs must use fresh output directories. A saved-evidence PASS is not a new Java measurement or an external proof. Full benchmark reruns require the recorded resources and variants.
