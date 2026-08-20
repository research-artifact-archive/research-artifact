package ltsa.updatingControllers.otf;

import org.testng.annotations.Test;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.attribute.BasicFileAttributes;
import java.security.MessageDigest;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Set;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

public class CompactStrongGameTest {

    private static final String SEMANTIC_SHA256 =
            "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";

    @Test
    public void allThreeJavaSolversConsumeTheSameWinningMappedGame()
            throws Exception {
        Path bundle = writeBundle(
                4,
                new byte[] {
                        CompactStrongGame.STATE_SAFE
                                | CompactStrongGame.STATE_STRUCTURALLY_VALID,
                        CompactStrongGame.STATE_SAFE
                                | CompactStrongGame.STATE_STRUCTURALLY_VALID,
                        CompactStrongGame.STATE_SAFE
                                | CompactStrongGame.STATE_STRUCTURALLY_VALID,
                        CompactStrongGame.STATE_SAFE
                                | CompactStrongGame.STATE_GOAL
                                | CompactStrongGame.STATE_STRUCTURALLY_VALID
                },
                new byte[] {
                        CompactStrongGame.ACTION_CONTROLLABLE
                                | CompactStrongGame.ACTION_UPDATE,
                        0
                },
                new int[] {0},
                new long[] {0, 1, 2, 3, 3},
                new int[] {0, 1, 1},
                new long[] {0, 2, 3, 4},
                new int[] {1, 2, 3, 3});
        String digest = sha256(bundle);

        try (CompactStrongGame game = CompactStrongGame.open(
                bundle, digest, SEMANTIC_SHA256)) {
            assertEquals(4, game.stateCount());
            assertEquals(SEMANTIC_SHA256, game.semanticSha256());
            assertEquals(2, game.actionCount());
            assertEquals(3L, game.bucketCount());
            assertEquals(4L, game.outcomeCount());
            assertEquals(Collections.singleton(Integer.valueOf(0)),
                    game.initialStates());
            assertEquals(Arrays.asList(Integer.valueOf(0)),
                    game.candidateActions(Integer.valueOf(0)));
            assertEquals(new LinkedHashSet<Integer>(Arrays.asList(
                            Integer.valueOf(1), Integer.valueOf(2))),
                    game.post(Integer.valueOf(0), Integer.valueOf(0)));

            OtfDucsResult<Integer, Integer, Integer> otf =
                    new OtfDucsSynthesizer<Integer, Integer, Integer>(game)
                            .synthesize();
            OtfDucsResult<Integer, Integer, Integer> generic =
                    new GenericLazyStrongSolver<Integer, Integer, Integer>(game)
                            .synthesize();
            DirectFullStrongSolver<Integer, Integer, Integer> directSolver =
                    new DirectFullStrongSolver<Integer, Integer, Integer>(game);
            OtfDucsResult<Integer, Integer, Integer> direct =
                    directSolver.synthesize();

            assertTrue(otf.isWinning());
            assertTrue(generic.isWinning());
            assertTrue(direct.isWinning());
            assertValid(game, otf);
            assertValid(game, generic);
            assertValid(game, direct);
            assertEquals(Integer.valueOf(2),
                    otf.winningCertificate().ranks().get(Integer.valueOf(0)));
            assertEquals(4L, directSolver.statistics().enumeratedStates());
        }
    }

    @Test
    public void reportsASealedDeadlockAsLosing() throws Exception {
        Path bundle = writeBundle(
                2,
                new byte[] {
                        CompactStrongGame.STATE_SAFE
                                | CompactStrongGame.STATE_STRUCTURALLY_VALID,
                        CompactStrongGame.STATE_SAFE
                                | CompactStrongGame.STATE_STRUCTURALLY_VALID
                },
                new byte[] {
                        CompactStrongGame.ACTION_CONTROLLABLE
                                | CompactStrongGame.ACTION_UPDATE
                },
                new int[] {0},
                new long[] {0, 1, 1},
                new int[] {0},
                new long[] {0, 1},
                new int[] {1});
        try (CompactStrongGame game = CompactStrongGame.open(
                bundle, sha256(bundle), SEMANTIC_SHA256)) {
            OtfDucsResult<Integer, Integer, Integer> result =
                    new OtfDucsSynthesizer<Integer, Integer, Integer>(game)
                            .synthesize();
            assertFalse(result.isWinning());
            assertTrue(result.losingCertificate().losingStates()
                    .contains(Integer.valueOf(0)));
            assertValid(game, result);
        }
    }

