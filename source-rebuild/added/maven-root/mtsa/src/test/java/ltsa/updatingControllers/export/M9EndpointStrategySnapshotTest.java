package ltsa.updatingControllers.export;

import MTSSynthesis.controller.gr.StrategyState;
import MTSTools.ac.ic.doc.commons.relations.Pair;
import MTSTools.ac.ic.doc.mtstools.model.MTS;
import MTSTools.ac.ic.doc.mtstools.model.impl.MTSImpl;
import MTSTools.ac.ic.doc.mtstools.utils.GenericMTSToLongStringMTSConverter;
import ltsa.ac.ic.doc.mtstools.util.fsp.AutomataToMTSConverter;
import ltsa.ac.ic.doc.mtstools.util.fsp.MTSToAutomataConverter;
import ltsa.lts.CompactState;
import ltsa.lts.CompositeState;
import ltsa.lts.EmptyLTSOuput;
import ltsa.lts.Options;
import org.testng.annotations.AfterMethod;
import org.testng.annotations.BeforeMethod;
import org.testng.annotations.Test;

import java.io.ByteArrayOutputStream;
import java.lang.reflect.Constructor;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.attribute.PosixFilePermissions;
import java.security.MessageDigest;
import java.util.LinkedHashMap;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.Collections;
import java.util.Vector;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

public class M9EndpointStrategySnapshotTest {
    @BeforeMethod(alwaysRun = true)
    public void acquireNativeCompositionLock() {
        M9NativeCompositionTestLock.acquire();
    }

    @AfterMethod(alwaysRun = true)
    public void releaseNativeCompositionLock() {
        M9NativeCompositionTestLock.release();
    }

    @Test
    public void bindsNativeStrategyThroughPlantAndEnvironmentToEnew() {
        Fixture fixture = fixture(false);
        M9EndpointStrategySnapshot snapshot = M9EndpointStrategySnapshot.capture(
                fixture.nativeController, fixture.plainController,
                fixture.nativeToPlain, fixture.solverEnvironment,
				fixture.solverPlant, fixture.plantProjection,
                fixture.environmentPrefix, Collections.<String>emptySet(), 1, 0);
        assertEquals(fixture.plainController.getStates().size(),
                snapshot.getPlainStateCoordinates().size());
        assertEquals(snapshot.getPlainController().getStates(),
                snapshot.getControllerStateToEnewState().keySet());
        for (Map.Entry<StrategyState<Long, Integer>, Long> entry
                : fixture.nativeToPlain.entrySet()) {
            M9EndpointStrategySnapshot.StateCoordinates coordinates =
                    snapshot.getPlainStateCoordinates().get(entry.getValue());
            assertEquals(entry.getKey().getState().longValue(),
                    coordinates.getPlantState());
            assertEquals(entry.getKey().getMemory().intValue(),
                    coordinates.getMemory());
            assertEquals(entry.getKey().getLazyness().intValue(),
                    coordinates.getLaziness());
			Long environmentState = fixture.plantProjection
					.getFirstComponentSourceStates().get(entry.getKey().getState());
			Long expectedEnew = fixture.environmentPrefix
					.getExtendedStateToPrefixState().get(environmentState);
			assertEquals(expectedEnew.longValue(), coordinates.getEnewState());
			assertEquals(expectedEnew,
					snapshot.getControllerStateToEnewState().get(entry.getValue()));
        }
		try {
			snapshot.getControllerStateToEnewState().put(
					Long.valueOf(0L), Long.valueOf(99L));
			fail("Returned endpoint provenance must be immutable.");
		} catch (UnsupportedOperationException expected) {
			// Expected immutable boundary.
		}
    }

    @Test
    public void rejectsMissingDuplicateAndWrongInitialMappings() {
        Fixture missingFixture = fixture(false);
        Map<StrategyState<Long, Integer>, Long> missing =
                new LinkedHashMap<StrategyState<Long, Integer>, Long>(
                        missingFixture.nativeToPlain);
        StrategyState<Long, Integer> removed = null;
        for (StrategyState<Long, Integer> state : missing.keySet()) {
            if (!state.equals(missingFixture.nativeController.getInitialState())) {
                removed = state;
                break;
            }
        }
        missing.remove(removed);
        expectFailure(missingFixture, missing, "mapping domain");

        Fixture duplicateFixture = fixture(false);
        Map<StrategyState<Long, Integer>, Long> duplicate =
                new LinkedHashMap<StrategyState<Long, Integer>, Long>(
                        duplicateFixture.nativeToPlain);
        Long initialPlain = duplicate.get(
                duplicateFixture.nativeController.getInitialState());
        for (StrategyState<Long, Integer> state : duplicate.keySet()) {
            if (!state.equals(duplicateFixture.nativeController.getInitialState())) {
                duplicate.put(state, initialPlain);
                break;
            }
        }
        expectFailure(duplicateFixture, duplicate, "noninjective");

        Fixture initialFixture = fixture(false);
        Map<StrategyState<Long, Integer>, Long> wrongInitial =
                new LinkedHashMap<StrategyState<Long, Integer>, Long>(
                        initialFixture.nativeToPlain);
        StrategyState<Long, Integer> initial =
                initialFixture.nativeController.getInitialState();
        StrategyState<Long, Integer> other = null;
        for (StrategyState<Long, Integer> state : wrongInitial.keySet()) {
            if (!state.equals(initial)) {
                other = state;
                break;
            }
        }
        Long initialValue = wrongInitial.get(initial);
        wrongInitial.put(initial, wrongInitial.get(other));
        wrongInitial.put(other, initialValue);
        expectFailure(initialFixture, wrongInitial, "initial-preserving");
    }

