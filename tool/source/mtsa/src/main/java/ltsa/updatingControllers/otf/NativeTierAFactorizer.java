package ltsa.updatingControllers.otf;

import MTSTools.ac.ic.doc.mtstools.model.MTS;
import MTSTools.ac.ic.doc.mtstools.model.impl.LTSAdapter;
import ltsa.lts.CompactState;
import ltsa.updatingControllers.UpdateConstants;
import ltsa.updatingControllers.structures.UpdateProtocolSpec;
import ltsa.updatingControllers.structures.UpdatingControllerCompositeState;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.Comparator;
import java.util.Deque;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.Vector;

/**
 * Tier-A decomposition of a parsed updating-controller contract before a
 * mixed-version global update game is constructed.
 *
 * <p>The implementation is deliberately conservative.  Every ordinary event,
 * safety tester, activation observer, transition requirement, and precedence
 * edge contributes a source-derived dependency.  A nontrivial result is
 * returned only after each projected local FG-DUCS problem has been built and
 * checked.  The full new endpoint is compiled solely to enumerate the
 * declared load domain; no global mixed update state or successor bucket is
 * generated.</p>
 */
public final class NativeTierAFactorizer {

    private NativeTierAFactorizer() {
        // Utility class.
    }

    private static final int MAX_BLOCK_OBSERVER_RELATION_STATES =
            Integer.getInteger(
                    "mtsa.revised.otf.maxBlockObserverRelationStates",
                    1000000).intValue();

        public static Result factor(UpdatingControllerCompositeState source) {
        Objects.requireNonNull(source, "source");
        StructuralInput input = StructuralInput.compile(source);
        Partition partition = input.dependencies();
        if (partition.blocks.size() <= 1) {
            input.validateExtractionOnly();
            return Result.trivial(input, partition);
        }
        List<LocalResult> locals = new ArrayList<LocalResult>();
        for (int index = 0; index < partition.blocks.size(); index++) {
            locals.add(input.solveBlock(index, partition.blocks.get(index)));
        }
        boolean allWinning = true;
        for (LocalResult local : locals) {
            allWinning &= local.result.isWinning();
        }
        boolean terminalProduct = input.quietProductContained(locals);
        TransportReport transport = input.verifyTransport(locals);
        boolean transportVerified = transport.isVerified();
        return new Result(
                allWinning && terminalProduct && transportVerified
                        ? "PRODUCER_VERIFIED_REFINED_WIN" : "INCONCLUSIVE",
                "NONTRIVIAL_SOURCE_NATIVE",
                partition,
                input.receipts,
                locals,
                input.oldEndpoint.reachableStates().size(),
                input.newEndpoint.reachableStates().size(),
                terminalProduct && transportVerified,
                transport);
    }

    public static final class Result {
        private final String solveStatus;
        private final String factorStatus;
        private final Partition partition;
        private final List<DependencyReceipt> receipts;
        private final List<LocalResult> locals;
        private final int oldEndpointStates;
        private final int newEndpointStates;
        private final boolean terminalProductVerified;
        private final TransportReport transportReport;

        private Result(
                String solveStatus,
                String factorStatus,
                Partition partition,
                Collection<DependencyReceipt> receipts,
                Collection<LocalResult> locals,
                int oldEndpointStates,
                int newEndpointStates,
                boolean terminalProductVerified,
                TransportReport transportReport) {
            this.solveStatus = solveStatus;
            this.factorStatus = factorStatus;
            this.partition = partition;
            this.receipts = Collections.unmodifiableList(
                    new ArrayList<DependencyReceipt>(receipts));
            this.locals = Collections.unmodifiableList(
                    new ArrayList<LocalResult>(locals));
            this.oldEndpointStates = oldEndpointStates;
            this.newEndpointStates = newEndpointStates;
            this.terminalProductVerified = terminalProductVerified;
            this.transportReport = Objects.requireNonNull(
                    transportReport, "transport report");
        }

        private static Result trivial(StructuralInput input, Partition partition) {
            return new Result(
                    "NOT_RUN", "TRIVIAL_ONE_BLOCK", partition,
                    input.receipts, Collections.<LocalResult>emptyList(),
                    input.oldEndpoint.reachableStates().size(),
                    input.newEndpoint.reachableStates().size(), false,
                    TransportReport.notRun());
        }

        public String solveStatus() { return solveStatus; }
        public String factorStatus() { return factorStatus; }
        public List<List<Integer>> blocks() { return partition.blocks; }
        public List<DependencyReceipt> dependencyReceipts() { return receipts; }
        public List<LocalResult> locals() { return locals; }
        public int oldEndpointStates() { return oldEndpointStates; }
        public int newEndpointStates() { return newEndpointStates; }
        public boolean terminalProductVerified() {
            return terminalProductVerified;
        }
        public TransportReport transportReport() { return transportReport; }
    }

    /** Source-to-local witness-transport census retained in the public bundle. */
    public static final class TransportReport {
        private final boolean verified;
        private final int activationTesterCount;
        private final int activationRelationPairCount;
        private final int observerRelationPairCount;
        private final int loadSelectorSignatureCount;
        private final int loadSelectorEndpointCount;
        private final int certificateTerminalTupleCount;
        private final int terminalObserverFiberCount;
        private final List<ObserverRelationReceipt> observerRelations;
        private final List<LoadSelectorReceipt> loadSelectors;
        private final List<TerminalAssembly> terminalAssemblies;

        private TransportReport(
                boolean verified,
                int activationTesterCount,
                int activationRelationPairCount,
                int observerRelationPairCount,
                int loadSelectorSignatureCount,
                int loadSelectorEndpointCount,
                int certificateTerminalTupleCount,
                int terminalObserverFiberCount,
                Collection<ObserverRelationReceipt> observerRelations,
                Collection<LoadSelectorReceipt> loadSelectors,
                Collection<TerminalAssembly> terminalAssemblies) {
            this.verified = verified;
            this.activationTesterCount = activationTesterCount;
            this.activationRelationPairCount = activationRelationPairCount;
            this.observerRelationPairCount = observerRelationPairCount;
            this.loadSelectorSignatureCount = loadSelectorSignatureCount;
            this.loadSelectorEndpointCount = loadSelectorEndpointCount;
            this.certificateTerminalTupleCount = certificateTerminalTupleCount;
            this.terminalObserverFiberCount = terminalObserverFiberCount;
            this.observerRelations = Collections.unmodifiableList(
                    new ArrayList<ObserverRelationReceipt>(observerRelations));
            this.loadSelectors = Collections.unmodifiableList(
                    new ArrayList<LoadSelectorReceipt>(loadSelectors));
            this.terminalAssemblies = Collections.unmodifiableList(
                    new ArrayList<TerminalAssembly>(terminalAssemblies));
        }

        private static TransportReport notRun() {
            return new TransportReport(
                    false, 0, 0, 0, 0, 0, 0, 0,
                    Collections.<ObserverRelationReceipt>emptyList(),
                    Collections.<LoadSelectorReceipt>emptyList(),
                    Collections.<TerminalAssembly>emptyList());
        }

        public boolean isVerified() { return verified; }
        public int activationTesterCount() { return activationTesterCount; }
        public int activationRelationPairCount() {
            return activationRelationPairCount;
        }
        public int observerRelationPairCount() {
            return observerRelationPairCount;
        }
        public int loadSelectorSignatureCount() {
            return loadSelectorSignatureCount;
        }
        public int loadSelectorEndpointCount() {
            return loadSelectorEndpointCount;
        }
        public int certificateTerminalTupleCount() {
            return certificateTerminalTupleCount;
        }
        public int terminalObserverFiberCount() {
            return terminalObserverFiberCount;
        }
        public List<ObserverRelationReceipt> observerRelations() {
            return observerRelations;
        }
        public List<LoadSelectorReceipt> loadSelectors() {
            return loadSelectors;
        }
        public List<TerminalAssembly> terminalAssemblies() {
            return terminalAssemblies;
        }
    }

    public static final class ObserverRelationReceipt {
        private final int blockIndex;
        private final List<Integer> globalObserverIndices;
        private final List<ObserverRelationPair> pairs;

        private ObserverRelationReceipt(
                int blockIndex,
                Collection<Integer> globalObserverIndices,
                Collection<ObserverRelationPair> pairs) {
            this.blockIndex = blockIndex;
            this.globalObserverIndices = Collections.unmodifiableList(
                    new ArrayList<Integer>(globalObserverIndices));
            this.pairs = Collections.unmodifiableList(
                    new ArrayList<ObserverRelationPair>(pairs));
        }

        public int blockIndex() { return blockIndex; }
        public List<Integer> globalObserverIndices() {
            return globalObserverIndices;
        }
        public List<ObserverRelationPair> pairs() { return pairs; }
    }

    public static final class ObserverRelationPair {
        private final List<Long> global;
        private final List<Long> local;

        private ObserverRelationPair(
                Collection<Long> global, Collection<Long> local) {
            this.global = Collections.unmodifiableList(
                    new ArrayList<Long>(global));
            this.local = Collections.unmodifiableList(
                    new ArrayList<Long>(local));
        }

        public List<Long> global() { return global; }
        public List<Long> local() { return local; }
    }

    public static final class LoadSelectorReceipt {
        private final String endpointId;
        private final long controllerState;
        private final List<Long> componentRawStates;
        private final List<Long> observerStates;
        private final Map<String, Long> testerStates;

        private LoadSelectorReceipt(
                String endpointId,
                long controllerState,
                Collection<Long> componentRawStates,
                Collection<Long> observerStates,
                Map<String, Long> testerStates) {
            this.endpointId = endpointId;
            this.controllerState = controllerState;
            this.componentRawStates = Collections.unmodifiableList(
                    new ArrayList<Long>(componentRawStates));
            this.observerStates = Collections.unmodifiableList(
                    new ArrayList<Long>(observerStates));
            this.testerStates = Collections.unmodifiableMap(
                    new LinkedHashMap<String, Long>(testerStates));
        }

        public String endpointId() { return endpointId; }
        public long controllerState() { return controllerState; }
        public List<Long> componentRawStates() { return componentRawStates; }
        public List<Long> observerStates() { return observerStates; }
        public Map<String, Long> testerStates() { return testerStates; }
    }

    /** One canonical concrete load selected for a local terminal/fiber pair. */
    public static final class TerminalAssembly {
        private final int terminalTupleIndex;
        private final int observerFiberIndex;
        private final List<String> localGoalSignatureIds;
        private final List<Long> globalObserverStates;
        private final String endpointId;
        private final long controllerState;

        private TerminalAssembly(
                int terminalTupleIndex,
                int observerFiberIndex,
                Collection<String> localGoalSignatureIds,
                Collection<Long> globalObserverStates,
                String endpointId,
                long controllerState) {
            this.terminalTupleIndex = terminalTupleIndex;
            this.observerFiberIndex = observerFiberIndex;
            this.localGoalSignatureIds = Collections.unmodifiableList(
                    new ArrayList<String>(localGoalSignatureIds));
            this.globalObserverStates = Collections.unmodifiableList(
                    new ArrayList<Long>(globalObserverStates));
            this.endpointId = endpointId;
            this.controllerState = controllerState;
        }

        public int terminalTupleIndex() { return terminalTupleIndex; }
        public int observerFiberIndex() { return observerFiberIndex; }
        public List<String> localGoalSignatureIds() {
            return localGoalSignatureIds;
        }
        public List<Long> globalObserverStates() {
            return globalObserverStates;
        }
        public String endpointId() { return endpointId; }
        public long controllerState() { return controllerState; }
    }

    public static final class DependencyReceipt {
        private final String kind;
        private final String declaration;
        private final List<Integer> components;

        private DependencyReceipt(
                String kind, String declaration, Collection<Integer> components) {
            this.kind = kind;
            this.declaration = declaration;
            List<Integer> ordered = new ArrayList<Integer>(components);
            Collections.sort(ordered);
            this.components = Collections.unmodifiableList(ordered);
        }

        public String kind() { return kind; }
        public String declaration() { return declaration; }
        public List<Integer> components() { return components; }
    }

    public static final class LocalResult {
        private final int blockIndex;
        private final List<Integer> components;
        private final FineGrainedUpdateProblem<MtsaRevisedOtfDucsAdapter.LocalState, Long>
                problem;
        private final OtfDucsResult<CanonicalUpdateConfiguration<
                MtsaRevisedOtfDucsAdapter.LocalState, Long>, String,
                GoalSignature<MtsaRevisedOtfDucsAdapter.LocalState, Long>> result;
        private final List<GoalSignature<MtsaRevisedOtfDucsAdapter.LocalState, Long>>
                fullGoals;
        private final List<GoalSignature<MtsaRevisedOtfDucsAdapter.LocalState, Long>>
                quietGoals;
        private final Set<String> fullGoalUncontrollableActions;
        private final List<MtsaRevisedOtfDucsAdapter.Observer> blockObservers;
        private final List<MtsaRevisedOtfDucsAdapter.TesterRecord>
                blockNewTesters;
        private final IndependentExplicitStrongSolver.VerificationReport
                independentVerification;

