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

/**
 * Exports the checked, typed FG-DUCS result consumed by the reference handoff
 * executor.  The bundle retains pre-update entries, the unquotiented winning
 * strategy, Goal-to-endpoint matches, controller-state loads, and the complete
 * post-update endpoint.  It is deliberately richer than the FSP visualization,
 * which has already quotiented Goal configurations into POST states.
 */
public final class AtomicHandoffBundleExporter {

    public static final String SCHEMA_VERSION =
            "fse2027-atomic-handoff-bundle-v1";

    private AtomicHandoffBundleExporter() {
    }

    public static void write(
            MtsaRevisedOtfDucsAdapter.Outcome outcome,
            Path destination) throws IOException {
        Objects.requireNonNull(destination, "destination");
        Path absolute = destination.toAbsolutePath().normalize();
        Path parent = absolute.getParent();
        if (parent != null) {
            Files.createDirectories(parent);
        }
        if (Files.exists(absolute)) {
            throw new IOException("Refusing to overwrite handoff bundle: " + absolute);
        }
        Map<String, Object> bundle = export(outcome);
        try (BufferedWriter writer = Files.newBufferedWriter(
                absolute,
                StandardCharsets.UTF_8,
                StandardOpenOption.CREATE_NEW,
                StandardOpenOption.WRITE)) {
            JSONValue.writeJSONString(bundle, writer);
            writer.newLine();
        }
    }

    public static Map<String, Object> export(
            MtsaRevisedOtfDucsAdapter.Outcome outcome) {
        Objects.requireNonNull(outcome, "outcome");
        if (!outcome.result().isWinning() || outcome.linkedController() == null) {
            throw new IllegalArgumentException(
                    "Atomic handoff bundles require a checked winning result");
        }

        FineGrainedUpdateProblem<MtsaRevisedOtfDucsAdapter.LocalState, Long> problem =
                outcome.problem();
        OtfDucsResult.WinningCertificate<
                CanonicalUpdateConfiguration<MtsaRevisedOtfDucsAdapter.LocalState, Long>,
                String,
                GoalSignature<MtsaRevisedOtfDucsAdapter.LocalState, Long>> certificate =
                outcome.result().winningCertificate();
        LinkedOtfDucsController<
                MtsaRevisedOtfDucsAdapter.EndpointState,
                MtsaRevisedOtfDucsAdapter.LocalState,
                Long,
                MtsaRevisedOtfDucsAdapter.EndpointState> linked =
                outcome.linkedController();

        List<CanonicalUpdateConfiguration<
                MtsaRevisedOtfDucsAdapter.LocalState, Long>> configurations =
                new ArrayList<CanonicalUpdateConfiguration<
                        MtsaRevisedOtfDucsAdapter.LocalState, Long>>(
                        certificate.ranks().keySet());
        Collections.sort(configurations, configurationComparator());
        Map<CanonicalUpdateConfiguration<
                MtsaRevisedOtfDucsAdapter.LocalState, Long>, String> configurationIds =
                new LinkedHashMap<CanonicalUpdateConfiguration<
                        MtsaRevisedOtfDucsAdapter.LocalState, Long>, String>();
        for (int index = 0; index < configurations.size(); index++) {
            configurationIds.put(configurations.get(index), "M" + index);
        }
        if (!configurationIds.keySet().containsAll(certificate.initialStates())) {
            throw new IllegalStateException("Winning ranks omit an initial configuration");
        }

        List<MtsaRevisedOtfDucsAdapter.EndpointState> oldStates =
                sortedEndpoints(outcome.oldEndpoint().reachableStates());
        List<MtsaRevisedOtfDucsAdapter.EndpointState> postStates =
                sortedEndpoints(outcome.newEndpoint().reachableStates());
        Map<MtsaRevisedOtfDucsAdapter.EndpointState, String> oldIds =
                endpointIds(oldStates, "O");
        Map<MtsaRevisedOtfDucsAdapter.EndpointState, String> postIds =
                endpointIds(postStates, "N");

        validateTypedLink(
                outcome, certificate, configurationIds, oldStates, postStates);

        LinkedHashMap<String, Object> root = new LinkedHashMap<String, Object>();
        root.put("schema_version", SCHEMA_VERSION);
        root.put("hot_swap_in_action", problem.hotSwapInAction());
        root.put("handoff_boundary_name", problem.hotSwapOutAction());
        root.put("controllable_actions", sortedStrings(linked.controllableActions()));
        root.put("initial_configuration_count", certificate.initialStates().size());
        root.put("certificate_state_count", configurations.size());
        root.put("strategy_bucket_count", strategyBucketCount(certificate));
        root.put("strategy_outcome_edge_count", strategyEdgeCount(certificate));
        root.put("goal_count", certificate.goalMatches().size());
        root.put("post_state_count", postStates.size());
        root.put("maximum_rank", maximumRank(certificate));
        root.put("configurations", configurationRecords(
                configurations, configurationIds, certificate));
        root.put("q0_entries", q0Records(
                outcome, oldStates, oldIds, configurationIds));
        root.put("strategy", strategyRecords(
                certificate, configurationIds));
        root.put("handoffs", handoffRecords(
                certificate, linked, configurationIds, postIds));
        root.put("post_states", postRecords(
                outcome.newEndpoint(), postStates, postIds));
        return Collections.unmodifiableMap(root);
    }

