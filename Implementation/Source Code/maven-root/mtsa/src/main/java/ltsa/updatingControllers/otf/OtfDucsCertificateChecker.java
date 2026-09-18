package ltsa.updatingControllers.otf;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.Deque;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

/** Independent, exhaustive checker for winning-rank and losing-region certificates. */
public final class OtfDucsCertificateChecker<Q, A, G> {

    private final ImplicitStrongGame<Q, A, G> game;

    public OtfDucsCertificateChecker(ImplicitStrongGame<Q, A, G> game) {
        if (game == null) {
            throw new IllegalArgumentException("game must not be null");
        }
        this.game = game;
    }

    public VerificationReport verify(OtfDucsResult<Q, A, G> result) {
        if (result == null) {
            return VerificationReport.failure("result is null");
        }
        return result.isWinning()
                ? verifyWinning(result.winningCertificate())
                : verifyLosing(result.losingCertificate());
    }

    public VerificationReport verifyWinning(
            OtfDucsResult.WinningCertificate<Q, A, G> certificate) {
        List<String> violations = new ArrayList<String>();
        if (!certificate.initialStates().equals(game.initialStates())) {
            violations.add("certificate roots differ from all Q0 hotSwapIn embeddings");
        }

        Deque<Q> work = new ArrayDeque<Q>(game.initialStates());
        Set<Q> reachable = new LinkedHashSet<Q>();
        Set<Q> expectedStrategySources = new LinkedHashSet<Q>();
        Set<Q> expectedGoalMatches = new LinkedHashSet<Q>();
        while (!work.isEmpty()) {
            Q state = work.removeFirst();
            if (!reachable.add(state)) {
                continue;
            }
            if (!game.isStructurallyValid(state)) {
                violations.add("non-canonical certified state: " + state);
                continue;
            }
            Integer sourceRank = certificate.ranks().get(state);
            if (sourceRank == null) {
                violations.add("missing rank: " + state);
                continue;
            }
            if (!game.isSafe(state)) {
                violations.add("unsafe strategy-reachable state: " + state);
            }

            Map<A, Set<Q>> retained = certificate.strategy().get(state);
            if (game.isGoal(state)) {
                expectedGoalMatches.add(state);
                if (sourceRank.intValue() != 0) {
                    violations.add("Goal rank is not zero: " + state);
                }
                if (retained != null && !retained.isEmpty()) {
                    violations.add("Goal has a mid-mode transition: " + state);
                }
                if (!certificate.goalMatches().containsKey(state)
                        || !Objects.equals(certificate.goalMatches().get(state), game.goalMatch(state))) {
                    violations.add("invalid atomic endpoint match: " + state);
                }
                continue;
            }

            expectedStrategySources.add(state);

            if (sourceRank.intValue() <= 0) {
                violations.add("non-Goal rank is not positive: " + state);
            }
            if (retained == null || retained.isEmpty()) {
                violations.add("deadlocked non-Goal certificate state: " + state);
                continue;
            }

            List<A> candidates = unique(game.candidateActions(state));
            Set<A> candidateSet = new LinkedHashSet<A>(candidates);
            List<A> uncontrollable = new ArrayList<A>();
            for (A action : candidates) {
                Set<Q> actual = nonNullPost(state, action, violations);
                if (!game.isControllable(action) && !actual.isEmpty()) {
                    uncontrollable.add(action);
                }
            }

            if (!uncontrollable.isEmpty()) {
                if (retained.size() != uncontrollable.size()) {
                    violations.add("certificate does not retain exactly all uncontrollable buckets: " + state);
                }
                for (A action : uncontrollable) {
                    checkExactBucket(certificate, state, action, retained.get(action),
                            sourceRank, work, violations);
                }
                for (A action : retained.keySet()) {
                    if (game.isControllable(action)) {
                        violations.add("controllable action retained while an uncontrollable action is enabled: "
                                + state + " / " + action);
                    }
                }
            } else {
                if (retained.size() != 1) {
                    violations.add("certificate must select exactly one controllable bucket: " + state);
                }
                for (Map.Entry<A, Set<Q>> entry : retained.entrySet()) {
                    if (!candidateSet.contains(entry.getKey())) {
                        violations.add("certificate selects an action outside candidateActions: "
                                + state + " / " + entry.getKey());
                    }
                    if (!game.isControllable(entry.getKey())) {
                        violations.add("unexpected uncontrollable bucket: " + state + " / " + entry.getKey());
                    }
                    checkExactBucket(certificate, state, entry.getKey(), entry.getValue(),
                            sourceRank, work, violations);
                }
            }
        }

        if (!reachable.equals(certificate.ranks().keySet())) {
            violations.add("rank domain is not exactly the strategy-reachable state set");
        }
        if (!expectedStrategySources.equals(certificate.strategy().keySet())) {
            violations.add("strategy domain is not exactly the reachable non-Goal state set");
        }
        if (!expectedGoalMatches.equals(certificate.goalMatches().keySet())) {
            violations.add("endpoint-match domain is not exactly the reachable Goal state set");
        }
        return new VerificationReport(violations);
    }