        private LocalResult(
                int blockIndex,
                Collection<Integer> components,
                FineGrainedUpdateProblem<
                        MtsaRevisedOtfDucsAdapter.LocalState, Long> problem,
                OtfDucsResult<CanonicalUpdateConfiguration<
                        MtsaRevisedOtfDucsAdapter.LocalState, Long>, String,
                        GoalSignature<MtsaRevisedOtfDucsAdapter.LocalState, Long>> result,
                Collection<GoalSignature<
                        MtsaRevisedOtfDucsAdapter.LocalState, Long>> fullGoals,
                Collection<GoalSignature<
                        MtsaRevisedOtfDucsAdapter.LocalState, Long>> quietGoals,
                Collection<String> fullGoalUncontrollableActions,
                Collection<MtsaRevisedOtfDucsAdapter.Observer> blockObservers,
                Collection<MtsaRevisedOtfDucsAdapter.TesterRecord>
                        blockNewTesters,
                IndependentExplicitStrongSolver.VerificationReport
                        independentVerification) {
            this.blockIndex = blockIndex;
            this.components = Collections.unmodifiableList(
                    new ArrayList<Integer>(components));
            this.problem = problem;
            this.result = result;
            this.fullGoals = Collections.unmodifiableList(
                    new ArrayList<GoalSignature<
                            MtsaRevisedOtfDucsAdapter.LocalState, Long>>(fullGoals));
            this.quietGoals = Collections.unmodifiableList(
                    new ArrayList<GoalSignature<
                            MtsaRevisedOtfDucsAdapter.LocalState, Long>>(quietGoals));
            this.fullGoalUncontrollableActions = Collections.unmodifiableSet(
                    new LinkedHashSet<String>(fullGoalUncontrollableActions));
            this.blockObservers = Collections.unmodifiableList(
                    new ArrayList<MtsaRevisedOtfDucsAdapter.Observer>(
                            blockObservers));
            this.blockNewTesters = Collections.unmodifiableList(
                    new ArrayList<MtsaRevisedOtfDucsAdapter.TesterRecord>(
                            blockNewTesters));
            this.independentVerification = Objects.requireNonNull(
                    independentVerification, "independent verification");
        }

        public int blockIndex() { return blockIndex; }
        public List<Integer> components() { return components; }
        public FineGrainedUpdateProblem<MtsaRevisedOtfDucsAdapter.LocalState, Long>
                problem() { return problem; }
        public OtfDucsResult<CanonicalUpdateConfiguration<
                MtsaRevisedOtfDucsAdapter.LocalState, Long>, String,
                GoalSignature<MtsaRevisedOtfDucsAdapter.LocalState, Long>> result() {
            return result;
        }
        public int fullGoalCount() { return fullGoals.size(); }
        public int quietGoalCount() { return quietGoals.size(); }
        public Set<String> fullGoalUncontrollableActions() {
            return fullGoalUncontrollableActions;
        }
        private List<MtsaRevisedOtfDucsAdapter.TesterRecord>
                dormantNewTesters() {
            return blockNewTesters;
        }
        public IndependentExplicitStrongSolver.VerificationReport
                independentVerification() {
            return independentVerification;
        }
    }

    private static final class StructuralInput {
        private final UpdatingControllerCompositeState source;
        private final List<CompactState> oldMachines;
        private final List<FiniteLts<Long>> rawOld;
        private final List<FiniteLts<Long>> rawNew;
        private final List<Map<Integer, Set<Integer>>> rawTransfers;
        private final Set<String> normalActions;
        private final Set<String> controllableNormal;
        private final Set<String> commonAlphabet;
        private final UpdateProtocolSpec protocol;
        private final List<MtsaRevisedOtfDucsAdapter.Observer> observers;
        private final List<MtsaRevisedOtfDucsAdapter.TesterRecord> oldTesters;
        private final List<MtsaRevisedOtfDucsAdapter.TesterRecord> newTesters;
        private final List<MtsaRevisedOtfDucsAdapter.TesterRecord> updateTesters;
        private final FiniteLts<Long> oldController;
        private final FiniteLts<Long> newController;
        private final List<VersionedComponent<MtsaRevisedOtfDucsAdapter.LocalState>>
                rawComponents;
        private final List<VersionedComponent<MtsaRevisedOtfDucsAdapter.LocalState>>
                endpointComponents;
        private final FiniteLts<MtsaRevisedOtfDucsAdapter.EndpointState> oldEndpoint;
        private final FiniteLts<MtsaRevisedOtfDucsAdapter.EndpointState> newEndpoint;
        private final Set<MtsaRevisedOtfDucsAdapter.EndpointState> loadableNew;
        private final List<DependencyReceipt> receipts;

        private StructuralInput(
                UpdatingControllerCompositeState source,
                List<CompactState> oldMachines,
                List<FiniteLts<Long>> rawOld,
                List<FiniteLts<Long>> rawNew,
                List<Map<Integer, Set<Integer>>> rawTransfers,
                Set<String> normalActions,
                Set<String> controllableNormal,
                Set<String> commonAlphabet,
                UpdateProtocolSpec protocol,
                List<MtsaRevisedOtfDucsAdapter.Observer> observers,
                List<MtsaRevisedOtfDucsAdapter.TesterRecord> oldTesters,
                List<MtsaRevisedOtfDucsAdapter.TesterRecord> newTesters,
                List<MtsaRevisedOtfDucsAdapter.TesterRecord> updateTesters,
                FiniteLts<Long> oldController,
                FiniteLts<Long> newController,
                List<VersionedComponent<MtsaRevisedOtfDucsAdapter.LocalState>>
                        rawComponents,
                List<VersionedComponent<MtsaRevisedOtfDucsAdapter.LocalState>>
                        endpointComponents,
                FiniteLts<MtsaRevisedOtfDucsAdapter.EndpointState> oldEndpoint,
                FiniteLts<MtsaRevisedOtfDucsAdapter.EndpointState> newEndpoint,
                Set<MtsaRevisedOtfDucsAdapter.EndpointState> loadableNew,
                List<DependencyReceipt> receipts) {
            this.source = source;
            this.oldMachines = oldMachines;
            this.rawOld = rawOld;
            this.rawNew = rawNew;
            this.rawTransfers = rawTransfers;
            this.normalActions = normalActions;
            this.controllableNormal = controllableNormal;
            this.commonAlphabet = commonAlphabet;
            this.protocol = protocol;
            this.observers = observers;
            this.oldTesters = oldTesters;
            this.newTesters = newTesters;
            this.updateTesters = updateTesters;
            this.oldController = oldController;
            this.newController = newController;
            this.rawComponents = rawComponents;
            this.endpointComponents = endpointComponents;
            this.oldEndpoint = oldEndpoint;
            this.newEndpoint = newEndpoint;
            this.loadableNew = loadableNew;
            this.receipts = receipts;
        }

        private static StructuralInput compile(
                UpdatingControllerCompositeState source) {
            if (!source.isRevisedOnTheFly() || !source.isFineGrained()
                    || !source.isOTF() || source.getUpdateProtocolSpec() == null
                    || source.getUpdateProtocolSpec().isSelective()) {
                throw new IllegalArgumentException(
                        "Tier A requires non-selective revised fine-grained input");
            }
            if (source.hasTransferRelationActionSequences()) {
                throw new IllegalArgumentException(
                        "Tier A requires direct transfer relations");
            }
            Vector<CompactState> oldVector =
                    source.getRawOldEnvironmentComponents();
            Vector<CompactState> newVector =
                    source.getRawNewEnvironmentComponents();
            List<Map<Integer, Set<Integer>>> transfers =
                    source.getRawTransferRelations();
            if (oldVector.isEmpty() || oldVector.size() != newVector.size()
                    || oldVector.size() != transfers.size()) {
                throw new IllegalArgumentException(
                        "native contract has an incomplete component mapping");
            }
            List<CompactState> oldMachines = new ArrayList<CompactState>(oldVector);
            List<FiniteLts<Long>> rawOld = new ArrayList<FiniteLts<Long>>();
            List<FiniteLts<Long>> rawNew = new ArrayList<FiniteLts<Long>>();
            LinkedHashSet<String> normal = new LinkedHashSet<String>();
            for (int index = 0; index < oldVector.size(); index++) {
                FiniteLts<Long> oldLts = FiniteLts.fromMtsa(oldVector.get(index));
                FiniteLts<Long> newLts = FiniteLts.fromMtsa(newVector.get(index));
                rawOld.add(oldLts);
                rawNew.add(newLts);
                normal.addAll(oldLts.alphabet());
                normal.addAll(newLts.alphabet());
            }
            normal.remove(UpdateConstants.BEGIN_UPDATE);
            normal.remove(UpdateConstants.FINISH_UPDATE);
            normal.remove("tau");
            UpdateProtocolSpec protocol = source.getUpdateProtocolSpec();
            LinkedHashSet<String> common = new LinkedHashSet<String>(normal);
            common.addAll(protocol.getProgressActions());
            List<MtsaRevisedOtfDucsAdapter.Observer> observers =
                    MtsaRevisedOtfDucsAdapter.compileObservers(
                            source.getSynthesisMachines(), normal);
            List<MtsaRevisedOtfDucsAdapter.TesterRecord> oldTesters =
                    MtsaRevisedOtfDucsAdapter.compileTesters(
                            source.getOldSafetyLTSs(), RequirementRole.OLD, common);
            List<MtsaRevisedOtfDucsAdapter.TesterRecord> newTesters =
                    MtsaRevisedOtfDucsAdapter.compileTesters(
                            source.getNewSafetyLTSs(), RequirementRole.NEW, common);
            List<MtsaRevisedOtfDucsAdapter.TesterRecord> updateTesters =
                    MtsaRevisedOtfDucsAdapter.compileTesters(
                            source.getTransitionRequirements(),
                            RequirementRole.UPDATE_TIME, common);
            MtsaRevisedOtfDucsAdapter.bindUpdateActions(
                    oldTesters, newTesters, protocol);
            validateConcreteUpdateActions(
                    protocol, oldVector.size(), oldTesters, newTesters,
                    normal);

            LinkedHashSet<String> controllable =
                    new LinkedHashSet<String>(source.getControllableActions());
            controllable.retainAll(normal);
            FiniteLts<Long> oldController = importController(
                    source.getOldController(), normal, "old");
            FiniteLts<Long> newController = importController(
                    source.getNewController(), normal, "new");

            List<VersionedComponent<MtsaRevisedOtfDucsAdapter.LocalState>>
                    rawComponents = new ArrayList<VersionedComponent<
                            MtsaRevisedOtfDucsAdapter.LocalState>>();
            for (int index = 0; index < rawOld.size(); index++) {
                rawComponents.add(rawComponent(
                        oldMachines.get(index), index,
                        rawOld.get(index), rawNew.get(index),
                        transfers.get(index), protocol));
            }
            List<Long> initialObserverStates = new ArrayList<Long>();
            for (MtsaRevisedOtfDucsAdapter.Observer observer : observers) {
                initialObserverStates.add(observer.initialState);
            }
            List<VersionedComponent<MtsaRevisedOtfDucsAdapter.LocalState>>
                    endpointComponents =
                    MtsaRevisedOtfDucsAdapter.compileComponents(
                            oldMachines, rawOld, rawNew, transfers,
                            protocol, observers, initialObserverStates, normal);
            MtsaRevisedOtfDucsAdapter.validateEndpointControllerAlphabets(
                    endpointComponents, oldController, newController);
            FiniteLts<MtsaRevisedOtfDucsAdapter.EndpointState> oldEndpoint =
                    MtsaRevisedOtfDucsAdapter.buildEndpoint(
                            oldController, endpointComponents,
                            oldTesters, true, normal);
            FiniteLts<MtsaRevisedOtfDucsAdapter.EndpointState> newEndpoint =
                    MtsaRevisedOtfDucsAdapter.buildEndpoint(
                            newController, endpointComponents,
                            newTesters, false, normal);
            Set<MtsaRevisedOtfDucsAdapter.EndpointState> loadable =
                    MtsaRevisedOtfDucsAdapter.selectLoadableNewEndpointStates(
                            source, newEndpoint);

            StructuralInput result = new StructuralInput(
                    source,
                    Collections.unmodifiableList(oldMachines),
                    Collections.unmodifiableList(rawOld),
                    Collections.unmodifiableList(rawNew),
                    Collections.unmodifiableList(new ArrayList<Map<Integer,
                            Set<Integer>>>(transfers)),
                    Collections.unmodifiableSet(normal),
                    Collections.unmodifiableSet(controllable),
                    Collections.unmodifiableSet(common),
                    protocol,
                    Collections.unmodifiableList(observers),
                    Collections.unmodifiableList(oldTesters),
                    Collections.unmodifiableList(newTesters),
                    Collections.unmodifiableList(updateTesters),
                    oldController, newController,
                    Collections.unmodifiableList(rawComponents),
                    Collections.unmodifiableList(endpointComponents),
                    oldEndpoint, newEndpoint, loadable,
                    new ArrayList<DependencyReceipt>());
            result.validateNativeEndpointContracts();
            return result;
        }

