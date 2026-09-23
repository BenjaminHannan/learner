"""Talker 24 -- ears, the 416-number typed thought, mouth, thinker, side arms.

Build task 3 of design/v3/24-talker-from-scratch-fable-design.md section 8, under the
decisions recorded in design/v3/24b-talker-decisions-ben.md (every recommended option).

THE FLOOR PLAN (section 3.4, "by construction")

  ears   : one sentence of <= 48 word-pieces  ->  ONE 416-number thought
  middle : thought -> notebook row / canonical question -> the FROZEN 79,316-parameter
           lookup operator (scripts/fable_talker24_bridge.py) -> answer code -> reply thought
  mouth  : ONE reply thought -> English.  It is shown NOTHING else.  Its ``forward``
           signature cannot even name the source sentence.

  Two structural walls, checked by ``floor_plan_report()`` and by the perturbation test in
  tests/test_fable_talker24_model.py:

    1. ``Mouth.forward`` / ``GRUMouth.forward`` accept a thought and the mouth's OWN
       previous output tokens.  No parameter may be named after the source sentence, the
       encoder states, the conversation or the notebook.  Changing the input words while
       holding the thought fixed changes no output bit -- there is no path.
    2. ``Thinker.forward`` accepts thoughts only.  No token ever enters the middle.

  And one representational wall: names and values reach the output ONLY by copy.  The
  mouth emits the copy actions ``<SUBJ>`` (5) ``<OBJ>`` (6) ``<OLD>`` (7); the printer
  resolves them through the symbol table from codes that were ROUTED (pointer + straight
  through) out of the input, never regressed.  A code that is not in the copy environment
  has probability exactly 0.0 of being spoken -- see ``code_emission_probability``.

THE 416 NUMBERS (section 3.2)

  | field         | slice     | size |
  | act           | 0:8       |   8  | TELL ASK CORRECT CHAT UNCLEAR + 3 spare
  | subject       | 8:56      |  48  | a symbol-table code, pointed at, never regressed
  | relation path | 56:104    |  48  | 3 x 16 (15 relations + "none")
  | object        | 104:152   |  48  | a symbol-table code, or all-zero for "no object"
  | flags         | 152:160   |   8  | path length, speaker, unknown-reason, has-old-value
  | gist          | 160:416   | 256  | only the first 32 survive when act != CHAT

RUNS ON: Mac CPU (this file's tests) and Windows + CUDA (S0 and the long runs).  Plain
torch + numpy; no ``tokenizers``, no ``datasets``, no ``torch.compile`` (unsupported for
NVIDIA on Windows -- section 2.3), eager mode everywhere.

CLI
  sizes                    print the exact parameter count of every preset, part by part
  floor-plan               print the structural report (signatures + wall checks)
  selftest                 a few seconds of shape and wall checks, no data needed
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field, asdict, replace
import importlib.util
import inspect
import json
import math
from pathlib import Path
import sys

# --------------------------------------------------------------------- torch bootstrap
# The project keeps its wheels in a uv cache and lists them in runtime.local.json; on the
# Windows GPU box torch is an ordinary import.  Try the ordinary import first so nothing
# Mac-specific is baked in.

HERE = Path(__file__).resolve().parent
WORKTREE = HERE.parent
BASE = Path('/Users/ben-hannan/Desktop/projects/beautiful-model')


def _bootstrap_torch():
    if importlib.util.find_spec('torch') is not None:
        return
    for root in (WORKTREE, BASE, HERE.parents[1]):
        path = root/'runtime.local.json'
        if path.exists():
            roots = json.loads(path.read_text()).get('import_roots', [])
            sys.path[:0] = [p for p in roots if Path(p).is_dir()]
            if importlib.util.find_spec('torch') is not None:
                return


_bootstrap_torch()

import torch                                                           # noqa: E402
from torch import nn                                                   # noqa: E402
import torch.nn.functional as F                                        # noqa: E402

# ------------------------------------------------------------------- the fixed vocabulary
# Mirrors artifacts/fable-talker24-20260920/INTERFACE-data.md section 2 exactly.  If that
# file changes, this block and fable_talker24_loader.ASSUMPTIONS change with it.

VOCAB_SIZE = 8192
PAD, BOS, EOS, UNK, ENT, SUBJ, OBJ, OLD, TURN, DOC = range(10)
COPY_ACTIONS = (SUBJ, OBJ, OLD)
COPY_ACTION_NAMES = ('<SUBJ>', '<OBJ>', '<OLD>')
ENT_NONE = 65535                       # INTERFACE-data.md: "no code at this position"
ENT_POOL = 4096                        # entity codes 0..4095 (3072..4095 reserved)
ENT_RESERVED_MIN = 3072
VALUE_CODE_MIN = 4096                  # model-side extension, see MODEL_SIDE_CODE_NOTE
VALUE_CODE_COUNT = 256
CODE_TABLE_SIZE = VALUE_CODE_MIN + VALUE_CODE_COUNT

MODEL_SIDE_CODE_NOTE = (
    'INTERFACE-data.md owns entity code ids 0..4095 and never emits anything else. The '
    'symbol table here is wider: 4096..4351 are VALUE codes, which the dialogue generator '
    '(build task 2) and the notebook bridge assign so that the object pointer can copy a '
    'value exactly the way it copies a name. Nothing in the data contract changes; every '
    'id still fits in uint16 and 65535 still means "no code".')

# ---------------------------------------------------------------------- thought layout

CODE_DIM = 48
ACT_DIM = 8
RELATION_SLOTS = 3
RELATION_CHOICES = 16                  # 15 relations + "none"
RELATION_DIM = RELATION_SLOTS*RELATION_CHOICES
FLAG_DIM = 8
GIST_DIM = 256
FACT_GIST_DIM = 32                     # section 3.2 rule 2: a fact thought has no free room
THOUGHT_DIM = ACT_DIM + CODE_DIM + RELATION_DIM + CODE_DIM + FLAG_DIM + GIST_DIM
assert THOUGHT_DIM == 416

FIELDS = (('act', 0, ACT_DIM),
          ('subject', ACT_DIM, CODE_DIM),
          ('relation_path', ACT_DIM + CODE_DIM, RELATION_DIM),
          ('object', ACT_DIM + CODE_DIM + RELATION_DIM, CODE_DIM),
          ('flags', ACT_DIM + CODE_DIM + RELATION_DIM + CODE_DIM, FLAG_DIM),
          ('gist', ACT_DIM + CODE_DIM + RELATION_DIM + CODE_DIM + FLAG_DIM, GIST_DIM))
SLICES = {name: slice(start, start + size) for name, start, size in FIELDS}

# Both act alphabets are 5 of 8.  The design lists replies as ACK/ANSWER/UNKNOWN/CLARIFY/
# CHAT; CHAT is moved to index 3 in BOTH alphabets so that the "gist is cut to 32 unless
# act == CHAT" rule is one index, not two.  (Judgement call, recorded in the report.)
HEARD_ACTS = ('TELL', 'ASK', 'CORRECT', 'CHAT', 'UNCLEAR', 'SPARE5', 'SPARE6', 'SPARE7')
REPLY_ACTS = ('ACK', 'ANSWER', 'UNKNOWN', 'CHAT', 'CLARIFY', 'SPARE5', 'SPARE6', 'SPARE7')
CHAT_ACT = 3
assert HEARD_ACTS[CHAT_ACT] == REPLY_ACTS[CHAT_ACT] == 'CHAT'

FLAG_NAMES = ('path_len_bit0', 'path_len_bit1', 'speaker_is_model', 'unknown_no_person',
              'unknown_no_fact', 'unknown_chain_broke', 'has_old_value', 'spare7')

RELATION_NONE = 0                      # choice 0 of 16 in every relation-path slot


# ============================================================================ presets

@dataclass
class TalkerConfig:
    """Every size is configuration.  No preset is spelled anywhere in the model code."""
    name: str = 'M'
    vocab_size: int = VOCAB_SIZE
    width: int = 384
    heads: int = 6
    enc_blocks: int = 6
    dec_blocks: int = 6
    thinker_blocks: int = 4
    mlp_ratio: int = 4
    max_len: int = 48                  # word-pieces per sentence (section 2.2)
    prefix_slots: int = 8              # the thought enters the mouth as 8 vectors
    thinker_context: int = 24          # <= 24 past thoughts + the notebook result
    pool_queries: int = 4
    pointer_dim: int = 64
    code_table_size: int = CODE_TABLE_SIZE
    code_seed: int = 24
    # side arm and yardstick
    gru_layers: int = 2
    gru_hidden: int = 768
    lm_width: int = 512
    lm_blocks: int = 8
    lm_heads: int = 8
    lm_context: int = 512
    # behaviour
    pointer_straight_through: bool = True
    hard_act: bool = False             # eval() flips this on; see Ears.forward

    @property
    def head_dim(self):
        return self.width//self.heads


PRESETS = {
    # S -- smoke test only (S0).  Design: "4+4+2 blocks, width 192".
    'S': TalkerConfig(name='S', width=192, heads=6, enc_blocks=4, dec_blocks=4,
                      thinker_blocks=2, gru_hidden=768, lm_width=256, lm_blocks=4,
                      lm_heads=4),
    # M -- the default (D2).  Design: "6 layers x width 384 each side" ~ 33M.
    'M': TalkerConfig(name='M', width=384, heads=6, enc_blocks=6, dec_blocks=6,
                      thinker_blocks=4),
    # L -- the first scale-up step.  Design says "85M (8+8+4 blocks, width 640)"; 640 is
    # arithmetically ~106M, so the stated NUMBER is honoured and the width is 576.
    # 'L640' below is the design's literal width, for whoever prefers it.
    'L': TalkerConfig(name='L', width=576, heads=9, enc_blocks=8, dec_blocks=8,
                      thinker_blocks=4, gru_hidden=1024),
    'L640': TalkerConfig(name='L640', width=640, heads=10, enc_blocks=8, dec_blocks=8,
                         thinker_blocks=4, gru_hidden=1024),
    # XL -- the second scale-up step Ben asked about (~200M total).
    'XL': TalkerConfig(name='XL', width=768, heads=12, enc_blocks=12, dec_blocks=12,
                       thinker_blocks=4, gru_hidden=1280),
    # tiny -- unit tests only.  Never trained on anything real.
    'tiny': TalkerConfig(name='tiny', vocab_size=96, width=32, heads=2, enc_blocks=2,
                         dec_blocks=2, thinker_blocks=1, max_len=16, prefix_slots=4,
                         thinker_context=6, pointer_dim=16, code_table_size=64,
                         gru_layers=1, gru_hidden=48, lm_width=32, lm_blocks=2,
                         lm_heads=2, lm_context=32),
}


def config(name='M', **overrides):
    if name not in PRESETS:
        raise KeyError(f'unknown preset {name!r}; have {sorted(PRESETS)}')
    return replace(PRESETS[name], **overrides) if overrides else replace(PRESETS[name])


# ============================================================== transformer ingredients

class RMSNorm(nn.Module):
    def __init__(self, width, eps=1e-6):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(width))
        self.eps = eps

    def forward(self, x):
        dtype = x.dtype
        x = x.float()
        x = x*torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.eps)
        return (x*self.weight.float()).to(dtype)


def rotary_table(length, head_dim, device, dtype):
    inv = 1.0/(10000.0**(torch.arange(0, head_dim, 2, device=device, dtype=torch.float32)
                         / head_dim))
    t = torch.arange(length, device=device, dtype=torch.float32)
    freqs = torch.outer(t, inv)
    return freqs.cos().to(dtype), freqs.sin().to(dtype)


def apply_rotary(x, cos, sin):
    """x: [B, heads, T, head_dim]."""
    a, b = x[..., 0::2], x[..., 1::2]
    cos, sin = cos[None, None], sin[None, None]
    return torch.stack((a*cos - b*sin, a*sin + b*cos), dim=-1).flatten(-2)


class Attention(nn.Module):
    """4 d^2 parameters: fused qkv + output.  No biases.  QK-norm.  Fused SDPA."""

    def __init__(self, cfg, causal):
        super().__init__()
        self.heads, self.head_dim, self.causal = cfg.heads, cfg.head_dim, causal
        self.qkv = nn.Linear(cfg.width, 3*cfg.width, bias=False)
        self.out = nn.Linear(cfg.width, cfg.width, bias=False)
        self.q_norm = RMSNorm(cfg.head_dim)
        self.k_norm = RMSNorm(cfg.head_dim)

    def forward(self, x, cos, sin, key_padding=None):
        B, T, _ = x.shape
        q, k, v = self.qkv(x).view(B, T, 3, self.heads, self.head_dim).permute(2, 0, 3, 1, 4)
        q, k = self.q_norm(q), self.k_norm(k)
        q, k = apply_rotary(q, cos, sin), apply_rotary(k, cos, sin)
        mask = None
        if key_padding is not None:                 # True where the key is real
            mask = key_padding[:, None, None, :].expand(B, self.heads, T, T)
            if self.causal:
                causal = torch.ones(T, T, dtype=torch.bool, device=x.device).tril()
                mask = mask & causal
            mask = mask.clone()
            # a fully-masked row would give NaN; let a padded query attend to itself
            dead = ~mask.any(-1)
            if dead.any():
                eye = torch.eye(T, dtype=torch.bool, device=x.device)[None, None]
                mask = mask | (dead[..., None] & eye)
            y = F.scaled_dot_product_attention(q, k, v, attn_mask=mask)
        else:
            y = F.scaled_dot_product_attention(q, k, v, is_causal=self.causal)
        return self.out(y.transpose(1, 2).reshape(B, T, -1))


class MLP(nn.Module):
    """8 d^2 parameters (4x hidden, GELU, no biases)."""

    def __init__(self, cfg, width=None):
        super().__init__()
        width = width or cfg.width
        hidden = cfg.mlp_ratio*width
        self.up = nn.Linear(width, hidden, bias=False)
        self.down = nn.Linear(hidden, width, bias=False)

    def forward(self, x):
        return self.down(F.gelu(self.up(x), approximate='tanh'))


class Block(nn.Module):
    """12 d^2 parameters: the unit the design's parameter table counts."""

    def __init__(self, cfg, causal):
        super().__init__()
        self.n1, self.n2 = RMSNorm(cfg.width), RMSNorm(cfg.width)
        self.attn, self.mlp = Attention(cfg, causal), MLP(cfg)

    def forward(self, x, cos, sin, key_padding=None):
        x = x + self.attn(self.n1(x), cos, sin, key_padding)
        return x + self.mlp(self.n2(x))


