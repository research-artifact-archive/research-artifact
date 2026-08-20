package ltsa.updatingControllers.export;

import java.io.DataOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;

import ltsa.updatingControllers.synthesis.UpdatingEnvironmentGenerator;

/**
 * Canonical, solver-free receipt core for one materialized M9 endpoint.
 *
 * <p>The core is intentionally small: it contains exact, domain-separated
 * digests and censuses for three streamed binary semantic sections.  The section
 * encoder covers every immutable field retained by
 * {@link M9EndpointStrategySnapshot} and
 * {@link M9ClosedLoopEndpointSnapshot}.  A publisher must write these exact
 * sections and compare the resulting size and digest to the descriptors before
 * making a receipt visible.  The one-shot hook hashes only
 * {@link #getCanonicalCoreBytes()}, avoiding a circular dependency on the seal
 * envelope that is available only after the hook closes.</p>
 */
public final class M9EndpointReceiptCore {
	public static final String DOMAIN = "FGDUCS-M9-ENDPOINT-RECEIPT-V2";
	public static final String SCHEMA_VERSION = "m9-endpoint-receipt-core-v2";
	public static final String CANONICALIZATION = "fse2027-canonical-json-v1";
	public static final String STRATEGY_SECTION = "strategy.bin";
	public static final String CLOSED_LOOP_SECTION = "closed-loop.bin";
	public static final String TRADITIONAL_SECTION = "traditional-pre-gr.bin";
	private static final String STRATEGY_FORMAT =
			"m9-endpoint-strategy-section-v1";
	private static final String CLOSED_LOOP_FORMAT =
			"m9-closed-loop-endpoint-section-v1";
	private static final String TRADITIONAL_FORMAT =
			"m9-traditional-pre-gr-section-v2";
	private static final int MAX_CORE_BYTES = 16 * 1024 * 1024;
	private static final long MAX_SECTION_BYTES = 32L * 1024L * 1024L;
	private static final long MAX_AGGREGATE_SECTION_BYTES =
			96L * 1024L * 1024L;
	/* Every reserved decoded item has at least one distinct wire byte. */
	private static final long MAX_DECODED_ITEMS_PER_SECTION = MAX_SECTION_BYTES;
	private static final int MAX_ID_BYTES = 256;

	private final Bindings bindings;
	private final M9EndpointStrategySnapshot strategy;
	private final M9ClosedLoopEndpointSnapshot closedLoop;
	private final TraditionalPreGrSnapshot traditional;
	private final M9TraditionalCompletionHandoffSnapshot completionHandoff;
	private final List<SectionDescriptor> sections;
	private final byte[] canonicalCoreBytes;
	private final byte[] canonicalCoreSha256;
	private final byte[] canonicalCoreTypedSha256;

	private M9EndpointReceiptCore(
			Bindings bindings,
			M9EndpointStrategySnapshot strategy,
			M9ClosedLoopEndpointSnapshot closedLoop,
			TraditionalPreGrSnapshot traditional,
			M9TraditionalCompletionHandoffSnapshot completionHandoff,
			List<SectionDescriptor> sections,
			byte[] canonicalCoreBytes) {
		this.bindings = bindings;
		this.strategy = strategy;
		this.closedLoop = closedLoop;
		this.traditional = traditional;
		this.completionHandoff = completionHandoff;
		this.sections = Collections.unmodifiableList(
				new ArrayList<SectionDescriptor>(sections));
		this.canonicalCoreBytes = canonicalCoreBytes.clone();
		this.canonicalCoreSha256 = sha256(canonicalCoreBytes);
		MessageDigest typed = newSha256();
		updateTypedPrefix(typed, SCHEMA_VERSION, canonicalCoreBytes.length);
		typed.update(canonicalCoreBytes);
		this.canonicalCoreTypedSha256 = typed.digest();
	}

	public static M9EndpointReceiptCore capture(
			Bindings bindings,
			M9EndpointStrategySnapshot strategy,
			M9ClosedLoopEndpointSnapshot closedLoop,
			TraditionalPreGrSnapshot traditional) {
		if (bindings == null || strategy == null || closedLoop == null
				|| traditional == null || traditional.getCompletionSeed() == null) {
			throw new IllegalArgumentException(
					"Combined receipt bindings and every immutable endpoint authority are required.");
		}
		M9TraditionalCompletionHandoffSnapshot handoff =
				M9TraditionalCompletionHandoffSnapshot.capture(
						traditional, strategy, closedLoop);
		List<SectionDescriptor> sections = new ArrayList<SectionDescriptor>(3);
		sections.add(describeSection(
				STRATEGY_SECTION, STRATEGY_FORMAT,
				strategy, closedLoop, traditional, handoff,
				strategyCensus(strategy)));
		sections.add(describeSection(
				CLOSED_LOOP_SECTION, CLOSED_LOOP_FORMAT,
				strategy, closedLoop, traditional, handoff,
				closedLoopCensus(closedLoop)));
		sections.add(describeSection(
				TRADITIONAL_SECTION, TRADITIONAL_FORMAT,
				strategy, closedLoop, traditional, handoff,
				traditionalCensus(traditional, handoff)));
		long aggregateSectionBytes = 0L;
		for (SectionDescriptor section : sections) {
			if (aggregateSectionBytes
					> MAX_AGGREGATE_SECTION_BYTES - section.getSizeBytes()) {
				throw new IllegalArgumentException(
						"Canonical endpoint receipt sections exceed the aggregate byte profile.");
			}
			aggregateSectionBytes += section.getSizeBytes();
		}
		byte[] core = canonicalCoreJson(bindings, sections);
		if (core.length == 0 || core.length > MAX_CORE_BYTES) {
			throw new IllegalArgumentException(
					"Canonical endpoint receipt core exceeds the registered byte profile.");
		}
		return new M9EndpointReceiptCore(
				bindings, strategy, closedLoop, traditional, handoff,
				sections, core);
	}

	public Bindings getBindings() { return bindings; }

	public List<SectionDescriptor> getSections() { return sections; }

	boolean hasTraditionalSnapshotIdentity(TraditionalPreGrSnapshot candidate) {
		return traditional == candidate;
	}

	M9TraditionalCompletionHandoffSnapshot getCompletionHandoff() {
		return completionHandoff;
	}

	public byte[] getCanonicalCoreBytes() { return canonicalCoreBytes.clone(); }

	public byte[] getCanonicalCoreSha256() {
		return canonicalCoreSha256.clone();
	}

	public byte[] getCanonicalCoreTypedSha256() {
		return canonicalCoreTypedSha256.clone();
	}

