package ltsa.updatingControllers.otf;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Deque;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Exhaustive reference solver and certificate validator used only for
 * differential evaluation of the production on-the-fly implementation.
 */
public final class IndependentExplicitStrongSolver<S, M> {

    public static final String EXHAUSTIVE_FIXED_POINT_BASIS =
            "exhaustive_reachable_fixed_point";
    public static final String INDEPENDENT_CERTIFICATE_BASIS =
            "independent_certificate_proof";

    private final FineGrainedUpdateProblem<S, M> problem;
    private final IndependentFineGrainedSemantics<S, M> semantics;
    private final UpdatePolicyRestriction<S, M> restriction;
    private final long stateLimit;
    private final long queryLimit;

    public IndependentExplicitStrongSolver(
            FineGrainedUpdateProblem<S, M> problem,
            long stateLimit,
            long queryLimit) {
        this(
                requireProblem(problem),
                new UpdatePolicyRestriction<S, M>(
                        requireProblem(problem),
                        UpdatePolicyRestriction.Mode.FULL_FG),
                stateLimit,
                queryLimit);
    }

    public IndependentExplicitStrongSolver(
            FineGrainedUpdateProblem<S, M> problem,
            UpdatePolicyRestriction<S, M> restriction,
            long stateLimit,
            long queryLimit) {
        if (problem == null) {
            throw new IllegalArgumentException("problem must not be null");
        }
        if (stateLimit < 1 || queryLimit < 1) {
            throw new IllegalArgumentException(
                    "reference limits must be positive");
        }
        this.problem = problem;
        this.semantics =
                new IndependentFineGrainedSemantics<S, M>(problem);
        if (restriction == null || !restriction.isForProblem(problem)) {
            throw new IllegalArgumentException(
                    "restriction must belong to the verified problem");
        }
        this.restriction = restriction;
        this.stateLimit = stateLimit;
        this.queryLimit = queryLimit;
    }

    public VerificationReport verify(
            OtfDucsResult<CanonicalUpdateConfiguration<S, M>, String,
                    GoalSignature<S, M>> result) {
        long started = System.nanoTime();
        try {
            ExplicitGame game = enumerate();
            FixedPoint fixedPoint = solve(game);
            List<String> violations = new ArrayList<String>();
            boolean referenceWinning =
                    fixedPoint.winning.containsAll(semantics.initialStates());
            if (result.isWinning() != referenceWinning) {
                violations.add(
                        "production decision differs from exhaustive reference");
            }
            if (result.isWinning()) {
                verifyWinningCertificate(
                        result.winningCertificate(),
                        game,
                        fixedPoint,
                        violations);
            } else {
                verifyLosingCertificate(
                        result.losingCertificate(),
                        game,
                        fixedPoint,
                        violations);
            }
            return VerificationReport.complete(
                    violations,
                    game.states.size(),
                    game.queries,
                    game.outcomes,
                    elapsedMillis(started),
                    EXHAUSTIVE_FIXED_POINT_BASIS);
        } catch (LimitExceeded limit) {
            return VerificationReport.inconclusive(
                    limit.getMessage(),
                    limit.states,
                    limit.queries,
                    limit.outcomes,
                    elapsedMillis(started),
                    EXHAUSTIVE_FIXED_POINT_BASIS);
        }
    }

