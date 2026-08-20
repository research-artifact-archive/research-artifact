package ltsa.lts;

import MTSSynthesis.ar.dc.uba.model.condition.Fluent;
import MTSSynthesis.controller.model.ControllerGoal;
import MTSTools.ac.ic.doc.mtstools.model.MTS;
import ltsa.ac.ic.doc.mtstools.util.fsp.AutomataToMTSConverter;
import ltsa.ac.ic.doc.mtstools.util.fsp.MTSToAutomataConverter;
import ltsa.control.ControllerGoalDefinition;
import ltsa.control.util.GoalDefToControllerGoal;
import ltsa.dispatcher.TransitionSystemDispatcher;
import ltsa.lts.ltl.AssertDefinition;
import ltsa.lts.ltl.PredicateDefinition;
import ltsa.updatingControllers.export.CompactStateEndpointAdmission;
import ltsa.updatingControllers.export.M9ClosedLoopEndpointSnapshot;
import ltsa.updatingControllers.export.M9CompositionProvenance;
import ltsa.updatingControllers.export.TraditionalPreGrSnapshotHook;
import ltsa.updatingControllers.structures.UpdatingControllerCompositeState;
import ltsa.updatingControllers.synthesis.UpdatingControllerSynthesizer;
import ltsa.updatingControllers.synthesis.UpdatingControllersUtils;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.Comparator;
import java.util.IdentityHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.Vector;
import java.nio.ByteBuffer;
import java.nio.CharBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

/**
 * One-parse, solver-free source boundary for the registered M9 UAV endpoint.
 *
 * <p>The factory owns its input and output objects, holds LTSA's process-wide
 * parser monitor through parsing and all source-derived materialization, and
 * never calls {@link LTSCompiler#continueCompilation(String)}.  Only the
 * registered dispatcher capability can consume the live graphs, exactly once.
 * Ordinary callers can inspect the immutable parser AST but cannot substitute
 * a graph, goal, provenance map, or output between preparation and synthesis.</p>
 */
public final class M9EndpointPreparedCase {
	private static final int MAX_SOURCE_CHARS = 16 * 1024 * 1024;
	private static final int MAX_AST_NODES = 1_000_000;
	private static final int MAX_STATES = 250_000;
	private static final int MAX_ACTIONS = 8_192;
	private static final int MAX_TRANSITIONS = 4_000_000;
	private static final int MAX_COMPONENTS = 64;
	private static final String ENEW_NAME = "M9_ENEW";
	private static final String SOURCE_NAME = "M9_CNEW_SOURCE";
	private static final String NO_IMPORT_DIRECTORY = "/M9-IMPORTS-FORBIDDEN";

	private final M9UpdatingControllerAst ast;
	private final CompositeState source;
	private final ControllerGoal<String> goal;
	private final EmptyLTSOuput output;
	private final CompactState materializedEnew;
	private final CompactStateEndpointAdmission.Admission enewAdmission;
	private final M9CompositionProvenance.Projection enewAuthority;
	private final M9CompositionProvenance.Projection environmentAuthority;
	private final M9CompositionProvenance.OrderedPrefixProjection environmentPrefix;
	private final TraditionalPreGrAuthority traditionalPreGrAuthority;
	private final TraditionalPreGrSnapshotHook.SealedCapture traditionalPreGrCapture;
	private final String sourceModelSha256;
	private final long sourceModelSizeBytes;
	private boolean consumed;

	private M9EndpointPreparedCase(
			M9UpdatingControllerAst ast,
			CompositeState source,
			ControllerGoal<String> goal,
			EmptyLTSOuput output,
			CompactState materializedEnew,
			CompactStateEndpointAdmission.Admission enewAdmission,
			M9CompositionProvenance.Projection enewAuthority,
			M9CompositionProvenance.Projection environmentAuthority,
			M9CompositionProvenance.OrderedPrefixProjection environmentPrefix,
			TraditionalPreGrAuthority traditionalPreGrAuthority,
			TraditionalPreGrSnapshotHook.SealedCapture traditionalPreGrCapture,
			String sourceModelSha256,
			long sourceModelSizeBytes) {
		this.ast = ast;
		this.source = source;
		this.goal = goal;
		this.output = output;
		this.materializedEnew = materializedEnew;
		this.enewAdmission = enewAdmission;
		this.enewAuthority = enewAuthority;
		this.environmentAuthority = environmentAuthority;
		this.environmentPrefix = environmentPrefix;
		this.traditionalPreGrAuthority = traditionalPreGrAuthority;
		this.traditionalPreGrCapture = traditionalPreGrCapture;
		this.sourceModelSha256 = sourceModelSha256;
		this.sourceModelSizeBytes = sourceModelSizeBytes;
	}

	/** Prepare from exact UTF-8 source bytes; no caller callback is retained. */
	public static M9EndpointPreparedCase prepareOfficial(byte[] sourceBytes) {
		if (sourceBytes == null || sourceBytes.length == 0
				|| sourceBytes.length > MAX_SOURCE_CHARS) {
			throw new IllegalArgumentException(
					"Registered M9 source bytes are absent or outside their byte profile.");
		}
		byte[] owned = sourceBytes.clone();
		String decoded;
		try {
			decoded = StandardCharsets.UTF_8.newDecoder()
					.onMalformedInput(CodingErrorAction.REPORT)
					.onUnmappableCharacter(CodingErrorAction.REPORT)
					.decode(ByteBuffer.wrap(owned)).toString();
		} catch (CharacterCodingException invalid) {
			throw new IllegalArgumentException(
					"Registered M9 source is not exact UTF-8.", invalid);
		}
		if (!java.util.Arrays.equals(
				owned, decoded.getBytes(StandardCharsets.UTF_8))) {
			throw new IllegalArgumentException(
					"Registered M9 source UTF-8 round trip differs.");
		}
		return prepareOwnedOfficial(
				decoded, hex(sha256(owned)), owned.length);
	}

	/** Convenience boundary for synthetic callers; bytes remain authoritative. */
	public static M9EndpointPreparedCase prepareOfficial(String sourceText) {
		if (sourceText == null || sourceText.isEmpty()
				|| sourceText.indexOf('\u0000') >= 0) {
			throw new IllegalArgumentException(
					"Registered M9 source text is absent or invalid.");
		}
		byte[] encoded;
		try {
			ByteBuffer buffer = StandardCharsets.UTF_8.newEncoder()
					.onMalformedInput(CodingErrorAction.REPORT)
					.onUnmappableCharacter(CodingErrorAction.REPORT)
					.encode(CharBuffer.wrap(sourceText));
			encoded = new byte[buffer.remaining()];
			buffer.get(encoded);
		} catch (CharacterCodingException invalid) {
			throw new IllegalArgumentException(
					"Registered M9 source text is not exact Unicode.", invalid);
		}
		return prepareOfficial(encoded);
	}

