package ltsa.updatingControllers.otf;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;

/** Canonical game key q=(physical state, active tester states, pending update actions). */
public final class CanonicalUpdateConfiguration<S, M> {
    private final PhysicalState<S> physicalState;
    private final Map<String, M> activeTesterStates;
    private final Set<String> pendingActions;

    private CanonicalUpdateConfiguration(
            PhysicalState<S> physicalState,
            Map<String, M> activeTesterStates,
            Set<String> pendingActions) {
        this.physicalState = Objects.requireNonNull(physicalState, "physicalState");
        Map<String, M> testerCopy = new LinkedHashMap<>();
        for (Map.Entry<String, M> entry
                : Objects.requireNonNull(activeTesterStates, "activeTesterStates").entrySet()) {
            testerCopy.put(
                    nonBlank(entry.getKey(), "requirement id"),
                    Objects.requireNonNull(entry.getValue(), "tester state"));
        }
        this.activeTesterStates = Collections.unmodifiableMap(testerCopy);

        Set<String> pendingCopy = new LinkedHashSet<>();
        for (String action : Objects.requireNonNull(pendingActions, "pendingActions")) {
            pendingCopy.add(nonBlank(action, "pending action"));
        }
        this.pendingActions = Collections.unmodifiableSet(pendingCopy);
    }

    public static <S, M> CanonicalUpdateConfiguration<S, M> of(
            PhysicalState<S> physicalState,
            Map<String, M> activeTesterStates,
            Set<String> pendingActions) {
        return new CanonicalUpdateConfiguration<>(physicalState, activeTesterStates, pendingActions);
    }

    public PhysicalState<S> physicalState() {
        return physicalState;
    }

    /** Contains active testers only; absence is the canonical BOT representation. */
    public Map<String, M> testerStatesByRequirementId() {
        return activeTesterStates;
    }

    public Map<String, M> activeTesterStates() {
        return activeTesterStates;
    }

    public Optional<M> testerState(String requirementId) {
        return Optional.ofNullable(activeTesterStates.get(requirementId));
    }

    public boolean isTesterActive(String requirementId) {
        return activeTesterStates.containsKey(requirementId);
    }

    public Set<String> pendingActions() {
        return pendingActions;
    }

    public boolean isPending(String action) {
        return pendingActions.contains(action);
    }

    @Override
    public boolean equals(Object other) {
        if (this == other) return true;
        if (!(other instanceof CanonicalUpdateConfiguration)) return false;
        CanonicalUpdateConfiguration<?, ?> that = (CanonicalUpdateConfiguration<?, ?>) other;
        return physicalState.equals(that.physicalState)
                && activeTesterStates.equals(that.activeTesterStates)
                && pendingActions.equals(that.pendingActions);
    }

    @Override
    public int hashCode() {
        return Objects.hash(physicalState, activeTesterStates, pendingActions);
    }

    @Override
    public String toString() {
        return "(" + physicalState + ", " + activeTesterStates + ", " + pendingActions + ")";
    }

    private static String nonBlank(String value, String label) {
        Objects.requireNonNull(value, label);
        if (value.trim().isEmpty()) {
            throw new IllegalArgumentException(label + " must not be blank");
        }
        return value;
    }
}
