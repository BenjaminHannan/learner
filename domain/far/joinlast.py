"""L10 (spec: MARKS-L10-2026-10-12.md): edit the pieces first, join last.

A joined practice problem is drafted inside the mode's own edit step in three steps, so the A10 edits act on each piece alone
and the join (one more reference) is not exposed to them:

  1. piece 1: mode.draft on a help example (ring 1, the plain help prompt); its whole piece P1 (widen.whole_piece) is found on
     the edited draft.
  2. piece 2: Q = the whole piece of a help example (any); only Q's own text gets the A10 edits (mode.vary); the edited q is put
     in P1's place and kept when the tool runs that single-piece draft (mode.accept), at most piece_tries times.
  3. join: P1's place gets P1 and q joined by an accepted (form, symbol) and a separator (widen.join_form); a candidate must
     pass mode.accept and not be a duplicate; at most join_tries redraws of (form, symbol, separator).

Nothing in it names a spreadsheet function, operator or layout: it uses the mode's own edits and the tool's verdict.
"""
from domain import mode
from domain.far import widen


def whole_pieces(tool, helps, ctx):
    """[(prompt, piece text)] for every help example that has a whole piece, in help order (cached in ctx)."""
    cache = ctx.setdefault('joinlast_wholes', {})
    key = tuple(h['prompt'] for h in helps)
    if key not in cache:
        runs = widen.tool_runs(tool)
        out = []
        for h in helps:
            w = widen.whole_piece(h['prompt'], tool, runs)
            if w:
                out.append((h['prompt'], ''.join(w[0][w[1][0]:w[1][1]])))
        cache[key] = out
    return cache[key]


def join_last_draft(tool, helps, kinds, rng, ctx, piece_tries=20, join_tries=5, pick=None):
    """One joined problem, drafted join-last. kinds: the accepted join kinds [(form, symbol)]. -> (item, None) or (None, reason);
    item as mode.draft's (kind = piece 1's kind, ring 'joinlast'). Reasons: mode.draft's own, 'no_whole_1', 'piece2', 'join'.
    L12: pick (optional) is a function rng -> (prompt, kind) that gives piece 1's example (e.g. a widened-ring example); None keeps
    L10's draw, a plain help example (rng.choice(helps)). Piece 2 always comes from the help page's whole pieces."""
    cons = ctx['cons']
    if pick is None:
        h = rng.choice(helps)
        ex1, kind1 = h['prompt'], h['kind']
    else:
        ex1, kind1 = pick(rng)
    item1, why = mode.draft(tool, ex1, kind1, rng, ctx)
    if item1 is None:
        return None, why
    w = widen.whole_piece(item1['prompt'], tool)
    if w is None:
        return None, 'no_whole_1'
    t, (i, j) = w
    p1 = ''.join(t[i:j])
    wholes = whole_pieces(tool, helps, ctx)
    if not wholes:
        return None, 'piece2'
    qtext = rng.choice(wholes)[1]
    q = None
    for _ in range(piece_tries):
        cand, counts = mode.vary(qtext, rng, ctx['lmax'], cons['vary_p'])
        if mode.accept(tool, widen.swap(t, i, j, cand), ctx)[2] is None:
            q = cand
            break
    if q is None:
        return None, 'piece2'
    for _ in range(join_tries):
        form, s = rng.choice(kinds)
        sep = rng.choice(['', ' '])
        prompt = widen.swap(t, i, j, widen.join_form(p1, q, s, form, sep))
        if prompt in ctx['quiz_set'] or prompt in ctx['seen']:
            continue
        value, steps, why = mode.accept(tool, prompt, ctx)
        if why is None:
            return dict(kind=item1['kind'], prompt=prompt, value=value, steps=steps, edits=item1['edits'], ring='joinlast'), None
    return None, 'join'
