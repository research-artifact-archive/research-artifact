package ltsa.updatingControllers.synthesis;

import MTSTools.ac.ic.doc.mtstools.model.MTS;
import MTSTools.ac.ic.doc.mtstools.model.impl.MTSImpl;
import MTSSynthesis.ar.dc.uba.model.condition.Fluent;
import MTSSynthesis.ar.dc.uba.model.condition.FluentImpl;
import MTSSynthesis.ar.dc.uba.model.condition.FluentPropositionalVariable;
import MTSSynthesis.ar.dc.uba.model.condition.Formula;
import MTSSynthesis.ar.dc.uba.model.condition.AndFormula;
import MTSSynthesis.ar.dc.uba.model.condition.NotFormula;
import MTSSynthesis.ar.dc.uba.model.condition.OrFormula;
import MTSSynthesis.ar.dc.uba.model.language.SingleSymbol;
import MTSSynthesis.ar.dc.uba.model.language.Symbol;
import MTSSynthesis.controller.util.FluentStateValuation;
import ltsa.updatingControllers.UpdateConstants;
import ltsa.updatingControllers.export.M9TraditionalSafetySemanticsSnapshot;
import org.testng.annotations.Test;

import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

import static org.testng.Assert.assertEquals;
import static org.testng.Assert.assertFalse;
import static org.testng.Assert.assertTrue;

public class UpdatingControllerSafetySynthesizerM9LifecycleTest {

    @Test
    public void oldActionNormalizationRequiresTheTerminalSuffix() {
        assertTrue(UpdatingControllersUtils.isOld("a.old"));
        assertFalse(UpdatingControllersUtils.isOld("a.old.tail"));
        assertFalse(UpdatingControllersUtils.isOld(null));
        assertEquals(UpdatingControllersUtils.withoutOld("a.old"), "a");
    }

    @Test(expectedExceptions = IllegalArgumentException.class)
    public void embeddedOldTextCannotBeStripped() {
        UpdatingControllersUtils.withoutOld("a.old.tail");
    }

    @Test
    public void confluentDiamondHasOneStableValuation() {
        MTS<Long, String> diamond = diamond("on", "alsoOn");
        Fluent fluent = fluent(
                "F", false,
                setOfSymbols("on", "alsoOn"),
                setOfSymbols("off"));
        FluentStateValuation<Long> valuation =
                UpdatingControllerSafetySynthesizer.buildValuations(
                        diamond, Collections.singleton(fluent));
        assertTrue(valuation.isTrue(Long.valueOf(3L), fluent));
    }

    @Test(expectedExceptions = IllegalArgumentException.class,
            expectedExceptionsMessageRegExp = ".*path-dependent.*")
    public void conflictingDiamondIsRejected() {
        MTS<Long, String> diamond = diamond("on", "idle");
        Fluent fluent = fluent(
                "F", false,
                setOfSymbols("on"),
                setOfSymbols("off"));
        UpdatingControllerSafetySynthesizer.buildValuations(
                diamond, Collections.singleton(fluent));
    }

    @Test(expectedExceptions = IllegalArgumentException.class,
            expectedExceptionsMessageRegExp = ".*both initiate and terminate.*")
    public void fluentInitiationAndTerminationMustBeDisjoint() {
        Fluent fluent = fluent(
                "F", false, setOfSymbols("on"), setOfSymbols("on"));
        UpdatingControllerSafetySynthesizer.buildValuations(
                diamond("on", "alsoOn"), Collections.singleton(fluent));
    }

