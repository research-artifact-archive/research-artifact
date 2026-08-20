package ltsa.updatingControllers.otf;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.OptionalInt;
import java.util.Set;
import java.util.function.Function;
import java.util.function.Predicate;

/**
 * Fully validated immutable input to the fine-grained OTF-DUCS game.
 *
 * <p>Construction is intentionally strict. Ill-formed testers, activation
 * obligations, event collisions, and precedence cycles are rejected before
 * exploration starts.  The reachable-endpoint builder methods additionally
 * guarantee complete old/new endpoint projection; manual endpoint methods are
 * explicitly a trusted low-level input path.</p>
 */
public final class FineGrainedUpdateProblem<S, M> {

    public static final String DEFAULT_HOT_SWAP_IN = "hotSwapIn";
    public static final String DEFAULT_HOT_SWAP_OUT = "hotSwapOut";

    private final List<VersionedComponent<S>> components;
    private final List<Map<S, Integer>> oldComponentStateOrder;
    private final List<Map<S, Integer>> newComponentStateOrder;
    private final Map<String, Requirement<S, M>> requirementsById;
    private final Map<String, Map<M, Integer>> testerStateOrder;
    private final Set<String> oldRequirementIds;
    private final Set<String> newRequirementIds;
    private final Set<String> updateRequirementIds;
    private final Set<String> normalActions;
    private final Set<String> controllableNormalActions;
    private final Set<String> controllableActions;
    private final Set<String> commonAlphabet;
    private final Set<String> updateActions;
    private final String hotSwapInAction;
    private final String hotSwapOutAction;
    private final Map<String, Integer> componentIndexByReconfigureAction;
    private final Map<String, String> requirementIdByUpdateAction;
    private final Map<String, UpdateEventKind> updateEventKinds;
    private final Map<String, Set<String>> directPredecessors;
    private final Map<String, Set<String>> transitivePredecessors;
    private final List<CanonicalUpdateConfiguration<S, M>> initialConfigurations;
    private final List<GoalSignature<S, M>> goalSignatures;
    private final boolean oldEndpointExhaustivelyEnumerated;
    private final boolean newEndpointExhaustivelyEnumerated;

