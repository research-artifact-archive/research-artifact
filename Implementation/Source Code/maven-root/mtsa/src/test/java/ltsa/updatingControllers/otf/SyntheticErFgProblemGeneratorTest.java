package ltsa.updatingControllers.otf;

import org.testng.annotations.Test;

import java.io.BufferedReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

public class SyntheticErFgProblemGeneratorTest {

    @Test
    public void generationIsDeterministicAndProfilesAreMatched() {
        SyntheticErFgProblemGenerator.GeneratedProblem first =
                SyntheticErFgProblemGenerator.generate(
                        SyntheticErFgProblemGenerator.Topology.PIPELINE,
                        2,
                        17L,
                        SyntheticErFgProblemGenerator.UProfile.U_LOCAL,
                        SyntheticErFgProblemGenerator.Mutation.BASE);
        SyntheticErFgProblemGenerator.GeneratedProblem second =
                SyntheticErFgProblemGenerator.generate(
                        SyntheticErFgProblemGenerator.Topology.PIPELINE,
                        2,
                        17L,
                        SyntheticErFgProblemGenerator.UProfile.U_LOCAL,
                        SyntheticErFgProblemGenerator.Mutation.BASE);
        SyntheticErFgProblemGenerator.GeneratedProblem cross =
                SyntheticErFgProblemGenerator.generate(
                        SyntheticErFgProblemGenerator.Topology.PIPELINE,
                        2,
                        17L,
                        SyntheticErFgProblemGenerator.UProfile.U_CROSS,
                        SyntheticErFgProblemGenerator.Mutation.BASE);
        SyntheticErFgProblemGenerator.GeneratedProblem noUpdateMonitor =
                SyntheticErFgProblemGenerator.generate(
                        SyntheticErFgProblemGenerator.Topology.PIPELINE,
                        2,
                        17L,
                        SyntheticErFgProblemGenerator.UProfile.U0,
                        SyntheticErFgProblemGenerator.Mutation.BASE);

        assertEquals(first.modelHash(), second.modelHash());
        assertEquals(first.inputId(), second.inputId());
        assertTrue(first.problem().hasExhaustiveEndpointCoverage());
        assertFalse(
                first.oldClosedLoop()
                        .reachableStates()
                        .isEmpty());
        assertFalse(
                first.newClosedLoop()
                        .reachableStates()
                        .isEmpty());
        assertEquals(1, first.oldRequirementCount());
        assertEquals(1, first.newRequirementCount());
        assertEquals(1, first.updateRequirementCount());
        assertEquals(4, first.uncontrollableNormalActionCount());
        assertEquals(
                first.uncontrollableNormalActionCount(),
                cross.uncontrollableNormalActionCount());
        assertEquals(
                first.normalActionCount(),
                cross.normalActionCount());
        assertFalse(first.modelHash().equals(cross.modelHash()));
        assertEquals(0, noUpdateMonitor.updateRequirementCount());
        assertEquals(0, noUpdateMonitor.uncontrollableNormalActionCount());
    }

    @Test
    public void allBaseProfilesWinAndPassIndependentReference() {
        for (SyntheticErFgProblemGenerator.UProfile profile
                : SyntheticErFgProblemGenerator.UProfile.values()) {
            SyntheticErFgProblemGenerator.GeneratedProblem generated =
                    SyntheticErFgProblemGenerator.generate(
                            SyntheticErFgProblemGenerator.Topology.HUB,
                            2,
                            23L,
                            profile,
                            SyntheticErFgProblemGenerator.Mutation.BASE);
            OtfDucsResult<
                    CanonicalUpdateConfiguration<String, String>,
                    String,
                    GoalSignature<String, String>> result =
                    solveCompleteLazy(generated);

            assertTrue(profile.id(), result.isWinning());
            assertTrue(
                    profile.id(),
                    new IndependentExplicitStrongSolver<String, String>(
                            generated.problem(),
                            200_000L,
                            2_000_000L)
                            .verify(result)
                            .isValid());
            LinkedOtfDucsController<
                    PhysicalState<String>,
                    String,
                    String,
                    PhysicalState<String>> linked =
                    LinkedOtfDucsController.link(
                            generated.oldClosedLoop(),
                            generated.newClosedLoop(),
                            generated.problem(),
                            result,
                            generated::initialProjection,
                            generated::goalProjection);
            assertFalse(profile.id(), linked.lts().states().isEmpty());
        }
    }

