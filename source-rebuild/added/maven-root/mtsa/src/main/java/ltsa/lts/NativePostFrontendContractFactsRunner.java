package ltsa.lts;

import MTSTools.ac.ic.doc.commons.relations.Pair;
import MTSTools.ac.ic.doc.mtstools.model.MTS;
import ltsa.updatingControllers.UpdateConstants;
import ltsa.updatingControllers.structures.UpdatingControllerCompositeState;
import org.json.simple.JSONValue;

import java.io.BufferedWriter;
import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Exports the conclusion-free post-frontend contract used by the M8s replay.
 *
 * <p>The shared MTSA loader parses, composes, compiles safety monitors, and
 * synthesizes the fixed old/new controllers.  This exporter records those
 * inputs and stops before endpoint products, activation closure, local games,
 * ownership partitioning, solving, or certificate construction.  In
 * particular, this class must not reference the native factorizer, revised
 * adapter, a solver, or a bundle exporter.</p>
 */
public final class NativePostFrontendContractFactsRunner {

    static final String SCHEMA =
            "fg-ducs-post-frontend-contract-facts-v1";

    private static final Set<String> ROOT_KEYS = immutableSet(
            "schema_version", "evidence_scope", "source_name",
            "source_sha256", "definition", "shared_mtsa_frontend",
            "independent_source_frontend",
            "fixed_endpoint_products_materialized",
            "local_update_games_materialized",
            "global_mixed_game_materialized",
            "old_new_controller_synthesis_performed",
            "source_to_witness_replay", "conclusion_fields_present",
            "flags", "controllable_actions", "components",
            "old_safety_machines", "new_safety_machines",
            "transition_requirement_machines", "observer_machines",
            "protocol", "extraction_stage", "controllers",
            "observer_registry", "new_activation_sources",
            "load_selector", "boundary_actions",
            "physical_closure_materialized",
            "activation_relations_materialized",
            "goal_signatures_materialized",
            "dependency_partition_materialized",
            "winning_certificate_materialized");

    private static final Set<String> FORBIDDEN_CONCLUSION_KEYS = immutableSet(
            "component_partition", "dependency_receipts", "factor_status",
            "solve_status", "winning", "losing", "certificate",
            "strategy", "rank", "witness", "proof", "local_game",
            "endpoint_product", "owner_sets", "action_owners",
            "candidate_buckets", "strategy_buckets", "terminal_assemblies");

