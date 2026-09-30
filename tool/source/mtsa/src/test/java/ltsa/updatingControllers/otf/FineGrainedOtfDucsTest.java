package ltsa.updatingControllers.otf;

import org.testng.annotations.Test;

import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Set;
import java.util.function.Function;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotEquals;
import static org.junit.Assert.assertTrue;

public class FineGrainedOtfDucsTest {

    @Test
    public void controllableActionOrderPropertyIsValidatedAndDefaultsToEndpointGuided() {
        assertEquals(
                FineGrainedSuccessorOracle.ControllableActionOrder.ENDPOINT_GUIDED,
                FineGrainedSuccessorOracle.ControllableActionOrder
                        .fromPropertyValue(null));
        assertEquals(
                FineGrainedSuccessorOracle.ControllableActionOrder.UPDATE_FIRST,
                FineGrainedSuccessorOracle.ControllableActionOrder
                        .fromPropertyValue("update_first"));

        boolean rejected = false;
        try {
            FineGrainedSuccessorOracle.ControllableActionOrder
                    .fromPropertyValue("invalid");
        } catch (IllegalArgumentException expected) {
            rejected = true;
        }
        assertTrue(rejected);
    }

    @Test
    public void normalSynchronizationReturnsTheFullCartesianProduct() {
        FiniteLts<String> oldA = FiniteLts.<String>builder("a0")
                .addTransition("a0", "move", "a1")
                .addTransition("a0", "move", "a2")
                .build();
        FiniteLts<String> oldB = FiniteLts.<String>builder("b0")
                .addTransition("b0", "move", "b1")
                .addTransition("b0", "move", "b2")
                .build();
        VersionedComponent<String> componentA = component(
                "A", oldA, singletonLts("an"), "a0", setOf("an"), "rhoA");
        VersionedComponent<String> componentB = component(
                "B", oldB, singletonLts("bn"), "b0", setOf("bn"), "rhoB");
        VersionedComponent<String> nonParticipant = component(
                "C", singletonLts("c0"), singletonLts("cn"),
                "c0", setOf("cn"), "rhoC");

        PhysicalState<String> initialPhysical = PhysicalState.of(
                TaggedState.oldState("a0"), TaggedState.oldState("b0"),
                TaggedState.oldState("c0"));
        FineGrainedUpdateProblem<String, String> problem =
                FineGrainedUpdateProblem.<String, String>builder()
                        .addComponent(componentA)
                        .addComponent(componentB)
                        .addComponent(nonParticipant)
                        .addInitialSnapshot(new InitialSnapshot<String, String>(
                                initialPhysical, Collections.<String, String>emptyMap()))
                        .addGoalSignature(new GoalSignature<String, String>(
                                "post", PhysicalState.of(
                                        TaggedState.newState("an"),
                                        TaggedState.newState("bn"),
                                        TaggedState.newState("cn")),
                                Collections.<String, String>emptyMap()))
                        .build();

        FineGrainedSuccessorOracle<String, String> oracle =
                new FineGrainedSuccessorOracle<String, String>(problem);
        CanonicalUpdateConfiguration<String, String> root =
                problem.initialConfigurations().get(0);
        Set<CanonicalUpdateConfiguration<String, String>> outcomes =
                oracle.post(root, "move");

        assertEquals(4, outcomes.size());
        Set<PhysicalState<String>> physical = new LinkedHashSet<PhysicalState<String>>();
        for (CanonicalUpdateConfiguration<String, String> outcome : outcomes) {
            physical.add(outcome.physicalState());
            assertEquals(root.pendingActions(), outcome.pendingActions());
        }
        assertTrue(physical.contains(PhysicalState.of(
                TaggedState.oldState("a1"), TaggedState.oldState("b1"),
                TaggedState.oldState("c0"))));
        assertTrue(physical.contains(PhysicalState.of(
                TaggedState.oldState("a1"), TaggedState.oldState("b2"),
                TaggedState.oldState("c0"))));
        assertTrue(physical.contains(PhysicalState.of(
                TaggedState.oldState("a2"), TaggedState.oldState("b1"),
                TaggedState.oldState("c0"))));
        assertTrue(physical.contains(PhysicalState.of(
                TaggedState.oldState("a2"), TaggedState.oldState("b2"),
                TaggedState.oldState("c0"))));
    }