    /**
     * Verifies the supplied decision as an independently checked proof.
     *
     * <p>Unlike {@link #verify(OtfDucsResult)}, this method does not enumerate
     * the complete reachable game.  It derives every local obligation directly
     * from {@link IndependentFineGrainedSemantics}: a winning rank proof must
     * retain every enabled uncontrollable bucket (or exactly one enabled
     * controllable bucket when none is enabled), contain the exact successor
     * set, and strictly decrease on every retained edge.  A losing-region proof
     * must satisfy the dual local closure condition.  These obligations are a
     * sound proof of the reported decision, while work is proportional to the
     * certificate rather than to unrelated reachable states.</p>
     */
    public VerificationReport verifyCertificate(
            OtfDucsResult<CanonicalUpdateConfiguration<S, M>, String,
                    GoalSignature<S, M>> result) {
        long started = System.nanoTime();
        CertificateWork work = new CertificateWork();
        List<String> violations = new ArrayList<String>();
        try {
            if (result == null) {
                violations.add("result is null");
            } else if (result.isWinning()) {
                verifyWinningCertificateProof(
                        result.winningCertificate(), work, violations);
            } else {
                verifyLosingCertificateProof(
                        result.losingCertificate(), work, violations);
            }
            return VerificationReport.complete(
                    violations,
                    work.states.size(),
                    work.queries,
                    work.outcomes,
                    elapsedMillis(started),
                    INDEPENDENT_CERTIFICATE_BASIS);
        } catch (LimitExceeded limit) {
            return VerificationReport.inconclusive(
                    limit.getMessage(),
                    limit.states,
                    limit.queries,
                    limit.outcomes,
                    elapsedMillis(started),
                    INDEPENDENT_CERTIFICATE_BASIS);
        }
    }

    private void verifyWinningCertificateProof(
            OtfDucsResult.WinningCertificate<
                    CanonicalUpdateConfiguration<S, M>,
                    String,
                    GoalSignature<S, M>> certificate,
            CertificateWork work,
            List<String> violations) {
        Set<CanonicalUpdateConfiguration<S, M>> initial =
                semantics.initialStates();
        if (!certificate.initialStates().equals(initial)) {
            violations.add("winning certificate initial roots differ");
        }

        Deque<CanonicalUpdateConfiguration<S, M>> queue =
                new ArrayDeque<CanonicalUpdateConfiguration<S, M>>();
        Set<CanonicalUpdateConfiguration<S, M>> discovered =
                new LinkedHashSet<CanonicalUpdateConfiguration<S, M>>();
        Set<CanonicalUpdateConfiguration<S, M>> expectedStrategySources =
                new LinkedHashSet<CanonicalUpdateConfiguration<S, M>>();
        Set<CanonicalUpdateConfiguration<S, M>> expectedGoalMatches =
                new LinkedHashSet<CanonicalUpdateConfiguration<S, M>>();
        for (CanonicalUpdateConfiguration<S, M> root : initial) {
            discoverCertificateState(root, discovered, queue, work);
        }

        while (!queue.isEmpty()) {
            CanonicalUpdateConfiguration<S, M> state = queue.removeFirst();
            if (!problem.isStructurallyValid(state)) {
                violations.add(
                        "certificate contains a non-canonical state");
                continue;
            }
            Integer sourceRank = certificate.ranks().get(state);
            if (sourceRank == null) {
                violations.add("certificate omits a reachable rank");
                continue;
            }
            if (!isRestrictedSafe(state)) {
                violations.add("certificate reaches an unsafe state");
                continue;
            }
            if (semantics.isGoal(state)) {
                expectedGoalMatches.add(state);
                if (sourceRank.intValue() != 0) {
                    violations.add("goal state has nonzero rank");
                }
                GoalSignature<S, M> expected =
                        problem.goalMatch(state).orElse(null);
                if (!java.util.Objects.equals(
                        expected, certificate.goalMatches().get(state))) {
                    violations.add("goal quotient match differs");
                }
                Map<String, Set<CanonicalUpdateConfiguration<S, M>>>
                        retained = certificate.strategy().get(state);
                if (retained != null && !retained.isEmpty()) {
                    violations.add("goal state retains an action bucket");
                }
                continue;
            }

            expectedStrategySources.add(state);
            if (sourceRank.intValue() <= 0) {
                violations.add("non-goal state has a nonpositive rank");
            }
            Map<String, Set<CanonicalUpdateConfiguration<S, M>>> retained =
                    certificate.strategy().get(state);
            if (retained == null || retained.isEmpty()) {
                violations.add(
                        "non-goal certificate state has no retained bucket");
                continue;
            }

            Map<String, Set<CanonicalUpdateConfiguration<S, M>>> enabled =
                    independentEnabledBuckets(state, work);
            List<String> uncontrollable = uncontrollableActions(enabled);
            if (!uncontrollable.isEmpty()) {
                if (!retained.keySet().equals(
                        new LinkedHashSet<String>(uncontrollable))) {
                    violations.add(
                            "certificate does not retain exactly all "
                                    + "uncontrollable buckets");
                }
            } else if (retained.size() != 1
                    || !semantics.isControllable(
                            retained.keySet().iterator().next())) {
                violations.add(
                        "certificate does not retain one controllable bucket");
            }

            for (Map.Entry<String,
                    Set<CanonicalUpdateConfiguration<S, M>>> entry
                    : retained.entrySet()) {
                Set<CanonicalUpdateConfiguration<S, M>> actual =
                        enabled.get(entry.getKey());
                if (actual == null || actual.isEmpty()
                        || !actual.equals(entry.getValue())) {
                    violations.add(
                            "certificate bucket differs from independent post");
                    continue;
                }
                for (CanonicalUpdateConfiguration<S, M> target : actual) {
                    Integer targetRank = certificate.ranks().get(target);
                    if (targetRank == null
                            || targetRank.intValue()
                                    >= sourceRank.intValue()) {
                        violations.add(
                                "certificate edge does not decrease rank");
                    }
                    discoverCertificateState(
                            target, discovered, queue, work);
                }
            }
        }

        if (!discovered.equals(certificate.ranks().keySet())) {
            violations.add(
                    "rank domain is not exactly the strategy-reachable set");
        }
        if (!expectedStrategySources.equals(
                certificate.strategy().keySet())) {
            violations.add(
                    "strategy domain is not exactly the reachable "
                            + "non-goal set");
        }
        if (!expectedGoalMatches.equals(
                certificate.goalMatches().keySet())) {
            violations.add(
                    "goal-match domain is not exactly the reachable goal set");
        }
    }

