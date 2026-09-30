package ltsa.updatingControllers.export;

import ltsa.lts.CompactState;
import ltsa.lts.Declaration;
import ltsa.lts.LTSConstants;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Role-specific fail-closed admission for a materialized deterministic
 * endpoint.  {@link CompactStateCanonicalSnapshot} is intentionally a raw
 * extractor and preserves tau, ERROR, and nondeterminism; those constructs
 * are rejected here before endpoint bytes can enter the M9 decision package.
 *
 * <p>A composed endpoint additionally requires a separately reconstructed
 * {@link M9CompositionProvenance.Projection}.  The native first-outcome map
 * remains diagnostic and is never treated as transition authority.</p>
 */
public final class CompactStateEndpointAdmission {
	private static final int MAX_STATES = 250_000;
	private static final int MAX_ACTIONS = 8_192;
	private static final int MAX_TRANSITIONS = 4_000_000;
	private static final int MAX_COMPONENTS = 64;

	private CompactStateEndpointAdmission() {
	}

	public static Admission admitPrimitive(
			CompactState source,
			boolean allowTerminalEndState) {
		CompactStateCanonicalTree canonicalTree =
				CompactStateCanonicalTree.captureForest(
						new CompactState[]{source}).get(0);
		if (!CompactStateCanonicalTree.canonicalEquals(
					canonicalTree,
					CompactStateCanonicalTree.captureForest(
							new CompactState[]{source}).get(0))) {
			throw new IllegalArgumentException(
					"Primitive endpoint bytes changed during admission.");
		}
		if (!CompactStateCanonicalTree.canonicalEquals(
				canonicalTree,
				CompactStateCanonicalTree.captureForest(
						new CompactState[]{source}).get(0))) {
			throw new IllegalArgumentException(
					"Primitive endpoint changed during final admission verification.");
		}
		CompactStateCanonicalSnapshot snapshot = canonicalTree.getSnapshot();
		if (!snapshot.getComponentNames().isEmpty()) {
			throw new IllegalArgumentException(
					"A primitive endpoint may not carry composition provenance.");
		}
		int normalizedEnd = validateDeterministicGraph(
				snapshot, allowTerminalEndState);
		return new Admission(snapshot, canonicalTree, normalizedEnd, false,
				Collections.<CompactStateCanonicalSnapshot>emptyList());
	}

	public static Admission admitComposed(
			CompactState source,
			M9CompositionProvenance.Projection authority,
			boolean allowTerminalEndState) {
		if (authority == null) {
			throw new IllegalArgumentException(
					"A composed endpoint requires external composition authority.");
		}
		if (source == null || source.components == null) {
			throw new IllegalArgumentException(
					"A composed endpoint has no native child component array.");
		}
		if (source.components.length == 0
				|| source.components.length > MAX_COMPONENTS) {
			throw new IllegalArgumentException(
					"Composed endpoint exceeds the registered component census.");
		}
		CompactState[] childReferences = source.components.clone();
		CompactStateCanonicalTree canonicalTree =
				CompactStateCanonicalTree.captureForest(
						new CompactState[]{source}).get(0);
		List<CompactStateCanonicalTree> childTrees = canonicalTree.getChildren();
		List<CompactStateCanonicalSnapshot> childSnapshots = rootSnapshots(childTrees);
		CompactStateCanonicalSnapshot snapshot = canonicalTree.getSnapshot();
		if (!sameComponentReferences(source.components, childReferences)
				|| !CompactStateCanonicalTree.canonicalEquals(
						canonicalTree,
						CompactStateCanonicalTree.captureForest(
								new CompactState[]{source}).get(0))) {
			throw new IllegalArgumentException(
					"Composed endpoint child bytes changed during admission.");
		}
		if (!sameComponentReferences(source.components, childReferences)
				|| !CompactStateCanonicalTree.canonicalEquals(
						canonicalTree,
						CompactStateCanonicalTree.captureForest(
								new CompactState[]{source}).get(0))) {
			throw new IllegalArgumentException(
					"Composed endpoint changed during final admission verification.");
		}
		int normalizedEnd = validateDeterministicGraph(
				snapshot, allowTerminalEndState);
		M9CompositionProvenance.requireSnapshotReachability(snapshot);
		validateCompositionAuthority(snapshot, childTrees, authority);
		return new Admission(
				snapshot, canonicalTree, normalizedEnd, true, childSnapshots);
	}

