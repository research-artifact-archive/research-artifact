package io.deephaven.engine.table.impl.remote;

/** Author study instrumentation; inactive without an explicitly installed observer. */
public final class RetryStudyHooks {
    private RetryStudyHooks() {}

    public interface Observer {
        void event(String stage, String kind, long a, long b, long c, long d);
    }

    public interface Scope extends AutoCloseable {
        @Override
        void close();
    }

    private static final ThreadLocal<Observer> OBSERVER = new ThreadLocal<>();
    private static final ThreadLocal<Binding> BINDING = new ThreadLocal<>();

    private static final class Binding {
        final String stage;
        final ConstructSnapshot.SnapshotControl control;
        boolean inBody;
        boolean protectedBody;

        Binding(String stage, ConstructSnapshot.SnapshotControl control) {
            this.stage = stage;
            this.control = control;
        }
    }

    public static void install(Observer observer) {
        if (OBSERVER.get() != null || BINDING.get() != null) {
            throw new IllegalStateException("Study observer already installed");
        }
        OBSERVER.set(observer);
    }

    public static void clear() {
        OBSERVER.remove();
        BINDING.remove();
    }

    public static Scope scope(String prefix, ConstructSnapshot.SnapshotControl control) {
        if (OBSERVER.get() == null ||
                !(prefix.equals("TreeTableImpl-keys") || prefix.equals("TreeTableImpl-source"))) {
            return () -> {};
        }
        final Binding previous = BINDING.get();
        if (previous != null) {
            throw new IllegalStateException("Nested target snapshot outside study scope");
        }
        final Binding binding = new Binding(prefix.endsWith("-keys") ? "K" : "V", control);
        BINDING.set(binding);
        emit(binding, "STAGE", 0, 0, 0, 0);
        return () -> BINDING.remove();
    }

    private static void emit(Binding binding, String kind, long a, long b, long c, long d) {
        final Observer observer = OBSERVER.get();
        if (observer != null) {
            observer.event(binding.stage, kind, a, b, c, d);
        }
    }

    public static boolean call(ConstructSnapshot.SnapshotControl control,
            ConstructSnapshot.SnapshotFunction function, boolean usePrev, long before, boolean protectedBody) {
        final Binding binding = BINDING.get();
        if (binding == null || binding.control != control) {
            return function.call(usePrev, before);
        }
        binding.inBody = true;
        binding.protectedBody = protectedBody;
        long returned = -1;
        try {
            emit(binding, "BEGIN", before, usePrev ? 1 : 0, protectedBody ? 1 : 0, 0);
            final boolean result = function.call(usePrev, before);
            returned = result ? 1 : 0;
            return result;
        } finally {
            emit(binding, "END", before, usePrev ? 1 : 0, protectedBody ? 1 : 0, returned);
            binding.inBody = false;
        }
    }

    public static void outcome(ConstructSnapshot.SnapshotControl control,
            long before, long after, boolean usePrev, boolean functionSuccessful, boolean consistent) {
        final Binding binding = BINDING.get();
        if (binding != null && binding.control == control) {
            emit(binding, "CHECK", before, after, usePrev ? 1 : 0,
                    (functionSuccessful ? 1 : 0) + (consistent ? 2 : 0));
        }
    }

    public static void work(String kind, long amount) {
        final Binding binding = BINDING.get();
        if (binding != null && binding.inBody) {
            emit(binding, kind, amount, binding.protectedBody ? 1 : 0, 0, 0);
        }
    }
}