    private void verifyLosingCertificateProof(
            OtfDucsResult.LosingCertificate<
                    CanonicalUpdateConfiguration<S, M>> certificate,
            CertificateWork work,
            List<String> violations) {
        Set<CanonicalUpdateConfiguration<S, M>> losing =
                certificate.losingStates();
        if (Collections.disjoint(losing, semantics.initialStates())) {
            violations.add("losing certificate contains no initial root");
        }
        for (CanonicalUpdateConfiguration<S, M> state : losing) {
            if (work.states.add(state)) {
                checkCertificateLimits(work);
            }
            if (!problem.isStructurallyValid(state)) {
                violations.add(
                        "losing certificate contains a non-canonical state");
                continue;
            }
            if (!isRestrictedSafe(state)) {
                continue;
            }
            if (semantics.isGoal(state)) {
                violations.add("losing certificate contains a goal state");
                continue;
            }

            Map<String, Set<CanonicalUpdateConfiguration<S, M>>> enabled =
                    independentEnabledBuckets(state, work);
            List<String> uncontrollable = uncontrollableActions(enabled);
            if (!uncontrollable.isEmpty()) {
                boolean witness = false;
                for (String action : uncontrollable) {
                    if (!Collections.disjoint(
                            enabled.get(action), losing)) {
                        witness = true;
                        break;
                    }
                }
                if (!witness) {
                    violations.add(
                            "losing state has no uncontrollable "
                                    + "closure witness");
                }
                continue;
            }

            for (Map.Entry<String,
                    Set<CanonicalUpdateConfiguration<S, M>>> entry
                    : enabled.entrySet()) {
                if (semantics.isControllable(entry.getKey())
                        && Collections.disjoint(
                                entry.getValue(), losing)) {
                    violations.add(
                            "controllable action escapes losing region");
                }
            }
        }
    }

