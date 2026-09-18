package ltsa.updatingControllers.export;

import MTSSynthesis.ar.dc.uba.model.condition.AndFormula;
import MTSSynthesis.ar.dc.uba.model.condition.BinaryFormula;
import MTSSynthesis.ar.dc.uba.model.condition.Fluent;
import MTSSynthesis.ar.dc.uba.model.condition.FluentPropositionalVariable;
import MTSSynthesis.ar.dc.uba.model.condition.Formula;
import MTSSynthesis.ar.dc.uba.model.condition.NotFormula;
import MTSSynthesis.ar.dc.uba.model.condition.OrFormula;
import MTSSynthesis.ar.dc.uba.model.language.SingleSymbol;
import MTSSynthesis.ar.dc.uba.model.language.Symbol;
import MTSSynthesis.controller.util.FluentStateValuation;
import ltsa.updatingControllers.UpdateConstants;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.Comparator;
import java.util.Deque;
import java.util.IdentityHashMap;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Immutable authority for the exact fluent and safety-formula semantics used
 * by the traditional pre-GR safety stage.
 *
 * <p>The legacy synthesizer evaluated mutable fluent/formula objects and then
 * retained only the union of violating states.  This snapshot independently
 * replays the fluent valuation over a frozen MTS, encodes a closed formula
 * language, checks every legacy result cell, and retains the full authority
 * needed by an independent receipt decoder.</p>
 */
public final class M9TraditionalSafetySemanticsSnapshot {
    private static final int MAX_IDENTIFIER_CHARS = 256;
    private static final int MAX_FLUENTS = 8_192;
    private static final int MAX_FORMULAS = 4_096;
    private static final int MAX_FORMULA_DEPTH = 64;
    private static final long MAX_FORMULA_TOKENS = 65_536L;
    private static final long MAX_VALUATION_TRUE_CELLS = 4_000_000L;
    private static final long MAX_FORMULA_TRUE_CELLS = 4_000_000L;

    public enum FormulaKind {
        OLD_SAFETY,
        NEW_SAFETY,
        TRANSITION_REQUIREMENT,
        SYNTHETIC
    }

    public enum Opcode {
        TRUE,
        FALSE,
        FLUENT,
        NOT,
        AND,
        OR
    }

    public enum LifecycleProfile {
        ORDERED_STOP_RECONFIGURE_START_COMPLETE,
        INDEPENDENT_AT_MOST_ONCE
    }

    /** Temporary, bounded input consumed during immutable capture. */
    public static final class FormulaInput {
        private final String definitionName;
        private final String sourceAssertionName;
        private final FormulaKind kind;
        private final Formula formula;

        public static FormulaInput of(
                String definitionName,
                String sourceAssertionName,
                FormulaKind kind,
                Formula formula) {
            return new FormulaInput(
                    definitionName, sourceAssertionName, kind, formula);
        }

        private FormulaInput(
                String definitionName,
                String sourceAssertionName,
                FormulaKind kind,
                Formula formula) {
            requireIdentifier(definitionName, "Formula definition");
            requireIdentifier(sourceAssertionName, "Formula source assertion");
            if (kind == null || formula == null) {
                throw new IllegalArgumentException(
                        "Formula authority input is incomplete.");
            }
            this.definitionName = definitionName;
            this.sourceAssertionName = sourceAssertionName;
            this.kind = kind;
            this.formula = formula;
        }

        public boolean isFormulaIdentity(Formula candidate) {
            return formula == candidate;
        }
    }

    public static final class FormulaToken {
        private final Opcode opcode;
        private final String fluentName;

        private FormulaToken(Opcode opcode, String fluentName) {
            this.opcode = opcode;
            this.fluentName = fluentName;
        }

        public Opcode getOpcode() {
            return opcode;
        }

        public String getFluentName() {
            return fluentName;
        }

        @Override
        public boolean equals(Object candidate) {
            if (this == candidate) return true;
            if (!(candidate instanceof FormulaToken)) return false;
            FormulaToken other = (FormulaToken) candidate;
            return opcode == other.opcode
                    && (fluentName == null
                    ? other.fluentName == null
                    : fluentName.equals(other.fluentName));
        }

