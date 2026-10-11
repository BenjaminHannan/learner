"""v9 (far transfer, 10-11): the model widens its own help page by swapping well-formed pieces between its examples.

An outside tool, the same for every domain (it knows text, not spreadsheets or RPN). Before day 1 the mode calls it once:

  ring 1 = the help page.
  ring 2 = every single swap on a ring-1 example: one well-formed piece of the example is replaced by one well-formed piece
           of any help example. A swap is kept when the domain's own tool runs the result within the model's caps (the same
           checks a practice problem passes, mode.accept). One example is kept per digit shape (every digit run read as #),
           and a shape already in an earlier ring is not kept again. Enumerated in a fixed order (no randomness).
  ring k > 2 = single swaps on random ring k-1 examples (the run's own random stream), kept by the same rules, until the
           ring holds widen_ring_max examples or the tries run out.

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


def build(tool, helps, ok, rng, cons):
    """-> (rings, stats). rings: {ring: [(kind, prompt), ...]}. ok(prompt) -> True when the domain's tool runs the prompt
    within the model's caps (mode.accept without the duplicate checks)."""
    n_rings, ring_max = cons['widen_rings'], cons['widen_ring_max']
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
