package ltsa.dispatcher;

import ltsa.MultiCore.ComputerOptions;
import ltsa.lts.M9EndpointPreparedCase;
import ltsa.updatingControllers.export.M9EndpointReceiptBundle;
import ltsa.updatingControllers.export.M9EndpointReceiptCore;
import org.json.simple.parser.JSONParser;
import org.json.simple.parser.ParseException;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.io.PrintStream;
import java.lang.management.ManagementFactory;
import java.net.JarURLConnection;
import java.net.URI;
import java.net.URL;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.channels.SeekableByteChannel;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.nio.file.DirectoryStream;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.OpenOption;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.SecureDirectoryStream;
import java.nio.file.StandardOpenOption;
import java.nio.file.attribute.BasicFileAttributeView;
import java.nio.file.attribute.BasicFileAttributes;
import java.nio.file.attribute.PosixFilePermission;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Comparator;
import java.util.Enumeration;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.Vector;
import java.util.zip.CRC32;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

/**
 * Fresh-process, one-shot entry for the registered UAV endpoint translation.
 *
 * <p>This class deliberately exposes no graph, hook, receipt core, or retry
 * seam.  It authenticates one canonical attempt plan and its durable T1 claim,
 * validates the exact single-JAR/no-agent runtime, reads only the registered
 * archive after that claim, prepares one source exactly once, invokes the
 * package-local bridge exactly once, and reports only a candidate bundle.  An
 * independent decoder and the outer transaction ledger remain responsible for
 * the final predecision PASS.</p>
 */
public final class M9EndpointWorker {
	private static final String CONTROL_NAME = "ENDPOINT_PLAN.json";
	private static final String CLAIM_NAME = "CLAIM.json";
	private static final String STARTED_NAME = "WORKER_STARTED.json";
	private static final String INVOKED_NAME = "WORKER_INVOKED.json";
	private static final String ENTERED_NAME = "WORKER_ENTERED.json";
	private static final String RUN_NAME = "RUN.json";
	private static final String PENDING_NAME = "endpoint-receipt.bundle.pending";
	private static final String RECEIPT_NAME = "endpoint-receipt.bundle";
	private static final String CONTROL_SCHEMA = "m9-endpoint-worker-control-v1";
	private static final String PLAN_SCHEMA = "m9-endpoint-attempt-plan-v1";
	private static final String CANONICALIZATION = "fse2027-canonical-json-v1";
	private static final String RUN_SCHEMA = "m9-t1-run-root-v1";
	private static final String CLAIM_SCHEMA = "m9-t1-attempt-claim-v1";
	private static final String RUN_STATUS = "READY_AFTER_VERIFIED_T1";
	private static final String CLAIM_STATUS =
			"CONSUMED_BEFORE_SELECTED_SOURCE_OPEN";
	private static final String CLUSTER = "uav_morph_taas2022";
	private static final String CLASSIFICATION =
			"SOURCE_ANCHORED_AUTHOR_FINITE_PROJECTION";
	private static final String PROJECTION_KIND =
			"uav_native_endpoint_pre_gr_v2";
	private static final String FINITE_PROFILE =
			"uav_mtsa_native_endpoint_pre_gr_v2";
	private static final String LAUNCH_PROFILE =
			"m9-java17-single-shaded-jar-no-agent-single-thread-v1";
	private static final String RUN_ROOT_NAME =
			"m9-source-contract-panel-run-20260811e";
	private static final Path RUN_RELATIVE_PATH = Paths.get(
			"Implementation", "Experiment", "FSE2027", "results",
			RUN_ROOT_NAME);
	private static final String T1_EVIDENCE_PATH =
			"Implementation/Experiment/FSE2027/results/"
			+ "m9-source-contract-panel-t1-20260811d";
	private static final Instant T0_CREATION_UPPER_BOUND =
			Instant.parse("2026-08-11T05:14:40Z");
	private static final String ARCHIVE_SHA256 =
			"01cc5b7ffefe6ca8c2030a917b71acb1f16166bccf29e0f169630d4e45997728";
	private static final long ARCHIVE_SIZE = 21573L;
	private static final int ARCHIVE_ENTRY_COUNT = 11;
	private static final int ARCHIVE_FILE_COUNT = 10;
	private static final long ARCHIVE_UNCOMPRESSED_SIZE = 113762L;
	private static final long MAX_CONTROL_BYTES = 256L * 1024L;
	private static final long MAX_CLAIM_BYTES = 1024L * 1024L;
	private static final long MAX_ARCHIVE_BYTES = 64L * 1024L * 1024L;
	private static final long MAX_ZIP_ENTRY_BYTES = 16L * 1024L * 1024L;
	private static final long MAX_ZIP_TOTAL_BYTES = 64L * 1024L * 1024L;
	private static final int MAX_ZIP_ENTRIES = 128;
	private static final long MAX_CAPTURED_OUTPUT_BYTES = 1024L * 1024L;
	private static final Set<String> DERIVED_HASH_KEYS = Collections.unmodifiableSet(
			new LinkedHashSet<String>(Arrays.asList(
					"attempt_claim_sha256", "endpoint_attempt_plan_sha256")));
	private static final Set<String> RECEIPT_HASH_CORE_KEYS;
	private static final Set<String> EXACT_VM_ARGUMENTS = Collections.unmodifiableSet(
			new LinkedHashSet<String>(Arrays.asList(
					"-Xms256m", "-Xmx4g", "-Djava.awt.headless=true",
					"-XX:+DisableAttachMechanism", "-XX:ActiveProcessorCount=1")));
	private static final Set<String> FORBIDDEN_ENVIRONMENT =
			Collections.unmodifiableSet(new LinkedHashSet<String>(Arrays.asList(
					"JAVA_TOOL_OPTIONS", "JDK_JAVA_OPTIONS", "_JAVA_OPTIONS",
					"CLASSPATH", "DYLD_INSERT_LIBRARIES", "DYLD_LIBRARY_PATH",
					"DYLD_FRAMEWORK_PATH", "LD_PRELOAD", "LD_LIBRARY_PATH")));
	private static final String T0_PROTOCOL =
			"0000000000000000000000000000000000000000000000000000000000000000";
	private static final String T0_PAYLOAD =
			"0000000000000000000000000000000000000000000000000000000000000000";
	private static final String T0_RESPONSE =
			"3f8761501ccbf8a6062024cec6370834b8fce723c796a8114656feb261a5aa48";
	private static final String T0_VERIFICATION =
			"9334b0609992feac05daedf79470837c787bd7e333ee11e6341cebd2faccce21";
	private static final String T0_SEAL =
			"41c5840addbb50e8c1d0277b4efb1b3fff5a1066421a23938b89228844f7a1b6";
	private static final String INTAKE_MANIFEST =
			"cba3ef3bd91e238d9843961a61375bc24a32534b9784f6ccb0a49dae033e81eb";
	private static final String INTAKE_SUMMARY =
			"b3ac47b9f8f8a09e4026c934d705c082610cf04bfc45adadcc7b76bf5857b1d5";
	private static final String INTAKE_SEAL =
			"9c15e1f6f13e1f003dba4f2cf63eec46f8a3d501cdf483105a97e5c65e60924a";
	private static final Map<String, CaseProfile> CASES;

	static {
		Set<String> keys = new LinkedHashSet<String>(
				M9EndpointReceiptCore.Bindings.requiredSha256BindingKeys());
		keys.removeAll(DERIVED_HASH_KEYS);
		RECEIPT_HASH_CORE_KEYS = Collections.unmodifiableSet(keys);
		Map<String, CaseProfile> cases = new LinkedHashMap<String, CaseProfile>();
		cases.put("uav_unexpected_goal_change", new CaseProfile(
				"uav_unexpected_goal_change",
				Arrays.asList(
						new SourceRow("old_model",
								"especificaciones/unexpected_goal_change--original.lts",
								"5a2f762a3418389da4a034153d85b82b8a7bf7acbdcf90588343019d8529464f",
								34589L, "9d7e6c74"),
						new SourceRow("new_model",
								"especificaciones/unexpected_goal_change--update.lts",
								"5883505c04cd1d5a0bc3afa3f97c5ec1bca786f958875ca11687f792daca0a7b",
								37004L, "7bf51294"))));
		cases.put("uav_unexpected_search_and_rescue", new CaseProfile(
				"uav_unexpected_search_and_rescue",
				Arrays.asList(
						new SourceRow("old_model",
								"especificaciones/unexpected_search_and_rescue--original.lts",
								"bfaf4c9ac7a45f6f650dbf92cd874cd31568941555d399f8a875307e44cd4eaf",
								8913L, "e8bbbb76"),
						new SourceRow("new_model",
								"especificaciones/unexpected_search_and_rescue--update.lts",
								"a7543a3516080dfb00f5ca9bb9db4ad9ead54acaf2ba7e185f4a9e0672b141c1",
								11094L, "b2a7109d"),
						new SourceRow("operational_code",
								"especificaciones/planner_PersonSensor.py",
								"4739101341ef00251b9b45ef367d5bbcbb3ccd319f4b5eeeee00c48daab9497d",
								1770L, "0d869416"))));
		CASES = Collections.unmodifiableMap(cases);
	}

