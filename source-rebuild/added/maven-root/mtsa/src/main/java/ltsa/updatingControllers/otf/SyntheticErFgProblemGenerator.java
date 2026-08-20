package ltsa.updatingControllers.otf;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.Collections;
import java.util.Comparator;
import java.util.Deque;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

/**
 * Deterministic generator for the matched synthetic ER-FG evaluation panel.
 *
 * <p>Every instance contains independently reconfigurable environment
 * components and independently stopped/started old/new requirements.  The
 * U-local and U-cross profiles use the same two-state update-time monitor and
 * differ only in the binding of the monitor's second uncontrollable event:
 * U-local binds it to the anchor component, while U-cross binds it to the
 * adjacent component.  Thus the topology, size, seed, and mutation factors are
 * reproducible and can be paired without editing an LTS file by hand.</p>
 */
public final class SyntheticErFgProblemGenerator {

    public static final String GENERATOR_VERSION = "synthetic-erfg-v2";

    private static final String IDLE = "idle";
    private static final String READY = "ready";
    private static final String BUSY = "busy";
    private static final String DONE = "done";
    private static final String OK = "ok";
    private static final String ZERO = "zero";
    private static final String ONE = "one";
    private static final String ERROR = "error";

    private SyntheticErFgProblemGenerator() {
        // Utility class.
    }

    public enum Topology {
        PIPELINE("pipeline"),
        RING("ring"),
        HUB("hub");

        private final String id;

        Topology(String id) {
            this.id = id;
        }

        public String id() {
            return id;
        }

        public static Topology parse(String text) {
            return parseEnum(values(), text, "topology");
        }
    }

    public enum UProfile {
        U0("u0"),
        U_LOCAL("u_local"),
        U_CROSS("u_cross");

        private final String id;

        UProfile(String id) {
            this.id = id;
        }

        public String id() {
            return id;
        }

        public static UProfile parse(String text) {
            return parseEnum(values(), text, "U profile");
        }
    }

    public enum Mutation {
        BASE("base", true),
        EMPTY_TRANSFER("empty_transfer", false),
        REJECT_UNCONTROLLABLE("reject_uncontrollable", false),
        UNCONTROLLABLE_LIVELOCK("uncontrollable_livelock", false);

        private final String id;
        private final boolean expectedWinning;

        Mutation(String id, boolean expectedWinning) {
            this.id = id;
            this.expectedWinning = expectedWinning;
        }

        public String id() {
            return id;
        }

        public boolean expectedWinning() {
            return expectedWinning;
        }

        public static Mutation parse(String text) {
            return parseEnum(values(), text, "mutation");
        }
    }

