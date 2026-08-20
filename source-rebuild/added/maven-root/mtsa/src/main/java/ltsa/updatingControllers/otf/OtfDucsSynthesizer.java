package ltsa.updatingControllers.otf;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.Comparator;
import java.util.Deque;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Exact interleaved OTF-DUCS implementation of Algorithms 1--3 in the revised
 * paper.  It assumes no fairness: every retained mid-mode edge must strictly
 * decrease a natural-number rank.
 */
public final class OtfDucsSynthesizer<Q, A, G> {

    /*
     * Algorithms 1--3 are the default implementation used by the paper.
     * The optional depth-first guided witness is an experimental variant and
     * must be enabled explicitly with both system properties.
     */
    private static final int DEFAULT_GUIDED_STATE_LIMIT = 0;
    private static final int DEFAULT_GUIDED_QUERY_LIMIT = 0;

    private final ImplicitStrongGame<Q, A, G> game;
    private final Comparator<A> actionOrder;
    private final int guidedStateLimit;
    private final int guidedQueryLimit;
    private final boolean lazyControllableBuckets;

    private final Set<Q> known = new LinkedHashSet<Q>();
    private final Set<Q> expanded = new LinkedHashSet<Q>();
    private final Deque<Q> frontier = new ArrayDeque<Q>();
    private final Set<Q> inFrontier = new HashSet<Q>();
    private final Set<Q> winning = new LinkedHashSet<Q>();
    private final Map<Q, Integer> rank = new LinkedHashMap<Q, Integer>();

    /** Sparse event-bucketed successors D(q,a). */
    private final Map<Q, Map<A, Set<Q>>> successors = new LinkedHashMap<Q, Map<A, Set<Q>>>();
    /** Event-labelled reverse incidences R(y). */
    private final Map<Q, Set<ActionKey<Q, A>>> reverse = new HashMap<Q, Set<ActionKey<Q, A>>>();
    private final Map<ActionKey<Q, A>, Integer> remaining = new HashMap<ActionKey<Q, A>, Integer>();
    private final Map<ActionKey<Q, A>, Integer> maximumWinningRank = new HashMap<ActionKey<Q, A>, Integer>();
    private final Map<Q, Set<A>> uncontrollableBuckets = new HashMap<Q, Set<A>>();
    private final Map<Q, Integer> openUncontrollable = new HashMap<Q, Integer>();
    private final Map<Q, A> bestControllable = new HashMap<Q, A>();
    /**
     * Controllable buckets not queried yet.  One winning controllable bucket
     * is sufficient at a state with no enabled uncontrollable action, so the
     * alternatives are opened only when the current partial graph reaches a
     * fixed point.  They are all exhausted before a losing result is returned.
     */
    private final Map<Q, Deque<A>> deferredControllableActions =
            new LinkedHashMap<Q, Deque<A>>();
    private final Deque<Q> deferredControllableStates = new ArrayDeque<Q>();
    private final Set<Q> queuedDeferredControllableStates = new HashSet<Q>();

    private long queriedStateActionPairs;
    private long materializedTransitions;
    private long propagatedIncidences;
    private long peakFrontier;
    private long deferredControllableCandidates;
    private long resumedControllableCandidates;
    private final Set<Q> guidedDiscovered = new LinkedHashSet<Q>();
    private final Set<Q> guidedExpanded = new LinkedHashSet<Q>();
    private long guidedQueriedStateActionPairs;
    private long guidedMaterializedTransitions;
    private long guidedMaximumDepth;
    private boolean guidedFallbackUsed;

    public OtfDucsSynthesizer(ImplicitStrongGame<Q, A, G> game) {
        this(game,
                Integer.getInteger(
                        "mtsa.otf.guidedStateLimit",
                        DEFAULT_GUIDED_STATE_LIMIT).intValue(),
                Integer.getInteger(
                        "mtsa.otf.guidedQueryLimit",
                        DEFAULT_GUIDED_QUERY_LIMIT).intValue(),
                Boolean.parseBoolean(System.getProperty(
                        "mtsa.otf.lazyControllableBuckets", "true")));
    }

    OtfDucsSynthesizer(
            ImplicitStrongGame<Q, A, G> game,
            int guidedStateLimit,
            int guidedQueryLimit) {
        this(game, guidedStateLimit, guidedQueryLimit, true);
    }

