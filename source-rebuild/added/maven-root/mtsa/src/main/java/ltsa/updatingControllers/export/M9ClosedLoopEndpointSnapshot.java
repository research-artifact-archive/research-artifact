package ltsa.updatingControllers.export;

import MTSTools.ac.ic.doc.mtstools.model.MTS;
import MTSTools.ac.ic.doc.mtstools.model.impl.MTSImpl;
import ltsa.ac.ic.doc.mtstools.util.fsp.AutomataToMTSConverter;
import ltsa.lts.CompactState;
import ltsa.lts.CompositeState;
import ltsa.lts.EmptyLTSOuput;
import ltsa.lts.Analyser;
import ltsa.lts.LTSConstants;
import ltsa.lts.Options;

import java.util.Map;
import java.util.LinkedHashSet;
import java.util.Set;
import java.util.Vector;

/**
 * Decision-free materialization and validation of the exact Cnew and CLnew
 * endpoint bytes after the one authorized endpoint-GR result has been sealed
 * into an {@link M9EndpointStrategySnapshot}.  The only graph construction in
 * this class is LTSA plain parallel composition; it never invokes synthesis or
 * a fixed point.
 *
 * <p>The caller must supply the exact native Cnew CompactState emitted by the
 * same dispatcher invocation as the strategy snapshot.  The materializer
 * bridge is responsible for that object-identity/receipt binding; this class
 * independently checks its complete graph against the immutable plain-MTS
 * authority before composing it with the already admitted Enew bytes.</p>
 */
public final class M9ClosedLoopEndpointSnapshot {
	private final CompactStateEndpointAdmission.Admission enewAdmission;
	private final CompactStateEndpointAdmission.Admission cnewAdmission;
	private final CompactStateEndpointAdmission.Admission closedLoopAdmission;
	private final M9CompositionProvenance.Projection closedLoopAuthority;
	private final M9CompositionProvenance.TwoCoordinateProjection coordinates;

	private M9ClosedLoopEndpointSnapshot(
			CompactStateEndpointAdmission.Admission enewAdmission,
			CompactStateEndpointAdmission.Admission cnewAdmission,
			CompactStateEndpointAdmission.Admission closedLoopAdmission,
			M9CompositionProvenance.Projection closedLoopAuthority,
			M9CompositionProvenance.TwoCoordinateProjection coordinates) {
		this.enewAdmission = enewAdmission;
		this.cnewAdmission = cnewAdmission;
		this.closedLoopAdmission = closedLoopAdmission;
		this.closedLoopAuthority = closedLoopAuthority;
		this.coordinates = coordinates;
	}

	public static M9ClosedLoopEndpointSnapshot capture(
			CompactState materializedEnew,
			CompactStateEndpointAdmission.Admission enewAdmission,
			CompactState materializedCnew,
			M9EndpointStrategySnapshot strategy) {
		if (materializedEnew == null || enewAdmission == null
				|| materializedCnew == null || strategy == null) {
			throw new IllegalArgumentException(
					"Materialized Enew/Cnew bytes, admission, and strategy are required.");
		}
		if (enewAdmission.getNormalizedEndState() >= 0) {
			throw new IllegalArgumentException(
					"M9 Enew may not retain a terminal END state.");
		}
		requireLiveTreeMatches(
				materializedEnew, enewAdmission, "Enew");

		M9CompositionProvenance.Projection exactEnewAuthority = strategy
				.getEnvironmentPrefix().getPrefixProductAuthority();
		CompactStateEndpointAdmission.Admission exactEnewAdmission =
				CompactStateEndpointAdmission.admitComposed(
						materializedEnew, exactEnewAuthority, false);
		if (!CompactStateCanonicalTree.canonicalEquals(
				enewAdmission.getCanonicalTree(),
				exactEnewAdmission.getCanonicalTree())
				|| enewAdmission.isComposed() != exactEnewAdmission.isComposed()
				|| enewAdmission.getNormalizedEndState()
						!= exactEnewAdmission.getNormalizedEndState()) {
			throw new IllegalArgumentException(
					"Enew admission differs from the strategy prefix authority.");
		}
		enewAdmission = exactEnewAdmission;
		M9MtsSnapshot enewSource = exactEnewAuthority.getProductSnapshot();
		M9CompositionProvenance.requireAdmissionMatchesSource(
				enewAdmission, enewSource, "Enew");

		CompactStateEndpointAdmission.Admission cnewAdmission =
				CompactStateEndpointAdmission.admitPrimitive(
						materializedCnew, false);
		M9MtsSnapshot cnewSource = strategy.getPlainController();
		M9CompositionProvenance.requireAdmissionMatchesSource(
				cnewAdmission, cnewSource, "Cnew");
		requireCompositionPreflight(enewAdmission, cnewAdmission);
		requireRegisteredNativeCompositionProfile();

		Vector<CompactState> machines = new Vector<CompactState>(2);
		machines.add(materializedEnew);
		machines.add(materializedCnew);
		CompositeState closedLoop = new CompositeState("M9_CLNEW", machines);
		closedLoop.compose(new EmptyLTSOuput());
		if (closedLoop.composition == null) {
			throw new IllegalArgumentException(
					"Plain Enew/Cnew composition produced no finite endpoint.");
		}

		MTS<Long, String> enewMts = reconstruct(enewSource);
		MTS<Long, String> closedLoopMts = AutomataToMTSConverter.getInstance()
				.convert(closedLoop.composition);
		M9CompositionProvenance.Projection authority =
				M9CompositionProvenance.capture(closedLoopMts, enewMts);
		CompactStateEndpointAdmission.Admission closedLoopAdmission =
				CompactStateEndpointAdmission.admitComposed(
						closedLoop.composition, authority, false);
		M9CompositionProvenance.TwoCoordinateProjection coordinates =
				M9CompositionProvenance.requireTwoCoordinateConsistency(
						authority, closedLoopAdmission,
						enewAdmission, cnewAdmission, cnewSource,
						strategy.getControllerStateToEnewState());

		requireLiveTreeMatches(materializedEnew, enewAdmission, "Enew");
		requireLiveTreeMatches(materializedCnew, cnewAdmission, "Cnew");
		return new M9ClosedLoopEndpointSnapshot(
				enewAdmission, cnewAdmission, closedLoopAdmission,
				authority, coordinates);
	}

