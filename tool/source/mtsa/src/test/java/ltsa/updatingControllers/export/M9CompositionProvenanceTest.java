package ltsa.updatingControllers.export;

import MTSTools.ac.ic.doc.mtstools.model.MTS;
import MTSTools.ac.ic.doc.mtstools.model.impl.MTSImpl;
import ltsa.ac.ic.doc.mtstools.util.fsp.AutomataToMTSConverter;
import ltsa.ac.ic.doc.mtstools.util.fsp.MTSToAutomataConverter;
import ltsa.lts.CompactState;
import ltsa.lts.CompositeState;
import ltsa.lts.EmptyLTSOuput;
import org.testng.annotations.Test;
import org.testng.annotations.BeforeMethod;
import org.testng.annotations.AfterMethod;

import java.util.Map;
import java.util.Vector;
import java.util.AbstractMap;
import java.util.List;
import java.util.Collections;
import java.util.LinkedHashMap;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

public class M9CompositionProvenanceTest {
	@BeforeMethod(alwaysRun = true)
	public void acquireNativeCompositionLock() {
		M9NativeCompositionTestLock.acquire();
	}

	@AfterMethod(alwaysRun = true)
	public void releaseNativeCompositionLock() {
		M9NativeCompositionTestLock.release();
	}

    @Test
    public void translatesCompactIndicesBackToNonContiguousSourceIds() {
        MTS<Long, String> source = new MTSImpl<Long, String>(Long.valueOf(20L));
        source.addState(Long.valueOf(10L));
        source.addAction("a");
        source.addRequired(Long.valueOf(20L), "a", Long.valueOf(10L));
        source.addRequired(Long.valueOf(10L), "a", Long.valueOf(20L));

        MTS<Long, String> observer = new MTSImpl<Long, String>(Long.valueOf(0L));
		observer.addState(Long.valueOf(1L));
        observer.addAction("a");
		observer.addRequired(Long.valueOf(0L), "a", Long.valueOf(1L));
		observer.addRequired(Long.valueOf(1L), "a", Long.valueOf(0L));

        Vector<CompactState> machines = new Vector<CompactState>();
        machines.add(MTSToAutomataConverter.getInstance().convert(
                source, "source", true));
        machines.add(MTSToAutomataConverter.getInstance().convert(
                observer, "observer", true));
        CompositeState composition = new CompositeState(machines);
        composition.compose(new EmptyLTSOuput());
        MTS<Long, String> product = AutomataToMTSConverter.getInstance()
                .convert(composition.composition);

        Map<Long, Long> provenance =
                M9CompositionProvenance.firstComponentSourceStates(
                        product, source);
		M9CompositionProvenance.Projection full =
				M9CompositionProvenance.capture(product, source);
        assertEquals(Integer.valueOf(product.getStates().size()),
                Integer.valueOf(provenance.size()));
        assertEquals(Long.valueOf(20L),
                provenance.get(product.getInitialState()));
        assertTrue(provenance.containsValue(Long.valueOf(10L)));
		assertEquals(Integer.valueOf(2),
				Integer.valueOf(full.getComponentNames().size()));
		assertEquals(Integer.valueOf(2),
				Integer.valueOf(full.getComponentSnapshots().size()));
        assertEquals(Integer.valueOf(product.getStates().size()),
                Integer.valueOf(full.getComponentStateTuples().size()));

		MTSImpl<?, ?> implementation = (MTSImpl<?, ?>) product;
		int initial = product.getInitialState().intValue();
		int[] originalInitialTuple = implementation.getStateToComponentStates()
				.get(Integer.valueOf(initial));
		implementation.getStateToComponentStates().put(
				Integer.valueOf(initial), new int[]{0, 1});
		try {
			M9CompositionProvenance.capture(product, source);
			fail("Expected a monitor-state tuple substitution to fail");
		} catch (IllegalArgumentException expected) {
			assertTrue(expected.getMessage(),
					expected.getMessage().contains("initial tuple")
					|| expected.getMessage().contains("Product Post")
					|| expected.getMessage().contains("matches no product target")
					|| expected.getMessage().contains("state domain"));
		} finally {
				implementation.getStateToComponentStates().put(
						Integer.valueOf(initial), originalInitialTuple);
		}

		Integer duplicateTarget = null;
		for (Integer state : implementation.getStateToComponentStates().keySet()) {
			if (state.intValue() != initial) {
				duplicateTarget = state;
				break;
			}
		}
		assertTrue(duplicateTarget != null);
		int[] originalDistinctTuple = implementation.getStateToComponentStates()
				.get(duplicateTarget);
		implementation.getStateToComponentStates().put(
				duplicateTarget, originalInitialTuple.clone());
		try {
			M9CompositionProvenance.capture(product, source);
			fail("Expected duplicate product tuples to fail");
		} catch (IllegalArgumentException expectedDuplicate) {
			assertTrue(expectedDuplicate.getMessage().contains("not injective"));
		} finally {
			implementation.getStateToComponentStates().put(
					duplicateTarget, originalDistinctTuple);
		}

		AbstractMap.SimpleEntry<Integer, String> diagnosticKey =
				new AbstractMap.SimpleEntry<Integer, String>(initial, "a");
		int[] originalDiagnostic = implementation
				.getStatePlusActionToComponentStates().get(diagnosticKey);
		implementation.getStatePlusActionToComponentStates().put(
				diagnosticKey, new int[]{0, 0});
		try {
			M9CompositionProvenance.capture(product, source);
			fail("Expected a first-outcome tuple substitution to fail");
		} catch (IllegalArgumentException expected) {
			assertTrue(expected.getMessage().contains("matches no product target"));
		} finally {
				implementation.getStatePlusActionToComponentStates().put(
						diagnosticKey, originalDiagnostic);
		}

		int retainedObserverEdges = full.getComponentSnapshots().get(1)
				.getTransitions().size();
		componentsOf(product)[1].states[0] = null;
		assertEquals(Integer.valueOf(retainedObserverEdges),
				Integer.valueOf(full.getComponentSnapshots().get(1)
						.getTransitions().size()));
	}

