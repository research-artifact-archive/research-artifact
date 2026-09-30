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

/** Independent structural checker for the complete atomic Link quotient. */
public final class LinkedOtfDucsControllerChecker<ZO, S, M, ZN> {

    public VerificationReport verify(
            LinkedOtfDucsController<ZO, S, M, ZN> controller,
            FiniteLts<ZO> oldClosedLoop,
            FiniteLts<ZN> newClosedLoop,
            FineGrainedUpdateProblem<S, M> problem,
            OtfDucsResult<CanonicalUpdateConfiguration<S, M>, String,
                    GoalSignature<S, M>> result,
            Function<? super ZO, ? extends InitialSnapshot<S, M>> initialProjection,
            Function<? super ZN, ? extends GoalSignature<S, M>> goalProjection) {
        List<String> violations = new ArrayList<String>();
        if (controller == null || oldClosedLoop == null || newClosedLoop == null
                || problem == null || result == null || initialProjection == null
                || goalProjection == null) {
            violations.add("link checker input contains null");
            return new VerificationReport(violations);
        }
        if (!result.isWinning()) {
            violations.add("linked controller is backed by a losing result");
            return new VerificationReport(violations);
        }

        FineGrainedSuccessorOracle<S, M> game = FineGrainedOtfDucs.game(problem);
        OtfDucsCertificateChecker.VerificationReport certificateReport =
                new OtfDucsCertificateChecker<CanonicalUpdateConfiguration<S, M>, String,
                        GoalSignature<S, M>>(game).verify(result);
        for (String violation : certificateReport.violations()) {
            violations.add("mid certificate: " + violation);
        }

        try {
            checkStructure(controller, oldClosedLoop, newClosedLoop, problem,
                    result.winningCertificate(), initialProjection, goalProjection,
                    game, violations);
        } catch (RuntimeException error) {
            violations.add("link validation failed: " + error.getMessage());
        }
        return new VerificationReport(violations);
    }