    OtfDucsSynthesizer(
            ImplicitStrongGame<Q, A, G> game,
            int guidedStateLimit,
            int guidedQueryLimit,
            boolean lazyControllableBuckets) {
        if (game == null) {
            throw new IllegalArgumentException("game must not be null");
        }
        if (guidedStateLimit < 0 || guidedQueryLimit < 0) {
            throw new IllegalArgumentException(
                    "guided search limits must be non-negative");
        }
        this.game = game;
        this.guidedStateLimit = guidedStateLimit;
        this.guidedQueryLimit = guidedQueryLimit;
        this.lazyControllableBuckets = lazyControllableBuckets;
        this.actionOrder = new Comparator<A>() {
            @Override
            public int compare(A left, A right) {
                boolean leftUpdate = OtfDucsSynthesizer.this.game.isUpdateAction(left);
                boolean rightUpdate = OtfDucsSynthesizer.this.game.isUpdateAction(right);
                if (leftUpdate != rightUpdate) {
                    return leftUpdate ? -1 : 1;
                }
                return OtfDucsSynthesizer.this.game.actionComparator().compare(left, right);
            }
        };
    }

    public OtfDucsResult<Q, A, G> synthesize() {
        if (game.initialStates() == null || game.initialStates().isEmpty()) {
            throw new IllegalArgumentException(
                    "OTF-DUCS requires at least one hotSwapIn embedding.");
        }
        OtfDucsResult<Q, A, G> guided = tryGuidedWinningProof();
        if (guided != null) {
            return guided;
        }
        initializeRoots();

        while (!winning.containsAll(game.initialStates())) {
            if (frontier.isEmpty()) {
                if (!advanceDeferredControllableAction()) {
                    break;
                }
                continue;
            }

            Q state = frontier.removeLast();
            inFrontier.remove(state);
            if (!expanded.add(state)) {
                continue;
            }

            Deque<Q> newlyWinning = new ArrayDeque<Q>();
            expand(state);
            initializeActionCounters(state);
            if (isReady(state)) {
                promote(state, newlyWinning);
            }
            propagate(newlyWinning);
        }

        boolean success = winning.containsAll(game.initialStates());
        boolean early = success
                && (!frontier.isEmpty() || hasDeferredControllableActions());
        OtfDucsResult.Statistics stats = new OtfDucsResult.Statistics(
                unionSize(guidedDiscovered, known),
                unionSize(guidedExpanded, expanded),
                guidedQueriedStateActionPairs + queriedStateActionPairs,
                guidedMaterializedTransitions + materializedTransitions,
                propagatedIncidences,
                Math.max(guidedMaximumDepth, peakFrontier),
                early,
                false,
                guidedFallbackUsed,
                guidedMaximumDepth,
                peakFrontier,
                lazyControllableBuckets,
                deferredControllableCandidates,
                resumedControllableCandidates,
                deferredControllableCandidates
                        - resumedControllableCandidates,
                0L,
                0L);

        if (success) {
            return OtfDucsResult.winning(extractCertificate(), stats);
        }

        // Failure is returned only after exhaustion of every reachable safe non-Goal state.
        Set<Q> losing = new LinkedHashSet<Q>(known);
        losing.removeAll(winning);
        return OtfDucsResult.losing(new OtfDucsResult.LosingCertificate<Q>(losing), stats);
    }

    /**
     * Tries to construct a small acyclic strong policy before materialising the
     * complete attractor graph.  This is a witness search, not a decision
     * shortcut: failure falls back to the complete algorithm, while success is
     * accepted only after the ordinary independent certificate checker passes.
     */
    private OtfDucsResult<Q, A, G> tryGuidedWinningProof() {
        // Zero is the documented switch for the proof/evaluation protocol that
        // runs the complete attractor alone.  Do not record a vacuous guided
        // attempt as a fallback in that configuration.
        if (guidedStateLimit == 0 || guidedQueryLimit == 0) {
            return null;
        }
        GuidedProofSearch search = new GuidedProofSearch();
        try {
            if (!search.proveEveryRoot()) {
                accumulateGuidedAttempt(search);
                return null;
            }
        } catch (GuidedSearchLimitExceeded limit) {
            accumulateGuidedAttempt(search);
            return null;
        }
        OtfDucsResult.WinningCertificate<Q, A, G> certificate =
                search.extractReachableCertificate();
        OtfDucsCertificateChecker.VerificationReport verification =
                new OtfDucsCertificateChecker<Q, A, G>(game)
                        .verifyWinning(certificate);
        if (!verification.isValid()) {
            accumulateGuidedAttempt(search);
            return null;
        }
        OtfDucsResult.Statistics statistics = new OtfDucsResult.Statistics(
                search.discovered.size(),
                search.expanded.size(),
                search.queriedPairs,
                search.transitions,
                0L,
                search.maximumDepth,
                true,
                true,
                false,
                search.maximumDepth,
                0L,
                lazyControllableBuckets,
                0L,
                0L,
                0L,
                0L,
                0L);
        return OtfDucsResult.winning(certificate, statistics);
    }

