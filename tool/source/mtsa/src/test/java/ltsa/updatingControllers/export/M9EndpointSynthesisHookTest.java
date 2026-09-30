package ltsa.updatingControllers.export;

import org.testng.annotations.Test;

import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.security.MessageDigest;
import java.util.concurrent.atomic.AtomicInteger;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

@Test(singleThreaded = true)
public class M9EndpointSynthesisHookTest {
	@Test
	public void publicCaptureApiRequiresAnOpaqueDispatcherAuthority() {
		Method capture = null;
		for (Method method : M9EndpointSynthesisHook.Scope.class.getDeclaredMethods()) {
			if ("markImmutableReceiptCaptured".equals(method.getName())) {
				assertTrue(Modifier.isPublic(method.getModifiers()));
				capture = method;
			}
			if ("markImmutableReceiptCapturedForTest".equals(method.getName())) {
				assertTrue(!Modifier.isPublic(method.getModifiers()));
			}
		}
		assertTrue(capture != null);
		assertEquals(Integer.valueOf(1),
				Integer.valueOf(capture.getParameterTypes().length));
		assertEquals(ltsa.dispatcher.TransitionSystemDispatcher
				.M9EndpointReceiptAuthority.class,
				capture.getParameterTypes()[0]);
	}

	@Test
	public void rejectsPrematureNullWrongIdentityAndPostReturnSecondEntry() {
		M9EndpointSynthesisHook.Scope premature = syntheticScope();
		try {
			premature.markImmutableReceiptCapturedForTest(new Object(), receiptPayload());
			fail("Expected capture before a returned strategy to fail");
		} catch (IllegalStateException expected) {
			assertTrue(expected.getMessage().contains("exactly once"));
		}
		premature.close();

		M9EndpointSynthesisHook.Scope nullResult = syntheticScope();
		M9EndpointSynthesisHook.Invocation nullInvocation =
				M9EndpointSynthesisHook.beforeControllerSynthesisEntryForTest(nullResult);
		try {
			nullInvocation.returned(null);
			fail("Expected a null native result to fail");
		} catch (IllegalStateException expected) {
			assertTrue(expected.getMessage().contains("no sealable"));
		}
		nullResult.close();

		M9EndpointSynthesisHook.Scope invalidDigest = syntheticScope();
		Object digestResult = new Object();
		M9EndpointSynthesisHook.Invocation digestInvocation =
				M9EndpointSynthesisHook.beforeControllerSynthesisEntryForTest(
						invalidDigest);
		digestInvocation.returned(digestResult);
		try {
			invalidDigest.markImmutableReceiptCapturedForTest(
					digestResult, new byte[0]);
			fail("Expected an empty canonical receipt to fail");
		} catch (IllegalArgumentException expected) {
			assertTrue(expected.getMessage().contains("canonical receipt"));
		}
		try {
			invalidDigest.markImmutableReceiptCapturedForTest(
					digestResult, receiptPayload());
			fail("Expected an invalid digest attempt to consume capture authority");
		} catch (IllegalStateException expected) {
			assertTrue(expected.getMessage().contains("exactly once"));
		}
		invalidDigest.close();

		M9EndpointSynthesisHook.Scope wrongIdentity = syntheticScope();
		Object exact = new Object();
		M9EndpointSynthesisHook.Invocation identityInvocation =
				M9EndpointSynthesisHook.beforeControllerSynthesisEntryForTest(wrongIdentity);
		identityInvocation.returned(exact);
		try {
			wrongIdentity.markImmutableReceiptCapturedForTest(
					new Object(), receiptPayload());
			fail("Expected the wrong native result identity to fail");
		} catch (IllegalStateException expected) {
			assertTrue(expected.getMessage().contains("exactly once"));
		}
		wrongIdentity.close();

		M9EndpointSynthesisHook.Scope postReturnSecond = syntheticScope();
		Object returned = new Object();
		M9EndpointSynthesisHook.Invocation returnedInvocation =
				M9EndpointSynthesisHook.beforeControllerSynthesisEntryForTest(
						postReturnSecond);
		returnedInvocation.returned(returned);
		try {
			M9EndpointSynthesisHook.beforeControllerSynthesisEntryForTest(
					postReturnSecond);
			fail("Expected a second entry after return to fail");
		} catch (IllegalStateException expected) {
			assertTrue(expected.getMessage().contains("one-shot"));
		}
		try {
			postReturnSecond.markImmutableReceiptCapturedForTest(
					returned, receiptPayload());
			fail("Expected the rejected second entry to invalidate capture");
		} catch (IllegalStateException expected) {
			assertTrue(expected.getMessage().contains("exactly once"));
		}
		postReturnSecond.close();
	}

