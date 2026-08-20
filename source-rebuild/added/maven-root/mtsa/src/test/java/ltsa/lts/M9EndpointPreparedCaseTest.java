package ltsa.lts;

import MTSSynthesis.ar.dc.uba.model.condition.Fluent;
import ltsa.dispatcher.TransitionSystemDispatcher;
import ltsa.updatingControllers.export.TraditionalPreGrSnapshot;
import ltsa.updatingControllers.export.TraditionalPreGrSnapshotHook;
import org.junit.Assert;
import org.testng.annotations.Test;

import java.lang.reflect.Field;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.List;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;

@Test(singleThreaded = true)
public class M9EndpointPreparedCaseTest {
	@Test
	public void preparesOneOwnedParseAndConsumesOnlyWithDispatcherCapability()
			throws Exception {
		M9EndpointPreparedCase prepared =
				M9EndpointPreparedCase.prepareOfficial(completeSource());
		Assert.assertEquals(
				Arrays.asList("NEW_B", "NEW_A"),
				prepared.getAst().getNewEndpoint().getEnvironmentReferences());
		try {
			prepared.consume(null);
			Assert.fail("Expected missing dispatcher capability rejection");
		} catch (IllegalArgumentException expected) {
			Assert.assertTrue(expected.getMessage().contains("capability"));
		}

		TransitionSystemDispatcher.M9PreparedCaseAccess access = accessForTest();
		M9EndpointPreparedCase.Materialization materialization =
				prepared.consume(access);
		Assert.assertEquals("M9_ENEW",
				materialization.getMaterializedEnew().getName());
		Assert.assertEquals(
				Arrays.asList("NEW_B", "NEW_A"),
				componentNames(materialization.getMaterializedEnew()));
		Assert.assertEquals("M9_CNEW_SOURCE",
				materialization.getSource().composition.getName());
		Assert.assertEquals(
				Arrays.asList("NEW_B", "NEW_A", "SAFE_B", "SAFE_A"),
				componentNames(materialization.getSource().composition));
		Assert.assertSame(materialization.getGoal(),
				materialization.getSource().goal);
		Assert.assertTrue(materialization.getSource().priorityIsLow);
		Assert.assertFalse(materialization.getSource().makeController);
		Assert.assertEquals(completeSource().getBytes(StandardCharsets.UTF_8).length,
				materialization.getSourceModelSizeBytes());
		Assert.assertEquals(
				hex(completeSource().getBytes(StandardCharsets.UTF_8)),
				materialization.getSourceModelSha256());
		Assert.assertTrue(materialization.getEnewAdmission().isComposed());
		Assert.assertFalse(
				materialization.getEnvironmentPrefix()
						.getExtendedStateToPrefixState().isEmpty());
		List<String> fluentNames = new ArrayList<String>();
		for (Fluent fluent : materialization.getGoal().getFluents()) {
			fluentNames.add(fluent.getName());
		}
		Assert.assertEquals(Arrays.asList("F"), fluentNames);
		try {
			prepared.consume(access);
			Assert.fail("Expected one-use prepared-case rejection");
		} catch (IllegalStateException expected) {
			Assert.assertTrue(expected.getMessage().contains("already"));
		}
	}

	@Test
	public void rejectsExecutableProcessProfilesBeforeEndpointSynthesis() {
		String deterministic = completeSource().replace(
				"NEW_A = (a -> NEW_A | b -> NEW_A).",
				"deterministic NEW_A = (a -> NEW_A | b -> NEW_A).");
		expectFailure(deterministic, "restricted inline");

		String compositeSafety = completeSource().replace(
				"property SAFE_A = (a -> SAFE_A | b -> SAFE_A).",
				"||SAFE_A = (NEW_A).");
		expectFailure(compositeSafety, "executable composite");

		String imported = completeSource().replace(
				"NEW_A = (a -> NEW_A | b -> NEW_A).",
				"import NEW_A = \"must-not-open.aut\"");
		expectFailure(imported, "forbids imported");
	}

