package ltsa.updatingControllers.export;

import org.testng.annotations.Test;

import java.io.ByteArrayOutputStream;
import java.lang.reflect.Constructor;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

public class M9EndpointReceiptCoreTest {
    private static final long DECODED_ITEM_LIMIT = 32L * 1024L * 1024L;

    @Test
    public void byteValidBodyCountAboveOldTightLimitIsAccepted()
            throws Exception {
        Object writer = newWriter();
        Method count = writer.getClass().getDeclaredMethod("count", long.class);
        count.setAccessible(true);
        count.invoke(writer, 250001L);
    }

    @Test
    public void canonicalWriterRejectsBodyCountBeyondIndependentBudget()
            throws Exception {
        Object writer = newWriter();
        Method count = writer.getClass().getDeclaredMethod("count", long.class);
        count.setAccessible(true);
        count.invoke(writer, DECODED_ITEM_LIMIT);
        try {
            count.invoke(writer, 1L);
            fail("Decoded section body exceeded the registered item budget.");
        } catch (InvocationTargetException expected) {
            assertTrue(expected.getCause() instanceof IllegalArgumentException);
            assertTrue(expected.getCause().getMessage().contains(
                    "decoded-item profile"));
        }
    }

    @Test
    public void serializedCensusDoesNotSpendBodyItemBudget() throws Exception {
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        Object writer = newWriter(bytes);
        Method census = writer.getClass().getDeclaredMethod("census", long.class);
        Method count = writer.getClass().getDeclaredMethod("count", long.class);
        census.setAccessible(true);
        count.setAccessible(true);
        census.invoke(writer, 4000000L);
        count.invoke(writer, DECODED_ITEM_LIMIT);
        assertEquals(16, bytes.size());
    }

    private static Object newWriter() throws Exception {
        return newWriter(new ByteArrayOutputStream());
    }

    private static Object newWriter(ByteArrayOutputStream bytes) throws Exception {
        Class<?> type = Class.forName(
                "ltsa.updatingControllers.export.M9EndpointReceiptCore$CanonicalWriter");
        Constructor<?> constructor = type.getDeclaredConstructor(
                java.io.OutputStream.class);
        constructor.setAccessible(true);
        return constructor.newInstance(bytes);
    }
}