    @Test
    public void rejectsDigestTrailingBytesAndNonCanonicalBuckets()
            throws Exception {
        Path valid = writeBundle(
                2,
                new byte[] {
                        CompactStrongGame.STATE_SAFE
                                | CompactStrongGame.STATE_STRUCTURALLY_VALID,
                        CompactStrongGame.STATE_SAFE
                                | CompactStrongGame.STATE_GOAL
                                | CompactStrongGame.STATE_STRUCTURALLY_VALID
                },
                new byte[] {
                        CompactStrongGame.ACTION_CONTROLLABLE
                                | CompactStrongGame.ACTION_UPDATE
                },
                new int[] {0},
                new long[] {0, 1, 1},
                new int[] {0},
                new long[] {0, 1},
                new int[] {1});
        expectOpenFailure(valid, repeat('0', 64), "SHA-256");

        byte[] trailing = Files.readAllBytes(valid);
        Path withTrailing = createTempFile("compact-game-trailing", ".fggb");
        Files.write(withTrailing, Arrays.copyOf(trailing, trailing.length + 1));
        expectOpenFailure(withTrailing, sha256(withTrailing), "size/reserved");

        Path duplicateTargets = writeBundleUnchecked(
                2,
                new byte[] {
                        CompactStrongGame.STATE_SAFE
                                | CompactStrongGame.STATE_STRUCTURALLY_VALID,
                        CompactStrongGame.STATE_SAFE
                                | CompactStrongGame.STATE_GOAL
                                | CompactStrongGame.STATE_STRUCTURALLY_VALID
                },
                new byte[] {
                        CompactStrongGame.ACTION_CONTROLLABLE
                                | CompactStrongGame.ACTION_UPDATE
                },
                new int[] {0},
                new long[] {0, 1, 1},
                new int[] {0},
                new long[] {0, 2},
                new int[] {1, 1});
        expectOpenFailure(duplicateTargets, sha256(duplicateTargets),
                "strictly increasing");
    }

    @Test
    public void rejectsUpdateActionsThatAreNotControllable() throws Exception {
        Path invalid = writeBundleUnchecked(
                1,
                new byte[] {
                        CompactStrongGame.STATE_SAFE
                                | CompactStrongGame.STATE_GOAL
                                | CompactStrongGame.STATE_STRUCTURALLY_VALID
                },
                new byte[] {CompactStrongGame.ACTION_UPDATE},
                new int[] {0},
                new long[] {0, 0},
                new int[] {},
                new long[] {0},
                new int[] {});
        expectOpenFailure(invalid, sha256(invalid), "action flags");
    }

    @Test
    public void rejectsBucketsFromTerminalGoalOrUnsafeStates() throws Exception {
        Path goalOutgoing = writeBundleUnchecked(
                1,
                new byte[] {
                        CompactStrongGame.STATE_SAFE
                                | CompactStrongGame.STATE_GOAL
                                | CompactStrongGame.STATE_STRUCTURALLY_VALID
                },
                new byte[] {CompactStrongGame.ACTION_CONTROLLABLE},
                new int[] {0},
                new long[] {0, 1},
                new int[] {0},
                new long[] {0, 1},
                new int[] {0});
        expectOpenFailure(goalOutgoing, sha256(goalOutgoing), "must be terminal");

        Path unsafeOutgoing = writeBundleUnchecked(
                1,
                new byte[] {CompactStrongGame.STATE_STRUCTURALLY_VALID},
                new byte[] {CompactStrongGame.ACTION_CONTROLLABLE},
                new int[] {0},
                new long[] {0, 1},
                new int[] {0},
                new long[] {0, 1},
                new int[] {0});
        expectOpenFailure(unsafeOutgoing, sha256(unsafeOutgoing), "must be terminal");
    }

