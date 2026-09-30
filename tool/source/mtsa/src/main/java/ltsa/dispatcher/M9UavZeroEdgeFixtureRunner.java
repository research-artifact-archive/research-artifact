package ltsa.dispatcher;

import ltsa.MultiCore.ComputerOptions;
import ltsa.lts.M9EndpointPreparedCase;
import ltsa.updatingControllers.export.M9EndpointReceiptCore;

import java.io.IOException;
import java.io.OutputStream;
import java.io.PrintStream;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.nio.file.attribute.PosixFilePermission;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Arrays;
import java.util.EnumSet;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * Fresh-JVM, fixture-only entry point for native UAV semantic sections
 * and their exact source/section binding manifest.
 *
 * <p>This class deliberately does not use {@link M9EndpointWorker}: it accepts
 * only an already staged synthetic source file and a private output directory,
 * creates no T1/ledger claim, and returns no controller authority.  Its only
 * visible result is the three zero-edge endpoint semantic section blobs,
 * their canonical source/section binding manifest, and a decision-free
 * canonical source-model successor derived from the same immutable typed
 * snapshots; it
 * never emits the live receipt core/seal whose attempt fields require a real
 * campaign ledger.
 * The Python fixture harness authenticates this source file, this runner, and
 * the observation JAR before launch.  This is not a live campaign entrypoint.</p>
 */
public final class M9UavZeroEdgeFixtureRunner {
	private static final String CLASSIFICATION = "SYNTHETIC_FIXTURE_ONLY";
	private static final String PROJECTION_KIND = "UAV_ZERO_EDGE_SOURCE_MODEL_V4";
	private static final String FINITE_PROFILE =
			"uav_mtsa_native_zero_edge_endpoint_fixture_v4";
	private static final String ATTEMPT_ID = "synthetic-fixture-attempt-1";
	private static final int MAX_SOURCE_BYTES = 16 * 1024 * 1024;
	private static final int MAX_NATIVE_DIAGNOSTIC_BYTES = 64 * 1024;

	private M9UavZeroEdgeFixtureRunner() {
	}

	public static void main(String[] arguments) {
		int status = 72;
		try {
			run(arguments);
			status = 0;
		} catch (Throwable failure) {
			if (failure instanceof ThreadDeath) throw (ThreadDeath) failure;
		}
		if (status != 0) System.exit(status);
	}