    /**
     * Generates one immutable problem.  The same tuple of parameters always
     * produces the same model hash and graph.
     */
    public static GeneratedProblem generate(
            Topology topology,
            int componentCount,
            long masterSeed,
            UProfile profile,
            Mutation mutation) {
        if (topology == null || profile == null || mutation == null) {
            throw new IllegalArgumentException(
                    "topology, profile, and mutation must be non-null");
        }
        if (componentCount < 2) {
            throw new IllegalArgumentException(
                    "synthetic ER-FG instances require at least two components");
        }

        List<Edge> edges = topologyEdges(
                topology, componentCount, masterSeed);
        int mutatedComponent = boundedHash(
                masterSeed, "mutation-component", componentCount);
        Set<String> normalActions = new LinkedHashSet<String>();
        Set<String> controllableNormalActions =
                new LinkedHashSet<String>();
        List<VersionedComponent<String>> components =
                new ArrayList<VersionedComponent<String>>();
        long transferEdges = 0L;

        for (int component = 0; component < componentCount; component++) {
            ComponentBuild built = buildComponent(
                    component,
                    componentCount,
                    masterSeed,
                    profile,
                    mutation,
                    mutatedComponent,
                    edges);
            components.add(built.component);
            normalActions.addAll(built.normalActions);
            controllableNormalActions.addAll(
                    built.controllableNormalActions);
            transferEdges += built.transferEdges;
        }

        List<String> oldRequirementIds = new ArrayList<String>();
        List<String> newRequirementIds = new ArrayList<String>();
        List<String> updateRequirementIds = new ArrayList<String>();
        Set<String> updateActions = new LinkedHashSet<String>();
        for (int component = 0; component < componentCount; component++) {
            updateActions.add(reconfigureAction(component));
        }
        for (int edgeIndex = 0; edgeIndex < edges.size(); edgeIndex++) {
            String oldId = oldRequirementId(edgeIndex);
            String newId = newRequirementId(edgeIndex);
            oldRequirementIds.add(oldId);
            newRequirementIds.add(newId);
            updateActions.add(stopAction(edgeIndex));
            updateActions.add(startAction(edgeIndex));
            if (profile != UProfile.U0) {
                updateRequirementIds.add(
                        updateRequirementId(edgeIndex));
            }
        }
        if (mutation == Mutation.REJECT_UNCONTROLLABLE) {
            updateRequirementIds.add("mut_reject");
        }

        Set<String> commonAlphabet =
                new LinkedHashSet<String>(normalActions);
        commonAlphabet.addAll(updateActions);
        PhysicalState<String> initialPhysical =
                uniformPhysicalState(componentCount, false, IDLE);
        PhysicalState<String> goalPhysical =
                uniformPhysicalState(componentCount, true, DONE);

        List<Requirement<String, String>> requirements =
                new ArrayList<Requirement<String, String>>();
        SafetyTester<String> alwaysSafe = alwaysSafeTester();
        ResidualLanguage<String> alwaysSafeResidual =
                alwaysSafeResidual(commonAlphabet);
        for (int edgeIndex = 0; edgeIndex < edges.size(); edgeIndex++) {
            requirements.add(
                    Requirement.<String, String>oldRequirement(
                            oldRequirementId(edgeIndex),
                            alwaysSafe,
                            stopAction(edgeIndex)));
            ActivationSpec<String, String> activation =
                    ActivationSpec
                            .<String, String, String>builder(
                                    alwaysSafeResidual)
                            .put(goalPhysical, OK, OK)
                            .build();
            requirements.add(
                    Requirement.<String, String>newRequirement(
                            newRequirementId(edgeIndex),
                            alwaysSafe,
                            activation,
                            startAction(edgeIndex)));
        }

        if (profile != UProfile.U0) {
            for (int edgeIndex = 0;
                    edgeIndex < edges.size();
                    edgeIndex++) {
                Edge edge = edges.get(edgeIndex);
                String firstAction = uncontrollableFirst(edge.anchor);
                String secondAction = profile == UProfile.U_LOCAL
                        ? uncontrollableSecond(edge.anchor)
                        : uncontrollableSecond(edge.partner);
                SafetyTester<String> monitor = twoEventMonitor(
                        firstAction, secondAction);
                ResidualLanguage<String> residual = twoEventResidual(
                        commonAlphabet, firstAction, secondAction);
                ActivationSpec<String, String> activation =
                        ActivationSpec
                                .<String, String, String>builder(residual)
                                .put(initialPhysical, ZERO, ZERO)
                                .build();
                requirements.add(
                        Requirement.<String, String>updateTimeRequirement(
                                updateRequirementId(edgeIndex),
                                monitor,
                                activation));
            }
        }

        if (mutation == Mutation.REJECT_UNCONTROLLABLE) {
            String faultAction = rejectAction(mutatedComponent);
            SafetyTester<String> rejecting =
                    rejectingTester(faultAction);
            ResidualLanguage<String> residual =
                    rejectingResidual(commonAlphabet, faultAction);
            ActivationSpec<String, String> activation =
                    ActivationSpec
                            .<String, String, String>builder(residual)
                            .put(initialPhysical, OK, OK)
                            .build();
            requirements.add(
                    Requirement.<String, String>updateTimeRequirement(
                            "mut_reject", rejecting, activation));
        }

        Map<String, String> initialRequirementStates =
                new LinkedHashMap<String, String>();
        for (String id : oldRequirementIds) {
            initialRequirementStates.put(id, OK);
        }
        Map<String, String> goalRequirementStates =
                new LinkedHashMap<String, String>();
        for (String id : newRequirementIds) {
            goalRequirementStates.put(id, OK);
        }

        EndpointBundle endpoints = buildEndpoints(
                components,
                normalActions,
                controllableNormalActions,
                initialPhysical,
                componentCount);
        Map<PhysicalState<String>, GoalSignature<String, String>>
                goalByEndpointState = goalSignatures(
                        endpoints.newClosedLoop,
                        goalRequirementStates);

        FineGrainedUpdateProblem.Builder<String, String> builder =
                FineGrainedUpdateProblem.<String, String>builder()
                        .components(components)
                        .requirements(requirements)
                        .normalActions(normalActions)
                        .controllableNormalActions(
                                controllableNormalActions)
                        .commonAlphabet(commonAlphabet)
                        .initialSnapshotsFromReachable(
                                endpoints.oldClosedLoop,
                                state -> new InitialSnapshot<String, String>(
                                        state,
                                        initialRequirementStates))
                        .goalSignaturesFromReachable(
                                endpoints.newClosedLoop,
                                goalByEndpointState::get);

        Set<String> precedence = new LinkedHashSet<String>();
        for (int edgeIndex = 0; edgeIndex < edges.size(); edgeIndex++) {
            Edge edge = edges.get(edgeIndex);
            addPrecedence(
                    builder,
                    precedence,
                    stopAction(edgeIndex),
                    reconfigureAction(edge.anchor));
            addPrecedence(
                    builder,
                    precedence,
                    stopAction(edgeIndex),
                    reconfigureAction(edge.partner));
            addPrecedence(
                    builder,
                    precedence,
                    reconfigureAction(edge.anchor),
                    startAction(edgeIndex));
            addPrecedence(
                    builder,
                    precedence,
                    reconfigureAction(edge.partner),
                    startAction(edgeIndex));
        }

        FineGrainedUpdateProblem<String, String> problem =
                builder.build();
        String descriptor = canonicalDescriptor(
                topology,
                componentCount,
                masterSeed,
                profile,
                mutation,
                mutatedComponent,
                edges);
        String modelHash = sha256Hex(descriptor);
        String inputId = "syn_" + topology.id()
                + "_n" + componentCount
                + "_s" + masterSeed
                + "_" + profile.id()
                + "_" + mutation.id();
        return new GeneratedProblem(
                problem,
                endpoints.oldClosedLoop,
                endpoints.newClosedLoop,
                initialRequirementStates,
                goalByEndpointState,
                inputId,
                modelHash,
                topology,
                componentCount,
                masterSeed,
                profile,
                mutation,
                edges.size(),
                oldRequirementIds.size(),
                newRequirementIds.size(),
                updateRequirementIds.size(),
                normalActions.size(),
                controllableNormalActions.size(),
                normalActions.size()
                        - controllableNormalActions.size(),
                updateActions.size(),
                precedence.size(),
                transferEdges,
                mutatedComponent);
    }

