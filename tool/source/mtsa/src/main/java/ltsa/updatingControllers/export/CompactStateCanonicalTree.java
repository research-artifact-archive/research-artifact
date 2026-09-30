package ltsa.updatingControllers.export;

import ltsa.lts.CompactState;

import java.util.ArrayList;
import java.util.Collections;
import java.util.IdentityHashMap;
import java.util.List;

/**
 * Immutable, recursively complete snapshot of an ordered CompactState
 * composition tree.  A flat CompactState snapshot intentionally retains only
 * child names and tuple tables; this type additionally binds every child graph
 * and rejects aliases/cycles that would make the native provenance ambiguous.
 */
public final class CompactStateCanonicalTree {
	private static final int MAX_DEPTH = 32;
	private static final int MAX_NODES = 512;
	private static final long MAX_AGGREGATE_STATES = 1_000_000L;
	private static final long MAX_AGGREGATE_ACTIONS = 32_768L;
	private static final long MAX_AGGREGATE_TRANSITIONS = 8_000_000L;
	private static final long MAX_AGGREGATE_TUPLE_CELLS = 32_000_000L;

	private final CompactStateCanonicalSnapshot snapshot;
	private final List<CompactStateCanonicalTree> children;

	private CompactStateCanonicalTree(
			CompactStateCanonicalSnapshot snapshot,
			List<CompactStateCanonicalTree> children) {
		this.snapshot = snapshot;
		this.children = Collections.unmodifiableList(
				new ArrayList<CompactStateCanonicalTree>(children));
	}

	public static List<CompactStateCanonicalTree> captureForest(
			CompactState[] roots) {
		if (roots == null || roots.length == 0) {
			throw new IllegalArgumentException(
					"CompactState component forest is empty.");
		}
		if (roots.length > MAX_NODES) {
			throw new IllegalArgumentException(
					"CompactState component forest exceeds the node cap.");
		}
		CaptureContext context = new CaptureContext();
		List<CompactStateCanonicalTree> result =
				new ArrayList<CompactStateCanonicalTree>(roots.length);
		for (CompactState root : roots) {
			result.add(capture(root, context, 0));
		}
		return Collections.unmodifiableList(result);
	}

	/** Verifies aggregate limits over already-immutable trees without recapture. */
	static void requireCombinedCensus(CompactStateCanonicalTree... roots) {
		if (roots == null || roots.length == 0 || roots.length > MAX_NODES) {
			throw new IllegalArgumentException(
					"CompactState canonical forest has no bounded root census.");
		}
		ImmutableCensus census = new ImmutableCensus();
		for (CompactStateCanonicalTree root : roots) {
			accumulateImmutable(root, census, 0);
		}
	}

	/**
	 * Verifies the immutable child forest together with a not-yet-created product
	 * root.  The materializer calls this before native composition so every tree
	 * aggregate allocation is known to fit the registered profile in advance.
	 */
	static void requireCombinedCensusWithProductRoot(
			long rootStates,
			long rootActions,
			long rootTransitions,
			long rootTupleCells,
			CompactStateCanonicalTree... children) {
		if (rootStates <= 0L || rootActions <= 0L
				|| rootTransitions < 0L || rootTupleCells < 0L
				|| children == null || children.length == 0
				|| children.length > MAX_NODES - 1) {
			throw new IllegalArgumentException(
					"CompactState product root has no bounded canonical census.");
		}
		ImmutableCensus census = new ImmutableCensus();
		census.nodes = 1L;
		census.states = rootStates;
		census.actions = rootActions;
		census.transitions = rootTransitions;
		census.tupleCells = rootTupleCells;
		if (census.states > MAX_AGGREGATE_STATES
				|| census.actions > MAX_AGGREGATE_ACTIONS
				|| census.transitions > MAX_AGGREGATE_TRANSITIONS
				|| census.tupleCells > MAX_AGGREGATE_TUPLE_CELLS) {
			throw new IllegalArgumentException(
					"CompactState product root exceeds the aggregate cap.");
		}
		for (CompactStateCanonicalTree child : children) {
			accumulateImmutable(child, census, 1);
		}
	}