	private static int validateDeterministicGraph(
			CompactStateCanonicalSnapshot snapshot,
			boolean allowTerminalEndState) {
		if (snapshot.getStateCount() > MAX_STATES
				|| snapshot.getActions().size() > MAX_ACTIONS
				|| snapshot.getTransitions().size() > MAX_TRANSITIONS
				|| snapshot.getComponentNames().size() > MAX_COMPONENTS) {
			throw new IllegalArgumentException(
					"Endpoint exceeds the registered finite resource profile.");
		}
		int tauCount = 0;
		Set<String> labels = new LinkedHashSet<String>();
		for (CompactStateCanonicalSnapshot.Action action : snapshot.getActions()) {
			String label = action.getLabel();
			validateAsciiLabel(label);
			if ("tau".equals(label)) tauCount++;
			else if (!labels.add(label)) {
				throw new IllegalArgumentException(
						"Endpoint visible alphabet contains a duplicate label.");
			}
		}
		if (tauCount < 1 || tauCount > 2) {
			throw new IllegalArgumentException(
					"Endpoint must retain one or two native tau declarations.");
		}

		Set<String> buckets = new LinkedHashSet<String>();
		for (CompactStateCanonicalSnapshot.Transition edge
				: snapshot.getTransitions()) {
			if ("tau".equals(edge.getActionLabel())) {
				throw new IllegalArgumentException(
						"Enabled tau is outside the deterministic endpoint profile.");
			}
			if (edge.getTargetState() == Declaration.ERROR) {
				throw new IllegalArgumentException(
						"Endpoint Post may not target LTSA ERROR.");
			}
			String bucket = edge.getFromState() + "\u0000" + edge.getActionLabel();
			if (!buckets.add(bucket)) {
				throw new IllegalArgumentException(
						"Endpoint Post is nondeterministic for a state/action bucket.");
			}
		}

		int rawEnd = snapshot.getEndState();
		int normalizedEnd = rawEnd == -9999
				|| rawEnd == LTSConstants.NO_SEQUENCE_FOUND ? -1 : rawEnd;
		for (Integer empty : snapshot.getEmptyTransitionStates()) {
			if (!allowTerminalEndState || empty.intValue() != normalizedEnd) {
				throw new IllegalArgumentException(
						"Endpoint has a non-END empty transition row.");
			}
		}
		if (normalizedEnd >= 0
				&& (!allowTerminalEndState
				|| !snapshot.getEmptyTransitionStates().contains(
						Integer.valueOf(normalizedEnd)))) {
			throw new IllegalArgumentException(
					"A declared END must be the sole permitted empty terminal row.");
		}
		return normalizedEnd;
	}

	private static void validateCompositionAuthority(
			CompactStateCanonicalSnapshot snapshot,
			List<CompactStateCanonicalTree> currentChildren,
			M9CompositionProvenance.Projection authority) {
		if (!snapshot.getComponentNames().equals(authority.getComponentNames())) {
			throw new IllegalArgumentException(
					"Composed endpoint component order differs from authority; actual="
							+ snapshot.getComponentNames() + ", authority="
							+ authority.getComponentNames() + ".");
		}
		if (new LinkedHashSet<String>(snapshot.getComponentNames()).size()
				!= snapshot.getComponentNames().size()
				|| authority.getComponentSnapshots().size()
				!= snapshot.getComponentNames().size()) {
			throw new IllegalArgumentException(
					"Composed endpoint child role census is ambiguous.");
		}
		for (int component = 0;
				component < authority.getComponentSnapshots().size(); component++) {
			if (!snapshot.getComponentNames().get(component).equals(
					authority.getComponentSnapshots().get(component).getName())) {
				throw new IllegalArgumentException(
						"Composed endpoint child snapshot order differs from authority.");
			}
			if (!CompactStateCanonicalTree.canonicalEquals(
					currentChildren.get(component),
					authority.getComponentTrees().get(component))) {
				throw new IllegalArgumentException(
						"Composed endpoint child bytes differ from authority.");
			}
		}
		if (authority.getProductInitialState() != snapshot.getInitialState()) {
			throw new IllegalArgumentException(
					"Composed endpoint initial state differs from authority.");
		}
		Map<Long, List<Integer>> authorityTuples =
				authority.getComponentStateTuples();
		if (new LinkedHashSet<List<Integer>>(
				snapshot.getComponentStateTuples().values()).size()
				!= snapshot.getStateCount()
				|| new LinkedHashSet<List<Integer>>(authorityTuples.values()).size()
				!= authorityTuples.size()) {
			throw new IllegalArgumentException(
					"Composed endpoint component tuples are not injective.");
		}
		if (authorityTuples.size() != snapshot.getStateCount()) {
			throw new IllegalArgumentException(
					"Composed endpoint state tuple census differs from authority.");
		}
		Set<Long> expectedStateKeys = new LinkedHashSet<Long>();
		for (int state = 0; state < snapshot.getStateCount(); state++) {
			expectedStateKeys.add(Long.valueOf(state));
		}
		List<Integer> initialTuple = snapshot.getComponentStateTuples().get(
				Integer.valueOf(snapshot.getInitialState()));
		if (initialTuple == null) {
			throw new IllegalArgumentException(
					"Composed endpoint initial tuple is absent.");
		}
		for (Integer local : initialTuple) {
			if (local.intValue() != 0) {
				throw new IllegalArgumentException(
						"Composed endpoint initial tuple is not the native child initial tuple.");
			}
		}
		if (!authority.getFirstComponentSourceStates().keySet()
				.equals(expectedStateKeys)) {
			throw new IllegalArgumentException(
					"Composed endpoint product-state authority is incomplete.");
		}
		for (int state = 0; state < snapshot.getStateCount(); state++) {
			List<Integer> expected = snapshot.getComponentStateTuples()
					.get(Integer.valueOf(state));
			if (!expected.equals(authorityTuples.get(Long.valueOf(state)))) {
				throw new IllegalArgumentException(
						"Composed endpoint state tuple differs from authority.");
			}
		}

		Set<String> labels = new LinkedHashSet<String>();
		for (CompactStateCanonicalSnapshot.Action action : snapshot.getActions()) {
			labels.add(action.getLabel());
		}
		M9CompositionProvenance.requireBucketBound(
				snapshot.getStateCount(), labels.size());
		Map<String, Set<List<Integer>>> expectedPost =
				new LinkedHashMap<String, Set<List<Integer>>>();
		for (int state = 0; state < snapshot.getStateCount(); state++) {
			for (String label : labels) {
				expectedPost.put(state + "\u0000" + label,
						new LinkedHashSet<List<Integer>>());
			}
		}
		for (CompactStateCanonicalSnapshot.Transition edge
				: snapshot.getTransitions()) {
			List<Integer> targetTuple = snapshot.getComponentStateTuples()
					.get(Integer.valueOf(edge.getTargetState()));
			expectedPost.get(edge.getFromState() + "\u0000"
					+ edge.getActionLabel()).add(targetTuple);
		}
		Map<String, Set<List<Integer>>> canonicalExpected =
				new LinkedHashMap<String, Set<List<Integer>>>();
		for (Map.Entry<String, Set<List<Integer>>> row : expectedPost.entrySet()) {
			canonicalExpected.put(row.getKey(), Collections.unmodifiableSet(
					new LinkedHashSet<List<Integer>>(row.getValue())));
		}
		if (!canonicalExpected.equals(authority.getDerivedComponentPost())) {
			throw new IllegalArgumentException(
					"Composed endpoint Post differs from derived component authority.");
		}
	}

