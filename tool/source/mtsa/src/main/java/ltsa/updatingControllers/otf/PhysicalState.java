package ltsa.updatingControllers.otf;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.List;
import java.util.Objects;

/** Immutable vector of tagged local component states. */
public final class PhysicalState<S> {
    private final List<TaggedState<S>> components;

    private PhysicalState(Collection<? extends TaggedState<S>> components) {
        Objects.requireNonNull(components, "components");
        List<TaggedState<S>> copy = new ArrayList<>();
        for (TaggedState<S> component : components) {
            copy.add(Objects.requireNonNull(component, "component state"));
        }
        this.components = Collections.unmodifiableList(copy);
    }

    public static <S> PhysicalState<S> of(Collection<? extends TaggedState<S>> components) {
        return new PhysicalState<>(components);
    }

    @SafeVarargs
    public static <S> PhysicalState<S> of(TaggedState<S>... components) {
        List<TaggedState<S>> values = new ArrayList<>();
        Collections.addAll(values, components);
        return new PhysicalState<>(values);
    }

    public List<TaggedState<S>> components() {
        return components;
    }

    public TaggedState<S> component(int index) {
        return components.get(index);
    }

    public int size() {
        return components.size();
    }

    public boolean allOld() {
        for (TaggedState<S> component : components) {
            if (!component.isOld()) return false;
        }
        return true;
    }

    public boolean allNew() {
        for (TaggedState<S> component : components) {
            if (!component.isNew()) return false;
        }
        return true;
    }

    public PhysicalState<S> withComponent(int index, TaggedState<S> state) {
        List<TaggedState<S>> copy = new ArrayList<>(components);
        copy.set(index, Objects.requireNonNull(state, "state"));
        return new PhysicalState<>(copy);
    }

    @Override
    public boolean equals(Object other) {
        if (this == other) return true;
        if (!(other instanceof PhysicalState)) return false;
        PhysicalState<?> that = (PhysicalState<?>) other;
        return components.equals(that.components);
    }

    @Override
    public int hashCode() {
        return components.hashCode();
    }

    @Override
    public String toString() {
        return components.toString();
    }
}