	/**
	 * Streams one canonical section and verifies the bytes written against the
	 * precomputed descriptor.  The caller owns and closes the output stream.
	 */
	public synchronized SectionDescriptor writeCanonicalSection(
			String name,
			OutputStream destination) throws IOException {
		if (destination == null) {
			throw new IllegalArgumentException("Endpoint receipt destination is absent.");
		}
		SectionDescriptor expected = requireSection(name);
		MessageDigest digest = newSha256();
		DigestCountingOutputStream sink =
				new DigestCountingOutputStream(
						destination, digest, expected.getSizeBytes());
		writeSectionPayload(
				name, strategy, closedLoop, traditional,
				completionHandoff, sink);
		sink.flush();
		byte[] actualDigest = digest.digest();
		if (sink.getCount() != expected.getSizeBytes()
				|| !Arrays.equals(actualDigest, expected.getContentSha256())) {
			throw new IOException(
					"Canonical endpoint receipt section changed during streaming.");
		}
		return expected;
	}

	private SectionDescriptor requireSection(String name) {
		for (SectionDescriptor section : sections) {
			if (section.getName().equals(name)) return section;
		}
		throw new IllegalArgumentException(
				"Unknown canonical endpoint receipt section: " + name);
	}

	private static SectionDescriptor describeSection(
			String name,
			String format,
			M9EndpointStrategySnapshot strategy,
			M9ClosedLoopEndpointSnapshot closedLoop,
			TraditionalPreGrSnapshot traditional,
			M9TraditionalCompletionHandoffSnapshot handoff,
			Map<String, Long> census) {
		MessageDigest rawDigest = newSha256();
		DigestCountingOutputStream raw = new DigestCountingOutputStream(
				NullOutputStream.INSTANCE, rawDigest, MAX_SECTION_BYTES);
		try {
			writeSectionPayload(
					name, strategy, closedLoop, traditional, handoff, raw);
			raw.flush();
		} catch (IOException boundedFailure) {
			throw new IllegalArgumentException(
					"Canonical endpoint receipt section exceeds its byte profile.",
					boundedFailure);
		}
		long size = raw.getCount();
		byte[] contentSha256 = rawDigest.digest();

		MessageDigest typedDigest = newSha256();
		updateTypedPrefix(typedDigest, format, size);
		DigestCountingOutputStream typed = new DigestCountingOutputStream(
				NullOutputStream.INSTANCE, typedDigest, size);
		try {
			writeSectionPayload(
					name, strategy, closedLoop, traditional, handoff, typed);
			typed.flush();
		} catch (IOException impossible) {
			throw new IllegalStateException(
					"In-memory typed section hashing failed.", impossible);
		}
		if (typed.getCount() != size) {
			throw new IllegalStateException(
					"Canonical section size changed between immutable hash passes.");
		}
		return new SectionDescriptor(
				name, format, size, contentSha256, typedDigest.digest(), census);
	}

	private static void writeSectionPayload(
			String name,
			M9EndpointStrategySnapshot strategy,
			M9ClosedLoopEndpointSnapshot closedLoop,
			TraditionalPreGrSnapshot traditional,
			M9TraditionalCompletionHandoffSnapshot handoff,
			OutputStream destination) throws IOException {
		CanonicalWriter writer = new CanonicalWriter(destination);
		if (STRATEGY_SECTION.equals(name)) {
			writeStrategySection(writer, strategy);
		} else if (CLOSED_LOOP_SECTION.equals(name)) {
			writeClosedLoopSection(writer, closedLoop);
		} else if (TRADITIONAL_SECTION.equals(name)) {
			writeTraditionalSection(writer, traditional, handoff);
		} else {
			throw new IllegalArgumentException(
					"Unknown canonical endpoint receipt section: " + name);
		}
		writer.flush();
	}

	private static void writeStrategySection(
			CanonicalWriter writer,
			M9EndpointStrategySnapshot value) throws IOException {
		writer.string(STRATEGY_FORMAT);
		writeMts(writer, value.getPlainController());
		writeMts(writer, value.getSolverEnvironment());
		writeMts(writer, value.getSolverPlant());
		writeProjection(writer, value.getPlantComposition());
		writePrefix(writer, value.getEnvironmentPrefix());
		writer.integer(value.getGuaranteeCount());
		writer.integer(value.getMaxLaziness());

		List<Long> coordinateKeys = sortedLongs(
				value.getPlainStateCoordinates().keySet());
		writer.count(coordinateKeys.size());
		for (Long state : coordinateKeys) {
			M9EndpointStrategySnapshot.StateCoordinates coordinate =
					value.getPlainStateCoordinates().get(state);
			writer.longInteger(state.longValue());
			writer.longInteger(coordinate.getPlantState());
			writer.integer(coordinate.getMemory());
			writer.integer(coordinate.getLaziness());
			writer.longInteger(coordinate.getEnewState());
		}
		writeLongLongMap(writer, value.getControllerStateToEnewState());
	}

	private static void writeClosedLoopSection(
			CanonicalWriter writer,
			M9ClosedLoopEndpointSnapshot value) throws IOException {
		writer.string(CLOSED_LOOP_FORMAT);
		writeAdmission(writer, value.getEnewAdmission());
		writeAdmission(writer, value.getCnewAdmission());
		writeAdmission(writer, value.getClosedLoopAdmission());
		writeProjection(writer, value.getClosedLoopAuthority());
		writeTwoCoordinateProjection(writer, value.getCoordinates());
	}

	private static void writeTraditionalSection(
			CanonicalWriter writer,
			TraditionalPreGrSnapshot value,
			M9TraditionalCompletionHandoffSnapshot handoff)
			throws IOException {
		if (value == null || value.getCompletionSeed() == null || handoff == null) {
			throw new IllegalArgumentException(
					"Traditional receipt authority is incomplete.");
		}
		writer.string(TRADITIONAL_FORMAT);
		writeMts(writer, value.getUpdatingEnvironment());
		writeMts(writer, value.getMetaEnvironment());
		writeMts(writer, value.getPrunedEnvironment());
		writeMts(writer, value.getSafetyEnvironment());
		writeUpdatingProvenance(writer, value.getUpdatingProvenance());
		writeLongLongMap(writer, value.getMetaStateToUpdatingState());
		writeLongLongMap(writer, value.getSafetyStateToPrunedState());
		writeLongLongMap(writer, value.getSafetyStateToUpdatingState());
		writeLongSet(writer, value.getProvenanceFreeUnsafeStates());
		writeLongSet(writer, value.getPrunedBySafetyFormula());
		writeStringSet(writer, value.getControllableActions());
		writeProjection(writer, value.getMetaCompositionProvenance());
		writeProjection(writer, value.getSafetyCompositionProvenance());
		writeSafetySemantics(writer, value.getSafetySemantics());
		writeCompletionSeed(writer, value.getCompletionSeed());
		writeCompletionHandoff(writer, handoff);
	}

