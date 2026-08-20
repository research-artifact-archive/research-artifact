package ltsa.lts;

import ltsa.updatingControllers.structures.UpdateProtocolSpec;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.Vector;
import java.util.Objects;

/**
 * Solver-free, immutable structural AST boundary for the registered UAV
 * endpoint route.  This descriptor is never source-completeness authority by
 * itself: the T1 worker must bind the exact raw source bytes and compare a
 * separately implemented complete reconstruction before accepting it.
 * The only production target is {@value #OFFICIAL_TARGET}; resolution performs
 * exactly one {@link LTSCompiler#compile()} and never calls composition,
 * dispatch, synthesis, or fixed-point code.
 */
public final class M9UpdatingControllerAst {
	public static final String OFFICIAL_TARGET = "UPDATE_CONTROLLER";

	public enum MappingProfile { LEGACY_MAPPING, RELATIONAL_TRIPLE }
	public enum NewControllerMode {
		EXPLICIT_SOURCE_CONTROLLER,
		SYNTHESIS_REQUIRED
	}

	private static final Set<String> KNOWN_CLAUSES;
	static {
		Set<String> clauses = new LinkedHashSet<String>();
		Collections.addAll(clauses,
				"oldController", "mapping", "oldEnvironment",
				"newEnvironment", "mapRelation", "oldGoal", "newGoal",
				"transition", "nonblocking", "on_the_fly",
				"revised_on_the_fly", "fine_grained",
				"selective_fine_grained", "newController", "precedence",
				"loadable_new_states");
		KNOWN_CLAUSES = Collections.unmodifiableSet(clauses);
	}

	private final List<String> aliasPath;
	private final List<Boolean> aliasMinimalFlags;
	private final String definitionName;
	private final MappingProfile mappingProfile;
	private final NewControllerMode newControllerMode;
	private final M9UpdatingEndpointAst oldEndpoint;
	private final M9UpdatingEndpointAst newEndpoint;
	private final String legacyMappingReference;
	private final List<String> mapRelationReferences;
	private final List<String> transitionGoalReferences;
	private final boolean nonblocking;
	private final boolean legacyOnTheFly;
	private final boolean revisedOnTheFly;
	private final boolean fineGrained;
	private final boolean selectiveFineGrained;
	private final List<PrecedenceEdgeAst> precedence;
	private final boolean loadableStatesSpecified;
	private final Set<Integer> loadableNewStateIndices;
	private final Map<String, Integer> clauseOccurrences;

	public static M9UpdatingControllerAst parseOfficial(
			LTSInput input,
			LTSOutput output,
			String currentDirectory) {
		if (input == null || output == null || currentDirectory == null
				|| currentDirectory.isEmpty()) {
			throw new IllegalArgumentException(
					"M9 parser input, output, and current directory are required.");
		}
		synchronized (LTSCompiler.m9ParseLock()) {
			LTSCompiler compiler = new LTSCompiler(input, output, currentDirectory);
			compiler.compile();
			return resolveForSyntheticTest(compiler, OFFICIAL_TARGET);
		}
	}

	static M9UpdatingControllerAst resolveForSyntheticTest(
			LTSCompiler parsedCompiler,
			String target) {
		if (parsedCompiler == null || !OFFICIAL_TARGET.equals(target)) {
			throw new IllegalArgumentException(
					"Only the registered UPDATE_CONTROLLER target may be resolved.");
		}
		return resolve(
				parsedCompiler.m9CompositesSnapshot(),
				parsedCompiler.m9ProcessesSnapshot(),
				parsedCompiler.m9RelationsSnapshot(),
				parsedCompiler.m9GoalSnapshots(),
				target);
	}

