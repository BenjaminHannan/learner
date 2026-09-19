"""Milestone 2 (reviews/opus-execution-02-answer-path.md): reproduce and localise D's answer-path failure on the
far-fact toy, then test the two bounded adjustments. CPU only; no rental; hard 30-minute training ledger.

Every subcommand imports `premonition` / `learnlab` from the frozen snapshot (--frozen, verified against its
FROZEN.SHA256SUMS before import), so all arms use the same source. The toy's synthetic vocabulary is a
diagnostic exception to the v2-tokenizer rule (no village data is used here).

    PY -B scripts/premonition_m02_answer_path.py --run m02-... data
    PY -B scripts/premonition_m02_answer_path.py --run m02-... audit
    PY -B scripts/premonition_m02_answer_path.py --run m02-... train --arm D --spec v16 --loops 2 --steps 600
    PY -B scripts/premonition_m02_answer_path.py --run m02-... probe --ckpt <name>
"""
from __future__ import annotations

import argparse
import contextlib
from dataclasses import asdict, fields
import hashlib
import json
import math
from pathlib import Path
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
CAP_SECONDS = 30 * 60
VISITS = 16
SEEDS = {"v16": {"train": 101, "validation": 202, "test": 303, "probe": 404, "paired": 505},
         "v4": {"train": 111, "validation": 212, "test": 313, "probe": 414, "paired": 515}}
EVAL_BATCHES = {"validation": 16, "test": 16, "probe": 16}
TRAIN_BATCHES = 3000
BISECT = ("nothink-oracle", "nothink-writer", "think1-oracle", "think1-writer")
ARMS = ("D",) + BISECT + ("D-think-gated", "D-card-bypass", "D-noask", "D-card-bypass+distractors")


# ----------------------------------------------------------------------------- frozen source
def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bootstrap(run: str) -> Path:
    archive = ROOT / "archive" / f"opus-{run}"
    frozen = archive / "frozen"
    bad = []
    for line in (archive / "FROZEN.SHA256SUMS").read_text().splitlines():
        digest, name = line.split(None, 1)
        if sha256(frozen / name) != digest:
            bad.append(name)
    if bad:
        raise SystemExit(f"frozen source changed: {bad}")
    sys.path.insert(0, str(frozen))
    import premonition
    if not Path(premonition.__file__).resolve().is_relative_to(frozen.resolve()):
        raise SystemExit(f"premonition imported from {premonition.__file__}, not the frozen snapshot")
    return archive


def out_dir(run: str) -> Path:
    path = ROOT / "artifacts" / f"opus-{run}"
    path.mkdir(parents=True, exist_ok=True)
    return path


# ----------------------------------------------------------------------------- ledger
def ledger_seconds(run: str) -> float:
    path = out_dir(run) / "ledger.jsonl"
    if not path.exists():
        return 0.0
    return sum(json.loads(line)["seconds"] for line in path.read_text().splitlines() if line.strip())


def ledger_add(run: str, entry: dict) -> None:
    with (out_dir(run) / "ledger.jsonl").open("a") as handle:
        handle.write(json.dumps(entry) + "\n")


# ----------------------------------------------------------------------------- data
def spec_of(name: str):
    from premonition.toy import ToySpec
    return {"v16": ToySpec(), "v4": ToySpec(values=4)}[name]


def batch_digest(batch) -> str:
    from learnlab.readonly import tensor_digest
    import torch
    digest = hashlib.sha256()
    for item in fields(batch):
        value = getattr(batch, item.name)
        if isinstance(value, torch.Tensor):
            digest.update(item.name.encode() + tensor_digest(value).encode())
    return digest.hexdigest()


def visit_prints(batch) -> list[str]:
    out = []
    for row in range(batch.tokens.shape[0]):
        length = int(batch.lengths[row])
        out.append(hashlib.sha1(batch.tokens[row, :length].numpy().tobytes()).hexdigest())
    return out


def train_stream(spec_name: str):
    from premonition.toy import toy_stream
    from premonition.train import label_free
    return (label_free(b) for b in toy_stream(spec_of(spec_name), VISITS, SEEDS[spec_name]["train"]))


def held_out(spec_name: str, split: str):
    from premonition.toy import toy_set
    from premonition.train import label_free
    return [label_free(b) for b in toy_set(spec_of(spec_name), EVAL_BATCHES[split], VISITS, SEEDS[spec_name][split])]


def cmd_data(args) -> None:
    import torch
    out = out_dir(args.run) / "data"
    out.mkdir(exist_ok=True)
    manifest = {"visits_per_batch": VISITS, "seeds": SEEDS, "label_free": "premonition.train.label_free (legacy "
                "toy rule: answer/feedback spans removed from the reader stream)",
                "vocabulary": "toy synthetic ids (diagnostic exception to the v2 tokenizer rule)", "specs": {}}
    for spec_name in SEEDS:
        spec = spec_of(spec_name)
        entry = {"spec": asdict(spec), "vocab_size": spec.vocab_size, "chance": spec.chance, "splits": {}}
        prints: dict[str, set] = {}
        for split in EVAL_BATCHES:
            batches = held_out(spec_name, split)
            path = out / f"{spec_name}-{split}.pt"
            torch.save(batches, path)
            prints[split] = {p for b in batches for p in visit_prints(b)}
            entry["splits"][split] = {"seed": SEEDS[spec_name][split], "batches": len(batches),
                                      "visits": sum(b.tokens.shape[0] for b in batches),
                                      "questions": sum(b.q_visit.shape[0] for b in batches),
                                      "file": str(path.relative_to(ROOT)), "sha256": sha256(path),
                                      "batch_digests": [batch_digest(b) for b in batches]}
        stream = train_stream(spec_name)
        digests, train_prints = [], set()
        for _ in range(TRAIN_BATCHES):
            batch = next(stream)
            digests.append(batch_digest(batch))
            train_prints.update(visit_prints(batch))
        prints["train"] = train_prints
        entry["splits"]["train"] = {"seed": SEEDS[spec_name]["train"], "batches_digested": TRAIN_BATCHES,
                                    "visits": TRAIN_BATCHES * VISITS, "regenerated_from_seed": True,
                                    "digest_of_batch_digests": hashlib.sha256("".join(digests).encode()).hexdigest()}
        (out / f"{spec_name}-train-digests.json").write_text(json.dumps(digests))
        names = sorted(prints)
        entry["overlap_visits"] = {f"{a}&{b}": len(prints[a] & prints[b])
                                   for i, a in enumerate(names) for b in names[i + 1:]}
        entry["duplicate_train_visits"] = TRAIN_BATCHES * VISITS - len(train_prints)
        manifest["specs"][spec_name] = entry
        print(spec_name, json.dumps(entry["overlap_visits"]), "dup train", entry["duplicate_train_visits"], flush=True)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print("manifest", sha256(out / "manifest.json"))


def load_split(run: str, spec_name: str, split: str):
    import torch
    manifest = json.loads((out_dir(run) / "data" / "manifest.json").read_text())
    info = manifest["specs"][spec_name]["splits"][split]
    path = ROOT / info["file"]
    if sha256(path) != info["sha256"]:
        raise SystemExit(f"{path} changed since the data freeze")
    return torch.load(path, weights_only=False)


def checked_train(run: str, spec_name: str):
    """The train stream, each batch checked against the frozen digest list."""
    digests = json.loads((out_dir(run) / "data" / f"{spec_name}-train-digests.json").read_text())
    for i, batch in enumerate(train_stream(spec_name)):
        if i < len(digests) and batch_digest(batch) != digests[i]:
            raise SystemExit(f"train batch {i} differs from the frozen digest")
        yield batch


