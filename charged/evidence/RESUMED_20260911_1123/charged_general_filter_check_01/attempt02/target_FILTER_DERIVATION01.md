# Constant-time charged mode queries

This author derivation follows PROOF01.md. Let A=q_D union h_S, T=Top_k(A), tau its kth entry and sigma its (k+1)th entry, extending missing entries with zero. Assume physical 0<=k<=|D|<=n. For a proposed unfinished job i, its entry in A is h_i. Exact thresholds from PROOF01 are

    cached_limit = T - max(0,h_i-sigma),
    fresh_limit  = T - min(p_i,max(0,tau-h_i))   (k>0),
    fresh_limit  = -p_i                        (k=0).

For cached, deleting an entry below the top k leaves T unchanged; deleting one in the top k replaces it by sigma. Ties have equal values, so either membership produces the same result. For fresh when i is in the top k, replacing h_i by q_i=p_i+h_i increases T by p_i, giving fresh_limit=T. When i is outside it, replacing h_i by q_i raises T by max(0,q_i-tau). Subtracting p_i gives the displayed threshold. For k=0, Top_0 is zero before and after replacement. For k=n, sigma=0 and every remaining fee is in the top k. These arguments include zero fees and ties.

An entry h_i cannot lie strictly between adjacent sorted values sigma and tau. Thus every ready job has cached_limit=T or fresh_limit=T, proving constructive mode availability at every viable state.

Maintain a min-heap of the top k entries and a max-heap of the rest, an index handle for each fixed job, and top sum T. Both heap arrays have capacity n allocated at construction. A query reads T and at most two roots and uses a fixed number of arithmetic/comparison operations. Completion increases one entry from h_i to q_i, repairs its heap, exchanges boundary roots if needed, and for a mismatch increases k by transferring the largest low entry to the high heap. Each step requires a constant number of O(log(n+1)) heap repairs. Constructor receives future h and already completed q only; it receives no future p/q, edges, write budget or latency data. It charges O(n+k log(n+1)) initialization and O(n) storage in this implementation, with no unbounded-arrival claim. Costs and bounds count abstract arithmetic/comparison operations; Python integer bit complexity, native memory management, and scheduling remain separate.

Unlike the earlier completed-only implementation, arbitrary premiums require future fee values and forbid some cached actions. The exact formula solves safety; choosing among its allowed ready actions to minimize total work remains a separate problem.