	private M9EndpointWorker() {
	}

	public static void main(String[] arguments) {
		int result = runMain(arguments);
		if (result != 0) System.exit(result);
	}

	static int runMain(String[] arguments) {
		try {
			if (arguments == null || arguments.length != 1) {
				throw new WorkerFailure("ARGUMENT_CENSUS");
			}
			Path controlPath = Paths.get(arguments[0]);
			Control control = loadControl(controlPath);
			requireAttemptDirectoryIdentity(control);
			RuntimeAuthority runtime = validateRuntime(control.hashCore);
			String enteredSha = claimWorkerEntry(control);
			requireAttemptDirectoryIdentity(control);
			M9EndpointReceiptBundle.PublicationTarget target =
					M9EndpointReceiptBundle.prepare(
							control.attemptDirectory.resolve(PENDING_NAME),
							control.attemptDirectory.resolve(RECEIPT_NAME),
							control.profile.caseId, control.attemptId,
							control.claimSha256);
			SelectedSources selected = extractSelectedSources(
					control.archivePath, control.profile);
			M9EndpointReceiptBundle.PublishedReceipt published;
			byte[] newSource = selected.newSource;
			try {
				M9EndpointPreparedCase prepared =
						M9EndpointPreparedCase.prepareOfficial(newSource);
				M9EndpointReceiptCore.Bindings bindings =
						M9EndpointReceiptCore.Bindings.capture(
								control.profile.caseId, CLUSTER, control.attemptId,
								CLASSIFICATION, PROJECTION_KIND, FINITE_PROFILE,
								control.profile.sources.size(),
								control.profile.totalSourceBytes(), control.fullHashes);
				BoundedOutput capturedOut = new BoundedOutput(MAX_CAPTURED_OUTPUT_BYTES);
				BoundedOutput capturedErr = new BoundedOutput(MAX_CAPTURED_OUTPUT_BYTES);
				PrintStream originalOut = System.out;
				PrintStream originalErr = System.err;
				try {
					System.setOut(new PrintStream(capturedOut, true, "UTF-8"));
					System.setErr(new PrintStream(capturedErr, true, "UTF-8"));
					published = M9EndpointMaterializerBridge
							.synthesiseValidateSealAndPublishOnce(
									prepared, bindings, target);
				} finally {
					System.setOut(originalOut);
					System.setErr(originalErr);
				}
				if (capturedOut.size() != 0 || capturedErr.size() != 0
						|| capturedOut.isOverflowed() || capturedErr.isOverflowed()) {
					throw new WorkerFailure("UNEXPECTED_NATIVE_OUTPUT");
				}
			} finally {
				Arrays.fill(newSource, (byte) 0);
				selected.clearOtherSources();
			}
			requireAttemptDirectoryIdentity(control);
			System.out.print(candidateReport(control, published, runtime, enteredSha));
			System.out.flush();
			return 0;
		} catch (Throwable failure) {
			if (failure instanceof ThreadDeath) throw (ThreadDeath) failure;
			String code = failure instanceof WorkerFailure
					? ((WorkerFailure) failure).code : "TERMINAL_FAILURE";
			try {
				System.err.print("M9_ENDPOINT_WORKER_FAILURE:" + code + "\n");
				System.err.flush();
			} catch (Throwable ignored) {
				// The outer durable attempt claim still records process failure.
			}
			return 2;
		}
	}

	private static Control loadControl(Path supplied) throws Exception {
		Path absolute = supplied.toAbsolutePath().normalize();
		if (!supplied.isAbsolute() || !supplied.equals(absolute)
				|| absolute.getFileName() == null
				|| !CONTROL_NAME.equals(absolute.getFileName().toString())) {
			throw new WorkerFailure("CONTROL_PATH");
		}
		String absoluteText = absolute.toString();
		for (int index = 0; index < absoluteText.length(); index++) {
			char value = absoluteText.charAt(index);
			if (value < 0x21 || value > 0x7e) {
				throw new WorkerFailure("CONTROL_PATH");
			}
		}
		Path attempt = absolute.getParent();
		if (attempt == null || attempt.getParent() == null
				|| attempt.getParent().getFileName() == null
				|| !"attempts".equals(attempt.getParent().getFileName().toString())
				|| attempt.getParent().getParent() == null
				|| attempt.getParent().getParent().getFileName() == null
				|| !RUN_ROOT_NAME.equals(
						attempt.getParent().getParent().getFileName().toString())) {
			throw new WorkerFailure("CONTROL_LOCATION");
		}
		Path executionRoot = Paths.get(System.getProperty("user.dir", ""))
				.toAbsolutePath().normalize();
		Path registeredRunRoot = executionRoot.resolve(RUN_RELATIVE_PATH).normalize();
		if (!attempt.getParent().getParent().equals(registeredRunRoot)) {
			throw new WorkerFailure("CONTROL_EXECUTION_ROOT");
		}
		requirePrivateDirectory(attempt);
		byte[] raw = readSecureFile(absolute, MAX_CONTROL_BYTES, "CONTROL_READ");
		String controlSha = sha256(raw);
		Map<String, Object> root = parseCanonicalObject(raw, "CONTROL_JSON");
		requireKeys(root, setOf(
				"canonicalization", "endpoint_attempt_plan",
				"receipt_hash_bindings", "schema_version"), "CONTROL_FIELDS");
		if (!CONTROL_SCHEMA.equals(string(root.get("schema_version")))
				|| !CANONICALIZATION.equals(string(root.get("canonicalization")))) {
			throw new WorkerFailure("CONTROL_PROFILE");
		}
		Map<String, Object> plan = object(root.get("endpoint_attempt_plan"));
		Map<String, String> core = hashMap(root.get("receipt_hash_bindings"),
				RECEIPT_HASH_CORE_KEYS, "HASH_CORE");
		String coreSha = sha256(canonicalBytes(core));
		requireKeys(plan, setOf(
				"archive", "attempt_id", "case_id", "classification", "cluster_id",
				"finite_semantics_profile_id", "launch_profile_id", "projection_kind",
				"receipt_hash_bindings_sha256", "schema_version",
				"selected_source_bindings_sha256", "selected_sources"), "PLAN_FIELDS");
		String caseId = string(plan.get("case_id"));
		CaseProfile profile = CASES.get(caseId);
		if (profile == null || !caseId.equals(attempt.getFileName().toString())
				|| !absolute.equals(registeredRunRoot.resolve("attempts")
						.resolve(caseId).resolve(CONTROL_NAME))
				|| !PLAN_SCHEMA.equals(string(plan.get("schema_version")))
				|| !CLUSTER.equals(string(plan.get("cluster_id")))
				|| !"attempt-0001".equals(string(plan.get("attempt_id")))
				|| !CLASSIFICATION.equals(string(plan.get("classification")))
				|| !PROJECTION_KIND.equals(string(plan.get("projection_kind")))
				|| !FINITE_PROFILE.equals(
						string(plan.get("finite_semantics_profile_id")))
				|| !LAUNCH_PROFILE.equals(string(plan.get("launch_profile_id")))
				|| !coreSha.equals(string(plan.get("receipt_hash_bindings_sha256")))) {
			throw new WorkerFailure("PLAN_PROFILE");
		}
		profile.requireSelectedRows(plan.get("selected_sources"));
		String selectedSha = profile.selectedBindingsSha256();
		if (!selectedSha.equals(string(plan.get("selected_source_bindings_sha256")))
				|| !selectedSha.equals(core.get("selected_source_bindings_sha256"))
				|| !profile.newSource().sha256.equals(
						core.get("selected_translation_source_sha256"))) {
			throw new WorkerFailure("SOURCE_BINDING");
		}
		Map<String, Object> archive = object(plan.get("archive"));
		requireKeys(archive, setOf(
				"entry_count", "file_count", "path", "sha256", "size_bytes",
				"uncompressed_size_bytes"), "ARCHIVE_FIELDS");
		Path archivePath = Paths.get(string(archive.get("path")));
		if (!archivePath.isAbsolute()
				|| !archivePath.normalize().equals(archivePath)
				|| !ARCHIVE_SHA256.equals(string(archive.get("sha256")))
				|| number(archive.get("size_bytes")) != ARCHIVE_SIZE
				|| number(archive.get("entry_count")) != ARCHIVE_ENTRY_COUNT
				|| number(archive.get("file_count")) != ARCHIVE_FILE_COUNT
				|| number(archive.get("uncompressed_size_bytes"))
						!= ARCHIVE_UNCOMPRESSED_SIZE) {
			throw new WorkerFailure("ARCHIVE_PROFILE");
		}
		String planSha = sha256(canonicalBytes(plan));
		Path claimPath = attempt.resolve(CLAIM_NAME);
		byte[] claimRaw = readSecureFile(claimPath, MAX_CLAIM_BYTES, "CLAIM_READ");
		Map<String, Object> claim = parseCanonicalObject(claimRaw, "CLAIM_JSON");
		requireKeys(claim, setOf(
				"attempt_number", "binding", "case_id", "retry_allowed",
				"schema_version", "status"), "CLAIM_FIELDS");
		Map<String, Object> claimBinding = object(claim.get("binding"));
		requireKeys(claimBinding, setOf(
				"case_plan_sha256", "endpoint_attempt_plan_sha256",
				"t1_seal_sha256"), "CLAIM_BINDING_FIELDS");
		if (!CLAIM_SCHEMA.equals(string(claim.get("schema_version")))
				|| !CLAIM_STATUS.equals(string(claim.get("status")))
				|| !caseId.equals(string(claim.get("case_id")))
				|| number(claim.get("attempt_number")) != 1L
				|| !Boolean.FALSE.equals(claim.get("retry_allowed"))
				|| !planSha.equals(string(
						claimBinding.get("endpoint_attempt_plan_sha256")))
				|| !core.get("case_plan_sha256").equals(
						string(claimBinding.get("case_plan_sha256")))
				|| !core.get("t1_seal_sha256").equals(
						string(claimBinding.get("t1_seal_sha256")))) {
			throw new WorkerFailure("CLAIM_BINDING");
		}
		String claimSha = sha256(claimRaw);
		Map<String, String> full = new TreeMap<String, String>(core);
		full.put("attempt_claim_sha256", claimSha);
		full.put("endpoint_attempt_plan_sha256", planSha);
		if (!full.keySet().equals(
				M9EndpointReceiptCore.Bindings.requiredSha256BindingKeys())) {
			throw new WorkerFailure("RECEIPT_HASH_CENSUS");
		}
		validateFixedHashes(full);
		String runSha = validateRunRoot(
				attempt.getParent().getParent(), caseId, full);
		StartAuthority started = validateWorkerStart(
				attempt, caseId, claimSha, controlSha, planSha, runSha, full);
		String invokedSha = validateWorkerInvocation(
				attempt, caseId, started.sha256);
		requireAttemptInventory(attempt, setOf(
				CLAIM_NAME, CONTROL_NAME, STARTED_NAME, INVOKED_NAME));
		return new Control(attempt, archivePath, profile, "attempt-0001",
				claimSha, controlSha, planSha, runSha, started.sha256, invokedSha,
				started.directoryDevice, started.directoryInode,
				Collections.unmodifiableMap(full), Collections.unmodifiableMap(core));
	}