# ----------------------------------------------------------------------------- model helpers
def build(arm: str, spec_name: str, seed: int, overrides: dict | None = None):
    """Baseline D (seed-initialised) or a variant copied from it: shared weights always start identical."""
    import torch
    from premonition import answer_path
    from premonition.config import MiniConfig
    from premonition.model import PremonitionMini
    variant = "D-noask" if arm == "D-noask" else "D"
    config = MiniConfig.preset(variant, "tiny", vocab_size=spec_of(spec_name).vocab_size, window=64,
                               **(overrides or {}))
    torch.manual_seed(seed)
    base = PremonitionMini(config)
    arm = arm.split("+")[0]
    if arm in answer_path.ADJUSTMENTS:
        return answer_path.from_base(arm, base)
    return base


def gold_preload(model, store, batch, episode) -> None:
    """Exactly `forward(mode="gold")`'s preload: every gold card before loop 1."""
    import torch
    count = batch.q_visit.shape[0]
    gold, _, missing = store.gold(batch.gold_lines, batch.q_visit, batch.q_line)
    if int(missing.sum()):
        raise RuntimeError("gold card missing")
    width = min(gold.shape[1], batch.gold_lines.shape[1] + 1, model.config.card_rows)
    preload = torch.where(gold, torch.arange(gold.shape[1]),
                          torch.full_like(gold, -1, dtype=torch.long)).topk(width, 1).values
    model._insert(episode, store, torch.arange(count), preload)


def distractor_preload(model, store, batch, episode, distractors: int, generator) -> "torch.Tensor":
    """Gold card plus `distractors` other eligible fact cards of the same visit (teacher-mode-like card sets), in a
    random order; returns [Q, 1 + distractors] (the inserted card indices, -1 = none) and inserts them."""
    import torch
    count = batch.q_visit.shape[0]
    gold, _, _ = store.gold(batch.gold_lines, batch.q_visit, batch.q_line)
    pool = store.eligible(batch.q_visit, batch.q_line) & ~gold
    pool[:, store.null] = False
    noise = torch.rand(pool.shape, generator=generator).masked_fill(~pool, -1.0)
    best, extra = noise.topk(distractors, 1)
    extra = extra.masked_fill(best < 0, -1)
    cards = torch.cat([batch.gold_lines[:, :1], extra], dim=1)
    order = torch.rand(cards.shape, generator=generator).argsort(1)
    cards = cards.gather(1, order)
    model._insert(episode, store, torch.arange(count), cards)
    return cards


def oracle_store(model, store, batch):
    """The store with each question's gold card value replaced by the answer's (tied) embedding: a clean card."""
    from dataclasses import replace
    values = store.values.index_put((batch.q_visit, batch.gold_lines[:, 0]),
                                    model.embed.weight[batch.answer[:, 0]].to(store.values.dtype))
    return replace(store, values=values)


def episode_for(model, batch, *, card: str, passes: int, keep: list | None = None):
    """Rows after the gold preload and `passes` think loops (via `_step`). `keep` collects snapshots."""
    import torch
    hidden = model.read(batch)
    store = model.build_store(hidden, batch)
    if card == "oracle":
        store = oracle_store(model, store, batch)
    elif card != "writer":
        raise ValueError(card)
    episode = model._start(batch, hidden, store, model._mentions(batch))
    if store is not None:
        gold_preload(model, store, batch, episode)
    if keep is not None:
        keep.append(("pre", episode.x.detach().clone(), episode.valid.clone()))
    everyone = torch.arange(batch.q_visit.shape[0])
    for step in range(passes):
        model._step(episode, everyone, step, store)
    return hidden, store, episode


def targets_inputs(model, batch):
    import torch
    from learnlab.core import IGNORE_INDEX
    answer = batch.answer
    length = int((answer != IGNORE_INDEX).sum(1).max().item())
    targets = answer[:, :max(length, 1)]
    start = batch.tokens[batch.q_visit, batch.q_span[:, 1] - 1]
    inputs = torch.cat([start.unsqueeze(1), targets[:, :-1]], dim=1)
    return targets, inputs.masked_fill(inputs == IGNORE_INDEX, model.config.pad_id)


def arm_loss(model, batch, arm: str, loops: int):
    """Answer-loss-only training objective of each arm (gold cards preloaded, fixed loops)."""
    import torch.nn.functional as F
    from learnlab.core import IGNORE_INDEX
    if arm.endswith("+distractors"):
        import torch
        base_arm = arm[:-len("+distractors")]
        hidden = model.read(batch)
        store = model.build_store(hidden, batch)
        episode = model._start(batch, hidden, store, model._mentions(batch))
        distractor_preload(model, store, batch, episode, 2, arm_loss.generator)
        targets, inputs = targets_inputs(model, batch)
        keep = targets != IGNORE_INDEX
        everyone = torch.arange(batch.q_visit.shape[0])
        terms = []
        for step in range(loops):
            rows, _, _, _ = model._step(episode, everyone, step, store)
            hidden_ans = model._decode_logits(rows, episode.valid, inputs)
            terms.append(F.cross_entropy(F.linear(hidden_ans[keep], model.embed.weight).float(), targets[keep]))
        return sum(terms) / len(terms), {}
    if arm not in BISECT:
        out = model.forward(batch, mode="gold", loops=loops, weights={"ans": 1.0})
        return out["ans"], out["metrics"]
    passes = 0 if arm.startswith("nothink") else 1
    _, _, episode = episode_for(model, batch, card=arm.split("-")[1], passes=passes)
    targets, inputs = targets_inputs(model, batch)
    hidden = model._decode_logits(episode.x, episode.valid, inputs)
    keep = targets != IGNORE_INDEX
    logits = F.linear(hidden[keep], model.embed.weight).float()
    return F.cross_entropy(logits, targets[keep]), {}


def arm_card_passes(arm: str, loops: int) -> tuple[str, int]:
    if arm in BISECT:
        return arm.split("-")[1], (0 if arm.startswith("nothink") else 1)
    return "writer", loops


def greedy_correct(model, batch, *, card: str, passes: int):
    """[Q] bool: greedy answer == target (value then <eos>), gold cards preloaded, fixed loops, no fetches."""
    import torch
    from learnlab.core import IGNORE_INDEX
    _, _, episode = episode_for(model, batch, card=card, passes=passes)
    tokens, lengths = model._greedy(batch, episode, model._mentions(batch), None)
    want = batch.answer
    ok = []
    for q in range(want.shape[0]):
        target = want[q][want[q] != IGNORE_INDEX].tolist()
        ok.append(tokens[q, :int(lengths[q])].tolist() == target)
    return torch.tensor(ok)


def wilson(k: int, n: int, z: float = 1.96) -> list[float]:
    if n == 0:
        return [0.0, 1.0]
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(centre - half, 4), round(centre + half, 4)]


def accuracy(model, batches, *, card: str, passes: int) -> dict:
    import torch
    was = model.training
    model.eval()
    with torch.no_grad():
        ok = torch.cat([greedy_correct(model, b, card=card, passes=passes) for b in batches])
    model.train(was)
    k, n = int(ok.sum()), ok.numel()
    return {"correct": k, "n": n, "acc": round(k / n, 4), "wilson95": wilson(k, n)}