class Stack(nn.Module):
    def __init__(self, cfg, blocks, causal):
        super().__init__()
        self.cfg, self.causal = cfg, causal
        self.blocks = nn.ModuleList(Block(cfg, causal) for _ in range(blocks))
        self.norm = RMSNorm(cfg.width)

    def forward(self, x, key_padding=None):
        cos, sin = rotary_table(x.shape[1], self.cfg.head_dim, x.device, x.dtype)
        for block in self.blocks:
            x = block(x, cos, sin, key_padding)
        return self.norm(x)


# ================================================================== the symbol table

class SymbolTable(nn.Module):
    """Frozen random 48-number codes, one per code id.  NEVER trained, never regressed.

    Section 4.3: the codes are drawn once from a fixed seed, so the same id means the same
    48 numbers on the Mac and on the GPU box, in every run.  Ids 3072..4095 are the
    reserved entity codes the talker must never have seen; 4096..4351 are value codes
    (MODEL_SIDE_CODE_NOTE).
    """

    def __init__(self, cfg):
        super().__init__()
        generator = torch.Generator().manual_seed(cfg.code_seed)
        codes = torch.randn(cfg.code_table_size, CODE_DIM, generator=generator)
        codes = codes/codes.norm(dim=-1, keepdim=True)*math.sqrt(CODE_DIM)
        self.register_buffer('codes', codes, persistent=True)
        self.size = cfg.code_table_size

    def lookup(self, ids):
        """ids: any integer tensor, ENT_NONE -> the zero code."""
        safe = torch.where(ids >= self.size, torch.zeros_like(ids), ids)
        out = self.codes[safe.long()]
        return torch.where((ids >= self.size)[..., None], torch.zeros_like(out), out)

    @torch.no_grad()
    def nearest(self, code, atol=1e-4):
        """Decode a code vector back to its id.  Returns -1 when it is not a table code.

        A routed code is a table row BIT-FOR-BIT, so the honest decode is an exact row
        match, tried first.  (``torch.cdist`` is not used for this: its matmul trick loses
        enough float32 precision that a code does not always match itself.)  The
        tolerance branch only exists so that a blended code -- which straight-through
        routing never produces -- is reported as "not a code" rather than silently
        snapping to the closest one.
        """
        flat = code.reshape(-1, CODE_DIM).float()
        table = self.codes.float()
        out = torch.full((flat.shape[0],), -1, dtype=torch.long, device=flat.device)
        for start in range(0, flat.shape[0], 64):
            chunk = flat[start:start + 64]
            equal = (chunk[:, None, :] == table[None]).all(-1)
            has = equal.any(-1)
            index = equal.to(torch.uint8).argmax(-1).long()
            if not bool(has.all()):
                d = torch.cdist(chunk.double(), table.double())
                best = d.argmin(-1)
                close = d.gather(-1, best[:, None])[:, 0] <= atol
                index = torch.where(has, index,
                                    torch.where(close, best, torch.full_like(best, -1)))
                has = has | close
            picked = torch.where(has, index, torch.full_like(index, -1))
            zero = chunk.abs().amax(-1) == 0
            out[start:start + chunk.shape[0]] = torch.where(
                zero, torch.full_like(picked, -1), picked)
        return out.reshape(code.shape[:-1])


