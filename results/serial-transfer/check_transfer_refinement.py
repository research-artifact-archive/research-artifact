"""Finite sanity check for transfer-only merge refinement.

This is a new, separate finite game experiment, not a performance benchmark,
source-model experiment, proof, or native FG-DUCS frontend validation.
Requirement monitors and precedence edges are absent. Therefore nonempty
monitor commutativity/error behavior and mapped precedence are not tested.
The earlier independent-product experiment is not part of this program.
"""
import argparse
import csv
from pathlib import Path

from dataclasses import dataclass
from itertools import product
from random import Random
import json

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--summary-csv", type=Path, help="Optional CSV output path")
args = parser.parse_args()
records = []
SCOPE = {
    "claim_scope": "finite sanity check; not proof or performance evidence",
    "monitor_scope": "no monitors; nonempty commuting/absorbing-error conditions not tested",
    "precedence_scope": "no edges; nonempty mapped-precedence conditions not tested",
    "frontend_scope": "abstract games; no FSP/native-solver validation",
}

def emit(kind, values):
    record = {"record_type": kind, **SCOPE, **values}
    records.append(record)
    print(json.dumps(record, sort_keys=True))


@dataclass(frozen=True)
class Component:
    n:int
    alphabet:tuple
    uc:tuple
    control:tuple
    transfer:tuple

@dataclass(frozen=True)
class Game:
    n:int
    goals:int
    uc:tuple
    controls:tuple

def bits(mask):
    while mask:
        x=mask & -mask
        yield x.bit_length()-1
        mask-=x

def wins(g):
    w=g.goals
    while True:
        old=w
        for s in range(g.n):
            if old>>s&1:continue
            if (g.uc[s] and not(g.uc[s]&~old)) or (not g.uc[s] and any(c and not(c&~old) for c in g.controls[s])):
                w |= 1<<s
        if w==old:return w

def enabled(comp,version,state):
    return sum(1<<label for label in range(2) if comp.alphabet[version]>>label&1 and comp.uc[version][state][label])
def assumptions(a,b):
    alph=all(c.alphabet[0]==c.alphabet[1] for c in (a,b))
    dominates=all(not(enabled(c,1,t)&~enabled(c,0,s)) for c in (a,b) for s in range(c.n) for t in bits(c.transfer[s]))
    return alph,dominates

def construct(a,b,targets,merged):
    states=list(product(range(2),range(a.n),range(2),range(b.n)))
    idx={s:i for i,s in enumerate(states)}
    us=[];cs=[];goals=0
    for row,(va,sa,vb,sb) in enumerate(states):
        u=0
        for label in range(2):
            participates=[bool(a.alphabet[va]>>label&1),bool(b.alphabet[vb]>>label&1)]
            if not any(participates):continue
            ma=a.uc[va][sa][label] if participates[0] else 1<<sa
            mb=b.uc[vb][sb][label] if participates[1] else 1<<sb
            for ta,tb in product(bits(ma),bits(mb)):
                u|=1<<idx[(va,ta,vb,tb)]
        us.append(u)
        choices=[]
        if not u:
            choices.append(1<<row) # shared controllable tick at every physical tuple
            ca=sum(1<<idx[(va,ta,vb,sb)] for ta in bits(a.control[va][sa]))
            cb=sum(1<<idx[(va,sa,vb,tb)] for tb in bits(b.control[vb][sb]))
            if ca:choices.append(ca)
            if cb:choices.append(cb)
            if merged:
                if va==vb==0:
                    c=sum(1<<idx[(1,ta,1,tb)] for ta,tb in product(bits(a.transfer[sa]),bits(b.transfer[sb])))
                    if c:choices.append(c)
            else:
                if va==0:
                    c=sum(1<<idx[(1,ta,vb,sb)] for ta in bits(a.transfer[sa]))
                    if c:choices.append(c)
                if vb==0:
                    c=sum(1<<idx[(va,sa,1,tb)] for tb in bits(b.transfer[sb]))
                    if c:choices.append(c)
            if va==vb==1 and (sa,sb) in targets:goals |= 1<<row
        cs.append(tuple(choices))
    return Game(len(states),goals,tuple(us),tuple(cs)),states,idx

