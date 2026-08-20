package ltsa.updatingControllers.otf;

import ltsa.dispatcher.TransitionSystemDispatcher;
import ltsa.lts.CompositeState;
import ltsa.lts.FileInput;
import ltsa.lts.LTSCompiler;
import ltsa.lts.LTSCompositionException;
import ltsa.lts.LTSOutput;
import ltsa.updatingControllers.structures.UpdatingControllerCompositeState;
import org.testng.SkipException;
import org.testng.annotations.Test;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.stream.Collectors;
import java.util.stream.Stream;

import static org.testng.Assert.assertEquals;
import static org.testng.Assert.assertFalse;
import static org.testng.Assert.assertNotNull;
import static org.testng.Assert.assertTrue;
import static org.testng.Assert.fail;

/**
 * Production-path smoke test for every primary Experiment/Models case.
 *
 * <p>This is deliberately one TestNG method: {@link LTSCompiler} and several
 * LTSA registries are process-global and must not compile these models in
 * parallel. Enable explicitly with
 * {@code -Dmtsa.revised.otf.integration=true} because the nine controller
 * synthesis runs are unsuitable for the ordinary unit-test cycle.</p>
 */
public class ExperimentModelsRevisedOtfIntegrationTest {

    private static final String ENABLE_PROPERTY = "mtsa.revised.otf.integration";
    private static final String MODELS_DIRECTORY_PROPERTY = "mtsa.experiment.models.dir";
    private static final String MODEL_PROPERTY = "mtsa.revised.otf.model";
    private static final String TARGET_PROPERTY = "mtsa.revised.otf.target";
    private static final String EVALUATION_PROPERTY = "mtsa.evaluation.enabled";
    private static final String PRINT_OUTPUT_PROPERTY =
            "mtsa.revised.otf.integration.printOutput";
    private static final String PRIMARY_TARGET = "UPDATE_CONTROLLER_OTF_FG";
    private static final List<String> REVISED_TARGETS = Collections.unmodifiableList(
            Arrays.asList(
                    PRIMARY_TARGET,
                    "UPDATE_CONTROLLER_OTF_FG_R1",
                    "UPDATE_CONTROLLER_OTF_FG_R2"));

    private static final List<String> EXPECTED_MODELS = Collections.unmodifiableList(
            Arrays.asList(
                    "GSM_FG.lts",
                    "Industry_FG.lts",
                    "MetaSocket_FG.lts",
                    "PowerPlant_FG.lts",
                    "ProductionCell_Arms=1_FG.lts",
                    "ProductionCell_Arms=2_FG.lts",
                    "Railcab_FG.lts",
                    "Surveillance_FG.lts",
                    "Workflow_FG.lts"));

    @Test
    public void everyPrimaryExperimentModelUsesTheRevisedOtfEngine() throws Exception {
        if (!Boolean.getBoolean(ENABLE_PROPERTY)) {
            throw new SkipException(
                    "Heavy revised OTF integration test is opt-in; set -D"
                            + ENABLE_PROPERTY + "=true");
        }

        Path modelsDirectory = resolveModelsDirectory();
        assertExactModelSet(modelsDirectory);

        String previousEvaluationValue = System.getProperty(EVALUATION_PROPERTY);
        System.setProperty(EVALUATION_PROPERTY, "false");
        try {
            String target = selectedTarget();
            for (String modelName : selectedModels()) {
                compileComposeAndCheck(modelsDirectory.resolve(modelName), target);
            }
        } finally {
            restoreProperty(EVALUATION_PROPERTY, previousEvaluationValue);
        }
    }

    private static String selectedTarget() {
        String selected = System.getProperty(TARGET_PROPERTY, PRIMARY_TARGET).trim();
        assertTrue(REVISED_TARGETS.contains(selected),
                "-D" + TARGET_PROPERTY + " must name one of " + REVISED_TARGETS
                        + " but was " + selected);
        return selected;
    }