    private static ComponentBuild buildComponent(
            int component,
            int componentCount,
            long masterSeed,
            UProfile profile,
            Mutation mutation,
            int mutatedComponent,
            List<Edge> edges) {
        FiniteLts.Builder<String> oldLts =
                FiniteLts.<String>builder(IDLE)
                        .addStates(
                                Arrays.asList(
                                        IDLE, READY, BUSY, DONE));
        FiniteLts.Builder<String> newLts =
                FiniteLts.<String>builder(IDLE)
                        .addStates(
                                Arrays.asList(
                                        IDLE, READY, BUSY, DONE));
        Set<String> normal = new LinkedHashSet<String>();
        Set<String> controllable = new LinkedHashSet<String>();

        String begin = privateAction("begin", component);
        String inspect = privateAction("inspect", component);
        String finish = privateAction("finish", component);
        String done = privateAction("done", component);
        addControllableTransition(
                oldLts, newLts, normal, controllable,
                IDLE, begin, READY);
        addControllableTransition(
                oldLts, newLts, normal, controllable,
                READY, inspect, BUSY);
        addControllableTransition(
                oldLts, newLts, normal, controllable,
                BUSY, finish, DONE);
        addControllableTransition(
                oldLts, newLts, normal, controllable,
                DONE, done, DONE);

        int distractorCount = 1 + boundedHash(
                masterSeed,
                "distractors-" + component,
                3);
        String[] distractorStates =
                new String[] { IDLE, READY, BUSY };
        for (int index = 0;
                index < distractorCount;
                index++) {
            String action = "a_spin_" + component + "_" + index;
            String state = distractorStates[index];
            oldLts.addTransition(state, action, state);
            newLts.addTransition(state, action, state);
            normal.add(action);
            controllable.add(action);
        }

        for (Edge edge : edges) {
            if (!edge.incident(component)) {
                continue;
            }
            String action = edgeAction(edge);
            for (String state :
                    Arrays.asList(IDLE, READY, BUSY, DONE)) {
                oldLts.addTransition(state, action, state);
            }
            newLts.addTransition(READY, action, BUSY);
            normal.add(action);
            controllable.add(action);
        }

        if (profile != UProfile.U0) {
            String first = uncontrollableFirst(component);
            String second = uncontrollableSecond(component);
            newLts.addTransition(READY, first, BUSY);
            newLts.addTransition(BUSY, second, DONE);
            normal.add(first);
            normal.add(second);
        }

        if (mutation == Mutation.REJECT_UNCONTROLLABLE
                && component == mutatedComponent) {
            String action = rejectAction(component);
            oldLts.addTransition(IDLE, action, IDLE);
            normal.add(action);
        }
        if (mutation == Mutation.UNCONTROLLABLE_LIVELOCK
                && component == mutatedComponent) {
            String action = livelockAction(component);
            for (String state :
                    Arrays.asList(IDLE, READY, BUSY, DONE)) {
                oldLts.addTransition(state, action, state);
                newLts.addTransition(state, action, state);
            }
            normal.add(action);
        }

        Map<String, Collection<String>> transfer =
                new LinkedHashMap<String, Collection<String>>();
        if (!(mutation == Mutation.EMPTY_TRANSFER
                && component == mutatedComponent)) {
            List<String> initialTargets =
                    new ArrayList<String>();
            initialTargets.add(IDLE);
            if (boundedHash(
                    masterSeed,
                    "relational-transfer-" + component,
                    3) == 0) {
                initialTargets.add(READY);
            }
            transfer.put(IDLE, initialTargets);
            transfer.put(
                    READY,
                    Collections.singletonList(READY));
        }
        long transferEdges = 0L;
        for (Collection<String> targets : transfer.values()) {
            transferEdges += targets.size();
        }
        VersionedComponent<String> result =
                new VersionedComponent<String>(
                        "cell_" + component,
                        oldLts.build(),
                        newLts.build(),
                        transfer,
                        reconfigureAction(component));
        return new ComponentBuild(
                result, normal, controllable, transferEdges);
    }

