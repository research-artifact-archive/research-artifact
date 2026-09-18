package ltsa.updatingControllers.export;

import ltsa.lts.CompactState;
import ltsa.lts.Declaration;
import ltsa.lts.EventState;
import ltsa.lts.LTSConstants;
import ltsa.lts.M9EventStateWalker;
import ltsa.lts.ProbabilisticEventState;
import ltsa.lts.util.MTSUtils;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Lossless snapshot of the LTSA fields used by the M9 native endpoint gate.
 * It deliberately reads the raw alphabet and EventState chains and never
 * calls reachability, clone, getAlphabet(), or the MTS converters.
 */
public final class CompactStateCanonicalSnapshot {
	private static final int MAX_STATES = 250000;
	private static final int MAX_ACTIONS = 8192;
	private static final int MAX_TRANSITIONS = 4000000;
	private static final int MAX_COMPONENTS = 64;
	private static final int MAX_ACTION_CHARS = 256;
	private static final int MAX_NAME_CHARS = 256;
	private static final long MAX_COMPONENT_TUPLE_CELLS = 16000000L;
    private final String name;
    private final int stateCount;
    private final int initialState;
    private final int endState;
    private final List<Action> actions;
    private final List<Transition> transitions;
    private final Set<Integer> emptyTransitionStates;
    private final List<String> componentNames;
    private final Map<Integer, List<Integer>> componentStateTuples;
	private final Map<String, List<Integer>> nativeFirstOutcomeDiagnostics;

    public static CompactStateCanonicalSnapshot fromRaw(CompactState source) {
		return fromRaw(source, false);
	}

	public static CompactStateCanonicalSnapshot fromRaw(
			CompactState source,
			boolean requireCompositionProvenance) {
		return fromRawBounded(
				source, requireCompositionProvenance, MAX_TRANSITIONS);
	}

