package ltsa.updatingControllers.synthesis;

import MTSSynthesis.ar.dc.uba.model.condition.Fluent;
import MTSSynthesis.ar.dc.uba.model.condition.FluentUtils;
import MTSSynthesis.ar.dc.uba.model.condition.Formula;
import MTSSynthesis.ar.dc.uba.model.language.SingleSymbol;
import MTSSynthesis.controller.util.FluentStateValuation;
import MTSTools.ac.ic.doc.commons.relations.Pair;
import MTSTools.ac.ic.doc.mtstools.model.MTS;
import MTSTools.ac.ic.doc.mtstools.model.impl.MTSImpl;
import ltsa.ac.ic.doc.mtstools.util.fsp.AutomataToMTSConverter;
import ltsa.ac.ic.doc.mtstools.util.fsp.MTSToAutomataConverter;
import ltsa.lts.CompactState;
import ltsa.lts.CompositeState;
import ltsa.lts.LTSOutput;
import ltsa.ui.StandardOutput;
import ltsa.updatingControllers.UpdateConstants;
import ltsa.updatingControllers.DUCHeartbeat;
import ltsa.updatingControllers.UpdatingControllerEvaluationRecorder;
import ltsa.updatingControllers.export.M9TraditionalSafetySemanticsSnapshot;

import java.util.*;
import java.util.logging.Level;
import java.util.logging.Logger;

/**
 * Created by lnahabedian on 06/07/16.
 */
public class UpdatingControllerSafetySynthesizer {


    public static MTS<Long, String> synthesizeSafety(MTS<Long, String> metaEnvironment, Set<Fluent> goalFluents, List<Formula> safetyFormulas, Set<String> controllableActions, LTSOutput output) {
        return synthesizeSafety(
                metaEnvironment,
                goalFluents,
                safetyFormulas,
                controllableActions,
                Arrays.asList(UpdateConstants.STOP_OLD_SPEC, UpdateConstants.START_NEW_SPEC),
                output);
    }

    public static MTS<Long, String> synthesizeSafety(
            MTS<Long, String> metaEnvironment,
            Set<Fluent> goalFluents,
            List<Formula> safetyFormulas,
            Set<String> controllableActions,
            Collection<String> dontDoTwiceActions,
            LTSOutput output) {
		return synthesizeSafetyWithProvenance(
				metaEnvironment,
				goalFluents,
				safetyFormulas,
				controllableActions,
				dontDoTwiceActions,
				output).getSafetyEnvironment();
	}

	public static SafetySynthesisResult synthesizeSafetyWithProvenance(
			MTS<Long, String> metaEnvironment,
			Set<Fluent> goalFluents,
			List<Formula> safetyFormulas,
			Set<String> controllableActions,
			Collection<String> dontDoTwiceActions,
			LTSOutput output) {
		List<M9TraditionalSafetySemanticsSnapshot.FormulaInput> inputs =
				new ArrayList<M9TraditionalSafetySemanticsSnapshot.FormulaInput>();
		for (int index = 0; index < safetyFormulas.size(); index++) {
			String identifier = String.format(
					Locale.ROOT, "m9-synthetic-formula-%06d", index);
			inputs.add(M9TraditionalSafetySemanticsSnapshot.FormulaInput.of(
					identifier,
					identifier,
					M9TraditionalSafetySemanticsSnapshot.FormulaKind.SYNTHETIC,
					safetyFormulas.get(index)));
		}
		return synthesizeSafetyWithProvenance(
				metaEnvironment,
				goalFluents,
				safetyFormulas,
				inputs,
				controllableActions,
				dontDoTwiceActions,
				output);
	}

