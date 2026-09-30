package ltsa.lts;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Objects;

/** Immutable parser-only endpoint descriptor; it contains no executable MTSA object. */
public final class M9UpdatingEndpointAst {
	private final boolean controllerSpecified;
	private final String controllerReference;
	private final boolean environmentSpecified;
	private final List<String> environmentReferences;
	private final boolean goalSpecified;
	private final String goalReference;
	private final M9ControllerGoalAst goal;

	M9UpdatingEndpointAst(
			boolean controllerSpecified,
			String controllerReference,
			boolean environmentSpecified,
			List<String> environmentReferences,
			boolean goalSpecified,
			String goalReference,
			M9ControllerGoalAst goal) {
		this.controllerSpecified = controllerSpecified;
		this.controllerReference = controllerSpecified
				? required(controllerReference, "endpoint controller") : null;
		this.environmentSpecified = environmentSpecified;
		this.environmentReferences = Collections.unmodifiableList(
				new ArrayList<String>(environmentReferences));
		if (environmentSpecified && this.environmentReferences.isEmpty()) {
			throw new IllegalArgumentException(
					"A specified endpoint environment is empty.");
		}
		this.goalSpecified = goalSpecified;
		this.goalReference = goalSpecified
				? required(goalReference, "endpoint goal") : null;
		this.goal = goalSpecified ? goal : null;
		if (goalSpecified && goal == null) {
			throw new IllegalArgumentException(
					"A specified endpoint goal has no descriptor.");
		}
	}

	private static String required(String value, String role) {
		if (value == null || value.isEmpty()) {
			throw new IllegalArgumentException(role + " is missing.");
		}
		return value;
	}

	public boolean isControllerSpecified() { return controllerSpecified; }
	public String getControllerReference() { return controllerReference; }
	public boolean isEnvironmentSpecified() { return environmentSpecified; }
	public List<String> getEnvironmentReferences() {
		return environmentReferences;
	}
	public boolean isGoalSpecified() { return goalSpecified; }
	public String getGoalReference() { return goalReference; }
	public M9ControllerGoalAst getGoal() { return goal; }

	@Override
	public boolean equals(Object candidate) {
		if (this == candidate) return true;
		if (!(candidate instanceof M9UpdatingEndpointAst)) return false;
		M9UpdatingEndpointAst other = (M9UpdatingEndpointAst) candidate;
		return controllerSpecified == other.controllerSpecified
				&& environmentSpecified == other.environmentSpecified
				&& goalSpecified == other.goalSpecified
				&& Objects.equals(controllerReference, other.controllerReference)
				&& environmentReferences.equals(other.environmentReferences)
				&& Objects.equals(goalReference, other.goalReference)
				&& Objects.equals(goal, other.goal);
	}

	@Override
	public int hashCode() {
		return Objects.hash(
				controllerSpecified, controllerReference,
				environmentSpecified, environmentReferences,
				goalSpecified, goalReference, goal);
	}
}
