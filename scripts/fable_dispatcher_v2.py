"""Dispatcher v2: call-cost shaping, evaluation-time interventions, layout variants.

This module IMPORTS `fable_dispatcher` (v1) and reuses its Dispatcher, executor
(`rollout`), candidate features, operators, panel machinery and `score_side`
unchanged.  Only two v1 functions are reproduced here, because they are the two that
had to change:

  * `train`  -- identical to v1's except that the rl arm's LEARNING signal is
                `correct - call_cost * calls` (the RLOO baseline is taken on that
                shaped signal), `mean_shaped` is logged beside the unchanged pure
                `mean_reward`, and `call_cost` is recorded.  With --call-cost 0 the
                shaped signal is bitwise the reward, no extra random number is drawn,
                and the run is bit-identical to v1.
  * `score`  -- identical to v1's for the label-free part (scores.json,
                transcripts.json are produced by the very same code path), plus an
                optional `--score-out` directory, `--diagnose` and
                `--layout-variants`.

Nothing in v1 is modified, monkey-patched or shadowed.

--diagnose is an EVALUATOR-ONLY instrument: it uses the exact interpreter's truth
chain to force one component of the policy at a time.  It never touches the normal
score, which stays label-free.

--layout-variants re-score the SAME frozen questions after harmless re-layouts of the
dispatcher's own input tensor (left padding, right padding, mixed-width batches).  The
executor and the operator see exactly the same (subject token, operation token) calls;
only the dispatcher's input layout moves.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import sys
import time
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fable_dispatcher as V1                                              # noqa: E402

torch = V1.torch
sha = V1.sha
write_new = V1.write_new
CELLS = V1.CELLS
MAX_CALLS = V1.MAX_CALLS
Dispatcher = V1.Dispatcher
OracleOperator = V1.OracleOperator

INTERVENTIONS = ('none', 'force_operation', 'force_subject', 'force_stop',
                 'force_operation+subject')
LAYOUTS = ('baseline', 'left_pad1', 'left_pad2', 'right_pad', 'batch_mixed')


# --------------------------------------------------------------------------- call cost


def shaped_signal(reward, calls, call_cost):
    """The rl arm's learning signal: correctness minus a flat charge per operator call.

    `reward` is the pure correctness indicator (0/1); failed episodes -- invalid action
    or over the four-call cap -- already carry reward 0 and are still charged for the
    calls they executed.  With call_cost == 0 this returns the reward bitwise.
    """
    if call_cost == 0.0:
        return reward
    return reward - call_cost * calls.to(reward.dtype)


# --------------------------------------------------------------------------- training


def train(args):
    """v1.train with the shaped rl signal.  Everything else, including the order and
    the amount of random numbers consumed, is v1's."""
    V1.configure()
    out = Path(args.out)
    if out.exists():
        raise SystemExit(f'refusing to overwrite an existing run directory: {out}')
    out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    record = dict(arm=args.arm, seed=args.seed, updates_requested=args.updates,
                  absolute_positions=bool(args.absolute_positions), operator=str(args.operator),
                  visits_per_update=args.visits, k=args.k, width=args.width,
                  entropy_bonus=[args.entropy, args.entropy_final], lr=args.lr, warmup=args.warmup,
                  clip=args.clip, time_cap=args.time_cap, panels=args.panels,
                  call_cost=float(args.call_cost),
                  reward_shaping=('correct - call_cost * calls (rl learning signal only; '
                                  'mean_reward stays pure correctness)'),
                  source_sha256=sha(__file__), v1_source_sha256=sha(V1.__file__),
                  dispatcher_version='v2',
                  registered_test=bool(args.arm == 'rl'),
                  note=('DIAGNOSTIC CEILING ARM, not the registered test'
                        if args.arm == 'supervised' else 'primary arm: final-answer reward only'))
    updates_done = 0
    log = None
    try:
        forbidden = frozenset()
        if args.panels:
            _, _, forbidden = V1.load_panels(args.panels)
        operator = V1.make_operator(args.operator)
        record['operator_detail'] = operator.describe()
        operator_before = operator.fingerprint
        torch.manual_seed(args.seed)
        model = V1.Dispatcher(width=args.width, absolute_positions=args.absolute_positions)
        record['dispatcher_parameters'] = model.parameters_count()
        print(json.dumps(dict(event='start', arm=args.arm, seed=args.seed,
                              dispatcher_parameters=model.parameters_count(),
                              call_cost=float(args.call_cost),
                              operator=operator.kind)), flush=True)
        optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, betas=(.9, .99), eps=1e-8,
                                      weight_decay=.01)
        rng = random.Random(f'{V1.TRAIN_NAMESPACE}:{args.seed}')
        generator = torch.Generator().manual_seed(9_000_000 + args.seed)
        log = (out / 'train_log.jsonl').open('x')
        window = dict(reward=0., shaped=0., invalid=0., calls=0., entropy=0., updates=0)
        capped = False
        for update in range(args.updates):
            if time.monotonic() - started >= args.time_cap:
                capped = True
                break
            for group in optimizer.param_groups:
                group['lr'] = args.lr * min(1., (update + 1) / max(1, args.warmup))
            inputs, questions, owners, answers = V1.training_visits(rng, args.visits, forbidden)
            reps, visit_of = V1.representatives(owners)
            table = operator.reachable_table(inputs, reps)
            tokens, present = V1.pad_questions(questions)
            if args.arm == 'rl':
                k = args.k
                repeat = torch.arange(len(questions)).repeat_interleave(k)
                episodes = V1.rollout(model, tokens[repeat], present[repeat], table,
                                      visit_of[repeat], mode='sample', generator=generator)
                reward = (episodes.answer == answers[repeat]).float()
                shaped = shaped_signal(reward, episodes.calls, float(args.call_cost))
                advantage = V1.rloo_advantage(shaped, k)
                beta = args.entropy + (args.entropy_final - args.entropy) * \
                    (update / max(1, args.updates - 1))
                mean_entropy = episodes.entropy.sum() / episodes.decisions.sum().clamp_min(1)
                loss = -(advantage.detach() * episodes.logprob).mean() - beta * mean_entropy
            else:
                episodes = V1.rollout(model, tokens, present, table, visit_of, mode='greedy',
                                      gold=V1.gold_actions(questions, tokens.shape[1]))
                reward = (episodes.answer == answers).float()
                shaped = shaped_signal(reward, episodes.calls, float(args.call_cost))
                mean_entropy = episodes.entropy.sum() / episodes.decisions.sum().clamp_min(1)
                loss = -episodes.logprob.mean()
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            norm = torch.nn.utils.clip_grad_norm_(model.parameters(), args.clip)
            if not bool(torch.isfinite(loss)) or not bool(torch.isfinite(norm)):
                raise RuntimeError('nonfinite dispatcher loss or gradient')
            optimizer.step()
            updates_done += 1
            window['updates'] += 1
            window['reward'] += float(reward.mean())
            window['shaped'] += float(shaped.mean())
            window['invalid'] += sum(s == 'invalid_action' for s in episodes.status) / len(episodes.status)
            window['calls'] += float(episodes.calls.float().mean())
            window['entropy'] += float(mean_entropy.detach())
            if updates_done % 100 == 0 or updates_done == 1:
                n = window['updates']
                line = dict(update=updates_done, mean_reward=window['reward'] / n,
                            invalid_fraction=window['invalid'] / n, mean_calls=window['calls'] / n,
                            entropy=window['entropy'] / n, seconds=time.monotonic() - started,
                            # the supervised arm is teacher-forced, so these describe the GOLD
                            # action sequence executed against F, not the arm's own policy
                            teacher_forced=bool(args.arm == 'supervised'),
                            # mean_reward above is PURE correctness; mean_shaped is the rl
                            # arm's learning signal, correct - call_cost * calls
                            mean_shaped=window['shaped'] / n, call_cost=float(args.call_cost))
                log.write(json.dumps(line) + '\n')
                log.flush()
                print(json.dumps(dict(seed=args.seed, arm=args.arm, **line)), flush=True)
                window = dict(reward=0., shaped=0., invalid=0., calls=0., entropy=0., updates=0)
        log.close()
        log = None
        assert operator.fingerprint == operator_before, 'the frozen operator changed during training'
        checkpoint = out / 'dispatcher.pt'
        torch.save(dict(state_dict=model.state_dict(), optimizer=optimizer.state_dict(),
                        torch_rng_state=torch.get_rng_state(), generator_state=generator.get_state(),
                        python_rng_state=rng.getstate(), updates=updates_done, seed=args.seed,
                        arm=args.arm, width=args.width, call_cost=float(args.call_cost),
                        absolute_positions=bool(args.absolute_positions)), checkpoint)
        seconds = time.monotonic() - started
        record.update(updates=updates_done, seconds=seconds,
                      updates_per_second=updates_done / max(1e-9, seconds),
                      checkpoint=str(checkpoint), checkpoint_sha256=sha(checkpoint),
                      operator_fingerprint_before=operator_before,
                      operator_fingerprint_after=operator.fingerprint,
                      operator_weights_unchanged=True, complete=not capped, time_capped=capped,
                      final_update_only=True, no_resume=True, no_checkpoint_selection=True)
        write_new(out / ('failure.json' if capped else 'training.json'), record)
        print(json.dumps(dict(event='done', arm=args.arm, seed=args.seed, updates=updates_done,
                              time_capped=capped, call_cost=float(args.call_cost),
                              updates_per_second=record['updates_per_second'])), flush=True)
    except BaseException as exc:
        if log is not None:
            log.close()
        record.update(updates=updates_done, seconds=time.monotonic() - started, complete=False,
                      time_capped=False, error=repr(exc), traceback=traceback.format_exc())
        path = out / 'failure.json'
        if not path.exists():
            write_new(path, record)
        raise