    @Test
    public void registeredLifecycleRequiresStopReconfigureStartPrecedence() {
        MTS<Long, String> base = new MTSImpl<Long, String>(Long.valueOf(0L));
        for (String action : Arrays.asList(
                "a",
                UpdateConstants.STOP_OLD_SPEC,
                UpdateConstants.RECONFIGURE,
                UpdateConstants.START_NEW_SPEC)) {
            base.addAction(action);
            base.addRequired(Long.valueOf(0L), action, Long.valueOf(0L));
        }

        MTS<Long, String> ordered =
                UpdatingControllerSafetySynthesizer.getDontDoTwiceGoals(
                        base,
                        Arrays.asList(
                                UpdateConstants.STOP_OLD_SPEC,
                                UpdateConstants.RECONFIGURE,
                                UpdateConstants.START_NEW_SPEC));
        Long initial = ordered.getInitialState();
        Long afterStop = uniqueNonErrorTarget(
                ordered, initial, UpdateConstants.STOP_OLD_SPEC);
        Long afterReconfigure = uniqueNonErrorTarget(
                ordered, afterStop, UpdateConstants.RECONFIGURE);
        Long afterStart = uniqueNonErrorTarget(
                ordered, afterReconfigure, UpdateConstants.START_NEW_SPEC);

        assertFalse(afterStop.equals(initial));
        assertFalse(afterReconfigure.equals(afterStop));
        assertFalse(afterStart.equals(afterReconfigure));
        assertEquals(requiredTargets(ordered, afterStop, "a"),
                java.util.Collections.singleton(afterStop));
        assertTrue(requiredTargets(
                ordered, initial, UpdateConstants.RECONFIGURE)
                .contains(Long.valueOf(-1L)));
        assertTrue(requiredTargets(
                ordered, initial, UpdateConstants.START_NEW_SPEC)
                .contains(Long.valueOf(-1L)));
        assertTrue(requiredTargets(
                ordered, afterStop, UpdateConstants.STOP_OLD_SPEC)
                .contains(Long.valueOf(-1L)));
        assertTrue(requiredTargets(
                ordered, afterReconfigure, UpdateConstants.STOP_OLD_SPEC)
                .contains(Long.valueOf(-1L)));
        assertTrue(requiredTargets(
                ordered, afterStart, UpdateConstants.START_NEW_SPEC)
                .contains(Long.valueOf(-1L)));
    }

    @Test
    public void capturesExactFluentFormulaAndLifecycleAuthority() {
        MTS<Long, String> meta = new MTSImpl<Long, String>(Long.valueOf(0L));
        meta.addState(Long.valueOf(1L));
        for (String action : Arrays.asList(
                "on", "off", "on.old", "off.old",
                UpdateConstants.STOP_OLD_SPEC,
                UpdateConstants.RECONFIGURE,
                UpdateConstants.START_NEW_SPEC)) {
            meta.addAction(action);
        }
        meta.addRequired(Long.valueOf(0L), "on.old", Long.valueOf(1L));
        meta.addRequired(Long.valueOf(1L), "off.old", Long.valueOf(0L));
        for (Long state : Arrays.asList(Long.valueOf(0L), Long.valueOf(1L))) {
            meta.addRequired(state, UpdateConstants.STOP_OLD_SPEC, state);
            meta.addRequired(state, UpdateConstants.RECONFIGURE, state);
            meta.addRequired(state, UpdateConstants.START_NEW_SPEC, state);
        }

        Fluent fluent = fluent(
                "F", false, setOfSymbols("on"), setOfSymbols("off"));
        Set<Fluent> fluents = Collections.singleton(fluent);
        Map<String, String> oldActions = new LinkedHashMap<String, String>();
        oldActions.put("off.old", "off");
        oldActions.put("on.old", "on");
        FluentStateValuation<Long> valuation =
                UpdatingControllerSafetySynthesizer.buildValuations(
                        meta, fluents, oldActions);

        Formula first = new FluentPropositionalVariable(fluent);
        Formula second = new AndFormula(
                Formula.TRUE_FORMULA,
                new OrFormula(
                        Formula.FALSE_FORMULA,
                        new NotFormula(new FluentPropositionalVariable(fluent))));
        List<M9TraditionalSafetySemanticsSnapshot.FormulaInput> inputs =
                Arrays.asList(
                        M9TraditionalSafetySemanticsSnapshot.FormulaInput.of(
                                "SAFE.old", "SAFE",
                                M9TraditionalSafetySemanticsSnapshot.FormulaKind
                                        .OLD_SAFETY,
                                first),
                        M9TraditionalSafetySemanticsSnapshot.FormulaInput.of(
                                "TRANS", "TRANS",
                                M9TraditionalSafetySemanticsSnapshot.FormulaKind
                                        .TRANSITION_REQUIREMENT,
                                second));
        M9TraditionalSafetySemanticsSnapshot snapshot =
                M9TraditionalSafetySemanticsSnapshot.capture(
                        meta,
                        fluents,
                        inputs,
                        valuation,
                        oldActions,
                        Arrays.asList(
                                UpdateConstants.STOP_OLD_SPEC,
                                UpdateConstants.RECONFIGURE,
                                UpdateConstants.START_NEW_SPEC));

        assertEquals(snapshot.getFluentCatalog().size(), 1);
        assertEquals(snapshot.getFluentCatalog().get(0).getName(), "F");
        assertEquals(snapshot.getValuations().get(0).getTrueFluents(),
                Collections.emptySet());
        assertEquals(snapshot.getValuations().get(1).getTrueFluents(),
                Collections.singleton("F"));
        assertEquals(snapshot.getFormulas().get(0).getTrueStates(),
                Collections.singleton(Long.valueOf(1L)));
        assertEquals(snapshot.getFormulas().get(1).getTrueStates(),
                Collections.singleton(Long.valueOf(0L)));
        assertEquals(snapshot.getFormulas().get(1).getPostfix().get(0)
                .getOpcode(), M9TraditionalSafetySemanticsSnapshot.Opcode.TRUE);
        assertEquals(snapshot.getFormulas().get(1).getPostfix().get(1)
                .getOpcode(), M9TraditionalSafetySemanticsSnapshot.Opcode.FALSE);
        assertEquals(snapshot.getFormulas().get(1).getPostfix().get(2)
                .getOpcode(), M9TraditionalSafetySemanticsSnapshot.Opcode.FLUENT);
        assertEquals(snapshot.getFormulas().get(1).getPostfix().get(3)
                .getOpcode(), M9TraditionalSafetySemanticsSnapshot.Opcode.NOT);
        assertEquals(snapshot.getFormulas().get(1).getPostfix().get(4)
                .getOpcode(), M9TraditionalSafetySemanticsSnapshot.Opcode.OR);
        assertEquals(snapshot.getFormulas().get(1).getPostfix().get(5)
                .getOpcode(), M9TraditionalSafetySemanticsSnapshot.Opcode.AND);
        assertEquals(snapshot.getUnsafeStates(),
                new LinkedHashSet<Long>(Arrays.asList(
                        Long.valueOf(0L), Long.valueOf(1L))));
        assertEquals(snapshot.getDerivedOldActionToSourceAction(), oldActions);
        assertEquals(snapshot.getLifecycleProfile(),
                M9TraditionalSafetySemanticsSnapshot.LifecycleProfile
                        .ORDERED_STOP_RECONFIGURE_START_COMPLETE);
    }

