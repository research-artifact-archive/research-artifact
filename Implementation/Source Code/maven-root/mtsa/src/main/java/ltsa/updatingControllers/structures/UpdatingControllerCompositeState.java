package ltsa.updatingControllers.structures;

import MTSSynthesis.ar.dc.uba.model.condition.Fluent;
import MTSSynthesis.controller.model.ControllerGoal;
import MTSTools.ac.ic.doc.mtstools.model.MTS;
import ltsa.control.ControllerGoalDefinition;
import ltsa.lts.CompactState;
import ltsa.lts.CompositeState;
import ltsa.lts.Symbol;
import ltsa.lts.util.MTSUtils;
import ltsa.updatingControllers.otf.LinkedOtfDucsController;
import ltsa.updatingControllers.otf.MtsaRevisedOtfDucsAdapter;
import ltsa.updatingControllers.otf.OtfDucsResult;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.Set;
import java.util.Vector;
import java.util.List;
import java.util.Map;

public class UpdatingControllerCompositeState extends CompositeState {

	private CompositeState oldController;
	private CompositeState mapping;
	private ControllerGoalDefinition updateSafetyGoals;
	private ControllerGoal<String> updateGRGoal;
	private Set<String> controllableActions;
	private MTS<Long, String> updateEnvironment;

	//OTF用
	private CompositeState newController;
	private boolean isOTF;
	private boolean fineGrained;
	private boolean revisedOnTheFly;
	private boolean revisedOtfDucsExecuted;
	private boolean revisedOtfDucsWinning;
	private OtfDucsResult<?, String, ?> revisedOtfDucsResult;
	private LinkedOtfDucsController<?, ?, ?, ?> revisedLinkedController;
	private MtsaRevisedOtfDucsAdapter.Outcome revisedOtfDucsOutcome;
	private UpdateProtocolSpec updateProtocolSpec;
	private Set<Integer> loadableNewEndpointStateIndices;
	// ★追加: Mappingを構成するLTSのリスト (OTF探索で利用)
    private Vector<CompactState> mappingComponents;
	// ★追加: Safety & Transition Constraints
    private Vector<CompactState> oldSafetyLTSs;
    private Vector<CompactState> newSafetyLTSs;
    // // ★変更: LTS(Vector<CompactState>) ではなく、定義シンボル(List<Symbol>)として保持
	// //transitionReqは単体のLTSにするとバグることが判明したので，Formulaのまま渡してOTFもFormulaのままチェックする
    // private List<Symbol> transitionGoals;

	// ★変更: List<Symbol> から Vector<CompactState> へ変更
	private Vector<CompactState> transitionRequirements;

	// ★追加: New Environmentを構成するコンポーネント群
    private Vector<CompactState> newEnvironmentComponents;

	private List<Map<Integer, Integer>> mappingMapEnvToNewEnv;

	/*
	 * Immutable snapshots of the component-local state spaces and the direct
	 * transfer relation used by revised OTF-DUCS. These deliberately do not
	 * expose MappingEnvironment state IDs.
	 */
	private final Vector<CompactState> rawOldEnvironmentComponents;
	private final Vector<CompactState> rawNewEnvironmentComponents;
	private final List<Map<Integer, Set<Integer>>> rawTransferRelations;
	private final List<Boolean> transferRelationsWithActionSequences;

	// ▼▼▼ 追加: New Safety用のFluentを保持するフィールド ▼▼▼
    private Vector<CompactState> synthesisMachines;

	// ★追加: Safetyプロパティと構成要素(Monitor+Fluents)の対応マップ
    private Map<CompactState, List<CompactState>> safetyComponentsMap;
    
    // ★追加: Safetyプロパティの状態追跡マップ (Look-up Table)
    private Map<CompactState, Map<List<Integer>, Integer>> safetyStateMapping;

	public UpdatingControllerCompositeState(CompositeState oldController, CompositeState mapping,
											ControllerGoalDefinition safetyGoals, ControllerGoal<String> updateGRGoal, String name) {
		this(oldController, mapping, safetyGoals, updateGRGoal, name, false, null);
	}

