package ltsa.updatingControllers.export;

import MTSTools.ac.ic.doc.mtstools.model.MTS;
import MTSTools.ac.ic.doc.mtstools.model.impl.MTSImpl;
import MTSTools.ac.ic.doc.commons.relations.Pair;
import ltsa.lts.CompactState;

import java.util.AbstractMap;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;

/**
 * Fail-closed extraction of the first component state from an MTSA parallel
 * composition.  MTSToAutomataConverter reindexes Long state identifiers, so
 * the component index is translated back through the exact converter order
 * instead of being mistaken for the original source identifier.
 */
public final class M9CompositionProvenance {
	private static final long MAX_COMPOSITION_BUCKETS = 2_000_000L;
	private static final int MAX_PROJECTION_STATES = 250_000;
	private static final int MAX_PROJECTION_COMPONENTS = 64;
	private static final long MAX_PROJECTION_TUPLE_CELLS = 16_000_000L;
	private static final long MAX_DERIVED_OUTCOME_TUPLES = 4_000_000L;
    private M9CompositionProvenance() {
    }

    public static Map<Long, Long> firstComponentSourceStates(
            MTS<Long, String> product,
            MTS<Long, String> firstComponentSource) {
		return capture(product, firstComponentSource)
				.getFirstComponentSourceStates();
	}

	public static Projection capture(
			MTS<Long, String> product,
			MTS<Long, String> firstComponentSource) {
		M9MtsSnapshot productSnapshot = M9MtsSnapshot.capture(product);
		M9MtsSnapshot firstComponentSourceSnapshot =
				M9MtsSnapshot.capture(firstComponentSource);
        if (!(product instanceof MTSImpl)) {
            throw new IllegalArgumentException(
                    "Product must retain MTSImpl composition metadata.");
        }
        MTSImpl<?, ?> implementation = (MTSImpl<?, ?>) product;
        CompactState[] components = copyComponentReferences(
				implementation.getComponents());
        Map<Integer, int[]> tuples = copyStateTupleMetadata(
				implementation.getStateToComponentStates(),
				productSnapshot.getStates().size(), components.length);
        if (components == null || components.length == 0
                || tuples == null || tuples.isEmpty()) {
            throw new IllegalArgumentException(
                    "Product has no component-state provenance.");
        }
		requireProjectionBound(
				productSnapshot.getStates().size()
						- (productSnapshot.getStates().contains(Long.valueOf(-1L)) ? 1 : 0),
				components.length);
		requireBucketBound(
				productSnapshot.getStates().size(),
				productSnapshot.getActions().size());
		List<CompactStateCanonicalTree> componentTrees =
				CompactStateCanonicalTree.captureForest(components);
		List<CompactStateCanonicalSnapshot> componentSnapshots =
				rootSnapshots(componentTrees);

        List<Long> compactIndexToSource = compactIndexToSourceState(
                firstComponentSourceSnapshot.getStates(),
                Long.valueOf(firstComponentSourceSnapshot.getInitialState()));
		verifyComponentSnapshotSemantics(
				componentSnapshots.get(0),
				firstComponentSourceSnapshot, compactIndexToSource,
				"First component");
        if (componentSnapshots.get(0).getStateCount()
				!= compactIndexToSource.size()) {
            throw new IllegalArgumentException(
                    "First component state census differs from source MTS.");
        }

		List<String> componentNames = new ArrayList<String>();
		for (CompactStateCanonicalSnapshot component : componentSnapshots) {
			if (component.getName() == null || component.getName().isEmpty()
					|| component.getStateCount() <= 0) {
				throw new IllegalArgumentException(
						"Product component descriptor is invalid.");
			}
			componentNames.add(component.getName());
		}

        Map<Long, Long> result = new LinkedHashMap<Long, Long>();
		Map<Long, List<Integer>> fullTuples =
				new LinkedHashMap<Long, List<Integer>>();
        List<Long> productStates = new ArrayList<Long>(
				productSnapshot.getStates());
        Collections.sort(productStates);
        for (Long productState : productStates) {
			if (productState.longValue() == -1L) {
				// LTSA's shared ERROR state intentionally has no unique component
				// tuple.  It remains in the transition snapshot as an unsafe sink.
				continue;
			}
			if (productState.longValue() < 0L
                    || productState.longValue() > Integer.MAX_VALUE) {
                throw new IllegalArgumentException(
                        "Product state identifier is outside the retained tuple domain.");
            }
            int[] tuple = tuples.get(Integer.valueOf(productState.intValue()));
            if (tuple == null || tuple.length != components.length) {
                throw new IllegalArgumentException(
                        "Product state has no exact component tuple: " + productState);
            }
            int firstIndex = tuple[0];
            if (firstIndex < 0 || firstIndex >= compactIndexToSource.size()) {
                throw new IllegalArgumentException(
                        "First component index is outside the source state domain.");
            }
            result.put(productState, compactIndexToSource.get(firstIndex));
			fullTuples.put(productState, immutableCheckedTuple(
					tuple, componentSnapshots,
					"product state " + productState, false));
        }
		int expected = productSnapshot.getStates().size()
				- (productSnapshot.getStates().contains(Long.valueOf(-1L)) ? 1 : 0);
        if (result.size() != expected) {
            throw new IllegalArgumentException(
                    "Component provenance does not cover every product state.");
        }
		if (new LinkedHashSet<List<Integer>>(fullTuples.values()).size()
				!= fullTuples.size()) {
			throw new IllegalArgumentException(
					"Product component tuples are not injective over product states.");
		}
		Set<Integer> expectedTupleKeys = new LinkedHashSet<Integer>();
		for (Long state : productStates) {
			if (state.longValue() != -1L) {
				expectedTupleKeys.add(Integer.valueOf(state.intValue()));
			}
		}
		if (!tuples.keySet().equals(expectedTupleKeys)) {
			throw new IllegalArgumentException(
					"Component tuple table has extra or missing product states.");
		}

		Map<String, List<Integer>> transitionTuples =
				new LinkedHashMap<String, List<Integer>>();
		Map<AbstractMap.SimpleEntry<Integer, String>, int[]> rawTransitionTuples =
				copyTransitionTupleMetadata(
						implementation.getStatePlusActionToComponentStates(),
						productSnapshot.getBucketCount(), components.length,
						tuples.size());
		if (rawTransitionTuples != null) {
			List<String> keys = new ArrayList<String>();
			Map<String, int[]> keyed = new LinkedHashMap<String, int[]>();
			for (Map.Entry<AbstractMap.SimpleEntry<Integer, String>, int[]> entry
					: rawTransitionTuples.entrySet()) {
				AbstractMap.SimpleEntry<Integer, String> key = entry.getKey();
				if (key == null || key.getKey() == null || key.getValue() == null
						|| !expectedTupleKeys.contains(key.getKey())
						|| key.getValue().isEmpty()) {
					throw new IllegalArgumentException(
							"Transition component provenance key is invalid.");
				}
				String canonicalKey = key.getKey() + "\u0000" + key.getValue();
				if (keyed.put(canonicalKey, entry.getValue()) != null) {
					throw new IllegalArgumentException(
							"Transition component provenance key is duplicated.");
				}
				keys.add(canonicalKey);
			}
			Collections.sort(keys);
			for (String key : keys) {
				int separator = key.indexOf('\u0000');
				Long from = Long.valueOf(key.substring(0, separator));
				String action = key.substring(separator + 1);
				Set<Long> productTargets = productSnapshot.getPost().get(from).get(action);
				boolean hasGlobalErrorOutcome = productTargets != null
						&& productTargets.contains(Long.valueOf(-1L));
				transitionTuples.put(key, immutableCheckedTuple(
						keyed.get(key), componentSnapshots,
						"transition component provenance " + key,
						hasGlobalErrorOutcome));
			}
		}
		Set<String> expectedDiagnosticKeys = new LinkedHashSet<String>();
		for (Long state : productStates) {
			if (state.longValue() == -1L) continue;
			for (String action : productSnapshot.getPost().get(state).keySet()) {
				expectedDiagnosticKeys.add(state + "\u0000" + action);
			}
		}
		if (!transitionTuples.keySet().equals(expectedDiagnosticKeys)) {
			throw new IllegalArgumentException(
					"Native first-outcome diagnostic census differs from product buckets.");
		}
		for (Map.Entry<String, List<Integer>> diagnostic
				: transitionTuples.entrySet()) {
			String key = diagnostic.getKey();
			int separator = key.indexOf('\u0000');
			Long from = Long.valueOf(key.substring(0, separator));
			String action = key.substring(separator + 1);
			Set<Long> targets = productSnapshot.getPost().get(from).get(action);
			if (targets == null) {
				throw new IllegalArgumentException(
						"Native diagnostic names no product bucket.");
			}
			boolean hasError = targets.contains(Long.valueOf(-1L));
			if (hasError && targets.size() != 1) {
				throw new IllegalArgumentException(
						"Mixed ERROR/non-ERROR product bucket lacks per-outcome diagnostics.");
			}
			if (hasError) {
				if (!diagnostic.getValue().contains(Integer.valueOf(-1))) {
					throw new IllegalArgumentException(
							"ERROR product diagnostic has no component ERROR coordinate.");
				}
			} else {
				boolean matches = false;
				for (Long target : targets) {
					if (diagnostic.getValue().equals(fullTuples.get(target))) {
						matches = true;
						break;
					}
				}
				if (!matches) {
					throw new IllegalArgumentException(
							"Native first-outcome diagnostic matches no product target tuple.");
				}
			}
		}
		Map<String, Set<List<Integer>>> derivedComponentPost =
				validateProductSemantics(
						productSnapshot, componentSnapshots, fullTuples);
		for (Map.Entry<String, List<Integer>> diagnostic
				: transitionTuples.entrySet()) {
			Set<List<Integer>> rawOutcomes = derivedComponentPost.get(
					diagnostic.getKey());
			if (rawOutcomes == null
					|| !rawOutcomes.contains(diagnostic.getValue())) {
				throw new IllegalArgumentException(
						"Native first-outcome diagnostic matches no exact raw "
						+ "component outcome.");
			}
		}
		M9MtsSnapshot.requireStableSourceEquals(product, productSnapshot);
		M9MtsSnapshot.requireStableSourceEquals(
				firstComponentSource, firstComponentSourceSnapshot);
		if (!sameComponentReferences(
						components, implementation.getComponents())
				|| !sameTupleMetadata(
						tuples, copyStateTupleMetadata(
								implementation.getStateToComponentStates(),
								productSnapshot.getStates().size(),
								components.length))
				|| !sameTransitionTupleMetadata(
						rawTransitionTuples,
							copyTransitionTupleMetadata(
									implementation.getStatePlusActionToComponentStates(),
									productSnapshot.getBucketCount(),
									components.length, tuples.size()))
				|| !sameComponentTrees(
						componentTrees,
						CompactStateCanonicalTree.captureForest(
								implementation.getComponents()))) {
			throw new IllegalArgumentException(
					"Product, component, or provenance bytes changed during capture.");
		}
		// A second bounded recopy closes the permanent one-shot mutation window
		// behind each first verification cursor without retaining another full
		// provenance graph.
		if (!sameComponentReferences(components, implementation.getComponents())
				|| !sameTupleMetadata(
						tuples, copyStateTupleMetadata(
								implementation.getStateToComponentStates(),
								productSnapshot.getStates().size(), components.length))
				|| !sameTransitionTupleMetadata(
						rawTransitionTuples,
							copyTransitionTupleMetadata(
									implementation.getStatePlusActionToComponentStates(),
									productSnapshot.getBucketCount(), components.length,
									tuples.size()))
				|| !sameComponentTrees(
						componentTrees,
						CompactStateCanonicalTree.captureForest(
								implementation.getComponents()))) {
			throw new IllegalArgumentException(
					"Product provenance changed during final canonical verification.");
		}

		return new Projection(
				productSnapshot,
				firstComponentSourceSnapshot,
				componentNames,
				componentSnapshots,
				componentTrees,
				productSnapshot.getInitialState(),
				result,
				fullTuples,
				derivedComponentPost,
				transitionTuples);
    }

