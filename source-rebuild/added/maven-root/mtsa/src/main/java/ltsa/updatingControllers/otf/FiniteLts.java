package ltsa.updatingControllers.otf;

import MTSTools.ac.ic.doc.commons.relations.Pair;
import MTSTools.ac.ic.doc.mtstools.model.LTS;
import MTSTools.ac.ic.doc.mtstools.model.MTS;
import ltsa.ac.ic.doc.mtstools.util.fsp.AutomataToMTSConverter;
import ltsa.lts.CompactState;

import java.util.ArrayList;
import java.util.ArrayDeque;
import java.util.Collection;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Deque;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

/**
 * Immutable finite, possibly nondeterministic labelled transition system.
 *
 * <p>The declared alphabet is retained independently of enabled transitions;
 * this distinction is required by synchronous-product semantics.</p>
 */
public final class FiniteLts<S> {

    private final S initialState;
    private final Set<S> states;
    private final Set<String> alphabet;
    private final Map<S, Map<String, Set<S>>> transitions;

    private FiniteLts(
            S initialState,
            Collection<? extends S> states,
            Collection<String> alphabet,
            Map<S, ? extends Map<String, ? extends Collection<? extends S>>> transitions) {
        this.initialState = Objects.requireNonNull(initialState, "initialState");
        this.states = immutableSet(states, "states");
        this.alphabet = immutableActions(alphabet);
        if (!this.states.contains(initialState)) {
            throw new IllegalArgumentException("Initial state is not in the state set: " + initialState);
        }

        Map<S, Map<String, Set<S>>> transitionCopy = new LinkedHashMap<>();
        for (S state : this.states) {
            Map<String, Set<S>> byActionCopy = new LinkedHashMap<>();
            Map<String, ? extends Collection<? extends S>> byAction = transitions.get(state);
            if (byAction != null) {
                for (Map.Entry<String, ? extends Collection<? extends S>> entry : byAction.entrySet()) {
                    String action = validateAction(entry.getKey(), "transition action");
                    if (!this.alphabet.contains(action)) {
                        throw new IllegalArgumentException("Transition action is outside the alphabet: " + action);
                    }
                    Set<S> outcomes = immutableSet(entry.getValue(), "transition outcomes");
                    if (outcomes.isEmpty()) {
                        continue;
                    }
                    for (S target : outcomes) {
                        if (!this.states.contains(target)) {
                            throw new IllegalArgumentException(
                                    "Transition target is outside the state set: " + target);
                        }
                    }
                    byActionCopy.put(action, outcomes);
                }
            }
            transitionCopy.put(state, Collections.unmodifiableMap(byActionCopy));
        }
        for (S source : transitions.keySet()) {
            if (!this.states.contains(source)) {
                throw new IllegalArgumentException("Transition source is outside the state set: " + source);
            }
        }
        this.transitions = Collections.unmodifiableMap(transitionCopy);
    }

    public static <S> Builder<S> builder() {
        return new Builder<>();
    }

    public static <S> Builder<S> builder(S initialState) {
        return FiniteLts.<S>builder().initialState(initialState);
    }

    /** Creates an immutable snapshot of an MTSA LTS. */
    public static <S> FiniteLts<S> fromMtsa(LTS<S, String> source) {
        Objects.requireNonNull(source, "source");
        S initial = Objects.requireNonNull(source.getInitialState(), "MTSA initial state");
        Set<S> sourceStates = new LinkedHashSet<>(source.getStates());
        if (!sourceStates.contains(initial)) {
            throw new IllegalArgumentException("MTSA initial state is outside its state set: " + initial);
        }
        Builder<S> builder = builder(initial);
        builder.addStates(sourceStates);

        List<String> actions = new ArrayList<String>();
        for (String action : source.getActions()) {
            if (!"tau".equals(action)) actions.add(action);
        }
        Collections.sort(actions);
        builder.addActions(actions);
        Set<String> sourceActions = new LinkedHashSet<>(actions);

        for (S state : sourceStates) {
            if (source.getTransitions(state) == null) {
                continue;
            }
            for (Pair<String, S> edge : source.getTransitions(state)) {
                if ("tau".equals(edge.getFirst())) {
                    throw new IllegalArgumentException(
                            "Internal tau transitions must be eliminated before importing an MTSA LTS");
                }
                if (!sourceActions.contains(edge.getFirst())) {
                    throw new IllegalArgumentException(
                            "MTSA transition action is outside its declared alphabet: " + edge.getFirst());
                }
                if (!sourceStates.contains(edge.getSecond())) {
                    throw new IllegalArgumentException(
                            "MTSA transition target is outside its state set: " + edge.getSecond());
                }
                builder.addTransition(state, edge.getFirst(), edge.getSecond());
            }
        }
        return builder.build();
    }

