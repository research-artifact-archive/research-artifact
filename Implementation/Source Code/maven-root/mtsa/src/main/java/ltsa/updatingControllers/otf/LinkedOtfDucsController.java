package ltsa.updatingControllers.otf;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.function.Function;

/**
 * Materialized pre/mid/post controller produced by the paper's atomic Link
 * quotient. Goal configurations are represented directly by their POST
 * endpoint state, so there is deliberately no {@code hotSwapOut} transition.
 */
public final class LinkedOtfDucsController<ZO, S, M, ZN> {

    public enum Region { PRE, MID, POST }

    /** Region-tagged disjoint-union state used by the linked finite LTS. */
    public static final class State<ZO, S, M, ZN> {
        private final Region region;
        private final ZO pre;
        private final CanonicalUpdateConfiguration<S, M> mid;
        private final ZN post;

        private State(
                Region region,
                ZO pre,
                CanonicalUpdateConfiguration<S, M> mid,
                ZN post) {
            this.region = Objects.requireNonNull(region, "region");
            this.pre = pre;
            this.mid = mid;
            this.post = post;
        }

        public static <ZO, S, M, ZN> State<ZO, S, M, ZN> pre(ZO state) {
            return new State<ZO, S, M, ZN>(
                    Region.PRE, Objects.requireNonNull(state, "pre state"), null, null);
        }

        public static <ZO, S, M, ZN> State<ZO, S, M, ZN> mid(
                CanonicalUpdateConfiguration<S, M> state) {
            return new State<ZO, S, M, ZN>(
                    Region.MID, null, Objects.requireNonNull(state, "mid state"), null);
        }

        public static <ZO, S, M, ZN> State<ZO, S, M, ZN> post(ZN state) {
            return new State<ZO, S, M, ZN>(
                    Region.POST, null, null, Objects.requireNonNull(state, "post state"));
        }

        public Region region() {
            return region;
        }

        public Optional<ZO> pre() {
            return Optional.ofNullable(pre);
        }

        public Optional<CanonicalUpdateConfiguration<S, M>> mid() {
            return Optional.ofNullable(mid);
        }

        public Optional<ZN> post() {
            return Optional.ofNullable(post);
        }

        @Override
        public boolean equals(Object other) {
            if (this == other) return true;
            if (!(other instanceof State)) return false;
            State<?, ?, ?, ?> that = (State<?, ?, ?, ?>) other;
            return region == that.region
                    && Objects.equals(pre, that.pre)
                    && Objects.equals(mid, that.mid)
                    && Objects.equals(post, that.post);
        }

        @Override
        public int hashCode() {
            return Objects.hash(region, pre, mid, post);
        }

        @Override
        public String toString() {
            if (region == Region.PRE) return "PRE(" + pre + ")";
            if (region == Region.MID) return "MID(" + mid + ")";
            return "POST(" + post + ")";
        }
    }

    private final FiniteLts<State<ZO, S, M, ZN>> lts;
    private final Set<String> controllableActions;
    private final Map<CanonicalUpdateConfiguration<S, M>, ZN> quotientTargets;
    private final String hotSwapInAction;
    private final String hotSwapOutBoundaryName;

    LinkedOtfDucsController(
            FiniteLts<State<ZO, S, M, ZN>> lts,
            Set<String> controllableActions,
            Map<CanonicalUpdateConfiguration<S, M>, ZN> quotientTargets,
            String hotSwapInAction,
            String hotSwapOutBoundaryName) {
        this.lts = Objects.requireNonNull(lts, "lts");
        this.controllableActions = Collections.unmodifiableSet(
                new LinkedHashSet<String>(controllableActions));
        this.quotientTargets = Collections.unmodifiableMap(
                new LinkedHashMap<CanonicalUpdateConfiguration<S, M>, ZN>(quotientTargets));
        this.hotSwapInAction = Objects.requireNonNull(hotSwapInAction, "hotSwapInAction");
        this.hotSwapOutBoundaryName = Objects.requireNonNull(
                hotSwapOutBoundaryName, "hotSwapOutBoundaryName");
    }

