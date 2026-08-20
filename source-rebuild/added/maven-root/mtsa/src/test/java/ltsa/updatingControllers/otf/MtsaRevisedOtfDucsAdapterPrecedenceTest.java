package ltsa.updatingControllers.otf;

import ltsa.updatingControllers.structures.UpdateProtocolSpec;
import org.testng.annotations.Test;

import java.util.Collections;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

public class MtsaRevisedOtfDucsAdapterPrecedenceTest {

    @Test
    public void copiesProtocolPrecedenceIntoTheCanonicalProblemBuilder() {
        String firstAction = "reconfigure_A";
        String secondAction = "reconfigure_B";
        UpdateProtocolSpec protocol = UpdateProtocolSpec.forFineGrained(
                null, null);
        protocol.registerReconfigure(0, firstAction);
        protocol.registerReconfigure(1, secondAction);
        protocol.addPrecedence(firstAction, secondAction);

        VersionedComponent<String> first = component(
                "A", "oldA", "newA", firstAction);
        VersionedComponent<String> second = component(
                "B", "oldB", "newB", secondAction);
        FineGrainedUpdateProblem.Builder<String, String> builder =
                FineGrainedUpdateProblem.<String, String>builder()
                        .addComponent(first)
                        .addComponent(second)
                        .addInitialSnapshot(
                                new InitialSnapshot<String, String>(
                                        PhysicalState.of(
                                                TaggedState.oldState("oldA"),
                                                TaggedState.oldState("oldB")),
                                        Collections.<String, String>emptyMap()))
                        .addGoalSignature(
                                new GoalSignature<String, String>(
                                        "post",
                                        PhysicalState.of(
                                                TaggedState.newState("newA"),
                                                TaggedState.newState("newB")),
                                        Collections.<String, String>emptyMap()));

        MtsaRevisedOtfDucsAdapter.addProtocolPrecedence(protocol, builder);
        FineGrainedUpdateProblem<String, String> problem = builder.build();

        assertEquals(
                Collections.singleton(firstAction),
                problem.directPredecessors(secondAction));
        assertTrue(problem.directPredecessors(firstAction).isEmpty());
    }

    @Test
    public void rejectsEndpointControllerThatOmitsAControllableEnvironmentAction() {
        FiniteLts<String> oldEnvironment =
                FiniteLts.<String>builder("old")
                        .addTransition("old", "controlled", "old")
                        .build();
        FiniteLts<String> newEnvironment =
                FiniteLts.<String>builder("new")
                        .addTransition("new", "controlled", "new")
                        .build();
        VersionedComponent<String> component =
                new VersionedComponent<String>(
                        "component",
                        oldEnvironment,
                        newEnvironment,
                        Collections.singletonMap(
                                "old", Collections.singleton("new")),
                        "rho");
        FiniteLts<String> missingActionController =
                FiniteLts.<String>builder("controller")
                        .addTransition("controller", "idle", "controller")
                        .build();
        FiniteLts<String> observingController =
                FiniteLts.<String>builder("controller")
                        .addAction("controlled")
                        .addTransition("controller", "idle", "controller")
                        .build();

        boolean rejected = false;
        try {
            MtsaRevisedOtfDucsAdapter.validateEndpointControllerAlphabets(
                    Collections.singletonList(component),
                    missingActionController,
                    observingController);
        } catch (IllegalArgumentException expected) {
            rejected = expected.getMessage().contains(
                    "old controller alphabet omits environment actions [controlled]");
        }
        assertTrue(
                "A missing controllable environment event must be rejected "
                        + "as an invalid endpoint contract",
                rejected);
    }

    @Test
    public void acceptsEndpointControllersThatObserveTheirEnvironmentAlphabets() {
        VersionedComponent<String> component = componentWithAction(
                "A", "oldA", "newA", "rhoA", "tick");
        FiniteLts<String> controller =
                FiniteLts.<String>builder("controller")
                        .addAction("tick")
                        .addTransition("controller", "idle", "controller")
                        .build();

        MtsaRevisedOtfDucsAdapter.validateEndpointControllerAlphabets(
                Collections.singletonList(component), controller, controller);
    }

    private static VersionedComponent<String> component(
            String id,
            String oldState,
            String newState,
            String action) {
        return new VersionedComponent<String>(
                id,
                FiniteLts.<String>builder(oldState).build(),
                FiniteLts.<String>builder(newState).build(),
                Collections.singletonMap(
                        oldState, Collections.singleton(newState)),
                action);
    }

    private static VersionedComponent<String> componentWithAction(
            String id,
            String oldState,
            String newState,
            String updateAction,
            String normalAction) {
        return new VersionedComponent<String>(
                id,
                FiniteLts.<String>builder(oldState)
                        .addTransition(oldState, normalAction, oldState)
                        .build(),
                FiniteLts.<String>builder(newState)
                        .addTransition(newState, normalAction, newState)
                        .build(),
                Collections.singletonMap(
                        oldState, Collections.singleton(newState)),
                updateAction);
    }
}
