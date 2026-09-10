from pathlib import Path
import hashlib,json
D=Path(__file__).resolve().parent;src=D.parent/'joint_work_native_01/ObservableJointCallbacks.java'
t=src.read_text().replace('ObservableJointCallbacks','OneRetryCallbacks')
t=t.replace('final String id,fixture,policy,layout,kernel,phase;final int[] w,pred,order;final int M,k,target;final boolean control;','final String id,fixture,cheap,layout,kernel,phase;final int[] w,pred,order;final int M,k,target;')
t=t.replace('if(a.length!=13)','if(a.length!=12)').replace('policy=a[5]','cheap=a[5]').replace(';control=Boolean.parseBoolean(a[12])','')
t=t.replace('Set.of("lawler","cached","fresh").contains(policy)','Set.of("replace","validate").contains(cheap)').replace('k>=w.length','k>w.length')
left=t.index('  // This object is the entire scheduler:');right=t.index('  static final class Value',left)
t=t[:left]+'''  // The controller sees only its fixed contract and success/completion events.
  // Cached comparison, values, shape and diagnostics never enter this object.
  static final class Policy {
    final int[] order,w; final int M; int pos=0; boolean failed=false;
    Policy(Case c){order=c.order.clone();w=c.w.clone();M=c.M;}
    boolean done(){return pos==order.length;}
    int nextJob(){return order[pos];}
    String mode(){return failed?"cached":w[nextJob()]>M?"fresh":"cheap";}
    void observed(boolean success){if(success)pos++;else failed=true;}
  }
''' + t[right:]
t=t.replace('// The visible cached-completion contract returns this local identity comparison.','// Output-only cached completion: success is always true; no comparison bit.')
t=t.replace('record Completion(Value output,boolean match) {}','record Completion(Value output,boolean success) {}')
t=t.replace('joint-resource-external-writer','one-retry-external-writer')
left=t.index('    Completion cached(');right=t.index('    Map<String,Object> result(',left)
t=t[:left]+'''    Map<String,Object> shape()throws Exception{
      var field=ConcurrentHashMap.class.getDeclaredField("table");field.setAccessible(true);
      Object[] table=(Object[])field.get(map);int trees=0,count=0;
      var next=Class.forName("java.util.concurrent.ConcurrentHashMap$Node").getDeclaredField("next");next.setAccessible(true);
      List<Map<String,Object>> bins=new ArrayList<>();
      for(int slot=0;slot<table.length;slot++)if(table[slot]!=null){
        Object head=table[slot];String type=head.getClass().getName();
        if(type.endsWith("$TreeBin")){trees++;var first=head.getClass().getDeclaredField("first");first.setAccessible(true);head=first.get(head);}
        int nodes=0;while(head!=null){nodes++;head=next.get(head);}count+=nodes;
        bins.add(obj("slot",slot,"class",type,"nodes",nodes));
      }
      return obj("capacity",table.length,"tree_bins",trees,"node_count",count,"bins",bins);
    }
    Completion cached(int i,Value captured,Value prepared){
      Q++;
      Value out=map.compute(key(i),(key,current)->{
        boolean match=current==captured;
        events.add(obj("kind","C","job",i,"captured",captured.id,"current",current.id,"prepared",prepared.id,"match",match));
        return match?prepared:kernel(current,true);
      });return new Completion(out,true);
    }
    Completion cheap(int i,Value captured,Value prepared){
      Q++;boolean success;
      if(c.cheap.equals("replace")){
        Value before=map.get(key(i));
        success=map.replace(key(i),captured,prepared);
        events.add(obj("kind","V","job",i,"captured",captured.id,"current",before.id,"prepared",prepared.id,"success",success,"wrapper",c.cheap));
      }else{
        boolean[] ok={false};
        map.compute(key(i),(key,current)->{
          ok[0]=current==captured;
          events.add(obj("kind","V","job",i,"captured",captured.id,"current",current.id,"prepared",prepared.id,"success",ok[0],"wrapper",c.cheap));
          return ok[0]?prepared:current;
        });success=ok[0];
      }
      return new Completion(success?prepared:null,success);
    }
    void execute()throws Exception{
      events.add(obj("kind","SH","phase","start","shape",shape()));
      Policy policy=new Policy(c);int pos=0;
      while(!policy.done()){
        if(pos>c.w.length)throw new AssertionError("call cap");
        int i=policy.nextJob();String mode=policy.mode();ready(i);
        events.add(obj("kind","S","position",pos,"job",i,"mode",mode));
        maybeWrite(pos,"before");
        Value captured=null,prepared=null;
        if(!mode.equals("fresh")){captured=map.get(key(i));prepared=kernel(captured,false);}
        maybeWrite(pos,"gate");
        Completion answer;
        if(mode.equals("fresh")){Q++;answer=new Completion(map.compute(key(i),(key,current)->kernel(current,true)),true);}
        else if(mode.equals("cached"))answer=cached(i,captured,prepared);
        else answer=cheap(i,captured,prepared);
        Value saved=answer.output();
        events.add(obj("kind","A","position",pos,"job",i,"mode",mode,"out",saved==null?null:saved.id,"success",answer.success(),"live",map.get(key(i)).id));
        maybeWrite(pos,"after");
        if(answer.success()){
          if(done[i]!=null||saved==null)throw new AssertionError("invalid milestone");done[i]=saved;
          events.add(obj("kind","D","job",i,"out",saved.id,"live",map.get(key(i)).id));
        }else if(saved!=null)throw new AssertionError("failed call published an output");
        events.add(obj("kind","X","position",pos,"job",i,"success",answer.success(),"live",map.get(key(i)).id));
        policy.observed(answer.success());pos++;
      }
      events.add(obj("kind","SH","phase","end","shape",shape()));
    }
''' + t[right:]
assert 'c.control' not in t and 'c.policy' not in t and 'answer.match' not in t
(D/'OneRetryCallbacks.java').write_text(t)
(D/'SOURCE_DERIVATION01.json').write_text(json.dumps({'original':str(src),'original_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'new_sha256':hashlib.sha256(t.encode()).hexdigest(),'original_modified':False},indent=2)+'\n')
print(len(t.encode()))
