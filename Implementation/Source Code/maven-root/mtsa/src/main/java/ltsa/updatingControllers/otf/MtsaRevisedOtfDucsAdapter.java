package ltsa.updatingControllers.otf;

import MTSTools.ac.ic.doc.mtstools.model.MTS;
import MTSTools.ac.ic.doc.mtstools.model.impl.LTSAdapter;
import ltsa.lts.CompactState;
import ltsa.lts.Declaration;
import ltsa.lts.EventState;
import ltsa.lts.LTSOutput;
import ltsa.updatingControllers.EvaluationProfiler;
import ltsa.updatingControllers.UpdateConstants;
import ltsa.updatingControllers.UpdatingControllerEvaluationRecorder;
import ltsa.updatingControllers.UpdatingControllerEvaluationRecorder.SolverStatus;
import ltsa.updatingControllers.UpdatingControllerEvaluationRecorder.VerificationStatus;
import ltsa.updatingControllers.structures.UpdateProtocolSpec;
import ltsa.updatingControllers.structures.UpdatingControllerCompositeState;

import java.lang.management.ManagementFactory;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.Comparator;
import java.util.Deque;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.Vector;

/**
 * Compiles the existing MTSA updating-controller input into the revised
 * canonical OTF-DUCS problem and exports its checked atomic Link back to the
 * representation consumed by the GUI.
 *
 * <p>This adapter is used only for the explicit {@code revised_on_the_fly}
 * mode.  The legacy {@code on_the_fly} implementation remains available for
 * reproducibility.  Component relations are consumed as direct, set-valued
 * transfer relations; phase/action sequences in a relation are rejected.</p>
 */
public final class MtsaRevisedOtfDucsAdapter {

    private static final long ERROR_STATE = Declaration.ERROR;
    private static final int DEFAULT_PHYSICAL_CLOSURE_LIMIT = 2_000_000;
    private static final long DEFAULT_REFERENCE_STATE_LIMIT = 500_000L;
    private static final long DEFAULT_REFERENCE_QUERY_LIMIT = 5_000_000L;
    private static final ThreadLocal<Outcome> LAST_OUTCOME =
            new ThreadLocal<Outcome>();

    private MtsaRevisedOtfDucsAdapter() {
        // Utility class.
    }

    /** Clears the per-thread typed result retained for headless bundle export. */
    public static void clearLastOutcomeForCurrentThread() {
        LAST_OUTCOME.remove();
    }

    /** Returns the most recent revised result produced by this compiler thread. */
    public static Outcome lastOutcomeForCurrentThread() {
        return LAST_OUTCOME.get();
    }

    /**
     * Runs revised OTF-DUCS and installs a checked linked controller in
     * {@code source}. A verified losing result deliberately leaves the
     * composition unset, matching the normal MTSA "not controllable" outcome.
     * The built-in certificate checker shares this adapter's successor
     * semantics; independent verification is reported separately.
     */
    public static Outcome synthesizeAndInstall(
            UpdatingControllerCompositeState source,
            LTSOutput output) {
        Objects.requireNonNull(source, "source");
        Objects.requireNonNull(output, "output");
        if (!source.isRevisedOnTheFly()) {
            throw new IllegalArgumentException(
                    "The revised adapter requires the revised_on_the_fly mode");
        }
        if (!source.isOTF() || !source.isFineGrained()) {
            throw new IllegalArgumentException(
                    "revised_on_the_fly requires on-the-fly fine-grained input");
        }
        if (source.getUpdateProtocolSpec() == null
                || source.getUpdateProtocolSpec().isSelective()) {
            throw new IllegalArgumentException(
                    "Revised OTF-DUCS requires non-selective fine-grained update events");
        }
        if (source.hasTransferRelationActionSequences()) {
            throw new IllegalArgumentException(
                    "Revised OTF-DUCS relations must define direct g_i edges; "
                            + "pre/post actions around reconfigure are unsupported");
        }

        output.outln("=========================================");
        output.outln("Mode: Revised OTF-DUCS (proof-producing strong synthesis)");
        output.outln("=========================================");

        String solverMode = configuredSolverMode();
        FineGrainedSuccessorOracle.ControllableActionOrder actionOrder =
                FineGrainedSuccessorOracle.ControllableActionOrder.configured();
        UpdatePolicyRestriction.Mode policyRestrictionMode =
                UpdatePolicyRestriction.Mode.configured();
        recordExecutionIdentity(
                source, actionOrder, solverMode, policyRestrictionMode);
        long preparationStart = System.nanoTime();
        PreparedInput prepared;
        try {
            prepared = prepare(source);
            EndpointContractValidator.validate(
                    prepared.oldEndpoint,
                    prepared.newEndpoint,
                    prepared.problem,
                    EndpointState::oldSnapshot,
                    state -> state.newSignature(prepared.newEndpointIds.get(state)));
        }
        catch (IllegalArgumentException invalidInput) {
            UpdatingControllerEvaluationRecorder.recordSolverOutcome(
                    SolverStatus.INVALID_INPUT,
                    VerificationStatus.UNVERIFIED);
            metric("revised_input_contract_status",
                    "Revised Correctness",
                    "FG-DUCS input contract status",
                    "invalid", "text");
            metric("revised_input_contract_reason",
                    "Revised Correctness",
                    "FG-DUCS input contract reason",
                    invalidInput.getMessage(), "text");
            output.outln("Revised OTF-DUCS input: INVALID ("
                    + invalidInput.getMessage() + ")");
            throw invalidInput;
        }
        metric("revised_input_contract_status",
                "Revised Correctness",
                "FG-DUCS input contract status",
                "valid", "text");
        long preparationNanos = System.nanoTime() - preparationStart;
        recordPreparedInput(prepared, preparationNanos);
        UpdatePolicyRestriction<LocalState, Long> policyRestriction =
                new UpdatePolicyRestriction<LocalState, Long>(
                        prepared.problem, policyRestrictionMode);
        recordPolicyRestriction(policyRestriction);
        output.outln(" - Components: " + prepared.problem.components().size());
        output.outln(" - Requirements: old=" + prepared.problem.oldRequirementIds().size()
                + ", new=" + prepared.problem.newRequirementIds().size()
                + ", update-time=" + prepared.problem.updateRequirementIds().size());
        output.outln(" - Initial endpoint embeddings: "
                + prepared.problem.initialConfigurations().size());
        output.outln(" - Loadable new endpoint signatures: "
                + prepared.problem.goalSignatures().size()
                + " / " + prepared.newEndpoint.reachableStates().size());
        output.outln(" - Controllable action order: "
                + ("generic_lazy".equals(solverMode)
                        ? "ignored_not_applicable"
                        : actionOrder.propertyValue()));
        output.outln(" - Solver implementation: " + solverMode);
        output.outln(" - Update-policy restriction: "
                + policyRestriction.id()
                + " (" + policyRestriction.interpretation() + ")");

        long synthesisStart = System.nanoTime();
        OtfDucsResult<CanonicalUpdateConfiguration<LocalState, Long>, String,
                GoalSignature<LocalState, Long>> result;
        DirectFullStrongSolver.Statistics directFullStatistics = null;
        FineGrainedSuccessorOracle<LocalState, Long> baseGame =
                FineGrainedOtfDucs.game(
                        prepared.problem, actionOrder);
        RestrictedFineGrainedGame<LocalState, Long> game =
                new RestrictedFineGrainedGame<LocalState, Long>(
                        baseGame, policyRestriction);
        if ("direct_full".equals(solverMode)) {
            DirectFullStrongSolver<
                    CanonicalUpdateConfiguration<LocalState, Long>,
                    String,
                    GoalSignature<LocalState, Long>> directFull =
                    new DirectFullStrongSolver<
                            CanonicalUpdateConfiguration<LocalState, Long>,
                            String,
                            GoalSignature<LocalState, Long>>(game);
            result = directFull.synthesize();
            new OtfDucsCertificateChecker<
                    CanonicalUpdateConfiguration<LocalState, Long>,
                    String,
                    GoalSignature<LocalState, Long>>(game)
                    .verify(result)
                    .throwIfInvalid();
            directFullStatistics = directFull.statistics();
        } else if ("generic_lazy".equals(solverMode)) {
            result = new GenericLazyStrongSolver<
                    CanonicalUpdateConfiguration<LocalState, Long>,
                    String,
                    GoalSignature<LocalState, Long>>(game)
                    .synthesize();
            new OtfDucsCertificateChecker<
                    CanonicalUpdateConfiguration<LocalState, Long>,
                    String,
                    GoalSignature<LocalState, Long>>(game)
                    .verify(result)
                    .throwIfInvalid();
        } else {
            result = new OtfDucsSynthesizer<
                    CanonicalUpdateConfiguration<LocalState, Long>,
                    String,
                    GoalSignature<LocalState, Long>>(game)
                    .synthesize();
            new OtfDucsCertificateChecker<
                    CanonicalUpdateConfiguration<LocalState, Long>,
                    String,
                    GoalSignature<LocalState, Long>>(game)
                    .verify(result)
                    .throwIfInvalid();
        }
        long synthesisNanos = System.nanoTime() - synthesisStart;
        UpdatingControllerEvaluationRecorder.recordSolverOutcome(
                result.isWinning() ? SolverStatus.REALIZABLE : SolverStatus.UNREALIZABLE,
                VerificationStatus.UNVERIFIED);
        recordDecisionMetrics(result, synthesisNanos, solverMode);
        if (directFullStatistics != null) {
            recordDirectFullMetrics(directFullStatistics);
        }
        IndependentExplicitStrongSolver.VerificationReport independent =
                runIndependentVerification(
                        prepared.problem,
                        policyRestriction,
                        result,
                        output);

        if (!result.isWinning()) {
            source.setComposition(null);
            source.recordRevisedOtfDucsResult(result, null);
            output.outln("Revised OTF-DUCS result: NO STRONG SOLUTION");
            output.outln(" - Internal losing-region certificate states: "
                    + result.losingCertificate().losingStates().size());
            output.outln(" - Internal certificate checker "
                    + "(same successor semantics): passed");
            printStatistics(result, output);
            recordLosingCertificate(result);
            recordEvaluationCompleteness(independent);
            Outcome outcome = new Outcome(prepared, result, null);
            source.recordRevisedOtfDucsOutcome(outcome);
            LAST_OUTCOME.set(outcome);
            return outcome;
        }

        long linkStart = System.nanoTime();
        LinkedOtfDucsController<EndpointState, LocalState, Long, EndpointState> linked =
                LinkedOtfDucsController.link(
                        prepared.oldEndpoint,
                        prepared.newEndpoint,
                        prepared.problem,
                        result,
                        EndpointState::oldSnapshot,
                        state -> state.newSignature(prepared.newEndpointIds.get(state)));

        CompactState controller = linked.toMtsa().toCompactState(source.getName());
        long linkNanos = System.nanoTime() - linkStart;
        source.setComposition(controller);
        source.setControllableActions(linked.controllableActions());
        source.recordRevisedOtfDucsResult(result, linked);

        int maximumRank = 0;
        for (Integer rank : result.winningCertificate().ranks().values()) {
            maximumRank = Math.max(maximumRank, rank.intValue());
        }
        output.outln("Revised OTF-DUCS result: WINNING");
        output.outln(" - Certificate states: "
                + result.winningCertificate().ranks().size());
        output.outln(" - Worst completion rank: " + maximumRank);
        output.outln(" - Atomic Link states: " + controller.maxStates);
        output.outln(" - Internal certificate checker "
                + "(same successor semantics): passed");
        output.outln(" - Atomic Link checker: passed");
        printStatistics(result, output);
        recordWinningCertificate(
                prepared.problem, result, controller, linkNanos);
        recordEvaluationCompleteness(independent);
        Outcome outcome = new Outcome(prepared, result, linked);
        source.recordRevisedOtfDucsOutcome(outcome);
        LAST_OUTCOME.set(outcome);
        return outcome;
    }

