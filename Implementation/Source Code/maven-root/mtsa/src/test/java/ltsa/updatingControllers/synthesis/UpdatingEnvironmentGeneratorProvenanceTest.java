package ltsa.updatingControllers.synthesis;

import MTSTools.ac.ic.doc.mtstools.model.MTS;
import MTSTools.ac.ic.doc.mtstools.model.impl.MTSImpl;
import MTSTools.ac.ic.doc.mtstools.model.impl.UpdatingEnvironment;
import MTSTools.ac.ic.doc.commons.relations.Pair;
import ltsa.updatingControllers.UpdateConstants;
import org.testng.annotations.Test;

import java.util.Arrays;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Set;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

public class UpdatingEnvironmentGeneratorProvenanceTest {

    @Test
    public void exposesTypedImmutableSourceStateProvenance() {
        MTS<Long, String> oldController = oldController();
        MTS<Long, String> mapping = mapping();
        UpdatingEnvironmentGenerator generator =
                new UpdatingEnvironmentGenerator(oldController, mapping, true);

        generator.generateEnvironment();
        UpdatingEnvironmentGenerator.Provenance provenance =
                generator.getProvenance();

        assertEquals(new java.util.LinkedHashSet<Long>(
                        Arrays.asList(Long.valueOf(0L), Long.valueOf(1L))),
                provenance.getOldControllerStates());
        assertEquals(Integer.valueOf(2), Integer.valueOf(
                provenance.getMappingStateToUpdatingState().size()));
        for (Map.Entry<Long, Long> entry
                : provenance.getMappingStateToUpdatingState().entrySet()) {
            assertEquals(entry.getKey(),
                    provenance.getUpdatingStateToMappingState().get(
                            entry.getValue()));
            assertFalse(provenance.getOldControllerStates().contains(
                    entry.getValue()));
        }

        assertEquals(Collections.singleton(Long.valueOf(0L)),
                provenance.getBeginUpdateSourcesByMappingState().get(
                        Long.valueOf(10L)));
        assertEquals(Collections.singleton(Long.valueOf(1L)),
                provenance.getBeginUpdateSourcesByMappingState().get(
                        Long.valueOf(11L)));
        assertEquals(Integer.valueOf(2), Integer.valueOf(
                provenance.getBeginUpdateRows().size()));

        for (Long oldState : provenance.getOldControllerStates()) {
            assertFalse(generator.getUpdEnv().getTransitionsFrom(oldState)
                    .getImage(UpdateConstants.BEGIN_UPDATE).isEmpty());
        }

        expectUnsupported(new Runnable() {
            @Override
            public void run() {
                provenance.getMappingStateToUpdatingState().put(
                        Long.valueOf(99L), Long.valueOf(99L));
            }
        });
        expectUnsupported(new Runnable() {
            @Override
            public void run() {
                Set<Long> sources = provenance
                        .getBeginUpdateSourcesByMappingState()
                        .get(Long.valueOf(10L));
                sources.add(Long.valueOf(99L));
            }
        });
    }

    @Test
    public void rejectsASecondGenerationAttempt() {
        UpdatingEnvironmentGenerator generator =
                new UpdatingEnvironmentGenerator(oldController(), mapping(), true);
        generator.generateEnvironment();
        try {
            generator.generateEnvironment();
            fail("Expected the one-shot generator to reject a second attempt");
        } catch (IllegalStateException expected) {
            assertTrue(expected.getMessage().contains("one-shot"));
        }
    }

    @Test
    public void deepCopiesInputsAndProducesRepeatableOutput() {
        MTS<Long, String> old = oldController();
        MTS<Long, String> map = mapping();
        String oldBefore = mtsRows(old);
        String mapBefore = mtsRows(map);

        UpdatingEnvironmentGenerator first =
                new UpdatingEnvironmentGenerator(old, map, true);
        first.generateEnvironment();
        UpdatingEnvironmentGenerator second =
                new UpdatingEnvironmentGenerator(old, map, true);
        second.generateEnvironment();

        assertEquals(oldBefore, mtsRows(old));
        assertEquals(mapBefore, mtsRows(map));
        assertFalse(old.getActions().contains(UpdateConstants.BEGIN_UPDATE));
        assertFalse(map.getActions().contains(UpdateConstants.BEGIN_UPDATE));
        assertEquals(environmentRows(first.getUpdEnv()),
                environmentRows(second.getUpdEnv()));
    }

