#!/usr/bin/env python3
"""novelty-19 TRAINING SIDE: awake practice, the three offline arms, native scoring,
the gates and the report of `design/v3/19-novelty-experiment-preregistration-draft.md`.

ADDITIVE ONLY.  Nothing here edits, deletes or re-hashes an existing file, and NO
model, loss, packing, rollout or scoring logic is re-implemented.  Everything
load-bearing is imported from the frozen modules:

  N   fable_novelty19_data      builder A's stream / memory / buffers / dev panels and
                                the neutral record schema (`iter_awake`, `load_buffer`,
                                `baseline_batch`, `dispatcher_inputs`, `merge_records`,
                                `training_item_view`, `load_dev_panels`, `DEV_CELLS`)
  V4  fable_dispatcher_v4       `build_model`, `flags_for_arm`, `rollout_v4`,
                                `score_side_v4`, `gate_summary`
  V3  fable_dispatcher_v3       `train_table`, `policy_gradient_loss`, `aggregate`,
                                `prepare_side`, `operator_on_chains`
  V1  fable_dispatcher          `make_operator`, `FrozenOperator`, `OracleOperator`,
                                `pad_questions`, `representatives`, `fingerprint`,
                                `configure`, `sha`, `write_new`
  B1  fable_baseline_transformer  `pack_batch`, `side_items`, `evaluate_side`,
                                `aggregate`, `model_emitter`, `output_tokens`,
                                `learning_rate`, `MAX_OUT`
  B2  fable_baseline_transformer_v2  `build_model` (operator-rescale init),
                                `teacher_forced_loss_v2`, `role_grid`, `hops_vector`
  LE  fable_baseline_length_eval  `CappedModel`, `cell_limits`, `trained_ranges`,
                                `wrong_breakdown`

-------------------------------------------------------------------------------
SUBCOMMANDS
-------------------------------------------------------------------------------
  awake    section 2 -- 6,000 updates from the registered init on builder A's common
           awake stream, consumed strictly in order, resumable in chunks of <= 750
  offline  section 4 -- 2,000 updates on one of the R/G/U buffers, following the shared
           offline-order, optimizers RESET at the boundary, chunks of <= 500
  score    section 6 -- all 32 development cells x 64 units with each architecture's
           NATIVE scoring
  gates    section 5 -- the awake-fit gate per arch x seed, plus builder A's
           generation-gate audit
  report   section 10 -- per seed / arch / arm / cell, the primary rule, the secondary
           families and a machine-readable report.json

-------------------------------------------------------------------------------
EXPERIMENT DIRECTORY LAYOUT (what `gates` and `report` expect under --exp)
-------------------------------------------------------------------------------
  EXP/buffers-<S>/             builder A's buffers (audit.json holds the generation gate)
  EXP/runs/awake-<arch>-s<S>/
  EXP/runs/offline-<arch>-s<S>-<arm>/
  EXP/scores/*.json            any name; every score file carries its own
                               arch / seed / phase / arm metadata, and several partial
                               files for one run are merged by cell.  A score file is
                               accepted only if it names the FINAL checkpoint of a
                               COMPLETED run (its sha256 must equal the one in that run's
                               completion.json) and was produced at the registered caps;
                               anything else is reported as "(wrong checkpoint)" and is
                               counted as missing, never merged
  EXP/DEV-PASSED.json          written by `report` ONLY when the registered THREE-SEED
                               development rule passes on complete evidence for the
                               registered seed set (1900, 1901, 1902).  Any other --seeds
                               prints the reason and writes nothing.  The confirmation
                               panels may not be scored without it, and `score` validates
                               its CONTENTS through fable_novelty19_data.validate_dev_passed
                               (schema, seed set, report hash, dev-panel manifest re-hashed
                               on disk, all 6 awake + 18 offline checkpoint hashes)

-------------------------------------------------------------------------------
RESUME
-------------------------------------------------------------------------------
A chunk boundary writes `ckpt-<updates-done:06d>.pt` holding the model, the optimizer,
the torch global RNG state, the policy generator state, the next update index, the
initial weight fingerprint and the two running fingerprints (data and update).  The
next invocation picks up at the highest checkpoint present, so a resumed run is
BIT-IDENTICAL to an uninterrupted one on the same machine -- `tests/
test_fable_novelty19_train.py` checks that for both architectures at small scale.
Progress is discovered by globbing, so nothing is ever overwritten or rewritten, and
before a checkpoint is resumed from, its bytes are re-hashed against the sha256 that
its own `chunk-*.json` recorded when it was written.

If a wave is KILLED mid-chunk, that chunk wrote no checkpoint, so the next invocation
repeats it from the previous boundary -- but the half-written `log-<start>-<stop>.jsonl`
is still there and the log is opened with mode 'x'.  Delete THAT LOG FILE, and only that
log file, before re-running.  Deleting a log costs nothing (it is a progress transcript,
not state); deleting a `ckpt-*.pt` or a `chunk-*.json` destroys the resume chain and is
never correct.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import resource
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fable_novelty19_data as N                                            # noqa: E402
import fable_dispatcher as V1                                              # noqa: E402
import fable_dispatcher_v3 as V3                                           # noqa: E402
import fable_dispatcher_v4 as V4                                           # noqa: E402
import fable_baseline_transformer as B1                                    # noqa: E402
import fable_baseline_transformer_v2 as B2                                 # noqa: E402
import fable_baseline_length_eval as LE                                    # noqa: E402

A = N.A
torch = N.torch
sha = V1.sha
write_new = V1.write_new
configure = V1.configure
weight_fingerprint = V1.fingerprint          # sha256 over every parameter's raw bytes

HEX64 = re.compile(r'^[0-9a-f]{64}$')

WORKTREE = Path(__file__).resolve().parent.parent


def base_checkout():
    """The checkout that owns `artifacts/` -- the base one when we run from a worktree."""
    here = Path(__file__).resolve().parent
    for parent in here.parents:
        if parent.name == 'worktrees' and parent.parent.name == '.claude':
            return parent.parent.parent
    return WORKTREE


BASE = base_checkout()

# ---- frozen registered numbers, sections 2/4/5/6.  DO NOT CHANGE. ----------------
REGISTERED_SEEDS = N.REGISTERED_SEEDS                 # (1900, 1901, 1902)
AWAKE_UPDATES = N.AWAKE_UPDATES                       # 6000
OFFLINE_UPDATES = N.OFFLINE_UPDATES                   # 2000
AWAKE_CHUNK = N.AWAKE_CHUNK                           # 750
OFFLINE_CHUNK = N.OFFLINE_CHUNK                       # 500
CHUNK_SECONDS = 1200                                  # section 9 compute budget
WAVE_DEADLINE = 1500                                  # section 9 wave deadline (--budget ceiling)

ARCHES = ('D', 'T')
ARMS = ('R', 'G', 'U')

# -- dispatcher D (section 2) ------------------------------------------------------
D_ARM = 'reg+ctx'
D_WIDTH = 32
D_PARAMETERS = 24_035
D_TRAIN_CAP = 8                                       # "common cap of eight primitive calls"
D_EVAL_CAP = 16                                       # "the existing cap 16"
D_K = 16
D_CALL_COST = 0.01
D_LR = 3e-3
D_WARMUP = 100
D_CLIP = 1.0
D_WEIGHT_DECAY = 0.01
D_BETAS = (0.9, 0.99)
D_EPS = 1e-8
D_ENTROPY = 0.2
D_ENTROPY_FINAL = 0.02
D_GENERATOR_BASE = 9_000_000                          # v4's own policy-sampling base

OPERATOR_PATH = (BASE / 'artifacts' / 'astra-canonical-operator-screen-20260920'
                 / 'astra_canonical_operator_seed-1' / 'final.pt')
OPERATOR_SHA256 = 'e7e5b6f3a6bfecf3890538bd0a14af7f5189b1565329e5cf411b52dd4d4dfbec'

# -- transformer T (section 2) -----------------------------------------------------
T_ARM = 'I1-H1'
T_INIT = 'operator-rescale'
T_EVIDENCE_AUX = 0.5
T_MODE = 'steps'
T_POSITIONS = 'line'
T_WIDTH, T_LAYERS, T_HEADS, T_HIDDEN = 48, 3, 4, 208
T_OUTPUT_CAPACITY = 12                                # "common output capacity 12"
T_LR = 1e-3
T_LR_FINAL = 1e-4
T_WARMUP = 100
T_CLIP = 1.0
T_WEIGHT_DECAY = 0.1
T_BETAS = (0.9, 0.99)
T_EPS = 1e-8

# -- marks (sections 5/6) ----------------------------------------------------------
AWAKE_FIT_MARK = 61                                   # >= 61/64 answers AND strict, F cells
PRIMARY_MARK = 58                                     # >= 58/64 answers AND strict, N cells
PRIMARY_GAIN = 13                                     # >= 13/64 strict over the R arm
FAMILY_MARK = dict(N=PRIMARY_MARK, E=PRIMARY_MARK, F=AWAKE_FIT_MARK, P=PRIMARY_MARK,
                   H=None, L=PRIMARY_MARK)            # H is descriptive only
FIT_CELLS = tuple(c for c in N.DEV_CELL_ORDER if c.startswith('F-'))       # the 7 F cells
PRIMARY_CELLS = tuple(c for c in N.DEV_CELL_ORDER if c.startswith('N-'))   # the 4 N cells


def family_of(cell):
    return cell.split('-')[0]


def source_fingerprint():
    """Every source this module's output depends on, so an import cannot drift unnoticed."""
    return dict(novelty19_train=sha(__file__), novelty19_data=sha(N.__file__),
                dispatcher=sha(V1.__file__), dispatcher_v3=sha(V3.__file__),
                dispatcher_v4=sha(V4.__file__), baseline=sha(B1.__file__),
                baseline_v2=sha(B2.__file__), baseline_length_eval=sha(LE.__file__),
                canonical_operator=sha(A.__file__), torch=torch.__version__)


def host_profile():
    return dict(hostname=platform.node(), platform=platform.platform(),
                machine=platform.machine(), python=sys.version.split()[0],
                torch=torch.__version__, threads=torch.get_num_threads(),
                interop_threads=torch.get_num_interop_threads())


def peak_rss_bytes():
    """macOS reports ru_maxrss in bytes; Linux in kibibytes."""
    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(raw) if sys.platform == 'darwin' else int(raw) * 1024


def chain(previous, payload):
    """A running fingerprint: sha256(previous || canonical-json(payload))."""
    digest = hashlib.sha256()
    digest.update(previous.encode())
    digest.update(json.dumps(payload, sort_keys=True, separators=(',', ':'),
                             allow_nan=False).encode())
    return digest.hexdigest()


def question_digest(items):
    """The raw question BYTES of one update -- what both architectures must agree on."""
    digest = hashlib.sha256()
    for item in items:
        digest.update(bytes(item['question']))
        digest.update(b'|')
    return digest.hexdigest()


def verified_operator(path=None, expect=OPERATOR_SHA256):
    """The frozen canonical operator, with its bytes checked BEFORE it is loaded.

    Section 2 names one operator for every D arm and seed and gives its SHA-256; a
    mismatch is an integrity failure, never a warning.
    """
    path = Path(path or OPERATOR_PATH)
    if str(path) == 'oracle':
        raise SystemExit('the registered D arms use the frozen canonical operator, not the oracle')
    if not path.is_file():
        raise SystemExit(f'frozen operator checkpoint not found: {path}')
    actual = sha(path)
    if expect is not None and actual != expect:
        raise SystemExit(f'frozen operator SHA-256 mismatch at {path}: expected {expect}, '
                         f'found {actual}.  Aborting: this is not the registered operator.')
    operator = V1.make_operator(str(path))
    assert operator.sha256 == actual
    return operator


# =========================================================================== data feeds


def awake_feed(seed, start, end, stream):
    """Builder A's records for updates [start, end), strictly in order.

    `N.iter_awake` re-hashes every stream chunk it opens against index.json, so a
    changed byte aborts the wave instead of training on it.
    """
    for record in N.iter_awake(seed, start, end, stream):
        yield record


def _world_record(buffer_record, world, questions_per_world):
    lo = world * questions_per_world
    return dict(kind=buffer_record['kind'], seed=buffer_record['seed'], index=world,
                namespaces=[buffer_record['namespaces'][world]],
                source=buffer_record['source'][lo:lo + questions_per_world],
                stories=[buffer_record['stories'][world]],
                memories=[buffer_record['memories'][world]],
                items=[dict(it, owner=0)
                       for it in buffer_record['items'][lo:lo + questions_per_world]])


def offline_record(buffer_record, indices, questions_per_world=N.BUFFER_QUESTIONS_PER_WORLD):
    """One offline update: the shared order's 16 memory worlds x their four questions.

    World indices are sampled WITH replacement, so the same memory world may appear
    twice in one update; each occurrence becomes its own batch slot, exactly as a
    repeated awake world would.  `N.merge_records` does the owner renumbering.
    """
    return N.merge_records([_world_record(buffer_record, int(w), questions_per_world)
                            for w in indices])


def read_offline_order(buffers):
    path = Path(buffers) / 'offline-order.json'
    if not path.exists():
        raise SystemExit(f'no offline-order.json in {buffers}')
    order = json.loads(path.read_text())
    rebuilt = N.offline_order(order['seed'], updates=order['updates'], visits=order['visits'],
                              worlds=order['worlds'])
    if rebuilt != order['order']:
        raise SystemExit(f'{path} is not reproducible from its namespace; run invalid')
    return order


def offline_feed(buffer_record, order, start, end):
    for update in range(start, end):
        yield offline_record(buffer_record, order['order'][update])


# =========================================================================== models


def build_dispatcher(seed):
    """The registered D: v4 `reg+ctx`, width 32, from the registered init."""
    flags = V4.flags_for_arm(D_ARM)
    torch.manual_seed(int(seed))
    model = V4.build_model(width=D_WIDTH, flags=flags)
    if model.parameters_count() != D_PARAMETERS:
        raise SystemExit(f'D has {model.parameters_count()} parameters, registered '
                         f'{D_PARAMETERS}; refusing to train a different architecture')
    return model, flags


