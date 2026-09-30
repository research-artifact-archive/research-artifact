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

public class OtfDucsSynthesizerTest {

    @Test
    public void producesRankCertificateAndStopsBeforeIrrelevantBranch() {
        GraphGame game = new GraphGame("s0")
                .goal("goal")
                .controllable("update", "wander", "loop")
                .update("update")
                .edge("s0", "update", "goal")
                .edge("s0", "wander", "detour")
                .edge("detour", "loop", "detour");

        OtfDucsResult<String, String, String> result = synthesize(game);

        assertTrue(result.isWinning());
        assertTrue(result.statistics().earlySuccess());
        assertEquals(1L, result.statistics().expandedStates());
        assertEquals(Integer.valueOf(1), result.winningCertificate().ranks().get("s0"));
        assertEquals(Integer.valueOf(0), result.winningCertificate().ranks().get("goal"));
        assertEquals(Collections.singleton("update"),
                result.winningCertificate().strategy().get("s0").keySet());
        assertValid(game, result);
    }

    @Test
    public void rejectsUncontrollableCycleEvenWhenControllableExitExists() {
        GraphGame game = new GraphGame("s0")
                .goal("goal")
                .controllable("escape")
                .edge("s0", "u", "s0")
                .edge("s0", "escape", "goal");

        OtfDucsResult<String, String, String> result = synthesize(game);

        assertFalse(result.isWinning());
        assertTrue(result.losingCertificate().losingStates().contains("s0"));
        assertValid(game, result);
    }

    @Test
    public void treatsEveryOutcomeOfOneControllableActionAsAdversarial() {
        GraphGame game = new GraphGame("s0")
                .goal("goal")
                .controllable("choose")
                .edge("s0", "choose", "goal", "dead");

        OtfDucsResult<String, String, String> result = synthesize(game);

        assertFalse(result.isWinning());
        assertTrue(result.losingCertificate().losingStates().contains("dead"));
        assertValid(game, result);
    }

    @Test
    public void retainsAllUncontrollableBucketsAndRanksFiniteChain() {
        GraphGame game = new GraphGame("s0")
                .goal("goal")
                .edge("s0", "u1", "s1")
                .edge("s0", "u2", "s2")
                .edge("s1", "u", "goal")
                .edge("s2", "u", "goal");

        OtfDucsResult<String, String, String> result = synthesize(game);

        assertTrue(result.isWinning());
        assertEquals(Integer.valueOf(2), result.winningCertificate().ranks().get("s0"));
        assertEquals(new LinkedHashSet<String>(Arrays.asList("u1", "u2")),
                result.winningCertificate().strategy().get("s0").keySet());
        assertValid(game, result);
    }

    @Test
    public void guidedPriorityFindsStopTransferAlignStartWitnessFirst() {
        GraphGame game = new GraphGame("root")
                .goal("goal")
                .controllable("stop", "reconfigure", "align", "start")
                .update("stop", "reconfigure", "start")
                .edge("root", "start", "a-trap")
                .edge("root", "stop", "b-stopped")
                .edge("b-stopped", "start", "a-trap")
                .edge("b-stopped", "reconfigure", "c-transferred")
                .edge("c-transferred", "start", "a-trap")
                .edge("c-transferred", "align", "d-aligned")
                .edge("d-aligned", "start", "goal")
                .explorationPriority("root", "stop", 0)
                .explorationPriority("root", "start", 3)
                .explorationPriority("b-stopped", "reconfigure", 0)
                .explorationPriority("b-stopped", "start", 2)
                .explorationPriority("c-transferred", "align", 0)
                .explorationPriority("c-transferred", "start", 1);

        OtfDucsResult<String, String, String> result =
                new OtfDucsSynthesizer<String, String, String>(
                        game, 50_000, 100_000).synthesize();

        assertTrue(result.isWinning());
        assertTrue(result.statistics().earlySuccess());
        assertTrue(result.statistics().guidedProofAccepted());
        assertFalse(result.statistics().guidedFallbackUsed());
        assertEquals(0L, result.statistics().attractorPeakFrontier());
        assertEquals(4L, result.statistics().expandedStates());
        assertEquals(Collections.singleton("stop"),
                result.winningCertificate().strategy().get("root").keySet());
        assertEquals(Collections.singleton("reconfigure"),
                result.winningCertificate().strategy().get("b-stopped").keySet());
        assertEquals(Collections.singleton("align"),
                result.winningCertificate().strategy().get("c-transferred").keySet());
        assertEquals(Collections.singleton("start"),
                result.winningCertificate().strategy().get("d-aligned").keySet());
        assertValid(game, result);
    }