	private static void writeUpdatingProvenance(
			CanonicalWriter writer,
			UpdatingEnvironmentGenerator.Provenance value) throws IOException {
		if (value == null) {
			throw new IllegalArgumentException(
					"Updating provenance authority is absent.");
		}
		writeLongSet(writer, value.getOldControllerStates());
		writeLongLongMap(writer, value.getMappingStateToUpdatingState());
		writeLongLongMap(writer, value.getUpdatingStateToMappingState());
		writeLongLongSetMap(writer, value.getBeginUpdateSourcesByMappingState());
		List<UpdatingEnvironmentGenerator.BeginUpdateRow> rows =
				new ArrayList<UpdatingEnvironmentGenerator.BeginUpdateRow>(
						value.getBeginUpdateRows());
		Collections.sort(rows,
				new Comparator<UpdatingEnvironmentGenerator.BeginUpdateRow>() {
					@Override
					public int compare(
							UpdatingEnvironmentGenerator.BeginUpdateRow left,
							UpdatingEnvironmentGenerator.BeginUpdateRow right) {
						int order = left.getOldControllerState().compareTo(
								right.getOldControllerState());
						if (order != 0) return order;
						order = left.getMappingState().compareTo(
								right.getMappingState());
						if (order != 0) return order;
						return left.getUpdatingState().compareTo(
								right.getUpdatingState());
					}
				});
		writer.count(rows.size());
		for (UpdatingEnvironmentGenerator.BeginUpdateRow row : rows) {
			writer.longInteger(row.getOldControllerState().longValue());
			writer.longInteger(row.getMappingState().longValue());
			writer.longInteger(row.getUpdatingState().longValue());
		}
	}

	private static void writeSafetySemantics(
			CanonicalWriter writer,
			M9TraditionalSafetySemanticsSnapshot value) throws IOException {
		if (value == null) {
			throw new IllegalArgumentException(
					"Traditional safety semantics authority is absent.");
		}
		writeMts(writer, value.getMetaEnvironment());
		writer.count(value.getFluentCatalog().size());
		for (M9TraditionalSafetySemanticsSnapshot.FluentRow row
				: value.getFluentCatalog()) {
			writer.string(row.getName());
			writer.bool(row.getInitialValue());
			writeStringSet(writer, row.getInitiatingActions());
			writeStringSet(writer, row.getTerminatingActions());
		}
		writer.count(value.getValuations().size());
		for (M9TraditionalSafetySemanticsSnapshot.StateValuationRow row
				: value.getValuations()) {
			writer.longInteger(row.getState());
			writeStringSet(writer, row.getTrueFluents());
		}
		writer.count(value.getFormulas().size());
		for (M9TraditionalSafetySemanticsSnapshot.FormulaRow row
				: value.getFormulas()) {
			writer.integer(row.getInputOrdinal());
			writer.string(row.getDefinitionName());
			writer.string(row.getSourceAssertionName());
			writer.string(row.getKind().name());
			writer.count(row.getPostfix().size());
			for (M9TraditionalSafetySemanticsSnapshot.FormulaToken token
					: row.getPostfix()) {
				writer.string(token.getOpcode().name());
				writer.bool(token.getFluentName() != null);
				if (token.getFluentName() != null) {
					writer.string(token.getFluentName());
				}
			}
			writeLongSet(writer, row.getTrueStates());
		}
		writeStringStringMap(
				writer, value.getDerivedOldActionToSourceAction());
		writer.string(value.getLifecycleProfile().name());
		writeStringList(writer, value.getLifecycleActions());
		writeLongSet(writer, value.getUnsafeStates());
	}

	private static void writeCompletionSeed(
			CanonicalWriter writer,
			TraditionalPreGrSnapshot.CompletionSeed value) throws IOException {
		if (value == null) {
			throw new IllegalArgumentException(
					"Traditional completion seed is absent.");
		}
		writeProjection(writer, value.getMappingProduct());
		writeProjection(writer, value.getNewEnvironment());
		writer.count(value.getLocalMappingToNew().size());
		for (Map<Integer, Integer> row : value.getLocalMappingToNew()) {
			writeIntegerIntegerMap(writer, row);
		}
		writeLongLongMap(writer, value.getMappingProductToNew());
		writer.count(value.getActionSequenceMarkers().size());
		for (Boolean marker : value.getActionSequenceMarkers()) {
			if (marker == null) {
				throw new IllegalArgumentException(
						"Completion marker authority contains null.");
			}
			writer.bool(marker.booleanValue());
		}
	}

	private static void writeCompletionHandoff(
			CanonicalWriter writer,
			M9TraditionalCompletionHandoffSnapshot value) throws IOException {
		writer.longInteger(value.getLifecycleCompleteCoordinate());
		List<Long> keys = sortedLongs(value.getCompletionStates().keySet());
		long rowCount = 0L;
		for (Long safetyState : keys) {
			List<M9TraditionalCompletionHandoffSnapshot.CompletionCoordinates>
					rows = value.getCompletionStates().get(safetyState);
			if (rows == null || rows.isEmpty()
					|| rowCount > Long.MAX_VALUE - rows.size()) {
				throw new IllegalArgumentException(
						"Completion handoff candidate relation is absent or oversized.");
			}
			rowCount += rows.size();
		}
		writer.count(rowCount);
		for (Long safetyState : keys) {
			for (M9TraditionalCompletionHandoffSnapshot.CompletionCoordinates row
					: value.getCompletionStates().get(safetyState)) {
				writer.longInteger(safetyState.longValue());
				writer.longInteger(row.getPrunedState());
				writer.longInteger(row.getMetaState());
				writer.longInteger(row.getUpdatingState());
				writer.longInteger(row.getMappingState());
				writer.longInteger(row.getEnewState());
				writer.longInteger(row.getSolverEnvironmentState());
				writer.longInteger(row.getCnewState());
				writer.longInteger(row.getClosedLoopState());
			}
		}
		if (value.getSyntheticTransitionCount() != 0L) {
			throw new IllegalArgumentException(
					"Completion handoff must not synthesize a transition.");
		}
		writer.census(value.getSyntheticTransitionCount());
	}

	private static void writeMts(
			CanonicalWriter writer,
			M9MtsSnapshot value) throws IOException {
		writer.longInteger(value.getInitialState());
		List<Long> states = sortedLongs(value.getStates());
		writer.count(states.size());
		for (Long state : states) writer.longInteger(state.longValue());
		List<String> actions = sortedStrings(value.getActions());
		writer.count(actions.size());
		for (String action : actions) writer.string(action);
		writer.count(states.size());
		for (Long state : states) {
			writer.longInteger(state.longValue());
			Map<String, Set<Long>> row = value.getPost().get(state);
			if (row == null) {
				throw new IllegalArgumentException(
						"Immutable MTS receipt row is absent.");
			}
			List<String> enabled = sortedStrings(row.keySet());
			writer.count(enabled.size());
			for (String action : enabled) {
				writer.string(action);
				List<Long> targets = sortedLongs(row.get(action));
				writer.count(targets.size());
				for (Long target : targets) {
					writer.longInteger(target.longValue());
				}
			}
		}
		writer.census(value.getBucketCount());
		writer.census(value.getOutcomeCount());
	}