        @Override
        public int hashCode() {
            return 31 * opcode.hashCode()
                    + (fluentName == null ? 0 : fluentName.hashCode());
        }
    }

    public static final class FluentRow {
        private final String name;
        private final boolean initialValue;
        private final Set<String> initiatingActions;
        private final Set<String> terminatingActions;

        private FluentRow(
                String name,
                boolean initialValue,
                Collection<String> initiatingActions,
                Collection<String> terminatingActions) {
            this.name = name;
            this.initialValue = initialValue;
            this.initiatingActions = immutableSortedStrings(initiatingActions);
            this.terminatingActions = immutableSortedStrings(terminatingActions);
        }

        public String getName() {
            return name;
        }

        public boolean getInitialValue() {
            return initialValue;
        }

        public Set<String> getInitiatingActions() {
            return initiatingActions;
        }

        public Set<String> getTerminatingActions() {
            return terminatingActions;
        }

        @Override
        public boolean equals(Object candidate) {
            if (this == candidate) return true;
            if (!(candidate instanceof FluentRow)) return false;
            FluentRow other = (FluentRow) candidate;
            return initialValue == other.initialValue
                    && name.equals(other.name)
                    && initiatingActions.equals(other.initiatingActions)
                    && terminatingActions.equals(other.terminatingActions);
        }

        @Override
        public int hashCode() {
            int result = name.hashCode();
            result = 31 * result + (initialValue ? 1 : 0);
            result = 31 * result + initiatingActions.hashCode();
            result = 31 * result + terminatingActions.hashCode();
            return result;
        }
    }

    public static final class StateValuationRow {
        private final long state;
        private final Set<String> trueFluents;

        private StateValuationRow(long state, Collection<String> trueFluents) {
            this.state = state;
            this.trueFluents = immutableSortedStrings(trueFluents);
        }

        public long getState() {
            return state;
        }

        public Set<String> getTrueFluents() {
            return trueFluents;
        }

        @Override
        public boolean equals(Object candidate) {
            if (this == candidate) return true;
            if (!(candidate instanceof StateValuationRow)) return false;
            StateValuationRow other = (StateValuationRow) candidate;
            return state == other.state && trueFluents.equals(other.trueFluents);
        }

        @Override
        public int hashCode() {
            int result = (int) (state ^ (state >>> 32));
            return 31 * result + trueFluents.hashCode();
        }
    }

    public static final class FormulaRow {
        private final int inputOrdinal;
        private final String definitionName;
        private final String sourceAssertionName;
        private final FormulaKind kind;
        private final List<FormulaToken> postfix;
        private final Set<Long> trueStates;

        private FormulaRow(
                int inputOrdinal,
                String definitionName,
                String sourceAssertionName,
                FormulaKind kind,
                Collection<FormulaToken> postfix,
                Collection<Long> trueStates) {
            this.inputOrdinal = inputOrdinal;
            this.definitionName = definitionName;
            this.sourceAssertionName = sourceAssertionName;
            this.kind = kind;
            this.postfix = Collections.unmodifiableList(
                    new ArrayList<FormulaToken>(postfix));
            this.trueStates = immutableSortedLongs(trueStates);
        }

        public int getInputOrdinal() {
            return inputOrdinal;
        }

        public String getDefinitionName() {
            return definitionName;
        }

        public String getSourceAssertionName() {
            return sourceAssertionName;
        }

        public FormulaKind getKind() {
            return kind;
        }

        public List<FormulaToken> getPostfix() {
            return postfix;
        }

        public Set<Long> getTrueStates() {
            return trueStates;
        }

        @Override
        public boolean equals(Object candidate) {
            if (this == candidate) return true;
            if (!(candidate instanceof FormulaRow)) return false;
            FormulaRow other = (FormulaRow) candidate;
            return inputOrdinal == other.inputOrdinal
                    && definitionName.equals(other.definitionName)
                    && sourceAssertionName.equals(other.sourceAssertionName)
                    && kind == other.kind
                    && postfix.equals(other.postfix)
                    && trueStates.equals(other.trueStates);
        }