	public static SafetySynthesisResult synthesizeSafetyWithProvenance(
			MTS<Long, String> metaEnvironment,
			Set<Fluent> goalFluents,
			List<Formula> safetyFormulas,
			List<M9TraditionalSafetySemanticsSnapshot.FormulaInput> formulaInputs,
			Set<String> controllableActions,
			Collection<String> dontDoTwiceActions,
			LTSOutput output) {
		if (safetyFormulas == null || formulaInputs == null
				|| safetyFormulas.size() != formulaInputs.size()) {
			throw new IllegalArgumentException(
					"Safety formulas and their authority inputs must have the same census.");
		}
		for (int index = 0; index < safetyFormulas.size(); index++) {
			M9TraditionalSafetySemanticsSnapshot.FormulaInput input =
					formulaInputs.get(index);
			if (input == null
					|| !input.isFormulaIdentity(safetyFormulas.get(index))) {
				throw new IllegalArgumentException(
						"Safety formula authority order or identity differs from evaluation input.");
			}
		}

        // /*
        // ▼▼▼ 追加: 追跡しているFluentの名前を一覧表示 ▼▼▼
        // System.out.println("=========================================");
        // System.out.println(" DEBUG: Tracking Fluents for New Safety");
        // System.out.println("=========================================");
        // if (goalFluents.isEmpty()) {
        //     System.out.println(" (No fluents are being tracked)");
        // } else {
        //     for (Fluent fl : goalFluents) {
        //         System.out.println(" Fluent Name: " + fl.getName());
        //         // 必要であれば初期値やアクションも表示可能です
        //         System.out.println("   Initial Value: " + fl.getInitialValue());
        //         System.out.println("   Initiating Actions: " + fl.getInitiatingActions());
        //         System.out.println("   Terminating Actions: " + fl.getTerminatingActions());
        //     }
        // }
        // System.out.println("=========================================");
        // ▲▲▲ 追加ここまで ▲▲▲
        // */

        long makeOldActionsStart = System.currentTimeMillis();
        UpdatingControllerEvaluationRecorder.beginFailureTimer(
                "Traditional DUC safetyEnv 構築時間内訳",
                "hotSwapIn 前の旧 action を uncontrollable 化する時間");
        Map<String, String> derivedOldActionToSourceAction =
                makeOldActionsUncontrollable(
                        controllableActions, metaEnvironment);
        UpdatingControllerEvaluationRecorder.endFailureTimer(
                "Traditional DUC safetyEnv 構築時間内訳",
                "hotSwapIn 前の旧 action を uncontrollable 化する時間");
        UpdatingControllerEvaluationRecorder.recordTime(
                "Traditional DUC safetyEnv 構築時間内訳",
                "hotSwapIn 前の旧 action を uncontrollable 化する時間",
                System.currentTimeMillis() - makeOldActionsStart);
        UpdatingControllerEvaluationRecorder.recordMemoryCheckpoint("Traditional 旧 action uncontrollable 化後");

        long valuationStart = System.currentTimeMillis();
        UpdatingControllerEvaluationRecorder.beginFailureTimer(
                "Traditional DUC safetyEnv 構築時間内訳",
                "Fluent valuation 構築時間");
        FluentStateValuation<Long> fluentStateValuation = buildValuations(
                metaEnvironment,
                goalFluents,
                derivedOldActionToSourceAction);
        UpdatingControllerEvaluationRecorder.endFailureTimer(
                "Traditional DUC safetyEnv 構築時間内訳",
                "Fluent valuation 構築時間");
        UpdatingControllerEvaluationRecorder.recordTime(
                "Traditional DUC safetyEnv 構築時間内訳",
                "Fluent valuation 構築時間",
                System.currentTimeMillis() - valuationStart);
        UpdatingControllerEvaluationRecorder.recordMemoryCheckpoint("Traditional Fluent valuation 構築後");

		M9TraditionalSafetySemanticsSnapshot safetySemantics =
				M9TraditionalSafetySemanticsSnapshot.capture(
						metaEnvironment,
						goalFluents,
						formulaInputs,
						fluentStateValuation,
						derivedOldActionToSourceAction,
						dontDoTwiceActions);

        long valuateSafetyStart = System.currentTimeMillis();
        UpdatingControllerEvaluationRecorder.beginFailureTimer(
                "Traditional DUC safetyEnv 構築時間内訳",
                "Safety formula 評価と違反状態 pruning 時間");
		SafetyPruningResult pruning = valuateSafetyWithProvenance(
				safetyFormulas, metaEnvironment, fluentStateValuation);
		if (!pruning.prunedStates.equals(safetySemantics.getUnsafeStates())) {
			throw new IllegalArgumentException(
					"Immutable formula truth differs from the legacy pruning census.");
		}
        MTS<Long, String> safetyEnv = pruning.environment;
        UpdatingControllerEvaluationRecorder.endFailureTimer(
                "Traditional DUC safetyEnv 構築時間内訳",
                "Safety formula 評価と違反状態 pruning 時間");
        UpdatingControllerEvaluationRecorder.recordTime(
                "Traditional DUC safetyEnv 構築時間内訳",
                "Safety formula 評価と違反状態 pruning 時間",
                System.currentTimeMillis() - valuateSafetyStart);

        // ▼▼▼ 評価実験用: [3] 枝刈り(Pruning)直後の状態数・遷移数 ▼▼▼
        long prunedCountStart = 0;
        int prunedStates = 0;
        int prunedTrans = 0;
        long prunedCountTime = 0;
        if (UpdatingControllerEvaluationRecorder.isEnabled()) {
            prunedCountStart = System.currentTimeMillis();
            prunedStates = safetyEnv.getStates().size();
            prunedTrans = countTransitions(safetyEnv); // ※このクラス内にも countTransitions メソッドをコピペしてください
            prunedCountTime = System.currentTimeMillis() - prunedCountStart;
        }
        TraditionalDUCDebugLogger.logStage(
                output,
                "[3. Pruned] Safety Environment before DontDoTwice",
                safetyEnv);
        UpdatingControllerEvaluationRecorder.recordStateSpace(
                "Traditional DUC 最大状態数と遷移数",
                "[3. Pruned] Safety Env (Before DontDoTwice)",
                prunedStates,
                prunedTrans,
                prunedCountTime,
                "Meta から safety formula に違反する状態を除去した環境。DontDoTwice 制約はまだ未適用。");
        UpdatePhaseEvaluator.recordMtsUpdatePhaseStateSpace(
                UpdatePhaseEvaluator.SECTION_TRADITIONAL,
                "[3. Pruned] Safety Env (Before DontDoTwice)",
                safetyEnv);
        UpdatePhaseEvaluator.recordMtsUpdateEventTransitionCounts(
                UpdatePhaseEvaluator.SECTION_TRADITIONAL_UPDATE_EVENTS,
                "[3. Pruned] Safety Env (Before DontDoTwice)",
                safetyEnv);
        UpdatePhaseEvaluator.recordMtsUpdatePhaseTransitionAnalysis(
                UpdatePhaseEvaluator.SECTION_TRADITIONAL_PHASE_DETAILS,
                UpdatePhaseEvaluator.SECTION_TRADITIONAL_PHASE_FLOW,
                UpdatePhaseEvaluator.SECTION_TRADITIONAL_COMPLETION_PATH,
                UpdatePhaseEvaluator.SECTION_TRADITIONAL_NORMAL_ACTIONS,
                UpdatePhaseEvaluator.SECTION_TRADITIONAL_NEXT_UPDATE_EVENT_DISTANCE,
                UpdatePhaseEvaluator.SECTION_TRADITIONAL_PROGRESS_FREE_CYCLES,
                UpdatePhaseEvaluator.SECTION_TRADITIONAL_ENABLED_UPDATE_EVENTS,
                UpdatePhaseEvaluator.SECTION_TRADITIONAL_UPDATE_ORDER_PATTERNS,
                UpdatePhaseEvaluator.SECTION_TRADITIONAL_NORMAL_RUN_LENGTH,
                "[3. Pruned] Safety Env (Before DontDoTwice)",
                safetyEnv,
                controllableActions);
        UpdatingControllerEvaluationRecorder.recordMemoryCheckpoint("Traditional Safety pruning 後");
        // ▲▲▲ 追加ここまで ▲▲▲

        long dontDoTwiceStart = System.currentTimeMillis();
        UpdatingControllerEvaluationRecorder.beginFailureTimer(
                "Traditional DUC safetyEnv 構築時間内訳",
                "DontDoTwice goal 合成時間");
        MTS<Long, String> result = getDontDoTwiceGoals(safetyEnv, dontDoTwiceActions);
        UpdatingControllerEvaluationRecorder.endFailureTimer(
                "Traditional DUC safetyEnv 構築時間内訳",
                "DontDoTwice goal 合成時間");
        UpdatingControllerEvaluationRecorder.recordTime(
                "Traditional DUC safetyEnv 構築時間内訳",
                "DontDoTwice goal 合成時間",
                System.currentTimeMillis() - dontDoTwiceStart);
        UpdatingControllerEvaluationRecorder.recordMemoryCheckpoint("Traditional DontDoTwice 合成後");

		return new SafetySynthesisResult(
				safetyEnv,
				result,
				pruning.prunedStates,
				dontDoTwiceActions,
				safetySemantics);

    }