    @Test
    public void boundedGuidedFailureFallsBackAndAccumulatesItsWork() {
        GraphGame game = new GraphGame("root")
                .goal("z-goal")
                .controllable("bad", "finish", "loop")
                .edge("root", "bad", "a-loop")
                .edge("root", "finish", "z-goal")
                .edge("a-loop", "loop", "a-loop");

        OtfDucsResult<String, String, String> result =
                new OtfDucsSynthesizer<String, String, String>(
                        game, 100, 2).synthesize();

        assertTrue(result.isWinning());
        assertFalse(result.statistics().guidedProofAccepted());
        assertTrue(result.statistics().guidedFallbackUsed());
        assertEquals(2L, result.statistics().guidedMaximumDepth());
        assertEquals(1L, result.statistics().attractorPeakFrontier());
        assertEquals(3L, result.statistics().discoveredStates());
        assertEquals(2L, result.statistics().expandedStates());
        assertEquals(5L, result.statistics().queriedStateActionPairs());
        assertEquals(5L, result.statistics().materializedTransitions());
        assertEquals(Collections.singleton("finish"),
                result.winningCertificate().strategy().get("root").keySet());
        assertValid(game, result);
    }

    @Test
    public void completeAttractorDefersIrrelevantControllableBucket() {
        GraphGame game = new GraphGame("root")
                .goal("goal")
                .controllable("a-finish", "z-irrelevant", "loop")
                .edge("root", "a-finish", "goal")
                .edge("root", "z-irrelevant", "large-branch")
                .edge("large-branch", "loop", "large-branch");

        OtfDucsResult<String, String, String> result =
                new OtfDucsSynthesizer<String, String, String>(
                        game, 0, 0).synthesize();

        assertTrue(result.isWinning());
        assertTrue(result.statistics().earlySuccess());
        assertFalse(result.statistics().guidedFallbackUsed());
        assertEquals(1L, result.statistics().queriedStateActionPairs());
        assertEquals(1L, result.statistics().expandedStates());
        assertTrue(result.statistics().lazyControllableBuckets());
        assertEquals(1L,
                result.statistics().deferredControllableCandidates());
        assertEquals(0L,
                result.statistics().resumedControllableCandidates());
        assertEquals(1L, result.statistics()
                .unqueriedControllableCandidatesAtTermination());
        assertEquals(Collections.singleton("a-finish"),
                result.winningCertificate().strategy().get("root").keySet());
        assertValid(game, result);
    }

