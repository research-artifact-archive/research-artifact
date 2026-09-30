package ltsa.updatingControllers.cli;

import ltsa.updatingControllers.otf.CompactStrongGame;

import org.testng.annotations.Test;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.security.MessageDigest;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

public class PanelProblemRunnerTest {

    private static final String SEMANTIC_SHA256 =
            "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";

    @Test
    public void dispatchesAllThreeRegisteredMethodsOverOneDigest()
            throws Exception {
        Path game = writeTwoStateGame(true);
        String digest = sha256(game);
        for (String method : new String[] {
                "fg_ducs_otf", "generic_lazy", "direct_full"}) {
            Path certificate = freshPath("runner-" + method, ".fgcert");
            RunCapture capture = captureDispatch(new String[] {
                    "--game", game.toString(),
                    "--expected-game-sha256", digest,
                    "--expected-semantic-sha256", SEMANTIC_SHA256,
                    "--method", method,
                    "--certificate", certificate.toString()
            });
            assertEquals(method, PanelProblemRunner.EXIT_REALIZABLE, capture.exit);
            assertTrue(Files.isRegularFile(certificate));
            assertTrue(Files.size(certificate) >= 128L);
            assertTrue(capture.stdout.endsWith("terminal_record=COMPLETE\n"));
            assertEquals(1, count(capture.stdout, "terminal_record=COMPLETE\n"));
            assertTrue(capture.stdout.contains("certificate_sha256=" + sha256(certificate)));
        }
    }

    @Test
    public void preservesAnUnrealizableDecisionAsExitSix() throws Exception {
        Path game = writeTwoStateGame(false);
        Path certificate = freshPath("runner-losing", ".fgcert");
        RunCapture capture = captureDispatch(new String[] {
                "--game", game.toString(),
                "--expected-game-sha256", sha256(game),
                "--expected-semantic-sha256", SEMANTIC_SHA256,
                "--method", "fg_ducs_otf",
                "--certificate", certificate.toString()
        });
        assertEquals(PanelProblemRunner.EXIT_UNREALIZABLE, capture.exit);
        assertTrue(Files.isRegularFile(certificate));
        assertTrue(capture.stdout.endsWith("terminal_record=COMPLETE\n"));
        assertTrue(capture.stdout.contains("decision=UNREALIZABLE\n"));
    }

    @Test
    public void rejectsUnknownOrDuplicateMethodSelection() throws Exception {
        Path game = writeTwoStateGame(true);
        Path certificate = freshPath("runner-invalid", ".fgcert");
        try {
            PanelProblemRunner.run(new String[] {
                    "--game", game.toString(),
                    "--expected-game-sha256", sha256(game),
                    "--expected-semantic-sha256", SEMANTIC_SHA256,
                    "--method", "not-registered",
                    "--certificate", certificate.toString()
            });
            fail("unknown method must be rejected");
        } catch (IllegalArgumentException expected) {
            assertTrue(expected.getMessage().contains("unknown registered method"));
        }
        assertTrue(!Files.exists(certificate));
        assertEquals(PanelProblemRunner.EXIT_INVALID_INVOCATION,
                captureDispatch(new String[0]).exit);
        assertEquals(PanelProblemRunner.EXIT_INVALID_INVOCATION,
                captureDispatch(new String[] {
                        "--game", "bad\u0000path",
                        "--expected-game-sha256", repeat('0', 64),
                        "--expected-semantic-sha256", SEMANTIC_SHA256,
                        "--method", "fg_ducs_otf",
                        "--certificate", certificate.toString()
                }).exit);
    }

    @Test
    public void failedExclusiveCertificateWriteNeverEmitsCompleteOrDeletesExistingBytes()
            throws Exception {
        Path game = writeTwoStateGame(true);
        Path certificate = freshPath("runner-existing", ".fgcert");
        Files.write(certificate, new byte[] {4, 3, 2, 1});
        Object fileKey = Files.readAttributes(
                certificate, java.nio.file.attribute.BasicFileAttributes.class,
                java.nio.file.LinkOption.NOFOLLOW_LINKS).fileKey();
        RunCapture capture = captureDispatch(new String[] {
                "--game", game.toString(),
                "--expected-game-sha256", sha256(game),
                "--expected-semantic-sha256", SEMANTIC_SHA256,
                "--method", "fg_ducs_otf",
                "--certificate", certificate.toString()
        });
        assertEquals(PanelProblemRunner.EXIT_INTERNAL_ERROR, capture.exit);
        assertFalse(capture.stdout.contains("terminal_record=COMPLETE"));
        assertTrue(capture.stderr.contains("PANEL_RUNNER_INTERNAL_ERROR="));
        assertTrue(java.util.Arrays.equals(
                new byte[] {4, 3, 2, 1}, Files.readAllBytes(certificate)));
        assertEquals(fileKey, Files.readAttributes(
                certificate, java.nio.file.attribute.BasicFileAttributes.class,
                java.nio.file.LinkOption.NOFOLLOW_LINKS).fileKey());
    }

