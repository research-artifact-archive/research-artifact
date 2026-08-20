package ltsa.updatingControllers.otf;

import java.util.Collection;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.Objects;
import java.util.Set;

/** Immutable deterministic, total safety tester with absorbing error states. */
public final class SafetyTester<M> {
    private final FiniteLts<M> automaton;
    private final Set<M> errorStates;

    private SafetyTester(FiniteLts<M> automaton, Collection<? extends M> errorStates) {
        this.automaton = Objects.requireNonNull(automaton, "automaton");
        LinkedHashSet<M> errors = new LinkedHashSet<>();
        for (M state : Objects.requireNonNull(errorStates, "errorStates")) {
            errors.add(Objects.requireNonNull(state, "error state"));
        }
        this.errorStates = Collections.unmodifiableSet(errors);
        validate();
    }

    public static <M> SafetyTester<M> of(FiniteLts<M> automaton, Collection<? extends M> errorStates) {
        return new SafetyTester<>(automaton, errorStates);
    }

    public static <M> Builder<M> builder() {
        return new Builder<>();
    }

    public FiniteLts<M> automaton() {
        return automaton;
    }

    public Set<M> states() {
        return automaton.states();
    }

    public Set<String> alphabet() {
        return automaton.alphabet();
    }

    public M initialState() {
        return automaton.initialState();
    }

    public Set<M> errorStates() {
        return errorStates;
    }

    public boolean isError(M state) {
        if (!states().contains(state)) {
            throw new IllegalArgumentException("Unknown tester state: " + state);
        }
        return errorStates.contains(state);
    }

    public M step(M state, String action) {
        if (!alphabet().contains(action)) {
            throw new IllegalArgumentException("Action outside tester alphabet: " + action);
        }
        Set<M> successors = automaton.successors(state, action);
        if (successors.size() != 1) {
            throw new IllegalStateException("Validated tester lost determinism/totality");
        }
        return successors.iterator().next();
    }

    /**
     * Applies the tester-local transition when the action belongs to A_r and
     * otherwise implements the required stutter on the common alphabet.
     */
    public M stepOrStutter(M state, String action) {
        if (!states().contains(state)) {
            throw new IllegalArgumentException("Unknown tester state: " + state);
        }
        return alphabet().contains(action) ? step(state, action) : state;
    }

    private void validate() {
        if (!states().containsAll(errorStates)) {
            throw new IllegalArgumentException("Tester error states must belong to its state set");
        }
        if (errorStates.contains(initialState())) {
            throw new IllegalArgumentException("A safety tester must start outside its error set");
        }
        for (M state : states()) {
            for (String action : alphabet()) {
                Set<M> targets = automaton.successors(state, action);
                if (targets.size() != 1) {
                    throw new IllegalArgumentException(
                            "Safety tester must be deterministic and total at " + state + " on " + action);
                }
                if (errorStates.contains(state) && !errorStates.contains(targets.iterator().next())) {
                    throw new IllegalArgumentException(
                            "Safety tester error states must be absorbing at " + state + " on " + action);
                }
            }
        }
    }

    public static final class Builder<M> {
        private final FiniteLts.Builder<M> automaton = FiniteLts.builder();
        private final Set<M> errors = new LinkedHashSet<>();

        public Builder<M> initialState(M state) {
            automaton.initialState(state);
            return this;
        }

        public Builder<M> addState(M state) {
            automaton.addState(state);
            return this;
        }

        public Builder<M> addStates(Collection<? extends M> states) {
            automaton.addStates(states);
            return this;
        }

        public Builder<M> addAction(String action) {
            automaton.addAction(action);
            return this;
        }

        public Builder<M> addActions(Collection<String> actions) {
            automaton.addActions(actions);
            return this;
        }

        public Builder<M> addTransition(M source, String action, M target) {
            automaton.addTransition(source, action, target);
            return this;
        }

        public Builder<M> addErrorState(M state) {
            errors.add(Objects.requireNonNull(state, "errorState"));
            automaton.addState(state);
            return this;
        }

        public SafetyTester<M> build() {
            return SafetyTester.of(automaton.build(), errors);
        }
    }
}