    @Test
    public void updatingEnvironmentDoesNotAliasRequiredRelations() {
        MTS<Long, String> old = oldController();
        UpdatingEnvironment copied = new UpdatingEnvironment(old);
        copied.addAction("local");
        copied.addTransition(Long.valueOf(0L), "local", Long.valueOf(0L));
        assertFalse(old.getActions().contains("local"));
        assertTrue(old.getTransitions(Long.valueOf(0L),
                MTS.TransitionType.REQUIRED).getImage("local").isEmpty());
    }

    @Test
    public void rejectsMaybeErrorAndReservedInputSemantics() {
        MTS<Long, String> maybe = oldController();
        maybe.addAction("optional");
        maybe.addPossible(Long.valueOf(0L), "optional", Long.valueOf(1L));
        expectIllegal(new Runnable() {
            @Override
            public void run() {
                new UpdatingEnvironmentGenerator(maybe, mapping(), true);
            }
        }, "MAYBE");

        MTS<Long, String> error = oldController();
        error.addState(Long.valueOf(-1L));
        error.addRequired(Long.valueOf(0L), "a", Long.valueOf(-1L));
        expectIllegal(new Runnable() {
            @Override
            public void run() {
                new UpdatingEnvironmentGenerator(error, mapping(), true);
            }
        }, "ERROR");

        MTS<Long, String> reserved = mapping();
        reserved.addAction(UpdateConstants.BEGIN_UPDATE);
        reserved.addRequired(Long.valueOf(10L), UpdateConstants.BEGIN_UPDATE,
                Long.valueOf(11L));
        expectIllegal(new Runnable() {
            @Override
            public void run() {
                new UpdatingEnvironmentGenerator(oldController(), reserved, true);
            }
        }, "reserved");
    }

    @Test
    public void rejectsAnOldStateWithoutARequestImage() {
        MTS<Long, String> old = new MTSImpl<Long, String>(Long.valueOf(0L));
        old.addState(Long.valueOf(1L));
        old.addAction("b");
        old.addRequired(Long.valueOf(0L), "b", Long.valueOf(1L));
        MTS<Long, String> map = new MTSImpl<Long, String>(Long.valueOf(10L));
        map.addState(Long.valueOf(11L));
        map.addAction("a");
		map.addAction(UpdateConstants.RECONFIGURE);
        map.addRequired(Long.valueOf(10L), "a", Long.valueOf(11L));
		map.addRequired(Long.valueOf(10L), UpdateConstants.RECONFIGURE,
				Long.valueOf(10L));
        UpdatingEnvironmentGenerator generator =
                new UpdatingEnvironmentGenerator(old, map, true);
        expectIllegal(new Runnable() {
            @Override
            public void run() {
                generator.generateEnvironment();
            }
        }, "not total");
    }

    @Test
    public void preservesTheNativeMappingReconfigureAction() {
        MTS<Long, String> map = new MTSImpl<Long, String>(Long.valueOf(10L));
        map.addState(Long.valueOf(11L));
        map.addAction("a");
        map.addAction(UpdateConstants.RECONFIGURE);
        map.addRequired(Long.valueOf(10L), "a", Long.valueOf(11L));
        map.addRequired(Long.valueOf(11L), "a", Long.valueOf(10L));
        map.addRequired(Long.valueOf(10L), UpdateConstants.RECONFIGURE,
                Long.valueOf(11L));

        UpdatingEnvironmentGenerator generator =
                new UpdatingEnvironmentGenerator(oldController(), map, true);
        generator.generateEnvironment();
        assertTrue(generator.getUpdEnv().getActions().contains(
                UpdateConstants.RECONFIGURE));
        assertEquals(Integer.valueOf(1), Integer.valueOf(
                generator.getUpdEnv().getTransitionsFrom(
                        generator.getProvenance()
                                .getMappingStateToUpdatingState()
                                .get(Long.valueOf(10L)))
                        .getImage(UpdateConstants.RECONFIGURE).size()));
    }

