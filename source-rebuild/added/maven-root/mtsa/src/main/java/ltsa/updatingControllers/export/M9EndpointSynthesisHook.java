package ltsa.updatingControllers.export;

import ltsa.dispatcher.TransitionSystemDispatcher;

import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Arrays;

/**
 * Process-wide one-shot ledger for the post-T1 native endpoint GR call.
 * Normal MTSA behaviour is unchanged before an M9 attempt is armed, but any
 * prior controller-synthesis entry permanently makes this JVM ineligible for
 * the prospective endpoint materializer.  The registered worker therefore
 * runs in a fresh child JVM and seals only after it has converted the returned
 * strategy into an immutable endpoint receipt.
 *
 * <p>The sealed attempt is a one-shot guard record, not a standalone
 * attestation that a solver was called.  The registered fresh-worker entrypoint
 * must be hash-bound separately, must obtain the paired callback from the
 * instrumented solver, and must publish the exact canonical receipt bytes whose
 * digest is returned here.</p>
 */
public final class M9EndpointSynthesisHook {
	private static final int MAX_CANONICAL_RECEIPT_BYTES = 16 * 1024 * 1024;
	private static final ThreadLocal<Scope> ACTIVE = new ThreadLocal<Scope>();
	private static final AttemptLedger PROCESS_LEDGER = new AttemptLedger();

	private M9EndpointSynthesisHook() {
	}

	public static Scope arm() {
		return armWithLedger(PROCESS_LEDGER, true);
	}

	static AttemptLedger newSyntheticAttemptLedgerForTest() {
		return new AttemptLedger();
	}

	static Scope armSyntheticForTest(AttemptLedger ledger) {
		if (ledger == null) {
			throw new IllegalArgumentException(
					"A synthetic endpoint-attempt ledger is required.");
		}
		return armWithLedger(ledger, false);
	}

	private static Scope armWithLedger(
			AttemptLedger ledger,
			boolean productionLedger) {
		if (ACTIVE.get() != null) {
			throw new IllegalStateException(
					"An endpoint-synthesis attempt is already armed on this thread.");
		}
		Scope scope = new Scope(
				Thread.currentThread(), ledger, productionLedger);
		if (!ledger.arm(scope)) {
			throw new IllegalStateException(
					"The endpoint-synthesis attempt for this process was already consumed.");
		}
		ACTIVE.set(scope);
		return scope;
	}

	/** Called as the first instruction of every native LTS GR synthesis. */
	public static Invocation beforeControllerSynthesisEntry() {
		Scope scope = ACTIVE.get();
		if (scope != null) scope.requireOwner();
		AttemptLedger ledger = scope == null ? PROCESS_LEDGER : scope.ledger;
		if (ledger.enter(scope)) {
			throw new IllegalStateException(
					"Native controller synthesis violates the one-shot M9 endpoint attempt.");
		}
		return new Invocation(scope, ledger, scope != null);
	}

	static Invocation beforeControllerSynthesisEntryForTest(Scope scope) {
		if (scope == null) {
			throw new IllegalArgumentException("Synthetic endpoint scope is absent.");
		}
		if (scope.ledger.enter(scope)) {
			throw new IllegalStateException(
					"Synthetic controller synthesis violated the one-shot attempt.");
		}
		return new Invocation(scope, scope.ledger, true);
	}

	/** Paired completion token returned by the first-instruction entry hook. */
	public static final class Invocation {
		private final Scope scope;
		private final AttemptLedger ledger;
		private final boolean trackedAttempt;
		private boolean completed;

		private Invocation(
				Scope scope,
				AttemptLedger ledger,
				boolean trackedAttempt) {
			this.scope = scope;
			this.ledger = ledger;
			this.trackedAttempt = trackedAttempt;
		}

		public void returned(Object nativeResult) {
			requireIncomplete();
			completed = true;
			if (trackedAttempt && !ledger.returned(scope, nativeResult)) {
				throw new IllegalStateException(
						"The endpoint synthesis returned no sealable native strategy.");
			}
		}

		public void failed(Throwable failure) {
			if (completed) return;
			completed = true;
			if (trackedAttempt) ledger.abort(scope);
		}

		/** Fails closed if a future solver return path omits its paired callback. */
		public void abortIfIncomplete() {
			if (completed) return;
			completed = true;
			if (trackedAttempt) ledger.abort(scope);
		}

		private void requireIncomplete() {
			if (completed) {
				throw new IllegalStateException(
						"Endpoint-synthesis invocation completion was already recorded.");
			}
			if (trackedAttempt) scope.requireOwner();
		}
	}

	public static final class Scope implements AutoCloseable {
		private final Thread owner;
		private final AttemptLedger ledger;
		private final boolean productionLedger;
		private volatile int synthesisEntries;
		private volatile int rejectedSynthesisEntries;
		private int immutableCaptures;
		private Object returnedNativeResult;
		private byte[] capturedReceiptSha256;
		private boolean closed;