	private static String claimWorkerEntry(Control control) throws Exception {
		requireAttemptDirectoryIdentity(control);
		requireAttemptInventory(control.attemptDirectory, setOf(
				CLAIM_NAME, CONTROL_NAME, STARTED_NAME, INVOKED_NAME));
		Map<String, Object> entry = new TreeMap<String, Object>();
		entry.put("attempt_id", control.attemptId);
		entry.put("case_id", control.profile.caseId);
		entry.put("retry_allowed", Boolean.FALSE);
		entry.put("schema_version", "m9-endpoint-worker-entry-v1");
		entry.put("status", "WORKER_SOURCE_OPEN_IRREVERSIBLY_CONSUMED");
		entry.put("worker_invocation_sha256", control.invokedSha256);
		byte[] payload = canonicalBytes(entry);
		Path path = control.attemptDirectory.resolve(ENTERED_NAME);
		try (FileChannel channel = FileChannel.open(
				path, StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE)) {
			ByteBuffer buffer = ByteBuffer.wrap(payload);
			while (buffer.hasRemaining()) channel.write(buffer);
			channel.force(true);
		}
		Set<PosixFilePermission> expectedPermissions = new HashSet<PosixFilePermission>(
				Arrays.asList(PosixFilePermission.OWNER_READ,
						PosixFilePermission.OWNER_WRITE));
		if (!Files.getPosixFilePermissions(path, LinkOption.NOFOLLOW_LINKS)
				.equals(expectedPermissions)) {
			throw new WorkerFailure("WORKER_ENTRY_MODE");
		}
		try (FileChannel directory = FileChannel.open(
				control.attemptDirectory, StandardOpenOption.READ)) {
			directory.force(true);
		}
		if (!Arrays.equals(readSecureFile(
				path, MAX_CLAIM_BYTES, "WORKER_ENTRY_STABILITY"), payload)) {
			throw new WorkerFailure("WORKER_ENTRY_STABILITY");
		}
		requireAttemptInventory(control.attemptDirectory, setOf(
				CLAIM_NAME, CONTROL_NAME, STARTED_NAME, INVOKED_NAME, ENTERED_NAME));
		requireAttemptDirectoryIdentity(control);
		return sha256(payload);
	}

	private static String validateRunRoot(
			Path runRoot, String caseId, Map<String, String> hashes) throws Exception {
		byte[] raw = readSecureFile(runRoot.resolve(RUN_NAME), MAX_CLAIM_BYTES,
				"RUN_READ");
		Map<String, Object> run = parseCanonicalObject(raw, "RUN_JSON");
		requireKeys(run, setOf(
				"first_case_id", "schema_version", "status", "t1_binding"),
				"RUN_FIELDS");
		Map<String, Object> binding = object(run.get("t1_binding"));
		requireKeys(binding, setOf(
				"creation_time_lower_bound_utc", "creation_time_upper_bound_utc",
				"evidence_path", "payload_sha256", "protocol_sha256",
				"response_sha256", "seal_sha256", "verification_sha256"),
				"RUN_BINDING_FIELDS");
		String lowerText = string(binding.get("creation_time_lower_bound_utc"));
		String upperText = string(binding.get("creation_time_upper_bound_utc"));
		Instant lower;
		Instant upper;
		try {
			lower = Instant.parse(lowerText);
			upper = Instant.parse(upperText);
		} catch (RuntimeException invalidTime) {
			throw new WorkerFailure("RUN_TIME_BINDING");
		}
		if (!lower.toString().equals(lowerText) || !upper.toString().equals(upperText)
				|| lower.isAfter(upper) || lower.isBefore(T0_CREATION_UPPER_BOUND)) {
			throw new WorkerFailure("RUN_TIME_BINDING");
		}
		if (!RUN_SCHEMA.equals(string(run.get("schema_version")))
				|| !RUN_STATUS.equals(string(run.get("status")))
				|| !"uav_unexpected_goal_change".equals(
						string(run.get("first_case_id")))
				|| !hashes.get("t1_protocol_sha256").equals(
						string(binding.get("protocol_sha256")))
				|| !hashes.get("t1_payload_sha256").equals(
						string(binding.get("payload_sha256")))
				|| !hashes.get("t1_response_sha256").equals(
						string(binding.get("response_sha256")))
				|| !hashes.get("t1_verification_sha256").equals(
						string(binding.get("verification_sha256")))
				|| !hashes.get("t1_seal_sha256").equals(
						string(binding.get("seal_sha256")))
				|| !T1_EVIDENCE_PATH.equals(string(binding.get("evidence_path")))) {
			throw new WorkerFailure("RUN_BINDING");
		}
		if (caseId.equals("uav_unexpected_goal_change")
				&& !caseId.equals(string(run.get("first_case_id")))) {
			throw new WorkerFailure("FIRST_CASE_BINDING");
		}
		return sha256(raw);
	}

