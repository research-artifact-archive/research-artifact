package ltsa.updatingControllers.otf;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.channels.FileChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.FileAlreadyExistsException;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.nio.file.attribute.BasicFileAttributes;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

/** Canonical binary serializer for checked compact-game certificates. */
public final class CompactStrongCertificate {

    public static final byte[] MAGIC = "FGDUCR01".getBytes(StandardCharsets.US_ASCII);
    public static final int VERSION = 1;
    public static final int HEADER_BYTES = 128;
    public static final int DECISION_WINNING = 1;
    public static final int DECISION_LOSING = 2;

    private CompactStrongCertificate() {
        // Utility class.
    }

    /**
     * Writes a certificate only after the ordinary exhaustive checker accepts
     * it for the exact mapped game.  The destination and every existing path
     * component must be non-symlink; the final file is created exclusively.
     */
    public static WriteResult writeChecked(
            Path suppliedDestination,
            CompactStrongGame game,
            OtfDucsResult<Integer, Integer, Integer> result) throws IOException {
        return writeChecked(suppliedDestination, game, result,
                new WriteFaultInjector() {
                    @Override
                    public void afterHeader(Path destination) {
                        // Production path has no injected failure.
                    }
                });
    }

    static WriteResult writeChecked(
            Path suppliedDestination,
            CompactStrongGame game,
            OtfDucsResult<Integer, Integer, Integer> result,
            WriteFaultInjector faultInjector) throws IOException {
        Objects.requireNonNull(game, "game");
        Objects.requireNonNull(result, "result");
        Objects.requireNonNull(faultInjector, "faultInjector");
        OtfDucsCertificateChecker.VerificationReport report =
                new OtfDucsCertificateChecker<Integer, Integer, Integer>(game)
                        .verify(result);
        if (!report.isValid()) {
            throw new IOException("refusing to serialize an invalid certificate: "
                    + report.violations());
        }

        Path destination = Objects.requireNonNull(
                suppliedDestination, "certificate destination")
                .toAbsolutePath().normalize();
        Path parent = destination.getParent();
        if (parent == null) {
            throw new IOException("certificate destination has no parent");
        }
        rejectSymbolicComponents(parent);
        BasicFileAttributes parentBefore = Files.readAttributes(
                parent, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
        if (!parentBefore.isDirectory() || parentBefore.isSymbolicLink()) {
            throw new IOException("certificate parent is not a regular directory");
        }
        requireUsableFileKey(parentBefore, "certificate parent");
        if (Files.exists(destination, LinkOption.NOFOLLOW_LINKS)) {
            throw new IOException("certificate destination already exists: " + destination);
        }

        CertificateArrays arrays = CertificateArrays.from(game, result);
        long size = arrays.fileSize();
        if (size > Integer.MAX_VALUE) {
            throw new IOException("certificate exceeds the registered 2 GiB format bound");
        }
        String digest;
        BasicFileAttributes destinationIdentity;
        try {
            /*
             * There is no portable Java primitive for an exclusive atomic
             * rename that also refuses an existing destination.  Create the
             * registered final name exactly once instead.  A failed write is
             * deliberately retained as non-PASS evidence; cleanup must never
             * unlink a path that a concurrent writer may have replaced.
             */
            try (FileChannel output = FileChannel.open(
                    destination,
                    StandardOpenOption.CREATE_NEW,
                    StandardOpenOption.READ,
                    StandardOpenOption.WRITE,
                    LinkOption.NOFOLLOW_LINKS)) {
                destinationIdentity = Files.readAttributes(
                        destination, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
                requireUsableFileKey(destinationIdentity, "certificate destination");
                if (!destinationIdentity.isRegularFile()
                        || destinationIdentity.isSymbolicLink()) {
                    throw new IOException("certificate destination is not a regular file");
                }
                writeFully(output, arrays.header(size, game.sha256()));
                faultInjector.afterHeader(destination);
                writeInts(output, arrays.roots);
                writePairs(output, arrays.rankStates, arrays.ranks);
                writeInts(output, arrays.strategySources);
                writeInts(output, arrays.strategyActions);
                writeLongs(output, arrays.strategyTargetOffsets);
                writeInts(output, arrays.strategyTargets);
                writeInts(output, arrays.goalStates);
                writeInts(output, arrays.losingStates);
                output.force(true);
                if (output.size() != size) {
                    throw new IOException("private certificate has the wrong size");
                }
                output.position(0L);
                digest = sha256(output);
            }
            BasicFileAttributes parentAfter = Files.readAttributes(
                    parent, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
            requireSameFile(parentBefore, parentAfter,
                    "certificate parent changed while writing");
            BasicFileAttributes certificate = Files.readAttributes(
                    destination, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
            requireSameFile(destinationIdentity, certificate,
                    "certificate destination changed while writing");
            if (!certificate.isRegularFile() || certificate.isSymbolicLink()
                    || certificate.size() != size || !sha256(destination).equals(digest)) {
                throw new IOException("published certificate failed exact validation");
            }
        } catch (FileAlreadyExistsException error) {
            throw new IOException("certificate destination already exists: " + destination,
                    error);
        }
        return new WriteResult(destination, digest, size,
                arrays.decision, arrays.roots.length, arrays.rankStates.length,
                arrays.strategySources.length, arrays.strategyTargets.length,
                arrays.goalStates.length, arrays.losingStates.length);
    }

    interface WriteFaultInjector {
        void afterHeader(Path destination) throws IOException;
    }

    public static final class WriteResult {
        private final Path path;
        private final String sha256;
        private final long sizeBytes;
        private final int decision;
        private final int rootCount;
        private final int rankCount;
        private final int strategyBucketCount;
        private final int strategyOutcomeCount;
        private final int goalCount;
        private final int losingCount;

        private WriteResult(
                Path path,
                String sha256,
                long sizeBytes,
                int decision,
                int rootCount,
                int rankCount,
                int strategyBucketCount,
                int strategyOutcomeCount,
                int goalCount,
                int losingCount) {
            this.path = path;
            this.sha256 = sha256;
            this.sizeBytes = sizeBytes;
            this.decision = decision;
            this.rootCount = rootCount;
            this.rankCount = rankCount;
            this.strategyBucketCount = strategyBucketCount;
            this.strategyOutcomeCount = strategyOutcomeCount;
            this.goalCount = goalCount;
            this.losingCount = losingCount;
        }

        public Path path() { return path; }
        public String sha256() { return sha256; }
        public long sizeBytes() { return sizeBytes; }
        public int decision() { return decision; }
        public int rootCount() { return rootCount; }
        public int rankCount() { return rankCount; }
        public int strategyBucketCount() { return strategyBucketCount; }
        public int strategyOutcomeCount() { return strategyOutcomeCount; }
        public int goalCount() { return goalCount; }
        public int losingCount() { return losingCount; }
    }

    private static final class CertificateArrays {
        private final int decision;
        private final int[] roots;
        private final int[] rankStates;
        private final int[] ranks;
        private final int[] strategySources;
        private final int[] strategyActions;
        private final long[] strategyTargetOffsets;
        private final int[] strategyTargets;
        private final int[] goalStates;
        private final int[] losingStates;

        private CertificateArrays(
                int decision,
                int[] roots,
                int[] rankStates,
                int[] ranks,
                int[] strategySources,
                int[] strategyActions,
                long[] strategyTargetOffsets,
                int[] strategyTargets,
                int[] goalStates,
                int[] losingStates) {
            this.decision = decision;
            this.roots = roots;
            this.rankStates = rankStates;
            this.ranks = ranks;
            this.strategySources = strategySources;
            this.strategyActions = strategyActions;
            this.strategyTargetOffsets = strategyTargetOffsets;
            this.strategyTargets = strategyTargets;
            this.goalStates = goalStates;
            this.losingStates = losingStates;
        }

        private static CertificateArrays from(
                CompactStrongGame game,
                OtfDucsResult<Integer, Integer, Integer> result) throws IOException {
            int[] roots = sortedIds(game.initialStates(), game.stateCount(), "root");
            if (!result.isWinning()) {
                int[] losing = sortedIds(
                        result.losingCertificate().losingStates(),
                        game.stateCount(), "losing state");
                return new CertificateArrays(
                        DECISION_LOSING, roots, new int[0], new int[0],
                        new int[0], new int[0], new long[] {0L}, new int[0],
                        new int[0], losing);
            }

            OtfDucsResult.WinningCertificate<Integer, Integer, Integer> certificate =
                    result.winningCertificate();
            List<Integer> rankStatesList = new ArrayList<Integer>(
                    certificate.ranks().keySet());
            Collections.sort(rankStatesList);
            int[] rankStates = new int[rankStatesList.size()];
            int[] ranks = new int[rankStatesList.size()];
            for (int index = 0; index < rankStatesList.size(); index++) {
                int state = checkedId(rankStatesList.get(index),
                        game.stateCount(), "rank state");
                Integer rank = certificate.ranks().get(Integer.valueOf(state));
                if (rank == null || rank.intValue() < 0) {
                    throw new IOException("invalid certificate rank for state " + state);
                }
                rankStates[index] = state;
                ranks[index] = rank.intValue();
            }

            List<Bucket> buckets = new ArrayList<Bucket>();
            long outcomeCount = 0L;
            for (Map.Entry<Integer, Map<Integer, Set<Integer>>> stateEntry
                    : certificate.strategy().entrySet()) {
                int source = checkedId(stateEntry.getKey(),
                        game.stateCount(), "strategy source");
                for (Map.Entry<Integer, Set<Integer>> actionEntry
                        : stateEntry.getValue().entrySet()) {
                    int action = checkedId(actionEntry.getKey(),
                            game.actionCount(), "strategy action");
                    int[] targets = sortedIds(actionEntry.getValue(),
                            game.stateCount(), "strategy target");
                    if (targets.length == 0) {
                        throw new IOException("strategy contains an empty bucket");
                    }
                    outcomeCount = Math.addExact(outcomeCount, targets.length);
                    buckets.add(new Bucket(source, action, targets));
                }
            }
            Collections.sort(buckets, new Comparator<Bucket>() {
                @Override
                public int compare(Bucket left, Bucket right) {
                    int byState = Integer.compare(left.source, right.source);
                    return byState != 0
                            ? byState : Integer.compare(left.action, right.action);
                }
            });
            if (outcomeCount > Integer.MAX_VALUE) {
                throw new IOException("strategy outcome census exceeds format bound");
            }
            int[] sources = new int[buckets.size()];
            int[] actions = new int[buckets.size()];
            long[] offsets = new long[buckets.size() + 1];
            int[] targets = new int[(int) outcomeCount];
            int cursor = 0;
            for (int index = 0; index < buckets.size(); index++) {
                Bucket bucket = buckets.get(index);
                if (index > 0 && bucket.source == buckets.get(index - 1).source
                        && bucket.action == buckets.get(index - 1).action) {
                    throw new IOException("duplicate strategy bucket");
                }
                sources[index] = bucket.source;
                actions[index] = bucket.action;
                offsets[index] = cursor;
                System.arraycopy(bucket.targets, 0, targets, cursor,
                        bucket.targets.length);
                cursor += bucket.targets.length;
            }
            offsets[buckets.size()] = cursor;
            int[] goals = sortedIds(certificate.goalMatches().keySet(),
                    game.stateCount(), "goal match");
            for (int goal : goals) {
                Integer match = certificate.goalMatches().get(Integer.valueOf(goal));
                if (match == null || match.intValue() != goal) {
                    throw new IOException("compact goal match is not the canonical state ID");
                }
            }
            return new CertificateArrays(
                    DECISION_WINNING, roots, rankStates, ranks, sources, actions,
                    offsets, targets, goals, new int[0]);
        }

        private long fileSize() throws IOException {
            try {
                long size = HEADER_BYTES;
                size = Math.addExact(size, Math.multiplyExact((long) roots.length, 4L));
                size = Math.addExact(size, Math.multiplyExact((long) rankStates.length, 8L));
                size = Math.addExact(size, Math.multiplyExact(
                        (long) strategySources.length, 8L));
                size = Math.addExact(size, Math.multiplyExact(
                        (long) strategyTargetOffsets.length, 8L));
                size = Math.addExact(size, Math.multiplyExact(
                        (long) strategyTargets.length, 4L));
                size = Math.addExact(size, Math.multiplyExact((long) goalStates.length, 4L));
                return Math.addExact(size, Math.multiplyExact((long) losingStates.length, 4L));
            } catch (ArithmeticException error) {
                throw new IOException("certificate size overflows", error);
            }
        }

        private ByteBuffer header(long size, String gameSha256) throws IOException {
            byte[] gameDigest = parseSha256(gameSha256);
            ByteBuffer header = ByteBuffer.allocate(HEADER_BYTES)
                    .order(ByteOrder.LITTLE_ENDIAN);
            header.put(MAGIC);
            header.putInt(VERSION);
            header.putInt(HEADER_BYTES);
            header.putLong(size);
            header.putInt(decision);
            header.putInt(0); // reserved
            header.putInt(roots.length);
            header.putInt(0); // reserved
            header.putLong(rankStates.length);
            header.putLong(strategySources.length);
            header.putLong(strategyTargets.length);
            header.putLong(goalStates.length);
            header.putLong(losingStates.length);
            header.put(gameDigest);
            while (header.position() < HEADER_BYTES) header.put((byte) 0);
            header.flip();
            return header;
        }
    }

    private static final class Bucket {
        private final int source;
        private final int action;
        private final int[] targets;

        private Bucket(int source, int action, int[] targets) {
            this.source = source;
            this.action = action;
            this.targets = targets;
        }
    }

    private static int[] sortedIds(Set<Integer> values, int bound, String label)
            throws IOException {
        List<Integer> sorted = new ArrayList<Integer>(values);
        Collections.sort(sorted);
        int[] result = new int[sorted.size()];
        int previous = -1;
        for (int index = 0; index < sorted.size(); index++) {
            int value = checkedId(sorted.get(index), bound, label);
            if (value <= previous) {
                throw new IOException(label + " values are not unique");
            }
            result[index] = value;
            previous = value;
        }
        return result;
    }

    private static int checkedId(Integer value, int bound, String label)
            throws IOException {
        if (value == null || value.intValue() < 0 || value.intValue() >= bound) {
            throw new IOException(label + " is outside the registered dense domain: " + value);
        }
        return value.intValue();
    }

    private static void writeFully(FileChannel output, ByteBuffer buffer)
            throws IOException {
        while (buffer.hasRemaining()) output.write(buffer);
    }

    private static void writeInts(FileChannel output, int[] values)
            throws IOException {
        ByteBuffer buffer = ByteBuffer.allocate(bufferBytes(values.length, 4))
                .order(ByteOrder.LITTLE_ENDIAN);
        for (int value : values) {
            if (buffer.remaining() < 4) {
                buffer.flip();
                writeFully(output, buffer);
                buffer.clear();
            }
            buffer.putInt(value);
        }
        buffer.flip();
        writeFully(output, buffer);
    }

    private static void writePairs(
            FileChannel output, int[] left, int[] right) throws IOException {
        if (left.length != right.length) {
            throw new IOException("certificate pair arrays differ in length");
        }
        ByteBuffer buffer = ByteBuffer.allocate(bufferBytes(left.length, 8))
                .order(ByteOrder.LITTLE_ENDIAN);
        for (int index = 0; index < left.length; index++) {
            if (buffer.remaining() < 8) {
                buffer.flip();
                writeFully(output, buffer);
                buffer.clear();
            }
            buffer.putInt(left[index]);
            buffer.putInt(right[index]);
        }
        buffer.flip();
        writeFully(output, buffer);
    }

    private static void writeLongs(FileChannel output, long[] values)
            throws IOException {
        ByteBuffer buffer = ByteBuffer.allocate(bufferBytes(values.length, 8))
                .order(ByteOrder.LITTLE_ENDIAN);
        for (long value : values) {
            if (buffer.remaining() < 8) {
                buffer.flip();
                writeFully(output, buffer);
                buffer.clear();
            }
            buffer.putLong(value);
        }
        buffer.flip();
        writeFully(output, buffer);
    }

    private static byte[] parseSha256(String value) throws IOException {
        if (value == null || !value.matches("[0-9a-f]{64}")) {
            throw new IOException("invalid game SHA-256 in certificate binding");
        }
        byte[] result = new byte[32];
        for (int index = 0; index < result.length; index++) {
            result[index] = (byte) Integer.parseInt(
                    value.substring(index * 2, index * 2 + 2), 16);
        }
        return result;
    }

    private static int bufferBytes(int length, int elementBytes) {
        long requested = Math.max((long) length, 1L) * elementBytes;
        return (int) Math.min(requested, 1024L * 1024L);
    }

    private static String sha256(Path path) throws IOException {
        try (FileChannel input = FileChannel.open(
                path, StandardOpenOption.READ, LinkOption.NOFOLLOW_LINKS)) {
            return sha256(input);
        }
    }

    private static String sha256(FileChannel input) throws IOException {
        MessageDigest digest;
        try {
            digest = MessageDigest.getInstance("SHA-256");
        } catch (NoSuchAlgorithmException error) {
            throw new IllegalStateException("SHA-256 is unavailable", error);
        }
        ByteBuffer buffer = ByteBuffer.allocate(1024 * 1024);
        input.position(0L);
        while (true) {
            int read = input.read(buffer);
            if (read < 0) break;
            if (read == 0) continue;
            buffer.flip();
            digest.update(buffer);
            buffer.clear();
        }
        StringBuilder result = new StringBuilder(64);
        for (byte value : digest.digest()) {
            result.append(String.format("%02x", Byte.valueOf(value)));
        }
        return result.toString();
    }

    private static void requireSameFile(
            BasicFileAttributes expected,
            BasicFileAttributes actual,
            String message) throws IOException {
        requireUsableFileKey(expected, "expected file identity");
        requireUsableFileKey(actual, "actual file identity");
        if (!Objects.equals(expected.fileKey(), actual.fileKey())) {
            throw new IOException(message);
        }
    }

    private static void requireUsableFileKey(
            BasicFileAttributes attributes, String label) throws IOException {
        if (attributes.fileKey() == null) {
            throw new IOException(label + " filesystem does not expose a stable file key");
        }
    }

    private static void rejectSymbolicComponents(Path absolute) throws IOException {
        Path current = absolute.getRoot();
        for (Path component : absolute) {
            current = current == null ? component : current.resolve(component);
            if (Files.isSymbolicLink(current)) {
                throw new IOException("symbolic path component is forbidden: " + current);
            }
        }
    }
}
