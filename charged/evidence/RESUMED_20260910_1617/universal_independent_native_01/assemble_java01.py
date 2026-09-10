from pathlib import Path
import hashlib,json
D=Path(__file__).resolve().parent;src=D.parent/'one_retry_native_01/OneRetryCallbacks.java';old=src.read_bytes();t=old.decode().replace('OneRetryCallbacks','UniversalCallbacks').replace('one-retry-external-writer','universal-external-writer')
a=t.index('  static final class Case {');b=t.index('  static final class Value {',a)
t=t[:a]+'''  static final class Case {
    final String id,fixture,cheap,layout,kernel,pattern; final int[] w,pred,order; final int r;
    Case(String row){
      String[] a=row.split("\\t",-1);if(a.length!=10)throw new IllegalArgumentException("columns");
      id=a[0];fixture=a[1];w=ints(a[2]);pred=ints(a[3]);order=ints(a[4]);cheap=a[5];r=Integer.parseInt(a[6]);layout=a[7];kernel=a[8];pattern=a[9];
      if(w.length!=pred.length||w.length!=order.length||r<0||!Set.of("replace","validate").contains(cheap)||!Set.of("distinct","colliding").contains(layout)||!Set.of("allocated","canonical").contains(kernel)||!pattern.matches("[01]+"))throw new IllegalArgumentException("shape");
      int seen=0;for(int i:order){if(i<0||i>=w.length||w[i]<1||(seen&(1<<i))!=0||pred[i]!=0)throw new IllegalArgumentException("independent jobs");seen|=1<<i;}
    }
  }
  // The controller independently sorts works and observes only completion.
  // No B, schedule, diagnostics, returned value or cached flag enters Policy.
  static final class Policy {
    final int[] order; final int r; int pos=0,failures=0;
    Policy(Case c){r=c.r;Integer[] jobs=new Integer[c.w.length];for(int i=0;i<jobs.length;i++)jobs[i]=i;
      Arrays.sort(jobs,Comparator.comparingInt((Integer i)->c.w[i]).thenComparingInt(i->i));
      order=Arrays.stream(jobs).mapToInt(Integer::intValue).toArray();}
    boolean done(){return pos==order.length;}
    int nextJob(){return order[pos];}
    String mode(){return failures<r?"cheap":"cached";}
    void observed(boolean success){if(success)pos++;else failures++;}
  }
''' +t[b:]
a=t.index('    void maybeWrite(');b=t.index('    Map<String,Object> shape()',a)
t=t[:a]+'''    void maybeWrite(int pos,String phase,int job)throws Exception{
      events.add(obj("kind","G","position",pos,"phase",phase));
      if(!phase.equals("gate")||c.pattern.charAt(pos)=='0')return;
      writer.submit(()->map.compute(key(job),(key,source)->{
        Value v=new Value(ids.incrementAndGet(),job,3*source.payload+7);
        events.add(obj("kind","B","job",job,"source",source.id,"out",v.id,"payload",v.payload,"thread",Thread.currentThread().getName()));writes++;return v;
      })).get(2,TimeUnit.SECONDS);
    }
''' +t[b:]
t=t.replace('if(pos>c.w.length)throw new AssertionError("call cap");','if(pos>=c.w.length+c.r||pos>=c.pattern.length())throw new AssertionError("call cap or schedule length");')
for phase in ['before','gate','after']:t=t.replace(f'maybeWrite(pos,"{phase}");',f'maybeWrite(pos,"{phase}",i);')
t=t.replace('      events.add(obj("kind","SH","phase","end","shape",shape()));','      if(pos!=c.pattern.length())throw new AssertionError("unconsumed schedule");\n      events.add(obj("kind","SH","phase","end","shape",shape()));')
# The old fresh branch is unreachable; delete it to keep the executable interface minimal.
t=t.replace('        if(!mode.equals("fresh")){captured=map.get(key(i));prepared=kernel(captured,false);}','        captured=map.get(key(i));prepared=kernel(captured,false);')
t=t.replace('        if(mode.equals("fresh")){Q++;answer=new Completion(map.compute(key(i),(key,current)->kernel(current,true)),true);}\n        else if(mode.equals("cached"))answer=cached(i,captured,prepared);','        if(mode.equals("cached"))answer=cached(i,captured,prepared);')
assert 'c.M' not in t and 'c.target' not in t and 'c.k!=' not in t and '"fresh"' not in t
assert not(D/'UniversalCallbacks.java').exists();(D/'UniversalCallbacks.java').write_text(t)
(D/'SOURCE_DERIVATION01.json').write_text(json.dumps(dict(previous_source='../one_retry_native_01/OneRetryCallbacks.java',previous_sha256=hashlib.sha256(old).hexdigest(),new_sha256=hashlib.sha256(t.encode()).hexdigest(),change='Independent weight sort, r failure policy with output-only cached completion, complete multiwrite comparison patterns; old source unchanged'),indent=2)+'\n')
