package ltsa.updatingControllers.otf;

import java.util.ArrayDeque;
import java.util.Collections;
import java.util.Deque;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;

/**
 * Finite activation guard D, activation map iota, and its independently
 * supplied residual bad-prefix automaton.
 */
public final class ActivationSpec<S, M> {
    private final Map<PhysicalState<S>, M> activationByState;
    private final Map<PhysicalState<S>, Object> residualStateByState;
    private final ResidualLanguage<?> residualLanguage;
    private final ErasedResidual residual;

    private <R> ActivationSpec(
            Map<PhysicalState<S>, M> activations,
            Map<PhysicalState<S>, R> residualStates,
            ResidualLanguage<R> residualLanguage) {
        this.activationByState = immutableMap(activations);
        Map<PhysicalState<S>, Object> residualCopy = new LinkedHashMap<>();
        residualCopy.putAll(residualStates);
        this.residualStateByState = Collections.unmodifiableMap(residualCopy);
        this.residualLanguage = Objects.requireNonNull(residualLanguage, "residualLanguage");
        this.residual = new ResidualAdapter<>(residualLanguage);

        if (!activationByState.keySet().equals(residualStateByState.keySet())) {
            throw new IllegalArgumentException("Activation and residual-state domains must be identical");
        }
        for (Object residualState : residualStateByState.values()) {
            if (!residual.containsState(residualState)) {
                throw new IllegalArgumentException("Unknown residual state in activation table: " + residualState);
            }
        }
    }

    public static <S, M, R> Builder<S, M, R> builder(ResidualLanguage<R> residualLanguage) {
        return new Builder<>(residualLanguage);
    }

    public Set<PhysicalState<S>> domain() {
        return activationByState.keySet();
    }

    public boolean isDefinedAt(PhysicalState<S> physicalState) {
        return activationByState.containsKey(physicalState);
    }

    public M activate(PhysicalState<S> physicalState) {
        M result = activationByState.get(physicalState);
        if (result == null) {
            throw new IllegalArgumentException("Physical state is outside activation guard D: " + physicalState);
        }
        return result;
    }

    public Optional<M> activationAt(PhysicalState<S> physicalState) {
        return Optional.ofNullable(activationByState.get(physicalState));
    }

    public Map<PhysicalState<S>, M> activationMap() {
        return activationByState;
    }

    public ResidualLanguage<?> residualLanguage() {
        return residualLanguage;
    }

    public Optional<Object> residualStateAt(PhysicalState<S> physicalState) {
        return Optional.ofNullable(residualStateByState.get(physicalState));
    }

    /** Checks every activation entry against the tester by exact DFA language equivalence. */
    public void validateLanguageEquivalence(SafetyTester<M> tester) {
        Objects.requireNonNull(tester, "tester");
        if (!residual.alphabet().containsAll(tester.alphabet())) {
            throw new IllegalArgumentException(
                    "Tester alphabet is not a subset of the residual alphabet: tester=" + tester.alphabet()
                            + ", residual=" + residual.alphabet());
        }
        for (Map.Entry<PhysicalState<S>, M> activation : activationByState.entrySet()) {
            M testerState = activation.getValue();
            if (!tester.states().contains(testerState)) {
                throw new IllegalArgumentException(
                        "Activation points to an unknown tester state at " + activation.getKey());
            }
            if (tester.isError(testerState)) {
                throw new IllegalArgumentException(
                        "Activation must point to a non-error tester state at " + activation.getKey());
            }
            Object residualState = residualStateByState.get(activation.getKey());
            validateEquivalentFrom(activation.getKey(), tester, testerState, residualState);
        }
    }

    private void validateEquivalentFrom(
            PhysicalState<S> physicalState,
            SafetyTester<M> tester,
            M testerStart,
            Object residualStart) {
        Deque<StatePair<M>> queue = new ArrayDeque<>();
        Set<StatePair<M>> seen = new LinkedHashSet<>();
        StatePair<M> initial = new StatePair<>(testerStart, residualStart);
        queue.add(initial);
        seen.add(initial);

        while (!queue.isEmpty()) {
            StatePair<M> pair = queue.removeFirst();
            if (tester.isError(pair.testerState) != residual.isError(pair.residualState)) {
                throw new IllegalArgumentException(
                        "Activation residual language differs from tester language at " + physicalState
                                + " (tester=" + pair.testerState + ", residual=" + pair.residualState + ")");
            }
            for (String action : residual.alphabet()) {
                StatePair<M> next = new StatePair<>(
                        tester.stepOrStutter(pair.testerState, action),
                        residual.step(pair.residualState, action));
                if (seen.add(next)) {
                    queue.addLast(next);
                }
            }
        }
    }

    public static final class Builder<S, M, R> {
        private final ResidualLanguage<R> residualLanguage;
        private final Map<PhysicalState<S>, M> activations = new LinkedHashMap<>();
        private final Map<PhysicalState<S>, R> residualStates = new LinkedHashMap<>();

        private Builder(ResidualLanguage<R> residualLanguage) {
            this.residualLanguage = Objects.requireNonNull(residualLanguage, "residualLanguage");
        }

        public Builder<S, M, R> put(PhysicalState<S> physicalState, M testerState, R residualState) {
            physicalState = Objects.requireNonNull(physicalState, "physicalState");
            testerState = Objects.requireNonNull(testerState, "testerState");
            residualState = Objects.requireNonNull(residualState, "residualState");
            if (activations.containsKey(physicalState)) {
                throw new IllegalArgumentException("Duplicate activation entry: " + physicalState);
            }
            activations.put(physicalState, testerState);
            residualStates.put(physicalState, residualState);
            return this;
        }

        public ActivationSpec<S, M> build() {
            return new ActivationSpec<>(activations, residualStates, residualLanguage);
        }
    }

    private interface ErasedResidual {
        Set<String> alphabet();
        boolean containsState(Object state);
        Object step(Object state, String action);
        boolean isError(Object state);
    }

    private static final class ResidualAdapter<R> implements ErasedResidual {
        private final ResidualLanguage<R> delegate;

        private ResidualAdapter(ResidualLanguage<R> delegate) {
            this.delegate = delegate;
        }

        @Override
        public Set<String> alphabet() {
            return delegate.alphabet();
        }

        @Override
        public boolean containsState(Object state) {
            return delegate.states().contains(state);
        }

        @Override
        @SuppressWarnings("unchecked")
        public Object step(Object state, String action) {
            return delegate.step((R) state, action);
        }

        @Override
        @SuppressWarnings("unchecked")
        public boolean isError(Object state) {
            return delegate.isError((R) state);
        }
    }

    private static final class StatePair<M> {
        private final M testerState;
        private final Object residualState;

        private StatePair(M testerState, Object residualState) {
            this.testerState = testerState;
            this.residualState = residualState;
        }

        @Override
        public boolean equals(Object other) {
            if (this == other) return true;
            if (!(other instanceof StatePair)) return false;
            StatePair<?> that = (StatePair<?>) other;
            return testerState.equals(that.testerState) && residualState.equals(that.residualState);
        }

        @Override
        public int hashCode() {
            return Objects.hash(testerState, residualState);
        }
    }

    private static <K, V> Map<K, V> immutableMap(Map<K, V> values) {
        Map<K, V> copy = new LinkedHashMap<>();
        for (Map.Entry<K, V> entry : values.entrySet()) {
            copy.put(
                    Objects.requireNonNull(entry.getKey(), "map key"),
                    Objects.requireNonNull(entry.getValue(), "map value"));
        }
        return Collections.unmodifiableMap(copy);
    }
}