    @Test(expectedExceptions = IllegalArgumentException.class,
            expectedExceptionsMessageRegExp = ".*Unsupported safety formula.*")
    public void customFormulaImplementationIsRejected() {
        MTS<Long, String> meta = new MTSImpl<Long, String>(Long.valueOf(0L));
        meta.addAction("idle");
        meta.addRequired(Long.valueOf(0L), "idle", Long.valueOf(0L));
        FluentStateValuation<Long> valuation =
                UpdatingControllerSafetySynthesizer.buildValuations(
                        meta, Collections.<Fluent>emptySet());
        Formula custom = new Formula() {
            @Override
            public boolean evaluate(
                    MTSSynthesis.ar.dc.uba.model.condition.Valuation ignored) {
                return false;
            }
        };
        M9TraditionalSafetySemanticsSnapshot.capture(
                meta,
                Collections.<Fluent>emptySet(),
                Collections.singletonList(
                        M9TraditionalSafetySemanticsSnapshot.FormulaInput.of(
                                "CUSTOM", "CUSTOM",
                                M9TraditionalSafetySemanticsSnapshot.FormulaKind
                                        .SYNTHETIC,
                                custom)),
                valuation,
                Collections.<String, String>emptyMap(),
                Collections.singletonList("idle"));
    }

    private static Set<Long> requiredTargets(
            MTS<Long, String> model, Long state, String action) {
        return model.getTransitions(state, MTS.TransitionType.REQUIRED)
                .getImage(action);
    }

    private static Long uniqueNonErrorTarget(
            MTS<Long, String> model, Long state, String action) {
        Set<Long> targets = requiredTargets(model, state, action);
        assertEquals(targets.size(), 1);
        Long target = targets.iterator().next();
        assertFalse(target.equals(Long.valueOf(-1L)));
        return target;
    }

    private static MTS<Long, String> diamond(
            String leftAction, String rightAction) {
        MTS<Long, String> result = new MTSImpl<Long, String>(Long.valueOf(0L));
        for (Long state : Arrays.asList(
                Long.valueOf(1L), Long.valueOf(2L), Long.valueOf(3L))) {
            result.addState(state);
        }
        for (String action : Arrays.asList(
                leftAction, rightAction, "join")) {
            result.addAction(action);
        }
        result.addRequired(Long.valueOf(0L), leftAction, Long.valueOf(1L));
        result.addRequired(Long.valueOf(0L), rightAction, Long.valueOf(2L));
        result.addRequired(Long.valueOf(1L), "join", Long.valueOf(3L));
        result.addRequired(Long.valueOf(2L), "join", Long.valueOf(3L));
        return result;
    }

    private static Fluent fluent(
            String name, boolean initial, Set<Symbol> initiating,
            Set<Symbol> terminating) {
        return new FluentImpl(name, initiating, terminating, initial);
    }

    private static Set<Symbol> setOfSymbols(String... names) {
        Set<Symbol> result = new LinkedHashSet<Symbol>();
        for (String name : names) result.add(new SingleSymbol(name));
        return result;
    }
}
