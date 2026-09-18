package ltsa.updatingControllers.export;

import java.io.DataOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.FileAlreadyExistsException;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.nio.file.attribute.BasicFileAttributes;
import java.nio.file.attribute.PosixFilePermission;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Arrays;
import java.util.List;
import java.util.Set;

/**
 * No-clobber durable container for a canonical endpoint receipt core, its
 * streamed semantic sections, and the post-hook seal envelope.
 *
 * <p>The caller must create the {@link PublicationTarget} before entering the
 * one-shot solver route.  This target is an in-process path/parent-identity
 * capture, not the durable cross-process attempt claim.  The registered T1
 * worker must create and fsync that separate no-retry claim before it invokes
 * this class.  Publication first writes and fsyncs the registered
 * pending path with {@code CREATE_NEW}; a hard link makes the final path appear
 * only after the entire container has been re-read and verified.  The pending
 * path is deliberately retained after every successful {@code CREATE_NEW}; no
 * cleanup path may unlink a concurrently substituted inode.  A write or power
 * failure before file/directory fsync need not leave durable partial evidence;
 * the outer attempt claim remains the authoritative consumed-attempt record.
 * Likewise, neither the pending nor final bundle path is a PASS marker: an
 * independent decoder must verify the full bytes before the outer ledger may
 * publish its unique {@code OUTCOME.json}.  A publication exception after the
 * hard-link step is retained as a terminal failure even if that link remains.</p>
 */
public final class M9EndpointReceiptBundle {
	private static final byte[] MAGIC =
			"M9EPRC02".getBytes(StandardCharsets.US_ASCII);
	public static final int VERSION = 2;
	public static final String SEAL_SCHEMA = "m9-endpoint-receipt-seal-v2";
	private static final String SEAL_DOMAIN =
			"FGDUCS-M9-ENDPOINT-RECEIPT-SEAL-V2";
	private static final long MAX_BUNDLE_BYTES = 128L * 1024L * 1024L;
	private static final String PENDING_NAME = "endpoint-receipt.bundle.pending";
	private static final String DESTINATION_NAME = "endpoint-receipt.bundle";

	private M9EndpointReceiptBundle() {
	}

	public static PublicationTarget prepare(
			Path suppliedPending,
			Path suppliedDestination,
			String expectedCaseId,
			String expectedAttemptId,
			String expectedAttemptClaimSha256) throws IOException {
		return PublicationTarget.capture(
				suppliedPending, suppliedDestination, expectedCaseId,
				expectedAttemptId, expectedAttemptClaimSha256);
	}

