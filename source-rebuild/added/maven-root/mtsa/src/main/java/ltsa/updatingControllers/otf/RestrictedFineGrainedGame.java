package ltsa.updatingControllers.otf;

import java.util.Collection;
import java.util.Collections;
import java.util.Comparator;
import java.util.Objects;
import java.util.Set;

/**
 * Same-state, same-successor game view with controller choices restricted by
 * an {@link UpdatePolicyRestriction}.
 */
public final class RestrictedFineGrainedGame<S, M>
        implements ImplicitStrongGame<CanonicalUpdateConfiguration<S, M>, String,
        GoalSignature<S, M>> {

    private final FineGrainedSuccessorOracle<S, M> delegate;
    private final UpdatePolicyRestriction<S, M> restriction;

    public RestrictedFineGrainedGame(
            FineGrainedSuccessorOracle<S, M> delegate,
            UpdatePolicyRestriction<S, M> restriction) {
        this.delegate = Objects.requireNonNull(delegate, "delegate");
        this.restriction = Objects.requireNonNull(
                restriction, "restriction");
    }

    public UpdatePolicyRestriction<S, M> restriction() {
        return restriction;
    }

    @Override
    public Set<CanonicalUpdateConfiguration<S, M>> initialStates() {
        return delegate.initialStates();
    }

    @Override
    public boolean isSafe(CanonicalUpdateConfiguration<S, M> state) {
        if (!delegate.isSafe(state)) {
            return false;
        }
        for (String action : delegate.candidateActions(state)) {
            if (!delegate.isControllable(action)
                    && restriction.isOutsideActiveBlock(state, action)
                    && !delegate.post(state, action).isEmpty()) {
                return false;
            }
        }
        return true;
    }

    @Override
    public boolean isGoal(CanonicalUpdateConfiguration<S, M> state) {
        return isSafe(state) && delegate.isGoal(state);
    }

    @Override
    public Collection<String> candidateActions(
            CanonicalUpdateConfiguration<S, M> state) {
        return restriction.filter(state, delegate.candidateActions(state));
    }

    @Override
    public Set<CanonicalUpdateConfiguration<S, M>> post(
            CanonicalUpdateConfiguration<S, M> state,
            String action) {
        if (!restriction.allows(state, action)) {
            return Collections.emptySet();
        }
        return delegate.post(state, action);
    }

    @Override
    public boolean isControllable(String action) {
        return delegate.isControllable(action);
    }

    @Override
    public boolean isUpdateAction(String action) {
        return delegate.isUpdateAction(action);
    }

    @Override
    public Comparator<String> actionComparator() {
        return delegate.actionComparator();
    }

    @Override
    public boolean preferUpdateActions(
            CanonicalUpdateConfiguration<S, M> state) {
        return delegate.preferUpdateActions(state);
    }

    @Override
    public int explorationActionPriority(
            CanonicalUpdateConfiguration<S, M> state,
            String action) {
        return delegate.explorationActionPriority(state, action);
    }

    @Override
    public Comparator<CanonicalUpdateConfiguration<S, M>> stateComparator() {
        return delegate.stateComparator();
    }

    @Override
    public GoalSignature<S, M> goalMatch(
            CanonicalUpdateConfiguration<S, M> goalState) {
        return delegate.goalMatch(goalState);
    }

    @Override
    public boolean isStructurallyValid(
            CanonicalUpdateConfiguration<S, M> state) {
        return delegate.isStructurallyValid(state);
    }
}