	private static StartAuthority validateWorkerStart(
			Path attempt, String caseId, String claimSha, String controlSha,
			String planSha, String runSha, Map<String, String> hashes)
			throws Exception {
		byte[] raw = readSecureFile(
				attempt.resolve(STARTED_NAME), MAX_CLAIM_BYTES, "WORKER_START_READ");
		Map<String, Object> start = parseCanonicalObject(raw, "WORKER_START_JSON");
		requireKeys(start, setOf(
				"attempt_claim_sha256", "attempt_id", "case_id",
				"endpoint_attempt_plan_sha256", "endpoint_control_sha256",
				"launch_contract", "launch_contract_sha256", "launch_profile_id",
				"materializer_jar_sha256", "retry_allowed",
				"run_record_sha256", "schema_version", "status",
				"t1_transaction_claim_sha256",
				"t1_transaction_terminal_sha256",
				"worker_entrypoint_sha256", "worker_java_executable_sha256"),
				"WORKER_START_FIELDS");
		String transactionClaim = string(
				start.get("t1_transaction_claim_sha256"));
		String transactionTerminal = string(
				start.get("t1_transaction_terminal_sha256"));
		Map<String, Object> launchContract = object(start.get("launch_contract"));
		String launchContractSha = string(start.get("launch_contract_sha256"));
		if (!transactionClaim.matches("[0-9a-f]{64}")
				|| !transactionTerminal.matches("[0-9a-f]{64}")
				|| !launchContractSha.matches("[0-9a-f]{64}")
				|| !launchContractSha.equals(sha256(canonicalBytes(launchContract)))
				|| !"m9-endpoint-worker-start-v1".equals(
						string(start.get("schema_version")))
				|| !"WORKER_INVOCATION_IRREVERSIBLY_CONSUMED".equals(
						string(start.get("status")))
				|| !caseId.equals(string(start.get("case_id")))
				|| !"attempt-0001".equals(string(start.get("attempt_id")))
				|| !claimSha.equals(string(start.get("attempt_claim_sha256")))
				|| !controlSha.equals(string(start.get("endpoint_control_sha256")))
				|| !planSha.equals(
						string(start.get("endpoint_attempt_plan_sha256")))
				|| !runSha.equals(string(start.get("run_record_sha256")))
				|| !LAUNCH_PROFILE.equals(string(start.get("launch_profile_id")))
				|| !hashes.get("materializer_jar_sha256").equals(
						string(start.get("materializer_jar_sha256")))
				|| !hashes.get("worker_entrypoint_sha256").equals(
						string(start.get("worker_entrypoint_sha256")))
				|| !hashes.get("worker_java_executable_sha256").equals(
						string(start.get("worker_java_executable_sha256")))
				|| !Boolean.FALSE.equals(start.get("retry_allowed"))) {
			throw new WorkerFailure("WORKER_START_BINDING");
		}
		long[] directoryIdentity = validateLaunchContract(
				attempt, launchContract, hashes);
		return new StartAuthority(
				sha256(raw), directoryIdentity[0], directoryIdentity[1]);
	}

	private static String validateWorkerInvocation(
			Path attempt, String caseId, String startedSha) throws Exception {
		byte[] startRaw = readSecureFile(
				attempt.resolve(STARTED_NAME), MAX_CLAIM_BYTES,
				"WORKER_START_STABILITY");
		if (!startedSha.equals(sha256(startRaw))) {
			throw new WorkerFailure("WORKER_START_STABILITY");
		}
		Map<String, Object> start = parseCanonicalObject(
				startRaw, "WORKER_START_STABILITY_JSON");
		String expectedLaunchSha = string(start.get("launch_contract_sha256"));
		byte[] raw = readSecureFile(
				attempt.resolve(INVOKED_NAME), MAX_CLAIM_BYTES,
				"WORKER_INVOCATION_READ");
		Map<String, Object> invocation = parseCanonicalObject(
				raw, "WORKER_INVOCATION_JSON");
		requireKeys(invocation, setOf(
				"attempt_id", "case_id", "launch_contract_sha256",
				"retry_allowed", "schema_version", "status",
				"worker_start_sha256"), "WORKER_INVOCATION_FIELDS");
		String launchSha = string(invocation.get("launch_contract_sha256"));
		if (!launchSha.matches("[0-9a-f]{64}")
				|| !launchSha.equals(expectedLaunchSha)
				|| !"m9-endpoint-worker-invocation-v1".equals(
						string(invocation.get("schema_version")))
				|| !"WORKER_PROCESS_LAUNCH_IRREVERSIBLY_CONSUMED".equals(
						string(invocation.get("status")))
				|| !caseId.equals(string(invocation.get("case_id")))
				|| !"attempt-0001".equals(string(invocation.get("attempt_id")))
				|| !startedSha.equals(string(invocation.get("worker_start_sha256")))
				|| !Boolean.FALSE.equals(invocation.get("retry_allowed"))) {
			throw new WorkerFailure("WORKER_INVOCATION_BINDING");
		}
		return sha256(raw);
	}

	private static long[] validateLaunchContract(
			Path attempt, Map<String, Object> contract, Map<String, String> hashes)
			throws Exception {
		requireKeys(contract, setOf(
				"attempt_directory_device", "attempt_directory_inode",
				"classpath_flag", "control_path", "cwd", "environment",
				"java_executable", "main_class", "runtime_jar",
				"schema_version", "start_new_session", "stderr_limit_bytes",
				"stdout_limit_bytes", "timeout_seconds", "umask_octal",
				"vm_arguments"), "LAUNCH_CONTRACT_FIELDS");
		Path cwd = Paths.get(System.getProperty("user.dir", ""))
				.toAbsolutePath().normalize();
		Path javaExecutable = Paths.get(System.getProperty("java.home"), "bin", "java")
				.toAbsolutePath().normalize();
		Path jar = codeSourcePath(M9EndpointWorker.class);
		long expectedDevice = number(contract.get("attempt_directory_device"));
		long expectedInode = number(contract.get("attempt_directory_inode"));
		List<?> arguments = contract.get("vm_arguments") instanceof List
				? (List<?>) contract.get("vm_arguments") : null;
		List<String> expectedArguments = Arrays.asList(
				"-Xms256m", "-Xmx4g", "-Djava.awt.headless=true",
				"-XX:+DisableAttachMechanism", "-XX:ActiveProcessorCount=1");
		if (expectedDevice < 0L || expectedInode < 1L
				|| arguments == null || !arguments.equals(expectedArguments)
				|| !"m9-endpoint-worker-launch-contract-v1".equals(
						string(contract.get("schema_version")))
				|| !javaExecutable.equals(Paths.get(string(
						contract.get("java_executable"))))
				|| !"-cp".equals(string(contract.get("classpath_flag")))
				|| !jar.equals(Paths.get(string(contract.get("runtime_jar"))))
				|| !M9EndpointWorker.class.getName().equals(
						string(contract.get("main_class")))
				|| !attempt.resolve(CONTROL_NAME).equals(
						Paths.get(string(contract.get("control_path"))))
				|| !cwd.equals(Paths.get(string(contract.get("cwd"))))
				|| number(contract.get("timeout_seconds")) != 3600L
				|| number(contract.get("stdout_limit_bytes")) != 65536L
				|| number(contract.get("stderr_limit_bytes")) != 65536L
				|| !Boolean.TRUE.equals(contract.get("start_new_session"))
				|| !"077".equals(string(contract.get("umask_octal")))) {
			throw new WorkerFailure("LAUNCH_CONTRACT");
		}
		Map<String, Object> suppliedEnvironment = object(contract.get("environment"));
		Map<String, String> expectedEnvironment = new TreeMap<String, String>();
		expectedEnvironment.put("LANG", "C");
		expectedEnvironment.put("LC_ALL", "C");
		expectedEnvironment.put("PATH", "/usr/bin:/bin");
		expectedEnvironment.put("TZ", "UTC");
		if (!suppliedEnvironment.equals(expectedEnvironment)
				|| !System.getenv().equals(expectedEnvironment)
				|| !ManagementFactory.getRuntimeMXBean().getInputArguments()
						.equals(expectedArguments)
				|| !hashes.get("worker_java_executable_sha256").matches(
						"[0-9a-f]{64}")) {
			throw new WorkerFailure("LAUNCH_CONTRACT_RUNTIME");
		}
		String expectedCommand = M9EndpointWorker.class.getName() + " "
				+ attempt.resolve(CONTROL_NAME).toString();
		if (!expectedCommand.equals(System.getProperty("sun.java.command", ""))) {
			throw new WorkerFailure("LAUNCH_COMMAND");
		}
		requireAttemptDirectoryIdentity(attempt, expectedDevice, expectedInode);
		return new long[]{expectedDevice, expectedInode};
	}

