package ltsa.updatingControllers.export;

import MTSTools.ac.ic.doc.mtstools.model.MTS;
import MTSTools.ac.ic.doc.mtstools.model.impl.MTSImpl;
import ltsa.ac.ic.doc.mtstools.util.fsp.AutomataToMTSConverter;
import ltsa.ac.ic.doc.mtstools.util.fsp.MTSToAutomataConverter;
import ltsa.lts.CompactState;
import ltsa.lts.CompositeState;
import ltsa.lts.Declaration;
import ltsa.lts.EmptyLTSOuput;
import ltsa.lts.EventState;
import ltsa.lts.EventStateUtils;
import org.testng.annotations.Test;
import org.testng.annotations.BeforeMethod;
import org.testng.annotations.AfterMethod;

import java.util.Vector;
import java.util.AbstractMap;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

public class CompactStateEndpointAdmissionTest {
	@BeforeMethod(alwaysRun = true)
	public void acquireNativeCompositionLock() {
		M9NativeCompositionTestLock.acquire();
	}

	@AfterMethod(alwaysRun = true)
	public void releaseNativeCompositionLock() {
		M9NativeCompositionTestLock.release();
	}

	@Test
	public void admitsDeterministicPrimitiveAndNormalizesBothNoEndSentinels() {
		CompactState endpoint = deterministicPrimitive();
		CompactStateEndpointAdmission.Admission admitted =
				CompactStateEndpointAdmission.admitPrimitive(endpoint, false);
		assertEquals(Integer.valueOf(-1),
				Integer.valueOf(admitted.getNormalizedEndState()));
		assertTrue(!admitted.isComposed());

		endpoint.endseq = ltsa.lts.LTSConstants.NO_SEQUENCE_FOUND;
		admitted = CompactStateEndpointAdmission.admitPrimitive(endpoint, false);
		assertEquals(Integer.valueOf(-1),
				Integer.valueOf(admitted.getNormalizedEndState()));

		CompactState sourceIndexedEndpoint = deterministicPrimitive();
		sourceIndexedEndpoint.maxStates = 3;
		sourceIndexedEndpoint.states = new EventState[]{
				new EventState(1, 1), new EventState(1, 0), new EventState(1, 2)};
		admitted = CompactStateEndpointAdmission.admitPrimitive(
				sourceIndexedEndpoint, false);
		assertEquals(Integer.valueOf(3),
				Integer.valueOf(admitted.getSnapshot().getStateCount()));
	}

	@Test
	public void rejectsEnabledTauNondeterminismErrorAndNonEndDeadlock() {
		CompactState enabledTau = deterministicPrimitive();
		enabledTau.states[0] = EventStateUtils.add(
				enabledTau.states[0], new EventState(0, 0));
		expectIllegal(enabledTau, "Enabled tau");

		CompactState nondeterministic = deterministicPrimitive();
		nondeterministic.states[0] = EventStateUtils.add(
				nondeterministic.states[0], new EventState(1, 0));
		expectIllegal(nondeterministic, "nondeterministic");

		CompactState error = deterministicPrimitive();
		error.states[0] = new EventState(1, Declaration.ERROR);
		expectIllegal(error, "ERROR");

		CompactState deadlock = deterministicPrimitive();
		deadlock.states[1] = null;
		expectIllegal(deadlock, "non-END");
		deadlock.endseq = 1;
		CompactStateEndpointAdmission.Admission terminal =
				CompactStateEndpointAdmission.admitPrimitive(deadlock, true);
		assertEquals(Integer.valueOf(1),
				Integer.valueOf(terminal.getNormalizedEndState()));

		CompactState nonterminalDeclaredEnd = deterministicPrimitive();
		nonterminalDeclaredEnd.endseq = 1;
		try {
			CompactStateEndpointAdmission.admitPrimitive(
					nonterminalDeclaredEnd, false);
			fail("Expected a declared END to require explicit admission");
		} catch (IllegalArgumentException expected) {
			assertTrue(expected.getMessage().contains("declared END"));
		}
		try {
			CompactStateEndpointAdmission.admitPrimitive(
					nonterminalDeclaredEnd, true);
			fail("Expected a nonempty END row to fail");
		} catch (IllegalArgumentException expected) {
			assertTrue(expected.getMessage().contains("declared END"));
		}
	}

