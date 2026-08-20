package ltsa.updatingControllers.export;

import MTSTools.ac.ic.doc.mtstools.model.MTS;
import MTSTools.ac.ic.doc.commons.relations.Pair;
import MTSTools.ac.ic.doc.mtstools.model.impl.MTSImpl;
import ltsa.ac.ic.doc.mtstools.util.fsp.AutomataToMTSConverter;
import ltsa.ac.ic.doc.mtstools.util.fsp.MTSToAutomataConverter;
import ltsa.lts.CompactState;
import ltsa.updatingControllers.UpdateConstants;
import ltsa.updatingControllers.synthesis.UpdatingControllerSafetySynthesizer;
import ltsa.updatingControllers.synthesis.UpdatingEnvironmentGenerator;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Immutable authority captured after traditional safety preprocessing and
 * before the native updater GR solver is entered.
 */
public final class TraditionalPreGrSnapshot {
    private final M9MtsSnapshot updatingEnvironment;
    private final M9MtsSnapshot metaEnvironment;
    private final M9MtsSnapshot prunedEnvironment;
    private final M9MtsSnapshot safetyEnvironment;
    private final UpdatingEnvironmentGenerator.Provenance updatingProvenance;
    private final Map<Long, Long> metaStateToUpdatingState;
    private final Map<Long, Long> safetyStateToPrunedState;
    private final Map<Long, Long> safetyStateToUpdatingState;
	private final Set<Long> provenanceFreeUnsafeStates;
    private final Set<Long> prunedBySafetyFormula;
    private final Set<String> controllableActions;
	private final M9CompositionProvenance.Projection metaCompositionProvenance;
	private final M9CompositionProvenance.Projection safetyCompositionProvenance;
	private final M9TraditionalSafetySemanticsSnapshot safetySemantics;
	private final CompletionSeed completionSeed;

    public static TraditionalPreGrSnapshot capture(
            MTS<Long, String> updatingEnvironment,
            MTS<Long, String> metaEnvironment,
            UpdatingControllerSafetySynthesizer.SafetySynthesisResult safety,
            UpdatingEnvironmentGenerator.Provenance updatingProvenance,
			M9CompositionProvenance.Projection preSafetyMetaProvenance,
            Collection<String> controllableActions) {
		return capture(
				updatingEnvironment, metaEnvironment, safety,
				updatingProvenance, preSafetyMetaProvenance,
				controllableActions, null,
				Collections.<CompactState>emptyList(),
				Collections.<Map<Integer, Integer>>emptyList(),
				Collections.<CompactState>emptyList(),
				Collections.<Boolean>emptyList(), null);
	}