	private static void requireAttemptDirectoryIdentity(Control control)
			throws IOException {
		requireAttemptDirectoryIdentity(
				control.attemptDirectory,
				control.directoryDevice,
				control.directoryInode);
	}

	private static void requireAttemptDirectoryIdentity(
			Path attempt, long expectedDevice, long expectedInode)
			throws IOException {
		Map<String, Object> identity = Files.readAttributes(
				attempt, "unix:dev,ino", LinkOption.NOFOLLOW_LINKS);
		Object device = identity.get("dev");
		Object inode = identity.get("ino");
		if (!(device instanceof Number) || !(inode instanceof Number)
				|| ((Number) device).longValue() != expectedDevice
				|| ((Number) inode).longValue() != expectedInode
				|| Files.isSymbolicLink(attempt)) {
			throw new WorkerFailure("ATTEMPT_DIRECTORY_IDENTITY");
		}
	}

	private static void requireAttemptInventory(Path attempt, Set<String> expected)
			throws IOException {
		Set<String> actual = new LinkedHashSet<String>();
		DirectoryStream<Path> stream = Files.newDirectoryStream(attempt);
		try {
			for (Path entry : stream) {
				Path name = entry.getFileName();
				if (name == null || !actual.add(name.toString())) {
					throw new WorkerFailure("ATTEMPT_INVENTORY");
				}
			}
		} finally {
			stream.close();
		}
		if (!actual.equals(expected)) {
			throw new WorkerFailure("ATTEMPT_INVENTORY");
		}
	}

	private static void validateFixedHashes(Map<String, String> hashes) {
		Map<String, String> fixed = new LinkedHashMap<String, String>();
		fixed.put("t0_protocol_sha256", T0_PROTOCOL);
		fixed.put("t0_payload_sha256", T0_PAYLOAD);
		fixed.put("t0_response_sha256", T0_RESPONSE);
		fixed.put("t0_verification_sha256", T0_VERIFICATION);
		fixed.put("t0_seal_sha256", T0_SEAL);
		fixed.put("intake_manifest_sha256", INTAKE_MANIFEST);
		fixed.put("intake_summary_sha256", INTAKE_SUMMARY);
		fixed.put("intake_seal_sha256", INTAKE_SEAL);
		for (Map.Entry<String, String> entry : fixed.entrySet()) {
			if (!entry.getValue().equals(hashes.get(entry.getKey()))) {
				throw new WorkerFailure("IMMUTABLE_BINDING");
			}
		}
	}

	private static SelectedSources extractSelectedSources(
			Path archivePath, CaseProfile profile) throws Exception {
		byte[] archive = readSecureFile(
				archivePath, MAX_ARCHIVE_BYTES, "ARCHIVE_READ");
		try {
			if (archive.length != ARCHIVE_SIZE
					|| !ARCHIVE_SHA256.equals(sha256(archive))) {
				throw new WorkerFailure("ARCHIVE_BYTES");
			}
			return scanSelectedArchive(
					archive, profile, ARCHIVE_ENTRY_COUNT,
					ARCHIVE_FILE_COUNT, ARCHIVE_UNCOMPRESSED_SIZE);
		} finally {
			Arrays.fill(archive, (byte) 0);
		}
	}

	private static SelectedSources scanSelectedArchive(
			byte[] archive, CaseProfile profile, int expectedEntries,
			int expectedFiles, long expectedUncompressed) throws Exception {
		Map<String, byte[]> retained = new HashMap<String, byte[]>();
		try {
			Map<String, SourceRow> selectedRows = new HashMap<String, SourceRow>();
			for (SourceRow row : profile.sources) selectedRows.put(row.member, row);
			Set<String> names = new HashSet<String>();
			int entries = 0;
			int files = 0;
			long total = 0L;
			ZipInputStream zip = new ZipInputStream(
					new ByteArrayInputStream(archive), StandardCharsets.UTF_8);
			try {
				for (ZipEntry entry = zip.getNextEntry(); entry != null;
						entry = zip.getNextEntry()) {
					entries++;
					if (entries > MAX_ZIP_ENTRIES) {
						throw new WorkerFailure("ZIP_ENTRY_CAP");
					}
					String name = canonicalZipName(entry.getName(), entry.isDirectory());
					if (!names.add(name)) throw new WorkerFailure("ZIP_DUPLICATE");
					if (entry.getMethod() != ZipEntry.STORED
							&& entry.getMethod() != ZipEntry.DEFLATED) {
						throw new WorkerFailure("ZIP_METHOD");
					}
					CRC32 crc = new CRC32();
					ByteArrayOutputStream selected = selectedRows.containsKey(name)
							? new ByteArrayOutputStream() : null;
					byte[] buffer = new byte[8192];
					long size = 0L;
					for (int count = zip.read(buffer); count >= 0; count = zip.read(buffer)) {
						if (count == 0) continue;
						size += count;
						if (size > MAX_ZIP_ENTRY_BYTES
								|| total > MAX_ZIP_TOTAL_BYTES - count) {
							throw new WorkerFailure("ZIP_SIZE_CAP");
						}
						total += count;
						crc.update(buffer, 0, count);
						if (selected != null) selected.write(buffer, 0, count);
					}
					zip.closeEntry();
					if (entry.isDirectory()) {
						if (size != 0L) throw new WorkerFailure("ZIP_DIRECTORY_BYTES");
					} else {
						files++;
					}
					if (entry.getSize() >= 0L && entry.getSize() != size) {
						throw new WorkerFailure("ZIP_DECLARED_SIZE");
					}
					if (entry.getCrc() >= 0L && entry.getCrc() != crc.getValue()) {
						throw new WorkerFailure("ZIP_DECLARED_CRC");
					}
					SourceRow row = selectedRows.get(name);
					if (row != null) {
						byte[] value = selected.toByteArray();
						if (row.size != value.length || !row.sha256.equals(sha256(value))
								|| !row.crc32.equals(String.format("%08x", crc.getValue()))) {
							Arrays.fill(value, (byte) 0);
							throw new WorkerFailure("SELECTED_MEMBER_BYTES");
						}
						if (retained.put(name, value) != null) {
							throw new WorkerFailure("SELECTED_MEMBER_DUPLICATE");
						}
					}
				}
			} finally {
				zip.close();
			}
			if (entries != expectedEntries || files != expectedFiles
					|| total != expectedUncompressed
					|| retained.size() != profile.sources.size()) {
				throw new WorkerFailure("ARCHIVE_CENSUS");
			}
			return new SelectedSources(profile, retained);
		} catch (Throwable failure) {
			for (byte[] value : retained.values()) Arrays.fill(value, (byte) 0);
			throw failure;
		}
	}

	private static String canonicalZipName(String value, boolean directory) {
		if (value == null || value.isEmpty() || value.startsWith("/")
				|| value.indexOf('\\') >= 0 || value.indexOf('\u0000') >= 0
				|| directory != value.endsWith("/")) {
			throw new WorkerFailure("ZIP_NAME");
		}
		String body = directory ? value.substring(0, value.length() - 1) : value;
		if (body.isEmpty()) throw new WorkerFailure("ZIP_NAME");
		for (String part : body.split("/", -1)) {
			if (part.isEmpty() || ".".equals(part) || "..".equals(part)) {
				throw new WorkerFailure("ZIP_NAME");
			}
		}
		return body;
	}

