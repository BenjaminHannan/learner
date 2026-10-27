"""Baseline v2 controls: initialization x supporting-line-hint, with per-role metrics
and an explicit lookup-fit gate.

Registered by design/v3/18-baseline-v2-preregistration-draft.md.  Motivated by
design/v3/18-audit-before-fable-continues.md section 1.

WHY THIS FILE EXISTS
--------------------
The audit found NO execution fault in the v1 baseline, but three things that make its
"the baseline cannot learn lookup" reading unsafe:

  1. INITIALIZATION MISMATCH.  The baseline leaves every `nn.Linear` weight at normal
     std 0.02.  The SUCCESSFUL lookup operator draws the same normals and then calls
     `premonition_token_initialization_probe.rescale`, which multiplies each Linear
     weight by `1 / (sqrt(3 * fan_in) * 0.02)` -- i.e. rescales THE SAME DRAWS to std
     `1 / sqrt(3 * fan_in)` (~0.083 at fan-in 48, ~4x larger).  That is an untested
     confound, not a demonstrated cause.
  2. AGGREGATE TOKEN ACCURACY HIDES LOOKUP FAILURE.  END tokens and intermediate
     people carry most of the score, so ~2/3 "token accuracy" coexisted with ~1/10
     one-hop answers.  v2 therefore logs END, intermediate-person, terminal-answer and
     one-hop-answer accuracy SEPARATELY, and treats aggregate token accuracy as
     secondary.
  3. NO FIT PREREQUISITE.  A model that cannot fit ordinary lookup cannot adjudicate
     length composition.  v2 makes that an explicit, per-seed, reported GATE.

ADDITIVE ONLY.  Nothing here edits, monkey-patches or re-runs anything.  v1 is
imported read-only and its hashes are frozen:

  B.BaselineTransformer, B.Block, B.Story, B.pack_stories, B.pack_batch,
  B.output_tokens, B.training_items, B.support_rows, B.evidence_loss,
  B.learning_rate, B.side_items, B.evaluate_side, B.model_emitter, B.END, B.MAX_OUT

and through it V3 (worlds, rendering, questions, true chains, the INDEPENDENT
evaluator-only interpreter `V3.interpret`) and A (the operator's own
`visible_signature` / `tensor_signature`, and `A.I.rescale` itself).

THE OPERATOR'S OWN RESCALE FUNCTION IS USED, NOT A PORT.
`astra_canonical_operator` (already imported transitively by v1, so this costs no new
import and no new side effect) does `import premonition_token_initialization_probe as I`
and builds every canonical operator as `torch.manual_seed(seed); model = ...;
I.rescale(model)`.  `RESCALE` below IS that function object; the test asserts the
identity.  v2 applies it in the same order, so the random DRAWS are identical between
the two init arms of one seed and the arms differ ONLY by the scalar rescaling.

THE 2x2 (design/v3/18-baseline-v2-preregistration-draft.md)
-----------------------------------------------------------
  arm     Linear init                        supporting-line loss
  I0-H0   normal std 0.02                    0
  I0-H1   normal std 0.02                    0.5
  I1-H0   same draws -> std 1/sqrt(3*fan_in) 0
  I1-H1   same draws -> std 1/sqrt(3*fan_in) 0.5      <- PRIMARY, nominated in advance

Seeds 1200/1201/1202, paired across arms; world RNG namespace `astra-baseline-v2-fit`.
Only Linear WEIGHTS are rescaled -- never embeddings, never biases (they are zero).

WHAT IS DELIBERATELY *NOT* HERE
-------------------------------
The draft registers sinusoidal / shared position functions and the untrained
output-index embedding rows as a SEPARATE next diagnostic ("Separate next diagnostic,
not folded into the four arms"), to be designed and frozen after fit succeeds.  So v2
changes NOTHING about positions, depth, width, curriculum, query format or the
embedding decay, and exposes no position flag beyond v1's.

BIT-FOR-BIT v1 PARITY
---------------------
With `--init default --evidence-aux 0 --train-namespace fable-baseline-train`, the v2
training loop is the v1 training loop: same model construction order, same optimizer,
same data stream, same loss graph.  `tests/test_fable_baseline_transformer_v2.py`
trains 5 updates through BOTH entry points and compares every parameter bitwise.
(The registered v2 arms use the draft's `astra-baseline-v2-fit` namespace, which is a
different stream by design -- that is why A-ev cannot be reused as a v2 cell.)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import sys
import time
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fable_baseline_transformer as B                                      # noqa: E402

V3 = B.V3
A = B.A
torch, nn, F = B.torch, B.nn, B.F
sha, write_new, configure = B.sha, B.write_new, B.configure

END, VOCAB, MAX_OUT = B.END, B.VOCAB, B.MAX_OUT
HELDOUT_REL, PRACTISED_RELS = B.HELDOUT_REL, B.PRACTISED_RELS
WIDTH, LAYERS, HEADS, HIDDEN = B.WIDTH, B.LAYERS, B.HEADS, B.HIDDEN
TARGET_PARAMETERS = B.TARGET_PARAMETERS

# THE OPERATOR'S OWN FUNCTION OBJECT -- `astra_canonical_operator.new_model` calls this
# exact callable on every canonical operator.  Not a port.
RESCALE = A.I.rescale
RESCALE_QUALNAME = f'{RESCALE.__module__}.{RESCALE.__name__}'

INIT_CHOICES = ('default', 'operator-rescale')

# arm -> (init, evidence_aux).  The draft's table, verbatim.
ARMS = {
    'I0-H0': ('default', 0.0),
    'I0-H1': ('default', 0.5),
    'I1-H0': ('operator-rescale', 0.0),
    'I1-H1': ('operator-rescale', 0.5),
}
ARM_ORDER = ('I0-H0', 'I0-H1', 'I1-H0', 'I1-H1')
PRIMARY_ARM = 'I1-H1'                      # nominated NOW, before any outcome is read
REGISTERED_SEEDS = (1200, 1201, 1202)
DEV_SEED_FLOOR = 990100                    # development seeds live at or above this

TRAIN_NAMESPACE = 'astra-baseline-v2-fit'  # the draft's world RNG namespace
OVERFIT_NAMESPACE = 'astra-baseline-v2-overfit'

REGISTERED_UPDATES = 6000
REGISTERED_VISITS = 16
REGISTERED_QUESTIONS_PER_WORLD = 4
REGISTERED_PEOPLE = 6
REGISTERED_MODE = 'steps'
REGISTERED_POSITIONS = 'line'
CHUNK_SECONDS = 1200                       # the draft's resumable-chunk ceiling

# --------------------------------------------------------------------------- fit panels

FIT_PEOPLE = 6
FIT_N = 512
PANEL_ATTEMPTS = 256                       # fixed, outcome-independent attempt sequence
FIT_PANEL_NAMESPACE = 'astra-baseline-v2-fit-panel-20260920'
CONFIRM_PANEL_NAMESPACE = 'astra-baseline-v2-confirm-panel-20260920'

FIT_CELLS = {
    'fit-k1-prac': dict(hops=1, terminal='practised',
                        title='1 hop, practised terminal relation, 6 people'),
    'fit-k1-held': dict(hops=1, terminal='heldout',
                        title='1 hop, held-out terminal relation 10, 6 people'),
    'fit-k2-prac': dict(hops=2, terminal='practised',
                        title='2 hops, practised terminal relation, 6 people'),
    'fit-k3-prac': dict(hops=3, terminal='practised',
                        title='3 hops, practised terminal relation, 6 people'),
}
FIT_CELL_ORDER = ('fit-k1-prac', 'fit-k1-held', 'fit-k2-prac', 'fit-k3-prac')
ONE_HOP_CELLS = ('fit-k1-prac', 'fit-k1-held')
COMPOSITION_CELLS = ('fit-k2-prac', 'fit-k3-prac')
# the draft's thresholds, out of FIT_N, on BOTH answers and exact greedy sequences
FIT_GATE = {'fit-k1-prac': 487, 'fit-k1-held': 487, 'fit-k2-prac': 461, 'fit-k3-prac': 461}


# --------------------------------------------------------------------------- init


def build_model(seed, init, *, positions=REGISTERED_POSITIONS, width=WIDTH, layers=LAYERS,
                heads=HEADS, hidden=HIDDEN):
    """`torch.manual_seed` -> construct -> (optionally) rescale, exactly the order
    `astra_canonical_operator.new_model` uses.  The DRAWS are therefore identical for
    both inits at one seed; the arms differ only by the scalar multiply."""
    if init not in INIT_CHOICES:
        raise ValueError(f'unknown init {init!r}')
    torch.manual_seed(seed)
    model = B.BaselineTransformer(positions=positions, width=width, layers=layers,
                                  heads=heads, hidden=hidden)
    if init == 'operator-rescale':
        RESCALE(model)
    return model


def rescale_factor(fan_in):
    """The operator's multiplier: std 0.02 -> std 1/sqrt(3*fan_in)."""
    return 1 / (math.sqrt(3 * fan_in) * .02)