	/**
	 * Projects every retained state of a flat native product onto the state of
	 * a separately materialized prefix product with the same ordered leading
	 * components.  This preserves the legacy solver product order while giving
	 * the endpoint materializer an exact solver-environment-to-Enew binding.
	 * The result is total over {@code product}; it is intentionally not required
	 * to be onto {@code prefixProduct} because later monitor components may
	 * restrict the reachable prefix tuples.
	 */
	public static OrderedPrefixProjection projectOrderedPrefix(
			Projection product,
			Projection prefixProduct) {
		if (product == null || prefixProduct == null) {
			throw new IllegalArgumentException(
					"Both product projections are required for prefix binding.");
		}
		int prefixArity = prefixProduct.componentTrees.size();
		if (prefixArity == 0 || product.componentTrees.size() < prefixArity) {
			throw new IllegalArgumentException(
					"Product has no complete ordered component prefix.");
		}
		for (int index = 0; index < prefixArity; index++) {
			if (!CompactStateCanonicalTree.canonicalEquals(
					product.componentTrees.get(index),
					prefixProduct.componentTrees.get(index))) {
				throw new IllegalArgumentException(
						"Product component prefix differs from the endpoint authority.");
			}
		}
		requireProjectionBound(
				product.componentStateTuples.size(), product.componentTrees.size());
		requireProjectionBound(
				prefixProduct.componentStateTuples.size(), prefixArity);

		Map<List<Integer>, Long> prefixTupleToState =
				new LinkedHashMap<List<Integer>, Long>();
		for (Map.Entry<Long, List<Integer>> entry
				: prefixProduct.componentStateTuples.entrySet()) {
			if (entry.getValue().size() != prefixArity
					|| prefixTupleToState.put(entry.getValue(), entry.getKey()) != null) {
				throw new IllegalArgumentException(
						"Endpoint prefix tuples are incomplete or noninjective.");
			}
		}

		Map<Long, Long> result = new LinkedHashMap<Long, Long>();
		for (Map.Entry<Long, List<Integer>> entry
				: product.componentStateTuples.entrySet()) {
			List<Integer> tuple = entry.getValue();
			if (tuple.size() != product.componentTrees.size()) {
				throw new IllegalArgumentException(
						"Product state tuple arity differs from its component census.");
			}
			List<Integer> prefix = new ArrayList<Integer>(
					tuple.subList(0, prefixArity));
			Long endpointState = prefixTupleToState.get(prefix);
			if (endpointState == null) {
				throw new IllegalArgumentException(
						"Product state has no state in the materialized prefix product.");
			}
			result.put(entry.getKey(), endpointState);
		}
		if (result.size() != product.componentStateTuples.size()
				|| !Long.valueOf(prefixProduct.productInitialState).equals(
						result.get(Long.valueOf(product.productInitialState)))) {
			throw new IllegalArgumentException(
					"Prefix projection is not total or does not preserve the initial state.");
		}
		Set<Long> unsafe = provenanceFreeUnsafeStates(product);
		return new OrderedPrefixProjection(
				product, prefixProduct, prefixArity, result, unsafe);
	}

