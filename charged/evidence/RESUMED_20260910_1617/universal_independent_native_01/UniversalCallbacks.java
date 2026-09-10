import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicLong;

/** New whole-kernel wrapper; previous native implementations are unchanged. */
public final class UniversalCallbacks {
  static int[] ints(String s) { return Arrays.stream(s.split(",")).mapToInt(Integer::parseInt).toArray(); }
  static Map<String,Object> obj(Object... a) {
    Map<String,Object> r=new LinkedHashMap<>();
    for(int i=0;i<a.length;i+=2)r.put(a[i].toString(),a[i+1]);return r;
  }
  static String json(Object x) {
    if(x==null)return "null";
    if(x instanceof String)return "\""+((String)x).replace("\\","\\\\").replace("\"","\\\"").replace("\n","\\n").replace("\r","\\r")+"\"";
    if(x instanceof Number||x instanceof Boolean)return x.toString();
    if(x instanceof Map){List<String> a=new ArrayList<>();for(var e:((Map<?,?>)x).entrySet())a.add(json(e.getKey())+":"+json(e.getValue()));return "{"+String.join(",",a)+"}";}
    if(x instanceof Iterable){List<String> a=new ArrayList<>();for(Object y:(Iterable<?>)x)a.add(json(y));return "["+String.join(",",a)+"]";}
    if(x instanceof long[])return Arrays.toString((long[])x);
    if(x instanceof int[])return Arrays.toString((int[])x);
    throw new IllegalArgumentException("unserializable "+x.getClass());
  }
  static final class Case {
    final String id,fixture,cheap,layout,kernel,pattern; final int[] w,pred,order; final int r;
    Case(String row){
      String[] a=row.split("\t",-1);if(a.length!=10)throw new IllegalArgumentException("columns");
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
  static final class Value {
    final long id,payload;final int job;
    Value(long id,int job,long payload){this.id=id;this.job=job;this.payload=payload;}
  }
  // Output-only cached completion: success is always true; no comparison bit.
  record Completion(Value output,boolean success) {}
  static final class Run {
    final Case c;final ConcurrentHashMap<Integer,Value> map=new ConcurrentHashMap<>(64);
    final AtomicLong ids=new AtomicLong();final Value[] done,canonical;
    final List<Map<String,Object>> events=Collections.synchronizedList(new ArrayList<>());
    final ExecutorService writer=Executors.newSingleThreadExecutor(r->new Thread(r,"universal-external-writer"));
    long W=0,L=0;int Q=0,writes=0;boolean writerStopped=false;
    Run(Case c){this.c=c;done=new Value[c.w.length];canonical=new Value[c.w.length];
      // Raw inputs and constant objects are not computed records. Every prepared
      // or completed result still requires a charged call to kernel().
      for(int i=0;i<c.w.length;i++){
        Value v=new Value(ids.incrementAndGet(),i,17L*(i+1));map.put(key(i),v);events.add(obj("kind","I","job",i,"id",v.id,"payload",v.payload,"key",key(i)));
        canonical[i]=new Value(ids.incrementAndGet(),i,101L+i);events.add(obj("kind","Z","job",i,"id",canonical[i].id,"payload",canonical[i].payload));
      }
    }
    int key(int i){return c.layout.equals("colliding")?128*i:i;}
    void ready(int i){for(int j=0;j<done.length;j++)if((c.pred[i]&(1<<j))!=0&&done[j]==null)throw new AssertionError("unready "+i);}
    Value kernel(Value source,boolean protectedCall){
      int i=source.job;ready(i);long parent=0;long[] parents=new long[done.length];Arrays.fill(parents,-1);
      for(int j=0;j<done.length;j++)if((c.pred[i]&(1<<j))!=0){parents[j]=done[j].id;parent+=(j+1)*done[j].payload;}
      long digest=source.payload;for(int k=0;k<c.w[i];k++)digest=1664525L*digest+1013904223L+parent;
      W+=c.w[i];if(protectedCall)L+=c.w[i];
      Value out=c.kernel.equals("canonical")?canonical[i]:new Value(ids.incrementAndGet(),i,digest);
      events.add(obj("kind","K","job",i,"source",source.id,"out",out.id,"payload",out.payload,"digest",digest,"parents",parents,"protected",protectedCall,"units",c.w[i]));return out;
    }
    void maybeWrite(int pos,String phase,int job)throws Exception{
      events.add(obj("kind","G","position",pos,"phase",phase));
      if(!phase.equals("gate")||c.pattern.charAt(pos)=='0')return;
      writer.submit(()->map.compute(key(job),(key,source)->{
        Value v=new Value(ids.incrementAndGet(),job,3*source.payload+7);
        events.add(obj("kind","B","job",job,"source",source.id,"out",v.id,"payload",v.payload,"thread",Thread.currentThread().getName()));writes++;return v;
      })).get(2,TimeUnit.SECONDS);
    }
    Map<String,Object> shape()throws Exception{
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
        if(pos>=c.w.length+c.r||pos>=c.pattern.length())throw new AssertionError("call cap or schedule length");
        int i=policy.nextJob();String mode=policy.mode();ready(i);
        events.add(obj("kind","S","position",pos,"job",i,"mode",mode));
        maybeWrite(pos,"before",i);
        Value captured=null,prepared=null;
        captured=map.get(key(i));prepared=kernel(captured,false);
        maybeWrite(pos,"gate",i);
        Completion answer;
        if(mode.equals("cached"))answer=cached(i,captured,prepared);
        else answer=cheap(i,captured,prepared);
        Value saved=answer.output();
        events.add(obj("kind","A","position",pos,"job",i,"mode",mode,"out",saved==null?null:saved.id,"success",answer.success(),"live",map.get(key(i)).id));
        maybeWrite(pos,"after",i);
        if(answer.success()){
          if(done[i]!=null||saved==null)throw new AssertionError("invalid milestone");done[i]=saved;
          events.add(obj("kind","D","job",i,"out",saved.id,"live",map.get(key(i)).id));
        }else if(saved!=null)throw new AssertionError("failed call published an output");
        events.add(obj("kind","X","position",pos,"job",i,"success",answer.success(),"live",map.get(key(i)).id));
        policy.observed(answer.success());pos++;
      }
      if(pos!=c.pattern.length())throw new AssertionError("unconsumed schedule");
      events.add(obj("kind","SH","phase","end","shape",shape()));
    }
    Map<String,Object> result(String status,String error){
      long[] saved=new long[done.length],live=new long[done.length];for(int i=0;i<done.length;i++){saved[i]=done[i]==null?-1:done[i].id;live[i]=map.get(key(i)).id;}
      return obj("id",c.id,"status",status,"error",error,"Q",Q,"W",W,"L",L,"writes",writes,"writer_terminated",writerStopped,"completed",saved,"live",live,"events",events);
    }
  }
  public static void main(String[] args)throws Exception{
    long deadline=System.nanoTime()+TimeUnit.SECONDS.toNanos(120);
    for(String row:Files.readAllLines(Path.of(args[0]))){
      Run r=new Run(new Case(row));String status="SUCCESS",error="";
      try{if(System.nanoTime()>=deadline){status="NOT_EXECUTED";error="execution deadline";}else r.execute();}
      catch(TimeoutException e){status="TIMEOUT";error=e.toString();}
      catch(IllegalArgumentException e){status="INVALID";error=e.toString();}
      catch(Throwable e){status="FAILURE";error=e.toString();}
      finally{r.writer.shutdownNow();r.writerStopped=r.writer.awaitTermination(2,TimeUnit.SECONDS);if(!r.writerStopped){status="FAILURE";error+=" writer did not terminate";}}
      System.out.println(json(r.result(status,error)));System.out.flush();
    }
  }
}