def linear_weights(model):
    return [(name, module) for name, module in model.named_modules()
            if isinstance(module, nn.Linear)]


def fingerprint(model):
    """SHA-256 over every parameter's raw bytes, in sorted name order."""
    digest = hashlib.sha256()
    for name, tensor in sorted(model.state_dict().items()):
        digest.update(name.encode())
        digest.update(tensor.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


def rng_state_fingerprint(rng):
    return hashlib.sha256(repr(rng.getstate()).encode()).hexdigest()


def torch_rng_fingerprint():
    return hashlib.sha256(torch.get_rng_state().numpy().tobytes()).hexdigest()


# --------------------------------------------------------------------------- roles

ROLE_NONE, ROLE_INTERMEDIATE, ROLE_TERMINAL, ROLE_END = 0, 1, 2, 3
ROLE_KEYS = ('intermediate', 'terminal', 'end', 'one_hop_terminal', 'multi_hop_terminal',
             'token', 'sequence', 'one_hop_sequence')


def role_grid(batch):
    """[Q, W] role code per scored position, 0 where the target is -100.

    A `steps` output is `e_1 .. e_{k-1} y END`, written at positions
    `q_len-1 .. q_len-1+k`.  So within the output, index j is an INTERMEDIATE person
    while j < len(o)-2, the TERMINAL answer at j == len(o)-2, and END at j == len(o)-1.
    That is also correct for `answer-only` (o == [y, END]) and for k == 1.
    """
    roles = torch.zeros_like(batch.target)
    for i, out in enumerate(batch.outputs):
        base = int(batch.q_len[i]) - 1
        for j in range(len(out)):
            roles[i, base + j] = (ROLE_INTERMEDIATE if j < len(out) - 2 else
                                  ROLE_TERMINAL if j == len(out) - 2 else ROLE_END)
    roles = roles * batch.target.ne(-100)
    return roles


def hops_vector(items):
    return torch.tensor([int(it['hops']) for it in items], dtype=torch.long)


@torch.no_grad()
def role_counts(logits, batch, roles, hops):
    """Per-role (hits, total).  THE POINT: `token` can no longer hide `terminal`."""
    pred = logits.argmax(-1)
    scored = batch.target.ne(-100)
    hit = pred.eq(batch.target) & scored
    one_hop = hops.eq(1)[:, None]
    masks = dict(intermediate=roles.eq(ROLE_INTERMEDIATE),
                 terminal=roles.eq(ROLE_TERMINAL),
                 end=roles.eq(ROLE_END),
                 one_hop_terminal=roles.eq(ROLE_TERMINAL) & one_hop,
                 multi_hop_terminal=roles.eq(ROLE_TERMINAL) & ~one_hop,
                 token=scored)
    out = {key: (int((hit & mask).sum()), int(mask.sum())) for key, mask in masks.items()}
    exact = (pred.eq(batch.target) | batch.target.eq(-100)).all(-1)
    out['sequence'] = (int(exact.sum()), int(exact.numel()))
    out['one_hop_sequence'] = (int((exact & hops.eq(1)).sum()), int(hops.eq(1).sum()))
    return out


def blank_counts():
    return {key: [0, 0] for key in ROLE_KEYS}


def accumulate(window, counts):
    for key, (hits, total) in counts.items():
        window[key][0] += hits
        window[key][1] += total


def ratios(counts):
    return {f'{key}_accuracy': (hits / total if total else None)
            for key, (hits, total) in counts.items()}


# --------------------------------------------------------------------------- loss


def teacher_forced_loss_v2(model, batch, *, evidence_aux=0., roles=None, hops=None):
    """v1's loss GRAPH, op for op, plus per-role counting under `no_grad`.

    The differentiable part is exactly `fable_baseline_transformer.teacher_forced_loss`:
    same reshape, same `F.cross_entropy(..., ignore_index=-100)`, same
    `loss + evidence_aux * evidence_loss(...)`.  The test asserts BITWISE equality of
    the loss tensor against v1 for evidence_aux in {0, 0.5}, so this duplication
    cannot silently drift.
    """
    logits, weights = model(batch, trace=bool(evidence_aux))
    flat_logits = logits.reshape(-1, logits.shape[-1])
    flat_target = batch.target.reshape(-1)
    loss = F.cross_entropy(flat_logits, flat_target, ignore_index=-100)
    aux = torch.zeros((), dtype=loss.dtype)
    if evidence_aux:
        aux = B.evidence_loss(batch, weights)
        loss = loss + evidence_aux * aux
    counts = role_counts(logits.detach(), batch, roles, hops) if roles is not None else {}
    return loss, float(aux.detach()), counts


# --------------------------------------------------------------------------- exclusions


def read_exclusion(path):
    """A panel directory, or a `forbidden-semantics.json` / `*-semantics.json` file."""
    path = Path(path)
    if path.is_dir():
        path = path / 'forbidden-semantics.json'
    if not path.exists():
        raise SystemExit(f'no exclusion file at {path}')
    return path, frozenset(json.loads(path.read_text()))


def exclusion_union(paths):
    """The FROZEN union of every supplied panel's semantic signatures, plus a record of
    exactly which files it came from.  The draft: "Add every panel signature to
    exclusions"; the validation draft: a collision INVALIDATES the run, it is never
    silently skipped (v1's `training_items` raises, which is the behaviour wanted)."""
    union, sources = set(), []
    for raw in paths or []:
        path, signatures = read_exclusion(raw)
        sources.append(dict(path=str(path.resolve()), sha256=sha(path), count=len(signatures),
                            new=len(signatures - union)))
        union |= signatures
    digest = hashlib.sha256()
    for signature in sorted(union):
        digest.update(signature.encode())
    return frozenset(union), dict(sources=sources, count=len(union), union_sha256=digest.hexdigest())


# --------------------------------------------------------------------------- panels


def fit_terminal(cell, index):
    """Deterministic, outcome-independent.  The practised one-hop cell alternates the
    two practised relations so the EQUAL-RELATION one-hop diagnostic strata the draft
    asks for are exactly balanced (256/256 at n=512)."""
    if FIT_CELLS[cell]['terminal'] == 'heldout':
        return HELDOUT_REL
    return PRACTISED_RELS[index % len(PRACTISED_RELS)]


def build_fit_unit(namespace, cell, index, taken_semantic, taken_tensor, exclusions):
    """One panel unit.  RNG is derived from (namespace, cell, unit index, ATTEMPT index)
    so the whole build is replayable, and every rejection reason is logged."""
    hops = FIT_CELLS[cell]['hops']
    terminal = fit_terminal(cell, index)
    rejections = {}
    for attempt in range(PANEL_ATTEMPTS):
        rng = random.Random(f'{namespace}:{cell}:{index}:{attempt}')
        world = V3.build_world(rng, FIT_PEOPLE)
        askers = list(world.ents) if hops == 1 else V3.distinct_askers(world, hops)
        if not askers:
            rejections['no-distinct-asker'] = rejections.get('no-distinct-asker', 0) + 1
            continue
        asker = rng.choice(askers)
        rows = V3.render(world)
        question = V3.question_tokens(asker, hops, terminal)
        semantic = A.visible_signature(rows, question)
        tensor = A.tensor_signature(rows, question)
        if semantic in exclusions:
            rejections['excluded-signature'] = rejections.get('excluded-signature', 0) + 1
            continue
        if semantic in taken_semantic:
            rejections['duplicate-semantic'] = rejections.get('duplicate-semantic', 0) + 1
            continue
        if tensor in taken_tensor:
            rejections['duplicate-tensor'] = rejections.get('duplicate-tensor', 0) + 1
            continue
        chain, people = V3.true_chain(world, asker, hops, terminal)
        side = dict(memory=[list(row) for row in rows] + [[]], question=question,
                    where=len(rows), answer=chain[-1][2], chain=chain, people=people,
                    terminal=terminal, hops=hops,
                    distinct=bool(len(set(people)) == len(people)))
        # independent evaluator-only interpreter must reproduce the chain
        got = V3.interpret(side['memory'], V3.side_eligible(side), question)
        if [list(step) for step in got] != [list(step) for step in chain]:
            raise RuntimeError(f'{cell}:{index}: independent interpreter disagrees with the chain')
        if hops >= 2 and len(set(people)) != hops:
            raise RuntimeError(f'{cell}:{index}: multi-hop chain is not pairwise distinct')
        if hops >= 2 and terminal == HELDOUT_REL:
            raise RuntimeError(f'{cell}:{index}: relation 10 must not be a multi-hop terminal')
        unit = dict(a=side, kind='single', cell=cell, index=index, attempt=attempt,
                    terminal=terminal, hops=hops)
        return unit, semantic, tensor, rejections
    raise RuntimeError(f'{cell}:{index}: exhausted {PANEL_ATTEMPTS} attempts')


def build_fit_panels(out, namespace, n, exclude):
    configure()
    folder = Path(out)
    folder.mkdir(parents=True, exist_ok=False)
    exclusions, exclusion_record = exclusion_union(exclude)
    manifest = dict(created_unix=time.time(), namespace=namespace, n=n, people=FIT_PEOPLE,
                    cell_order=list(FIT_CELL_ORDER), gate=dict(FIT_GATE),
                    panel_attempts=PANEL_ATTEMPTS,
                    source_sha256=sha(__file__), v1_source_sha256=sha(B.__file__),
                    v3_source_sha256=sha(V3.__file__),
                    frozen_before_any_v2_training=True,
                    exclusion_inputs=exclusion_record,
                    rejection_rule=('fixed attempt sequence 0..255 per unit; a unit is rejected '
                                    'only for: no pairwise-distinct asker, a signature in the '
                                    'frozen exclusion union, or a duplicate semantic/tensor '
                                    'signature.  No model, no correctness, no confidence.'),
                    cells={})
    semantic_all, tensor_all, rejections_all = set(), set(), {}
    for cell in FIT_CELL_ORDER:
        cfg = FIT_CELLS[cell]
        units, rejections, relations = [], {}, {}
        for index in range(n):
            unit, semantic, tensor, reasons = build_fit_unit(
                namespace, cell, index, semantic_all, tensor_all, exclusions)
            for key, value in reasons.items():
                rejections[key] = rejections.get(key, 0) + value
            semantic_all.add(semantic)
            tensor_all.add(tensor)
            relations[unit['terminal']] = relations.get(unit['terminal'], 0) + 1
            units.append(unit)
        if cfg['terminal'] == 'practised' and cfg['hops'] == 1:
            counts = sorted(relations.values())
            if len(set(counts)) != 1:
                raise RuntimeError(f'{cell}: one-hop practised strata are not equal: {relations}')
        for key, value in rejections.items():
            rejections_all[key] = rejections_all.get(key, 0) + value
        path = folder / f'{cell}.json'
        write_new(path, dict(cell=cell, n=n, namespace=namespace, people=FIT_PEOPLE,
                             hops=cfg['hops'], terminal=cfg['terminal'], title=cfg['title'],
                             gate=FIT_GATE[cell], relation_strata={str(k): v
                                                                   for k, v in relations.items()},
                             rejections=rejections, units=units))
        manifest['cells'][cell] = dict(path=str(path), sha256=sha(path), n=n, hops=cfg['hops'],
                                       terminal=cfg['terminal'], title=cfg['title'],
                                       gate=FIT_GATE[cell],
                                       relation_strata={str(k): v for k, v in relations.items()},
                                       rejections=rejections)
        print(json.dumps(dict(cell=cell, n=n, relations={str(k): v for k, v in relations.items()},
                              rejections=rejections)), flush=True)
    forbidden = folder / 'forbidden-semantics.json'
    write_new(forbidden, sorted(semantic_all))
    manifest.update(exclusion_path=str(forbidden), exclusion_sha256=sha(forbidden),
                    exclusion_count=len(semantic_all), unique_tensor_inputs=len(tensor_all),
                    duplicate_or_overlap_failures=0, rejections=rejections_all,
                    all_audits_passed=True)
    write_new(folder / 'manifest.json', manifest)
    summary = dict(panels=str(folder.resolve()), namespace=namespace, cells=len(FIT_CELL_ORDER),
                   n=n, exclusion_count=len(semantic_all), unique_tensor_inputs=len(tensor_all),
                   manifest_sha256=sha(folder / 'manifest.json'))
    print(json.dumps(summary), flush=True)
    return summary


def load_fit_panels(panels):
    folder = Path(panels)
    manifest = json.loads((folder / 'manifest.json').read_text())
    loaded = {}
    for cell, row in manifest['cells'].items():
        path = folder / f'{cell}.json'
        if sha(path) != row['sha256']:
            raise RuntimeError(f'panel changed on disk: {path}')
        loaded[cell] = json.loads(path.read_text())
    forbidden = folder / 'forbidden-semantics.json'
    if sha(forbidden) != manifest['exclusion_sha256']:
        raise RuntimeError('forbidden-semantics.json changed on disk')
    return manifest, loaded, frozenset(json.loads(forbidden.read_text()))


# --------------------------------------------------------------------------- train


def resolve_arm(args):
    if args.arm:
        if args.init is not None or args.evidence_aux is not None:
            raise SystemExit('pass --arm OR (--init and --evidence-aux), not both')
        return args.arm, *ARMS[args.arm]
    init = args.init or 'default'
    aux = 0. if args.evidence_aux is None else float(args.evidence_aux)
    named = [name for name, (i, a) in ARMS.items() if i == init and a == aux]
    return (named[0] if named else None), init, aux


def train(args):
    configure()
    arm, init, evidence_aux = resolve_arm(args)
    out = Path(args.out)
    if out.exists():
        raise SystemExit(f'refusing to overwrite an existing run directory: {out}')
    out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    exclusions, exclusion_record = exclusion_union(args.exclude)
    record = dict(baseline='fable-baseline-transformer-v2',
                  registration='design/v3/18-baseline-v2-preregistration-draft.md',
                  arm=arm, init=init, evidence_aux=evidence_aux,
                  init_rule=('operator-rescale multiplies EVERY nn.Linear weight by '
                             '1/(sqrt(3*fan_in)*0.02), i.e. the same normal draws rescaled to '
                             'std 1/sqrt(3*fan_in); embeddings and biases untouched'),
                  rescale_function=RESCALE_QUALNAME,
                  rescale_is_operator_function=bool(RESCALE is A.I.rescale),
                  mode=args.mode, positions=args.positions, seed=args.seed,
                  train_namespace=args.train_namespace,
                  registered_seeds=list(REGISTERED_SEEDS),
                  registered_seed=bool(args.seed in REGISTERED_SEEDS),
                  primary_arm=PRIMARY_ARM, arm_is_primary=bool(arm == PRIMARY_ARM),
                  updates_requested=args.updates, visits_per_update=args.visits,
                  questions_per_world=args.questions_per_world,
                  train_hops=list(B.TRAIN_HOPS), train_people=args.train_people,
                  lr=args.lr, lr_final=args.lr_final, warmup=args.warmup, clip=args.clip,
                  weight_decay=args.weight_decay, betas=[.9, .99], eps=1e-8, dropout=0.,
                  time_cap=args.time_cap, chunk_seconds_ceiling=CHUNK_SECONDS,
                  end_token=END, vocab=VOCAB, max_output_tokens=MAX_OUT,
                  exclusions=exclusion_record,
                  source_sha256=sha(__file__), v1_source_sha256=sha(B.__file__),
                  v3_source_sha256=sha(V3.__file__),
                  supervision_note=(
                      'steps mode receives the gold intermediate entities as output targets. '
                      'The H1 arms additionally receive v1\'s supporting-line attention loss at '
                      'coefficient 0.5 on the LAST layer\'s head-mean attention at every '
                      'result-predicting position, END excluded -- analogous to, NOT identical '
                      'to, the operator\'s allocation of evidence loss across three reads.'),
                  position_note=(
                      'positions, depth, width, curriculum and query format are UNCHANGED from '
                      'v1.  The draft registers sinusoidal/shared position functions and the '
                      'untrained output-index rows as a SEPARATE later diagnostic, so nothing '
                      'about them is implemented or varied here.'))
    updates_done, log = 0, None
    try:
        model = build_model(args.seed, init, positions=args.positions, width=args.width,
                            layers=args.layers, heads=args.heads, hidden=args.hidden)
        total = model.parameters_count()
        record.update(parameters=total, parameter_target=TARGET_PARAMETERS,
                      parameter_ratio=total / TARGET_PARAMETERS, config=model.config(),
                      initial_weight_fingerprint=fingerprint(model),
                      torch_rng_after_init_sha256=torch_rng_fingerprint())
        optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, betas=(.9, .99), eps=1e-8,
                                      weight_decay=args.weight_decay)
        rng = random.Random(f'{args.train_namespace}:{args.seed}')
        record.update(data_rng_initial_state_sha256=rng_state_fingerprint(rng))
        print(json.dumps(dict(event='start', arm=arm, init=init, evidence_aux=evidence_aux,
                              seed=args.seed, parameters=total,
                              parameter_ratio=round(total / TARGET_PARAMETERS, 4),
                              initial_weight_fingerprint=record['initial_weight_fingerprint'],
                              exclusion_count=exclusion_record['count'])), flush=True)
        log = (out / 'train_log.jsonl').open('x')
        window, window_updates = blank_counts(), 0
        window_loss = window_aux = window_norm = 0.
        flops, capped, padded_tokens, real_tokens = 0., False, 0, 0
        for update in range(args.updates):
            if time.monotonic() - started >= args.time_cap:
                capped = True
                break
            for group in optimizer.param_groups:
                group['lr'] = B.learning_rate(args.lr, update, args.updates, args.warmup,
                                              args.lr_final)
            stories, items = B.training_items(rng, args.visits, args.train_people, B.TRAIN_HOPS,
                                              exclusions, args.questions_per_world,
                                              support=bool(evidence_aux))
            batch = B.pack_batch(stories, items, args.mode, support=bool(evidence_aux))
            flops += model.flops(batch.story, tuple(batch.seq.shape), backward=True)
            padded_tokens += (batch.story.rows.numel() if args.positions == 'line'
                              else batch.story.flat.numel())
            real_tokens += int(batch.story.lens.sum())
            loss, aux, counts = teacher_forced_loss_v2(
                model, batch, evidence_aux=evidence_aux,
                roles=role_grid(batch), hops=hops_vector(items))
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            norm = torch.nn.utils.clip_grad_norm_(model.parameters(), args.clip)
            if not bool(torch.isfinite(loss)) or not bool(torch.isfinite(norm)):
                raise RuntimeError('nonfinite baseline loss or gradient')
            optimizer.step()
            updates_done += 1
            window_updates += 1
            window_loss += float(loss.detach())
            window_aux += aux
            window_norm += float(norm)
            accumulate(window, counts)
            if updates_done % args.log_every == 0 or updates_done == 1:
                n = window_updates
                line = dict(update=updates_done, loss=window_loss / n, evidence=window_aux / n,
                            grad_norm=window_norm / n,
                            lr=optimizer.param_groups[0]['lr'],
                            seconds=time.monotonic() - started, flops=flops,
                            **ratios(window),
                            counts={k: list(v) for k, v in window.items()})
                log.write(json.dumps(line) + '\n')
                log.flush()
                print(json.dumps(dict(seed=args.seed, arm=arm, **{
                    k: v for k, v in line.items() if k != 'counts'})), flush=True)
                window, window_updates = blank_counts(), 0
                window_loss = window_aux = window_norm = 0.
        log.close()
        log = None
        checkpoint = out / 'baseline.pt'
        torch.save(dict(state_dict=model.state_dict(), config=model.config(), mode=args.mode,
                        seed=args.seed, updates=updates_done, arm=arm, init=init,
                        evidence_aux=evidence_aux,
                        train_namespace=args.train_namespace), checkpoint)
        seconds = time.monotonic() - started
        record.update(updates=updates_done, seconds=seconds,
                      updates_per_second=updates_done / max(1e-9, seconds),
                      training_flops=flops,
                      training_flops_per_update=flops / max(1, updates_done),
                      padded_story_tokens_per_update=padded_tokens / max(1, updates_done),
                      real_story_tokens_per_update=real_tokens / max(1, updates_done),
                      flop_convention=('matmul only, 2 FLOPs per MAC, x3 for forward+backward; '
                                       'embeddings/softmax/norm/optimiser excluded; padded '
                                       'positions charged because they are executed'),
                      final_weight_fingerprint=fingerprint(model),
                      checkpoint=str(checkpoint), checkpoint_sha256=sha(checkpoint),
                      complete=not capped, time_capped=capped, final_update_only=True,
                      no_resume=True, no_checkpoint_selection=True,
                      incomplete_note=('a time cap is INCOMPLETE ("under-trained -- '
                                       'inconclusive"), never an architecture failure'))
        write_new(out / ('incomplete.json' if capped else 'training.json'), record)
        print(json.dumps(dict(event='done', seed=args.seed, arm=arm, updates=updates_done,
                              time_capped=capped, seconds=seconds,
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


# --------------------------------------------------------------------------- fit gate


def cell_items(panel):
    return B.side_items(panel['units'], 'a')


@torch.no_grad()
def teacher_forced_panel(model, stories, items, mode, block=64):
    total = blank_counts()
    for start in range(0, len(items), block):
        chunk = [dict(it, owner=it['owner'] - start) for it in items[start:start + block]]
        batch = B.pack_batch(stories[start:start + block], chunk, mode)
        logits, _ = model(batch)
        accumulate(total, role_counts(logits, batch, role_grid(batch), hops_vector(chunk)))
    return total


def fit_inference_flops(model, panels, block=32):
    """Greedy cost at the worst case of MAX_OUT decode steps, mirroring
    `fable_baseline_transformer.inference_flops`."""
    total = 0.
    for cell in FIT_CELL_ORDER:
        stories, items = cell_items(panels[cell])
        for start in range(0, len(items), block):
            chunk = items[start:start + block]
            story = B.pack_stories(stories[start:start + block])
            width = max(len(it['question']) for it in chunk)
            total += model.story_flops(story, backward=False)
            for step in range(MAX_OUT):
                total += model.stream_flops(story.flat.shape[1], len(chunk), width + step,
                                            backward=False)
    return total


def gate_report(cells):
    """The draft's prerequisite, split so the audit's demand is explicit:

      one_hop_lookup_gate  -- ordinary lookup succeeds (both k=1 cells at 487/512 on
                              BOTH answers and exact greedy sequences).  Until this is
                              true for a seed, NO failure of that seed may be used to
                              argue anything about length composition.
      fit_gate             -- the full prerequisite: the above PLUS practised k=2 and
                              k=3 at 461/512 on both.
    """
    per_cell = {}
    for cell in FIT_CELL_ORDER:
        row = cells[cell]
        need = FIT_GATE[cell]
        per_cell[cell] = dict(n=row['n'], need=need, answers=row['answers'], strict=row['strict'],
                              answers_pass=bool(row['answers'] >= need),
                              strict_pass=bool(row['strict'] >= need),
                              passed=bool(row['answers'] >= need and row['strict'] >= need))
    one_hop = all(per_cell[c]['passed'] for c in ONE_HOP_CELLS)
    return dict(cells=per_cell,
                one_hop_lookup_gate=bool(one_hop),
                composition_cells_pass=bool(all(per_cell[c]['passed'] for c in COMPOSITION_CELLS)),
                fit_gate=bool(all(per_cell[c]['passed'] for c in FIT_CELL_ORDER)),
                composition_claims_licensed=bool(one_hop),
                note=('failure means "lookup/sequence fit prerequisite failed under this '
                      'recipe", NOT "more training would necessarily fix it"; no averaging '
                      'across seeds and no seed substitution'))


def relation_strata(items, results):
    out = {}
    for item, row in zip(items, results):
        key = str(int(item['chain'][-1][1]))
        bucket = out.setdefault(key, dict(n=0, answers=0, strict=0))
        bucket['n'] += 1
        bucket['answers'] += int(row['correct'])
        bucket['strict'] += int(row['strict_path'])
    return out


def fit(args):
    configure()
    run = Path(args.run)
    config_path = next((run / name for name in ('training.json', 'incomplete.json', 'failure.json')
                        if (run / name).exists()), None)
    if config_path is None:
        raise SystemExit(f'no training.json / incomplete.json / failure.json in {run}')
    config = json.loads(config_path.read_text())
    checkpoint = run / 'baseline.pt'
    if not checkpoint.exists():
        raise SystemExit(f'no baseline checkpoint in {run}')
    saved = torch.load(checkpoint, map_location='cpu', weights_only=False)
    model = B.BaselineTransformer(**saved['config'])
    model.load_state_dict(saved['state_dict'], strict=True)
    model.eval()
    manifest, panels, _ = load_fit_panels(args.panels)
    if manifest['namespace'] != FIT_PANEL_NAMESPACE and not args.confirmation:
        raise SystemExit(f'panel namespace {manifest["namespace"]!r} is not the development-fit '
                         f'namespace; pass --confirmation only for a fit-qualified configuration')
    out = Path(args.out) if args.out else run / ('confirm' if args.confirmation else 'fit')
    out.mkdir(parents=True, exist_ok=False)
    mode = saved['mode']
    emit = B.model_emitter(model, args.block)
    started = time.monotonic()
    cells, strata, transcripts, tokens = {}, {}, {}, {}
    for cell in FIT_CELL_ORDER:
        stories, items = cell_items(panels[cell])
        results = B.evaluate_side(items, emit(stories, items), mode)
        n = len(items)
        cells[cell] = dict(n=n, hops=panels[cell]['hops'], terminal=panels[cell]['terminal'],
                           title=panels[cell]['title'], need=FIT_GATE[cell],
                           answers=sum(r['correct'] for r in results),
                           strict=sum(r['strict_path'] for r in results),
                           no_end=sum(1 - r['end_emitted'] for r in results),
                           mean_output_tokens=sum(r['output_tokens'] for r in results) / max(1, n))
        strata[cell] = relation_strata(items, results)
        transcripts[cell] = results
        counts = teacher_forced_panel(model, stories, items, mode, args.block)
        tokens[cell] = dict(counts={k: list(v) for k, v in counts.items()}, **ratios(counts))
        print(json.dumps(dict(cell=cell, **{k: cells[cell][k] for k in
                                            ('n', 'need', 'answers', 'strict', 'no_end')},
                              terminal_accuracy=tokens[cell]['terminal_accuracy'],
                              end_accuracy=tokens[cell]['end_accuracy'])), flush=True)
    gate = gate_report(cells)
    seconds = time.monotonic() - started
    report = dict(baseline='fable-baseline-transformer-v2',
                  registration='design/v3/18-baseline-v2-preregistration-draft.md',
                  run=str(run), arm=saved.get('arm'), init=saved.get('init'),
                  evidence_aux=saved.get('evidence_aux'), seed=saved.get('seed'),
                  registered_seed=bool(saved.get('seed') in REGISTERED_SEEDS),
                  train_namespace=saved.get('train_namespace'),
                  updates=config.get('updates'), time_capped=config.get('time_capped'),
                  complete=config.get('complete'),
                  training_seconds=config.get('seconds'),
                  training_flops=config.get('training_flops'),
                  checkpoint_sha256=sha(checkpoint),
                  panels=str(Path(args.panels).resolve()),
                  panel_namespace=manifest['namespace'],
                  panel_manifest_sha256=sha(Path(args.panels) / 'manifest.json'),
                  is_confirmation_panel=bool(args.confirmation),
                  evaluation='greedy (argmax) decoding, FINAL checkpoint only, no selection',
                  cell_order=list(FIT_CELL_ORDER), cells=cells,
                  one_hop_relation_strata={c: strata[c] for c in ONE_HOP_CELLS},
                  relation_strata=strata,
                  teacher_forced=tokens,
                  gate=gate,
                  inference_flops=fit_inference_flops(model, panels, args.block),
                  scoring_seconds=seconds,
                  source_sha256=sha(__file__), v1_source_sha256=sha(B.__file__),
                  created_unix=time.time())
    write_new(out / 'fit.json', report)
    write_new(out / 'transcripts.json', transcripts)
    print(json.dumps(dict(event='gate', seed=saved.get('seed'), arm=saved.get('arm'),
                          one_hop_lookup_gate=gate['one_hop_lookup_gate'],
                          fit_gate=gate['fit_gate'])), flush=True)
    return report


# --------------------------------------------------------------------------- overfit


def overfit_once(init, batch, roles, hops, args, seed):
    """Can this init memorise a TINY FIXED batch?  The audit's suggested implementation
    check: it separates a remaining expressivity/optimization difficulty from an
    evaluation bug.  It certifies nothing about generalization."""
    model = build_model(seed, init, positions=args.positions, width=args.width,
                        layers=args.layers, heads=args.heads, hidden=args.hidden)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, betas=(.9, .99), eps=1e-8,
                                  weight_decay=args.weight_decay)
    started = time.monotonic()
    memorised_at, trace, last, applied = None, [], None, 0
    # `counts` is always measured BEFORE this iteration's optimizer step, so `applied`
    # is the number of updates that had already been taken when it was observed.
    for update in range(args.max_updates + 1):
        loss, aux, counts = teacher_forced_loss_v2(model, batch, evidence_aux=args.evidence_aux,
                                                   roles=roles, hops=hops)
        last, applied = counts, update
        if update % args.log_every == 0 or update == args.max_updates:
            trace.append(dict(updates_applied=update, loss=float(loss.detach()), **ratios(counts)))
        if counts['sequence'][0] == counts['sequence'][1]:
            memorised_at = update
            break
        if update == args.max_updates:
            break
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), args.clip)
        optimizer.step()
    return dict(init=init, seed=seed, memorised=bool(memorised_at is not None),
                updates_to_memorise=memorised_at, updates_applied=applied,
                max_updates=args.max_updates,
                seconds=time.monotonic() - started,
                final=dict(counts={k: list(v) for k, v in last.items()}, **ratios(last)),
                trace=trace)


