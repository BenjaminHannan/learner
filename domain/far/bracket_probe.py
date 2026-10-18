"""Bracket probe (zero training, scoring only): per item, the teacher-forced (TF) correctness of every round of a saved checkpoint, checked
against its free run, and what a perfect repair of any set of rounds would score.

  python3 -m domain.far.bracket_probe collect --ckpt PATH (--sha256 HEX | --no-sha) --label NAME --eval-rows eval-rows-l5.jsonl [--probe sheet-probe.jsonl]
        [--rewrites plus,minus,swap,strip,spaced] [--rewrite-strata HO] [--threads 4] [--bs 64] [--no-margins] [--self-check 256] [--limit N]
        [--validate-sample 64 | --no-validate] [--allow-premise-fail] --out DIR
  python3 -m domain.far.bracket_probe report DIR [DIR ...] (--expect HO=59/420 [L13:D=0 ...] | --no-gate) [--accept-allowed-failures] [--out report.md]

collect writes DIR/bracket-NAME.jsonl (one line per item x version: ids, strata, gold and bracket-stripped steps, d, call types, the TF call of every
round with exact / either-order flags and gates, ans_tf, the free calls / prediction / hit, the margin proxy, the wrong-round classes) and
DIR/bracket-NAME.meta.json (ckpt sha256 and whether it was checked, strata counts and the real-strata check, rewrite counts, make_row drops, the own-calls
self-check with its per-cell row counts for the original and every rewritten version, the gold-path premise check with its pass counts per version, the
hit-level and round-level identity per version, the validate_repair agreements and mismatches, failures allowed by --allow-premise-fail). report reads those files only (no model) and writes DIR/bracket-report.md. The checkpoint is refused
(and only that is reported as 'REFUSED') when --sha256 does not match; --sha256 is REQUIRED (an empty string is an error) unless --no-sha is given, which
records 'sha unchecked' in the meta. collect is FATAL (exit 1, nothing written) on a failed premise check, own-calls self-check or real-strata check unless
--allow-premise-fail is given, which records the failure in meta['allowed_failures'] (the report prints it loudly). report exits 1 when an expectation fails,
when an --expect label or key matches no run / cell, when validate_repair disagrees with its prediction (hit bit or forced tape != gold tape) in more than 5% of
any stratum or set, when D has items with a TF-wrong round and none of them was validated by a forced run (the D stratum group and every repair set empty; a D
fully solved under TF prints a note instead), when the round-level identity of the orig version
breaks in any D / D_K / D_J item or in more than 0.5% of any other stratum, when ANY failure collect let through (meta['allowed_failures'], a failed
self-check, premise check or real-strata check) is present -- unless --accept-allowed-failures is given, which accepts them one by one (a self-check
failure only against a self-check entry of that version, a premise failure against a premise entry of that version, a strata failure against a strata
entry; one not individually recorded still fails) and prints ACCEPTED ALLOWED FAILURES loudly (an empty D validation is not one of them and still fails) -- or when no --expect is given (unless --no-gate: the report then says 'GATE NOT RUN').
--expect KEY=HITS checks the hit count, KEY=HITS/N also the cell size. Gating checks are explicit raises (ProbeError and subclasses), not asserts.

THE IDENTITY (shown: read from custom_io/models/tool.py:315-374 and measured by test_bracket_probe.py on a random-init T1SD span model and on all 2,100
real eval rows). In Tool.run() the controller Z at round t depends only on the prompt and on the tape text revealed so far (entries 0..t-2); the model's
own written call reaches a later round only through the TEXT of the tape entry `op a b = r` the calculator appends. So the greedy free run equals the TF
run (gold tape revealed one entry per round, in the free run's own 7 x LE tape layout, m._full_tape) up to the first round whose TF call text differs from
the gold entry text. An item's predicted free hit = (TF call == gold call as exact text at every round 0..6, NOOP at rounds >= n) and ans_tf (the answer
read out under the full gold tape). The identity is also checked round by round (round_identity): the free calls equal the gold calls up to the first TF-wrong round and the free call at
that round equals the TF call, exact text; agreement counts per stratum and per version are in the report (the hit bit alone can agree by luck: a model
that never hits agrees on every item). Mismatches (free hit != predicted) are listed with the first differing round and a reason class: either-order-only
(add/mul/min/max written commuted: other tape text), normalised-number-only (same numbers, e.g. a leading zero), extra call, missing call / NOOP,
alternative program (a different call whose run still reaches the answer), other. What the identity does NOT cover, each a place it can fail on a trained
checkpoint: (1) a wrong call that still reaches the right answer (alternative program: free hit while predicted miss); (2) the calculator's reply or the
LE = 40 truncation making a tape entry differ from the gold entry text (checked equal for every gold entry of the 2,100 real rows; collect repeats the
check on every version, see PREMISE CHECK). Note that tool.entry() cuts the text 'op a b = r' at LE = 40 characters: two different calls whose entries agree
in the first 40 characters would put the same tape text in front of the controller, so the identity is an identity of tape TEXT, not of call text, and the
forced-call check below compares the truncated entry; with the operands of these sheets (at most a few digits) no entry is cut; (3) float noise: the
default TF layout of p2_diag.teacher_forced (K = longest gold program, le = longest entry) differs from the free layout by up to 2e-5 in op logits
(measured, random init, no argmax flip), so this module always uses the free layout; the own-calls self-check run by collect measures the free/TF logit
difference on the real checkpoint (0.0 on random init at both sizes) with ONE helper, logit_diff, which compares op logits, cell probabilities and (span
copy) gate / pointer logits and reports the maximum per kind in the meta ('max_diff_by'; PremiseCheck uses the same helper); (4) a row make_row drops has no TF record; (5) after make_row drops rows, a TF chunk is the free chunk MINUS the dropped rows, so the two runs of a
chunk no longer hold the same rows (the prompt padding width, hence the float noise, may differ); the TF and free runs of a row are only compared through
the identity, which relies on the rows of a batch not influencing each other (batch independence, tested: test_free_pass_batch_independence) and on the
gold-path premise check (collect), not on identical chunks. The premise check itself runs the forced free run on the made rows of the chunk only, so
that its logit comparison holds the same rows (and padding) as the TF run even in a chunk with drops.

REPAIR COUNTERFACTUALS (suggested by the identity; validate_all checks samples with real forced free runs). C_S = share of items whose TF-wrong
rounds all carry a role in S and whose answer readout is right (or 'answer' is in S). Roles of a round, by position: r0, K_cont, J_first (round nK),
J_cont, join (last), post (round >= n) -- only for items whose program is K, J, join in order (order_ok); every other round of an item that is not order_ok
(other than r0 and post) is 'unordered' and carries no position role; with nK == 0 (K a bare cell) round 0 is J_first: r0 and J_first coincide there and the
round carries both labels, so the repair set r0 includes it; by call type: lookup (both operands grid cells), ca_mul (the 'mul y 2' call of a cell-arithmetic piece X+Y*2),
ca_add ('add x r'), join, other; d = the first round at which the bracket-stripped program differs from the gold. forced_run forces a call at a chosen
round by an instance-level patch (a forward hook on m.op_head adds a large logit to the forced op; m.written returns the forced operand strings);
restored in a finally block; tool.py is not edited. After every forced run the written call and tape entry of every forced (row, round) are
asserted equal to exactly the forced call (entry(op, a, b, calc(op, a, b)); no call for a forced NOOP), else ForcedCallError: a competing hook or a
changed controller can no longer silently leave a call unforced. Forced rows share their chunk with other rows (forced and unforced); this is safe only
because the rows of a batch do not influence each other (batch independence, tested). collect RUNS the check (validate_all) on the original items: every D
item with exactly one TF-wrong round (and D_K / D_J), a seeded sample (default 64 per stratum) of such items in every other stratum, the gold call forced at
that round, the free hit compared with ans_tf AND the forced run's tape with the gold tape (exact text, every round; a tape mismatch is a mismatch); and the repair sets r0, J_first, d, r0+J_first on the D items whose wrong rounds all lie in the set (the gold
call forced at all of them). The agreements and mismatches are in the meta and the report's gate section; a mismatch rate above 5% in any stratum or set is
a FAIL line there and makes the report exit 1.

PREMISE CHECK (collect, every version -- orig, each rewrite, and the probe rows): the gold calls forced into a free run reproduce the gold tape text
exactly and the free and TF runs agree in gate / span-pointer logits (PremiseCheck, riding on tf_pass's own TF run); pass counts per version, the rows make_row
dropped (reported as NOT CHECKED, never as passes) and the number of chunks the logits were compared on are in the meta. A failure is fatal unless
--allow-premise-fail.

MARGINS are a PROXY (suggested), NOT correctness: log p(op) + per operand [gold string is a number token of the visible context: logsigmoid(gate) +
logsumexp of the span pointer's log-softmax over the marked units-digit positions; else logsigmoid(-gate) + the cells' log-prob], logaddexp over both
operand orders for add/mul/min/max. It reuses span_gold's marking and cell_ids, never calls m.loss(), and defines no correct/wrong anywhere. (Checked: for
rows whose operands are all number tokens it equals -(op CE) - span_call of Tool.span_terms; without span copy it equals -(op CE) - the cells NLL of
Tool.call_loss -- both ONLY for calls whose two operands differ: call_loss takes logaddexp(lab, lba) over the two orders of a commutative op also when
sa == sb, which adds log 2, while call_logprob takes the logaddexp only when sa != sb, so for sa == sb the proxy is log 2 below the training term.)

Layouts (parse_layout) follow the tree domain/tools/sheet evaluates: the root is the last + or - at bracket depth 0, else the last * or /; a formula that is one
piece (X+Y*2 alone, A2/A3) has no layout.

Strata (eval-rows-l5.jsonl; the real file has 106 / 60 / 46 / 126): D = HO & 4 calls & a cell-arithmetic piece (join_gap.CA, or any X+Y*2); D_K / D_J =
the piece in K / J; HO_CA_all = HO & such a piece; HO4 (139), HO4_nonD (33), HO_nonCA (294), HPO_CA (146), twins = S5 rows in '(K)+(J)' / '(K)-(J)' with
such a piece (41); F4x / F4_other = probe F4-two rows with / without the ')*(' layout. Rewrites of a '(K)*(J)' item: plus '(K)+(J)', minus '(K)-(J)'
(skipped where K < J: the tool refuses a negative), swap '(J)*(K)', strip 'K*J', spaced ')   *   ('.
"""
import argparse
import contextlib
import json
import math
import os
import random
import re
import sys
from collections import Counter, defaultdict

from domain.far import join_gap as JG
from domain.far import learn_probe as LP
from domain.far import p2_diag as P2
from domain.far import sheet_probe as SP
from domain.tools import sheet
from domain.tools import Fail, Runner
from learnlab.metrics import wilson_interval

N_RES = 7
NOOP = 'noop'
SYM = JG.SYM
CA_FULL = re.compile(r'[A-Z]\d+\+[A-Z]\d+\*2')          # the cell-arithmetic piece X+Y*2 (join_gap.CA is the A/B-column case)
CA_PARTS = re.compile(r'([A-Z])(\d+)\+([A-Z])(\d+)\*2')
LAYOUTS = ('(K)*(J)', '(K)+(J)', '(K)-(J)', 'K+J', 'K-J', 'K*J')
REWRITES = ('plus', 'minus', 'swap', 'strip', 'spaced')
ROLES = ('r0', 'K_cont', 'J_first', 'J_cont', 'join', 'post')
TYPES = ('lookup', 'ca_mul', 'ca_add', 'join', 'other')
REAL_STRATA = {'D': 106, 'D_K': 60, 'D_J': 46, 'HO_CA_all': 126, 'HO4': 139, 'HO4_nonD': 33}
STRATA_ORDER = ('D', 'D_K', 'D_J', 'HO4_nonD', 'HO_CA_all', 'HO_nonCA', 'HPO_CA', 'twins')
REPAIR_SETS = {'none': (), 'r0': ('r0',), 'J_first': ('J_first',), 'r0+J_first': ('r0', 'J_first'), 'ca_mul': ('ca_mul',), 'ca_add': ('ca_add',),
               'd': ('d',), 'join': ('join',), 'answer': ('answer',), 'lookup': ('lookup',), 'K_cont': ('K_cont',), 'J_cont': ('J_cont',)}
LARGE_LOGIT = 1e4            # forced_run: added to the forced op's logit


# ---------- small pure helpers ----------

class ChecksumRefused(ValueError):
    """The checkpoint's sha256 is not the one asked for (the only error main() reports as REFUSED)."""


class ProbeError(RuntimeError):
    """A gating check of this module failed (raised explicitly, never by `assert`, so that python -O cannot strip it)."""


class StrataError(ProbeError):
    """check_real_strata: the eval rows do not have the strata counts of the real eval-rows-l5 file."""


class TFRunError(ProbeError):
    """tf_run: an ans_drill draw happened during the teacher-forced run."""


def check_sha(path, expect):
    """Refuse (ChecksumRefused, a ValueError) a checkpoint whose sha256 is not `expect` (case-insensitive); expect None = no check; an empty `expect`
    is a ValueError (never a silent no-check). -> the digest."""
    got = LP.sha256_file(path)
    if expect is not None:
        want = expect.strip().lower()
        if not want:
            raise ValueError('an empty sha256 is not a checksum (pass the digest, or no check at all)')
        if got != want:
            raise ChecksumRefused(f'checkpoint sha256 mismatch for {path}: got {got}, expected {want}')
    return got


def wilson(k, n):
    """95% Wilson interval of k / n as (lo, hi) in [0, 1]; None when n == 0. learnlab.metrics.wilson_interval (which raises on n == 0, hence the
    None here). The former local formula used z = 1.96 where the library uses 1.959964: the two agree to < 2e-5 for every k, n tested (including
    k = 0, lo exactly 0.0, and k = n, hi exactly 1.0), far below the 0.1-point precision frac() prints, so the library one replaces it."""
    if not n:
        return None
    return wilson_interval(int(k), int(n))


def frac(k, n):
    """'k/n = p% [lo, hi]' (Wilson 95%), the denominator always shown."""
    if not n:
        return f'{k}/{n}'
    lo, hi = wilson(k, n)
    return f'{k}/{n} = {100 * k / n:.1f}% [{100 * lo:.1f}, {100 * hi:.1f}]'


# ---------- rows: layout, pieces, program, provenance ----------