    @Test
    public void observerOnlyTransitionsTrackButDoNotEnableEnvironmentActions() {
        FiniteLts<String> augmentedCarrierOld = FiniteLts.<String>builder("carrier0")
                .addTransition("carrier0", "observed", "carrier1")
                .addTransition("carrier1", "observed", "carrier1")
                .build();
        VersionedComponent<String> observerCarrier = new VersionedComponent<String>(
                "carrier",
                augmentedCarrierOld,
                singletonLts("carrierNew"),
                Collections.singletonMap("carrier0", setOf("carrierNew")),
                "rhoCarrier",
                Collections.<String>emptySet(),
                Collections.<String>emptySet());
        VersionedComponent<String> physicalSource = new VersionedComponent<String>(
                "source",
                FiniteLts.<String>builder("source0")
                        .addTransition("source0", "observed", "source1")
                        .build(),
                singletonLts("sourceNew"),
                Collections.singletonMap("source0", setOf("sourceNew")),
                "rhoSource");

        FineGrainedUpdateProblem<String, String> enabledProblem =
                FineGrainedUpdateProblem.<String, String>builder()
                        .addComponent(observerCarrier)
                        .addComponent(physicalSource)
                        .addInitialSnapshot(new InitialSnapshot<String, String>(
                                PhysicalState.of(
                                        TaggedState.oldState("carrier0"),
                                        TaggedState.oldState("source0")),
                                Collections.<String, String>emptyMap()))
                        .addGoalSignature(new GoalSignature<String, String>(
                                "post",
                                PhysicalState.of(
                                        TaggedState.newState("carrierNew"),
                                        TaggedState.newState("sourceNew")),
                                Collections.<String, String>emptyMap()))
                        .build();
        FineGrainedSuccessorOracle<String, String> enabledOracle =
                new FineGrainedSuccessorOracle<String, String>(enabledProblem);
        CanonicalUpdateConfiguration<String, String> enabledRoot =
                enabledProblem.initialConfigurations().get(0);
        CanonicalUpdateConfiguration<String, String> tracked =
                only(enabledOracle.post(enabledRoot, "observed"));
        assertEquals("carrier1", tracked.physicalState().component(0).state());
        assertEquals("source1", tracked.physicalState().component(1).state());

        FineGrainedUpdateProblem<String, String> disabledProblem =
                FineGrainedUpdateProblem.<String, String>builder()
                        .addComponent(observerCarrier)
                        .addInitialSnapshot(new InitialSnapshot<String, String>(
                                PhysicalState.of(TaggedState.oldState("carrier0")),
                                Collections.<String, String>emptyMap()))
                        .addGoalSignature(new GoalSignature<String, String>(
                                "post",
                                PhysicalState.of(TaggedState.newState("carrierNew")),
                                Collections.<String, String>emptyMap()))
                        .build();
        FineGrainedSuccessorOracle<String, String> disabledOracle =
                new FineGrainedSuccessorOracle<String, String>(disabledProblem);
        CanonicalUpdateConfiguration<String, String> disabledRoot =
                disabledProblem.initialConfigurations().get(0);
        assertFalse(disabledOracle.candidateActions(disabledRoot).contains("observed"));
        assertTrue(disabledOracle.post(disabledRoot, "observed").isEmpty());
    }

    @Test
    public void stopAndStartUseTheSpecifiedHalfOpenBoundaries() {
        String rho = "rho";
        String stop = "stop.old";
        String start = "start.new";
        Set<String> common = setOf(rho, stop, start);
        PhysicalState<String> oldPhysical = PhysicalState.of(TaggedState.oldState("old"));
        PhysicalState<String> newPhysical = PhysicalState.of(TaggedState.newState("new"));

        SafetyTester<String> oldTester = badOn("oldSafe", "oldError", stop);
        SafetyTester<String> newTester = badOn("newActivated", "newError", start);
        SafetyTester<String> intervalTester = recorderTester(stop, start);

        ActivationSpec<String, String> newActivation =
                ActivationSpec.<String, String, String>builder(
                                badOnResidual(common, start, "newResidualSafe", "newResidualError"))
                        .put(oldPhysical, "newActivated", "newResidualSafe")
                        .build();
        ActivationSpec<String, String> intervalActivation =
                ActivationSpec.<String, String, String>builder(
                                emptyBadLanguage(common, "intervalResidual"))
                        .put(oldPhysical, "interval0", "intervalResidual")
                        .build();

        VersionedComponent<String> component = component(
                "C", singletonLts("old"), singletonLts("new"),
                "old", setOf("new"), rho);
        FineGrainedUpdateProblem<String, String> problem =
                FineGrainedUpdateProblem.<String, String>builder()
                        .addComponent(component)
                        .addRequirement(Requirement.<String, String>oldRequirement(
                                "oldR", oldTester, stop))
                        .addRequirement(Requirement.<String, String>newRequirement(
                                "newR", newTester, newActivation, start))
                        .addRequirement(Requirement.<String, String>updateTimeRequirement(
                                "duringR", intervalTester, intervalActivation))
                        .addInitialSnapshot(new InitialSnapshot<String, String>(
                                oldPhysical, Collections.singletonMap("oldR", "oldSafe")))
                        .addGoalSignature(new GoalSignature<String, String>(
                                "post", newPhysical,
                                Collections.singletonMap("newR", "newActivated")))
                        .build();
        FineGrainedSuccessorOracle<String, String> oracle =
                new FineGrainedSuccessorOracle<String, String>(problem);

        CanonicalUpdateConfiguration<String, String> root =
                problem.initialConfigurations().get(0);
        CanonicalUpdateConfiguration<String, String> afterStop = only(oracle.post(root, stop));
        assertFalse(afterStop.isTesterActive("oldR"));
        assertEquals("intervalStopped", afterStop.testerState("duringR").get());
        assertTrue(oracle.isSafe(afterStop));

        CanonicalUpdateConfiguration<String, String> afterStart =
                only(oracle.post(afterStop, start));
        assertEquals("newActivated", afterStart.testerState("newR").get());
        assertEquals("intervalBoth", afterStart.testerState("duringR").get());
        assertTrue("The target new tester must not observe its own start action",
                oracle.isSafe(afterStart));
    }