	private static void writeSnapshot(
			CanonicalWriter writer,
			CompactStateCanonicalSnapshot value) throws IOException {
		writer.string(value.getName());
		writer.integer(value.getStateCount());
		writer.integer(value.getInitialState());
		writer.integer(value.getEndState());
		writer.count(value.getActions().size());
		for (CompactStateCanonicalSnapshot.Action action : value.getActions()) {
			writer.integer(action.getNativeIndex());
			writer.string(action.getLabel());
		}
		writer.count(value.getTransitions().size());
		for (CompactStateCanonicalSnapshot.Transition edge : value.getTransitions()) {
			writer.integer(edge.getFromState());
			writer.integer(edge.getActionIndex());
			writer.string(edge.getActionLabel());
			writer.integer(edge.getTargetState());
		}
		List<Integer> emptyRows = sortedIntegers(
				value.getEmptyTransitionStates());
		writer.count(emptyRows.size());
		for (Integer state : emptyRows) writer.integer(state.intValue());
		writer.count(value.getComponentNames().size());
		for (String component : value.getComponentNames()) writer.string(component);
		writeIntegerListMap(writer, value.getComponentStateTuples());
		writeStringIntegerListMap(
				writer, value.getNativeFirstOutcomeDiagnostics());
	}

	private static void writeTree(
			CanonicalWriter writer,
			CompactStateCanonicalTree value) throws IOException {
		writeSnapshot(writer, value.getSnapshot());
		writer.count(value.getChildren().size());
		for (CompactStateCanonicalTree child : value.getChildren()) {
			writeTree(writer, child);
		}
	}

	private static void writeProjection(
			CanonicalWriter writer,
			M9CompositionProvenance.Projection value) throws IOException {
		writeMts(writer, value.getProductSnapshot());
		writeMts(writer, value.getFirstComponentSourceSnapshot());
		writer.count(value.getComponentNames().size());
		for (String component : value.getComponentNames()) writer.string(component);
		writer.count(value.getComponentSnapshots().size());
		for (CompactStateCanonicalSnapshot snapshot : value.getComponentSnapshots()) {
			writeSnapshot(writer, snapshot);
		}
		writer.count(value.getComponentTrees().size());
		for (CompactStateCanonicalTree tree : value.getComponentTrees()) {
			writeTree(writer, tree);
		}
		writer.longInteger(value.getProductInitialState());
		writeLongLongMap(writer, value.getFirstComponentSourceStates());
		writeLongIntegerListMap(writer, value.getComponentStateTuples());
		writeDerivedPost(writer, value.getDerivedComponentPost());
		writeStringIntegerListMap(
				writer, value.getNativeFirstOutcomeDiagnostics());
	}

	private static void writePrefix(
			CanonicalWriter writer,
			M9CompositionProvenance.OrderedPrefixProjection value)
			throws IOException {
		writeProjection(writer, value.getExtendedProductAuthority());
		writeProjection(writer, value.getPrefixProductAuthority());
		writer.integer(value.getPrefixArity());
		writeLongLongMap(writer, value.getExtendedStateToPrefixState());
		List<Long> unsafe = sortedLongs(value.getProvenanceFreeUnsafeStates());
		writer.count(unsafe.size());
		for (Long state : unsafe) writer.longInteger(state.longValue());
	}

	private static void writeAdmission(
			CanonicalWriter writer,
			CompactStateEndpointAdmission.Admission value) throws IOException {
		writeSnapshot(writer, value.getSnapshot());
		writeTree(writer, value.getCanonicalTree());
		writer.integer(value.getNormalizedEndState());
		writer.bool(value.isComposed());
		writer.count(value.getComponentSnapshots().size());
		for (CompactStateCanonicalSnapshot snapshot : value.getComponentSnapshots()) {
			writeSnapshot(writer, snapshot);
		}
	}

	private static void writeTwoCoordinateProjection(
			CanonicalWriter writer,
			M9CompositionProvenance.TwoCoordinateProjection value)
			throws IOException {
		List<Long> keys = sortedLongs(value.getProductStateCoordinates().keySet());
		writer.count(keys.size());
		for (Long state : keys) {
			M9CompositionProvenance.SourceCoordinates coordinates =
					value.getProductStateCoordinates().get(state);
			writer.longInteger(state.longValue());
			writer.longInteger(coordinates.getFirstSourceState());
			writer.longInteger(coordinates.getSecondSourceState());
		}
		writeLongLongMap(writer, value.getSecondStateToFirstState());
		List<Long> unobserved = sortedLongs(
				value.getUnobservedSecondComponentStates());
		writer.count(unobserved.size());
		for (Long state : unobserved) writer.longInteger(state.longValue());
	}

	private static void writeLongLongMap(
			CanonicalWriter writer,
			Map<Long, Long> value) throws IOException {
		List<Long> keys = sortedLongs(value.keySet());
		writer.count(keys.size());
		for (Long key : keys) {
			Long target = value.get(key);
			if (target == null) {
				throw new IllegalArgumentException(
						"Canonical receipt map contains a null value.");
			}
			writer.longInteger(key.longValue());
			writer.longInteger(target.longValue());
		}
	}

	private static void writeLongSet(
			CanonicalWriter writer, Set<Long> value) throws IOException {
		List<Long> values = sortedLongs(value);
		writer.count(values.size());
		for (Long element : values) writer.longInteger(element.longValue());
	}

	private static void writeStringSet(
			CanonicalWriter writer, Set<String> value) throws IOException {
		List<String> values = sortedStrings(value);
		writer.count(values.size());
		for (String element : values) writer.string(element);
	}

	private static void writeStringList(
			CanonicalWriter writer, List<String> value) throws IOException {
		if (value == null || value.contains(null)) {
			throw new IllegalArgumentException(
					"Canonical receipt string list is absent or contains null.");
		}
		writer.count(value.size());
		for (String element : value) writer.string(element);
	}

	private static void writeStringStringMap(
			CanonicalWriter writer,
			Map<String, String> value) throws IOException {
		List<String> keys = sortedStrings(value.keySet());
		writer.count(keys.size());
		for (String key : keys) {
			String target = value.get(key);
			if (target == null) {
				throw new IllegalArgumentException(
						"Canonical receipt string map contains null.");
			}
			writer.string(key);
			writer.string(target);
		}
	}

	private static void writeLongLongSetMap(
			CanonicalWriter writer,
			Map<Long, Set<Long>> value) throws IOException {
		List<Long> keys = sortedLongs(value.keySet());
		writer.count(keys.size());
		for (Long key : keys) {
			Set<Long> targets = value.get(key);
			if (targets == null) {
				throw new IllegalArgumentException(
						"Canonical receipt long-set map contains null.");
			}
			writer.longInteger(key.longValue());
			writeLongSet(writer, targets);
		}
	}

