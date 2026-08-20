package ltsa.lts;

import org.junit.Assert;
import org.testng.annotations.Test;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.List;
import java.util.Map;

@Test(singleThreaded = true)
public class NativeSourceDependencyFactsRunnerTest {

    @Test
    public void machineFactPreservesExplicitRequiredTransitionsOnly() {
        CompactState machine = new CompactState();
        machine.name = "FACT_MACHINE";
        machine.maxStates = 2;
        machine.alphabet = new String[]{"tau", "move", "move?"};
        machine.states = new EventState[2];
        machine.states[0] = new EventState(1, 1);
        machine.states[1] = new EventState(1, 1);

        Map<String, Object> fact =
                NativeSourceDependencyFactsRunner.machineFact(machine);
        Assert.assertEquals("FACT_MACHINE", fact.get("name"));
        Assert.assertEquals(Long.valueOf(2L), fact.get("max_states"));
        Assert.assertEquals(
                Arrays.asList("tau", "move", "move?"),
                fact.get("alphabet"));
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> transitions =
                (List<Map<String, Object>>) fact.get("transitions");
        Assert.assertEquals(2, transitions.size());
        Assert.assertEquals(Long.valueOf(0L), transitions.get(0).get("source"));
        Assert.assertEquals(Long.valueOf(1L),
                transitions.get(0).get("action_index"));
        Assert.assertEquals(Arrays.asList(Integer.valueOf(1)),
                transitions.get(0).get("targets"));
        Assert.assertEquals(Long.valueOf(1L), transitions.get(1).get("source"));
    }

    @Test
    public void runnerBytecodeDoesNotReferenceFactorizerAdapterOrUpdateGameSolver() throws Exception {
        String resource = "/ltsa/lts/NativeSourceDependencyFactsRunner.class";
        InputStream input = NativeSourceDependencyFactsRunner.class
                .getResourceAsStream(resource);
        Assert.assertNotNull(input);
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        byte[] block = new byte[8192];
        int read;
        while ((read = input.read(block)) >= 0) {
            bytes.write(block, 0, read);
        }
        String constantPool = new String(
                bytes.toByteArray(), StandardCharsets.ISO_8859_1);
        for (String forbidden : Arrays.asList(
                "NativeTierAFactorizer",
                "NativeTierABundleExporter",
                "MtsaRevisedOtfDucsAdapter",
                "FineGrainedOtfDucs",
                "IndependentExplicitStrongSolver")) {
            Assert.assertFalse(
                    "facts runner must not reference " + forbidden,
                    constantPool.contains(forbidden));
        }
    }
}
