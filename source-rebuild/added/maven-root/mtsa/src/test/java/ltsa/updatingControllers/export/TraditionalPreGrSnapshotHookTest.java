package ltsa.updatingControllers.export;

import MTSSynthesis.ar.dc.uba.model.condition.Fluent;
import MTSSynthesis.ar.dc.uba.model.condition.Formula;
import MTSSynthesis.controller.model.ControllerGoal;
import MTSTools.ac.ic.doc.mtstools.model.MTS;
import MTSTools.ac.ic.doc.mtstools.model.impl.MTSImpl;
import ltsa.ac.ic.doc.mtstools.util.fsp.MTSToAutomataConverter;
import ltsa.control.ControllerGoalDefinition;
import ltsa.control.util.ControllerUtils;
import ltsa.lts.CompactState;
import ltsa.lts.CompositeState;
import ltsa.lts.EmptyLTSOuput;
import ltsa.updatingControllers.UpdateConstants;
import ltsa.updatingControllers.UpdatingControllerEvaluationRecorder;
import ltsa.updatingControllers.synthesis.UpdatingControllerSafetySynthesizer;
import ltsa.updatingControllers.synthesis.UpdatingControllerGRSynthesizer;
import ltsa.updatingControllers.synthesis.UpdatingControllerSynthesizer;
import ltsa.updatingControllers.synthesis.UpdatingControllersUtils;
import ltsa.updatingControllers.synthesis.UpdatingEnvironmentGenerator;
import ltsa.updatingControllers.structures.UpdatingControllerCompositeState;
import org.testng.annotations.Test;
import org.testng.annotations.BeforeMethod;
import org.testng.annotations.AfterMethod;

import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.Set;
import java.util.Vector;
import java.util.Map;
import java.util.List;
import java.lang.reflect.Field;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.atomic.AtomicInteger;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

@Test(singleThreaded = true)
public class TraditionalPreGrSnapshotHookTest {
	@BeforeMethod(alwaysRun = true)
	public void acquireNativeCompositionLock() {
		M9NativeCompositionTestLock.acquire();
	}

	@AfterMethod(alwaysRun = true)
	public void releaseNativeCompositionLock() {
		M9NativeCompositionTestLock.release();
	}

	@Test
	public void productionSynthesizerTerminatesAtTheHookBeforeGr() {
		UpdatingControllerEvaluationRecorder.reset();
		UpdatingControllersUtils.ACTION_FLUENTS_FOR_UPDATE.clear();
		UpdatingControllersUtils.ACTION_FLUENTS_FOR_UPDATE.add(
				UpdatingControllersUtils.stopFluent);
		MTS<Long, String> old = cycle(Long.valueOf(0L),
				Long.valueOf(1L), "a");
		MTS<Long, String> mapping = mappingCycle();
		CompositeState oldComposite = composite("old", old);
		CompositeState mappingComposite = composite("mapping", mapping);

		ControllerGoalDefinition safety = new ControllerGoalDefinition("safety");
		ControllerGoal<String> gr = new ControllerGoal<String>();
		gr.addAllControllableActions(new LinkedHashSet<String>(Arrays.asList(
				"a", UpdateConstants.STOP_OLD_SPEC,
				UpdateConstants.START_NEW_SPEC,
				UpdateConstants.RECONFIGURE)));
		UpdatingControllerCompositeState uccs =
				new UpdatingControllerCompositeState(
						oldComposite,
						mappingComposite,
						safety,
						gr,
						"synthetic-uav-pre-gr");

		TraditionalPreGrSnapshotHook.Scope scope =
				TraditionalPreGrSnapshotHook.armSyntheticForTest(
						TraditionalPreGrSnapshotHook.newSyntheticAttemptLedgerForTest());
		TraditionalPreGrSnapshotHook.SealedCapture sealed = null;
		try {
			UpdatingControllerSynthesizer.generateController(
					uccs, new EmptyLTSOuput());
			fail("Expected production synthesis to terminate at pre-GR capture");
		} catch (TraditionalPreGrSnapshotHook.SnapshotComplete expected) {
			sealed = scope.closeAndSeal();
		} finally {
			if (TraditionalPreGrSnapshotHook.isArmed()) scope.close();
		}
		assertTrue(sealed != null);
		assertEquals(Integer.valueOf(1),
				Integer.valueOf(sealed.getCaptureAttempts()));
		assertEquals(Integer.valueOf(0),
				Integer.valueOf(sealed.getNativeUpdateGrEntries()));
		assertFalse(sealed.getSnapshot().getSafetyEnvironment()
				.getStates().isEmpty());
		assertTrue(sealed.getSnapshot().getSafetySemantics() != null);
		assertEquals(
				M9TraditionalSafetySemanticsSnapshot.LifecycleProfile
						.ORDERED_STOP_RECONFIGURE_START_COMPLETE,
				sealed.getSnapshot().getSafetySemantics().getLifecycleProfile());
		assertTrue(UpdatingControllersUtils.ACTION_FLUENTS_FOR_UPDATE.isEmpty());
		assertRecorderHasNoActiveScopeOrTimer();
	}

