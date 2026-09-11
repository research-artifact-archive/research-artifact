import java.util.Comparator;
import java.util.PriorityQueue;

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
    private final PriorityQueue<Long> high = new PriorityQueue<>();
    private final PriorityQueue<Long> low = new PriorityQueue<>(Comparator.reverseOrder());
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
        if ((long) high.size() < k) return Math.addExact(topSum, weight);
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
        if ((long) high.size() < k) {
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
        return new State(k, ell, topSum, (long) high.size() + low.size(),
                         k > 0 && (long) high.size() == k ? high.peek() : null);
    }
}
