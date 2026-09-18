package ltsa.updatingControllers.otf;

import java.util.Collections;
import org.testng.annotations.Test;
import static org.junit.Assert.*;

/** Counterexamples with explicit, trusted endpoint projections for the game boundary. */
public class QuiescentUpdateBoundaryTest {
    private FineGrainedUpdateProblem<String, String> problem(
            FiniteLts<String> oldLts, FiniteLts<String> newLts,
            String transferSource, String... targets) {
        FineGrainedUpdateProblem.Builder<String, String> builder =
                FineGrainedUpdateProblem.<String, String>builder()
                .addComponent(new VersionedComponent<String>("cell", oldLts, newLts,
                        Collections.singletonMap(transferSource, Collections.singleton("n")), "rho"))
                .addInitialSnapshot(new InitialSnapshot<String, String>(
                        PhysicalState.of(TaggedState.oldState("o")), Collections.<String, String>emptyMap()));
        for (String target : targets) {
            builder.addGoalSignature(new GoalSignature<String, String>(target,
                    PhysicalState.of(TaggedState.newState(target)), Collections.<String, String>emptyMap()));
        }
        return builder.build();
    }

    private void checkDecision(FineGrainedUpdateProblem<String, String> problem, boolean winning) {
        OtfDucsResult<CanonicalUpdateConfiguration<String, String>, String, GoalSignature<String, String>>
                result = FineGrainedOtfDucs.synthesizeTrustedEndpointProjections(problem);
        assertEquals(winning, result.isWinning());
        assertTrue(new IndependentExplicitStrongSolver<String, String>(problem, 1000L, 10000L).verify(result).isValid());
    }

    @Test
    public void uncontrollableLoopDisablesTransferAtPostBoundary() {
        FineGrainedUpdateProblem<String, String> p = problem(
                FiniteLts.<String>builder("o").addTransition("o", "u", "o").build(),
                FiniteLts.<String>builder("n").build(), "o", "n");
        CanonicalUpdateConfiguration<String, String> root = p.initialConfigurations().get(0);
        assertTrue(new FineGrainedSuccessorOracle<String, String>(p).post(root, "rho").isEmpty());
        assertTrue(new IndependentFineGrainedSemantics<String, String>(p).post(root, "rho").isEmpty());
        checkDecision(p, false);
    }

    @Test
    public void commandBecomesAvailableAfterUncontrollableFinishes() {
        FineGrainedUpdateProblem<String, String> p = problem(
                FiniteLts.<String>builder("o").addTransition("o", "u", "ready").build(),
                FiniteLts.<String>builder("n").build(), "ready", "n");
        FineGrainedSuccessorOracle<String, String> oracle = new FineGrainedSuccessorOracle<String, String>(p);
        CanonicalUpdateConfiguration<String, String> ready =
                oracle.post(p.initialConfigurations().get(0), "u").iterator().next();
        assertEquals(1, oracle.post(ready, "rho").size());
        checkDecision(p, true);
    }

    @Test
    public void matchingGoalWithUncontrollableLoopIsLosing() {
        FineGrainedUpdateProblem<String, String> p = problem(
                FiniteLts.<String>builder("o").build(),
                FiniteLts.<String>builder("n").addTransition("n", "u", "n").build(), "o", "n");
        FineGrainedSuccessorOracle<String, String> oracle = new FineGrainedSuccessorOracle<String, String>(p);
        CanonicalUpdateConfiguration<String, String> matched =
                oracle.post(p.initialConfigurations().get(0), "rho").iterator().next();
        assertFalse(p.goalMatch(matched).isPresent());
        assertFalse(oracle.isGoal(matched));
        assertFalse(new IndependentFineGrainedSemantics<String, String>(p).isGoal(matched));
        checkDecision(p, false);
    }

    @Test
    public void matchedNonquiescentStateContinuesToQuiescentGoal() {
        FineGrainedUpdateProblem<String, String> p = problem(
                FiniteLts.<String>builder("o").build(),
                FiniteLts.<String>builder("n").addTransition("n", "u", "done").build(), "o", "n", "done");
        checkDecision(p, true);
        OtfDucsResult<CanonicalUpdateConfiguration<String, String>, String, GoalSignature<String, String>>
                result = FineGrainedOtfDucs.synthesizeTrustedEndpointProjections(p);
        for (CanonicalUpdateConfiguration<String, String> goal : result.winningCertificate().goalMatches().keySet()) {
            assertEquals("done", goal.physicalState().component(0).state());
        }
        assertEquals(Integer.valueOf(2), result.winningCertificate().ranks().get(p.initialConfigurations().get(0)));
    }

    @Test
    public void disabledSynchronizationDoesNotBlockCommand() {
        FineGrainedUpdateProblem<String, String> p = FineGrainedUpdateProblem.<String, String>builder()
                .addComponent(new VersionedComponent<String>("a",
                        FiniteLts.<String>builder("a").addTransition("a", "u", "a").build(),
                        FiniteLts.<String>builder("an").build(),
                        Collections.singletonMap("a", Collections.singleton("an")), "rhoA"))
                .addComponent(new VersionedComponent<String>("b",
                        FiniteLts.<String>builder("b").addTransition("elsewhere", "u", "elsewhere").build(),
                        FiniteLts.<String>builder("bn").build(),
                        Collections.singletonMap("b", Collections.singleton("bn")), "rhoB"))
                .addInitialSnapshot(new InitialSnapshot<String, String>(
                        PhysicalState.of(TaggedState.oldState("a"), TaggedState.oldState("b")),
                        Collections.<String, String>emptyMap()))
                .addGoalSignature(new GoalSignature<String, String>("post",
                        PhysicalState.of(TaggedState.newState("an"), TaggedState.newState("bn")),
                        Collections.<String, String>emptyMap())).build();
        CanonicalUpdateConfiguration<String, String> root = p.initialConfigurations().get(0);
        assertFalse(p.hasEnabledUncontrollable(root));
        assertEquals(1, new FineGrainedSuccessorOracle<String, String>(p).post(root, "rhoA").size());
        assertEquals(1, new IndependentFineGrainedSemantics<String, String>(p).post(root, "rhoA").size());
        checkDecision(p, true);
    }
}