	public static TraditionalPreGrSnapshot capture(
			MTS<Long, String> updatingEnvironment,
			MTS<Long, String> metaEnvironment,
			UpdatingControllerSafetySynthesizer.SafetySynthesisResult safety,
			UpdatingEnvironmentGenerator.Provenance updatingProvenance,
			M9CompositionProvenance.Projection preSafetyMetaProvenance,
			Collection<String> controllableActions,
			MTS<Long, String> liveMappingProduct,
			List<CompactState> mappingComponents,
			List<Map<Integer, Integer>> mappingStateToRawNewState,
			List<CompactState> rawNewEnvironmentComponents,
			List<Boolean> actionSequenceMarkers,
			M9CompositionProvenance.Projection newEnvironmentAuthority) {
        if (updatingEnvironment == null || metaEnvironment == null
                || safety == null || updatingProvenance == null
				|| preSafetyMetaProvenance == null
                || controllableActions == null) {
            throw new IllegalArgumentException(
                    "Traditional pre-GR capture requires every authority input.");
        }

		M9CompositionProvenance.Projection metaComposition =
				preSafetyMetaProvenance;
		if (!metaComposition.getFirstComponentSourceStates().keySet()
				.equals(metaEnvironment.getStates().contains(Long.valueOf(-1L))
						? withoutError(metaEnvironment.getStates())
						: metaEnvironment.getStates())) {
			throw new IllegalArgumentException(
					"Pre-safety meta provenance state census changed during safety preprocessing.");
		}
		M9CompositionProvenance.Projection safetyComposition =
				M9CompositionProvenance.capture(
						safety.getSafetyEnvironment(),
						safety.getPrunedEnvironment());
        Map<Long, Long> metaToUpdating =
				metaComposition.getFirstComponentSourceStates();
        Map<Long, Long> safetyToPruned =
				safetyComposition.getFirstComponentSourceStates();
        Map<Long, Long> safetyToUpdating = new LinkedHashMap<Long, Long>();
        for (Map.Entry<Long, Long> entry : safetyToPruned.entrySet()) {
            Long metaState = entry.getValue();
            Long updatingState = metaToUpdating.get(metaState);
            if (updatingState == null) {
                throw new IllegalArgumentException(
                        "Safety-product provenance leaves the meta-environment domain.");
            }
            safetyToUpdating.put(entry.getKey(), updatingState);
        }
		Set<Long> provenanceFreeUnsafe = new LinkedHashSet<Long>(
				safety.getSafetyEnvironment().getStates());
		provenanceFreeUnsafe.removeAll(safetyToUpdating.keySet());
		if (!provenanceFreeUnsafe.isEmpty()
				&& !provenanceFreeUnsafe.equals(
						Collections.singleton(Long.valueOf(-1L)))) {
			throw new IllegalArgumentException(
					"Only LTSA ERROR may lack a unique component provenance tuple.");
		}

        Set<Long> beginSources = new LinkedHashSet<Long>();
        for (Set<Long> sources : updatingProvenance
                .getBeginUpdateSourcesByMappingState().values()) {
            beginSources.addAll(sources);
        }
        if (!beginSources.equals(updatingProvenance.getOldControllerStates())) {
            throw new IllegalArgumentException(
                    "hotSwapIn is not total over the retained old-controller states.");
        }

        for (Long updatingState : updatingProvenance
                .getMappingStateToUpdatingState().values()) {
            if (!updatingEnvironment.getStates().contains(updatingState)) {
                throw new IllegalArgumentException(
                        "Mapping provenance names an absent updating state.");
            }
        }
        for (Long oldState : updatingProvenance.getOldControllerStates()) {
            if (updatingEnvironment.getTransitions(
                    oldState, MTS.TransitionType.REQUIRED)
                    .getImage(UpdateConstants.BEGIN_UPDATE).isEmpty()) {
                throw new IllegalArgumentException(
                        "An old-controller state has no hotSwapIn outcome.");
            }
        }
		List<String> requiredLifecycle = Arrays.asList(
				UpdateConstants.STOP_OLD_SPEC,
				UpdateConstants.RECONFIGURE,
				UpdateConstants.START_NEW_SPEC);
		if (!safety.getDontDoTwiceActions().equals(requiredLifecycle)) {
			throw new IllegalArgumentException(
					"Strict pre-GR lifecycle monitor must preserve stop/reconfigure/start order.");
		}
		M9TraditionalSafetySemanticsSnapshot semantics =
				safety.getSafetySemantics();
		if (semantics == null
				|| semantics.getLifecycleProfile()
				!= M9TraditionalSafetySemanticsSnapshot.LifecycleProfile
						.ORDERED_STOP_RECONFIGURE_START_COMPLETE
				|| !semantics.getLifecycleActions().equals(requiredLifecycle)
				|| !semantics.getUnsafeStates().equals(safety.getPrunedStates())) {
			throw new IllegalArgumentException(
					"Strict pre-GR safety semantics authority is inconsistent.");
		}
		for (String action : requiredLifecycle) {
			if (!updatingEnvironment.getActions().contains(action)) {
				throw new IllegalArgumentException(
						"Strict pre-GR lifecycle action is absent: " + action);
			}
			long edges = 0L;
			for (Long state : updatingEnvironment.getStates()) {
				edges += updatingEnvironment.getTransitions(
						state, MTS.TransitionType.REQUIRED)
						.getImage(action).size();
			}
			if (edges == 0L) {
				throw new IllegalArgumentException(
						"Strict pre-GR lifecycle action has no source edge: " + action);
			}
		}
		if (controllableActions.contains(UpdateConstants.BEGIN_UPDATE)) {
			throw new IllegalArgumentException(
					"Traditional hotSwapIn must remain an uncontrollable request.");
		}
		if (!controllableActions.containsAll(requiredLifecycle)) {
			throw new IllegalArgumentException(
					"Every strict lifecycle action must be controllable.");
		}
		for (String action : controllableActions) {
			if (action == null || !updatingEnvironment.getActions().contains(action)) {
				throw new IllegalArgumentException(
						"Controllable ownership names an absent updating action: " + action);
			}
		}

		M9MtsSnapshot updatingSnapshot = M9MtsSnapshot.capture(
				updatingEnvironment);
		M9MtsSnapshot metaSnapshot = M9MtsSnapshot.capture(metaEnvironment);
		M9MtsSnapshot prunedSnapshot = M9MtsSnapshot.capture(
				safety.getPrunedEnvironment());
		M9MtsSnapshot safetySnapshot = M9MtsSnapshot.capture(
				safety.getSafetyEnvironment());
		if (!M9MtsSnapshot.canonicalEquals(
				metaSnapshot, semantics.getMetaEnvironment())) {
			throw new IllegalArgumentException(
					"Safety semantics is not bound to the captured meta environment.");
		}
		if (!metaSnapshot.getActions().containsAll(safetySnapshot.getActions())) {
			throw new IllegalArgumentException(
					"Final safety environment introduces an unauthorised action.");
		}
		CompletionSeed seed = CompletionSeed.capture(
				liveMappingProduct, mappingComponents,
				mappingStateToRawNewState, rawNewEnvironmentComponents,
				actionSequenceMarkers, newEnvironmentAuthority);
		if (seed != null) {
			Set<Long> mappingStates = new LinkedHashSet<Long>(
					seed.getMappingProduct().getProductSnapshot().getStates());
			mappingStates.remove(Long.valueOf(-1L));
			if (!mappingStates.equals(
					updatingProvenance.getMappingStateToUpdatingState().keySet())) {
				throw new IllegalArgumentException(
						"Completion mapping product differs from updating provenance.");
			}
		}

		return new TraditionalPreGrSnapshot(
				updatingSnapshot,
				metaSnapshot,
				prunedSnapshot,
				safetySnapshot,
				updatingProvenance,
                metaToUpdating,
                safetyToPruned,
                safetyToUpdating,
				provenanceFreeUnsafe,
                safety.getPrunedStates(),
				controllableActions,
				metaComposition,
				safetyComposition,
				semantics,
				seed);
    }

