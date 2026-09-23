"""Talker 24 -- the four thought-intervention tests of design section 3.4, reusable.

The design's own table, with the design's own marks:

  | test           | do this                                            | must happen                          | mark |
  | slot swap      | change exactly one of subject / relation / object  | the sentence changes in exactly that | >= 98 %
  |                | in a reply thought                                 | place, nothing else in meaning       | (S0 >= 95 %)
  | gist shuffle   | give a fact reply some other sentence's gist       | the stated fact does not change      | >= 99 %
  | gist zero      | zero the gist of a CHAT reply                      | the reply changes                    | >= 90 % change
  | thought replace| decode sentence i from sentence j's thought        | the output follows j, not i          | >= 95 % of tokens

HOW EACH ONE IS SCORED (the design says what must happen; these are the exact rules)

  slot swap, subject / object : the subject and the object reach the output ONLY through a
      copy action, so swapping the code must leave the WORDS bit-identical and move the
      RENDERED name -- and nothing else.  A turn counts only if the base decoding really
      emitted that copy action; otherwise it is ineligible and is counted as such, never
      as a pass.  A turn passes when the token stream is unchanged AND the rendered
      sentence is the base sentence with that one name replaced by the swapped code's
      name.  If the words move, the mouth was using the code for something other than
      copying, which is the failure this test exists to catch.  A field with no eligible
      turns scores None -- NOT MEASURED -- and the mark fails; it is never 0.0.
  slot swap, relation : the relation is spoken as ordinary words, so the words MUST change,
      while the copy actions stay in the same places resolving to the same codes.
  gist shuffle : "the stated fact does not change" = the ordered list of (copy action,
      resolved code) pairs is unchanged.  Whether the wording changed is reported beside
      it, not marked.
  gist zero : the token sequence differs from the unzeroed one.
  thought replace : the fraction of emitted tokens equal to the reference decoding of j.

THE PRE-NAMED FAILURE SIGNATURE (section 3.4, named in advance, not after the fact)

  "mouth ignores the thought" = fluent output, but exact reconstruction < 30 % OR
  thought-replace sensitivity < 50 % OR (slot-swap < 90 % while gist-shuffle changes
  nothing at all).  ``ignores_thought_signature`` returns which clause fired and the
  pre-named fix order; it never invents a new fix.

  "gist is blurry" = more than 40 % of chat replies are among the 10 most common.
  ``blurry_gist_signature`` reports it with its own pre-named fix order.

CLI
  toy      run the whole harness on an untrained toy model (shape check, not a result)
  report   run it on a checkpoint written by fable_talker24_train.py
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import fable_talker24_model as M                                       # noqa: E402
import fable_talker24_loader as L                                      # noqa: E402

torch, F = M.torch, M.F

# The marks, taken from the design and not from any run.
MARKS = dict(slot_swap=0.98, slot_swap_s0=0.95, gist_shuffle=0.99,
             gist_zero_change=0.90, thought_replace=0.95)
SIGNATURE_THRESHOLDS = dict(exact_reconstruction=0.30, thought_replace=0.50,
                            slot_swap=0.90)
IGNORES_THOUGHT_FIXES = (
    '1. word dropout -- blank 30 % of the mouth\'s own previous words during training so '
    'it cannot coast on fluency (Bowman et al.)',
    '2. a bag-of-words side loss: the thought alone must predict which words appear',
    '3. shrink the mouth to 4 blocks and widen the prefix to 16 vectors')
BLURRY_GIST_FIXES = (
    '1. confirm cross-entropy-through-mouth is on, not MSE',
    '2. code-book gist (4 code-books x 256 entries) so the thinker CLASSIFIES instead of '
    'regressing')
BLURRY_GIST_THRESHOLD = 0.40
NOT_MEASURED_NOTE = ('NOT MEASURED: no eligible sample for {fields}. This is not a score '
                     'of zero -- the question was never put to the model. See counts.')


# ------------------------------------------------------------------- thought surgery

def set_code(thought, field, code_vector):
    out = thought.clone()
    out[..., M.SLICES[field]] = code_vector
    return out


def set_relation(thought, slot, choice):
    out = thought.clone()
    path = M.field_of(out, 'relation_path').reshape(-1, M.RELATION_SLOTS,
                                                    M.RELATION_CHOICES).clone()
    path[:, slot] = 0.0
    path[:, slot, choice] = 1.0
    out[..., M.SLICES['relation_path']] = path.reshape(-1, M.RELATION_DIM)
    return out


def set_gist(thought, gist):
    out = thought.clone()
    out[..., M.SLICES['gist']] = gist*M.gist_gate(M.field_of(thought, 'act'))
    return out


def set_act(thought, act_index):
    out = thought.clone()
    # Device fix (S0 on BensPC): ``torch.full`` defaults to CPU, so on a non-CPU model
    # this one-hot act could not be written into the thought.  Build it where the
    # thought lives.
    act = F.one_hot(torch.full(thought.shape[:-1], act_index, dtype=torch.long,
                               device=thought.device),
                    M.ACT_DIM).to(thought.dtype)
    out[..., M.SLICES['act']] = act
    gist = M.field_of(thought, 'gist')
    out[..., M.SLICES['gist']] = gist*M.gist_gate(act)
    return out


# ------------------------------------------------------------------------- utilities

def speak(model, thought, max_new=32):
    with torch.no_grad():
        return model.mouth.speak(thought, max_new=max_new)


def trim(tokens):
    out = []
    for t in [int(x) for x in tokens]:
        if t == M.EOS:
            break
        if t != M.PAD:
            out.append(t)
    return out


def copy_trace(tokens, environment):
    """The ordered (copy action, resolved code) pairs -- "the stated fact", exactly."""
    return [(t, environment.resolve(t)) for t in trim(tokens) if t in M.COPY_ACTIONS]


def words_only(tokens):
    return [t for t in trim(tokens)]


# ============================================================== the four interventions

def placeholder_names(symbols):
    """A surface string for every table code, so ``M.render`` can print a name.

    The strings are synthetic on purpose.  The test only asks WHICH code reached the
    output, and a synthetic name makes that unambiguous even when no lexicon is to hand.
    Pass the real ``names`` map instead when there is one.
    """
    return {c: f'<name {c}>' for c in range(int(symbols.size))}


def slot_swap_test(model, thoughts, symbols, n_codes=None, names=None, train_stage=None):
    """Change exactly one slot; everything else must stay put.

    The copy arm (subject / object) is a test OF THE MODEL, and it is scored that way:

      * a turn is ELIGIBLE only if the base decoding actually emits that field's copy
        action.  A model that never says ``<SUBJ>`` is not silently credited with a pass;
        the turn is counted as ineligible and the count is reported.
      * a turn is SKIPPED when the pointer sits on its NULL slot, so the slot holds the
        zero vector and ``symbols.nearest`` returns -1.  There is no code to swap.  That
        count is reported too, under ``n_skipped_null_pointer``.
      * PASS = the emitted token stream is bit-identical (a name has no route to the
        tokens -- the reply says ``<SUBJ>``, never the name) AND the RENDERED sentence is
        exactly the base sentence with that one name replaced by the swapped code's name.

    ``resolution_changed`` is kept only as a labelled diagnostic.  It is computed from the
    thought and the symbol table with no model in the loop, so it can never be evidence
    about a model, and it is no longer part of the pass condition.

    A field with no eligible turns scores ``None`` -- NOT MEASURED -- never 0.0.

    ``train_stage`` is the stage the checkpoint was trained at.  ``'autoencode'`` is
    refused: that stage never supervises the pointer heads, so every pointer sits on NULL
    and the copy arm has nothing to measure.
    """
    if train_stage == 'autoencode':
        raise ValueError(
            "slot_swap_test refuses an 'autoencode'-stage checkpoint: the autoencode "
            "stage never trains the subject/object pointer heads, so every pointer sits "
            "on its NULL slot and the copy arm has no code to swap.  Run the slot-swap "
            "test on a 'slots' or 'thinker' checkpoint instead.")
    n_codes = n_codes or symbols.size
    names = placeholder_names(symbols) if names is None else names
    results = []
    counts = dict(n_relation=0, n_subject=0, n_object=0, n_skipped_null_pointer=0,
                  n_skipped_no_copy_token=0)
    base_tokens = speak(model, thoughts)
    for i in range(thoughts.shape[0]):
        base = thoughts[i:i + 1]
        base_env = M.CopyEnvironment.from_thought(base[0], symbols)
        base_out = words_only(base_tokens[i])
        for field in ('subject', 'object'):
            action = M.SUBJ if field == 'subject' else M.OBJ
            old = int(symbols.nearest(M.field_of(base[0], field)))
            if old < 0:
                counts['n_skipped_null_pointer'] += 1
                continue
            if action not in base_out:
                # The mouth never named this slot, so a swap cannot show up anywhere.
                # Not a pass, not a failure -- an ineligible turn, counted as one.
                counts['n_skipped_no_copy_token'] += 1
                continue
            new = (old + 1 + i) % n_codes
            if new == old:
                new = (old + 1) % n_codes
            if new == old:                       # a one-row table: nothing to swap to
                counts['n_skipped_null_pointer'] += 1
                continue
            swapped = set_code(base, field, symbols.codes[new][None])
            out = words_only(speak(model, swapped)[0])
            env = M.CopyEnvironment.from_thought(swapped[0], symbols)
            words_unchanged = out == base_out
            # What the sentence MUST become: the same tokens, rendered in the swapped
            # environment.  Built from ``base_out`` so it does not depend on the model.
            expected = M.render(base_out, env, names)
            before = M.render(base_out, base_env, names)
            after = M.render(out, env, names)
            new_name, old_name = names.get(new), names.get(old)
            renders_as_expected = bool(after == expected and after != before
                                       and new_name is not None and new_name in after
                                       and (old_name is None or old_name not in after))
            counts[f'n_{field}'] += 1
            results.append(dict(field=field,
                                passed=bool(words_unchanged and renders_as_expected),
                                words_unchanged=bool(words_unchanged),
                                name_followed_the_pointer=renders_as_expected,
                                resolution_changed=bool(env.resolve(action) == new
                                                        and base_env.resolve(action) == old)))
        path = M.field_of(base[0], 'relation_path').reshape(M.RELATION_SLOTS,
                                                            M.RELATION_CHOICES)
        old_choice = int(path[0].argmax())
        new_choice = (old_choice + 1) % M.RELATION_CHOICES
        swapped = set_relation(base, 0, new_choice)
        out = words_only(speak(model, swapped)[0])
        same_copies = ([t for t in out if t in M.COPY_ACTIONS]
                       == [t for t in base_out if t in M.COPY_ACTIONS])
        counts['n_relation'] += 1
        results.append(dict(field='relation', passed=bool(out != base_out and same_copies),
                            words_changed=bool(out != base_out),
                            copies_unchanged=bool(same_copies)))
    by_field = {f: _mean([r['passed'] for r in results if r['field'] == f])
                for f in ('subject', 'object', 'relation')}
    not_measured = sorted(f for f, v in by_field.items() if v is None)
    score = _mean([r['passed'] for r in results])
    if not_measured:
        # An unmeasured field is not a zero.  Refuse to report an overall score at all.
        score = None
    return dict(score=score, n=len(results), measured=not not_measured,
                not_measured=not_measured, counts=counts, by_field=by_field,
                note=(NOT_MEASURED_NOTE.format(fields=', '.join(not_measured))
                      if not_measured else ''),
                diagnostics=dict(
                    copy_words_unchanged=_mean([r['words_unchanged'] for r in results
                                                if 'words_unchanged' in r]),
                    copy_name_followed_the_pointer=_mean(
                        [r['name_followed_the_pointer'] for r in results
                         if 'name_followed_the_pointer' in r]),
                    # Model-free bookkeeping about the thought and the symbol table.  It
                    # is NOT evidence about the model and is not part of any pass rule.
                    copy_resolution_changed_MODEL_FREE=_mean(
                        [r['resolution_changed'] for r in results
                         if 'resolution_changed' in r]),
                    relation_words_changed=_mean([r['words_changed'] for r in results
                                                  if 'words_changed' in r])))


def gist_shuffle_test(model, thoughts, symbols):
    """Another sentence's gist; the stated fact must survive."""
    base = speak(model, thoughts)
    rolled = torch.roll(M.field_of(thoughts, 'gist'), 1, dims=0)
    shuffled = set_gist(thoughts, rolled)
    after = speak(model, shuffled)
    kept, reworded = [], []
    for i in range(thoughts.shape[0]):
        env = M.CopyEnvironment.from_thought(thoughts[i], symbols)
        kept.append(copy_trace(base[i], env) == copy_trace(after[i], env))
        reworded.append(words_only(base[i]) != words_only(after[i]))
    return dict(score=_mean(kept), n=len(kept), reworded_rate=_mean(reworded))