    static FluentStateValuation<Long> buildValuations(
            MTS<Long, String> metaEnv, Set<Fluent> fluents) {
		return buildValuations(
				metaEnv,
				fluents,
				Collections.<String, String>emptyMap());
	}

    static FluentStateValuation<Long> buildValuations(
            MTS<Long, String> metaEnv,
			Set<Fluent> fluents,
			Map<String, String> derivedOldActionToSourceAction) {
        if (metaEnv == null || fluents == null) {
            throw new IllegalArgumentException(
                    "Traditional valuation requires a graph and fluent catalog.");
        }
        List<Fluent> orderedFluents = new ArrayList<Fluent>(fluents);
        Collections.sort(orderedFluents, new Comparator<Fluent>() {
            @Override
            public int compare(Fluent left, Fluent right) {
                String leftName = left == null ? null : left.getName();
                String rightName = right == null ? null : right.getName();
                if (leftName == null || rightName == null) {
                    throw new IllegalArgumentException(
                            "Traditional fluent name is absent.");
                }
                return leftName.compareTo(rightName);
            }
        });
        Set<String> names = new LinkedHashSet<String>();
        for (Fluent fluent : orderedFluents) {
            if (fluent == null || fluent.getName() == null
                    || fluent.getName().isEmpty()
                    || fluent.getInitiatingActions() == null
                    || fluent.getTerminatingActions() == null
                    || !names.add(fluent.getName())) {
                throw new IllegalArgumentException(
                        "Traditional fluent catalog is absent or duplicated.");
            }
            Set<Object> overlap = new HashSet<Object>(
                    fluent.getInitiatingActions());
            overlap.retainAll(fluent.getTerminatingActions());
            if (!overlap.isEmpty()) {
                throw new IllegalArgumentException(
                        "A traditional fluent action cannot both initiate and terminate: "
                                + fluent.getName());
            }
        }

        FluentStateValuation<Long> fsv =
                new FluentStateValuation<Long>(metaEnv.getStates());
        DUCHeartbeat.beginPhase("TRADITIONAL_SAFETY_VALUATION");
        DUCHeartbeat.setCounter("metaStates", metaEnv.getStates().size());
        DUCHeartbeat.setCounter("fluents", orderedFluents.size());

        Long initial = metaEnv.getInitialState();
        Set<Fluent> initialValue = new LinkedHashSet<Fluent>();
        for (Fluent fluent : orderedFluents) {
            if (fluent.getInitialValue()) initialValue.add(fluent);
        }
        Map<Long, Set<Fluent>> pathValuations =
                new LinkedHashMap<Long, Set<Fluent>>();
        pathValuations.put(initial, initialValue);
        for (Fluent fluent : initialValue) {
            fsv.addHoldingFluent(initial, fluent);
        }
        Queue<Long> toVisit = new ArrayDeque<Long>();
        toVisit.add(initial);
        long visitedStates = 0L;
        long visitedTransitions = 0L;
        while (!toVisit.isEmpty()) {
            Long from = toVisit.remove();
            Set<Fluent> fromValue = pathValuations.get(from);
            visitedStates++;
            if ((visitedStates & 0x3fffL) == 0L) {
                DUCHeartbeat.setCounter("valuationStates", visitedStates);
                DUCHeartbeat.setCounter("valuationQueue", toVisit.size());
            }
            for (Pair<String, Long> transition : metaEnv.getTransitions(
                    from, MTS.TransitionType.REQUIRED)) {
                visitedTransitions++;
                if ((visitedTransitions & 0x3fffL) == 0L) {
                    DUCHeartbeat.setCounter(
                            "valuationTransitions", visitedTransitions);
                }
                String graphAction = transition.getFirst();
                if (graphAction == null) {
                    throw new IllegalArgumentException(
                            "Traditional valuation action is absent.");
                }
                String valuationAction =
						derivedOldActionToSourceAction.containsKey(graphAction)
								? derivedOldActionToSourceAction.get(graphAction)
								: graphAction;
                SingleSymbol symbol = new SingleSymbol(valuationAction);
                Set<Fluent> nextValue = new LinkedHashSet<Fluent>();
                for (Fluent fluent : orderedFluents) {
                    boolean holds = fromValue.contains(fluent);
                    if (fluent.getTerminatingActions().contains(symbol)) {
                        holds = false;
                    }
                    if (fluent.getInitiatingActions().contains(symbol)) {
                        holds = true;
                    }
                    if (holds) nextValue.add(fluent);
                }
                Long target = transition.getSecond();
                Set<Fluent> existing = pathValuations.get(target);
                if (existing == null) {
                    pathValuations.put(target, nextValue);
                    for (Fluent fluent : nextValue) {
                        fsv.addHoldingFluent(target, fluent);
                    }
                    toVisit.add(target);
                } else if (!existing.equals(nextValue)) {
                    throw new IllegalArgumentException(
                            "Traditional fluent valuation is path-dependent at state "
                                    + target + ".");
                }
            }
        }
        DUCHeartbeat.setCounter("valuationStates", visitedStates);
        DUCHeartbeat.setCounter("valuationTransitions", visitedTransitions);
        DUCHeartbeat.setCounter("valuationQueue", toVisit.size());
        return fsv;
    }