    private final class GuidedProofSearch {
        private final Set<Q> discovered = new LinkedHashSet<Q>();
        private final Set<Q> expanded = new LinkedHashSet<Q>();
        private final Map<Q, Integer> ranks = new LinkedHashMap<Q, Integer>();
        private final Map<Q, Map<A, Set<Q>>> policy =
                new LinkedHashMap<Q, Map<A, Set<Q>>>();
        private final Map<Q, G> matches = new LinkedHashMap<Q, G>();
        private long queriedPairs;
        private long transitions;
        private long maximumDepth;

        private boolean proveEveryRoot() {
            List<Q> roots = sortedStates(game.initialStates());
            discovered.addAll(roots);
            if (discovered.size() > guidedStateLimit) {
                throw new GuidedSearchLimitExceeded();
            }
            for (Q root : roots) {
                requireCanonical(root);
                if (!prove(root, new LinkedHashSet<Q>(), 1L)) {
                    return false;
                }
            }
            return true;
        }

        private boolean prove(Q state, Set<Q> visiting, long depth) {
            if (ranks.containsKey(state)) {
                return true;
            }
            maximumDepth = Math.max(maximumDepth, depth);
            if (!game.isSafe(state) || !visiting.add(state)) {
                return false;
            }
            if (game.isGoal(state)) {
                ranks.put(state, Integer.valueOf(0));
                matches.put(state, game.goalMatch(state));
                visiting.remove(state);
                return true;
            }

            expanded.add(state);
            List<A> candidates = uniqueSortedActions(
                    state, game.candidateActions(state));
            List<GuidedBucket> uncontrollable =
                    materializeGuidedBuckets(state, candidates, false);
            if (!uncontrollable.isEmpty()) {
                int maximum = proveAll(uncontrollable, visiting, depth);
                visiting.remove(state);
                if (maximum < 0) {
                    return false;
                }
                ranks.put(state, Integer.valueOf(maximum + 1));
                policy.put(state, guidedPolicy(uncontrollable));
                return true;
            }

            List<GuidedBucket> controllable =
                    materializeGuidedBuckets(state, candidates, true);
            for (GuidedBucket bucket : controllable) {
                int maximum = proveAll(
                        Collections.singletonList(bucket), visiting, depth);
                if (maximum < 0) {
                    continue;
                }
                visiting.remove(state);
                ranks.put(state, Integer.valueOf(maximum + 1));
                policy.put(state, guidedPolicy(
                        Collections.singletonList(bucket)));
                return true;
            }
            visiting.remove(state);
            return false;
        }

        private int proveAll(
                List<GuidedBucket> buckets,
                Set<Q> visiting,
                long depth) {
            int maximum = -1;
            for (GuidedBucket bucket : buckets) {
                for (Q target : bucket.outcomes) {
                    if (!prove(target, visiting, depth + 1L)) {
                        return -1;
                    }
                    maximum = Math.max(
                            maximum, ranks.get(target).intValue());
                }
            }
            return maximum;
        }

        private List<GuidedBucket> materializeGuidedBuckets(
                final Q state,
                List<A> candidates,
                boolean controllable) {
            List<GuidedBucket> result = new ArrayList<GuidedBucket>();
            for (A action : candidates) {
                if (game.isControllable(action) != controllable) {
                    continue;
                }
                if (queriedPairs >= guidedQueryLimit) {
                    throw new GuidedSearchLimitExceeded();
                }
                queriedPairs++;
                Set<Q> raw = game.post(state, action);
                if (raw == null || raw.isEmpty()) {
                    continue;
                }
                List<Q> ordered = sortedStates(raw);
                LinkedHashSet<Q> outcomes = new LinkedHashSet<Q>(ordered);
                transitions += outcomes.size();
                for (Q outcome : outcomes) {
                    requireCanonical(outcome);
                    if (discovered.add(outcome)
                            && discovered.size() > guidedStateLimit) {
                        throw new GuidedSearchLimitExceeded();
                    }
                }
                result.add(new GuidedBucket(action, outcomes, ordered.get(0)));
            }

            final boolean updateFirst = game.preferUpdateActions(state);
            final Map<A, Integer> priorities = new LinkedHashMap<A, Integer>();
            for (GuidedBucket bucket : result) {
                priorities.put(
                        bucket.action,
                        Integer.valueOf(game.explorationActionPriority(
                                state, bucket.action)));
            }
            Collections.sort(result, new Comparator<GuidedBucket>() {
                @Override
                public int compare(GuidedBucket left, GuidedBucket right) {
                    int comparison = Integer.compare(
                            priorities.get(left.action).intValue(),
                            priorities.get(right.action).intValue());
                    if (comparison != 0) {
                        return comparison;
                    }
                    boolean leftUpdate = game.isUpdateAction(left.action);
                    boolean rightUpdate = game.isUpdateAction(right.action);
                    if (leftUpdate != rightUpdate) {
                        return leftUpdate == updateFirst ? -1 : 1;
                    }
                    comparison = game.stateComparator().compare(
                            left.bestOutcome, right.bestOutcome);
                    return comparison != 0
                            ? comparison
                            : game.actionComparator().compare(
                                    left.action, right.action);
                }
            });
            return result;
        }

