import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;
import ltsa.updatingControllers.otf.*;

/** Finite-input adapter and diagnostics only; every solver/semantics/checker is the fixed E1 JAR. */
public final class WitnessDriver {
    static final ObjectMapper JSON = new ObjectMapper();
    public static final String E1_SHA = "ff1e6b176f004ea85f1e99690a90388a6a4d24f44cd8d8e636fcd9337dcf67d5";
    static final class Fixture {
        JsonNode input;
        FineGrainedUpdateProblem<String,String> problem;
        FiniteLts<String> oldEndpoint,newEndpoint;
        Map<String,InitialSnapshot<String,String>> oldProjection = new LinkedHashMap<>();
        Map<String,GoalSignature<String,String>> newProjection = new LinkedHashMap<>();
    }
    public static void main(String[] args) throws Exception {
        Map<String,String> opt = new LinkedHashMap<>();
        for(int i=0;i<args.length;i+=2) {
            if(i+1==args.length || !args[i].startsWith("--") || opt.put(args[i],args[i+1])!=null)
                throw new IllegalArgumentException("Expected unique --input FILE --merge MODE --solver lazy|direct_full --output FILE options");
        }
        String merge=required(opt,"--merge"),solver=required(opt,"--solver");
        if(!Arrays.asList("none","transfers","boundaries","both").contains(merge))throw new IllegalArgumentException("Unknown merge");
        if(!Arrays.asList("lazy","direct_full").contains(solver))throw new IllegalArgumentException("Unknown solver");
        System.setProperty("mtsa.otf.guidedStateLimit","0");
        System.setProperty("mtsa.otf.guidedQueryLimit","0");
        System.setProperty("mtsa.otf.lazyControllableBuckets",solver.equals("lazy")?"true":"false");
        System.setProperty("mtsa.otf.controllableActionOrder","endpoint_guided");
        long begin=System.nanoTime(); Path input=Paths.get(required(opt,"--input"));
        Fixture fixture=load(input);
        FineGrainedUpdateProblem<String,String> problem=fixture.problem.withContractMerge(merge);
        EndpointContractValidator.validate(fixture.oldEndpoint,fixture.newEndpoint,problem,fixture.oldProjection::get,fixture.newProjection::get);
        double preparation=elapsed(begin);
        Map<String,Object> equivalence=null;
        if(opt.containsKey("--compare-input")) {
            Fixture other=load(Paths.get(opt.get("--compare-input")));
            equivalence=compareGames(problem,other.problem.withContractMerge(opt.getOrDefault("--compare-merge","none")));
        }
        Map<String,Object> result=solve(fixture,problem,merge,solver,preparation);
        result.put("input_sha256",sha(input));
        if(equivalence!=null)result.put("game_equivalence",equivalence);
        Path output=Paths.get(required(opt,"--output"));
        Path certificate=output.toAbsolutePath().getParent().resolve("certificate.json");
        Object proof=result.remove("_certificate");
        save(certificate,proof);result.put("certificate_file",certificate.getFileName().toString());
        result.put("certificate_sha256",sha(certificate));
        save(output,result);System.out.println(JSON.writeValueAsString(result));
        if("LOSS".equals(result.get("decision")))System.exit(2);
    }
    static String required(Map<String,String> x,String k){if(!x.containsKey(k))throw new IllegalArgumentException("Missing "+k);return x.get(k);}
    static double elapsed(long start){return (System.nanoTime()-start)/1e9;}
    static void save(Path p,Object value)throws Exception {
        Files.createDirectories(p.toAbsolutePath().getParent());
        Files.write(p,JSON.writerWithDefaultPrettyPrinter().writeValueAsBytes(value),StandardOpenOption.CREATE_NEW);
    }
    static String sha(Path p)throws Exception {
        MessageDigest h=MessageDigest.getInstance("SHA-256");
        try(java.io.InputStream in=Files.newInputStream(p)){byte[] b=new byte[1048576];int n;while((n=in.read(b))>=0)h.update(b,0,n);}
        StringBuilder s=new StringBuilder();for(byte b:h.digest())s.append(String.format("%02x",b&255));return s.toString();
    }
    static String str(JsonNode x,String k){JsonNode v=x.get(k);if(v==null||!v.isTextual()||v.asText().isEmpty())throw new IllegalArgumentException("Expected nonempty string "+k);return v.asText();}
    static List<String> strings(JsonNode x) {
        if(x==null||!x.isArray())throw new IllegalArgumentException("Expected string array");
        List<String> v=new ArrayList<>();for(JsonNode n:x){if(!n.isTextual())throw new IllegalArgumentException("Expected string");v.add(n.asText());}return v;
    }
    static List<String> uniqueStrings(JsonNode x){List<String> r=strings(x);if(new HashSet<>(r).size()!=r.size())throw new IllegalArgumentException("Duplicate string array entry");return r;}
    static FiniteLts<String> lts(JsonNode x) {
        List<String> states=uniqueStrings(x.get("states"));String initial=str(x,"initial");
        if(!states.contains(initial))throw new IllegalArgumentException("LTS initial not in states");
        FiniteLts.Builder<String> b=FiniteLts.builder(initial);for(String s:states)b.addState(s);
        Set<List<String>> edges=new HashSet<>();
        for(JsonNode e:x.get("edges")) {
            List<String> t=strings(e);
            if(t.size()!=3||!states.contains(t.get(0))||!states.contains(t.get(2))||!edges.add(t))throw new IllegalArgumentException("Invalid/duplicate LTS edge "+t);
            b.addTransition(t.get(0),t.get(1),t.get(2));
        }
        return b.build();
    }
    static SafetyTester<String> tester(JsonNode x) {
        List<String> states=uniqueStrings(x.get("states")),actions=uniqueStrings(x.get("alphabet"));
        Set<String> errors=new LinkedHashSet<>(uniqueStrings(x.get("errors")));
        if(!states.containsAll(errors)||!states.contains(str(x,"initial")))throw new IllegalArgumentException("Unknown tester state");
        Map<List<String>,String> changes=new LinkedHashMap<>();
        for(JsonNode e:x.get("changes")) {
            List<String> t=strings(e);
            if(t.size()!=3||!states.contains(t.get(0))||!states.contains(t.get(2))||!actions.contains(t.get(1)))throw new IllegalArgumentException("Unknown tester transition");
            if(changes.put(t.subList(0,2),t.get(2))!=null)throw new IllegalArgumentException("Duplicate tester transition");
            if(errors.contains(t.get(0))&&!errors.contains(t.get(2)))throw new IllegalArgumentException("Error not absorbing");
        }
        SafetyTester.Builder<String> b=SafetyTester.<String>builder().initialState(str(x,"initial")).addStates(states).addActions(actions);
        for(String e:errors)b.addErrorState(e);
        for(String q:states)for(String a:actions)b.addTransition(q,a,changes.getOrDefault(Arrays.asList(q,a),q));
        return b.build();
    }
    static ResidualLanguage<String> residual(final SafetyTester<String> t) {
        return new ResidualLanguage<String>() {
            public Set<String> states(){return t.states();}public Set<String> alphabet(){return t.alphabet();}
            public String initialState(){return t.initialState();}public boolean isError(String q){return t.isError(q);}
            public String step(String q,String a){return t.stepOrStutter(q,a);}
        };
    }
    static PhysicalState<String> physical(JsonNode x) {
        List<TaggedState<String>> tuple=new ArrayList<>();
        for(JsonNode t:x) {
            List<String> v=strings(t);if(v.size()!=2)throw new IllegalArgumentException("Physical coordinate must be [OLD|NEW,state]");
            tuple.add(TaggedState.of(ComponentVersion.valueOf(v.get(0)),v.get(1)));
        }
        return PhysicalState.of(tuple);
    }
    static Map<String,String> stringMap(JsonNode x) {
        if(x==null||!x.isObject())throw new IllegalArgumentException("Expected tester-state object");
        Map<String,String> out=new LinkedHashMap<>();Iterator<String> keys=x.fieldNames();while(keys.hasNext()){String k=keys.next();out.put(k,str(x,k));}return out;
    }
    static Fixture load(Path path)throws Exception {
        JsonNode input=JSON.readTree(path.toFile());if(!str(input,"schema").equals("fg-ducs-witness-v1"))throw new IllegalArgumentException("Wrong schema");
        Fixture f=new Fixture();f.input=input;
        FineGrainedUpdateProblem.Builder<String,String> b=FineGrainedUpdateProblem.<String,String>builder()
            .normalActions(uniqueStrings(input.get("ordinary"))).controllableNormalActions(uniqueStrings(input.get("controllable")));
        if(input.has("generated_contract_mode"))GeneratedContractInput.allowGroups(b,str(input,"generated_contract_mode"));
        for(JsonNode c:input.get("components")) {
            Map<String,Set<String>> transfer=new LinkedHashMap<>();Iterator<String> keys=c.get("transfer").fieldNames();
            while(keys.hasNext()){String q=keys.next();transfer.put(q,new LinkedHashSet<>(uniqueStrings(c.get("transfer").get(q))));}
            b.addComponent(new VersionedComponent<>(str(c,"id"),lts(c.get("old")),lts(c.get("new")),transfer,str(c,"transfer_action")));
        }
        for(JsonNode r:input.get("requirements")) {
            String id=str(r,"id"),role=str(r,"role");SafetyTester<String> test=tester(r.get("tester"));
            if(role.equals("old")){b.addRequirement(Requirement.oldRequirement(id,test,str(r,"update_action")));continue;}
            JsonNode a=r.get("activation");SafetyTester<String> residualTester=a.has("residual")?tester(a.get("residual")):test;
            ActivationSpec.Builder<String,String,String> ab=ActivationSpec.builder(residual(residualTester));
            for(JsonNode entry:a.get("entries"))ab.put(physical(entry.get("physical")),str(entry,"tester_state"),str(entry,"residual_state"));
            if(role.equals("new"))b.addRequirement(Requirement.newRequirement(id,test,ab.build(),str(r,"update_action")));
            else if(role.equals("interval"))b.addRequirement(Requirement.updateTimeRequirement(id,test,ab.build()));
            else throw new IllegalArgumentException("Unknown role "+role);
        }
        for(JsonNode e:input.get("precedence")){List<String> edge=strings(e);if(edge.size()!=2)throw new IllegalArgumentException("Precedence edge length");b.addPrecedence(edge.get(0),edge.get(1));}
        JsonNode old=input.get("endpoints").get("old"),fresh=input.get("endpoints").get("new");
        f.oldEndpoint=lts(old.get("lts"));f.newEndpoint=lts(fresh.get("lts"));
        Iterator<String> keys=old.get("projection").fieldNames();
        while(keys.hasNext()){String q=keys.next();JsonNode v=old.get("projection").get(q);f.oldProjection.put(q,new InitialSnapshot<>(physical(v.get("physical")),stringMap(v.get("testers"))));}
        keys=fresh.get("projection").fieldNames();
        while(keys.hasNext()){String q=keys.next();JsonNode v=fresh.get("projection").get(q);f.newProjection.put(q,new GoalSignature<>(str(v,"goal_id"),physical(v.get("physical")),stringMap(v.get("testers"))));}
        Set<String> loadable=new LinkedHashSet<>(uniqueStrings(fresh.get("loadable")));
        if(!f.newEndpoint.states().containsAll(loadable))throw new IllegalArgumentException("Unknown loadable endpoint state");
        b.initialSnapshotsFromReachable(f.oldEndpoint,f.oldProjection::get);
        b.goalSignaturesFromReachable(f.newEndpoint,f.newProjection::get,loadable::contains);
        f.problem=b.build();
        EndpointContractValidator.validate(f.oldEndpoint,f.newEndpoint,f.problem,f.oldProjection::get,f.newProjection::get);
        return f;
    }
    static final class CountingGame implements ImplicitStrongGame<CanonicalUpdateConfiguration<String,String>,String,GoalSignature<String,String>> {
        final FineGrainedSuccessorOracle<String,String> g;
        final Map<CanonicalUpdateConfiguration<String,String>,Set<String>> queried=new HashMap<>();long buckets=0,outcomes=0;
        CountingGame(FineGrainedSuccessorOracle<String,String> game){g=game;}
        public Set<CanonicalUpdateConfiguration<String,String>> initialStates(){return g.initialStates();}
        public boolean isSafe(CanonicalUpdateConfiguration<String,String> q){return g.isSafe(q);}
        public boolean isGoal(CanonicalUpdateConfiguration<String,String> q){return g.isGoal(q);}
        public Collection<String> candidateActions(CanonicalUpdateConfiguration<String,String> q){return g.candidateActions(q);}
        public Set<CanonicalUpdateConfiguration<String,String>> post(CanonicalUpdateConfiguration<String,String> q,String a){
            Set<CanonicalUpdateConfiguration<String,String>> next=g.post(q,a);
            if(queried.computeIfAbsent(q,k->new HashSet<>()).add(a)&&!next.isEmpty()){buckets++;outcomes+=next.size();}return next;
        }
        public boolean isControllable(String a){return g.isControllable(a);}public boolean isUpdateAction(String a){return g.isUpdateAction(a);}
        public Comparator<String> actionComparator(){return g.actionComparator();}
        public boolean preferUpdateActions(CanonicalUpdateConfiguration<String,String> q){return g.preferUpdateActions(q);}
        public int explorationActionPriority(CanonicalUpdateConfiguration<String,String> q,String a){return g.explorationActionPriority(q,a);}
        public Comparator<CanonicalUpdateConfiguration<String,String>> stateComparator(){return g.stateComparator();}
        public GoalSignature<String,String> goalMatch(CanonicalUpdateConfiguration<String,String> q){return g.goalMatch(q);}
        public boolean isStructurallyValid(CanonicalUpdateConfiguration<String,String> q){return g.isStructurallyValid(q);}
    }
    static String state(CanonicalUpdateConfiguration<String,String> q){return q.physicalState()+"|"+new TreeMap<>(q.activeTesterStates())+"|"+new TreeSet<>(q.pendingActions());}
    static Map<String,Object> stateObject(CanonicalUpdateConfiguration<String,String> q) {
        Map<String,Object> out=new LinkedHashMap<>();List<Object> physical=new ArrayList<>();
        for(int i=0;i<q.physicalState().size();i++){TaggedState<String> t=q.physicalState().component(i);physical.add(Arrays.asList(t.isOld()?"OLD":"NEW",t.state()));}
        out.put("physical",physical);out.put("testers",new TreeMap<>(q.activeTesterStates()));out.put("pending",new TreeSet<>(q.pendingActions()));return out;
    }
    static Map<String,Object> solve(Fixture f,FineGrainedUpdateProblem<String,String> p,String merge,String solver,double preparation) {
        FineGrainedSuccessorOracle<String,String> game=FineGrainedOtfDucs.game(p);CountingGame measured=new CountingGame(game);
        long begin=System.nanoTime();
        OtfDucsResult<CanonicalUpdateConfiguration<String,String>,String,GoalSignature<String,String>> result=
            solver.equals("lazy")?new OtfDucsSynthesizer<>(measured).synthesize():new DirectFullStrongSolver<>(measured).synthesize();
        double seconds=elapsed(begin);begin=System.nanoTime();FineGrainedOtfDucs.verify(p,result).throwIfInvalid();
        Map<String,Object> row=new LinkedHashMap<>();row.put("id",str(f.input,"id"));row.put("family",str(f.input,"family"));row.put("parameters",f.input.get("parameters"));
        row.put("merge",merge);row.put("generated_contract_mode",f.input.has("generated_contract_mode")?str(f.input,"generated_contract_mode"):"none");row.put("solver",solver);row.put("jar_sha256",E1_SHA);row.put("java_version",System.getProperty("java.version"));
        row.put("decision",result.isWinning()?"WIN":"LOSS");row.put("states_discovered",result.statistics().discoveredStates());row.put("states_expanded",result.statistics().expandedStates());
        row.put("successor_queries",result.statistics().queriedStateActionPairs());row.put("materialized_transitions",result.statistics().materializedTransitions());
        row.put("enabled_buckets",measured.buckets);row.put("enabled_buckets_definition","distinct queried state/action pairs with nonempty Post during synthesis, before certificate/Link diagnostics");
        if(measured.outcomes!=result.statistics().materializedTransitions())throw new IllegalStateException("Measured Post outcome count differs from solver statistics");
        row.put("preparation_seconds",preparation);row.put("solver_seconds",seconds);row.put("certificate_checker","PASS");row.put("endpoint_checker","PASS");
        Map<String,Object> proof=new LinkedHashMap<>();proof.put("decision",row.get("decision"));proof.put("jar_sha256",E1_SHA);
        Set<CanonicalUpdateConfiguration<String,String>> certificateStates=result.isWinning()?result.winningCertificate().ranks().keySet():result.losingCertificate().losingStates();
        List<CanonicalUpdateConfiguration<String,String>> ordered=new ArrayList<>(certificateStates);ordered.sort(Comparator.comparing(WitnessDriver::state));
        Map<CanonicalUpdateConfiguration<String,String>,Integer> ids=new HashMap<>();List<Object> nodes=new ArrayList<>();
        for(CanonicalUpdateConfiguration<String,String> q:ordered){int id=ids.size();ids.put(q,id);Map<String,Object> node=stateObject(q);node.put("id",id);node.put("initial",p.initialConfigurations().contains(q));node.put("safe",game.isSafe(q));node.put("goal",game.isGoal(q));if(result.isWinning())node.put("rank",result.winningCertificate().ranks().get(q));nodes.add(node);}
        proof.put("states",nodes);
        if(result.isWinning()) {
            Map<String,Integer> roots=new TreeMap<>();int max=0;for(int rank:result.winningCertificate().ranks().values())max=Math.max(max,rank);
            for(CanonicalUpdateConfiguration<String,String> q:p.initialConfigurations())roots.put(state(q),result.winningCertificate().ranks().get(q));
            row.put("worst_completion_rank",max);row.put("root_ranks",roots);row.put("certificate_states",certificateStates.size());row.put("losing_region_states",null);
            List<Object> edges=new ArrayList<>();
            for(Map.Entry<CanonicalUpdateConfiguration<String,String>,Map<String,Set<CanonicalUpdateConfiguration<String,String>>>> e:result.winningCertificate().strategy().entrySet())
                for(Map.Entry<String,Set<CanonicalUpdateConfiguration<String,String>>> a:e.getValue().entrySet())for(CanonicalUpdateConfiguration<String,String> t:a.getValue())edges.add(Arrays.asList(ids.get(e.getKey()),a.getKey(),ids.get(t)));
            proof.put("strategy_edges",edges);
            LinkedOtfDucsController<String,String,String,String> linked=LinkedOtfDucsController.link(f.oldEndpoint,f.newEndpoint,p,result,f.oldProjection::get,f.newProjection::get);
            row.put("link_checker","PASS");row.put("linked_states",linked.lts().states().size());row.put("loss_summary",null);
        } else {
            row.put("worst_completion_rank",null);row.put("root_ranks",null);row.put("certificate_states",certificateStates.size());row.put("losing_region_states",certificateStates.size());row.put("link_checker","NOT_APPLICABLE_LOSS");
            Map<String,Object> diagnostic=lossSummary(p,game,certificateStates);row.put("loss_summary",diagnostic);
            row.put("loss_reason","The checked discovered-state losing certificate contains "+certificateStates.size()+" states ("+diagnostic.get("unsafe_region_states")+" unsafe) and "+diagnostic.get("losing_initial_states")+"/"+diagnostic.get("initial_states")+" initial states; its stored root buckets retain every adversarial outcome and identify the outcomes in this certificate (local closure evidence, not a unique causal explanation).");
        }
        row.put("checking_and_link_seconds",elapsed(begin));row.put("_certificate",proof);return row;
    }
    static Map<String,Object> lossSummary(FineGrainedUpdateProblem<String,String> p,FineGrainedSuccessorOracle<String,String> game,Set<CanonicalUpdateConfiguration<String,String>> losing) {
        Map<String,Object> s=new LinkedHashMap<>();int unsafe=0,initial=0;for(CanonicalUpdateConfiguration<String,String> q:losing)if(!game.isSafe(q))unsafe++;
        List<Object> examples=new ArrayList<>();
        for(CanonicalUpdateConfiguration<String,String> q:p.initialConfigurations())if(losing.contains(q)) {
            initial++;if(examples.size()==3)continue;Map<String,Object> ex=stateObject(q);List<Object> buckets=new ArrayList<>();
            for(String action:game.candidateActions(q)) {
                Set<CanonicalUpdateConfiguration<String,String>> next=game.post(q,action);if(next.isEmpty())continue;
                Map<String,Object> b=new LinkedHashMap<>();b.put("action",action);b.put("controllable",game.isControllable(action));b.put("update",game.isUpdateAction(action));b.put("outcomes",next.size());
                int in=0,bad=0;List<Object> unsafeExamples=new ArrayList<>();
                for(CanonicalUpdateConfiguration<String,String> t:next){if(losing.contains(t))in++;if(!game.isSafe(t)){bad++;if(unsafeExamples.size()<3)unsafeExamples.add(stateObject(t));}}
                b.put("outcomes_in_certificate_region",in);b.put("unsafe_outcomes",bad);b.put("unsafe_outcome_examples",unsafeExamples);buckets.add(b);
            }
            ex.put("enabled_action_buckets",buckets);ex.put("safe",game.isSafe(q));examples.add(ex);
        }
        s.put("scope","checked discovered-state losing certificate; sampled local root closure evidence, not a unique whole-game causal explanation");
        s.put("region_states",losing.size());s.put("unsafe_region_states",unsafe);s.put("safe_region_states",losing.size()-unsafe);
        s.put("initial_states",p.initialConfigurations().size());s.put("losing_initial_states",initial);s.put("initial_examples_limit",3);s.put("initial_examples",examples);return s;
    }
    static Map<String,Object> compareGames(FineGrainedUpdateProblem<String,String> a,FineGrainedUpdateProblem<String,String> b) {
        FineGrainedSuccessorOracle<String,String> x=FineGrainedOtfDucs.game(a),y=FineGrainedOtfDucs.game(b);
        if(!x.initialStates().equals(y.initialStates())||!a.commonAlphabet().equals(b.commonAlphabet()))throw new IllegalArgumentException("Comparison roots/alphabet differ");
        Set<CanonicalUpdateConfiguration<String,String>> seen=new LinkedHashSet<>(x.initialStates());Deque<CanonicalUpdateConfiguration<String,String>> todo=new ArrayDeque<>(seen);long buckets=0,outcomes=0;
        while(!todo.isEmpty()) {
            CanonicalUpdateConfiguration<String,String> q=todo.removeFirst();
            if(x.isSafe(q)!=y.isSafe(q)||x.isGoal(q)!=y.isGoal(q))throw new IllegalStateException("Comparison safety/goal differs");
            for(String action:a.commonAlphabet()) {
                Set<CanonicalUpdateConfiguration<String,String>> px=x.post(q,action),py=y.post(q,action);
                if(!px.equals(py)||x.isControllable(action)!=y.isControllable(action))throw new IllegalStateException("Comparison Post differs: "+state(q)+"/"+action);
                if(!px.isEmpty())buckets++;outcomes+=px.size();for(CanonicalUpdateConfiguration<String,String> t:px)if(seen.add(t))todo.addLast(t);
            }
            if(seen.size()>1000000)throw new IllegalStateException("Preflight comparison exceeds one million states");
        }
        Map<String,Object> result=new LinkedHashMap<>();result.put("status","PASS");result.put("reachable_states",seen.size());result.put("nonempty_buckets",buckets);result.put("outcomes",outcomes);return result;
    }
}
