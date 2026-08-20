package ltsa.updatingControllers.otf;

import org.testng.annotations.Test;

import java.util.ArrayDeque;
import java.util.Collections;
import java.util.Deque;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Random;
import java.util.Set;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

public class IndependentExplicitStrongSolverTest {

    @Test
    public void independentlyAcceptsWinningCertificateAndDecision() {
        FineGrainedUpdateProblem<String, String> problem =
                simpleProblem(true);
        OtfDucsResult<CanonicalUpdateConfiguration<String, String>, String,
                GoalSignature<String, String>> result =
                FineGrainedOtfDucs.synthesizeTrustedEndpointProjections(problem);

        IndependentExplicitStrongSolver.VerificationReport report =
                verifier(problem).verify(result);

        assertTrue(result.isWinning());
        assertTrue(report.violations().toString(), report.isComplete());
        assertTrue(report.violations().toString(), report.isValid());
        assertTrue(report.states() >= 3);
        assertTrue(report.queries() >= 2);
    }

    @Test
    public void independentCertificateProofAcceptsWinningDecisionWithoutFullEnumeration() {
        FineGrainedUpdateProblem<String, String> problem =
                simpleProblem(true);
        OtfDucsResult<CanonicalUpdateConfiguration<String, String>, String,
                GoalSignature<String, String>> result =
                FineGrainedOtfDucs.synthesizeTrustedEndpointProjections(problem);

        IndependentExplicitStrongSolver.VerificationReport report =
                verifier(problem).verifyCertificate(result);

        assertTrue(result.isWinning());
        assertTrue(report.violations().toString(), report.isComplete());
        assertTrue(report.violations().toString(), report.isValid());
        assertEquals(
                IndependentExplicitStrongSolver.INDEPENDENT_CERTIFICATE_BASIS,
                report.basis());
        assertEquals(
                result.winningCertificate().ranks().size(),
                report.states());
    }

    @Test
    public void independentCertificateProofAcceptsLosingDecision() {
        FineGrainedUpdateProblem<String, String> problem =
                simpleProblem(false);
        OtfDucsResult<CanonicalUpdateConfiguration<String, String>, String,
                GoalSignature<String, String>> result =
                FineGrainedOtfDucs.synthesizeTrustedEndpointProjections(problem);

        IndependentExplicitStrongSolver.VerificationReport report =
                verifier(problem).verifyCertificate(result);

        assertFalse(result.isWinning());
        assertTrue(report.violations().toString(), report.isComplete());
        assertTrue(report.violations().toString(), report.isValid());
        assertEquals(
                IndependentExplicitStrongSolver.INDEPENDENT_CERTIFICATE_BASIS,
                report.basis());
    }

    @Test
    public void independentlyAcceptsUnrealizableDecisionAndLosingRegion() {
        FineGrainedUpdateProblem<String, String> problem =
                simpleProblem(false);
        OtfDucsResult<CanonicalUpdateConfiguration<String, String>, String,
                GoalSignature<String, String>> result =
                FineGrainedOtfDucs.synthesizeTrustedEndpointProjections(problem);

        IndependentExplicitStrongSolver.VerificationReport report =
                verifier(problem).verify(result);

        assertFalse(result.isWinning());
        assertTrue(report.violations().toString(), report.isComplete());
        assertTrue(report.violations().toString(), report.isValid());
    }

    @Test
    public void independentGameBundleExportsCompleteWinningAndLosingGraphs() {
        Map<String, Object> winning =
                IndependentStrongGameBundleExporter.export(
                        simpleProblem(true), true, 100L, 1000L);
        Map<String, Object> losing =
                IndependentStrongGameBundleExporter.export(
                        simpleProblem(false), false, 100L, 1000L);

        assertEquals(
                IndependentStrongGameBundleExporter.SCHEMA_VERSION,
                winning.get("schema_version"));
        assertEquals("realizable", winning.get("claimed_decision"));
        assertEquals("unrealizable", losing.get("claimed_decision"));
        assertTrue(((Number) winning.get("state_count")).longValue() >= 3L);
        assertTrue(((Number) winning.get("query_count")).longValue() >= 2L);
        assertFalse(((java.util.List<?>) winning.get("initial_state_ids")).isEmpty());
        assertFalse(((java.util.List<?>) winning.get("goal_state_ids")).isEmpty());
        assertTrue(((java.util.List<?>) losing.get("goal_state_ids")).isEmpty());
    }