    private NativePostFrontendContractFactsRunner() {
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
            Map<String, Object> facts = facts(
                    source,
                    lts.getFileName().toString(),
                    sha256(bytes),
                    definition);
            Path normalized = output.toAbsolutePath().normalize();
            Path outputParent = normalized.getParent();
            if (outputParent != null) {
                Files.createDirectories(outputParent);
            }
            try (BufferedWriter writer = Files.newBufferedWriter(
                    normalized,
                    StandardCharsets.UTF_8,
                    StandardOpenOption.CREATE_NEW,
                    StandardOpenOption.WRITE)) {
                JSONValue.writeJSONString(facts, writer);
                writer.write('\n');
            }
            System.out.println("source_sha256=" + sha256(bytes));
            System.out.println("definition=" + definition);
            System.out.println("conclusion_fields_present=false");
            System.out.println("terminal_record=COMPLETE");
            return 0;
        } catch (IllegalArgumentException error) {
            System.err.println("POST_FRONTEND_FACTS_INVALID="
                    + error.getMessage());
            return 2;
        } catch (Throwable error) {
            System.err.println("POST_FRONTEND_FACTS_ERROR="
                    + error.getClass().getName() + ":" + error.getMessage());
            error.printStackTrace(System.err);
            return 70;
        }
    }

    static Map<String, Object> facts(
            UpdatingControllerCompositeState source,
            String sourceName,
            String sourceSha256,
            String definition) {
        if (source == null) {
            throw new IllegalArgumentException("native source contract is absent");
        }
        LinkedHashMap<String, Object> root =
                new LinkedHashMap<String, Object>(
                        NativeSourceDependencyFactsRunner.facts(
                                source, sourceName, sourceSha256, definition));
        root.put("schema_version", SCHEMA);
        root.put("evidence_scope",
                "shared_mtsa_post_frontend_conclusion_free_contract");
        root.put("extraction_stage",
                "AFTER_FIXED_ENDPOINT_CONTROLLER_SYNTHESIS_BEFORE_ENDPOINT_PRODUCT");
        addCompactInitialStates(root);
        LinkedHashMap<String, Object> controllers =
                new LinkedHashMap<String, Object>();
        controllers.put("old", mtsFact(
                source.getOldController(), "old controller"));
        controllers.put("new", mtsFact(
                source.getNewController(), "new controller"));
        root.put("controllers", controllers);
        List<CompactState> observers = observerRegistryOrder(source);
        root.put("observer_registry", observerRegistry(observers));
        root.put("new_activation_sources",
                newActivationSources(source, observers));
        root.put("load_selector", loadSelector(source));
        LinkedHashMap<String, Object> boundary =
                new LinkedHashMap<String, Object>();
        boundary.put("hot_swap_in", UpdateConstants.BEGIN_UPDATE);
        boundary.put("hot_swap_out", UpdateConstants.FINISH_UPDATE);
        root.put("boundary_actions", boundary);
        root.put("fixed_endpoint_products_materialized", Boolean.FALSE);
        root.put("physical_closure_materialized", Boolean.FALSE);
        root.put("activation_relations_materialized", Boolean.FALSE);
        root.put("goal_signatures_materialized", Boolean.FALSE);
        root.put("local_update_games_materialized", Boolean.FALSE);
        root.put("global_mixed_game_materialized", Boolean.FALSE);
        root.put("dependency_partition_materialized", Boolean.FALSE);
        root.put("winning_certificate_materialized", Boolean.FALSE);
        root.put("source_to_witness_replay", Boolean.FALSE);
        root.put("conclusion_fields_present", Boolean.FALSE);
        validateConclusionFreeRoot(root);
        return root;
    }

    /**
     * Freezes the v1 producer boundary.  The inherited frontend exporter is a
     * useful implementation dependency, but its future root-schema growth must
     * not silently broaden this conclusion-free schema.  The recursive guard
     * separately prevents a known conclusion object from being hidden below an
     * otherwise allowed root field.
     */
    static void validateConclusionFreeRoot(Map<String, Object> root) {
        if (root == null || !ROOT_KEYS.equals(root.keySet())) {
            LinkedHashSet<String> difference =
                    new LinkedHashSet<String>(ROOT_KEYS);
            if (root != null) {
                difference.addAll(root.keySet());
                LinkedHashSet<String> intersection =
                        new LinkedHashSet<String>(ROOT_KEYS);
                intersection.retainAll(root.keySet());
                difference.removeAll(intersection);
            }
            throw new IllegalArgumentException(
                    "post-frontend IR root key census differs: " + difference);
        }
        rejectConclusionKeys(root);
    }

    private static void rejectConclusionKeys(Object value) {
        if (value instanceof Map<?, ?>) {
            for (Map.Entry<?, ?> entry : ((Map<?, ?>) value).entrySet()) {
                if (!(entry.getKey() instanceof String)) {
                    throw new IllegalArgumentException(
                            "post-frontend IR contains a non-text key");
                }
                String key = (String) entry.getKey();
                if (FORBIDDEN_CONCLUSION_KEYS.contains(key)) {
                    throw new IllegalArgumentException(
                            "post-frontend IR contains conclusion field " + key);
                }
                rejectConclusionKeys(entry.getValue());
            }
        }
        else if (value instanceof Iterable<?>) {
            for (Object child : (Iterable<?>) value) {
                rejectConclusionKeys(child);
            }
        }
    }

    private static Set<String> immutableSet(String... values) {
        return Collections.unmodifiableSet(
                new LinkedHashSet<String>(Arrays.asList(values)));
    }

    static Map<String, Object> mtsFact(
            MTS<Long, String> source, String label) {
        if (source == null || source.getInitialState() == null
                || source.getStates() == null || source.getActions() == null) {
            throw new IllegalArgumentException(label + " is incomplete");
        }
        List<Long> states = new ArrayList<Long>(source.getStates());
        List<String> actions = new ArrayList<String>(source.getActions());
        if (states.contains(null) || actions.contains(null)
                || !states.contains(source.getInitialState())) {
            throw new IllegalArgumentException(label + " declarations are invalid");
        }
        Collections.sort(states);
        Collections.sort(actions);
        LinkedHashSet<Long> stateDomain = new LinkedHashSet<Long>(states);
        LinkedHashSet<String> actionDomain = new LinkedHashSet<String>(actions);
        List<Object> transitions = new ArrayList<Object>();
        for (Long state : states) {
            if (!source.getTransitions(state, MTS.TransitionType.MAYBE)
                    .isEmpty()) {
                throw new IllegalArgumentException(
                        label + " contains a MAYBE transition");
            }
            LinkedHashMap<String, Set<Long>> byAction =
                    new LinkedHashMap<String, Set<Long>>();
            for (Pair<String, Long> transition : source.getTransitions(
                    state, MTS.TransitionType.REQUIRED)) {
                if (transition == null
                        || !actionDomain.contains(transition.getFirst())
                        || !stateDomain.contains(transition.getSecond())) {
                    throw new IllegalArgumentException(
                            label + " transition leaves its declared domain");
                }
                Set<Long> targets = byAction.get(transition.getFirst());
                if (targets == null) {
                    targets = new LinkedHashSet<Long>();
                    byAction.put(transition.getFirst(), targets);
                }
                if (!targets.add(transition.getSecond())) {
                    throw new IllegalArgumentException(
                            label + " contains a duplicate transition");
                }
            }
            List<String> enabled = new ArrayList<String>(byAction.keySet());
            Collections.sort(enabled);
            for (String action : enabled) {
                List<Long> targets = new ArrayList<Long>(byAction.get(action));
                Collections.sort(targets);
                LinkedHashMap<String, Object> row =
                        new LinkedHashMap<String, Object>();
                row.put("source", state);
                row.put("action", action);
                row.put("targets", targets);
                transitions.add(row);
            }
        }
        LinkedHashMap<String, Object> result =
                new LinkedHashMap<String, Object>();
        result.put("initial_state", source.getInitialState());
        result.put("states", states);
        result.put("actions", actions);
        result.put("required_transitions", transitions);
        result.put("maybe_transition_count", Long.valueOf(0L));
        return result;
    }

    @SuppressWarnings("unchecked")
    private static void addCompactInitialStates(
            Map<String, Object> root) {
        List<Object> components = (List<Object>) root.get("components");
        for (Object raw : components) {
            Map<String, Object> component = (Map<String, Object>) raw;
            ((Map<String, Object>) component.get("old_machine"))
                    .put("initial_state", Long.valueOf(0L));
            ((Map<String, Object>) component.get("new_machine"))
                    .put("initial_state", Long.valueOf(0L));
        }
        for (String field : new String[]{
                "old_safety_machines", "new_safety_machines",
                "transition_requirement_machines", "observer_machines"}) {
            for (Object raw : (List<Object>) root.get(field)) {
                ((Map<String, Object>) raw).put(
                        "initial_state", Long.valueOf(0L));
            }
        }
    }

    private static List<CompactState> observerRegistryOrder(
            UpdatingControllerCompositeState source) {
        List<CompactState> observers = new ArrayList<CompactState>();
        if (source.getSynthesisMachines() != null) {
            for (CompactState observer : source.getSynthesisMachines()) {
                if (observer != null) observers.add(observer);
            }
        }
        Collections.sort(observers, new Comparator<CompactState>() {
            @Override
            public int compare(CompactState left, CompactState right) {
                return machineName(left).compareTo(machineName(right));
            }
        });
        String previous = null;
        for (CompactState observer : observers) {
            String name = machineName(observer);
            if (name.equals(previous)) {
                throw new IllegalArgumentException(
                        "duplicate observer name " + name);
            }
            previous = name;
        }
        return observers;
    }

    private static List<Object> observerRegistry(
            List<CompactState> observers) {
        List<Object> result = new ArrayList<Object>();
        for (int index = 0; index < observers.size(); index++) {
            LinkedHashMap<String, Object> row =
                    new LinkedHashMap<String, Object>();
            row.put("id", observerId(observers.get(index), index));
            row.put("index", Long.valueOf(index));
            row.put("name", machineName(observers.get(index)));
            Map<String, Object> machine =
                    NativeSourceDependencyFactsRunner.machineFact(
                            observers.get(index));
            machine.put("initial_state", Long.valueOf(0L));
            row.put("machine", machine);
            result.add(row);
        }
        return result;
    }

    private static List<Object> newActivationSources(
            UpdatingControllerCompositeState source,
            List<CompactState> observers) {
        List<CompactState> newSafety = new ArrayList<CompactState>();
        if (source.getNewSafetyLTSs() != null) {
            for (CompactState machine : source.getNewSafetyLTSs()) {
                if (machine != null) newSafety.add(machine);
            }
        }
        Collections.sort(newSafety, new Comparator<CompactState>() {
            @Override
            public int compare(CompactState left, CompactState right) {
                return machineName(left).compareTo(machineName(right));
            }
        });
        Map<CompactState, List<CompactState>> bindings =
                source.getSafetyComponentsMap();
        Map<CompactState, Map<List<Integer>, Integer>> mappings =
                source.getSafetyStateMapping();
        List<Object> result = new ArrayList<Object>();
        String previous = null;
        for (int ordinal = 0; ordinal < newSafety.size(); ordinal++) {
            CompactState safety = newSafety.get(ordinal);
            String name = machineName(safety);
            if (name.equals(previous)) {
                throw new IllegalArgumentException(
                        "duplicate new safety name " + name);
            }
            previous = name;
            List<CompactState> localObservers = bindings == null
                    ? null : bindings.get(safety);
            Map<List<Integer>, Integer> mapping = mappings == null
                    ? null : mappings.get(safety);
            List<Long> indices = new ArrayList<Long>();
            List<String> ids = new ArrayList<String>();
            if (localObservers != null) {
                for (CompactState observer : localObservers) {
                    int index = identityIndex(observers, observer);
                    if (index < 0) {
                        index = uniqueNamedIndex(
                                observers, machineName(observer));
                    }
                    if (index < 0) {
                        throw new IllegalArgumentException(
                                "new activation names an unknown observer");
                    }
                    indices.add(Long.valueOf(index));
                    ids.add(observerId(observers.get(index), index));
                }
            }
            boolean mapped = !indices.isEmpty() && mapping != null;
            LinkedHashMap<String, Object> row =
                    new LinkedHashMap<String, Object>();
            row.put("new_requirement_id",
                    "new:" + name + ":" + ordinal);
            row.put("safety_machine", name);
            row.put("mode", mapped ? "OBSERVER_MAPPING" : "INITIAL");
            row.put("ordered_observer_indices", indices);
            row.put("ordered_observer_ids", ids);
            row.put("mapping_rows", mapped
                    ? mappingRows(name, mapping)
                    : new ArrayList<Object>());
            result.add(row);
        }
        return result;
    }

    private static List<Object> mappingRows(
            String safety,
            Map<List<Integer>, Integer> mapping) {
        for (Map.Entry<List<Integer>, Integer> entry : mapping.entrySet()) {
            List<Integer> signature = entry.getKey();
            if (signature == null || signature.contains(null)
                    || entry.getValue() == null) {
                throw new IllegalArgumentException(
                        "invalid observer signature for " + safety);
            }
        }
        List<List<Integer>> signatures =
                new ArrayList<List<Integer>>(mapping.keySet());
        Collections.sort(signatures, new Comparator<List<Integer>>() {
            @Override
            public int compare(List<Integer> left, List<Integer> right) {
                int limit = Math.min(left.size(), right.size());
                for (int index = 0; index < limit; index++) {
                    int compared = left.get(index).compareTo(right.get(index));
                    if (compared != 0) return compared;
                }
                return Integer.compare(left.size(), right.size());
            }
        });
        List<Object> result = new ArrayList<Object>();
        for (List<Integer> signature : signatures) {
            Integer target = mapping.get(signature);
            LinkedHashMap<String, Object> row =
                    new LinkedHashMap<String, Object>();
            row.put("observer_state_tuple",
                    new ArrayList<Integer>(signature));
            row.put("tester_state", Long.valueOf(target.longValue()));
            result.add(row);
        }
        return result;
    }

    private static int identityIndex(
            List<CompactState> values, CompactState sought) {
        for (int index = 0; index < values.size(); index++) {
            if (values.get(index) == sought) return index;
        }
        return -1;
    }

    private static int uniqueNamedIndex(
            List<CompactState> values, String name) {
        int match = -1;
        for (int index = 0; index < values.size(); index++) {
            if (!machineName(values.get(index)).equals(name)) continue;
            if (match >= 0) {
                throw new IllegalArgumentException(
                        "ambiguous observer name " + name);
            }
            match = index;
        }
        return match;
    }

    private static String observerId(CompactState observer, int index) {
        return "observer:" + machineName(observer) + ":" + index;
    }

    private static Map<String, Object> loadSelector(
            UpdatingControllerCompositeState source) {
        LinkedHashMap<String, Object> result =
                new LinkedHashMap<String, Object>();
        if (!source.hasLoadableNewEndpointStateIndices()) {
            result.put("mode", "ALL_REACHABLE");
            result.put("reachable_indices", new ArrayList<Long>());
            return result;
        }
        List<Integer> indices = new ArrayList<Integer>(
                source.getLoadableNewEndpointStateIndices());
        for (Integer index : indices) {
            if (index == null || index.intValue() < 0) {
                throw new IllegalArgumentException(
                        "load selector indices are invalid");
            }
        }
        Collections.sort(indices);
        List<Long> values = new ArrayList<Long>();
        Integer previous = null;
        for (Integer index : indices) {
            if (index.equals(previous)) {
                throw new IllegalArgumentException(
                        "load selector indices are invalid");
            }
            values.add(Long.valueOf(index.longValue()));
            previous = index;
        }
        if (values.isEmpty()) {
            throw new IllegalArgumentException("load selector is empty");
        }
        result.put("mode", "EXPLICIT_REACHABLE_INDEX");
        result.put("reachable_indices", values);
        return result;
    }

    private static String machineName(CompactState machine) {
        String name = machine == null ? null : machine.getName();
        if (name == null || name.trim().isEmpty()) {
            throw new IllegalArgumentException("machine name is absent");
        }
        return name;
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
