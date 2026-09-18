package ltsa.updatingControllers.export;

import MTSSynthesis.controller.gr.StrategyState;
import MTSTools.ac.ic.doc.commons.relations.BinaryRelation;
import MTSTools.ac.ic.doc.commons.relations.Pair;
import MTSTools.ac.ic.doc.mtstools.model.MTS;

import java.util.ArrayList;
import java.util.ArrayDeque;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;

/**
 * Immutable, decision-free validation of the native endpoint strategy returned
 * by the single post-T1 GR call.  This type never invokes a solver.  It binds
 * native {@link StrategyState} coordinates to the exact plain-controller IDs
 * and through the admitted plant/prefix provenance to Enew source states.
 * This is a structural validator, not a standalone solver attestation: the
 * production materializer must pass the rewrite-action set captured by the
 * same dispatcher invocation and bind the returned snapshot into its receipt.
 */
public final class M9EndpointStrategySnapshot {
    private final M9MtsSnapshot plainController;
	private final M9MtsSnapshot solverEnvironment;
	private final M9MtsSnapshot solverPlant;
	private final M9CompositionProvenance.Projection plantComposition;
	private final M9CompositionProvenance.OrderedPrefixProjection environmentPrefix;
	private final int guaranteeCount;
	private final int maxLaziness;
    private final Map<Long, StateCoordinates> plainStateCoordinates;
    private final Map<Long, Long> controllerStateToEnewState;

    private M9EndpointStrategySnapshot(
            M9MtsSnapshot plainController,
			M9MtsSnapshot solverEnvironment,
			M9MtsSnapshot solverPlant,
			M9CompositionProvenance.Projection plantComposition,
			M9CompositionProvenance.OrderedPrefixProjection environmentPrefix,
			int guaranteeCount,
			int maxLaziness,
            Map<Long, StateCoordinates> plainStateCoordinates,
            Map<Long, Long> controllerStateToEnewState) {
        this.plainController = plainController;
		this.solverEnvironment = solverEnvironment;
		this.solverPlant = solverPlant;
		this.plantComposition = plantComposition;
		this.environmentPrefix = environmentPrefix;
		this.guaranteeCount = guaranteeCount;
		this.maxLaziness = maxLaziness;
        this.plainStateCoordinates = Collections.unmodifiableMap(
                new LinkedHashMap<Long, StateCoordinates>(plainStateCoordinates));
        this.controllerStateToEnewState = Collections.unmodifiableMap(
                new LinkedHashMap<Long, Long>(controllerStateToEnewState));
    }