    private void checkStructure(
            LinkedOtfDucsController<ZO, S, M, ZN> controller,
            FiniteLts<ZO> oldClosedLoop,
            FiniteLts<ZN> newClosedLoop,
            FineGrainedUpdateProblem<S, M> problem,
            OtfDucsResult.WinningCertificate<CanonicalUpdateConfiguration<S, M>, String,
                    GoalSignature<S, M>> certificate,
            Function<? super ZO, ? extends InitialSnapshot<S, M>> initialProjection,
            Function<? super ZN, ? extends GoalSignature<S, M>> goalProjection,
            FineGrainedSuccessorOracle<S, M> game,
            List<String> violations) {
        if (!problem.normalActions().containsAll(oldClosedLoop.alphabet())
                || !problem.normalActions().containsAll(newClosedLoop.alphabet())) {
            violations.add("endpoint closed-loop alphabets contain non-normal actions");
        }
        Map<ZO, CanonicalUpdateConfiguration<S, M>> roots = new LinkedHashMap<>();
        Map<ZO, InitialSnapshot<S, M>> oldProjectionByState = new LinkedHashMap<>();
        Set<CanonicalUpdateConfiguration<S, M>> coveredRoots = new LinkedHashSet<>();
        for (ZO oldState : oldClosedLoop.reachableStates()) {
            if (oldClosedLoop.enabledActions(oldState).isEmpty()) {
                violations.add("old closed loop is deadlocked at " + oldState);
            }
            InitialSnapshot<S, M> snapshot = Objects.requireNonNull(
                    initialProjection.apply(oldState), "initial projection for " + oldState);
            oldProjectionByState.put(oldState, snapshot);
            CanonicalUpdateConfiguration<S, M> root =
                    LinkedOtfDucsController.resolveInitial(problem, snapshot);
            roots.put(oldState, root);
            coveredRoots.add(root);
        }
        if (!coveredRoots.equals(new LinkedHashSet<CanonicalUpdateConfiguration<S, M>>(
                problem.initialConfigurations()))) {
            violations.add("hotSwapIn projection does not cover exactly all Q0 roots");
        }

        Map<String, ZN> postById = new LinkedHashMap<>();
        Map<ZN, GoalSignature<S, M>> newProjectionByState = new LinkedHashMap<>();
        Set<GoalSignature<S, M>> coveredGoals = new LinkedHashSet<>();
        Set<GoalSignature<S, M>> declaredGoals =
                new LinkedHashSet<GoalSignature<S, M>>(
                        problem.goalSignatures());
        for (ZN newState : newClosedLoop.reachableStates()) {
            if (newClosedLoop.enabledActions(newState).isEmpty()) {
                violations.add("new closed loop is deadlocked at " + newState);
            }
            GoalSignature<S, M> signature = Objects.requireNonNull(
                    goalProjection.apply(newState), "goal projection for " + newState);
            newProjectionByState.put(newState, signature);
            if (postById.put(signature.endpointId(), newState) != null) {
                violations.add("duplicate new endpoint id: " + signature.endpointId());
            }
            if (declaredGoals.contains(signature)) {
                coveredGoals.add(signature);
            }
        }
        if (!coveredGoals.equals(declaredGoals)) {
            violations.add(
                    "post projection does not cover every declared loadable Goal signature");
        }
        checkEndpointProjectionTransitions(
                oldClosedLoop, newClosedLoop, problem,
                oldProjectionByState, newProjectionByState, violations);

        Map<CanonicalUpdateConfiguration<S, M>, ZN> quotient = new LinkedHashMap<>();
        for (Map.Entry<CanonicalUpdateConfiguration<S, M>, GoalSignature<S, M>> entry
                : certificate.goalMatches().entrySet()) {
            ZN endpoint = postById.get(entry.getValue().endpointId());
            if (endpoint == null) {
                violations.add("Goal quotient has no reachable endpoint: "
                        + entry.getValue().endpointId());
            } else {
                quotient.put(entry.getKey(), endpoint);
            }
        }
        if (!quotient.equals(controller.quotientTargets())) {
            violations.add("Goal quotient target map differs from fixed endpoint matching");
        }

        Set<LinkedOtfDucsController.State<ZO, S, M, ZN>> expectedStates =
                new LinkedHashSet<>();
        for (ZO state : oldClosedLoop.reachableStates()) {
            expectedStates.add(LinkedOtfDucsController.State.<ZO, S, M, ZN>pre(state));
        }
        for (ZN state : newClosedLoop.reachableStates()) {
            expectedStates.add(LinkedOtfDucsController.State.<ZO, S, M, ZN>post(state));
        }
        for (CanonicalUpdateConfiguration<S, M> state : certificate.ranks().keySet()) {
            if (!game.isGoal(state)) {
                expectedStates.add(LinkedOtfDucsController.State.<ZO, S, M, ZN>mid(state));
            }
        }
        if (!expectedStates.equals(controller.lts().states())) {
            violations.add("linked state set is not PRE union non-Goal MID union POST");
        }

        LinkedOtfDucsController.State<ZO, S, M, ZN> expectedInitial =
                LinkedOtfDucsController.State.<ZO, S, M, ZN>pre(
                        oldClosedLoop.initialState());
        if (!expectedInitial.equals(controller.lts().initialState())) {
            violations.add("linked initial state is not the old closed-loop initial state");
        }

        Set<String> expectedAlphabet = new LinkedHashSet<String>(problem.commonAlphabet());
        expectedAlphabet.add(problem.hotSwapInAction());
        if (!expectedAlphabet.equals(controller.lts().alphabet())) {
            violations.add("linked action alphabet differs from common alphabet plus hotSwapIn");
        }
        if (controller.lts().alphabet().contains(problem.hotSwapOutAction())) {
            violations.add("hotSwapOut was materialized as an event instead of an atomic quotient");
        }

        Set<String> expectedControllable = new LinkedHashSet<String>(
                problem.controllableActions());
        expectedControllable.add(problem.hotSwapInAction());
        if (!expectedControllable.equals(controller.controllableActions())) {
            violations.add("linked controllability classification is incorrect");
        }
        if (!problem.hotSwapInAction().equals(controller.hotSwapInAction())
                || !problem.hotSwapOutAction().equals(controller.hotSwapOutBoundaryName())) {
            violations.add("link boundary metadata is incorrect");
        }

        for (LinkedOtfDucsController.State<ZO, S, M, ZN> state : expectedStates) {
            Map<String, Set<LinkedOtfDucsController.State<ZO, S, M, ZN>>> expected =
                    expectedTransitions(state, oldClosedLoop, newClosedLoop, problem,
                            certificate, roots, quotient, game);
            Map<String, Set<LinkedOtfDucsController.State<ZO, S, M, ZN>>> actual =
                    controller.lts().transitions().get(state);
            if (!expected.equals(actual)) {
                violations.add("linked transitions differ at " + state);
            }
            if (actual == null || actual.isEmpty()) {
                violations.add("linked controller is deadlocked at " + state);
            }
        }
    }

