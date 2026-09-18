package ltsa.updatingControllers.otf;

import org.json.simple.JSONValue;

import java.io.BufferedWriter;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.TreeMap;

/** Canonical public projection of one source-native Tier-A result. */
public final class NativeTierABundleExporter {

    public static final String SCHEMA_VERSION =
            "fg-ducs-native-tier-a-result-v4";

    private NativeTierABundleExporter() {
        // Utility class.
    }

    public static void write(
            NativeTierAFactorizer.Result result,
            String sourceName,
            String sourceSha256,
            String definition,
            Path destination) throws IOException {
        Objects.requireNonNull(result, "result");
        requireText(sourceName, "source name");
        requireSha256(sourceSha256, "source SHA-256");
        requireText(definition, "definition");
        Objects.requireNonNull(destination, "destination");

        Map<String, Object> root = new LinkedHashMap<String, Object>();
        root.put("schema_version", SCHEMA_VERSION);
        root.put("source_name", sourceName);
        root.put("source_sha256", sourceSha256);
        root.put("definition", definition);
        root.put("extraction_status", "COMPLETE_CONSERVATIVE");
        root.put("claim_scope", "one_way_sufficient_win_only");
        root.put("strategy_model", "finite_memory_local_product");
        root.put("goal_policy",
                "check_original_goal_and_load_before_priority_arbiter");
        root.put("factorization_stage",
                "source_native_before_global_mixed_version_update_game");
        root.put("fixed_endpoint_products_materialized", Boolean.TRUE);
        root.put("factor_status", result.factorStatus());
        root.put("solve_status", result.solveStatus());
        root.put("global_mixed_game_materialized", Boolean.FALSE);
        root.put("global_mixed_state_count", Long.valueOf(0L));
        root.put("global_mixed_post_query_count", Long.valueOf(0L));
        root.put("old_endpoint_state_count",
                Long.valueOf(result.oldEndpointStates()));
        root.put("new_endpoint_state_count",
                Long.valueOf(result.newEndpointStates()));
        root.put("terminal_product_verified",
                Boolean.valueOf(result.terminalProductVerified()));
        Map<String, Object> arbiter = new LinkedHashMap<String, Object>();
        List<Long> blockOrder = new ArrayList<Long>();
        for (int index = 0; index < result.blocks().size(); index++) {
            blockOrder.add(Long.valueOf(index));
        }
        arbiter.put("block_order", blockOrder);
        arbiter.put("original_goal_preempts_local_progress", Boolean.TRUE);
        arbiter.put("uncontrollable_mode", "allow_all_then_wait");
        arbiter.put("shared_controllable_pure_stutter", "disabled");
        root.put("arbiter", arbiter);

        NativeTierAFactorizer.TransportReport transport =
                result.transportReport();
        Map<String, Object> transportRecord =
                new LinkedHashMap<String, Object>();
        transportRecord.put("verified",
                Boolean.valueOf(transport.isVerified()));
        transportRecord.put("activation_tester_count",
                Long.valueOf(transport.activationTesterCount()));
        transportRecord.put("activation_relation_pair_count",
                Long.valueOf(transport.activationRelationPairCount()));
        transportRecord.put("observer_relation_pair_count",
                Long.valueOf(transport.observerRelationPairCount()));
        transportRecord.put("load_selector_signature_count",
                Long.valueOf(transport.loadSelectorSignatureCount()));
        transportRecord.put("load_selector_endpoint_count",
                Long.valueOf(transport.loadSelectorEndpointCount()));
        transportRecord.put("certificate_terminal_tuple_count",
                Long.valueOf(transport.certificateTerminalTupleCount()));
        transportRecord.put("terminal_observer_fiber_count",
                Long.valueOf(transport.terminalObserverFiberCount()));
        List<Object> observerRelations = new ArrayList<Object>();
        for (NativeTierAFactorizer.ObserverRelationReceipt relation
                : transport.observerRelations()) {
            Map<String, Object> record = new LinkedHashMap<String, Object>();
            record.put("block_index", Long.valueOf(relation.blockIndex()));
            record.put("global_observer_indices",
                    new ArrayList<Integer>(relation.globalObserverIndices()));
            List<Object> pairs = new ArrayList<Object>();
            for (NativeTierAFactorizer.ObserverRelationPair pair
                    : relation.pairs()) {
                Map<String, Object> pairRecord =
                        new LinkedHashMap<String, Object>();
                pairRecord.put("global", new ArrayList<Long>(pair.global()));
                pairRecord.put("local", new ArrayList<Long>(pair.local()));
                pairs.add(pairRecord);
            }
            record.put("pairs", pairs);
            observerRelations.add(record);
        }
        transportRecord.put("observer_relations", observerRelations);

        List<Object> loadSelectors = new ArrayList<Object>();
        for (NativeTierAFactorizer.LoadSelectorReceipt selector
                : transport.loadSelectors()) {
            Map<String, Object> record = new LinkedHashMap<String, Object>();
            record.put("endpoint_id", selector.endpointId());
            record.put("controller_state",
                    Long.valueOf(selector.controllerState()));
            record.put("component_raw_states",
                    new ArrayList<Long>(selector.componentRawStates()));
            record.put("observer_states",
                    new ArrayList<Long>(selector.observerStates()));
            record.put("tester_states",
                    new TreeMap<String, Long>(selector.testerStates()));
            loadSelectors.add(record);
        }
        transportRecord.put("load_selectors", loadSelectors);

        List<Object> terminalAssemblies = new ArrayList<Object>();
        for (NativeTierAFactorizer.TerminalAssembly assembly
                : transport.terminalAssemblies()) {
            Map<String, Object> record = new LinkedHashMap<String, Object>();
            record.put("terminal_tuple_index",
                    Long.valueOf(assembly.terminalTupleIndex()));
            record.put("observer_fiber_index",
                    Long.valueOf(assembly.observerFiberIndex()));
            record.put("local_goal_signature_ids",
                    new ArrayList<String>(assembly.localGoalSignatureIds()));
            record.put("global_observer_states",
                    new ArrayList<Long>(assembly.globalObserverStates()));
            record.put("endpoint_id", assembly.endpointId());
            record.put("controller_state",
                    Long.valueOf(assembly.controllerState()));
            terminalAssemblies.add(record);
        }
        transportRecord.put("terminal_assemblies", terminalAssemblies);
        root.put("transport", transportRecord);

        List<Object> blocks = new ArrayList<Object>();
        for (List<Integer> block : result.blocks()) {
            blocks.add(new ArrayList<Integer>(block));
        }
        root.put("component_partition", blocks);

        List<Object> dependencies = new ArrayList<Object>();
        for (NativeTierAFactorizer.DependencyReceipt receipt
                : result.dependencyReceipts()) {
            Map<String, Object> record = new LinkedHashMap<String, Object>();
            record.put("kind", receipt.kind());
            record.put("declaration", receipt.declaration());
            record.put("components",
                    new ArrayList<Integer>(receipt.components()));
            dependencies.add(record);
        }
        root.put("dependency_receipts", dependencies);

        List<Object> localRecords = new ArrayList<Object>();
        long localStates = 0L;
        long localQueries = 0L;
        long localOutcomes = 0L;
        for (NativeTierAFactorizer.LocalResult local : result.locals()) {
            Map<String, Object> record = new LinkedHashMap<String, Object>();
            record.put("block_index", Long.valueOf(local.blockIndex()));
            record.put("components",
                    new ArrayList<Integer>(local.components()));
            record.put("full_goal_count",
                    Long.valueOf(local.fullGoalCount()));
            record.put("quiet_terminal_count",
                    Long.valueOf(local.quietGoalCount()));
            record.put("full_goal_uncontrollable_actions",
                    new ArrayList<String>(
                            local.fullGoalUncontrollableActions()));
            record.put("decision",
                    local.result().isWinning() ? "realizable" : "unrealizable");
            OtfDucsResult.Statistics stats = local.result().statistics();
            record.put("solver_discovered_states",
                    Long.valueOf(stats.discoveredStates()));
            record.put("solver_successor_queries",
                    Long.valueOf(stats.queriedStateActionPairs()));
            record.put("solver_outcomes",
                    Long.valueOf(stats.materializedTransitions()));
            if (local.result().isWinning()) {
                OtfDucsResult.WinningCertificate<?, ?, ?> certificate =
                        local.result().winningCertificate();
                long strategyBuckets = 0L;
                for (Map<?, ?> actions : certificate.strategy().values()) {
                    strategyBuckets += actions.size();
                }
                record.put("certificate_initial_count", Long.valueOf(
                        certificate.initialStates().size()));
                record.put("certificate_rank_count", Long.valueOf(
                        certificate.ranks().size()));
                record.put("certificate_strategy_source_count", Long.valueOf(
                        certificate.strategy().size()));
                record.put("certificate_strategy_bucket_count", Long.valueOf(
                        strategyBuckets));
                record.put("certificate_goal_match_count", Long.valueOf(
                        certificate.goalMatches().size()));
                record.put("proof", winningProof(local));
            } else {
                record.put("certificate_losing_state_count", Long.valueOf(
                        local.result().losingCertificate()
                                .losingStates().size()));
            }
            IndependentExplicitStrongSolver.VerificationReport verification =
                    local.independentVerification();
            record.put("independent_certificate_valid",
                    Boolean.valueOf(verification.isValid()));
            record.put("independent_certificate_basis",
                    verification.basis());
            record.put("independent_certificate_states",
                    Long.valueOf(verification.states()));
            record.put("independent_certificate_queries",
                    Long.valueOf(verification.queries()));
            record.put("independent_certificate_outcomes",
                    Long.valueOf(verification.outcomes()));
            record.put("independent_certificate_elapsed_ms",
                    Long.valueOf(verification.elapsedMillis()));
            localRecords.add(record);
            localStates += stats.discoveredStates();
            localQueries += stats.queriedStateActionPairs();
            localOutcomes += stats.materializedTransitions();
        }
        root.put("locals", localRecords);
        root.put("local_solver_discovered_states_sum",
                Long.valueOf(localStates));
        root.put("local_solver_successor_queries_sum",
                Long.valueOf(localQueries));
        root.put("local_solver_outcomes_sum", Long.valueOf(localOutcomes));

        Path absolute = destination.toAbsolutePath().normalize();
        Path parent = absolute.getParent();
        if (parent != null) Files.createDirectories(parent);
        if (Files.exists(absolute)) {
            throw new IOException(
                    "refusing to overwrite native Tier-A result: " + absolute);
        }
        try (BufferedWriter writer = Files.newBufferedWriter(
                absolute,
                StandardCharsets.UTF_8,
                StandardOpenOption.CREATE_NEW,
                StandardOpenOption.WRITE)) {
            JSONValue.writeJSONString(root, writer);
            writer.newLine();
        }
    }