    @Test
    public void rejectsRawPlainPostDriftMaybeAndMissingPlantProvenance() {
        Fixture plainDrift = fixture(false);
        Pair<String, Long> edge = plainDrift.plainController.getTransitions(
                Long.valueOf(0L), MTS.TransitionType.REQUIRED).iterator().next();
        plainDrift.plainController.removeRequired(
                Long.valueOf(0L), edge.getFirst(), edge.getSecond());
        expectFailure(plainDrift, plainDrift.nativeToPlain, "Post differ");

        Fixture maybe = fixture(false);
        StrategyState<Long, Integer> nativeInitial =
                maybe.nativeController.getInitialState();
        Pair<String, StrategyState<Long, Integer>> nativeEdge =
                maybe.nativeController.getTransitions(
                        nativeInitial, MTS.TransitionType.REQUIRED).iterator().next();
        maybe.nativeController.removeRequired(
                nativeInitial, nativeEdge.getFirst(), nativeEdge.getSecond());
        maybe.nativeController.addPossible(
                nativeInitial, nativeEdge.getFirst(), nativeEdge.getSecond());
        expectFailure(maybe, maybe.nativeToPlain, "MAYBE");

        Fixture outside = fixture(true);
        expectFailure(outside, outside.nativeToPlain, "plant Post edge");
    }

	@Test
	public void rejectsLegacyRewriteAndActualAuthorityDrift() {
		Fixture rewrite = fixture(false);
		expectFailure(rewrite, rewrite.nativeToPlain,
				Collections.singleton("a"), 1, 0,
				"Legacy controller self-loop rewriting");

		Fixture environmentDrift = fixture(false);
		environmentDrift.solverEnvironment.addAction("extra");
		expectFailure(environmentDrift, environmentDrift.nativeToPlain,
				Collections.<String>emptySet(), 1, 0,
				"declarations changed");

		Fixture plantDrift = fixture(false);
		plantDrift.solverPlant.addAction("extra");
		expectFailure(plantDrift, plantDrift.nativeToPlain,
				Collections.<String>emptySet(), 1, 0,
				"declarations changed");

		Fixture actual = fixture(false, "a");
		Fixture unrelated = fixture(false, "b");
		try {
			M9EndpointStrategySnapshot.capture(
					actual.nativeController, actual.plainController,
					actual.nativeToPlain, actual.solverEnvironment,
					actual.solverPlant, actual.plantProjection,
					unrelated.environmentPrefix,
					Collections.<String>emptySet(), 1, 0);
			fail("Same-domain unrelated prefix authority must be rejected.");
		} catch (IllegalArgumentException expected) {
			assertTrue(expected.getMessage(),
					expected.getMessage().contains("declarations changed"));
		}
	}

	@Test
	public void rejectsInitialMemoryLazinessAndUnreachableProfiles() {
		Fixture rerooted = fixture(false);
		StrategyState<Long, Integer> oldInitial =
				rerooted.nativeController.getInitialState();
		StrategyState<Long, Integer> other = null;
		for (StrategyState<Long, Integer> state
				: rerooted.nativeController.getStates()) {
			if (!state.equals(oldInitial)) {
				other = state;
				break;
			}
		}
		Long oldInitialId = rerooted.nativeToPlain.get(oldInitial);
		Long otherId = rerooted.nativeToPlain.get(other);
		rerooted.nativeController.setInitialState(other);
		rerooted.nativeToPlain.put(other, oldInitialId);
		rerooted.nativeToPlain.put(oldInitial, otherId);
		expectFailure(rerooted, rerooted.nativeToPlain,
				Collections.<String>emptySet(), 1, 0,
				"registered GR profile");

		Fixture badMemory = remapNonInitialCoordinate(fixture(false), 2, 0, false);
		expectFailure(badMemory, badMemory.nativeToPlain,
				Collections.<String>emptySet(), 1, 0,
				"memory/laziness");

		Fixture badLaziness = remapNonInitialCoordinate(
				fixture(false), 1, 1, false);
		expectFailure(badLaziness, badLaziness.nativeToPlain,
				Collections.<String>emptySet(), 1, 0,
				"memory/laziness");

		Fixture unreachable = remapNonInitialCoordinate(
				fixture(false), 1, 0, true);
		expectFailure(unreachable, unreachable.nativeToPlain,
				Collections.<String>emptySet(), 2, 0,
				"unreachable state");
	}