	private static SafetyPruningResult valuateSafetyWithProvenance(
			List<Formula> safetyFormulas,
			MTS<Long, String> metaEnvironment,
			FluentStateValuation<Long> fluentStateValuation) {

        HashSet<Long> toBuild = new HashSet<Long>();
        long formulaEvalStart = System.currentTimeMillis();
        UpdatingControllerEvaluationRecorder.beginFailureTimer(
                "Traditional DUC safetyEnv 構築時間内訳",
                "Safety formula を全状態で評価する時間");
        formulaToStateSet(toBuild, metaEnvironment.getStates(), safetyFormulas,	fluentStateValuation);
        UpdatingControllerEvaluationRecorder.endFailureTimer(
                "Traditional DUC safetyEnv 構築時間内訳",
                "Safety formula を全状態で評価する時間");
        UpdatingControllerEvaluationRecorder.recordTime(
                "Traditional DUC safetyEnv 構築時間内訳",
                "Safety formula を全状態で評価する時間",
                System.currentTimeMillis() - formulaEvalStart);

        long applySafetyStart = System.currentTimeMillis();
        UpdatingControllerEvaluationRecorder.beginFailureTimer(
                "Traditional DUC safetyEnv 構築時間内訳",
                "Safety 違反状態を除去した MTS 構築時間");
        MTS<Long, String> safetyEnv = applySafetyInEnvironment(metaEnvironment, toBuild);
        UpdatingControllerEvaluationRecorder.endFailureTimer(
                "Traditional DUC safetyEnv 構築時間内訳",
                "Safety 違反状態を除去した MTS 構築時間");
        UpdatingControllerEvaluationRecorder.recordTime(
                "Traditional DUC safetyEnv 構築時間内訳",
                "Safety 違反状態を除去した MTS 構築時間",
                System.currentTimeMillis() - applySafetyStart);
		return new SafetyPruningResult(safetyEnv, toBuild);
    }