# ----------------------------------------------------------------------------- audit (no training)
def cmd_audit(args) -> None:
    import torch
    import torch.nn.functional as F
    from premonition import answer_path
    from premonition.model import ROW_CARD, _norm
    from premonition.toy import ANSWER, EOS, QUESTION, WORLD
    report: dict = {}
    batch = load_split(args.run, "v16", "validation")[0]
    spec = spec_of("v16")
    model = build("D", "v16", 0)
    targets, inputs = targets_inputs(model, batch)
    count = batch.q_visit.shape[0]
    # 1. shifting and targets
    val_tokens = []
    for q in range(count):
        v, line = int(batch.q_visit[q]), int(batch.gold_lines[q, 0])
        s = int(batch.line_start[v, line])
        fact = batch.tokens[v, s:s + 4].tolist()
        qs, qe = (int(x) for x in batch.q_span[q])
        ask = batch.tokens[v, qs:qe].tolist()
        val_tokens.append(fact[3])
        assert fact[0] == WORLD and ask[0] == QUESTION and ask[-1] == ANSWER, (fact, ask)
        assert fact[1:3] == ask[1:3], "gold line must state the asked entity and relation"
        assert int(targets[q, 0]) == fact[3] and int(targets[q, 1]) == EOS
        line_end = int(batch.line_start[v, int(batch.q_line[q]) + 1]) if int(batch.q_line[q]) + 1 < \
            batch.line_start.shape[1] and int(batch.line_start[v, int(batch.q_line[q]) + 1]) >= 0 else int(batch.lengths[v])
        shown = batch.tokens[v, qs:line_end].tolist()
        assert fact[3] not in shown[4:], "label-free: the answer must not be in the reader stream after [answer]"
    report["targets"] = {"questions": count, "input0_is_answer_tag": bool((inputs[:, 0] == ANSWER).all()),
                         "input1_equals_target0": bool((inputs[:, 1] == targets[:, 0]).all()),
                         "target1_is_eos": bool((targets[:, 1] == EOS).all()),
                         "gold_line_matches_question_and_target": True, "answer_hidden_from_reader": True}
    # decoder causality: position 0 must not see the answer token at position 1
    with torch.no_grad():
        _, _, episode = episode_for(model, batch, card="writer", passes=1)
        a = model._decode_logits(episode.x, episode.valid, inputs)
        other = inputs.clone()
        other[:, 1] = (other[:, 1] + 1) % spec.vocab_size
        b = model._decode_logits(episode.x, episode.valid, other)
    report["decoder_causal"] = {"pos0_max_abs_change": float((a[:, 0] - b[:, 0]).abs().max()),
                                "pos1_changes": float((a[:, 1] - b[:, 1]).abs().max())}
    # 2. masks after the preload
    with torch.no_grad():
        hidden, store, episode = episode_for(model, batch, card="writer", passes=0)
    c = model.config
    card_slice = slice(c.question_rows + c.slots, c.question_rows + c.slots + c.cards)
    q_valid = episode.valid[:, :c.question_rows].sum(1)
    cards_valid = episode.valid[:, card_slice].sum(1)
    slot_valid = episode.valid[:, c.question_rows:c.question_rows + c.slots]
    expected_slots = torch.zeros_like(slot_valid)
    for q in range(count):
        v = int(batch.q_visit[q])
        ents = batch.tokens[v, :int(batch.q_span[q, 1])] - c.vocab_size
        ents = ents[(ents >= 0) & (ents < c.n_ent)]
        expected_slots[q, ents] = True
    card_row = episode.x[:, card_slice][:, 0]
    gold_val = store.values[batch.q_visit, batch.gold_lines[:, 0]]
    from premonition.store import age_bucket
    age = age_bucket(batch.q_line - batch.gold_lines[:, 0], c.age_buckets)
    expect_row = gold_val + model.think.age(age) + model.think.row_type.weight[ROW_CARD]
    report["masks"] = {"question_rows_valid": sorted(set(q_valid.tolist())),
                       "card_rows_valid": sorted(set(cards_valid.tolist())),
                       "slot_valid_equals_mentions": bool(torch.equal(slot_valid, expected_slots)),
                       "registers_valid": bool(episode.valid[:, card_slice.stop:].all()),
                       "card_row_equals_value_age_type": float((card_row - expect_row).abs().max()),
                       "valid_rows_per_question": sorted(set(episode.valid.sum(1).tolist()))}
    # decoder cross-attention exactly as Decoder.forward, to check masking and to trace it later
    with torch.no_grad():
        trace = decoder_trace(model, episode.x, episode.valid, inputs[:, :1])
        direct = model._decode_logits(episode.x, episode.valid, inputs[:, :1])
    report["decoder_trace_matches"] = float((trace["out"] - direct).abs().max())
    report["attention_on_invalid_rows"] = float((trace["weights"] * ~episode.valid[:, None, None, :]).sum())
    # 3. finite gradients, answer loss only, gold mode
    model.zero_grad()
    loss, _ = arm_loss(model, batch, "D", 2)
    loss.backward()
    grads = {n: p.grad for n, p in model.named_parameters()}
    report["gradients"] = {"loss": float(loss), "chance_loss": math.log(spec.values),
                           "all_finite": all(g is None or bool(torch.isfinite(g).all()) for g in grads.values()),
                           "none": sorted(n for n, g in grads.items() if g is None),
                           "zero": sorted(n for n, g in grads.items() if g is not None and float(g.abs().max()) == 0)}
    # 4. equivalences between the harness arms and D's own forward
    with torch.no_grad():
        d1 = model.forward(batch, mode="gold", loops=1, weights={"ans": 1.0})["ans"]
        t1, _ = arm_loss(model, batch, "think1-writer", 1)
        n0, _ = arm_loss(model, batch, "nothink-writer", 1)
        gated = answer_path.from_base(answer_path.THINK_GATED, model)
        g1 = gated.forward(batch, mode="gold", loops=1, weights={"ans": 1.0})["ans"]
        bypass = answer_path.from_base(answer_path.CARD_BYPASS, model)
        b1 = bypass.forward(batch, mode="gold", loops=1, weights={"ans": 1.0})["ans"]
    report["equivalence"] = {"D_gold_loop1_vs_think1_writer": float(abs(d1 - t1)),
                             "gated_alpha0_loop1_vs_nothink_writer": float(abs(g1 - n0)),
                             "D_loop1_ans": float(d1), "nothink_ans": float(n0), "bypass_loop1_ans": float(b1)}
    # gated: alpha gets a gradient at zero; the gated branch does not
    gated.zero_grad()
    gl = gated.forward(batch, mode="gold", loops=2, weights={"ans": 1.0})["ans"]
    gl.backward()
    report["gated_init_grads"] = {"alpha_grad": float(gated.think.alpha.grad),
                                  "think_layer_grad_max": max(float(p.grad.abs().max()) for p in
                                                              gated.think.layers.parameters() if p.grad is not None),
                                  "step_embedding_grad_max": float(gated.think.step.weight.grad.abs().max())}
    # bypass: decoder card rows are the inserted rows even after think
    with torch.no_grad():
        _, _, ep = episode_for(bypass, batch, card="writer", passes=2)
        _, _, ep0 = episode_for(bypass, batch, card="writer", passes=0)
    report["bypass_inserted_equals_prethink"] = float((ep.inserted - ep0.x[:, card_slice]).abs().max())
    report["bypass_postthink_differs"] = float((ep.x[:, card_slice] - ep0.x[:, card_slice]).abs().max())
    # greedy answer == teacher-forced correctness
    with torch.no_grad():
        greedy = greedy_correct(model, batch, card="writer", passes=2)
        out = model.forward(batch, mode="gold", loops=2, weights={"ans": 1.0})
    report["greedy_vs_teacher_forced_acc"] = [float(greedy.float().mean()), float(out["metrics"]["answer_acc"])]
    path = out_dir(args.run) / "audit.json"
    path.write_text(json.dumps(report, indent=1))
    print(json.dumps(report, indent=1))


