import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;

public final class FrontierChargedCallbacks {
  static int[] ints(String x){return x.equals("-")?new int[0]:Arrays.stream(x.split(",")).mapToInt(Integer::parseInt).toArray();}
  static String json(Object x){
    if(x==null)return "null";
    if(x instanceof String)return "\""+((String)x).replace("\\","\\\\").replace("\"","\\\"").replace("\n","\\n").replace("\r","\\r")+"\"";
    if(x instanceof Number||x instanceof Boolean)return x.toString();
    if(x instanceof Map){List<String> out=new ArrayList<>();for(Object e0:((Map<?,?>)x).entrySet()){Map.Entry<?,?> e=(Map.Entry<?,?>)e0;out.add(json(e.getKey().toString())+":"+json(e.getValue()));}return "{"+String.join(",",out)+"}";}
    if(x instanceof Iterable){List<String> out=new ArrayList<>();for(Object z:(Iterable<?>)x)out.add(json(z));return "["+String.join(",",out)+"]";}
    if(x instanceof int[])return Arrays.toString((int[])x);
    if(x instanceof long[])return Arrays.toString((long[])x);
    throw new IllegalArgumentException("json type "+x.getClass());
  }
  static Map<String,Object> obj(Object... xs){Map<String,Object> m=new LinkedHashMap<>();for(int i=0;i<xs.length;i+=2)m.put(xs[i].toString(),xs[i+1]);return m;}
  static final class Input {
    String id,policy;int[] w,p,g,v,r,pred;int n,threshold;boolean three;Map<Integer,long[]> curves=new HashMap<>();
    Input(String line,Path dir)throws Exception{
      String[] z=line.split("\t",-1);if(z.length!=9)throw new IllegalArgumentException("case fields");
      id=z[0];w=ints(z[1]);p=ints(z[2]);g=ints(z[3]);v=ints(z[4]);r=ints(z[5]);pred=ints(z[6]);n=w.length;policy=z[8];
      if(!Set.of("slack_three-0","slack_three-1","slack_three-2","slack_three-3","slack_two-0","slack_two-1","slack_two-2","slack_two-3").contains(policy))throw new IllegalArgumentException("policy");
      threshold=Integer.parseInt(policy.substring(policy.length()-1));three=policy.startsWith("slack_three");
      if(n<2||n>5||p.length!=n||g.length!=n||v.length!=n||r.length!=n||pred.length!=n)throw new IllegalArgumentException("shape");
      for(int i=0;i<n;i++)if(w[i]<1||w[i]>256||p[i]!=w[i]||g[i]!=0||v[i]!=r[i]||(v[i]!=0&&v[i]!=2)||pred[i]<0||pred[i]>=(1<<n)||(pred[i]&(1<<i))!=0||8*w[i]-Integer.bitCount(pred[i])<=0)throw new IllegalArgumentException("vector prices");
      for(String row:Files.readAllLines(dir.resolve(z[7]))){
        String[] x=row.split("\t",-1);if(x.length!=2)throw new IllegalArgumentException("curve fields");
        int mask=Integer.parseInt(x[0]);String[] y=x[1].split(";",-1);if(mask<0||mask>=(1<<n)||y.length!=4||curves.containsKey(mask))throw new IllegalArgumentException("curve shape");
        long[] values=new long[4];for(int j=0;j<4;j++){values[j]=Long.parseLong(y[j]);if(values[j]<0)throw new IllegalArgumentException("curve data");}curves.put(mask,values);
      }
      if(curves.size()!=(1<<n))throw new IllegalArgumentException("missing curve");
      for(int j=0;j<4;j++)if(value(0,j)!=0)throw new IllegalArgumentException("empty curve");
      for(int mask=1;mask<(1<<n);mask++)for(int budget=0;budget<4;budget++)choose(mask,budget);
    }
    long value(int mask,int b){if(b<0||b>3)throw new IllegalArgumentException("budget");return curves.get(mask)[b];}
    int[] choose(int mask,int b){
      int job=-1;for(int i=0;i<n;i++)if((mask&(1<<i))!=0&&(pred[i]&mask)==0){job=i;break;}if(job<0)throw new IllegalArgumentException("readiness");
      int mode=(b==0||b>threshold)?1:(three?0:2),child=mask^(1<<job);long q;
      if(mode==2)q=p[job]+value(child,b);
      else if(mode==1)q=b==0?value(child,b):Math.max(value(child,b),w[job]+v[job]+value(mask,b-1));
      else q=Math.max(value(child,b),w[job]+p[job]+value(child,b-1));
      if(q!=value(mask,b))throw new IllegalArgumentException("policy table equation");return new int[]{job,mode};
    }
    long ceiling(int b){long a=0;for(int i=0;i<n;i++)a+=w[i]+Math.min(v[i],g[i]+r[i]);return 8*(a+value((1<<n)-1,b));}
  }
  static final class Value {final long id;final int slot,bg,seed;final int[] a;Value(long id,int slot,int bg,int[] a,int seed){this.id=id;this.slot=slot;this.bg=bg;this.a=a;this.seed=seed;}}
  static final class Run {
    final String id,layout,kind,schedule,mutant;final Input in;final int B,seed;
    final ConcurrentHashMap<Integer,Value> map=new ConcurrentHashMap<>(64);
    final Value[] done;final long[] protectedCalls,callbacks,conditionals;final AtomicLong ids=new AtomicLong();
    final AtomicInteger writes=new AtomicInteger();final List<Map<String,Object>> events=Collections.synchronizedList(new ArrayList<>());
    final List<String> trace=new ArrayList<>();final List<int[]> failureWitnesses=new ArrayList<>();
    final ExecutorService writer=Executors.newSingleThreadExecutor(r->{Thread t=new Thread(r,"charged-external-writer");t.setDaemon(true);return t;});
    long work=0,setupNs;int pos=0;boolean forcedPost=false;Future<?> concurrent;
    Run(String row,Map<String,Input> inputs){
      long t=System.nanoTime();String[] z=row.split("\t",-1);id=z[0];in=inputs.get(z[1]);layout=z[2];kind=z[3];B=Integer.parseInt(z[4]);schedule=z[5].equals("-")?"":z[5];seed=Integer.parseInt(z[6]);mutant=z[7];
      if(in==null||B<0||(!layout.equals("distinct")&&!layout.equals("colliding")))throw new IllegalArgumentException("run");
      done=new Value[in.n];protectedCalls=new long[in.n];callbacks=new long[in.n];conditionals=new long[in.n];
      for(int i=0;i<in.n;i++){int[] a=new int[8*in.w[i]-Integer.bitCount(in.pred[i])];int s=0;for(int j=0;j<a.length;j++){a[j]=17*(i+1)+31*j;s=31*s+a[j];}Value v=new Value(ids.incrementAndGet(),i,0,a,s);map.put(key(i),v);events.add(obj("kind","I","job",i,"id",v.id,"seed",s));}setupNs=System.nanoTime()-t;
    }
    int key(int i){return layout.equals("colliding")?128*i:i;}
    void ready(int i){for(int j=0;j<in.n;j++)if((in.pred[i]&(1<<j))!=0&&done[j]==null)throw new AssertionError("early kernel "+i);}
    Value kernel(Value src,boolean inside){
      int i=src.slot;ready(i);int parent=0;long[] parents=new long[in.n];Arrays.fill(parents,-1);
      for(int j=0;j<in.n;j++)if((in.pred[i]&(1<<j))!=0){Value v=mutant.equals("live_parent")?map.get(key(j)):done[j];parents[j]=v.id;parent=31*parent+v.seed;work++;}
      int[] a=new int[src.a.length];int s=0;for(int j=0;j<a.length;j++){a[j]=1664525*src.a[j]+1013904223+parent;s=31*s+a[j];work++;if(kind.equals("concurrent")&&j%16==0)Thread.yield();}
      if(inside)protectedCalls[i]++;Value next=new Value(ids.incrementAndGet(),i,src.bg,a,s);
      events.add(obj("kind","K","job",i,"source",src.id,"id",next.id,"inside",inside,"parents",parents,"seed",s));return next;
    }
    void background(int i){map.compute(key(i),(key,src)->{int[] a=new int[src.a.length];int s=0;for(int j=0;j<a.length;j++){a[j]=3*src.a[j]+7;s=31*s+a[j];}Value next=new Value(ids.incrementAndGet(),i,src.bg+1,a,s);events.add(obj("kind","B","job",i,"source",src.id,"id",next.id,"epoch",next.bg,"seed",s));writes.incrementAndGet();return next;});}
    void inject(int i)throws Exception{writer.submit(()->background(i)).get(2,TimeUnit.SECONDS);}
    void complete(int i,Value v)throws Exception{
      ready(i);if(done[i]!=null)throw new AssertionError("duplicate completion");done[i]=v;events.add(obj("kind","D","job",i,"id",v.id));
      if(kind.equals("postwrite")&&i==0&&!forcedPost){inject(0);forcedPost=true;}
    }
    boolean replayFailure(int i)throws Exception{
      if(kind.equals("concurrent"))return false;
      if(pos>=schedule.length())throw new IllegalArgumentException("schedule exhausted");char c=schedule.charAt(pos++);if(c!='S'&&c!='F')throw new IllegalArgumentException("outcome");if(c=='F')inject(i);return c=='F';
    }
    void failure(int i,Value before){failureWitnesses.add(new int[]{i,before.bg+1});}
    void execute()throws Exception{
      if(kind.equals("concurrent")){CountDownLatch go=new CountDownLatch(1);concurrent=writer.submit(()->{try{go.await();}catch(InterruptedException e){Thread.currentThread().interrupt();return;}Random rng=new Random(seed);for(int k=0;k<B;k++){for(int z=0;z<rng.nextInt(17);z++)Thread.yield();background(rng.nextInt(in.n));}});go.countDown();}
      int mask=(1<<in.n)-1,b=B;
      while(mask!=0){int[] choice=in.choose(mask,b);int i=choice[0],mode=choice[1];ready(i);
        if(mode==2){callbacks[i]++;Value v=map.compute(key(i),(key,src)->kernel(src,true));trace.add(i+":P");complete(i,v);mask^=1<<i;continue;}
        Value before=map.get(key(i)),prepared=kernel(before,false);boolean requested=replayFailure(i);boolean ok;
        if(mode==0){boolean[] match={false};callbacks[i]++;Value v=map.compute(key(i),(key,src)->{match[0]=src==before;return match[0]?prepared:kernel(src,true);});ok=match[0];trace.add(i+":C"+(ok?"S":"F"));if(!ok){failure(i,before);if(--b<0)throw new AssertionError("failure budget");}complete(i,v);mask^=1<<i;
        }else{
          if(in.v[i]<=in.g[i]+in.r[i]){conditionals[i]++;ok=map.replace(key(i),before,prepared);trace.add(i+":V"+(ok?"S":"F"));}
          else{boolean[] match={false};callbacks[i]++;map.compute(key(i),(key,src)->{match[0]=src==before;return match[0]?prepared:src;});ok=match[0];trace.add(i+":A"+(ok?"S":"F"));}
          if(ok){complete(i,prepared);mask^=1<<i;}else{failure(i,before);if(--b<0)throw new AssertionError("failure budget");}
        }
        if(!kind.equals("concurrent")&&ok==requested)throw new AssertionError("replay outcome mismatch");
      }
      if(concurrent!=null)concurrent.get(2,TimeUnit.SECONDS);
      if(!kind.equals("concurrent")&&pos!=schedule.length())throw new IllegalArgumentException("unused outcomes");
      if(writes.get()>B)throw new AssertionError("write quota");
    }
    Map<String,Object> result(String status,String error,long elapsed){
      long cost=work;for(int i=0;i<in.n;i++){cost+=8L*in.p[i]*protectedCalls[i]+8L*(in.g[i]+in.r[i])*callbacks[i];if(!mutant.equals("skip_conditional_fee"))cost+=8L*in.v[i]*conditionals[i];}
      long[] completed=new long[in.n],live=new long[in.n];for(int i=0;i<in.n;i++){completed[i]=done[i]==null?-1:done[i].id;live[i]=map.get(key(i)).id;}
      return obj("id",id,"status",status,"error",error,"work",work,"protected_calls",protectedCalls,"callbacks",callbacks,"conditionals",conditionals,"cost",cost,"ceiling",in.ceiling(B),"writes",writes.get(),"failures",failureWitnesses,"trace",trace,"completed",completed,"live",live,"events",events,"elapsed_ns",elapsed,"initialization_ns",setupNs);
    }
  }
  public static void main(String[] args)throws Exception{
    Path dir=Path.of(args[0]);Map<String,Input> inputs=new HashMap<>();for(String row:Files.readAllLines(dir.resolve("CASES.tsv"))){Input in=new Input(row,dir);inputs.put(in.id,in);}
    long end=System.nanoTime()+TimeUnit.SECONDS.toNanos(180);
    for(String row:Files.readAllLines(dir.resolve("RUNS.tsv"))){Run run=new Run(row,inputs);String status="SUCCESS",error="";long t=System.nanoTime();
      try{if(t>=end){status="NOT_RUN";error="campaign cap";}else run.execute();}
      catch(TimeoutException e){status="TIMEOUT";error=e.toString();}catch(IllegalArgumentException e){status="INVALID";error=e.toString();}catch(Throwable e){status="FAILURE";error=e.toString();}
      finally{run.writer.shutdownNow();run.writer.awaitTermination(2,TimeUnit.SECONDS);}
      System.out.println(json(run.result(status,error,System.nanoTime()-t)));System.out.flush();
    }
  }
}
