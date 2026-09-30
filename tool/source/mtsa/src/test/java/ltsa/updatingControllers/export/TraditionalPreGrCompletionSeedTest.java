package ltsa.updatingControllers.export;

import MTSTools.ac.ic.doc.mtstools.model.MTS;
import ltsa.ac.ic.doc.mtstools.util.fsp.AutomataToMTSConverter;
import ltsa.lts.CompactState;
import ltsa.lts.CompositeState;
import ltsa.lts.EmptyLTSOuput;
import ltsa.lts.EventState;
import ltsa.lts.EventStateUtils;
import org.junit.Assert;
import org.testng.annotations.AfterMethod;
import org.testng.annotations.BeforeMethod;
import org.testng.annotations.Test;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Vector;

public class TraditionalPreGrCompletionSeedTest {
	@BeforeMethod(alwaysRun = true)
	public void lockNativeComposition() {
		M9NativeCompositionTestLock.acquire();
	}

	@AfterMethod(alwaysRun = true)
	public void unlockNativeComposition() {
		M9NativeCompositionTestLock.release();
	}

	@Test
	public void capturesExactAtomicRelationalStateMap() {
		CompactState mapping = mapping("MAP", "reconfigure");
		CompactState newComponent = newComponent("NEW");
		Product mappingProduct = product("MAPPING", mapping);
		Product newProduct = product("ENEW", newComponent);
		TraditionalPreGrSnapshot.CompletionSeed seed =
				TraditionalPreGrSnapshot.CompletionSeed.captureForSyntheticTest(
						mappingProduct.mts,
						Collections.singletonList(mapping),
						Collections.singletonList(
								Collections.singletonMap(1, 0)),
						Collections.singletonList(newComponent),
						Collections.singletonList(Boolean.FALSE),
						newProduct.authority);
		Assert.assertEquals(Collections.singletonMap(1, 0),
				seed.getLocalMappingToNew().get(0));
		Assert.assertEquals(Collections.singletonMap(1L, 0L),
				seed.getMappingProductToNew());
		Assert.assertTrue(M9CompositionProvenance.canonicalEquals(
				newProduct.authority, seed.getNewEnvironment()));
	}

	@Test
	public void rejectsActionSequencesForeignTargetsAndPartialTuples() {
		CompactState mapping = mapping("MAP", "reconfigure");
		CompactState newComponent = newComponent("NEW");
		Product mappingProduct = product("MAPPING", mapping);
		Product newProduct = product("ENEW", newComponent);
		expectFailure(
				mappingProduct,
				Collections.singletonList(mapping),
				Collections.singletonList(Collections.singletonMap(1, 0)),
				Collections.singletonList(newComponent),
				Collections.singletonList(Boolean.TRUE),
				newProduct.authority,
				"action sequences");
		expectFailure(
				mappingProduct,
				Collections.singletonList(mapping),
				Collections.singletonList(Collections.singletonMap(1, 7)),
				Collections.singletonList(newComponent),
				Collections.singletonList(Boolean.FALSE),
				newProduct.authority,
				"outside its component domains");

		CompactState left = mapping("LEFT", "reconfigure");
		left.states[0] = EventStateUtils.add(
				left.states[0], new EventState(0, 1));
		CompactState right = mapping("RIGHT", "reconfigure");
		CompactState newLeft = newComponent("NEW_LEFT");
		CompactState newRight = newComponent("NEW_RIGHT");
		Product twoMapping = product("TWO_MAPPING", left, right);
		Product twoNew = product("TWO_NEW", newLeft, newRight);
		expectFailure(
				twoMapping,
				Arrays.asList(left, right),
				Arrays.asList(
						Collections.singletonMap(1, 0),
						Collections.singletonMap(1, 0)),
				Arrays.asList(newLeft, newRight),
				Arrays.asList(Boolean.FALSE, Boolean.FALSE),
				twoNew.authority,
				"partially loadable");
	}

	private static void expectFailure(
			Product mappingProduct,
			List<CompactState> mappings,
			List<Map<Integer, Integer>> localMaps,
			List<CompactState> news,
			List<Boolean> markers,
			M9CompositionProvenance.Projection newAuthority,
			String fragment) {
		try {
			TraditionalPreGrSnapshot.CompletionSeed.captureForSyntheticTest(
					mappingProduct.mts, mappings, localMaps, news, markers,
					newAuthority);
			Assert.fail("Expected completion seed rejection containing " + fragment);
		} catch (IllegalArgumentException expected) {
			Assert.assertTrue(expected.getMessage(),
					expected.getMessage().contains(fragment));
		}
	}

	private static Product product(String name, CompactState... components) {
		Vector<CompactState> machines = new Vector<CompactState>();
		for (CompactState component : components) machines.add(component.myclone());
		CompositeState composite = new CompositeState(name, machines);
		composite.compose(new EmptyLTSOuput());
		MTS<Long, String> mts = AutomataToMTSConverter.getInstance()
				.convert(composite.composition);
		MTS<Long, String> first = AutomataToMTSConverter.getInstance()
				.convert(components[0]);
		return new Product(mts, M9CompositionProvenance.capture(mts, first));
	}

	private static CompactState mapping(String name, String reconfigure) {
		CompactState state = new CompactState(name);
		state.maxStates = 2;
		state.alphabet = new String[]{"tau", "a", reconfigure};
		state.states = new EventState[2];
		state.states[0] = EventStateUtils.add(
				state.states[0], new EventState(1, 0));
		state.states[0] = EventStateUtils.add(
				state.states[0], new EventState(2, 1));
		state.states[1] = EventStateUtils.add(
				state.states[1], new EventState(1, 1));
		return state;
	}

	private static CompactState newComponent(String name) {
		CompactState state = new CompactState(name);
		state.maxStates = 1;
		state.alphabet = new String[]{"tau", "a"};
		state.states = new EventState[]{new EventState(1, 0)};
		return state;
	}

	private static final class Product {
		private final MTS<Long, String> mts;
		private final M9CompositionProvenance.Projection authority;

		private Product(
				MTS<Long, String> mts,
				M9CompositionProvenance.Projection authority) {
			this.mts = mts;
			this.authority = authority;
		}
	}
}
