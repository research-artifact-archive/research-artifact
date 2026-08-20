package ltsa.lts;

import org.junit.Assert;
import org.testng.annotations.Test;

import java.util.Arrays;

@Test(singleThreaded = true)
public class M9UpdatingControllerAstTest {
	@Test
	public void resolvesOnlyTheFixedTargetThroughTransparentAliases() {
		LTSCompiler compiler = compile(mappingSource(
				"minimal ||ALIAS = (UPD).\n"
				+ "||UPDATE_CONTROLLER = (ALIAS)."));
		int registrySize = compiler.getComposites().size();
		M9UpdatingControllerAst ast =
				M9UpdatingControllerAst.resolveForSyntheticTest(
						compiler, M9UpdatingControllerAst.OFFICIAL_TARGET);
		Assert.assertEquals(
				Arrays.asList("UPDATE_CONTROLLER", "ALIAS", "UPD"),
				ast.getAliasPath());
		Assert.assertEquals(Arrays.asList(false, true),
				ast.getAliasMinimalFlags());
		Assert.assertEquals("UPD", ast.getDefinitionName());
		Assert.assertEquals(M9UpdatingControllerAst.MappingProfile.LEGACY_MAPPING,
				ast.getMappingProfile());
		Assert.assertEquals(M9UpdatingControllerAst.NewControllerMode.SYNTHESIS_REQUIRED,
				ast.getNewControllerMode());
		Assert.assertEquals("OLD_CONTROLLER",
				ast.getOldEndpoint().getControllerReference());
		Assert.assertEquals(Arrays.asList("NEW"),
				ast.getNewEndpoint().getEnvironmentReferences());
		Assert.assertEquals("MAP_ENV", ast.getLegacyMappingReference());
		Assert.assertTrue(ast.isNonblocking());
		Assert.assertEquals(registrySize, compiler.getComposites().size());
		try {
			ast.getAliasPath().add("MUTANT");
			Assert.fail("Expected immutable alias path");
		} catch (UnsupportedOperationException expected) {
			// expected
		}
	}

	@Test
	public void acceptsDirectRelationalLeafAndPreservesClausePresence() {
		String source = String.join("\n",
				baseDefinitions(),
				"relation R = {OLD@OLD = reconfigure_COMPONENT -> NEW@NEW}",
				"updatingController UPDATE_CONTROLLER = {",
				"oldController = OLD_CONTROLLER,",
				"oldEnvironment = {OLD},",
				"newEnvironment = {NEW},",
				"mapRelation = {R},",
				"oldGoal = OLD_SPEC, newGoal = NEW_SPEC,",
				"nonblocking, revised_on_the_fly, fine_grained,",
				"precedence = { stopOldSpec < reconfigure, reconfigure < startNewSpec },",
				"loadable_new_states = {0, 2}",
				"}");
		M9UpdatingControllerAst ast = M9UpdatingControllerAst
				.resolveForSyntheticTest(compile(source),
						M9UpdatingControllerAst.OFFICIAL_TARGET);
		Assert.assertEquals(Arrays.asList("UPDATE_CONTROLLER"), ast.getAliasPath());
		Assert.assertEquals(M9UpdatingControllerAst.MappingProfile.RELATIONAL_TRIPLE,
				ast.getMappingProfile());
		Assert.assertEquals(Arrays.asList("OLD"),
				ast.getOldEndpoint().getEnvironmentReferences());
		Assert.assertEquals(Arrays.asList("R"), ast.getMapRelationReferences());
		Assert.assertTrue(ast.isRevisedOnTheFly());
		Assert.assertTrue(ast.isFineGrained());
		Assert.assertTrue(ast.isLoadableStatesSpecified());
		Assert.assertEquals(2, ast.getPrecedence().size());
		Assert.assertEquals("OLD_SPEC", ast.getOldEndpoint().getGoal().getName());
	}

	@Test
	public void retainsAnInstanceOwnedParseAfterASecondCompilerRuns() {
		LTSCompiler first = compile(mappingSource(
				"||UPDATE_CONTROLLER = (UPD)."));
		String secondSource = mappingSource(
				"||UPDATE_CONTROLLER = (UPD).")
				.replace("NEW = (a -> NEW).", "NEW_B = (a -> NEW_B).")
				.replace("NEW_CONTROLLER = NEW~", "NEW_CONTROLLER = NEW_B~")
				.replace("newEnvironment = {NEW}", "newEnvironment = {NEW_B}");
		LTSCompiler second = compile(secondSource);

		M9UpdatingControllerAst firstAst =
				M9UpdatingControllerAst.resolveForSyntheticTest(
						first, M9UpdatingControllerAst.OFFICIAL_TARGET);
		M9UpdatingControllerAst secondAst =
				M9UpdatingControllerAst.resolveForSyntheticTest(
						second, M9UpdatingControllerAst.OFFICIAL_TARGET);
		Assert.assertEquals(Arrays.asList("NEW"),
				firstAst.getNewEndpoint().getEnvironmentReferences());
		Assert.assertEquals(Arrays.asList("NEW_B"),
				secondAst.getNewEndpoint().getEnvironmentReferences());
	}