    @Test
    public void eachUnrealizableMutationStratumLosesAndIsVerified() {
        for (SyntheticErFgProblemGenerator.Mutation mutation
                : SyntheticErFgProblemGenerator.Mutation.values()) {
            if (mutation == SyntheticErFgProblemGenerator.Mutation.BASE) {
                continue;
            }
            SyntheticErFgProblemGenerator.GeneratedProblem generated =
                    SyntheticErFgProblemGenerator.generate(
                            SyntheticErFgProblemGenerator.Topology.RING,
                            2,
                            31L,
                            SyntheticErFgProblemGenerator.UProfile.U0,
                            mutation);
            OtfDucsResult<
                    CanonicalUpdateConfiguration<String, String>,
                    String,
                    GoalSignature<String, String>> result =
                    solveCompleteLazy(generated);

            assertFalse(mutation.id(), result.isWinning());
            assertTrue(
                    mutation.id(),
                    new IndependentExplicitStrongSolver<String, String>(
                            generated.problem(),
                            200_000L,
                            2_000_000L)
                            .verify(result)
                            .isValid());
        }
    }

    @Test
    public void benchmarkWritesOneAuthoritativeRowPerMethodAndMutation()
            throws Exception {
        Path directory = Files.createTempDirectory(
                "synthetic-erfg-smoke-");
        Path output = directory.resolve("runs.csv");
        String sourceManifestSha256 =
                repeat('a', 64);
        String[] arguments = new String[] {
            "--output", output.toString(),
            "--panel", "custom",
            "--seeds", "7",
            "--sizes", "2",
            "--topologies", "pipeline",
            "--profiles", "u0",
            "--mutations",
            "base,empty_transfer,reject_uncontrollable,uncontrollable_livelock",
            "--methods", "fg_otf,direct_full",
            "--method-order-methods",
            "fg_otf,eager_c,guided,update_first,direct_full",
            "--repetitions", "1",
            "--reference", "true",
            "--source-manifest-sha256",
            sourceManifestSha256
        };
        Fse2027SyntheticBenchmark.main(
                arguments);

        List<List<String>> csv = readCsv(output);
        assertEquals(1 + 4 * 2, csv.size());
        List<String> columns = csv.get(0);
        Map<String, String> firstRow =
                row(columns, csv.get(1));
        assertEquals(
                5,
                firstRow.get("method_order_sequence")
                        .split(">")
                        .length);
        assertEquals(
                "fse2027-synthetic-run-v2",
                firstRow.get("schema_version"));
        assertEquals(
                "run-id-v2",
                firstRow.get("run_id_version"));
        assertEquals(
                sourceManifestSha256,
                firstRow.get("source_manifest_sha256"));
        assertEquals(
                jsonArray(arguments),
                firstRow.get("benchmark_argv_json"));
        assertEquals(
                SyntheticErFgProblemGenerator.sha256Hex(
                        jsonArray(arguments)),
                firstRow.get("benchmark_argv_sha256"));
        assertEquals(
                Long.toString(
                        Runtime.getRuntime().maxMemory()),
                firstRow.get("jvm_max_memory_bytes"));
        assertEquals(
                "not_measured_by_in_process_driver",
                firstRow.get(
                        "outer_timeout_measurement_status"));
        assertEquals(
                "not_measured",
                firstRow.get("outer_timeout_seconds"));
        assertEquals(
                "not_measured_by_in_process_driver",
                firstRow.get(
                        "peak_rss_measurement_status"));
        assertEquals(
                "not_measured",
                firstRow.get("peak_rss_bytes"));
        assertFalse(
                firstRow.get("code_source_location")
                        .isEmpty());
        assertFalse(
                firstRow.get("execution_artifact_kind")
                        .isEmpty());

        Path secondOutput = directory.resolve(
                "runs-again.csv");
        String[] secondArguments = arguments.clone();
        secondArguments[1] = secondOutput.toString();
        Fse2027SyntheticBenchmark.main(secondArguments);
        List<List<String>> secondCsv =
                readCsv(secondOutput);
        for (int index = 1; index < csv.size(); index++) {
            Map<String, String> first =
                    row(columns, csv.get(index));
            Map<String, String> second =
                    row(secondCsv.get(0), secondCsv.get(index));
            assertEquals(
                    first.get("run_id"),
                    second.get("run_id"));
        }
        assertFalse(
                firstRow.get("benchmark_argv_json")
                        .equals(
                                row(
                                        secondCsv.get(0),
                                        secondCsv.get(1))
                                        .get(
                                                "benchmark_argv_json")));
    }