        /** Matches FineGrainedUpdateProblem's global update-action namespace. */
        private static void validateConcreteUpdateActions(
                UpdateProtocolSpec protocol,
                int componentCount,
                List<MtsaRevisedOtfDucsAdapter.TesterRecord> oldTesters,
                List<MtsaRevisedOtfDucsAdapter.TesterRecord> newTesters,
                Set<String> normalActions) {
            LinkedHashSet<String> concrete = new LinkedHashSet<String>();
            for (int index = 0; index < componentCount; index++) {
                registerConcreteUpdateAction(
                        concrete,
                        MtsaRevisedOtfDucsAdapter.requireReconfigureAction(
                                protocol, index));
            }
            for (MtsaRevisedOtfDucsAdapter.TesterRecord tester : oldTesters) {
                registerConcreteUpdateAction(concrete, tester.updateAction);
            }
            for (MtsaRevisedOtfDucsAdapter.TesterRecord tester : newTesters) {
                registerConcreteUpdateAction(concrete, tester.updateAction);
            }
            if (!concrete.equals(protocol.getProgressActions())) {
                LinkedHashSet<String> missing = new LinkedHashSet<String>(
                        protocol.getProgressActions());
                missing.removeAll(concrete);
                LinkedHashSet<String> extra =
                        new LinkedHashSet<String>(concrete);
                extra.removeAll(protocol.getProgressActions());
                throw new IllegalArgumentException(
                        "native update-action census differs from protocol: "
                                + "missing=" + missing + ", extra=" + extra);
            }
            LinkedHashSet<String> collision =
                    new LinkedHashSet<String>(concrete);
            collision.retainAll(normalActions);
            if (!collision.isEmpty()) {
                throw new IllegalArgumentException(
                        "normal/update action namespaces overlap: " + collision);
            }
            for (Map.Entry<String, Set<Integer>> entry
                    : protocol.getActionToMappingIndices().entrySet()) {
                if (entry.getValue().size() != 1) {
                    throw new IllegalArgumentException(
                            "one concrete reconfigure action is shared by "
                                    + "multiple mappings: " + entry);
                }
            }
        }

        private static void registerConcreteUpdateAction(
                Set<String> actions, String action) {
            if (action == null || action.trim().isEmpty()
                    || !actions.add(action)) {
                throw new IllegalArgumentException(
                        "every concrete update action must be unique: " + action);
            }
        }

        /**
         * Replays the production endpoint Link contract without constructing
         * the mixed-version update game.  Every reachable fixed-endpoint state
         * must be live.  If a controller permits an action, its physical and
         * tester projection must retain every environment outcome; moreover an
         * uncontrollable environment action may not be disabled by the fixed
         * controller.  Observer-only transitions are deliberately excluded
         * from physical participation, matching EndpointContractValidator.
         */
        private void validateNativeEndpointContracts() {
            validateNativeEndpoint(
                    "old", oldEndpoint, oldTesters, true);
            validateNativeEndpoint(
                    "new", newEndpoint, newTesters, false);
        }

        private void validateNativeEndpoint(
                String label,
                FiniteLts<MtsaRevisedOtfDucsAdapter.EndpointState> endpoint,
                List<MtsaRevisedOtfDucsAdapter.TesterRecord> testers,
                boolean old) {
            if (!normalActions.containsAll(endpoint.alphabet())) {
                throw new IllegalArgumentException(
                        label + " endpoint contains a non-normal action");
            }
            for (MtsaRevisedOtfDucsAdapter.EndpointState state
                    : endpoint.reachableStates()) {
                if (endpoint.enabledActions(state).isEmpty()) {
                    throw new IllegalArgumentException(
                            label + " endpoint is deadlocked at " + state);
                }
                for (String action : normalActions) {
                    Set<EndpointProjection> expected = endpointPostProjection(
                            state, testers, old, action);
                    LinkedHashSet<EndpointProjection> actual =
                            new LinkedHashSet<EndpointProjection>();
                    for (MtsaRevisedOtfDucsAdapter.EndpointState target
                            : endpoint.successors(state, action)) {
                        actual.add(new EndpointProjection(
                                target.localStates(), target.testerStates()));
                    }
                    if (!actual.isEmpty() && !actual.equals(expected)) {
                        throw new IllegalArgumentException(
                                label + " endpoint does not preserve every "
                                        + "environment outcome at " + state
                                        + " / " + action);
                    }
                    if (!controllableNormal.contains(action)
                            && !expected.isEmpty() && actual.isEmpty()) {
                        throw new IllegalArgumentException(
                                label + " endpoint disables uncontrollable "
                                        + "action at " + state + " / " + action);
                    }
                }
            }
        }

        private Set<EndpointProjection> endpointPostProjection(
                MtsaRevisedOtfDucsAdapter.EndpointState state,
                List<MtsaRevisedOtfDucsAdapter.TesterRecord> testers,
                boolean old,
                String action) {
            List<List<MtsaRevisedOtfDucsAdapter.LocalState>> choices =
                    new ArrayList<List<MtsaRevisedOtfDucsAdapter.LocalState>>();
            boolean participant = false;
            for (int index = 0; index < endpointComponents.size(); index++) {
                VersionedComponent<MtsaRevisedOtfDucsAdapter.LocalState>
                        component = endpointComponents.get(index);
                FiniteLts<MtsaRevisedOtfDucsAdapter.LocalState> active = old
                        ? component.oldLts() : component.newLts();
                MtsaRevisedOtfDucsAdapter.LocalState local =
                        state.localStates().get(index);
                if (component.environmentHasAction(
                        old ? ComponentVersion.OLD : ComponentVersion.NEW,
                        action)) {
                    participant = true;
                }
                if (active.hasAction(action)) {
                    Set<MtsaRevisedOtfDucsAdapter.LocalState> targets =
                            active.successors(local, action);
                    if (targets.isEmpty()) return Collections.emptySet();
                    choices.add(new ArrayList<
                            MtsaRevisedOtfDucsAdapter.LocalState>(targets));
                }
                else {
                    choices.add(Collections.singletonList(local));
                }
            }
            if (!participant) return Collections.emptySet();

            LinkedHashMap<String, Long> testerTargets =
                    new LinkedHashMap<String, Long>();
            for (MtsaRevisedOtfDucsAdapter.TesterRecord tester : testers) {
                Long testerState = state.testerStates().get(tester.id);
                if (testerState == null) {
                    throw new IllegalArgumentException(
                            "endpoint projection omits tester " + tester.id);
                }
                testerTargets.put(tester.id,
                        tester.tester.stepOrStutter(testerState, action));
            }
            LinkedHashSet<EndpointProjection> result =
                    new LinkedHashSet<EndpointProjection>();
            endpointCartesian(
                    choices, 0,
                    new ArrayList<MtsaRevisedOtfDucsAdapter.LocalState>(),
                    testerTargets, result);
            return result;
        }

        private static void endpointCartesian(
                List<List<MtsaRevisedOtfDucsAdapter.LocalState>> choices,
                int index,
                List<MtsaRevisedOtfDucsAdapter.LocalState> current,
                Map<String, Long> testerTargets,
                Set<EndpointProjection> output) {
            if (index == choices.size()) {
                output.add(new EndpointProjection(current, testerTargets));
                return;
            }
            for (MtsaRevisedOtfDucsAdapter.LocalState choice
                    : choices.get(index)) {
                current.add(choice);
                endpointCartesian(
                        choices, index + 1, current, testerTargets, output);
                current.remove(current.size() - 1);
            }
        }

        private static final class EndpointProjection {
            private final List<MtsaRevisedOtfDucsAdapter.LocalState> physical;
            private final Map<String, Long> testers;

            private EndpointProjection(
                    Collection<MtsaRevisedOtfDucsAdapter.LocalState> physical,
                    Map<String, Long> testers) {
                this.physical = Collections.unmodifiableList(
                        new ArrayList<MtsaRevisedOtfDucsAdapter.LocalState>(
                                physical));
                this.testers = Collections.unmodifiableMap(
                        new LinkedHashMap<String, Long>(testers));
            }

            @Override public boolean equals(Object other) {
                if (!(other instanceof EndpointProjection)) return false;
                EndpointProjection that = (EndpointProjection) other;
                return physical.equals(that.physical)
                        && testers.equals(that.testers);
            }

            @Override public int hashCode() {
                return Objects.hash(physical, testers);
            }
        }

        private Partition dependencies() {
            UnionFind union = new UnionFind(rawOld.size());
            receipts.clear();
            Map<String, Set<Integer>> actionOwners = actionOwners();
            for (Map.Entry<String, Set<Integer>> entry : actionOwners.entrySet()) {
                if (!entry.getValue().isEmpty()) {
                    addDependency(union, "ordinary-action", entry.getKey(),
                            entry.getValue());
                }
            }

            Map<String, Set<Integer>> updateOwners = new LinkedHashMap<String,
                    Set<Integer>>();
            for (int index = 0; index < rawOld.size(); index++) {
                String action = MtsaRevisedOtfDucsAdapter
                        .requireReconfigureAction(protocol, index);
                updateOwners.put(action, union(
                        updateOwners.get(action), singleton(index)));
            }
            boolean changed;
            do {
                changed = false;
                for (MtsaRevisedOtfDucsAdapter.TesterRecord tester
                        : allTesters()) {
                    Set<Integer> support = testerSupport(tester, actionOwners,
                            updateOwners);
                    if (tester.updateAction != null) {
                        Set<Integer> previous = updateOwners.get(tester.updateAction);
                        Set<Integer> merged = union(previous, support);
                        if (!merged.equals(previous)) {
                            updateOwners.put(tester.updateAction, merged);
                            changed = true;
                        }
                    }
                }
            } while (changed);

            for (Map.Entry<String, Set<Integer>> entry
                    : updateOwners.entrySet()) {
                if (entry.getValue() == null || entry.getValue().isEmpty()) {
                    throw new IllegalArgumentException(
                            "update action has no native component support: "
                                    + entry.getKey());
                }
                addDependency(union, "update-action", entry.getKey(),
                        entry.getValue());
            }
            for (MtsaRevisedOtfDucsAdapter.TesterRecord tester
                    : allTesters()) {
                Set<Integer> support = testerSupport(
                        tester, actionOwners, updateOwners);
                if (support.isEmpty()) {
                    throw new IllegalArgumentException(
                            "opaque tester has no native component support: "
                                    + tester.sourceName);
                }
                addDependency(union, "tester", tester.sourceName, support);
            }

            /*
             * Fluent/action observers are an implementation encoding of the
             * compiled safety languages.  In particular an action-proposition
             * observer may reset on every unrelated event although the final
             * safety tester stutters on those events.  Dependency is therefore
             * taken from the tester language below; the observer is projected
             * to that language when a local problem is constructed.
             */
            for (MtsaRevisedOtfDucsAdapter.TesterRecord tester : newTesters) {
                LinkedHashSet<Integer> support = new LinkedHashSet<Integer>(
                        testerSupport(tester, actionOwners, updateOwners));
                addDependency(union, "activation", tester.sourceName,
                        support);
            }
            for (UpdateProtocolSpec.PrecedenceEdge edge
                    : protocol.getPrecedenceEdges()) {
                Set<Integer> support = union(
                        updateOwners.get(edge.before()),
                        updateOwners.get(edge.after()));
                addDependency(union, "precedence",
                        edge.before() + "<" + edge.after(), support);
            }
            return new Partition(union.components());
        }

        /** Validation that remains meaningful even when no local split exists. */
        private void validateExtractionOnly() {
            validateOwnerlessActions(actionOwners());
            if (oldEndpoint.reachableStates().isEmpty()
                    || newEndpoint.reachableStates().isEmpty()
                    || loadableNew.isEmpty()) {
                throw new IllegalArgumentException(
                        "native endpoint/load domains must be nonempty");
            }
        }

        private Map<String, Set<Integer>> actionOwners() {
            LinkedHashMap<String, Set<Integer>> result =
                    new LinkedHashMap<String, Set<Integer>>();
            for (String action : normalActions) {
                LinkedHashSet<Integer> owners = new LinkedHashSet<Integer>();
                for (int index = 0; index < rawOld.size(); index++) {
                    if (hasNonIdentityParticipation(rawOld.get(index), action)
                            || hasNonIdentityParticipation(
                                    rawNew.get(index), action)) {
                        owners.add(Integer.valueOf(index));
                    }
                }
                result.put(action, Collections.unmodifiableSet(owners));
            }
            return result;
        }

        /**
         * A declared participant is transparent only when the event is
         * enabled at every local state and has exactly the identity outcome.
         * Partial self-loops therefore remain dependencies, as required by
         * synchronous enabledness semantics.
         */
        private static boolean hasNonIdentityParticipation(
                FiniteLts<Long> lts, String action) {
            if (!lts.hasAction(action)) return false;
            for (Long state : lts.states()) {
                Set<Long> targets = lts.successors(state, action);
                if (targets.size() != 1 || !targets.contains(state)) {
                    return true;
                }
            }
            return false;
        }

