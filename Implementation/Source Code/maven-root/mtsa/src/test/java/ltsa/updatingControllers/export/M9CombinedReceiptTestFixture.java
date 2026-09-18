package ltsa.updatingControllers.export;

import MTSSynthesis.ar.dc.uba.model.condition.Fluent;
import MTSSynthesis.ar.dc.uba.model.condition.Formula;
import MTSSynthesis.controller.gr.StrategyState;
import MTSTools.ac.ic.doc.commons.relations.Pair;
import MTSTools.ac.ic.doc.mtstools.model.MTS;
import MTSTools.ac.ic.doc.mtstools.model.impl.MTSImpl;
import MTSTools.ac.ic.doc.mtstools.utils.GenericMTSToLongStringMTSConverter;
import ltsa.ac.ic.doc.mtstools.util.fsp.AutomataToMTSConverter;
import ltsa.ac.ic.doc.mtstools.util.fsp.MTSToAutomataConverter;
import ltsa.control.util.ControllerUtils;
import ltsa.lts.CompactState;
import ltsa.lts.CompositeState;
import ltsa.lts.EmptyLTSOuput;
import ltsa.lts.EventState;
import ltsa.lts.EventStateUtils;
import ltsa.updatingControllers.UpdateConstants;
import ltsa.updatingControllers.synthesis.UpdatingControllerSafetySynthesizer;
import ltsa.updatingControllers.synthesis.UpdatingEnvironmentGenerator;

import java.lang.reflect.Constructor;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Set;
import java.util.Vector;

/** Solver-free, one-state combined-receipt authority used only by tests. */
final class M9CombinedReceiptTestFixture {
	final M9EndpointStrategySnapshot strategy;
	final M9ClosedLoopEndpointSnapshot closedLoop;
	final TraditionalPreGrSnapshot traditional;

	private M9CombinedReceiptTestFixture(
			M9EndpointStrategySnapshot strategy,
			M9ClosedLoopEndpointSnapshot closedLoop,
			TraditionalPreGrSnapshot traditional) {
		this.strategy = strategy;
		this.closedLoop = closedLoop;
		this.traditional = traditional;
	}

	static M9CombinedReceiptTestFixture create() {
		CompactState mapping = mappingComponent();
		CompactState enewComponent = newComponent();
		Product mappingProduct = product("MAPPING", mapping);
		Product enew = product("ENEW", enewComponent);

		MTS<Long, String> old = new MTSImpl<Long, String>(Long.valueOf(0L));
		for (String action : Collections.singletonList("a")) {
			old.addAction(action);
			old.addRequired(Long.valueOf(0L), action, Long.valueOf(0L));
		}
		UpdatingEnvironmentGenerator generator =
				new UpdatingEnvironmentGenerator(old, mappingProduct.mts, true);
		generator.generateEnvironment();
		MTS<Long, String> updating = ControllerUtils.UpdateEnvironment2MTS(
				generator.getUpdEnv());
		MTS<Long, String> meta = ControllerUtils.removeTopStates(
				updating, Collections.<Fluent>emptySet());
		M9CompositionProvenance.Projection metaProjection =
				M9CompositionProvenance.capture(meta, updating);
		Set<String> controllable = new LinkedHashSet<String>(Arrays.asList(
				"a", UpdateConstants.STOP_OLD_SPEC,
				UpdateConstants.RECONFIGURE,
				UpdateConstants.START_NEW_SPEC));
		UpdatingControllerSafetySynthesizer.SafetySynthesisResult safety =
				UpdatingControllerSafetySynthesizer.synthesizeSafetyWithProvenance(
						meta, Collections.<Fluent>emptySet(),
						Collections.<Formula>emptyList(), controllable,
						Arrays.asList(
								UpdateConstants.STOP_OLD_SPEC,
								UpdateConstants.RECONFIGURE,
								UpdateConstants.START_NEW_SPEC),
						new EmptyLTSOuput());
		TraditionalPreGrSnapshot traditional = TraditionalPreGrSnapshot.capture(
				updating, meta, safety, generator.getProvenance(), metaProjection,
				controllable, mappingProduct.mts,
				Collections.singletonList(mapping),
				Collections.singletonList(Collections.singletonMap(1, 0)),
				Collections.singletonList(enewComponent),
				Collections.singletonList(Boolean.FALSE), enew.authority);

		Product solverEnvironment = product(
				"SOURCE", enewComponent, safetySuffixComponent());
		M9CompositionProvenance.OrderedPrefixProjection prefix =
				M9CompositionProvenance.projectOrderedPrefix(
						solverEnvironment.authority, enew.authority);
		CompactState neutral = newComponent();
		neutral.name = "FLUENT_NEUTRAL";
		Product plant = product(
				"PLANT", solverEnvironment.composition, neutral);
		M9CompositionProvenance.Projection plantAuthority =
				M9CompositionProvenance.capture(
						plant.mts, solverEnvironment.mts);

		Map<Long, StrategyState<Long, Integer>> nativeStates =
				new LinkedHashMap<Long, StrategyState<Long, Integer>>();
		for (Long state : plant.mts.getStates()) {
			nativeStates.put(state, new StrategyState<Long, Integer>(
					state, Integer.valueOf(1), Integer.valueOf(0)));
		}
		MTS<StrategyState<Long, Integer>, String> nativeController =
				new MTSImpl<StrategyState<Long, Integer>, String>(
						nativeStates.get(plant.mts.getInitialState()));
		nativeController.addStates(nativeStates.values());
		nativeController.addActions(plant.mts.getActions());
		for (Long state : plant.mts.getStates()) {
			for (Pair<String, Long> edge : plant.mts.getTransitions(
					state, MTS.TransitionType.REQUIRED)) {
				nativeController.addRequired(
						nativeStates.get(state), edge.getFirst(),
						nativeStates.get(edge.getSecond()));
			}
		}
		GenericMTSToLongStringMTSConverter<StrategyState<Long, Integer>, String>
				converter = new GenericMTSToLongStringMTSConverter<
						StrategyState<Long, Integer>, String>();
		MTS<Long, String> plain = converter.transform(nativeController);
		Map<StrategyState<Long, Integer>, Long> nativeToPlain =
				new LinkedHashMap<StrategyState<Long, Integer>, Long>(
						converter.getStateMapping());
		M9EndpointStrategySnapshot strategy = M9EndpointStrategySnapshot.capture(
				nativeController, plain, nativeToPlain,
				solverEnvironment.mts, plant.mts,
				plantAuthority, prefix, Collections.<String>emptySet(), 1, 0);
		CompactStateEndpointAdmission.Admission enewAdmission =
				CompactStateEndpointAdmission.admitComposed(
						enew.composition, enew.authority, false);
		CompactState cnew = MTSToAutomataConverter.getInstance().convert(
				plain, "Cnew", true);
		M9ClosedLoopEndpointSnapshot closedLoop =
				M9ClosedLoopEndpointSnapshot.capture(
						enew.composition, enewAdmission, cnew, strategy);
		return new M9CombinedReceiptTestFixture(strategy, closedLoop, traditional);
	}

