"""English question-answering data and scorer for Test B1 (design/B1-students.md).
Rows = one per (example, panel source_text / paraphrase, question): prompt = panel + ' ' + question. en_norm is the round-6 scorer's norm;
taught_answer / atype read the prompt's word tokens (data.word_spans). `python -m custom_io.english build --teach F --gen F --out DIR --eval DIR`
writes DIR/teach and DIR/gen (train.jsonl, dev/in_dist.jsonl, charvocab.json, MANIFEST.json), refusing on any eval-passage overlap and
cutting the bigger arm to the other's row count; eval_english(...) is what train.py --english-eval stores as result['english']."""
import argparse, collections, contextlib, hashlib, json, os, re, sys, unicodedata
import numpy as np
import torch
from custom_io.data import ASCII, MAX_PROMPT, CharVocab, Dataset, collate, to_device, word_spans
from custom_io.evalx import donor_eval, donor_pairs, evaluate

SPAN_MAX, W_MAX = 12, 64                # = ledger span_max and models.progparse.W_MAX
MAX_TAUGHT = 32
PANELS = ('source_text', 'paraphrase')
EVAL_FILES = {'fresh': 'FRESH-EN-R3.json', 'new_r5': 'NEW-KINDS-R5.json', 'new_r6': 'NEW-KINDS2-R6.json', 'gen_heldout': 'GEN-HELDOUT-R4.json'}
GEN_LABEL = "generator kinds, the GEN arm's own distribution"
STOP = set('a an the and or of to in on at by for with from as is was were are be been it its this that these those he she they his her '
           'their him them who whom what which when where did do does not no yes than then there into onto over under after before'.split())
_TRAIL, _PUNCT = re.compile(r'[.!?,;:]+$'), '.!?,;:'
_CLEAN = {ord('’'): "'", ord('‘'): "'", ord('“'): '"', ord('”'): '"', ord('–'): '-', ord('—'): '-', 0xa0: ' '}


def en_norm(s):
    """Round-6 norm: NFC, lower-case, curly single quotes -> ', strip, collapse whitespace, strip trailing [.!?,;:]+, strip."""
    s = unicodedata.normalize('NFC', s).lower().replace('’', "'").replace('‘', "'").strip()
    return _TRAIL.sub('', re.sub(r'\s+', ' ', s)).strip()


def clean(s):
    """Training-data character clean-up: curly quotes -> straight, en/em dash -> '-', no-break space -> space, then NFC."""
    return unicodedata.normalize('NFC', s.translate(_CLEAN))


def _runs(prompt, ws, tn, span_max, w_max):
    n, out = min(len(ws), w_max), []
    if not tn:
        return out
    fast = prompt.isascii() and tn.isascii()
    if fast:                                # ascii: first char must agree and the text can only grow past the target
        low, sq = prompt.lower(), len(''.join(tn.split()))
    for s in range(n):
        a = ws[s][0]
        if fast and low[a] != tn[0]:
            continue
        for e in range(s, min(n, s + span_max)):
            text = prompt[a:ws[e][1]]
            if fast and len(''.join(text.rstrip(_PUNCT).split())) > sq:
                break
            if en_norm(text) == tn:
                out.append((s, e))
    return out


def word_runs(prompt, target_norm, span_max=SPAN_MAX, w_max=W_MAX):
    """Every (s, e) word-token pair (data.word_spans, first w_max tokens), s <= e < s + span_max, with
    en_norm(prompt[ws[s]:we[e]]) == target_norm; earliest start first (then shortest)."""
    return _runs(prompt, word_spans(prompt), target_norm, span_max, w_max)


def _first_run(prompt, canonical, accepted):
    """-> (candidate string, (s, e)) for the first of [canonical] + accepted whose norm is a word-token run (earliest start), else None."""
    ws = word_spans(prompt)
    for a in [canonical] + list(accepted):
        r = _runs(prompt, ws, en_norm(a), 10 ** 6, 10 ** 6)
        if r:
            return a, r[0]
    return None


def taught_answer(prompt, canonical, accepted_answers):
    """The one string both students learn: the canonical answer if it is yes / no; else the first of [canonical] + accepted whose
    norm equals a run of the prompt's word tokens; else the canonical answer."""
    if en_norm(canonical) in ('yes', 'no'):
        return canonical
    f = _first_run(prompt, canonical, accepted_answers)
    return f[0] if f else canonical