	@Test
	public void doesNotCompileAnUnselectedInvalidProcessAndRejectsZeroFluentGoal() {
		M9EndpointPreparedCase prepared = M9EndpointPreparedCase.prepareOfficial(
				"UNSELECTED = MISSING.\n" + completeSource());
		Assert.assertEquals("UPDATE_CONTROLLER",
				prepared.getAst().getAliasPath().get(0));

		String zeroFluent = completeSource()
				.replace("fluent F = <a,b>\n", "")
				.replace("liveness = {F} ", "");
		expectFailure(zeroFluent, "GR guarantee");

		String outsideFluent = completeSource().replace(
				"fluent F = <a,b>", "fluent F = <outside,b>");
		expectFailure(outsideFluent, "outside the source alphabet");

		String permissive = completeSource().replace(
				"controllerSpec NEW_SPEC = { liveness",
				"controllerSpec NEW_SPEC = { permissive liveness");
		expectFailure(permissive, "unsupported ranking profile");

		try {
			M9EndpointPreparedCase.prepareOfficial(
					new byte[]{(byte) 0xc3, (byte) 0x28});
			Assert.fail("Expected malformed UTF-8 rejection");
		} catch (IllegalArgumentException expected) {
			Assert.assertTrue(expected.getMessage().contains("exact UTF-8"));
		}
	}

	@Test
	public void retainsAUnaryEnvironmentAsAnExplicitComposition() throws Exception {
		String unary = completeSource().replace(
				"newEnvironment = {NEW_B, NEW_A}",
				"newEnvironment = {NEW_A}");
		M9EndpointPreparedCase.Materialization materialization =
				M9EndpointPreparedCase.prepareOfficial(unary)
						.consume(accessForTest());
		Assert.assertTrue(materialization.getMaterializedEnew().isComposition());
		Assert.assertEquals(Arrays.asList("NEW_A"),
				componentNames(materialization.getMaterializedEnew()));
	}

	@Test
	public void capturesOneTraditionalPreGrSnapshotWithoutUpdaterGr()
			throws Exception {
		TransitionSystemDispatcher.M9PreparedCaseAccess access = accessForTest();
		M9EndpointPreparedCase.Materialization materialization =
				M9EndpointPreparedCase.prepareOfficial(traditionalPreGrSource())
						.consume(access);
		M9EndpointPreparedCase.prepareOfficial(completeSource());
		materialization.requireTraditionalPreGrEligible(access);
		TraditionalPreGrSnapshotHook.SealedCapture capture =
				materialization.captureTraditionalPreGr(access);
		TraditionalPreGrSnapshot snapshot = capture.getSnapshot();
		Assert.assertNotNull(snapshot);
		Assert.assertEquals(1, capture.getCaptureAttempts());
		Assert.assertEquals(0, capture.getNativeUpdateGrEntries());
		Assert.assertTrue(capture.usesProductionLedger());
		Assert.assertTrue(capture.isAttemptConsumed());
		TraditionalPreGrSnapshot.CompletionSeed seed =
				snapshot.getCompletionSeed();
		Assert.assertNotNull(seed);
		Assert.assertEquals(Collections.singletonList("MAP_OLD_NEW_A"),
				seed.getMappingProduct().getComponentNames());
		Assert.assertEquals(
				new LinkedHashSet<Long>(Arrays.asList(0L, 1L)),
				seed.getMappingProduct().getProductSnapshot().getStates());
		Assert.assertEquals(Collections.singletonList("NEW_A"),
				seed.getNewEnvironment().getComponentNames());
		Assert.assertEquals(Collections.singleton(Long.valueOf(0L)),
				seed.getNewEnvironment().getProductSnapshot().getStates());
		Assert.assertEquals(Collections.singletonList(
				Collections.singletonMap(Integer.valueOf(1), Integer.valueOf(0))),
				seed.getLocalMappingToNew());
		Assert.assertEquals(Collections.singletonMap(
				Long.valueOf(1L), Long.valueOf(0L)),
				seed.getMappingProductToNew());
		Assert.assertEquals(Collections.singletonList(Boolean.FALSE),
				seed.getActionSequenceMarkers());
		Assert.assertFalse(TraditionalPreGrSnapshotHook.isArmed());
		try {
			materialization.captureTraditionalPreGr(access);
			Assert.fail("Expected one-use traditional pre-GR rejection");
		} catch (IllegalStateException expected) {
			Assert.assertTrue(expected.getMessage().contains("already"));
		}
	}