    public static M9EndpointStrategySnapshot capture(
            MTS<StrategyState<Long, Integer>, String> nativeController,
            MTS<Long, String> plainController,
            Map<StrategyState<Long, Integer>, Long> nativeToPlainState,
			MTS<Long, String> solverEnvironment,
			MTS<Long, String> solverPlant,
            M9CompositionProvenance.Projection plantComposition,
            M9CompositionProvenance.OrderedPrefixProjection
                    solverEnvironmentToEnew,
			Set<String> legacyControllerRewriteActions,
			int guaranteeCount,
			int maxLaziness) {
        if (nativeController == null || plainController == null
                || nativeToPlainState == null || solverEnvironment == null
				|| solverPlant == null || plantComposition == null
                || solverEnvironmentToEnew == null
				|| legacyControllerRewriteActions == null
				|| guaranteeCount <= 0 || maxLaziness < 0) {
            throw new IllegalArgumentException(
                    "Native/plain controllers, mapping, and provenance are required.");
        }
		if (!legacyControllerRewriteActions.isEmpty()) {
			throw new IllegalArgumentException(
					"Legacy controller self-loop rewriting is outside the exact native/plain profile.");
		}
        if (!solverEnvironmentToEnew.getProvenanceFreeUnsafeStates().isEmpty()) {
            throw new IllegalArgumentException(
                    "Solver environment prefix retains an untyped unsafe state.");
		}
		M9MtsSnapshot environmentSnapshot = solverEnvironmentToEnew
				.getExtendedProductAuthority().getProductSnapshot();
		M9MtsSnapshot plantSnapshot = plantComposition.getProductSnapshot();
		M9MtsSnapshot.requireStableSourceEquals(
				solverEnvironment, environmentSnapshot);
		M9MtsSnapshot.requireStableSourceEquals(solverPlant, plantSnapshot);
		requireExactProvenanceChain(
				environmentSnapshot, plantSnapshot,
				plantComposition, solverEnvironmentToEnew);

        M9MtsSnapshot plainSnapshot = M9MtsSnapshot.capture(plainController);
        requireDensePlainDomain(plainSnapshot);
        CapturedNative first = captureNative(
                nativeController, nativeToPlainState,
                plantComposition, solverEnvironmentToEnew, plainSnapshot,
				plantSnapshot, guaranteeCount, maxLaziness);
        CapturedNative second = captureNative(
                nativeController, nativeToPlainState,
                plantComposition, solverEnvironmentToEnew, plainSnapshot,
				plantSnapshot, guaranteeCount, maxLaziness);
        if (!first.equalsCanonical(second)) {
            throw new IllegalArgumentException(
                    "Native strategy or plain controller changed during capture.");
        }
		M9MtsSnapshot.requireStableSourceEquals(plainController, plainSnapshot);
		M9MtsSnapshot.requireStableSourceEquals(
				solverEnvironment, environmentSnapshot);
		M9MtsSnapshot.requireStableSourceEquals(solverPlant, plantSnapshot);
		CapturedNative finalNative = captureNative(
				nativeController, nativeToPlainState,
				plantComposition, solverEnvironmentToEnew, plainSnapshot,
				plantSnapshot, guaranteeCount, maxLaziness);
		if (!first.equalsCanonical(finalNative)) {
			throw new IllegalArgumentException(
					"Native strategy changed during final authority verification.");
		}
        return new M9EndpointStrategySnapshot(
                plainSnapshot, environmentSnapshot, plantSnapshot,
				plantComposition, solverEnvironmentToEnew,
				guaranteeCount, maxLaziness,
				first.coordinates, first.enewOrigins);
    }