	private static RuntimeAuthority validateRuntime(
			Map<String, String> bindings) throws Exception {
		List<String> input = ManagementFactory.getRuntimeMXBean().getInputArguments();
		if (input.size() != EXACT_VM_ARGUMENTS.size()
				|| !new LinkedHashSet<String>(input).equals(EXACT_VM_ARGUMENTS)) {
			throw new WorkerFailure("VM_ARGUMENTS");
		}
		for (String name : FORBIDDEN_ENVIRONMENT) {
			String value = System.getenv(name);
			if (value != null && !value.isEmpty()) {
				throw new WorkerFailure("JAVA_ENVIRONMENT");
			}
		}
		if (System.getSecurityManager() != null
				|| Thread.currentThread().getContextClassLoader()
						!= ClassLoader.getSystemClassLoader()) {
			throw new WorkerFailure("CLASSLOADER_PROFILE");
		}
		Path jar = codeSourcePath(M9EndpointWorker.class);
		String classPath = System.getProperty("java.class.path", "");
		String[] classPathEntries = classPath.split(
				java.util.regex.Pattern.quote(System.getProperty("path.separator")), -1);
		if (classPathEntries.length != 1
				|| !Paths.get(classPathEntries[0]).toAbsolutePath().normalize().equals(jar)
				|| !jar.getFileName().toString().endsWith(".jar")) {
			throw new WorkerFailure("CLASSPATH_PROFILE");
		}
		Class<?>[] authorities = {
				M9EndpointWorker.class, M9EndpointMaterializerBridge.class,
				TransitionSystemDispatcher.class, M9EndpointPreparedCase.class,
				M9EndpointReceiptCore.class, M9EndpointReceiptBundle.class,
				ltsa.updatingControllers.export.M9EndpointSynthesisHook.class,
				ltsa.updatingControllers.export.TraditionalPreGrSnapshotHook.class,
				ltsa.updatingControllers.export.TraditionalPreGrSnapshot.class,
				ltsa.updatingControllers.export.M9TraditionalSafetySemanticsSnapshot.class,
				ltsa.updatingControllers.export.M9TraditionalCompletionHandoffSnapshot.class,
		};
		for (Class<?> authority : authorities) {
			if (authority.getClassLoader() != ClassLoader.getSystemClassLoader()
					|| !codeSourcePath(authority).equals(jar)) {
				throw new WorkerFailure("AUTHORITY_CODE_SOURCE");
			}
			requireUniqueJarResource(authority, jar);
		}
		String jarSha = hashStableFile(jar, 1024L * 1024L * 1024L);
		if (!jarSha.equals(bindings.get("materializer_jar_sha256"))) {
			throw new WorkerFailure("SELF_JAR_BINDING");
		}
		String workerSha;
		InputStream workerStream = M9EndpointWorker.class.getResourceAsStream(
				"M9EndpointWorker.class");
		if (workerStream == null) throw new WorkerFailure("WORKER_RESOURCE");
		try {
			workerSha = sha256(readBounded(workerStream, 4L * 1024L * 1024L));
		} finally {
			workerStream.close();
		}
		if (!workerSha.equals(bindings.get("worker_entrypoint_sha256"))) {
			throw new WorkerFailure("WORKER_ENTRY_BINDING");
		}
		Path javaExecutable = Paths.get(System.getProperty("java.home"), "bin", "java")
				.toAbsolutePath().normalize();
		String executableSha = hashStableFile(javaExecutable, 256L * 1024L * 1024L);
		if (!executableSha.equals(bindings.get("worker_java_executable_sha256"))) {
			throw new WorkerFailure("JAVA_EXECUTABLE_BINDING");
		}
		long maxMemory = Runtime.getRuntime().maxMemory();
		if (Runtime.getRuntime().availableProcessors() != 1
				|| maxMemory < 3L * 1024L * 1024L * 1024L
				|| maxMemory > 5L * 1024L * 1024L * 1024L) {
			throw new WorkerFailure("RUNTIME_RESOURCE_PROFILE");
		}
		Thread current = Thread.currentThread();
		for (Thread thread : Thread.getAllStackTraces().keySet()) {
			if (thread != current && thread.isAlive() && !thread.isDaemon()) {
				throw new WorkerFailure("APPLICATION_THREAD_CENSUS");
			}
		}
		ComputerOptions.getInstance().setAllowedThreads(1);
		if (ComputerOptions.getInstance().getAllowedThreads() != 1) {
			throw new WorkerFailure("RANKING_THREAD_PROFILE");
		}
		return new RuntimeAuthority(jarSha, workerSha, executableSha);
	}

	private static Path codeSourcePath(Class<?> value) throws Exception {
		URI uri = value.getProtectionDomain().getCodeSource().getLocation().toURI();
		Path result = Paths.get(uri).toAbsolutePath().normalize();
		if (!Files.isRegularFile(result, LinkOption.NOFOLLOW_LINKS)) {
			throw new WorkerFailure("CODE_SOURCE_PATH");
		}
		return result;
	}

	private static void requireUniqueJarResource(
			Class<?> value, Path jar) throws Exception {
		String name = value.getName().replace('.', '/') + ".class";
		Enumeration<URL> resources = ClassLoader.getSystemClassLoader().getResources(name);
		if (!resources.hasMoreElements()) throw new WorkerFailure("CLASS_RESOURCE");
		URL resource = resources.nextElement();
		if (resources.hasMoreElements() || !"jar".equals(resource.getProtocol())) {
			throw new WorkerFailure("CLASS_RESOURCE_CENSUS");
		}
		JarURLConnection connection = (JarURLConnection) resource.openConnection();
		connection.setUseCaches(false);
		Path resourceJar = Paths.get(connection.getJarFileURL().toURI())
				.toAbsolutePath().normalize();
		if (!resourceJar.equals(jar)) throw new WorkerFailure("CLASS_RESOURCE_JAR");
	}

	private static String candidateReport(
			Control control, M9EndpointReceiptBundle.PublishedReceipt receipt,
			RuntimeAuthority runtime, String enteredSha) {
		Map<String, Object> value = new TreeMap<String, Object>();
		value.put("attempt_id", control.attemptId);
		value.put("attempt_claim_sha256", control.claimSha256);
		value.put("case_id", control.profile.caseId);
		value.put("endpoint_attempt_plan_sha256", control.planSha256);
		value.put("endpoint_control_sha256", control.controlSha256);
		value.put("core_sha256", hex(receipt.getCoreSha256()));
		value.put("destination", RECEIPT_NAME);
		value.put("full_sha256", hex(receipt.getSha256()));
		value.put("prefix_sha256", hex(receipt.getPrefixSha256()));
		value.put("runtime_jar_sha256", runtime.jarSha256);
		value.put("run_record_sha256", control.runSha256);
		value.put("schema_version", "m9-endpoint-worker-report-v1");
		value.put("seal_sha256", hex(receipt.getSealSha256()));
		value.put("size_bytes", Long.valueOf(receipt.getSizeBytes()));
		value.put("status",
				"CANDIDATE_RECEIPT_PUBLISHED_NOT_YET_INDEPENDENTLY_VERIFIED");
		value.put("worker_started_sha256", control.startedSha256);
		value.put("worker_invocation_sha256", control.invokedSha256);
		value.put("worker_entered_sha256", enteredSha);
		return new String(canonicalBytes(value), StandardCharsets.UTF_8);
	}