    private static synchronized RunCapture captureDispatch(String[] arguments)
            throws Exception {
        PrintStream originalOut = System.out;
        PrintStream originalErr = System.err;
        ByteArrayOutputStream stdout = new ByteArrayOutputStream();
        ByteArrayOutputStream stderr = new ByteArrayOutputStream();
        try {
            System.setOut(new PrintStream(stdout, true, "UTF-8"));
            System.setErr(new PrintStream(stderr, true, "UTF-8"));
            int exit = PanelProblemRunner.dispatch(arguments);
            return new RunCapture(
                    exit,
                    new String(stdout.toByteArray(), StandardCharsets.UTF_8),
                    new String(stderr.toByteArray(), StandardCharsets.UTF_8));
        } finally {
            System.setOut(originalOut);
            System.setErr(originalErr);
        }
    }

    private static int count(String value, String needle) {
        int result = 0;
        int offset = 0;
        while ((offset = value.indexOf(needle, offset)) >= 0) {
            result++;
            offset += needle.length();
        }
        return result;
    }

    private static final class RunCapture {
        private final int exit;
        private final String stdout;
        private final String stderr;

        private RunCapture(int exit, String stdout, String stderr) {
            this.exit = exit;
            this.stdout = stdout;
            this.stderr = stderr;
        }
    }

    private static Path writeTwoStateGame(boolean winning) throws Exception {
        byte[] actionFlags = new byte[] {
                (byte) (CompactStrongGame.ACTION_CONTROLLABLE
                        | CompactStrongGame.ACTION_UPDATE)
        };
        byte[] stateFlags = winning
                ? new byte[] {
                        (byte) (CompactStrongGame.STATE_SAFE
                                | CompactStrongGame.STATE_STRUCTURALLY_VALID),
                        (byte) (CompactStrongGame.STATE_SAFE
                                | CompactStrongGame.STATE_GOAL
                                | CompactStrongGame.STATE_STRUCTURALLY_VALID)
                }
                : new byte[] {
                        (byte) (CompactStrongGame.STATE_SAFE
                                | CompactStrongGame.STATE_STRUCTURALLY_VALID),
                        (byte) (CompactStrongGame.STATE_SAFE
                                | CompactStrongGame.STATE_STRUCTURALLY_VALID)
                };
        long size = CompactStrongGame.HEADER_BYTES
                + actionFlags.length + stateFlags.length
                + 4L + 3L * 8L + 4L + 2L * 8L + 4L;
        ByteBuffer data = ByteBuffer.allocate((int) size)
                .order(ByteOrder.LITTLE_ENDIAN);
        data.put(CompactStrongGame.MAGIC);
        data.putInt(CompactStrongGame.VERSION);
        data.putInt(CompactStrongGame.HEADER_BYTES);
        data.putLong(size);
        data.putInt(2);
        data.putInt(1);
        data.putInt(1);
        data.putInt(0);
        data.putLong(1L);
        data.putLong(1L);
        data.putLong(0L);
        data.put(parseHex(SEMANTIC_SHA256));
        data.put(actionFlags);
        data.put(stateFlags);
        data.putInt(0);
        data.putLong(0L).putLong(1L).putLong(1L);
        data.putInt(0);
        data.putLong(0L).putLong(1L);
        data.putInt(1);
        Path result = freshPath("panel-runner-game", ".fggb");
        Files.write(result, data.array());
        return result;
    }

    private static Path freshPath(String prefix, String suffix) throws Exception {
        Path realTemporaryDirectory = Paths.get(
                System.getProperty("java.io.tmpdir")).toRealPath();
        Path result = Files.createTempFile(realTemporaryDirectory, prefix, suffix);
        Files.delete(result);
        return result;
    }

    private static String sha256(Path path) throws Exception {
        byte[] digest = MessageDigest.getInstance("SHA-256")
                .digest(Files.readAllBytes(path));
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
        java.util.Arrays.fill(result, value);
        return new String(result);
    }
}