	@Test
	public void rejectsConsistentWrongPlantEdgeAndAlphabetMutants() {
		Fixture wrongEdge = fixture(false);
		StrategyState<Long, Integer> initial =
				wrongEdge.nativeController.getInitialState();
		Pair<String, StrategyState<Long, Integer>> original =
				wrongEdge.nativeController.getTransitions(
						initial, MTS.TransitionType.REQUIRED).iterator().next();
		wrongEdge.nativeController.removeRequired(
				initial, original.getFirst(), original.getSecond());
		wrongEdge.nativeController.addRequired(
				initial, original.getFirst(), initial);
		wrongEdge = reconvertNative(wrongEdge);
		expectFailure(wrongEdge, wrongEdge.nativeToPlain, "plant Post edge");

		Fixture missingAction = fixture(false);
		for (StrategyState<Long, Integer> state
				: missingAction.nativeController.getStates()) {
			List<Pair<String, StrategyState<Long, Integer>>> transitions =
					new ArrayList<Pair<String, StrategyState<Long, Integer>>>();
			for (Pair<String, StrategyState<Long, Integer>> transition
					: missingAction.nativeController.getTransitions(
							state, MTS.TransitionType.REQUIRED)) {
				transitions.add(transition);
			}
			for (Pair<String, StrategyState<Long, Integer>> transition
					: transitions) {
				missingAction.nativeController.removeRequired(
						state, transition.getFirst(), transition.getSecond());
			}
		}
		missingAction.nativeController.removeAction("a");
		missingAction = reconvertNative(missingAction);
		expectFailure(missingAction, missingAction.nativeToPlain,
				"omits a registered plant action");

			Fixture declaredAlias = fixture(false);
			declaredAlias.nativeController.addAction("#w#_a");
			declaredAlias = reconvertNative(declaredAlias);
			expectFailure(declaredAlias, declaredAlias.nativeToPlain,
					"rank aliases are outside");

			Fixture enabledAlias = fixture(false);
			StrategyState<Long, Integer> aliasInitial =
					enabledAlias.nativeController.getInitialState();
			Pair<String, StrategyState<Long, Integer>> aliasEdge =
					enabledAlias.nativeController.getTransitions(
						aliasInitial, MTS.TransitionType.REQUIRED).iterator().next();
			enabledAlias.nativeController.removeRequired(
					aliasInitial, aliasEdge.getFirst(), aliasEdge.getSecond());
			enabledAlias.nativeController.addAction("#w#_a");
			enabledAlias.nativeController.addRequired(
					aliasInitial, "#w#_a", aliasEdge.getSecond());
			enabledAlias = reconvertNative(enabledAlias);
			expectFailure(enabledAlias, enabledAlias.nativeToPlain,
					"rank aliases are outside");
		}

	@Test
	public void materializesExactCnewAndClosedLoopWithoutAnotherSolver() {
		Fixture fixture = fixture(false);
		M9EndpointStrategySnapshot strategy =
				M9EndpointStrategySnapshot.capture(
						fixture.nativeController, fixture.plainController,
						fixture.nativeToPlain, fixture.solverEnvironment,
						fixture.solverPlant, fixture.plantProjection,
						fixture.environmentPrefix,
						Collections.<String>emptySet(), 1, 0);
		CompactStateEndpointAdmission.Admission enewAdmission =
				CompactStateEndpointAdmission.admitComposed(
						fixture.enewEndpoint,
						fixture.environmentPrefix.getPrefixProductAuthority(), false);
		CompactState cnew = MTSToAutomataConverter.getInstance().convert(
				fixture.plainController, "Cnew", true);
		M9ClosedLoopEndpointSnapshot endpoint =
				M9ClosedLoopEndpointSnapshot.capture(
						fixture.enewEndpoint, enewAdmission, cnew, strategy);
		assertTrue(endpoint.getCnewAdmission().isComposed() == false);
		assertTrue(endpoint.getClosedLoopAdmission().isComposed());
		assertEquals("M9_CLNEW",
				endpoint.getClosedLoopAdmission().getSnapshot().getName());
		assertEquals(Integer.valueOf(2), Integer.valueOf(
				endpoint.getClosedLoopAuthority().getComponentTrees().size()));
		assertEquals(endpoint.getClosedLoopAuthority().getProductSnapshot()
				.getStates(), endpoint.getCoordinates()
				.getProductStateCoordinates().keySet());
		assertEquals(strategy.getControllerStateToEnewState(),
				endpoint.getCoordinates().getSecondStateToFirstState());
		String retainedEnewName = endpoint.getEnewAdmission()
				.getSnapshot().getName();
		String retainedCnewName = endpoint.getCnewAdmission()
				.getSnapshot().getName();
		fixture.enewEndpoint.name = "mutated-after-capture";
		cnew.name = "mutated-after-capture";
		assertEquals(retainedEnewName,
				endpoint.getEnewAdmission().getSnapshot().getName());
		assertEquals(retainedCnewName,
				endpoint.getCnewAdmission().getSnapshot().getName());
	}

	@Test
	public void rejectsSubstitutedEnewAndCnewBytesBeforePublication() {
		Fixture fixture = fixture(false);
		M9EndpointStrategySnapshot strategy =
				M9EndpointStrategySnapshot.capture(
						fixture.nativeController, fixture.plainController,
						fixture.nativeToPlain, fixture.solverEnvironment,
						fixture.solverPlant, fixture.plantProjection,
						fixture.environmentPrefix,
						Collections.<String>emptySet(), 1, 0);
		CompactStateEndpointAdmission.Admission enewAdmission =
				CompactStateEndpointAdmission.admitComposed(
						fixture.enewEndpoint,
						fixture.environmentPrefix.getPrefixProductAuthority(), false);

		CompactState wrongCnew = MTSToAutomataConverter.getInstance().convert(
				cycle("b"), "Cnew", true);
		try {
			M9ClosedLoopEndpointSnapshot.capture(
					fixture.enewEndpoint, enewAdmission, wrongCnew, strategy);
			fail("Substituted Cnew bytes must be rejected.");
		} catch (IllegalArgumentException expected) {
			assertTrue(expected.getMessage(),
					expected.getMessage().contains("Cnew alphabet"));
		}

		CompactState correctCnew = MTSToAutomataConverter.getInstance().convert(
				fixture.plainController, "Cnew", true);
		CompactState duplicateRoleCnew = MTSToAutomataConverter.getInstance().convert(
				fixture.plainController, fixture.enewEndpoint.getName(), true);
		try {
			M9ClosedLoopEndpointSnapshot.capture(
					fixture.enewEndpoint, enewAdmission,
					duplicateRoleCnew, strategy);
			fail("Duplicate Enew/Cnew role names must be rejected before composition.");
		} catch (IllegalArgumentException expected) {
			assertTrue(expected.getMessage(),
					expected.getMessage().contains("distinct direct-child"));
		}
		try {
			M9ClosedLoopEndpointSnapshot.capture(
					correctCnew, enewAdmission, correctCnew, strategy);
			fail("Substituted Enew bytes must be rejected.");
		} catch (IllegalArgumentException expected) {
			assertTrue(expected.getMessage(),
			expected.getMessage().contains("Enew bytes"));
		}

		Options.setCompositionStrategyClass(
				Options.CompositionStrategy.RANDOM_STRATEGY);
		try {
			M9ClosedLoopEndpointSnapshot.capture(
					fixture.enewEndpoint, enewAdmission, correctCnew, strategy);
			fail("Unregistered native composition strategy must be rejected.");
		} catch (IllegalArgumentException expected) {
			assertTrue(expected.getMessage(),
					expected.getMessage().contains("DFS/no-POR/no-threshold"));
		} finally {
			Options.setCompositionStrategyClass(
					Options.CompositionStrategy.DFS_STRATEGY);
		}
	}