	private static M9EndpointPreparedCase prepareOwnedOfficial(
			String ownedSource, String sourceSha256, long sourceSizeBytes) {
		if (ownedSource.indexOf('\u0000') >= 0) {
			throw new IllegalArgumentException(
					"Registered M9 source contains NUL.");
		}
		synchronized (LTSCompiler.m9ParseLock()) {
			EmptyLTSOuput output = new EmptyLTSOuput();
			LTSCompiler compiler = new LTSCompiler(
					new LTSInputString(ownedSource), output, NO_IMPORT_DIRECTORY);
			compiler.compile();
			M9UpdatingControllerAst ast =
					M9UpdatingControllerAst.resolveForSyntheticTest(
							compiler, M9UpdatingControllerAst.OFFICIAL_TARGET);
			if (ast.getNewControllerMode()
					!= M9UpdatingControllerAst.NewControllerMode.SYNTHESIS_REQUIRED) {
				throw new IllegalArgumentException(
						"Registered endpoint route requires native Cnew synthesis.");
			}
			try {
				return prepareUnderParserLock(
						compiler, ast, output, sourceSha256, sourceSizeBytes);
			} finally {
				UpdatingControllersUtils.ACTION_FLUENTS_FOR_UPDATE.clear();
			}
		}
	}

	private static M9EndpointPreparedCase prepareUnderParserLock(
			LTSCompiler compiler,
			M9UpdatingControllerAst ast,
			EmptyLTSOuput output,
			String sourceSha256,
			long sourceSizeBytes) {
		Map<String, ProcessSpec> processes = compiler.m9ProcessesSnapshot();
		Map<String, CompositionExpression> composites =
				compiler.m9CompositesSnapshot();
		TraditionalPreGrAuthority traditionalPreGrAuthority =
				TraditionalPreGrAuthority.inspect(
						compiler, ast, composites, processes);
		List<String> environmentNames =
				ast.getNewEndpoint().getEnvironmentReferences();
		if (environmentNames.isEmpty()
				|| new LinkedHashSet<String>(environmentNames).size()
				!= environmentNames.size()) {
			throw new IllegalArgumentException(
					"Registered new environment is empty or duplicated.");
		}

		PredicateDefinition.compileAll();
		AssertDefinition.compileAll(output);
		String goalName = ast.getNewEndpoint().getGoalReference();
		ControllerGoalDefinition goalDefinition =
				ControllerGoalDefinition.getDefinition(
						new Symbol(Symbol.UPPERIDENT, goalName));
		M9ControllerGoalAst goalAst = M9ControllerGoalAst.capture(goalDefinition);
		if (!goalAst.equals(ast.getNewEndpoint().getGoal())) {
			throw new IllegalArgumentException(
					"Live controller goal differs from the compiler-owned AST.");
		}
		if (goalAst.isPermissive()
				|| goalAst.getParallelRankingThreads() != 0) {
			throw new IllegalArgumentException(
					"Registered endpoint goal requests an unsupported ranking profile.");
		}
		UpdatingControllersUtils.ACTION_FLUENTS_FOR_UPDATE.clear();
		ControllerGoal<String> goal = GoalDefToControllerGoal.getInstance()
				.buildControllerGoal(goalDefinition);
		canonicalizeAndValidateGoal(goal);

		List<CompactState> environment = new ArrayList<CompactState>();
		Set<String> componentNames = new LinkedHashSet<String>();
		for (String name : environmentNames) {
			environment.add(compileRestrictedProcess(
					compiler, processes, name, ProcessRole.ENVIRONMENT));
			if (!componentNames.add(name)) {
				throw new IllegalArgumentException(
						"New-environment component name is duplicated.");
			}
		}

		List<CompactState> safety = new ArrayList<CompactState>();
		Set<String> safetyNames = new LinkedHashSet<String>();
		for (Symbol reference : goalDefinition.getSafetyDefinitions()) {
			if (reference == null || reference.getName() == null
					|| reference.getName().isEmpty()) {
				throw new IllegalArgumentException(
						"Controller goal contains an absent safety reference.");
			}
			String name = reference.getName();
			if (!safetyNames.add(name) || !componentNames.add(name)) {
				throw new IllegalArgumentException(
						"Safety/environment component name is duplicated.");
			}
			boolean process = processes.containsKey(name);
			boolean constraint = AssertDefinition.getConstraint(name) != null;
			boolean composite = composites.containsKey(name);
			if ((process ? 1 : 0) + (constraint ? 1 : 0)
					+ (composite ? 1 : 0) != 1 || composite) {
				throw new IllegalArgumentException(
						"Safety reference is ambiguous, absent, or executable composite: "
								+ name);
			}
			CompactState machine;
			if (process) {
				machine = compileRestrictedProcess(
						compiler, processes, name, ProcessRole.SAFETY);
			} else {
				machine = AssertDefinition.compileConstraint(output, name);
				if (machine == null) {
					throw new IllegalArgumentException(
							"Safety constraint produced no finite machine: " + name);
				}
				MTS<Long, String> converted = AutomataToMTSConverter
						.getInstance().convert(machine);
				converted.removeAction("@" + name);
				machine = MTSToAutomataConverter.getInstance()
						.convert(converted, name, true);
				validatePrimitiveMachine(machine, name);
			}
			safety.add(machine);
		}
		if (environment.size() + safety.size() > MAX_COMPONENTS) {
			throw new IllegalArgumentException(
					"Registered endpoint exceeds the component census.");
		}

		M9ClosedLoopEndpointSnapshot.requireRegisteredNativeCompositionProfile();
		CompositeState enewState = new CompositeState(
				ENEW_NAME, clones(environment));
		enewState.compose(output);
		CompactState enew = requireComposition(
				enewState, ENEW_NAME, environmentNames);
		M9ClosedLoopEndpointSnapshot.requireRegisteredNativeCompositionProfile();

		List<CompactState> sourceChildren = new ArrayList<CompactState>();
		sourceChildren.addAll(environment);
		sourceChildren.addAll(safety);
		List<String> sourceNames = new ArrayList<String>();
		sourceNames.addAll(environmentNames);
		sourceNames.addAll(safetyNames);
		CompositeState source = new CompositeState(
				SOURCE_NAME, clones(sourceChildren));
		source.goal = goal;
		source.priorityIsLow = true;
		source.compose(output);
		CompactState sourceProduct = requireComposition(
				source, SOURCE_NAME, sourceNames);
		M9ClosedLoopEndpointSnapshot.requireRegisteredNativeCompositionProfile();
		requireGoalActionDomain(goal, sourceProduct);

		MTS<Long, String> firstComponent = AutomataToMTSConverter
				.getInstance().convert(environment.get(0));
		M9CompositionProvenance.Projection enewAuthority =
				M9CompositionProvenance.capture(
						AutomataToMTSConverter.getInstance().convert(enew),
						firstComponent);
		CompactStateEndpointAdmission.Admission enewAdmission =
				CompactStateEndpointAdmission.admitComposed(
						enew, enewAuthority, false);
		M9CompositionProvenance.Projection environmentAuthority =
				M9CompositionProvenance.capture(
						AutomataToMTSConverter.getInstance().convert(sourceProduct),
						firstComponent);
		M9CompositionProvenance.OrderedPrefixProjection prefix =
				M9CompositionProvenance.projectOrderedPrefix(
						environmentAuthority, enewAuthority);
		TraditionalPreGrSnapshotHook.SealedCapture traditionalPreGrCapture =
				traditionalPreGrAuthority.captureUnderParserLockIfEligible(
						ast, output, enewAuthority);

		return new M9EndpointPreparedCase(
				ast, source, goal, output, enew, enewAdmission,
				enewAuthority, environmentAuthority, prefix,
				traditionalPreGrAuthority, traditionalPreGrCapture,
				sourceSha256, sourceSizeBytes);
	}