def gist_zero_test(model, thoughts):
    """Zero a CHAT reply's gist; the reply must change (it shows the gist is used)."""
    chat = set_act(thoughts, M.CHAT_ACT)
    base = speak(model, chat)
    zeroed = set_gist(chat, torch.zeros_like(M.field_of(chat, 'gist')))
    after = speak(model, zeroed)
    changed = [words_only(base[i]) != words_only(after[i]) for i in range(len(base))]
    return dict(score=_mean(changed), n=len(changed))


def thought_replace_test(model, thoughts):
    """Decode i from j's thought; the tokens must follow j."""
    order = torch.roll(torch.arange(thoughts.shape[0]), 1)
    own = speak(model, thoughts)
    other = speak(model, thoughts[order])
    follow_j, follow_i = [], []
    for i in range(thoughts.shape[0]):
        a, b, c = words_only(other[i]), words_only(own[order[i]]), words_only(own[i])
        follow_j.append(_token_agreement(a, b))
        follow_i.append(_token_agreement(a, c))
    return dict(score=_mean(follow_j), n=len(follow_j), follows_own=_mean(follow_i))


def exact_reconstruction(model, tokens, codes):
    """Held-out "say it back": token accuracy and exact-sentence rate."""
    with torch.no_grad():
        heard = model.ears(tokens, codes)
        spoken = model.mouth.speak(heard['thought'], max_new=tokens.shape[1] + 2)
    exact, correct, total = [], 0, 0
    for i in range(tokens.shape[0]):
        target = words_only(tokens[i][1:])          # drop <bos>
        got = words_only(spoken[i])
        exact.append(target == got)
        total += len(target)
        correct += sum(1 for a, b in zip(target, got) if a == b)
    return dict(exact=_mean(exact), token_accuracy=correct/max(total, 1), n=len(exact))