def build_transformer(seed):
    """The registered T: corrected baseline v2, arm I1-H1, from the registered init."""
    return B2.build_model(int(seed), T_INIT, positions=T_POSITIONS, width=T_WIDTH,
                          layers=T_LAYERS, heads=T_HEADS, hidden=T_HIDDEN)


def dispatcher_optimizer(model):
    return torch.optim.AdamW(model.parameters(), lr=D_LR, betas=D_BETAS, eps=D_EPS,
                             weight_decay=D_WEIGHT_DECAY)


def transformer_optimizer(model):
    return torch.optim.AdamW(model.parameters(), lr=T_LR, betas=T_BETAS, eps=T_EPS,
                             weight_decay=T_WEIGHT_DECAY)


def dispatcher_schedule(update, total):
    """v4's warmup (no decay) and the registered linear entropy ramp, over `total`."""
    lr = D_LR * min(1., (update + 1) / max(1, D_WARMUP))
    beta = D_ENTROPY + (D_ENTROPY_FINAL - D_ENTROPY) * (update / max(1, total - 1))
    return lr, beta


def transformer_schedule(update, total):
    return B1.learning_rate(T_LR, update, total, T_WARMUP, T_LR_FINAL)


# =========================================================================== one update


def dispatcher_update(model, flags, operator, optimizer, generator, record, update, total):
    """v4's `train` loop body, function for function: `V3.train_table`,
    `V4.rollout_v4` and `V3.policy_gradient_loss` do all the work."""
    lr, beta = dispatcher_schedule(update, total)
    for group in optimizer.param_groups:
        group['lr'] = lr
    items = record['items']
    inputs = N.dispatcher_inputs(record)
    questions = [it['question'] for it in items]
    owners = [it['owner'] for it in items]
    answers = torch.tensor([it['answer'] for it in items], dtype=torch.long)
    reps, visit_of = V1.representatives(owners)
    table = V3.train_table(operator, inputs, reps, D_TRAIN_CAP)
    tokens, present = V1.pad_questions(questions)
    repeat = torch.arange(len(questions)).repeat_interleave(D_K)
    gates = [] if flags.learned_register else None
    episodes = V4.rollout_v4(model, tokens[repeat], present[repeat], table, visit_of[repeat],
                             D_TRAIN_CAP, mode='sample', generator=generator, flags=flags,
                             gates=gates)
    reward = (episodes.answer == answers[repeat]).float()
    loss, shaped, mean_entropy = V3.policy_gradient_loss(episodes, reward, D_K, D_CALL_COST, beta)
    optimizer.zero_grad(set_to_none=True)
    loss.backward()
    norm = torch.nn.utils.clip_grad_norm_(model.parameters(), D_CLIP)
    if not bool(torch.isfinite(loss)) or not bool(torch.isfinite(norm)):
        raise RuntimeError(f'nonfinite dispatcher loss or gradient at update {update}')
    optimizer.step()
    summary = V4.gate_summary(gates) if gates else None
    return dict(update=update, lr=lr, entropy_coefficient=beta, loss=float(loss.detach()),
                grad_norm=float(norm), mean_reward=float(reward.mean()),
                mean_shaped=float(shaped.mean()), mean_calls=float(episodes.calls.float().mean()),
                entropy=float(mean_entropy.detach()),
                invalid_fraction=sum(s == 'invalid_action' for s in episodes.status)
                / len(episodes.status),
                over_cap_fraction=sum(s == 'over_cap' for s in episodes.status)
                / len(episodes.status),
                mean_write_gate=None if summary is None else summary['mean'],
                write_gate_above_half=None if summary is None else summary['fraction_above_half'])


def transformer_update(model, optimizer, record, update, total):
    """baseline-v2's `train` loop body: `N.baseline_batch` then
    `B2.teacher_forced_loss_v2`, with v1's supporting-line loss at 0.5."""
    lr = transformer_schedule(update, total)
    for group in optimizer.param_groups:
        group['lr'] = lr
    batch = N.baseline_batch(record, T_MODE, support=bool(T_EVIDENCE_AUX))
    _stories, items = N.training_item_view(record)
    loss, aux, counts = B2.teacher_forced_loss_v2(
        model, batch, evidence_aux=T_EVIDENCE_AUX, roles=B2.role_grid(batch),
        hops=B2.hops_vector(items))
    optimizer.zero_grad(set_to_none=True)
    loss.backward()
    norm = torch.nn.utils.clip_grad_norm_(model.parameters(), T_CLIP)
    if not bool(torch.isfinite(loss)) or not bool(torch.isfinite(norm)):
        raise RuntimeError(f'nonfinite baseline loss or gradient at update {update}')
    optimizer.step()
    row = dict(update=update, lr=lr, loss=float(loss.detach()), evidence=float(aux),
               grad_norm=float(norm))
    row.update({f'{k}_hits': v[0] for k, v in counts.items()})
    row.update({f'{k}_total': v[1] for k, v in counts.items()})
    return row


def update_digest_payload(arch, row):
    """The scalars the per-update running fingerprint chains over."""
    if arch == 'D':
        keys = ('update', 'lr', 'entropy_coefficient', 'loss', 'grad_norm', 'mean_reward',
                'mean_shaped', 'mean_calls', 'entropy')
    else:
        keys = ('update', 'lr', 'loss', 'evidence', 'grad_norm', 'token_hits', 'sequence_hits')
    return {k: row[k] for k in keys if k in row}


# =========================================================================== checkpoints


def checkpoint_name(done):
    return f'ckpt-{done:06d}.pt'


def existing_checkpoints(out):
    """(updates_done, path) for every chunk boundary already on disk, ascending."""
    found = []
    for path in sorted(Path(out).glob('ckpt-*.pt')):
        stem = path.stem.split('-')[-1]
        if stem.isdigit():
            found.append((int(stem), path))
    return sorted(found)


def save_state(out, done, *, arch, model, optimizer, generator, meta):
    path = Path(out) / checkpoint_name(done)
    if path.exists():
        raise SystemExit(f'refusing to overwrite an existing checkpoint: {path}')
    payload = dict(meta)
    payload.update(arch=arch, updates_done=int(done), state_dict=model.state_dict(),
                   optimizer=optimizer.state_dict(),
                   torch_rng_state=torch.get_rng_state(),
                   generator_state=None if generator is None else generator.get_state())
    torch.save(payload, path)
    return path


def recorded_checkpoint_sha(path):
    """The sha256 that this run's own bookkeeping recorded for `path` when it was written.

    `chunk-<start>-<stop>.json` is written immediately after `ckpt-<stop>.pt` and names it;
    `completion.json` names the final one.  Returning None means the run directory holds a
    checkpoint that no record in that directory accounts for.
    """
    path = Path(path)
    folder = path.parent
    for record in sorted(folder.glob('chunk-*.json')):
        row = json.loads(record.read_text())
        if row.get('checkpoint') == path.name:
            return row.get('checkpoint_sha256'), str(record)
    done = folder / 'completion.json'
    if done.is_file():
        row = json.loads(done.read_text())
        if Path(str(row.get('checkpoint', ''))).name == path.name:
            return row.get('checkpoint_sha256'), str(done)
    return None, None


def verify_recorded_sha(path):
    """Must-fix 5: never resume from bytes that are not the bytes we wrote.

    Truncation is caught by torch's own container check, but a silent corruption inside a
    tensor blob is not, so the hash is compared BEFORE `torch.load` is called at all.
    """
    path = Path(path)
    expected, source = recorded_checkpoint_sha(path)
    if expected is None:
        raise SystemExit(f'{path} is not recorded in any chunk-*.json or completion.json of '
                         f'{path.parent}; refusing to resume from an unaccounted checkpoint')
    actual = sha(path)
    if actual != expected:
        raise SystemExit(f'{path} hashes to {actual} but {source} recorded {expected}; '
                         f'the checkpoint has changed on disk since it was written -- '
                         f'refusing to resume')
    return dict(checkpoint=str(path), sha256=actual, recorded_in=source)


def load_state(path, *, arch, model, optimizer, generator):
    verify_recorded_sha(path)
    saved = torch.load(Path(path), map_location='cpu', weights_only=False)
    if saved.get('arch') != arch:
        raise SystemExit(f'{path} holds architecture {saved.get("arch")!r}, asked for {arch!r}')
    model.load_state_dict(saved['state_dict'], strict=True)
    if optimizer is not None:
        optimizer.load_state_dict(saved['optimizer'])
    torch.set_rng_state(saved['torch_rng_state'])
    if generator is not None and saved.get('generator_state') is not None:
        generator.set_state(saved['generator_state'])
    return saved


def load_weights_only(path, arch, model):
    """The awake-final weights for an offline arm.  The optimizer is NOT restored:
    section 4 resets it at this boundary, in every arm.

    The awake run's own bookkeeping is consulted first, so an offline arm can only start
    from the exact bytes that awake run wrote (must-fix 5)."""
    verify_recorded_sha(path)
    saved = torch.load(Path(path), map_location='cpu', weights_only=False)
    if saved.get('arch') != arch:
        raise SystemExit(f'{path} holds architecture {saved.get("arch")!r}, asked for {arch!r}')
    if 'final_weight_fingerprint' not in saved:
        # note N4: without the key the fingerprint comparison below would compare a value
        # with itself, so an awake checkpoint that lacks it is refused rather than trusted.
        raise SystemExit(f'{path} carries no final_weight_fingerprint; it was not written '
                         f'by this script and cannot start an offline arm')
    model.load_state_dict(saved['state_dict'], strict=True)
    return saved


# =========================================================================== the driver