        private Map<A, Set<Q>> guidedPolicy(List<GuidedBucket> buckets) {
            Map<A, Set<Q>> retained = new LinkedHashMap<A, Set<Q>>();
            for (GuidedBucket bucket : buckets) {
                retained.put(bucket.action, bucket.outcomes);
            }
            return retained;
        }

        private OtfDucsResult.WinningCertificate<Q, A, G>
                extractReachableCertificate() {
            Map<Q, Integer> reachableRanks =
                    new LinkedHashMap<Q, Integer>();
            Map<Q, Map<A, Set<Q>>> reachablePolicy =
                    new LinkedHashMap<Q, Map<A, Set<Q>>>();
            Map<Q, G> reachableMatches = new LinkedHashMap<Q, G>();
            Deque<Q> work = new ArrayDeque<Q>(sortedStates(game.initialStates()));
            Set<Q> seen = new LinkedHashSet<Q>();
            while (!work.isEmpty()) {
                Q state = work.removeFirst();
                if (!seen.add(state)) {
                    continue;
                }
                reachableRanks.put(state, ranks.get(state));
                if (game.isGoal(state)) {
                    reachableMatches.put(state, matches.get(state));
                    continue;
                }
                Map<A, Set<Q>> retained = policy.get(state);
                reachablePolicy.put(state, retained);
                for (Set<Q> outcomes : retained.values()) {
                    work.addAll(sortedStates(outcomes));
                }
            }
            return new OtfDucsResult.WinningCertificate<Q, A, G>(
                    game.initialStates(),
                    reachableRanks,
                    reachablePolicy,
                    reachableMatches);
        }

        private final class GuidedBucket {
            private final A action;
            private final Set<Q> outcomes;
            private final Q bestOutcome;

            private GuidedBucket(A action, Set<Q> outcomes, Q bestOutcome) {
                this.action = action;
                this.outcomes = outcomes;
                this.bestOutcome = bestOutcome;
            }
        }
    }

    private void accumulateGuidedAttempt(GuidedProofSearch search) {
        guidedFallbackUsed = true;
        guidedDiscovered.addAll(search.discovered);
        guidedExpanded.addAll(search.expanded);
        guidedQueriedStateActionPairs += search.queriedPairs;
        guidedMaterializedTransitions += search.transitions;
        guidedMaximumDepth = Math.max(
                guidedMaximumDepth, search.maximumDepth);
    }

    private long unionSize(Set<Q> left, Set<Q> right) {
        if (left.isEmpty()) {
            return right.size();
        }
        Set<Q> union = new HashSet<Q>(left);
        union.addAll(right);
        return union.size();
    }

    private static final class GuidedSearchLimitExceeded
            extends RuntimeException {
        private static final long serialVersionUID = 1L;
    }

    private void initializeRoots() {
        if (game.initialStates() == null || game.initialStates().isEmpty()) {
            throw new IllegalArgumentException("OTF-DUCS requires at least one hotSwapIn embedding.");
        }
        List<Q> roots = sortedStates(game.initialStates());
        for (int index = roots.size() - 1; index >= 0; index--) {
            Q root = roots.get(index);
            requireCanonical(root);
            known.add(root);
            if (game.isSafe(root) && game.isGoal(root)) {
                winning.add(root);
                rank.put(root, Integer.valueOf(0));
            } else if (game.isSafe(root)) {
                addToFrontier(root);
            }
        }
    }

