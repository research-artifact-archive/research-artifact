package ltsa.updatingControllers.otf;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.OptionalInt;
import java.util.Set;

/**
 * Executable reference semantics for evaluation.
 *
 * <p>This implementation deliberately does not call
 * {@link FineGrainedSuccessorOracle}. It derives candidates and successors
 * directly from the immutable problem objects so differential tests can detect
 * defects in the production successor implementation.</p>
 */
public final class IndependentFineGrainedSemantics<S, M> {

    private final FineGrainedUpdateProblem<S, M> problem;

    public IndependentFineGrainedSemantics(
            FineGrainedUpdateProblem<S, M> problem) {
        this.problem = Objects.requireNonNull(problem, "problem");
    }

    public Set<CanonicalUpdateConfiguration<S, M>> initialStates() {
        return Collections.unmodifiableSet(
                new LinkedHashSet<CanonicalUpdateConfiguration<S, M>>(
                        problem.initialConfigurations()));
    }

    public boolean isSafe(CanonicalUpdateConfiguration<S, M> state) {
        if (!problem.isStructurallyValid(state)) {
            return false;
        }
        for (Map.Entry<String, M> active
                : state.testerStatesByRequirementId().entrySet()) {
            Requirement<S, M> requirement =
                    problem.requirementsById().get(active.getKey());
            if (requirement == null
                    || requirement.tester().isError(active.getValue())) {
                return false;
            }
        }
        return true;
    }

    public boolean isGoal(CanonicalUpdateConfiguration<S, M> state) {
        return isSafe(state)
                && state.pendingActions().isEmpty()
                && problem.goalMatch(state).isPresent();
    }

    public boolean isControllable(String action) {
        return action != null && problem.isControllable(action);
    }

    public List<String> candidateActions(
            CanonicalUpdateConfiguration<S, M> state) {
        requireCanonical(state);
        LinkedHashSet<String> candidates = new LinkedHashSet<String>();
        PhysicalState<S> physical = state.physicalState();
        for (int index = 0; index < physical.size(); index++) {
            TaggedState<S> tagged = physical.component(index);
            VersionedComponent<S> component = problem.components().get(index);
            for (String action : component.environmentActions(tagged.version())) {
                if (problem.normalActions().contains(action)) {
                    candidates.add(action);
                }
            }
        }
        for (String action : state.pendingActions()) {
            if (problem.isUpdateActionEligible(state, action)) {
                candidates.add(action);
            }
        }
        List<String> ordered = new ArrayList<String>(candidates);
        Collections.sort(ordered);
        return Collections.unmodifiableList(ordered);
    }

    public Set<CanonicalUpdateConfiguration<S, M>> post(
            CanonicalUpdateConfiguration<S, M> state,
            String action) {
        Objects.requireNonNull(action, "action");
        requireCanonical(state);
        if (problem.normalActions().contains(action)) {
            return postNormal(state, action);
        }
        if (!problem.updateActions().contains(action)
                || !problem.isUpdateActionEligible(state, action)) {
            return Collections.emptySet();
        }

        OptionalInt componentIndex =
                problem.componentIndexForReconfigure(action);
        if (componentIndex.isPresent()) {
            return postReconfigure(state, action, componentIndex.getAsInt());
        }
        Optional<Requirement<S, M>> stopped =
                problem.oldRequirementForStopAction(action);
        if (stopped.isPresent()) {
            return postStop(state, action, stopped.get());
        }
        Optional<Requirement<S, M>> started =
                problem.newRequirementForStartAction(action);
        if (started.isPresent()) {
            return postStart(state, action, started.get());
        }
        return Collections.emptySet();
    }

    private Set<CanonicalUpdateConfiguration<S, M>> postNormal(
            CanonicalUpdateConfiguration<S, M> state,
            String action) {
        List<List<TaggedState<S>>> localOutcomes =
                new ArrayList<List<TaggedState<S>>>();
        boolean participant = false;
        for (int index = 0; index < state.physicalState().size(); index++) {
            TaggedState<S> tagged = state.physicalState().component(index);
            VersionedComponent<S> component = problem.components().get(index);
            FiniteLts<S> active =
                    tagged.isOld() ? component.oldLts() : component.newLts();
            List<TaggedState<S>> choices = new ArrayList<TaggedState<S>>();
            if (component.environmentHasAction(tagged.version(), action)) {
                participant = true;
            }
            if (active.hasAction(action)) {
                Set<S> successors = active.successors(tagged.state(), action);
                if (successors.isEmpty()) {
                    return Collections.emptySet();
                }
                for (S successor : successors) {
                    choices.add(TaggedState.of(
                            tagged.version(), successor));
                }
            } else {
                choices.add(tagged);
            }
            localOutcomes.add(choices);
        }
        if (!participant) {
            return Collections.emptySet();
        }

        Map<String, M> testerStates =
                stepActiveTesters(state, action, null);
        List<PhysicalState<S>> physicalOutcomes =
                new ArrayList<PhysicalState<S>>();
        cartesianPhysical(
                localOutcomes,
                0,
                new ArrayList<TaggedState<S>>(),
                physicalOutcomes);
        LinkedHashSet<CanonicalUpdateConfiguration<S, M>> results =
                new LinkedHashSet<CanonicalUpdateConfiguration<S, M>>();
        for (PhysicalState<S> physical : physicalOutcomes) {
            results.add(CanonicalUpdateConfiguration.of(
                    physical, testerStates, state.pendingActions()));
        }
        return immutableResults(results);
    }

