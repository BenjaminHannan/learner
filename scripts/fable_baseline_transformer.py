"""A FAIR BASELINE for the v3 dispatcher panels: one ordinary decoder-only
transformer that reads the story and the question as a single sequence and writes
out its reasoning steps.

WHAT THIS IS FOR
----------------
System S (the thing being compared against) is two pieces:

  * a 79,316-parameter LOOKUP transformer (`premonition_token_memory.TokenMemoryReasoner`,
    wrapped as `astra_canonical_operator.CanonicalOperator`) that answers ONE canonical
    4-token query `[QUESTION, entity, relation, ANSWER]` against a story, and
  * a 15,522-parameter learned DISPATCHER (`fable_dispatcher_v3.Dispatcher`) that decides,
    by final-answer reward only, which query to send next and when to stop.

  Total 94,838 parameters.  Registered result: >= 59/64 answers WITH exact paths on
  every one of the 25 frozen panel cells, in 3/3 seeds.

This file is the obvious thing a sceptic asks for: "would a plain transformer of the
same size, allowed to write its chain of thought, just do this?"  It is a BASELINE, so
every choice that could be accused of hobbling it is made in its favour and written
down, and every advantage it has over S is written down too (see PREREGISTRATION.md
next to the artifacts directory).

ADDITIVE ONLY.  Nothing here edits, monkey-patches or re-trains anything.  The v3
world builder, question builder, exact interpreter and frozen panels are IMPORTED
read-only:

  V3.build_world, V3.render, V3.distinct_askers, V3.question_tokens, V3.true_chain,
  V3.sample_training_question, V3.interpret, V3.side_eligible, V3.load_panels,
  V3.CELLS, V3.CELL_ORDER, V3.HELDOUT_REL, V3.PRACTISED_RELS

SEQUENCE FORMAT
---------------
  story rows, flattened in layout order:   [3, ent, rel, val, filler.., 7] [3, ...] ...
  then the question:                       [4, ENT, op_1, .., op_k, 5]
  then the OUTPUT the model must write:    steps mode      e_1 .. e_{k-1} y END
                                           answer-only     y END

  * The ROW SEPARATOR is the grammar's existing NEWLINE token 7, which already
    terminates every rendered row.  No new separator id was needed.
  * END is a NEW id 68.  Ids 0..67 keep their exact meaning (0 = padding, 3 = WORLD,
    4 = QUESTION, 5 = ANSWER, 7 = NEWLINE, 8/9/10 = relations, 11 = LINK, 12..27 =
    values, 28..51 = fillers, 52..67 = entities).  Vocabulary is therefore 69.
  * Next-token cross entropy on the OUTPUT part only.  The position that predicts the
    first output token is the question's final ANSWER token.

POSITION VARIANTS (`--positions`)
---------------------------------
`--positions` selects a POSITIONAL PACKAGE: an attention mask together with the
position embeddings that go with it.  This is stated up front because the mask is
part of the variant, not a hidden constant:

  line      (PRIMARY)  story tokens attend only inside their own row (causally); the
                       question attends to every story token and causally to itself;
                       the output attends to everything before it.  Embeddings:
                       position-within-row, a segment embedding {story, question,
                       output}, and an output-step index.  This mirrors S's lookup
                       encoder, which encodes each line independently with
                       within-line positions and has NO inter-line order -- and it is
                       why this variant's logits are invariant to permuting story rows.
  absolute             ordinary full causal mask over the whole flat sequence, plus
                       ordinary learned absolute positions.  NOT row-permutation
                       invariant.  The table is sized for the longest panel sequence
                       (ABSOLUTE_SLOTS); 6-person TRAINING sequences only ever reach
                       ~325 positions while 16-person PANEL sequences reach ~591, so
                       roughly positions 325..590 of this table ARE NEVER TRAINED.
                       That is a real, stated handicap of this arm, not a bug.
  none                 full causal mask, no positional embedding at all.  The only
                       positional signal is the causal mask itself.  Also not
                       row-permutation invariant.

EFFICIENT, MATHEMATICALLY IDENTICAL EXECUTION
---------------------------------------------
In every variant the story precedes the question, so under a causal mask the story's
hidden states cannot depend on the question.  The story is therefore encoded ONCE per
world and its per-layer keys/values are shared by that world's questions.  Under the
`line` mask the story's rows are additionally independent of each other, so they are
encoded as a batch of short row-sequences.  Both are exact re-orderings of the same
computation, not approximations; `tests/test_fable_baseline_transformer.py` checks the
row-batched path against a dense-mask reference to 1e-5.

FLOP CONVENTION
---------------
`flops(...)` counts MATMULS ONLY -- the four attention projections, the two MLP
projections, the QK^T and AV products, and the output head -- at 2 FLOPs per
multiply-accumulate, times 3 for a training step (forward + backward).  Embedding
lookups, softmax, LayerNorm, indexing and the optimiser are excluded.  This is the
same convention as `premonition_token_memory.training_flops` (whose `48*n*d*d` term is
6 x (4d^2 + 4d^2) MACs per token), so the numbers are comparable with S.  Padded
positions are charged, because they are actually executed.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import json
import math
from pathlib import Path
import random
import sys
import time
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fable_dispatcher_v3 as V3                                            # noqa: E402

A = V3.A
V1 = V3.V1
torch = V3.torch
nn = V3.nn
F = torch.nn.functional

sha = V3.sha
write_new = V3.write_new
configure = V3.configure

QUESTION, ANSWER, WORLD, LINK = V3.QUESTION, V3.ANSWER, V3.WORLD, V3.LINK
NEWLINE = V3.NEWLINE
HELDOUT_REL, PRACTISED_RELS = V3.HELDOUT_REL, V3.PRACTISED_RELS

END = 68                       # NEW id: "I have finished writing my answer"
VOCAB = 69                     # 0..68
MAX_OUT = 12                   # hard cap on emitted output tokens; no END = failure

ROW_POS_SLOTS = 16             # longest rendered row is 10 tokens; longest question 11
SEGMENT_SLOTS = 3              # {story, question, output}
OUT_STEP_SLOTS = 16            # >= MAX_OUT
ABSOLUTE_SLOTS = 640           # longest panel sequence is 568 story + 11 question + 12 output

STORY, QSEG, OSEG = 0, 1, 2

TRAIN_NAMESPACE = 'fable-baseline-train'
TRAIN_PEOPLE = V3.TRAIN_PEOPLE
TRAIN_HOPS = V3.TRAIN_HOPS
QUESTIONS_PER_WORLD = V3.QUESTIONS_PER_WORLD
CELL_MARK = V3.CELL_MARK                       # 58/64, the report's display mark

TARGET_PARAMETERS = 79_316 + 15_522            # 94,838 -- S's total
PARAMETER_TOLERANCE = .03

PANEL_MANIFEST_SHA256 = '5c9b4507cf4197beccd933d2cb27b424cbbec13bdbb0f774d8b3bd9ca83867e7'

# width 48 / 3 layers / 4 heads / MLP hidden 208 gives 94,629 parameters for the
# primary `line` variant: 0.22% under S's 94,838.
WIDTH, LAYERS, HEADS, HIDDEN = 48, 3, 4, 208


# --------------------------------------------------------------------------- model


def _safe(mask):
    """Every query must see at least one key, or its softmax is NaN and the NaN then
    poisons padded keys that later rows multiply by a zero weight."""
    mask = mask.clone()
    mask[..., 0] |= ~mask.any(-1)
    return mask


class Block(nn.Module):
    """Pre-LN decoder block: masked attention over (memory ++ own), then a GELU MLP."""

    def __init__(self, width, heads, hidden):
        super().__init__()
        if width % heads:
            raise ValueError('width must be divisible by heads')
        self.width, self.heads, self.head_width = width, heads, width // heads
        self.norm1, self.norm2 = nn.LayerNorm(width), nn.LayerNorm(width)
        self.query = nn.Linear(width, width)
        self.key = nn.Linear(width, width)
        self.value = nn.Linear(width, width)
        self.output = nn.Linear(width, width)
        self.fc1 = nn.Linear(width, hidden)
        self.fc2 = nn.Linear(hidden, width)

    def split(self, x):
        return x.reshape(*x.shape[:-1], self.heads, self.head_width).transpose(-3, -2)

    def forward(self, x, mask, memory=None, *, trace=False):
        """x [B, N, d]; mask [B, N, M+N] over (memory keys ++ own keys)."""
        z = self.norm1(x)
        k, v = self.split(self.key(z)), self.split(self.value(z))
        keys, values = (k, v) if memory is None else \
            (torch.cat((memory[0], k), 2), torch.cat((memory[1], v), 2))
        q = self.split(self.query(z))
        scores = (q @ keys.transpose(-1, -2)) / math.sqrt(self.head_width)
        weights = scores.masked_fill(~mask[:, None], -torch.inf).softmax(-1)
        read = (weights @ values).transpose(1, 2).contiguous().reshape(x.shape)
        x = x + self.output(read)
        x = x + self.fc2(F.gelu(self.fc1(self.norm2(x))))
        return x, (k, v), (weights if trace else None)


class BaselineTransformer(nn.Module):
    def __init__(self, positions='line', vocab=VOCAB, width=WIDTH, layers=LAYERS,
                 heads=HEADS, hidden=HIDDEN):
        super().__init__()
        if positions not in ('line', 'absolute', 'none'):
            raise ValueError(f'unknown position variant {positions!r}')
        self.positions, self.vocab, self.width = positions, vocab, width
        self.layers, self.heads, self.hidden = layers, heads, hidden
        self.embedding = nn.Embedding(vocab, width, padding_idx=0)
        self.blocks = nn.ModuleList(Block(width, heads, hidden) for _ in range(layers))
        self.final_norm = nn.LayerNorm(width)
        self.output_bias = nn.Parameter(torch.zeros(vocab))          # tied embeddings
        if positions == 'line':
            self.row_position = nn.Embedding(ROW_POS_SLOTS, width)
            self.segment = nn.Embedding(SEGMENT_SLOTS, width)
            self.output_step = nn.Embedding(OUT_STEP_SLOTS, width)
        elif positions == 'absolute':
            self.absolute = nn.Embedding(ABSOLUTE_SLOTS, width)
        self.apply(self._initialize)
        with torch.no_grad():
            self.embedding.weight[0].zero_()
        self._causal = {}

    @staticmethod
    def _initialize(module):
        if isinstance(module, (nn.Linear, nn.Embedding)):
            nn.init.normal_(module.weight, std=.02)
            if isinstance(module, nn.Linear):
                nn.init.zeros_(module.bias)

    def parameters_count(self):
        return sum(p.numel() for p in self.parameters())

    def config(self):
        return dict(positions=self.positions, vocab=self.vocab, width=self.width,
                    layers=self.layers, heads=self.heads, hidden=self.hidden)

    def causal(self, n, device):
        key = (n, str(device))
        if key not in self._causal:
            self._causal[key] = torch.ones(n, n, dtype=torch.bool, device=device).tril()
        return self._causal[key]

    # ------------------------------------------------------------------ embeddings

    def embed_story(self, story):
        """`line`: the padded [W, R, T] row grid.  Otherwise the flat [W, S] story."""
        if self.positions == 'line':
            ids = story.rows
            x = self.embedding(ids)
            within = torch.arange(ids.shape[-1], device=ids.device).clamp(max=ROW_POS_SLOTS - 1)
            x = x + self.row_position(within) + self.segment.weight[STORY]
            return x * ids.ne(0)[..., None]
        ids = story.flat
        x = self.embedding(ids)
        if self.positions == 'absolute':
            index = torch.arange(ids.shape[1], device=ids.device).clamp(max=ABSOLUTE_SLOTS - 1)
            x = x + self.absolute(index)
        return x * story.flat_valid[..., None]

    def embed_stream(self, seq, seq_valid, q_len, story_len):
        """The question ++ output stream.  `q_len` [Q]; `story_len` [Q] per question."""
        index = torch.arange(seq.shape[1], device=seq.device)[None]
        is_output = index >= q_len[:, None]
        x = self.embedding(seq)
        if self.positions == 'line':
            within = index.clamp(max=ROW_POS_SLOTS - 1).expand_as(seq)
            x = x + self.row_position(within) * (~is_output)[..., None]
            x = x + self.segment(torch.where(is_output, OSEG, QSEG))
            step = (index - q_len[:, None]).clamp(0, OUT_STEP_SLOTS - 1)
            x = x + self.output_step(step) * is_output[..., None]
        elif self.positions == 'absolute':
            x = x + self.absolute((story_len[:, None] + index).clamp(max=ABSOLUTE_SLOTS - 1))
        return x * seq_valid[..., None]

    # ------------------------------------------------------------------ forward

    def encode_story(self, story):
        """Per-layer story keys/values in FLAT layout [W, H, S, hd], plus [W, S] validity.

        The story precedes the question under every variant's causal mask, so this is
        question-independent and is computed once per world.
        """
        if self.positions == 'line':
            w, rows, length = story.rows.shape
            ids = story.rows.reshape(w * rows, length)
            x = self.embed_story(story).reshape(w * rows, length, self.width)
            mask = _safe(self.causal(length, ids.device)[None] & ids.ne(0)[:, None, :])
            memory = []
            for block in self.blocks:
                x, kv, _ = block(x, mask)
                memory.append(tuple(story.compact(t, w, rows, length) for t in kv))
            return memory, story.flat_valid
        x = self.embed_story(story)
        mask = _safe(self.causal(x.shape[1], x.device)[None] & story.flat_valid[:, None, :])
        memory = []
        for block in self.blocks:
            x, kv, _ = block(x, mask)
            memory.append(kv)
        return memory, story.flat_valid

    def stream(self, seq, seq_valid, q_len, owner, memory, story_valid, story_len,
               *, trace=False):
        """Logits [Q, U, V] for the question ++ output stream."""
        q, u = seq.shape
        x = self.embed_stream(seq, seq_valid, q_len, story_len[owner])
        mem_mask = story_valid[owner][:, None, :].expand(q, u, story_valid.shape[1])
        own_mask = self.causal(u, seq.device)[None] & seq_valid[:, None, :]
        mask = _safe(torch.cat((mem_mask, own_mask), -1))
        weights = None
        for depth, block in enumerate(self.blocks):
            keys, values = memory[depth]
            last = trace and depth == len(self.blocks) - 1
            x, _, w = block(x, mask, (keys[owner], values[owner]), trace=last)
            if w is not None:
                weights = w
        x = self.final_norm(x)
        return F.linear(x, self.embedding.weight, self.output_bias), weights

    def forward(self, batch, *, trace=False):
        memory, story_valid = self.encode_story(batch.story)
        return self.stream(batch.seq, batch.seq_valid, batch.q_len, batch.owner, memory,
                           story_valid, batch.story.lens, trace=trace)

    # ------------------------------------------------------------------ decoding

    @torch.no_grad()
    def generate(self, story, owner, question, q_len, max_out=MAX_OUT):
        """Greedy decoding.  Returns the emitted tokens per row, truncated at the FIRST
        END (END included).  A row that never emits END keeps all `max_out` tokens and
        is scored as a failure by `evaluate_side`."""
        memory, story_valid = self.encode_story(story)
        n, width = question.shape
        seq = torch.cat((question, torch.zeros(n, max_out, dtype=torch.long)), 1)
        seq_valid = torch.arange(width + max_out)[None] < q_len[:, None]
        rows = torch.arange(n)
        finished = torch.zeros(n, dtype=torch.bool)
        emitted = torch.zeros(n, max_out, dtype=torch.long)
        steps = 0
        for step in range(max_out):
            used = width + step + 1
            logits, _ = self.stream(seq[:, :used], seq_valid[:, :used], q_len, owner, memory,
                                    story_valid, story.lens)
            nxt = logits[rows, q_len + step - 1].argmax(-1)
            seq[rows, q_len + step] = nxt
            seq_valid[rows, q_len + step] = True
            emitted[:, step] = nxt
            steps = step + 1
            finished |= nxt.eq(END)
            if bool(finished.all()):
                break
        out = []
        for i in range(n):
            row = [int(t) for t in emitted[i, :steps]]
            out.append(row[:row.index(END) + 1] if END in row else row)
        return out

    # ------------------------------------------------------------------ flops

    def _per_token_linear(self):
        return 4 * self.width * self.width + 2 * self.width * self.hidden

    def story_flops(self, story, *, backward):
        """Matmul MACs x 2 (x3 more with a backward pass) for encoding the story once."""
        w, rows, length = story.rows.shape
        if self.positions == 'line':
            tokens, span = w * rows * length, length
        else:
            tokens, span = w * story.flat.shape[1], story.flat.shape[1]
        macs = self.layers * tokens * (self._per_token_linear() + 2 * span * self.width)
        return (6 if backward else 2) * macs

    def stream_flops(self, story_width, questions, width, *, backward):
        """Cost of one pass of the question ++ output stream against a cached story."""
        macs = self.layers * questions * width * (
            self._per_token_linear() + 2 * (story_width + width) * self.width)
        macs += questions * width * self.width * self.vocab
        return (6 if backward else 2) * macs

    def flops(self, story, seq_shape, *, backward):
        """Matmul-only FLOPs for one teacher-forced pass over this batch."""
        questions, width = seq_shape
        return self.story_flops(story, backward=backward) + \
            self.stream_flops(story.flat.shape[1], questions, width, backward=backward)


# --------------------------------------------------------------------------- packing


@dataclass
class Story:
    rows: torch.Tensor                    # [W, R, T] padded row grid, 0 = pad
    flat: torch.Tensor                    # [W, S] the same tokens, rows concatenated
    flat_row: torch.Tensor                # [W, S] which row each flat token came from
    flat_valid: torch.Tensor              # [W, S] bool
    lens: torch.Tensor                    # [W] real story tokens
    source: torch.Tensor                  # [W, S] index into the flattened row grid

    def compact(self, tensor, w, rows, length):
        """[W*R, H, T, hd] row-major keys/values -> [W, H, S, hd] flat-layout ones."""
        heads, head_width = tensor.shape[1], tensor.shape[3]
        x = tensor.transpose(1, 2).reshape(w, rows * length, heads, head_width)
        index = self.source[..., None, None].expand(w, self.flat.shape[1], heads, head_width)
        return x.gather(1, index).transpose(1, 2)


def pack_stories(stories):
    w = len(stories)
    rows_n = max(len(s) for s in stories)
    length = max(max(len(r) for r in s) for s in stories)
    rows = torch.zeros(w, rows_n, length, dtype=torch.long)
    for i, story in enumerate(stories):
        for j, row in enumerate(story):
            rows[i, j, :len(row)] = torch.tensor(row, dtype=torch.long)
    grid = rows.reshape(w, rows_n * length)
    real = grid.ne(0)
    size = max(1, int(real.sum(1).max()))
    rank = real.long().cumsum(1) - 1
    owner = torch.arange(w)[:, None].expand_as(real)
    source = torch.zeros(w, size, dtype=torch.long)
    flat_row = torch.zeros(w, size, dtype=torch.long)
    position = torch.arange(rows_n * length)[None].expand_as(real)
    source[owner[real], rank[real]] = position[real]
    flat_row[owner[real], rank[real]] = (position // length)[real]
    lens = real.sum(1)
    valid = torch.arange(size)[None] < lens[:, None]
    flat = grid.gather(1, source) * valid
    return Story(rows=rows, flat=flat, flat_row=flat_row * valid, flat_valid=valid,
                 lens=lens, source=source)


def output_tokens(chain, mode):
    if mode == 'steps':
        return [int(step[2]) for step in chain] + [END]
    if mode == 'answer-only':
        return [int(chain[-1][2]), END]
    raise ValueError(f'unknown mode {mode!r}')


@dataclass
class Batch:
    story: Story
    owner: torch.Tensor
    seq: torch.Tensor
    seq_valid: torch.Tensor
    q_len: torch.Tensor
    target: torch.Tensor
    questions: list = field(default_factory=list)
    outputs: list = field(default_factory=list)
    support: torch.Tensor = None          # [Q, MAX_OUT] flat row index, -1 where none


def pack_batch(stories, items, mode, *, support=False):
    """`items`: dicts with owner, question, chain.  Teacher-forced sequence and targets."""
    story = pack_stories(stories)
    questions = [list(it['question']) for it in items]
    outputs = [output_tokens(it['chain'], mode) for it in items]
    q_len = torch.tensor([len(q) for q in questions], dtype=torch.long)
    width = max(len(q) + len(o) for q, o in zip(questions, outputs))
    seq = torch.zeros(len(items), width, dtype=torch.long)
    target = torch.full((len(items), width), -100, dtype=torch.long)
    for i, (q, o) in enumerate(zip(questions, outputs)):
        whole = q + o
        seq[i, :len(whole)] = torch.tensor(whole, dtype=torch.long)
        # position len(q)-1 (the ANSWER token) predicts o[0]; position len(q)-1+j predicts o[j]
        for j, token in enumerate(o):
            target[i, len(q) - 1 + j] = token
    seq_valid = seq.ne(0)
    rows = None
    if support:
        rows = torch.full((len(items), MAX_OUT), -1, dtype=torch.long)
        for i, it in enumerate(items):
            for j, index in enumerate(it.get('support', [])[:MAX_OUT]):
                rows[i, j] = index
    return Batch(story=story, owner=torch.tensor([it['owner'] for it in items], dtype=torch.long),
                 seq=seq, seq_valid=seq_valid, q_len=q_len, target=target,
                 questions=questions, outputs=outputs, support=rows)


# --------------------------------------------------------------------------- training stream


def support_rows(rows, chain):
    """For each chain step, the index of the visible row that licenses it."""
    out = []
    for subject, op, result in chain:
        found = -1
        for index, row in enumerate(rows):
            if len(row) >= 4 and row[0] == WORLD and row[1] == subject and row[2] == op \
                    and row[3] == result:
                found = index
                break
        out.append(found)
    return out


def training_items(rng, visits=16, people=TRAIN_PEOPLE, hops_choices=TRAIN_HOPS,
                   forbidden=frozenset(), questions_per_world=QUESTIONS_PER_WORLD,
                   support=False):
    """`visits` worlds x `questions_per_world` questions, EXACTLY S's training regime.

    Hop count uniform over `hops_choices` (drawn once per question), terminal relation
    uniform over {8, 9, 10} at one hop and {8, 9} at k >= 2 (so relation 10 is never the
    terminal relation of a multi-hop training question -- asserted inside
    `V3.sample_training_question` and again here), chains pairwise distinct at k >= 2,
    and every question's visible semantics checked against the panels' forbidden set.
    """
    hops_choices = list(hops_choices)
    if any(h < 1 for h in hops_choices):
        raise ValueError('hop counts must be >= 1')
    if max(hops_choices) > people:
        raise ValueError('a pairwise-distinct k-chain needs at least k people')
    stories, items = [], []
    for v in range(visits):
        for _attempt in range(256):
            world = V3.build_world(rng, people)
            asked, drawn = set(), []
            for _ in range(questions_per_world):
                hops = rng.choice(hops_choices)
                placed = False
                for _try in range(64):
                    made = V3.sample_training_question(rng, world, hops)
                    if made is None:
                        break
                    asker, terminal = made
                    if (hops, asker, terminal) in asked:
                        continue
                    asked.add((hops, asker, terminal))
                    drawn.append((hops, asker, terminal))
                    placed = True
                    break
                if not placed:
                    break
            if len(drawn) == questions_per_world:
                break
        else:
            raise RuntimeError('could not draw a usable training world')
        rows = V3.render(world)
        stories.append(rows)
        for hops, asker, terminal in drawn:
            assert not (hops >= 2 and terminal == HELDOUT_REL), \
                'relation 10 must never be the terminal relation of a multi-hop training question'
            question = V3.question_tokens(asker, hops, terminal)
            chain, chain_people = V3.true_chain(world, asker, hops, terminal)
            if hops >= 2:
                assert len(set(chain_people)) == hops, 'multi-hop training chains must be distinct'
            if forbidden and A.visible_signature(rows, question) in forbidden:
                raise RuntimeError('training/panel semantic overlap; run invalid')
            item = dict(owner=v, question=question, chain=chain, hops=hops, terminal=terminal,
                        answer=chain[-1][2])
            if support:
                item['support'] = support_rows(rows, chain)
            items.append(item)
    rng.randrange(1 << 30)
    return stories, items


# --------------------------------------------------------------------------- losses


def teacher_forced_loss(model, batch, *, evidence_aux=0.):
    logits, weights = model(batch, trace=bool(evidence_aux))
    flat_logits = logits.reshape(-1, logits.shape[-1])
    flat_target = batch.target.reshape(-1)
    loss = F.cross_entropy(flat_logits, flat_target, ignore_index=-100)
    scored = flat_target.ne(-100)
    hits = (flat_logits.argmax(-1) == flat_target) & scored
    token_accuracy = hits.sum().float() / scored.sum().clamp(min=1)
    per_row = ((logits.argmax(-1) == batch.target) | batch.target.eq(-100)).all(-1)
    aux = torch.zeros((), dtype=loss.dtype)
    if evidence_aux:
        aux = evidence_loss(batch, weights)
        loss = loss + evidence_aux * aux
    return loss, float(token_accuracy), float(per_row.float().mean()), float(aux.detach())


def evidence_loss(batch, weights):
    """OPTIONAL, default OFF.  Push the last layer's head-mean attention from each
    output-predicting position onto the tokens of the gold supporting row.

    This is the baseline's counterpart to the supporting-line attention supervision
    S's LOOKUP training received; it is NOT used by any registered arm here.
    """
    if batch.support is None:
        raise ValueError('pack_batch(..., support=True) is required for the evidence loss')
    story_width = batch.story.flat.shape[1]
    attention = weights.mean(1)[:, :, :story_width]            # [Q, U, S] head mean over story
    row_of = batch.story.flat_row[batch.owner]                 # [Q, S]
    valid = batch.story.flat_valid[batch.owner]
    terms = []
    for step in range(batch.support.shape[1]):
        rows = batch.support[:, step]
        live = rows.ge(0)
        if not bool(live.any()):
            continue
        at = (batch.q_len + step - 1).clamp(0, attention.shape[1] - 1)
        got = attention[torch.arange(attention.shape[0]), at]
        mass = (got * (row_of == rows[:, None]) * valid).sum(-1)
        terms.append(-(mass[live].clamp(min=1e-9)).log())
    if not terms:
        return torch.zeros((), dtype=attention.dtype)
    return torch.cat(terms).mean()


def learning_rate(base, update, updates, warmup=100, final=1e-4):
    """Warmup to `base`, then flat, then linear decay to `final` over the last third."""
    scale = min(1., (update + 1) / max(1, warmup))
    start = (2 * updates) // 3
    if update >= start and updates > start:
        span = max(1, updates - start)
        scale = scale * (1. - (1. - final / base) * (update - start) / span)
    return base * scale


# --------------------------------------------------------------------------- train


def train(args):
    configure()
    out = Path(args.out)
    if out.exists():
        raise SystemExit(f'refusing to overwrite an existing run directory: {out}')
    out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    record = dict(baseline='fable-baseline-transformer', mode=args.mode, positions=args.positions,
                  seed=args.seed, updates_requested=args.updates, visits_per_update=args.visits,
                  questions_per_world=args.questions_per_world,
                  train_hops=list(TRAIN_HOPS), train_people=args.train_people,
                  lr=args.lr, lr_final=args.lr_final, warmup=args.warmup, clip=args.clip,
                  weight_decay=args.weight_decay, betas=[.9, .99], dropout=0.,
                  evidence_aux=float(args.evidence_aux), time_cap=args.time_cap,
                  panels=args.panels, end_token=END, vocab=VOCAB, max_output_tokens=MAX_OUT,
                  registered_test=bool(args.seed in (0, 1, 2)),
                  source_sha256=sha(__file__), v3_source_sha256=sha(V3.__file__),
                  supervision_note=(
                      'steps mode receives the gold intermediate entities as output targets -- '
                      'the same intermediate labels S\'s lookup training used.  It does NOT '
                      'receive supporting-line attention supervision (S\'s lookup did) unless '
                      '--evidence-aux is passed, which no registered arm does.'))
    updates_done, log = 0, None
    try:
        forbidden = frozenset()
        if args.panels:
            _, _, forbidden = V3.load_panels(args.panels)
        torch.manual_seed(args.seed)
        model = BaselineTransformer(positions=args.positions, width=args.width,
                                    layers=args.layers, heads=args.heads, hidden=args.hidden)
        total = model.parameters_count()
        record.update(parameters=total, parameter_target=TARGET_PARAMETERS,
                      parameter_ratio=total / TARGET_PARAMETERS, config=model.config())
        print(json.dumps(dict(event='start', mode=args.mode, positions=args.positions,
                              seed=args.seed, parameters=total,
                              parameter_ratio=round(total / TARGET_PARAMETERS, 4))), flush=True)
        optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, betas=(.9, .99), eps=1e-8,
                                      weight_decay=args.weight_decay)
        rng = random.Random(f'{TRAIN_NAMESPACE}:{args.seed}')
        log = (out / 'train_log.jsonl').open('x')
        window = dict(loss=0., token=0., row=0., aux=0., updates=0)
        flops, capped, padded_tokens, real_tokens = 0., False, 0, 0
        for update in range(args.updates):
            if time.monotonic() - started >= args.time_cap:
                capped = True
                break
            for group in optimizer.param_groups:
                group['lr'] = learning_rate(args.lr, update, args.updates, args.warmup,
                                            args.lr_final)
            stories, items = training_items(rng, args.visits, args.train_people, TRAIN_HOPS,
                                            forbidden, args.questions_per_world,
                                            support=bool(args.evidence_aux))
            batch = pack_batch(stories, items, args.mode, support=bool(args.evidence_aux))
            flops += model.flops(batch.story, tuple(batch.seq.shape), backward=True)
            padded_tokens += (batch.story.rows.numel() if args.positions == 'line'
                              else batch.story.flat.numel())
            real_tokens += int(batch.story.lens.sum())
            loss, token, row, aux = teacher_forced_loss(model, batch,
                                                        evidence_aux=float(args.evidence_aux))
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            norm = torch.nn.utils.clip_grad_norm_(model.parameters(), args.clip)
            if not bool(torch.isfinite(loss)) or not bool(torch.isfinite(norm)):
                raise RuntimeError('nonfinite baseline loss or gradient')
            optimizer.step()
            updates_done += 1
            window['updates'] += 1
            window['loss'] += float(loss.detach())
            window['token'] += token
            window['row'] += row
            window['aux'] += aux
            if updates_done % args.log_every == 0 or updates_done == 1:
                n = window['updates']
                line = dict(update=updates_done, loss=window['loss'] / n,
                            token_accuracy=window['token'] / n,
                            sequence_accuracy=window['row'] / n, evidence=window['aux'] / n,
                            seconds=time.monotonic() - started, flops=flops,
                            lr=optimizer.param_groups[0]['lr'])
                log.write(json.dumps(line) + '\n')
                log.flush()
                print(json.dumps(dict(seed=args.seed, mode=args.mode, **line)), flush=True)
                window = dict(loss=0., token=0., row=0., aux=0., updates=0)
        log.close()
        log = None
        checkpoint = out / 'baseline.pt'
        torch.save(dict(state_dict=model.state_dict(), config=model.config(), mode=args.mode,
                        seed=args.seed, updates=updates_done), checkpoint)
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
                      checkpoint=str(checkpoint), checkpoint_sha256=sha(checkpoint),
                      complete=not capped, time_capped=capped, final_update_only=True,
                      no_resume=True, no_checkpoint_selection=True)
        write_new(out / ('failure.json' if capped else 'training.json'), record)
        print(json.dumps(dict(event='done', seed=args.seed, updates=updates_done,
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


# --------------------------------------------------------------------------- scoring


def side_items(units, side):
    """The visible rows, question and truth chain of one side of a panel cell."""
    stories, items = [], []
    for index, unit in enumerate(units):
        one = unit[side]
        rows = [row for position, row in enumerate(one['memory'])
                if row and position < one['where']]
        stories.append(rows)
        items.append(dict(owner=index, question=list(one['question']), chain=one['chain'],
                          answer=one['answer'], hops=one['hops']))
    return stories, items


def evaluate_side(items, emissions, mode):
    """Answer / strict-path scoring of one side from the emitted tokens alone."""
    out = []
    for item, emitted in zip(items, emissions):
        ended = bool(emitted) and emitted[-1] == END and len(emitted) >= 2
        answer = emitted[-2] if ended else None
        truth = output_tokens(item['chain'], mode)
        strict = int(ended and list(emitted) == truth)
        out.append(dict(emitted=list(emitted), end_emitted=int(ended),
                        answer=(None if answer is None else int(answer)),
                        target=int(item['answer']),
                        correct=int(ended and answer == item['answer']),
                        strict_path=strict, hops=item['hops'],
                        output_tokens=len(emitted)))
    return out


def aggregate(per_side, n, cfg):
    """Mirrors `fable_dispatcher_v3.aggregate`: pair cells need BOTH twins."""
    sides = list(per_side)
    both = [all(per_side[s][i]['correct'] for s in sides) for i in range(n)]
    identical = [len({per_side[s][i]['answer'] for s in sides}) == 1 for i in range(n)]
    rows = [r for s in sides for r in per_side[s]]
    return dict(
        answers=sum(both),
        strict=sum(all(per_side[s][i]['strict_path'] for s in sides) for i in range(n)),
        identical_twin_answers=sum(identical),
        unit_pass=sum(c and (i or not cfg['invariant']) for c, i in zip(both, identical)),
        no_end=sum(1 - r['end_emitted'] for r in rows),
        rows=len(rows),
        mean_output_tokens=sum(r['output_tokens'] for r in rows) / max(1, len(rows)))


def model_emitter(model, block=32):
    @torch.no_grad()
    def emit(stories, items):
        out = []
        for start in range(0, len(items), block):
            chunk = items[start:start + block]
            index = sorted({it['owner'] for it in chunk})
            remap = {o: i for i, o in enumerate(index)}
            story = pack_stories([stories[o] for o in index])
            owner = torch.tensor([remap[it['owner']] for it in chunk], dtype=torch.long)
            width = max(len(it['question']) for it in chunk)
            question = torch.zeros(len(chunk), width, dtype=torch.long)
            for i, it in enumerate(chunk):
                question[i, :len(it['question'])] = torch.tensor(it['question'], dtype=torch.long)
            q_len = torch.tensor([len(it['question']) for it in chunk], dtype=torch.long)
            out.extend(model.generate(story, owner, question, q_len))
        return out
    return emit


def oracle_emitter(mode):
    """A hand-built emitter that writes the truth chain.  Used ONLY by the test that
    checks the scorer can award 64/64 -- never by a scored run."""
    def emit(stories, items):
        return [output_tokens(it['chain'], mode) for it in items]
    return emit


def score_panels(emit, panels, mode, cells=None):
    cells = cells or V3.CELL_ORDER
    summary, transcripts = {}, {}
    for cell in cells:
        cfg = V3.CELLS[cell]
        units = panels[cell]['units']
        sides = ['a'] + (['b'] if cfg['kind'] == 'pair' else [])
        per_side = {}
        for side in sides:
            stories, items = side_items(units, side)
            per_side[side] = evaluate_side(items, emit(stories, items), mode)
        summary[cell] = dict(n=len(units), sides=len(sides), hops=cfg['hops'],
                             people=cfg['people'], terminal=cfg['terminal'], kind=cfg['kind'],
                             title=cfg['title'], **aggregate(per_side, len(units), cfg))
        transcripts[cell] = per_side
    return summary, transcripts


def inference_flops(model, panels, block=32, cells=None):
    """Greedy scoring cost, charged at the worst case of MAX_OUT decode steps per unit:
    one story encode per block, then MAX_OUT stream passes of growing width."""
    total = 0.
    for cell in (cells or V3.CELL_ORDER):
        cfg = V3.CELLS[cell]
        units = panels[cell]['units']
        for side in ['a'] + (['b'] if cfg['kind'] == 'pair' else []):
            stories, items = side_items(units, side)
            for start in range(0, len(items), block):
                chunk = items[start:start + block]
                story = pack_stories(stories[start:start + block])
                width = max(len(it['question']) for it in chunk)
                total += model.story_flops(story, backward=False)
                for step in range(MAX_OUT):
                    total += model.stream_flops(story.flat.shape[1], len(chunk), width + step,
                                                backward=False)
    return total


def score(args):
    configure()
    run = Path(args.run)
    config_path = run / 'training.json'
    if not config_path.exists():
        config_path = run / 'failure.json'
    if not config_path.exists():
        raise SystemExit(f'no training.json or failure.json in {run}')
    config = json.loads(config_path.read_text())
    checkpoint = run / 'baseline.pt'
    if not checkpoint.exists():
        raise SystemExit(f'no baseline checkpoint in {run}')
    saved = torch.load(checkpoint, map_location='cpu', weights_only=False)
    model = BaselineTransformer(**saved['config'])
    model.load_state_dict(saved['state_dict'], strict=True)
    model.eval()
    manifest_sha = sha(Path(args.panels) / 'manifest.json')
    if not args.allow_other_panels and manifest_sha != PANEL_MANIFEST_SHA256:
        raise SystemExit(f'panel manifest sha256 {manifest_sha} is not the registered '
                         f'{PANEL_MANIFEST_SHA256}')
    manifest, panels, _ = V3.load_panels(args.panels)
    out = Path(args.score_out) if args.score_out else run / 'score'
    out.mkdir(parents=True, exist_ok=False)
    mode = saved['mode']
    started = time.monotonic()
    summary, transcripts = score_panels(model_emitter(model, args.block), panels, mode)
    seconds = time.monotonic() - started
    for cell in V3.CELL_ORDER:
        row = summary[cell]
        print(json.dumps(dict(cell=cell, hops=row['hops'], answers=row['answers'],
                              strict=row['strict'], no_end=row['no_end'])), flush=True)
    write_new(out / 'scores.json',
              dict(baseline='fable-baseline-transformer', run=str(run), mode=mode,
                   positions=saved['config']['positions'], seed=config.get('seed'),
                   registered_test=config.get('registered_test'),
                   parameters=model.parameters_count(), parameter_target=TARGET_PARAMETERS,
                   updates=config.get('updates'), time_capped=config.get('time_capped'),
                   training_flops=config.get('training_flops'),
                   training_seconds=config.get('seconds'),
                   inference_flops=inference_flops(model, panels, args.block),
                   scoring_seconds=seconds,
                   panels=str(Path(args.panels).resolve()), panel_manifest_sha256=manifest_sha,
                   panel_manifest_is_registered=bool(manifest_sha == PANEL_MANIFEST_SHA256),
                   evaluation='greedy (argmax) decoding, final checkpoint only',
                   answer='the token emitted immediately before END; no END is a failure',
                   strict_path=('every emitted token equals the truth chain\'s results and END '
                                'is emitted immediately after the answer'),
                   mark=CELL_MARK, cell_order=V3.CELL_ORDER, cells=summary,
                   operator_audit=manifest['operator_audit'],
                   source_sha256=sha(__file__), v3_source_sha256=sha(V3.__file__),
                   created_unix=time.time()))
    write_new(out / 'transcripts.json', transcripts)
    return summary


# --------------------------------------------------------------------------- CLI


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)

    p = sub.add_parser('train')
    p.add_argument('--mode', choices=('steps', 'answer-only'), default='steps')
    p.add_argument('--positions', choices=('line', 'absolute', 'none'), default='line')
    p.add_argument('--seed', type=int, required=True)
    p.add_argument('--updates', type=int, default=6000)
    p.add_argument('--out', required=True)
    p.add_argument('--time-cap', type=float, default=1700)
    p.add_argument('--panels', default=None,
                   help='panel directory whose visible semantics the training stream must avoid')
    p.add_argument('--visits', type=int, default=16)
    p.add_argument('--questions-per-world', type=int, default=QUESTIONS_PER_WORLD)
    p.add_argument('--train-people', type=int, default=TRAIN_PEOPLE)
    p.add_argument('--width', type=int, default=WIDTH)
    p.add_argument('--layers', type=int, default=LAYERS)
    p.add_argument('--heads', type=int, default=HEADS)
    p.add_argument('--hidden', type=int, default=HIDDEN)
    p.add_argument('--lr', type=float, default=1e-3)
    p.add_argument('--lr-final', type=float, default=1e-4)
    p.add_argument('--warmup', type=int, default=100)
    p.add_argument('--clip', type=float, default=1.0)
    p.add_argument('--weight-decay', type=float, default=.1)
    p.add_argument('--evidence-aux', type=float, default=0.,
                   help='OFF by default; 0.5 turns on the supporting-line attention loss')
    p.add_argument('--log-every', type=int, default=100)

    p = sub.add_parser('score')
    p.add_argument('--run', required=True)
    p.add_argument('--panels', required=True)
    p.add_argument('--score-out', default=None)
    p.add_argument('--block', type=int, default=32)
    p.add_argument('--allow-other-panels', action='store_true',
                   help='dev only: score panels whose manifest is not the registered one')

    args = parser.parse_args(argv)
    if args.command == 'train':
        train(args)
    else:
        score(args)


if __name__ == '__main__':
    main()