    private static IndependentExplicitStrongSolver.VerificationReport
            runIndependentVerification(
                    FineGrainedUpdateProblem<LocalState, Long> problem,
                    UpdatePolicyRestriction<LocalState, Long> restriction,
                    OtfDucsResult<
                            CanonicalUpdateConfiguration<LocalState, Long>,
                            String,
                            GoalSignature<LocalState, Long>> result,
                    LTSOutput output) {
        boolean enabled = Boolean.parseBoolean(System.getProperty(
                "mtsa.revised.otf.independentVerification", "false"));
        if (!enabled) {
            output.outln(" - Independent explicit verification: not run "
                    + "(enable with "
                    + "-Dmtsa.revised.otf.independentVerification=true)");
            metric("revised_independent_verification_status",
                    "Revised Correctness",
                    "Independent explicit verification status",
                    "not_run", "text");
            return null;
        }

        long stateLimit = positiveLongProperty(
                "mtsa.revised.otf.independentStateLimit",
                DEFAULT_REFERENCE_STATE_LIMIT);
        long queryLimit = positiveLongProperty(
                "mtsa.revised.otf.independentQueryLimit",
                DEFAULT_REFERENCE_QUERY_LIMIT);
        String verificationMode = System.getProperty(
                "mtsa.revised.otf.independentVerificationMode",
                "exhaustive").trim().toLowerCase(java.util.Locale.ROOT);
        IndependentExplicitStrongSolver<LocalState, Long> verifier =
                new IndependentExplicitStrongSolver<LocalState, Long>(
                        problem, restriction, stateLimit, queryLimit);
        IndependentExplicitStrongSolver.VerificationReport report;
        if ("exhaustive".equals(verificationMode)) {
            report = verifier.verify(result);
        } else if ("certificate".equals(verificationMode)) {
            report = verifier.verifyCertificate(result);
        } else {
            throw new IllegalArgumentException(
                    "mtsa.revised.otf.independentVerificationMode must be "
                            + "exhaustive or certificate");
        }
        metric("revised_independent_verification_states",
                "Revised Correctness",
                "Independent verification states checked",
                report.states(), "states");
        metric("revised_independent_verification_queries",
                "Revised Correctness",
                "Independent verification successor queries",
                report.queries(), "calls");
        metric("revised_independent_verification_outcomes",
                "Revised Correctness",
                "Independent verification transition outcomes",
                report.outcomes(), "outcomes");
        metric("revised_independent_verification_basis",
                "Revised Correctness",
                "Independent verification basis",
                report.basis(), "text");
        if (IndependentExplicitStrongSolver.EXHAUSTIVE_FIXED_POINT_BASIS
                .equals(report.basis())) {
            metric("revised_independent_reference_states",
                    "Revised Correctness",
                    "Independent reference reachable states",
                    report.states(), "states");
            metric("revised_independent_reference_queries",
                    "Revised Correctness",
                    "Independent reference successor queries",
                    report.queries(), "calls");
            metric("revised_independent_reference_outcomes",
                    "Revised Correctness",
                    "Independent reference transition outcomes",
                    report.outcomes(), "outcomes");
        } else {
            metric("revised_independent_certificate_states",
                    "Revised Correctness",
                    "Independent certificate states checked",
                    report.states(), "states");
            metric("revised_independent_certificate_queries",
                    "Revised Correctness",
                    "Independent certificate successor queries",
                    report.queries(), "calls");
            metric("revised_independent_certificate_outcomes",
                    "Revised Correctness",
                    "Independent certificate transition outcomes",
                    report.outcomes(), "outcomes");
        }
        metric("revised_independent_verification_time",
                "Revised Time / Memory",
                "Independent explicit verification time",
                report.elapsedMillis(), "ms");
        metric("revised_independent_semantics_scope",
                "Revised Correctness",
                "Independent semantics scope",
                IndependentExplicitStrongSolver.EXHAUSTIVE_FIXED_POINT_BASIS
                        .equals(report.basis())
                        ? "separate_successor_and_fixed_point_over_shared_validated_problem"
                        : "separate_successor_and_certificate_proof_over_shared_validated_problem",
                "text");
        if (!report.isComplete()) {
            UpdatingControllerEvaluationRecorder.recordVerificationOutcome(
                    VerificationStatus.UNVERIFIED);
            metric("revised_independent_verification_status",
                    "Revised Correctness",
                    "Independent explicit verification status",
                    "inconclusive_resource_limit", "text");
            metric("revised_independent_verification_reason",
                    "Revised Correctness",
                    "Independent verification reason",
                    report.reason(), "text");
            output.outln(" - Independent explicit verification: "
                    + "INCONCLUSIVE (" + report.reason() + ")");
            return report;
        }
        if (!report.isValid()) {
            UpdatingControllerEvaluationRecorder.recordVerificationOutcome(
                    VerificationStatus.INVALID);
            metric("revised_independent_verification_status",
                    "Revised Correctness",
                    "Independent explicit verification status",
                    "failed", "text");
            metric("revised_independent_verification_reason",
                    "Revised Correctness",
                    "Independent verification reason",
                    String.join(" | ", report.violations()), "text");
            throw new IllegalStateException(
                    "Independent explicit verification rejected the solver "
                            + "result: " + report.violations());
        }
        UpdatingControllerEvaluationRecorder.recordVerificationOutcome(
                VerificationStatus.VERIFIED);
        metric("revised_independent_verification_status",
                "Revised Correctness",
                "Independent explicit verification status",
                "passed", "text");
        metric("revised_independent_verification_reason",
                "Revised Correctness",
                "Independent verification reason",
                "none", "text");
        output.outln(" - Independent explicit verification: PASSED "
                + "(basis=" + report.basis()
                + ", states=" + report.states()
                + ", queries=" + report.queries()
                + ", time=" + report.elapsedMillis() + " ms)");
        return report;
    }

    private static long positiveLongProperty(
            String name,
            long defaultValue) {
        String raw = System.getProperty(name);
        if (raw == null || raw.trim().isEmpty()) {
            return defaultValue;
        }
        long parsed;
        try {
            parsed = Long.parseLong(raw.trim());
        } catch (NumberFormatException invalid) {
            throw new IllegalArgumentException(
                    name + " must be a positive integer", invalid);
        }
        if (parsed < 1L) {
            throw new IllegalArgumentException(
                    name + " must be a positive integer");
        }
        return parsed;
    }

    private static void printStatistics(
            OtfDucsResult<?, ?, ?> result,
            LTSOutput output) {
        OtfDucsResult.Statistics statistics = result.statistics();
        output.outln(" - Explored states: " + statistics.discoveredStates()
                + " (expanded=" + statistics.expandedStates() + ")");
        output.outln(" - Cumulative materialized transition outcomes: "
                + statistics.materializedTransitions());
        output.outln(" - Oracle state-action queries: "
                + statistics.queriedStateActionPairs());
        output.outln(" - Guided proof accepted: "
                + statistics.guidedProofAccepted()
                + " (fallback=" + statistics.guidedFallbackUsed() + ")");
        output.outln(" - Deferred controllable candidates: "
                + statistics.deferredControllableCandidates()
                + " (resumed=" + statistics.resumedControllableCandidates()
                + ", unqueried="
                + statistics.unqueriedControllableCandidatesAtTermination()
                + ")");
        output.outln(" - Early success: " + statistics.earlySuccess());
    }

    private static void recordExecutionIdentity(
            UpdatingControllerCompositeState source,
            FineGrainedSuccessorOracle.ControllableActionOrder actionOrder,
            String solverMode,
            UpdatePolicyRestriction.Mode policyRestrictionMode) {
        int guidedStateLimit =
                Integer.getInteger("mtsa.otf.guidedStateLimit", 0)
                        .intValue();
        int guidedQueryLimit =
                Integer.getInteger("mtsa.otf.guidedQueryLimit", 0)
                        .intValue();
        boolean guidedEnabled =
                guidedStateLimit > 0 && guidedQueryLimit > 0;
        boolean lazyControllableBuckets = Boolean.parseBoolean(
                System.getProperty(
                        "mtsa.otf.lazyControllableBuckets", "true"));
        String attractorSchedule = lazyControllableBuckets
                ? "interleaved_lazy_complete_attractor"
                : "interleaved_eager_controllable_complete_attractor";
        String schedule;
        String methodId;
        String implementationVariant;
        if ("direct_full".equals(solverMode)) {
            schedule = "exhaustive_reachable_game_then_explicit_fixed_point";
            methodId = "Direct-Full";
            implementationVariant = "revised_direct_full_v1";
        } else if ("generic_lazy".equals(solverMode)) {
            schedule = "opaque_hash_order_batched_materialization_and_fixed_point";
            methodId = "Generic-Lazy";
            implementationVariant = "generic_lazy_strong_baseline_v4";
        } else {
            schedule = guidedEnabled
                    ? "guided_witness_then_" + attractorSchedule
                    : attractorSchedule;
            if (guidedEnabled) {
                methodId = "FG-OTF-Guided";
            } else if (!lazyControllableBuckets) {
                methodId = "FG-OTF-EagerC";
            } else if (actionOrder
                    == FineGrainedSuccessorOracle.ControllableActionOrder
                            .UPDATE_FIRST) {
                methodId = "FG-OTF-UpdateFirst";
            } else {
                methodId = "FG-OTF";
            }
            implementationVariant = "revised_otf_ducs_direct_v1";
        }

        metric("revised_input_target", "Revised Identity",
                "Updating-controller target", source.getName(), "text");
        metric("revised_method_id", "Revised Identity", "Method ID",
                methodId, "text");
        metric("revised_representation", "Revised Identity", "Representation",
                "direct_canonical_configuration", "text");
        metric("revised_schedule", "Revised Identity", "Exploration schedule",
                schedule, "text");
        metric("revised_controllable_action_order", "Revised Identity",
                "Controllable action exploration order",
                "generic_lazy".equals(solverMode)
                        ? "ignored_not_applicable"
                        : actionOrder.propertyValue(),
                "text");
        metric("revised_generic_baseline_hint_api_used", "Revised Identity",
                "Generic-baseline state-dependent hint API used",
                "generic_lazy".equals(solverMode) ? "false" : "not_applicable",
                "text");
        metric("revised_implementation_variant", "Revised Identity",
                "Implementation variant",
                implementationVariant, "text");
        String buildCommit = System.getProperty("mtsa.build.commit", "").trim();
        metric("revised_build_commit_id", "Revised Identity",
                "Build commit ID",
                buildCommit.isEmpty() ? "not_supplied" : buildCommit, "text");
        metric("revised_objective", "Revised Identity", "Synthesis objective",
                "strong_finite_completion", "text");
        metric("revised_scheduler_semantics", "Revised Identity",
                "Scheduler semantics",
                "all_maximal_traces_no_fairness", "text");
        metric("revised_update_policy_restriction",
                "Revised Identity",
                "Update-policy restriction",
                policyRestrictionMode.propertyValue(), "text");
        metric("revised_nondeterminism_semantics", "Revised Identity",
                "Nondeterministic transfer semantics",
                "all_outcomes_adversarial", "text");
        metric("revised_traditional_objective_compatibility",
                "Revised Completeness",
                "Traditional DUCS objective compatibility",
                "not_established", "text",
                "Traditional implementation uses a GR(1) progress objective; "
                        + "this implementation requires a decreasing rank on every retained edge.");
        metric("revised_java_version", "Revised Identity",
                "Java version", System.getProperty("java.version", "unknown"),
                "text");
        metric("revised_jvm_name", "Revised Identity",
                "JVM name", System.getProperty("java.vm.name", "unknown"),
                "text");
        metric("revised_jvm_vendor", "Revised Identity",
                "JVM vendor", System.getProperty("java.vm.vendor", "unknown"),
                "text");
        metric("revised_jvm_arguments", "Revised Identity",
                "JVM arguments",
                String.join(" ",
                        ManagementFactory.getRuntimeMXBean().getInputArguments()),
                "text");
        metric("revised_os_name", "Revised Identity",
                "Operating system", System.getProperty("os.name", "unknown"),
                "text");
        metric("revised_os_version", "Revised Identity",
                "Operating-system version",
                System.getProperty("os.version", "unknown"), "text");
        metric("revised_os_arch", "Revised Identity",
                "Operating-system architecture",
                System.getProperty("os.arch", "unknown"), "text");
        metric("revised_available_processors", "Revised Identity",
                "Available processors",
                Runtime.getRuntime().availableProcessors(), "processors");
        metric("revised_solver_thread_count", "Revised Identity",
                "Solver thread count", 1L, "threads");
        metric("revised_jvm_max_heap_bytes", "Revised Identity",
                "JVM maximum heap", Runtime.getRuntime().maxMemory(), "B");
        metric("revised_guided_state_limit", "Revised Identity",
                "Guided-search state limit",
                guidedStateLimit,
                "states");
        metric("revised_guided_query_limit", "Revised Identity",
                "Guided-search oracle-query limit",
                guidedQueryLimit,
                "calls");
        metric("revised_physical_closure_limit", "Revised Identity",
                "Activation physical-closure limit",
                Integer.getInteger(
                        "mtsa.revised.otf.maxPhysicalStates",
                        DEFAULT_PHYSICAL_CLOSURE_LIMIT).longValue(),
                "states");
    }