    @Test
    public void reconfigureKeepsEveryTransferOutcomeIncludingUnsafeOnes() {
        String rho = "rho";
        PhysicalState<String> oldPhysical = PhysicalState.of(TaggedState.oldState("old"));
        VersionedComponent<String> component = component(
                "C", singletonLts("old"),
                FiniteLts.<String>builder("newSafe").addState("newUnsafe").build(),
                "old", setOf("newSafe", "newUnsafe"), rho);
        SafetyTester<String> interval = badOn("safe", "error", rho);
        ActivationSpec<String, String> activation =
                ActivationSpec.<String, String, String>builder(
                                badOnResidual(setOf(rho), rho, "residualSafe", "residualError"))
                        .put(oldPhysical, "safe", "residualSafe")
                        .build();
        FineGrainedUpdateProblem<String, String> problem =
                FineGrainedUpdateProblem.<String, String>builder()
                        .addComponent(component)
                        .addRequirement(Requirement.<String, String>updateTimeRequirement(
                                "during", interval, activation))
                        .addInitialSnapshot(new InitialSnapshot<String, String>(
                                oldPhysical, Collections.<String, String>emptyMap()))
                        .addGoalSignature(new GoalSignature<String, String>(
                                "safeEndpoint",
                                PhysicalState.of(TaggedState.newState("newSafe")),
                                Collections.<String, String>emptyMap()))
                        .addGoalSignature(new GoalSignature<String, String>(
                                "unsafeEndpoint",
                                PhysicalState.of(TaggedState.newState("newUnsafe")),
                                Collections.<String, String>emptyMap()))
                        .build();
        FineGrainedSuccessorOracle<String, String> oracle =
                new FineGrainedSuccessorOracle<String, String>(problem);

        Set<CanonicalUpdateConfiguration<String, String>> outcomes = oracle.post(
                problem.initialConfigurations().get(0), rho);
        assertEquals(2, outcomes.size());
        for (CanonicalUpdateConfiguration<String, String> outcome : outcomes) {
            assertFalse("Unsafe outcomes must be materialized, not filtered", oracle.isSafe(outcome));
            assertEquals("error", outcome.testerState("during").get());
        }
        OtfDucsResult<CanonicalUpdateConfiguration<String, String>, String,
                GoalSignature<String, String>> result =
                FineGrainedOtfDucs.synthesizeTrustedEndpointProjections(problem);
        assertFalse(result.isWinning());
        assertTrue(FineGrainedOtfDucs.verify(problem, result).isValid());
    }

    @Test
    public void emptyTransferAndGuardOutsideDisableActionsWithoutRejectingInput() {
        String rho = "rho";
        String start = "start";
        PhysicalState<String> oldPhysical = PhysicalState.of(TaggedState.oldState("old"));
        VersionedComponent<String> component = new VersionedComponent<String>(
                "C", singletonLts("old"), singletonLts("new"),
                Collections.<String, Set<String>>emptyMap(), rho);
        SafetyTester<String> tester = oneStateTester("safe");
        ActivationSpec<String, String> emptyGuard =
                ActivationSpec.<String, String, String>builder(
                        emptyBadLanguage(setOf(rho, start), "residual")).build();
        FineGrainedUpdateProblem<String, String> problem =
                FineGrainedUpdateProblem.<String, String>builder()
                        .addComponent(component)
                        .addRequirement(Requirement.<String, String>newRequirement(
                                "newR", tester, emptyGuard, start))
                        .addInitialSnapshot(new InitialSnapshot<String, String>(
                                oldPhysical, Collections.<String, String>emptyMap()))
                        .addGoalSignature(new GoalSignature<String, String>(
                                "post", PhysicalState.of(TaggedState.newState("new")),
                                Collections.singletonMap("newR", "safe")))
                        .build();
        FineGrainedSuccessorOracle<String, String> oracle =
                new FineGrainedSuccessorOracle<String, String>(problem);
        CanonicalUpdateConfiguration<String, String> root =
                problem.initialConfigurations().get(0);

        assertTrue(oracle.post(root, rho).isEmpty());
        assertTrue(oracle.post(root, start).isEmpty());
    }

