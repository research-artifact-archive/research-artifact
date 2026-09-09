import java.util.*;
import java.util.concurrent.*;
import java.nio.file.*;
public class SuffixProbe {
  record Value(int version,long seed) {}
  static final class Selector {
    final int[] works,pred,top; final String policy; int remaining,t,h,ell;
    Selector(int[] w,int[] p,int r,String mode) { works=w.clone();pred=p.clone();policy=mode;remaining=(1<<w.length)-1;t=r;int[] sorted=w.clone();Arrays.sort(sorted);top=new int[w.length+1];for(int i=0;i<w.length;i++)top[i+1]=top[i]+sorted[w.length-i-1]; }
    int job(){int best=-1;for(int i=0;i<works.length;i++)if((remaining&(1<<i))!=0&&(pred[i]&remaining)==0&&(best<0||works[i]<works[best]))best=i;return best;}
    String mode(){if(t>0)return "cheap";int sum=0;for(int i=0;i<works.length;i++)if((remaining&(1<<i))!=0)sum+=works[i];if(policy.equals("tail"))return ell+sum<=top[Math.min(h,works.length)]?"fresh":"cached";if(!policy.equals("certificate"))return "cached";int next=job();List<Integer> suffix=new ArrayList<>();for(int i=0;i<works.length;i++)if(i!=next&&(remaining&(1<<i))!=0)suffix.add(works[i]);suffix.sort(Comparator.reverseOrder());int accumulated=ell+works[next];if(accumulated>top[Math.min(h,works.length)])return "cached";for(int k=0;k<suffix.size();k++){accumulated+=suffix.get(k);if(accumulated>top[Math.min(h+k+1,works.length)])return "cached";}return "fresh";}
    void observe(int i,String mode,boolean mismatch){if(mode.equals("cheap")&&mismatch){t--;return;}if(mode.equals("cached")&&mismatch){h++;ell+=works[i];}if(mode.equals("fresh"))ell+=works[i];remaining^=1<<i;}
  }
  static final class Engine {
    final ConcurrentHashMap<Integer,Value> map=new ConcurrentHashMap<>();final long[] outputs;final int[] w,pred;long W,L,Q;int writes;final List<Object> kernels=new ArrayList<>(),calls=new ArrayList<>();
    Engine(int[] weights,int[] predecessors){w=weights;pred=predecessors;outputs=new long[w.length];for(int i=0;i<w.length;i++)map.put(i,new Value(0,17+31L*i));}
    List<Long> parents(int i){List<Long>a=new ArrayList<>();for(int j=0;j<w.length;j++)if((pred[i]&(1<<j))!=0)a.add(outputs[j]);return a;}
    long kernel(int i,Value v,boolean inside){List<Long>a=parents(i);long x=v.seed();for(long y:a)x^=y;for(int j=0;j<w[i];j++){x=Long.rotateLeft(x,13)*6364136223846793005L+1442695040888963407L;W++;if(inside)L++;}kernels.add(row("job",i,"input_version",v.version(),"inside",inside,"parents",a,"output",x,"iterations",w[i]));return x;}
    void write(int i)throws Exception {Thread thread=new Thread(()->{Value v=map.get(i);map.put(i,new Value(v.version()+1,17+31L*i+104729L*(v.version()+1)));});thread.start();thread.join(3000);if(thread.isAlive())throw new RuntimeException("writer timeout");writes++;}
    void call(int i,String mode,char outcome)throws Exception {
      Value captured=null;long prepared=0;if(!mode.equals("fresh")){captured=map.get(i);prepared=kernel(i,captured,false);}
      if(outcome=='F')write(i);if(mode.equals("fresh")!=(outcome=='P'))throw new RuntimeException("planned mode/path mismatch");
      final Value old=captured;final long cached=prepared;final boolean[] mismatch={false};final long[] value={0};final int[] liveVersion={-1};Q++;
      map.compute(i,(key,live)->{liveVersion[0]=live.version();mismatch[0]=old!=live;
        if(mode.equals("cheap")&&mismatch[0])return live;
        value[0]=mode.equals("fresh")||mismatch[0]?kernel(i,live,true):cached;
        return new Value(live.version(),value[0]);});
      boolean failed=mode.equals("cheap")&&mismatch[0];if(!failed)outputs[i]=value[0];
      if(!mode.equals("fresh")&&mismatch[0]!=(outcome=='F'))throw new RuntimeException("unexpected identity outcome");
      calls.add(row("job",i,"mode",mode,"outcome",String.valueOf(outcome),"input_version",liveVersion[0],"completed",!failed,"output",failed?null:value[0]));
    }
  }
  static Map<String,Object> row(Object...args){Map<String,Object> m=new LinkedHashMap<>();for(int i=0;i<args.length;i+=2)m.put((String)args[i],args[i+1]);return m;}
  static String json(Object x){if(x==null)return "null";if(x instanceof String)return "\""+((String)x).replace("\\","\\\\").replace("\"","\\\"")+"\"";if(x instanceof Number||x instanceof Boolean)return x.toString();if(x instanceof Map<?,?>m){List<String>a=new ArrayList<>();for(var e:m.entrySet())a.add(json(e.getKey())+":"+json(e.getValue()));return "{"+String.join(",",a)+"}";}if(x instanceof Iterable<?>list){List<String>a=new ArrayList<>();for(Object v:list)a.add(json(v));return "["+String.join(",",a)+"]";}if(x instanceof long[]a){List<Long>b=new ArrayList<>();for(long v:a)b.add(v);return json(b);}throw new RuntimeException("json type");}
  public static void main(String[]args)throws Exception {
    int sequence=0;for(String line:Files.readAllLines(Path.of(args[0]))){String[]x=line.split("\t",-1);int[]w=Arrays.stream(x[2].split(",")).mapToInt(Integer::parseInt).toArray();int[]pred=new int[w.length];if(!x[3].isEmpty())for(String edge:x[3].split(";")){String[]uv=edge.split("-");pred[Integer.parseInt(uv[1])]|=1<<Integer.parseInt(uv[0]);}
      Engine e=new Engine(w,pred);Selector s=new Selector(w,pred,Integer.parseInt(x[4]),x[6]);String status="SUCCESS",error="";int at=0;
      try {while(s.remaining!=0){int i=s.job();String mode=s.mode();if(at>=x[7].length())throw new RuntimeException("short path");char c=x[7].charAt(at++);e.call(i,mode,c);s.observe(i,mode,c=='F');}if(at!=x[7].length())throw new RuntimeException("unused path");}
      catch(Exception ex){status="FAILURE";error=ex.toString();}
      System.out.println(json(row("id",x[0],"case",x[1],"r",Integer.parseInt(x[4]),"budget_tag",Integer.parseInt(x[5]),"policy",x[6],"path",x[7],"sequence",sequence++,"status",status,"error",error,"W",e.W,"L",e.L,"Q",e.Q,"writes",e.writes,"kernels",e.kernels,"calls",e.calls,"final_outputs",e.outputs)));}
  }
}