	private static M9UpdatingControllerAst resolve(
			Map<String, CompositionExpression> registry,
			Map<String, ProcessSpec> processes,
			Map<String, RelationDefinition> relations,
			Map<String, M9ControllerGoalAst> goalSnapshots,
			String target) {
		for (Map.Entry<String, ProcessSpec> entry : processes.entrySet()) {
			if (entry.getValue() == null || entry.getValue().imported()) {
				throw new IllegalArgumentException(
						"Registered M9 parse forbids imported or absent process bytes: "
								+ entry.getKey());
			}
		}
		List<String> path = new ArrayList<String>();
		List<Boolean> minimalFlags = new ArrayList<Boolean>();
		Set<String> visited = new LinkedHashSet<String>();
		String currentName = target;
		UpdatingControllersDefinition definition;
		while (true) {
			if (!visited.add(currentName)) {
				throw new IllegalArgumentException(
						"UPDATE_CONTROLLER alias graph contains a cycle.");
			}
			CompositionExpression expression = registry.get(currentName);
			if (expression == null) {
				throw new IllegalArgumentException(
						"Registered UPDATE_CONTROLLER target or alias is absent: "
								+ currentName);
			}
			requireNamed(expression, currentName);
			if (processes.containsKey(currentName)) {
				throw new IllegalArgumentException(
						"UPDATE_CONTROLLER alias collides with a process definition.");
			}
			path.add(currentName);
			if (expression.getClass() == UpdatingControllersDefinition.class) {
				definition = (UpdatingControllersDefinition) expression;
				break;
			}
			if (expression.getClass() != CompositionExpression.class) {
				throw new IllegalArgumentException(
						"UPDATE_CONTROLLER alias has an unsupported AST type.");
			}
			validateTransparentAlias(expression);
			minimalFlags.add(Boolean.valueOf(expression.makeMinimal));
			ProcessRef reference = soleReference(expression.body);
			if (reference.forceCompilation || !reference.passBackClone
					|| reference.actualParams != null) {
				throw new IllegalArgumentException(
						"UPDATE_CONTROLLER alias reference is executable or parameterized.");
			}
			currentName = symbolName(reference.name, "alias target");
		}

		return fromDefinition(
				definition,
				path,
				minimalFlags,
				registry,
				processes,
				relations,
				goalSnapshots);
	}