    private Map<String, Set<CanonicalUpdateConfiguration<S, M>>>
            independentEnabledBuckets(
                    CanonicalUpdateConfiguration<S, M> state,
                    CertificateWork work) {
        Map<String, Set<CanonicalUpdateConfiguration<S, M>>> enabled =
                new LinkedHashMap<String,
                        Set<CanonicalUpdateConfiguration<S, M>>>();
        for (String action : candidateActions(state)) {
            work.queries++;
            checkCertificateLimits(work);
            Set<CanonicalUpdateConfiguration<S, M>> outcomes =
                    semantics.post(state, action);
            if (!outcomes.isEmpty()) {
                work.outcomes += outcomes.size();
                enabled.put(action, outcomes);
            }
        }
        return enabled;
    }

    private void discoverCertificateState(
            CanonicalUpdateConfiguration<S, M> state,
            Set<CanonicalUpdateConfiguration<S, M>> discovered,
            Deque<CanonicalUpdateConfiguration<S, M>> queue,
            CertificateWork work) {
        if (discovered.add(state)) {
            work.states.add(state);
            checkCertificateLimits(work);
            queue.addLast(state);
        }
    }

    private void checkCertificateLimits(CertificateWork work) {
        if (work.states.size() > stateLimit
                || work.queries > queryLimit) {
            throw new LimitExceeded(
                    "independent certificate-check resource limit exceeded",
                    work.states.size(),
                    work.queries,
                    work.outcomes);
        }
    }

    private ExplicitGame enumerate() {
        ExplicitGame game = new ExplicitGame();
        Deque<CanonicalUpdateConfiguration<S, M>> queue =
                new ArrayDeque<CanonicalUpdateConfiguration<S, M>>();
        for (CanonicalUpdateConfiguration<S, M> initial
                : semantics.initialStates()) {
            if (game.states.add(initial)) {
                queue.addLast(initial);
            }
        }

        while (!queue.isEmpty()) {
            CanonicalUpdateConfiguration<S, M> state = queue.removeFirst();
            if (!isRestrictedSafe(state)) {
                continue;
            }
            Map<String, Set<CanonicalUpdateConfiguration<S, M>>> buckets =
                    new LinkedHashMap<String,
                            Set<CanonicalUpdateConfiguration<S, M>>>();
            for (String action : candidateActions(state)) {
                game.queries++;
                checkLimits(game);
                Set<CanonicalUpdateConfiguration<S, M>> outcomes =
                        semantics.post(state, action);
                if (outcomes.isEmpty()) {
                    continue;
                }
                game.outcomes += outcomes.size();
                buckets.put(action, outcomes);
                for (CanonicalUpdateConfiguration<S, M> outcome : outcomes) {
                    if (game.states.add(outcome)) {
                        checkLimits(game);
                        queue.addLast(outcome);
                    }
                }
            }
            game.successors.put(state, buckets);
        }
        return game;
    }

    private List<String> candidateActions(
            CanonicalUpdateConfiguration<S, M> state) {
        return restriction.filter(state, semantics.candidateActions(state));
    }

    private boolean isRestrictedSafe(
            CanonicalUpdateConfiguration<S, M> state) {
        if (!semantics.isSafe(state)) {
            return false;
        }
        for (String action : semantics.candidateActions(state)) {
            if (!semantics.isControllable(action)
                    && restriction.isOutsideActiveBlock(state, action)
                    && !semantics.post(state, action).isEmpty()) {
                return false;
            }
        }
        return true;
    }

    private static <S, M> FineGrainedUpdateProblem<S, M> requireProblem(
            FineGrainedUpdateProblem<S, M> problem) {
        if (problem == null) {
            throw new IllegalArgumentException("problem must not be null");
        }
        return problem;
    }

