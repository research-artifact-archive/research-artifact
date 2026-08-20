package ltsa.updatingControllers.otf;

import org.testng.annotations.Test;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

import static org.junit.Assert.assertTrue;

public class EndpointContractValidatorTest {

    @Test
    public void rejectsDeadlockedEndpointBeforeSolvingTheUpdateGame() {
        Fixture fixture = fixture(false, false);
        List<String> violations = EndpointContractValidator.violations(
                fixture.oldEndpoint,
                fixture.newEndpoint,
                fixture.problem,
                fixture.oldSnapshots::get,
                fixture.newSignatures::get);

        assertContains(violations, "old closed loop is deadlocked");
        assertContains(violations, "old endpoint disables uncontrollable action");
    }

    @Test
    public void rejectsEndpointThatSuppressesAnUncontrollableEnvironmentAction() {
        Fixture fixture = fixture(true, false);
        List<String> violations = EndpointContractValidator.violations(
                fixture.oldEndpoint,
                fixture.newEndpoint,
                fixture.problem,
                fixture.oldSnapshots::get,
                fixture.newSignatures::get);

        assertContains(violations, "old endpoint disables uncontrollable action");
    }

    @Test
    public void acceptsDeadlockFreeOutcomePreservingEndpoints() {
        Fixture fixture = fixture(true, true);
        List<String> violations = EndpointContractValidator.violations(
                fixture.oldEndpoint,
                fixture.newEndpoint,
                fixture.problem,
                fixture.oldSnapshots::get,
                fixture.newSignatures::get);

        assertTrue(violations.toString(), violations.isEmpty());
    }

    @Test
    public void advancesObserverOnlyTransitionsWithoutLettingThemEnableEvents() {
        FiniteLts<String> oldObserver = FiniteLts.<String>builder("old-observer-0")
                .addTransition("old-observer-0", "idle", "old-observer-0")
                .addTransition("old-observer-0", "pulse", "old-observer-1")
                .addTransition("old-observer-1", "idle", "old-observer-1")
                .addTransition("old-observer-1", "pulse", "old-observer-0")
                .build();
        FiniteLts<String> newObserver = FiniteLts.<String>builder("new-observer-0")
                .addTransition("new-observer-0", "idle", "new-observer-0")
                .addTransition("new-observer-0", "pulse", "new-observer-1")
                .addTransition("new-observer-1", "idle", "new-observer-1")
                .addTransition("new-observer-1", "pulse", "new-observer-0")
                .build();
        VersionedComponent<String> observer = new VersionedComponent<String>(
                "observer",
                oldObserver,
                newObserver,
                Collections.singletonMap(
                        "old-observer-0",
                        Collections.singleton("new-observer-0")),
                "rho-observer",
                Collections.singleton("idle"),
                Collections.singleton("idle"));

        FiniteLts<String> oldOwner = FiniteLts.<String>builder("old-owner")
                .addTransition("old-owner", "pulse", "old-owner")
                .build();
        FiniteLts<String> newOwner = FiniteLts.<String>builder("new-owner")
                .addTransition("new-owner", "pulse", "new-owner")
                .build();
        VersionedComponent<String> owner = new VersionedComponent<String>(
                "owner",
                oldOwner,
                newOwner,
                Collections.singletonMap(
                        "old-owner", Collections.singleton("new-owner")),
                "rho-owner");

        PhysicalState<String> old0 = PhysicalState.of(
                TaggedState.oldState("old-observer-0"),
                TaggedState.oldState("old-owner"));
        PhysicalState<String> old1 = PhysicalState.of(
                TaggedState.oldState("old-observer-1"),
                TaggedState.oldState("old-owner"));
        PhysicalState<String> new0 = PhysicalState.of(
                TaggedState.newState("new-observer-0"),
                TaggedState.newState("new-owner"));
        PhysicalState<String> new1 = PhysicalState.of(
                TaggedState.newState("new-observer-1"),
                TaggedState.newState("new-owner"));
        FiniteLts<PhysicalState<String>> oldEndpoint =
                FiniteLts.<PhysicalState<String>>builder(old0)
                        .addTransition(old0, "pulse", old1)
                        .addTransition(old1, "pulse", old0)
                        .build();
        FiniteLts<PhysicalState<String>> newEndpoint =
                FiniteLts.<PhysicalState<String>>builder(new0)
                        .addTransition(new0, "pulse", new1)
                        .addTransition(new1, "pulse", new0)
                        .build();

        Map<PhysicalState<String>, InitialSnapshot<String, String>> oldSnapshots =
                new LinkedHashMap<>();
        oldSnapshots.put(old0, new InitialSnapshot<String, String>(
                old0, Collections.<String, String>emptyMap()));
        oldSnapshots.put(old1, new InitialSnapshot<String, String>(
                old1, Collections.<String, String>emptyMap()));
        Map<PhysicalState<String>, GoalSignature<String, String>> newSignatures =
                new LinkedHashMap<>();
        newSignatures.put(new0, new GoalSignature<String, String>(
                "new-0", new0, Collections.<String, String>emptyMap()));
        newSignatures.put(new1, new GoalSignature<String, String>(
                "new-1", new1, Collections.<String, String>emptyMap()));

        FineGrainedUpdateProblem<String, String> problem =
                FineGrainedUpdateProblem.<String, String>builder()
                        .addComponent(observer)
                        .addComponent(owner)
                        .addNormalAction("idle", true)
                        .addNormalAction("pulse", true)
                        .initialSnapshotsFromReachable(
                                oldEndpoint, oldSnapshots::get)
                        .goalSignaturesFromReachable(
                                newEndpoint, newSignatures::get)
                        .build();

        List<String> violations = EndpointContractValidator.violations(
                oldEndpoint,
                newEndpoint,
                problem,
                oldSnapshots::get,
                newSignatures::get);
        assertTrue(violations.toString(), violations.isEmpty());
    }