		private Scope(
				Thread owner,
				AttemptLedger ledger,
				boolean productionLedger) {
			this.owner = owner;
			this.ledger = ledger;
			this.productionLedger = productionLedger;
		}

		private void requireOwner() {
			if (Thread.currentThread() != owner) {
				throw new IllegalStateException(
						"Endpoint-synthesis scope is thread-confined.");
			}
			if (closed) {
				throw new IllegalStateException(
						"Endpoint-synthesis scope is already closed.");
			}
		}

		/**
		 * Called only after the nonnull native strategy, all endpoint/provenance
		 * snapshots, and the publication payload have been built immutably.
		 */
		public void markImmutableReceiptCaptured(
				TransitionSystemDispatcher.M9EndpointReceiptAuthority authority) {
			requireOwner();
			if (authority == null) {
				ledger.abort(this);
				throw new IllegalArgumentException(
						"A registered endpoint receipt authority is required.");
			}
			markImmutableReceiptBytes(
					authority.getNativeResultIdentity(),
					authority.getCanonicalReceiptCore().getCanonicalCoreBytes());
		}

		/* Synthetic hook tests only; production callers cannot supply raw bytes. */
		void markImmutableReceiptCapturedForTest(
				Object nativeResult,
				byte[] canonicalReceiptBytes) {
			requireOwner();
			if (productionLedger) {
				ledger.abort(this);
				throw new IllegalStateException(
						"Raw receipt bytes are forbidden on the production ledger.");
			}
			markImmutableReceiptBytes(nativeResult, canonicalReceiptBytes);
		}

		private void markImmutableReceiptBytes(
				Object nativeResult,
				byte[] canonicalReceiptBytes) {
			requireOwner();
			byte[] capturedDigest;
			try {
				capturedDigest = sha256OfStableReceipt(canonicalReceiptBytes);
			} catch (IllegalArgumentException invalidReceipt) {
				ledger.abort(this);
				throw invalidReceipt;
			}
			immutableCaptures++;
			if (immutableCaptures != 1
					|| !ledger.markCaptured(
							this, nativeResult, capturedDigest)) {
				ledger.abort(this);
				throw new IllegalStateException(
						"The endpoint receipt may be captured exactly once after one synthesis entry.");
			}
		}

		public SealedAttempt closeAndSeal() {
			requireOwner();
			byte[] receiptSha256 = capturedReceiptSha256 == null
					? null : capturedReceiptSha256.clone();
			if (synthesisEntries != 1 || immutableCaptures != 1
					|| rejectedSynthesisEntries != 0
					|| !ledger.seal(this)) {
				ledger.abort(this);
				detach();
				throw new IllegalStateException(
						"A sealed endpoint attempt requires one synthesis entry and one immutable receipt.");
			}
			SealedAttempt result = new SealedAttempt(
					synthesisEntries, immutableCaptures,
					rejectedSynthesisEntries, productionLedger,
					ledger.isConsumed(), receiptSha256);
			capturedReceiptSha256 = null;
			detach();
			return result;
		}

		public int getSynthesisEntries() {
			if (Thread.currentThread() != owner) {
				throw new IllegalStateException(
						"Endpoint-synthesis scope is thread-confined.");
			}
			return synthesisEntries;
		}

		public int getImmutableCaptures() {
			if (Thread.currentThread() != owner) {
				throw new IllegalStateException(
						"Endpoint-synthesis scope is thread-confined.");
			}
			return immutableCaptures;
		}

		public int getRejectedSynthesisEntries() {
			if (Thread.currentThread() != owner) {
				throw new IllegalStateException(
						"Endpoint-synthesis scope is thread-confined.");
			}
			return rejectedSynthesisEntries;
		}

		@Override
		public void close() {
			if (Thread.currentThread() != owner) {
				throw new IllegalStateException(
						"Endpoint-synthesis scope is thread-confined.");
			}
			if (closed) return;
			ledger.abort(this);
			detach();
		}

		private void detach() {
			if (ACTIVE.get() != this) {
				throw new IllegalStateException(
						"Endpoint-synthesis scope identity changed.");
			}
			ACTIVE.remove();
			closed = true;
		}
	}

	public static final class SealedAttempt {
		private final int synthesisEntries;
		private final int immutableCaptures;
		private final int rejectedSynthesisEntries;
		private final boolean productionLedger;
		private final boolean attemptConsumed;
		private final byte[] capturedReceiptSha256;
		private boolean publicationConsumed;