def atype(prompt, canonical, accepted_answers):
    """Reporting only: yes_no / span1 (the earliest run is one token) / spanN / nonspan."""
    if en_norm(canonical) in ('yes', 'no'):
        return 'yes_no'
    f = _first_run(prompt, canonical, accepted_answers)
    return 'nonspan' if f is None else 'span1' if f[1][0] == f[1][1] else 'spanN'


def load_examples(path):
    """A {'examples': [...]} JSON file, a JSON list, or JSONL (one example per line)."""
    text = open(path, encoding='utf-8').read()
    try:
        d = json.loads(text)
    except json.JSONDecodeError:
        return [json.loads(l) for l in text.splitlines() if l.strip()]
    return d['examples'] if isinstance(d, dict) and 'examples' in d else d if isinstance(d, list) else [d]


def clean_example(e):
    q = [dict(x, question=clean(x['question']), canonical_answer=clean(x['canonical_answer']),
              accepted_answers=[clean(a) for a in x.get('accepted_answers', [])]) for x in e['questions']]
    return dict(e, source_text=clean(e['source_text']), paraphrase=clean(e['paraphrase']), questions=q)


def qa_rows(examples):
    """Choice-1 rows in rows_of order (example, panel source_text then paraphrase, question). answer = the taught string, canonical = the
    canonical answer, accepted = [canonical] + accepted_answers (raw, de-duplicated, order kept), ex = the example id."""
    out = []
    for e in examples:
        for panel in PANELS:
            for qi, q in enumerate(e['questions']):
                prompt, can = e[panel] + ' ' + q['question'], q['canonical_answer']
                acc = list(dict.fromkeys([can] + list(q.get('accepted_answers', []))))
                out.append(dict(id=f"{e['id']}-{panel}-q{qi}", prompt=prompt, answer=taught_answer(prompt, can, acc), canonical=can, accepted=acc,
                                family=e['family'], type=q.get('type', ''), panel=panel, level=0, atype=atype(prompt, can, acc), ex=e['id']))
    return out


def eval_examples(eval_dir):
    return {k: load_examples(os.path.join(eval_dir, f)) for k, f in EVAL_FILES.items()}


def eval_sets(eval_dir):
    """-> {'fresh', 'new_r5', 'new_r6', 'gen_heldout', 'new_pooled' (= new_r5 + new_r6)} rows (192 each, 384 pooled)."""
    s = {k: qa_rows(v) for k, v in eval_examples(eval_dir).items()}
    s['new_pooled'] = s['new_r5'] + s['new_r6']
    return s


# ---- the donor lesion (choice 9) ----------------------------------------------------------------------------------
def _gives(ri, rj, runs_j):
    """True if donor j's span positions, read on row i's prompt, give text in i's accepted set."""
    ws, acc = word_spans(ri['prompt'])[:W_MAX], {en_norm(a) for a in ri['accepted']}
    return any(e < len(ws) and en_norm(ri['prompt'][ws[s][0]:ws[e][1]]) in acc for s, e in runs_j)


def _taught_runs(r):
    return [] if en_norm(r['answer']) in ('yes', 'no') else word_runs(r['prompt'], en_norm(r['answer']))


def judged_pairs(rows, seed=0):
    """-> ([(i, j)], n_skipped): donor j of the same kind AND question type, canonical answer not in i's accepted set, and whose taught-answer
    span positions never give an accepted answer when read on i's prompt. Seeded, rows in order; a row with no such donor is skipped."""
    rng, grp, pairs = np.random.RandomState(seed), {}, []
    for i, r in enumerate(rows):
        grp.setdefault((r['family'], r['type']), []).append(i)
    runs = [_taught_runs(r) for r in rows]
    for i, r in enumerate(rows):
        acc = {en_norm(a) for a in r['accepted']}
        cand = [j for j in grp[(r['family'], r['type'])] if en_norm(rows[j].get('canonical', rows[j]['answer'])) not in acc and not _gives(r, rows[j], runs[j])]
        if cand:
            pairs.append((i, cand[rng.randint(len(cand))]))
    return pairs, len(rows) - len(pairs)


