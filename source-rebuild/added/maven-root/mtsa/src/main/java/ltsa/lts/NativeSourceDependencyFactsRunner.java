package ltsa.lts;

import ltsa.updatingControllers.UpdateConstants;
import ltsa.updatingControllers.structures.UpdateProtocolSpec;
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
import java.util.Collections;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.Vector;

/**
 * Exports compiled declaration facts for an independent dependency replay.
 *
 * <p>This class deliberately has no direct dependency on the native
 * factorizer, bundle exporter, or revised OTF adapter.  It shares MTSA's
 * parser/composer through {@link NativeUpdatingContractLoader}; that compose
 * path synthesizes the fixed old/new controllers and remains producer TCB.
 * Extraction then stops before fixed-endpoint products, physical closure,
 * local games, or mixed update-game construction.  The exported schema contains no owner,
 * dependency, partition, factor-status, solve-status, or witness field.</p>
 */
public final class NativeSourceDependencyFactsRunner {

    static final String SCHEMA =
            "fg-ducs-native-source-dependency-facts-v1";

    private NativeSourceDependencyFactsRunner() {
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
            System.out.println("component_count="
                    + source.getRawOldEnvironmentComponents().size());
            System.out.println("conclusion_fields_present=false");
            System.out.println("terminal_record=COMPLETE");
            return 0;
        } catch (IllegalArgumentException error) {
            System.err.println("NATIVE_SOURCE_FACTS_INVALID="
                    + error.getMessage());
            return 2;
        } catch (Throwable error) {
            System.err.println("NATIVE_SOURCE_FACTS_ERROR="
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
        if (source == null || source.getUpdateProtocolSpec() == null) {
            throw new IllegalArgumentException(
                    "native source contract or update protocol is absent");
        }
        Vector<CompactState> oldComponents =
                source.getRawOldEnvironmentComponents();
        Vector<CompactState> newComponents =
                source.getRawNewEnvironmentComponents();
        List<Map<Integer, Set<Integer>>> transfers =
                source.getRawTransferRelations();
        List<Boolean> transferKinds =
                source.getTransferRelationsWithActionSequences();
        if (oldComponents.isEmpty()
                || oldComponents.size() != newComponents.size()
                || oldComponents.size() != transfers.size()
                || oldComponents.size() != transferKinds.size()) {
            throw new IllegalArgumentException(
                    "native declaration has an incomplete component mapping");
        }

        UpdateProtocolSpec protocol = source.getUpdateProtocolSpec();
        LinkedHashMap<String, Object> root =
                new LinkedHashMap<String, Object>();
        root.put("schema_version", SCHEMA);
        root.put("evidence_scope",
                "shared_mtsa_frontend_compiled_declaration_facts");
        root.put("source_name", requireText(sourceName, "source name"));
        root.put("source_sha256", requireSha256(sourceSha256));
        root.put("definition", requireText(definition, "definition"));
        root.put("shared_mtsa_frontend", Boolean.TRUE);
        root.put("independent_source_frontend", Boolean.FALSE);
        root.put("fixed_endpoint_products_materialized", Boolean.FALSE);
        root.put("local_update_games_materialized", Boolean.FALSE);
        root.put("global_mixed_game_materialized", Boolean.FALSE);
        root.put("old_new_controller_synthesis_performed", Boolean.TRUE);
        root.put("source_to_witness_replay", Boolean.FALSE);
        root.put("conclusion_fields_present", Boolean.FALSE);
        root.put("flags", flags(source, protocol));
        root.put("controllable_actions",
                sortedStrings(source.getControllableActions()));

        List<Object> components = new ArrayList<Object>();
        for (int index = 0; index < oldComponents.size(); index++) {
            LinkedHashMap<String, Object> row =
                    new LinkedHashMap<String, Object>();
            row.put("index", Long.valueOf(index));
            row.put("old_machine", machineFact(oldComponents.get(index)));
            row.put("new_machine", machineFact(newComponents.get(index)));
            row.put("transfer_relation",
                    transferFact(transfers.get(index)));
            row.put("transfer_has_action_sequence",
                    Boolean.valueOf(Boolean.TRUE.equals(
                            transferKinds.get(index))));
            row.put("reconfigure_action",
                    requireText(protocol.getReconfigureActionForMappingIndex(
                            index), "reconfigure action"));
            components.add(row);
        }
        root.put("components", components);
        root.put("old_safety_machines",
                machineFacts(source.getOldSafetyLTSs()));
        root.put("new_safety_machines",
                machineFacts(source.getNewSafetyLTSs()));
        root.put("transition_requirement_machines",
                machineFacts(source.getTransitionRequirements()));
        root.put("observer_machines",
                machineFacts(source.getSynthesisMachines()));
        root.put("protocol", protocolFact(protocol));
        return root;
    }

    private static Map<String, Object> flags(
            UpdatingControllerCompositeState source,
            UpdateProtocolSpec protocol) {
        LinkedHashMap<String, Object> result =
                new LinkedHashMap<String, Object>();
        result.put("on_the_fly", Boolean.valueOf(source.isOTF()));
        result.put("revised_on_the_fly",
                Boolean.valueOf(source.isRevisedOnTheFly()));
        result.put("fine_grained", Boolean.valueOf(source.isFineGrained()));
        result.put("selective", Boolean.valueOf(protocol.isSelective()));
        result.put("direct_transfer_relations",
                Boolean.valueOf(!source.hasTransferRelationActionSequences()));
        return result;
    }

    private static Map<String, Object> protocolFact(
            UpdateProtocolSpec protocol) {
        LinkedHashMap<String, Object> result =
                new LinkedHashMap<String, Object>();
        result.put("progress_actions_in_index_order",
                new ArrayList<String>(
                        protocol.getProgressActionsInIndexOrder()));
        result.put("stop_old_actions",
                sortedStrings(protocol.getStopOldSpecActions()));
        result.put("reconfigure_actions",
                sortedStrings(protocol.getReconfigureActions()));
        result.put("start_new_actions",
                sortedStrings(protocol.getStartNewSpecActions()));
        result.put("old_safety_to_stop_action",
                sortedStringMap(protocol.getOldSafetyToStopAction()));
        result.put("new_safety_to_start_action",
                sortedStringMap(protocol.getNewSafetyToStartAction()));

        List<Object> actionMappings = new ArrayList<Object>();
        List<String> mappedActions = new ArrayList<String>(
                protocol.getActionToMappingIndices().keySet());
        Collections.sort(mappedActions);
        for (String action : mappedActions) {
            LinkedHashMap<String, Object> row =
                    new LinkedHashMap<String, Object>();
            row.put("action", action);
            row.put("mapping_indices", sortedIntegers(
                    protocol.getActionToMappingIndices().get(action)));
            actionMappings.add(row);
        }
        result.put("action_to_mapping_indices", actionMappings);

        List<UpdateProtocolSpec.PrecedenceEdge> edges =
                new ArrayList<UpdateProtocolSpec.PrecedenceEdge>(
                        protocol.getPrecedenceEdges());
        Collections.sort(edges,
                new Comparator<UpdateProtocolSpec.PrecedenceEdge>() {
                    @Override
                    public int compare(
                            UpdateProtocolSpec.PrecedenceEdge left,
                            UpdateProtocolSpec.PrecedenceEdge right) {
                        int first = left.before().compareTo(right.before());
                        return first != 0 ? first
                                : left.after().compareTo(right.after());
                    }
                });
        List<Object> precedence = new ArrayList<Object>();
        for (UpdateProtocolSpec.PrecedenceEdge edge : edges) {
            LinkedHashMap<String, Object> row =
                    new LinkedHashMap<String, Object>();
            row.put("before", edge.before());
            row.put("after", edge.after());
            precedence.add(row);
        }
        result.put("precedence", precedence);
        return result;
    }

    static Map<String, Object> machineFact(CompactState machine) {
        if (machine == null || machine.maxStates <= 0
                || machine.states == null
                || machine.states.length < machine.maxStates
                || machine.alphabet == null) {
            throw new IllegalArgumentException(
                    "raw declaration machine is incomplete");
        }
        LinkedHashMap<String, Object> result =
                new LinkedHashMap<String, Object>();
        result.put("name", machineName(machine));
        result.put("max_states", Long.valueOf(machine.maxStates));
        List<Object> alphabet = new ArrayList<Object>();
        for (int index = 0; index < machine.alphabet.length; index++) {
            String action = machine.alphabet[index];
            if (action == null || action.isEmpty()) {
                throw new IllegalArgumentException(
                        "raw declaration alphabet contains an empty action");
            }
            alphabet.add(action);
        }
        result.put("alphabet", alphabet);

        List<Object> transitions = new ArrayList<Object>();
        for (int state = 0; state < machine.maxStates; state++) {
            for (int event = 0; event < machine.alphabet.length; event++) {
                int[] rawTargets = EventState.nextState(
                        machine.states[state], event);
                if (rawTargets == null || rawTargets.length == 0) {
                    continue;
                }
                LinkedHashSet<Integer> distinct =
                        new LinkedHashSet<Integer>();
                for (int target : rawTargets) {
                    distinct.add(Integer.valueOf(target));
                }
                List<Integer> targets = new ArrayList<Integer>(distinct);
                Collections.sort(targets);
                LinkedHashMap<String, Object> row =
                        new LinkedHashMap<String, Object>();
                row.put("source", Long.valueOf(state));
                row.put("action_index", Long.valueOf(event));
                row.put("targets", new ArrayList<Integer>(targets));
                transitions.add(row);
            }
        }
        result.put("transitions", transitions);
        return result;
    }

    private static List<Object> machineFacts(
            List<CompactState> machines) {
        List<CompactState> ordered = new ArrayList<CompactState>();
        if (machines != null) {
            for (CompactState machine : machines) {
                if (machine != null) ordered.add(machine);
            }
        }
        Collections.sort(ordered, new Comparator<CompactState>() {
            @Override
            public int compare(CompactState left, CompactState right) {
                return machineName(left).compareTo(machineName(right));
            }
        });
        List<Object> result = new ArrayList<Object>();
        for (CompactState machine : ordered) {
            result.add(machineFact(machine));
        }
        return result;
    }

    private static List<Object> transferFact(
            Map<Integer, Set<Integer>> relation) {
        if (relation == null) {
            throw new IllegalArgumentException("transfer relation is absent");
        }
        List<Integer> sources = new ArrayList<Integer>(relation.keySet());
        Collections.sort(sources);
        List<Object> result = new ArrayList<Object>();
        for (Integer source : sources) {
            LinkedHashMap<String, Object> row =
                    new LinkedHashMap<String, Object>();
            row.put("source", Long.valueOf(source.longValue()));
            row.put("targets", sortedIntegers(relation.get(source)));
            result.add(row);
        }
        return result;
    }

    private static Map<String, Object> sortedStringMap(
            Map<String, String> source) {
        LinkedHashMap<String, Object> result =
                new LinkedHashMap<String, Object>();
        List<String> keys = new ArrayList<String>(source.keySet());
        Collections.sort(keys);
        for (String key : keys) {
            result.put(key, source.get(key));
        }
        return result;
    }

    private static List<String> sortedStrings(Iterable<String> values) {
        LinkedHashSet<String> distinct = new LinkedHashSet<String>();
        if (values != null) {
            for (String value : values) {
                if (value != null) distinct.add(value);
            }
        }
        List<String> result = new ArrayList<String>(distinct);
        Collections.sort(result);
        return result;
    }

    private static List<Long> sortedIntegers(
            Iterable<Integer> values) {
        List<Integer> ordered = new ArrayList<Integer>();
        if (values != null) {
            for (Integer value : values) {
                if (value == null) {
                    throw new IllegalArgumentException(
                            "integer declaration contains null");
                }
                ordered.add(value);
            }
        }
        Collections.sort(ordered);
        List<Long> result = new ArrayList<Long>();
        Integer previous = null;
        for (Integer value : ordered) {
            if (!value.equals(previous)) {
                result.add(Long.valueOf(value.longValue()));
            }
            previous = value;
        }
        return result;
    }

    private static String machineName(CompactState machine) {
        String name = machine == null ? null : machine.getName();
        return name == null || name.trim().isEmpty()
                ? "(unnamed)" : name;
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

    private static String requireText(String value, String label) {
        if (value == null || value.trim().isEmpty()) {
            throw new IllegalArgumentException(label + " is blank");
        }
        return value;
    }

    private static String requireSha256(String value) {
        if (value == null || !value.matches("[0-9a-f]{64}")) {
            throw new IllegalArgumentException("source SHA-256 is invalid");
        }
        return value;
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