	static void run(String[] arguments) throws Exception {
		Set<String> required = M9EndpointReceiptCore.Bindings
				.requiredSha256BindingKeys();
		if (arguments == null || arguments.length != 7 + 2 * required.size()) {
			throw new IllegalArgumentException("Fixture runner argument census differs.");
		}
		Path source = Paths.get(arguments[0]).toAbsolutePath().normalize();
		Path caseDirectory = Paths.get(arguments[1]).toAbsolutePath().normalize();
		String caseId = arguments[2];
		String clusterId = arguments[3];
		long sourceFileCount = parseNonnegative(arguments[4], "source file count");
		long sourceTotalBytes = parseNonnegative(arguments[5], "source byte count");
		String expectedSourceSha256 = arguments[6];
		Map<String, String> hashes = new LinkedHashMap<String, String>();
		for (int index = 7; index < arguments.length; index += 2) {
			if (hashes.put(arguments[index], arguments[index + 1]) != null) {
				throw new IllegalArgumentException("Fixture receipt hash key is duplicated.");
			}
		}
		if (!hashes.keySet().equals(required)
				|| !expectedSourceSha256.matches("[0-9a-f]{64}")
				|| !expectedSourceSha256.equals(
					hashes.get("selected_translation_source_sha256"))) {
			throw new IllegalArgumentException("Fixture receipt hash bindings differ.");
		}
		if (!Files.isRegularFile(source, LinkOption.NOFOLLOW_LINKS)
				|| Files.isSymbolicLink(source)) {
			throw new IllegalArgumentException("Fixture source is not a regular file.");
		}
		if (!Files.isDirectory(caseDirectory, LinkOption.NOFOLLOW_LINKS)
				|| Files.isSymbolicLink(caseDirectory)
				|| caseDirectory.getFileName() == null
				|| !caseId.equals(caseDirectory.getFileName().toString())) {
			throw new IllegalArgumentException("Fixture output directory differs.");
		}
		Set<PosixFilePermission> expectedMode = EnumSet.of(
				PosixFilePermission.OWNER_READ,
				PosixFilePermission.OWNER_WRITE,
				PosixFilePermission.OWNER_EXECUTE);
		if (!Files.getPosixFilePermissions(
				caseDirectory, LinkOption.NOFOLLOW_LINKS).equals(expectedMode)) {
			throw new IllegalArgumentException("Fixture output directory is not mode 0700.");
		}

		byte[] sourceBytes = Files.readAllBytes(source);
		try {
			if (sourceBytes.length == 0 || sourceBytes.length > MAX_SOURCE_BYTES
					|| !hex(MessageDigest.getInstance("SHA-256").digest(sourceBytes))
						.equals(expectedSourceSha256)
					|| sourceFileCount < 1L || sourceTotalBytes < sourceBytes.length) {
				throw new IllegalArgumentException("Fixture source byte binding differs.");
			}
			M9EndpointPreparedCase prepared =
					M9EndpointPreparedCase.prepareOfficial(sourceBytes);
			ComputerOptions.getInstance().setAllowedThreads(1);
			M9EndpointReceiptCore.Bindings bindings =
					M9EndpointReceiptCore.Bindings.capture(
							caseId, clusterId, ATTEMPT_ID, CLASSIFICATION,
							PROJECTION_KIND, FINITE_PROFILE, sourceFileCount,
							sourceTotalBytes, hashes);
			BoundedOutput capturedOut = new BoundedOutput();
			BoundedOutput capturedErr = new BoundedOutput();
			PrintStream originalOut = System.out;
			PrintStream originalErr = System.err;
			try {
				System.setOut(new PrintStream(capturedOut, true, "UTF-8"));
				System.setErr(new PrintStream(capturedErr, true, "UTF-8"));
				TransitionSystemDispatcher.M9EndpointFixtureSections result =
						M9EndpointMaterializerBridge
						.synthesiseFixtureSectionsOnce(prepared, bindings);
				for (M9EndpointReceiptCore.SectionDescriptor section
						: result.getSections().getSections()) {
					Path destination = caseDirectory.resolve(section.getName());
					try (OutputStream output = Files.newOutputStream(
							destination, StandardOpenOption.CREATE_NEW,
							StandardOpenOption.WRITE,
							LinkOption.NOFOLLOW_LINKS)) {
						result.getSections().writeCanonicalSection(
								section.getName(), output);
					}
					if (!Files.isRegularFile(destination, LinkOption.NOFOLLOW_LINKS)
							|| Files.size(destination) != section.getSizeBytes()) {
						throw new IllegalStateException(
								"Native fixture semantic section differs after write.");
					}
				}
				Path sourceModel = caseDirectory.resolve("source-model.json");
				try (OutputStream output = Files.newOutputStream(
						sourceModel, StandardOpenOption.CREATE_NEW,
						StandardOpenOption.WRITE, LinkOption.NOFOLLOW_LINKS)) {
					result.getSections().writeCanonicalZeroEdgeSourceModel(
							expectedSourceSha256, output);
				}
				if (!Files.isRegularFile(sourceModel, LinkOption.NOFOLLOW_LINKS)
						|| Files.size(sourceModel) <= 0L) {
					throw new IllegalStateException(
							"Native fixture zero-edge source model differs after write.");
				}
				Path binding = caseDirectory.resolve("source-section-binding.json");
				byte[] bindingBytes = sourceSectionBinding(
						caseId, expectedSourceSha256, sourceBytes.length,
						sourceFileCount, sourceTotalBytes, result);
				try (OutputStream output = Files.newOutputStream(
						binding, StandardOpenOption.CREATE_NEW,
						StandardOpenOption.WRITE, LinkOption.NOFOLLOW_LINKS)) {
					output.write(bindingBytes);
				}
				if (!Files.isRegularFile(binding, LinkOption.NOFOLLOW_LINKS)
						|| Files.size(binding) != bindingBytes.length) {
					throw new IllegalStateException(
							"Native fixture source/section binding differs after write.");
				}
				Arrays.fill(bindingBytes, (byte) 0);
			} finally {
				System.setOut(originalOut);
				System.setErr(originalErr);
			}
			if (capturedOut.isOverflowed() || capturedErr.isOverflowed()) {
				throw new IllegalStateException("Native fixture diagnostics exceeded their bound.");
			}
		} finally {
			Arrays.fill(sourceBytes, (byte) 0);
		}
	}

