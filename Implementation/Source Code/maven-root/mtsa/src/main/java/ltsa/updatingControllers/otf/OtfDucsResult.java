package ltsa.updatingControllers.otf;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Set;

/** Immutable result and mechanically checkable certificates produced by OTF-DUCS. */
public final class OtfDucsResult<Q, A, G> {

    private final WinningCertificate<Q, A, G> winningCertificate;
    private final LosingCertificate<Q> losingCertificate;
    private final Statistics statistics;

    static <Q, A, G> OtfDucsResult<Q, A, G> winning(
            WinningCertificate<Q, A, G> certificate,
            Statistics statistics) {
        return new OtfDucsResult<Q, A, G>(certificate, null, statistics);
    }

    static <Q, A, G> OtfDucsResult<Q, A, G> losing(
            LosingCertificate<Q> certificate,
            Statistics statistics) {
        return new OtfDucsResult<Q, A, G>(null, certificate, statistics);
    }

    private OtfDucsResult(
            WinningCertificate<Q, A, G> winningCertificate,
            LosingCertificate<Q> losingCertificate,
            Statistics statistics) {
        this.winningCertificate = winningCertificate;
        this.losingCertificate = losingCertificate;
        this.statistics = statistics;
    }

    public boolean isWinning() {
        return winningCertificate != null;
    }

    public WinningCertificate<Q, A, G> winningCertificate() {
        if (winningCertificate == null) {
            throw new IllegalStateException("OTF-DUCS returned no solution.");
        }
        return winningCertificate;
    }

    public LosingCertificate<Q> losingCertificate() {
        if (losingCertificate == null) {
            throw new IllegalStateException("OTF-DUCS returned a winning controller.");
        }
        return losingCertificate;
    }

    public Statistics statistics() {
        return statistics;
    }

    public static final class WinningCertificate<Q, A, G> {
        private final Set<Q> initialStates;
        private final Map<Q, Integer> ranks;
        private final Map<Q, Map<A, Set<Q>>> strategy;
        private final Map<Q, G> goalMatches;

        WinningCertificate(
                Set<Q> initialStates,
                Map<Q, Integer> ranks,
                Map<Q, Map<A, Set<Q>>> strategy,
                Map<Q, G> goalMatches) {
            this.initialStates = immutableSet(initialStates);
            this.ranks = Collections.unmodifiableMap(new LinkedHashMap<Q, Integer>(ranks));
            this.strategy = immutableGraph(strategy);
            this.goalMatches = Collections.unmodifiableMap(new LinkedHashMap<Q, G>(goalMatches));
        }

        public Set<Q> initialStates() {
            return initialStates;
        }

        /** Ranks are stored exactly for the strategy-reachable mid states. */
        public Map<Q, Integer> ranks() {
            return ranks;
        }

        /** Goal states deliberately have no mid-mode outgoing transition. */
        public Map<Q, Map<A, Set<Q>>> strategy() {
            return strategy;
        }

        /** Atomic, zero-step links from Goal configurations to new-controller states. */
        public Map<Q, G> goalMatches() {
            return goalMatches;
        }
    }

    public static final class LosingCertificate<Q> {
        private final Set<Q> losingStates;

        LosingCertificate(Set<Q> losingStates) {
            this.losingStates = immutableSet(losingStates);
        }

        public Set<Q> losingStates() {
            return losingStates;
        }
    }

    public static final class Statistics {
        private final long discoveredStates;
        private final long expandedStates;
        private final long queriedStateActionPairs;
        private final long materializedTransitions;
        private final long propagatedIncidences;
        private final long peakFrontier;
        private final boolean earlySuccess;
        private final boolean guidedProofAccepted;
        private final boolean guidedFallbackUsed;
        private final long guidedMaximumDepth;
        private final long attractorPeakFrontier;
        private final boolean lazyControllableBuckets;
        private final long deferredControllableCandidates;
        private final long resumedControllableCandidates;
        private final long unqueriedControllableCandidatesAtTermination;
        private final long fixedPointStateInspections;
        private final long fixedPointComputations;

