package ltsa.updatingControllers.export;

import MTSTools.ac.ic.doc.mtstools.model.MTS;
import ltsa.updatingControllers.synthesis.UpdatingControllerSafetySynthesizer;
import ltsa.updatingControllers.synthesis.UpdatingEnvironmentGenerator;
import ltsa.lts.CompactState;

import java.util.Collection;
import java.util.Collections;
import java.util.List;
import java.util.Map;

/**
 * Fresh-JVM, thread-confined hook used by the prospective UAV materializer.
 * The production path is unchanged when the hook is not armed.
 */
public final class TraditionalPreGrSnapshotHook {
    private static final ThreadLocal<Scope> ACTIVE = new ThreadLocal<Scope>();
	private static final AttemptLedger PROCESS_LEDGER = new AttemptLedger();

    private TraditionalPreGrSnapshotHook() {
    }

    public static Scope arm() {
		return armWithLedger(PROCESS_LEDGER, true, null);
	}

	public static Scope arm(
			M9CompositionProvenance.Projection newEnvironmentAuthority) {
		if (newEnvironmentAuthority == null) {
			throw new IllegalArgumentException(
					"A prepared Enew projection is required.");
		}
		return armWithLedger(
				PROCESS_LEDGER, true, newEnvironmentAuthority);
	}

	static Scope armSyntheticForTest(AttemptLedger ledger) {
		if (ledger == null) {
			throw new IllegalArgumentException("A synthetic attempt ledger is required.");
		}
		return armWithLedger(ledger, false, null);
	}

	static AttemptLedger newSyntheticAttemptLedgerForTest() {
		return new AttemptLedger();
	}

	private static Scope armWithLedger(
			AttemptLedger ledger,
			boolean productionLedger,
			M9CompositionProvenance.Projection newEnvironmentAuthority) {
        if (ACTIVE.get() != null) {
            throw new IllegalStateException("A pre-GR snapshot hook is already armed.");
        }
		Scope scope = new Scope(
				Thread.currentThread(), ledger, productionLedger,
				newEnvironmentAuthority);
		if (!ledger.arm(scope)) {
			throw new IllegalStateException(
					"The pre-GR snapshot attempt for this process ledger was already consumed.");
		}
        ACTIVE.set(scope);
        return scope;
    }

    public static boolean isArmed() {
        return ACTIVE.get() != null;
    }

	/** Called at the first instruction of the native updater GR implementation. */
	public static void beforeNativeUpdateGrEntry() {
		Scope scope = ACTIVE.get();
		if (scope != null) {
			scope.requireOwner();
			scope.ledger.rejectNativeGrEntry(scope);
			throw new IllegalStateException(
					"Native updater GR is forbidden while a pre-GR snapshot scope is armed.");
		}
		if (PROCESS_LEDGER.rejectNativeGrEntry(null)) {
			throw new IllegalStateException(
					"Native updater GR is forbidden in a process that consumed the M9 pre-GR attempt.");
		}
	}

	static void beforeNativeUpdateGrEntryForTest(Scope scope) {
		if (scope == null || !scope.ledger.rejectNativeGrEntry(scope)) {
			throw new IllegalStateException("Synthetic pre-GR scope was not armed.");
		}
		throw new IllegalStateException(
				"Native updater GR invalidated the synthetic pre-GR scope.");
	}

    public static void captureAndStop(
            MTS<Long, String> updatingEnvironment,
            MTS<Long, String> metaEnvironment,
            UpdatingControllerSafetySynthesizer.SafetySynthesisResult safety,
            UpdatingEnvironmentGenerator.Provenance updatingProvenance,
			M9CompositionProvenance.Projection preSafetyMetaProvenance,
            Collection<String> controllableActions) {
		captureAndStop(
				updatingEnvironment, metaEnvironment, safety,
				updatingProvenance, preSafetyMetaProvenance,
				null, Collections.<CompactState>emptyList(),
				Collections.<Map<Integer, Integer>>emptyList(),
				Collections.<CompactState>emptyList(),
				Collections.<Boolean>emptyList(), controllableActions);
	}

	public static void captureAndStop(
			MTS<Long, String> updatingEnvironment,
			MTS<Long, String> metaEnvironment,
			UpdatingControllerSafetySynthesizer.SafetySynthesisResult safety,
			UpdatingEnvironmentGenerator.Provenance updatingProvenance,
			M9CompositionProvenance.Projection preSafetyMetaProvenance,
			MTS<Long, String> liveMappingProduct,
			List<CompactState> mappingComponents,
			List<Map<Integer, Integer>> mappingStateToRawNewState,
			List<CompactState> rawNewEnvironmentComponents,
			List<Boolean> actionSequenceMarkers,
			Collection<String> controllableActions) {
        Scope scope = ACTIVE.get();
        if (scope == null) {
            return;
        }
        scope.requireOwner();
		scope.captureAttempts++;
		if (scope.captureAttempts != 1 || scope.snapshot != null) {
			scope.ledger.abort(scope);
            throw new IllegalStateException(
                    "The pre-GR hook may capture exactly once.");
        }
		try {
			scope.snapshot = TraditionalPreGrSnapshot.capture(
					updatingEnvironment,
					metaEnvironment,
					safety,
					updatingProvenance,
					preSafetyMetaProvenance,
					controllableActions,
					liveMappingProduct,
					mappingComponents,
					mappingStateToRawNewState,
					rawNewEnvironmentComponents,
					actionSequenceMarkers,
					scope.newEnvironmentAuthority);
			scope.ledger.markCaptured(scope);
		} catch (RuntimeException | Error failure) {
			scope.ledger.abort(scope);
			throw failure;
		}
        throw SnapshotComplete.INSTANCE;
    }

