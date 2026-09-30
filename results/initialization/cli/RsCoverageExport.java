package ltsa.lts;

import ltsa.control.ControllerGoalDefinition;
import ltsa.lts.ltl.AssertDefinition;
import ltsa.lts.ltl.PredicateDefinition;
import ltsa.lts.ltl.FormulaFactory;
import ltsa.lts.chart.util.FormulaUtils;
import MTSSynthesis.ar.dc.uba.model.condition.Fluent;
import org.json.simple.JSONValue;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

/** Standalone read-only monitor compiler. No controller composition/synthesis is called. */
public final class RsCoverageExport {
    private static List<String> actions(Collection<?> values) {
        List<String> result=new ArrayList<>();
        for(Object value:values)result.add(value.toString());
        Collections.sort(result);return result;
    }
    private static Map<String,Object> export(CompactState machine,String target,String kind,String requirement) throws Exception {
        Map<String,Object> result=new LinkedHashMap<>();
        result.put("target",target);result.put("kind",kind);result.put("requirement",requirement);
        result.put("monitor_nonerror_states",machine.maxStates);result.put("monitor_initial",0);result.put("error_state",-1);
        result.put("alphabet",Arrays.asList(machine.alphabet));
        List<Object> edges=new ArrayList<>();
        for(int state=0;state<machine.maxStates;state++)for(int event=0;event<machine.alphabet.length;event++){
            int[] next=EventState.nextState(machine.states[state],event);
            if(next!=null)for(int to:next)edges.add(Arrays.asList(state,machine.alphabet[event],to));
        }
        result.put("transitions",edges);
        AssertDefinition def=AssertDefinition.getDefinition(requirement);
        if(def==null)def=AssertDefinition.getConstraint(requirement);
        if(def==null)throw new IllegalArgumentException("No formula for "+requirement);
        FormulaFactory factory=new FormulaFactory();
        factory.setFormula(def.getLTLFormula().removeLeftTemporalOperators().expand(factory,new Hashtable(),
            def.getInitParams()==null?new Hashtable():def.getInitParams()));
        Set<Fluent> fluents=new HashSet<>();
        FormulaUtils.adaptFormulaAndCreateFluents(factory.getFormula(),fluents);
        List<Fluent> sorted=new ArrayList<>(fluents);sorted.sort(Comparator.comparing(Fluent::getName));
        List<Object> observerFacts=new ArrayList<>();
        for(Fluent f:sorted){
            Map<String,Object> item=new LinkedHashMap<>();
            item.put("name",f.getName());item.put("initial_value",f.getInitialValue());
            item.put("initiating",actions(f.getInitiatingActions()));item.put("terminating",actions(f.getTerminatingActions()));
            observerFacts.add(item);
        }
        result.put("frontend_lookup_fluents",observerFacts);
        // Read the parser's expanded action sets rather than re-parsing the
        // pretty-printed proposition name (which may contain range/set syntax).
        java.lang.reflect.Field actionField=FormulaFactory.class.getDeclaredField("actionPredicates");
        actionField.setAccessible(true);
        Map actionPredicates=(Map)actionField.get(factory);
        List<Object> referenceObservers=new ArrayList<>();
        for(Object proposition:factory.getProps()){
            String name=proposition.toString();PredicateDefinition predicate=PredicateDefinition.get(name);
            Map<String,Object> item=new LinkedHashMap<>();item.put("name",name);
            if(predicate!=null){
                PredicateDefinition.compile(predicate);item.put("initial_value",predicate.initial()==1);
                item.put("initiating",actions(predicate.getInitiatingActions()));item.put("terminating",actions(predicate.getTerminatingActions()));
                item.put("kind","declared_fluent");
            }else{
                if(actionPredicates==null || !actionPredicates.containsKey(name))throw new IllegalArgumentException("No expanded action predicate "+name);
                item.put("initial_value",false);item.put("initiating",actions((Collection)actionPredicates.get(name)));
                item.put("terminating",Arrays.asList("*"));item.put("kind","event_predicate");
            }
            referenceObservers.add(item);
        }
        result.put("referenced_fluents",referenceObservers);
        result.put("initializer_mode",kind.equals("new")?"fluent_lookup_nonerror_entries":"constant_after_hotSwapIn");
        int begin=-1;for(int i=0;i<machine.alphabet.length;i++)if(machine.alphabet[i].equals("hotSwapIn"))begin=i;
        int boundary=0;
        if(begin>=0){int[] next=EventState.nextState(machine.states[0],begin);if(next==null||next.length==0)boundary=-1;
            else{boundary=next[0];for(int n:next)if(n!=boundary)throw new IllegalArgumentException("Nondeterministic boundary");}}
        result.put("boundary_state_after_hotSwapIn",boundary);
        return result;
    }
    public static void main(String[] args)throws Exception{
        if(args.length!=2)throw new IllegalArgumentException("Usage: model.lts output.json");
        Path input=Paths.get(args[0]);Path output=Paths.get(args[1]);
        LTSOutput quiet=new EmptyLTSOuput();
        LTSCompiler compiler=new LTSCompiler(new LTSInputString(Files.readString(input)),quiet,input.toAbsolutePath().getParent().toString());
        compiler.compile(); // Parsing only: never call continueCompilation or compose.
        PredicateDefinition.compileAll();AssertDefinition.compileAll(quiet);
        List<Object> rows=new ArrayList<>(),contracts=new ArrayList<>();
        Map<String,CompactState> newCache=new HashMap<>(),updateCache=new HashMap<>();
        for(String target:Arrays.asList("base","r1","r2")){
            String definition="UpdCont_OTF_FG"+(target.equals("base")?"":"_"+target.toUpperCase());
            CompositionExpression expression=compiler.getComposites().get(definition);
            if(!(expression instanceof UpdatingControllersDefinition))throw new IllegalArgumentException("Missing "+definition);
            UpdatingControllersDefinition uc=(UpdatingControllersDefinition)expression;
            ControllerGoalDefinition goal=ControllerGoalDefinition.getDefinition(uc.getNewGoal());
            // All selected requirements must be ltl_property. The frontend fallback
            // for process/composite requirements is deliberately not reachable here.
            for(Symbol symbol:goal.getSafetyDefinitions())
                if(AssertDefinition.getConstraint(symbol.getName())==null || LTSCompiler.getProcesses().containsKey(symbol.getName()))
                    throw new IllegalArgumentException("Unsupported non-LTL safety "+symbol.getName());
            if(newCache.isEmpty())for(CompactState machine:CompositionExpression.preProcessSafetyReqs(goal,quiet))newCache.put(machine.name,machine);
            for(Symbol symbol:goal.getSafetyDefinitions())rows.add(export(newCache.get(symbol.getName()),target,"new",symbol.getName()));
            for(Symbol symbol:uc.getTransitionGoals()){
                String name=symbol.getName();if(!updateCache.containsKey(name))updateCache.put(name,AssertDefinition.compileConstraint(quiet,name));
                if(updateCache.get(name)==null)throw new IllegalArgumentException("Missing update property "+name);
                rows.add(export(updateCache.get(name),target,"upd",name));
            }
            Map<String,Object> contract=new LinkedHashMap<>();contract.put("target",target);contract.put("definition",definition);
            contract.put("components",uc.oldEnvironmentForM9().size());contract.put("map_relations",actions(uc.mapRelationsForM9()));
            contract.put("new_monitors",goal.getSafetyDefinitions().size());contract.put("upd_monitors",uc.getTransitionGoals().size());
            contract.put("explicit_precedence_edges",uc.getUpdatePrecedenceEdges().size());
            contract.put("load_selector",uc.hasLoadableNewEndpointStateIndices()?uc.getLoadableNewEndpointStateIndices():"all_reachable_new_endpoint_states");
            contracts.add(contract);
        }
        Map<String,Object> result=new LinkedHashMap<>();result.put("schema","fgducs-rs-monitor-export-v1");
        result.put("source_name",input.getFileName().toString());result.put("controller_synthesis_performed",false);
        result.put("endpoint_products_materialized",false);result.put("requirements",rows);result.put("contracts",contracts);
        Files.writeString(output,JSONValue.toJSONString(result)+"\n",StandardCharsets.UTF_8,StandardOpenOption.CREATE_NEW);
        System.out.println("PARSE_MONITOR_EXPORT_COMPLETE requirements="+rows.size()+" targets="+contracts.size()+" synthesis=false");
    }
}