	public static final class SafetySynthesisResult {
		private final MTS<Long, String> prunedEnvironment;
		private final MTS<Long, String> safetyEnvironment;
		private final Set<Long> prunedStates;
		private final List<String> dontDoTwiceActions;
		private final M9TraditionalSafetySemanticsSnapshot safetySemantics;

		private SafetySynthesisResult(
				MTS<Long, String> prunedEnvironment,
				MTS<Long, String> safetyEnvironment,
				Collection<Long> prunedStates,
				Collection<String> dontDoTwiceActions,
				M9TraditionalSafetySemanticsSnapshot safetySemantics) {
			if (safetySemantics == null) {
				throw new IllegalArgumentException(
						"Traditional safety semantics authority is absent.");
			}
			this.prunedEnvironment = prunedEnvironment;
			this.safetyEnvironment = safetyEnvironment;
			List<Long> sorted = new ArrayList<Long>(prunedStates);
			Collections.sort(sorted);
			this.prunedStates = Collections.unmodifiableSet(
					new LinkedHashSet<Long>(sorted));
			this.dontDoTwiceActions = Collections.unmodifiableList(
					new ArrayList<String>(dontDoTwiceActions));
			this.safetySemantics = safetySemantics;
		}

		public MTS<Long, String> getPrunedEnvironment() {
			return prunedEnvironment;
		}