    private static List<String> selectedModels() {
        String selected = System.getProperty(MODEL_PROPERTY);
        if (selected == null || selected.trim().isEmpty()) {
            return EXPECTED_MODELS;
        }
        String normalized = selected.trim();
        assertTrue(EXPECTED_MODELS.contains(normalized),
                "-D" + MODEL_PROPERTY + " must name one of " + EXPECTED_MODELS
                        + " but was " + normalized);
        return Collections.singletonList(normalized);
    }

    private static void compileComposeAndCheck(
            Path modelPath,
            String targetName) throws Exception {
        String caseLabel = modelPath.getFileName() + " / " + targetName;
        RecordingLtsOutput output = new RecordingLtsOutput();
        LTSCompiler compiler = new LTSCompiler(
                new FileInput(modelPath.toFile()),
                output,
                modelPath.getParent().toString());

        compiler.compile();
        CompositeState composite;
        try {
            composite = compiler.continueCompilation(targetName);
        } catch (LTSCompositionException losing) {
            assertRevisedEngineWasUsed(output, caseLabel);
            String transcript = output.toString();
            assertTrue(transcript.contains("Revised OTF-DUCS result: NO STRONG SOLUTION"),
                    caseLabel + ": composition aborted without a verified losing result\n"
                            + output.tail(4000));
            assertTrue(transcript.contains(
                            "Internal certificate checker (same successor semantics): passed"),
                    caseLabel + ": losing certificate did not pass the built-in checker\n"
                            + output.tail(4000));
            printOutputWhenRequested(caseLabel, output);
            System.out.println("REVISED_OTF_RESULT " + caseLabel + " LOSING");
            return;
        }
        assertNotNull(composite, caseLabel + ": continueCompilation returned null");
        if (composite instanceof UpdatingControllerCompositeState) {
            UpdatingControllerCompositeState updating =
                    (UpdatingControllerCompositeState) composite;
            assertTrue(updating.isOTF(), caseLabel + ": target is not marked on-the-fly");
            assertTrue(updating.isFineGrained(), caseLabel + ": target is not fine-grained");
            assertTrue(updating.isRevisedOnTheFly(),
                    caseLabel + ": target is not marked for the revised OTF engine");
        }

        /*
         * Experiment targets are intentionally public || aliases. Resolving the
         * alias synthesises its UpdatingControllerCompositeState and returns a
         * one-machine CompositeState, which is exactly the object passed by the
         * GUI Compose action to the dispatcher.
         */
        TransitionSystemDispatcher.applyComposition(composite, output);
        assertNotNull(composite.getComposition(),
                caseLabel + ": dispatcher produced no controller composition\n"
                        + output.tail(4000));

        assertRevisedEngineWasUsed(output, caseLabel);
        assertFalse(Arrays.asList(composite.getComposition().alphabet).contains("hotSwapOut"),
                caseLabel + ": revised atomic Link must not expose hotSwapOut as an event");
        printOutputWhenRequested(caseLabel, output);
        System.out.println("REVISED_OTF_RESULT " + caseLabel + " WINNING");
    }

    private static void printOutputWhenRequested(
            String caseLabel,
            RecordingLtsOutput output) {
        if (Boolean.getBoolean(PRINT_OUTPUT_PROPERTY)) {
            System.out.println("REVISED_OTF_OUTPUT_BEGIN " + caseLabel);
            System.out.print(output.toString());
            System.out.println("REVISED_OTF_OUTPUT_END " + caseLabel);
        }
    }