    private static void recordPolicyRestriction(
            UpdatePolicyRestriction<LocalState, Long> restriction) {
        metric("revised_update_policy_restriction_interpretation",
                "Revised Capability / Restriction",
                "Update-policy restriction interpretation",
                restriction.interpretation(), "text");
        metric("revised_update_policy_restriction_scope",
                "Revised Capability / Restriction",
                "Restricted semantic scope",
                "same_states_and_successors_controller_discipline", "text",
                "The comparison uses the same FG-DUCS states and successor "
                        + "relations. It removes controller choices; in a "
                        + "contiguous block, an enabled uncontrollable event "
                        + "outside the block makes the discipline fail.");
        metric("revised_update_policy_uncontrollables_preserved",
                "Revised Capability / Restriction",
                "All uncontrollable actions preserved",
                "true", "boolean",
                "A restriction cannot suppress an uncontrollable normal "
                        + "event and never removes an adversarial outcome.");
        metric("revised_update_policy_same_input",
                "Revised Capability / Restriction",
                "Same validated FG-DUCS input",
                "true", "boolean");
        String formalCorrespondence;
        if (restriction.mode() == UpdatePolicyRestriction.Mode.FULL_FG) {
            formalCorrespondence = "unrestricted_fg_ducs";
        } else if (restriction.mode()
                == UpdatePolicyRestriction.Mode.REQUIREMENT_BLOCK) {
            formalCorrespondence = "requirement_block_comparator";
        } else {
            formalCorrespondence =
                    "none_operational_discipline_not_paper_formal_comparator";
        }
        metric("revised_update_policy_formal_comparator_correspondence",
                "Revised Capability / Restriction",
                "Correspondence to a paper comparison restriction",
                formalCorrespondence, "text");
        metric("revised_update_policy_static_uninterrupted_block_precondition",
                "Revised Capability / Restriction",
                "Static uninterrupted-block precondition",
                restriction.isContinuousBlockMode()
                        ? Boolean.toString(restriction
                                .hasStaticUninterruptedBlockPrecondition())
                        : "not_applicable",
                "text",
                "For contiguous-transfer/update and requirement-block modes, "
                        + "false means an enabled uncontrollable event outside "
                        + "the active block makes that state losing; such an "
                        + "event is never suppressed.");
        metric("revised_update_policy_transfer_action_count",
                "Revised Capability / Restriction",
                "Reconfiguration actions in restricted group",
                restriction.transferActions().size(), "actions");
        metric("revised_update_policy_requirement_action_count",
                "Revised Capability / Restriction",
                "Requirement-switch actions in restricted group",
                restriction.requirementActions().size(), "actions");
        metric("revised_update_policy_fixed_sequence",
                "Revised Capability / Restriction",
                "Precedence-respecting fixed update sequence",
                String.join(">", restriction.fixedSequence()), "text",
                "Recorded for reproducibility; enforced only in "
                        + "fixed_update_order mode. This does not fix normal "
                        + "controllable actions and is not the paper's "
                        + "observation-independent fixed-script comparator.");
    }

    private static void recordPreparedInput(
            PreparedInput prepared,
            long preparationNanos) {
        FineGrainedUpdateProblem<LocalState, Long> problem = prepared.problem;
        InputCensus census = prepared.census;
        metric("revised_preparation_time", "Revised Time / Memory",
                "Representation and endpoint preparation time",
                millisText(preparationNanos), "ms");
        metric("revised_component_count", "Revised Workload / Input",
                "Component count", problem.components().size(), "components");
        metric("revised_old_component_states_total", "Revised Workload / Input",
                "Old component states total", census.oldStatesTotal, "states");
        metric("revised_old_component_transitions_total", "Revised Workload / Input",
                "Old component transitions total", census.oldTransitionsTotal,
                "transitions");
        metric("revised_new_component_states_total", "Revised Workload / Input",
                "New component states total", census.newStatesTotal, "states");
        metric("revised_new_component_transitions_total", "Revised Workload / Input",
                "New component transitions total", census.newTransitionsTotal,
                "transitions");
        for (int index = 0; index < census.oldStatesByComponent.size(); index++) {
            String suffix = Integer.toString(index);
            metric("revised_old_component_" + suffix + "_states",
                    "Revised Workload / Input", "Old component " + index + " states",
                    census.oldStatesByComponent.get(index).longValue(), "states");
            metric("revised_old_component_" + suffix + "_transitions",
                    "Revised Workload / Input",
                    "Old component " + index + " transitions",
                    census.oldTransitionsByComponent.get(index).longValue(),
                    "transitions");
            metric("revised_new_component_" + suffix + "_states",
                    "Revised Workload / Input", "New component " + index + " states",
                    census.newStatesByComponent.get(index).longValue(), "states");
            metric("revised_new_component_" + suffix + "_transitions",
                    "Revised Workload / Input",
                    "New component " + index + " transitions",
                    census.newTransitionsByComponent.get(index).longValue(),
                    "transitions");
        }
        metric("revised_old_requirement_count", "Revised Workload / Input",
                "Old requirement count", problem.oldRequirementIds().size(),
                "requirements");
        metric("revised_new_requirement_count", "Revised Workload / Input",
                "New requirement count", problem.newRequirementIds().size(),
                "requirements");
        metric("revised_update_requirement_count", "Revised Workload / Input",
                "Update-time requirement count",
                problem.updateRequirementIds().size(), "requirements");
        metric("revised_tester_states_total", "Revised Workload / Input",
                "Tester states total", census.testerStatesTotal, "states");
        metric("revised_tester_transitions_total", "Revised Workload / Input",
                "Tester transitions total", census.testerTransitionsTotal,
                "transitions");
        metric("revised_activation_domain_entries_total",
                "Revised Workload / Input",
                "Activation-domain entries total",
                census.activationDomainEntries, "entries");
        metric("revised_normal_action_count", "Revised Workload / Input",
                "Normal action count", problem.normalActions().size(), "actions");
        metric("revised_controllable_normal_action_count",
                "Revised Workload / Input",
                "Controllable normal action count",
                problem.controllableNormalActions().size(), "actions");
        metric("revised_uncontrollable_normal_action_count",
                "Revised Workload / Input",
                "Uncontrollable normal action count",
                problem.normalActions().size()
                        - problem.controllableNormalActions().size(),
                "actions");
        metric("revised_update_action_count", "Revised Workload / Input",
                "Update action count", problem.updateActions().size(), "actions");
        metric("revised_stop_action_count", "Revised Workload / Input",
                "Stop-old action count", problem.oldRequirementIds().size(),
                "actions");
        metric("revised_reconfigure_action_count", "Revised Workload / Input",
                "Reconfigure action count", problem.components().size(), "actions");
        metric("revised_start_action_count", "Revised Workload / Input",
                "Start-new action count", problem.newRequirementIds().size(),
                "actions");
        metric("revised_transfer_relation_edges_total",
                "Revised Workload / Input",
                "Transfer-relation edges total", census.transferEdges,
                "relation_edges");
        metric("revised_transfer_relation_max_fan_out",
                "Revised Workload / Input",
                "Transfer-relation maximum fan-out", census.transferMaxFanOut,
                "targets/source");
        metric("revised_transfer_relation_nondeterministic_sources",
                "Revised Workload / Input",
                "Transfer sources with multiple targets",
                census.nondeterministicTransferSources, "sources");
        metric("revised_precedence_transitive_edges",
                "Revised Workload / Input",
                "Precedence edges (transitive closure)",
                census.precedenceEdges, "edges");
        metric("revised_precedence_density", "Revised Workload / Input",
                "Precedence density",
                String.format(java.util.Locale.ROOT, "%.6f",
                        census.precedenceDensity), "ratio",
                "|transitive precedence relation| / (K*(K-1)/2), with 0 for K<2.");
        metric("revised_dependency_metrics_availability",
                "Revised Completeness",
                "Component-requirement dependency metrics",
                "unsupported_no_dependency_relation_in_input", "text");
        metric("revised_initial_endpoint_embeddings",
                "Revised Workload / Input",
                "Initial endpoint embeddings",
                problem.initialConfigurations().size(), "states");
        metric("revised_new_endpoint_signatures",
                "Revised Workload / Input",
                "New endpoint signatures", problem.goalSignatures().size(),
                "states");
        metric("revised_reachable_physical_states_for_activation",
                "Revised Workload / Input",
                "Reachable physical states used for activation",
                census.reachablePhysicalStates, "states");
        metric("revised_endpoint_coverage_complete",
                "Revised Completeness",
                "Exhaustive old/new endpoint coverage",
                Boolean.toString(problem.hasExhaustiveEndpointCoverage()),
                "boolean");
        metric("revised_internal_input_validation",
                "Revised Correctness",
                "Internal input validation",
                "passed", "text",
                "FineGrainedUpdateProblem construction validates namespaces, "
                        + "testers, activation languages, precedence, and endpoint coverage.");
        metric("revised_independent_input_checker_status",
                "Revised Correctness",
                "Independent input checker status",
                "not_run", "text");
    }

    private static void recordDecisionMetrics(
            OtfDucsResult<CanonicalUpdateConfiguration<LocalState, Long>, String,
                    GoalSignature<LocalState, Long>> result,
            long synthesisNanos,
            String solverMode) {
        OtfDucsResult.Statistics statistics = result.statistics();
        metric("revised_solve_and_internal_check_time",
                "Revised Time / Memory",
                "Solve plus internal certificate-check time",
                millisText(synthesisNanos), "ms",
                "Includes the selected solver and its same-semantics "
                        + "certificate checker; independent explicit "
                        + "verification is timed separately.");
        metric("revised_semantic_states_discovered",
                "Revised Workload / Search",
                "Distinct semantic states discovered across all attempts",
                statistics.discoveredStates(), "states",
                "Set union of states discovered by the guided witness attempt "
                        + "and, when used, the complete attractor fallback.");
        metric("revised_semantic_states_expanded",
                "Revised Workload / Search",
                "Distinct semantic states expanded across all attempts",
                statistics.expandedStates(), "states",
                "Set union of states expanded by the guided witness attempt "
                        + "and, when used, the complete attractor fallback.");
        metric("revised_successor_oracle_calls_cumulative",
                "Revised Workload / Search",
                "Solver successor-oracle calls (cumulative)",
                statistics.queriedStateActionPairs(), "calls",
                "Guided-attempt calls + complete-attractor calls made by the "
                        + "solver. Certificate-checker calls are excluded. A "
                        + "pair queried again after fallback is counted again "
                        + "as actual work.");
        metric("revised_materialized_transition_outcomes_cumulative",
                "Revised Workload / Search",
                "Cumulative materialized transition outcomes",
                statistics.materializedTransitions(), "outcomes",
                "All generated outcomes across guided and fallback attempts; "
                        + "this is not claimed to be unique (q,a,q').");
        if ("generic_lazy".equals(solverMode)) {
            metric("revised_propagated_incidences",
                    "Revised Workload / Search",
                    "Propagated reverse incidences",
                    "not_comparable_fixed_point_baseline", "text");
        } else {
            metric("revised_propagated_incidences",
                    "Revised Workload / Search",
                    "Propagated reverse incidences",
                    statistics.propagatedIncidences(), "incidences");
        }
        metric("revised_fixed_point_state_inspections",
                "Revised Workload / Search",
                "Generic/direct fixed-point state inspections",
                statistics.fixedPointStateInspections(), "inspections",
                "Zero for the reverse-propagation OTF solver; reported as a "
                        + "separate, non-comparable workload for explicit "
                        + "fixed-point solvers.");
        metric("revised_fixed_point_computations",
                "Revised Workload / Search",
                "Generic/direct fixed-point computations",
                statistics.fixedPointComputations(), "computations",
                "Zero for the reverse-propagation OTF solver.");
        metric("revised_early_success", "Revised Workload / Search",
                "Early success", Boolean.toString(statistics.earlySuccess()),
                "boolean");
        String searchMode = "direct_full".equals(solverMode)
                ? "exhaustive_reachable_game_then_explicit_fixed_point"
                : ("generic_lazy".equals(solverMode)
                        ? "opaque_hash_order_batched_materialization_and_fixed_point"
                        : (statistics.guidedProofAccepted()
                        ? "guided_winning_certificate"
                        : (statistics.guidedFallbackUsed()
                                ? "guided_attempt_then_complete_attractor"
                                : "complete_attractor")));
        metric("revised_search_mode", "Revised Identity",
                "Decision-producing search mode", searchMode, "text");
        metric("revised_guided_proof_accepted",
                "Revised Workload / Search",
                "Guided winning proof accepted",
                Boolean.toString(statistics.guidedProofAccepted()), "boolean");
        metric("revised_guided_fallback_used",
                "Revised Workload / Search",
                "Complete-attractor fallback used",
                Boolean.toString(statistics.guidedFallbackUsed()), "boolean");
        metric("revised_guided_maximum_depth",
                "Revised Workload / Search",
                "Guided search maximum recursion depth",
                statistics.guidedMaximumDepth(), "states");
        metric("revised_attractor_peak_frontier",
                "Revised Workload / Search",
                "Complete-attractor peak frontier",
                statistics.attractorPeakFrontier(), "states");
        metric("revised_lazy_controllable_buckets_enabled",
                "Revised Identity",
                "Lazy controllable-bucket expansion enabled",
                Boolean.toString(statistics.lazyControllableBuckets()),
                "boolean");
        metric("revised_deferred_controllable_candidates",
                "Revised Workload / Search",
                "Controllable candidates deferred by complete attractor",
                statistics.deferredControllableCandidates(), "candidates");
        metric("revised_resumed_controllable_candidates",
                "Revised Workload / Search",
                "Deferred controllable candidates later queried",
                statistics.resumedControllableCandidates(), "candidates");
        metric("revised_deferred_controllable_candidates_unqueried",
                "Revised Workload / Search",
                "Deferred controllable candidates left unqueried at termination",
                statistics.unqueriedControllableCandidatesAtTermination(),
                "candidates");
        metric("revised_peak_frontier_or_guided_depth",
                "Revised Workload / Search",
                "Peak frontier or guided recursion depth",
                statistics.peakFrontier(), "states",
                "max(guided recursion depth, complete-attractor frontier size); "
                        + "the two components are also reported separately above.");
        metric("revised_semantic_transitions_unique_availability",
                "Revised Completeness",
                "Unique semantic (q,a,q') transition count",
                "unsupported_current_collector", "text");
        metric("revised_internal_certificate_check",
                "Revised Correctness",
                "Internal certificate checker",
                "passed", "text");
        metric("revised_internal_certificate_check_scope",
                "Revised Correctness",
                "Internal certificate checker scope",
                "same_successor_semantics_not_independent", "text");
        metric("revised_jvm_heap_peak_bytes",
                "Revised Time / Memory",
                "JVM heap peak",
                EvaluationProfiler.getPeakMemoryUsage(), "B");
        metric("revised_peak_rss_availability",
                "Revised Completeness",
                "Peak RSS availability",
                "not_run_requires_parent_process_monitor", "text");
    }