# ============================================================== thought helpers (pure)

def field_of(thought, name):
    return thought[..., SLICES[name]]


def gist_gate(act_vector):
    """The section 3.2 capacity rule, differentiably.

    Gist dimensions 0..31 always survive.  32..255 are multiplied by P(act == CHAT), which
    is exactly 0 or 1 once the act is hard.  With a soft act during training the rule is
    the same rule, smoothed -- no separate code path, so nothing can drift apart.
    """
    chat = act_vector[..., CHAT_ACT:CHAT_ACT + 1]
    keep = torch.ones(GIST_DIM, device=act_vector.device, dtype=act_vector.dtype)
    keep = keep[None].expand(*act_vector.shape[:-1], GIST_DIM).clone()
    keep[..., FACT_GIST_DIM:] = chat
    return keep


def assemble_thought(act, subject, relation_path, object_code, flags, gist):
    gist = gist*gist_gate(act)
    return torch.cat((act, subject, relation_path, object_code, flags, gist), dim=-1)


def blank_thought(batch, device=None, dtype=torch.float32):
    return torch.zeros(batch, THOUGHT_DIM, device=device, dtype=dtype)


def thought_report(thought, symbols):
    """A human-readable reading of one thought.  Used by the trace and by the tests."""
    act = int(field_of(thought, 'act').argmax(-1))
    path = field_of(thought, 'relation_path').reshape(RELATION_SLOTS, RELATION_CHOICES)
    return dict(act=act,
                act_heard=HEARD_ACTS[act], act_reply=REPLY_ACTS[act],
                subject_code=int(symbols.nearest(field_of(thought, 'subject'))),
                object_code=int(symbols.nearest(field_of(thought, 'object'))),
                relation_path=[int(p.argmax(-1)) for p in path],
                flags=[float(f) for f in field_of(thought, 'flags')],
                gist_live=int((field_of(thought, 'gist').abs() > 0).sum()))