    private static void assertRevisedEngineWasUsed(
            RecordingLtsOutput output,
            String caseLabel) {
        String transcript = output.toString();
        String normalizedOutput = transcript.toLowerCase(Locale.ROOT);
        boolean revisedMarkerPresent =
                normalizedOutput.contains("revised otf-ducs")
                        || normalizedOutput.contains("revised otf-duc")
                        || normalizedOutput.contains("revised_otf_ducs");
        if (!revisedMarkerPresent) {
            fail(caseLabel
                    + ": revised-engine output marker was not found; this prevents the test "
                            + "from distinguishing the revised implementation from the legacy path\n"
                    + output.tail(4000));
        }
        assertTrue(
                transcript.contains("Using explicitly supplied New Controller:"),
                caseLabel + ": revised target did not use its explicit newController; "
                        + "falling back to internal synthesis would make the tested endpoint "
                        + "different from the declared controller\n"
                        + output.tail(4000));
        String expectedOrder =
                FineGrainedSuccessorOracle.ControllableActionOrder
                        .configured().propertyValue();
        assertTrue(
                transcript.contains(
                        "Controllable action order: " + expectedOrder),
                caseLabel + ": selected controllable-action order was not "
                        + "reported as " + expectedOrder + "\n"
                        + output.tail(4000));
    }

    private static Path resolveModelsDirectory() {
        String configured = System.getProperty(MODELS_DIRECTORY_PROPERTY);
        if (configured != null && !configured.trim().isEmpty()) {
            Path configuredPath = Paths.get(configured);
            if (!configuredPath.isAbsolute()) {
                configuredPath = Paths.get(System.getProperty("user.dir"))
                        .resolve(configuredPath);
            }
            return requireModelsDirectory(configuredPath.normalize());
        }

        Path cursor = Paths.get(System.getProperty("user.dir"))
                .toAbsolutePath()
                .normalize();
        List<Path> tried = new ArrayList<Path>();
        while (cursor != null) {
            Path implementationRelative = cursor
                    .resolve("Implementation")
                    .resolve("Experiment")
                    .resolve("Models");
            tried.add(implementationRelative);
            if (Files.isDirectory(implementationRelative)) {
                return implementationRelative;
            }

            Path moduleRelative = cursor
                    .resolve("Experiment")
                    .resolve("Models");
            tried.add(moduleRelative);
            if (Files.isDirectory(moduleRelative)) {
                return moduleRelative;
            }
            cursor = cursor.getParent();
        }
        throw new AssertionError(
                "Could not locate Implementation/Experiment/Models from user.dir="
                        + System.getProperty("user.dir") + "; tried " + tried);
    }

    private static Path requireModelsDirectory(Path path) {
        if (!Files.isDirectory(path)) {
            throw new AssertionError(
                    "Configured experiment models directory does not exist: " + path);
        }
        return path;
    }

    private static void assertExactModelSet(Path modelsDirectory) throws Exception {
        Set<String> actual;
        try (Stream<Path> files = Files.list(modelsDirectory)) {
            actual = files
                    .filter(Files::isRegularFile)
                    .map(path -> path.getFileName().toString())
                    .filter(name -> name.endsWith(".lts"))
                    .sorted()
                    .collect(Collectors.toCollection(LinkedHashSet::new));
        }
        Set<String> expected = new LinkedHashSet<String>(EXPECTED_MODELS);
        assertEquals(actual, expected,
                "Experiment/Models file set changed; update the integration matrix explicitly");
    }

    private static void restoreProperty(String name, String previousValue) {
        if (previousValue == null) {
            System.clearProperty(name);
        } else {
            System.setProperty(name, previousValue);
        }
    }

    private static final class RecordingLtsOutput implements LTSOutput {
        private final StringBuilder content = new StringBuilder();

        @Override
        public void clearOutput() {
            content.setLength(0);
        }

        @Override
        public void out(String value) {
            content.append(value);
        }

        @Override
        public void outln(String value) {
            content.append(value).append(System.lineSeparator());
        }

        private String tail(int maximumCharacters) {
            int start = Math.max(0, content.length() - maximumCharacters);
            return content.substring(start);
        }

        @Override
        public String toString() {
            return content.toString();
        }
    }
}