    private TraditionalPreGrSnapshot(
            M9MtsSnapshot updatingEnvironment,
            M9MtsSnapshot metaEnvironment,
            M9MtsSnapshot prunedEnvironment,
            M9MtsSnapshot safetyEnvironment,
            UpdatingEnvironmentGenerator.Provenance updatingProvenance,
            Map<Long, Long> metaStateToUpdatingState,
            Map<Long, Long> safetyStateToPrunedState,
            Map<Long, Long> safetyStateToUpdatingState,
            Collection<Long> provenanceFreeUnsafeStates,
            Collection<Long> prunedBySafetyFormula,
				Collection<String> controllableActions,
				M9CompositionProvenance.Projection metaCompositionProvenance,
				M9CompositionProvenance.Projection safetyCompositionProvenance,
				M9TraditionalSafetySemanticsSnapshot safetySemantics,
				CompletionSeed completionSeed) {
        this.updatingEnvironment = updatingEnvironment;
        this.metaEnvironment = metaEnvironment;
        this.prunedEnvironment = prunedEnvironment;
        this.safetyEnvironment = safetyEnvironment;
        this.updatingProvenance = updatingProvenance;
        this.metaStateToUpdatingState = immutableSortedMap(metaStateToUpdatingState);
        this.safetyStateToPrunedState = immutableSortedMap(safetyStateToPrunedState);
        this.safetyStateToUpdatingState = immutableSortedMap(safetyStateToUpdatingState);
		this.provenanceFreeUnsafeStates =
				immutableSortedLongSet(provenanceFreeUnsafeStates);
        this.prunedBySafetyFormula = immutableSortedLongSet(prunedBySafetyFormula);
        List<String> actions = new ArrayList<String>(controllableActions);
        Collections.sort(actions);
        this.controllableActions = Collections.unmodifiableSet(
                new LinkedHashSet<String>(actions));
		this.metaCompositionProvenance = metaCompositionProvenance;
		this.safetyCompositionProvenance = safetyCompositionProvenance;
		this.safetySemantics = safetySemantics;
		this.completionSeed = completionSeed;
    }

