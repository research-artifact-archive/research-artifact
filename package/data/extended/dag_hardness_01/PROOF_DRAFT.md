# Exact DAG threshold complexity at a single possible failure

Author proof draft, 2026-09-08 04:08 JST, before new finite reduction checks. Subject to read-only author challenge. Model is the existing reduced retry game, with a_i=c_i>0,p_i>=0,normal excess0,failed fast excessc_i consuming one token,protected completion excessp_i. No source semantics or old outcomes change.

## Single-failure certificate and fixed-order equality

For B=1, let a deterministic policy's path with no failures have topological completion order pi and each job's mode FAST or PROTECTED. On this path, let P_i be the sum of premiums of protected jobs completed before jobi, and let P_total be the sum on the whole path. Replacing every continuation after the one possible failure by all-fast completion cannot increase excess cost, since remaining allowance iszero. The resulting policy's worst excess is exactly

max(P_total, max over fast jobi of(P_i+c_i)).

Indeed, an adversary either never fails, or chooses its first/only failure at one fast job on the no-failure path. The latter then finishes and all other jobs finish with zero additional excess. The no-failure path's order can be fixed in advance; after a failure use that same remaining order. It remains topological. Thus F(J,1)=V(J,1) for everyDAG; B0 also has zero excess. An order plus mode bits is a polynomial certificate for threshold feasibility, and its value is computed by one scan. This establishes membership inNP for the B1 threshold decision problem, with binary prices and threshold.

## Reduction from CLIQUE

Start from an undirected simple graph G and target k>=2. If k exceeds the vertex count or m<ell=k(k-1)/2, map the trivially negative instance to one job with c=2,p=1,B1,excess threshold0. Otherwise add one isolated vertex, preserving existence of a k-clique and guaranteeing n>k. Let n andm be the resulting vertex andedge counts, and

K=n+m-ell >= n > k.

Create a vertex jobx_v for every vertex, with p_v=1 andc_v=K+1. Create an edge joby_e for every edgee={u,v}, with p_e=1 andc_e=K-k. Add only dependencies x_u->y_e andx_v->y_e. There are N=n+m jobs and2m edges. The DAG has two layers and maximum indegree2, all premiums are1, and the positive failure costs use only the two valuesK+1 andK-k. All numbers are bounded byN+1. Ask whether V(J,1)<=K, or equivalently whether minimum full work is at most sum_i c_i+K.

If G has a k-clique, first protect its k vertex jobs. Run its ell edge jobs fast. Any failure during this phase incurs excess k+(K-k)=K; after it, finish every remaining job fast at residual allowancezero. If no failure occurs, protect every remaining vertex/edge job, obtaining total protected premium n+m-ell=K. The no-failure order takes clique vertices, clique edges, remaining vertices, remaining edges, and remains legal after a failure. Thus V<=K.

Conversely, suppose V<=K and inspect a winning deterministic policy's no-failure path. A vertex job cannot be fast: its legal failure would alone costK+1, in addition to nonnegative earlier premiums. Hence all n vertex jobs are protected. Every fast edge job must occur with prior protected premium at most K-c_e=k, or Nature could fail it and exceedK. Both endpoint vertex jobs have then been protected. Consequently all fast edges have both endpoints among the first k protected vertex jobs on this one no-failure path. (Protected edge jobs also consume premium; they cannot enlarge this set.) If f edge jobs are fast, no-failure premium is n+(m-f)<=K=n+m-ell, hence f>=ell. At mostk vertices in a simple graph contain at mostell edges, with equality only for a k-clique. Therefore G contains a k-clique.

This is a polynomial reduction and proves NP-completeness for B1, even with uniform premiums, two positive failure costs, a two-layer DAG and maximum indegree2. It shows hardness is present without large numerical budgets or an adaptive-order gap. It does not prove an exponential-space lower bound, an exponential curve-count lower bound, or tightness of this implementation's ideal enumeration. The primitive-value theorem transfers the value threshold to the declared richer interface, but it does not yieldNP membership for unrelated arbitrary-language program-synthesis problems.

## Separation of boundaries

1. B<=1: one initial fixed-order retry controller attains V for everyDAG, but finding the optimum can already beNP-complete.
2. At mostthree jobs: the earlier concave-operator/two-job argument gives F=V for each initialbudget.
3. Fourjobs,B2: the k-scaled c=(3,7,5,1),p=(2,2,6,2) example gives positive gap1/13.
4. Costs nondecreasing along edges: the existing ordered specialization compiles/checks allbudgets inO(E+nlogn).

These are author mathematical results, not an acceptance prediction. Nearest-work attribution and application questions remain separate.