def decoder_trace(model, rows, valid, inputs) -> dict:
    """Decoder.forward re-computed step by step: attention weights, cross-attention output, final output."""
    import torch
    import torch.nn.functional as F
    from premonition.model import _norm, rope
    dec = model.decoder
    x = model.embed(inputs)
    n, length, width = x.shape
    heads = dec.heads
    q, k, v = dec.qkv(dec.norm1(x)).view(n, length, 3, heads, -1).permute(2, 0, 3, 1, 4)
    positions = torch.arange(length)
    q, k = rope(q, positions, dec.base), rope(k, positions, dec.base)
    x = x + dec.proj(F.scaled_dot_product_attention(q, k, v, is_causal=True).transpose(1, 2).reshape(n, length, width))
    memory = _norm(rows)
    q = dec.cross_q(dec.norm2(x)).view(n, length, heads, -1).transpose(1, 2)
    k, v = dec.cross_kv(memory).view(n, rows.shape[1], 2, heads, -1).permute(2, 0, 3, 1, 4)
    scores = (q @ k.transpose(-1, -2)) / math.sqrt(q.shape[-1])
    scores = scores.masked_fill(~valid[:, None, None, :], float("-inf"))
    weights = scores.softmax(-1)
    cross = dec.cross_proj((weights @ v).transpose(1, 2).reshape(n, length, width))
    x = x + cross
    x = x + dec.mlp(dec.norm3(x))
    return {"out": dec.norm(x), "weights": weights, "cross": cross, "memory": memory}


# ----------------------------------------------------------------------------- training
def cmd_train(args) -> None:
    import torch
    from premonition import answer_path
    spent = ledger_seconds(args.run)
    remaining = CAP_SECONDS - spent
    if remaining <= 5:
        raise SystemExit(f"training budget exhausted ({spent:.1f} s of {CAP_SECONDS} s)")
    started = time.perf_counter()
    name = args.name or f"{args.arm}-{args.spec}-L{args.loops}-s{args.seed}-{args.steps}"
    model = build(args.arm, args.spec, args.seed)
    params = list(model.parameters())
    optimizer = torch.optim.AdamW(
        [{"params": [p for p in params if p.dim() >= 2], "weight_decay": 0.1},
         {"params": [p for p in params if p.dim() < 2], "weight_decay": 0.0}],
        lr=args.lr, betas=(0.9, 0.99), eps=1e-8)
    validation = load_split(args.run, args.spec, "validation")[:args.eval_batches]
    card, passes = arm_card_passes(args.arm, args.loops)
    history = []
    stream = checked_train(args.run, args.spec)
    arm_loss.generator = torch.Generator().manual_seed(1000 + args.seed)
    stopped = "steps"
    step = 0
    for step in range(args.steps):
        if time.perf_counter() - started > remaining:
            stopped = "30-minute ledger cap"
            break
        for group in optimizer.param_groups:
            group["lr"] = args.lr * min(1.0, (step + 1) / args.warmup)
        batch = next(stream)
        loss, metrics = arm_loss(model, batch, args.arm, args.loops)
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        finite = all(p.grad is None or bool(torch.isfinite(p.grad).all()) for p in params)
        norm = float(torch.nn.utils.clip_grad_norm_(params, 1.0))
        alpha_grad = float(model.think.alpha.grad) if hasattr(model.think, "alpha") else None
        optimizer.step()
        if (step + 1) % args.eval_every == 0 or step == 0 or step + 1 == args.steps:
            entry = {"step": step + 1, "loss": round(float(loss), 4), "grad_norm": round(norm, 3), "finite": finite,
                     "seconds": round(time.perf_counter() - started, 1),
                     "val": accuracy(model, validation, card=card, passes=passes)}
            if args.arm in ("think1-oracle", "nothink-oracle"):
                entry["val_writer_cards"] = accuracy(model, validation, card="writer", passes=passes)
            if alpha_grad is not None:
                entry["alpha"] = round(float(model.think.alpha), 5)
                entry["alpha_grad"] = alpha_grad
            if metrics:
                entry["train_acc"] = round(float(metrics["answer_acc"]), 4)
            history.append(entry)
            print(json.dumps(entry), flush=True)
            if not finite:
                stopped = "non-finite gradient"
                break
    seconds = time.perf_counter() - started
    ckpt_dir = out_dir(args.run) / "ckpt"
    ckpt_dir.mkdir(exist_ok=True)
    path = ckpt_dir / f"{name}.pt"
    base_arm = args.arm.split("+")[0]
    ident = answer_path.identity(base_arm, model.config) if base_arm in answer_path.ADJUSTMENTS else \
        {"variant": model.config.variant, "arm": args.arm, "purpose": "diagnostic"}
    if base_arm != args.arm:
        ident = {**ident, "training_cards": "gold + 2 random distractor fact cards, shuffled"}
    torch.save({"state_dict": model.state_dict(), "config": asdict(model.config), "arm": args.arm,
                "identity": ident, "spec": args.spec, "loops": args.loops, "seed": args.seed,
                "steps_done": step + 1 if stopped == "steps" else step, "lr": args.lr}, path)
    result = {"name": name, "arm": args.arm, "spec": args.spec, "loops": args.loops, "seed": args.seed,
              "steps": args.steps, "lr": args.lr, "warmup": args.warmup, "stopped": stopped,
              "seconds": round(seconds, 2), "ckpt": str(path.relative_to(ROOT)), "ckpt_sha256": sha256(path),
              "identity": ident, "history": history, "command": " ".join(sys.argv)}
    (out_dir(args.run) / "runs").mkdir(exist_ok=True)
    (out_dir(args.run) / "runs" / f"{name}.json").write_text(json.dumps(result, indent=1))
    ledger_add(args.run, {"kind": "train", "name": name, "seconds": round(seconds, 2)})
    print(f"done {name}: {seconds:.1f} s; ledger {ledger_seconds(args.run):.1f} / {CAP_SECONDS} s", flush=True)


def load_ckpt(run: str, name: str):
    import torch
    from premonition import answer_path
    from premonition.config import MiniConfig
    from premonition.model import PremonitionMini
    blob = torch.load(out_dir(run) / "ckpt" / f"{name}.pt", weights_only=False)
    config = MiniConfig(**{k: tuple(v) if isinstance(v, list) else v for k, v in blob["config"].items()})
    cls = answer_path.CLASSES.get(blob["arm"].split("+")[0], PremonitionMini)
    model = cls(config)
    model.load_state_dict(blob["state_dict"])
    model.eval()
    return model, blob


# ----------------------------------------------------------------------------- probes and collapse
def fit_probe(train_x, train_y, test_x, test_y, classes: int, epochs: int = 300) -> dict:
    """Multinomial logistic regression on frozen features (standardised on the fit set)."""
    import torch
    import torch.nn.functional as F
    mean, std = train_x.mean(0), train_x.std(0).clamp_min(1e-6)
    a, b = (train_x - mean) / std, (test_x - mean) / std
    w = torch.zeros(a.shape[1], classes, requires_grad=True)
    bias = torch.zeros(classes, requires_grad=True)
    opt = torch.optim.LBFGS([w, bias], max_iter=epochs, line_search_fn="strong_wolfe")

    def closure():
        opt.zero_grad()
        loss = F.cross_entropy(a @ w + bias, train_y) + 1e-3 * (w * w).sum()
        loss.backward()
        return loss
    opt.step(closure)
    with torch.no_grad():
        fit = float(((a @ w + bias).argmax(1) == train_y).float().mean())
        k = int(((b @ w + bias).argmax(1) == test_y).sum())
    return {"fit_acc": round(fit, 4), "test_correct": k, "test_n": len(test_y), "test_acc": round(k / len(test_y), 4),
            "wilson95": wilson(k, len(test_y))}


