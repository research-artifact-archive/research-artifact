"""Exact evaluation of nine declared algebraic examples, not a game oracle."""
from pathlib import Path
from fractions import Fraction as F
import json
import datetime
import hashlib

out = Path(__file__).resolve().parent
source = (out / "ARITHMETIC_INPUT.json").read_bytes()
data = json.loads(source)
rows = []
for case in data["cases"]:
    if case["kind"] == "geometric":
        r = case["r"]
        theta, gamma, t = map(F, (case["theta"], case["gamma"], case["t"]))
        n = case["n"]
        q = F(r) / (r + theta)
        weights = [t * q**j for j in range(n)]
        omega = sum(weights, F(0))
        terms = [r * weights[s-1] + theta * sum(weights[:s], F(0)) for s in range(1,n+1)]
        bad = (theta+1)*omega + r*t + gamma*(n+r)
        optimum = omega + max(terms) + gamma*(n+r)
        beta = 1 + F(r)*theta / ((theta+1)*(theta+r))
        row = {
            "id": case["id"], "input":case, "q":str(q),
            "weights_descending":[str(w) for w in weights],
            "Omega":str(omega), "all_s_terms":[str(v) for v in terms],
            "constant_s_term":str(t*(r+theta)),
            "term_equality":all(v == t*(r+theta) for v in terms),
            "bad_caller_joint_cost":str(bad), "optimal_joint_cost":str(optimum),
            "ratio":str(bad/optimum), "ratio_decimal_display_only":float(bad/optimum),
            "beta":str(beta), "ratio_le_beta":bad/optimum <= beta,
            "gamma_calls_over_t":str(gamma*(n+r)/t),
            "work_only_alpha":str(F(3*r+2, 2*r+2)),
        }
    else:
        weights = sorted(map(F,case["weights"]))
        n, r, B = len(weights), case["r"], case["B"]
        lam, gamma = F(case["lambda"]), F(case["gamma"])
        omega, M = sum(weights,F(0)), weights[-1]
        if B <= r:
            corners = [(omega+B*M,F(0),F(n+B))]
        else:
            corners = [(omega+r*weights[n-s]+sum(weights[-s:],F(0)),sum(weights[-s:],F(0)),F(n+r)) for s in range(1,min(B-r,n)+1)]
        costs = [w+lam*l+gamma*q for w,l,q in corners]
        maxima = tuple(max(v[j] for v in corners) for j in range(3))
        separate = maxima[0]+lam*maxima[1]+gamma*maxima[2]
        row = {
            "id":case["id"],"input":case,
            "corners_W_L_Q":[list(map(str,v)) for v in corners],
            "joint_corner_costs":list(map(str,costs)),
            "joint_optimum":str(max(costs)),
            "maximizing_corner_indices_1_based":[i+1 for i,c in enumerate(costs) if c==max(costs)],
            "componentwise_maxima":list(map(str,maxima)),
            "sum_of_separate_suprema":str(separate),
            "separate_minus_joint":str(separate-max(costs)),
        }
        if "indicator_thresholds" in case:
            threshold = tuple(map(F,case["indicator_thresholds"]))
            indicator = lambda v: int(all(x>=y for x,y in zip(v,threshold)))
            row["monotone_indicator_at_each_corner"] = [indicator(v) for v in corners]
            row["monotone_indicator_at_componentwise_maxima"] = indicator(maxima)
    rows.append(row)
result = {"completed_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
          "input_sha256":hashlib.sha256(source).hexdigest(),
          "case_count":len(rows), "rows":rows,
          "all_geometric_equalities_and_upper_bounds":all(row.get("term_equality",True) and row.get("ratio_le_beta",True) for row in rows),
          "limits":"Arithmetic of displayed expressions only; not a semantic experiment or a proof certificate."}
destination=out/"ARITHMETIC_OUTPUT.json"
with destination.open("x") as f:
    json.dump(result,f,ensure_ascii=False,indent=2)
    f.write("\n")
print(json.dumps(result,ensure_ascii=False,indent=2))