	/** Exact value comparison for two already-validated immutable projections. */
	public static boolean canonicalEquals(
			Projection left, Projection right) {
		if (left == right) return true;
		if (left == null || right == null
				|| !M9MtsSnapshot.canonicalEquals(
						left.productSnapshot, right.productSnapshot)
				|| !M9MtsSnapshot.canonicalEquals(
						left.firstComponentSourceSnapshot,
						right.firstComponentSourceSnapshot)
				|| !left.componentNames.equals(right.componentNames)
				|| left.componentTrees.size() != right.componentTrees.size()
				|| left.productInitialState != right.productInitialState
				|| !left.firstComponentSourceStates.equals(
						right.firstComponentSourceStates)
				|| !left.componentStateTuples.equals(right.componentStateTuples)
				|| !left.derivedComponentPost.equals(right.derivedComponentPost)
				|| !left.nativeFirstOutcomeDiagnostics.equals(
						right.nativeFirstOutcomeDiagnostics)) {
			return false;
		}
		for (int index = 0; index < left.componentTrees.size(); index++) {
			if (!CompactStateCanonicalTree.canonicalEquals(
					left.componentTrees.get(index),
					right.componentTrees.get(index))) {
				return false;
			}
		}
		return true;
	}

	/**
	 * Binds a separately admitted two-component endpoint (for M9, CLnew) to
	 * the exact local state of each previously admitted child (Enew and Cnew).
	 * Only reachable product tuples are required to occur; source-indexed child
	 * states absent from the product are retained explicitly in the returned
	 * unrepresented-state censuses.
	 */
	public static TwoCoordinateProjection requireTwoCoordinateConsistency(
			Projection productAuthority,
			CompactStateEndpointAdmission.Admission productAdmission,
			CompactStateEndpointAdmission.Admission firstAdmission,
			CompactStateEndpointAdmission.Admission secondAdmission,
			M9MtsSnapshot secondComponentSource,
			Map<Long, Long> secondStateToFirstSourceState) {
		if (productAuthority == null || productAdmission == null
				|| firstAdmission == null || secondAdmission == null
				|| secondComponentSource == null
				|| secondStateToFirstSourceState == null) {
			throw new IllegalArgumentException(
					"Product, child admissions, source, and origin map are required.");
		}
		if (!productAdmission.isComposed()
				|| secondAdmission.isComposed()
				|| productAuthority.componentTrees.size() != 2
				|| productAdmission.getCanonicalTree().getChildren().size() != 2) {
			throw new IllegalArgumentException(
					"The admitted endpoint is not an exact two-component product.");
		}
		List<CompactStateCanonicalTree> admittedChildren =
				productAdmission.getCanonicalTree().getChildren();
		CompactStateCanonicalTree[] expectedChildren =
				new CompactStateCanonicalTree[]{
						firstAdmission.getCanonicalTree(),
						secondAdmission.getCanonicalTree()};
		for (int index = 0; index < 2; index++) {
			if (!CompactStateCanonicalTree.canonicalEquals(
					admittedChildren.get(index), expectedChildren[index])
					|| !CompactStateCanonicalTree.canonicalEquals(
					productAuthority.componentTrees.get(index),
					expectedChildren[index])) {
				throw new IllegalArgumentException(
						"Two-component endpoint child bytes differ from admission authority.");
			}
		}

		CompactStateCanonicalSnapshot productSnapshot =
				productAdmission.getSnapshot();
		if (productSnapshot.getStateCount()
				!= productAuthority.componentStateTuples.size()
				|| productSnapshot.getInitialState()
				!= productAuthority.productInitialState) {
			throw new IllegalArgumentException(
					"Two-component endpoint state census differs from product authority.");
		}
		requireProjectionBound(productAuthority.componentStateTuples.size(), 2);
		if (!provenanceFreeUnsafeStates(productAuthority).isEmpty()) {
			throw new IllegalArgumentException(
					"Admitted two-component endpoint retains an unsafe untyped state.");
		}

		List<Long> secondCompactIndexToSource = compactIndexToSourceState(
				secondComponentSource.getStates(),
				Long.valueOf(secondComponentSource.getInitialState()));
		verifyComponentSnapshotSemantics(
				secondAdmission.getSnapshot(), secondComponentSource,
				secondCompactIndexToSource, "Second component");
		Set<Long> expectedSecondSourceStates =
				new LinkedHashSet<Long>(secondComponentSource.getStates());
		expectedSecondSourceStates.remove(Long.valueOf(-1L));
		Set<Long> firstSourceStates = new LinkedHashSet<Long>(
				productAuthority.firstComponentSourceSnapshot.getStates());
		firstSourceStates.remove(Long.valueOf(-1L));
		Map<Long, Long> copiedOrigins = copyStableOriginMap(
				secondStateToFirstSourceState,
				expectedSecondSourceStates, firstSourceStates);

		Map<Long, SourceCoordinates> coordinates =
				new LinkedHashMap<Long, SourceCoordinates>();
		Set<Long> observedSecondStates = new LinkedHashSet<Long>();
		for (Map.Entry<Long, List<Integer>> entry
				: productAuthority.componentStateTuples.entrySet()) {
			List<Integer> tuple = entry.getValue();
			if (tuple.size() != 2
					|| tuple.get(1).intValue() < 0
					|| tuple.get(1).intValue()
							>= secondCompactIndexToSource.size()) {
				throw new IllegalArgumentException(
						"Two-component endpoint tuple leaves an admitted child domain.");
			}
			List<Integer> admittedTuple =
					productSnapshot.getComponentStateTuples().get(
							Integer.valueOf(entry.getKey().intValue()));
			if (!tuple.equals(admittedTuple)) {
				throw new IllegalArgumentException(
						"Two-component endpoint tuple differs from admitted bytes.");
			}
			Long firstSourceState =
					productAuthority.firstComponentSourceStates.get(entry.getKey());
			Long secondSourceState = secondCompactIndexToSource.get(
					tuple.get(1).intValue());
			if (firstSourceState == null
					|| !firstSourceState.equals(copiedOrigins.get(secondSourceState))) {
				throw new IllegalArgumentException(
						"Closed-loop child coordinates violate Cnew-origin-to-Enew consistency.");
			}
			coordinates.put(entry.getKey(),
					new SourceCoordinates(firstSourceState, secondSourceState));
			observedSecondStates.add(secondSourceState);
		}
		Long productInitial = Long.valueOf(productAuthority.productInitialState);
		SourceCoordinates initial = coordinates.get(productInitial);
		if (initial == null
				|| initial.getFirstSourceState()
						!= productAuthority.firstComponentSourceSnapshot.getInitialState()
				|| initial.getSecondSourceState()
						!= secondComponentSource.getInitialState()
				|| !Long.valueOf(initial.getFirstSourceState()).equals(
						copiedOrigins.get(Long.valueOf(
								initial.getSecondSourceState())))) {
			throw new IllegalArgumentException(
					"Two-component endpoint does not preserve both child initial states.");
		}
		Set<Long> unobservedSecond =
				new LinkedHashSet<Long>(expectedSecondSourceStates);
		unobservedSecond.removeAll(observedSecondStates);
		if (!copiedOrigins.equals(copyStableOriginMap(
				secondStateToFirstSourceState,
				expectedSecondSourceStates, firstSourceStates))) {
			throw new IllegalArgumentException(
					"Second-component origin map changed during coordinate capture.");
		}
		if (!copiedOrigins.equals(copyStableOriginMap(
				secondStateToFirstSourceState,
				expectedSecondSourceStates, firstSourceStates))) {
			throw new IllegalArgumentException(
					"Second-component origin changed during final coordinate verification.");
		}
		return new TwoCoordinateProjection(
				coordinates, copiedOrigins, unobservedSecond);
	}

	private static Map<Long, Long> copyStableOriginMap(
			Map<Long, Long> source,
			Set<Long> expectedDomain,
			Set<Long> allowedRange) {
		if (source.size() != expectedDomain.size()
				|| !source.keySet().equals(expectedDomain)) {
			throw new IllegalArgumentException(
					"Second-component origin map domain differs from its source states.");
		}
		Map<Long, Long> result = new LinkedHashMap<Long, Long>();
		for (Long secondState : new TreeSet<Long>(expectedDomain)) {
			Long firstState = source.get(secondState);
			if (firstState == null || !allowedRange.contains(firstState)) {
				throw new IllegalArgumentException(
						"Second-component origin leaves the admitted first source domain.");
			}
			result.put(secondState, firstState);
		}
		if (source.size() != result.size()
				|| !source.keySet().equals(expectedDomain)) {
			throw new IllegalArgumentException(
					"Second-component origin map changed during capture.");
		}
		return Collections.unmodifiableMap(result);
	}

