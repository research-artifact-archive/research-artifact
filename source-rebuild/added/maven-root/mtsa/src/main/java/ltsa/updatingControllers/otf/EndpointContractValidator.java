package ltsa.updatingControllers.otf;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.function.Function;

/**
 * Validates the two fixed endpoint closed loops before update synthesis.
 *
 * <p>This check is deliberately independent of whether the update game is
 * winning.  Invalid endpoint controllers must therefore be reported as an
 * input-contract failure instead of being hidden behind a losing update
 * result.</p>
 */
public final class EndpointContractValidator {

    private EndpointContractValidator() {
        // Utility class.
    }

    public static <ZO, S, M, ZN> void validate(
            FiniteLts<ZO> oldClosedLoop,
            FiniteLts<ZN> newClosedLoop,
            FineGrainedUpdateProblem<S, M> problem,
            Function<? super ZO, ? extends InitialSnapshot<S, M>> initialProjection,
            Function<? super ZN, ? extends GoalSignature<S, M>> goalProjection) {
        List<String> violations = violations(
                oldClosedLoop, newClosedLoop, problem,
                initialProjection, goalProjection);
        if (!violations.isEmpty()) {
            throw new IllegalArgumentException(
                    "Invalid FG-DUCS endpoint contract: "
                            + String.join("; ", violations));
        }
    }

    public static <ZO, S, M, ZN> List<String> violations(
            FiniteLts<ZO> oldClosedLoop,
            FiniteLts<ZN> newClosedLoop,
            FineGrainedUpdateProblem<S, M> problem,
            Function<? super ZO, ? extends InitialSnapshot<S, M>> initialProjection,
            Function<? super ZN, ? extends GoalSignature<S, M>> goalProjection) {
        List<String> result = new ArrayList<String>();
        if (oldClosedLoop == null || newClosedLoop == null || problem == null
                || initialProjection == null || goalProjection == null) {
            result.add("endpoint validation input contains null");
            return Collections.unmodifiableList(result);
        }
        if (!problem.hasExhaustiveEndpointCoverage()) {
            result.add("endpoint states were not exhaustively enumerated from reachable LTSs");
        }
        if (!problem.normalActions().containsAll(oldClosedLoop.alphabet())
                || !problem.normalActions().containsAll(newClosedLoop.alphabet())) {
            result.add("endpoint closed-loop alphabets contain non-normal actions");
        }

        Map<ZO, InitialSnapshot<S, M>> oldProjection = new LinkedHashMap<>();
        Set<CanonicalUpdateConfiguration<S, M>> roots = new LinkedHashSet<>();
        for (ZO state : oldClosedLoop.reachableStates()) {
            if (oldClosedLoop.enabledActions(state).isEmpty()) {
                result.add("old closed loop is deadlocked at " + state);
            }
            try {
                InitialSnapshot<S, M> snapshot = Objects.requireNonNull(
                        initialProjection.apply(state),
                        "initial projection for " + state);
                oldProjection.put(state, snapshot);
                roots.add(LinkedOtfDucsController.resolveInitial(problem, snapshot));
            } catch (RuntimeException error) {
                result.add("invalid old endpoint projection at " + state
                        + ": " + message(error));
            }
        }
        if (!roots.equals(new LinkedHashSet<CanonicalUpdateConfiguration<S, M>>(
                problem.initialConfigurations()))) {
            result.add("old endpoint projection does not cover exactly all initial roots");
        }

        Map<ZN, GoalSignature<S, M>> newProjection = new LinkedHashMap<>();
        Set<GoalSignature<S, M>> declaredGoals =
                new LinkedHashSet<GoalSignature<S, M>>(problem.goalSignatures());
        Set<GoalSignature<S, M>> coveredGoals = new LinkedHashSet<>();
        Set<String> endpointIds = new LinkedHashSet<>();
        for (ZN state : newClosedLoop.reachableStates()) {
            if (newClosedLoop.enabledActions(state).isEmpty()) {
                result.add("new closed loop is deadlocked at " + state);
            }
            try {
                GoalSignature<S, M> signature = Objects.requireNonNull(
                        goalProjection.apply(state),
                        "goal projection for " + state);
                newProjection.put(state, signature);
                if (!endpointIds.add(signature.endpointId())) {
                    result.add("duplicate new endpoint id: " + signature.endpointId());
                }
                if (declaredGoals.contains(signature)) {
                    coveredGoals.add(signature);
                }
            } catch (RuntimeException error) {
                result.add("invalid new endpoint projection at " + state
                        + ": " + message(error));
            }
        }
        if (!coveredGoals.equals(declaredGoals)) {
            result.add("new endpoint projection does not cover every loadable goal signature");
        }

        checkProjectionTransitions(
                "old", oldClosedLoop, problem, oldProjection,
                problem.oldRequirementIds(), true, result);
        checkProjectionTransitions(
                "new", newClosedLoop, problem, newProjection,
                problem.newRequirementIds(), false, result);
        return Collections.unmodifiableList(result);
    }