    @Test
    public void controllableOrderChangesLazyCertificateButNotWinningDecision() {
        GraphGame updateFirst = new GraphGame("root")
                .goal("update-goal")
                .goal("normal-goal")
                .controllable("a-normal", "z-update")
                .update("z-update")
                .edge("root", "a-normal", "normal-goal")
                .edge("root", "z-update", "update-goal");
        GraphGame normalFirst = new GraphGame("root")
                .goal("update-goal")
                .goal("normal-goal")
                .controllable("a-normal", "z-update")
                .update("z-update")
                .edge("root", "a-normal", "normal-goal")
                .edge("root", "z-update", "update-goal")
                .explorationPriority("root", "a-normal", 0)
                .explorationPriority("root", "z-update", 1);

        OtfDucsResult<String, String, String> updateResult =
                new OtfDucsSynthesizer<String, String, String>(
                        updateFirst, 0, 0).synthesize();
        OtfDucsResult<String, String, String> normalResult =
                new OtfDucsSynthesizer<String, String, String>(
                        normalFirst, 0, 0).synthesize();

        assertTrue(updateResult.isWinning());
        assertTrue(normalResult.isWinning());
        assertEquals(Collections.singleton("z-update"),
                updateResult.winningCertificate().strategy().get("root").keySet());
        assertEquals(Collections.singleton("a-normal"),
                normalResult.winningCertificate().strategy().get("root").keySet());
        assertEquals(1L, updateResult.statistics().queriedStateActionPairs());
        assertEquals(1L, normalResult.statistics().queriedStateActionPairs());
        assertEquals(1L, updateResult.statistics()
                .unqueriedControllableCandidatesAtTermination());
        assertEquals(1L, normalResult.statistics()
                .unqueriedControllableCandidatesAtTermination());
        assertValid(updateFirst, updateResult);
        assertValid(normalFirst, normalResult);
    }

    @Test
    public void controllableOrderExhaustsEveryCandidateBeforeLosing() {
        GraphGame updateFirst = new GraphGame("root")
                .controllable("a-normal", "z-update")
                .update("z-update")
                .edge("root", "a-normal", "dead")
                .edge("root", "z-update", "root");
        GraphGame normalFirst = new GraphGame("root")
                .controllable("a-normal", "z-update")
                .update("z-update")
                .edge("root", "a-normal", "dead")
                .edge("root", "z-update", "root")
                .explorationPriority("root", "a-normal", 0)
                .explorationPriority("root", "z-update", 1);

        for (GraphGame game : Arrays.asList(updateFirst, normalFirst)) {
            OtfDucsResult<String, String, String> result =
                    new OtfDucsSynthesizer<String, String, String>(
                            game, 0, 0).synthesize();
            assertFalse(result.isWinning());
            assertEquals(2L, result.statistics().queriedStateActionPairs());
            assertEquals(0L, result.statistics()
                    .unqueriedControllableCandidatesAtTermination());
            assertValid(game, result);
        }
    }

    @Test
    public void zeroEitherGuidedLimitDisablesGuidedAttempt() {
        GraphGame game = new GraphGame("root")
                .goal("goal")
                .controllable("finish")
                .edge("root", "finish", "goal");

        OtfDucsResult<String, String, String> zeroStateLimit =
                new OtfDucsSynthesizer<String, String, String>(
                        game, 0, 100).synthesize();
        OtfDucsResult<String, String, String> zeroQueryLimit =
                new OtfDucsSynthesizer<String, String, String>(
                        game, 100, 0).synthesize();

        for (OtfDucsResult<String, String, String> result
                : Arrays.asList(zeroStateLimit, zeroQueryLimit)) {
            assertTrue(result.isWinning());
            assertFalse(result.statistics().guidedProofAccepted());
            assertFalse(result.statistics().guidedFallbackUsed());
            assertEquals(0L, result.statistics().guidedMaximumDepth());
            assertEquals(1L, result.statistics().queriedStateActionPairs());
            assertEquals(1L, result.statistics().attractorPeakFrontier());
            assertValid(game, result);
        }
    }

    @Test
    public void eagerControllableAblationMaterializesEveryBucket() {
        GraphGame game = new GraphGame("root")
                .goal("goal")
                .controllable("a-finish", "z-irrelevant", "loop")
                .edge("root", "a-finish", "goal")
                .edge("root", "z-irrelevant", "large-branch")
                .edge("large-branch", "loop", "large-branch");

        OtfDucsResult<String, String, String> result =
                new OtfDucsSynthesizer<String, String, String>(
                        game, 0, 0, false).synthesize();

        assertTrue(result.isWinning());
        assertFalse(result.statistics().lazyControllableBuckets());
        assertEquals(2L, result.statistics().queriedStateActionPairs());
        assertEquals(0L,
                result.statistics().deferredControllableCandidates());
        assertEquals(3L, result.statistics().discoveredStates());
        assertValid(game, result);
    }

