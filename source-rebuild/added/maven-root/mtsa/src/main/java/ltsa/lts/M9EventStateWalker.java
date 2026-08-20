package ltsa.lts;

import java.util.ArrayList;
import java.util.Collections;
import java.util.IdentityHashMap;
import java.util.List;

/**
 * Field-level, fail-closed walker for the canonical EventState list/nondet
 * representation consumed by the prospective M9 materializer.
 */
public final class M9EventStateWalker {
	private static final int DEFAULT_MAX_EDGES = 10000000;

    private M9EventStateWalker() {
    }

    public static List<Edge> flattenExact(EventState head) {
		return flattenExact(head, DEFAULT_MAX_EDGES);
	}

	public static List<Edge> flattenExact(EventState head, int maxEdges) {
		if (maxEdges <= 0) {
			throw new IllegalArgumentException(
					"EventState edge budget must be positive.");
		}
        List<Edge> result = new ArrayList<Edge>();
        IdentityHashMap<EventState, Boolean> visited =
                new IdentityHashMap<EventState, Boolean>();
        EventState eventHead = head;
        int previousEvent = -1;
        while (eventHead != null) {
			if (visited.containsKey(eventHead)) {
				throw new IllegalArgumentException(
						"EventState graph contains an identity cycle or alias.");
			}
			if (eventHead.getClass() != EventState.class) {
                throw new IllegalArgumentException(
						"EventState subclass is outside the closed M9 runtime schema.");
            }
            if (eventHead.event <= previousEvent) {
                throw new IllegalArgumentException(
                        "EventState top-level event order is noncanonical.");
            }
            previousEvent = eventHead.event;
            EventState nondeterministic = eventHead;
            boolean first = true;
            while (nondeterministic != null) {
                if (visited.put(nondeterministic, Boolean.TRUE) != null) {
                    throw new IllegalArgumentException(
                            "EventState graph contains an identity cycle or alias.");
                }
				if (nondeterministic.getClass() != EventState.class) {
                    throw new IllegalArgumentException(
							"EventState subclass is outside the closed M9 runtime schema.");
                }
                if (nondeterministic.event != eventHead.event) {
                    throw new IllegalArgumentException(
                            "EventState nondeterministic chain changes action index.");
                }
                if (!first && nondeterministic.list != null) {
                    throw new IllegalArgumentException(
                            "EventState nondeterministic node hides a list branch.");
                }
				// EventState.path is native analyser scratch metadata, not part of
				// the list/nondet transition relation.  Native composition leaves it
				// populated, so the M9 authority deliberately ignores it.
				if (result.size() >= maxEdges) {
                    throw new IllegalArgumentException(
                            "EventState edge census exceeds the admission cap.");
                }
                result.add(new Edge(
                        nondeterministic.event, nondeterministic.next));
                nondeterministic = nondeterministic.nondet;
                first = false;
            }
            eventHead = eventHead.list;
        }
        return Collections.unmodifiableList(result);
    }

    public static final class Edge {
        private final int event;
        private final int target;

        private Edge(int event, int target) {
            this.event = event;
            this.target = target;
        }

        public int getEvent() { return event; }
        public int getTarget() { return target; }
    }
}
