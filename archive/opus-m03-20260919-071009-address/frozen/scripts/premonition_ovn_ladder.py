"""Overnight experiment 1 (run ovn-20260918-235851): read / choose / combine with SUPPLIED cards.

Privileged gold-evidence diagnostic on a synthetic-vocabulary toy (premonition/toy_ladder.py; a declared exception
to the v2-tokenizer rule). Local CPU, answer loss only, hard 30-minute training ledger for the whole experiment
(arms, development trials, probes, reruns). Imports come only from the frozen snapshot (verified before import).

    PY -B scripts/premonition_ovn_ladder.py data
    PY -B scripts/premonition_ovn_ladder.py audit
    PY -B scripts/premonition_ovn_ladder.py train --arm D-think-centered --steps 1000 --seed 0
    PY -B scripts/premonition_ovn_ladder.py eval --ckpt <name>        # validation (development)
    PY -B scripts/premonition_ovn_ladder.py test --ckpt <name>        # untouched test, once per checkpoint
    PY -B scripts/premonition_ovn_ladder.py causal --ckpt <name>      # paired consistent-input interventions
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, fields
import hashlib
import json
import math
from pathlib import Path
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
RUN = "ovn-20260918-235851"
ARCHIVE = ROOT / "archive" / f"opus-{RUN}"
OUT = ROOT / "artifacts" / f"opus-{RUN}" / "exp1"
CAP_SECONDS = 30 * 60
VISITS = 16
SEEDS = {"train": 1101, "validation": 1202, "test": 1303, "paired": 1505}
EVAL_BATCHES = 16
TRAIN_BATCHES = 4000
LOOPS = 2
ARMS = ("nothink", "D", "D-card-bypass", "D-think-gated", "D-think-centered", "D-think-centered+final",
        "nothink+qread", "D-think-centered+qread", "D-think-centered+qread+final", "D-think-gated+qread",
        "nothink-noask+qread", "D-think-gated+qread+final")


def parse(arm: str) -> tuple[str, set]:
    base, *flags = arm.split("+")
    return base, set(flags)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bootstrap() -> None:
    frozen = ARCHIVE / "frozen"
    bad = [name for digest, name in (line.split(None, 1) for line in
                                     (ARCHIVE / "FROZEN.SHA256SUMS").read_text().splitlines())
           if sha256(frozen / name) != digest]
    if bad:
        raise SystemExit(f"frozen source changed: {bad}")
    sys.path.insert(0, str(frozen))
    import premonition
    if not Path(premonition.__file__).resolve().is_relative_to(frozen.resolve()):
        raise SystemExit(f"premonition imported from {premonition.__file__}")


def ledger_seconds() -> float:
    path = OUT / "ledger.jsonl"
    return 0.0 if not path.exists() else sum(json.loads(l)["seconds"] for l in path.read_text().splitlines() if l)


def ledger_add(entry: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "ledger.jsonl").open("a") as handle:
        handle.write(json.dumps(entry) + "\n")


def wilson(k: int, n: int, z: float = 1.96) -> list:
    if n == 0:
        return [0.0, 1.0]
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(centre - half, 4), round(centre + half, 4)]


# ----------------------------------------------------------------------------- data
def spec():
    from premonition.toy_ladder import LadderSpec
    return LadderSpec()


def batch_digest(item) -> str:
    from learnlab.readonly import tensor_digest
    import torch
    batch, supplied, hops = item
    digest = hashlib.sha256()
    for f in fields(batch):
        value = getattr(batch, f.name)
        if isinstance(value, torch.Tensor):
            digest.update(f.name.encode() + tensor_digest(value).encode())
    digest.update(tensor_digest(supplied).encode() + tensor_digest(hops).encode())
    return digest.hexdigest()


def label_free_item(item):
    from premonition.train import label_free
    batch, supplied, hops = item
    return label_free(batch), supplied, hops


def train_stream():
    from premonition import toy_ladder
    rng = random.Random(SEEDS["train"])
    while True:
        yield label_free_item(toy_ladder.make(spec(), VISITS, rng, training=True, prefix="train"))


def held_out(split: str):
    from premonition import toy_ladder
    rng = random.Random(SEEDS[split])
    return [label_free_item(toy_ladder.make(spec(), VISITS, rng, training=False, prefix=split))
            for _ in range(EVAL_BATCHES)]


def prints(item) -> list:
    batch = item[0]
    return [hashlib.sha1(batch.tokens[r, :int(batch.lengths[r])].numpy().tobytes()).hexdigest()
            for r in range(batch.tokens.shape[0])]


def cmd_data(args) -> None:
    import torch
    out = OUT / "data"
    out.mkdir(parents=True, exist_ok=True)
    manifest = {"spec": asdict(spec()), "vocab_size": spec().vocab_size, "chance": spec().chance, "seeds": SEEDS,
                "visits_per_batch": VISITS, "label_free": "premonition.train.label_free (legacy toy rule)",
                "vocabulary": "toy synthetic ids (diagnostic exception to the v2 tokenizer rule)",
                "privilege": "gold-evidence diagnostic: the 5 supplied cards per question come from the generator",
                "splits": {}}
    seen = {}
    for split in ("validation", "test"):
        items = held_out(split)
        path = out / f"{split}.pt"
        torch.save(items, path)
        seen[split] = {p for item in items for p in prints(item)}
        hops = torch.cat([item[2] for item in items])
        held = torch.cat([item[0].slices["heldout"] for item in items])
        manifest["splits"][split] = {"seed": SEEDS[split], "batches": len(items), "visits": len(items) * VISITS,
                                     "questions": int(hops.numel()), "one_hop": int((hops == 1).sum()),
                                     "two_hop": int((hops == 2).sum()), "two_hop_heldout": int(held.sum()),
                                     "file": str(path.relative_to(ROOT)), "sha256": sha256(path)}
    digests, train_prints, held_train = [], set(), 0
    stream = train_stream()
    for _ in range(TRAIN_BATCHES):
        item = next(stream)
        digests.append(batch_digest(item))
        train_prints.update(prints(item))
        held_train += int(item[0].slices["heldout"].sum())
    seen["train"] = train_prints
    (out / "train-digests.json").write_text(json.dumps(digests))
    manifest["splits"]["train"] = {"seed": SEEDS["train"], "batches_digested": TRAIN_BATCHES,
                                   "heldout_two_hop_in_train": held_train,
                                   "digest_of_digests": hashlib.sha256("".join(digests).encode()).hexdigest()}
    names = sorted(seen)
    manifest["overlap_visits"] = {f"{a}&{b}": len(seen[a] & seen[b]) for i, a in enumerate(names) for b in names[i + 1:]}
    manifest["shortcut_ceilings_validation"] = shortcut_ceilings(torch.load(out / "validation.pt", weights_only=False))
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(json.dumps(manifest, indent=1)[:4000])


def shortcut_ceilings(items) -> dict:
    """Expected accuracy of rules that pick uniformly among the supplied attribute cards satisfying a simple
    condition that does not solve the question (shortcut strategies)."""
    from premonition.toy_ladder import ANSWER, QUESTION
    s = spec()
    out = {"one_hop": {}, "two_hop": {}}
    counts = {"one_hop": {}, "two_hop": {}}
    for batch, supplied, hops in items:
        for q in range(len(hops)):
            v = int(batch.q_visit[q])
            start = int(batch.q_span[q, 0])
            ask = batch.tokens[v, start:int(batch.q_span[q, 1])].tolist()
            ent, target = ask[1], int(batch.answer[q, 0])
            rel = ask[2] if hops[q] == 1 else ask[3]
            cards = []
            for line in supplied[q].tolist():
                if line < 0:
                    continue
                ls = int(batch.line_start[v, line])
                cards.append(batch.tokens[v, ls:ls + 4].tolist())
            attrs = [c for c in cards if c[2] != s.link]
            links = [c for c in cards if c[2] == s.link]
            rules = {
                "entity_match_any_relation": [c[3] for c in attrs if c[1] == ent],
                "relation_match_any_entity": [c[3] for c in attrs if c[2] == rel],
                "random_attribute_card": [c[3] for c in attrs],
                "entity_not_in_question": [c[3] for c in attrs if c[1] != ent],
                "object_of_any_link": [c[3] for c in attrs if any(l[3] == c[1] for l in links)],
                "relation_match_and_object_of_a_link_whose_subject_has_a_card": [
                    c[3] for c in attrs if c[2] == rel and any(l[3] == c[1] and any(x[1] == l[1] for x in attrs)
                                                                for l in links)],
                "relation_match_and_entity_not_a_link_object": [
                    c[3] for c in attrs if c[2] == rel and not any(l[3] == c[1] for l in links)],
            }
            key = "one_hop" if hops[q] == 1 else "two_hop"
            for name, values in rules.items():
                hit = (values.count(target) / len(values)) if values else 0.0
                out[key][name] = out[key].get(name, 0.0) + hit
                counts[key][name] = counts[key].get(name, 0) + 1
    return {k: {name: round(total / counts[k][name], 4) for name, total in v.items()} for k, v in out.items()}


def load_split(split: str):
    import torch
    manifest = json.loads((OUT / "data" / "manifest.json").read_text())
    info = manifest["splits"][split]
    path = ROOT / info["file"]
    if sha256(path) != info["sha256"]:
        raise SystemExit(f"{path} changed since the data freeze")
    return torch.load(path, weights_only=False)


def checked_train():
    digests = json.loads((OUT / "data" / "train-digests.json").read_text())
    for i, item in enumerate(train_stream()):
        if i < len(digests) and batch_digest(item) != digests[i]:
            raise SystemExit(f"train batch {i} differs from the frozen digest")
        yield item


# ----------------------------------------------------------------------------- models
def build(arm: str, seed: int):
    import torch
    from premonition.config import MiniConfig
    from premonition.model import PremonitionMini
    variant = "D-noask" if "noask" in parse(arm)[0] else "D"
    config = MiniConfig.preset(variant, "tiny", vocab_size=spec().vocab_size, window=64)
    torch.manual_seed(seed)
    base = PremonitionMini(config)
    cls = model_class(arm)
    if cls is PremonitionMini:
        return base
    model = cls(config)
    missing, unexpected = model.load_state_dict(base.state_dict(), strict=False)
    if unexpected or sorted(missing) not in ([], ["think.alpha"]):
        raise RuntimeError(f"{arm}: state mismatch {missing} {unexpected}")
    return model


def model_class(arm: str):
    from premonition import answer_path, ovn_qread, ovn_variants
    from premonition.model import PremonitionMini
    base, flags = parse(arm)
    if "qread" in flags:
        if base == "D-think-gated":      # composed here from frozen classes (no frozen file changes)
            return type("GatedQReadMini", (ovn_qread.QReadMixin, answer_path.ThinkGatedMini),
                        {"variant_name": "D-think-gated+qread"})
        return {"nothink": ovn_qread.QReadMini, "D": ovn_qread.QReadMini, "nothink-noask": ovn_qread.QReadMini,
                "D-think-centered": ovn_qread.ThinkCenteredQReadMini}[base]
    return {**answer_path.CLASSES, **ovn_variants.CLASSES}.get(base, PremonitionMini)


def arm_identity(arm: str, model) -> dict:
    from premonition import answer_path, ovn_qread, ovn_variants
    base, flags = parse(arm)
    if base in answer_path.ADJUSTMENTS:
        ident = answer_path.identity(base, model.config)
    elif base in ovn_variants.VARIANTS:
        ident = ovn_variants.identity(base, model.config)
    else:
        ident = {"variant": model.config.variant, "purpose": "diagnostic"}
    if "qread" in flags:
        ident["qread"] = {"module": "premonition/ovn_qread.py", "prefix": ovn_qread.PREFIX,
                          "sha256": hashlib.sha256(Path(ovn_qread.__file__).read_bytes()).hexdigest()}
    return {**ident, "arm": arm, "passes": 0 if base.startswith("nothink") else LOOPS,
            "supervision": "final loop only" if "final" in flags else
            ("single decode" if base == "nothink" else "every loop (D's deep supervision)")}


def episode(model, item, *, cards: str, generator, passes: int, keep_rows: bool = False):
    """Read, write cards, insert the supplied cards (all 5 shuffled, or the gold ones only), run `passes` loops.
    Returns (episode, per-pass rows list, pre rows)."""
    import torch
    batch, supplied, hops = item
    hidden = model.read(batch)
    store = model.build_store(hidden, batch)
    ep = model._start(batch, hidden, store, model._mentions(batch))
    if cards == "all":
        order = torch.rand(supplied.shape, generator=generator).argsort(1)
        chosen = supplied.gather(1, order)
    elif cards == "gold":
        chosen = torch.where(torch.arange(supplied.shape[1]) < hops.unsqueeze(1), supplied,
                             torch.full_like(supplied, -1))[:, :2]
    elif cards == "none":
        chosen = torch.full((supplied.shape[0], 1), -1, dtype=torch.long)
    else:
        raise ValueError(cards)
    if cards != "none" and store is not None:
        model._insert(ep, store, torch.arange(len(hops)), chosen)
    pre = ep.x.detach().clone() if keep_rows else None
    everyone = torch.arange(len(hops))
    rows = []
    for step in range(passes):
        r, _, _, _ = model._step(ep, everyone, step, store)
        rows.append(r)
    return ep, rows, pre, store


def targets_inputs(model, batch):
    import torch
    from learnlab.core import IGNORE_INDEX
    length = int((batch.answer != IGNORE_INDEX).sum(1).max().item())
    targets = batch.answer[:, :max(length, 1)]
    start = batch.tokens[batch.q_visit, batch.q_span[:, 1] - 1]
    inputs = torch.cat([start.unsqueeze(1), targets[:, :-1]], dim=1)
    return targets, inputs.masked_fill(inputs == IGNORE_INDEX, model.config.pad_id)


def loss_of(model, item, arm: str, generator, cards: str = "all"):
    import torch.nn.functional as F
    from learnlab.core import IGNORE_INDEX
    base, flags = parse(arm)
    passes = 0 if base.startswith("nothink") else LOOPS
    ep, rows, _, _ = episode(model, item, cards=cards, generator=generator, passes=passes)
    batch = item[0]
    targets, inputs = targets_inputs(model, batch)
    first = 0
    if getattr(model, "qread", False):
        inputs, first = model.qread_inputs(batch, targets)
    keep = targets != IGNORE_INDEX
    if passes == 0:
        decoded = [model._decode_logits(ep.x, ep.valid, inputs)]
    elif "final" in flags:
        decoded = [model._decode_logits(rows[-1], ep.valid, inputs)]
    else:
        decoded = [model._decode_logits(r, ep.valid, inputs) for r in rows]
    decoded = [h[:, first:] for h in decoded]
    terms = [F.cross_entropy(F.linear(h[keep], model.embed.weight).float(), targets[keep]) for h in decoded]
    return sum(terms) / len(terms)


def predictions(model, item, *, cards: str, seed: int):
    """[Q] first answer token of the greedy answer (value then <eos> expected) and [Q] full-answer correctness."""
    import torch
    from learnlab.core import IGNORE_INDEX
    gen = torch.Generator().manual_seed(seed)
    passes = 0 if getattr(model, "_nothink", False) else LOOPS
    ep, _, _, _ = episode(model, item, cards=cards, generator=gen, passes=passes)
    batch = item[0]
    tokens, lengths = model._greedy(batch, ep, model._mentions(batch), None)
    ok = []
    for q in range(batch.answer.shape[0]):
        target = batch.answer[q][batch.answer[q] != IGNORE_INDEX].tolist()
        ok.append(tokens[q, :int(lengths[q])].tolist() == target)
    return tokens[:, 0], torch.tensor(ok)


def ladder_scores(model, items, *, seed: int = 99) -> dict:
    import torch
    was = model.training
    model.eval()
    out = {}
    with torch.no_grad():
        for cards in ("gold", "all"):
            ok_all, hops_all, held_all = [], [], []
            for i, item in enumerate(items):
                _, ok = predictions(model, item, cards=cards, seed=seed + i)
                ok_all.append(ok)
                hops_all.append(item[2])
                held_all.append(item[0].slices["heldout"])
            ok, hops, held = torch.cat(ok_all), torch.cat(hops_all), torch.cat(held_all)
            for name, mask in (("one_hop", hops == 1), ("two_hop_trained_rel", (hops == 2) & ~held),
                               ("two_hop_heldout_rel", (hops == 2) & held)):
                k, n = int(ok[mask].sum()), int(mask.sum())
                label = {"gold": "read", "all": "choose" if name == "one_hop" else "combine"}[cards]
                out[f"{label}:{name}"] = {"correct": k, "n": n, "acc": round(k / max(n, 1), 4),
                                          "wilson95": wilson(k, n)}
    model.train(was)
    return out


# ----------------------------------------------------------------------------- commands
def cmd_audit(args) -> None:
    import torch
    items = load_split("validation")
    item = items[0]
    batch, supplied, hops = item
    report = {}
    model = build("D", 0)
    gen = torch.Generator().manual_seed(0)
    with torch.no_grad():
        ep, rows, pre, store = episode(model, item, cards="all", generator=gen, passes=0, keep_rows=True)
    c = model.config
    base = c.question_rows + c.slots
    report["card_rows_valid"] = sorted(set(ep.valid[:, base:base + c.cards].sum(1).tolist()))
    report["question_rows_valid"] = sorted(set(ep.valid[:, :c.question_rows].sum(1).tolist()))
    gold, _, missing = store.gold(batch.gold_lines, batch.q_visit, batch.q_line)
    report["gold_missing"] = int(missing.sum())
    report["gold_in_supplied"] = bool(all(set(batch.gold_lines[q][batch.gold_lines[q] >= 0].tolist())
                                          <= set(supplied[q].tolist()) for q in range(len(hops))))
    report["supplied_distinct"] = bool(all(len({x for x in supplied[q].tolist() if x >= 0}) == (4 if int(hops[q]) == 1
                                                                                                 else 6)
                                           for q in range(len(hops))))
    # targets: 1-hop value = gold attribute line's value; 2-hop = value of the friend's attribute line
    s = spec()
    bad = 0
    for q in range(len(hops)):
        v = int(batch.q_visit[q])
        ask = batch.tokens[v, int(batch.q_span[q, 0]):int(batch.q_span[q, 1])].tolist()
        lines = batch.gold_lines[q][batch.gold_lines[q] >= 0].tolist()
        facts = [batch.tokens[v, int(batch.line_start[v, l]):int(batch.line_start[v, l]) + 4].tolist() for l in lines]
        if int(hops[q]) == 1:
            ok = facts[0][1:3] == ask[1:3] and facts[0][3] == int(batch.answer[q, 0])
        else:
            link, attr = facts
            ok = link[1] == ask[1] and link[2] == s.link and attr[1] == link[3] and attr[2] == ask[3] \
                and attr[3] == int(batch.answer[q, 0])
        bad += not ok
    report["target_errors"] = bad
    for arm in ARMS:
        m = build(arm, 0)
        m.zero_grad()
        loss = loss_of(m, item, arm, torch.Generator().manual_seed(1))
        loss.backward()
        grads = [p.grad for p in m.parameters() if p.grad is not None]
        report[f"init_loss:{arm}"] = round(float(loss), 4)
        report[f"finite:{arm}"] = all(bool(torch.isfinite(g).all()) for g in grads)
    shared = build("D", 0).state_dict()
    report["shared_init_identical"] = all(
        all(torch.equal(v, shared[k]) for k, v in build(arm, 0).state_dict().items() if k in shared) for arm in ARMS)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "audit.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report, indent=1))


def cmd_train(args) -> None:
    import torch
    spent = ledger_seconds()
    remaining = CAP_SECONDS - spent - args.reserve
    if remaining <= 10:
        raise SystemExit(f"experiment-1 budget exhausted ({spent:.1f} s)")
    started = time.perf_counter()
    name = args.name or f"{args.arm}-s{args.seed}-{args.steps}"
    model = build(args.arm, args.seed)
    params = list(model.parameters())
    optimizer = torch.optim.AdamW([{"params": [p for p in params if p.dim() >= 2], "weight_decay": 0.1},
                                   {"params": [p for p in params if p.dim() < 2], "weight_decay": 0.0}],
                                  lr=args.lr, betas=(0.9, 0.99), eps=1e-8)
    validation = load_split("validation")[:args.eval_batches]
    model._nothink = parse(args.arm)[0].startswith("nothink")
    gen = torch.Generator().manual_seed(5000 + args.seed)
    history, stopped, step = [], "steps", 0
    stream = checked_train()
    for step in range(args.steps):
        if time.perf_counter() - started > remaining:
            stopped = "experiment ledger cap"
            break
        for group in optimizer.param_groups:
            group["lr"] = args.lr * min(1.0, (step + 1) / args.warmup)
        loss = loss_of(model, next(stream), args.arm, gen, cards="gold" if step < args.gold_steps else "all")
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        finite = all(p.grad is None or bool(torch.isfinite(p.grad).all()) for p in params)
        norm = float(torch.nn.utils.clip_grad_norm_(params, 1.0))
        optimizer.step()
        if (step + 1) % args.eval_every == 0 or step + 1 == args.steps:
            scores = ladder_scores(model, validation)
            entry = {"step": step + 1, "loss": round(float(loss.detach()), 4), "grad_norm": round(norm, 3),
                     "finite": finite, "seconds": round(time.perf_counter() - started, 1),
                     **{k: f"{v['correct']}/{v['n']}" for k, v in scores.items()}}
            if hasattr(model.think, "alpha"):
                entry["alpha"] = round(float(model.think.alpha.detach()), 5)
            history.append(entry)
            print(json.dumps(entry), flush=True)
            if not finite:
                stopped = "non-finite gradient"
                break
    seconds = time.perf_counter() - started
    (OUT / "ckpt").mkdir(parents=True, exist_ok=True)
    path = OUT / "ckpt" / f"{name}.pt"
    ident = arm_identity(args.arm, model)
    torch.save({"state_dict": model.state_dict(), "config": asdict(model.config), "arm": args.arm,
                "identity": ident, "seed": args.seed, "steps_done": len(history) and history[-1]["step"],
                "lr": args.lr}, path)
    result = {"name": name, "arm": args.arm, "seed": args.seed, "steps": args.steps, "gold_steps": args.gold_steps,
              "lr": args.lr,
              "warmup": args.warmup, "stopped": stopped, "seconds": round(seconds, 2),
              "ckpt": str(path.relative_to(ROOT)), "ckpt_sha256": sha256(path), "identity": ident,
              "history": history, "command": " ".join(sys.argv)}
    (OUT / "runs").mkdir(exist_ok=True)
    (OUT / "runs" / f"{name}.json").write_text(json.dumps(result, indent=1))
    ledger_add({"kind": "train", "name": name, "seconds": round(seconds, 2)})
    print(f"done {name}: {seconds:.1f} s; experiment-1 ledger {ledger_seconds():.1f} / {CAP_SECONDS} s", flush=True)


def load(name: str):
    import torch
    from premonition.config import MiniConfig
    blob = torch.load(OUT / "ckpt" / f"{name}.pt", weights_only=False)
    config = MiniConfig(**{k: tuple(v) if isinstance(v, list) else v for k, v in blob["config"].items()})
    model = model_class(blob["arm"])(config)
    model.load_state_dict(blob["state_dict"])
    model._nothink = parse(blob["arm"])[0].startswith("nothink")
    model.eval()
    return model, blob


def collapse(model, items) -> dict:
    """Medians over questions of the decoder memory after the last loop (valid rows): mean-row size, centred
    spread, pairwise cosine after the decoder's parameter-free norm; and the gate value."""
    import torch
    from premonition.model import _norm
    stats = {"mean_row": [], "spread": [], "cos": []}
    with torch.no_grad():
        for i, item in enumerate(items[:4]):
            ep, rows, _, _ = episode(model, item, cards="all", generator=torch.Generator().manual_seed(i),
                                     passes=0 if model._nothink else LOOPS)
            x = rows[-1] if rows else ep.x
            if hasattr(ep, "inserted"):
                c = model.config
                base = c.question_rows + c.slots
                x = torch.cat([x[:, :base], ep.inserted, x[:, base + c.cards:]], dim=1)
            valid = ep.valid
            n = valid.sum(1).float()
            mean = (x * valid.unsqueeze(-1)).sum(1) / n.unsqueeze(1)
            spread = ((((x - mean.unsqueeze(1)) ** 2).sum(-1) * valid).sum(1) / n).sqrt()
            z = torch.nn.functional.normalize(_norm(x), dim=-1)
            pair = valid.unsqueeze(1) & valid.unsqueeze(2) & ~torch.eye(x.shape[1], dtype=torch.bool)
            cos = ((z @ z.transpose(1, 2)) * pair).sum((1, 2)) / pair.sum((1, 2))
            stats["mean_row"].append(mean.norm(dim=-1))
            stats["spread"].append(spread)
            stats["cos"].append(cos)
    out = {k: round(float(torch.cat(v).median()), 4) for k, v in stats.items()}
    if hasattr(model.think, "alpha"):
        out["alpha"] = round(float(model.think.alpha), 5)
    return out


