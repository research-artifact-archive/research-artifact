package ltsa.updatingControllers.otf;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.Comparator;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;

/**
 * A controller-side update discipline used for same-input capability
 * comparisons.
 *
 * <p>The restriction never removes an uncontrollable action and never changes
 * an action's successor set. It removes controllable choices and, for a
 * contiguous block, rejects a state from which an enabled uncontrollable event
 * would necessarily be able to interrupt that block. It therefore evaluates
 * an additional controller discipline over one fixed FG-DUCS plant and
 * requirement input. A winning strategy under a restriction is also a sound
 * strategy for the unrestricted game. Conversely, a losing restricted game
 * establishes only that the selected update discipline is insufficient; it
 * does not establish that the FG-DUCS input is unrealizable.</p>
 *
 * <p>{@code contiguous_transfer} does not aggregate the local transfer
 * relations into one global Cartesian-product action, and
 * {@code fixed_update_order} fixes only the order of update events while
 * leaving normal controllable choices state dependent. They must therefore
 * not be reported as the paper's global-transfer or observation-independent
 * fixed-script restrictions. {@code requirement_block}, by contrast, exactly
 * enforces a contiguous block using the pending requirement-event set; an
 * enabled uncontrollable event outside the block is an unavoidable block
 * violation.</p>
 */
public final class UpdatePolicyRestriction<S, M> {

    public static final String PROPERTY =
            "mtsa.revised.otf.policyRestriction";

    public enum Mode {
        FULL_FG("full_fg"),
        CONTIGUOUS_TRANSFER("contiguous_transfer"),
        CONTIGUOUS_UPDATE("contiguous_update"),
        FIXED_UPDATE_ORDER("fixed_update_order"),
        REQUIREMENT_BLOCK("requirement_block");

        private final String propertyValue;

        Mode(String propertyValue) {
            this.propertyValue = propertyValue;
        }

        public String propertyValue() {
            return propertyValue;
        }

        public static Mode configured() {
            return fromPropertyValue(System.getProperty(PROPERTY));
        }

        public static Mode fromPropertyValue(String configured) {
            String normalized = configured == null
                    ? FULL_FG.propertyValue
                    : configured.trim().toLowerCase(Locale.ROOT);
            if (normalized.isEmpty()) {
                normalized = FULL_FG.propertyValue;
            }
            if ("atomic_transfer".equals(normalized)) {
                normalized = CONTIGUOUS_TRANSFER.propertyValue;
            } else if ("atomic_requirements".equals(normalized)
                    || "contiguous_requirements".equals(normalized)) {
                normalized = REQUIREMENT_BLOCK.propertyValue;
            } else if ("all_coarse".equals(normalized)) {
                normalized = CONTIGUOUS_UPDATE.propertyValue;
            } else if ("fixed_sequence".equals(normalized)) {
                normalized = FIXED_UPDATE_ORDER.propertyValue;
            }
            for (Mode mode : values()) {
                if (mode.propertyValue.equals(normalized)) {
                    return mode;
                }
            }
            throw new IllegalArgumentException(
                    PROPERTY + " must be one of full_fg, "
                            + "contiguous_transfer, contiguous_update, "
                            + "fixed_update_order, or requirement_block, "
                            + "but was " + configured);
        }
    }

    private final FineGrainedUpdateProblem<S, M> problem;
    private final Mode mode;
    private final Set<String> transferActions;
    private final Set<String> requirementActions;
    private final List<String> fixedSequence;

    public UpdatePolicyRestriction(
            FineGrainedUpdateProblem<S, M> problem,
            Mode mode) {
        this.problem = Objects.requireNonNull(problem, "problem");
        this.mode = Objects.requireNonNull(mode, "mode");

        LinkedHashSet<String> transfers = new LinkedHashSet<String>();
        LinkedHashSet<String> requirements = new LinkedHashSet<String>();
        for (String action : problem.updateActions()) {
            Optional<UpdateEventKind> kind = problem.updateEventKind(action);
            if (!kind.isPresent()) {
                throw new IllegalArgumentException(
                        "Update action has no kind: " + action);
            }
            if (kind.get() == UpdateEventKind.RECONFIGURE) {
                transfers.add(action);
            } else {
                requirements.add(action);
            }
        }
        this.transferActions = Collections.unmodifiableSet(transfers);
        this.requirementActions = Collections.unmodifiableSet(requirements);
        this.fixedSequence = Collections.unmodifiableList(
                precedenceRespectingSequence(problem));
    }

    public static <S, M> UpdatePolicyRestriction<S, M> configured(
            FineGrainedUpdateProblem<S, M> problem) {
        return new UpdatePolicyRestriction<S, M>(
                problem, Mode.configured());
    }

    public Mode mode() {
        return mode;
    }

    boolean isForProblem(FineGrainedUpdateProblem<S, M> candidate) {
        return problem == candidate;
    }

    public String id() {
        return mode.propertyValue();
    }

    public List<String> fixedSequence() {
        return fixedSequence;
    }

    public Set<String> transferActions() {
        return transferActions;
    }

    public Set<String> requirementActions() {
        return requirementActions;
    }

