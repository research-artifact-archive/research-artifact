package ltsa.updatingControllers.export;

import org.testng.annotations.Test;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

import static org.junit.Assert.assertTrue;

@Test(singleThreaded = true)
public class M9EndpointSynthesisHookProcessTest {
	@Test public void productionLedgerRejectsTheRawTestCaptureApi() throws Exception {
		assertProbe("raw-production-rejected");
	}

	@Test public void crossThreadEntryInvalidatesProductionAttempt() throws Exception {
		assertProbe("cross-thread-entry");
	}

	@Test public void preArmEntryPermanentlyConsumesFreshProcess() throws Exception {
		assertProbe("pre-arm-entry");
	}

	@Test public void failedAttemptCannotRetry() throws Exception {
		assertProbe("failure-consumes");
	}

	@Test public void parallelFirstArmHasExactlyOneWinner() throws Exception {
		assertProbe("parallel-arm");
	}

	private static void assertProbe(String scenario) throws Exception {
		String output = runProbe(scenario);
		assertTrue(output, output.contains(
				"M9_ENDPOINT_HOOK_PROBE_PASS=" + scenario));
	}

	private static String runProbe(String scenario) throws Exception {
		String java = new File(System.getProperty("java.home"), "bin/java")
				.getAbsolutePath();
		String classpath = System.getProperty("surefire.test.class.path");
		if (classpath == null || classpath.isEmpty()) {
			classpath = System.getProperty("java.class.path");
		}
		List<String> command = new ArrayList<String>();
		command.add(java);
		command.add("-cp");
		command.add(classpath);
		command.add(M9EndpointSynthesisHookProcessProbe.class.getName());
		command.add(scenario);
		Process process = new ProcessBuilder(command)
				.redirectErrorStream(true).start();
		ByteArrayOutputStream output = new ByteArrayOutputStream();
		InputStream input = process.getInputStream();
		byte[] buffer = new byte[8192];
		for (int count; (count = input.read(buffer)) != -1;) {
			output.write(buffer, 0, count);
		}
		int exit = process.waitFor();
		String text = new String(output.toByteArray(), StandardCharsets.UTF_8);
		if (exit != 0) throw new AssertionError(
				"Probe " + scenario + " exited " + exit + ":\n" + text);
		return text;
	}
}