	private static Set<Long> provenanceFreeUnsafeStates(Projection projection) {
		Set<Long> result = new LinkedHashSet<Long>(
				projection.productSnapshot.getStates());
		result.removeAll(projection.componentStateTuples.keySet());
		if (!result.isEmpty()
				&& !result.equals(Collections.singleton(Long.valueOf(-1L)))) {
			throw new IllegalArgumentException(
					"Product contains a provenance-free state other than LTSA ERROR.");
		}
		return Collections.unmodifiableSet(result);
	}

	private static CompactState[] copyComponentReferences(
			CompactState[] source) {
		if (source == null || source.length == 0
				|| source.length > MAX_PROJECTION_COMPONENTS) {
			throw new IllegalArgumentException(
					"Product has no bounded component-state provenance.");
		}
		CompactState[] result = source.clone();
		for (CompactState component : result) {
			if (component == null) {
				throw new IllegalArgumentException(
						"Product component descriptor is null.");
			}
		}
		return result;
	}

	private static Map<Integer, int[]> copyStateTupleMetadata(
			Map<Integer, int[]> source,
			int stateBound,
			int componentCount) {
		if (source == null || source.size() > stateBound) {
			throw new IllegalArgumentException(
					"Product component tuple census exceeds its state domain.");
		}
		requireProjectionBound(source.size(), componentCount);
		List<Map.Entry<Integer, int[]>> copied =
				new ArrayList<Map.Entry<Integer, int[]>>(source.size());
		for (Map.Entry<Integer, int[]> entry : source.entrySet()) {
			Integer key = entry.getKey();
			int[] tuple = entry.getValue();
			if (key == null || tuple == null || tuple.length != componentCount) {
				throw new IllegalArgumentException(
						"Product component tuple metadata is malformed.");
			}
			if (copied.size() >= stateBound) {
				throw new IllegalArgumentException(
						"Product component tuple census exceeds its state domain.");
			}
			copied.add(new AbstractMap.SimpleImmutableEntry<Integer, int[]>(
					key, tuple.clone()));
		}
		if (copied.size() != source.size()) {
			throw new IllegalArgumentException(
					"Product component tuple metadata changed during capture.");
		}
		Collections.sort(copied,
				new java.util.Comparator<Map.Entry<Integer, int[]>>() {
					@Override
					public int compare(
							Map.Entry<Integer, int[]> left,
							Map.Entry<Integer, int[]> right) {
						return left.getKey().compareTo(right.getKey());
					}
				});
		Map<Integer, int[]> result = new LinkedHashMap<Integer, int[]>();
		for (Map.Entry<Integer, int[]> entry : copied) {
			if (result.put(entry.getKey(), entry.getValue()) != null) {
				throw new IllegalArgumentException(
						"Product component tuple key is duplicated.");
			}
		}
		return Collections.unmodifiableMap(result);
	}

	private static Map<AbstractMap.SimpleEntry<Integer, String>, int[]>
				copyTransitionTupleMetadata(
						Map<AbstractMap.SimpleEntry<Integer, String>, int[]> source,
						long bucketBound,
						int componentCount,
						long retainedStateTupleRows) {
		if (source == null) {
			return Collections.emptyMap();
		}
		if (source.size() > bucketBound
				|| retainedStateTupleRows < 0L
				|| (long) source.size() + retainedStateTupleRows
						> MAX_PROJECTION_TUPLE_CELLS / componentCount) {
			throw new IllegalArgumentException(
					"Transition provenance exceeds the product bucket census.");
		}
		Map<String, Map.Entry<AbstractMap.SimpleEntry<Integer, String>, int[]>>
				canonical = new LinkedHashMap<String,
						Map.Entry<AbstractMap.SimpleEntry<Integer, String>, int[]>>();
		for (Map.Entry<AbstractMap.SimpleEntry<Integer, String>, int[]> entry
				: source.entrySet()) {
			AbstractMap.SimpleEntry<Integer, String> key = entry.getKey();
			int[] tuple = entry.getValue();
			if (key == null || key.getKey() == null || key.getValue() == null
					|| tuple == null || tuple.length != componentCount) {
				throw new IllegalArgumentException(
						"Transition component provenance metadata is malformed.");
			}
			String canonicalKey = key.getKey() + "\u0000" + key.getValue();
			if (canonical.size() >= bucketBound) {
				throw new IllegalArgumentException(
						"Transition provenance exceeds the product bucket census.");
			}
			if (canonical.put(canonicalKey, entry) != null) {
				throw new IllegalArgumentException(
						"Transition component provenance key is duplicated.");
			}
		}
		if (canonical.size() != source.size()) {
			throw new IllegalArgumentException(
					"Transition component provenance changed during capture.");
		}
		Map<AbstractMap.SimpleEntry<Integer, String>, int[]> result =
				new LinkedHashMap<AbstractMap.SimpleEntry<Integer, String>, int[]>();
		for (String canonicalKey : new TreeSet<String>(canonical.keySet())) {
			Map.Entry<AbstractMap.SimpleEntry<Integer, String>, int[]> entry =
					canonical.get(canonicalKey);
			result.put(new AbstractMap.SimpleEntry<Integer, String>(
					entry.getKey().getKey(), entry.getKey().getValue()),
					entry.getValue().clone());
		}
		return Collections.unmodifiableMap(result);
	}

	private static boolean sameComponentReferences(
			CompactState[] expected,
			CompactState[] actual) {
		if (actual == null || expected.length != actual.length) return false;
		for (int index = 0; index < expected.length; index++) {
			if (expected[index] != actual[index]) return false;
		}
		return true;
	}

	private static boolean sameTupleMetadata(
			Map<Integer, int[]> expected,
			Map<Integer, int[]> actual) {
		if (actual == null || expected.size() != actual.size()
				|| !expected.keySet().equals(actual.keySet())) return false;
		for (Map.Entry<Integer, int[]> entry : expected.entrySet()) {
			if (!sameIntArray(entry.getValue(), actual.get(entry.getKey()))) {
				return false;
			}
		}
		return true;
	}

	private static boolean sameTransitionTupleMetadata(
			Map<AbstractMap.SimpleEntry<Integer, String>, int[]> expected,
			Map<AbstractMap.SimpleEntry<Integer, String>, int[]> actual) {
		if (actual == null) return expected.isEmpty();
		if (expected.size() != actual.size()
				|| !expected.keySet().equals(actual.keySet())) return false;
		for (Map.Entry<AbstractMap.SimpleEntry<Integer, String>, int[]> entry
				: expected.entrySet()) {
			if (!sameIntArray(entry.getValue(), actual.get(entry.getKey()))) {
				return false;
			}
		}
		return true;
	}

	private static boolean sameIntArray(int[] expected, int[] actual) {
		if (expected == null || actual == null || expected.length != actual.length) {
			return false;
		}
		for (int index = 0; index < expected.length; index++) {
			if (expected[index] != actual[index]) return false;
		}
		return true;
	}

	private static boolean sameComponentTrees(
			List<CompactStateCanonicalTree> expected,
			List<CompactStateCanonicalTree> actual) {
		if (expected.size() != actual.size()) return false;
		for (int index = 0; index < expected.size(); index++) {
			if (!CompactStateCanonicalTree.canonicalEquals(
					expected.get(index), actual.get(index))) return false;
		}
		return true;
	}

	static void requireProjectionBound(int states, int components) {
		if (states < 0 || states > MAX_PROJECTION_STATES
				|| components <= 0 || components > MAX_PROJECTION_COMPONENTS
				|| states > MAX_PROJECTION_TUPLE_CELLS / components) {
			throw new IllegalArgumentException(
					"Projection tuple census exceeds the registered finite bound.");
		}
	}

