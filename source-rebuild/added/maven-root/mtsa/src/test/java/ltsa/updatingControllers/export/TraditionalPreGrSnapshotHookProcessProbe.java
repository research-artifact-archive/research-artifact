package ltsa.updatingControllers.export;

import MTSSynthesis.controller.model.ControllerGoal;
import MTSTools.ac.ic.doc.mtstools.model.MTS;
import MTSTools.ac.ic.doc.mtstools.model.impl.MTSImpl;
import ltsa.ac.ic.doc.mtstools.util.fsp.MTSToAutomataConverter;
import ltsa.control.ControllerGoalDefinition;
import ltsa.lts.CompactState;
import ltsa.lts.CompositeState;
import ltsa.lts.EmptyLTSOuput;
import ltsa.updatingControllers.UpdateConstants;
import ltsa.updatingControllers.synthesis.UpdatingControllerGRSynthesizer;
import ltsa.updatingControllers.synthesis.UpdatingControllerSynthesizer;
import ltsa.updatingControllers.structures.UpdatingControllerCompositeState;

import java.util.Arrays;
import java.util.LinkedHashSet;
import java.util.Vector;
import java.util.concurrent.atomic.AtomicInteger;

/** Fresh-process probe; invoked only by TraditionalPreGrSnapshotHookProcessTest. */
public final class TraditionalPreGrSnapshotHookProcessProbe {
	private TraditionalPreGrSnapshotHookProcessProbe() {
	}

	public static void main(String[] args) {
		try {
			if (args.length != 1) throw new IllegalArgumentException("scenario required");
			if ("capture-seal".equals(args[0])) captureSeal();
			else if ("cross-thread-gr".equals(args[0])) crossThreadGr();
			else if ("double-capture".equals(args[0])) doubleCapture();
			else if ("pre-arm-gr".equals(args[0])) preArmGr();
			else throw new IllegalArgumentException("unknown scenario: " + args[0]);
			System.out.println("M9_PROCESS_PROBE_PASS=" + args[0]);
		} catch (Throwable failure) {
			failure.printStackTrace(System.err);
			System.exit(70);
		}
	}

	private static void captureSeal() {
		UpdatingControllerCompositeState problem = problem("capture-seal");
		TraditionalPreGrSnapshotHook.Scope scope = TraditionalPreGrSnapshotHook.arm();
		runUntilCaptured(problem);
		TraditionalPreGrSnapshotHook.SealedCapture sealed = scope.closeAndSeal();
		require(sealed.usesProductionLedger(), "capture did not use production ledger");
		require(sealed.isAttemptConsumed(), "attempt was not consumed");
		require(sealed.getCaptureAttempts() == 1, "capture count differs");
		require(sealed.getNativeUpdateGrEntries() == 0, "GR count differs");
		expectNativeGrRejected();
		expectRearmRejected();
	}

	private static void crossThreadGr() throws InterruptedException {
		UpdatingControllerCompositeState problem = problem("cross-thread-gr");
		TraditionalPreGrSnapshotHook.Scope scope = TraditionalPreGrSnapshotHook.arm();
		runUntilCaptured(problem);
		AtomicInteger rejected = new AtomicInteger();
		Thread attacker = new Thread(new Runnable() {
			@Override
			public void run() {
				try {
					UpdatingControllerGRSynthesizer.synthesizeGR(null, null, null, null);
				} catch (IllegalStateException expected) {
					rejected.incrementAndGet();
				}
			}
		}, "m9-production-cross-thread-gr");
		attacker.start();
		attacker.join();
		require(rejected.get() == 1, "cross-thread GR was not rejected");
		require(scope.getNativeUpdateGrEntries() == 1,
				"cross-thread GR did not invalidate the production scope");
		try {
			scope.closeAndSeal();
			throw new AssertionError("cross-thread GR allowed sealing");
		} catch (IllegalStateException expected) {
			require(expected.getMessage().contains("zero native GR"),
					"unexpected seal rejection: " + expected.getMessage());
		}
		expectRearmRejected();
	}

