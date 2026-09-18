package ltsa.updatingControllers.cli;

import ltsa.updatingControllers.otf.CompactStrongCertificate;
import ltsa.updatingControllers.otf.CompactStrongGame;
import ltsa.updatingControllers.otf.DirectFullStrongSolver;
import ltsa.updatingControllers.otf.GenericLazyStrongSolver;
import ltsa.updatingControllers.otf.OtfDucsCertificateChecker;
import ltsa.updatingControllers.otf.OtfDucsResult;
import ltsa.updatingControllers.otf.OtfDucsSynthesizer;

import java.io.IOException;
import java.nio.file.InvalidPathException;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Runs exactly one registered Java decision method over one already
 * materialised canonical game.  This command never parses FSP, synthesises an
 * endpoint controller, or reconstructs a source projection.
 */
public final class PanelProblemRunner {

    public static final int EXIT_REALIZABLE = 0;
    public static final int EXIT_INVALID_INVOCATION = 2;
    public static final int EXIT_UNREALIZABLE = 6;
    public static final int EXIT_INTERNAL_ERROR = 70;
    public static final int EXIT_RESOURCE_ERROR = 71;

    private PanelProblemRunner() {
        // Utility class.
    }

    public static void main(String[] arguments) {
        System.exit(dispatch(arguments));
    }

    static int dispatch(String[] arguments) {
        int exit;
        try {
            exit = run(arguments);
        } catch (InvalidInvocationException error) {
            System.err.println("PANEL_RUNNER_INVALID_INVOCATION="
                    + safeMessage(error));
            exit = EXIT_INVALID_INVOCATION;
        } catch (OutOfMemoryError error) {
            System.err.println("PANEL_RUNNER_RESOURCE_ERROR="
                    + error.getClass().getName());
            exit = EXIT_RESOURCE_ERROR;
        } catch (Throwable error) {
            System.err.println("PANEL_RUNNER_INTERNAL_ERROR="
                    + error.getClass().getName() + ":" + safeMessage(error));
            error.printStackTrace(System.err);
            exit = EXIT_INTERNAL_ERROR;
        }
        return exit;
    }

    static int run(String[] arguments) throws IOException {
        Map<String, String> options = parse(arguments);
        String method = require(options, "--method");
        if (!method.equals("fg_ducs_otf")
                && !method.equals("generic_lazy")
                && !method.equals("direct_full")) {
            throw new InvalidInvocationException("unknown registered method: " + method);
        }
        Path bundle = requirePath(options, "--game");
        String bundleSha256 = requireSha256(
                options, "--expected-game-sha256");
        String semanticSha256 = requireSha256(
                options, "--expected-semantic-sha256");
        Path certificate = requirePath(options, "--certificate");
        if (options.size() != 5) {
            throw new InvalidInvocationException("unexpected command-line option");
        }

        /* Freeze the public OTF constructor's only semantic tuning inputs. */
        System.setProperty("mtsa.otf.guidedStateLimit", "0");
        System.setProperty("mtsa.otf.guidedQueryLimit", "0");
        System.setProperty("mtsa.otf.lazyControllableBuckets", "true");

        long started = System.nanoTime();
        Map<String, Object> record = new LinkedHashMap<String, Object>();
        int decisionExit;
        try (CompactStrongGame game = CompactStrongGame.open(
                bundle, bundleSha256, semanticSha256)) {
            OtfDucsResult<Integer, Integer, Integer> result;
            DirectFullStrongSolver.Statistics directStatistics = null;
            long solveStarted = System.nanoTime();
            if (method.equals("direct_full")) {
                DirectFullStrongSolver<Integer, Integer, Integer> solver =
                        new DirectFullStrongSolver<Integer, Integer, Integer>(game);
                result = solver.synthesize();
                directStatistics = solver.statistics();
            } else if (method.equals("generic_lazy")) {
                result = new GenericLazyStrongSolver<Integer, Integer, Integer>(game)
                        .synthesize();
            } else {
                result = new OtfDucsSynthesizer<Integer, Integer, Integer>(game)
                        .synthesize();
            }
            long solveNanos = System.nanoTime() - solveStarted;
            OtfDucsCertificateChecker.VerificationReport verification =
                    new OtfDucsCertificateChecker<Integer, Integer, Integer>(game)
                            .verify(result);
            if (!verification.isValid()) {
                throw new IOException("registered Java certificate failed verification: "
                        + verification.violations());
            }
            game.verifyUnchanged();
            CompactStrongCertificate.WriteResult written =
                    CompactStrongCertificate.writeChecked(
                            certificate, game, result);
            game.verifyUnchanged();

            record.put("schema_version", "m9-panel-java-cell-v1");
            record.put("method", method);
            record.put("decision", result.isWinning() ? "REALIZABLE" : "UNREALIZABLE");
            record.put("game_sha256", game.sha256());
            record.put("semantic_sha256", game.semanticSha256());
            record.put("certificate_sha256", written.sha256());
            record.put("certificate_size_bytes", Long.valueOf(written.sizeBytes()));
            record.put("states", Integer.valueOf(game.stateCount()));
            record.put("actions", Integer.valueOf(game.actionCount()));
            record.put("roots", Integer.valueOf(game.rootCount()));
            record.put("enabled_buckets", Long.valueOf(game.bucketCount()));
            record.put("outcomes", Long.valueOf(game.outcomeCount()));
            record.put("certificate_ranks", Integer.valueOf(written.rankCount()));
            record.put("certificate_strategy_buckets",
                    Integer.valueOf(written.strategyBucketCount()));
            record.put("certificate_strategy_outcomes",
                    Integer.valueOf(written.strategyOutcomeCount()));
            record.put("certificate_goals", Integer.valueOf(written.goalCount()));
            record.put("certificate_losing_states", Integer.valueOf(written.losingCount()));
            record.put("solve_nanos", Long.valueOf(solveNanos));
            recordCommonStatistics(record, result.statistics());
            if (directStatistics != null) {
                record.put("direct_enumerated_states",
                        Long.valueOf(directStatistics.enumeratedStates()));
                record.put("direct_enabled_buckets",
                        Long.valueOf(directStatistics.enabledActionBuckets()));
                record.put("direct_fixed_point_iterations",
                        Long.valueOf(directStatistics.fixedPointIterations()));
            }
            decisionExit = result.isWinning() ? EXIT_REALIZABLE : EXIT_UNREALIZABLE;
        }
        record.put("total_nanos", Long.valueOf(System.nanoTime() - started));
        emitComplete(record);
        return decisionExit;
    }

