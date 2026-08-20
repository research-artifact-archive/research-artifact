package ltsa.updatingControllers.otf;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.Comparator;
import java.util.Deque;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

/**
 * Solver-neutral lazy baseline for finite strong-reachability games.
 *
 * <p>The baseline consumes only safety, Goal, controllability, candidate and
 * complete successor queries from {@link ImplicitStrongGame}.  It deliberately
 * ignores update-action classification and every state-dependent exploration
 * hint.  Its control flow is independent of {@link OtfDucsSynthesizer}: it
 * incrementally materialises action buckets and recomputes a standard least
 * strong-attractor fixed point after each batched expansion epoch.</p>
 *
 * <p>All uncontrollable candidates at a state are queried before the state may
 * enter the attractor.  If none is enabled, controllable buckets are queried
 * in a stable domain-separated SHA-256 order over opaque IDs until one proves
 * winning or all have been exhausted.  The order never gives lexical priority
 * to names such as {@code reconfigure}.  Thus an early winning answer is sound,
 * while a losing answer is
 * returned only after the relevant reachable game has been exhausted.</p>
 *
 * <p>The game must expose immutable state and action objects whose
 * {@code String.valueOf} representations are unique and stable for the life of
 * the solver.  The production adapter satisfies this condition with canonical
 * state IDs and action strings.  Digests are cached, so mutating an ID after it
 * is first observed is outside this baseline's contract.</p>
 */
public final class GenericLazyStrongSolver<Q, A, G> {

    private final ImplicitStrongGame<Q, A, G> game;
    private final Comparator<A> neutralActionOrder;
    private final Comparator<Q> neutralStateOrder;
    private final Map<A, byte[]> actionOrderDigests =
            new LinkedHashMap<A, byte[]>();
    private final Map<Q, byte[]> stateOrderDigests =
            new LinkedHashMap<Q, byte[]>();

    private final Set<Q> known = new LinkedHashSet<Q>();
    private final Deque<Q> scanQueue = new ArrayDeque<Q>();
    private final Set<Q> queued = new HashSet<Q>();
    private final Set<Q> scanned = new LinkedHashSet<Q>();
    private final Map<Q, Map<A, Set<Q>>> enabledBuckets =
            new LinkedHashMap<Q, Map<A, Set<Q>>>();
    private final Map<Q, List<A>> enabledUncontrollable =
            new LinkedHashMap<Q, List<A>>();
    private final Map<Q, Deque<A>> deferredControllable =
            new LinkedHashMap<Q, Deque<A>>();

    private long queriedPairs;
    private long materializedOutcomes;
    private long peakQueue;
    private long deferredCandidates;
    private long resumedCandidates;
    private long fixedPointStateInspections;
    private long fixedPointComputations;

    public GenericLazyStrongSolver(ImplicitStrongGame<Q, A, G> game) {
        if (game == null) {
            throw new IllegalArgumentException("game must not be null");
        }
        this.game = game;
        this.neutralActionOrder = stableOpaqueHashOrder(
                "action", actionOrderDigests);
        this.neutralStateOrder = stableOpaqueHashOrder(
                "state", stateOrderDigests);
    }

    public OtfDucsResult<Q, A, G> synthesize() {
        Set<Q> roots = game.initialStates();
        if (roots == null || roots.isEmpty()) {
            throw new IllegalArgumentException(
                    "Generic lazy solving requires at least one initial state");
        }
        for (Q root : sortedStates(roots)) {
            discover(root);
        }

        Map<Q, Integer> ranks = Collections.emptyMap();
        while (true) {
            while (!scanQueue.isEmpty()) {
                Q state = scanQueue.removeFirst();
                queued.remove(state);
                scan(state);
            }
            ranks = computeAttractor();
            if (ranks.keySet().containsAll(roots)) {
                break;
            }
            if (!resumeControllableBatch(ranks)) {
                break;
            }
        }

        boolean winning = ranks.keySet().containsAll(roots);
        boolean early = winning
                && (!scanQueue.isEmpty() || hasDeferredCandidates());
        OtfDucsResult.Statistics statistics =
                new OtfDucsResult.Statistics(
                        known.size(),
                        scanned.size(),
                        queriedPairs,
                        materializedOutcomes,
                        0L,
                        peakQueue,
                        early,
                        false,
                        false,
                        0L,
                        peakQueue,
                        true,
                        deferredCandidates,
                        resumedCandidates,
                        deferredCandidates - resumedCandidates,
                        fixedPointStateInspections,
                        fixedPointComputations);
        if (winning) {
            return OtfDucsResult.winning(
                    extractWinningCertificate(roots, ranks), statistics);
        }
        LinkedHashSet<Q> losing = new LinkedHashSet<Q>(known);
        losing.removeAll(ranks.keySet());
        return OtfDucsResult.losing(
                new OtfDucsResult.LosingCertificate<Q>(losing), statistics);
    }