    @Test
    public void completeAttractorExhaustsDeferredBucketsBeforeLosing() {
        GraphGame game = new GraphGame("root")
                .controllable("a-cycle", "b-dead")
                .edge("root", "a-cycle", "root")
                .edge("root", "b-dead", "dead");

        OtfDucsResult<String, String, String> result =
                new OtfDucsSynthesizer<String, String, String>(
                        game, 0, 0).synthesize();

        assertFalse(result.isWinning());
        assertEquals(2L, result.statistics().queriedStateActionPairs());
        assertEquals(1L,
                result.statistics().deferredControllableCandidates());
        assertEquals(1L,
                result.statistics().resumedControllableCandidates());
        assertEquals(0L, result.statistics()
                .unqueriedControllableCandidatesAtTermination());
        assertTrue(result.losingCertificate().losingStates().contains("root"));
        assertTrue(result.losingCertificate().losingStates().contains("dead"));
        assertValid(game, result);
    }

    @Test
    public void deferredBucketPromotesAfterItsTargetWinsLater() {
        GraphGame game = new GraphGame("root")
                .goal("goal")
                .controllable("a-cycle", "b-to-mid", "finish")
                .edge("root", "a-cycle", "root")
                .edge("root", "b-to-mid", "mid")
                .edge("mid", "finish", "goal");

        OtfDucsResult<String, String, String> result =
                new OtfDucsSynthesizer<String, String, String>(
                        game, 0, 0).synthesize();

        assertTrue(result.isWinning());
        assertEquals(Integer.valueOf(2),
                result.winningCertificate().ranks().get("root"));
        assertEquals(Collections.singleton("b-to-mid"),
                result.winningCertificate().strategy().get("root").keySet());
        assertValid(game, result);
    }

    @Test
    public void deferredExpansionSkipsDisabledCandidates() {
        GraphGame game = new GraphGame("root")
                .goal("goal")
                .controllable("a-disabled", "b-cycle", "c-finish")
                .edge("root", "a-disabled")
                .edge("root", "b-cycle", "root")
                .edge("root", "c-finish", "goal");

        OtfDucsResult<String, String, String> result =
                new OtfDucsSynthesizer<String, String, String>(
                        game, 0, 0).synthesize();

        assertTrue(result.isWinning());
        assertEquals(3L, result.statistics().queriedStateActionPairs());
        assertEquals(Collections.singleton("c-finish"),
                result.winningCertificate().strategy().get("root").keySet());
        assertValid(game, result);
    }

    @Test
    public void requiresEveryHotSwapInEmbeddingToWin() {
        GraphGame game = new GraphGame("good", "bad")
                .goal("goal")
                .controllable("finish")
                .edge("good", "finish", "goal")
                .edge("bad", "u", "bad");

        OtfDucsResult<String, String, String> result = synthesize(game);

        assertFalse(result.isWinning());
        assertTrue(result.losingCertificate().losingStates().contains("bad"));
        assertFalse(result.losingCertificate().losingStates().contains("good"));
        assertValid(game, result);
    }

    @Test
    public void independentCheckerRejectsNonDecreasingRank() {
        GraphGame game = new GraphGame("s0")
                .goal("goal")
                .controllable("finish")
                .edge("s0", "finish", "goal");
        OtfDucsResult<String, String, String> valid = synthesize(game);

        Map<String, Integer> badRanks = new LinkedHashMap<String, Integer>(
                valid.winningCertificate().ranks());
        badRanks.put("s0", Integer.valueOf(0));
        OtfDucsResult.WinningCertificate<String, String, String> mutant =
                new OtfDucsResult.WinningCertificate<String, String, String>(
                        valid.winningCertificate().initialStates(), badRanks,
                        valid.winningCertificate().strategy(),
                        valid.winningCertificate().goalMatches());

        OtfDucsCertificateChecker.VerificationReport report =
                new OtfDucsCertificateChecker<String, String, String>(game).verifyWinning(mutant);
        assertFalse(report.isValid());
    }

