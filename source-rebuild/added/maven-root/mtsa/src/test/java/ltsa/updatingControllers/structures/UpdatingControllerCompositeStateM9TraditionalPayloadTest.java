package ltsa.updatingControllers.structures;

import MTSSynthesis.controller.model.ControllerGoal;
import ltsa.control.ControllerGoalDefinition;
import ltsa.lts.CompactState;
import ltsa.lts.EventState;
import org.junit.Assert;
import org.testng.annotations.Test;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Vector;

public class UpdatingControllerCompositeStateM9TraditionalPayloadTest {
	@Test
	public void traditionalPayloadIsOwnedAndClonePreservesIt() {
		CompactState mapping = oneState("MAP");
		CompactState newEnvironment = oneState("NEW");
		Vector<CompactState> mappings = new Vector<CompactState>();
		mappings.add(mapping);
		Vector<CompactState> news = new Vector<CompactState>();
		news.add(newEnvironment);
		Map<Integer, Integer> row = new LinkedHashMap<Integer, Integer>();
		row.put(Integer.valueOf(0), Integer.valueOf(0));
		List<Map<Integer, Integer>> rows =
				new ArrayList<Map<Integer, Integer>>();
		rows.add(row);
		List<Boolean> markers = new ArrayList<Boolean>(
				Collections.singletonList(Boolean.FALSE));

		UpdatingControllerCompositeState state = traditionalPayload(
				mappings, rows, news, markers);
		mapping.name = "MUTATED_INPUT_MAP";
		mapping.alphabet[1] = "mutated";
		newEnvironment.name = "MUTATED_INPUT_NEW";
		row.put(Integer.valueOf(0), Integer.valueOf(9));
		markers.set(0, Boolean.TRUE);

		Assert.assertEquals("MAP",
				state.getM9TraditionalMappingComponents().get(0).getName());
		Assert.assertEquals("a",
				state.getM9TraditionalMappingComponents().get(0).alphabet[1]);
		Assert.assertEquals("NEW",
				state.getM9TraditionalNewEnvironmentComponents().get(0).getName());
		Assert.assertEquals(Collections.singletonMap(
				Integer.valueOf(0), Integer.valueOf(0)),
				state.getM9TraditionalMappingStateToNewState().get(0));
		Assert.assertEquals(Collections.singletonList(Boolean.FALSE),
				state.getM9TraditionalActionSequenceMarkers());

		Vector<CompactState> exposed =
				state.getM9TraditionalMappingComponents();
		exposed.get(0).name = "MUTATED_GETTER";
		Assert.assertEquals("MAP",
				state.getM9TraditionalMappingComponents().get(0).getName());
		try {
			state.getM9TraditionalMappingStateToNewState().get(0)
					.put(Integer.valueOf(7), Integer.valueOf(7));
			Assert.fail("Expected immutable local mapping row");
		} catch (UnsupportedOperationException expected) {
			// Expected.
		}
		List<Boolean> exposedMarkers =
				state.getM9TraditionalActionSequenceMarkers();
		exposedMarkers.set(0, Boolean.TRUE);
		Assert.assertEquals(Collections.singletonList(Boolean.FALSE),
				state.getM9TraditionalActionSequenceMarkers());

		UpdatingControllerCompositeState clone = state.clone();
		Assert.assertEquals(state.getM9TraditionalMappingStateToNewState(),
				clone.getM9TraditionalMappingStateToNewState());
		Assert.assertEquals(state.getM9TraditionalActionSequenceMarkers(),
				clone.getM9TraditionalActionSequenceMarkers());
		Assert.assertEquals("MAP",
				clone.getM9TraditionalMappingComponents().get(0).getName());
		Assert.assertEquals("NEW",
				clone.getM9TraditionalNewEnvironmentComponents().get(0).getName());
	}

	private static UpdatingControllerCompositeState traditionalPayload(
			List<CompactState> mappings,
			List<Map<Integer, Integer>> rows,
			List<CompactState> news,
			List<Boolean> markers) {
		return new UpdatingControllerCompositeState(
				null, null,
				new ControllerGoalDefinition("SYNTHETIC_SAFETY"),
				new ControllerGoal<String>(),
				"SYNTHETIC_PAYLOAD", false, null,
				mappings, rows, news, markers);
	}

	private static CompactState oneState(String name) {
		CompactState state = new CompactState(name);
		state.maxStates = 1;
		state.alphabet = new String[]{"tau", "a"};
		state.states = new EventState[1];
		state.states[0] = new EventState(1, 0);
		return state;
	}
}
