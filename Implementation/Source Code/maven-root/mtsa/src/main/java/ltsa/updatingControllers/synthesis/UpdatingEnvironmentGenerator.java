package ltsa.updatingControllers.synthesis;

import MTSTools.ac.ic.doc.commons.relations.Pair;
import MTSTools.ac.ic.doc.mtstools.model.MTS;
import MTSTools.ac.ic.doc.mtstools.model.impl.UpdatingEnvironment;
import MTSTools.ac.ic.doc.mtstools.model.impl.MTSImpl;
import ltsa.control.util.ControllerUtils;
import ltsa.updatingControllers.UpdateConstants;

import java.util.*;

public class UpdatingEnvironmentGenerator {

    private final MTS<Long, String> oldController;
    private final MTS<Long, String> mapping;

    private UpdatingEnvironment updEnv;
    private Map<Long, Long> mappingToUpdEnv;
	private ArrayList<Long> eParallelCStates; // used for relabeling actions
	private final Set<Long> oldControllerStates;
	private final Map<Long, Set<Long>> beginUpdateSourcesByMappingState;
	private final Set<BeginUpdateRow> beginUpdateRows;
	private final boolean strictM9;
	private boolean generated;
	private boolean generationCompleted;

	public UpdatingEnvironmentGenerator(MTS<Long, String> oldController, MTS<Long, String> mapping) {
		this(oldController, mapping, false);
	}

	public UpdatingEnvironmentGenerator(
			MTS<Long, String> oldController,
			MTS<Long, String> mapping,
			boolean strictM9) {

        this.oldController = validatedCopy(
				oldController, "old controller", false, strictM9);
        this.mapping = validatedCopy(
				mapping, "mapping environment", true, strictM9);
		this.strictM9 = strictM9;

        updEnv = new UpdatingEnvironment(this.oldController);
        mappingToUpdEnv = new HashMap<Long, Long>();
		eParallelCStates = new ArrayList<Long>(updEnv.getStates());
		oldControllerStates = new LinkedHashSet<Long>(this.oldController.getStates());
		beginUpdateSourcesByMappingState = new LinkedHashMap<Long, Set<Long>>();
		beginUpdateRows = new LinkedHashSet<BeginUpdateRow>();
		generated = false;
		generationCompleted = false;

	}

	public void generateEnvironment() {
		if (generated) {
			throw new IllegalStateException(
					"Updating environment generation is one-shot.");
		}
		generated = true;

        linkWithBeginUpdate();
        completeWithMapping();
		if (strictM9) {
			validateCompleteGeneration();
		}
		generationCompleted = true;
	}

