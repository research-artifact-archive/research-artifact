package ltsa.updatingControllers.export;

import MTSTools.ac.ic.doc.mtstools.model.MTS;
import MTSTools.ac.ic.doc.mtstools.model.impl.MTSImpl;
import MTSTools.ac.ic.doc.commons.relations.BinaryRelation;
import org.testng.annotations.Test;

import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

public class M9MtsSnapshotTest {

    @Test
    public void retainsAnIncomingCanonicalErrorOutcome() {
        MTS<Long, String> source = new MTSImpl<Long, String>(Long.valueOf(0L));
        source.addState(Long.valueOf(-1L));
        source.addAction("fail");
        source.addRequired(Long.valueOf(0L), "fail", Long.valueOf(-1L));
        M9MtsSnapshot snapshot = M9MtsSnapshot.capture(source);
        assertTrue(snapshot.getStates().contains(Long.valueOf(-1L)));
        assertTrue(snapshot.getPost().get(Long.valueOf(0L))
                .get("fail").contains(Long.valueOf(-1L)));
    }

    @Test
    public void rejectsAnErrorStateWithOutgoingBehavior() {
        MTS<Long, String> source = new MTSImpl<Long, String>(Long.valueOf(0L));
        source.addState(Long.valueOf(-1L));
        source.addAction("fail");
        source.addAction("escape");
        source.addRequired(Long.valueOf(0L), "fail", Long.valueOf(-1L));
        source.addRequired(Long.valueOf(-1L), "escape", Long.valueOf(0L));
        try {
            M9MtsSnapshot.capture(source);
            fail("Expected nonterminal LTSA ERROR to fail");
        } catch (IllegalArgumentException expected) {
            assertTrue(expected.getMessage().contains("terminal unsafe sink"));
        }
    }

    @Test
    public void rejectsEveryRegisteredResourceCensusBeforeAllocation() {
        M9MtsSnapshot.requireResourceCensus(
                250_000L, 8_192L, 2_000_000L, 4_000_000L);
        expectResourceRejection(250_001L, 0L, 0L, 0L);
        expectResourceRejection(0L, 8_193L, 0L, 0L);
        expectResourceRejection(0L, 0L, 2_000_001L, 0L);
        expectResourceRejection(0L, 0L, 0L, 4_000_001L);
    }

	@Test
	public void rejectsAOneShotMutationBehindTheVerificationCursor() {
		MutatingMts source = new MutatingMts();
		try {
			M9MtsSnapshot.capture(source);
			fail("Expected a permanent behind-cursor row mutation to fail");
		} catch (IllegalArgumentException expected) {
			assertTrue(expected.getMessage(),
					expected.getMessage().contains("transitions changed"));
		}
	}

	@Test
	public void rejectsAnUnboundedActionIdentifier() {
		MTS<Long, String> source = new MTSImpl<Long, String>(Long.valueOf(0L));
		StringBuilder label = new StringBuilder();
		for (int index = 0; index < 257; index++) label.append('a');
		source.addAction(label.toString());
		try {
			M9MtsSnapshot.capture(source);
			fail("Expected an oversized action identifier to fail");
		} catch (IllegalArgumentException expected) {
			assertTrue(expected.getMessage(),
					expected.getMessage().contains("byte profile"));
		}
	}

    private static void expectResourceRejection(
            long states,
            long actions,
            long buckets,
            long outcomes) {
        try {
            M9MtsSnapshot.requireResourceCensus(
                    states, actions, buckets, outcomes);
            fail("Expected the finite MTS resource profile to reject the census");
        } catch (IllegalArgumentException expected) {
            assertTrue(expected.getMessage().contains("resource profile"));
        }
    }

	private static final class MutatingMts extends MTSImpl<Long, String> {
		private int stateOneRequiredReads;

		private MutatingMts() {
			super(Long.valueOf(0L));
			addState(Long.valueOf(1L));
			addAction("a");
			addRequired(Long.valueOf(0L), "a", Long.valueOf(1L));
			addRequired(Long.valueOf(1L), "a", Long.valueOf(0L));
		}

		@Override
		public BinaryRelation<String, Long> getTransitions(
				Long state,
				MTS.TransitionType type) {
			if (Long.valueOf(1L).equals(state)
					&& type == MTS.TransitionType.REQUIRED
					&& ++stateOneRequiredReads == 2) {
				removeRequired(Long.valueOf(0L), "a", Long.valueOf(1L));
				addRequired(Long.valueOf(0L), "a", Long.valueOf(0L));
			}
			return super.getTransitions(state, type);
		}
	}
}
