package ltsa.updatingControllers.export;

import org.testng.annotations.Test;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

@Test(singleThreaded = true)
public class TraditionalPreGrSnapshotHookProcessTest {
	@Test
	public void productionCaptureSealsAndWritesOnlyCapturedHeartbeat() throws Exception {
		Path heartbeat = Files.createTempFile("m9-heartbeat-", ".log");
		try {
			String output = runProbe("capture-seal", heartbeat);
			assertTrue(output, output.contains("M9_PROCESS_PROBE_PASS=capture-seal"));
			String log = new String(Files.readAllBytes(heartbeat),
					StandardCharsets.UTF_8);
			assertTrue(log, log.contains("finish status=snapshot-captured"));
			assertFalse(log, log.contains("failed:SnapshotComplete"));
			assertFalse(log, log.contains("finish status=snapshot-complete"));
		} finally {
			Files.deleteIfExists(heartbeat);
		}
	}

	@Test
	public void crossThreadGrInvalidatesTheProductionCapture() throws Exception {
		String output = runProbe("cross-thread-gr", null);
		assertTrue(output, output.contains("M9_PROCESS_PROBE_PASS=cross-thread-gr"));
	}

	@Test
	public void doubleCaptureConsumesTheProductionAttempt() throws Exception {
		String output = runProbe("double-capture", null);
		assertTrue(output, output.contains("M9_PROCESS_PROBE_PASS=double-capture"));
	}

	@Test
	public void nativeGrBeforeArmPermanentlyRejectsTheProductionAttempt()
			throws Exception {
		String output = runProbe("pre-arm-gr", null);
		assertTrue(output, output.contains("M9_PROCESS_PROBE_PASS=pre-arm-gr"));
	}

	private static String runProbe(String scenario, Path heartbeat) throws Exception {
		String java = new File(System.getProperty("java.home"), "bin/java")
				.getAbsolutePath();
		String classpath = System.getProperty("surefire.test.class.path");
		if (classpath == null || classpath.isEmpty()) {
			classpath = System.getProperty("java.class.path");
		}
		List<String> command = new ArrayList<String>();
		command.add(java);
		if (heartbeat != null) {
			command.add("-Dduc.heartbeat=true");
			command.add("-Dduc.heartbeat.file=" + heartbeat.toAbsolutePath());
			command.add("-Dduc.heartbeat.intervalSec=1");
		}
		command.add("-cp");
		command.add(classpath);
		command.add(TraditionalPreGrSnapshotHookProcessProbe.class.getName());
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