stats={'product_games':0,'old_start_states':0,'coarse_win_fine_win':0,'fine_only_win':0,'both_loss':0,'violations':0,'quiet_prefixes':0,'endpoint_cartesian_checks':0,'partial_transfer_games':0,'multisucc_transfer_games':0,'multisucc_uc_games':0,'multisucc_control_games':0}
def check(a,b,targets):
    assert assumptions(a,b)==(True,True)
    fine,states,idx=construct(a,b,targets,False)
    coarse,_,_=construct(a,b,targets,True)
    fw,cw=wins(fine),wins(coarse)
    stats['product_games']+=1
    stats['partial_transfer_games']+=any(t==0 for c in (a,b) for t in c.transfer)
    stats['multisucc_transfer_games']+=any(t.bit_count()>1 for c in (a,b) for t in c.transfer)
    stats['multisucc_uc_games']+=any(m.bit_count()>1 for c in (a,b) for v in c.uc for s in v for m in s)
    stats['multisucc_control_games']+=any(m.bit_count()>1 for c in (a,b) for v in c.control for m in v)
    for sa,sb in product(range(a.n),range(b.n)):
        root=idx[(0,sa,0,sb)];x=bool(cw>>root&1);y=bool(fw>>root&1)
        stats['old_start_states']+=1
        if x and not y:
            stats['violations']+=1
            raise AssertionError((a,b,targets,states[root],cw,fw))
        stats['coarse_win_fine_win' if x else 'fine_only_win' if y else 'both_loss']+=1
        if fine.uc[root] or not a.transfer[sa] or not b.transfer[sb]:continue
        coarse_out={(1,ta,1,tb) for ta,tb in product(bits(a.transfer[sa]),bits(b.transfer[sb]))}
        for order in [(0,1),(1,0)]:
            prefixes=[(1,ta,0,sb) for ta in bits(a.transfer[sa])] if order[0]==0 else [(0,sa,1,tb) for tb in bits(b.transfer[sb])]
            reached=set()
            for prefix in prefixes:
                stats['quiet_prefixes']+=1
                assert not fine.uc[idx[prefix]],(a,b,prefix)
                if order[0]==0:reached.update((1,prefix[1],1,tb) for tb in bits(b.transfer[prefix[3]]))
                else:reached.update((1,ta,1,prefix[3]) for ta in bits(a.transfer[prefix[1]]))
            assert reached==coarse_out
            stats['endpoint_cartesian_checks']+=1

# Exhaust all one-physical-state components for 2 UC labels:
# label absent, present-disabled, enabled-old-only, or enabled-both.
one=[]
for labels in product(range(4),repeat=2):
    alpha=sum(1<<l for l,x in enumerate(labels) if x)
    old=(tuple(int(x in (2,3)) for x in labels),)
    new=(tuple(int(x==3) for x in labels),)
    one.append(Component(1,(alpha,alpha),(old,new),((1,),(1,)),(1,)))
for a,b in product(one,repeat=2):check(a,b,{(0,0)})
exhaustive_stats = dict(stats)
emit("one_state_exhaustive", {
    **stats, "components": 2, "physical_states_per_version": 1,
    "uc_labels": 2, "generation": "all 16 local types squared",
})

# 4096 reproducible generated 2-physical-state pairs. Local UC alphabets may differ by component,
# but are version invariant. Transfer outcomes are sampled only from dominating new local states.
# Goals are a nonempty subset of globally quiet all-new tuples, including correlated subsets.
rng=Random(20261003)
def random_component():
    alpha=rng.randrange(4)
    u=tuple(tuple(tuple(rng.randrange(4) if alpha>>l&1 else 0 for l in range(2)) for s in range(2)) for v in range(2))
    cs=tuple(tuple(rng.randrange(4) for s in range(2)) for v in range(2))
    temp=Component(2,(alpha,alpha),u,cs,())
    gs=[]
    for s in range(2):
        allowed=[t for t in range(2) if not(enabled(temp,1,t)&~enabled(temp,0,s))]
        mask=rng.randrange(1<<len(allowed))
        gs.append(sum(1<<t for k,t in enumerate(allowed) if mask>>k&1))
    return Component(2,(alpha,alpha),u,cs,tuple(gs))
