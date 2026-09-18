package ltsa.updatingControllers.otf;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.MappedByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.FileAlreadyExistsException;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.nio.file.attribute.BasicFileAttributes;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.AbstractList;
import java.util.AbstractSet;
import java.util.Collection;
import java.util.Collections;
import java.util.Comparator;
import java.util.Iterator;
import java.util.LinkedHashSet;
import java.util.NoSuchElementException;
import java.util.Objects;
import java.util.Set;
import java.util.UUID;

/**
 * Read-only, memory-mapped representation of one completely materialised
 * finite strong reachability game.
 *
 * <p>The format deliberately contains no parser- or source-specific logic.
 * A source projection and its independent reconstruction must first agree on
 * the exact canonical bytes.  Every registered Java solver then consumes the
 * same bytes through this class, while an independently implemented frontend
 * can read the documented primitive arrays directly.</p>
 *
 * <p>All integers are unsigned little-endian values in the file.  Java state
 * and action identifiers are dense non-negative {@link Integer}s.  Only
 * enabled, non-empty action buckets are stored; complete empty-bucket coverage
 * remains an obligation of the source-projection audit.</p>
 */
public final class CompactStrongGame
        implements ImplicitStrongGame<Integer, Integer, Integer>, AutoCloseable {

    public static final byte[] MAGIC = "FGDUGB01".getBytes(StandardCharsets.US_ASCII);
    public static final int VERSION = 1;
    public static final int HEADER_BYTES = 96;

    public static final int ACTION_CONTROLLABLE = 1;
    public static final int ACTION_UPDATE = 2;
    public static final int STATE_SAFE = 1;
    public static final int STATE_GOAL = 2;
    public static final int STATE_STRUCTURALLY_VALID = 4;

    private final Path path;
    private final String sha256;
    private final String semanticSha256;
    private final FileChannel channel;
    private final MappedByteBuffer data;
    private final int stateCount;
    private final int actionCount;
    private final int rootCount;
    private final long bucketCount;
    private final long outcomeCount;
    private final int actionFlagsOffset;
    private final int stateFlagsOffset;
    private final int rootsOffset;
    private final int stateBucketOffsetsOffset;
    private final int bucketActionIdsOffset;
    private final int bucketTargetOffsetsOffset;
    private final int targetsOffset;
    private final Set<Integer> roots;
    private boolean closed;

    private CompactStrongGame(
            Path path,
            String sha256,
            String semanticSha256,
            FileChannel channel,
            MappedByteBuffer data,
            int stateCount,
            int actionCount,
            int rootCount,
            long bucketCount,
            long outcomeCount,
            int actionFlagsOffset,
            int stateFlagsOffset,
            int rootsOffset,
            int stateBucketOffsetsOffset,
            int bucketActionIdsOffset,
            int bucketTargetOffsetsOffset,
            int targetsOffset,
            Set<Integer> roots) {
        this.path = path;
        this.sha256 = sha256;
        this.semanticSha256 = semanticSha256;
        this.channel = channel;
        this.data = data;
        this.stateCount = stateCount;
        this.actionCount = actionCount;
        this.rootCount = rootCount;
        this.bucketCount = bucketCount;
        this.outcomeCount = outcomeCount;
        this.actionFlagsOffset = actionFlagsOffset;
        this.stateFlagsOffset = stateFlagsOffset;
        this.rootsOffset = rootsOffset;
        this.stateBucketOffsetsOffset = stateBucketOffsetsOffset;
        this.bucketActionIdsOffset = bucketActionIdsOffset;
        this.bucketTargetOffsetsOffset = bucketTargetOffsetsOffset;
        this.targetsOffset = targetsOffset;
        this.roots = roots;
    }

    /** Opens and validates an exact regular file with a mandatory SHA-256. */
    public static CompactStrongGame open(
            Path supplied,
            String expectedSha256,
            String expectedSemanticSha256)
            throws IOException {
        Objects.requireNonNull(supplied, "bundle path");
        String expected = requireSha256(expectedSha256);
        String expectedSemantic = requireSha256(expectedSemanticSha256);
        Path absolute = supplied.toAbsolutePath().normalize();
        rejectSymbolicComponents(absolute);
        BasicFileAttributes before = Files.readAttributes(
                absolute, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
        if (!before.isRegularFile() || before.isSymbolicLink()) {
            throw new IOException("game bundle is not a regular non-symlink file: " + absolute);
        }
        if (before.size() < HEADER_BYTES || before.size() > Integer.MAX_VALUE) {
            throw new IOException("game bundle size is outside the supported mapped range: "
                    + before.size());
        }
        FileChannel channel = openPrivateSnapshot();
        boolean success = false;
        try (FileChannel original = FileChannel.open(
                absolute, StandardOpenOption.READ, LinkOption.NOFOLLOW_LINKS)) {
            BasicFileAttributes afterOpen = Files.readAttributes(
                    absolute, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
            requireSameIdentity(before, afterOpen, "while opening");
            String actual = copyAndHash(original, channel);
            if (!actual.equals(expected)) {
                throw new IOException("game bundle SHA-256 mismatch: expected="
                        + expected + ", actual=" + actual);
            }
            BasicFileAttributes afterCopy = Files.readAttributes(
                    absolute, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
            requireSameIdentity(before, afterCopy, "while snapshotting");
            if (channel.size() != before.size()) {
                throw new IOException("private game snapshot has the wrong size");
            }
            channel.force(true);
            MappedByteBuffer mapped = channel.map(
                    FileChannel.MapMode.READ_ONLY, 0L, before.size());
            mapped.order(ByteOrder.LITTLE_ENDIAN);
            if (!sha256(mapped.asReadOnlyBuffer()).equals(expected)) {
                throw new IOException("private mapped game snapshot digest mismatch");
            }
            CompactStrongGame result = parse(
                    absolute, expected, expectedSemantic,
                    channel, mapped, before.size());
            success = true;
            return result;
        } finally {
            if (!success) {
                channel.close();
            }
        }
    }

    private static CompactStrongGame parse(
            Path path,
            String sha256,
            String expectedSemanticSha256,
            FileChannel channel,
            MappedByteBuffer data,
            long fileSize) throws IOException {
        ByteBuffer header = data.asReadOnlyBuffer().order(ByteOrder.LITTLE_ENDIAN);
        byte[] magic = new byte[MAGIC.length];
        header.get(magic);
        if (!MessageDigest.isEqual(magic, MAGIC)) {
            throw new IOException("invalid compact game magic");
        }
        int version = header.getInt();
        int headerBytes = header.getInt();
        long declaredFileSize = header.getLong();
        long stateCountRaw = Integer.toUnsignedLong(header.getInt());
        long actionCountRaw = Integer.toUnsignedLong(header.getInt());
        long rootCountRaw = Integer.toUnsignedLong(header.getInt());
        int reserved32 = header.getInt();
        long bucketCount = header.getLong();
        long outcomeCount = header.getLong();
        long reserved64 = header.getLong();
        byte[] semanticDigest = new byte[32];
        header.get(semanticDigest);
        String semanticSha256 = hex(semanticDigest);
        if (version != VERSION || headerBytes != HEADER_BYTES) {
            throw new IOException("unsupported compact game version/header: "
                    + version + "/" + headerBytes);
        }
        if (declaredFileSize != fileSize || reserved32 != 0 || reserved64 != 0L) {
            throw new IOException("compact game header size/reserved fields are invalid");
        }
        if (!semanticSha256.equals(expectedSemanticSha256)) {
            throw new IOException("compact game semantic SHA-256 mismatch: expected="
                    + expectedSemanticSha256 + ", actual=" + semanticSha256);
        }
        if (stateCountRaw == 0 || actionCountRaw == 0 || rootCountRaw == 0
                || stateCountRaw > Integer.MAX_VALUE
                || actionCountRaw > Integer.MAX_VALUE
                || rootCountRaw > Integer.MAX_VALUE
                || bucketCount < 0L || outcomeCount < 0L
                || bucketCount > Integer.MAX_VALUE
                || outcomeCount > Integer.MAX_VALUE) {
            throw new IOException("compact game census is invalid or unsupported");
        }
        int states = (int) stateCountRaw;
        int actions = (int) actionCountRaw;
        int rootsCount = (int) rootCountRaw;
        if (rootsCount > states) {
            throw new IOException("root count exceeds state count");
        }

        long cursor = HEADER_BYTES;
        int actionFlagsOffset = checkedOffset(cursor, fileSize);
        cursor = checkedAdd(cursor, actions);
        int stateFlagsOffset = checkedOffset(cursor, fileSize);
        cursor = checkedAdd(cursor, states);
        int rootsOffset = checkedOffset(cursor, fileSize);
        cursor = checkedAdd(cursor, checkedMultiply(rootsCount, 4L));
        int stateBucketOffsetsOffset = checkedOffset(cursor, fileSize);
        cursor = checkedAdd(cursor, checkedMultiply(((long) states) + 1L, 8L));
        int bucketActionIdsOffset = checkedOffset(cursor, fileSize);
        cursor = checkedAdd(cursor, checkedMultiply(bucketCount, 4L));
        int bucketTargetOffsetsOffset = checkedOffset(cursor, fileSize);
        cursor = checkedAdd(cursor, checkedMultiply(bucketCount + 1L, 8L));
        int targetsOffset = checkedOffset(cursor, fileSize);
        cursor = checkedAdd(cursor, checkedMultiply(outcomeCount, 4L));
        if (cursor != fileSize) {
            throw new IOException("compact game has trailing or missing bytes: expected="
                    + cursor + ", actual=" + fileSize);
        }

        for (int action = 0; action < actions; action++) {
            int flags = Byte.toUnsignedInt(data.get(actionFlagsOffset + action));
            if ((flags & ~(ACTION_CONTROLLABLE | ACTION_UPDATE)) != 0
                    || ((flags & ACTION_UPDATE) != 0
                    && (flags & ACTION_CONTROLLABLE) == 0)) {
                throw new IOException("invalid action flags at action " + action);
            }
        }
        for (int state = 0; state < states; state++) {
            int flags = Byte.toUnsignedInt(data.get(stateFlagsOffset + state));
            if ((flags & ~(STATE_SAFE | STATE_GOAL | STATE_STRUCTURALLY_VALID)) != 0
                    || (flags & STATE_STRUCTURALLY_VALID) == 0
                    || ((flags & STATE_GOAL) != 0 && (flags & STATE_SAFE) == 0)) {
                throw new IOException("invalid state flags at state " + state);
            }
        }

        LinkedHashSet<Integer> roots = new LinkedHashSet<Integer>();
        int previousRoot = -1;
        for (int index = 0; index < rootsCount; index++) {
            int root = getDenseId(data, rootsOffset + index * 4, states, "root");
            if (root <= previousRoot) {
                throw new IOException("root identifiers are not strictly increasing");
            }
            roots.add(Integer.valueOf(root));
            previousRoot = root;
        }

        validateOffsets(data, stateBucketOffsetsOffset, ((long) states) + 1L,
                bucketCount, "state bucket");
        validateOffsets(data, bucketTargetOffsetsOffset, bucketCount + 1L,
                outcomeCount, "bucket target");
        for (int state = 0; state < states; state++) {
            int first = checkedInt(getLong(data,
                    stateBucketOffsetsOffset + state * 8), "bucket offset");
            int last = checkedInt(getLong(data,
                    stateBucketOffsetsOffset + (state + 1) * 8), "bucket offset");
            int stateFlags = Byte.toUnsignedInt(data.get(stateFlagsOffset + state));
            if (((stateFlags & STATE_SAFE) == 0 || (stateFlags & STATE_GOAL) != 0)
                    && first != last) {
                throw new IOException(
                        "unsafe and Goal states must be terminal in the compact game: "
                                + state);
            }
            int previousAction = -1;
            for (int bucket = first; bucket < last; bucket++) {
                int action = getDenseId(data,
                        bucketActionIdsOffset + bucket * 4, actions, "action");
                if (action <= previousAction) {
                    throw new IOException("actions are not strictly increasing at state " + state);
                }
                previousAction = action;
                int firstTarget = checkedInt(getLong(data,
                        bucketTargetOffsetsOffset + bucket * 8), "target offset");
                int lastTarget = checkedInt(getLong(data,
                        bucketTargetOffsetsOffset + (bucket + 1) * 8), "target offset");
                if (firstTarget == lastTarget) {
                    throw new IOException("stored action bucket is empty at state/action "
                            + state + "/" + action);
                }
                int previousTarget = -1;
                for (int targetIndex = firstTarget; targetIndex < lastTarget; targetIndex++) {
                    int target = getDenseId(data,
                            targetsOffset + targetIndex * 4, states, "target");
                    if (target <= previousTarget) {
                        throw new IOException("targets are not strictly increasing at bucket " + bucket);
                    }
                    previousTarget = target;
                }
            }
        }

        return new CompactStrongGame(
                path, sha256, semanticSha256, channel, data,
                states, actions, rootsCount,
                bucketCount, outcomeCount, actionFlagsOffset, stateFlagsOffset,
                rootsOffset, stateBucketOffsetsOffset, bucketActionIdsOffset,
                bucketTargetOffsetsOffset, targetsOffset,
                Collections.unmodifiableSet(roots));
    }

    public Path path() { return path; }
    public String sha256() { return sha256; }
    public String semanticSha256() { return semanticSha256; }
    public int stateCount() { return stateCount; }
    public int actionCount() { return actionCount; }
    public int rootCount() { return rootCount; }
    public long bucketCount() { return bucketCount; }
    public long outcomeCount() { return outcomeCount; }

    /** Revalidates the exact private mapped bytes after a potentially long solve. */
    public void verifyUnchanged() throws IOException {
        requireOpen();
        String current = sha256(data.asReadOnlyBuffer());
        if (!sha256.equals(current)) {
            throw new IOException("private mapped game bytes changed after opening");
        }
    }

    @Override
    public Set<Integer> initialStates() {
        requireOpen();
        return roots;
    }

    @Override
    public boolean isSafe(Integer state) {
        return (stateFlags(state) & STATE_SAFE) != 0;
    }

    @Override
    public boolean isGoal(Integer state) {
        return (stateFlags(state) & STATE_GOAL) != 0;
    }

    @Override
    public Collection<Integer> candidateActions(Integer state) {
        int id = stateId(state);
        int first = bucketOffset(id);
        int last = bucketOffset(id + 1);
        return new ActionList(first, last);
    }

    @Override
    public Set<Integer> post(Integer state, Integer action) {
        int stateId = stateId(state);
        int actionId = actionId(action);
        int low = bucketOffset(stateId);
        int high = bucketOffset(stateId + 1) - 1;
        while (low <= high) {
            int middle = (low + high) >>> 1;
            int candidate = bucketAction(middle);
            if (candidate < actionId) {
                low = middle + 1;
            } else if (candidate > actionId) {
                high = middle - 1;
            } else {
                return new TargetSet(targetOffset(middle), targetOffset(middle + 1));
            }
        }
        return Collections.emptySet();
    }

    @Override
    public boolean isControllable(Integer action) {
        return (actionFlags(action) & ACTION_CONTROLLABLE) != 0;
    }

    @Override
    public boolean isUpdateAction(Integer action) {
        return (actionFlags(action) & ACTION_UPDATE) != 0;
    }

    @Override
    public Comparator<Integer> actionComparator() {
        return Comparator.naturalOrder();
    }

    @Override
    public Comparator<Integer> stateComparator() {
        return Comparator.naturalOrder();
    }

    @Override
    public Integer goalMatch(Integer goalState) {
        int state = stateId(goalState);
        if (!isGoal(Integer.valueOf(state))) {
            throw new IllegalArgumentException("state is not a Goal: " + state);
        }
        return Integer.valueOf(state);
    }

    @Override
    public boolean isStructurallyValid(Integer state) {
        return (stateFlags(state) & STATE_STRUCTURALLY_VALID) != 0;
    }

    @Override
    public void close() throws IOException {
        if (!closed) {
            closed = true;
            channel.close();
        }
    }

    private int stateFlags(Integer state) {
        int id = stateId(state);
        return Byte.toUnsignedInt(data.get(stateFlagsOffset + id));
    }

    private int actionFlags(Integer action) {
        int id = actionId(action);
        return Byte.toUnsignedInt(data.get(actionFlagsOffset + id));
    }

    private int stateId(Integer state) {
        requireOpen();
        if (state == null || state.intValue() < 0 || state.intValue() >= stateCount) {
            throw new IllegalArgumentException("unknown compact game state: " + state);
        }
        return state.intValue();
    }

    private int actionId(Integer action) {
        requireOpen();
        if (action == null || action.intValue() < 0 || action.intValue() >= actionCount) {
            throw new IllegalArgumentException("unknown compact game action: " + action);
        }
        return action.intValue();
    }

    private int bucketOffset(int stateBoundary) {
        return checkedInt(getLong(data,
                stateBucketOffsetsOffset + stateBoundary * 8), "bucket offset");
    }

    private int targetOffset(int bucketBoundary) {
        return checkedInt(getLong(data,
                bucketTargetOffsetsOffset + bucketBoundary * 8), "target offset");
    }

    private int bucketAction(int bucket) {
        return data.getInt(bucketActionIdsOffset + bucket * 4);
    }

    private int target(int targetIndex) {
        return data.getInt(targetsOffset + targetIndex * 4);
    }

    private void requireOpen() {
        if (closed) {
            throw new IllegalStateException("compact game is closed");
        }
    }

    private final class ActionList extends AbstractList<Integer> {
        private final int first;
        private final int last;

        private ActionList(int first, int last) {
            this.first = first;
            this.last = last;
        }

        @Override
        public Integer get(int index) {
            if (index < 0 || index >= size()) {
                throw new IndexOutOfBoundsException("action index " + index);
            }
            requireOpen();
            return Integer.valueOf(bucketAction(first + index));
        }

        @Override
        public int size() {
            return last - first;
        }
    }

    private final class TargetSet extends AbstractSet<Integer> {
        private final int first;
        private final int last;

        private TargetSet(int first, int last) {
            this.first = first;
            this.last = last;
        }

        @Override
        public Iterator<Integer> iterator() {
            return new Iterator<Integer>() {
                private int cursor = first;

                @Override
                public boolean hasNext() {
                    return cursor < last;
                }

                @Override
                public Integer next() {
                    if (!hasNext()) {
                        throw new NoSuchElementException();
                    }
                    requireOpen();
                    return Integer.valueOf(target(cursor++));
                }
            };
        }

        @Override
        public int size() {
            return last - first;
        }

        @Override
        public boolean contains(Object value) {
            if (!(value instanceof Integer)) {
                return false;
            }
            int wanted = ((Integer) value).intValue();
            int low = first;
            int high = last - 1;
            while (low <= high) {
                int middle = (low + high) >>> 1;
                int candidate = target(middle);
                if (candidate < wanted) low = middle + 1;
                else if (candidate > wanted) high = middle - 1;
                else return true;
            }
            return false;
        }
    }

    private static void validateOffsets(
            ByteBuffer data,
            int offset,
            long count,
            long expectedLast,
            String label) throws IOException {
        long previous = -1L;
        for (long index = 0L; index < count; index++) {
            long value = getLong(data, offset + checkedInt(index * 8L, label), label);
            if (value < 0L || value < previous || value > expectedLast) {
                throw new IOException(label + " offsets are invalid at index " + index);
            }
            if (index == 0L && value != 0L) {
                throw new IOException(label + " offsets must start at zero");
            }
            previous = value;
        }
        if (previous != expectedLast) {
            throw new IOException(label + " offsets do not end at the declared census");
        }
    }

    private static long getLong(ByteBuffer data, int offset) {
        return data.getLong(offset);
    }

    private static long getLong(ByteBuffer data, int offset, String label)
            throws IOException {
        try {
            return data.getLong(offset);
        } catch (IndexOutOfBoundsException error) {
            throw new IOException(label + " offset is outside the bundle", error);
        }
    }

    private static int getDenseId(
            ByteBuffer data, int offset, int bound, String label) throws IOException {
        long value = Integer.toUnsignedLong(data.getInt(offset));
        if (value >= bound) {
            throw new IOException(label + " identifier is outside 0.." + (bound - 1));
        }
        return (int) value;
    }

    private static int checkedOffset(long value, long fileSize) throws IOException {
        if (value < 0L || value > fileSize || value > Integer.MAX_VALUE) {
            throw new IOException("compact game offset is outside the mapped file");
        }
        return (int) value;
    }

    private static long checkedAdd(long left, long right) throws IOException {
        try {
            return Math.addExact(left, right);
        } catch (ArithmeticException error) {
            throw new IOException("compact game size overflows", error);
        }
    }

    private static long checkedMultiply(long left, long right) throws IOException {
        try {
            return Math.multiplyExact(left, right);
        } catch (ArithmeticException error) {
            throw new IOException("compact game size overflows", error);
        }
    }

    private static int checkedInt(long value, String label) {
        if (value < 0L || value > Integer.MAX_VALUE) {
            throw new IllegalArgumentException(label + " is outside the supported range: " + value);
        }
        return (int) value;
    }

    private static String requireSha256(String value) {
        Objects.requireNonNull(value, "expected SHA-256");
        if (!value.matches("[0-9a-f]{64}")) {
            throw new IllegalArgumentException("expected SHA-256 must be 64 lowercase hex digits");
        }
        return value;
    }

    private static String hex(byte[] digest) {
        StringBuilder result = new StringBuilder(digest.length * 2);
        for (byte value : digest) {
            result.append(String.format("%02x", Byte.valueOf(value)));
        }
        return result.toString();
    }

    private static String copyAndHash(FileChannel source, FileChannel target)
            throws IOException {
        MessageDigest digest;
        try {
            digest = MessageDigest.getInstance("SHA-256");
        } catch (NoSuchAlgorithmException error) {
            throw new IllegalStateException("SHA-256 is unavailable", error);
        }
        ByteBuffer buffer = ByteBuffer.allocateDirect(1024 * 1024);
        source.position(0L);
        target.position(0L);
        while (true) {
            int read = source.read(buffer);
            if (read < 0) break;
            if (read == 0) continue;
            buffer.flip();
            ByteBuffer hashed = buffer.asReadOnlyBuffer();
            digest.update(hashed);
            while (buffer.hasRemaining()) {
                target.write(buffer);
            }
            buffer.clear();
        }
        target.truncate(target.position());
        target.position(0L);
        return hex(digest.digest());
    }

    private static String sha256(ByteBuffer source) {
        MessageDigest digest;
        try {
            digest = MessageDigest.getInstance("SHA-256");
        } catch (NoSuchAlgorithmException error) {
            throw new IllegalStateException("SHA-256 is unavailable", error);
        }
        source.position(0);
        digest.update(source);
        return hex(digest.digest());
    }

    private static void rejectSymbolicComponents(Path absolute) throws IOException {
        Path root = absolute.getRoot();
        Path current = root;
        for (Path component : absolute) {
            current = current == null ? component : current.resolve(component);
            if (Files.isSymbolicLink(current)) {
                throw new IOException("symbolic path component is forbidden: " + current);
            }
        }
    }

    private static void requireSameIdentity(
            BasicFileAttributes before,
            BasicFileAttributes after,
            String context) throws IOException {
        requireUsableFileKey(before, "game bundle");
        requireUsableFileKey(after, "game bundle");
        if (!Objects.equals(before.fileKey(), after.fileKey())
                || before.size() != after.size()
                || !before.lastModifiedTime().equals(after.lastModifiedTime())
                || !before.creationTime().equals(after.creationTime())) {
            throw new IOException("game bundle changed " + context);
        }
    }

    private static void requireUsableFileKey(
            BasicFileAttributes attributes, String label) throws IOException {
        if (attributes.fileKey() == null) {
            throw new IOException(label + " filesystem does not expose a stable file key");
        }
    }

    private static FileChannel openPrivateSnapshot() throws IOException {
        Path directory = Paths.get(System.getProperty("java.io.tmpdir")).toRealPath();
        for (int attempt = 0; attempt < 32; attempt++) {
            Path candidate = directory.resolve(
                    ".fgdu-panel-game-" + UUID.randomUUID().toString() + ".snapshot");
            try {
                /* CREATE_NEW binds the only open; DELETE_ON_CLOSE owns cleanup. */
                return FileChannel.open(
                        candidate,
                        StandardOpenOption.CREATE_NEW,
                        StandardOpenOption.READ,
                        StandardOpenOption.WRITE,
                        StandardOpenOption.DELETE_ON_CLOSE,
                        LinkOption.NOFOLLOW_LINKS);
            } catch (FileAlreadyExistsException collision) {
                // A UUID collision is harmless; retry without touching the existing file.
            }
        }
        throw new IOException("could not allocate an exclusive private game snapshot");
    }
}
