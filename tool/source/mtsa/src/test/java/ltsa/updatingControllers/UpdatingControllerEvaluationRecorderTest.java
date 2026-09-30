package ltsa.updatingControllers;

import static org.testng.Assert.assertEquals;
import static org.testng.Assert.assertFalse;
import static org.testng.Assert.assertTrue;

import org.testng.annotations.AfterMethod;
import org.testng.annotations.BeforeMethod;
import org.testng.annotations.Test;

import ltsa.lts.LTSOutput;
import ltsa.updatingControllers.UpdatingControllerEvaluationRecorder.ResultStatus;
import ltsa.updatingControllers.UpdatingControllerEvaluationRecorder.SolverStatus;
import ltsa.updatingControllers.UpdatingControllerEvaluationRecorder.VerificationStatus;

@Test(singleThreaded = true)
public class UpdatingControllerEvaluationRecorderTest {

    private static final String EVALUATION_ENABLED_PROPERTY = "mtsa.evaluation.enabled";
    private static final String DETAILED_REPORT_PROPERTY =
            "updating.controller.evaluation.printDetailedReport";

    private String previousEvaluationEnabled;
    private String previousDetailedReport;

    @BeforeMethod
    public void setUp() {
        previousEvaluationEnabled = System.getProperty(EVALUATION_ENABLED_PROPERTY);
        previousDetailedReport = System.getProperty(DETAILED_REPORT_PROPERTY);
        System.setProperty(EVALUATION_ENABLED_PROPERTY, "true");
        System.setProperty(DETAILED_REPORT_PROPERTY, "false");
        UpdatingControllerEvaluationRecorder.reset();
    }

    @AfterMethod
    public void tearDown() {
        UpdatingControllerEvaluationRecorder.reset();
        restoreProperty(EVALUATION_ENABLED_PROPERTY, previousEvaluationEnabled);
        restoreProperty(DETAILED_REPORT_PROPERTY, previousDetailedReport);
    }

    @Test
    public void storesSolverAndVerificationStatusesOrthogonally() {
        UpdatingControllerEvaluationRecorder.recordSolverOutcome(
                SolverStatus.UNREALIZABLE,
                VerificationStatus.VERIFIED);

        assertEquals(
                UpdatingControllerEvaluationRecorder.getSolverStatus(),
                SolverStatus.UNREALIZABLE);
        assertEquals(
                UpdatingControllerEvaluationRecorder.getVerificationStatus(),
                VerificationStatus.VERIFIED);
        assertEquals(
                UpdatingControllerEvaluationRecorder.getResultStatus(),
                ResultStatus.UNREALIZABLE);
        assertTrue(UpdatingControllerEvaluationRecorder.isRunVerified());

        UpdatingControllerEvaluationRecorder.recordVerificationOutcome(
                VerificationStatus.INVALID);

        assertEquals(
                UpdatingControllerEvaluationRecorder.getSolverStatus(),
                SolverStatus.UNREALIZABLE);
        assertEquals(
                UpdatingControllerEvaluationRecorder.getVerificationStatus(),
                VerificationStatus.INVALID);
        assertFalse(UpdatingControllerEvaluationRecorder.isRunVerified());

        UpdatingControllerEvaluationRecorder.recordSolverOutcome(
                SolverStatus.TIMEOUT,
                VerificationStatus.VERIFIED);
        assertEquals(
                UpdatingControllerEvaluationRecorder.getVerificationStatus(),
                VerificationStatus.VERIFIED);
        assertEquals(
                UpdatingControllerEvaluationRecorder.getResultStatus(),
                ResultStatus.UNKNOWN_FAILURE);
        assertFalse(UpdatingControllerEvaluationRecorder.isRunVerified());
    }

    @Test
    public void keepsLegacyRecordingCompatibleWithTheNewSolverAxis() {
        UpdatingControllerEvaluationRecorder.markSuccess();
        assertEquals(
                UpdatingControllerEvaluationRecorder.getSolverStatus(),
                SolverStatus.REALIZABLE);
        assertEquals(
                UpdatingControllerEvaluationRecorder.getVerificationStatus(),
                VerificationStatus.UNVERIFIED);
        assertEquals(
                UpdatingControllerEvaluationRecorder.getResultStatus(),
                ResultStatus.SUCCESS);

        UpdatingControllerEvaluationRecorder.reset();
        UpdatingControllerEvaluationRecorder.recordFailure(
                ResultStatus.OUT_OF_MEMORY,
                "heap cap");
        assertEquals(
                UpdatingControllerEvaluationRecorder.getSolverStatus(),
                SolverStatus.OOM);
        assertFalse(UpdatingControllerEvaluationRecorder.isRunVerified());
    }