    private FineGrainedUpdateProblem(Builder<S, M> builder) {
        this.components = immutableList(builder.components, "components");
        if (components.isEmpty()) {
            throw new IllegalArgumentException("At least one versioned component is required");
        }
        this.oldComponentStateOrder = indexComponentStates(components, true);
        this.newComponentStateOrder = indexComponentStates(components, false);

        this.requirementsById = indexRequirements(builder.requirements);
        this.testerStateOrder = indexTesterStates(requirementsById);
        this.oldRequirementIds = roleIds(RequirementRole.OLD);
        this.newRequirementIds = roleIds(RequirementRole.NEW);
        this.updateRequirementIds = roleIds(RequirementRole.UPDATE_TIME);

        this.hotSwapInAction = nonBlank(builder.hotSwapInAction, "hotSwapIn action");
        this.hotSwapOutAction = nonBlank(builder.hotSwapOutAction, "hotSwapOut action");
        if (hotSwapInAction.equals(hotSwapOutAction)) {
            throw new IllegalArgumentException("hotSwapIn and hotSwapOut must be distinct");
        }

        LinkedHashSet<String> inferredNormal = new LinkedHashSet<>();
        for (VersionedComponent<S> component : components) {
            inferredNormal.addAll(component.oldLts().alphabet());
            inferredNormal.addAll(component.newLts().alphabet());
        }
        LinkedHashSet<String> configuredNormal = builder.normalActionsExplicit
                ? checkedActions(builder.normalActions, "normal action")
                : inferredNormal;
        if (!configuredNormal.containsAll(inferredNormal)) {
            LinkedHashSet<String> missing = new LinkedHashSet<>(inferredNormal);
            missing.removeAll(configuredNormal);
            throw new IllegalArgumentException("Component actions missing from normalActions: " + missing);
        }
        this.normalActions = Collections.unmodifiableSet(configuredNormal);

        LinkedHashSet<String> configuredControllable = checkedActions(
                builder.controllableNormalActions, "controllable normal action");
        if (!normalActions.containsAll(configuredControllable)) {
            LinkedHashSet<String> invalid = new LinkedHashSet<>(configuredControllable);
            invalid.removeAll(normalActions);
            throw new IllegalArgumentException("Controllable normal actions outside normalActions: " + invalid);
        }
        this.controllableNormalActions = Collections.unmodifiableSet(configuredControllable);

        Map<String, Integer> componentActions = new LinkedHashMap<>();
        Map<String, String> requirementActions = new LinkedHashMap<>();
        Map<String, UpdateEventKind> kinds = new LinkedHashMap<>();
        LinkedHashSet<String> allUpdateActions = new LinkedHashSet<>();
        Set<String> componentIds = new LinkedHashSet<>();
        for (int index = 0; index < components.size(); index++) {
            VersionedComponent<S> component = components.get(index);
            if (!componentIds.add(component.id())) {
                throw new IllegalArgumentException("Duplicate component id: " + component.id());
            }
            registerUpdateAction(
                    component.reconfigureAction(),
                    UpdateEventKind.RECONFIGURE,
                    allUpdateActions,
                    kinds);
            componentActions.put(component.reconfigureAction(), index);
        }
        for (Requirement<S, M> requirement : requirementsById.values()) {
            if (requirement.role() == RequirementRole.OLD) {
                String action = requirement.stopAction().get();
                registerUpdateAction(action, UpdateEventKind.STOP_OLD_REQUIREMENT, allUpdateActions, kinds);
                requirementActions.put(action, requirement.id());
            } else if (requirement.role() == RequirementRole.NEW) {
                String action = requirement.startAction().get();
                registerUpdateAction(action, UpdateEventKind.START_NEW_REQUIREMENT, allUpdateActions, kinds);
                requirementActions.put(action, requirement.id());
            }
        }
        this.updateActions = Collections.unmodifiableSet(allUpdateActions);
        this.componentIndexByReconfigureAction = Collections.unmodifiableMap(componentActions);
        this.requirementIdByUpdateAction = Collections.unmodifiableMap(requirementActions);
        this.updateEventKinds = Collections.unmodifiableMap(kinds);

        validateActionNamespaces();

        LinkedHashSet<String> expectedCommonAlphabet = new LinkedHashSet<>(normalActions);
        expectedCommonAlphabet.addAll(updateActions);
        LinkedHashSet<String> configuredCommon = builder.commonAlphabetExplicit
                ? checkedActions(builder.commonAlphabet, "common alphabet action")
                : expectedCommonAlphabet;
        if (!configuredCommon.equals(expectedCommonAlphabet)) {
            throw new IllegalArgumentException(
                    "commonAlphabet must equal normalActions union updateActions; expected="
                            + expectedCommonAlphabet + ", actual=" + configuredCommon);
        }
        this.commonAlphabet = Collections.unmodifiableSet(configuredCommon);

        LinkedHashSet<String> allControllable = new LinkedHashSet<>(controllableNormalActions);
        allControllable.addAll(updateActions);
        this.controllableActions = Collections.unmodifiableSet(allControllable);

        validateComponentAlphabets();
        validateRequirementsAndActivations();

        Map<String, Set<String>> direct = buildDirectPredecessors(builder.precedenceEdges);
        assertAcyclic(direct);
        this.directPredecessors = immutableSetMap(direct);
        this.transitivePredecessors = immutableSetMap(computeTransitivePredecessors(direct));

        List<InitialSnapshot<S, M>> snapshots = immutableList(builder.initialSnapshots, "initialSnapshots");
        this.initialConfigurations = buildInitialConfigurations(snapshots);
        this.goalSignatures = validateGoalSignatures(builder.goalSignatures);
        this.oldEndpointExhaustivelyEnumerated = builder.initialSnapshotsEnumerated;
        this.newEndpointExhaustivelyEnumerated = builder.goalSignaturesEnumerated;
    }

    public static <S, M> Builder<S, M> builder() {
        return new Builder<>();
    }

    public List<VersionedComponent<S>> components() {
        return components;
    }

    public Map<String, Requirement<S, M>> requirementsById() {
        return requirementsById;
    }

    public Collection<Requirement<S, M>> requirements() {
        return requirementsById.values();
    }

    public Optional<Requirement<S, M>> requirement(String id) {
        return Optional.ofNullable(requirementsById.get(id));
    }

    public Set<String> oldRequirementIds() {
        return oldRequirementIds;
    }

    public Set<String> newRequirementIds() {
        return newRequirementIds;
    }

    public Set<String> updateRequirementIds() {
        return updateRequirementIds;
    }

    public Set<String> updateActions() {
        return updateActions;
    }

    public Set<String> normalActions() {
        return normalActions;
    }

    public Set<String> controllableNormalActions() {
        return controllableNormalActions;
    }

    /** Normal controllable actions plus every (necessarily controllable) update event. */
    public Set<String> controllableActions() {
        return controllableActions;
    }

    public boolean isControllable(String action) {
        return controllableActions.contains(action);
    }

    public Set<String> commonAlphabet() {
        return commonAlphabet;
    }

    public String hotSwapInAction() {
        return hotSwapInAction;
    }

    public String hotSwapOutAction() {
        return hotSwapOutAction;
    }

