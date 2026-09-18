package ltsa.updatingControllers.otf;

import java.io.BufferedWriter;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.security.CodeSource;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Comparator;
import java.util.EnumSet;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

/**
 * Standalone, deterministic synthetic benchmark for the FSE 2027 evaluation.
 *
 * <p>The CSV is deliberately a flat, one-row-per-input/method/repetition
 * table.  It includes all experimental factors, expected and actual decisions,
 * production certificate checking, a separately implemented exhaustive
 * reference check, search work, timing, and deterministic method-order
 * metadata.  Rows are flushed immediately so a resource-limited outer harness
 * retains every completed observation.</p>
 */
public final class Fse2027SyntheticBenchmark {

    private static final String SCHEMA_VERSION = "fse2027-synthetic-run-v2";
    private static final String RUN_ID_VERSION = "run-id-v2";
    private static final String METHOD_ORDER_VERSION = "method-order-v1";
    private static final String NOT_MEASURED = "not_measured";
    private static final String NOT_MEASURED_BY_DRIVER =
            "not_measured_by_in_process_driver";

    private static final List<String> HEADER = Collections.unmodifiableList(
            Arrays.asList(
                    "schema_version",
                    "run_id",
                    "timestamp_utc",
                    "panel_id",
                    "input_id",
                    "topology",
                    "component_count",
                    "master_seed",
                    "seed_rank",
                    "seed_selection_version",
                    "seed_universe",
                    "panel_seed_count",
                    "pilot_seed_count",
                    "u_profile",
                    "mutation",
                    "mutated_component",
                    "expected_decision",
                    "method",
                    "method_family",
                    "representation",
                    "policy",
                    "controllable_order",
                    "lazy_controllable_buckets",
                    "guided_state_limit",
                    "guided_query_limit",
                    "reference_enabled",
                    "reference_state_limit",
                    "reference_query_limit",
                    "repetition",
                    "warmup_repetitions",
                    "method_order_version",
                    "method_order_key",
                    "method_order_rotation",
                    "method_order_direction",
                    "method_order_position",
                    "method_order_sequence",
                    "status",
                    "decision",
                    "decision_matches_expected",
                    "run_verified",
                    "certificate_verification_status",
                    "certificate_valid",
                    "certificate_violations",
                    "reference_verification_status",
                    "reference_complete",
                    "reference_valid",
                    "reference_reason",
                    "generation_time_ns",
                    "solver_time_ns",
                    "certificate_verification_time_ns",
                    "reference_verification_time_ns",
                    "end_to_end_time_ns",
                    "discovered_states",
                    "expanded_states",
                    "queried_state_action_pairs",
                    "materialized_transitions",
                    "propagated_incidences",
                    "peak_frontier",
                    "early_success",
                    "guided_proof_accepted",
                    "guided_fallback_used",
                    "guided_maximum_depth",
                    "attractor_peak_frontier",
                    "deferred_controllable_candidates",
                    "resumed_controllable_candidates",
                    "unqueried_controllable_candidates",
                    "certificate_states",
                    "certificate_transitions",
                    "worst_rank",
                    "losing_certificate_states",
                    "direct_full_enumerated_states",
                    "direct_full_enabled_buckets",
                    "direct_full_fixed_point_iterations",
                    "direct_full_state_inspections",
                    "direct_full_bucket_inspections",
                    "direct_full_outcome_inspections",
                    "direct_full_enumeration_time_ns",
                    "direct_full_fixed_point_time_ns",
                    "direct_full_certificate_time_ns",
                    "reference_states",
                    "reference_queries",
                    "reference_outcomes",
                    "topology_edges",
                    "old_requirements",
                    "new_requirements",
                    "update_time_requirements",
                    "normal_actions",
                    "controllable_normal_actions",
                    "uncontrollable_normal_actions",
                    "update_actions",
                    "precedence_edges",
                    "transfer_relation_edges",
                    "model_hash_sha256",
                    "generator_version",
                    "jvm_version",
                    "java_vendor",
                    "os_name",
                    "os_arch",
                    "available_processors",
                    "error_class",
                    "error_message",
                    "run_id_version",
                    "benchmark_argv_json",
                    "benchmark_argv_sha256",
                    "code_source_location",
                    "execution_artifact_kind",
                    "execution_artifact_path",
                    "execution_artifact_sha256",
                    "execution_artifact_bytes",
                    "execution_artifact_hash_status",
                    "source_manifest_sha256",
                    "jvm_max_memory_bytes",
                    "outer_timeout_measurement_status",
                    "outer_timeout_seconds",
                    "peak_rss_measurement_status",
                    "peak_rss_bytes"));

    private Fse2027SyntheticBenchmark() {
        // Command-line utility.
    }