	@Test
	public void rejectsThirdTauAndNonAsciiLabels() {
		CompactState thirdTau = deterministicPrimitive();
		thirdTau.alphabet = new String[]{"tau", "a", "tau", "tau"};
		expectIllegal(thirdTau, "one or two");

		CompactState nonAscii = deterministicPrimitive();
		nonAscii.alphabet[1] = "更新";
		expectIllegal(nonAscii, "ASCII");

		CompactState unpairedHighSurrogate = deterministicPrimitive();
		unpairedHighSurrogate.alphabet[1] = "\ud800";
		expectIllegal(unpairedHighSurrogate, "ASCII");

		CompactState unpairedLowSurrogate = deterministicPrimitive();
		unpairedLowSurrogate.alphabet[1] = "\udc00";
		expectIllegal(unpairedLowSurrogate, "ASCII");
	}

	@Test
	public void composedEndpointRequiresAndMatchesDerivedAuthority() {
		MTS<Long, String> left = cycle();
		MTS<Long, String> right = cycle();
		Vector<CompactState> machines = new Vector<CompactState>();
		machines.add(MTSToAutomataConverter.getInstance().convert(
				left, "left", true));
		machines.add(MTSToAutomataConverter.getInstance().convert(
				right, "right", true));
		CompositeState composition = new CompositeState(machines);
		composition.compose(new EmptyLTSOuput());
		MTS<Long, String> product = AutomataToMTSConverter.getInstance()
				.convert(composition.composition);
		M9CompositionProvenance.Projection authority =
				M9CompositionProvenance.capture(product, left);
		assertEquals(Long.valueOf(0L),
				Long.valueOf(authority.getProductInitialState()));
		CompactStateEndpointAdmission.Admission admitted =
				CompactStateEndpointAdmission.admitComposed(
						composition.composition, authority, false);
		assertTrue(admitted.isComposed());
		assertEquals(Integer.valueOf(2), Integer.valueOf(
				admitted.getComponentSnapshots().size()));

		try {
			CompactStateEndpointAdmission.admitComposed(
					composition.composition, null, false);
			fail("Expected absent composition authority to fail");
		} catch (IllegalArgumentException expected) {
			assertTrue(expected.getMessage().contains("external composition authority"));
		}

		int[] original = composition.composition.stateToComponentStates
				.get(Integer.valueOf(0));
		composition.composition.stateToComponentStates.put(
				Integer.valueOf(0), new int[]{0, 1});
		try {
			CompactStateEndpointAdmission.admitComposed(
					composition.composition, authority, false);
			fail("Expected a tuple substitution to fail");
		} catch (IllegalArgumentException expected) {
			assertTrue(expected.getMessage(),
					expected.getMessage().contains("tuple differs")
						|| expected.getMessage().contains("tuple matches no native target"));
		} finally {
			composition.composition.stateToComponentStates.put(
					Integer.valueOf(0), original);
		}

		CompactState secondChild = composition.composition.components[1];
		EventState originalChildPost = secondChild.states[0];
		secondChild.states[0] = new EventState(1, 0);
		try {
			CompactStateEndpointAdmission.admitComposed(
					composition.composition, authority, false);
			fail("Expected a child Post mutation after authority capture to fail");
		} catch (IllegalArgumentException expected) {
			assertTrue(expected.getMessage(),
					expected.getMessage().contains("child bytes")
						|| expected.getMessage().contains("Nested product Post"));
		} finally {
			secondChild.states[0] = originalChildPost;
		}

		MTSImpl<?, ?> rawProduct = (MTSImpl<?, ?>) product;
		int[] tuple0 = rawProduct.getStateToComponentStates()
				.get(Integer.valueOf(0));
		int[] tuple1 = rawProduct.getStateToComponentStates()
				.get(Integer.valueOf(1));
		AbstractMap.SimpleEntry<Integer, String> key0 =
				new AbstractMap.SimpleEntry<Integer, String>(0, "a");
		AbstractMap.SimpleEntry<Integer, String> key1 =
				new AbstractMap.SimpleEntry<Integer, String>(1, "a");
		int[] diagnostic0 = rawProduct.getStatePlusActionToComponentStates()
				.get(key0);
		int[] diagnostic1 = rawProduct.getStatePlusActionToComponentStates()
				.get(key1);
		rawProduct.getStateToComponentStates().put(Integer.valueOf(0), tuple1);
		rawProduct.getStateToComponentStates().put(Integer.valueOf(1), tuple0);
		rawProduct.getStatePlusActionToComponentStates().put(key0, tuple0);
		rawProduct.getStatePlusActionToComponentStates().put(key1, tuple1);
		try {
			MTSImpl<Long, String> shiftedProduct =
					new MTSImpl<Long, String>(Long.valueOf(1L),
							composition.composition);
			shiftedProduct.addState(Long.valueOf(0L));
			shiftedProduct.addAction("tau");
			shiftedProduct.addAction("a");
			shiftedProduct.addRequired(Long.valueOf(0L), "a", Long.valueOf(1L));
			shiftedProduct.addRequired(Long.valueOf(1L), "a", Long.valueOf(0L));
			M9CompositionProvenance.Projection shiftedAuthority =
					M9CompositionProvenance.capture(shiftedProduct, left);
			assertEquals(Long.valueOf(1L),
					Long.valueOf(shiftedAuthority.getProductInitialState()));
			try {
				CompactStateEndpointAdmission.admitComposed(
						composition.composition, shiftedAuthority, false);
				fail("Expected a shifted authority initial state to fail");
			} catch (IllegalArgumentException expected) {
				assertTrue(expected.getMessage(),
						expected.getMessage().contains("initial state")
						|| expected.getMessage().contains("initial tuple"));
			}
		} finally {
			rawProduct.getStateToComponentStates().put(Integer.valueOf(0), tuple0);
			rawProduct.getStateToComponentStates().put(Integer.valueOf(1), tuple1);
			rawProduct.getStatePlusActionToComponentStates().put(key0, diagnostic0);
			rawProduct.getStatePlusActionToComponentStates().put(key1, diagnostic1);
		}
	}

	private static CompactState deterministicPrimitive() {
		CompactState endpoint = new CompactState();
		endpoint.name = "endpoint";
		endpoint.maxStates = 2;
		endpoint.alphabet = new String[]{"tau", "a"};
		endpoint.states = new EventState[2];
		endpoint.states[0] = new EventState(1, 1);
		endpoint.states[1] = new EventState(1, 0);
		endpoint.endseq = -9999;
		return endpoint;
	}

	private static MTS<Long, String> cycle() {
		MTS<Long, String> result = new MTSImpl<Long, String>(Long.valueOf(0L));
		result.addState(Long.valueOf(1L));
		result.addAction("a");
		result.addRequired(Long.valueOf(0L), "a", Long.valueOf(1L));
		result.addRequired(Long.valueOf(1L), "a", Long.valueOf(0L));
		return result;
	}

	private static void expectIllegal(CompactState source, String fragment) {
		try {
			CompactStateEndpointAdmission.admitPrimitive(source, false);
			fail("Expected endpoint rejection containing " + fragment);
		} catch (IllegalArgumentException expected) {
			assertTrue(expected.getMessage(),
					expected.getMessage().contains(fragment));
		}
	}
}
