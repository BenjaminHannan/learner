"""Run card R2, stage 0 (design/steals-2026-10-17/R2-STAGE0-CARD.md, sealed): fetch_gate on the far-fact toy, CPU, $0.

Arms: A0 = D with every steal off; A1 = the same with `fetch_gate=True` (paired init: at a seed every shared weight
and the RNG stream are identical). Each run is the registered `train.train_toy("D", steps=1500, seed=s)` with AdamW.
The readout is accuracy, not time, so runs need no interleaving and may run in separate processes (`--arms`).

Primary: held-out toy accuracy with own retrieval (`validate` -> accuracy); d_s = acc(A1, s) - acc(A0, s).
Guards (sealed card): G1 gold-card gain >= own-retrieval gain (pooled); G2 recall@4(A1) >= 0.8 recall@4(A0) (pooled);
G3 mean card gate >= 0.2 on gold rows the model fetched itself in `answer()` (pooled; fewer than 30 rows is a trip).
The gates on preloaded gold cards (`answer_with_gold`) and the decoder cross-attention gate (one teacher-mode pass)
are reported. Every run is bound to the commit, the runner, card and package hashes, and the sealed runner and card.

    OMP_NUM_THREADS=1 python3 -B scripts/premonition_steals_r2_stage0.py --out artifacts/claude-steals-20261017/r2-stage0
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from premonition import train as ptrain                                     # noqa: E402
from premonition.toy import ToySpec, toy_set                                 # noqa: E402

ARMS = {"A0": {}, "A1": {"fetch_gate": True}}
CARD_SEEDS = (0, 1, 2)
EXTENSION_SEEDS = (3, 4)
MIN_EFFECT = 0.03                     # accuracy points
RECALL_FLOOR = 0.8                    # G2: A1's pooled recall@4 at least 0.8 x A0's
GATE_FLOOR = 0.2                      # G3: pooled mean card gate on gold rows the model fetched itself
GATE_MIN_ROWS = 30                    # G3: fewer own-fetched gold rows (pooled) is a trip
CHANCE_MARGIN = 0.02                  # "at chance": accuracy <= chance + 2 points ...
CHANCE_BAND = 0.01                    # ... and |d_s| < 1 point, both in every seed
CARD_SETTINGS = {"steps": 1500, "visits": 16}
CARD = ROOT / "design" / "steals-2026-10-17" / "R2-STAGE0-CARD.md"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identity() -> dict:
    """What a run is bound to: the commit, the runner and card hashes, and one hash over premonition/*.py."""
    package = hashlib.sha256()
    for path in sorted((ROOT / "premonition").glob("*.py")):
        package.update(path.name.encode() + path.read_bytes())
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    return {"commit": commit, "runner": sha256(Path(__file__).resolve()), "card": sha256(CARD),
            "premonition": package.hexdigest()}


def check_seal(out: Path, ident: dict) -> None:
    """The run's runner and card must be the sealed ones (SEAL.sha256.txt in the output directory)."""
    seal = out / "SEAL.sha256.txt"
    if not seal.exists():
        return                                   # smoke runs outside the sealed directory
    sealed = {line.split()[1]: line.split()[0] for line in seal.read_text().splitlines() if line.strip()}
    want = {"design/steals-2026-10-17/R2-STAGE0-CARD.md": ident["card"],
            "scripts/premonition_steals_r2_stage0.py": ident["runner"]}
    for name, digest in want.items():
        if sealed.get(name) != digest:
            raise SystemExit(f"{name} does not match the seal in {seal}; refusing to run")


def write_json(path: Path, value) -> None:
    """Atomic: a killed run never leaves a half-written result behind."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=1))
    os.replace(tmp, path)


@torch.no_grad()
def gate_means(model, batches: list, answer) -> dict:
    """Mean card gate on gold / wrong inserted rows and mean decoder cross-attention gate, per head, over `answer`
    (`model.answer`: own fetches only; `train.answer_with_gold`: every told question's gold cards preloaded)."""
    think, decoder = model.think, model.decoder
    record = {"gold": [], "wrong": [], "cross": []}
    current: dict = {}
    original_insert = model._insert

    def insert(episode, store, index, cards):
        current["index"], current["cards"] = index, cards
        return original_insert(episode, store, index, cards)

    def card_hook(_m, _a, out):
        gate = torch.sigmoid(out.float())                                   # [n, K, H]
        index, cards = current["index"], current["cards"]
        gold = current["gold"][index]                                       # [n, G] gold lines of each question
        real = (cards >= 0) & (cards < current["lines"])
        is_gold = (cards.unsqueeze(-1) == gold.unsqueeze(1)).any(-1) & real
        record["gold"].append(gate[is_gold])
        record["wrong"].append(gate[real & ~is_gold])

    def cross_hook(_m, _a, out):
        record["cross"].append(torch.sigmoid(out.float()).reshape(-1, out.shape[-1]))

    model.eval()
    handle = think.fetch_gate.register_forward_hook(card_hook)
    model._insert = insert
    try:                                     # card gates: only the inserts of `answer` itself
        for batch in batches:
            current["gold"] = batch.gold_lines
            current["lines"] = batch.line_start.shape[1]
            answer(batch)
    finally:
        del model._insert
        handle.remove()
    # The decoder's cross-attention gate, once per answer position: one teacher-mode pass, 4 fixed loops. The card
    # hook is detached first, so teacher-forced cards never count as the model's own fetches.
    handle = decoder.cross_gate.register_forward_hook(cross_hook)
    try:
        for i, batch in enumerate(batches):
            model(batch, mode="teacher", loops=4, generator=torch.Generator().manual_seed(1234 + i))
    finally:
        handle.remove()
    out = {}
    for name, parts in record.items():
        rows = torch.cat(parts) if parts else torch.zeros(0, model.config.n_heads)
        out[name] = {"rows": int(rows.shape[0]), "per_head": rows.mean(0).tolist() if rows.numel() else None,
                     "mean": float(rows.mean()) if rows.numel() else None}
    return out


def run(arm: str, seed: int, settings: dict, ident: dict, log) -> dict:
    started = time.perf_counter()
    trained = ptrain.train_toy("D", steps=settings["steps"], visits=settings["visits"], seed=seed,
                               config_overrides=ARMS[arm] or None)
    seconds = time.perf_counter() - started
    model, validation = trained["trainer"].model, trained["validation"]
    last = [r for r in trained["history"] if "eval" not in r][-1]
    result = {"arm": arm, "seed": seed, "settings": settings, "identity": ident, "steps": trained["trainer"].step,
              "seconds": seconds,
              "parameters": trained["parameters"], "chance": trained["chance"],
              "final_losses": {k: last.get(k) for k in ("loss", "lm", "ask", "ans", "halt")},
              "validation": {k: validation.get(k) for k in (
                  "accuracy", "accuracy_gold_cards", "gold_recall_at_4", "random_recall_at_4", "asked_rate",
                  "loops_mean", "halt_rate", "questions")}}
    result["finite"] = all(isinstance(v, float) and math.isfinite(v) for v in result["final_losses"].values()
                           if v is not None)
    if arm == "A1":
        spec = ToySpec()
        held_out = [ptrain.label_free(b) for b in toy_set(spec, 4, settings["visits"], seed + 1000)]
        result["gates_own"] = gate_means(model, held_out, model.answer)                             # G3
        result["gates_preload"] = gate_means(model, held_out, lambda b: ptrain.answer_with_gold(model, b))  # reported
    log(f"{arm} s{seed}: steps {result['steps']} {seconds:.0f}s acc {validation['accuracy']:.4f} "
        f"gold {validation['accuracy_gold_cards']:.4f} recall {validation['gold_recall_at_4']:.3f}")
    return result


def judge(a0: list[dict], a1: list[dict]) -> dict:
    """The card's bar, guards and verdict on paired runs (same seeds, same order)."""
    acc = lambda r, key="accuracy": r["validation"][key]
    d = [acc(x) - acc(o) for o, x in zip(a0, a1)]
    d_gold = [acc(x, "accuracy_gold_cards") - acc(o, "accuracy_gold_cards") for o, x in zip(a0, a1)]
    n = len(d)
    mean, sd = statistics.fmean(d), statistics.stdev(d)
    se = sd / math.sqrt(n)
    positive = sum(x > 0 for x in d)
    need = math.ceil(2 * n / 3)                                       # 2 of 3; 4 of 5 after the extension
    bar = mean - 2 * se > 0 and mean >= MIN_EFFECT and positive >= need
    g1 = statistics.fmean(d_gold) >= mean
    recalls = lambda runs: [r["validation"]["gold_recall_at_4"] for r in runs
                            if r["validation"]["gold_recall_at_4"] is not None]
    r0, r1 = recalls(a0), recalls(a1)
    recall0 = statistics.fmean(r0) if r0 else None
    recall1 = statistics.fmean(r1) if r1 else None
    g2 = recall0 is not None and recall1 is not None and recall1 >= RECALL_FLOOR * recall0   # unreadable: trips
    rows = sum(r["gates_own"]["gold"]["rows"] for r in a1)
    weighted = sum(r["gates_own"]["gold"]["mean"] * r["gates_own"]["gold"]["rows"] for r in a1
                   if r["gates_own"]["gold"]["rows"])
    gate_gold = weighted / rows if rows else None
    g3 = rows >= GATE_MIN_ROWS and gate_gold >= GATE_FLOOR
    at_chance = all(abs(x) < CHANCE_BAND and acc(o) <= o["chance"] + CHANCE_MARGIN
                    and acc(r) <= r["chance"] + CHANCE_MARGIN for x, o, r in zip(d, a0, a1))
    if not all(r["finite"] for r in a0 + a1):
        verdict = "DID NOT TRAIN"
    elif bar and not (g1 and g3):
        verdict = "GAIN NOT COUNTED (bypassed the cards: " + ", ".join(
            name for name, ok in (("G1", g1), ("G3", g3)) if not ok) + ")"
    elif bar and not g2:
        verdict = "NOT COUNTED (retrieval guard G2)"
    elif bar:
        verdict = "PASS"
    elif mean + 2 * se < 0:
        verdict = "PROVED WRONG"
    elif at_chance:
        verdict = "PROVED WRONG (both arms at chance in every seed)"
    else:
        verdict = "NOT SHOWN"
    extension_due = not bar and (-se < mean - 2 * se <= 0 or MIN_EFFECT - se <= mean < MIN_EFFECT)
    return {"d": d, "d_gold": d_gold, "mean_d": mean, "sd_d": sd, "lower": mean - 2 * se, "upper": mean + 2 * se,
            "seeds_positive": positive, "seeds_needed": need, "bar": bar,
            "G1": {"ok": g1, "mean_d_gold": statistics.fmean(d_gold), "mean_d": mean},
            "G2": {"ok": g2, "recall_A0": recall0, "recall_A1": recall1,
                   "floor": None if recall0 is None else RECALL_FLOOR * recall0},
            "G3": {"ok": g3, "gate_gold_own": gate_gold, "rows": rows, "min_rows": GATE_MIN_ROWS,
                   "floor": GATE_FLOOR},
            "both_at_chance": at_chance, "extension_due": extension_due, "verdict": verdict}


def score(runs: list[dict]) -> dict:
    by = {(r["arm"], r["seed"]): r for r in runs}
    seeds = sorted(s for s in {r["seed"] for r in runs} if ("A0", s) in by and ("A1", s) in by)
    if seeds[:3] != list(CARD_SEEDS) or seeds not in (list(CARD_SEEDS), list(CARD_SEEDS + EXTENSION_SEEDS)):
        return {"verdict": f"NOT SCORED: the card registers seeds {CARD_SEEDS} (+ {EXTENSION_SEEDS} by the extension "
                           f"rule), these runs have {tuple(seeds)}"}
    if len({json.dumps(r.get("identity"), sort_keys=True) for r in runs}) != 1:
        return {"verdict": "NOT SCORED: the runs come from different code (commit, runner, card or package hash)"}
    pick = lambda arm, chosen: [by[(arm, s)] for s in chosen]
    first = judge(pick("A0", CARD_SEEDS), pick("A1", CARD_SEEDS))
    if len(seeds) == len(CARD_SEEDS):
        if first["extension_due"]:
            first["verdict"] = f"EXTENSION DUE (run seeds {EXTENSION_SEEDS} once, then score seeds 0-4)"
        result = first
    elif not first["extension_due"]:
        return {"verdict": "NOT SCORED: seeds 3-4 were run but the 3-seed score did not call for the extension",
                "three_seed": first}
    else:
        result = judge(pick("A0", seeds), pick("A1", seeds))
        result["three_seed"] = first
        result["extension_due"] = False                               # once only
    result["seeds"] = seeds
    if runs[0]["settings"]["steps"] != CARD_SETTINGS["steps"] or runs[0]["settings"]["visits"] != CARD_SETTINGS["visits"]:
        result["verdict"] = "SMOKE, not the card's settings: " + result["verdict"]
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--steps", type=int, default=1500)
    parser.add_argument("--visits", type=int, default=16)
    parser.add_argument("--seeds", type=int, nargs="+", default=list(CARD_SEEDS))
    parser.add_argument("--arms", nargs="+", default=list(ARMS), choices=list(ARMS))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    torch.set_num_threads(1)
    settings = {"steps": args.steps, "visits": args.visits, "torch": torch.__version__}
    args.out.mkdir(parents=True, exist_ok=True)
    ident = identity()
    check_seal(args.out, ident)
    log_file = (args.out / "log.txt").open("a")

    def log(line: str) -> None:
        print(line, flush=True)
        log_file.write(line + "\n")
        log_file.flush()

    log(f"R2 stage 0 start {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} arms {args.arms} seeds {args.seeds} "
        f"settings {settings}")
    for seed in args.seeds:
        for arm in args.arms:
            path = args.out / f"{arm}-s{seed}.json"
            if path.exists():
                saved = json.loads(path.read_text())
                if saved.get("settings") != settings or saved.get("identity") != ident:
                    raise SystemExit(f"{path} was made with other settings or code; use a new --out")
                log(f"{arm} s{seed}: reusing {path.name}")
                continue
            write_json(path, run(arm, seed, settings, ident, log))
    runs = [json.loads(p.read_text()) for p in sorted(args.out.glob("A*-s*.json"))]
    if any(r.get("settings") != settings or r.get("identity") != ident for r in runs):
        raise SystemExit(f"{args.out} holds runs with other settings or code")
    result = score(runs)
    write_json(args.out / "result.json", {"settings": settings, "identity": ident, "score": result, "runs": runs})
    if "mean_d" in result:
        log(f"A1 vs A0: d {[round(x, 4) for x in result['d']]} mean {result['mean_d']:+.4f} "
            f"(2SE {result['lower']:+.4f}..{result['upper']:+.4f}) {result['seeds_positive']}/{len(result['d'])} positive; "
            f"G1 {result['G1']['ok']} G2 {result['G2']['ok']} G3 {result['G3']['ok']} "
            f"extension_due {result['extension_due']} -> {result['verdict']}")
    else:
        log(result["verdict"])
    log(f"R2 stage 0 end {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")


if __name__ == "__main__":
    main()