# --------------------------------------------------------------------------- layouts


def pad_questions_layout(questions, left=0, right=0):
    """v1.pad_questions with `left` not-present slots before and `right` after.

    Padding tokens are id 0 and are marked NOT present, exactly like v1's own
    right-hand padding of a short question in a mixed-width batch.  The executor and
    the operator are untouched: the dispatcher simply cannot point at a padding slot
    (its logits are masked to -inf there), so the (subject token, operation token)
    semantics of every executed call are unchanged.
    """
    inner = max(len(q) for q in questions)
    width = left + inner + right
    tokens = torch.zeros(len(questions), width, dtype=torch.long)
    present = torch.zeros(len(questions), width, dtype=torch.bool)
    for i, q in enumerate(questions):
        tokens[i, left:left + len(q)] = torch.tensor(q, dtype=torch.long)
        present[i, left:left + len(q)] = True
    return tokens, present


def pack_pairs(pairs):
    """Pack an arbitrary list of (unit, side) into one batch of stories and questions."""
    return V1.A.data.pack([unit[side]['memory'] for unit, side in pairs],
                          [unit[side]['question'] for unit, side in pairs],
                          list(range(len(pairs))),
                          [unit[side]['where'] for unit, side in pairs]), \
        [unit[side]['question'] for unit, side in pairs]


