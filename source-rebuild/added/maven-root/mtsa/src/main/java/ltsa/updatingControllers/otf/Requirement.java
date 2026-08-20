package ltsa.updatingControllers.otf;

import java.util.Objects;
import java.util.Optional;

/** A role-tagged, independently instantiated safety requirement. */
public final class Requirement<S, M> {
    private final String id;
    private final RequirementRole role;
    private final SafetyTester<M> tester;
    private final ActivationSpec<S, M> activationSpec;
    private final String updateAction;

    private Requirement(
            String id,
            RequirementRole role,
            SafetyTester<M> tester,
            ActivationSpec<S, M> activationSpec,
            String updateAction) {
        this.id = nonBlank(id, "requirement id");
        this.role = Objects.requireNonNull(role, "role");
        this.tester = Objects.requireNonNull(tester, "tester");
        this.activationSpec = activationSpec;
        this.updateAction = updateAction;

        if (role == RequirementRole.OLD) {
            if (activationSpec != null) {
                throw new IllegalArgumentException("OLD requirements inherit endpoint state and have no activation spec");
            }
            nonBlank(updateAction, "old stop action");
        } else if (role == RequirementRole.NEW) {
            Objects.requireNonNull(activationSpec, "new requirement activationSpec");
            nonBlank(updateAction, "new start action");
        } else {
            Objects.requireNonNull(activationSpec, "update-time requirement activationSpec");
            if (updateAction != null) {
                throw new IllegalArgumentException("UPDATE_TIME requirements have no stop/start action");
            }
        }
    }

    public static <S, M> Requirement<S, M> oldRequirement(
            String id, SafetyTester<M> tester, String stopAction) {
        return new Requirement<>(id, RequirementRole.OLD, tester, null, stopAction);
    }

    public static <S, M> Requirement<S, M> newRequirement(
            String id, SafetyTester<M> tester, ActivationSpec<S, M> activationSpec, String startAction) {
        return new Requirement<>(id, RequirementRole.NEW, tester, activationSpec, startAction);
    }

    public static <S, M> Requirement<S, M> updateTimeRequirement(
            String id, SafetyTester<M> tester, ActivationSpec<S, M> activationSpec) {
        return new Requirement<>(id, RequirementRole.UPDATE_TIME, tester, activationSpec, null);
    }

    public String id() {
        return id;
    }

    public RequirementRole role() {
        return role;
    }

    public SafetyTester<M> tester() {
        return tester;
    }

    public Optional<ActivationSpec<S, M>> activationSpec() {
        return Optional.ofNullable(activationSpec);
    }

    public ActivationSpec<S, M> requiredActivationSpec() {
        if (activationSpec == null) {
            throw new IllegalStateException("OLD requirement has no activation spec: " + id);
        }
        return activationSpec;
    }

    public Optional<String> updateAction() {
        return Optional.ofNullable(updateAction);
    }

    public Optional<String> stopAction() {
        return role == RequirementRole.OLD ? Optional.of(updateAction) : Optional.empty();
    }

    public Optional<String> startAction() {
        return role == RequirementRole.NEW ? Optional.of(updateAction) : Optional.empty();
    }

    private static String nonBlank(String value, String label) {
        Objects.requireNonNull(value, label);
        if (value.trim().isEmpty()) {
            throw new IllegalArgumentException(label + " must not be blank");
        }
        return value;
    }
}
