package ltsa.updatingControllers.export;

import MTSTools.ac.ic.doc.commons.relations.Pair;
import MTSTools.ac.ic.doc.commons.relations.BinaryRelation;
import MTSTools.ac.ic.doc.mtstools.model.MTS;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;

/** Immutable, sorted snapshot of a finite required-transition MTS. */
public final class M9MtsSnapshot {
    private static final long MAX_STATES = 250_000L;
    private static final long MAX_ACTIONS = 8_192L;
    private static final long MAX_BUCKETS = 2_000_000L;
    private static final long MAX_OUTCOMES = 4_000_000L;
	private static final int MAX_ACTION_CHARS = 256;

    private final long initialState;
    private final Set<Long> states;
    private final Set<String> actions;
    private final Map<Long, Map<String, Set<Long>>> post;
    private final long bucketCount;
    private final long outcomeCount;

    public static M9MtsSnapshot capture(MTS<Long, String> source) {
        M9MtsSnapshot result = capturePass(source, null);
		requireStableSourceEquals(source, result);
        return result;
    }

    /**
     * Replays the bounded canonical capture against an already-immutable
     * authority without retaining another complete Post relation.  This is
     * used at composition seams where the authority snapshot is already part
     * of a frozen projection and only temporal stability of the live MTS must
     * be established.
     */
    static void requireStableSourceEquals(
            MTS<Long, String> source,
            M9MtsSnapshot expected) {
        if (expected == null) {
            throw new IllegalArgumentException(
                    "Expected MTS authority snapshot is absent.");
        }
		// Two row-wise passes catch a one-shot mutation of an already-checked
		// row without retaining a second complete relation.  Production still
		// runs this inside a fresh single-owner materializer worker.
        capturePass(source, expected);
		capturePass(source, expected);
    }

    /**
     * Captures once when {@code expected} is null and otherwise performs a
     * second, bounded pass that must reproduce the exact canonical snapshot.
     * The verification pass retains only one row at a time, so the stability
     * check does not duplicate the complete transition relation in memory.
     */
    private static M9MtsSnapshot capturePass(
            MTS<Long, String> source,
            M9MtsSnapshot expected) {
        if (source == null) {
            throw new IllegalArgumentException("MTS source is absent.");
        }
        Long initial = source.getInitialState();
        Set<Long> declaredStates = source.getStates();
        Set<String> declaredActions = source.getActions();
        if (initial == null || declaredStates == null || declaredActions == null) {
            throw new IllegalArgumentException(
                    "MTS must have finite state and action declarations.");
        }
        requireResourceCensus(
                declaredStates.size(), declaredActions.size(), 0L, 0L);

        List<Long> sortedStates = boundedStateCopy(declaredStates);
        List<String> sortedActions = boundedActionCopy(declaredActions);
        if (!sortedStates.contains(initial)) {
            throw new IllegalArgumentException(
                    "MTS must have a retained initial state.");
        }
		if (initial.longValue() == -1L) {
			throw new IllegalArgumentException(
					"LTSA ERROR cannot be the initial M9 state.");
		}

        Collections.sort(sortedStates);
        Collections.sort(sortedActions);

        if (expected != null
                && (expected.initialState != initial.longValue()
                || !expected.states.equals(new LinkedHashSet<Long>(sortedStates))
                || !expected.actions.equals(new LinkedHashSet<String>(sortedActions)))) {
            throw new IllegalArgumentException(
                    "MTS declarations changed during canonical capture.");
        }

        Set<Long> stateDomain = new LinkedHashSet<Long>(sortedStates);
        Set<String> actionDomain = new LinkedHashSet<String>(sortedActions);

        Map<Long, Map<String, Set<Long>>> post = expected == null
                ? new LinkedHashMap<Long, Map<String, Set<Long>>>() : null;
        long buckets = 0L;
        long outcomes = 0L;
        for (Long state : sortedStates) {
            BinaryRelation<String, Long> maybe = source.getTransitions(
                    state, MTS.TransitionType.MAYBE);
            BinaryRelation<String, Long> required = source.getTransitions(
                    state, MTS.TransitionType.REQUIRED);
            if (maybe == null || required == null) {
                throw new IllegalArgumentException(
                        "MTS transition rows must be total over declared states.");
            }
            if (!maybe.isEmpty()) {
                throw new IllegalArgumentException(
                        "M9 traditional snapshot does not permit MAYBE transitions.");
            }
            Map<String, Set<Long>> mutable =
                    new LinkedHashMap<String, Set<Long>>();
			if (state.longValue() == -1L
					&& !required.isEmpty()) {
				throw new IllegalArgumentException(
						"LTSA ERROR must be a terminal unsafe sink.");
			}
            for (Pair<String, Long> transition : required) {
                if (transition == null) {
                    throw new IllegalArgumentException(
                            "MTS transition entries must be nonnull.");
                }
                String action = transition.getFirst();
                Long target = transition.getSecond();
                if (action == null || target == null
                        || !actionDomain.contains(action)
                        || !stateDomain.contains(target)) {
                    throw new IllegalArgumentException(
                            "Transition leaves the declared MTS domain.");
                }
                Set<Long> targets = mutable.get(action);
                if (targets == null) {
                    requireResourceCensus(
                            sortedStates.size(), sortedActions.size(),
                            buckets + 1L, outcomes);
                    targets = new TreeSet<Long>();
                    mutable.put(action, targets);
                    buckets++;
                }
                requireResourceCensus(
                        sortedStates.size(), sortedActions.size(),
                        buckets, outcomes + 1L);
                if (!targets.add(target)) {
                    throw new IllegalArgumentException(
                            "Duplicate MTS transition is noncanonical.");
                }
                outcomes++;
            }

            List<String> enabled = new ArrayList<String>(mutable.keySet());
            Collections.sort(enabled);
            Map<String, Set<Long>> row =
                    new LinkedHashMap<String, Set<Long>>();
            for (String action : enabled) {
                Set<Long> targets = mutable.get(action);
                row.put(action, Collections.unmodifiableSet(
                        new LinkedHashSet<Long>(targets)));
            }
            Map<String, Set<Long>> canonicalRow =
                    Collections.unmodifiableMap(row);
            if (expected == null) {
                post.put(state, canonicalRow);
            } else if (!canonicalRow.equals(expected.post.get(state))) {
                throw new IllegalArgumentException(
                        "MTS transitions changed during canonical capture.");
            }
        }

        requireResourceCensus(
                sortedStates.size(), sortedActions.size(), buckets, outcomes);
        if (expected != null) {
            Set<Long> finalStates = source.getStates();
            Set<String> finalActions = source.getActions();
            if (finalStates == null || finalActions == null) {
                throw new IllegalArgumentException(
                        "MTS declarations changed during canonical capture.");
            }
            requireResourceCensus(
                    finalStates.size(), finalActions.size(), buckets, outcomes);
            if (expected.bucketCount != buckets || expected.outcomeCount != outcomes
                    || expected.post.size() != sortedStates.size()
                    || !initial.equals(source.getInitialState())
                    || !stateDomain.equals(new LinkedHashSet<Long>(
                            boundedStateCopy(finalStates)))
                    || !actionDomain.equals(new LinkedHashSet<String>(
                            boundedActionCopy(finalActions)))) {
                throw new IllegalArgumentException(
                        "MTS changed during canonical capture.");
            }
            return expected;
        }

        return new M9MtsSnapshot(
                initial.longValue(),
                sortedStates,
                sortedActions,
                post,
                buckets,
                outcomes);
    }