    private static void validateTypedLink(
            MtsaRevisedOtfDucsAdapter.Outcome outcome,
            OtfDucsResult.WinningCertificate<
                    CanonicalUpdateConfiguration<MtsaRevisedOtfDucsAdapter.LocalState, Long>,
                    String,
                    GoalSignature<MtsaRevisedOtfDucsAdapter.LocalState, Long>> certificate,
            Map<CanonicalUpdateConfiguration<
                    MtsaRevisedOtfDucsAdapter.LocalState, Long>, String> configurationIds,
            List<MtsaRevisedOtfDucsAdapter.EndpointState> oldStates,
            List<MtsaRevisedOtfDucsAdapter.EndpointState> postStates) {
        LinkedOtfDucsController<
                MtsaRevisedOtfDucsAdapter.EndpointState,
                MtsaRevisedOtfDucsAdapter.LocalState,
                Long,
                MtsaRevisedOtfDucsAdapter.EndpointState> linked =
                outcome.linkedController();
        FiniteLts<LinkedOtfDucsController.State<
                MtsaRevisedOtfDucsAdapter.EndpointState,
                MtsaRevisedOtfDucsAdapter.LocalState,
                Long,
                MtsaRevisedOtfDucsAdapter.EndpointState>> linkedLts = linked.lts();

        Set<CanonicalUpdateConfiguration<
                MtsaRevisedOtfDucsAdapter.LocalState, Long>> coveredRoots =
                new LinkedHashSet<CanonicalUpdateConfiguration<
                        MtsaRevisedOtfDucsAdapter.LocalState, Long>>();
        for (MtsaRevisedOtfDucsAdapter.EndpointState old : oldStates) {
            CanonicalUpdateConfiguration<
                    MtsaRevisedOtfDucsAdapter.LocalState, Long> root =
                    LinkedOtfDucsController.resolveInitial(
                            outcome.problem(), old.oldSnapshot());
            coveredRoots.add(root);
            LinkedOtfDucsController.State<
                    MtsaRevisedOtfDucsAdapter.EndpointState,
                    MtsaRevisedOtfDucsAdapter.LocalState,
                    Long,
                    MtsaRevisedOtfDucsAdapter.EndpointState> source =
                    LinkedOtfDucsController.State.pre(old);
            Set<LinkedOtfDucsController.State<
                    MtsaRevisedOtfDucsAdapter.EndpointState,
                    MtsaRevisedOtfDucsAdapter.LocalState,
                    Long,
                    MtsaRevisedOtfDucsAdapter.EndpointState>> actual =
                    linkedLts.successors(source, outcome.problem().hotSwapInAction());
            LinkedOtfDucsController.State<
                    MtsaRevisedOtfDucsAdapter.EndpointState,
                    MtsaRevisedOtfDucsAdapter.LocalState,
                    Long,
                    MtsaRevisedOtfDucsAdapter.EndpointState> expected =
                    linkedTarget(root, certificate, linked);
            if (!actual.equals(Collections.singleton(expected))) {
                throw new IllegalStateException(
                        "Atomic Link differs at a pre-update entry");
            }
        }
        if (!coveredRoots.equals(certificate.initialStates())) {
            throw new IllegalStateException(
                    "Typed old endpoints do not cover exactly every Q0 configuration");
        }

        for (Map.Entry<CanonicalUpdateConfiguration<
                MtsaRevisedOtfDucsAdapter.LocalState, Long>,
                Map<String, Set<CanonicalUpdateConfiguration<
                        MtsaRevisedOtfDucsAdapter.LocalState, Long>>>> stateEntry
                : certificate.strategy().entrySet()) {
            LinkedOtfDucsController.State<
                    MtsaRevisedOtfDucsAdapter.EndpointState,
                    MtsaRevisedOtfDucsAdapter.LocalState,
                    Long,
                    MtsaRevisedOtfDucsAdapter.EndpointState> source =
                    LinkedOtfDucsController.State.mid(stateEntry.getKey());
            for (Map.Entry<String, Set<CanonicalUpdateConfiguration<
                    MtsaRevisedOtfDucsAdapter.LocalState, Long>>> actionEntry
                    : stateEntry.getValue().entrySet()) {
                LinkedHashSet<LinkedOtfDucsController.State<
                        MtsaRevisedOtfDucsAdapter.EndpointState,
                        MtsaRevisedOtfDucsAdapter.LocalState,
                        Long,
                        MtsaRevisedOtfDucsAdapter.EndpointState>> expected =
                        new LinkedHashSet<LinkedOtfDucsController.State<
                                MtsaRevisedOtfDucsAdapter.EndpointState,
                                MtsaRevisedOtfDucsAdapter.LocalState,
                                Long,
                                MtsaRevisedOtfDucsAdapter.EndpointState>>();
                for (CanonicalUpdateConfiguration<
                        MtsaRevisedOtfDucsAdapter.LocalState, Long> target
                        : actionEntry.getValue()) {
                    if (!configurationIds.containsKey(target)) {
                        throw new IllegalStateException(
                                "Strategy outcome is absent from winning ranks");
                    }
                    expected.add(linkedTarget(target, certificate, linked));
                }
                if (!linkedLts.successors(source, actionEntry.getKey()).equals(expected)) {
                    throw new IllegalStateException(
                            "Atomic Link differs from a certificate event bucket");
                }
            }
        }

        if (!new LinkedHashSet<MtsaRevisedOtfDucsAdapter.EndpointState>(postStates)
                .equals(outcome.newEndpoint().reachableStates())) {
            throw new IllegalStateException("POST state enumeration is incomplete");
        }
    }