	public UpdatingControllerCompositeState(CompositeState oldController, CompositeState mapping,
										ControllerGoalDefinition safetyGoals, ControllerGoal<String> updateGRGoal,
										String name, boolean fineGrained, UpdateProtocolSpec updateProtocolSpec) {
		this(oldController, mapping, safetyGoals, updateGRGoal, name,
				fineGrained, updateProtocolSpec,
				Collections.<CompactState>emptyList(),
				Collections.<Map<Integer, Integer>>emptyList(),
				Collections.<CompactState>emptyList(),
				Collections.<Boolean>emptyList());
	}

	public UpdatingControllerCompositeState(
			CompositeState oldController,
			CompositeState mapping,
			ControllerGoalDefinition safetyGoals,
			ControllerGoal<String> updateGRGoal,
			String name,
			boolean fineGrained,
			UpdateProtocolSpec updateProtocolSpec,
			List<CompactState> mappingComponents,
			List<Map<Integer, Integer>> mappingMapEnvToNewEnv,
			List<CompactState> rawNewEnvironmentComponents,
			List<Boolean> transferRelationsWithActionSequences) {
		super.setMachines(new Vector<CompactState>());
		validateTraditionalPostProjectionPayload(
				mappingComponents, mappingMapEnvToNewEnv,
				rawNewEnvironmentComponents,
				transferRelationsWithActionSequences);
		this.oldController = oldController;
		this.mapping = mapping;
		this.updateSafetyGoals = safetyGoals;
		this.updateGRGoal = updateGRGoal;
		this.controllableActions = this.updateGRGoal.getControllableActions();

		super.setCompositionType(Symbol.UPDATING_CONTROLLER);
		super.name = name;

		//明示的な初期化
		this.newController = null;
		this.isOTF = false;
		this.fineGrained = fineGrained;
		this.revisedOnTheFly = false;
		this.updateProtocolSpec = updateProtocolSpec;
		this.mappingComponents = deepCopyCompactStates(mappingComponents);
		this.mappingMapEnvToNewEnv = immutableIntegerMaps(
				mappingMapEnvToNewEnv);
		this.rawOldEnvironmentComponents = new Vector<>();
		this.rawNewEnvironmentComponents = deepCopyCompactStates(
				rawNewEnvironmentComponents);
		this.rawTransferRelations = Collections.emptyList();
		this.transferRelationsWithActionSequences = immutableBooleanList(
				transferRelationsWithActionSequences);
	}

	//OTF用
	public UpdatingControllerCompositeState(CompositeState oldController, CompositeState newController,
											Vector<CompactState> mappingComponents, Vector<CompactState> newEnvironmentComponents,
											List<Map<Integer, Integer>> mappingMapEnvToNewEnv,
											Vector<CompactState> oldSafetyLTSs, Vector<CompactState> newSafetyLTSs,
											// List<Symbol> transitionGoals,
											Vector<CompactState> transitionRequirements,
											Vector<CompactState> synthesisMachines, // Monitor + Fluents
											Map<CompactState, List<CompactState>> safetyComponentsMap,
											Map<CompactState, Map<List<Integer>, Integer>> safetyStateMapping,
											UpdateProtocolSpec updateProtocolSpec,
											Set<String> controllableActions,
											boolean isOTF, boolean fineGrained, String name) {
		this(oldController, newController, mappingComponents, newEnvironmentComponents,
				mappingMapEnvToNewEnv,
				new Vector<CompactState>(), new Vector<CompactState>(),
				Collections.<Map<Integer, Set<Integer>>>emptyList(),
				Collections.<Boolean>emptyList(),
				oldSafetyLTSs, newSafetyLTSs, transitionRequirements,
				synthesisMachines, safetyComponentsMap, safetyStateMapping,
				updateProtocolSpec, controllableActions, isOTF, fineGrained, name);
	}