	private static byte[] sha256(byte[] value) {
		try {
			return MessageDigest.getInstance("SHA-256").digest(value.clone());
		} catch (NoSuchAlgorithmException impossible) {
			throw new IllegalStateException(
					"Registered SHA-256 runtime is unavailable.", impossible);
		}
	}

	private static String hex(byte[] value) {
		StringBuilder result = new StringBuilder(value.length * 2);
		for (byte element : value) {
			result.append(Character.forDigit((element >>> 4) & 0xf, 16));
			result.append(Character.forDigit(element & 0xf, 16));
		}
		return result.toString();
	}

	private static void canonicalizeAndValidateGoal(
			ControllerGoal<String> goal) {
		if (goal == null || goal.getGuarantees() == null
				|| goal.getFluents() == null
				|| goal.getControllableActions() == null
				|| goal.getGuarantees().isEmpty()
				|| goal.getGuarantees().size() > MAX_COMPONENTS) {
			throw new IllegalArgumentException(
					"Registered endpoint goal has no bounded GR guarantee.");
		}
		if (goal.isNonBlocking() || goal.isExceptionHandling()
				|| goal.isNonTransient() || goal.isReachability()
				|| goal.isTestLatency()
				|| !goal.getConcurrencyFluents().isEmpty()
				|| !goal.getActivityFluents().isEmpty()
				|| !goal.getMarking().isEmpty()
				|| !goal.getDisturbances().isEmpty()
				|| !goal.getSelfLoopsUncontrollable().isEmpty()) {
			throw new IllegalArgumentException(
					"Registered endpoint goal requests an unsupported decision mode.");
		}
		if (goal.getLazyness() == null || goal.getLazyness().intValue() < 0) {
			throw new IllegalArgumentException(
					"Registered endpoint goal has an invalid laziness bound.");
		}
		List<Fluent> fluents = new ArrayList<Fluent>(goal.getFluents());
		Set<String> names = new LinkedHashSet<String>();
		for (Fluent fluent : fluents) {
			if (fluent == null || fluent.getName() == null
					|| fluent.getName().isEmpty() || !names.add(fluent.getName())) {
				throw new IllegalArgumentException(
						"Registered endpoint goal contains an invalid fluent.");
			}
		}
		Collections.sort(fluents, new Comparator<Fluent>() {
			@Override
			public int compare(Fluent left, Fluent right) {
				return left.getName().compareTo(right.getName());
			}
		});
		if (fluents.isEmpty() || fluents.size() + 1 > MAX_COMPONENTS) {
			throw new IllegalArgumentException(
					"Registered endpoint currently requires a bounded nonempty fluent set.");
		}
		goal.setFluents(new LinkedHashSet<Fluent>(fluents));
	}

	private static void requireGoalActionDomain(
			ControllerGoal<String> goal, CompactState source) {
		Set<String> visible = new LinkedHashSet<String>();
		for (String action : source.alphabet) {
			if (action == null || action.isEmpty()
					|| "*".equals(action)
					|| ltsa.lts.util.MTSUtils.isMaybe(action)) {
				throw new IllegalArgumentException(
						"Registered source has an invalid visible action.");
			}
			if (!"tau".equals(action)) visible.add(action);
		}
		if (!visible.containsAll(goal.getControllableActions())) {
			throw new IllegalArgumentException(
					"Registered controllable action is outside the source alphabet.");
		}
		for (Fluent fluent : goal.getFluents()) {
			requireFluentActions(
					fluent.getInitiatingActions(), visible, fluent.getName());
			requireFluentActions(
					fluent.getTerminatingActions(), visible, fluent.getName());
		}
	}

	private static void requireFluentActions(
			Set<MTSSynthesis.ar.dc.uba.model.language.Symbol> actions,
			Set<String> visible,
			String fluentName) {
		if (actions == null || actions.isEmpty()) {
			throw new IllegalArgumentException(
					"Registered fluent has no complete action definition: "
							+ fluentName);
		}
		for (MTSSynthesis.ar.dc.uba.model.language.Symbol action : actions) {
			String label = action == null ? null : action.toString();
			if (label == null || label.isEmpty() || !visible.contains(label)) {
				throw new IllegalArgumentException(
						"Registered fluent action is outside the source alphabet: "
								+ fluentName);
			}
		}
	}

	private enum ProcessRole { ENVIRONMENT, SAFETY }

	private static CompactState compileRestrictedProcess(
			LTSCompiler compiler,
			Map<String, ProcessSpec> processes,
			String name,
			ProcessRole role) {
		ProcessSpec process = processes.get(name);
		if (process == null || process != LTSCompiler.processes.get(name)) {
			throw new IllegalArgumentException(
					"Selected process differs from the atomic parser snapshot: " + name);
		}
		requireRestrictedProcess(process, role);
		CompactState machine = normalizeRequiredLts(
				new StateMachine(process).makeCompactState(), name);
		validatePrimitiveMachine(machine, name);
		if (processes != compiler.m9ProcessesSnapshot()
				|| process != compiler.m9ProcessesSnapshot().get(name)) {
			throw new IllegalArgumentException(
					"Compiler-owned process snapshot changed during materialization.");
		}
		return machine;
	}