def parse_layout(f):
    """Top-level layout of a formula (no leading '=') -> (layout, op, K, J) with K, J the piece texts (brackets of a '(K)op(J)' layout removed), or
    None. The split is the ROOT of the tree domain/tools/sheet evaluates: operators + - * / at bracket depth 0, * and / bind tighter than + and -, and
    equal levels associate to the left, so the root is the LAST + or - at depth 0, else the last * or /; K is everything before it, J everything after
    ('C1*A1+B1*2' -> K 'C1*A1', J 'B1*2'; 'SUM(A1:A2)+B1+B2*2' -> K 'SUM(A1:A2)+B1', J 'B2*2'; 'SUM(A1:A2)*B1/B2' -> K 'SUM(A1:A2)*B1', J 'B2').
    The program of K then that of J then the root call is then the sheet's own call order (checked by _prep_row's order_ok and by the tests on all real
    rows). A formula that is one piece is not a join: the cell-arithmetic atom 'A1+B2*2' on its own, or one operator between two bare cells ('A2/A3')."""
    f = f.strip()
    if CA_FULL.fullmatch(f):
        return None
    pos = JG.depth0(f, '+-*/')
    if not pos or (len(pos) == 1 and '(' not in f):
        return None
    low = [i for i in pos if f[i] in '+-']
    i = (low or pos)[-1]
    if i == 0:
        return None
    K, J = f[:i].strip(), f[i + 1:].strip()
    if not K or not J:
        return None
    kb, jb = JG.strip_outer(K), JG.strip_outer(J)
    if kb and jb:
        return f'(K){f[i]}(J)', f[i], kb, jb
    return f'K{f[i]}J', f[i], K, J


class _Tag(int):
    """An int that remembers where it came from: ('cell', 'B2'), ('res', step index); a plain int is a formula constant."""

    def __new__(cls, v, src):
        o = super().__new__(cls, v)
        o.src = src
        return o


class _ProvRunner(Runner):
    def __init__(self):
        super().__init__()
        self.srcs = []

    def call(self, op, a, b):
        s = (getattr(a, 'src', ('const',)), getattr(b, 'src', ('const',)))
        r = super().call(op, int(a), int(b))
        self.srcs.append(s)
        return _Tag(r, ('res', len(self.steps) - 1))


def provenance(prompt):
    """-> per step ((src of a), (src of b)) with src ('cell', 'B2') / ('res', j) / ('const',); None when the prompt cannot run. Re-runs the sheet
    tool's own parser and evaluator with tagged ints, so it cannot disagree with sheet.evaluate (checked by the tests)."""
    try:
        grid_text, formula = prompt.split(';')
        grid = {c: [_Tag(v, ('cell', f'{c}{i + 1}')) for i, v in enumerate(vs)] for c, vs in sheet._parse_grid(grid_text).items()}
        p = sheet._Parser(sheet._tokens(formula.strip()[1:]))
        node = p.expr()
        run = _ProvRunner()
        sheet._ev(node, grid, run)
        return run.srcs
    except (Fail, RecursionError, ValueError, IndexError):
        return None


def piece_steps(prompt, formula):
    return [tuple(s) for s in sheet.evaluate(JG.piece_prompt(prompt, formula))['steps']]


def _prep_row(r):
    """One eval/probe row -> the prepared item: gold steps, layout, K / J, nK, nJ, ca_pos, flat program, d, call types (module docstring)."""
    prompt = r['prompt']
    res = sheet.evaluate(prompt)
    steps = [tuple(s) for s in res['steps']]
    f = prompt.split(';', 1)[1].strip()[1:]
    p = dict(id=r['id'], base_id=r.get('base_id', r['id']), version=r.get('version', 'orig'), split=r.get('split'), kind=r.get('kind'),
             partner=r.get('partner'), prompt=prompt, value=res['value'], answer=r.get('answer', res['value']),
             accepted=list(r.get('accepted', [r.get('answer', res['value'])])), steps=steps, n=len(steps), layout=None, op=None, K=None, J=None,
             nK=None, nJ=None, order_ok=False, ca_pos=None, ca=None, flat_steps=steps, paren_sensitive=False, d=None, flat_value=res['value'],
             types=['other'] * len(steps), strata=[])
    p['answer_ok'] = res['value'] == p['answer']
    lay = parse_layout(f)
    if lay is None:
        return p
    p['layout'], p['op'], p['K'], p['J'] = lay
    ks, js = piece_steps(prompt, p['K']), piece_steps(prompt, p['J'])
    p['nK'], p['nJ'] = len(ks), len(js)
    p['order_ok'] = (steps[:p['nK']] == ks and steps[p['nK']:p['nK'] + p['nJ']] == js and p['n'] == p['nK'] + p['nJ'] + 1
                     and steps[-1][0] == sheet.BIN_OP[p['op']])
    kc, jc = bool(CA_FULL.fullmatch(p['K'])), bool(CA_FULL.fullmatch(p['J']))
    p['ca_pos'] = 'K' if kc and not jc else 'J' if jc and not kc else 'KJ' if kc and jc else None
    if p['layout'].startswith('('):
        flat = sheet.evaluate(JG.piece_prompt(prompt, f"{p['K']}{p['op']}{p['J']}"))
        p['flat_steps'], p['flat_value'] = [tuple(s) for s in flat['steps']], flat['value']
        p['paren_sensitive'] = p['flat_steps'] != steps
        if p['paren_sensitive']:
            p['d'] = next((i for i, (a, b) in enumerate(zip(steps, p['flat_steps'])) if a != b), min(len(steps), len(p['flat_steps'])))
    prov = provenance(prompt)
    start = {'K': 0, 'J': p['nK']}.get(p['ca_pos'])
    if start is not None:
        mt = CA_PARTS.fullmatch(p[p['ca_pos']])
        x, y = mt.group(1, 2), mt.group(3, 4)
        grid = P2.grid_and_refs(prompt)[0]
        xv, yv = grid.get((x[0], int(x[1]))), grid.get((y[0], int(y[1])))
        shape = (start + 1 < p['n'] and steps[start][0] == 'mul' and steps[start][2] == '2' and steps[start + 1][0] == 'add'
                 and steps[start + 1][2] == steps[start][3])
        p['ca'] = dict(start=start, x=x[0] + x[1], y=y[0] + y[1], xv=xv, yv=yv, shape_ok=bool(shape))
    for k in range(p['n']):
        if k == p['n'] - 1 and p['order_ok']:
            t = 'join'
        elif p['ca'] and p['ca']['shape_ok'] and k == p['ca']['start']:
            t = 'ca_mul'
        elif p['ca'] and p['ca']['shape_ok'] and k == p['ca']['start'] + 1:
            t = 'ca_add'
        elif prov and k < len(prov) and prov[k][0][0] == 'cell' and prov[k][1][0] == 'cell':
            t = 'lookup'
        else:
            t = 'other'
        p['types'][k] = t
    return p


def prep_row(r):
    """_prep_row plus the strata labels (a row may carry its own 'strata', as the rewritten versions of an item do)."""
    p = _prep_row(r)
    p['strata'] = list(r.get('strata') or strata_of(p))
    return p


def strata_of(p):
    """Stratum labels of a prepared item (module docstring)."""
    s = [p['split']] if p['split'] else []
    ca = p['ca_pos'] is not None
    if p['split'] == 'HO':
        if p['n'] == 4:
            s.append('HO4')
            s.append('D' if ca else 'HO4_nonD')
            if ca:
                s.append('D_' + p['ca_pos'])
        s.append('HO_CA_all' if ca else 'HO_nonCA')
    if p['split'] == 'HPO' and ca:
        s.append('HPO_CA')
    if p['split'] == 'S5' and p['layout'] in ('(K)+(J)', '(K)-(J)') and ca:
        s.append('twins')
    if p['split'] == 'F4-two':
        s.append('F4x' if p['layout'] == '(K)*(J)' else 'F4_other')
    return s


def prepare(rows):
    return [prep_row(r) for r in rows]


def strata_counts(preps):
    c = Counter(s for p in preps for s in p['strata'])
    return dict(c)


def check_real_strata(preps, expect=None):
    """The real eval file: D 106, D_K 60, D_J 46, HO_CA_all 126, HO4 139, HO4_nonD 33. -> the counts; StrataError on a mismatch."""
    c = strata_counts(preps)
    for k, v in (expect or REAL_STRATA).items():
        if c.get(k, 0) != v:
            raise StrataError(f'stratum {k}: {c.get(k, 0)} rows, expected {v}')
    return c


# ---------- rewrites of a '(K)*(J)' row ----------

def _prompt_with(p, formula):
    return f'{JG.grid_of(p["prompt"])} ; ={formula}'


def spaced_ok():
    """The sheet tokenizer skips spaces (TOKEN's leading \\s*): the spaced rewrite evaluates to the unspaced program."""
    a, b = 'A: 3 4 | B: 5 6 ; =(SUM(A1:A2))*(MAX(B1:B2))', 'A: 3 4 | B: 5 6 ; =(SUM(A1:A2))   *   (MAX(B1:B2))'
    return sheet.evaluate(a) == sheet.evaluate(b) and sheet.evaluate(a)['value'] != '?'


def rewrite_prompt(p, name):
    """The rewritten prompt of a '(K)*(J)' item, or None (not that layout)."""
    if p['layout'] != '(K)*(J)' or p['op'] != '*':
        return None
    K, J = p['K'], p['J']
    f = {'plus': f'({K})+({J})', 'minus': f'({K})-({J})', 'swap': f'({J})*({K})', 'strip': f'{K}*{J}',
         'spaced': f'({K})   *   ({J})'}[name]
    return _prompt_with(p, f)


def relation_ok(p, v, name):
    """-> (ok, reason): the new item v has the program relation to p that rewrite `name` promises (value != '?' for plus / minus / strip)."""
    n, nK, nJ = p['n'], p['nK'], p['nJ']
    if v['value'] == '?':
        return False, 'value ?'
    if name in ('plus', 'minus'):
        want = 'add' if name == 'plus' else 'sub'
        ok = (v['steps'][:n - 1] == p['steps'][:n - 1] and len(v['steps']) == n and v['steps'][n - 1][0] == want
              and v['steps'][n - 1][1:3] == p['steps'][n - 1][1:3])
    elif name == 'swap':
        jn = p['steps'][n - 1]
        ok = (v['value'] == p['value'] and v['steps'] == p['steps'][nK:nK + nJ] + p['steps'][:nK] + [('mul', jn[2], jn[1], jn[3])])
    elif name == 'strip':
        ok = v['steps'] == p['flat_steps']
    else:
        ok = v['steps'] == p['steps'] and v['value'] == p['value']
    return ok, '' if ok else 'relation'


def make_version(p, name, spaced=None):
    """-> (prepared version item, None) or (None, reason). Recomputes gold with sheet.evaluate and checks the promised relation. spaced: the result of
    spaced_ok() when the caller already has it (make_versions computes it once per call, not once per prompt); None = compute it here."""
    if name == 'spaced' and not (spaced_ok() if spaced is None else spaced):
        return None, 'tokenizer does not skip spaces'
    prompt = rewrite_prompt(p, name)
    if prompt is None:
        return None, 'not (K)*(J)'
    v = prep_row(dict(id=f'{p["id"]}~{name}', base_id=p['base_id'], version=name, split=p['split'], kind=p['kind'], partner=p['partner'],
                      prompt=prompt, answer=sheet.evaluate(prompt)['value']))
    ok, why = relation_ok(p, v, name)
    if not ok:
        return None, why
    v['strata'] = list(p['strata'])
    return v, None


def make_versions(preps, name, strata=('HO',)):
    """-> (versions, skipped {reason: count}) for the items of the given strata."""
    out, skip = [], Counter()
    spaced = spaced_ok() if name == 'spaced' else None          # one tokenizer check per call, not one per prompt
    for p in preps:
        if not set(strata) & set(p['strata']) or p['layout'] != '(K)*(J)':
            continue
        v, why = make_version(p, name, spaced)
        if v is None:
            skip[why] += 1
        else:
            out.append(v)
    return out, dict(skip)


# ---------- running the model: batches, the free run, the forcing patch ----------

def make_batch(m, rows):
    from custom_io.data import Dataset, collate, to_device
    ds = Dataset(rows, m.vocab, strict=False)
    return to_device(collate([ds[i] for i in range(len(rows))]), 'cpu')


def free_rows(prompts):
    """The rows domain/mode.greedy builds for a chunk of prompts."""
    return [{'id': f'g{i}', 'prompt': p, 'answer': '', 'accepted': [], 'family': '', 'level': 0} for i, p in enumerate(prompts)]


def hit_of(pred, accepted):
    """domain/score.py: the stripped answer is one of the stripped accepted answers."""
    return int(pred.strip() in {x.strip() for x in accepted})


# DEFERRED (not done here, it touches custom_io/models/tool.py): make forcing a `force` parameter of Tool.run instead of this instance-level patch.
@contextlib.contextmanager
def forcing(m, force):
    """Instance-level patch of the free run: force = {row index in the batch: {round k: (op, a, b)}}. At round k the forced rows get a large logit
    added to the forced op only (a forward hook on m.op_head; round = call order inside one run) and m.written returns the forced operand strings
    for them (an instance attribute). An op named 'noop' forces NO call. Everything else (calculator, tape write, later rounds) is the real free
    path. Restored in the finally block (hook removed, instance attribute deleted or put back); tool.py is not edited. Yields the round counters,
    cnt['raw'] = the op logits of every round BEFORE the forced op's boost (what the controller computed; PremiseCheck compares these with the TF run)."""
    from custom_io.models.tool import NAMES
    cnt = dict(op=0, written=0, raw=[])
    had = 'written' in m.__dict__
    prev = m.__dict__.get('written')
    orig = m.written

    def hook(mod, inp, out):
        k, cnt['op'] = cnt['op'], cnt['op'] + 1
        cnt['raw'].append(out.detach())
        out = out.clone()
        for i, fk in force.items():
            if k in fk:
                out[i, NAMES.index(fk[k][0])] += LARGE_LOGIT
        return out

    def written(st):
        k, cnt['written'] = cnt['written'], cnt['written'] + 1
        res = list(orig(st))
        for i, fk in force.items():
            if k in fk and fk[k][0] != NOOP:
                res[i] = (fk[k][1], fk[k][2])
        return res

    handle = m.op_head.register_forward_hook(hook)
    m.written = written
    try:
        yield cnt
    finally:
        handle.remove()
        if had:
            m.written = prev
        else:
            del m.written


def tape_texts(m, o):
    """[B][N_RES] the text of every tape entry the free run wrote (decoded from the tape the thinker saw; '' = no entry)."""
    ids, vis, le = o['tape'][1], o['tape'][2], o['le']
    out = []
    for i in range(ids.shape[0]):
        row = []
        for k in range(o['K']):
            sl = slice(k * le, (k + 1) * le)
            row.append(m.vocab.decode(ids[i, sl].tolist()) if bool(vis[i, sl].any()) else '')
        out.append(row)
    return out


class ForcedCallError(RuntimeError):
    """A forced (row, round) did not produce exactly the forced call / tape entry (something competed with the forcing patch)."""


