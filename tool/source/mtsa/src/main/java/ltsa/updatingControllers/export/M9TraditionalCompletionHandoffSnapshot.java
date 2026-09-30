package ltsa.updatingControllers.export;

import ltsa.updatingControllers.UpdateConstants;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;

/**
 * Immutable zero-edge handoff authority from completed traditional safety
 * states to the exact endpoint Enew/Cnew/CLnew states.  The handoff identifies
 * an atomic load boundary; it never fabricates a hotSwapOut transition.
 */
public final class M9TraditionalCompletionHandoffSnapshot {
	private static final long MAX_HANDOFF_ROWS = 250_000L;
	private final long lifecycleCompleteCoordinate;
	private final Map<Long, List<CompletionCoordinates>> completionStates;

	public static M9TraditionalCompletionHandoffSnapshot capture(
			TraditionalPreGrSnapshot traditional,
			M9EndpointStrategySnapshot strategy,
			M9ClosedLoopEndpointSnapshot closedLoop) {
		if (traditional == null || strategy == null || closedLoop == null
				|| traditional.getCompletionSeed() == null) {
			throw new IllegalArgumentException(
					"Traditional, endpoint, closed-loop, and completion authorities are required.");
		}
		TraditionalPreGrSnapshot.CompletionSeed seed =
				traditional.getCompletionSeed();
		M9CompositionProvenance.Projection strategyEnew = strategy
				.getEnvironmentPrefix().getPrefixProductAuthority();
		if (seed.getNewEnvironment() != strategyEnew
				|| !M9CompositionProvenance.canonicalEquals(
				seed.getNewEnvironment(),
				strategyEnew)) {
			throw new IllegalArgumentException(
					"Completion seed Enew differs from the endpoint strategy prefix.");
		}
		if (!closedLoop.getCoordinates().getSecondStateToFirstState()
				.equals(strategy.getControllerStateToEnewState())) {
			throw new IllegalArgumentException(
					"Closed-loop controller origins differ from the endpoint strategy.");
		}
		M9CompositionProvenance.Projection safetyProjection =
				traditional.getSafetyCompositionProvenance();
		if (safetyProjection.getComponentSnapshots().size() != 2
				|| safetyProjection.getComponentTrees().size() != 2
				|| !safetyProjection.getComponentTrees().get(1)
						.getChildren().isEmpty()) {
			throw new IllegalArgumentException(
					"Traditional safety completion requires exactly one lifecycle monitor.");
		}
		long complete = requireLifecycleCompleteCoordinate(
				safetyProjection.getComponentSnapshots().get(1),
				traditional.getSafetySemantics().getLifecycleActions());

		Map<Long, List<Long>> cnewByEnew = new LinkedHashMap<Long, List<Long>>();
		for (Map.Entry<Long, Long> entry
				: strategy.getControllerStateToEnewState().entrySet()) {
			List<Long> fiber = cnewByEnew.get(entry.getValue());
			if (fiber == null) {
				fiber = new ArrayList<Long>();
				cnewByEnew.put(entry.getValue(), fiber);
			}
			fiber.add(entry.getKey());
		}
		for (List<Long> fiber : cnewByEnew.values()) Collections.sort(fiber);
		Map<Long, List<Long>> mappingByEnew =
				new LinkedHashMap<Long, List<Long>>();
		for (Map.Entry<Long, Long> entry
				: seed.getMappingProductToNew().entrySet()) {
			List<Long> fiber = mappingByEnew.get(entry.getValue());
			if (fiber == null) {
				fiber = new ArrayList<Long>();
				mappingByEnew.put(entry.getValue(), fiber);
			}
			fiber.add(entry.getKey());
		}
		for (List<Long> fiber : mappingByEnew.values()) Collections.sort(fiber);
		Map<String, Long> closedByCoordinates =
				new LinkedHashMap<String, Long>();
		for (Map.Entry<Long, M9CompositionProvenance.SourceCoordinates> entry
				: closedLoop.getCoordinates().getProductStateCoordinates().entrySet()) {
			M9CompositionProvenance.SourceCoordinates coordinates = entry.getValue();
			String key = coordinates.getFirstSourceState() + "\u0000"
					+ coordinates.getSecondSourceState();
			if (closedByCoordinates.put(key, entry.getKey()) != null) {
				throw new IllegalArgumentException(
						"CLnew coordinates are not injective.");
			}
		}

		Map<Long, List<CompletionCoordinates>> rows =
				new LinkedHashMap<Long, List<CompletionCoordinates>>();
		long retainedRowCount = 0L;
		for (Long safetyState : new TreeSet<Long>(
				traditional.getSafetyStateToUpdatingState().keySet())) {
			List<Integer> safetyTuple = safetyProjection
					.getComponentStateTuples().get(safetyState);
			if (safetyTuple == null || safetyTuple.size() != 2
					|| safetyTuple.get(1).longValue() != complete) {
				continue;
			}
			Long updatingState = traditional.getSafetyStateToUpdatingState()
					.get(safetyState);
			Long mappingState = traditional.getUpdatingProvenance()
					.getUpdatingStateToMappingState().get(updatingState);
			Long enewState = mappingState == null ? null
					: seed.getMappingProductToNew().get(mappingState);
			if (mappingState == null || enewState == null) {
				throw new IllegalArgumentException(
						"Lifecycle-complete safety state has no atomic Enew load target.");
			}
			if (!updatingState.equals(traditional.getUpdatingProvenance()
					.getMappingStateToUpdatingState().get(mappingState))) {
				throw new IllegalArgumentException(
						"Updating/mapping completion provenance is not invertible.");
			}
			List<Long> mappingFiber = mappingByEnew.get(enewState);
			if (mappingFiber == null || mappingFiber.size() != 1
					|| !mappingState.equals(mappingFiber.get(0))) {
				throw new IllegalArgumentException(
						"Lifecycle-complete Enew state has no unique mapping-product origin.");
			}
			List<Long> cnewFiber = cnewByEnew.get(enewState);
			if (cnewFiber == null || cnewFiber.isEmpty()) {
				throw new IllegalArgumentException(
						"Lifecycle-complete Enew state has no Cnew strategy state.");
			}
			Long prunedState = traditional.getSafetyStateToPrunedState()
					.get(safetyState);
			Long metaState = prunedState == null ? null
					: traditional.getMetaStateToUpdatingState().containsKey(prunedState)
							? prunedState : null;
			if (prunedState == null || metaState == null
					|| !updatingState.equals(traditional
							.getMetaStateToUpdatingState().get(metaState))) {
				throw new IllegalArgumentException(
						"Completion safety/pruned/meta provenance chain differs.");
			}
			List<CompletionCoordinates> candidates =
					new ArrayList<CompletionCoordinates>();
			for (Long cnewState : cnewFiber) {
				if (retainedRowCount >= MAX_HANDOFF_ROWS) {
					throw new IllegalArgumentException(
							"Completion handoff candidate relation exceeds the registered receipt profile.");
				}
				M9EndpointStrategySnapshot.StateCoordinates strategyCoordinates =
						strategy.getPlainStateCoordinates().get(cnewState);
				Long solverEnvironmentState = strategyCoordinates == null ? null
						: strategy.getPlantComposition()
								.getFirstComponentSourceStates().get(
										Long.valueOf(strategyCoordinates.getPlantState()));
				Long projectedEnew = solverEnvironmentState == null ? null
						: strategy.getEnvironmentPrefix()
								.getExtendedStateToPrefixState().get(
										solverEnvironmentState);
				if (strategyCoordinates == null
						|| !enewState.equals(projectedEnew)
						|| strategyCoordinates.getEnewState()
								!= enewState.longValue()) {
					throw new IllegalArgumentException(
							"Cnew plant coordinate differs from its solver-environment/Enew provenance.");
				}
				Long closedState = closedByCoordinates.get(
						enewState + "\u0000" + cnewState);
				Long closedFirst = closedState == null ? null
						: closedLoop.getClosedLoopAuthority()
								.getFirstComponentSourceStates().get(closedState);
				if (closedState == null || !enewState.equals(closedFirst)) {
					throw new IllegalArgumentException(
							"Lifecycle-complete Enew/Cnew coordinates have no unique CLnew state.");
				}
				candidates.add(new CompletionCoordinates(
						prunedState.longValue(), metaState.longValue(),
						updatingState.longValue(), mappingState.longValue(),
						enewState.longValue(), solverEnvironmentState.longValue(),
						cnewState.longValue(), closedState.longValue()));
				retainedRowCount++;
			}
			rows.put(safetyState, Collections.unmodifiableList(candidates));
		}
		if (rows.isEmpty()) {
			throw new IllegalArgumentException(
					"Traditional safety authority has no loadable lifecycle-complete state.");
		}
		return new M9TraditionalCompletionHandoffSnapshot(complete, rows);
	}