	/**
	 * Binds an already admitted CompactState endpoint to the exact immutable
	 * source-MTS authority used by the materializer.  The native converter's
	 * initial-first, then sorted-state indexing is part of this profile.
	 */
	static void requireAdmissionMatchesSource(
			CompactStateEndpointAdmission.Admission admission,
			M9MtsSnapshot source,
			String role) {
		if (admission == null || source == null || role == null
				|| role.isEmpty()) {
			throw new IllegalArgumentException(
					"Endpoint admission, source authority, and role are required.");
		}
		List<Long> compactIndexToSource = compactIndexToSourceState(
				source.getStates(), Long.valueOf(source.getInitialState()));
		verifyComponentSnapshotSemantics(
				admission.getSnapshot(), source, compactIndexToSource, role);
	}

	private static void verifyComponentSnapshotSemantics(
			CompactStateCanonicalSnapshot snapshot,
			M9MtsSnapshot source,
			List<Long> compactIndexToSource,
			String role) {
		if (snapshot.getStateCount() != compactIndexToSource.size()
				|| snapshot.getInitialState() != 0) {
			throw new IllegalArgumentException(
					role + " state indexing differs from the source MTS.");
		}
		Set<String> actualVisibleAlphabet = new LinkedHashSet<String>();
		int actualTauCount = 0;
		for (CompactStateCanonicalSnapshot.Action action : snapshot.getActions()) {
			if ("tau".equals(action.getLabel())) actualTauCount++;
			else actualVisibleAlphabet.add(action.getLabel());
		}
		Set<String> expectedVisibleAlphabet =
				new LinkedHashSet<String>(source.getActions());
		expectedVisibleAlphabet.remove("tau");
		if (!actualVisibleAlphabet.equals(expectedVisibleAlphabet)
				|| actualTauCount < 1 || actualTauCount > 2
				|| snapshot.getActions().size()
						!= actualVisibleAlphabet.size() + actualTauCount) {
			throw new IllegalArgumentException(
					role + " alphabet differs from the source MTS.");
		}

		Map<Long, Integer> sourceToCompact = new LinkedHashMap<Long, Integer>();
		for (int index = 0; index < compactIndexToSource.size(); index++) {
			sourceToCompact.put(compactIndexToSource.get(index),
					Integer.valueOf(index));
		}
		Set<String> expectedTransitions = new LinkedHashSet<String>();
		for (Long state : source.getStates()) {
			if (state.longValue() == -1L) continue;
			Integer from = sourceToCompact.get(state);
			Map<String, Set<Long>> row = source.getPost().get(state);
			for (Map.Entry<String, Set<Long>> bucket : row.entrySet()) {
				for (Long sourceTarget : bucket.getValue()) {
					int target = sourceTarget.longValue() == -1L
							? -1 : sourceToCompact.get(sourceTarget).intValue();
					expectedTransitions.add(from + "\u0000" + bucket.getKey()
							+ "\u0000" + target);
				}
			}
		}
		Set<String> actualTransitions = new LinkedHashSet<String>();
		for (CompactStateCanonicalSnapshot.Transition edge
				: snapshot.getTransitions()) {
			actualTransitions.add(edge.getFromState() + "\u0000"
					+ edge.getActionLabel() + "\u0000" + edge.getTargetState());
		}
		if (!actualTransitions.equals(expectedTransitions)) {
			Set<String> missing = new LinkedHashSet<String>(expectedTransitions);
			missing.removeAll(actualTransitions);
			Set<String> extra = new LinkedHashSet<String>(actualTransitions);
			extra.removeAll(expectedTransitions);
			throw new IllegalArgumentException(
					role + " transition relation differs from the source MTS; "
							+ "missing=" + missing + ", extra=" + extra + ".");
		}
	}

	private static Map<String, Set<List<Integer>>> validateProductSemantics(
			M9MtsSnapshot product,
			List<CompactStateCanonicalSnapshot> snapshots,
			Map<Long, List<Integer>> productTuples) {
		Set<String> expectedAlphabet = new LinkedHashSet<String>();
		for (CompactStateCanonicalSnapshot snapshot : snapshots) {
			for (CompactStateCanonicalSnapshot.Action action : snapshot.getActions()) {
				expectedAlphabet.add(action.getLabel());
			}
		}
		if (!new LinkedHashSet<String>(product.getActions()).equals(expectedAlphabet)) {
			throw new IllegalArgumentException(
					"Product alphabet differs from its native component union.");
		}
		requireBucketBound(product.getStates().size(), expectedAlphabet.size());
		requireMtsReachability(product);
		List<Integer> initialTuple = productTuples.get(
				Long.valueOf(product.getInitialState()));
		if (initialTuple == null) {
			throw new IllegalArgumentException("Product initial tuple is absent.");
		}
		for (Integer local : initialTuple) {
			if (local.intValue() != 0) {
				throw new IllegalArgumentException(
						"Product initial tuple is not the ordered native initial tuple.");
			}
		}

		List<Map<Integer, Map<String, Set<Integer>>>> localPost =
				new ArrayList<Map<Integer, Map<String, Set<Integer>>>>();
		List<Set<String>> localAlphabets = new ArrayList<Set<String>>();
		for (CompactStateCanonicalSnapshot snapshot : snapshots) {
			Map<Integer, Map<String, Set<Integer>>> byState =
					new LinkedHashMap<Integer, Map<String, Set<Integer>>>();
			for (int state = 0; state < snapshot.getStateCount(); state++) {
				byState.put(Integer.valueOf(state),
						new LinkedHashMap<String, Set<Integer>>());
			}
			for (CompactStateCanonicalSnapshot.Transition edge
					: snapshot.getTransitions()) {
				Map<String, Set<Integer>> row = byState.get(
						Integer.valueOf(edge.getFromState()));
				Set<Integer> targets = row.get(edge.getActionLabel());
				if (targets == null) {
					targets = new LinkedHashSet<Integer>();
					row.put(edge.getActionLabel(), targets);
				}
				targets.add(Integer.valueOf(edge.getTargetState()));
			}
			localPost.add(byState);
			Set<String> alphabet = new LinkedHashSet<String>();
			for (CompactStateCanonicalSnapshot.Action action : snapshot.getActions()) {
				alphabet.add(action.getLabel());
			}
			localAlphabets.add(alphabet);
		}

		Map<String, Set<List<Integer>>> derivedComponentPost =
				new LinkedHashMap<String, Set<List<Integer>>>();
		long[] aggregateOutcomeTuples = new long[]{0L};
		for (Map.Entry<Long, List<Integer>> sourceEntry : productTuples.entrySet()) {
			Long source = sourceEntry.getKey();
			List<Integer> sourceTuple = sourceEntry.getValue();
			for (String action : expectedAlphabet) {
				Set<List<Integer>> componentOutcomes = "tau".equals(action)
						? asynchronousTauOutcomeTuples(
								sourceTuple, action, localPost,
								aggregateOutcomeTuples)
						: synchronizedOutcomeTuples(
								sourceTuple, action, localPost, localAlphabets,
								aggregateOutcomeTuples);
				derivedComponentPost.put(source + "\u0000" + action,
						immutableSortedTuples(componentOutcomes));
				Set<String> expectedTargets = "tau".equals(action)
						? asynchronousTauTargets(
								sourceTuple, action, localPost)
						: synchronizedTargets(
								sourceTuple, action, localPost, localAlphabets);
				Set<String> actualTargets = new LinkedHashSet<String>();
				Set<Long> productTargets = product.getPost().get(source).get(action);
				if (productTargets == null) {
					productTargets = Collections.emptySet();
				}
				for (Long target : productTargets) {
					if (target.longValue() == -1L) {
						actualTargets.add("ERROR");
					} else {
						List<Integer> tuple = productTuples.get(target);
						if (tuple == null) {
							throw new IllegalArgumentException(
									"Product transition target has no component tuple.");
						}
						actualTargets.add(tupleKey(tuple));
					}
				}
				if (!actualTargets.equals(expectedTargets)) {
					throw new IllegalArgumentException(
							"Product Post differs from native component Post at state "
									+ source + " action " + action + ".");
				}
			}
		}
		return Collections.unmodifiableMap(derivedComponentPost);
	}