        private List<MtsaRevisedOtfDucsAdapter.TesterRecord> allTesters() {
            List<MtsaRevisedOtfDucsAdapter.TesterRecord> result =
                    new ArrayList<MtsaRevisedOtfDucsAdapter.TesterRecord>();
            result.addAll(oldTesters);
            result.addAll(newTesters);
            result.addAll(updateTesters);
            return result;
        }

        private Set<Integer> testerSupport(
                MtsaRevisedOtfDucsAdapter.TesterRecord tester,
                Map<String, Set<Integer>> actionOwners,
                Map<String, Set<Integer>> updateOwners) {
            LinkedHashSet<Integer> result = new LinkedHashSet<Integer>(
                    ownersOf(effectiveTesterActions(tester.tester),
                            actionOwners, updateOwners));
            if (tester.updateAction != null) {
                Set<Integer> update = updateOwners.get(tester.updateAction);
                if (update != null) result.addAll(update);
            }
            return Collections.unmodifiableSet(result);
        }

        /**
         * Returns exactly the observer actions whose declared transition is
         * non-identity at some state.  LTSA completes fluent alphabets with
         * identity loops for synchronization; those loops are semantically
         * foreign stutter and must not create a dependency edge.
         */
        private static Set<String> effectiveObserverActions(
                MtsaRevisedOtfDucsAdapter.Observer observer) {
            LinkedHashSet<String> result = new LinkedHashSet<String>();
            for (String action : observer.alphabet) {
                for (long raw = 0L; raw < observer.source.maxStates; raw++) {
                    Long state = Long.valueOf(raw);
                    if (!observer.stepOrStutter(state, action).equals(state)) {
                        result.add(action);
                        break;
                    }
                }
            }
            return Collections.unmodifiableSet(result);
        }

        /** Same non-identity support rule for deterministic safety testers. */
        private static Set<String> effectiveTesterActions(
                SafetyTester<Long> tester) {
            LinkedHashSet<String> result = new LinkedHashSet<String>();
            for (String action : tester.alphabet()) {
                for (Long state : tester.states()) {
                    if (!tester.stepOrStutter(state, action).equals(state)) {
                        result.add(action);
                        break;
                    }
                }
            }
            return Collections.unmodifiableSet(result);
        }

        private static Set<Integer> ownersOf(
                Collection<String> actions,
                Map<String, Set<Integer>> normalOwners,
                Map<String, Set<Integer>> updateOwners) {
            LinkedHashSet<Integer> result = new LinkedHashSet<Integer>();
            for (String action : actions) {
                Set<Integer> owners = normalOwners.get(action);
                if (owners == null) owners = updateOwners.get(action);
                if (owners != null) result.addAll(owners);
            }
            return result;
        }

        private void addDependency(
                UnionFind union,
                String kind,
                String declaration,
                Collection<Integer> support) {
            List<Integer> ordered = new ArrayList<Integer>(support);
            Collections.sort(ordered);
            if (ordered.isEmpty()) return;
            if (ordered.size() >= 2) {
                for (int index = 1; index < ordered.size(); index++) {
                    union.join(ordered.get(0).intValue(),
                            ordered.get(index).intValue());
                }
            }
            DependencyReceipt receipt =
                    new DependencyReceipt(kind, declaration, ordered);
            for (DependencyReceipt existing : receipts) {
                if (existing.kind().equals(receipt.kind())
                        && existing.declaration().equals(receipt.declaration())
                        && existing.components().equals(receipt.components())) {
                    return;
                }
            }
            receipts.add(receipt);
        }

        private LocalResult solveBlock(
                int blockIndex, List<Integer> block) {
            LinkedHashSet<String> blockNormal = new LinkedHashSet<String>();
            Set<Integer> blockSet = new LinkedHashSet<Integer>(block);
            Map<String, Set<Integer>> normalOwners = actionOwners();
            validateOwnerlessActions(normalOwners);
            for (Map.Entry<String, Set<Integer>> entry
                    : normalOwners.entrySet()) {
                if (!entry.getValue().isEmpty()
                        && blockSet.containsAll(entry.getValue())) {
                    blockNormal.add(entry.getKey());
                }
            }
            blockNormal.retainAll(normalActions);
            LinkedHashSet<String> blockUpdate = new LinkedHashSet<String>();
            for (Integer component : block) {
                blockUpdate.add(MtsaRevisedOtfDucsAdapter.requireReconfigureAction(
                        protocol, component.intValue()));
            }
            Map<String, Set<Integer>> updateOwners = updateOwnersForPartition();

            List<MtsaRevisedOtfDucsAdapter.TesterRecord> selectedOld =
                    localTesters(oldTesters, block, normalOwners, updateOwners);
            List<MtsaRevisedOtfDucsAdapter.TesterRecord> selectedNew =
                    localTesters(newTesters, block, normalOwners, updateOwners);
            List<MtsaRevisedOtfDucsAdapter.TesterRecord> selectedUpdate =
                    localTesters(updateTesters, block, normalOwners, updateOwners);
            for (MtsaRevisedOtfDucsAdapter.TesterRecord tester : selectedOld) {
                blockUpdate.add(tester.updateAction);
            }
            for (MtsaRevisedOtfDucsAdapter.TesterRecord tester : selectedNew) {
                blockUpdate.add(tester.updateAction);
            }
            LinkedHashSet<String> blockCommon =
                    new LinkedHashSet<String>(blockNormal);
            blockCommon.addAll(blockUpdate);

            List<MtsaRevisedOtfDucsAdapter.TesterRecord> blockOld =
                    projectTesters(selectedOld, blockCommon);
            List<MtsaRevisedOtfDucsAdapter.TesterRecord> blockNew =
                    projectTesters(selectedNew, blockCommon);
            List<MtsaRevisedOtfDucsAdapter.TesterRecord> blockUpdateTesters =
                    projectTesters(selectedUpdate, blockCommon);

            List<MtsaRevisedOtfDucsAdapter.Observer> blockObservers =
                    localObservers(selectedNew, blockNormal);
            List<Long> initialObserverStates = new ArrayList<Long>();
            for (MtsaRevisedOtfDucsAdapter.Observer observer : blockObservers) {
                initialObserverStates.add(observer.initialState);
            }

            List<VersionedComponent<MtsaRevisedOtfDucsAdapter.LocalState>>
                    components = localComponents(
                            block, blockObservers, initialObserverStates,
                            blockNormal);

            List<InitialSnapshot<MtsaRevisedOtfDucsAdapter.LocalState, Long>>
                    roots = projectRoots(block, components, blockObservers,
                            blockOld, blockUpdateTesters);
            Set<PhysicalState<MtsaRevisedOtfDucsAdapter.LocalState>> rootPhysical =
                    new LinkedHashSet<PhysicalState<
                            MtsaRevisedOtfDucsAdapter.LocalState>>();
            for (InitialSnapshot<MtsaRevisedOtfDucsAdapter.LocalState, Long>
                    root : roots) {
                rootPhysical.add(root.physicalState());
            }
            Set<PhysicalState<MtsaRevisedOtfDucsAdapter.LocalState>> closure =
                    blockNew.isEmpty()
                            ? Collections.<PhysicalState<
                                    MtsaRevisedOtfDucsAdapter.LocalState>>emptySet()
                            : MtsaRevisedOtfDucsAdapter.physicalClosure(
                                    components, blockNormal, rootPhysical);

            List<Requirement<MtsaRevisedOtfDucsAdapter.LocalState, Long>>
                    requirements = new ArrayList<Requirement<
                            MtsaRevisedOtfDucsAdapter.LocalState, Long>>();
            for (MtsaRevisedOtfDucsAdapter.TesterRecord tester : blockOld) {
                requirements.add(Requirement.oldRequirement(
                        tester.id, tester.tester, tester.updateAction));
            }
            for (MtsaRevisedOtfDucsAdapter.TesterRecord tester : blockNew) {
                requirements.add(Requirement.newRequirement(
                        tester.id, tester.tester,
                        MtsaRevisedOtfDucsAdapter.newActivation(
                                tester, closure, blockObservers,
                                source.getSafetyComponentsMap(),
                                source.getSafetyStateMapping(), blockCommon),
                        tester.updateAction));
            }
            for (MtsaRevisedOtfDucsAdapter.TesterRecord tester
                    : blockUpdateTesters) {
                requirements.add(Requirement.updateTimeRequirement(
                        tester.id, tester.tester,
                        MtsaRevisedOtfDucsAdapter.updateActivation(
                                tester, rootPhysical, blockCommon)));
            }

            List<GoalSignature<MtsaRevisedOtfDucsAdapter.LocalState, Long>>
                    fullGoals = projectGoals(
                            block, components, blockObservers, blockNew);
            LinkedHashSet<String> fullGoalUc = new LinkedHashSet<String>();
            List<GoalSignature<MtsaRevisedOtfDucsAdapter.LocalState, Long>>
                    quietGoals = new ArrayList<GoalSignature<
                            MtsaRevisedOtfDucsAdapter.LocalState, Long>>();
            for (GoalSignature<MtsaRevisedOtfDucsAdapter.LocalState, Long> goal
                    : fullGoals) {
                Set<String> enabled = enabledUncontrollableAtGoal(
                        components, goal, blockNormal);
                if (enabled.isEmpty()) quietGoals.add(goal);
                else fullGoalUc.addAll(enabled);
            }
            if (quietGoals.isEmpty()) {
                throw new IllegalArgumentException(
                        "block " + blockIndex
                                + " has no loadable uncontrollable-quiescent Goal slice");
            }

            FineGrainedUpdateProblem.Builder<
                    MtsaRevisedOtfDucsAdapter.LocalState, Long> builder =
                    FineGrainedUpdateProblem.<
                            MtsaRevisedOtfDucsAdapter.LocalState, Long>builder()
                            .components(components)
                            .requirements(requirements)
                            .normalActions(blockNormal)
                            .controllableNormalActions(intersection(
                                    controllableNormal, blockNormal))
                            .initialSnapshots(roots)
                            .goalSignatures(quietGoals);
            addLocalPrecedence(builder, blockUpdate);
            FineGrainedUpdateProblem<MtsaRevisedOtfDucsAdapter.LocalState, Long>
                    problem = builder.build();
            OtfDucsResult<CanonicalUpdateConfiguration<
                    MtsaRevisedOtfDucsAdapter.LocalState, Long>, String,
                    GoalSignature<MtsaRevisedOtfDucsAdapter.LocalState, Long>>
                    result = FineGrainedOtfDucs
                            .synthesizeTrustedEndpointProjections(problem);
            IndependentExplicitStrongSolver.VerificationReport verification =
                    new IndependentExplicitStrongSolver<
                            MtsaRevisedOtfDucsAdapter.LocalState, Long>(
                            problem,
                            Long.getLong(
                                    "mtsa.native.factor.certificateStateLimit",
                                    10_000_000L).longValue(),
                            Long.getLong(
                                    "mtsa.native.factor.certificateQueryLimit",
                                    100_000_000L).longValue())
                            .verifyCertificate(result);
            verification.throwIfInvalid();
            return new LocalResult(
                    blockIndex, block, problem, result,
                    fullGoals, quietGoals, fullGoalUc, blockObservers,
                    blockNew,
                    verification);
        }

        private boolean quietProductContained(List<LocalResult> locals) {
            List<List<String>> choices = new ArrayList<List<String>>();
            for (LocalResult local : locals) {
                LinkedHashSet<String> keys = new LinkedHashSet<String>();
                for (GoalSignature<MtsaRevisedOtfDucsAdapter.LocalState, Long>
                        goal : local.quietGoals) {
                    keys.add(goalProjectionKey(goal));
                }
                if (keys.isEmpty()) return false;
                List<String> ordered = new ArrayList<String>(keys);
                Collections.sort(ordered);
                choices.add(ordered);
            }
            long maximum = Long.getLong(
                    "mtsa.native.factor.maxTerminalProduct", 1_000_000L)
                    .longValue();
            long product = 1L;
            for (List<String> values : choices) {
                if (product > maximum / values.size()) {
                    throw new IllegalStateException(
                            "quiet terminal product exceeds the registered bound");
                }
                product *= values.size();
            }
            LinkedHashSet<List<String>> expected =
                    new LinkedHashSet<List<String>>();
            cartesianStrings(choices, 0, new ArrayList<String>(), expected);

            LinkedHashSet<List<String>> actual =
                    new LinkedHashSet<List<String>>();
            for (MtsaRevisedOtfDucsAdapter.EndpointState endpoint
                    : loadableNew) {
                List<String> tuple = new ArrayList<String>();
                boolean selected = true;
                for (LocalResult local : locals) {
                    List<TaggedState<MtsaRevisedOtfDucsAdapter.LocalState>>
                            physical;
                    try {
                        physical = projectedTagged(
                                endpoint, local.components,
                                local.problem.components(),
                                local.blockObservers, false);
                    } catch (IllegalArgumentException unprojectable) {
                        selected = false;
                        break;
                    }
                    LinkedHashMap<String, Long> testers =
                            new LinkedHashMap<String, Long>();
                    for (String id : local.problem.newRequirementIds()) {
                        Long state = endpoint.testerStates().get(id);
                        if (state == null) {
                            throw new IllegalArgumentException(
                                    "new endpoint omits local tester " + id);
                        }
                        testers.put(id, state);
                    }
                    String key = goalProjectionKey(
                            PhysicalState.of(physical), testers);
                    if (!choices.get(tuple.size()).contains(key)) {
                        selected = false;
                        break;
                    }
                    tuple.add(key);
                }
                if (selected) {
                    actual.add(Collections.unmodifiableList(tuple));
                }
            }
            return actual.equals(expected);
        }