	public UpdatingControllerCompositeState(CompositeState oldController, CompositeState newController,
											Vector<CompactState> mappingComponents, Vector<CompactState> newEnvironmentComponents,
											List<Map<Integer, Integer>> mappingMapEnvToNewEnv,
											Vector<CompactState> rawOldEnvironmentComponents,
											Vector<CompactState> rawNewEnvironmentComponents,
											List<Map<Integer, Set<Integer>>> rawTransferRelations,
											List<Boolean> transferRelationsWithActionSequences,
											Vector<CompactState> oldSafetyLTSs, Vector<CompactState> newSafetyLTSs,
											Vector<CompactState> transitionRequirements,
											Vector<CompactState> synthesisMachines,
											Map<CompactState, List<CompactState>> safetyComponentsMap,
											Map<CompactState, Map<List<Integer>, Integer>> safetyStateMapping,
											UpdateProtocolSpec updateProtocolSpec,
											Set<String> controllableActions,
											boolean isOTF, boolean fineGrained, String name) {
		super.setMachines(new Vector<CompactState>());
		validateRawTransferPayload(rawOldEnvironmentComponents,
				rawNewEnvironmentComponents, rawTransferRelations,
				transferRelationsWithActionSequences);
		this.oldController = oldController;
		// OTFモードではこれらはnullにしておく（またはダミー）
		this.mapping = null;
		this.updateSafetyGoals = null; 
        this.updateGRGoal = null;

		this.controllableActions = controllableActions;

		super.setCompositionType(Symbol.UPDATING_CONTROLLER);
		super.name = name;

		//追加フィールド
		this.newController = newController;
		this.isOTF = isOTF;
		this.fineGrained = fineGrained;
		this.revisedOnTheFly = false;
		this.updateProtocolSpec = updateProtocolSpec;
		this.mappingComponents = mappingComponents;
		this.newEnvironmentComponents = newEnvironmentComponents;
		this.mappingMapEnvToNewEnv = mappingMapEnvToNewEnv;
		this.rawOldEnvironmentComponents = deepCopyCompactStates(rawOldEnvironmentComponents);
		this.rawNewEnvironmentComponents = deepCopyCompactStates(rawNewEnvironmentComponents);
		this.rawTransferRelations = immutableTransferRelations(rawTransferRelations);
		this.transferRelationsWithActionSequences =
				immutableBooleanList(transferRelationsWithActionSequences);
		this.oldSafetyLTSs = oldSafetyLTSs;
        this.newSafetyLTSs = newSafetyLTSs;
        // this.transitionGoals = transitionGoals;
		// ★変更: CompactStateのリストとして保存
        this.transitionRequirements = transitionRequirements;

		// ▼▼▼ 追加: フィールドへの代入 ▼▼▼
        this.synthesisMachines = synthesisMachines;
		this.safetyComponentsMap = safetyComponentsMap;
		this.safetyStateMapping = safetyStateMapping;

		// //デバッグ用
		// ★修正: 可視化(Drawタブ)のために、全ての構成要素をmachinesリストにまとめる
        Vector<CompactState> allMachines = new Vector<>();
        if (mappingComponents != null) allMachines.addAll(mappingComponents);
		if (newEnvironmentComponents != null) allMachines.addAll(newEnvironmentComponents);
        if (oldSafetyLTSs != null) allMachines.addAll(oldSafetyLTSs);
        if (newSafetyLTSs != null) allMachines.addAll(newSafetyLTSs);

		// ★追加
        if (transitionRequirements != null) allMachines.addAll(transitionRequirements);

		if (synthesisMachines != null) allMachines.addAll(synthesisMachines);
        
        super.setMachines(allMachines);
	}

	private static void validateRawTransferPayload(
			List<CompactState> oldComponents,
			List<CompactState> newComponents,
			List<Map<Integer, Set<Integer>>> transferRelations,
			List<Boolean> actionSequenceMetadata) {
		int oldSize = oldComponents == null ? 0 : oldComponents.size();
		int newSize = newComponents == null ? 0 : newComponents.size();
		int relationSize = transferRelations == null ? 0 : transferRelations.size();
		int metadataSize = actionSequenceMetadata == null ? 0 : actionSequenceMetadata.size();
		if (oldSize != newSize || oldSize != relationSize || oldSize != metadataSize) {
			throw new IllegalArgumentException(
					"Raw OTF transfer payload must have one old component, new component, "
							+ "transfer relation, and action-sequence marker per mapping.");
		}
	}