def operator_table(operator, pairs, block=32):
    """The operator's lookup table for a list of (unit, side), packed exactly as v1's
    `score_side` packs it: blocks of 32 of the cell's own units.

    Every variant below reuses this table, so the operator always sees byte-identical
    inputs no matter how the DISPATCHER's question tensor is laid out or batched.
    """
    chunks = []
    for start in range(0, len(pairs), block):
        chunk = pairs[start:start + block]
        inputs, _ = pack_pairs(chunk)
        chunks.append(operator.table(inputs, list(range(len(chunk)))))
    return torch.cat(chunks, 0)


# --------------------------------------------------------------------------- interventions


def intervention_policy(kind, hops, width, left=0, base=None):
    """A `rollout` policy callback that forces ONLY the named component(s).

    `hops` is the true chain length of each row, read from the exact interpreter's
    chain -- this is the evaluator-only part.  Components that are not forced are
    returned as None (or as `base`'s choice), which v1's `pick` already honours per
    component: a None component falls through to the model's own greedy argmax.

      force_operation  step t -> question position left+2+min(t, hops-1)
      force_subject    step t -> question position left+1 before any result, then the
                       candidate slot of the MOST RECENT result
      force_stop       step t -> STOP iff t >= hops-1 (CONTINUE until the true length)
    """
    if kind not in INTERVENTIONS:
        raise ValueError(kind)
    do_op = 'operation' in kind
    do_subject = 'subject' in kind
    do_stop = 'stop' in kind
    hops = torch.as_tensor(hops, dtype=torch.long)

    def policy(step, tokens, results, n_results):
        batch = tokens.shape[0]
        if base is None:
            subject = operation = stop = None
        else:
            subject, operation, stop = base(step, tokens, results, n_results)
        here = torch.full((batch,), step, dtype=torch.long)
        if do_subject:
            subject = torch.where(n_results > 0, width + n_results - 1,
                                  torch.full((batch,), left + 1, dtype=torch.long))
        if do_op:
            operation = left + 2 + torch.minimum(here, hops - 1)
        if do_stop:
            stop = (here >= hops - 1).long()
        return subject, operation, stop
    return policy


