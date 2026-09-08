import java.nio.*;
import java.nio.file.*;
import java.security.*;
import java.util.*;
import java.util.concurrent.*;

public final class NativeDagFinal {
  static final class Value {
    final int[] a; final int generation,slot,seed;
    Value(int[] a,int generation,int slot,int seed){this.a=a;this.generation=generation;this.slot=slot;this.seed=seed;}
  }
  static final ExecutorService worker=Executors.newSingleThreadExecutor(r->{Thread t=new Thread(r,"dag-external-writer");t.setDaemon(true);return t;});
  static int[] ints(String s){return s.equals("-")||s.isEmpty()?new int[0]:Arrays.stream(s.split(",")).mapToInt(Integer::parseInt).toArray();}
  static String quote(String s){return "\""+s.replace("\\","\\\\").replace("\"","\\\"").replace("\n","\\n").replace("\r","\\r").replace("\t","\\t")+"\"";}
  static int fold(int[] a){int seed=0;for(int x:a)seed=31*seed+x;return seed;}
  static Value initial(int key,int size){int[] a=new int[size];for(int j=0;j<size;j++)a[j]=17*(key+1)+31*j;return new Value(a,0,key,fold(a));}
  static Value background(Value v){int[] a=new int[v.a.length];for(int j=0;j<a.length;j++)a[j]=3*v.a[j]+7;return new Value(a,v.generation+1,v.slot,fold(a));}
  static String digest(Value v)throws Exception{
    if(v==null)return "MISSING";
    ByteBuffer b=ByteBuffer.allocate(4*v.a.length).order(ByteOrder.LITTLE_ENDIAN);for(int x:v.a)b.putInt(x);
    return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(b.array()));
  }
  static final class Case {
    final String id;final int[] c,p,pred,lengths,weights;final int d,scale;
    final Map<Integer,long[][]> profiles=new HashMap<>();
    final boolean ordered;final int[] orderedJobs;final long[] thresholds;
    Case(String line,Path directory)throws Exception{
      String[] z=line.split("\t",-1);id=z[0];c=ints(z[1]);p=ints(z[2]);pred=ints(z[3]);lengths=ints(z[4]);weights=ints(z[5]);d=Integer.parseInt(z[6]);scale=Integer.parseInt(z[7]);
      if(c.length>6||p.length!=c.length||pred.length!=c.length||lengths.length!=c.length||weights.length!=c.length)throw new IllegalArgumentException("shape");
      for(int i=0;i<c.length;i++)if(lengths[i]+Integer.bitCount(pred[i])!=scale*c[i]||(long)weights[i]*c[i]!=(long)d*p[i])throw new IllegalArgumentException("price mapping");
      List<String> encoded=Files.readAllLines(directory.resolve(z[8]));
      ordered=encoded.get(0).startsWith("ORDER\t");
      if(ordered){
        if(encoded.size()!=2)throw new IllegalArgumentException("ordered file shape");
        orderedJobs=ints(encoded.get(0).split("\t",-1)[1]);
        String[] ts=encoded.get(1).split("\t",-1);
        if(!ts[0].equals("THRESHOLDS"))throw new IllegalArgumentException("threshold header");
        thresholds=Arrays.stream(ts[1].split(",")).mapToLong(Long::parseLong).toArray();
        if(orderedJobs.length!=c.length||thresholds.length!=c.length)throw new IllegalArgumentException("ordered shape");
        int done=0;
        for(int k=0;k<orderedJobs.length;k++){int i=orderedJobs[k];
          if(i<0||i>=c.length||(done&(1<<i))!=0||(pred[i]&done)!=pred[i]||thresholds[k]<0||(k>0&&c[orderedJobs[k-1]]>c[i]))throw new IllegalArgumentException("ordered topology/cost/threshold");
          done|=1<<i;
        }
      }else{
      orderedJobs=new int[0];thresholds=new long[0];
      for(String row:encoded){
        String[] parts=row.split("\t");String[] pieces=parts[1].split(";");long[][] f=new long[pieces.length][3];
        for(int k=0;k<pieces.length;k++){String[] a=pieces[k].split(":");for(int j=0;j<3;j++)f[k][j]=Long.parseLong(a[j]);}
        if(f[0][0]!=0||f[0][1]!=0||f[f.length-1][2]!=0)throw new IllegalArgumentException("profile endpoints");
        profiles.put(Integer.parseInt(parts[0]),f);
      }
      }
    }
    long value(int s,int b){long[][] f=profiles.get(s);if(f==null)throw new IllegalArgumentException("missing state");long[] q=f[0];for(long[] part:f){if(part[0]>b)break;q=part;}return q[1]+(b-q[0])*q[2];}
    boolean available(int s,int i){return (s&(1<<i))!=0&&(s&pred[i])==0;}
  }
  static final class Run {
    final String id,kind,layout,outcomes;final Case input;final int B;final int[] order;final boolean postwrite;
    final ConcurrentHashMap<Integer,Value> map=new ConcurrentHashMap<>(64);
    final Value[] milestones;final long[] protectedByKey;
    final List<String> actions=Collections.synchronizedList(new ArrayList<>()),parentInputs=new ArrayList<>();
    final Map<String,Long> memo=new HashMap<>();
    int pos=0,backgroundCount=0,publicFalse=0,cursor=0;long work=0;boolean postwriteDone=false;
    Run(String line,Map<String,Case> cases){
      String[] z=line.split("\t",-1);id=z[0];input=cases.get(z[1]);kind=z[2];layout=z[3];B=Integer.parseInt(z[4]);order=ints(z[5]);outcomes=z[6].equals("-")?"":z[6];postwrite=z[7].equals("1");
      if(input==null||(!layout.equals("distinct")&&!layout.equals("colliding")))throw new IllegalArgumentException("unknown input");
      milestones=new Value[input.c.length];protectedByKey=new long[input.c.length];for(int i=0;i<milestones.length;i++)map.put(storage(i),initial(i,input.lengths[i]));
    }
    int storage(int i){return layout.equals("colliding")?128*i:i;}
    void ready(int i){for(int j=0;j<milestones.length;j++)if((input.pred[i]&(1<<j))!=0&&milestones[j]==null)throw new AssertionError("early kernel or commit "+i+" missing "+j);}
    void charge(int i,boolean inside){work++;if(inside)protectedByKey[i]++;}
    Value transform(Value v,boolean inside){
      int i=v.slot;ready(i);int parent=0;
      for(int j=0;j<milestones.length;j++)if((input.pred[i]&(1<<j))!=0){parent=31*parent+milestones[j].seed;charge(i,inside);}
      parentInputs.add(i+":"+parent);int[] a=new int[v.a.length];int seed=0;
      for(int j=0;j<a.length;j++){a[j]=1664525*v.a[j]+1013904223+parent;seed=31*seed+a[j];charge(i,inside);}
      return new Value(a,v.generation+1,i,seed);
    }
    void inject(int i,boolean after)throws Exception{
      worker.submit(()->map.compute(storage(i),(k,v)->{Value next=background(v);if(after)actions.add(i+":G_AFTER");return next;})).get(2,TimeUnit.SECONDS);backgroundCount++;
    }
    void complete(int i,Value v)throws Exception{
      ready(i);if(milestones[i]!=null)throw new AssertionError("duplicate milestone");milestones[i]=v;
      if(kind.equals("hybrid")&&input.ordered){if(cursor>=input.orderedJobs.length||input.orderedJobs[cursor]!=i)throw new AssertionError("cursor completion");cursor++;}
      if(postwrite&&i==0&&!postwriteDone){inject(0,true);postwriteDone=true;}
    }
    char outcome(){if(pos>=outcomes.length())throw new IllegalArgumentException("schedule exhausted");return outcomes.charAt(pos++);}
    long upper(int s,int b){long best=Long.MAX_VALUE;for(int k=-1;k<input.c.length;k++){
      if(k>=0&&(s&(1<<k))==0)continue;long t=k<0?0:input.c[k],v=b*t;
      for(int i=0;i<input.c.length;i++)if((s&(1<<i))!=0&&input.c[i]>t)v+=input.p[i];best=Math.min(best,v);
    }return best;}
    int first(int s){for(int i:order)if((s&(1<<i))!=0)return i;throw new AssertionError("fixed order exhausted");}
    long restricted(int s,int b,boolean fixed){
      if(s==0||b==0)return 0;String key=s+":"+b;if(memo.containsKey(key))return memo.get(key);long best=Long.MAX_VALUE;
      for(int i=0;i<input.c.length;i++)if(input.available(s,i)&&(!fixed||i==first(s))){
        int rest=s^(1<<i);long g=restricted(rest,b,fixed);
        best=Math.min(best,input.p[i]+g);
        best=Math.min(best,Math.max(g,input.c[i]+(fixed?restricted(s,b-1,true):input.p[i]+restricted(rest,b-1,false))));
      }memo.put(key,best);return best;
    }
    int[] select(int s,int b){
      if(kind.equals("hybrid")){
        if(input.ordered){
          if(cursor>=input.orderedJobs.length)throw new AssertionError("cursor exhausted");
          int suffix=0;for(int k=cursor;k<input.orderedJobs.length;k++)suffix|=1<<input.orderedJobs[k];
          if(s!=suffix)throw new AssertionError("cursor/suffix mismatch");
          return new int[]{input.orderedJobs[cursor],b>=input.thresholds[cursor]?1:0};
        }
        int fast=-1,protectedI=-1;long protectedQ=Long.MAX_VALUE;
        for(int i=0;i<input.c.length;i++)if(input.available(s,i)){
          if(fast<0||input.c[i]<input.c[fast])fast=i;
          long q=input.p[i]+input.value(s^(1<<i),b);if(q<protectedQ){protectedQ=q;protectedI=i;}
        }
        return protectedQ==input.value(s,b)?new int[]{protectedI,1}:new int[]{fast,0};
      }
      if(kind.equals("fixed")){
        int i=first(s);long g=restricted(s^(1<<i),b,true),q=input.p[i]+g;
        return new int[]{i,q==restricted(s,b,true)?1:0};
      }
      boolean cached=kind.equals("cached"),pTie=kind.equals("look_protected");
      long best=Long.MAX_VALUE;int bestRank=2,bestC=Integer.MAX_VALUE,bestI=-1,bestMode=-1;
      for(int i=0;i<input.c.length;i++)if(input.available(s,i))for(int mode=0;mode<2;mode++){
        int rest=s^(1<<i);long q;
        if(mode==1)q=input.p[i]+(cached?restricted(rest,b,false):upper(rest,b));
        else if(b==0)q=0;
        else if(cached)q=Math.max(restricted(rest,b,false),input.c[i]+input.p[i]+restricted(rest,b-1,false));
        else q=Math.max(upper(rest,b),input.c[i]+upper(s,b-1));
        int rank=pTie?1-mode:mode;
        if(q<best||q==best&&(rank<bestRank||rank==bestRank&&(input.c[i]<bestC||input.c[i]==bestC&&i<bestI))){best=q;bestRank=rank;bestC=input.c[i];bestI=i;bestMode=mode;}
      }
      if(bestI<0)throw new AssertionError("no available action");return new int[]{bestI,bestMode};
    }
    void execute()throws Exception{
      int s=(1<<input.c.length)-1,b=B;
      while(s!=0){int[] choice=select(s,b);int i=choice[0];ready(i);
        if(choice[1]==1){Value done=map.compute(storage(i),(k,v)->transform(v,true));actions.add(i+":P");complete(i,done);s^=1<<i;}
        else{
          Value before=map.get(storage(i)),prepared=transform(before,false);char o=outcome();
          if(o=='F'||o=='X'){if(b<=0)throw new IllegalArgumentException("budget exceeded");inject(i,false);b--;}
          if(kind.equals("cached")){
            if(o!='M'&&o!='X')throw new IllegalArgumentException("cached outcome");
            Value done=map.compute(storage(i),(k,v)->{boolean match=v==before;if(match!=(o=='M'))throw new AssertionError("cached match mismatch");return match?prepared:transform(v,true);});
            actions.add(i+":"+o);complete(i,done);s^=1<<i;
          }else{
            if(o!='S'&&o!='F')throw new IllegalArgumentException("fast outcome");
            boolean ok=map.replace(storage(i),before,prepared);if(ok!=(o=='S'))throw new AssertionError("replace mismatch");actions.add(i+":"+o);
            if(ok){complete(i,prepared);s^=1<<i;}else publicFalse++;
          }
        }
      }
      if(pos!=outcomes.length())throw new IllegalArgumentException("unused outcomes");if(backgroundCount>B)throw new AssertionError("total-write budget exceeded");
    }
    String result(String status,String error,long elapsed)throws Exception{
      List<String> live=new ArrayList<>(),captured=new ArrayList<>();List<Integer> generations=new ArrayList<>(),seeds=new ArrayList<>();
      long weighted=0;for(int i=0;i<milestones.length;i++){live.add(quote(digest(map.get(storage(i)))));captured.add(quote(digest(milestones[i])));generations.add(map.get(storage(i)).generation);seeds.add(milestones[i]==null?0:milestones[i].seed);weighted+=(long)input.weights[i]*protectedByKey[i];}
      return "{\"id\":"+quote(id)+",\"status\":"+quote(status)+",\"work\":"+work+",\"protected_by_key\":"+Arrays.toString(protectedByKey)+",\"cost\":"+((long)input.d*work+weighted)+",\"trace\":"+quote(String.join(";",actions))+",\"parent_inputs\":"+quote(String.join(";",parentInputs))+",\"digests\":["+String.join(",",live)+"],\"milestone_digests\":["+String.join(",",captured)+"],\"gens\":"+generations+",\"milestone_seeds\":"+seeds+",\"background\":"+backgroundCount+",\"public_false\":"+publicFalse+",\"elapsed_ns\":"+elapsed+",\"error\":"+quote(error)+"}";
    }
  }
  public static void main(String[] args)throws Exception{
    Path directory=Path.of(args[0]);Map<String,Case> cases=new HashMap<>();for(String line:Files.readAllLines(directory.resolve("CASES.tsv"))){Case c=new Case(line,directory);cases.put(c.id,c);}
    try{for(String line:Files.readAllLines(directory.resolve("INPUTS.tsv"))){Run run=new Run(line,cases);long t=System.nanoTime();String status="SUCCESS",error="";
      try{run.execute();}catch(TimeoutException e){status="TIMEOUT";error=e.toString();}catch(IllegalArgumentException e){status="INVALID";error=e.toString();}catch(Throwable e){status="FAILURE";error=e.toString();}
      System.out.println(run.result(status,error,System.nanoTime()-t));System.out.flush();
    }}finally{worker.shutdownNow();}
  }
}