	/**
	 * StateMachine advertises the modal companion of every LTS action even
	 * when the parsed process has no MAYBE edge.  The registered endpoint
	 * schema is an exact required-only LTS profile, so prove the stronger fact
	 * on the converted graph and rebuild only that required graph before any
	 * composition or admission step.
	 */
	static CompactState normalizeRequiredLts(
			CompactState machine, String expectedName) {
		if (machine == null || !expectedName.equals(machine.getName())) {
			throw new IllegalArgumentException(
					"Selected inline process produced no named finite machine: "
							+ expectedName);
		}
		MTS<Long, String> converted = AutomataToMTSConverter
				.getInstance().convert(machine);
		for (Long state : converted.getStates()) {
			if (!converted.getTransitions(
					state, MTS.TransitionType.MAYBE).isEmpty()) {
				throw new IllegalArgumentException(
						"Selected inline process contains a modal transition: "
								+ expectedName);
			}
		}
		CompactState required = MTSToAutomataConverter.getInstance()
				.convert(converted, expectedName, true);
		if (required.stateToComponentStates != null
				|| required.statePlusActionToComponentStates != null) {
			throw new IllegalArgumentException(
					"Required-only normalization retained composition metadata: "
							+ expectedName);
		}
		return required;
	}

	private static void requireRestrictedProcess(
			ProcessSpec process, ProcessRole role) {
		if (process.imported() || process.stateDefns == null
				|| process.stateDefns.isEmpty()
				|| process.isMinimal || process.isDeterministic
				|| process.isOptimistic || process.isPessimistic
				|| process.isClousure || process.isAbstract
				|| process.isController || process.isProbabilistic
				|| process.isMDP || process.isStarEnv || process.goal != null
				|| (role == ProcessRole.ENVIRONMENT
					&& (process.isProperty || process.actionsToErrorSet != null))
				|| (role == ProcessRole.SAFETY
					&& process.actionsToErrorSet != null && !process.isProperty)) {
			throw new IllegalArgumentException(
					"Selected process leaves the restricted inline LTSA profile.");
		}
		if (process.parameters == null || process.init_constants == null
				|| process.parameters.size() != process.init_constants.size()) {
			throw new IllegalArgumentException(
					"Selected process parameter defaults are incomplete.");
		}
		for (Object parameter : process.parameters) {
			if (!(parameter instanceof String)
					|| !process.init_constants.containsKey(parameter)) {
				throw new IllegalArgumentException(
						"Selected process parameter default is absent.");
			}
		}
		IdentityHashMap<StateExpr, Integer> colors =
				new IdentityHashMap<StateExpr, Integer>();
		int[] count = new int[]{0};
		for (StateDefn definition : process.stateDefns) {
			if (definition == null || definition.stateExpr == null) {
				throw new IllegalArgumentException(
						"Selected process contains an absent state expression.");
			}
			visitStateExpression(definition.stateExpr, colors, count);
		}
	}

	private static void visitStateExpression(
			StateExpr expression,
			IdentityHashMap<StateExpr, Integer> colors,
			int[] count) {
		Integer color = colors.get(expression);
		if (color != null) {
			if (color.intValue() == 1) {
				throw new IllegalArgumentException(
						"Selected process AST contains an identity cycle.");
			}
			return;
		}
		if (++count[0] > MAX_AST_NODES) {
			throw new IllegalArgumentException(
					"Selected process AST exceeds its node bound.");
		}
		colors.put(expression, Integer.valueOf(1));
		if (expression.processes != null && !expression.processes.isEmpty()) {
			throw new IllegalArgumentException(
					"Sequential process references are forbidden in the M9 endpoint profile.");
		}
		if (expression.boolexpr != null) {
			if (expression.thenpart == null || expression.elsepart == null) {
				throw new IllegalArgumentException(
						"Conditional state expression is incomplete.");
			}
			visitStateExpression(expression.thenpart, colors, count);
			visitStateExpression(expression.elsepart, colors, count);
		} else if (expression.thenpart != null || expression.elsepart != null) {
			throw new IllegalArgumentException(
					"State expression has orphan conditional branches.");
		}
		if (expression.choices != null) {
			for (ChoiceElement choice : expression.choices) {
				if (choice == null || choice instanceof ProbabilisticChoiceElement
						|| choice.stateExpr == null || choice.action == null) {
					throw new IllegalArgumentException(
							"Selected process has a probabilistic or incomplete choice.");
				}
				visitStateExpression(choice.stateExpr, colors, count);
			}
		}
		colors.put(expression, Integer.valueOf(2));
	}

	private static void validatePrimitiveMachine(
			CompactState machine, String expectedName) {
		if (machine == null || !expectedName.equals(machine.getName())
				|| machine.isComposition() || machine.components != null
				|| machine.stateToComponentStates != null
				|| machine.statePlusActionToComponentStates != null
				|| machine.maxStates < 1 || machine.maxStates > MAX_STATES
				|| machine.alphabet == null || machine.alphabet.length > MAX_ACTIONS
				|| machine.ntransitions() > MAX_TRANSITIONS) {
			throw new IllegalArgumentException(
					"Selected inline process produced an invalid primitive machine: "
							+ expectedName);
		}
	}

	private static Vector<CompactState> clones(List<CompactState> machines) {
		Vector<CompactState> result = new Vector<CompactState>(machines.size());
		for (CompactState machine : machines) result.add(machine.myclone());
		return result;
	}

	private static CompactState requireComposition(
			CompositeState state, String expectedName, List<String> childNames) {
		CompactState product = state == null ? null : state.composition;
		if (product == null || !expectedName.equals(product.getName())
				|| !product.isComposition() || product.components == null
				|| product.components.length != childNames.size()) {
			throw new IllegalArgumentException(
					"Plain registered composition lost its child provenance: "
							+ expectedName);
		}
		for (int index = 0; index < childNames.size(); index++) {
			if (product.components[index] == null
					|| !childNames.get(index).equals(
							product.components[index].getName())) {
				throw new IllegalArgumentException(
						"Plain registered composition reordered a child.");
			}
		}
		return product;
	}

	private static final class TraditionalPreGrAuthority {
		private final LTSCompiler compiler;
		private final long parserEpoch;
		private final UpdatingControllersDefinition definition;
		private final M9UpdatingControllerAst astSnapshot;
		private final ControllerGoalDefinition oldGoalDefinition;
		private final ControllerGoalDefinition newGoalDefinition;
		private final M9ControllerGoalAst oldGoalSnapshot;
		private final M9ControllerGoalAst newGoalSnapshot;
		private final Map<String, CompositionExpression> composites;
		private final Map<String, ProcessSpec> processes;
		private final Map<String, RelationDefinition> relations;
		private final List<UpdateFluentValue> updateFluents;
		private final String ineligibility;