    /**
     * Whether a candidate action remains available to the controller.
     * Uncontrollable actions are unconditionally preserved.
     */
    public boolean allows(
            CanonicalUpdateConfiguration<S, M> state,
            String action) {
        Objects.requireNonNull(state, "state");
        Objects.requireNonNull(action, "action");
        if (!problem.isStructurallyValid(state)) {
            throw new IllegalArgumentException(
                    "Non-canonical update configuration: " + state);
        }
        if (!problem.isControllable(action)) {
            return true;
        }
        switch (mode) {
            case FULL_FG:
                return true;
            case CONTIGUOUS_TRANSFER:
                return !isGroupInProgress(state, transferActions)
                        || transferActions.contains(action);
            case CONTIGUOUS_UPDATE:
                return !isGroupInProgress(state, problem.updateActions())
                        || problem.updateActions().contains(action);
            case FIXED_UPDATE_ORDER:
                return allowsFixedSequence(state, action);
            case REQUIREMENT_BLOCK:
                return !isGroupInProgress(state, requirementActions)
                        || requirementActions.contains(action);
            default:
                throw new IllegalStateException("Unhandled mode: " + mode);
        }
    }

    public List<String> filter(
            CanonicalUpdateConfiguration<S, M> state,
            Collection<String> candidates) {
        Objects.requireNonNull(candidates, "candidates");
        List<String> result = new ArrayList<String>();
        for (String action : candidates) {
            if (allows(state, action)) {
                result.add(action);
            }
        }
        return Collections.unmodifiableList(result);
    }

    /**
     * Static precondition under which an "atomic" label denotes a genuinely
     * contiguous block.  When uncontrollable normal events exist they must
     * remain enabled, so the comparison is conservatively a controller-choice
     * restriction and not an atomicity claim.
     */
    public boolean hasStaticUninterruptedBlockPrecondition() {
        if (!isContinuousBlockMode()) {
            return true;
        }
        return problem.normalActions().size()
                == problem.controllableNormalActions().size();
    }

    public boolean isContinuousBlockMode() {
        return mode == Mode.CONTIGUOUS_TRANSFER
                || mode == Mode.CONTIGUOUS_UPDATE
                || mode == Mode.REQUIREMENT_BLOCK;
    }

    public String interpretation() {
        switch (mode) {
            case FULL_FG:
                return "unrestricted_fine_grained_update_choices";
            case CONTIGUOUS_TRANSFER:
                return "no_controllable_interleaving_while_component_transfers_are_partial";
            case CONTIGUOUS_UPDATE:
                return "no_controllable_normal_interleaving_after_first_update_event";
            case FIXED_UPDATE_ORDER:
                return "one_precedence_respecting_total_order_for_update_events";
            case REQUIREMENT_BLOCK:
                return "no_interleaving_while_requirement_switches_are_partial";
            default:
                throw new IllegalStateException("Unhandled mode: " + mode);
        }
    }

    /**
     * True when {@code action} lies outside an active contiguous block. A
     * controllable such action is filtered by {@link #allows}; an enabled
     * uncontrollable such action makes the block discipline unrealizable and
     * is handled as an unavoidable violation by the restricted game.
     */
    public boolean isOutsideActiveBlock(
            CanonicalUpdateConfiguration<S, M> state,
            String action) {
        Objects.requireNonNull(state, "state");
        Objects.requireNonNull(action, "action");
        switch (mode) {
            case CONTIGUOUS_TRANSFER:
                return isGroupInProgress(state, transferActions)
                        && !transferActions.contains(action);
            case CONTIGUOUS_UPDATE:
                return isGroupInProgress(state, problem.updateActions())
                        && !problem.updateActions().contains(action);
            case REQUIREMENT_BLOCK:
                return isGroupInProgress(state, requirementActions)
                        && !requirementActions.contains(action);
            default:
                return false;
        }
    }

    private boolean allowsFixedSequence(
            CanonicalUpdateConfiguration<S, M> state,
            String action) {
        if (!problem.updateActions().contains(action)) {
            return true;
        }
        for (String next : fixedSequence) {
            if (state.pendingActions().contains(next)) {
                return next.equals(action);
            }
        }
        return false;
    }

    private static <S, M> boolean isGroupInProgress(
            CanonicalUpdateConfiguration<S, M> state,
            Set<String> group) {
        if (group.isEmpty()) {
            return false;
        }
        boolean pending = false;
        boolean completed = false;
        for (String action : group) {
            if (state.pendingActions().contains(action)) {
                pending = true;
            } else {
                completed = true;
            }
        }
        return pending && completed;
    }

    private static <S, M> List<String> precedenceRespectingSequence(
            FineGrainedUpdateProblem<S, M> problem) {
        LinkedHashSet<String> remaining =
                new LinkedHashSet<String>(problem.updateActions());
        List<String> result = new ArrayList<String>();
        Comparator<String> order = new Comparator<String>() {
            @Override
            public int compare(String left, String right) {
                int comparison = Integer.compare(
                        phase(problem, left), phase(problem, right));
                return comparison != 0
                        ? comparison
                        : left.compareTo(right);
            }
        };
        while (!remaining.isEmpty()) {
            List<String> eligible = new ArrayList<String>();
            for (String action : remaining) {
                if (Collections.disjoint(
                        problem.predecessors(action), remaining)) {
                    eligible.add(action);
                }
            }
            if (eligible.isEmpty()) {
                throw new IllegalArgumentException(
                        "Update precedence has no topological order");
            }
            Collections.sort(eligible, order);
            String selected = eligible.get(0);
            result.add(selected);
            remaining.remove(selected);
        }
        return result;
    }

    private static <S, M> int phase(
            FineGrainedUpdateProblem<S, M> problem,
            String action) {
        UpdateEventKind kind = problem.updateEventKind(action)
                .orElseThrow(() -> new IllegalArgumentException(
                        "Unknown update action: " + action));
        if (kind == UpdateEventKind.STOP_OLD_REQUIREMENT) {
            return 0;
        }
        if (kind == UpdateEventKind.RECONFIGURE) {
            return 1;
        }
        return 2;
    }
}