    private static LinkedOtfDucsController.State<
            MtsaRevisedOtfDucsAdapter.EndpointState,
            MtsaRevisedOtfDucsAdapter.LocalState,
            Long,
            MtsaRevisedOtfDucsAdapter.EndpointState> linkedTarget(
            CanonicalUpdateConfiguration<
                    MtsaRevisedOtfDucsAdapter.LocalState, Long> target,
            OtfDucsResult.WinningCertificate<
                    CanonicalUpdateConfiguration<MtsaRevisedOtfDucsAdapter.LocalState, Long>,
                    String,
                    GoalSignature<MtsaRevisedOtfDucsAdapter.LocalState, Long>> certificate,
            LinkedOtfDucsController<
                    MtsaRevisedOtfDucsAdapter.EndpointState,
                    MtsaRevisedOtfDucsAdapter.LocalState,
                    Long,
                    MtsaRevisedOtfDucsAdapter.EndpointState> linked) {
        if (!certificate.goalMatches().containsKey(target)) {
            return LinkedOtfDucsController.State.mid(target);
        }
        MtsaRevisedOtfDucsAdapter.EndpointState endpoint =
                linked.quotientTargets().get(target);
        if (endpoint == null) {
            throw new IllegalStateException("Goal lacks a quotient target");
        }
        return LinkedOtfDucsController.State.post(endpoint);
    }