@torch.no_grad()
def episode_rows(model, pairs, tokens, present, table, visit_of, policy=None):
    """One greedy episode per row, scored against the frozen answer and truth chain."""
    episodes = V1.rollout(model, tokens, present, table, visit_of, mode='greedy', policy=policy)
    rows = []
    for i, (unit, side) in enumerate(pairs):
        transcript = episodes.transcripts[i]
        chain = unit[side]['chain']
        executed = [[s, o] for s, o, _ in transcript]
        rows.append(dict(index=unit['index'], side=side,
                         answer=int(episodes.answer[i]), target=unit[side]['answer'],
                         correct=int(int(episodes.answer[i]) == unit[side]['answer']),
                         full_path=int(executed == [[s, o] for s, o, _ in chain]
                                       and episodes.status[i] == 'answered'),
                         status=episodes.status[i], calls=int(episodes.calls[i]),
                         executed=executed))
    return rows


def aggregate(per_side, n):
    """v1's own convention: a pair unit counts only when BOTH twins are right."""
    sides = list(per_side)
    counts = dict(
        answers=sum(all(per_side[s][i]['correct'] for s in sides) for i in range(n)),
        full_path=sum(all(per_side[s][i]['full_path'] for s in sides) for i in range(n)),
        over_cap=sum(r['status'] == 'over_cap' for s in sides for r in per_side[s]),
        invalid=sum(r['status'] == 'invalid_action' for s in sides for r in per_side[s]),
        rows=sum(len(per_side[s]) for s in sides),
        mean_calls=sum(r['calls'] for s in sides for r in per_side[s])
        / max(1, sum(len(per_side[s]) for s in sides)),
        calls_histogram={str(c): sum(r['calls'] == c for s in sides for r in per_side[s])
                         for c in range(MAX_CALLS + 1)})
    counts['per_side'] = {s: dict(answers=sum(r['correct'] for r in per_side[s]),
                                  full_path=sum(r['full_path'] for r in per_side[s]),
                                  over_cap=sum(r['status'] == 'over_cap' for r in per_side[s]),
                                  invalid=sum(r['status'] == 'invalid_action' for r in per_side[s]))
                          for s in sides}
    return counts


def table_cache(operators, panels):
    """One operator table per (operator, cell, side), shared by the diagnosis and the
    layout variants.  Every variant therefore reads the SAME frozen lookups."""
    store = {}

    def get(label, cell, side):
        key = (label, cell, side)
        if key not in store:
            store[key] = operator_table(operators[label],
                                        [(unit, side) for unit in panels[cell]['units']])
        return store[key]
    return get