    @Test
    public void printsCsvBeforeSummaryWithAllRunStatusColumns() {
        UpdatingControllerEvaluationRecorder.setMode("Traditional DUC");
        UpdatingControllerEvaluationRecorder.recordTime(
                "共通 / HPWindow",
                "合成ボタンを押してから合成完了までの時間",
                123L);
        UpdatingControllerEvaluationRecorder.markSuccess();

        RecordingOutput output = new RecordingOutput();
        UpdatingControllerEvaluationRecorder.printSummary(output);
        String content = output.toString();

        int csvStart = content.indexOf("================ EVALUATION DATA CSV ================");
        int summaryStart = content.indexOf("================ EVALUATION SUMMARY ================");
        assertTrue(csvStart >= 0, "CSV block was not printed");
        assertTrue(summaryStart > csvStart, "summary must be printed after the CSV block");

        String csvBlock = content.substring(csvStart, summaryStart);
        assertTrue(csvBlock.contains(
                "mode,result,solver_status,verification_status,run_verified,failure_reason"));
        assertTrue(csvBlock.contains("Traditional DUC,SUCCESS,realizable,unverified,false,"));
        assertTrue(csvBlock.contains(",solver_status,solver status,realizable,text,"));
        assertTrue(csvBlock.contains(",verification_status,verification status,unverified,text,"));
        assertTrue(csvBlock.contains(",run_verified,run verified,false,boolean,"));
        assertTrue(
                csvBlock.contains("合成の全体時間"),
                "summary-derived metrics must already be present in the CSV");
        String summaryBlock = content.substring(summaryStart);
        assertFalse(summaryBlock.contains(
                        "OTF-DUC new safety fluent 数（重複排除後）"),
                "Traditional summary must not request an OTF-only metric");
    }

    @Test
    public void revisedSummaryContainsOnlyRecordedRevisedMetrics() {
        UpdatingControllerEvaluationRecorder.setMode("Revised OTF-DUCS");
        UpdatingControllerEvaluationRecorder.recordSolverOutcome(
                SolverStatus.UNREALIZABLE,
                VerificationStatus.UNVERIFIED);
        UpdatingControllerEvaluationRecorder.recordValue(
                "入力規模",
                "Legacy-only metric",
                "must-not-appear-in-revised-summary");
        UpdatingControllerEvaluationRecorder.recordRevisedMetric(
                "revised_identity_input_id",
                "Revised OTF-DUCS / Identity",
                "Input ID",
                "case-01",
                "text");
        UpdatingControllerEvaluationRecorder.recordRevisedMetric(
                "revised_outcome_certificate_kind",
                "Revised OTF-DUCS / Outcome",
                "Certificate kind",
                "losing-region",
                "text");
        UpdatingControllerEvaluationRecorder.recordRevisedMetric(
                "revised_internal_certificate_check",
                "Revised OTF-DUCS / Correctness",
                "Internal certificate check",
                "PASSED",
                "text");
        UpdatingControllerEvaluationRecorder.recordRevisedMetric(
                "revised_workload_discovered_states",
                "Revised OTF-DUCS / Workload",
                "Discovered states",
                "17",
                "states");
        UpdatingControllerEvaluationRecorder.recordRevisedMetric(
                "revised_timing_solver_time",
                "Revised OTF-DUCS / Time / Memory",
                "Solver time",
                "31",
                "ms");
        UpdatingControllerEvaluationRecorder.recordRevisedMetric(
                "revised_memory_peak_rss",
                "Revised OTF-DUCS / Time / Memory",
                "Peak RSS",
                "4096",
                "B");
        UpdatingControllerEvaluationRecorder.recordRevisedMetric(
                "revised_completeness_record_valid",
                "Revised OTF-DUCS / Completeness",
                "Record valid",
                "true",
                "boolean");

        RecordingOutput output = new RecordingOutput();
        UpdatingControllerEvaluationRecorder.printSummary(output);
        String content = output.toString();
        int csvStart = content.indexOf("================ EVALUATION DATA CSV ================");
        int summaryStart = content.indexOf("================ EVALUATION SUMMARY ================");
        assertTrue(summaryStart > csvStart);

        String summary = content.substring(summaryStart);
        assertTrue(summary.contains("[Identity]"));
        assertTrue(summary.contains("[Outcome]"));
        assertTrue(summary.contains("[Correctness]"));
        assertTrue(summary.contains("[Workload]"));
        assertTrue(summary.contains("[Time / Memory]"));
        assertTrue(summary.contains("[Completeness]"));
        assertTrue(summary.contains("Result : UNREALIZABLE"));
        assertTrue(summary.contains("Solver status : unrealizable"));
        assertTrue(summary.contains("Verification status : unverified"));
        assertTrue(summary.contains("Run verified : false"));
        assertTrue(summary.contains("case-01"));
        assertTrue(summary.contains("PASSED"));
        assertFalse(summary.contains("Legacy-only metric"));
        assertFalse(summary.contains("OTF-DUC固有"));
        assertFalse(summary.contains("Old Controller 状態数"));
        assertFalse(summary.contains("未記録"));
    }

    private static void restoreProperty(String name, String value) {
        if (value == null) {
            System.clearProperty(name);
        } else {
            System.setProperty(name, value);
        }
    }

    private static final class RecordingOutput implements LTSOutput {
        private final StringBuilder content = new StringBuilder();

        @Override
        public void out(String value) {
            content.append(value);
        }

        @Override
        public void outln(String value) {
            content.append(value).append(System.lineSeparator());
        }

        @Override
        public void clearOutput() {
            content.setLength(0);
        }

        @Override
        public String toString() {
            return content.toString();
        }
    }
}
