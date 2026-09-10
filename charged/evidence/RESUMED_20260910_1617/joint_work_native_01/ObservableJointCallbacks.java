import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicLong;

/** New whole-kernel wrapper; previous native implementations are unchanged. */
public final class ObservableJointCallbacks {
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
    final String id,fixture,policy,layout,kernel,phase;final int[] w,pred,order;final int M,k,target;final boolean control;
    Case(String row){
      String[] a=row.split("\t",-1);if(a.length!=13)throw new IllegalArgumentException("columns");
      id=a[0];fixture=a[1];w=ints(a[2]);pred=ints(a[3]);order=ints(a[4]);policy=a[5];M=Integer.parseInt(a[6]);layout=a[7];kernel=a[8];k=Integer.parseInt(a[9]);target=Integer.parseInt(a[10]);phase=a[11];control=Boolean.parseBoolean(a[12]);
      if(w.length!=pred.length||w.length!=order.length||!Set.of("lawler","cached","fresh").contains(policy)||!Set.of("distinct","colliding").contains(layout)||!Set.of("allocated","canonical").contains(kernel)||!Set.of("none","before","gate","after").contains(phase))throw new IllegalArgumentException("shape");
      int seen=0;for(int i:order){if(i<0||i>=w.length||w[i]<1||(seen&(1<<i))!=0||(pred[i]&seen)!=pred[i])throw new IllegalArgumentException("order");seen|=1<<i;}
      if(phase.equals("none")?(k!=-1||target!=-1):(k<0||k>=w.length||target<0||target>=w.length))throw new IllegalArgumentException("schedule");
    }
  }
  // This object is the entire scheduler: no writer, diagnostic counters, clock,
  // object identifiers, map, kernel payload, or actual comparison in controls.
  static final class Policy {
    final int[] order,w;final String family;final int M;int pos=0;boolean observedMismatch=false;
    Policy(Case c){order=c.order.clone();w=c.w.clone();family=c.policy;M=c.M;}
    int nextJob(){return order[pos];}
    boolean fresh(){return family.equals("fresh")||(family.equals("lawler")&&!observedMismatch&&w[nextJob()]>M);}
    void completed(boolean usedCached,boolean comparisonMatch){if(usedCached&&!comparisonMatch)observedMismatch=true;pos++;}
  }
  static final class Value {
    final long id,payload;final int job;
    Value(long id,int job,long payload){this.id=id;this.job=job;this.payload=payload;}
  }
  // The visible cached-completion contract returns this local identity comparison.
  record Completion(Value output,boolean match) {}
  static final class Run {
    final Case c;final ConcurrentHashMap<Integer,Value> map=new ConcurrentHashMap<>(64);
    final AtomicLong ids=new AtomicLong();final Value[] done,canonical;
    final List<Map<String,Object>> events=Collections.synchronizedList(new ArrayList<>());
    final ExecutorService writer=Executors.newSingleThreadExecutor(r->new Thread(r,"joint-resource-external-writer"));
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
    void maybeWrite(int pos,String phase)throws Exception{
      events.add(obj("kind","G","position",pos,"phase",phase));
      if(c.k!=pos||!c.phase.equals(phase))return;
      writer.submit(()->map.compute(key(c.target),(key,source)->{
        Value v=new Value(ids.incrementAndGet(),c.target,3*source.payload+7);
        events.add(obj("kind","B","job",c.target,"source",source.id,"out",v.id,"payload",v.payload,"thread",Thread.currentThread().getName()));writes++;return v;
      })).get(2,TimeUnit.SECONDS);
    }
    Completion cached(int i,Value captured,Value prepared){
      boolean[] match={false};Q++;
      Value out=map.compute(key(i),(key,current)->{
        match[0]=current==captured;
        events.add(obj("kind","C","job",i,"captured",captured.id,"current",current.id,"prepared",prepared.id,"match",match[0]));
        return match[0]?prepared:kernel(current,true);
      });return new Completion(out,match[0]);
    }
    void execute()throws Exception{
      Policy policy=new Policy(c);
      for(int pos=0;pos<c.w.length;pos++){
        int i=policy.nextJob();boolean fresh=policy.fresh();ready(i);
        events.add(obj("kind","S","position",pos,"job",i,"mode",fresh?"fresh":"cached"));
        maybeWrite(pos,"before");
        Value captured=null,prepared=null;
        if(!fresh){captured=map.get(key(i));prepared=kernel(captured,false);}
        maybeWrite(pos,"gate");
        Completion answer;
        if(fresh){Q++;answer=new Completion(map.compute(key(i),(key,current)->kernel(current,true)),true);}
        else answer=cached(i,captured,prepared);
        Value saved=answer.output();
        events.add(obj("kind","A","position",pos,"job",i,"mode",fresh?"fresh":"cached","out",saved.id,"match",fresh?null:answer.match(),"returned_is_prepared",prepared==null?null:saved==prepared));
        maybeWrite(pos,"after");
        if(done[i]!=null)throw new AssertionError("duplicate milestone");done[i]=saved;
        events.add(obj("kind","D","job",i,"out",saved.id,"live",map.get(key(i)).id));
        policy.completed(!fresh,c.control?true:answer.match());
      }
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