def features(model, batches, *, card: str, passes: int) -> dict:
    """Per-question vectors at each point of the answer path, plus the collapse measures."""
    import torch
    from premonition.model import _norm
    c = model.config
    base = c.question_rows + c.slots
    out: dict[str, list] = {k: [] for k in ("value", "pre", "post", "memory", "cross", "label", "attn_card",
                                              "attn_max", "attn_entropy", "valid_rows", "spread_pre", "mean_pre",
                                              "spread_post", "mean_post", "cos_post", "cos_pre", "cos_card_post",
                                              "norm_post_card", "norm_post_other")}
    with torch.no_grad():
        for batch in batches:
            keep: list = []
            hidden, store, episode = episode_for(model, batch, card=card, passes=passes, keep=keep)
            _, pre_x, valid = keep[0]
            count = batch.q_visit.shape[0]
            _, inputs = targets_inputs(model, batch)
            rows = episode.x
            if hasattr(episode, "inserted"):                 # D-card-bypass: the decoder reads inserted card rows
                rows = torch.cat([rows[:, :base], episode.inserted, rows[:, base + c.cards:]], dim=1)
            trace = decoder_trace(model, rows, episode.valid, inputs[:, :1])
            card_pos = base                                   # the one preloaded card lands in the first card row
            assert bool(episode.valid[:, card_pos].all()) and int(episode.valid[:, base:base + c.cards].sum()) == count
            out["value"].append(store.values[batch.q_visit, batch.gold_lines[:, 0]].float())
            out["pre"].append(pre_x[:, card_pos])
            out["post"].append(episode.x[:, card_pos])
            out["memory"].append(trace["memory"][:, card_pos])
            out["cross"].append(trace["cross"][:, 0])
            out["label"].append(batch.answer[:, 0])
            w = trace["weights"][:, :, 0]                     # [Q, heads, rows] at decoder position 0
            out["attn_card"].append(w[:, :, card_pos].mean(1))
            out["attn_max"].append(w.max(-1).values.mean(1))
            ent = -(w.clamp_min(1e-12).log() * w).sum(-1).mean(1)
            out["attn_entropy"].append(ent)
            nv = episode.valid.sum(1).float()
            out["valid_rows"].append(nv)
            for tag, x in (("pre", pre_x), ("post", rows)):
                m = valid.unsqueeze(-1).float()
                mean = (x * m).sum(1) / nv.unsqueeze(1)
                spread = ((((x - mean.unsqueeze(1)) ** 2).sum(-1) * valid).sum(1) / nv).sqrt()
                out[f"spread_{tag}"].append(spread)
                out[f"mean_{tag}"].append(mean.norm(dim=-1))
                z = torch.nn.functional.normalize(_norm(x), dim=-1)
                cos = z @ z.transpose(1, 2)
                pair = valid.unsqueeze(1) & valid.unsqueeze(2) & ~torch.eye(x.shape[1], dtype=torch.bool)
                out[f"cos_{tag}"].append((cos * pair).sum((1, 2)) / pair.sum((1, 2)))
                if tag == "post":
                    other = valid.clone()
                    other[:, card_pos] = False
                    out["cos_card_post"].append((cos[:, card_pos] * other).sum(1) / other.sum(1))
                    norms = x.norm(dim=-1)
                    out["norm_post_card"].append(norms[:, card_pos])
                    out["norm_post_other"].append((norms * other).sum(1) / other.sum(1))
    return {k: torch.cat(v) for k, v in out.items()}


def summary(values) -> dict:
    v = values.float()
    q = [round(float(x), 4) for x in v.quantile(torch_tensor([0.1, 0.5, 0.9]))]
    return {"mean": round(float(v.mean()), 4), "p10": q[0], "median": q[1], "p90": q[2]}


def torch_tensor(values):
    import torch
    return torch.tensor(values)


def paired_batches(spec_name: str, visits: int):
    """(original, changed, question index per visit): the first question's fact gets a new value; every other
    token, including all filler, stays identical, and the question's target follows the new value."""
    from dataclasses import replace
    from premonition import toy
    from premonition.train import label_free
    spec = spec_of(spec_name)
    rng = random.Random(SEEDS[spec_name]["paired"])
    change = random.Random(SEEDS[spec_name]["paired"] + 1)
    original, changed = [], []
    for _ in range(visits):
        lines = toy.visit_lines(spec, rng)
        first = next(i for i, line in enumerate(lines) if line.question)
        ask = lines[first]
        old = ask.answer[0]
        new = spec.value(change.choice([v for v in range(spec.values) if spec.value(v) != old]))
        fact = lines[ask.gold]
        assert fact.tokens[3] == old and ask.tokens[4] == old
        edited = list(lines)
        edited[ask.gold] = replace(fact, tokens=fact.tokens[:3] + [new] + fact.tokens[4:])
        edited[first] = replace(ask, tokens=ask.tokens[:4] + [new] + ask.tokens[5:], answer=[new])
        original.append(lines)
        changed.append(edited)

    def assemble(rows, prefix):
        it = iter(rows)
        saved = toy.visit_lines
        toy.visit_lines = lambda spec, rng: next(it)
        try:
            return label_free(toy.make_batch(spec, len(rows), random.Random(0), prefix=prefix))
        finally:
            toy.visit_lines = saved
    out = []
    for start in range(0, visits, VISITS):
        a = assemble(original[start:start + VISITS], "paired-a")
        b = assemble(changed[start:start + VISITS], "paired-b")
        firsts = [int((a.q_visit == v).nonzero()[0]) for v in range(a.tokens.shape[0])]
        out.append((a, b, firsts))
    return out


def irrelevant_batches(spec_name: str, visits: int):
    """(original, changed, first-question index per visit, kind): one fact that NO question of the visit asks
    gets a new value (preferring one about the first question's entity, then its relation); every other token
    and every target stays identical, so the first question's correct answer must not change."""
    from dataclasses import replace
    from premonition import toy
    from premonition.train import label_free
    spec = spec_of(spec_name)
    rng = random.Random(SEEDS[spec_name]["paired"] + 7)
    change = random.Random(SEEDS[spec_name]["paired"] + 8)
    original, changed, kinds = [], [], []
    for _ in range(visits):
        lines = toy.visit_lines(spec, rng)
        first = next(i for i, line in enumerate(lines) if line.question)
        ask = lines[first]
        asked = {line.gold for line in lines if line.question}
        facts = [i for i, line in enumerate(lines) if line.ents and not line.question and i not in asked]
        same_ent = [i for i in facts if lines[i].tokens[1] == ask.tokens[1]]
        same_rel = [i for i in facts if lines[i].tokens[2] == ask.tokens[2]]
        pick, kind = (same_ent[0], "same-entity") if same_ent else (same_rel[0], "same-relation") if same_rel \
            else (facts[0], "other")
        fact = lines[pick]
        old = fact.tokens[3]
        new = spec.value(change.choice([v for v in range(spec.values) if spec.value(v) != old]))
        edited = list(lines)
        edited[pick] = replace(fact, tokens=fact.tokens[:3] + [new] + fact.tokens[4:])
        original.append(lines)
        changed.append(edited)
        kinds.append(kind)

    def assemble(rows, prefix):
        it = iter(rows)
        saved = toy.visit_lines
        toy.visit_lines = lambda spec, rng: next(it)
        try:
            return label_free(toy.make_batch(spec, len(rows), random.Random(0), prefix=prefix))
        finally:
            toy.visit_lines = saved
    out = []
    for start in range(0, visits, VISITS):
        a = assemble(original[start:start + VISITS], "irrelevant-a")
        b = assemble(changed[start:start + VISITS], "irrelevant-b")
        firsts = [int((a.q_visit == v).nonzero()[0]) for v in range(a.tokens.shape[0])]
        out.append((a, b, firsts, kinds[start:start + VISITS]))
    return out


