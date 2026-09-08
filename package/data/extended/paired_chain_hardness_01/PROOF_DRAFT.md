# Binary-price hardness on disjoint two-job chains

Author proof proposal, not yet independently checked or experimentally tested at creation. This supplements the unit-premium/indegree-two CLIQUE reduction; it does not replace that result or assert strong NP-hardness for this restriction.

Take positive PARTITION numbers a_1,...,a_m summing to 2D>0. For every item create a two-job chain r_i→l_i, with no edges between chains. Set root (c,p)=(3D+1,a_i) and leaf (c,p)=(2D,a_i). Fix B=1 and excess threshold K=3D. The normal-work baseline can be added to both sides for a full-cost threshold. The graph has maximum indegree/outdegree one, undirected treewidth one, and exactly two failure-cost values. Each pair has equal premiums. Prices have polynomial binary encoding, not polynomial numerical magnitude. Odd-total PARTITION instances are immediate negatives and can map to a fixed negative instance; equivalently restrict the source to even totals, which remains NP-complete by doubling its entries.

Use the exact B1 no-failure certificate: a topological order and protected subset H have cost max(sum_{H}p_i, max_{fast i}(c_i+sum_{protected j before i}p_j)). After the first failure all remaining jobs can complete fast, so this certificate represents all adaptive policies at B1.

If a partition subset I has weight D, protect its roots and execute their leaves fast, then protect every other root and leaf. No-failure premium is D+2D=3D. A fast failure occurs after at most D protected premium and costs 2D, so every branch costs at most3D.

Conversely, consider a certificate of cost at most3D. Every root is protected, because trying any root fast permits failure cost3D+1. Let I be its fast leaves. Its no-failure premium is 2D+(2D-sum_{i in I}a_i), giving sum_{i in I}a_i>=D. The failure branch at the last fast leaf forces the protected premium before that leaf to be at most D. All roots corresponding to fast leaves precede it, so sum_{i in I}a_i<=D. Therefore equality holds and I is a partition. I cannot be empty, since D>0.

Membership in NP follows from the order/mode certificate. Thus binary-price threshold synthesis is NP-complete even for disjoint two-job chains. The PARTITION reduction gives weak hardness, not a strong-hardness result. B1 still has an optimal initially fixed order; this is a synthesis-hardness result, not an adaptive-order gap. Merely bounding graph indegree, undirected treewidth or component size does not yield polynomial time in the full binary input unless P=NP. This statement does not rule out pseudo-polynomial algorithms or contradict the existing O(n log n) cost-compatible case: every constructed edge decreases c.

The source NP-completeness result is inherited from PARTITION (Karp1972); the retry mapping above is author reasoning. Closest scheduling formulations can also imply special cases, so this is not standalone novelty certification.