    @Test
    public void transitivePrecedenceAndOneShotPendingRemovalAreEnforced() {
        VersionedComponent<String> a = component(
                "A", singletonLts("ao"), singletonLts("an"),
                "ao", setOf("an"), "rhoA");
        VersionedComponent<String> b = component(
                "B", singletonLts("bo"), singletonLts("bn"),
                "bo", setOf("bn"), "rhoB");
        VersionedComponent<String> c = component(
                "C", singletonLts("co"), singletonLts("cn"),
                "co", setOf("cn"), "rhoC");
        FineGrainedUpdateProblem<String, String> problem =
                FineGrainedUpdateProblem.<String, String>builder()
                        .addComponent(a).addComponent(b).addComponent(c)
                        .addPrecedence("rhoA", "rhoB")
                        .addPrecedence("rhoB", "rhoC")
                        .addInitialSnapshot(new InitialSnapshot<String, String>(
                                PhysicalState.of(
                                        TaggedState.oldState("ao"),
                                        TaggedState.oldState("bo"),
                                        TaggedState.oldState("co")),
                                Collections.<String, String>emptyMap()))
                        .addGoalSignature(new GoalSignature<String, String>(
                                "post", PhysicalState.of(
                                        TaggedState.newState("an"),
                                        TaggedState.newState("bn"),
                                        TaggedState.newState("cn")),
                                Collections.<String, String>emptyMap()))
                        .build();
        FineGrainedSuccessorOracle<String, String> oracle =
                new FineGrainedSuccessorOracle<String, String>(problem);
        IndependentFineGrainedSemantics<String, String> independent =
                new IndependentFineGrainedSemantics<String, String>(problem);
        CanonicalUpdateConfiguration<String, String> root =
                problem.initialConfigurations().get(0);

        assertEquals(setOf("rhoA"),
                new LinkedHashSet<String>(oracle.candidateActions(root)));
        assertEquals(setOf("rhoA"),
                new LinkedHashSet<String>(independent.candidateActions(root)));
        assertTrue(oracle.post(root, "rhoB").isEmpty());
        assertTrue(oracle.post(root, "rhoC").isEmpty());
        CanonicalUpdateConfiguration<String, String> afterA = only(oracle.post(root, "rhoA"));
        assertFalse(afterA.pendingActions().contains("rhoA"));
        assertEquals(setOf("rhoB"),
                new LinkedHashSet<String>(oracle.candidateActions(afterA)));
        assertEquals(setOf("rhoB"),
                new LinkedHashSet<String>(independent.candidateActions(afterA)));
        assertTrue(oracle.post(afterA, "rhoA").isEmpty());
        assertTrue(oracle.post(afterA, "rhoC").isEmpty());
        CanonicalUpdateConfiguration<String, String> afterB = only(oracle.post(afterA, "rhoB"));
        assertEquals(setOf("rhoC"),
                new LinkedHashSet<String>(oracle.candidateActions(afterB)));
        assertEquals(setOf("rhoC"),
                new LinkedHashSet<String>(independent.candidateActions(afterB)));
        CanonicalUpdateConfiguration<String, String> afterC = only(oracle.post(afterB, "rhoC"));
        assertTrue(oracle.candidateActions(afterC).isEmpty());
        assertTrue(independent.candidateActions(afterC).isEmpty());
        assertTrue(afterC.pendingActions().isEmpty());
        assertTrue(oracle.isGoal(afterC));
    }

    @Test
    public void oneBadTransferOutcomeMakesTheStrongProblemLosing() {
        String rho = "rho";
        VersionedComponent<String> component = component(
                "C", singletonLts("old"),
                FiniteLts.<String>builder("good").addState("bad").build(),
                "old", setOf("good", "bad"), rho);
        FineGrainedUpdateProblem<String, String> problem =
                FineGrainedUpdateProblem.<String, String>builder()
                        .addComponent(component)
                        .addInitialSnapshot(new InitialSnapshot<String, String>(
                                PhysicalState.of(TaggedState.oldState("old")),
                                Collections.<String, String>emptyMap()))
                        .addGoalSignature(new GoalSignature<String, String>(
                                "onlyGood", PhysicalState.of(TaggedState.newState("good")),
                                Collections.<String, String>emptyMap()))
                        .build();

        OtfDucsResult<CanonicalUpdateConfiguration<String, String>, String,
                GoalSignature<String, String>> result =
                FineGrainedOtfDucs.synthesizeTrustedEndpointProjections(problem);
        assertFalse(result.isWinning());
        assertTrue(FineGrainedOtfDucs.verify(problem, result).isValid());
    }

    @Test
    public void protocolGuidedOrderingPrioritizesReconfigureBeforeAlignment() {
        String normal = "a-normal";
        String update = "z-update";
        FiniteLts<String> oldLts = FiniteLts.<String>builder("old0")
                .addTransition("old0", normal, "old1")
                .addTransition("old1", normal, "old2")
                .build();
        FiniteLts<String> newLts = FiniteLts.<String>builder("newMid")
                .addTransition("newMid", normal, "newGoal")
                .build();
        Map<String, Set<String>> transfer = new LinkedHashMap<String, Set<String>>();
        transfer.put("old0", setOf("newMid"));
        transfer.put("old1", setOf("newMid"));
        transfer.put("old2", setOf("newGoal"));
        VersionedComponent<String> component = new VersionedComponent<String>(
                "C", oldLts, newLts, transfer, update);
        FineGrainedUpdateProblem<String, String> problem =
                FineGrainedUpdateProblem.<String, String>builder()
                        .addComponent(component)
                        .controllableNormalActions(setOf(normal))
                        .addInitialSnapshot(new InitialSnapshot<String, String>(
                                PhysicalState.of(TaggedState.oldState("old0")),
                                Collections.<String, String>emptyMap()))
                        .addGoalSignature(new GoalSignature<String, String>(
                                "post",
                                PhysicalState.of(TaggedState.newState("newGoal")),
                                Collections.<String, String>emptyMap()))
                        .build();

        FineGrainedSuccessorOracle<String, String> updateFirstGame =
                new FineGrainedSuccessorOracle<String, String>(
                        problem,
                        FineGrainedSuccessorOracle.ControllableActionOrder.UPDATE_FIRST);
        FineGrainedSuccessorOracle<String, String> endpointGuidedGame =
                new FineGrainedSuccessorOracle<String, String>(
                        problem,
                        FineGrainedSuccessorOracle.ControllableActionOrder.ENDPOINT_GUIDED);
        OtfDucsResult<CanonicalUpdateConfiguration<String, String>, String,
                GoalSignature<String, String>> updateFirst =
                new OtfDucsSynthesizer<CanonicalUpdateConfiguration<String, String>,
                        String, GoalSignature<String, String>>(
                        updateFirstGame, 0, 0).synthesize();
        OtfDucsResult<CanonicalUpdateConfiguration<String, String>, String,
                GoalSignature<String, String>> endpointGuided =
                new OtfDucsSynthesizer<CanonicalUpdateConfiguration<String, String>,
                        String, GoalSignature<String, String>>(
                        endpointGuidedGame, 0, 0).synthesize();

        CanonicalUpdateConfiguration<String, String> root =
                problem.initialConfigurations().get(0);
        assertTrue(updateFirst.isWinning());
        assertTrue(endpointGuided.isWinning());
        assertEquals(Collections.singleton(update),
                updateFirst.winningCertificate().strategy().get(root).keySet());
        assertEquals(Collections.singleton(update),
                endpointGuided.winningCertificate().strategy().get(root).keySet());
        assertEquals(updateFirst.statistics().queriedStateActionPairs(),
                endpointGuided.statistics().queriedStateActionPairs());
        assertEquals(updateFirst.winningCertificate().ranks().size(),
                endpointGuided.winningCertificate().ranks().size());
        new OtfDucsCertificateChecker<CanonicalUpdateConfiguration<String, String>,
                String, GoalSignature<String, String>>(updateFirstGame)
                .verify(updateFirst).throwIfInvalid();
        new OtfDucsCertificateChecker<CanonicalUpdateConfiguration<String, String>,
                String, GoalSignature<String, String>>(endpointGuidedGame)
                .verify(endpointGuided).throwIfInvalid();
    }