    private static Map<String, Object> winningProof(
            NativeTierAFactorizer.LocalResult local) {
        FineGrainedUpdateProblem<
                MtsaRevisedOtfDucsAdapter.LocalState, Long> problem =
                local.problem();
        OtfDucsResult.WinningCertificate<
                CanonicalUpdateConfiguration<
                        MtsaRevisedOtfDucsAdapter.LocalState, Long>,
                String,
                GoalSignature<MtsaRevisedOtfDucsAdapter.LocalState, Long>>
                certificate = local.result().winningCertificate();
        IndependentFineGrainedSemantics<
                MtsaRevisedOtfDucsAdapter.LocalState, Long> semantics =
                new IndependentFineGrainedSemantics<
                        MtsaRevisedOtfDucsAdapter.LocalState, Long>(problem);

        List<CanonicalUpdateConfiguration<
                MtsaRevisedOtfDucsAdapter.LocalState, Long>> states =
                new ArrayList<CanonicalUpdateConfiguration<
                        MtsaRevisedOtfDucsAdapter.LocalState, Long>>(
                        certificate.ranks().keySet());
        Collections.sort(states, new Comparator<CanonicalUpdateConfiguration<
                MtsaRevisedOtfDucsAdapter.LocalState, Long>>() {
            @Override public int compare(
                    CanonicalUpdateConfiguration<
                            MtsaRevisedOtfDucsAdapter.LocalState, Long> left,
                    CanonicalUpdateConfiguration<
                            MtsaRevisedOtfDucsAdapter.LocalState, Long> right) {
                return stateKey(left).compareTo(stateKey(right));
            }
        });
        LinkedHashMap<CanonicalUpdateConfiguration<
                MtsaRevisedOtfDucsAdapter.LocalState, Long>, String> ids =
                new LinkedHashMap<CanonicalUpdateConfiguration<
                        MtsaRevisedOtfDucsAdapter.LocalState, Long>, String>();
        for (int index = 0; index < states.size(); index++) {
            ids.put(states.get(index), String.format("q%08d", index));
        }

        Map<String, Object> proof = new LinkedHashMap<String, Object>();
        proof.put("schema_version", "fg-ducs-local-rank-proof-v1");
        proof.put("semantic_basis", "independent_fine_grained_semantics");
        List<String> roots = new ArrayList<String>();
        for (CanonicalUpdateConfiguration<
                MtsaRevisedOtfDucsAdapter.LocalState, Long> root
                : certificate.initialStates()) {
            String id = ids.get(root);
            if (id == null) {
                throw new IllegalArgumentException(
                        "rank proof omits a local initial state");
            }
            roots.add(id);
        }
        Collections.sort(roots);
        proof.put("root_state_ids", roots);

        List<Object> stateRecords = new ArrayList<Object>();
        List<Object> candidateRecords = new ArrayList<Object>();
        List<Object> strategyRecords = new ArrayList<Object>();
        for (CanonicalUpdateConfiguration<
                MtsaRevisedOtfDucsAdapter.LocalState, Long> state : states) {
            String sourceId = ids.get(state);
            Map<String, Object> stateRecord = stateProjection(state);
            stateRecord.put("id", sourceId);
            stateRecord.put("rank", Long.valueOf(
                    certificate.ranks().get(state).longValue()));
            stateRecord.put("safe", Boolean.valueOf(semantics.isSafe(state)));
            stateRecord.put("goal", Boolean.valueOf(semantics.isGoal(state)));
            GoalSignature<MtsaRevisedOtfDucsAdapter.LocalState, Long> goal =
                    certificate.goalMatches().get(state);
            stateRecord.put("goal_signature_id",
                    goal == null ? null : goal.endpointId());
            stateRecord.put("goal_signature",
                    goal == null ? null : goalSignatureProjection(goal));
            stateRecords.add(stateRecord);

            List<String> actions = new ArrayList<String>(
                    semantics.candidateActions(state));
            Collections.sort(actions);
            Map<String, Set<CanonicalUpdateConfiguration<
                    MtsaRevisedOtfDucsAdapter.LocalState, Long>>> retained =
                    certificate.strategy().get(state);
            for (String action : actions) {
                Set<CanonicalUpdateConfiguration<
                        MtsaRevisedOtfDucsAdapter.LocalState, Long>> targets =
                        semantics.post(state, action);
                Map<String, Object> candidate =
                        new LinkedHashMap<String, Object>();
                candidate.put("source", sourceId);
                candidate.put("action", action);
                candidate.put("controllable", Boolean.valueOf(
                        semantics.isControllable(action)));
                candidate.put("update", Boolean.valueOf(
                        problem.updateActions().contains(action)));
                candidate.put("target_keys", sortedTargetKeys(targets));
                candidateRecords.add(candidate);
                if (retained != null && retained.containsKey(action)) {
                    if (!retained.get(action).equals(targets)) {
                        throw new IllegalArgumentException(
                                "retained local bucket differs from independent post");
                    }
                    Map<String, Object> strategy =
                            new LinkedHashMap<String, Object>();
                    strategy.put("source", sourceId);
                    strategy.put("action", action);
                    List<String> targetIds = new ArrayList<String>();
                    for (CanonicalUpdateConfiguration<
                            MtsaRevisedOtfDucsAdapter.LocalState, Long> target
                            : targets) {
                        String targetId = ids.get(target);
                        if (targetId == null) {
                            throw new IllegalArgumentException(
                                    "retained local bucket leaves rank domain");
                        }
                        targetIds.add(targetId);
                    }
                    Collections.sort(targetIds);
                    strategy.put("target_state_ids", targetIds);
                    strategyRecords.add(strategy);
                }
            }
        }
        proof.put("states", stateRecords);
        proof.put("candidate_buckets", candidateRecords);
        proof.put("strategy_buckets", strategyRecords);
        return proof;
    }

