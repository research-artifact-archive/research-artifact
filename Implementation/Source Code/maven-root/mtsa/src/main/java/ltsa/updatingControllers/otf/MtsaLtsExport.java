package ltsa.updatingControllers.otf;

import MTSTools.ac.ic.doc.mtstools.model.MTS;
import MTSTools.ac.ic.doc.mtstools.model.impl.MTSImpl;
import ltsa.ac.ic.doc.mtstools.util.fsp.MTSToAutomataConverter;
import ltsa.lts.CompactState;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Objects;

/** MTSA-compatible numbered export of a generic {@link FiniteLts}. */
public final class MtsaLtsExport<S> {
    private final MTS<Long, String> mts;
    private final Map<S, Long> idByState;
    private final Map<Long, S> stateById;

    private MtsaLtsExport(
            MTS<Long, String> mts,
            Map<S, Long> idByState,
            Map<Long, S> stateById) {
        this.mts = mts;
        this.idByState = Collections.unmodifiableMap(new LinkedHashMap<S, Long>(idByState));
        this.stateById = Collections.unmodifiableMap(new LinkedHashMap<Long, S>(stateById));
    }

    static <S> MtsaLtsExport<S> from(FiniteLts<S> source) {
        Objects.requireNonNull(source, "source");
        Map<S, Long> ids = new LinkedHashMap<S, Long>();
        Map<Long, S> states = new LinkedHashMap<Long, S>();
        long next = 0L;
        ids.put(source.initialState(), Long.valueOf(next));
        states.put(Long.valueOf(next++), source.initialState());
        for (S state : source.states()) {
            if (!ids.containsKey(state)) {
                ids.put(state, Long.valueOf(next));
                states.put(Long.valueOf(next++), state);
            }
        }

        MTSImpl<Long, String> target = new MTSImpl<Long, String>(Long.valueOf(0L));
        target.addStates(states.keySet());
        target.addActions(source.alphabet());
        for (Map.Entry<S, Map<String, java.util.Set<S>>> stateEntry
                : source.transitions().entrySet()) {
            for (Map.Entry<String, java.util.Set<S>> actionEntry
                    : stateEntry.getValue().entrySet()) {
                for (S outcome : actionEntry.getValue()) {
                    target.addTransition(
                            ids.get(stateEntry.getKey()), actionEntry.getKey(), ids.get(outcome),
                            MTS.TransitionType.REQUIRED);
                }
            }
        }
        return new MtsaLtsExport<S>(target, ids, states);
    }

    public MTS<Long, String> mts() {
        return mts;
    }

    public Map<S, Long> idByState() {
        return idByState;
    }

    public Map<Long, S> stateById() {
        return stateById;
    }

    /** Converts the linked result into the representation used by the MTSA GUI. */
    public CompactState toCompactState(String name) {
        Objects.requireNonNull(name, "name");
        if (name.trim().isEmpty()) {
            throw new IllegalArgumentException("CompactState name must not be blank");
        }
        return MTSToAutomataConverter.getInstance().convert(mts, name, false, false);
    }
}