    @Test
    public void phaseAwareOrderingStopsTransfersAlignsThenStarts() {
        String normal = "normal";
        String stop = "stop.old";
        String reconfigure = "reconfigure";
        String start = "start.new";
        PhysicalState<String> oldPhysical =
                PhysicalState.of(TaggedState.oldState("old"));
        PhysicalState<String> intermediatePhysical =
                PhysicalState.of(TaggedState.newState("newMid"));
        PhysicalState<String> goalPhysical =
                PhysicalState.of(TaggedState.newState("newGoal"));
        FiniteLts<String> oldLts = FiniteLts.<String>builder("old")
                .addTransition("old", normal, "old")
                .build();
        FiniteLts<String> newLts = FiniteLts.<String>builder("newMid")
                .addTransition("newMid", normal, "newGoal")
                .addTransition("newGoal", normal, "newGoal")
                .build();
        Map<String, Set<String>> transfer = new LinkedHashMap<String, Set<String>>();
        transfer.put("old", setOf("newMid"));
        VersionedComponent<String> component = new VersionedComponent<String>(
                "C", oldLts, newLts, transfer, reconfigure);
        Set<String> common = setOf(normal, stop, reconfigure, start);
        ActivationSpec<String, String> newActivation =
                ActivationSpec.<String, String, String>builder(
                                emptyBadLanguage(common, "residual"))
                        .put(goalPhysical, "newSafe", "residual")
                        .build();
        FineGrainedUpdateProblem<String, String> problem =
                FineGrainedUpdateProblem.<String, String>builder()
                        .addComponent(component)
                        .addRequirement(Requirement.<String, String>oldRequirement(
                                "oldR", oneStateTester("oldSafe"), stop))
                        .addRequirement(Requirement.<String, String>newRequirement(
                                "newR", oneStateTester("newSafe"),
                                newActivation, start))
                        .controllableNormalActions(setOf(normal))
                        .addInitialSnapshot(new InitialSnapshot<String, String>(
                                oldPhysical,
                                Collections.singletonMap("oldR", "oldSafe")))
                        .addGoalSignature(new GoalSignature<String, String>(
                                "post", goalPhysical,
                                Collections.singletonMap("newR", "newSafe")))
                        .build();
        FineGrainedSuccessorOracle<String, String> endpointGuided =
                new FineGrainedSuccessorOracle<String, String>(
                        problem,
                        FineGrainedSuccessorOracle.ControllableActionOrder
                                .ENDPOINT_GUIDED);
        FineGrainedSuccessorOracle<String, String> updateFirst =
                new FineGrainedSuccessorOracle<String, String>(
                        problem,
                        FineGrainedSuccessorOracle.ControllableActionOrder
                                .UPDATE_FIRST);

        CanonicalUpdateConfiguration<String, String> root =
                problem.initialConfigurations().get(0);
        CanonicalUpdateConfiguration<String, String> afterStop =
                CanonicalUpdateConfiguration.of(
                        oldPhysical,
                        Collections.<String, String>emptyMap(),
                        setOf(reconfigure, start));
        CanonicalUpdateConfiguration<String, String> afterTransfer =
                CanonicalUpdateConfiguration.of(
                        intermediatePhysical,
                        Collections.<String, String>emptyMap(),
                        setOf(start));
        CanonicalUpdateConfiguration<String, String> aligned =
                CanonicalUpdateConfiguration.of(
                        goalPhysical,
                        Collections.<String, String>emptyMap(),
                        setOf(start));

        assertEquals(0, endpointGuided.explorationActionPriority(root, stop));
        assertEquals(1, endpointGuided.explorationActionPriority(
                root, reconfigure));
        assertEquals(2, endpointGuided.explorationActionPriority(root, normal));
        assertEquals(3, endpointGuided.explorationActionPriority(root, start));
        assertEquals(0, endpointGuided.explorationActionPriority(
                afterStop, reconfigure));
        assertEquals(1, endpointGuided.explorationActionPriority(
                afterStop, normal));
        assertEquals(2, endpointGuided.explorationActionPriority(
                afterStop, start));
        assertFalse(endpointGuided.preferUpdateActions(afterTransfer));
        assertEquals(0, endpointGuided.explorationActionPriority(
                afterTransfer, normal));
        assertEquals(1, endpointGuided.explorationActionPriority(
                afterTransfer, start));
        assertTrue(endpointGuided.preferUpdateActions(aligned));
        assertEquals(0, endpointGuided.explorationActionPriority(
                aligned, start));
        assertEquals(1, endpointGuided.explorationActionPriority(
                aligned, normal));
        assertEquals(0, updateFirst.explorationActionPriority(
                afterTransfer, start));
        assertEquals(1, updateFirst.explorationActionPriority(
                afterTransfer, normal));
    }