    @Test
    public void serializesOnlyCheckedCertificatesAndBindsTheGameDigest()
            throws Exception {
        Path bundle = writeBundle(
                2,
                new byte[] {
                        CompactStrongGame.STATE_SAFE
                                | CompactStrongGame.STATE_STRUCTURALLY_VALID,
                        CompactStrongGame.STATE_SAFE
                                | CompactStrongGame.STATE_GOAL
                                | CompactStrongGame.STATE_STRUCTURALLY_VALID
                },
                new byte[] {
                        CompactStrongGame.ACTION_CONTROLLABLE
                                | CompactStrongGame.ACTION_UPDATE
                },
                new int[] {0},
                new long[] {0, 1, 1},
                new int[] {0},
                new long[] {0, 1},
                new int[] {1});
        String gameDigest = sha256(bundle);
        try (CompactStrongGame game = CompactStrongGame.open(
                bundle, gameDigest, SEMANTIC_SHA256)) {
            OtfDucsResult<Integer, Integer, Integer> valid =
                    new OtfDucsSynthesizer<Integer, Integer, Integer>(game)
                            .synthesize();
            Path certificate = createTempFile("compact-certificate", ".fgcert");
            Files.delete(certificate);
            CompactStrongCertificate.WriteResult written =
                    CompactStrongCertificate.writeChecked(certificate, game, valid);
            assertEquals(CompactStrongCertificate.DECISION_WINNING,
                    written.decision());
            assertEquals(1, written.rootCount());
            assertEquals(2, written.rankCount());
            assertEquals(1, written.strategyBucketCount());
            assertEquals(1, written.strategyOutcomeCount());
            assertEquals(1, written.goalCount());
            assertEquals(0, written.losingCount());
            assertEquals(sha256(certificate), written.sha256());

            ByteBuffer header = ByteBuffer.wrap(Files.readAllBytes(certificate))
                    .order(ByteOrder.LITTLE_ENDIAN);
            byte[] magic = new byte[8];
            header.get(magic);
            assertTrue(Arrays.equals(CompactStrongCertificate.MAGIC, magic));
            assertEquals(CompactStrongCertificate.VERSION, header.getInt());
            assertEquals(CompactStrongCertificate.HEADER_BYTES, header.getInt());
            assertEquals(written.sizeBytes(), header.getLong());
            assertEquals(CompactStrongCertificate.DECISION_WINNING,
                    header.getInt());
            header.position(80);
            byte[] embeddedGameDigest = new byte[32];
            header.get(embeddedGameDigest);
            assertEquals(gameDigest, hex(embeddedGameDigest));

            byte[] certificateBefore = Files.readAllBytes(certificate);
            Object certificateFileKey = Files.readAttributes(
                    certificate, BasicFileAttributes.class,
                    LinkOption.NOFOLLOW_LINKS).fileKey();
            try {
                CompactStrongCertificate.writeChecked(certificate, game, valid);
                fail("certificate overwrite must be rejected");
            } catch (IOException expected) {
                assertTrue(expected.getMessage().contains("already exists"));
            }
            assertTrue(Arrays.equals(certificateBefore, Files.readAllBytes(certificate)));
            assertEquals(certificateFileKey, Files.readAttributes(
                    certificate, BasicFileAttributes.class,
                    LinkOption.NOFOLLOW_LINKS).fileKey());

            Path sentinel = createTempFile("certificate-sentinel", ".txt");
            Files.write(sentinel, new byte[] {9, 8, 7, 6});
            Object sentinelFileKey = Files.readAttributes(
                    sentinel, BasicFileAttributes.class,
                    LinkOption.NOFOLLOW_LINKS).fileKey();
            Path partial = createTempFile("partial-certificate", ".fgcert");
            Files.delete(partial);
            try {
                CompactStrongCertificate.writeChecked(
                        partial, game, valid,
                        new CompactStrongCertificate.WriteFaultInjector() {
                            @Override
                            public void afterHeader(Path destination) throws IOException {
                                throw new IOException("injected after header");
                            }
                        });
                fail("injected certificate write must fail");
            } catch (IOException expected) {
                assertTrue(expected.getMessage().contains("injected after header"));
            }
            assertTrue(Files.isRegularFile(partial));
            assertEquals(CompactStrongCertificate.HEADER_BYTES, Files.size(partial));
            assertTrue(Arrays.equals(
                    new byte[] {9, 8, 7, 6}, Files.readAllBytes(sentinel)));
            assertEquals(sentinelFileKey, Files.readAttributes(
                    sentinel, BasicFileAttributes.class,
                    LinkOption.NOFOLLOW_LINKS).fileKey());

            Map<Integer, Integer> wrongRanks = new LinkedHashMap<Integer, Integer>();
            wrongRanks.put(Integer.valueOf(0), Integer.valueOf(1));
            Map<Integer, Map<Integer, Set<Integer>>> strategy =
                    new LinkedHashMap<Integer, Map<Integer, Set<Integer>>>();
            strategy.put(Integer.valueOf(0), Collections.singletonMap(
                    Integer.valueOf(0), Collections.singleton(Integer.valueOf(1))));
            OtfDucsResult.WinningCertificate<Integer, Integer, Integer> invalidCertificate =
                    new OtfDucsResult.WinningCertificate<Integer, Integer, Integer>(
                            Collections.singleton(Integer.valueOf(0)),
                            wrongRanks,
                            strategy,
                            Collections.<Integer, Integer>emptyMap());
            OtfDucsResult<Integer, Integer, Integer> invalid = OtfDucsResult.winning(
                    invalidCertificate, valid.statistics());
            Path rejected = createTempFile("rejected-certificate", ".fgcert");
            Files.delete(rejected);
            try {
                CompactStrongCertificate.writeChecked(rejected, game, invalid);
                fail("invalid certificate must be rejected");
            } catch (IOException expected) {
                assertTrue(expected.getMessage().contains("invalid certificate"));
                assertFalse(Files.exists(rejected));
            }
        }
    }