# ====================================================================== ears (encoder)

class Pointer(nn.Module):
    """Route, never regress.  A softmax over input positions; the forward value is the
    hard one-hot, the gradient is the soft one (straight-through).  The selected code is
    therefore a bit-exact row of the symbol table."""

    def __init__(self, cfg, with_null):
        super().__init__()
        self.q = nn.Linear(cfg.width, cfg.pointer_dim, bias=False)
        self.scale = cfg.pointer_dim**-0.5
        self.straight_through = cfg.pointer_straight_through
        self.null = nn.Parameter(torch.zeros(cfg.pointer_dim)) if with_null else None

    def forward(self, query, keys, codes, copyable):
        """query [B,d]; keys [B,T,p]; codes [B,T,48]; copyable [B,T] bool."""
        scores = torch.einsum('bp,btp->bt', self.q(query), keys)*self.scale
        if self.null is not None:
            null_score = (self.q(query)*self.null).sum(-1, keepdim=True)*self.scale
            scores = torch.cat((scores, null_score), dim=-1)
            copyable = torch.cat((copyable, torch.ones_like(copyable[:, :1])), dim=-1)
            codes = torch.cat((codes, torch.zeros_like(codes[:, :1])), dim=1)
        scores = scores.masked_fill(~copyable, float('-inf'))
        dead = ~copyable.any(-1)
        if dead.any():                      # nothing copyable at all -> the zero code
            scores = torch.where(dead[:, None], torch.zeros_like(scores), scores)
        soft = scores.softmax(-1)
        index = soft.argmax(-1)
        blended = torch.einsum('bt,btc->bc', soft, codes)
        if self.straight_through:
            # The forward value is the GATHERED row -- bit-for-bit the symbol table's own
            # 48 numbers.  (A one-hot matmul is NOT bit-exact: it rounds by about one ULP,
            # which is enough to stop a code decoding to itself.)  The gradient is the
            # soft mixture's, so the pointer still learns.
            picked = codes.gather(1, index[:, None, None].expand(-1, 1, CODE_DIM))[:, 0]
            # The parentheses matter: ``blended - blended.detach()`` is EXACTLY the zero
            # tensor, so ``picked + 0`` is bit-exact, while ``picked + blended - blended``
            # would be evaluated as ``(picked + blended) - blended`` and round.
            code = picked + (blended - blended.detach())
        else:
            code = blended
        if dead.any():
            code = torch.where(dead[:, None], torch.zeros_like(code), code)
        return code, soft, index


class Ears(nn.Module):
    """One sentence in, one 416-number thought out.  Looks both ways; no causal mask."""

    def __init__(self, cfg, embedding, symbols):
        super().__init__()
        self.cfg, self.embedding, self.symbols = cfg, embedding, symbols
        self.code_in = nn.Linear(CODE_DIM, cfg.width, bias=False)
        self.stack = Stack(cfg, cfg.enc_blocks, causal=False)
        self.queries = nn.Parameter(torch.randn(cfg.pool_queries, cfg.width)*0.02)
        self.pool_k = nn.Linear(cfg.width, cfg.width, bias=False)
        self.act_head = nn.Linear(cfg.width, ACT_DIM, bias=False)
        self.flag_head = nn.Linear(cfg.width, FLAG_DIM, bias=False)
        self.path_head = nn.Linear(cfg.width, RELATION_DIM, bias=False)
        self.gist_head = nn.Linear(2*cfg.width, GIST_DIM, bias=False)
        self.pointer_k = nn.Linear(cfg.width, cfg.pointer_dim, bias=False)
        self.subject_pointer = Pointer(cfg, with_null=True)
        self.object_pointer = Pointer(cfg, with_null=True)

    def embed(self, tokens, code_ids):
        x = self.embedding(tokens)
        if code_ids is not None:
            has = code_ids < self.symbols.size
            x = x + self.code_in(self.symbols.lookup(code_ids))*has[..., None].to(x.dtype)
        return x

    def forward(self, tokens, code_ids=None, attention_mask=None, hard_act=None):
        """tokens [B,T] int; code_ids [B,T] int (ENT_NONE where there is no code)."""
        if attention_mask is None:
            attention_mask = tokens != PAD
        h = self.stack(self.embed(tokens, code_ids), key_padding=attention_mask)
        # four learned pooling queries, single-head, values are the states themselves
        k = self.pool_k(h)
        scores = torch.einsum('qd,btd->bqt', self.queries, k)*self.cfg.width**-0.5
        scores = scores.masked_fill(~attention_mask[:, None, :], float('-inf'))
        pooled = torch.einsum('bqt,btd->bqd', scores.softmax(-1), h)

        act_logits = self.act_head(pooled[:, 0])
        hard = self.cfg.hard_act if hard_act is None else hard_act
        act = F.one_hot(act_logits.argmax(-1), ACT_DIM).to(act_logits.dtype) \
            if hard else act_logits.softmax(-1)
        flags = torch.sigmoid(self.flag_head(pooled[:, 0]))
        path_logits = self.path_head(pooled[:, 1]).view(-1, RELATION_SLOTS, RELATION_CHOICES)
        path = (F.one_hot(path_logits.argmax(-1), RELATION_CHOICES).to(path_logits.dtype)
                if hard else path_logits.softmax(-1))
        gist = self.gist_head(torch.cat((pooled[:, 2], pooled[:, 3]), dim=-1))

        keys = self.pointer_k(h)
        codes = self.symbols.lookup(code_ids) if code_ids is not None \
            else torch.zeros(*tokens.shape, CODE_DIM, device=tokens.device, dtype=h.dtype)
        copyable = (code_ids < self.symbols.size) & attention_mask if code_ids is not None \
            else torch.zeros_like(attention_mask)
        subject, subj_p, subj_i = self.subject_pointer(pooled[:, 0], keys, codes, copyable)
        object_, obj_p, obj_i = self.object_pointer(pooled[:, 1], keys, codes, copyable)

        thought = assemble_thought(act, subject, path.reshape(-1, RELATION_DIM),
                                   object_, flags, gist)
        return dict(thought=thought, act_logits=act_logits, path_logits=path_logits,
                    flag_logits=self.flag_head(pooled[:, 0]),
                    subject_pointer=subj_p, object_pointer=obj_p,
                    subject_index=subj_i, object_index=obj_i,
                    gist=gist, states=h, pooled=pooled)