    private void scan(Q state) {
        if (!scanned.add(state) || !game.isSafe(state)
                || game.isGoal(state)) {
            return;
        }
        Collection<A> rawCandidates = game.candidateActions(state);
        if (rawCandidates == null) {
            throw new IllegalStateException(
                    "candidate oracle returned null for " + state);
        }
        List<A> candidates = sortedActions(rawCandidates);
        List<A> uncontrollable = new ArrayList<A>();
        Deque<A> controllable = new ArrayDeque<A>();
        for (A action : candidates) {
            if (game.isControllable(action)) {
                controllable.addLast(action);
            } else {
                uncontrollable.add(action);
            }
        }

        List<A> enabledUncontrollableActions = new ArrayList<A>();
        for (A action : uncontrollable) {
            if (query(state, action)) {
                enabledUncontrollableActions.add(action);
            }
        }
        enabledUncontrollable.put(
                state,
                Collections.unmodifiableList(
                        enabledUncontrollableActions));
        if (!enabledUncontrollableActions.isEmpty()) {
            return;
        }

        while (!controllable.isEmpty()) {
            A action = controllable.removeFirst();
            if (query(state, action)) {
                break;
            }
        }
        if (!controllable.isEmpty()) {
            deferredControllable.put(state, controllable);
            deferredCandidates += controllable.size();
        }
    }

    /**
     * Resume at most one further enabled controllable bucket per currently
     * losing state, skipping disabled candidates.  Batching is the standard
     * fixed-point granularity for the neutral baseline: it avoids charging a
     * full global attractor recomputation to every individual oracle query,
     * while retaining lazy candidate materialisation.
     */
    private boolean resumeControllableBatch(Map<Q, Integer> ranks) {
        boolean queried = false;
        List<Q> states = sortedStates(deferredControllable.keySet());
        for (Q state : states) {
            if (ranks.containsKey(state)) {
                deferredControllable.remove(state);
                continue;
            }
            Deque<A> actions = deferredControllable.get(state);
            while (actions != null && !actions.isEmpty()) {
                A action = actions.removeFirst();
                resumedCandidates++;
                queried = true;
                boolean enabled = query(state, action);
                if (actions.isEmpty()) {
                    deferredControllable.remove(state);
                }
                if (enabled) {
                    break;
                }
            }
            if (actions == null || actions.isEmpty()) {
                deferredControllable.remove(state);
            }
        }
        return queried;
    }

    private boolean query(Q state, A action) {
        queriedPairs++;
        Set<Q> raw = game.post(state, action);
        if (raw == null) {
            throw new IllegalStateException(
                    "successor oracle returned null: "
                            + state + " / " + action);
        }
        if (raw.isEmpty()) {
            return false;
        }
        LinkedHashSet<Q> outcomes =
                new LinkedHashSet<Q>(sortedStates(raw));
        materializedOutcomes += outcomes.size();
        Map<A, Set<Q>> byAction = enabledBuckets.get(state);
        if (byAction == null) {
            byAction = new LinkedHashMap<A, Set<Q>>();
            enabledBuckets.put(state, byAction);
        }
        byAction.put(action, Collections.unmodifiableSet(outcomes));
        for (Q outcome : outcomes) {
            discover(outcome);
        }
        return true;
    }

    private void discover(Q state) {
        if (state == null || !game.isStructurallyValid(state)) {
            throw new IllegalStateException(
                    "successor oracle produced a non-canonical state: "
                            + state);
        }
        if (known.add(state) && queued.add(state)) {
            scanQueue.addLast(state);
            peakQueue = Math.max(peakQueue, scanQueue.size());
        }
    }