	@Test
	public void sealsExactlyOneSyntheticEntryAndImmutableCapture() {
		M9EndpointSynthesisHook.AttemptLedger ledger =
				M9EndpointSynthesisHook.newSyntheticAttemptLedgerForTest();
		M9EndpointSynthesisHook.Scope scope =
				M9EndpointSynthesisHook.armSyntheticForTest(ledger);
		Object nativeResult = new Object();
		M9EndpointSynthesisHook.Invocation invocation =
				M9EndpointSynthesisHook.beforeControllerSynthesisEntryForTest(scope);
		invocation.returned(nativeResult);
		byte[] payload = receiptPayload();
		byte[] expectedDigest = sha256(payload);
		scope.markImmutableReceiptCapturedForTest(nativeResult, payload);
		payload[0] ^= 0x7f;
		M9EndpointSynthesisHook.SealedAttempt sealed = scope.closeAndSeal();
		assertEquals(1, sealed.getSynthesisEntries());
		assertEquals(1, sealed.getImmutableCaptures());
		assertEquals(0, sealed.getRejectedSynthesisEntries());
		assertArrayEquals(expectedDigest, sealed.getCapturedReceiptSha256());
		assertTrue(sealed.isAttemptConsumed());
	}

	@Test
	public void sealedScopeIsTryWithResourcesSafe() {
		M9EndpointSynthesisHook.SealedAttempt sealed;
		try (M9EndpointSynthesisHook.Scope scope = syntheticScope()) {
			Object nativeResult = new Object();
			M9EndpointSynthesisHook.Invocation invocation =
					M9EndpointSynthesisHook.beforeControllerSynthesisEntryForTest(scope);
			invocation.returned(nativeResult);
			scope.markImmutableReceiptCapturedForTest(nativeResult, receiptPayload());
			sealed = scope.closeAndSeal();
		}
		assertEquals(1, sealed.getSynthesisEntries());
		assertEquals(1, sealed.getImmutableCaptures());
	}

	@Test
	public void rejectsASecondEntryBeforeCapture() {
		M9EndpointSynthesisHook.AttemptLedger ledger =
				M9EndpointSynthesisHook.newSyntheticAttemptLedgerForTest();
		M9EndpointSynthesisHook.Scope scope =
				M9EndpointSynthesisHook.armSyntheticForTest(ledger);
		M9EndpointSynthesisHook.Invocation first =
				M9EndpointSynthesisHook.beforeControllerSynthesisEntryForTest(scope);
		try {
			M9EndpointSynthesisHook.beforeControllerSynthesisEntryForTest(scope);
			fail("Expected a second controller-synthesis entry to fail");
		} catch (IllegalStateException expected) {
			assertTrue(expected.getMessage().contains("one-shot"));
		}
		assertEquals(1, scope.getSynthesisEntries());
		assertEquals(1, scope.getRejectedSynthesisEntries());
		try {
			M9EndpointSynthesisHook.beforeControllerSynthesisEntryForTest(scope);
			fail("Expected every later controller-synthesis entry to fail");
		} catch (IllegalStateException expected) {
			assertTrue(expected.getMessage().contains("one-shot"));
		}
		assertEquals(2, scope.getRejectedSynthesisEntries());
		try {
			first.returned(new Object());
			fail("Expected a failed double entry to forbid return completion");
		} catch (IllegalStateException expected) {
			assertTrue(expected.getMessage().contains("no sealable"));
		}
		scope.close();
	}

	@Test
	public void crossThreadEntryInvalidatesTheOwnerScope() throws Exception {
		M9EndpointSynthesisHook.AttemptLedger ledger =
				M9EndpointSynthesisHook.newSyntheticAttemptLedgerForTest();
		M9EndpointSynthesisHook.Scope scope =
				M9EndpointSynthesisHook.armSyntheticForTest(ledger);
		M9EndpointSynthesisHook.Invocation first =
				M9EndpointSynthesisHook.beforeControllerSynthesisEntryForTest(scope);
		AtomicInteger rejected = new AtomicInteger();
		Thread attacker = new Thread(new Runnable() {
			@Override
			public void run() {
				try {
					M9EndpointSynthesisHook.beforeControllerSynthesisEntryForTest(scope);
				} catch (IllegalStateException expected) {
					rejected.incrementAndGet();
				}
			}
		}, "m9-endpoint-hook-attacker");
		attacker.start();
		attacker.join();
		assertEquals(1, rejected.get());
		assertEquals(1, scope.getSynthesisEntries());
		assertEquals(1, scope.getRejectedSynthesisEntries());
		try {
			first.returned(new Object());
			fail("Expected a cross-thread entry to forbid return completion");
		} catch (IllegalStateException expected) {
			assertTrue(expected.getMessage().contains("no sealable"));
		}
		scope.close();
	}

	private static M9EndpointSynthesisHook.Scope syntheticScope() {
		return M9EndpointSynthesisHook.armSyntheticForTest(
				M9EndpointSynthesisHook.newSyntheticAttemptLedgerForTest());
	}

	private static byte[] receiptPayload() {
		byte[] result = new byte[73];
		for (int index = 0; index < result.length; index++) {
			result[index] = (byte) (index + 1);
		}
		return result;
	}

	private static byte[] sha256(byte[] payload) {
		try {
			return MessageDigest.getInstance("SHA-256").digest(payload);
		} catch (Exception impossible) {
			throw new AssertionError(impossible);
		}
	}
}