    /**
     * Checks that the supplied endpoint projections are transition-preserving
     * closed-loop projections, not merely arbitrary per-state labels.
     */
    private void checkEndpointProjectionTransitions(
            FiniteLts<ZO> oldClosedLoop,
            FiniteLts<ZN> newClosedLoop,
            FineGrainedUpdateProblem<S, M> problem,
            Map<ZO, InitialSnapshot<S, M>> oldProjection,
            Map<ZN, GoalSignature<S, M>> newProjection,
            List<String> violations) {
        for (ZO source : oldClosedLoop.reachableStates()) {
            InitialSnapshot<S, M> projectedSource = oldProjection.get(source);
            for (String action : problem.normalActions()) {
                Set<ProjectionKey<S, M>> expected = projectedEndpointPost(
                        problem, projectedSource.physicalState(),
                        projectedSource.oldRequirementStates(),
                        problem.oldRequirementIds(), action);
                Set<ProjectionKey<S, M>> actual = new LinkedHashSet<>();
                for (ZO target : oldClosedLoop.successors(source, action)) {
                    InitialSnapshot<S, M> projectedTarget = oldProjection.get(target);
                    if (projectedTarget == null) {
                        violations.add("old endpoint transition leaves its reachable projection: "
                                + source + " / " + action);
                        continue;
                    }
                    actual.add(new ProjectionKey<S, M>(
                            projectedTarget.physicalState(),
                            projectedTarget.oldRequirementStates()));
                }
                checkEndpointBucket(
                        "old", source, action, expected, actual,
                        problem.controllableNormalActions().contains(action), violations);
            }
        }

        for (ZN source : newClosedLoop.reachableStates()) {
            GoalSignature<S, M> projectedSource = newProjection.get(source);
            for (String action : problem.normalActions()) {
                Set<ProjectionKey<S, M>> expected = projectedEndpointPost(
                        problem, projectedSource.physicalState(),
                        projectedSource.newRequirementStates(),
                        problem.newRequirementIds(), action);
                Set<ProjectionKey<S, M>> actual = new LinkedHashSet<>();
                for (ZN target : newClosedLoop.successors(source, action)) {
                    GoalSignature<S, M> projectedTarget = newProjection.get(target);
                    if (projectedTarget == null) {
                        violations.add("new endpoint transition leaves its reachable projection: "
                                + source + " / " + action);
                        continue;
                    }
                    actual.add(new ProjectionKey<S, M>(
                            projectedTarget.physicalState(),
                            projectedTarget.newRequirementStates()));
                }
                checkEndpointBucket(
                        "new", source, action, expected, actual,
                        problem.controllableNormalActions().contains(action), violations);
            }
        }
    }

    private void checkEndpointBucket(
            String endpoint,
            Object source,
            String action,
            Set<ProjectionKey<S, M>> expected,
            Set<ProjectionKey<S, M>> actual,
            boolean controllable,
            List<String> violations) {
        if (!actual.isEmpty() && !actual.equals(expected)) {
            violations.add(endpoint + " endpoint does not preserve every outcome at "
                    + source + " / " + action);
        } else if (!controllable && !expected.isEmpty() && actual.isEmpty()) {
            violations.add(endpoint + " endpoint disables uncontrollable action at "
                    + source + " / " + action);
        }
    }

