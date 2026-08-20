package ltsa.updatingControllers.otf;

import org.testng.annotations.Test;

import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

public class UpdatePolicyRestrictionTest {

    @Test
    public void aliasesAreAcceptedButReportedWithNonOverclaimingIds() {
        assertEquals(
                UpdatePolicyRestriction.Mode.FULL_FG,
                UpdatePolicyRestriction.Mode.fromPropertyValue(null));
        assertEquals(
                UpdatePolicyRestriction.Mode.CONTIGUOUS_TRANSFER,
                UpdatePolicyRestriction.Mode.fromPropertyValue(
                        "atomic_transfer"));
        assertEquals(
                "contiguous_transfer",
                UpdatePolicyRestriction.Mode.fromPropertyValue(
                        "atomic_transfer").propertyValue());
        assertEquals(
                UpdatePolicyRestriction.Mode.CONTIGUOUS_UPDATE,
                UpdatePolicyRestriction.Mode.fromPropertyValue(
                        "all_coarse"));
        assertEquals(
                UpdatePolicyRestriction.Mode.FIXED_UPDATE_ORDER,
                UpdatePolicyRestriction.Mode.fromPropertyValue(
                        "fixed_sequence"));
        assertEquals(
                UpdatePolicyRestriction.Mode.REQUIREMENT_BLOCK,
                UpdatePolicyRestriction.Mode.fromPropertyValue(
                        "atomic_requirements"));
    }

    @Test
    public void productionCellInterleavingSeparatesFineGrainedFromBlocks() {
        FineGrainedUpdateProblem<String, String> problem =
                productionCellProblem(true);
        OtfDucsResult<CanonicalUpdateConfiguration<String, String>, String,
                GoalSignature<String, String>> unrestricted =
                solve(problem, UpdatePolicyRestriction.Mode.FULL_FG);
        OtfDucsResult<CanonicalUpdateConfiguration<String, String>, String,
                GoalSignature<String, String>> transferBlock =
                solve(
                        problem,
                        UpdatePolicyRestriction.Mode.CONTIGUOUS_TRANSFER);
        OtfDucsResult<CanonicalUpdateConfiguration<String, String>, String,
                GoalSignature<String, String>> updateBlock =
                solve(
                        problem,
                        UpdatePolicyRestriction.Mode.CONTIGUOUS_UPDATE);

        assertTrue(unrestricted.isWinning());
        assertFalse(transferBlock.isWinning());
        assertFalse(updateBlock.isWinning());

        verifyIndependently(
                problem,
                UpdatePolicyRestriction.Mode.FULL_FG,
                unrestricted);
        verifyIndependently(
                problem,
                UpdatePolicyRestriction.Mode.CONTIGUOUS_TRANSFER,
                transferBlock);
        verifyIndependently(
                problem,
                UpdatePolicyRestriction.Mode.CONTIGUOUS_UPDATE,
                updateBlock);
    }

    @Test
    public void restrictionNeverSuppressesAnUncontrollableEventOrOutcome() {
        FineGrainedUpdateProblem<String, String> problem =
                productionCellProblem(false);
        FineGrainedSuccessorOracle<String, String> base =
                new FineGrainedSuccessorOracle<String, String>(problem);
        UpdatePolicyRestriction<String, String> restriction =
                new UpdatePolicyRestriction<String, String>(
                        problem,
                        UpdatePolicyRestriction.Mode.CONTIGUOUS_TRANSFER);
        RestrictedFineGrainedGame<String, String> restricted =
                new RestrictedFineGrainedGame<String, String>(
                        base, restriction);
        CanonicalUpdateConfiguration<String, String> root =
                problem.initialConfigurations().get(0);
        CanonicalUpdateConfiguration<String, String> afterB =
                only(base.post(root, "rhoB"));

        assertFalse(base.isControllable("moveB"));
        assertTrue(restriction.isOutsideActiveBlock(afterB, "moveB"));
        assertTrue(restricted.candidateActions(afterB).contains("moveB"));
        assertEquals(
                base.post(afterB, "moveB"),
                restricted.post(afterB, "moveB"));
        assertFalse(
                "An enabled uncontrollable interruption makes the block "
                        + "discipline fail; the event is not filtered",
                restricted.isSafe(afterB));
        assertFalse(restriction.hasStaticUninterruptedBlockPrecondition());
    }