	private static void validateTraditionalPostProjectionPayload(
			List<CompactState> mappingComponents,
			List<Map<Integer, Integer>> mappingStateToNewState,
			List<CompactState> newComponents,
			List<Boolean> actionSequenceMetadata) {
		int mappingSize = mappingComponents == null ? 0 : mappingComponents.size();
		int mapSize = mappingStateToNewState == null
				? 0 : mappingStateToNewState.size();
		int newSize = newComponents == null ? 0 : newComponents.size();
		int metadataSize = actionSequenceMetadata == null
				? 0 : actionSequenceMetadata.size();
		boolean noRelationalAuthority = mapSize == 0
				&& newSize == 0 && metadataSize == 0;
		if (!noRelationalAuthority
				&& (mappingSize == 0 || mappingSize != mapSize
						|| mappingSize != newSize
						|| mappingSize != metadataSize)) {
			throw new IllegalArgumentException(
					"Traditional post-projection authority must have one local map, "
							+ "new component, and action-sequence marker per mapping component.");
		}
	}

	private static Vector<CompactState> deepCopyCompactStates(
			List<CompactState> components) {
		Vector<CompactState> copy = new Vector<>();
		if (components == null) {
			return copy;
		}
		for (CompactState component : components) {
			copy.add(component == null ? null : component.myclone());
		}
		return copy;
	}

	private static List<Map<Integer, Set<Integer>>> immutableTransferRelations(
			List<Map<Integer, Set<Integer>>> transferRelations) {
		List<Map<Integer, Set<Integer>>> copy = copyTransferRelations(transferRelations);
		List<Map<Integer, Set<Integer>>> immutable = new ArrayList<>();
		for (Map<Integer, Set<Integer>> relation : copy) {
			Map<Integer, Set<Integer>> immutableRelation = new LinkedHashMap<>();
			for (Map.Entry<Integer, Set<Integer>> entry : relation.entrySet()) {
				immutableRelation.put(entry.getKey(),
						Collections.unmodifiableSet(new LinkedHashSet<>(entry.getValue())));
			}
			immutable.add(Collections.unmodifiableMap(immutableRelation));
		}
		return Collections.unmodifiableList(immutable);
	}

	private static List<Map<Integer, Integer>> immutableIntegerMaps(
			List<Map<Integer, Integer>> source) {
		if (source == null) return Collections.emptyList();
		List<Map<Integer, Integer>> result = new ArrayList<>();
		for (Map<Integer, Integer> row : source) {
			if (row == null) {
				throw new IllegalArgumentException(
						"Traditional post-projection local map is absent.");
			}
			result.add(Collections.unmodifiableMap(
					new LinkedHashMap<Integer, Integer>(row)));
		}
		return Collections.unmodifiableList(result);
	}

	private static List<Map<Integer, Set<Integer>>> copyTransferRelations(
			List<Map<Integer, Set<Integer>>> transferRelations) {
		List<Map<Integer, Set<Integer>>> copy = new ArrayList<>();
		if (transferRelations == null) {
			return copy;
		}
		for (Map<Integer, Set<Integer>> relation : transferRelations) {
			Map<Integer, Set<Integer>> relationCopy = new LinkedHashMap<>();
			if (relation != null) {
				for (Map.Entry<Integer, Set<Integer>> entry : relation.entrySet()) {
					Set<Integer> targets = entry.getValue() == null
							? Collections.<Integer>emptySet()
							: entry.getValue();
					relationCopy.put(entry.getKey(), new LinkedHashSet<>(targets));
				}
			}
			copy.add(relationCopy);
		}
		return copy;
	}

	private static List<Boolean> immutableBooleanList(List<Boolean> values) {
		if (values == null) {
			return Collections.emptyList();
		}
		return Collections.unmodifiableList(new ArrayList<>(values));
	}

	public MTS<Long, String> getUpdateController() {
		return MTSUtils.getMTSComposition(this);
	}

	public MTS<Long, String> getOldController() {
		return MTSUtils.getMTSComposition(oldController);
	}

	public MTS<Long, String> getMapping() {
		if (mapping == null) return null;
		return MTSUtils.getMTSComposition(mapping);
	}

	public Set<String> getControllableActions() {
		return controllableActions;
	}

	public void setControllableActions(Set<String> actions) {
		this.controllableActions = actions == null
				? Collections.<String>emptySet()
				: Collections.unmodifiableSet(new LinkedHashSet<>(actions));
	}

	public ControllerGoalDefinition getUpdateSafetyGoals() {
		return updateSafetyGoals;
	}

	public ControllerGoal<String> getUpdateGRGoal() {
		return updateGRGoal;
	}

	public boolean isShowGRGameInDraw() {
		return Boolean.getBoolean("updating.controller.draw.grGame");
	}

