# Root caps certify sorted-order suffixes

Draft before checker execution, September8 01:52 JST. Author argument, not formal or blind certification.

Let the supplied F have F(0)=0, positive integer nonincreasing marginal runs, and a zero tail at P=sum_i p_i. Let a valid topological order have nondecreasing c_i. For position k define P_k=sum_{j>=k}p_j and f_k(b)=min(F(b),P_k). The final suffix f_n is zero. It suffices to verify, for every positive budget b,

f_k(b)=min(p_k+f_{k+1}(b), max(f_{k+1}(b),c_k+f_k(b-1))).

Induction on suffix length and budget gives the value of the fixed-order policy; the independent-order theorem and a legal sorted topological order give unrestricted DAG optimality. The root is f_0=F. No construction-specific cap property is assumed by this validation argument.

For p=0, adjacent candidates coincide and protection is optimal everywhere. Require threshold0. Otherwise write a=P_{k+1}<z=P_k and tau(x)=min{b:F(b)>=x}, with tau(0)=0. Set u=tau(a), v=tau(z). Both exist, v>=u and v>=1. Check:

1. If u>=2, Delta F(u-1)>=c.
2. If u>=1, min(F(u),z)=min(z,max(a,c+F(u-1))).
3. On the integer interval max(1,u+1)<=b<=v-1, require Delta F at both endpoints to equal c (an empty interval imposes nothing).
4. z<=c+F(v-1).
5. The encoded protection threshold equals v.

For 1<=b<u, F(b)<a and both suffixes equal F(b); protection is larger and fast attains F exactly iff DeltaF(b)>=c. Concavity reduces this prefix to condition1. At b=u>=1, the child is a, the parent is min(F(u),z), and the previous parent is F(u-1)<a; condition2 is exactly Bellman. For u<b<v, the child is a, the parent is F(b)<z and F(b-1)>=a, so Bellman holds iff DeltaF(b)=c. Concavity and condition3 cover that interval. At b=v, the parent is z and the child is a<z; protection gives z and fast cannot undercut it iff condition4 holds. If u=v, conditions2 and4 intentionally overlap. For b>v the parent and child are their constant caps and protection attains the smaller cost. Budget0 is the separate no-failure boundary. Thus all budgets are covered.

For p>0, protection is strictly above f_k(b) for b<v and attains f_k(b)=z for b>=v. Thresholdv therefore implements earliest protection-first ties. At p0 threshold0 does so. This fixes the narrower canonical-threshold gap of checker01, although checker01 still verified action optimality.

Store cumulative run lengths and areas. Budget values, marginal values and tau queries each take O(log(r+1)) comparisons with exact integer arithmetic; tau uses one ceiling division within its located run. Graph/order validation costs O(n+|E|) with a rank array and duplicate-edge set. All n local conditions plus curve validation cost O(n log(r+1)+n+|E|+r) arithmetic operations and O(n+|E|+r) memory including input checks. Bit complexity remains a separate cost.

Why compiler01 should supply a passing candidate: each reverse-order insertion raises only the previous final singleton and appends new slopes. Removing exactly its premium from the rightmost positive marginal mass reconstructs the previous suffix, including any partially raised singleton. Equivalently the previous suffix curve is the new curve capped at its previous total premium. Repeated caps compose by their smaller level, so all sorted suffixes are caps of the final root. This construction lemma explains completeness for packing; checker soundness instead follows from the direct Bellman argument above.
