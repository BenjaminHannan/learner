"""Exploratory (fast lane) pretraining of the core on the generated skills curriculum (PR #32).

Not a sealed run. Same frozen LFM, same reader + core + prefix + calculator-path modules and the same
per-update step as the English pilot (train_english_paraphrase_pilot_windows_v1.train_step), but the
input is a curriculum prompt and the target is its short answer. Starts from a pilot parent checkpoint
and continues its Adam state. Rows are read in file order (easy to hard); --updates takes an even
stride through train.jsonl so every stage is visited.

usage: skills_pretrain_v1.py --root PKG --data OUT_DIR --out REL_DIR --updates N [--parent-seed 0]
       [--eval-every 4000] [--dev-n 100] [--minutes 120] [--phase train|eval]
       [--parent-path CKPT.pt] [--eval-at-start] [--no-checkpoint]   (stiffness test, STIFFNESS-TEST-v1.md)
       [--eval-only] [--dev-kinds in_dist,family] [--sample-seed S] [--fixed-rows M --passes P]   (plateau diagnosis, PLATEAU-DIAG-v1.md)
       [--plan-route N]   (copy-path + gen-fix + steps: a frozen planner + exact calculator answers the 4 chain families; the LM speaks it)
       [--plan-talk]      (with --plan-route: the planner's plan goes to the talker as a note, the talker writes calc(...), a calculator replies, the talker answers)
Writes OUT/final-checkpoint.pt (parent-shaped, so the English pilot can start from it) and OUT/SKILLS-RESULT.json.
"""
import argparse
import copy
import random
import json
import math
import re
from pathlib import Path
import sys
import time
from collections import Counter

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import english_pilot_common_v1 as common  # noqa: E402
import english_pilot_runtime_v1 as runtime  # noqa: E402
import train_english_paraphrase_pilot_windows_v1 as trainer  # noqa: E402

BUSY = Path(r'C:\Users\benja\GPU-BUSY.txt')
EXP = 'artifacts/cap256-launch/contextual-input-compare-v1/ENGLISH-PILOT-v1/CONFIGS-v1/'
CP = {'ids': None}
STEPS = {'on': False}
SEP = ' # '
DEV = ('in_dist', 'answer', 'frame', 'vocab', 'variant', 'family')


def norm(s):
    return ' '.join(s.strip().lower().split())


LORA = {'on': True}
SHUF = {'prev': None, 'on': False}
CHAT = {}
TWO = {'ce2': []}
AUX = {}
TXT = {'on': False}
LES = {'mode': None, 'store': {}, 'fam': None, 'key': None, 'rstore': {}, 'rswap': {}, 'nstore': {}, 'nswap': {}}  # --final-lesions: replace each row's pooled core vectors at eval (rstore/rswap: --plan-route R tokens; nstore/nswap: --plan-talk notes)
CHAIN_FAMS = ('chain_ops', 'state_update', 'chain_story2', 'var_chain')  # --plan-route: the families the planner + calculator answer
PLAN = {'on': False, 'pl': None, 'ud': None, 'shown': False, 'talk': False, 'talk_shown': False}
THINK = ' thinker: '  # --plan-talk: R = THINK + the planner's note
CALL = 'calc('  # --plan-talk: the talker's call is ' calc(' + note + ')'

def rich_steps(row):
    try:
        return _rich_steps(row)
    except (KeyError, IndexError, ValueError):  # dev splits with other variants/meta keep their curriculum steps
        return row['steps']