def _pct(c, n):
    return 100 * c / n if n else 0.0


def _pair_numbers(rows, pairs, skipped, preds, intact):
    """Everything read from a pairing and the predictions {id: [donor id, pred]}."""
    n = len(pairs)
    byid = {r['id']: r for r in rows}
    hit = dm = pm = npos = pc = good = ngood = 0
    fam, aty = {}, {}
    for i, j in pairs:
        ri, rj = rows[i], rows[j]
        p = preds[ri['id']][1]
        h = en_norm(p) in {en_norm(a) for a in ri['accepted']}
        hit += h
        dm += en_norm(p) in {en_norm(a) for a in rj['accepted']}
        runs = _taught_runs(rj)
        pc += _gives(ri, rj, runs)
        if runs:
            ws, (s, e) = word_spans(ri['prompt'])[:W_MAX], runs[0]
            npos += 1
            pm += e < len(ws) and en_norm(ri['prompt'][ws[s][0]:ws[e][1]]) == en_norm(p)
        if intact is not None and intact.get(ri['id']):
            ngood += 1
            good += h
        for d, k in ((fam, ri['family']), (aty, ri.get('atype', '?'))):
            c = d.setdefault(k, {'correct': 0, 'n': 0})
            c['correct'] += h
            c['n'] += 1
    for d in (fam, aty):
        for c in d.values():
            c['exact'] = _pct(c['correct'], c['n'])
    return dict(exact=_pct(hit, n), correct=int(hit), n=n, skipped=skipped, donor_match=_pct(dm, n), pos_coincide=_pct(pc, n),
                donor_position_match=_pct(pm, npos), donor_position_n=npos, exact_given_intact_right=dict(exact=_pct(good, ngood), n=ngood),
                by_family=fam, by_atype=aty)


# ---- scoring ------------------------------------------------------------------------------------------------------
def _tally(rows, hits, key):
    d = {}
    for r, h in zip(rows, hits):
        c = d.setdefault(r.get(key, '?'), {'correct': 0, 'n': 0})
        c['correct'] += h
        c['n'] += 1
    for c in d.values():
        c['exact'] = _pct(c['correct'], c['n'])
    return d


def score(rows, preds):
    """-> {'exact' (%), 'correct', 'n', 'by_family', 'by_type', 'by_atype', 'by_panel'}; an empty set is {'n': 0}."""
    if not rows:
        return {'n': 0}
    hits = [int(en_norm(preds[r['id']]) in {en_norm(a) for a in r['accepted']}) for r in rows]
    return dict(exact=_pct(sum(hits), len(rows)), correct=sum(hits), n=len(rows),
                **{f'by_{k}': _tally(rows, hits, k) for k in ('family', 'type', 'atype', 'panel')})


def _reach(model):
    """row -> can the talker emit it at all? B2: a word-token span of the prompt, a number in the prompt, or an accepted answer of
    <= 8 chars; plain_tf: an accepted answer of <= max_ans (32) chars."""
    if not model.supports_donor():
        k = getattr(model, 'max_ans', 8)
        return lambda r: any(len(a) <= k for a in r['accepted'])
    def f(r):
        nums = {int(x) for x in re.findall(r'\d+', r['prompt'])[:16]}
        if any(re.fullmatch(r'-?\d+', a) and str(int(a)) == a and int(a) in nums for a in r['accepted']):
            return True
        return any(word_runs(r['prompt'], en_norm(a)) for a in r['accepted']) or any(len(a) <= 8 for a in r['accepted'])
    return f


@torch.no_grad()
def _gen_modes(model, rows, device, batch_size, amp, loops):
    """Ledger.state(loops) + talk(return_modes=True) on every row -> ({id: pred}, [decoded mode per row, rows order])."""
    was = model.training
    model.eval()
    ds = Dataset(rows, model.vocab, strict=False)
    order = sorted(range(len(rows)), key=lambda i: len(rows[i]['prompt']))
    preds, modes = [None] * len(rows), [None] * len(rows)
    for s in range(0, len(order), batch_size):
        ids = order[s:s + batch_size]
        b = to_device(collate([ds[i] for i in ids]), device)
        with amp():
            out, md = model.talk(model.state(b, loops=loops), b, return_modes=True)
        for i, p, m in zip(ids, out, md):
            preds[i], modes[i] = p, m
    model.train(was)
    return {r['id']: p for r, p in zip(rows, preds)}, modes