def run_phase(*, out, arch, seed, phase, total, chunk, budget, feed_factory, inputs_record,
              arm=None, awake_ckpt=None, argv=None, progress=True):
    """Train `total` updates in resumable chunks of at most `chunk`.

    One invocation is one wave: it trains chunk after chunk until the phase is finished
    or the compute budget is spent, always making at least one chunk of progress.  Every
    chunk boundary writes a complete checkpoint, so re-invoking the SAME command resumes
    at the exact next update and the result is bit-identical to an uninterrupted run.
    """
    configure()
    folder = Path(out)
    folder.mkdir(parents=True, exist_ok=True)
    done_path = folder / 'completion.json'
    if done_path.exists():
        record = json.loads(done_path.read_text())
        if progress:
            print(json.dumps(dict(event='already-complete', out=str(folder),
                                  updates=record.get('updates_done'))), flush=True)
        return record
    if not 1 <= chunk <= (AWAKE_CHUNK if phase == 'awake' else OFFLINE_CHUNK):
        raise SystemExit(f'--chunk-updates must be 1..'
                         f'{AWAKE_CHUNK if phase == "awake" else OFFLINE_CHUNK} for {phase}')

    operator = None
    if arch == 'D':
        model, flags = build_dispatcher(seed)
        optimizer = dispatcher_optimizer(model)
        generator = torch.Generator().manual_seed(D_GENERATOR_BASE + int(seed))
        operator = verified_operator()
        operator_before = operator.fingerprint
    else:
        model, flags = build_transformer(seed), None
        optimizer = transformer_optimizer(model)
        generator = None
        operator_before = None
    initial_fingerprint = weight_fingerprint(model)

    started_index, data_digest, update_digest = 0, '', ''
    boundaries = existing_checkpoints(folder)
    resumed_from = None
    if boundaries and boundaries[-1][0] >= total:
        raise SystemExit(f'{folder} already holds {boundaries[-1][0]} updates but has no '
                         f'completion.json; nothing left to train')
    if boundaries:
        started_index, resumed_from = boundaries[-1]
        saved = load_state(resumed_from, arch=arch, model=model, optimizer=optimizer,
                           generator=generator)
        initial_fingerprint = saved['initial_weight_fingerprint']
        data_digest, update_digest = saved['data_fingerprint'], saved['update_fingerprint']
        if saved.get('phase') != phase or int(saved.get('seed')) != int(seed):
            raise SystemExit(f'{resumed_from} is a {saved.get("phase")}/seed-{saved.get("seed")} '
                             f'checkpoint, not {phase}/seed-{seed}')
    elif phase == 'offline':
        if awake_ckpt is None:
            raise SystemExit('offline needs --awake-ckpt')
        awake_saved = load_weights_only(awake_ckpt, arch, model)
        if int(awake_saved.get('seed')) != int(seed):
            raise SystemExit(f'--awake-ckpt holds seed {awake_saved.get("seed")}, asked for {seed}')
        if awake_saved.get('phase') != 'awake':
            raise SystemExit('--awake-ckpt must be an awake checkpoint')
        initial_fingerprint = weight_fingerprint(model)
        if initial_fingerprint != awake_saved['final_weight_fingerprint']:
            raise SystemExit('the loaded awake weights do not match their own fingerprint')
        # section 4: reset the optimizer here, in EVERY arm.  Nothing of the awake
        # optimizer's state (step counts, moments) survives this boundary.
        optimizer = dispatcher_optimizer(model) if arch == 'D' else transformer_optimizer(model)
        if generator is not None:
            generator = torch.Generator().manual_seed(D_GENERATOR_BASE + int(seed))
        torch.manual_seed(D_GENERATOR_BASE + int(seed))

    if started_index >= total:
        raise SystemExit(f'{folder} already holds {started_index} updates but has no '
                         f'completion.json; nothing left to train')

    began = time.monotonic()
    chunk_records = [json.loads(p.read_text()) for p in sorted(folder.glob('chunk-*.json'))]
    seconds_before = sum(row['seconds'] for row in chunk_records)
    index = started_index
    while index < total:
        stop = min(index + chunk, total)
        log_path = folder / f'log-{index:06d}-{stop:06d}.jsonl'
        if log_path.exists():
            raise SystemExit(f'refusing to overwrite {log_path}')
        chunk_began = time.monotonic()
        seen = 0
        feed = feed_factory(index, stop)
        with log_path.open('x') as log:
            for update in range(index, stop):
                record = next(feed, None)
                if record is None:
                    raise RuntimeError(f'the data feed ran out at update {update}; '
                                       f'{phase} needs records [{index}, {stop})')
                seen += 1
                data_digest = chain(data_digest, dict(u=update, q=question_digest(record['items'])))
                if arch == 'D':
                    row = dispatcher_update(model, flags, operator, optimizer, generator,
                                            record, update, total)
                else:
                    row = transformer_update(model, optimizer, record, update, total)
                update_digest = chain(update_digest, update_digest_payload(arch, row))
                if (update + 1) % 100 == 0 or update == index:
                    log.write(json.dumps(row) + '\n')
                    log.flush()
                    if progress:
                        print(json.dumps(dict(arch=arch, seed=seed, phase=phase, arm=arm,
                                              seconds=round(time.monotonic() - began, 1),
                                              **row)), flush=True)
        if seen != stop - index:
            raise RuntimeError(f'consumed {seen} records, expected {stop - index}')
        if operator is not None and operator.fingerprint != operator_before:
            raise RuntimeError('the frozen operator changed during training')
        meta = dict(seed=int(seed), phase=phase, arm=arm, total_updates=int(total),
                    initial_weight_fingerprint=initial_fingerprint,
                    final_weight_fingerprint=weight_fingerprint(model),
                    data_fingerprint=data_digest, update_fingerprint=update_digest,
                    inputs=inputs_record, chunk=int(chunk),
                    source_fingerprint=source_fingerprint(),
                    operator_sha256=None if operator is None else operator.sha256,
                    operator_fingerprint=None if operator is None else operator.fingerprint)
        path = save_state(folder, stop, arch=arch, model=model, optimizer=optimizer,
                          generator=generator, meta=meta)
        elapsed = time.monotonic() - chunk_began
        write_new(folder / f'chunk-{index:06d}-{stop:06d}.json',
                  dict(start=index, end=stop, updates=stop - index, seconds=elapsed,
                       updates_per_second=(stop - index) / max(1e-9, elapsed),
                       checkpoint=path.name, checkpoint_sha256=sha(path),
                       weight_fingerprint=meta['final_weight_fingerprint'],
                       data_fingerprint=data_digest, update_fingerprint=update_digest,
                       peak_rss_bytes=peak_rss_bytes(), created_unix=time.time()))
        chunk_records.append(json.loads((folder / f'chunk-{index:06d}-{stop:06d}.json').read_text()))
        index = stop
        if progress:
            print(json.dumps(dict(event='chunk', arch=arch, seed=seed, phase=phase, arm=arm,
                                  done=index, of=total, seconds=round(elapsed, 1))), flush=True)
        if index < total and budget is not None and time.monotonic() - began >= budget:
            if progress:
                print(json.dumps(dict(event='budget', done=index, of=total,
                                      budget_seconds=budget,
                                      note='incomplete, not a result; re-run the same command')),
                      flush=True)
            return dict(complete=False, updates_done=index, total_updates=total,
                        out=str(folder.resolve()))

    seconds = seconds_before + (time.monotonic() - began)
    final = weight_fingerprint(model)
    last = folder / checkpoint_name(total)
    completion = dict(
        kind='novelty19-run', arch=arch, seed=int(seed), phase=phase, arm=arm,
        complete=True, updates_done=int(total), total_updates=int(total),
        seconds=seconds, updates_per_second=total / max(1e-9, seconds),
        chunk_updates=int(chunk), chunks=len(chunk_records), chunk_log=chunk_records,
        resumed_from=None if resumed_from is None else Path(resumed_from).name,
        initial_weight_fingerprint=initial_fingerprint, final_weight_fingerprint=final,
        data_fingerprint=data_digest, update_fingerprint=update_digest,
        checkpoint=str(last.resolve()), checkpoint_sha256=sha(last),
        inputs=inputs_record,
        awake_checkpoint=None if awake_ckpt is None else str(Path(awake_ckpt).resolve()),
        awake_checkpoint_sha256=None if awake_ckpt is None else sha(Path(awake_ckpt)),
        optimizer_reset_at_offline_boundary=bool(phase == 'offline'),
        operator=None if operator is None else operator.describe(),
        operator_sha256_expected=None if operator is None else OPERATOR_SHA256,
        operator_weights_unchanged=None if operator is None else True,
        hyperparameters=(dict(train_cap=D_TRAIN_CAP, eval_cap=D_EVAL_CAP, k=D_K,
                              call_cost=D_CALL_COST, lr=D_LR, warmup=D_WARMUP, clip=D_CLIP,
                              weight_decay=D_WEIGHT_DECAY, betas=list(D_BETAS), eps=D_EPS,
                              entropy=[D_ENTROPY, D_ENTROPY_FINAL], width=D_WIDTH, arm=D_ARM)
                         if arch == 'D' else
                         dict(lr=T_LR, lr_final=T_LR_FINAL, warmup=T_WARMUP, clip=T_CLIP,
                              weight_decay=T_WEIGHT_DECAY, betas=list(T_BETAS), eps=T_EPS,
                              evidence_aux=T_EVIDENCE_AUX, mode=T_MODE, positions=T_POSITIONS,
                              width=T_WIDTH, layers=T_LAYERS, heads=T_HEADS, hidden=T_HIDDEN,
                              output_capacity=T_OUTPUT_CAPACITY, arm=T_ARM, init=T_INIT)),
        parameters=model.parameters_count(),
        peak_rss_bytes=peak_rss_bytes(), host=host_profile(),
        source_fingerprint=source_fingerprint(),
        argv=list(argv if argv is not None else sys.argv), created_unix=time.time())
    write_new(done_path, completion)
    if progress:
        print(json.dumps(dict(event='done', arch=arch, seed=seed, phase=phase, arm=arm,
                              updates=total, seconds=round(seconds, 1),
                              updates_per_second=round(completion['updates_per_second'], 3),
                              chunks=len(chunk_records))), flush=True)
    return completion


# =========================================================================== awake / offline


def awake(args):
    """Section 2: `--updates` ordinary training on builder A's common awake stream."""
    folder, index = N.read_awake_index(args.stream)
    if int(index['seed']) != int(args.seed):
        raise SystemExit(f'stream {folder} holds seed {index["seed"]}, asked for {args.seed}')
    if int(index['updates']) < int(args.updates):
        raise SystemExit(f'stream {folder} holds {index["updates"]} updates, '
                         f'{args.updates} requested')
    inputs_record = dict(
        stream=str(folder.resolve()), stream_index_sha256=sha(folder / 'index.json'),
        stream_seed=int(index['seed']), stream_updates=int(index['updates']),
        stream_chunks=[dict(name=c['name'], sha256=c['sha256']) for c in index['chunks']],
        stream_exclusion_sha256=index['exclusion']['union_sha256'],
        stream_fingerprint=index['fingerprint'])
    return run_phase(out=args.out, arch=args.arch, seed=args.seed, phase='awake',
                     total=args.updates, chunk=args.chunk_updates, budget=args.budget_seconds,
                     feed_factory=lambda lo, hi: awake_feed(args.seed, lo, hi, args.stream),
                     inputs_record=inputs_record, argv=sys.argv, progress=not args.quiet)


def offline(args):
    """Section 4: `--updates` offline updates on ONE buffer, following the shared order."""
    buffers = Path(args.buffers)
    manifest = json.loads((buffers / 'manifest.json').read_text())
    if int(manifest['seed']) != int(args.seed):
        raise SystemExit(f'buffers hold seed {manifest["seed"]}, asked for {args.seed}')
    if args.arm not in manifest['arms']:
        raise SystemExit(f'{buffers} has no arm {args.arm}; it holds {manifest["arms"]}')
    order = read_offline_order(buffers)
    if int(order['seed']) != int(args.seed):
        raise SystemExit('offline-order.json holds a different seed')
    if int(order['updates']) < int(args.updates):
        raise SystemExit(f'offline-order.json holds {order["updates"]} updates, '
                         f'{args.updates} requested')
    buffer_record = N.load_buffer(buffers, args.arm)
    inputs_record = dict(
        buffers=str(buffers.resolve()),
        buffers_manifest_sha256=sha(buffers / 'manifest.json'),
        buffer_file=f'buffer-{args.arm}.pt',
        buffer_sha256=manifest['files'][f'buffer-{args.arm}.pt'],
        buffer_audit_sha256=manifest['audit_sha256'],
        offline_order_sha256=sha(buffers / 'offline-order.json'),
        offline_order_namespace=order['namespace'],
        offline_order_digest=order['order_sha256'],
        worlds=len(buffer_record['stories']), questions=len(buffer_record['items']),
        arm_note='the three arms differ ONLY in which buffer-*.pt is read; the world bytes, '
                 'the world-index order, the schedules and every hyper-parameter are shared')
    return run_phase(out=args.out, arch=args.arch, seed=args.seed, phase='offline',
                     total=args.updates, chunk=args.chunk_updates, budget=args.budget_seconds,
                     feed_factory=lambda lo, hi: offline_feed(buffer_record, order, lo, hi),
                     inputs_record=inputs_record, arm=args.arm, awake_ckpt=args.awake_ckpt,
                     argv=sys.argv, progress=not args.quiet)


# =========================================================================== failure shapes


def _bump(counter, key):
    counter[str(key)] = counter.get(str(key), 0) + 1


def dispatcher_failure_shapes(per_side):
    """Where D's native episodes went wrong, over every scored ROW (both twins of a pair).

    `calls_histogram` / `stopped_at` are the mean-calls ceiling diagnostic of section 8
    ("G learns c=4/5 but stops at exactly five on c>=6"): they show the LENGTH the
    controller actually produced, not only whether it was right.
    """
    calls_hist, stopped_at, first_wrong = {}, {}, {}
    rows = answered = over_cap = invalid = 0
    early = late = right_length = wrong_terminal = answer_wrong_path = operator_wrong = 0
    total_calls = 0
    for side, results in per_side.items():
        for row in results:
            rows += 1
            total_calls += row['calls']
            _bump(calls_hist, row['calls'])
            if row['status'] == 'answered':
                answered += 1
                _bump(stopped_at, row['calls'])
            elif row['status'] == 'over_cap':
                over_cap += 1
            elif row['status'] == 'invalid_action':
                invalid += 1
            if row['operator_chain_all'] == 0:
                operator_wrong += 1
            if row['correct'] and not row['strict_path']:
                answer_wrong_path += 1
            if row['strict_path']:
                continue
            chain_ = row['truth_chain']
            transcript = row['transcript']
            index = None
            for j, step in enumerate(transcript):
                if j >= len(chain_) or list(step) != list(chain_[j]):
                    index = j
                    break
            if index is None and len(transcript) != len(chain_):
                index = len(transcript)
            _bump(first_wrong, 'none' if index is None else index)
            if row['status'] == 'answered':
                if row['calls'] < row['hops']:
                    early += 1
                elif row['calls'] > row['hops']:
                    late += 1
                else:
                    right_length += 1
                if transcript and list(transcript[-1])[1] != list(chain_[-1])[1]:
                    wrong_terminal += 1
    return dict(rows=rows, answered=answered, over_cap=over_cap, invalid_action=invalid,
                calls_histogram=calls_hist, stopped_at=stopped_at,
                first_wrong_call=first_wrong, stopped_early=early, stopped_late=late,
                right_length_wrong_path=right_length,
                wrong_terminal_operation=wrong_terminal,
                answer_with_wrong_path=answer_wrong_path,
                frozen_operator_wrong_on_true_chain=operator_wrong,
                mean_calls=total_calls / max(1, rows),
                note=('a cap hit (over_cap) is a FAILURE even if the last token happens to '
                      'equal the answer; stopped_at counts only episodes that chose STOP'))


def _trained_hops(phase, arm):
    """What the checkpoint's own training actually exercised, for the position annotations."""
    if phase == 'awake' or arm == 'R':
        return list(N.AWAKE_CALLS)
    return list(N.UNIFORM_CALLS)


# =========================================================================== score


def panel_kind(panels):
    """(kind, namespace) read from manifest.json BEFORE anything is loaded or hashed."""
    manifest = json.loads((Path(panels) / 'manifest.json').read_text())
    return manifest.get('kind'), manifest.get('namespace'), manifest


def guard_confirmation(panels, confirmation, experiment):
    """Section 7: the confirmation suite may not be read until development has passed.

    The check runs on the panel manifest alone, so a confirmation directory is refused
    before a single unit is loaded, let alone scored.

    Must-fix 2: the unlock is the CONTENT of `DEV-PASSED.json`, not its existence.  The
    data module owns that contract, so its own `validate_dev_passed` is what decides:
    the schema string, the registered seed set, a report hash, the dev-panel manifest
    hash RE-HASHED against the manifest on disk, and all six awake plus eighteen offline
    checkpoint hashes in hex64 with no extra keys.  `{}`, a one-seed payload, a wrong
    schema and non-JSON bytes are all refused.

    `panels_folder` is deliberately NOT passed: `dev_panels.manifest_sha256` records the
    DEVELOPMENT suite the verdict was computed on, while `panels` here is the confirmation
    suite being scored.  The two are different directories by construction, so the data
    module resolves the development path recorded inside the file, exactly as
    `build_dev_panels(confirmation=True)` does.

    M-1 closes the other direction.  Validating the presented `DEV-PASSED.json` proves it
    is A valid verdict; it does not prove it is THE verdict these confirmation panels were
    generated from.  `build_dev_panels(confirmation=True)` writes the verdict record it
    unlocked on into the confirmation manifest under `dev_passed`, so the suite carries the
    hash of the file it was born from.  We therefore hash the presented file and require it
    to equal `manifest['dev_passed']['sha256']`.  A second, equally valid verdict -- a
    re-run, a later generation, another experiment's file -- is refused by name, and so is
    a confirmation manifest that records no hash at all.
    """
    kind, namespace, manifest = panel_kind(panels)
    looks_confirmation = bool(kind == 'confirmation' or namespace == N.NS_CONFIRM)
    if not looks_confirmation:
        if confirmation:
            raise SystemExit(f'--confirmation was passed but {panels} is a {kind!r} panel set')
        return dict(is_confirmation=False, kind=kind, namespace=namespace)
    if not confirmation:
        raise SystemExit(f'{panels} is the CONFIRMATION suite; scoring it needs --confirmation')
    if experiment is None:
        raise SystemExit('--confirmation needs --experiment <folder holding DEV-PASSED.json>')
    flag = Path(experiment) / 'DEV-PASSED.json'
    if not flag.exists():
        raise SystemExit(f'refusing to score confirmation panels: no {flag}.  Confirmation is '
                         'scored only after development passes without recipe changes.')
    record = N.validate_dev_passed(experiment, seeds=REGISTERED_SEEDS)
    bound = manifest.get('dev_passed')
    if not isinstance(bound, dict) or not bound.get('sha256'):
        raise SystemExit(f'refusing to score confirmation panels: {Path(panels)}/manifest.json '
                         'records no dev_passed.sha256, so there is nothing tying this suite to '
                         'the verdict that unlocked it.  Rebuild the suite with '
                         'build_dev_panels(confirmation=True).')
    if bound['sha256'] != record['sha256']:
        raise SystemExit(f'refusing to score confirmation panels: {flag} hashes to '
                         f'{record["sha256"]} but {Path(panels)}/manifest.json was generated '
                         f'from the verdict {bound["sha256"]}.  This is a VALID verdict but not '
                         f'THE one these panels were unlocked by -- present the original '
                         f'DEV-PASSED.json, or rebuild the confirmation suite from this one.')
    return dict(is_confirmation=True, kind=kind, namespace=namespace,
                dev_passed=str(flag.resolve()), dev_passed_sha256=record['sha256'],
                dev_passed_validated_by='fable_novelty19_data.validate_dev_passed',
                dev_passed_bound_to_suite=True, dev_passed_record=record)


