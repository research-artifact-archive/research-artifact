/** Body-work residual safety component, Java 17. Single foreground owner.
 * No future-job input, scheduler, write budget, or runtime counters enter here.
 * State: completed positive long weights, credit k, protected body work ell.
 * Heaps and topSum are derived indexes of that state. Operations with a result
 * outside the nonnegative signed-long domain throw ArithmeticException.
 * Validation/overflow rejection is atomic, excluding resource exhaustion.
 */
public final class ResidualFilter {
    public enum Outcome { MATCH, MISMATCH, FRESH }
    public record State(long k, long ell, long topSum, long completed, Long kth) {}
    private final Heap high = new Heap(true);
    private final Heap low = new Heap(false);
    private long k, ell, topSum;

    public ResidualFilter() { this(new long[0], 0, 0); }
    public ResidualFilter(long[] completedWeights, long k, long ell) {
        if (completedWeights == null || k < 0 || ell < 0)
            throw new IllegalArgumentException("null completed weights or negative k/ell");
        this.k = k;
        for (long weight : completedWeights) {
            checkWeight(weight);
            prospectiveTop(weight); // preflight representability before insertion
            insert(weight);
        }
        if (ell > topSum) throw new IllegalArgumentException("nonviable residual state");
        this.ell = ell;
    }
    private static void checkWeight(long weight) {
        if (weight <= 0) throw new IllegalArgumentException("current weight must be positive");
    }
    private long prospectiveTop(long weight) {
        if (k == 0) return 0;
        if (high.size() < k) return Math.addExact(topSum, weight);
        return Math.addExact(topSum, Math.max(0, weight - high.element()));
    }
    /** Current weight is transient: query does not insert it or mark completion.
     * The scheduler must ensure a fixed positive weight and a ready new job.
     * O(1) comparisons, long arithmetic, and heap-peek accesses.
     */
    public boolean permitsFresh(long currentWeight) {
        checkWeight(currentWeight);
        long nextEll = Math.addExact(ell, currentWeight);
        return nextEll <= prospectiveTop(currentWeight);
    }
    /** Call exactly once AFTER a successful completion. MATCH also admits a
     * successful cheap-phase completion before starting the residual suffix.
     * Failed cheap calls must not be recorded. No job identities are stored:
     * duplicate completion and incorrect callback labels are caller obligations.
     * O(log(|D|+1)); all foreseeable validation/overflow is checked before edits.
     */
    public void recordCompletion(long currentWeight, Outcome outcome) {
        checkWeight(currentWeight);
        if (outcome == null) throw new IllegalArgumentException("null outcome");
        Math.addExact(Math.addExact(high.size(), low.size()), 1); // completion-count preflight
        long nextK = outcome == Outcome.MISMATCH ? Math.addExact(k, 1) : k;
        long nextEll = outcome == Outcome.MATCH ? ell : Math.addExact(ell, currentWeight);
        // Top_(k+1)(D+w) = Top_k(D) + max(w, largest value outside old top-k).
        long nextTop = outcome == Outcome.MISMATCH
            ? Math.addExact(topSum, Math.max(currentWeight, low.isEmpty() ? 0 : low.element()))
            : prospectiveTop(currentWeight);
        if (nextEll > nextTop) throw new IllegalArgumentException("unsafe fresh completion");
        if (outcome == Outcome.MISMATCH) {
            k = nextK;
            if (!low.isEmpty()) {
                long promoted = low.remove();
                high.add(promoted);
                topSum = Math.addExact(topSum, promoted);
            }
        }
        insert(currentWeight);
        ell = nextEll;
        if (topSum != nextTop) throw new AssertionError("heap transition mismatch");
    }
    private void insert(long weight) {
        if (high.size() < k) {
            high.add(weight);
            topSum = Math.addExact(topSum, weight);
        } else if (!high.isEmpty() && weight > high.element()) {
            long removed = high.remove();
            high.add(weight);
            low.add(removed);
            topSum = Math.addExact(topSum, weight - removed);
        } else low.add(weight);
    }
    /** O(1) mathematical state observation for a caller/trace, no runtime data. */
    public State state() {
        return new State(k, ell, topSum, Math.addExact(high.size(), low.size()),
                         k > 0 && high.size() == k ? high.peek() : null);
    }

    /** Linked complete binary heap. Avoids PriorityQueue's occasional O(n)
     * backing-array copy. An insertion/removal follows at most O(log n) parent,
     * child, or binary-index links and allocates at most one node. GC and memory
     * allocation latency are outside this abstract operation-count guarantee.
     */
    private static final class Heap {
        private static final class Node {
            long value; Node parent, left, right;
            Node(long value, Node parent) { this.value=value; this.parent=parent; }
        }
        private final boolean minimum;
        private Node root;
        private long size;
        Heap(boolean minimum) { this.minimum=minimum; }
        long size() { return size; }
        boolean isEmpty() { return size==0; }
        long element() {
            if(root==null) throw new IllegalStateException("empty heap");
            return root.value;
        }
        Long peek() { return root==null?null:root.value; }
        private boolean precedes(long a,long b) { return minimum?a<b:a>b; }
        private Node at(long index) {
            Node node=root;
            for(long bit=Long.highestOneBit(index)>>>1;bit!=0;bit>>>=1)
                node=(index&bit)==0?node.left:node.right;
            return node;
        }
        void add(long value) {
            long index=Math.addExact(size,1);
            if(size==0) { root=new Node(value,null);size=index;return; }
            Node parent=at(index>>>1),node=new Node(value,parent);
            if((index&1)==0) parent.left=node; else parent.right=node;
            size=index;
            while(node.parent!=null && precedes(node.value,node.parent.value)) {
                long t=node.value;node.value=node.parent.value;node.parent.value=t;
                node=node.parent;
            }
        }
        long remove() {
            long out=element();
            if(size==1) { root=null;size=0;return out; }
            Node last=at(size);
            root.value=last.value;
            if((size&1)==0) last.parent.left=null; else last.parent.right=null;
            size--;
            Node node=root;
            while(node.left!=null) {
                Node child=node.left;
                if(node.right!=null && precedes(node.right.value,child.value)) child=node.right;
                if(!precedes(child.value,node.value)) break;
                long t=node.value;node.value=child.value;child.value=t;node=child;
            }
            return out;
        }
    }
}