		private SealedAttempt(
				int synthesisEntries,
				int immutableCaptures,
				int rejectedSynthesisEntries,
				boolean productionLedger,
				boolean attemptConsumed,
				byte[] capturedReceiptSha256) {
			this.synthesisEntries = synthesisEntries;
			this.immutableCaptures = immutableCaptures;
			this.rejectedSynthesisEntries = rejectedSynthesisEntries;
			this.productionLedger = productionLedger;
			this.attemptConsumed = attemptConsumed;
			this.capturedReceiptSha256 = exactSha256Digest(capturedReceiptSha256);
		}

		public int getSynthesisEntries() { return synthesisEntries; }
		public int getImmutableCaptures() { return immutableCaptures; }
		public int getRejectedSynthesisEntries() {
			return rejectedSynthesisEntries;
		}
		public boolean usesProductionLedger() { return productionLedger; }
		public boolean isAttemptConsumed() { return attemptConsumed; }
		public byte[] getCapturedReceiptSha256() {
			return capturedReceiptSha256.clone();
		}

		synchronized void claimPublication() {
			if (publicationConsumed) {
				throw new IllegalStateException(
						"The sealed endpoint attempt was already used for publication.");
			}
			publicationConsumed = true;
		}
	}

	private static byte[] exactSha256Digest(byte[] digest) {
		if (digest == null || digest.length != 32) {
			throw new IllegalArgumentException(
					"An exact 32-byte receipt SHA-256 is required.");
		}
		return digest.clone();
	}

	private static byte[] sha256OfStableReceipt(byte[] receipt) {
		if (receipt == null || receipt.length == 0
				|| receipt.length > MAX_CANONICAL_RECEIPT_BYTES) {
			throw new IllegalArgumentException(
					"A nonempty bounded canonical receipt payload is required.");
		}
		byte[] first = receipt.clone();
		byte[] second = receipt.clone();
		if (!Arrays.equals(first, second)) {
			throw new IllegalArgumentException(
					"Canonical receipt bytes changed during capture.");
		}
		try {
			return MessageDigest.getInstance("SHA-256").digest(first);
		} catch (NoSuchAlgorithmException impossible) {
			throw new IllegalStateException(
					"The registered SHA-256 runtime is unavailable.", impossible);
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

		/** Returns true exactly when the caller must reject this entry. */
		private synchronized boolean enter(Scope candidate) {
			if (state == State.UNUSED) {
				state = State.SOLVER_USED;
				return false;
			}
			if (state == State.SOLVER_USED) return false;
			if (state == State.SEALED) return true;
			if (state == State.FAILED) {
				if (candidate != null && !candidate.closed) {
					candidate.rejectedSynthesisEntries++;
				}
				return true;
			}
			if (candidate == null || candidate != scope || state != State.ARMED) {
				Scope retained = scope;
				if (retained != null) retained.rejectedSynthesisEntries++;
				failAndRelease(retained);
				return true;
			}
			scope.synthesisEntries++;
			state = State.ENTERED;
			return false;
		}

		private synchronized boolean returned(
				Scope candidate,
				Object nativeResult) {
			if (candidate != scope || state != State.ENTERED
					|| candidate.synthesisEntries != 1 || nativeResult == null) {
				failAndRelease(scope == null ? candidate : scope);
				return false;
			}
			candidate.returnedNativeResult = nativeResult;
			state = State.RETURNED_NONNULL;
			return true;
		}

		private synchronized boolean markCaptured(
				Scope candidate,
				Object nativeResult,
				byte[] receiptSha256) {
			if (candidate != scope || state != State.RETURNED_NONNULL
					|| candidate.synthesisEntries != 1
					|| candidate.rejectedSynthesisEntries != 0
					|| candidate.returnedNativeResult != nativeResult
					|| receiptSha256 == null || receiptSha256.length != 32) {
				failAndRelease(scope == null ? candidate : scope);
				return false;
			}
			candidate.capturedReceiptSha256 = receiptSha256.clone();
			state = State.CAPTURED;
			return true;
		}

		private synchronized boolean seal(Scope candidate) {
			if (candidate != scope || state != State.CAPTURED
					|| candidate.capturedReceiptSha256 == null
					|| candidate.capturedReceiptSha256.length != 32) {
				failAndRelease(scope == null ? candidate : scope);
				return false;
			}
			state = State.SEALED;
			candidate.returnedNativeResult = null;
			scope = null;
			return true;
		}

		private synchronized void abort(Scope candidate) {
			if (candidate == scope && state != State.SEALED) {
				failAndRelease(candidate);
			}
		}

		private void failAndRelease(Scope retained) {
			state = State.FAILED;
			if (retained != null) {
				retained.returnedNativeResult = null;
				retained.capturedReceiptSha256 = null;
			}
			scope = null;
		}

		private synchronized boolean isConsumed() {
			return state != State.UNUSED;
		}

		private enum State {
			UNUSED, SOLVER_USED, ARMED, ENTERED, RETURNED_NONNULL,
			CAPTURED, SEALED, FAILED
		}
	}
}
