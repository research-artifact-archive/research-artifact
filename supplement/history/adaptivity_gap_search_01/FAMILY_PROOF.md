# A four-job 1/13 total-work separation

Author derivation, 2026-09-08. Developed after adaptive numerical search; the six scaled instances were fixed before independent scalar validation. This is a constructive lower bound on possible adaptivity gain, not a universal upper bound or prevalence claim. Search/raw/fixed evaluation denominators are distinct.

For any k>0 use c=a=k(3,7,5,1), p=k(2,2,6,2), edges 0->1, 0->2, 1->3 and initial failure allowance B=2. There are exactly three topological completion orders: 0123,0132,0213. Normal work is16k. We show adaptive excess8k, every optimal fixed-order excess10k, hence total24k versus26k, relative reduction1/13.

All values below divide byk. Bellman is homogeneous, so it suffices to work with k=1. The relevant residual upsets and values are:

|Unfinished S|V(S,0)|V(S,1)|V(S,2)|
|---|---:|---:|---:|
|empty|0|0|0|
|3|0|1|2|
|2|0|5|6|
|1,3|0|3|4|
|2,3|0|5|6|
|1,2,3|0|5|8|
|0,1,2,3|0|5|8|

Each row follows by enumerating the available jobs and their two Bellman branches. For S={1,3}, job1 is the only available job, giving min(2+1,7)=3 and min(2+2,max(2,7+3))=4. For {2,3}, atb1 a fast action gives5; atb2 fast3 gives max(V({2},2),1+V({2,3},1))=max(6,6)=6, and every protected/fast alternative is at least6.

For S={1,2,3}, atb1 FAST2 has value max(3,5)=5; PROTECTED1 has7, FAST1 has7, PROTECTED2 has9. Atb2 PROTECTED1 has2+6=8; FAST1 has max(6,7+5)=12, PROTECTED2 has6+4=10, FAST2 has max(4,5+5)=10. Thus values5 and8 and the optimal next jobs differ across these two budgets. At the root onlyjob0 is ready. Atb1 FAST0 costs max(5,3)=5 versus protected7. Atb2 FAST0 costs max(8,3+5)=8 versus protected10. This establishes the adaptive value8.

For fixed orders0123 and0132, the suffix afterjob0 has values7 and8 atbudgets1 and2. Applying job0's single-job recurrence gives root values7 and10. For order0213, the suffix afterjob0 has values5 and10, hence root values5 and10. All three orders therefore cost10 atB2, even though modes and number of retries are chosen optimally for each observed failure history. These are all legal orders, establishing the lower bound and its attainment.

The adaptive root retriesjob0. If it succeeds with no failure, the residual allowance remains2 and the policy protectsjob1 before continuing. If job0 fails once and then succeeds, the residual allowance is1 and the policy startsjob2 fast. Both histories are legal. A fixed completion order cannot implement both residual choices. This example isolates budget-dependent sequencing after a mandatory prefix; it does not rely on a weak heuristic baseline.

The separation is robust to small price perturbations. With n=4,B=2, every terminating macro path contains at most2 failed attempts and4 protected completions. Its excess cost therefore changes by at most6epsilon when each c_i,p_i changes by at mostepsilon. Maxima over paths and minima over policies/orders preserve this bound, so F-V changes by at most12epsilon. The original excess gap2k remains positive whenever epsilon<k/6. Costs and premiums remain admissible in this neighborhood. Thus positive gain occurs on an open region; the exact1/13 ratio is asserted only for the homogeneous family.

`scalar_check.py` independently enumerated finite-budget Bellman actions and all permutations without importing the search curves. It checked the24 chain winners and six specified family scalings:30/30 SUCCESS,365 root comparisons,0 adverse statuses. This supplements the explicit calculation above and is not a proof of a global adaptivity-gap bound. The previous native fixed evaluation still has2/192 strict roots,max2.0833%; the new selected family is not part of that evaluation.