    private static <Z, S, M, P> void checkProjectionTransitions(
            String label,
            FiniteLts<Z> endpoint,
            FineGrainedUpdateProblem<S, M> problem,
            Map<Z, P> projections,
            Set<String> requirementIds,
            boolean old,
            List<String> violations) {
        for (Z source : endpoint.reachableStates()) {
            P projectedSource = projections.get(source);
            if (projectedSource == null) {
                continue;
            }
            PhysicalState<S> physical = old
                    ? ((InitialSnapshot<S, M>) projectedSource).physicalState()
                    : ((GoalSignature<S, M>) projectedSource).physicalState();
            Map<String, M> testerStates = old
                    ? ((InitialSnapshot<S, M>) projectedSource).oldRequirementStates()
                    : ((GoalSignature<S, M>) projectedSource).newRequirementStates();
            for (String action : problem.normalActions()) {
                Set<ProjectionKey<S, M>> expected;
                try {
                    expected = projectedPost(
                            problem, physical, testerStates,
                            requirementIds, action);
                } catch (RuntimeException error) {
                    violations.add(label + " endpoint projection failed at "
                            + source + " / " + action + ": " + message(error));
                    continue;
                }
                Set<ProjectionKey<S, M>> actual = new LinkedHashSet<>();
                for (Z target : endpoint.successors(source, action)) {
                    P projectedTarget = projections.get(target);
                    if (projectedTarget == null) {
                        violations.add(label
                                + " endpoint transition leaves its reachable projection at "
                                + source + " / " + action);
                        continue;
                    }
                    PhysicalState<S> targetPhysical = old
                            ? ((InitialSnapshot<S, M>) projectedTarget).physicalState()
                            : ((GoalSignature<S, M>) projectedTarget).physicalState();
                    Map<String, M> targetTesters = old
                            ? ((InitialSnapshot<S, M>) projectedTarget)
                                    .oldRequirementStates()
                            : ((GoalSignature<S, M>) projectedTarget)
                                    .newRequirementStates();
                    actual.add(new ProjectionKey<S, M>(targetPhysical, targetTesters));
                }
                boolean controllable =
                        problem.controllableNormalActions().contains(action);
                if (!actual.isEmpty() && !actual.equals(expected)) {
                    violations.add(label
                            + " endpoint does not preserve every environment outcome at "
                            + source + " / " + action);
                }
                else if (!controllable && !expected.isEmpty() && actual.isEmpty()) {
                    violations.add(label + " endpoint disables uncontrollable action at "
                            + source + " / " + action);
                }
            }
        }
    }