def _token_agreement(a, b):
    if not a and not b:
        return 1.0
    n = max(len(a), len(b))
    return sum(1 for x, y in zip(a, b) if x == y)/max(n, 1)


def _mean(values, empty=None):
    """The mean, or ``empty`` (``None``) when there is nothing to average.

    NEVER 0.0 on an empty list.  In S0 that default turned "no sample was ever run" into
    "the model scored zero", and the subject/object slot-swap 0.000 in
    ``s0-benspc/s0-marks.json`` was read as a result for a day.  A score that was not
    measured must say so.
    """
    values = list(values)
    return float(sum(values)/len(values)) if values else empty


def _mark(score, mark, detail=None):
    """One mark.  An unmeasured score (``None``) does NOT pass -- it says NOT MEASURED."""
    if score is None:
        fields = ', '.join(detail) if detail else 'the whole test'
        return dict(score=None, mark=mark, passed=False, measured=False,
                    note=NOT_MEASURED_NOTE.format(fields=fields))
    return dict(score=score, mark=mark, passed=bool(score >= mark), measured=True)


# ========================================================== the pre-named signatures

def ignores_thought_signature(metrics):
    """Named in advance in section 3.4.  Reports WHICH clause fired and the fix order."""
    # A metric that was never measured is None.  It can neither fire a clause nor clear
    # one, so it is reported separately instead of being silently read as a zero.
    not_measured = sorted(k for k, v in metrics.items() if v is None)
    metrics = {k: v for k, v in metrics.items() if v is not None}
    clauses = []
    if metrics.get('exact_reconstruction', 1.0) < SIGNATURE_THRESHOLDS['exact_reconstruction']:
        clauses.append(f'exact reconstruction {metrics["exact_reconstruction"]:.3f} < '
                       f'{SIGNATURE_THRESHOLDS["exact_reconstruction"]}')
    if metrics.get('thought_replace', 1.0) < SIGNATURE_THRESHOLDS['thought_replace']:
        clauses.append(f'thought-replace sensitivity {metrics["thought_replace"]:.3f} < '
                       f'{SIGNATURE_THRESHOLDS["thought_replace"]}')
    if (metrics.get('slot_swap', 1.0) < SIGNATURE_THRESHOLDS['slot_swap']
            and metrics.get('gist_shuffle_reworded', 1.0) == 0.0):
        clauses.append(f'slot-swap {metrics["slot_swap"]:.3f} < '
                       f'{SIGNATURE_THRESHOLDS["slot_swap"]} while gist-shuffle changes '
                       f'nothing at all')
    return dict(name='mouth ignores the thought', triggered=bool(clauses),
                clauses=clauses, not_measured=not_measured,
                fixes_in_order=list(IGNORES_THOUGHT_FIXES),
                note='apply the fixes ONE AT A TIME, in this order; they were named '
                     'before any run (design section 3.4)')