def overfit(args):
    configure()
    if args.seed < DEV_SEED_FLOOR and not args.allow_registered_seed:
        raise SystemExit(f'overfit is a development check: use a seed >= {DEV_SEED_FLOOR} '
                         f'(got {args.seed})')
    out = Path(args.out)
    if out.exists():
        raise SystemExit(f'refusing to overwrite an existing directory: {out}')
    out.mkdir(parents=True, exist_ok=False)
    exclusions, exclusion_record = exclusion_union(args.exclude)
    rng = random.Random(f'{OVERFIT_NAMESPACE}:{args.seed}')
    stories, items = B.training_items(rng, args.worlds, args.train_people, B.TRAIN_HOPS,
                                      exclusions, args.questions_per_world,
                                      support=bool(args.evidence_aux))
    batch = B.pack_batch(stories, items, args.mode, support=bool(args.evidence_aux))
    roles, hops = role_grid(batch), hops_vector(items)
    inits = INIT_CHOICES if args.init == 'both' else (args.init,)
    results = [overfit_once(init, batch, roles, hops, args, args.seed) for init in inits]
    for row in results:
        print(json.dumps({k: v for k, v in row.items() if k != 'trace'}), flush=True)
    report = dict(check='baseline-v2 tiny-fixed-batch overfit',
                  registration='design/v3/18-baseline-v2-preregistration-draft.md',
                  audit='design/v3/18-audit-before-fable-continues.md section 1',
                  namespace=OVERFIT_NAMESPACE, seed=args.seed, worlds=args.worlds,
                  questions_per_world=args.questions_per_world, questions=len(items),
                  train_people=args.train_people, hops=list(B.TRAIN_HOPS), mode=args.mode,
                  positions=args.positions, evidence_aux=args.evidence_aux,
                  max_updates=args.max_updates, lr=args.lr, weight_decay=args.weight_decay,
                  clip=args.clip, exclusions=exclusion_record,
                  rescale_function=RESCALE_QUALNAME, results=results,
                  interpretation=('memorising a fixed finite batch shows the architecture and '
                                  'optimizer CAN fit these targets; it is not evidence of '
                                  'generalization, and failure to memorise indicates a '
                                  'remaining expressivity/optimization difficulty or a bug'),
                  source_sha256=sha(__file__), v1_source_sha256=sha(B.__file__),
                  created_unix=time.time())
    write_new(out / 'overfit.json', report)
    return report


