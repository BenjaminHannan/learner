"""Talker 24 -- the resume-safe trainer (design section 2.3, 2.6 and stage plan 5).

STAGES (section 5)

  autoencode  "say it back": ears -> 416-number thought -> mouth, cross-entropy on the
              sentence, with the 12 -> 24 -> 48 length curriculum, gist noise and gist
              dropout.  This is S1's first and longest job.
  slots       slot fine-tuning on the generated dialogue turns: act, relation path, the
              two pointers and the flags get their own supervised losses, and 30 % of
              fact sentences are decoded from ANOTHER sentence's gist so the mouth learns
              that the slots decide the content and the gist only decides the wording.
  thinker     the mouth is FROZEN; the 4-block thinker predicts the reply thought and is
              trained by cross-entropy THROUGH that frozen mouth (D5, SONAR-LLM's recipe).
  yardstick   the plain ~29M chat LM of D6, on the same tokens.  The comparison arm, not
              part of the talker.

SURVIVING INTERRUPTIONS (section 2.6, exception D8)

  * the data order is a pure function of (seed, position) -- SentenceStream
  * atomic checkpoints every 10 minutes AND every 2,000 steps: model, optimiser, schedule
    step, tokens seen, stream position, every random-number state.  Written to a temp file
    and renamed, so a crash mid-write cannot leave a half checkpoint.
  * ``restart-loop`` restarts the process from the newest checkpoint if it dies
  * ``kill-test`` proves it: run N steps; run again with a real SIGKILL partway; resume;
    the parameter hashes must be equal.  Result is printed, not asserted away.

RUNS ON Windows + CUDA (bf16 autocast, EAGER -- no torch.compile, which still has no
NVIDIA-on-Windows support, section 2.3) and on Mac CPU (fp32).  torch + numpy only.

CLI
  train        one stage
  restart-loop the same, restarted from the newest checkpoint until it finishes
  kill-test    uninterrupted vs killed-and-resumed, parameter hashes compared
  bench        tokens/s, peak memory and implied FLOPs/s for one or more presets
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, asdict, replace
import hashlib
import json
import math
import os
from pathlib import Path
import random
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import fable_talker24_model as M                                       # noqa: E402
import fable_talker24_loader as L                                      # noqa: E402

torch = M.torch
nn, F = M.nn, M.F
np = L.np

STAGES = ('autoencode', 'slots', 'thinker', 'yardstick')


# ============================================================================== config

@dataclass
class TrainConfig:
    stage: str = 'autoencode'
    preset: str = 'M'
    gru_mouth: bool = False
    steps: int = 1000
    seed: int = 24
    # section 2.3
    lr: float = 6e-4
    betas: tuple = (0.9, 0.95)
    weight_decay: float = 0.1
    warmup: int = 300
    decay_fraction: float = 0.15       # warm-up -- stable -- decay, last 15 %
    final_lr_fraction: float = 0.10
    grad_clip: float = 1.0
    batch_tokens: int = 131072
    micro_batch: int = 64
    gist_noise: float = 0.2
    gist_dropout: float = 0.1
    gist_swap_rate: float = 0.30
    curriculum: tuple = ((0.20, 12), (0.50, 24), (1.01, 48))
    # section 2.6
    checkpoint_minutes: float = 10.0
    checkpoint_steps: int = 2000
    keep_last: int = 3
    log_every: int = 25
    max_minutes: float = 0.0           # 0 = no limit; the D8 exception caps a run at 6 h
    device: str = 'auto'
    shards: str = ''
    dialogues: str = ''                # artifacts folder holding dialogues/ (build task 2)
    dialogue_split: str = 'train'      # a file under dialogues/, or 'train' = generate
    generate_split: str = 'L1'         # which wording level to generate (L1 | L2)
    dialogue_start: int = L.TRAIN_INDEX_START   # past the sealed 0..999 evaluation block
    symbol_mode: str = 'm0'            # m0 | pool  (INTERFACE-dialogues.md section 7)
    code_pool: str = 'train'           # train | reserved, pool mode only
    allow_sealed: bool = False         # train on L1/L2 test sets (never, in a real run)
    synthetic_sentences: int = 4096
    synthetic_dialogues: int = 512
    out: str = ''

    def resolve_device(self):
        if self.device != 'auto':
            return self.device
        return 'cuda' if torch.cuda.is_available() else 'cpu'


def stage_max_len(cfg, step):
    """Length curriculum: <= 12 for the first 20 % of steps, <= 24 to 50 %, <= 48 after."""
    fraction = (step + 1)/max(cfg.steps, 1)
    for bound, length in cfg.curriculum:
        if fraction <= bound:
            return length
    return cfg.curriculum[-1][1]


def learning_rate(cfg, step):
    """Warm-up -- stable -- decay (section 2.3): flat, so a run can be cut short or
    extended after an interruption without re-planning the schedule."""
    if step < cfg.warmup:
        return cfg.lr*(step + 1)/max(cfg.warmup, 1)
    decay_start = cfg.steps*(1.0 - cfg.decay_fraction)
    if step < decay_start:
        return cfg.lr
    span = max(cfg.steps - decay_start, 1)
    t = min((step - decay_start)/span, 1.0)
    return cfg.lr*(1.0 - t*(1.0 - cfg.final_lr_fraction))


# ============================================================== reproducible RNG state

def rng_state():
    return dict(python=random.getstate(),
                numpy=np.random.get_state(legacy=True),
                torch=torch.get_rng_state().tolist(),
                cuda=[s.tolist() for s in torch.cuda.get_rng_state_all()]
                if torch.cuda.is_available() else [])


def load_rng_state(state):
    random.setstate(tuple(tuple(x) if isinstance(x, list) else x for x in state['python']))
    np_state = state['numpy']
    np.random.set_state((np_state[0], np.asarray(np_state[1], dtype=np.uint32),
                         int(np_state[2]), int(np_state[3]), float(np_state[4])))
    torch.set_rng_state(torch.tensor(state['torch'], dtype=torch.uint8))
    if torch.cuda.is_available() and state.get('cuda'):
        torch.cuda.set_rng_state_all([torch.tensor(s, dtype=torch.uint8)
                                      for s in state['cuda']])


def parameter_hash(module):
    """sha256 over every parameter and buffer, in name order.  The kill test's verdict."""
    h = hashlib.sha256()
    for name, tensor in sorted(module.state_dict().items()):
        h.update(name.encode())
        h.update(tensor.detach().to('cpu').contiguous().float().numpy().tobytes())
    return h.hexdigest()


