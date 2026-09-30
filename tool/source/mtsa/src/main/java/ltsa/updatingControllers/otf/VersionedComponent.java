package ltsa.updatingControllers.otf;

import java.util.Collection;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

/** Old/new component pair and its finite, possibly partial/nondeterministic transfer relation. */
public final class VersionedComponent<S> {
    private final String id;
    private final FiniteLts<S> oldLts;
    private final FiniteLts<S> newLts;
    private final Set<String> oldEnvironmentActions;
    private final Set<String> newEnvironmentActions;
    private final Map<S, Set<S>> transferRelation;
    private final String reconfigureAction;

    public VersionedComponent(
            String id,
            FiniteLts<S> oldLts,
            FiniteLts<S> newLts,
            Map<S, ? extends Collection<? extends S>> transferRelation,
            String reconfigureAction) {
        this(id, oldLts, newLts, transferRelation, reconfigureAction,
                oldLts == null ? null : oldLts.alphabet(),
                newLts == null ? null : newLts.alphabet());
    }

    /**
     * Creates a component whose state LTS may contain additional observer
     * transitions without letting those transitions enable environment events.
     *
     * <p>The two environment-action sets are the alphabets of the unaugmented
     * physical components.  The LTS alphabets may be larger when a finite
     * history observer is stored in this component.  Such observer-only
     * transitions are taken when another active physical component enables the
     * event, but they never enable the event by themselves.</p>
     */
    public VersionedComponent(
            String id,
            FiniteLts<S> oldLts,
            FiniteLts<S> newLts,
            Map<S, ? extends Collection<? extends S>> transferRelation,
            String reconfigureAction,
            Collection<String> oldEnvironmentActions,
            Collection<String> newEnvironmentActions) {
        this.id = nonBlank(id, "component id");
        this.oldLts = Objects.requireNonNull(oldLts, "oldLts");
        this.newLts = Objects.requireNonNull(newLts, "newLts");
        this.reconfigureAction = nonBlank(reconfigureAction, "reconfigureAction");
        this.oldEnvironmentActions = checkedEnvironmentActions(
                oldEnvironmentActions, oldLts, "old");
        this.newEnvironmentActions = checkedEnvironmentActions(
                newEnvironmentActions, newLts, "new");

        Map<S, Set<S>> copy = new LinkedHashMap<>();
        for (Map.Entry<S, ? extends Collection<? extends S>> entry
                : Objects.requireNonNull(transferRelation, "transferRelation").entrySet()) {
            S oldState = Objects.requireNonNull(entry.getKey(), "old transfer state");
            if (!oldLts.states().contains(oldState)) {
                throw new IllegalArgumentException("Transfer source is not an old state: " + oldState);
            }
            LinkedHashSet<S> targets = new LinkedHashSet<>();
            for (S newState : Objects.requireNonNull(entry.getValue(), "transfer targets")) {
                newState = Objects.requireNonNull(newState, "new transfer state");
                if (!newLts.states().contains(newState)) {
                    throw new IllegalArgumentException("Transfer target is not a new state: " + newState);
                }
                targets.add(newState);
            }
            copy.put(oldState, Collections.unmodifiableSet(targets));
        }
        this.transferRelation = Collections.unmodifiableMap(copy);
    }

    public String id() {
        return id;
    }

    public FiniteLts<S> oldLts() {
        return oldLts;
    }

    public FiniteLts<S> newLts() {
        return newLts;
    }

    public Set<String> oldEnvironmentActions() {
        return oldEnvironmentActions;
    }

    public Set<String> newEnvironmentActions() {
        return newEnvironmentActions;
    }

    public Set<String> environmentActions(ComponentVersion version) {
        Objects.requireNonNull(version, "version");
        return version == ComponentVersion.OLD
                ? oldEnvironmentActions : newEnvironmentActions;
    }

    public boolean environmentHasAction(ComponentVersion version, String action) {
        return action != null && environmentActions(version).contains(action);
    }

    public String reconfigureAction() {
        return reconfigureAction;
    }

    /** Returns every adversarial transfer outcome; an empty set means disabled. */
    public Set<S> transferFrom(S oldState) {
        if (!oldLts.states().contains(oldState)) {
            throw new IllegalArgumentException("Unknown old component state: " + oldState);
        }
        Set<S> result = transferRelation.get(oldState);
        return result == null ? Collections.emptySet() : result;
    }

    public Map<S, Set<S>> transferRelation() {
        return transferRelation;
    }

    private static <S> Set<String> checkedEnvironmentActions(
            Collection<String> actions,
            FiniteLts<S> stateLts,
            String version) {
        Objects.requireNonNull(actions, version + "EnvironmentActions");
        LinkedHashSet<String> copy = new LinkedHashSet<>();
        for (String action : actions) {
            copy.add(nonBlank(action, version + " environment action"));
        }
        if (!stateLts.alphabet().containsAll(copy)) {
            LinkedHashSet<String> missing = new LinkedHashSet<>(copy);
            missing.removeAll(stateLts.alphabet());
            throw new IllegalArgumentException(
                    version + " environment actions have no state-LTS transition alphabet: "
                            + missing);
        }
        return Collections.unmodifiableSet(copy);
    }

    private static String nonBlank(String value, String label) {
        Objects.requireNonNull(value, label);
        if (value.trim().isEmpty()) {
            throw new IllegalArgumentException(label + " must not be blank");
        }
        return value;
    }
}