    @Test
    public void independentCheckerRejectsOmittedNondeterministicOutcome() {
        GraphGame game = new GraphGame("s0")
                .goal("g1")
                .goal("g2")
                .controllable("finish")
                .edge("s0", "finish", "g1", "g2");
        OtfDucsResult<String, String, String> valid = synthesize(game);

        Map<String, Map<String, Set<String>>> badStrategy =
                new LinkedHashMap<String, Map<String, Set<String>>>();
        Map<String, Set<String>> onlyOneOutcome = new LinkedHashMap<String, Set<String>>();
        onlyOneOutcome.put("finish", Collections.singleton("g1"));
        badStrategy.put("s0", onlyOneOutcome);
        OtfDucsResult.WinningCertificate<String, String, String> mutant =
                new OtfDucsResult.WinningCertificate<String, String, String>(
                        valid.winningCertificate().initialStates(),
                        valid.winningCertificate().ranks(), badStrategy,
                        valid.winningCertificate().goalMatches());

        OtfDucsCertificateChecker.VerificationReport report =
                new OtfDucsCertificateChecker<String, String, String>(game).verifyWinning(mutant);
        assertFalse(report.isValid());
    }

    @Test
    public void independentCheckerRejectsLosingSetWithControllableEscape() {
        GraphGame game = new GraphGame("s0")
                .goal("goal")
                .controllable("finish")
                .edge("s0", "finish", "goal");
        OtfDucsResult.LosingCertificate<String> mutant =
                new OtfDucsResult.LosingCertificate<String>(Collections.singleton("s0"));

        OtfDucsCertificateChecker.VerificationReport report =
                new OtfDucsCertificateChecker<String, String, String>(game).verifyLosing(mutant);
        assertFalse(report.isValid());
    }

    @Test
    public void agreesWithAnIndependentExhaustiveFixedPointOnRandomGames() {
        Random random = new Random(20270722L);
        for (int sample = 0; sample < 250; sample++) {
            int stateCount = 2 + random.nextInt(6);
            GraphGame game = new GraphGame("s0");
            for (int state = 0; state < stateCount; state++) {
                if (random.nextInt(5) == 0) {
                    game.goal("s" + state);
                }
                int actionCount = random.nextInt(4);
                for (int actionIndex = 0; actionIndex < actionCount; actionIndex++) {
                    String action = (random.nextBoolean() ? "c" : "u")
                            + state + "_" + actionIndex;
                    if (action.charAt(0) == 'c') {
                        game.controllable(action);
                        if (random.nextBoolean()) {
                            game.update(action);
                        }
                        game.explorationPriority(
                                "s" + state, action, random.nextInt(3));
                    }
                    int outcomeCount = 1 + random.nextInt(Math.min(3, stateCount));
                    LinkedHashSet<String> outcomes = new LinkedHashSet<String>();
                    while (outcomes.size() < outcomeCount) {
                        outcomes.add("s" + random.nextInt(stateCount));
                    }
                    game.edge("s" + state, action,
                            outcomes.toArray(new String[outcomes.size()]));
                }
            }

            boolean expected = exhaustiveWinningSet(game).contains("s0");
            OtfDucsResult<String, String, String> result = synthesize(game);
            assertEquals("sample " + sample, expected, result.isWinning());
            assertValid(game, result);

            OtfDucsResult<String, String, String> fallbackOnly =
                    new OtfDucsSynthesizer<String, String, String>(
                            game, 0, 0).synthesize();
            assertEquals("fallback sample " + sample,
                    expected, fallbackOnly.isWinning());
            assertValid(game, fallbackOnly);

            OtfDucsResult<String, String, String> eagerFallback =
                    new OtfDucsSynthesizer<String, String, String>(
                            game, 0, 0, false).synthesize();
            assertEquals("eager fallback sample " + sample,
                    expected, eagerFallback.isWinning());
            assertValid(game, eagerFallback);
        }
    }