	@Test
	public void canonicalReceiptCoreBindsEveryImmutableEndpointSection()
			throws Exception {
		M9CombinedReceiptTestFixture combined =
				M9CombinedReceiptTestFixture.create();

		M9EndpointReceiptCore first = M9EndpointReceiptCore.capture(
				receiptBindings("synthetic_case_a"), combined.strategy,
				combined.closedLoop, combined.traditional);
		M9EndpointReceiptCore second = M9EndpointReceiptCore.capture(
				receiptBindings("synthetic_case_a"), combined.strategy,
				combined.closedLoop, combined.traditional);
		assertArrayEquals(first.getCanonicalCoreBytes(),
				second.getCanonicalCoreBytes());
		assertArrayEquals(first.getCanonicalCoreSha256(),
				second.getCanonicalCoreSha256());
		Map<Long, Long> nonInjectivePrefix = combined.strategy
				.getEnvironmentPrefix().getExtendedStateToPrefixState();
		assertTrue(new java.util.LinkedHashSet<Long>(
				nonInjectivePrefix.values()).size() < nonInjectivePrefix.size());
		long handoffRows = 0L;
		boolean observedNonInjectiveFiber = false;
		for (Map.Entry<Long, List<
				M9TraditionalCompletionHandoffSnapshot.CompletionCoordinates>> entry
				: first.getCompletionHandoff().getCompletionStates().entrySet()) {
			List<M9TraditionalCompletionHandoffSnapshot.CompletionCoordinates> rows =
					entry.getValue();
			handoffRows += rows.size();
			Long expectedUpdating = combined.traditional
					.getSafetyStateToUpdatingState().get(entry.getKey());
			Long expectedPruned = combined.traditional
					.getSafetyStateToPrunedState().get(entry.getKey());
			Long expectedMapping = combined.traditional.getUpdatingProvenance()
					.getUpdatingStateToMappingState().get(expectedUpdating);
			Long expectedEnew = combined.traditional.getCompletionSeed()
					.getMappingProductToNew().get(expectedMapping);
			Set<Long> expectedCnewStates = new java.util.LinkedHashSet<Long>();
			for (Map.Entry<Long, Long> origin : combined.strategy
					.getControllerStateToEnewState().entrySet()) {
				if (expectedEnew.equals(origin.getValue())) {
					expectedCnewStates.add(origin.getKey());
				}
			}
			observedNonInjectiveFiber |= expectedCnewStates.size() > 1;
			Set<Long> actualCnewStates = new java.util.LinkedHashSet<Long>();
			for (M9TraditionalCompletionHandoffSnapshot.CompletionCoordinates row
					: rows) {
				assertEquals(expectedPruned.longValue(), row.getPrunedState());
				assertEquals(expectedPruned.longValue(), row.getMetaState());
				assertEquals(expectedUpdating.longValue(), row.getUpdatingState());
				assertEquals(expectedMapping.longValue(), row.getMappingState());
				assertEquals(expectedEnew.longValue(), row.getEnewState());
				M9EndpointStrategySnapshot.StateCoordinates cnew = combined.strategy
						.getPlainStateCoordinates().get(Long.valueOf(row.getCnewState()));
				Long solverEnvironment = combined.strategy.getPlantComposition()
						.getFirstComponentSourceStates().get(
								Long.valueOf(cnew.getPlantState()));
				assertEquals(solverEnvironment.longValue(),
						row.getSolverEnvironmentState());
				M9CompositionProvenance.SourceCoordinates closed = combined.closedLoop
						.getCoordinates().getProductStateCoordinates().get(
								Long.valueOf(row.getClosedLoopState()));
				assertEquals(row.getEnewState(), closed.getFirstSourceState());
				assertEquals(row.getCnewState(), closed.getSecondSourceState());
				actualCnewStates.add(Long.valueOf(row.getCnewState()));
			}
			assertEquals(expectedCnewStates, actualCnewStates);
		}
		assertTrue("Non-injective Enew fibers must retain every typed candidate.",
				handoffRows > first.getCompletionHandoff()
						.getCompletionStates().size());
		assertTrue("The fixture must exercise a non-injective Enew fiber.",
				observedNonInjectiveFiber);
		assertEquals(Integer.valueOf(3), Integer.valueOf(first.getSections().size()));
		assertEquals(Arrays.asList(
				M9EndpointReceiptCore.STRATEGY_SECTION,
				M9EndpointReceiptCore.CLOSED_LOOP_SECTION,
				M9EndpointReceiptCore.TRADITIONAL_SECTION),
				Arrays.asList(
						first.getSections().get(0).getName(),
						first.getSections().get(1).getName(),
						first.getSections().get(2).getName()));
		for (M9EndpointReceiptCore.SectionDescriptor section : first.getSections()) {
			ByteArrayOutputStream output = new ByteArrayOutputStream();
			first.writeCanonicalSection(section.getName(), output);
			byte[] bytes = output.toByteArray();
			assertEquals(Long.valueOf(bytes.length),
					Long.valueOf(section.getSizeBytes()));
			assertArrayEquals(MessageDigest.getInstance("SHA-256").digest(bytes),
					section.getContentSha256());
			assertArrayEquals(fixedJavaSectionVector(section.getName()), bytes);
		}

		byte[] escapedCore = first.getCanonicalCoreBytes();
		escapedCore[0] ^= 1;
		assertTrue(!Arrays.equals(escapedCore, first.getCanonicalCoreBytes()));
		byte[] escapedDigest = first.getCanonicalCoreSha256();
		escapedDigest[0] ^= 1;
		assertTrue(!Arrays.equals(escapedDigest, first.getCanonicalCoreSha256()));

		M9EndpointReceiptCore otherCase = M9EndpointReceiptCore.capture(
				receiptBindings("synthetic_case_b"), combined.strategy,
				combined.closedLoop, combined.traditional);
		assertTrue(!Arrays.equals(first.getCanonicalCoreSha256(),
				otherCase.getCanonicalCoreSha256()));

		Map<String, String> missing = receiptHashes();
		missing.remove("t1_seal_sha256");
		try {
			M9EndpointReceiptCore.Bindings.capture(
					"synthetic_case_a", "synthetic_cluster", "attempt-0001",
					"POSITIVE_SOURCE_DEFINED_UPDATE", "UAV_NATIVE_ENDPOINT",
					"M9_UAV_EXACT_V1", 5L, 1234L, missing);
			fail("Missing receipt binding must be rejected.");
		} catch (IllegalArgumentException expected) {
			assertTrue(expected.getMessage(),
					expected.getMessage().contains("key census"));
		}
	}

