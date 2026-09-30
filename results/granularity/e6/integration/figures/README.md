# ME figure prototypes

The SVGs are the editable vector sources, generated from checked certificate paths by `render_me.py`. The PNGs are full-size visual previews. Plain Rolling uses four update transitions; Audit uses the six-transition path from one old-unlogged Lazy root and explicitly discloses the policy-wide rank7. Old/new audit lifetime bars overlap between start-new and stop-old; one interval bar covers both availability and audit coverage. All labels identify event order, not time.

Visual QA: complete extents and all labels checked after full-size ImageMagick rendering with an explicit system font. Horizontal bars and arrowheads are simple filled vector primitives for renderer compatibility. Quick Look produced a cropped draft thumbnail, retained under `preview_failures/`; it is not a handoff figure. No measured model/result or manuscript was edited.

## Measured scaling plot

`rolling_state_counts.tex` is a standalone PGFPlots figure compiled successfully with the native editor on 2026-09-29. `../build_rolling_plot.py` reads the canonical original and scale summaries; its provenance JSON binds both source digests. Both panels show all n=2..16 observations for m=1 and m=n−1. Axes explicitly say discovered states; the logarithmic ordinate and individual markers remain visible. No timing comparison or extrapolated measured point is included. `rolling_structural_sizes.csv` records the polynomial-sized explicit input alongside observed solver state counts.