    @Test
    public void capturesExactlyOnceAndStopsBeforeNativeGr() {
        MTS<Long, String> oldController = cycle(Long.valueOf(0L),
                Long.valueOf(1L), "a");
        MTS<Long, String> mapping = mappingCycle();
        UpdatingEnvironmentGenerator generator =
                new UpdatingEnvironmentGenerator(oldController, mapping, true);
        generator.generateEnvironment();

        MTS<Long, String> updating = ControllerUtils.UpdateEnvironment2MTS(
                generator.getUpdEnv());
        MTS<Long, String> meta = ControllerUtils.removeTopStates(
                updating, Collections.<Fluent>emptySet());
		M9CompositionProvenance.Projection preSafetyMeta =
				M9CompositionProvenance.capture(meta, updating);
        Set<String> controllable = new LinkedHashSet<String>(Arrays.asList(
                "a", UpdateConstants.STOP_OLD_SPEC,
				UpdateConstants.RECONFIGURE,
                UpdateConstants.START_NEW_SPEC));
        UpdatingControllerSafetySynthesizer.SafetySynthesisResult safety =
                UpdatingControllerSafetySynthesizer
                        .synthesizeSafetyWithProvenance(
                                meta,
                                Collections.<Fluent>emptySet(),
                                Collections.<Formula>emptyList(),
                                controllable,
                                Arrays.asList(
                                        UpdateConstants.STOP_OLD_SPEC,
										UpdateConstants.RECONFIGURE,
                                        UpdateConstants.START_NEW_SPEC),
                                new EmptyLTSOuput());

		TraditionalPreGrSnapshotHook.Scope scope =
				TraditionalPreGrSnapshotHook.armSyntheticForTest(
						TraditionalPreGrSnapshotHook.newSyntheticAttemptLedgerForTest());
		TraditionalPreGrSnapshotHook.SealedCapture sealed = null;
        try {
            TraditionalPreGrSnapshotHook.captureAndStop(
                    updating,
                    meta,
                    safety,
                    generator.getProvenance(),
					preSafetyMeta,
                    controllable);
            fail("Expected pre-GR terminal control flow");
        } catch (TraditionalPreGrSnapshotHook.SnapshotComplete expected) {
			sealed = scope.closeAndSeal();
            TraditionalPreGrSnapshot snapshot = sealed.getSnapshot();
			int mapped = snapshot.getSafetyStateToUpdatingState().size();
			int unmappedUnsafe = snapshot.getProvenanceFreeUnsafeStates().size();
			assertEquals(Integer.valueOf(
						snapshot.getSafetyEnvironment().getStates().size()),
					Integer.valueOf(mapped + unmappedUnsafe));
			assertTrue(snapshot.getProvenanceFreeUnsafeStates().isEmpty()
					|| snapshot.getProvenanceFreeUnsafeStates().equals(
							Collections.singleton(Long.valueOf(-1L))));
            assertEquals(generator.getProvenance().getOldControllerStates(),
                    snapshot.getUpdatingProvenance().getOldControllerStates());
            assertTrue(snapshot.getUpdatingEnvironment().getActions()
                    .contains(UpdateConstants.BEGIN_UPDATE));
            assertFalse(snapshot.getSafetyEnvironment().getStates().isEmpty());
        } finally {
			if (TraditionalPreGrSnapshotHook.isArmed()) scope.close();
        }
		assertTrue(sealed != null);
        assertFalse(TraditionalPreGrSnapshotHook.isArmed());
    }