        Statistics(
                long discoveredStates,
                long expandedStates,
                long queriedStateActionPairs,
                long materializedTransitions,
                long propagatedIncidences,
                long peakFrontier,
                boolean earlySuccess,
                boolean guidedProofAccepted,
                boolean guidedFallbackUsed,
                long guidedMaximumDepth,
                long attractorPeakFrontier,
                boolean lazyControllableBuckets,
                long deferredControllableCandidates,
                long resumedControllableCandidates,
                long unqueriedControllableCandidatesAtTermination,
                long fixedPointStateInspections,
                long fixedPointComputations) {
            this.discoveredStates = discoveredStates;
            this.expandedStates = expandedStates;
            this.queriedStateActionPairs = queriedStateActionPairs;
            this.materializedTransitions = materializedTransitions;
            this.propagatedIncidences = propagatedIncidences;
            this.peakFrontier = peakFrontier;
            this.earlySuccess = earlySuccess;
            this.guidedProofAccepted = guidedProofAccepted;
            this.guidedFallbackUsed = guidedFallbackUsed;
            this.guidedMaximumDepth = guidedMaximumDepth;
            this.attractorPeakFrontier = attractorPeakFrontier;
            this.lazyControllableBuckets = lazyControllableBuckets;
            this.deferredControllableCandidates = deferredControllableCandidates;
            this.resumedControllableCandidates = resumedControllableCandidates;
            this.unqueriedControllableCandidatesAtTermination =
                    unqueriedControllableCandidatesAtTermination;
            this.fixedPointStateInspections = fixedPointStateInspections;
            this.fixedPointComputations = fixedPointComputations;
        }

        public long discoveredStates() { return discoveredStates; }
        public long expandedStates() { return expandedStates; }
        public long queriedStateActionPairs() { return queriedStateActionPairs; }
        public long materializedTransitions() { return materializedTransitions; }
        public long propagatedIncidences() { return propagatedIncidences; }
        /** Legacy aggregate: the maximum of guided depth and attractor frontier. */
        public long peakFrontier() { return peakFrontier; }
        public boolean earlySuccess() { return earlySuccess; }
        public boolean guidedProofAccepted() { return guidedProofAccepted; }
        public boolean guidedFallbackUsed() { return guidedFallbackUsed; }
        public long guidedMaximumDepth() { return guidedMaximumDepth; }
        public long attractorPeakFrontier() { return attractorPeakFrontier; }
        public boolean lazyControllableBuckets() { return lazyControllableBuckets; }
        public long deferredControllableCandidates() {
            return deferredControllableCandidates;
        }
        public long resumedControllableCandidates() {
            return resumedControllableCandidates;
        }
        public long unqueriedControllableCandidatesAtTermination() {
            return unqueriedControllableCandidatesAtTermination;
        }
        public long fixedPointStateInspections() {
            return fixedPointStateInspections;
        }
        public long fixedPointComputations() {
            return fixedPointComputations;
        }
    }

    private static <T> Set<T> immutableSet(Set<T> source) {
        return Collections.unmodifiableSet(new LinkedHashSet<T>(source));
    }

    private static <Q, A> Map<Q, Map<A, Set<Q>>> immutableGraph(
            Map<Q, Map<A, Set<Q>>> source) {
        Map<Q, Map<A, Set<Q>>> outer = new LinkedHashMap<Q, Map<A, Set<Q>>>();
        for (Map.Entry<Q, Map<A, Set<Q>>> stateEntry : source.entrySet()) {
            Map<A, Set<Q>> actions = new LinkedHashMap<A, Set<Q>>();
            for (Map.Entry<A, Set<Q>> actionEntry : stateEntry.getValue().entrySet()) {
                actions.put(actionEntry.getKey(), immutableSet(actionEntry.getValue()));
            }
            outer.put(stateEntry.getKey(), Collections.unmodifiableMap(actions));
        }
        return Collections.unmodifiableMap(outer);
    }
}