    @Test
    public void oneLosingHotSwapInEmbeddingMakesTheWholeProblemLosing() {
        Map<String, Set<String>> transfer = new LinkedHashMap<String, Set<String>>();
        transfer.put("oldGood", setOf("new"));
        transfer.put("oldBad", Collections.<String>emptySet());
        VersionedComponent<String> component = new VersionedComponent<String>(
                "C", FiniteLts.<String>builder("oldGood").addState("oldBad").build(),
                singletonLts("new"), transfer, "rho");
        FineGrainedUpdateProblem<String, String> problem =
                FineGrainedUpdateProblem.<String, String>builder()
                        .addComponent(component)
                        .addInitialSnapshot(new InitialSnapshot<String, String>(
                                PhysicalState.of(TaggedState.oldState("oldGood")),
                                Collections.<String, String>emptyMap()))
                        .addInitialSnapshot(new InitialSnapshot<String, String>(
                                PhysicalState.of(TaggedState.oldState("oldBad")),
                                Collections.<String, String>emptyMap()))
                        .addGoalSignature(new GoalSignature<String, String>(
                                "post", PhysicalState.of(TaggedState.newState("new")),
                                Collections.<String, String>emptyMap()))
                        .build();

        OtfDucsResult<CanonicalUpdateConfiguration<String, String>, String,
                GoalSignature<String, String>> result =
                FineGrainedOtfDucs.synthesizeTrustedEndpointProjections(problem);
        assertFalse(result.isWinning());
        assertTrue(FineGrainedOtfDucs.verify(problem, result).isValid());
        assertEquals(1, result.losingCertificate().losingStates().size());
    }

