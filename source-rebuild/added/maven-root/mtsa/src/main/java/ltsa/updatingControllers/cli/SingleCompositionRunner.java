package ltsa.updatingControllers.cli;

import java.io.File;
import java.io.FileOutputStream;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.HashMap;
import java.util.Map;

import ltsa.lts.CompactState;
import ltsa.lts.CompositeState;
import ltsa.lts.LTSInputString;
import ltsa.lts.PrintTransitions;
import ltsa.updatingControllers.CompositionEvaluationRunner;
import ltsa.updatingControllers.UpdatingControllerEvaluationRecorder;
import ltsa.updatingControllers.UpdatingControllerEvaluationRecorder.SolverStatus;
import ltsa.updatingControllers.UpdatingControllerEvaluationRecorder.VerificationStatus;
import ltsa.updatingControllers.otf.AtomicHandoffBundleExporter;
import ltsa.updatingControllers.otf.IndependentStrongGameBundleExporter;
import ltsa.updatingControllers.otf.MtsaRevisedOtfDucsAdapter;
import ltsa.updatingControllers.structures.UpdatingControllerCompositeState;

public final class SingleCompositionRunner {

    static final String TRANSITION_OUTPUT_FULL = "full";
    static final String TRANSITION_OUTPUT_SUMMARY = "summary";

    static final int EXIT_SUCCESS = 0;
    static final int EXIT_NO_COMPOSITION = 2;
    static final int EXIT_NO_TRANSITION_OUTPUT = 3;
    static final int EXIT_EXCEPTION = 4;
    static final int EXIT_OUT_OF_MEMORY = 5;
    static final int EXIT_UNREALIZABLE = 6;
    static final int EXIT_INVALID_CERTIFICATE = 7;
    static final int EXIT_INVALID_INPUT = 8;
    static final int EXIT_VERIFICATION_INCONCLUSIVE = 9;
    static final int EXIT_USAGE = 64;

    private SingleCompositionRunner() {
    }

    public static void main(String[] args) {
        int exitCode = runMain(args);
        System.exit(exitCode);
    }

    static int runMain(String[] args) {
        CliFileLTSOutput output = null;
        try {
            Map<String, String> options = parseArgs(args);
            if (options.containsKey("help")) {
                printUsage(System.out);
                return EXIT_SUCCESS;
            }

            File ltsFile = requiredFile(options, "lts");
            String target = required(options, "target");
            File outputFile = requiredFile(options, "output");
            File transitionsFile = requiredFile(options, "transitions");
            String transitionOutput = transitionOutputMode(options);
            File deploymentOutput = optionalFile(options, "deployment-output");
            File gameOutput = optionalFile(options, "game-output");
            if (deploymentOutput != null || gameOutput != null) {
                MtsaRevisedOtfDucsAdapter.clearLastOutcomeForCurrentThread();
            }

            output = new CliFileLTSOutput(outputFile);
            String source = new String(Files.readAllBytes(ltsFile.toPath()), StandardCharsets.UTF_8);
            File parent = ltsFile.getAbsoluteFile().getParentFile();
            String currentDirectory = parent == null
                    ? new File(".").getAbsolutePath()
                    : parent.getAbsolutePath();

            CompositionEvaluationRunner.Request request =
                    new CompositionEvaluationRunner.Request(
                            output,
                            CompositionEvaluationRunner.ltsCompilerStep(
                                    new LTSInputString(source),
                                    target,
                                    currentDirectory))
                            .withOpenFileName(ltsFile.getAbsolutePath());

            CompositionEvaluationRunner.Result result = CompositionEvaluationRunner.run(request);
            MtsaRevisedOtfDucsAdapter.Outcome retainedOutcome = null;
            CompositeState retainedState = result.getCompositeState();
            if (retainedState instanceof UpdatingControllerCompositeState) {
                retainedOutcome = ((UpdatingControllerCompositeState) retainedState)
                        .getRevisedOtfDucsOutcome();
            }
            if (retainedOutcome == null) {
                retainedOutcome = MtsaRevisedOtfDucsAdapter
                        .lastOutcomeForCurrentThread();
            }
            if (gameOutput != null) {
                if (retainedOutcome == null) {
                    throw new IllegalArgumentException(
                            "--game-output requires a completed revised OTF-DUCS decision.");
                }
                IndependentStrongGameBundleExporter.write(
                        retainedOutcome, gameOutput.toPath());
            }
            int recordedOutcome = recordedOutcomeExitCode();
            if (recordedOutcome >= 0) {
                return recordedOutcome;
            }
            Throwable failure = result.getFailure();
            if (failure instanceof OutOfMemoryError) {
                return EXIT_OUT_OF_MEMORY;
            }
            if (failure != null) {
                failure.printStackTrace(System.err);
                return EXIT_EXCEPTION;
            }

            CompositeState current = result.getCompositeState();
            if (current == null || current.composition == null || !result.isSuccessful()) {
                return EXIT_NO_COMPOSITION;
            }

            CompactState selected = selectMachine(current, target);
            if (selected == null) {
                System.err.println("Transition target was not found: " + target);
                return EXIT_NO_TRANSITION_OUTPUT;
            }

            writeTransitions(selected, transitionsFile, transitionOutput);
            if (deploymentOutput != null) {
                MtsaRevisedOtfDucsAdapter.Outcome outcome = retainedOutcome;
                if (current instanceof UpdatingControllerCompositeState) {
                    outcome = ((UpdatingControllerCompositeState) current)
                            .getRevisedOtfDucsOutcome();
                }
                if (outcome == null) {
                    outcome = MtsaRevisedOtfDucsAdapter
                            .lastOutcomeForCurrentThread();
                }
                if (outcome == null) {
                    throw new IllegalArgumentException(
                            "--deployment-output requires a completed revised OTF-DUCS run.");
                }
                AtomicHandoffBundleExporter.write(
                        outcome, deploymentOutput.toPath());
            }
            return EXIT_SUCCESS;
        } catch (OutOfMemoryError e) {
            e.printStackTrace(System.err);
            return EXIT_OUT_OF_MEMORY;
        } catch (IllegalArgumentException e) {
            System.err.println(e.getMessage());
            printUsage(System.err);
            return EXIT_USAGE;
        } catch (Throwable e) {
            e.printStackTrace(System.err);
            return EXIT_EXCEPTION;
        } finally {
            if (output != null) {
                try {
                    output.close();
                } catch (Exception ignored) {
                    // best effort
                }
            }
        }
    }