    private FixedPoint solve(ExplicitGame game) {
        LinkedHashSet<CanonicalUpdateConfiguration<S, M>> winning =
                new LinkedHashSet<CanonicalUpdateConfiguration<S, M>>();
        Map<CanonicalUpdateConfiguration<S, M>, Integer> ranks =
                new LinkedHashMap<CanonicalUpdateConfiguration<S, M>, Integer>();
        for (CanonicalUpdateConfiguration<S, M> state : game.states) {
            if (semantics.isGoal(state)) {
                winning.add(state);
                ranks.put(state, Integer.valueOf(0));
            }
        }

        boolean changed;
        do {
            changed = false;
            for (CanonicalUpdateConfiguration<S, M> state : game.states) {
                if (winning.contains(state)
                        || !isRestrictedSafe(state)
                        || semantics.isGoal(state)) {
                    continue;
                }
                Map<String, Set<CanonicalUpdateConfiguration<S, M>>> buckets =
                        game.successors.get(state);
                if (buckets == null || buckets.isEmpty()) {
                    continue;
                }
                List<String> uncontrollable =
                        uncontrollableActions(buckets);
                int maximumRank = -1;
                boolean ready;
                if (!uncontrollable.isEmpty()) {
                    ready = true;
                    for (String action : uncontrollable) {
                        Set<CanonicalUpdateConfiguration<S, M>> outcomes =
                                buckets.get(action);
                        if (!winning.containsAll(outcomes)) {
                            ready = false;
                            break;
                        }
                        maximumRank = Math.max(
                                maximumRank,
                                maximumRank(outcomes, ranks));
                    }
                } else {
                    ready = false;
                    for (Map.Entry<String,
                            Set<CanonicalUpdateConfiguration<S, M>>> entry
                            : buckets.entrySet()) {
                        if (!semantics.isControllable(entry.getKey())
                                || !winning.containsAll(entry.getValue())) {
                            continue;
                        }
                        ready = true;
                        maximumRank = Math.max(
                                maximumRank,
                                maximumRank(entry.getValue(), ranks));
                        break;
                    }
                }
                if (ready) {
                    winning.add(state);
                    ranks.put(
                            state,
                            Integer.valueOf(maximumRank + 1));
                    changed = true;
                }
            }
        } while (changed);
        return new FixedPoint(winning, ranks);
    }

    private void verifyWinningCertificate(
            OtfDucsResult.WinningCertificate<
                    CanonicalUpdateConfiguration<S, M>,
                    String,
                    GoalSignature<S, M>> certificate,
            ExplicitGame game,
            FixedPoint fixedPoint,
            List<String> violations) {
        if (!certificate.initialStates().equals(semantics.initialStates())) {
            violations.add("winning certificate initial roots differ");
        }
        if (!certificate.ranks().keySet().containsAll(
                semantics.initialStates())) {
            violations.add("winning certificate omits an initial root");
        }
        for (Map.Entry<CanonicalUpdateConfiguration<S, M>, Integer> ranked
                : certificate.ranks().entrySet()) {
            CanonicalUpdateConfiguration<S, M> state = ranked.getKey();
            Integer rank = ranked.getValue();
            if (!fixedPoint.winning.contains(state)) {
                violations.add(
                        "certificate contains a reference-losing state");
                continue;
            }
            if (rank == null || rank.intValue() < 0) {
                violations.add("certificate contains an invalid rank");
                continue;
            }
            if (semantics.isGoal(state)) {
                if (rank.intValue() != 0) {
                    violations.add("goal state has nonzero rank");
                }
                GoalSignature<S, M> expected =
                        problem.goalMatch(state).orElse(null);
                if (!expected.equals(
                        certificate.goalMatches().get(state))) {
                    violations.add("goal quotient match differs");
                }
                continue;
            }
            Map<String, Set<CanonicalUpdateConfiguration<S, M>>> retained =
                    certificate.strategy().get(state);
            Map<String, Set<CanonicalUpdateConfiguration<S, M>>> enabled =
                    game.successors.get(state);
            if (retained == null || retained.isEmpty()
                    || enabled == null) {
                violations.add(
                        "non-goal certificate state has no retained bucket");
                continue;
            }
            List<String> uncontrollable =
                    uncontrollableActions(enabled);
            if (!uncontrollable.isEmpty()) {
                if (!retained.keySet().equals(
                        new LinkedHashSet<String>(uncontrollable))) {
                    violations.add(
                            "certificate does not retain exactly all "
                                    + "uncontrollable buckets");
                }
            } else if (retained.size() != 1
                    || !semantics.isControllable(
                            retained.keySet().iterator().next())) {
                violations.add(
                        "certificate does not retain one controllable bucket");
            }
            for (Map.Entry<String,
                    Set<CanonicalUpdateConfiguration<S, M>>> entry
                    : retained.entrySet()) {
                Set<CanonicalUpdateConfiguration<S, M>> expected =
                        enabled.get(entry.getKey());
                if (expected == null
                        || !expected.equals(entry.getValue())) {
                    violations.add(
                            "certificate bucket differs from reference post");
                    continue;
                }
                for (CanonicalUpdateConfiguration<S, M> target
                        : entry.getValue()) {
                    Integer targetRank = certificate.ranks().get(target);
                    if (targetRank == null
                            || targetRank.intValue() >= rank.intValue()) {
                        violations.add(
                                "certificate edge does not decrease rank");
                    }
                }
            }
        }
    }