    private Map<Q, Integer> computeAttractor() {
        fixedPointComputations++;
        List<Q> orderedKnown = sortedStates(known);
        LinkedHashMap<Q, Integer> ranks =
                new LinkedHashMap<Q, Integer>();
        for (Q state : orderedKnown) {
            if (game.isSafe(state) && game.isGoal(state)) {
                ranks.put(state, Integer.valueOf(0));
            }
        }

        boolean changed;
        do {
            changed = false;
            for (Q state : orderedKnown) {
                if (ranks.containsKey(state) || !scanned.contains(state)
                        || !game.isSafe(state) || game.isGoal(state)) {
                    continue;
                }
                fixedPointStateInspections++;
                int predecessorMaximum = predecessorMaximum(state, ranks);
                if (predecessorMaximum >= 0) {
                    ranks.put(
                            state,
                            Integer.valueOf(predecessorMaximum + 1));
                    changed = true;
                }
            }
        } while (changed);
        return ranks;
    }

    private int predecessorMaximum(
            Q state,
            Map<Q, Integer> ranks) {
        List<A> uncontrollable = enabledUncontrollable.get(state);
        if (uncontrollable == null) {
            return -1;
        }
        Map<A, Set<Q>> byAction = enabledBuckets.get(state);
        if (!uncontrollable.isEmpty()) {
            int maximum = -1;
            for (A action : uncontrollable) {
                int bucketMaximum = bucketMaximum(byAction.get(action), ranks);
                if (bucketMaximum < 0) {
                    return -1;
                }
                maximum = Math.max(maximum, bucketMaximum);
            }
            return maximum;
        }

        int best = Integer.MAX_VALUE;
        if (byAction != null) {
            for (Map.Entry<A, Set<Q>> entry : byAction.entrySet()) {
                A action = entry.getKey();
                if (!game.isControllable(action)) {
                    continue;
                }
                int bucketMaximum = bucketMaximum(
                        entry.getValue(), ranks);
                if (bucketMaximum >= 0) {
                    best = Math.min(best, bucketMaximum);
                }
            }
        }
        return best == Integer.MAX_VALUE ? -1 : best;
    }

    private int bucketMaximum(
            Set<Q> outcomes,
            Map<Q, Integer> ranks) {
        if (outcomes == null || outcomes.isEmpty()) {
            return -1;
        }
        int maximum = -1;
        for (Q outcome : outcomes) {
            Integer rank = ranks.get(outcome);
            if (rank == null) {
                return -1;
            }
            maximum = Math.max(maximum, rank.intValue());
        }
        return maximum;
    }

    private OtfDucsResult.WinningCertificate<Q, A, G>
            extractWinningCertificate(
                    Set<Q> roots,
                    Map<Q, Integer> ranks) {
        LinkedHashMap<Q, Integer> reachableRanks =
                new LinkedHashMap<Q, Integer>();
        LinkedHashMap<Q, Map<A, Set<Q>>> strategy =
                new LinkedHashMap<Q, Map<A, Set<Q>>>();
        LinkedHashMap<Q, G> goalMatches =
                new LinkedHashMap<Q, G>();
        Deque<Q> work = new ArrayDeque<Q>(sortedStates(roots));
        Set<Q> reached = new LinkedHashSet<Q>();
        while (!work.isEmpty()) {
            Q state = work.removeFirst();
            if (!reached.add(state)) {
                continue;
            }
            Integer sourceRank = ranks.get(state);
            if (sourceRank == null) {
                throw new IllegalStateException(
                        "winning extraction reached an unranked state: "
                                + state);
            }
            reachableRanks.put(state, sourceRank);
            if (game.isGoal(state)) {
                goalMatches.put(state, game.goalMatch(state));
                continue;
            }

            LinkedHashMap<A, Set<Q>> retained =
                    new LinkedHashMap<A, Set<Q>>();
            List<A> uncontrollable = enabledUncontrollable.get(state);
            Map<A, Set<Q>> byAction = enabledBuckets.get(state);
            if (uncontrollable != null && !uncontrollable.isEmpty()) {
                for (A action : uncontrollable) {
                    retain(action, byAction.get(action), retained, work);
                }
            } else {
                A chosen = chooseWinningControllable(
                        state, byAction, ranks, sourceRank.intValue());
                retain(chosen, byAction.get(chosen), retained, work);
            }
            strategy.put(state, retained);
        }
        return new OtfDucsResult.WinningCertificate<Q, A, G>(
                new LinkedHashSet<Q>(roots),
                reachableRanks,
                strategy,
                goalMatches);
    }