# ==================================================================== checkpoint store

def atomic_save(payload, path):
    """Temp file, fsync, rename.  A crash mid-write cannot leave a half checkpoint."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    with open(tmp, 'wb') as handle:
        torch.save(payload, handle)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)
    return path


def newest_checkpoint(out):
    out = Path(out)
    files = sorted(out.glob('step-*.pt'),
                   key=lambda p: int(p.stem.split('-')[1]))
    return files[-1] if files else None


def prune_checkpoints(out, keep):
    files = sorted(Path(out).glob('step-*.pt'),
                   key=lambda p: int(p.stem.split('-')[1]))
    for path in files[:-keep] if keep > 0 else []:
        path.unlink(missing_ok=True)


# ====================================================================== the data supply

def build_streams(cfg, model_cfg):
    """Shards if they exist, synthetic if they do not.  Always says which."""
    shards, source = [], f'synthetic ({cfg.synthetic_sentences} sentences, NOT real text)'
    if cfg.shards:
        stems = L.list_shards(cfg.shards, 's0') or L.list_shards(cfg.shards, 'train')
        if stems:
            shards = [L.load_shard(s) for s in stems]
            source = f'{len(shards)} shard(s) under {cfg.shards}'
            # A real shard speaks the 8,192-piece vocabulary; the "tiny" test preset does
            # not.  Say so loudly and fall back rather than dying on an embedding index.
            widest = max(int(np.asarray(s.tokens).max()) for s in shards)
            if widest >= model_cfg.vocab_size:
                source = (f'synthetic -- the shards under {cfg.shards} use token ids up '
                          f'to {widest} but preset "{cfg.preset}" has a '
                          f'{model_cfg.vocab_size}-piece vocabulary')
                print(f'[data] {source}', flush=True)
                shards = []
    if not shards:
        shards = [L.synthetic_shard(cfg.synthetic_sentences, seed=cfg.seed,
                                    vocab_size=model_cfg.vocab_size,
                                    max_len=min(model_cfg.max_len, 16))]
    stream = L.SentenceStream(shards, seed=cfg.seed, max_len=model_cfg.max_len)
    valid = L.SentenceStream(shards, seed=cfg.seed + 1, max_len=model_cfg.max_len)
    return stream, valid, source


def build_dialogues(cfg, model_cfg):
    """Real dialogue records if build task 2 has shipped any, synthetic otherwise.

    ``--dialogues`` is the artifacts folder that holds ``dialogues/`` (and usually
    ``shards/`` beside it, which is where the tokenizer export the reader needs lives).
    The set always carries its own source string, which goes into result.json, so no
    report can accidentally claim synthetic numbers were real ones.

    THREE WAYS TO GET TURNS, in order:

    1. ``--dialogue-split`` names a file under ``dialogues/`` -- read it.  This is how the
       SEALED evaluation sets (``L1``, ``L2``) are used; training on them is refused
       unless ``--allow-sealed`` is given, because they are the test set.
    2. ``--dialogue-split train`` (the default) -- STREAM FROM THE GENERATOR.
       INTERFACE-dialogues.md section 1 ships no training file on purpose: a record is
       ~18 kB, so a million of them would be ~18 GB.  The generator makes one in well
       under a millisecond, from ``(namespace, split, index)`` alone, so a resumed run
       re-draws exactly the same records.  Indices start past the sealed block.
    3. nothing worked -- synthetic stand-ins, and the source string says so in capitals.
    """
    dialogues = None
    if cfg.dialogues:
        path = L.find_dialogue_file(cfg.dialogues, cfg.dialogue_split)
        if path is not None:
            if not cfg.allow_sealed and cfg.dialogue_split in ('L1', 'L2'):
                print(f'[data] {path.name} is a SEALED evaluation set; refusing to train '
                      f'on it (pass --allow-sealed to override). Generating instead.',
                      flush=True)
            else:
                dialogues = L.load_dialogues(cfg.dialogues, cfg.dialogue_split,
                                             shards_dir=cfg.shards or None)
        if dialogues is None:
            made, why = L.generate_dialogues(
                cfg.dialogues, split=cfg.generate_split, n=cfg.synthetic_dialogues,
                start=cfg.dialogue_start, symbol_mode=cfg.symbol_mode,
                pool=cfg.code_pool, shards_dir=cfg.shards or None)
            if made is None:
                print(f'[data] cannot generate dialogues: {why}', flush=True)
            dialogues = made
        if dialogues is not None and not len(dialogues):
            print(f'[data] {dialogues.source}: no usable turns '
                  f'({dialogues.filled}); falling back to synthetic', flush=True)
            dialogues = None
    if dialogues is None:
        dialogues = L.synthetic_dialogues(cfg.synthetic_dialogues, seed=cfg.seed,
                                          vocab_size=model_cfg.vocab_size,
                                          max_len=min(model_cfg.max_len, 16))
    return dialogues


# ========================================================================== the losses

def token_loss(logits, targets, ignore=M.PAD):
    return F.cross_entropy(logits.reshape(-1, logits.shape[-1]), targets.reshape(-1),
                           ignore_index=ignore)


def gold_pointer_index(code_ids, wanted, null_index):
    """Where in the sentence the gold code sits.  ``null_index`` when it is not there."""
    match = (code_ids == wanted[:, None]) & (wanted[:, None] != L.ENT_NONE)
    has = match.any(-1)
    first = match.float().argmax(-1)
    return torch.where(has, first, torch.full_like(first, null_index))


def slot_losses(heard, labels, code_ids):
    """Act, relation path, flags and both pointers, each supervised by construction."""
    null = heard['subject_pointer'].shape[-1] - 1
    out = {}
    out['act'] = F.cross_entropy(heard['act_logits'], labels['act'])
    out['path'] = F.cross_entropy(
        heard['path_logits'].reshape(-1, M.RELATION_CHOICES),
        labels['relation_path'].reshape(-1))
    out['flags'] = F.binary_cross_entropy_with_logits(heard['flag_logits'],
                                                      labels['flags'])
    for name, key in (('subject', 'subject_code'), ('object', 'object_code')):
        gold = gold_pointer_index(code_ids, labels[key], null)
        out[f'{name}_pointer'] = F.nll_loss(
            torch.log(heard[f'{name}_pointer'].clamp_min(1e-9)), gold)
    return out


# ============================================================================ training

class Trainer:
    def __init__(self, cfg):
        self.cfg = cfg
        self.device = torch.device(cfg.resolve_device())
        self.out = Path(cfg.out)
        self.out.mkdir(parents=True, exist_ok=True)
        torch.manual_seed(cfg.seed)
        random.seed(cfg.seed)
        np.random.seed(cfg.seed % (2**32))
        self.model_cfg = M.config(cfg.preset)
        if cfg.stage == 'yardstick':
            self.model = M.ChatLM(self.model_cfg).to(self.device)
        else:
            self.model = M.Talker(self.model_cfg, gru_mouth=cfg.gru_mouth).to(self.device)
        self.stream, self.valid, self.source = build_streams(cfg, self.model_cfg)
        self.dialogues = (build_dialogues(cfg, self.model_cfg)
                          if cfg.stage in ('slots', 'thinker') else None)
        if self.dialogues is not None:
            # The report must never be able to mistake stand-in data for real data.
            self.source = f'{self.source} + dialogues: {self.dialogues.source}'
        self.noise = torch.Generator(device='cpu').manual_seed(cfg.seed + 7)
        self.optimizer = self._optimizer()
        self.step = 0
        self.tokens = 0
        self.history = []
        self.last_checkpoint = time.time()
        self.forward_parameters = self._forward_parameters()
        self._freeze_for_stage()

    # ---------------------------------------------------------------- setup helpers
    def _optimizer(self):
        decay, plain = [], []
        for name, p in self.model.named_parameters():
            if not p.requires_grad:
                continue
            (decay if p.ndim >= 2 else plain).append(p)
        groups = [dict(params=decay, weight_decay=self.cfg.weight_decay),
                  dict(params=plain, weight_decay=0.0)]
        return torch.optim.AdamW(groups, lr=self.cfg.lr, betas=tuple(self.cfg.betas))

    def _freeze_for_stage(self):
        if self.cfg.stage == 'thinker':
            for p in self.model.mouth.parameters():
                p.requires_grad_(False)
            for p in self.model.ears.parameters():
                p.requires_grad_(False)
            self.model.mouth.eval()
            self.optimizer = self._optimizer()

    def _forward_parameters(self):
        if self.cfg.stage == 'yardstick':
            return sum(p.numel() for p in self.model.parameters())
        parts = M.forward_parameters(self.model)
        return parts['thinker'] if self.cfg.stage == 'thinker' else parts['autoencoder']

    # ------------------------------------------------------------------- one step
    def batch_sentences(self, stream, max_len, n):
        pairs = stream.take(n)
        return L.pad_batch(pairs, max_len, device=self.device)

    def autocast(self):
        if self.device.type == 'cuda':
            return torch.autocast('cuda', dtype=torch.bfloat16)
        return torch.autocast('cpu', enabled=False)

    def loss_autoencode(self, max_len):
        tokens, codes = self.batch_sentences(self.stream, max_len, self.cfg.micro_batch)
        out = self.model.autoencode(tokens, codes, gist_noise=self.cfg.gist_noise,
                                    gist_dropout=self.cfg.gist_dropout,
                                    generator=self.noise)
        loss = token_loss(out['logits'], out['targets'])
        return loss, dict(loss=float(loss.detach())), int((tokens != M.PAD).sum())

    def loss_slots(self, max_len):
        turns = self._sample_turns(self.cfg.micro_batch)
        tokens, codes, labels = L.dialogue_batch(turns, device=self.device)
        heard = self.model.ears(tokens, codes)
        parts = slot_losses(heard, labels, codes)
        thought = heard['thought']
        # gist-swap augmentation on fact turns: the slots decide the content, the gist
        # only decides the wording (section 3.4 "by training").
        fact = labels['act'] != M.CHAT_ACT
        pick = torch.rand(len(turns), generator=self.noise) < self.cfg.gist_swap_rate
        swap = (fact.cpu() & pick).to(self.device)
        if bool(swap.any()):
            rolled = torch.roll(M.field_of(thought, 'gist'), 1, dims=0)
            gist = torch.where(swap[:, None], rolled, M.field_of(thought, 'gist'))
            thought = torch.cat((thought[..., :M.SLICES['gist'].start],
                                 gist*M.gist_gate(M.field_of(thought, 'act'))), dim=-1)
        thought = M.perturb_gist(thought, self.cfg.gist_noise, self.cfg.gist_dropout,
                                 self.noise)
        parts['say'] = token_loss(self.model.mouth(thought, tokens[:, :-1]),
                                  tokens[:, 1:])
        loss = sum(parts.values())
        return loss, {k: float(v.detach()) for k, v in parts.items()}, int((tokens != M.PAD).sum())

    def loss_thinker(self, max_len):
        turns = self._sample_turns(self.cfg.micro_batch)
        tokens, codes, _ = L.dialogue_batch(turns, device=self.device)
        reply, _, reply_labels = L.dialogue_batch(turns, device=self.device, reply=True)
        with torch.no_grad():
            heard = self.model.ears(tokens, codes)
        thoughts = heard['thought'][:, None]
        predicted = self.model.thinker(thoughts)
        # the mouth is frozen: gradient flows through it into the predicted thought only
        logits = self.model.mouth(predicted['thought'], reply[:, :-1])
        parts = dict(through_mouth=token_loss(logits, reply[:, 1:]))
        parts['act'] = 0.1*F.cross_entropy(predicted['act_logits'], reply_labels['act'])
        loss = sum(parts.values())
        return loss, {k: float(v.detach()) for k, v in parts.items()}, int((reply != M.PAD).sum())

    def loss_yardstick(self, max_len):
        pairs = self.stream.take(self.cfg.micro_batch)
        flat = []
        for tokens, _ in pairs:
            flat.extend([M.BOS] + [int(t) for t in tokens] + [M.EOS])
        width = min(self.model_cfg.lm_context, max(16, len(flat)//8))
        rows = [flat[i:i + width] for i in range(0, len(flat) - width, width)] or [flat[:width]]
        x = torch.tensor([r + [M.PAD]*(width - len(r)) for r in rows],
                         dtype=torch.long, device=self.device)
        logits = self.model(x[:, :-1])
        loss = token_loss(logits, x[:, 1:])
        return loss, dict(loss=float(loss.detach())), int((x != M.PAD).sum())

    def _sample_turns(self, n):
        turns = self.dialogues.turns
        start = (self.step*n) % max(len(turns), 1)
        picked = [turns[(start + i) % len(turns)] for i in range(n)]
        return picked

    def one_step(self):
        cfg = self.cfg
        max_len = stage_max_len(cfg, self.step)
        if cfg.stage in ('autoencode', 'yardstick'):
            self.stream.set_max_len(max_len)
        lr = learning_rate(cfg, self.step)
        for group in self.optimizer.param_groups:
            group['lr'] = lr
        self.optimizer.zero_grad(set_to_none=True)
        with self.autocast():
            loss, parts, tokens = getattr(self, f'loss_{cfg.stage}')(max_len)
        loss.backward()
        grad_norm = torch.nn.utils.clip_grad_norm_(
            [p for p in self.model.parameters() if p.requires_grad], cfg.grad_clip)
        self.optimizer.step()
        self.step += 1
        self.tokens += tokens
        parts['lr'] = lr
        parts['grad_norm'] = float(grad_norm)
        parts['max_len'] = max_len
        return parts, tokens

    # ------------------------------------------------------------------ checkpoints
    def checkpoint_payload(self):
        return dict(format='fable-talker24-train/1',
                    train_config=asdict(self.cfg),
                    model_config=asdict(self.model_cfg),
                    step=self.step, tokens=self.tokens,
                    model=self.model.state_dict(),
                    optimizer=self.optimizer.state_dict(),
                    stream=self.stream.state(),
                    valid_stream=self.valid.state(),
                    noise_generator=self.noise.get_state().tolist(),
                    rng=rng_state(),
                    parameter_hash=parameter_hash(self.model),
                    history=self.history[-50:])

    def save(self, tag=None):
        name = tag or f'step-{self.step:08d}'
        path = atomic_save(self.checkpoint_payload(), self.out/f'{name}.pt')
        if tag is None:
            prune_checkpoints(self.out, self.cfg.keep_last)
        self.last_checkpoint = time.time()
        return path

    def restore(self, path):
        payload = torch.load(path, map_location=self.device, weights_only=False)
        self.model.load_state_dict(payload['model'])
        self.optimizer.load_state_dict(payload['optimizer'])
        self.step, self.tokens = payload['step'], payload['tokens']
        self.stream.load_state(payload['stream'])
        self.valid.load_state(payload['valid_stream'])
        self.noise.set_state(torch.tensor(payload['noise_generator'], dtype=torch.uint8))
        load_rng_state(payload['rng'])
        self.history = list(payload.get('history', []))
        self._freeze_for_stage()
        self.optimizer.load_state_dict(payload['optimizer'])
        return payload

    def maybe_resume(self):
        path = newest_checkpoint(self.out)
        if path is None:
            return None
        payload = self.restore(path)
        print(f'[resume] {path.name}: step {self.step}, {self.tokens:,} tokens, '
              f'hash {payload["parameter_hash"][:16]}', flush=True)
        return path

    # ------------------------------------------------------------------------ loop
    def run(self, die_at=None):
        cfg = self.cfg
        started = time.time()
        window_tokens, window_start = 0, time.time()
        log_path = self.out/'heartbeat.jsonl'
        print(f'[start] stage={cfg.stage} preset={cfg.preset} device={self.device} '
              f'steps={cfg.steps} from step {self.step}; data = {self.source}', flush=True)
        while self.step < cfg.steps:
            parts, tokens = self.one_step()
            window_tokens += tokens
            now = time.time()
            if self.step % cfg.log_every == 0 or self.step == cfg.steps:
                elapsed = max(now - window_start, 1e-9)
                rate = window_tokens/elapsed
                flops = 6.0*self.forward_parameters*rate
                line = dict(step=self.step, tokens=self.tokens, tokens_per_s=round(rate, 1),
                            tflops=round(flops/1e12, 3), elapsed_s=round(now - started, 2),
                            peak_mem_mb=peak_memory_mb(self.device), **parts)
                self.history.append(line)
                with log_path.open('a') as handle:
                    handle.write(json.dumps(line) + '\n')
                loss_text = ' '.join(f'{k}={v:.4f}' for k, v in parts.items()
                                     if isinstance(v, float) and k not in ('lr',))
                print(f'[step {self.step:>7}/{cfg.steps}] {loss_text} '
                      f'lr={parts["lr"]:.2e} {rate:,.0f} tok/s '
                      f'{flops/1e12:.2f} TFLOP/s', flush=True)
                window_tokens, window_start = 0, now
            due = (self.step % cfg.checkpoint_steps == 0
                   or now - self.last_checkpoint >= cfg.checkpoint_minutes*60)
            if due:
                self.save()
            if die_at is not None and self.step >= die_at:
                # NO save here on purpose: a real crash does not get to checkpoint.  The
                # resume must come from the last periodic checkpoint and replay from there.
                print(f'[kill] SIGKILL at step {self.step} (requested, nothing saved)',
                      flush=True)
                sys.stdout.flush()
                if hasattr(signal, 'SIGKILL'):
                    os.kill(os.getpid(), signal.SIGKILL)
                os._exit(137)
            if cfg.max_minutes and (now - started) >= cfg.max_minutes*60:
                path = self.save(tag='final')
                print(f'[stop] time limit {cfg.max_minutes} min reached at step '
                      f'{self.step}', flush=True)
                result = dict(finished=False, stopped='time-limit', step=self.step,
                              tokens=self.tokens, checkpoint=str(path),
                              parameter_hash=parameter_hash(self.model),
                              seconds=round(time.time() - started, 2), source=self.source,
                              **self.data_note())
                (self.out/'result.json').write_text(json.dumps(result, indent=2))
                print('[done] ' + json.dumps(result), flush=True)
                return result
        path = self.save(tag='final')
        result = dict(finished=True, step=self.step, tokens=self.tokens,
                      parameter_hash=parameter_hash(self.model), checkpoint=str(path),
                      seconds=round(time.time() - started, 2), source=self.source,
                      **self.data_note())
        (self.out/'result.json').write_text(json.dumps(result, indent=2))
        print('[done] ' + json.dumps(result), flush=True)
        return result

    def data_note(self):
        """What the turns actually were -- copied into every result.json (section 2.6)."""
        if self.dialogues is None:
            return dict(dialogues=None)
        return dict(dialogues=dict(source=self.dialogues.source,
                                   turns=len(self.dialogues),
                                   parse_counters={str(k): int(v) for k, v
                                                   in (self.dialogues.filled or {}).items()},
                                   synthetic='synthetic' in self.dialogues.source.lower()))


def peak_memory_mb(device):
    if device.type == 'cuda':
        return round(torch.cuda.max_memory_allocated()/2**20, 1)
    return None


# ============================================================================ benchmark

def benchmark(preset, steps=20, device=None, batch=32, length=48, gru_mouth=False,
              stage='autoencode'):
    """Tokens/s, peak memory and implied FLOPs/s -- so real hours can be quoted from a
    measurement instead of the 15-TFLOPS planning guess of section 2.4."""
    device = torch.device(device or ('cuda' if torch.cuda.is_available() else 'cpu'))
    cfg = M.config(preset)
    model = M.Talker(cfg, gru_mouth=gru_mouth).to(device)
    forward_parameters = M.forward_parameters(model)['autoencoder']
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
    tokens = torch.randint(16, cfg.vocab_size, (batch, length), device=device)
    codes = torch.full((batch, length), L.ENT_NONE, device=device, dtype=torch.long)
    if device.type == 'cuda':
        torch.cuda.reset_peak_memory_stats()

    def one():
        optimizer.zero_grad(set_to_none=True)
        ctx = torch.autocast('cuda', dtype=torch.bfloat16) if device.type == 'cuda' \
            else torch.autocast('cpu', enabled=False)
        with ctx:
            out = model.autoencode(tokens, codes)
            loss = token_loss(out['logits'], out['targets'])
        loss.backward()
        optimizer.step()

    for _ in range(3):
        one()
    if device.type == 'cuda':
        torch.cuda.synchronize()
    start = time.time()
    for _ in range(steps):
        one()
    if device.type == 'cuda':
        torch.cuda.synchronize()
    elapsed = time.time() - start
    seen = steps*batch*length
    rate = seen/elapsed
    return dict(preset=preset, device=str(device), gru_mouth=gru_mouth,
                parameters=sum(p.numel() for p in model.parameters()),
                forward_parameters=forward_parameters,
                batch=batch, length=length, steps=steps,
                seconds=round(elapsed, 3), tokens_per_s=round(rate, 1),
                tflops=round(6.0*forward_parameters*rate/1e12, 3),
                peak_mem_mb=peak_memory_mb(device),
                note='6 x forward-parameters x tokens/s (design section 2.4); '
                     'attention extra at <= 48 pieces is under 1 % and is ignored')


# =========================================================================== evaluation

S0_MARKS = {'token_accuracy': 0.90, 'exact': 0.50, 'thought_exact': 0.95,
            'slot_swap': 0.95, 'throughput_tokens_per_s': 60000}


def load_model(checkpoint, device='cpu'):
    payload = torch.load(checkpoint, map_location=device, weights_only=False)
    cfg = M.TalkerConfig(**payload['model_config'])
    model = M.Talker(cfg, gru_mouth=payload['train_config'].get('gru_mouth', False))
    model.load_state_dict(payload['model'])
    return model.to(device).eval(), cfg, payload


def evaluate(checkpoint, n=256, device='cpu', max_len=16, seed=101, dialogues='',
             shards=''):
    """The S0 marks that are about the MODEL (design section 5, S0 table).

    Held-out here means "sentences this run never trained on": a different stream seed
    over the same corpus, or -- when there is no corpus yet -- freshly drawn synthetic
    sentences.  The report says which, because on synthetic data these numbers measure the
    plumbing and nothing else.
    """
    import fable_talker24_interventions as IV
    model, cfg, payload = load_model(checkpoint, device)
    train_cfg = payload['train_config']
    source = 'synthetic held-out (NOT real text)'
    stems = L.list_shards(shards, 'valid') if shards else []
    if stems:
        shard_list, source = [L.load_shard(s) for s in stems], f'valid shards {shards}'
    else:
        shard_list = [L.synthetic_shard(n*2, seed=seed, vocab_size=cfg.vocab_size,
                                        max_len=max_len)]
    stream = L.SentenceStream(shard_list, seed=seed, max_len=max_len)
    tokens, codes = L.pad_batch(stream.take(n), max_len + 2, device=device)
    recon = IV.exact_reconstruction(model, tokens, codes)

    turn_set = None
    if dialogues:
        turn_set = L.load_dialogues(dialogues, 'L1', limit=n, shards_dir=shards or None)
    if turn_set is None or not len(turn_set):
        turn_set = L.synthetic_dialogues(n, seed=seed + 1, vocab_size=cfg.vocab_size,
                                         max_len=min(cfg.max_len, 12))
    turns = turn_set.turns[:n]
    dtok, dcod, labels = L.dialogue_batch(turns, device=device)
    with torch.no_grad():
        heard = model.hear(dtok, dcod)
    null = heard['subject_pointer'].shape[-1] - 1
    act_ok = heard['act_logits'].argmax(-1) == labels['act']
    path_ok = (heard['path_logits'].argmax(-1) == labels['relation_path']).all(-1)
    subj_ok = heard['subject_index'] == gold_pointer_index(dcod, labels['subject_code'],
                                                           null)
    obj_ok = heard['object_index'] == gold_pointer_index(dcod, labels['object_code'], null)
    whole = (act_ok & path_ok & subj_ok & obj_ok).float().mean().item()
    thought = dict(act=act_ok.float().mean().item(),
                   relation_path=path_ok.float().mean().item(),
                   subject=subj_ok.float().mean().item(),
                   object=obj_ok.float().mean().item(), whole_thought_exact=whole,
                   n=len(turns), source=turn_set.source)

    # Device fix (S0 on BensPC): ``thoughts_from_turns`` defaults to device=None (CPU
    # tensors) while the model here lives on ``device``.
    thoughts, ttok, tcod, _ = IV.thoughts_from_turns(model, turns[:min(64, len(turns))],
                                                     device=device)
    swaps = IV.run_interventions(model, thoughts, ttok, tcod, stage='S0',
                                 label=str(checkpoint))
    marks = dict(token_accuracy=recon['token_accuracy'] >= S0_MARKS['token_accuracy'],
                 exact=recon['exact'] >= S0_MARKS['exact'],
                 thought_exact=whole >= S0_MARKS['thought_exact'],
                 slot_swap=bool(swaps.get('slot_swap', {}).get('pass')))
    return dict(checkpoint=str(checkpoint), stage=train_cfg.get('stage'),
                preset=train_cfg.get('preset'), held_out=source,
                reconstruction=recon, thought=thought, interventions=swaps,
                marks=marks, thresholds=S0_MARKS,
                all_marks_met=all(marks.values()),
                honest_note='On synthetic stand-in data these marks measure the pipeline, '
                            'not the idea. Only a run over real shards and real dialogue '
                            'records may be quoted as an S0 result.')


# ============================================================================ kill test

def kill_test(out_root, steps=40, die_at=18, preset='tiny', stage='autoencode',
              seed=5, micro_batch=8, python=None):
    """A real SIGKILL, a real resume, two parameter hashes.

    Run A: ``steps`` steps, never interrupted.
    Run B: the same, killed hard at ``die_at`` with NOTHING saved at that moment (a real
    crash does not get to checkpoint), then restarted; the restart picks up the newest
    periodic checkpoint -- an earlier step -- and replays forward to ``steps``.
    The verdict is whether the two hashes are equal, printed either way.
    """
    python = python or sys.executable
    out_root = Path(out_root)
    common = ['--preset', preset, '--stage', stage, '--steps', str(steps),
              '--seed', str(seed), '--micro-batch', str(micro_batch),
              '--checkpoint-steps', '5', '--log-every', str(max(steps//4, 1)),
              '--device', 'cpu']
    clean = out_root/'uninterrupted'
    killed = out_root/'killed'
    for path in (clean, killed):
        if path.exists():
            for f in path.glob('*'):
                f.unlink()
    env = dict(os.environ, OMP_NUM_THREADS='1', VECLIB_MAXIMUM_THREADS='1',
               PYTHONHASHSEED='0')
    script = str(Path(__file__).resolve())
    a = subprocess.run([python, '-B', script, 'train', '--out', str(clean)] + common,
                       capture_output=True, text=True, env=env)
    if a.returncode != 0:
        return dict(ok=False, stage='run-a', stdout=a.stdout[-4000:], stderr=a.stderr[-4000:])
    b1 = subprocess.run([python, '-B', script, 'train', '--out', str(killed),
                         '--die-at', str(die_at)] + common,
                        capture_output=True, text=True, env=env)
    b2 = subprocess.run([python, '-B', script, 'train', '--out', str(killed)] + common,
                        capture_output=True, text=True, env=env)
    if b2.returncode != 0:
        return dict(ok=False, stage='run-b-resume', stdout=b2.stdout[-4000:],
                    stderr=b2.stderr[-4000:])
    ha = json.loads((clean/'result.json').read_text())
    hb = json.loads((killed/'result.json').read_text())
    result = dict(ok=ha['parameter_hash'] == hb['parameter_hash'],
                  steps=steps, die_at=die_at, preset=preset, stage=stage,
                  killed_signal=b1.returncode,
                  uninterrupted_hash=ha['parameter_hash'],
                  resumed_hash=hb['parameter_hash'],
                  uninterrupted_tokens=ha['tokens'], resumed_tokens=hb['tokens'],
                  resume_line=[l for l in b2.stdout.splitlines()
                               if l.startswith('[resume]')][:1])
    return result


# ========================================================================= restart loop

def restart_loop(argv, max_restarts=20, python=None):
    """The ``.bat`` loop of section 2.6, as Python so it works on both machines."""
    python = python or sys.executable
    script = str(Path(__file__).resolve())
    for attempt in range(max_restarts + 1):
        proc = subprocess.run([python, '-B', script, 'train'] + argv)
        if proc.returncode == 0:
            return 0
        print(f'[restart-loop] exit {proc.returncode}; restart {attempt + 1}/'
              f'{max_restarts} from the newest checkpoint', flush=True)
    print('[restart-loop] giving up', flush=True)
    return 1


# ================================================================================ CLI

def add_train_args(parser):
    parser.add_argument('--stage', default='autoencode', choices=STAGES)
    parser.add_argument('--preset', default='M')
    parser.add_argument('--gru-mouth', action='store_true')
    parser.add_argument('--steps', type=int, default=1000)
    parser.add_argument('--seed', type=int, default=24)
    parser.add_argument('--lr', type=float, default=6e-4)
    parser.add_argument('--warmup', type=int, default=300)
    parser.add_argument('--micro-batch', type=int, default=64)
    parser.add_argument('--batch-tokens', type=int, default=131072)
    parser.add_argument('--checkpoint-minutes', type=float, default=10.0)
    parser.add_argument('--checkpoint-steps', type=int, default=2000)
    parser.add_argument('--log-every', type=int, default=25)
    parser.add_argument('--max-minutes', type=float, default=0.0)
    parser.add_argument('--device', default='auto')
    parser.add_argument('--shards', default='')
    parser.add_argument('--dialogues', default='',
                        help='artifacts folder containing dialogues/ (build task 2)')
    parser.add_argument('--dialogue-split', default='train',
                        help="a file under dialogues/, or 'train' to stream from the "
                             "generator (the default; no training file is shipped)")
    parser.add_argument('--generate-split', default='L1', choices=('L1', 'L2'))
    parser.add_argument('--dialogue-start', type=int, default=L.TRAIN_INDEX_START,
                        help='first generated dialogue index; must be past the sealed '
                             f'block 0..{L.SEALED_INDEX_END - 1}')
    parser.add_argument('--symbol-mode', default='m0', choices=('m0', 'pool'))
    parser.add_argument('--code-pool', default='train', choices=('train', 'reserved'))
    parser.add_argument('--allow-sealed', action='store_true',
                        help='train on a SEALED evaluation set (debugging only)')
    parser.add_argument('--synthetic-dialogues', type=int, default=512,
                        help='number of dialogues to generate (or synthesise) per run')
    parser.add_argument('--synthetic-sentences', type=int, default=4096)
    parser.add_argument('--out', required=True)
    parser.add_argument('--die-at', type=int, default=None,
                        help='SIGKILL the process at this step (kill test only)')


def train_config_from(args):
    return TrainConfig(stage=args.stage, preset=args.preset, gru_mouth=args.gru_mouth,
                       steps=args.steps, seed=args.seed, lr=args.lr, warmup=args.warmup,
                       micro_batch=args.micro_batch, batch_tokens=args.batch_tokens,
                       checkpoint_minutes=args.checkpoint_minutes,
                       checkpoint_steps=args.checkpoint_steps, log_every=args.log_every,
                       max_minutes=args.max_minutes, device=args.device,
                       shards=args.shards, dialogues=args.dialogues,
                       dialogue_split=args.dialogue_split,
                       generate_split=args.generate_split,
                       dialogue_start=args.dialogue_start,
                       symbol_mode=args.symbol_mode, code_pool=args.code_pool,
                       allow_sealed=args.allow_sealed,
                       synthetic_dialogues=args.synthetic_dialogues,
                       synthetic_sentences=args.synthetic_sentences, out=args.out)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest='command', required=True)
    add_train_args(sub.add_parser('train'))
    add_train_args(sub.add_parser('restart-loop'))
    k = sub.add_parser('kill-test')
    k.add_argument('--out', required=True)
    k.add_argument('--steps', type=int, default=40)
    k.add_argument('--die-at', type=int, default=18)
    k.add_argument('--preset', default='tiny')
    k.add_argument('--stage', default='autoencode', choices=STAGES)
    k.add_argument('--micro-batch', type=int, default=8)
    e = sub.add_parser('eval', help='the S0 model marks on a checkpoint')
    e.add_argument('--checkpoint', required=True)
    e.add_argument('--n', type=int, default=256)
    e.add_argument('--max-len', type=int, default=16)
    e.add_argument('--device', default='cpu')
    e.add_argument('--shards', default='')
    e.add_argument('--dialogues', default='')
    e.add_argument('--json', default=None)
    b = sub.add_parser('bench')
    b.add_argument('--presets', nargs='*', default=['M', 'L', 'XL'])
    b.add_argument('--steps', type=int, default=20)
    b.add_argument('--batch', type=int, default=32)
    b.add_argument('--length', type=int, default=48)
    b.add_argument('--device', default=None)
    b.add_argument('--gru-mouth', action='store_true')
    b.add_argument('--json', default=None)
    args = parser.parse_args(argv)
    if torch.cuda.is_available():
        torch.backends.cuda.matmul.allow_tf32 = True
    else:
        torch.set_num_threads(1)

    if args.command == 'train':
        trainer = Trainer(train_config_from(args))
        trainer.maybe_resume()
        result = trainer.run(die_at=args.die_at)
        # A run that stopped because it hit its own time cap did what it was told, so it
        # exits 0: the restart loop must not treat a deliberate stop as a crash.
        return 0 if (result.get('finished')
                     or result.get('stopped') == 'time-limit') else 3
    if args.command == 'restart-loop':
        passthrough = [a for a in (sys.argv[2:] if argv is None else argv[1:])]
        return restart_loop(passthrough)
    if args.command == 'eval':
        report = evaluate(args.checkpoint, n=args.n, device=args.device,
                          max_len=args.max_len, shards=args.shards,
                          dialogues=args.dialogues)
        print(json.dumps(report, indent=2))
        if args.json:
            Path(args.json).parent.mkdir(parents=True, exist_ok=True)
            Path(args.json).write_text(json.dumps(report, indent=2))
        print('S0 MODEL MARKS: ' + ('ALL MET' if report['all_marks_met']
                                    else 'NOT ALL MET'))
        return 0
    if args.command == 'kill-test':
        result = kill_test(args.out, steps=args.steps, die_at=args.die_at,
                           preset=args.preset, stage=args.stage,
                           micro_batch=args.micro_batch)
        Path(args.out).mkdir(parents=True, exist_ok=True)
        (Path(args.out)/'kill-test.json').write_text(json.dumps(result, indent=2))
        print(json.dumps(result, indent=2))
        print('KILL TEST: ' + ('BIT-IDENTICAL' if result.get('ok') else 'NOT IDENTICAL'))
        return 0 if result.get('ok') else 1
    rows = [benchmark(p, steps=args.steps, device=args.device, batch=args.batch,
                      length=args.length, gru_mouth=args.gru_mouth)
            for p in args.presets]
    for row in rows:
        print(json.dumps(row))
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(rows, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