        @Override
        public int hashCode() {
            int result = inputOrdinal;
            result = 31 * result + definitionName.hashCode();
            result = 31 * result + sourceAssertionName.hashCode();
            result = 31 * result + kind.hashCode();
            result = 31 * result + postfix.hashCode();
            result = 31 * result + trueStates.hashCode();
            return result;
        }
    }

    private final M9MtsSnapshot metaEnvironment;
    private final List<FluentRow> fluentCatalog;
    private final List<StateValuationRow> valuations;
    private final List<FormulaRow> formulas;
    private final Map<String, String> derivedOldActionToSourceAction;
    private final LifecycleProfile lifecycleProfile;
    private final List<String> lifecycleActions;
    private final Set<Long> unsafeStates;

    public static M9TraditionalSafetySemanticsSnapshot capture(
            MTSTools.ac.ic.doc.mtstools.model.MTS<Long, String> metaEnvironment,
            Collection<Fluent> finalFluents,
            List<FormulaInput> formulaInputs,
            FluentStateValuation<Long> legacyValuation,
            Map<String, String> derivedOldActionToSourceAction,
            Collection<String> lifecycleActions) {
        if (metaEnvironment == null || finalFluents == null
                || formulaInputs == null || legacyValuation == null
                || derivedOldActionToSourceAction == null
                || lifecycleActions == null) {
            throw new IllegalArgumentException(
                    "Traditional safety semantics requires every authority input.");
        }
        M9MtsSnapshot meta = M9MtsSnapshot.capture(metaEnvironment);
        List<FluentRow> fluents = captureFluents(finalFluents);
        if (!fluents.equals(captureFluents(finalFluents))) {
            throw new IllegalArgumentException(
                    "Fluent definitions changed during safety semantics capture.");
        }
        Map<String, FluentRow> fluentByName = new LinkedHashMap<String, FluentRow>();
        for (FluentRow fluent : fluents) fluentByName.put(fluent.name, fluent);

        Map<String, String> oldActions = captureDerivedOldActions(
                derivedOldActionToSourceAction, meta.getActions());
        List<String> lifecycle = captureLifecycleActions(lifecycleActions);
        LifecycleProfile profile = lifecycle.equals(registeredLifecycleActions())
                ? LifecycleProfile.ORDERED_STOP_RECONFIGURE_START_COMPLETE
                : LifecycleProfile.INDEPENDENT_AT_MOST_ONCE;

        Map<Long, Set<String>> replayed = replayValuations(
                meta, fluentByName, oldActions);
        List<StateValuationRow> valuationRows = new ArrayList<StateValuationRow>();
        long valuationTrueCells = 0L;
        for (Long state : sortedLongs(meta.getStates())) {
            Set<String> trueFluents = replayed.get(state);
            if (trueFluents == null) {
                throw new IllegalArgumentException(
                        "Traditional meta environment contains an unreachable state: "
                                + state);
            }
            for (Fluent fluent : finalFluents) {
                String name = fluent.getName();
                boolean expected = trueFluents.contains(name);
                if (legacyValuation.isTrue(state, fluent) != expected) {
                    throw new IllegalArgumentException(
                            "Legacy fluent valuation differs from the immutable replay at state "
                                    + state + " for " + name + ".");
                }
            }
            valuationTrueCells += trueFluents.size();
            requireCellCap(valuationTrueCells, MAX_VALUATION_TRUE_CELLS,
                    "Fluent valuation");
            valuationRows.add(new StateValuationRow(state.longValue(), trueFluents));
        }
        if (!legacyValuation.getStates().equals(meta.getStates())) {
            throw new IllegalArgumentException(
                    "Legacy fluent valuation state census differs from the meta environment.");
        }

        if (formulaInputs.size() > MAX_FORMULAS) {
            throw new IllegalArgumentException(
                    "Safety formula catalog exceeds the registered finite profile.");
        }
        Set<String> definitionNames = new LinkedHashSet<String>();
        List<FormulaRow> formulaRows = new ArrayList<FormulaRow>();
        Set<Long> unsafe = new LinkedHashSet<Long>();
        long tokenCount = 0L;
        long formulaTrueCells = 0L;
        for (int ordinal = 0; ordinal < formulaInputs.size(); ordinal++) {
            FormulaInput input = formulaInputs.get(ordinal);
            if (input == null || !definitionNames.add(input.definitionName)) {
                throw new IllegalArgumentException(
                        "Safety formula authority is absent or duplicated.");
            }
            List<FormulaToken> tokens = new ArrayList<FormulaToken>();
            encodeFormula(input.formula, fluentByName, tokens,
                    new IdentityHashMap<Formula, Boolean>(), 0);
            validatePostfix(tokens);
            tokenCount += tokens.size();
            requireCellCap(tokenCount, MAX_FORMULA_TOKENS, "Formula token");
            Set<Long> trueStates = new LinkedHashSet<Long>();
            for (Long state : sortedLongs(meta.getStates())) {
                boolean immutableValue = evaluatePostfix(tokens, replayed.get(state));
                legacyValuation.setActualState(state);
                boolean legacyValue = input.formula.evaluate(legacyValuation);
                if (immutableValue != legacyValue) {
                    throw new IllegalArgumentException(
                            "Legacy formula evaluation differs from the immutable replay at state "
                                    + state + " for " + input.definitionName + ".");
                }
                if (immutableValue) trueStates.add(state);
            }
            formulaTrueCells += trueStates.size();
            requireCellCap(formulaTrueCells, MAX_FORMULA_TRUE_CELLS,
                    "Formula truth");
            unsafe.addAll(trueStates);
            formulaRows.add(new FormulaRow(
                    ordinal,
                    input.definitionName,
                    input.sourceAssertionName,
                    input.kind,
                    tokens,
                    trueStates));
        }
        M9MtsSnapshot.requireStableSourceEquals(metaEnvironment, meta);
        if (!fluents.equals(captureFluents(finalFluents))) {
            throw new IllegalArgumentException(
                    "Fluent definitions changed during safety semantics capture.");
        }
        return new M9TraditionalSafetySemanticsSnapshot(
                meta, fluents, valuationRows, formulaRows, oldActions,
                profile, lifecycle, unsafe);
    }