    private Set<CanonicalUpdateConfiguration<S, M>> postReconfigure(
            CanonicalUpdateConfiguration<S, M> state,
            String action,
            int componentIndex) {
        if (componentIndex < 0
                || componentIndex >= problem.components().size()) {
            return Collections.emptySet();
        }
        TaggedState<S> current =
                state.physicalState().component(componentIndex);
        if (!current.isOld()) {
            return Collections.emptySet();
        }
        VersionedComponent<S> component =
                problem.components().get(componentIndex);
        Set<S> targets = component.transferFrom(current.state());
        if (targets.isEmpty()) {
            return Collections.emptySet();
        }

        Map<String, M> testerStates =
                stepActiveTesters(state, action, null);
        Set<String> pending = without(state.pendingActions(), action);
        LinkedHashSet<CanonicalUpdateConfiguration<S, M>> results =
                new LinkedHashSet<CanonicalUpdateConfiguration<S, M>>();
        for (S target : targets) {
            PhysicalState<S> physical = state.physicalState().withComponent(
                    componentIndex, TaggedState.newState(target));
            results.add(CanonicalUpdateConfiguration.of(
                    physical, testerStates, pending));
        }
        return immutableResults(results);
    }

    private Set<CanonicalUpdateConfiguration<S, M>> postStop(
            CanonicalUpdateConfiguration<S, M> state,
            String action,
            Requirement<S, M> stopped) {
        if (!state.isTesterActive(stopped.id())) {
            return Collections.emptySet();
        }
        return singleton(CanonicalUpdateConfiguration.of(
                state.physicalState(),
                stepActiveTesters(state, action, stopped.id()),
                without(state.pendingActions(), action)));
    }

    private Set<CanonicalUpdateConfiguration<S, M>> postStart(
            CanonicalUpdateConfiguration<S, M> state,
            String action,
            Requirement<S, M> started) {
        ActivationSpec<S, M> activation =
                started.requiredActivationSpec();
        if (state.isTesterActive(started.id())
                || !activation.isDefinedAt(state.physicalState())) {
            return Collections.emptySet();
        }
        Map<String, M> testerStates =
                new LinkedHashMap<String, M>(
                        stepActiveTesters(state, action, null));
        testerStates.put(
                started.id(),
                activation.activate(state.physicalState()));
        return singleton(CanonicalUpdateConfiguration.of(
                state.physicalState(),
                testerStates,
                without(state.pendingActions(), action)));
    }

    private Map<String, M> stepActiveTesters(
            CanonicalUpdateConfiguration<S, M> state,
            String action,
            String excludedRequirementId) {
        Map<String, M> result = new LinkedHashMap<String, M>();
        for (Map.Entry<String, M> active
                : state.testerStatesByRequirementId().entrySet()) {
            if (active.getKey().equals(excludedRequirementId)) {
                continue;
            }
            Requirement<S, M> requirement =
                    problem.requirementsById().get(active.getKey());
            if (requirement == null) {
                throw new IllegalArgumentException(
                        "Unknown active requirement: " + active.getKey());
            }
            result.put(
                    active.getKey(),
                    requirement.tester().stepOrStutter(
                            active.getValue(), action));
        }
        return result;
    }

    private void cartesianPhysical(
            List<List<TaggedState<S>>> choices,
            int index,
            List<TaggedState<S>> current,
            List<PhysicalState<S>> output) {
        if (index == choices.size()) {
            output.add(PhysicalState.of(current));
            return;
        }
        for (TaggedState<S> choice : choices.get(index)) {
            current.add(choice);
            cartesianPhysical(choices, index + 1, current, output);
            current.remove(current.size() - 1);
        }
    }

    private void requireCanonical(
            CanonicalUpdateConfiguration<S, M> state) {
        if (state == null || !problem.isStructurallyValid(state)) {
            throw new IllegalArgumentException(
                    "Non-canonical update configuration: " + state);
        }
    }

    private Set<CanonicalUpdateConfiguration<S, M>> singleton(
            CanonicalUpdateConfiguration<S, M> state) {
        LinkedHashSet<CanonicalUpdateConfiguration<S, M>> values =
                new LinkedHashSet<CanonicalUpdateConfiguration<S, M>>();
        values.add(state);
        return immutableResults(values);
    }

    private Set<CanonicalUpdateConfiguration<S, M>> immutableResults(
            Collection<CanonicalUpdateConfiguration<S, M>> values) {
        return Collections.unmodifiableSet(
                new LinkedHashSet<CanonicalUpdateConfiguration<S, M>>(values));
    }

    private static Set<String> without(
            Set<String> source,
            String removed) {
        LinkedHashSet<String> result = new LinkedHashSet<String>(source);
        result.remove(removed);
        return Collections.unmodifiableSet(result);
    }
}