	private static void writeIntegerIntegerMap(
			CanonicalWriter writer,
			Map<Integer, Integer> value) throws IOException {
		List<Integer> keys = sortedIntegers(value.keySet());
		writer.count(keys.size());
		for (Integer key : keys) {
			Integer target = value.get(key);
			if (target == null) {
				throw new IllegalArgumentException(
						"Canonical receipt integer map contains null.");
			}
			writer.integer(key.intValue());
			writer.integer(target.intValue());
		}
	}

	private static void writeIntegerListMap(
			CanonicalWriter writer,
			Map<Integer, List<Integer>> value) throws IOException {
		List<Integer> keys = sortedIntegers(value.keySet());
		writer.count(keys.size());
		for (Integer key : keys) {
			writer.integer(key.intValue());
			writeIntegerList(writer, value.get(key));
		}
	}

	private static void writeLongIntegerListMap(
			CanonicalWriter writer,
			Map<Long, List<Integer>> value) throws IOException {
		List<Long> keys = sortedLongs(value.keySet());
		writer.count(keys.size());
		for (Long key : keys) {
			writer.longInteger(key.longValue());
			writeIntegerList(writer, value.get(key));
		}
	}

	private static void writeStringIntegerListMap(
			CanonicalWriter writer,
			Map<String, List<Integer>> value) throws IOException {
		List<String> keys = sortedStrings(value.keySet());
		writer.count(keys.size());
		for (String key : keys) {
			writer.string(key);
			writeIntegerList(writer, value.get(key));
		}
	}

	private static void writeIntegerList(
			CanonicalWriter writer,
			List<Integer> value) throws IOException {
		if (value == null) {
			throw new IllegalArgumentException(
					"Canonical receipt integer tuple is absent.");
		}
		writer.count(value.size());
		for (Integer element : value) {
			if (element == null) {
				throw new IllegalArgumentException(
						"Canonical receipt integer tuple contains null.");
			}
			writer.integer(element.intValue());
		}
	}

	private static void writeDerivedPost(
			CanonicalWriter writer,
			Map<String, Set<List<Integer>>> value) throws IOException {
		List<String> keys = sortedStrings(value.keySet());
		writer.count(keys.size());
		for (String key : keys) {
			writer.string(key);
			List<List<Integer>> outcomes =
					new ArrayList<List<Integer>>(value.get(key));
			Collections.sort(outcomes, INTEGER_LIST_COMPARATOR);
			writer.count(outcomes.size());
			for (List<Integer> outcome : outcomes) {
				writeIntegerList(writer, outcome);
			}
		}
	}

	private static Map<String, Long> strategyCensus(
			M9EndpointStrategySnapshot value) {
		Map<String, Long> result = new TreeMap<String, Long>();
		long states = 0L;
		long actions = 0L;
		long buckets = 0L;
		long outcomes = 0L;
		for (M9MtsSnapshot snapshot : Arrays.asList(
				value.getPlainController(), value.getSolverEnvironment(),
				value.getSolverPlant())) {
			states += snapshot.getStates().size();
			actions += snapshot.getActions().size();
			buckets += snapshot.getBucketCount();
			outcomes += snapshot.getOutcomeCount();
		}
		result.put("direct_mts_actions", Long.valueOf(actions));
		result.put("direct_mts_buckets", Long.valueOf(buckets));
		result.put("direct_mts_outcomes", Long.valueOf(outcomes));
		result.put("direct_mts_states", Long.valueOf(states));
		result.put("plain_state_coordinates", Long.valueOf(
				value.getPlainStateCoordinates().size()));
		result.put("prefix_state_rows", Long.valueOf(value.getEnvironmentPrefix()
				.getExtendedStateToPrefixState().size()));
		return result;
	}

	private static Map<String, Long> closedLoopCensus(
			M9ClosedLoopEndpointSnapshot value) {
		Map<String, Long> result = new TreeMap<String, Long>();
		TreeCensus census = new TreeCensus();
		accumulateTree(value.getEnewAdmission().getCanonicalTree(), census);
		accumulateTree(value.getCnewAdmission().getCanonicalTree(), census);
		accumulateTree(value.getClosedLoopAdmission().getCanonicalTree(), census);
		result.put("admission_actions", Long.valueOf(census.actions));
		result.put("admission_states", Long.valueOf(census.states));
		result.put("admission_transitions", Long.valueOf(census.transitions));
		result.put("admission_tree_nodes", Long.valueOf(census.nodes));
		result.put("admission_tuple_cells", Long.valueOf(census.tupleCells));
		result.put("closed_loop_coordinate_rows", Long.valueOf(value.getCoordinates()
				.getProductStateCoordinates().size()));
		result.put("unobserved_controller_states", Long.valueOf(value.getCoordinates()
				.getUnobservedSecondComponentStates().size()));
		return result;
	}