    public static <ZO, S, M, ZN> LinkedOtfDucsController<ZO, S, M, ZN> link(
            FiniteLts<ZO> oldClosedLoop,
            FiniteLts<ZN> newClosedLoop,
            FineGrainedUpdateProblem<S, M> problem,
            OtfDucsResult<CanonicalUpdateConfiguration<S, M>, String,
                    GoalSignature<S, M>> result,
            Function<? super ZO, ? extends InitialSnapshot<S, M>> initialProjection,
            Function<? super ZN, ? extends GoalSignature<S, M>> goalProjection) {
        Objects.requireNonNull(oldClosedLoop, "oldClosedLoop");
        Objects.requireNonNull(newClosedLoop, "newClosedLoop");
        Objects.requireNonNull(problem, "problem");
        Objects.requireNonNull(result, "result");
        Objects.requireNonNull(initialProjection, "initialProjection");
        Objects.requireNonNull(goalProjection, "goalProjection");
        if (!result.isWinning()) {
            throw new IllegalArgumentException("A losing OTF-DUCS result cannot be linked");
        }

        FineGrainedSuccessorOracle<S, M> game = FineGrainedOtfDucs.game(problem);
        new OtfDucsCertificateChecker<CanonicalUpdateConfiguration<S, M>, String,
                GoalSignature<S, M>>(game).verify(result).throwIfInvalid();
        validateEndpointAlphabets(oldClosedLoop, newClosedLoop, problem);

        Map<ZO, CanonicalUpdateConfiguration<S, M>> rootsByOldState =
                projectOldRoots(oldClosedLoop, problem, initialProjection);
        Map<String, ZN> postByEndpointId =
                projectNewEndpoints(newClosedLoop, problem, goalProjection);
        Map<CanonicalUpdateConfiguration<S, M>, ZN> quotientTargets =
                resolveQuotientTargets(result.winningCertificate(), postByEndpointId);

        FiniteLts.Builder<State<ZO, S, M, ZN>> linked = FiniteLts.builder(
                State.<ZO, S, M, ZN>pre(oldClosedLoop.initialState()));
        linked.addActions(problem.commonAlphabet());
        linked.addAction(problem.hotSwapInAction());

        for (ZO state : oldClosedLoop.reachableStates()) {
            linked.addState(State.<ZO, S, M, ZN>pre(state));
        }
        for (ZN state : newClosedLoop.reachableStates()) {
            linked.addState(State.<ZO, S, M, ZN>post(state));
        }
        for (CanonicalUpdateConfiguration<S, M> state
                : result.winningCertificate().ranks().keySet()) {
            if (!game.isGoal(state)) {
                linked.addState(State.<ZO, S, M, ZN>mid(state));
            }
        }

        copyPreTransitions(oldClosedLoop, linked);
        for (Map.Entry<ZO, CanonicalUpdateConfiguration<S, M>> entry
                : rootsByOldState.entrySet()) {
            linked.addTransition(
                    State.<ZO, S, M, ZN>pre(entry.getKey()),
                    problem.hotSwapInAction(),
                    linkedTarget(entry.getValue(), game, quotientTargets));
        }
        copyMidTransitions(result.winningCertificate(), game, quotientTargets, linked);
        copyPostTransitions(newClosedLoop, linked);

        LinkedHashSet<String> controllable = new LinkedHashSet<String>(
                problem.controllableActions());
        controllable.add(problem.hotSwapInAction());
        LinkedOtfDucsController<ZO, S, M, ZN> controller =
                new LinkedOtfDucsController<ZO, S, M, ZN>(
                        linked.build(), controllable, quotientTargets,
                        problem.hotSwapInAction(), problem.hotSwapOutAction());

        new LinkedOtfDucsControllerChecker<ZO, S, M, ZN>().verify(
                controller, oldClosedLoop, newClosedLoop, problem, result,
                initialProjection, goalProjection).throwIfInvalid();
        return controller;
    }

    public FiniteLts<State<ZO, S, M, ZN>> lts() {
        return lts;
    }

    /** Exports the complete linked controller for MTSA visualization/composition. */
    public MtsaLtsExport<State<ZO, S, M, ZN>> toMtsa() {
        return lts.toMtsa();
    }

    public Set<String> controllableActions() {
        return controllableActions;
    }

    /** Goal configurations identified with their concrete post-endpoint state. */
    public Map<CanonicalUpdateConfiguration<S, M>, ZN> quotientTargets() {
        return quotientTargets;
    }