    private static <S, M> Set<ProjectionKey<S, M>> projectedPost(
            FineGrainedUpdateProblem<S, M> problem,
            PhysicalState<S> physical,
            Map<String, M> testerStates,
            Set<String> requirementIds,
            String action) {
        Set<PhysicalState<S>> physicalOutcomes = physicalPost(problem, physical, action);
        if (physicalOutcomes.isEmpty()) {
            return Collections.emptySet();
        }
        Map<String, M> testerOutcome = new LinkedHashMap<>();
        for (String id : requirementIds) {
            Requirement<S, M> requirement = problem.requirementsById().get(id);
            M source = testerStates.get(id);
            if (source == null) {
                throw new IllegalArgumentException(
                        "endpoint projection omits tester state for " + id);
            }
            testerOutcome.put(
                    id, requirement.tester().stepOrStutter(source, action));
        }
        Set<ProjectionKey<S, M>> result = new LinkedHashSet<>();
        for (PhysicalState<S> outcome : physicalOutcomes) {
            result.add(new ProjectionKey<S, M>(outcome, testerOutcome));
        }
        return result;
    }

    private static <S, M> Set<PhysicalState<S>> physicalPost(
            FineGrainedUpdateProblem<S, M> problem,
            PhysicalState<S> physical,
            String action) {
        List<List<TaggedState<S>>> localOutcomes = new ArrayList<>();
        boolean participant = false;
        for (int index = 0; index < physical.size(); index++) {
            TaggedState<S> tagged = physical.component(index);
            VersionedComponent<S> component = problem.components().get(index);
            FiniteLts<S> active = tagged.isOld()
                    ? component.oldLts()
                    : component.newLts();
            List<TaggedState<S>> choices = new ArrayList<>();
            /*
             * The first augmented component may contain observer-only
             * transitions for actions owned by another physical component.
             * Such a transition must follow an enabled shared event, but it
             * must not enable that event by itself.  This is the same split
             * used by FineGrainedSuccessorOracle: environmentHasAction marks
             * a physical participant, while hasAction advances every
             * synchronizing observer.
             */
            if (component.environmentHasAction(tagged.version(), action)) {
                participant = true;
            }
            if (active.hasAction(action)) {
                for (S target : active.successors(tagged.state(), action)) {
                    choices.add(tagged.isOld()
                            ? TaggedState.oldState(target)
                            : TaggedState.newState(target));
                }
                if (choices.isEmpty()) {
                    return Collections.emptySet();
                }
            } else {
                choices.add(tagged);
            }
            localOutcomes.add(choices);
        }
        if (!participant) {
            return Collections.emptySet();
        }
        Set<PhysicalState<S>> result = new LinkedHashSet<>();
        cartesian(localOutcomes, 0, new ArrayList<TaggedState<S>>(), result);
        return result;
    }

    private static <S> void cartesian(
            List<List<TaggedState<S>>> choices,
            int index,
            List<TaggedState<S>> current,
            Set<PhysicalState<S>> result) {
        if (index == choices.size()) {
            result.add(PhysicalState.of(current));
            return;
        }
        for (TaggedState<S> choice : choices.get(index)) {
            current.add(choice);
            cartesian(choices, index + 1, current, result);
            current.remove(current.size() - 1);
        }
    }

    private static String message(RuntimeException error) {
        String text = error.getMessage();
        return text == null || text.trim().isEmpty()
                ? error.getClass().getSimpleName()
                : text;
    }

    private static final class ProjectionKey<S, M> {
        private final PhysicalState<S> physical;
        private final Map<String, M> testers;

        private ProjectionKey(
                PhysicalState<S> physical,
                Map<String, M> testers) {
            this.physical = Objects.requireNonNull(physical, "physical");
            this.testers = Collections.unmodifiableMap(
                    new LinkedHashMap<String, M>(testers));
        }

        @Override
        public boolean equals(Object other) {
            if (this == other) {
                return true;
            }
            if (!(other instanceof ProjectionKey)) {
                return false;
            }
            ProjectionKey<?, ?> that = (ProjectionKey<?, ?>) other;
            return physical.equals(that.physical) && testers.equals(that.testers);
        }

        @Override
        public int hashCode() {
            return 31 * physical.hashCode() + testers.hashCode();
        }
    }
}