	private static Map<String, Long> traditionalCensus(
			TraditionalPreGrSnapshot value,
			M9TraditionalCompletionHandoffSnapshot handoff) {
		Map<String, Long> result = new TreeMap<String, Long>();
		long states = 0L;
		long actions = 0L;
		long buckets = 0L;
		long outcomes = 0L;
		for (M9MtsSnapshot snapshot : Arrays.asList(
				value.getUpdatingEnvironment(), value.getMetaEnvironment(),
				value.getPrunedEnvironment(), value.getSafetyEnvironment())) {
			states += snapshot.getStates().size();
			actions += snapshot.getActions().size();
			buckets += snapshot.getBucketCount();
			outcomes += snapshot.getOutcomeCount();
		}
		UpdatingEnvironmentGenerator.Provenance provenance =
				value.getUpdatingProvenance();
		long sourceCells = 0L;
		for (Set<Long> row
				: provenance.getBeginUpdateSourcesByMappingState().values()) {
			sourceCells += row.size();
		}
		M9TraditionalSafetySemanticsSnapshot semantics =
				value.getSafetySemantics();
		long valuationCells = 0L;
		for (M9TraditionalSafetySemanticsSnapshot.StateValuationRow row
				: semantics.getValuations()) {
			valuationCells += row.getTrueFluents().size();
		}
		long formulaTokens = 0L;
		long formulaCells = 0L;
		for (M9TraditionalSafetySemanticsSnapshot.FormulaRow row
				: semantics.getFormulas()) {
			formulaTokens += row.getPostfix().size();
			formulaCells += row.getTrueStates().size();
		}
		TraditionalPreGrSnapshot.CompletionSeed seed = value.getCompletionSeed();
		long localRows = 0L;
		for (Map<Integer, Integer> row : seed.getLocalMappingToNew()) {
			localRows += row.size();
		}
		result.put("begin_update_rows", Long.valueOf(
				provenance.getBeginUpdateRows().size()));
		result.put("begin_update_source_cells", Long.valueOf(sourceCells));
		result.put("begin_update_source_keys", Long.valueOf(
				provenance.getBeginUpdateSourcesByMappingState().size()));
		result.put("completion_components", Long.valueOf(
				seed.getLocalMappingToNew().size()));
		result.put("completion_local_rows", Long.valueOf(localRows));
		result.put("completion_markers", Long.valueOf(
				seed.getActionSequenceMarkers().size()));
		result.put("completion_product_rows", Long.valueOf(
				seed.getMappingProductToNew().size()));
		result.put("controllable_actions", Long.valueOf(
				value.getControllableActions().size()));
		result.put("derived_old_action_rows", Long.valueOf(
				semantics.getDerivedOldActionToSourceAction().size()));
		result.put("direct_mts_actions", Long.valueOf(actions));
		result.put("direct_mts_buckets", Long.valueOf(buckets));
		result.put("direct_mts_outcomes", Long.valueOf(outcomes));
		result.put("direct_mts_states", Long.valueOf(states));
		long handoffRows = 0L;
		for (List<M9TraditionalCompletionHandoffSnapshot.CompletionCoordinates>
				row : handoff.getCompletionStates().values()) {
			if (row == null || handoffRows > Long.MAX_VALUE - row.size()) {
				throw new IllegalArgumentException(
						"Completion handoff row census overflows.");
			}
			handoffRows += row.size();
		}
		result.put("handoff_rows", Long.valueOf(handoffRows));
		result.put("lifecycle_actions", Long.valueOf(
				semantics.getLifecycleActions().size()));
		result.put("meta_to_updating_rows", Long.valueOf(
				value.getMetaStateToUpdatingState().size()));
		result.put("provenance_free_unsafe_states", Long.valueOf(
				value.getProvenanceFreeUnsafeStates().size()));
		result.put("pruned_by_formula_states", Long.valueOf(
				value.getPrunedBySafetyFormula().size()));
		result.put("safety_fluent_rows", Long.valueOf(
				semantics.getFluentCatalog().size()));
		result.put("safety_formula_rows", Long.valueOf(
				semantics.getFormulas().size()));
		result.put("safety_formula_tokens", Long.valueOf(formulaTokens));
		result.put("safety_formula_true_cells", Long.valueOf(formulaCells));
		result.put("safety_to_pruned_rows", Long.valueOf(
				value.getSafetyStateToPrunedState().size()));
		result.put("safety_to_updating_rows", Long.valueOf(
				value.getSafetyStateToUpdatingState().size()));
		result.put("safety_valuation_rows", Long.valueOf(
				semantics.getValuations().size()));
		result.put("safety_valuation_true_cells", Long.valueOf(valuationCells));
		result.put("synthetic_transitions", Long.valueOf(
				handoff.getSyntheticTransitionCount()));
		result.put("updating_inverse_rows", Long.valueOf(
				provenance.getUpdatingStateToMappingState().size()));
		result.put("updating_mapping_rows", Long.valueOf(
				provenance.getMappingStateToUpdatingState().size()));
		result.put("updating_old_states", Long.valueOf(
				provenance.getOldControllerStates().size()));
		return result;
	}

	private static void accumulateTree(
			CompactStateCanonicalTree value,
			TreeCensus census) {
		census.nodes++;
		CompactStateCanonicalSnapshot snapshot = value.getSnapshot();
		census.states += snapshot.getStateCount();
		census.actions += snapshot.getActions().size();
		census.transitions += snapshot.getTransitions().size();
		census.tupleCells += ((long) snapshot.getStateCount()
				+ (long) snapshot.getNativeFirstOutcomeDiagnostics().size())
				* (long) snapshot.getComponentNames().size();
		for (CompactStateCanonicalTree child : value.getChildren()) {
			accumulateTree(child, census);
		}
	}

	private static byte[] canonicalCoreJson(
			Bindings bindings,
			List<SectionDescriptor> sections) {
		StringBuilder result = new StringBuilder(8192);
		result.append('{');
		result.append("\"attempt_expectation\":{");
		result.append("\"attempt_consumed\":true,");
		result.append("\"immutable_captures\":1,");
		result.append("\"production_ledger\":true,");
		result.append("\"rejected_synthesis_entries\":0,");
		result.append("\"synthesis_entries\":1},");
		result.append("\"bindings\":{");
		appendJsonStringField(result, "attempt_id", bindings.getAttemptId(), true);
		appendJsonStringField(result, "case_id", bindings.getCaseId(), true);
		appendJsonStringField(result, "classification", bindings.getClassification(), true);
		appendJsonStringField(result, "cluster_id", bindings.getClusterId(), true);
		appendJsonStringField(result, "finite_semantics_profile_id",
				bindings.getFiniteSemanticsProfileId(), true);
		result.append("\"hashes\":{");
		boolean firstHash = true;
		for (Map.Entry<String, String> entry : bindings.getSha256Bindings().entrySet()) {
			if (!firstHash) result.append(',');
			appendJsonStringField(result, entry.getKey(), entry.getValue(), false);
			firstHash = false;
		}
		result.append("},");
		appendJsonStringField(result, "projection_kind",
				bindings.getProjectionKind(), true);
		result.append("\"source_binding_file_count\":")
				.append(bindings.getSourceBindingFileCount()).append(',');
		result.append("\"source_binding_total_bytes\":")
				.append(bindings.getSourceBindingTotalBytes()).append("},");
		appendJsonStringField(result, "canonicalization", CANONICALIZATION, true);
		appendJsonStringField(result, "domain", DOMAIN, true);
		appendJsonStringField(result, "schema_version", SCHEMA_VERSION, true);
		result.append("\"sections\":[");
		for (int index = 0; index < sections.size(); index++) {
			if (index != 0) result.append(',');
			SectionDescriptor section = sections.get(index);
			result.append("{\"census\":{");
			boolean firstCensus = true;
			for (Map.Entry<String, Long> entry : section.getCensus().entrySet()) {
				if (!firstCensus) result.append(',');
				appendJsonKey(result, entry.getKey());
				result.append(':').append(entry.getValue().longValue());
				firstCensus = false;
			}
			result.append("},");
			appendJsonStringField(result, "content_sha256",
					hex(section.getContentSha256()), true);
			appendJsonStringField(result, "format", section.getFormat(), true);
			appendJsonStringField(result, "name", section.getName(), true);
			result.append("\"size_bytes\":").append(section.getSizeBytes()).append(',');
			appendJsonStringField(result, "typed_sha256",
					hex(section.getTypedSha256()), false);
			result.append('}');
		}
		result.append("],");
		result.append("\"traditional_pre_gr_expectation\":{");
		result.append("\"attempt_consumed\":true,");
		result.append("\"capture_attempts\":1,");
		result.append("\"native_update_gr_entries\":0,");
		result.append("\"production_ledger\":true}}\n");
		return result.toString().getBytes(StandardCharsets.UTF_8);
	}

	private static void appendJsonStringField(
			StringBuilder result,
			String key,
			String value,
			boolean comma) {
		appendJsonKey(result, key);
		result.append(':');
		appendJsonString(result, value);
		if (comma) result.append(',');
	}

	private static void appendJsonKey(StringBuilder result, String value) {
		appendJsonString(result, value);
	}

