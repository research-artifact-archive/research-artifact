package ltsa.updatingControllers.export;

import java.util.concurrent.locks.ReentrantLock;

/**
 * Serializes synthetic tests that exercise MTSA's process-global native
 * composition context.  Surefire runs methods in parallel, while the legacy
 * composer and converter registries are intentionally isolated by a fresh JVM
 * in the registered M9 route rather than being thread-safe in-process.
 */
final class M9NativeCompositionTestLock {
	private static final ReentrantLock LOCK = new ReentrantLock(true);

	private M9NativeCompositionTestLock() {
	}

	static void acquire() {
		LOCK.lock();
	}

	static void release() {
		LOCK.unlock();
	}
}