# ====================================================================== mouth (decoder)

class Mouth(nn.Module):
    """The thought, and nothing else.

    ``forward(thought, reply_tokens)``.  ``reply_tokens`` are the mouth's OWN previous
    outputs (teacher forcing).  There is no parameter, buffer or closure through which a
    source sentence, an encoder state, the conversation or the notebook could arrive --
    ``floor_plan_report`` checks the signature against FORBIDDEN_MOUTH_ARGS and
    tests/test_fable_talker24_model.py checks it numerically.
    """

    def __init__(self, cfg, embedding):
        super().__init__()
        self.cfg, self.embedding = cfg, embedding
        self.prefix = nn.Linear(THOUGHT_DIM, cfg.prefix_slots*cfg.width, bias=False)
        self.stack = Stack(cfg, cfg.dec_blocks, causal=True)

    def forward(self, thought, reply_tokens=None):
        """``reply_tokens`` starts with <bos>; ``logits[:, j]`` predicts the token that
        follows ``reply_tokens[:, j]``.  Same contract as GRUMouth."""
        B = thought.shape[0]
        prefix = self.prefix(thought).view(B, self.cfg.prefix_slots, self.cfg.width)
        if reply_tokens is None or reply_tokens.shape[1] == 0:
            reply_tokens = torch.full((B, 1), BOS, dtype=torch.long,
                                      device=thought.device)
        x = torch.cat((prefix, self.embedding(reply_tokens)), dim=1)
        h = self.stack(x)
        logits = F.linear(h, self.embedding.weight)         # tied
        return logits[:, self.cfg.prefix_slots:]

    @torch.no_grad()
    def speak(self, thought, max_new=48, banned=(PAD, BOS, ENT), greedy=True,
              temperature=1.0, generator=None):
        """Greedy (or sampled) decoding.  ``banned`` keeps <ENT> out of a reply: a name
        has no route to the output except a copy action."""
        device = thought.device
        tokens = torch.full((thought.shape[0], 1), BOS, dtype=torch.long, device=device)
        done = torch.zeros(thought.shape[0], dtype=torch.bool, device=device)
        for _ in range(max_new):
            logits = self(thought, tokens)[:, -1]
            for b in banned:
                logits[:, b] = float('-inf')
            if greedy:
                nxt = logits.argmax(-1)
            else:
                probs = (logits/max(temperature, 1e-6)).softmax(-1)
                nxt = torch.multinomial(probs, 1, generator=generator)[:, 0]
            nxt = torch.where(done, torch.full_like(nxt, PAD), nxt)
            tokens = torch.cat((tokens, nxt[:, None]), dim=1)
            done = done | (nxt == EOS)
            if bool(done.all()):
                break
        return tokens[:, 1:]


class GRUMouth(nn.Module):
    """The section 3.3 side arm: the same contract, a fixed-state decoder.

    Twenty minutes inside S0, reported beside the transformer on exact reconstruction,
    slot-swap faithfulness and tokens per second.  Same wall: thought in, words out.
    """

    def __init__(self, cfg, embedding):
        super().__init__()
        self.cfg, self.embedding = cfg, embedding
        self.init = nn.Linear(THOUGHT_DIM, cfg.gru_layers*cfg.gru_hidden, bias=False)
        self.gru = nn.GRU(cfg.width, cfg.gru_hidden, cfg.gru_layers, batch_first=True)
        self.out = nn.Linear(cfg.gru_hidden, cfg.width, bias=False)

    def forward(self, thought, reply_tokens=None):
        B = thought.shape[0]
        h0 = self.init(thought).view(B, self.cfg.gru_layers, self.cfg.gru_hidden)
        h0 = h0.transpose(0, 1).contiguous()
        if reply_tokens is None or reply_tokens.shape[1] == 0:
            reply_tokens = torch.full((B, 1), BOS, dtype=torch.long,
                                      device=thought.device)
        y, _ = self.gru(self.embedding(reply_tokens), h0)
        return F.linear(self.out(y), self.embedding.weight)

    speak = Mouth.speak


# ========================================================================== the thinker