    /** All strict (transitive) predecessors of an update event. */
    public Set<String> predecessors(String updateAction) {
        Set<String> result = transitivePredecessors.get(updateAction);
        if (result == null) {
            throw new IllegalArgumentException("Unknown update action: " + updateAction);
        }
        return result;
    }

    public Set<String> directPredecessors(String updateAction) {
        Set<String> result = directPredecessors.get(updateAction);
        if (result == null) {
            throw new IllegalArgumentException("Unknown update action: " + updateAction);
        }
        return result;
    }

    public boolean isUpdateActionEligible(CanonicalUpdateConfiguration<S, M> configuration, String action) {
        Objects.requireNonNull(configuration, "configuration");
        return configuration.pendingActions().contains(action)
                && Collections.disjoint(predecessors(action), configuration.pendingActions());
    }

    public OptionalInt componentIndexForReconfigure(String action) {
        Integer result = componentIndexByReconfigureAction.get(action);
        return result == null ? OptionalInt.empty() : OptionalInt.of(result);
    }

    public Optional<VersionedComponent<S>> componentForReconfigureAction(String action) {
        OptionalInt index = componentIndexForReconfigure(action);
        return index.isPresent() ? Optional.of(components.get(index.getAsInt())) : Optional.empty();
    }

    public Optional<Requirement<S, M>> requirementForUpdateAction(String action) {
        String id = requirementIdByUpdateAction.get(action);
        return id == null ? Optional.empty() : Optional.of(requirementsById.get(id));
    }

    public Optional<Requirement<S, M>> oldRequirementForStopAction(String action) {
        Optional<Requirement<S, M>> result = requirementForUpdateAction(action);
        return result.isPresent() && result.get().role() == RequirementRole.OLD
                ? result : Optional.empty();
    }

    public Optional<Requirement<S, M>> newRequirementForStartAction(String action) {
        Optional<Requirement<S, M>> result = requirementForUpdateAction(action);
        return result.isPresent() && result.get().role() == RequirementRole.NEW
                ? result : Optional.empty();
    }

    public Optional<UpdateEventKind> updateEventKind(String action) {
        return Optional.ofNullable(updateEventKinds.get(action));
    }

    public List<CanonicalUpdateConfiguration<S, M>> initialConfigurations() {
        return initialConfigurations;
    }

    public List<GoalSignature<S, M>> goalSignatures() {
        return goalSignatures;
    }

    /**
     * True only when both endpoint state sets came from complete reachable-LTS
     * enumeration. This records state coverage; the full Link checker validates
     * that the supplied projections also preserve endpoint transitions.
     */
    public boolean hasExhaustiveEndpointCoverage() {
        return oldEndpointExhaustivelyEnumerated && newEndpointExhaustivelyEnumerated;
    }

    public Optional<GoalSignature<S, M>> goalMatch(CanonicalUpdateConfiguration<S, M> configuration) {
        if (!isStructurallyValid(configuration)
                || !configuration.pendingActions().isEmpty()
                || !configuration.physicalState().allNew()
                || !isSafe(configuration)) {
            return Optional.empty();
        }
        for (GoalSignature<S, M> signature : goalSignatures) {
            if (signature.matches(configuration)) {
                return Optional.of(signature);
            }
        }
        return Optional.empty();
    }

    public boolean isGoal(CanonicalUpdateConfiguration<S, M> configuration) {
        return goalMatch(configuration).isPresent();
    }

    public boolean isSafe(CanonicalUpdateConfiguration<S, M> configuration) {
        for (Map.Entry<String, M> active : configuration.activeTesterStates().entrySet()) {
            Requirement<S, M> requirement = requirementsById.get(active.getKey());
            if (requirement == null
                    || !requirement.tester().states().contains(active.getValue())
                    || requirement.tester().isError(active.getValue())) {
                return false;
            }
        }
        return true;
    }

    /** Checks exactly the canonical tuple invariants, not reachability or safety. */
    public boolean isStructurallyValid(CanonicalUpdateConfiguration<S, M> configuration) {
        if (configuration == null
                || !isPhysicalStateValid(configuration.physicalState())
                || !updateActions.containsAll(configuration.pendingActions())) {
            return false;
        }
        for (int index = 0; index < components.size(); index++) {
            boolean old = configuration.physicalState().component(index).isOld();
            boolean reconfigurePending = configuration.pendingActions()
                    .contains(components.get(index).reconfigureAction());
            if (old != reconfigurePending) {
                return false;
            }
        }
        if (!requirementsById.keySet().containsAll(configuration.activeTesterStates().keySet())) {
            return false;
        }
        for (Requirement<S, M> requirement : requirementsById.values()) {
            boolean active = configuration.isTesterActive(requirement.id());
            boolean shouldBeActive;
            if (requirement.role() == RequirementRole.OLD) {
                shouldBeActive = configuration.pendingActions().contains(requirement.stopAction().get());
            } else if (requirement.role() == RequirementRole.NEW) {
                shouldBeActive = !configuration.pendingActions().contains(requirement.startAction().get());
            } else {
                shouldBeActive = true;
            }
            if (active != shouldBeActive) {
                return false;
            }
            if (active && !requirement.tester().states()
                    .contains(configuration.activeTesterStates().get(requirement.id()))) {
                return false;
            }
        }
        return true;
    }