    static void requireResourceCensus(
            long states,
            long actions,
            long buckets,
            long outcomes) {
        if (states < 0L || states > MAX_STATES
                || actions < 0L || actions > MAX_ACTIONS
                || buckets < 0L || buckets > MAX_BUCKETS
                || outcomes < 0L || outcomes > MAX_OUTCOMES) {
            throw new IllegalArgumentException(
                    "MTS exceeds the registered finite resource profile.");
        }
    }

    private static List<Long> boundedStateCopy(Set<Long> source) {
        List<Long> result = new ArrayList<Long>(
                Math.min(source.size(), (int) MAX_STATES));
        for (Long state : source) {
            if (state == null) {
                throw new IllegalArgumentException(
                        "MTS state identifiers must be nonnull.");
            }
            if (result.size() >= MAX_STATES) {
                throw new IllegalArgumentException(
                        "MTS exceeds the registered finite resource profile.");
            }
            result.add(state);
        }
        if (result.size() != source.size()) {
            throw new IllegalArgumentException(
                    "MTS declarations changed during canonical capture.");
        }
        return result;
    }

    private static List<String> boundedActionCopy(Set<String> source) {
        List<String> result = new ArrayList<String>(
                Math.min(source.size(), (int) MAX_ACTIONS));
        for (String action : source) {
            if (action == null) {
                throw new IllegalArgumentException(
                        "MTS action identifiers must be nonnull.");
            }
			if (action.length() > MAX_ACTION_CHARS) {
				throw new IllegalArgumentException(
						"MTS action identifier exceeds the registered byte profile.");
			}
            if (result.size() >= MAX_ACTIONS) {
                throw new IllegalArgumentException(
                        "MTS exceeds the registered finite resource profile.");
            }
            result.add(action);
        }
        if (result.size() != source.size()) {
            throw new IllegalArgumentException(
                    "MTS declarations changed during canonical capture.");
        }
        return result;
    }

    private M9MtsSnapshot(
            long initialState,
            List<Long> states,
            List<String> actions,
            Map<Long, Map<String, Set<Long>>> post,
            long bucketCount,
            long outcomeCount) {
        this.initialState = initialState;
        this.states = Collections.unmodifiableSet(
                new LinkedHashSet<Long>(states));
        this.actions = Collections.unmodifiableSet(
                new LinkedHashSet<String>(actions));
        this.post = Collections.unmodifiableMap(
                new LinkedHashMap<Long, Map<String, Set<Long>>>(post));
        this.bucketCount = bucketCount;
        this.outcomeCount = outcomeCount;
    }

    public long getInitialState() {
        return initialState;
    }

    public Set<Long> getStates() {
        return states;
    }

    public Set<String> getActions() {
        return actions;
    }

    public Map<Long, Map<String, Set<Long>>> getPost() {
        return post;
    }

    public long getBucketCount() {
        return bucketCount;
    }

    public long getOutcomeCount() {
        return outcomeCount;
    }

	public static boolean canonicalEquals(
			M9MtsSnapshot left,
			M9MtsSnapshot right) {
		return left != null && right != null
				&& left.initialState == right.initialState
				&& left.bucketCount == right.bucketCount
				&& left.outcomeCount == right.outcomeCount
				&& left.states.equals(right.states)
				&& left.actions.equals(right.actions)
				&& left.post.equals(right.post);
	}
}