    @Test
    public void rejectsNestedScopes() {
		TraditionalPreGrSnapshotHook.AttemptLedger ledger =
				TraditionalPreGrSnapshotHook.newSyntheticAttemptLedgerForTest();
        TraditionalPreGrSnapshotHook.Scope scope =
				TraditionalPreGrSnapshotHook.armSyntheticForTest(ledger);
        try {
            try {
				TraditionalPreGrSnapshotHook.armSyntheticForTest(ledger);
                fail("Expected nested pre-GR scope to fail");
            } catch (IllegalStateException expected) {
                assertTrue(expected.getMessage().contains("already armed"));
            }
        } finally {
            scope.close();
        }
    }

	@Test
	public void aConsumedLedgerCannotBeRearmed() {
		TraditionalPreGrSnapshotHook.AttemptLedger ledger =
				TraditionalPreGrSnapshotHook.newSyntheticAttemptLedgerForTest();
		TraditionalPreGrSnapshotHook.Scope scope =
				TraditionalPreGrSnapshotHook.armSyntheticForTest(ledger);
		scope.close();
		try {
			TraditionalPreGrSnapshotHook.armSyntheticForTest(ledger);
			fail("Expected a consumed attempt ledger to reject re-arm");
		} catch (IllegalStateException expected) {
			assertTrue(expected.getMessage().contains("already consumed"));
		}
	}

	@Test
	public void anUncapturedScopeCannotSeal() {
		TraditionalPreGrSnapshotHook.Scope scope =
				TraditionalPreGrSnapshotHook.armSyntheticForTest(
						TraditionalPreGrSnapshotHook.newSyntheticAttemptLedgerForTest());
		try {
			scope.closeAndSeal();
			fail("Expected an uncaptured scope to reject sealing");
		} catch (IllegalStateException expected) {
			assertTrue(expected.getMessage().contains("one capture"));
		}
		assertFalse(TraditionalPreGrSnapshotHook.isArmed());
	}

	@Test
	public void actualNativeGrEntryConsumesTheScopeWithoutEvidence() {
		TraditionalPreGrSnapshotHook.Scope scope =
				TraditionalPreGrSnapshotHook.armSyntheticForTest(
						TraditionalPreGrSnapshotHook.newSyntheticAttemptLedgerForTest());
		try {
			UpdatingControllerGRSynthesizer.synthesizeGR(null, null, null, null);
			fail("Expected native GR entry to be rejected before dereferencing inputs");
		} catch (IllegalStateException expected) {
			assertTrue(expected.getMessage().contains("forbidden"));
		}
		assertEquals(Integer.valueOf(1),
				Integer.valueOf(scope.getNativeUpdateGrEntries()));
		try {
			scope.closeAndSeal();
			fail("Expected a GR-entered scope to reject sealing");
		} catch (IllegalStateException expected) {
			assertTrue(expected.getMessage().contains("zero native GR"));
		}
		assertFalse(TraditionalPreGrSnapshotHook.isArmed());
	}

	@Test
	public void aCrossThreadGrAttemptInvalidatesACapturedScope() throws Exception {
		MTS<Long, String> oldController = cycle(
				Long.valueOf(0L), Long.valueOf(1L), "a");
		MTS<Long, String> mapping = mappingCycle();
		UpdatingEnvironmentGenerator generator =
				new UpdatingEnvironmentGenerator(oldController, mapping, true);
		generator.generateEnvironment();
		MTS<Long, String> updating = ControllerUtils.UpdateEnvironment2MTS(
				generator.getUpdEnv());
		MTS<Long, String> meta = ControllerUtils.removeTopStates(
				updating, Collections.<Fluent>emptySet());
		M9CompositionProvenance.Projection preSafetyMeta =
				M9CompositionProvenance.capture(meta, updating);
		Set<String> controllable = new LinkedHashSet<String>(Arrays.asList(
				"a", UpdateConstants.STOP_OLD_SPEC,
				UpdateConstants.RECONFIGURE, UpdateConstants.START_NEW_SPEC));
		UpdatingControllerSafetySynthesizer.SafetySynthesisResult safety =
				UpdatingControllerSafetySynthesizer.synthesizeSafetyWithProvenance(
						meta,
						Collections.<Fluent>emptySet(),
						Collections.<Formula>emptyList(),
						controllable,
						Arrays.asList(
								UpdateConstants.STOP_OLD_SPEC,
								UpdateConstants.RECONFIGURE,
								UpdateConstants.START_NEW_SPEC),
						new EmptyLTSOuput());

		TraditionalPreGrSnapshotHook.Scope scope =
				TraditionalPreGrSnapshotHook.armSyntheticForTest(
						TraditionalPreGrSnapshotHook.newSyntheticAttemptLedgerForTest());
		try {
			TraditionalPreGrSnapshotHook.captureAndStop(
					updating, meta, safety, generator.getProvenance(),
					preSafetyMeta, controllable);
			fail("Expected capture terminal control flow");
		} catch (TraditionalPreGrSnapshotHook.SnapshotComplete expected) {
			// The captured scope deliberately remains unsealed for the race probe.
		}
		final AtomicInteger rejected = new AtomicInteger();
		Thread attacker = new Thread(new Runnable() {
			@Override
			public void run() {
				try {
					TraditionalPreGrSnapshotHook
							.beforeNativeUpdateGrEntryForTest(scope);
				} catch (IllegalStateException expected) {
					rejected.incrementAndGet();
				}
			}
		}, "m9-cross-thread-gr");
		attacker.start();
		attacker.join();
		assertEquals(Integer.valueOf(1), Integer.valueOf(rejected.get()));
		assertEquals(Integer.valueOf(1),
				Integer.valueOf(scope.getNativeUpdateGrEntries()));
		try {
			scope.closeAndSeal();
			fail("Expected the cross-thread GR attempt to invalidate sealing");
		} catch (IllegalStateException expected) {
			assertTrue(expected.getMessage().contains("zero native GR"));
		}
		assertFalse(TraditionalPreGrSnapshotHook.isArmed());
	}