    @Test
    public void independentSemanticsMatchesProductionOnEveryReachableBucket() {
        FineGrainedUpdateProblem<String, String> problem =
                branchingProblem();
        FineGrainedSuccessorOracle<String, String> production =
                new FineGrainedSuccessorOracle<String, String>(problem);
        IndependentFineGrainedSemantics<String, String> reference =
                new IndependentFineGrainedSemantics<String, String>(problem);
        Set<CanonicalUpdateConfiguration<String, String>> seen =
                new LinkedHashSet<CanonicalUpdateConfiguration<String, String>>();
        Deque<CanonicalUpdateConfiguration<String, String>> queue =
                new ArrayDeque<CanonicalUpdateConfiguration<String, String>>();
        queue.addAll(problem.initialConfigurations());
        seen.addAll(problem.initialConfigurations());

        while (!queue.isEmpty()) {
            CanonicalUpdateConfiguration<String, String> state =
                    queue.removeFirst();
            assertEquals(
                    production.isSafe(state),
                    reference.isSafe(state));
            assertEquals(
                    production.isGoal(state),
                    reference.isGoal(state));
            assertEquals(
                    new LinkedHashSet<String>(
                            production.candidateActions(state)),
                    new LinkedHashSet<String>(
                            reference.candidateActions(state)));
            for (String action : reference.candidateActions(state)) {
                Set<CanonicalUpdateConfiguration<String, String>> expected =
                        reference.post(state, action);
                assertEquals(expected, production.post(state, action));
                for (CanonicalUpdateConfiguration<String, String> target
                        : expected) {
                    if (seen.add(target)) {
                        queue.addLast(target);
                    }
                }
            }
        }
        assertTrue(seen.size() >= 4);
    }

    @Test
    public void independentlyRejectsRankMutation() {
        FineGrainedUpdateProblem<String, String> problem =
                simpleProblem(true);
        OtfDucsResult<CanonicalUpdateConfiguration<String, String>, String,
                GoalSignature<String, String>> result =
                FineGrainedOtfDucs.synthesizeTrustedEndpointProjections(problem);
        OtfDucsResult.WinningCertificate<
                CanonicalUpdateConfiguration<String, String>,
                String,
                GoalSignature<String, String>> original =
                result.winningCertificate();
        Map<CanonicalUpdateConfiguration<String, String>, Integer> ranks =
                new LinkedHashMap<CanonicalUpdateConfiguration<String, String>,
                        Integer>(original.ranks());
        for (CanonicalUpdateConfiguration<String, String> root
                : original.initialStates()) {
            ranks.put(root, Integer.valueOf(0));
        }
        OtfDucsResult.WinningCertificate<
                CanonicalUpdateConfiguration<String, String>,
                String,
                GoalSignature<String, String>> mutantCertificate =
                new OtfDucsResult.WinningCertificate<
                        CanonicalUpdateConfiguration<String, String>,
                        String,
                        GoalSignature<String, String>>(
                        original.initialStates(),
                        ranks,
                        original.strategy(),
                        original.goalMatches());
        OtfDucsResult<CanonicalUpdateConfiguration<String, String>, String,
                GoalSignature<String, String>> mutant =
                OtfDucsResult.winning(
                        mutantCertificate,
                        result.statistics());

        IndependentExplicitStrongSolver.VerificationReport report =
                verifier(problem).verify(mutant);

        assertTrue(report.isComplete());
        assertFalse(report.isValid());
        assertTrue(report.violations().toString(),
                report.violations().contains(
                        "certificate edge does not decrease rank"));
    }