def diagnose(model, operators, panels, note, tables):
    """Every panel cell under each evaluation-time intervention, for each operator."""
    out = dict(note=note, interventions=list(INTERVENTIONS),
               definition=dict(
                   force_operation='the correct operation pointer at every step; '
                                   'subject and stop are the model\'s own greedy choices',
                   force_subject='question position 1, then the most recent result; '
                                 'operation and stop free',
                   force_stop='CONTINUE until the true chain length then STOP; others free',
                   **{'force_operation+subject': 'only stopping is free'}),
               source='the truth chain of the exact interpreter, frozen in the panel',
               cells={})
    for cell, panel in panels.items():
        cfg = CELLS[cell]
        units = panel['units']
        sides = ['a'] + (['b'] if cfg['kind'] == 'pair' else [])
        cell_out = {}
        for label in operators:
            batches = {side: ([(unit, side) for unit in units],
                              [unit[side]['question'] for unit in units]) for side in sides}
            rows = {}
            for kind in INTERVENTIONS:
                per_side = {}
                for side in sides:
                    pairs, questions = batches[side]
                    tokens, present = V1.pad_questions(questions)
                    hops = torch.tensor([len(unit[side]['chain']) for unit, _ in pairs],
                                        dtype=torch.long)
                    policy = None if kind == 'none' else intervention_policy(
                        kind, hops, tokens.shape[1])
                    per_side[side] = episode_rows(model, pairs, tokens, present,
                                                  tables(label, cell, side),
                                                  torch.arange(len(pairs)), policy)
                rows[kind] = aggregate(per_side, len(units))
            cell_out[label] = rows
        out['cells'][cell] = dict(n=len(units), sides=len(sides), title=cfg['title'], **cell_out)
        print(json.dumps(dict(diagnose=cell, **{k: dict(answers=v['answers'],
                                                        full_path=v['full_path'],
                                                        over_cap=v['over_cap'])
                                                for k, v in cell_out['trained_operator'].items()})),
              flush=True)
    return out


def layout_variants(model, operators, panels, note, tables):
    """The same questions, re-laid-out in the dispatcher's input tensor only."""
    out = dict(note=note, variants=list(LAYOUTS),
               definition=dict(
                   baseline='the single-cell batch v1 scores',
                   left_pad1='one not-present padding token (id 0) before the question',
                   left_pad2='two not-present padding tokens before the question',
                   right_pad='two not-present padding tokens after [answer]',
                   batch_mixed='the cell scored in one batch with questions of a different '
                               'hop count (d1 units, or d4 units for cell d1), so the tensor '
                               'width and padding differ from the single-cell batch'),
               invariant='the executed (subject token, operation token) pairs must not move',
               cells={})
    partners = {cell: ('d4' if cell == 'd1' else 'd1') for cell in panels}
    for cell, panel in panels.items():
        cfg = CELLS[cell]
        units = panel['units']
        sides = ['a'] + (['b'] if cfg['kind'] == 'pair' else [])
        other = [(unit, 'a') for unit in panels[partners[cell]]['units']]
        cell_out = {}
        for label in operators:
            partner_table = tables(label, partners[cell], 'a')
            base_rows, variant_out = {}, {}
            for variant in LAYOUTS:
                per_side = {}
                for side in sides:
                    pairs = [(unit, side) for unit in units]
                    if variant == 'batch_mixed':
                        # the cell's own rows keep their own operator table rows; only the
                        # dispatcher's batch composition (and therefore its tensor width
                        # and padding) changes
                        mixed, visit, keep = [], [], []
                        for i, pair in enumerate(pairs):
                            keep.append(len(mixed))
                            mixed.append(pair)
                            visit.append(i)
                            mixed.append(other[i % len(other)])
                            visit.append(len(pairs) + (i % len(other)))
                        table = torch.cat((tables(label, cell, side), partner_table), 0)
                        questions = [unit[s]['question'] for unit, s in mixed]
                        tokens, present = pad_questions_layout(questions)
                        rows = episode_rows(model, mixed, tokens, present, table,
                                            torch.tensor(visit, dtype=torch.long))
                        rows = [rows[i] for i in keep]
                    else:
                        questions = [unit[side]['question'] for unit in units]
                        left = {'left_pad1': 1, 'left_pad2': 2}.get(variant, 0)
                        right = 2 if variant == 'right_pad' else 0
                        tokens, present = pad_questions_layout(questions, left, right)
                        rows = episode_rows(model, pairs, tokens, present,
                                            tables(label, cell, side),
                                            torch.arange(len(pairs)))
                    per_side[side] = rows
                counts = aggregate(per_side, len(units))
                if variant == 'baseline':
                    base_rows = {s: [r['executed'] for r in per_side[s]] for s in sides}
                    counts['rows_with_moved_calls'] = 0
                    counts['identical_executed_calls'] = True
                else:
                    moved = sum(r['executed'] != base_rows[s][i]
                                for s in sides for i, r in enumerate(per_side[s]))
                    counts['rows_with_moved_calls'] = moved
                    counts['identical_executed_calls'] = bool(moved == 0)
                variant_out[variant] = counts
            cell_out[label] = variant_out
        out['cells'][cell] = dict(n=len(units), sides=len(sides), partner=partners[cell],
                                  **cell_out)
        print(json.dumps(dict(layout=cell,
                              **{k: dict(answers=v['answers'], moved=v['rows_with_moved_calls'])
                                 for k, v in cell_out['trained_operator'].items()})), flush=True)
    return out