	private static void accumulateImmutable(
			CompactStateCanonicalTree tree,
			ImmutableCensus census,
			int depth) {
		if (tree == null || depth > MAX_DEPTH) {
			throw new IllegalArgumentException(
					"CompactState canonical forest exceeds its depth profile.");
		}
		CompactStateCanonicalSnapshot value = tree.snapshot;
		census.nodes++;
		census.states += value.getStateCount();
		census.actions += value.getActions().size();
		census.transitions += value.getTransitions().size();
		census.tupleCells += ((long) value.getStateCount()
					+ (long) value.getNativeFirstOutcomeDiagnostics().size())
					* (long) value.getComponentNames().size();
		if (census.nodes > MAX_NODES
				|| census.states > MAX_AGGREGATE_STATES
				|| census.actions > MAX_AGGREGATE_ACTIONS
				|| census.transitions > MAX_AGGREGATE_TRANSITIONS
				|| census.tupleCells > MAX_AGGREGATE_TUPLE_CELLS) {
			throw new IllegalArgumentException(
					"CompactState canonical forest exceeds the aggregate cap.");
		}
		for (CompactStateCanonicalTree child : tree.children) {
			accumulateImmutable(child, census, depth + 1);
		}
	}

	private static CompactStateCanonicalTree capture(
			CompactState source,
			CaptureContext context,
			int depth) {
		if (source == null) {
			throw new IllegalArgumentException(
					"CompactState composition tree contains a null node.");
		}
		if (depth > MAX_DEPTH) {
			throw new IllegalArgumentException(
					"CompactState composition tree exceeds the depth cap.");
		}
		if (context.seen.put(source, Boolean.TRUE) != null) {
			throw new IllegalArgumentException(
					"CompactState composition tree contains an alias or cycle.");
		}

		context.preflight(source);
		CompactStateCanonicalSnapshot snapshot =
				CompactStateCanonicalSnapshot.fromRawBounded(
						source, false, context.remainingTransitions());
		requireNativeTauCensus(snapshot);
		context.add(snapshot);
		List<String> childNames = snapshot.getComponentNames();
		CompactState[] rawChildren = source.components;
		if (childNames.isEmpty()) {
			if (rawChildren != null && rawChildren.length != 0) {
				throw new IllegalArgumentException(
						"CompactState child graph census differs from its snapshot.");
			}
			return new CompactStateCanonicalTree(snapshot,
					Collections.<CompactStateCanonicalTree>emptyList());
		}
		if (rawChildren == null || rawChildren.length != childNames.size()) {
			throw new IllegalArgumentException(
					"CompactState child graph census differs from its snapshot.");
		}
		List<CompactStateCanonicalTree> children =
				new ArrayList<CompactStateCanonicalTree>(rawChildren.length);
		for (int index = 0; index < rawChildren.length; index++) {
			CompactStateCanonicalTree child =
					capture(rawChildren[index], context, depth + 1);
			if (!childNames.get(index).equals(child.snapshot.getName())) {
				throw new IllegalArgumentException(
						"CompactState child order differs from its snapshot.");
			}
			children.add(child);
		}
		List<CompactStateCanonicalSnapshot> childSnapshots =
				new ArrayList<CompactStateCanonicalSnapshot>(children.size());
		for (CompactStateCanonicalTree child : children) {
			childSnapshots.add(child.snapshot);
		}
		M9CompositionProvenance.validateSnapshotComposition(
				snapshot, childSnapshots);
		return new CompactStateCanonicalTree(snapshot, children);
	}

	private static void requireNativeTauCensus(
			CompactStateCanonicalSnapshot snapshot) {
		int tauCount = 0;
		for (CompactStateCanonicalSnapshot.Action action : snapshot.getActions()) {
			if ("tau".equals(action.getLabel())) tauCount++;
		}
		if (tauCount < 1 || tauCount > 2) {
			throw new IllegalArgumentException(
					"Every native CompactState tree node must retain one or two tau declarations.");
		}
	}

	public CompactStateCanonicalSnapshot getSnapshot() { return snapshot; }
	public List<CompactStateCanonicalTree> getChildren() { return children; }

