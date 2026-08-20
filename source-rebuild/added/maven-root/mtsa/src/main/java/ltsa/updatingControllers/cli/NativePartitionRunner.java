package ltsa.updatingControllers.cli;

import ltsa.lts.EmptyLTSOuput;
import ltsa.lts.NativeUpdatingContractLoader;
import ltsa.updatingControllers.otf.NativeTierABundleExporter;
import ltsa.updatingControllers.otf.NativeTierAFactorizer;
import ltsa.updatingControllers.structures.UpdatingControllerCompositeState;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.util.LinkedHashMap;
import java.util.Map;

/** Runs source-native Tier-A factorization without invoking a global game. */
public final class NativePartitionRunner {

    private NativePartitionRunner() {
        // Utility class.
    }

    public static void main(String[] args) {
        System.exit(runMain(args));
    }

    static int runMain(String[] args) {
        try {
            Map<String, String> options = parse(args);
            Path lts = requiredPath(options, "lts");
            Path output = requiredPath(options, "output");
            String definition = required(options, "definition");
            if (options.size() != 3) {
                throw new IllegalArgumentException(
                        "unexpected command-line option");
            }
            byte[] bytes = Files.readAllBytes(lts);
            File parent = lts.toAbsolutePath().normalize().toFile()
                    .getParentFile();
            String currentDirectory = parent == null
                    ? new File(".").getCanonicalPath()
                    : parent.getCanonicalPath();
            UpdatingControllerCompositeState source =
                    NativeUpdatingContractLoader.load(
                            new String(bytes, StandardCharsets.UTF_8),
                            definition,
                            currentDirectory,
                            new EmptyLTSOuput());
            long started = System.nanoTime();
            NativeTierAFactorizer.Result result =
                    NativeTierAFactorizer.factor(source);
            NativeTierABundleExporter.write(
                    result,
                    lts.getFileName().toString(),
                    sha256(bytes),
                    definition,
                    output);
            System.out.println("source_sha256=" + sha256(bytes));
            System.out.println("definition=" + definition);
            System.out.println("factor_status=" + result.factorStatus());
            System.out.println("solve_status=" + result.solveStatus());
            System.out.println("block_count=" + result.blocks().size());
            System.out.println("terminal_product_verified="
                    + result.terminalProductVerified());
            System.out.println("elapsed_nanos="
                    + (System.nanoTime() - started));
            System.out.println("terminal_record=COMPLETE");
            return 0;
        } catch (IllegalArgumentException error) {
            System.err.println("NATIVE_FACTOR_INVALID=" + error.getMessage());
            return 2;
        } catch (Throwable error) {
            System.err.println("NATIVE_FACTOR_ERROR="
                    + error.getClass().getName() + ":" + error.getMessage());
            error.printStackTrace(System.err);
            return 70;
        }
    }

    private static Map<String, String> parse(String[] args) {
        if (args == null || args.length % 2 != 0) {
            throw new IllegalArgumentException(
                    "usage: --lts PATH --definition NAME --output PATH");
        }
        Map<String, String> result = new LinkedHashMap<String, String>();
        for (int index = 0; index < args.length; index += 2) {
            String key = args[index];
            if (!key.startsWith("--") || args[index + 1].isEmpty()
                    || result.put(key.substring(2), args[index + 1]) != null) {
                throw new IllegalArgumentException(
                        "invalid or duplicate option: " + key);
            }
        }
        return result;
    }

    private static String required(
            Map<String, String> options, String key) {
        String value = options.get(key);
        if (value == null || value.trim().isEmpty()) {
            throw new IllegalArgumentException(
                    "missing required option --" + key);
        }
        return value;
    }

    private static Path requiredPath(
            Map<String, String> options, String key) {
        return Paths.get(required(options, key)).toAbsolutePath().normalize();
    }

    private static String sha256(byte[] bytes) throws Exception {
        byte[] digest = MessageDigest.getInstance("SHA-256").digest(bytes);
        StringBuilder result = new StringBuilder();
        for (byte value : digest) {
            result.append(String.format("%02x", value & 0xff));
        }
        return result.toString();
    }
}