	static CompactStateCanonicalSnapshot fromRawBounded(
			CompactState source,
			boolean requireCompositionProvenance,
			int transitionBudget) {
		if (transitionBudget < 0 || transitionBudget > MAX_TRANSITIONS) {
			throw new IllegalArgumentException(
					"CompactState transition budget is outside the registered profile.");
		}
        if (source == null || source.name == null || source.name.isEmpty()
				|| source.name.length() > MAX_NAME_CHARS) {
            throw new IllegalArgumentException("CompactState name is required.");
        }
        if (source.maxStates <= 0 || source.states == null
                || source.states.length != source.maxStates) {
            throw new IllegalArgumentException("CompactState state array is invalid.");
        }
        if (source.alphabet == null || source.alphabet.length == 0) {
            throw new IllegalArgumentException("CompactState alphabet is empty.");
        }
		if (source.maxStates > MAX_STATES
				|| source.alphabet.length > MAX_ACTIONS) {
			throw new IllegalArgumentException(
					"CompactState exceeds the registered raw snapshot resource profile.");
		}
        if (source.endseq != -9999
				&& source.endseq != LTSConstants.NO_SEQUENCE_FOUND
                && (source.endseq < 0 || source.endseq >= source.maxStates)) {
            throw new IllegalArgumentException("CompactState END state is invalid.");
        }

        List<Action> actions = new ArrayList<Action>();
        Set<String> labels = new LinkedHashSet<String>();
        for (int index = 0; index < source.alphabet.length; index++) {
            String label = source.alphabet[index];
            if (label == null || label.isEmpty()
					|| label.length() > MAX_ACTION_CHARS) {
                throw new IllegalArgumentException(
                        "CompactState alphabet labels must be nonempty.");
            }
			if (!labels.add(label) && !"tau".equals(label)) {
				throw new IllegalArgumentException(
						"Only the native converter's duplicate tau label is permitted.");
            }
            if (MTSUtils.isMaybe(label)) {
                throw new IllegalArgumentException(
                        "Modal CompactState actions are outside the M9 UAV schema.");
            }
            actions.add(new Action(index, label));
        }
		if (!"tau".equals(actions.get(0).getLabel())) {
			throw new IllegalArgumentException(
					"CompactState alphabet index zero must be native tau.");
		}

        List<Transition> transitions = new ArrayList<Transition>();
        Set<String> triples = new LinkedHashSet<String>();
        Set<Integer> deadlocks = new LinkedHashSet<Integer>();
        for (int from = 0; from < source.maxStates; from++) {
            EventState head = source.states[from];
            if (head == null) {
                deadlocks.add(Integer.valueOf(from));
                continue;
            }
			int remaining = transitionBudget - transitions.size();
			for (M9EventStateWalker.Edge transition
					: M9EventStateWalker.flattenExact(head, remaining)) {
                int event = transition.getEvent();
                int target = transition.getTarget();
                if (event < 0 || event >= actions.size()) {
                    throw new IllegalArgumentException(
                            "CompactState transition has an invalid action index.");
                }
                if (target != Declaration.ERROR
                        && (target < 0 || target >= source.maxStates)) {
                    throw new IllegalArgumentException(
                            "CompactState transition has an invalid target state.");
                }
                String triple = from + "\u0000" + event + "\u0000" + target;
                if (!triples.add(triple)) {
                    throw new IllegalArgumentException(
                            "Duplicate CompactState transition is noncanonical.");
                }
                transitions.add(new Transition(
                        from, event, actions.get(event).getLabel(), target));
            }
        }
        Collections.sort(transitions, new Comparator<Transition>() {
            @Override
            public int compare(Transition left, Transition right) {
                int value = Integer.compare(left.fromState, right.fromState);
                if (value != 0) return value;
                value = left.actionLabel.compareTo(right.actionLabel);
                if (value != 0) return value;
                value = Integer.compare(left.actionIndex, right.actionIndex);
                if (value != 0) return value;
                return Integer.compare(left.targetState, right.targetState);
            }
        });

        List<String> componentNames = new ArrayList<String>();
        Map<Integer, List<Integer>> componentTuples =
                new LinkedHashMap<Integer, List<Integer>>();
        boolean hasAnyCompositionField = source.components != null
                || source.stateToComponentStates != null
                || source.statePlusActionToComponentStates != null;
		if (requireCompositionProvenance && !hasAnyCompositionField) {
			throw new IllegalArgumentException(
					"CompactState composition provenance is required for this role.");
		}
		Map<String, List<Integer>> transitionTuples =
				new LinkedHashMap<String, List<Integer>>();
        if (hasAnyCompositionField) {
            if (source.components == null || source.components.length == 0
					|| source.components.length > MAX_COMPONENTS
                    || source.stateToComponentStates == null
                    || source.stateToComponentStates.isEmpty()
                    || source.statePlusActionToComponentStates == null) {
                throw new IllegalArgumentException(
                        "CompactState composition provenance is partial.");
            }
			long componentTupleRows = (long) source.maxStates
					+ (long) source.statePlusActionToComponentStates.size();
			if (source.stateToComponentStates.size() != source.maxStates
					|| componentTupleRows
							> MAX_COMPONENT_TUPLE_CELLS
									/ source.components.length) {
				throw new IllegalArgumentException(
						"CompactState composition provenance exceeds its bounded census.");
			}
			if (source.statePlusActionToComponentStates.size()
					> transitions.size()) {
				throw new IllegalArgumentException(
						"Transition component tuple has no native transition bucket.");
			}
            for (CompactState component : source.components) {
                if (component == null || component.name == null
						|| component.name.isEmpty()
						|| component.name.length() > MAX_NAME_CHARS) {
                    throw new IllegalArgumentException(
                            "CompactState component name is missing.");
                }
                componentNames.add(component.name);
            }
            for (int state = 0; state < source.maxStates; state++) {
                int[] tuple = source.stateToComponentStates.get(
                        Integer.valueOf(state));
                if (tuple == null || tuple.length != source.components.length) {
                    throw new IllegalArgumentException(
                            "CompactState component tuple census is incomplete.");
                }
                List<Integer> copied = new ArrayList<Integer>(tuple.length);
				for (int componentIndex = 0;
						componentIndex < tuple.length; componentIndex++) {
					int localState = tuple[componentIndex];
					if (localState < 0
							|| localState >= source.components[componentIndex].maxStates) {
						throw new IllegalArgumentException(
								"CompactState component tuple leaves its local state domain.");
					}
					copied.add(Integer.valueOf(localState));
                }
                componentTuples.put(Integer.valueOf(state),
                        Collections.unmodifiableList(copied));
            }
			Set<Integer> expectedStateKeys = new LinkedHashSet<Integer>();
			for (int state = 0; state < source.maxStates; state++) {
				expectedStateKeys.add(Integer.valueOf(state));
			}
			if (!source.stateToComponentStates.keySet().equals(expectedStateKeys)) {
				throw new IllegalArgumentException(
						"CompactState component tuple table has extra state keys.");
			}
			Set<String> expectedTransitionTupleKeys = new LinkedHashSet<String>();
			Map<String, Set<Integer>> tupleKeyTargets =
					new LinkedHashMap<String, Set<Integer>>();
			for (Transition transition : transitions) {
				String key = transition.fromState + "\u0000"
						+ transition.actionLabel;
				expectedTransitionTupleKeys.add(key);
				Set<Integer> targets = tupleKeyTargets.get(key);
				if (targets == null) {
					targets = new LinkedHashSet<Integer>();
					tupleKeyTargets.put(key, targets);
				}
				targets.add(Integer.valueOf(transition.targetState));
			}
			Set<String> actualTransitionTupleKeys = new LinkedHashSet<String>();
			for (Map.Entry<java.util.AbstractMap.SimpleEntry<Integer, String>, int[]> entry
					: source.statePlusActionToComponentStates.entrySet()) {
				java.util.AbstractMap.SimpleEntry<Integer, String> key = entry.getKey();
				if (key == null || key.getKey() == null || key.getValue() == null
						|| !expectedStateKeys.contains(key.getKey())
						|| !labels.contains(key.getValue())) {
					throw new IllegalArgumentException(
							"CompactState transition tuple key is invalid.");
				}
				int[] tuple = entry.getValue();
				if (tuple == null || tuple.length != source.components.length) {
					throw new IllegalArgumentException(
							"CompactState transition tuple has the wrong arity.");
				}
				String canonicalKey = key.getKey() + "\u0000" + key.getValue();
				Set<Integer> bucketTargets = tupleKeyTargets.get(canonicalKey);
				if (bucketTargets == null) {
					throw new IllegalArgumentException(
							"Transition component tuple has no native transition bucket.");
				}
				boolean errorOutcome = bucketTargets.contains(
						Integer.valueOf(Declaration.ERROR));
				if (errorOutcome && bucketTargets.size() != 1) {
					throw new IllegalArgumentException(
							"A mixed ERROR/non-ERROR bucket has no per-outcome component tuple.");
				}
				if (!actualTransitionTupleKeys.add(canonicalKey)) {
					throw new IllegalArgumentException(
							"CompactState transition tuple key is duplicated.");
				}
				List<Integer> copied = new ArrayList<Integer>(tuple.length);
				boolean containsComponentError = false;
				if (!errorOutcome) {
					boolean matchesNativeTarget = false;
					for (Integer target : bucketTargets) {
						int[] targetTuple = source.stateToComponentStates.get(target);
						if (targetTuple != null && Arrays.equals(tuple, targetTuple)) {
							matchesNativeTarget = true;
							break;
						}
					}
					if (!matchesNativeTarget) {
						throw new IllegalArgumentException(
								"Transition component tuple matches no native target outcome.");
					}
				}
				for (int componentIndex = 0;
						componentIndex < tuple.length; componentIndex++) {
					int localState = tuple[componentIndex];
					if (localState == Declaration.ERROR && errorOutcome) {
						containsComponentError = true;
						copied.add(Integer.valueOf(localState));
						continue;
					}
					if (localState < 0
							|| localState >= source.components[componentIndex].maxStates) {
						throw new IllegalArgumentException(
								"CompactState transition tuple leaves its local state domain.");
					}
					copied.add(Integer.valueOf(localState));
				}
				if (errorOutcome != containsComponentError) {
					throw new IllegalArgumentException(
							"Transition component tuple disagrees with ERROR outcome typing.");
				}
				transitionTuples.put(canonicalKey,
						Collections.unmodifiableList(copied));
			}
			if (!actualTransitionTupleKeys.equals(expectedTransitionTupleKeys)) {
				throw new IllegalArgumentException(
						"CompactState transition tuple census is incomplete.");
			}
			List<String> sortedTransitionTupleKeys =
					new ArrayList<String>(transitionTuples.keySet());
			Collections.sort(sortedTransitionTupleKeys);
			Map<String, List<Integer>> sortedTransitionTuples =
					new LinkedHashMap<String, List<Integer>>();
			for (String key : sortedTransitionTupleKeys) {
				sortedTransitionTuples.put(key, transitionTuples.get(key));
			}
			transitionTuples.clear();
			transitionTuples.putAll(sortedTransitionTuples);
        }

        return new CompactStateCanonicalSnapshot(
                source.name,
                source.maxStates,
                0,
                source.endseq,
                actions,
                transitions,
                deadlocks,
                componentNames,
				componentTuples,
				transitionTuples);
    }