    public boolean isPhysicalStateValid(PhysicalState<S> physicalState) {
        if (physicalState == null || physicalState.size() != components.size()) {
            return false;
        }
        for (int index = 0; index < components.size(); index++) {
            TaggedState<S> local = physicalState.component(index);
            VersionedComponent<S> component = components.get(index);
            if (local.isOld()) {
                if (!component.oldLts().states().contains(local.state())) return false;
            } else if (!component.newLts().states().contains(local.state())) {
                return false;
            }
        }
        return true;
    }

    /** Package-local fixed total order induced by each finite component declaration. */
    int compareComponentStates(
            int componentIndex, ComponentVersion version, S left, S right) {
        if (Objects.equals(left, right)) return 0;
        Map<S, Integer> order = version == ComponentVersion.OLD
                ? oldComponentStateOrder.get(componentIndex)
                : newComponentStateOrder.get(componentIndex);
        Integer leftIndex = order.get(left);
        Integer rightIndex = order.get(right);
        if (leftIndex == null || rightIndex == null) {
            throw new IllegalArgumentException("Component state is outside the declared finite LTS");
        }
        return Integer.compare(leftIndex.intValue(), rightIndex.intValue());
    }

    /** Package-local fixed total order induced by each tester declaration. */
    int compareTesterStates(String requirementId, M left, M right) {
        if (Objects.equals(left, right)) return 0;
        Map<M, Integer> order = testerStateOrder.get(requirementId);
        if (order == null || !order.containsKey(left) || !order.containsKey(right)) {
            throw new IllegalArgumentException(
                    "Tester state is outside requirement " + requirementId);
        }
        return Integer.compare(order.get(left).intValue(), order.get(right).intValue());
    }

    private Map<String, Requirement<S, M>> indexRequirements(List<Requirement<S, M>> requirements) {
        LinkedHashMap<String, Requirement<S, M>> result = new LinkedHashMap<>();
        for (Requirement<S, M> requirement : requirements) {
            requirement = Objects.requireNonNull(requirement, "requirement");
            if (result.putIfAbsent(requirement.id(), requirement) != null) {
                throw new IllegalArgumentException("Duplicate requirement id: " + requirement.id());
            }
        }
        return Collections.unmodifiableMap(result);
    }

    private Set<String> roleIds(RequirementRole role) {
        LinkedHashSet<String> result = new LinkedHashSet<>();
        for (Requirement<S, M> requirement : requirementsById.values()) {
            if (requirement.role() == role) result.add(requirement.id());
        }
        return Collections.unmodifiableSet(result);
    }

    private void validateActionNamespaces() {
        if (normalActions.contains(hotSwapInAction) || normalActions.contains(hotSwapOutAction)) {
            throw new IllegalArgumentException("hotSwap boundary actions must not be normal actions");
        }
        if (updateActions.contains(hotSwapInAction) || updateActions.contains(hotSwapOutAction)) {
            throw new IllegalArgumentException("Update actions must not collide with hotSwap boundaries");
        }
        LinkedHashSet<String> collisions = new LinkedHashSet<>(updateActions);
        collisions.retainAll(normalActions);
        if (!collisions.isEmpty()) {
            throw new IllegalArgumentException("Update actions collide with normal actions: " + collisions);
        }
    }

    private void validateComponentAlphabets() {
        for (VersionedComponent<S> component : components) {
            if (!normalActions.containsAll(component.oldLts().alphabet())
                    || !normalActions.containsAll(component.newLts().alphabet())) {
                throw new IllegalArgumentException("Component alphabet is outside normalActions: " + component.id());
            }
            if (component.oldLts().alphabet().contains(hotSwapInAction)
                    || component.oldLts().alphabet().contains(hotSwapOutAction)
                    || component.newLts().alphabet().contains(hotSwapInAction)
                    || component.newLts().alphabet().contains(hotSwapOutAction)) {
                throw new IllegalArgumentException("Component alphabets must exclude hotSwap boundaries: "
                        + component.id());
            }
        }
    }