	private static void appendJsonString(StringBuilder result, String value) {
		result.append('"');
		for (int index = 0; index < value.length(); index++) {
			char character = value.charAt(index);
			switch (character) {
				case '"': result.append("\\\""); break;
				case '\\': result.append("\\\\"); break;
				case '\b': result.append("\\b"); break;
				case '\f': result.append("\\f"); break;
				case '\n': result.append("\\n"); break;
				case '\r': result.append("\\r"); break;
				case '\t': result.append("\\t"); break;
				default:
					if (character < 0x20) {
						String hex = Integer.toHexString(character);
						result.append("\\u");
						for (int pad = hex.length(); pad < 4; pad++) result.append('0');
						result.append(hex);
					} else {
						result.append(character);
					}
			}
		}
		result.append('"');
	}

	private static void updateTypedPrefix(
			MessageDigest digest,
			String format,
			long size) {
		byte[] domain = (DOMAIN + "\u0000").getBytes(StandardCharsets.US_ASCII);
		byte[] tag = format.getBytes(StandardCharsets.US_ASCII);
		if (tag.length > 0xffff) {
			throw new IllegalArgumentException("Typed receipt tag is too long.");
		}
		digest.update(domain);
		digest.update((byte) ((tag.length >>> 8) & 0xff));
		digest.update((byte) (tag.length & 0xff));
		digest.update(tag);
		for (int shift = 56; shift >= 0; shift -= 8) {
			digest.update((byte) ((size >>> shift) & 0xff));
		}
	}

	private static List<Long> sortedLongs(Set<Long> values) {
		if (values == null || values.contains(null)) {
			throw new IllegalArgumentException(
					"Canonical receipt long set is null or contains null.");
		}
		List<Long> result = new ArrayList<Long>(values);
		Collections.sort(result);
		return result;
	}

	private static List<Integer> sortedIntegers(Set<Integer> values) {
		if (values == null || values.contains(null)) {
			throw new IllegalArgumentException(
					"Canonical receipt integer set is null or contains null.");
		}
		List<Integer> result = new ArrayList<Integer>(values);
		Collections.sort(result);
		return result;
	}

	private static List<String> sortedStrings(Set<String> values) {
		if (values == null || values.contains(null)) {
			throw new IllegalArgumentException(
					"Canonical receipt string set is null or contains null.");
		}
		List<String> result = new ArrayList<String>(values);
		Collections.sort(result, UTF8_COMPARATOR);
		return result;
	}

	private static byte[] exactUtf8(String value) {
		if (value == null) {
			throw new IllegalArgumentException("Canonical receipt string is null.");
		}
		try {
			ByteBuffer encoded = StandardCharsets.UTF_8.newEncoder()
					.onMalformedInput(CodingErrorAction.REPORT)
					.onUnmappableCharacter(CodingErrorAction.REPORT)
					.encode(java.nio.CharBuffer.wrap(value));
			byte[] result = new byte[encoded.remaining()];
			encoded.get(result);
			return result;
		} catch (CharacterCodingException invalid) {
			throw new IllegalArgumentException(
					"Canonical receipt string is not exact UTF-8.", invalid);
		}
	}

	private static MessageDigest newSha256() {
		try {
			return MessageDigest.getInstance("SHA-256");
		} catch (NoSuchAlgorithmException impossible) {
			throw new IllegalStateException(
					"The registered SHA-256 runtime is unavailable.", impossible);
		}
	}

	private static byte[] sha256(byte[] value) {
		return newSha256().digest(value.clone());
	}

	private static String hex(byte[] value) {
		StringBuilder result = new StringBuilder(value.length * 2);
		for (byte element : value) {
			result.append(Character.forDigit((element >>> 4) & 0xf, 16));
			result.append(Character.forDigit(element & 0xf, 16));
		}
		return result.toString();
	}

	private static final Comparator<String> UTF8_COMPARATOR =
			new Comparator<String>() {
				@Override
				public int compare(String left, String right) {
					byte[] a = exactUtf8(left);
					byte[] b = exactUtf8(right);
					int count = Math.min(a.length, b.length);
					for (int index = 0; index < count; index++) {
						int value = Integer.compare(a[index] & 0xff, b[index] & 0xff);
						if (value != 0) return value;
					}
					return Integer.compare(a.length, b.length);
				}
			};

	private static final Comparator<List<Integer>> INTEGER_LIST_COMPARATOR =
			new Comparator<List<Integer>>() {
				@Override
				public int compare(List<Integer> left, List<Integer> right) {
					int count = Math.min(left.size(), right.size());
					for (int index = 0; index < count; index++) {
						int value = Integer.compare(
								left.get(index).intValue(), right.get(index).intValue());
						if (value != 0) return value;
					}
					return Integer.compare(left.size(), right.size());
				}
			};

	/** Exact, immutable predecision bindings supplied by the verified T1 worker. */
	public static final class Bindings {
		private static final Set<String> REQUIRED_HASH_KEYS;
		static {
			Set<String> keys = new TreeSet<String>();
			Collections.addAll(keys,
					"attempt_claim_sha256",
					"case_plan_sha256",
					"intake_manifest_sha256",
					"intake_seal_sha256",
					"intake_summary_sha256",
					"materializer_build_attestation_sha256",
					"materializer_jar_sha256",
					"materializer_source_aggregate_sha256",
					"materializer_source_manifest_sha256",
					"endpoint_attempt_plan_sha256",
					"selected_source_bindings_sha256",
					"selected_translation_source_sha256",
					"t0_payload_sha256",
					"t0_protocol_sha256",
					"t0_response_sha256",
					"t0_seal_sha256",
					"t0_verification_sha256",
					"t1_payload_sha256",
					"t1_protocol_sha256",
					"t1_response_sha256",
					"t1_seal_sha256",
					"t1_verification_sha256",
					"worker_entrypoint_sha256",
					"worker_java_executable_sha256");
			REQUIRED_HASH_KEYS = Collections.unmodifiableSet(keys);
		}

		private final String caseId;
		private final String clusterId;
		private final String attemptId;
		private final String classification;
		private final String projectionKind;
		private final String finiteSemanticsProfileId;
		private final long sourceBindingFileCount;
		private final long sourceBindingTotalBytes;
		private final Map<String, String> sha256Bindings;

		public static Bindings capture(
				String caseId,
				String clusterId,
				String attemptId,
				String classification,
				String projectionKind,
				String finiteSemanticsProfileId,
				long sourceBindingFileCount,
				long sourceBindingTotalBytes,
				Map<String, String> sha256Bindings) {
			requireAsciiId(caseId, "case_id");
			requireAsciiId(clusterId, "cluster_id");
			requireAsciiId(attemptId, "attempt_id");
			requireAsciiId(classification, "classification");
			requireAsciiId(projectionKind, "projection_kind");
			requireAsciiId(finiteSemanticsProfileId,
					"finite_semantics_profile_id");
			if (sourceBindingFileCount < 0L || sourceBindingTotalBytes < 0L) {
				throw new IllegalArgumentException(
						"Source binding censuses must be nonnegative.");
			}
			Map<String, String> first = copyHashes(sha256Bindings);
			Map<String, String> second = copyHashes(sha256Bindings);
			Map<String, String> third = copyHashes(sha256Bindings);
			if (!first.equals(second) || !first.equals(third)) {
				throw new IllegalArgumentException(
						"Receipt binding authority changed during capture.");
			}
			return new Bindings(
					caseId, clusterId, attemptId, classification,
					projectionKind, finiteSemanticsProfileId,
					sourceBindingFileCount, sourceBindingTotalBytes, first);
		}