    private CompactStateCanonicalSnapshot(
            String name,
            int stateCount,
            int initialState,
            int endState,
            List<Action> actions,
            List<Transition> transitions,
            Set<Integer> deadlockStates,
            List<String> componentNames,
			Map<Integer, List<Integer>> componentStateTuples,
			Map<String, List<Integer>> transitionComponentTuples) {
        this.name = name;
        this.stateCount = stateCount;
        this.initialState = initialState;
        this.endState = endState;
        this.actions = Collections.unmodifiableList(new ArrayList<Action>(actions));
        this.transitions = Collections.unmodifiableList(
                new ArrayList<Transition>(transitions));
		this.emptyTransitionStates = Collections.unmodifiableSet(
                new LinkedHashSet<Integer>(deadlockStates));
        this.componentNames = Collections.unmodifiableList(
                new ArrayList<String>(componentNames));
        this.componentStateTuples = Collections.unmodifiableMap(
                new LinkedHashMap<Integer, List<Integer>>(componentStateTuples));
		this.nativeFirstOutcomeDiagnostics = Collections.unmodifiableMap(
				new LinkedHashMap<String, List<Integer>>(transitionComponentTuples));
    }

    public String getName() { return name; }
    public int getStateCount() { return stateCount; }
    public int getInitialState() { return initialState; }
    public int getEndState() { return endState; }
    public List<Action> getActions() { return actions; }
    public List<Transition> getTransitions() { return transitions; }
	public Set<Integer> getEmptyTransitionStates() { return emptyTransitionStates; }
    public List<String> getComponentNames() { return componentNames; }
    public Map<Integer, List<Integer>> getComponentStateTuples() {
        return componentStateTuples;
    }
	public Map<String, List<Integer>> getNativeFirstOutcomeDiagnostics() {
		return nativeFirstOutcomeDiagnostics;
	}

    public static final class Action {
        private final int nativeIndex;
        private final String label;

        private Action(int nativeIndex, String label) {
            this.nativeIndex = nativeIndex;
            this.label = label;
        }

        public int getNativeIndex() { return nativeIndex; }
        public String getLabel() { return label; }
    }

    public static final class Transition {
        private final int fromState;
        private final int actionIndex;
        private final String actionLabel;
        private final int targetState;

        private Transition(
                int fromState,
                int actionIndex,
                String actionLabel,
                int targetState) {
            this.fromState = fromState;
            this.actionIndex = actionIndex;
            this.actionLabel = actionLabel;
            this.targetState = targetState;
        }

        public int getFromState() { return fromState; }
        public int getActionIndex() { return actionIndex; }
        public String getActionLabel() { return actionLabel; }
        public int getTargetState() { return targetState; }
    }
}
