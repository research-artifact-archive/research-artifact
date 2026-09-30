#!/usr/bin/env python3
"""Generate the predeclared full Cell ring; no solver or measured data is read."""
import argparse
import json
from pathlib import Path

SCHEMA = "fg-ducs-full-cell-ring-v1"


def lts(initial, states, edges):
    return {"initial": initial, "states": states, "edges": edges}


def monitor(initial, states, alphabet, changes):
    return {"initial": initial, "states": states, "alphabet": alphabet,
            "error": "E", "changes": changes,
            "omitted_transitions": "stutter; E absorbs every alphabet event"}


def model(n):
    if not 2 <= n <= 10:
        raise ValueError("The preregistered range is n=2..10")
    stations = [chr(ord("A") + i) for i in range(n)]
    moves = ["m_" + s for s in stations]
    inspections = ["j" if n == 2 else "j_" + s for s in stations[1:]]
    pending = ["d" if n == 2 else "d_" + s for s in stations[1:]]
    components = []
    for i, s in enumerate(stations):
        initial = "h" if i == 0 else "e"
        edges = [["h", moves[(i + 1) % n], "e"], ["e", moves[i], "h"]]
        # Retain the original two-station declaration order as well as its LTS.
        if i > 0:
            edges = list(reversed(edges))
        components.append({"id": s,
                           "old": lts(initial, ["h", "e"], edges),
                           "new": lts(initial, ["h", "e"], edges +
                                      ([["h", inspections[i - 1], "h"]] if i else [])),
                           "transfer_action": "rho_" + s,
                           "transfer": {"e": ["e"]}})
    one = [[s, moves[j], stations[j] if j == (i + 1) % n else "E"]
           for i, s in enumerate(stations) for j in range(n)]
    inspect = []
    for i in range(1, n):
        inspect.extend([["c", moves[i], pending[i - 1]],
                        [pending[i - 1], inspections[i - 1], "c"],
                        [pending[i - 1], moves[(i + 1) % n], "E"]])
    old_controller = lts("c_o", ["c_o"], [["c_o", m, "c_o"] for m in moves])
    new_controller_edges = [["c_0", moves[0], "c_0"]]
    for i in range(1, n):
        c = "c_" + str(i)
        new_controller_edges += [["c_0", moves[i], c], ["c_0", inspections[i - 1], "c_0"],
                                 [c, inspections[i - 1], "c_0"], [c, moves[i], c]]
    old_endpoint_states = [{"id": "x_" + s, "holder": i, "controller": "c_o", "old": "k"}
                           for i, s in enumerate(stations)]
    new_endpoint_states = [{"id": "z_" + s, "holder": i, "controller": "c_0", "inspect": "c"}
                           for i, s in enumerate(stations)]
    new_endpoint_states += [{"id": "y_" + stations[i], "holder": i, "controller": "c_" + str(i),
                            "inspect": pending[i - 1]} for i in range(1, n)]
    old_edges = [["x_" + s, moves[(i + 1) % n], "x_" + stations[(i + 1) % n]]
                 for i, s in enumerate(stations)]
    new_edges = []
    for i, s in enumerate(stations):
        j = (i + 1) % n
        new_edges.append(["z_" + s, moves[j], ("z_" if j == 0 else "y_") + stations[j]])
        if i:
            new_edges += [["y_" + s, inspections[i - 1], "z_" + s],
                          ["z_" + s, inspections[i - 1], "z_" + s]]
    return {"schema": SCHEMA, "n": n, "stations": stations,
            "ordinary": moves + inspections, "controllable": moves + inspections,
            "components": components,
            "requirements": {
                "old": monitor("k", ["k", "E"], inspections,
                               [["k", j, "E"] for j in inspections]),
                "inspect": monitor("c", ["c"] + pending + ["E"], moves + inspections, inspect),
                "one": monitor("A", stations + ["E"], moves, one)},
            "boundaries": {"start": "s", "stop": "t", "precedence": [["s", "t"]]},
            "activation": {
                "inspect_domain": "all versioned physical products (4^n entries)",
                "inspect_initializer": "d_i for the least-index non-A holding station i, otherwise c",
                "unreachable_completion": "For n=2 the zero/multiple-holder completion equals the preexisting Java fixture. S1 specifies the 8 one-product versioned tuples; the Java initializer contains 16 entries. Conservation excludes the additional tuples from every reachable Post state, so their completion cannot affect decision/rank.",
                "one_domain": "all-old physical states with exactly one holder",
                "one_initializer": "holder station name",
                "residual": "explicit total DFA over common alphabet, same transition function/error set as tester"},
            "controllers": {"old": old_controller,
                            "new": lts("c_0", ["c_" + str(i) for i in range(n)], new_controller_edges)},
            "endpoints": {
                "old": {"initial": "x_A", "states": old_endpoint_states, "edges": old_edges},
                "new": {"initial": "z_A", "states": new_endpoint_states, "edges": new_edges},
                "loadable": ["z_" + s for s in stations],
                "goal_ids": ["h", "e"] if n == 2 else ["z_" + s for s in stations]},
            "scope": "constructed witness, not an application benchmark or prevalence estimate"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "inputs")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for n in range(2, 11):
        path = args.output / ("cell_n%02d.json" % n)
        text = json.dumps(model(n), indent=2, ensure_ascii=True) + "\n"
        if path.exists() and path.read_text() != text:
            raise SystemExit("Refusing to overwrite a different existing input: " + str(path))
        if not path.exists():
            path.write_text(text)
        print(path)


if __name__ == "__main__":
    main()