    private static void addControllableTransition(
            FiniteLts.Builder<String> oldLts,
            FiniteLts.Builder<String> newLts,
            Set<String> normal,
            Set<String> controllable,
            String source,
            String action,
            String target) {
        oldLts.addTransition(source, action, target);
        newLts.addTransition(source, action, target);
        normal.add(action);
        controllable.add(action);
    }

    /**
     * Constructs concrete deadlock-free old/new closed loops for the endpoint
     * projections.  A closed loop may disable controllable actions, but every
     * enabled uncontrollable action and every one of its plant outcomes is
     * retained.  Consequently the generated Q0 and Z_load sets are exhaustive
     * reachable endpoint projections rather than trusted hand-written samples.
     */
    private static EndpointBundle buildEndpoints(
            List<VersionedComponent<String>> components,
            Set<String> normalActions,
            Set<String> controllableNormalActions,
            PhysicalState<String> oldInitial,
            int componentCount) {
        FiniteLts<PhysicalState<String>> oldClosedLoop =
                buildEndpointClosedLoop(
                        components,
                        normalActions,
                        controllableNormalActions,
                        oldInitial,
                        true);
        FiniteLts<PhysicalState<String>> newClosedLoop =
                buildEndpointClosedLoop(
                        components,
                        normalActions,
                        controllableNormalActions,
                        uniformPhysicalState(
                                componentCount, true, IDLE),
                        false);
        assertEligibleEndpoint(
                "old",
                oldClosedLoop,
                components,
                normalActions,
                controllableNormalActions);
        assertEligibleEndpoint(
                "new",
                newClosedLoop,
                components,
                normalActions,
                controllableNormalActions);
        return new EndpointBundle(oldClosedLoop, newClosedLoop);
    }

    private static FiniteLts<PhysicalState<String>>
            buildEndpointClosedLoop(
                    List<VersionedComponent<String>> components,
                    Set<String> normalActions,
                    Set<String> controllableNormalActions,
                    PhysicalState<String> initial,
                    boolean oldEndpoint) {
        FiniteLts.Builder<PhysicalState<String>> builder =
                FiniteLts.<PhysicalState<String>>builder(initial)
                        .addActions(normalActions);
        LinkedHashSet<PhysicalState<String>> discovered =
                new LinkedHashSet<PhysicalState<String>>();
        Deque<PhysicalState<String>> queue =
                new ArrayDeque<PhysicalState<String>>();
        List<String> orderedActions =
                new ArrayList<String>(normalActions);
        Collections.sort(orderedActions);
        discovered.add(initial);
        queue.addLast(initial);

        while (!queue.isEmpty()) {
            PhysicalState<String> source = queue.removeFirst();
            for (String action : orderedActions) {
                if (controllableNormalActions.contains(action)) {
                    continue;
                }
                addEndpointTransitions(
                        builder,
                        discovered,
                        queue,
                        source,
                        action,
                        physicalPost(components, source, action));
            }

            String selected = oldEndpoint
                    ? "a_spin_0_0"
                    : preferredNewEndpointAction(source);
            Set<PhysicalState<String>> outcomes =
                    physicalPost(components, source, selected);
            if (outcomes.isEmpty()) {
                throw new IllegalStateException(
                        (oldEndpoint ? "old" : "new")
                                + " endpoint controller selected disabled action "
                                + selected + " at " + source);
            }
            addEndpointTransitions(
                    builder,
                    discovered,
                    queue,
                    source,
                    selected,
                    outcomes);
        }
        return builder.build();
    }

    private static String preferredNewEndpointAction(
            PhysicalState<String> state) {
        for (int component = 0;
                component < state.size();
                component++) {
            TaggedState<String> local = state.component(component);
            if (!local.isNew()) {
                throw new IllegalArgumentException(
                        "new endpoint contains an OLD component: " + state);
            }
            if (IDLE.equals(local.state())) {
                return privateAction("begin", component);
            }
            if (READY.equals(local.state())) {
                return privateAction("inspect", component);
            }
            if (BUSY.equals(local.state())) {
                return privateAction("finish", component);
            }
            if (!DONE.equals(local.state())) {
                throw new IllegalArgumentException(
                        "unknown new endpoint local state: " + local);
            }
        }
        return privateAction("done", 0);
    }

    private static void addEndpointTransitions(
            FiniteLts.Builder<PhysicalState<String>> builder,
            Set<PhysicalState<String>> discovered,
            Deque<PhysicalState<String>> queue,
            PhysicalState<String> source,
            String action,
            Set<PhysicalState<String>> outcomes) {
        for (PhysicalState<String> outcome : outcomes) {
            builder.addTransition(source, action, outcome);
            if (discovered.add(outcome)) {
                queue.addLast(outcome);
            }
        }
    }