	private static M9UpdatingControllerAst fromDefinition(
			UpdatingControllersDefinition definition,
			List<String> path,
			List<Boolean> minimalFlags,
			Map<String, CompositionExpression> registry,
			Map<String, ProcessSpec> processes,
			Map<String, RelationDefinition> relations,
			Map<String, M9ControllerGoalAst> goalSnapshots) {
		Map<String, Integer> counts = definition.m9ClauseOccurrences();
		if (!KNOWN_CLAUSES.containsAll(counts.keySet())) {
			throw new IllegalArgumentException(
					"Updating-controller definition contains an unknown M9 clause.");
		}
		for (String clause : KNOWN_CLAUSES) {
			int count = count(counts, clause);
			if (count < 0 || (count > 1 && !"transition".equals(clause))) {
				throw new IllegalArgumentException(
						"Updating-controller clause occurs more than once: " + clause);
			}
		}
		requireOnce(counts, "oldController");
		requireOnce(counts, "oldGoal");
		requireOnce(counts, "newGoal");
		requireOnce(counts, "newEnvironment");

		int mappingCount = count(counts, "mapping");
		int oldEnvironmentCount = count(counts, "oldEnvironment");
		int relationCount = count(counts, "mapRelation");
		MappingProfile profile;
		if (mappingCount == 1 && oldEnvironmentCount == 0 && relationCount == 0) {
			profile = MappingProfile.LEGACY_MAPPING;
		} else if (mappingCount == 0 && oldEnvironmentCount == 1
				&& relationCount == 1) {
			profile = MappingProfile.RELATIONAL_TRIPLE;
		} else {
			throw new IllegalArgumentException(
					"Updating-controller mapping clauses are partial or mixed.");
		}

		boolean legacyOtf = count(counts, "on_the_fly") == 1;
		boolean revised = count(counts, "revised_on_the_fly") == 1;
		boolean fine = count(counts, "fine_grained") == 1;
		boolean selective = count(counts, "selective_fine_grained") == 1;
		if (legacyOtf && revised) {
			throw new IllegalArgumentException(
					"Legacy and revised on-the-fly modes are both present.");
		}
		if (fine && selective || revised && selective) {
			throw new IllegalArgumentException(
					"Fine-grained mode flags conflict.");
		}
		if (definition.isRevisedOnTheFly() != revised
				|| definition.isPlainFineGrainedForM9() != fine
				|| definition.isSelectiveFineGrained() != selective
				|| definition.isOTF() != (legacyOtf || revised)) {
			throw new IllegalArgumentException(
					"Parsed updating-controller mode flags disagree with clause presence.");
		}
		if (definition.isNonblocking()
				!= (count(counts, "nonblocking") == 1)) {
			throw new IllegalArgumentException(
					"Nonblocking value differs from its parsed clause presence.");
		}
		if (profile == MappingProfile.LEGACY_MAPPING
				&& (fine || selective || count(counts, "precedence") != 0
				|| count(counts, "loadable_new_states") != 0)) {
			throw new IllegalArgumentException(
					"Legacy mapping profile cannot carry fine-grained-only clauses.");
		}
		if ((count(counts, "precedence") != 0
				|| count(counts, "loadable_new_states") != 0)
				&& (!revised || !fine)) {
			throw new IllegalArgumentException(
					"Precedence/loadable clauses require revised plain fine-grained mode.");
		}

		String oldController = symbolName(
				definition.getOldController(), "old controller");
		requireComposite(registry, oldController, "old controller");
		boolean newControllerSpecified = count(counts, "newController") == 1;
		if (definition.hasExplicitNewController() != newControllerSpecified) {
			throw new IllegalArgumentException(
					"New-controller presence flag differs from its parsed clause.");
		}
		String newController = newControllerSpecified
				? symbolName(definition.getNewController(), "new controller") : null;
		if (newControllerSpecified) {
			if (!revised) {
				throw new IllegalArgumentException(
						"An explicit new controller requires revised-on-the-fly mode.");
			}
			requireComposite(registry, newController, "new controller");
		}

		List<String> oldEnvironment = symbolNames(
				definition.oldEnvironmentForM9(), "old environment");
		List<String> newEnvironment = symbolNames(
				definition.newEnvironmentForM9(), "new environment");
		List<String> mapRelations = symbolNames(
				definition.mapRelationsForM9(), "map relation");
		if (newEnvironment.isEmpty()) {
			throw new IllegalArgumentException("New endpoint environment is empty.");
		}
		for (String reference : newEnvironment) {
			requireProcess(processes, reference, "new environment");
		}
		if (profile == MappingProfile.RELATIONAL_TRIPLE) {
			if (oldEnvironment.size() != newEnvironment.size()
					|| oldEnvironment.size() != mapRelations.size()
					|| oldEnvironment.isEmpty()) {
				throw new IllegalArgumentException(
						"Relational endpoint lists have unequal or empty censuses.");
			}
			for (String reference : oldEnvironment) {
				requireProcess(processes, reference, "old environment");
			}
			for (String reference : mapRelations) {
				if (!relations.containsKey(reference)) {
					throw new IllegalArgumentException(
							"Map relation is not defined: " + reference);
				}
			}
		} else if (!oldEnvironment.isEmpty() || !mapRelations.isEmpty()) {
			throw new IllegalArgumentException(
					"Legacy mapping profile leaked relational endpoint lists.");
		}

		String mapping = profile == MappingProfile.LEGACY_MAPPING
				? symbolName(definition.getMapping(), "mapping") : null;
		if (mapping != null) requireComposite(registry, mapping, "mapping");

		String oldGoal = symbolName(definition.getOldGoal(), "old goal");
		String newGoal = symbolName(definition.getNewGoal(), "new goal");
		M9ControllerGoalAst oldGoalAst = goalSnapshots.get(oldGoal);
		M9ControllerGoalAst newGoalAst = goalSnapshots.get(newGoal);
		if (oldGoalAst == null || newGoalAst == null) {
			throw new IllegalArgumentException(
					"Endpoint goal is absent from the compiler-owned M9 snapshot.");
		}

		List<String> transitionGoals = symbolNames(
				definition.getTransitionGoals(), "transition goal");
		if (transitionGoals.size() != count(counts, "transition")
				|| new LinkedHashSet<String>(transitionGoals).size()
				!= transitionGoals.size()) {
			throw new IllegalArgumentException(
					"Transition-goal clause census is inconsistent or duplicated.");
		}

		List<PrecedenceEdgeAst> precedence = capturePrecedence(
				definition.getUpdatePrecedenceEdges(),
				count(counts, "precedence") == 1);
		boolean loadableSpecified = count(counts, "loadable_new_states") == 1;
		if (definition.hasLoadableNewEndpointStateIndices() != loadableSpecified) {
			throw new IllegalArgumentException(
					"Loadable-state presence flag differs from its parsed clause.");
		}

		M9UpdatingEndpointAst oldEndpoint = new M9UpdatingEndpointAst(
				true, oldController,
				profile == MappingProfile.RELATIONAL_TRIPLE, oldEnvironment,
				true, oldGoal, oldGoalAst);
		M9UpdatingEndpointAst newEndpoint = new M9UpdatingEndpointAst(
				newControllerSpecified, newController,
				true, newEnvironment,
				true, newGoal, newGoalAst);

		return new M9UpdatingControllerAst(
				path, minimalFlags, definition.getName().getName(), profile,
				newControllerSpecified
						? NewControllerMode.EXPLICIT_SOURCE_CONTROLLER
						: NewControllerMode.SYNTHESIS_REQUIRED,
				oldEndpoint, newEndpoint, mapping, mapRelations,
				transitionGoals, definition.isNonblocking(), legacyOtf, revised,
				fine, selective, precedence, loadableSpecified,
				definition.getLoadableNewEndpointStateIndices(), counts);
	}