    private static List<Object> configurationRecords(
            List<CanonicalUpdateConfiguration<
                    MtsaRevisedOtfDucsAdapter.LocalState, Long>> configurations,
            Map<CanonicalUpdateConfiguration<
                    MtsaRevisedOtfDucsAdapter.LocalState, Long>, String> ids,
            OtfDucsResult.WinningCertificate<
                    CanonicalUpdateConfiguration<MtsaRevisedOtfDucsAdapter.LocalState, Long>,
                    String,
                    GoalSignature<MtsaRevisedOtfDucsAdapter.LocalState, Long>> certificate) {
        List<Object> records = new ArrayList<Object>();
        for (CanonicalUpdateConfiguration<
                MtsaRevisedOtfDucsAdapter.LocalState, Long> configuration
                : configurations) {
            LinkedHashMap<String, Object> record = new LinkedHashMap<String, Object>();
            record.put("id", ids.get(configuration));
            record.put("rank", certificate.ranks().get(configuration));
            record.put("initial", certificate.initialStates().contains(configuration));
            record.put("goal", certificate.goalMatches().containsKey(configuration));
            record.put("physical_state", configuration.physicalState().toString());
            record.put("active_monitor_states", longMap(
                    configuration.activeTesterStates()));
            record.put("pending_update_actions", sortedStrings(
                    configuration.pendingActions()));
            GoalSignature<MtsaRevisedOtfDucsAdapter.LocalState, Long> goal =
                    certificate.goalMatches().get(configuration);
            if (goal != null) {
                record.put("goal_endpoint_id", goal.endpointId());
            }
            records.add(record);
        }
        return records;
    }

    private static List<Object> q0Records(
            MtsaRevisedOtfDucsAdapter.Outcome outcome,
            List<MtsaRevisedOtfDucsAdapter.EndpointState> oldStates,
            Map<MtsaRevisedOtfDucsAdapter.EndpointState, String> oldIds,
            Map<CanonicalUpdateConfiguration<
                    MtsaRevisedOtfDucsAdapter.LocalState, Long>, String> configurationIds) {
        List<Object> records = new ArrayList<Object>();
        for (MtsaRevisedOtfDucsAdapter.EndpointState state : oldStates) {
            CanonicalUpdateConfiguration<
                    MtsaRevisedOtfDucsAdapter.LocalState, Long> root =
                    LinkedOtfDucsController.resolveInitial(
                            outcome.problem(), state.oldSnapshot());
            LinkedHashMap<String, Object> record = new LinkedHashMap<String, Object>();
            record.put("old_state_id", oldIds.get(state));
            record.put("old_controller_state", state.controllerState());
            record.put("root_configuration", configurationIds.get(root));
            records.add(record);
        }
        return records;
    }

    private static List<Object> strategyRecords(
            OtfDucsResult.WinningCertificate<
                    CanonicalUpdateConfiguration<MtsaRevisedOtfDucsAdapter.LocalState, Long>,
                    String,
                    GoalSignature<MtsaRevisedOtfDucsAdapter.LocalState, Long>> certificate,
            Map<CanonicalUpdateConfiguration<
                    MtsaRevisedOtfDucsAdapter.LocalState, Long>, String> configurationIds) {
        List<Object> records = new ArrayList<Object>();
        List<CanonicalUpdateConfiguration<
                MtsaRevisedOtfDucsAdapter.LocalState, Long>> sources =
                new ArrayList<CanonicalUpdateConfiguration<
                        MtsaRevisedOtfDucsAdapter.LocalState, Long>>(
                        certificate.strategy().keySet());
        Collections.sort(sources, configurationComparator());
        for (CanonicalUpdateConfiguration<
                MtsaRevisedOtfDucsAdapter.LocalState, Long> source : sources) {
            List<String> actions = new ArrayList<String>(
                    certificate.strategy().get(source).keySet());
            Collections.sort(actions);
            for (String action : actions) {
                List<CanonicalUpdateConfiguration<
                        MtsaRevisedOtfDucsAdapter.LocalState, Long>> targets =
                        new ArrayList<CanonicalUpdateConfiguration<
                                MtsaRevisedOtfDucsAdapter.LocalState, Long>>(
                                certificate.strategy().get(source).get(action));
                Collections.sort(targets, configurationComparator());
                List<Object> outcomes = new ArrayList<Object>();
                for (int index = 0; index < targets.size(); index++) {
                    CanonicalUpdateConfiguration<
                            MtsaRevisedOtfDucsAdapter.LocalState, Long> target =
                            targets.get(index);
                    LinkedHashMap<String, Object> outcome =
                            new LinkedHashMap<String, Object>();
                    outcome.put("index", index);
                    outcome.put("target", configurationIds.get(target));
                    outcome.put("goal", certificate.goalMatches().containsKey(target));
                    outcomes.add(outcome);
                }
                LinkedHashMap<String, Object> record =
                        new LinkedHashMap<String, Object>();
                record.put("source", configurationIds.get(source));
                record.put("action", action);
                record.put("outcomes", outcomes);
                records.add(record);
            }
        }
        return records;
    }