	@Test
	public void onlyOneParallelThreadConsumesAnAttemptLedger() throws Exception {
		final TraditionalPreGrSnapshotHook.AttemptLedger ledger =
				TraditionalPreGrSnapshotHook.newSyntheticAttemptLedgerForTest();
		final CountDownLatch start = new CountDownLatch(1);
		final AtomicInteger accepted = new AtomicInteger();
		final AtomicInteger rejected = new AtomicInteger();
		Runnable contender = new Runnable() {
			@Override
			public void run() {
				try {
					start.await();
					TraditionalPreGrSnapshotHook.Scope scope =
							TraditionalPreGrSnapshotHook.armSyntheticForTest(ledger);
					accepted.incrementAndGet();
					scope.close();
				} catch (IllegalStateException expected) {
					rejected.incrementAndGet();
				} catch (InterruptedException interrupted) {
					Thread.currentThread().interrupt();
				}
			}
		};
		Thread first = new Thread(contender, "m9-ledger-first");
		Thread second = new Thread(contender, "m9-ledger-second");
		first.start();
		second.start();
		start.countDown();
		first.join();
		second.join();
		assertEquals(Integer.valueOf(1), Integer.valueOf(accepted.get()));
		assertEquals(Integer.valueOf(1), Integer.valueOf(rejected.get()));
	}

	private static void assertRecorderHasNoActiveScopeOrTimer() {
		try {
			Field timers = UpdatingControllerEvaluationRecorder.class
					.getDeclaredField("activeTimers");
			timers.setAccessible(true);
			Field scopes = UpdatingControllerEvaluationRecorder.class
					.getDeclaredField("activeCountScopes");
			scopes.setAccessible(true);
			assertTrue(((Map<?, ?>) timers.get(null)).isEmpty());
			assertTrue(((List<?>) scopes.get(null)).isEmpty());
		} catch (ReflectiveOperationException failure) {
			throw new AssertionError(failure);
		}
	}

    private static MTS<Long, String> cycle(
            Long first, Long second, String action) {
        MTS<Long, String> mts = new MTSImpl<Long, String>(first);
        mts.addState(second);
        mts.addAction(action);
        mts.addRequired(first, action, second);
        mts.addRequired(second, action, first);
        return mts;
    }

	private static MTS<Long, String> mappingCycle() {
		MTS<Long, String> mts = cycle(
				Long.valueOf(10L), Long.valueOf(11L), "a");
		mts.addAction(UpdateConstants.RECONFIGURE);
		mts.addRequired(Long.valueOf(10L), UpdateConstants.RECONFIGURE,
				Long.valueOf(10L));
		return mts;
	}

	private static CompositeState composite(String name, MTS<Long, String> mts) {
		Vector<CompactState> machines = new Vector<CompactState>();
		machines.add(MTSToAutomataConverter.getInstance().convert(
				mts, name, true));
		return new CompositeState(name, machines);
	}
}