		private TraditionalPreGrAuthority(
				LTSCompiler compiler,
				long parserEpoch,
				UpdatingControllersDefinition definition,
				M9UpdatingControllerAst astSnapshot,
				ControllerGoalDefinition oldGoalDefinition,
				ControllerGoalDefinition newGoalDefinition,
				M9ControllerGoalAst oldGoalSnapshot,
				M9ControllerGoalAst newGoalSnapshot,
				Map<String, CompositionExpression> composites,
				Map<String, ProcessSpec> processes,
				Map<String, RelationDefinition> relations,
				List<UpdateFluentValue> updateFluents,
				String ineligibility) {
			this.compiler = compiler;
			this.parserEpoch = parserEpoch;
			this.definition = definition;
			this.astSnapshot = astSnapshot;
			this.oldGoalDefinition = oldGoalDefinition;
			this.newGoalDefinition = newGoalDefinition;
			this.oldGoalSnapshot = oldGoalSnapshot;
			this.newGoalSnapshot = newGoalSnapshot;
			this.composites = Collections.unmodifiableMap(
					new java.util.LinkedHashMap<String, CompositionExpression>(
							composites));
			this.processes = Collections.unmodifiableMap(
					new java.util.LinkedHashMap<String, ProcessSpec>(processes));
			this.relations = Collections.unmodifiableMap(
					new java.util.LinkedHashMap<String, RelationDefinition>(
						relations));
			this.updateFluents = Collections.unmodifiableList(
					new ArrayList<UpdateFluentValue>(updateFluents));
			this.ineligibility = ineligibility;
		}

		static TraditionalPreGrAuthority inspect(
				LTSCompiler compiler,
				M9UpdatingControllerAst ast,
				Map<String, CompositionExpression> parsedComposites,
				Map<String, ProcessSpec> parsedProcesses) {
			try {
				return inspectEligible(
						compiler, ast, parsedComposites, parsedProcesses);
			} catch (IllegalArgumentException ineligible) {
				return new TraditionalPreGrAuthority(
						compiler,
							compiler.m9CapturedParseEpoch(),
							null,
							ast,
							null,
							null,
							null,
							null,
							Collections.<String, CompositionExpression>emptyMap(),
							Collections.<String, ProcessSpec>emptyMap(),
							Collections.<String, RelationDefinition>emptyMap(),
							Collections.<UpdateFluentValue>emptyList(),
							ineligible.getMessage());
			}
		}

		private static TraditionalPreGrAuthority inspectEligible(
				LTSCompiler compiler,
				M9UpdatingControllerAst ast,
				Map<String, CompositionExpression> parsedComposites,
				Map<String, ProcessSpec> parsedProcesses) {
			if (!ast.isLegacyOnTheFly() || ast.isRevisedOnTheFly()
					|| ast.isFineGrained() || ast.isSelectiveFineGrained()) {
				throw new IllegalArgumentException(
						"Traditional pre-GR requires legacy non-fine on-the-fly mode.");
			}
			CompositionExpression rawDefinition =
					parsedComposites.get(ast.getDefinitionName());
			if (rawDefinition == null
					|| rawDefinition.getClass()
					   != UpdatingControllersDefinition.class
					|| rawDefinition != LTSCompiler.getComposite(
							ast.getDefinitionName())) {
				throw new IllegalArgumentException(
						"Updating-controller definition authority differs.");
			}
			Map<String, CompositionExpression> usedComposites =
					new java.util.LinkedHashMap<String, CompositionExpression>();
			Map<String, ProcessSpec> usedProcesses =
					new java.util.LinkedHashMap<String, ProcessSpec>();
			IdentityHashMap<CompositionExpression, Boolean> activeComposites =
					new IdentityHashMap<CompositionExpression, Boolean>();
			int[] graphNodes = new int[]{0};
			int[] leafOccurrences = new int[]{0};
			requirePlainCompositeGraph(
					ast.getOldEndpoint().getControllerReference(),
					parsedComposites, parsedProcesses,
					usedComposites, usedProcesses,
					activeComposites, graphNodes, leafOccurrences);
			if (ast.getMappingProfile()
					!= M9UpdatingControllerAst.MappingProfile.RELATIONAL_TRIPLE) {
				throw new IllegalArgumentException(
						"Traditional completion handoff requires a relational mapping profile.");
			}
			for (String name : ast.getOldEndpoint()
					.getEnvironmentReferences()) {
				requireTraditionalLeafOccurrence(
						name, parsedProcesses, usedProcesses,
						leafOccurrences);
			}
			for (String name : ast.getNewEndpoint()
					.getEnvironmentReferences()) {
				requireTraditionalLeafOccurrence(
						name, parsedProcesses, usedProcesses,
						leafOccurrences);
			}
			Map<String, RelationDefinition> usedRelations =
					new java.util.LinkedHashMap<String, RelationDefinition>();
			for (String name : ast.getMapRelationReferences()) {
				RelationDefinition relation =
						compiler.m9RelationsSnapshot().get(name);
				if (relation == null
						|| relation != LTSCompiler.getRelations().get(name)) {
					throw new IllegalArgumentException(
							"Mapping relation authority differs: " + name);
				}
				usedRelations.put(name, relation);
			}
			requireTraditionalFormulaProfile(ast.getOldEndpoint().getGoal());
			requireTraditionalFormulaProfile(ast.getNewEndpoint().getGoal());
			ControllerGoalDefinition oldGoalDefinition =
					ControllerGoalDefinition.getDefinition(
							new Symbol(Symbol.UPPERIDENT,
									ast.getOldEndpoint().getGoalReference()));
			ControllerGoalDefinition newGoalDefinition =
					ControllerGoalDefinition.getDefinition(
							new Symbol(Symbol.UPPERIDENT,
									ast.getNewEndpoint().getGoalReference()));
			requireLiveGoalAuthority(
					oldGoalDefinition, ast.getOldEndpoint().getGoal(), "old");
			requireLiveGoalAuthority(
					newGoalDefinition, ast.getNewEndpoint().getGoal(), "new");
			for (String name : ast.getTransitionGoalReferences()) {
				if (AssertDefinition.getConstraint(name) == null) {
					throw new IllegalArgumentException(
							"Traditional transition requirement is not an LTL constraint: "
									+ name);
				}
			}
			usedComposites.put(ast.getDefinitionName(), rawDefinition);
			return new TraditionalPreGrAuthority(
					compiler,
					compiler.m9CapturedParseEpoch(),
					(UpdatingControllersDefinition) rawDefinition,
					ast,
					oldGoalDefinition,
					newGoalDefinition,
					M9ControllerGoalAst.capture(oldGoalDefinition),
					M9ControllerGoalAst.capture(newGoalDefinition),
					usedComposites,
					usedProcesses,
					usedRelations,
					captureUpdateFluents(),
					null);
		}

		private static void requireLiveGoalAuthority(
				ControllerGoalDefinition definition,
				M9ControllerGoalAst expected,
				String role) {
			if (definition == null
					|| definition.getControllableActionSet() == null
					|| definition.getSafetyDefinitions() == null
					|| definition.getFaultsDefinitions() == null
					|| !M9ControllerGoalAst.capture(definition).equals(expected)) {
				throw new IllegalArgumentException(
						"Traditional " + role + " goal authority differs.");
			}
		}