    private static Map<String, Object> goalSignatureProjection(
            GoalSignature<MtsaRevisedOtfDucsAdapter.LocalState, Long> goal) {
        Map<String, Object> record = new LinkedHashMap<String, Object>();
        record.put("id", goal.endpointId());
        List<Object> physical = new ArrayList<Object>();
        for (int index = 0; index < goal.physicalState().size(); index++) {
            TaggedState<MtsaRevisedOtfDucsAdapter.LocalState> tagged =
                    goal.physicalState().component(index);
            Map<String, Object> component =
                    new LinkedHashMap<String, Object>();
            component.put("version", tagged.version().name());
            component.put("raw_state",
                    Long.valueOf(tagged.state().rawState()));
            component.put("observer_states",
                    new ArrayList<Long>(tagged.state().observerStates()));
            physical.add(component);
        }
        record.put("physical", physical);
        record.put("new_requirement_states",
                new TreeMap<String, Long>(goal.newRequirementStates()));
        return record;
    }

    private static List<String> sortedTargetKeys(
            Set<CanonicalUpdateConfiguration<
                    MtsaRevisedOtfDucsAdapter.LocalState, Long>> targets) {
        List<String> result = new ArrayList<String>();
        for (CanonicalUpdateConfiguration<
                MtsaRevisedOtfDucsAdapter.LocalState, Long> target : targets) {
            result.add(stateKey(target));
        }
        Collections.sort(result);
        return result;
    }