    public VerificationReport verifyLosing(OtfDucsResult.LosingCertificate<Q> certificate) {
        List<String> violations = new ArrayList<String>();
        Set<Q> losing = certificate.losingStates();
        Set<Q> initialIntersection = new LinkedHashSet<Q>(game.initialStates());
        initialIntersection.retainAll(losing);
        if (initialIntersection.isEmpty()) {
            violations.add("losing certificate contains no initial state");
        }

        for (Q state : losing) {
            if (!game.isStructurallyValid(state)) {
                violations.add("non-canonical losing state: " + state);
                continue;
            }
            if (game.isGoal(state)) {
                violations.add("losing certificate contains a Goal: " + state);
            }
            if (!game.isSafe(state)) {
                continue; // Unsafe states need no local closure obligation.
            }

            List<A> candidates = unique(game.candidateActions(state));
            Set<Q> uncontrollableOutcomes = new LinkedHashSet<Q>();
            for (A action : candidates) {
                if (!game.isControllable(action)) {
                    uncontrollableOutcomes.addAll(nonNullPost(state, action, violations));
                }
            }
            if (!uncontrollableOutcomes.isEmpty()) {
                if (Collections.disjoint(uncontrollableOutcomes, losing)) {
                    violations.add("all uncontrollable outcomes escape losing region: " + state);
                }
                continue;
            }

            for (A action : candidates) {
                if (!game.isControllable(action)) {
                    continue;
                }
                Set<Q> outcomes = nonNullPost(state, action, violations);
                if (!outcomes.isEmpty() && Collections.disjoint(outcomes, losing)) {
                    violations.add("winning controllable escape from losing region: "
                            + state + " / " + action);
                }
            }
        }
        return new VerificationReport(violations);
    }

    private void checkExactBucket(
            OtfDucsResult.WinningCertificate<Q, A, G> certificate,
            Q state,
            A action,
            Set<Q> certified,
            Integer sourceRank,
            Deque<Q> work,
            List<String> violations) {
        Set<Q> actual = nonNullPost(state, action, violations);
        if (certified == null || !actual.equals(certified)) {
            violations.add("certificate omits or invents an action outcome: " + state + " / " + action);
            return;
        }
        if (actual.isEmpty()) {
            violations.add("certificate retains a disabled action: " + state + " / " + action);
        }
        for (Q outcome : actual) {
            work.addLast(outcome);
            Integer targetRank = certificate.ranks().get(outcome);
            if (targetRank == null || targetRank.intValue() >= sourceRank.intValue()) {
                violations.add("rank does not strictly decrease: " + state + " -> " + outcome);
            }
        }
    }

    private Set<Q> nonNullPost(Q state, A action, List<String> violations) {
        Set<Q> result = game.post(state, action);
        if (result == null) {
            violations.add("successor oracle returned null: " + state + " / " + action);
            return Collections.emptySet();
        }
        return result;
    }

    private List<A> unique(Collection<A> values) {
        return new ArrayList<A>(new LinkedHashSet<A>(values));
    }

    public static final class VerificationReport {
        private final List<String> violations;

        private VerificationReport(List<String> violations) {
            this.violations = Collections.unmodifiableList(new ArrayList<String>(violations));
        }

        static VerificationReport failure(String violation) {
            List<String> violations = new ArrayList<String>();
            violations.add(violation);
            return new VerificationReport(violations);
        }

        public boolean isValid() {
            return violations.isEmpty();
        }

        public List<String> violations() {
            return violations;
        }

        public void throwIfInvalid() {
            if (!isValid()) {
                throw new IllegalStateException("Invalid OTF-DUCS certificate: " + violations);
            }
        }
    }
}