    static int recordedOutcomeExitCode() {
        SolverStatus solver = UpdatingControllerEvaluationRecorder.getSolverStatus();
        VerificationStatus verification =
                UpdatingControllerEvaluationRecorder.getVerificationStatus();
        if (verification == VerificationStatus.INVALID) {
            return EXIT_INVALID_CERTIFICATE;
        }
        if (solver == SolverStatus.INVALID_INPUT) {
            return EXIT_INVALID_INPUT;
        }
        boolean verificationRequested = Boolean.parseBoolean(
                System.getProperty(
                        "mtsa.revised.otf.independentVerification", "false"));
        if (verificationRequested
                && verification == VerificationStatus.UNVERIFIED
                && (solver == SolverStatus.REALIZABLE
                        || solver == SolverStatus.UNREALIZABLE)) {
            return EXIT_VERIFICATION_INCONCLUSIVE;
        }
        if (solver == SolverStatus.UNREALIZABLE) {
            return EXIT_UNREALIZABLE;
        }
        return -1;
    }

    private static CompactState selectMachine(CompositeState current, String target) {
        if (current.composition != null && namesMatch(current.composition.name, target)) {
            return current.composition;
        }
        if (current.machines != null) {
            for (Object machineObject : current.machines) {
                if (machineObject instanceof CompactState) {
                    CompactState machine = (CompactState) machineObject;
                    if (namesMatch(machine.name, target)) {
                        return machine;
                    }
                }
            }
        }

        return current.composition;
    }

    private static boolean namesMatch(String machineName, String target) {
        if (machineName == null || target == null) {
            return false;
        }
        return machineName.equals(target)
                || machineName.equals("||" + target)
                || machineName.endsWith(":" + target);
    }

    static void writeTransitions(
            CompactState selected,
            File transitionsFile,
            String transitionOutput) throws Exception {
        CliFileLTSOutput transitionsOutput = new CliFileLTSOutput(transitionsFile);
        try {
            transitionsOutput.clearOutput();
            if (TRANSITION_OUTPUT_SUMMARY.equals(transitionOutput)) {
                transitionsOutput.outln("Format:");
                transitionsOutput.outln("\tmtsa-controller-summary-v1");
                transitionsOutput.outln("Process:");
                transitionsOutput.outln("\t" + selected.name);
                transitionsOutput.outln("States:");
                transitionsOutput.outln("\t" + selected.maxStates);
                transitionsOutput.outln("Transitions:");
                transitionsOutput.outln("\t" + selected.ntransitions());
                transitionsOutput.outln("Representation:");
                transitionsOutput.outln(
                        "\tstructural summary; full FSP rendering intentionally omitted");
            } else {
                new PrintTransitions(selected).print(transitionsOutput);
            }
        } finally {
            transitionsOutput.close();
        }
    }

    private static String transitionOutputMode(Map<String, String> options) {
        String mode = options.get("transition-output");
        if (mode == null || mode.trim().isEmpty()) {
            return TRANSITION_OUTPUT_FULL;
        }
        if (TRANSITION_OUTPUT_FULL.equals(mode)
                || TRANSITION_OUTPUT_SUMMARY.equals(mode)) {
            return mode;
        }
        throw new IllegalArgumentException(
                "--transition-output must be full or summary.");
    }

    private static Map<String, String> parseArgs(String[] args) {
        Map<String, String> options = new HashMap<String, String>();
        for (int i = 0; i < args.length; i++) {
            String arg = args[i];
            if ("--help".equals(arg) || "-h".equals(arg)) {
                options.put("help", "true");
            } else if (arg.startsWith("--")) {
                String key = arg.substring(2);
                if (i + 1 >= args.length) {
                    throw new IllegalArgumentException("Missing value for " + arg);
                }
                options.put(key, args[++i]);
            } else {
                throw new IllegalArgumentException("Unknown argument: " + arg);
            }
        }
        return options;
    }

    private static String required(Map<String, String> options, String key) {
        String value = options.get(key);
        if (value == null || value.trim().isEmpty()) {
            throw new IllegalArgumentException("--" + key + " is required.");
        }
        return value;
    }

    private static File requiredFile(Map<String, String> options, String key) {
        return new File(required(options, key));
    }

    private static File optionalFile(Map<String, String> options, String key) {
        String value = options.get(key);
        if (value == null) {
            return null;
        }
        if (value.trim().isEmpty()) {
            throw new IllegalArgumentException("--" + key + " must not be blank.");
        }
        return new File(value);
    }

    private static void printUsage(PrintStream out) {
        out.println("Usage: java -cp mtsa.jar "
                + "ltsa.updatingControllers.cli.SingleCompositionRunner "
                + "--lts file.lts --target Target "
                + "--output output.txt --transitions transitions.txt "
                + "[--transition-output full|summary] "
                + "[--deployment-output handoff-bundle.json] "
                + "[--game-output independent-game-bundle.json]");
    }
}
