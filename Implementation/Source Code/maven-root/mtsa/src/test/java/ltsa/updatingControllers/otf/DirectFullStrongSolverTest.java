package ltsa.updatingControllers.otf;

import org.testng.annotations.Test;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.Collections;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.Set;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

public class DirectFullStrongSolverTest {

    @Test
    public void exhaustivelyBuildsRepresentationBeforeSolving() {
        GraphGame game = new GraphGame("root")
                .goal("goal")
                .controllable("a-finish", "z-detour", "loop")
                .update("a-finish")
                .edge("root", "a-finish", "goal")
                .edge("root", "z-detour", "trap")
                .edge("trap", "loop", "trap");

        DirectFullStrongSolver<String, String, String> direct =
                new DirectFullStrongSolver<String, String, String>(game);
        OtfDucsResult<String, String, String> directResult =
                direct.synthesize();
        OtfDucsResult<String, String, String> otfResult =
                new OtfDucsSynthesizer<String, String, String>(
                        game, 0, 0).synthesize();

        assertTrue(directResult.isWinning());
        assertEquals(otfResult.isWinning(), directResult.isWinning());
        assertEquals(3L, direct.statistics().enumeratedStates());
        assertEquals(2L, direct.statistics().expandedStates());
        assertEquals(3L,
                direct.statistics().queriedStateActionPairs());
        assertEquals(3L, direct.statistics().enabledActionBuckets());
        assertEquals(3L, direct.statistics().materializedTransitions());
        assertTrue(directResult.statistics().queriedStateActionPairs()
                > otfResult.statistics().queriedStateActionPairs());
        assertEquals(Collections.singleton("a-finish"),
                directResult.winningCertificate().strategy()
                        .get("root").keySet());
        assertValid(game, directResult);
        assertValid(game, otfResult);
    }

    @Test
    public void solvesAllUncontrollableBucketsAndNondeterministicOutcomes() {
        GraphGame winning = new GraphGame("root")
                .goal("goal")
                .edge("root", "u-left", "left")
                .edge("root", "u-right", "right-a", "right-b")
                .edge("left", "u", "goal")
                .edge("right-a", "u", "goal")
                .edge("right-b", "u", "goal");
        GraphGame losing = new GraphGame("root")
                .goal("goal")
                .controllable("escape")
                .edge("root", "uncontrollable", "goal", "trap")
                .edge("root", "escape", "goal")
                .edge("trap", "loop", "trap");

        assertAgreesWithCompleteOtf(winning);
        assertAgreesWithCompleteOtf(losing);

        OtfDucsResult<String, String, String> result =
                new DirectFullStrongSolver<String, String, String>(
                        winning).synthesize();
        assertTrue(result.isWinning());
        assertEquals(
                new LinkedHashSet<String>(
                        Arrays.asList("u-left", "u-right")),
                result.winningCertificate().strategy()
                        .get("root").keySet());
    }

    @Test
    public void agreesWithCompleteOtfOnRandomImplicitGames() {
        Random random = new Random(2027072401L);
        for (int sample = 0; sample < 300; sample++) {
            int stateCount = 2 + random.nextInt(7);
            GraphGame game = new GraphGame("s0");
            for (int state = 0; state < stateCount; state++) {
                if (random.nextInt(5) == 0) {
                    game.goal("s" + state);
                }
                int actionCount = random.nextInt(5);
                for (int actionIndex = 0;
                        actionIndex < actionCount;
                        actionIndex++) {
                    boolean controllable = random.nextBoolean();
                    String action = (controllable ? "c" : "u")
                            + state + "_" + actionIndex;
                    if (controllable) {
                        game.controllable(action);
                        if (random.nextBoolean()) {
                            game.update(action);
                        }
                    }
                    int outcomeCount =
                            1 + random.nextInt(Math.min(3, stateCount));
                    Set<String> outcomes =
                            new LinkedHashSet<String>();
                    while (outcomes.size() < outcomeCount) {
                        outcomes.add(
                                "s" + random.nextInt(stateCount));
                    }
                    game.edge(
                            "s" + state,
                            action,
                            outcomes.toArray(
                                    new String[outcomes.size()]));
                }
            }

            OtfDucsResult<String, String, String> direct =
                    new DirectFullStrongSolver<String, String, String>(
                            game).synthesize();
            OtfDucsResult<String, String, String> otf =
                    new OtfDucsSynthesizer<String, String, String>(
                            game, 0, 0).synthesize();
            OtfDucsResult<String, String, String> genericLazy =
                    new GenericLazyStrongSolver<String, String, String>(
                            game).synthesize();
            assertEquals(
                    "decision mismatch in random graph " + sample,
                    otf.isWinning(), direct.isWinning());
            assertEquals(
                    "generic-lazy mismatch in random graph " + sample,
                    direct.isWinning(), genericLazy.isWinning());
            assertValid(game, direct);
            assertValid(game, otf);
            assertValid(game, genericLazy);
        }
    }