def load_run_checkpoint(path, arch):
    # N8: hash BEFORE loading, exactly as the resume path does.  A checkpoint that changed
    # on disk since its run recorded it is refused without ever being deserialised.
    recorded = verify_recorded_sha(path)
    saved = torch.load(Path(path), map_location='cpu', weights_only=False)
    if saved.get('arch') != arch:
        raise SystemExit(f'{path} holds architecture {saved.get("arch")!r}, asked for {arch!r}')
    if arch == 'D':
        model, flags = build_dispatcher(saved['seed'])
        model.load_state_dict(saved['state_dict'], strict=True)
    else:
        model = build_transformer(saved['seed'])
        model.load_state_dict(saved['state_dict'], strict=True)
        flags = None
    model.eval()
    if weight_fingerprint(model) != saved['final_weight_fingerprint']:
        raise SystemExit(f'{path}: the loaded weights do not match their stored fingerprint')
    saved['_verified_on_disk'] = recorded
    return saved, model, flags


@torch.no_grad()
def score_dispatcher_cell(model, flags, operator, oracle, units, cfg, cap, tables):
    sides = ['a'] + (['b'] if cfg['kind'] == 'pair' else [])
    hits = {s: V3.operator_on_chains(operator, units, s) for s in sides}
    gates = [] if flags.learned_register else None
    native = {s: V4.score_side_v4(model, operator, units, s, cap, flags, chain_hits=hits,
                                  prepared=tables.get('trained_operator', cfg['name'], units, s),
                                  gates=gates)
              for s in sides}
    row = dict(V3.aggregate(native, len(units), cfg))
    row['failure_shapes'] = dispatcher_failure_shapes(native)
    row['write_gate'] = V4.gate_summary(gates) if gates else None
    if oracle is not None:
        diagnostic = {s: V4.score_side_v4(model, oracle, units, s, cap, flags,
                                          prepared=tables.get('oracle_operator', cfg['name'],
                                                              units, s))
                      for s in sides}
        row['oracle_operator'] = V3.aggregate(diagnostic, len(units), cfg)
    return row, native


@torch.no_grad()
def score_transformer_cell(model, units, cfg, capacity, trained, block=32):
    sides = ['a'] + (['b'] if cfg['kind'] == 'pair' else [])
    loaded = {s: B1.side_items(units, s) for s in sides}
    limits = LE.cell_limits(model, loaded, capacity, trained, cfg['hops'])
    if limits['unscorable_reason'] is not None:
        # section 2: "Assert no position-table clipping or clamping in any panel."
        raise SystemExit(f'{cfg["name"]}: the registered output capacity {capacity} would clamp '
                         f'a fixed position table -- {limits["unscorable_reason"]}')
    emit = B1.model_emitter(LE.CappedModel(model, capacity), block)
    native = {s: B1.evaluate_side(loaded[s][1], emit(*loaded[s]), T_MODE) for s in sides}
    row = dict(B1.aggregate(native, len(units), cfg))
    row['failure_shapes'] = LE.wrong_breakdown({s: loaded[s][1] for s in sides}, native, T_MODE,
                                               cfg['hops'], capacity)
    row['limits'] = limits
    return row, native


def score(args):
    configure()
    if args.eval_cap != D_EVAL_CAP or args.capacity != T_OUTPUT_CAPACITY:
        print(json.dumps(dict(
            event='non-registered-cap', eval_cap=args.eval_cap, capacity=args.capacity,
            registered=dict(eval_cap=D_EVAL_CAP, output_capacity=T_OUTPUT_CAPACITY),
            note='this file is a DIAGNOSTIC: `report` refuses to merge a score produced at '
                 'any cap other than the registered one')), flush=True)
    guard = guard_confirmation(args.panels, args.confirmation, args.experiment)
    saved, model, flags = load_run_checkpoint(args.ckpt, args.arch)
    manifest, panels, _forbidden = N.load_dev_panels(args.panels)
    expected_n = int(manifest['n'])
    short = {c: len(p['units']) for c, p in panels.items()
             if len(p['units']) != expected_n}
    if short:
        # Ruling 6: the target answer is a function of the unit index, so a prefix or any
        # other subset of a cell is NOT a smaller unbiased sample of it.  Cells are scored
        # whole or not at all; `--cells` splits work by CELL, never inside one.
        raise SystemExit(f'refusing to score partial cells {short}: the manifest registers '
                         f'{expected_n} units per cell and the answer is a function of the '
                         f'unit index, so a prefix is not a smaller version of the cell')
    for cell, row in manifest['cells'].items():
        if cell in panels and int(row.get('n', expected_n)) != expected_n:
            raise SystemExit(f'{cell}: manifest says n={row["n"]}, suite says n={expected_n}')
    order = [c for c in manifest['cell_order'] if c in panels]
    if args.cells:
        wanted = [c for c in args.cells.split(',') if c]
        unknown = [c for c in wanted if c not in panels]
        if unknown:
            raise SystemExit(f'unknown cell(s): {unknown}')
        order = [c for c in order if c in wanted]
    phase, arm = saved.get('phase'), saved.get('arm')
    operator = oracle = tables = None
    trained = None
    if args.arch == 'D':
        operator = verified_operator(args.operator)
        if operator.fingerprint != saved.get('operator_fingerprint', operator.fingerprint):
            raise SystemExit('this checkpoint was trained with a different frozen operator')
        oracle = None if args.no_oracle else V1.OracleOperator()
        operators = dict(trained_operator=operator)
        if oracle is not None:
            operators['oracle_operator'] = oracle
        tables = V3.TableCache(operators)
    else:
        trained = LE.trained_ranges(dict(train_hops=_trained_hops(phase, arm), train_people=6))
    operator_before = None if operator is None else operator.fingerprint

    began = time.monotonic()
    cells, transcripts = {}, {}
    # V3.audit_unit / B1.aggregate look a cell up by NAME in V3.CELLS; the data
    # module lends them the new names for the duration and restores the table.
    with N.registered_cells():
        for cell in order:
            cfg = dict(N.DEV_CELLS[cell], name=cell)
            units = panels[cell]['units']
            if args.arch == 'D':
                row, native = score_dispatcher_cell(model, flags, operator, oracle, units, cfg,
                                                    args.eval_cap, tables)
                headline = dict(answers=row['answers'], strict=row['strict'],
                                mean_calls=round(row['mean_calls'], 3), over_cap=row['over_cap'])
            else:
                row, native = score_transformer_cell(model, units, cfg, args.capacity, trained,
                                                     args.block)
                headline = dict(answers=row['answers'], strict=row['strict'],
                                mean_output_tokens=round(row['mean_output_tokens'], 3),
                                no_end=row['no_end'])
            mark = FAMILY_MARK[family_of(cell)]
            row.update(cell=cell, family=family_of(cell), n=len(units),
                       sides=1 + int(cfg['kind'] == 'pair'), hops=cfg['hops'], people=cfg['people'],
                       terminal=cfg['terminal'], fixed_terminal=cfg['fixed_terminal'],
                       kind=cfg['kind'], invariant=cfg['invariant'], title=cfg['title'], mark=mark,
                       marked=bool(mark is not None
                                   and row['answers'] >= mark and row['strict'] >= mark))
            cells[cell] = row
            transcripts[cell] = native
            print(json.dumps(dict(cell=cell, family=family_of(cell), hops=cfg['hops'],
                                  mark=mark, **headline)), flush=True)
    if operator is not None and operator.fingerprint != operator_before:
        raise RuntimeError('the frozen operator changed during scoring')

    out = Path(args.out)
    report = dict(
        kind='novelty19-score', arch=args.arch, seed=int(saved['seed']), phase=phase, arm=arm,
        updates_done=saved.get('updates_done'), total_updates=saved.get('total_updates'),
        checkpoint=str(Path(args.ckpt).resolve()), checkpoint_sha256=sha(Path(args.ckpt)),
        # N8: hashed and matched against the run's own record BEFORE torch.load ran.
        checkpoint_verified_before_load=saved.get('_verified_on_disk'),
        final_weight_fingerprint=saved.get('final_weight_fingerprint'),
        data_fingerprint=saved.get('data_fingerprint'),
        update_fingerprint=saved.get('update_fingerprint'),
        panels=str(Path(args.panels).resolve()),
        panel_manifest_sha256=sha(Path(args.panels) / 'manifest.json'),
        panel_guard=guard, n_per_cell=int(manifest['n']),
        cell_order=order, cells_scored=len(order), cells=cells,
        scoring=('D: greedy (argmax) native episodes, cap %d, strict = correct subject, '
                 'operation and returned token at every call, in order, with STOP '
                 'immediately after the requested terminal lookup' % args.eval_cap)
        if args.arch == 'D' else
        ('T: greedy (argmax) decoding at the common output capacity %d, strict = the exact '
         'gold steps sequence and END immediately after the answer' % args.capacity),
        capacity_note=('the registered common output capacity is a single fixed value for '
                       'EVERY cell, not the per-cell hops+1+margin rule that '
                       'fable_baseline_length_eval defaults to')
        if args.arch == 'T' else None,
        eval_cap=args.eval_cap if args.arch == 'D' else None,
        output_capacity=args.capacity if args.arch == 'T' else None,
        registered_eval_cap=D_EVAL_CAP, registered_output_capacity=T_OUTPUT_CAPACITY,
        registered_caps=bool(args.eval_cap == D_EVAL_CAP
                             and args.capacity == T_OUTPUT_CAPACITY),
        # must-fix 3: what this checkpoint IS, so the report can bind the score to a run
        # instead of trusting the filename.  `run_dir` is where completion.json must live.
        run_dir=str(Path(args.ckpt).resolve().parent),
        expected_updates=AWAKE_UPDATES if phase == 'awake' else OFFLINE_UPDATES,
        is_final_checkpoint=bool(saved.get('updates_done') is not None
                                 and saved.get('updates_done') == saved.get('total_updates')),
        oracle_operator_diagnostic=bool(args.arch == 'D' and not args.no_oracle),
        operator=None if operator is None else operator.describe(),
        trained_ranges=trained, marks=dict(FAMILY_MARK), primary_cells=list(PRIMARY_CELLS),
        fit_cells=list(FIT_CELLS), scoring_seconds=time.monotonic() - began,
        peak_rss_bytes=peak_rss_bytes(), host=host_profile(),
        source_fingerprint=source_fingerprint(), argv=list(sys.argv), created_unix=time.time())
    out.parent.mkdir(parents=True, exist_ok=True)
    write_new(out, report)
    if args.transcripts:
        Path(args.transcripts).parent.mkdir(parents=True, exist_ok=True)
        write_new(Path(args.transcripts), transcripts)
    print(json.dumps(dict(event='scored', arch=args.arch, seed=report['seed'], phase=phase,
                          arm=arm, cells=len(order),
                          seconds=round(report['scoring_seconds'], 1),
                          out=str(out.resolve()))), flush=True)
    return report


# =========================================================================== collection


def run_key(arch, seed, phase, arm):
    return f'{phase}-{arch}-s{int(seed)}' + (f'-{arm}' if arm else '')


def registered_caps_of(payload):
    """Must-fix 4: the registered scoring knobs, re-checked at merge time.

    D is scored at eval cap 16 and T at output capacity 12.  Those are constants of the
    preregistration, not options, so a file produced at any other value is a diagnostic
    and can never become part of a registered run -- and two files at different caps can
    never be merged into one, which would silently mix two measurements.
    """
    problems = []
    arch = payload.get('arch')
    cap = payload.get('eval_cap')
    capacity = payload.get('output_capacity')
    if arch == 'D':
        if cap != D_EVAL_CAP:
            problems.append(f'eval_cap is {cap!r}, the registered value is {D_EVAL_CAP}')
        if capacity is not None:
            problems.append(f'a D score file carries output_capacity {capacity!r}')
    else:
        if capacity != T_OUTPUT_CAPACITY:
            problems.append(f'output_capacity is {capacity!r}, the registered value is '
                            f'{T_OUTPUT_CAPACITY}')
        if cap is not None:
            problems.append(f'a T score file carries eval_cap {cap!r}')
    return problems, dict(eval_cap=cap, output_capacity=capacity,
                          oracle_operator_diagnostic=payload.get('oracle_operator_diagnostic'))