# --------------------------------------------------------------------------- CLI


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)

    p = sub.add_parser('train')
    p.add_argument('--arm', choices=ARM_ORDER, default=None,
                   help='the draft\'s 2x2 cell; sets --init and --evidence-aux together')
    p.add_argument('--init', choices=INIT_CHOICES, default=None)
    p.add_argument('--evidence-aux', type=float, default=None)
    p.add_argument('--seed', type=int, required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--exclude', action='append', default=[],
                   help='panel directory or forbidden-semantics.json; repeatable.  The FROZEN '
                        'union of these signatures is forbidden to the training stream and a '
                        'collision invalidates the run')
    p.add_argument('--train-namespace', default=TRAIN_NAMESPACE)
    p.add_argument('--mode', choices=('steps', 'answer-only'), default=REGISTERED_MODE)
    p.add_argument('--positions', choices=('line', 'absolute', 'none'),
                   default=REGISTERED_POSITIONS)
    p.add_argument('--updates', type=int, default=REGISTERED_UPDATES)
    p.add_argument('--time-cap', type=float, default=CHUNK_SECONDS)
    p.add_argument('--visits', type=int, default=REGISTERED_VISITS)
    p.add_argument('--questions-per-world', type=int, default=REGISTERED_QUESTIONS_PER_WORLD)
    p.add_argument('--train-people', type=int, default=REGISTERED_PEOPLE)
    p.add_argument('--width', type=int, default=WIDTH)
    p.add_argument('--layers', type=int, default=LAYERS)
    p.add_argument('--heads', type=int, default=HEADS)
    p.add_argument('--hidden', type=int, default=HIDDEN)
    p.add_argument('--lr', type=float, default=1e-3)
    p.add_argument('--lr-final', type=float, default=1e-4)
    p.add_argument('--warmup', type=int, default=100)
    p.add_argument('--clip', type=float, default=1.0)
    p.add_argument('--weight-decay', type=float, default=.1)
    p.add_argument('--log-every', type=int, default=100)

    p = sub.add_parser('panels')
    p.add_argument('--out', required=True)
    p.add_argument('--kind', choices=('fit', 'confirm'), default='fit')
    p.add_argument('--n', type=int, default=FIT_N)
    p.add_argument('--exclude', action='append', default=[])

    p = sub.add_parser('fit')
    p.add_argument('--run', required=True)
    p.add_argument('--panels', required=True)
    p.add_argument('--out', default=None)
    p.add_argument('--block', type=int, default=32)
    p.add_argument('--confirmation', action='store_true',
                   help='score the UNTOUCHED confirmation panel; only for a configuration that '
                        'already cleared the development-fit gate')

    p = sub.add_parser('overfit')
    p.add_argument('--out', required=True)
    p.add_argument('--init', choices=INIT_CHOICES + ('both',), default='both')
    p.add_argument('--seed', type=int, default=DEV_SEED_FLOOR)
    p.add_argument('--allow-registered-seed', action='store_true')
    p.add_argument('--worlds', type=int, default=8)
    p.add_argument('--questions-per-world', type=int, default=4)
    p.add_argument('--train-people', type=int, default=REGISTERED_PEOPLE)
    p.add_argument('--max-updates', type=int, default=1500)
    p.add_argument('--exclude', action='append', default=[])
    p.add_argument('--mode', choices=('steps', 'answer-only'), default=REGISTERED_MODE)
    p.add_argument('--positions', choices=('line', 'absolute', 'none'),
                   default=REGISTERED_POSITIONS)
    p.add_argument('--evidence-aux', type=float, default=0.)
    p.add_argument('--width', type=int, default=WIDTH)
    p.add_argument('--layers', type=int, default=LAYERS)
    p.add_argument('--heads', type=int, default=HEADS)
    p.add_argument('--hidden', type=int, default=HIDDEN)
    p.add_argument('--lr', type=float, default=1e-3)
    p.add_argument('--clip', type=float, default=1.0)
    p.add_argument('--weight-decay', type=float, default=.1)
    p.add_argument('--log-every', type=int, default=100)

    args = parser.parse_args(argv)
    if args.command == 'train':
        train(args)
    elif args.command == 'panels':
        namespace = FIT_PANEL_NAMESPACE if args.kind == 'fit' else CONFIRM_PANEL_NAMESPACE
        build_fit_panels(args.out, namespace, args.n, args.exclude)
    elif args.command == 'fit':
        fit(args)
    else:
        overfit(args)


if __name__ == '__main__':
    main()