	private static CompactState[] componentsOf(MTS<Long, String> product) {
		return ((MTSImpl<?, ?>) product).getComponents();
	}

	@Test
	public void rejectsAnErrorDiagnosticWithTheWrongRawErrorCoordinate() {
		MTS<Long, String> first =
				new MTSImpl<Long, String>(Long.valueOf(0L));
		first.addState(Long.valueOf(-1L));
		first.addAction("a");
		first.addRequired(Long.valueOf(0L), "a", Long.valueOf(-1L));
		MTS<Long, String> second =
				new MTSImpl<Long, String>(Long.valueOf(0L));
		second.addState(Long.valueOf(1L));
		second.addAction("a");
		second.addRequired(Long.valueOf(0L), "a", Long.valueOf(1L));

		Vector<CompactState> machines = new Vector<CompactState>();
		machines.add(MTSToAutomataConverter.getInstance().convert(
				first, "error-first", true));
		machines.add(MTSToAutomataConverter.getInstance().convert(
				second, "ordinary-second", true));
		CompositeState composition = new CompositeState(machines);
		composition.compose(new EmptyLTSOuput());
		MTS<Long, String> product = AutomataToMTSConverter.getInstance()
				.convert(composition.composition);
		MTSImpl<?, ?> implementation = (MTSImpl<?, ?>) product;
		AbstractMap.SimpleEntry<Integer, String> key =
				new AbstractMap.SimpleEntry<Integer, String>(
						Integer.valueOf(product.getInitialState().intValue()), "a");
		int[] original = implementation.getStatePlusActionToComponentStates()
				.get(key);
		assertTrue(original != null);
		assertTrue(original[0] == -1);
		implementation.getStatePlusActionToComponentStates().put(
				key, new int[]{0, -1});
		try {
			M9CompositionProvenance.capture(product, first);
			fail("Expected the wrong raw ERROR coordinate to fail");
		} catch (IllegalArgumentException expected) {
			assertTrue(expected.getMessage().contains("exact raw component outcome"));
		} finally {
			implementation.getStatePlusActionToComponentStates().put(key, original);
		}
	}

	@Test
	public void rejectsATypeCompatibleButDifferentFirstComponent() {
		MTS<Long, String> actual = new MTSImpl<Long, String>(Long.valueOf(0L));
		actual.addState(Long.valueOf(1L));
		actual.addAction("a");
		actual.addRequired(Long.valueOf(0L), "a", Long.valueOf(1L));
		actual.addRequired(Long.valueOf(1L), "a", Long.valueOf(0L));
		MTS<Long, String> observer = new MTSImpl<Long, String>(Long.valueOf(0L));
		observer.addAction("a");
		observer.addRequired(Long.valueOf(0L), "a", Long.valueOf(0L));

		Vector<CompactState> machines = new Vector<CompactState>();
		machines.add(MTSToAutomataConverter.getInstance().convert(
				actual, "actual", true));
		machines.add(MTSToAutomataConverter.getInstance().convert(
				observer, "observer", true));
		CompositeState composition = new CompositeState(machines);
		composition.compose(new EmptyLTSOuput());
		MTS<Long, String> product = AutomataToMTSConverter.getInstance()
				.convert(composition.composition);

		MTS<Long, String> forged = new MTSImpl<Long, String>(Long.valueOf(0L));
		forged.addState(Long.valueOf(1L));
		forged.addAction("a");
		forged.addRequired(Long.valueOf(0L), "a", Long.valueOf(0L));
		forged.addRequired(Long.valueOf(1L), "a", Long.valueOf(1L));
		try {
			M9CompositionProvenance.capture(product, forged);
			fail("Expected a same-census semantic substitution to fail");
		} catch (IllegalArgumentException expected) {
			assertTrue(expected.getMessage().contains("transition relation"));
		}
	}

