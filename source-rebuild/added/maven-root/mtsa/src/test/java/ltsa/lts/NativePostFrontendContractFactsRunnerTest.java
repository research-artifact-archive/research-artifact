package ltsa.lts;

import MTSTools.ac.ic.doc.mtstools.model.MTS;
import MTSTools.ac.ic.doc.mtstools.model.impl.MTSImpl;
import org.junit.Assert;
import org.testng.annotations.Test;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.lang.reflect.Field;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

@Test(singleThreaded = true)
public class NativePostFrontendContractFactsRunnerTest {

    @Test
    public void controllerFactPreservesInitialStateAndNondeterminism() {
        MTS<Long, String> source =
                new MTSImpl<Long, String>(Long.valueOf(7L));
        source.addState(Long.valueOf(3L));
        source.addState(Long.valueOf(7L));
        source.addState(Long.valueOf(11L));
        source.addAction("move");
        source.addRequired(Long.valueOf(7L), "move", Long.valueOf(3L));
        source.addRequired(Long.valueOf(7L), "move", Long.valueOf(11L));

        Map<String, Object> fact =
                NativePostFrontendContractFactsRunner.mtsFact(
                        source, "test controller");
        Assert.assertEquals(Long.valueOf(7L), fact.get("initial_state"));
        Assert.assertEquals(
                Arrays.asList(Long.valueOf(3L), Long.valueOf(7L),
                        Long.valueOf(11L)),
                fact.get("states"));
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> transitions =
                (List<Map<String, Object>>) fact.get("required_transitions");
        Assert.assertEquals(1, transitions.size());
        Assert.assertEquals("move", transitions.get(0).get("action"));
        Assert.assertEquals(
                Arrays.asList(Long.valueOf(3L), Long.valueOf(11L)),
                transitions.get(0).get("targets"));
    }

    @Test(expectedExceptions = IllegalArgumentException.class)
    public void controllerFactRejectsMaybeTransitions() {
        MTS<Long, String> source =
                new MTSImpl<Long, String>(Long.valueOf(0L));
        source.addState(Long.valueOf(1L));
        source.addAction("move");
        source.addPossible(Long.valueOf(0L), "move", Long.valueOf(1L));
        NativePostFrontendContractFactsRunner.mtsFact(
                source, "modal controller");
    }

    @Test
    public void runnerBytecodeDoesNotReferenceProducerConclusionPath()
            throws Exception {
        for (String resource : Arrays.asList(
                "/ltsa/lts/NativePostFrontendContractFactsRunner.class",
                "/ltsa/lts/NativePostFrontendContractFactsRunner$1.class",
                "/ltsa/lts/NativePostFrontendContractFactsRunner$2.class",
                "/ltsa/lts/NativePostFrontendContractFactsRunner$3.class",
                "/ltsa/lts/NativeSourceDependencyFactsRunner.class",
                "/ltsa/lts/NativeSourceDependencyFactsRunner$1.class",
                "/ltsa/lts/NativeSourceDependencyFactsRunner$2.class",
                "/ltsa/lts/NativeUpdatingContractLoader.class")) {
            assertNoProducerConclusionReference(resource);
        }
    }

    private static void assertNoProducerConclusionReference(String resource)
            throws Exception {
        InputStream input = NativePostFrontendContractFactsRunner.class
                .getResourceAsStream(resource);
        Assert.assertNotNull("missing dependency class " + resource, input);
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        byte[] block = new byte[8192];
        int read;
        while ((read = input.read(block)) >= 0) {
            bytes.write(block, 0, read);
        }
        input.close();
        String constantPool = new String(
                bytes.toByteArray(), StandardCharsets.ISO_8859_1);
        for (String forbidden : Arrays.asList(
                "NativeTierAFactorizer", "NativeTierABundleExporter",
                "MtsaRevisedOtfDucsAdapter", "FineGrainedOtfDucs",
                "IndependentExplicitStrongSolver",
                "OtfDucsCertificateChecker")) {
            Assert.assertFalse(
                    resource + " must not reference " + forbidden,
                    constantPool.contains(forbidden));
        }
    }

    @Test
    public void conclusionFreeRootRejectsRootAndNestedSchemaDrift()
            throws Exception {
        Field field = NativePostFrontendContractFactsRunner.class
                .getDeclaredField("ROOT_KEYS");
        field.setAccessible(true);
        @SuppressWarnings("unchecked")
        Set<String> keys = (Set<String>) field.get(null);
        LinkedHashMap<String, Object> valid =
                new LinkedHashMap<String, Object>();
        for (String key : keys) valid.put(key, null);
        NativePostFrontendContractFactsRunner
                .validateConclusionFreeRoot(valid);

        LinkedHashMap<String, Object> extra =
                new LinkedHashMap<String, Object>(valid);
        extra.put("future_inherited_field", Boolean.TRUE);
        assertInvalidRoot(extra);

        LinkedHashMap<String, Object> nested =
                new LinkedHashMap<String, Object>();
        nested.put("proof", Boolean.TRUE);
        LinkedHashMap<String, Object> hidden =
                new LinkedHashMap<String, Object>(valid);
        hidden.put("flags", nested);
        assertInvalidRoot(hidden);
    }

    private static void assertInvalidRoot(Map<String, Object> value) {
        try {
            NativePostFrontendContractFactsRunner
                    .validateConclusionFreeRoot(value);
            Assert.fail("schema drift must be rejected");
        } catch (IllegalArgumentException expected) {
            Assert.assertNotNull(expected.getMessage());
        }
    }
}