    private static void recordDirectFullMetrics(
            DirectFullStrongSolver.Statistics statistics) {
        metric("revised_direct_full_initial_states",
                "Direct-Full Workload",
                "Initial states",
                statistics.initialStates(), "states");
        metric("revised_direct_full_enumerated_states",
                "Direct-Full Workload",
                "Exhaustively enumerated states",
                statistics.enumeratedStates(), "states");
        metric("revised_direct_full_expanded_states",
                "Direct-Full Workload",
                "Expanded states",
                statistics.expandedStates(), "states");
        metric("revised_direct_full_successor_queries",
                "Direct-Full Workload",
                "Successor state-action queries",
                statistics.queriedStateActionPairs(), "calls");
        metric("revised_direct_full_enabled_action_buckets",
                "Direct-Full Workload",
                "Enabled action buckets",
                statistics.enabledActionBuckets(), "buckets");
        metric("revised_direct_full_materialized_transition_outcomes",
                "Direct-Full Workload",
                "Materialized transition outcomes",
                statistics.materializedTransitions(), "outcomes");
        metric("revised_direct_full_peak_enumeration_frontier",
                "Direct-Full Workload",
                "Peak enumeration frontier",
                statistics.peakEnumerationFrontier(), "states");
        metric("revised_direct_full_fixed_point_iterations",
                "Direct-Full Workload",
                "Explicit fixed-point iterations",
                statistics.fixedPointIterations(), "iterations");
        metric("revised_direct_full_fixed_point_state_inspections",
                "Direct-Full Workload",
                "Fixed-point state inspections",
                statistics.fixedPointStateInspections(), "inspections");
        metric("revised_direct_full_fixed_point_bucket_inspections",
                "Direct-Full Workload",
                "Fixed-point action-bucket inspections",
                statistics.fixedPointBucketInspections(), "inspections");
        metric("revised_direct_full_fixed_point_outcome_inspections",
                "Direct-Full Workload",
                "Fixed-point outcome inspections",
                statistics.fixedPointOutcomeInspections(), "inspections");
        metric("revised_direct_full_enumeration_time",
                "Revised Time / Memory",
                "Direct-Full exhaustive enumeration time",
                millisText(statistics.enumerationNanoseconds()), "ms");
        metric("revised_direct_full_fixed_point_time",
                "Revised Time / Memory",
                "Direct-Full explicit fixed-point time",
                millisText(statistics.fixedPointNanoseconds()), "ms");
        metric("revised_direct_full_certificate_time",
                "Revised Time / Memory",
                "Direct-Full certificate extraction time",
                millisText(statistics.certificateNanoseconds()), "ms");
    }

    private static String configuredSolverMode() {
        String value = System.getProperty(
                "mtsa.revised.otf.solver", "otf").trim();
        if ("otf".equals(value) || "direct_full".equals(value)
                || "generic_lazy".equals(value)) {
            return value;
        }
        throw new IllegalArgumentException(
                "mtsa.revised.otf.solver must be otf, generic_lazy, or direct_full: "
                        + value);
    }

    private static void recordLosingCertificate(
            OtfDucsResult<CanonicalUpdateConfiguration<LocalState, Long>, String,
                    GoalSignature<LocalState, Long>> result) {
        Set<CanonicalUpdateConfiguration<LocalState, Long>> losing =
                result.losingCertificate().losingStates();
        metric("revised_decision", "Revised Outcome",
                "Decision", "unrealizable", "text");
        metric("revised_losing_region_states",
                "Revised Correctness",
                "Losing-region states", losing.size(), "states");
        metric("revised_losing_region_phase_masks",
                "Revised Correctness",
                "Distinct pending-action masks in losing region",
                distinctPendingMasks(losing), "masks");
        metric("revised_output_controller_availability",
                "Revised Outcome",
                "Output controller availability",
                "not_applicable_unrealizable", "text");
        metric("revised_guard_coverage_availability",
                "Revised Outcome",
                "Guard coverage availability",
                "not_applicable_unrealizable", "text");
    }

    private static void recordWinningCertificate(
            FineGrainedUpdateProblem<LocalState, Long> problem,
            OtfDucsResult<CanonicalUpdateConfiguration<LocalState, Long>, String,
                    GoalSignature<LocalState, Long>> result,
            CompactState controller,
            long linkNanos) {
        OtfDucsResult.WinningCertificate<
                CanonicalUpdateConfiguration<LocalState, Long>, String,
                GoalSignature<LocalState, Long>> certificate =
                result.winningCertificate();
        long strategyActions = 0;
        long strategyTransitions = 0;
        int maximumRank = 0;
        for (Integer value : certificate.ranks().values()) {
            maximumRank = Math.max(maximumRank, value.intValue());
        }
        for (Map<String, Set<CanonicalUpdateConfiguration<LocalState, Long>>> actions
                : certificate.strategy().values()) {
            strategyActions += actions.size();
            for (Set<CanonicalUpdateConfiguration<LocalState, Long>> outcomes
                    : actions.values()) {
                strategyTransitions += outcomes.size();
            }
        }
        metric("revised_decision", "Revised Outcome",
                "Decision", "realizable", "text");
        metric("revised_certificate_states", "Revised Correctness",
                "Winning-certificate states",
                certificate.ranks().size(), "states");
        metric("revised_certificate_strategy_action_buckets",
                "Revised Correctness",
                "Strategy state-action buckets",
                strategyActions, "buckets");
        metric("revised_certificate_strategy_transitions_unique",
                "Revised Correctness",
                "Strategy transitions (unique q,a,q')",
                strategyTransitions, "transitions");
        metric("revised_certificate_goal_matches",
                "Revised Correctness",
                "Atomic Goal links", certificate.goalMatches().size(), "links");
        metric("revised_worst_completion_rank",
                "Revised Correctness",
                "Worst completion rank", maximumRank, "steps");
        metric("revised_certificate_phase_masks",
                "Revised Correctness",
                "Distinct pending-action masks in certificate",
                distinctPendingMasks(certificate.ranks().keySet()), "masks");
        metric("revised_link_and_export_time", "Revised Time / Memory",
                "Atomic Link checking and export time",
                millisText(linkNanos), "ms");
        metric("revised_link_checker", "Revised Correctness",
                "Atomic Link checker", "passed", "text");
        metric("revised_output_controller_states",
                "Revised Workload / Output",
                "Output controller states", controller.maxStates, "states");
        metric("revised_output_controller_transitions",
                "Revised Workload / Output",
                "Output controller transitions",
                controller.ntransitions(), "transitions");
        recordGuardCoverage(problem, certificate);
    }

    private static void recordGuardCoverage(
            FineGrainedUpdateProblem<LocalState, Long> problem,
            OtfDucsResult.WinningCertificate<
                    CanonicalUpdateConfiguration<LocalState, Long>, String,
                    GoalSignature<LocalState, Long>> certificate) {
        double coverageTotal = 0.0;
        int requirementCount = 0;
        int index = 0;
        for (Requirement<LocalState, Long> requirement
                : problem.requirements()) {
            if (requirement.role() != RequirementRole.NEW) continue;
            String startAction = requirement.startAction().get();
            Set<PhysicalState<LocalState>> reached =
                    new LinkedHashSet<>();
            for (Map.Entry<
                    CanonicalUpdateConfiguration<LocalState, Long>,
                    Map<String, Set<CanonicalUpdateConfiguration<LocalState, Long>>>>
                    entry : certificate.strategy().entrySet()) {
                if (entry.getValue().containsKey(startAction)) {
                    reached.add(entry.getKey().physicalState());
                }
            }
            int domainSize = requirement.requiredActivationSpec().domain().size();
            double coverage = domainSize == 0
                    ? 0.0
                    : reached.size() / (double) domainSize;
            coverageTotal += coverage;
            requirementCount++;
            String prefix = "revised_new_requirement_" + index++;
            metric(prefix + "_id", "Revised Workload / Guard Coverage",
                    "New requirement ID", requirement.id(), "text");
            metric(prefix + "_activation_guard_states",
                    "Revised Workload / Guard Coverage",
                    "Activation guard states for " + requirement.id(),
                    domainSize, "states");
            metric(prefix + "_reached_start_states",
                    "Revised Workload / Guard Coverage",
                    "Reached start states for " + requirement.id(),
                    reached.size(), "states");
            metric(prefix + "_guard_coverage",
                    "Revised Workload / Guard Coverage",
                    "Guard coverage for " + requirement.id(),
                    String.format(java.util.Locale.ROOT, "%.6f", coverage),
                    "ratio",
                    "distinct strategy-reachable physical sources of "
                            + startAction + " / |D_r|.");
        }
        double macroAverage = requirementCount == 0
                ? 0.0
                : coverageTotal / requirementCount;
        metric("revised_guard_coverage_macro_average",
                "Revised Workload / Guard Coverage",
                "Guard coverage macro average",
                String.format(java.util.Locale.ROOT, "%.6f", macroAverage),
                "ratio",
                "Arithmetic mean of per-new-requirement guard coverage; "
                        + "0 when there is no new requirement.");
    }

    private static void recordEvaluationCompleteness(
            IndependentExplicitStrongSolver.VerificationReport independent) {
        metric("revised_true_end_to_end_time_availability",
                "Revised Completeness",
                "Process-level end-to-end time",
                "not_run_requires_parent_process", "text");
        metric("revised_record_valid", "Revised Completeness",
                "Paper evaluation record valid",
                "false", "boolean");
        String buildCommit = System.getProperty("mtsa.build.commit", "").trim();
        String missing = "independent_input_language_verification;"
                + (independent == null || !independent.isValid()
                        ? "independent_semantic_verification;"
                        : "")
                + "peak_rss;"
                + "process_end_to_end;component_requirement_dependency_density;"
                + "discovered_phase_coverage;memo_table_peak;"
                + "unique_semantic_transitions"
                + (buildCommit.isEmpty() ? ";build_commit_id" : "");
        metric("revised_missing_required_metrics",
                "Revised Completeness",
                "Missing required paper-evaluation metrics",
                missing,
                "metric_ids");
    }

    private static int distinctPendingMasks(
            Collection<CanonicalUpdateConfiguration<LocalState, Long>> states) {
        Set<Set<String>> masks = new LinkedHashSet<>();
        for (CanonicalUpdateConfiguration<LocalState, Long> state : states) {
            masks.add(state.pendingActions());
        }
        return masks.size();
    }

    private static String millisText(long nanos) {
        return String.format(java.util.Locale.ROOT, "%.3f", nanos / 1_000_000.0);
    }