	public static PublishedReceipt publish(
			M9EndpointReceiptCore core,
			M9EndpointSynthesisHook.SealedAttempt sealedAttempt,
			TraditionalPreGrSnapshotHook.SealedCapture traditionalCapture,
			PublicationTarget target) throws IOException {
		if (core == null || sealedAttempt == null || traditionalCapture == null
				|| target == null) {
			throw new IllegalArgumentException(
					"Combined receipt core, endpoint/pre-GR seals, and publication target are required.");
		}
		sealedAttempt.claimPublication();
		traditionalCapture.claimCombinedPublication();
		target.claim();
		target.requireBindings(core.getBindings());
		validateSealedAttempt(core, sealedAttempt);
		validateTraditionalCapture(core, traditionalCapture);
		byte[] coreBytes = core.getCanonicalCoreBytes();
		byte[] sealBytes = canonicalSealJson(
				core, sealedAttempt, traditionalCapture);
		long expectedPrefixSize = exactPrefixSize(core, coreBytes, sealBytes);
		if (expectedPrefixSize < 0L
				|| expectedPrefixSize > MAX_BUNDLE_BYTES - 32L) {
			throw new IOException(
					"Endpoint receipt bundle exceeds the registered 128 MiB profile.");
		}

		target.verifyBeforeWrite();
		BasicFileAttributes pendingIdentity;
		byte[] prefixSha256;
		byte[] fullSha256;
		long fullSize = expectedPrefixSize + 32L;
		try (FileChannel channel = FileChannel.open(
				target.pending,
				StandardOpenOption.CREATE_NEW,
				StandardOpenOption.READ,
				StandardOpenOption.WRITE,
				LinkOption.NOFOLLOW_LINKS)) {
			pendingIdentity = Files.readAttributes(
					target.pending, BasicFileAttributes.class,
					LinkOption.NOFOLLOW_LINKS);
			requireRegularIdentity(pendingIdentity, "receipt pending path");
			MessageDigest prefixDigest = newSha256();
			ChannelDigestOutputStream sink =
					new ChannelDigestOutputStream(channel, prefixDigest);
			DataOutputStream writer = new DataOutputStream(sink);
			writer.write(MAGIC);
			writer.writeInt(VERSION);
			writer.writeLong(coreBytes.length);
			writer.writeLong(sealBytes.length);
			writer.writeInt(core.getSections().size());
			writer.write(coreBytes);
			writer.write(sealBytes);
			for (M9EndpointReceiptCore.SectionDescriptor section
					: core.getSections()) {
				writeAsciiShort(writer, section.getName());
				writeAsciiShort(writer, section.getFormat());
				writer.writeLong(section.getSizeBytes());
				writer.write(section.getContentSha256());
				writer.write(section.getTypedSha256());
				long before = sink.getCount();
				core.writeCanonicalSection(section.getName(), sink);
				if (sink.getCount() - before != section.getSizeBytes()) {
					throw new IOException(
							"Canonical receipt section length changed during bundle write.");
				}
			}
			writer.flush();
			if (sink.getCount() != expectedPrefixSize) {
				throw new IOException(
						"Canonical receipt prefix has the wrong byte census.");
			}
			prefixSha256 = prefixDigest.digest();
			writeFully(channel, ByteBuffer.wrap(prefixSha256));
			channel.force(true);
			if (channel.size() != fullSize) {
				throw new IOException(
						"Canonical receipt container has the wrong final size.");
			}
			verifyPrefixAndTrailer(channel, expectedPrefixSize, prefixSha256);
			fullSha256 = sha256(channel, fullSize);
		} catch (FileAlreadyExistsException exists) {
			throw new IOException(
					"Endpoint receipt pending path already exists: " + target.pending,
					exists);
		}

		target.verifyPending(pendingIdentity, fullSize, fullSha256);
		try {
			Files.createLink(target.destination, target.pending);
		} catch (FileAlreadyExistsException exists) {
			throw new IOException(
					"Endpoint receipt destination already exists: " + target.destination,
					exists);
		}
		forceDirectory(target.parent);
		target.verifyPublished(pendingIdentity, fullSize, fullSha256);
		return new PublishedReceipt(
				target.pending, target.destination, fullSize,
				fullSha256, prefixSha256, core.getCanonicalCoreSha256(),
				sha256(sealBytes));
	}

	private static void validateSealedAttempt(
			M9EndpointReceiptCore core,
			M9EndpointSynthesisHook.SealedAttempt sealed) {
		if (sealed.getSynthesisEntries() != 1
				|| sealed.getImmutableCaptures() != 1
				|| sealed.getRejectedSynthesisEntries() != 0
				|| !sealed.usesProductionLedger()
				|| !sealed.isAttemptConsumed()
				|| !Arrays.equals(sealed.getCapturedReceiptSha256(),
						core.getCanonicalCoreSha256())) {
			throw new IllegalArgumentException(
					"Endpoint hook seal differs from the canonical receipt core.");
		}
	}

	private static void validateTraditionalCapture(
			M9EndpointReceiptCore core,
			TraditionalPreGrSnapshotHook.SealedCapture sealed) {
		if (!core.hasTraditionalSnapshotIdentity(sealed.getSnapshot())
				|| sealed.getCaptureAttempts() != 1
				|| sealed.getNativeUpdateGrEntries() != 0
				|| !sealed.usesProductionLedger()
				|| !sealed.isAttemptConsumed()) {
			throw new IllegalArgumentException(
					"Traditional pre-GR seal differs from the canonical combined receipt.");
		}
	}