def eval_english(model, eval_dir, heldout_rows, device, batch_size=128, amp=contextlib.nullcontext, log=None):
    """Section-1 eval -> JSON-able dict: intact exact on fresh / new_r5 / new_r6 / new_pooled / gen_heldout / in_dist_heldout (each score() +
    'reachable'); 'lesions' {new_pooled|fresh: {'donor' (choice 9 and its read-only numbers, 'plain' = the same-kind pairing), 'loops:0'
    (+ 'modes' NUM / span / GEN for a Ledger, 'question-blind talker'), every non-loops name in model.LESIONS}}; 'preds' and 'donor_preds'
    ({set: {id: pred}} / {set: {id: [donor id, pred]}}) for intact new_pooled and fresh. log(dict) is called once per set and lesion."""
    sets = eval_sets(eval_dir)
    sets['in_dist_heldout'] = list(heldout_rows)
    reach = _reach(model)
    note = lambda **kw: log(kw) if log else None
    def run(rows, lesion=None):
        with amp():
            return evaluate(model, rows, batch_size, device, lesion, return_preds=True, norm=en_norm)['preds']
    res, preds = {'intact': {}, 'lesions': {}, 'preds': {}, 'donor_preds': {}}, {}
    for k in ('fresh', 'new_pooled', 'gen_heldout', 'in_dist_heldout'):
        if sets[k]:
            preds[k] = run(sets[k])
    for k in ('fresh', 'new_r5', 'new_r6', 'new_pooled', 'gen_heldout', 'in_dist_heldout'):
        rows = sets[k]
        if not rows:
            res['intact'][k] = {'n': 0}
        else:
            p = preds['new_pooled' if k in ('new_r5', 'new_r6') else k]
            res['intact'][k] = dict(score(rows, p), reachable=dict(zip(('n', 'share'), (lambda c: (c, _pct(c, len(rows))))(sum(map(reach, rows))))))
            if k == 'gen_heldout':
                res['intact'][k]['label'] = GEN_LABEL
        note(event='eval', set=k, lesion=None, exact=res['intact'][k].get('exact'), n=res['intact'][k]['n'])
    res['preds'] = {k: preds[k] for k in ('new_pooled', 'fresh') if k in preds}
    for k in ('new_pooled', 'fresh'):
        rows, les = sets[k], {}
        intact = {r['id']: en_norm(preds[k][r['id']]) in {en_norm(a) for a in r['accepted']} for r in rows}
        if model.supports_donor():
            jp, sk = judged_pairs(rows)
            with amp():
                d = donor_eval(model, rows, batch_size, device, norm=en_norm, pairs=(jp, sk), return_preds=True)
            res['donor_preds'][k] = d['preds']
            les['donor'] = _pair_numbers(rows, jp, sk, d['preds'], intact)
            pp_, psk = donor_pairs(rows, 0, en_norm)
            with amp():
                dp = donor_eval(model, rows, batch_size, device, norm=en_norm, pairs=(pp_, psk), return_preds=True)
            les['donor']['plain'] = {x: v for x, v in _pair_numbers(rows, pp_, psk, dp['preds'], None).items()
                                     if x in ('exact', 'n', 'skipped', 'donor_match', 'pos_coincide', 'donor_position_match')}
            note(event='eval', set=k, lesion='donor', exact=les['donor']['exact'], n=les['donor']['n'], skipped=sk)
        if getattr(model, 'n_loops', 1) > 1:
            if type(model).__name__ == 'Ledger':
                p0, md = _gen_modes(model, rows, device, batch_size, amp, 0)
                les['loops:0'] = dict(score(rows, p0), label='question-blind talker', modes={m: md.count(i) for i, m in enumerate(('NUM', 'span', 'GEN'))})
            else:
                les['loops:0'] = dict(score(rows, run(rows, 'loops:0')), label='question-blind talker')
            note(event='eval', set=k, lesion='loops:0', exact=les['loops:0']['exact'], n=len(rows))
        for name in model.LESIONS:
            if name.split(':')[0] != 'loops':
                les[name] = score(rows, run(rows, name))
                note(event='eval', set=k, lesion=name, exact=les[name]['exact'], n=len(rows))
        res['lesions'][k] = les
    return res