    @Test
    public void independentCertificateProofRejectsRankMutation() {
        FineGrainedUpdateProblem<String, String> problem =
                simpleProblem(true);
        OtfDucsResult<CanonicalUpdateConfiguration<String, String>, String,
                GoalSignature<String, String>> result =
                FineGrainedOtfDucs.synthesizeTrustedEndpointProjections(problem);
        OtfDucsResult.WinningCertificate<
                CanonicalUpdateConfiguration<String, String>,
                String,
                GoalSignature<String, String>> original =
                result.winningCertificate();
        Map<CanonicalUpdateConfiguration<String, String>, Integer> ranks =
                new LinkedHashMap<CanonicalUpdateConfiguration<String, String>,
                        Integer>(original.ranks());
        for (CanonicalUpdateConfiguration<String, String> root
                : original.initialStates()) {
            ranks.put(root, Integer.valueOf(0));
        }
        OtfDucsResult<CanonicalUpdateConfiguration<String, String>, String,
                GoalSignature<String, String>> mutant =
                OtfDucsResult.winning(
                        new OtfDucsResult.WinningCertificate<
                                CanonicalUpdateConfiguration<String, String>,
                                String,
                                GoalSignature<String, String>>(
                                original.initialStates(),
                                ranks,
                                original.strategy(),
                                original.goalMatches()),
                        result.statistics());

        IndependentExplicitStrongSolver.VerificationReport report =
                verifier(problem).verifyCertificate(mutant);

        assertTrue(report.isComplete());
        assertFalse(report.isValid());
        assertTrue(report.violations().toString(),
                report.violations().contains(
                        "certificate edge does not decrease rank"));
    }

    @Test
    public void independentCertificateProofRejectsControllableChoiceWhileUncontrollableEnabled() {
        FineGrainedUpdateProblem<String, String> problem =
                winningUncontrollableProblem();
        OtfDucsResult<CanonicalUpdateConfiguration<String, String>, String,
                GoalSignature<String, String>> result =
                FineGrainedOtfDucs.synthesizeTrustedEndpointProjections(problem);
        OtfDucsResult.WinningCertificate<
                CanonicalUpdateConfiguration<String, String>,
                String,
                GoalSignature<String, String>> original =
                result.winningCertificate();
        CanonicalUpdateConfiguration<String, String> root =
                original.initialStates().iterator().next();
        IndependentFineGrainedSemantics<String, String> semantics =
                new IndependentFineGrainedSemantics<String, String>(problem);
        Map<CanonicalUpdateConfiguration<String, String>,
                Map<String, Set<CanonicalUpdateConfiguration<String, String>>>>
                strategy =
                new LinkedHashMap<CanonicalUpdateConfiguration<String, String>,
                        Map<String, Set<
                                CanonicalUpdateConfiguration<String, String>>>>(
                        original.strategy());
        Map<String, Set<CanonicalUpdateConfiguration<String, String>>>
                invalidRoot =
                new LinkedHashMap<String,
                        Set<CanonicalUpdateConfiguration<String, String>>>();
        invalidRoot.put("rho", semantics.post(root, "rho"));
        strategy.put(root, invalidRoot);
        OtfDucsResult<CanonicalUpdateConfiguration<String, String>, String,
                GoalSignature<String, String>> mutant =
                OtfDucsResult.winning(
                        new OtfDucsResult.WinningCertificate<
                                CanonicalUpdateConfiguration<String, String>,
                                String,
                                GoalSignature<String, String>>(
                                original.initialStates(),
                                original.ranks(),
                                strategy,
                                original.goalMatches()),
                        result.statistics());

        IndependentExplicitStrongSolver.VerificationReport report =
                verifier(problem).verifyCertificate(mutant);

        assertTrue(report.isComplete());
        assertFalse(report.isValid());
        assertTrue(report.violations().toString(),
                report.violations().contains(
                        "certificate does not retain exactly all "
                                + "uncontrollable buckets"));
    }