    @Test
    public void genericLazyIgnoresCandidateIterationOrder() {
        GraphGame forward = new GraphGame("root")
                .goal("goal")
                .controllable("finish", "detour", "loop")
                .edge("root", "finish", "goal")
                .edge("root", "detour", "trap")
                .edge("trap", "loop", "trap");
        GraphGame reverse = new GraphGame("root")
                .goal("goal")
                .controllable("finish", "detour", "loop")
                .edge("trap", "loop", "trap")
                .edge("root", "detour", "trap")
                .edge("root", "finish", "goal");

        OtfDucsResult<String, String, String> left =
                new GenericLazyStrongSolver<String, String, String>(
                        forward).synthesize();
        OtfDucsResult<String, String, String> right =
                new GenericLazyStrongSolver<String, String, String>(
                        reverse).synthesize();

        assertTrue(left.isWinning());
        assertEquals(left.isWinning(), right.isWinning());
        assertEquals(
                left.winningCertificate().strategy(),
                right.winningCertificate().strategy());
        assertEquals(
                left.statistics().queriedStateActionPairs(),
                right.statistics().queriedStateActionPairs());
        assertEquals(
                left.statistics().materializedTransitions(),
                right.statistics().materializedTransitions());
        assertEquals(
                left.statistics().fixedPointStateInspections(),
                right.statistics().fixedPointStateInspections());
        assertEquals(
                left.statistics().fixedPointComputations(),
                right.statistics().fixedPointComputations());
        assertValid(forward, left);
        assertValid(reverse, right);
    }

    @Test
    public void producesValidCertificateForRepresentativeFineGrainedGame() {
        FineGrainedUpdateProblem<String, String> problem =
                fineGrainedProblem(
                        3,
                        Collections.singleton("c0"),
                        transitionMap(
                                edge("n0", "c0", "n1"),
                                edge("n1", "u1", "n2")),
                        Collections.singleton("n0"));

        FineGrainedSuccessorOracle<String, String> directGame =
                FineGrainedOtfDucs.game(problem);
        DirectFullStrongSolver<
                CanonicalUpdateConfiguration<String, String>,
                String,
                GoalSignature<String, String>> direct =
                new DirectFullStrongSolver<
                        CanonicalUpdateConfiguration<String, String>,
                        String,
                        GoalSignature<String, String>>(directGame);
        OtfDucsResult<
                CanonicalUpdateConfiguration<String, String>,
                String,
                GoalSignature<String, String>> directResult =
                direct.synthesize();

        FineGrainedSuccessorOracle<String, String> otfGame =
                FineGrainedOtfDucs.game(problem);
        OtfDucsResult<
                CanonicalUpdateConfiguration<String, String>,
                String,
                GoalSignature<String, String>> otfResult =
                new OtfDucsSynthesizer<
                        CanonicalUpdateConfiguration<String, String>,
                        String,
                        GoalSignature<String, String>>(
                                otfGame, 0, 0).synthesize();

        assertTrue(directResult.isWinning());
        assertEquals(otfResult.isWinning(), directResult.isWinning());
        assertEquals(4L, direct.statistics().enumeratedStates());
        assertValid(directGame, directResult);
        assertValid(otfGame, otfResult);
    }

