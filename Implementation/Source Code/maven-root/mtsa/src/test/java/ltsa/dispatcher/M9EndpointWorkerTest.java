package ltsa.dispatcher;

import ltsa.updatingControllers.export.M9EndpointReceiptCore;
import org.testng.annotations.Test;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.lang.reflect.Field;
import java.lang.reflect.Constructor;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Set;
import java.util.zip.CRC32;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

import static org.testng.Assert.assertEquals;
import static org.testng.Assert.assertFalse;
import static org.testng.Assert.assertTrue;
import static org.testng.Assert.fail;

@Test(singleThreaded = true)
public class M9EndpointWorkerTest {
	@Test
	public void exposesOnlyOnePublicCliAndUsesTheAcyclicReceiptHashSchema()
			throws Exception {
		Set<String> publicMethods = new LinkedHashSet<String>();
		for (Method method : M9EndpointWorker.class.getDeclaredMethods()) {
			if (Modifier.isPublic(method.getModifiers())) {
				publicMethods.add(method.getName() + Arrays.toString(method.getParameterTypes()));
			}
		}
		assertEquals(publicMethods, Collections.singleton(
				"main[class [Ljava.lang.String;]"));

		Set<String> keys = M9EndpointReceiptCore.Bindings
				.requiredSha256BindingKeys();
		assertEquals(keys.size(), 24);
		assertTrue(keys.contains("endpoint_attempt_plan_sha256"));
		assertTrue(keys.contains("selected_translation_source_sha256"));
		assertTrue(keys.contains("t1_protocol_sha256"));
		assertTrue(keys.contains("worker_java_executable_sha256"));
		assertFalse(keys.contains("predecision_case_contract_sha256"));
		assertFalse(keys.contains("source_model_sha256"));
		assertFalse(keys.contains("t1_plan_sha256"));
		assertFalse(keys.contains("worker_java_runtime_sha256"));

		Field profilesField = M9EndpointWorker.class.getDeclaredField("CASES");
		profilesField.setAccessible(true);
		@SuppressWarnings("unchecked")
		Map<String, M9EndpointWorker.CaseProfile> profiles =
				(Map<String, M9EndpointWorker.CaseProfile>) profilesField.get(null);
		M9EndpointWorker.CaseProfile first = profiles.get(
				"uav_unexpected_goal_change");
		assertEquals(first.selectedBindingsSha256(),
				"a5000a6e93c76b78b3adebb80489ba5c1685092e7c636ac36bbc45dbdc4be9ee");
		assertEquals(first.totalSourceBytes(), 71593L);
	}

	@Test
	public void reflectivelyConstructedPreparedCaseTokenIsNotTheSingleton()
			throws Exception {
		Constructor<TransitionSystemDispatcher.M9PreparedCaseAccess> constructor =
				TransitionSystemDispatcher.M9PreparedCaseAccess.class
						.getDeclaredConstructor();
		constructor.setAccessible(true);
		TransitionSystemDispatcher.M9PreparedCaseAccess forged =
				constructor.newInstance();
		assertFalse(TransitionSystemDispatcher
				.isRegisteredM9PreparedCaseAccess(forged));
	}

	@Test
	public void exactJsonParserRejectsDuplicateWhitespaceAndNumericDomainMutants()
			throws Exception {
		Method parser = M9EndpointWorker.class.getDeclaredMethod(
				"parseCanonicalObject", byte[].class, String.class);
		parser.setAccessible(true);
		@SuppressWarnings("unchecked")
		Map<String, Object> parsed = (Map<String, Object>) parser.invoke(
				null, "{\"a\":1}\n".getBytes(StandardCharsets.UTF_8), "TEST");
		assertEquals(parsed.get("a"), Long.valueOf(1L));
		for (String mutant : Arrays.asList(
				"{\"a\":1,\"a\":2}\n",
				"{ \"a\":1}\n",
				"{\"a\":1.0}\n",
				"{\"a\":1}")) {
			expectInvocationFailure(parser,
					new Object[]{mutant.getBytes(StandardCharsets.UTF_8), "TEST"});
		}
	}