    private void expand(Q state) {
        Map<A, Set<Q>> byAction = new LinkedHashMap<A, Set<Q>>();
        successors.put(state, byAction);

        List<A> actions = uniqueSortedActions(
                state, game.candidateActions(state));
        List<A> uncontrollableActions = new ArrayList<A>();
        List<A> controllableActions = new ArrayList<A>();
        for (A action : actions) {
            if (game.isControllable(action)) {
                controllableActions.add(action);
            } else {
                uncontrollableActions.add(action);
            }
        }
        List<Q> newlyDiscoveredSafeNonGoals = new ArrayList<Q>();
        Set<Q> newlyQueued = new HashSet<Q>();

        /*
         * Under the strong supervisory-game policy used by Ready, Extract and
         * the independent checker, an enabled uncontrollable bucket pre-empts
         * every controllable choice at the same state.  Materialising those
         * controllable branches cannot affect the winning region or either
         * certificate, but can create the complete 2^K update-phase product
         * while a physical completion event is pending.
         */
        boolean hasEnabledUncontrollable = materializeActions(
                state, uncontrollableActions, byAction,
                newlyDiscoveredSafeNonGoals, newlyQueued);
        if (!hasEnabledUncontrollable) {
            if (lazyControllableBuckets) {
                materializeFirstEnabledControllable(
                        state, controllableActions, byAction,
                        newlyDiscoveredSafeNonGoals, newlyQueued);
            } else {
                materializeActions(
                        state, controllableActions, byAction,
                        newlyDiscoveredSafeNonGoals, newlyQueued);
            }
        }

        /*
         * Order discoveries globally rather than letting the first action name
         * dominate all outcomes.  The game comparator may supply an exact
         * endpoint-distance hint; this remains a pure exploration order.
         */
        Collections.sort(newlyDiscoveredSafeNonGoals, game.stateComparator());
        // Frontier is LIFO. Reverse insertion makes the least state pop first.
        for (int i = newlyDiscoveredSafeNonGoals.size() - 1; i >= 0; i--) {
            addToFrontier(newlyDiscoveredSafeNonGoals.get(i));
        }
    }

    private void materializeFirstEnabledControllable(
            Q state,
            List<A> actions,
            Map<A, Set<Q>> byAction,
            List<Q> newlyDiscoveredSafeNonGoals,
            Set<Q> newlyQueued) {
        for (int index = 0; index < actions.size(); index++) {
            A action = actions.get(index);
            if (!materializeAction(
                    state, action, byAction,
                    newlyDiscoveredSafeNonGoals, newlyQueued)) {
                continue;
            }
            if (index + 1 < actions.size()) {
                Deque<A> deferred = new ArrayDeque<A>();
                for (int remainingIndex = index + 1;
                        remainingIndex < actions.size();
                        remainingIndex++) {
                    deferred.addLast(actions.get(remainingIndex));
                }
                deferredControllableCandidates += deferred.size();
                deferredControllableActions.put(state, deferred);
                queueDeferredControllableState(state);
            }
            return;
        }
    }

    private boolean materializeActions(
            Q state,
            List<A> actions,
            Map<A, Set<Q>> byAction,
            List<Q> newlyDiscoveredSafeNonGoals,
            Set<Q> newlyQueued) {
        boolean materializedAny = false;
        for (A action : actions) {
            materializedAny |= materializeAction(
                    state, action, byAction,
                    newlyDiscoveredSafeNonGoals, newlyQueued);
        }
        return materializedAny;
    }

    private boolean materializeAction(
            Q state,
            A action,
            Map<A, Set<Q>> byAction,
            List<Q> newlyDiscoveredSafeNonGoals,
            Set<Q> newlyQueued) {
        queriedStateActionPairs++;
        Set<Q> raw = game.post(state, action);
        if (raw == null || raw.isEmpty()) {
            return false;
        }
        Set<Q> outcomes = new LinkedHashSet<Q>(sortedStates(raw));
        byAction.put(action, outcomes);
        materializedTransitions += outcomes.size();

        ActionKey<Q, A> key = new ActionKey<Q, A>(state, action);
        for (Q outcome : outcomes) {
            requireCanonical(outcome);
            Set<ActionKey<Q, A>> incidences = reverse.get(outcome);
            if (incidences == null) {
                incidences = new LinkedHashSet<ActionKey<Q, A>>();
                reverse.put(outcome, incidences);
            }
            incidences.add(key);

            if (known.add(outcome)) {
                if (game.isSafe(outcome) && game.isGoal(outcome)) {
                    winning.add(outcome);
                    rank.put(outcome, Integer.valueOf(0));
                } else if (game.isSafe(outcome) && newlyQueued.add(outcome)) {
                    newlyDiscoveredSafeNonGoals.add(outcome);
                }
            }
        }
        return true;
    }