    @Test
    public void rejectsProductsWithoutCompositionMetadata() {
        MTS<Long, String> plain = new MTSImpl<Long, String>(Long.valueOf(0L));
        try {
            M9CompositionProvenance.firstComponentSourceStates(plain, plain);
            fail("Expected missing composition metadata to fail");
        } catch (IllegalArgumentException expected) {
            assertTrue(expected.getMessage().contains("component-state provenance"));
        }
    }

	@Test
	public void projectsAFlatProductOntoAnExactSeparatelyComposedPrefix() {
		MTS<Long, String> first = cycle();
		MTS<Long, String> second = cycle();
		MTS<Long, String> monitor = cycle();

		Vector<CompactState> endpointMachines = new Vector<CompactState>();
		endpointMachines.add(MTSToAutomataConverter.getInstance().convert(
				first, "environment-first", true));
		endpointMachines.add(MTSToAutomataConverter.getInstance().convert(
				second, "environment-second", true));
		CompositeState endpoint = new CompositeState(endpointMachines);
		endpoint.compose(new EmptyLTSOuput());
		MTS<Long, String> endpointProduct = AutomataToMTSConverter.getInstance()
				.convert(endpoint.composition);
		M9CompositionProvenance.Projection endpointAuthority =
				M9CompositionProvenance.capture(endpointProduct, first);

		Vector<CompactState> flatMachines = new Vector<CompactState>();
		flatMachines.add(MTSToAutomataConverter.getInstance().convert(
				first, "environment-first", true));
		flatMachines.add(MTSToAutomataConverter.getInstance().convert(
				second, "environment-second", true));
		flatMachines.add(MTSToAutomataConverter.getInstance().convert(
				monitor, "safety-monitor", true));
		CompositeState flat = new CompositeState(flatMachines);
		flat.compose(new EmptyLTSOuput());
		MTS<Long, String> flatProduct = AutomataToMTSConverter.getInstance()
				.convert(flat.composition);
		M9CompositionProvenance.Projection flatAuthority =
				M9CompositionProvenance.capture(flatProduct, first);

		M9CompositionProvenance.OrderedPrefixProjection prefix =
				M9CompositionProvenance.projectOrderedPrefix(
						flatAuthority, endpointAuthority);
		Map<Long, Long> prefixStates = prefix.getExtendedStateToPrefixState();
		assertEquals(Integer.valueOf(2), Integer.valueOf(prefix.getPrefixArity()));
		assertTrue(prefix.getProvenanceFreeUnsafeStates().isEmpty());
		assertEquals(Integer.valueOf(flatProduct.getStates().size()),
				Integer.valueOf(prefixStates.size()));
		for (Map.Entry<Long, Long> entry : prefixStates.entrySet()) {
			List<Integer> flatTuple = flatAuthority.getComponentStateTuples()
					.get(entry.getKey());
			List<Integer> endpointTuple =
					endpointAuthority.getComponentStateTuples().get(entry.getValue());
			assertEquals(endpointTuple, flatTuple.subList(0, 2));
		}
		assertEquals(Long.valueOf(endpointAuthority.getProductInitialState()),
				prefixStates.get(Long.valueOf(flatAuthority.getProductInitialState())));

		Vector<CompactState> reversedMachines = new Vector<CompactState>();
		reversedMachines.add(MTSToAutomataConverter.getInstance().convert(
				second, "environment-second", true));
		reversedMachines.add(MTSToAutomataConverter.getInstance().convert(
				first, "environment-first", true));
		CompositeState reversed = new CompositeState(reversedMachines);
		reversed.compose(new EmptyLTSOuput());
		M9CompositionProvenance.Projection reversedAuthority =
				M9CompositionProvenance.capture(
						AutomataToMTSConverter.getInstance().convert(
								reversed.composition), second);
		try {
			M9CompositionProvenance.projectOrderedPrefix(
					flatAuthority, reversedAuthority);
			fail("Expected an ordered prefix component substitution to fail");
		} catch (IllegalArgumentException expected) {
			assertTrue(expected.getMessage().contains("prefix differs"));
		}
	}