	public void setUpdateEnvironment(MTS<Long, String> updateEnvironment) {
		this.updateEnvironment = updateEnvironment;
	}

	// ★追加: newControllerの取得
    public MTS<Long, String> getNewController()
	{
        if (newController == null) return null;
        return MTSUtils.getMTSComposition(newController);
    }

	// OTF: Mapping Components
    public Vector<CompactState> getMappingComponents() {
        return mappingComponents;
    }

	public Vector<CompactState> getOldSafetyLTSs() { return oldSafetyLTSs; }
    public Vector<CompactState> getNewSafetyLTSs() { return newSafetyLTSs; }
    // public List<Symbol> getTransitionGoals() { return transitionGoals; }
	// ★変更: ゲッターの戻り値も変更
    public Vector<CompactState> getTransitionRequirements() {
        return transitionRequirements;
    }

	// ★追加: OTFフラグの確認
	public boolean isOTF()
	{
        return isOTF;
	}

	public boolean isRevisedOnTheFly() {
		return revisedOnTheFly;
	}

	public void setRevisedOnTheFly(boolean revisedOnTheFly) {
		this.revisedOnTheFly = revisedOnTheFly;
		if (revisedOnTheFly) {
			this.isOTF = true;
		}
	}

	public boolean wasRevisedOtfDucsExecuted() {
		return revisedOtfDucsExecuted;
	}

	public boolean isRevisedOtfDucsWinning() {
		return revisedOtfDucsExecuted && revisedOtfDucsWinning;
	}

	public OtfDucsResult<?, String, ?> getRevisedOtfDucsResult() {
		return revisedOtfDucsResult;
	}

	public LinkedOtfDucsController<?, ?, ?, ?> getRevisedLinkedController() {
		return revisedLinkedController;
	}

	public MtsaRevisedOtfDucsAdapter.Outcome getRevisedOtfDucsOutcome() {
		return revisedOtfDucsOutcome;
	}

	public void recordRevisedOtfDucsResult(
			OtfDucsResult<?, String, ?> result,
			LinkedOtfDucsController<?, ?, ?, ?> linkedController) {
		this.revisedOtfDucsResult = result;
		this.revisedLinkedController = linkedController;
		this.revisedOtfDucsExecuted = true;
		this.revisedOtfDucsWinning = result != null && result.isWinning();
	}

	public void recordRevisedOtfDucsOutcome(
			MtsaRevisedOtfDucsAdapter.Outcome outcome) {
		this.revisedOtfDucsOutcome = outcome;
	}

	public boolean isFineGrained()
	{
		return fineGrained;
	}

	public UpdateProtocolSpec getUpdateProtocolSpec()
	{
		return updateProtocolSpec;
	}

	public void setLoadableNewEndpointStateIndices(Set<Integer> indices) {
		if (indices == null || indices.isEmpty()) {
			throw new IllegalArgumentException(
					"loadable new endpoint state indices must be nonempty");
		}
		LinkedHashSet<Integer> copy = new LinkedHashSet<>();
		for (Integer index : indices) {
			if (index == null || index.intValue() < 0) {
				throw new IllegalArgumentException(
						"loadable new endpoint state indices must be nonnegative");
			}
			copy.add(index);
		}
		this.loadableNewEndpointStateIndices =
				Collections.unmodifiableSet(copy);
	}

	public boolean hasLoadableNewEndpointStateIndices() {
		return loadableNewEndpointStateIndices != null;
	}

	public Set<Integer> getLoadableNewEndpointStateIndices() {
		return loadableNewEndpointStateIndices == null
				? Collections.<Integer>emptySet()
				: loadableNewEndpointStateIndices;
	}

	public void setNewEnvironmentComponents(Vector<CompactState> components)
	{
        this.newEnvironmentComponents = components;
    }

    public List<CompactState> getNewEnvironmentComponents()
	{
        return newEnvironmentComponents;
    }

	public List<Map<Integer, Integer>> getMappingMapEnvToNewEnv()
	{
		return mappingMapEnvToNewEnv;
	}

	public Vector<CompactState> getM9TraditionalMappingComponents() {
		return deepCopyCompactStates(mappingComponents);
	}

	public List<Map<Integer, Integer>>
			getM9TraditionalMappingStateToNewState() {
		return immutableIntegerMaps(mappingMapEnvToNewEnv);
	}