def checkpoint_binding(payload):
    """Must-fix 3: is this score the FINAL checkpoint of a COMPLETED run?

    A mid-run checkpoint scores perfectly well -- it is just not the result.  The score
    file must name a checkpoint whose run directory holds a `completion.json` that agrees
    on architecture, seed, phase, arm and update count, and whose recorded sha256 is the
    sha256 this score was taken from.  When the checkpoint file itself is still on disk,
    its bytes are re-hashed too.
    """
    problems = []
    phase = payload.get('phase')
    expect = AWAKE_UPDATES if phase == 'awake' else OFFLINE_UPDATES
    for field in ('updates_done', 'total_updates'):
        value = payload.get(field)
        if value is None or int(value) != expect:
            problems.append(f'{field}={value!r}, the registered {phase} run is {expect} updates')
    ckpt = Path(str(payload.get('checkpoint', '')))
    done_path = ckpt.parent / 'completion.json'
    if not done_path.is_file():
        problems.append(f'no completion.json beside {ckpt} -- the run it came from never '
                        f'finished, or the score does not point at a run directory')
    else:
        done = json.loads(done_path.read_text())
        if done.get('complete') is not True:
            problems.append(f'{done_path} does not record a complete run')
        if Path(str(done.get('checkpoint', ''))).name != ckpt.name:
            problems.append(f'{done_path} finished on {Path(str(done.get("checkpoint"))).name}, '
                            f'this score is of {ckpt.name}')
        if done.get('checkpoint_sha256') != payload.get('checkpoint_sha256'):
            problems.append(f'checkpoint sha256 {str(payload.get("checkpoint_sha256"))[:16]}... '
                            f'is not the {str(done.get("checkpoint_sha256"))[:16]}... that '
                            f'{done_path} recorded')
        for field in ('arch', 'phase', 'arm'):
            if done.get(field) != payload.get(field):
                problems.append(f'{field}: run says {done.get(field)!r}, score says '
                                f'{payload.get(field)!r}')
        if int(done.get('seed', -1)) != int(payload.get('seed', -2)):
            problems.append(f'seed: run says {done.get("seed")!r}, score says '
                            f'{payload.get("seed")!r}')
        if int(done.get('total_updates', -1)) != expect:
            problems.append(f'the run itself recorded {done.get("total_updates")!r} updates')
    if ckpt.is_file() and sha(ckpt) != payload.get('checkpoint_sha256'):
        problems.append(f'{ckpt} no longer hashes to the value this score was taken from')
    return problems


def collect_scores(exp, *, seeds=REGISTERED_SEEDS):
    """Merge every score file under EXP/scores into one run -> cells map.

    Several PARTIAL score files (one per scoring wave's `--cells` range) merge into one
    run.  Disagreeing checkpoints are a conflict, never a silent overwrite.

    A file is only merged once it has been BOUND to a finished run at the registered caps
    (`checkpoint_binding`, `registered_caps_of`).  Anything else -- a mid-run checkpoint,
    a checkpoint whose run never completed, a sha that does not match the run's own
    record, a file produced at `--eval-cap 4` -- is listed in `rejected` and its run is
    left absent, so it appears in `missing` and prints as "(wrong checkpoint)".  It is
    never merged and never averaged in.
    """
    folder = Path(exp) / 'scores'
    runs, conflicts, files, rejected = {}, [], [], []
    for path in sorted(folder.glob('*.json')) if folder.is_dir() else []:
        payload = json.loads(path.read_text())
        if payload.get('kind') != 'novelty19-score':
            continue
        files.append(dict(path=str(path), sha256=sha(path)))
        key = run_key(payload['arch'], payload['seed'], payload['phase'], payload.get('arm'))
        cap_problems, caps = registered_caps_of(payload)
        problems = checkpoint_binding(payload) + cap_problems
        if problems:
            rejected.append(dict(run=key, path=str(path), sha256=sha(path), reasons=problems))
            continue
        entry = runs.setdefault(key, dict(
            arch=payload['arch'], seed=int(payload['seed']), phase=payload['phase'],
            arm=payload.get('arm'), checkpoint_sha256=payload['checkpoint_sha256'],
            checkpoint=payload['checkpoint'], updates_done=payload.get('updates_done'),
            panel_manifest_sha256=payload['panel_manifest_sha256'],
            panels=payload.get('panels'),
            panel_guard=payload.get('panel_guard'), n_per_cell=payload.get('n_per_cell'),
            data_fingerprint=payload.get('data_fingerprint'),
            update_fingerprint=payload.get('update_fingerprint'),
            source_fingerprint=payload.get('source_fingerprint'),
            total_updates=payload.get('total_updates'), caps=caps,
            cells={}, sources=[]))
        if entry['checkpoint_sha256'] != payload['checkpoint_sha256']:
            conflicts.append(dict(run=key, path=str(path), reason='two checkpoints for one run'))
            continue
        if entry['panel_manifest_sha256'] != payload['panel_manifest_sha256']:
            conflicts.append(dict(run=key, path=str(path), reason='two panel suites for one run'))
            continue
        if entry['source_fingerprint'] != payload.get('source_fingerprint'):
            # two waves of one run scored by two different script versions
            conflicts.append(dict(run=key, path=str(path),
                                  reason='two trainer versions for one run'))
            continue
        if entry['caps'] != caps:
            # must-fix 4: two measurements taken at different caps are two different
            # numbers; they are never pooled into one run.
            conflicts.append(dict(run=key, path=str(path), reason='two scoring caps for one run',
                                  have=entry['caps'], got=caps))
            continue
        for cell, row in payload['cells'].items():
            if cell in entry['cells'] and entry['cells'][cell] != row:
                conflicts.append(dict(run=key, path=str(path), cell=cell,
                                      reason='two different scores for one cell'))
                continue
            entry['cells'][cell] = row
        entry['sources'].append(str(path))
    expected = [run_key('D', s, 'awake', None) for s in seeds] \
        + [run_key('T', s, 'awake', None) for s in seeds] \
        + [run_key(a, s, 'offline', arm) for s in seeds for a in ARCHES for arm in ARMS]
    missing = [key for key in expected if key not in runs]
    incomplete = {key: sorted(set(N.DEV_CELL_ORDER) - set(runs[key]['cells']))
                  for key in runs if set(runs[key]['cells']) != set(N.DEV_CELL_ORDER)}
    rejected_runs = {}
    for item in rejected:
        rejected_runs.setdefault(item['run'], []).extend(item['reasons'])
    return dict(runs=runs, expected=expected, missing=missing, incomplete=incomplete,
                conflicts=conflicts, files=files, rejected=rejected,
                rejected_runs=rejected_runs)


def buffer_folders(exp):
    """Every buffer folder of an experiment, in the data module's registered layout.

    `EXPERIMENT_LAYOUT` puts them at `<exp>/buffers-<seed>`; a `<exp>/buffers/<name>`
    tree is also accepted so a wave can keep its own arrangement.  The seed always
    comes from the manifest, never from the folder name.
    """
    root = Path(exp)
    found = {}
    for pattern in ('buffers-*/manifest.json', 'buffers/*/manifest.json'):
        for path in sorted(root.glob(pattern)):
            if (path.parent / 'audit.json').is_file():
                found[str(path.parent.resolve())] = path.parent
    return list(found.values())


def collect_generation_gates(exp):
    """Builder A's per-seed generation-gate audit (section 5), read from disk."""
    out = {}
    for folder in buffer_folders(exp):
        path = folder / 'audit.json'
        audit = json.loads(path.read_text())
        gate = audit.get('generation_gate')
        out[str(audit['seed'])] = dict(
            path=str(path), sha256=sha(path), seed=int(audit['seed']),
            passed=None if gate is None else bool(gate['passed']),
            structures=None if gate is None else {
                k: dict(distinct_questions=v['distinct_questions'],
                        distinct_worlds=v['distinct_worlds'],
                        awake_instances=v['awake_instances'], required=v['required'],
                        passed=v['passed'])
                for k, v in gate['structures'].items()},
            identical_world_bytes=audit['identical_world_bytes']['identical'],
            zero_composite_r10_exposure=audit['composite_r10_exposure']['zero_exposure'],
            fallbacks={a: audit['per_arm'][a]['fallbacks'] for a in audit['arms']},
            length_histogram={a: audit['per_arm'][a]['length_histogram'] for a in audit['arms']})
    return out


def awake_fit_gate(entry):
    """Section 5: >= 61/64 answers AND >= 61/64 strict in every one of the 7 F cells.

    Note N1: a DEFINITE failure dominates an absence.  One F cell scored below the mark
    means the gate did not hold, whatever the other cells do -- the run cannot be rescued
    by scoring the rest, so calling it "undetermined" would misreport it (and would let
    the forgetting screen treat a failed seat as merely unscored).  Only when every
    scored cell passes and some are absent is the verdict None.
    """
    per_cell = {}
    for cell in FIT_CELLS:
        row = entry['cells'].get(cell) if entry else None
        if row is None:
            per_cell[cell] = dict(present=False, answers=None, strict=None, passed=None)
            continue
        ok = bool(row['answers'] >= AWAKE_FIT_MARK and row['strict'] >= AWAKE_FIT_MARK)
        per_cell[cell] = dict(present=True, n=row['n'], need=AWAKE_FIT_MARK,
                              answers=row['answers'], strict=row['strict'], passed=ok)
    verdicts = [v['passed'] for v in per_cell.values()]
    passed = (False if any(v is False for v in verdicts)
              else (None if any(v is None for v in verdicts) else True))
    return dict(need=AWAKE_FIT_MARK, cells=per_cell, passed=passed,
                failed_cells=[c for c, v in per_cell.items() if v['passed'] is False],
                absent_cells=[c for c, v in per_cell.items() if v['passed'] is None])


def identical_questions(collected, *, seeds=REGISTERED_SEEDS):
    """Note N7: D and T must have consumed byte-identical questions, as a recorded fact.

    Every checkpoint carries `data_fingerprint`, a chained sha256 over the raw question
    bytes of every update it trained on.  Comparing D's against T's per seed and per arm
    turns "I checked it by hand once" into something the gates command asserts.
    """
    out = {}
    for seed in seeds:
        for phase, arm in (('awake', None),) + tuple(('offline', a) for a in ARMS):
            label = f's{int(seed)}|' + (phase if arm is None else f'offline-{arm}')
            got = {arch: (collected['runs'].get(run_key(arch, seed, phase, arm)) or {})
                   .get('data_fingerprint') for arch in ARCHES}
            out[label] = dict(**got, identical=(None if any(v is None for v in got.values())
                                                else bool(len(set(got.values())) == 1)))
    values = [v['identical'] for v in out.values()]
    return dict(per_run=out,
                passed=(False if any(v is False for v in values)
                        else (None if any(v is None for v in values) else True)),
                note='a chained sha256 over the raw question bytes of every update; equal '
                     'digests mean the two architectures saw the same questions in the '
                     'same order, and null means a run is not on disk')


def trainer_version(collected, *, seeds=REGISTERED_SEEDS):
    """M-2: every merged run must come from ONE frozen script version.

    `checkpoint_sha256` embeds `source_fingerprint()`, so a mixed trainer makes the
    checkpoint hashes of different runs incomparable and quietly mixes two recipes.  The
    fingerprint was written into every artifact and read back nowhere, which made "one
    frozen script version" a launch instruction rather than a checked fact.

    Comparison is over the WHOLE fingerprint -- this module, the seven frozen modules it
    imports and the torch version -- not just this file, because a drift in any of them
    changes what the numbers mean.  A run with no fingerprint at all is a refusal, not an
    unknown: it was not written by this script.
    """
    per_run, seen, absent = {}, {}, []
    for key, entry in sorted(collected['runs'].items()):
        got = entry.get('source_fingerprint')
        per_run[key] = got
        if not isinstance(got, dict) or not got:
            absent.append(key)
            continue
        seen.setdefault(json.dumps(got, sort_keys=True), []).append(key)
    versions = [dict(fingerprint=json.loads(text), runs=runs)
                for text, runs in sorted(seen.items(), key=lambda kv: (len(kv[1]), kv[1]))]
    keys = sorted({k for v in versions for k in v['fingerprint']})
    differing = sorted(k for k in keys
                       if len({json.dumps(v['fingerprint'].get(k)) for v in versions}) > 1)
    if not collected['runs']:
        passed, offenders = None, []
    elif absent:
        passed, offenders = False, list(absent)
    elif len(versions) > 1:
        # the minority versions are the ones to look at first
        passed = False
        offenders = [r for v in versions[:-1] for r in v['runs']]
    else:
        passed, offenders = True, []
    return dict(passed=passed, distinct=len(versions), versions=versions,
                per_run=per_run, runs_without_a_fingerprint=absent,
                differing_fields=differing, offending_runs=offenders,
                note=('every merged run must carry one identical source_fingerprint -- this '
                      'script plus the frozen modules it imports plus the torch version.  A '
                      'run without one is refused; null means nothing was merged to compare.'))


def gates(args):
    collected = collect_scores(args.exp, seeds=args.seed_list)
    fit = {}
    for arch in ARCHES:
        for seed in args.seed_list:
            key = run_key(arch, seed, 'awake', None)
            fit[key] = dict(arch=arch, seed=int(seed), present=key in collected['runs'],
                            **awake_fit_gate(collected['runs'].get(key)))
    generation = collect_generation_gates(args.exp)
    verdict = dict(
        kind='novelty19-gates', experiment=str(Path(args.exp).resolve()),
        seeds=list(args.seed_list), awake_fit_gate=fit,
        awake_fit_gate_passed={arch: (None if any(
            fit[run_key(arch, s, 'awake', None)]['passed'] is None for s in args.seed_list)
            else bool(all(fit[run_key(arch, s, 'awake', None)]['passed']
                          for s in args.seed_list))) for arch in ARCHES},
        generation_gate=generation,
        generation_gate_passed={s: generation.get(str(s), {}).get('passed')
                                for s in args.seed_list},
        identical_questions=identical_questions(collected, seeds=args.seed_list),
        single_trainer_version=trainer_version(collected, seeds=args.seed_list),
        missing_runs=collected['missing'], conflicts=collected['conflicts'],
        rejected_score_files=collected['rejected'],
        note=('a missing run is reported as null -- never as a zero and never as a pass.  '
              'A failing architecture has not met the prerequisite under this recipe; its '
              'registered offline claim stops and its failed seeds are never omitted.'),
        source_fingerprint=source_fingerprint(), argv=list(sys.argv), created_unix=time.time())
    print(json.dumps({k: v for k, v in verdict.items()
                      if k not in ('source_fingerprint', 'argv')}, indent=2), flush=True)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        write_new(Path(args.out), verdict)
    version = verdict['single_trainer_version']
    if version['passed'] is False:
        # written first, then refused: the artifact of record still exists.
        raise SystemExit(
            f'the merged runs were not produced by one frozen script version '
            f'({version["distinct"]} distinct, differing in {version["differing_fields"]}; '
            f'{len(version["runs_without_a_fingerprint"])} without a fingerprint).  '
            f'Offending runs: {version["offending_runs"]}')
    return verdict


# =========================================================================== report