# ---- the adapter: build the TEACH / GEN training folders ---------------------------------------------------------------
class OverlapError(SystemExit):
    pass


def _sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def _counts(examples, rows=None):
    return dict(examples=len(examples), questions=sum(len(e['questions']) for e in examples), rows=len(rows) if rows is not None else 2 * sum(len(e['questions']) for e in examples))


def _bad_row(r):
    """-> reason this row is dropped, or None."""
    if not all(c in ASCII for s in [r['prompt'], r['answer']] + r['accepted'] for c in s):
        return 'not_printable_ascii'
    if len(r['prompt']) > MAX_PROMPT:
        return 'prompt_over_208'
    if not r['answer'].strip():
        return 'answer_empty'
    if len(r['answer']) > MAX_TAUGHT:
        return 'answer_over_32'
    return None


def prepare_arm(path, name=None):
    """Read and clean one arm's source -> dict(examples (cleaned, one entry per kept example with its kept rows in 'rows'), steps, drops)."""
    raw = load_examples(path)
    steps, drops, by_kind = [dict(step='source', **_counts(raw))], collections.Counter(), collections.Counter()
    ex, nrows = [], 0
    for e in raw:
        e = clean_example(e)
        rows = qa_rows([e])
        keep = []
        for r in rows:
            why = _bad_row(r)
            if why:
                drops[why] += 1
                by_kind[e['family']] += 1
            else:
                keep.append(r)
        if keep:
            ex.append(dict(e, rows=keep))
        nrows += len(keep)
    steps.append(dict(step='clean_up', examples=len(ex), questions=sum(len({r['id'].rsplit('-q', 1)[1] for r in e['rows']}) for e in ex), rows=nrows))
    ids = [r['id'] for e in ex for r in e['rows']]
    assert len(ids) == len(set(ids)), 'duplicate row ids'
    return dict(path=path, sha256=_sha(path), examples=ex, steps=steps, drops=dict(drops), drops_by_kind=dict(sorted(by_kind.items())))


def _passages(examples):
    return {k for e in examples for p in PANELS for k in (en_norm(e[p]), en_norm(clean(e[p])))}


def guard(examples, evals, arm=''):
    """Refuse (OverlapError, exit 1) if any eval source_text / paraphrase (en_norm) equals a training passage; assert no training prompt
    equals an eval prompt."""
    train = _passages(examples)
    for k, ev in evals.items():
        hit = sorted(train & _passages(ev))
        if hit:
            raise OverlapError(f'{arm}: {len(hit)} {k} passage(s) equal a training passage, refusing to build: {hit[:3]}')
    prompts = {en_norm(r['prompt']) for ev in evals.values() for r in qa_rows(ev)}
    bad = [r['id'] for e in examples for r in e.get('rows', qa_rows([e])) if en_norm(r['prompt']) in prompts]
    assert not bad, f'{arm}: training prompts equal eval prompts: {bad[:3]}'


def _words(s):
    return {w for w in re.findall(r"[a-z0-9]+(?:'[a-z]+)?", en_norm(s)) if w not in STOP}