	private static byte[] sourceSectionBinding(
			String caseId,
			String sourceSha256,
			long sourceSizeBytes,
			long sourceFileCount,
			long sourceTotalBytes,
			TransitionSystemDispatcher.M9EndpointFixtureSections result) {
		if (!caseId.matches("[a-z0-9_]+")) {
			throw new IllegalArgumentException("Fixture case identifier differs.");
		}
		StringBuilder value = new StringBuilder(2048);
		value.append('{');
		value.append("\"campaign_attempts_consumed\":0,");
		value.append("\"case_id\":\"").append(caseId).append("\",");
		value.append("\"decision_status\":\"NOT_RUN\",");
		value.append("\"endpoint_gr_invocations\":")
				.append(result.getEndpointSynthesisEntries()).append(',');
		value.append("\"fixture_only\":true,");
		value.append("\"game_fixed_point_invocations\":0,");
		value.append("\"immutable_section_captures\":")
				.append(result.getImmutableSectionCaptures()).append(',');
		value.append("\"rejected_synthesis_entries\":")
				.append(result.getRejectedSynthesisEntries()).append(',');
		value.append("\"schema_version\":")
				.append("\"m9-uav-zero-edge-source-section-binding-v1\",");
		value.append("\"selected_fg_solver_invocations\":0,");
		value.append("\"semantic_sections\":[");
		for (int index = 0;
				index < result.getSections().getSections().size(); index++) {
			if (index != 0) value.append(',');
			M9EndpointReceiptCore.SectionDescriptor section =
					result.getSections().getSections().get(index);
			value.append("{\"name\":\"").append(section.getName())
					.append("\",\"sha256\":\"")
					.append(hex(section.getContentSha256()))
					.append("\",\"size_bytes\":")
					.append(section.getSizeBytes()).append('}');
		}
		value.append("],");
		value.append("\"source_binding_file_count\":")
				.append(sourceFileCount).append(',');
		value.append("\"source_binding_total_bytes\":")
				.append(sourceTotalBytes).append(',');
		value.append("\"source_open_markers\":0,");
		value.append("\"source_sha256\":\"").append(sourceSha256).append("\",");
		value.append("\"source_size_bytes\":").append(sourceSizeBytes).append(',');
		value.append("\"tsa_requests\":0,");
		value.append("\"updater_gr_invocations\":0}\n");
		return value.toString().getBytes(StandardCharsets.UTF_8);
	}

	private static long parseNonnegative(String value, String label) {
		try {
			long result = Long.parseLong(value);
			if (result < 0L) throw new NumberFormatException();
			return result;
		} catch (NumberFormatException invalid) {
			throw new IllegalArgumentException("Fixture " + label + " differs.", invalid);
		}
	}

	private static String hex(byte[] bytes) {
		StringBuilder result = new StringBuilder(bytes.length * 2);
		for (byte value : bytes) {
			result.append(String.format("%02x", Integer.valueOf(value & 0xff)));
		}
		return result.toString();
	}

	private static final class BoundedOutput extends OutputStream {
		private int size;
		private boolean overflowed;

		@Override
		public void write(int value) throws IOException {
			if (size >= MAX_NATIVE_DIAGNOSTIC_BYTES) {
				overflowed = true;
				throw new IOException("Native fixture diagnostic output exceeded its bound.");
			}
			size++;
		}

		@Override
		public void write(byte[] values, int offset, int length) throws IOException {
			if (length < 0 || offset < 0 || offset > values.length - length) {
				throw new IndexOutOfBoundsException();
			}
			if (size > MAX_NATIVE_DIAGNOSTIC_BYTES - length) {
				overflowed = true;
				throw new IOException("Native fixture diagnostic output exceeded its bound.");
			}
			size += length;
		}

		boolean isOverflowed() { return overflowed; }
	}
}