MISSING = '(missing)'
WRONG_CKPT = '(wrong checkpoint)'   # a score file that exists but is not bound to the run


def cell_pair(row):
    """'ans/str' for one cell, or the literal '(missing)' -- never a zero, never a pass."""
    return MISSING if row is None else f'{row["answers"]:>2}/{row["strict"]:>2}'


def signed(value):
    return MISSING if value is None else f'{value:+d}'


def primary_verdict(collected, arch, treatment='G', *, seeds=REGISTERED_SEEDS):
    """Section 6 primary rule, evaluated cell by cell and seed by seed.

    A cell-seed passes when the treatment arm reaches >= 58/64 on BOTH answers and strict
    AND beats its own R arm by >= 13/64 strict.  Anything not on disk is null, which makes
    the whole verdict null: a run that did not happen is not a pass and is not a failure.
    """
    per, decided = {}, True
    for seed in seeds:
        treat = collected['runs'].get(run_key(arch, seed, 'offline', treatment))
        replay = collected['runs'].get(run_key(arch, seed, 'offline', 'R'))
        for cell in PRIMARY_CELLS:
            trow = (treat or {}).get('cells', {}).get(cell)
            rrow = (replay or {}).get('cells', {}).get(cell)
            gain = None if (trow is None or rrow is None) else trow['strict'] - rrow['strict']
            ok = None if (trow is None or gain is None) else bool(
                trow['answers'] >= PRIMARY_MARK and trow['strict'] >= PRIMARY_MARK
                and gain >= PRIMARY_GAIN)
            decided = False if ok is None else decided
            per[f's{int(seed)}|{cell}'] = dict(
                seed=int(seed), cell=cell, arm=treatment,
                treatment=None if trow is None else dict(answers=trow['answers'],
                                                         strict=trow['strict'], n=trow['n']),
                replay=None if rrow is None else dict(answers=rrow['answers'],
                                                      strict=rrow['strict'], n=rrow['n']),
                strict_gain=gain, need_mark=PRIMARY_MARK, need_gain=PRIMARY_GAIN, passed=ok)
    return dict(arch=arch, arm=treatment, cells=list(PRIMARY_CELLS), seeds=list(seeds),
                per_cell_seed=per,
                passed=(None if not decided else bool(all(v['passed'] for v in per.values()))),
                note='every cell in every seed must pass; no averaging across seeds')


def secondary_family(collected, arch, family, *, seeds=REGISTERED_SEEDS):
    cells = [c for c in N.DEV_CELL_ORDER if family_of(c) == family]
    mark, rows = FAMILY_MARK[family], {}
    for seed in seeds:
        for arm in ('awake',) + ARMS:
            key = (run_key(arch, seed, 'awake', None) if arm == 'awake'
                   else run_key(arch, seed, 'offline', arm))
            entry = collected['runs'].get(key)
            for cell in cells:
                row = (entry or {}).get('cells', {}).get(cell)
                rows[f's{int(seed)}|{arm}|{cell}'] = (
                    None if row is None else dict(answers=row['answers'], strict=row['strict'],
                                                  n=row['n'], mark=mark,
                                                  marked=None if mark is None else row['marked']))
    return dict(family=family, cells=cells, mark=mark, descriptive=mark is None, rows=rows,
                title=FAMILY_TITLE.get(family, ''))


def calls_ceiling(collected, arch, *, seeds=REGISTERED_SEEDS):
    """Diagnostic, not a gate: is the search cap, rather than the policy, ending episodes?"""
    field = 'mean_calls' if arch == 'D' else 'mean_output_tokens'
    ceiling = D_EVAL_CAP if arch == 'D' else T_OUTPUT_CAPACITY
    rows, worst = {}, None
    for seed in seeds:
        for arm in ('awake',) + ARMS:
            key = (run_key(arch, seed, 'awake', None) if arm == 'awake'
                   else run_key(arch, seed, 'offline', arm))
            entry = collected['runs'].get(key)
            # must-fix 4: divide by the cap this run was ACTUALLY scored at.  Only the
            # registered value survives `collect_scores`, so the two agree for any merged
            # run -- but the diagnostic reads the recorded number rather than assuming it.
            caps = (entry or {}).get('caps') or {}
            ceiling = ((caps.get('eval_cap') if arch == 'D' else caps.get('output_capacity'))
                       or (D_EVAL_CAP if arch == 'D' else T_OUTPUT_CAPACITY))
            for cell in N.DEV_CELL_ORDER:
                row = (entry or {}).get('cells', {}).get(cell)
                if row is None:
                    rows[f's{int(seed)}|{arm}|{cell}'] = None
                    continue
                pressure = float(row[field]) / float(ceiling)
                item = dict(value=round(float(row[field]), 3), ceiling=ceiling,
                            hops=row['hops'], headroom=round(ceiling - float(row[field]), 3),
                            fraction_of_ceiling=round(pressure, 4),
                            over_cap=row.get('over_cap'), no_end=row.get('no_end'))
                rows[f's{int(seed)}|{arm}|{cell}'] = item
                if worst is None or pressure > worst[1]['fraction_of_ceiling']:
                    worst = (f's{int(seed)}|{arm}|{cell}', item)
    return dict(arch=arch, field=field,
                ceiling=D_EVAL_CAP if arch == 'D' else T_OUTPUT_CAPACITY, rows=rows,
                ceilings_seen=sorted({v['ceiling'] for v in rows.values() if v is not None}),
                worst=None if worst is None else dict(where=worst[0], **worst[1]),
                note=('a mean near the ceiling means the cap is truncating the search, so the '
                      'cell measures the cap and not the model'))


FAMILY_TITLE = dict(N='novel structures (primary)', E='exchangeability invariants',
                    F='ordinary awake fit', P='pressure / longer chains',
                    H='held-out relation types (descriptive)', L='length generalisation')


def print_cell_table(collected, arch, seed, out):
    """One table per architecture x seed.  Seeds are never pooled or averaged."""
    arms = ('awake',) + ARMS
    keys = {a: (run_key(arch, seed, 'awake', None) if a == 'awake'
                else run_key(arch, seed, 'offline', a)) for a in arms}
    entries = {a: collected['runs'].get(k) for a, k in keys.items()}
    out(f'\n--- arch {arch}  seed {int(seed)} ---')
    for arm in arms:
        state = 'present' if entries[arm] else MISSING
        if entries[arm] and keys[arm] in collected['incomplete']:
            state = f'partial ({len(entries[arm]["cells"])}/{len(N.DEV_CELL_ORDER)} cells)'
        out(f'    {arm:<6} {keys[arm]:<22} {state}')
    head = f'    {"cell":<16}{"fam":<4}{"c":>2}  ' + ''.join(f'{a:>11}' for a in arms)
    out(head + f'{"G-R":>7}{"U-R":>7}{"mark":>6}  verdict')
    out('    ' + '-' * (len(head) + 16))
    for cell in N.DEV_CELL_ORDER:
        rows = {a: (entries[a] or {}).get('cells', {}).get(cell) for a in arms}
        gr = (None if rows['G'] is None or rows['R'] is None
              else rows['G']['strict'] - rows['R']['strict'])
        ur = (None if rows['U'] is None or rows['R'] is None
              else rows['U']['strict'] - rows['R']['strict'])
        mark = FAMILY_MARK[family_of(cell)]
        if cell in PRIMARY_CELLS:
            ok = (None if rows['G'] is None or gr is None else
                  bool(rows['G']['answers'] >= PRIMARY_MARK and rows['G']['strict'] >= PRIMARY_MARK
                       and gr >= PRIMARY_GAIN))
            verdict = MISSING if ok is None else ('PASS' if ok else 'fail')
        elif mark is None:
            verdict = 'descriptive'
        else:
            ok = None if rows['G'] is None else rows['G']['marked']
            verdict = MISSING if ok is None else ('mark' if ok else 'below')
        out(f'    {cell:<16}{family_of(cell):<4}{N.DEV_CELLS[cell]["hops"]:>2}  '
            + ''.join(f'{cell_pair(rows[a]):>11}' for a in arms)
            + f'{signed(gr):>7}{signed(ur):>7}'
            + f'{("-" if mark is None else mark):>6}  {verdict}')