		private static void requireTraditionalFormulaProfile(
				M9ControllerGoalAst goal) {
			for (String name : goal.getSafety()) {
				if (AssertDefinition.getConstraint(name) == null) {
					throw new IllegalArgumentException(
							"Traditional safety is not an LTL constraint: " + name);
				}
			}
		}

		private static void requireRestrictedProcessIdentity(
				String name,
				Map<String, ProcessSpec> parsedProcesses,
				Map<String, ProcessSpec> usedProcesses) {
			ProcessSpec process = parsedProcesses.get(name);
			if (process == null || process != LTSCompiler.getProcesses().get(name)
					|| AssertDefinition.getConstraint(name) != null
					|| AssertDefinition.getDefinition(name) != null) {
				throw new IllegalArgumentException(
						"Traditional process authority differs or its namespace is ambiguous: "
								+ name);
			}
			requireRestrictedProcess(process, ProcessRole.ENVIRONMENT);
			usedProcesses.put(name, process);
		}

		private static void requireTraditionalLeafOccurrence(
				String name,
				Map<String, ProcessSpec> parsedProcesses,
				Map<String, ProcessSpec> usedProcesses,
				int[] leafOccurrences) {
			if (leafOccurrences == null || leafOccurrences.length != 1
					|| ++leafOccurrences[0] > MAX_COMPONENTS) {
				throw new IllegalArgumentException(
						"Traditional plain graph exceeds its leaf occurrence bound.");
			}
			requireRestrictedProcessIdentity(name, parsedProcesses, usedProcesses);
		}

		private static void requirePlainCompositeGraph(
				String name,
				Map<String, CompositionExpression> parsedComposites,
				Map<String, ProcessSpec> parsedProcesses,
				Map<String, CompositionExpression> usedComposites,
				Map<String, ProcessSpec> usedProcesses,
				IdentityHashMap<CompositionExpression, Boolean> active,
				int[] graphNodes,
				int[] leafOccurrences) {
			CompositionExpression expression = parsedComposites.get(name);
			if (expression == null || expression != LTSCompiler.getComposite(name)
					|| expression.getClass() != CompositionExpression.class
					|| AssertDefinition.getConstraint(name) != null
					|| AssertDefinition.getDefinition(name) != null) {
				throw new IllegalArgumentException(
						"Traditional composite authority is absent, executable, or ambiguous: "
								+ name);
			}
			if (active.containsKey(expression)) {
				throw new IllegalArgumentException(
						"Traditional composite graph is recursive: " + name);
			}
			if (graphNodes == null || graphNodes.length != 1
					|| ++graphNodes[0] > 4 * MAX_COMPONENTS) {
				throw new IllegalArgumentException(
						"Traditional composite graph exceeds its expanded-node bound.");
			}
			if (expression.body == null
					|| expression.parameters == null
					|| !expression.parameters.isEmpty()
					|| expression.priorityActions != null
					|| expression.alphaHidden != null
					|| expression.exposeNotHide
					|| expression.makeDeterministic || expression.makeMinimal
					|| expression.makeProperty || expression.makeCompose
					|| expression.makeOptimistic || expression.makePessimistic
					|| expression.makeClousure || expression.makeAbstract
					|| expression.makeController || expression.makeRTCController
					|| expression.makeRTCAnalysisController || expression.makeMDP
					|| expression.isProbabilistic || expression.makeEnactment
					|| expression.checkCompatible || expression.isStarEnv
					|| expression.isPlant || expression.isControlledDet
					|| expression.makeControlStack || expression.isHeuristic
					|| expression.isCompositional
					|| expression.isMonolithicDirector
					|| expression.isPartialOrderReduction
					|| expression.goal != null
					|| expression.actionsToErrorSet != null
					|| expression.isMakeComponent()) {
				throw new IllegalArgumentException(
						"Traditional composite requests an executable modifier: "
								+ name);
			}
			active.put(expression, Boolean.TRUE);
			usedComposites.put(name, expression);
			try {
				visitPlainCompositeBody(
						expression.body, parsedComposites, parsedProcesses,
						usedComposites, usedProcesses, active,
						graphNodes, leafOccurrences);
			} finally {
				active.remove(expression);
			}
		}

		private static void visitPlainCompositeBody(
				CompositeBody body,
				Map<String, CompositionExpression> parsedComposites,
				Map<String, ProcessSpec> parsedProcesses,
				Map<String, CompositionExpression> usedComposites,
				Map<String, ProcessSpec> usedProcesses,
				IdentityHashMap<CompositionExpression, Boolean> active,
				int[] graphNodes,
				int[] leafOccurrences) {
			if (graphNodes == null || graphNodes.length != 1
					|| ++graphNodes[0] > 4 * MAX_COMPONENTS) {
				throw new IllegalArgumentException(
						"Traditional composite body exceeds its expanded-node bound.");
			}
			if (body == null || body.boolexpr != null || body.range != null
					|| body.thenpart != null || body.elsepart != null
					|| body.prefix != null || body.accessSet != null
					|| body.relabelDefns != null
					|| (body.singleton == null) == (body.procRefs == null)) {
				throw new IllegalArgumentException(
						"Traditional composite body leaves the plain profile.");
			}
			if (body.singleton != null) {
				ProcessRef reference = body.singleton;
				if (reference.name == null || reference.actualParams != null
						|| reference.forceCompilation || !reference.passBackClone) {
					throw new IllegalArgumentException(
							"Traditional composite reference is executable.");
				}
				String name = reference.name.toString();
				if (parsedProcesses.containsKey(name)) {
					requireTraditionalLeafOccurrence(
							name, parsedProcesses, usedProcesses,
							leafOccurrences);
				} else {
					requirePlainCompositeGraph(
							name, parsedComposites, parsedProcesses,
							usedComposites, usedProcesses, active,
							graphNodes, leafOccurrences);
				}
				return;
			}
			if (body.procRefs.isEmpty()) {
				throw new IllegalArgumentException(
						"Traditional composite body is empty.");
			}
			for (CompositeBody child : body.procRefs) {
				visitPlainCompositeBody(
						child, parsedComposites, parsedProcesses,
						usedComposites, usedProcesses, active,
						graphNodes, leafOccurrences);
			}
		}

		void requireEligible() {
			if (ineligibility != null) {
				throw new IllegalArgumentException(
						"Registered source is not traditional pre-GR eligible: "
								+ ineligibility);
			}
		}