def cmd_interventions(args) -> None:
    """Eval only: (1) an irrelevant (unasked) fact changes -> the answer should stay; (2) the supplied card is
    removed at evaluation (a distribution shift: diagnostic only; the trained D-noask run is the real control)."""
    import torch
    started = time.perf_counter()
    model, blob = load_ckpt(args.run, args.ckpt)
    card, passes = arm_card_passes(blob["arm"], blob["loops"])
    report = {"ckpt": args.ckpt, "arm": blob["arm"], "card": card, "passes": passes}
    with torch.no_grad():
        counts: dict = {}
        for a, b, firsts, kinds in irrelevant_batches(blob["spec"], args.visits):
            pa = greedy_tokens(model, a, card=card, passes=passes)[firsts]
            pb = greedy_tokens(model, b, card=card, passes=passes)[firsts]
            target = a.answer[firsts, 0]
            assert torch.equal(target, b.answer[firsts, 0])
            for i, kind in enumerate(kinds):
                for key in (kind, "all"):
                    c = counts.setdefault(key, {"questions": 0, "unchanged": 0, "both_correct": 0,
                                                "correct_before": 0})
                    c["questions"] += 1
                    c["unchanged"] += int(pa[i] == pb[i])
                    c["both_correct"] += int(pa[i] == target[i] and pb[i] == target[i])
                    c["correct_before"] += int(pa[i] == target[i])
        for c in counts.values():
            c["wilson95_unchanged"] = wilson(c["unchanged"], c["questions"])
        report["irrelevant_fact_change"] = counts
        n = both = moved = 0
        for a, b, firsts in paired_batches(blob["spec"], args.visits):
            pa = greedy_tokens(model, a, card=card, passes=passes)[firsts]
            pb = greedy_tokens(model, b, card=card, passes=passes)[firsts]
            n += len(firsts)
            both += int(((pa == a.answer[firsts, 0]) & (pb == b.answer[firsts, 0])).sum())
            moved += int((pa != pb).sum())
        report["relevant_fact_change"] = {"questions": n, "both_correct": both, "wilson95_both": wilson(both, n),
                                          "prediction_changed": moved}
        if model.config.store:
            batches = load_split(args.run, blob["spec"], "validation")
            right = n = 0
            for batch in batches:
                hidden = model.read(batch)
                store = model.build_store(hidden, batch)
                mentions = model._mentions(batch)
                episode = model._start(batch, hidden, store, mentions)      # no card inserted
                everyone = torch.arange(batch.q_visit.shape[0])
                for step in range(passes):
                    model._step(episode, everyone, step, store)
                tokens, _ = model._greedy(batch, episode, mentions, None)
                right += int((tokens[:, 0] == batch.answer[:, 0]).sum())
                n += batch.q_visit.shape[0]
            report["card_removed_at_eval"] = {"correct": right, "n": n, "acc": round(right / n, 4),
                                              "wilson95": wilson(right, n)}
    report["seconds"] = round(time.perf_counter() - started, 2)
    (out_dir(args.run) / "interventions").mkdir(exist_ok=True)
    (out_dir(args.run) / "interventions" / f"{args.ckpt}.json").write_text(json.dumps(report, indent=1))
    ledger_add(args.run, {"kind": "intervention-eval", "name": args.ckpt, "seconds": report["seconds"]})
    print(json.dumps(report))


def greedy_tokens(model, batch, *, card: str, passes: int, store_edit=None):
    import torch
    hidden = model.read(batch)
    store = model.build_store(hidden, batch)
    if card == "oracle":
        store = oracle_store(model, store, batch)
    if store_edit is not None:
        store = store_edit(store, batch)
    episode = model._start(batch, hidden, store, model._mentions(batch))
    if store is not None:
        gold_preload(model, store, batch, episode)
    everyone = torch.arange(batch.q_visit.shape[0])
    for step in range(passes):
        model._step(episode, everyone, step, store)
    tokens, _ = model._greedy(batch, episode, model._mentions(batch), None)
    return tokens[:, 0]


def value_swap(store, batch):
    """Internal off-distribution swap: each question's gold card value <- the value vector of another fact line
    of the same visit that states a different value (None when there is none)."""
    from dataclasses import replace
    values = store.values.clone()
    swapped_to = []
    for q in range(batch.q_visit.shape[0]):
        v, gold = int(batch.q_visit[q]), int(batch.gold_lines[q, 0])
        want = int(batch.answer[q, 0])
        pick = None
        for line in range(batch.line_start.shape[1]):
            s = int(batch.line_start[v, line])
            if line == gold or s < 0 or batch.line_is_question[v, line] or int(batch.line_ents[v, line, 0]) < 0:
                continue
            if int(batch.tokens[v, s + 3]) != want:
                pick = (line, int(batch.tokens[v, s + 3]))
                break
        swapped_to.append(-1 if pick is None else pick[1])
        if pick is not None:
            values[v, gold] = store.values[v, pick[0]]
    value_swap.last = swapped_to
    return replace(store, values=values)


