package ltsa.lts;

import org.testng.annotations.Test;

import static org.testng.Assert.assertEquals;
import static org.testng.Assert.assertNull;

/** Regression test for ERROR labels during reachable-state renumbering. */
public class CompactStateReachableStateLabelTest {

    @Test
    public void reachableIgnoresNegativePseudoStateLabels() {
        CompactState machine = new CompactState();
        machine.name = "ERROR_LABEL_REGRESSION";
        machine.maxStates = 2;
        machine.alphabet = new String[]{"tau", "go", "fail"};
        machine.states = new EventState[2];
        machine.states[0] = new EventState(1, 1);
        machine.states[0] = EventStateUtils.add(
                machine.states[0],
                new EventState(2, Declaration.ERROR));
        machine.states[1] = new EventState(1, 1);
        machine.addStateLabel("START", 0);
        machine.addStateLabel("LIVE", 1);
        machine.addStateLabel("ERROR", Declaration.ERROR);

        machine.reachable();

        assertEquals(machine.getStateId("START"), Integer.valueOf(0));
        assertEquals(machine.getStateId("LIVE"), Integer.valueOf(1));
        assertNull(machine.getStateId("ERROR"));
        assertEquals(
                machine.states[0].getNext(2),
                Declaration.ERROR,
                "reachable() must preserve transitions to the ERROR pseudo-state");
    }
}