    private A chooseWinningControllable(
            Q state,
            Map<A, Set<Q>> byAction,
            Map<Q, Integer> ranks,
            int sourceRank) {
        if (byAction != null) {
            for (Map.Entry<A, Set<Q>> entry : byAction.entrySet()) {
                A action = entry.getKey();
                if (game.isControllable(action)) {
                    int maximum = bucketMaximum(
                            entry.getValue(), ranks);
                    if (maximum >= 0 && maximum < sourceRank) {
                        return action;
                    }
                }
            }
        }
        throw new IllegalStateException(
                "winning controllable state has no rank-decreasing bucket: "
                        + state);
    }

    private void retain(
            A action,
            Set<Q> outcomes,
            Map<A, Set<Q>> retained,
            Deque<Q> work) {
        if (action == null || outcomes == null || outcomes.isEmpty()) {
            throw new IllegalStateException(
                    "winning strategy contains an empty action bucket");
        }
        retained.put(action, outcomes);
        for (Q outcome : outcomes) {
            work.addLast(outcome);
        }
    }

    private boolean hasDeferredCandidates() {
        for (Deque<A> actions : deferredControllable.values()) {
            if (actions != null && !actions.isEmpty()) {
                return true;
            }
        }
        return false;
    }

    private List<A> sortedActions(Collection<A> actions) {
        LinkedHashSet<A> unique = new LinkedHashSet<A>(actions);
        List<A> result = new ArrayList<A>(unique);
        Collections.sort(result, neutralActionOrder);
        return result;
    }

    private List<Q> sortedStates(Collection<Q> states) {
        LinkedHashSet<Q> unique = new LinkedHashSet<Q>(states);
        List<Q> result = new ArrayList<Q>(unique);
        Collections.sort(result, neutralStateOrder);
        return result;
    }

    /**
     * Orders opaque IDs by a fixed, domain-separated SHA-256 digest without
     * consulting game-specific action/state hints or lexical label prefixes.
     * Production actions are unique strings and canonical states have unique,
     * deterministic textual IDs.  A digest collision fails closed rather than
     * silently falling back to a typed or lexicographic comparator.
     */
    private static <T> Comparator<T> stableOpaqueHashOrder(
            final String kind,
            final Map<T, byte[]> digestCache) {
        return new Comparator<T>() {
            @Override
            public int compare(T left, T right) {
                if (left == right || (left != null && left.equals(right))) {
                    return 0;
                }
                if (left == null || right == null) {
                    throw new IllegalArgumentException(
                            "generic lazy " + kind + " IDs must not be null");
                }
                String leftId = String.valueOf(left);
                String rightId = String.valueOf(right);
                int comparison = compareUnsigned(
                        cachedOpaqueDigest(kind, left, leftId, digestCache),
                        cachedOpaqueDigest(kind, right, rightId, digestCache));
                if (comparison == 0) {
                    throw new IllegalArgumentException(
                            "generic lazy opaque-ID digest collision for "
                                    + kind + ": " + leftId + " / " + rightId);
                }
                return comparison;
            }
        };
    }

    private static <T> byte[] cachedOpaqueDigest(
            String kind,
            T value,
            String identifier,
            Map<T, byte[]> cache) {
        byte[] result = cache.get(value);
        if (result == null) {
            result = opaqueDigest(kind, identifier);
            cache.put(value, result);
        }
        return result;
    }

    private static byte[] opaqueDigest(String kind, String identifier) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            digest.update(
                    "fse2027-generic-lazy-order-v1\u0000".getBytes(
                            StandardCharsets.UTF_8));
            digest.update(kind.getBytes(StandardCharsets.UTF_8));
            digest.update((byte) 0);
            digest.update(identifier.getBytes(StandardCharsets.UTF_8));
            return digest.digest();
        } catch (NoSuchAlgorithmException error) {
            throw new IllegalStateException("SHA-256 is unavailable", error);
        }
    }

    private static int compareUnsigned(byte[] left, byte[] right) {
        for (int index = 0; index < left.length; index++) {
            int difference = (left[index] & 0xff) - (right[index] & 0xff);
            if (difference != 0) {
                return difference;
            }
        }
        return left.length - right.length;
    }
}