    public static void main(String[] arguments) throws Exception {
        Options options = Options.parse(arguments);
        if (options.help) {
            printUsage();
            return;
        }
        options.validate();
        prepareOutput(options.output, options.force);
        ExecutionProvenance provenance =
                ExecutionProvenance.capture(
                        arguments,
                        options.sourceManifestSha256);

        List<SeedSelection> seeds = selectSeeds(options);
        long completedRows = 0L;
        long verifiedRows = 0L;
        long mismatchRows = 0L;
        try (BufferedWriter writer = Files.newBufferedWriter(
                options.output,
                StandardCharsets.UTF_8,
                StandardOpenOption.CREATE_NEW,
                StandardOpenOption.WRITE)) {
            writeCsvRow(writer, HEADER);
            writer.flush();

            for (SyntheticErFgProblemGenerator.Topology topology
                    : options.topologies) {
                for (Integer size : options.sizes) {
                    for (SeedSelection seed : seeds) {
                        for (SyntheticErFgProblemGenerator.UProfile profile
                                : options.profiles) {
                            for (SyntheticErFgProblemGenerator.Mutation mutation
                                    : options.mutations) {
                                long generationStarted = System.nanoTime();
                                SyntheticErFgProblemGenerator.GeneratedProblem
                                        generated =
                                        SyntheticErFgProblemGenerator.generate(
                                                topology,
                                                size.intValue(),
                                                seed.seed,
                                                profile,
                                                mutation);
                                long generationTime =
                                        System.nanoTime()
                                                - generationStarted;

                                runWarmups(
                                        options,
                                        generated);
                                for (int repetition = 0;
                                        repetition
                                                < options.repetitions;
                                        repetition++) {
                                    MethodOrder order = methodOrder(
                                            options.methodOrderMethods(),
                                            generated,
                                            repetition);
                                    for (int position = 0;
                                            position
                                                    < order.methods.size();
                                            position++) {
                                        Method method =
                                                order.methods.get(position);
                                        if (!options.methods.contains(
                                                method)) {
                                            continue;
                                        }
                                        Map<String, String> row =
                                                baseRow(
                                                        options,
                                                        generated,
                                                        seed,
                                                        method,
                                                        repetition,
                                                        order,
                                                        position,
                                                        generationTime,
                                                        provenance);
                                        executeMeasured(
                                                options,
                                                generated,
                                                method,
                                                row);
                                        writeMapRow(writer, row);
                                        writer.flush();
                                        completedRows++;
                                        if ("true".equals(
                                                row.get(
                                                        "run_verified"))) {
                                            verifiedRows++;
                                        }
                                        if ("false".equals(
                                                row.get(
                                                        "decision_matches_expected"))) {
                                            mismatchRows++;
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        System.out.println(
                "Synthetic ER-FG benchmark complete: rows="
                        + completedRows
                        + ", independently verified="
                        + verifiedRows
                        + ", unexpected decisions="
                        + mismatchRows
                        + ", output="
                        + options.output.toAbsolutePath());
        if (mismatchRows > 0L) {
            throw new IllegalStateException(
                    "At least one generated instance disagreed with its "
                            + "predeclared mutation oracle; inspect the CSV");
        }
    }

    private static void runWarmups(
            Options options,
            SyntheticErFgProblemGenerator.GeneratedProblem generated) {
        for (int repetition = 0;
                repetition < options.warmups;
                repetition++) {
            for (Method method : options.methods) {
                try {
                    execute(
                            options,
                            generated,
                            method,
                            false);
                } catch (Throwable ignored) {
                    /*
                     * A measured row will record the failure.  Warm-ups are
                     * intentionally absent from the authoritative CSV.
                     */
                }
            }
        }
    }

    private static void executeMeasured(
            Options options,
            SyntheticErFgProblemGenerator.GeneratedProblem generated,
            Method method,
            Map<String, String> row) {
        long started = System.nanoTime();
        try {
            Execution execution = execute(
                    options,
                    generated,
                    method,
                    options.referenceVerification);
            populateExecution(row, execution, generated);
        } catch (Throwable failure) {
            row.put("status", "error");
            row.put("run_verified", "false");
            row.put("error_class", failure.getClass().getName());
            row.put(
                    "error_message",
                    failure.getMessage() == null
                            ? ""
                            : failure.getMessage());
        } finally {
            row.put(
                    "end_to_end_time_ns",
                    Long.toString(System.nanoTime() - started));
        }
    }

    private static Execution execute(
            Options options,
            SyntheticErFgProblemGenerator.GeneratedProblem generated,
            Method method,
            boolean runReference) {
        if (!generated.problem().hasExhaustiveEndpointCoverage()) {
            throw new IllegalArgumentException(
                    "Synthetic benchmark inputs must exhaustively enumerate "
                            + "the reachable old and new endpoint closed loops");
        }
        FineGrainedSuccessorOracle.ControllableActionOrder actionOrder =
                method == Method.UPDATE_FIRST
                        ? FineGrainedSuccessorOracle
                                .ControllableActionOrder
                                .UPDATE_FIRST
                        : FineGrainedSuccessorOracle
                                .ControllableActionOrder
                                .ENDPOINT_GUIDED;
        FineGrainedSuccessorOracle<String, String> game =
                new FineGrainedSuccessorOracle<String, String>(
                        generated.problem(), actionOrder);

        OtfDucsResult<
                CanonicalUpdateConfiguration<String, String>,
                String,
                GoalSignature<String, String>> result;
        DirectFullStrongSolver.Statistics directStatistics = null;
        long solverStarted = System.nanoTime();
        if (method == Method.DIRECT_FULL) {
            DirectFullStrongSolver<
                    CanonicalUpdateConfiguration<String, String>,
                    String,
                    GoalSignature<String, String>> solver =
                    new DirectFullStrongSolver<
                            CanonicalUpdateConfiguration<String, String>,
                            String,
                            GoalSignature<String, String>>(game);
            result = solver.synthesize();
            directStatistics = solver.statistics();
        } else {
            int guidedStates = method == Method.GUIDED
                    ? options.guidedStateLimit : 0;
            int guidedQueries = method == Method.GUIDED
                    ? options.guidedQueryLimit : 0;
            boolean lazy = method != Method.EAGER_C;
            result = new OtfDucsSynthesizer<
                    CanonicalUpdateConfiguration<String, String>,
                    String,
                    GoalSignature<String, String>>(
                            game,
                            guidedStates,
                            guidedQueries,
                            lazy)
                    .synthesize();
        }
        long solverTime = System.nanoTime() - solverStarted;

        long certificateStarted = System.nanoTime();
        OtfDucsCertificateChecker.VerificationReport
                certificateVerification =
                new OtfDucsCertificateChecker<
                        CanonicalUpdateConfiguration<String, String>,
                        String,
                        GoalSignature<String, String>>(game)
                        .verify(result);
        long certificateTime =
                System.nanoTime() - certificateStarted;

        IndependentExplicitStrongSolver.VerificationReport
                referenceVerification = null;
        Throwable referenceFailure = null;
        long referenceTime = 0L;
        if (runReference) {
            long referenceStarted = System.nanoTime();
            try {
                referenceVerification =
                        new IndependentExplicitStrongSolver<
                                String, String>(
                                generated.problem(),
                                options.referenceStateLimit,
                                options.referenceQueryLimit)
                                .verify(result);
            } catch (Throwable failure) {
                referenceFailure = failure;
            } finally {
                referenceTime =
                        System.nanoTime() - referenceStarted;
            }
        }
        return new Execution(
                result,
                directStatistics,
                certificateVerification,
                referenceVerification,
                referenceFailure,
                solverTime,
                certificateTime,
                referenceTime,
                runReference);
    }

    private static void populateExecution(
            Map<String, String> row,
            Execution execution,
            SyntheticErFgProblemGenerator.GeneratedProblem generated) {
        OtfDucsResult<
                CanonicalUpdateConfiguration<String, String>,
                String,
                GoalSignature<String, String>> result =
                execution.result;
        OtfDucsResult.Statistics statistics =
                result.statistics();
        row.put(
                "decision",
                result.isWinning() ? "winning" : "losing");
        boolean decisionMatches =
                result.isWinning() == generated.expectedWinning();
        row.put(
                "decision_matches_expected",
                Boolean.toString(decisionMatches));
        row.put(
                "solver_time_ns",
                Long.toString(execution.solverTime));
        row.put(
                "certificate_verification_time_ns",
                Long.toString(execution.certificateTime));
        row.put(
                "reference_verification_time_ns",
                Long.toString(execution.referenceTime));

        row.put(
                "certificate_valid",
                Boolean.toString(
                        execution.certificateVerification.isValid()));
        row.put(
                "certificate_verification_status",
                execution.certificateVerification.isValid()
                        ? "passed" : "failed");
        row.put(
                "certificate_violations",
                join(
                        execution.certificateVerification
                                .violations(),
                        " | "));

        boolean independentlyVerified = false;
        if (!execution.referenceRequested) {
            row.put(
                    "reference_verification_status",
                    "disabled");
            row.put("reference_complete", "false");
            row.put("reference_valid", "false");
            row.put(
                    "reference_reason",
                    "disabled by CLI");
        } else if (execution.referenceFailure != null) {
            row.put(
                    "reference_verification_status",
                    "error");
            row.put("reference_complete", "false");
            row.put("reference_valid", "false");
            row.put(
                    "reference_reason",
                    execution.referenceFailure
                                    .getMessage()
                            == null
                            ? execution.referenceFailure
                                    .getClass().getName()
                            : execution.referenceFailure
                                    .getClass().getName()
                                    + ": "
                                    + execution.referenceFailure
                                            .getMessage());
        } else {
            IndependentExplicitStrongSolver.VerificationReport
                    reference = execution.referenceVerification;
            row.put(
                    "reference_complete",
                    Boolean.toString(reference.isComplete()));
            row.put(
                    "reference_valid",
                    Boolean.toString(reference.isValid()));
            row.put(
                    "reference_reason",
                    reference.reason());
            row.put(
                    "reference_states",
                    Long.toString(reference.states()));
            row.put(
                    "reference_queries",
                    Long.toString(reference.queries()));
            row.put(
                    "reference_outcomes",
                    Long.toString(reference.outcomes()));
            if (reference.isValid()) {
                row.put(
                        "reference_verification_status",
                        "passed");
                independentlyVerified = true;
            } else if (reference.isComplete()) {
                row.put(
                        "reference_verification_status",
                        "failed");
            } else {
                row.put(
                        "reference_verification_status",
                        "inconclusive");
            }
        }

        boolean runVerified =
                decisionMatches
                        && execution.certificateVerification.isValid()
                        && independentlyVerified;
        row.put("run_verified", Boolean.toString(runVerified));
        if (!decisionMatches) {
            row.put("status", "unexpected_decision");
        } else if (!execution.certificateVerification.isValid()) {
            row.put("status", "invalid_certificate");
        } else if (independentlyVerified) {
            row.put("status", "verified");
        } else {
            row.put("status", "unverified");
        }

        row.put(
                "discovered_states",
                Long.toString(statistics.discoveredStates()));
        row.put(
                "expanded_states",
                Long.toString(statistics.expandedStates()));
        row.put(
                "queried_state_action_pairs",
                Long.toString(
                        statistics.queriedStateActionPairs()));
        row.put(
                "materialized_transitions",
                Long.toString(
                        statistics.materializedTransitions()));
        row.put(
                "propagated_incidences",
                Long.toString(
                        statistics.propagatedIncidences()));
        row.put(
                "peak_frontier",
                Long.toString(statistics.peakFrontier()));
        row.put(
                "early_success",
                Boolean.toString(statistics.earlySuccess()));
        row.put(
                "guided_proof_accepted",
                Boolean.toString(
                        statistics.guidedProofAccepted()));
        row.put(
                "guided_fallback_used",
                Boolean.toString(
                        statistics.guidedFallbackUsed()));
        row.put(
                "guided_maximum_depth",
                Long.toString(
                        statistics.guidedMaximumDepth()));
        row.put(
                "attractor_peak_frontier",
                Long.toString(
                        statistics.attractorPeakFrontier()));
        row.put(
                "deferred_controllable_candidates",
                Long.toString(
                        statistics
                                .deferredControllableCandidates()));
        row.put(
                "resumed_controllable_candidates",
                Long.toString(
                        statistics
                                .resumedControllableCandidates()));
        row.put(
                "unqueried_controllable_candidates",
                Long.toString(
                        statistics
                                .unqueriedControllableCandidatesAtTermination()));

        if (result.isWinning()) {
            OtfDucsResult.WinningCertificate<
                    CanonicalUpdateConfiguration<String, String>,
                    String,
                    GoalSignature<String, String>> certificate =
                    result.winningCertificate();
            row.put(
                    "certificate_states",
                    Integer.toString(certificate.ranks().size()));
            long transitions = 0L;
            int maximumRank = 0;
            for (Integer rank : certificate.ranks().values()) {
                maximumRank =
                        Math.max(maximumRank, rank.intValue());
            }
            for (Map<String, Set<
                    CanonicalUpdateConfiguration<String, String>>>
                    buckets : certificate.strategy().values()) {
                for (Set<CanonicalUpdateConfiguration<
                        String, String>> outcomes
                        : buckets.values()) {
                    transitions += outcomes.size();
                }
            }
            row.put(
                    "certificate_transitions",
                    Long.toString(transitions));
            row.put(
                    "worst_rank",
                    Integer.toString(maximumRank));
            row.put(
                    "losing_certificate_states",
                    "0");
        } else {
            row.put("certificate_states", "0");
            row.put("certificate_transitions", "0");
            row.put("worst_rank", "");
            row.put(
                    "losing_certificate_states",
                    Integer.toString(
                            result.losingCertificate()
                                    .losingStates()
                                    .size()));
        }

        if (execution.directStatistics != null) {
            DirectFullStrongSolver.Statistics direct =
                    execution.directStatistics;
            row.put(
                    "direct_full_enumerated_states",
                    Long.toString(direct.enumeratedStates()));
            row.put(
                    "direct_full_enabled_buckets",
                    Long.toString(direct.enabledActionBuckets()));
            row.put(
                    "direct_full_fixed_point_iterations",
                    Long.toString(
                            direct.fixedPointIterations()));
            row.put(
                    "direct_full_state_inspections",
                    Long.toString(
                            direct.fixedPointStateInspections()));
            row.put(
                    "direct_full_bucket_inspections",
                    Long.toString(
                            direct.fixedPointBucketInspections()));
            row.put(
                    "direct_full_outcome_inspections",
                    Long.toString(
                            direct.fixedPointOutcomeInspections()));
            row.put(
                    "direct_full_enumeration_time_ns",
                    Long.toString(
                            direct.enumerationNanoseconds()));
            row.put(
                    "direct_full_fixed_point_time_ns",
                    Long.toString(
                            direct.fixedPointNanoseconds()));
            row.put(
                    "direct_full_certificate_time_ns",
                    Long.toString(
                            direct.certificateNanoseconds()));
        }
    }

    private static Map<String, String> baseRow(
            Options options,
            SyntheticErFgProblemGenerator.GeneratedProblem generated,
            SeedSelection seed,
            Method method,
            int repetition,
            MethodOrder order,
            int position,
            long generationTime,
            ExecutionProvenance provenance) {
        Map<String, String> row =
                new LinkedHashMap<String, String>();
        for (String column : HEADER) {
            row.put(column, "");
        }
        row.put("schema_version", SCHEMA_VERSION);
        row.put(
                "run_id",
                SyntheticErFgProblemGenerator.sha256Hex(
                                RUN_ID_VERSION
                                        + "|"
                                        + options.panel
                                        + "|"
                                        + generated.modelHash()
                                        + "|"
                                        + method.id
                                        + "|"
                                        + repetition
                                        + "|reference="
                                        + options.referenceVerification
                                        + "|reference-states="
                                        + options.referenceStateLimit
                                        + "|reference-queries="
                                        + options.referenceQueryLimit
                                        + "|warmups="
                                        + options.warmups
                                        + "|guided-states="
                                        + (method == Method.GUIDED
                                                ? options.guidedStateLimit
                                                : 0)
                                        + "|guided-queries="
                                        + (method == Method.GUIDED
                                                ? options.guidedQueryLimit
                                                : 0)
                                        + "|method-order="
                                        + order.key
                                        + "|method-order-sequence="
                                        + methodSequence(
                                                order.methods)
                                        + "|generator="
                                        + SyntheticErFgProblemGenerator
                                                .GENERATOR_VERSION
                                        + "|artifact="
                                        + provenance
                                                .executionArtifactSha256
                                        + "|source-manifest="
                                        + provenance
                                                .sourceManifestSha256)
                        .substring(0, 24));
        row.put("timestamp_utc", Instant.now().toString());
        row.put("panel_id", options.panel);
        row.put("input_id", generated.inputId());
        row.put("topology", generated.topology().id());
        row.put(
                "component_count",
                Integer.toString(generated.componentCount()));
        row.put(
                "master_seed",
                Long.toString(generated.masterSeed()));
        row.put("seed_rank", Integer.toString(seed.rank));
        row.put("seed_selection_version", "sample-v1");
        row.put(
                "seed_universe",
                Integer.toString(options.seedUniverse));
        row.put(
                "panel_seed_count",
                Integer.toString(
                        options.explicitSeeds.isEmpty()
                                ? options.seedCount
                                : options.explicitSeeds.size()));
        row.put(
                "pilot_seed_count",
                Integer.toString(options.pilotSeedCount));
        row.put("u_profile", generated.profile().id());
        row.put("mutation", generated.mutation().id());
        row.put(
                "mutated_component",
                Integer.toString(generated.mutatedComponent()));
        row.put(
                "expected_decision",
                generated.expectedWinning()
                        ? "winning" : "losing");
        row.put("method", method.id);
        row.put("method_family", method.family);
        row.put("representation", method.representation);
        row.put("policy", method.policy);
        row.put(
                "controllable_order",
                method == Method.UPDATE_FIRST
                        ? "update_first"
                        : "endpoint_guided");
        row.put(
                "lazy_controllable_buckets",
                Boolean.toString(method != Method.EAGER_C
                        && method != Method.DIRECT_FULL));
        row.put(
                "guided_state_limit",
                method == Method.GUIDED
                        ? Integer.toString(
                                options.guidedStateLimit)
                        : "0");
        row.put(
                "guided_query_limit",
                method == Method.GUIDED
                        ? Integer.toString(
                                options.guidedQueryLimit)
                        : "0");
        row.put(
                "reference_enabled",
                Boolean.toString(
                        options.referenceVerification));
        row.put(
                "reference_state_limit",
                Long.toString(options.referenceStateLimit));
        row.put(
                "reference_query_limit",
                Long.toString(options.referenceQueryLimit));
        row.put("repetition", Integer.toString(repetition));
        row.put(
                "warmup_repetitions",
                Integer.toString(options.warmups));
        row.put(
                "method_order_version",
                METHOD_ORDER_VERSION);
        row.put("method_order_key", order.key);
        row.put(
                "method_order_rotation",
                Integer.toString(order.rotation));
        row.put(
                "method_order_direction",
                order.reverse ? "reverse" : "forward");
        row.put(
                "method_order_position",
                Integer.toString(position));
        row.put(
                "method_order_sequence",
                methodSequence(order.methods));
        row.put(
                "generation_time_ns",
                Long.toString(generationTime));
        row.put(
                "topology_edges",
                Integer.toString(generated.topologyEdges()));
        row.put(
                "old_requirements",
                Integer.toString(
                        generated.oldRequirementCount()));
        row.put(
                "new_requirements",
                Integer.toString(
                        generated.newRequirementCount()));
        row.put(
                "update_time_requirements",
                Integer.toString(
                        generated.updateRequirementCount()));
        row.put(
                "normal_actions",
                Integer.toString(
                        generated.normalActionCount()));
        row.put(
                "controllable_normal_actions",
                Integer.toString(
                        generated
                                .controllableNormalActionCount()));
        row.put(
                "uncontrollable_normal_actions",
                Integer.toString(
                        generated
                                .uncontrollableNormalActionCount()));
        row.put(
                "update_actions",
                Integer.toString(
                        generated.updateActionCount()));
        row.put(
                "precedence_edges",
                Integer.toString(
                        generated.precedenceEdgeCount()));
        row.put(
                "transfer_relation_edges",
                Long.toString(
                        generated.transferEdgeCount()));
        row.put(
                "model_hash_sha256",
                generated.modelHash());
        row.put(
                "generator_version",
                SyntheticErFgProblemGenerator
                        .GENERATOR_VERSION);
        row.put(
                "jvm_version",
                System.getProperty("java.version", ""));
        row.put(
                "java_vendor",
                System.getProperty("java.vendor", ""));
        row.put(
                "os_name",
                System.getProperty("os.name", ""));
        row.put(
                "os_arch",
                System.getProperty("os.arch", ""));
        row.put(
                "available_processors",
                Integer.toString(
                        Runtime.getRuntime()
                                .availableProcessors()));
        row.put("run_id_version", RUN_ID_VERSION);
        row.put(
                "benchmark_argv_json",
                provenance.benchmarkArgvJson);
        row.put(
                "benchmark_argv_sha256",
                provenance.benchmarkArgvSha256);
        row.put(
                "code_source_location",
                provenance.codeSourceLocation);
        row.put(
                "execution_artifact_kind",
                provenance.executionArtifactKind);
        row.put(
                "execution_artifact_path",
                provenance.executionArtifactPath);
        row.put(
                "execution_artifact_sha256",
                provenance.executionArtifactSha256);
        row.put(
                "execution_artifact_bytes",
                provenance.executionArtifactBytes);
        row.put(
                "execution_artifact_hash_status",
                provenance.executionArtifactHashStatus);
        row.put(
                "source_manifest_sha256",
                provenance.sourceManifestSha256);
        row.put(
                "jvm_max_memory_bytes",
                provenance.jvmMaxMemoryBytes);
        row.put(
                "outer_timeout_measurement_status",
                NOT_MEASURED_BY_DRIVER);
        row.put("outer_timeout_seconds", NOT_MEASURED);
        row.put(
                "peak_rss_measurement_status",
                NOT_MEASURED_BY_DRIVER);
        row.put("peak_rss_bytes", NOT_MEASURED);
        return row;
    }

    private static MethodOrder methodOrder(
            List<Method> selected,
            SyntheticErFgProblemGenerator.GeneratedProblem generated,
            int repetition) {
        String key = SyntheticErFgProblemGenerator.sha256Hex(
                METHOD_ORDER_VERSION
                        + "|"
                        + generated.modelHash()
                        + "|"
                        + repetition);
        int rotation =
                SyntheticErFgProblemGenerator.boundedHash(
                        generated.masterSeed(),
                        "method-rotation-"
                                + generated.modelHash()
                                + "-"
                                + repetition,
                        selected.size());
        boolean reverse =
                SyntheticErFgProblemGenerator.boundedHash(
                        generated.masterSeed(),
                        "method-direction-"
                                + generated.modelHash()
                                + "-"
                                + repetition,
                        2) == 1;
        List<Method> ordered =
                new ArrayList<Method>(selected);
        if (reverse) {
            Collections.reverse(ordered);
        }
        Collections.rotate(ordered, -rotation);
        return new MethodOrder(
                Collections.unmodifiableList(ordered),
                key.substring(0, 16),
                rotation,
                reverse);
    }

    private static List<SeedSelection> selectSeeds(
            Options options) {
        if (!options.explicitSeeds.isEmpty()) {
            List<SeedSelection> result =
                    new ArrayList<SeedSelection>();
            for (Long seed : options.explicitSeeds) {
                result.add(
                        new SeedSelection(
                                seed.longValue(), -1));
            }
            return result;
        }
        List<SeedCandidate> universe =
                new ArrayList<SeedCandidate>();
        for (int seed = 0;
                seed < options.seedUniverse;
                seed++) {
            universe.add(
                    new SeedCandidate(
                            seed,
                            SyntheticErFgProblemGenerator
                                    .sha256Hex(
                                            "sample-v1|"
                                                    + seed)));
        }
        Collections.sort(
                universe,
                new Comparator<SeedCandidate>() {
                    @Override
                    public int compare(
                            SeedCandidate left,
                            SeedCandidate right) {
                        int comparison =
                                left.hash.compareTo(right.hash);
                        return comparison != 0
                                ? comparison
                                : Long.compare(
                                        left.seed,
                                        right.seed);
                    }
                });
        int offset = "final".equals(options.panel)
                ? options.pilotSeedCount : 0;
        if (offset + options.seedCount > universe.size()) {
            throw new IllegalArgumentException(
                    "seed selection exceeds the configured universe");
        }
        List<SeedSelection> result =
                new ArrayList<SeedSelection>();
        for (int rank = offset;
                rank < offset + options.seedCount;
                rank++) {
            result.add(
                    new SeedSelection(
                            universe.get(rank).seed, rank));
        }
        return result;
    }

    private static void prepareOutput(
            Path output,
            boolean force) throws IOException {
        Path absolute = output.toAbsolutePath();
        Path parent = absolute.getParent();
        if (parent != null) {
            Files.createDirectories(parent);
        }
        if (Files.exists(absolute)) {
            if (!force) {
                throw new IllegalArgumentException(
                        "output already exists; pass --force to replace it: "
                                + absolute);
            }
            Files.delete(absolute);
        }
    }

    private static void writeMapRow(
            BufferedWriter writer,
            Map<String, String> row) throws IOException {
        List<String> values =
                new ArrayList<String>(HEADER.size());
        for (String column : HEADER) {
            values.add(row.get(column));
        }
        writeCsvRow(writer, values);
    }

    private static void writeCsvRow(
            BufferedWriter writer,
            List<String> values) throws IOException {
        for (int index = 0; index < values.size(); index++) {
            if (index > 0) {
                writer.write(',');
            }
            writer.write(csv(values.get(index)));
        }
        writer.newLine();
    }

    private static String csv(String raw) {
        String value = raw == null ? "" : raw;
        boolean quote = value.indexOf(',') >= 0
                || value.indexOf('"') >= 0
                || value.indexOf('\n') >= 0
                || value.indexOf('\r') >= 0;
        if (!quote) {
            return value;
        }
        return "\"" + value.replace("\"", "\"\"") + "\"";
    }

    private static String jsonArray(String[] values) {
        StringBuilder result = new StringBuilder();
        result.append('[');
        for (int index = 0; index < values.length; index++) {
            if (index > 0) {
                result.append(',');
            }
            appendJsonString(result, values[index]);
        }
        result.append(']');
        return result.toString();
    }

    private static void appendJsonString(
            StringBuilder result,
            String value) {
        result.append('"');
        for (int index = 0; index < value.length(); index++) {
            char character = value.charAt(index);
            switch (character) {
                case '"':
                    result.append("\\\"");
                    break;
                case '\\':
                    result.append("\\\\");
                    break;
                case '\b':
                    result.append("\\b");
                    break;
                case '\f':
                    result.append("\\f");
                    break;
                case '\n':
                    result.append("\\n");
                    break;
                case '\r':
                    result.append("\\r");
                    break;
                case '\t':
                    result.append("\\t");
                    break;
                default:
                    if (character < 0x20) {
                        result.append("\\u");
                        String hexadecimal =
                                Integer.toHexString(character);
                        for (int padding =
                                hexadecimal.length();
                                padding < 4;
                                padding++) {
                            result.append('0');
                        }
                        result.append(hexadecimal);
                    } else {
                        result.append(character);
                    }
            }
        }
        result.append('"');
    }

    private static String sha256Hex(Path path)
            throws IOException {
        MessageDigest digest;
        try {
            digest = MessageDigest.getInstance("SHA-256");
        } catch (NoSuchAlgorithmException impossible) {
            throw new IllegalStateException(
                    "JVM does not provide SHA-256", impossible);
        }
        byte[] buffer = new byte[64 * 1024];
        try (InputStream stream = Files.newInputStream(path)) {
            int count;
            while ((count = stream.read(buffer)) >= 0) {
                if (count > 0) {
                    digest.update(buffer, 0, count);
                }
            }
        }
        StringBuilder result =
                new StringBuilder(digest.getDigestLength() * 2);
        for (byte item : digest.digest()) {
            result.append(
                    String.format(
                            Locale.ROOT, "%02x", item & 0xff));
        }
        return result.toString();
    }

    private static String methodSequence(List<Method> methods) {
        List<String> values = new ArrayList<String>();
        for (Method method : methods) {
            values.add(method.id);
        }
        return join(values, ">");
    }

    private static String join(
            Iterable<?> values,
            String separator) {
        StringBuilder result = new StringBuilder();
        for (Object value : values) {
            if (result.length() > 0) {
                result.append(separator);
            }
            result.append(value);
        }
        return result.toString();
    }

    private static void printUsage() {
        System.out.println(
                "Usage: Fse2027SyntheticBenchmark [options]\n"
                + "  --output PATH                  CSV output (default synthetic-erfg-results.csv)\n"
                + "  --panel pilot|final|custom    disjoint seed panel label (default pilot)\n"
                + "  --seed-count N                hashed seeds selected for pilot/final (default 1)\n"
                + "  --pilot-seed-count N          final-panel offset (default 4)\n"
                + "  --seed-universe N             candidate IDs 0..N-1 (default 10000)\n"
                + "  --seeds ID,ID                 explicit custom master seeds\n"
                + "  --sizes N,N                   component counts (default 2)\n"
                + "  --topologies pipeline,ring,hub\n"
                + "  --profiles u0,u_local,u_cross\n"
                + "  --mutations base,empty_transfer,reject_uncontrollable,uncontrollable_livelock\n"
                + "  --methods fg_otf,eager_c,guided,update_first,direct_full\n"
                + "  --method-order-methods LIST    full order universe for forked subset runs\n"
                + "  --repetitions N               measured repetitions (default 1)\n"
                + "  --warmups N                   unrecorded warm-ups per method/input (default 0)\n"
                + "  --guided-state-limit N        guided wrapper state cap (default 50000)\n"
                + "  --guided-query-limit N        guided wrapper query cap (default 100000)\n"
                + "  --reference-state-limit N     exhaustive checker cap (default 200000)\n"
                + "  --reference-query-limit N     exhaustive checker cap (default 2000000)\n"
                + "  --reference true|false        run independent checker (default true)\n"
                + "  --source-manifest-sha256 HEX  SHA-256 of the source/replication manifest\n"
                + "  --force                       replace an existing output\n"
                + "  --help");
    }

    private enum Method {
        FG_OTF(
                "fg_otf",
                "proposed",
                "direct",
                "interleaved_lazy"),
        EAGER_C(
                "eager_c",
                "ablation",
                "direct",
                "interleaved_eager_controllable"),
        GUIDED(
                "guided",
                "production",
                "direct",
                "guided_then_interleaved_lazy"),
        UPDATE_FIRST(
                "update_first",
                "ablation",
                "direct",
                "interleaved_lazy"),
        DIRECT_FULL(
                "direct_full",
                "baseline",
                "direct",
                "exhaustive_then_fixed_point");

        private final String id;
        private final String family;
        private final String representation;
        private final String policy;

        Method(
                String id,
                String family,
                String representation,
                String policy) {
            this.id = id;
            this.family = family;
            this.representation = representation;
            this.policy = policy;
        }

        private static Method parse(String text) {
            String normalized =
                    text.trim().toLowerCase(Locale.ROOT);
            for (Method method : values()) {
                if (method.id.equals(normalized)) {
                    return method;
                }
            }
            throw new IllegalArgumentException(
                    "Unknown method: " + text);
        }
    }

    private static final class ExecutionProvenance {
        private final String benchmarkArgvJson;
        private final String benchmarkArgvSha256;
        private final String codeSourceLocation;
        private final String executionArtifactKind;
        private final String executionArtifactPath;
        private final String executionArtifactSha256;
        private final String executionArtifactBytes;
        private final String executionArtifactHashStatus;
        private final String sourceManifestSha256;
        private final String jvmMaxMemoryBytes;

        private ExecutionProvenance(
                String benchmarkArgvJson,
                String benchmarkArgvSha256,
                String codeSourceLocation,
                String executionArtifactKind,
                String executionArtifactPath,
                String executionArtifactSha256,
                String executionArtifactBytes,
                String executionArtifactHashStatus,
                String sourceManifestSha256,
                String jvmMaxMemoryBytes) {
            this.benchmarkArgvJson = benchmarkArgvJson;
            this.benchmarkArgvSha256 = benchmarkArgvSha256;
            this.codeSourceLocation = codeSourceLocation;
            this.executionArtifactKind = executionArtifactKind;
            this.executionArtifactPath = executionArtifactPath;
            this.executionArtifactSha256 =
                    executionArtifactSha256;
            this.executionArtifactBytes =
                    executionArtifactBytes;
            this.executionArtifactHashStatus =
                    executionArtifactHashStatus;
            this.sourceManifestSha256 =
                    sourceManifestSha256;
            this.jvmMaxMemoryBytes = jvmMaxMemoryBytes;
        }

        private static ExecutionProvenance capture(
                String[] arguments,
                String sourceManifestSha256) {
            String argvJson = jsonArray(arguments);
            String locationText = "unknown";
            String artifactKind = "unknown";
            String artifactPath = "unknown";
            String artifactSha256 = "unknown";
            String artifactBytes = "unknown";
            String hashStatus = "code_source_unavailable";
            try {
                CodeSource codeSource =
                        Fse2027SyntheticBenchmark.class
                                .getProtectionDomain()
                                .getCodeSource();
                if (codeSource != null
                        && codeSource.getLocation() != null) {
                    locationText =
                            codeSource.getLocation()
                                    .toExternalForm();
                    if ("file".equalsIgnoreCase(
                            codeSource.getLocation()
                                    .getProtocol())) {
                        Path path = Paths.get(
                                        codeSource.getLocation()
                                                .toURI())
                                .toAbsolutePath()
                                .normalize();
                        artifactPath = path.toString();
                        if (Files.isRegularFile(path)) {
                            artifactKind =
                                    path.getFileName()
                                                    .toString()
                                                    .toLowerCase(
                                                            Locale.ROOT)
                                                    .endsWith(".jar")
                                            ? "jar"
                                            : "regular_file";
                            artifactBytes =
                                    Long.toString(
                                            Files.size(path));
                            artifactSha256 =
                                    sha256Hex(path);
                            hashStatus = "recorded";
                        } else if (Files.isDirectory(path)) {
                            artifactKind =
                                    "classes_directory";
                            hashStatus =
                                    "not_a_regular_file";
                        } else {
                            artifactKind =
                                    "missing_file_code_source";
                            hashStatus =
                                    "not_a_regular_file";
                        }
                    } else {
                        artifactKind =
                                "non_file_code_source";
                        hashStatus =
                                "non_file_code_source";
                    }
                }
            } catch (Exception unavailable) {
                hashStatus =
                        "unavailable_"
                                + unavailable.getClass()
                                        .getSimpleName();
            }
            return new ExecutionProvenance(
                    argvJson,
                    SyntheticErFgProblemGenerator
                            .sha256Hex(argvJson),
                    locationText,
                    artifactKind,
                    artifactPath,
                    artifactSha256,
                    artifactBytes,
                    hashStatus,
                    sourceManifestSha256,
                    Long.toString(
                            Runtime.getRuntime()
                                    .maxMemory()));
        }
    }

    private static final class Execution {
        private final OtfDucsResult<
                CanonicalUpdateConfiguration<String, String>,
                String,
                GoalSignature<String, String>> result;
        private final DirectFullStrongSolver.Statistics
                directStatistics;
        private final OtfDucsCertificateChecker.VerificationReport
                certificateVerification;
        private final IndependentExplicitStrongSolver.VerificationReport
                referenceVerification;
        private final Throwable referenceFailure;
        private final long solverTime;
        private final long certificateTime;
        private final long referenceTime;
        private final boolean referenceRequested;

        private Execution(
                OtfDucsResult<
                        CanonicalUpdateConfiguration<String, String>,
                        String,
                        GoalSignature<String, String>> result,
                DirectFullStrongSolver.Statistics directStatistics,
                OtfDucsCertificateChecker.VerificationReport
                        certificateVerification,
                IndependentExplicitStrongSolver.VerificationReport
                        referenceVerification,
                Throwable referenceFailure,
                long solverTime,
                long certificateTime,
                long referenceTime,
                boolean referenceRequested) {
            this.result = result;
            this.directStatistics = directStatistics;
            this.certificateVerification =
                    certificateVerification;
            this.referenceVerification =
                    referenceVerification;
            this.referenceFailure = referenceFailure;
            this.solverTime = solverTime;
            this.certificateTime = certificateTime;
            this.referenceTime = referenceTime;
            this.referenceRequested = referenceRequested;
        }
    }

    private static final class MethodOrder {
        private final List<Method> methods;
        private final String key;
        private final int rotation;
        private final boolean reverse;

        private MethodOrder(
                List<Method> methods,
                String key,
                int rotation,
                boolean reverse) {
            this.methods = methods;
            this.key = key;
            this.rotation = rotation;
            this.reverse = reverse;
        }
    }

    private static final class SeedCandidate {
        private final long seed;
        private final String hash;

        private SeedCandidate(long seed, String hash) {
            this.seed = seed;
            this.hash = hash;
        }
    }

    private static final class SeedSelection {
        private final long seed;
        private final int rank;

        private SeedSelection(long seed, int rank) {
            this.seed = seed;
            this.rank = rank;
        }
    }

    private static final class Options {
        private Path output = Paths.get(
                "synthetic-erfg-results.csv");
        private String panel = "pilot";
        private int seedCount = 1;
        private int pilotSeedCount = 4;
        private int seedUniverse = 10_000;
        private final List<Long> explicitSeeds =
                new ArrayList<Long>();
        private List<Integer> sizes =
                new ArrayList<Integer>(
                        Collections.singletonList(
                                Integer.valueOf(2)));
        private List<SyntheticErFgProblemGenerator.Topology>
                topologies =
                new ArrayList<
                        SyntheticErFgProblemGenerator.Topology>(
                        Arrays.asList(
                                SyntheticErFgProblemGenerator
                                        .Topology.values()));
        private List<SyntheticErFgProblemGenerator.UProfile>
                profiles =
                new ArrayList<
                        SyntheticErFgProblemGenerator.UProfile>(
                        Arrays.asList(
                                SyntheticErFgProblemGenerator
                                        .UProfile.values()));
        private List<SyntheticErFgProblemGenerator.Mutation>
                mutations =
                new ArrayList<
                        SyntheticErFgProblemGenerator.Mutation>(
                        Arrays.asList(
                                SyntheticErFgProblemGenerator
                                        .Mutation.values()));
        private List<Method> methods =
                new ArrayList<Method>(
                        Arrays.asList(Method.values()));
        private List<Method> methodOrderMethods;
        private int repetitions = 1;
        private int warmups = 0;
        private int guidedStateLimit = 50_000;
        private int guidedQueryLimit = 100_000;
        private long referenceStateLimit = 200_000L;
        private long referenceQueryLimit = 2_000_000L;
        private boolean referenceVerification = true;
        private String sourceManifestSha256 = "unknown";
        private boolean force;
        private boolean help;

        private static Options parse(String[] arguments) {
            Options result = new Options();
            for (int index = 0;
                    index < arguments.length;
                    index++) {
                String option = arguments[index];
                if ("--force".equals(option)) {
                    result.force = true;
                    continue;
                }
                if ("--help".equals(option)
                        || "-h".equals(option)) {
                    result.help = true;
                    continue;
                }
                if (!option.startsWith("--")) {
                    throw new IllegalArgumentException(
                            "Unknown positional argument: "
                                    + option);
                }
                if (index + 1 >= arguments.length) {
                    throw new IllegalArgumentException(
                            "Missing value for " + option);
                }
                String value = arguments[++index];
                if ("--output".equals(option)) {
                    result.output = Paths.get(value);
                } else if ("--panel".equals(option)) {
                    result.panel =
                            value.trim().toLowerCase(
                                    Locale.ROOT);
                } else if ("--seed-count".equals(option)) {
                    result.seedCount =
                            parsePositiveInt(option, value);
                } else if ("--pilot-seed-count".equals(option)) {
                    result.pilotSeedCount =
                            parseNonnegativeInt(option, value);
                } else if ("--seed-universe".equals(option)) {
                    result.seedUniverse =
                            parsePositiveInt(option, value);
                } else if ("--seeds".equals(option)) {
                    result.explicitSeeds.clear();
                    for (String item : split(value)) {
                        result.explicitSeeds.add(
                                Long.valueOf(
                                        Long.parseLong(item)));
                    }
                    result.panel = "custom";
                } else if ("--sizes".equals(option)) {
                    result.sizes =
                            new ArrayList<Integer>();
                    for (String item : split(value)) {
                        result.sizes.add(
                                Integer.valueOf(
                                        parsePositiveInt(
                                                option, item)));
                    }
                } else if ("--topologies".equals(option)) {
                    result.topologies =
                            parseTopologies(value);
                } else if ("--profiles".equals(option)) {
                    result.profiles = parseProfiles(value);
                } else if ("--mutations".equals(option)) {
                    result.mutations = parseMutations(value);
                } else if ("--methods".equals(option)) {
                    result.methods = parseMethods(value);
                } else if ("--method-order-methods".equals(option)) {
                    result.methodOrderMethods =
                            parseMethods(value);
                } else if ("--repetitions".equals(option)) {
                    result.repetitions =
                            parsePositiveInt(option, value);
                } else if ("--warmups".equals(option)) {
                    result.warmups =
                            parseNonnegativeInt(option, value);
                } else if ("--guided-state-limit".equals(option)) {
                    result.guidedStateLimit =
                            parsePositiveInt(option, value);
                } else if ("--guided-query-limit".equals(option)) {
                    result.guidedQueryLimit =
                            parsePositiveInt(option, value);
                } else if ("--reference-state-limit".equals(option)) {
                    result.referenceStateLimit =
                            parsePositiveLong(option, value);
                } else if ("--reference-query-limit".equals(option)) {
                    result.referenceQueryLimit =
                            parsePositiveLong(option, value);
                } else if ("--reference".equals(option)) {
                    result.referenceVerification =
                            parseBoolean(option, value);
                } else if ("--source-manifest-sha256"
                        .equals(option)) {
                    result.sourceManifestSha256 =
                            parseSha256(option, value);
                } else {
                    throw new IllegalArgumentException(
                            "Unknown option: " + option);
                }
            }
            return result;
        }

        private void validate() {
            if (!Arrays.asList("pilot", "final", "custom")
                    .contains(panel)) {
                throw new IllegalArgumentException(
                        "--panel must be pilot, final, or custom");
            }
            if ("custom".equals(panel)
                    && explicitSeeds.isEmpty()) {
                throw new IllegalArgumentException(
                        "custom panel requires --seeds");
            }
            for (Integer size : sizes) {
                if (size.intValue() < 2) {
                    throw new IllegalArgumentException(
                            "every size must be at least 2");
                }
            }
            requireNonempty(sizes, "sizes");
            requireNonempty(topologies, "topologies");
            requireNonempty(profiles, "profiles");
            requireNonempty(mutations, "mutations");
            requireNonempty(methods, "methods");
            if (!methodOrderMethods().containsAll(methods)) {
                throw new IllegalArgumentException(
                        "--method-order-methods must contain every "
                                + "executed --methods entry");
            }
        }

        private List<Method> methodOrderMethods() {
            return methodOrderMethods == null
                    ? methods : methodOrderMethods;
        }

        private static List<
                SyntheticErFgProblemGenerator.Topology>
                parseTopologies(String value) {
            Set<SyntheticErFgProblemGenerator.Topology> selected =
                    EnumSet.noneOf(
                            SyntheticErFgProblemGenerator
                                    .Topology.class);
            for (String item : split(value)) {
                selected.add(
                        SyntheticErFgProblemGenerator
                                .Topology.parse(item));
            }
            List<SyntheticErFgProblemGenerator.Topology> result =
                    new ArrayList<
                            SyntheticErFgProblemGenerator.Topology>();
            for (SyntheticErFgProblemGenerator.Topology candidate
                    : SyntheticErFgProblemGenerator.Topology
                            .values()) {
                if (selected.contains(candidate)) {
                    result.add(candidate);
                }
            }
            return result;
        }

        private static List<
                SyntheticErFgProblemGenerator.UProfile>
                parseProfiles(String value) {
            Set<SyntheticErFgProblemGenerator.UProfile> selected =
                    EnumSet.noneOf(
                            SyntheticErFgProblemGenerator
                                    .UProfile.class);
            for (String item : split(value)) {
                selected.add(
                        SyntheticErFgProblemGenerator
                                .UProfile.parse(item));
            }
            List<SyntheticErFgProblemGenerator.UProfile> result =
                    new ArrayList<
                            SyntheticErFgProblemGenerator.UProfile>();
            for (SyntheticErFgProblemGenerator.UProfile candidate
                    : SyntheticErFgProblemGenerator.UProfile
                            .values()) {
                if (selected.contains(candidate)) {
                    result.add(candidate);
                }
            }
            return result;
        }

        private static List<
                SyntheticErFgProblemGenerator.Mutation>
                parseMutations(String value) {
            Set<SyntheticErFgProblemGenerator.Mutation> selected =
                    EnumSet.noneOf(
                            SyntheticErFgProblemGenerator
                                    .Mutation.class);
            for (String item : split(value)) {
                selected.add(
                        SyntheticErFgProblemGenerator
                                .Mutation.parse(item));
            }
            List<SyntheticErFgProblemGenerator.Mutation> result =
                    new ArrayList<
                            SyntheticErFgProblemGenerator.Mutation>();
            for (SyntheticErFgProblemGenerator.Mutation candidate
                    : SyntheticErFgProblemGenerator.Mutation
                            .values()) {
                if (selected.contains(candidate)) {
                    result.add(candidate);
                }
            }
            return result;
        }

        private static List<Method> parseMethods(
                String value) {
            Set<Method> selected =
                    EnumSet.noneOf(Method.class);
            for (String item : split(value)) {
                selected.add(Method.parse(item));
            }
            List<Method> result =
                    new ArrayList<Method>();
            for (Method candidate : Method.values()) {
                if (selected.contains(candidate)) {
                    result.add(candidate);
                }
            }
            return result;
        }

        private static List<String> split(String value) {
            List<String> result = new ArrayList<String>();
            for (String item : value.split(",")) {
                String trimmed = item.trim();
                if (!trimmed.isEmpty()) {
                    result.add(trimmed);
                }
            }
            if (result.isEmpty()) {
                throw new IllegalArgumentException(
                        "comma-separated option must not be empty");
            }
            return result;
        }

        private static int parsePositiveInt(
                String option,
                String value) {
            int parsed = Integer.parseInt(value);
            if (parsed < 1) {
                throw new IllegalArgumentException(
                        option + " must be positive");
            }
            return parsed;
        }

        private static int parseNonnegativeInt(
                String option,
                String value) {
            int parsed = Integer.parseInt(value);
            if (parsed < 0) {
                throw new IllegalArgumentException(
                        option + " must be nonnegative");
            }
            return parsed;
        }

        private static long parsePositiveLong(
                String option,
                String value) {
            long parsed = Long.parseLong(value);
            if (parsed < 1L) {
                throw new IllegalArgumentException(
                        option + " must be positive");
            }
            return parsed;
        }

        private static boolean parseBoolean(
                String option,
                String value) {
            if ("true".equalsIgnoreCase(value)) {
                return true;
            }
            if ("false".equalsIgnoreCase(value)) {
                return false;
            }
            throw new IllegalArgumentException(
                    option + " must be true or false");
        }

        private static String parseSha256(
                String option,
                String value) {
            String normalized =
                    value.trim().toLowerCase(Locale.ROOT);
            if (!normalized.matches("[0-9a-f]{64}")) {
                throw new IllegalArgumentException(
                        option
                                + " must be exactly 64 hexadecimal characters");
            }
            return normalized;
        }

        private static void requireNonempty(
                List<?> values,
                String label) {
            if (values.isEmpty()) {
                throw new IllegalArgumentException(
                        label + " must not be empty");
            }
        }
    }
}