    @Test
    public void exhaustiveEndpointsSynthesizeAndMaterializeTheAtomicLink() {
        FiniteLts<String> oldEndpoint = FiniteLts.<String>builder("z0")
                .addTransition("z0", "tick", "z1")
                .addTransition("z1", "tick", "z1")
                .build();
        FiniteLts<String> newEndpoint = FiniteLts.<String>builder("p0")
                .addTransition("p0", "tick", "p1")
                .addTransition("p1", "tick", "p1")
                .build();
        FiniteLts<String> oldComponent = FiniteLts.<String>builder("old0")
                .addTransition("old0", "tick", "old1")
                .addTransition("old1", "tick", "old1")
                .build();
        FiniteLts<String> newComponent = FiniteLts.<String>builder("new0")
                .addTransition("new0", "tick", "new1")
                .addTransition("new1", "tick", "new1")
                .build();
        Map<String, Set<String>> transfer = new LinkedHashMap<String, Set<String>>();
        transfer.put("old0", setOf("new0"));
        transfer.put("old1", setOf("new1"));
        VersionedComponent<String> component = new VersionedComponent<String>(
                "C", oldComponent, newComponent, transfer, "rho");

        Function<String, InitialSnapshot<String, String>> oldProjection =
                new Function<String, InitialSnapshot<String, String>>() {
                    @Override
                    public InitialSnapshot<String, String> apply(String state) {
                        String local = state.equals("z0") ? "old0" : "old1";
                        return new InitialSnapshot<String, String>(
                                PhysicalState.of(TaggedState.oldState(local)),
                                Collections.<String, String>emptyMap());
                    }
                };
        Function<String, GoalSignature<String, String>> newProjection =
                new Function<String, GoalSignature<String, String>>() {
                    @Override
                    public GoalSignature<String, String> apply(String state) {
                        String local = state.equals("p0") ? "new0" : "new1";
                        return new GoalSignature<String, String>(
                                state, PhysicalState.of(TaggedState.newState(local)),
                                Collections.<String, String>emptyMap());
                    }
                };

        FineGrainedUpdateProblem<String, String> problem =
                FineGrainedUpdateProblem.<String, String>builder()
                        .addComponent(component)
                        .controllableNormalActions(setOf("tick"))
                        .initialSnapshotsFromReachable(oldEndpoint, oldProjection)
                        .goalSignaturesFromReachable(newEndpoint, newProjection)
                        .build();
        assertTrue(problem.hasExhaustiveEndpointCoverage());

        OtfDucsResult<CanonicalUpdateConfiguration<String, String>, String,
                GoalSignature<String, String>> result = FineGrainedOtfDucs.synthesize(problem);
        assertTrue(result.isWinning());
        assertEquals(2, result.winningCertificate().initialStates().size());

        LinkedOtfDucsController<String, String, String, String> linked =
                LinkedOtfDucsController.link(oldEndpoint, newEndpoint, problem, result,
                        oldProjection, newProjection);
        assertEquals(6, linked.lts().states().size());
        assertFalse(linked.lts().alphabet().contains(problem.hotSwapOutAction()));
        for (String oldState : oldEndpoint.reachableStates()) {
            assertEquals(1, linked.lts().successors(
                    LinkedOtfDucsController.State.<String, String, String, String>pre(oldState),
                    problem.hotSwapInAction()).size());
        }
        Set<LinkedOtfDucsController.State<String, String, String, String>> inherited =
                linked.lts().successors(
                        LinkedOtfDucsController.State.<String, String, String, String>post("p0"),
                        "tick");
        assertEquals(Collections.singleton(
                LinkedOtfDucsController.State.<String, String, String, String>post("p1")),
                inherited);
        MtsaLtsExport<LinkedOtfDucsController.State<String, String, String, String>> export =
                linked.toMtsa();
        assertEquals(linked.lts().states().size(), export.mts().getStates().size());
        assertEquals(Long.valueOf(0L), export.idByState().get(linked.lts().initialState()));
        assertEquals(linked.lts().states().size(),
                export.toCompactState("REVISED_OTF_DUCS").maxStates);
        assertFalse(FiniteLts.fromMtsa(
                export.toCompactState("REVISED_OTF_DUCS_ROUNDTRIP"))
                .alphabet().contains("tau"));
        LinkedOtfDucsControllerChecker.VerificationReport report =
                new LinkedOtfDucsControllerChecker<String, String, String, String>().verify(
                        linked, oldEndpoint, newEndpoint, problem, result,
                        oldProjection, newProjection);
        assertTrue(report.violations().toString(), report.isValid());

        FiniteLts<LinkedOtfDucsController.State<String, String, String, String>> original =
                linked.lts();
        FiniteLts.Builder<LinkedOtfDucsController.State<String, String, String, String>> mutantLts =
                FiniteLts.builder(original.initialState());
        mutantLts.addStates(original.states()).addActions(original.alphabet());
        LinkedOtfDucsController.State<String, String, String, String> omittedSource =
                LinkedOtfDucsController.State.<String, String, String, String>post("p0");
        for (Map.Entry<LinkedOtfDucsController.State<String, String, String, String>,
                Map<String, Set<LinkedOtfDucsController.State<String, String, String, String>>>>
                stateEntry : original.transitions().entrySet()) {
            for (Map.Entry<String,
                    Set<LinkedOtfDucsController.State<String, String, String, String>>>
                    actionEntry : stateEntry.getValue().entrySet()) {
                if (stateEntry.getKey().equals(omittedSource)
                        && actionEntry.getKey().equals("tick")) {
                    continue;
                }
                for (LinkedOtfDucsController.State<String, String, String, String> target
                        : actionEntry.getValue()) {
                    mutantLts.addTransition(
                            stateEntry.getKey(), actionEntry.getKey(), target);
                }
            }
        }
        LinkedOtfDucsController<String, String, String, String> missingPostEdge =
                new LinkedOtfDucsController<String, String, String, String>(
                        mutantLts.build(), linked.controllableActions(),
                        linked.quotientTargets(), linked.hotSwapInAction(),
                        linked.hotSwapOutBoundaryName());
        LinkedOtfDucsControllerChecker.VerificationReport mutantReport =
                new LinkedOtfDucsControllerChecker<String, String, String, String>().verify(
                        missingPostEdge, oldEndpoint, newEndpoint, problem, result,
                        oldProjection, newProjection);
        assertFalse(mutantReport.isValid());

        Function<String, InitialSnapshot<String, String>> transitionInconsistentProjection =
                new Function<String, InitialSnapshot<String, String>>() {
                    @Override
                    public InitialSnapshot<String, String> apply(String state) {
                        String swapped = state.equals("z0") ? "old1" : "old0";
                        return new InitialSnapshot<String, String>(
                                PhysicalState.of(TaggedState.oldState(swapped)),
                                Collections.<String, String>emptyMap());
                    }
                };
        boolean rejected = false;
        try {
            LinkedOtfDucsController.link(
                    oldEndpoint, newEndpoint, problem, result,
                    transitionInconsistentProjection, newProjection);
        } catch (IllegalStateException expected) {
            rejected = true;
        }
        assertTrue("Link must reject a state-complete but transition-inconsistent projection",
                rejected);
    }

    @Test(expectedExceptions = IllegalArgumentException.class)
    public void compactStateImportRejectsInternalTauTransitions() {
        FiniteLts<String> withTau = FiniteLts.<String>builder("s")
                .addTransition("s", "tau", "s")
                .build();
        FiniteLts.fromMtsa(withTau.toMtsa().toCompactState("TAU_INPUT"));
    }

    @Test(expectedExceptions = IllegalStateException.class)
    public void reachableGoalEnumerationCannotBeMixedWithManualGoals() {
        FiniteLts<String> endpoint = FiniteLts.<String>builder("p")
                .addTransition("p", "tick", "p")
                .build();
        FineGrainedUpdateProblem.Builder<String, String> builder =
                FineGrainedUpdateProblem.<String, String>builder();
        builder.goalSignaturesFromReachable(endpoint,
                new Function<String, GoalSignature<String, String>>() {
                    @Override
                    public GoalSignature<String, String> apply(String ignored) {
                        return new GoalSignature<String, String>(
                                "p", PhysicalState.of(TaggedState.newState("new")),
                                Collections.<String, String>emptyMap());
                    }
                });
        builder.addGoalSignature(new GoalSignature<String, String>(
                "invented", PhysicalState.of(TaggedState.newState("new")),
                Collections.<String, String>emptyMap()));
    }

