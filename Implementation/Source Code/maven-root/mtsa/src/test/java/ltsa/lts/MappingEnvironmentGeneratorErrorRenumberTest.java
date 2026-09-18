package ltsa.lts;

import org.testng.annotations.Test;

import java.util.Arrays;

import static org.testng.Assert.assertTrue;

/** Regression tests for ERROR targets in mapping-environment reachability. */
public class MappingEnvironmentGeneratorErrorRenumberTest {

    @Test
    public void safeRenumberPreservesDeterministicAndNondeterministicErrorTargets() {
        EventState transitions = null;
        transitions = EventStateUtils.add(
                transitions,
                new EventState(1, Declaration.ERROR));
        transitions = EventStateUtils.add(transitions, new EventState(2, 0));
        transitions = EventStateUtils.add(transitions, new EventState(3, 0));
        transitions = EventStateUtils.add(
                transitions,
                new EventState(3, Declaration.ERROR));

        MyIntHash oldToNew = new MyIntHash(1);
        oldToNew.put(0, 0);
        EventState renumbered = new MappingEnvironmentGenerator()
                .safeRenumberStates(transitions, oldToNew);

        int[] errorOnly = EventState.nextState(renumbered, 1);
        assertTrue(errorOnly.length == 1 && errorOnly[0] == Declaration.ERROR);
        int[] stateOnly = EventState.nextState(renumbered, 2);
        assertTrue(stateOnly.length == 1 && stateOnly[0] == 0);
        int[] nondeterministic = EventState.nextState(renumbered, 3);
        Arrays.sort(nondeterministic);
        assertTrue(nondeterministic.length == 2);
        assertTrue(Arrays.binarySearch(nondeterministic, Declaration.ERROR) >= 0);
        assertTrue(Arrays.binarySearch(nondeterministic, 0) >= 0);
    }
}