		private Bindings(
				String caseId,
				String clusterId,
				String attemptId,
				String classification,
				String projectionKind,
				String finiteSemanticsProfileId,
				long sourceBindingFileCount,
				long sourceBindingTotalBytes,
				Map<String, String> sha256Bindings) {
			this.caseId = caseId;
			this.clusterId = clusterId;
			this.attemptId = attemptId;
			this.classification = classification;
			this.projectionKind = projectionKind;
			this.finiteSemanticsProfileId = finiteSemanticsProfileId;
			this.sourceBindingFileCount = sourceBindingFileCount;
			this.sourceBindingTotalBytes = sourceBindingTotalBytes;
			this.sha256Bindings = Collections.unmodifiableMap(
					new LinkedHashMap<String, String>(sha256Bindings));
		}

		private static Map<String, String> copyHashes(Map<String, String> source) {
			if (source == null || !source.keySet().equals(REQUIRED_HASH_KEYS)) {
				throw new IllegalArgumentException(
						"Receipt SHA-256 binding key census differs from the registered schema.");
			}
			Map<String, String> result = new LinkedHashMap<String, String>();
			for (String key : REQUIRED_HASH_KEYS) {
				String value = source.get(key);
				if (value == null || !value.matches("[0-9a-f]{64}")) {
					throw new IllegalArgumentException(
							"Receipt binding " + key + " is not lowercase SHA-256.");
				}
				result.put(key, value);
			}
			return result;
		}

		private static void requireAsciiId(String value, String role) {
			if (value == null || value.isEmpty()
					|| value.getBytes(StandardCharsets.US_ASCII).length > MAX_ID_BYTES
					|| !value.matches("[A-Za-z0-9][A-Za-z0-9._:-]*")) {
				throw new IllegalArgumentException(
						"Receipt " + role + " is outside the registered ASCII ID profile.");
			}
		}

		public String getCaseId() { return caseId; }
		public String getClusterId() { return clusterId; }
		public String getAttemptId() { return attemptId; }
		public String getClassification() { return classification; }
		public String getProjectionKind() { return projectionKind; }
		public String getFiniteSemanticsProfileId() {
			return finiteSemanticsProfileId;
		}
		public long getSourceBindingFileCount() { return sourceBindingFileCount; }
		public long getSourceBindingTotalBytes() { return sourceBindingTotalBytes; }
		public Map<String, String> getSha256Bindings() { return sha256Bindings; }

		/** Exact key census used by strict T1 loaders and independent verifiers. */
		public static Set<String> requiredSha256BindingKeys() {
			return REQUIRED_HASH_KEYS;
		}
	}

	public static final class SectionDescriptor {
		private final String name;
		private final String format;
		private final long sizeBytes;
		private final byte[] contentSha256;
		private final byte[] typedSha256;
		private final Map<String, Long> census;

		private SectionDescriptor(
				String name,
				String format,
				long sizeBytes,
				byte[] contentSha256,
				byte[] typedSha256,
				Map<String, Long> census) {
			this.name = name;
			this.format = format;
			this.sizeBytes = sizeBytes;
			this.contentSha256 = contentSha256.clone();
			this.typedSha256 = typedSha256.clone();
			this.census = Collections.unmodifiableMap(
					new TreeMap<String, Long>(census));
		}

		public String getName() { return name; }
		public String getFormat() { return format; }
		public long getSizeBytes() { return sizeBytes; }
		public byte[] getContentSha256() { return contentSha256.clone(); }
		public byte[] getTypedSha256() { return typedSha256.clone(); }
		public Map<String, Long> getCensus() { return census; }
	}

	private static final class TreeCensus {
		private long nodes;
		private long states;
		private long actions;
		private long transitions;
		private long tupleCells;
	}

	private static final class CanonicalWriter {
		private final DataOutputStream output;
		private long remainingDecodedItems = MAX_DECODED_ITEMS_PER_SECTION;

		private CanonicalWriter(OutputStream output) {
			this.output = new DataOutputStream(output);
		}

		private void count(long value) throws IOException {
			if (value < 0L || value > remainingDecodedItems) {
				throw new IllegalArgumentException(
						"Canonical receipt section exceeds its decoded-item profile.");
			}
			remainingDecodedItems -= value;
			output.writeLong(value);
		}

		private void census(long value) throws IOException {
			if (value < 0L) {
				throw new IllegalArgumentException(
						"Canonical receipt census is negative.");
			}
			output.writeLong(value);
		}

		private void longInteger(long value) throws IOException {
			output.writeLong(value);
		}

		private void integer(int value) throws IOException {
			output.writeInt(value);
		}

		private void bool(boolean value) throws IOException {
			output.writeByte(value ? 1 : 0);
		}

		private void string(String value) throws IOException {
			byte[] bytes = exactUtf8(value);
			output.writeInt(bytes.length);
			output.write(bytes);
		}

		private void flush() throws IOException { output.flush(); }
	}

	private static final class DigestCountingOutputStream extends OutputStream {
		private final OutputStream destination;
		private final MessageDigest digest;
		private final long maximumBytes;
		private long count;

		private DigestCountingOutputStream(
				OutputStream destination,
				MessageDigest digest,
				long maximumBytes) {
			this.destination = destination;
			this.digest = digest;
			if (maximumBytes < 0L || maximumBytes > MAX_SECTION_BYTES) {
				throw new IllegalArgumentException(
						"Canonical receipt section byte budget is invalid.");
			}
			this.maximumBytes = maximumBytes;
		}

		@Override
		public void write(int value) throws IOException {
			byte[] single = new byte[]{(byte) value};
			write(single, 0, 1);
		}

		@Override
		public void write(byte[] value, int offset, int length) throws IOException {
			if (length < 0 || count > Long.MAX_VALUE - length
					|| count > maximumBytes - length) {
				throw new IOException("Canonical receipt section size overflow.");
			}
			destination.write(value, offset, length);
			digest.update(value, offset, length);
			count += length;
		}

		@Override
		public void flush() throws IOException { destination.flush(); }
		private long getCount() { return count; }
	}

	private static final class NullOutputStream extends OutputStream {
		private static final NullOutputStream INSTANCE = new NullOutputStream();
		@Override public void write(int value) { }
		@Override public void write(byte[] value, int offset, int length) { }
	}
}