	@Test
	public void rejectsEnabledTauInLifecycleCompletionMonitor()
			throws Exception {
		CompactState monitor = new CompactState("LIFECYCLE_TAU");
		monitor.maxStates = 4;
		monitor.alphabet = new String[]{
				"tau", ltsa.updatingControllers.UpdateConstants.STOP_OLD_SPEC,
				ltsa.updatingControllers.UpdateConstants.RECONFIGURE,
				ltsa.updatingControllers.UpdateConstants.START_NEW_SPEC, "a"};
		monitor.states = new ltsa.lts.EventState[4];
		for (int state = 0; state < 4; state++) {
			monitor.states[state] = ltsa.lts.EventStateUtils.add(
					monitor.states[state], new ltsa.lts.EventState(4, state));
			for (int action = 1; action <= 3; action++) {
				int target = action - 1 == state && state < 3 ? state + 1 : -1;
				monitor.states[state] = ltsa.lts.EventStateUtils.add(
						monitor.states[state], new ltsa.lts.EventState(action, target));
			}
		}
		monitor.states[0] = ltsa.lts.EventStateUtils.add(
				monitor.states[0], new ltsa.lts.EventState(0, 0));
		java.lang.reflect.Method validator =
				M9TraditionalCompletionHandoffSnapshot.class.getDeclaredMethod(
						"requireLifecycleCompleteCoordinate",
						CompactStateCanonicalSnapshot.class, List.class);
		validator.setAccessible(true);
		try {
			validator.invoke(null, CompactStateCanonicalSnapshot.fromRaw(monitor),
					Arrays.asList(
							ltsa.updatingControllers.UpdateConstants.STOP_OLD_SPEC,
							ltsa.updatingControllers.UpdateConstants.RECONFIGURE,
							ltsa.updatingControllers.UpdateConstants.START_NEW_SPEC));
			fail("An enabled lifecycle tau transition must be rejected.");
		} catch (java.lang.reflect.InvocationTargetException expected) {
			assertTrue(expected.getCause() instanceof IllegalArgumentException);
			assertTrue(expected.getCause().getMessage(),
					expected.getCause().getMessage().contains(
							"enabled tau transition"));
		}
	}