    private void validateRequirementsAndActivations() {
        for (Requirement<S, M> requirement : requirementsById.values()) {
            if (!commonAlphabet.containsAll(requirement.tester().alphabet())) {
                throw new IllegalArgumentException(
                        "Tester alphabet must be a subset of commonAlphabet for requirement "
                                + requirement.id());
            }
            if (requirement.role() != RequirementRole.OLD) {
                ActivationSpec<S, M> activation = requirement.requiredActivationSpec();
                if (!activation.residualLanguage().alphabet().equals(commonAlphabet)) {
                    throw new IllegalArgumentException(
                            "Residual automaton alphabet must equal commonAlphabet for requirement "
                                    + requirement.id());
                }
                for (PhysicalState<S> physicalState : activation.domain()) {
                    if (!isPhysicalStateValid(physicalState)) {
                        throw new IllegalArgumentException(
                                "Activation guard contains an invalid physical state for " + requirement.id()
                                        + ": " + physicalState);
                    }
                }
                try {
                    activation.validateLanguageEquivalence(requirement.tester());
                } catch (IllegalArgumentException error) {
                    throw new IllegalArgumentException(
                            "Invalid activation specification for requirement " + requirement.id()
                                    + ": " + error.getMessage(), error);
                }
            }
        }
    }

    private Map<String, Set<String>> buildDirectPredecessors(List<PrecedenceEdge> edges) {
        Map<String, Set<String>> result = new LinkedHashMap<>();
        for (String action : updateActions) {
            result.put(action, new LinkedHashSet<>());
        }
        for (PrecedenceEdge edge : edges) {
            if (!updateActions.contains(edge.before) || !updateActions.contains(edge.after)) {
                throw new IllegalArgumentException("Precedence mentions a non-update action: " + edge);
            }
            if (edge.before.equals(edge.after)) {
                throw new IllegalArgumentException("Strict precedence cannot contain a self edge: " + edge.before);
            }
            result.get(edge.after).add(edge.before);
        }
        return result;
    }

    private void assertAcyclic(Map<String, Set<String>> predecessors) {
        Map<String, Integer> color = new LinkedHashMap<>();
        for (String action : updateActions) color.put(action, 0);
        for (String action : updateActions) {
            visitPrecedence(action, predecessors, color);
        }
    }

    private void visitPrecedence(
            String action, Map<String, Set<String>> predecessors, Map<String, Integer> color) {
        int current = color.get(action);
        if (current == 1) {
            throw new IllegalArgumentException("Precedence relation contains a cycle through " + action);
        }
        if (current == 2) return;
        color.put(action, 1);
        for (String predecessor : predecessors.get(action)) {
            visitPrecedence(predecessor, predecessors, color);
        }
        color.put(action, 2);
    }

    private Map<String, Set<String>> computeTransitivePredecessors(Map<String, Set<String>> direct) {
        Map<String, Set<String>> result = new LinkedHashMap<>();
        for (String action : updateActions) {
            LinkedHashSet<String> closure = new LinkedHashSet<>();
            collectPredecessors(action, direct, closure);
            result.put(action, closure);
        }
        return result;
    }

    private void collectPredecessors(
            String action, Map<String, Set<String>> direct, Set<String> result) {
        for (String predecessor : direct.get(action)) {
            if (result.add(predecessor)) {
                collectPredecessors(predecessor, direct, result);
            }
        }
    }

    private List<CanonicalUpdateConfiguration<S, M>> buildInitialConfigurations(
            List<InitialSnapshot<S, M>> snapshots) {
        if (snapshots.isEmpty()) {
            throw new IllegalArgumentException("At least one reachable old endpoint snapshot is required");
        }
        LinkedHashSet<CanonicalUpdateConfiguration<S, M>> configurations = new LinkedHashSet<>();
        for (InitialSnapshot<S, M> snapshot : snapshots) {
            if (!snapshot.physicalState().allOld() || !isPhysicalStateValid(snapshot.physicalState())) {
                throw new IllegalArgumentException("Initial snapshot must contain valid OLD component states: "
                        + snapshot.physicalState());
            }
            if (!snapshot.oldRequirementStates().keySet().equals(oldRequirementIds)) {
                throw new IllegalArgumentException(
                        "Initial snapshot must provide exactly every OLD tester state; expected="
                                + oldRequirementIds + ", actual=" + snapshot.oldRequirementStates().keySet());
            }

            Map<String, M> active = new LinkedHashMap<>();
            for (String id : oldRequirementIds) {
                M state = snapshot.oldRequirementStates().get(id);
                SafetyTester<M> tester = requirementsById.get(id).tester();
                if (!tester.states().contains(state) || tester.isError(state)) {
                    throw new IllegalArgumentException("Invalid/unsafe OLD tester state in initial snapshot: " + id);
                }
                active.put(id, state);
            }
            for (String id : updateRequirementIds) {
                Requirement<S, M> requirement = requirementsById.get(id);
                ActivationSpec<S, M> activation = requirement.requiredActivationSpec();
                if (!activation.isDefinedAt(snapshot.physicalState())) {
                    throw new IllegalArgumentException(
                            "UPDATE_TIME activation guard does not cover initial physical state for " + id
                                    + ": " + snapshot.physicalState());
                }
                M state = activation.activate(snapshot.physicalState());
                if (requirement.tester().isError(state)) {
                    throw new IllegalArgumentException("UPDATE_TIME requirement activates in error: " + id);
                }
                active.put(id, state);
            }
            CanonicalUpdateConfiguration<S, M> configuration = CanonicalUpdateConfiguration.of(
                    snapshot.physicalState(), active, updateActions);
            if (!isStructurallyValid(configuration)) {
                throw new IllegalStateException("Constructed initial configuration violates canonical invariants");
            }
            configurations.add(configuration);
        }
        return Collections.unmodifiableList(new ArrayList<>(configurations));
    }