# --------------------------------------------------------------------------- scoring


def score(args):
    """v1.score verbatim for the label-free part, plus --score-out/--diagnose/--layout-variants."""
    V1.configure()
    run = Path(args.run)
    config_path = run / 'training.json'
    if not config_path.exists():
        config_path = run / 'failure.json'
    if not config_path.exists():
        raise SystemExit(f'no training.json or failure.json in {run}')
    config = json.loads(config_path.read_text())
    checkpoint = run / 'dispatcher.pt'
    if not checkpoint.exists():
        raise SystemExit(f'no dispatcher checkpoint in {run}')
    saved = torch.load(checkpoint, map_location='cpu', weights_only=False)
    model = V1.Dispatcher(width=saved['width'], absolute_positions=saved['absolute_positions'])
    model.load_state_dict(saved['state_dict'], strict=True)
    model.eval()
    _manifest, panels, _ = V1.load_panels(args.panels)
    operator = V1.make_operator(args.operator or config.get('operator'))
    oracle = V1.OracleOperator()
    before = operator.fingerprint
    out = Path(args.score_out) if args.score_out else run / 'score'
    out.mkdir(parents=True, exist_ok=False)
    summary = dict(run=str(run), arm=config.get('arm'), seed=config.get('seed'),
                   registered_test=config.get('registered_test'), note=config.get('note'),
                   dispatcher_parameters=model.parameters_count(), updates=config.get('updates'),
                   time_capped=config.get('time_capped'), operator=operator.describe(),
                   panels=str(Path(args.panels).resolve()),
                   panel_manifest_sha256=sha(Path(args.panels) / 'manifest.json'),
                   evaluation='greedy (argmax) episodes, final update only', cells={})
    transcripts = {}
    for cell, panel in panels.items():
        cfg = CELLS[cell]
        units = panel['units']
        sides = ['a'] + (['b'] if cfg['kind'] == 'pair' else [])
        scored = {'trained_operator': {s: V1.score_side(model, operator, units, s) for s in sides},
                  'oracle_operator': {s: V1.score_side(model, oracle, units, s) for s in sides}}
        counts = dict(n=len(units), sides=len(sides))
        for label, rows in scored.items():
            both_correct = [all(rows[s][i]['correct'] for s in sides) for i in range(len(units))]
            identical = [len({rows[s][i]['answer'] for s in sides}) == 1 for i in range(len(units))]
            counts[label] = dict(
                answers=sum(both_correct),
                full_path=sum(all(rows[s][i]['full_path'] for s in sides) for i in range(len(units))),
                identical_twin_answers=sum(identical),
                unit_pass=sum(c and (i or not cfg['invariant'])
                              for c, i in zip(both_correct, identical)),
                invalid=sum(r['status'] == 'invalid_action' for s in sides for r in rows[s]),
                over_cap=sum(r['status'] == 'over_cap' for s in sides for r in rows[s]),
                mean_calls=sum(r['calls'] for s in sides for r in rows[s])
                / max(1, sum(len(rows[s]) for s in sides)))
        trained = scored['trained_operator']
        counts['frozen_operator_on_true_chains'] = dict(
            units_all_steps=sum(all(trained[s][i]['operator_chain_all'] for s in sides)
                                for i in range(len(units))),
            steps_correct=sum(sum(r['operator_chain_hits']) for s in sides for r in trained[s]),
            steps=sum(len(r['operator_chain_hits']) for s in sides for r in trained[s]))
        counts['mark'] = cfg['mark']
        counts['path_mark'] = cfg['path_mark']
        counts['pass'] = bool(counts['trained_operator']['unit_pass'] >= cfg['mark']
                              and (cfg['path_mark'] is None
                                   or counts['trained_operator']['full_path'] >= cfg['path_mark']))
        summary['cells'][cell] = counts
        transcripts[cell] = scored
        print(json.dumps(dict(cell=cell, mark=cfg['mark'], path_mark=cfg['path_mark'],
                              **{k: v for k, v in counts.items()
                                 if k in ('trained_operator', 'oracle_operator',
                                          'frozen_operator_on_true_chains', 'pass')})), flush=True)
    assert operator.fingerprint == before, 'the frozen operator changed during scoring'
    summary['operator_weights_unchanged'] = True
    write_new(out / 'scores.json', summary)
    write_new(out / 'transcripts.json', transcripts)

    note = (args.note or
            ('POST-HOC diagnosis of an already-scored run; the registered score of this run '
             'lives in its own run folder and was not touched'
             if args.score_out else 'diagnosis written beside this run\'s own score'))
    operators = {'trained_operator': operator, 'oracle_operator': oracle}
    tables = table_cache(operators, panels)
    if args.diagnose:
        report = diagnose(model, operators, panels, note, tables)
        report.update(run=str(run), post_hoc=bool(args.score_out),
                      operator=operator.describe(), panels=str(Path(args.panels).resolve()))
        write_new(out / 'diagnosis.json', report)
    if args.layout_variants:
        report = layout_variants(model, operators, panels, note, tables)
        report.update(run=str(run), post_hoc=bool(args.score_out),
                      operator=operator.describe(), panels=str(Path(args.panels).resolve()))
        write_new(out / 'layout.json', report)
    assert operator.fingerprint == before, 'the frozen operator changed during diagnosis'
    write_new(out / 'score_meta.json',
              dict(note=note, post_hoc=bool(args.score_out), run=str(run),
                   score_out=str(out.resolve()), diagnose=bool(args.diagnose),
                   layout_variants=bool(args.layout_variants),
                   dispatcher_version='v2', source_sha256=sha(__file__),
                   v1_source_sha256=sha(V1.__file__),
                   label_free_outputs=['scores.json', 'transcripts.json'],
                   evaluator_only_outputs=['diagnosis.json', 'layout.json'],
                   created_unix=time.time()))
    return summary