    private static void metric(
            String key, String section, String label, long value, String unit) {
        metric(key, section, label, Long.toString(value), unit);
    }

    private static void metric(
            String key,
            String section,
            String label,
            long value,
            String unit,
            String formula) {
        metric(key, section, label, Long.toString(value), unit, formula);
    }

    private static void metric(
            String key, String section, String label, String value, String unit) {
        UpdatingControllerEvaluationRecorder.recordRevisedMetric(
                key, section, label, value, unit);
    }

    private static void metric(
            String key,
            String section,
            String label,
            String value,
            String unit,
            String formula) {
        UpdatingControllerEvaluationRecorder.recordRevisedMetric(
                key, section, label, value, unit, formula);
    }

    private static PreparedInput prepare(UpdatingControllerCompositeState source) {
        Vector<CompactState> oldMachines = source.getRawOldEnvironmentComponents();
        Vector<CompactState> newMachines = source.getRawNewEnvironmentComponents();
        List<Map<Integer, Set<Integer>>> rawTransfers =
                source.getRawTransferRelations();
        if (oldMachines.isEmpty()
                || oldMachines.size() != newMachines.size()
                || oldMachines.size() != rawTransfers.size()) {
            throw new IllegalArgumentException(
                    "Missing complete old/new component and direct transfer payload");
        }

        List<FiniteLts<Long>> rawOld = new ArrayList<>();
        List<FiniteLts<Long>> rawNew = new ArrayList<>();
        LinkedHashSet<String> normalActions = new LinkedHashSet<>();
        for (int index = 0; index < oldMachines.size(); index++) {
            FiniteLts<Long> oldLts = FiniteLts.fromMtsa(oldMachines.get(index));
            FiniteLts<Long> newLts = FiniteLts.fromMtsa(newMachines.get(index));
            rawOld.add(oldLts);
            rawNew.add(newLts);
            normalActions.addAll(oldLts.alphabet());
            normalActions.addAll(newLts.alphabet());
        }
        normalActions.remove(UpdateConstants.BEGIN_UPDATE);
        normalActions.remove(UpdateConstants.FINISH_UPDATE);
        normalActions.remove("tau");

        UpdateProtocolSpec protocol = source.getUpdateProtocolSpec();
        LinkedHashSet<String> updateActions =
                new LinkedHashSet<>(protocol.getProgressActions());
        LinkedHashSet<String> commonAlphabet = new LinkedHashSet<>(normalActions);
        commonAlphabet.addAll(updateActions);

        List<Observer> observers = compileObservers(
                source.getSynthesisMachines(), normalActions);
        List<Long> initialObserverStates = new ArrayList<>();
        for (Observer observer : observers) {
            initialObserverStates.add(observer.initialState);
        }

        List<VersionedComponent<LocalState>> components =
                compileComponents(
                        oldMachines, rawOld, rawNew, rawTransfers,
                        protocol, observers, initialObserverStates, normalActions);

        LinkedHashSet<String> controllableNormal =
                new LinkedHashSet<>(source.getControllableActions());
        controllableNormal.retainAll(normalActions);

        List<TesterRecord> oldTesters = compileTesters(
                source.getOldSafetyLTSs(), RequirementRole.OLD, commonAlphabet);
        List<TesterRecord> newTesters = compileTesters(
                source.getNewSafetyLTSs(), RequirementRole.NEW, commonAlphabet);
        List<TesterRecord> updateTesters = compileTesters(
                source.getTransitionRequirements(), RequirementRole.UPDATE_TIME,
                commonAlphabet);

        bindUpdateActions(oldTesters, newTesters, protocol);

        FiniteLts<Long> oldController = importController(
                source.getOldController(), normalActions, "old");
        FiniteLts<Long> newController = importController(
                source.getNewController(), normalActions, "new");
        validateEndpointControllerAlphabets(
                components, oldController, newController);

        FiniteLts<EndpointState> oldEndpoint = buildEndpoint(
                oldController, components, oldTesters, true, normalActions);
        FiniteLts<EndpointState> newEndpoint = buildEndpoint(
                newController, components, newTesters, false, normalActions);

        LinkedHashMap<EndpointState, String> newEndpointIds = new LinkedHashMap<>();
        int endpointIndex = 0;
        for (EndpointState state : newEndpoint.reachableStates()) {
            newEndpointIds.put(state, String.format("new-%08d", endpointIndex++));
        }
        Set<EndpointState> loadableNewEndpointStates =
                selectLoadableNewEndpointStates(source, newEndpoint);

        LinkedHashSet<PhysicalState<LocalState>> oldRoots = new LinkedHashSet<>();
        for (EndpointState state : oldEndpoint.reachableStates()) {
            oldRoots.add(state.physical(true));
        }
        Set<PhysicalState<LocalState>> reachablePhysical =
                newTesters.isEmpty()
                        ? Collections.<PhysicalState<LocalState>>emptySet()
                        : physicalClosure(
                                components, normalActions, oldRoots);

        List<Requirement<LocalState, Long>> requirements = new ArrayList<>();
        for (TesterRecord tester : oldTesters) {
            requirements.add(Requirement.oldRequirement(
                    tester.id, tester.tester, tester.updateAction));
        }

        Map<CompactState, List<CompactState>> safetyComponents =
                source.getSafetyComponentsMap();
        Map<CompactState, Map<List<Integer>, Integer>> safetyStateMappings =
                source.getSafetyStateMapping();
        for (TesterRecord tester : newTesters) {
            ActivationSpec<LocalState, Long> activation = newActivation(
                    tester, reachablePhysical, observers,
                    safetyComponents, safetyStateMappings, commonAlphabet);
            requirements.add(Requirement.newRequirement(
                    tester.id, tester.tester, activation, tester.updateAction));
        }
        for (TesterRecord tester : updateTesters) {
            ActivationSpec<LocalState, Long> activation = updateActivation(
                    tester, oldRoots, commonAlphabet);
            requirements.add(Requirement.updateTimeRequirement(
                    tester.id, tester.tester, activation));
        }

        FineGrainedUpdateProblem.Builder<LocalState, Long> builder =
                FineGrainedUpdateProblem.<LocalState, Long>builder()
                        .components(components)
                        .requirements(requirements)
                        .normalActions(normalActions)
                        .controllableNormalActions(controllableNormal)
                        .initialSnapshotsFromReachable(
                                oldEndpoint, EndpointState::oldSnapshot)
                        .goalSignaturesFromReachable(
                                newEndpoint,
                                state -> state.newSignature(newEndpointIds.get(state)),
                                loadableNewEndpointStates::contains);

        addProtocolPrecedence(protocol, builder);

        FineGrainedUpdateProblem<LocalState, Long> problem = builder.build();
        InputCensus census = InputCensus.from(
                rawOld, rawNew, rawTransfers, problem, reachablePhysical.size());
        return new PreparedInput(
                problem, oldEndpoint, newEndpoint, newEndpointIds, census);
    }

    static Set<EndpointState> selectLoadableNewEndpointStates(
            UpdatingControllerCompositeState source,
            FiniteLts<EndpointState> newEndpoint) {
        List<EndpointState> reachable =
                new ArrayList<EndpointState>(
                        newEndpoint.reachableStates());
        if (!source.hasLoadableNewEndpointStateIndices()) {
            return Collections.unmodifiableSet(
                    new LinkedHashSet<EndpointState>(reachable));
        }

        LinkedHashSet<EndpointState> result =
                new LinkedHashSet<EndpointState>();
        for (Integer index
                : source.getLoadableNewEndpointStateIndices()) {
            if (index.intValue() >= reachable.size()) {
                throw new IllegalArgumentException(
                        "loadable_new_states index " + index
                                + " is outside the reachable new endpoint range 0.."
                                + (reachable.size() - 1));
            }
            result.add(reachable.get(index.intValue()));
        }
        return Collections.unmodifiableSet(result);
    }

    static <S, M> void addProtocolPrecedence(
            UpdateProtocolSpec protocol,
            FineGrainedUpdateProblem.Builder<S, M> builder) {
        Objects.requireNonNull(protocol, "protocol");
        Objects.requireNonNull(builder, "builder");
        protocol.validatePrecedence();
        for (UpdateProtocolSpec.PrecedenceEdge edge
                : protocol.getPrecedenceEdges()) {
            builder.addPrecedence(edge.before(), edge.after());
        }
    }

    static List<VersionedComponent<LocalState>> compileComponents(
            List<CompactState> oldMachines,
            List<FiniteLts<Long>> rawOld,
            List<FiniteLts<Long>> rawNew,
            List<Map<Integer, Set<Integer>>> rawTransfers,
            UpdateProtocolSpec protocol,
            List<Observer> observers,
            List<Long> initialObserverStates,
            Set<String> normalActions) {
        List<VersionedComponent<LocalState>> result = new ArrayList<>();

        FiniteLts<LocalState> augmentedOld = buildAugmented(
                rawOld.get(0), observers, normalActions,
                new LocalState(rawOld.get(0).initialState(), initialObserverStates),
                Collections.<LocalState>emptySet());

        LinkedHashSet<LocalState> newSeeds = new LinkedHashSet<>();
        newSeeds.add(new LocalState(
                rawNew.get(0).initialState(), initialObserverStates));
        Map<Integer, Set<Integer>> firstRawTransfer = rawTransfers.get(0);
        for (LocalState oldState : augmentedOld.states()) {
            Set<Integer> targets = firstRawTransfer.get(
                    Integer.valueOf(oldState.rawState.intValue()));
            if (targets == null) continue;
            for (Integer target : targets) {
                newSeeds.add(new LocalState(
                        Long.valueOf(target.longValue()), oldState.observerStates));
            }
        }
        FiniteLts<LocalState> augmentedNew = buildAugmented(
                rawNew.get(0), observers, normalActions,
                new LocalState(rawNew.get(0).initialState(), initialObserverStates),
                newSeeds);

        Map<LocalState, Set<LocalState>> firstTransfer = new LinkedHashMap<>();
        for (LocalState oldState : augmentedOld.states()) {
            Set<Integer> targets = firstRawTransfer.get(
                    Integer.valueOf(oldState.rawState.intValue()));
            if (targets == null) continue;
            LinkedHashSet<LocalState> localTargets = new LinkedHashSet<>();
            for (Integer target : targets) {
                LocalState converted = new LocalState(
                        Long.valueOf(target.longValue()), oldState.observerStates);
                if (!augmentedNew.states().contains(converted)) {
                    throw new IllegalStateException(
                            "Augmented transfer target is absent from the new component: "
                                    + converted);
                }
                localTargets.add(converted);
            }
            firstTransfer.put(oldState, localTargets);
        }
        result.add(new VersionedComponent<>(
                componentId(oldMachines.get(0), 0),
                augmentedOld,
                augmentedNew,
                firstTransfer,
                requireReconfigureAction(protocol, 0),
                rawOld.get(0).alphabet(),
                rawNew.get(0).alphabet()));

        for (int index = 1; index < rawOld.size(); index++) {
            FiniteLts<LocalState> oldLts = wrapRaw(rawOld.get(index));
            FiniteLts<LocalState> newLts = wrapRaw(rawNew.get(index));
            Map<LocalState, Set<LocalState>> transfer = new LinkedHashMap<>();
            for (Map.Entry<Integer, Set<Integer>> entry
                    : rawTransfers.get(index).entrySet()) {
                LocalState source = LocalState.raw(entry.getKey().longValue());
                LinkedHashSet<LocalState> targets = new LinkedHashSet<>();
                for (Integer target : entry.getValue()) {
                    targets.add(LocalState.raw(target.longValue()));
                }
                transfer.put(source, targets);
            }
            result.add(new VersionedComponent<>(
                    componentId(oldMachines.get(index), index),
                    oldLts,
                    newLts,
                    transfer,
                    requireReconfigureAction(protocol, index)));
        }
        return result;
    }

    static String componentId(CompactState machine, int index) {
        String name = machine == null ? null : machine.getName();
        if (name == null || name.trim().isEmpty()) {
            return "component-" + index;
        }
        return index + ":" + name;
    }

    static String requireReconfigureAction(
            UpdateProtocolSpec protocol,
            int index) {
        String action = protocol.getReconfigureActionForMappingIndex(index);
        if (action == null || action.trim().isEmpty()) {
            throw new IllegalArgumentException(
                    "Missing concrete reconfigure action for component " + index);
        }
        return action;
    }