        /**
         * Fail-closed transport gate from the source contract to the local
         * witnesses.  It checks exact endpoint projections, conditional-exact
         * activation quotients, action/frame classification, and a unique
         * load endpoint for every certificate-reachable terminal tuple.
         */
        private TransportReport verifyTransport(List<LocalResult> locals) {
            validateActionPartition(locals);
            validateExactEndpointProjection(locals);
            ActivationCensus activation = validateActivationQuotients(locals);
            List<BlockObserverRelation> relation =
                    blockObserverRelations(locals);
            return validateCertificateTerminalAssembler(
                    locals, activation, relation);
        }

        private void validateActionPartition(List<LocalResult> locals) {
            Map<String, Set<Integer>> owners = actionOwners();
            for (String action : normalActions) {
                Set<Integer> support = owners.get(action);
                if (support == null || support.isEmpty()) continue;
                int matches = 0;
                for (LocalResult local : locals) {
                    if (new LinkedHashSet<Integer>(local.components)
                            .containsAll(support)) matches++;
                }
                if (matches != 1) {
                    throw new IllegalArgumentException(
                            "normal event is not assigned to exactly one block: "
                                    + action + "/" + support);
                }
            }
        }

        private void validateExactEndpointProjection(
                List<LocalResult> locals) {
            for (MtsaRevisedOtfDucsAdapter.EndpointState endpoint
                    : oldEndpoint.reachableStates()) {
                for (LocalResult local : locals) {
                    projectedTagged(endpoint, local.components,
                            local.problem.components(), local.blockObservers,
                            true);
                }
            }
            for (MtsaRevisedOtfDucsAdapter.EndpointState endpoint
                    : loadableNew) {
                for (LocalResult local : locals) {
                    try {
                        projectedTagged(endpoint, local.components,
                                local.problem.components(),
                                local.blockObservers, false);
                    } catch (IllegalArgumentException outsideRefinedSlice) {
                        break;
                    }
                }
            }
        }

        private ActivationCensus validateActivationQuotients(
                List<LocalResult> locals) {
            int testerCount = 0;
            int relationPairCount = 0;
            for (LocalResult local : locals) {
                for (MtsaRevisedOtfDucsAdapter.TesterRecord localTester
                        : local.dormantNewTesters()) {
                    testerCount++;
                    MtsaRevisedOtfDucsAdapter.TesterRecord globalTester =
                            testerById(newTesters, localTester.id);
                    List<Integer> globalIndices =
                            MtsaRevisedOtfDucsAdapter.observerIndicesForTester(
                                    globalTester, observers,
                                    source.getSafetyComponentsMap());
                    List<Integer> localIndices =
                            MtsaRevisedOtfDucsAdapter.observerIndicesForTester(
                                    localTester, local.blockObservers,
                                    source.getSafetyComponentsMap());
                    List<MtsaRevisedOtfDucsAdapter.Observer> globalRelevant =
                            observersAtIndices(observers, globalIndices);
                    List<MtsaRevisedOtfDucsAdapter.Observer> localRelevant =
                            observersAtIndices(
                                    local.blockObservers, localIndices);
                    if (globalRelevant.size() != localRelevant.size()) {
                        throw new IllegalArgumentException(
                                "activation quotient observer arity differs for "
                                        + globalTester.sourceName);
                    }
                    List<Integer> signatureIndices =
                            sequentialIndices(globalRelevant.size());
                    Map<List<Integer>, Integer> mapping =
                            source.getSafetyStateMapping().get(
                                    globalTester.source);
                    LinkedHashSet<ObserverPair> seen =
                            new LinkedHashSet<ObserverPair>();
                    Deque<ObserverPair> queue = new ArrayDeque<ObserverPair>();
                    for (MtsaRevisedOtfDucsAdapter.EndpointState endpoint
                            : oldEndpoint.reachableStates()) {
                        List<Long> globalValues = endpoint.localStates().get(0)
                                .observerStates();
                        List<Long> relevantValues = valuesAtIndices(
                                globalValues, globalIndices);
                        ObserverPair initial = new ObserverPair(
                                relevantValues, relevantValues);
                        if (seen.add(initial)) queue.add(initial);
                    }
                    while (!queue.isEmpty()) {
                        ObserverPair pair = queue.removeFirst();
                        Long globalState = mappedActivation(
                                globalTester, signatureIndices, mapping,
                                pair.global);
                        Long localState = mappedActivation(
                                localTester, signatureIndices, mapping,
                                pair.local);
                        /*
                         * newActivation deliberately omits an error residual
                         * from its domain.  Such a local value is therefore a
                         * conservative non-activation, not an observable
                         * initialisation that must equal the source iota.
                         */
                        if (localState != null
                                && !localTester.tester.isError(localState)
                                && !localState.equals(globalState)) {
                            throw new IllegalArgumentException(
                                    "local activation quotient differs from "
                                            + "source iota for "
                                            + globalTester.sourceName
                                            + ": pair=" + pair
                                            + ", local=" + localState
                                            + ", global=" + globalState);
                        }
                        for (String action : normalActions) {
                            ObserverPair target = pair.step(
                                    globalRelevant, localRelevant, action);
                            if (seen.add(target)) queue.add(target);
                        }
                    }
                    relationPairCount += seen.size();
                }
            }
            return new ActivationCensus(testerCount, relationPairCount);
        }

        private static final class ActivationCensus {
            private final int testerCount;
            private final int relationPairCount;

            private ActivationCensus(int testerCount, int relationPairCount) {
                this.testerCount = testerCount;
                this.relationPairCount = relationPairCount;
            }
        }

        /**
         * Per-block abstraction relation between the source observer slice and
         * the projected local slice.  The terminal gate below accepts only a
         * singleton concrete fibre for every certificate terminal, which is a
         * conservative sufficient check and avoids enumerating the exponential
         * joint product of otherwise independent observer slices.
         */
        private List<BlockObserverRelation> blockObserverRelations(
                List<LocalResult> locals) {
            List<BlockObserverRelation> result =
                    new ArrayList<BlockObserverRelation>();
            for (LocalResult local : locals) {
                List<Integer> globalIndices = observerIndicesByName(
                        local.blockObservers);
                List<MtsaRevisedOtfDucsAdapter.Observer> globalRelevant =
                        observersAtIndices(observers, globalIndices);
                LinkedHashSet<ObserverPair> seen =
                        new LinkedHashSet<ObserverPair>();
                Deque<ObserverPair> queue = new ArrayDeque<ObserverPair>();
                for (MtsaRevisedOtfDucsAdapter.EndpointState endpoint
                        : oldEndpoint.reachableStates()) {
                    List<Long> global = valuesAtIndices(
                            endpoint.localStates().get(0).observerStates(),
                            globalIndices);
                    ObserverPair seed = new ObserverPair(global, global);
                    if (seen.add(seed)) {
                        requireObserverRelationBudget(seen.size());
                        queue.add(seed);
                    }
                }
                while (!queue.isEmpty()) {
                    ObserverPair sourceState = queue.removeFirst();
                    for (String action : normalActions) {
                        ObserverPair target = sourceState.step(
                                globalRelevant, local.blockObservers, action);
                        if (seen.add(target)) {
                            requireObserverRelationBudget(seen.size());
                            queue.add(target);
                        }
                    }
                }
                result.add(new BlockObserverRelation(
                        globalIndices, seen));
            }
            return Collections.unmodifiableList(result);
        }

        private List<Integer> observerIndicesByName(
                List<MtsaRevisedOtfDucsAdapter.Observer> selected) {
            List<Integer> result = new ArrayList<Integer>();
            for (MtsaRevisedOtfDucsAdapter.Observer observer : selected) {
                int match = -1;
                for (int index = 0; index < observers.size(); index++) {
                    if (observers.get(index).name.equals(observer.name)) {
                        if (match >= 0) {
                            throw new IllegalArgumentException(
                                    "ambiguous source observer name "
                                            + observer.name);
                        }
                        match = index;
                    }
                }
                if (match < 0) {
                    throw new IllegalArgumentException(
                            "projected observer is absent from source registry: "
                                    + observer.name);
                }
                result.add(Integer.valueOf(match));
            }
            return result;
        }

        private static void requireObserverRelationBudget(int size) {
            if (MAX_BLOCK_OBSERVER_RELATION_STATES <= 0
                    || size > MAX_BLOCK_OBSERVER_RELATION_STATES) {
                throw new IllegalArgumentException(
                        "block observer relation budget exhausted at " + size
                                + " states (limit "
                                + MAX_BLOCK_OBSERVER_RELATION_STATES + ")");
            }
        }

        private static final class BlockObserverRelation {
            private final List<Integer> globalIndices;
            private final Set<ObserverPair> pairs;

            private BlockObserverRelation(
                    Collection<Integer> globalIndices,
                    Collection<ObserverPair> pairs) {
                this.globalIndices = Collections.unmodifiableList(
                        new ArrayList<Integer>(globalIndices));
                this.pairs = Collections.unmodifiableSet(
                        new LinkedHashSet<ObserverPair>(pairs));
            }

            private Set<List<Long>> concreteFiber(List<Long> local) {
                LinkedHashSet<List<Long>> result =
                        new LinkedHashSet<List<Long>>();
                for (ObserverPair pair : pairs) {
                    if (pair.local.equals(local)) result.add(pair.global);
                }
                return Collections.unmodifiableSet(result);
            }
        }

        private static MtsaRevisedOtfDucsAdapter.TesterRecord testerById(
                List<MtsaRevisedOtfDucsAdapter.TesterRecord> values,
                String id) {
            for (MtsaRevisedOtfDucsAdapter.TesterRecord value : values) {
                if (value.id.equals(id)) return value;
            }
            throw new IllegalArgumentException("unknown tester id " + id);
        }

        private static List<MtsaRevisedOtfDucsAdapter.Observer>
                observersAtIndices(
                List<MtsaRevisedOtfDucsAdapter.Observer> values,
                List<Integer> indices) {
            List<MtsaRevisedOtfDucsAdapter.Observer> result =
                    new ArrayList<MtsaRevisedOtfDucsAdapter.Observer>();
            for (Integer index : indices) {
                if (index.intValue() < 0 || index.intValue() >= values.size()) {
                    throw new IllegalArgumentException(
                            "activation quotient observer index is out of range");
                }
                result.add(values.get(index.intValue()));
            }
            return result;
        }

        private static List<Long> valuesAtIndices(
                List<Long> values, List<Integer> indices) {
            List<Long> result = new ArrayList<Long>();
            for (Integer index : indices) {
                if (index.intValue() < 0 || index.intValue() >= values.size()) {
                    throw new IllegalArgumentException(
                            "activation quotient seed is out of range");
                }
                result.add(values.get(index.intValue()));
            }
            return result;
        }

        private static List<Integer> sequentialIndices(int size) {
            List<Integer> result = new ArrayList<Integer>();
            for (int index = 0; index < size; index++) {
                result.add(Integer.valueOf(index));
            }
            return result;
        }

        private static List<Long> initialStates(
                List<MtsaRevisedOtfDucsAdapter.Observer> values) {
            List<Long> result = new ArrayList<Long>();
            for (MtsaRevisedOtfDucsAdapter.Observer value : values) {
                result.add(value.initialState);
            }
            return result;
        }

        private static Long mappedActivation(
                MtsaRevisedOtfDucsAdapter.TesterRecord tester,
                List<Integer> indices,
                Map<List<Integer>, Integer> mapping,
                List<Long> observerStates) {
            if (indices.isEmpty() || mapping == null) {
                return tester.tester.initialState();
            }
            List<Integer> signature = new ArrayList<Integer>();
            for (Integer index : indices) {
                if (index.intValue() < 0
                        || index.intValue() >= observerStates.size()) {
                    return null;
                }
                signature.add(Integer.valueOf(
                        observerStates.get(index.intValue()).intValue()));
            }
            Integer mapped = mapping.get(signature);
            if (mapped == null) return null;
            Long state = Long.valueOf(mapped.longValue());
            return tester.tester.states().contains(state) ? state : null;
        }

