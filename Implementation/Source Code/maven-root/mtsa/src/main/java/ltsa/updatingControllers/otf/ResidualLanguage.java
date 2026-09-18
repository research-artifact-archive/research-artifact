package ltsa.updatingControllers.otf;

import java.util.Set;

/** Deterministic complete automaton for a residual bad-prefix language. */
public interface ResidualLanguage<R> {
    Set<R> states();
    Set<String> alphabet();
    R initialState();
    R step(R state, String action);
    boolean isError(R state);
}