def cmd_probe(args) -> None:
    import torch
    started = time.perf_counter()
    if args.ckpt == "init":
        model = build(args.arm, args.spec, args.seed)
        model.eval()
        blob = {"arm": args.arm, "spec": args.spec, "loops": args.loops}
    else:
        model, blob = load_ckpt(args.run, args.ckpt)
    spec_name = blob["spec"]
    card, passes = arm_card_passes(blob["arm"], blob["loops"])
    card = args.card or card
    fit_set = load_split(args.run, spec_name, "probe")
    test_set = load_split(args.run, spec_name, "validation")
    f_fit = features(model, fit_set, card=card, passes=passes)
    f_test = features(model, test_set, card=card, passes=passes)
    classes = model.config.total_vocab
    report = {"ckpt": args.ckpt, "arm": blob["arm"], "card": card, "passes": passes,
              "probe_note": "linear probes on frozen features (model weights fixed); fit on the probe split, "
                            "scored on the validation split; both held out from training",
              "probes": {}}
    for point in ("value", "pre", "post", "memory", "cross"):
        report["probes"][point] = fit_probe(f_fit[point], f_fit["label"], f_test[point], f_test["label"], classes)
    report["collapse"] = {k: summary(f_test[k]) for k in ("valid_rows", "spread_pre", "mean_pre", "spread_post",
                                                            "mean_post", "cos_pre", "cos_post", "cos_card_post",
                                                            "norm_post_card", "norm_post_other", "attn_card",
                                                            "attn_max", "attn_entropy")}
    report["collapse"]["uniform_attention_on_one_row"] = round(float((1 / f_test["valid_rows"]).mean()), 4)
    with torch.no_grad():
        right = torch.cat([greedy_correct(model, b, card=card, passes=passes) for b in test_set])
    report["collapse_by_outcome"] = {name: {k: summary(f_test[k][mask]) for k in ("cos_post", "attn_card", "mean_post")}
                                     for name, mask in (("correct", right), ("wrong", ~right)) if bool(mask.any())}
    report["collapse_by_outcome"]["counts"] = {"correct": int(right.sum()), "wrong": int((~right).sum())}
    report["accuracy_writer_cards"] = accuracy(model, test_set, card="writer", passes=passes)
    if card == "oracle":
        report["accuracy_oracle_cards"] = accuracy(model, test_set, card="oracle", passes=passes)
    # causal paired test with consistent inputs and targets
    with torch.no_grad():
        n = both = moved = follows = orig_ok = new_ok = 0
        for a, b, firsts in paired_batches(spec_name, args.paired_visits):
            pa = greedy_tokens(model, a, card=card, passes=passes)[firsts]
            pb = greedy_tokens(model, b, card=card, passes=passes)[firsts]
            ta, tb = a.answer[firsts, 0], b.answer[firsts, 0]
            n += len(firsts)
            orig_ok += int((pa == ta).sum())
            new_ok += int((pb == tb).sum())
            both += int(((pa == ta) & (pb == tb)).sum())
            moved += int((pa != pb).sum())
            follows += int((pb == tb).sum())
        report["paired_value_change"] = {"questions": n, "original_correct": orig_ok, "changed_correct": new_ok,
                                         "both_correct": both, "wilson95_both": wilson(both, n),
                                         "prediction_changed": moved, "wilson95_changed": wilson(moved, n)}
        # internal card-value swap (off-distribution)
        n = to_swap = to_orig = 0
        for batch in test_set:
            pred = greedy_tokens(model, batch, card=card, passes=passes, store_edit=value_swap)
            target = torch.tensor(value_swap.last)
            ok = target >= 0
            n += int(ok.sum())
            to_swap += int(((pred == target) & ok).sum())
            to_orig += int(((pred == batch.answer[:, 0]) & ok).sum())
        report["card_value_swap"] = {"questions": n, "predicts_swapped_value": to_swap,
                                     "predicts_original_value": to_orig, "wilson95_swapped": wilson(to_swap, n)}
    seconds = time.perf_counter() - started
    report["seconds"] = round(seconds, 2)
    (out_dir(args.run) / "probes").mkdir(exist_ok=True)
    tag = args.tag or f"{args.ckpt}-{card}"
    (out_dir(args.run) / "probes" / f"{tag}.json").write_text(json.dumps(report, indent=1))
    ledger_add(args.run, {"kind": "probe", "name": tag, "seconds": round(seconds, 2)})
    print(json.dumps(report, indent=1))
    print(f"ledger {ledger_seconds(args.run):.1f} / {CAP_SECONDS} s")


def own_fixed(model, batch, loops: int, *, no_cards: bool = False) -> dict:
    """Own retrieval with exactly `loops` think loops (HALT ignored): after loop t < loops, the model's ASK
    (logit > 0) fetches its top-k eligible cards, so at most loops - 1 reads. Greedy answer after the last loop."""
    import torch
    from dataclasses import replace
    from learnlab.core import IGNORE_INDEX
    hidden = model.read(batch)
    store = model.build_store(hidden, batch)
    if store is not None and no_cards:
        store = replace(store, valid=torch.zeros_like(store.valid))
    mentions = model._mentions(batch)
    episode = model._start(batch, hidden, store, mentions)
    everyone = torch.arange(batch.q_visit.shape[0])
    asked = torch.zeros(len(everyone), dtype=torch.long)
    for step in range(loops):
        rows, halt, ask, scores = model._step(episode, everyone, step, store)
        if store is not None and step + 1 < loops:
            cards = store.top(scores, model.config.top_k).masked_fill((ask <= 0).unsqueeze(1), -1)
            asked += (ask > 0).long()
            model._insert(episode, store, everyone, cards)
    tokens, lengths = model._greedy(batch, episode, mentions, None)
    ok = []
    for q in range(batch.answer.shape[0]):
        target = batch.answer[q][batch.answer[q] != IGNORE_INDEX].tolist()
        ok.append(tokens[q, :int(lengths[q])].tolist() == target)
    got_gold = 0
    if store is not None and episode.fetched is not None:
        got_gold = int(episode.fetched.gather(1, batch.gold_lines[:, :1].clamp_min(0)).sum())
    return {"correct": sum(ok), "n": len(ok), "asked_loops": int(asked.sum()), "gold_fetched": got_gold}


def own_report(model, batches, loops: int, *, no_cards: bool = False) -> dict:
    import torch
    total = {"correct": 0, "n": 0, "asked_loops": 0, "gold_fetched": 0}
    with torch.no_grad():
        for batch in batches:
            for k, v in own_fixed(model, batch, loops, no_cards=no_cards).items():
                total[k] += v
    total["acc"] = round(total["correct"] / total["n"], 4)
    total["wilson95"] = wilson(total["correct"], total["n"])
    total["reads_allowed"] = loops - 1
    return total


@contextlib.contextmanager
def cards_removed(model):
    """Cards-only intervention: every real card is gone (NULL stays); reader state and name mentions kept."""
    import torch
    from dataclasses import replace
    original = model.build_store
    model.build_store = lambda hidden, batch: (lambda s: None if s is None else
                                               replace(s, valid=torch.zeros_like(s.valid)))(original(hidden, batch))
    try:
        yield
    finally:
        del model.build_store


def cmd_own(args) -> None:
    """Own retrieval + free generation: D's full curriculum (gold -> teacher -> own, all four losses)."""
    import itertools
    import torch
    from premonition import answer_path
    from premonition.train import MiniTrainer, budget_for_steps, mini_train_config, validate, validation_hook
    spent = ledger_seconds(args.run)
    remaining = CAP_SECONDS - spent - args.reserve
    if remaining <= 30:
        raise SystemExit(f"not enough training budget left ({spent:.1f} s spent)")
    started = time.perf_counter()
    name = args.name or f"own-{args.arm}-{args.spec}-s{args.seed}-{args.steps}"
    model = build(args.arm, args.spec, args.seed)
    trainer = MiniTrainer(model, mini_train_config(lr=args.lr, warmup_steps=args.warmup, log_every=50,
                                                   eval_every=args.eval_every), "cpu", flop_budget=1.0, seed=args.seed)
    stream = checked_train(args.run, args.spec)
    head = [next(stream) for _ in range(2)]
    trainer.calibrate(head)
    trainer.flop_budget = budget_for_steps(trainer, head, args.steps)
    validation = load_split(args.run, args.spec, "validation")
    curve = []
    report = trainer.train(itertools.chain(head, stream), max_seconds=remaining - (time.perf_counter() - started),
                           evaluate=validation_hook(validation[:4]),
                           on_log=lambda entry: curve.append({k: entry.get(k) for k in (
                               "step", "phase", "p_own", "loss", "lm", "ask", "ans", "halt", "gold_recall_at_4",
                               "answer_acc", "loops_per_question", "halt_rate", "eval") if k in entry}))
    train_seconds = time.perf_counter() - started
    model.eval()
    result = {"name": name, "arm": args.arm, "seed": args.seed, "steps_requested": args.steps,
              "train_report": {k: v for k, v in report.items() if isinstance(v, (int, float, str, bool, type(None)))},
              "curve": curve[-40:], "evals_during_training": [h for h in trainer.history if "eval" in h or "validation" in h][-6:]}
    with torch.no_grad():
        result["validation_learned_halting"] = trainer.evaluate(validation_hook(validation))
        result["validation_fixed_loops"] = {f"K={k}": own_report(model, validation, k) for k in (1, 2, 4)}
        if model.config.store:
            with cards_removed(model):
                result["validation_cards_removed"] = {
                    "learned_halting": validate(model, validation, gold_cards=False),
                    "K=2": own_report(model, validation, 2)}
        test = load_split(args.run, args.spec, "test")
        result["test_learned_halting"] = validate(model, test, gold_cards=bool(model.config.store))
        result["test_fixed_loops"] = {f"K={k}": own_report(model, test, k) for k in (1, 2)}
    seconds = time.perf_counter() - started
    ckpt_dir = out_dir(args.run) / "ckpt"
    ckpt_dir.mkdir(exist_ok=True)
    path = ckpt_dir / f"{name}.pt"
    ident = answer_path.identity(args.arm, model.config) if args.arm in answer_path.ADJUSTMENTS else \
        {"variant": model.config.variant, "arm": args.arm, "purpose": "diagnostic"}
    torch.save({"state_dict": model.state_dict(), "config": asdict(model.config), "arm": args.arm, "identity": ident,
                "spec": args.spec, "loops": model.config.max_loops, "seed": args.seed}, path)
    result.update(seconds_train=round(train_seconds, 2), seconds_total=round(seconds, 2), identity=ident,
                  ckpt=str(path.relative_to(ROOT)), ckpt_sha256=sha256(path), command=" ".join(sys.argv))
    (out_dir(args.run) / "runs").mkdir(exist_ok=True)
    (out_dir(args.run) / "runs" / f"{name}.json").write_text(json.dumps(result, indent=1, default=str))
    ledger_add(args.run, {"kind": "own-train+eval", "name": name, "seconds": round(seconds, 2)})
    print(json.dumps({k: result[k] for k in result if k not in ("curve", "evals_during_training")}, indent=1,
                     default=str)[:9000])
    print(f"ledger {ledger_seconds(args.run):.1f} / {CAP_SECONDS} s")