    private static Set<PhysicalState<String>> physicalPost(
            List<VersionedComponent<String>> components,
            PhysicalState<String> state,
            String action) {
        List<List<TaggedState<String>>> localOutcomes =
                new ArrayList<List<TaggedState<String>>>();
        boolean participant = false;
        for (int index = 0; index < components.size(); index++) {
            TaggedState<String> local = state.component(index);
            VersionedComponent<String> component = components.get(index);
            FiniteLts<String> active = local.isOld()
                    ? component.oldLts()
                    : component.newLts();
            if (component.environmentHasAction(
                    local.version(), action)) {
                participant = true;
            }
            if (active.hasAction(action)) {
                Set<String> targets =
                        active.successors(local.state(), action);
                if (targets.isEmpty()) {
                    return Collections.emptySet();
                }
                List<TaggedState<String>> taggedTargets =
                        new ArrayList<TaggedState<String>>();
                for (String target : targets) {
                    taggedTargets.add(
                            TaggedState.of(local.version(), target));
                }
                localOutcomes.add(taggedTargets);
            } else {
                localOutcomes.add(
                        Collections.singletonList(local));
            }
        }
        if (!participant) {
            return Collections.emptySet();
        }
        LinkedHashSet<PhysicalState<String>> outcomes =
                new LinkedHashSet<PhysicalState<String>>();
        cartesianPhysical(
                localOutcomes,
                0,
                new ArrayList<TaggedState<String>>(),
                outcomes);
        return outcomes;
    }

    private static void cartesianPhysical(
            List<List<TaggedState<String>>> choices,
            int index,
            List<TaggedState<String>> current,
            Set<PhysicalState<String>> outcomes) {
        if (index == choices.size()) {
            outcomes.add(PhysicalState.of(current));
            return;
        }
        for (TaggedState<String> choice : choices.get(index)) {
            current.add(choice);
            cartesianPhysical(
                    choices, index + 1, current, outcomes);
            current.remove(current.size() - 1);
        }
    }

    private static void assertEligibleEndpoint(
            String name,
            FiniteLts<PhysicalState<String>> closedLoop,
            List<VersionedComponent<String>> components,
            Set<String> normalActions,
            Set<String> controllableNormalActions) {
        for (PhysicalState<String> state
                : closedLoop.reachableStates()) {
            if (closedLoop.enabledActions(state).isEmpty()) {
                throw new IllegalStateException(
                        name + " endpoint deadlocks at " + state);
            }
            for (String action : normalActions) {
                Set<PhysicalState<String>> plantOutcomes =
                        physicalPost(components, state, action);
                Set<PhysicalState<String>> retained =
                        closedLoop.successors(state, action);
                if (!retained.isEmpty()
                        && !retained.equals(plantOutcomes)) {
                    throw new IllegalStateException(
                            name + " endpoint drops a plant outcome at "
                                    + state + " / " + action);
                }
                if (!controllableNormalActions.contains(action)
                        && !plantOutcomes.isEmpty()
                        && !retained.equals(plantOutcomes)) {
                    throw new IllegalStateException(
                            name + " endpoint disables an uncontrollable action at "
                                    + state + " / " + action);
                }
            }
        }
    }

    private static Map<PhysicalState<String>,
            GoalSignature<String, String>> goalSignatures(
                    FiniteLts<PhysicalState<String>> newClosedLoop,
                    Map<String, String> goalRequirementStates) {
        Map<PhysicalState<String>, GoalSignature<String, String>> result =
                new LinkedHashMap<PhysicalState<String>,
                        GoalSignature<String, String>>();
        int index = 0;
        for (PhysicalState<String> state
                : newClosedLoop.reachableStates()) {
            result.put(
                    state,
                    new GoalSignature<String, String>(
                            "post_" + index++,
                            state,
                            goalRequirementStates));
        }
        return Collections.unmodifiableMap(result);
    }

    private static List<Edge> topologyEdges(
            Topology topology,
            int componentCount,
            long masterSeed) {
        List<UnorientedEdge> raw =
                new ArrayList<UnorientedEdge>();
        if (topology == Topology.PIPELINE) {
            for (int component = 0;
                    component + 1 < componentCount;
                    component++) {
                raw.add(
                        new UnorientedEdge(
                                component, component + 1));
            }
        } else if (topology == Topology.HUB) {
            int hub = boundedHash(
                    masterSeed, "hub", componentCount);
            for (int component = 0;
                    component < componentCount;
                    component++) {
                if (component != hub) {
                    raw.add(new UnorientedEdge(hub, component));
                }
            }
        } else {
            int omitted = boundedHash(
                    masterSeed, "ring-omitted-edge",
                    componentCount);
            for (int component = 0;
                    component < componentCount;
                    component++) {
                if (component == omitted) {
                    continue;
                }
                raw.add(
                        new UnorientedEdge(
                                component,
                                (component + 1)
                                        % componentCount));
            }
        }

        Collections.sort(raw, new Comparator<UnorientedEdge>() {
            @Override
            public int compare(
                    UnorientedEdge left,
                    UnorientedEdge right) {
                int comparison = Integer.compare(
                        left.minimum, right.minimum);
                return comparison != 0
                        ? comparison
                        : Integer.compare(
                                left.maximum, right.maximum);
            }
        });
        List<Edge> result = new ArrayList<Edge>();
        for (UnorientedEdge edge : raw) {
            boolean reverse = boundedHash(
                    masterSeed,
                    "edge-orientation-"
                            + edge.minimum
                            + "-"
                            + edge.maximum,
                    2) == 1;
            result.add(
                    reverse
                            ? new Edge(
                                    edge.maximum, edge.minimum)
                            : new Edge(
                                    edge.minimum, edge.maximum));
        }
        return Collections.unmodifiableList(result);
    }