    @Test
    public void agreesOnRandomFineGrainedGames() {
        Random random = new Random(2027072402L);
        for (int sample = 0; sample < 100; sample++) {
            int newStateCount = 2 + random.nextInt(5);
            Map<String, List<Transition>> transitions =
                    new LinkedHashMap<String, List<Transition>>();
            Set<String> controllable = new LinkedHashSet<String>();
            for (int source = 0;
                    source < newStateCount;
                    source++) {
                int actionCount = random.nextInt(4);
                for (int actionIndex = 0;
                        actionIndex < actionCount;
                        actionIndex++) {
                    boolean isControllable = random.nextBoolean();
                    String action = (isControllable ? "c" : "u")
                            + source + "_" + actionIndex;
                    if (isControllable) {
                        controllable.add(action);
                    }
                    int outcomeCount = 1 + random.nextInt(
                            Math.min(3, newStateCount));
                    Set<String> targets =
                            new LinkedHashSet<String>();
                    while (targets.size() < outcomeCount) {
                        targets.add(
                                "n" + random.nextInt(newStateCount));
                    }
                    for (String target : targets) {
                        addTransition(
                                transitions,
                                new Transition(
                                        "n" + source,
                                        action,
                                        target));
                    }
                }
            }
            Set<String> transferTargets =
                    new LinkedHashSet<String>();
            int transferCount = 1 + random.nextInt(
                    Math.min(3, newStateCount));
            while (transferTargets.size() < transferCount) {
                transferTargets.add(
                        "n" + random.nextInt(newStateCount));
            }
            FineGrainedUpdateProblem<String, String> problem =
                    fineGrainedProblem(
                            newStateCount,
                            controllable,
                            transitions,
                            transferTargets);

            FineGrainedSuccessorOracle<String, String> directGame =
                    FineGrainedOtfDucs.game(problem);
            OtfDucsResult<
                    CanonicalUpdateConfiguration<String, String>,
                    String,
                    GoalSignature<String, String>> direct =
                    new DirectFullStrongSolver<
                            CanonicalUpdateConfiguration<String, String>,
                            String,
                            GoalSignature<String, String>>(
                                    directGame).synthesize();
            FineGrainedSuccessorOracle<String, String> otfGame =
                    FineGrainedOtfDucs.game(problem);
            OtfDucsResult<
                    CanonicalUpdateConfiguration<String, String>,
                    String,
                    GoalSignature<String, String>> otf =
                    new OtfDucsSynthesizer<
                            CanonicalUpdateConfiguration<String, String>,
                            String,
                            GoalSignature<String, String>>(
                                    otfGame, 0, 0).synthesize();
            FineGrainedSuccessorOracle<String, String> genericGame =
                    FineGrainedOtfDucs.game(problem);
            OtfDucsResult<
                    CanonicalUpdateConfiguration<String, String>,
                    String,
                    GoalSignature<String, String>> genericLazy =
                    new GenericLazyStrongSolver<
                            CanonicalUpdateConfiguration<String, String>,
                            String,
                            GoalSignature<String, String>>(
                                    genericGame).synthesize();

            assertEquals(
                    "decision mismatch in random FG game " + sample,
                    otf.isWinning(), direct.isWinning());
            assertEquals(
                    "generic-lazy mismatch in random FG game " + sample,
                    direct.isWinning(), genericLazy.isWinning());
            assertValid(directGame, direct);
            assertValid(otfGame, otf);
            assertValid(genericGame, genericLazy);
        }
    }

    private void assertAgreesWithCompleteOtf(GraphGame game) {
        OtfDucsResult<String, String, String> direct =
                new DirectFullStrongSolver<String, String, String>(
                        game).synthesize();
        OtfDucsResult<String, String, String> otf =
                new OtfDucsSynthesizer<String, String, String>(
                        game, 0, 0).synthesize();
        assertEquals(otf.isWinning(), direct.isWinning());
        assertValid(game, direct);
        assertValid(game, otf);
    }

    private <Q, A, G> void assertValid(
            ImplicitStrongGame<Q, A, G> game,
            OtfDucsResult<Q, A, G> result) {
        OtfDucsCertificateChecker.VerificationReport report =
                new OtfDucsCertificateChecker<Q, A, G>(
                        game).verify(result);
        assertTrue(report.violations().toString(), report.isValid());
    }