	private M9UpdatingControllerAst(
			List<String> aliasPath,
			List<Boolean> aliasMinimalFlags,
		String definitionName,
			MappingProfile mappingProfile,
			NewControllerMode newControllerMode,
			M9UpdatingEndpointAst oldEndpoint,
			M9UpdatingEndpointAst newEndpoint,
			String legacyMappingReference,
			List<String> mapRelationReferences,
			List<String> transitionGoalReferences,
			boolean nonblocking,
			boolean legacyOnTheFly,
			boolean revisedOnTheFly,
			boolean fineGrained,
			boolean selectiveFineGrained,
			List<PrecedenceEdgeAst> precedence,
			boolean loadableStatesSpecified,
			Set<Integer> loadableNewStateIndices,
			Map<String, Integer> clauseOccurrences) {
		this.aliasPath = immutable(aliasPath);
		this.aliasMinimalFlags = Collections.unmodifiableList(
				new ArrayList<Boolean>(aliasMinimalFlags));
		this.definitionName = definitionName;
		this.mappingProfile = mappingProfile;
		this.newControllerMode = newControllerMode;
		this.oldEndpoint = oldEndpoint;
		this.newEndpoint = newEndpoint;
		this.legacyMappingReference = legacyMappingReference;
		this.mapRelationReferences = immutable(mapRelationReferences);
		this.transitionGoalReferences = immutable(transitionGoalReferences);
		this.nonblocking = nonblocking;
		this.legacyOnTheFly = legacyOnTheFly;
		this.revisedOnTheFly = revisedOnTheFly;
		this.fineGrained = fineGrained;
		this.selectiveFineGrained = selectiveFineGrained;
		this.precedence = Collections.unmodifiableList(
				new ArrayList<PrecedenceEdgeAst>(precedence));
		this.loadableStatesSpecified = loadableStatesSpecified;
		this.loadableNewStateIndices = Collections.unmodifiableSet(
				new LinkedHashSet<Integer>(loadableNewStateIndices));
		this.clauseOccurrences = Collections.unmodifiableMap(
				new LinkedHashMap<String, Integer>(clauseOccurrences));
	}

	private static void validateTransparentAlias(CompositionExpression alias) {
		if (alias.parameters == null || !alias.parameters.isEmpty()
				|| alias.init_constants == null || !alias.init_constants.isEmpty()
				|| alias.priorityIsLow == false || alias.priorityActions != null
				|| alias.alphaHidden != null || alias.exposeNotHide
				|| alias.makeDeterministic || alias.makeProperty || alias.makeCompose
				|| alias.makeOptimistic || alias.makePessimistic
				|| alias.makeClousure || alias.makeAbstract || alias.makeController
				|| alias.makeRTCController || alias.makeRTCAnalysisController
				|| alias.makeMDP || alias.isProbabilistic || alias.makeEnactment
				|| alias.checkCompatible || alias.isStarEnv || alias.isPlant
				|| alias.isControlledDet || alias.makeControlStack
				|| alias.isHeuristic || alias.isCompositional
				|| alias.isMonolithicDirector || alias.isPartialOrderReduction
				|| alias.goal != null || alias.controlStackEnvironments != null
				|| alias.enactmentControlled != null || alias.actionsToErrorSet != null
				|| alias.isMakeComponent() || alias.getComponentAlphabet() != null
				|| (alias.compositionType != -1
				&& alias.compositionType != Symbol.DOT)) {
			throw new IllegalArgumentException(
					"UPDATE_CONTROLLER alias contains a semantic modifier.");
		}
	}

	private static ProcessRef soleReference(CompositeBody body) {
		if (body == null || body.boolexpr != null || body.range != null
				|| body.prefix != null || body.accessSet != null
				|| body.relabelDefns != null || body.thenpart != null
				|| body.elsepart != null) {
			throw new IllegalArgumentException(
					"UPDATE_CONTROLLER alias body is not a transparent singleton.");
		}
		if (body.singleton != null && body.procRefs == null) return body.singleton;
		if (body.singleton == null && body.procRefs != null
				&& body.procRefs.size() == 1) {
			return soleReference(body.procRefs.get(0));
		}
		throw new IllegalArgumentException(
				"UPDATE_CONTROLLER alias body is not a sole reference.");
	}