        private TransportReport validateCertificateTerminalAssembler(
                List<LocalResult> locals,
                ActivationCensus activation,
                List<BlockObserverRelation> relations) {
            List<List<GoalSignature<
                    MtsaRevisedOtfDucsAdapter.LocalState, Long>>> reached =
                    new ArrayList<List<GoalSignature<
                            MtsaRevisedOtfDucsAdapter.LocalState, Long>>>();
            for (LocalResult local : locals) {
                if (!local.result.isWinning()) return TransportReport.notRun();
                LinkedHashSet<GoalSignature<
                        MtsaRevisedOtfDucsAdapter.LocalState, Long>> goals =
                        new LinkedHashSet<GoalSignature<
                                MtsaRevisedOtfDucsAdapter.LocalState, Long>>();
                for (GoalSignature<MtsaRevisedOtfDucsAdapter.LocalState, Long>
                        goal : local.result.winningCertificate()
                                .goalMatches().values()) {
                    goals.add(goal);
                }
                if (goals.isEmpty()) return TransportReport.notRun();
                reached.add(new ArrayList<GoalSignature<
                        MtsaRevisedOtfDucsAdapter.LocalState, Long>>(goals));
            }

            List<List<GoalSignature<
                    MtsaRevisedOtfDucsAdapter.LocalState, Long>>> terminals =
                    new ArrayList<List<GoalSignature<
                            MtsaRevisedOtfDucsAdapter.LocalState, Long>>>();
            cartesianGoals(
                    reached, 0,
                    new ArrayList<GoalSignature<
                            MtsaRevisedOtfDucsAdapter.LocalState, Long>>(),
                    terminals);

            LinkedHashMap<EndpointProjection, SelectorChoice> selector =
                    new LinkedHashMap<EndpointProjection, SelectorChoice>();
            LinkedHashMap<EndpointProjection, LoadSelectorReceipt>
                    selectorReceipts =
                    new LinkedHashMap<EndpointProjection, LoadSelectorReceipt>();
            int endpointIndex = 0;
            int loadEndpointCount = 0;
            for (MtsaRevisedOtfDucsAdapter.EndpointState endpoint
                    : newEndpoint.reachableStates()) {
                String endpointId = String.format("new-%08d", endpointIndex++);
                if (!loadableNew.contains(endpoint)) continue;
                loadEndpointCount++;
                EndpointProjection key = new EndpointProjection(
                        endpoint.localStates(), endpoint.testerStates());
                if (!selector.containsKey(key)) {
                    selector.put(key, new SelectorChoice(
                            endpointId, endpoint.controllerState()));
                    List<Long> componentRawStates = new ArrayList<Long>();
                    for (MtsaRevisedOtfDucsAdapter.LocalState state
                            : endpoint.localStates()) {
                        componentRawStates.add(Long.valueOf(state.rawState()));
                    }
                    List<Long> observerStates = endpoint.localStates().isEmpty()
                            ? Collections.<Long>emptyList()
                            : endpoint.localStates().get(0).observerStates();
                    selectorReceipts.put(key, new LoadSelectorReceipt(
                            endpointId,
                            endpoint.controllerState(),
                            componentRawStates,
                            observerStates,
                            new java.util.TreeMap<String, Long>(
                                    endpoint.testerStates())));
                }
            }

            List<TerminalAssembly> assemblies =
                    new ArrayList<TerminalAssembly>();
            List<ObserverRelationReceipt> relationReceipts =
                    new ArrayList<ObserverRelationReceipt>();
            int fiberCount = 0;
            int relationPairCount = 0;
            for (int blockIndex = 0;
                    blockIndex < relations.size(); blockIndex++) {
                BlockObserverRelation relation = relations.get(blockIndex);
                relationPairCount += relation.pairs.size();
                List<ObserverRelationPair> pairs =
                        new ArrayList<ObserverRelationPair>();
                for (ObserverPair pair : relation.pairs) {
                    pairs.add(new ObserverRelationPair(
                            pair.global, pair.local));
                }
                relationReceipts.add(new ObserverRelationReceipt(
                        blockIndex, relation.globalIndices, pairs));
            }
            for (int terminalIndex = 0;
                    terminalIndex < terminals.size(); terminalIndex++) {
                List<GoalSignature<
                        MtsaRevisedOtfDucsAdapter.LocalState, Long>> terminal =
                        terminals.get(terminalIndex);
                List<Long> globalObservers = singletonTerminalObserverFiber(
                        terminal, relations);
                int fiberIndex = 0;
                {
                    EndpointProjection concrete = concreteTerminalProjection(
                            terminal, globalObservers, locals);
                    SelectorChoice choice = selector.get(concrete);
                    if (choice == null) {
                        throw new IllegalArgumentException(
                                "certificate terminal observer fibre is outside "
                                        + "the original loadable Goal: terminal="
                                        + terminalIndex + ", fibre=" + fiberIndex);
                    }
                    List<String> localGoalSignatureIds =
                            new ArrayList<String>();
                    for (GoalSignature<
                            MtsaRevisedOtfDucsAdapter.LocalState, Long> goal
                            : terminal) {
                        localGoalSignatureIds.add(goal.endpointId());
                    }
                    assemblies.add(new TerminalAssembly(
                            terminalIndex, fiberIndex,
                            localGoalSignatureIds,
                            globalObservers,
                            choice.endpointId, choice.controllerState));
                    fiberIndex++;
                    fiberCount++;
                }
            }

            return new TransportReport(
                    true,
                    activation.testerCount,
                    activation.relationPairCount,
                    relationPairCount,
                    selector.size(),
                    loadEndpointCount,
                    terminals.size(),
                    fiberCount,
                    relationReceipts,
                    selectorReceipts.values(),
                    assemblies);
        }

        private static final class SelectorChoice {
            private final String endpointId;
            private final long controllerState;

            private SelectorChoice(String endpointId, long controllerState) {
                this.endpointId = endpointId;
                this.controllerState = controllerState;
            }
        }

        private List<Long> singletonTerminalObserverFiber(
                List<GoalSignature<
                        MtsaRevisedOtfDucsAdapter.LocalState, Long>> terminal,
                List<BlockObserverRelation> relations) {
            if (terminal.size() != relations.size()) {
                throw new IllegalArgumentException(
                        "terminal/relation block counts differ");
            }
            Long[] global = new Long[observers.size()];
            for (int block = 0; block < terminal.size(); block++) {
                if (terminal.get(block).physicalState().size() == 0) {
                    throw new IllegalArgumentException(
                            "terminal has no physical component");
                }
                List<Long> terminalObservers = terminal.get(block)
                        .physicalState().component(0).state().observerStates();
                BlockObserverRelation relation = relations.get(block);
                Set<List<Long>> fiber =
                        relation.concreteFiber(terminalObservers);
                if (fiber.size() != 1) {
                    throw new IllegalArgumentException(
                            "certificate terminal observer fibre is not "
                                    + "singleton for block " + block
                                    + ": size=" + fiber.size());
                }
                List<Long> values = fiber.iterator().next();
                if (values.size() != relation.globalIndices.size()) {
                    throw new IllegalArgumentException(
                            "terminal observer fibre arity differs");
                }
                for (int offset = 0; offset < values.size(); offset++) {
                    int index = relation.globalIndices.get(offset).intValue();
                    Long previous = global[index];
                    Long value = values.get(offset);
                    if (previous != null && !previous.equals(value)) {
                        throw new IllegalArgumentException(
                                "overlapping observer fibres disagree at "
                                        + observers.get(index).name);
                    }
                    global[index] = value;
                }
            }
            List<Long> result = new ArrayList<Long>();
            for (int index = 0; index < global.length; index++) {
                if (global[index] == null) {
                    throw new IllegalArgumentException(
                            "terminal abstraction does not cover source observer "
                                    + observers.get(index).name);
                }
                result.add(global[index]);
            }
            return Collections.unmodifiableList(result);
        }

        private EndpointProjection concreteTerminalProjection(
                List<GoalSignature<
                        MtsaRevisedOtfDucsAdapter.LocalState, Long>> terminal,
                List<Long> globalObservers,
                List<LocalResult> locals) {
            MtsaRevisedOtfDucsAdapter.LocalState[] physical =
                    new MtsaRevisedOtfDucsAdapter.LocalState[rawOld.size()];
            LinkedHashMap<String, Long> testers =
                    new LinkedHashMap<String, Long>();
            for (int block = 0; block < locals.size(); block++) {
                LocalResult local = locals.get(block);
                GoalSignature<MtsaRevisedOtfDucsAdapter.LocalState, Long>
                        goal = terminal.get(block);
                if (goal.physicalState().size() != local.components.size()) {
                    throw new IllegalArgumentException(
                            "terminal physical arity differs from its block");
                }
                for (int offset = 0;
                        offset < local.components.size(); offset++) {
                    TaggedState<MtsaRevisedOtfDucsAdapter.LocalState> state =
                            goal.physicalState().component(offset);
                    if (!state.isNew()) {
                        throw new IllegalArgumentException(
                                "terminal refinement contains an old component");
                    }
                    int globalIndex = local.components.get(offset).intValue();
                    Collection<Long> observerValues = globalIndex == 0
                            ? globalObservers : Collections.<Long>emptyList();
                    physical[globalIndex] =
                            new MtsaRevisedOtfDucsAdapter.LocalState(
                                    Long.valueOf(state.state().rawState()),
                                    observerValues);
                }
                for (Map.Entry<String, Long> entry
                        : goal.newRequirementStates().entrySet()) {
                    if (testers.put(entry.getKey(), entry.getValue()) != null) {
                        throw new IllegalArgumentException(
                                "new tester belongs to more than one block: "
                                        + entry.getKey());
                    }
                }
            }
            List<MtsaRevisedOtfDucsAdapter.LocalState> physicalList =
                    new ArrayList<MtsaRevisedOtfDucsAdapter.LocalState>();
            for (int index = 0; index < physical.length; index++) {
                if (physical[index] == null) {
                    throw new IllegalArgumentException(
                            "terminal partition omits component " + index);
                }
                physicalList.add(physical[index]);
            }
            LinkedHashSet<String> expectedTesterIds =
                    new LinkedHashSet<String>();
            for (MtsaRevisedOtfDucsAdapter.TesterRecord tester : newTesters) {
                expectedTesterIds.add(tester.id);
            }
            if (!testers.keySet().equals(expectedTesterIds)) {
                throw new IllegalArgumentException(
                        "terminal partition does not cover every new tester");
            }
            return new EndpointProjection(physicalList, testers);
        }

        private static void cartesianGoals(
                List<List<GoalSignature<
                        MtsaRevisedOtfDucsAdapter.LocalState, Long>>> choices,
                int index,
                List<GoalSignature<
                        MtsaRevisedOtfDucsAdapter.LocalState, Long>> current,
                List<List<GoalSignature<
                        MtsaRevisedOtfDucsAdapter.LocalState, Long>>> output) {
            if (index == choices.size()) {
                output.add(Collections.unmodifiableList(
                        new ArrayList<GoalSignature<
                                MtsaRevisedOtfDucsAdapter.LocalState, Long>>(
                                current)));
                return;
            }
            for (GoalSignature<MtsaRevisedOtfDucsAdapter.LocalState, Long>
                    choice : choices.get(index)) {
                current.add(choice);
                cartesianGoals(choices, index + 1, current, output);
                current.remove(current.size() - 1);
            }
        }

        private List<Long> selectObserverValues(
                List<MtsaRevisedOtfDucsAdapter.Observer> selected,
                List<Long> globalValues) {
            List<Long> result = new ArrayList<Long>();
            for (MtsaRevisedOtfDucsAdapter.Observer observer : selected) {
                int index = -1;
                for (int candidate = 0; candidate < observers.size(); candidate++) {
                    if (observers.get(candidate).name.equals(observer.name)) {
                        index = candidate;
                        break;
                    }
                }
                if (index < 0 || index >= globalValues.size()) {
                    throw new IllegalArgumentException(
                            "observer quotient seed is outside source registry");
                }
                result.add(globalValues.get(index));
            }
            return result;
        }

        private static final class ObserverPair {
            private final List<Long> global;
            private final List<Long> local;

            private ObserverPair(List<Long> global, List<Long> local) {
                this.global = Collections.unmodifiableList(
                        new ArrayList<Long>(global));
                this.local = Collections.unmodifiableList(
                        new ArrayList<Long>(local));
            }

            private ObserverPair step(
                    List<MtsaRevisedOtfDucsAdapter.Observer> globalObservers,
                    List<MtsaRevisedOtfDucsAdapter.Observer> localObservers,
                    String action) {
                List<Long> globalTarget = new ArrayList<Long>();
                for (int index = 0; index < globalObservers.size(); index++) {
                    globalTarget.add(globalObservers.get(index).stepOrStutter(
                            global.get(index), action));
                }
                List<Long> localTarget = new ArrayList<Long>();
                for (int index = 0; index < localObservers.size(); index++) {
                    localTarget.add(localObservers.get(index).stepOrStutter(
                            local.get(index), action));
                }
                return new ObserverPair(globalTarget, localTarget);
            }

            @Override public boolean equals(Object other) {
                if (!(other instanceof ObserverPair)) return false;
                ObserverPair that = (ObserverPair) other;
                return global.equals(that.global) && local.equals(that.local);
            }

            @Override public int hashCode() {
                return Objects.hash(global, local);
            }

            @Override public String toString() {
                return "(" + global + " => " + local + ")";
            }
        }