    private Set<ProjectionKey<S, M>> projectedEndpointPost(
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
            testerOutcome.put(id, requirement.tester().stepOrStutter(source, action));
        }
        Set<ProjectionKey<S, M>> result = new LinkedHashSet<>();
        for (PhysicalState<S> outcome : physicalOutcomes) {
            result.add(new ProjectionKey<S, M>(outcome, testerOutcome));
        }
        return result;
    }

    private Set<PhysicalState<S>> physicalPost(
            FineGrainedUpdateProblem<S, M> problem,
            PhysicalState<S> physical,
            String action) {
        List<List<TaggedState<S>>> localOutcomes = new ArrayList<>();
        boolean participant = false;
        for (int index = 0; index < physical.size(); index++) {
            TaggedState<S> tagged = physical.component(index);
            VersionedComponent<S> component = problem.components().get(index);
            FiniteLts<S> active = tagged.isOld() ? component.oldLts() : component.newLts();
            List<TaggedState<S>> choices = new ArrayList<>();
            /*
             * An augmented component can contain observer-only transitions.
             * They must track an event emitted by another physical component,
             * but must not make that event enabled by the environment here.
             */
            if (component.environmentHasAction(tagged.version(), action)) {
                participant = true;
            }
            if (active.hasAction(action)) {
                Set<S> successors = active.successors(tagged.state(), action);
                if (successors.isEmpty()) return Collections.emptySet();
                for (S successor : successors) {
                    choices.add(TaggedState.of(tagged.version(), successor));
                }
            } else {
                choices.add(tagged);
            }
            localOutcomes.add(choices);
        }
        if (!participant) return Collections.emptySet();
        Set<PhysicalState<S>> result = new LinkedHashSet<>();
        cartesianPhysical(localOutcomes, 0, new ArrayList<TaggedState<S>>(), result);
        return result;
    }

    private void cartesianPhysical(
            List<List<TaggedState<S>>> choices,
            int index,
            List<TaggedState<S>> current,
            Set<PhysicalState<S>> output) {
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

    private Map<String, Set<LinkedOtfDucsController.State<ZO, S, M, ZN>>>
            expectedTransitions(
                    LinkedOtfDucsController.State<ZO, S, M, ZN> state,
                    FiniteLts<ZO> oldClosedLoop,
                    FiniteLts<ZN> newClosedLoop,
                    FineGrainedUpdateProblem<S, M> problem,
                    OtfDucsResult.WinningCertificate<CanonicalUpdateConfiguration<S, M>, String,
                            GoalSignature<S, M>> certificate,
                    Map<ZO, CanonicalUpdateConfiguration<S, M>> roots,
                    Map<CanonicalUpdateConfiguration<S, M>, ZN> quotient,
                    FineGrainedSuccessorOracle<S, M> game) {
        Map<String, Set<LinkedOtfDucsController.State<ZO, S, M, ZN>>> result =
                new LinkedHashMap<>();
        if (state.region() == LinkedOtfDucsController.Region.PRE) {
            ZO raw = state.pre().get();
            for (String action : oldClosedLoop.enabledActions(raw)) {
                for (ZO target : oldClosedLoop.successors(raw, action)) {
                    add(result, action,
                            LinkedOtfDucsController.State.<ZO, S, M, ZN>pre(target));
                }
            }
            add(result, problem.hotSwapInAction(), linkedTarget(roots.get(raw), quotient, game));
        } else if (state.region() == LinkedOtfDucsController.Region.MID) {
            CanonicalUpdateConfiguration<S, M> raw = state.mid().get();
            Map<String, Set<CanonicalUpdateConfiguration<S, M>>> actions =
                    certificate.strategy().get(raw);
            if (actions != null) {
                for (Map.Entry<String, Set<CanonicalUpdateConfiguration<S, M>>> entry
                        : actions.entrySet()) {
                    for (CanonicalUpdateConfiguration<S, M> target : entry.getValue()) {
                        add(result, entry.getKey(), linkedTarget(target, quotient, game));
                    }
                }
            }
        } else {
            ZN raw = state.post().get();
            for (String action : newClosedLoop.enabledActions(raw)) {
                for (ZN target : newClosedLoop.successors(raw, action)) {
                    add(result, action,
                            LinkedOtfDucsController.State.<ZO, S, M, ZN>post(target));
                }
            }
        }
        return result;
    }

    private LinkedOtfDucsController.State<ZO, S, M, ZN> linkedTarget(
            CanonicalUpdateConfiguration<S, M> target,
            Map<CanonicalUpdateConfiguration<S, M>, ZN> quotient,
            FineGrainedSuccessorOracle<S, M> game) {
        if (game.isGoal(target)) {
            ZN endpoint = quotient.get(target);
            if (endpoint == null) {
                throw new IllegalArgumentException("unresolved Goal quotient target");
            }
            return LinkedOtfDucsController.State.<ZO, S, M, ZN>post(endpoint);
        }
        return LinkedOtfDucsController.State.<ZO, S, M, ZN>mid(target);
    }

    private static <T> void add(Map<String, Set<T>> transitions, String action, T target) {
        Set<T> outcomes = transitions.get(action);
        if (outcomes == null) {
            outcomes = new LinkedHashSet<T>();
            transitions.put(action, outcomes);
        }
        outcomes.add(target);
    }

    private static final class ProjectionKey<S, M> {
        private final PhysicalState<S> physical;
        private final Map<String, M> testerStates;

        private ProjectionKey(PhysicalState<S> physical, Map<String, M> testerStates) {
            this.physical = Objects.requireNonNull(physical, "physical projection");
            this.testerStates = Collections.unmodifiableMap(
                    new LinkedHashMap<String, M>(testerStates));
        }

        @Override
        public boolean equals(Object other) {
            if (this == other) return true;
            if (!(other instanceof ProjectionKey)) return false;
            ProjectionKey<?, ?> that = (ProjectionKey<?, ?>) other;
            return physical.equals(that.physical)
                    && testerStates.equals(that.testerStates);
        }

        @Override
        public int hashCode() {
            return Objects.hash(physical, testerStates);
        }
    }

    public static final class VerificationReport {
        private final List<String> violations;

        private VerificationReport(List<String> violations) {
            this.violations = Collections.unmodifiableList(
                    new ArrayList<String>(violations));
        }

        public boolean isValid() {
            return violations.isEmpty();
        }

        public List<String> violations() {
            return violations;
        }

        public void throwIfInvalid() {
            if (!isValid()) {
                throw new IllegalStateException(
                        "Invalid linked OTF-DUCS controller: " + violations);
            }
        }
    }
}