		public MTS<Long, String> getSafetyEnvironment() {
			return safetyEnvironment;
		}

		public Set<Long> getPrunedStates() {
			return prunedStates;
		}

		public List<String> getDontDoTwiceActions() {
			return dontDoTwiceActions;
		}

		public M9TraditionalSafetySemanticsSnapshot getSafetySemantics() {
			return safetySemantics;
		}
	}

	private static final class SafetyPruningResult {
		private final MTS<Long, String> environment;
		private final Set<Long> prunedStates;

		private SafetyPruningResult(
				MTS<Long, String> environment,
				Collection<Long> prunedStates) {
			this.environment = environment;
			this.prunedStates = new LinkedHashSet<Long>(prunedStates);
		}
	}

    private static void formulaToStateSet(Set<Long> toBuild, Set<Long> allStates, List<Formula> formulas, FluentStateValuation<Long> valuation) {

        DUCHeartbeat.beginPhase("TRADITIONAL_SAFETY_FORMULA_EVAL");
        DUCHeartbeat.setCounter("metaStates", allStates.size());
        DUCHeartbeat.setCounter("safetyFormulas", formulas.size());
        long evaluations = 0L;
        int formulaIndex = 0;
        for (Formula formula : formulas) {
            formulaIndex++;
            DUCHeartbeat.setCounter("formulaIndex", formulaIndex);
            for (Long state : allStates) {
                formulaToStateSet(toBuild, formula, state, valuation);
                evaluations++;
                if ((evaluations & 0x3fffL) == 0L) {
                    DUCHeartbeat.setCounter("formulaEvaluations", evaluations);
                    DUCHeartbeat.setCounter("formulaSatisfiedStates", toBuild.size());
                }
            }
            if (toBuild.isEmpty()) {
                Logger.getAnonymousLogger().log(Level.WARNING, "No state satisfies formula: " + formula);
            }
        }
        DUCHeartbeat.setCounter("formulaEvaluations", evaluations);
        DUCHeartbeat.setCounter("formulaSatisfiedStates", toBuild.size());
    }

    private static void formulaToStateSet(Set<Long> toBuild, Formula formula, Long state, FluentStateValuation<Long> valuation) {

        valuation.setActualState(state);
        if (formula.evaluate(valuation)) {
            toBuild.add(state);
        }
    }

    private static MTS<Long, String> applySafetyInEnvironment(MTS<Long, String> metaEnvironment, HashSet<Long> toBuild) {

        DUCHeartbeat.beginPhase("TRADITIONAL_SAFETY_APPLY_PRUNING");
        DUCHeartbeat.setCounter("metaStates", metaEnvironment.getStates().size());
        DUCHeartbeat.setCounter("prunedStateCandidates", toBuild.size());
        MTS<Long, String> result = new MTSImpl<Long, String>(metaEnvironment.getInitialState());
        long checkedStates = 0L;
        long copiedTransitions = 0L;
        long prunedStates = 0L;

        for (Long state : metaEnvironment.getStates()) {
            checkedStates++;
            result.addState(state);
            if (!toBuild.contains(state)){
                for (Pair<String, Long> transition : metaEnvironment.getTransitions(state, MTS.TransitionType.REQUIRED)) {
                    copiedTransitions++;

                    result.addState(transition.getSecond());
                    result.addAction(transition.getFirst());

                    result.addRequired(state, transition.getFirst(), transition.getSecond());
                }
            } else {
                prunedStates++;
            }
            if ((checkedStates & 0x3fffL) == 0L) {
                DUCHeartbeat.setCounter("checkedStates", checkedStates);
                DUCHeartbeat.setCounter("copiedTransitions", copiedTransitions);
                DUCHeartbeat.setCounter("prunedStates", prunedStates);
            }

        }
        result.removeUnreachableStates();
        DUCHeartbeat.setCounter("checkedStates", checkedStates);
        DUCHeartbeat.setCounter("copiedTransitions", copiedTransitions);
        DUCHeartbeat.setCounter("prunedStates", prunedStates);
        DUCHeartbeat.setCounter("createdSafetyStates", result.getStates().size());
        return result;

    }

