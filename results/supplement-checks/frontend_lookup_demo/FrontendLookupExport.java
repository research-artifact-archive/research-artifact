package ltsa.lts;

import ltsa.lts.ltl.AssertDefinition;
import ltsa.lts.ltl.FormulaFactory;
import ltsa.lts.chart.util.FormulaUtils;
import ltsa.updatingControllers.otf.MtsaRevisedOtfDucsAdapter;
import ltsa.updatingControllers.structures.UpdatingControllerCompositeState;
import MTSSynthesis.ar.dc.uba.model.condition.Fluent;
import org.json.simple.JSONValue;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

/** Export the actual frontend mapping object; never call the FG synthesizer. */
public final class FrontendLookupExport {
    private static List<String> actions(Collection<?> values) {
        List<String> result = new ArrayList<>();
        for (Object value : values) result.add(value.toString());
        Collections.sort(result); return result;
    }

    private static Map<String,Object> machine(CompactState m) {
        Map<String,Object> out = new LinkedHashMap<>();
        out.put("name", m.name); out.put("nonerror_states", m.maxStates);
        out.put("initial_state", 0); out.put("error_state", -1);
        out.put("alphabet", Arrays.asList(m.alphabet));
        List<Object> edges = new ArrayList<>();
        for (int s=0; s<m.maxStates; s++) for (int a=0; a<m.alphabet.length; a++) {
            int[] targets = EventState.nextState(m.states[s], a);
            if (targets != null) for (int t : targets) edges.add(Arrays.asList(s, m.alphabet[a], t));
        }
        out.put("transitions", edges); return out;
    }

    private static Map<String,Fluent> fluents(String requirement) {
        AssertDefinition def = AssertDefinition.getDefinition(requirement);
        if (def == null) def = AssertDefinition.getConstraint(requirement);
        if (def == null) throw new IllegalArgumentException("No formula: " + requirement);
        FormulaFactory factory = new FormulaFactory();
        factory.setFormula(def.getLTLFormula().removeLeftTemporalOperators().expand(factory,
            new Hashtable(), def.getInitParams() == null ? new Hashtable() : def.getInitParams()));
        Set<Fluent> found = new HashSet<>();
        FormulaUtils.adaptFormulaAndCreateFluents(factory.getFormula(), found);
        Map<String,Fluent> result = new TreeMap<>();
        for (Fluent f : found) {
            if (result.put(f.getName(), f) != null) throw new IllegalArgumentException("Duplicate fluent name");
        }
        return result;
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 3) throw new IllegalArgumentException("Usage: model.lts definition output.json");
        Path input = Paths.get(args[0]), destination = Paths.get(args[2]);
        if (Files.exists(destination)) throw new FileAlreadyExistsException(destination.toString());
        LTSOutput log = new LTSOutput() {
            public void out(String s) { System.out.print(s); }
            public void outln(String s) { System.out.println(s); }
            public void clearOutput() { }
        };
        MtsaRevisedOtfDucsAdapter.clearLastOutcomeForCurrentThread();
        LTSCompiler compiler = new LTSCompiler(new LTSInputString(Files.readString(input)), log,
            input.toAbsolutePath().getParent().toString());
        compiler.compile();
        if (!(compiler.getComposites().get(args[1]) instanceof UpdatingControllersDefinition))
            throw new IllegalArgumentException("Exact updating definition missing: " + args[1]);
        // This normal frontend call synthesizes the endpoint controllers and
        // constructs SafetyStateMapping. Do not call applyComposition on its
        // returned updating state: that would start FG synthesis/preparation.
        CompositeState compiled = compiler.continueCompilation(args[1]);
        if (!(compiled instanceof UpdatingControllerCompositeState))
            throw new IllegalStateException("Unexpected compiled state type");
        UpdatingControllerCompositeState source = (UpdatingControllerCompositeState) compiled;
        if (source.wasRevisedOtfDucsExecuted() || source.getRevisedOtfDucsOutcome() != null
                || MtsaRevisedOtfDucsAdapter.lastOutcomeForCurrentThread() != null)
            throw new IllegalStateException("FG synthesis unexpectedly executed");
        Map<CompactState,Map<List<Integer>,Integer>> tables = source.getSafetyStateMapping();
        Map<CompactState,List<CompactState>> components = source.getSafetyComponentsMap();
        if (tables == null || components == null) throw new IllegalStateException("Missing frontend mapping");
        List<CompactState> monitors = new ArrayList<>(source.getNewSafetyLTSs());
        monitors.sort(Comparator.comparing(m -> m.name));
        if (tables.size() != monitors.size()) throw new IllegalStateException("Table/NEW count disagreement");
        List<Object> requirements = new ArrayList<>();
        for (CompactState monitor : monitors) {
            Map<List<Integer>,Integer> table = tables.get(monitor);
            List<CompactState> columns = components.get(monitor);
            if (table == null || columns == null) throw new IllegalStateException("Missing monitor mapping: " + monitor.name);
            Map<String,Fluent> facts = fluents(monitor.name);
            if (facts.size() != columns.size()) throw new IllegalStateException("Observer/formula count differs");
            Map<String,Object> row = new LinkedHashMap<>();
            row.put("requirement", monitor.name); row.put("monitor", machine(monitor));
            List<Object> observers = new ArrayList<>();
            for (CompactState column : columns) {
                Fluent f = facts.get(column.name);
                if (f == null) throw new IllegalStateException("Unknown actual observer: " + column.name);
                Map<String,Object> observer = machine(column);
                observer.put("initial_value", f.getInitialValue());
                observer.put("initiating", actions(f.getInitiatingActions()));
                observer.put("terminating", actions(f.getTerminatingActions()));
                observers.add(observer);
            }
            row.put("observers_in_actual_column_order", observers);
            List<Map<String,Object>> entries = new ArrayList<>();
            for (Map.Entry<List<Integer>,Integer> entry : table.entrySet()) {
                if (entry.getKey().size() != columns.size()) throw new IllegalStateException("Wrong key arity");
                Map<String,Object> item = new LinkedHashMap<>();
                item.put("observer_state_indices", new ArrayList<>(entry.getKey()));
                item.put("monitor_state", entry.getValue()); entries.add(item);
            }
            entries.sort(Comparator.comparing(e -> e.get("observer_state_indices").toString()));
            row.put("actual_lookup_entries", entries); row.put("actual_lookup_entry_count", entries.size());
            requirements.add(row);
        }
        Map<String,Object> result = new LinkedHashMap<>();
        result.put("schema", "fgducs-actual-frontend-lookup-v1");
        result.put("source_name", input.getFileName().toString()); result.put("definition", args[1]);
        result.put("provenance", "Fresh same-input frozen-JAR frontend materialization; not historic process memory");
        result.put("table_source", "UpdatingControllerCompositeState.getSafetyStateMapping()");
        result.put("endpoint_controller_synthesis_performed", true);
        result.put("fg_solver_executed", source.wasRevisedOtfDucsExecuted());
        result.put("physical_closure_or_activation_spec_requested", false);
        result.put("requirements", requirements);
        Files.writeString(destination, JSONValue.toJSONString(result) + "\n", StandardCharsets.UTF_8,
            StandardOpenOption.CREATE_NEW);
        System.out.println("FRONTEND_LOOKUP_EXPORT_COMPLETE requirements=" + requirements.size()
            + " fg_solver=false physical_closure=false activation_spec=false");
    }
}
