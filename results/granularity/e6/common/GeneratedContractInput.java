package ltsa.updatingControllers.otf;

/** Input-adapter bridge only: allow already-generated atomic groups without changing E1 semantics. */
public final class GeneratedContractInput {
    private GeneratedContractInput() { }
    public static <S,M> FineGrainedUpdateProblem.Builder<S,M> allowGroups(
            FineGrainedUpdateProblem.Builder<S,M> builder,String kind) {
        if(!kind.equals("transfers")&&!kind.equals("boundaries")&&!kind.equals("both"))
            throw new IllegalArgumentException("generated_contract_mode must be transfers, boundaries, or both");
        // This existing package-private E1 method only marks the builder's
        // already-merged input mode. Reachable endpoint enumeration follows.
        return builder.mergedContract("generated_"+kind,false);
    }
}