    /**
     * Opens one further controllable bucket after the current partial graph has
     * reached a fixed point.  Disabled candidates are skipped.  Returning
     * {@code false} is the proof-relevant exhaustion condition: every
     * non-winning state has then had all of its relevant buckets queried.
     */
    private boolean advanceDeferredControllableAction() {
        while (!deferredControllableStates.isEmpty()) {
            Q state = deferredControllableStates.removeFirst();
            queuedDeferredControllableStates.remove(state);
            Deque<A> deferred = deferredControllableActions.get(state);
            if (winning.contains(state)
                    || deferred == null
                    || deferred.isEmpty()) {
                deferredControllableActions.remove(state);
                continue;
            }

            Map<A, Set<Q>> byAction = successors.get(state);
            List<Q> newlyDiscoveredSafeNonGoals = new ArrayList<Q>();
            Set<Q> newlyQueued = new HashSet<Q>();
            boolean enabled = false;
            A action = null;
            while (!deferred.isEmpty() && !enabled) {
                action = deferred.removeFirst();
                resumedControllableCandidates++;
                enabled = materializeAction(
                        state, action, byAction,
                        newlyDiscoveredSafeNonGoals, newlyQueued);
            }
            if (deferred.isEmpty()) {
                deferredControllableActions.remove(state);
            } else {
                queueDeferredControllableState(state);
            }
            if (!enabled) {
                continue;
            }

            Collections.sort(
                    newlyDiscoveredSafeNonGoals, game.stateComparator());
            for (int index = newlyDiscoveredSafeNonGoals.size() - 1;
                    index >= 0;
                    index--) {
                addToFrontier(newlyDiscoveredSafeNonGoals.get(index));
            }

            int rem = initializeActionCounter(
                    state, action, byAction.get(action));
            if (rem == 0) {
                considerBest(state, action);
            }
            Deque<Q> newlyWinning = new ArrayDeque<Q>();
            if (isReady(state)) {
                promote(state, newlyWinning);
            }
            propagate(newlyWinning);
            return true;
        }
        return false;
    }

    private void queueDeferredControllableState(Q state) {
        if (queuedDeferredControllableStates.add(state)) {
            deferredControllableStates.addLast(state);
        }
    }

    private boolean hasDeferredControllableActions() {
        for (Deque<A> deferred : deferredControllableActions.values()) {
            if (!deferred.isEmpty()) {
                return true;
            }
        }
        return false;
    }

    private void initializeActionCounters(Q state) {
        Map<A, Set<Q>> byAction = successors.get(state);
        Set<A> uncontrollable = new LinkedHashSet<A>();
        int open = 0;

        for (Map.Entry<A, Set<Q>> entry : byAction.entrySet()) {
            A action = entry.getKey();
            int rem = initializeActionCounter(
                    state, action, entry.getValue());
            if (!game.isControllable(action)) {
                uncontrollable.add(action);
                if (rem > 0) {
                    open++;
                }
            }
        }

        uncontrollableBuckets.put(state, uncontrollable);
        openUncontrollable.put(state, Integer.valueOf(open));
        if (uncontrollable.isEmpty()) {
            for (Map.Entry<A, Set<Q>> entry : byAction.entrySet()) {
                if (!game.isControllable(entry.getKey())) {
                    continue;
                }
                ActionKey<Q, A> key = new ActionKey<Q, A>(state, entry.getKey());
                if (remaining.get(key).intValue() == 0) {
                    considerBest(state, entry.getKey());
                }
            }
        }
    }

    private int initializeActionCounter(
            Q state,
            A action,
            Set<Q> outcomes) {
        ActionKey<Q, A> key = new ActionKey<Q, A>(state, action);
        int rem = 0;
        int amax = -1;
        for (Q outcome : outcomes) {
            if (winning.contains(outcome)) {
                amax = Math.max(amax, rank.get(outcome).intValue());
            } else {
                rem++;
            }
        }
        remaining.put(key, Integer.valueOf(rem));
        maximumWinningRank.put(key, Integer.valueOf(amax));
        return rem;
    }