    private static Map<Long, Long> immutableSortedMap(Map<Long, Long> input) {
        List<Long> keys = new ArrayList<Long>(input.keySet());
        Collections.sort(keys);
        Map<Long, Long> result = new LinkedHashMap<Long, Long>();
        for (Long key : keys) {
            result.put(key, input.get(key));
        }
        return Collections.unmodifiableMap(result);
    }

	private static Set<Long> withoutError(Collection<Long> input) {
		Set<Long> result = new LinkedHashSet<Long>(input);
		result.remove(Long.valueOf(-1L));
		return result;
	}

    private static Set<Long> immutableSortedLongSet(Collection<Long> input) {
        List<Long> values = new ArrayList<Long>(input);
        Collections.sort(values);
        return Collections.unmodifiableSet(new LinkedHashSet<Long>(values));
    }

    public M9MtsSnapshot getUpdatingEnvironment() {
        return updatingEnvironment;
    }

    public M9MtsSnapshot getMetaEnvironment() {
        return metaEnvironment;
    }

    public M9MtsSnapshot getPrunedEnvironment() {
        return prunedEnvironment;
    }

    public M9MtsSnapshot getSafetyEnvironment() {
        return safetyEnvironment;
    }

    public UpdatingEnvironmentGenerator.Provenance getUpdatingProvenance() {
        return updatingProvenance;
    }

    public Map<Long, Long> getMetaStateToUpdatingState() {
        return metaStateToUpdatingState;
    }

    public Map<Long, Long> getSafetyStateToPrunedState() {
        return safetyStateToPrunedState;
    }

    public Map<Long, Long> getSafetyStateToUpdatingState() {
        return safetyStateToUpdatingState;
    }

	public Set<Long> getProvenanceFreeUnsafeStates() {
		return provenanceFreeUnsafeStates;
	}

    public Set<Long> getPrunedBySafetyFormula() {
        return prunedBySafetyFormula;
    }

    public Set<String> getControllableActions() {
        return controllableActions;
    }

	public M9CompositionProvenance.Projection getMetaCompositionProvenance() {
		return metaCompositionProvenance;
	}

	public M9CompositionProvenance.Projection getSafetyCompositionProvenance() {
		return safetyCompositionProvenance;
	}

	public M9TraditionalSafetySemanticsSnapshot getSafetySemantics() {
		return safetySemantics;
	}

	public CompletionSeed getCompletionSeed() {
		return completionSeed;
	}

	/**
	 * Immutable relational authority from the traditional mapping product to
	 * the exact prepared Enew product.  It identifies states only; it does not
	 * invent a synthetic hotSwapOut transition.
	 */
	public static final class CompletionSeed {
		private static final int MAX_COMPONENTS = 64;
		private final M9CompositionProvenance.Projection mappingProduct;
		private final M9CompositionProvenance.Projection newEnvironment;
		private final List<Map<Integer, Integer>> localMappingToNew;
		private final Map<Long, Long> mappingProductToNew;
		private final List<Boolean> actionSequenceMarkers;

		private CompletionSeed(
				M9CompositionProvenance.Projection mappingProduct,
				M9CompositionProvenance.Projection newEnvironment,
				List<Map<Integer, Integer>> localMappingToNew,
				Map<Long, Long> mappingProductToNew,
				List<Boolean> actionSequenceMarkers) {
			this.mappingProduct = mappingProduct;
			this.newEnvironment = newEnvironment;
			this.localMappingToNew = immutableIntegerMaps(localMappingToNew);
			this.mappingProductToNew = immutableSortedLongMap(
					mappingProductToNew);
			this.actionSequenceMarkers = Collections.unmodifiableList(
					new ArrayList<Boolean>(actionSequenceMarkers));
		}