	private static List<PrecedenceEdgeAst> capturePrecedence(
			List<UpdateProtocolSpec.PrecedenceEdge> source,
			boolean specified) {
		if (!specified && !source.isEmpty()) {
			throw new IllegalArgumentException(
					"Precedence presence differs from its parsed edge census.");
		}
		List<PrecedenceEdgeAst> result = new ArrayList<PrecedenceEdgeAst>();
		Set<String> keys = new LinkedHashSet<String>();
		Map<String, Set<String>> graph = new LinkedHashMap<String, Set<String>>();
		for (UpdateProtocolSpec.PrecedenceEdge edge : source) {
			String before = actionName(edge.before(), "precedence predecessor");
			String after = actionName(edge.after(), "precedence successor");
			if (before.equals(after) || !keys.add(before + "\u0000" + after)) {
				throw new IllegalArgumentException(
						"Precedence contains a self-edge or duplicate edge.");
			}
			Set<String> successors = graph.get(before);
			if (successors == null) {
				successors = new LinkedHashSet<String>();
				graph.put(before, successors);
			}
			successors.add(after);
			result.add(new PrecedenceEdgeAst(before, after));
		}
		for (String node : graph.keySet()) {
			if (hasCycle(node, graph, new LinkedHashSet<String>(),
					new LinkedHashSet<String>())) {
				throw new IllegalArgumentException("Precedence relation is cyclic.");
			}
		}
		return Collections.unmodifiableList(result);
	}

	private static boolean hasCycle(
			String node,
			Map<String, Set<String>> graph,
			Set<String> active,
			Set<String> complete) {
		if (complete.contains(node)) return false;
		if (!active.add(node)) return true;
		Set<String> successors = graph.get(node);
		if (successors != null) {
			for (String successor : successors) {
				if (hasCycle(successor, graph, active, complete)) return true;
			}
		}
		active.remove(node);
		complete.add(node);
		return false;
	}

	private static void requireNamed(
			CompositionExpression expression,
			String registryName) {
		if (expression.getName() == null
				|| expression.getName().kind != Symbol.UPPERIDENT
				|| !registryName.equals(expression.getName().getName())) {
			throw new IllegalArgumentException(
					"Composite registry key differs from its parsed AST name.");
		}
	}

	private static void requireComposite(
			Map<String, CompositionExpression> registry,
			String reference,
			String role) {
		if (!registry.containsKey(reference)) {
			throw new IllegalArgumentException(role + " is not a composite: "
					+ reference);
		}
	}

	private static void requireProcess(
			Map<String, ProcessSpec> processes,
			String reference,
			String role) {
		ProcessSpec process = processes.get(reference);
		if (process == null) {
			throw new IllegalArgumentException(role + " is not a process: "
					+ reference);
		}
		if (process.imported()) {
			throw new IllegalArgumentException(
					role + " uses an unpinned imported process: " + reference);
		}
	}

	private static List<String> symbolNames(
			List<Symbol> symbols,
			String role) {
		List<String> result = new ArrayList<String>();
		for (Symbol symbol : symbols) result.add(symbolName(symbol, role));
		return Collections.unmodifiableList(result);
	}

	private static String symbolName(Symbol symbol, String role) {
		if (symbol == null || symbol.kind != Symbol.UPPERIDENT) {
			throw new IllegalArgumentException(role + " is not an upper identifier.");
		}
		String name = symbol.getName();
		if (name == null || !name.matches("[A-Z][A-Za-z0-9_]*")) {
			throw new IllegalArgumentException(
					role + " is outside the registered simple-reference profile: " + name);
		}
		return name;
	}

	private static String actionName(String value, String role) {
		if (value == null || value.isEmpty()
				|| !value.matches("[A-Za-z_][A-Za-z0-9_]*")) {
			throw new IllegalArgumentException(role + " is invalid: " + value);
		}
		return value;
	}

	private static int count(Map<String, Integer> counts, String clause) {
		Integer count = counts.get(clause);
		return count == null ? 0 : count.intValue();
	}

	private static void requireOnce(Map<String, Integer> counts, String clause) {
		if (count(counts, clause) != 1) {
			throw new IllegalArgumentException(
					"Required updating-controller clause is absent: " + clause);
		}
	}

