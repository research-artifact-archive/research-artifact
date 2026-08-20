package ltsa.updatingControllers.cli;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;

import ltsa.lts.CompactState;
import ltsa.updatingControllers.UpdatingControllerEvaluationRecorder;
import ltsa.updatingControllers.UpdatingControllerEvaluationRecorder.SolverStatus;
import ltsa.updatingControllers.UpdatingControllerEvaluationRecorder.VerificationStatus;
import org.testng.annotations.AfterMethod;
import org.testng.annotations.Test;

import static org.junit.Assert.assertEquals;

public class SingleCompositionRunnerOutcomeTest {

    @AfterMethod
    public void cleanUp() {
        System.clearProperty("mtsa.revised.otf.independentVerification");
        UpdatingControllerEvaluationRecorder.reset();
    }

    @Test
    public void invalidCertificateTakesPrecedenceOverLosingDecision() {
        UpdatingControllerEvaluationRecorder.reset();
        UpdatingControllerEvaluationRecorder.recordSolverOutcome(
                SolverStatus.UNREALIZABLE, VerificationStatus.INVALID);

        assertEquals(
                SingleCompositionRunner.EXIT_INVALID_CERTIFICATE,
                SingleCompositionRunner.recordedOutcomeExitCode());
    }

    @Test
    public void invalidInputHasItsOwnExitCode() {
        UpdatingControllerEvaluationRecorder.reset();
        UpdatingControllerEvaluationRecorder.recordSolverOutcome(
                SolverStatus.INVALID_INPUT, VerificationStatus.UNVERIFIED);

        assertEquals(
                SingleCompositionRunner.EXIT_INVALID_INPUT,
                SingleCompositionRunner.recordedOutcomeExitCode());
    }

    @Test
    public void requestedButIncompleteVerificationIsNotSuccess() {
        UpdatingControllerEvaluationRecorder.reset();
        System.setProperty(
                "mtsa.revised.otf.independentVerification", "true");
        UpdatingControllerEvaluationRecorder.recordSolverOutcome(
                SolverStatus.REALIZABLE, VerificationStatus.UNVERIFIED);

        assertEquals(
                SingleCompositionRunner.EXIT_VERIFICATION_INCONCLUSIVE,
                SingleCompositionRunner.recordedOutcomeExitCode());
    }

    @Test
    public void summaryTransitionOutputDoesNotRenderTheFullFsp() throws Exception {
        CompactState controller = new CompactState("SUMMARY_TEST");
        controller.maxStates = 1;
        controller.states = new ltsa.lts.EventState[] {null};
        controller.alphabet = new String[] {"tau"};
        File artifact = File.createTempFile("mtsa-controller-summary", ".txt");
        try {
            SingleCompositionRunner.writeTransitions(
                    controller,
                    artifact,
                    SingleCompositionRunner.TRANSITION_OUTPUT_SUMMARY);
            String content = new String(
                    Files.readAllBytes(artifact.toPath()), StandardCharsets.UTF_8);
            org.junit.Assert.assertTrue(
                    content.contains("mtsa-controller-summary-v1"));
            org.junit.Assert.assertTrue(content.contains("SUMMARY_TEST"));
            org.junit.Assert.assertTrue(content.contains("States:\n\t1"));
            org.junit.Assert.assertTrue(content.contains("Transitions:\n\t0"));
            org.junit.Assert.assertFalse(content.contains("SUMMARY_TEST = Q0"));
        } finally {
            Files.deleteIfExists(artifact.toPath());
        }
    }
}
