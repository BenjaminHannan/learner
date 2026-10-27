"""Dispatcher v4: LEARN the two bookkeeping features v3 was handed.

The v3 result -- one 15,522-parameter controller trained on 1-3 hop questions in
6-person worlds, scoring >= 59/64 on all 25 frozen cells (k = 1..8, 16 people,
held-out terminal relation, strict paths, k = 5 edited twin pairs) in 3/3 seeds --
rests on two features the executor hands the model for free:

  (1) an "is the most recent result" flag on every transcript candidate, and
  (2) two RELATIVE offsets: (this question position) minus (the previously chosen
      op-pointer position) and minus (the previously chosen subject position),
      clipped to [-3, 3].

Deleting either one collapses k >= 4 to about 4/64.  A reviewer localised the cause
at `fable_dispatcher.py` ~line 635 (`Dispatcher.advance`): the candidate keys of two
repeated LINK tokens are IDENTICAL without the offsets, and the GRU state update
receives the chosen TOKENS and the result but never the chosen POSITIONS, so after
the first LINK the controller has no signal at all that distinguishes "the LINK I
just used" from "the next LINK"; it would have to count through its recurrent state
alone.  In the no-offsets seed-0 checkpoint, forcing the correct OPERATION pointer
takes 4-hop from 6/64 to 64/64, while forcing the subject or the stop bit does not.

v4 keeps the v3 recipe bit-for-bit and offers two LEARNED replacements, each behind
its own flag so they can be tested separately and together.

  A  --learned-register        (replaces the recent-result flag)
     No recency marker exists anywhere: `self.recent` is DELETED from the module and
     the feature is a constant zero that nothing reads.  Instead the controller owns
     a state register r (a width-vector) with a model-controlled write gate.  After
     each call, with `u = [token(result) ; state]`:

         g = sigmoid(register_gate(u))                     # scalar per row, logged
         r = g * tanh(register_write(u)) + (1 - g) * r

     The SUBJECT and OPERATION pointer queries are formed from `state + r` (the stop
     head still reads `state` alone, exactly as in v3).  r starts at a learned
     `register_start`, initialised to zeros, so the very first step of an episode is
     numerically identical to v3's.  The model must learn to keep "the person I am
     standing on" in r itself; nothing in the candidate features says which
     transcript slot is newest, and two result slots holding the same token are
     literally indistinguishable.

  B  --contextual-positions    (replaces the relative offsets)
     No offset feature exists anywhere: `self.offset_op` and `self.offset_subject`
     are DELETED and the offset entries in the feature dict are a constant N/A that
     nothing reads.  Instead a small BIDIRECTIONAL GRU encoder runs over the raw
     question tokens and gives every question position a contextual representation
     ctx[p] = [forward_p ; backward_p] (two GRUCells of width/2, concatenated to
     width, added to the candidate key exactly where the two offset embeddings used
     to be added).  Transcript result slots get the zero vector.  AND -- the
     reviewer's point -- the contextual representations of the two SELECTED
     positions (chosen operation, chosen subject) are fed into the state update:

         step = transcript([tok_s ; tok_o ; tok_r]) + selected([ctx_s ; ctx_o])
         state = GRUCell(step, state)

     so the recurrence finally observes WHERE it pointed, not only WHAT it read.

     Why a recurrent encoder and not learned absolute positions.  An earlier arm with
     per-index position embeddings scored 0/64 at k = 8: index 9 of a question is
     simply never visited when training stops at k = 3, so its embedding keeps its
     random initial value and the pointer logits at that index are noise.  A
     recurrent encoder has no per-index parameter at all -- the same GRUCell weights
     produce position 3 and position 9 -- so the representation of an unseen depth is
     the continuation of a dynamic that WAS trained, not an untrained parameter.
     Concretely, a k-hop question is [4, ENT, LINK * (k-1), REL, 5]; the backward
     state at a LINK position is a function of the suffix, i.e. of how many LINKs
     remain before the terminal relation, and the forward state is a function of how
     many have been passed.  Both are produced by iterating one learned map, and the
     controller's own state advances by iterating one learned map as well, so
     "match the query to the position representation" is a relation that can hold
     past the trained lengths.  This is a real chance, not a guarantee: a GRU can
     saturate, and then depth 4 and depth 8 become indistinguishable.  The
     experiment is exactly the test of whether it does.

ARMS
  v3-repro   neither flag.  MUST reproduce v3's computation exactly -- identical
             parameters from the same seed, identical logits, identical gradients and
             an identical AdamW parameter update on the same batch, tolerance 0.
             `tests/test_fable_dispatcher_v4.py` checks all four.
  reg        A only  (the recent flag is gone, the offsets are kept)
  ctx        B only  (the offsets are gone, the recent flag is kept)
  reg+ctx    both    (neither supplied bookkeeping feature survives)

WRAPPED FROM v1/v3 (imported, never edited, never monkey-patched)
  V1.Dispatcher            subclassed; `DispatcherV4` calls `super().__init__` FIRST,
                           so with no flags every v3 parameter is created, in order,
                           from the same random draws
  V1.FrozenOperator / V1.OracleOperator / V1.make_operator, V1.rloo_advantage,
  V1.pad_questions, V1.representatives, V1.configure, V1.sha, V1.write_new
  V3.build_world / render / true_chain / make_side / interpret / audit_unit,
  V3.CELLS / CELL_ORDER, V3.load_panels, V3.training_visits, V3.train_table,
  V3.prepare_side / TableCache / aggregate, V3.correct_policy,
  V3.intervention_policy / INTERVENTIONS, V3.policy_gradient_loss, V3.shaped_signal

COPIED AND CHANGED (and only these)
  candidate_features_v3 -> `candidate_features_v4`   the two replaced features become
                           inert constants and an optional `context` tensor is added
  rollout_v3            -> `rollout_v4`              carries the register and the
                           question context; logs the gate
  score_side            -> `score_side_v4`           calls `rollout_v4`
  diagnose              -> `diagnose_v4`             calls `score_side_v4`
  train / score         -> `train` / `score`         v4 arms, flags and logging

Everything written here is additive and lives under its own --out directory.  The
registered panels, pass marks and every optimisation hyper-parameter are v3's.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import random
import sys
import time
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fable_dispatcher as V1                                               # noqa: E402
import fable_dispatcher_v3 as V3                                            # noqa: E402

A = V1.A
torch = V1.torch
nn = V1.nn

sha = V1.sha
write_new = V1.write_new
configure = V1.configure
make_operator = V1.make_operator
OracleOperator = V1.OracleOperator
pad_questions = V1.pad_questions
representatives = V1.representatives

CELLS = V3.CELLS
CELL_ORDER = V3.CELL_ORDER
INTERVENTIONS = V3.INTERVENTIONS
ENTITY_MIN, ENTITY_MAX = V1.ENTITY_MIN, V1.ENTITY_MAX
VOCAB = V1.VOCAB
OFFSET_NA, OFFSET_SLOTS = V1.OFFSET_NA, V1.OFFSET_SLOTS
QUESTION, ANSWER, WORLD, LINK = V3.QUESTION, V3.ANSWER, V3.WORLD, V3.LINK

TRAIN_NAMESPACE = 'fable-dispatcher-v4-train'
THROWAWAY_NAMESPACE = 'fable-dispatcher-v4-throwaway'     # never the registered panels
TRAIN_HOPS = V3.TRAIN_HOPS
TRAIN_PEOPLE = V3.TRAIN_PEOPLE
TRAIN_CAP = V3.TRAIN_CAP
EVAL_CAP = V3.EVAL_CAP
QUESTIONS_PER_WORLD = V3.QUESTIONS_PER_WORLD
CELL_MARK = 59                        # the registered v4 pass mark, per cell, per seed

ARMS = ('v3-repro', 'reg', 'ctx', 'reg+ctx')


# --------------------------------------------------------------------------- flags


@dataclass(frozen=True)
class FeatureFlags:
    """Which learned replacement is switched on.

    `learned_register` removes the supplied recency flag; `contextual_positions`
    removes the supplied relative offsets.  Neither flag adds a supplied feature: both
    DELETE one and give the model a mechanism it has to drive itself.
    """
    learned_register: bool = False
    contextual_positions: bool = False

    def as_dict(self):
        return dict(learned_register=self.learned_register,
                    contextual_positions=self.contextual_positions)


def flags_for_arm(arm):
    if arm not in ARMS:
        raise ValueError(f'unknown arm {arm!r}; expected one of {ARMS}')
    return FeatureFlags(learned_register=arm in ('reg', 'reg+ctx'),
                        contextual_positions=arm in ('ctx', 'reg+ctx'))


# --------------------------------------------------------------------------- the model


class DispatcherV4(V1.Dispatcher):
    """v1's dispatcher plus the two optional LEARNED mechanisms.

    Construction order matters and is deliberate: `super().__init__` builds and
    initialises every v3 parameter first, from the same random draws, so with both
    flags off `torch.manual_seed(s); DispatcherV4(width)` and
    `torch.manual_seed(s); V1.Dispatcher(width)` have byte-identical state dicts.
    The replaced embeddings are then DELETED rather than left dead, so no offset and
    no recency parameter can be reached at all in the arms that replace them.

    As in v1, no method here accepts a story, a memory tensor, an eligibility mask, a
    hop count or a question-length scalar.  The only story-derived value that ever
    enters the network is the result TOKEN the executor appends after a call.
    """

    def __init__(self, width=32, learned_register=False, contextual_positions=False):
        super().__init__(width=width, absolute_positions=False)
        self.learned_register = bool(learned_register)
        self.contextual_positions = bool(contextual_positions)
        if width % 2:
            raise ValueError('width must be even: the two encoder directions are width/2 each')
        self.encoder_width = width // 2
        if self.learned_register:
            del self.recent                                    # no recency marker exists
            self.register_start = nn.Parameter(torch.zeros(width))
            self.register_write = nn.Linear(2 * width, width)
            self.register_gate = nn.Linear(2 * width, 1)
            for module in (self.register_write, self.register_gate):
                nn.init.normal_(module.weight, std=.1)
                nn.init.zeros_(module.bias)
        if self.contextual_positions:
            del self.offset_op                                 # no offset feature exists
            del self.offset_subject
            self.encoder_forward = nn.GRUCell(width, self.encoder_width)
            self.encoder_backward = nn.GRUCell(width, self.encoder_width)
            self.encoder_start_forward = nn.Parameter(torch.zeros(self.encoder_width))
            self.encoder_start_backward = nn.Parameter(torch.zeros(self.encoder_width))
            self.selected = nn.Linear(2 * width, width)
            nn.init.normal_(self.selected.weight, std=.1)
            nn.init.zeros_(self.selected.bias)

    # ---------------------------------------------------------------- introspection

    def flags(self):
        return FeatureFlags(learned_register=self.learned_register,
                            contextual_positions=self.contextual_positions)

    def parameter_groups(self):
        """Per-module parameter counts, for the honest 'what did we add' table."""
        groups = {}
        for name, parameter in self.named_parameters():
            groups[name.split('.')[0]] = groups.get(name.split('.')[0], 0) + parameter.numel()
        return dict(sorted(groups.items()))

    def added_parameters(self):
        added = ('register_start', 'register_write', 'register_gate', 'encoder_forward',
                 'encoder_backward', 'encoder_start_forward', 'encoder_start_backward',
                 'selected')
        groups = self.parameter_groups()
        return {k: v for k, v in groups.items() if k in added}

    # ---------------------------------------------------------------- mechanism A

    def initial_register(self, batch):
        if not self.learned_register:
            return None
        return self.register_start.expand(batch, self.width).contiguous()

    def update_register(self, state, register, result):
        """r <- g * tanh(write([token(result) ; state])) + (1 - g) * r, with g logged."""
        joined = torch.cat((self.token(result), state), -1)
        gate = torch.sigmoid(self.register_gate(joined))
        content = torch.tanh(self.register_write(joined))
        return gate * content + (1 - gate) * register, gate.squeeze(-1)

    def pointer_state(self, state, register):
        """The query input for the two pointer heads.  v3 when the register is off."""
        if not self.learned_register:
            return state
        return state + register

    # ---------------------------------------------------------------- mechanism B

    def question_context(self, tokens, present):
        """[B, W, width] contextual representation of every question position.

        Two GRUCells of width/2, one left-to-right and one right-to-left, over the
        same per-token step vectors `question_state` reads.  Padded positions are
        skipped in both directions (padding is a suffix, so the backward pass simply
        starts at the last present position) and their output is zeroed.  There is no
        per-index parameter, which is the whole point.
        """
        if not self.contextual_positions:
            return None
        batch, w = tokens.shape
        e = self.encoder_width
        kind = torch.zeros_like(tokens)
        steps = [self.token(tokens[:, p]) + self.source(kind[:, p]) for p in range(w)]
        state = self.encoder_start_forward.expand(batch, e).contiguous()
        forward = []
        for p in range(w):
            state = torch.where(present[:, p, None], self.encoder_forward(steps[p], state), state)
            forward.append(state)
        state = self.encoder_start_backward.expand(batch, e).contiguous()
        backward = [None] * w
        for p in range(w - 1, -1, -1):
            state = torch.where(present[:, p, None], self.encoder_backward(steps[p], state), state)
            backward[p] = state
        context = torch.stack([torch.cat((forward[p], backward[p]), -1) for p in range(w)], 1)
        return context * present[:, :, None]

    def candidate_context(self, context, cap):
        """The question context widened to the candidate axis; result slots get zeros."""
        if context is None:
            return None
        batch, _w, width = context.shape
        pad = torch.zeros(batch, cap, width, dtype=context.dtype, device=context.device)
        return torch.cat((context, pad), 1)

    # ---------------------------------------------------------------- heads

    def candidate_keys(self, features):
        """v1's key, with each replaced feature's term removed rather than zeroed.

        The addition order is v1's exactly, so with both flags off the result is
        bitwise identical (floating-point addition is not associative).
        """
        base = self.token(features['token']) + self.source(features['source'])
        if not self.learned_register:
            base = base + self.recent(features['recent'])
        if self.contextual_positions:
            base = base + features['context']
        else:
            base = base + self.offset_op(features['offset_op']) \
                + self.offset_subject(features['offset_subject'])
        return self.key(torch.tanh(base))

    def advance_v4(self, state, subject, operation, result, selected_context=None):
        """v1's state update, plus the SELECTED positions' contextual representations."""
        step = self.transcript(torch.cat((self.token(subject), self.token(operation),
                                          self.token(result)), -1))
        if self.contextual_positions:
            if selected_context is None:
                raise ValueError('--contextual-positions needs the selected positions')
            step = step + self.selected(selected_context)
        return self.cell(step, state)


def build_model(width=32, flags=FeatureFlags()):
    return DispatcherV4(width=width, learned_register=flags.learned_register,
                        contextual_positions=flags.contextual_positions)


# --------------------------------------------------------------------------- features


def candidate_features_v4(tokens, present, results, n_results, previous_op, previous_subject,
                          cap, flags=FeatureFlags(), context=None):
    """v3's candidate features with each replaced feature reduced to an inert constant.

    `learned_register`      'recent' is all zeros and no module reads it.
    `contextual_positions`  'offset_op'/'offset_subject' are the N/A slot everywhere and
                            no module reads them; 'context' carries the encoder output.

    The keys are still present in the returned dict so that a test can POISON them and
    show the network's outputs do not move.
    """
    batch, width = tokens.shape
    device = tokens.device
    rows = torch.arange(batch, device=device)
    position = torch.arange(width, device=device)[None].expand(batch, width)
    slot = torch.arange(cap, device=device)[None].expand(batch, cap)
    live = torch.cat((present, slot < n_results[:, None]), 1)
    token = torch.cat((tokens, results), 1) * live
    source = torch.cat((torch.zeros_like(tokens), torch.ones_like(results)), 1)
    if flags.learned_register:
        recent = torch.zeros_like(token)
    else:
        recent = torch.cat((torch.zeros_like(tokens),
                            (slot == (n_results[:, None] - 1)).long()), 1) * live
    features = dict(token=token, source=source, recent=recent, present=live, rows=rows)
    for name, previous in (('offset_op', previous_op), ('offset_subject', previous_subject)):
        if flags.contextual_positions:
            features[name] = torch.full((batch, width + cap), OFFSET_NA, dtype=torch.long,
                                        device=device)
            continue
        offsets = (position - previous[:, None]).clamp(-V1.OFFSET_CLIP, V1.OFFSET_CLIP) \
            + V1.OFFSET_CLIP
        offsets = torch.where((previous >= 0)[:, None], offsets,
                              torch.full_like(offsets, OFFSET_NA))
        features[name] = torch.cat((offsets, torch.full_like(slot, OFFSET_NA)), 1)
    if flags.contextual_positions:
        if context is None:
            raise ValueError('--contextual-positions needs the question context')
        features['context'] = context
    return features


# --------------------------------------------------------------------------- executor


def rollout_v4(model, tokens, present, table, visit_of, cap, *, mode='sample', generator=None,
               policy=None, flags=FeatureFlags(), record=None, gates=None):
    """v3's executor carrying the learned register and the question context.

    With both flags off this is `V3.rollout_v3` line for line: the register is None and
    never touched, `pointer_state` returns `state` itself, the context is None and
    `advance_v4` is `V1.Dispatcher.advance`.  The tests check that claim numerically.

    `gates`, if a list, receives the per-step write-gate values (one scalar per row).
    """
    if flags != model.flags():
        raise ValueError(f'flags {flags.as_dict()} do not match the model {model.flags().as_dict()}')
    batch, width = tokens.shape
    device = tokens.device
    rows = torch.arange(batch, device=device)
    op_index = V1.OP_INDEX.to(device)
    results = torch.zeros(batch, cap, dtype=torch.long, device=device)
    n_results = torch.zeros(batch, dtype=torch.long, device=device)
    previous_op = torch.full((batch,), -1, dtype=torch.long, device=device)
    previous_subject = torch.full((batch,), -1, dtype=torch.long, device=device)
    active = torch.ones(batch, dtype=torch.bool, device=device)
    answer = torch.zeros(batch, dtype=torch.long, device=device)
    calls = torch.zeros(batch, dtype=torch.long, device=device)
    logprob = torch.zeros(batch, device=device)
    entropy = torch.zeros(batch, device=device)
    decisions = torch.zeros(batch, device=device)
    status = ['over_cap'] * batch
    transcripts = [[] for _ in range(batch)]
    pointers = [[] for _ in range(batch)]
    state = model.question_state(tokens, present)
    register = model.initial_register(batch)
    context = model.question_context(tokens, present)
    candidate_context = model.candidate_context(context, cap)

    def pick(logits, forced):
        distribution = torch.distributions.Categorical(logits=logits)
        if mode == 'greedy':
            choice = logits.argmax(-1)
        elif generator is None:
            choice = distribution.sample()
        else:
            choice = torch.multinomial(distribution.probs, 1, generator=generator).squeeze(-1)
        if forced is not None:
            values, mask = forced
            choice = torch.where(mask, values.to(choice.device), choice)
        return choice, distribution.log_prob(choice), distribution.entropy()

    for step in range(cap):
        if not bool(active.any()):
            break
        features = candidate_features_v4(tokens, present, results, n_results, previous_op,
                                         previous_subject, cap, flags, candidate_context)
        slots = features['present']
        keys = model.candidate_keys(features)
        query = model.pointer_state(state, register)
        forced = policy(step, tokens, results, n_results) if policy is not None else {}
        live = active.clone()
        subject_scores = model.subject_logits(query, keys, slots)
        subject, subject_logprob, subject_entropy = pick(subject_scores, forced.get('subject'))
        chosen = keys[rows, subject]
        operation_scores = model.operation_logits(query, chosen, keys, slots)
        operation, operation_logprob, operation_entropy = pick(operation_scores,
                                                               forced.get('operation'))
        subject_token = features['token'][rows, subject]
        operation_token = features['token'][rows, operation]
        logprob = logprob + live * (subject_logprob + operation_logprob)
        entropy = entropy + live * (subject_entropy + operation_entropy)
        decisions = decisions + 2 * live.float()
        legal = (subject_token >= ENTITY_MIN) & (subject_token < ENTITY_MAX) \
            & (op_index[operation_token.clamp(0, VOCAB - 1)] >= 0)
        for index in (live & ~legal).nonzero().flatten().tolist():
            status[index] = 'invalid_action'
            pointers[index].append([int(subject[index]), int(operation[index]), -1])
        active = active & legal
        live = active.clone()
        if not bool(live.any()):
            break
        looked_up = table[visit_of,
                          (subject_token - ENTITY_MIN).clamp(0, ENTITY_MAX - ENTITY_MIN - 1),
                          op_index[operation_token.clamp(0, VOCAB - 1)].clamp(min=0)]
        result = torch.where(live, looked_up, torch.zeros_like(looked_up))
        target = n_results.clamp(max=cap - 1)
        results = results.clone()
        results[rows, target] = torch.where(live, result, results[rows, target])
        n_results = n_results + live.long()
        calls = calls + live.long()
        on_question = subject < width
        previous_subject = torch.where(live, torch.where(on_question, subject,
                                                         torch.full_like(subject, -1)),
                                       previous_subject)
        on_question = operation < width
        previous_op = torch.where(live, torch.where(on_question, operation,
                                                    torch.full_like(operation, -1)), previous_op)
        selected_context = None
        if flags.contextual_positions:
            selected_context = torch.cat((candidate_context[rows, subject],
                                          candidate_context[rows, operation]), -1)
        state = torch.where(live[:, None],
                            model.advance_v4(state, subject_token, operation_token, result,
                                             selected_context), state)
        gate = None
        if flags.learned_register:
            written, gate = model.update_register(state, register, result)
            register = torch.where(live[:, None], written, register)
            if gates is not None:
                gates.append(dict(step=step, active=live.clone(), gate=gate.detach().clone()))
        stop_scores = model.stop_logits(state)
        stop, stop_logprob, stop_entropy = pick(stop_scores, forced.get('stop'))
        if record is not None:
            record.append(dict(step=step, active=live.clone(),
                               subject=subject_scores.detach().clone(),
                               operation=operation_scores.detach().clone(),
                               stop=stop_scores.detach().clone(),
                               state=state.detach().clone(),
                               gate=None if gate is None else gate.detach().clone()))
        logprob = logprob + live * stop_logprob
        entropy = entropy + live * stop_entropy
        decisions = decisions + live.float()
        for index in live.nonzero().flatten().tolist():
            transcripts[index].append([int(subject_token[index]), int(operation_token[index]),
                                       int(result[index])])
            pointers[index].append([int(subject[index]), int(operation[index]), int(stop[index])])
        stopping = live & stop.bool()
        answer = torch.where(stopping, result, answer)
        for index in stopping.nonzero().flatten().tolist():
            status[index] = 'answered'
        active = active & ~stopping
    return V1.Rollout(logprob=logprob, entropy=entropy, decisions=decisions, answer=answer,
                      status=status, calls=calls, transcripts=transcripts, pointers=pointers)


def gate_summary(gates):
    """min / mean / max of every logged write-gate value, and how many were logged."""
    values = []
    for row in gates:
        values.append(row['gate'][row['active']])
    if not values:
        return None
    flat = torch.cat(values)
    if not flat.numel():
        return None
    return dict(n=int(flat.numel()), min=float(flat.min()), mean=float(flat.mean()),
                max=float(flat.max()),
                fraction_above_half=float((flat > .5).float().mean()))


# --------------------------------------------------------------------------- throwaway panels


def throwaway_unit(cell, index, namespace=THROWAWAY_NAMESPACE):
    """V3.make_unit with its own RNG namespace, so a dev/test panel can never be
    confused with -- or overlap -- the frozen registered panels."""
    cfg = CELLS[cell]
    rng = random.Random(f'{namespace}:{cell}:{index}')
    rejections = {}
    hops = cfg['hops']
    while True:
        world = V3.build_world(rng, cfg['people'])
        askers = V3.distinct_askers(world, hops) if cfg['distinct'] else list(world.ents)
        if not askers:
            V3._bump(rejections, 'no_distinct_chain')
            continue
        asker = rng.choice(askers)
        terminal = V3._terminal(rng, cfg['terminal'])
        side_a = V3.make_side(world, asker, hops, terminal)
        if cfg['kind'] == 'single':
            return dict(cell=cell, index=index, kind='single', a=side_a)
        made = V3._edit_world(world, asker, cfg['edit'], rng, rejections, hops, terminal)
        if made is None:
            continue
        edited, detail = made
        if cfg['distinct'] and asker not in V3.distinct_askers(edited, hops):
            continue
        side_b = V3.make_side(edited, asker, hops, terminal)
        if side_b['question'] != side_a['question'] or side_b['where'] != side_a['where']:
            continue
        expected = 1 if cfg['edit'] == 'link' else 2
        if V3.memory_diffs(side_a['memory'], side_b['memory']) != expected:
            continue
        changed = side_b['answer'] != side_a['answer']
        if cfg['invariant'] != (not changed):
            continue
        if sorted(world.attr.values()) != sorted(edited.attr.values()):
            continue
        return dict(cell=cell, index=index, kind='pair', a=side_a, b=side_b, edit_detail=detail)


def throwaway_panels(n=8, namespace=THROWAWAY_NAMESPACE, audit=True):
    """Every cell, n units each, audited exactly as `V3.build_panels` audits them.

    NOT the registered panels: different RNG namespace, never written beside a score,
    never used for a pass/fail claim.
    """
    panels = {}
    for cell in CELL_ORDER:
        units = []
        for index in range(n):
            unit = throwaway_unit(cell, index, namespace)
            if audit:
                problems = V3.audit_unit(unit)
                if problems:
                    raise AssertionError(f'{cell}:{index}: {problems}')
            units.append(unit)
        panels[cell] = dict(cell=cell, n=n, units=units)
    return panels


# --------------------------------------------------------------------------- training


def train(args):
    configure()
    out = Path(args.out)
    if out.exists():
        raise SystemExit(f'refusing to overwrite an existing run directory: {out}')
    out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    hops_choices = V3.parse_hops(args.train_hops)
    flags = flags_for_arm(args.arm)
    record = dict(dispatcher_version='v4', arm=args.arm, seed=args.seed,
                  updates_requested=args.updates, operator=str(args.operator),
                  visits_per_update=args.visits, questions_per_world=QUESTIONS_PER_WORLD,
                  train_hops=list(hops_choices), train_people=args.train_people,
                  train_cap=args.train_cap, k=args.k, width=args.width,
                  entropy_bonus=[args.entropy, args.entropy_final], lr=args.lr,
                  warmup=args.warmup, clip=args.clip, time_cap=args.time_cap, panels=args.panels,
                  call_cost=float(args.call_cost), flags=flags.as_dict(),
                  reward_shaping=('correct - call_cost * calls (rl learning signal only; '
                                  'mean_reward stays pure correctness)'),
                  source_sha256=sha(__file__), v1_source_sha256=sha(V1.__file__),
                  v3_source_sha256=sha(V3.__file__),
                  registered_test=bool(args.arm != 'v3-repro'),
                  note='final-answer reward only; v3 recipe, v4 mechanisms')
    updates_done = 0
    log = None
    try:
        forbidden = frozenset()
        if args.panels:
            _, _, forbidden = V3.load_panels(args.panels)
        operator = make_operator(args.operator)
        record['operator_detail'] = operator.describe()
        operator_before = operator.fingerprint
        torch.manual_seed(args.seed)
        model = build_model(width=args.width, flags=flags)
        record['dispatcher_parameters'] = model.parameters_count()
        record['parameter_groups'] = model.parameter_groups()
        record['added_parameters'] = model.added_parameters()
        record['v3_parameters'] = 15522
        print(json.dumps(dict(event='start', arm=args.arm, seed=args.seed,
                              dispatcher_parameters=model.parameters_count(),
                              added_parameters=model.added_parameters(),
                              train_hops=list(hops_choices), train_people=args.train_people,
                              train_cap=args.train_cap, call_cost=float(args.call_cost),
                              flags=flags.as_dict(), operator=operator.kind)), flush=True)
        optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, betas=(.9, .99), eps=1e-8,
                                      weight_decay=.01)
        rng = random.Random(f'{TRAIN_NAMESPACE}:{args.seed}')
        generator = torch.Generator().manual_seed(9_000_000 + args.seed)
        log = (out / 'train_log.jsonl').open('x')
        blank = lambda: dict(reward=0., shaped=0., invalid=0., over_cap=0., calls=0., entropy=0.,
                             gate=0., gate_high=0., gate_batches=0, updates=0)
        window = blank()
        capped = False
        for update in range(args.updates):
            if time.monotonic() - started >= args.time_cap:
                capped = True
                break
            for group in optimizer.param_groups:
                group['lr'] = args.lr * min(1., (update + 1) / max(1, args.warmup))
            inputs, questions, owners, answers, _meta = V3.training_visits(
                rng, args.visits, args.train_people, hops_choices, forbidden)
            reps, visit_of = representatives(owners)
            table = V3.train_table(operator, inputs, reps, args.train_cap)
            tokens, present = pad_questions(questions)
            k = args.k
            repeat = torch.arange(len(questions)).repeat_interleave(k)
            gates = [] if flags.learned_register else None
            episodes = rollout_v4(model, tokens[repeat], present[repeat], table, visit_of[repeat],
                                  args.train_cap, mode='sample', generator=generator, flags=flags,
                                  gates=gates)
            reward = (episodes.answer == answers[repeat]).float()
            beta = args.entropy + (args.entropy_final - args.entropy) * \
                (update / max(1, args.updates - 1))
            loss, shaped, mean_entropy = V3.policy_gradient_loss(episodes, reward, k,
                                                                 float(args.call_cost), beta)
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
            window['invalid'] += sum(s == 'invalid_action' for s in episodes.status) \
                / len(episodes.status)
            window['over_cap'] += sum(s == 'over_cap' for s in episodes.status) \
                / len(episodes.status)
            window['calls'] += float(episodes.calls.float().mean())
            window['entropy'] += float(mean_entropy.detach())
            if gates is not None:
                summary = gate_summary(gates)
                if summary is not None:
                    window['gate'] += summary['mean']
                    window['gate_high'] += summary['fraction_above_half']
                    window['gate_batches'] += 1
            if updates_done % 100 == 0 or updates_done == 1:
                n = window['updates']
                line = dict(update=updates_done, mean_reward=window['reward'] / n,
                            invalid_fraction=window['invalid'] / n,
                            over_cap_fraction=window['over_cap'] / n,
                            mean_calls=window['calls'] / n, entropy=window['entropy'] / n,
                            seconds=time.monotonic() - started,
                            mean_shaped=window['shaped'] / n, call_cost=float(args.call_cost))
                if window['gate_batches']:
                    line['mean_write_gate'] = window['gate'] / window['gate_batches']
                    line['write_gate_above_half'] = window['gate_high'] / window['gate_batches']
                log.write(json.dumps(line) + '\n')
                log.flush()
                print(json.dumps(dict(seed=args.seed, arm=args.arm, **line)), flush=True)
                window = blank()
        log.close()
        log = None
        assert operator.fingerprint == operator_before, 'the frozen operator changed during training'
        checkpoint = out / 'dispatcher.pt'
        torch.save(dict(state_dict=model.state_dict(), optimizer=optimizer.state_dict(),
                        torch_rng_state=torch.get_rng_state(),
                        generator_state=generator.get_state(), python_rng_state=rng.getstate(),
                        updates=updates_done, seed=args.seed, arm=args.arm, width=args.width,
                        call_cost=float(args.call_cost), train_cap=args.train_cap,
                        train_hops=list(hops_choices), train_people=args.train_people,
                        flags=flags.as_dict()), checkpoint)
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
                              time_capped=capped,
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


# --------------------------------------------------------------------------- scoring


@torch.no_grad()
def score_side_v4(model, operator, units, side, cap, flags=FeatureFlags(), policy_factory=None,
                  block=32, chain_hits=None, prepared=None, gates=None):
    """V3.score_side, calling `rollout_v4`.  Same per-unit record, plus the gate log."""
    out = []
    if prepared is None:
        prepared = V3.prepare_side(operator, units, side, block)
    for block_index, start in enumerate(range(0, len(units), block)):
        chunk = units[start:start + block]
        _inputs, questions, table = prepared[block_index]
        tokens, present = pad_questions(questions)
        policy = None
        if policy_factory is not None:
            hops = torch.tensor([len(unit[side]['chain']) for unit in chunk], dtype=torch.long)
            policy = policy_factory(hops, tokens.shape[1])
        episodes = rollout_v4(model, tokens, present, table, torch.arange(len(chunk)), cap,
                              mode='greedy', policy=policy, flags=flags, gates=gates)
        for i, unit in enumerate(chunk):
            chain = unit[side]['chain']
            transcript = episodes.transcripts[i]
            answered = episodes.status[i] == 'answered'
            hits = None
            if chain_hits is not None:
                hits = chain_hits[side][start + i]
            out.append(dict(index=unit['index'], side=side, answer=int(episodes.answer[i]),
                            target=unit[side]['answer'],
                            correct=int(int(episodes.answer[i]) == unit[side]['answer']),
                            status=episodes.status[i], calls=int(episodes.calls[i]),
                            hops=len(chain), transcript=transcript,
                            pointers=episodes.pointers[i], truth_chain=chain,
                            strict_path=int(transcript == chain and answered),
                            loose_path=int([[s, o] for s, o, _ in transcript]
                                           == [[s, o] for s, o, _ in chain] and answered),
                            operator_chain_hits=hits,
                            operator_chain_all=None if hits is None else int(all(hits))))
    return out


def diagnose_v4(model, operators, panels, cap, flags, note, tables=None):
    """V3.diagnose, calling `score_side_v4`."""
    out = dict(note=note, interventions=list(INTERVENTIONS),
               definition=dict(
                   force_operation='the correct operation pointer at every step INSIDE the '
                                   'true chain; subject and stop are the model\'s own greedy '
                                   'choices, and beyond the true length nothing is forced',
                   force_subject='question position 1, then the most recent result, for steps '
                                 'inside the true chain only; operation and stop free',
                   force_stop='CONTINUE until the true chain length then STOP, for steps inside '
                              'the true chain only; others free',
                   **{'force_operation+subject': 'both pointers forced inside the true chain; '
                                                 'only stopping is free'}),
               note_on_v4=('force_subject points at the most recent result SLOT.  That is an '
                           'evaluator-side instrument, not a model feature: the model itself '
                           'has no recency flag in the --learned-register arms.'),
               source='the truth chain of the exact interpreter, frozen in the panel', cells={})
    if tables is None:
        tables = V3.TableCache(operators)
    # CELL_ORDER order, but only the cells actually supplied (a dev/throwaway panel may
    # hold a subset; the registered score always passes all 25)
    for cell in [name for name in CELL_ORDER if name in panels]:
        cfg = CELLS[cell]
        units = panels[cell]['units']
        sides = ['a'] + (['b'] if cfg['kind'] == 'pair' else [])
        cell_out = {}
        for label, operator in operators.items():
            rows = {}
            for kind in INTERVENTIONS:
                factory = None if kind == 'none' else (
                    lambda hops, width, _k=kind: V3.intervention_policy(_k, hops, width))
                per_side = {s: score_side_v4(model, operator, units, s, cap, flags, factory,
                                             prepared=tables.get(label, cell, units, s))
                            for s in sides}
                rows[kind] = V3.aggregate(per_side, len(units), cfg)
            cell_out[label] = rows
        out['cells'][cell] = dict(n=len(units), sides=len(sides), title=cfg['title'], **cell_out)
        print(json.dumps(dict(diagnose=cell,
                              **{k: dict(answers=v['answers'], strict=v['strict'],
                                         over_cap=v['over_cap'])
                                 for k, v in cell_out['trained_operator'].items()})), flush=True)
    return out


def load_checkpoint(run):
    run = Path(run)
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
    flags = FeatureFlags(**saved['flags'])
    model = build_model(width=saved['width'], flags=flags)
    model.load_state_dict(saved['state_dict'], strict=True)
    model.eval()
    return config, saved, model, flags


def score(args):
    configure()
    run = Path(args.run)
    config, saved, model, flags = load_checkpoint(run)
    manifest, panels, _ = V3.load_panels(args.panels)
    operator = make_operator(args.operator or config.get('operator'))
    oracle = OracleOperator()
    before = operator.fingerprint
    out = Path(args.score_out) if args.score_out else run / 'score'
    out.mkdir(parents=True, exist_ok=False)
    cap = args.eval_cap
    summary = dict(dispatcher_version='v4', run=str(run), arm=config.get('arm'),
                   seed=config.get('seed'), registered_test=config.get('registered_test'),
                   dispatcher_parameters=model.parameters_count(),
                   parameter_groups=model.parameter_groups(),
                   added_parameters=model.added_parameters(), v3_parameters=15522,
                   updates=config.get('updates'), time_capped=config.get('time_capped'),
                   operator=operator.describe(), train_cap=config.get('train_cap'), eval_cap=cap,
                   flags=flags.as_dict(), train_hops=config.get('train_hops'),
                   train_people=config.get('train_people'), call_cost=config.get('call_cost'),
                   cap_note=('no per-slot parameter exists in any v4 arm -- the recency flag is '
                             'gone in the register arms and the contextual encoder has no '
                             'per-index parameter -- so the evaluation cap is free'),
                   panels=str(Path(args.panels).resolve()),
                   panel_manifest_sha256=sha(Path(args.panels) / 'manifest.json'),
                   evaluation='greedy (argmax) episodes, final update only',
                   strict_path='subjects, operations, stop point AND every returned token',
                   loose_path='subjects, operations and stop point only (v1 full_path)',
                   cell_mark=CELL_MARK, cell_order=CELL_ORDER, cells={})
    operators = {'trained_operator': operator, 'oracle_operator': oracle}
    tables = V3.TableCache(operators)
    transcripts = {}
    passes = {}
    for cell in CELL_ORDER:
        cfg = CELLS[cell]
        panel = panels[cell]
        units = panel['units']
        sides = ['a'] + (['b'] if cfg['kind'] == 'pair' else [])
        hits = panel.get('operator_chain_hits')
        gates = [] if flags.learned_register else None
        scored = {'trained_operator': {
            s: score_side_v4(model, operator, units, s, cap, flags, chain_hits=hits,
                             prepared=tables.get('trained_operator', cell, units, s), gates=gates)
            for s in sides},
            'oracle_operator': {
            s: score_side_v4(model, oracle, units, s, cap, flags,
                             prepared=tables.get('oracle_operator', cell, units, s))
            for s in sides}}
        counts = dict(n=len(units), sides=len(sides), hops=cfg['hops'], people=cfg['people'],
                      terminal=cfg['terminal'], kind=cfg['kind'])
        for label, rows in scored.items():
            counts[label] = V3.aggregate(rows, len(units), cfg)
        counts['frozen_operator_on_true_chains'] = manifest['operator_audit'][cell]
        if gates is not None:
            counts['write_gate'] = gate_summary(gates)
        trained = counts['trained_operator']
        passes[cell] = bool(trained['answers'] >= CELL_MARK and trained['strict'] >= CELL_MARK)
        summary['cells'][cell] = counts
        transcripts[cell] = scored
        print(json.dumps(dict(cell=cell, hops=cfg['hops'], passed=passes[cell],
                              trained=dict(answers=trained['answers'], strict=trained['strict'],
                                           over_cap=trained['over_cap']),
                              oracle=dict(answers=counts['oracle_operator']['answers'],
                                          strict=counts['oracle_operator']['strict'],
                                          over_cap=counts['oracle_operator']['over_cap']))),
              flush=True)
    assert operator.fingerprint == before, 'the frozen operator changed during scoring'
    summary['operator_weights_unchanged'] = True
    summary['cell_passes'] = passes
    summary['all_cells_pass'] = bool(all(passes.values()))
    summary['failing_cells'] = [cell for cell in CELL_ORDER if not passes[cell]]
    write_new(out / 'scores.json', summary)
    write_new(out / 'transcripts.json', transcripts)
    note = (args.note or 'diagnosis written beside this run\'s own score')
    if args.diagnose:
        report = diagnose_v4(model, operators, panels, cap, flags, note, tables)
        report.update(run=str(run), eval_cap=cap, operator=operator.describe(),
                      panels=str(Path(args.panels).resolve()))
        write_new(out / 'diagnosis.json', report)
    assert operator.fingerprint == before, 'the frozen operator changed during diagnosis'
    write_new(out / 'score_meta.json',
              dict(dispatcher_version='v4', run=str(run), score_out=str(out.resolve()),
                   eval_cap=cap, diagnose=bool(args.diagnose), flags=flags.as_dict(),
                   source_sha256=sha(__file__), v1_source_sha256=sha(V1.__file__),
                   v3_source_sha256=sha(V3.__file__),
                   label_free_outputs=['scores.json', 'transcripts.json'],
                   evaluator_only_outputs=['diagnosis.json'], created_unix=time.time()))
    return summary


# --------------------------------------------------------------------------- CLI


def parameters_report(width=32):
    rows = {}
    for arm in ARMS:
        torch.manual_seed(0)
        model = build_model(width=width, flags=flags_for_arm(arm))
        rows[arm] = dict(total=model.parameters_count(), added=model.added_parameters(),
                         groups=model.parameter_groups())
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)

    p = sub.add_parser('params', help='parameter counts per arm')
    p.add_argument('--width', type=int, default=32)

    p = sub.add_parser('train')
    p.add_argument('--arm', choices=ARMS, required=True)
    p.add_argument('--operator', required=True,
                   help='"oracle" or a CanonicalOperator checkpoint path')
    p.add_argument('--seed', type=int, required=True)
    p.add_argument('--updates', type=int, default=6000)
    p.add_argument('--out', required=True)
    p.add_argument('--time-cap', type=float, default=1500)
    p.add_argument('--panels', default=None,
                   help='panel directory whose visible semantics the training stream must avoid')
    p.add_argument('--visits', type=int, default=16)
    p.add_argument('--train-hops', default=','.join(str(h) for h in TRAIN_HOPS))
    p.add_argument('--train-people', type=int, default=TRAIN_PEOPLE)
    p.add_argument('--train-cap', type=int, default=TRAIN_CAP)
    p.add_argument('--k', type=int, default=16)
    p.add_argument('--width', type=int, default=32)
    p.add_argument('--lr', type=float, default=3e-3)
    p.add_argument('--warmup', type=int, default=100)
    p.add_argument('--clip', type=float, default=1.0)
    p.add_argument('--entropy', type=float, default=.2)
    p.add_argument('--entropy-final', type=float, default=.02)
    p.add_argument('--call-cost', type=float, default=0.0,
                   help='charge per executed operator call in the rl LEARNING signal only')

    p = sub.add_parser('score')
    p.add_argument('--run', required=True)
    p.add_argument('--panels', required=True)
    p.add_argument('--operator', default=None)
    p.add_argument('--eval-cap', type=int, default=EVAL_CAP)
    p.add_argument('--score-out', default=None)
    p.add_argument('--diagnose', action='store_true')
    p.add_argument('--note', default=None)

    args = parser.parse_args(argv)
    if args.command == 'params':
        print(json.dumps(parameters_report(args.width), indent=2, sort_keys=True), flush=True)
    elif args.command == 'train':
        train(args)
    else:
        score(args)


if __name__ == '__main__':
    main()
