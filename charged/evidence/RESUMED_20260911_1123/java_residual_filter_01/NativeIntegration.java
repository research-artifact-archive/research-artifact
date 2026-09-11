import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;

/** Minimal authored integration of the existing per-key wrapper pattern.
 * Not a real client, native-speed study, JMM proof, or fairness/progress proof.
 */
public final class NativeIntegration {
    // No equals override: map values have reference identity; all fields immutable.
    static final class Value {
        final long id, payload;
        final int job;
        Value(long id,int job,long payload) { this.id=id;this.job=job;this.payload=payload; }
    }
    static final class Key {
        final int job; final boolean collision;
        Key(int job,boolean collision) { this.job=job;this.collision=collision; }
        @Override public int hashCode() { return collision?0:job; }
        @Override public boolean equals(Object other) { return other instanceof Key k && k.job==job && k.collision==collision; }
    }
    record Input(String id,String root,String fixture,long[] weights,int[] pred,int r,
                 String policy,String layout,String boundary,String pattern) {
        static Input parse(String row) {
            String[] a=row.split("\t",-1);
            if(a.length!=10) throw new IllegalArgumentException("input columns");
            Input c=new Input(a[0],a[1],a[2],Json.longs(a[3]),Json.ints(a[4]),Integer.parseInt(a[5]),a[6],a[7],a[8],a[9].equals("-")?"":a[9]);
            int n=c.weights.length;
            if(n<1||n>6||c.pred.length!=n||c.r<0||c.r>2||!Set.of("filter","allfresh","allcached").contains(c.policy)||!Set.of("distinct","colliding").contains(c.layout)||!Set.of("normal","postwrite","doublewrite").contains(c.boundary)||!c.pattern.matches("[01]*")) throw new IllegalArgumentException("input shape");
            for(int i=0;i<n;i++) if(c.weights[i]<=0||c.weights[i]>100||c.pred[i]<0||(c.pred[i]&~((1<<i)-1))!=0) throw new IllegalArgumentException("invalid weight/order");
            return c;
        }
    }
    /** Pure whole-kernel on captured immutable own input and captured immutable
     * saved-parent list. No live map reads, recursive updates, diagnostics, IDs,
     * write counters, clocks, or policy access. Signed wraparound is intentional
     * payload semantics; it is unrelated to checked body-work accounting.
     */
    static long pureKernel(Value own,List<Value> parents,long weight) {
        long parentFold=0;
        for(Value parent:parents) parentFold=31*parentFold+parent.payload;
        long payload=own.payload;
        for(long step=0;step<weight;step++) payload=1664525L*payload+1013904223L+parentFold;
        return payload;
    }
    record Answer(Value output,boolean success,Boolean match) {}
    static final class Controller {
        final String policy;final int r;
        final ResidualFilter filter;
        int failures;
        Controller(String policy,int r) { this.policy=policy;this.r=r;filter=policy.equals("filter")?new ResidualFilter():null; }
        String select(long currentWeight) {
            if(policy.equals("allfresh")) return "fresh";
            if(failures<r) return "cheap";
            return filter!=null && filter.permitsFresh(currentWeight) ? "fresh":"cached";
        }
        // Only declared weight and public wrapper outcome cross this boundary.
        void observe(long weight,String mode,Answer answer) {
            if(!answer.success()) { if(!mode.equals("cheap")) throw new AssertionError("noncheap failure"); failures++; return; }
            if(filter!=null) filter.recordCompletion(weight,mode.equals("fresh")?ResidualFilter.Outcome.FRESH:
                mode.equals("cached") && !answer.match()?ResidualFilter.Outcome.MISMATCH:ResidualFilter.Outcome.MATCH);
        }
    }
    static final class Run {
        final Input c;
        final ConcurrentHashMap<Key,Value> map=new ConcurrentHashMap<>(64);
        final Key[] keys;
        final Value[] done;
        final List<Object> events=new ArrayList<>();
        final ExecutorService writer=Executors.newSingleThreadExecutor(r->new Thread(r,"residual-external-writer"));
        final Controller controller;
        long nextId,bodyW,bodyL,actualWrites;
        int Q,patternPos;
        boolean writerStopped;
        Run(Input c) {
            this.c=c;keys=new Key[c.weights.length];done=new Value[keys.length];
            controller=new Controller(c.policy,c.r);
            for(int i=0;i<keys.length;i++) {
                keys[i]=new Key(i,c.layout.equals("colliding"));
                Value v=value(i,17L*(i+1));map.put(keys[i],v);
                events.add(Json.obj("kind","initial","job",i,"id",v.id,"payload",v.payload));
            }
        }
        Value value(int job,long payload) { nextId=Math.addExact(nextId,1);return new Value(nextId,job,payload); }
        List<Value> parents(int job) {
            List<Value> parents=new ArrayList<>();
            for(int i=0;i<done.length;i++) if((c.pred[job]&(1<<i))!=0) {
                if(done[i]==null) throw new AssertionError("unready parent");parents.add(done[i]);
            }
            return List.copyOf(parents);
        }
        Value body(Value source,List<Value> parents,long weight,boolean protectedBody) {
            long payload=pureKernel(source,parents,weight);
            bodyW=Math.addExact(bodyW,weight);if(protectedBody) bodyL=Math.addExact(bodyL,weight);
            Value out=value(source.job,payload);
            List<Long> parentIds=parents.stream().map(p->p.id).toList();
            events.add(Json.obj("kind","body","job",source.job,"source",source.id,"parents",parentIds,"out",out.id,"payload",out.payload,"weight",weight,"protected",protectedBody));
            return out;
        }
        void write(int job,String phase) throws Exception {
            writer.submit(()->{
                Value before=map.get(keys[job]);
                Value out=map.compute(keys[job],(key,current)->value(job,3*current.payload+7));
                // Count and trace AFTER the actual external map publication returns.
                actualWrites=Math.addExact(actualWrites,1);
                events.add(Json.obj("kind","write","job",job,"source",before.id,"out",out.id,"payload",out.payload,"phase",phase));
            }).get(2,TimeUnit.SECONDS);
        }
        Answer fresh(int job,List<Value> parents) {
            Q=Math.addExact(Q,1);
            Value out=map.compute(keys[job],(key,current)->body(current,parents,c.weights[job],true));
            return new Answer(out,true,null);
        }
        Answer cheap(int job,Value captured,Value prepared) {
            Q=Math.addExact(Q,1);boolean[] matched={false};
            map.compute(keys[job],(key,current)->{
                matched[0]=current==captured;
                events.add(Json.obj("kind","compare","mode","cheap","job",job,"captured",captured.id,"current",current.id,"prepared",prepared.id,"match",matched[0]));
                return matched[0]?prepared:current;
            });
            return new Answer(matched[0]?prepared:null,matched[0],matched[0]);
        }
        Answer cached(int job,Value captured,Value prepared,List<Value> parents) {
            Q=Math.addExact(Q,1);boolean[] matched={false};
            Value out=map.compute(keys[job],(key,current)->{
                matched[0]=current==captured;
                events.add(Json.obj("kind","compare","mode","cached","job",job,"captured",captured.id,"current",current.id,"prepared",prepared.id,"match",matched[0]));
                return matched[0]?prepared:body(current,parents,c.weights[job],true);
            });
            return new Answer(out,true,matched[0]);
        }
        void execute() throws Exception {
            int job=0;
            while(job<done.length) {
                if(Q>=done.length+c.r) throw new AssertionError("call cap");
                List<Value> savedParents=parents(job);
                String mode=controller.select(c.weights[job]);
                events.add(Json.obj("kind","select","job",job,"mode",mode,"filter",controller.filter==null?null:controller.filter.state()));
                Answer answer;
                if(mode.equals("fresh")) answer=fresh(job,savedParents);
                else {
                    Value captured=map.get(keys[job]);
                    Value prepared=body(captured,savedParents,c.weights[job],false);
                    if(patternPos>=c.pattern.length()) throw new IllegalArgumentException("schedule exhausted");
                    boolean bad=c.pattern.charAt(patternPos++)=='1';
                    if(bad) for(int w=0;w<(c.boundary.equals("doublewrite")?2:1);w++) write(job,"gate");
                    answer=mode.equals("cheap")?cheap(job,captured,prepared):cached(job,captured,prepared,savedParents);
                }
                // Deliberate competing publication before storing the saved output.
                if(answer.success() && job==0 && c.boundary.equals("postwrite")) write(job,"after-return-before-save");
                if(answer.success()) {
                    if(done[job]!=null||answer.output()==null) throw new AssertionError("completion once");
                    done[job]=answer.output();
                }
                controller.observe(c.weights[job],mode,answer);
                events.add(Json.obj("kind","answer","job",job,"mode",mode,"success",answer.success(),"match",answer.match(),"saved",answer.output()==null?null:answer.output().id,"live",map.get(keys[job]).id,"filter",controller.filter==null?null:controller.filter.state()));
                if(answer.success()) job++;
            }
            if(patternPos!=c.pattern.length()) throw new IllegalArgumentException("unused schedule");
        }
        Map<String,Object> result(String status,String error) {
            List<Object> outputs=new ArrayList<>(),live=new ArrayList<>();
            for(int i=0;i<done.length;i++) {
                Value v=done[i];outputs.add(v==null?null:Json.obj("id",v.id,"payload",v.payload));
                Value l=map.get(keys[i]);live.add(Json.obj("id",l.id,"payload",l.payload));
            }
            return Json.obj("id",c.id,"root",c.root,"status",status,"error",error,"actualExternalWrites",actualWrites,"bodyW",bodyW,"bodyL",bodyL,"Q",Q,"savedOutputs",outputs,"liveOutputs",live,"writerTerminated",writerStopped,"events",events);
        }
    }
    public static void main(String[] args) throws Exception {
        long deadline=System.nanoTime()+TimeUnit.SECONDS.toNanos(115);
        for(String row:Files.readAllLines(Path.of(args[0]))) {
            Run run=new Run(Input.parse(row));String status="SUCCESS",error="";
            try {
                if(System.nanoTime()>=deadline) { status="NOT_EXECUTED";error="native process deadline"; }
                else run.execute();
            } catch(TimeoutException e) { status="TIMEOUT";error=e.toString(); }
              catch(IllegalArgumentException e) { status="INVALID";error=e.toString(); }
              catch(Throwable e) { status="FAILURE";error=e.toString(); }
            finally {
                run.writer.shutdownNow();run.writerStopped=run.writer.awaitTermination(2,TimeUnit.SECONDS);
                if(!run.writerStopped) { status="FAILURE";error+=" writer did not terminate"; }
            }
            System.out.println(Json.encode(run.result(status,error)));System.out.flush();
        }
    }
}