def _rich_steps(row):
    """Worked steps from the row's own meta for the four families whose curriculum steps are only labels
    ("look up each letter", "infer rule", "cycle length 2"); every other family keeps its steps. Each list ends in
    a line that states the answer's ingredients, so the answer after " # " follows from the steps alone."""
    f, v, m = row['family'], row.get('variant'), row.get('meta') or {}
    if f == 'cipher_map':
        table = dict(zip(m['letters'], m['nums']))
        if v == 'encode':
            return ['%s=%d' % (c, table[c]) for c in m['w']]
        inv = {n: c for c, n in table.items()}
        return ['%d=%s' % (n, inv[n]) for n in m['n']]
    if f == 'fewshot_number_rule':
        if v == 'pair_sum':
            (a, b), q = m['pairs'][0], m['pairs'][-1]
            return ['%d + %d = %d so add' % (a, b, a + b), '%d + %d = %d' % (q[0], q[1], q[0] + q[1])]
        x0, q = m['xs'][0], m['xs'][-1]
        if v == 'add':
            return ['%d - %d = %d' % (x0 * m['A'] + m['B'], x0, m['B']), 'rule: add %d' % m['B'], '%d + %d = %d' % (q, m['B'], q + m['B'])]
        if v == 'mult':
            return ['%d / %d = %d' % (x0 * m['A'] + m['B'], x0, m['A']), 'rule: times %d' % m['A'], '%d * %d = %d' % (q, m['A'], q * m['A'])]
    if f == 'group_induct':
        A, B, q = m['A'], m['B'], m['q']
        if v == 'parity':
            ea = 'even' if A[0] % 2 == 0 else 'odd'
            eb = 'odd' if ea == 'even' else 'even'
            return ['A %s, B %s' % (ea, eb), '%d is %s' % (q, 'even' if q % 2 == 0 else 'odd')]
        if v == 'multiple':
            for k in range(2, 20):
                if all(x % k == 0 for x in A) and not any(x % k == 0 for x in B):
                    return ['A multiples of %d' % k, '%d is %s' % (q, 'one' if q % k == 0 else 'not')]
    if f == 'seq_cycle' and STEPS.get('seq2'):  # v2: no counting of shown items, mod written as a division
        pat, L = m['pat'], len(m['pat'])
        if v == 'kth_letter':
            k, i = m['k'], (m['k'] - 1) % len(m['pat'])
            return ['cycle ' + ' '.join('%d=%s' % (j, c) for j, c in enumerate(pat)),
                    '%d-1 = %d = %d*%d + %d' % (k, k - 1, L, (k - 1) // L, i), '%d=%s' % (i, pat[i])]
        if v == 'next_letter':
            last, nxt = pat[(m['n'] - 1) % L], pat[m['n'] % L]
            return ['cycle ' + ' '.join(pat), 'last is %s' % last, 'after %s comes %s' % (last, nxt)]
    if f == 'seq_cycle':
        pat = m['pat']
        if v == 'kth_letter':
            i = (m['k'] - 1) % len(pat)
            return ['cycle %s, length %d' % (' '.join(pat), len(pat)), '(%d-1) mod %d = %d' % (m['k'], len(pat), i), 'item %d = %s' % (i, pat[i])]
        if v == 'next_letter':
            i = m['n'] % len(pat)
            return ['cycle %s, length %d' % (' '.join(pat), len(pat)), '%d mod %d = %d' % (m['n'], len(pat), i), 'item %d = %s' % (i, pat[i])]
    return row['steps']


def encode(tokenizer, row, torch, device):
    ids = list(tokenizer.encode(row['prompt'], add_special_tokens=False)) + [common.EOS_ID]
    if len(ids) > 64:
        return None
    steps = rich_steps(row) if STEPS.get('rich') else row['steps']
    if row.get('family') in STEPS.get('none', ()) or (PLAN['on'] and row.get('family') in CHAIN_FAMS):
        steps = []  # --answer-only-fams / --plan-route chain rows: target ' # answer', scored by the same parse
    tgt = (' ; '.join(steps) + SEP + row['answer']) if STEPS['on'] else row['answer']
    labels = list(tokenizer.encode(tgt, add_special_tokens=False)) + [common.EOS_ID]
    return (torch.tensor([ids], device=device, dtype=torch.long), torch.ones((1, len(ids)), device=device, dtype=torch.bool),
            torch.tensor([labels], device=device, dtype=torch.long))


def direct_reader_swap(torch, reader, opt, named, feats):
    """--direct-reader: reader.proj = LN -> Linear(2048,32) -> GELU -> Linear(32,256) becomes LN -> Linear(2048,256), keeping the
    same LayerNorm module (its weights and Adam state carry over). The new Linear is the ridge least-squares fit to the old proj's
    outputs on `feats` (a list of [N,2048] frozen-LM states, one per question): fitted on the first 7/8 of the questions, R^2
    also reported on the last 1/8. The four old Linear tensors leave the optimizer; the new Linear gets its own group (fresh Adam
    state, the optimizer's defaults). Returns (named, info)."""
    seq = reader.proj
    ln, l1, l3 = seq[0], seq[1], seq[3]
    cut = len(feats) - len(feats) // 8
    with torch.no_grad():
        X = [torch.cat([ln(f.float()) for f in part]).double() for part in (feats[:cut], feats[cut:])]
        Y = [torch.cat([seq(f.float()) for f in part]).double() for part in (feats[:cut], feats[cut:])]
        Xa = [torch.cat([x, torch.ones(len(x), 1, dtype=x.dtype, device=x.device)], 1) for x in X]
        A = Xa[0].T @ Xa[0]
        A += 1e-3 * A.diagonal().mean() * torch.eye(A.shape[0], dtype=A.dtype, device=A.device)
        Wb = torch.linalg.solve(A, Xa[0].T @ Y[0])

        def r2(x, y):
            return float(1 - ((y - x @ Wb) ** 2).sum() / ((y - y.mean(0)) ** 2).sum())
        lin = torch.nn.Linear(l1.in_features, l3.out_features).to(l1.weight.device)
        lin.weight.copy_(Wb[:-1].T.float())
        lin.bias.copy_(Wb[-1].float())
        info = {'questions': len(feats), 'fit_tokens': len(Xa[0]), 'check_tokens': len(Xa[1]),
                'r2_fit': round(r2(Xa[0], Y[0]), 4), 'r2_check': round(r2(Xa[1], Y[1]), 4) if len(Xa[1]) else None}
    old = (l1.weight, l1.bias, l3.weight, l3.bias)
    gone = {id(p) for p in old}
    for g in opt.param_groups:
        g['params'] = [p for p in g['params'] if id(p) not in gone]
    for p in old:
        opt.state.pop(p, None)
    opt.add_param_group({'params': [lin.weight, lin.bias]})
    reader.proj = torch.nn.Sequential(ln, lin)
    named = [(n, p) for n, p in named if id(p) not in gone] + [('reader.direct.weight', lin.weight), ('reader.direct.bias', lin.bias)]
    info['params'] = sum(p.numel() for p in reader.parameters())
    return named, info


# ---------------------------------------------------------------- --plan-route: frozen planner + exact calculator
class Planner:
    """The uc_diag_v4 --mode plan --op-attend learner: its own reader + core and three heads, no LM in its loss.
    ptr: per question token, slot 0 = start number, slots 1..5 = operand of step 1..5; op: 5 steps x {+,-,*,/,STOP}
    from the 8-chunk pooled state; op_tok: adds what the pointer-attended token says to each step's op (pointer detached)."""

    def __init__(self, reader, core, ptr, op, op_tok):
        self.reader, self.core, self.ptr, self.op, self.op_tok = reader, core, ptr, op, op_tok

    def modules(self):
        return [self.core, self.reader, self.ptr, self.op, self.op_tok]

    def logits(self, rt, f, mask):
        F = rt.torch.nn.functional
        h, _ = runtime.english_graph(rt, self.core, self.reader, f, mask)
        z = F.layer_norm(h.float(), (256,))
        lg, ol = self.ptr(z[0]), self.op(F.adaptive_avg_pool1d(z[0].T[None], 8)[0].T.reshape(1, -1)).view(5, 5)
        return lg, ol + self.op_tok(F.softmax(lg[:, 1:].detach(), 0).T @ z[0])


def plan_parse(rt, tokenizer, pl, feats, ids, mask):
    """the (frozen) planner's argmax pointers am (slots 0..5), argmax op indices oa (5 steps, into ud.PLAN_OPS), and the stripped prompt tokens"""
    with rt.torch.no_grad():
        lg, ol = pl.logits(rt, feats, mask)
    am, oa = lg.argmax(0).tolist(), ol.argmax(1).tolist()
    toks = [tokenizer.decode([t]).strip() for t in ids[0].tolist()]
    return am, oa, toks


def plan_value(rt, tokenizer, ud, pl, feats, ids, mask):
    """argmax pointers + ops of the (frozen) planner, run through the exact calculator -> int, or None if not executable"""
    am, oa, toks = plan_parse(rt, tokenizer, pl, feats, ids, mask)
    return ud.plan_exec(ud.to_int(toks[am[0]]), [ud.PLAN_OPS[j] for j in oa], [ud.to_int(toks[t]) for t in am[1:]])


def render_note(toks, am, ops):
    """--plan-talk: a plan as text. toks = stripped prompt tokens, am = pointers (slot 0 = start, slot k = operand of step k), ops = op symbols
    (5 steps, STOP ends). '10 - 5 * 5' = start 10, then '- 5', then '* 5'. No ops before the first STOP -> just the start token."""
    note = toks[am[0]]
    for k, o in enumerate(ops):
        if o == 'STOP':
            break
        note += ' ' + o + ' ' + toks[am[k + 1]]
    return note


def plan_note(rt, tokenizer, ud, pl, feats, ids, mask):
    """--plan-talk: (note, value) for one question: the planner's argmax plan as text (render_note) and plan_value's result"""
    am, oa, toks = plan_parse(rt, tokenizer, pl, feats, ids, mask)
    ops = [ud.PLAN_OPS[j] for j in oa]
    return render_note(toks, am, ops), ud.plan_exec(ud.to_int(toks[am[0]]), ops, [ud.to_int(toks[t]) for t in am[1:]])


CALC_RE = re.compile(r'(-?\d+)((?:\s*[-+*/]\s*-?\d+)*)')
CALC_STEP = re.compile(r'([-+*/])\s*(-?\d+)')


def calc_fold(s, ud=None):
    """--plan-talk calculator tool: 'a op b op c ...' (integers, + - * /, spaces optional, a leading '-' on a number allowed) folded LEFT TO RIGHT
    with exact integer division (ud.plan_exec) -> int; None if it does not parse or a division is not exact (or divides by 0)"""
    m = CALC_RE.fullmatch(s.strip())
    if m is None:
        return None
    ud = ud or PLAN['ud'] or __import__('uc_diag_v4')
    steps = CALC_STEP.findall(m.group(2))
    return ud.plan_exec(ud.to_int(m.group(1)), [o for o, _ in steps], [ud.to_int(w) for _, w in steps])


def tool_reply(value):
    """the calculator's reply text for calc_fold's result"""
    return ' = %s' % (value if value is not None else '?')


def talk_labels(torch, tokenizer, note, c_ids, device, ud=None):
    """--plan-talk target for a chain row = A + B + C, each tokenized separately (as at generation): A = ' calc(' + note + ')' (the talker's call),
    B = the calculator's reply to that note (the tool writes it, not the talker), C = c_ids (SEP + answer + EOS, as encode builds it for these rows).
    Returns (labels [1,L] long, loss mask [1,L] bool: False exactly on B, (A, B, C) id lists)"""
    A = list(tokenizer.encode(' ' + CALL + note + ')', add_special_tokens=False))
    B = list(tokenizer.encode(tool_reply(calc_fold(note, ud)), add_special_tokens=False))
    C = list(c_ids)
    return (torch.tensor([A + B + C], device=device, dtype=torch.long),
            torch.tensor([[True] * len(A) + [False] * len(B) + [True] * len(C)], device=device, dtype=torch.bool), (A, B, C))


def talk_train_row(torch, tokenizer, row, labels, device):
    """--plan-talk training row, called after plan_route_row: a chain row (CP['note'] set) gets labels = A + B + C of its note (talk_labels; C = the
    ' # answer' + EOS labels encode built) and CP['LM'] = the loss mask; any other row, or the flag off, keeps `labels` (CP['LM'] stays None/unset)"""
    if not PLAN.get('talk') or CP.get('note') is None:
        return labels
    labels, CP['LM'], abc = talk_labels(torch, tokenizer, CP['note'], labels[0].tolist(), device)
    if not PLAN['talk_shown']:
        PLAN['talk_shown'] = True
        print(json.dumps({'event': 'plan-talk-labels', 'id': row.get('id'), 'R': tokenizer.decode(CP['R'][0].tolist()), 'A': tokenizer.decode(abc[0]),
                          'B': tokenizer.decode(abc[1]), 'C': tokenizer.decode(abc[2]), 'tokens': [len(x) for x in abc], 'counted': int(CP['LM'].sum()),
                          'answer': row['answer']}), flush=True)
    return labels


def masked_human_loss(rt, lm, prefix, target, bos, eos, lmask):
    """--plan-talk: human_loss (BOS + shifted target teacher forcing, per-example mean) where the INPUT still holds every target token (the talker
    reads the tool's reply) but only positions with lmask True count in the loss. No -100 in `target` (human_loss would also hide those from
    attention and replace them by EOS at the input). Same arithmetic as human_loss: with lmask all True the result is identical.
    Returns (per-example loss [B], argmax predictions [B,T])"""
    torch = rt.torch
    emb = lm.get_input_embeddings()
    start = torch.full((len(target), 1), bos, device=target.device, dtype=torch.long)
    shifted = torch.cat((start, target[:, :-1]), 1)
    x = torch.cat((prefix.to(emb.weight.dtype), emb(shifted)), 1)
    attention = torch.ones(x.shape[:2], device=x.device, dtype=torch.long)
    logits = lm(inputs_embeds=x, attention_mask=attention, use_cache=False).logits[:, prefix.shape[1]:].float()
    loss = torch.nn.functional.cross_entropy(logits.transpose(1, 2), target, reduction='none')
    per = (loss * lmask.to(loss.dtype)).sum(1) / lmask.sum(1)
    return per, logits.detach().argmax(-1)


def lm_loss(rt, lm, prefix, target, bos, eos):
    """the LM's teacher-forced loss for one row: human_loss, or masked_human_loss when CP['LM'] holds a loss mask (--plan-talk chain rows).
    Returns (per-example loss, predictions, mask of the positions that count)"""
    lmask = CP.get('LM')
    if lmask is None:
        per, pred = rt.human_loss(lm, prefix, target, bos, eos, True, True)
        return per, pred, target != -100
    per, pred = masked_human_loss(rt, lm, prefix, target, bos, eos, lmask)
    return per, pred, lmask


def train_planner(rt, lm, tokenizer, ud, parts, rows, seed, device, every=2000, cosine=False):
    """Build the planner from deep copies of the restored reader + core, re-initialised like ud.reset_fresh (torch seeded with
    `seed` first, then again right before the heads, as mode_plan does), and train it like mode_plan --op-attend --fresh-rows:
    one pass over `rows` (rows whose plan does not parse / has >5 steps / has a literal missing from the question / is too long
    are skipped), batch 1, AdamW lr 1e-3 wd 0, clip 1.0, linear warmup 200, loss = op CE summed over the 5 steps + pointer NLL
    over the used slots. Features are computed per row (one pass, no cache). Returns the planner, frozen (eval, requires_grad off),
    and an info dict. The caller's RNG state is restored afterwards, so the main run's RNG does not depend on the route.
    cosine (--plan-cosine): the lr also decays to 0 along a cosine over the kept rows, as mode_plan --lr-cosine."""
    torch = rt.torch
    F = torch.nn.functional
    t0 = time.time()
    dv = torch.device(device)
    with torch.random.fork_rng(devices=[dv.index if dv.index is not None else torch.cuda.current_device()] if dv.type == 'cuda' else []):
        pc, pr = copy.deepcopy(parts['core']), copy.deepcopy(parts['reader'])
        if not rt.cap64.is_bound(pc):  # deepcopy keeps the instance binding on the copy; rebind if it ever does not
            vars(pc).pop('begin_latent', None)
            rt.cap64.bind_english_cap64(pc)
        torch.manual_seed(seed)
        ud.reset_fresh({'core': pc, 'reader': pr})
        pc.halt.requires_grad_(False)
        torch.manual_seed(seed)
        ptr, op = torch.nn.Linear(256, 6).to(device), torch.nn.Linear(2048, 25).to(device)
        op_tok = torch.nn.Linear(256, 5).to(device)
        pl = Planner(pr, pc, ptr, op, op_tok)
        train_params = [p for m in (pc, pr) for p in m.parameters() if p.requires_grad] + \
            [p for m in (ptr, op, op_tok) for p in m.parameters()]
        opt = torch.optim.AdamW(train_params, lr=1e-3, weight_decay=0)
        n_upd = sum(1 for r in rows if (lambda e: e and ud.plan_labels(tokenizer, r, e[0][0].tolist())[0])(encode(tokenizer, r, torch, device))) if cosine else 0
        cos = (lambda i: 0.5 * (1 + math.cos(math.pi * min(i, n_upd) / n_upd))) if cosine and n_upd else (lambda i: 1.0)
        sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda i: min(1, (i + 1) / 200) * cos(i))
        pc.train()
        pr.train()
        u, dropped, losses = 0, Counter(), []
        for row in rows:
            enc = encode(tokenizer, row, torch, device)
            lab, why = ud.plan_labels(tokenizer, row, enc[0][0].tolist()) if enc else (None, 'long')
            if lab is None:
                dropped[why] += 1
                continue
            ids, mask, _ = enc
            f = rt.compare.extract_question_features(lm, ids, mask, 'contextual', torch)
            ops5 = lab['ops'] + ['STOP'] * (5 - len(lab['ops']))
            tgt = torch.tensor([ud.PLAN_OPS.index(o) for o in ops5], device=device)
            opt.zero_grad(set_to_none=True)
            lg, ol = pl.logits(rt, f, mask)
            lp = F.log_softmax(lg, 0)
            loss = F.cross_entropy(ol, tgt, reduction='sum') - sum(
                torch.logsumexp(lp[torch.tensor(lab['P'][k], device=device), k], 0) for k in range(len(lab['ops']) + 1))
            loss.backward()
            torch.nn.utils.clip_grad_norm_(train_params, 1.0)
            opt.step()
            sched.step()
            u += 1
            losses.append(float(loss.detach()))
            if u % every == 0:
                print(json.dumps({'event': 'plan-pretrain', 'update': u, 'loss': round(sum(losses[-every:]) / every, 4),
                                  'minutes': round((time.time() - t0) / 60, 2)}), flush=True)
        for m in pl.modules():
            m.eval()
            m.requires_grad_(False)
    info = {'rows': len(rows), 'updates': u, 'minutes': round((time.time() - t0) / 60, 2),
            'final_loss': round(sum(losses[-every:]) / len(losses[-every:]), 4) if losses else None,
            'dropped': dict(dropped), 'seed': seed, 'cosine': bool(cosine), 'cosine_updates': n_upd}
    return pl, info


def plan_swap_map(rstore):
    """{key: (family, R)} in visit order -> {key: R of the next same-family row, cyclic} (same construction as LES['swap'])"""
    byf = {}
    for k, (f, R) in rstore.items():
        byf.setdefault(f, []).append((k, R))
    return {kv[j][0]: kv[(j + 1) % len(kv)][1] for kv in byf.values() for j in range(len(kv))}


def plan_lesion_R(own_R):
    """--final-lesions: 'collect' remembers this chain row's R; 'plan_swap' returns the next same-family row's R; else the row's own"""
    if LES['mode'] == 'collect':
        LES['rstore'].setdefault(LES['key'], (LES['fam'], own_R))
    elif LES['mode'] == 'plan_swap':
        return LES['rswap'].get(LES['key'], own_R)
    return own_R


def plan_lesion_note(own_note):
    """--final-lesions with --plan-talk: 'collect' remembers this chain row's note; 'plan_swap' returns the next same-family row's note; else the row's own"""
    if LES['mode'] == 'collect':
        LES['nstore'].setdefault(LES['key'], (LES['fam'], own_note))
    elif LES['mode'] == 'plan_swap':
        return LES['nswap'].get(LES['key'], own_note)
    return own_note


def plan_talk_row(rt, tokenizer, row, feats, ids, mask, device):
    """--plan-talk, chain row: CP['R'] = tokens of THINK + note (the planner's plan as text), CP['note'] = the note the talker is given (after the
    plan_swap lesion; None when note_drop gives it none and R is None), CP['own_note'] = this row's own planner note. Returns (True, planner value)"""
    note, v = plan_note(rt, tokenizer, PLAN['ud'], PLAN['pl'], feats, ids, mask)
    CP['own_note'] = note
    if LES['mode'] == 'note_drop':  # lesion: the talker gets no note at all
        return True, v
    note = plan_lesion_note(note)
    CP['note'] = note
    CP['R'] = rt.torch.tensor([tokenizer.encode(THINK + note, add_special_tokens=False)], device=device)
    return True, v


def plan_route_row(rt, tokenizer, row, feats, ids, mask, device):
    """--plan-route: set CP['R'] for this row = ' = <planner value>' tokens for a chain-family row ('?' if the plan cannot run),
    None for any other row. Returns (is_chain_row, planner value). Does nothing (CP untouched) when the route is off.
    --plan-talk: chain rows get THINK + note instead (plan_talk_row) and CP's F (forced tokens), LM (loss mask), note, own_note are reset for every row."""
    if not PLAN['on']:
        return False, None
    CP['R'] = None
    if PLAN.get('talk'):
        CP.update(F=None, LM=None, note=None, own_note=None)
    if row.get('family') not in CHAIN_FAMS:
        return False, None
    if PLAN.get('talk'):
        return plan_talk_row(rt, tokenizer, row, feats, ids, mask, device)
    v = plan_value(rt, tokenizer, PLAN['ud'], PLAN['pl'], feats, ids, mask)
    CP['R'] = plan_lesion_R(rt.torch.tensor([tokenizer.encode(' = %s' % (v if v is not None else '?'), add_special_tokens=False)], device=device))
    return True, v


def append_R(torch, emb, pe):
    """question embeddings pe [1,N,D] -> pe followed by the embeddings of CP['R'] when a chain row has one"""
    R = CP.get('R')
    return pe if R is None else torch.cat([pe, emb(R).to(pe.dtype)], 1)


def install_forced_tokens(rt, lm):
    """--plan-talk: wrap lm.generate so that, while CP['F'] holds token ids [1,n], they are appended after the generation input (the decoder builds
    [front][question][R] + BOS, then calls lm.generate(inputs_embeds=...)): the LM continues after BOS + F. A no-op while CP['F'] is None. The
    result is the newly generated ids only (the forced ones are not echoed), as HF generate does for inputs_embeds. Installed as an instance
    attribute outside the observer, which wraps whatever lm.generate is when it runs and restores it afterwards."""
    torch = rt.torch
    emb = lm.get_input_embeddings()
    orig = lm.generate

    def generate(*args, **kw):
        F = CP.get('F')
        if F is not None and 'inputs_embeds' in kw:
            kw = dict(kw)
            x = kw['inputs_embeds']
            kw['inputs_embeds'] = torch.cat([x, emb(F.to(x.device)).to(x.dtype)], 1)
            kw['attention_mask'] = torch.ones(kw['inputs_embeds'].shape[:2], device=x.device, dtype=torch.long)
        return orig(*args, **kw)
    lm.generate = generate


def talk_generate(rt, ctx, parts, feats, mask, tokenizer, max1=48, max2=16):
    """--plan-talk, one chain row. Phase 1: generate (up to max1 tokens, 48 as for steps). If the text has CALL followed later by ')', cut the generation at the token
    that closed the call (greedy, so this equals stopping there), run the calculator on the text between 'calc(' and the first ')' after it, and
    phase 2: generate up to max2 more tokens with CP['F'] = the phase-1 tokens through the closing token + the tool reply's tokens forced after
    BOS. No call -> the phase-1 text. Returns dict: text (full decoded text), call (content or None), tool (calculator value or None)"""
    torch = rt.torch
    obs = runtime.generate_observed(rt, ctx.dec, parts['core'], parts['reader'], feats, mask, max1)
    out = list(obs['MODEL_native_decoder_return'][0]) if obs['MODEL_native_decoder_return'] else []
    for j in range(len(out)):
        t = tokenizer.decode(out[:j + 1], skip_special_tokens=True)
        i = t.find(CALL)
        c = t.find(')', i + len(CALL)) if i >= 0 else -1
        if c >= 0:
            break
    else:
        return {'text': tokenizer.decode(out, skip_special_tokens=True), 'call': None, 'tool': None}
    call, tool = t[i + len(CALL):c], calc_fold(t[i + len(CALL):c])
    forced = out[:j + 1] + list(tokenizer.encode(tool_reply(tool), add_special_tokens=False))
    CP['F'] = torch.tensor([forced], device=ctx.device, dtype=torch.long)
    try:
        obs = runtime.generate_observed(rt, ctx.dec, parts['core'], parts['reader'], feats, mask, max2)
    finally:
        CP['F'] = None
    out2 = list(obs['MODEL_native_decoder_return'][0]) if obs['MODEL_native_decoder_return'] else []
    return {'text': tokenizer.decode(forced + out2, skip_special_tokens=True), 'call': call, 'tool': tool}


def evaluate(rt, ctx, modules, rows, tokenizer):
    torch = rt.torch
    parts = runtime.module_dict(modules)
    for _, m in modules:
        m.eval()
    ok = skipped = plan_ok = plan_n = 0
    fam, texts = {}, []
    talk = {'n': 0, 'calls': 0, 'call_eq_note': 0, 'answer_eq_calc': 0}  # --plan-talk, chain rows: rows / with a call / call == the note the talker got / answer == calc_fold(that note)

    def lm_input_len(feats, mask):  # length of what the LM gets before BOS at generation
        with torch.no_grad():
            h_, _ = runtime.english_graph(rt, parts['core'], parts['reader'], feats, mask)
            pk = rt.FinalLatent(h_, torch.ones_like(h_, dtype=torch.bool), mask, (1, h_.shape[1]))
            return int(ctx.dec.adapter(pk).shape[1])
    for row in rows:
        enc = encode(tokenizer, row, torch, ctx.device)
        if enc is None:
            skipped += 1
            continue
        ids, mask, _ = enc
        CP['ids'] = ids
        LES['fam'], LES['key'] = row.get('family', '?'), row.get('id', id(row))
        feats = rt.compare.extract_question_features(ctx.lm, ids, mask, 'contextual', torch)
        chain, pv = plan_route_row(rt, tokenizer, row, feats, ids, mask, ctx.device)  # --plan-route: sets CP['R']
        if chain:
            plan_n += 1
            plan_ok += pv is not None and str(pv) == norm(row['answer'])
            if not PLAN['shown'] and CP['R'] is not None:  # layout of the first chain row: [front vectors][question + EOS][R] then BOS (R is None only under the note_drop lesion)
                PLAN['shown'] = True
                plen = lm_input_len(feats, mask)
                print(json.dumps({'event': 'plan-route-layout', 'id': row.get('id'), 'family': row['family'],
                                  'prompt_tokens_with_EOS': int(ids.shape[1]), 'R_ids': CP['R'][0].tolist(),
                                  'R_decoded': tokenizer.decode(CP['R'][0].tolist()), 'planner_value': pv, 'answer': row['answer'],
                                  'lm_input_before_BOS': plen, 'front_vectors': plen - int(ids.shape[1]) - int(CP['R'].shape[1])}), flush=True)
        if row is rows[0] and not SHUF['on']:  # what length does the LM input have at generation?
            plen = lm_input_len(feats, mask)
            print(json.dumps({'event': 'gen-layout', 'prompt_tokens_with_EOS': int(ids.shape[1]), 'lm_input_before_BOS': plen}), flush=True)
        talked = chain and PLAN.get('talk')  # --plan-talk chain row: the talker may call the calculator (two-phase generation)
        if talked:
            tk = talk_generate(rt, ctx, parts, feats, mask, tokenizer)
            text = raw = tk['text']
        else:
            obs = runtime.generate_observed(rt, ctx.dec, parts['core'], parts['reader'], feats, mask, 48 if STEPS['on'] else 12)
            out = obs['MODEL_native_decoder_return'][0] if obs['MODEL_native_decoder_return'] else []
            text = raw = tokenizer.decode(out, skip_special_tokens=True)
        if STEPS['on']:
            text = text.rsplit('#', 1)[-1] if '#' in text else '\x00no-answer'
        hit = norm(text) in {norm(a) for a in row['accepted']}
        ok += hit
        if talked:
            note, cv = CP['note'], calc_fold(CP['note']) if CP['note'] is not None else None  # the note the talker actually got (swapped under plan_swap, None under note_drop)
            talk['n'] += 1
            talk['calls'] += tk['call'] is not None
            talk['call_eq_note'] += tk['call'] is not None and note is not None and ' '.join(tk['call'].split()) == ' '.join(note.split())
            talk['answer_eq_calc'] += cv is not None and norm(text) == str(cv)
        if TXT['on']:
            texts.append([row.get('id'), row.get('family'), row['answer'], raw, bool(hit), LES['mode']] + ([note, tk['call'], tk['tool']] if talked else []))
        f = fam.setdefault(row.get('family', '?'), [0, 0])
        f[0] += hit
        f[1] += 1
    for _, m in modules:
        m.train()
    parts['core'].halt.requires_grad_(False)
    return {'correct': ok, 'n': len(rows) - skipped, 'skipped': skipped, 'by_family': fam, **({'texts': texts} if TXT['on'] else {}),
            **({'plan_correct': plan_ok, 'plan_n': plan_n} if PLAN['on'] else {}), **({'talk': talk} if PLAN.get('talk') else {})}


def load_dev(data, n):
    dev = {}
    for k in DEV:
        p = Path(data) / 'dev' / (k + '.jsonl')
        rows = [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []
        step = max(1, len(rows) // n)
        dev[k] = rows[::step][:n]
    return dev


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', required=True)
    ap.add_argument('--data', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--updates', type=int, required=True)
    ap.add_argument('--parent-seed', type=int, default=0)
    ap.add_argument('--eval-every', type=int, default=4000)
    ap.add_argument('--dev-n', type=int, default=100)
    ap.add_argument('--minutes', type=float, default=120)
    ap.add_argument('--lr-mult', type=float, default=1.0)
    ap.add_argument('--lr-final-mult', type=float, default=None, help='cosine-decay lr from lr-mult to this multiple over the run')
    ap.add_argument('--plan-route', type=int, default=0, help='N>0, with --copy-path --gen-fix --steps: first train a frozen planner (fresh reader+core copies + pointer/op heads, no LM in its loss; uc_diag_v4 --mode plan --op-attend) on N distinct chain-family rows, one pass; then chain_ops/state_update/chain_story2/var_chain rows get " = <value>" (planner argmax plan run through an exact calculator) appended after the question embeddings and the target " # answer"; --final-lesions adds plan_swap')
    ap.add_argument('--plan-cosine', action='store_true', help='with --plan-route: the planner\'s lr decays to 0 along a cosine over its one pass (uc_diag_v4 --lr-cosine)')
    ap.add_argument('--plan-talk', action='store_true', help='with --plan-route: the talker calls the calculator itself. Chain rows get R = " thinker: " + the planner\'s plan as text ("10 - 5 * 5") instead of " = value"; the target is " calc(note)" + the calculator\'s reply " = v" (written by the tool, not in the loss) + " # answer"; scoring generates " calc(...)", runs the calculator, forces its reply after BOS and generates the answer. --final-lesions: plan_swap swaps the note; adds note_drop (no note)')
    ap.add_argument('--final-lesions', action='store_true', help='after training, score trainfit and in_dist again with each row\'s pooled core vectors replaced by its family mean, another same-family row\'s, or the global mean (copy-path only)')
    ap.add_argument('--answer-only-fams', default='', help='with --steps: these families get the target " # " + answer, no steps')
    ap.add_argument('--save-texts', action='store_true', help='keep every generated text in the eval results (id, family, answer, text, hit, lesion mode)')
    ap.add_argument('--seq-steps-v2', action='store_true', help='with --steps-rich: seq_cycle steps without counting (next_letter: last letter, what follows it; kth_letter: indexed cycle, k-1 as L*q + r)')
    ap.add_argument('--steps-rich', action='store_true', help='with --steps: worked steps from row meta for cipher_map, fewshot_number_rule, group_induct, seq_cycle (their curriculum steps are labels only)')
    ap.add_argument('--steps', action='store_true', help='target = worked steps + " # " + answer; scored on the text after the last #')
    ap.add_argument('--copy-path', action='store_true', help='prefix = 8 pooled vectors + the prompt token embeddings (talker can copy prompt tokens)')
    ap.add_argument('--families', default='', help='comma list: train and score only these families (diagnosis)')
    ap.add_argument('--parent-path', default='', help='start from this parent-shaped checkpoint (e.g. a skills final-checkpoint.pt) instead of the pinned seed parent; any update count accepted')
    ap.add_argument('--eval-at-start', action='store_true', help='score in_dist once before the first update (curve point at update 0)')
    ap.add_argument('--no-checkpoint', action='store_true', help='do not write final-checkpoint.pt (saves ~61 MB of disk per run)')
    ap.add_argument('--eval-only', action='store_true', help='no training: score the starting checkpoint on the dev files')
    ap.add_argument('--dev-kinds', default='', help='comma list of dev files to score (default: all six)')
    ap.add_argument('--sample-seed', type=int, default=None, help='train on a seeded random sample of the (family-filtered) rows instead of the ordered stride')
    ap.add_argument('--fixed-rows', type=int, default=0, help='with --sample-seed: draw this many rows once and repeat them --passes times (reshuffled each pass); also scores them as dev "trainfit"')
    ap.add_argument('--passes', type=int, default=1)
    ap.add_argument('--feat-cache', type=int, default=0, help='T4: cache the frozen LM question features by token ids, up to this many distinct rows (0 = recompute every row, the old behaviour); off when --lm-lora')
    ap.add_argument('--receipt-every', type=int, default=1, help='T4: run the per-update gradient receipt only every N updates (1 = every update, the old behaviour; the accum path never runs it)')
    ap.add_argument('--profile-parts', action='store_true', help='T4: sync + time each part of the update; prints a skills-profile event at the end')
    ap.add_argument('--ce-dump', type=int, default=0, help='T4: write the first N updates CE (repr floats) to <out>/ce-first-N.json')
    ap.add_argument('--pointer', action='store_true', help='with --copy-path: add 8 pointer vectors (Linear 256->8 softmax over prompt positions, value = prompt embedding), the allptr exit; fresh params')
    ap.add_argument('--prefix-hidden', type=int, default=0, help='widen the exit StatePrefix 259->32->2048 hidden to this width; function-preserving, fresh Adam state for the widened layers')
    ap.add_argument('--zero-pool', action='store_true', help='with --copy-path: zero the 8 pooled core vectors (lesion: does the core matter?)')
    ap.add_argument('--lora-lr-mult', type=float, default=1.0, help='LoRA adapters train at this multiple of the base lr (v3 used 1.0, i.e. 1e-3)')
    ap.add_argument('--lm-lora', type=int, default=0, help='rank-r LoRA on every Linear inside the frozen LM (not lm_head), used only when the LM talks (off during reader feature extraction); B=0 so the start is exactly the parent; kept outside lm.parameters()')
    ap.add_argument('--shuffle-pool', action='store_true', help='with --copy-path: replace the 8 pooled core vectors with the previous question\'s (lesion: does the core carry question-specific information?)')
    ap.add_argument('--gen-fix', action='store_true', help='with --copy-path: generation sees the training layout [pooled][prompt][BOS] (the old patch put the prompt in twice at generation)')
    ap.add_argument('--back', type=int, default=0, help='with --copy-path --gen-fix: a second exit (copy of the trained StatePrefix, fresh Adam) writes this many vectors AFTER the question, right before BOS')
    ap.add_argument('--chat', action='store_true', help='with --copy-path --gen-fix: the question sits in the LM native chat template; the token before the answer is the template newline instead of BOS')
    ap.add_argument('--no-front', action='store_true', help='with --copy-path --gen-fix: drop the 8 front vectors (use with --back)')
    ap.add_argument('--two-path', type=float, default=0.0, help='with --copy-path --gen-fix: add this weight x answer CE with the LM seeing only the core vectors (no question words)')
    ap.add_argument('--accum', type=int, default=1, help='rows per optimizer update (gradient accumulation); --updates counts rows')
    ap.add_argument('--moe-revive', type=float, default=0.0, help='copy expert 0 into experts 2-7 and give the zero routers a random init with this std (function-preserving at the start)')
    ap.add_argument('--aux-weight', type=float, default=0.0, help='add this weight x the MoE load-balancing aux term to the loss (it is computed but excluded today)')
    ap.add_argument('--fresh-adam', action='store_true', help='start Adam moments from zero instead of the parent state')
    ap.add_argument('--wd', type=float, default=0.0, help='AdamW weight decay (parent recipe 0)')
    ap.add_argument('--rounds', type=int, default=4, help='latent loop rounds (shared weights; parent used 4)')
    ap.add_argument('--reader-hidden', type=int, default=0, help='widen the reader 2048->32->256 bottleneck to this width; function-preserving (new units feed zero weights), new weights get fresh Adam state; checkpoint then has the wider shape')
    ap.add_argument('--direct-reader', action='store_true', help='merged Hearer+Reader: drop the reader 2048->32->256 and let the thinker read the frozen LM\'s states through its LayerNorm + one Linear 2048->256; the Linear starts as the least-squares fit to the old reader on the first 256 distinct training questions (R^2 logged), fresh Adam state; the --plan-route planner gets the same layout (fresh, as before)')
    a = ap.parse_args()
    if a.direct_reader and (a.reader_hidden or a.lm_lora or a.eval_only):
        raise SystemExit('--direct-reader excludes --reader-hidden, --lm-lora and --eval-only')
    STEPS['on'] = a.steps
    STEPS['rich'] = a.steps_rich
    STEPS['seq2'] = a.seq_steps_v2
    STEPS['none'] = {f for f in a.answer_only_fams.split(',') if f}
    if STEPS['none'] and not a.steps:
        raise SystemExit('--answer-only-fams needs --steps')
    TXT['on'] = a.save_texts
    if a.plan_route < 0:
        raise SystemExit('--plan-route must be >= 0')
    if a.plan_cosine and not a.plan_route:
        raise SystemExit('--plan-cosine needs --plan-route')
    if a.plan_talk and not a.plan_route:
        raise SystemExit('--plan-talk needs --plan-route')
    if a.plan_route and not (a.copy_path and a.gen_fix and a.steps):
        raise SystemExit('--plan-route needs --copy-path --gen-fix --steps')
    PLAN['on'] = a.plan_route > 0
    PLAN['talk'] = a.plan_talk
    if a.steps_rich and not a.steps:
        raise SystemExit('--steps-rich needs --steps')
    SHUF['on'] = a.shuffle_pool
    root = Path(a.root).resolve()
    out = root / a.out
    out.mkdir(parents=True, exist_ok=True)
    if BUSY.exists():
        raise SystemExit('GPU-BUSY marker present: ' + BUSY.read_text()[:200])
    BUSY.write_text('skills pretrain\n')
    try:
        cfg = json.loads((root / EXP / 'TRAIN-CONFIG-v2.json').read_text())
        rt = runtime.import_runtime()
        torch = rt.torch
        rt.compare.install_cuda_memory_budget(torch, cfg['budget']['cuda_peak_reserved_cap_bytes'])
        dec, tokenizer, lm = runtime.load_native_stack(rt, root, cfg)
        parent = next(p for p in cfg['parents'] if p['seed'] == a.parent_seed)
        if a.parent_path:
            src = Path(a.parent_path).resolve()
            saved = torch.load(src, map_location='cpu', weights_only=True)
            print(json.dumps({'event': 'parent-path', 'path': str(src), 'sha256': common.digest(src), 'update': saved.get('update')}), flush=True)
        else:
            saved = torch.load(common.pinned(root, parent['checkpoint']), map_location='cpu', weights_only=True)
        modules = runtime.build_modules(rt, dec, a.parent_seed, cfg['device'])
        named = runtime.restore_parent_modules(rt, saved, modules, lm)
        names = [n for n, _ in named]
        runtime.validate_parent_metadata(saved, names, saved['update'] if a.parent_path else runtime.PARENT_UPDATE)
        opt = runtime.make_optimizer(torch, [p for _, p in named])
        runtime.restore_adam(torch, opt, saved, named)
        participation, nonzero = Counter(saved['participation']), Counter()
        if a.moe_revive:
            # main2's routers are exactly zero (zero init, equal clones, aux not in the loss), so every token goes to
            # experts 0+1 with weight 0.5 each and experts 2-7 never train. Copy expert 0 into 2-7 (function-preserving:
            # all experts equal, so any routing gives the same output) and give each router a small random init so
            # tokens spread out and the experts can diverge.
            core_ = runtime.module_dict(modules)['core']
            g = torch.Generator(device='cpu').manual_seed(4000 + (a.sample_seed or 0))
            with torch.no_grad():
                for block in core_.blocks:
                    mlp = block.mlp
                    for e_ in mlp.experts[2:]:
                        e_.load_state_dict(mlp.experts[0].state_dict())
                    mlp.router.weight.copy_(torch.randn(mlp.router.weight.shape, generator=g) * a.moe_revive)
            for n_, p_ in named:
                if '.mlp.experts.' in n_ and int(n_.split('.mlp.experts.')[1].split('.')[0]) >= 2:
                    opt.state.pop(p_, None)
            print(json.dumps({'event': 'moe-revived', 'router_std': a.moe_revive}), flush=True)
        if a.aux_weight:
            o_graph = runtime.english_graph

            def graph_aux(*x, **k):
                h_, aux_ = o_graph(*x, **k)
                AUX['v'] = aux_
                return h_, aux_
            runtime.english_graph = graph_aux
        if a.fresh_adam:
            opt.state.clear()
        if a.wd:
            for g_ in opt.param_groups:
                g_['weight_decay'] = a.wd
        if a.lm_lora:
            r_, lora = a.lm_lora, torch.nn.ModuleDict()
            g = torch.Generator(device='cpu').manual_seed(3000 + (a.sample_seed or 0))
            LORA['on'] = True

            def hook(mod, inp, out, key=None):
                if not LORA['on']:
                    return out
                A, B = lora[key + '_A'], lora[key + '_B']
                return out + B(A(inp[0].to(A.weight.dtype))).to(out.dtype)
            for name, mod in lm.model.named_modules():
                if isinstance(mod, torch.nn.Linear):
                    key = name.replace('.', '__')
                    A = torch.nn.Linear(mod.in_features, r_, bias=False)
                    B = torch.nn.Linear(r_, mod.out_features, bias=False)
                    with torch.no_grad():
                        A.weight.copy_(torch.randn(r_, mod.in_features, generator=g) / math.sqrt(mod.in_features))
                        B.weight.zero_()
                    lora[key + '_A'], lora[key + '_B'] = A, B
                    mod.register_forward_hook(lambda m, i, o, key=key: hook(m, i, o, key))
            lora = lora.to(cfg['device'])
            o_extract = rt.compare.extract_question_features

            def extract_off(*x, **k):
                LORA['on'] = False
                try:
                    return o_extract(*x, **k)
                finally:
                    LORA['on'] = True
            rt.compare.extract_question_features = extract_off
            named = named + [('lora.' + n, p) for n, p in lora.named_parameters()]
            opt.add_param_group({'params': list(lora.parameters()), 'lr_scale': a.lora_lr_mult})
            print(json.dumps({'event': 'lm-lora', 'rank': r_, 'linears': len(lora) // 2,
                              'params': sum(p.numel() for p in lora.parameters())}), flush=True)
        if a.rounds != 4:
            R = a.rounds

            def fixed_rounds(core, query, notebook=None, **metadata):
                state = core.begin_latent(query, notebook, **metadata)
                terms = []
                for _ in range(R):
                    state = core.advance_latent(state)
                    terms.extend(block.mlp.aux for block in core.blocks)
                h, q = core.read_latent(state)
                return h, q, torch.stack(terms).mean()
            rt.train_api.fixed4_training = fixed_rounds
        for which, H in (('reader', a.reader_hidden), ('prefix', a.prefix_hidden)):
            if not H:
                continue
            seq = runtime.module_dict(modules)['reader'].proj if which == 'reader' else dec.adapter.project
            i1, i2 = (1, 3) if which == 'reader' else (0, 2)
            l1, l2 = seq[i1], seq[i2]
            old_h = l1.out_features
            if H <= old_h:
                raise SystemExit('--%s-hidden must exceed %d' % (which, old_h))
            g = torch.Generator(device='cpu').manual_seed(1000 + (a.sample_seed or 0))
            n1 = torch.nn.Linear(l1.in_features, H).to(l1.weight.device)
            n2 = torch.nn.Linear(H, l2.out_features).to(l2.weight.device)
            with torch.no_grad():
                bound = 1.0 / math.sqrt(l1.in_features)
                n1.weight.copy_((torch.rand(H, l1.in_features, generator=g) * 2 - 1).mul_(bound))
                n1.bias.copy_((torch.rand(H, generator=g) * 2 - 1).mul_(bound))
                n1.weight[:old_h] = l1.weight
                n1.bias[:old_h] = l1.bias
                n2.weight.zero_()
                n2.weight[:, :old_h] = l2.weight
                n2.bias.copy_(l2.bias)
            swap = {id(l1.weight): n1.weight, id(l1.bias): n1.bias, id(l2.weight): n2.weight, id(l2.bias): n2.bias}
            seq[i1], seq[i2] = n1, n2
            new_named = [(n, swap.get(id(p), p)) for n, p in named]
            opt2 = runtime.make_optimizer(torch, [p for _, p in new_named])
            for (_, p_old), (_, p_new) in zip(named, new_named):
                if p_old is p_new and opt.state.get(p_old):
                    opt2.state[p_new] = opt.state[p_old]
            named, opt = new_named, opt2
            print(json.dumps({'event': which + '-widened', 'from': old_h, 'to': H,
                              'params': sum(p.numel() for p in seq.parameters())}), flush=True)
        if a.copy_path:
            ad = dec.adapter
            emb = lm.get_input_embeddings()
            if (a.back or a.chat or a.two_path or a.no_front) and not a.gen_fix:
                raise SystemExit('--back/--chat/--two-path/--no-front need --gen-fix')
            ad2 = None
            if a.back:  # a second exit (copy of the trained one, fresh Adam state) writing K vectors AFTER the question
                ad2 = copy.deepcopy(ad)
                ad2.prefix_tokens = a.back
                opt.add_param_group({'params': list(ad2.parameters())})
                named = named + [('prefix2.' + n, p) for n, p in ad2.named_parameters()]
                print(json.dumps({'event': 'back-exit', 'vectors': a.back, 'params': sum(p.numel() for p in ad2.parameters())}), flush=True)
            o_train, o_fwd = ad.project_training, ad.forward
            if a.chat:  # native LFM chat layout: <|startoftext|><|im_start|>user\n Q <|im_end|>\n<|im_start|>assistant [back] \n ANSWER <|im_end|>
                CHAT['head'] = list(tokenizer.encode('<|startoftext|><|im_start|>user\n', add_special_tokens=False))
                tail = list(tokenizer.encode('<|im_end|>\n<|im_start|>assistant\n', add_special_tokens=False))
                CHAT['tail'], CHAT['nl'] = tail[:-1], tail[-1]
                dec.bos_id = CHAT['nl']  # the token right before the answer (human_loss and generate put it there)
                print(json.dumps({'event': 'chat-layout', 'head': CHAT['head'], 'tail': CHAT['tail'], 'before_answer': CHAT['nl'],
                                  'decoded': tokenizer.decode(CHAT['head'] + [11111] + CHAT['tail'] + [CHAT['nl']])}), flush=True)

            ptr = None
            if a.pointer:  # allptr exit (reasoner_ptr/real/english/run_english.py): + 8 pointer vectors over prompt embeddings
                g = torch.Generator(device='cpu').manual_seed(2000 + (a.sample_seed or 0))
                ptr = torch.nn.Linear(256, 8)
                with torch.no_grad():
                    bound = 1.0 / math.sqrt(256)
                    ptr.weight.copy_((torch.rand(8, 256, generator=g) * 2 - 1).mul_(bound))
                    ptr.bias.copy_((torch.rand(8, generator=g) * 2 - 1).mul_(bound))
                ptr = ptr.to(cfg['device'])
                opt.add_param_group({'params': list(ptr.parameters())})
                named = named + [('ptr.weight', ptr.weight), ('ptr.bias', ptr.bias)]

            def with_prompt(pref, h, x=None, alone=False):
                with torch.no_grad():
                    if a.chat:
                        q = CP['ids'][:, :-1]  # drop the plain EOS; the chat tail closes the user turn
                        pe = torch.cat([emb(torch.tensor([CHAT['head']], device=q.device)), emb(q),
                                        emb(torch.tensor([CHAT['tail']], device=q.device))], 1).to(pref.dtype)
                    else:
                        pe = emb(CP['ids']).to(pref.dtype)
                    pe_r = pe if alone else append_R(torch, emb, pe)  # --plan-route: ' = value' tokens after the question (pointer keeps the question only)
                if LES['mode'] == 'collect':
                    LES['store'].setdefault(LES['key'], (LES['fam'], pref.detach().clone()))
                elif LES['mode'] == 'family_mean':
                    pref = LES['fmean'][LES['fam']].to(pref.dtype)
                elif LES['mode'] == 'global_mean':
                    pref = LES['gmean'].to(pref.dtype)
                elif LES['mode'] == 'shuffle_same_family':
                    pref = LES['swap'][LES['key']].to(pref.dtype)
                if a.shuffle_pool:
                    prev, SHUF['prev'] = SHUF['prev'], pref.detach()
                    pref = prev if prev is not None else pref * 0
                parts = [] if a.no_front else [pref * 0 if a.zero_pool else pref]
                if ptr is not None:
                    pw = ptr(h.float()).softmax(1)
                    parts.append(torch.einsum('bnk,bnl->bkl', pw, pe))
                back = [type(ad2).project_training(ad2, *x)] if ad2 is not None else []
                if alone:  # two-path loss: the LM sees only the core's vectors, no question words
                    return torch.cat(([pref] if not a.no_front else []) + back, 1)
                return torch.cat(parts + [pe_r] + back, 1)
            ad.project_training = lambda *x, **k: with_prompt(o_train(*x, **k), x[0], x)
            ad.forward = lambda *x, **k: with_prompt(o_fwd(*x, **k), x[0].latent)
            if a.gen_fix:
                # o_fwd (StatePrefix.forward) calls self.project_training, which is the patched instance attribute
                # above, so the old forward appended the prompt (and pointer, zero/shuffle lesions) twice at
                # generation: [pooled][prompt][prompt][BOS]. Training sees [pooled][prompt][BOS]. This makes
                # generation see exactly the training layout.
                ad.forward = lambda p, **k: ad.project_training(p.latent, p.latent_mask, p.answer_mask, p.token_shape)

            def loss_fn(rt_, lm_, dec_, h, mask, target):
                x = (h, torch.ones_like(h, dtype=torch.bool), mask, (1, h.shape[1]))
                prefix = dec_.adapter.project_training(*x)
                per, pred, valid = lm_loss(rt_, lm_, prefix, target, dec_.bos_id, dec_.eos_id)  # human_loss; --plan-talk chain rows: the tool's reply (CP['LM']) is not in the loss
                if a.aux_weight and AUX.get('v') is not None and AUX['v'].requires_grad:
                    per = per + a.aux_weight * AUX['v']
                if a.two_path:
                    alone = with_prompt(o_train(*x), h, x, alone=True)
                    per2 = rt_.human_loss(lm_, alone, target, dec_.bos_id, dec_.eos_id, True, False) if CP.get('LM') is None else \
                        masked_human_loss(rt_, lm_, alone, target, dec_.bos_id, dec_.eos_id, CP['LM'])[0]
                    TWO['ce2'].append(float(per2.detach().mean()))
                    per = per + a.two_path * per2
                ok = (pred == target) & valid
                return per, pred, {'CE': float(per.detach().mean()), 'valid_target_tokens': int(valid.sum()),
                                   'first_token_CE': 0.0, 'EOS_CE': 0.0,
                                   'teacherforced_token_accuracy': float(ok.sum()) / int(valid.sum()),
                                   'teacherforced_exact': bool(ok.sum() == valid.sum())}
            runtime.english_loss = loss_fn
        ctx = type('Ctx', (), {})()
        ctx.lm, ctx.dec, ctx.device = lm, dec, cfg['device']
        dev = load_dev(a.data, a.dev_n)
        rows_all = [json.loads(l) for l in (Path(a.data) / 'train.jsonl').read_text().splitlines()]
        if a.families:
            keep = set(a.families.split(','))
            rows_all = [r for r in rows_all if r['family'] in keep]
            dev = {k: [r for r in json.loads('[' + ','.join(l for l in (Path(a.data) / 'dev' / (k + '.jsonl')).read_text().splitlines()) + ']') if r['family'] in keep][:a.dev_n] for k in DEV if (Path(a.data) / 'dev' / (k + '.jsonl')).exists()}
        if a.dev_kinds:
            dev = {k: v for k, v in dev.items() if k in a.dev_kinds.split(',')}
        stride = max(1, len(rows_all) // max(1, a.updates))
        if a.eval_only:
            rows = []
            if a.sample_seed is not None and a.fixed_rows:  # same draw as the training branch, scored only
                dev['trainfit'] = random.Random('fixed|%d' % a.sample_seed).sample(rows_all, a.fixed_rows)[:a.dev_n]
        elif a.sample_seed is not None and a.fixed_rows:
            rng = random.Random('fixed|%d' % a.sample_seed)
            fixed = rng.sample(rows_all, a.fixed_rows)
            rows = []
            for _ in range(a.passes):
                rows += rng.sample(fixed, len(fixed))
            dev['trainfit'] = fixed[:a.dev_n]
        elif a.sample_seed is not None:
            rows = random.Random('sample|%d' % a.sample_seed).sample(rows_all, min(a.updates, len(rows_all)))
        else:
            rows = rows_all[::stride][:a.updates]
        print(json.dumps({'event': 'skills-start', 'train_rows': len(rows_all), 'used': len(rows), 'stride': stride}), flush=True)
        DR = None
        if a.direct_reader:  # before the planner, so its deep copy of the reader has the new layout
            seen_, feats_ = set(), []
            for r_ in rows:
                if r_['prompt'] in seen_:
                    continue
                seen_.add(r_['prompt'])
                enc_ = encode(tokenizer, r_, torch, cfg['device'])
                if enc_:
                    feats_.append(rt.compare.extract_question_features(lm, enc_[0], enc_[1], 'contextual', torch)[0])
                if len(feats_) == 256:
                    break
            named, DR = direct_reader_swap(torch, runtime.module_dict(modules)['reader'], opt, named, feats_)
            del feats_
            print(json.dumps({'event': 'direct-reader', **DR}), flush=True)
        plan_info = None
        if a.plan_route:  # frozen planner for the chain families, trained first (not in `named`, not in opt, not counted in t0/--minutes)
            import uc_diag_v4 as ud  # its pure helpers only: parse_plan / plan_labels / to_int / plan_exec / reset_fresh
            all_train = rows_all if not a.families else [json.loads(l) for l in (Path(a.data) / 'train.jsonl').read_text().splitlines()]
            chain_rows = [r for r in all_train if r['family'] in CHAIN_FAMS]
            pseed, n_plan = a.sample_seed or 0, min(a.plan_route, len(chain_rows))
            plan_rows = random.Random('plan|%d' % pseed).sample(chain_rows, n_plan)
            print(json.dumps({'event': 'plan-pretrain-start', 'requested': a.plan_route, 'chain_rows_available': len(chain_rows),
                              'rows': n_plan, 'seed': pseed}), flush=True)
            PLAN['pl'], plan_info = train_planner(rt, lm, tokenizer, ud, runtime.module_dict(modules), plan_rows, pseed, cfg['device'],
                                                    cosine=a.plan_cosine)
            PLAN['ud'] = ud
            print(json.dumps({'event': 'plan-pretrain-done', **plan_info}), flush=True)
            if a.plan_talk:
                install_forced_tokens(rt, lm)  # generation: CP['F'] tokens are forced after BOS (no-op while CP['F'] is None)
        FEAT_CACHE, PROF, CE_DUMP = {}, {}, []
        log, curve, t0, done = [], [], time.time(), 0
        base_lr = runtime.ADAM_RECIPE['lr'] * a.lr_mult
        for g in opt.param_groups:
            g['lr'] = base_lr * g.get('lr_scale', 1.0)
        if a.eval_at_start:
            curve.append({'update': 0, **{k: evaluate(rt, ctx, modules, dev[k], tokenizer) for k in ('in_dist', 'trainfit') if k in dev}})
            print(json.dumps({'event': 'skills-eval', **curve[-1]}), flush=True)
        for i, row in enumerate(rows, 1):
            if a.lr_final_mult is not None:
                fin = runtime.ADAM_RECIPE['lr'] * a.lr_final_mult
                cur = fin + 0.5 * (base_lr - fin) * (1 + math.cos(math.pi * (i - 1) / len(rows)))
                for g in opt.param_groups:
                    g['lr'] = cur * g.get('lr_scale', 1.0)
            enc = encode(tokenizer, row, torch, ctx.device)
            if enc is None:
                continue
            ids, mask, labels = enc
            CP['ids'] = ids
            _tp = time.perf_counter() if a.profile_parts else 0.0
            if a.feat_cache and not a.lm_lora:
                _key = ids.detach().cpu().numpy().tobytes() + mask.detach().cpu().numpy().tobytes()
                feats = FEAT_CACHE.get(_key)
                if feats is None:
                    feats = rt.compare.extract_question_features(lm, ids, mask, 'contextual', torch)
                    if len(FEAT_CACHE) < a.feat_cache:
                        FEAT_CACHE[_key] = feats
                    FEAT_CACHE['_miss'] = FEAT_CACHE.get('_miss', 0) + 1
                else:
                    FEAT_CACHE['_hit'] = FEAT_CACHE.get('_hit', 0) + 1
            else:
                feats = rt.compare.extract_question_features(lm, ids, mask, 'contextual', torch)
            if a.profile_parts:
                common.synchronize(torch)
                PROF['features'] = PROF.get('features', 0.0) + time.perf_counter() - _tp
            plan_route_row(rt, tokenizer, row, feats, ids, mask, ctx.device)  # --plan-route: sets CP['R'] (None for non-chain rows)
            labels = talk_train_row(torch, tokenizer, row, labels, ctx.device)  # --plan-talk chain rows: target = call + tool reply (loss-free) + " # answer" from this row's note
            ctx.tokens, ctx.features = {0: (ids, mask, labels)}, {0: feats}
            if a.accum > 1:  # batch a.accum rows per optimizer update (mean loss, one clip at 1.0, one AdamW step)
                parts_ = runtime.module_dict(modules)
                if (i - 1) % a.accum == 0:
                    opt.zero_grad(set_to_none=True)
                h_, _ = runtime.english_graph(rt, parts_['core'], parts_['reader'], feats, mask)
                per_, _, r = runtime.english_loss(rt, lm, dec, h_, mask, labels)
                (per_.mean() / a.accum).backward()
                if i % a.accum == 0 or i == len(rows):
                    torch.nn.utils.clip_grad_norm_([p for _, p in named], 1.0)
                    opt.step()
            else:
                r = trainer.train_step(rt, ctx, modules, named, opt, 0, participation, nonzero,
                                       receipt=(i - 1) % a.receipt_every == 0, prof=PROF if a.profile_parts else None)
            if a.ce_dump and done < a.ce_dump:
                CE_DUMP.append(repr(float(r['CE'])))
            if a.lm_lora and done == 0:
                lg = [(n, p.grad) for n, p in named if n.startswith('lora.') and n.endswith('_A.weight')]
                print(json.dumps({'event': 'lm-lora-first-step', 'A_with_grad': sum(1 for _, g_ in lg if g_ is not None),
                                  'A_total': len(lg)}), flush=True)
            done += 1
            log.append((row['stage'], r['CE'], r['teacherforced_exact']))
            if i % 500 == 0:
                last = log[-500:]
                print(json.dumps({'event': 'skills-progress', 'update': i, 'stage': row['stage'],
                                  'CE': round(sum(x[1] for x in last) / len(last), 4),
                                  'exact': round(sum(x[2] for x in last) / len(last), 3),
                                  **({'CE2': round(sum(TWO['ce2'][-500:]) / len(TWO['ce2'][-500:]), 4)} if TWO['ce2'] else {}),
                                  'minutes': round((time.time() - t0) / 60, 1)}), flush=True)
            if i % a.eval_every == 0:
                curve.append({'update': i, **{k: evaluate(rt, ctx, modules, dev[k], tokenizer) for k in ('in_dist', 'trainfit') if k in dev}})
                print(json.dumps({'event': 'skills-eval', **curve[-1]}), flush=True)
            if (time.time() - t0) / 60 > a.minutes:
                print(json.dumps({'event': 'skills-time-cap', 'update': i}), flush=True)
                break
        if a.profile_parts or a.feat_cache:
            print(json.dumps({'event': 'skills-profile', 'updates': done, 'seconds_by_part': {k: round(v, 3) for k, v in PROF.items()},
                              'feat_cache_hits': FEAT_CACHE.get('_hit', 0), 'feat_cache_misses': FEAT_CACHE.get('_miss', 0),
                              'wall_loop_seconds': round(time.time() - t0, 2)}), flush=True)
        if a.ce_dump:
            Path(a.out, 'ce-first-%d.json' % a.ce_dump).write_text(json.dumps(CE_DUMP))
        final = {k: evaluate(rt, ctx, modules, v, tokenizer) for k, v in dev.items()}
        lesions = None
        if a.final_lesions:  # how much of the score needs this row's own core vectors? (generation, real metric)
            lesions = {}
            for split in ('trainfit', 'in_dist'):
                if split not in dev:
                    continue
                LES['mode'], LES['store'], LES['rstore'], LES['nstore'] = 'collect', {}, {}, {}
                res_ = {'intact': evaluate(rt, ctx, modules, dev[split], tokenizer)}
                byf = {}
                for key_, (f_, v_) in LES['store'].items():
                    byf.setdefault(f_, []).append((key_, v_))
                LES['fmean'] = {f_: torch.stack([v_ for _, v_ in kv]).mean(0) for f_, kv in byf.items()}
                LES['gmean'] = torch.stack([v_ for _, v_ in LES['store'].values()]).mean(0)
                LES['swap'] = {kv[j][0]: kv[(j + 1) % len(kv)][1] for kv in byf.values() for j in range(len(kv))}
                LES['rswap'] = plan_swap_map(LES['rstore'])  # --plan-route: each chain row gets the next same-family row's R
                LES['nswap'] = plan_swap_map(LES['nstore'])  # --plan-talk: ... and the next same-family row's note (R holds the note)
                for mode in ('family_mean', 'shuffle_same_family', 'global_mean') + (('plan_swap',) if a.plan_route else ()) + (('note_drop',) if a.plan_talk else ()):
                    LES['mode'] = mode
                    res_[mode] = evaluate(rt, ctx, modules, dev[split], tokenizer)
                LES['mode'] = None
                lesions[split] = res_
                print(json.dumps({'event': 'final-lesions', 'split': split, **{m: r_['correct'] for m, r_ in res_.items()}}), flush=True)
        ck_sha = None
        if not a.no_checkpoint:
            payload = copy.copy(saved)
            payload.update(runtime.checkpoint_payload(modules, opt, names, participation,
                                                      {'update': runtime.PARENT_UPDATE + done}, common.rng_snapshot(torch)))
            ck = out / 'final-checkpoint.pt'
            torch.save(payload, ck)
            ck_sha = common.digest(ck)
        res = {'updates_done': done, 'rounds': a.rounds, 'pointer': a.pointer, 'reader_hidden': a.reader_hidden or None, 'prefix_hidden': a.prefix_hidden or None, 'zero_pool': a.zero_pool, 'shuffle_pool': a.shuffle_pool, 'lm_lora': a.lm_lora or None, 'lora_lr_mult': a.lora_lr_mult if a.lm_lora else None, 'gen_fix': a.gen_fix, 'steps': a.steps, 'steps_rich': a.steps_rich, 'seq_steps_v2': a.seq_steps_v2, 'answer_only_fams': a.answer_only_fams or None, 'save_texts': a.save_texts, 'back': a.back or None, 'chat': a.chat, 'no_front': a.no_front, 'two_path': a.two_path or None, 'accum': a.accum, 'moe_revive': a.moe_revive or None, 'aux_weight': a.aux_weight or None, 'fresh_adam': a.fresh_adam, 'wd': a.wd or None, 'plan_route': a.plan_route or None, 'plan_talk': a.plan_talk, 'plan_pretrain': plan_info, 'direct_reader': DR, 'sample_seed': a.sample_seed, 'fixed_rows': a.fixed_rows, 'passes': a.passes,
               'families': a.families or None, 'stride': stride, 'parent_seed': a.parent_seed, 'lr_mult': a.lr_mult,
               'dev_n': a.dev_n, 'final_dev': final, 'final_lesions': lesions, 'in_dist_curve': curve, 'parent_path': a.parent_path or None,
               'checkpoint_sha256': ck_sha, 'minutes': round((time.time() - t0) / 60, 1)}
        (out / 'SKILLS-RESULT.json').write_text(json.dumps(res, indent=1))
        print('SKILLS-RESULT ' + json.dumps(res), flush=True)
    finally:
        try:
            BUSY.unlink()
        except OSError:
            pass


if __name__ == '__main__':
    main()