    @Test
    public void independentCertificateProofRejectsLosingRegionWithoutRoot() {
        FineGrainedUpdateProblem<String, String> problem =
                simpleProblem(false);
        OtfDucsResult<CanonicalUpdateConfiguration<String, String>, String,
                GoalSignature<String, String>> result =
                FineGrainedOtfDucs.synthesizeTrustedEndpointProjections(problem);
        Set<CanonicalUpdateConfiguration<String, String>> losing =
                new LinkedHashSet<CanonicalUpdateConfiguration<String, String>>(
                        result.losingCertificate().losingStates());
        losing.removeAll(problem.initialConfigurations());
        OtfDucsResult<CanonicalUpdateConfiguration<String, String>, String,
                GoalSignature<String, String>> mutant =
                OtfDucsResult.losing(
                        new OtfDucsResult.LosingCertificate<
                                CanonicalUpdateConfiguration<String, String>>(
                                losing),
                        result.statistics());

        IndependentExplicitStrongSolver.VerificationReport report =
                verifier(problem).verifyCertificate(mutant);

        assertTrue(report.isComplete());
        assertFalse(report.isValid());
        assertTrue(report.violations().toString(),
                report.violations().contains(
                        "losing certificate contains no initial root"));
    }

    @Test
    public void referenceLimitIsReportedAsInconclusiveNotAsFailure() {
        FineGrainedUpdateProblem<String, String> problem =
                simpleProblem(true);
        OtfDucsResult<CanonicalUpdateConfiguration<String, String>, String,
                GoalSignature<String, String>> result =
                FineGrainedOtfDucs.synthesizeTrustedEndpointProjections(problem);

        IndependentExplicitStrongSolver.VerificationReport report =
                new IndependentExplicitStrongSolver<String, String>(
                        problem, 1L, 1L).verify(result);

        assertFalse(report.isComplete());
        assertFalse(report.isValid());
        assertTrue(report.reason().contains("limit"));
    }

    @Test
    public void randomizedSmallFineGrainedGamesAgreeWithIndependentSemantics() {
        Random random = new Random(2027072402L);
        for (int sample = 0; sample < 250; sample++) {
            FineGrainedUpdateProblem<String, String> problem =
                    randomProblem(random, sample);
            assertSemanticAgreement(problem);
            FineGrainedSuccessorOracle<String, String> game =
                    new FineGrainedSuccessorOracle<String, String>(problem);
            OtfDucsResult<
                    CanonicalUpdateConfiguration<String, String>,
                    String,
                    GoalSignature<String, String>> result =
                    new OtfDucsSynthesizer<
                            CanonicalUpdateConfiguration<String, String>,
                            String,
                            GoalSignature<String, String>>(
                            game, 0, 0).synthesize();
            IndependentExplicitStrongSolver.VerificationReport report =
                    verifier(problem).verify(result);
            assertTrue(
                    "sample " + sample + ": "
                            + report.violations(),
                    report.isValid());
        }
    }

    private static IndependentExplicitStrongSolver<String, String> verifier(
            FineGrainedUpdateProblem<String, String> problem) {
        return new IndependentExplicitStrongSolver<String, String>(
                problem, 10_000L, 100_000L);
    }

    private static FineGrainedUpdateProblem<String, String> simpleProblem(
            boolean withFinish) {
        FiniteLts.Builder<String> newer =
                FiniteLts.<String>builder("n0").addState("n1");
        if (withFinish) {
            newer.addTransition("n0", "finish", "n1");
        }
        VersionedComponent<String> component =
                new VersionedComponent<String>(
                        "C",
                        FiniteLts.<String>builder("old").build(),
                        newer.build(),
                        Collections.singletonMap(
                                "old",
                                Collections.singleton("n0")),
                        "rho");
        FineGrainedUpdateProblem.Builder<String, String> builder =
                FineGrainedUpdateProblem.<String, String>builder()
                        .addComponent(component)
                        .addInitialSnapshot(
                                new InitialSnapshot<String, String>(
                                        PhysicalState.of(
                                                TaggedState.oldState("old")),
                                        Collections.<String, String>emptyMap()))
                        .addGoalSignature(
                                new GoalSignature<String, String>(
                                        "post",
                                        PhysicalState.of(
                                                TaggedState.newState("n1")),
                                        Collections.<String, String>emptyMap()));
        if (withFinish) {
            builder.controllableNormalActions(
                    Collections.singleton("finish"));
        }
        return builder.build();
    }