    private M9TraditionalSafetySemanticsSnapshot(
            M9MtsSnapshot metaEnvironment,
            Collection<FluentRow> fluentCatalog,
            Collection<StateValuationRow> valuations,
            Collection<FormulaRow> formulas,
            Map<String, String> derivedOldActionToSourceAction,
            LifecycleProfile lifecycleProfile,
            Collection<String> lifecycleActions,
            Collection<Long> unsafeStates) {
        this.metaEnvironment = metaEnvironment;
        this.fluentCatalog = Collections.unmodifiableList(
                new ArrayList<FluentRow>(fluentCatalog));
        this.valuations = Collections.unmodifiableList(
                new ArrayList<StateValuationRow>(valuations));
        this.formulas = Collections.unmodifiableList(
                new ArrayList<FormulaRow>(formulas));
        this.derivedOldActionToSourceAction = Collections.unmodifiableMap(
                new LinkedHashMap<String, String>(derivedOldActionToSourceAction));
        this.lifecycleProfile = lifecycleProfile;
        this.lifecycleActions = Collections.unmodifiableList(
                new ArrayList<String>(lifecycleActions));
        this.unsafeStates = immutableSortedLongs(unsafeStates);
    }

    private static List<FluentRow> captureFluents(Collection<Fluent> source) {
        if (source.size() > MAX_FLUENTS) {
            throw new IllegalArgumentException(
                    "Fluent catalog exceeds the registered finite profile.");
        }
        List<FluentRow> result = new ArrayList<FluentRow>();
        Set<String> names = new LinkedHashSet<String>();
        for (Fluent fluent : source) {
            if (fluent == null) {
                throw new IllegalArgumentException("Fluent authority is absent.");
            }
            String name = fluent.getName();
            requireIdentifier(name, "Fluent");
            if (!names.add(name)) {
                throw new IllegalArgumentException(
                        "Fluent name is duplicated: " + name);
            }
            Set<String> initiating = captureSymbols(
                    fluent.getInitiatingActions(), "initiating");
            Set<String> terminating = captureSymbols(
                    fluent.getTerminatingActions(), "terminating");
            Set<String> overlap = new LinkedHashSet<String>(initiating);
            overlap.retainAll(terminating);
            if (!overlap.isEmpty()) {
                throw new IllegalArgumentException(
                        "A fluent action cannot both initiate and terminate: " + name);
            }
            result.add(new FluentRow(
                    name, fluent.getInitialValue(), initiating, terminating));
        }
        Collections.sort(result, new Comparator<FluentRow>() {
            @Override
            public int compare(FluentRow left, FluentRow right) {
                return left.name.compareTo(right.name);
            }
        });
        return result;
    }