def blurry_gist_signature(replies):
    """> 40 % of chat replies among the 10 most common."""
    keys = [tuple(words_only(r)) for r in replies]
    counts = Counter(keys)
    top = sum(c for _, c in counts.most_common(10))
    share = top/max(len(keys), 1)
    return dict(name='gist is blurry', triggered=bool(share > BLURRY_GIST_THRESHOLD),
                top10_share=share, threshold=BLURRY_GIST_THRESHOLD,
                distinct_replies=len(counts), fixes_in_order=list(BLURRY_GIST_FIXES))


# =============================================================== the reusable harness

def run_interventions(model, thoughts, tokens=None, codes=None, stage='S1', label='',
                      train_stage=None, names=None):
    """Everything in one call.  ``stage='S0'`` relaxes only the slot-swap mark, which is
    the only mark the design relaxes for the smoke test.

    ``train_stage`` is the stage of the checkpoint under test (``'autoencode'``,
    ``'slots'``, ``'thinker'``, ``'yardstick'``).  ``'autoencode'`` is refused by
    ``slot_swap_test``.  Left ``None`` -- unknown -- the run still goes ahead, and an
    all-NULL pointer now shows up honestly as NOT MEASURED rather than as 0.000.
    """
    model.eval()
    symbols = model.symbols
    report = dict(label=label, stage=stage, train_stage=train_stage,
                  n_thoughts=int(thoughts.shape[0]))
    report['slot_swap'] = slot_swap_test(model, thoughts, symbols, names=names,
                                         train_stage=train_stage)
    report['gist_shuffle'] = gist_shuffle_test(model, thoughts, symbols)
    report['gist_zero'] = gist_zero_test(model, thoughts)
    report['thought_replace'] = thought_replace_test(model, thoughts)
    if tokens is not None:
        report['reconstruction'] = exact_reconstruction(model, tokens, codes)
    chat = set_act(thoughts, M.CHAT_ACT)
    report['blurry_gist'] = blurry_gist_signature(speak(model, chat))

    slot_mark = MARKS['slot_swap_s0'] if stage == 'S0' else MARKS['slot_swap']
    report['marks'] = dict(
        slot_swap=_mark(report['slot_swap']['score'], slot_mark,
                        detail=report['slot_swap'].get('not_measured')),
        gist_shuffle=_mark(report['gist_shuffle']['score'], MARKS['gist_shuffle']),
        gist_zero_change=_mark(report['gist_zero']['score'], MARKS['gist_zero_change']),
        thought_replace=_mark(report['thought_replace']['score'],
                              MARKS['thought_replace']))
    report['all_marks_passed'] = all(m['passed'] for m in report['marks'].values())
    report['signature'] = ignores_thought_signature(dict(
        exact_reconstruction=report.get('reconstruction', {}).get('exact', 1.0),
        thought_replace=report['thought_replace']['score'],
        slot_swap=report['slot_swap']['score'],
        gist_shuffle_reworded=report['gist_shuffle']['reworded_rate']))
    return report