	@Test
	public void typesExplicitAndSynthesisedNewControllerRoutes() {
		String explicit = String.join("\n",
				baseDefinitions(),
				"relation R = {OLD@OLD = reconfigure_COMPONENT -> NEW@NEW}",
				"updatingController UPDATE_CONTROLLER = {",
				"oldController = OLD_CONTROLLER, oldEnvironment = {OLD},",
				"newEnvironment = {NEW}, mapRelation = {R},",
				"oldGoal = OLD_SPEC, newGoal = NEW_SPEC,",
				"revised_on_the_fly, newController = NEW_CONTROLLER",
				"}");
		M9UpdatingControllerAst explicitAst =
				M9UpdatingControllerAst.resolveForSyntheticTest(
						compile(explicit), M9UpdatingControllerAst.OFFICIAL_TARGET);
		Assert.assertEquals(
				M9UpdatingControllerAst.NewControllerMode.EXPLICIT_SOURCE_CONTROLLER,
				explicitAst.getNewControllerMode());

		String ignoredExplicit = mappingSource(
				"||UPDATE_CONTROLLER = (UPD).")
				.replace("nonblocking, on_the_fly",
						"nonblocking, on_the_fly, newController = NEW_CONTROLLER");
		expectResolveFailure(ignoredExplicit, "requires revised-on-the-fly");
	}

	@Test
	public void distinguishesAnExplicitEmptyPrecedenceRelation() {
		String source = String.join("\n",
				baseDefinitions(),
				"relation R = {OLD@OLD = reconfigure_COMPONENT -> NEW@NEW}",
				"updatingController UPDATE_CONTROLLER = {",
				"oldController = OLD_CONTROLLER, oldEnvironment = {OLD},",
				"newEnvironment = {NEW}, mapRelation = {R},",
				"oldGoal = OLD_SPEC, newGoal = NEW_SPEC,",
				"revised_on_the_fly, fine_grained, precedence = {}",
				"}");
		M9UpdatingControllerAst ast =
				M9UpdatingControllerAst.resolveForSyntheticTest(
						compile(source), M9UpdatingControllerAst.OFFICIAL_TARGET);
		Assert.assertTrue(ast.getClauseOccurrences().containsKey("precedence"));
		Assert.assertTrue(ast.getPrecedence().isEmpty());
	}

	@Test
	public void keepsTransitionRequirementsOutOfTheControllerGoalRegistry() {
		String source = mappingSource(
				"||UPDATE_CONTROLLER = (UPD).")
				.replace("nonblocking, on_the_fly",
						"transition = TRANSITION_REQ, nonblocking, on_the_fly");
		M9UpdatingControllerAst ast =
				M9UpdatingControllerAst.resolveForSyntheticTest(
						compile(source), M9UpdatingControllerAst.OFFICIAL_TARGET);
		Assert.assertEquals(Arrays.asList("TRANSITION_REQ"),
				ast.getTransitionGoalReferences());
	}

	@Test
	public void rejectsDuplicateAndPartialDefinitionClauses() {
		String duplicate = mappingSource(
				"||UPDATE_CONTROLLER = (UPD).")
				.replace("oldGoal = OLD_SPEC,",
						"oldGoal = OLD_SPEC, oldGoal = OLD_SPEC,");
		expectResolveFailure(duplicate, "more than once");

		String partial = mappingSource(
				"||UPDATE_CONTROLLER = (UPD).")
				.replace("mapping = MAP_ENV,", "oldEnvironment = {OLD},");
		expectResolveFailure(partial, "partial or mixed");
	}

	@Test
	public void rejectsImportedProcessBytesBeforeAnyEndpointMaterialization() {
		String imported = mappingSource(
				"||UPDATE_CONTROLLER = (UPD).")
				.replace("NEW = (a -> NEW).", "import NEW = \"unopened-mutant.aut\"");
		expectResolveFailure(imported, "forbids imported");
	}

	@Test
	public void rejectsParallelAliasAndNonOfficialTarget() {
		String parallel = mappingSource(
				"||UPDATE_CONTROLLER = (UPD || UPD).");
		expectResolveFailure(parallel, "semantic modifier");

		LTSCompiler compiler = compile(mappingSource(
				"||UPDATE_CONTROLLER = (UPD)."));
		try {
			M9UpdatingControllerAst.resolveForSyntheticTest(compiler, "UPD");
			Assert.fail("Expected nonofficial target rejection");
		} catch (IllegalArgumentException expected) {
			Assert.assertTrue(expected.getMessage().contains("Only the registered"));
		}
	}

	private static String mappingSource(String target) {
		return String.join("\n",
				baseDefinitions(),
				"||MAP_ENV = MAP.",
				"updatingController UPD = {",
				"oldController = OLD_CONTROLLER,",
				"mapping = MAP_ENV,",
				"newEnvironment = {NEW},",
				"oldGoal = OLD_SPEC,",
				"newGoal = NEW_SPEC,",
				"nonblocking, on_the_fly",
				"}",
				target);
	}

	private static String baseDefinitions() {
		return String.join("\n",
				"set C = {a}",
				"OLD = (a -> OLD).",
				"NEW = (a -> NEW).",
				"MAP = (a -> MAP).",
				"controllerSpec OLD_SPEC = { controllable = {C} }",
				"controller ||OLD_CONTROLLER = OLD~{OLD_SPEC}.",
				"controllerSpec NEW_SPEC = { controllable = {C} }",
				"controller ||NEW_CONTROLLER = NEW~{NEW_SPEC}.");
	}

	private static void expectResolveFailure(String source, String fragment) {
		try {
			M9UpdatingControllerAst.resolveForSyntheticTest(
					compile(source), M9UpdatingControllerAst.OFFICIAL_TARGET);
			Assert.fail("Expected resolver failure containing " + fragment);
		} catch (IllegalArgumentException expected) {
			Assert.assertTrue(expected.getMessage(),
					expected.getMessage().contains(fragment));
		}
	}

	private static LTSCompiler compile(String source) {
		LTSCompiler compiler = new LTSCompiler(
				new LTSInputString(source), new EmptyLTSOuput(), ".");
		compiler.compile();
		return compiler;
	}
}
