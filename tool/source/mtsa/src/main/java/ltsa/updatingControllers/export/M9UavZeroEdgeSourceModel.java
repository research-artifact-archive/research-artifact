package ltsa.updatingControllers.export;

import ltsa.updatingControllers.synthesis.UpdatingEnvironmentGenerator;

import java.io.IOException;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/**
 * Canonical, solver-free source model for the synthetic UAV zero-edge
 * successor fixture.  Every graph and handoff row is read from the immutable
 * native snapshots captured by the same fresh-JVM endpoint invocation.  This
 * writer has no campaign, attempt, TSA, decision, or publication API.
 */
final class M9UavZeroEdgeSourceModel {
	private static final String SCHEMA =
			"fse2027-m9-uav-zero-edge-source-model-v4";
	private static final String PROFILE =
			"ONE_STATE_TRADITIONAL_ZERO_EDGE_FIXTURE_V1";

	private M9UavZeroEdgeSourceModel() { }

	static void write(
			String sourceSha256,
			M9EndpointStrategySnapshot strategy,
			M9ClosedLoopEndpointSnapshot closedLoop,
			TraditionalPreGrSnapshot traditional,
			M9TraditionalCompletionHandoffSnapshot handoff,
			OutputStream destination) throws IOException {
		if (sourceSha256 == null
				|| !sourceSha256.matches("[0-9a-f]{64}")
				|| strategy == null || closedLoop == null
				|| traditional == null || handoff == null
				|| destination == null) {
			throw new IllegalArgumentException(
					"UAV zero-edge source-model inputs are incomplete.");
		}
		Map<String, Object> model = object();
		model.put("schema_version", SCHEMA);
		model.put("profile", PROFILE);
		model.put("source_sha256", sourceSha256);
		model.put("controllable_actions", strings(
				traditional.getControllableActions()));
		model.put("unsafe_state_ids", longs(
				traditional.getProvenanceFreeUnsafeStates()));

		Map<String, Object> boundary = object();
		boundary.put("request_action", "hotSwapIn");
		boundary.put("completion_boundary_name", "hotSwapOut");
		boundary.put("completion_semantics", "ZERO_EDGE_ATOMIC_QUOTIENT");
		boundary.put("materialized_event", Boolean.FALSE);
		boundary.put("synthetic_transition_count", Long.valueOf(0L));
		boundary.put("derived_edge_count", Long.valueOf(0L));
		model.put("boundary", boundary);

		Map<String, Object> lifecycle = object();
		lifecycle.put("actions", new ArrayList<String>(
				traditional.getSafetySemantics().getLifecycleActions()));
		lifecycle.put("complete_coordinate", Long.valueOf(
				handoff.getLifecycleCompleteCoordinate()));
		lifecycle.put("goal_states", longs(
				handoff.getCompletionStates().keySet()));
		model.put("lifecycle", lifecycle);

		model.put("transfer_rows", transferRows(traditional));
		model.put("safety_graph", graph(traditional.getSafetyEnvironment()));
		model.put("updating_graph", graph(
				traditional.getUpdatingEnvironment()));
		model.put("completion_handoff", completionRows(handoff));
		model.put("post_load_graph", graph(
				closedLoop.getClosedLoopAuthority().getProductSnapshot()));

		Map<String, Object> claim = object();
		claim.put("fixture_only", Boolean.TRUE);
		claim.put("decision_status", "NOT_RUN");
		claim.put("endpoint_gr_invocations", Long.valueOf(1L));
		claim.put("updater_gr_invocations", Long.valueOf(0L));
		claim.put("selected_fg_solver_invocations", Long.valueOf(0L));
		claim.put("game_fixed_point_invocations", Long.valueOf(0L));
		claim.put("formal_kappa", new ArrayList<Object>());
		claim.put("operational_load_claim", Boolean.FALSE);
		model.put("claim_boundary", claim);

		StringBuilder encoded = new StringBuilder(8192);
		json(model, encoded);
		encoded.append('\n');
		destination.write(encoded.toString().getBytes(StandardCharsets.UTF_8));
	}

	private static List<Object> transferRows(
			TraditionalPreGrSnapshot traditional) {
		List<UpdatingEnvironmentGenerator.BeginUpdateRow> source =
				new ArrayList<UpdatingEnvironmentGenerator.BeginUpdateRow>(
						traditional.getUpdatingProvenance().getBeginUpdateRows());
		Collections.sort(source,
				new Comparator<UpdatingEnvironmentGenerator.BeginUpdateRow>() {
					@Override
					public int compare(
							UpdatingEnvironmentGenerator.BeginUpdateRow left,
							UpdatingEnvironmentGenerator.BeginUpdateRow right) {
						int order = left.getOldControllerState().compareTo(
								right.getOldControllerState());
						if (order != 0) return order;
						order = left.getMappingState().compareTo(
								right.getMappingState());
						return order != 0 ? order : left.getUpdatingState().compareTo(
								right.getUpdatingState());
					}
				});
		List<Object> result = new ArrayList<Object>(source.size());
		for (UpdatingEnvironmentGenerator.BeginUpdateRow row : source) {
			Map<String, Object> value = object();
			value.put("old_state", row.getOldControllerState());
			value.put("mapping_state", row.getMappingState());
			value.put("updating_state", row.getUpdatingState());
			result.add(value);
		}
		return result;
	}