def two_hop_errors(model, items) -> dict:
    """On 2-hop questions with all 5 cards: which supplied value did a wrong answer copy?"""
    import torch
    s = spec()
    tally = {"correct": 0, "own_attribute(1-hop shortcut)": 0, "decoy_chain_answer": 0, "decoy_chain_start": 0,
             "other": 0, "n": 0}
    with torch.no_grad():
        for i, item in enumerate(items):
            first, ok = predictions(model, item, cards="all", seed=99 + i)
            batch, supplied, hops = item
            for q in range(len(hops)):
                if int(hops[q]) != 2:
                    continue
                v = int(batch.q_visit[q])
                cards = [batch.tokens[v, int(batch.line_start[v, l]):int(batch.line_start[v, l]) + 4].tolist()
                         for l in supplied[q].tolist()]
                own, decoy, decoy_start = cards[2][3], cards[4][3], cards[5][3]   # A(a,r), A(d,r), A(c,r)
                tally["n"] += 1
                p = int(first[q])
                if bool(ok[q]):
                    tally["correct"] += 1
                elif p == own:
                    tally["own_attribute(1-hop shortcut)"] += 1
                elif p == decoy:
                    tally["decoy_chain_answer"] += 1
                elif p == decoy_start:
                    tally["decoy_chain_start"] += 1
                else:
                    tally["other"] += 1
    return tally