    private void verifyLosingCertificate(
            OtfDucsResult.LosingCertificate<
                    CanonicalUpdateConfiguration<S, M>> certificate,
            ExplicitGame game,
            FixedPoint fixedPoint,
            List<String> violations) {
        Set<CanonicalUpdateConfiguration<S, M>> expected =
                new LinkedHashSet<CanonicalUpdateConfiguration<S, M>>(
                        game.states);
        expected.removeAll(fixedPoint.winning);
        Set<CanonicalUpdateConfiguration<S, M>> losing =
                certificate.losingStates();
        if (!expected.containsAll(losing)) {
            violations.add(
                    "losing certificate contains a reference-winning state");
        }
        if (Collections.disjoint(losing, semantics.initialStates())) {
            violations.add("losing certificate contains no initial root");
        }
        for (CanonicalUpdateConfiguration<S, M> state : losing) {
            if (!isRestrictedSafe(state)) {
                continue;
            }
            if (semantics.isGoal(state)) {
                violations.add("losing certificate contains a goal state");
                continue;
            }
            Map<String, Set<CanonicalUpdateConfiguration<S, M>>> buckets =
                    game.successors.get(state);
            if (buckets == null) {
                buckets = Collections.emptyMap();
            }
            List<String> uncontrollable =
                    uncontrollableActions(buckets);
            if (!uncontrollable.isEmpty()) {
                boolean witness = false;
                for (String action : uncontrollable) {
                    if (!Collections.disjoint(
                            buckets.get(action), losing)) {
                        witness = true;
                        break;
                    }
                }
                if (!witness) {
                    violations.add(
                            "losing state has no uncontrollable closure witness");
                }
            } else {
                for (Map.Entry<String,
                        Set<CanonicalUpdateConfiguration<S, M>>> entry
                        : buckets.entrySet()) {
                    if (semantics.isControllable(entry.getKey())
                            && Collections.disjoint(
                                    entry.getValue(), losing)) {
                        violations.add(
                                "controllable action escapes losing region");
                    }
                }
            }
        }
    }

    private List<String> uncontrollableActions(
            Map<String, Set<CanonicalUpdateConfiguration<S, M>>> buckets) {
        List<String> result = new ArrayList<String>();
        for (String action : buckets.keySet()) {
            if (!semantics.isControllable(action)) {
                result.add(action);
            }
        }
        Collections.sort(result);
        return result;
    }

    private int maximumRank(
            Set<CanonicalUpdateConfiguration<S, M>> states,
            Map<CanonicalUpdateConfiguration<S, M>, Integer> ranks) {
        int result = -1;
        for (CanonicalUpdateConfiguration<S, M> state : states) {
            Integer rank = ranks.get(state);
            if (rank == null) {
                throw new IllegalStateException(
                        "reference fixed point has an unranked successor");
            }
            result = Math.max(result, rank.intValue());
        }
        return result;
    }

    private void checkLimits(ExplicitGame game) {
        if (game.states.size() > stateLimit
                || game.queries > queryLimit) {
            throw new LimitExceeded(
                    "reference resource limit exceeded",
                    game.states.size(),
                    game.queries,
                    game.outcomes);
        }
    }