    private static List<Object> handoffRecords(
            OtfDucsResult.WinningCertificate<
                    CanonicalUpdateConfiguration<MtsaRevisedOtfDucsAdapter.LocalState, Long>,
                    String,
                    GoalSignature<MtsaRevisedOtfDucsAdapter.LocalState, Long>> certificate,
            LinkedOtfDucsController<
                    MtsaRevisedOtfDucsAdapter.EndpointState,
                    MtsaRevisedOtfDucsAdapter.LocalState,
                    Long,
                    MtsaRevisedOtfDucsAdapter.EndpointState> linked,
            Map<CanonicalUpdateConfiguration<
                    MtsaRevisedOtfDucsAdapter.LocalState, Long>, String> configurationIds,
            Map<MtsaRevisedOtfDucsAdapter.EndpointState, String> postIds) {
        List<CanonicalUpdateConfiguration<
                MtsaRevisedOtfDucsAdapter.LocalState, Long>> goals =
                new ArrayList<CanonicalUpdateConfiguration<
                        MtsaRevisedOtfDucsAdapter.LocalState, Long>>(
                        certificate.goalMatches().keySet());
        Collections.sort(goals, configurationComparator());
        List<Object> records = new ArrayList<Object>();
        for (CanonicalUpdateConfiguration<
                MtsaRevisedOtfDucsAdapter.LocalState, Long> goal : goals) {
            GoalSignature<MtsaRevisedOtfDucsAdapter.LocalState, Long> signature =
                    certificate.goalMatches().get(goal);
            MtsaRevisedOtfDucsAdapter.EndpointState endpoint =
                    linked.quotientTargets().get(goal);
            if (endpoint == null || !postIds.containsKey(endpoint)) {
                throw new IllegalStateException(
                        "Goal handoff target is absent from the new endpoint");
            }
            LinkedHashMap<String, Object> record = new LinkedHashMap<String, Object>();
            record.put("goal_configuration", configurationIds.get(goal));
            record.put("endpoint_id", signature.endpointId());
            record.put("post_state_id", postIds.get(endpoint));
            record.put("controller_state_to_load", endpoint.controllerState());
            records.add(record);
        }
        return records;
    }

    private static List<Object> postRecords(
            FiniteLts<MtsaRevisedOtfDucsAdapter.EndpointState> post,
            List<MtsaRevisedOtfDucsAdapter.EndpointState> states,
            Map<MtsaRevisedOtfDucsAdapter.EndpointState, String> ids) {
        List<Object> records = new ArrayList<Object>();
        for (MtsaRevisedOtfDucsAdapter.EndpointState state : states) {
            LinkedHashMap<String, Object> record = new LinkedHashMap<String, Object>();
            record.put("id", ids.get(state));
            record.put("controller_state", state.controllerState());
            List<String> locals = new ArrayList<String>();
            for (MtsaRevisedOtfDucsAdapter.LocalState local : state.localStates()) {
                locals.add(local.toString());
            }
            record.put("local_states", locals);
            record.put("monitor_states", longMap(state.testerStates()));
            List<Object> transitions = new ArrayList<Object>();
            List<String> actions = new ArrayList<String>(post.enabledActions(state));
            Collections.sort(actions);
            for (String action : actions) {
                List<MtsaRevisedOtfDucsAdapter.EndpointState> targets =
                        sortedEndpoints(post.successors(state, action));
                List<String> targetIds = new ArrayList<String>();
                for (MtsaRevisedOtfDucsAdapter.EndpointState target : targets) {
                    targetIds.add(ids.get(target));
                }
                LinkedHashMap<String, Object> transition =
                        new LinkedHashMap<String, Object>();
                transition.put("action", action);
                transition.put("outcomes", targetIds);
                transitions.add(transition);
            }
            record.put("transitions", transitions);
            records.add(record);
        }
        return records;
    }

