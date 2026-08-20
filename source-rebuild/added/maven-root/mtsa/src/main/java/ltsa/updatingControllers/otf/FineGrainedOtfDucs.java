package ltsa.updatingControllers.otf;

import java.util.Objects;
import java.util.function.Function;

/**
 * Public entry point for the revised, proof-producing OTF-DUCS algorithm.
 *
 * <p>The returned strategy is checked against the successor oracle before it
 * is exposed. Thus both successful and unsuccessful results carry a
 * mechanically checked certificate for the exact input problem. Endpoint
 * projection functions and residual bad-prefix automata are specification
 * inputs; use {@link #synthesizeAndLink} to additionally check endpoint
 * transition consistency while materializing the complete Link.</p>
 */
public final class FineGrainedOtfDucs {

    private FineGrainedOtfDucs() {
        // Utility class.
    }

    public static <S, M> OtfDucsResult<CanonicalUpdateConfiguration<S, M>, String,
            GoalSignature<S, M>> synthesize(FineGrainedUpdateProblem<S, M> problem) {
        return synthesize(
                problem,
                FineGrainedSuccessorOracle.ControllableActionOrder.configured());
    }

    static <S, M> OtfDucsResult<CanonicalUpdateConfiguration<S, M>, String,
            GoalSignature<S, M>> synthesize(
                    FineGrainedUpdateProblem<S, M> problem,
                    FineGrainedSuccessorOracle.ControllableActionOrder actionOrder) {
        Objects.requireNonNull(problem, "problem");
        if (!problem.hasExhaustiveEndpointCoverage()) {
            throw new IllegalArgumentException(
                    "Certificate-producing synthesis requires initialSnapshotsFromReachable and "
                            + "goalSignaturesFromReachable; use synthesizeTrustedEndpointProjections "
                            + "only when externally supplied endpoint projections are known complete");
        }
        return synthesizeTrustedEndpointProjections(problem, actionOrder);
    }

    /**
     * Low-level entry point for callers that establish endpoint reachability
     * and completeness outside this implementation.
     */
    public static <S, M> OtfDucsResult<CanonicalUpdateConfiguration<S, M>, String,
            GoalSignature<S, M>> synthesizeTrustedEndpointProjections(
                    FineGrainedUpdateProblem<S, M> problem) {
        return synthesizeTrustedEndpointProjections(
                problem,
                FineGrainedSuccessorOracle.ControllableActionOrder.configured());
    }

    static <S, M> OtfDucsResult<CanonicalUpdateConfiguration<S, M>, String,
            GoalSignature<S, M>> synthesizeTrustedEndpointProjections(
                    FineGrainedUpdateProblem<S, M> problem,
                    FineGrainedSuccessorOracle.ControllableActionOrder actionOrder) {
        FineGrainedSuccessorOracle<S, M> game = game(problem, actionOrder);
        OtfDucsResult<CanonicalUpdateConfiguration<S, M>, String, GoalSignature<S, M>> result =
                new OtfDucsSynthesizer<CanonicalUpdateConfiguration<S, M>, String,
                        GoalSignature<S, M>>(game).synthesize();
        new OtfDucsCertificateChecker<CanonicalUpdateConfiguration<S, M>, String,
                GoalSignature<S, M>>(game).verify(result).throwIfInvalid();
        return result;
    }

    /** Exposes the exact implicit game for independent evaluation and checking. */
    public static <S, M> FineGrainedSuccessorOracle<S, M> game(
            FineGrainedUpdateProblem<S, M> problem) {
        return game(
                problem,
                FineGrainedSuccessorOracle.ControllableActionOrder.configured());
    }

    static <S, M> FineGrainedSuccessorOracle<S, M> game(
            FineGrainedUpdateProblem<S, M> problem,
            FineGrainedSuccessorOracle.ControllableActionOrder actionOrder) {
        return new FineGrainedSuccessorOracle<S, M>(
                Objects.requireNonNull(problem, "problem"),
                Objects.requireNonNull(actionOrder, "actionOrder"));
    }

    /** Independently rechecks a previously produced result against the input. */
    public static <S, M> OtfDucsCertificateChecker.VerificationReport verify(
            FineGrainedUpdateProblem<S, M> problem,
            OtfDucsResult<CanonicalUpdateConfiguration<S, M>, String,
                    GoalSignature<S, M>> result) {
        return new OtfDucsCertificateChecker<CanonicalUpdateConfiguration<S, M>, String,
                GoalSignature<S, M>>(game(problem)).verify(result);
    }

    /** Synthesizes and materializes the complete atomic pre/mid/post Link. */
    public static <ZO, S, M, ZN> LinkedOtfDucsController<ZO, S, M, ZN> synthesizeAndLink(
            FiniteLts<ZO> oldClosedLoop,
            FiniteLts<ZN> newClosedLoop,
            FineGrainedUpdateProblem<S, M> problem,
            Function<? super ZO, ? extends InitialSnapshot<S, M>> initialProjection,
            Function<? super ZN, ? extends GoalSignature<S, M>> goalProjection) {
        OtfDucsResult<CanonicalUpdateConfiguration<S, M>, String, GoalSignature<S, M>> result =
                synthesize(problem);
        if (!result.isWinning()) {
            throw new IllegalStateException(
                    "OTF-DUCS has no strong solution; inspect its losing certificate before linking");
        }
        return LinkedOtfDucsController.link(
                oldClosedLoop, newClosedLoop, problem, result,
                initialProjection, goalProjection);
    }
}
