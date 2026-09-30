package ltsa.updatingControllers.export;

import ltsa.lts.CompactState;
import ltsa.lts.Declaration;
import ltsa.lts.EventState;
import ltsa.lts.EventStateUtils;
import ltsa.lts.ProbabilisticEventState;
import org.testng.annotations.Test;

import java.util.AbstractMap;
import java.util.HashMap;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

public class CompactStateCanonicalSnapshotTest {

    @Test
    public void retainsRawTauErrorDeadlockUnusedActionAndNondeterminism() {
        CompactState machine = primitive();
        CompactStateCanonicalSnapshot snapshot =
                CompactStateCanonicalSnapshot.fromRaw(machine);
        assertEquals(Integer.valueOf(3),
                Integer.valueOf(snapshot.getActions().size()));
        assertEquals(Integer.valueOf(4),
                Integer.valueOf(snapshot.getTransitions().size()));
		assertTrue(snapshot.getEmptyTransitionStates().contains(Integer.valueOf(1)));
        assertEquals(Integer.valueOf(2), Integer.valueOf(snapshot.getEndState()));
        boolean sawError = false;
        boolean sawTau = false;
        for (CompactStateCanonicalSnapshot.Transition transition
                : snapshot.getTransitions()) {
            sawError |= transition.getTargetState() == Declaration.ERROR;
            sawTau |= "tau".equals(transition.getActionLabel());
        }
        assertTrue(sawError);
        assertTrue(sawTau);
    }

    @Test
    public void requiresExactCompositionAndErrorTupleCensuses() {
        CompactState composed = composed();
        CompactStateCanonicalSnapshot snapshot =
                CompactStateCanonicalSnapshot.fromRaw(composed, true);
        assertEquals(Integer.valueOf(3),
                Integer.valueOf(snapshot.getComponentStateTuples().size()));
        assertEquals(Integer.valueOf(3),
				Integer.valueOf(snapshot.getNativeFirstOutcomeDiagnostics().size()));

        CompactState missing = composed();
        missing.statePlusActionToComponentStates.clear();
        expectIllegal(new Runnable() {
            @Override
            public void run() {
                CompactStateCanonicalSnapshot.fromRaw(missing, true);
            }
		}, "transition tuple census");

        CompactState extra = composed();
        extra.statePlusActionToComponentStates.put(
				new AbstractMap.SimpleEntry<Integer, String>(1, "a"),
				new int[]{1, 1});
        expectIllegal(new Runnable() {
            @Override
            public void run() {
                CompactStateCanonicalSnapshot.fromRaw(extra, true);
            }
		}, "no native transition bucket");

        expectIllegal(new Runnable() {
            @Override
            public void run() {
                CompactStateCanonicalSnapshot.fromRaw(primitive(), true);
            }
        }, "required");
    }

    @Test
    public void rejectsBadTauModalProbabilityAndTupleDomains() {
        CompactState badTau = primitive();
        badTau.alphabet = new String[]{"a", "tau", "unused"};
        expectIllegal(new Runnable() {
            @Override
            public void run() {
                CompactStateCanonicalSnapshot.fromRaw(badTau);
            }
        }, "index zero");

        CompactState modal = primitive();
        modal.alphabet[1] = "a?";
        expectIllegal(new Runnable() {
            @Override
            public void run() {
                CompactStateCanonicalSnapshot.fromRaw(modal);
            }
        }, "Modal");

        CompactState probabilistic = primitive();
        probabilistic.states[1] = new ProbabilisticEventState(1, 1);
        expectIllegal(new Runnable() {
            @Override
            public void run() {
                CompactStateCanonicalSnapshot.fromRaw(probabilistic);
            }
		}, "subclass");

		CompactState exotic = primitive();
		exotic.states[1] = new ExoticEventState(1, 1);
		expectIllegal(new Runnable() {
			@Override
			public void run() {
				CompactStateCanonicalSnapshot.fromRaw(exotic);
			}
		}, "subclass");

        CompactState badTuple = composed();
        badTuple.stateToComponentStates.put(Integer.valueOf(1),
                new int[]{1, 99});
        expectIllegal(new Runnable() {
            @Override
            public void run() {
                CompactStateCanonicalSnapshot.fromRaw(badTuple, true);
            }
        }, "local state domain");

		CompactState cyclic = primitive();
		cyclic.states[0] = new EventState(1, 0);
		cyclic.states[0].setList(cyclic.states[0]);
		expectIllegal(new Runnable() {
			@Override
			public void run() {
				CompactStateCanonicalSnapshot.fromRaw(cyclic);
			}
		}, "identity cycle");

		CompactState hidden = primitive();
		EventState sameAction = new EventState(1, 2);
		hidden.states[0] = EventStateUtils.add(
				new EventState(1, 1), sameAction);
		java.util.Enumeration visible = hidden.states[0].elements();
		visible.nextElement();
		EventState nondeterministic = (EventState) visible.nextElement();
		nondeterministic.setList(new ProbabilisticEventState(2, 2));
		expectIllegal(new Runnable() {
			@Override
			public void run() {
				CompactStateCanonicalSnapshot.fromRaw(hidden);
			}
		}, "hides a list branch");
    }

    private static CompactState primitive() {
        CompactState machine = new CompactState();
        machine.name = "raw";
        machine.maxStates = 3;
        machine.alphabet = new String[]{"tau", "a", "unused"};
        machine.states = new EventState[3];
        machine.states[0] = new EventState(1, 1);
        machine.states[0] = EventStateUtils.add(
                machine.states[0], new EventState(1, Declaration.ERROR));
        machine.states[0] = EventStateUtils.add(
                machine.states[0], new EventState(0, 2));
        machine.states[2] = new EventState(1, 2);
        machine.endseq = 2;
        return machine;
    }

    private static CompactState composed() {
        CompactState machine = primitive();
		machine.states[0] = EventState.remove(
				machine.states[0], new EventState(1, 1));
        machine.name = "product";
        machine.components = new CompactState[]{component("left"), component("right")};
        machine.stateToComponentStates = new HashMap<Integer, int[]>();
        machine.stateToComponentStates.put(Integer.valueOf(0), new int[]{0, 0});
        machine.stateToComponentStates.put(Integer.valueOf(1), new int[]{1, 1});
        machine.stateToComponentStates.put(Integer.valueOf(2), new int[]{2, 2});
        machine.statePlusActionToComponentStates =
                new HashMap<AbstractMap.SimpleEntry<Integer, String>, int[]>();
        machine.statePlusActionToComponentStates.put(
                new AbstractMap.SimpleEntry<Integer, String>(0, "a"),
                new int[]{Declaration.ERROR, 1});
		machine.statePlusActionToComponentStates.put(
				new AbstractMap.SimpleEntry<Integer, String>(0, "tau"),
				new int[]{2, 2});
		machine.statePlusActionToComponentStates.put(
				new AbstractMap.SimpleEntry<Integer, String>(2, "a"),
				new int[]{2, 2});
        return machine;
    }

	private static CompactState component(String name) {
        CompactState component = primitive();
        component.name = name;
        return component;
	}

	private static final class ExoticEventState extends EventState {
		private ExoticEventState(int event, int target) {
			super(event, target);
		}
	}

    private static void expectIllegal(Runnable operation, String fragment) {
        try {
            operation.run();
            fail("Expected IllegalArgumentException containing " + fragment);
        } catch (IllegalArgumentException expected) {
            assertTrue(expected.getMessage(),
                    expected.getMessage().contains(fragment));
        }
    }
}