    private static CapturedNative captureNative(
            MTS<StrategyState<Long, Integer>, String> nativeController,
            Map<StrategyState<Long, Integer>, Long> nativeToPlainState,
            M9CompositionProvenance.Projection plantComposition,
            M9CompositionProvenance.OrderedPrefixProjection prefix,
            M9MtsSnapshot plain,
			M9MtsSnapshot plant,
			int guaranteeCount,
			int maxLaziness) {
        StrategyState<Long, Integer> nativeInitial =
                nativeController.getInitialState();
        Set<StrategyState<Long, Integer>> nativeStates =
                nativeController.getStates();
        Set<String> nativeActions = nativeController.getActions();
        if (nativeInitial == null || nativeStates == null || nativeActions == null
                || !nativeStates.contains(nativeInitial)) {
            throw new IllegalArgumentException(
                    "Native strategy has no retained finite initial state.");
        }
        M9MtsSnapshot.requireResourceCensus(
                nativeStates.size(), nativeActions.size(), 0L, 0L);
        if (nativeToPlainState.size() != nativeStates.size()
                || !nativeToPlainState.keySet().equals(nativeStates)) {
            throw new IllegalArgumentException(
                    "Native-to-plain mapping domain differs from strategy states.");
        }

        Map<Long, StrategyState<Long, Integer>> plainToNative =
                new LinkedHashMap<Long, StrategyState<Long, Integer>>();
        for (StrategyState<Long, Integer> state : nativeStates) {
            Long plainState = nativeToPlainState.get(state);
            if (state == null || plainState == null
                    || plainToNative.put(plainState, state) != null) {
                throw new IllegalArgumentException(
                        "Native-to-plain mapping is null or noninjective.");
            }
        }
        if (!plainToNative.keySet().equals(plain.getStates())
                || !Long.valueOf(plain.getInitialState()).equals(
                        nativeToPlainState.get(nativeInitial))) {
            throw new IllegalArgumentException(
                    "Native-to-plain mapping is not a total initial-preserving bijection.");
        }
		if (!Long.valueOf(plant.getInitialState()).equals(
				nativeInitial.getState())
				|| nativeInitial.getMemory() == null
				|| nativeInitial.getMemory().intValue() != 1
				|| nativeInitial.getLazyness() == null
				|| nativeInitial.getLazyness().intValue() != maxLaziness) {
			throw new IllegalArgumentException(
					"Native strategy initial coordinate differs from the registered GR profile.");
		}

        Set<String> actionDomain = new LinkedHashSet<String>(nativeActions);
        if (actionDomain.contains(null) || !actionDomain.equals(plain.getActions())) {
            throw new IllegalArgumentException(
                    "Native and plain controller alphabets differ.");
        }
		if (!actionDomain.containsAll(plant.getActions())) {
			throw new IllegalArgumentException(
					"Native strategy alphabet omits a registered plant action.");
		}
		for (String plantAction : plant.getActions()) {
			if (plantAction.startsWith("#w#_")) {
				throw new IllegalArgumentException(
						"Plant alphabet collides with the reserved rank-alias namespace.");
			}
		}
		for (String action : actionDomain) {
			if (action.startsWith("#w#_")
					|| !plant.getActions().contains(action)) {
				throw new IllegalArgumentException(
						"Native strategy rank aliases are outside the exact Cnew/CLnew profile.");
			}
		}

        Map<Long, StateCoordinates> coordinates =
                new LinkedHashMap<Long, StateCoordinates>();
        Map<Long, Long> enewOrigins = new LinkedHashMap<Long, Long>();
        long buckets = 0L;
        long outcomes = 0L;
		for (Long plainState : new TreeSet<Long>(plainToNative.keySet())) {
            StrategyState<Long, Integer> state = plainToNative.get(plainState);
            Long plantState = state.getState();
            Integer memory = state.getMemory();
            Integer laziness = state.getLazyness();
            if (plantState == null || memory == null || laziness == null) {
                throw new IllegalArgumentException(
                        "Native strategy coordinates must be fully typed.");
            }
			if (memory.intValue() < 1 || memory.intValue() > guaranteeCount
					|| laziness.intValue() < 0
					|| laziness.intValue() > maxLaziness) {
				throw new IllegalArgumentException(
						"Native strategy memory/laziness leaves the registered GR profile.");
			}
            Long solverEnvironmentState =
                    plantComposition.getFirstComponentSourceStates().get(plantState);
            Long enewState = solverEnvironmentState == null ? null
                    : prefix.getExtendedStateToPrefixState().get(
                            solverEnvironmentState);
            if (solverEnvironmentState == null || enewState == null) {
                throw new IllegalArgumentException(
                        "Native strategy plant state leaves the Enew provenance chain.");
            }
            StateCoordinates coordinate = new StateCoordinates(
                    plantState.longValue(), memory.intValue(),
                    laziness.intValue(), enewState.longValue());
            coordinates.put(plainState, coordinate);
            enewOrigins.put(plainState, enewState);

            BinaryRelation<String, StrategyState<Long, Integer>> maybe =
                    nativeController.getTransitions(
                            state, MTS.TransitionType.MAYBE);
            BinaryRelation<String, StrategyState<Long, Integer>> required =
                    nativeController.getTransitions(
                            state, MTS.TransitionType.REQUIRED);
            if (maybe == null || required == null || !maybe.isEmpty()) {
                throw new IllegalArgumentException(
                        "Native endpoint strategy contains MAYBE or missing rows.");
            }
            Map<String, Set<Long>> row =
                    new LinkedHashMap<String, Set<Long>>();
            for (Pair<String, StrategyState<Long, Integer>> edge : required) {
                if (edge == null || edge.getFirst() == null
                        || edge.getSecond() == null
                        || !actionDomain.contains(edge.getFirst())) {
                    throw new IllegalArgumentException(
                            "Native strategy transition leaves its declared domain.");
                }
                Long target = nativeToPlainState.get(edge.getSecond());
                if (target == null) {
                    throw new IllegalArgumentException(
                            "Native strategy transition target has no plain state.");
                }
				String plantAction = edge.getFirst();
				if (plantAction.isEmpty()
						|| !plant.getActions().contains(plantAction)) {
					throw new IllegalArgumentException(
							"Native strategy action has no registered plant action.");
				}
				Long targetPlantState = edge.getSecond().getState();
				Set<Long> plantTargets = plant.getPost().get(plantState)
						.get(plantAction);
				if (targetPlantState == null || plantTargets == null
						|| !plantTargets.contains(targetPlantState)) {
					throw new IllegalArgumentException(
							"Native strategy edge is not a registered plant Post edge.");
				}
                Set<Long> targets = row.get(edge.getFirst());
                if (targets == null) {
					M9MtsSnapshot.requireResourceCensus(
							nativeStates.size(), nativeActions.size(),
							buckets + 1L, outcomes);
                    targets = new TreeSet<Long>();
                    row.put(edge.getFirst(), targets);
                    buckets++;
                }
				M9MtsSnapshot.requireResourceCensus(
						nativeStates.size(), nativeActions.size(),
						buckets, outcomes + 1L);
                if (!targets.add(target)) {
                    throw new IllegalArgumentException(
                            "Duplicate native strategy transition is noncanonical.");
                }
                outcomes++;
            }
            List<String> labels = new ArrayList<String>(row.keySet());
            Collections.sort(labels);
            Map<String, Set<Long>> canonicalRow =
                    new LinkedHashMap<String, Set<Long>>();
            for (String label : labels) {
                canonicalRow.put(label, Collections.unmodifiableSet(
                        new LinkedHashSet<Long>(row.get(label))));
            }
			if (!canonicalRow.equals(plain.getPost().get(plainState))) {
				throw new IllegalArgumentException(
						"Native strategy and plain controller Post differ under the mapping.");
			}
        }
        M9MtsSnapshot.requireResourceCensus(
                nativeStates.size(), nativeActions.size(), buckets, outcomes);
		requireReachability(plain);
        return new CapturedNative(coordinates, enewOrigins,
                actionDomain, nativeToPlainState.get(nativeInitial));
    }