	/**
	 * Reconstructs every bucket of a retained native composition snapshot from
	 * its ordered child snapshots.  This is deliberately package-private so the
	 * recursive tree capture can apply the same fail-closed check at every
	 * nonleaf, rather than authenticating only the outer product.
	 */
	static void validateSnapshotComposition(
			CompactStateCanonicalSnapshot product,
			List<CompactStateCanonicalSnapshot> components) {
		if (components == null || components.isEmpty()
				|| product.getComponentNames().size() != components.size()) {
			throw new IllegalArgumentException(
					"Nested product child census is incomplete.");
		}
		Set<String> expectedAlphabet = new LinkedHashSet<String>();
		for (CompactStateCanonicalSnapshot component : components) {
			for (CompactStateCanonicalSnapshot.Action action : component.getActions()) {
				expectedAlphabet.add(action.getLabel());
			}
		}
		Set<String> actualAlphabet = new LinkedHashSet<String>();
		int tauCount = 0;
		for (CompactStateCanonicalSnapshot.Action action : product.getActions()) {
			actualAlphabet.add(action.getLabel());
			if ("tau".equals(action.getLabel())) tauCount++;
		}
		if (!actualAlphabet.equals(expectedAlphabet)
				|| tauCount < 1 || tauCount > 2
				|| product.getActions().size() != expectedAlphabet.size()
						+ (tauCount == 2 ? 1 : 0)) {
			throw new IllegalArgumentException(
					"Nested product alphabet differs from its ordered child union.");
		}
		requireBucketBound(product.getStateCount(), expectedAlphabet.size());
		requireSnapshotReachability(product);

		Map<Integer, List<Integer>> tuples = product.getComponentStateTuples();
		if (tuples.size() != product.getStateCount()
				|| new LinkedHashSet<List<Integer>>(tuples.values()).size()
				!= tuples.size()) {
			throw new IllegalArgumentException(
					"Nested product component tuples are incomplete or noninjective.");
		}
		List<Integer> initialTuple = tuples.get(
				Integer.valueOf(product.getInitialState()));
		if (initialTuple == null || initialTuple.size() != components.size()) {
			throw new IllegalArgumentException("Nested product initial tuple is absent.");
		}
		for (Integer local : initialTuple) {
			if (local.intValue() != 0) {
				throw new IllegalArgumentException(
						"Nested product initial tuple is not the ordered child initial tuple.");
			}
		}

		List<Map<Integer, Map<String, Set<Integer>>>> localPost =
				new ArrayList<Map<Integer, Map<String, Set<Integer>>>>();
		List<Set<String>> localAlphabets = new ArrayList<Set<String>>();
		for (CompactStateCanonicalSnapshot component : components) {
			Map<Integer, Map<String, Set<Integer>>> byState =
					new LinkedHashMap<Integer, Map<String, Set<Integer>>>();
			for (int state = 0; state < component.getStateCount(); state++) {
				byState.put(Integer.valueOf(state),
						new LinkedHashMap<String, Set<Integer>>());
			}
			for (CompactStateCanonicalSnapshot.Transition edge
					: component.getTransitions()) {
				Map<String, Set<Integer>> row = byState.get(
						Integer.valueOf(edge.getFromState()));
				Set<Integer> targets = row.get(edge.getActionLabel());
				if (targets == null) {
					targets = new LinkedHashSet<Integer>();
					row.put(edge.getActionLabel(), targets);
				}
				targets.add(Integer.valueOf(edge.getTargetState()));
			}
			localPost.add(byState);
			Set<String> alphabet = new LinkedHashSet<String>();
			for (CompactStateCanonicalSnapshot.Action action : component.getActions()) {
				alphabet.add(action.getLabel());
			}
			localAlphabets.add(alphabet);
		}

		Map<String, Set<String>> actualPost =
				new LinkedHashMap<String, Set<String>>();
		for (int state = 0; state < product.getStateCount(); state++) {
			for (String action : expectedAlphabet) {
				actualPost.put(state + "\u0000" + action,
						new LinkedHashSet<String>());
			}
		}
		for (CompactStateCanonicalSnapshot.Transition edge
				: product.getTransitions()) {
			Set<String> targets = actualPost.get(edge.getFromState() + "\u0000"
					+ edge.getActionLabel());
			if (targets == null) {
				throw new IllegalArgumentException(
						"Nested product transition uses an undeclared child action.");
			}
			if (edge.getTargetState() == -1) {
				targets.add("ERROR");
			} else {
				List<Integer> targetTuple = tuples.get(
						Integer.valueOf(edge.getTargetState()));
				if (targetTuple == null) {
					throw new IllegalArgumentException(
							"Nested product target has no component tuple.");
				}
				targets.add(tupleKey(targetTuple));
			}
		}

		for (int state = 0; state < product.getStateCount(); state++) {
			List<Integer> sourceTuple = tuples.get(Integer.valueOf(state));
			for (String action : expectedAlphabet) {
				Set<String> expectedTargets = "tau".equals(action)
						? asynchronousTauTargets(sourceTuple, action, localPost)
						: synchronizedTargets(
								sourceTuple, action, localPost, localAlphabets);
				if (!expectedTargets.equals(
						actualPost.get(state + "\u0000" + action))) {
					throw new IllegalArgumentException(
							"Nested product Post differs from ordered child Post at state "
									+ state + " action " + action + ".");
				}
			}
		}
	}

	static void requireSnapshotReachability(
			CompactStateCanonicalSnapshot snapshot) {
		List<List<Integer>> successors =
				new ArrayList<List<Integer>>(snapshot.getStateCount());
		for (int state = 0; state < snapshot.getStateCount(); state++) {
			successors.add(new ArrayList<Integer>());
		}
		for (CompactStateCanonicalSnapshot.Transition edge
				: snapshot.getTransitions()) {
			if (edge.getTargetState() >= 0) {
				successors.get(edge.getFromState()).add(
						Integer.valueOf(edge.getTargetState()));
			}
		}
		Set<Integer> reached = new LinkedHashSet<Integer>();
		ArrayDeque<Integer> pending = new ArrayDeque<Integer>();
		pending.add(Integer.valueOf(snapshot.getInitialState()));
		while (!pending.isEmpty()) {
			Integer state = pending.removeFirst();
			if (!reached.add(state)) continue;
			for (Integer target : successors.get(state.intValue())) {
				if (!reached.contains(target)) pending.addLast(target);
			}
		}
		if (reached.size() != snapshot.getStateCount()) {
			throw new IllegalArgumentException(
					"Native product contains an unreachable non-ERROR state.");
		}
	}

	private static void requireMtsReachability(M9MtsSnapshot product) {
		Set<Long> reached = new LinkedHashSet<Long>();
		ArrayDeque<Long> pending = new ArrayDeque<Long>();
		pending.add(Long.valueOf(product.getInitialState()));
		while (!pending.isEmpty()) {
			Long state = pending.removeFirst();
			if (state.longValue() == -1L || !reached.add(state)) continue;
			for (Set<Long> targets : product.getPost().get(state).values()) {
				for (Long target : targets) {
					if (target.longValue() != -1L && !reached.contains(target)) {
						pending.addLast(target);
					}
				}
		}
		}
		Set<Long> expected = new LinkedHashSet<Long>(product.getStates());
		expected.remove(Long.valueOf(-1L));
		if (!reached.equals(expected)) {
			throw new IllegalArgumentException(
					"Native product MTS contains an unreachable non-ERROR state.");
		}
	}

	static void requireBucketBound(int states, int actions) {
		if (states < 0 || actions < 0
				|| (actions != 0
				&& (long) states > MAX_COMPOSITION_BUCKETS / (long) actions)) {
			throw new IllegalArgumentException(
					"Native composition exceeds the registered state/action bucket cap.");
		}
	}