    public String hotSwapInAction() {
        return hotSwapInAction;
    }

    /** Metadata only: atomic quotienting creates no transition with this label. */
    public String hotSwapOutBoundaryName() {
        return hotSwapOutBoundaryName;
    }

    static <S, M> CanonicalUpdateConfiguration<S, M> resolveInitial(
            FineGrainedUpdateProblem<S, M> problem,
            InitialSnapshot<S, M> snapshot) {
        Objects.requireNonNull(snapshot, "initial snapshot projection");
        CanonicalUpdateConfiguration<S, M> match = null;
        for (CanonicalUpdateConfiguration<S, M> candidate : problem.initialConfigurations()) {
            if (!candidate.physicalState().equals(snapshot.physicalState())) continue;
            boolean equal = true;
            for (String id : problem.oldRequirementIds()) {
                if (!Objects.equals(candidate.activeTesterStates().get(id),
                        snapshot.oldRequirementStates().get(id))) {
                    equal = false;
                    break;
                }
            }
            if (equal && snapshot.oldRequirementStates().keySet()
                    .equals(problem.oldRequirementIds())) {
                if (match != null && !match.equals(candidate)) {
                    throw new IllegalArgumentException(
                            "Ambiguous old endpoint projection: " + snapshot.physicalState());
                }
                match = candidate;
            }
        }
        if (match == null) {
            throw new IllegalArgumentException(
                    "Reachable old endpoint is absent from Q0: " + snapshot.physicalState());
        }
        return match;
    }

    private static <ZO, S, M> Map<ZO, CanonicalUpdateConfiguration<S, M>> projectOldRoots(
            FiniteLts<ZO> oldClosedLoop,
            FineGrainedUpdateProblem<S, M> problem,
            Function<? super ZO, ? extends InitialSnapshot<S, M>> projection) {
        Map<ZO, CanonicalUpdateConfiguration<S, M>> result = new LinkedHashMap<>();
        Set<CanonicalUpdateConfiguration<S, M>> covered = new LinkedHashSet<>();
        for (ZO state : oldClosedLoop.reachableStates()) {
            CanonicalUpdateConfiguration<S, M> root = resolveInitial(
                    problem, Objects.requireNonNull(projection.apply(state),
                            "initial projection for " + state));
            result.put(state, root);
            covered.add(root);
        }
        if (!covered.equals(new LinkedHashSet<CanonicalUpdateConfiguration<S, M>>(
                problem.initialConfigurations()))) {
            throw new IllegalArgumentException(
                    "Old endpoint projection is not exactly all Q0 configurations");
        }
        return result;
    }

    private static <S, M, ZN> Map<String, ZN> projectNewEndpoints(
            FiniteLts<ZN> newClosedLoop,
            FineGrainedUpdateProblem<S, M> problem,
            Function<? super ZN, ? extends GoalSignature<S, M>> projection) {
        Map<String, ZN> byId = new LinkedHashMap<>();
        Set<GoalSignature<S, M>> covered = new LinkedHashSet<>();
        Set<GoalSignature<S, M>> declared =
                new LinkedHashSet<GoalSignature<S, M>>(
                        problem.goalSignatures());
        for (ZN state : newClosedLoop.reachableStates()) {
            GoalSignature<S, M> signature = Objects.requireNonNull(
                    projection.apply(state), "goal projection for " + state);
            if (byId.put(signature.endpointId(), state) != null) {
                throw new IllegalArgumentException(
                        "Duplicate reachable new endpoint id: " + signature.endpointId());
            }
            if (declared.contains(signature)) {
                covered.add(signature);
            }
        }
        if (!covered.equals(declared)) {
            throw new IllegalArgumentException(
                    "New endpoint projection does not cover every declared loadable Goal");
        }
        return byId;
    }

    private static <S, M, ZN> Map<CanonicalUpdateConfiguration<S, M>, ZN>
            resolveQuotientTargets(
                    OtfDucsResult.WinningCertificate<CanonicalUpdateConfiguration<S, M>, String,
                            GoalSignature<S, M>> certificate,
                    Map<String, ZN> postByEndpointId) {
        Map<CanonicalUpdateConfiguration<S, M>, ZN> result = new LinkedHashMap<>();
        for (Map.Entry<CanonicalUpdateConfiguration<S, M>, GoalSignature<S, M>> entry
                : certificate.goalMatches().entrySet()) {
            ZN endpoint = postByEndpointId.get(entry.getValue().endpointId());
            if (endpoint == null) {
                throw new IllegalArgumentException(
                        "Goal has no reachable post endpoint: " + entry.getValue().endpointId());
            }
            result.put(entry.getKey(), endpoint);
        }
        return result;
    }

