package ltsa.updatingControllers.cli;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.file.*;
import java.util.*;
import java.util.function.Function;
import ltsa.updatingControllers.otf.*;
import ltsa.updatingControllers.otf.MtsaRevisedOtfDucsAdapter.LocalState;
import ltsa.updatingControllers.otf.MtsaRevisedOtfDucsAdapter.EndpointState;
/** Validation-only replay/export through fixed E1; not a replacement solver. */
public final class Pc2CertificateExportRunner {
 public static void main(String[] args) throws Exception {
  List<String> cli=new ArrayList<>();Path path=null;
  for(int i=0;i<args.length;i++)if(args[i].equals("--certificate-output"))path=Paths.get(args[++i]);else cli.add(args[i]);
  if(path==null)throw new IllegalArgumentException("--certificate-output required");
  MtsaRevisedOtfDucsAdapter.clearLastOutcomeForCurrentThread();int code=SingleCompositionRunner.runMain(cli.toArray(new String[0]));
  var outcome=MtsaRevisedOtfDucsAdapter.lastOutcomeForCurrentThread();
  if(outcome!=null){var proof=export(outcome);Files.write(path,new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsBytes(proof),StandardOpenOption.CREATE_NEW);}
  System.exit(code);
 }
 static PhysicalState<LocalState> physical(EndpointState q,boolean old){List<TaggedState<LocalState>> values=new ArrayList<>();for(LocalState s:q.localStates())values.add(old?TaggedState.oldState(s):TaggedState.newState(s));return PhysicalState.of(values);}
 static Map<String,Object> state(CanonicalUpdateConfiguration<LocalState,Long> q){Map<String,Object> out=new LinkedHashMap<>();List<Object> values=new ArrayList<>();for(var s:q.physicalState().components())values.add(Arrays.asList(s.isOld()?"OLD":"NEW",s.state().rawState(),s.state().observerStates()));out.put("physical",values);out.put("testers",q.activeTesterStates());out.put("pending",q.pendingActions());return out;}
 static Map<String,Object> export(MtsaRevisedOtfDucsAdapter.Outcome outcome){
  var p=outcome.problem();var r=outcome.result();var game=FineGrainedOtfDucs.game(p);FineGrainedOtfDucs.verify(p,r).throwIfInvalid();
  if(!p.normalActions().containsAll(Arrays.asList("calibrated.1","calibrated.2")))throw new IllegalStateException("Calibration action names differ");
  Map<String,Object> proof=new LinkedHashMap<>();proof.put("purpose","validation-only replay; excluded from measured series/timing comparisons");proof.put("decision",r.isWinning()?"WIN":"LOSS");proof.put("certificate_checker","PASS rechecked by fixed E1");proof.put("states_discovered",r.statistics().discoveredStates());proof.put("successor_queries",r.statistics().queriedStateActionPairs());proof.put("materialized_transitions",r.statistics().materializedTransitions());
  Set<CanonicalUpdateConfiguration<LocalState,Long>> region=r.isWinning()?r.winningCertificate().ranks().keySet():r.losingCertificate().losingStates();
  List<CanonicalUpdateConfiguration<LocalState,Long>> ordered=new ArrayList<>(region);ordered.sort(Comparator.comparing(Object::toString));Map<CanonicalUpdateConfiguration<LocalState,Long>,Integer> ids=new HashMap<>();List<Object> nodes=new ArrayList<>();int minimumReady=2;
  for(var q:ordered){int id=ids.size();ids.put(q,id);Map<String,Object> node=state(q);node.put("id",id);node.put("initial",p.initialConfigurations().contains(q));node.put("safe",game.isSafe(q));node.put("goal",game.isGoal(q));int ready=0;for(int i=0;i<q.physicalState().size();i++){var s=q.physicalState().component(i);if(s.isOld()||!p.components().get(i).newLts().enabledActions(s.state()).contains("calibrated."+(i+1)))ready++;}node.put("physical_operational_arms",ready);minimumReady=Math.min(minimumReady,ready);if(r.isWinning())node.put("rank",r.winningCertificate().ranks().get(q));nodes.add(node);}
  proof.put("states",nodes);proof.put("minimum_physical_operational_arms",minimumReady);
  if(r.isWinning()){
   List<Object> edges=new ArrayList<>();for(var e:r.winningCertificate().strategy().entrySet())for(var a:e.getValue().entrySet())for(var t:a.getValue())edges.add(Arrays.asList(ids.get(e.getKey()),a.getKey(),ids.get(t)));proof.put("strategy_edges",edges);
   int max=0;for(int rank:r.winningCertificate().ranks().values())max=Math.max(max,rank);proof.put("worst_completion_rank",max);
   Map<String,Object> goals=new TreeMap<>();for(var e:r.winningCertificate().goalMatches().entrySet())goals.put(ids.get(e.getKey()).toString(),e.getValue().endpointId());proof.put("goal_matches",goals);
   Map<EndpointState,GoalSignature<LocalState,Long>> newProjection=new LinkedHashMap<>();int index=0;
   for(var q:outcome.newEndpoint().reachableStates()){var signature=new GoalSignature<LocalState,Long>(String.format("new-%08d",index++),physical(q,false),q.testerStates());if(!p.goalSignatures().contains(signature))throw new IllegalStateException("Reconstructed endpoint signature differs");newProjection.put(q,signature);}
   Function<EndpointState,InitialSnapshot<LocalState,Long>> oldProjection=q->new InitialSnapshot<>(physical(q,true),q.testerStates());
   new LinkedOtfDucsControllerChecker<EndpointState,LocalState,Long,EndpointState>().verify(outcome.linkedController(),outcome.oldEndpoint(),outcome.newEndpoint(),p,r,oldProjection,newProjection::get).throwIfInvalid();proof.put("link_checker","PASS rechecked by fixed E1 structural Link checker");
   var linked=outcome.linkedController().lts();Map<Object,Integer> linkIds=new LinkedHashMap<>();List<Object> linkNodes=new ArrayList<>(),linkEdges=new ArrayList<>();for(var q:linked.states()){linkIds.put(q,linkIds.size());linkNodes.add(q.toString());}for(var q:linked.states())for(String a:linked.enabledActions(q))for(var t:linked.successors(q,a))linkEdges.add(Arrays.asList(linkIds.get(q),a,linkIds.get(t)));proof.put("linked_state_descriptions",linkNodes);proof.put("linked_edges",linkEdges);
  }else{proof.put("losing_region_states",region.size());proof.put("link_checker","NOT_APPLICABLE_LOSS");}
  return proof;
 }
}