	private static byte[] canonicalSealJson(
			M9EndpointReceiptCore core,
			M9EndpointSynthesisHook.SealedAttempt sealed,
			TraditionalPreGrSnapshotHook.SealedCapture traditional) {
		StringBuilder result = new StringBuilder(1024);
		result.append("{\"attempt\":{");
		result.append("\"attempt_consumed\":")
				.append(sealed.isAttemptConsumed()).append(',');
		result.append("\"immutable_captures\":")
				.append(sealed.getImmutableCaptures()).append(',');
		result.append("\"production_ledger\":")
				.append(sealed.usesProductionLedger()).append(',');
		result.append("\"rejected_synthesis_entries\":")
				.append(sealed.getRejectedSynthesisEntries()).append(',');
		result.append("\"synthesis_entries\":")
				.append(sealed.getSynthesisEntries()).append("},");
		result.append("\"canonicalization\":\"")
				.append(M9EndpointReceiptCore.CANONICALIZATION).append("\",");
		result.append("\"core\":{");
		result.append("\"content_sha256\":\"")
				.append(hex(core.getCanonicalCoreSha256())).append("\",");
		result.append("\"size_bytes\":")
				.append(core.getCanonicalCoreBytes().length).append(',');
		result.append("\"typed_sha256\":\"")
				.append(hex(core.getCanonicalCoreTypedSha256())).append("\"},");
		result.append("\"domain\":\"").append(SEAL_DOMAIN).append("\",");
		result.append("\"schema_version\":\"").append(SEAL_SCHEMA)
				.append("\",");
		result.append("\"traditional_pre_gr\":{");
		result.append("\"attempt_consumed\":")
				.append(traditional.isAttemptConsumed()).append(',');
		result.append("\"capture_attempts\":")
				.append(traditional.getCaptureAttempts()).append(',');
		result.append("\"native_update_gr_entries\":")
				.append(traditional.getNativeUpdateGrEntries()).append(',');
		result.append("\"production_ledger\":")
				.append(traditional.usesProductionLedger()).append("}}\n");
		return result.toString().getBytes(StandardCharsets.US_ASCII);
	}

	private static long exactPrefixSize(
			M9EndpointReceiptCore core,
			byte[] coreBytes,
			byte[] sealBytes) throws IOException {
		long size = MAGIC.length + 4L + 8L + 8L + 4L;
		size = checkedAdd(size, coreBytes.length);
		size = checkedAdd(size, sealBytes.length);
		for (M9EndpointReceiptCore.SectionDescriptor section : core.getSections()) {
			byte[] name = exactAscii(section.getName());
			byte[] format = exactAscii(section.getFormat());
			if (name.length > 0xffff || format.length > 0xffff) {
				throw new IOException("Endpoint receipt section identifier is too long.");
			}
			size = checkedAdd(size, 2L + name.length);
			size = checkedAdd(size, 2L + format.length);
			size = checkedAdd(size, 8L + 32L + 32L);
			size = checkedAdd(size, section.getSizeBytes());
		}
		return size;
	}

	private static long checkedAdd(long left, long right) throws IOException {
		if (right < 0L || left < 0L || left > Long.MAX_VALUE - right) {
			throw new IOException("Endpoint receipt bundle size overflow.");
		}
		return left + right;
	}

	private static void writeAsciiShort(
			DataOutputStream output,
			String value) throws IOException {
		byte[] bytes = exactAscii(value);
		if (bytes.length > 0xffff) {
			throw new IOException("Endpoint receipt ASCII field is too long.");
		}
		output.writeShort(bytes.length);
		output.write(bytes);
	}

	private static byte[] exactAscii(String value) {
		if (value == null || value.isEmpty()) {
			throw new IllegalArgumentException(
					"Endpoint receipt ASCII field is absent.");
		}
		byte[] bytes = value.getBytes(StandardCharsets.US_ASCII);
		if (!value.equals(new String(bytes, StandardCharsets.US_ASCII))) {
			throw new IllegalArgumentException(
					"Endpoint receipt field is not exact ASCII.");
		}
		return bytes;
	}

