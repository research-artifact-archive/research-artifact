package ltsa.updatingControllers.otf;

import org.testng.annotations.Test;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

public class LoadableEndpointSubsetTest {

    @Test
    public void arbitraryReachableNewEndpointSubsetIsUsedAsGoalAndLinks() {
        FiniteLts<String> oldComponent =
                FiniteLts.<String>builder("old")
                        .addTransition("old", "tick", "old")
                        .build();
        FiniteLts<String> newComponent =
                FiniteLts.<String>builder("new0")
                        .addTransition("new0", "tick", "new1")
                        .addTransition("new1", "tick", "new1")
                        .build();
        VersionedComponent<String> component =
                new VersionedComponent<String>(
                        "component",
                        oldComponent,
                        newComponent,
                        Collections.singletonMap(
                                "old",
                                Collections.singleton("new0")),
                        "reconfigure_component");

        PhysicalState<String> old = PhysicalState.of(
                TaggedState.oldState("old"));
        PhysicalState<String> new0 = PhysicalState.of(
                TaggedState.newState("new0"));
        PhysicalState<String> new1 = PhysicalState.of(
                TaggedState.newState("new1"));
        FiniteLts<PhysicalState<String>> oldEndpoint =
                FiniteLts.<PhysicalState<String>>builder(old)
                        .addTransition(old, "tick", old)
                        .build();
        FiniteLts<PhysicalState<String>> newEndpoint =
                FiniteLts.<PhysicalState<String>>builder(new0)
                        .addTransition(new0, "tick", new1)
                        .addTransition(new1, "tick", new1)
                        .build();
        Map<PhysicalState<String>, GoalSignature<String, String>> signatures =
                new LinkedHashMap<PhysicalState<String>,
                        GoalSignature<String, String>>();
        signatures.put(
                new0,
                new GoalSignature<String, String>(
                        "new0", new0, Collections.<String, String>emptyMap()));
        signatures.put(
                new1,
                new GoalSignature<String, String>(
                        "new1", new1, Collections.<String, String>emptyMap()));

        FineGrainedUpdateProblem<String, String> problem =
                FineGrainedUpdateProblem.<String, String>builder()
                        .addComponent(component)
                        .addNormalAction("tick", true)
                        .initialSnapshotsFromReachable(
                                oldEndpoint,
                                state -> new InitialSnapshot<String, String>(
                                        state,
                                        Collections.<String, String>emptyMap()))
                        .goalSignaturesFromReachable(
                                newEndpoint,
                                signatures::get,
                                new1::equals)
                        .build();

        assertTrue(problem.hasExhaustiveEndpointCoverage());
        assertEquals(1, problem.goalSignatures().size());
        assertEquals("new1", problem.goalSignatures().get(0).endpointId());

        OtfDucsResult<
                CanonicalUpdateConfiguration<String, String>,
                String,
                GoalSignature<String, String>> result =
                FineGrainedOtfDucs.synthesize(problem);
        assertTrue(result.isWinning());
        LinkedOtfDucsController<
                PhysicalState<String>,
                String,
                String,
                PhysicalState<String>> linked =
                LinkedOtfDucsController.link(
                        oldEndpoint,
                        newEndpoint,
                        problem,
                        result,
                        state -> new InitialSnapshot<String, String>(
                                state,
                                Collections.<String, String>emptyMap()),
                        signatures::get);
        assertTrue(linked.lts().states().contains(
                LinkedOtfDucsController.State.<
                        PhysicalState<String>, String, String,
                        PhysicalState<String>>post(new0)));
        assertTrue(linked.lts().states().contains(
                LinkedOtfDucsController.State.<
                        PhysicalState<String>, String, String,
                        PhysicalState<String>>post(new1)));
    }
}