	@Test
	public void rejectsUnsupportedTraditionalAuthority()
			throws Exception {
		TransitionSystemDispatcher.M9PreparedCaseAccess access = accessForTest();
		M9EndpointPreparedCase.Materialization controllerWrapped =
				M9EndpointPreparedCase.prepareOfficial(completeSource())
						.consume(access);
		try {
			controllerWrapped.requireTraditionalPreGrEligible(access);
			Assert.fail("Expected controller-wrapped old authority rejection");
		} catch (IllegalArgumentException expected) {
			Assert.assertTrue(expected.getMessage(),
					expected.getMessage().contains("traditional pre-GR eligible"));
		}

		String legacyMapping = traditionalPreGrSource()
				.replace(
						"relation R = {OLD@OLD = reconfigure -> NEW_A@NEW_A}",
						"MAP = (reconfigure -> MAP | a -> MAP | b -> MAP).\n"
								+ "||MAP_ENV = MAP.")
				.replace(
						"oldEnvironment = {OLD},\n"
								+ "newEnvironment = {NEW_A},\n"
								+ "mapRelation = {R},",
						"mapping = MAP_ENV,\nnewEnvironment = {NEW_A},");
		M9EndpointPreparedCase.Materialization legacy =
				M9EndpointPreparedCase.prepareOfficial(legacyMapping)
						.consume(access);
		try {
			legacy.requireTraditionalPreGrEligible(access);
			Assert.fail("Expected legacy mapping completion authority rejection");
		} catch (IllegalArgumentException expected) {
			Assert.assertTrue(expected.getMessage(),
					expected.getMessage().contains("relational mapping profile"));
		}
	}

	@Test
	public void rejectsTraditionalNamespaceCollisionAndLeafOccurrenceOverflow()
			throws Exception {
		String collision = traditionalPreGrSource().replace(
				"||OLD_CONTROLLER = OLD.",
				"constraint OLD_LAYER = (a || !a)\n"
						+ "||OLD_LAYER = OLD.\n"
						+ "||OLD_CONTROLLER = OLD_LAYER.");
		try {
			M9EndpointPreparedCase.prepareOfficial(collision);
			Assert.fail("Expected constraint/composite namespace collision rejection");
		} catch (RuntimeException expected) {
			Assert.assertTrue(expected.getMessage(),
					expected.getMessage().contains("name already defined")
						|| expected.getMessage().contains("ambiguous"));
		}
		Assert.assertFalse(TraditionalPreGrSnapshotHook.isArmed());

		StringBuilder repeated = new StringBuilder("||OLD_CONTROLLER = (");
		for (int index = 0; index < 63; index++) {
			if (index != 0) repeated.append(" || ");
			repeated.append("OLD");
		}
		repeated.append(").");
		M9EndpointPreparedCase.Materialization overflow =
				M9EndpointPreparedCase.prepareOfficial(
						traditionalPreGrSource().replace(
								"||OLD_CONTROLLER = OLD.", repeated.toString()))
						.consume(accessForTest());
		try {
			overflow.requireTraditionalPreGrEligible(accessForTest());
			Assert.fail("Expected traditional leaf occurrence bound rejection");
		} catch (IllegalArgumentException expected) {
			Assert.assertTrue(expected.getMessage(),
					expected.getMessage().contains("leaf occurrence bound"));
		}
		Assert.assertFalse(TraditionalPreGrSnapshotHook.isArmed());
	}

