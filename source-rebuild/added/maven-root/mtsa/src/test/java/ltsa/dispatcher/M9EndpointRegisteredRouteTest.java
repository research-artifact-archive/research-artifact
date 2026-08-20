package ltsa.dispatcher;

import MTSSynthesis.ar.dc.uba.model.condition.Formula;
import MTSSynthesis.controller.model.ControllerGoal;
import ltsa.lts.CompactState;
import ltsa.lts.CompositeState;
import ltsa.lts.EmptyLTSOuput;
import ltsa.lts.EventState;
import ltsa.lts.M9EndpointPreparedCase;
import ltsa.updatingControllers.export.M9EndpointReceiptBundle;
import ltsa.updatingControllers.export.M9EndpointReceiptCore;
import org.testng.annotations.Test;

import java.lang.reflect.Method;
import java.lang.reflect.Constructor;
import java.lang.reflect.Modifier;
import java.util.Collections;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

/** Preconditions only: every case rejects before the forbidden solver entry. */
public class M9EndpointRegisteredRouteTest {

	@Test
	public void rejectsTauAndBuchiBeforeEndpointSynthesis() {
		CompactState tau = endpoint("tau-source", true);
		expectPreSolverFailure(composite(tau), new ControllerGoal<String>(),
				"deterministic tau-free non-Buchi");

		ControllerGoal<String> buchi = new ControllerGoal<String>();
		buchi.addBuchi(Formula.TRUE_FORMULA);
		expectPreSolverFailure(
				composite(endpoint("buchi-source", false)), buchi,
				"deterministic tau-free non-Buchi");
	}

	@Test
	public void rejectsLegacyRewriteBeforeEndpointSynthesis() {
		ControllerGoal<String> goal = new ControllerGoal<String>();
		goal.setSelfLoopsUncontrollable(Collections.singleton("a"));
		expectPreSolverFailure(
				composite(endpoint("rewrite-source", false)), goal,
				"forbids legacy controller rewriting");
	}

	@Test
	public void bridgeExposesOnlyAtomicPublishedReceiptAndOpaqueAuthority() {
		Method entry = null;
		for (Method method : M9EndpointMaterializerBridge.class.getDeclaredMethods()) {
			if ("synthesiseValidateSealAndPublishOnce".equals(method.getName())) {
				if (entry != null) fail("Atomic endpoint entrypoint is ambiguous.");
				entry = method;
			}
		}
		assertTrue("Atomic endpoint entrypoint is absent.", entry != null);
		assertEquals(
				ltsa.updatingControllers.export.M9EndpointReceiptBundle.PublishedReceipt.class,
				entry.getReturnType());
		assertEquals(Integer.valueOf(3),
				Integer.valueOf(entry.getParameterTypes().length));
		assertEquals(M9EndpointPreparedCase.class,
				entry.getParameterTypes()[0]);
		assertEquals(M9EndpointReceiptCore.Bindings.class,
				entry.getParameterTypes()[1]);
		assertEquals(M9EndpointReceiptBundle.PublicationTarget.class,
				entry.getParameterTypes()[2]);
		for (Class<?> parameter : entry.getParameterTypes()) {
			assertTrue("Hook scope/native capture must not cross the bridge.",
					!parameter.getName().contains("M9EndpointSynthesisHook$Scope")
					&& !parameter.getName().contains("DeterministicLtsSynthesisCapture"));
		}
		Constructor<?>[] constructors = TransitionSystemDispatcher
				.M9EndpointReceiptAuthority.class.getDeclaredConstructors();
		assertTrue("Receipt authority constructor is absent.", constructors.length > 0);
		int sourceConstructors = 0;
		for (Constructor<?> constructor : constructors) {
			assertTrue("Receipt authority exposes a public/protected constructor.",
					!Modifier.isPublic(constructor.getModifiers())
					&& !Modifier.isProtected(constructor.getModifiers()));
			if (!constructor.isSynthetic()) {
				sourceConstructors++;
				assertTrue("Source receipt authority constructor must be private.",
						Modifier.isPrivate(constructor.getModifiers()));
			}
		}
		assertEquals(Integer.valueOf(1), Integer.valueOf(sourceConstructors));
	}

	@Test
	public void rejectsWildcardAndDuplicateEndpointRoleBeforeSynthesis() {
		CompactState wildcard = endpoint("wildcard-source", false);
		wildcard.alphabet = new String[]{"tau", "*"};
		expectPreSolverFailure(composite(wildcard), new ControllerGoal<String>(),
				"wildcard action");

		CompositeState source = composite(endpoint("same-role", false));
		try {
			TransitionSystemDispatcher.validateRegisteredM9EndpointRoleNames(
					source, endpoint("same-role", false));
			fail("Expected duplicate endpoint role rejection");
		} catch (IllegalArgumentException expected) {
			assertTrue(expected.getMessage(),
					expected.getMessage().contains("distinct"));
		}
	}

	private static void expectPreSolverFailure(
			CompositeState source,
			ControllerGoal<String> goal,
			String fragment) {
		try {
			TransitionSystemDispatcher
					.validateRegisteredM9DeterministicEndpointInput(
							source, goal, new EmptyLTSOuput());
			fail("Expected registered endpoint precondition rejection");
		} catch (IllegalArgumentException expected) {
			assertTrue(expected.getMessage(),
					expected.getMessage().contains(fragment));
		}
	}

	private static CompositeState composite(CompactState endpoint) {
		CompositeState result = new CompositeState();
		result.name = endpoint.name;
		result.composition = endpoint;
		return result;
	}

	private static CompactState endpoint(String name, boolean enabledTau) {
		CompactState result = new CompactState();
		result.name = name;
		result.maxStates = 1;
		result.alphabet = new String[]{"tau", "a"};
		result.states = new EventState[]{
				new EventState(enabledTau ? 0 : 1, 0)};
		result.endseq = -9999;
		return result;
	}
}
