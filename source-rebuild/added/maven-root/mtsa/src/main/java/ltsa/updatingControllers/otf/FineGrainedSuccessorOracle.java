package ltsa.updatingControllers.otf;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.OptionalInt;
import java.util.Set;

/**
 * Direct successor oracle for the revised fine-grained update semantics.
 *
 * <p>The oracle operates only on canonical {@code (x, mu, P)} tuples.  It
 * does not construct phase, activation, or precedence automata.  Every member
 * of a transition relation and every member of a component LTS successor set
 * is returned as an adversarial outcome of the same action.</p>
 */
public final class FineGrainedSuccessorOracle<S, M>
        implements ImplicitStrongGame<CanonicalUpdateConfiguration<S, M>, String,
        GoalSignature<S, M>> {

    static final String CONTROLLABLE_ACTION_ORDER_PROPERTY =
            "mtsa.otf.controllableActionOrder";

    enum ControllableActionOrder {
        UPDATE_FIRST("update_first"),
        ENDPOINT_GUIDED("endpoint_guided");

        private final String propertyValue;

        ControllableActionOrder(String propertyValue) {
            this.propertyValue = propertyValue;
        }

        String propertyValue() {
            return propertyValue;
        }

        static ControllableActionOrder configured() {
            return fromPropertyValue(
                    System.getProperty(CONTROLLABLE_ACTION_ORDER_PROPERTY));
        }

        static ControllableActionOrder fromPropertyValue(String configured) {
            String normalized = configured == null
                    ? ENDPOINT_GUIDED.propertyValue
                    : configured.trim();
            for (ControllableActionOrder order : values()) {
                if (order.propertyValue.equalsIgnoreCase(normalized)) {
                    return order;
                }
            }
            throw new IllegalArgumentException(
                    CONTROLLABLE_ACTION_ORDER_PROPERTY
                            + " must be update_first or endpoint_guided, but was "
                            + normalized);
        }
    }

    private static final Comparator<String> ACTION_NAME_ORDER = Comparator.naturalOrder();

    private final FineGrainedUpdateProblem<S, M> problem;
    private final ControllableActionOrder controllableActionOrder;
    private final Set<CanonicalUpdateConfiguration<S, M>> initialStates;
    private final Comparator<String> semanticActionOrder;
    private final Comparator<String> updateFirstActionOrder;
    private final Comparator<CanonicalUpdateConfiguration<S, M>> stateOrder;
    private final Map<CanonicalUpdateConfiguration<S, M>, Integer>
            goalProjectionMismatchCache =
            new HashMap<CanonicalUpdateConfiguration<S, M>, Integer>();

    public FineGrainedSuccessorOracle(FineGrainedUpdateProblem<S, M> problem) {
        this(problem, ControllableActionOrder.configured());
    }

    FineGrainedSuccessorOracle(
            FineGrainedUpdateProblem<S, M> problem,
            ControllableActionOrder controllableActionOrder) {
        this.problem = Objects.requireNonNull(problem, "problem");
        this.controllableActionOrder = Objects.requireNonNull(
                controllableActionOrder, "controllableActionOrder");
        this.initialStates = Collections.unmodifiableSet(
                new LinkedHashSet<CanonicalUpdateConfiguration<S, M>>(
                        problem.initialConfigurations()));
        this.semanticActionOrder = new Comparator<String>() {
            @Override
            public int compare(String left, String right) {
                int comparison = Integer.compare(
                        updateActionPriority(left), updateActionPriority(right));
                return comparison != 0
                        ? comparison
                        : ACTION_NAME_ORDER.compare(left, right);
            }
        };
        this.updateFirstActionOrder = new Comparator<String>() {
            @Override
            public int compare(String left, String right) {
                boolean leftUpdate = FineGrainedSuccessorOracle.this.isUpdateAction(left);
                boolean rightUpdate = FineGrainedSuccessorOracle.this.isUpdateAction(right);
                if (leftUpdate != rightUpdate) {
                    return leftUpdate ? -1 : 1;
                }
                return semanticActionOrder.compare(left, right);
            }
        };
        this.stateOrder = new Comparator<CanonicalUpdateConfiguration<S, M>>() {
            @Override
            public int compare(
                    CanonicalUpdateConfiguration<S, M> left,
                    CanonicalUpdateConfiguration<S, M> right) {
                int comparison = Integer.compare(
                        goalProjectionMismatch(left),
                        goalProjectionMismatch(right));
                if (comparison != 0) return comparison;
                comparison = Integer.compare(
                        left.pendingActions().size(),
                        right.pendingActions().size());
                return comparison != 0
                        ? comparison
                        : compareCanonical(left, right);
            }
        };

        if (initialStates.isEmpty()) {
            throw new IllegalArgumentException(
                    "Fine-grained update problem has no hotSwapIn embeddings");
        }
        for (CanonicalUpdateConfiguration<S, M> initial : initialStates) {
            if (!problem.isStructurallyValid(initial)) {
                throw new IllegalArgumentException(
                        "Non-canonical initial update configuration: " + initial);
            }
        }
    }

    @Override
    public Set<CanonicalUpdateConfiguration<S, M>> initialStates() {
        return initialStates;
    }

    @Override
    public boolean isSafe(CanonicalUpdateConfiguration<S, M> state) {
        if (!problem.isStructurallyValid(state)) {
            return false;
        }
        for (Map.Entry<String, M> active : state.testerStatesByRequirementId().entrySet()) {
            Requirement<S, M> requirement = problem.requirementsById().get(active.getKey());
            if (requirement == null || requirement.tester().isError(active.getValue())) {
                return false;
            }
        }
        return true;
    }

    @Override
    public boolean isGoal(CanonicalUpdateConfiguration<S, M> state) {
        return isSafe(state)
                && state.pendingActions().isEmpty()
                && problem.goalMatch(state).isPresent();
    }

    @Override
    public Collection<String> candidateActions(CanonicalUpdateConfiguration<S, M> state) {
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
        Collections.sort(ordered, updateFirstActionOrder);
        return Collections.unmodifiableList(ordered);
    }

    @Override
    public Set<CanonicalUpdateConfiguration<S, M>> post(
            CanonicalUpdateConfiguration<S, M> state,
            String action) {
        Objects.requireNonNull(action, "action");
        requireCanonical(state);
        if (problem.normalActions().contains(action)) {
            return postNormal(state, action);
        }
        if (!problem.updateActions().contains(action)
                || !state.pendingActions().contains(action)
                || !precedenceSatisfied(state, action)) {
            return Collections.emptySet();
        }

        OptionalInt componentIndex = problem.componentIndexForReconfigure(action);
        if (componentIndex.isPresent()) {
            return postReconfigure(state, action, componentIndex.getAsInt());
        }
        Optional<Requirement<S, M>> oldRequirement =
                problem.oldRequirementForStopAction(action);
        if (oldRequirement.isPresent()) {
            return postStop(state, action, oldRequirement.get());
        }
        Optional<Requirement<S, M>> newRequirement =
                problem.newRequirementForStartAction(action);
        if (newRequirement.isPresent()) {
            return postStart(state, action, newRequirement.get());
        }
        return Collections.emptySet();
    }

    @Override
    public boolean isControllable(String action) {
        return action != null && problem.isControllable(action);
    }

    @Override
    public boolean isUpdateAction(String action) {
        return action != null && problem.updateActions().contains(action);
    }

    @Override
    public Comparator<String> actionComparator() {
        return semanticActionOrder;
    }

    @Override
    public boolean preferUpdateActions(
            CanonicalUpdateConfiguration<S, M> state) {
        requireCanonical(state);
        return controllableActionOrder == ControllableActionOrder.UPDATE_FIRST
                || goalProjectionMismatch(state) == 0;
    }

    /**
     * Conservative witness order for fine-grained updates.  It first retires
     * old obligations and transfers components, then uses normal controller
     * actions to align the transferred state with an exact new endpoint, and
     * only then activates the new obligations. This ordering is shared by the
     * guided witness search and lazy complete attractor. It never removes a
     * candidate; a losing result still requires exhaustive deferred expansion.
     */
    @Override
    public int explorationActionPriority(
            CanonicalUpdateConfiguration<S, M> state,
            String action) {
        requireCanonical(state);
        if (controllableActionOrder == ControllableActionOrder.UPDATE_FIRST) {
            return isUpdateAction(action) ? 0 : 1;
        }
        boolean pendingStop = false;
        boolean pendingReconfigure = false;
        for (String pending : state.pendingActions()) {
            Optional<UpdateEventKind> kind = problem.updateEventKind(pending);
            if (!kind.isPresent()) {
                continue;
            }
            if (kind.get() == UpdateEventKind.STOP_OLD_REQUIREMENT) {
                pendingStop = true;
            } else if (kind.get() == UpdateEventKind.RECONFIGURE) {
                pendingReconfigure = true;
            }
        }

        Optional<UpdateEventKind> kind = problem.updateEventKind(action);
        if (pendingStop) {
            if (kind.isPresent()
                    && kind.get() == UpdateEventKind.STOP_OLD_REQUIREMENT) {
                return 0;
            }
            if (kind.isPresent()
                    && kind.get() == UpdateEventKind.RECONFIGURE) {
                return 1;
            }
            return kind.isPresent() ? 3 : 2;
        }
        if (pendingReconfigure) {
            if (kind.isPresent()
                    && kind.get() == UpdateEventKind.RECONFIGURE) {
                return 0;
            }
            return kind.isPresent() ? 2 : 1;
        }

        boolean endpointAligned = goalProjectionMismatch(state) == 0;
        if (kind.isPresent()
                && kind.get() == UpdateEventKind.START_NEW_REQUIREMENT) {
            return endpointAligned ? 0 : 1;
        }
        return endpointAligned ? 1 : 0;
    }

    /*
     * Stable order within one exploration-priority class and for certificate
     * tie-breaking. The state-dependent stage priority is evaluated before
     * this order by both guided and complete exploration.
     */
    private int updateActionPriority(String action) {
        Optional<UpdateEventKind> kind = problem.updateEventKind(action);
        if (!kind.isPresent()) {
            return 3;
        }
        switch (kind.get()) {
            case START_NEW_REQUIREMENT:
                return 0;
            case RECONFIGURE:
                return 1;
            case STOP_OLD_REQUIREMENT:
                return 2;
            default:
                return 3;
        }
    }

    /*
     * Exact endpoint-projection distance used only as an exploration hint.
     * An old local state counts as matching when its direct transfer relation
     * contains the endpoint local state; an inactive new tester counts as
     * matching when its checked activation map yields the endpoint state.
     */
    private int goalProjectionMismatch(
            CanonicalUpdateConfiguration<S, M> state) {
        Integer cached = goalProjectionMismatchCache.get(state);
        if (cached != null) {
            return cached.intValue();
        }
        int mismatch = computeGoalProjectionMismatch(state);
        goalProjectionMismatchCache.put(state, Integer.valueOf(mismatch));
        return mismatch;
    }

    private int computeGoalProjectionMismatch(
            CanonicalUpdateConfiguration<S, M> state) {
        int best = Integer.MAX_VALUE;
        for (GoalSignature<S, M> goal : problem.goalSignatures()) {
            int mismatch = 0;
            for (int index = 0; index < state.physicalState().size(); index++) {
                TaggedState<S> current = state.physicalState().component(index);
                TaggedState<S> target = goal.physicalState().component(index);
                if (current.isOld()) {
                    if (!problem.components().get(index)
                            .transferFrom(current.state())
                            .contains(target.state())) {
                        mismatch++;
                    }
                } else if (!current.state().equals(target.state())) {
                    mismatch++;
                }
            }
            for (Map.Entry<String, M> expected
                    : goal.newRequirementStates().entrySet()) {
                M current = state.testerStatesByRequirementId()
                        .get(expected.getKey());
                if (current != null) {
                    if (!current.equals(expected.getValue())) mismatch++;
                    continue;
                }
                Requirement<S, M> requirement =
                        problem.requirementsById().get(expected.getKey());
                if (requirement == null
                        || requirement.role() != RequirementRole.NEW) {
                    mismatch++;
                    continue;
                }
                ActivationSpec<S, M> activation =
                        requirement.requiredActivationSpec();
                if (!activation.isDefinedAt(state.physicalState())
                        || !activation.activate(state.physicalState())
                        .equals(expected.getValue())) {
                    mismatch++;
                }
            }
            best = Math.min(best, mismatch);
            if (best == 0) return 0;
        }
        return best == Integer.MAX_VALUE ? 1 : best;
    }

    /** Comparator including the paper's update-before-normal priority. */
    public Comparator<String> updateFirstActionComparator() {
        return updateFirstActionOrder;
    }

    @Override
    public Comparator<CanonicalUpdateConfiguration<S, M>> stateComparator() {
        return stateOrder;
    }

    @Override
    public GoalSignature<S, M> goalMatch(CanonicalUpdateConfiguration<S, M> goalState) {
        if (!isGoal(goalState)) {
            throw new IllegalArgumentException("Configuration is not a Goal: " + goalState);
        }
        return problem.goalMatch(goalState).get();
    }

    @Override
    public boolean isStructurallyValid(CanonicalUpdateConfiguration<S, M> state) {
        return state != null && problem.isStructurallyValid(state);
    }

    private Set<CanonicalUpdateConfiguration<S, M>> postNormal(
            CanonicalUpdateConfiguration<S, M> state,
            String action) {
        List<List<TaggedState<S>>> localOutcomes = new ArrayList<List<TaggedState<S>>>();
        boolean participant = false;
        for (int index = 0; index < state.physicalState().size(); index++) {
            TaggedState<S> tagged = state.physicalState().component(index);
            VersionedComponent<S> component = problem.components().get(index);
            FiniteLts<S> active = tagged.isOld() ? component.oldLts() : component.newLts();
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
                    choices.add(TaggedState.of(tagged.version(), successor));
                }
            } else {
                choices.add(tagged);
            }
            localOutcomes.add(choices);
        }
        if (!participant) {
            return Collections.emptySet();
        }

        Map<String, M> testerStates = stepActiveTesters(state, action, null);
        List<PhysicalState<S>> physicalOutcomes = new ArrayList<PhysicalState<S>>();
        cartesianPhysical(localOutcomes, 0, new ArrayList<TaggedState<S>>(), physicalOutcomes);
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
        if (componentIndex < 0 || componentIndex >= problem.components().size()) {
            return Collections.emptySet();
        }
        TaggedState<S> current = state.physicalState().component(componentIndex);
        if (!current.isOld()) {
            return Collections.emptySet();
        }
        VersionedComponent<S> component = problem.components().get(componentIndex);
        Set<S> transferTargets = component.transferFrom(current.state());
        if (transferTargets.isEmpty()) {
            return Collections.emptySet();
        }

        Map<String, M> testerStates = stepActiveTesters(state, action, null);
        Set<String> pending = without(state.pendingActions(), action);
        LinkedHashSet<CanonicalUpdateConfiguration<S, M>> results =
                new LinkedHashSet<CanonicalUpdateConfiguration<S, M>>();
        for (S target : transferTargets) {
            PhysicalState<S> physical = state.physicalState().withComponent(
                    componentIndex, TaggedState.newState(target));
            results.add(CanonicalUpdateConfiguration.of(physical, testerStates, pending));
        }
        return immutableResults(results);
    }

    private Set<CanonicalUpdateConfiguration<S, M>> postStop(
            CanonicalUpdateConfiguration<S, M> state,
            String action,
            Requirement<S, M> stopped) {
        if (!state.testerStatesByRequirementId().containsKey(stopped.id())) {
            return Collections.emptySet();
        }
        Map<String, M> testerStates = stepActiveTesters(state, action, stopped.id());
        return singleton(CanonicalUpdateConfiguration.of(
                state.physicalState(), testerStates, without(state.pendingActions(), action)));
    }

    private Set<CanonicalUpdateConfiguration<S, M>> postStart(
            CanonicalUpdateConfiguration<S, M> state,
            String action,
            Requirement<S, M> started) {
        ActivationSpec<S, M> activation = started.requiredActivationSpec();
        if (state.testerStatesByRequirementId().containsKey(started.id())
                || !activation.isDefinedAt(state.physicalState())) {
            return Collections.emptySet();
        }

        // Existing testers observe b_r first.  The target tester is activated
        // afterwards and therefore does not observe its own start boundary.
        Map<String, M> testerStates = new LinkedHashMap<String, M>(
                stepActiveTesters(state, action, null));
        testerStates.put(started.id(), activation.activate(state.physicalState()));
        return singleton(CanonicalUpdateConfiguration.of(
                state.physicalState(), testerStates, without(state.pendingActions(), action)));
    }

    private Map<String, M> stepActiveTesters(
            CanonicalUpdateConfiguration<S, M> state,
            String action,
            String excludedRequirementId) {
        Map<String, M> result = new LinkedHashMap<String, M>();
        for (Map.Entry<String, M> active : state.testerStatesByRequirementId().entrySet()) {
            if (active.getKey().equals(excludedRequirementId)) {
                continue;
            }
            Requirement<S, M> requirement = problem.requirementsById().get(active.getKey());
            if (requirement == null) {
                throw new IllegalArgumentException(
                        "Unknown active requirement: " + active.getKey());
            }
            SafetyTester<M> tester = requirement.tester();
            M next = tester.alphabet().contains(action)
                    ? tester.step(active.getValue(), action)
                    : active.getValue();
            result.put(active.getKey(), next);
        }
        return result;
    }

    private boolean precedenceSatisfied(
            CanonicalUpdateConfiguration<S, M> state,
            String action) {
        for (String predecessor : problem.predecessors(action)) {
            if (state.pendingActions().contains(predecessor)) {
                return false;
            }
        }
        return true;
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

    private int compareCanonical(
            CanonicalUpdateConfiguration<S, M> left,
            CanonicalUpdateConfiguration<S, M> right) {
        if (left == right || left.equals(right)) {
            return 0;
        }
        int comparison = Integer.compare(
                left.physicalState().size(), right.physicalState().size());
        if (comparison != 0) return comparison;
        for (int index = 0; index < left.physicalState().size(); index++) {
            TaggedState<S> leftState = left.physicalState().component(index);
            TaggedState<S> rightState = right.physicalState().component(index);
            comparison = leftState.version().compareTo(rightState.version());
            if (comparison != 0) return comparison;
            comparison = problem.compareComponentStates(
                    index, leftState.version(), leftState.state(), rightState.state());
            if (comparison != 0) return comparison;
        }

        comparison = compareStringCollections(
                left.testerStatesByRequirementId().keySet(),
                right.testerStatesByRequirementId().keySet());
        if (comparison != 0) return comparison;
        List<String> ids = new ArrayList<String>(left.testerStatesByRequirementId().keySet());
        Collections.sort(ids);
        for (String id : ids) {
            comparison = problem.compareTesterStates(
                    id,
                    left.testerStatesByRequirementId().get(id),
                    right.testerStatesByRequirementId().get(id));
            if (comparison != 0) return comparison;
        }
        return compareStringCollections(left.pendingActions(), right.pendingActions());
    }

    private static int compareStringCollections(
            Collection<String> left,
            Collection<String> right) {
        List<String> leftValues = new ArrayList<String>(left);
        List<String> rightValues = new ArrayList<String>(right);
        Collections.sort(leftValues);
        Collections.sort(rightValues);
        int bound = Math.min(leftValues.size(), rightValues.size());
        for (int index = 0; index < bound; index++) {
            int comparison = leftValues.get(index).compareTo(rightValues.get(index));
            if (comparison != 0) return comparison;
        }
        return Integer.compare(leftValues.size(), rightValues.size());
    }

    private void requireCanonical(CanonicalUpdateConfiguration<S, M> state) {
        if (state == null || !problem.isStructurallyValid(state)) {
            throw new IllegalArgumentException("Non-canonical update configuration: " + state);
        }
    }

    private static Set<String> without(Set<String> source, String removed) {
        LinkedHashSet<String> copy = new LinkedHashSet<String>(source);
        copy.remove(removed);
        return Collections.unmodifiableSet(copy);
    }

    private Set<CanonicalUpdateConfiguration<S, M>> singleton(
            CanonicalUpdateConfiguration<S, M> state) {
        LinkedHashSet<CanonicalUpdateConfiguration<S, M>> values =
                new LinkedHashSet<CanonicalUpdateConfiguration<S, M>>();
        values.add(state);
        return immutableResults(values);
    }

    private Set<CanonicalUpdateConfiguration<S, M>> immutableResults(
            Set<CanonicalUpdateConfiguration<S, M>> results) {
        return Collections.unmodifiableSet(
                new LinkedHashSet<CanonicalUpdateConfiguration<S, M>>(results));
    }

}