	private static Map<String, Object> graph(M9MtsSnapshot snapshot) {
		Map<String, Object> result = object();
		result.put("initial_state", Long.valueOf(snapshot.getInitialState()));
		result.put("states", longs(snapshot.getStates()));
		result.put("actions", strings(snapshot.getActions()));
		List<Object> buckets = new ArrayList<Object>();
		for (Long state : sortedLongs(snapshot.getStates())) {
			Map<String, java.util.Set<Long>> row = snapshot.getPost().get(state);
			if (row == null) {
				throw new IllegalArgumentException(
						"UAV source-model MTS row is absent.");
			}
			List<String> actions = new ArrayList<String>(row.keySet());
			Collections.sort(actions);
			for (String action : actions) {
				Map<String, Object> bucket = object();
				bucket.put("source", state);
				bucket.put("action", action);
				bucket.put("targets", longs(row.get(action)));
				buckets.add(bucket);
			}
		}
		result.put("buckets", buckets);
		return result;
	}

	private static List<Object> completionRows(
			M9TraditionalCompletionHandoffSnapshot handoff) {
		List<Object> result = new ArrayList<Object>();
		for (Long safety : sortedLongs(handoff.getCompletionStates().keySet())) {
			List<M9TraditionalCompletionHandoffSnapshot.CompletionCoordinates> rows =
					new ArrayList<M9TraditionalCompletionHandoffSnapshot.CompletionCoordinates>(
							handoff.getCompletionStates().get(safety));
			Collections.sort(rows,
					new Comparator<M9TraditionalCompletionHandoffSnapshot.CompletionCoordinates>() {
						@Override
					public int compare(
							M9TraditionalCompletionHandoffSnapshot.CompletionCoordinates left,
							M9TraditionalCompletionHandoffSnapshot.CompletionCoordinates right) {
						int order = Long.compare(
								left.getCnewState(), right.getCnewState());
						if (order != 0) return order;
						order = Long.compare(
								left.getClosedLoopState(), right.getClosedLoopState());
						if (order != 0) return order;
						order = Long.compare(left.getPrunedState(), right.getPrunedState());
						if (order != 0) return order;
						order = Long.compare(left.getMetaState(), right.getMetaState());
						if (order != 0) return order;
						order = Long.compare(
								left.getUpdatingState(), right.getUpdatingState());
						if (order != 0) return order;
						order = Long.compare(left.getMappingState(), right.getMappingState());
						if (order != 0) return order;
						order = Long.compare(left.getEnewState(), right.getEnewState());
						if (order != 0) return order;
						return Long.compare(
								left.getSolverEnvironmentState(),
								right.getSolverEnvironmentState());
					}
				});
			for (M9TraditionalCompletionHandoffSnapshot.CompletionCoordinates row
					: rows) {
				Map<String, Object> value = object();
				value.put("safety_state", safety);
				value.put("pruned_state", Long.valueOf(row.getPrunedState()));
				value.put("meta_state", Long.valueOf(row.getMetaState()));
				value.put("updating_state", Long.valueOf(row.getUpdatingState()));
				value.put("mapping_state", Long.valueOf(row.getMappingState()));
				value.put("enew_state", Long.valueOf(row.getEnewState()));
				value.put("solver_environment_state", Long.valueOf(
						row.getSolverEnvironmentState()));
				value.put("cnew_state", Long.valueOf(row.getCnewState()));
				value.put("closed_loop_state", Long.valueOf(
						row.getClosedLoopState()));
				result.add(value);
			}
		}
		return result;
	}

	private static Map<String, Object> object() {
		return new LinkedHashMap<String, Object>();
	}

	private static List<Long> sortedLongs(Collection<Long> values) {
		List<Long> result = new ArrayList<Long>(values);
		Collections.sort(result);
		return result;
	}

	private static List<Object> longs(Collection<Long> values) {
		return new ArrayList<Object>(sortedLongs(values));
	}

	private static List<Object> strings(Collection<String> values) {
		List<String> sorted = new ArrayList<String>(values);
		Collections.sort(sorted);
		return new ArrayList<Object>(sorted);
	}

	private static void json(Object value, StringBuilder output) {
		if (value == null) {
			output.append("null");
		} else if (value instanceof Boolean || value instanceof Number) {
			output.append(value.toString());
		} else if (value instanceof String) {
			quoted((String) value, output);
		} else if (value instanceof List<?>) {
			output.append('[');
			List<?> list = (List<?>) value;
			for (int index = 0; index < list.size(); index++) {
				if (index != 0) output.append(',');
				json(list.get(index), output);
			}
			output.append(']');
		} else if (value instanceof Map<?, ?>) {
			Map<String, Object> sorted = new TreeMap<String, Object>();
			for (Map.Entry<?, ?> entry : ((Map<?, ?>) value).entrySet()) {
				if (!(entry.getKey() instanceof String)) {
					throw new IllegalArgumentException(
							"UAV source-model JSON key is not a string.");
				}
				sorted.put((String) entry.getKey(), entry.getValue());
			}
			output.append('{');
			boolean first = true;
			for (Map.Entry<String, Object> entry : sorted.entrySet()) {
				if (!first) output.append(',');
				first = false;
				quoted(entry.getKey(), output);
				output.append(':');
				json(entry.getValue(), output);
			}
			output.append('}');
		} else {
			throw new IllegalArgumentException(
					"UAV source-model contains an unsupported JSON value.");
		}
	}

	private static void quoted(String value, StringBuilder output) {
		output.append('"');
		for (int index = 0; index < value.length(); index++) {
			char character = value.charAt(index);
			switch (character) {
			case '"': output.append("\\\""); break;
			case '\\': output.append("\\\\"); break;
			case '\b': output.append("\\b"); break;
			case '\f': output.append("\\f"); break;
			case '\n': output.append("\\n"); break;
			case '\r': output.append("\\r"); break;
			case '\t': output.append("\\t"); break;
			default:
				if (character < 0x20) {
					output.append(String.format("\\u%04x", Integer.valueOf(character)));
				} else {
					output.append(character);
				}
			}
		}
		output.append('"');
	}
}