    private FineGrainedUpdateProblem<String, String>
            fineGrainedProblem(
                    int newStateCount,
                    Set<String> controllable,
                    Map<String, List<Transition>> transitions,
                    Set<String> transferTargets) {
        FiniteLts.Builder<String> newLts =
                FiniteLts.<String>builder("n0");
        for (int state = 0; state < newStateCount; state++) {
            newLts.addState("n" + state);
        }
        for (List<Transition> outgoing : transitions.values()) {
            for (Transition transition : outgoing) {
                newLts.addTransition(
                        transition.source,
                        transition.action,
                        transition.target);
            }
        }
        VersionedComponent<String> component =
                new VersionedComponent<String>(
                        "C",
                        FiniteLts.<String>builder("old").build(),
                        newLts.build(),
                        Collections.singletonMap(
                                "old", transferTargets),
                        "reconfigure.C");
        return FineGrainedUpdateProblem
                .<String, String>builder()
                .addComponent(component)
                .controllableNormalActions(controllable)
                .addInitialSnapshot(
                        new InitialSnapshot<String, String>(
                                PhysicalState.of(
                                        TaggedState.oldState("old")),
                                Collections.<String, String>emptyMap()))
                .addGoalSignature(
                        new GoalSignature<String, String>(
                                "post",
                                PhysicalState.of(
                                        TaggedState.newState(
                                                "n"
                                                        + (newStateCount
                                                                - 1))),
                                Collections.<String, String>emptyMap()))
                .build();
    }

    private Map<String, List<Transition>> transitionMap(
            Transition... transitions) {
        Map<String, List<Transition>> result =
                new LinkedHashMap<String, List<Transition>>();
        for (Transition transition : transitions) {
            addTransition(result, transition);
        }
        return result;
    }

    private static void addTransition(
            Map<String, List<Transition>> transitions,
            Transition transition) {
        List<Transition> outgoing =
                transitions.get(transition.source);
        if (outgoing == null) {
            outgoing = new ArrayList<Transition>();
            transitions.put(transition.source, outgoing);
        }
        outgoing.add(transition);
    }

    private Transition edge(
            String source,
            String action,
            String target) {
        return new Transition(source, action, target);
    }

    private static final class Transition {
        private final String source;
        private final String action;
        private final String target;

        private Transition(
                String source,
                String action,
                String target) {
            this.source = source;
            this.action = action;
            this.target = target;
        }
    }

    private static final class GraphGame
            implements ImplicitStrongGame<String, String, String> {
        private final Set<String> roots =
                new LinkedHashSet<String>();
        private final Set<String> goals =
                new LinkedHashSet<String>();
        private final Set<String> controllable =
                new LinkedHashSet<String>();
        private final Set<String> update =
                new LinkedHashSet<String>();
        private final Map<String, Map<String, Set<String>>> graph =
                new LinkedHashMap<String, Map<String, Set<String>>>();

        private GraphGame(String... roots) {
            this.roots.addAll(Arrays.asList(roots));
        }

        private GraphGame goal(String state) {
            goals.add(state);
            return this;
        }

        private GraphGame controllable(String... actions) {
            controllable.addAll(Arrays.asList(actions));
            return this;
        }

        private GraphGame update(String... actions) {
            update.addAll(Arrays.asList(actions));
            return this;
        }

        private GraphGame edge(
                String source,
                String action,
                String... targets) {
            Map<String, Set<String>> actions = graph.get(source);
            if (actions == null) {
                actions =
                        new LinkedHashMap<String, Set<String>>();
                graph.put(source, actions);
            }
            actions.put(
                    action,
                    new LinkedHashSet<String>(
                            Arrays.asList(targets)));
            return this;
        }

        @Override
        public Set<String> initialStates() {
            return Collections.unmodifiableSet(roots);
        }

        @Override
        public boolean isSafe(String state) {
            return true;
        }

        @Override
        public boolean isGoal(String state) {
            return goals.contains(state);
        }

        @Override
        public Collection<String> candidateActions(String state) {
            Map<String, Set<String>> actions = graph.get(state);
            return actions == null
                    ? Collections.<String>emptyList()
                    : new ArrayList<String>(actions.keySet());
        }

        @Override
        public Set<String> post(String state, String action) {
            Map<String, Set<String>> actions = graph.get(state);
            if (actions == null || !actions.containsKey(action)) {
                return Collections.emptySet();
            }
            return Collections.unmodifiableSet(
                    actions.get(action));
        }

        @Override
        public boolean isControllable(String action) {
            return controllable.contains(action);
        }

        @Override
        public boolean isUpdateAction(String action) {
            return update.contains(action);
        }

        @Override
        public Comparator<String> actionComparator() {
            return Comparator.naturalOrder();
        }

        @Override
        public Comparator<String> stateComparator() {
            return Comparator.naturalOrder();
        }

        @Override
        public String goalMatch(String goalState) {
            return "post:" + goalState;
        }

        @Override
        public boolean isStructurallyValid(String state) {
            return state != null;
        }
    }
}