def cmd_eval(args) -> None:
    started = time.perf_counter()
    model, blob = load(args.ckpt)
    items = load_split("validation")
    report = {"ckpt": args.ckpt, "arm": blob["arm"], "seed": blob["seed"], "split": "validation",
              "scores": ladder_scores(model, items), "collapse": collapse(model, items),
              "two_hop_errors": two_hop_errors(model, items)}
    report["seconds"] = round(time.perf_counter() - started, 2)
    (OUT / "eval").mkdir(parents=True, exist_ok=True)
    (OUT / "eval" / f"{args.ckpt}.json").write_text(json.dumps(report, indent=1))
    ledger_add({"kind": "eval", "name": args.ckpt, "seconds": report["seconds"]})
    print(json.dumps(report))


def cmd_test(args) -> None:
    started = time.perf_counter()
    model, blob = load(args.ckpt)
    path = OUT / "tests" / f"{args.ckpt}.json"
    if path.exists():
        raise SystemExit("already scored on the test split")
    report = {"ckpt": args.ckpt, "arm": blob["arm"], "seed": blob["seed"], "split": "test",
              "scores": ladder_scores(model, load_split("test"), seed=7)}
    report["seconds"] = round(time.perf_counter() - started, 2)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=1))
    ledger_add({"kind": "test-eval", "name": args.ckpt, "seconds": report["seconds"]})
    print(json.dumps(report))