def overlap_report(examples, evals):
    """Report only. Per eval set: training questions equal to an eval question (per kind), the highest word-set Jaccard of an eval passage
    against any training passage, the number of training passages at or above 0.8, and the number containing a capitalised name from an eval passage."""
    tp = sorted({e[p] for e in examples for p in PANELS})
    sets = [_words(p) for p in tp]
    vid = {}
    for s in sets:
        for w in s:
            vid.setdefault(w, len(vid))
    size = np.array([len(s) for s in sets])
    pid = np.fromiter((i for i, s in enumerate(sets) for _ in s), np.int64, int(size.sum()))
    wid = np.fromiter((vid[w] for s in sets for w in s), np.int64, int(size.sum()))
    o = np.argsort(wid, kind='stable')
    pid, wid = pid[o], wid[o]
    start = np.searchsorted(wid, np.arange(len(vid) + 1))
    caps = [set(re.findall(r"\b[A-Z][a-z]+\b", p)) for p in tp]
    qs = collections.defaultdict(collections.Counter)
    for e in examples:
        for q in e['questions']:
            qs[en_norm(q['question'])][e['family']] += 1
    rep = {}
    for k, ev in evals.items():
        ep = sorted({x for e in ev for x in (e[p] for p in PANELS)})
        lower = {w for x in ep for w in re.findall(r"\b[a-z]+\b", x)}
        names = {w for x in ep for w in re.findall(r"\b[A-Z][a-z]+\b", x) if w.lower() not in lower and w.lower() not in STOP}
        best, hi = 0.0, np.zeros(len(tp), bool)
        for x in ep:
            ws = _words(x)
            inter = np.zeros(len(tp), np.int32)
            for w in ws:
                if w in vid:
                    inter[pid[start[vid[w]]:start[vid[w] + 1]]] += 1
            jac = inter / np.maximum(size + len(ws) - inter, 1)
            best, hi = max(best, float(jac.max()) if len(jac) else 0.0), hi | (jac >= 0.8)
        eq = collections.Counter()
        for q in {en_norm(q['question']) for e in ev for q in e['questions']}:
            eq.update(qs.get(q, {}))
        rep[k] = dict(max_jaccard=round(best, 4), passages_ge_0_8=int(hi.sum()), passages_with_eval_name=sum(bool(c & names) for c in caps),
                      eval_names=len(names), train_questions_equal_eval_question=dict(sorted(eq.items())),
                      n_train_questions_equal=sum(eq.values()))
    return rep


def split_heldout(examples, seed=0, frac=0.01, max_rows=2000):
    """-> (train examples, heldout examples): 1% of examples (at least 1; at most max_rows rows), closed under 'shares a passage (en_norm)'."""
    by_p = collections.defaultdict(list)
    for i, e in enumerate(examples):
        for p in PANELS:
            by_p[en_norm(e[p])].append(i)
    order = np.random.RandomState(seed).permutation(len(examples))
    want, taken, rows = max(1, int(round(frac * len(examples)))), set(), 0
    seeds = 0
    for i in order:
        if seeds >= want:
            break
        if i in taken:
            continue
        group, todo = set(), [i]
        while todo:
            k = todo.pop()
            if k not in group:
                group.add(k)
                todo += [m for p in PANELS for m in by_p[en_norm(examples[k][p])]]
        n = sum(len(examples[k]['rows']) for k in group)
        if rows + n > max_rows and (taken or n > max_rows):
            continue
        taken |= group
        rows += n
        seeds += 1
    assert taken, 'empty held-out slice'
    tr = [e for i, e in enumerate(examples) if i not in taken]
    assert not _passages(tr) & _passages([examples[i] for i in taken]), 'a held-out passage equals a training passage'
    return tr, [examples[i] for i in sorted(taken)]


def parity_cut(examples, target, seed=0):
    """Drop whole examples (seeded) until the row count is within one example of target; any rows still over (examples have up to 4 rows)
    are the last rows of one more seeded example, so the count equals target exactly. -> (examples, rows trimmed from a kept example)."""
    n, drop, trim = sum(len(e['rows']) for e in examples), set(), 0
    order = [int(i) for i in np.random.RandomState(seed).permutation(len(examples))]
    for i in order:
        if n == target:
            break
        if n - len(examples[i]['rows']) >= target:
            drop.add(i)
            n -= len(examples[i]['rows'])
    out = [e for i, e in enumerate(examples) if i not in drop]
    if n > target:
        trim = n - target
        i = next(i for i in order if i not in drop and len(examples[i]['rows']) > trim)
        out = [dict(e, rows=e['rows'][:-trim]) if e is examples[i] else e for e in out]
    assert sum(len(e['rows']) for e in out) == target
    return out, trim


def _rows(examples):
    return [r for e in examples for r in e['rows']]