    private List<GoalSignature<S, M>> validateGoalSignatures(List<GoalSignature<S, M>> signatures) {
        if (signatures.isEmpty()) {
            throw new IllegalArgumentException("At least one reachable new endpoint goal signature is required");
        }
        Set<String> endpointIds = new LinkedHashSet<>();
        List<GoalSignature<S, M>> result = new ArrayList<>();
        for (GoalSignature<S, M> signature : signatures) {
            signature = Objects.requireNonNull(signature, "goal signature");
            if (!endpointIds.add(signature.endpointId())) {
                throw new IllegalArgumentException("Duplicate goal endpoint id: " + signature.endpointId());
            }
            if (!signature.physicalState().allNew() || !isPhysicalStateValid(signature.physicalState())) {
                throw new IllegalArgumentException("Goal signature must contain valid NEW component states: "
                        + signature.endpointId());
            }
            if (!signature.newRequirementStates().keySet().equals(newRequirementIds)) {
                throw new IllegalArgumentException(
                        "Goal signature must provide exactly every NEW tester state: " + signature.endpointId());
            }
            for (String id : newRequirementIds) {
                M state = signature.newRequirementStates().get(id);
                SafetyTester<M> tester = requirementsById.get(id).tester();
                if (!tester.states().contains(state) || tester.isError(state)) {
                    throw new IllegalArgumentException(
                            "Invalid/unsafe NEW tester state in goal signature " + signature.endpointId());
                }
            }
            result.add(signature);
        }
        result.sort(Comparator.naturalOrder());
        return Collections.unmodifiableList(result);
    }

    private static void registerUpdateAction(
            String action,
            UpdateEventKind kind,
            Set<String> allActions,
            Map<String, UpdateEventKind> kinds) {
        action = nonBlank(action, "update action");
        if (!allActions.add(action)) {
            throw new IllegalArgumentException("Every concrete update action must be unique: " + action);
        }
        kinds.put(action, kind);
    }

    private static <S> List<Map<S, Integer>> indexComponentStates(
            List<VersionedComponent<S>> components, boolean oldVersion) {
        List<Map<S, Integer>> result = new ArrayList<>();
        for (VersionedComponent<S> component : components) {
            result.add(indexOrder(oldVersion
                    ? component.oldLts().states()
                    : component.newLts().states()));
        }
        return Collections.unmodifiableList(result);
    }

    private static <S, M> Map<String, Map<M, Integer>> indexTesterStates(
            Map<String, Requirement<S, M>> requirements) {
        Map<String, Map<M, Integer>> result = new LinkedHashMap<>();
        for (Requirement<S, M> requirement : requirements.values()) {
            result.put(requirement.id(), indexOrder(requirement.tester().states()));
        }
        return Collections.unmodifiableMap(result);
    }

    private static <T> Map<T, Integer> indexOrder(Collection<? extends T> values) {
        Map<T, Integer> result = new LinkedHashMap<>();
        int index = 0;
        for (T value : values) {
            result.put(value, Integer.valueOf(index++));
        }
        return Collections.unmodifiableMap(result);
    }

    private static <T> List<T> immutableList(Collection<? extends T> values, String label) {
        Objects.requireNonNull(values, label);
        List<T> copy = new ArrayList<>();
        for (T value : values) copy.add(Objects.requireNonNull(value, label + " element"));
        return Collections.unmodifiableList(copy);
    }

    private static LinkedHashSet<String> checkedActions(Collection<String> values, String label) {
        Objects.requireNonNull(values, label);
        LinkedHashSet<String> result = new LinkedHashSet<>();
        for (String value : values) result.add(nonBlank(value, label));
        return result;
    }

    private static Map<String, Set<String>> immutableSetMap(Map<String, Set<String>> source) {
        Map<String, Set<String>> result = new LinkedHashMap<>();
        for (Map.Entry<String, Set<String>> entry : source.entrySet()) {
            result.put(entry.getKey(), Collections.unmodifiableSet(new LinkedHashSet<>(entry.getValue())));
        }
        return Collections.unmodifiableMap(result);
    }