	private static List<String> immutable(List<String> source) {
		return Collections.unmodifiableList(new ArrayList<String>(source));
	}

	public List<String> getAliasPath() { return aliasPath; }
	/**
	 * Ordered outer-wrapper operations.  A true entry is not semantically
	 * transparent: the native post-GR comparison worker must apply and record
	 * that minimisation.  It never alters the predecision endpoint package.
	 */
	public List<Boolean> getAliasMinimalFlags() { return aliasMinimalFlags; }
	public String getDefinitionName() { return definitionName; }
	public MappingProfile getMappingProfile() { return mappingProfile; }
	public NewControllerMode getNewControllerMode() { return newControllerMode; }
	public M9UpdatingEndpointAst getOldEndpoint() { return oldEndpoint; }
	public M9UpdatingEndpointAst getNewEndpoint() { return newEndpoint; }
	public String getLegacyMappingReference() { return legacyMappingReference; }
	public List<String> getMapRelationReferences() { return mapRelationReferences; }
	public List<String> getTransitionGoalReferences() {
		return transitionGoalReferences;
	}
	public boolean isNonblocking() { return nonblocking; }
	public boolean isLegacyOnTheFly() { return legacyOnTheFly; }
	public boolean isRevisedOnTheFly() { return revisedOnTheFly; }
	public boolean isFineGrained() { return fineGrained; }
	public boolean isSelectiveFineGrained() { return selectiveFineGrained; }
	public List<PrecedenceEdgeAst> getPrecedence() { return precedence; }
	public boolean isLoadableStatesSpecified() { return loadableStatesSpecified; }
	public Set<Integer> getLoadableNewStateIndices() {
		return loadableNewStateIndices;
	}
	public Map<String, Integer> getClauseOccurrences() {
		return clauseOccurrences;
	}

	@Override
	public boolean equals(Object candidate) {
		if (this == candidate) return true;
		if (!(candidate instanceof M9UpdatingControllerAst)) return false;
		M9UpdatingControllerAst other = (M9UpdatingControllerAst) candidate;
		return nonblocking == other.nonblocking
				&& legacyOnTheFly == other.legacyOnTheFly
				&& revisedOnTheFly == other.revisedOnTheFly
				&& fineGrained == other.fineGrained
				&& selectiveFineGrained == other.selectiveFineGrained
				&& loadableStatesSpecified == other.loadableStatesSpecified
				&& aliasPath.equals(other.aliasPath)
				&& aliasMinimalFlags.equals(other.aliasMinimalFlags)
				&& definitionName.equals(other.definitionName)
				&& mappingProfile == other.mappingProfile
				&& newControllerMode == other.newControllerMode
				&& oldEndpoint.equals(other.oldEndpoint)
				&& newEndpoint.equals(other.newEndpoint)
				&& Objects.equals(
						legacyMappingReference, other.legacyMappingReference)
				&& mapRelationReferences.equals(other.mapRelationReferences)
				&& transitionGoalReferences.equals(other.transitionGoalReferences)
				&& precedence.equals(other.precedence)
				&& loadableNewStateIndices.equals(other.loadableNewStateIndices)
				&& clauseOccurrences.equals(other.clauseOccurrences);
	}

	@Override
	public int hashCode() {
		return Objects.hash(
				aliasPath, aliasMinimalFlags, definitionName, mappingProfile,
				newControllerMode, oldEndpoint, newEndpoint,
				legacyMappingReference, mapRelationReferences,
				transitionGoalReferences, nonblocking, legacyOnTheFly,
				revisedOnTheFly, fineGrained, selectiveFineGrained,
				precedence, loadableStatesSpecified,
				loadableNewStateIndices, clauseOccurrences);
	}

	public static final class PrecedenceEdgeAst {
		private final String before;
		private final String after;

		private PrecedenceEdgeAst(String before, String after) {
			this.before = before;
			this.after = after;
		}

		public String getBefore() { return before; }
		public String getAfter() { return after; }

		@Override
		public boolean equals(Object candidate) {
			if (this == candidate) return true;
			if (!(candidate instanceof PrecedenceEdgeAst)) return false;
			PrecedenceEdgeAst other = (PrecedenceEdgeAst) candidate;
			return before.equals(other.before) && after.equals(other.after);
		}

		@Override
		public int hashCode() {
			return Objects.hash(before, after);
		}
	}
}