    private static void requireDensePlainDomain(M9MtsSnapshot plain) {
        if (plain.getInitialState() != 0L
                || plain.getStates().contains(Long.valueOf(-1L))) {
            throw new IllegalArgumentException(
                    "Plain controller must use the converter's non-ERROR initial zero domain.");
        }
        long expected = 0L;
        for (Long state : new TreeSet<Long>(plain.getStates())) {
            if (state.longValue() != expected++) {
                throw new IllegalArgumentException(
                        "Plain controller state IDs are not the converter's dense domain.");
            }
        }
    }

	private static void requireExactProvenanceChain(
			M9MtsSnapshot environment,
			M9MtsSnapshot plantSnapshot,
			M9CompositionProvenance.Projection plant,
			M9CompositionProvenance.OrderedPrefixProjection prefix) {
		M9CompositionProvenance.Projection extended =
				prefix.getExtendedProductAuthority();
		if (!M9MtsSnapshot.canonicalEquals(
				plantSnapshot, plant.getProductSnapshot())
				|| !M9MtsSnapshot.canonicalEquals(
						environment, extended.getProductSnapshot())
				|| plant.getComponentTrees().isEmpty()
				|| !M9MtsSnapshot.canonicalEquals(
						plant.getFirstComponentSourceSnapshot(),
						extended.getProductSnapshot())) {
			throw new IllegalArgumentException(
					"Plant first-component authority is not the prefix's extended product.");
		}
		Long environmentInitial = Long.valueOf(environment.getInitialState());
		Long enewInitial = prefix.getExtendedStateToPrefixState().get(
				environmentInitial);
		if (!environmentInitial.equals(Long.valueOf(
				plant.getFirstComponentSourceSnapshot().getInitialState()))
				|| !Long.valueOf(prefix.getPrefixProductAuthority()
						.getProductInitialState()).equals(enewInitial)) {
			throw new IllegalArgumentException(
					"Plant/environment/Enew provenance does not preserve initial states.");
		}
		CompactStateCanonicalTree plantFirstTree =
				plant.getComponentTrees().get(0);
		if (plantFirstTree.getChildren().size()
				!= extended.getComponentTrees().size()) {
			throw new IllegalArgumentException(
					"Plant first-component tree differs from the prefix authority.");
		}
		for (int index = 0; index < plantFirstTree.getChildren().size(); index++) {
			if (!CompactStateCanonicalTree.canonicalEquals(
					plantFirstTree.getChildren().get(index),
					extended.getComponentTrees().get(index))) {
				throw new IllegalArgumentException(
						"Plant first-component tree differs from the prefix authority.");
			}
		}
		Map<Integer, List<Integer>> rawTuples =
				plantFirstTree.getSnapshot().getComponentStateTuples();
		if (rawTuples.size() != extended.getComponentStateTuples().size()) {
			throw new IllegalArgumentException(
					"Plant first-component tuple authority differs from the prefix product.");
		}
		for (Map.Entry<Long, List<Integer>> entry
				: extended.getComponentStateTuples().entrySet()) {
			if (!entry.getValue().equals(rawTuples.get(
					Integer.valueOf(entry.getKey().intValue())))) {
				throw new IllegalArgumentException(
						"Plant first-component tuple authority differs from the prefix product.");
			}
		}
		if (!plantFirstTree.getSnapshot().getNativeFirstOutcomeDiagnostics()
				.equals(extended.getNativeFirstOutcomeDiagnostics())) {
			throw new IllegalArgumentException(
					"Plant first-component diagnostic authority differs from the prefix product.");
		}
	}