	private static List<CompactStateCanonicalSnapshot> rootSnapshots(
			List<CompactStateCanonicalTree> trees) {
		List<CompactStateCanonicalSnapshot> snapshots =
				new ArrayList<CompactStateCanonicalSnapshot>();
		for (CompactStateCanonicalTree tree : trees) {
			snapshots.add(tree.getSnapshot());
		}
		return Collections.unmodifiableList(snapshots);
	}

	private static Set<String> asynchronousTauTargets(
			List<Integer> sourceTuple,
			String action,
			List<Map<Integer, Map<String, Set<Integer>>>> localPost) {
		Set<String> result = new LinkedHashSet<String>();
		for (int component = 0; component < localPost.size(); component++) {
			Set<Integer> targets = localPost.get(component)
					.get(sourceTuple.get(component)).get(action);
			if (targets == null) continue;
			for (Integer target : targets) {
				if (target.intValue() == -1) {
					result.add("ERROR");
				} else {
					List<Integer> tuple = new ArrayList<Integer>(sourceTuple);
					tuple.set(component, target);
					result.add(tupleKey(tuple));
				}
			}
		}
		return result;
	}

	private static Set<List<Integer>> asynchronousTauOutcomeTuples(
			List<Integer> sourceTuple,
			String action,
			List<Map<Integer, Map<String, Set<Integer>>>> localPost,
			long[] aggregateOutcomeTuples) {
		long upperBound = 0L;
		for (int component = 0; component < localPost.size(); component++) {
			Set<Integer> targets = localPost.get(component)
					.get(sourceTuple.get(component)).get(action);
			if (targets != null) upperBound += targets.size();
		}
		reserveDerivedOutcomes(aggregateOutcomeTuples, upperBound);
		Set<List<Integer>> result = new LinkedHashSet<List<Integer>>();
		for (int component = 0; component < localPost.size(); component++) {
			Set<Integer> targets = localPost.get(component)
					.get(sourceTuple.get(component)).get(action);
			if (targets == null) continue;
			for (Integer target : targets) {
				List<Integer> tuple = new ArrayList<Integer>(sourceTuple);
				tuple.set(component, target);
				result.add(Collections.unmodifiableList(tuple));
			}
		}
		return result;
	}

	private static Set<String> synchronizedTargets(
			List<Integer> sourceTuple,
			String action,
			List<Map<Integer, Map<String, Set<Integer>>>> localPost,
			List<Set<String>> localAlphabets) {
		List<List<Integer>> choices = new ArrayList<List<Integer>>();
		for (int component = 0; component < localPost.size(); component++) {
			if (!localAlphabets.get(component).contains(action)) {
				choices.add(Collections.singletonList(sourceTuple.get(component)));
				continue;
			}
			Set<Integer> targets = localPost.get(component)
					.get(sourceTuple.get(component)).get(action);
			if (targets == null || targets.isEmpty()) {
				return Collections.emptySet();
			}
			choices.add(new ArrayList<Integer>(targets));
		}
		Set<String> result = new LinkedHashSet<String>();
		expandTargetProduct(
				choices, 0, new ArrayList<Integer>(), result, new long[]{0L});
		return result;
	}

	private static Set<List<Integer>> synchronizedOutcomeTuples(
			List<Integer> sourceTuple,
			String action,
			List<Map<Integer, Map<String, Set<Integer>>>> localPost,
			List<Set<String>> localAlphabets,
			long[] aggregateOutcomeTuples) {
		List<List<Integer>> choices = new ArrayList<List<Integer>>();
		for (int component = 0; component < localPost.size(); component++) {
			if (!localAlphabets.get(component).contains(action)) {
				choices.add(Collections.singletonList(sourceTuple.get(component)));
				continue;
			}
			Set<Integer> targets = localPost.get(component)
					.get(sourceTuple.get(component)).get(action);
			if (targets == null || targets.isEmpty()) {
				return Collections.emptySet();
			}
			choices.add(new ArrayList<Integer>(targets));
		}
		long upperBound = 1L;
		for (List<Integer> choice : choices) {
			if (choice.isEmpty()
					|| upperBound > 100000L / choice.size()) {
				throw new IllegalArgumentException(
						"Native composition bucket exceeds the registered outcome cap.");
			}
			upperBound *= choice.size();
		}
		reserveDerivedOutcomes(aggregateOutcomeTuples, upperBound);
		Set<List<Integer>> result = new LinkedHashSet<List<Integer>>();
		expandRawTargetProduct(
				choices, 0, new ArrayList<Integer>(), result, new long[]{0L});
		return result;
	}

	private static void reserveDerivedOutcomes(
			long[] aggregate,
			long additional) {
		if (aggregate == null || aggregate.length != 1 || additional < 0L
				|| additional > MAX_DERIVED_OUTCOME_TUPLES
				|| aggregate[0] > MAX_DERIVED_OUTCOME_TUPLES - additional) {
			throw new IllegalArgumentException(
					"Derived component outcomes exceed the aggregate resource cap.");
		}
		aggregate[0] += additional;
	}

	private static void expandRawTargetProduct(
			List<List<Integer>> choices,
			int index,
			List<Integer> prefix,
			Set<List<Integer>> result,
			long[] expansions) {
		if (++expansions[0] > 100000L) {
			throw new IllegalArgumentException(
					"Native composition bucket exceeds the registered outcome cap.");
		}
		if (index == choices.size()) {
			result.add(Collections.unmodifiableList(
					new ArrayList<Integer>(prefix)));
			return;
		}
		for (Integer value : choices.get(index)) {
			prefix.add(value);
			expandRawTargetProduct(choices, index + 1, prefix, result, expansions);
			prefix.remove(prefix.size() - 1);
		}
	}

	private static Set<List<Integer>> immutableSortedTuples(
			Collection<List<Integer>> tuples) {
		List<List<Integer>> sorted = new ArrayList<List<Integer>>(tuples);
		Collections.sort(sorted, new java.util.Comparator<List<Integer>>() {
			@Override
			public int compare(List<Integer> left, List<Integer> right) {
				int length = Math.min(left.size(), right.size());
				for (int index = 0; index < length; index++) {
					int value = left.get(index).compareTo(right.get(index));
					if (value != 0) return value;
				}
				return Integer.compare(left.size(), right.size());
			}
		});
		return Collections.unmodifiableSet(
				new LinkedHashSet<List<Integer>>(sorted));
	}

	private static void expandTargetProduct(
			List<List<Integer>> choices,
			int index,
			List<Integer> prefix,
			Set<String> result,
			long[] expansions) {
		if (++expansions[0] > 100000L) {
			throw new IllegalArgumentException(
					"Native composition bucket exceeds the registered outcome cap.");
		}
		if (index == choices.size()) {
			for (Integer value : prefix) {
				if (value.intValue() == -1) {
					result.add("ERROR");
					return;
				}
			}
			result.add(tupleKey(prefix));
			return;
		}
		for (Integer value : choices.get(index)) {
			prefix.add(value);
			expandTargetProduct(
					choices, index + 1, prefix, result, expansions);
			prefix.remove(prefix.size() - 1);
		}
	}

	private static String tupleKey(Collection<Integer> tuple) {
		StringBuilder result = new StringBuilder();
		for (Integer value : tuple) {
			if (result.length() != 0) result.append(',');
			result.append(value.intValue());
		}
		return result.toString();
	}

	private static List<Integer> immutableCheckedTuple(
			int[] tuple,
			List<CompactStateCanonicalSnapshot> components,
			String role,
			boolean allowComponentError) {
		if (tuple == null || tuple.length != components.size()) {
			throw new IllegalArgumentException(role + " has the wrong tuple arity.");
		}
		List<Integer> result = new ArrayList<Integer>(tuple.length);
		for (int index = 0; index < tuple.length; index++) {
			if (tuple[index] == -1 && allowComponentError) {
				result.add(Integer.valueOf(-1));
				continue;
			}
			if (tuple[index] < 0
					|| tuple[index] >= components.get(index).getStateCount()) {
				throw new IllegalArgumentException(
						role + " leaves component " + index + " state domain.");
			}
			result.add(Integer.valueOf(tuple[index]));
		}
		return Collections.unmodifiableList(result);
	}