def report(args):
    exp = Path(args.exp).resolve()
    seeds = args.seed_list
    collected = collect_scores(exp, seeds=seeds)
    lines = []

    def out(text=''):
        lines.append(text)
        print(text, flush=True)

    out('=' * 96)
    out(f'novelty-19 report   experiment={exp}')
    out(f'seeds={list(map(int, seeds))}   answers/strict are out of 64 per cell   '
        f'"{MISSING}" means the run is not on disk')
    out(f'score files found: {len(collected["files"])}   '
        f'rejected: {len(collected["rejected"])}   '
        f'runs expected: {len(collected["expected"])}   missing: {len(collected["missing"])}')
    for key in collected['missing']:
        label = WRONG_CKPT if key in collected['rejected_runs'] else MISSING
        out(f'    {label} {key}')
    for bad in collected['rejected']:
        out(f'    {WRONG_CKPT} {bad["run"]}  {bad["path"]}')
        for reason in bad['reasons']:
            out(f'        {reason}')
    for bad in collected['conflicts']:
        out(f'    CONFLICT {bad}')

    out('\n' + '=' * 96)
    out('gates')
    fit = {}
    for arch in ARCHES:
        for seed in seeds:
            key = run_key(arch, seed, 'awake', None)
            verdict = awake_fit_gate(collected['runs'].get(key))
            fit[key] = verdict
            state = (MISSING if verdict['passed'] is None
                     else ('PASS' if verdict['passed'] else 'FAIL'))
            detail = '  '.join(
                f'{c.split("-", 1)[1]}={cell_pair(collected["runs"].get(key, {}).get("cells", {}).get(c))}'
                for c in FIT_CELLS)
            out(f'    awake fit {arch} s{int(seed)} need {AWAKE_FIT_MARK}/64 both: '
                f'{state}   {detail}')
    generation = collect_generation_gates(exp)
    for seed in seeds:
        info = generation.get(str(int(seed)))
        if info is None:
            out(f'    generation gate s{int(seed)}: {MISSING} '
                f'(no buffers-{int(seed)}/audit.json)')
            continue
        state = 'PASS' if info['passed'] else 'FAIL'
        detail = '  '.join(f'{k}={v["distinct_questions"]}q/{v["distinct_worlds"]}w'
                           for k, v in sorted(info['structures'].items()))
        out(f'    generation gate s{int(seed)}: {state}   {detail}   '
            f'identical_world_bytes={info["identical_world_bytes"]}  '
            f'zero_composite_r10_exposure={info["zero_composite_r10_exposure"]}')

    out('\n' + '=' * 96)
    out('per seed x arch x arm x cell   (never averaged across seeds)')
    for arch in ARCHES:
        for seed in seeds:
            print_cell_table(collected, arch, seed, out)

    out('\n' + '=' * 96)
    out(f'primary rule: every N cell in every seed needs >= {PRIMARY_MARK}/64 answers AND strict '
        f'in the generated arm, and >= {PRIMARY_GAIN}/64 strict over that seed\'s replay arm')
    primary = {}
    for arch in ARCHES:
        for treatment in ('G', 'U'):
            verdict = primary_verdict(collected, arch, treatment, seeds=seeds)
            primary[f'{arch}-{treatment}'] = verdict
            state = (MISSING if verdict['passed'] is None
                     else ('PASS' if verdict['passed'] else 'fail'))
            label = 'registered primary' if treatment == 'G' else 'unstructured control'
            decided = sum(1 for v in verdict['per_cell_seed'].values() if v['passed'] is not None)
            won = sum(1 for v in verdict['per_cell_seed'].values() if v['passed'])
            out(f'    {arch} arm {treatment} ({label}): {state}   '
                f'{won}/{len(verdict["per_cell_seed"])} cell-seeds pass, {decided} decided')
            for name, item in verdict['per_cell_seed'].items():
                if item['passed']:
                    continue
                out(f'        {name:<26} treat={cell_pair(item["treatment"])} '
                    f'replay={cell_pair(item["replay"])} gain={signed(item["strict_gain"])} '
                    f'-> {MISSING if item["passed"] is None else "fail"}')

    out('\n' + '=' * 96)
    out('secondary families (reported for completeness; they do not decide the primary claim)')
    secondary = {}
    for arch in ARCHES:
        for family in ('E', 'F', 'P', 'H', 'L'):
            block = secondary_family(collected, arch, family, seeds=seeds)
            secondary[f'{arch}-{family}'] = block
            present = [v for v in block['rows'].values() if v is not None]
            if block['descriptive']:
                out(f'    {arch} {family} {block["title"]}: descriptive only, no mark   '
                    f'{len(present)}/{len(block["rows"])} scored')
                continue
            marked = sum(1 for v in present if v['marked'])
            out(f'    {arch} {family} {block["title"]}: mark {block["mark"]}/64   '
                f'{marked}/{len(present)} scored rows reach it   '
                f'{len(block["rows"]) - len(present)} {MISSING}')

    out('\n' + '=' * 96)
    out('mean call / output-length ceiling diagnostic')
    ceilings = {}
    for arch in ARCHES:
        block = calls_ceiling(collected, arch, seeds=seeds)
        ceilings[arch] = block
        if block['worst'] is None:
            out(f'    {arch}: {MISSING} -- nothing scored')
            continue
        worst = block['worst']
        out(f'    {arch}: {block["field"]} against ceiling {block["ceiling"]}; '
            f'closest approach {worst["value"]} at {worst["where"]} '
            f'(c={worst["hops"]}, headroom {worst["headroom"]}, '
            f'{worst["fraction_of_ceiling"] * 100:.1f}% of ceiling)')
        crowded = [k for k, v in block['rows'].items()
                   if v is not None and v['fraction_of_ceiling'] >= 0.75]
        out(f'        cells at >= 75% of the ceiling: '
            f'{len(crowded)}' + (f'   {crowded[:8]}' if crowded else ''))

    out('\n' + '=' * 96)
    out(f'replicated forgetting screen (ruling 7, SECONDARY -- it cannot alter the primary '
        f'verdict): awake-final minus offline-final on the {len(FIT_CELLS)} F and '
        f'{len(FORGET_CELLS) - len(FIT_CELLS)} H cells, answers and strict kept apart, each '
        f'out of 64 and never added')
    out(f'    a trigger needs ONE fixed (arch, arm, cell, metric) losing >= {FORGET_DROP}/64 '
        f'in >= {FORGET_REPLICATIONS} of the {len(seeds)} registered seeds; the denominator '
        f'stays {len(seeds)} seeds')
    forgetting = {}
    for arch in ARCHES:
        screen = forgetting_screen(collected, arch, seeds=seeds)
        forgetting[arch] = screen
        out(f'\n    arch {arch}: {screen["outcome"]}   '
            f'{len(screen["triggered"])} triggered, {len(screen["undetermined"])} still '
            f'reachable, {len(screen["combos"])} (arm, cell, metric) combinations')
        out(f'    {"arm|cell|metric":<30}' + ''.join(f'{"s" + str(int(s)):>18}' for s in seeds)
            + f'{"reps":>6}  verdict')
        for name, combo in screen['combos'].items():
            cells_txt = ''
            for seed in seeds:
                item = combo['per_seed'][str(int(seed))]
                if item['status'] == 'missing':
                    cells_txt += f'{MISSING:>18}'
                elif item['status'] == 'gate_failed':
                    cells_txt += f'{"gate-failed":>18}'
                elif item['status'] == 'not_eligible':
                    cells_txt += '{:>18}'.format(f'awake {item["awake"]} not-elig')
                else:
                    cells_txt += '{:>18}'.format(
                        f'{item["awake"]}->{item["offline"]} d{item["delta"]:+d}')
            verdict = ('TRIGGER' if combo['triggered']
                       else ('open' if combo['still_reachable'] else 'no'))
            if combo['triggered'] or combo['still_reachable'] or combo['replications']:
                out(f'    {name:<30}{cells_txt}{combo["replications"]:>6}  {verdict}')
        if not screen['triggered'] and not screen['undetermined']:
            out('        no combination reached or can still reach the replication rule')
        out(f'    awake-fit qualification by seed: ' + '  '.join(
            f's{s}={screen["awake_fit_gate"][int(s)]}' for s in seeds))

    out('\n' + '=' * 96)
    out('accepted practice-length mix actually present in the buffers (ruling 8; the '
        '6.5% / 40% figures are neither a quota nor an exact prediction)')
    mixes = length_mix(exp, seeds=seeds)
    for seed in seeds:
        row = mixes[str(int(seed))]
        if row is None:
            out(f'    s{int(seed)}: {MISSING} (no buffers manifest/audit)')
            continue
        for arm in ('G', 'U'):
            arm_row = row['arms'].get(arm)
            if arm_row is None:
                out(f'    s{int(seed)} {arm}: {MISSING}')
                continue
            share = arm_row['four_or_five_share']
            out(f'    s{int(seed)} {arm}: {arm_row["four_or_five_calls"]}/'
                f'{arm_row["questions"]} questions at c=4/5 '
                f'({"n/a" if share is None else f"{share * 100:.1f}%"}), '
                f'{arm_row["fallbacks"]} fallbacks   {arm_row["length_histogram"]}')
        if not row['audit_sha256_matches']:
            out(f'    s{int(seed)}: CONFLICT audit.json does not match its own manifest hash')

    out('\n' + '=' * 96)
    version = trainer_version(collected, seeds=seeds)
    questions = identical_questions(collected, seeds=seeds)
    out('evidence provenance')
    state = (MISSING if version['passed'] is None
             else ('one frozen script version' if version['passed'] else 'MIXED'))
    out(f'    trainer version across {len(collected["runs"])} merged runs: {state} '
        f'({version["distinct"]} distinct)')
    if version['passed'] is False:
        out(f'        differing fields: {version["differing_fields"]}')
        out(f'        runs from another version: {version["offending_runs"]}')
        out(f'        runs with no fingerprint: {version["runs_without_a_fingerprint"]}')
    shared = (MISSING if questions['passed'] is None
              else ('identical' if questions['passed'] else 'DIFFERENT'))
    out(f'    D and T question bytes per seed and arm: {shared}')
    if questions['passed'] is False:
        out('        ' + str([k for k, v in questions['per_run'].items()
                              if v['identical'] is False]))

    out('\n' + '=' * 96)
    rule = development_rule(collected, generation, primary, seeds=seeds, version=version)
    state = MISSING if rule['passed'] is None else ('PASS' if rule['passed'] else 'fail')
    out(f'registered development rule ({rule["architecture"]}-{rule["arm"]}): {state}')
    for name, part in rule['parts'].items():
        got = part['passed']
        out(f'    {name:<20} {MISSING if got is None else ("pass" if got else "FAIL"):<9} '
            f'{part["required"]}')

    payload = dict(
        kind='novelty19-report', experiment=str(exp), seeds=list(map(int, seeds)),
        n_per_cell=V3.PANEL_N, cells=list(N.DEV_CELL_ORDER), family_marks=dict(FAMILY_MARK),
        primary=primary, secondary=secondary, ceiling=ceilings,
        forgetting_screen=forgetting, length_mix=mixes, development_rule=rule,
        forget_cells=list(FORGET_CELLS), forget_drop=FORGET_DROP,
        forget_replications=FORGET_REPLICATIONS,
        awake_fit_gate=fit, generation_gate=generation,
        runs={k: {kk: vv for kk, vv in v.items() if kk != 'cells'}
              for k, v in collected['runs'].items()},
        cells_by_run={k: v['cells'] for k, v in collected['runs'].items()},
        missing_runs=collected['missing'], incomplete_runs=collected['incomplete'],
        rejected_score_files=collected['rejected'],
        rejected_runs=collected['rejected_runs'],
        identical_questions=questions, single_trainer_version=version,
        conflicts=collected['conflicts'], score_files=collected['files'],
        text='\n'.join(lines), source_fingerprint=source_fingerprint(),
        host=host_profile(), argv=list(sys.argv), created_unix=time.time())
    target = Path(args.out) if args.out else exp / 'report.json'
    if target.exists() and args.overwrite:
        stamp = time.strftime('%Y%m%dT%H%M%S', time.gmtime())
        target = target.with_name(f'{target.stem}-{stamp}{target.suffix}')
    target.parent.mkdir(parents=True, exist_ok=True)
    write_new(target, payload)
    out(f'\nwrote {target}')

    # The unlock is decided AFTER report.json is on disk, because the record it carries
    # hashes that file.  The decision is therefore reported on the console and on the
    # returned object under `dev_passed` / `dev_passed_problems`, not inside report.json.
    flag = exp / 'DEV-PASSED.json'
    payload['dev_passed'], payload['dev_passed_problems'] = None, []
    if rule['passed'] is True:
        if flag.exists():
            out(f'{flag} already exists; leaving it untouched')
        else:
            unlock, sidecar, problems = dev_passed_payload(exp, collected, rule, target,
                                                           seeds=seeds)
            payload['dev_passed_problems'] = list(problems)
            if problems:
                out(f'NOT writing {flag}: the rule passed on the seeds given, but the '
                    f'unlock record cannot be issued')
                for problem in problems:
                    out(f'        {problem}')
            else:
                write_new(flag, unlock)
                write_new(exp / 'DEV-PASSED.meta.json', sidecar)
                out(f'wrote {flag} ({len(unlock["awake_checkpoints"])} awake + '
                    f'{len(unlock["offline_checkpoints"])} offline checkpoint hashes, '
                    f'panel manifest {unlock["dev_panels"]["manifest_sha256"][:16]}...)')
                payload['dev_passed'] = str(flag)
    else:
        out(f'not writing {flag}: the registered development rule is '
            f'{"undetermined" if rule["passed"] is None else "not met"}')
    # M-2: the same refusal `gates` makes, raised only after report.json is on disk so the
    # evidence of the mix is written down rather than lost with the exception.
    if version['passed'] is False:
        raise SystemExit(
            f'the merged runs were not produced by one frozen script version '
            f'({version["distinct"]} distinct, differing in {version["differing_fields"]}; '
            f'{len(version["runs_without_a_fingerprint"])} without a fingerprint).  '
            f'Offending runs: {version["offending_runs"]}.  '
            f'The report was still written to {target}.')
    return payload


# =========================================================================== command line


def seed_list(text):
    seeds = tuple(int(part) for part in str(text).split(',') if part != '')
    if not seeds:
        raise argparse.ArgumentTypeError('give at least one seed')
    return seeds


def bounded(name, ceiling):
    def parse(text):
        value = int(text)
        if value < 1 or value > ceiling:
            raise argparse.ArgumentTypeError(f'{name} must be in 1..{ceiling}')
        return value
    return parse


def budget_seconds(text):
    """Section 9: one wave is one invocation, and a wave may not outlive its deadline."""
    value = float(text)
    if value < 0 or value > WAVE_DEADLINE:
        raise argparse.ArgumentTypeError(
            f'--budget-seconds must be in 0..{WAVE_DEADLINE} (the registered wave deadline); '
            f'the registered compute budget is {CHUNK_SECONDS}')
    return value