def paired_two_hop(visits: int):
    """Consistent-input pairs on each visit's first 2-hop question: (kind, original item, edited item, q index per
    visit). Kinds: 'relevant' (the friend's attribute value changes -> answer must follow), 'tempting' (the asker's
    own attribute, a supplied distractor, changes -> answer must stay), 'link' (the asker's friend changes to
    another person whose attribute value differs -> answer must follow)."""
    from copy import deepcopy
    from premonition import toy_ladder
    s = spec()
    rng = random.Random(SEEDS["paired"])
    edit_rng = random.Random(SEEDS["paired"] + 1)
    out = {"relevant": ([], []), "tempting": ([], []), "link": ([], [])}
    for _ in range(visits):
        lines, world, plan = toy_ladder.visit(s, rng, training=False)
        first = next(l for l in lines if l.question and l.hops == 2)
        a = first.ents[0]
        r = first.relation
        b = world.friend[a]
        for kind in out:
            edited = deepcopy(world)
            if kind == "relevant":
                edited.attr[(b, r)] = edit_rng.choice([v for v in range(s.values) if v != world.attr[(b, r)]])
            elif kind == "tempting":
                edited.attr[(a, r)] = edit_rng.choice([v for v in range(s.values) if v != world.attr[(a, r)]])
            else:
                options = [x for x in world.ents if x not in (a, b) and world.attr[(x, r)] != world.attr[(b, r)]]
                if not options:
                    continue
                edited.friend[a] = edit_rng.choice(options)
            new_lines, _, _ = toy_ladder.visit(s, rng, training=False, world=edited, plan=plan)
            new_first = next(l for l in new_lines if l.question and l.hops == 2)
            if len(set(new_first.supplied)) != 6 or len(set(first.supplied)) != 6:
                continue
            out[kind][0].append(lines)
            out[kind][1].append(new_lines)
    batches = {}
    for kind, (orig, edit) in out.items():
        pairs = []
        for start in range(0, len(orig), VISITS):
            a_item = label_free_item(toy_ladder.assemble(s, orig[start:start + VISITS], prefix=f"{kind}-a"))
            b_item = label_free_item(toy_ladder.assemble(s, edit[start:start + VISITS], prefix=f"{kind}-b"))
            firsts = [int(((a_item[0].q_visit == v) & (a_item[2] == 2)).nonzero()[0]) for v in range(len(orig[start:start + VISITS]))]
            pairs.append((a_item, b_item, firsts))
        batches[kind] = pairs
    return batches


