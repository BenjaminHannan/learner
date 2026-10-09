"""Domain mode (DM-S): a model learns a tool's domain from the tool's help page, by itself.

Design: domain/DESIGN-AND-MARKS-2026-10-09.md, sec. 2 (the steps) and sec. 5 (constants, mix, rules).

  python -m domain.mode --parent CKPT --tool sheet|rpn --out DIR --seed N [--smoke] [--data DIR] [--threads N]

  --data DIR  folder holding train.jsonl (default $CUSTOM_IO_DATA, else custom_io.data.DEFAULT_DATA). Only prompts are read.
  --smoke     64 problems a day, quiz 32, diary 128 + check 64, max 1 night, 20 updates a night. Logged as smoke.

Writes DIR/log.jsonl (one JSON line per decision), DIR/night_K/checkpoint.pt (same format as the parent, loads the same way)
and DIR/summary.json. Never opens the sealed panel or a DEV file: guard() asserts on every path before it is opened.

Deviations from the design text are listed in the report and marked "choice:" in the code.
"""
import argparse
import hashlib
import importlib
import itertools
import json
import math
import os
import random
import re
import subprocess
import time
from collections import Counter

import numpy as np
import torch

from custom_io.data import DEFAULT_DATA, DEV_SPLITS, MAX_ANS, MAX_PROMPT, Dataset, collate, to_device
from custom_io.models import load_model
from custom_io.models.tool import LE, NAMES, entry

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
CONST_PATH = os.path.join(HERE, 'constants.json')
PANEL = '/mnt/project-files/domain-mode/panel'
CELLS_MAX = 10          # operand text: up to 9 digits and a sign (tool.py:84, CELLS = 11 with EOS)
LEARNED = 0.8           # summary only: "kinds learned" (design sec. 2 step 7); not a training constant
SMOKE = dict(day_problems=64, quiz=32, diary=128, check=64, max_nights=1)
SMOKE_UPDATES = 20
ARITH = {'add': '+', 'sub': '-', 'mul': '*', 'div': '/'}
# choice: no text form exists for these calls in progparse (custom_io/models/progparse.py:108-166), so their rows cannot
# be trained. A dated deviation (DESIGN-AND-MARKS addendum A2), logged at the start of every run.
NO_ROW_FORM = frozenset({'mod', 'cmp'})
IDS = itertools.count()  # row ids are unique per process: progparse caches targets by row id (progparse.py:188)


def guard(path):
    """Refuse the sealed panel and every DEV file (checked on the resolved path). Called before each path this module opens.
    Returns the path as given, so logs show the path that was opened."""
    p = os.path.realpath(os.path.expanduser(str(path)))
    assert not (p + os.sep).startswith(PANEL + os.sep), f'refused: sealed panel {p}'
    parts = [s.lower() for s in p.split(os.sep)]
    assert 'dev' not in parts and 'panel' not in parts, f'refused: DEV or panel folder {p}'
    assert os.path.basename(p) not in {s + '.jsonl' for s in DEV_SPLITS}, f'refused: DEV split file {p}'
    return str(path)


def git_info():
    try:
        c = subprocess.run(['git', '-C', REPO, 'rev-parse', 'HEAD'], capture_output=True, text=True, timeout=30).stdout.strip()
        d = subprocess.run(['git', '-C', REPO, 'status', '--porcelain'], capture_output=True, text=True, timeout=30).stdout
        return c, len([x for x in d.splitlines() if x.strip()])
    except Exception as e:  # not fatal: logged as unknown
        return f'unknown ({type(e).__name__})', -1


class Log:
    """DIR/log.jsonl: one JSON line per decision. Refuses an existing log, so two runs never share one."""

    def __init__(self, out):
        os.makedirs(out, exist_ok=True)
        path = os.path.join(out, 'log.jsonl')
        assert not os.path.exists(path), f'{path} exists: give a new --out folder'
        self.f, self.t0 = open(path, 'w'), time.time()

    def write(self, event, **kw):
        rec = dict(event=event, secs=round(time.time() - self.t0, 1), **kw)
        self.f.write(json.dumps(rec, sort_keys=True, default=str) + '\n')
        self.f.flush()

    def __call__(self, event, **kw):
        self.write(event, **kw)
        print(event, json.dumps(kw, sort_keys=True, default=str)[:300], flush=True)


