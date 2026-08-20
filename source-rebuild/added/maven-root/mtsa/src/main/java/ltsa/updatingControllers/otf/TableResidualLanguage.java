package ltsa.updatingControllers.otf;

import java.util.Collection;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

/** Immutable table implementation of {@link ResidualLanguage}. */
public final class TableResidualLanguage<R> implements ResidualLanguage<R> {
    private final R initialState;
    private final Set<R> states;
    private final Set<String> alphabet;
    private final Set<R> errorStates;
    private final Map<R, Map<String, R>> transitions;

    private TableResidualLanguage(
            R initialState,
            Set<R> states,
            Set<String> alphabet,
            Set<R> errorStates,
            Map<R, Map<String, R>> transitions) {
        this.initialState = initialState;
        this.states = states;
        this.alphabet = alphabet;
        this.errorStates = errorStates;
        this.transitions = transitions;
        validate();
    }

    public static <R> Builder<R> builder() {
        return new Builder<>();
    }

    @Override
    public Set<R> states() {
        return states;
    }

    @Override
    public Set<String> alphabet() {
        return alphabet;
    }

    @Override
    public R initialState() {
        return initialState;
    }

    @Override
    public R step(R state, String action) {
        Map<String, R> byAction = transitions.get(state);
        if (byAction == null) {
            throw new IllegalArgumentException("Unknown residual state: " + state);
        }
        R target = byAction.get(action);
        if (target == null) {
            throw new IllegalArgumentException("Action outside residual alphabet: " + action);
        }
        return target;
    }

    @Override
    public boolean isError(R state) {
        if (!states.contains(state)) {
            throw new IllegalArgumentException("Unknown residual state: " + state);
        }
        return errorStates.contains(state);
    }

    public Set<R> errorStates() {
        return errorStates;
    }

    private void validate() {
        if (initialState == null || !states.contains(initialState)) {
            throw new IllegalArgumentException("Residual initial state must belong to its state set");
        }
        if (!states.containsAll(errorStates)) {
            throw new IllegalArgumentException("Residual error states must belong to its state set");
        }
        for (R state : states) {
            Map<String, R> byAction = transitions.get(state);
            if (byAction == null || !byAction.keySet().equals(alphabet)) {
                throw new IllegalArgumentException(
                        "Residual automaton must be total over its alphabet at state " + state);
            }
            for (R target : byAction.values()) {
                if (!states.contains(target)) {
                    throw new IllegalArgumentException("Residual transition target is not a state: " + target);
                }
            }
        }
        for (R error : errorStates) {
            for (String action : alphabet) {
                if (!errorStates.contains(transitions.get(error).get(action))) {
                    throw new IllegalArgumentException(
                            "Residual error states must be absorbing: " + error + " --" + action + "-->");
                }
            }
        }
    }

    public static final class Builder<R> {
        private R initialState;
        private final Set<R> states = new LinkedHashSet<>();
        private final Set<String> alphabet = new LinkedHashSet<>();
        private final Set<R> errorStates = new LinkedHashSet<>();
        private final Map<R, Map<String, R>> transitions = new LinkedHashMap<>();

        public Builder<R> initialState(R state) {
            initialState = Objects.requireNonNull(state, "initialState");
            states.add(state);
            return this;
        }

        public Builder<R> addState(R state) {
            states.add(Objects.requireNonNull(state, "state"));
            return this;
        }

        public Builder<R> addStates(Collection<? extends R> values) {
            Objects.requireNonNull(values, "states");
            for (R state : values) {
                addState(state);
            }
            return this;
        }

        public Builder<R> addAction(String action) {
            Objects.requireNonNull(action, "action");
            if (action.trim().isEmpty()) {
                throw new IllegalArgumentException("Action must not be blank");
            }
            alphabet.add(action);
            return this;
        }

        public Builder<R> addActions(Collection<String> actions) {
            Objects.requireNonNull(actions, "actions");
            for (String action : actions) {
                addAction(action);
            }
            return this;
        }

        public Builder<R> addErrorState(R state) {
            state = Objects.requireNonNull(state, "errorState");
            states.add(state);
            errorStates.add(state);
            return this;
        }

        public Builder<R> addTransition(R source, String action, R target) {
            source = Objects.requireNonNull(source, "source");
            action = Objects.requireNonNull(action, "action");
            target = Objects.requireNonNull(target, "target");
            states.add(source);
            states.add(target);
            alphabet.add(action);
            R previous = transitions.computeIfAbsent(source, ignored -> new LinkedHashMap<>())
                    .putIfAbsent(action, target);
            if (previous != null && !previous.equals(target)) {
                throw new IllegalArgumentException(
                        "Residual automaton is nondeterministic at " + source + " on " + action);
            }
            return this;
        }

        public TableResidualLanguage<R> build() {
            Set<R> immutableStates = Collections.unmodifiableSet(new LinkedHashSet<>(states));
            Set<String> immutableAlphabet = Collections.unmodifiableSet(new LinkedHashSet<>(alphabet));
            Set<R> immutableErrors = Collections.unmodifiableSet(new LinkedHashSet<>(errorStates));
            Map<R, Map<String, R>> immutableTransitions = new LinkedHashMap<>();
            for (R state : states) {
                Map<String, R> byAction = transitions.get(state);
                immutableTransitions.put(state, Collections.unmodifiableMap(
                        byAction == null ? new LinkedHashMap<>() : new LinkedHashMap<>(byAction)));
            }
            return new TableResidualLanguage<>(
                    initialState,
                    immutableStates,
                    immutableAlphabet,
                    immutableErrors,
                    Collections.unmodifiableMap(immutableTransitions));
        }
    }
}
