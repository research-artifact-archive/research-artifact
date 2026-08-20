package ltsa.lts;

import ltsa.updatingControllers.structures.UpdatingControllerCompositeState;
import ltsa.lts.ltl.AssertDefinition;
import ltsa.lts.ltl.PredicateDefinition;

import java.util.Objects;

/**
 * Loads one ordinary updating-controller declaration without dispatching its
 * global update-game synthesis.  Parsing and composition remain under MTSA's
 * process-global parser lock; the returned value contains the compiled
 * component, endpoint, tester, observer, transfer, and protocol declarations.
 */
public final class NativeUpdatingContractLoader {

    private NativeUpdatingContractLoader() {
        // Utility class.
    }

    public static UpdatingControllerCompositeState load(
            String sourceText,
            String definitionName,
            String currentDirectory,
            LTSOutput output) {
        Objects.requireNonNull(sourceText, "sourceText");
        Objects.requireNonNull(definitionName, "definitionName");
        Objects.requireNonNull(currentDirectory, "currentDirectory");
        Objects.requireNonNull(output, "output");
        if (definitionName.trim().isEmpty()) {
            throw new IllegalArgumentException(
                    "updating-controller definition name must not be blank");
        }
        synchronized (LTSCompiler.m9ParseLock()) {
            LTSCompiler compiler = new LTSCompiler(
                    new LTSInputString(sourceText), output, currentDirectory);
            compiler.compile();
            ProgressDefinition.compile();
            MenuDefinition.compile();
            PredicateDefinition.compileAll();
            AssertDefinition.compileAll(output);
            CompositionExpression expression =
                    LTSCompiler.getComposite(definitionName);
            if (!(expression instanceof UpdatingControllersDefinition)) {
                throw new IllegalArgumentException(
                        "target is not an updatingController declaration: "
                                + definitionName);
            }
            CompositeState composed =
                    ((UpdatingControllersDefinition) expression).compose(null);
            if (!(composed instanceof UpdatingControllerCompositeState)) {
                throw new IllegalStateException(
                        "updatingController composition returned the wrong type");
            }
            UpdatingControllerCompositeState result =
                    (UpdatingControllerCompositeState) composed;
            if (!result.isRevisedOnTheFly() || !result.isFineGrained()
                    || !result.isOTF()) {
                throw new IllegalArgumentException(
                        "pre-flat factorization requires revised_on_the_fly, "
                                + "fine_grained input");
            }
            return result;
        }
    }
}