	private static void doubleCapture() {
		UpdatingControllerCompositeState problem = problem("double-capture");
		TraditionalPreGrSnapshotHook.Scope scope = TraditionalPreGrSnapshotHook.arm();
		runUntilCaptured(problem);
		try {
			UpdatingControllerSynthesizer.generateController(
					problem, new EmptyLTSOuput());
			throw new AssertionError("second capture was accepted");
		} catch (IllegalStateException expected) {
			require(expected.getMessage().contains("exactly once"),
					"unexpected second-capture rejection: " + expected.getMessage());
		}
		require(scope.getCaptureAttempts() == 2, "second attempt was not counted");
		try {
			scope.closeAndSeal();
			throw new AssertionError("double capture allowed sealing");
		} catch (IllegalStateException expected) {
			require(expected.getMessage().contains("one capture"),
					"unexpected seal rejection: " + expected.getMessage());
		}
		expectRearmRejected();
	}

	private static void preArmGr() {
		try {
			UpdatingControllerGRSynthesizer.synthesizeGR(null, null, null, null);
			throw new AssertionError("null probe unexpectedly completed native GR");
		} catch (NullPointerException expectedAfterEntry) {
			// The first-instruction ledger guard ran before null was dereferenced.
		}
		expectRearmRejected();
	}

	private static void runUntilCaptured(UpdatingControllerCompositeState problem) {
		try {
			UpdatingControllerSynthesizer.generateController(
					problem, new EmptyLTSOuput());
			throw new AssertionError("production synthesis reached native GR");
		} catch (TraditionalPreGrSnapshotHook.SnapshotComplete expected) {
			// The owner seals explicitly after the expected terminal returns.
		}
	}

	private static void expectNativeGrRejected() {
		try {
			UpdatingControllerGRSynthesizer.synthesizeGR(null, null, null, null);
			throw new AssertionError("native GR entered after a sealed production attempt");
		} catch (IllegalStateException expected) {
			require(expected.getMessage().contains("forbidden"),
					"unexpected GR rejection: " + expected.getMessage());
		}
	}

	private static void expectRearmRejected() {
		try {
			TraditionalPreGrSnapshotHook.arm();
			throw new AssertionError("production ledger allowed a second arm");
		} catch (IllegalStateException expected) {
			require(expected.getMessage().contains("already consumed"),
					"unexpected re-arm rejection: " + expected.getMessage());
		}
	}

	private static UpdatingControllerCompositeState problem(String name) {
		MTS<Long, String> old = cycle(Long.valueOf(0L), Long.valueOf(1L), "a");
		MTS<Long, String> mapping = cycle(
				Long.valueOf(10L), Long.valueOf(11L), "a");
		mapping.addAction(UpdateConstants.RECONFIGURE);
		mapping.addRequired(Long.valueOf(10L), UpdateConstants.RECONFIGURE,
				Long.valueOf(10L));
		ControllerGoal<String> gr = new ControllerGoal<String>();
		gr.addAllControllableActions(new LinkedHashSet<String>(Arrays.asList(
				"a", UpdateConstants.STOP_OLD_SPEC,
				UpdateConstants.RECONFIGURE, UpdateConstants.START_NEW_SPEC)));
		return new UpdatingControllerCompositeState(
				composite("old", old),
				composite("mapping", mapping),
				new ControllerGoalDefinition("safety-" + name),
				gr,
				"synthetic-process-" + name);
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

	private static CompositeState composite(String name, MTS<Long, String> mts) {
		Vector<CompactState> machines = new Vector<CompactState>();
		machines.add(MTSToAutomataConverter.getInstance().convert(mts, name, true));
		return new CompositeState(name, machines);
	}

	private static void require(boolean condition, String message) {
		if (!condition) throw new AssertionError(message);
	}
}