    static FiniteLts<LocalState> wrapRaw(FiniteLts<Long> raw) {
        LocalState initial = LocalState.raw(raw.initialState().longValue());
        FiniteLts.Builder<LocalState> builder =
                FiniteLts.<LocalState>builder(initial)
                        .addActions(raw.alphabet());
        for (Long state : raw.states()) {
            builder.addState(LocalState.raw(state.longValue()));
        }
        for (Map.Entry<Long, Map<String, Set<Long>>> stateEntry
                : raw.transitions().entrySet()) {
            for (Map.Entry<String, Set<Long>> actionEntry
                    : stateEntry.getValue().entrySet()) {
                for (Long target : actionEntry.getValue()) {
                    builder.addTransition(
                            LocalState.raw(stateEntry.getKey().longValue()),
                            actionEntry.getKey(),
                            LocalState.raw(target.longValue()));
                }
            }
        }
        return builder.build();
    }

    static FiniteLts<LocalState> buildAugmented(
            FiniteLts<Long> raw,
            List<Observer> observers,
            Set<String> normalActions,
            LocalState initial,
            Collection<LocalState> additionalSeeds) {
        LinkedHashSet<String> alphabet = new LinkedHashSet<>(raw.alphabet());
        for (Observer observer : observers) {
            alphabet.addAll(observer.alphabet);
        }
        alphabet.retainAll(normalActions);
        List<String> orderedActions = sorted(alphabet);

        FiniteLts.Builder<LocalState> builder =
                FiniteLts.<LocalState>builder(initial).addActions(orderedActions);
        LinkedHashSet<LocalState> discovered = new LinkedHashSet<>();
        Deque<LocalState> queue = new ArrayDeque<>();
        addSeed(initial, discovered, queue, builder);
        for (LocalState seed : additionalSeeds) {
            if (!raw.states().contains(seed.rawState)) {
                throw new IllegalArgumentException(
                        "Augmented seed uses an unknown raw state: " + seed);
            }
            if (seed.observerStates.size() != observers.size()) {
                throw new IllegalArgumentException(
                        "Augmented seed observer arity mismatch: " + seed);
            }
            addSeed(seed, discovered, queue, builder);
        }

        while (!queue.isEmpty()) {
            LocalState source = queue.removeFirst();
            for (String action : orderedActions) {
                Set<Long> rawTargets;
                if (raw.hasAction(action)) {
                    rawTargets = raw.successors(source.rawState, action);
                    if (rawTargets.isEmpty()) continue;
                } else {
                    rawTargets = Collections.singleton(source.rawState);
                }

                List<Long> observerTargets = new ArrayList<>();
                for (int index = 0; index < observers.size(); index++) {
                    observerTargets.add(observers.get(index).stepOrStutter(
                            source.observerStates.get(index), action));
                }
                for (Long rawTarget : rawTargets) {
                    LocalState target = new LocalState(rawTarget, observerTargets);
                    builder.addTransition(source, action, target);
                    if (discovered.add(target)) {
                        queue.addLast(target);
                    }
                }
            }
        }
        return builder.build();
    }

    private static void addSeed(
            LocalState seed,
            Set<LocalState> discovered,
            Deque<LocalState> queue,
            FiniteLts.Builder<LocalState> builder) {
        builder.addState(seed);
        if (discovered.add(seed)) {
            queue.addLast(seed);
        }
    }

    static List<Observer> compileObservers(
            Collection<CompactState> machines,
            Set<String> normalActions) {
        List<Observer> result = new ArrayList<>();
        if (machines == null) return result;
        for (CompactState machine : machines) {
            if (machine == null) continue;
            result.add(Observer.from(machine, normalActions));
        }
        result.sort(Comparator.comparing(observer -> observer.name));
        return result;
    }

    static List<TesterRecord> compileTesters(
            Collection<CompactState> machines,
            RequirementRole role,
            Set<String> commonAlphabet) {
        List<CompactState> ordered = new ArrayList<>();
        if (machines != null) ordered.addAll(machines);
        ordered.sort(Comparator.comparing(MtsaRevisedOtfDucsAdapter::machineName));

        List<TesterRecord> result = new ArrayList<>();
        int index = 0;
        for (CompactState machine : ordered) {
            String name = machineName(machine);
            SafetyTester<Long> tester = compileSafetyTester(machine, commonAlphabet);
            Long boundaryState = stepRawOrStutter(
                    machine, Long.valueOf(0L), UpdateConstants.BEGIN_UPDATE);
            String id = role.name().toLowerCase() + ":" + name + ":" + index++;
            result.add(new TesterRecord(
                    id, name, role, machine, tester, boundaryState));
        }
        return result;
    }

    private static String machineName(CompactState machine) {
        if (machine == null || machine.getName() == null
                || machine.getName().trim().isEmpty()) {
            return "(unnamed)";
        }
        return machine.getName();
    }

    static void bindUpdateActions(
            List<TesterRecord> oldTesters,
            List<TesterRecord> newTesters,
            UpdateProtocolSpec protocol) {
        for (TesterRecord tester : oldTesters) {
            tester.updateAction = protocol.getOldSafetyToStopAction().get(tester.sourceName);
            if (tester.updateAction == null) {
                throw new IllegalArgumentException(
                        "No stop action for old safety " + tester.sourceName);
            }
        }
        for (TesterRecord tester : newTesters) {
            tester.updateAction = protocol.getNewSafetyToStartAction().get(tester.sourceName);
            if (tester.updateAction == null) {
                throw new IllegalArgumentException(
                        "No start action for new safety " + tester.sourceName);
            }
        }
    }

    private static SafetyTester<Long> compileSafetyTester(
            CompactState machine,
            Set<String> commonAlphabet) {
        if (machine == null || machine.maxStates <= 0) {
            throw new IllegalArgumentException("Safety tester has no states");
        }
        rejectInternalTau(machine);
        LinkedHashSet<String> localAlphabet = new LinkedHashSet<>();
        if (machine.alphabet != null) {
            for (String action : machine.alphabet) {
                if (action == null || isBoundaryOrInternal(action)
                        || action.startsWith("@")) {
                    continue;
                }
                if (action.endsWith("?")) {
                    throw new IllegalArgumentException(
                            "Modal action is unsupported in safety tester "
                                    + machineName(machine) + ": " + action);
                }
                if (!commonAlphabet.contains(action)) {
                    throw new IllegalArgumentException(
                            "Safety tester action is outside the revised common alphabet: "
                                    + machineName(machine) + " / " + action);
                }
                localAlphabet.add(action);
            }
        }

        SafetyTester.Builder<Long> builder = SafetyTester.<Long>builder()
                .initialState(Long.valueOf(0L))
                .addActions(sorted(localAlphabet))
                .addErrorState(Long.valueOf(ERROR_STATE));
        for (long state = 0; state < machine.maxStates; state++) {
            builder.addState(Long.valueOf(state));
        }
        for (long state = 0; state < machine.maxStates; state++) {
            for (String action : sorted(localAlphabet)) {
                Long target = deterministicRawTarget(
                        machine, Long.valueOf(state), action, true);
                builder.addTransition(Long.valueOf(state), action, target);
            }
        }
        for (String action : sorted(localAlphabet)) {
            builder.addTransition(
                    Long.valueOf(ERROR_STATE), action, Long.valueOf(ERROR_STATE));
        }
        return builder.build();
    }

    private static boolean isBoundaryOrInternal(String action) {
        return "tau".equals(action)
                || UpdateConstants.BEGIN_UPDATE.equals(action)
                || UpdateConstants.FINISH_UPDATE.equals(action);
    }

    private static void rejectInternalTau(CompactState machine) {
        int tau = actionIndex(machine, "tau");
        if (tau < 0 || machine.states == null) return;
        for (int state = 0; state < machine.maxStates; state++) {
            int[] targets = EventState.nextState(machine.states[state], tau);
            if (targets != null && targets.length > 0) {
                throw new IllegalArgumentException(
                        "Internal tau transitions must be eliminated from safety tester "
                                + machineName(machine));
            }
        }
    }

    private static Long stepRawOrStutter(
            CompactState machine,
            Long state,
            String action) {
        if (state.longValue() == ERROR_STATE) return state;
        if (actionIndex(machine, action) < 0) return state;
        return deterministicRawTarget(machine, state, action, true);
    }

    private static Long deterministicRawTarget(
            CompactState machine,
            Long state,
            String action,
            boolean missingIsError) {
        if (state.longValue() == ERROR_STATE) {
            return Long.valueOf(ERROR_STATE);
        }
        if (state.longValue() < 0 || state.longValue() >= machine.maxStates) {
            throw new IllegalArgumentException(
                    "Unknown tester state " + state + " in " + machineName(machine));
        }
        int event = actionIndex(machine, action);
        if (event < 0) return state;
        int[] targets = EventState.nextState(
                machine.states[state.intValue()], event);
        if (targets == null || targets.length == 0) {
            return missingIsError ? Long.valueOf(ERROR_STATE) : state;
        }
        LinkedHashSet<Integer> distinct = new LinkedHashSet<>();
        for (int target : targets) distinct.add(Integer.valueOf(target));
        if (distinct.size() != 1) {
            throw new IllegalArgumentException(
                    "Safety/observer automaton is nondeterministic at "
                            + machineName(machine) + " state " + state
                            + " on " + action + ": " + distinct);
        }
        int target = distinct.iterator().next().intValue();
        if (target < 0) return Long.valueOf(ERROR_STATE);
        if (target >= machine.maxStates) {
            throw new IllegalArgumentException(
                    "Transition leaves tester state space in " + machineName(machine));
        }
        return Long.valueOf(target);
    }

    private static int actionIndex(CompactState machine, String action) {
        if (machine == null || machine.alphabet == null) return -1;
        for (int index = 0; index < machine.alphabet.length; index++) {
            if (action.equals(machine.alphabet[index])) return index;
        }
        return -1;
    }

    /*
     * Imports C, not E || C. buildEndpoint composes this controller exactly
     * once with the versioned component product and the endpoint testers.
     */
    static FiniteLts<Long> importController(
            MTS<Long, String> source,
            Set<String> normalActions,
            String label) {
        if (source == null) {
            throw new IllegalArgumentException(
                    "Missing " + label + " endpoint controller");
        }
        FiniteLts<Long> imported = FiniteLts.fromMtsa(
                new LTSAdapter<Long, String>(
                        source, MTS.TransitionType.REQUIRED));
        FiniteLts.Builder<Long> builder =
                FiniteLts.<Long>builder(imported.initialState())
                        .addStates(imported.states());
        LinkedHashSet<String> alphabet = new LinkedHashSet<>(imported.alphabet());
        alphabet.retainAll(normalActions);
        builder.addActions(sorted(alphabet));
        for (Map.Entry<Long, Map<String, Set<Long>>> stateEntry
                : imported.transitions().entrySet()) {
            for (Map.Entry<String, Set<Long>> actionEntry
                    : stateEntry.getValue().entrySet()) {
                if (!normalActions.contains(actionEntry.getKey())) {
                    throw new IllegalArgumentException(
                            label + " endpoint has a non-normal transition: "
                                    + actionEntry.getKey());
                }
                for (Long target : actionEntry.getValue()) {
                    builder.addTransition(
                            stateEntry.getKey(), actionEntry.getKey(), target);
                }
            }
        }
        return builder.build();
    }

    /**
     * Requires each fixed endpoint controller to observe every event owned by
     * its endpoint environment.  Without this contract, an action absent from
     * the controller alphabet would be treated by {@link #buildEndpoint} as
     * globally disabled even though ordinary synchronous-product semantics
     * lets a non-shared environment action proceed independently.
     */
    static <S, CO, CN> void validateEndpointControllerAlphabets(
            List<VersionedComponent<S>> components,
            FiniteLts<CO> oldController,
            FiniteLts<CN> newController) {
        Objects.requireNonNull(components, "components");
        Objects.requireNonNull(oldController, "oldController");
        Objects.requireNonNull(newController, "newController");

        LinkedHashSet<String> oldEnvironmentActions = new LinkedHashSet<>();
        LinkedHashSet<String> newEnvironmentActions = new LinkedHashSet<>();
        for (VersionedComponent<S> component : components) {
            VersionedComponent<S> checked =
                    Objects.requireNonNull(component, "component");
            oldEnvironmentActions.addAll(checked.oldEnvironmentActions());
            newEnvironmentActions.addAll(checked.newEnvironmentActions());
        }
        requireControllerObservesEnvironment(
                "old", oldEnvironmentActions, oldController.alphabet());
        requireControllerObservesEnvironment(
                "new", newEnvironmentActions, newController.alphabet());
    }

    private static void requireControllerObservesEnvironment(
            String endpoint,
            Set<String> environmentActions,
            Set<String> controllerActions) {
        LinkedHashSet<String> missing =
                new LinkedHashSet<String>(environmentActions);
        missing.removeAll(controllerActions);
        if (!missing.isEmpty()) {
            throw new IllegalArgumentException(
                    "Invalid FG-DUCS endpoint contract: "
                            + endpoint
                            + " controller alphabet omits environment actions "
                            + missing);
        }
    }