class Thinker(nn.Module):
    """The middle.  Thoughts in, one reply thought out.  NO TOKEN EVER ENTERS HERE.

    Reads <= ``thinker_context`` past thoughts plus the reasoner's result (itself a
    thought), left to right.  Its slot pointers choose WHICH EARLIER SLOT fills a reply
    slot, so a reply code is one of the codes already on the table -- routed, never
    regressed (section 3.2 rule 1).
    """

    def __init__(self, cfg, symbols):
        super().__init__()
        self.cfg, self.symbols = cfg, symbols
        self.thought_in = nn.Linear(THOUGHT_DIM, cfg.width, bias=False)
        self.stack = Stack(cfg, cfg.thinker_blocks, causal=True)
        self.act_head = nn.Linear(cfg.width, ACT_DIM, bias=False)
        self.flag_head = nn.Linear(cfg.width, FLAG_DIM, bias=False)
        self.path_head = nn.Linear(cfg.width, RELATION_DIM, bias=False)
        self.gist_head = nn.Linear(cfg.width, GIST_DIM, bias=False)
        self.slot_k = nn.Linear(cfg.width, cfg.pointer_dim, bias=False)
        self.subject_pointer = Pointer(cfg, with_null=True)
        self.object_pointer = Pointer(cfg, with_null=True)

    def forward(self, thoughts, thought_mask=None, hard_act=None):
        """thoughts [B,L,416] -- the conversation so far, the reasoner's result last."""
        B, L, _ = thoughts.shape
        if thought_mask is None:
            thought_mask = torch.ones(B, L, dtype=torch.bool, device=thoughts.device)
        h = self.stack(self.thought_in(thoughts), key_padding=thought_mask)
        last = h[:, -1]

        act_logits = self.act_head(last)
        hard = self.cfg.hard_act if hard_act is None else hard_act
        act = F.one_hot(act_logits.argmax(-1), ACT_DIM).to(act_logits.dtype) \
            if hard else act_logits.softmax(-1)
        flags = torch.sigmoid(self.flag_head(last))
        path_logits = self.path_head(last).view(B, RELATION_SLOTS, RELATION_CHOICES)
        path = (F.one_hot(path_logits.argmax(-1), RELATION_CHOICES).to(path_logits.dtype)
                if hard else path_logits.softmax(-1))
        gist = self.gist_head(last)

        # candidate slots: every subject and object code already on the table
        subj_codes = field_of(thoughts, 'subject')
        obj_codes = field_of(thoughts, 'object')
        codes = torch.cat((subj_codes, obj_codes), dim=1)              # [B, 2L, 48]
        keys = self.slot_k(h).repeat(1, 2, 1)
        alive = (codes.abs().amax(-1) > 0) & thought_mask.repeat(1, 2)
        subject, subj_p, subj_i = self.subject_pointer(last, keys, codes, alive)
        object_, obj_p, obj_i = self.object_pointer(last, keys, codes, alive)

        thought = assemble_thought(act, subject, path.reshape(B, RELATION_DIM),
                                   object_, flags, gist)
        return dict(thought=thought, act_logits=act_logits, path_logits=path_logits,
                    flag_logits=self.flag_head(last), gist=gist,
                    subject_pointer=subj_p, object_pointer=obj_p,
                    subject_index=subj_i, object_index=obj_i, slot_codes=codes)


# ====================================================================== the whole talker

class Talker(nn.Module):
    """Ears + mouth + thinker + the shared tied embedding + the frozen symbol table."""

    def __init__(self, cfg=None, gru_mouth=False):
        super().__init__()
        self.cfg = cfg or config('M')
        self.embedding = nn.Embedding(self.cfg.vocab_size, self.cfg.width)
        nn.init.normal_(self.embedding.weight, std=0.02)
        self.symbols = SymbolTable(self.cfg)
        self.ears = Ears(self.cfg, self.embedding, self.symbols)
        self.mouth = (GRUMouth(self.cfg, self.embedding) if gru_mouth
                      else Mouth(self.cfg, self.embedding))
        self.thinker = Thinker(self.cfg, self.symbols)
        self.gru_mouth = gru_mouth
        self.apply(self._init)

    @staticmethod
    def _init(module):
        if isinstance(module, nn.Linear):
            nn.init.normal_(module.weight, std=0.02)
            if module.bias is not None:
                nn.init.zeros_(module.bias)

    def hear(self, tokens, code_ids=None, attention_mask=None, hard_act=None):
        return self.ears(tokens, code_ids, attention_mask, hard_act)

    def say(self, thought, reply_tokens=None):
        return self.mouth(thought, reply_tokens)

    def autoencode(self, tokens, code_ids=None, attention_mask=None, targets=None,
                   gist_noise=0.0, gist_dropout=0.0, swap_gist=None, generator=None):
        """Squeeze a sentence into a thought and say it back (S1 stage 1)."""
        heard = self.ears(tokens, code_ids, attention_mask)
        thought = heard['thought']
        if swap_gist is not None:
            thought = torch.cat((thought[..., :SLICES['gist'].start],
                                 swap_gist*gist_gate(field_of(thought, 'act'))), dim=-1)
        if gist_noise or gist_dropout:
            thought = perturb_gist(thought, gist_noise, gist_dropout, generator)
        # ``tokens`` is the framed sentence <bos> ... <eos>.  The mouth is fed everything
        # but the last piece and predicts everything but the first -- exactly what
        # ``Mouth.speak`` does at inference, which is why an overfit model reconstructs
        # free-running and not only under teacher forcing.
        frame = tokens if targets is None else targets
        inputs, targets = frame[:, :-1], frame[:, 1:]
        logits = self.mouth(thought, inputs)
        return dict(heard=heard, thought=thought, logits=logits, targets=targets)

    def parameter_counts(self):
        return parameter_counts(self)


def perturb_gist(thought, noise=0.2, dropout=0.1, generator=None):
    """Section 2.3: Gaussian noise at sigma x the gist's per-dimension spread, plus gist
    dropout.  Applied to the gist only; the routed codes stay bit-exact."""
    gist = field_of(thought, 'gist')
    out = gist
    # Device fix (S0 on BensPC): the trainer's RNG is a CPU ``torch.Generator``, and
    # ``torch.randn``/``torch.rand`` refuse a generator whose device differs from the
    # target device -- so on cuda (or mps) this raised at step 1 of every run.  Draw on
    # the generator's own device, then move the draw to the gist.  When the two already
    # agree (the CPU path) ``.to`` is a no-op and the random stream is bit-identical.
    gen_device = generator.device if generator is not None else gist.device
    if noise:
        spread = gist.detach().std(dim=0, keepdim=True).clamp_min(1e-6)
        eps = torch.randn(gist.shape, device=gen_device, dtype=gist.dtype,
                          generator=generator).to(gist.device)
        out = out + eps*spread*noise
    if dropout:
        keep = torch.rand(gist.shape, device=gen_device, dtype=gist.dtype,
                          generator=generator).to(gist.device) >= dropout
        out = out*keep.to(out.dtype)
    out = out*gist_gate(field_of(thought, 'act'))
    return torch.cat((thought[..., :SLICES['gist'].start], out), dim=-1)