	private static MTS<Long, String> reconstruct(M9MtsSnapshot snapshot) {
		MTS<Long, String> result = new MTSImpl<Long, String>(
				Long.valueOf(snapshot.getInitialState()));
		result.addStates(snapshot.getStates());
		result.addActions(snapshot.getActions());
		for (Long source : snapshot.getStates()) {
			Map<String, Set<Long>> row = snapshot.getPost().get(source);
			for (Map.Entry<String, Set<Long>> bucket : row.entrySet()) {
				for (Long target : bucket.getValue()) {
					result.addRequired(source, bucket.getKey(), target);
				}
			}
		}
		M9MtsSnapshot.requireStableSourceEquals(result, snapshot);
		return result;
	}

	private static void requireCompositionPreflight(
			CompactStateEndpointAdmission.Admission enew,
			CompactStateEndpointAdmission.Admission cnew) {
		if (enew.getSnapshot().getName().equals(cnew.getSnapshot().getName())) {
			throw new IllegalArgumentException(
					"Enew and Cnew must have distinct direct-child role names.");
		}
		int enewStates = enew.getSnapshot().getStateCount();
		int cnewStates = cnew.getSnapshot().getStateCount();
		if (enewStates <= 0 || cnewStates <= 0
				|| enewStates > Integer.MAX_VALUE / cnewStates) {
			throw new IllegalArgumentException(
					"Enew/Cnew Cartesian state bound overflows the registered profile.");
		}
		int productStateBound = enewStates * cnewStates;
		Set<String> productActions = new LinkedHashSet<String>();
		for (CompactStateCanonicalSnapshot.Action action
				: enew.getSnapshot().getActions()) {
			productActions.add(action.getLabel());
		}
		for (CompactStateCanonicalSnapshot.Action action
				: cnew.getSnapshot().getActions()) {
			productActions.add(action.getLabel());
		}
		M9CompositionProvenance.requireProjectionBound(productStateBound, 2);
		M9MtsSnapshot.requireResourceCensus(
				0L, productActions.size(), 0L, 0L);
		M9CompositionProvenance.requireBucketBound(
				productStateBound, productActions.size());
		long visibleActions = productActions.contains("tau")
				? productActions.size() - 1L : productActions.size();
		long productTransitionBound = (long) productStateBound * visibleActions;
		long productTupleCells = ((long) productStateBound
				+ productTransitionBound) * 2L;
		CompactStateCanonicalTree.requireCombinedCensusWithProductRoot(
				productStateBound, productActions.size(),
				productTransitionBound, productTupleCells,
				enew.getCanonicalTree(), cnew.getCanonicalTree());
	}

	public static void requireRegisteredNativeCompositionProfile() {
		if (Thread.currentThread().isInterrupted()
				|| Analyser.partialOrderReduction
				|| !"ltsa.lts.DFSCompositionEngine".equals(
						Options.getCompositionStrategyClass())
				|| Options.getMaxStatesGeneration()
						!= LTSConstants.NO_MAX_STATE_GENERATION) {
			throw new IllegalArgumentException(
					"CLnew requires the registered uninterrupted DFS/no-POR/no-threshold composition profile.");
		}
	}

	private static void requireLiveTreeMatches(
			CompactState source,
			CompactStateEndpointAdmission.Admission admission,
			String role) {
		CompactStateCanonicalTree actual =
				CompactStateCanonicalTree.captureForest(
						new CompactState[]{source}).get(0);
		if (!CompactStateCanonicalTree.canonicalEquals(
				actual, admission.getCanonicalTree())) {
			throw new IllegalArgumentException(
					role + " bytes differ from their immutable admission.");
		}
	}

	public CompactStateEndpointAdmission.Admission getEnewAdmission() {
		return enewAdmission;
	}

	public CompactStateEndpointAdmission.Admission getCnewAdmission() {
		return cnewAdmission;
	}

	public CompactStateEndpointAdmission.Admission getClosedLoopAdmission() {
		return closedLoopAdmission;
	}

	public M9CompositionProvenance.Projection getClosedLoopAuthority() {
		return closedLoopAuthority;
	}

	public M9CompositionProvenance.TwoCoordinateProjection getCoordinates() {
		return coordinates;
	}
}
