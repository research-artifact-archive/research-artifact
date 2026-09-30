# Literal hidden-outcome proposal (not implemented)

The initial proposal used an old healthy state, new healthy/broken states, the set-valued transfer healthy -> {healthy, broken}, a controllable restart, and an interval predicate that directly counts physical healthy states immediately after transfer. This design was inspected before any synthesis trial.

The fixed E1 API's deterministic SafetyTester observes action labels. Both transfer outcomes have the same transfer label, so this tester cannot directly distinguish their physical health. Initializers can inspect physical states when a requirement activates, but they do not reinitialize the interval tester after every transfer. Implementing a physical-state oracle or changing Post would violate this experiment's fixed-solver rule.

No input or result was generated for this literal proposal. It is retained as a rejected representation, not a measured LOSS or evidence that such a contract cannot be expressed in another formalism. The subsequent reported-health version adds explicit, finite, uncontrollable observation transitions and retains both transfer outcomes. Its interval requirement and additional physical-policy check are reported separately.