        private static void cartesianStrings(
                List<List<String>> choices,
                int index,
                List<String> current,
                Set<List<String>> output) {
            if (index == choices.size()) {
                output.add(Collections.unmodifiableList(
                        new ArrayList<String>(current)));
                return;
            }
            for (String choice : choices.get(index)) {
                current.add(choice);
                cartesianStrings(choices, index + 1, current, output);
                current.remove(current.size() - 1);
            }
        }

        private static String goalProjectionKey(
                GoalSignature<MtsaRevisedOtfDucsAdapter.LocalState, Long>
                        goal) {
            return goalProjectionKey(
                    goal.physicalState(), goal.newRequirementStates());
        }

        private static String goalProjectionKey(
                PhysicalState<MtsaRevisedOtfDucsAdapter.LocalState> physical,
                Map<String, Long> testers) {
            return physical.toString() + ":" + new java.util.TreeMap<String,
                    Long>(testers).toString();
        }

        private Map<String, Set<Integer>> updateOwnersForPartition() {
            Map<String, Set<Integer>> normalOwners = actionOwners();
            LinkedHashMap<String, Set<Integer>> result =
                    new LinkedHashMap<String, Set<Integer>>();
            for (int index = 0; index < rawOld.size(); index++) {
                String action = MtsaRevisedOtfDucsAdapter
                        .requireReconfigureAction(protocol, index);
                result.put(action, union(
                        result.get(action), singleton(index)));
            }
            boolean changed;
            do {
                changed = false;
                for (MtsaRevisedOtfDucsAdapter.TesterRecord tester
                        : allTesters()) {
                    if (tester.updateAction == null) continue;
                    Set<Integer> support = testerSupport(
                            tester, normalOwners, result);
                    Set<Integer> merged = union(
                            result.get(tester.updateAction), support);
                    if (!merged.equals(result.get(tester.updateAction))) {
                        result.put(tester.updateAction, merged);
                        changed = true;
                    }
                }
            } while (changed);
            return result;
        }

        private void validateOwnerlessActions(
                Map<String, Set<Integer>> normalOwners) {
            for (Map.Entry<String, Set<Integer>> entry
                    : normalOwners.entrySet()) {
                if (!entry.getValue().isEmpty()) continue;
                String action = entry.getKey();
                boolean testerEffect = false;
                for (MtsaRevisedOtfDucsAdapter.TesterRecord tester
                        : allTesters()) {
                    if (effectiveTesterActions(tester.tester)
                            .contains(action)) {
                        testerEffect = true;
                        break;
                    }
                }
                boolean observerEffect = false;
                for (MtsaRevisedOtfDucsAdapter.Observer observer : observers) {
                    if (effectiveObserverActions(observer).contains(action)) {
                        observerEffect = true;
                        break;
                    }
                }
                if (!controllableNormal.contains(action)
                        || testerEffect || observerEffect) {
                    throw new IllegalArgumentException(
                            "ownerless normal event is not a disable-able pure "
                                    + "stutter: " + action);
                }
            }
        }

        private List<MtsaRevisedOtfDucsAdapter.TesterRecord> localTesters(
                Collection<MtsaRevisedOtfDucsAdapter.TesterRecord> testers,
                Collection<Integer> block,
                Map<String, Set<Integer>> normalOwners,
                Map<String, Set<Integer>> updateOwners) {
            Set<Integer> blockSet = new LinkedHashSet<Integer>(block);
            List<MtsaRevisedOtfDucsAdapter.TesterRecord> result =
                    new ArrayList<MtsaRevisedOtfDucsAdapter.TesterRecord>();
            for (MtsaRevisedOtfDucsAdapter.TesterRecord tester : testers) {
                Set<Integer> support = testerSupport(
                        tester, normalOwners, updateOwners);
                if (support.isEmpty()) {
                    throw new IllegalArgumentException(
                            "opaque tester has no native component support: "
                                    + tester.sourceName);
                }
                if (blockSet.containsAll(support)) result.add(tester);
            }
            return result;
        }

        private List<MtsaRevisedOtfDucsAdapter.TesterRecord> projectTesters(
                Collection<MtsaRevisedOtfDucsAdapter.TesterRecord> selected,
                Set<String> blockCommon) {
            List<MtsaRevisedOtfDucsAdapter.TesterRecord> result =
                    new ArrayList<MtsaRevisedOtfDucsAdapter.TesterRecord>();
            for (MtsaRevisedOtfDucsAdapter.TesterRecord record : selected) {
                LinkedHashSet<String> actions = new LinkedHashSet<String>(
                        effectiveTesterActions(record.tester));
                actions.retainAll(blockCommon);
                SafetyTester.Builder<Long> builder = SafetyTester.<Long>builder()
                        .initialState(record.tester.initialState())
                        .addStates(record.tester.states())
                        .addActions(actions);
                for (Long error : record.tester.errorStates()) {
                    builder.addErrorState(error);
                }
                for (Long state : record.tester.states()) {
                    for (String action : actions) {
                        builder.addTransition(state, action,
                                record.tester.stepOrStutter(state, action));
                    }
                }
                MtsaRevisedOtfDucsAdapter.TesterRecord projected =
                        new MtsaRevisedOtfDucsAdapter.TesterRecord(
                                record.id, record.sourceName, record.role,
                                record.source, builder.build(),
                                record.boundaryState);
                projected.updateAction = record.updateAction;
                result.add(projected);
            }
            return result;
        }

        private List<MtsaRevisedOtfDucsAdapter.Observer> localObservers(
                Collection<MtsaRevisedOtfDucsAdapter.TesterRecord>
                        selectedNewTesters,
                Set<String> blockNormal) {
            LinkedHashSet<Integer> requiredIndices =
                    new LinkedHashSet<Integer>();
            LinkedHashSet<String> testerLanguage =
                    new LinkedHashSet<String>();
            for (MtsaRevisedOtfDucsAdapter.TesterRecord tester
                    : selectedNewTesters) {
                requiredIndices.addAll(
                        MtsaRevisedOtfDucsAdapter.observerIndicesForTester(
                                tester, observers,
                                source.getSafetyComponentsMap()));
                testerLanguage.addAll(effectiveTesterActions(tester.tester));
            }
            List<MtsaRevisedOtfDucsAdapter.Observer> result =
                    new ArrayList<MtsaRevisedOtfDucsAdapter.Observer>();
            for (int index = 0; index < observers.size(); index++) {
                if (!requiredIndices.contains(Integer.valueOf(index))) {
                    continue;
                }
                MtsaRevisedOtfDucsAdapter.Observer observer =
                        observers.get(index);
                LinkedHashSet<String> localAlphabet =
                        new LinkedHashSet<String>(observer.alphabet);
                localAlphabet.retainAll(testerLanguage);
                localAlphabet.retainAll(blockNormal);
                result.add(new MtsaRevisedOtfDucsAdapter.Observer(
                        observer.name, observer.source,
                        observer.initialState,
                        Collections.unmodifiableSet(localAlphabet)));
            }
            return result;
        }

        private List<VersionedComponent<MtsaRevisedOtfDucsAdapter.LocalState>>
                localComponents(
                List<Integer> block,
                List<MtsaRevisedOtfDucsAdapter.Observer> blockObservers,
                List<Long> initialObserverStates,
                Set<String> blockNormal) {
            List<VersionedComponent<MtsaRevisedOtfDucsAdapter.LocalState>>
                    result = new ArrayList<VersionedComponent<
                            MtsaRevisedOtfDucsAdapter.LocalState>>();
            for (int localIndex = 0; localIndex < block.size(); localIndex++) {
                int globalIndex = block.get(localIndex).intValue();
                if (localIndex == 0) {
                    result.add(augmentedComponent(
                            oldMachines.get(globalIndex), globalIndex,
                            projectRaw(rawOld.get(globalIndex), blockNormal),
                            projectRaw(rawNew.get(globalIndex), blockNormal),
                            rawTransfers.get(globalIndex), protocol,
                            blockObservers, initialObserverStates,
                            blockNormal));
                } else {
                    result.add(rawComponent(
                            oldMachines.get(globalIndex), globalIndex,
                            projectRaw(rawOld.get(globalIndex), blockNormal),
                            projectRaw(rawNew.get(globalIndex), blockNormal),
                            rawTransfers.get(globalIndex), protocol));
                }
            }
            return result;
        }

        private static FiniteLts<Long> projectRaw(
                FiniteLts<Long> source, Set<String> actions) {
            LinkedHashSet<String> kept = new LinkedHashSet<String>(
                    source.alphabet());
            kept.retainAll(actions);
            FiniteLts.Builder<Long> builder = FiniteLts.<Long>builder(
                    source.initialState()).addStates(source.states())
                    .addActions(kept);
            for (Long state : source.states()) {
                for (String action : kept) {
                    for (Long target : source.successors(state, action)) {
                        builder.addTransition(state, action, target);
                    }
                }
            }
            return builder.build();
        }

        private List<InitialSnapshot<MtsaRevisedOtfDucsAdapter.LocalState, Long>>
                projectRoots(
                List<Integer> block,
                List<VersionedComponent<MtsaRevisedOtfDucsAdapter.LocalState>>
                        components,
                List<MtsaRevisedOtfDucsAdapter.Observer> blockObservers,
                List<MtsaRevisedOtfDucsAdapter.TesterRecord> blockOld,
                List<MtsaRevisedOtfDucsAdapter.TesterRecord> blockUpdateTesters) {
            LinkedHashSet<InitialSnapshot<
                    MtsaRevisedOtfDucsAdapter.LocalState, Long>> result =
                    new LinkedHashSet<InitialSnapshot<
                            MtsaRevisedOtfDucsAdapter.LocalState, Long>>();
            for (MtsaRevisedOtfDucsAdapter.EndpointState endpoint
                    : oldEndpoint.reachableStates()) {
                List<TaggedState<MtsaRevisedOtfDucsAdapter.LocalState>> local =
                        projectedTagged(endpoint, block, components,
                                blockObservers, true);
                LinkedHashMap<String, Long> testers =
                        new LinkedHashMap<String, Long>();
                for (MtsaRevisedOtfDucsAdapter.TesterRecord tester : blockOld) {
                    testers.put(tester.id,
                            endpoint.testerStates().get(tester.id));
                }
                result.add(new InitialSnapshot<
                        MtsaRevisedOtfDucsAdapter.LocalState, Long>(
                        PhysicalState.of(local), testers));
            }
            return new ArrayList<InitialSnapshot<
                    MtsaRevisedOtfDucsAdapter.LocalState, Long>>(result);
        }

        private List<GoalSignature<MtsaRevisedOtfDucsAdapter.LocalState, Long>>
                projectGoals(
                List<Integer> block,
                List<VersionedComponent<MtsaRevisedOtfDucsAdapter.LocalState>>
                        components,
                List<MtsaRevisedOtfDucsAdapter.Observer> blockObservers,
                List<MtsaRevisedOtfDucsAdapter.TesterRecord> blockNew) {
            LinkedHashMap<String, GoalSignature<
                    MtsaRevisedOtfDucsAdapter.LocalState, Long>> unique =
                    new LinkedHashMap<String, GoalSignature<
                            MtsaRevisedOtfDucsAdapter.LocalState, Long>>();
            for (MtsaRevisedOtfDucsAdapter.EndpointState endpoint
                    : loadableNew) {
                List<TaggedState<MtsaRevisedOtfDucsAdapter.LocalState>> local;
                try {
                    local = projectedTagged(endpoint, block, components,
                            blockObservers, false);
                } catch (IllegalArgumentException outsideRefinedSlice) {
                    continue;
                }
                LinkedHashMap<String, Long> testers =
                        new LinkedHashMap<String, Long>();
                for (MtsaRevisedOtfDucsAdapter.TesterRecord tester : blockNew) {
                    testers.put(tester.id,
                            endpoint.testerStates().get(tester.id));
                }
                String key = local.toString() + ":" + testers;
                if (!unique.containsKey(key)) {
                    unique.put(key, new GoalSignature<
                            MtsaRevisedOtfDucsAdapter.LocalState, Long>(
                            "block-goal-" + unique.size(),
                            PhysicalState.of(local), testers));
                }
            }
            return new ArrayList<GoalSignature<
                    MtsaRevisedOtfDucsAdapter.LocalState, Long>>(unique.values());
        }

        private List<TaggedState<MtsaRevisedOtfDucsAdapter.LocalState>>
                projectedTagged(
                MtsaRevisedOtfDucsAdapter.EndpointState endpoint,
                List<Integer> block,
                List<VersionedComponent<MtsaRevisedOtfDucsAdapter.LocalState>>
                        components,
                List<MtsaRevisedOtfDucsAdapter.Observer> blockObservers,
                boolean old) {
            List<TaggedState<MtsaRevisedOtfDucsAdapter.LocalState>> result =
                    new ArrayList<TaggedState<
                            MtsaRevisedOtfDucsAdapter.LocalState>>();
            for (int localIndex = 0; localIndex < block.size(); localIndex++) {
                int globalIndex = block.get(localIndex).intValue();
                MtsaRevisedOtfDucsAdapter.LocalState original =
                        endpoint.localStates().get(globalIndex);
                MtsaRevisedOtfDucsAdapter.LocalState projected;
                if (localIndex == 0) {
                    List<Long> selectedObservers = selectedObserverStates(
                            components.get(localIndex), blockObservers,
                            endpoint.localStates().get(0).observerStates());
                    projected = findLocalState(
                            old ? components.get(localIndex).oldLts()
                                    : components.get(localIndex).newLts(),
                            original.rawState(),
                            selectedObservers);
                } else {
                    projected = findLocalState(
                            old ? components.get(localIndex).oldLts()
                                    : components.get(localIndex).newLts(),
                            original.rawState(), Collections.<Long>emptyList());
                }
                result.add(old ? TaggedState.oldState(projected)
                        : TaggedState.newState(projected));
            }
            return result;
        }