def thoughts_from_turns(model, turns, device=None):
    tokens, codes, labels = L.dialogue_batch(turns, device=device)
    with torch.no_grad():
        heard = model.ears(tokens, codes, hard_act=True)
    return heard['thought'], tokens, codes, labels


# ================================================================================ CLI

def _toy(n=16, seed=0, preset='tiny'):
    torch.manual_seed(seed)
    model = M.Talker(M.config(preset)).eval()
    turns = L.synthetic_dialogues(n, seed=seed, vocab_size=model.cfg.vocab_size,
                                  max_len=min(model.cfg.max_len, 12)).turns
    thoughts, tokens, codes, _ = thoughts_from_turns(model, turns)
    return run_interventions(model, thoughts, tokens, codes, stage='S0',
                             label=f'UNTRAINED toy {preset} model, seed {seed}')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest='command', required=True)
    t = sub.add_parser('toy', help='shape check on an untrained toy model')
    t.add_argument('--n', type=int, default=16)
    t.add_argument('--preset', default='tiny')
    t.add_argument('--seed', type=int, default=0)
    t.add_argument('--json', default=None)
    r = sub.add_parser('report', help='run the harness on a trainer checkpoint')
    r.add_argument('--checkpoint', required=True)
    r.add_argument('--n', type=int, default=128)
    r.add_argument('--stage', default='S1', choices=['S0', 'S1', 'S2'])
    r.add_argument('--json', default=None)
    args = parser.parse_args(argv)
    torch.set_num_threads(1)

    if args.command == 'toy':
        report = _toy(args.n, args.seed, args.preset)
        report['warning'] = ('An UNTRAINED model. These numbers check that the harness '
                             'runs and that the walls hold; they are not a result and no '
                             'mark here means anything.')
    else:
        payload = torch.load(args.checkpoint, map_location='cpu', weights_only=False)
        cfg = M.TalkerConfig(**payload['model_config'])
        model = M.Talker(cfg, gru_mouth=payload['train_config'].get('gru_mouth', False))
        model.load_state_dict(payload['model'])
        turns = L.synthetic_dialogues(args.n, seed=1, vocab_size=cfg.vocab_size,
                                      max_len=min(cfg.max_len, 12)).turns
        thoughts, tokens, codes, _ = thoughts_from_turns(model, turns)
        report = run_interventions(model, thoughts, tokens, codes, stage=args.stage,
                                   label=str(args.checkpoint),
                                   train_stage=payload['train_config'].get('stage'))
    print(json.dumps(report, indent=2))
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