    @Test
    public void fixedUpdateOrderIsTopologicalButDoesNotClaimFixedScript() {
        FineGrainedUpdateProblem<String, String> problem =
                productionCellProblem(true, true);
        UpdatePolicyRestriction<String, String> restriction =
                new UpdatePolicyRestriction<String, String>(
                        problem,
                        UpdatePolicyRestriction.Mode.FIXED_UPDATE_ORDER);
        List<String> sequence = restriction.fixedSequence();

        assertTrue(sequence.indexOf("rhoB") < sequence.indexOf("rhoA"));
        assertTrue(restriction.interpretation().contains("total_order"));

        CanonicalUpdateConfiguration<String, String> root =
                problem.initialConfigurations().get(0);
        assertTrue(restriction.allows(root, "moveB"));
        assertTrue(restriction.allows(root, "rhoB"));
        assertFalse(restriction.allows(root, "rhoA"));
    }

    @Test
    public void requirementBlockIsExactForControllableAndUncontrollableOutsiders() {
        FineGrainedUpdateProblem<String, String> controllableProblem =
                requirementBlockProblem(true);
        FineGrainedSuccessorOracle<String, String> controllableBase =
                new FineGrainedSuccessorOracle<String, String>(
                        controllableProblem);
        UpdatePolicyRestriction<String, String> controllableRestriction =
                new UpdatePolicyRestriction<String, String>(
                        controllableProblem,
                        UpdatePolicyRestriction.Mode.REQUIREMENT_BLOCK);
        CanonicalUpdateConfiguration<String, String> afterFirstStop =
                only(controllableBase.post(
                        controllableProblem.initialConfigurations().get(0),
                        "stop1"));

        assertTrue(controllableRestriction.allows(
                afterFirstStop, "stop2"));
        assertFalse(controllableRestriction.allows(
                afterFirstStop, "rho"));
        assertFalse(controllableRestriction.allows(
                afterFirstStop, "tick"));

        FineGrainedUpdateProblem<String, String> uncontrollableProblem =
                requirementBlockProblem(false);
        FineGrainedSuccessorOracle<String, String> uncontrollableBase =
                new FineGrainedSuccessorOracle<String, String>(
                        uncontrollableProblem);
        UpdatePolicyRestriction<String, String> uncontrollableRestriction =
                new UpdatePolicyRestriction<String, String>(
                        uncontrollableProblem,
                        UpdatePolicyRestriction.Mode.REQUIREMENT_BLOCK);
        RestrictedFineGrainedGame<String, String> uncontrollableGame =
                new RestrictedFineGrainedGame<String, String>(
                        uncontrollableBase, uncontrollableRestriction);
        CanonicalUpdateConfiguration<String, String> ucAfterFirstStop =
                only(uncontrollableBase.post(
                        uncontrollableProblem.initialConfigurations().get(0),
                        "stop1"));

        assertTrue(uncontrollableGame.candidateActions(
                ucAfterFirstStop).contains("tick"));
        assertFalse(uncontrollableGame.isSafe(ucAfterFirstStop));
    }

    private static OtfDucsResult<
            CanonicalUpdateConfiguration<String, String>,
            String,
            GoalSignature<String, String>> solve(
                    FineGrainedUpdateProblem<String, String> problem,
                    UpdatePolicyRestriction.Mode mode) {
        FineGrainedSuccessorOracle<String, String> base =
                new FineGrainedSuccessorOracle<String, String>(problem);
        UpdatePolicyRestriction<String, String> restriction =
                new UpdatePolicyRestriction<String, String>(problem, mode);
        RestrictedFineGrainedGame<String, String> game =
                new RestrictedFineGrainedGame<String, String>(
                        base, restriction);
        OtfDucsResult<CanonicalUpdateConfiguration<String, String>, String,
                GoalSignature<String, String>> result =
                new OtfDucsSynthesizer<
                        CanonicalUpdateConfiguration<String, String>,
                        String,
                        GoalSignature<String, String>>(game)
                        .synthesize();
        new OtfDucsCertificateChecker<
                CanonicalUpdateConfiguration<String, String>,
                String,
                GoalSignature<String, String>>(game)
                .verify(result)
                .throwIfInvalid();
        return result;
    }

    private static void verifyIndependently(
            FineGrainedUpdateProblem<String, String> problem,
            UpdatePolicyRestriction.Mode mode,
            OtfDucsResult<CanonicalUpdateConfiguration<String, String>, String,
                    GoalSignature<String, String>> result) {
        UpdatePolicyRestriction<String, String> restriction =
                new UpdatePolicyRestriction<String, String>(problem, mode);
        IndependentExplicitStrongSolver.VerificationReport report =
                new IndependentExplicitStrongSolver<String, String>(
                        problem, restriction, 100_000L, 1_000_000L)
                        .verify(result);
        assertTrue(report.reason(), report.isComplete());
        assertTrue(report.violations().toString(), report.isValid());
    }

