import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;

public final class ProbeBlocking {
  static final int[] WEIGHTS={1,2,3,5}, PRED={0,1,2,4};
  static final int[] SCALES={64,2048,65536,2097152};
  static final int N=4;
  static final class Value {
    final long seed; final int version;
    Value(long s,int v){seed=s;version=v;}
  }
  // No scale, writer state or B reaches this selector.
  static final class Selector {
    final int[] pred; final boolean cached; int slack;
    Selector(int[] p,boolean c,int r){pred=p.clone();cached=c;slack=r;}
    int[] choose(int mask){
      for(int i=0;i<pred.length;i++)if((mask&(1<<i))!=0&&(pred[i]&mask)==0)
        return new int[]{i,slack>0?1:cached?0:2};
      throw new IllegalStateException("no ready job");
    }
    void failed(){if(slack--<=0)throw new AssertionError("slack");}
  }
  static Map<String,Object> obj(Object... x){Map<String,Object> m=new LinkedHashMap<>();for(int i=0;i<x.length;i+=2)m.put(x[i].toString(),x[i+1]);return m;}
  static String json(Object x){
    if(x==null)return "null";
    if(x instanceof String)return "\""+x.toString().replace("\\","\\\\").replace("\"","\\\"").replace("\n","\\n").replace("\r","\\r")+"\"";
    if(x instanceof Number||x instanceof Boolean)return x.toString();
    if(x instanceof Map){List<String> a=new ArrayList<>();for(var e:((Map<?,?>)x).entrySet())a.add(json(e.getKey().toString())+":"+json(e.getValue()));return "{"+String.join(",",a)+"}";}
    if(x instanceof Iterable){List<String>a=new ArrayList<>();for(Object y:(Iterable<?>)x)a.add(json(y));return "["+String.join(",",a)+"]";}
    if(x instanceof long[])return Arrays.toString((long[])x);
    if(x instanceof int[])return Arrays.toString((int[])x);
    throw new IllegalArgumentException("json type");
  }
  static final class Ticket {
    final CountDownLatch issued=new CountDownLatch(1);
    volatile long start,entry,end;
    Future<?> future;
  }
  static final class Run {
    final int scale,r;final boolean cached,same;final ExecutorService probe,writer;
    final ConcurrentHashMap<Integer,Value> map=new ConcurrentHashMap<>(64);
    final Value[] done=new Value[N];final List<Map<String,Object>> probes=new ArrayList<>();
    final List<String> trace=new ArrayList<>();
    long work,protectedWork,outKernelNs,inKernelNs,setupNs;int q,writes,failures;long origin;
    Run(int s,int r,boolean c,boolean same,ExecutorService p,ExecutorService w){
      long t=System.nanoTime();scale=s;this.r=r;cached=c;this.same=same;probe=p;writer=w;
      for(int i=0;i<N;i++)map.put(128*i,new Value(17L+31L*i,0));
      map.put(probeKey(),new Value(37,0));setupNs=System.nanoTime()-t;
    }
    int probeKey(){return same?512:1;}
    Value kernel(int i,Value src,boolean inside){
      long start=System.nanoTime(),parent=0;
      for(int j=0;j<N;j++)if((PRED[i]&(1<<j))!=0){if(done[j]==null)throw new AssertionError("uncaptured parent");parent=Long.rotateLeft(parent,7)^done[j].seed;}
      long x=src.seed^parent;int iterations=WEIGHTS[i]*scale;
      for(int k=0;k<iterations;k++)x=Long.rotateLeft(x,13)*6364136223846793005L+1442695040888963407L;
      work+=iterations;if(inside)protectedWork+=iterations;
      long ns=System.nanoTime()-start;if(inside)inKernelNs+=ns;else outKernelNs+=ns;
      return new Value(x,src.version);
    }
    void inject(int i)throws Exception{
      writer.submit(()->{map.compute(128*i,(key,v)->new Value(v.seed+104729,v.version+1));}).get(3,TimeUnit.SECONDS);writes++;
    }
    Ticket issue(){
      Ticket t=new Ticket();
      t.future=probe.submit(()->{
        t.start=System.nanoTime();t.issued.countDown();
        map.compute(probeKey(),(key,v)->{t.entry=System.nanoTime();return v;});t.end=System.nanoTime();
      });
      try{if(!t.issued.await(3,TimeUnit.SECONDS))throw new RuntimeException("probe ready timeout");}
      catch(InterruptedException e){Thread.currentThread().interrupt();throw new RuntimeException(e);}
      return t;
    }
    Value callback(int i,Value before,Value prepared)throws Exception{
      Ticket[] ticket={null};long[] ticks=new long[3];boolean[] match={false};q++;
      Value result=map.compute(128*i,(key,src)->{
        ticks[0]=System.nanoTime();ticket[0]=issue();ticks[1]=System.nanoTime();
        match[0]=src==before;
        Value v=cached&&match[0]?prepared:kernel(i,src,true);
        ticks[2]=System.nanoTime();return v;
      });
      ticket[0].future.get(3,TimeUnit.SECONDS);Ticket t=ticket[0];
      if(t.start==0||t.entry<t.start||t.end<t.entry||(same&&t.entry<ticks[2]))throw new AssertionError("probe chronology");
      if(cached&&!match[0])throw new AssertionError("unexpected cached mismatch");
      probes.add(obj("job",i,"issue_ns",t.start-origin,"entry_ns",t.entry-origin,"end_ns",t.end-origin,"callback_entry_ns",ticks[0]-origin,"body_start_ns",ticks[1]-origin,"body_end_ns",ticks[2]-origin,"wait_ns",t.entry-t.start,"operation_ns",t.end-t.start,"callback_body_ns",ticks[2]-ticks[1],"callback_hooked_ns",ticks[2]-ticks[0]));
      return result;
    }
    Map<String,Object> execute(){
      origin=System.nanoTime();String status="SUCCESS",error="";
      try{
        Selector selector=new Selector(PRED,cached,r);int mask=(1<<N)-1;
        while(mask!=0){int[] action=selector.choose(mask);int i=action[0],mode=action[1];Value result;
          if(mode==1){
            Value old=map.get(128*i),fresh=kernel(i,old,false);inject(i);q++;
            if(map.replace(128*i,old,fresh))throw new AssertionError("forced failure published");
            failures++;selector.failed();trace.add(i+":F");continue;
          }
          if(mode==0){Value old=map.get(128*i),fresh=kernel(i,old,false);result=callback(i,old,fresh);trace.add(i+":C");}
          else{result=callback(i,null,null);trace.add(i+":P");}
          done[i]=result;mask^=1<<i;
        }
        if(q!=N+r||writes!=r||failures!=r||work!=(11L+r)*scale||protectedWork!=(cached?0L:11L*scale)||probes.size()!=N)throw new AssertionError("resource equation");
        if(map.get(probeKey()).seed!=37||map.get(probeKey()).version!=0)throw new AssertionError("probe wrote");
      }catch(TimeoutException e){status="TIMEOUT";error=e.toString();}
      catch(IllegalArgumentException e){status="INVALID";error=e.toString();}
      catch(Throwable e){status="FAILURE";error=e.toString();}
      long elapsed=System.nanoTime()-origin;long[] seeds=new long[N];int[] versions=new int[N];
      for(int i=0;i<N;i++){seeds[i]=done[i]==null?0:done[i].seed;versions[i]=done[i]==null?-1:done[i].version;}
      long waitSum=0,waitMax=0;for(var p:probes){long w=((Number)p.get("wait_ns")).longValue();waitSum+=w;waitMax=Math.max(waitMax,w);}
      return obj("status",status,"error",error,"scale",scale,"r",r,"policy",cached?"three":"two","layout",same?"same_bin":"disjoint_bin","Q",q,"W",work,"L",protectedWork,"writes",writes,"failures",failures,"seeds",seeds,"versions",versions,"trace",trace,"probes",probes,"wait_sum_ns",waitSum,"wait_max_ns",waitMax,"foreground_ns",elapsed,"setup_ns",setupNs,"kernel_out_ns",outKernelNs,"kernel_in_ns",inKernelNs);
    }
  }
  static Thread daemon(Runnable r,String name){Thread t=new Thread(r,name);t.setDaemon(true);return t;}
  public static void main(String[] args)throws Exception{
    int fork=Integer.parseInt(args[0]),warm=Integer.parseInt(args[1]),reps=Integer.parseInt(args[2]);
    ExecutorService probe=Executors.newSingleThreadExecutor(r->daemon(r,"unchanged-value-probe"));
    ExecutorService writer=Executors.newSingleThreadExecutor(r->daemon(r,"external-invalidating-writer"));
    long start=System.nanoTime();Random random=new Random(20260909L+fork);int sequence=0;
    try{
      for(int rep=-warm;rep<reps;rep++){
        List<int[]> pairs=new ArrayList<>();for(int s:SCALES)for(int r=0;r<3;r++)for(int b=0;b<2;b++)pairs.add(new int[]{s,r,b});
        Collections.shuffle(pairs,random);
        for(int[] cell:pairs){boolean first=random.nextBoolean();
          for(boolean cached:new boolean[]{first,!first}){
            Run run=new Run(cell[0],cell[1],cached,cell[2]==0,probe,writer);var result=run.execute();
            result.put("fork",fork);result.put("phase",rep<0?"warmup":"measure");result.put("rep",rep);result.put("sequence",sequence++);result.put("process_elapsed_ns",System.nanoTime()-start);
            System.out.println(json(result));System.out.flush();
            if(!result.get("status").equals("SUCCESS"))return;
          }
        }
      }
    }finally{writer.shutdownNow();probe.shutdownNow();writer.awaitTermination(3,TimeUnit.SECONDS);probe.awaitTermination(3,TimeUnit.SECONDS);}
  }
}