    private void propagate(Deque<Q> queue) {
        while (!queue.isEmpty()) {
            Q newlyWinning = queue.removeFirst();
            Set<ActionKey<Q, A>> incoming = reverse.get(newlyWinning);
            if (incoming == null) {
                continue;
            }
            for (ActionKey<Q, A> key : incoming) {
                Q predecessor = key.state;
                if (!expanded.contains(predecessor) || winning.contains(predecessor)) {
                    continue;
                }
                Integer remValue = remaining.get(key);
                if (remValue == null || remValue.intValue() <= 0) {
                    continue;
                }
                propagatedIncidences++;
                int rem = remValue.intValue() - 1;
                remaining.put(key, Integer.valueOf(rem));
                maximumWinningRank.put(key, Integer.valueOf(Math.max(
                        maximumWinningRank.get(key).intValue(), rank.get(newlyWinning).intValue())));
                if (rem == 0) {
                    if (!game.isControllable(key.action)) {
                        openUncontrollable.put(predecessor, Integer.valueOf(
                                openUncontrollable.get(predecessor).intValue() - 1));
                    } else if (uncontrollableBuckets.get(predecessor).isEmpty()) {
                        considerBest(predecessor, key.action);
                    }
                    if (isReady(predecessor)) {
                        promote(predecessor, queue);
                    }
                }
            }
        }
    }

    private boolean isReady(Q state) {
        if (!expanded.contains(state) || winning.contains(state) || !game.isSafe(state)) {
            return false;
        }
        Set<A> uncontrollable = uncontrollableBuckets.get(state);
        if (uncontrollable == null) {
            return false;
        }
        if (!uncontrollable.isEmpty()) {
            return openUncontrollable.get(state).intValue() == 0;
        }
        return bestControllable.containsKey(state);
    }

    private void promote(Q state, Deque<Q> queue) {
        if (winning.contains(state)) {
            return;
        }
        int evidenceMaximum = -1;
        Set<A> uncontrollable = uncontrollableBuckets.get(state);
        if (!uncontrollable.isEmpty()) {
            for (A action : uncontrollable) {
                evidenceMaximum = Math.max(evidenceMaximum,
                        maximumWinningRank.get(new ActionKey<Q, A>(state, action)).intValue());
            }
        } else {
            A action = bestControllable.get(state);
            evidenceMaximum = maximumWinningRank.get(new ActionKey<Q, A>(state, action)).intValue();
        }
        if (evidenceMaximum < 0) {
            throw new IllegalStateException("Ready state has no ranked evidence successor: " + state);
        }
        winning.add(state);
        rank.put(state, Integer.valueOf(evidenceMaximum + 1));
        queue.addLast(state);
    }

    private void considerBest(Q state, A candidate) {
        A current = bestControllable.get(state);
        if (current == null || compareWinningActions(state, candidate, current) < 0) {
            bestControllable.put(state, candidate);
        }
    }

    private int compareWinningActions(Q state, A left, A right) {
        int leftRank = maximumWinningRank.get(new ActionKey<Q, A>(state, left)).intValue();
        int rightRank = maximumWinningRank.get(new ActionKey<Q, A>(state, right)).intValue();
        int comparison = Integer.compare(leftRank, rightRank);
        return comparison != 0 ? comparison : actionOrder.compare(left, right);
    }

    private OtfDucsResult.WinningCertificate<Q, A, G> extractCertificate() {
        Map<Q, Integer> certificateRanks = new LinkedHashMap<Q, Integer>();
        Map<Q, Map<A, Set<Q>>> strategy = new LinkedHashMap<Q, Map<A, Set<Q>>>();
        Map<Q, G> goalMatches = new LinkedHashMap<Q, G>();
        Deque<Q> work = new ArrayDeque<Q>(sortedStates(game.initialStates()));
        Set<Q> seen = new LinkedHashSet<Q>();

        while (!work.isEmpty()) {
            Q state = work.removeFirst();
            if (!seen.add(state)) {
                continue;
            }
            certificateRanks.put(state, rank.get(state));
            if (game.isGoal(state)) {
                goalMatches.put(state, game.goalMatch(state));
                continue;
            }

            Map<A, Set<Q>> retained = new LinkedHashMap<A, Set<Q>>();
            Map<A, Set<Q>> byAction = successors.get(state);
            List<A> uncontrollable = new ArrayList<A>();
            for (A action : byAction.keySet()) {
                if (!game.isControllable(action)) {
                    uncontrollable.add(action);
                }
            }
            Collections.sort(uncontrollable, actionOrder);
            if (!uncontrollable.isEmpty()) {
                for (A action : uncontrollable) {
                    Set<Q> outcomes = byAction.get(action);
                    requireRankDecrease(state, outcomes);
                    retained.put(action, outcomes);
                    work.addAll(sortedStates(outcomes));
                }
            } else {
                A selected = selectExtractedControllable(state, byAction);
                Set<Q> outcomes = byAction.get(selected);
                requireRankDecrease(state, outcomes);
                retained.put(selected, outcomes);
                work.addAll(sortedStates(outcomes));
            }
            strategy.put(state, retained);
        }

        return new OtfDucsResult.WinningCertificate<Q, A, G>(
                game.initialStates(), certificateRanks, strategy, goalMatches);
    }