    private static SafetyTester<String> alwaysSafeTester() {
        return SafetyTester.<String>builder()
                .initialState(OK)
                .build();
    }

    private static ResidualLanguage<String> alwaysSafeResidual(
            Set<String> commonAlphabet) {
        TableResidualLanguage.Builder<String> builder =
                TableResidualLanguage.<String>builder()
                        .initialState(OK)
                        .addActions(commonAlphabet);
        for (String action : commonAlphabet) {
            builder.addTransition(OK, action, OK);
        }
        return builder.build();
    }

    private static SafetyTester<String> twoEventMonitor(
            String firstAction,
            String secondAction) {
        return SafetyTester.<String>builder()
                .initialState(ZERO)
                .addState(ONE)
                .addActions(
                        Arrays.asList(
                                firstAction, secondAction))
                .addTransition(ZERO, firstAction, ONE)
                .addTransition(ZERO, secondAction, ZERO)
                .addTransition(ONE, firstAction, ONE)
                .addTransition(ONE, secondAction, ZERO)
                .build();
    }

    private static ResidualLanguage<String> twoEventResidual(
            Set<String> commonAlphabet,
            String firstAction,
            String secondAction) {
        TableResidualLanguage.Builder<String> builder =
                TableResidualLanguage.<String>builder()
                        .initialState(ZERO)
                        .addState(ONE)
                        .addActions(commonAlphabet);
        for (String action : commonAlphabet) {
            builder.addTransition(
                    ZERO,
                    action,
                    action.equals(firstAction) ? ONE : ZERO);
            builder.addTransition(
                    ONE,
                    action,
                    action.equals(secondAction)
                            ? ZERO : ONE);
        }
        return builder.build();
    }

    private static SafetyTester<String> rejectingTester(
            String action) {
        return SafetyTester.<String>builder()
                .initialState(OK)
                .addErrorState(ERROR)
                .addAction(action)
                .addTransition(OK, action, ERROR)
                .addTransition(ERROR, action, ERROR)
                .build();
    }

    private static ResidualLanguage<String> rejectingResidual(
            Set<String> commonAlphabet,
            String rejectedAction) {
        TableResidualLanguage.Builder<String> builder =
                TableResidualLanguage.<String>builder()
                        .initialState(OK)
                        .addErrorState(ERROR)
                        .addActions(commonAlphabet);
        for (String action : commonAlphabet) {
            builder.addTransition(
                    OK,
                    action,
                    action.equals(rejectedAction)
                            ? ERROR : OK);
            builder.addTransition(
                    ERROR, action, ERROR);
        }
        return builder.build();
    }

    private static PhysicalState<String> uniformPhysicalState(
            int componentCount,
            boolean newVersion,
            String localState) {
        List<TaggedState<String>> states =
                new ArrayList<TaggedState<String>>();
        for (int component = 0;
                component < componentCount;
                component++) {
            states.add(
                    newVersion
                            ? TaggedState.newState(localState)
                            : TaggedState.oldState(localState));
        }
        return PhysicalState.of(states);
    }

    private static void addPrecedence(
            FineGrainedUpdateProblem.Builder<String, String> builder,
            Set<String> seen,
            String before,
            String after) {
        String key = before + "\u0000" + after;
        if (seen.add(key)) {
            builder.addPrecedence(before, after);
        }
    }

    private static String canonicalDescriptor(
            Topology topology,
            int componentCount,
            long masterSeed,
            UProfile profile,
            Mutation mutation,
            int mutatedComponent,
            List<Edge> edges) {
        StringBuilder descriptor = new StringBuilder();
        descriptor.append(GENERATOR_VERSION)
                .append('\n')
                .append("topology=").append(topology.id())
                .append('\n')
                .append("n=").append(componentCount)
                .append('\n')
                .append("seed=").append(masterSeed)
                .append('\n')
                .append("profile=").append(profile.id())
                .append('\n')
                .append("mutation=").append(mutation.id())
                .append('\n')
                .append("mutated_component=")
                .append(mutatedComponent)
                .append('\n');
        for (int component = 0;
                component < componentCount;
                component++) {
            descriptor.append("node=")
                    .append(component)
                    .append(",distractors=")
                    .append(
                            1 + boundedHash(
                                    masterSeed,
                                    "distractors-" + component,
                                    3))
                    .append(",relational=")
                    .append(
                            boundedHash(
                                    masterSeed,
                                    "relational-transfer-"
                                            + component,
                                    3) == 0)
                    .append('\n');
        }
        for (Edge edge : edges) {
            descriptor.append("edge=")
                    .append(edge.anchor)
                    .append("->")
                    .append(edge.partner)
                    .append('\n');
        }
        return descriptor.toString();
    }