    private static String nonBlank(String value, String label) {
        Objects.requireNonNull(value, label);
        if (value.trim().isEmpty()) throw new IllegalArgumentException(label + " must not be blank");
        return value;
    }

    public static final class Builder<S, M> {
        private final List<VersionedComponent<S>> components = new ArrayList<>();
        private final List<Requirement<S, M>> requirements = new ArrayList<>();
        private final Set<String> normalActions = new LinkedHashSet<>();
        private final Set<String> controllableNormalActions = new LinkedHashSet<>();
        private final Set<String> commonAlphabet = new LinkedHashSet<>();
        private boolean normalActionsExplicit;
        private boolean commonAlphabetExplicit;
        private String hotSwapInAction = DEFAULT_HOT_SWAP_IN;
        private String hotSwapOutAction = DEFAULT_HOT_SWAP_OUT;
        private final List<PrecedenceEdge> precedenceEdges = new ArrayList<>();
        private final List<InitialSnapshot<S, M>> initialSnapshots = new ArrayList<>();
        private final List<GoalSignature<S, M>> goalSignatures = new ArrayList<>();
        private boolean initialSnapshotsManual;
        private boolean initialSnapshotsEnumerated;
        private boolean goalSignaturesManual;
        private boolean goalSignaturesEnumerated;

        public Builder<S, M> addComponent(VersionedComponent<S> component) {
            components.add(Objects.requireNonNull(component, "component"));
            return this;
        }

        public Builder<S, M> components(Collection<? extends VersionedComponent<S>> values) {
            components.clear();
            for (VersionedComponent<S> value : Objects.requireNonNull(values, "components")) {
                addComponent(value);
            }
            return this;
        }

        public Builder<S, M> addRequirement(Requirement<S, M> requirement) {
            requirements.add(Objects.requireNonNull(requirement, "requirement"));
            return this;
        }

        public Builder<S, M> requirements(Collection<? extends Requirement<S, M>> values) {
            requirements.clear();
            for (Requirement<S, M> value : Objects.requireNonNull(values, "requirements")) {
                addRequirement(value);
            }
            return this;
        }

        public Builder<S, M> normalActions(Collection<String> actions) {
            normalActions.clear();
            normalActions.addAll(Objects.requireNonNull(actions, "normalActions"));
            normalActionsExplicit = true;
            return this;
        }

        public Builder<S, M> controllableNormalActions(Collection<String> actions) {
            controllableNormalActions.clear();
            controllableNormalActions.addAll(Objects.requireNonNull(actions, "controllableNormalActions"));
            return this;
        }

        public Builder<S, M> addNormalAction(String action, boolean controllable) {
            normalActions.add(nonBlank(action, "normal action"));
            normalActionsExplicit = true;
            if (controllable) controllableNormalActions.add(action);
            return this;
        }

        public Builder<S, M> commonAlphabet(Collection<String> actions) {
            commonAlphabet.clear();
            commonAlphabet.addAll(Objects.requireNonNull(actions, "commonAlphabet"));
            commonAlphabetExplicit = true;
            return this;
        }

        public Builder<S, M> hotSwapActions(String hotSwapInAction, String hotSwapOutAction) {
            this.hotSwapInAction = nonBlank(hotSwapInAction, "hotSwapIn action");
            this.hotSwapOutAction = nonBlank(hotSwapOutAction, "hotSwapOut action");
            return this;
        }

        /** Adds the strict precedence edge {@code before < after}. */
        public Builder<S, M> addPrecedence(String before, String after) {
            precedenceEdges.add(new PrecedenceEdge(
                    nonBlank(before, "precedence predecessor"),
                    nonBlank(after, "precedence successor")));
            return this;
        }

        /**
         * Low-level trusted input. Prefer {@link #initialSnapshotsFromReachable}
         * when the full old endpoint LTS is available.
         */
        public Builder<S, M> addInitialSnapshot(InitialSnapshot<S, M> snapshot) {
            if (initialSnapshotsEnumerated) {
                throw new IllegalStateException(
                        "Cannot mix manual old endpoint snapshots with exhaustive enumeration");
            }
            initialSnapshotsManual = true;
            initialSnapshots.add(Objects.requireNonNull(snapshot, "snapshot"));
            return this;
        }

        public Builder<S, M> initialSnapshots(Collection<? extends InitialSnapshot<S, M>> values) {
            if (initialSnapshotsEnumerated) {
                throw new IllegalStateException(
                        "Cannot replace exhaustively enumerated old endpoint snapshots manually");
            }
            initialSnapshots.clear();
            initialSnapshotsManual = true;
            for (InitialSnapshot<S, M> value : Objects.requireNonNull(values, "initialSnapshots")) {
                addInitialSnapshot(value);
            }
            return this;
        }

