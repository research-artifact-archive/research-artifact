"""Canonical micro-program translation of the fixed two-thread Java producer."""
import hashlib
import json


def digest(value):
    return hashlib.sha256(json.dumps(value, separators=(',', ':'), sort_keys=True).encode()).hexdigest()


class JavaRandom:
    def __init__(self, seed):
        self.state = (seed ^ 0x5DEECE66D) & ((1 << 48) - 1)

    def next_bits(self, bits):
        self.state = (self.state * 0x5DEECE66D + 0xB) & ((1 << 48) - 1)
        return self.state >> (48 - bits)

    def next_int(self, bound):
        if bound & (bound - 1) == 0:
            return (bound * self.next_bits(31)) >> 31
        while True:
            bits = self.next_bits(31)
            value = bits % bound
            if bits - value + bound - 1 < 1 << 31:
                return value


def writer_jobs(seed, n, budget):
    rng = JavaRandom(seed)
    result = []
    for _ in range(budget):
        z = 0
        while z < rng.next_int(17):
            z += 1
        result.append(rng.next_int(n))
    return result


def build(case, run, row):
    assert run['id'] == row['id'] and case['id'] == run['case'], 'input identity binding'
    assert run['layout'] in ('distinct', 'colliding')
    assert run['kind'] in ('concurrent', 'replay', 'postwrite')
    assert run['mutant'] == 'none', 'mutant source is not the ordinary producer model'
    n = len(case['jobs'])
    events = row['events']
    assert 1 <= n <= 5
    assert all(e['kind'] == 'I' and e['job'] == i and e['id'] == i + 1 for i, e in enumerate(events[:n]))
    assert all(e['kind'] != 'I' for e in events[n:])
    foreground = [(i, e) for i, e in enumerate(events) if e['kind'] in ('K', 'D')]
    background = [(i, e) for i, e in enumerate(events) if e['kind'] == 'B']
    values = {e['id']: e for e in events if e['kind'] != 'D'}
    initial = [events[i]['id'] for i in range(n)]
    links = [{} for _ in range(n)]
    for e in events:
        if e['kind'] == 'B':
            source, ident = e['source'], e['id']
        elif e['kind'] == 'D':
            ident = e['id']
            source = values[ident]['source']
        else:
            continue
        assert source not in links[e['job']], 'forked publication chain'
        links[e['job']][source] = ident
    chains, positions = [], {}
    for job in range(n):
        chain = [initial[job]]
        while chain[-1] in links[job]:
            ident = links[job][chain[-1]]
            assert ident not in chain
            chain.append(ident)
        assert len(chain) == len(links[job]) + 1 and chain[-1] == row['live'][job]
        for pos, ident in enumerate(chain):
            positions[ident] = pos
        chains.append(chain)

    programs = [[], []]
    F, W = programs

    def emit(program, op, **fields):
        program.append(dict(op=op, **fields))
        return len(program)

    def key(job):
        return 0 if run['layout'] == 'colliding' else job

    bg_starts, bg_returns = [], []
    for index, e in background:
        job = e['job']
        bg_starts.append(len(W))
        emit(W, 'wait', other_pc=0)
        emit(W, 'lock', job=job, bin=key(job))
        emit(W, 'read', job=job, source=e['source'])
        emit(W, 'alloc', id=e['id'])
        emit(W, 'log', index=index)
        emit(W, 'publish', job=job, source=e['source'], id=e['id'])
        emit(W, 'unlock', bin=key(job))
        emit(W, 'return')
        bg_returns.append(len(W))

    cursor, injection = 0, 0
    outcomes = []
    post_done = False

    def take(kind, job, inside=None):
        nonlocal cursor
        assert cursor < len(foreground)
        index, e = foreground[cursor]
        cursor += 1
        assert e['kind'] == kind and e['job'] == job
        if inside is not None:
            assert e['inside'] is inside
        return index, e

    def inject(job):
        nonlocal injection
        assert injection < len(background) and background[injection][1]['job'] == job, 'wrong injected writer job'
        after_submit = emit(F, 'submit', writer_call=injection)
        W[bg_starts[injection]]['other_pc'] = after_submit
        emit(F, 'wait', other_pc=bg_returns[injection])
        injection += 1

    for label in row['trace']:
        sjob, act = label.split(':')
        job = int(sjob)
        if act == 'P':
            index, output = take('K', job, True)
            emit(F, 'lock', job=job, bin=key(job))
            emit(F, 'read', job=job, source=output['source'])
            emit(F, 'alloc', id=output['id'])
            emit(F, 'log', index=index)
            emit(F, 'publish', job=job, source=output['source'], id=output['id'])
            emit(F, 'unlock', bin=key(job))
            emit(F, 'return')
            succeeds = True
        else:
            mode, outcome = act
            assert mode in 'CAV' and outcome in 'SF'
            index, outside = take('K', job, False)
            emit(F, 'read', job=job, source=outside['source'])
            emit(F, 'alloc', id=outside['id'])
            emit(F, 'log', index=index)
            if run['kind'] != 'concurrent':
                outcomes.append(outcome)
                if outcome == 'F':
                    inject(job)
            emit(F, 'lock', job=job, bin=key(job))
            emit(F, 'compare', job=job, before=outside['source'], match=outcome == 'S')
            output = outside
            if mode == 'C' and outcome == 'F':
                inside_index, output = take('K', job, True)
                emit(F, 'read', job=job, source=output['source'])
                emit(F, 'alloc', id=output['id'])
                emit(F, 'log', index=inside_index)
            succeeds = outcome == 'S' or mode == 'C'
            if succeeds:
                emit(F, 'publish', job=job, source=output['source'], id=output['id'])
            elif mode == 'A':
                emit(F, 'identity_store', job=job)
            emit(F, 'unlock', bin=key(job))
            emit(F, 'return')
        if succeeds:
            index, done = take('D', job)
            assert done['id'] == output['id']
            emit(F, 'log', index=index)
            if run['kind'] == 'postwrite' and job == 0 and not post_done:
                inject(0)
                post_done = True
    assert cursor == len(foreground)
    if run['kind'] == 'concurrent':
        assert not run['outcomes']
        assert [e['job'] for _, e in background] == writer_jobs(run['seed'], n, run['budget']), 'writer Random sequence differs'
        emit(F, 'wait', other_pc=len(W))
    else:
        assert ''.join(outcomes) == run['outcomes']
        assert injection == len(background), 'unrequested writer call'
    return dict(schema='charged-fixed-producer-microprogram-v1', n=n, initial=initial,
                final=row['live'], chains=chains, positions=positions, programs=programs,
                events=events, initial_logs=n, raw_sha256=digest(row),
                input_sha256=digest(dict(case=case, run=run)))