    private static Fixture fixture(
            boolean oldHasIdle,
            boolean oldKeepsUncontrollable) {
        FiniteLts<String> oldComponent = FiniteLts.<String>builder("old")
                .addTransition("old", "idle", "old")
                .addTransition("old", "u", "old")
                .build();
        FiniteLts<String> newComponent = FiniteLts.<String>builder("new")
                .addTransition("new", "idle", "new")
                .addTransition("new", "u", "new")
                .build();
        VersionedComponent<String> component = new VersionedComponent<String>(
                "component",
                oldComponent,
                newComponent,
                Collections.singletonMap("old", Collections.singleton("new")),
                "rho");

        PhysicalState<String> oldPhysical =
                PhysicalState.of(TaggedState.oldState("old"));
        PhysicalState<String> newPhysical =
                PhysicalState.of(TaggedState.newState("new"));
        FiniteLts.Builder<PhysicalState<String>> oldBuilder =
                FiniteLts.<PhysicalState<String>>builder(oldPhysical)
                        .addAction("idle")
                        .addAction("u");
        if (oldHasIdle) {
            oldBuilder.addTransition(oldPhysical, "idle", oldPhysical);
        }
        if (oldKeepsUncontrollable) {
            oldBuilder.addTransition(oldPhysical, "u", oldPhysical);
        }
        FiniteLts<PhysicalState<String>> oldEndpoint = oldBuilder.build();
        FiniteLts<PhysicalState<String>> newEndpoint =
                FiniteLts.<PhysicalState<String>>builder(newPhysical)
                        .addTransition(newPhysical, "idle", newPhysical)
                        .addTransition(newPhysical, "u", newPhysical)
                        .build();

        Map<PhysicalState<String>, InitialSnapshot<String, String>> oldSnapshots =
                new LinkedHashMap<>();
        oldSnapshots.put(oldPhysical, new InitialSnapshot<String, String>(
                oldPhysical, Collections.<String, String>emptyMap()));
        Map<PhysicalState<String>, GoalSignature<String, String>> newSignatures =
                new LinkedHashMap<>();
        newSignatures.put(newPhysical, new GoalSignature<String, String>(
                "new", newPhysical, Collections.<String, String>emptyMap()));

        FineGrainedUpdateProblem<String, String> problem =
                FineGrainedUpdateProblem.<String, String>builder()
                        .addComponent(component)
                        .addNormalAction("idle", true)
                        .addNormalAction("u", false)
                        .initialSnapshotsFromReachable(
                                oldEndpoint, oldSnapshots::get)
                        .goalSignaturesFromReachable(
                                newEndpoint, newSignatures::get)
                        .build();
        return new Fixture(
                problem, oldEndpoint, newEndpoint,
                oldSnapshots, newSignatures);
    }

    private static void assertContains(List<String> values, String fragment) {
        for (String value : values) {
            if (value.contains(fragment)) {
                return;
            }
        }
        throw new AssertionError("Missing '" + fragment + "' in " + values);
    }

    private static final class Fixture {
        private final FineGrainedUpdateProblem<String, String> problem;
        private final FiniteLts<PhysicalState<String>> oldEndpoint;
        private final FiniteLts<PhysicalState<String>> newEndpoint;
        private final Map<PhysicalState<String>, InitialSnapshot<String, String>>
                oldSnapshots;
        private final Map<PhysicalState<String>, GoalSignature<String, String>>
                newSignatures;

        private Fixture(
                FineGrainedUpdateProblem<String, String> problem,
                FiniteLts<PhysicalState<String>> oldEndpoint,
                FiniteLts<PhysicalState<String>> newEndpoint,
                Map<PhysicalState<String>, InitialSnapshot<String, String>> oldSnapshots,
                Map<PhysicalState<String>, GoalSignature<String, String>> newSignatures) {
            this.problem = problem;
            this.oldEndpoint = oldEndpoint;
            this.newEndpoint = newEndpoint;
            this.oldSnapshots = oldSnapshots;
            this.newSignatures = newSignatures;
        }
    }
}