    private static void assertValid(
            CompactStrongGame game,
            OtfDucsResult<Integer, Integer, Integer> result) {
        OtfDucsCertificateChecker.VerificationReport report =
                new OtfDucsCertificateChecker<Integer, Integer, Integer>(game)
                        .verify(result);
        assertTrue(report.violations().toString(), report.isValid());
    }

    private static void expectOpenFailure(
            Path path, String digest, String expectedMessage) throws Exception {
        try {
            CompactStrongGame.open(path, digest, SEMANTIC_SHA256).close();
            fail("expected bundle rejection");
        } catch (IOException error) {
            assertTrue(error.toString(), error.getMessage().contains(expectedMessage));
        }
    }

    private static Path writeBundle(
            int states,
            byte[] stateFlags,
            byte[] actionFlags,
            int[] roots,
            long[] stateBucketOffsets,
            int[] bucketActions,
            long[] targetOffsets,
            int[] targets) throws Exception {
        return writeBundleUnchecked(states, stateFlags, actionFlags, roots,
                stateBucketOffsets, bucketActions, targetOffsets, targets);
    }

    private static Path writeBundleUnchecked(
            int states,
            byte[] stateFlags,
            byte[] actionFlags,
            int[] roots,
            long[] stateBucketOffsets,
            int[] bucketActions,
            long[] targetOffsets,
            int[] targets) throws Exception {
        long size = CompactStrongGame.HEADER_BYTES
                + actionFlags.length
                + stateFlags.length
                + roots.length * 4L
                + stateBucketOffsets.length * 8L
                + bucketActions.length * 4L
                + targetOffsets.length * 8L
                + targets.length * 4L;
        ByteBuffer data = ByteBuffer.allocate((int) size)
                .order(ByteOrder.LITTLE_ENDIAN);
        data.put(CompactStrongGame.MAGIC);
        data.putInt(CompactStrongGame.VERSION);
        data.putInt(CompactStrongGame.HEADER_BYTES);
        data.putLong(size);
        data.putInt(states);
        data.putInt(actionFlags.length);
        data.putInt(roots.length);
        data.putInt(0);
        data.putLong(bucketActions.length);
        data.putLong(targets.length);
        data.putLong(0L);
        data.put(parseHex(SEMANTIC_SHA256));
        data.put(actionFlags);
        data.put(stateFlags);
        for (int value : roots) data.putInt(value);
        for (long value : stateBucketOffsets) data.putLong(value);
        for (int value : bucketActions) data.putInt(value);
        for (long value : targetOffsets) data.putLong(value);
        for (int value : targets) data.putInt(value);
        Path path = createTempFile("compact-strong-game", ".fggb");
        Files.write(path, data.array());
        return path;
    }

    private static Path createTempFile(String prefix, String suffix)
            throws Exception {
        Path realTemporaryDirectory = Paths.get(
                System.getProperty("java.io.tmpdir")).toRealPath();
        return Files.createTempFile(realTemporaryDirectory, prefix, suffix);
    }

    private static String sha256(Path path) throws Exception {
        byte[] digest = MessageDigest.getInstance("SHA-256")
                .digest(Files.readAllBytes(path));
        return hex(digest);
    }

    private static String hex(byte[] digest) {
        StringBuilder result = new StringBuilder();
        for (byte value : digest) result.append(String.format("%02x", value));
        return result.toString();
    }

    private static byte[] parseHex(String value) {
        byte[] result = new byte[value.length() / 2];
        for (int index = 0; index < result.length; index++) {
            result[index] = (byte) Integer.parseInt(
                    value.substring(index * 2, index * 2 + 2), 16);
        }
        return result;
    }

    private static String repeat(char value, int count) {
        char[] result = new char[count];
        Arrays.fill(result, value);
        return new String(result);
    }
}