    private static Map<String, String> makeOldActionsUncontrollable(
			Set<String> controllableActions,
			MTS<Long, String> env) {

		List<String> orderedControllable =
				new ArrayList<String>(controllableActions);
		Collections.sort(orderedControllable);
		Map<String, String> derivedOldActionToSourceAction =
				new LinkedHashMap<String, String>();
		for (String action : orderedControllable) {
			if (action == null) {
				throw new IllegalArgumentException(
						"Controllable action authority is absent.");
			}
			if (UpdatingControllersUtils.isNotUpdateAction(action)) {
				if (action.endsWith(UpdateConstants.OLD_LABEL)) {
					throw new IllegalArgumentException(
							"A source controllable action cannot use the reserved .old suffix: "
									+ action);
				}
				String derived = action + UpdateConstants.OLD_LABEL;
				if (env.getActions().contains(derived)) {
					throw new IllegalArgumentException(
							"A source action collides with a derived .old action: "
									+ derived);
				}
				derivedOldActionToSourceAction.put(derived, action);
			}
		}

        Set<Fluent> fluentSet = new HashSet<Fluent>();
        fluentSet.add(UpdatingControllersUtils.beginFluent);

        FluentStateValuation<Long> beginUpdateValuation = FluentUtils.getInstance().buildValuation(env, fluentSet);

        for (Long state : env.getStates()) {
            if (! beginUpdateValuation.isTrue(state, UpdatingControllersUtils.beginFluent)) {

                List<Pair<String, Long>> toBeChanged = new ArrayList<Pair<String, Long>>();
                for (Pair<String, Long> action_toState : env.getTransitions(state, MTS.TransitionType.REQUIRED)) {
                    if (controllableActions.contains(action_toState.getFirst())) {
                        toBeChanged.add(action_toState);
                    }
                }
                for (Pair<String, Long> action_toState : toBeChanged) {
                    String action = action_toState.getFirst();
                    Long toState = action_toState.getSecond();
                    env.removeRequired(state, action, toState);
                    String actionWithOld = action + UpdateConstants.OLD_LABEL;
                    env.addAction(actionWithOld);
                    env.addRequired(state, actionWithOld, toState);
                }
            }
        }
        // add all .old accions to MTS so as to avoid problems while parallel composition
        // I think is useless but I want to keep the structure consistent
        for (String action : controllableActions) {
            if (UpdatingControllersUtils.isNotUpdateAction(action)) {
                env.addAction(action + UpdateConstants.OLD_LABEL);
            }
        }
		return Collections.unmodifiableMap(
				new LinkedHashMap<String, String>(
						derivedOldActionToSourceAction));
    }

    public static MTS<Long, String> getDontDoTwiceGoals(MTS<Long, String> SafetyEnv) {
        return getDontDoTwiceGoals(
                SafetyEnv,
                Arrays.asList(UpdateConstants.STOP_OLD_SPEC, UpdateConstants.START_NEW_SPEC));
    }

    public static MTS<Long, String> getDontDoTwiceGoals(
            MTS<Long, String> SafetyEnv,
            Collection<String> dontDoTwiceActions) {
		if (SafetyEnv == null || dontDoTwiceActions == null
				|| dontDoTwiceActions.isEmpty()) {
			throw new IllegalArgumentException(
					"Dont-do-twice composition requires explicit actions.");
		}
		Set<String> unique = new LinkedHashSet<String>();
		for (String action : dontDoTwiceActions) {
			if (action == null || action.isEmpty() || !unique.add(action)
					|| !SafetyEnv.getActions().contains(action)) {
				throw new IllegalArgumentException(
						"Dont-do-twice action is absent, empty, or duplicated: " + action);
			}
		}

        Vector<CompactState> machinesToCompose = new Vector<CompactState>();
        machinesToCompose.add(MTSToAutomataConverter.getInstance().convert(SafetyEnv, "safetyEnv", true));

        List<String> ordered = new ArrayList<String>(dontDoTwiceActions);
        List<String> registeredLifecycle = Arrays.asList(
                UpdateConstants.STOP_OLD_SPEC,
                UpdateConstants.RECONFIGURE,
                UpdateConstants.START_NEW_SPEC);
        if (ordered.equals(registeredLifecycle)) {
            machinesToCompose.add(orderedLifecycleModel(SafetyEnv.getActions()));
        } else {
            // Legacy profiles retain their original independent at-most-once
            // monitors.  The registered M9 profile is the exact three-action
            // sequence above and therefore receives a true precedence monitor.
            for (String action : dontDoTwiceActions) {
                machinesToCompose.add(dontDoTwiceModel(
                        action, SafetyEnv.getActions()));
            }
        }

        CompositeState c = new CompositeState(machinesToCompose);
        c.compose(new StandardOutput());
        return AutomataToMTSConverter.getInstance().convert(c.composition);
    }