		private static CompletionSeed capture(
				MTS<Long, String> liveMappingProduct,
				List<CompactState> mappingComponents,
				List<Map<Integer, Integer>> mappingStateToRawNewState,
				List<CompactState> rawNewEnvironmentComponents,
				List<Boolean> actionSequenceMarkers,
				M9CompositionProvenance.Projection newEnvironmentAuthority) {
			int mappings = size(mappingComponents);
			int localMaps = size(mappingStateToRawNewState);
			int newComponents = size(rawNewEnvironmentComponents);
			int markers = size(actionSequenceMarkers);
			if (mappings == 0 && localMaps == 0 && newComponents == 0
					&& markers == 0 && newEnvironmentAuthority == null) {
				return null;
			}
			if (liveMappingProduct == null || newEnvironmentAuthority == null
					|| mappings <= 0 || mappings > MAX_COMPONENTS
					|| localMaps != mappings || newComponents != mappings
					|| markers != mappings) {
				throw new IllegalArgumentException(
						"Completion seed requires one bounded relational row per component.");
			}
			for (Boolean marker : actionSequenceMarkers) {
				if (marker == null || marker.booleanValue()) {
					throw new IllegalArgumentException(
							"Completion seed forbids pre/post reconfigure action sequences.");
				}
			}

			List<CompactState> normalizedMapping =
					new ArrayList<CompactState>();
			List<CompactState> normalizedNew =
					new ArrayList<CompactState>();
			List<Map<Integer, Integer>> canonicalLocalMaps =
					new ArrayList<Map<Integer, Integer>>();
			for (int index = 0; index < mappings; index++) {
				CompactState rawMapping = requirePrimitive(
						mappingComponents.get(index), "mapping", index);
				CompactState rawNew = requirePrimitive(
						rawNewEnvironmentComponents.get(index), "new environment", index);
				CompactState mapping = normalizeRequired(rawMapping);
				CompactState newComponent = normalizeRequired(rawNew);
				Map<Integer, Integer> mappingIndex =
						rawStateToCanonicalIndex(rawMapping);
				for (int state = 0; state < mapping.maxStates; state++) {
					if (!Integer.valueOf(state).equals(
							mappingIndex.get(Integer.valueOf(state)))) {
						throw new IllegalArgumentException(
								"Mapping component normalization changed a state identifier.");
					}
				}
				Map<Integer, Integer> newIndex =
						rawStateToCanonicalIndex(rawNew);
				Map<Integer, Integer> canonical = canonicalizeLocalMap(
						mappingStateToRawNewState.get(index),
						mappingIndex, newIndex, mapping.maxStates,
						newComponent.maxStates);
				requireMappedGraphEquals(mapping, newComponent, canonical);
				normalizedMapping.add(mapping);
				normalizedNew.add(newComponent);
				canonicalLocalMaps.add(canonical);
			}

			if (!(liveMappingProduct instanceof MTSImpl)
					|| ((MTSImpl<?, ?>) liveMappingProduct).getComponents() == null
					|| ((MTSImpl<?, ?>) liveMappingProduct).getComponents().length
							!= mappings) {
				throw new IllegalArgumentException(
						"Completion mapping product has no exact component provenance.");
			}
			CompactState liveFirst = ((MTSImpl<?, ?>) liveMappingProduct)
					.getComponents()[0];
			M9CompositionProvenance.Projection mappingProjection =
					M9CompositionProvenance.capture(
							liveMappingProduct,
							AutomataToMTSConverter.getInstance().convert(
									liveFirst));
			requireExactForest(
					mappingProjection.getComponentTrees(), normalizedMapping,
					"mapping");
			requireExactForest(
					newEnvironmentAuthority.getComponentTrees(), normalizedNew,
					"new environment");

			Map<List<Integer>, Long> newTupleToProduct =
					new LinkedHashMap<List<Integer>, Long>();
			for (Map.Entry<Long, List<Integer>> entry
					: newEnvironmentAuthority.getComponentStateTuples().entrySet()) {
				if (newTupleToProduct.put(entry.getValue(), entry.getKey()) != null) {
					throw new IllegalArgumentException(
							"Enew component tuples are not injective.");
				}
			}
			Map<Long, Long> productToNew = new LinkedHashMap<Long, Long>();
			Set<Long> usedNewStates = new LinkedHashSet<Long>();
			for (Map.Entry<Long, List<Integer>> entry
					: mappingProjection.getComponentStateTuples().entrySet()) {
				List<Integer> tuple = entry.getValue();
				List<Integer> target = new ArrayList<Integer>(tuple.size());
				int defined = 0;
				for (int index = 0; index < tuple.size(); index++) {
					Integer value = canonicalLocalMaps.get(index).get(tuple.get(index));
					if (value != null) {
						defined++;
						target.add(value);
					}
				}
				if (defined != 0 && defined != tuple.size()) {
					throw new IllegalArgumentException(
							"A mapping-product tuple is only partially loadable.");
				}
				if (defined == tuple.size()) {
					Long targetState = newTupleToProduct.get(target);
					if (targetState == null || !usedNewStates.add(targetState)) {
						throw new IllegalArgumentException(
								"Completion tuple has no unique Enew product state.");
					}
					productToNew.put(entry.getKey(), targetState);
				}
			}
			if (productToNew.isEmpty()) {
				throw new IllegalArgumentException(
						"Completion seed has no loadable mapping-product state.");
			}
			return new CompletionSeed(
					mappingProjection, newEnvironmentAuthority,
					canonicalLocalMaps, productToNew, actionSequenceMarkers);
		}

