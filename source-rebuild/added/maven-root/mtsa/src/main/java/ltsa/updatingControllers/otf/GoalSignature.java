package ltsa.updatingControllers.otf;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Objects;

/** Reachable new endpoint projection and stable identifier for atomic linking. */
public final class GoalSignature<S, M> implements Comparable<GoalSignature<S, M>> {
    private final String endpointId;
    private final PhysicalState<S> physicalState;
    private final Map<String, M> newRequirementStates;

    public GoalSignature(
            String endpointId,
            PhysicalState<S> physicalState,
            Map<String, M> newRequirementStates) {
        this.endpointId = Objects.requireNonNull(endpointId, "endpointId");
        if (endpointId.trim().isEmpty()) {
            throw new IllegalArgumentException("Endpoint id must not be blank");
        }
        this.physicalState = Objects.requireNonNull(physicalState, "physicalState");
        Map<String, M> copy = new LinkedHashMap<>();
        for (Map.Entry<String, M> entry
                : Objects.requireNonNull(newRequirementStates, "newRequirementStates").entrySet()) {
            copy.put(
                    Objects.requireNonNull(entry.getKey(), "requirement id"),
                    Objects.requireNonNull(entry.getValue(), "tester state"));
        }
        this.newRequirementStates = Collections.unmodifiableMap(copy);
    }

    public String endpointId() {
        return endpointId;
    }

    public PhysicalState<S> physicalState() {
        return physicalState;
    }

    public Map<String, M> newRequirementStates() {
        return newRequirementStates;
    }

    public boolean matches(CanonicalUpdateConfiguration<S, M> configuration) {
        if (!physicalState.equals(configuration.physicalState())) {
            return false;
        }
        for (Map.Entry<String, M> expected : newRequirementStates.entrySet()) {
            if (!expected.getValue().equals(configuration.activeTesterStates().get(expected.getKey()))) {
                return false;
            }
        }
        return true;
    }

    @Override
    public int compareTo(GoalSignature<S, M> other) {
        return endpointId.compareTo(other.endpointId);
    }

    @Override
    public boolean equals(Object other) {
        if (this == other) return true;
        if (!(other instanceof GoalSignature)) return false;
        GoalSignature<?, ?> that = (GoalSignature<?, ?>) other;
        return endpointId.equals(that.endpointId)
                && physicalState.equals(that.physicalState)
                && newRequirementStates.equals(that.newRequirementStates);
    }

    @Override
    public int hashCode() {
        return Objects.hash(endpointId, physicalState, newRequirementStates);
    }

    @Override
    public String toString() {
        return endpointId + ":" + physicalState + ":" + newRequirementStates;
    }
}
