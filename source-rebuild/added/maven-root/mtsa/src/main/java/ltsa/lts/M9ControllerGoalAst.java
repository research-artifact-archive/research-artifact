package ltsa.lts;

import ltsa.control.ControllerGoalDefinition;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Objects;

/** Immutable value snapshot of every controller-goal field observable by MTSA. */
public final class M9ControllerGoalAst {
	private final String name;
	private final List<String> controllableActions;
	private final List<String> safety;
	private final List<String> assumptions;
	private final List<String> guarantees;
	private final List<String> faults;
	private final List<String> buchi;
	private final List<String> concurrency;
	private final List<String> activity;
	private final List<String> marking;
	private final List<String> disturbances;
	private final boolean nonblocking;
	private final boolean permissive;
	private final boolean exceptionHandling;
	private final int laziness;
	private final boolean nonTransient;
	private final boolean reachability;
	private final boolean testLatency;
	private final int maxControllers;
	private final int maxSchedulers;
	private final int parallelRankingThreads;

	static M9ControllerGoalAst capture(ControllerGoalDefinition source) {
		if (source == null) {
			throw new IllegalArgumentException("Controller goal is absent.");
		}
		return new M9ControllerGoalAst(
				source.getNameString(),
				strings(source.getControllableActionSet()),
				symbols(source.getSafetyDefinitions()),
				symbols(source.getAssumeDefinitions()),
				symbols(source.getGuaranteeDefinitions()),
				symbols(source.getFaultsDefinitions()),
				symbols(source.getBuchiDefinitions()),
				symbols(source.getConcurrencyDefinitions()),
				symbols(source.getActivityDefinitions()),
				strings(source.getMarkingDefinitions()),
				strings(source.getDisturbanceActions()),
				source.isNonBlocking(),
				source.isPermissive(),
				source.isExceptionHandling(),
				integer(source.getLazyness()),
				source.isNonTransient(),
				source.isReachability(),
				source.isTestLatency(),
				integer(source.getMaxControllers()),
				integer(source.getMaxSchedulers()),
				source.parallelRankingThreads());
	}

	private M9ControllerGoalAst(
			String name,
			List<String> controllableActions,
			List<String> safety,
			List<String> assumptions,
			List<String> guarantees,
			List<String> faults,
			List<String> buchi,
			List<String> concurrency,
			List<String> activity,
			List<String> marking,
			List<String> disturbances,
			boolean nonblocking,
			boolean permissive,
			boolean exceptionHandling,
			int laziness,
			boolean nonTransient,
			boolean reachability,
			boolean testLatency,
			int maxControllers,
			int maxSchedulers,
			int parallelRankingThreads) {
		this.name = required(name, "controller goal name");
		this.controllableActions = controllableActions;
		this.safety = safety;
		this.assumptions = assumptions;
		this.guarantees = guarantees;
		this.faults = faults;
		this.buchi = buchi;
		this.concurrency = concurrency;
		this.activity = activity;
		this.marking = marking;
		this.disturbances = disturbances;
		this.nonblocking = nonblocking;
		this.permissive = permissive;
		this.exceptionHandling = exceptionHandling;
		this.laziness = laziness;
		this.nonTransient = nonTransient;
		this.reachability = reachability;
		this.testLatency = testLatency;
		this.maxControllers = maxControllers;
		this.maxSchedulers = maxSchedulers;
		this.parallelRankingThreads = parallelRankingThreads;
	}

	private static int integer(Integer value) {
		return value == null ? 0 : value.intValue();
	}

	private static List<String> symbols(List<Symbol> source) {
		List<String> result = new ArrayList<String>();
		if (source != null) {
			for (Symbol symbol : source) {
				if (symbol == null) throw new IllegalArgumentException(
						"Controller goal contains a null symbol.");
				result.add(required(symbol.getName(), "controller goal symbol"));
			}
		}
		return Collections.unmodifiableList(result);
	}

	private static List<String> strings(List<String> source) {
		List<String> result = new ArrayList<String>();
		if (source != null) {
			for (String value : source) result.add(required(value, "goal string"));
		}
		return Collections.unmodifiableList(result);
	}

	private static String required(String value, String role) {
		if (value == null || value.isEmpty()) {
			throw new IllegalArgumentException(role + " is missing.");
		}
		return value;
	}

	public String getName() { return name; }
	public List<String> getControllableActions() { return controllableActions; }
	public List<String> getSafety() { return safety; }
	public List<String> getAssumptions() { return assumptions; }
	public List<String> getGuarantees() { return guarantees; }
	public List<String> getFaults() { return faults; }
	public List<String> getBuchi() { return buchi; }
	public List<String> getConcurrency() { return concurrency; }
	public List<String> getActivity() { return activity; }
	public List<String> getMarking() { return marking; }
	public List<String> getDisturbances() { return disturbances; }
	public boolean isNonblocking() { return nonblocking; }
	public boolean isPermissive() { return permissive; }
	public boolean isExceptionHandling() { return exceptionHandling; }
	public int getLaziness() { return laziness; }
	public boolean isNonTransient() { return nonTransient; }
	public boolean isReachability() { return reachability; }
	public boolean isTestLatency() { return testLatency; }
	public int getMaxControllers() { return maxControllers; }
	public int getMaxSchedulers() { return maxSchedulers; }
	public int getParallelRankingThreads() { return parallelRankingThreads; }

	@Override
	public boolean equals(Object other) {
		if (this == other) return true;
		if (!(other instanceof M9ControllerGoalAst)) return false;
		M9ControllerGoalAst value = (M9ControllerGoalAst) other;
		return nonblocking == value.nonblocking
				&& permissive == value.permissive
				&& exceptionHandling == value.exceptionHandling
				&& laziness == value.laziness
				&& nonTransient == value.nonTransient
				&& reachability == value.reachability
				&& testLatency == value.testLatency
				&& maxControllers == value.maxControllers
				&& maxSchedulers == value.maxSchedulers
				&& parallelRankingThreads == value.parallelRankingThreads
				&& name.equals(value.name)
				&& controllableActions.equals(value.controllableActions)
				&& safety.equals(value.safety)
				&& assumptions.equals(value.assumptions)
				&& guarantees.equals(value.guarantees)
				&& faults.equals(value.faults)
				&& buchi.equals(value.buchi)
				&& concurrency.equals(value.concurrency)
				&& activity.equals(value.activity)
				&& marking.equals(value.marking)
				&& disturbances.equals(value.disturbances);
	}

	@Override
	public int hashCode() {
		return Objects.hash(
				name, controllableActions, safety, assumptions, guarantees,
				faults, buchi, concurrency, activity, marking, disturbances,
				nonblocking, permissive, exceptionHandling, laziness,
				nonTransient, reachability, testLatency, maxControllers,
				maxSchedulers, parallelRankingThreads);
	}
}