	private static MTS<Long, String> validatedCopy(
			MTS<Long, String> source,
			String role,
			boolean permitMappingReconfigure,
			boolean strictM9) {
		if (source == null || source.getInitialState() == null
				|| source.getStates() == null || source.getStates().isEmpty()
				|| !source.getStates().contains(source.getInitialState())) {
			throw new IllegalArgumentException(role + " has an invalid state domain.");
		}
		if (strictM9 && source.getStates().contains(Long.valueOf(-1L))) {
			throw new IllegalArgumentException(
					role + " contains LTSA ERROR; the pre-GR schema requires an explicit terminal.");
		}
		Set<String> reserved = new LinkedHashSet<String>(Arrays.asList(
				UpdateConstants.BEGIN_UPDATE,
				UpdateConstants.STOP_OLD_SPEC,
				UpdateConstants.START_NEW_SPEC,
				UpdateConstants.FINISH_UPDATE));
		if (!permitMappingReconfigure) {
			reserved.add(UpdateConstants.RECONFIGURE);
		}
		for (String action : source.getActions()) {
			if (action == null || action.isEmpty()) {
				throw new IllegalArgumentException(role + " has an empty action.");
			}
			if (strictM9 && reserved.contains(action)) {
				throw new IllegalArgumentException(
						role + " already contains reserved update action " + action + ".");
			}
			if (strictM9 && "tau".equals(action)) {
				for (Long state : source.getStates()) {
					if (!source.getTransitions(state, MTS.TransitionType.REQUIRED)
							.getImage(action).isEmpty()) {
						throw new IllegalArgumentException(
								role + " contains a native tau transition outside the pre-GR schema.");
					}
				}
			}
		}

		MTSImpl<Long, String> copy = new MTSImpl<Long, String>(
				source.getInitialState());
		for (Long state : source.getStates()) {
			if (state == null) {
				throw new IllegalArgumentException(role + " has a null state.");
			}
			copy.addState(state);
		}
		for (String action : source.getActions()) {
			if (!strictM9 || !"tau".equals(action)) {
				copy.addAction(action);
			}
		}
		for (Long state : source.getStates()) {
			if (strictM9
					&& !source.getTransitions(state, MTS.TransitionType.MAYBE).isEmpty()) {
				throw new IllegalArgumentException(
						role + " contains MAYBE transitions outside the pre-GR schema.");
			}
			for (Pair<String, Long> transition : source.getTransitions(
					state, MTS.TransitionType.REQUIRED)) {
				if (!source.getActions().contains(transition.getFirst())
						|| !source.getStates().contains(transition.getSecond())) {
					throw new IllegalArgumentException(
							role + " has a transition outside its declared domain.");
				}
				copy.addRequired(state, transition.getFirst(), transition.getSecond());
			}
		}
		return copy;
	}

    /**
     * pre: updEnv is E||C
     * post: updEnv is E||C plus some states of E (only the one that has an incoming hotSwapIn transition)
     * states from E has a stopOldSpec, startNewSpec actions
     */
    private void linkWithBeginUpdate() {

        // updEnv.addAction(UpdateConstants.BEGIN_UPDATE);
        updEnv.addAction(UpdateConstants.BEGIN_UPDATE);
        addBeginUpdateTransition(updEnv.getInitialState(), mapping.getInitialState());
        eParallelCStates.add(updEnv.getInitialState());

        // BFS
		Queue<Pair<Long,Long>> toVisit = new LinkedList<Pair<Long,Long>>();
		Pair<Long, Long> firstState = new Pair(new Long(oldController.getInitialState()), new Long(mapping.getInitialState()));
		toVisit.add(firstState);
		ArrayList<Pair<Long, Long>> discovered = new ArrayList<Pair<Long, Long>>();

		while (!toVisit.isEmpty()) {
			Pair<Long, Long> actual = toVisit.remove();
			if (!discovered.contains(actual)) {
				discovered.add(actual);
				for (Pair<String, Long> action_toState : oldController.getTransitions(actual.getFirst(), MTS.TransitionType.REQUIRED)) {
					toVisit.addAll(nextToVisitInParallelComposition(actual, action_toState));
				}
			}
		}
    }

	private ArrayList<Pair<Long, Long>> nextToVisitInParallelComposition(Pair<Long, Long> actual, Pair<String, Long> transition) {

		ArrayList<Pair<Long, Long>> toVisit = new ArrayList<Pair<Long, Long>>();

		for (Pair<String, Long> action_toStateInMapping : mapping.getTransitions(actual.getSecond(), MTS.TransitionType.REQUIRED)) {

			String actionInMapping = action_toStateInMapping.getFirst();
			Long toStateInMapping = action_toStateInMapping.getSecond();

			if (transition.getFirst().equals(actionInMapping)) {

                //action = action.concat(UpdateControllerSolver.label); // rename the actions so as to
				// distinguish from the controllable in the new problem controller
                eParallelCStates.add(transition.getSecond());

                addBeginUpdateTransition(transition.getSecond(), toStateInMapping);
				toVisit.add(new Pair<Long, Long>(transition.getSecond(), toStateInMapping));
			}
		}

		return toVisit;
	}