    @Test
    public void benchmarkRejectsMalformedSourceManifestDigest()
            throws Exception {
        Path output = Files.createTempDirectory(
                        "synthetic-erfg-invalid-manifest-")
                .resolve("runs.csv");
        boolean rejected = false;
        try {
            Fse2027SyntheticBenchmark.main(
                    new String[] {
                        "--output", output.toString(),
                        "--source-manifest-sha256", "not-a-sha256"
                    });
        } catch (IllegalArgumentException expected) {
            rejected = true;
            assertTrue(
                    expected.getMessage()
                            .contains(
                                    "exactly 64 hexadecimal"));
        }
        assertTrue(rejected);
        assertFalse(Files.exists(output));
    }

    @Test
    public void benchmarkRecordsUnknownWhenManifestOptionIsOmitted()
            throws Exception {
        Path output = Files.createTempDirectory(
                        "synthetic-erfg-unknown-manifest-")
                .resolve("runs.csv");
        Fse2027SyntheticBenchmark.main(
                new String[] {
                    "--output", output.toString(),
                    "--panel", "custom",
                    "--seeds", "7",
                    "--sizes", "2",
                    "--topologies", "pipeline",
                    "--profiles", "u0",
                    "--mutations", "base",
                    "--methods", "fg_otf",
                    "--repetitions", "1",
                    "--reference", "false"
                });
        List<List<String>> csv = readCsv(output);
        assertEquals(
                "unknown",
                row(csv.get(0), csv.get(1))
                        .get("source_manifest_sha256"));
    }

    private static List<List<String>> readCsv(Path path)
            throws Exception {
        List<List<String>> result =
                new ArrayList<List<String>>();
        try (BufferedReader reader = Files.newBufferedReader(
                path, StandardCharsets.UTF_8)) {
            String line;
            while ((line = reader.readLine()) != null) {
                result.add(parseCsvLine(line));
            }
        }
        return result;
    }

    private static List<String> parseCsvLine(String line) {
        List<String> values = new ArrayList<String>();
        StringBuilder value = new StringBuilder();
        boolean quoted = false;
        for (int index = 0; index < line.length(); index++) {
            char character = line.charAt(index);
            if (quoted) {
                if (character == '"') {
                    if (index + 1 < line.length()
                            && line.charAt(index + 1) == '"') {
                        value.append('"');
                        index++;
                    } else {
                        quoted = false;
                    }
                } else {
                    value.append(character);
                }
            } else if (character == '"') {
                quoted = true;
            } else if (character == ',') {
                values.add(value.toString());
                value.setLength(0);
            } else {
                value.append(character);
            }
        }
        if (quoted) {
            throw new IllegalArgumentException(
                    "unterminated quoted CSV field");
        }
        values.add(value.toString());
        return values;
    }

    private static Map<String, String> row(
            List<String> header,
            List<String> values) {
        assertEquals(header.size(), values.size());
        Map<String, String> result =
                new LinkedHashMap<String, String>();
        for (int index = 0; index < header.size(); index++) {
            result.put(header.get(index), values.get(index));
        }
        return result;
    }

    private static String jsonArray(String[] values) {
        StringBuilder result = new StringBuilder("[");
        for (int index = 0; index < values.length; index++) {
            if (index > 0) {
                result.append(',');
            }
            result.append('"')
                    .append(
                            values[index]
                                    .replace("\\", "\\\\")
                                    .replace("\"", "\\\""))
                    .append('"');
        }
        return result.append(']').toString();
    }

    private static String repeat(char value, int count) {
        char[] values = new char[count];
        Arrays.fill(values, value);
        return new String(values);
    }

    private static OtfDucsResult<
            CanonicalUpdateConfiguration<String, String>,
            String,
            GoalSignature<String, String>> solveCompleteLazy(
                    SyntheticErFgProblemGenerator.GeneratedProblem
                            generated) {
        OtfDucsResult<
                CanonicalUpdateConfiguration<String, String>,
                String,
                GoalSignature<String, String>> result =
                FineGrainedOtfDucs.synthesize(generated.problem());
        assertTrue(
                FineGrainedOtfDucs.verify(
                        generated.problem(), result)
                        .isValid());
        return result;
    }
}