    private static Set<String> captureSymbols(
            Collection<Symbol> source, String role) {
        if (source == null) {
            throw new IllegalArgumentException(
                    "Fluent " + role + " action set is absent.");
        }
        Set<String> result = new LinkedHashSet<String>();
        for (Symbol symbol : source) {
            if (symbol == null || symbol.getClass() != SingleSymbol.class) {
                throw new IllegalArgumentException(
                        "Fluent actions must be exact single symbols.");
            }
            String name = symbol.toString();
            requireIdentifier(name, "Fluent action");
            if (!result.add(name)) {
                throw new IllegalArgumentException(
                        "Fluent action is duplicated: " + name);
            }
        }
        return immutableSortedStrings(result);
    }

    private static Map<String, String> captureDerivedOldActions(
            Map<String, String> source, Set<String> alphabet) {
        List<String> keys = new ArrayList<String>(source.keySet());
        Collections.sort(keys);
        Map<String, String> result = new LinkedHashMap<String, String>();
        Set<String> values = new LinkedHashSet<String>();
        for (String derived : keys) {
            String base = source.get(derived);
            requireIdentifier(derived, "Derived old action");
            requireIdentifier(base, "Source old action");
            if (!derived.equals(base + UpdateConstants.OLD_LABEL)
                    || base.endsWith(UpdateConstants.OLD_LABEL)
                    || !alphabet.contains(derived)
                    || !alphabet.contains(base)
                    || !values.add(base)) {
                throw new IllegalArgumentException(
                        "Derived old-action authority is inconsistent: " + derived);
            }
            result.put(derived, base);
        }
        for (String action : alphabet) {
            if (action.endsWith(UpdateConstants.OLD_LABEL)
                    && !result.containsKey(action)) {
                throw new IllegalArgumentException(
                        "An .old action lacks an exact derivation authority: " + action);
            }
        }
        return result;
    }

    private static List<String> captureLifecycleActions(Collection<String> source) {
        List<String> result = new ArrayList<String>();
        Set<String> unique = new LinkedHashSet<String>();
        for (String action : source) {
            requireIdentifier(action, "Lifecycle action");
            if (!unique.add(action)) {
                throw new IllegalArgumentException(
                        "Lifecycle action is duplicated: " + action);
            }
            result.add(action);
        }
        if (result.isEmpty()) {
            throw new IllegalArgumentException("Lifecycle action authority is empty.");
        }
        return result;
    }

    private static List<String> registeredLifecycleActions() {
        List<String> result = new ArrayList<String>();
        result.add(UpdateConstants.STOP_OLD_SPEC);
        result.add(UpdateConstants.RECONFIGURE);
        result.add(UpdateConstants.START_NEW_SPEC);
        return result;
    }