    static FiniteLts<EndpointState> buildEndpoint(
            FiniteLts<Long> controller,
            List<VersionedComponent<LocalState>> components,
            List<TesterRecord> testers,
            boolean old,
            Set<String> normalActions) {
        List<FiniteLts<LocalState>> locals = new ArrayList<>();
        List<LocalState> initialLocals = new ArrayList<>();
        for (VersionedComponent<LocalState> component : components) {
            FiniteLts<LocalState> local =
                    old ? component.oldLts() : component.newLts();
            locals.add(local);
            initialLocals.add(local.initialState());
        }
        LinkedHashMap<String, Long> initialTesterStates = new LinkedHashMap<>();
        for (TesterRecord tester : testers) {
            initialTesterStates.put(tester.id, tester.tester.initialState());
        }
        EndpointState initial = new EndpointState(
                controller.initialState(), initialLocals, initialTesterStates);

        LinkedHashSet<String> endpointAlphabet =
                new LinkedHashSet<>(controller.alphabet());
        endpointAlphabet.retainAll(normalActions);
        List<String> orderedActions = sorted(endpointAlphabet);
        FiniteLts.Builder<EndpointState> builder =
                FiniteLts.<EndpointState>builder(initial)
                        .addActions(orderedActions);
        LinkedHashSet<EndpointState> discovered = new LinkedHashSet<>();
        Deque<EndpointState> queue = new ArrayDeque<>();
        discovered.add(initial);
        queue.addLast(initial);

        while (!queue.isEmpty()) {
            EndpointState state = queue.removeFirst();
            for (String action : orderedActions) {
                Set<Long> controllerTargets =
                        controller.successors(state.controllerState, action);
                if (controllerTargets.isEmpty()) continue;
                Set<List<LocalState>> physicalTargets =
                        localProductPost(locals, state.localStates, action);
                if (physicalTargets.isEmpty()) continue;

                LinkedHashMap<String, Long> testerTargets = new LinkedHashMap<>();
                boolean safe = true;
                for (TesterRecord tester : testers) {
                    Long target = tester.tester.stepOrStutter(
                            state.testerStates.get(tester.id), action);
                    testerTargets.put(tester.id, target);
                    if (tester.tester.isError(target)) safe = false;
                }
                if (!safe) {
                    throw new IllegalArgumentException(
                            (old ? "Old" : "New")
                                    + " endpoint violates its safety tester on "
                                    + action + " from " + state);
                }

                for (Long controllerTarget : controllerTargets) {
                    for (List<LocalState> physicalTarget : physicalTargets) {
                        EndpointState target = new EndpointState(
                                controllerTarget, physicalTarget, testerTargets);
                        builder.addTransition(state, action, target);
                        if (discovered.add(target)) queue.addLast(target);
                    }
                }
            }
        }
        return builder.build();
    }

    private static Set<List<LocalState>> localProductPost(
            List<FiniteLts<LocalState>> locals,
            List<LocalState> states,
            String action) {
        List<List<LocalState>> choices = new ArrayList<>();
        boolean participant = false;
        for (int index = 0; index < locals.size(); index++) {
            FiniteLts<LocalState> local = locals.get(index);
            if (local.hasAction(action)) {
                participant = true;
                Set<LocalState> targets = local.successors(states.get(index), action);
                if (targets.isEmpty()) return Collections.emptySet();
                choices.add(new ArrayList<>(targets));
            } else {
                choices.add(Collections.singletonList(states.get(index)));
            }
        }
        if (!participant) return Collections.emptySet();
        LinkedHashSet<List<LocalState>> result = new LinkedHashSet<>();
        cartesian(choices, 0, new ArrayList<LocalState>(), result);
        return result;
    }

    private static <T> void cartesian(
            List<List<T>> choices,
            int index,
            List<T> current,
            Set<List<T>> result) {
        if (index == choices.size()) {
            result.add(Collections.unmodifiableList(new ArrayList<>(current)));
            return;
        }
        for (T choice : choices.get(index)) {
            current.add(choice);
            cartesian(choices, index + 1, current, result);
            current.remove(current.size() - 1);
        }
    }

    static Set<PhysicalState<LocalState>> physicalClosure(
            List<VersionedComponent<LocalState>> components,
            Set<String> normalActions,
            Collection<PhysicalState<LocalState>> roots) {
        int limit = Integer.getInteger(
                "mtsa.revised.otf.maxPhysicalStates",
                DEFAULT_PHYSICAL_CLOSURE_LIMIT).intValue();
        LinkedHashSet<PhysicalState<LocalState>> discovered =
                new LinkedHashSet<>(roots);
        Deque<PhysicalState<LocalState>> queue = new ArrayDeque<>(roots);
        List<String> orderedActions = sorted(normalActions);

        while (!queue.isEmpty()) {
            PhysicalState<LocalState> state = queue.removeFirst();
            for (String action : orderedActions) {
                for (PhysicalState<LocalState> target
                        : physicalPost(components, state, action)) {
                    addPhysical(target, discovered, queue, limit);
                }
            }
            for (int index = 0; index < components.size(); index++) {
                TaggedState<LocalState> local = state.component(index);
                if (!local.isOld()) continue;
                for (LocalState target
                        : components.get(index).transferFrom(local.state())) {
                    addPhysical(
                            state.withComponent(index, TaggedState.newState(target)),
                            discovered, queue, limit);
                }
            }
        }
        return Collections.unmodifiableSet(discovered);
    }

    private static void addPhysical(
            PhysicalState<LocalState> target,
            Set<PhysicalState<LocalState>> discovered,
            Deque<PhysicalState<LocalState>> queue,
            int limit) {
        if (discovered.add(target)) {
            if (discovered.size() > limit) {
                throw new IllegalStateException(
                        "Revised activation-state closure exceeded "
                                + limit + " states; raise "
                                + "-Dmtsa.revised.otf.maxPhysicalStates explicitly");
            }
            queue.addLast(target);
        }
    }

    private static Set<PhysicalState<LocalState>> physicalPost(
            List<VersionedComponent<LocalState>> components,
            PhysicalState<LocalState> state,
            String action) {
        List<List<TaggedState<LocalState>>> choices = new ArrayList<>();
        boolean participant = false;
        for (int index = 0; index < components.size(); index++) {
            TaggedState<LocalState> local = state.component(index);
            VersionedComponent<LocalState> component = components.get(index);
            FiniteLts<LocalState> active = local.isOld()
                    ? component.oldLts()
                    : component.newLts();
            if (component.environmentHasAction(local.version(), action)) {
                participant = true;
            }
            if (active.hasAction(action)) {
                Set<LocalState> targets = active.successors(local.state(), action);
                if (targets.isEmpty()) return Collections.emptySet();
                List<TaggedState<LocalState>> taggedTargets = new ArrayList<>();
                for (LocalState target : targets) {
                    taggedTargets.add(TaggedState.of(local.version(), target));
                }
                choices.add(taggedTargets);
            } else {
                choices.add(Collections.singletonList(local));
            }
        }
        if (!participant) return Collections.emptySet();
        LinkedHashSet<List<TaggedState<LocalState>>> products =
                new LinkedHashSet<>();
        cartesian(choices, 0, new ArrayList<TaggedState<LocalState>>(), products);
        LinkedHashSet<PhysicalState<LocalState>> result = new LinkedHashSet<>();
        for (List<TaggedState<LocalState>> product : products) {
            result.add(PhysicalState.of(product));
        }
        return result;
    }

    static ActivationSpec<LocalState, Long> newActivation(
            TesterRecord tester,
            Set<PhysicalState<LocalState>> domainCandidates,
            List<Observer> observers,
            Map<CompactState, List<CompactState>> safetyComponents,
            Map<CompactState, Map<List<Integer>, Integer>> safetyStateMappings,
            Set<String> commonAlphabet) {
        TableResidualLanguage<Long> residual =
                residualLanguage(tester.tester, commonAlphabet);
        ActivationSpec.Builder<LocalState, Long, Long> builder =
                ActivationSpec.builder(residual);

        List<Integer> observerIndices = observerIndices(
                tester.source, observers, safetyComponents);
        Map<List<Integer>, Integer> stateMapping =
                safetyStateMappings == null ? null
                        : safetyStateMappings.get(tester.source);

        for (PhysicalState<LocalState> physical : domainCandidates) {
            Long activationState = activationState(
                    tester, physical, observerIndices, stateMapping);
            if (activationState == null
                    || tester.tester.isError(activationState)) {
                continue;
            }
            builder.put(physical, activationState, activationState);
        }
        return builder.build();
    }

    private static List<Integer> observerIndices(
            CompactState safety,
            List<Observer> observers,
            Map<CompactState, List<CompactState>> safetyComponents) {
        if (safetyComponents == null) return Collections.emptyList();
        List<CompactState> localObservers = safetyComponents.get(safety);
        if (localObservers == null || localObservers.isEmpty()) {
            return Collections.emptyList();
        }
        List<Integer> indices = new ArrayList<>();
        for (CompactState local : localObservers) {
            int index = observerIdentityIndex(observers, local);
            if (index < 0) {
                index = namedObserverIndex(observers, machineName(local));
            }
            if (index < 0) {
                throw new IllegalArgumentException(
                        "New safety activation references an unknown fluent observer: "
                                + machineName(local));
            }
            indices.add(Integer.valueOf(index));
        }
        return indices;
    }

    private static int observerIdentityIndex(
            List<Observer> values,
            CompactState sought) {
        if (values == null) return -1;
        for (int index = 0; index < values.size(); index++) {
            if (values.get(index).source == sought) return index;
        }
        return -1;
    }

    private static int namedObserverIndex(
            List<Observer> observers,
            String name) {
        int match = -1;
        for (int index = 0; index < observers.size(); index++) {
            if (!observers.get(index).name.equals(name)) continue;
            if (match >= 0) {
                throw new IllegalArgumentException(
                        "Ambiguous fluent observer name: " + name);
            }
            match = index;
        }
        return match;
    }

    static Long activationState(
            TesterRecord tester,
            PhysicalState<LocalState> physical,
            List<Integer> observerIndices,
            Map<List<Integer>, Integer> stateMapping) {
        if (observerIndices.isEmpty() || stateMapping == null) {
            return tester.tester.initialState();
        }
        if (physical.size() == 0) return null;
        List<Long> currentObservers =
                physical.component(0).state().observerStates;
        List<Integer> signature = new ArrayList<>();
        for (Integer index : observerIndices) {
            if (index.intValue() < 0
                    || index.intValue() >= currentObservers.size()) {
                return null;
            }
            signature.add(Integer.valueOf(
                    currentObservers.get(index.intValue()).intValue()));
        }
        Integer mapped = stateMapping.get(signature);
        if (mapped == null) return null;
        Long state = Long.valueOf(mapped.longValue());
        return tester.tester.states().contains(state) ? state : null;
    }

    static ActivationSpec<LocalState, Long> updateActivation(
            TesterRecord tester,
            Set<PhysicalState<LocalState>> oldRoots,
            Set<String> commonAlphabet) {
        if (tester.boundaryState == null
                || tester.tester.isError(tester.boundaryState)) {
            throw new IllegalArgumentException(
                    "Update-time requirement activates in error after hotSwapIn: "
                            + tester.sourceName);
        }
        TableResidualLanguage<Long> residual =
                residualLanguage(tester.tester, commonAlphabet);
        ActivationSpec.Builder<LocalState, Long, Long> builder =
                ActivationSpec.builder(residual);
        for (PhysicalState<LocalState> physical : oldRoots) {
            builder.put(physical, tester.boundaryState, tester.boundaryState);
        }
        return builder.build();
    }

    static List<Integer> observerIndicesForTester(
            TesterRecord tester,
            List<Observer> observers,
            Map<CompactState, List<CompactState>> safetyComponents) {
        return observerIndices(tester.source, observers, safetyComponents);
    }

    static TableResidualLanguage<Long> residualLanguage(
            SafetyTester<Long> tester,
            Set<String> commonAlphabet) {
        TableResidualLanguage.Builder<Long> builder =
                TableResidualLanguage.<Long>builder()
                        .initialState(tester.initialState())
                        .addStates(tester.states())
                        .addActions(sorted(commonAlphabet));
        for (Long error : tester.errorStates()) {
            builder.addErrorState(error);
        }
        for (Long state : tester.states()) {
            for (String action : sorted(commonAlphabet)) {
                builder.addTransition(
                        state, action, tester.stepOrStutter(state, action));
            }
        }
        return builder.build();
    }

    static List<String> sorted(Collection<String> actions) {
        List<String> result = new ArrayList<>(actions);
        Collections.sort(result);
        return result;
    }