# --------------------------------------------------------------------------- CLI


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)

    p = sub.add_parser('train')
    p.add_argument('--arm', choices=('rl', 'supervised'), required=True)
    p.add_argument('--absolute-positions', action='store_true')
    p.add_argument('--operator', required=True, help='"oracle" or a CanonicalOperator checkpoint path')
    p.add_argument('--seed', type=int, required=True)
    p.add_argument('--updates', type=int, default=6000)
    p.add_argument('--out', required=True)
    p.add_argument('--time-cap', type=float, default=1500)
    p.add_argument('--panels', default=None,
                   help='panel directory whose visible semantics the training stream must avoid')
    p.add_argument('--visits', type=int, default=16)
    p.add_argument('--k', type=int, default=8)
    p.add_argument('--width', type=int, default=32)
    p.add_argument('--lr', type=float, default=3e-3)
    p.add_argument('--warmup', type=int, default=100)
    p.add_argument('--clip', type=float, default=1.0)
    p.add_argument('--entropy', type=float, default=.01)
    p.add_argument('--entropy-final', type=float, default=.001)
    p.add_argument('--call-cost', type=float, default=0.0,
                   help='charge per executed operator call in the rl LEARNING signal only')

    p = sub.add_parser('score')
    p.add_argument('--run', required=True)
    p.add_argument('--panels', required=True)
    p.add_argument('--operator', default=None)
    p.add_argument('--score-out', default=None,
                   help='write the score here instead of RUN/score (never inside a registered run)')
    p.add_argument('--diagnose', action='store_true')
    p.add_argument('--layout-variants', action='store_true')
    p.add_argument('--note', default=None)

    args = parser.parse_args(argv)
    if args.command == 'train':
        train(args)
    else:
        score(args)


if __name__ == '__main__':
    main()