	public static boolean canonicalEquals(
			CompactStateCanonicalTree left,
			CompactStateCanonicalTree right) {
		if (!sameSnapshot(left.snapshot, right.snapshot)
				|| left.children.size() != right.children.size()) return false;
		for (int index = 0; index < left.children.size(); index++) {
			if (!canonicalEquals(left.children.get(index), right.children.get(index))) {
				return false;
			}
		}
		return true;
	}

	private static boolean sameSnapshot(
			CompactStateCanonicalSnapshot left,
			CompactStateCanonicalSnapshot right) {
		if (!left.getName().equals(right.getName())
				|| left.getStateCount() != right.getStateCount()
				|| left.getInitialState() != right.getInitialState()
				|| left.getEndState() != right.getEndState()
				|| !left.getEmptyTransitionStates().equals(
					right.getEmptyTransitionStates())
				|| !left.getComponentNames().equals(right.getComponentNames())
				|| !left.getComponentStateTuples().equals(
					right.getComponentStateTuples())
				|| !left.getNativeFirstOutcomeDiagnostics().equals(
					right.getNativeFirstOutcomeDiagnostics())
				|| left.getActions().size() != right.getActions().size()
				|| left.getTransitions().size() != right.getTransitions().size()) {
			return false;
		}
		for (int index = 0; index < left.getActions().size(); index++) {
			CompactStateCanonicalSnapshot.Action a = left.getActions().get(index);
			CompactStateCanonicalSnapshot.Action b = right.getActions().get(index);
			if (a.getNativeIndex() != b.getNativeIndex()
					|| !a.getLabel().equals(b.getLabel())) return false;
		}
		for (int index = 0; index < left.getTransitions().size(); index++) {
			CompactStateCanonicalSnapshot.Transition a =
					left.getTransitions().get(index);
			CompactStateCanonicalSnapshot.Transition b =
					right.getTransitions().get(index);
			if (a.getFromState() != b.getFromState()
					|| a.getActionIndex() != b.getActionIndex()
					|| !a.getActionLabel().equals(b.getActionLabel())
					|| a.getTargetState() != b.getTargetState()) return false;
		}
		return true;
	}

	private static final class CaptureContext {
		private final IdentityHashMap<CompactState, Boolean> seen =
				new IdentityHashMap<CompactState, Boolean>();
		private long nodes;
		private long states;
		private long actions;
		private long transitions;
		private long tupleCells;

		private void preflight(CompactState source) {
			long componentCount = source.components == null
					? 0L : source.components.length;
			long stateCount = Math.max(0, source.maxStates);
			long actionCount = source.alphabet == null
					? 0L : source.alphabet.length;
			long diagnosticRows = source.statePlusActionToComponentStates == null
					? 0L : source.statePlusActionToComponentStates.size();
			long tupleRows = stateCount + diagnosticRows;
			if (nodes >= MAX_NODES
					|| stateCount > MAX_AGGREGATE_STATES - states
					|| actionCount > MAX_AGGREGATE_ACTIONS - actions
					|| (componentCount != 0L
						&& tupleRows > (MAX_AGGREGATE_TUPLE_CELLS - tupleCells)
								/ componentCount)) {
				throw new IllegalArgumentException(
						"CompactState composition tree exceeds the aggregate cap.");
			}
		}

		private int remainingTransitions() {
			long remaining = MAX_AGGREGATE_TRANSITIONS - transitions;
			return (int) Math.min(4_000_000L, remaining);
		}

		private void add(CompactStateCanonicalSnapshot snapshot) {
			nodes++;
			states += snapshot.getStateCount();
			actions += snapshot.getActions().size();
			transitions += snapshot.getTransitions().size();
			tupleCells += ((long) snapshot.getStateCount()
					+ (long) snapshot.getNativeFirstOutcomeDiagnostics().size())
					* (long) snapshot.getComponentNames().size();
			if (nodes > MAX_NODES || states > MAX_AGGREGATE_STATES
					|| actions > MAX_AGGREGATE_ACTIONS
					|| transitions > MAX_AGGREGATE_TRANSITIONS
					|| tupleCells > MAX_AGGREGATE_TUPLE_CELLS) {
				throw new IllegalArgumentException(
						"CompactState composition tree exceeds the aggregate cap.");
			}
		}
	}

	private static final class ImmutableCensus {
		private long nodes;
		private long states;
		private long actions;
		private long transitions;
		private long tupleCells;
	}
}
