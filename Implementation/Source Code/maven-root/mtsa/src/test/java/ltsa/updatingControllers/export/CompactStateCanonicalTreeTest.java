package ltsa.updatingControllers.export;

import MTSTools.ac.ic.doc.mtstools.model.MTS;
import MTSTools.ac.ic.doc.mtstools.model.impl.MTSImpl;
import ltsa.ac.ic.doc.mtstools.util.fsp.MTSToAutomataConverter;
import ltsa.lts.CompactState;
import ltsa.lts.CompositeState;
import ltsa.lts.EmptyLTSOuput;
import ltsa.lts.EventState;
import ltsa.lts.EventStateUtils;
import org.testng.annotations.Test;
import org.testng.annotations.BeforeMethod;
import org.testng.annotations.AfterMethod;

import java.util.AbstractMap;
import java.util.HashMap;
import java.util.List;
import java.util.Vector;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

public class CompactStateCanonicalTreeTest {
	@BeforeMethod(alwaysRun = true)
	public void acquireNativeCompositionLock() {
		M9NativeCompositionTestLock.acquire();
	}

	@AfterMethod(alwaysRun = true)
	public void releaseNativeCompositionLock() {
		M9NativeCompositionTestLock.release();
	}

	@Test
	public void rejectsAnImpossibleNativeTauCensusAtEveryTreeNode() {
		CompactState leaf = MTSToAutomataConverter.getInstance().convert(
				cycleA(), "leaf", true);
		leaf.alphabet = new String[]{"tau", "a", "tau", "tau"};
		try {
			CompactStateCanonicalTree.captureForest(new CompactState[]{leaf});
			fail("Expected a leaf with three tau declarations to fail");
		} catch (IllegalArgumentException expected) {
			assertTrue(expected.getMessage(),
					expected.getMessage().contains("one or two tau"));
		}
	}

	@Test
	public void rejectsAnExactButUnreachableClosedProductSubgraph() {
		CompactState left = MTSToAutomataConverter.getInstance().convert(
				cycleA(), "left", true);
		CompactState right = MTSToAutomataConverter.getInstance().convert(
				cycleA(), "right", true);
		CompactState product = new CompactState();
		product.name = "unreachable-exact-scc";
		product.maxStates = 4;
		product.alphabet = new String[]{"tau", "a"};
		product.states = new EventState[]{
				new EventState(1, 1), new EventState(1, 0),
				new EventState(1, 3), new EventState(1, 2)};
		product.endseq = -9999;
		product.components = new CompactState[]{left, right};
		product.stateToComponentStates = new HashMap<Integer, int[]>();
		product.stateToComponentStates.put(0, new int[]{0, 0});
		product.stateToComponentStates.put(1, new int[]{1, 1});
		product.stateToComponentStates.put(2, new int[]{0, 1});
		product.stateToComponentStates.put(3, new int[]{1, 0});
		product.statePlusActionToComponentStates =
				new HashMap<AbstractMap.SimpleEntry<Integer, String>, int[]>();
		for (int state = 0; state < 4; state++) {
			int target = state == 0 ? 1 : state == 1 ? 0 : state == 2 ? 3 : 2;
			product.statePlusActionToComponentStates.put(
					new AbstractMap.SimpleEntry<Integer, String>(state, "a"),
					product.stateToComponentStates.get(target));
		}
		try {
			CompactStateCanonicalTree.captureForest(new CompactState[]{product});
			fail("Expected an unreachable exact product SCC to fail");
		} catch (IllegalArgumentException expected) {
			assertTrue(expected.getMessage(),
					expected.getMessage().contains("unreachable"));
		}
	}

	@Test
	public void capsCartesianExpansionsEvenWhenTheyCollapseToOneErrorOutcome() {
		CompactState product = new CompactState();
		product.name = "collapsed-error-product";
		product.maxStates = 1;
		product.alphabet = new String[]{"tau", "a"};
		product.states = new EventState[]{new EventState(1, -1)};
		product.endseq = -9999;
		product.components = new CompactState[18];
		for (int component = 0; component < product.components.length; component++) {
			CompactState child = new CompactState();
			child.name = "child" + component;
			child.maxStates = 1;
			child.alphabet = new String[]{"tau", "a"};
			child.states = new EventState[1];
			child.states[0] = new EventState(1, -1);
			if (component != 0) {
				child.states[0] = EventStateUtils.add(
						child.states[0], new EventState(1, 0));
			}
			child.endseq = -9999;
			product.components[component] = child;
		}
		product.stateToComponentStates = new HashMap<Integer, int[]>();
		product.stateToComponentStates.put(Integer.valueOf(0), new int[18]);
		product.statePlusActionToComponentStates =
				new HashMap<AbstractMap.SimpleEntry<Integer, String>, int[]>();
		int[] errorTuple = new int[18];
		errorTuple[0] = -1;
		product.statePlusActionToComponentStates.put(
				new AbstractMap.SimpleEntry<Integer, String>(0, "a"), errorTuple);
		try {
			CompactStateCanonicalTree.captureForest(new CompactState[]{product});
			fail("Expected collapsed Cartesian expansion cap rejection");
		} catch (IllegalArgumentException expected) {
			assertTrue(expected.getMessage(),
					expected.getMessage().contains("outcome cap"));
		}
	}

