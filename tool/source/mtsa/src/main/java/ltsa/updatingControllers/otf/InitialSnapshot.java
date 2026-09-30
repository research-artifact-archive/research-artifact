package ltsa.updatingControllers.otf;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Objects;

/** Reachable old endpoint projection used to construct one member of Q0. */
public final class InitialSnapshot<S, M> {
    private final PhysicalState<S> physicalState;
    private final Map<String, M> oldRequirementStates;

    public InitialSnapshot(PhysicalState<S> physicalState, Map<String, M> oldRequirementStates) {
        this.physicalState = Objects.requireNonNull(physicalState, "physicalState");
        Map<String, M> copy = new LinkedHashMap<>();
        for (Map.Entry<String, M> entry
                : Objects.requireNonNull(oldRequirementStates, "oldRequirementStates").entrySet()) {
            String id = Objects.requireNonNull(entry.getKey(), "requirement id");
            if (id.trim().isEmpty()) {
                throw new IllegalArgumentException("Requirement id must not be blank");
            }
            copy.put(id, Objects.requireNonNull(entry.getValue(), "tester state"));
        }
        this.oldRequirementStates = Collections.unmodifiableMap(copy);
    }

    public PhysicalState<S> physicalState() {
        return physicalState;
    }

    public Map<String, M> oldRequirementStates() {
        return oldRequirementStates;
    }

    @Override
    public boolean equals(Object other) {
        if (this == other) return true;
        if (!(other instanceof InitialSnapshot)) return false;
        InitialSnapshot<?, ?> that = (InitialSnapshot<?, ?>) other;
        return physicalState.equals(that.physicalState)
                && oldRequirementStates.equals(that.oldRequirementStates);
    }

    @Override
    public int hashCode() {
        return Objects.hash(physicalState, oldRequirementStates);
    }

    @Override
    public String toString() {
        return physicalState + ":" + oldRequirementStates;
    }
}