    @Test
    public void canonicalComparatorDoesNotCollapseHashAndStringCollisions() {
        Colliding old0 = new Colliding(0);
        Colliding old1 = new Colliding(1);
        Colliding newer = new Colliding(2);
        FiniteLts<Colliding> oldLts = FiniteLts.<Colliding>builder(old0)
                .addState(old1)
                .build();
        VersionedComponent<Colliding> component = new VersionedComponent<Colliding>(
                "C", oldLts, singletonLts(newer),
                Collections.singletonMap(old0, Collections.singleton(newer)), "rho");
        FineGrainedUpdateProblem<Colliding, String> problem =
                FineGrainedUpdateProblem.<Colliding, String>builder()
                        .addComponent(component)
                        .addInitialSnapshot(new InitialSnapshot<Colliding, String>(
                                PhysicalState.of(TaggedState.oldState(old0)),
                                Collections.<String, String>emptyMap()))
                        .addGoalSignature(new GoalSignature<Colliding, String>(
                                "post", PhysicalState.of(TaggedState.newState(newer)),
                                Collections.<String, String>emptyMap()))
                        .build();
        FineGrainedSuccessorOracle<Colliding, String> oracle =
                new FineGrainedSuccessorOracle<Colliding, String>(problem);
        CanonicalUpdateConfiguration<Colliding, String> left =
                problem.initialConfigurations().get(0);
        CanonicalUpdateConfiguration<Colliding, String> right =
                CanonicalUpdateConfiguration.of(
                        PhysicalState.of(TaggedState.oldState(old1)),
                        Collections.<String, String>emptyMap(), setOf("rho"));

        assertNotEquals(0, oracle.stateComparator().compare(left, right));
    }

    private static VersionedComponent<String> component(
            String id,
            FiniteLts<String> oldLts,
            FiniteLts<String> newLts,
            String oldState,
            Set<String> transferTargets,
            String action) {
        return new VersionedComponent<String>(id, oldLts, newLts,
                Collections.singletonMap(oldState, transferTargets), action);
    }

    private static <S> FiniteLts<S> singletonLts(S state) {
        return FiniteLts.<S>builder(state).build();
    }

    private static SafetyTester<String> oneStateTester(String state) {
        return SafetyTester.<String>builder().initialState(state).build();
    }

    private static SafetyTester<String> badOn(String safe, String error, String action) {
        return SafetyTester.<String>builder()
                .initialState(safe)
                .addErrorState(error)
                .addTransition(safe, action, error)
                .addTransition(error, action, error)
                .build();
    }

    private static SafetyTester<String> recorderTester(String stop, String start) {
        SafetyTester.Builder<String> builder = SafetyTester.<String>builder()
                .initialState("interval0")
                .addStates(Arrays.asList(
                        "intervalStopped", "intervalStarted", "intervalBoth"));
        builder.addTransition("interval0", stop, "intervalStopped");
        builder.addTransition("interval0", start, "intervalStarted");
        builder.addTransition("intervalStopped", stop, "intervalStopped");
        builder.addTransition("intervalStopped", start, "intervalBoth");
        builder.addTransition("intervalStarted", stop, "intervalBoth");
        builder.addTransition("intervalStarted", start, "intervalStarted");
        builder.addTransition("intervalBoth", stop, "intervalBoth");
        builder.addTransition("intervalBoth", start, "intervalBoth");
        return builder.build();
    }

    private static TableResidualLanguage<String> emptyBadLanguage(
            Set<String> actions, String state) {
        TableResidualLanguage.Builder<String> builder =
                TableResidualLanguage.<String>builder().initialState(state).addActions(actions);
        for (String action : actions) {
            builder.addTransition(state, action, state);
        }
        return builder.build();
    }

    private static TableResidualLanguage<String> badOnResidual(
            Set<String> actions, String badAction, String safe, String error) {
        TableResidualLanguage.Builder<String> builder =
                TableResidualLanguage.<String>builder()
                        .initialState(safe)
                        .addErrorState(error)
                        .addActions(actions);
        for (String action : actions) {
            builder.addTransition(safe, action, action.equals(badAction) ? error : safe);
            builder.addTransition(error, action, error);
        }
        return builder.build();
    }

    private static <S, M> CanonicalUpdateConfiguration<S, M> only(
            Set<CanonicalUpdateConfiguration<S, M>> values) {
        assertEquals(1, values.size());
        return values.iterator().next();
    }

    private static <T> Set<T> setOf(T... values) {
        LinkedHashSet<T> result = new LinkedHashSet<T>();
        Collections.addAll(result, values);
        return result;
    }

    private static final class Colliding {
        private final int id;

        private Colliding(int id) {
            this.id = id;
        }

        @Override
        public boolean equals(Object other) {
            return other instanceof Colliding && id == ((Colliding) other).id;
        }

        @Override
        public int hashCode() {
            return 7;
        }

        @Override
        public String toString() {
            return "same";
        }
    }
}