		static CompletionSeed captureForSyntheticTest(
				MTS<Long, String> liveMappingProduct,
				List<CompactState> mappingComponents,
				List<Map<Integer, Integer>> mappingStateToRawNewState,
				List<CompactState> rawNewEnvironmentComponents,
				List<Boolean> actionSequenceMarkers,
				M9CompositionProvenance.Projection newEnvironmentAuthority) {
			return capture(
					liveMappingProduct, mappingComponents,
					mappingStateToRawNewState, rawNewEnvironmentComponents,
					actionSequenceMarkers, newEnvironmentAuthority);
		}

		private static int size(Collection<?> values) {
			return values == null ? 0 : values.size();
		}

		private static CompactState requirePrimitive(
				CompactState value, String role, int index) {
			if (value == null || value.getName() == null
					|| value.getName().isEmpty() || value.components != null
					|| value.stateToComponentStates != null
					|| value.statePlusActionToComponentStates != null) {
				throw new IllegalArgumentException(
						"Completion " + role + " component is not primitive at " + index + ".");
			}
			return value;
		}

		private static CompactState normalizeRequired(CompactState raw) {
			MTS<Long, String> mts = AutomataToMTSConverter.getInstance().convert(raw);
			for (Long state : mts.getStates()) {
				if (!mts.getTransitions(state, MTS.TransitionType.MAYBE).isEmpty()) {
					throw new IllegalArgumentException(
							"Completion component contains a modal transition.");
				}
			}
			CompactState result = MTSToAutomataConverter.getInstance().convert(
					mts, raw.getName(), true);
			return requirePrimitive(result, "normalized", 0);
		}

		private static Map<Integer, Integer> rawStateToCanonicalIndex(
				CompactState raw) {
			MTS<Long, String> source = AutomataToMTSConverter.getInstance().convert(raw);
			List<Long> order = M9CompositionProvenance.compactIndexToSourceState(
					source.getStates(), source.getInitialState());
			Map<Integer, Integer> result = new LinkedHashMap<Integer, Integer>();
			for (int index = 0; index < order.size(); index++) {
				Long rawState = order.get(index);
				if (rawState.longValue() < 0L
						|| rawState.longValue() > Integer.MAX_VALUE
						|| result.put(Integer.valueOf(rawState.intValue()),
								Integer.valueOf(index)) != null) {
					throw new IllegalArgumentException(
							"Completion component state indexing is invalid.");
				}
			}
			return result;
		}