accepted=0;generated=0
while accepted<4096:
    generated+=1;a=random_component();b=random_component()
    probe,states,idx=construct(a,b,set(),False)
    quiet=[(sa,sb) for sa,sb in product(range(2),repeat=2) if not probe.uc[idx[(1,sa,1,sb)]]]
    if not quiet:continue
    take=rng.randrange(1,1<<len(quiet));targets={p for k,p in enumerate(quiet) if take>>k&1}
    check(a,b,targets);accepted+=1
sampling = {
    "seed": 20261003,
    "generated_candidates": generated,
    "accepted_candidates": accepted,
    "excluded_no_quiet_all_new_target": generated - accepted,
    "exclusion_reason": "generated pair has no globally quiet all-new tuple; outside chosen nonempty-target test domain",
}
emit("two_state_seeded", {
    **{key: value - exhaustive_stats[key] for key, value in stats.items()},
    **sampling, "components": 2, "physical_states_per_version": 2,
    "uc_labels": 2, "generation": "seeded accepted pairs; not exhaustive",
})
emit("combined", {**stats, **sampling, "components": 2, "uc_labels": 2})

def uc_graph_acyclic(game):
    indegree = [0] * game.n
    for successors in game.uc:
        for target in bits(successors):
            indegree[target] += 1
    pending = [state for state, count in enumerate(indegree) if count == 0]
    removed = 0
    while pending:
        state = pending.pop()
        removed += 1
        for target in bits(game.uc[state]):
            indegree[target] -= 1
            if indegree[target] == 0:
                pending.append(target)
    return removed == game.n

# Retain counterexample 1: acyclic one-step UC, total identity, static alphabets,
# but transfer creates a locally enabled UC event.
a=Component(2,(3,3),(((0,2),(0,0)),((2,0),(0,0))),((1,2),(1,2)),(1,2))
b=Component(2,(3,3),(((2,0),(0,0)),((0,2),(0,0))),((1,2),(1,2)),(1,2))
# Counterexample 2: enabled-UC domination holds, but version alphabets remove blockers.
a2=Component(1,(3,2),(((0,1),),((0,0),)),((1,),(1,)),(1,))
b2=Component(1,(3,1),(((1,0),),((0,0),)),((1,),(1,)),(1,))
for label,aa,bb in [('acyclic_total_breaks_enabled_domination',a,b),('dropping_alphabet_breaks_static_participants',a2,b2)]:
    fine,ss,ix=construct(aa,bb,{(0,0)},False);coarse,_,_=construct(aa,bb,{(0,0)},True)
    root=ix[(0,0,0,0)]
    report={'alphabet_static':assumptions(aa,bb)[0],'enabled_domination':assumptions(aa,bb)[1],'fine_win':bool(wins(fine)>>root&1),'coarse_win':bool(wins(coarse)>>root&1)}
    assert not report['fine_win'] and report['coarse_win']
    report["total_local_transfers"] = all(c.transfer[s] for c in (aa, bb) for s in range(c.n))
    report["uc_graph_acyclic"] = uc_graph_acyclic(fine)
    report["counterexample"] = label
    report["components"] = 2
    report["physical_states_per_version"] = aa.n
    report["uc_labels"] = 2
    if label == "acyclic_total_breaks_enabled_domination":
        assert report["uc_graph_acyclic"] and report["total_local_transfers"]
    emit("retained_counterexample", report)

if args.summary_csv is not None:
    fields = list(dict.fromkeys(key for record in records for key in record))
    with args.summary_csv.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)