def cmd_causal(args) -> None:
    import torch
    started = time.perf_counter()
    model, blob = load(args.ckpt)
    report = {"ckpt": args.ckpt, "arm": blob["arm"], "cards": "all 6 supplied (shuffled, same order in a pair)"}
    with torch.no_grad():
        for kind, pairs in paired_two_hop(args.visits).items():
            n = both = moved = 0
            for i, (a, b, firsts) in enumerate(pairs):
                pa, _ = predictions(model, a, cards="all", seed=300 + i)
                pb, _ = predictions(model, b, cards="all", seed=300 + i)
                pa, pb = pa[firsts], pb[firsts]
                ta, tb = a[0].answer[firsts, 0], b[0].answer[firsts, 0]
                n += len(firsts)
                both += int(((pa == ta) & (pb == tb)).sum())
                moved += int((pa != pb).sum())
            expect = "answer must stay" if kind == "tempting" else "answer must change"
            report[kind] = {"pairs": n, "both_correct": both, "wilson95_both": wilson(both, n),
                            "prediction_changed": moved, "expected": expect}
    report["seconds"] = round(time.perf_counter() - started, 2)
    (OUT / "causal").mkdir(parents=True, exist_ok=True)
    (OUT / "causal" / f"{args.ckpt}.json").write_text(json.dumps(report, indent=1))
    ledger_add({"kind": "causal-eval", "name": args.ckpt, "seconds": report["seconds"]})
    print(json.dumps(report))


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("data")
    sub.add_parser("audit")
    train = sub.add_parser("train")
    train.add_argument("--arm", choices=ARMS, required=True)
    train.add_argument("--steps", type=int, default=1000)
    train.add_argument("--seed", type=int, default=0)
    train.add_argument("--lr", type=float, default=1e-3)
    train.add_argument("--warmup", type=int, default=100)
    train.add_argument("--eval-every", type=int, default=250)
    train.add_argument("--eval-batches", type=int, default=4)
    train.add_argument("--reserve", type=float, default=0.0)
    train.add_argument("--gold-steps", type=int, default=0, help="curriculum: first N steps supply only gold cards")
    train.add_argument("--name")
    for name in ("eval", "test"):
        p = sub.add_parser(name)
        p.add_argument("--ckpt", required=True)
    causal = sub.add_parser("causal")
    causal.add_argument("--ckpt", required=True)
    causal.add_argument("--visits", type=int, default=256)
    args = parser.parse_args()
    bootstrap()
    import torch
    torch.set_num_threads(8)
    {"data": cmd_data, "audit": cmd_audit, "train": cmd_train, "eval": cmd_eval, "test": cmd_test,
     "causal": cmd_causal}[args.cmd](args)


if __name__ == "__main__":
    main()