    private static <ZO, S, M, ZN> State<ZO, S, M, ZN> linkedTarget(
            CanonicalUpdateConfiguration<S, M> target,
            FineGrainedSuccessorOracle<S, M> game,
            Map<CanonicalUpdateConfiguration<S, M>, ZN> quotientTargets) {
        if (!game.isGoal(target)) {
            return State.<ZO, S, M, ZN>mid(target);
        }
        ZN endpoint = quotientTargets.get(target);
        if (endpoint == null) {
            throw new IllegalArgumentException("Unresolved Goal quotient target: " + target);
        }
        return State.<ZO, S, M, ZN>post(endpoint);
    }

    private static <ZO, S, M, ZN> void copyPreTransitions(
            FiniteLts<ZO> source,
            FiniteLts.Builder<State<ZO, S, M, ZN>> target) {
        for (ZO state : source.reachableStates()) {
            for (String action : source.enabledActions(state)) {
                for (ZO outcome : source.successors(state, action)) {
                    target.addTransition(State.<ZO, S, M, ZN>pre(state), action,
                            State.<ZO, S, M, ZN>pre(outcome));
                }
            }
        }
    }

    private static <ZO, S, M, ZN> void copyMidTransitions(
            OtfDucsResult.WinningCertificate<CanonicalUpdateConfiguration<S, M>, String,
                    GoalSignature<S, M>> certificate,
            FineGrainedSuccessorOracle<S, M> game,
            Map<CanonicalUpdateConfiguration<S, M>, ZN> quotientTargets,
            FiniteLts.Builder<State<ZO, S, M, ZN>> target) {
        for (Map.Entry<CanonicalUpdateConfiguration<S, M>,
                Map<String, Set<CanonicalUpdateConfiguration<S, M>>>> stateEntry
                : certificate.strategy().entrySet()) {
            State<ZO, S, M, ZN> source = State.<ZO, S, M, ZN>mid(stateEntry.getKey());
            for (Map.Entry<String, Set<CanonicalUpdateConfiguration<S, M>>> actionEntry
                    : stateEntry.getValue().entrySet()) {
                for (CanonicalUpdateConfiguration<S, M> outcome : actionEntry.getValue()) {
                    target.addTransition(source, actionEntry.getKey(),
                            linkedTarget(outcome, game, quotientTargets));
                }
            }
        }
    }

    private static <ZO, S, M, ZN> void copyPostTransitions(
            FiniteLts<ZN> source,
            FiniteLts.Builder<State<ZO, S, M, ZN>> target) {
        for (ZN state : source.reachableStates()) {
            for (String action : source.enabledActions(state)) {
                for (ZN outcome : source.successors(state, action)) {
                    target.addTransition(State.<ZO, S, M, ZN>post(state), action,
                            State.<ZO, S, M, ZN>post(outcome));
                }
            }
        }
    }

    private static <ZO, S, M, ZN> void validateEndpointAlphabets(
            FiniteLts<ZO> oldClosedLoop,
            FiniteLts<ZN> newClosedLoop,
            FineGrainedUpdateProblem<S, M> problem) {
        if (!problem.normalActions().containsAll(oldClosedLoop.alphabet())
                || !problem.normalActions().containsAll(newClosedLoop.alphabet())) {
            throw new IllegalArgumentException(
                    "Endpoint closed-loop alphabets must contain normal actions only");
        }
        for (ZO state : oldClosedLoop.reachableStates()) {
            if (oldClosedLoop.enabledActions(state).isEmpty()) {
                throw new IllegalArgumentException("Old closed loop is deadlocked at " + state);
            }
        }
        for (ZN state : newClosedLoop.reachableStates()) {
            if (newClosedLoop.enabledActions(state).isEmpty()) {
                throw new IllegalArgumentException("New closed loop is deadlocked at " + state);
            }
        }
    }
}