    static int boundedHash(
            long masterSeed,
            String factor,
            int bound) {
        if (bound <= 0) {
            throw new IllegalArgumentException(
                    "hash bound must be positive");
        }
        byte[] digest = sha256(
                GENERATOR_VERSION
                        + "|"
                        + masterSeed
                        + "|"
                        + factor);
        long value = 0L;
        for (int index = 0; index < 8; index++) {
            value = (value << 8)
                    | (digest[index] & 0xffL);
        }
        return (int) Long.remainderUnsigned(value, bound);
    }

    static String sha256Hex(String value) {
        byte[] digest = sha256(value);
        StringBuilder result =
                new StringBuilder(digest.length * 2);
        for (byte item : digest) {
            result.append(
                    String.format(
                            Locale.ROOT, "%02x", item & 0xff));
        }
        return result.toString();
    }

    private static byte[] sha256(String value) {
        try {
            return MessageDigest.getInstance("SHA-256")
                    .digest(value.getBytes(StandardCharsets.UTF_8));
        } catch (NoSuchAlgorithmException impossible) {
            throw new IllegalStateException(
                    "JVM does not provide SHA-256", impossible);
        }
    }

    private static String privateAction(
            String stem,
            int component) {
        return stem + "_" + component;
    }

    private static String reconfigureAction(int component) {
        return "reconfigure_" + component;
    }

    private static String oldRequirementId(int edge) {
        return "old_req_" + edge;
    }

    private static String newRequirementId(int edge) {
        return "new_req_" + edge;
    }

    private static String updateRequirementId(int edge) {
        return "update_req_" + edge;
    }

    private static String stopAction(int edge) {
        return "stop_old_" + edge;
    }

    private static String startAction(int edge) {
        return "start_new_" + edge;
    }

    private static String uncontrollableFirst(int component) {
        return "u_first_" + component;
    }

    private static String uncontrollableSecond(int component) {
        return "u_second_" + component;
    }

    private static String rejectAction(int component) {
        return "u_reject_" + component;
    }

    private static String livelockAction(int component) {
        return "u_livelock_" + component;
    }

    private static String edgeAction(Edge edge) {
        int minimum = Math.min(edge.anchor, edge.partner);
        int maximum = Math.max(edge.anchor, edge.partner);
        return "transfer_" + minimum + "_" + maximum;
    }

    private static <E> E parseEnum(
            E[] values,
            String text,
            String label) {
        if (text == null) {
            throw new IllegalArgumentException(
                    label + " must not be null");
        }
        String normalized = text.trim().toLowerCase(Locale.ROOT);
        for (E value : values) {
            String id;
            if (value instanceof Topology) {
                id = ((Topology) value).id();
            } else if (value instanceof UProfile) {
                id = ((UProfile) value).id();
            } else {
                id = ((Mutation) value).id();
            }
            if (id.equals(normalized)) {
                return value;
            }
        }
        throw new IllegalArgumentException(
                "Unknown " + label + ": " + text);
    }

    private static final class ComponentBuild {
        private final VersionedComponent<String> component;
        private final Set<String> normalActions;
        private final Set<String> controllableNormalActions;
        private final long transferEdges;

        private ComponentBuild(
                VersionedComponent<String> component,
                Set<String> normalActions,
                Set<String> controllableNormalActions,
                long transferEdges) {
            this.component = component;
            this.normalActions = normalActions;
            this.controllableNormalActions =
                    controllableNormalActions;
            this.transferEdges = transferEdges;
        }
    }

    private static final class EndpointBundle {
        private final FiniteLts<PhysicalState<String>> oldClosedLoop;
        private final FiniteLts<PhysicalState<String>> newClosedLoop;

        private EndpointBundle(
                FiniteLts<PhysicalState<String>> oldClosedLoop,
                FiniteLts<PhysicalState<String>> newClosedLoop) {
            this.oldClosedLoop = oldClosedLoop;
            this.newClosedLoop = newClosedLoop;
        }
    }

    private static final class UnorientedEdge {
        private final int minimum;
        private final int maximum;

        private UnorientedEdge(int left, int right) {
            this.minimum = Math.min(left, right);
            this.maximum = Math.max(left, right);
        }
    }

    private static final class Edge {
        private final int anchor;
        private final int partner;

        private Edge(int anchor, int partner) {
            this.anchor = anchor;
            this.partner = partner;
        }

        private boolean incident(int component) {
            return anchor == component || partner == component;
        }
    }

