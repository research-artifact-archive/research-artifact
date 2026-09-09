# Notification subphases — recorded before native follow-up

The finite DP and upcoming108 cells use the existing synchronized driver: at FULL/COMPLETE, the observer waits while value notifications and cycle completion finish together. No foreground callback runs between notification and the end of that writer request. Within that domain, clock parity and the known initial clock determine the modeled phase and remaining starts.

General native executions can expose a notification while the logical clock remains Updating. V's notification-aware control can then fail without a clock boundary, and a later callback can select current values before the cycle ends. K's notification-oblivious control differs. A parity-only game does not explicitly represent this notified-but-still-Updating state. Therefore neither all-native exactness nor an upper bound for unrestricted notification timing follows from this first phase model. A broader abstraction must distinguish notification readiness/usePreviousValues (possibly a third state) and analyze the K/V difference.

The upcoming result is a finite-DP controller extension on the fixed synchronized source driver, with actual native callbacks. It is not an all-budget import, a whole-program optimum, or an unrestricted application guarantee. The previously derived flat2q bound and its original scope remain separate.