	private static void requireReachability(M9MtsSnapshot controller) {
		Set<Long> reached = new LinkedHashSet<Long>();
		ArrayDeque<Long> pending = new ArrayDeque<Long>();
		Long initial = Long.valueOf(controller.getInitialState());
		reached.add(initial);
		pending.add(initial);
		while (!pending.isEmpty()) {
			Long state = pending.removeFirst();
			for (Set<Long> targets : controller.getPost().get(state).values()) {
				for (Long target : targets) {
					if (reached.add(target)) pending.addLast(target);
				}
			}
		}
		if (!reached.equals(controller.getStates())) {
			throw new IllegalArgumentException(
					"Native endpoint controller retains an unreachable state.");
		}
	}

    public M9MtsSnapshot getPlainController() {
        return plainController;
    }

	public M9MtsSnapshot getSolverEnvironment() { return solverEnvironment; }
	public M9MtsSnapshot getSolverPlant() { return solverPlant; }
	public M9CompositionProvenance.Projection getPlantComposition() {
		return plantComposition;
	}
	public M9CompositionProvenance.OrderedPrefixProjection getEnvironmentPrefix() {
		return environmentPrefix;
	}
	public int getGuaranteeCount() { return guaranteeCount; }
	public int getMaxLaziness() { return maxLaziness; }

    public Map<Long, StateCoordinates> getPlainStateCoordinates() {
        return plainStateCoordinates;
    }

    public Map<Long, Long> getControllerStateToEnewState() {
        return controllerStateToEnewState;
    }

    public static final class StateCoordinates {
        private final long plantState;
        private final int memory;
        private final int laziness;
        private final long enewState;

        private StateCoordinates(
                long plantState,
                int memory,
                int laziness,
                long enewState) {
            this.plantState = plantState;
            this.memory = memory;
            this.laziness = laziness;
            this.enewState = enewState;
        }

        public long getPlantState() { return plantState; }
        public int getMemory() { return memory; }
        public int getLaziness() { return laziness; }
        public long getEnewState() { return enewState; }

        @Override
        public boolean equals(Object other) {
            if (this == other) return true;
            if (!(other instanceof StateCoordinates)) return false;
            StateCoordinates value = (StateCoordinates) other;
            return plantState == value.plantState && memory == value.memory
                    && laziness == value.laziness && enewState == value.enewState;
        }

        @Override
        public int hashCode() {
            int result = Long.valueOf(plantState).hashCode();
            result = 31 * result + memory;
            result = 31 * result + laziness;
            return 31 * result + Long.valueOf(enewState).hashCode();
        }
    }

    private static final class CapturedNative {
        private final Map<Long, StateCoordinates> coordinates;
        private final Map<Long, Long> enewOrigins;
        private final Set<String> actions;
        private final Long initialPlainState;

        private CapturedNative(
                Map<Long, StateCoordinates> coordinates,
                Map<Long, Long> enewOrigins,
                Set<String> actions,
                Long initialPlainState) {
            this.coordinates = Collections.unmodifiableMap(
                    new LinkedHashMap<Long, StateCoordinates>(coordinates));
            this.enewOrigins = Collections.unmodifiableMap(
                    new LinkedHashMap<Long, Long>(enewOrigins));
            this.actions = Collections.unmodifiableSet(
                    new LinkedHashSet<String>(actions));
            this.initialPlainState = initialPlainState;
        }

        private boolean equalsCanonical(CapturedNative other) {
            return other != null && coordinates.equals(other.coordinates)
                    && enewOrigins.equals(other.enewOrigins)
					&& actions.equals(other.actions)
                    && initialPlainState.equals(other.initialPlainState);
        }
    }
}