    private static FineGrainedUpdateProblem<String, String>
            productionCellProblem(boolean movesControllable) {
        return productionCellProblem(movesControllable, false);
    }

    private static FineGrainedUpdateProblem<String, String>
            productionCellProblem(
                    boolean movesControllable,
                    boolean bBeforeA) {
        FiniteLts<String> stationA = FiniteLts.<String>builder("hold")
                .addTransition("hold", "moveB", "empty")
                .addTransition("empty", "moveA", "hold")
                .build();
        FiniteLts<String> stationB = FiniteLts.<String>builder("empty")
                .addTransition("empty", "moveB", "hold")
                .addTransition("hold", "moveA", "empty")
                .build();
        Map<String, Set<String>> emptyTransfer =
                new LinkedHashMap<String, Set<String>>();
        emptyTransfer.put("empty", Collections.singleton("empty"));
        VersionedComponent<String> a = new VersionedComponent<String>(
                "A", stationA, stationA, emptyTransfer, "rhoA");
        VersionedComponent<String> b = new VersionedComponent<String>(
                "B", stationB, stationB, emptyTransfer, "rhoB");

        FineGrainedUpdateProblem.Builder<String, String> builder =
                FineGrainedUpdateProblem.<String, String>builder()
                        .addComponent(a)
                        .addComponent(b)
                        .controllableNormalActions(
                                movesControllable
                                        ? setOf("moveA", "moveB")
                                        : Collections.<String>emptySet())
                        .addInitialSnapshot(
                                new InitialSnapshot<String, String>(
                                        PhysicalState.of(
                                                TaggedState.oldState("hold"),
                                                TaggedState.oldState("empty")),
                                        Collections.<String, String>emptyMap()))
                        .addGoalSignature(
                                new GoalSignature<String, String>(
                                        "post",
                                        PhysicalState.of(
                                                TaggedState.newState("empty"),
                                                TaggedState.newState("hold")),
                                        Collections.<String, String>emptyMap()));
        if (bBeforeA) {
            builder.addPrecedence("rhoB", "rhoA");
        }
        return builder.build();
    }

    private static FineGrainedUpdateProblem<String, String>
            requirementBlockProblem(boolean tickControllable) {
        FiniteLts<String> oldLts = FiniteLts.<String>builder("old")
                .addTransition("old", "tick", "old")
                .build();
        FiniteLts<String> newLts = FiniteLts.<String>builder("new")
                .addTransition("new", "tick", "new")
                .build();
        VersionedComponent<String> component =
                new VersionedComponent<String>(
                        "C",
                        oldLts,
                        newLts,
                        Collections.singletonMap(
                                "old", Collections.singleton("new")),
                        "rho");
        SafetyTester<String> first = SafetyTester.<String>builder()
                .initialState("safe1")
                .build();
        SafetyTester<String> second = SafetyTester.<String>builder()
                .initialState("safe2")
                .build();
        Map<String, String> initialRequirements =
                new LinkedHashMap<String, String>();
        initialRequirements.put("old1", "safe1");
        initialRequirements.put("old2", "safe2");
        return FineGrainedUpdateProblem.<String, String>builder()
                .addComponent(component)
                .addRequirement(Requirement.<String, String>oldRequirement(
                        "old1", first, "stop1"))
                .addRequirement(Requirement.<String, String>oldRequirement(
                        "old2", second, "stop2"))
                .controllableNormalActions(
                        tickControllable
                                ? Collections.singleton("tick")
                                : Collections.<String>emptySet())
                .addInitialSnapshot(new InitialSnapshot<String, String>(
                        PhysicalState.of(TaggedState.oldState("old")),
                        initialRequirements))
                .addGoalSignature(new GoalSignature<String, String>(
                        "post",
                        PhysicalState.of(TaggedState.newState("new")),
                        Collections.<String, String>emptyMap()))
                .build();
    }

    private static <T> T only(Set<T> values) {
        assertEquals(1, values.size());
        return values.iterator().next();
    }

    @SafeVarargs
    private static <T> Set<T> setOf(T... values) {
        return new LinkedHashSet<T>(Arrays.asList(values));
    }
}
