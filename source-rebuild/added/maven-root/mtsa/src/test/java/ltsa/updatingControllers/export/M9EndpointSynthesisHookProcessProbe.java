package ltsa.updatingControllers.export;

import MTSSynthesis.controller.LTSControllerSynthesiserImpl;

import java.util.concurrent.CountDownLatch;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Fresh-process ledger simulation; it deliberately never reaches a native
 * game solve and therefore is not endpoint-synthesis evidence.
 */
public final class M9EndpointSynthesisHookProcessProbe {
	private M9EndpointSynthesisHookProcessProbe() {
	}

	public static void main(String[] args) {
		try {
			if (args.length != 1) throw new IllegalArgumentException("scenario required");
			if ("raw-production-rejected".equals(args[0])) rawProductionRejected();
			else if ("cross-thread-entry".equals(args[0])) crossThreadEntry();
			else if ("pre-arm-entry".equals(args[0])) preArmEntry();
			else if ("failure-consumes".equals(args[0])) failureConsumes();
			else if ("parallel-arm".equals(args[0])) parallelArm();
			else throw new IllegalArgumentException("unknown scenario: " + args[0]);
			System.out.println("M9_ENDPOINT_HOOK_PROBE_PASS=" + args[0]);
		} catch (Throwable failure) {
			failure.printStackTrace(System.err);
			System.exit(70);
		}
	}

	private static void rawProductionRejected() {
		M9EndpointSynthesisHook.Scope scope = M9EndpointSynthesisHook.arm();
		Object nativeResult = new Object();
		M9EndpointSynthesisHook.Invocation invocation =
				M9EndpointSynthesisHook.beforeControllerSynthesisEntry();
		invocation.returned(nativeResult);
		try {
			scope.markImmutableReceiptCapturedForTest(
					nativeResult, receiptPayload());
			throw new AssertionError("raw production receipt capture was accepted");
		} catch (IllegalStateException expected) {
			require(expected.getMessage().contains("production ledger"),
					"unexpected raw-capture rejection: " + expected.getMessage());
		}
		scope.close();
		expectEntryRejected();
		expectRearmRejected();
	}

	private static void crossThreadEntry() throws Exception {
		M9EndpointSynthesisHook.Scope scope = M9EndpointSynthesisHook.arm();
		M9EndpointSynthesisHook.Invocation invocation =
				M9EndpointSynthesisHook.beforeControllerSynthesisEntry();
		Thread attacker = new Thread(new Runnable() {
			@Override
			public void run() {
				try {
					M9EndpointSynthesisHook.beforeControllerSynthesisEntry();
					throw new AssertionError("cross-thread entry was accepted");
				} catch (IllegalStateException expected) {
					// expected
				}
			}
		}, "m9-endpoint-production-attacker");
		attacker.start();
		attacker.join();
		try {
			invocation.returned(new Object());
			throw new AssertionError("cross-thread entry allowed return completion");
		} catch (IllegalStateException expected) {
			// expected
		}
		scope.close();
		expectRearmRejected();
	}

	private static void preArmEntry() {
		try {
			new LTSControllerSynthesiserImpl<Long, String>()
					.synthesiseGR(null, null);
			throw new AssertionError("null probe passed the solver entry");
		} catch (NullPointerException expectedAfterEntry) {
			// Hook is the first instruction; the null dereference occurs afterward.
		}
		expectRearmRejected();
	}

	private static void failureConsumes() {
		M9EndpointSynthesisHook.Scope scope = M9EndpointSynthesisHook.arm();
		try {
			new LTSControllerSynthesiserImpl<Long, String>()
					.synthesiseGR(null, null);
			throw new AssertionError("null armed probe reached native solve");
		} catch (NullPointerException expectedAfterEntry) {
			// The paired invocation callback marks the attempt failed.
		}
		scope.close();
		expectRearmRejected();
	}

	private static void parallelArm() throws Exception {
		CountDownLatch start = new CountDownLatch(1);
		AtomicInteger armed = new AtomicInteger();
		AtomicInteger rejected = new AtomicInteger();
		Runnable contender = new Runnable() {
			@Override
			public void run() {
				try {
					start.await();
					M9EndpointSynthesisHook.Scope scope =
							M9EndpointSynthesisHook.arm();
					armed.incrementAndGet();
					scope.close();
				} catch (IllegalStateException expected) {
					rejected.incrementAndGet();
				} catch (InterruptedException interrupted) {
					throw new AssertionError(interrupted);
				}
			}
		};
		Thread first = new Thread(contender, "m9-endpoint-arm-1");
		Thread second = new Thread(contender, "m9-endpoint-arm-2");
		first.start();
		second.start();
		start.countDown();
		first.join();
		second.join();
		require(armed.get() == 1, "parallel arm success count differs");
		require(rejected.get() == 1, "parallel arm rejection count differs");
		expectRearmRejected();
	}

	private static void expectEntryRejected() {
		try {
			M9EndpointSynthesisHook.beforeControllerSynthesisEntry();
			throw new AssertionError("entry after seal was accepted");
		} catch (IllegalStateException expected) {
			require(expected.getMessage().contains("one-shot"),
					"unexpected entry rejection: " + expected.getMessage());
		}
	}

	private static void expectRearmRejected() {
		try {
			M9EndpointSynthesisHook.arm();
			throw new AssertionError("consumed process attempt re-armed");
		} catch (IllegalStateException expected) {
			require(expected.getMessage().contains("already consumed"),
					"unexpected rearm rejection: " + expected.getMessage());
		}
	}

	private static void require(boolean condition, String message) {
		if (!condition) throw new AssertionError(message);
	}

	private static byte[] receiptPayload() {
		byte[] result = new byte[73];
		for (int index = 0; index < result.length; index++) {
			result[index] = (byte) (0xa0 + index);
		}
		return result;
	}

}