    private static FineGrainedUpdateProblem<String, String> branchingProblem() {
        FiniteLts<String> oldLts = FiniteLts.<String>builder("old0")
                .addTransition("old0", "u", "old1")
                .addTransition("old1", "u", "old1")
                .build();
        FiniteLts<String> newLts = FiniteLts.<String>builder("new0")
                .addTransition("new0", "c", "new1")
                .addTransition("new0", "u", "new0")
                .addTransition("new1", "u", "new1")
                .build();
        Map<String, Set<String>> transfer =
                new LinkedHashMap<String, Set<String>>();
        transfer.put("old0", setOf("new0", "new1"));
        transfer.put("old1", Collections.singleton("new1"));
        VersionedComponent<String> component =
                new VersionedComponent<String>(
                        "C", oldLts, newLts, transfer, "rho");
        return FineGrainedUpdateProblem.<String, String>builder()
                .addComponent(component)
                .controllableNormalActions(Collections.singleton("c"))
                .addInitialSnapshot(new InitialSnapshot<String, String>(
                        PhysicalState.of(TaggedState.oldState("old0")),
                        Collections.<String, String>emptyMap()))
                .addGoalSignature(new GoalSignature<String, String>(
                        "post",
                        PhysicalState.of(TaggedState.newState("new1")),
                        Collections.<String, String>emptyMap()))
                .build();
    }

    private static FineGrainedUpdateProblem<String, String>
            winningUncontrollableProblem() {
        FiniteLts<String> oldLts = FiniteLts.<String>builder("old0")
                .addTransition("old0", "u", "old1")
                .build();
        FiniteLts<String> newLts =
                FiniteLts.<String>builder("new0").build();
        Map<String, Set<String>> transfer =
                new LinkedHashMap<String, Set<String>>();
        transfer.put("old0", Collections.singleton("new0"));
        transfer.put("old1", Collections.singleton("new0"));
        VersionedComponent<String> component =
                new VersionedComponent<String>(
                        "C", oldLts, newLts, transfer, "rho");
        return FineGrainedUpdateProblem.<String, String>builder()
                .addComponent(component)
                .addInitialSnapshot(new InitialSnapshot<String, String>(
                        PhysicalState.of(TaggedState.oldState("old0")),
                        Collections.<String, String>emptyMap()))
                .addGoalSignature(new GoalSignature<String, String>(
                        "post",
                        PhysicalState.of(TaggedState.newState("new0")),
                        Collections.<String, String>emptyMap()))
                .build();
    }