def greedy(m, prompts, bs=64):
    """Greedy answers, calculator on. -> [(calls, answer)]; calls = [(op, a, b, result)] strings (the calculator's replies)."""
    m.eval()
    out = []
    for s in range(0, len(prompts), bs):
        chunk = prompts[s:s + bs]
        ds = Dataset([{'id': f'g{i}', 'prompt': p, 'answer': '', 'accepted': [], 'family': '', 'level': 0}
                      for i, p in enumerate(chunk)], m.vocab, strict=False)
        batch = to_device(collate([ds[i] for i in range(len(chunk))]), 'cpu')
        with torch.no_grad():
            o = m.run(batch)
            ans = m.talk(m.state_of(o), batch)
        out += [([(op, a, b, r) for (t, op, a, b, r) in o['calls'][i]], ans[i]) for i in range(len(chunk))]
    return out


# ---------- problems: the help example with new digits, the tool's answer, the caps ----------

def digit_run(rng, n):
    """A random digit run of length n, no leading zero unless n is 1."""
    if n == 1:
        return str(rng.randrange(10))
    return str(rng.randrange(1, 10)) + ''.join(str(rng.randrange(10)) for _ in range(n - 1))


def draft(tool, example, kind, rng, ctx):
    """One problem from one help example. ctx = dict(vchars, cons, seen, quiz_set). -> (item, None) or (None, reason)."""
    cons = ctx['cons']
    prompt = re.sub(r'\d+', lambda g: digit_run(rng, len(g.group())), example)
    if prompt in ctx['quiz_set']:
        return None, 'quiz_dup'
    if prompt in ctx['seen']:
        return None, 'dup'
    if len(prompt) > MAX_PROMPT:
        return None, 'caps_prompt'
    if not set(prompt) <= ctx['vchars']:
        return None, 'vocab'
    if len(re.findall(r'\d+', prompt)) > cons['max_numbers']:
        return None, 'caps_numbers'
    try:
        res = tool.evaluate(prompt)
    except Exception:  # the tool must answer '?' instead of raising; counted, not hidden
        return None, 'tool_exception'
    value, steps = res['value'], [tuple(s) for s in res['steps']]
    if value == '?' or any(s[3] == '?' for s in steps):
        return None, 'tool_?'
    if any(s[1].startswith('-') or s[2].startswith('-') or s[3].startswith('-') for s in steps):
        return None, 'tool_negative'
    if steps and steps[-1][3] != value:
        return None, 'tool_mismatch'
    if not steps:  # a single-cell range (e.g. A3:A3) has no working to learn from (addendum A5)
        return None, 'no_steps'
    if not value or len(value) > MAX_ANS:
        return None, 'caps_answer'
    if not set(value) <= ctx['vchars']:
        return None, 'vocab'
    if len(steps) > cons['max_calls']:
        return None, 'caps_calls'
    if any(len(s[1]) > CELLS_MAX or len(s[2]) > CELLS_MAX for s in steps):
        return None, 'caps_operand'
    if any(len(f'{s[0]} {s[1]} {s[2]} = {s[3]}') > LE for s in steps):
        return None, 'caps_entry'
    if any(s[0] not in NAMES[1:] for s in steps):
        return None, 'bad_op'
    return dict(kind=kind, prompt=prompt, value=value, steps=steps), None