# ==================================================================== yardstick chat LM

class ChatLM(nn.Module):
    """D6: one ordinary ~29M decoder-only chat model on the same data.  The yardstick, and
    the comparison arm of section 4.1 option (a).  It sees words all the way through --
    that is the point of having it."""

    def __init__(self, cfg=None):
        cfg = cfg or config('M')
        super().__init__()
        inner = replace(cfg, width=cfg.lm_width, heads=cfg.lm_heads,
                        enc_blocks=cfg.lm_blocks, dec_blocks=cfg.lm_blocks,
                        max_len=cfg.lm_context)
        self.cfg = inner
        self.embedding = nn.Embedding(cfg.vocab_size, cfg.lm_width)
        nn.init.normal_(self.embedding.weight, std=0.02)
        self.stack = Stack(inner, cfg.lm_blocks, causal=True)

    def forward(self, tokens):
        return F.linear(self.stack(self.embedding(tokens)), self.embedding.weight)


# ======================================================== the printer and the copy wall

@dataclass
class CopyEnvironment:
    """What the three copy actions resolve to.

    ``subject`` and ``object`` are read out of the thought itself -- routed codes, so they
    are exact table ids.  ``old`` is the pre-correction value; the 416-number layout has no
    third code slot, so the MIDDLE supplies it from the notebook row the correction
    replaced (recorded as an ambiguity in the design; the value is still an exact code that
    was never regressed, and it is still reachable only through a copy action).
    """
    subject: int = -1
    object: int = -1
    old: int = -1

    def resolve(self, action):
        return {SUBJ: self.subject, OBJ: self.object, OLD: self.old}[action]

    def codes(self):
        return tuple(c for c in (self.subject, self.object, self.old) if c >= 0)

    @classmethod
    def from_thought(cls, thought, symbols, old=-1):
        return cls(subject=int(symbols.nearest(field_of(thought, 'subject'))),
                   object=int(symbols.nearest(field_of(thought, 'object'))), old=old)


def render(token_ids, environment, names, decode=None):
    """The printer.  A name reaches the output HERE and nowhere else.

    ``names`` maps a code id to its surface string.  An unresolved copy action is printed
    visibly (``<SUBJ?>``), never silently dropped.
    """
    pieces, plain = [], []

    def flush():
        if plain:
            pieces.append(decode(plain) if decode else ' '.join(str(t) for t in plain))
            plain.clear()

    for t in [int(t) for t in token_ids]:
        if t in (PAD, BOS, UNK, DOC):
            continue
        if t == EOS:
            break
        if t in COPY_ACTIONS:
            flush()
            code = environment.resolve(t)
            pieces.append(names.get(code, f'<{COPY_ACTION_NAMES[t - SUBJ][1:-1]}?>')
                          if code >= 0 else f'<{COPY_ACTION_NAMES[t - SUBJ][1:-1]}?>')
        elif t == ENT:
            flush()
            pieces.append('<ENT?>')      # no code source in a reply: visible, never silent
        elif t == TURN:
            flush()
            pieces.append('\n')
        else:
            plain.append(t)
    flush()
    return ''.join(pieces) if decode else ' '.join(pieces)


def code_emission_probability(probabilities, environment, code):
    """P(the spoken sentence names this code), exactly.

    ``probabilities`` is [T, vocab] of per-step probabilities.  The ONLY routes to a name
    are the three copy actions, and each resolves through ``environment``.  If no route
    resolves to ``code``, the answer is the float 0.0 -- not "small", zero, because the
    path does not exist.  This function is the test in tests/test_fable_talker24_model.py
    ("a name absent from the thought has exactly zero probability").
    """
    routes = [a for a in COPY_ACTIONS if environment.resolve(a) == code and code >= 0]
    if not routes:
        return 0.0
    miss = 1.0
    for step in probabilities:
        miss *= float(1.0 - sum(float(step[a]) for a in routes))
    return 1.0 - miss


def reachable_codes(thought, symbols, old=-1):
    return CopyEnvironment.from_thought(thought, symbols, old).codes()


# ======================================================== floor plan (structural checks)

FORBIDDEN_MOUTH_ARGS = ('source', 'source_tokens', 'src', 'src_tokens', 'input_ids',
                        'sentence', 'sentence_tokens', 'context', 'context_tokens',
                        'encoder', 'encoder_states', 'memory', 'notebook', 'rows',
                        'history', 'conversation', 'words', 'prompt', 'ent', 'code_ids')
FORBIDDEN_MIDDLE_ARGS = FORBIDDEN_MOUTH_ARGS + ('tokens', 'reply_tokens', 'targets',
                                                'ids', 'text')


def _signature(fn):
    return [p for p in inspect.signature(fn).parameters if p != 'self']


def floor_plan_report(model=None):
    """Every wall, checked -- signatures now, numbers in the test file."""
    out = {}
    for label, fn, forbidden in (('mouth', Mouth.forward, FORBIDDEN_MOUTH_ARGS),
                                 ('gru_mouth', GRUMouth.forward, FORBIDDEN_MOUTH_ARGS),
                                 ('mouth.speak', Mouth.speak, FORBIDDEN_MOUTH_ARGS),
                                 ('thinker', Thinker.forward, FORBIDDEN_MIDDLE_ARGS)):
        args = _signature(fn)
        bad = sorted(a for a in args if a in forbidden)
        out[label] = dict(arguments=args, forbidden_present=bad, ok=not bad)
    out['thought_dim'] = THOUGHT_DIM
    out['fact_gist_dim'] = FACT_GIST_DIM
    out['copy_actions'] = dict(zip(COPY_ACTION_NAMES, COPY_ACTIONS))
    if model is not None:
        mouth_modules = {id(m) for m in model.mouth.modules()}
        shared = [n for n, m in model.named_modules()
                  if id(m) in mouth_modules and not n.startswith('mouth')
                  and n not in ('', 'embedding')]
        out['mouth_shares_only_embedding'] = dict(shared=shared, ok=not shared)
    out['ok'] = all(v['ok'] for v in out.values() if isinstance(v, dict) and 'ok' in v)
    return out