    private static FineGrainedUpdateProblem<String, String> randomProblem(
            Random random,
            int sample) {
        int componentCount = 1 + random.nextInt(2);
        FineGrainedUpdateProblem.Builder<String, String> builder =
                FineGrainedUpdateProblem.<String, String>builder();
        Set<String> controllable = new LinkedHashSet<String>();
        java.util.List<TaggedState<String>> initial =
                new java.util.ArrayList<TaggedState<String>>();
        java.util.List<TaggedState<String>> goal =
                new java.util.ArrayList<TaggedState<String>>();
        for (int componentIndex = 0;
                componentIndex < componentCount;
                componentIndex++) {
            String prefix = "s" + sample + "_c" + componentIndex;
            String old0 = prefix + "_o0";
            String old1 = prefix + "_o1";
            String new0 = prefix + "_n0";
            String new1 = prefix + "_n1";
            String controlled = prefix + "_controlled";
            String uncontrolled = prefix + "_uncontrolled";
            FiniteLts.Builder<String> oldLts =
                    FiniteLts.<String>builder(old0).addState(old1);
            FiniteLts.Builder<String> newLts =
                    FiniteLts.<String>builder(new0).addState(new1);
            boolean controlledUsed = false;
            if (random.nextBoolean()) {
                oldLts.addTransition(old0, uncontrolled, old1);
            }
            if (random.nextBoolean()) {
                oldLts.addTransition(old1, controlled, old0);
                controlledUsed = true;
            }
            if (random.nextBoolean()) {
                newLts.addTransition(new0, controlled, new1);
                controlledUsed = true;
            }
            if (random.nextBoolean()) {
                newLts.addTransition(new1, uncontrolled, new0);
            }
            if (random.nextBoolean()) {
                newLts.addTransition(new0, uncontrolled, new0);
            }
            if (controlledUsed) {
                controllable.add(controlled);
            }
            Map<String, Set<String>> transfer =
                    new LinkedHashMap<String, Set<String>>();
            transfer.put(old0, randomTargets(random, new0, new1));
            transfer.put(old1, randomTargets(random, new0, new1));
            String reconfigure = prefix + "_rho";
            builder.addComponent(new VersionedComponent<String>(
                    prefix,
                    oldLts.build(),
                    newLts.build(),
                    transfer,
                    reconfigure));
            initial.add(TaggedState.oldState(
                    random.nextBoolean() ? old0 : old1));
            goal.add(TaggedState.newState(
                    random.nextBoolean() ? new0 : new1));
            if (componentIndex > 0 && random.nextBoolean()) {
                builder.addPrecedence(
                        "s" + sample + "_c"
                                + (componentIndex - 1) + "_rho",
                        reconfigure);
            }
        }
        return builder
                .controllableNormalActions(controllable)
                .addInitialSnapshot(new InitialSnapshot<String, String>(
                        PhysicalState.of(initial),
                        Collections.<String, String>emptyMap()))
                .addGoalSignature(new GoalSignature<String, String>(
                        "goal-" + sample,
                        PhysicalState.of(goal),
                        Collections.<String, String>emptyMap()))
                .build();
    }

    private static Set<String> randomTargets(
            Random random,
            String first,
            String second) {
        Set<String> result = new LinkedHashSet<String>();
        if (random.nextBoolean()) {
            result.add(first);
        }
        if (random.nextBoolean()) {
            result.add(second);
        }
        return result;
    }

    private static void assertSemanticAgreement(
            FineGrainedUpdateProblem<String, String> problem) {
        FineGrainedSuccessorOracle<String, String> production =
                new FineGrainedSuccessorOracle<String, String>(problem);
        IndependentFineGrainedSemantics<String, String> reference =
                new IndependentFineGrainedSemantics<String, String>(problem);
        Set<CanonicalUpdateConfiguration<String, String>> seen =
                new LinkedHashSet<CanonicalUpdateConfiguration<String, String>>();
        Deque<CanonicalUpdateConfiguration<String, String>> queue =
                new ArrayDeque<CanonicalUpdateConfiguration<String, String>>();
        seen.addAll(reference.initialStates());
        queue.addAll(reference.initialStates());
        while (!queue.isEmpty()) {
            CanonicalUpdateConfiguration<String, String> state =
                    queue.removeFirst();
            assertEquals(production.isSafe(state), reference.isSafe(state));
            assertEquals(production.isGoal(state), reference.isGoal(state));
            Set<String> actions = new LinkedHashSet<String>(
                    reference.candidateActions(state));
            assertEquals(
                    new LinkedHashSet<String>(
                            production.candidateActions(state)),
                    actions);
            for (String action : actions) {
                Set<CanonicalUpdateConfiguration<String, String>> expected =
                        reference.post(state, action);
                assertEquals(expected, production.post(state, action));
                for (CanonicalUpdateConfiguration<String, String> target
                        : expected) {
                    if (seen.add(target)) {
                        queue.addLast(target);
                    }
                }
            }
        }
    }

    @SafeVarargs
    private static <T> Set<T> setOf(T... values) {
        LinkedHashSet<T> result = new LinkedHashSet<T>();
        Collections.addAll(result, values);
        return result;
    }
}