    private static Map<Long, Set<String>> replayValuations(
            M9MtsSnapshot meta,
            Map<String, FluentRow> fluents,
            Map<String, String> oldActions) {
        Map<Long, Set<String>> result = new LinkedHashMap<Long, Set<String>>();
        Set<String> initial = new LinkedHashSet<String>();
        for (FluentRow fluent : fluents.values()) {
            if (fluent.initialValue) initial.add(fluent.name);
        }
        Long initialState = Long.valueOf(meta.getInitialState());
        result.put(initialState, immutableSortedStrings(initial));
        Deque<Long> pending = new ArrayDeque<Long>();
        pending.add(initialState);
        while (!pending.isEmpty()) {
            Long from = pending.removeFirst();
            Set<String> fromValue = result.get(from);
            Map<String, Set<Long>> row = meta.getPost().get(from);
            for (Map.Entry<String, Set<Long>> bucket : row.entrySet()) {
                String observed = bucket.getKey();
                String normalized = oldActions.containsKey(observed)
                        ? oldActions.get(observed) : observed;
                Set<String> next = new LinkedHashSet<String>();
                for (FluentRow fluent : fluents.values()) {
                    boolean holds = fromValue.contains(fluent.name);
                    if (fluent.terminatingActions.contains(normalized)) holds = false;
                    if (fluent.initiatingActions.contains(normalized)) holds = true;
                    if (holds) next.add(fluent.name);
                }
                Set<String> canonicalNext = immutableSortedStrings(next);
                for (Long target : bucket.getValue()) {
                    Set<String> existing = result.get(target);
                    if (existing == null) {
                        result.put(target, canonicalNext);
                        pending.addLast(target);
                    } else if (!existing.equals(canonicalNext)) {
                        throw new IllegalArgumentException(
                                "Traditional fluent valuation is path-dependent at state "
                                        + target + ".");
                    }
                }
            }
        }
        return result;
    }

    private static void encodeFormula(
            Formula formula,
            Map<String, FluentRow> fluentByName,
            List<FormulaToken> output,
            IdentityHashMap<Formula, Boolean> visiting,
            int depth) {
        if (formula == null || depth > MAX_FORMULA_DEPTH) {
            throw new IllegalArgumentException(
                    "Safety formula exceeds the registered depth profile.");
        }
        if (visiting.put(formula, Boolean.TRUE) != null) {
            throw new IllegalArgumentException("Safety formula contains a cycle.");
        }
        try {
            if (formula == Formula.TRUE_FORMULA) {
                output.add(new FormulaToken(Opcode.TRUE, null));
            } else if (formula == Formula.FALSE_FORMULA) {
                output.add(new FormulaToken(Opcode.FALSE, null));
            } else if (formula.getClass() == FluentPropositionalVariable.class) {
                String name = ((FluentPropositionalVariable) formula)
                        .getFluent().getName();
                requireIdentifier(name, "Formula fluent");
                if (!fluentByName.containsKey(name)) {
                    throw new IllegalArgumentException(
                            "Formula fluent is absent from the final catalog: " + name);
                }
                output.add(new FormulaToken(Opcode.FLUENT, name));
            } else if (formula.getClass() == NotFormula.class) {
                encodeFormula(((NotFormula) formula).getFormula(), fluentByName,
                        output, visiting, depth + 1);
                output.add(new FormulaToken(Opcode.NOT, null));
            } else if (formula.getClass() == AndFormula.class) {
                encodeBinary((BinaryFormula) formula, Opcode.AND, fluentByName,
                        output, visiting, depth);
            } else if (formula.getClass() == OrFormula.class) {
                encodeBinary((BinaryFormula) formula, Opcode.OR, fluentByName,
                        output, visiting, depth);
            } else {
                throw new IllegalArgumentException(
                        "Unsupported safety formula implementation: "
                                + formula.getClass().getName());
            }
            if (output.size() > MAX_FORMULA_TOKENS) {
                throw new IllegalArgumentException(
                        "Safety formula exceeds the registered token profile.");
            }
        } finally {
            visiting.remove(formula);
        }
    }

    private static void encodeBinary(
            BinaryFormula formula,
            Opcode opcode,
            Map<String, FluentRow> fluentByName,
            List<FormulaToken> output,
            IdentityHashMap<Formula, Boolean> visiting,
            int depth) {
        encodeFormula(formula.getLeftFormula(), fluentByName,
                output, visiting, depth + 1);
        encodeFormula(formula.getRightFormula(), fluentByName,
                output, visiting, depth + 1);
        output.add(new FormulaToken(opcode, null));
    }