	@Test
	public void normalizesDeclaredUnusedTauButRejectsTauBehavior() {
		MTS<Long, String> unused = oldController();
		unused.addAction("tau");
		UpdatingEnvironmentGenerator accepted =
				new UpdatingEnvironmentGenerator(unused, mapping(), true);
		accepted.generateEnvironment();
		assertFalse(accepted.getUpdEnv().getActions().contains("tau"));

		MTS<Long, String> used = oldController();
		used.addAction("tau");
		used.addRequired(Long.valueOf(0L), "tau", Long.valueOf(1L));
		expectIllegal(new Runnable() {
			@Override
			public void run() {
				new UpdatingEnvironmentGenerator(used, mapping(), true);
			}
		}, "tau transition");
	}

	@Test
	public void rejectsReconfigureOnlyInADisconnectedMappingRegion() {
		MTS<Long, String> old = new MTSImpl<Long, String>(Long.valueOf(0L));
		MTS<Long, String> map = new MTSImpl<Long, String>(Long.valueOf(10L));
		map.addState(Long.valueOf(11L));
		map.addAction(UpdateConstants.RECONFIGURE);
		map.addRequired(Long.valueOf(11L), UpdateConstants.RECONFIGURE,
				Long.valueOf(11L));
		UpdatingEnvironmentGenerator generator =
				new UpdatingEnvironmentGenerator(old, map, true);
		expectIllegal(new Runnable() {
			@Override
			public void run() {
				generator.generateEnvironment();
			}
		}, "no reconfigure transition");
	}

    private static MTS<Long, String> oldController() {
        MTS<Long, String> mts = new MTSImpl<Long, String>(Long.valueOf(0L));
        mts.addState(Long.valueOf(1L));
        mts.addAction("a");
        mts.addRequired(Long.valueOf(0L), "a", Long.valueOf(1L));
        mts.addRequired(Long.valueOf(1L), "a", Long.valueOf(0L));
        return mts;
    }

    private static MTS<Long, String> mapping() {
        MTS<Long, String> mts = new MTSImpl<Long, String>(Long.valueOf(10L));
        mts.addState(Long.valueOf(11L));
        mts.addAction("a");
		mts.addAction(UpdateConstants.RECONFIGURE);
        mts.addRequired(Long.valueOf(10L), "a", Long.valueOf(11L));
        mts.addRequired(Long.valueOf(11L), "a", Long.valueOf(10L));
		mts.addRequired(Long.valueOf(10L), UpdateConstants.RECONFIGURE,
				Long.valueOf(10L));
        return mts;
    }

    private static void expectUnsupported(Runnable mutation) {
        try {
            mutation.run();
            fail("Expected immutable provenance");
        } catch (UnsupportedOperationException expected) {
            // Expected.
        }
    }

    private static void expectIllegal(Runnable operation, String fragment) {
        try {
            operation.run();
            fail("Expected an IllegalArgumentException containing " + fragment);
        } catch (IllegalArgumentException expected) {
            assertTrue(expected.getMessage(),
                    expected.getMessage().contains(fragment));
        }
    }

    private static String mtsRows(MTS<Long, String> mts) {
        List<String> rows = new ArrayList<String>();
        for (Long state : mts.getStates()) {
            for (Pair<String, Long> edge : mts.getTransitions(
                    state, MTS.TransitionType.REQUIRED)) {
                rows.add(state + ":" + edge.getFirst() + ":" + edge.getSecond());
            }
            for (Pair<String, Long> edge : mts.getTransitions(
                    state, MTS.TransitionType.MAYBE)) {
                rows.add(state + ":MAYBE:" + edge.getFirst() + ":" + edge.getSecond());
            }
        }
        Collections.sort(rows);
        return mts.getInitialState() + "|" + new java.util.TreeSet<Long>(
                mts.getStates()) + "|" + new java.util.TreeSet<String>(
                mts.getActions()) + "|" + rows;
    }

    private static String environmentRows(UpdatingEnvironment environment) {
        List<String> rows = new ArrayList<String>();
        for (Long state : environment.getStates()) {
            for (Pair<String, Long> edge : environment.getTransitionsFrom(state)) {
                rows.add(state + ":" + edge.getFirst() + ":" + edge.getSecond());
            }
        }
        Collections.sort(rows);
        return environment.getInitialState() + "|" + new java.util.TreeSet<Long>(
                environment.getStates()) + "|" + new java.util.TreeSet<String>(
                environment.getActions()) + "|" + rows;
    }
}