    private Set<String> exhaustiveWinningSet(GraphGame game) {
        Set<String> winning = new LinkedHashSet<String>(game.goals);
        boolean changed;
        do {
            changed = false;
            LinkedHashSet<String> states = new LinkedHashSet<String>();
            states.addAll(game.roots);
            states.addAll(game.graph.keySet());
            for (Map<String, Set<String>> actions : game.graph.values()) {
                for (Set<String> outcomes : actions.values()) states.addAll(outcomes);
            }
            for (String state : states) {
                if (winning.contains(state) || game.goals.contains(state)) continue;
                Map<String, Set<String>> actions = game.graph.get(state);
                if (actions == null || actions.isEmpty()) continue;
                List<Map.Entry<String, Set<String>>> uncontrollable =
                        new ArrayList<Map.Entry<String, Set<String>>>();
                for (Map.Entry<String, Set<String>> entry : actions.entrySet()) {
                    if (!game.controllable.contains(entry.getKey()) && !entry.getValue().isEmpty()) {
                        uncontrollable.add(entry);
                    }
                }
                boolean ready;
                if (!uncontrollable.isEmpty()) {
                    ready = true;
                    for (Map.Entry<String, Set<String>> entry : uncontrollable) {
                        if (!winning.containsAll(entry.getValue())) {
                            ready = false;
                            break;
                        }
                    }
                } else {
                    ready = false;
                    for (Map.Entry<String, Set<String>> entry : actions.entrySet()) {
                        if (game.controllable.contains(entry.getKey())
                                && !entry.getValue().isEmpty()
                                && winning.containsAll(entry.getValue())) {
                            ready = true;
                            break;
                        }
                    }
                }
                if (ready && winning.add(state)) changed = true;
            }
        } while (changed);
        return winning;
    }

    private OtfDucsResult<String, String, String> synthesize(GraphGame game) {
        return new OtfDucsSynthesizer<String, String, String>(game).synthesize();
    }

    private void assertValid(GraphGame game, OtfDucsResult<String, String, String> result) {
        OtfDucsCertificateChecker.VerificationReport report =
                new OtfDucsCertificateChecker<String, String, String>(game).verify(result);
        assertTrue(report.violations().toString(), report.isValid());
    }

    private static final class GraphGame implements ImplicitStrongGame<String, String, String> {
        private final Set<String> roots = new LinkedHashSet<String>();
        private final Set<String> goals = new LinkedHashSet<String>();
        private final Set<String> controllable = new LinkedHashSet<String>();
        private final Set<String> update = new LinkedHashSet<String>();
        private final Map<String, Map<String, Set<String>>> graph =
                new LinkedHashMap<String, Map<String, Set<String>>>();
        private final Map<String, Map<String, Integer>> explorationPriorities =
                new LinkedHashMap<String, Map<String, Integer>>();

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

        private GraphGame edge(String source, String action, String... targets) {
            Map<String, Set<String>> actions = graph.get(source);
            if (actions == null) {
                actions = new LinkedHashMap<String, Set<String>>();
                graph.put(source, actions);
            }
            actions.put(action, new LinkedHashSet<String>(Arrays.asList(targets)));
            return this;
        }

        private GraphGame explorationPriority(
                String state,
                String action,
                int priority) {
            Map<String, Integer> priorities = explorationPriorities.get(state);
            if (priorities == null) {
                priorities = new LinkedHashMap<String, Integer>();
                explorationPriorities.put(state, priorities);
            }
            priorities.put(action, Integer.valueOf(priority));
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
            return Collections.unmodifiableSet(actions.get(action));
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
        public int explorationActionPriority(String state, String action) {
            Map<String, Integer> priorities = explorationPriorities.get(state);
            Integer priority = priorities == null ? null : priorities.get(action);
            return priority == null ? 0 : priority.intValue();
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