    private static void recordCommonStatistics(
            Map<String, Object> record,
            OtfDucsResult.Statistics statistics) {
        record.put("solver_discovered_states", Long.valueOf(statistics.discoveredStates()));
        record.put("solver_expanded_states", Long.valueOf(statistics.expandedStates()));
        record.put("solver_queried_pairs", Long.valueOf(statistics.queriedStateActionPairs()));
        record.put("solver_materialized_outcomes",
                Long.valueOf(statistics.materializedTransitions()));
        record.put("solver_fixed_point_inspections",
                Long.valueOf(statistics.fixedPointStateInspections()));
        record.put("solver_fixed_point_computations",
                Long.valueOf(statistics.fixedPointComputations()));
        record.put("solver_early_success", Boolean.valueOf(statistics.earlySuccess()));
        record.put("solver_lazy_controllable_buckets",
                Boolean.valueOf(statistics.lazyControllableBuckets()));
    }

    private static Map<String, String> parse(String[] arguments) {
        if (arguments == null || arguments.length % 2 != 0) {
            throw new InvalidInvocationException(
                    "usage: --game PATH --expected-game-sha256 HEX "
                            + "--expected-semantic-sha256 HEX "
                            + "--method METHOD --certificate PATH");
        }
        Map<String, String> result = new LinkedHashMap<String, String>();
        for (int index = 0; index < arguments.length; index += 2) {
            String key = arguments[index];
            String value = arguments[index + 1];
            if (!key.startsWith("--") || value == null || value.isEmpty()
                    || result.put(key, value) != null) {
                throw new InvalidInvocationException("invalid or duplicate option: " + key);
            }
        }
        return result;
    }

    private static String require(Map<String, String> options, String key) {
        String value = options.get(key);
        if (value == null) {
            throw new InvalidInvocationException("missing required option: " + key);
        }
        return value;
    }

    private static String requireSha256(Map<String, String> options, String key) {
        String value = require(options, key);
        if (!value.matches("[0-9a-f]{64}")) {
            throw new InvalidInvocationException(key + " is not a lowercase SHA-256");
        }
        return value;
    }

    private static Path requirePath(Map<String, String> options, String key) {
        String value = require(options, key);
        try {
            return Paths.get(value);
        } catch (InvalidPathException error) {
            throw new InvalidInvocationException(key + " is not a valid path");
        }
    }

    private static void emitComplete(Map<String, Object> record) throws IOException {
        StringBuilder text = new StringBuilder();
        for (Map.Entry<String, Object> entry : record.entrySet()) {
            text.append(entry.getKey()).append('=').append(String.valueOf(entry.getValue()))
                    .append('\n');
        }
        text.append("terminal_record=COMPLETE\n");
        System.out.print(text.toString());
        System.out.flush();
        if (System.out.checkError()) {
            throw new IOException("registered terminal record could not be written");
        }
    }

    private static String safeMessage(Throwable error) {
        String message = error.getMessage();
        if (message == null) return "";
        return message.replace('\n', ' ').replace('\r', ' ');
    }

    private static final class InvalidInvocationException
            extends IllegalArgumentException {
        private InvalidInvocationException(String message) {
            super(message);
        }
    }
}