	private static byte[] readSecureFile(
			Path path, long maximum, String failureCode) throws Exception {
		Path absolute = path.toAbsolutePath().normalize();
		if (!path.isAbsolute() || !path.normalize().equals(absolute)) {
			throw new WorkerFailure(failureCode);
		}
		Path root = absolute.getRoot();
		if (root == null) throw new WorkerFailure(failureCode);
		Path relative = root.relativize(absolute);
		List<DirectoryStream<Path>> streams = new ArrayList<DirectoryStream<Path>>();
		try {
			DirectoryStream<Path> rootStream = Files.newDirectoryStream(root);
			streams.add(rootStream);
			if (!(rootStream instanceof SecureDirectoryStream)) {
				throw new WorkerFailure("SECURE_DIRECTORY_STREAM_REQUIRED");
			}
			@SuppressWarnings("unchecked")
			SecureDirectoryStream<Path> current =
					(SecureDirectoryStream<Path>) rootStream;
			for (int index = 0; index < relative.getNameCount() - 1; index++) {
				SecureDirectoryStream<Path> child = current.newDirectoryStream(
						relative.getName(index), LinkOption.NOFOLLOW_LINKS);
				streams.add(child);
				current = child;
			}
			Path leaf = relative.getFileName();
			BasicFileAttributeView view = current.getFileAttributeView(
					leaf, BasicFileAttributeView.class, LinkOption.NOFOLLOW_LINKS);
			BasicFileAttributes before = view.readAttributes();
			if (!before.isRegularFile() || before.isSymbolicLink()
					|| before.size() < 1L || before.size() > maximum
					|| before.fileKey() == null) {
				throw new WorkerFailure(failureCode);
			}
			Set<OpenOption> options = new HashSet<OpenOption>();
			options.add(StandardOpenOption.READ);
			options.add(LinkOption.NOFOLLOW_LINKS);
			SeekableByteChannel channel = current.newByteChannel(leaf, options);
			byte[] result;
			try {
				ByteArrayOutputStream output = new ByteArrayOutputStream(
						(int) Math.min(before.size(), 1024L * 1024L));
				ByteBuffer buffer = ByteBuffer.allocate(64 * 1024);
				long total = 0L;
				while (channel.read(buffer) >= 0) {
					if (buffer.position() == 0) continue;
					buffer.flip();
					int count = buffer.remaining();
					total += count;
					if (total > maximum) throw new WorkerFailure(failureCode);
					output.write(buffer.array(), buffer.position(), count);
					buffer.clear();
				}
				result = output.toByteArray();
			} finally {
				channel.close();
			}
			BasicFileAttributes after = view.readAttributes();
			if (before.size() != result.length || before.size() != after.size()
					|| !before.fileKey().equals(after.fileKey())
					|| !before.lastModifiedTime().equals(after.lastModifiedTime())) {
				Arrays.fill(result, (byte) 0);
				throw new WorkerFailure(failureCode);
			}
			return result;
		} finally {
			for (int index = streams.size() - 1; index >= 0; index--) {
				try { streams.get(index).close(); } catch (IOException ignored) { }
			}
		}
	}