    /** Immutable component-local state used by the concrete MTSA adapter. */
    public static final class LocalState {
        private final Long rawState;
        private final List<Long> observerStates;

        LocalState(Long rawState, Collection<Long> observerStates) {
            this.rawState = Objects.requireNonNull(rawState, "rawState");
            List<Long> copy = new ArrayList<>();
            for (Long state : Objects.requireNonNull(
                    observerStates, "observerStates")) {
                copy.add(Objects.requireNonNull(state, "observer state"));
            }
            this.observerStates = Collections.unmodifiableList(copy);
        }

        static LocalState raw(long state) {
            return new LocalState(
                    Long.valueOf(state), Collections.<Long>emptyList());
        }

        public long rawState() {
            return rawState.longValue();
        }

        public List<Long> observerStates() {
            return observerStates;
        }

        @Override
        public boolean equals(Object other) {
            if (this == other) return true;
            if (!(other instanceof LocalState)) return false;
            LocalState that = (LocalState) other;
            return rawState.equals(that.rawState)
                    && observerStates.equals(that.observerStates);
        }

        @Override
        public int hashCode() {
            return Objects.hash(rawState, observerStates);
        }

        @Override
        public String toString() {
            return observerStates.isEmpty()
                    ? rawState.toString()
                    : rawState + "@" + observerStates;
        }
    }

    /** Endpoint state retaining the exact physical and tester projections. */
    public static final class EndpointState {
        private final Long controllerState;
        private final List<LocalState> localStates;
        private final Map<String, Long> testerStates;

        private EndpointState(
                Long controllerState,
                Collection<LocalState> localStates,
                Map<String, Long> testerStates) {
            this.controllerState =
                    Objects.requireNonNull(controllerState, "controllerState");
            this.localStates = Collections.unmodifiableList(
                    new ArrayList<>(localStates));
            this.testerStates = Collections.unmodifiableMap(
                    new LinkedHashMap<>(testerStates));
        }

        PhysicalState<LocalState> physical(boolean old) {
            List<TaggedState<LocalState>> tagged = new ArrayList<>();
            for (LocalState state : localStates) {
                tagged.add(old
                        ? TaggedState.oldState(state)
                        : TaggedState.newState(state));
            }
            return PhysicalState.of(tagged);
        }

        InitialSnapshot<LocalState, Long> oldSnapshot() {
            return new InitialSnapshot<>(physical(true), testerStates);
        }

        GoalSignature<LocalState, Long> newSignature(String endpointId) {
            return new GoalSignature<>(
                    Objects.requireNonNull(endpointId, "endpointId"),
                    physical(false),
                    testerStates);
        }

        public long controllerState() {
            return controllerState.longValue();
        }

        public List<LocalState> localStates() {
            return localStates;
        }

        public Map<String, Long> testerStates() {
            return testerStates;
        }

        @Override
        public boolean equals(Object other) {
            if (this == other) return true;
            if (!(other instanceof EndpointState)) return false;
            EndpointState that = (EndpointState) other;
            return controllerState.equals(that.controllerState)
                    && localStates.equals(that.localStates)
                    && testerStates.equals(that.testerStates);
        }

        @Override
        public int hashCode() {
            return Objects.hash(controllerState, localStates, testerStates);
        }

        @Override
        public String toString() {
            return controllerState + ":" + localStates + ":" + testerStates;
        }
    }

    /** Result retained by tests, CLI runners, and future evaluation tooling. */
    public static final class Outcome {
        private final PreparedInput prepared;
        private final OtfDucsResult<CanonicalUpdateConfiguration<LocalState, Long>,
                String, GoalSignature<LocalState, Long>> result;
        private final LinkedOtfDucsController<EndpointState, LocalState, Long,
                EndpointState> linkedController;

        private Outcome(
                PreparedInput prepared,
                OtfDucsResult<CanonicalUpdateConfiguration<LocalState, Long>,
                        String, GoalSignature<LocalState, Long>> result,
                LinkedOtfDucsController<EndpointState, LocalState, Long,
                        EndpointState> linkedController) {
            this.prepared = prepared;
            this.result = result;
            this.linkedController = linkedController;
        }

        public FineGrainedUpdateProblem<LocalState, Long> problem() {
            return prepared.problem;
        }

        public FiniteLts<EndpointState> oldEndpoint() {
            return prepared.oldEndpoint;
        }

        public FiniteLts<EndpointState> newEndpoint() {
            return prepared.newEndpoint;
        }

        public OtfDucsResult<CanonicalUpdateConfiguration<LocalState, Long>,
                String, GoalSignature<LocalState, Long>> result() {
            return result;
        }

        public LinkedOtfDucsController<EndpointState, LocalState, Long,
                EndpointState> linkedController() {
            return linkedController;
        }
    }

    private static final class PreparedInput {
        private final FineGrainedUpdateProblem<LocalState, Long> problem;
        private final FiniteLts<EndpointState> oldEndpoint;
        private final FiniteLts<EndpointState> newEndpoint;
        private final Map<EndpointState, String> newEndpointIds;
        private final InputCensus census;

        private PreparedInput(
                FineGrainedUpdateProblem<LocalState, Long> problem,
                FiniteLts<EndpointState> oldEndpoint,
                FiniteLts<EndpointState> newEndpoint,
                Map<EndpointState, String> newEndpointIds,
                InputCensus census) {
            this.problem = problem;
            this.oldEndpoint = oldEndpoint;
            this.newEndpoint = newEndpoint;
            this.newEndpointIds = Collections.unmodifiableMap(
                    new LinkedHashMap<>(newEndpointIds));
            this.census = Objects.requireNonNull(census, "census");
        }
    }

    /** Stable input-size census used by the paper-evaluation recorder. */
    private static final class InputCensus {
        private final List<Long> oldStatesByComponent;
        private final List<Long> oldTransitionsByComponent;
        private final List<Long> newStatesByComponent;
        private final List<Long> newTransitionsByComponent;
        private final long oldStatesTotal;
        private final long oldTransitionsTotal;
        private final long newStatesTotal;
        private final long newTransitionsTotal;
        private final long testerStatesTotal;
        private final long testerTransitionsTotal;
        private final long activationDomainEntries;
        private final long transferEdges;
        private final long transferMaxFanOut;
        private final long nondeterministicTransferSources;
        private final long precedenceEdges;
        private final double precedenceDensity;
        private final long reachablePhysicalStates;

        private InputCensus(
                List<Long> oldStatesByComponent,
                List<Long> oldTransitionsByComponent,
                List<Long> newStatesByComponent,
                List<Long> newTransitionsByComponent,
                long testerStatesTotal,
                long testerTransitionsTotal,
                long activationDomainEntries,
                long transferEdges,
                long transferMaxFanOut,
                long nondeterministicTransferSources,
                long precedenceEdges,
                double precedenceDensity,
                long reachablePhysicalStates) {
            this.oldStatesByComponent = immutableLongList(oldStatesByComponent);
            this.oldTransitionsByComponent =
                    immutableLongList(oldTransitionsByComponent);
            this.newStatesByComponent = immutableLongList(newStatesByComponent);
            this.newTransitionsByComponent =
                    immutableLongList(newTransitionsByComponent);
            this.oldStatesTotal = sum(this.oldStatesByComponent);
            this.oldTransitionsTotal = sum(this.oldTransitionsByComponent);
            this.newStatesTotal = sum(this.newStatesByComponent);
            this.newTransitionsTotal = sum(this.newTransitionsByComponent);
            this.testerStatesTotal = testerStatesTotal;
            this.testerTransitionsTotal = testerTransitionsTotal;
            this.activationDomainEntries = activationDomainEntries;
            this.transferEdges = transferEdges;
            this.transferMaxFanOut = transferMaxFanOut;
            this.nondeterministicTransferSources =
                    nondeterministicTransferSources;
            this.precedenceEdges = precedenceEdges;
            this.precedenceDensity = precedenceDensity;
            this.reachablePhysicalStates = reachablePhysicalStates;
        }

        private static InputCensus from(
                List<FiniteLts<Long>> oldComponents,
                List<FiniteLts<Long>> newComponents,
                List<Map<Integer, Set<Integer>>> transfers,
                FineGrainedUpdateProblem<LocalState, Long> problem,
                long reachablePhysicalStates) {
            List<Long> oldStates = new ArrayList<>();
            List<Long> oldTransitions = new ArrayList<>();
            List<Long> newStates = new ArrayList<>();
            List<Long> newTransitions = new ArrayList<>();
            for (FiniteLts<Long> component : oldComponents) {
                oldStates.add(Long.valueOf(component.states().size()));
                oldTransitions.add(Long.valueOf(transitionCount(component)));
            }
            for (FiniteLts<Long> component : newComponents) {
                newStates.add(Long.valueOf(component.states().size()));
                newTransitions.add(Long.valueOf(transitionCount(component)));
            }

            long testerStates = 0;
            long testerTransitions = 0;
            long activationEntries = 0;
            for (Requirement<LocalState, Long> requirement
                    : problem.requirements()) {
                testerStates += requirement.tester().states().size();
                testerTransitions +=
                        transitionCount(requirement.tester().automaton());
                if (requirement.activationSpec().isPresent()) {
                    activationEntries += requirement.requiredActivationSpec()
                            .domain().size();
                }
            }

            long relationEdges = 0;
            long maximumFanOut = 0;
            long nondeterministicSources = 0;
            for (Map<Integer, Set<Integer>> relation : transfers) {
                for (Set<Integer> targets : relation.values()) {
                    long fanOut = targets.size();
                    relationEdges += fanOut;
                    maximumFanOut = Math.max(maximumFanOut, fanOut);
                    if (fanOut > 1) nondeterministicSources++;
                }
            }

            long transitivePrecedenceEdges = 0;
            for (String action : problem.updateActions()) {
                transitivePrecedenceEdges += problem.predecessors(action).size();
            }
            long actionCount = problem.updateActions().size();
            double density = actionCount < 2
                    ? 0.0
                    : transitivePrecedenceEdges
                            / (actionCount * (actionCount - 1) / 2.0);

            return new InputCensus(
                    oldStates, oldTransitions, newStates, newTransitions,
                    testerStates, testerTransitions, activationEntries,
                    relationEdges, maximumFanOut, nondeterministicSources,
                    transitivePrecedenceEdges, density, reachablePhysicalStates);
        }

        private static long transitionCount(FiniteLts<?> lts) {
            long count = 0;
            for (Map<String, ? extends Set<?>> byAction
                    : lts.transitions().values()) {
                for (Set<?> targets : byAction.values()) {
                    count += targets.size();
                }
            }
            return count;
        }

        private static List<Long> immutableLongList(Collection<Long> values) {
            return Collections.unmodifiableList(new ArrayList<>(values));
        }

        private static long sum(Collection<Long> values) {
            long total = 0;
            for (Long value : values) total += value.longValue();
            return total;
        }
    }

    static final class TesterRecord {
        final String id;
        final String sourceName;
        final RequirementRole role;
        final CompactState source;
        final SafetyTester<Long> tester;
        final Long boundaryState;
        String updateAction;

        TesterRecord(
                String id,
                String sourceName,
                RequirementRole role,
                CompactState source,
                SafetyTester<Long> tester,
                Long boundaryState) {
            this.id = id;
            this.sourceName = sourceName;
            this.role = role;
            this.source = source;
            this.tester = tester;
            this.boundaryState = boundaryState;
        }
    }

    static final class Observer {
        final String name;
        final CompactState source;
        final Long initialState;
        final Set<String> alphabet;

        Observer(
                String name,
                CompactState source,
                Long initialState,
                Set<String> alphabet) {
            this.name = name;
            this.source = source;
            this.initialState = initialState;
            this.alphabet = alphabet;
        }

        static Observer from(
                CompactState source,
                Set<String> normalActions) {
            rejectInternalTau(source);
            LinkedHashSet<String> alphabet = new LinkedHashSet<>();
            if (source.alphabet != null) {
                for (String action : source.alphabet) {
                    if (action != null && normalActions.contains(action)) {
                        alphabet.add(action);
                    }
                }
            }
            if (source.maxStates <= 0) {
                throw new IllegalArgumentException(
                        "Fluent observer has no states: " + machineName(source));
            }
            return new Observer(
                    machineName(source),
                    source,
                    Long.valueOf(0L),
                    Collections.unmodifiableSet(alphabet));
        }

        Long stepOrStutter(Long state, String action) {
            if (!alphabet.contains(action)) return state;
            Long target = deterministicRawTarget(
                    source, state, action, false);
            if (target.longValue() == ERROR_STATE) {
                throw new IllegalArgumentException(
                        "Fluent observer reaches ERROR: " + name);
            }
            return target;
        }
    }
}
