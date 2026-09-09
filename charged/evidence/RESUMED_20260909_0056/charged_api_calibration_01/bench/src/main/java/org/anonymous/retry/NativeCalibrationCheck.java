package org.anonymous.retry;

/** Untimed semantic sanity checks; separate from all JMH samples. */
public final class NativeCalibrationCheck {
    private static void check(boolean condition) {
        if (!condition) { throw new AssertionError("calibration primitive mismatch"); }
    }
    private static void transformed(MyBenchmark.Value old, MyBenchmark.Value value) {
        check(value != old && value.data != old.data && value.data.length == old.data.length);
        int sum = 0;
        for (int i = 0; i < old.data.length; ++i) {
            int expected = 1664525 * old.data[i] + 1013904223;
            check(value.data[i] == expected);
            sum = 31 * sum + expected;
        }
        check(value.checksum == sum && value.version == old.version + 1);
    }
    public static void main(String[] args) {
        int cells = 0;
        for (String layout : new String[] {"distinct", "colliding"}) {
            for (int length : new int[] {1, 8, 64, 512}) {
                MyBenchmark benchmark = new MyBenchmark();
                benchmark.layout = layout; benchmark.length = length; benchmark.setup();
                MyBenchmark.Value original = benchmark.get();
                transformed(original, benchmark.prepare());
                check(benchmark.get() == original);
                check(benchmark.replaceMatch() && benchmark.get() != original);
                check(benchmark.replaceMatch() && benchmark.get() == original);
                check(!benchmark.replaceMismatch() && benchmark.get() == original);
                check(benchmark.validateCallbackMatch() != original);
                check(benchmark.validateCallbackMatch() == original);
                check(benchmark.validateCallbackMismatch() == original);
                check(benchmark.cachedCallbackMatch() != original);
                check(benchmark.cachedCallbackMatch() == original);
                MyBenchmark.Value cached = benchmark.cachedCallbackMismatch();
                transformed(original, cached);
                check(cached == benchmark.get());
                MyBenchmark.Value fresh = benchmark.freshCallback();
                check(fresh == benchmark.get()); transformed(cached, fresh);
                transformed(fresh, benchmark.freshCallback());
                ++cells;
            }
        }
        System.out.println("Untimed native semantics: " + cells + " states passed; no timing samples.");
    }
}