	@Test
	public void syntheticZipScannerRetainsOnlyRegisteredRowsAndRejectsTraversal()
			throws Exception {
		byte[] oldBytes = "old".getBytes(StandardCharsets.US_ASCII);
		byte[] newBytes = "new-source".getBytes(StandardCharsets.US_ASCII);
		M9EndpointWorker.SourceRow oldRow = new M9EndpointWorker.SourceRow(
				"old_model", "root/old.lts", sha256(oldBytes), oldBytes.length,
				crc32(oldBytes));
		M9EndpointWorker.SourceRow newRow = new M9EndpointWorker.SourceRow(
				"new_model", "root/new.lts", sha256(newBytes), newBytes.length,
				crc32(newBytes));
		M9EndpointWorker.CaseProfile profile = new M9EndpointWorker.CaseProfile(
				"synthetic_case", Arrays.asList(oldRow, newRow));
		byte[] archive = zip(new String[]{"root/", "root/old.lts", "root/new.lts"},
				new byte[][]{new byte[0], oldBytes, newBytes});
		Method scanner = M9EndpointWorker.class.getDeclaredMethod(
				"scanSelectedArchive", byte[].class,
				M9EndpointWorker.CaseProfile.class, Integer.TYPE, Integer.TYPE, Long.TYPE);
		scanner.setAccessible(true);
		Object selected = scanner.invoke(
				null, archive, profile, Integer.valueOf(3), Integer.valueOf(2),
				Long.valueOf(oldBytes.length + newBytes.length));
		Field newSource = selected.getClass().getDeclaredField("newSource");
		newSource.setAccessible(true);
		assertEquals((byte[]) newSource.get(selected), newBytes);

		byte[] traversal = zip(
				new String[]{"root/", "root/old.lts", "root/new.lts", "../escape"},
				new byte[][]{new byte[0], oldBytes, newBytes, new byte[]{1}});
		expectInvocationFailure(scanner, new Object[]{
				traversal, profile, Integer.valueOf(4), Integer.valueOf(3),
				Long.valueOf(oldBytes.length + newBytes.length + 1L),
		});
	}

	@Test
	public void invalidCliNeverReachesTheBridgeAndEmitsOnlyAReasonCode() {
		PrintStream original = System.err;
		ByteArrayOutputStream captured = new ByteArrayOutputStream();
		try {
			System.setErr(new PrintStream(captured));
			assertEquals(M9EndpointWorker.runMain(new String[0]), 2);
		} finally {
			System.setErr(original);
		}
		assertEquals(new String(captured.toByteArray(), StandardCharsets.US_ASCII),
				"M9_ENDPOINT_WORKER_FAILURE:ARGUMENT_CENSUS\n");
	}

	@Test
	public void lexicalDotSegmentsAreRejectedBeforeAnyControlRead() {
		Path mutant = Paths.get(System.getProperty("user.dir"), "mutant", "..",
				"ENDPOINT_PLAN.json");
		PrintStream original = System.err;
		ByteArrayOutputStream captured = new ByteArrayOutputStream();
		try {
			System.setErr(new PrintStream(captured));
			assertEquals(M9EndpointWorker.runMain(
					new String[]{mutant.toString()}), 2);
		} finally {
			System.setErr(original);
		}
		assertEquals(new String(captured.toByteArray(), StandardCharsets.US_ASCII),
				"M9_ENDPOINT_WORKER_FAILURE:CONTROL_PATH\n");
	}

	@Test
	public void attemptDirectoryAuthorityBindsExactDeviceAndInode()
			throws Exception {
		Path directory = Files.createTempDirectory("m9-worker-directory-");
		try {
			Map<String, Object> identity = Files.readAttributes(
					directory, "unix:dev,ino", LinkOption.NOFOLLOW_LINKS);
			long device = ((Number) identity.get("dev")).longValue();
			long inode = ((Number) identity.get("ino")).longValue();
			Method verifier = M9EndpointWorker.class.getDeclaredMethod(
					"requireAttemptDirectoryIdentity",
					Path.class, Long.TYPE, Long.TYPE);
			verifier.setAccessible(true);
			verifier.invoke(null, directory, device, inode);
			expectInvocationFailure(
					verifier, new Object[]{directory, device, inode + 1L});
		} finally {
			Files.deleteIfExists(directory);
		}
	}

	private static void expectInvocationFailure(Method method, Object[] arguments)
			throws Exception {
		try {
			method.invoke(null, arguments);
			fail("expected fail-closed worker rejection");
		} catch (InvocationTargetException expected) {
			assertTrue(expected.getCause() instanceof IllegalArgumentException,
					String.valueOf(expected.getCause()));
		}
	}

	private static byte[] zip(String[] names, byte[][] payloads) throws Exception {
		ByteArrayOutputStream bytes = new ByteArrayOutputStream();
		ZipOutputStream archive = new ZipOutputStream(bytes, StandardCharsets.UTF_8);
		for (int index = 0; index < names.length; index++) {
			ZipEntry entry = new ZipEntry(names[index]);
			archive.putNextEntry(entry);
			archive.write(payloads[index]);
			archive.closeEntry();
		}
		archive.finish();
		archive.close();
		return bytes.toByteArray();
	}

	private static String sha256(byte[] value) throws Exception {
		return hex(MessageDigest.getInstance("SHA-256").digest(value));
	}

	private static String crc32(byte[] value) {
		CRC32 crc = new CRC32();
		crc.update(value);
		return String.format("%08x", crc.getValue());
	}

	private static String hex(byte[] value) {
		StringBuilder result = new StringBuilder(value.length * 2);
		for (byte element : value) result.append(String.format("%02x", element & 0xff));
		return result.toString();
	}
}