	@Test
	public void publishesOneCanonicalBundleAndConsumesSealAndTarget()
			throws Exception {
		M9CombinedReceiptTestFixture combined =
				M9CombinedReceiptTestFixture.create();
		M9EndpointReceiptCore core = M9EndpointReceiptCore.capture(
				receiptBindings("synthetic_case_a"), combined.strategy,
				combined.closedLoop, combined.traditional);
		M9EndpointSynthesisHook.SealedAttempt sealed =
				syntheticPublicationSeal(core);
		TraditionalPreGrSnapshotHook.SealedCapture traditionalSeal =
				M9CombinedReceiptTestFixture.sealed(combined.traditional);

		Path testOutput = Paths.get("target").toAbsolutePath().normalize();
		Path base = Files.createTempDirectory(testOutput, "m9-endpoint-bundle-");
		Path caseDirectory = base.resolve("synthetic_case_a");
		Files.createDirectory(caseDirectory);
		Files.setPosixFilePermissions(
				caseDirectory, PosixFilePermissions.fromString("rwx------"));
		Path pending = caseDirectory.resolve("endpoint-receipt.bundle.pending");
		Path destination = caseDirectory.resolve("endpoint-receipt.bundle");
		try {
			M9EndpointReceiptBundle.PublicationTarget target =
					M9EndpointReceiptBundle.prepare(
							pending, destination, "synthetic_case_a", "attempt-0001",
							receiptHashes().get("attempt_claim_sha256"));
			M9EndpointReceiptBundle.PublishedReceipt published =
					M9EndpointReceiptBundle.publish(
							core, sealed, traditionalSeal, target);
			assertTrue(Files.isSameFile(pending, destination));
			byte[] container = Files.readAllBytes(destination);
			assertArrayEquals(fixedJavaCombinedBundleVector(), container);
			assertArrayEquals("M9EPRC02".getBytes("US-ASCII"),
					Arrays.copyOfRange(container, 0, 8));
			assertEquals(Integer.valueOf(2), Integer.valueOf(
					java.nio.ByteBuffer.wrap(container, 8, 4).getInt()));
			assertEquals(Integer.valueOf(3), Integer.valueOf(
					java.nio.ByteBuffer.wrap(container, 28, 4).getInt()));
			long coreSize = java.nio.ByteBuffer.wrap(container, 12, 8).getLong();
			long sealSize = java.nio.ByteBuffer.wrap(container, 20, 8).getLong();
			String sealJson = new String(
					container, (int) (32L + coreSize), (int) sealSize, "US-ASCII");
			assertTrue(sealJson.contains(
					"\"schema_version\":\"m9-endpoint-receipt-seal-v2\""));
			assertTrue(sealJson.contains(
					"\"traditional_pre_gr\":{\"attempt_consumed\":true,"));
			assertEquals(Long.valueOf(container.length),
					Long.valueOf(published.getSizeBytes()));
			assertArrayEquals(MessageDigest.getInstance("SHA-256").digest(container),
					published.getSha256());
			byte[] prefix = Arrays.copyOf(container, container.length - 32);
			byte[] trailer = Arrays.copyOfRange(
					container, container.length - 32, container.length);
			assertArrayEquals(MessageDigest.getInstance("SHA-256").digest(prefix),
					trailer);

			try {
				M9EndpointReceiptBundle.publish(
						core, syntheticPublicationSeal(core),
						M9CombinedReceiptTestFixture.sealed(combined.traditional), target);
				fail("A publication target must be consumed exactly once.");
			} catch (IllegalStateException expected) {
				assertTrue(expected.getMessage(),
						expected.getMessage().contains("target was already consumed"));
			}

			Path secondBase = Files.createTempDirectory(
					testOutput, "m9-endpoint-bundle-second-");
			Path secondCase = secondBase.resolve("synthetic_case_a");
			Files.createDirectory(secondCase);
			Files.setPosixFilePermissions(
					secondCase, PosixFilePermissions.fromString("rwx------"));
			try {
				M9EndpointReceiptBundle.PublicationTarget secondTarget =
						M9EndpointReceiptBundle.prepare(
								secondCase.resolve("endpoint-receipt.bundle.pending"),
								secondCase.resolve("endpoint-receipt.bundle"),
								"synthetic_case_a", "attempt-0001",
								receiptHashes().get("attempt_claim_sha256"));
				try {
					M9EndpointReceiptBundle.publish(
							core, sealed,
							M9CombinedReceiptTestFixture.sealed(combined.traditional),
							secondTarget);
					fail("A sealed attempt must authorize exactly one publication.");
				} catch (IllegalStateException expected) {
					assertTrue(expected.getMessage(),
							expected.getMessage().contains("already used for publication"));
				}
			} finally {
				Files.deleteIfExists(secondCase);
				Files.deleteIfExists(secondBase);
			}

			Path thirdBase = Files.createTempDirectory(
					testOutput, "m9-endpoint-bundle-third-");
			Path thirdCase = thirdBase.resolve("synthetic_case_a");
			Files.createDirectory(thirdCase);
			Files.setPosixFilePermissions(
					thirdCase, PosixFilePermissions.fromString("rwx------"));
			try {
				M9EndpointReceiptBundle.PublicationTarget thirdTarget =
						M9EndpointReceiptBundle.prepare(
								thirdCase.resolve("endpoint-receipt.bundle.pending"),
								thirdCase.resolve("endpoint-receipt.bundle"),
								"synthetic_case_a", "attempt-0001",
								receiptHashes().get("attempt_claim_sha256"));
				try {
					M9EndpointReceiptBundle.publish(
							core, syntheticPublicationSeal(core),
							traditionalSeal, thirdTarget);
					fail("A traditional pre-GR seal must authorize one publication.");
				} catch (IllegalStateException expected) {
					assertTrue(expected.getMessage(), expected.getMessage().contains(
							"already used for combined publication"));
				}
			} finally {
				Files.deleteIfExists(thirdCase);
				Files.deleteIfExists(thirdBase);
			}
		} finally {
			Files.deleteIfExists(destination);
			Files.deleteIfExists(pending);
			Files.deleteIfExists(caseDirectory);
			Files.deleteIfExists(base);
		}
	}

	private static byte[] fixedJavaSectionVector(String section) throws Exception {
		String filename;
		if (M9EndpointReceiptCore.STRATEGY_SECTION.equals(section)) {
			filename = "m9-strategy-v2-java-vector.b64";
		} else if (M9EndpointReceiptCore.CLOSED_LOOP_SECTION.equals(section)) {
			filename = "m9-closed-loop-v2-java-vector.b64";
		} else if (M9EndpointReceiptCore.TRADITIONAL_SECTION.equals(section)) {
			filename = "m9-traditional-v2-java-vector.b64";
		} else {
			throw new IllegalArgumentException("Unknown fixed Java section: " + section);
		}
		Path workspace = Paths.get("../../../..").toAbsolutePath().normalize();
		byte[] encoded = Files.readAllBytes(workspace.resolve(
				"Implementation/Experiment/FSE2027/tests/fixtures/" + filename));
		return java.util.Base64.getMimeDecoder().decode(encoded);
	}