def check_forced(m, o, force):
    """After a forced free run: for every forced (row i, round k) the call written at round k and the tape entry k must be exactly the forced call:
    entry(op, a, b, calc(op, a, b)) in the tape and the call (k + 1, op, a, b, result) in o['calls'][i]; for a forced NOOP no call at round k + 1 and an
    empty tape entry. Raises ForcedCallError listing the first offenders."""
    from custom_io.models.tool import calc, entry
    tapes = tape_texts(m, o)
    bad = []
    for i, fk in force.items():
        calls = {c[0] - 1: tuple(c[1:4]) for c in o['calls'][i]}
        for k, (op, a, b) in fk.items():
            if op == NOOP:
                want_call, want_tape = None, ''
            else:
                want_call, want_tape = (op, a, b), entry(op, a, b, calc(op, a, b))
            got_call, got_tape = calls.get(k), tapes[i][k] if k < len(tapes[i]) else None
            if got_call != want_call or got_tape != want_tape:
                bad.append(f'row {i} round {k}: forced {(op, a, b)} -> wanted call {want_call} / tape {want_tape!r}, got call {got_call} / tape {got_tape!r}')
    if bad:
        raise ForcedCallError(f'{len(bad)} forced call(s) not written exactly as forced (a competing op_head hook or a changed controller?): '
                              + '; '.join(bad[:5]))


def free_chunk(m, prompts, force=None):
    """One chunk of a free run exactly as mode.greedy does it (run, then talk on the run's state), optionally with forced calls
    ({row index: {round: (op, a, b)}}), each checked after the run (check_forced). -> (o, answers, batch)."""
    import torch
    m.eval()
    batch = make_batch(m, free_rows(prompts))
    with torch.no_grad():
        if force:
            with forcing(m, force) as cnt:
                o = m.run(batch)
            o['op_raw'] = cnt['raw']              # the op logits before the forcing boost, per round (PremiseCheck)
            check_forced(m, o, force)
        else:
            o = m.run(batch)
        ans = m.talk(m.state_of(o), batch)
    return o, ans, batch


def free_records(m, o, ans, accepted, with_tape=False):
    tapes = tape_texts(m, o) if with_tape else None
    out = []
    for i, a in enumerate(ans):
        rec = dict(calls=[list(c) for c in o['calls'][i]], pred=a, hit=hit_of(a, accepted[i]) if accepted[i] is not None else None)
        if with_tape:
            rec['tape'] = tapes[i]
        out.append(rec)
    return out


def free_pass(m, rows, bs=64, with_tape=False):
    """Greedy free run of every row, in this order and in chunks of bs (domain/score.py hands domain/mode.greedy the whole ordered row list, which
    chunks it by 64: pass the rows in that order to reproduce its batches). Same run + talk as mode.greedy (tested equal), but keeps the round of
    every call. rows: dicts with 'prompt' and optionally 'accepted' / 'answer'. -> per row dict(calls [[t, op, a, b, r]], pred, hit)."""
    out = []
    for s in range(0, len(rows), bs):
        chunk = rows[s:s + bs]
        o, ans, _ = free_chunk(m, [r['prompt'] for r in chunk])
        out += free_records(m, o, ans, [r.get('accepted', [r['answer']] if 'answer' in r else None) for r in chunk], with_tape)
    return out


def forced_run(m, rows, force, bs=64):
    """Free run of rows in which the call at (row index, round k) is FORCED to (op, a, b) text: force = {(i, k): (op, a, b)} with i the index in
    `rows`. -> per row dict(calls, pred, hit, tape [N_RES entry texts]). Chunking as free_pass; a forced row shares its chunk with the other rows (forced
    or not), which is safe because batch-mates do not influence each other. Raises ForcedCallError unless every forced call was written exactly."""
    out = []
    for s in range(0, len(rows), bs):
        chunk = rows[s:s + bs]
        sub = defaultdict(dict)
        for (i, k), call in force.items():
            if s <= i < s + len(chunk):
                sub[i - s][k] = tuple(call)
        o, ans, _ = free_chunk(m, [r['prompt'] for r in chunk], dict(sub))
        out += free_records(m, o, ans, [r.get('accepted', [r['answer']] if 'answer' in r else None) for r in chunk], True)
    return out


DIFF_KINDS = ('op', 'cells', 'gate', 'pointer')


def _finite_max(x):
    """float(x), with NaN read as +inf (a NaN difference must never look like a pass: nan > tol is False)."""
    x = float(x)
    return math.inf if math.isnan(x) else x


def merge_diff(a, b):
    """The per-kind maximum of two logit_diff dicts (None = not compared on that side)."""
    return {k: (b[k] if a[k] is None else a[k] if b[k] is None else max(a[k], b[k])) for k in DIFF_KINDS}


def diff_overall(d):
    """The largest difference over the kinds that were compared; None when none was."""
    v = [x for x in d.values() if x is not None]
    return max(v) if v else None


def logit_diff(steps_a, steps_b, compare_op=True):
    """THE comparison of two runs' controller outputs (own_call_identity and PremiseCheck both use it). steps_*: the `steps` of two Tool.run outputs
    (per round a tuple (op logits [B, ops], cell probabilities [B, 2 * CELLS, V]) and, with span copy, a third item with the span gate logits ga / gb and
    the pointer logits la / lb over the visible positions). -> dict(op, cells, gate, pointer): the largest |difference| of that kind over all rounds and
    rows; 'op' only when compare_op (None = not compared: op logits are skipped by a caller that cannot compare them, gate / pointer when a model has no
    span copy). A model without span copy still has its op logits and cell probabilities compared. Pointer logits count at positions visible in BOTH
    runs. NaN counts as inf."""
    import torch
    if len(steps_a) != len(steps_b):
        raise ProbeError(f'logit_diff: {len(steps_a)} rounds against {len(steps_b)}')
    out = dict.fromkeys(DIFF_KINDS)

    def put(kind, d):
        v = _finite_max(d.max()) if d.numel() else 0.0
        out[kind] = v if out[kind] is None else max(out[kind], v)

    for a, b in zip(steps_a, steps_b):
        if len(a) != len(b):
            raise ProbeError('logit_diff: one run has span-copy outputs and the other has not')
        if compare_op:
            put('op', (a[0].float() - b[0].float()).abs())
        put('cells', (a[1].float() - b[1].float()).abs())
        if len(a) >= 3:
            for key in ('ga', 'gb'):
                put('gate', (a[2][key].float() - b[2][key].float()).abs())
            vis = a[2]['m'] & b[2]['m']
            for key in ('la', 'lb'):
                d = (a[2][key].float() - b[2][key].float()).abs()
                put('pointer', torch.where(vis, d, torch.zeros_like(d)))
    return out


