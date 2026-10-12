"""v9 (far transfer, 10-11): the model widens its own help page by swapping well-formed pieces between its examples.

An outside tool, the same for every domain (it knows text, not spreadsheets or RPN). Before day 1 the mode calls it once:

  ring 1 = the help page.
  ring 2 = every single swap on a ring-1 example: one well-formed piece of the example is replaced by one well-formed piece
           of any help example. A swap is kept when the domain's own tool runs the result within the model's caps (the same
           checks a practice problem passes, mode.accept). One example is kept per digit shape (every digit run read as #),
           and a shape already in an earlier ring is not kept again. Enumerated in a fixed order (no randomness).
  ring k > 2 = single swaps on random ring k-1 examples (the run's own random stream), kept by the same rules, until the
           ring holds widen_ring_max examples or the tries run out.

  join ring (only when the constants ask for it, widen_join): one more ring, the next number after the swap rings (ring 4
           when widen_rings is 3), built after them from examples of rings 1 to widen_rings. A value slot of an example is a
           well-formed piece whose replacement by `1` still runs. A join replaces one value slot P of a random example by P and
           a random value piece Q of the help page (a value slot of some help example) joined by a symbol s: `P s Q`,
           `Q s P`, `(P) s (Q)`, `(Q) s (P)` (bracket forms only when the help page uses both ( and )), `P Q s` or `Q P s`,
           with an empty or a single-space separator between the three parts. The symbols are the help prompts' own
           one-character tokens that are not letters, digits, spaces or brackets. A join kind is a (form, symbol) pair.
           The first 20,000 tries draw join kinds evenly; the kinds with a kept example are the accepted kinds, and the
           ring then fills an equal quota (widen_ring_max // accepted kinds) per accepted kind (probe examples count).
           Kept by the same rules as ring 3, until every quota is full or 1000 * widen_ring_max tries are spent.
           Without widen_join nothing changes (same rings).

A well-formed piece is a run of whole tokens (a token is a run of letters and digits, a run of spaces, or one other
character) that does not start or end with a space and whose brackets ( ) [ ] { } balance. Each new example keeps the kind
of the help example it was made from, so the model's own per-kind scores still apply.

Practice then draws each problem's example from a ring picked evenly among the rings that hold that kind
(mode.pick_example), and varies it exactly as before (addendum A10's edits). Disclosed: chosen after the diagnosis in
/mnt/project-files/far-transfer/diag/ (far questions join two kinds and use 5-6 row grids, which no practice row had),
so v9 is scored on a fresh panel draw (sheet.v3, rpn.v3).
"""
import hashlib
import json
import re

TOKEN = re.compile(r'[A-Za-z0-9]+|\s+|.')
OPEN, CLOSE = '([{', ')]}'


def tokens(text):
    return TOKEN.findall(text)


def balanced(toks):
    depth = 0
    for t in toks:
        if t in OPEN:
            depth += 1
        elif t in CLOSE:
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def spans(toks):
    """(i, j) for every well-formed piece toks[i:j], in order."""
    out = []
    for i in range(len(toks)):
        if toks[i].isspace():
            continue
        for j in range(i + 1, len(toks) + 1):
            if not toks[j - 1].isspace() and balanced(toks[i:j]):
                out.append((i, j))
    return out


def pieces(helps):
    """Every well-formed piece of every help prompt, sorted (a fixed order)."""
    out = set()
    for h in helps:
        t = tokens(h['prompt'])
        out.update(''.join(t[i:j]) for i, j in spans(t))
    return sorted(out)


def shape(text):
    return re.sub(r'[0-9]+', '#', text)


def swap(toks, i, j, piece):
    return ''.join(toks[:i]) + piece + ''.join(toks[j:])


def symbols(helps):
    """The one-character tokens of the help prompts that are not alphanumeric, not spaces and not brackets, sorted."""
    return sorted({t for h in helps for t in tokens(h['prompt']) if len(t) == 1 and not t.isalnum() and not t.isspace()
                   and t not in OPEN + CLOSE})


def join_form(p, q, s, form, sep):
    """P and Q joined by symbol s in one of the six forms (0-5), parts separated by sep."""
    parts = [(p, s, q), (q, s, p), ('(' + p + ')', s, '(' + q + ')'), ('(' + q + ')', s, '(' + p + ')'), (p, q, s), (q, p, s)][form]
    return sep.join(parts)