	private static byte[] fixedJavaCombinedBundleVector() throws Exception {
		Path workspace = Paths.get("../../../..").toAbsolutePath().normalize();
		byte[] encoded = Files.readAllBytes(workspace.resolve(
				"Implementation/Experiment/FSE2027/tests/fixtures/"
				+ "m9-combined-v2-java-bundle.b64"));
		return java.util.Base64.getMimeDecoder().decode(encoded);
	}

	private static M9EndpointSynthesisHook.SealedAttempt
			syntheticPublicationSeal(M9EndpointReceiptCore core) throws Exception {
		Constructor<M9EndpointSynthesisHook.SealedAttempt> constructor =
				M9EndpointSynthesisHook.SealedAttempt.class.getDeclaredConstructor(
						Integer.TYPE, Integer.TYPE, Integer.TYPE,
						Boolean.TYPE, Boolean.TYPE, byte[].class);
		constructor.setAccessible(true);
		return constructor.newInstance(
				Integer.valueOf(1), Integer.valueOf(1), Integer.valueOf(0),
				Boolean.TRUE, Boolean.TRUE, core.getCanonicalCoreSha256());
	}

	private static M9EndpointReceiptCore.Bindings receiptBindings(String caseId) {
		return M9EndpointReceiptCore.Bindings.capture(
				caseId, "synthetic_cluster", "attempt-0001",
				"POSITIVE_SOURCE_DEFINED_UPDATE", "UAV_NATIVE_ENDPOINT",
				"M9_UAV_EXACT_V1", 5L, 1234L, receiptHashes());
	}

	private static Map<String, String> receiptHashes() {
		Map<String, String> result = new LinkedHashMap<String, String>();
		for (String key : M9EndpointReceiptCore.Bindings
				.requiredSha256BindingKeys()) {
			result.put(key,
					"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef");
		}
		return result;
	}

    private static void expectFailure(
            Fixture fixture,
            Map<StrategyState<Long, Integer>, Long> mapping,
            String fragment) {
		expectFailure(fixture, mapping, Collections.<String>emptySet(),
				1, 0, fragment);
	}

	private static void expectFailure(
			Fixture fixture,
			Map<StrategyState<Long, Integer>, Long> mapping,
			Set<String> legacyRewriteActions,
			int guaranteeCount,
			int maxLaziness,
			String fragment) {
        try {
            M9EndpointStrategySnapshot.capture(
                    fixture.nativeController, fixture.plainController, mapping,
                    fixture.solverEnvironment, fixture.solverPlant,
					fixture.plantProjection, fixture.environmentPrefix,
					legacyRewriteActions, guaranteeCount, maxLaziness);
            fail("Expected endpoint strategy rejection containing " + fragment);
        } catch (IllegalArgumentException expected) {
            assertTrue(expected.getMessage(),
                    expected.getMessage().contains(fragment));
        }
    }

    private static Fixture fixture(boolean replaceOnePlantState) {
		return fixture(replaceOnePlantState, "a");
	}

	private static Fixture fixture(
			boolean replaceOnePlantState,
			String action) {
		MTS<Long, String> first = cycle(action);
		MTS<Long, String> second = cycle(action);
		MTS<Long, String> safety = cycle(action);
		MTS<Long, String> fluent = cycle(action);

        CompositeState enew = compose(new MTS[]{first, second},
                new String[]{"enew-first", "enew-second"});
        MTS<Long, String> enewMts = AutomataToMTSConverter.getInstance()
                .convert(enew.composition);
        M9CompositionProvenance.Projection enewProjection =
                M9CompositionProvenance.capture(enewMts, first);

        CompositeState solverEnvironment = compose(
                new MTS[]{first, second, safety},
                new String[]{"enew-first", "enew-second", "safety"});
        MTS<Long, String> solverEnvironmentMts =
                AutomataToMTSConverter.getInstance()
                        .convert(solverEnvironment.composition);
        M9CompositionProvenance.Projection solverEnvironmentProjection =
                M9CompositionProvenance.capture(solverEnvironmentMts, first);
        M9CompositionProvenance.OrderedPrefixProjection environmentPrefix =
                M9CompositionProvenance.projectOrderedPrefix(
                        solverEnvironmentProjection, enewProjection);

        Vector<CompactState> plantMachines = new Vector<CompactState>();
        plantMachines.add(solverEnvironment.composition);
        plantMachines.add(MTSToAutomataConverter.getInstance().convert(
                fluent, "fluent", true));
        CompositeState plant = new CompositeState(plantMachines);
        plant.compose(new EmptyLTSOuput());
        MTS<Long, String> plantMts = AutomataToMTSConverter.getInstance()
                .convert(plant.composition);
        M9CompositionProvenance.Projection plantProjection =
                M9CompositionProvenance.capture(
                        plantMts, solverEnvironmentMts);

        Map<Long, StrategyState<Long, Integer>> strategyStates =
                new LinkedHashMap<Long, StrategyState<Long, Integer>>();
        for (Long plantState : plantMts.getStates()) {
            long represented = replaceOnePlantState
                    && !plantState.equals(plantMts.getInitialState())
                    ? 9999L : plantState.longValue();
            strategyStates.put(plantState,
                    new StrategyState<Long, Integer>(
							Long.valueOf(represented), Integer.valueOf(1),
                            Integer.valueOf(0)));
        }
        MTS<StrategyState<Long, Integer>, String> nativeController =
                new MTSImpl<StrategyState<Long, Integer>, String>(
                        strategyStates.get(plantMts.getInitialState()));
        nativeController.addStates(strategyStates.values());
        nativeController.addActions(plantMts.getActions());
        for (Long state : plantMts.getStates()) {
            for (Pair<String, Long> transition : plantMts.getTransitions(
                    state, MTS.TransitionType.REQUIRED)) {
                nativeController.addRequired(strategyStates.get(state),
                        transition.getFirst(),
                        strategyStates.get(transition.getSecond()));
            }
        }
        GenericMTSToLongStringMTSConverter<
                StrategyState<Long, Integer>, String> converter =
                new GenericMTSToLongStringMTSConverter<
                        StrategyState<Long, Integer>, String>();
        MTS<Long, String> plain = converter.transform(nativeController);
		return new Fixture(nativeController, plain,
                new LinkedHashMap<StrategyState<Long, Integer>, Long>(
                        converter.getStateMapping()),
				solverEnvironmentMts, plantMts, enew.composition,
				plantProjection, environmentPrefix);
    }