	public static final class OrderedPrefixProjection {
		private final Projection extendedProductAuthority;
		private final Projection prefixProductAuthority;
		private final int prefixArity;
		private final Map<Long, Long> extendedStateToPrefixState;
		private final Set<Long> provenanceFreeUnsafeStates;

		private OrderedPrefixProjection(
				Projection extendedProductAuthority,
				Projection prefixProductAuthority,
				int prefixArity,
				Map<Long, Long> extendedStateToPrefixState,
				Set<Long> provenanceFreeUnsafeStates) {
			this.extendedProductAuthority = extendedProductAuthority;
			this.prefixProductAuthority = prefixProductAuthority;
			this.prefixArity = prefixArity;
			this.extendedStateToPrefixState = Collections.unmodifiableMap(
					new LinkedHashMap<Long, Long>(extendedStateToPrefixState));
			this.provenanceFreeUnsafeStates = Collections.unmodifiableSet(
					new LinkedHashSet<Long>(provenanceFreeUnsafeStates));
		}

		public int getPrefixArity() { return prefixArity; }
		public Projection getExtendedProductAuthority() {
			return extendedProductAuthority;
		}
		public Projection getPrefixProductAuthority() {
			return prefixProductAuthority;
		}
		public Map<Long, Long> getExtendedStateToPrefixState() {
			return extendedStateToPrefixState;
		}
		public Set<Long> getProvenanceFreeUnsafeStates() {
			return provenanceFreeUnsafeStates;
		}
	}

	public static final class SourceCoordinates {
		private final long firstSourceState;
		private final long secondSourceState;

		private SourceCoordinates(long firstSourceState, long secondSourceState) {
			this.firstSourceState = firstSourceState;
			this.secondSourceState = secondSourceState;
		}

		public long getFirstSourceState() { return firstSourceState; }
		public long getSecondSourceState() { return secondSourceState; }

		@Override
		public boolean equals(Object other) {
			if (this == other) return true;
			if (!(other instanceof SourceCoordinates)) return false;
			SourceCoordinates coordinates = (SourceCoordinates) other;
			return firstSourceState == coordinates.firstSourceState
					&& secondSourceState == coordinates.secondSourceState;
		}

		@Override
		public int hashCode() {
			int result = Long.valueOf(firstSourceState).hashCode();
			return 31 * result + Long.valueOf(secondSourceState).hashCode();
		}
	}

	public static final class TwoCoordinateProjection {
		private final Map<Long, SourceCoordinates> productStateCoordinates;
		private final Map<Long, Long> secondStateToFirstState;
		private final Set<Long> unobservedSecondComponentStates;

		private TwoCoordinateProjection(
				Map<Long, SourceCoordinates> productStateCoordinates,
				Map<Long, Long> secondStateToFirstState,
				Set<Long> unobservedSecondComponentStates) {
			this.productStateCoordinates = Collections.unmodifiableMap(
					new LinkedHashMap<Long, SourceCoordinates>(
							productStateCoordinates));
			this.secondStateToFirstState = Collections.unmodifiableMap(
					new LinkedHashMap<Long, Long>(secondStateToFirstState));
			this.unobservedSecondComponentStates = Collections.unmodifiableSet(
					new LinkedHashSet<Long>(unobservedSecondComponentStates));
		}

		public Map<Long, SourceCoordinates> getProductStateCoordinates() {
			return productStateCoordinates;
		}
		public Map<Long, Long> getSecondStateToFirstState() {
			return secondStateToFirstState;
		}
		public Set<Long> getUnobservedSecondComponentStates() {
			return unobservedSecondComponentStates;
		}
	}

	public static final class Projection {
		private final M9MtsSnapshot productSnapshot;
		private final M9MtsSnapshot firstComponentSourceSnapshot;
		private final List<String> componentNames;
		private final List<CompactStateCanonicalSnapshot> componentSnapshots;
		private final List<CompactStateCanonicalTree> componentTrees;
		private final long productInitialState;
		private final Map<Long, Long> firstComponentSourceStates;
		private final Map<Long, List<Integer>> componentStateTuples;
		private final Map<String, Set<List<Integer>>> derivedComponentPost;
		private final Map<String, List<Integer>> nativeFirstOutcomeDiagnostics;

		private Projection(
				M9MtsSnapshot productSnapshot,
				M9MtsSnapshot firstComponentSourceSnapshot,
				Collection<String> componentNames,
				Collection<CompactStateCanonicalSnapshot> componentSnapshots,
				Collection<CompactStateCanonicalTree> componentTrees,
				long productInitialState,
				Map<Long, Long> firstComponentSourceStates,
				Map<Long, List<Integer>> componentStateTuples,
				Map<String, Set<List<Integer>>> derivedComponentPost,
				Map<String, List<Integer>> transitionComponentTuples) {
			this.productSnapshot = productSnapshot;
			this.firstComponentSourceSnapshot = firstComponentSourceSnapshot;
			this.componentNames = Collections.unmodifiableList(
					new ArrayList<String>(componentNames));
			this.componentSnapshots = Collections.unmodifiableList(
					new ArrayList<CompactStateCanonicalSnapshot>(componentSnapshots));
			this.componentTrees = Collections.unmodifiableList(
					new ArrayList<CompactStateCanonicalTree>(componentTrees));
			this.productInitialState = productInitialState;
			this.firstComponentSourceStates = Collections.unmodifiableMap(
					new LinkedHashMap<Long, Long>(firstComponentSourceStates));
			this.componentStateTuples = Collections.unmodifiableMap(
					new LinkedHashMap<Long, List<Integer>>(componentStateTuples));
			this.derivedComponentPost = Collections.unmodifiableMap(
					new LinkedHashMap<String, Set<List<Integer>>>(derivedComponentPost));
			this.nativeFirstOutcomeDiagnostics = Collections.unmodifiableMap(
					new LinkedHashMap<String, List<Integer>>(transitionComponentTuples));
		}

		public M9MtsSnapshot getProductSnapshot() { return productSnapshot; }
		public M9MtsSnapshot getFirstComponentSourceSnapshot() {
			return firstComponentSourceSnapshot;
		}
		public List<String> getComponentNames() { return componentNames; }
		public List<CompactStateCanonicalSnapshot> getComponentSnapshots() {
			return componentSnapshots;
		}
		public List<CompactStateCanonicalTree> getComponentTrees() {
			return componentTrees;
		}
		public long getProductInitialState() { return productInitialState; }
		public Map<Long, Long> getFirstComponentSourceStates() {
			return firstComponentSourceStates;
		}
		public Map<Long, List<Integer>> getComponentStateTuples() {
			return componentStateTuples;
		}
		public Map<String, Set<List<Integer>>> getDerivedComponentPost() {
			return derivedComponentPost;
		}
		public Map<String, List<Integer>> getNativeFirstOutcomeDiagnostics() {
			return nativeFirstOutcomeDiagnostics;
		}
	}

    static List<Long> compactIndexToSourceState(
            Set<Long> states,
            Long initialState) {
		if (states == null || states.isEmpty() || initialState == null
				|| !states.contains(initialState) || initialState.longValue() == -1L) {
            throw new IllegalArgumentException(
                    "Finite source state domain must contain its initial state and no ERROR id.");
        }
        List<Long> result = new ArrayList<Long>(states.size());
        result.add(initialState);
        for (Long state : new TreeSet<Long>(states)) {
			if (state.longValue() != -1L && !state.equals(initialState)) {
                result.add(state);
            }
        }
        return Collections.unmodifiableList(result);
    }
}