        /**
         * Enumerates every reachable old endpoint state and projects it into
         * one Q0 snapshot. A null projection is rejected rather than silently
         * dropping an endpoint state. The projection function represents the
         * plan's supplied endpoint/component isomorphism; Link checking later
         * verifies its transition consistency.
         */
        public <Z> Builder<S, M> initialSnapshotsFromReachable(
                FiniteLts<Z> oldEndpoint,
                Function<? super Z, ? extends InitialSnapshot<S, M>> projection) {
            Objects.requireNonNull(oldEndpoint, "oldEndpoint");
            Objects.requireNonNull(projection, "projection");
            if (initialSnapshotsManual || initialSnapshotsEnumerated || !initialSnapshots.isEmpty()) {
                throw new IllegalStateException(
                        "Exhaustive old endpoint enumeration cannot be mixed or repeated");
            }
            initialSnapshotsEnumerated = true;
            for (Z endpointState : oldEndpoint.reachableStates()) {
                InitialSnapshot<S, M> snapshot = Objects.requireNonNull(
                        projection.apply(endpointState),
                        "Initial projection for reachable endpoint state " + endpointState);
                initialSnapshots.add(snapshot);
            }
            return this;
        }

        /**
         * Low-level trusted input. Prefer {@link #goalSignaturesFromReachable}
         * when the full new endpoint LTS is available.
         */
        public Builder<S, M> addGoalSignature(GoalSignature<S, M> signature) {
            if (goalSignaturesEnumerated) {
                throw new IllegalStateException(
                        "Cannot mix manual new endpoint goals with exhaustive enumeration");
            }
            goalSignaturesManual = true;
            goalSignatures.add(Objects.requireNonNull(signature, "signature"));
            return this;
        }

        public Builder<S, M> goalSignatures(Collection<? extends GoalSignature<S, M>> values) {
            if (goalSignaturesEnumerated) {
                throw new IllegalStateException(
                        "Cannot replace exhaustively enumerated new endpoint goals manually");
            }
            goalSignatures.clear();
            goalSignaturesManual = true;
            for (GoalSignature<S, M> value : Objects.requireNonNull(values, "goalSignatures")) {
                addGoalSignature(value);
            }
            return this;
        }

        /**
         * Enumerates and projects every reachable new endpoint state. The full
         * Link checker later verifies transition consistency of this supplied
         * endpoint projection.
         */
        public <Z> Builder<S, M> goalSignaturesFromReachable(
                FiniteLts<Z> newEndpoint,
                Function<? super Z, ? extends GoalSignature<S, M>> projection) {
            return goalSignaturesFromReachable(
                    newEndpoint, projection, ignored -> true);
        }

        /**
         * Exhaustively checks the reachable new endpoint projection while
         * selecting an arbitrary nonempty subset as {@code Z_load}.  States
         * outside the subset remain POST states of the linked new closed loop,
         * but are not legal update-completion targets.
         */
        public <Z> Builder<S, M> goalSignaturesFromReachable(
                FiniteLts<Z> newEndpoint,
                Function<? super Z, ? extends GoalSignature<S, M>> projection,
                Predicate<? super Z> loadable) {
            Objects.requireNonNull(newEndpoint, "newEndpoint");
            Objects.requireNonNull(projection, "projection");
            Objects.requireNonNull(loadable, "loadable");
            if (goalSignaturesManual || goalSignaturesEnumerated || !goalSignatures.isEmpty()) {
                throw new IllegalStateException(
                        "Exhaustive new endpoint enumeration cannot be mixed or repeated");
            }
            goalSignaturesEnumerated = true;
            Set<String> endpointIds = new LinkedHashSet<>();
            for (Z endpointState : newEndpoint.reachableStates()) {
                GoalSignature<S, M> signature = Objects.requireNonNull(
                        projection.apply(endpointState),
                        "Goal projection for reachable endpoint state " + endpointState);
                if (!endpointIds.add(signature.endpointId())) {
                    throw new IllegalArgumentException(
                            "Duplicate reachable new endpoint id: "
                                    + signature.endpointId());
                }
                if (loadable.test(endpointState)) {
                    goalSignatures.add(signature);
                }
            }
            return this;
        }

        public FineGrainedUpdateProblem<S, M> build() {
            return new FineGrainedUpdateProblem<>(this);
        }
    }

    private static final class PrecedenceEdge {
        private final String before;
        private final String after;

        private PrecedenceEdge(String before, String after) {
            this.before = before;
            this.after = after;
        }

        @Override
        public String toString() {
            return before + " < " + after;
        }
    }
}
