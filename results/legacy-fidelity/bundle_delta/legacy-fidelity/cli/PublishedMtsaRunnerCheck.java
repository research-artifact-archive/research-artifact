package fidelity;
import ltsa.lts.LTSCompositionException;
/** Classification-only fixture; never compiles a model or invokes synthesis. */
public final class PublishedMtsaRunnerCheck {
    public static void main(String[] args) {
        if (!PublishedMtsaRunner.completedUnrealizable(new LTSCompositionException("Composition not controllable."),true)) throw new AssertionError("explicit GR loss");
        if (PublishedMtsaRunner.completedUnrealizable(new LTSCompositionException("Composition not controllable."),false)) throw new AssertionError("unexplained null/error");
        if (PublishedMtsaRunner.completedUnrealizable(new IllegalStateException("unexpected failure"),true)) throw new AssertionError("unrelated exception");
        if (PublishedMtsaRunner.completedUnrealizable(new OutOfMemoryError("fixture"),true)) throw new AssertionError("OOM is not LOSS");
        System.out.println("4 adapter classification assertions PASS; no synthesis invoked");
    }
}