	private static void verifyPrefixAndTrailer(
			FileChannel channel,
			long prefixSize,
			byte[] expectedPrefixDigest) throws IOException {
		MessageDigest digest = newSha256();
		channel.position(0L);
		ByteBuffer buffer = ByteBuffer.allocate(64 * 1024);
		long remaining = prefixSize;
		while (remaining > 0L) {
			buffer.clear();
			buffer.limit((int) Math.min(buffer.capacity(), remaining));
			int read = channel.read(buffer);
			if (read <= 0) {
				throw new IOException("Canonical receipt prefix is truncated.");
			}
			digest.update(buffer.array(), 0, read);
			remaining -= read;
		}
		byte[] trailer = new byte[32];
		readFully(channel, ByteBuffer.wrap(trailer));
		if (!Arrays.equals(digest.digest(), expectedPrefixDigest)
				|| !Arrays.equals(trailer, expectedPrefixDigest)) {
			throw new IOException("Canonical receipt trailer digest differs.");
		}
	}

	private static byte[] sha256(FileChannel channel, long size) throws IOException {
		MessageDigest digest = newSha256();
		channel.position(0L);
		ByteBuffer buffer = ByteBuffer.allocate(64 * 1024);
		long remaining = size;
		while (remaining > 0L) {
			buffer.clear();
			buffer.limit((int) Math.min(buffer.capacity(), remaining));
			int read = channel.read(buffer);
			if (read <= 0) throw new IOException("Endpoint receipt file is truncated.");
			digest.update(buffer.array(), 0, read);
			remaining -= read;
		}
		return digest.digest();
	}

	private static byte[] sha256(Path path, long size) throws IOException {
		try (FileChannel input = FileChannel.open(
				path, StandardOpenOption.READ, LinkOption.NOFOLLOW_LINKS)) {
			if (input.size() != size) {
				throw new IOException("Endpoint receipt path has the wrong size.");
			}
			return sha256(input, size);
		}
	}

	private static byte[] sha256(byte[] value) {
		return newSha256().digest(value.clone());
	}

	private static MessageDigest newSha256() {
		try {
			return MessageDigest.getInstance("SHA-256");
		} catch (NoSuchAlgorithmException impossible) {
			throw new IllegalStateException(
					"The registered SHA-256 runtime is unavailable.", impossible);
		}
	}

	private static void writeFully(FileChannel channel, ByteBuffer value)
			throws IOException {
		while (value.hasRemaining()) {
			if (channel.write(value) <= 0) {
				throw new IOException("Endpoint receipt write made no progress.");
			}
		}
	}

	private static void readFully(FileChannel channel, ByteBuffer value)
			throws IOException {
		while (value.hasRemaining()) {
			if (channel.read(value) <= 0) {
				throw new IOException("Endpoint receipt read is truncated.");
			}
		}
	}