	@Test
	public void recursivelyBindsAndValidatesEveryNativeCompositionNode() {
		CompactState nested = compose(cycleAB(), cycleAB());
		List<CompactStateCanonicalTree> honest =
				CompactStateCanonicalTree.captureForest(
						new CompactState[]{nested});
		assertEquals(1, honest.size());
		assertEquals(2, honest.get(0).getChildren().size());

		int a = actionIndex(nested, "a");
		int b = actionIndex(nested, "b");
		EventState originalRow = nested.states[0];
		AbstractMap.SimpleEntry<Integer, String> b0 =
				new AbstractMap.SimpleEntry<Integer, String>(0, "b");
		int[] originalDiagnostic =
				nested.statePlusActionToComponentStates.get(b0);
		EventState forged = null;
		forged = EventStateUtils.add(forged, new EventState(a, 1));
		forged = EventStateUtils.add(forged, new EventState(b, 0));
		nested.states[0] = forged;
		nested.statePlusActionToComponentStates.put(
				b0, nested.stateToComponentStates.get(Integer.valueOf(0)));
		try {
			CompactStateCanonicalTree.captureForest(new CompactState[]{nested});
			fail("Expected a forged nested parent Post to fail");
		} catch (IllegalArgumentException expected) {
			assertTrue(expected.getMessage(),
					expected.getMessage().contains("Nested product Post"));
		} finally {
			nested.states[0] = originalRow;
			nested.statePlusActionToComponentStates.put(b0, originalDiagnostic);
		}

		int[] tuple0 = nested.stateToComponentStates.get(Integer.valueOf(0));
		int[] tuple1 = nested.stateToComponentStates.get(Integer.valueOf(1));
		AbstractMap.SimpleEntry<Integer, String> a0 =
				new AbstractMap.SimpleEntry<Integer, String>(0, "a");
		AbstractMap.SimpleEntry<Integer, String> a1 =
				new AbstractMap.SimpleEntry<Integer, String>(1, "a");
		AbstractMap.SimpleEntry<Integer, String> b1 =
				new AbstractMap.SimpleEntry<Integer, String>(1, "b");
		int[] diagnosticA0 = nested.statePlusActionToComponentStates.get(a0);
		int[] diagnosticA1 = nested.statePlusActionToComponentStates.get(a1);
		int[] diagnosticB0 = nested.statePlusActionToComponentStates.get(b0);
		int[] diagnosticB1 = nested.statePlusActionToComponentStates.get(b1);
		nested.stateToComponentStates.put(Integer.valueOf(0), tuple1);
		nested.stateToComponentStates.put(Integer.valueOf(1), tuple0);
		nested.statePlusActionToComponentStates.put(a0, tuple0);
		nested.statePlusActionToComponentStates.put(b0, tuple0);
		nested.statePlusActionToComponentStates.put(a1, tuple1);
		nested.statePlusActionToComponentStates.put(b1, tuple1);
		try {
			CompactStateCanonicalTree.captureForest(new CompactState[]{nested});
			fail("Expected a shifted nested initial tuple to fail");
		} catch (IllegalArgumentException expected) {
			assertTrue(expected.getMessage(),
					expected.getMessage().contains("initial tuple"));
		} finally {
			nested.stateToComponentStates.put(Integer.valueOf(0), tuple0);
			nested.stateToComponentStates.put(Integer.valueOf(1), tuple1);
			nested.statePlusActionToComponentStates.put(a0, diagnosticA0);
			nested.statePlusActionToComponentStates.put(a1, diagnosticA1);
			nested.statePlusActionToComponentStates.put(b0, diagnosticB0);
			nested.statePlusActionToComponentStates.put(b1, diagnosticB1);
		}
	}

	private static CompactState compose(
			MTS<Long, String> left,
			MTS<Long, String> right) {
		Vector<CompactState> machines = new Vector<CompactState>();
		machines.add(MTSToAutomataConverter.getInstance().convert(
				left, "left", true));
		machines.add(MTSToAutomataConverter.getInstance().convert(
				right, "right", true));
		CompositeState composition = new CompositeState(machines);
		composition.compose(new EmptyLTSOuput());
		return composition.composition;
	}

	private static MTS<Long, String> cycleAB() {
		MTS<Long, String> result =
				new MTSImpl<Long, String>(Long.valueOf(0L));
		result.addState(Long.valueOf(1L));
		result.addAction("a");
		result.addAction("b");
		result.addRequired(Long.valueOf(0L), "a", Long.valueOf(1L));
		result.addRequired(Long.valueOf(1L), "a", Long.valueOf(0L));
		result.addRequired(Long.valueOf(0L), "b", Long.valueOf(1L));
		result.addRequired(Long.valueOf(1L), "b", Long.valueOf(0L));
		return result;
	}

	private static MTS<Long, String> cycleA() {
		MTS<Long, String> result =
				new MTSImpl<Long, String>(Long.valueOf(0L));
		result.addState(Long.valueOf(1L));
		result.addAction("a");
		result.addRequired(Long.valueOf(0L), "a", Long.valueOf(1L));
		result.addRequired(Long.valueOf(1L), "a", Long.valueOf(0L));
		return result;
	}

	private static int actionIndex(CompactState source, String action) {
		for (int index = 0; index < source.alphabet.length; index++) {
			if (action.equals(source.alphabet[index])) return index;
		}
		throw new AssertionError("Missing action " + action);
	}
}
