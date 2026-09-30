import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.file.*;
import java.util.*;
import ltsa.updatingControllers.otf.*;

/** Input adapter only. All synthesis, Post, merging, and checking come from the fixed E1 JAR. */
public final class CellRingDriver {
    static final ObjectMapper JSON = new ObjectMapper();
    static final String E1_SHA = "ff1e6b176f004ea85f1e99690a90388a6a4d24f44cd8d8e636fcd9337dcf67d5";
    static final class Fixture {
        final int n;
        final FineGrainedUpdateProblem<String,String> problem;
        final FiniteLts<String> oldEndpoint,newEndpoint,oldController,newController;
        final Map<String,InitialSnapshot<String,String>> oldProjection;
        final Map<String,GoalSignature<String,String>> newProjection;
        Fixture(int n,FineGrainedUpdateProblem<String,String> p,FiniteLts<String> oe,FiniteLts<String> ne,
                FiniteLts<String> oc,FiniteLts<String> nc,Map<String,InitialSnapshot<String,String>> op,
                Map<String,GoalSignature<String,String>> np) {
            this.n=n;problem=p;oldEndpoint=oe;newEndpoint=ne;oldController=oc;newController=nc;
            oldProjection=op;newProjection=np;
        }
    }
    public static void main(String[] args) throws Exception {
        Map<String,String> options=new LinkedHashMap<>();
        for(int i=0;i<args.length;i+=2) {
            if(i+1>=args.length||!args[i].startsWith("--"))throw new IllegalArgumentException("Use --input FILE --merge MODE --solver lazy|direct_full --output FILE, or --validate-n2 FILE --output FILE");
            options.put(args[i],args[i+1]);
        }
        configure();
        if(options.containsKey("--validate-n2")) {
            Map<String,Object> report=validateN2(Paths.get(options.get("--validate-n2")));
            save(Paths.get(required(options,"--output")),report);System.out.println(JSON.writeValueAsString(report));return;
        }
        String merge=required(options,"--merge"),solver=required(options,"--solver");
        if(!Arrays.asList("none","transfers","boundaries","both").contains(merge))throw new IllegalArgumentException("Bad merge mode");
        if(!Arrays.asList("lazy","direct_full").contains(solver))throw new IllegalArgumentException("Bad solver");
        if(solver.equals("direct_full")&&!merge.equals("none"))throw new IllegalArgumentException("DF is preregistered only for none");
        long began=System.nanoTime();Fixture f=load(Paths.get(required(options,"--input")));
        FineGrainedUpdateProblem<String,String> p=f.problem.withContractMerge(merge);
        double preparation=secondsSince(began);
        Map<String,Object> row=solve(f,p,merge,solver,preparation);
        save(Paths.get(required(options,"--output")),row);
        System.out.println(JSON.writeValueAsString(row));
        if(row.get("decision").equals("LOSS"))System.exit(2);
    }
    static void configure() {
        System.setProperty("mtsa.otf.guidedStateLimit","0");System.setProperty("mtsa.otf.guidedQueryLimit","0");
        System.setProperty("mtsa.otf.lazyControllableBuckets","true");
        System.setProperty("mtsa.otf.controllableActionOrder","endpoint_guided");
    }
    static String required(Map<String,String> m,String k){if(!m.containsKey(k))throw new IllegalArgumentException("Missing "+k);return m.get(k);}
    static double secondsSince(long t){return (System.nanoTime()-t)/1e9;}
    static void save(Path path,Object value)throws Exception{Files.createDirectories(path.toAbsolutePath().getParent());Files.write(path,JSON.writerWithDefaultPrettyPrinter().writeValueAsBytes(value),StandardOpenOption.CREATE_NEW);}
    static List<String> strings(JsonNode a){List<String> r=new ArrayList<>();for(JsonNode x:a)r.add(x.asText());return r;}
    static String str(JsonNode a,String k){if(!a.has(k))throw new IllegalArgumentException("Missing data: "+k);return a.get(k).asText();}
    static FiniteLts<String> lts(JsonNode a) {
        FiniteLts.Builder<String> b=FiniteLts.builder(str(a,"initial"));
        for(JsonNode q:a.get("states"))b.addState(q.isTextual()?q.asText():str(q,"id"));
        for(JsonNode e:a.get("edges"))b.addTransition(e.get(0).asText(),e.get(1).asText(),e.get(2).asText());
        return b.build();
    }
    static SafetyTester<String> tester(JsonNode a) {
        SafetyTester.Builder<String> b=SafetyTester.<String>builder().initialState(str(a,"initial")).addErrorState(str(a,"error"));
        for(String q:strings(a.get("states")))for(String action:strings(a.get("alphabet"))) {
            String target=q;
            for(JsonNode e:a.get("changes"))if(e.get(0).asText().equals(q)&&e.get(1).asText().equals(action))target=e.get(2).asText();
            if(q.equals(str(a,"error")))target=q;
            b.addTransition(q,action,target);
        }
        return b.build();
    }
    static ResidualLanguage<String> residual(final SafetyTester<String> t,final Set<String> alphabet) {
        return new ResidualLanguage<String>() {
            public Set<String> states(){return t.states();}public Set<String> alphabet(){return alphabet;}
            public String initialState(){return t.initialState();}public boolean isError(String q){return t.isError(q);}
            public String step(String q,String a){return t.stepOrStutter(q,a);}
        };
    }
    static PhysicalState<String> physical(int n,boolean fresh,int holder) {
        List<TaggedState<String>> values=new ArrayList<>();
        for(int i=0;i<n;i++)values.add(TaggedState.of(fresh?ComponentVersion.NEW:ComponentVersion.OLD,i==holder?"h":"e"));
        return PhysicalState.of(values);
    }
    static Fixture load(Path path)throws Exception {
        JsonNode a=JSON.readTree(path.toFile());
        if(!str(a,"schema").equals("fg-ducs-full-cell-ring-v1"))throw new IllegalArgumentException("Unrecognized schema");
        int n=a.get("n").asInt();if(n<2||n>10)throw new IllegalArgumentException("n outside preregistration");
        if(!str(a.get("activation"),"inspect_domain").equals("all versioned physical products (4^n entries)"))throw new IllegalArgumentException("Unrecognized activation domain");
        FineGrainedUpdateProblem.Builder<String,String> b=FineGrainedUpdateProblem.<String,String>builder()
                .normalActions(strings(a.get("ordinary"))).controllableNormalActions(strings(a.get("controllable")));
        Set<String> alphabet=new LinkedHashSet<>(strings(a.get("ordinary")));
        for(JsonNode c:a.get("components")) {
            Map<String,Set<String>> transfer=new LinkedHashMap<>();
            Iterator<String> keys=c.get("transfer").fieldNames();while(keys.hasNext()){String k=keys.next();transfer.put(k,new LinkedHashSet<>(strings(c.get("transfer").get(k))));}
            b.addComponent(new VersionedComponent<>(str(c,"id"),lts(c.get("old")),lts(c.get("new")),transfer,str(c,"transfer_action")));
            alphabet.add(str(c,"transfer_action"));
        }
        String start=str(a.get("boundaries"),"start"),stop=str(a.get("boundaries"),"stop");alphabet.add(start);alphabet.add(stop);
        SafetyTester<String> old=tester(a.get("requirements").get("old"));
        SafetyTester<String> inspect=tester(a.get("requirements").get("inspect"));
        SafetyTester<String> one=tester(a.get("requirements").get("one"));
        ActivationSpec.Builder<String,String,String> ia=ActivationSpec.builder(residual(inspect,alphabet));
        ActivationSpec.Builder<String,String,String> oa=ActivationSpec.builder(residual(one,alphabet));
        fillActivation(n,0,new ArrayList<TaggedState<String>>(),ia);
        List<String> stations=strings(a.get("stations"));
        for(int i=0;i<n;i++)oa.put(physical(n,false,i),stations.get(i),stations.get(i));
        b.addRequirement(Requirement.oldRequirement("old",old,stop))
         .addRequirement(Requirement.newRequirement("inspect",inspect,ia.build(),start))
         .addRequirement(Requirement.updateTimeRequirement("one",one,oa.build()));
        for(JsonNode e:a.get("boundaries").get("precedence"))b.addPrecedence(e.get(0).asText(),e.get(1).asText());
        FiniteLts<String> oe=lts(a.get("endpoints").get("old")),ne=lts(a.get("endpoints").get("new"));
        Map<String,InitialSnapshot<String,String>> op=new LinkedHashMap<>();
        for(JsonNode q:a.get("endpoints").get("old").get("states"))op.put(str(q,"id"),new InitialSnapshot<>(physical(n,false,q.get("holder").asInt()),Collections.singletonMap("old",str(q,"old"))));
        Map<String,GoalSignature<String,String>> np=new LinkedHashMap<>();
        List<String> load=strings(a.get("endpoints").get("loadable"));List<String> ids=strings(a.get("endpoints").get("goal_ids"));
        for(JsonNode q:a.get("endpoints").get("new").get("states")) {
            String name=str(q,"id"),id=load.contains(name)?ids.get(load.indexOf(name)):name;
            np.put(name,new GoalSignature<>(id,physical(n,true,q.get("holder").asInt()),Collections.singletonMap("inspect",str(q,"inspect"))));
        }
        // Add in the declared order, matching the original fixed Cell fixture.
        for(String q:op.keySet())b.addInitialSnapshot(op.get(q));for(String q:load)b.addGoalSignature(np.get(q));
        return new Fixture(n,b.build(),oe,ne,lts(a.get("controllers").get("old")),lts(a.get("controllers").get("new")),op,np);
    }
    static void fillActivation(int n,int i,List<TaggedState<String>> tuple,ActivationSpec.Builder<String,String,String> b) {
        if(i==n) {
            String state="c";
            for(int k=1;k<n;k++)if(tuple.get(k).state().equals("h")){state=n==2?"d":"d_"+(char)('A'+k);break;}
            b.put(PhysicalState.of(tuple),state,state);return;
        }
        for(ComponentVersion v:ComponentVersion.values())for(String q:Arrays.asList("h","e")) {
            tuple.add(TaggedState.of(v,q));fillActivation(n,i+1,tuple,b);tuple.remove(tuple.size()-1);
        }
    }
    static Map<String,Object> solve(Fixture f,FineGrainedUpdateProblem<String,String> p,String merge,String solver,double preparation) {
        FineGrainedSuccessorOracle<String,String> game=FineGrainedOtfDucs.game(p);
        long began=System.nanoTime();
        OtfDucsResult<CanonicalUpdateConfiguration<String,String>,String,GoalSignature<String,String>> result=
                solver.equals("lazy")?new OtfDucsSynthesizer<>(game).synthesize():new DirectFullStrongSolver<>(game).synthesize();
        double elapsed=secondsSince(began);began=System.nanoTime();
        FineGrainedOtfDucs.verify(p,result).throwIfInvalid();
        Map<String,Object> row=new LinkedHashMap<>();row.put("n",f.n);row.put("merge",merge);row.put("solver",solver);
        row.put("jar_sha256",E1_SHA);row.put("java_version",System.getProperty("java.version"));
        row.put("decision",result.isWinning()?"WIN":"LOSS");
        row.put("states_discovered",result.statistics().discoveredStates());row.put("states_expanded",result.statistics().expandedStates());
        row.put("successor_queries",result.statistics().queriedStateActionPairs());row.put("materialized_transitions",result.statistics().materializedTransitions());
        row.put("enabled_buckets",result.statistics().materializedTransitions());
        row.put("enabled_buckets_definition","all input Post buckets are singleton; materialized transitions equals enabled buckets");
        row.put("preparation_seconds",preparation);row.put("solver_seconds",elapsed);row.put("certificate_checker","PASS");
        row.put("inspection_initializer_entries",1L<<(2*f.n));row.put("one_initializer_entries",f.n);
        if(result.isWinning()) {
            Map<String,Integer> roots=new TreeMap<>();int maximum=0;
            for(Integer rank:result.winningCertificate().ranks().values())maximum=Math.max(maximum,rank);
            for(CanonicalUpdateConfiguration<String,String> q:p.initialConfigurations())roots.put(state(q),result.winningCertificate().ranks().get(q));
            row.put("worst_completion_rank",maximum);row.put("root_ranks",roots);
            row.put("certificate_states",result.winningCertificate().ranks().size());
            row.put("losing_region_states",null);
            LinkedOtfDucsController<String,String,String,String> linked=LinkedOtfDucsController.link(
                    f.oldEndpoint,f.newEndpoint,p,result,f.oldProjection::get,f.newProjection::get);
            row.put("link_checker","PASS");row.put("linked_states",linked.lts().states().size());
        } else {
            row.put("worst_completion_rank",null);row.put("root_ranks",null);
            row.put("losing_region_states",result.losingCertificate().losingStates().size());row.put("link_checker","NOT_APPLICABLE_LOSS");
        }
        row.put("checking_and_link_seconds",secondsSince(began));return row;
    }
    static String state(CanonicalUpdateConfiguration<String,String> q){return q.physicalState()+"|"+new TreeMap<>(q.activeTesterStates())+"|"+new TreeSet<>(q.pendingActions());}
    static void addLts(List<String> lines,String prefix,FiniteLts<String> lts) {
        lines.add(prefix+" initial="+lts.initialState());lines.add(prefix+" states="+new TreeSet<>(lts.states()));lines.add(prefix+" alphabet="+new TreeSet<>(lts.alphabet()));
        for(String q:lts.states())for(String a:lts.alphabet())lines.add(prefix+" "+q+"/"+a+"="+new TreeSet<>(lts.successors(q,a)));
    }
    static List<String> structure(Fixture f) {
        List<String> s=new ArrayList<>();FineGrainedUpdateProblem<String,String> p=f.problem;
        s.add("ordinary="+new TreeSet<>(p.normalActions()));s.add("controllable="+new TreeSet<>(p.controllableActions()));
        for(VersionedComponent<String> c:p.components()) {
            addLts(s,c.id()+" old",c.oldLts());addLts(s,c.id()+" new",c.newLts());
            for(String q:c.oldLts().states())s.add(c.id()+" transfer "+q+"="+new TreeSet<>(c.transferFrom(q)));
            s.add(c.id()+" rho="+c.reconfigureAction());
        }
        for(Requirement<String,String> r:p.requirements()) {
            addLts(s,r.id()+" tester",r.tester().automaton());s.add(r.id()+" errors="+new TreeSet<>(r.tester().errorStates()));
            s.add(r.id()+" role/action="+r.role()+"/"+r.updateAction());
            if(r.role()!=RequirementRole.OLD)for(PhysicalState<String> q:r.requiredActivationSpec().domain())
                s.add(r.id()+" iota "+q+"="+r.requiredActivationSpec().activate(q)+"/"+r.requiredActivationSpec().residualStateAt(q));
        }
        for(String a:p.updateActions())s.add("precedence "+a+"="+new TreeSet<>(p.directPredecessors(a)));
        for(CanonicalUpdateConfiguration<String,String> q:p.initialConfigurations())s.add("root "+state(q));
        for(GoalSignature<String,String> q:p.goalSignatures())s.add("goal "+q);
        addLts(s,"old endpoint",f.oldEndpoint);addLts(s,"new endpoint",f.newEndpoint);
        addLts(s,"old controller",f.oldController);addLts(s,"new controller",f.newController);
        for(Map.Entry<String,InitialSnapshot<String,String>> e:f.oldProjection.entrySet())s.add("old projection "+e.getKey()+"="+e.getValue().physicalState()+"/"+e.getValue().oldRequirementStates());
        for(Map.Entry<String,GoalSignature<String,String>> e:f.newProjection.entrySet())s.add("new projection "+e.getKey()+"="+e.getValue());
        Collections.sort(s);return s;
    }
    static Map<String,Object> validateN2(Path input)throws Exception {
        Fixture generated=load(input),fixed=FixedCellReference.make();
        if(generated.n!=2)throw new IllegalArgumentException("The compatibility check requires n=2");
        List<String> a=structure(generated),b=structure(fixed);
        if(!a.equals(b)){List<String> aa=new ArrayList<>(a);aa.removeAll(b);List<String> bb=new ArrayList<>(b);bb.removeAll(a);throw new AssertionError("primitive/fixture difference generated="+aa+" fixed="+bb);}
        FineGrainedSuccessorOracle<String,String> g=FineGrainedOtfDucs.game(generated.problem),r=FineGrainedOtfDucs.game(fixed.problem);
        IndependentFineGrainedSemantics<String,String> independent=new IndependentFineGrainedSemantics<>(fixed.problem);
        Set<CanonicalUpdateConfiguration<String,String>> seen=new HashSet<>(g.initialStates());Deque<CanonicalUpdateConfiguration<String,String>> todo=new ArrayDeque<>(seen);
        int safe=0,goals=0,nonempty=0,outcomes=0;
        while(!todo.isEmpty()) {
            CanonicalUpdateConfiguration<String,String> q=todo.remove();if(g.isSafe(q))safe++;if(g.isGoal(q))goals++;
            if(g.isGoal(q)!=r.isGoal(q)||g.isSafe(q)!=r.isSafe(q)||g.isGoal(q)!=independent.isGoal(q))throw new AssertionError("state classification mismatch");
            for(String event:generated.problem.commonAlphabet()) {
                Set<CanonicalUpdateConfiguration<String,String>> next=g.post(q,event);
                if(!next.equals(r.post(q,event))||!next.equals(independent.post(q,event)))throw new AssertionError("Post mismatch at "+q+"/"+event);
                if(!next.isEmpty())nonempty++;outcomes+=next.size();for(CanonicalUpdateConfiguration<String,String> t:next)if(seen.add(t))todo.add(t);
            }
        }
        if(seen.size()!=56||safe!=26||goals!=2||nonempty!=139||outcomes!=139)throw new AssertionError("S1 full-closure census mismatch");
        List<Object> comparisons=new ArrayList<>();
        for(String solver:Arrays.asList("lazy","direct_full")) {
            Map<String,Object> gr=solve(generated,generated.problem,"none",solver,0),fr=solve(fixed,fixed.problem,"none",solver,0);
            for(String field:Arrays.asList("decision","root_ranks","worst_completion_rank","states_discovered","successor_queries"))
                if(!Objects.equals(gr.get(field),fr.get(field)))throw new AssertionError(solver+" fixed-reference mismatch: "+field);
            Map<String,Object> c=new LinkedHashMap<>();c.put("solver",solver);c.put("generated",gr);c.put("fixed_reference",fr);comparisons.add(c);
        }
        Map<String,Object> report=new LinkedHashMap<>();report.put("status","PASS");report.put("jar_sha256",E1_SHA);
        report.put("primitive_and_fixed_java_activation_equality",true);report.put("reachable_post_game_equality",true);
        report.put("endpoint_closed_loop_equality",true);report.put("full_closure_states",seen.size());report.put("safe_states",safe);
        report.put("goal_states",goals);report.put("nonempty_buckets",nonempty);report.put("comparisons",comparisons);
        report.put("scope","Reachable S1 game and endpoint identity; unreachable iota completion additionally matches the fixed Java fixture, not a larger paper premise");return report;
    }
}