    private static long elapsedMillis(long started) {
        return Math.max(
                0L,
                (System.nanoTime() - started) / 1_000_000L);
    }

    private final class ExplicitGame {
        private final Set<CanonicalUpdateConfiguration<S, M>> states =
                new LinkedHashSet<CanonicalUpdateConfiguration<S, M>>();
        private final Map<CanonicalUpdateConfiguration<S, M>,
                Map<String, Set<CanonicalUpdateConfiguration<S, M>>>>
                successors =
                new LinkedHashMap<CanonicalUpdateConfiguration<S, M>,
                        Map<String,
                                Set<CanonicalUpdateConfiguration<S, M>>>>();
        private long queries;
        private long outcomes;
    }

    private final class FixedPoint {
        private final Set<CanonicalUpdateConfiguration<S, M>> winning;
        private final Map<CanonicalUpdateConfiguration<S, M>, Integer> ranks;

        private FixedPoint(
                Set<CanonicalUpdateConfiguration<S, M>> winning,
                Map<CanonicalUpdateConfiguration<S, M>, Integer> ranks) {
            this.winning = winning;
            this.ranks = ranks;
        }
    }

    private final class CertificateWork {
        private final Set<CanonicalUpdateConfiguration<S, M>> states =
                new LinkedHashSet<CanonicalUpdateConfiguration<S, M>>();
        private long queries;
        private long outcomes;
    }

    private static final class LimitExceeded extends RuntimeException {
        private static final long serialVersionUID = 1L;
        private final long states;
        private final long queries;
        private final long outcomes;

        private LimitExceeded(
                String message,
                long states,
                long queries,
                long outcomes) {
            super(message);
            this.states = states;
            this.queries = queries;
            this.outcomes = outcomes;
        }
    }

    public static final class VerificationReport {
        private final boolean complete;
        private final List<String> violations;
        private final String reason;
        private final long states;
        private final long queries;
        private final long outcomes;
        private final long elapsedMillis;
        private final String basis;

        private VerificationReport(
                boolean complete,
                List<String> violations,
                String reason,
                long states,
                long queries,
                long outcomes,
                long elapsedMillis,
                String basis) {
            this.complete = complete;
            this.violations = Collections.unmodifiableList(
                    new ArrayList<String>(violations));
            this.reason = reason;
            this.states = states;
            this.queries = queries;
            this.outcomes = outcomes;
            this.elapsedMillis = elapsedMillis;
            this.basis = basis;
        }

        private static VerificationReport complete(
                List<String> violations,
                long states,
                long queries,
                long outcomes,
                long elapsedMillis,
                String basis) {
            return new VerificationReport(
                    true,
                    violations,
                    violations.isEmpty() ? "" : "validation failed",
                    states,
                    queries,
                    outcomes,
                    elapsedMillis,
                    basis);
        }

        private static VerificationReport inconclusive(
                String reason,
                long states,
                long queries,
                long outcomes,
                long elapsedMillis,
                String basis) {
            return new VerificationReport(
                    false,
                    Collections.<String>emptyList(),
                    reason,
                    states,
                    queries,
                    outcomes,
                    elapsedMillis,
                    basis);
        }

        public boolean isComplete() {
            return complete;
        }

        public boolean isValid() {
            return complete && violations.isEmpty();
        }

        public List<String> violations() {
            return violations;
        }

        public String reason() {
            return reason;
        }

        public long states() {
            return states;
        }

        public long queries() {
            return queries;
        }

        public long outcomes() {
            return outcomes;
        }

        public long elapsedMillis() {
            return elapsedMillis;
        }

        public String basis() {
            return basis;
        }

        public void throwIfInvalid() {
            if (!isValid()) {
                throw new IllegalStateException(
                        complete
                                ? "Independent verification failed: "
                                        + violations
                                : "Independent verification incomplete: "
                                        + reason);
            }
        }
    }
}