class PremiseCheck:
    """The premise of the identity as a tf_pass observer. For each TF chunk (the made rows of bs consecutive items; make_row-dropped rows are left out of
    both runs) the GOLD calls (NOOP past the program) are forced into a free run of exactly those rows and (1) the free tape text must equal the gold tape
    text, row by row; (2) the gate / span-pointer logits of that free run and of the TF run must agree, row by row. Because both runs hold the same rows
    (padding included) a chunk with drops is compared too. Nothing about a dropped row is checked: result() lists it as 'dropped'/'not checked'.
    The logits compared are logit_diff's: op logits (the forced free run's are taken BEFORE the forcing boost, which would otherwise alter them on every forced
    round -- here all of them), cell probabilities, and with span copy the gate and pointer logits."""

    def __init__(self, m, items, bs=64):
        self.m, self.items, self.bs = m, items, bs
        self.ok_idx, self.bad_idx, self.worst, self.compared, self.rows_compared = [], [], dict.fromkeys(DIFF_KINDS), 0, 0

    def __call__(self, idx, g, o2):
        chunk = [self.items[i] for i in idx]
        force = {j: {k: (tuple(p['steps'][k][:3]) if k < p['n'] else (NOOP, '', '')) for k in range(N_RES)} for j, p in enumerate(chunk)}
        o, _, _ = free_chunk(self.m, [p['prompt'] for p in chunk], force)
        tapes = tape_texts(self.m, o)
        for j, i in enumerate(idx):
            (self.ok_idx if tapes[j] == list(g['tape'][j]) else self.bad_idx).append(i)
        raw = o.get('op_raw')                    # the free run's op logits before the forcing boost: what the controller computed, comparable to the TF run's
        have_raw = raw is not None and len(raw) == len(o['steps'])
        steps = [(raw[k],) + tuple(st[1:]) for k, st in enumerate(o['steps'])] if have_raw else o['steps']
        self.worst = merge_diff(self.worst, logit_diff(steps, o2['steps'], compare_op=have_raw))   # op (unboosted), cells, gate, pointer
        self.compared += 1
        self.rows_compared += len(idx)

    def result(self, tf_out):
        """tf_out: the tf_pass output of the same items. -> dict(n = rows checked, ok, bad_ids, bad_idx, dropped = rows make_row drops (not checked),
        dropped_idx, max_diff = largest logit difference over the rows compared and over all kinds (None when no chunk was compared), max_diff_by =
        {op, cells, gate, pointer: largest difference of that kind, None = not compared} (logit_diff), logit_chunks = [chunks compared, chunks],
        logit_rows = rows compared)."""
        dropped_idx = [i for i, o in enumerate(tf_out) if not o['made']]
        bad = sorted(self.bad_idx)
        return dict(n=len(self.ok_idx) + len(bad), ok=len(self.ok_idx), bad_ids=[self.items[i]['id'] for i in bad], bad_idx=bad,
                    dropped=len(dropped_idx), dropped_idx=dropped_idx, max_diff=diff_overall(self.worst), max_diff_by=dict(self.worst),
                    logit_chunks=[self.compared, -(-len(self.items) // self.bs)], logit_rows=self.rows_compared)


def tf_with_premise(m, items, bs=64, margins=False):
    """THE teacher-forced pass collect runs: tf_pass with the premise check riding on it (one TF run per chunk serves both). -> (tf_pass output,
    PremiseCheck.result). collect_items goes through this (the tests' gold_path_check wrapper too)."""
    pcheck = PremiseCheck(m, items, bs)
    tf = tf_pass(m, items, bs, margins=margins, observer=pcheck)
    return tf, pcheck.result(tf)


# ---------- the teacher-forced pass ----------

def judge(call, gold):
    """call = (op, a, b) the model wrote (op 'noop' = no call), gold = (op, a, b) or None (no call expected) -> (exact, either).
    exact: the same op and operand TEXT (the tape entry text is then identical); either: join_gap.same_call (numbers, either order for
    add/mul/min/max). A NOOP is right exactly when no call is expected."""
    if gold is None:
        return call[0] == NOOP, call[0] == NOOP
    if call[0] == NOOP:
        return False, False
    return tuple(call) == tuple(gold), JG.same_call(tuple(call), tuple(gold))


def drill_state(m):
    return (dict(m.drill_stats), m._drill_rng.getstate())


def tf_run(m, batch, g):
    """The TF run in the free-run tape layout (m._full_tape = True: N_RES entries of LE chars, restored afterwards): needs g['op'] [B, N_RES] and
    g['tape'] [B][N_RES]. The run is ALWAYS in eval mode (m.eval() is called here, and stays on the model); o['caller_training'] records whether
    the caller handed a model in training mode. -> (o, answers under the full gold tape)."""
    import torch
    was_training = bool(m.training)     # what the caller handed us; recorded in the result, the run itself is always in eval mode
    m.eval()
    before = drill_state(m)
    prev = m._full_tape
    m._full_tape = True
    try:
        with torch.no_grad():
            o = m.run(batch, gold=g)
            ans = m.talk(m.state_of(o), batch)
    finally:
        m._full_tape = prev
    if drill_state(m) != before:
        raise TFRunError('an ans_drill draw happened during the teacher-forced run (the run is not deterministic)')
    o['caller_training'] = was_training
    return o, ans


def tf_rounds(m, o):
    """Per row, per round: the model's argmax op name, its written operand strings (m.written, exact text), the gate logits and whether the span
    (gate >= 0) or the cells were used for each operand."""
    import torch
    from custom_io.models.tool import NAMES
    steps = o['steps']
    B = len(o['calls'])
    with torch.no_grad():
        ops = [st[0].argmax(-1).tolist() for st in steps]
        wr = [m.written(st) for st in steps]
    out = [[] for _ in range(B)]
    for k, st in enumerate(steps):
        ga, gb = (st[2]['ga'].tolist(), st[2]['gb'].tolist()) if len(st) >= 3 else ([None] * B, [None] * B)
        for i in range(B):
            out[i].append(dict(op=NAMES[ops[k][i]] if ops[k][i] else NOOP, a=wr[k][i][0], b=wr[k][i][1], ga=ga[i], gb=gb[i],
                               sa=None if ga[i] is None else ga[i] >= 0, sb=None if gb[i] is None else gb[i] >= 0))
    return out


def judge_rounds(rounds, gold):
    """gold = [(op, a, b)] -> rounds with 'ex' / 'ei' (exact / either-order) added, one per round."""
    for k, r in enumerate(rounds):
        r['ex'], r['ei'] = judge((r['op'], r['a'], r['b']), gold[k] if k < len(gold) else None)
    return rounds


def call_logprob(m, st, i, op, sa, sb, ma, mb):
    """The proxy log-prob of one call of row i at one round (module docstring): op + operands, logaddexp over both orders for add/mul/min/max.
    ma / mb: bool numpy [N] marks of the units-digit positions of every visible occurrence of sa / sb (span_gold). NOOP: log p(NOOP)."""
    import torch
    import torch.nn.functional as F
    from custom_io.models.ledger import COMM
    from custom_io.models.tool import CELLS, NAMES
    lop = F.log_softmax(st[0][i].float(), -1)
    if op == NOOP:
        return float(lop[0])
    oi = NAMES.index(op)
    lp = torch.log(st[1][i] + 1e-6)

    def cells(s, side):
        t = m.cell_ids(s)
        row = lp[side * CELLS:(side + 1) * CELLS]
        return sum(float(row[j, x]) for j, x in enumerate(t) if x >= 0)

    def side(s, mark, which):
        if not m.span_copy:
            return cells(s, which)
        sp = st[2]
        lg, gl = sp['la' if which == 0 else 'lb'][i].float(), sp['ga' if which == 0 else 'gb'][i].float()
        mk = torch.from_numpy(mark)
        if bool(mk.any()):
            return float(F.logsigmoid(gl) + torch.logsumexp(lg[mk], 0) - torch.logsumexp(lg, 0))
        return float(F.logsigmoid(-gl)) + cells(s, which)

    lab = side(sa, ma, 0) + side(sb, mb, 1)
    if oi in COMM and sa != sb:
        lba = side(sb, mb, 0) + side(sa, ma, 1)
        lab = max(lab, lba) + math.log1p(math.exp(-abs(lab - lba)))
    return float(lop[oi]) + lab


def margins_batch(m, o, batch, flats=None):
    """Proxy log-prob of the gold call at every round (rounds >= n: log p(NOOP)), per batch row; flats[i] = (round d, (op, a, b)) adds the proxy
    of that bracket-stripped call at round d. NOT correctness (module docstring). -> [dict(lp [N_RES], lp_flat)]."""
    from custom_io.models.tool import NAMES, calc, entry
    rows, T = batch['rows'], batch['prompt_ids'].shape[1]
    base = [m.row_gold(r) + (r['answer'], False) for r in rows]
    Ma = Mb = None
    if m.span_copy:
        Ma, Mb, _, _ = m.span_gold(rows, T, o['le'], o['K'], base)
    flat_marks = None
    if m.span_copy and flats and any(flats):
        golds = []
        for i, gld in enumerate(base):
            ops, opd, tape = list(gld[0]), list(gld[1]), list(gld[2])
            if flats[i] is not None and flats[i][1][0] != NOOP:
                d, (fop, fa, fb) = flats[i]
                if d < len(opd):
                    opd[d] = (fa, fb)
                elif d == len(opd) < N_RES:     # the flat program is longer than the gold: its call d comes after ALL gold entries, which are also the
                    ops.append(NAMES.index(fop))  # flat tape's entries 0..d-1 (d is the first difference); mark the operands of that call on them
                    opd.append((fa, fb))
                    tape[d] = entry(fop, fa, fb, calc(fop, fa, fb))
            golds.append((ops, opd, tape) + tuple(gld[3:]))
        flat_marks = m.span_gold(rows, T, o['le'], o['K'], golds)[:2]
    out = []
    zero = None
    for i in range(len(rows)):
        ops, opd = base[i][0], base[i][1]
        lp = []
        for k, st in enumerate(o['steps']):
            if k < len(ops):
                lp.append(call_logprob(m, st, i, NAMES[ops[k]], opd[k][0], opd[k][1], Ma[i, k] if Ma is not None else zero,
                                       Mb[i, k] if Mb is not None else zero))
            else:
                lp.append(call_logprob(m, st, i, NOOP, '', '', None, None))
        lpf = None
        if flats and flats[i] is not None:
            d, (fop, fa, fb) = flats[i]
            if d < len(o['steps']):
                lpf = call_logprob(m, o['steps'][d], i, fop, fa, fb, flat_marks[0][i, d] if flat_marks else zero,
                                   flat_marks[1][i, d] if flat_marks else zero)
        out.append(dict(lp=lp, lp_flat=lpf))
    return out


def tf_pass(m, rows, bs=64, margins=False, cons=None, observer=None):
    """Teacher-forced pass over prepared items (prep_row dicts), in chunks of bs of this list (pass the same list as free_pass to share batches).
    The gold is built with mode.make_row exactly as p2_diag.teacher_forced does; a row make_row drops gets dict(made=False, drop=reason). The run
    is the free-run tape layout (tf_run). Per made row: tf (per round: op, a, b, ga, gb, sa, sb, ex, ei), ans_tf (the answer read out under the
    full gold tape, scored as score.py does), ans_text, and with margins=True lp / lp_flat. The run is always in eval mode (every result carries caller_training: whether the model arrived in training mode); raises TFRunError if an ans_drill draw happened. observer: called after
    each TF chunk as observer(indices of its made rows, g, o) (PremiseCheck uses it to share this run instead of repeating it)."""
    from domain import mode
    from custom_io.models.tool import NAMES
    caller_training = bool(m.training)
    m.eval()
    if cons is None:
        with open(mode.CONST_PATH) as fh:
            cons = json.load(fh)
    out = [None] * len(rows)
    for s in range(0, len(rows), bs):
        idx, grows = [], []
        for i in range(s, min(s + bs, len(rows))):
            r = rows[i]
            g, why = mode.make_row(m, 'domain_sheet', r['prompt'], r['value'], [tuple(x) for x in r['steps']], cons, 'tool')
            if g is None:
                out[i] = dict(made=False, drop=why, caller_training=caller_training)
            else:
                idx.append(i)
                grows.append(g)
        if not idx:
            continue
        batch = make_batch(m, grows)
        g = m.gold(batch['rows'], 'cpu')
        o, ans = tf_run(m, batch, g)
        rounds = tf_rounds(m, o)
        if observer is not None:
            observer(idx, g, o)
        flats = None
        if margins:
            flats = []
            for i in idx:
                r = rows[i]
                fl = r['flat_steps']
                flats.append((r['d'], tuple(fl[r['d']][:3]) if r['d'] < len(fl) else (NOOP, '', '')) if r['d'] is not None else None)
            mg = margins_batch(m, o, batch, flats)
        for j, i in enumerate(idx):
            gold = [(NAMES[op], a, b) for op, (a, b) in zip(g['rowg'][j][0], g['rowg'][j][1])]
            res = dict(made=True, drop=None, tf=judge_rounds(rounds[j], gold), ans_text=ans[j], ans_tf=bool(hit_of(ans[j], rows[i]['accepted'])),
                       caller_training=caller_training)
            if margins:
                res.update(mg[j])
            out[i] = res
    return out


def own_call_identity(m, rows, bs=64):
    """Self-check of the run() path, needing no trained model: free-run each chunk, then teacher-force the model's OWN calls (its own tape entries
    as the gold, in the free-run layout) in the same chunk and compare. By the identity every round's TF call must equal the free call exactly
    (NOOP where it wrote none) and the answer read under that tape must equal the free answer. -> dict(n, bad [(row, round, free call, TF call)],
    ans_bad [(row, free answer, TF answer)], max_diff = the largest |difference| of any kind between the two runs, max_diff_by = {op, cells, gate,
    pointer: largest difference of that kind; None = not compared (no span copy)} -- logit_diff, the same comparison PremiseCheck uses)."""
    import torch
    from custom_io.models.tool import NAMES, entry
    bad, ans_bad, n, by = [], [], 0, dict.fromkeys(DIFF_KINDS)
    for s in range(0, len(rows), bs):
        chunk = rows[s:s + bs]
        o, ans, batch = free_chunk(m, [r['prompt'] for r in chunk])
        op = torch.zeros(len(chunk), N_RES, dtype=torch.long)
        tape = [[''] * N_RES for _ in chunk]
        gold = [[None] * N_RES for _ in chunk]
        for i in range(len(chunk)):
            for t, opn, a, b, r in o['calls'][i]:
                op[i, t - 1] = NAMES.index(opn)
                tape[i][t - 1] = entry(opn, a, b, r)
                gold[i][t - 1] = (opn, a, b)
        o2, ans2 = tf_run(m, batch, dict(op=op, tape=tape))
        rounds = tf_rounds(m, o2)
        by = merge_diff(by, logit_diff(o['steps'], o2['steps'], compare_op=True))
        for i in range(len(chunk)):
            n += 1
            for k, r in enumerate(judge_rounds(rounds[i], gold[i])):
                if not r['ex']:
                    bad.append((s + i, k, gold[i][k], (r['op'], r['a'], r['b'])))
            if ans2[i] != ans[i]:
                ans_bad.append((s + i, ans[i], ans2[i]))
    overall = diff_overall(by)
    return dict(n=n, bad=bad, ans_bad=ans_bad, max_diff=0.0 if overall is None else overall, max_diff_by=by)


# ---------- per-item analysis (records are plain dicts: a prepared item + tf + free) ----------

def position_role(rec, k):
    """The position role of round k (ROLES). Only an order_ok item (program = K steps, J steps, join) has K_cont / J_first / J_cont / join; for any
    other item every round but r0 and post is 'unordered' (nK is not a boundary there). With nK == 0 (K a bare cell, e.g. '=B3+A2*2*B3/A1') the program
    has no K steps, so round 0 IS the first J round: it is labelled 'J_first' (or 'join' when it is also the last round); r0 and J_first coincide there,
    and round_labels still gives that round the label 'r0' as well, so the repair set r0 keeps containing it."""
    n, nK = rec['n'], rec['nK']
    if k >= n:
        return 'post'
    ordered = nK is not None and rec['order_ok']
    if k == 0 and not (ordered and nK == 0):
        return 'r0'
    if not ordered:
        return 'unordered'
    if k == n - 1:                 # the join first: with nJ == 0 (a bare cell as J) round nK IS the join round
        return 'join'
    if k == nK:
        return 'J_first'
    return 'K_cont' if k < nK else 'J_cont'


def round_labels(rec, k):
    """Every role label a round carries: position role, call type ('post' past the program), 'd' for the paren divergence round. Round 0 always carries
    'r0' (for an order_ok item with nK == 0 its position role is J_first, and it carries both)."""
    lab = {position_role(rec, k)}
    if k == 0:
        lab.add('r0')
    lab.add(rec['types'][k] if k < rec['n'] else 'post')
    if rec.get('d') is not None and k == rec['d']:
        lab.add('d')
    return lab


def wrong_rounds(rec):
    return [k for k, r in enumerate(rec['tf']) if not r['ex']]


def predicted_hit(rec):
    return bool(rec['tf']) and not wrong_rounds(rec) and bool(rec['ans_tf'])


def repair_ok(rec, S):
    """The item succeeds when the rounds in role set S are repaired: every TF-wrong round carries a label in S, and the answer readout is right
    (or 'answer' is in S). S = () is no repair."""
    S = set(S)
    return all(round_labels(rec, k) & S for k in wrong_rounds(rec)) and (bool(rec['ans_tf']) or 'answer' in S)


def repair_table(recs, sets=None):
    """{name: (successes, n)} over the items that have a TF record."""
    ok = [r for r in recs if r.get('tf')]
    return {name: (sum(1 for r in ok if repair_ok(r, S)), len(ok)) for name, S in (sets or REPAIR_SETS).items()}


def mismatch_reason(rec):
    """Why free hit != predicted hit: (first round where the free calls differ from the gold, first TF-wrong round, reason class)."""
    gold = [tuple(g[:3]) for g in rec['gold']]
    free = {c[0] - 1: (c[1], c[2], c[3]) for c in rec['free']['calls']}
    first_free = next((k for k in range(N_RES) if free.get(k) != (gold[k] if k < len(gold) else None)), None)
    wr = wrong_rounds(rec)
    if not wr:
        return first_free, None, 'other'
    k = wr[0]
    r = rec['tf'][k]
    g = gold[k] if k < len(gold) else None
    if g is None:
        return first_free, k, 'extra call'
    if r['op'] == NOOP:
        return first_free, k, 'missing call/NOOP'
    if r['ei']:
        same_order = r['op'] == g[0] and tuple(JG.num(x) for x in (r['a'], r['b'])) == tuple(JG.num(x) for x in g[1:3])
        return first_free, k, 'normalised-number-only' if same_order else 'either-order-only'
    return first_free, k, 'alternative program' if rec['free']['hit'] and not predicted_hit(rec) else 'other'


def round_identity(rec):
    """The identity round by round, for one item with a TF record: the free calls equal the gold calls (no call at a round >= n) at every round up to
    the first TF-wrong round (all 7 rounds when none is wrong), and the free call at that round equals the TF call, as exact text (no call = NOOP).
    -> (ok, round of the first failure or None, why)."""
    gold = [tuple(g[:3]) for g in rec['gold']]
    free = {c[0] - 1: (c[1], c[2], c[3]) for c in rec['free']['calls']}
    wr = wrong_rounds(rec)
    kw = wr[0] if wr else None
    for k in range(N_RES if kw is None else kw):
        want = gold[k] if k < len(gold) else None
        if free.get(k) != want:
            return False, k, f'free call {free.get(k)} != gold call {want} before the first TF-wrong round'
    if kw is not None:
        r = rec['tf'][kw]
        tfc = None if r['op'] == NOOP else (r['op'], r['a'], r['b'])
        if free.get(kw) != tfc:
            return False, kw, f'free call {free.get(kw)} != TF call {tfc} at the first TF-wrong round'
    return True, None, ''


def identity_check(recs):
    """Predicted free hit (all rounds TF-exact and ans_tf) against the observed free hit, and the round-level identity (round_identity). ->
    dict(table {(pred, obs): n}, n, agree, mismatches [dict(id, version, predicted, observed, first_free_round, first_tf_wrong, reason)],
    round_agree, round_mismatches [dict(id, version, round, why)])."""
    ok = [r for r in recs if r.get('tf')]
    table = Counter((predicted_hit(r), bool(r['free']['hit'])) for r in ok)
    mism, rmism = [], []
    for r in ok:
        p, o = predicted_hit(r), bool(r['free']['hit'])
        if p != o:
            ff, tw, why = mismatch_reason(r)
            mism.append(dict(id=r['id'], version=r['version'], predicted=p, observed=o, first_free_round=ff, first_tf_wrong=tw, reason=why))
        good, k, why = round_identity(r)
        if not good:
            rmism.append(dict(id=r['id'], version=r['version'], round=k, why=why))
    return dict(table=dict(table), n=len(ok), agree=len(ok) - len(mism), mismatches=mism, round_agree=len(ok) - len(rmism), round_mismatches=rmism)


def _forced_hits(m, rows, recs, cand, bs):
    """Free runs of rows[i] for i in cand with the GOLD call forced at every TF-wrong round of recs[i] (no call, past the program)."""
    force = {}
    for j, i in enumerate(cand):
        for k in wrong_rounds(recs[i]):
            force[(j, k)] = tuple(recs[i]['gold'][k][:3]) if k < len(recs[i]['gold']) else (NOOP, '', '')
    return forced_run(m, [rows[i] for i in cand], force, bs)


def gold_tape(rec):
    """[N_RES] the gold tape entry texts of a record (entry(op, a, b, result) per gold step, '' past the program) -- what a free run that makes the gold call
    at every round writes."""
    from custom_io.models.tool import entry
    return [entry(*rec['gold'][k][:4]) if k < len(rec['gold']) else '' for k in range(N_RES)]


def _agreement(recs, cand, res):
    """The prediction after repairing every TF-wrong round of an item is ans_tf (all other rounds are TF-right, the readout is the only thing left);
    compare it with the forced free hit AND require the forced run's tape (forced_run returns it) to equal the gold tape exactly: after forcing the gold
    call at every wrong round the whole tape must be the gold tape, and a hit bit that agrees by luck on another tape is a mismatch. -> dict(n, agree,
    mismatches [dict(id, rounds, predicted, observed) + tape_round (first round whose tape text differs from the gold) when the tape differs])."""
    mism = []
    for i, f in zip(cand, res):
        want, got = gold_tape(recs[i]), list(f.get('tape') or [])
        got += [''] * (N_RES - len(got))
        bad_tape = next((k for k in range(N_RES) if got[k] != want[k]), None)
        if bool(recs[i]['ans_tf']) != bool(f['hit']) or bad_tape is not None:
            x = dict(id=recs[i]['id'], rounds=wrong_rounds(recs[i]), predicted=bool(recs[i]['ans_tf']), observed=bool(f['hit']))
            if bad_tape is not None:
                x['tape_round'] = bad_tape
            mism.append(x)
    return dict(n=len(cand), agree=len(cand) - len(mism), mismatches=mism)


FULL_VALIDATE = ('D', 'D_K', 'D_J')              # strata validated on ALL their single-wrong-round items (the others on a seeded sample)
VALIDATE_SETS = ('r0', 'J_first', 'd', 'r0+J_first')
VALIDATE_FAIL_RATE = 0.05


def validate_all(m, rows, recs, sample=64, bs=64, seed=0, sets=VALIDATE_SETS):
    """The gate on the repair counterfactuals (collect runs it on the 'orig' items; rows and recs index-aligned). (1) per stratum: every item with exactly
    one TF-wrong round in D / D_K / D_J, and a seeded sample (`sample` per stratum, random.Random(f'{seed}:{stratum}'); None = all, 0 = none) of such items
    in every other stratum: the gold call is forced at that round and the free hit must equal ans_tf. (2) per repair set in `sets` (r0, J_first, d, r0+J_first
    -- REPAIR_SETS names): the D items with TF-wrong rounds, all of them carrying a label of the set, get the gold call forced at ALL their wrong rounds.
    Every item is run once. -> dict(sample, seed, strata {name: dict(n, agree, mismatches, rate)}, sets {name: same}); rate = mismatches / n."""
    ok = [i for i, r in enumerate(recs) if r.get('tf') and wrong_rounds(r)]
    single = [i for i in ok if len(wrong_rounds(recs[i])) == 1]
    groups = {}
    for s in sorted({s for i in single for s in recs[i]['strata']}):
        c = [i for i in single if s in recs[i]['strata']]
        if s not in FULL_VALIDATE and sample is not None and len(c) > sample:
            c = sorted(random.Random(f'{seed}:{s}').sample(c, sample))
        groups[('strata', s)] = c
    for name in sets:
        S = set(REPAIR_SETS[name])
        groups[('sets', name)] = [i for i in ok if 'D' in recs[i]['strata'] and all(round_labels(recs[i], k) & S for k in wrong_rounds(recs[i]))]
    cand = sorted({i for c in groups.values() for i in c})
    res = dict(zip(cand, _forced_hits(m, rows, recs, cand, bs))) if cand else {}
    out = dict(sample=sample, seed=seed, strata={}, sets={})
    for (kind, name), c in groups.items():
        a = _agreement(recs, c, [res[i] for i in c])
        a['rate'] = (a['n'] - a['agree']) / a['n'] if a['n'] else 0.0
        out[kind][name] = a
    return out


# ---------- classifiers of a TF-wrong round ----------

def wrong_kind(rec, k):
    """What kind of wrong call round k is (p2_diag.classify's operand taxonomy for one round): extra call, missing call (NOOP), later step done
    first, wrong op, format only (same numbers, other text/order), then for the first wrong operand number: wrong_named_cell / unnamed_cell /
    constant (p2_diag.number_spot), intermediate (an earlier result), other_number."""
    r = rec['tf'][k]
    call = (r['op'], r['a'], r['b'])
    if k >= rec['n']:
        return 'extra call'
    gold = tuple(rec['gold'][k][:3])
    if r['op'] == NOOP:
        return 'missing call (NOOP)'
    if any(JG.same_call(call, tuple(s[:3])) for s in rec['gold'][k + 1:]):
        return 'later step done first'
    if r['op'] != gold[0]:
        return 'wrong op'
    want, got = [str(JG.num(x)) for x in gold[1:3]], [str(JG.num(x)) for x in call[1:3]]
    if gold[0] in SYM:
        left, bad = list(want), []
        for x in got:
            left.remove(x) if x in left else bad.append(x)
    else:
        bad = [x for x, w in zip(got, want) if x != w]
    if not bad:
        return 'format only'
    x = bad[0]
    spot = P2.number_spot(rec['prompt'], x)
    if spot:
        return {'operand: a cell the formula names (the wrong one)': 'wrong_named_cell',
                'operand: a grid cell the formula does not name': 'unnamed_cell', 'operand: a literal of the formula': 'constant'}[spot]
    earlier = {str(JG.num(s[3])) for s in rec['gold'][:k]}
    return 'intermediate' if x in earlier else 'other_number'


def matches_flat(rec, k):
    """The model's call at round k equals the bracket-stripped program's call at round k -- ONLY at the divergence round d (join_gap.same_call:
    numbers, either order for add/mul/min/max, so a non-commutative flat call written with its operands swapped does not match). After d the tape of
    the flat program differs from the gold tape the model sees, so the flat program's later calls are not what a model reading the stripped formula
    would write there: see flat_coincides."""
    r, fl = rec['tf'][k], rec['flat']
    return (bool(rec['paren_sensitive']) and rec.get('d') is not None and k == rec['d'] and k < len(fl) and r['op'] != NOOP
            and JG.same_call((r['op'], r['a'], r['b']), tuple(fl[k][:3])))


def flat_coincides(rec, k):
    """A wrong call AFTER the divergence round equals the flat program's call at that round: coincidental, not evidence (the flat program's tape differs
    there). Counted in the report only to show how large the coincidence rate is."""
    r, fl = rec['tf'][k], rec['flat']
    return (bool(rec['paren_sensitive']) and rec.get('d') is not None and k > rec['d'] and k < len(fl) and r['op'] != NOOP
            and JG.same_call((r['op'], r['a'], r['b']), tuple(fl[k][:3])))


def ca_took_x(rec, k):
    """At the ca_mul round ('mul y 2') the model wrote the value of the piece's first-named cell x instead of y: a mul of x's value and 2."""
    ca = rec.get('ca')
    if not ca or not ca['shape_ok'] or k != ca['start'] or ca['xv'] == ca['yv']:
        return False
    r = rec['tf'][k]
    return r['op'] == 'mul' and sorted(str(JG.num(x)) for x in (r['a'], r['b'])) == sorted([str(ca['xv']), '2'])


def annotate_wrong(rec):
    return [dict(k=k, kind=wrong_kind(rec, k), matches_flat=bool(matches_flat(rec, k)), flat_coincides=bool(flat_coincides(rec, k)),
                 ca_took_x=bool(ca_took_x(rec, k))) for k in wrong_rounds(rec)]


# ---------- collect: one record per item x version ----------

KEEP = ('id', 'base_id', 'version', 'split', 'kind', 'partner', 'layout', 'prompt', 'answer', 'accepted', 'strata', 'n', 'nK', 'nJ', 'ca_pos', 'ca',
        'order_ok', 'paren_sensitive', 'd', 'types')


def make_record(label, p, free, tf):
    rec = {k: p[k] for k in KEEP}
    rec.update(label=label, gold=[list(s) for s in p['steps']], flat=[list(s) for s in p['flat_steps']], free=free,
               dropped=None if tf['made'] else tf['drop'], tf=tf.get('tf', []), ans_tf=tf.get('ans_tf'), ans_text=tf.get('ans_text'),
               lp=tf.get('lp'), lp_flat=tf.get('lp_flat'))
    rec['wrong'] = annotate_wrong(rec) if tf['made'] else []
    return rec


def collect_items(m, preps, label, bs=64, with_margins=True):
    """Free pass and TF pass over the same ordered list in the same chunks (so the two share batch shapes); the premise check rides on the TF pass
    (tf_with_premise: PremiseCheck as the TF pass's observer, one TF run serves both). -> (records, premise dict with the per-cell counts, premise_cells)."""
    free = free_pass(m, preps, bs)
    tf, pc = tf_with_premise(m, preps, bs, margins=with_margins)
    return [make_record(label, p, f, t) for p, f, t in zip(preps, free, tf)], premise_cells(preps, pc)


def ordered_rows(eval_rows, probe_rows=None, probe_cells=('F0-near', 'F4-two')):
    """The row order learn_probe.eval_sets hands the scorer (cells S5, S, HP, HO, HPO from the eval file, then the probe cells; the fit cell, last, is
    not available here), so that free-run chunks of 64 are the scorer's chunks for the eval cells."""
    out = [r for c in LP.L5_CELLS for r in eval_rows if r['split'] == c]
    if probe_rows is not None:
        scored = [r for r in probe_rows if r['kind'] in SP.SCORED]
        out += [dict(r, split=c) for c in probe_cells for r in scored if r['split'] == c]
    return out


def self_check_indices(preps, total=256, seed=0):
    """Indices (sorted) of the rows for the own-calls self-check: EVERY D row (HO, 4 calls, cell-arithmetic piece), plus a sample of the rest of
    total - |D| rows (all of them if fewer), stratified by cell (split): proportional to the cell's size with largest remainders, at least one row per
    cell while the budget allows, drawn with random.Random(seed)."""
    dset = [i for i, p in enumerate(preps) if 'D' in p['strata']]
    rest = defaultdict(list)
    for i, p in enumerate(preps):
        if 'D' not in p['strata']:
            rest[p['split']].append(i)
    budget = max(0, total - len(dset))
    size = sum(len(v) for v in rest.values())
    if budget >= size:
        return sorted(dset + [i for v in rest.values() for i in v])
    cells = sorted(rest, key=str)
    want = {c: budget * len(rest[c]) / size for c in cells}
    floor1 = 1 if budget >= len(cells) else 0
    base = {c: min(len(rest[c]), max(floor1, int(want[c]))) for c in cells}
    while sum(base.values()) > budget:                      # the one-per-cell floor overshot: take back from the cell with the most surplus
        c = max((c for c in cells if base[c] > floor1), key=lambda c: base[c] - want[c])
        base[c] -= 1
    left = budget - sum(base.values())
    for c in sorted(cells, key=lambda c: (-(want[c] - base[c]), str(c))):
        if left <= 0:
            break
        if base[c] < len(rest[c]):
            base[c] += 1
            left -= 1
    rng = random.Random(seed)
    pick = [i for c in cells for i in rng.sample(rest[c], base[c])]
    return sorted(dset + pick)


class PremiseFailed(RuntimeError):
    """collect found a failed premise check, self-check or real-strata check (fatal unless --allow-premise-fail)."""


def diff_bad(x):
    """A logit difference above float noise (None = not compared: not a failure by itself, the report shows the counts)."""
    return x is not None and x > 1e-4


def premise_unchecked(pc):
    """The premise check compared nothing: no row checked (n == 0), or the logits were compared on no chunk (max_diff None / logit_chunks[0] == 0).
    A check that compared nothing is not a pass."""
    chunks = pc.get('logit_chunks')
    return pc['n'] == 0 or pc['max_diff'] is None or (chunks is not None and chunks[0] == 0)


def premise_failed(pc):
    """A premise check that failed or that checked nothing (premise_unchecked): fatal at collect, a gate failure in the report."""
    return premise_unchecked(pc) or pc['n'] != pc['ok'] or diff_bad(pc['max_diff'])


def premise_unchecked_text(version):
    return f'premise unchecked for {version}'


def self_check_failed(sc):
    return bool(sc['bad'] or sc['ans_bad'] or diff_bad(sc['max_diff']))


def premise_cells(items, pc):
    """pc plus pc['cells'] = {cell: dict(ok, n = rows checked, not_checked = make_row-dropped rows)}: a dropped row is never counted as a pass."""
    bad, dropped = set(pc['bad_idx']), set(pc['dropped_idx'])
    cells = defaultdict(lambda: dict(ok=0, n=0, not_checked=0))
    for i, it in enumerate(items):
        c = cells[str(it['split'])]
        if i in dropped:
            c['not_checked'] += 1
        else:
            c['n'] += 1
            c['ok'] += i not in bad
    pc['cells'] = dict(cells)
    return pc


def looks_like_l5(eval_rows):
    """The eval file has the cells of eval-rows-l5.jsonl (S5, S, HP, HO, HPO)."""
    return set(LP.L5_CELLS) <= {r.get('split') for r in eval_rows}


def collect(ckpt, label, eval_rows, probe_rows=None, rewrites=REWRITES, rewrite_strata=('HO',), bs=64, with_margins=True, sha=None, self_check=256,
            limit=None, probe_cells=('F0-near', 'F4-two'), validate_sample=64, allow_premise_fail=False, validate=True):
    """-> (records, meta). See the module docstring. meta['self_check'] holds the own-calls identity result for self_check_indices(preps, self_check)
    (every D row + a cell-stratified sample, per-cell counts in 'cells', 'D' = the D rows), meta['self_check_versions'] the same for each rewrite;
    meta['premise'] the gold-path premise check per version ('orig' = eval + probe rows, then each rewrite): n checked, ok, bad_ids, dropped (not
    checked), per-cell dict(ok, n, not_checked), max_diff, logit_chunks; meta['identity'] the hit-level and round-level identity per version;
    meta['validate'] the validate_all result (validate_sample per non-D stratum; None = validate=False, not run); meta['real_strata_checked'] the real-strata
    counts, or the reason they were not checked. A failed premise / self-check / strata check raises PremiseFailed unless allow_premise_fail, which
    appends it to meta['allowed_failures']. sha None = no checksum asked for: meta['sha_check'] = 'sha unchecked'."""
    from custom_io.models import load_model
    digest = check_sha(ckpt, sha)
    m = load_model(ckpt).eval()
    rows = ordered_rows(eval_rows, probe_rows, probe_cells)
    if limit:
        rows = rows[:limit]
    preps = prepare(rows)
    meta = dict(label=label, ckpt=ckpt, sha256=digest, sha_check='ok' if sha is not None else 'sha unchecked', rows=len(preps), strata=strata_counts(preps),
                bs=bs, rewrites={}, spaced_ok=spaced_ok(), allowed_failures=[])

    def problem(what):
        if not allow_premise_fail:
            raise PremiseFailed(what)
        meta['allowed_failures'].append(what)
        print(f'WARNING (!!!): {what} (allowed by --allow-premise-fail; recorded in the meta)', file=sys.stderr)

    if not looks_like_l5(eval_rows):
        meta['real_strata_checked'] = 'not checked: the eval rows lack the cells of eval-rows-l5 ' + str(LP.L5_CELLS)
    elif limit:
        meta['real_strata_checked'] = 'strata unchecked (limit)'
    else:
        try:
            meta['real_strata_checked'] = check_real_strata(preps)
        except StrataError as e:
            meta['real_strata_checked'] = f'FAILED: {e}'
            problem(f'real strata check failed: {e}')

    def selfcheck(items, version):
        idx = self_check_indices(items, self_check)
        sc = own_call_identity(m, [items[i] for i in idx], bs)
        sc = dict(n=sc['n'], bad=len(sc['bad']), ans_bad=len(sc['ans_bad']), max_diff=sc['max_diff'], max_diff_by=sc.get('max_diff_by'), total=self_check, seed=0,
                  D=sum(1 for i in idx if 'D' in items[i]['strata']), cells=dict(Counter(str(items[i]['split']) for i in idx)),
                  cells_available=dict(Counter(str(p['split']) for p in items)))
        if self_check_failed(sc):
            problem(f'{label}/{version}: the own-calls self-check failed ({sc["bad"]} calls, {sc["ans_bad"]} answers, max logit diff {sc["max_diff"]:.3g}, by kind {sc.get("max_diff_by")}): '
                    'the run() path is not the identity on this checkpoint')
        return sc

    def premise_problem(version, pc):
        if premise_unchecked(pc):
            problem(f'{label}/{version}: {premise_unchecked_text(version)} (n {pc["n"]}, {pc["dropped"]} dropped, logits compared on {pc.get("logit_chunks")}): '
                    'the premise check compared nothing, which is not a pass')
        elif premise_failed(pc):
            problem(f'{label}/{version}: gold-path premise check FAILED for {pc["n"] - pc["ok"]}/{pc["n"]} rows (ids {pc["bad_ids"][:10]}), max logit diff '
                    f'{pc["max_diff"]} (by kind {pc.get("max_diff_by")}): forced gold calls do not reproduce the gold tape / the TF run')
        if pc['dropped']:
            print(f'NOTE: {label}/{version}: {pc["dropped"]} row(s) dropped by make_row are NOT checked by the premise check', file=sys.stderr)

    if self_check:
        meta['self_check'] = selfcheck(preps, 'orig')
    meta['premise'], meta['identity'], meta['self_check_versions'] = {}, {}, {}
    recs, pc = collect_items(m, preps, label, bs, with_margins)
    meta['premise']['orig'] = pc
    premise_problem('orig', pc)
    meta['drops'] = {s: dict(Counter(r['dropped'] for r in recs if r['version'] == 'orig' and r['dropped'] and s in r['strata']))
                     for s in sorted({s for r in recs if r['dropped'] for s in r['strata']})}
    orig_n = len(recs)
    for name in rewrites:
        vs, skipped = make_versions(preps, name, rewrite_strata)
        meta['rewrites'][name] = dict(made=len(vs), skipped=skipped)
        if vs:
            if self_check:
                meta['self_check_versions'][name] = selfcheck(vs, name)
            vrecs, pc = collect_items(m, vs, label, bs, with_margins)
            meta['premise'][name] = pc
            premise_problem(name, pc)
            recs += vrecs
    for v in sorted({r['version'] for r in recs}):
        idc = identity_check([r for r in recs if r['version'] == v])
        meta['identity'][v] = dict(n=idc['n'], agree=idc['agree'], round_agree=idc['round_agree'], round_mismatches=idc['round_mismatches'][:20])
    if not validate:
        meta['validate'] = None
        print('WARNING (!!!): validate_repair was NOT run (--no-validate): the repair counterfactuals are unchecked', file=sys.stderr)
    else:
        meta['validate'] = validate_all(m, preps, recs[:orig_n], validate_sample, bs)
    return recs, meta


# ---------- report ----------

def load_records(paths):
    """Directories (bracket-*.jsonl inside) or files -> {label: [records]}, {label: meta}. The label is the one INSIDE the records (the file name is
    not trusted): a file holds exactly one label, a label may come from one file only (ValueError on a second file, a mixed file or a meta file whose
    label differs), and meta is keyed by that label."""
    recs, meta, src = {}, {}, {}
    for p in paths:
        files = [os.path.join(p, f) for f in sorted(os.listdir(p)) if f.startswith('bracket-') and f.endswith('.jsonl')] if os.path.isdir(p) else [p]
        for f in files:
            rs = LP.load_jsonl(f)
            labels = sorted({r['label'] for r in rs})
            if len(labels) != 1:
                raise ValueError(f'{f}: expected records of exactly one label, found {labels}')
            lab = labels[0]
            if lab in recs:
                raise ValueError(f'duplicate label {lab!r}: records in both {src[lab]} and {f} (a run is reported once; rename or drop one)')
            recs[lab], src[lab] = rs, f
            mp = f[:-len('.jsonl')] + '.meta.json'
            if os.path.exists(mp):
                with open(mp) as fh:
                    mt = json.load(fh)
                if mt.get('label', lab) != lab:
                    raise ValueError(f'{mp}: meta label {mt.get("label")!r} differs from the records\' label {lab!r}')
                meta[lab] = mt
    return recs, meta


def of(recs, stratum=None, version='orig', tf=True):
    return [r for r in recs if r['version'] == version and (stratum is None or stratum in r['strata']) and (r['tf'] or not tf)]


def role_ks(rec, role, kind):
    """The rounds of the item that carry `role` (kind 'pos' / 'type')."""
    if kind == 'pos':
        return [k for k in range(N_RES) if position_role(rec, k) == role]
    return [k for k in range(N_RES) if (rec['types'][k] if k < rec['n'] else 'post') == role]


def role_acc(recs, role, kind, flag='ex'):
    """(items with every round of the role right, items having the role); answer role: ans_tf. INCLUSION: kind 'pos' (position roles) counts only
    order_ok items (nK is a boundary only there); kind 'type' (call types) counts every item with a round of that type, order_ok or not (call types
    are defined for all items); the answer role counts every item."""
    if role == 'answer':
        return sum(1 for r in recs if r['ans_tf']), len(recs)
    have = [(r, role_ks(r, role, kind)) for r in recs if kind != 'pos' or r['order_ok']]
    have = [(r, ks) for r, ks in have if ks]
    return sum(1 for r, ks in have if all(r['tf'][k][flag] for k in ks)), len(have)


def parse_expect(items):
    """['HO=59', 'L14:D=0', 'HO=59/420'] -> {label or None: {key: (hits, n or None)}}; a key without a label applies to every run. ValueError on a
    malformed item or a key given twice for one label."""
    out = defaultdict(dict)
    for it in items or []:
        lab, _, rest = it.rpartition(':')
        key, eq, val = rest.partition('=')
        hits, _, n = val.partition('/')
        if not (key and eq and hits.isdigit() and (n == '' or n.isdigit()) and ('/' not in val or n)):
            raise ValueError(f'bad --expect {it!r}: want KEY=HITS, KEY=HITS/N, LABEL:KEY=HITS or LABEL:KEY=HITS/N')
        if key in out[lab or None]:
            raise ValueError(f'--expect {it!r}: {key} given twice')
        out[lab or None][key] = (int(hits), int(n) if n else None)
    return out


ID_STRICT = ('D', 'D_K', 'D_J')      # strata in which ANY round-level identity mismatch of the orig version fails the gate
ID_FAIL_RATE = 0.005                 # elsewhere a mismatch rate above this fails it


def identity_gate(by_label, no_gate, fails):
    """The round-level identity as a gate (orig version): any mismatch in D, D_K, D_J fails; in any other stratum (and over all orig items) a mismatch rate
    above 0.5% does. -> the report lines; appends to `fails` (unless no_gate)."""
    L = ['\n### Round-level identity (orig version): a gate\n',
         'Round-level mismatch = the free calls differ from the gold calls before the first TF-wrong round, or the free call there differs from the TF call. '
         f'Any mismatch in {", ".join(ID_STRICT)} is a FAIL; in every other stratum (and over all orig items) a rate above {100 * ID_FAIL_RATE:.1f}% is.\n']
    rows = []
    for lab, recs in by_label.items():
        o = of(recs)
        names = ['all'] + [s for s in ID_STRICT if any(s in r['strata'] for r in o)] + sorted({s for r in o for s in r['strata']} - set(ID_STRICT))
        for s in names:
            sub = o if s == 'all' else of(recs, s)
            idc = identity_check(sub)
            n, k = idc['n'], idc['n'] - idc['round_agree']
            strict = s in ID_STRICT
            bad = k > 0 if strict else bool(n) and k / n > ID_FAIL_RATE
            if bad and not no_gate:
                fails.append(f'{lab}: round-level identity broken in {k}/{n} orig items of {s} '
                             f'({"any mismatch fails" if strict else f"rate {100 * k / n:.1f}% > {100 * ID_FAIL_RATE:.1f}%"})')
            rows.append([lab, s, n, k, f'{100 * k / n:.2f}%' if n else '', 'any' if strict else f'> {100 * ID_FAIL_RATE:.1f}%', 'FAIL' if bad else 'ok'])
    L.append(P2.md_table(['run', 'stratum', 'items', 'round-level mismatches', 'rate', 'fails when', 'gate'], rows))
    for r in rows:
        if r[-1] == 'FAIL':
            L.append(f'\n**FAIL: {r[0]} {r[1]}: the round-level identity breaks in {r[3]} of {r[2]} items.**')
    return L


def sec_repro(by_label, meta, expect, no_gate, fails, accept_allowed=False):
    """Section 0, the gate: expectations (hits, and n when given), the round-level identity, validate_repair's agreement (an empty D group fails), failures
    recorded at collect (fail unless accept_allowed = --accept-allowed-failures, which prints ACCEPTED ALLOWED FAILURES). Appends one line to `fails` per
    gate failure; a --expect label or key that matches nothing is a failure, not a dropped row."""
    L = ['## 0. Reproduction gate\n']
    ex = parse_expect(expect)
    n0 = len(fails)
    if no_gate:
        L.append('**GATE NOT RUN** (--no-gate): no expectation was checked and nothing below changes the exit status.\n')
    elif not ex:
        fails.append('no --expect given (pass --expect, or --no-gate to run without the gate)')
        L.append('**FAIL: no --expect given**; the free-run counts were not compared with anything (pass --expect KEY=HITS[/N], or --no-gate).\n')
    rows = []
    if ex and not no_gate:
        for lab in ex:
            if lab is not None and lab not in by_label:
                fails.append(f'--expect label {lab!r} matches no run (runs: {sorted(by_label)})')
                rows.append([lab, '', '', '', f'FAIL: no such run (runs: {sorted(by_label)})'])
    for lab, recs in by_label.items():
        o = [r for r in recs if r['version'] == 'orig']
        want = {**ex.get(None, {}), **ex.get(lab, {})} if not no_gate else {}
        for key, (wh, wn) in want.items():
            sel = [r for r in o if key in r['strata'] or r['split'] == key]
            got, n = sum(r['free']['hit'] for r in sel), len(sel)
            if not sel:
                fails.append(f'{lab}: --expect key {key!r} matches no cell or stratum')
                rows.append([lab, key, '0/0', wh if wn is None else f'{wh}/{wn}', 'FAIL: no such cell / stratum'])
                continue
            ok = got == wh and (wn is None or n == wn)
            if not ok:
                fails.append(f'{lab}: {key}: got {got}/{n}, expected {wh}' + ('' if wn is None else f'/{wn}'))
            rows.append([lab, key, f'{got}/{n}', wh if wn is None else f'{wh}/{wn}', 'PASS' if ok else 'FAIL'])
        for c in sorted({r['split'] for r in o}):
            sub = [r for r in o if r['split'] == c]
            rows.append([lab, f'{c} (observed)', frac(sum(r['free']['hit'] for r in sub), len(sub)), '', ''])
    L.append(P2.md_table(['run', 'cell / stratum', 'free hits', 'expected (hits or hits/n)', 'gate'], rows))
    if not no_gate and ex and len(fails) == n0:
        L.append('\nGate: all given expectations met.\n')
    elif not no_gate and ex:
        L.append('\nGate: FAILED, STOP: the rows or the record are wrong (or an --expect names nothing).\n')
    L += identity_gate(by_label, no_gate, fails)
    L.append('\n### validate_repair: the repair counterfactuals against real forced free runs\n')
    L.append('Forcing the gold call at every TF-wrong round of an item must give a free hit equal to ans_tf and the forced tape the gold tape (the identity). '
             f'Mismatch rate > {100 * VALIDATE_FAIL_RATE:.0f}% in any stratum or set is a FAIL; D items with a TF-wrong round, none of them forced '
             '(no single-wrong-round group, no repair set), is a FAIL too (D is unvalidated); a D with no TF-wrong round is a note; other empty groups are notes.\n')
    vrows = []
    for lab in by_label:
        mt = (meta or {}).get(lab)
        if meta is None:
            continue
        v = (mt or {}).get('validate')
        if v is None:
            msg = f'{lab}: validate_repair was NOT run' if mt else f'{lab}: no meta file next to the records (validate_repair result unknown)'
            L.append(f'**FAIL: {msg}.**\n')
            if not no_gate:
                fails.append(msg)
            continue
        d_wrong = sum(1 for r in by_label[lab] if r['version'] == 'orig' and 'D' in r['strata'] and r.get('tf') and wrong_rounds(r))
        d_forced = (v['strata'].get('D', {}).get('n') or 0) + sum(a.get('n') or 0 for a in v['sets'].values())   # repair-set groups hold D items only
        if not d_wrong:
            L.append(f'Note: {lab}: D has no TF-wrong rounds: nothing to validate.\n')
        elif not d_forced:
            msg = (f'{lab}: the D validation group (D items with exactly one TF-wrong round) and every repair set are empty (n == 0) although {d_wrong} D item(s) '
                   'have a TF-wrong round: none was validated by a forced run, so the repair counterfactuals for D are unvalidated (nothing in D was forced; empty is not passed)')
            L.append(f'**FAIL: {msg}.**\n')
            if not no_gate:
                fails.append(msg)
        empty = [('set ' if kind == 'sets' else 'stratum ') + name for kind in ('strata', 'sets') for name, a in v[kind].items()
                 if not a['n'] and not (kind == 'strata' and name == 'D')]
        if empty:
            L.append(f'Note: {lab}: validation groups with no item (not forced, not passed): {", ".join(empty)}.\n')
        for kind in ('strata', 'sets'):
            for name, a in v[kind].items():
                bad = a['n'] and a['rate'] > VALIDATE_FAIL_RATE
                if bad and not no_gate:
                    fails.append(f'{lab}: validate_repair mismatch rate {100 * a["rate"]:.1f}% ({a["n"] - a["agree"]}/{a["n"]}) in {kind[:-1] if kind == "sets" else "stratum"} {name}')
                vrows.append([lab, ('set ' if kind == 'sets' else 'stratum ') + name, a['n'], a['agree'], len(a['mismatches']), f'{100 * a["rate"]:.1f}%',
                              'FAIL' if bad else 'ok'])
        for kind in ('strata', 'sets'):
            for name, a in v[kind].items():
                if a['mismatches']:
                    L.append(f'{lab} {kind[:-1]} {name} mismatches (id, forced rounds, predicted = ans_tf, observed forced hit, first round whose forced tape '
                             'text differs from the gold tape): ' + '; '.join(f'{x["id"]} {x["rounds"]} {x["predicted"]} {x["observed"]}'
                                                                              + (f' tape@{x["tape_round"]}' if 'tape_round' in x else '') for x in a['mismatches'][:20]) + '\n')
    if vrows:
        L.append(P2.md_table(['run', 'group', 'items forced', 'agree', 'mismatches', 'rate', 'gate'], vrows))
        for r in vrows:
            if r[-1] == 'FAIL':
                L.append(f'\n**FAIL: {r[0]} {r[1]}: validate_repair disagrees with its prediction in {r[5]} of {r[2]} items.**')
    accepted = []
    for lab in by_label:
        mt = (meta or {}).get(lab) or {}
        allowed = mt.get('allowed_failures') or []

        def failure(what, recorded):
            """A failure that collect let through (--allow-premise-fail): a gate failure unless --accept-allowed-failures AND collect recorded it."""
            if accept_allowed and recorded:
                accepted.append(f'{lab}: {what}')
                L.append(f'\n**ACCEPTED ALLOWED FAILURES: {lab}: {what}**')
            else:
                if not no_gate:
                    fails.append(f'{lab}: {what}' + ('' if recorded else ' (NOT recorded in meta allowed_failures: the meta is inconsistent)')
                                 + ('' if accept_allowed or not recorded else ' (pass --accept-allowed-failures to accept failures allowed at collect)'))
                L.append(f'\n**FAIL: {lab}: {what}**')
        for what in allowed:
            failure(f'failure ALLOWED at collect (--allow-premise-fail): {what}', True)
        def recorded(marker, version=None):
            """Did collect record THIS kind of failure (marker in an allowed_failures entry; for a per-version failure, an entry for that version)?"""
            return any(marker in e and (version is None or f'/{version}:' in e) for e in allowed if isinstance(e, str))
        if mt:
            checks = [('orig', mt.get('self_check'))] + [(v_, sc_) for v_, sc_ in (mt.get('self_check_versions') or {}).items()]
            for v_, sc_ in checks:
                if sc_ and self_check_failed(sc_):
                    failure(f'the own-calls self-check FAILED{"" if v_ == "orig" else " for " + v_} (bad {sc_["bad"]}, ans_bad {sc_["ans_bad"]}, '
                            f'max logit diff {sc_["max_diff"]})', recorded('own-calls self-check failed', v_))
            for v_, pc_ in (mt.get('premise') or {}).items():
                if premise_unchecked(pc_):
                    failure(premise_unchecked_text(v_), recorded(premise_unchecked_text(v_), v_))
                elif premise_failed(pc_):
                    failure(f'gold-path premise check FAILED for version {v_} ({pc_["ok"]}/{pc_["n"]} rows, max logit diff {pc_["max_diff"]})',
                            recorded('gold-path premise check FAILED', v_))
            if str(mt.get('real_strata_checked') or '').startswith('FAILED'):
                failure(f'real strata check FAILED ({mt["real_strata_checked"]})', recorded('real strata check failed'))
        if mt.get('sha_check') == 'sha unchecked':
            L.append(f'\n**{lab}: sha unchecked** (collect ran with --no-sha: the checkpoint is not verified).')
    if accept_allowed:
        if accepted:
            L.insert(1, '\n**!!! ACCEPTED ALLOWED FAILURES (--accept-allowed-failures): this run has failures that collect let through with '
                        '--allow-premise-fail and they are NOT gate failures here; read each one below before trusting any number !!!**\n')
        else:
            L.append('\n--accept-allowed-failures was given, but no failure was allowed at collect: nothing was accepted.')
    return '\n'.join(L)


def sec_identity(by_label, strata=('HO', 'D', 'HPO', 'S5')):
    L = ['## 1. The identity: predicted free hit (every round TF-exact and the answer right under the full gold tape) against the observed free hit\n',
         'Denominator: items with a TF record (make_row kept them). 2x2 cell = (predicted, observed). Round-level identity: the free calls equal the gold '
         'calls up to the first TF-wrong round and the free call at that round equals the TF call (exact text); the hit bit alone can agree by luck.\n']
    for lab, recs in by_label.items():
        rows = []
        for s in (None,) + tuple(strata):
            sub = of(recs, s)
            idc = identity_check(sub)
            t = idc['table']
            rows.append([s or 'all'] + [t.get(k, 0) for k in ((True, True), (True, False), (False, True), (False, False))] +
                        [frac(idc['agree'], idc['n']), frac(idc['round_agree'], idc['n'])])
        L.append(f'### {lab}\n')
        L.append(P2.md_table(['stratum', 'pred hit, obs hit', 'pred hit, obs miss', 'pred miss, obs hit', 'pred miss, obs miss', 'hit agreement',
                              'round-level agreement'], rows))
        vrows = []
        for v in [v for v in ('orig',) + REWRITES if any(r['version'] == v for r in recs)]:
            idc = identity_check(of(recs, None, v))
            vrows.append([v, frac(idc['agree'], idc['n']), frac(idc['round_agree'], idc['n'])])
        L.append('\nPer version (all strata):\n')
        L.append(P2.md_table(['version', 'hit agreement', 'round-level agreement'], vrows))
        idc = identity_check(of(recs))
        cls = Counter(x['reason'] for x in idc['mismatches'])
        L.append(f'\nMismatches over all orig items: {len(idc["mismatches"])} of {idc["n"]}; agreement {frac(idc["agree"], idc["n"])} '
                 f'(target >= 98%: {"met" if idc["n"] and idc["agree"] >= 0.98 * idc["n"] else "NOT met, the identity is in doubt for this run"}); '
                 f'reason classes {dict(cls)}. Round-level: {len(idc["round_mismatches"])} of {idc["n"]} items break it '
                 f'({"none" if not idc["round_mismatches"] else "the identity is in doubt for this run"}).\n')
        if idc['mismatches']:
            L.append(P2.md_table(['id', 'predicted', 'observed', 'first round free != gold', 'first TF-wrong round', 'reason'],
                                 [[x['id'], x['predicted'], x['observed'], x['first_free_round'], x['first_tf_wrong'], x['reason']] for x in idc['mismatches'][:40]]))
            L.append('')
        if idc['round_mismatches']:
            L.append(P2.md_table(['id', 'round', 'what differs'], [[x['id'], x['round'], x['why']] for x in idc['round_mismatches'][:40]]))
            L.append('')
        drops = Counter((s, r['dropped']) for r in recs if r['version'] == 'orig' and r['dropped'] for s in r['strata'])
        L.append(f'make_row drops (stratum, reason): {dict(drops) if drops else "none"}\n')
    return '\n'.join(L)


def sec_roles(by_label, strata=STRATA_ORDER):
    L = ['## 2. Teacher-forced accuracy by round role and by call type, per stratum\n',
         'Item level: an item is right on a role when EVERY round of that role is right; denominator = items that have the role. Position tables use only '
         'items whose program is K steps, J steps, join in order (order_ok); call-type tables use every item with a TF record that has a round of the '
         'type, order_ok or not; the answer column is ans_tf over all items of the stratum. For an order_ok item with no K steps (nK = 0) round 0 is '
         'J_first, not r0 (the two coincide there: the r0 column leaves those items out, the repair set r0 includes them). exact = same op and operand '
         'text; either = same call as numbers, either order for add/mul/min/max.\n']
    for lab, by in by_label.items():
        for flag, nm in (('ex', 'exact'), ('ei', 'either order')):
            L.append(f'### {lab}: by position, {nm}\n')
            L.append('Inclusion: order_ok items only (the order_ok count is in each row label).\n')
            rows = []
            for s in strata:
                sub = of(by, s)
                rows.append([f'{s} (n={len(sub)}, order_ok {sum(1 for r in sub if r["order_ok"])})'] +
                            [frac(*role_acc(sub, ro, 'pos', flag)) for ro in ROLES] + [frac(*role_acc(sub, 'answer', 'pos'))])
            L.append(P2.md_table(['stratum'] + list(ROLES) + ['answer'], rows))
            L.append(f'\n### {lab}: by call type, {nm}\n')
            L.append('Inclusion: all items with a TF record, order_ok or not (denominator = items having a round of the type).\n')
            rows = []
            for s in strata:
                sub = of(by, s)
                rows.append([s] + [frac(*role_acc(sub, ty, 'type', flag)) for ty in TYPES])
            L.append(P2.md_table(['stratum'] + list(TYPES), rows))
            L.append('')
    return '\n'.join(L)


def sec_2x2(by_label):
    L = ['## 3. Inside D: call type (ca_mul vs lookup) x position (r0 vs J_first), TF exact\n',
         'D_K: the cell-arithmetic piece is K, so r0 is its ca_mul and J_first (round nK) a lookup. D_J: r0 is a lookup and J_first (round nK = 1) the ca_mul. '
         'Cells pool the round of each item (one round per item per cell). Inclusion: D items (all of them are order_ok).\n']
    for lab, recs in by_label.items():
        d = of(recs, 'D')

        def cell(items, ty, pos):
            sel = [(r, k) for r in items for k in range(r['n']) if r['types'][k] == ty and position_role(r, k) == pos]
            return frac(sum(1 for r, k in sel if r['tf'][k]['ex']), len(sel))
        rows = [['ca_mul', cell(d, 'ca_mul', 'r0'), cell(d, 'ca_mul', 'J_first')], ['lookup', cell(d, 'lookup', 'r0'), cell(d, 'lookup', 'J_first')]]
        L.append(f'### {lab}\n')
        L.append(P2.md_table(['type \\ position', 'r0', 'J_first'], rows))
        L.append('')
    return '\n'.join(L)


def sec_first_wrong(by_label, strata=STRATA_ORDER + ('HO',)):
    L = ['## 4. First TF-wrong round (exact), % of the stratum\n',
         '"none, answer wrong": every call right, the readout under the full gold tape wrong; "none, hit": predicted free hit.\n']
    cols = [str(k) for k in range(N_RES)] + ['none, answer wrong', 'none, hit']
    for lab, recs in by_label.items():
        rows = []
        for s in strata:
            sub = of(recs, s)
            c = Counter()
            for r in sub:
                w = wrong_rounds(r)
                c[str(w[0]) if w else ('none, hit' if r['ans_tf'] else 'none, answer wrong')] += 1
            rows.append([f'{s} (n={len(sub)})'] + [frac(c[x], len(sub)) for x in cols])
        L.append(f'### {lab}\n')
        L.append(P2.md_table(['stratum'] + cols, rows))
        L.append('')
    return '\n'.join(L)


def sec_repair(by_label, strata=STRATA_ORDER + ('HO',)):
    L = ['## 5. Repair counterfactuals C_S: share of items that would hit if an oracle repaired the rounds in S\n',
         'C_S counts items whose TF-wrong rounds ALL carry a label in S and whose answer readout is right (or whose S contains answer). none = no repair '
         '(= the predicted free hit). W_free = the observed free hit. By the identity this is exact for the repaired run except through alternative '
         'programs; validate_repair checks samples with real forced free runs. d = the paren divergence round (items without a divergence: no d round).\n']
    for lab, recs in by_label.items():
        rows = []
        for s in strata:
            sub = of(recs, s)
            t = repair_table(sub)
            rows.append([f'{s}', len(sub), frac(sum(r['free']['hit'] for r in sub), len(sub))] + [frac(*t[name]) for name in REPAIR_SETS])
        L.append(f'### {lab}\n')
        L.append(P2.md_table(['stratum', 'n', 'W_free'] + list(REPAIR_SETS), rows))
        L.append('')
    return '\n'.join(L)


KIND_STRATA = (('D_K', 'D_K (the CA piece is K)'), ('D_J', 'D_J (the CA piece is J)'), ('D', 'D pooled (mixes call types)'), ('HO_nonCA', 'HO_nonCA'))


def sec_classifiers(by_label, strata=('D', 'D_K', 'D_J', 'HO4_nonD', 'HO_CA_all', 'HO_nonCA', 'HO')):
    L = ['## 6. What the wrong calls are\n']
    for lab, recs in by_label.items():
        L.append(f'### {lab}: matches_flat (at the divergence round d the wrong call equals the bracket-stripped program\'s call)\n')
        L.append('Only round d is evidence: there the gold tape and the flat program\'s tape agree. After d the flat program\'s calls are of a different '
                 'tape; a wrong call that equals the flat call there is counted in the last column as COINCIDENTAL, NOT EVIDENCE.\n')
        rows = []
        for s in strata:
            sub = [r for r in of(recs, s) if r['paren_sensitive']]
            at_d = [(r, w) for r in sub for w in r['wrong'] if w['k'] == r['d']]
            after = [w for r in sub for w in r['wrong'] if r['d'] is not None and w['k'] > r['d']]
            rows.append([s, len(sub), frac(len(at_d), len(sub)), frac(sum(1 for _, w in at_d if w['matches_flat']), len(at_d)),
                         frac(sum(1 for w in after if w.get('flat_coincides')), len(after))])
        L.append(P2.md_table(['stratum (paren-sensitive items)', 'items', 'wrong at round d', 'of those: call == flat call at d',
                              'wrong rounds after d: call == flat call there (coincidental, not evidence)'], rows))
        L.append(f'\n### {lab}: ca_took_x (at the ca_mul round the model wrote mul x 2 instead of mul y 2)\n')
        rows = []
        for s in strata:
            sel = [(r, k) for r in of(recs, s) if r['ca'] and r['ca']['shape_ok'] for k in [r['ca']['start']]]
            wrong = [(r, k) for r, k in sel if not r['tf'][k]['ex']]
            rows.append([s, frac(len(wrong), len(sel)), frac(sum(1 for r, k in wrong if ca_took_x(r, k)), len(wrong)),
                         frac(sum(1 for r, k in sel if ca_took_x(r, k)), len(sel))])
        L.append(P2.md_table(['stratum', 'ca_mul round wrong', 'of wrong: took x', 'of all ca_mul rounds: took x'], rows))
        L.append(f'\n### {lab}: kind of every wrong round, by position (count; % of that stratum\'s wrong rounds)\n')
        for s, title in KIND_STRATA:
            sub = of(recs, s)
            kinds = sorted({w['kind'] for r in sub for w in r['wrong']})
            tot = sum(len(r['wrong']) for r in sub)
            rows = []
            for ro in ROLES:
                c = Counter(w['kind'] for r in sub for w in r['wrong'] if position_role(r, w['k']) == ro)
                rows.append([ro, sum(c.values())] + [c.get(kd, 0) for kd in kinds])
            unord = sum(1 for r in sub for w in r['wrong'] if position_role(r, w['k']) == 'unordered')
            L.append(f'{title}: {tot} wrong rounds (inclusion: every item of the stratum; {unord} wrong round(s) of items that are not order_ok have no position '
                     'role and are in no row)\n')
            L.append(P2.md_table(['role', 'wrong rounds'] + kinds, rows))
            L.append('')
    return '\n'.join(L)


def sec_b1b2(by_label, strata=('D', 'D_K', 'D_J', 'HO4_nonD', 'HO_CA_all', 'HO_nonCA', 'HO', 'S5')):
    L = ['## 7. B2 and B1 recomputed from the TF pass\n',
         'B2 = share of items whose rounds 0..n-2 are ALL TF-exact (the prefix before the join call). B1 = TF join-call accuracy given that prefix '
         '(denominator = the B2 count). Inclusion: items with a TF record that have a layout AND are order_ok (program = K steps, J steps, join: only there '
         'is round n-1 the join call); the excluded counts are shown per stratum.\n']
    for lab, recs in by_label.items():
        rows = []
        for s in strata:
            allr = of(recs, s)
            sub = [r for r in allr if r['layout'] and r['order_ok']]
            nolay, unord = sum(1 for r in allr if not r['layout']), sum(1 for r in allr if r['layout'] and not r['order_ok'])
            pre = [r for r in sub if all(r['tf'][k]['ex'] for k in range(r['n'] - 1))]
            rows.append([s, len(sub), f'{len(allr) - len(sub)} ({nolay} no layout, {unord} layout but not order_ok)', frac(len(pre), len(sub)),
                         frac(sum(1 for r in pre if r['tf'][r['n'] - 1]['ex']), len(pre)),
                         frac(sum(1 for r in sub if r['tf'][r['n'] - 1]['ex']), len(sub))])
        L.append(f'### {lab}\n')
        L.append(P2.md_table(['stratum', 'items used', 'items excluded', 'B2: prefix all right', 'B1: join right given prefix', 'join right, unconditional'], rows))
        L.append('')
    return '\n'.join(L)


def sec_rewrites(by_label, strata=('D', 'D_K', 'D_J', 'HO')):
    L = ['## 8. Rewrites of the (K)*(J) items: version against the original, same base items\n',
         'Per round: TF exact accuracy over items that have that round (n shown) in each version; Delta = version - original. The "all rounds" and '
         '"free hit" rows count items. plus / minus change only the join call; swap moves the ca call between round 0 and the boundary; strip is the '
         'flat program; spaced is the same program with spaces around the *.\n']
    for lab, recs in by_label.items():
        vers = [v for v in REWRITES if any(r['version'] == v for r in recs)]
        orig = {r['id']: r for r in of(recs)}
        for s in strata:
            for v in vers:
                pairs = [(orig[r['base_id']], r) for r in of(recs, s, v) if r['base_id'] in orig and s in orig[r['base_id']]['strata']]
                if not pairs:
                    continue
                rows = []
                for k in range(N_RES):
                    a = [o for o, _ in pairs if k < o['n']]
                    b = [x for _, x in pairs if k < x['n']]
                    pa, pb = sum(1 for o in a if o['tf'][k]['ex']), sum(1 for x in b if x['tf'][k]['ex'])
                    if a or b:
                        dl = f'{100 * pb / len(b) - 100 * pa / len(a):+.1f}' if a and b else ''
                        rows.append([k, frac(pa, len(a)), frac(pb, len(b)), dl])
                for nm, fn in (('all rounds + answer (predicted hit)', predicted_hit), ('free hit', lambda r: r['free']['hit'])):
                    pa, pb = sum(1 for o, _ in pairs if fn(o)), sum(1 for _, x in pairs if fn(x))
                    rows.append([nm, frac(pa, len(pairs)), frac(pb, len(pairs)), f'{100 * (pb - pa) / len(pairs):+.1f}'])
                L.append(f'### {lab}: {s}, {v} (paired items {len(pairs)})\n')
                L.append(P2.md_table(['round', 'original', v, 'Delta (pts)'], rows))
                trows = []
                for ty in TYPES:
                    a = [(o, role_ks(o, ty, 'type')) for o, _ in pairs]
                    b = [(x, role_ks(x, ty, 'type')) for _, x in pairs]
                    a, b = [(r, ks) for r, ks in a if ks], [(r, ks) for r, ks in b if ks]          # call types: every paired item, order_ok or not
                    pa, pb = sum(1 for r, ks in a if all(r['tf'][k]['ex'] for k in ks)), sum(1 for r, ks in b if all(r['tf'][k]['ex'] for k in ks))
                    trows.append([ty, frac(pa, len(a)), frac(pb, len(b))])
                L.append('\nBy call type (inclusion: every paired item with a round of the type, order_ok or not):\n')
                L.append(P2.md_table(['call type', 'original', v], trows))
                L.append('')
    return '\n'.join(L)


def sec_margins(by_label, strata=('D', 'D_K', 'D_J', 'HO_nonCA')):
    L = ['## 9. Log-prob margin PROXY (not correctness)\n',
         'Mean proxy log-prob of the gold call by position role (item mean over the rounds of the role), and at the divergence round d the mean of '
         '(gold - flat) with the share of items where the flat call scores higher. Inclusion: order_ok items with a TF record and margins.\n']
    for lab, recs in by_label.items():
        rows = []
        for s in strata:
            sub = [r for r in of(recs, s) if r['lp'] is not None and r['order_ok']]
            cells = []
            for ro in ROLES[:5]:
                v = [sum(r['lp'][k] for k in ks) / len(ks) for r in sub for ks in [role_ks(r, ro, 'pos')] if ks]
                cells.append(f'{sum(v) / len(v):.2f} (n={len(v)})' if v else '')
            dd = [(r['lp'][r['d']] - r['lp_flat']) for r in sub if r['d'] is not None and r['lp_flat'] is not None]
            cells.append(f'{sum(dd) / len(dd):.2f}, flat higher {frac(sum(1 for x in dd if x < 0), len(dd))}' if dd else '')
            rows.append([s] + cells)
        L.append(f'### {lab}\n')
        L.append(P2.md_table(['stratum'] + list(ROLES[:5]) + ['at d: gold - flat'], rows))
        L.append('')
    return '\n'.join(L)


def make_report(by_label, meta=None, expect=None, no_gate=False, accept_allowed=False):
    """-> (text, fails): the report and the list of gate failures (the CLI exits 1 when it is not empty). meta: {label: meta dict} as load_records
    returns it (None = no meta at all: the checks that need it are skipped, for pure analysis calls); expect: the --expect items; accept_allowed: do
    not fail on failures that collect recorded in meta['allowed_failures'] (--allow-premise-fail), but print ACCEPTED ALLOWED FAILURES."""
    fails = []
    head = ['# Bracket probe report\n',
            'Zero-training probe: teacher-forced (TF) correctness of every round against the free run (module docstring of domain/far/bracket_probe.py). '
            'Every proportion is k/n with its denominator and a Wilson 95% interval. One run per checkpoint: intervals are over items, not seeds.\n']
    for lab, mt in (meta or {}).items():
        sc = mt.get('self_check')
        if sc and self_check_failed(sc):
            head.append(f'- **{lab}: the own-calls self-check FAILED ({sc}); the identity does not hold numerically on this checkpoint.**')
        for v, sc in (mt.get('self_check_versions') or {}).items():
            if self_check_failed(sc):
                head.append(f'- **{lab}/{v}: the own-calls self-check FAILED ({sc}).**')
        for v, pc in (mt.get('premise') or {}).items():
            if premise_unchecked(pc):
                head.append(f'- **{lab}/{v}: {premise_unchecked_text(v)} (n {pc["n"]}, logits compared on {pc.get("logit_chunks")}).**')
            elif premise_failed(pc):
                head.append(f'- **{lab}/{v}: the gold-path premise check FAILED ({pc["ok"]}/{pc["n"]} rows, max logit diff {pc["max_diff"]}).**')
        head.append(f'- {lab}: premise check (gold calls forced into a free run reproduce the gold tape; make_row-dropped rows are NOT checked) ok/n per version '
                    '(not checked in brackets), and the chunks whose logits were compared: '
                    + str({v: f'{pc["ok"]}/{pc["n"]}' + (f' ({pc["dropped"]} not checked)' if pc.get('dropped') else '') + ', logits on '
                           + ('? chunks' if 'logit_chunks' not in pc else f'{pc["logit_chunks"][0]} of {pc["logit_chunks"][1]} chunks')
                           for v, pc in (mt.get('premise') or {}).items()}))
        head.append(f'- {lab}: max logit difference between the runs, by kind (op / cells / gate / pointer; None = not compared): premise '
                    + str({v: pc.get('max_diff_by') for v, pc in (mt.get('premise') or {}).items()}) + '; self-check ' + str((mt.get('self_check') or {}).get('max_diff_by')))
        head.append(f'- {lab}: ckpt {mt.get("ckpt")} sha256 {mt.get("sha256")} ({mt.get("sha_check", "sha check not recorded")}); real strata: '
                    f'{mt.get("real_strata_checked")}; self-check {mt.get("self_check")}; rewrites {mt.get("rewrites")}')
    secs = [sec_repro(by_label, meta, expect, no_gate, fails, accept_allowed), sec_identity(by_label), sec_roles(by_label), sec_2x2(by_label), sec_first_wrong(by_label),
            sec_repair(by_label), sec_classifiers(by_label), sec_b1b2(by_label), sec_rewrites(by_label), sec_margins(by_label)]
    if 'ACCEPTED ALLOWED FAILURES' in secs[0]:
        head.insert(1, '**!!! ACCEPTED ALLOWED FAILURES (--accept-allowed-failures): see section 0; some failures that collect let through are accepted !!!**\n')
    return '\n'.join(head) + '\n\n' + '\n\n'.join(secs), fails


# ---------- command line ----------

def rewrite_list(text):
    """argparse type of --rewrites: 'plus,swap' -> ('plus', 'swap'); '' -> (); an unknown name is an argparse error (not an assert)."""
    names = tuple(x.strip() for x in text.split(',') if x.strip())
    bad = [x for x in names if x not in REWRITES]
    if bad:
        raise argparse.ArgumentTypeError(f'unknown rewrite(s) {bad}: choose from {", ".join(REWRITES)}')
    return names


def main(argv=None):
    a = argparse.ArgumentParser(description='Bracket probe: per-round teacher-forced correctness vs the free run (scoring only, nothing is trained).')
    sub = a.add_subparsers(dest='cmd', required=True)
    c = sub.add_parser('collect')
    c.add_argument('--ckpt', required=True)
    c.add_argument('--sha256', default=None, help='refuse the checkpoint unless its sha256 is this (required unless --no-sha)')
    c.add_argument('--no-sha', action='store_true', help='run without a checksum check; the meta records "sha unchecked"')
    c.add_argument('--label', required=True)
    c.add_argument('--eval-rows', required=True)
    c.add_argument('--probe', default=None, help='sheet-probe.jsonl: its F0-near and F4-two cells are run too (F0-near only keeps the scorer\'s batch order)')
    c.add_argument('--rewrites', default=','.join(REWRITES), type=rewrite_list,
                   help=f'comma-separated, from {",".join(REWRITES)} (empty = none)')
    c.add_argument('--rewrite-strata', default='HO', help='strata whose (K)*(J) items are rewritten')
    c.add_argument('--threads', type=int, default=4)
    c.add_argument('--bs', type=int, default=64)
    c.add_argument('--no-margins', action='store_true')
    c.add_argument('--self-check', type=int, default=256, help='rows for the own-calls identity self-check: every D row + a cell-stratified sample up to this total (0 = skip)')
    c.add_argument('--limit', type=int, default=None, help='first N rows only (smoke test; the real-strata check is then not run)')
    c.add_argument('--validate-sample', type=int, default=64, help='validate_repair: single-wrong-round items per stratum other than D (D is validated on all); 0 = none')
    c.add_argument('--no-validate', action='store_true', help='do not run validate_repair (the report then fails its gate)')
    c.add_argument('--allow-premise-fail', action='store_true', help='record a failed premise check / self-check / strata check in the meta instead of stopping')
    c.add_argument('--out', required=True)
    r = sub.add_parser('report')
    r.add_argument('dirs', nargs='+')
    r.add_argument('--expect', nargs='*', default=[], help='KEY=HITS[/N] or LABEL:KEY=HITS[/N], KEY a cell or stratum (e.g. HO=59/420 L14:D=0)')
    r.add_argument('--no-gate', action='store_true', help='report without the reproduction gate (the report says GATE NOT RUN)')
    r.add_argument('--accept-allowed-failures', action='store_true',
                   help='do not fail on failures that collect recorded under --allow-premise-fail (a premise / self-check / strata failure): they are accepted and '
                        'ACCEPTED ALLOWED FAILURES is printed. An empty D validation group is NOT an allowed failure and still fails')
    r.add_argument('--out', default=None, help='default: DIR/bracket-report.md for the first DIR')
    a_ = a
    a = a.parse_args(argv)
    if a.cmd == 'collect':
        if a.no_sha == (a.sha256 is not None):
            a_.error('collect needs exactly one of --sha256 HEX (the checkpoint is refused unless it matches) and --no-sha')
        if a.sha256 is not None and not a.sha256.strip():
            a_.error('--sha256 is empty: an empty string checks nothing')
        import torch
        torch.set_num_threads(a.threads)
        rewrites = a.rewrites
        try:
            recs, meta = collect(a.ckpt, a.label, LP.load_jsonl(a.eval_rows), LP.load_jsonl(a.probe) if a.probe else None, rewrites,
                                 tuple(x for x in a.rewrite_strata.split(',') if x), a.bs, not a.no_margins, a.sha256, a.self_check, a.limit,
                                 validate_sample=a.validate_sample, allow_premise_fail=a.allow_premise_fail, validate=not a.no_validate)
        except ChecksumRefused as e:    # only check_sha's refusal; every other exception propagates
            sys.exit(f'REFUSED: {e}')
        except PremiseFailed as e:
            sys.exit(f'FATAL: {e}\nnothing was written (--allow-premise-fail records the failure in the meta and goes on)')
        os.makedirs(a.out, exist_ok=True)
        base = os.path.join(a.out, f'bracket-{a.label}')
        with open(base + '.jsonl', 'w') as f:
            for rec in recs:
                f.write(json.dumps(rec) + '\n')
        with open(base + '.meta.json', 'w') as f:
            json.dump(meta, f, indent=1)
        o = [r for r in recs if r['version'] == 'orig']
        print('free hits per cell:', {c: f"{sum(r['free']['hit'] for r in o if r['split'] == c)}/{sum(1 for r in o if r['split'] == c)}"
                                      for c in sorted({r['split'] for r in o})})
        idc = identity_check(o)
        print(f'identity: agree {idc["agree"]}/{idc["n"]}, round-level {idc["round_agree"]}/{idc["n"]}; self-check {meta.get("self_check")}; '
              f'rewrites {meta["rewrites"]}; drops {meta["drops"]}')
        print('premise (gold calls forced into a free run reproduce the gold tape), ok/n per version:',
              {v: f'{pc["ok"]}/{pc["n"]}' + (f' ({pc["dropped"]} not checked)' if pc['dropped'] else '') for v, pc in meta['premise'].items()})
        v = meta['validate']
        print('validate_repair:', 'NOT RUN' if v is None else {k: f'{x["agree"]}/{x["n"]}' for kind in ('strata', 'sets') for k, x in v[kind].items()})
        if meta['allowed_failures']:
            print('ALLOWED FAILURES (recorded in the meta):', meta['allowed_failures'], file=sys.stderr)
        print('wrote', base + '.jsonl')
    else:
        try:
            parse_expect(a.expect)
        except ValueError as e:
            a_.error(str(e))
        if a.no_gate and a.expect:
            a_.error('--no-gate and --expect together: either run the gate or do not')
        try:
            by_label, meta = load_records(a.dirs)
        except ValueError as e:
            sys.exit(f'ERROR: {e}')
        text, fails = make_report(by_label, meta, a.expect, a.no_gate, a.accept_allowed_failures)
        out = a.out or (os.path.join(a.dirs[0], 'bracket-report.md') if os.path.isdir(a.dirs[0]) else None)
        if out:
            with open(out, 'w') as f:
                f.write(text + '\n')
            print('wrote', out, file=sys.stderr)
        print(text)
        if 'ACCEPTED ALLOWED FAILURES' in text:
            print('!!! ACCEPTED ALLOWED FAILURES: the failures listed in section 0 of the report were let through by --allow-premise-fail at collect '
                  'and accepted by --accept-allowed-failures !!!', file=sys.stderr)
        if fails and not a.no_gate:
            print('GATE FAILED:\n  ' + '\n  '.join(fails), file=sys.stderr)
            raise SystemExit(1)


if __name__ == '__main__':
    main()