	private static void validateAsciiLabel(String label) {
		for (int index = 0; index < label.length(); index++) {
			char value = label.charAt(index);
			if (value < 0x21 || value > 0x7e) {
				throw new IllegalArgumentException(
						"Endpoint labels must use the registered printable ASCII profile.");
			}
		}
		byte[] bytes = label.getBytes(StandardCharsets.UTF_8);
		if (bytes.length != label.length()) {
			throw new IllegalArgumentException(
					"Endpoint labels must use the registered printable ASCII profile.");
		}
		for (byte value : bytes) {
			int unsigned = value & 0xff;
			if (unsigned < 0x21 || unsigned > 0x7e) {
				throw new IllegalArgumentException(
						"Endpoint labels must use the registered printable ASCII profile.");
			}
		}
	}

	private static List<CompactStateCanonicalSnapshot> rootSnapshots(
			List<CompactStateCanonicalTree> trees) {
		List<CompactStateCanonicalSnapshot> result =
				new ArrayList<CompactStateCanonicalSnapshot>(trees.size());
		for (CompactStateCanonicalTree tree : trees) {
			result.add(tree.getSnapshot());
		}
		return Collections.unmodifiableList(result);
	}

	private static boolean sameComponentReferences(
			CompactState[] current,
			CompactState[] captured) {
		if (current == null || current.length != captured.length) return false;
		for (int index = 0; index < current.length; index++) {
			if (current[index] != captured[index]) return false;
		}
		return true;
	}

	public static final class Admission {
		private final CompactStateCanonicalSnapshot snapshot;
		private final CompactStateCanonicalTree canonicalTree;
		private final int normalizedEndState;
		private final boolean composed;
		private final List<CompactStateCanonicalSnapshot> componentSnapshots;

		private Admission(
				CompactStateCanonicalSnapshot snapshot,
				CompactStateCanonicalTree canonicalTree,
				int normalizedEndState,
				boolean composed,
				List<CompactStateCanonicalSnapshot> componentSnapshots) {
			this.snapshot = snapshot;
			this.canonicalTree = canonicalTree;
			this.normalizedEndState = normalizedEndState;
			this.composed = composed;
			this.componentSnapshots = Collections.unmodifiableList(
					new ArrayList<CompactStateCanonicalSnapshot>(componentSnapshots));
		}

		public CompactStateCanonicalSnapshot getSnapshot() { return snapshot; }
		public CompactStateCanonicalTree getCanonicalTree() { return canonicalTree; }
		public int getNormalizedEndState() { return normalizedEndState; }
		public boolean isComposed() { return composed; }
		public List<CompactStateCanonicalSnapshot> getComponentSnapshots() {
			return componentSnapshots;
		}
	}
}