    public static final class GeneratedProblem {
        private final FineGrainedUpdateProblem<String, String> problem;
        private final FiniteLts<PhysicalState<String>> oldClosedLoop;
        private final FiniteLts<PhysicalState<String>> newClosedLoop;
        private final Map<String, String> initialRequirementStates;
        private final Map<PhysicalState<String>,
                GoalSignature<String, String>> goalByEndpointState;
        private final String inputId;
        private final String modelHash;
        private final Topology topology;
        private final int componentCount;
        private final long masterSeed;
        private final UProfile profile;
        private final Mutation mutation;
        private final int topologyEdges;
        private final int oldRequirementCount;
        private final int newRequirementCount;
        private final int updateRequirementCount;
        private final int normalActionCount;
        private final int controllableNormalActionCount;
        private final int uncontrollableNormalActionCount;
        private final int updateActionCount;
        private final int precedenceEdgeCount;
        private final long transferEdgeCount;
        private final int mutatedComponent;

        private GeneratedProblem(
                FineGrainedUpdateProblem<String, String> problem,
                FiniteLts<PhysicalState<String>> oldClosedLoop,
                FiniteLts<PhysicalState<String>> newClosedLoop,
                Map<String, String> initialRequirementStates,
                Map<PhysicalState<String>,
                        GoalSignature<String, String>> goalByEndpointState,
                String inputId,
                String modelHash,
                Topology topology,
                int componentCount,
                long masterSeed,
                UProfile profile,
                Mutation mutation,
                int topologyEdges,
                int oldRequirementCount,
                int newRequirementCount,
                int updateRequirementCount,
                int normalActionCount,
                int controllableNormalActionCount,
                int uncontrollableNormalActionCount,
                int updateActionCount,
                int precedenceEdgeCount,
                long transferEdgeCount,
                int mutatedComponent) {
            this.problem = problem;
            this.oldClosedLoop = oldClosedLoop;
            this.newClosedLoop = newClosedLoop;
            this.initialRequirementStates =
                    Collections.unmodifiableMap(
                            new LinkedHashMap<String, String>(
                                    initialRequirementStates));
            this.goalByEndpointState =
                    Collections.unmodifiableMap(
                            new LinkedHashMap<PhysicalState<String>,
                                    GoalSignature<String, String>>(
                                            goalByEndpointState));
            this.inputId = inputId;
            this.modelHash = modelHash;
            this.topology = topology;
            this.componentCount = componentCount;
            this.masterSeed = masterSeed;
            this.profile = profile;
            this.mutation = mutation;
            this.topologyEdges = topologyEdges;
            this.oldRequirementCount = oldRequirementCount;
            this.newRequirementCount = newRequirementCount;
            this.updateRequirementCount =
                    updateRequirementCount;
            this.normalActionCount = normalActionCount;
            this.controllableNormalActionCount =
                    controllableNormalActionCount;
            this.uncontrollableNormalActionCount =
                    uncontrollableNormalActionCount;
            this.updateActionCount = updateActionCount;
            this.precedenceEdgeCount = precedenceEdgeCount;
            this.transferEdgeCount = transferEdgeCount;
            this.mutatedComponent = mutatedComponent;
        }

        public FineGrainedUpdateProblem<String, String> problem() {
            return problem;
        }

        public FiniteLts<PhysicalState<String>> oldClosedLoop() {
            return oldClosedLoop;
        }

        public FiniteLts<PhysicalState<String>> newClosedLoop() {
            return newClosedLoop;
        }

        public InitialSnapshot<String, String> initialProjection(
                PhysicalState<String> state) {
            if (!oldClosedLoop.reachableStates().contains(state)) {
                throw new IllegalArgumentException(
                        "unknown old endpoint state: " + state);
            }
            return new InitialSnapshot<String, String>(
                    state, initialRequirementStates);
        }

        public GoalSignature<String, String> goalProjection(
                PhysicalState<String> state) {
            GoalSignature<String, String> result =
                    goalByEndpointState.get(state);
            if (result == null) {
                throw new IllegalArgumentException(
                        "unknown new endpoint state: " + state);
            }
            return result;
        }

        public String inputId() {
            return inputId;
        }

        public String modelHash() {
            return modelHash;
        }

        public Topology topology() {
            return topology;
        }

        public int componentCount() {
            return componentCount;
        }

        public long masterSeed() {
            return masterSeed;
        }

        public UProfile profile() {
            return profile;
        }

        public Mutation mutation() {
            return mutation;
        }

        public boolean expectedWinning() {
            return mutation.expectedWinning();
        }

        public int topologyEdges() {
            return topologyEdges;
        }

        public int oldRequirementCount() {
            return oldRequirementCount;
        }

        public int newRequirementCount() {
            return newRequirementCount;
        }

        public int updateRequirementCount() {
            return updateRequirementCount;
        }

        public int normalActionCount() {
            return normalActionCount;
        }

        public int controllableNormalActionCount() {
            return controllableNormalActionCount;
        }

        public int uncontrollableNormalActionCount() {
            return uncontrollableNormalActionCount;
        }

        public int updateActionCount() {
            return updateActionCount;
        }

        public int precedenceEdgeCount() {
            return precedenceEdgeCount;
        }

        public long transferEdgeCount() {
            return transferEdgeCount;
        }

        public int mutatedComponent() {
            return mutatedComponent;
        }
    }
}