	private static void forceDirectory(Path directory) throws IOException {
		try (FileChannel channel = FileChannel.open(
				directory, StandardOpenOption.READ, LinkOption.NOFOLLOW_LINKS)) {
			channel.force(true);
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

	private static void requireRegularIdentity(
			BasicFileAttributes value,
			String role) throws IOException {
		if (!value.isRegularFile() || value.isSymbolicLink()
				|| value.fileKey() == null) {
			throw new IOException(role + " has no stable regular-file identity.");
		}
	}

	private static void requireSameIdentity(
			BasicFileAttributes expected,
			BasicFileAttributes actual,
			String role) throws IOException {
		if (expected.fileKey() == null || actual.fileKey() == null
				|| !expected.fileKey().equals(actual.fileKey())) {
			throw new IOException(role + " identity changed.");
		}
	}

	private static void rejectSymbolicComponents(Path path) throws IOException {
		Path absolute = path.toAbsolutePath().normalize();
		Path current = absolute.getRoot();
		if (current == null) throw new IOException("Receipt path has no filesystem root.");
		for (Path part : absolute) {
			current = current.resolve(part);
			BasicFileAttributes attributes = Files.readAttributes(
					current, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
			if (attributes.isSymbolicLink()) {
				throw new IOException(
						"Endpoint receipt path contains a symbolic component: " + current);
			}
		}
	}

	public static final class PublicationTarget {
		private final Path pending;
		private final Path destination;
		private final Path parent;
		private final BasicFileAttributes parentIdentity;
		private final String expectedCaseId;
		private final String expectedAttemptId;
		private final String expectedAttemptClaimSha256;
		private boolean consumed;

		private static PublicationTarget capture(
				Path suppliedPending,
				Path suppliedDestination,
				String expectedCaseId,
				String expectedAttemptId,
				String expectedAttemptClaimSha256) throws IOException {
			if (suppliedPending == null || suppliedDestination == null) {
				throw new IllegalArgumentException(
						"Pending and final endpoint receipt paths are required.");
			}
			Path pending = suppliedPending.toAbsolutePath().normalize();
			Path destination = suppliedDestination.toAbsolutePath().normalize();
			if (expectedCaseId == null
					|| !expectedCaseId.matches("[A-Za-z0-9][A-Za-z0-9._:-]*")
					|| expectedAttemptId == null
					|| !expectedAttemptId.matches("[A-Za-z0-9][A-Za-z0-9._:-]*")
					|| expectedAttemptClaimSha256 == null
					|| !expectedAttemptClaimSha256.matches("[0-9a-f]{64}")) {
				throw new IOException(
						"Endpoint receipt target has invalid case/attempt bindings.");
			}
			if (pending.equals(destination)
					|| pending.getParent() == null
					|| !pending.getParent().equals(destination.getParent())) {
				throw new IOException(
						"Pending and final receipt paths must be distinct siblings.");
			}
			Path parent = pending.getParent();
			if (!PENDING_NAME.equals(pending.getFileName().toString())
					|| !DESTINATION_NAME.equals(destination.getFileName().toString())
					|| parent.getFileName() == null
					|| !expectedCaseId.equals(parent.getFileName().toString())) {
				throw new IOException(
						"Endpoint receipt paths do not identify the registered case attempt.");
			}
			rejectSymbolicComponents(parent);
			BasicFileAttributes parentIdentity = Files.readAttributes(
					parent, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
			if (!parentIdentity.isDirectory() || parentIdentity.isSymbolicLink()
					|| parentIdentity.fileKey() == null) {
				throw new IOException(
						"Endpoint receipt parent has no stable directory identity.");
			}
			Set<PosixFilePermission> permissions;
			try {
				permissions = Files.getPosixFilePermissions(
						parent, LinkOption.NOFOLLOW_LINKS);
			} catch (UnsupportedOperationException unsupported) {
				throw new IOException(
						"Endpoint receipt requires a POSIX private attempt directory.",
						unsupported);
			}
			Set<PosixFilePermission> expectedPermissions =
					java.util.EnumSet.of(
							PosixFilePermission.OWNER_READ,
							PosixFilePermission.OWNER_WRITE,
							PosixFilePermission.OWNER_EXECUTE);
			if (!permissions.equals(expectedPermissions)) {
				throw new IOException(
						"Endpoint receipt attempt directory must have mode 0700.");
			}
			if (Files.exists(pending, LinkOption.NOFOLLOW_LINKS)
					|| Files.exists(destination, LinkOption.NOFOLLOW_LINKS)) {
				throw new IOException(
						"Endpoint receipt output path already exists.");
			}
			forceDirectory(parent);
			return new PublicationTarget(
					pending, destination, parent, parentIdentity,
					expectedCaseId, expectedAttemptId,
					expectedAttemptClaimSha256);
		}

		private PublicationTarget(
				Path pending,
				Path destination,
				Path parent,
				BasicFileAttributes parentIdentity,
				String expectedCaseId,
				String expectedAttemptId,
				String expectedAttemptClaimSha256) {
			this.pending = pending;
			this.destination = destination;
			this.parent = parent;
			this.parentIdentity = parentIdentity;
			this.expectedCaseId = expectedCaseId;
			this.expectedAttemptId = expectedAttemptId;
			this.expectedAttemptClaimSha256 = expectedAttemptClaimSha256;
		}

		private void requireBindings(M9EndpointReceiptCore.Bindings bindings) {
			String claim = bindings.getSha256Bindings().get(
					"attempt_claim_sha256");
			if (!expectedCaseId.equals(bindings.getCaseId())
					|| !expectedAttemptId.equals(bindings.getAttemptId())
					|| !expectedAttemptClaimSha256.equals(claim)) {
				throw new IllegalArgumentException(
						"Endpoint receipt target differs from its case/attempt claim bindings.");
			}
		}

		private synchronized void claim() {
			if (consumed) {
				throw new IllegalStateException(
						"Endpoint receipt publication target was already consumed.");
			}
			consumed = true;
		}

		private void verifyBeforeWrite() throws IOException {
			BasicFileAttributes currentParent = Files.readAttributes(
					parent, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
			requireSameIdentity(
					parentIdentity, currentParent, "Endpoint receipt parent");
			if (Files.exists(pending, LinkOption.NOFOLLOW_LINKS)
					|| Files.exists(destination, LinkOption.NOFOLLOW_LINKS)) {
				throw new IOException("Endpoint receipt output was created before write.");
			}
		}

		private void verifyPending(
				BasicFileAttributes identity,
				long size,
				byte[] digest) throws IOException {
			BasicFileAttributes actual = Files.readAttributes(
					pending, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
			requireRegularIdentity(actual, "receipt pending path");
			requireSameIdentity(identity, actual, "Endpoint receipt pending path");
			if (actual.size() != size
					|| !Arrays.equals(sha256(pending, size), digest)) {
				throw new IOException("Endpoint receipt pending path failed exact verification.");
			}
		}

		private void verifyPublished(
				BasicFileAttributes pendingIdentity,
				long size,
				byte[] digest) throws IOException {
			BasicFileAttributes currentParent = Files.readAttributes(
					parent, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
			requireSameIdentity(
					parentIdentity, currentParent, "Endpoint receipt parent");
			BasicFileAttributes pendingAttributes = Files.readAttributes(
					pending, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
			BasicFileAttributes finalAttributes = Files.readAttributes(
					destination, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
			requireRegularIdentity(pendingAttributes, "receipt pending path");
			requireRegularIdentity(finalAttributes, "receipt final path");
			requireSameIdentity(
					pendingIdentity, pendingAttributes, "Endpoint receipt pending path");
			requireSameIdentity(
					pendingIdentity, finalAttributes, "Endpoint receipt hard link");
			if (finalAttributes.size() != size
					|| !Arrays.equals(sha256(destination, size), digest)) {
				throw new IOException("Published endpoint receipt failed exact verification.");
			}
		}

		public Path getPendingPath() { return pending; }
		public Path getDestinationPath() { return destination; }
	}

	public static final class PublishedReceipt {
		private final Path pendingPath;
		private final Path destinationPath;
		private final long sizeBytes;
		private final byte[] sha256;
		private final byte[] prefixSha256;
		private final byte[] coreSha256;
		private final byte[] sealSha256;

		private PublishedReceipt(
				Path pendingPath,
				Path destinationPath,
				long sizeBytes,
				byte[] sha256,
				byte[] prefixSha256,
				byte[] coreSha256,
				byte[] sealSha256) {
			this.pendingPath = pendingPath;
			this.destinationPath = destinationPath;
			this.sizeBytes = sizeBytes;
			this.sha256 = sha256.clone();
			this.prefixSha256 = prefixSha256.clone();
			this.coreSha256 = coreSha256.clone();
			this.sealSha256 = sealSha256.clone();
		}

		public Path getPendingPath() { return pendingPath; }
		public Path getDestinationPath() { return destinationPath; }
		public long getSizeBytes() { return sizeBytes; }
		public byte[] getSha256() { return sha256.clone(); }
		public byte[] getPrefixSha256() { return prefixSha256.clone(); }
		public byte[] getCoreSha256() { return coreSha256.clone(); }
		public byte[] getSealSha256() { return sealSha256.clone(); }
	}

	private static final class ChannelDigestOutputStream extends OutputStream {
		private final FileChannel channel;
		private final MessageDigest digest;
		private long count;

		private ChannelDigestOutputStream(
				FileChannel channel,
				MessageDigest digest) {
			this.channel = channel;
			this.digest = digest;
		}

		@Override
		public void write(int value) throws IOException {
			byte[] single = new byte[]{(byte) value};
			write(single, 0, 1);
		}

		@Override
		public void write(byte[] value, int offset, int length) throws IOException {
			if (length < 0 || count > Long.MAX_VALUE - length) {
				throw new IOException("Endpoint receipt output size overflow.");
			}
			writeFully(channel, ByteBuffer.wrap(value, offset, length));
			digest.update(value, offset, length);
			count += length;
		}

		private long getCount() { return count; }
	}
}