def cmd_multi(args) -> None:
    """Eval only: gold card + n distractor fact cards preloaded (shuffled), fixed loops. Which card does the
    answer copy?"""
    import torch
    from learnlab.core import IGNORE_INDEX
    started = time.perf_counter()
    model, blob = load_ckpt(args.run, args.ckpt)
    loops = blob["loops"]
    batches = load_split(args.run, blob["spec"], "validation")
    report = {"ckpt": args.ckpt, "arm": blob["arm"], "loops": loops, "split": "validation", "by_distractors": {}}
    for n in args.distractors:
        gen = torch.Generator().manual_seed(7000 + n)
        right = other = total = 0
        with torch.no_grad():
            for batch in batches:
                hidden = model.read(batch)
                store = model.build_store(hidden, batch)
                mentions = model._mentions(batch)
                episode = model._start(batch, hidden, store, mentions)
                cards = distractor_preload(model, store, batch, episode, n, gen)
                everyone = torch.arange(batch.q_visit.shape[0])
                for step in range(loops):
                    model._step(episode, everyone, step, store)
                tokens, _ = model._greedy(batch, episode, mentions, None)
                pred = tokens[:, 0]
                for q in range(len(pred)):
                    v = int(batch.q_visit[q])
                    vals = {int(batch.tokens[v, int(batch.line_start[v, int(c)]) + 3]) for c in cards[q] if int(c) >= 0
                            and int(c) != int(batch.gold_lines[q, 0])}
                    total += 1
                    right += int(pred[q]) == int(batch.answer[q, 0])
                    other += int(pred[q]) in vals and int(pred[q]) != int(batch.answer[q, 0])
        report["by_distractors"][n] = {"n": total, "correct": right, "acc": round(right / total, 4),
                                       "wilson95": wilson(right, total), "predicts_a_distractor_value": other,
                                       "copy_a_random_card_rate": round(1 / (1 + n), 4)}
    report["seconds"] = round(time.perf_counter() - started, 2)
    (out_dir(args.run) / "multi").mkdir(exist_ok=True)
    (out_dir(args.run) / "multi" / f"{args.ckpt}.json").write_text(json.dumps(report, indent=1))
    ledger_add(args.run, {"kind": "multi-card-eval", "name": args.ckpt, "seconds": report["seconds"]})
    print(json.dumps(report))


def cmd_test(args) -> None:
    """The untouched final-test split, scored once per checkpoint (never used to choose the repair)."""
    started = time.perf_counter()
    model, blob = load_ckpt(args.run, args.ckpt)
    card, passes = arm_card_passes(blob["arm"], blob["loops"])
    tests = out_dir(args.run) / "tests"
    tests.mkdir(exist_ok=True)
    path = tests / f"{args.ckpt}.json"
    if path.exists():
        raise SystemExit(f"{args.ckpt} was already scored on the test split")
    report = {"ckpt": args.ckpt, "arm": blob["arm"], "seed": blob["seed"], "split": "test", "card": card,
              "passes": passes, "fixed_loops": True, "accuracy": accuracy(model, load_split(args.run, blob["spec"],
                                                                                          "test"),
                                                                           card=card, passes=passes)}
    report["seconds"] = round(time.perf_counter() - started, 2)
    path.write_text(json.dumps(report, indent=1))
    ledger_add(args.run, {"kind": "test-eval", "name": args.ckpt, "seconds": report["seconds"]})
    print(json.dumps(report))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("data")
    sub.add_parser("audit")
    train = sub.add_parser("train")
    train.add_argument("--arm", choices=ARMS, required=True)
    train.add_argument("--spec", choices=sorted(SEEDS), default="v16")
    train.add_argument("--loops", type=int, default=2)
    train.add_argument("--steps", type=int, default=600)
    train.add_argument("--seed", type=int, default=0)
    train.add_argument("--lr", type=float, default=1e-3)
    train.add_argument("--warmup", type=int, default=100)
    train.add_argument("--eval-every", type=int, default=100)
    train.add_argument("--eval-batches", type=int, default=8)
    train.add_argument("--name")
    probe = sub.add_parser("probe")
    probe.add_argument("--ckpt", required=True)
    probe.add_argument("--arm", default="D")
    probe.add_argument("--spec", default="v16")
    probe.add_argument("--loops", type=int, default=2)
    probe.add_argument("--seed", type=int, default=0)
    probe.add_argument("--card", choices=["writer", "oracle"])
    probe.add_argument("--paired-visits", type=int, default=256)
    probe.add_argument("--tag")
    own = sub.add_parser("own")
    own.add_argument("--arm", choices=ARMS, required=True)
    own.add_argument("--spec", choices=sorted(SEEDS), default="v16")
    own.add_argument("--steps", type=int, default=1000)
    own.add_argument("--seed", type=int, default=0)
    own.add_argument("--lr", type=float, default=1e-3)
    own.add_argument("--warmup", type=int, default=100)
    own.add_argument("--eval-every", type=int, default=250)
    own.add_argument("--reserve", type=float, default=60.0)
    own.add_argument("--name")
    inter = sub.add_parser("interventions")
    inter.add_argument("--ckpt", required=True)
    inter.add_argument("--visits", type=int, default=256)
    multi = sub.add_parser("multi")
    multi.add_argument("--ckpt", required=True)
    multi.add_argument("--distractors", type=int, nargs="+", default=[0, 1, 2, 3])
    test = sub.add_parser("test")
    test.add_argument("--ckpt", required=True)
    args = parser.parse_args()
    bootstrap(args.run)
    import torch
    torch.set_num_threads(8)
    {"data": cmd_data, "audit": cmd_audit, "train": cmd_train, "probe": cmd_probe, "test": cmd_test, "own": cmd_own, "multi": cmd_multi, "interventions": cmd_interventions}[args.cmd](args)


if __name__ == "__main__":
    main()