def make_quiz(tool, kinds, ex, n, rng, ctx, log):
    """256 (or 32 in smoke) problems kept aside, even across kinds. Never trained on."""
    quota = {k: n // len(kinds) + (1 if i < n % len(kinds) else 0) for i, k in enumerate(kinds)}
    items, disc = [], Counter()
    for k in kinds:
        got, tries = 0, 0
        while got < quota[k] and tries < 300 * quota[k] + 300:
            tries += 1
            item, why = draft(tool, ex[k], k, rng, ctx)
            if item is None:
                disc[why] += 1
                continue
            ctx['seen'].add(item['prompt'])
            ctx['quiz_set'].add(item['prompt'])
            items.append(item)
            got += 1
        if got < quota[k]:
            log('quiz_short', kind=k, wanted=quota[k], got=got)
    log('quiz_built', n=len(items), per_kind=dict(Counter(i['kind'] for i in items)), discards=dict(disc), tries=sum(disc.values()) + len(items))
    return items


def make_practice(tool, kinds, ex, share, n, rng, ctx):
    """One day's practice: a kind by the day's mix for each draft, kept if draft() accepts it. Over-draws, capped."""
    items, disc, tries, cap = [], Counter(), 0, 300 * n
    weights = [share[k] for k in kinds]
    while len(items) < n and tries < cap:
        tries += 1
        kind = rng.choices(kinds, weights=weights)[0]
        item, why = draft(tool, ex[kind], kind, rng, ctx)
        if item is None:
            disc[why] += 1
            continue
        ctx['seen'].add(item['prompt'])
        items.append(item)
    return items, disc, tries


# ---------- training rows: the row format of custom_io (progparse) ----------

def step_text(op, a, b, r):
    """One call as a progparse step, or None when that format has no form for it (NO_ROW_FORM): progparse.py:108-166."""
    if op in ARITH:
        return f'{a} {ARITH[op]} {b} = {r}'
    if op == 'min':
        return f'smallest of [{a},{b}]'
    if op == 'max':
        return f'largest of [{a},{b}]'
    return None  # NO_ROW_FORM (choice, addendum A2) and anything else with no text form


def verify(m, row, calls):
    """The targets custom_io would train on (row_gold) must be exactly these calls and tape. -> None, or a reason."""
    try:
        ops, opd, tape, md, word = m.row_gold(row)
    except Exception as e:
        return 'gold_error_' + type(e).__name__
    if [NAMES[o] for o in ops] != [c[0] for c in calls]:
        return 'gold_ops'
    if [tuple(x) for x in opd] != [(c[1], c[2]) for c in calls]:
        return 'gold_operands'
    if list(tape[:len(calls)]) != [entry(*c) for c in calls]:
        return 'gold_tape'
    return None


def make_row(m, fam, prompt, answer, calls, cons, source):
    """A training row whose targets are exactly `calls` then `answer`. -> (row, None) or (None, reason)."""
    if not answer or len(answer) > MAX_ANS:
        return None, 'answer_len'
    if not calls:  # answer-only rows (no tool check, no worked steps) never train (addendum A5)
        return None, 'zero_steps'
    if len(calls) > cons['max_calls']:
        return None, 'caps_calls'
    if any(c[3] == '?' or c[3].startswith('-') or c[1].startswith('-') or c[2].startswith('-') for c in calls):
        return None, 'calc_?_or_negative'
    if calls and calls[-1][3] != answer:
        return None, 'final_mismatch'
    steps = []
    for c in calls:
        s = step_text(*c)
        if s is None:
            return None, 'no_row_form_' + c[0]
        steps.append(s)
    row = dict(id=f'dm{next(IDS)}', family=fam, prompt=prompt, answer=answer, accepted=[answer],
               steps=steps, level=len(steps), stage=len(steps), source=source)
    why = verify(m, row, calls)
    if why:
        return None, why
    return row, None


def try_day(m, tool, items, kinds, cons, log, day, write_row):
    """Greedy try on the day's problems. Correct: the model's own calls (else the tool's steps). Wrong: the tool's steps."""
    fam = 'domain_' + tool.NAME  # the model never sees the family; it is for the audit
    res = greedy(m, [it['prompt'] for it in items])
    rows, st = [], {k: Counter() for k in kinds}
    for it, (calls, ans) in zip(items, res):
        k = it['kind']
        ok = ans == it['value']
        st[k]['correct' if ok else 'wrong'] += 1
        row, why = None, None
        if ok and [tuple(c) for c in calls] == [tuple(s) for s in it['steps']]:
            # choice: an own try is kept only when its calls are the tool's working (addendum A6). Agreement of the
            # final answer alone let wrong workings train (a wrong cell, a missing step).
            row, why = make_row(m, fam, it['prompt'], it['value'], calls, cons, 'own')
            if row is None:
                st[k]['own_refused_' + why] += 1
        elif ok:
            st[k]['own_not_tool_working'] += 1
        if row is None:
            row, why = make_row(m, fam, it['prompt'], it['value'], it['steps'], cons, 'tool')
            if row is None:
                st[k]['dropped_' + why] += 1
                continue
        st[k][row['source']] += 1
        rows.append(row)
        write_row(day=day, kind=k, id=row['id'], source=row['source'], prompt=row['prompt'], answer=row['answer'], steps=row['steps'])
    log('try', day=day, n=len(items), rows=len(rows), per_kind={k: dict(v) for k, v in st.items()})
    return rows


def build_diary(m, pool, cons, ctx, log, write_row):
    """Forgetting check (pre-mode answers to the first check prompts of the pool) and the self-replay diary (own calls
    and own answer on the rest of the pool, pre-mode). The check set is taken first: if the diary refuses many answers
    (no-calls rows, addendum A5), the check set must not be starved, or agreement would read 0 and undo every night."""
    n_d, n_c = cons['diary'], cons['check']
    check = [dict(prompt=p, pre=ans) for p, (_, ans) in zip(pool[:n_c], greedy(m, pool[:n_c]))]
    diary, disc, pos = [], Counter(), n_c
    while len(diary) < n_d and pos < len(pool):
        chunk = pool[pos:pos + 256]
        pos += len(chunk)
        for p, (calls, ans) in zip(chunk, greedy(m, chunk)):
            if not ans or not set(ans) <= ctx['vchars']:
                disc['answer_empty_or_vocab'] += 1
                continue
            row, why = make_row(m, 'diary', p, ans, calls, cons, 'diary')
            if row is None:
                disc[why] += 1
                continue
            diary.append(row)
            write_row(day=0, kind='diary', id=row['id'], source='diary', prompt=p, answer=ans, steps=row['steps'])
            if len(diary) == n_d:
                break
    log('diary', n=len(diary), check=len(check), scanned=pos, discards=dict(disc),
        calls_hist={str(k): v for k, v in sorted(Counter(len(r['steps']) for r in diary).items())})
    return diary, check


# ---------- quiz, check, night ----------

def quiz_eval(m, quiz, kinds):
    """Greedy quiz accuracy (exact answer) per kind, and pooled. Fractions."""
    res = greedy(m, [q['prompt'] for q in quiz])
    hits = [int(a == q['value']) for (_, a), q in zip(res, quiz)]
    per = {}
    for k in kinds:
        h = [x for x, q in zip(hits, quiz) if q['kind'] == k]
        per[k] = sum(h) / len(h) if h else 0.0
    return per, sum(hits) / max(len(hits), 1)


def check_agree(m, check):
    """Percent of check prompts answered the same as before the mode (pre-mode answers)."""
    res = greedy(m, [c['prompt'] for c in check])
    return 100.0 * sum(a == c['pre'] for (_, a), c in zip(res, check)) / max(len(check), 1)


def make_opt(m, lr):
    """AdamW as custom_io training runs it (train.py:146-151): betas (0.9, 0.95); weight decay 0.1 on matrices, 0 on
    biases, norms and embedding tables."""
    emb = {id(mod.weight) for mod in m.modules() if isinstance(mod, torch.nn.Embedding)}
    decay = [p for p in m.parameters() if p.requires_grad and p.ndim >= 2 and id(p) not in emb]
    no_decay = [p for p in m.parameters() if p.requires_grad and (p.ndim < 2 or id(p) in emb)]
    return torch.optim.AdamW([{'params': decay, 'weight_decay': 0.1}, {'params': no_decay, 'weight_decay': 0.0}],
                             lr=lr, betas=(0.9, 0.95))


def train_night(m, new, diary, updates, cons, seed):
    """Each batch: half new rows (cycling through reshuffles, so each is seen about visits_per_new_row times), half
    self-replay rows drawn from the diary. Grad clip 1.0 as in custom_io training (train.py:172). -> per-update losses."""
    assert diary, 'empty diary: no replay half'
    nb_new = int(round(cons['batch'] * (1 - cons['replay_share'])))
    nb_rep = cons['batch'] - nb_new
    ds_new, ds_rep = Dataset(new, m.vocab), Dataset(diary, m.vocab)
    rng = np.random.RandomState(seed)
    torch.manual_seed(seed)  # ans_drill draws from the model's own RNG in train mode (tool.py:151)
    opt = make_opt(m, cons['lr'])
    order, pos, losses = np.array([], dtype=int), 0, []
    m.train()
    for _ in range(updates):
        ni = []
        while len(ni) < nb_new:
            if pos >= len(order):
                order, pos = rng.permutation(len(new)), 0
            take = min(nb_new - len(ni), len(order) - pos)
            ni += [int(i) for i in order[pos:pos + take]]
            pos += take
        ri = [int(j) for j in rng.randint(0, len(diary), size=nb_rep)]
        b = to_device(collate([ds_new[i] for i in ni] + [ds_rep[j] for j in ri]), 'cpu')
        out = m.loss(b)
        loss = out[0] if isinstance(out, tuple) else out
        loss.backward()
        torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0)
        opt.step()
        opt.zero_grad(set_to_none=True)
        losses.append(float(loss.detach()))
    m.eval()
    return losses


