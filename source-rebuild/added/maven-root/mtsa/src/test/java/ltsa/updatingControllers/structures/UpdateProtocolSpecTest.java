package ltsa.updatingControllers.structures;

import MTSTools.ac.ic.doc.mtstools.model.operations.DCS.nonblocking.ProgressRegistry;
import ltsa.control.ControllerGoalDefinition;
import ltsa.lts.LTSException;
import ltsa.lts.Symbol;
import ltsa.updatingControllers.UpdateConstants;
import org.testng.annotations.Test;

import java.util.List;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

public class UpdateProtocolSpecTest {

    @Test
    public void generatesStopAndStartActionsFromSafetyNames() {
        ControllerGoalDefinition oldGoal = goalWithSafeties("OLD", "P_OLD_A", "P_SHARED");
        ControllerGoalDefinition newGoal = goalWithSafeties("NEW", "P_NEW_B", "P_SHARED");

        UpdateProtocolSpec spec = UpdateProtocolSpec.forFineGrained(oldGoal, newGoal);
        spec.registerReconfigure(0, "reconfigure_MAP_A");

        assertTrue(spec.isStopOldSpecAction("stopOldSpec_P_OLD_A"));
        assertTrue(spec.isStopOldSpecAction("stopOldSpec_P_SHARED"));
        assertTrue(spec.isStartNewSpecAction("startNewSpec_P_NEW_B"));
        assertTrue(spec.isStartNewSpecAction("startNewSpec_P_SHARED"));
        assertTrue(spec.isReconfigureAction("reconfigure_MAP_A"));
        assertEquals(5, spec.progressActionCount());
        assertTrue(spec.getAllUpdateActions().contains(UpdateConstants.BEGIN_UPDATE));
        assertTrue(spec.getAllUpdateActions().contains(UpdateConstants.FINISH_UPDATE));
    }

    @Test
    public void progressRegistrySupportsMoreThanSixtyThreeActions() {
        ControllerGoalDefinition oldGoal = new ControllerGoalDefinition("OLD");
        for (int i = 0; i < 70; i++) {
            oldGoal.addSafetyDefinition(new Symbol(Symbol.UPPERIDENT, "P_" + i));
        }

        UpdateProtocolSpec spec = UpdateProtocolSpec.forFineGrained(oldGoal, new ControllerGoalDefinition("NEW"));
        ProgressRegistry registry = new ProgressRegistry(spec);
        long state = ProgressRegistry.UPDATE_EMPTY;

        List<String> actions = spec.getProgressActionsInIndexOrder();
        assertEquals(70, actions.size());
        for (String action : actions) {
            assertFalse(registry.isCompleted(state, action));
            state = registry.nextFor(state, action);
            assertTrue(registry.isCompleted(state, action));
        }

        assertTrue(registry.isAllDone(state));
        assertFalse(registry.isAllDone(ProgressRegistry.GOAL));
        for (String action : actions) {
            assertTrue(registry.isCompleted(ProgressRegistry.GOAL, action));
        }
    }

    @Test
    public void validatesAndExposesStrictUpdatePrecedence() {
        ControllerGoalDefinition oldGoal = goalWithSafeties("OLD", "P_OLD");
        ControllerGoalDefinition newGoal = goalWithSafeties("NEW", "P_NEW");
        UpdateProtocolSpec spec = UpdateProtocolSpec.forFineGrained(
                oldGoal, newGoal);
        spec.registerReconfigure(0, "reconfigure_ENV");
        spec.addPrecedence("stopOldSpec_P_OLD", "reconfigure_ENV");
        spec.addPrecedence("reconfigure_ENV", "startNewSpec_P_NEW");

        spec.validatePrecedence();

        assertEquals(2, spec.getPrecedenceEdges().size());
        assertTrue(spec.getPrecedenceEdges().contains(
                new UpdateProtocolSpec.PrecedenceEdge(
                        "stopOldSpec_P_OLD", "reconfigure_ENV")));
        assertTrue(spec.getPrecedenceEdges().contains(
                new UpdateProtocolSpec.PrecedenceEdge(
                        "reconfigure_ENV", "startNewSpec_P_NEW")));
    }

    @Test
    public void rejectsUnknownActionsAndCyclesInUpdatePrecedence() {
        ControllerGoalDefinition oldGoal = goalWithSafeties("OLD", "P_OLD");
        UpdateProtocolSpec unknown = UpdateProtocolSpec.forFineGrained(
                oldGoal, new ControllerGoalDefinition("NEW"));
        unknown.addPrecedence("stopOldSpec_P_OLD", "reconfigure_MISSING");
        try {
            unknown.validatePrecedence();
            throw new AssertionError("Expected unknown precedence action to fail");
        } catch (LTSException expected) {
            assertTrue(expected.getMessage().contains("unknown update action"));
        }

        ControllerGoalDefinition newGoal = goalWithSafeties("NEW", "P_NEW");
        UpdateProtocolSpec cyclic = UpdateProtocolSpec.forFineGrained(
                oldGoal, newGoal);
        cyclic.addPrecedence("stopOldSpec_P_OLD", "startNewSpec_P_NEW");
        cyclic.addPrecedence("startNewSpec_P_NEW", "stopOldSpec_P_OLD");
        try {
            cyclic.validatePrecedence();
            throw new AssertionError("Expected precedence cycle to fail");
        } catch (LTSException expected) {
            assertTrue(expected.getMessage().contains("contains a cycle"));
        }
    }

    private ControllerGoalDefinition goalWithSafeties(String name, String... safeties) {
        ControllerGoalDefinition goal = new ControllerGoalDefinition(name);
        for (String safety : safeties) {
            goal.addSafetyDefinition(new Symbol(Symbol.UPPERIDENT, safety));
        }
        return goal;
    }
}
