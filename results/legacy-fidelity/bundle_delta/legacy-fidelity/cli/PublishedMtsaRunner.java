package fidelity;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import ltsa.lts.*;
import ltsa.dispatcher.TransitionSystemDispatcher;

/** Headless adapter only: the lab-maintained original DUCS JAR is unmodified. */
public final class PublishedMtsaRunner {
    private static final class Output implements LTSOutput, AutoCloseable {
        final PrintWriter file;
        boolean noController;
        Output(Path path) throws IOException { file = new PrintWriter(Files.newBufferedWriter(path, StandardCharsets.UTF_8)); }
        public void out(String s) { file.print(s); file.flush(); }
        public void outln(String s) { if (s.startsWith("There is no controller for model ")) noController = true; file.println(s); file.flush(); }
        public void clearOutput() { /* Preserve compiler and solver diagnostics. */ }
        public void close() { file.close(); }
        void metric(String key, Object value, String decision) {
            file.println(key + "," + value + ",published_mtsa," + decision + "," + decision);
        }
    }
    public static void main(String[] args) { System.exit(run(args)); }
    static boolean completedUnrealizable(Throwable failure, boolean explicitNoController) {
        return explicitNoController && failure instanceof LTSCompositionException;
    }
    static int run(String[] args) {
        try {
            Map<String,String> options = new HashMap<>();
            for (int i=0;i<args.length;i+=2) {
                if (i+1>=args.length || !args[i].startsWith("--")) throw new IllegalArgumentException("Expected --option value pairs");
                options.put(args[i].substring(2),args[i+1]);
            }
            for (String key : Arrays.asList("lts","target","output","transitions"))
                if (!options.containsKey(key)) throw new IllegalArgumentException("Missing --"+key);
            if (!"summary".equals(options.getOrDefault("transition-output",options.getOrDefault("transition-output-mode","summary"))))
                throw new IllegalArgumentException("This adapter supports structural summary only");
            Path model=Paths.get(options.get("lts")).toAbsolutePath();
            String target=options.get("target");
            try (Output output = new Output(Paths.get(options.get("output")))) {
                long begin=System.nanoTime();
                LTSCompiler compiler=new LTSCompiler(new LTSInputString(new String(Files.readAllBytes(model),StandardCharsets.UTF_8)),output,model.getParent().toString());
                compiler.compile();
                // continueCompilation otherwise silently falls back to another composite.
                if (!compiler.getComposites().containsKey(target)) throw new IllegalArgumentException("Unknown composite: "+target);
                CompositeState state=null;
                long compiled;
                try {
                    // A named || composite wraps the inner updating controller.
                    // Its synthesis can already occur during continueCompilation.
                    state=compiler.continueCompilation(target);
                    compiled=System.nanoTime();
                    TransitionSystemDispatcher.applyComposition(state,output);
                } catch (LTSCompositionException failure) {
                    // CompositionExpression throws this after a completed inner GR LOSS.
                    // Unrelated composition errors must remain crashes.
                    if (!completedUnrealizable(failure,output.noController)) throw failure;
                    state=null;
                    compiled=System.nanoTime();
                    output.outln("Adapter retained the explicit inner DUCS no-controller decision.");
                }
                long composed=System.nanoTime();
                CompactState controller=state==null?null:state.composition;
                String decision=controller!=null?"REALIZABLE":output.noController?"UNREALIZABLE":"UNKNOWN";
                output.outln("================ EVALUATION DATA CSV ================");
                output.outln("metric_key,value,mode,result,solver_status");
                output.metric("published_compile_time_ms",(compiled-begin)/1e6,decision);
                output.metric("published_compose_time_ms",(composed-compiled)/1e6,decision);
                output.metric("published_compile_compose_time_ms",(composed-begin)/1e6,decision);
                output.metric("output_update_controller_states",controller==null?0:controller.maxStates,decision);
                output.metric("output_update_controller_transitions",controller==null?0:controller.ntransitions(),decision);
                output.outln("================ EVALUATION SUMMARY ================");
                output.outln("Headless adapter result: "+decision);
                if (controller!=null) {
                    String summary="Process:\n\t"+target+"\nStates:\n\t"+controller.maxStates+"\nTransitions:\n\t"+controller.ntransitions()+"\nRepresentation:\n\tstructural summary\n";
                    Files.write(Paths.get(options.get("transitions")),summary.getBytes(StandardCharsets.UTF_8));
                    return 0;
                }
                return output.noController?6:2;
            }
        } catch (OutOfMemoryError e) { e.printStackTrace(System.err); return 5;
        } catch (Throwable e) { e.printStackTrace(System.err); return 4; }
    }
}
