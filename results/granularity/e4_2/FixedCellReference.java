import java.util.*;
import ltsa.updatingControllers.otf.*;
/** Independent fixed n=2 input. cell() is copied without modifications from the preexisting ContractMergeTest fixture. */
public final class FixedCellReference {
    static CellRingDriver.Fixture make() {
        FineGrainedUpdateProblem<String,String> p=cell();
        FiniteLts<String> oe=FiniteLts.<String>builder("x_A").addTransition("x_A","m_B","x_B").addTransition("x_B","m_A","x_A").build();
        FiniteLts<String> ne=FiniteLts.<String>builder("z_A").addTransition("z_A","m_B","y_B").addTransition("y_B","j","z_B").addTransition("z_B","m_A","z_A").addTransition("z_B","j","z_B").build();
        FiniteLts<String> oc=FiniteLts.<String>builder("c_o").addTransition("c_o","m_A","c_o").addTransition("c_o","m_B","c_o").build();
        FiniteLts<String> nc=FiniteLts.<String>builder("c_0").addTransition("c_0","m_A","c_0").addTransition("c_0","j","c_0").addTransition("c_0","m_B","c_1").addTransition("c_1","j","c_0").addTransition("c_1","m_B","c_1").build();
        Map<String,InitialSnapshot<String,String>> op=new LinkedHashMap<>();
        op.put("x_A",new InitialSnapshot<>(PhysicalState.of(TaggedState.oldState("h"),TaggedState.oldState("e")),map("old","k")));
        op.put("x_B",new InitialSnapshot<>(PhysicalState.of(TaggedState.oldState("e"),TaggedState.oldState("h")),map("old","k")));
        Map<String,GoalSignature<String,String>> np=new LinkedHashMap<>();
        np.put("z_A",new GoalSignature<>("h",PhysicalState.of(TaggedState.newState("h"),TaggedState.newState("e")),map("inspect","c")));
        np.put("y_B",new GoalSignature<>("y_B",PhysicalState.of(TaggedState.newState("e"),TaggedState.newState("h")),map("inspect","d")));
        np.put("z_B",new GoalSignature<>("e",PhysicalState.of(TaggedState.newState("e"),TaggedState.newState("h")),map("inspect","c")));
        return new CellRingDriver.Fixture(2,p,oe,ne,oc,nc,op,np);
    }
    /** Exact finite primitives from paper S1 / check_witnesses.py cell(False). */
    private static FineGrainedUpdateProblem<String,String> cell() {
        FiniteLts<String> a = FiniteLts.<String>builder("h").addTransition("h","m_B","e").addTransition("e","m_A","h").build();
        FiniteLts<String> bo = FiniteLts.<String>builder("e").addTransition("e","m_B","h").addTransition("h","m_A","e").build();
        FiniteLts<String> bn = FiniteLts.<String>builder("e").addTransition("e","m_B","h").addTransition("h","m_A","e").addTransition("h","j","h").build();
        SafetyTester<String> one = tester(new String[]{"A","B","E"}, new String[]{"m_A","m_B"},
                new String[][]{{"A","m_B","B"},{"B","m_A","A"},{"A","m_A","E"},{"B","m_B","E"}});
        SafetyTester<String> old = tester(new String[]{"k","E"}, new String[]{"j"}, new String[][]{{"k","j","E"}});
        SafetyTester<String> inspect = tester(new String[]{"c","d","E"}, new String[]{"m_A","m_B","j"},
                new String[][]{{"c","m_B","d"},{"d","j","c"},{"d","m_A","E"}});
        Set<String> alphabet = set("m_A","m_B","j","rho_A","rho_B","s","t");
        ActivationSpec.Builder<String,String,String> ia = ActivationSpec.builder(residual(inspect,alphabet));
        ActivationSpec.Builder<String,String,String> oa = ActivationSpec.builder(residual(one,alphabet));
        for (ComponentVersion va : ComponentVersion.values()) for (ComponentVersion vb : ComponentVersion.values())
            for (String x : set("h","e")) for (String y : set("h","e")) {
                PhysicalState<String> p = PhysicalState.of(TaggedState.of(va,x),TaggedState.of(vb,y));
                String q = y.equals("h")?"d":"c"; ia.put(p,q,q);
                if (va==ComponentVersion.OLD && vb==ComponentVersion.OLD && !x.equals(y)) {
                    String holder=x.equals("h")?"A":"B"; oa.put(p,holder,holder);
                }
            }
        FineGrainedUpdateProblem.Builder<String,String> b = FineGrainedUpdateProblem.<String,String>builder()
                .addComponent(new VersionedComponent<>("A",a,a,Collections.singletonMap("e",set("e")),"rho_A"))
                .addComponent(new VersionedComponent<>("B",bo,bn,Collections.singletonMap("e",set("e")),"rho_B"))
                .controllableNormalActions(set("m_A","m_B","j"))
                .addRequirement(Requirement.oldRequirement("old",old,"t"))
                .addRequirement(Requirement.newRequirement("inspect",inspect,ia.build(),"s"))
                .addRequirement(Requirement.updateTimeRequirement("one",one,oa.build())).addPrecedence("s","t");
        for (String x : set("h","e")) {
            String y=x.equals("h")?"e":"h";
            b.addInitialSnapshot(new InitialSnapshot<>(PhysicalState.of(TaggedState.oldState(x),TaggedState.oldState(y)),map("old","k")))
             .addGoalSignature(new GoalSignature<>(x,PhysicalState.of(TaggedState.newState(x),TaggedState.newState(y)),map("inspect","c")));
        }
        return b.build();
    }

    private static SafetyTester<String> tester(String[] states,String[] actions,String[][] changes) {
        SafetyTester.Builder<String> b=SafetyTester.<String>builder().initialState(states[0]).addErrorState("E");
        for(String q:states) for(String a:actions) {
            String next=q;
            for(String[] e:changes) if(e[0].equals(q)&&e[1].equals(a)) next=e[2];
            b.addTransition(q,a,next);
        }
        return b.build();
    }
    private static ResidualLanguage<String> residual(final SafetyTester<String> t, final Set<String> alphabet) {
        return new ResidualLanguage<String>() {
            public Set<String> states(){return t.states();}
            public Set<String> alphabet(){return alphabet;}
            public String initialState(){return t.initialState();}
            public String step(String q,String a){return t.stepOrStutter(q,a);}
            public boolean isError(String q){return t.isError(q);}
        };
    }
    private static Set<String> set(String...values){return new LinkedHashSet<>(Arrays.asList(values));}
    private static Map<String,String> map(String...values){Map<String,String> r=new LinkedHashMap<>(); for(int i=0;i<values.length;i+=2)r.put(values[i],values[i+1]);return r;}
}