def make_mix(kinds, hist_k, night, cons):
    """Design sec. 5 step 5. progress = |quiz now - quiz progress_window_days nights ago| (0 without that history).
    Each kind: explore/K, plus (1 - explore) in proportion to progress, over kinds not yet mastered. Mastered kinds get only
    the explore share. All zero progress -> even. Renormalised to sum 1."""
    K, w, ex, mast = len(kinds), cons['progress_window_days'], cons['explore'], cons['mastered']
    now = hist_k[night]
    prog = {k: abs(now[k] - hist_k[night - w][k]) if night - w >= 0 else 0.0 for k in kinds}
    active = [k for k in kinds if now[k] < mast]
    share = {k: ex / K for k in kinds}
    if active:
        tot = sum(prog[k] for k in active)
        for k in active:
            share[k] += (1 - ex) * (prog[k] / tot if tot > 0 else 1 / len(active))
    else:
        share = {k: 1 / K for k in kinds}
    s = sum(share.values())
    return {k: share[k] / s for k in kinds}, prog


def save_ckpt(ck, m, path):
    """Same keys as the parent's checkpoint (train.py:201): model replaced, the rest copied, so load_model reads it the same way."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    out = dict(ck)
    out['model'] = {k: v.detach().clone() for k, v in m.state_dict().items()}
    torch.save(out, path)


def parse_args(argv=None):
    a = argparse.ArgumentParser(description='Domain mode (DM-S): learn a help-page tool by itself.')
    a.add_argument('--parent', required=True, help='parent checkpoint.pt (T1SDR)')
    a.add_argument('--tool', required=True, choices=['sheet', 'rpn'])
    a.add_argument('--out', required=True, help='new folder for log.jsonl, night_K/, summary.json')
    a.add_argument('--seed', type=int, required=True)
    a.add_argument('--smoke', action='store_true')
    a.add_argument('--data', default=os.environ.get('CUSTOM_IO_DATA', DEFAULT_DATA), help='folder with train.jsonl')
    a.add_argument('--threads', type=int, default=4)
    a.add_argument('--even-mix', action='store_true',
                   help='control arm for addendum A8 R1 (not the deployed mode): practice spread evenly every day')
    a.add_argument('--fixed-nights', type=int, default=None,
                   help='control arm only: run exactly this many nights (the mode run\'s own stop night), no stop rule')
    return a.parse_args(argv)


def main(argv=None):
    a = parse_args(argv)
    torch.set_num_threads(a.threads)
    T, t_run = Counter(), time.time()
    raw = open(CONST_PATH, 'rb').read()
    csha = hashlib.sha256(raw).hexdigest()
    cons = json.loads(raw)
    if a.smoke:
        cons.update(SMOKE)
    if a.fixed_nights:
        assert a.even_mix, '--fixed-nights is for the even-mix control only'
        cons['max_nights'] = max(cons['max_nights'], a.fixed_nights)
    commit, dirty = git_info()
    log = Log(a.out)
    parent = guard(a.parent)
    log('start', parent=parent, tool=a.tool, seed=a.seed, smoke=a.smoke, constants_sha256=csha, git_commit=commit,
        git_dirty_files=dirty, constants=cons, smoke_updates=SMOKE_UPDATES if a.smoke else None, data=a.data,
        even_mix_control=a.even_mix, fixed_nights_control=a.fixed_nights)

    tool = importlib.import_module(f'domain.tools.{a.tool}')
    assert tool.NAME == a.tool, (tool.NAME, a.tool)
    helps = tool.help()
    kinds = [h['kind'] for h in helps]
    assert len(set(kinds)) == len(kinds), 'one help example per kind'
    ex = {h['kind']: h['prompt'] for h in helps}
    log('help', kinds=kinds, examples=ex)
    # choice (dated deviation A2): these calls have no row form, so their rows never train
    log('deviation', id='A2', no_row_form_ops=sorted(NO_ROW_FORM))

    torch.manual_seed(a.seed)
    ck = torch.load(parent, map_location='cpu', weights_only=True)
    torch.manual_seed(a.seed)  # the model's ans_drill RNG is seeded at construction (tool.py:151)
    m = load_model(parent).eval()
    ctx = dict(vchars=set(ck['chars']), cons=cons, seen=set(), quiz_set=set())
    write_row = lambda **kw: log.write('row', **kw)

    # step 1: diary (self-replay) and check set, from TRAIN prompts only
    t = time.time()
    train = guard(os.path.join(a.data, 'train.jsonl'))
    pool = []
    with open(train) as f:
        for line in f:
            p = json.loads(line)['prompt']
            if len(p) <= MAX_PROMPT and set(p) <= ctx['vchars']:
                pool.append(p)
    pool = list(dict.fromkeys(pool))
    random.Random(f'{a.seed}-diary').shuffle(pool)
    diary, check = build_diary(m, pool, cons, ctx, log, write_row)
    T['diary'] += time.time() - t
    assert len(diary) > 0, 'no diary rows'
    assert check, 'empty check set: agreement would read 0 and every night would be undone'

    # step 2 (day 1 part): the quiz first, then the practice
    t = time.time()
    quiz = make_quiz(tool, kinds, ex, cons['quiz'], random.Random(f'{a.seed}-quiz'), ctx, log)
    T['quiz_make'] += time.time() - t

    t = time.time()
    per, pooled = quiz_eval(m, quiz, kinds)
    T['quiz'] += time.time() - t
    hist_k, hist_p = [per], [pooled]
    log('quiz', when='before_night_1', pooled=round(100 * pooled, 2), per_kind={k: round(v, 4) for k, v in per.items()})

    share = {k: 1 / len(kinds) for k in kinds}   # day 1: even (no history yet)
    prog = {k: 0.0 for k in kinds}
    visits, undo_prev, stop, night, last_ck = cons['visits_per_new_row'], False, None, 0, None
    for night in range(1, cons['max_nights'] + 1):
        # step 2: practice for this day, by the day's mix
        t = time.time()
        items, disc, tries = make_practice(tool, kinds, ex, share, cons['day_problems'], random.Random(f'{a.seed}-day-{night}'), ctx)
        T['practice'] += time.time() - t
        log('practice', day=night, n=len(items), tries=tries, share={k: round(v, 4) for k, v in share.items()},
            progress={k: round(v, 4) for k, v in prog.items()}, kept=dict(Counter(i['kind'] for i in items)), discards=dict(disc))
        if len(items) < cons['day_problems']:
            log('practice_short', day=night, n=len(items), wanted=cons['day_problems'])

        # step 3: try
        t = time.time()
        new = try_day(m, tool, items, kinds, cons, log, night, write_row)
        T['try'] += time.time() - t

        # step 6: night (undo of the previous night halves this one's visits)
        n_new = len(new)
        vis = visits / 2 if undo_prev else visits
        if a.smoke:
            updates = SMOKE_UPDATES if n_new else 0
        else:
            updates = math.ceil(vis * n_new / (cons['batch'] * (1 - cons['replay_share']))) if n_new else 0
        log('night_plan', night=night, new_rows=n_new, visits_per_new_row=vis, updates=updates, halved_after_undo=undo_prev)
        snap = {k: v.detach().clone() for k, v in m.state_dict().items()}
        # step 7: the same check prompts before and after this night; undo if agreement fell more than
        # undo_drop_points. choice: the test is per night (design step 6: "before and after each night"), not against
        # 100, so a night's drift is not counted again on the next night (addendum A4).
        t = time.time()
        before = check_agree(m, check)
        T['check'] += time.time() - t
        t = time.time()
        losses = train_night(m, new, diary, updates, cons, seed=a.seed * 1000 + night) if updates else []
        T['train'] += time.time() - t
        t = time.time()
        agree = check_agree(m, check)
        T['check'] += time.time() - t
        drop = before - agree
        undo = drop > cons['undo_drop_points']
        if undo:
            m.load_state_dict(snap)
            m.eval()
        undo_prev = undo
        log('check', night=night, agreement_before=round(before, 2), agreement=round(agree, 2), drop=round(drop, 2),
            undo=undo, rows_dropped=n_new if undo else 0)

        t = time.time()
        path = os.path.join(a.out, f'night_{night}', 'checkpoint.pt')
        save_ckpt(ck, m, path)
        T['save'] += time.time() - t
        last_ck = path

        # step 4: quiz after this night (= before the next one)
        t = time.time()
        per, pooled = quiz_eval(m, quiz, kinds)
        T['quiz'] += time.time() - t
        hist_k.append(per)
        hist_p.append(pooled)
        log('night', night=night, updates=updates, loss_first10=round(float(np.mean(losses[:10])), 4) if losses else None,
            loss_last10=round(float(np.mean(losses[-10:])), 4) if losses else None, undone=undo, checkpoint=path,
            quiz_pooled=round(100 * pooled, 2), quiz_per_kind={k: round(v, 4) for k, v in per.items()})

        # step 8: stop rules
        mastered_all = all(per[k] >= cons['mastered'] for k in kinds)
        rise = (hist_p[night] - hist_p[night - 2]) * 100 if night >= 2 else None  # choice: the stop window = progress_window_days
        if a.fixed_nights:   # A8 R1 control: same number of nights as the mode run chose
            stop = 'fixed_nights_control' if night >= a.fixed_nights else None
        elif mastered_all:
            stop = 'all_kinds_mastered'
        elif rise is not None and rise < cons['stop_min_rise_points']:
            stop = 'quiz_rise_below_%g_over_2_nights' % cons['stop_min_rise_points']
        elif night == cons['max_nights']:
            stop = 'max_nights'
        log('stop_check', night=night, rise_over_2_nights_points=None if rise is None else round(rise, 3),
            mastered_all=mastered_all, stop=stop)
        if stop:
            break
        share, prog = make_mix(kinds, hist_k, night, cons)
        if a.even_mix:   # A8 R1 control: same nights and rows, no picking
            share = {k: 1 / len(kinds) for k in kinds}
        log('mix', for_day=night + 1, share={k: round(v, 4) for k, v in share.items()}, progress={k: round(v, 4) for k, v in prog.items()})

    final = hist_k[-1]
    summary = dict(parent=parent, tool=a.tool, seed=a.seed, smoke=a.smoke, even_mix_control=a.even_mix, nights_run=night, stop_reason=stop,
                   quiz_pooled_history=[round(100 * p, 2) for p in hist_p],
                   quiz_per_kind_history=[{k: round(v, 4) for k, v in h.items()} for h in hist_k],
                   quiz_per_kind_final={k: round(v, 4) for k, v in final.items()},
                   kinds_learned=[k for k in kinds if final[k] >= LEARNED],
                   kinds_not_learned=[k for k in kinds if final[k] < LEARNED],
                   final_checkpoint=last_ck, constants_sha256=csha, git_commit=commit,
                   seconds={k: round(v, 1) for k, v in T.items()}, total_seconds=round(time.time() - t_run, 1))
    with open(os.path.join(a.out, 'summary.json'), 'w') as f:
        json.dump(summary, f, indent=1)
    log('done', nights_run=night, stop_reason=stop, final_checkpoint=last_ck, total_seconds=summary['total_seconds'])


if __name__ == '__main__':
    main()
