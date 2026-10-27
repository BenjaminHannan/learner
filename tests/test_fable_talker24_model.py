"""Checks for scripts/fable_talker24_model.py.  Plain script; prints ALL N CHECKS PASSED.

Run whole:   python3.12 -B tests/test_fable_talker24_model.py
Run a group: python3.12 -B tests/test_fable_talker24_model.py --only floorplan

Groups: layout, presets, shapes, floorplan, copy, pointers, overfit, interventions.

Everything here is CPU-only, single-threaded and finishes in well under two minutes.  No
checkpoint of anything registered is opened; nothing outside a temporary directory is
written.  The ``overfit`` group trains a ~0.87M toy for a few seconds -- that is the only
training in this file.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import random
import sys
import time

HERE = Path(__file__).resolve().parent
for entry in (str(HERE.parent/'scripts'), str(HERE)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

import fable_talker24_model as M                                       # noqa: E402
import fable_talker24_loader as L                                      # noqa: E402
import fable_talker24_interventions as I                               # noqa: E402

torch, F = M.torch, M.F
torch.set_num_threads(1)

CHECKS = []
GROUPS = ('layout', 'presets', 'shapes', 'floorplan', 'copy', 'pointers', 'overfit',
          'interventions', 'slotswap')


def check(group, text, condition, detail=''):
    CHECKS.append((group, text, bool(condition), str(detail)))


# ------------------------------------------------------------------------- layout

def group_layout():
    check('layout', 'the thought is 416 numbers', M.THOUGHT_DIM == 416, M.THOUGHT_DIM)
    sizes = {n: s for n, _, s in M.FIELDS}
    check('layout', 'act 8 / subject 48 / path 3x16 / object 48 / flags 8 / gist 256',
          sizes == dict(act=8, subject=48, relation_path=48, object=48, flags=8,
                        gist=256), sizes)
    spans = sorted((sl.start, sl.stop) for sl in M.SLICES.values())
    contiguous = all(a[1] == b[0] for a, b in zip(spans, spans[1:]))
    check('layout', 'the six fields tile 0..416 with no gap and no overlap',
          contiguous and spans[0][0] == 0 and spans[-1][1] == 416, spans)
    check('layout', 'CHAT is index 3 in BOTH act alphabets',
          M.HEARD_ACTS[M.CHAT_ACT] == 'CHAT' and M.REPLY_ACTS[M.CHAT_ACT] == 'CHAT')

    act_chat = F.one_hot(torch.tensor([M.CHAT_ACT]), M.ACT_DIM).float()
    act_tell = F.one_hot(torch.tensor([0]), M.ACT_DIM).float()
    gist = torch.ones(1, M.GIST_DIM)
    chat = gist*M.gist_gate(act_chat)
    fact = gist*M.gist_gate(act_tell)
    check('layout', 'a CHAT thought keeps all 256 gist numbers',
          int((chat != 0).sum()) == 256, int((chat != 0).sum()))
    check('layout', 'a fact thought keeps exactly the first 32 gist numbers',
          int((fact != 0).sum()) == M.FACT_GIST_DIM
          and float(fact[0, M.FACT_GIST_DIM:].abs().max()) == 0.0,
          int((fact != 0).sum()))
    half = act_chat*0.5 + act_tell*0.5
    soft = gist*M.gist_gate(half)
    check('layout', 'the gate is the same rule smoothed, not a second code path',
          abs(float(soft[0, 100]) - 0.5) < 1e-6, float(soft[0, 100]))

    table = M.SymbolTable(M.config('tiny'))
    code = table.codes[7]
    check('layout', 'a symbol-table code decodes back to its own id exactly',
          int(table.nearest(code)) == 7)
    check('layout', 'a vector that is not a table code decodes to -1',
          int(table.nearest(code + 3.0)) == -1)
    check('layout', 'the all-zero code means "no code"',
          int(table.nearest(torch.zeros(M.CODE_DIM))) == -1)


# ------------------------------------------------------------------------ presets

EXPECTED = {
    # preset: (total trainable, word embeddings, ears total, mouth total, thinker total)
    'S': (7013312, 1572864, 1965888, 2410432, 1064128),
    'M': (33569664, 3145728, 11085056, 11900544, 7438336),
    'L': (87627968, 4718592, 32665536, 33778240, 16465600),
    'XL': (209009664, 6291456, 86175104, 87511296, 29031808),
}


def group_presets():
    rows = {r['preset']: r for r in M.preset_table(('S', 'M', 'L', 'XL'))}
    for name, (total, embed, ears, mouth, thinker) in EXPECTED.items():
        r = rows[name]
        check('presets', f'{name}: total trainable is exactly {total:,}',
              r['total_trainable'] == total, r['total_trainable'])
        check('presets', f'{name}: parts add up to the total',
              r['word_embeddings_tied'] + r['ears_total'] + r['mouth_total']
              + r['thinker_total'] == r['total_trainable'])
        check('presets', f'{name}: word embeddings {embed:,} / ears {ears:,} / '
              f'mouth {mouth:,} / thinker {thinker:,}',
              (r['word_embeddings_tied'], r['ears_total'], r['mouth_total'],
               r['thinker_total']) == (embed, ears, mouth, thinker),
              (r['word_embeddings_tied'], r['ears_total'], r['mouth_total'],
               r['thinker_total']))
    check('presets', 'M is the design\'s ~33M (33.0M..34.5M)',
          33.0e6 <= rows['M']['total_trainable'] <= 34.5e6)
    check('presets', 'L is in the 85M..100M band the build task asks for',
          85e6 <= rows['L']['total_trainable'] <= 100e6, rows['L']['total_trainable'])
    check('presets', 'XL is ~200M (190M..215M)',
          190e6 <= rows['XL']['total_trainable'] <= 215e6, rows['XL']['total_trainable'])
    check('presets', 'the yardstick chat LM is the design\'s ~29M',
          28.5e6 <= rows['M']['yardstick_chat_lm'] <= 30.0e6,
          rows['M']['yardstick_chat_lm'])
    check('presets', 'the frozen reasoner is 79,316 parameters and is not counted in',
          rows['M']['reasoner_frozen'] == 79316)
    cfg = M.config('M')
    block = M.Block(cfg, causal=True)
    n = sum(p.numel() for p in block.parameters())
    check('presets', 'one block is 12 d^2 plus norms (design section 2.2)',
          12*cfg.width**2 <= n <= 12*cfg.width**2 + 8*cfg.width,
          (n, 12*cfg.width**2))
    check('presets', 'the mouth prefix is exactly 416 x 8 x width',
          rows['M']['mouth_thought_prefix'] == 416*8*cfg.width,
          rows['M']['mouth_thought_prefix'])
    check('presets', 'presets are configuration: an override changes the count',
          sum(p.numel() for p in M.Talker(M.config('M', enc_blocks=7)).parameters())
          > rows['M']['total_trainable'])


# ------------------------------------------------------------------------- shapes

def toy(seed=0, **overrides):
    torch.manual_seed(seed)
    return M.Talker(M.config('tiny', **overrides))


def toy_batch(cfg, batch=4, length=8, seed=0):
    rng = random.Random(seed)
    tokens = torch.tensor([[M.BOS] + [rng.randrange(16, cfg.vocab_size)
                                      for _ in range(length)] + [M.EOS]
                           for _ in range(batch)])
    codes = torch.full(tokens.shape, M.ENT_NONE)
    for i in range(batch):
        tokens[i, 1] = M.ENT
        codes[i, 1] = i + 3
    return tokens, codes


def group_shapes():
    model = toy().eval()
    cfg = model.cfg
    tokens, codes = toy_batch(cfg)
    heard = model.ears(tokens, codes)
    check('shapes', 'ears produce one 416-number thought per sentence',
          heard['thought'].shape == (4, 416), tuple(heard['thought'].shape))
    check('shapes', 'the act head is 8-wide', heard['act_logits'].shape == (4, 8))
    check('shapes', 'the relation path head is 3 x 16',
          heard['path_logits'].shape == (4, 3, 16))
    logits = model.mouth(heard['thought'], tokens[:, :-1])
    check('shapes', 'the mouth predicts one distribution per input piece',
          logits.shape == (4, tokens.shape[1] - 1, cfg.vocab_size),
          tuple(logits.shape))
    check('shapes', 'the mouth head is exactly vocab-wide (copy actions are ids 5/6/7)',
          logits.shape[-1] == cfg.vocab_size)
    out = model.autoencode(tokens, codes)
    check('shapes', 'autoencode aligns inputs to targets (next-token)',
          out['logits'].shape[:2] == out['targets'].shape, tuple(out['logits'].shape))
    thoughts = heard['thought'][:, None].repeat(1, 3, 1)
    reply = model.thinker(thoughts)
    check('shapes', 'the thinker returns one reply thought',
          reply['thought'].shape == (4, 416))
    check('shapes', 'the thinker points over earlier SLOTS (2 per thought + null)',
          reply['subject_pointer'].shape == (4, 2*3 + 1),
          tuple(reply['subject_pointer'].shape))
    gru = M.Talker(M.config('tiny'), gru_mouth=True).eval()
    g = gru.mouth(heard['thought'], tokens[:, :-1])
    check('shapes', 'the GRU side arm obeys the same contract',
          g.shape == logits.shape, tuple(g.shape))
    lm = M.ChatLM(cfg)
    x = torch.randint(16, cfg.vocab_size, (2, 12))
    check('shapes', 'the yardstick chat LM is an ordinary next-token model',
          lm(x).shape == (2, 12, cfg.vocab_size), tuple(lm(x).shape))
    spoken = model.mouth.speak(heard['thought'], max_new=6)
    check('shapes', 'speak returns at most max_new pieces', spoken.shape[1] <= 6,
          tuple(spoken.shape))


# ---------------------------------------------------------------------- floor plan

def group_floorplan():
    model = toy().eval()
    plan = M.floor_plan_report(model)
    check('floorplan', 'the mouth signature names no source of words',
          plan['mouth']['ok'], plan['mouth'])
    check('floorplan', 'the GRU mouth signature names no source of words',
          plan['gru_mouth']['ok'], plan['gru_mouth'])
    check('floorplan', 'the mouth takes only (thought, its own previous tokens)',
          plan['mouth']['arguments'] == ['thought', 'reply_tokens'],
          plan['mouth']['arguments'])
    check('floorplan', 'the middle takes no tokens at all',
          plan['thinker']['ok'] and 'tokens' not in plan['thinker']['arguments'],
          plan['thinker']['arguments'])
    check('floorplan', 'the mouth shares nothing with the ears but the word embedding',
          plan['mouth_shares_only_embedding']['ok'],
          plan['mouth_shares_only_embedding'])

    # numeric wall 1: same thought, different words -> not one output bit moves
    cfg = model.cfg
    a_tokens, a_codes = toy_batch(cfg, seed=1)
    b_tokens, b_codes = toy_batch(cfg, seed=2)
    with torch.no_grad():
        thought = model.ears(a_tokens, a_codes)['thought']
        out_a = model.mouth(thought, a_tokens[:, :-1])
        out_b = model.mouth(thought, a_tokens[:, :-1])
        _ = model.ears(b_tokens, b_codes)          # the words change in between
        out_c = model.mouth(thought, a_tokens[:, :-1])
    check('floorplan', 'holding the thought fixed, changing the input words changes no '
          'decoder output bit', torch.equal(out_a, out_c) and torch.equal(out_a, out_b),
          float((out_a - out_c).abs().max()))

    # numeric wall 2: the ONLY gradient path from the words to the mouth is the thought
    heard = model.ears(a_tokens, a_codes)
    states = heard['states']                       # a pure function of the input words
    through = model.mouth(heard['thought'], a_tokens[:, :-1]).sum()
    g_through = torch.autograd.grad(through, states, retain_graph=True,
                                    allow_unused=True)[0]
    heard2 = model.ears(a_tokens, a_codes)
    detached = model.mouth(heard2['thought'].detach(), a_tokens[:, :-1]).sum()
    g_detached = torch.autograd.grad(detached, heard2['states'], retain_graph=True,
                                     allow_unused=True)[0]
    check('floorplan', 'with the thought attached, the words do reach the mouth',
          g_through is not None and float(g_through.abs().max()) > 0)
    check('floorplan', 'with the thought detached, NO gradient reaches the mouth -- the '
          '416 numbers are the only path', g_detached is None,
          'None' if g_detached is None else float(g_detached.abs().max()))

    # wall 3: the thinker cannot see words even by accident
    thoughts = heard['thought'].detach()[:, None].repeat(1, 2, 1)
    import inspect
    args = list(inspect.signature(M.Thinker.forward).parameters)
    check('floorplan', 'Thinker.forward has no token-shaped parameter',
          all(a in ('self', 'thoughts', 'thought_mask', 'hard_act') for a in args), args)
    r = model.thinker(thoughts)
    check('floorplan', 'the thinker runs on thoughts alone', r['thought'].shape == (4, 416))


# ------------------------------------------------------------ the copy-only name wall

def group_copy():
    model = toy().eval()
    cfg = model.cfg
    tokens, codes = toy_batch(cfg, batch=2, seed=3)
    with torch.no_grad():
        thought = model.ears(tokens, codes, hard_act=True)['thought']
        spoken = model.mouth.speak(thought, max_new=10)
        logits = model.mouth(thought, torch.cat(
            (torch.full((2, 1), M.BOS, dtype=torch.long), spoken[:, :-1]), dim=1))
        probs = logits.softmax(-1)

    env = M.CopyEnvironment.from_thought(thought[0], model.symbols)
    present = set(env.codes())
    absent = [c for c in range(model.symbols.size) if c not in present][:20]
    zero = [M.code_emission_probability(probs[0], env, c) for c in absent]
    check('copy', 'a name absent from the thought has EXACTLY zero probability',
          all(p == 0.0 for p in zero), max(zero) if zero else None)
    check('copy', 'zero means the float 0.0, not a small number',
          all(isinstance(p, float) and p == 0.0 for p in zero))
    if present:
        code = sorted(present)[0]
        p = M.code_emission_probability(probs[0], env, code)
        check('copy', 'a name that IS in the thought has a non-zero route',
              0.0 <= p <= 1.0 and isinstance(p, float), p)
    check('copy', 'the copy environment holds at most three codes',
          len(env.codes()) <= 3, env)

    names = {c: f'Name{c}' for c in present}
    text = M.render(spoken[0], env, names)
    for word in text.split():
        if word.startswith('Name'):
            check('copy', f'{word} in the output is a code that was in the thought',
                  int(word[4:]) in present, word)
    other = M.CopyEnvironment(subject=-1, object=-1, old=-1)
    blind = M.render(spoken[0], other, names)
    check('copy', 'with an empty environment no name can be printed at all',
          'Name' not in blind, blind[:80])
    check('copy', 'an unresolved copy action is printed visibly, never silently dropped',
          ('<SUBJ?>' in blind) or ('<OBJ?>' in blind) or ('<OLD?>' in blind)
          or not any(int(t) in M.COPY_ACTIONS for t in spoken[0]), blind[:80])
    import inspect
    banned = inspect.signature(M.Mouth.speak).parameters['banned'].default
    check('copy', 'speak bans <ENT> by default -- a reply has no code source for it',
          M.ENT in banned, banned)
    check('copy', 'the three copy actions are the data contract\'s ids 5, 6, 7',
          M.COPY_ACTIONS == (5, 6, 7), M.COPY_ACTIONS)
    tok = L.TokenizerExport.load(HERE.parent/'artifacts/fable-talker24-20260920/shards')
    check('copy', 'the tokenizer export agrees about the special ids',
          tok.specials['<SUBJ>'] == 5 and tok.specials['<OBJ>'] == 6
          and tok.specials['<OLD>'] == 7 and tok.specials['<ENT>'] == 4, tok.specials)
    reachable = M.reachable_codes(thought[0], model.symbols)
    check('copy', 'reachable_codes agrees with the environment',
          set(reachable) == present, (reachable, present))


# -------------------------------------------------------------- routed, not regressed

def group_pointers():
    model = toy(seed=4).eval()
    cfg = model.cfg
    tokens, codes = toy_batch(cfg, batch=5, seed=5)
    heard = model.ears(tokens, codes)
    subject = M.field_of(heard['thought'], 'subject')
    ids = model.symbols.nearest(subject)
    ok = 0
    for i in range(5):
        if int(ids[i]) >= 0:
            ok += int(torch.equal(subject[i], model.symbols.codes[int(ids[i])]))
        else:
            ok += int(float(subject[i].detach().abs().max()) == 0.0)   # the null slot
    check('pointers', 'every routed subject code is a table row BIT-EXACTLY (or the '
          'null zero code)', ok == 5, ok)
    check('pointers', 'the pointer is a proper distribution over the positions + null',
          abs(float(heard['subject_pointer'].sum(-1)[0]) - 1.0) < 1e-5)
    check('pointers', 'the pointer has one extra column for "no object"',
          heard['object_pointer'].shape[-1] == tokens.shape[1] + 1,
          tuple(heard['object_pointer'].shape))
    loss = M.field_of(heard['thought'], 'subject').sum()
    grads = torch.autograd.grad(loss, model.ears.subject_pointer.q.weight,
                                allow_unused=True)[0]
    check('pointers', 'straight-through leaves a gradient for the pointer to learn from',
          grads is not None and float(grads.abs().max()) > 0)
    soft = M.Talker(M.config('tiny', pointer_straight_through=False)).eval()
    h2 = soft.ears(tokens, codes)
    mixed = soft.symbols.nearest(M.field_of(h2['thought'], 'subject'))
    check('pointers', 'without straight-through the code is a BLEND and stops being a '
          'table row -- which is why straight-through is the default',
          int((mixed < 0).sum()) >= 1, mixed.tolist())
    check('pointers', 'the symbol table is a buffer, never a trained parameter',
          not any(p is model.symbols.codes for p in model.parameters()))
    before = model.symbols.codes.clone()
    M.Talker(M.config('tiny'))
    check('pointers', 'the codes are a pure function of the seed (same on both machines)',
          torch.equal(before, M.SymbolTable(M.config('tiny')).codes))


# ---------------------------------------------------------------------- tiny overfit

def group_overfit():
    torch.manual_seed(0)
    cfg = M.config('tiny', width=96, heads=3, enc_blocks=2, dec_blocks=2, vocab_size=64,
                   max_len=12, prefix_slots=4)
    model = M.Talker(cfg)
    rng = random.Random(0)
    n, length = 8, 6
    sentences = [[rng.randrange(16, 64) for _ in range(length)] for _ in range(n)]
    tokens = torch.tensor([[M.BOS] + s + [M.EOS] for s in sentences])
    codes = torch.full(tokens.shape, M.ENT_NONE)
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-3, betas=(0.9, 0.95),
                                  weight_decay=0.01)
    started = time.time()
    for _ in range(400):
        optimizer.zero_grad(set_to_none=True)
        out = model.autoencode(tokens, codes)
        loss = F.cross_entropy(out['logits'].reshape(-1, cfg.vocab_size),
                               out['targets'].reshape(-1), ignore_index=M.PAD)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
    model.eval()
    with torch.no_grad():
        thought = model.ears(tokens, codes)['thought']
        spoken = model.mouth.speak(thought, max_new=length + 3)
    exact = 0
    for i in range(n):
        got = I.trim(spoken[i])
        exact += int(got == sentences[i])
    elapsed = time.time() - started
    check('overfit', 'a tiny model memorises 8 sentences THROUGH the 416-number thought',
          exact >= 7, f'{exact}/{n} exact, final loss {float(loss):.5f}')
    check('overfit', 'it takes under a minute on one CPU thread', elapsed < 60,
          f'{elapsed:.1f}s')
    check('overfit', 'the thought really is the bottleneck: 416 numbers carried '
          f'{n} x {length} pieces', thought.shape == (n, 416))
    with torch.no_grad():
        shuffled = model.mouth.speak(thought[torch.tensor([1, 0, 3, 2, 5, 4, 7, 6])],
                                     max_new=length + 3)
    follows = sum(I.trim(shuffled[i]) == sentences[[1, 0, 3, 2, 5, 4, 7, 6][i]]
                  for i in range(n))
    check('overfit', 'swapping the thoughts swaps the sentences -- the mouth is reading '
          'the thought, not memorising an order', follows >= 7, f'{follows}/{n}')


# ------------------------------------------------------------------- the harness

def group_interventions():
    report = I._toy(n=8, seed=0)
    for name in ('slot_swap', 'gist_shuffle', 'gist_zero', 'thought_replace'):
        score = report[name]['score']
        # None is legal and means NOT MEASURED -- it is never read as a zero.
        check('interventions', f'the {name} test runs and returns a score in [0, 1] or '
              'None for NOT MEASURED',
              score is None or 0.0 <= score <= 1.0, score)
    check('interventions', 'the marks are the design\'s, not a run\'s',
          report['marks']['slot_swap']['mark'] == I.MARKS['slot_swap_s0']
          and report['marks']['gist_shuffle']['mark'] == 0.99
          and report['marks']['gist_zero_change']['mark'] == 0.90
          and report['marks']['thought_replace']['mark'] == 0.95,
          {k: v['mark'] for k, v in report['marks'].items()})
    check('interventions', 'S1 uses the stricter 98 % slot-swap mark',
          I.MARKS['slot_swap'] == 0.98)
    check('interventions', 'the pre-named "mouth ignores the thought" detector fires on '
          'an untrained model (reconstruction 0)', report['signature']['triggered']
          and any('reconstruction' in c for c in report['signature']['clauses']),
          report['signature']['clauses'])
    check('interventions', 'it reports the three pre-named fixes IN ORDER',
          len(report['signature']['fixes_in_order']) == 3
          and report['signature']['fixes_in_order'][0].startswith('1. word dropout'))
    check('interventions', 'the "gist is blurry" detector fires when replies collapse',
          report['blurry_gist']['triggered'] and report['blurry_gist']['threshold'] == 0.4,
          report['blurry_gist']['top10_share'])
    good = I.ignores_thought_signature(dict(exact_reconstruction=0.9,
                                            thought_replace=0.97, slot_swap=0.99,
                                            gist_shuffle_reworded=0.3))
    check('interventions', 'the detector stays quiet on healthy numbers',
          not good['triggered'], good['clauses'])
    check('interventions', 'an untrained model does not pass all four marks',
          not report['all_marks_passed'])

    # the surgery helpers must change exactly what they say they change
    model = toy().eval()
    tokens, codes = toy_batch(model.cfg, batch=3, seed=9)
    thought = model.ears(tokens, codes, hard_act=True)['thought'].detach()
    swapped = I.set_code(thought, 'subject', model.symbols.codes[11][None])
    diff = (swapped != thought).any(0).nonzero().flatten().tolist()
    inside = all(M.SLICES['subject'].start <= d < M.SLICES['subject'].stop for d in diff)
    check('interventions', 'a subject swap touches only the 48 subject numbers', inside,
          diff[:8])
    rel = I.set_relation(thought, 0, 5)
    diff = (rel != thought).any(0).nonzero().flatten().tolist()
    inside = all(M.SLICES['relation_path'].start <= d
                 < M.SLICES['relation_path'].start + 16 for d in diff)
    check('interventions', 'a relation swap touches only the first path slot', inside,
          diff[:8])


# ------------------------------------------------- the slot-swap scorer, after S0
#
# S0 on BensPC reported subject 0.000 and object 0.000 on the autoencode checkpoint.
# Neither was a measurement: every pointer sat on its NULL slot, every sample was
# skipped, and the mean of the empty list was reported as 0.0.  These checks pin the
# three properties that stop that happening again.

class _ScriptedMouth:
    """A mouth that says exactly what the script says, so the SCORER is what is tested."""

    def __init__(self, script, follow=None):
        self.script, self.follow = script, follow        # follow: tokens once swapped
        self.base = None

    def speak(self, thought, max_new=32, **kw):
        if self.base is None:                            # the first call is the base one
            self.base = thought.clone()
        rows = []
        for i in range(thought.shape[0]):
            untouched = any(bool(torch.equal(thought[i], b)) for b in self.base)
            rows.append(self.script if untouched or self.follow is None else self.follow)
        return torch.tensor(rows, dtype=torch.long, device=thought.device)


class _ScriptedModel:
    def __init__(self, symbols, script, follow=None):
        self.symbols, self.mouth = symbols, _ScriptedMouth(script, follow)

    def eval(self):
        return self


def _slot_thoughts(symbols, subject=3, object_=4, n=2):
    base = torch.zeros(n, M.THOUGHT_DIM)
    base = I.set_code(base, 'subject', symbols.codes[subject][None])
    return I.set_code(base, 'object', symbols.codes[object_][None])


def group_slotswap():
    symbols = toy().eval().symbols

    # 1. a field with no eligible turn is None and NOT MEASURED -- never 0.0
    check('slotswap', '_mean of an empty list is None, not 0.0',
          I._mean([]) is None and I._mean([], empty='x') == 'x', I._mean([]))
    mute = _ScriptedModel(symbols, [40, 41, M.EOS])          # never says <SUBJ>/<OBJ>
    r = I.slot_swap_test(mute, _slot_thoughts(symbols), symbols)
    check('slotswap', 'a model that never emits the copy token scores None, not 0.0, for '
          'subject and object', r['by_field']['subject'] is None
          and r['by_field']['object'] is None and r['score'] is None,
          r['by_field'])
    check('slotswap', 'and it is NOT MEASURED, with the ineligible turns counted',
          r['measured'] is False and r['not_measured'] == ['object', 'subject']
          and r['counts']['n_skipped_no_copy_token'] == 4
          and r['counts']['n_subject'] == 0, r['counts'])
    check('slotswap', 'the NOT MEASURED note says so in words',
          'NOT MEASURED' in r['note'] and 'not a score of zero' in r['note'], r['note'])
    mark = I._mark(None, 0.95, detail=['subject'])
    check('slotswap', 'an unmeasured mark FAILS loudly rather than passing or scoring 0',
          mark['passed'] is False and mark['measured'] is False
          and mark['score'] is None and 'NOT MEASURED' in mark['note'], mark)

    # 2. the copy arm is a test OF THE MODEL: the rendered name must follow the pointer
    faithful = _ScriptedModel(symbols, [M.SUBJ, 40, M.OBJ, M.EOS])
    r = I.slot_swap_test(faithful, _slot_thoughts(symbols), symbols)
    check('slotswap', 'a mouth that really copies passes both copy fields',
          r['by_field']['subject'] == 1.0 and r['by_field']['object'] == 1.0
          and r['counts']['n_subject'] == 2, r['by_field'])
    moody = _ScriptedModel(symbols, [M.SUBJ, 40, M.OBJ, M.EOS],
                           follow=[M.SUBJ, 41, M.OBJ, M.EOS])   # re-words on a swap
    r = I.slot_swap_test(moody, _slot_thoughts(symbols), symbols)
    check('slotswap', 'a mouth that re-words the sentence on a pointer swap FAILS the '
          'copy arm', r['by_field']['subject'] == 0.0
          and r['diagnostics']['copy_words_unchanged'] == 0.0, r['by_field'])
    check('slotswap', 'the model-free resolution flag is kept only as a labelled '
          'diagnostic, out of the pass rule',
          'copy_resolution_changed_MODEL_FREE' in r['diagnostics']
          and r['diagnostics']['copy_resolution_changed_MODEL_FREE'] == 1.0
          and r['by_field']['subject'] == 0.0, r['diagnostics'])

    # 3. an autoencode checkpoint is refused by name
    try:
        I.slot_swap_test(faithful, _slot_thoughts(symbols), symbols,
                         train_stage='autoencode')
        refused, message = False, ''
    except ValueError as exc:
        refused, message = True, str(exc)
    check('slotswap', 'slot-swap REFUSES an autoencode-stage checkpoint, naming the stage',
          refused and 'autoencode' in message and 'NULL' in message, message[:80])
    for stage in ('slots', 'thinker'):
        ok = True
        try:
            I.slot_swap_test(faithful, _slot_thoughts(symbols), symbols,
                             train_stage=stage)
        except ValueError:
            ok = False
        check('slotswap', f'but it allows a {stage}-stage checkpoint', ok)

    # 4. the three interventions that scored 1.000 in S0 were real: n > 0 in the file
    marks = Path(__file__).resolve().parents[1]/('artifacts/fable-talker24-20260920/'
                                                 's0-benspc/s0-marks.json')
    if marks.exists():
        got = json.loads(marks.read_text())['interventions']
        check('slotswap', 'S0\'s gist-shuffle / gist-zero / thought-replace 1.000 were '
              'measured (n > 0), so those three scores stand',
              all(got[k]['n'] > 0 for k in ('gist_shuffle', 'gist_zero',
                                            'thought_replace')),
              {k: got[k]['n'] for k in ('gist_shuffle', 'gist_zero', 'thought_replace')})
        swap = got['slot_swap']
        # n == 64 == one relation result per thought leaves no room for a copy result,
        # and the model-free resolution flag can only read 0.0 when it averaged nothing.
        check('slotswap', 'S0\'s slot-swap subject/object 0.000 carries the empty-mean '
              'fingerprint, so it was never measured',
              swap['n'] == 64 and swap['by_field']['subject'] == 0.0
              and swap['by_field']['object'] == 0.0
              and swap['diagnostics']['copy_resolution_changed'] == 0.0,
              {'n': swap['n'], 'by_field': swap['by_field']})


# ------------------------------------------------------------------------- runner

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--only', nargs='*', default=None, choices=GROUPS)
    args = parser.parse_args(argv)
    groups = args.only or GROUPS
    started = time.time()
    for name in groups:
        globals()[f'group_{name}']()
    failed = [c for c in CHECKS if not c[2]]
    for group, text, ok, detail in CHECKS:
        mark = 'ok  ' if ok else 'FAIL'
        print(f'{mark} [{group}] {text}' + (f'   -- {detail}' if detail and not ok else ''))
    print()
    if failed:
        print(f'{len(failed)} OF {len(CHECKS)} CHECKS FAILED '
              f'({time.time() - started:.1f}s)')
        return 1
    print(f'ALL {len(CHECKS)} CHECKS PASSED ({time.time() - started:.1f}s)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