def _write_arm(out, name, tr, ho, arm, steps, evals, seed):
    d = os.path.join(out, name)
    os.makedirs(os.path.join(d, 'dev'), exist_ok=True)
    files = {'train.jsonl': _rows(tr), 'dev/in_dist.jsonl': _rows(ho)}
    for f, rows in files.items():
        with open(os.path.join(d, f), 'w', encoding='ascii', newline='\n') as fh:
            fh.writelines(json.dumps(r) + '\n' for r in rows)
    CharVocab(ASCII).save(os.path.join(d, 'charvocab.json'), train_bytes=os.path.getsize(os.path.join(d, 'train.jsonl')))
    rows = _rows(tr)
    assert len({r['id'] for r in rows} | {r['id'] for r in _rows(ho)}) == len(rows) + len(_rows(ho)), 'duplicate ids'
    assert not _passages(tr) & _passages(ho), 'a held-out passage equals a training passage'
    rep = overlap_report(tr, evals)
    yes, no = (sum(en_norm(r['answer']) == v for r in rows) for v in ('yes', 'no'))
    man = dict(     # source.file is the basename only, on purpose: the manifest hash must not depend on the machine's path
        arm=name, seed=seed, source=dict(file=os.path.basename(arm['path']), sha256=arm['sha256']), steps=steps,
        drops_by_reason=arm['drops'], drops_by_kind=arm['drops_by_kind'],
        atype=dict(sorted(collections.Counter(r['atype'] for r in rows).items())), yes=yes, no=no, yes_to_no=round(yes / no, 4) if no else None,
        max_prompt=max(len(r['prompt']) for r in rows), max_answer=max(len(r['answer']) for r in rows),
        n_heldout_rows=len(_rows(ho)), n_vocab=len(CharVocab(ASCII)), overlap=rep,
        train_passages_with_gen_heldout_name=rep['gen_heldout']['passages_with_eval_name'],
        families=dict(sorted(collections.Counter(r['family'] for r in rows).items())),
        files={f: _sha(os.path.join(d, f)) for f in ('train.jsonl', 'dev/in_dist.jsonl', 'charvocab.json')})
    with open(os.path.join(d, 'MANIFEST.json'), 'w', encoding='ascii', newline='\n') as fh:     # newline='\n': same bytes (same sha) on Windows and Linux
        json.dump(man, fh, indent=1)
    return man


def build_pair(teach_src, gen_src, out_dir, eval_dir, seed=0):
    """Build out_dir/teach and out_dir/gen (choices 1-5) -> {'teach': manifest, 'gen': manifest}. Raises OverlapError before writing anything."""
    evals = eval_examples(eval_dir)
    arms = {'teach': prepare_arm(teach_src), 'gen': prepare_arm(gen_src)}
    for n, a in arms.items():
        guard(a['examples'], evals, n)
        a['steps'].append(dict(a['steps'][-1], step='overlap_guard', refused=0))
        a['train'], a['held'] = split_heldout(a['examples'], seed)
        a['steps'].append(dict(step='heldout_split', examples=len(a['train']), rows=len(_rows(a['train'])),
                               heldout_examples=len(a['held']), heldout_rows=len(_rows(a['held']))))
    target = min(len(_rows(a['train'])) for a in arms.values())
    for a in arms.values():
        a['train'], trim = parity_cut(a['train'], target, seed)
        a['steps'].append(dict(step='parity_cut', examples=len(a['train']), rows=len(_rows(a['train'])), target=target, rows_trimmed_from_one_example=trim))
    os.makedirs(out_dir, exist_ok=True)
    return {n: _write_arm(out_dir, n, a['train'], a['held'], a, a['steps'], evals, seed) for n, a in arms.items()}


def main(argv=None):
    ap = argparse.ArgumentParser(prog='python -m custom_io.english')
    sp = ap.add_subparsers(dest='cmd', required=True)
    b = sp.add_parser('build', help='write OUT/teach and OUT/gen')
    b.add_argument('--teach', required=True)
    b.add_argument('--gen', required=True)
    b.add_argument('--out', required=True)
    b.add_argument('--eval', required=True, help='dir with the four English eval JSONs')
    b.add_argument('--seed', type=int, default=0)
    a = ap.parse_args(argv)
    man = build_pair(a.teach, a.gen, a.out, a.eval, a.seed)
    for n, m in man.items():
        p = os.path.join(a.out, n, 'MANIFEST.json')
        print(f"{n}: rows {m['steps'][-1]['rows']}  heldout {m['n_heldout_rows']}  atype {m['atype']}  yes:no {m['yes']}:{m['no']}  "
              f"MANIFEST sha256 {_sha(p)}")
    return man


if __name__ == '__main__':
    main()