	private M9TraditionalCompletionHandoffSnapshot(
			long lifecycleCompleteCoordinate,
			Map<Long, List<CompletionCoordinates>> completionStates) {
		this.lifecycleCompleteCoordinate = lifecycleCompleteCoordinate;
		Map<Long, List<CompletionCoordinates>> copy =
				new LinkedHashMap<Long, List<CompletionCoordinates>>();
		for (Map.Entry<Long, List<CompletionCoordinates>> entry
				: completionStates.entrySet()) {
			copy.put(entry.getKey(), Collections.unmodifiableList(
					new ArrayList<CompletionCoordinates>(entry.getValue())));
		}
		this.completionStates = Collections.unmodifiableMap(copy);
	}

	private static long requireLifecycleCompleteCoordinate(
			CompactStateCanonicalSnapshot monitor,
			List<String> lifecycleActions) {
		if (monitor == null || lifecycleActions == null
				|| !lifecycleActions.equals(Arrays.asList(
						UpdateConstants.STOP_OLD_SPEC,
						UpdateConstants.RECONFIGURE,
						UpdateConstants.START_NEW_SPEC))
				|| monitor.getStateCount() <= 0
				|| monitor.getInitialState() < 0
				|| monitor.getInitialState() >= monitor.getStateCount()) {
			throw new IllegalArgumentException(
					"Lifecycle monitor authority is not the registered ordered profile.");
		}
		Map<Integer, Map<String, Integer>> targets =
				new LinkedHashMap<Integer, Map<String, Integer>>();
		for (CompactStateCanonicalSnapshot.Transition edge
				: monitor.getTransitions()) {
			if ("tau".equals(edge.getActionLabel())) {
				throw new IllegalArgumentException(
						"Lifecycle monitor contains an enabled tau transition.");
			}
			Map<String, Integer> row = targets.get(
					Integer.valueOf(edge.getFromState()));
			if (row == null) {
				row = new LinkedHashMap<String, Integer>();
				targets.put(Integer.valueOf(edge.getFromState()), row);
			}
			if (row.put(edge.getActionLabel(),
					Integer.valueOf(edge.getTargetState())) != null) {
				throw new IllegalArgumentException(
						"Lifecycle monitor transition is nondeterministic.");
			}
		}
		List<Integer> phases = new ArrayList<Integer>();
		int state = monitor.getInitialState();
		Set<Integer> visited = new LinkedHashSet<Integer>();
		visited.add(Integer.valueOf(state));
		phases.add(Integer.valueOf(state));
		for (int phase = 0; phase < lifecycleActions.size(); phase++) {
			String action = lifecycleActions.get(phase);
			Integer target = targetFor(targets, state, action);
			if (target == null || target.intValue() < 0
					|| !visited.add(target)) {
				throw new IllegalArgumentException(
						"Lifecycle monitor has no unique ordered completion path.");
			}
			state = target.intValue();
			phases.add(target);
		}
		if (visited.size() != monitor.getStateCount()) {
			throw new IllegalArgumentException(
					"Lifecycle completion path does not exhaust the monitor state domain.");
		}
		Set<String> lifecycle = new LinkedHashSet<String>(lifecycleActions);
		for (int phase = 0; phase < phases.size(); phase++) {
			int source = phases.get(phase).intValue();
			for (int actionIndex = 0;
					actionIndex < lifecycleActions.size(); actionIndex++) {
				Integer target = targetFor(
						targets, source, lifecycleActions.get(actionIndex));
				int expected = actionIndex == phase
						&& phase < lifecycleActions.size()
						? phases.get(phase + 1).intValue() : -1;
				if (target == null || target.intValue() != expected) {
					throw new IllegalArgumentException(
							"Lifecycle monitor accepts an out-of-order or repeated update.");
				}
			}
			for (CompactStateCanonicalSnapshot.Action action
					: monitor.getActions()) {
				if (lifecycle.contains(action.getLabel())
						|| "tau".equals(action.getLabel())) {
					continue;
				}
				Integer target = targetFor(targets, source, action.getLabel());
				if (target == null || target.intValue() != source) {
					throw new IllegalArgumentException(
							"Lifecycle monitor does not stutter on ordinary actions.");
				}
			}
		}
		return state;
	}

