package ltsa.updatingControllers.otf;

import org.testng.annotations.Test;

import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.Set;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;

public class ActivationSpecTest {

    @Test
    public void localTesterAlphabetStuttersOverCommonAlphabet() {
        PhysicalState<Integer> oldPhysical = PhysicalState.of(TaggedState.oldState(0));

        SafetyTester<String> tester = SafetyTester.<String>builder()
                .initialState("safe")
                .addErrorState("error")
                .addAction("tick")
                .addTransition("safe", "tick", "safe")
                .addTransition("error", "tick", "error")
                .build();

        TableResidualLanguage<String> residual = residual(false);
        ActivationSpec<Integer, String> activation =
                ActivationSpec.<Integer, String, String>builder(residual)
                        .put(oldPhysical, "safe", "residualSafe")
                        .build();

        FiniteLts<Integer> oldLts = FiniteLts.<Integer>builder(0)
                .addTransition(0, "tick", 0)
                .build();
        FiniteLts<Integer> newLts = FiniteLts.<Integer>builder(1)
                .addTransition(1, "tick", 1)
                .build();
        VersionedComponent<Integer> component = new VersionedComponent<>(
                "component", oldLts, newLts,
                Collections.singletonMap(0, Collections.singleton(1)), "rho");

        Requirement<Integer, String> requirement = Requirement.newRequirement(
                "newSafety", tester, activation, "startNewSafety");

        FineGrainedUpdateProblem<Integer, String> problem =
                FineGrainedUpdateProblem.<Integer, String>builder()
                        .addComponent(component)
                        .addRequirement(requirement)
                        .addInitialSnapshot(new InitialSnapshot<>(oldPhysical, Collections.emptyMap()))
                        .addGoalSignature(new GoalSignature<>(
                                "newEndpoint",
                                PhysicalState.of(TaggedState.newState(1)),
                                Collections.singletonMap("newSafety", "safe")))
                        .build();

        assertNotNull(problem);
        assertEquals("safe", tester.stepOrStutter("safe", "rho"));
        assertEquals(setOf("tick", "rho", "startNewSafety"), problem.commonAlphabet());
    }

    @Test(expectedExceptions = IllegalArgumentException.class)
    public void rejectsResidualThatDisagreesWithTesterStutter() {
        PhysicalState<Integer> state = PhysicalState.of(TaggedState.oldState(0));
        SafetyTester<String> tester = SafetyTester.<String>builder()
                .initialState("safe")
                .addErrorState("error")
                .addAction("tick")
                .addTransition("safe", "tick", "safe")
                .addTransition("error", "tick", "error")
                .build();

        ActivationSpec<Integer, String> activation =
                ActivationSpec.<Integer, String, String>builder(residual(true))
                        .put(state, "safe", "residualSafe")
                        .build();
        activation.validateLanguageEquivalence(tester);
    }

    private static TableResidualLanguage<String> residual(boolean boundaryIsBad) {
        TableResidualLanguage.Builder<String> builder = TableResidualLanguage.<String>builder()
                .initialState("residualSafe")
                .addErrorState("residualError")
                .addActions(setOf("tick", "rho", "startNewSafety"))
                .addTransition("residualSafe", "tick", "residualSafe")
                .addTransition("residualSafe", "rho",
                        boundaryIsBad ? "residualError" : "residualSafe")
                .addTransition("residualSafe", "startNewSafety", "residualSafe");
        for (String action : setOf("tick", "rho", "startNewSafety")) {
            builder.addTransition("residualError", action, "residualError");
        }
        return builder.build();
    }

    private static Set<String> setOf(String... values) {
        Set<String> result = new LinkedHashSet<>();
        Collections.addAll(result, values);
        return result;
    }
}