	private static Fixture remapNonInitialCoordinate(
			Fixture source,
			int nonInitialMemory,
			int nonInitialLaziness,
			boolean addDisconnected) {
		StrategyState<Long, Integer> oldInitial =
				source.nativeController.getInitialState();
		Map<StrategyState<Long, Integer>, StrategyState<Long, Integer>> replacements =
				new LinkedHashMap<StrategyState<Long, Integer>,
						StrategyState<Long, Integer>>();
		for (StrategyState<Long, Integer> state
				: source.nativeController.getStates()) {
			boolean initial = state.equals(oldInitial);
			replacements.put(state, new StrategyState<Long, Integer>(
					state.getState(), Integer.valueOf(initial ? 1 : nonInitialMemory),
					Integer.valueOf(initial ? 0 : nonInitialLaziness)));
		}
		MTS<StrategyState<Long, Integer>, String> replacement =
				new MTSImpl<StrategyState<Long, Integer>, String>(
						replacements.get(oldInitial));
		replacement.addStates(replacements.values());
		replacement.addActions(source.nativeController.getActions());
		for (StrategyState<Long, Integer> state
				: source.nativeController.getStates()) {
			for (Pair<String, StrategyState<Long, Integer>> transition
					: source.nativeController.getTransitions(
							state, MTS.TransitionType.REQUIRED)) {
				replacement.addRequired(replacements.get(state),
						transition.getFirst(), replacements.get(transition.getSecond()));
			}
		}
		if (addDisconnected) {
			replacement.addState(new StrategyState<Long, Integer>(
					oldInitial.getState(), Integer.valueOf(2), Integer.valueOf(0)));
		}
		return reconvertNative(new Fixture(
				replacement, source.plainController,
				Collections.<StrategyState<Long, Integer>, Long>emptyMap(),
				source.solverEnvironment, source.solverPlant,
				source.enewEndpoint,
				source.plantProjection, source.environmentPrefix));
	}

	private static Fixture reconvertNative(Fixture source) {
		GenericMTSToLongStringMTSConverter<
				StrategyState<Long, Integer>, String> converter =
				new GenericMTSToLongStringMTSConverter<
						StrategyState<Long, Integer>, String>();
		MTS<Long, String> plain = converter.transform(source.nativeController);
		return new Fixture(source.nativeController, plain,
				new LinkedHashMap<StrategyState<Long, Integer>, Long>(
						converter.getStateMapping()),
				source.solverEnvironment, source.solverPlant,
				source.enewEndpoint,
				source.plantProjection, source.environmentPrefix);
	}

    @SuppressWarnings("unchecked")
    private static CompositeState compose(MTS<Long, String>[] systems,
                                          String[] names) {
        Vector<CompactState> machines = new Vector<CompactState>();
        for (int index = 0; index < systems.length; index++) {
            machines.add(MTSToAutomataConverter.getInstance().convert(
                    systems[index], names[index], true));
        }
        CompositeState result = new CompositeState(machines);
        result.compose(new EmptyLTSOuput());
        return result;
    }

    private static MTS<Long, String> cycle(String action) {
        MTS<Long, String> result =
                new MTSImpl<Long, String>(Long.valueOf(0L));
        result.addState(Long.valueOf(1L));
        result.addAction(action);
        result.addRequired(Long.valueOf(0L), action, Long.valueOf(1L));
        result.addRequired(Long.valueOf(1L), action, Long.valueOf(0L));
        return result;
    }

    private static final class Fixture {
        private final MTS<StrategyState<Long, Integer>, String> nativeController;
        private final MTS<Long, String> plainController;
        private final Map<StrategyState<Long, Integer>, Long> nativeToPlain;
		private final MTS<Long, String> solverEnvironment;
		private final MTS<Long, String> solverPlant;
		private final CompactState enewEndpoint;
        private final M9CompositionProvenance.Projection plantProjection;
        private final M9CompositionProvenance.OrderedPrefixProjection
                environmentPrefix;

        private Fixture(
                MTS<StrategyState<Long, Integer>, String> nativeController,
                MTS<Long, String> plainController,
                Map<StrategyState<Long, Integer>, Long> nativeToPlain,
				MTS<Long, String> solverEnvironment,
				MTS<Long, String> solverPlant,
				CompactState enewEndpoint,
                M9CompositionProvenance.Projection plantProjection,
                M9CompositionProvenance.OrderedPrefixProjection
                        environmentPrefix) {
            this.nativeController = nativeController;
            this.plainController = plainController;
            this.nativeToPlain = nativeToPlain;
			this.solverEnvironment = solverEnvironment;
			this.solverPlant = solverPlant;
			this.enewEndpoint = enewEndpoint;
            this.plantProjection = plantProjection;
            this.environmentPrefix = environmentPrefix;
        }
    }
}