	private void addBeginUpdateTransition(Long from, Long originalMappingState) {
		Set<Long> sources = beginUpdateSourcesByMappingState.get(originalMappingState);
		if (sources == null) {
			sources = new LinkedHashSet<Long>();
			beginUpdateSourcesByMappingState.put(originalMappingState, sources);
		}
		sources.add(from);

        Long toState;
        if (mappingToUpdEnv.containsKey(originalMappingState)) {
            toState = mappingToUpdEnv.get(originalMappingState);
            // updEnv.addTransition(from, UpdateConstants.BEGIN_UPDATE, toState);
            updEnv.addTransition(from, UpdateConstants.BEGIN_UPDATE, toState);
        } else {
            Long freshState = updEnv.newState();
            // updEnv.addTransition(from, UpdateConstants.BEGIN_UPDATE, freshState);
            updEnv.addTransition(from, UpdateConstants.BEGIN_UPDATE, freshState);

            mappingToUpdEnv.put(originalMappingState, freshState);
            addStopOldAndStartNewSpecActions(freshState);
			toState = freshState;
        }
		beginUpdateRows.add(new BeginUpdateRow(
				from, originalMappingState, toState));
    }

	private void validateCompleteGeneration() {
		if (!mapping.getActions().contains(UpdateConstants.RECONFIGURE)) {
			throw new IllegalArgumentException(
					"The strict mapping environment has no reconfigure action.");
		}
		Set<Long> requestReachableMappingStates = new LinkedHashSet<Long>();
		Queue<Long> pendingMappingStates = new LinkedList<Long>();
		for (BeginUpdateRow row : beginUpdateRows) {
			if (requestReachableMappingStates.add(row.getMappingState())) {
				pendingMappingStates.add(row.getMappingState());
			}
		}
		while (!pendingMappingStates.isEmpty()) {
			Long state = pendingMappingStates.remove();
			for (Pair<String, Long> edge : mapping.getTransitions(
					state, MTS.TransitionType.REQUIRED)) {
				if (requestReachableMappingStates.add(edge.getSecond())) {
					pendingMappingStates.add(edge.getSecond());
				}
			}
		}
		long reconfigureEdges = 0L;
		for (Long state : requestReachableMappingStates) {
			reconfigureEdges += mapping.getTransitions(
					state, MTS.TransitionType.REQUIRED)
					.getImage(UpdateConstants.RECONFIGURE).size();
		}
		if (reconfigureEdges == 0L) {
			throw new IllegalArgumentException(
					"The strict mapping environment has no reconfigure transition.");
		}
		Set<Long> allSources = new LinkedHashSet<Long>();
		for (BeginUpdateRow row : beginUpdateRows) {
			allSources.add(row.getOldControllerState());
			Long expectedTarget = mappingToUpdEnv.get(row.getMappingState());
			if (!row.getUpdatingState().equals(expectedTarget)) {
				throw new IllegalStateException(
						"hotSwapIn provenance target differs from the mapping image.");
			}
		}
		if (!allSources.equals(oldControllerStates)) {
			throw new IllegalArgumentException(
					"hotSwapIn is not total over the old-controller state domain.");
		}
		Set<Long> generatedUpdateStates = new LinkedHashSet<Long>(
				mappingToUpdEnv.values());
		for (Long state : oldControllerStates) {
			Set<Long> targets = updEnv.getTransitionsFrom(state)
					.getImage(UpdateConstants.BEGIN_UPDATE);
			if (targets.isEmpty() || !generatedUpdateStates.containsAll(targets)) {
				throw new IllegalStateException(
						"An old state has an invalid hotSwapIn image.");
			}
		}
		for (Long state : generatedUpdateStates) {
			if (!updEnv.getTransitionsFrom(state)
					.getImage(UpdateConstants.BEGIN_UPDATE).isEmpty()) {
				throw new IllegalStateException(
						"hotSwapIn is enabled after entering the update region.");
			}
		}
	}