    private static CompactState dontDoTwiceModel(String dontDoTwiceAction, Set<String> alphabet) {

        // states
        Long initialState = new Long(0);
        Long secondState = new Long(1);
        Long errorState = new Long(-1);

        // add states to model
        MTS<Long, String> model = new MTSImpl<Long, String>(initialState);
        model.addState(secondState);
        model.addState(errorState);

        // when I do the action twice I must go to ERROR
        model.addAction(dontDoTwiceAction);
        model.addRequired(initialState,dontDoTwiceAction,secondState);
        model.addRequired(secondState,dontDoTwiceAction,errorState);

        // In state 0 and 1 we can signaled any action
        for(String action : alphabet){

            if (! action.equals(dontDoTwiceAction)){
                model.addAction(action);
                model.addRequired(initialState,action,initialState);
                model.addRequired(secondState,action,secondState);
            }
        }
        return MTSToAutomataConverter.getInstance().convert(model,"dontDo"+dontDoTwiceAction.toUpperCase(), true);
    }

    private static CompactState orderedLifecycleModel(Set<String> alphabet) {
        Long beforeStop = Long.valueOf(0L);
        Long beforeReconfigure = Long.valueOf(1L);
        Long beforeStart = Long.valueOf(2L);
        Long complete = Long.valueOf(3L);
        Long error = Long.valueOf(-1L);
        List<Long> phases = Arrays.asList(
                beforeStop, beforeReconfigure, beforeStart, complete);
        MTS<Long, String> model = new MTSImpl<Long, String>(beforeStop);
        for (Long phase : phases) model.addState(phase);
        model.addState(error);
        for (String action : alphabet) {
            model.addAction(action);
            if (UpdateConstants.STOP_OLD_SPEC.equals(action)) {
                model.addRequired(beforeStop, action, beforeReconfigure);
                model.addRequired(beforeReconfigure, action, error);
                model.addRequired(beforeStart, action, error);
                model.addRequired(complete, action, error);
            } else if (UpdateConstants.RECONFIGURE.equals(action)) {
                model.addRequired(beforeStop, action, error);
                model.addRequired(beforeReconfigure, action, beforeStart);
                model.addRequired(beforeStart, action, error);
                model.addRequired(complete, action, error);
            } else if (UpdateConstants.START_NEW_SPEC.equals(action)) {
                model.addRequired(beforeStop, action, error);
                model.addRequired(beforeReconfigure, action, error);
                model.addRequired(beforeStart, action, complete);
                model.addRequired(complete, action, error);
            } else {
                for (Long phase : phases) {
                    model.addRequired(phase, action, phase);
                }
            }
        }
        return MTSToAutomataConverter.getInstance().convert(
                model, "m9OrderedLifecycle", true);
    }

    // ▼▼▼ 評価実験用: MTSの遷移数をカウントするヘルパーメソッド ▼▼▼
    private static int countTransitions(MTS<Long, String> mts) {
        int count = 0;
        for (Long state : mts.getStates()) {
            // REQUIRED と MAYBE の両方の遷移をカウントする（通常はREQUIREDのみですが念のため両方）
            count += mts.getTransitions(state, MTSTools.ac.ic.doc.mtstools.model.MTS.TransitionType.REQUIRED).size();
            count += mts.getTransitions(state, MTSTools.ac.ic.doc.mtstools.model.MTS.TransitionType.MAYBE).size();
        }
        return count;
    }
    // ▲▲▲ 追加ここまで ▲▲▲

}
