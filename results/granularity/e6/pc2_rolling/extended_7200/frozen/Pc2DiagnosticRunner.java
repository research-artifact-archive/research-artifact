package ltsa.updatingControllers.cli;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.file.*;
import java.util.*;
import ltsa.updatingControllers.otf.*;
import ltsa.updatingControllers.otf.MtsaRevisedOtfDucsAdapter.LocalState;
/** Post-run diagnostics via the existing CLI and its public retained Outcome. No solver implementation. */
public final class Pc2DiagnosticRunner {
 public static void main(String[] args) throws Exception {
  List<String> cli=new ArrayList<>();Path out=null;
  for(int i=0;i<args.length;i++){if(args[i].equals("--diagnostic-output")){out=Paths.get(args[++i]);}else cli.add(args[i]);}
  if(out==null)throw new IllegalArgumentException("--diagnostic-output required");
  MtsaRevisedOtfDucsAdapter.clearLastOutcomeForCurrentThread();
  int exit=SingleCompositionRunner.runMain(cli.toArray(new String[0]));
  MtsaRevisedOtfDucsAdapter.Outcome outcome=MtsaRevisedOtfDucsAdapter.lastOutcomeForCurrentThread();
  if(outcome!=null){long start=System.nanoTime();Map<String,Object> data=diagnose(outcome);data.put("diagnostic_seconds",(System.nanoTime()-start)/1e9);Files.write(out,new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsBytes(data),StandardOpenOption.CREATE_NEW);}
  System.exit(exit);
 }
 static Map<String,Object> state(CanonicalUpdateConfiguration<LocalState,Long> q){Map<String,Object>d=new LinkedHashMap<>();List<Object> physical=new ArrayList<>();for(TaggedState<LocalState> x:q.physicalState().components())physical.add(Arrays.asList(x.isOld()?"OLD":"NEW",x.state().rawState(),x.state().observerStates()));d.put("physical",physical);d.put("testers",q.activeTesterStates());d.put("pending",q.pendingActions());return d;}
 static Map<String,Object> diagnose(MtsaRevisedOtfDucsAdapter.Outcome outcome){
  var p=outcome.problem();var r=outcome.result();var game=FineGrainedOtfDucs.game(p);Map<String,Object>d=new LinkedHashMap<>();
  d.put("decision",r.isWinning()?"WIN":"LOSS");d.put("certificate_checker","PASS (existing E1 synthesis path)");d.put("link_checker",outcome.linkedController()==null?"NOT_APPLICABLE_LOSS":"PASS (existing E1 synthesis path)");d.put("states_discovered",r.statistics().discoveredStates());d.put("successor_queries",r.statistics().queriedStateActionPairs());d.put("materialized_transitions",r.statistics().materializedTransitions());d.put("initial_states",p.initialConfigurations().size());d.put("old_endpoint_states",outcome.oldEndpoint().states().size());d.put("new_endpoint_states",outcome.newEndpoint().states().size());
  Set<CanonicalUpdateConfiguration<LocalState,Long>> region=r.isWinning()?r.winningCertificate().ranks().keySet():r.losingCertificate().losingStates();
  d.put("certificate_states",region.size());d.put("scope",r.isWinning()?"strategy-reachable winning certificate":"checked discovered-state losing certificate; not the complete losing region of the full game");
  long unsafe=0,initial=0;List<Object>bad=new ArrayList<>(),roots=new ArrayList<>();
  for(var q:region){if(!game.isSafe(q)){unsafe++;if(bad.size()<3)bad.add(state(q));}}
  for(var q:p.initialConfigurations())if(region.contains(q)){initial++;if(roots.size()<3){Map<String,Object>ex=state(q);List<Object>buckets=new ArrayList<>();for(String a:game.candidateActions(q)){var next=game.post(q,a);if(next.isEmpty())continue;Map<String,Object>b=new LinkedHashMap<>();b.put("action",a);b.put("controllable",game.isControllable(a));b.put("update",game.isUpdateAction(a));b.put("outcomes",next.size());int in=0,un=0;for(var t:next){if(region.contains(t))in++;if(!game.isSafe(t))un++;}b.put("outcomes_in_region",in);b.put("unsafe_outcomes",un);buckets.add(b);}ex.put("buckets",buckets);roots.add(ex);}}
  d.put("unsafe_region_states",unsafe);d.put("safe_region_states",region.size()-unsafe);d.put("initial_states_in_region",initial);d.put("unsafe_examples",bad);d.put("initial_examples",roots);
  if(r.isWinning()){int max=0;for(int rank:r.winningCertificate().ranks().values())max=Math.max(max,rank);d.put("worst_completion_rank",max);d.put("rank_scope","maximum rank across strategy-reachable winning certificate states");}else{d.put("losing_region_states",region.size());d.put("loss_reason","Checked losing certificate contains "+region.size()+" states, including "+unsafe+" unsafe states and "+initial+"/"+p.initialConfigurations().size()+" initial states; local root buckets are stored, without asserting a unique causal explanation.");}
  return d;
 }
}