	static TraditionalPreGrSnapshotHook.SealedCapture sealed(
			TraditionalPreGrSnapshot snapshot) throws Exception {
		Constructor<TraditionalPreGrSnapshotHook.SealedCapture> constructor =
				TraditionalPreGrSnapshotHook.SealedCapture.class.getDeclaredConstructor(
						TraditionalPreGrSnapshot.class, Integer.TYPE, Integer.TYPE,
						Boolean.TYPE, Boolean.TYPE);
		constructor.setAccessible(true);
		return constructor.newInstance(
				snapshot, Integer.valueOf(1), Integer.valueOf(0),
				Boolean.TRUE, Boolean.TRUE);
	}

	private static CompactState mappingComponent() {
		CompactState state = new CompactState("MAP");
		state.maxStates = 2;
		state.alphabet = new String[]{
				"tau", "a", UpdateConstants.RECONFIGURE};
		state.states = new EventState[2];
		add(state, 0, 1, 0);
		add(state, 0, 2, 1);
		add(state, 1, 1, 1);
		return state;
	}

	private static CompactState newComponent() {
		CompactState state = new CompactState("NEW");
		state.maxStates = 1;
		state.alphabet = new String[]{"tau", "a"};
		state.states = new EventState[1];
		add(state, 0, 1, 0);
		return state;
	}

	private static CompactState safetySuffixComponent() {
		CompactState state = new CompactState("SAFETY_SUFFIX");
		state.maxStates = 2;
		state.alphabet = new String[]{"tau", "a"};
		state.states = new EventState[2];
		add(state, 0, 1, 1);
		add(state, 1, 1, 0);
		return state;
	}

	private static void add(
			CompactState state, int from, int action, int target) {
		state.states[from] = EventStateUtils.add(
				state.states[from], new EventState(action, target));
	}

	private static Product product(String name, CompactState... components) {
		try {
			Vector<CompactState> machines = new Vector<CompactState>();
			for (CompactState component : components) {
				machines.add(component.myclone());
			}
			CompositeState composite = new CompositeState(name, machines);
			composite.compose(new EmptyLTSOuput());
			MTS<Long, String> mts = AutomataToMTSConverter.getInstance().convert(
					composite.composition);
			MTS<Long, String> first = AutomataToMTSConverter.getInstance().convert(
					components[0]);
			return new Product(
					composite.composition, mts,
					M9CompositionProvenance.capture(mts, first));
		} catch (IllegalArgumentException error) {
			throw new IllegalArgumentException(
					"Combined fixture product " + name + " failed: "
							+ error.getMessage(), error);
		}
	}

	private static final class Product {
		private final CompactState composition;
		private final MTS<Long, String> mts;
		private final M9CompositionProvenance.Projection authority;

		private Product(
				CompactState composition,
				MTS<Long, String> mts,
				M9CompositionProvenance.Projection authority) {
			this.composition = composition;
			this.mts = mts;
			this.authority = authority;
		}
	}
}