		UpdatingControllerCompositeState materialize(
				M9UpdatingControllerAst ast,
				LTSOutput output) {
			requireEligible();
			if (compiler.m9CapturedParseEpoch() != parserEpoch
					|| LTSCompiler.m9CurrentParseEpoch() != parserEpoch) {
				throw new IllegalStateException(
						"Parser registry epoch changed before pre-GR capture.");
			}
			M9UpdatingControllerAst currentAst =
					M9UpdatingControllerAst.resolveForSyntheticTest(
							compiler, M9UpdatingControllerAst.OFFICIAL_TARGET);
			if (!astSnapshot.equals(ast)
					|| !astSnapshot.equals(currentAst)) {
				throw new IllegalStateException(
						"Updating-controller AST changed before pre-GR capture.");
			}
			if (ControllerGoalDefinition.getDefinition(new Symbol(
					Symbol.UPPERIDENT,
					ast.getOldEndpoint().getGoalReference())) != oldGoalDefinition
					|| ControllerGoalDefinition.getDefinition(new Symbol(
					Symbol.UPPERIDENT,
					ast.getNewEndpoint().getGoalReference())) != newGoalDefinition
					|| !M9ControllerGoalAst.capture(oldGoalDefinition)
							.equals(oldGoalSnapshot)
					|| !M9ControllerGoalAst.capture(newGoalDefinition)
							.equals(newGoalSnapshot)) {
				throw new IllegalStateException(
						"Controller-goal authority changed before pre-GR capture.");
			}
			if (!captureUpdateFluents().equals(updateFluents)) {
				throw new IllegalStateException(
						"Internal update-fluent authority changed before pre-GR capture.");
			}
			for (Map.Entry<String, CompositionExpression> entry
					: composites.entrySet()) {
				if (compiler.m9CompositesSnapshot().get(entry.getKey())
						!= entry.getValue()
						|| LTSCompiler.getComposite(entry.getKey())
						!= entry.getValue()) {
					throw new IllegalStateException(
							"Composite authority changed before pre-GR capture.");
				}
			}
			for (Map.Entry<String, ProcessSpec> entry : processes.entrySet()) {
				if (compiler.m9ProcessesSnapshot().get(entry.getKey())
						!= entry.getValue()
						|| LTSCompiler.getProcesses().get(entry.getKey())
						!= entry.getValue()) {
					throw new IllegalStateException(
							"Process authority changed before pre-GR capture.");
				}
			}
			for (Map.Entry<String, RelationDefinition> entry
					: relations.entrySet()) {
				if (compiler.m9RelationsSnapshot().get(entry.getKey())
						!= entry.getValue()
						|| LTSCompiler.getRelations().get(entry.getKey())
						!= entry.getValue()) {
					throw new IllegalStateException(
							"Relation authority changed before pre-GR capture.");
				}
			}
			for (String name : processes.keySet()) {
				if (LTSCompiler.getCompiled().containsKey(name)) {
					throw new IllegalStateException(
							"A compiled-process cache bypasses pre-GR authority: " + name);
				}
			}
			for (String name : composites.keySet()) {
				if (LTSCompiler.getCompiled().containsKey(name)) {
					throw new IllegalStateException(
							"A compiled-composite cache bypasses pre-GR authority: " + name);
				}
			}
			PredicateDefinition.compileAll();
			AssertDefinition.compileAll(output);
			return definition.composeTraditionalPreGrForM9(ast);
		}

		TraditionalPreGrSnapshotHook.SealedCapture
				captureUnderParserLockIfEligible(
						M9UpdatingControllerAst ast,
						LTSOutput output,
						M9CompositionProvenance.Projection enewAuthority) {
			if (ineligibility != null) {
				return null;
			}
			UpdatingControllersUtils.ACTION_FLUENTS_FOR_UPDATE.clear();
			TraditionalPreGrSnapshotHook.Scope scope = null;
			try {
				UpdatingControllerCompositeState state = materialize(ast, output);
				requireLegacyMappingAction(state);
				scope = TraditionalPreGrSnapshotHook.arm(enewAuthority);
				try {
					UpdatingControllerSynthesizer.generateController(state, output);
				} catch (TraditionalPreGrSnapshotHook.SnapshotComplete expected) {
					TraditionalPreGrSnapshotHook.SealedCapture sealed =
							scope.closeAndSeal();
					ltsa.updatingControllers.export.TraditionalPreGrSnapshot
							.CompletionSeed seed = sealed.getSnapshot()
									.getCompletionSeed();
					if (!sealed.usesProductionLedger()
							|| !sealed.isAttemptConsumed()
							|| sealed.getCaptureAttempts() != 1
							|| sealed.getNativeUpdateGrEntries() != 0
							|| seed == null
							|| !M9CompositionProvenance.canonicalEquals(
									seed.getNewEnvironment(), enewAuthority)) {
						throw new IllegalStateException(
								"Traditional completion seed is not bound to the prepared Enew authority.");
					}
					return sealed;
				}
				throw new IllegalStateException(
						"Traditional pre-GR synthesizer returned without capture.");
			} finally {
				if (scope != null && TraditionalPreGrSnapshotHook.isArmed()) {
					scope.close();
				}
				UpdatingControllersUtils.ACTION_FLUENTS_FOR_UPDATE.clear();
			}
		}

		private static void requireLegacyMappingAction(
				UpdatingControllerCompositeState state) {
			MTS<Long, String> mapping = state == null ? null : state.getMapping();
			if (mapping == null || !mapping.getActions().contains("reconfigure")) {
				throw new IllegalArgumentException(
						"Traditional mapping has no exact reconfigure action.");
			}
			for (String action : mapping.getActions()) {
				if (action != null && action.startsWith("reconfigure")
						&& !"reconfigure".equals(action)) {
					throw new IllegalArgumentException(
							"Traditional mapping contains a non-legacy reconfigure label.");
				}
			}
		}

		private static List<UpdateFluentValue> captureUpdateFluents() {
			List<UpdateFluentValue> result = new ArrayList<UpdateFluentValue>();
			result.add(UpdateFluentValue.capture(UpdatingControllersUtils.beginFluent));
			result.add(UpdateFluentValue.capture(UpdatingControllersUtils.stopFluent));
			result.add(UpdateFluentValue.capture(UpdatingControllersUtils.reconFluent));
			result.add(UpdateFluentValue.capture(UpdatingControllersUtils.startFluent));
			return result;
		}

		private static final class UpdateFluentValue {
			private final String name;
			private final boolean initial;
			private final List<String> initiating;
			private final List<String> terminating;

			private UpdateFluentValue(
					String name,
					boolean initial,
					List<String> initiating,
					List<String> terminating) {
				this.name = name;
				this.initial = initial;
				this.initiating = initiating;
				this.terminating = terminating;
			}