    private static String stateKey(
            CanonicalUpdateConfiguration<
                    MtsaRevisedOtfDucsAdapter.LocalState, Long> state) {
        return JSONValue.toJSONString(stateProjection(state));
    }

    private static Map<String, Object> stateProjection(
            CanonicalUpdateConfiguration<
                    MtsaRevisedOtfDucsAdapter.LocalState, Long> state) {
        Map<String, Object> record = new LinkedHashMap<String, Object>();
        List<Object> physical = new ArrayList<Object>();
        for (int index = 0; index < state.physicalState().size(); index++) {
            TaggedState<MtsaRevisedOtfDucsAdapter.LocalState> tagged =
                    state.physicalState().component(index);
            Map<String, Object> component =
                    new LinkedHashMap<String, Object>();
            component.put("version", tagged.version().name());
            component.put("raw_state",
                    Long.valueOf(tagged.state().rawState()));
            component.put("observer_states",
                    new ArrayList<Long>(tagged.state().observerStates()));
            physical.add(component);
        }
        record.put("physical", physical);
        Map<String, Object> testers = new LinkedHashMap<String, Object>();
        for (Map.Entry<String, Long> entry
                : new TreeMap<String, Long>(
                        state.activeTesterStates()).entrySet()) {
            testers.put(entry.getKey(), entry.getValue());
        }
        record.put("active_testers", testers);
        List<String> pending =
                new ArrayList<String>(state.pendingActions());
        Collections.sort(pending);
        record.put("pending_actions", pending);
        return record;
    }

    private static void requireText(String value, String label) {
        Objects.requireNonNull(value, label);
        if (value.trim().isEmpty()) {
            throw new IllegalArgumentException(label + " must not be blank");
        }
    }

    private static void requireSha256(String value, String label) {
        requireText(value, label);
        if (!value.matches("[0-9a-f]{64}")) {
            throw new IllegalArgumentException(
                    label + " must be lowercase hexadecimal");
        }
    }
}
