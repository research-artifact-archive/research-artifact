package ltsa.updatingControllers.otf;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.Comparator;
import java.util.Deque;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Matched explicit-state baseline for the revised strong OTF-DUCS game.
 *
 * <p>The baseline deliberately separates representation construction from
 * solving.  It first queries every action at every reachable safe, non-goal
 * state and stores every enabled outcome bucket.  Only after that exhaustive
 * enumeration has terminated does it compute the strong winning fixed point.
 * Consequently it uses exactly the supplied {@link ImplicitStrongGame}
 * semantics, but none of the production solver's interleaving, guided proof,
 * early termination, or lazy controllable-bucket optimisations.</p>
 *
 * <p>The returned result uses the ordinary {@link OtfDucsResult} certificate
 * format and can therefore be checked by {@link OtfDucsCertificateChecker}.
 * Baseline-specific phase and work counters are available through
 * {@link #statistics()} after synthesis.</p>
 */
public final class DirectFullStrongSolver<Q, A, G> {

    private final ImplicitStrongGame<Q, A, G> game;
    private Statistics statistics;

    public DirectFullStrongSolver(ImplicitStrongGame<Q, A, G> game) {
        if (game == null) {
            throw new IllegalArgumentException("game must not be null");
        }
        this.game = game;
    }

    public OtfDucsResult<Q, A, G> synthesize() {
        long enumerationStarted = System.nanoTime();
        ExplicitGame explicit = enumerateReachableGame();
        long enumerationFinished = System.nanoTime();

        FixedPoint fixedPoint = solveExplicitGame(explicit);
        long fixedPointFinished = System.nanoTime();

        boolean winning = fixedPoint.winning.containsAll(explicit.initialStates);
        OtfDucsResult.WinningCertificate<Q, A, G> winningCertificate = null;
        OtfDucsResult.LosingCertificate<Q> losingCertificate = null;
        if (winning) {
            winningCertificate = extractWinningCertificate(
                    explicit, fixedPoint);
        } else {
            LinkedHashSet<Q> losing = new LinkedHashSet<Q>(explicit.states);
            losing.removeAll(fixedPoint.winning);
            losingCertificate =
                    new OtfDucsResult.LosingCertificate<Q>(losing);
        }
        long certificateFinished = System.nanoTime();

        statistics = new Statistics(
                explicit.initialStates.size(),
                explicit.states.size(),
                explicit.expandedStates,
                explicit.queriedStateActionPairs,
                explicit.enabledActionBuckets,
                explicit.materializedTransitions,
                explicit.peakFrontier,
                fixedPoint.iterations,
                fixedPoint.stateInspections,
                fixedPoint.bucketInspections,
                fixedPoint.outcomeInspections,
                fixedPoint.promotedStates,
                enumerationFinished - enumerationStarted,
                fixedPointFinished - enumerationFinished,
                certificateFinished - fixedPointFinished);

        /*
         * These common counters deliberately contain only quantities having
         * the same meaning in both implementations.  Direct-Full's explicit
         * fixed-point scans are exposed separately above rather than being
         * mislabeled as OTF reverse-incidence propagation.
         */
        OtfDucsResult.Statistics commonStatistics =
                new OtfDucsResult.Statistics(
                        explicit.states.size(),
                        explicit.expandedStates,
                        explicit.queriedStateActionPairs,
                        explicit.materializedTransitions,
                        0L,
                        explicit.peakFrontier,
                        false,
                        false,
                        false,
                        0L,
                        explicit.peakFrontier,
                        false,
                        0L,
                        0L,
                        0L,
                        fixedPoint.stateInspections,
                        fixedPoint.iterations);
        return winning
                ? OtfDucsResult.winning(
                        winningCertificate, commonStatistics)
                : OtfDucsResult.losing(
                        losingCertificate, commonStatistics);
    }

    /**
     * Returns statistics for the most recent synthesis.
     *
     * @throws IllegalStateException if synthesis has not run yet
     */
    public Statistics statistics() {
        if (statistics == null) {
            throw new IllegalStateException(
                    "Direct-Full statistics are unavailable before synthesis");
        }
        return statistics;
    }

    private ExplicitGame enumerateReachableGame() {
        Set<Q> suppliedInitialStates = game.initialStates();
        if (suppliedInitialStates == null
                || suppliedInitialStates.isEmpty()) {
            throw new IllegalArgumentException(
                    "Direct-Full requires at least one hotSwapIn embedding.");
        }

        ExplicitGame explicit = new ExplicitGame();
        Deque<Q> frontier = new ArrayDeque<Q>();
        for (Q root : sortedStates(suppliedInitialStates)) {
            requireCanonical(root);
            if (explicit.states.add(root)) {
                frontier.addLast(root);
            }
        }
        explicit.initialStates.addAll(suppliedInitialStates);
        explicit.peakFrontier = frontier.size();

        while (!frontier.isEmpty()) {
            Q state = frontier.removeFirst();
            if (!game.isSafe(state) || game.isGoal(state)) {
                continue;
            }
            explicit.expandedStates++;

            Map<A, Set<Q>> byAction =
                    new LinkedHashMap<A, Set<Q>>();
            for (A action : sortedActions(
                    state, game.candidateActions(state))) {
                explicit.queriedStateActionPairs++;
                Set<Q> rawOutcomes = game.post(state, action);
                if (rawOutcomes == null) {
                    throw new IllegalStateException(
                            "successor oracle returned null: "
                                    + state + " / " + action);
                }
                if (rawOutcomes.isEmpty()) {
                    continue;
                }
                LinkedHashSet<Q> outcomes =
                        new LinkedHashSet<Q>(sortedStates(rawOutcomes));
                byAction.put(action, outcomes);
                explicit.enabledActionBuckets++;
                explicit.materializedTransitions += outcomes.size();
                for (Q outcome : outcomes) {
                    requireCanonical(outcome);
                    if (explicit.states.add(outcome)) {
                        frontier.addLast(outcome);
                    }
                }
                explicit.peakFrontier = Math.max(
                        explicit.peakFrontier, frontier.size());
            }
            explicit.successors.put(
                    state,
                    Collections.unmodifiableMap(byAction));
        }
        return explicit;
    }

    private FixedPoint solveExplicitGame(ExplicitGame explicit) {
        FixedPoint result = new FixedPoint();
        for (Q state : sortedStates(explicit.states)) {
            if (game.isSafe(state) && game.isGoal(state)) {
                result.winning.add(state);
                result.ranks.put(state, Integer.valueOf(0));
            }
        }

        while (true) {
            result.iterations++;
            List<Promotion> promotions = new ArrayList<Promotion>();
            for (Q state : sortedStates(explicit.states)) {
                if (result.winning.contains(state)
                        || !game.isSafe(state)
                        || game.isGoal(state)) {
                    continue;
                }
                result.stateInspections++;
                Map<A, Set<Q>> buckets = explicit.successors.get(state);
                if (buckets == null || buckets.isEmpty()) {
                    continue;
                }

                List<A> uncontrollable =
                        enabledUncontrollableActions(state, buckets);
                if (!uncontrollable.isEmpty()) {
                    int maximumRank = -1;
                    boolean allWinning = true;
                    for (A action : uncontrollable) {
                        result.bucketInspections++;
                        int bucketMaximum = winningBucketMaximumRank(
                                buckets.get(action), result);
                        if (bucketMaximum < 0) {
                            allWinning = false;
                            break;
                        }
                        maximumRank = Math.max(
                                maximumRank, bucketMaximum);
                    }
                    if (allWinning) {
                        promotions.add(
                                new Promotion(state, maximumRank + 1));
                    }
                    continue;
                }

                int bestMaximumRank = Integer.MAX_VALUE;
                for (A action : sortedActions(state, buckets.keySet())) {
                    if (!game.isControllable(action)) {
                        continue;
                    }
                    result.bucketInspections++;
                    int bucketMaximum = winningBucketMaximumRank(
                            buckets.get(action), result);
                    if (bucketMaximum >= 0) {
                        bestMaximumRank = Math.min(
                                bestMaximumRank, bucketMaximum);
                    }
                }
                if (bestMaximumRank != Integer.MAX_VALUE) {
                    promotions.add(
                            new Promotion(state, bestMaximumRank + 1));
                }
            }

            if (promotions.isEmpty()) {
                break;
            }
            for (Promotion promotion : promotions) {
                result.winning.add(promotion.state);
                result.ranks.put(
                        promotion.state,
                        Integer.valueOf(promotion.rank));
                result.promotedStates++;
            }
        }
        return result;
    }

    private int winningBucketMaximumRank(
            Set<Q> outcomes,
            FixedPoint fixedPoint) {
        int maximum = -1;
        for (Q outcome : outcomes) {
            fixedPoint.outcomeInspections++;
            Integer outcomeRank = fixedPoint.ranks.get(outcome);
            if (outcomeRank == null) {
                return -1;
            }
            maximum = Math.max(maximum, outcomeRank.intValue());
        }
        return maximum;
    }

    private OtfDucsResult.WinningCertificate<Q, A, G>
            extractWinningCertificate(
                    ExplicitGame explicit,
                    FixedPoint fixedPoint) {
        Map<Q, Integer> ranks = new LinkedHashMap<Q, Integer>();
        Map<Q, Map<A, Set<Q>>> strategy =
                new LinkedHashMap<Q, Map<A, Set<Q>>>();
        Map<Q, G> goalMatches = new LinkedHashMap<Q, G>();
        Deque<Q> work =
                new ArrayDeque<Q>(sortedStates(explicit.initialStates));
        Set<Q> reachable = new LinkedHashSet<Q>();

        while (!work.isEmpty()) {
            Q state = work.removeFirst();
            if (!reachable.add(state)) {
                continue;
            }
            Integer sourceRank = fixedPoint.ranks.get(state);
            if (sourceRank == null) {
                throw new IllegalStateException(
                        "Winning certificate reached an unranked state: "
                                + state);
            }
            ranks.put(state, sourceRank);
            if (game.isGoal(state)) {
                goalMatches.put(state, game.goalMatch(state));
                continue;
            }

            Map<A, Set<Q>> buckets = explicit.successors.get(state);
            if (buckets == null || buckets.isEmpty()) {
                throw new IllegalStateException(
                        "Winning non-goal has no enabled action: " + state);
            }
            Map<A, Set<Q>> retained =
                    new LinkedHashMap<A, Set<Q>>();
            List<A> uncontrollable =
                    enabledUncontrollableActions(state, buckets);
            if (!uncontrollable.isEmpty()) {
                for (A action : uncontrollable) {
                    Set<Q> outcomes = buckets.get(action);
                    requireRankDecrease(
                            state, sourceRank, outcomes, fixedPoint.ranks);
                    retained.put(action, outcomes);
                    work.addAll(sortedStates(outcomes));
                }
            } else {
                A selected = selectControllableAction(
                        state, sourceRank, buckets, fixedPoint.ranks);
                Set<Q> outcomes = buckets.get(selected);
                retained.put(selected, outcomes);
                work.addAll(sortedStates(outcomes));
            }
            strategy.put(state, retained);
        }
        return new OtfDucsResult.WinningCertificate<Q, A, G>(
                explicit.initialStates, ranks, strategy, goalMatches);
    }

    private A selectControllableAction(
            final Q state,
            Integer sourceRank,
            Map<A, Set<Q>> buckets,
            final Map<Q, Integer> ranks) {
        List<A> candidates = new ArrayList<A>();
        for (A action : sortedActions(state, buckets.keySet())) {
            if (!game.isControllable(action)) {
                continue;
            }
            Set<Q> outcomes = buckets.get(action);
            boolean decreasing = true;
            for (Q outcome : outcomes) {
                Integer targetRank = ranks.get(outcome);
                if (targetRank == null
                        || targetRank.intValue()
                                >= sourceRank.intValue()) {
                    decreasing = false;
                    break;
                }
            }
            if (decreasing) {
                candidates.add(action);
            }
        }
        if (candidates.isEmpty()) {
            throw new IllegalStateException(
                    "Winning state has no rank-decreasing controllable action: "
                            + state);
        }
        Collections.sort(candidates, new Comparator<A>() {
            @Override
            public int compare(A left, A right) {
                int comparison = Integer.compare(
                        maximumRank(buckets.get(left), ranks),
                        maximumRank(buckets.get(right), ranks));
                if (comparison != 0) {
                    return comparison;
                }
                return actionOrder(state).compare(left, right);
            }
        });
        A selected = candidates.get(0);
        requireRankDecrease(
                state, sourceRank, buckets.get(selected), ranks);
        return selected;
    }

    private int maximumRank(
            Set<Q> outcomes,
            Map<Q, Integer> ranks) {
        int maximum = -1;
        for (Q outcome : outcomes) {
            maximum = Math.max(
                    maximum, ranks.get(outcome).intValue());
        }
        return maximum;
    }

    private void requireRankDecrease(
            Q source,
            Integer sourceRank,
            Set<Q> outcomes,
            Map<Q, Integer> ranks) {
        for (Q outcome : outcomes) {
            Integer targetRank = ranks.get(outcome);
            if (targetRank == null
                    || targetRank.intValue() >= sourceRank.intValue()) {
                throw new IllegalStateException(
                        "Non-decreasing Direct-Full certificate edge: "
                                + source + " -> " + outcome);
            }
        }
    }

    private List<A> enabledUncontrollableActions(
            Q state,
            Map<A, Set<Q>> buckets) {
        List<A> result = new ArrayList<A>();
        for (A action : buckets.keySet()) {
            if (!game.isControllable(action)) {
                result.add(action);
            }
        }
        Collections.sort(result, actionOrder(state));
        return result;
    }

    private List<A> sortedActions(
            final Q state,
            Collection<A> actions) {
        if (actions == null) {
            throw new IllegalStateException(
                    "candidateActions returned null");
        }
        LinkedHashSet<A> unique = new LinkedHashSet<A>();
        for (A action : actions) {
            if (action == null) {
                throw new IllegalStateException(
                        "candidateActions returned a null action");
            }
            unique.add(action);
        }
        List<A> result = new ArrayList<A>(unique);
        Collections.sort(result, actionOrder(state));
        return result;
    }

    private Comparator<A> actionOrder(final Q state) {
        final Map<A, Integer> priorities =
                new LinkedHashMap<A, Integer>();
        final boolean updateFirst = game.preferUpdateActions(state);
        return new Comparator<A>() {
            @Override
            public int compare(A left, A right) {
                Integer leftPriority = priorities.get(left);
                if (leftPriority == null) {
                    leftPriority = Integer.valueOf(
                            game.explorationActionPriority(state, left));
                    priorities.put(left, leftPriority);
                }
                Integer rightPriority = priorities.get(right);
                if (rightPriority == null) {
                    rightPriority = Integer.valueOf(
                            game.explorationActionPriority(state, right));
                    priorities.put(right, rightPriority);
                }
                int comparison = Integer.compare(
                        leftPriority.intValue(),
                        rightPriority.intValue());
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
        };
    }

    private List<Q> sortedStates(Collection<Q> states) {
        List<Q> result = new ArrayList<Q>(states);
        Collections.sort(result, game.stateComparator());
        return result;
    }

    private void requireCanonical(Q state) {
        if (state == null || !game.isStructurallyValid(state)) {
            throw new IllegalStateException(
                    "Successor oracle produced a non-canonical state: "
                            + state);
        }
    }

    private final class ExplicitGame {
        private final Set<Q> initialStates = new LinkedHashSet<Q>();
        private final Set<Q> states = new LinkedHashSet<Q>();
        private final Map<Q, Map<A, Set<Q>>> successors =
                new LinkedHashMap<Q, Map<A, Set<Q>>>();
        private long expandedStates;
        private long queriedStateActionPairs;
        private long enabledActionBuckets;
        private long materializedTransitions;
        private long peakFrontier;
    }

    private final class FixedPoint {
        private final Set<Q> winning = new LinkedHashSet<Q>();
        private final Map<Q, Integer> ranks =
                new LinkedHashMap<Q, Integer>();
        private long iterations;
        private long stateInspections;
        private long bucketInspections;
        private long outcomeInspections;
        private long promotedStates;
    }

    private final class Promotion {
        private final Q state;
        private final int rank;

        private Promotion(Q state, int rank) {
            this.state = state;
            this.rank = rank;
        }
    }

    /** Immutable, baseline-specific phase and work counters. */
    public static final class Statistics {
        private final long initialStates;
        private final long enumeratedStates;
        private final long expandedStates;
        private final long queriedStateActionPairs;
        private final long enabledActionBuckets;
        private final long materializedTransitions;
        private final long peakEnumerationFrontier;
        private final long fixedPointIterations;
        private final long fixedPointStateInspections;
        private final long fixedPointBucketInspections;
        private final long fixedPointOutcomeInspections;
        private final long promotedStates;
        private final long enumerationNanoseconds;
        private final long fixedPointNanoseconds;
        private final long certificateNanoseconds;

        private Statistics(
                long initialStates,
                long enumeratedStates,
                long expandedStates,
                long queriedStateActionPairs,
                long enabledActionBuckets,
                long materializedTransitions,
                long peakEnumerationFrontier,
                long fixedPointIterations,
                long fixedPointStateInspections,
                long fixedPointBucketInspections,
                long fixedPointOutcomeInspections,
                long promotedStates,
                long enumerationNanoseconds,
                long fixedPointNanoseconds,
                long certificateNanoseconds) {
            this.initialStates = initialStates;
            this.enumeratedStates = enumeratedStates;
            this.expandedStates = expandedStates;
            this.queriedStateActionPairs = queriedStateActionPairs;
            this.enabledActionBuckets = enabledActionBuckets;
            this.materializedTransitions = materializedTransitions;
            this.peakEnumerationFrontier = peakEnumerationFrontier;
            this.fixedPointIterations = fixedPointIterations;
            this.fixedPointStateInspections = fixedPointStateInspections;
            this.fixedPointBucketInspections =
                    fixedPointBucketInspections;
            this.fixedPointOutcomeInspections =
                    fixedPointOutcomeInspections;
            this.promotedStates = promotedStates;
            this.enumerationNanoseconds = enumerationNanoseconds;
            this.fixedPointNanoseconds = fixedPointNanoseconds;
            this.certificateNanoseconds = certificateNanoseconds;
        }

        public long initialStates() {
            return initialStates;
        }

        public long enumeratedStates() {
            return enumeratedStates;
        }

        public long expandedStates() {
            return expandedStates;
        }

        public long queriedStateActionPairs() {
            return queriedStateActionPairs;
        }

        public long enabledActionBuckets() {
            return enabledActionBuckets;
        }

        public long materializedTransitions() {
            return materializedTransitions;
        }

        public long peakEnumerationFrontier() {
            return peakEnumerationFrontier;
        }

        /** Includes the final no-change scan. */
        public long fixedPointIterations() {
            return fixedPointIterations;
        }

        public long fixedPointStateInspections() {
            return fixedPointStateInspections;
        }

        public long fixedPointBucketInspections() {
            return fixedPointBucketInspections;
        }

        public long fixedPointOutcomeInspections() {
            return fixedPointOutcomeInspections;
        }

        public long promotedStates() {
            return promotedStates;
        }

        public long enumerationNanoseconds() {
            return enumerationNanoseconds;
        }

        public long fixedPointNanoseconds() {
            return fixedPointNanoseconds;
        }

        public long certificateNanoseconds() {
            return certificateNanoseconds;
        }

        public long totalNanoseconds() {
            return enumerationNanoseconds
                    + fixedPointNanoseconds
                    + certificateNanoseconds;
        }
    }
}