			static UpdateFluentValue capture(Fluent fluent) {
				if (fluent == null || fluent.getName() == null
						|| fluent.getInitiatingActions() == null
						|| fluent.getTerminatingActions() == null) {
					throw new IllegalArgumentException(
							"Internal update-fluent authority is absent.");
				}
				return new UpdateFluentValue(
						fluent.getName(),
						fluent.getInitialValue(),
						captureSymbols(fluent.getInitiatingActions()),
						captureSymbols(fluent.getTerminatingActions()));
			}

			private static List<String> captureSymbols(
					Collection<MTSSynthesis.ar.dc.uba.model.language.Symbol> symbols) {
				List<String> result = new ArrayList<String>();
				for (MTSSynthesis.ar.dc.uba.model.language.Symbol symbol : symbols) {
					if (symbol == null || symbol.toString() == null
							|| symbol.toString().isEmpty()) {
						throw new IllegalArgumentException(
								"Internal update-fluent action is absent.");
					}
					result.add(symbol.toString());
				}
				Collections.sort(result);
				if (new LinkedHashSet<String>(result).size() != result.size()) {
					throw new IllegalArgumentException(
							"Internal update-fluent action is duplicated.");
				}
				return Collections.unmodifiableList(result);
			}

			@Override
			public boolean equals(Object candidate) {
				if (this == candidate) return true;
				if (!(candidate instanceof UpdateFluentValue)) return false;
				UpdateFluentValue other = (UpdateFluentValue) candidate;
				return initial == other.initial
						&& name.equals(other.name)
						&& initiating.equals(other.initiating)
						&& terminating.equals(other.terminating);
			}

			@Override
			public int hashCode() {
				int result = name.hashCode();
				result = 31 * result + (initial ? 1 : 0);
				result = 31 * result + initiating.hashCode();
				result = 31 * result + terminating.hashCode();
				return result;
			}
		}
	}

	public M9UpdatingControllerAst getAst() {
		return ast;
	}

	/** Consume once; the capability constructor and instance are dispatcher-private. */
	public synchronized Materialization consume(
			TransitionSystemDispatcher.M9PreparedCaseAccess access) {
		if (!TransitionSystemDispatcher.isRegisteredM9PreparedCaseAccess(access)) {
			throw new IllegalArgumentException(
					"Registered dispatcher capability is required.");
		}
		if (consumed) {
			throw new IllegalStateException(
					"Registered M9 prepared case has already been consumed.");
		}
		consumed = true;
		return new Materialization(
				source, goal, output, materializedEnew, enewAdmission,
				enewAuthority, environmentAuthority, environmentPrefix,
				traditionalPreGrAuthority, traditionalPreGrCapture,
				sourceModelSha256, sourceModelSizeBytes);
	}

	/** Opaque payload visible only after possession of the dispatcher token. */
	public static final class Materialization {
		private final CompositeState source;
		private final ControllerGoal<String> goal;
		private final EmptyLTSOuput output;
		private final CompactState materializedEnew;
		private final CompactStateEndpointAdmission.Admission enewAdmission;
		private final M9CompositionProvenance.Projection enewAuthority;
		private final M9CompositionProvenance.Projection environmentAuthority;
		private final M9CompositionProvenance.OrderedPrefixProjection environmentPrefix;
		private final TraditionalPreGrAuthority traditionalPreGrAuthority;
		private final TraditionalPreGrSnapshotHook.SealedCapture
				traditionalPreGrCapture;
		private final String sourceModelSha256;
		private final long sourceModelSizeBytes;
		private boolean traditionalPreGrConsumed;

		private Materialization(
				CompositeState source,
				ControllerGoal<String> goal,
				EmptyLTSOuput output,
				CompactState materializedEnew,
				CompactStateEndpointAdmission.Admission enewAdmission,
				M9CompositionProvenance.Projection enewAuthority,
				M9CompositionProvenance.Projection environmentAuthority,
				M9CompositionProvenance.OrderedPrefixProjection environmentPrefix,
				TraditionalPreGrAuthority traditionalPreGrAuthority,
				TraditionalPreGrSnapshotHook.SealedCapture traditionalPreGrCapture,
				String sourceModelSha256,
				long sourceModelSizeBytes) {
			this.source = source;
			this.goal = goal;
			this.output = output;
			this.materializedEnew = materializedEnew;
			this.enewAdmission = enewAdmission;
			this.enewAuthority = enewAuthority;
			this.environmentAuthority = environmentAuthority;
			this.environmentPrefix = environmentPrefix;
			this.traditionalPreGrAuthority = traditionalPreGrAuthority;
			this.traditionalPreGrCapture = traditionalPreGrCapture;
			this.sourceModelSha256 = sourceModelSha256;
			this.sourceModelSizeBytes = sourceModelSizeBytes;
		}

		public CompositeState getSource() { return source; }
		public ControllerGoal<String> getGoal() { return goal; }
		public EmptyLTSOuput getOutput() { return output; }
		public CompactState getMaterializedEnew() { return materializedEnew; }
		public CompactStateEndpointAdmission.Admission getEnewAdmission() {
			return enewAdmission;
		}
		public M9CompositionProvenance.Projection getEnewAuthority() {
			return enewAuthority;
		}
		public M9CompositionProvenance.Projection getEnvironmentAuthority() {
			return environmentAuthority;
		}
		public M9CompositionProvenance.OrderedPrefixProjection
				getEnvironmentPrefix() { return environmentPrefix; }
		public String getSourceModelSha256() { return sourceModelSha256; }
		public long getSourceModelSizeBytes() { return sourceModelSizeBytes; }

		public synchronized void requireTraditionalPreGrEligible(
				TransitionSystemDispatcher.M9PreparedCaseAccess access) {
			if (!TransitionSystemDispatcher.isRegisteredM9PreparedCaseAccess(access)) {
				throw new IllegalArgumentException(
						"Registered dispatcher capability is required.");
			}
			traditionalPreGrAuthority.requireEligible();
			if (traditionalPreGrCapture == null) {
				throw new IllegalStateException(
						"Traditional pre-GR capture was not sealed during parsing.");
			}
		}

		public synchronized TraditionalPreGrSnapshotHook.SealedCapture
				captureTraditionalPreGr(
						TransitionSystemDispatcher.M9PreparedCaseAccess access) {
			if (!TransitionSystemDispatcher.isRegisteredM9PreparedCaseAccess(access)) {
				throw new IllegalArgumentException(
						"Registered dispatcher capability is required.");
			}
			if (traditionalPreGrConsumed) {
				throw new IllegalStateException(
						"Traditional pre-GR capture was already consumed.");
			}
			traditionalPreGrConsumed = true;
			traditionalPreGrAuthority.requireEligible();
			if (traditionalPreGrCapture == null) {
				throw new IllegalStateException(
						"Traditional pre-GR capture was not sealed during parsing.");
			}
			return traditionalPreGrCapture;
		}
	}
}