def value_slots(p, ok):
    """(tokens, [(i, j)]): the well-formed pieces of prompt p that are value slots, i.e. replacing the piece by 1 still runs."""
    t = tokens(p)
    return t, [(i, j) for i, j in spans(t) if ok(swap(t, i, j, '1'))]


def join_ring(tool, helps, rings, ok, rng, cons, seen):
    """-> (examples, tries, info): the join ring, made from rings 1..widen_rings by the rules in the docstring. seen: digit
    shapes already kept (updated). info: accepted join kinds ('form:symbol') and kept per kind."""
    ring_max, cap = cons['widen_ring_max'], 1000 * cons['widen_ring_max']
    syms = symbols(helps)
    brackets = any('(' in h['prompt'] for h in helps) and any(')' in h['prompt'] for h in helps)
    kinds = [(f, s) for f in (range(6) if brackets else (0, 1, 4, 5)) for s in syms]
    slots = {}
    vq = set()   # value pieces of the help page
    for h in helps:
        t, sl = slots.setdefault(h['prompt'], value_slots(h['prompt'], ok))
        vq.update(''.join(t[i:j]) for i, j in sl)
    vq = sorted(vq)
    pool = [x for r in range(1, cons['widen_rings'] + 1) for x in rings[r]]
    out, tries, kept = [], 0, {}
    accepted = None   # set after the probe
    while pool and vq and kinds and len(out) < ring_max and tries < cap:
        if accepted is not None:
            open_ = [k for k in accepted if kept[k] < ring_max // len(accepted)]
            if not open_:
                break
        else:
            open_ = kinds
        tries += 1
        kind, p = rng.choice(pool)
        if p not in slots:
            slots[p] = value_slots(p, ok)
        t, sl = slots[p]
        if not sl:
            continue
        i, j = rng.choice(sl)
        form, s = rng.choice(open_)
        cand = swap(t, i, j, join_form(''.join(t[i:j]), rng.choice(vq), s, form, rng.choice(['', ' '])))
        sh = shape(cand)
        if sh not in seen and ok(cand):
            seen.add(sh)
            out.append((kind, cand))
            kept[(form, s)] = kept.get((form, s), 0) + 1
        if accepted is None and tries >= 20000:
            accepted = sorted(kept)
            if not accepted:
                break
    info = dict(accepted=[f'{f}:{s}' for f, s in sorted(kept)], kept={f'{f}:{s}': n for (f, s), n in sorted(kept.items())})
    return out, tries, info


def whole_join_ring(tool, helps, ok, rng, cons, seen):
    """-> (examples, tries, info): the whole-formula join ring (L9, widen_join_whole). The whole piece of a help example is its
    value slot under R1 such that the example with that piece replaced by `1` is answered `1` with no calculator steps (the
    piece that does all the work); several: the longest by character length, ties the first in spans order; none: the example
    is left out of host and Q choices (its whole piece is None). Each try: host = a help
    example, P = its whole piece, Q = the whole piece of a help example (the host included), a join kind (form, symbol) and a
    separator as in join_ring; P is replaced by P and Q joined. Balanced join kinds as join_ring: the first 20,000 tries keep
    anything new, the kinds kept by then are the accepted ones and each then fills ring_max // accepted. seen: digit shapes
    already kept (updated). info: whole piece per help example, accepted join kinds, kept per kind."""
    ring_max, cap = cons['widen_ring_max'], 1000 * cons['widen_ring_max']
    runs = tool_runs(tool)
    syms = symbols(helps)
    brackets = any('(' in h['prompt'] for h in helps) and any(')' in h['prompt'] for h in helps)
    kinds = [(f, s) for f in (range(6) if brackets else (0, 1, 4, 5)) for s in syms]
    def does_all_the_work(prompt):   # the tool answers `1` with no calculator steps
        try:
            res = tool.evaluate(prompt)
        except Exception:
            return False
        return res['value'] == '1' and not res['steps']
    hosts = []   # (kind, tokens, (i, j), whole piece text) for each help example that has a whole piece
    wholes = {}
    for h in helps:
        t, sl = value_slots(h['prompt'], runs)
        best = None
        for i, j in sl:
            if does_all_the_work(swap(t, i, j, '1')) and (best is None or len(''.join(t[i:j])) > len(''.join(t[best[0]:best[1]]))):
                best = (i, j)
        wholes[h['prompt']] = ''.join(t[best[0]:best[1]]) if best else None
        if best:
            hosts.append((h['kind'], t, best, wholes[h['prompt']]))
    out, tries, kept = [], 0, {}
    accepted = None   # set after the probe
    while hosts and kinds and len(out) < ring_max and tries < cap:
        if accepted is not None:
            open_ = [k for k in accepted if kept.get(k, 0) < ring_max // len(accepted)]
            if not open_:
                break
        else:
            open_ = kinds
        tries += 1
        kind, t, (i, j), p = rng.choice(hosts)
        q = rng.choice(hosts)[3]
        form, s = rng.choice(open_)
        cand = swap(t, i, j, join_form(p, q, s, form, rng.choice(['', ' '])))
        sh = shape(cand)
        if sh not in seen and ok(cand):
            seen.add(sh)
            out.append((kind, cand))
            kept[(form, s)] = kept.get((form, s), 0) + 1
        if accepted is None and tries >= 20000:
            accepted = sorted(kept)
            if not accepted:
                break
    info = dict(wholes=wholes, accepted=[f'{f}:{s}' for f, s in (accepted if accepted is not None else sorted(kept))],
                kept={f'{f}:{s}': n for (f, s), n in sorted(kept.items())}, tries=tries)
    return out, tries, info


def layout(text):
    """The whole prompt text with every maximal run of letters and digits written as `x`, then every run of `x` separated only
    by spaces written as one `x` (a list counts once, whatever its length). Domain-free."""
    return re.sub(r'x(?: +x)+', 'x', re.sub(r'[A-Za-z0-9]+', 'x', text))


def tool_runs(tool):
    """-> runs(prompt): R1, the tool computes a value (zero steps and the caps are fine here); candidates still need the full ok."""
    def runs(prompt):
        try:
            res = tool.evaluate(prompt)
        except Exception:
            return False
        return res['value'] not in ('?', 'Fail') and not any(st[3] in ('?', 'Fail') for st in res['steps'])
    return runs


def subst_ring(tool, helps, ok, rng, cons, seen):
    """-> (examples, tries, info): the substitution ring (L8, widen_subst = max depth). Starts from the help examples (ring 1
    only); each try picks a pool entry of depth < max, one of its value slots, and one value piece Q of the help page, and
    replaces the slot by Q (wrapped in round brackets with chance 1/2 when the help page uses them). A kept result joins the
    pool one level deeper. Balanced layouts: the first 20,000 tries keep anything new; the layouts kept by then are the
    accepted ones and each then fills ring_max // accepted. seen: digit shapes already kept (updated)."""
    ring_max, cap, max_depth = cons['widen_ring_max'], 1000 * cons['widen_ring_max'], cons['widen_subst']
    brackets = any('(' in h['prompt'] for h in helps) and any(')' in h['prompt'] for h in helps)

    runs = tool_runs(tool)
    slots = {}
    vq = set()   # value pieces of the help page
    for h in helps:
        t, sl = slots.setdefault(h['prompt'], value_slots(h['prompt'], runs))
        vq.update(''.join(t[i:j]) for i, j in sl)
    vq = sorted(vq)
    pool = [(h['kind'], h['prompt'], 0) for h in helps]
    eligible = [e for e in pool if e[2] < max_depth]   # pool entries a try may pick, in pool order
    out, tries, kept, depth = [], 0, {}, {}
    accepted = None   # set after the probe
    while eligible and vq and len(out) < ring_max and tries < cap:
        if accepted is not None and all(kept.get(k, 0) >= ring_max // len(accepted) for k in accepted):
            break
        tries += 1
        kind, p, d = rng.choice(eligible)
        if p not in slots:
            slots[p] = value_slots(p, runs)
        t, sl = slots[p]
        if sl:
            i, j = rng.choice(sl)
            q = rng.choice(vq)
            if brackets and rng.random() < 0.5:
                q = '(' + q + ')'
            cand = swap(t, i, j, q)
            if cand != p:
                lay = layout(cand)
                if accepted is None or (lay in accepted and kept.get(lay, 0) < ring_max // len(accepted)):   # layout quota open
                    sh = shape(cand)
                    if sh not in seen and ok(cand):
                        seen.add(sh)
                        out.append((kind, cand))
                        kept[lay] = kept.get(lay, 0) + 1
                        depth[d + 1] = depth.get(d + 1, 0) + 1
                        pool.append((kind, cand, d + 1))
                        if d + 1 < max_depth:
                            eligible.append(pool[-1])
        if accepted is None and tries >= 20000:
            accepted = set(kept)
            if not accepted:
                break
    top = sorted(kept.items(), key=lambda kv: (-kv[1], kv[0]))[:20]
    info = dict(accepted=len(accepted if accepted is not None else kept), top_layouts=top, depth=dict(sorted(depth.items())), vq=len(vq))
    return out, tries, info


def build(tool, helps, ok, rng, cons):
    """-> (rings, stats). rings: {ring: [(kind, prompt), ...]}. ok(prompt) -> True when the domain's tool runs the prompt
    within the model's caps (mode.accept without the duplicate checks)."""
    n_rings, ring_max = cons['widen_rings'], cons['widen_ring_max']
    if cons.get('widen_join') and cons.get('widen_subst'):
        raise ValueError('widen_join and widen_subst are both set: one change at a time')
    if cons.get('widen_join_whole') and (cons.get('widen_join') or cons.get('widen_subst')):
        raise ValueError('widen_join_whole with widen_join or widen_subst: one change at a time')
    rings = {1: [(h['kind'], h['prompt']) for h in helps]}
    seen = {shape(p) for _, p in rings[1]}
    piece_list = pieces(helps)
    stats = dict(pieces=len(piece_list), tries={}, kept={})

    def keep(out, kind, cand):
        sh = shape(cand)
        if sh in seen or not ok(cand):
            return False
        seen.add(sh)
        out.append((kind, cand))
        return True

    if n_rings >= 2:   # ring 2: every single swap on the help page, in a fixed order
        out, tries = [], 0
        for kind, p in rings[1]:
            t = tokens(p)
            for i, j in spans(t):
                for pc in piece_list:
                    if len(out) >= ring_max:
                        break
                    tries += 1
                    keep(out, kind, swap(t, i, j, pc))
        rings[2], stats['tries'][2] = out, tries
    for r in range(3, n_rings + 1):   # ring r: random single swaps on ring r-1 examples
        prev, out, tries = rings[r - 1], [], 0
        cap = 1000 * ring_max
        while prev and len(out) < ring_max and tries < cap:
            tries += 1
            kind, p = rng.choice(prev)
            t = tokens(p)
            i, j = rng.choice(spans(t))
            keep(out, kind, swap(t, i, j, rng.choice(piece_list)))
        rings[r], stats['tries'][r] = out, tries
    if cons.get('widen_join'):   # the join ring, after the swap rings
        r = n_rings + 1
        rings[r], stats['tries'][r], stats['join'] = join_ring(tool, helps, rings, ok, rng, cons, seen)
        stats['symbols'] = symbols(helps)
    if cons.get('widen_join_whole'):   # the whole-formula join ring (L9): help examples only, shares `seen`
        r = n_rings + 1
        rings[r], stats['tries'][r], stats['join_whole'] = whole_join_ring(tool, helps, ok, rng, cons, seen)
    if cons.get('widen_subst'):   # the substitution ring (L8): starts from ring 1 only, shares `seen` with the swap rings
        r = n_rings + 1
        rings[r], stats['tries'][r], stats['subst'] = subst_ring(tool, helps, ok, rng, cons, seen)
    stats['kept'] = {r: len(v) for r, v in rings.items()}
    stats['per_kind'] = {r: dict(sorted(_count(k for k, _ in v).items())) for r, v in rings.items()}
    stats['sha256'] = hashlib.sha256(json.dumps({str(r): v for r, v in rings.items()}).encode()).hexdigest()
    return rings, stats


def _count(it):
    c = {}
    for x in it:
        c[x] = c.get(x, 0) + 1
    return c


def by_kind(rings, kinds):
    """{kind: {ring: [prompt, ...]}} with only the rings that hold that kind (ring 1 always does)."""
    out = {k: {} for k in kinds}
    for r, items in sorted(rings.items()):
        for kind, p in items:
            out[kind].setdefault(r, []).append(p)
    return out