	private static TransitionSystemDispatcher.M9PreparedCaseAccess accessForTest()
			throws Exception {
		Field field = TransitionSystemDispatcher.class
				.getDeclaredField("M9_PREPARED_CASE_ACCESS");
		field.setAccessible(true);
		return (TransitionSystemDispatcher.M9PreparedCaseAccess) field.get(null);
	}

	private static List<String> componentNames(CompactState state) {
		List<String> result = new ArrayList<String>();
		for (CompactState component : state.components) {
			result.add(component.getName());
		}
		return result;
	}

	private static void expectFailure(String source, String fragment) {
		try {
			M9EndpointPreparedCase.prepareOfficial(source);
			Assert.fail("Expected prepared-case rejection containing " + fragment);
		} catch (IllegalArgumentException expected) {
			Assert.assertTrue(expected.getMessage(),
					expected.getMessage().contains(fragment));
		}
	}

	private static String hex(byte[] source) {
		try {
			byte[] digest = MessageDigest.getInstance("SHA-256").digest(source);
			StringBuilder result = new StringBuilder(64);
			for (byte value : digest) {
				result.append(Character.forDigit((value >>> 4) & 0xf, 16));
				result.append(Character.forDigit(value & 0xf, 16));
			}
			return result.toString();
		} catch (Exception impossible) {
			throw new AssertionError(impossible);
		}
	}

	private static String completeSource() {
		return String.join("\n",
				"set C = {a}",
				"fluent F = <a,b>",
				"OLD = (a -> OLD | b -> OLD).",
				"NEW_A = (a -> NEW_A | b -> NEW_A).",
				"NEW_B = (a -> NEW_B | b -> NEW_B).",
				"MAP = (a -> MAP | b -> MAP).",
				"property SAFE_A = (a -> SAFE_A | b -> SAFE_A).",
				"property SAFE_B = (a -> SAFE_B | b -> SAFE_B).",
				"controllerSpec OLD_SPEC = { controllable = {C} }",
				"controller ||OLD_CONTROLLER = OLD~{OLD_SPEC}.",
				"controllerSpec NEW_SPEC = { liveness = {F} "
						+ "safety = {SAFE_B, SAFE_A} controllable = {C} }",
				"controller ||NEW_CONTROLLER = NEW_A~{NEW_SPEC}.",
				"||MAP_ENV = MAP.",
				"updatingController UPD = {",
				"oldController = OLD_CONTROLLER,",
				"mapping = MAP_ENV,",
				"newEnvironment = {NEW_B, NEW_A},",
				"oldGoal = OLD_SPEC,",
				"newGoal = NEW_SPEC,",
				"nonblocking, on_the_fly",
				"}",
				"||UPDATE_CONTROLLER = (UPD).");
	}

	private static String traditionalPreGrSource() {
		return String.join("\n",
				"set C = {a}",
				"fluent F = <a,b>",
				"OLD = (a -> OLD | b -> OLD).",
				"NEW_A = (a -> NEW_A | b -> NEW_A).",
				"relation R = {OLD@OLD = reconfigure -> NEW_A@NEW_A}",
				"controllerSpec OLD_SPEC = { controllable = {C} }",
				"||OLD_CONTROLLER = OLD.",
				"controllerSpec NEW_SPEC = { liveness = {F} "
						+ "controllable = {C} }",
				"controller ||NEW_CONTROLLER = NEW_A~{NEW_SPEC}.",
				"updatingController UPD = {",
				"oldController = OLD_CONTROLLER,",
				"oldEnvironment = {OLD},",
				"newEnvironment = {NEW_A},",
				"mapRelation = {R},",
				"oldGoal = OLD_SPEC,",
				"newGoal = NEW_SPEC,",
				"nonblocking, on_the_fly",
				"}",
				"||UPDATE_CONTROLLER = (UPD).");
	}
}