# ================================================================== parameter counting

def _count(module):
    return sum(p.numel() for p in module.parameters())


def parameter_counts(model):
    """Exact counts, part by part, as the design's section 2.2 table lays them out."""
    embed = model.embedding.weight.numel()
    ears_total = _count(model.ears) - embed
    mouth_total = _count(model.mouth) - embed
    thinker_total = _count(model.thinker)
    ears_blocks = _count(model.ears.stack)
    ears_heads = ears_total - ears_blocks
    if model.gru_mouth:
        mouth_blocks = _count(model.mouth.gru)
        mouth_extra = mouth_total - mouth_blocks
    else:
        mouth_blocks = _count(model.mouth.stack)
        mouth_extra = mouth_total - mouth_blocks
    thinker_blocks = _count(model.thinker.stack)
    total = _count(model)
    counts = dict(word_embeddings_tied=embed,
                  ears_blocks=ears_blocks, ears_heads=ears_heads, ears_total=ears_total,
                  mouth_blocks=mouth_blocks, mouth_thought_prefix=mouth_extra,
                  mouth_total=mouth_total,
                  thinker_blocks=thinker_blocks,
                  thinker_heads=thinker_total - thinker_blocks,
                  thinker_total=thinker_total,
                  symbol_table_frozen_buffer=model.symbols.codes.numel(),
                  total_trainable=total)
    assert embed + ears_total + mouth_total + thinker_total == total, counts
    return counts


def preset_table(names=('S', 'M', 'L', 'L640', 'XL'), include_gru=True, include_lm=True):
    rows = []
    for name in names:
        cfg = config(name)
        model = Talker(cfg)
        row = dict(preset=name, width=cfg.width,
                   blocks=f'{cfg.enc_blocks}+{cfg.dec_blocks}+{cfg.thinker_blocks}',
                   **parameter_counts(model))
        if include_gru:
            row['gru_mouth_total'] = _count(Talker(cfg, gru_mouth=True).mouth) \
                - cfg.vocab_size*cfg.width
        if include_lm:
            row['yardstick_chat_lm'] = _count(ChatLM(cfg))
        row['reasoner_frozen'] = 79316
        rows.append(row)
    return rows


def forward_parameters(model):
    """Parameters a token passes through -- the 6*N*tokens FLOPs rule of section 2.4."""
    embed = model.embedding.weight.numel()
    return dict(autoencoder=_count(model.ears) + _count(model.mouth) - embed,
                thinker=_count(model.thinker) + _count(model.mouth) - embed
                + _count(model.ears) - embed,
                mouth_only=_count(model.mouth))


# ================================================================================ CLI

def _print_sizes(names):
    rows = preset_table(names)
    keys = ('preset', 'width', 'blocks', 'word_embeddings_tied', 'ears_blocks',
            'ears_heads', 'ears_total', 'mouth_blocks', 'mouth_thought_prefix',
            'mouth_total', 'thinker_blocks', 'thinker_heads', 'thinker_total',
            'total_trainable', 'gru_mouth_total', 'yardstick_chat_lm', 'reasoner_frozen')
    width = max(len(k) for k in keys)
    header = ' '.join(f'{r["preset"]:>14}' for r in rows)
    print(f'{"field".ljust(width)} {header}')
    for key in keys:
        if key == 'preset':
            continue
        cells = []
        for r in rows:
            v = r.get(key, '')
            cells.append(f'{v:>14,}' if isinstance(v, int) else f'{str(v):>14}')
        print(f'{key.ljust(width)} ' + ' '.join(cells))
    print()
    for r in rows:
        print(f'{r["preset"]:>5}: total {r["total_trainable"]:,} trainable '
              f'({r["total_trainable"]/1e6:.2f}M) + {r["reasoner_frozen"]:,} frozen '
              f'reasoner; yardstick chat LM {r["yardstick_chat_lm"]:,} '
              f'({r["yardstick_chat_lm"]/1e6:.2f}M)')
    return rows


def _selftest():
    torch.manual_seed(0)
    cfg = config('tiny')
    model = Talker(cfg).eval()
    B, T = 3, 10
    tokens = torch.randint(16, cfg.vocab_size, (B, T))
    codes = torch.full((B, T), ENT_NONE)
    codes[:, 2] = torch.tensor([5, 6, 7])
    tokens[:, 2] = ENT
    out = model.autoencode(tokens, codes)
    assert out['thought'].shape == (B, THOUGHT_DIM)
    assert out['logits'].shape == (B, T, cfg.vocab_size)
    fact = out['thought'].clone()
    fact[:, SLICES['act']] = F.one_hot(torch.zeros(B, dtype=torch.long), ACT_DIM).float()
    gated = assemble_thought(*[field_of(fact, n) for n, _, _ in FIELDS])
    assert float(field_of(gated, 'gist')[:, FACT_GIST_DIM:].abs().max()) == 0.0
    thoughts = out['thought'][:, None].repeat(1, 3, 1)
    reply = model.thinker(thoughts)
    assert reply['thought'].shape == (B, THOUGHT_DIM)
    plan = floor_plan_report(model)
    assert plan['ok'], plan
    print(json.dumps(plan, indent=2))
    print('selftest OK')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest='command', required=True)
    s = sub.add_parser('sizes', help='exact parameter counts per preset and part')
    s.add_argument('--presets', nargs='*', default=['S', 'M', 'L', 'L640', 'XL'])
    s.add_argument('--json', default=None)
    sub.add_parser('floor-plan', help='structural report')
    sub.add_parser('selftest', help='fast shape and wall checks')
    args = parser.parse_args(argv)
    torch.set_num_threads(1)
    if args.command == 'sizes':
        rows = _print_sizes(args.presets)
        if args.json:
            Path(args.json).write_text(json.dumps(rows, indent=2))
    elif args.command == 'floor-plan':
        print(json.dumps(floor_plan_report(Talker(config('tiny'))), indent=2))
    else:
        _selftest()


if __name__ == '__main__':
    main()