    private static void validatePostfix(List<FormulaToken> tokens) {
        int stackDepth = 0;
        for (FormulaToken token : tokens) {
            if (token.opcode == Opcode.TRUE
                    || token.opcode == Opcode.FALSE
                    || token.opcode == Opcode.FLUENT) {
                stackDepth++;
            } else if (token.opcode == Opcode.NOT) {
                if (stackDepth < 1) throw invalidPostfix();
            } else {
                if (stackDepth < 2) throw invalidPostfix();
                stackDepth--;
            }
        }
        if (stackDepth != 1) throw invalidPostfix();
    }

    private static IllegalArgumentException invalidPostfix() {
        return new IllegalArgumentException(
                "Safety formula postfix authority is malformed.");
    }

    private static boolean evaluatePostfix(
            List<FormulaToken> tokens, Set<String> trueFluents) {
        Deque<Boolean> stack = new ArrayDeque<Boolean>();
        for (FormulaToken token : tokens) {
            switch (token.opcode) {
                case TRUE:
                    stack.addLast(Boolean.TRUE);
                    break;
                case FALSE:
                    stack.addLast(Boolean.FALSE);
                    break;
                case FLUENT:
                    stack.addLast(Boolean.valueOf(
                            trueFluents.contains(token.fluentName)));
                    break;
                case NOT:
                    stack.addLast(Boolean.valueOf(!stack.removeLast()));
                    break;
                case AND: {
                    boolean right = stack.removeLast().booleanValue();
                    boolean left = stack.removeLast().booleanValue();
                    stack.addLast(Boolean.valueOf(left && right));
                    break;
                }
                case OR: {
                    boolean right = stack.removeLast().booleanValue();
                    boolean left = stack.removeLast().booleanValue();
                    stack.addLast(Boolean.valueOf(left || right));
                    break;
                }
                default:
                    throw invalidPostfix();
            }
        }
        if (stack.size() != 1) throw invalidPostfix();
        return stack.removeLast().booleanValue();
    }

    private static Set<String> immutableSortedStrings(Collection<String> input) {
        List<String> sorted = new ArrayList<String>(input);
        Collections.sort(sorted);
        return Collections.unmodifiableSet(new LinkedHashSet<String>(sorted));
    }

    private static Set<Long> immutableSortedLongs(Collection<Long> input) {
        List<Long> sorted = sortedLongs(input);
        return Collections.unmodifiableSet(new LinkedHashSet<Long>(sorted));
    }

    private static List<Long> sortedLongs(Collection<Long> input) {
        List<Long> sorted = new ArrayList<Long>(input);
        Collections.sort(sorted);
        return sorted;
    }

    private static void requireIdentifier(String value, String role) {
        if (value == null || value.isEmpty()
                || value.length() > MAX_IDENTIFIER_CHARS) {
            throw new IllegalArgumentException(
                    role + " identifier is absent or exceeds the registered profile.");
        }
    }

    private static void requireCellCap(long value, long cap, String role) {
        if (value < 0L || value > cap) {
            throw new IllegalArgumentException(
                    role + " census exceeds the registered finite profile.");
        }
    }

    public M9MtsSnapshot getMetaEnvironment() {
        return metaEnvironment;
    }

    public List<FluentRow> getFluentCatalog() {
        return fluentCatalog;
    }

    public List<StateValuationRow> getValuations() {
        return valuations;
    }

    public List<FormulaRow> getFormulas() {
        return formulas;
    }

    public Map<String, String> getDerivedOldActionToSourceAction() {
        return derivedOldActionToSourceAction;
    }

    public LifecycleProfile getLifecycleProfile() {
        return lifecycleProfile;
    }

    public List<String> getLifecycleActions() {
        return lifecycleActions;
    }

    public Set<Long> getUnsafeStates() {
        return unsafeStates;
    }
}