    /**
     * pre: updEnv is E||C plus some states of E (only the one that has an incoming hotSwapIn transition)
     * post: updEnv is E||C -> E -> E'
     * states from E and E' has a stopOldSpec, startNewSpec actions.
     */
	private void completeWithMapping() {

        for (Long originalOldEnvState : mapping.getStates()) {

            for (Pair<String, Long> action_toState : mapping.getTransitions(originalOldEnvState, MTS.TransitionType.REQUIRED)) {

                if (mappingToUpdEnv.containsKey(originalOldEnvState)) {

                    Long updEnvState = mappingToUpdEnv.get(originalOldEnvState);
                    Set<Long> freshState = addTransitionCreatingNewStates(action_toState, updEnvState);
                    addStopOldAndStartNewSpecActions(freshState);
                } else {

                    Long freshUpdEnvState = addState(originalOldEnvState);
                    addStopOldAndStartNewSpecActions(freshUpdEnvState);
                    Set<Long> freshState = addTransitionCreatingNewStates(action_toState, freshUpdEnvState);
                    addStopOldAndStartNewSpecActions(freshState);

                }
            }
        }
	}

    private void addStopOldAndStartNewSpecActions(Set<Long> freshState) {
        if (freshState.isEmpty()) return;
        addStopOldAndStartNewSpecActions(freshState.iterator().next());
    }

    private void addStopOldAndStartNewSpecActions(Long state) {
        updEnv.addAction(UpdateConstants.STOP_OLD_SPEC);
        updEnv.addAction(UpdateConstants.START_NEW_SPEC);
        updEnv.addTransition(state, UpdateConstants.STOP_OLD_SPEC, state);
        updEnv.addTransition(state, UpdateConstants.START_NEW_SPEC, state);
    }

    /**
     *
     * @param action_toState
     * @param state
     * @return empty set if not fresh state was created. A set with the new state if a fresh state was created
     */
	private Set<Long> addTransitionCreatingNewStates(Pair<String, Long> action_toState, Long state) {

        Set<Long> result = new HashSet<Long>();
		updEnv.addAction(action_toState.getFirst());
		if (!mappingToUpdEnv.containsKey(action_toState.getSecond())) {

			Long freshUpdEnvState = addState(action_toState.getSecond());
			updEnv.addTransition(state, action_toState.getFirst(), freshUpdEnvState);
            result.add(freshUpdEnvState);

		} else {
			updEnv.addTransition(state, action_toState.getFirst(), mappingToUpdEnv.get(action_toState.getSecond()));
		}
        return result;
	}

	private Long addState(Long originalState) {

		Long newState = updEnv.newState();
		mappingToUpdEnv.put(originalState, newState);
		return newState;
	}

	public UpdatingEnvironment getUpdEnv(){
		return updEnv;
	}

	/**
	 * Returns an immutable provenance snapshot for the generated updating
	 * environment.  The snapshot deliberately distinguishes original old
	 * controller state identifiers from original mapping-environment state
	 * identifiers even when the two source domains use the same numbers.
	 */
	public Provenance getProvenance() {
		if (!generationCompleted) {
			throw new IllegalStateException(
					"Complete updating-environment generation before requesting provenance.");
		}
		return new Provenance(
				oldControllerStates,
				mappingToUpdEnv,
				beginUpdateSourcesByMappingState,
				beginUpdateRows);
	}

	public static final class BeginUpdateRow {
		private final Long oldControllerState;
		private final Long mappingState;
		private final Long updatingState;

		private BeginUpdateRow(
				Long oldControllerState,
				Long mappingState,
				Long updatingState) {
			this.oldControllerState = oldControllerState;
			this.mappingState = mappingState;
			this.updatingState = updatingState;
		}

		public Long getOldControllerState() { return oldControllerState; }
		public Long getMappingState() { return mappingState; }
		public Long getUpdatingState() { return updatingState; }