	private static Integer targetFor(
			Map<Integer, Map<String, Integer>> targets,
			int state,
			String action) {
		Map<String, Integer> row = targets.get(Integer.valueOf(state));
		return row == null ? null : row.get(action);
	}

	public long getLifecycleCompleteCoordinate() {
		return lifecycleCompleteCoordinate;
	}

	public Map<Long, List<CompletionCoordinates>> getCompletionStates() {
		return completionStates;
	}

	public long getSyntheticTransitionCount() { return 0L; }

	public static final class CompletionCoordinates {
		private final long prunedState;
		private final long metaState;
		private final long updatingState;
		private final long mappingState;
		private final long enewState;
		private final long solverEnvironmentState;
		private final long cnewState;
		private final long closedLoopState;

		private CompletionCoordinates(
				long prunedState,
				long metaState,
				long updatingState,
				long mappingState,
				long enewState,
				long solverEnvironmentState,
				long cnewState,
				long closedLoopState) {
			this.prunedState = prunedState;
			this.metaState = metaState;
			this.updatingState = updatingState;
			this.mappingState = mappingState;
			this.enewState = enewState;
			this.solverEnvironmentState = solverEnvironmentState;
			this.cnewState = cnewState;
			this.closedLoopState = closedLoopState;
		}

		public long getPrunedState() { return prunedState; }
		public long getMetaState() { return metaState; }
		public long getUpdatingState() { return updatingState; }
		public long getMappingState() { return mappingState; }
		public long getEnewState() { return enewState; }
		public long getSolverEnvironmentState() {
			return solverEnvironmentState;
		}
		public long getCnewState() { return cnewState; }
		public long getClosedLoopState() { return closedLoopState; }
	}
}