	public Vector<CompactState> getM9TraditionalNewEnvironmentComponents() {
		return deepCopyCompactStates(rawNewEnvironmentComponents);
	}

	public List<Boolean> getM9TraditionalActionSequenceMarkers() {
		return new ArrayList<Boolean>(transferRelationsWithActionSequences);
	}

	public Vector<CompactState> getRawOldEnvironmentComponents() {
		return deepCopyCompactStates(rawOldEnvironmentComponents);
	}

	public Vector<CompactState> getRawNewEnvironmentComponents() {
		return deepCopyCompactStates(rawNewEnvironmentComponents);
	}

	public List<Map<Integer, Set<Integer>>> getRawTransferRelations() {
		return copyTransferRelations(rawTransferRelations);
	}

	public List<Boolean> getTransferRelationsWithActionSequences() {
		return new ArrayList<>(transferRelationsWithActionSequences);
	}

	public boolean hasTransferRelationActionSequences() {
		for (Boolean hasSequence : transferRelationsWithActionSequences) {
			if (Boolean.TRUE.equals(hasSequence)) {
				return true;
			}
		}
		return false;
	}

	// ▼▼▼ 追加: ゲッター ▼▼▼
    public Vector<CompactState> getSynthesisMachines() {
        return synthesisMachines;
    }

	// ★追加: 安全性コンポーネントマップのゲッター
    public Map<CompactState, List<CompactState>> getSafetyComponentsMap() {
        return safetyComponentsMap;
    }

    // ★追加: 状態追跡マップのゲッター
    public Map<CompactState, Map<List<Integer>, Integer>> getSafetyStateMapping() {
        return safetyStateMapping;
    }

	@Override
	public UpdatingControllerCompositeState clone() {
		UpdatingControllerCompositeState clone;

		// ★修正: OTFモードかどうかでコンストラクタを使い分ける
        if (this.isOTF) {
            clone = new UpdatingControllerCompositeState(oldController, newController, mappingComponents, newEnvironmentComponents,
														mappingMapEnvToNewEnv,
														rawOldEnvironmentComponents,
														rawNewEnvironmentComponents,
														rawTransferRelations,
														transferRelationsWithActionSequences,
														oldSafetyLTSs, newSafetyLTSs,
														// transitionGoals,
														transitionRequirements,
														synthesisMachines,
														safetyComponentsMap,
														safetyStateMapping,
														updateProtocolSpec,
														controllableActions,
														isOTF, fineGrained, name);
		} else {
			clone = new UpdatingControllerCompositeState(
					oldController, mapping, updateSafetyGoals,
					updateGRGoal, name, fineGrained, updateProtocolSpec,
					mappingComponents, mappingMapEnvToNewEnv,
					rawNewEnvironmentComponents,
					transferRelationsWithActionSequences);
		}
		clone.setCompositionType(getCompositionType());
		clone.makeAbstract = makeAbstract;
		clone.makeClousure = makeClousure;
		clone.makeCompose = makeCompose;
		clone.makeDeterministic = makeDeterministic;
		clone.makeMinimal = makeMinimal;
		clone.makeControlStack = makeControlStack;
		clone.makeOptimistic = makeOptimistic;
		clone.makePessimistic = makePessimistic;
		clone.makeController = makeController;
		clone.setMakeComponent(isMakeComponent());
		clone.setComponentAlphabet(getComponentAlphabet());
		clone.goal = goal;
		clone.controlStackEnvironments = controlStackEnvironments;
		clone.controlStackSpecificTier = controlStackSpecificTier;
		clone.isProbabilistic = isProbabilistic;
		clone.revisedOnTheFly = revisedOnTheFly;
		clone.revisedOtfDucsExecuted = revisedOtfDucsExecuted;
		clone.revisedOtfDucsWinning = revisedOtfDucsWinning;
		clone.revisedOtfDucsResult = revisedOtfDucsResult;
		clone.revisedLinkedController = revisedLinkedController;
		clone.revisedOtfDucsOutcome = revisedOtfDucsOutcome;
		if (loadableNewEndpointStateIndices != null) {
			clone.setLoadableNewEndpointStateIndices(
					loadableNewEndpointStateIndices);
		}
		return clone;
	}

}