	@Test
	public void bindsAnAdmittedClosedLoopToBothExactChildDomains() {
		MTS<Long, String> environment = cycle();
		MTS<Long, String> controller =
				new MTSImpl<Long, String>(Long.valueOf(0L));
		controller.addState(Long.valueOf(1L));
		controller.addState(Long.valueOf(2L));
		controller.addAction("a");
		controller.addRequired(Long.valueOf(0L), "a", Long.valueOf(1L));
		controller.addRequired(Long.valueOf(1L), "a", Long.valueOf(0L));
		controller.addRequired(Long.valueOf(2L), "a", Long.valueOf(2L));
		CompactState environmentEndpoint =
				MTSToAutomataConverter.getInstance().convert(
						environment, "Enew", true);
		CompactState controllerEndpoint =
				MTSToAutomataConverter.getInstance().convert(
						controller, "Cnew", true);

		CompactStateEndpointAdmission.Admission environmentAdmission =
				CompactStateEndpointAdmission.admitPrimitive(
						environmentEndpoint, false);
		CompactStateEndpointAdmission.Admission controllerAdmission =
				CompactStateEndpointAdmission.admitPrimitive(
						controllerEndpoint, false);

		Vector<CompactState> machines = new Vector<CompactState>();
		machines.add(environmentEndpoint);
		machines.add(controllerEndpoint);
		CompositeState closedLoop = new CompositeState(machines);
		closedLoop.compose(new EmptyLTSOuput());
		MTS<Long, String> product = AutomataToMTSConverter.getInstance()
				.convert(closedLoop.composition);
		M9CompositionProvenance.Projection authority =
				M9CompositionProvenance.capture(product, environment);
		CompactStateEndpointAdmission.Admission closedLoopAdmission =
				CompactStateEndpointAdmission.admitComposed(
						closedLoop.composition, authority, false);

		Map<Long, Long> controllerOrigins = new LinkedHashMap<Long, Long>();
		controllerOrigins.put(Long.valueOf(0L), Long.valueOf(0L));
		controllerOrigins.put(Long.valueOf(1L), Long.valueOf(1L));
		controllerOrigins.put(Long.valueOf(2L), Long.valueOf(0L));
		M9CompositionProvenance.TwoCoordinateProjection coordinates =
				M9CompositionProvenance.requireTwoCoordinateConsistency(
						authority, closedLoopAdmission,
						environmentAdmission, controllerAdmission,
						M9MtsSnapshot.capture(controller), controllerOrigins);
		assertEquals(Integer.valueOf(product.getStates().size()), Integer.valueOf(
				coordinates.getProductStateCoordinates().size()));
		assertEquals(controllerOrigins,
				coordinates.getSecondStateToFirstState());
		assertEquals(Collections.singleton(Long.valueOf(2L)),
				coordinates.getUnobservedSecondComponentStates());

		Map<Long, Long> flippedOrigin =
				new LinkedHashMap<Long, Long>(controllerOrigins);
		flippedOrigin.put(Long.valueOf(1L), Long.valueOf(0L));
		try {
			M9CompositionProvenance.requireTwoCoordinateConsistency(
					authority, closedLoopAdmission,
					environmentAdmission, controllerAdmission,
					M9MtsSnapshot.capture(controller), flippedOrigin);
			fail("Expected a Cnew origin substitution to fail");
		} catch (IllegalArgumentException expected) {
			assertTrue(expected.getMessage().contains("origin-to-Enew"));
		}

		CompactState wrongController = new CompactState();
		wrongController.name = "wrong-Cnew";
		wrongController.maxStates = 3;
		wrongController.alphabet = new String[]{"tau", "a"};
		wrongController.states = new ltsa.lts.EventState[]{
				new ltsa.lts.EventState(1, 1),
				new ltsa.lts.EventState(1, 0),
				new ltsa.lts.EventState(1, 2)};
		wrongController.endseq = -9999;
		try {
			M9CompositionProvenance.requireTwoCoordinateConsistency(
					authority, closedLoopAdmission, environmentAdmission,
					CompactStateEndpointAdmission.admitPrimitive(
							wrongController, false),
					M9MtsSnapshot.capture(controller), controllerOrigins);
			fail("Expected a closed-loop child substitution to fail");
		} catch (IllegalArgumentException expected) {
			assertTrue(expected.getMessage().contains("child bytes"));
		}
	}

	private static MTS<Long, String> cycle() {
		MTS<Long, String> result =
				new MTSImpl<Long, String>(Long.valueOf(0L));
		result.addState(Long.valueOf(1L));
		result.addAction("a");
		result.addRequired(Long.valueOf(0L), "a", Long.valueOf(1L));
		result.addRequired(Long.valueOf(1L), "a", Long.valueOf(0L));
		return result;
	}
}