    /** Convenience adapter for the existing LTSA representation. */
    public static FiniteLts<Long> fromMtsa(CompactState source) {
        Objects.requireNonNull(source, "source");
        AutomataToMTSConverter converter = AutomataToMTSConverter.getInstance();
        MTS<Long, String> mts;
        synchronized (converter) {
            mts = converter.convert(source);
        }
        Builder<Long> builder = builder(mts.getInitialState()).addStates(mts.getStates());
        List<String> actions = new ArrayList<String>();
        for (String action : mts.getActions()) {
            if (!"tau".equals(action)) actions.add(action);
        }
        Collections.sort(actions);
        builder.addActions(actions);
        for (Long state : mts.getStates()) {
            if (!mts.getTransitions(state, MTS.TransitionType.MAYBE).isEmpty()) {
                throw new IllegalArgumentException(
                        "Revised OTF-DUCS accepts finite LTS input only; modal '?' transitions "
                                + "are unsupported in CompactState " + source.getName());
            }
            for (Pair<String, Long> edge
                    : mts.getTransitions(state, MTS.TransitionType.REQUIRED)) {
                if ("tau".equals(edge.getFirst())) {
                    throw new IllegalArgumentException(
                            "Internal tau transitions must be eliminated before importing CompactState "
                                    + source.getName());
                }
                builder.addTransition(state, edge.getFirst(), edge.getSecond());
            }
        }
        return builder.build();
    }

    public S initialState() {
        return initialState;
    }

    public Set<S> states() {
        return states;
    }

    public Set<String> alphabet() {
        return alphabet;
    }

    public boolean hasAction(String action) {
        return alphabet.contains(action);
    }

    public Set<S> successors(S state, String action) {
        Map<String, Set<S>> byAction = transitions.get(state);
        if (byAction == null) {
            throw new IllegalArgumentException("Unknown state: " + state);
        }
        Set<S> result = byAction.get(action);
        return result == null ? Collections.emptySet() : result;
    }

    public Set<String> enabledActions(S state) {
        Map<String, Set<S>> byAction = transitions.get(state);
        if (byAction == null) {
            throw new IllegalArgumentException("Unknown state: " + state);
        }
        return byAction.keySet();
    }

    public Map<S, Map<String, Set<S>>> transitions() {
        return transitions;
    }

    /** Numbered REQUIRED-transition export for the existing MTSA/LTSA toolchain. */
    public MtsaLtsExport<S> toMtsa() {
        return MtsaLtsExport.from(this);
    }

    /** Reachable states in deterministic breadth-first discovery order. */
    public Set<S> reachableStates() {
        LinkedHashSet<S> reachable = new LinkedHashSet<>();
        Deque<S> queue = new ArrayDeque<>();
        reachable.add(initialState);
        queue.addLast(initialState);
        while (!queue.isEmpty()) {
            S source = queue.removeFirst();
            for (String action : alphabet) {
                for (S target : successors(source, action)) {
                    if (reachable.add(target)) {
                        queue.addLast(target);
                    }
                }
            }
        }
        return Collections.unmodifiableSet(reachable);
    }

    public static final class Builder<S> {
        private S initialState;
        private final Set<S> states = new LinkedHashSet<>();
        private final Set<String> alphabet = new LinkedHashSet<>();
        private final Map<S, Map<String, Set<S>>> transitions = new LinkedHashMap<>();

        public Builder<S> initialState(S state) {
            this.initialState = Objects.requireNonNull(state, "initialState");
            this.states.add(state);
            return this;
        }

        public Builder<S> addState(S state) {
            this.states.add(Objects.requireNonNull(state, "state"));
            return this;
        }

        public Builder<S> addStates(Collection<? extends S> states) {
            Objects.requireNonNull(states, "states");
            for (S state : states) {
                addState(state);
            }
            return this;
        }

        public Builder<S> addAction(String action) {
            this.alphabet.add(validateAction(action, "action"));
            return this;
        }

        public Builder<S> addActions(Collection<String> actions) {
            Objects.requireNonNull(actions, "actions");
            for (String action : actions) {
                addAction(action);
            }
            return this;
        }

        public Builder<S> addTransition(S source, String action, S target) {
            source = Objects.requireNonNull(source, "source");
            target = Objects.requireNonNull(target, "target");
            action = validateAction(action, "action");
            states.add(source);
            states.add(target);
            alphabet.add(action);
            transitions.computeIfAbsent(source, ignored -> new LinkedHashMap<>())
                    .computeIfAbsent(action, ignored -> new LinkedHashSet<>())
                    .add(target);
            return this;
        }

        public FiniteLts<S> build() {
            if (initialState == null) {
                throw new IllegalStateException("An initial state is required");
            }
            return new FiniteLts<>(initialState, states, alphabet, transitions);
        }
    }

    private static String validateAction(String action, String label) {
        Objects.requireNonNull(action, label);
        if (action.trim().isEmpty()) {
            throw new IllegalArgumentException(label + " must not be blank");
        }
        return action;
    }

    private static Set<String> immutableActions(Collection<String> actions) {
        Objects.requireNonNull(actions, "alphabet");
        LinkedHashSet<String> copy = new LinkedHashSet<>();
        for (String action : actions) {
            copy.add(validateAction(action, "alphabet action"));
        }
        return Collections.unmodifiableSet(copy);
    }

    private static <T> Set<T> immutableSet(Collection<? extends T> values, String label) {
        Objects.requireNonNull(values, label);
        LinkedHashSet<T> copy = new LinkedHashSet<>();
        for (T value : values) {
            copy.add(Objects.requireNonNull(value, label + " element"));
        }
        return Collections.unmodifiableSet(copy);
    }
}