    private static int strategyBucketCount(
            OtfDucsResult.WinningCertificate<
                    CanonicalUpdateConfiguration<MtsaRevisedOtfDucsAdapter.LocalState, Long>,
                    String,
                    GoalSignature<MtsaRevisedOtfDucsAdapter.LocalState, Long>> certificate) {
        int count = 0;
        for (Map<String, Set<CanonicalUpdateConfiguration<
                MtsaRevisedOtfDucsAdapter.LocalState, Long>>> buckets
                : certificate.strategy().values()) {
            count += buckets.size();
        }
        return count;
    }

    private static int strategyEdgeCount(
            OtfDucsResult.WinningCertificate<
                    CanonicalUpdateConfiguration<MtsaRevisedOtfDucsAdapter.LocalState, Long>,
                    String,
                    GoalSignature<MtsaRevisedOtfDucsAdapter.LocalState, Long>> certificate) {
        int count = 0;
        for (Map<String, Set<CanonicalUpdateConfiguration<
                MtsaRevisedOtfDucsAdapter.LocalState, Long>>> buckets
                : certificate.strategy().values()) {
            for (Set<?> targets : buckets.values()) {
                count += targets.size();
            }
        }
        return count;
    }

    private static int maximumRank(
            OtfDucsResult.WinningCertificate<
                    CanonicalUpdateConfiguration<MtsaRevisedOtfDucsAdapter.LocalState, Long>,
                    String,
                    GoalSignature<MtsaRevisedOtfDucsAdapter.LocalState, Long>> certificate) {
        int maximum = 0;
        for (Integer rank : certificate.ranks().values()) {
            maximum = Math.max(maximum, rank.intValue());
        }
        return maximum;
    }

    private static Comparator<CanonicalUpdateConfiguration<
            MtsaRevisedOtfDucsAdapter.LocalState, Long>> configurationComparator() {
        return new Comparator<CanonicalUpdateConfiguration<
                MtsaRevisedOtfDucsAdapter.LocalState, Long>>() {
            @Override
            public int compare(
                    CanonicalUpdateConfiguration<
                            MtsaRevisedOtfDucsAdapter.LocalState, Long> left,
                    CanonicalUpdateConfiguration<
                            MtsaRevisedOtfDucsAdapter.LocalState, Long> right) {
                return left.toString().compareTo(right.toString());
            }
        };
    }

    private static List<MtsaRevisedOtfDucsAdapter.EndpointState> sortedEndpoints(
            Set<MtsaRevisedOtfDucsAdapter.EndpointState> states) {
        List<MtsaRevisedOtfDucsAdapter.EndpointState> result =
                new ArrayList<MtsaRevisedOtfDucsAdapter.EndpointState>(states);
        Collections.sort(result, new Comparator<MtsaRevisedOtfDucsAdapter.EndpointState>() {
            @Override
            public int compare(
                    MtsaRevisedOtfDucsAdapter.EndpointState left,
                    MtsaRevisedOtfDucsAdapter.EndpointState right) {
                int controller = Long.compare(
                        left.controllerState(), right.controllerState());
                return controller != 0
                        ? controller
                        : left.toString().compareTo(right.toString());
            }
        });
        return result;
    }

    private static Map<MtsaRevisedOtfDucsAdapter.EndpointState, String> endpointIds(
            List<MtsaRevisedOtfDucsAdapter.EndpointState> states,
            String prefix) {
        LinkedHashMap<MtsaRevisedOtfDucsAdapter.EndpointState, String> ids =
                new LinkedHashMap<MtsaRevisedOtfDucsAdapter.EndpointState, String>();
        for (int index = 0; index < states.size(); index++) {
            ids.put(states.get(index), prefix + index);
        }
        return ids;
    }

    private static List<String> sortedStrings(Set<String> values) {
        List<String> result = new ArrayList<String>(values);
        Collections.sort(result);
        return result;
    }

    private static Map<String, Object> longMap(Map<String, Long> values) {
        List<String> keys = new ArrayList<String>(values.keySet());
        Collections.sort(keys);
        LinkedHashMap<String, Object> result = new LinkedHashMap<String, Object>();
        for (String key : keys) {
            result.put(key, values.get(key));
        }
        return result;
    }
}