    public static final class Scope implements AutoCloseable {
        private final Thread owner;
		private final AttemptLedger ledger;
		private final boolean productionLedger;
		private final M9CompositionProvenance.Projection
				newEnvironmentAuthority;
        private int captureAttempts;
		private volatile int nativeUpdateGrEntries;
        private TraditionalPreGrSnapshot snapshot;
        private boolean closed;

		private Scope(
				Thread owner,
				AttemptLedger ledger,
				boolean productionLedger,
				M9CompositionProvenance.Projection newEnvironmentAuthority) {
            this.owner = owner;
			this.ledger = ledger;
			this.productionLedger = productionLedger;
			this.newEnvironmentAuthority = newEnvironmentAuthority;
        }

        private void requireOwner() {
            if (Thread.currentThread() != owner) {
                throw new IllegalStateException(
                        "Pre-GR snapshot scope is thread-confined.");
            }
            if (closed) {
                throw new IllegalStateException("Pre-GR snapshot scope is closed.");
            }
        }

        public int getCaptureAttempts() {
			if (Thread.currentThread() != owner) {
				throw new IllegalStateException(
						"Pre-GR snapshot scope is thread-confined.");
			}
            return captureAttempts;
        }

		public int getNativeUpdateGrEntries() {
			if (Thread.currentThread() != owner) {
				throw new IllegalStateException(
						"Pre-GR snapshot scope is thread-confined.");
			}
			return nativeUpdateGrEntries;
		}

		public SealedCapture closeAndSeal() {
			requireOwner();
			if (snapshot == null || captureAttempts != 1
					|| nativeUpdateGrEntries != 0
					|| !ledger.seal(this)) {
				ledger.abort(this);
				detach();
				throw new IllegalStateException(
						"A sealed pre-GR capture requires one capture and zero native GR entries.");
			}
			TraditionalPreGrSnapshot captured = snapshot;
			detach();
			return new SealedCapture(
					captured, captureAttempts, nativeUpdateGrEntries,
					productionLedger, ledger.isConsumed());
		}

		@Override
        public void close() {
            requireOwner();
			ledger.abort(this);
			detach();
		}

		private void detach() {
            if (ACTIVE.get() != this) {
                throw new IllegalStateException(
                        "Pre-GR snapshot scope identity changed.");
            }
            ACTIVE.remove();
            closed = true;
        }
    }

	public static final class SealedCapture {
		private final TraditionalPreGrSnapshot snapshot;
		private final int captureAttempts;
		private final int nativeUpdateGrEntries;
		private final boolean productionLedger;
		private final boolean attemptConsumed;
		private boolean combinedPublicationConsumed;

		private SealedCapture(
				TraditionalPreGrSnapshot snapshot,
				int captureAttempts,
				int nativeUpdateGrEntries,
				boolean productionLedger,
				boolean attemptConsumed) {
			this.snapshot = snapshot;
			this.captureAttempts = captureAttempts;
			this.nativeUpdateGrEntries = nativeUpdateGrEntries;
			this.productionLedger = productionLedger;
			this.attemptConsumed = attemptConsumed;
		}

		public TraditionalPreGrSnapshot getSnapshot() { return snapshot; }
		public int getCaptureAttempts() { return captureAttempts; }
		public int getNativeUpdateGrEntries() { return nativeUpdateGrEntries; }
		public boolean usesProductionLedger() { return productionLedger; }
		public boolean isAttemptConsumed() { return attemptConsumed; }

		synchronized void claimCombinedPublication() {
			if (combinedPublicationConsumed) {
				throw new IllegalStateException(
						"The sealed pre-GR capture was already used for combined publication.");
			}
			combinedPublicationConsumed = true;
		}
	}

	static final class AttemptLedger {
		private State state = State.UNUSED;
		private Scope scope;

		private synchronized boolean arm(Scope candidate) {
			if (state != State.UNUSED) return false;
			state = State.ARMED;
			scope = candidate;
			return true;
		}

		private synchronized void markCaptured(Scope candidate) {
			if (scope != candidate || state != State.ARMED) {
				state = State.FAILED;
				throw new IllegalStateException(
						"The pre-GR attempt was invalidated before capture completed.");
			}
			state = State.CAPTURED;
		}

		private synchronized boolean seal(Scope candidate) {
			if (scope != candidate || state != State.CAPTURED) {
				state = State.FAILED;
				return false;
			}
			state = State.SEALED;
			return true;
		}

		private synchronized void abort(Scope candidate) {
			if (scope == candidate && state != State.SEALED) {
				state = State.FAILED;
			}
		}

		private synchronized boolean rejectNativeGrEntry(Scope candidate) {
			if (state == State.UNUSED) {
				state = State.GR_USED;
				return false;
			}
			if (state == State.GR_USED) return false;
			if (candidate != null && scope != candidate) return false;
			if (state == State.SEALED || state == State.FAILED) return true;
			if (scope != null) scope.nativeUpdateGrEntries++;
			state = State.FAILED;
			return true;
		}

		private synchronized boolean isConsumed() {
			return state != State.UNUSED;
		}

		private enum State {
			UNUSED, GR_USED, ARMED, CAPTURED, SEALED, FAILED
		}
	}

    /** Expected terminal control flow; only the dedicated worker may catch it. */
    public static final class SnapshotComplete extends RuntimeException {
        private static final SnapshotComplete INSTANCE = new SnapshotComplete();

        private SnapshotComplete() {
            super("M9 traditional pre-GR snapshot complete", null, false, false);
        }
    }
}