	private static String hashStableFile(Path path, long maximum) throws Exception {
		Path absolute = path.toAbsolutePath().normalize();
		requireNoSymlinkComponents(absolute);
		BasicFileAttributes before = Files.readAttributes(
				absolute, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
		if (!before.isRegularFile() || before.isSymbolicLink()
				|| before.size() < 1L || before.size() > maximum
				|| before.fileKey() == null) {
			throw new WorkerFailure("STABLE_FILE_HASH");
		}
		MessageDigest digest;
		try {
			digest = MessageDigest.getInstance("SHA-256");
		} catch (NoSuchAlgorithmException impossible) {
			throw new IllegalStateException(impossible);
		}
		SeekableByteChannel channel = Files.newByteChannel(
				absolute, StandardOpenOption.READ, LinkOption.NOFOLLOW_LINKS);
		long total = 0L;
		try {
			ByteBuffer buffer = ByteBuffer.allocate(1024 * 1024);
			while (channel.read(buffer) >= 0) {
				if (buffer.position() == 0) continue;
				buffer.flip();
				total += buffer.remaining();
				if (total > maximum) throw new WorkerFailure("STABLE_FILE_HASH");
				digest.update(buffer);
				buffer.clear();
			}
		} finally {
			channel.close();
		}
		BasicFileAttributes after = Files.readAttributes(
				absolute, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
		if (total != before.size() || before.size() != after.size()
				|| !before.fileKey().equals(after.fileKey())
				|| !before.lastModifiedTime().equals(after.lastModifiedTime())) {
			throw new WorkerFailure("STABLE_FILE_HASH");
		}
		return hex(digest.digest());
	}

	private static void requireNoSymlinkComponents(Path absolute) throws IOException {
		Path current = absolute.getRoot();
		if (current == null) throw new WorkerFailure("PATH_ROOT");
		for (Path part : current.relativize(absolute)) {
			current = current.resolve(part);
			if (Files.isSymbolicLink(current)) {
				throw new WorkerFailure("PATH_SYMLINK");
			}
		}
	}

	private static byte[] readBounded(InputStream input, long maximum)
			throws IOException {
		ByteArrayOutputStream output = new ByteArrayOutputStream();
		byte[] buffer = new byte[8192];
		long total = 0L;
		for (int count = input.read(buffer); count >= 0; count = input.read(buffer)) {
			if (count == 0) continue;
			total += count;
			if (total > maximum) throw new IOException("bounded input exceeded");
			output.write(buffer, 0, count);
		}
		return output.toByteArray();
	}

	private static void requirePrivateDirectory(Path path) throws IOException {
		Set<PosixFilePermission> permissions = Files.getPosixFilePermissions(
				path, LinkOption.NOFOLLOW_LINKS);
		Set<PosixFilePermission> expected = new HashSet<PosixFilePermission>(
				Arrays.asList(PosixFilePermission.OWNER_READ,
						PosixFilePermission.OWNER_WRITE,
						PosixFilePermission.OWNER_EXECUTE));
		if (!permissions.equals(expected) || Files.isSymbolicLink(path)) {
			throw new WorkerFailure("ATTEMPT_DIRECTORY_MODE");
		}
	}

	private static Map<String, Object> parseCanonicalObject(
			byte[] raw, String failureCode) throws Exception {
		String text;
		try {
			text = StandardCharsets.UTF_8.newDecoder()
					.onMalformedInput(CodingErrorAction.REPORT)
					.onUnmappableCharacter(CodingErrorAction.REPORT)
					.decode(ByteBuffer.wrap(raw)).toString();
		} catch (CharacterCodingException invalid) {
			throw new WorkerFailure(failureCode);
		}
		Object parsed;
		try {
			parsed = new JSONParser().parse(text);
		} catch (ParseException invalid) {
			throw new WorkerFailure(failureCode);
		}
		Map<String, Object> result = object(parsed);
		if (!Arrays.equals(raw, canonicalBytes(result))) {
			throw new WorkerFailure(failureCode);
		}
		return result;
	}

	private static byte[] canonicalBytes(Object value) {
		StringBuilder result = new StringBuilder();
		appendJson(result, value, 0);
		result.append('\n');
		return result.toString().getBytes(StandardCharsets.UTF_8);
	}

	private static void appendJson(StringBuilder result, Object value, int depth) {
		if (depth > 32) throw new WorkerFailure("JSON_DEPTH");
		if (value instanceof Map) {
			Map<?, ?> source = (Map<?, ?>) value;
			TreeMap<String, Object> sorted = new TreeMap<String, Object>();
			for (Map.Entry<?, ?> entry : source.entrySet()) {
				if (!(entry.getKey() instanceof String)
						|| sorted.put((String) entry.getKey(), entry.getValue()) != null) {
					throw new WorkerFailure("JSON_OBJECT");
				}
			}
			result.append('{');
			boolean first = true;
			for (Map.Entry<String, Object> entry : sorted.entrySet()) {
				if (!first) result.append(',');
				appendJsonString(result, entry.getKey());
				result.append(':');
				appendJson(result, entry.getValue(), depth + 1);
				first = false;
			}
			result.append('}');
		} else if (value instanceof List) {
			List<?> list = (List<?>) value;
			if (list.size() > 1024) throw new WorkerFailure("JSON_ARRAY_CENSUS");
			result.append('[');
			for (int index = 0; index < list.size(); index++) {
				if (index != 0) result.append(',');
				appendJson(result, list.get(index), depth + 1);
			}
			result.append(']');
		} else if (value instanceof String) {
			appendJsonString(result, (String) value);
		} else if (value instanceof Long) {
			result.append(((Long) value).longValue());
		} else if (value instanceof Boolean) {
			result.append(Boolean.TRUE.equals(value) ? "true" : "false");
		} else {
			throw new WorkerFailure("JSON_VALUE_TYPE");
		}
	}

	private static void appendJsonString(StringBuilder result, String value) {
		if (value == null || value.length() > 16 * 1024) {
			throw new WorkerFailure("JSON_STRING");
		}
		result.append('"');
		for (int index = 0; index < value.length(); index++) {
			char character = value.charAt(index);
			if (character > 0x7e || (character < 0x20 && character != '\b'
					&& character != '\f' && character != '\n'
					&& character != '\r' && character != '\t')) {
				throw new WorkerFailure("JSON_ASCII_PROFILE");
			}
			switch (character) {
				case '"': result.append("\\\""); break;
				case '\\': result.append("\\\\"); break;
				case '\b': result.append("\\b"); break;
				case '\f': result.append("\\f"); break;
				case '\n': result.append("\\n"); break;
				case '\r': result.append("\\r"); break;
				case '\t': result.append("\\t"); break;
				default: result.append(character);
			}
		}
		result.append('"');
	}

	@SuppressWarnings("unchecked")
	private static Map<String, Object> object(Object value) {
		if (!(value instanceof Map)) throw new WorkerFailure("JSON_OBJECT_TYPE");
		Map<?, ?> source = (Map<?, ?>) value;
		Map<String, Object> result = new LinkedHashMap<String, Object>();
		for (Map.Entry<?, ?> entry : source.entrySet()) {
			if (!(entry.getKey() instanceof String)) {
				throw new WorkerFailure("JSON_OBJECT_KEY");
			}
			result.put((String) entry.getKey(), entry.getValue());
		}
		return result;
	}

	private static Map<String, String> hashMap(
			Object value, Set<String> keys, String failureCode) {
		Map<String, Object> source = object(value);
		if (!source.keySet().equals(keys)) throw new WorkerFailure(failureCode);
		Map<String, String> result = new TreeMap<String, String>();
		for (String key : keys) {
			String digest = string(source.get(key));
			if (!digest.matches("[0-9a-f]{64}")) {
				throw new WorkerFailure(failureCode);
			}
			result.put(key, digest);
		}
		return result;
	}

	private static void requireKeys(
			Map<String, ?> value, Set<String> keys, String failureCode) {
		if (!value.keySet().equals(keys)) throw new WorkerFailure(failureCode);
	}

	private static Set<String> setOf(String... values) {
		return new LinkedHashSet<String>(Arrays.asList(values));
	}

	private static String string(Object value) {
		if (!(value instanceof String)) throw new WorkerFailure("JSON_STRING_TYPE");
		return (String) value;
	}

	private static long number(Object value) {
		if (!(value instanceof Long)) throw new WorkerFailure("JSON_INTEGER_TYPE");
		return ((Long) value).longValue();
	}

	private static String sha256(byte[] value) {
		try {
			return hex(MessageDigest.getInstance("SHA-256").digest(value));
		} catch (NoSuchAlgorithmException impossible) {
			throw new IllegalStateException(impossible);
		}
	}

	private static String hex(byte[] value) {
		StringBuilder result = new StringBuilder(value.length * 2);
		for (byte element : value) result.append(String.format("%02x", element & 0xff));
		return result.toString();
	}

	static final class SourceRow {
		final String role;
		final String member;
		final String sha256;
		final long size;
		final String crc32;

		SourceRow(String role, String member, String sha256, long size, String crc32) {
			this.role = role;
			this.member = member;
			this.sha256 = sha256;
			this.size = size;
			this.crc32 = crc32;
		}

		Map<String, Object> asJson() {
			Map<String, Object> value = new TreeMap<String, Object>();
			value.put("crc32", crc32);
			value.put("member", member);
			value.put("role", role);
			value.put("sha256", sha256);
			value.put("size_bytes", Long.valueOf(size));
			return value;
		}
	}

	static final class CaseProfile {
		final String caseId;
		final List<SourceRow> sources;

		CaseProfile(String caseId, List<SourceRow> sources) {
			this.caseId = caseId;
			this.sources = Collections.unmodifiableList(new ArrayList<SourceRow>(sources));
		}

		SourceRow newSource() {
			for (SourceRow row : sources) if ("new_model".equals(row.role)) return row;
			throw new WorkerFailure("NEW_SOURCE_ROLE");
		}

		long totalSourceBytes() {
			long result = 0L;
			for (SourceRow row : sources) result += row.size;
			return result;
		}

		String selectedBindingsSha256() {
			Map<String, Object> value = new TreeMap<String, Object>();
			value.put("case_id", caseId);
			value.put("cluster_id", CLUSTER);
			List<Object> rows = new ArrayList<Object>();
			for (SourceRow row : sources) rows.add(row.asJson());
			value.put("ordered_sources", rows);
			value.put("schema_version", "m9-selected-source-bindings-v1");
			return sha256(canonicalBytes(value));
		}

		void requireSelectedRows(Object supplied) {
			if (!(supplied instanceof List)) throw new WorkerFailure("SOURCE_ROWS");
			List<?> rows = (List<?>) supplied;
			if (rows.size() != sources.size()) throw new WorkerFailure("SOURCE_ROWS");
			for (int index = 0; index < rows.size(); index++) {
				Map<String, Object> actual = object(rows.get(index));
				if (!actual.equals(sources.get(index).asJson())) {
					throw new WorkerFailure("SOURCE_ROWS");
				}
			}
		}
	}

	private static final class SelectedSources {
		private final CaseProfile profile;
		private final Map<String, byte[]> values;
		private final byte[] newSource;

		private SelectedSources(CaseProfile profile, Map<String, byte[]> values) {
			this.profile = profile;
			this.values = values;
			this.newSource = values.get(profile.newSource().member);
			if (newSource == null) throw new WorkerFailure("NEW_SOURCE_BYTES");
		}

		private void clearOtherSources() {
			for (byte[] value : values.values()) {
				if (value != newSource) Arrays.fill(value, (byte) 0);
			}
		}
	}

	private static final class Control {
		private final Path attemptDirectory;
		private final Path archivePath;
		private final CaseProfile profile;
		private final String attemptId;
		private final String claimSha256;
		private final String controlSha256;
		private final String planSha256;
		private final String runSha256;
		private final String startedSha256;
		private final String invokedSha256;
		private final long directoryDevice;
		private final long directoryInode;
		private final Map<String, String> fullHashes;
		private final Map<String, String> hashCore;

		private Control(
				Path attemptDirectory, Path archivePath, CaseProfile profile,
				String attemptId, String claimSha256, String controlSha256,
				String planSha256, String runSha256, String startedSha256,
				String invokedSha256, long directoryDevice, long directoryInode,
				Map<String, String> fullHashes, Map<String, String> hashCore) {
			this.attemptDirectory = attemptDirectory;
			this.archivePath = archivePath;
			this.profile = profile;
			this.attemptId = attemptId;
			this.claimSha256 = claimSha256;
			this.controlSha256 = controlSha256;
			this.planSha256 = planSha256;
			this.runSha256 = runSha256;
			this.startedSha256 = startedSha256;
			this.invokedSha256 = invokedSha256;
			this.directoryDevice = directoryDevice;
			this.directoryInode = directoryInode;
			this.fullHashes = fullHashes;
			this.hashCore = hashCore;
		}
	}

	private static final class StartAuthority {
		private final String sha256;
		private final long directoryDevice;
		private final long directoryInode;

		private StartAuthority(
				String sha256, long directoryDevice, long directoryInode) {
			this.sha256 = sha256;
			this.directoryDevice = directoryDevice;
			this.directoryInode = directoryInode;
		}
	}

	private static final class RuntimeAuthority {
		private final String jarSha256;
		@SuppressWarnings("unused") private final String workerSha256;
		@SuppressWarnings("unused") private final String javaExecutableSha256;

		private RuntimeAuthority(
				String jarSha256, String workerSha256, String javaExecutableSha256) {
			this.jarSha256 = jarSha256;
			this.workerSha256 = workerSha256;
			this.javaExecutableSha256 = javaExecutableSha256;
		}
	}

	private static final class BoundedOutput extends OutputStream {
		private final long maximum;
		private long count;
		private boolean overflowed;

		private BoundedOutput(long maximum) { this.maximum = maximum; }

		@Override public void write(int value) { write(new byte[]{(byte) value}, 0, 1); }

		@Override public void write(byte[] value, int offset, int length) {
			if (length < 0 || count > maximum - length) {
				overflowed = true;
				return;
			}
			count += length;
		}

		private long size() { return count; }
		private boolean isOverflowed() { return overflowed; }
	}

	private static final class WorkerFailure extends IllegalArgumentException {
		private final String code;
		private WorkerFailure(String code) {
			super(code);
			this.code = code;
		}
	}
}
