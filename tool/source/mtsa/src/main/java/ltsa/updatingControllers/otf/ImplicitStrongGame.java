package ltsa.updatingControllers.otf;

import java.util.Collection;
import java.util.Comparator;
import java.util.Set;

/**
 * Read-only interface consumed by the revised OTF-DUCS strong-attractor
 * implementation.
 *
 * <p>An action is a controller choice, but every state returned by
 * {@link #post(Object, Object)} is an adversarial outcome of that action.  An
 * uncontrollable action is never removable.  Implementations must return all
 * outcomes, including unsafe ones.</p>
 */
public interface ImplicitStrongGame<Q, A, G> {

    /** All hotSwapIn embeddings.  OTF-DUCS succeeds only when every root wins. */
    Set<Q> initialStates();

    /** Whether all currently active safety testers are outside their errors. */
    boolean isSafe(Q state);

    /** Whether the state is a safe, fully updated, reachable new endpoint. */
    boolean isGoal(Q state);

    /**
     * Candidate normal and pending update actions.  Disabled candidates may be
     * returned; they are discarded when {@code post(state, action)} is empty.
     */
    Collection<A> candidateActions(Q state);

    /** The complete finite set of adversarial outcomes of one action. */
    Set<Q> post(Q state, A action);

    /** Update actions are controllable by definition; normal actions use input controllability. */
    boolean isControllable(A action);

    /** Used only for reproducible strategy and exploration tie-breaking. */
    boolean isUpdateAction(A action);

    /** Stable ordering within the normal/update action classes. */
    Comparator<A> actionComparator();

    /**
     * Secondary exploration hint used after
     * {@link #explorationActionPriority(Object, Object)}. Returning
     * {@code false} tries normal actions before update actions at this state;
     * no action is removed.
     */
    default boolean preferUpdateActions(Q state) {
        return true;
    }

    /**
     * Optional, state-dependent ordering hint for candidate exploration.
     * Smaller values are tried first. The hint never disables an action and
     * therefore does not change the exact winning region.
     */
    default int explorationActionPriority(Q state, A action) {
        return 0;
    }

    /** Stable ordering for multiple outcomes of one action. */
    Comparator<Q> stateComparator();

    /** The fixed endpoint state selected for the atomic Goal quotient. */
    G goalMatch(Q goalState);

    /** Checks the canonical (x, mu, P) invariants for independent certificates. */
    boolean isStructurallyValid(Q state);
}