		private static Map<Integer, Integer> canonicalizeLocalMap(
				Map<Integer, Integer> raw,
				Map<Integer, Integer> mappingIndex,
				Map<Integer, Integer> newIndex,
				int mappingStates,
				int newStates) {
			if (raw == null || raw.isEmpty()) {
				throw new IllegalArgumentException(
						"Completion local mapping is empty.");
			}
			List<Integer> keys = new ArrayList<Integer>(raw.keySet());
			Collections.sort(keys);
			Map<Integer, Integer> result = new LinkedHashMap<Integer, Integer>();
			Set<Integer> targets = new LinkedHashSet<Integer>();
			for (Integer rawKey : keys) {
				Integer rawValue = raw.get(rawKey);
				Integer key = mappingIndex.get(rawKey);
				Integer value = newIndex.get(rawValue);
				if (rawKey == null || rawValue == null || key == null || value == null
						|| key.intValue() < 0 || key.intValue() >= mappingStates
						|| value.intValue() < 0 || value.intValue() >= newStates
						|| result.put(key, value) != null || !targets.add(value)) {
					throw new IllegalArgumentException(
							"Completion local mapping is outside its component domains or noninjective.");
				}
			}
			return Collections.unmodifiableMap(result);
		}

		private static void requireMappedGraphEquals(
				CompactState mapping,
				CompactState newComponent,
				Map<Integer, Integer> localMap) {
			MTS<Long, String> mappingMts =
					AutomataToMTSConverter.getInstance().convert(mapping);
			MTS<Long, String> newMts =
					AutomataToMTSConverter.getInstance().convert(newComponent);
			for (Map.Entry<Integer, Integer> entry : localMap.entrySet()) {
				Set<String> actual = new LinkedHashSet<String>();
				for (Pair<String, Long> edge : mappingMts.getTransitions(
						Long.valueOf(entry.getKey().longValue()),
						MTS.TransitionType.REQUIRED)) {
					Integer target = localMap.get(Integer.valueOf(
							edge.getSecond().intValue()));
					if (target == null) {
						throw new IllegalArgumentException(
								"Mapped completion state leaves the local load domain.");
					}
					actual.add(edge.getFirst() + "\u0000" + target);
				}
				Set<String> expected = new LinkedHashSet<String>();
				for (Pair<String, Long> edge : newMts.getTransitions(
						Long.valueOf(entry.getValue().longValue()),
						MTS.TransitionType.REQUIRED)) {
					expected.add(edge.getFirst() + "\u0000" + edge.getSecond());
				}
				if (!actual.equals(expected)) {
					throw new IllegalArgumentException(
							"Mapped completion state differs from its new-environment state.");
				}
			}
		}

		private static void requireExactForest(
				List<CompactStateCanonicalTree> expected,
				List<CompactState> components,
				String role) {
			CompactState[] array = components.toArray(
					new CompactState[components.size()]);
			List<CompactStateCanonicalTree> actual =
					CompactStateCanonicalTree.captureForest(array);
			if (expected.size() != actual.size()) {
				throw new IllegalArgumentException(
						"Completion " + role + " component census differs.");
			}
			for (int index = 0; index < expected.size(); index++) {
				if (!CompactStateCanonicalTree.canonicalEquals(
						expected.get(index), actual.get(index))) {
					throw new IllegalArgumentException(
							"Completion " + role + " component forest differs at " + index + ".");
				}
			}
		}

		private static List<Map<Integer, Integer>> immutableIntegerMaps(
				List<Map<Integer, Integer>> input) {
			List<Map<Integer, Integer>> result =
					new ArrayList<Map<Integer, Integer>>();
			for (Map<Integer, Integer> row : input) {
				result.add(Collections.unmodifiableMap(
						new LinkedHashMap<Integer, Integer>(row)));
			}
			return Collections.unmodifiableList(result);
		}

		private static Map<Long, Long> immutableSortedLongMap(
				Map<Long, Long> input) {
			List<Long> keys = new ArrayList<Long>(input.keySet());
			Collections.sort(keys);
			Map<Long, Long> result = new LinkedHashMap<Long, Long>();
			for (Long key : keys) result.put(key, input.get(key));
			return Collections.unmodifiableMap(result);
		}

		public M9CompositionProvenance.Projection getMappingProduct() {
			return mappingProduct;
		}
		public M9CompositionProvenance.Projection getNewEnvironment() {
			return newEnvironment;
		}
		public List<Map<Integer, Integer>> getLocalMappingToNew() {
			return localMappingToNew;
		}
		public Map<Long, Long> getMappingProductToNew() {
			return mappingProductToNew;
		}
		public List<Boolean> getActionSequenceMarkers() {
			return actionSequenceMarkers;
		}
	}
}