        private List<Long> selectedObserverStates(
                VersionedComponent<MtsaRevisedOtfDucsAdapter.LocalState>
                        component,
                List<MtsaRevisedOtfDucsAdapter.Observer> blockObservers,
                List<Long> allObserverStates) {
            int arity = component.oldLts().states().iterator().next()
                    .observerStates().size();
            List<Long> selected = new ArrayList<Long>();
            for (MtsaRevisedOtfDucsAdapter.Observer local : blockObservers) {
                int global = -1;
                for (int index = 0; index < observers.size(); index++) {
                    if (observers.get(index).name.equals(local.name)) {
                        global = index;
                        break;
                    }
                }
                if (global < 0 || global >= allObserverStates.size()) {
                    throw new IllegalArgumentException(
                            "local observer is absent from native registry");
                }
                selected.add(allObserverStates.get(global));
            }
            if (selected.size() != arity) {
                throw new IllegalArgumentException(
                        "local observer projection arity mismatch");
            }
            return selected;
        }

        private MtsaRevisedOtfDucsAdapter.LocalState findLocalState(
                FiniteLts<MtsaRevisedOtfDucsAdapter.LocalState> lts,
                long raw,
                List<Long> observers) {
            for (MtsaRevisedOtfDucsAdapter.LocalState state : lts.states()) {
                if (state.rawState() == raw
                        && state.observerStates().equals(observers)) return state;
            }
            throw new IllegalArgumentException(
                    "exact projected endpoint state is absent from local LTS: "
                            + raw + "/" + observers);
        }

        private Set<String> enabledUncontrollableAtGoal(
                List<VersionedComponent<MtsaRevisedOtfDucsAdapter.LocalState>>
                        components,
                GoalSignature<MtsaRevisedOtfDucsAdapter.LocalState, Long> goal,
                Set<String> localNormal) {
            LinkedHashSet<String> enabled = new LinkedHashSet<String>();
            for (String action : localNormal) {
                if (controllableNormal.contains(action)) continue;
                boolean participant = false;
                boolean blocked = false;
                for (int index = 0; index < components.size(); index++) {
                    VersionedComponent<MtsaRevisedOtfDucsAdapter.LocalState>
                            component = components.get(index);
                    TaggedState<MtsaRevisedOtfDucsAdapter.LocalState> state =
                            goal.physicalState().component(index);
                    if (!component.environmentHasAction(
                            state.version(), action)) continue;
                    participant = true;
                    FiniteLts<MtsaRevisedOtfDucsAdapter.LocalState> active =
                            component.newLts();
                    if (active.hasAction(action)
                            && active.successors(state.state(), action).isEmpty()) {
                        blocked = true;
                    }
                }
                if (participant && !blocked) enabled.add(action);
            }
            return enabled;
        }

        private void addLocalPrecedence(
                FineGrainedUpdateProblem.Builder<
                        MtsaRevisedOtfDucsAdapter.LocalState, Long> builder,
                Set<String> localUpdateActions) {
            for (UpdateProtocolSpec.PrecedenceEdge edge
                    : protocol.getPrecedenceEdges()) {
                if (localUpdateActions.contains(edge.before())
                        && localUpdateActions.contains(edge.after())) {
                    builder.addPrecedence(edge.before(), edge.after());
                } else if (localUpdateActions.contains(edge.before())
                        || localUpdateActions.contains(edge.after())) {
                    throw new IllegalArgumentException(
                            "cross-block precedence survived dependency closure: "
                                    + edge.before() + "<" + edge.after());
                }
            }
        }
    }

    private static VersionedComponent<MtsaRevisedOtfDucsAdapter.LocalState>
            rawComponent(
            CompactState machine,
            int index,
            FiniteLts<Long> rawOld,
            FiniteLts<Long> rawNew,
            Map<Integer, Set<Integer>> rawTransfer,
            UpdateProtocolSpec protocol) {
        FiniteLts<MtsaRevisedOtfDucsAdapter.LocalState> oldLts =
                MtsaRevisedOtfDucsAdapter.wrapRaw(rawOld);
        FiniteLts<MtsaRevisedOtfDucsAdapter.LocalState> newLts =
                MtsaRevisedOtfDucsAdapter.wrapRaw(rawNew);
        Map<MtsaRevisedOtfDucsAdapter.LocalState, Set<
                MtsaRevisedOtfDucsAdapter.LocalState>> transfer =
                new LinkedHashMap<MtsaRevisedOtfDucsAdapter.LocalState,
                        Set<MtsaRevisedOtfDucsAdapter.LocalState>>();
        for (Map.Entry<Integer, Set<Integer>> entry : rawTransfer.entrySet()) {
            LinkedHashSet<MtsaRevisedOtfDucsAdapter.LocalState> targets =
                    new LinkedHashSet<MtsaRevisedOtfDucsAdapter.LocalState>();
            for (Integer target : entry.getValue()) {
                targets.add(MtsaRevisedOtfDucsAdapter.LocalState.raw(
                        target.longValue()));
            }
            transfer.put(MtsaRevisedOtfDucsAdapter.LocalState.raw(
                    entry.getKey().longValue()), targets);
        }
        return new VersionedComponent<MtsaRevisedOtfDucsAdapter.LocalState>(
                MtsaRevisedOtfDucsAdapter.componentId(machine, index),
                oldLts, newLts, transfer,
                MtsaRevisedOtfDucsAdapter.requireReconfigureAction(
                        protocol, index));
    }

    private static VersionedComponent<MtsaRevisedOtfDucsAdapter.LocalState>
            augmentedComponent(
            CompactState machine,
            int index,
            FiniteLts<Long> rawOld,
            FiniteLts<Long> rawNew,
            Map<Integer, Set<Integer>> rawTransfer,
            UpdateProtocolSpec protocol,
            List<MtsaRevisedOtfDucsAdapter.Observer> observers,
            List<Long> initialObserverStates,
            Set<String> normalActions) {
        MtsaRevisedOtfDucsAdapter.LocalState initialOld =
                new MtsaRevisedOtfDucsAdapter.LocalState(
                        rawOld.initialState(), initialObserverStates);
        FiniteLts<MtsaRevisedOtfDucsAdapter.LocalState> oldLts =
                MtsaRevisedOtfDucsAdapter.buildAugmented(
                        rawOld, observers, normalActions,
                        initialOld, Collections.<
                                MtsaRevisedOtfDucsAdapter.LocalState>emptySet());
        LinkedHashSet<MtsaRevisedOtfDucsAdapter.LocalState> seeds =
                new LinkedHashSet<MtsaRevisedOtfDucsAdapter.LocalState>();
        seeds.add(new MtsaRevisedOtfDucsAdapter.LocalState(
                rawNew.initialState(), initialObserverStates));
        for (MtsaRevisedOtfDucsAdapter.LocalState oldState : oldLts.states()) {
            Set<Integer> targets = rawTransfer.get(
                    Integer.valueOf((int) oldState.rawState()));
            if (targets == null) continue;
            for (Integer target : targets) {
                seeds.add(new MtsaRevisedOtfDucsAdapter.LocalState(
                        Long.valueOf(target.longValue()),
                        oldState.observerStates()));
            }
        }
        FiniteLts<MtsaRevisedOtfDucsAdapter.LocalState> newLts =
                MtsaRevisedOtfDucsAdapter.buildAugmented(
                        rawNew, observers, normalActions,
                        new MtsaRevisedOtfDucsAdapter.LocalState(
                                rawNew.initialState(), initialObserverStates),
                        seeds);
        LinkedHashMap<MtsaRevisedOtfDucsAdapter.LocalState, Set<
                MtsaRevisedOtfDucsAdapter.LocalState>> transfer =
                new LinkedHashMap<MtsaRevisedOtfDucsAdapter.LocalState,
                        Set<MtsaRevisedOtfDucsAdapter.LocalState>>();
        for (MtsaRevisedOtfDucsAdapter.LocalState oldState : oldLts.states()) {
            Set<Integer> targets = rawTransfer.get(
                    Integer.valueOf((int) oldState.rawState()));
            if (targets == null) continue;
            LinkedHashSet<MtsaRevisedOtfDucsAdapter.LocalState> localTargets =
                    new LinkedHashSet<MtsaRevisedOtfDucsAdapter.LocalState>();
            for (Integer target : targets) {
                localTargets.add(new MtsaRevisedOtfDucsAdapter.LocalState(
                        Long.valueOf(target.longValue()),
                        oldState.observerStates()));
            }
            transfer.put(oldState, localTargets);
        }
        return new VersionedComponent<MtsaRevisedOtfDucsAdapter.LocalState>(
                MtsaRevisedOtfDucsAdapter.componentId(machine, index),
                oldLts, newLts, transfer,
                MtsaRevisedOtfDucsAdapter.requireReconfigureAction(
                        protocol, index), rawOld.alphabet(), rawNew.alphabet());
    }

    private static FiniteLts<Long> importController(
            MTS<Long, String> source,
            Set<String> normalActions,
            String label) {
        if (source == null) {
            throw new IllegalArgumentException(
                    "missing " + label + " endpoint controller");
        }
        FiniteLts<Long> imported = FiniteLts.fromMtsa(
                new LTSAdapter<Long, String>(
                        source, MTS.TransitionType.REQUIRED));
        FiniteLts.Builder<Long> builder =
                FiniteLts.<Long>builder(imported.initialState())
                        .addStates(imported.states());
        LinkedHashSet<String> alphabet =
                new LinkedHashSet<String>(imported.alphabet());
        alphabet.retainAll(normalActions);
        builder.addActions(alphabet);
        for (Map.Entry<Long, Map<String, Set<Long>>> state
                : imported.transitions().entrySet()) {
            for (Map.Entry<String, Set<Long>> action
                    : state.getValue().entrySet()) {
                if (!normalActions.contains(action.getKey())) {
                    throw new IllegalArgumentException(
                            label + " endpoint has a non-normal transition: "
                                    + action.getKey());
                }
                for (Long target : action.getValue()) {
                    builder.addTransition(
                            state.getKey(), action.getKey(), target);
                }
            }
        }
        return builder.build();
    }

    private static Set<Integer> singleton(int value) {
        return Collections.singleton(Integer.valueOf(value));
    }

    private static <T> Set<T> union(Set<T> left, Set<T> right) {
        LinkedHashSet<T> result = new LinkedHashSet<T>();
        if (left != null) result.addAll(left);
        if (right != null) result.addAll(right);
        return Collections.unmodifiableSet(result);
    }

    private static <T> Set<T> intersection(
            Collection<T> left, Collection<T> right) {
        LinkedHashSet<T> result = new LinkedHashSet<T>(left);
        result.retainAll(new LinkedHashSet<T>(right));
        return result;
    }

    private static final class Partition {
        private final List<List<Integer>> blocks;

        private Partition(Collection<List<Integer>> blocks) {
            List<List<Integer>> copy = new ArrayList<List<Integer>>();
            for (List<Integer> block : blocks) {
                copy.add(Collections.unmodifiableList(
                        new ArrayList<Integer>(block)));
            }
            Collections.sort(copy, new Comparator<List<Integer>>() {
                @Override
                public int compare(List<Integer> left, List<Integer> right) {
                    return Integer.compare(left.get(0), right.get(0));
                }
            });
            this.blocks = Collections.unmodifiableList(copy);
        }
    }

    private static final class UnionFind {
        private final int[] parent;

        private UnionFind(int size) {
            parent = new int[size];
            for (int index = 0; index < size; index++) parent[index] = index;
        }

        private int root(int value) {
            if (parent[value] != value) parent[value] = root(parent[value]);
            return parent[value];
        }

        private void join(int left, int right) {
            int a = root(left);
            int b = root(right);
            if (a != b) parent[Math.max(a, b)] = Math.min(a, b);
        }

        private List<List<Integer>> components() {
            LinkedHashMap<Integer, List<Integer>> values =
                    new LinkedHashMap<Integer, List<Integer>>();
            for (int index = 0; index < parent.length; index++) {
                int root = root(index);
                List<Integer> block = values.get(Integer.valueOf(root));
                if (block == null) {
                    block = new ArrayList<Integer>();
                    values.put(Integer.valueOf(root), block);
                }
                block.add(Integer.valueOf(index));
            }
            return new ArrayList<List<Integer>>(values.values());
        }
    }
}
