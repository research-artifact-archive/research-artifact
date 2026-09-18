package ltsa.updatingControllers.otf;

import java.util.Objects;

/** Local component state tagged with the active component version. */
public final class TaggedState<S> {
    private final ComponentVersion version;
    private final S state;

    private TaggedState(ComponentVersion version, S state) {
        this.version = Objects.requireNonNull(version, "version");
        this.state = Objects.requireNonNull(state, "state");
    }

    public static <S> TaggedState<S> oldState(S state) {
        return new TaggedState<>(ComponentVersion.OLD, state);
    }

    public static <S> TaggedState<S> newState(S state) {
        return new TaggedState<>(ComponentVersion.NEW, state);
    }

    public static <S> TaggedState<S> of(ComponentVersion version, S state) {
        return new TaggedState<>(version, state);
    }

    public ComponentVersion version() {
        return version;
    }

    public S state() {
        return state;
    }

    public boolean isOld() {
        return version == ComponentVersion.OLD;
    }

    public boolean isNew() {
        return version == ComponentVersion.NEW;
    }

    @Override
    public boolean equals(Object other) {
        if (this == other) return true;
        if (!(other instanceof TaggedState)) return false;
        TaggedState<?> that = (TaggedState<?>) other;
        return version == that.version && state.equals(that.state);
    }

    @Override
    public int hashCode() {
        return Objects.hash(version, state);
    }

    @Override
    public String toString() {
        return version + "(" + state + ")";
    }
}