def build_parser():
    parser = argparse.ArgumentParser(
        prog='fable_novelty19_train.py', description=__doc__.strip().splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    subs = parser.add_subparsers(dest='command', required=True)

    train = argparse.ArgumentParser(add_help=False)
    train.add_argument('--arch', required=True, choices=list(ARCHES),
                       help='D = dispatcher v4 reg+ctx over the frozen operator, '
                            'T = baseline v2 I1-H1')
    train.add_argument('--seed', required=True, type=int)
    train.add_argument('--out', required=True, help='run directory (created; append-only)')
    train.add_argument('--quiet', action='store_true')

    a = subs.add_parser('awake', parents=[train], help='section 2 awake training')
    a.add_argument('--stream', required=True, help="builder A's awake stream directory")
    a.add_argument('--updates', type=int, default=N.AWAKE_UPDATES)
    a.add_argument('--chunk-updates', type=bounded('--chunk-updates', N.AWAKE_CHUNK),
                   default=N.AWAKE_CHUNK, help=f'registered ceiling {N.AWAKE_CHUNK}')
    a.add_argument('--budget-seconds', type=budget_seconds, default=CHUNK_SECONDS,
                   help=f'stop after this many seconds at the next chunk boundary; '
                        f'ceiling {WAVE_DEADLINE} (the registered wave deadline)')
    a.set_defaults(handler=awake)

    o = subs.add_parser('offline', parents=[train], help='section 4 offline consolidation')
    o.add_argument('--arm', required=True, choices=list(ARMS))
    o.add_argument('--awake-ckpt', required=True, help='awake final.pt for this arch and seed')
    o.add_argument('--buffers', required=True, help="builder A's buffer directory for this seed")
    o.add_argument('--updates', type=int, default=N.OFFLINE_UPDATES)
    o.add_argument('--chunk-updates', type=bounded('--chunk-updates', N.OFFLINE_CHUNK),
                   default=N.OFFLINE_CHUNK, help=f'registered ceiling {N.OFFLINE_CHUNK}')
    o.add_argument('--budget-seconds', type=budget_seconds, default=CHUNK_SECONDS,
                   help=f'stop after this many seconds at the next chunk boundary; '
                        f'ceiling {WAVE_DEADLINE} (the registered wave deadline)')
    o.set_defaults(handler=offline)

    s = subs.add_parser('score', help='native scoring of every dev cell')
    s.add_argument('--arch', required=True, choices=list(ARCHES))
    s.add_argument('--ckpt', required=True)
    s.add_argument('--panels', required=True, help='dev panel directory')
    s.add_argument('--out', required=True, help='score JSON (never overwritten)')
    s.add_argument('--cells', default=None,
                   help='comma-separated subset, so one wave stays inside the time limit; '
                        'report merges the partial files')
    s.add_argument('--eval-cap', type=int, default=D_EVAL_CAP, help='D only')
    s.add_argument('--capacity', type=int, default=T_OUTPUT_CAPACITY, help='T only')
    s.add_argument('--block', type=int, default=32)
    s.add_argument('--operator', default=None, help='override only for a fixture test')
    s.add_argument('--no-oracle', action='store_true',
                   help='skip the oracle-operator diagnostic for D')
    s.add_argument('--confirmation', action='store_true',
                   help='score the confirmation panels; refused unless DEV-PASSED.json exists')
    s.add_argument('--experiment', default=None, help='experiment root holding DEV-PASSED.json')
    s.add_argument('--transcripts', default=None, help='optional per-item transcript JSON')
    s.set_defaults(handler=score)

    g = subs.add_parser('gates', help='awake-fit gate and the generation-gate audit')
    g.add_argument('--exp', required=True)
    g.add_argument('--seeds', dest='seed_list', type=seed_list, default=REGISTERED_SEEDS)
    g.add_argument('--out', default=None)
    g.set_defaults(handler=gates)

    r = subs.add_parser('report', help='per seed x arch x arm x cell tables and the verdicts')
    r.add_argument('--exp', required=True)
    r.add_argument('--seeds', dest='seed_list', type=seed_list, default=REGISTERED_SEEDS)
    r.add_argument('--out', default=None, help='default EXP/report.json')
    r.add_argument('--overwrite', action='store_true',
                   help='write a timestamped sibling instead of failing on an existing file')
    r.set_defaults(handler=report)
    return parser


def main(argv=None):
    torch.set_num_threads(1)
    args = build_parser().parse_args(argv)
    args.handler(args)
    return 0



# =========================================================================== ruling 7 / 8


FORGET_CELLS = FIT_CELLS + tuple(c for c in N.DEV_CELL_ORDER if c.startswith('H-'))
FORGET_DROP = 7               # awake_count - offline_count >= 7, one metric, one cell
FORGET_REPLICATIONS = 2       # in at least two of the three registered seeds
FORGET_H_ELIGIBLE = 58        # an H cell is eligible for a metric only at >= 58/64 awake
FORGET_METRICS = ('answers', 'strict')


def forgetting_screen(collected, arch, *, seeds=REGISTERED_SEEDS):
    """Ruling 7: the replicated forgetting screen.  Secondary; it cannot move the primary.

    A trigger needs ONE fixed (architecture, arm, cell, metric) to lose at least
    `FORGET_DROP` out of 64 between the awake-final and offline-final checkpoints in at
    least two of the three registered seeds.  Different cells, metrics or arms never
    combine to make the two replications.  Answer and strict counts are kept apart and
    are never added.  Missing evidence is undetermined, which is not "no forgetting".
    """
    gate, awake_rows = {}, {}
    for seed in seeds:
        key = run_key(arch, seed, 'awake', None)
        gate[int(seed)] = awake_fit_gate(collected['runs'].get(key))['passed']
        awake_rows[int(seed)] = (collected['runs'].get(key) or {}).get('cells', {})

    combos, triggered, open_combos = {}, [], []
    for arm in ARMS:
        for cell in FORGET_CELLS:
            for metric in FORGET_METRICS:
                per_seed, tally = {}, dict(drop=0, no_drop=0, not_eligible=0,
                                           gate_failed=0, missing=0)
                for seed in seeds:
                    s = int(seed)
                    offline = (collected['runs'].get(run_key(arch, seed, 'offline', arm))
                               or {}).get('cells', {})
                    a_row, o_row = awake_rows[s].get(cell), offline.get(cell)
                    a_val = None if a_row is None else int(a_row[metric])
                    o_val = None if o_row is None else int(o_row[metric])
                    delta = None if (a_val is None or o_val is None) else a_val - o_val
                    if gate[s] is None:
                        status = 'missing'
                    elif gate[s] is False:
                        status = 'gate_failed'
                    elif family_of(cell) == 'H' and a_val is not None \
                            and a_val < FORGET_H_ELIGIBLE:
                        status = 'not_eligible'
                    elif delta is None:
                        status = 'missing'
                    else:
                        status = 'drop' if delta >= FORGET_DROP else 'no_drop'
                    tally[status] += 1
                    per_seed[str(s)] = dict(
                        seed=s, awake=a_val, offline=o_val, delta=delta,
                        awake_fit_gate=gate[s], status=status,
                        eligible=bool(status in ('drop', 'no_drop')),
                        n=None if a_row is None else a_row['n'])
                name = f'{arm}|{cell}|{metric}'
                reachable = tally['drop'] + tally['gate_failed'] + tally['missing']
                combo = dict(arch=arch, arm=arm, cell=cell, family=family_of(cell),
                             metric=metric, seeds=len(seeds), per_seed=per_seed,
                             replications=tally['drop'], tally=tally,
                             triggered=bool(tally['drop'] >= FORGET_REPLICATIONS),
                             still_reachable=bool(tally['drop'] < FORGET_REPLICATIONS
                                                  and reachable >= FORGET_REPLICATIONS))
                combos[name] = combo
                if combo['triggered']:
                    triggered.append(name)
                elif combo['still_reachable'] or tally['missing'] or tally['gate_failed']:
                    # ruling 7: missing required evidence is undetermined, and a seed
                    # that never met section 5's awake qualification has not shown an
                    # absence of forgetting either.
                    open_combos.append(name)
    outcome = ('TRIGGER' if triggered else
               ('UNDETERMINED' if open_combos else 'NO-TRIGGER'))
    return dict(arch=arch, outcome=outcome, seeds=[int(s) for s in seeds],
                denominator=len(seeds), drop=FORGET_DROP,
                replications_required=FORGET_REPLICATIONS,
                h_eligibility_mark=FORGET_H_ELIGIBLE, cells=list(FORGET_CELLS),
                metrics=list(FORGET_METRICS), awake_fit_gate=gate,
                combos=combos, triggered=triggered, undetermined=open_combos,
                note=('secondary readout (ruling 7).  It cannot alter the primary verdict, '
                      'select a recipe or checkpoint, or establish recent activity as a '
                      'cause.  Answer and strict counts are separate, each out of 64, and '
                      'are never added.  UNDETERMINED means missing evidence, not an '
                      'absence of forgetting.'))


def length_mix(exp, *, seeds=REGISTERED_SEEDS):
    """Ruling 8: the ACTUAL accepted length mix of G and U in each seed, from the buffers.

    The approximate 6.5% / 40% four-and-five-call figures are neither a quota nor an
    exact finite-buffer prediction, so what the buffers actually contain is reported.
    """
    out = {str(int(s)): None for s in seeds}
    for folder in buffer_folders(exp):
        manifest_path, audit_path = folder / 'manifest.json', folder / 'audit.json'
        manifest = json.loads(manifest_path.read_text())
        seed = int(manifest['seed'])
        if seed not in [int(s) for s in seeds]:
            continue
        row = dict(seed=int(seed), manifest=str(manifest_path),
                   manifest_sha256=sha(manifest_path), audit_sha256=sha(audit_path),
                   audit_sha256_matches=bool(sha(audit_path) == manifest['audit_sha256']),
                   files=dict(manifest['files']), arms={})
        audit = json.loads(audit_path.read_text())
        for arm in manifest['arms']:
            histogram = audit['per_arm'][arm]['length_histogram']
            total = sum(histogram.values())
            long_keys = {k: v for k, v in histogram.items()
                         if int(k.split(',')[0].split('=')[1]) in (4, 5)}
            row['arms'][arm] = dict(
                questions=total, length_histogram=dict(sorted(histogram.items())),
                four_or_five_calls=sum(long_keys.values()),
                four_or_five_share=(None if not total
                                    else round(sum(long_keys.values()) / total, 4)),
                fallbacks=audit['per_arm'][arm]['fallbacks'],
                accepted=audit['per_arm'][arm]['accepted'],
                buffer_sha256=audit['per_arm'][arm]['sha256'])
        out[str(int(seed))] = row
    return out


# =========================================================================== DEV-PASSED


PRIMARY_ARCH = 'D'            # section 6: the registered primary claim is D-G against D-R
PRIMARY_ARM = 'G'
E_CELLS = tuple(c for c in N.DEV_CELL_ORDER if c.startswith('E-'))


def development_rule(collected, generation, primary, *, seeds=REGISTERED_SEEDS,
                     version=None):
    """Section 6's registered DEVELOPMENT rule, as a single explicit verdict.

    A null anywhere is not a pass: the gate has to be shown to hold, seed by seed and
    cell by cell, on runs that are all present and all scored on one panel suite.
    """
    treatment = {s: collected['runs'].get(run_key(PRIMARY_ARCH, s, 'offline', PRIMARY_ARM))
                 for s in seeds}
    parts = {}

    gen = [generation.get(str(int(s)), {}).get('passed') for s in seeds]
    parts['generation_gate'] = dict(
        required='ruling 1: >= 16 distinct (world, question) instances over >= 16 worlds '
                 'for each of the four new structures, in every seed',
        per_seed={str(int(s)): g for s, g in zip(seeds, gen)},
        passed=None if any(g is None for g in gen) else bool(all(gen)))

    fit = [awake_fit_gate(collected['runs'].get(run_key(PRIMARY_ARCH, s, 'awake', None)))
           for s in seeds]
    parts['awake_fit_gate'] = dict(
        required=f'section 5: >= {AWAKE_FIT_MARK}/64 answers AND strict in all '
                 f'{len(FIT_CELLS)} F cells, every seed, architecture {PRIMARY_ARCH}',
        per_seed={str(int(s)): v['passed'] for s, v in zip(seeds, fit)},
        passed=None if any(v['passed'] is None for v in fit)
        else bool(all(v['passed'] for v in fit)))

    parts['primary'] = dict(
        required=f'section 6: every N cell in every seed, {PRIMARY_ARCH}-{PRIMARY_ARM} '
                 f'>= {PRIMARY_MARK}/64 answers AND strict and >= {PRIMARY_GAIN}/64 strict '
                 f'over {PRIMARY_ARCH}-R',
        passed=primary[f'{PRIMARY_ARCH}-{PRIMARY_ARM}']['passed'])

    def family_block(cells, need_answers, need_strict, label):
        rows, verdicts = {}, []
        for seed in seeds:
            for cell in cells:
                row = (treatment[seed] or {}).get('cells', {}).get(cell)
                ok = None if row is None else bool(row['answers'] >= need_answers
                                                   and row['strict'] >= need_strict)
                verdicts.append(ok)
                rows[f's{int(seed)}|{cell}'] = (
                    None if row is None else dict(answers=row['answers'],
                                                  strict=row['strict'], n=row['n'], passed=ok))
        return dict(required=label, cells=list(cells), rows=rows,
                    passed=None if any(v is None for v in verdicts) else bool(all(verdicts)))

    parts['guard_E'] = family_block(
        E_CELLS, 0, PRIMARY_MARK,
        f'section 6: required anti-shortcut guard, {PRIMARY_ARCH}-{PRIMARY_ARM} '
        f'>= {PRIMARY_MARK}/64 strict pair units in each E cell')
    parts['retention_F'] = family_block(
        FIT_CELLS, AWAKE_FIT_MARK, AWAKE_FIT_MARK,
        f'section 6: required retention, {PRIMARY_ARCH}-{PRIMARY_ARM} '
        f'>= {AWAKE_FIT_MARK}/64 answers AND strict in each F cell after offline practice')

    version = trainer_version(collected, seeds=seeds) if version is None else version
    complete = (not collected['missing'] and not collected['incomplete']
                and not collected['conflicts'] and not collected['rejected']
                and version['passed'] is True)
    parts['evidence_complete'] = dict(
        required='every registered run scored on every cell of one panel suite, at the '
                 'registered caps, from each run\'s final checkpoint, by ONE frozen script '
                 'version, with no conflicting and no rejected score files',
        missing_runs=collected['missing'], incomplete_runs=sorted(collected['incomplete']),
        rejected_runs=sorted(collected['rejected_runs']),
        trainer_versions=version['distinct'],
        runs_from_another_version=version['offending_runs'],
        runs_without_a_fingerprint=version['runs_without_a_fingerprint'],
        conflicts=len(collected['conflicts']), passed=bool(complete))

    verdicts = [v['passed'] for v in parts.values()]
    passed = None if any(v is None for v in verdicts) else bool(all(verdicts))
    return dict(architecture=PRIMARY_ARCH, arm=PRIMARY_ARM, parts=parts, passed=passed,
                note='development only.  A development success without untouched '
                     'confirmation is reported as development success, never as the '
                     'registered result.')


def dev_passed_payload(exp, collected, rule, report_path, *, seeds=REGISTERED_SEEDS):
    """The unlock record, in the EXACT shape `fable_novelty19_data` will verify.

    That module documents `novelty19-dev-passed-v1` and refuses anything else, so this
    writes those keys and nothing more; provenance goes into a `.meta.json` sidecar,
    following the convention the data artifacts already use.  A hash that is not 64
    lower-case hex characters, a missing run, or a panel manifest that no longer matches
    the bytes on disk means no file is written at all.

    Must-fix 1: the registered rule is a THREE-SEED rule.  `--seeds` exists so a partial
    experiment can be read while it is being built, and a report over any other seed set
    is a working view, not the registered verdict -- so it can never unlock confirmation,
    however well it scores.  The seed list, and the full 6 + 18 key sets the data module
    will demand, are checked here before a single byte is written.
    """
    given = tuple(int(s) for s in seeds)
    if given != tuple(int(s) for s in REGISTERED_SEEDS):
        return None, None, [f'the seed set is {list(given)}; the registered development rule '
                            f'is over exactly {list(map(int, REGISTERED_SEEDS))}, so this '
                            f'report cannot unlock confirmation']
    suites = sorted({e['panel_manifest_sha256'] for e in collected['runs'].values()})
    folders = sorted({e['panels'] for e in collected['runs'].values() if e.get('panels')})
    awake, offline, problems = {}, {}, []
    for arch in ARCHES:
        for seed in seeds:
            entry = collected['runs'].get(run_key(arch, seed, 'awake', None))
            awake[f'{arch}-{int(seed)}'] = (None if entry is None
                                            else entry['checkpoint_sha256'])
            for arm in ARMS:
                oentry = collected['runs'].get(run_key(arch, seed, 'offline', arm))
                offline[f'{arch}-{arm}-{int(seed)}'] = (None if oentry is None
                                                        else oentry['checkpoint_sha256'])
    for label, table in (('awake', awake), ('offline', offline)):
        for key, value in table.items():
            if value is None:
                problems.append(f'{label} checkpoint {key} is missing')
            elif not HEX64.match(str(value)):
                problems.append(f'{label} checkpoint {key} is not a sha256')
    if set(awake) != set(N.AWAKE_CHECKPOINT_KEYS):
        problems.append(f'the awake checkpoint keys are {sorted(awake)}, the data module '
                        f'requires exactly {list(N.AWAKE_CHECKPOINT_KEYS)}')
    if set(offline) != set(N.OFFLINE_CHECKPOINT_KEYS):
        problems.append(f'the offline checkpoint keys do not match the data module\'s '
                        f'{len(N.OFFLINE_CHECKPOINT_KEYS)} registered keys')
    if len(suites) != 1:
        problems.append(f'{len(suites)} different panel manifests among the score files')
    if len(folders) != 1:
        problems.append(f'{len(folders)} different panel folders among the score files')
    else:
        manifest = Path(folders[0]) / 'manifest.json'
        if not manifest.is_file():
            problems.append(f'the panel manifest {manifest} is not on disk')
        elif sha(manifest) != suites[0]:
            problems.append(f'{manifest} no longer hashes to the value the runs were '
                            f'scored against')
    payload = dict(
        schema=N.DEV_PASSED_SCHEMA, seeds=[int(s) for s in seeds],
        report_sha256=sha(Path(report_path)),
        dev_panels=dict(path=folders[0] if len(folders) == 1 else None,
                        manifest_sha256=suites[0] if len(suites) == 1 else None),
        awake_checkpoints=awake, offline_checkpoints=offline)
    sidecar = dict(
        kind='novelty19-dev-passed-meta', experiment=str(Path(exp).resolve()),
        report=str(Path(report_path).resolve()), development=rule,
        awake_keys_expected=list(N.AWAKE_CHECKPOINT_KEYS),
        offline_keys_expected=list(N.OFFLINE_CHECKPOINT_KEYS),
        registered_seeds=list(REGISTERED_SEEDS),
        note=('written only because the registered development rule passed.  Confirmation '
              'panels are generated and scored once, without any recipe change; if the '
              'outcome motivates a change these panels become development and a new '
              'namespace is required.'),
        source_fingerprint=source_fingerprint(), host=host_profile(),
        argv=list(sys.argv), created_unix=time.time())
    return payload, sidecar, problems

if __name__ == '__main__':
    raise SystemExit(main())