    private A selectExtractedControllable(Q state, Map<A, Set<Q>> byAction) {
        List<A> candidates = new ArrayList<A>();
        for (Map.Entry<A, Set<Q>> entry : byAction.entrySet()) {
            if (!game.isControllable(entry.getKey()) || entry.getValue().isEmpty()) {
                continue;
            }
            boolean lower = true;
            for (Q outcome : entry.getValue()) {
                Integer outcomeRank = rank.get(outcome);
                if (!winning.contains(outcome) || outcomeRank == null
                        || outcomeRank.intValue() >= rank.get(state).intValue()) {
                    lower = false;
                    break;
                }
            }
            if (lower) {
                candidates.add(entry.getKey());
            }
        }
        if (candidates.isEmpty()) {
            throw new IllegalStateException("Winning state has no rank-decreasing action: " + state);
        }
        Collections.sort(candidates, new Comparator<A>() {
            @Override
            public int compare(A left, A right) {
                int leftMax = maxSuccessorRank(state, byAction.get(left));
                int rightMax = maxSuccessorRank(state, byAction.get(right));
                int comparison = Integer.compare(leftMax, rightMax);
                return comparison != 0 ? comparison : actionOrder.compare(left, right);
            }
        });
        return candidates.get(0);
    }

    private int maxSuccessorRank(Q state, Set<Q> outcomes) {
        int maximum = -1;
        for (Q outcome : outcomes) {
            Integer value = rank.get(outcome);
            if (value == null) {
                throw new IllegalStateException("Unranked successor of " + state + ": " + outcome);
            }
            maximum = Math.max(maximum, value.intValue());
        }
        return maximum;
    }

    private void requireRankDecrease(Q source, Set<Q> outcomes) {
        int sourceRank = rank.get(source).intValue();
        for (Q outcome : outcomes) {
            Integer targetRank = rank.get(outcome);
            if (targetRank == null || targetRank.intValue() >= sourceRank) {
                throw new IllegalStateException("Non-decreasing certificate edge: "
                        + source + " -> " + outcome);
            }
        }
    }

    private void addToFrontier(Q state) {
        if (!expanded.contains(state) && inFrontier.add(state)) {
            frontier.addLast(state);
            peakFrontier = Math.max(peakFrontier, frontier.size());
        }
    }

    private List<A> uniqueSortedActions(final Q state, Collection<A> actions) {
        if (actions == null) {
            throw new IllegalStateException("candidateActions returned null");
        }
        List<A> result = new ArrayList<A>(new LinkedHashSet<A>(actions));
        final boolean updateFirst = game.preferUpdateActions(state);
        final Map<A, Integer> priorities = new LinkedHashMap<A, Integer>();
        for (A action : result) {
            priorities.put(
                    action,
                    Integer.valueOf(game.explorationActionPriority(
                            state, action)));
        }
        Collections.sort(result, new Comparator<A>() {
            @Override
            public int compare(A left, A right) {
                int comparison = Integer.compare(
                        priorities.get(left).intValue(),
                        priorities.get(right).intValue());
                if (comparison != 0) {
                    return comparison;
                }
                boolean leftUpdate = game.isUpdateAction(left);
                boolean rightUpdate = game.isUpdateAction(right);
                if (leftUpdate != rightUpdate) {
                    return leftUpdate == updateFirst ? -1 : 1;
                }
                return game.actionComparator().compare(left, right);
            }
        });
        return result;
    }

    private List<Q> sortedStates(Collection<Q> states) {
        List<Q> result = new ArrayList<Q>(states);
        Collections.sort(result, game.stateComparator());
        return result;
    }

    private void requireCanonical(Q state) {
        if (state == null || !game.isStructurallyValid(state)) {
            throw new IllegalStateException("Successor oracle produced a non-canonical state: " + state);
        }
    }

    private static final class ActionKey<Q, A> {
        private final Q state;
        private final A action;

        private ActionKey(Q state, A action) {
            this.state = state;
            this.action = action;
        }

        @Override
        public boolean equals(Object other) {
            if (this == other) return true;
            if (!(other instanceof ActionKey)) return false;
            ActionKey<?, ?> that = (ActionKey<?, ?>) other;
            return java.util.Objects.equals(state, that.state)
                    && java.util.Objects.equals(action, that.action);
        }

        @Override
        public int hashCode() {
            return java.util.Objects.hash(state, action);
        }
    }
}