		@Override
		public boolean equals(Object other) {
			if (this == other) return true;
			if (!(other instanceof BeginUpdateRow)) return false;
			BeginUpdateRow row = (BeginUpdateRow) other;
			return oldControllerState.equals(row.oldControllerState)
					&& mappingState.equals(row.mappingState)
					&& updatingState.equals(row.updatingState);
		}

		@Override
		public int hashCode() {
			int result = oldControllerState.hashCode();
			result = 31 * result + mappingState.hashCode();
			return 31 * result + updatingState.hashCode();
		}
	}

	public static final class Provenance {
		private final Set<Long> oldControllerStates;
		private final Map<Long, Long> mappingStateToUpdatingState;
		private final Map<Long, Long> updatingStateToMappingState;
		private final Map<Long, Set<Long>> beginUpdateSourcesByMappingState;
		private final Set<BeginUpdateRow> beginUpdateRows;

		private Provenance(
				Collection<Long> oldControllerStates,
				Map<Long, Long> mappingStateToUpdatingState,
				Map<Long, Set<Long>> beginUpdateSourcesByMappingState,
				Collection<BeginUpdateRow> beginUpdateRows) {
			this.oldControllerStates = Collections.unmodifiableSet(
					new LinkedHashSet<Long>(oldControllerStates));

			Map<Long, Long> forward = new LinkedHashMap<Long, Long>();
			Map<Long, Long> inverse = new LinkedHashMap<Long, Long>();
			List<Long> mappingStates = new ArrayList<Long>(
					mappingStateToUpdatingState.keySet());
			Collections.sort(mappingStates);
			for (Long mappingState : mappingStates) {
				Long updatingState = mappingStateToUpdatingState.get(mappingState);
				if (inverse.put(updatingState, mappingState) != null) {
					throw new IllegalStateException(
							"Two mapping states share an updating-environment state.");
				}
				forward.put(mappingState, updatingState);
			}
			this.mappingStateToUpdatingState = Collections.unmodifiableMap(forward);
			this.updatingStateToMappingState = Collections.unmodifiableMap(inverse);

			Map<Long, Set<Long>> sources = new LinkedHashMap<Long, Set<Long>>();
			List<Long> sourceKeys = new ArrayList<Long>(
					beginUpdateSourcesByMappingState.keySet());
			Collections.sort(sourceKeys);
			for (Long mappingState : sourceKeys) {
				List<Long> sortedSources = new ArrayList<Long>(
						beginUpdateSourcesByMappingState.get(mappingState));
				Collections.sort(sortedSources);
				sources.put(mappingState, Collections.unmodifiableSet(
						new LinkedHashSet<Long>(sortedSources)));
			}
			this.beginUpdateSourcesByMappingState =
					Collections.unmodifiableMap(sources);

			List<BeginUpdateRow> rows = new ArrayList<BeginUpdateRow>(beginUpdateRows);
			Collections.sort(rows, new Comparator<BeginUpdateRow>() {
				@Override
				public int compare(BeginUpdateRow left, BeginUpdateRow right) {
					int value = left.getOldControllerState().compareTo(
							right.getOldControllerState());
					if (value != 0) return value;
					value = left.getMappingState().compareTo(right.getMappingState());
					if (value != 0) return value;
					return left.getUpdatingState().compareTo(right.getUpdatingState());
				}
			});
			this.beginUpdateRows = Collections.unmodifiableSet(
					new LinkedHashSet<BeginUpdateRow>(rows));
		}

		public Set<Long> getOldControllerStates() {
			return oldControllerStates;
		}

		public Map<Long, Long> getMappingStateToUpdatingState() {
			return mappingStateToUpdatingState;
		}

		public Map<Long, Long> getUpdatingStateToMappingState() {
			return updatingStateToMappingState;
		}

		public Map<Long, Set<Long>> getBeginUpdateSourcesByMappingState() {
			return beginUpdateSourcesByMappingState;
		}

		public Set<BeginUpdateRow> getBeginUpdateRows() {
			return beginUpdateRows;
		}
	}

}
