"""Run card R2, stage 0 (design/steals-2026-10-17/R2-STAGE0-CARD.md, sealed): fetch_gate on the far-fact toy, CPU, $0.

Arms: A0 = D with every steal off; A1 = the same with `fetch_gate=True` (paired init: at a seed every shared weight
and the RNG stream are identical). Each run is the registered `train.train_toy("D", steps=1500, seed=s)` with AdamW.
The readout is accuracy, not time, so runs need no interleaving and may run in separate processes (`--arms`).

Primary: held-out toy accuracy with own retrieval (`validate` -> accuracy); d_s = acc(A1, s) - acc(A0, s).
Guards (sealed card): G1 gold-card gain >= own-retrieval gain (pooled); G2 recall@4(A1) >= 0.8 recall@4(A0) (pooled);
G3 mean card gate >= 0.2 on gold rows the model fetched itself in `answer()` (pooled; fewer than 30 rows is a trip).
The gates on preloaded gold cards (`answer_with_gold`) and the decoder cross-attention gate (one teacher-mode pass)
are reported. Exactly seeds 0-2, no extension (coordinator ruling 10-20). Every run is bound by content hash to the
runner, the card and the package (premonition/ and learnlab/; the commit is recorded, not binding); the seal holds all
three (the package as PACKAGE.sha256, a sha256sum-checkable file list beside the seal). A run made without the
matching seal (--unsealed) is labelled UNSEALED and never scored as the card; --score also refuses runs whose hashes or
seal differ from the current ones. Training never writes result.json; `--score` (no training) is its only writer.

    OMP_NUM_THREADS=1 python3 -B scripts/premonition_steals_r2_stage0.py --out artifacts/claude-steals-20261017/r2-stage0
    OMP_NUM_THREADS=1 python3 -B scripts/premonition_steals_r2_stage0.py --out artifacts/claude-steals-20261017/r2-stage0 --score
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

from learnlab.core import IGNORE_INDEX                                       # noqa: E402
from premonition import train as ptrain                                     # noqa: E402
from premonition.toy import ToySpec, toy_set                                 # noqa: E402

ARMS = {"A0": {}, "A1": {"fetch_gate": True}}
CARD_SEEDS = (0, 1, 2)
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


PACKAGE = "PACKAGE.sha256"                        # beside the seal: one sha256sum line per package file
SEAL = "SEAL.sha256.txt"


def package_listing() -> str:
    """The code a run executes, premonition/*.py and learnlab/**/*.py, as `sha256sum` lines (repo-relative paths)."""
    paths = sorted([*(ROOT / "premonition").glob("*.py"), *(ROOT / "learnlab").rglob("*.py")])
    return "".join(f"{sha256(path)}  {path.relative_to(ROOT).as_posix()}\n" for path in paths)


def identity() -> dict:
    """What a run is bound to, by content: the runner, the card and the package (the sha256 of its listing)."""
    return {"runner": sha256(Path(__file__).resolve()), "card": sha256(CARD),
            "package": hashlib.sha256(package_listing().encode()).hexdigest()}


def provenance() -> dict:
    """Recorded beside each run, never compared."""
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    return {"commit": commit or None, "torch": torch.__version__}


def check_seal(out: Path, ident: dict, unsealed: bool) -> bool:
    """True when `out` holds SEAL.sha256.txt matching this runner, card and package. Without a seal only --unsealed
    runs (labelled UNSEALED); a sealed directory never takes --unsealed, and a mismatch refuses to run."""
    seal = out / SEAL
    if not seal.exists():
        if not unsealed:
            raise SystemExit(f"{seal} is missing; pass --unsealed for a plumbing run (labelled UNSEALED)")
        return False
    if unsealed:
        raise SystemExit(f"{seal} exists: a sealed directory runs only the card, never --unsealed")
    sealed = {Path(line.split(maxsplit=1)[1]).name if line.split(maxsplit=1)[1].endswith(PACKAGE)
              else line.split(maxsplit=1)[1]: line.split()[0] for line in seal.read_text().splitlines()
              if len(line.split()) >= 2}
    want = {"design/steals-2026-10-17/R2-STAGE0-CARD.md": ident["card"],
            "scripts/premonition_steals_r2_stage0.py": ident["runner"], PACKAGE: ident["package"]}
    for name, digest in want.items():
        if sealed.get(name) != digest:
            raise SystemExit(f"{name} does not match the seal in {seal}; refusing to run")
    listing = out / PACKAGE
    if not listing.exists() or sha256(listing) != ident["package"]:
        raise SystemExit(f"{listing} is missing or is not the sealed package listing; refusing to run")
    return True


def seal_hash(out: Path):
    seal = out / SEAL
    return sha256(seal) if seal.exists() else None


def write_json(path: Path, value) -> None:
    """Atomic: a killed run never leaves a half-written result behind."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=1))
    os.replace(tmp, path)


@torch.no_grad()
def gate_means(model, batches: list, answer) -> dict:
    """Mean card gate on gold / wrong inserted rows, per head, over `answer` (`model.answer`: own fetches only;
    `train.answer_with_gold`: every told question's gold cards preloaded)."""
    think = model.think
    record = {"gold": [], "wrong": []}
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
    return {name: summary(parts, model.config.n_heads) for name, parts in record.items()}


def summary(parts: list, heads: int) -> dict:
    rows = torch.cat(parts) if parts else torch.zeros(0, heads)
    return {"rows": int(rows.shape[0]), "per_head": rows.mean(0).tolist() if rows.numel() else None,
            "mean": float(rows.mean()) if rows.numel() else None}


@torch.no_grad()
def cross_gate_means(model, batches: list) -> dict:
    """The decoder's cross-attention gate, per head, on real answer positions only (target not IGNORE_INDEX): one
    teacher-mode pass with 4 fixed loops, so every question decodes at every loop. Reported, not judged; no card
    hook is attached, so the teacher's forced cards never reach the G3 record."""
    record, current = [], {}

    def hook(_m, _a, out):
        real = current["real"]
        if out.shape[:2] != real.shape:
            raise RuntimeError(f"cross gate rows {tuple(out.shape[:2])} do not match the answers {tuple(real.shape)}")
        record.append(torch.sigmoid(out.float())[real])

    model.eval()
    handle = model.decoder.cross_gate.register_forward_hook(hook)
    try:
        for i, batch in enumerate(batches):
            answer = batch.answer
            length = int((answer != IGNORE_INDEX).sum(1).max().item())
            current["real"] = answer[:, :max(length, 1)] != IGNORE_INDEX          # as the model builds its targets
            model(batch, mode="teacher", loops=4, generator=torch.Generator().manual_seed(1234 + i))
    finally:
        handle.remove()
    return summary(record, model.config.n_heads)


def fmt(value, spec: str = ".4f") -> str:
    return "n/a" if value is None else format(value, spec)


def run(arm: str, seed: int, settings: dict, ident: dict, sealed: bool, seal) -> tuple:
    """(the run's record, its model). The gate readouts are added by `gates` after the record is saved."""
    started = time.perf_counter()
    trained = ptrain.train_toy("D", steps=settings["steps"], visits=settings["visits"], seed=seed,
                               config_overrides=ARMS[arm] or None)
    seconds = time.perf_counter() - started
    model, validation = trained["trainer"].model, trained["validation"]
    logged = [r for r in trained["history"] if "eval" not in r]
    last = logged[-1] if logged else {}             # no training record at all: every loss None, so not finite
    result = {"arm": arm, "seed": seed, "settings": settings, "identity": ident, "sealed": sealed, "seal": seal,
              "provenance": provenance(), "steps": trained["trainer"].step, "seconds": seconds,
              "parameters": trained["parameters"], "chance": trained["chance"],
              "final_losses": {k: last.get(k) for k in ("loss", "lm", "ask", "ans", "halt")},
              "validation": {k: validation.get(k) for k in (
                  "accuracy", "accuracy_gold_cards", "gold_recall_at_4", "random_recall_at_4", "asked_rate",
                  "loops_mean", "halt_rate", "questions")}}
    losses = [v for v in result["final_losses"].values() if v is not None]
    result["finite"] = bool(losses) and all(isinstance(v, float) and math.isfinite(v) for v in losses)
    return result, model


def gates(result: dict, model) -> dict:
    """A1's gate readouts on the held-out batches; G3 reads `gates_own`."""
    spec = ToySpec()
    held_out = [ptrain.label_free(b) for b in toy_set(spec, 4, result["settings"]["visits"], result["seed"] + 1000)]
    return {"gates_own": gate_means(model, held_out, model.answer),                                    # G3
            "gates_preload": gate_means(model, held_out, lambda b: ptrain.answer_with_gold(model, b)),  # reported
            "gates_cross": cross_gate_means(model, held_out)}                                           # reported


def describe(result: dict) -> str:
    """One log line; every value may be None."""
    v = result["validation"]
    return (f"{result['arm']} s{result['seed']}: steps {result['steps']} {result['seconds']:.0f}s "
            f"acc {fmt(v.get('accuracy'))} gold {fmt(v.get('accuracy_gold_cards'))} "
            f"recall {fmt(v.get('gold_recall_at_4'), '.3f')}")


def judge(a0: list[dict], a1: list[dict]) -> dict:
    """The card's bar, guards and verdict on paired runs (same seeds, same order)."""
    acc = lambda r, key="accuracy": r["validation"][key]
    d = [acc(x) - acc(o) for o, x in zip(a0, a1)]
    d_gold = [acc(x, "accuracy_gold_cards") - acc(o, "accuracy_gold_cards") for o, x in zip(a0, a1)]
    n = len(d)
    mean, sd = statistics.fmean(d), statistics.stdev(d)
    se = sd / math.sqrt(n)
    positive = sum(x > 0 for x in d)
    need = math.ceil(2 * n / 3)                                       # 2 of 3
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
    return {"d": d, "d_gold": d_gold, "mean_d": mean, "sd_d": sd, "lower": mean - 2 * se, "upper": mean + 2 * se,
            "seeds_positive": positive, "seeds_needed": need, "bar": bar,
            "G1": {"ok": g1, "mean_d_gold": statistics.fmean(d_gold), "mean_d": mean},
            "G2": {"ok": g2, "recall_A0": recall0, "recall_A1": recall1,
                   "floor": None if recall0 is None else RECALL_FLOOR * recall0},
            "G3": {"ok": g3, "gate_gold_own": gate_gold, "rows": rows, "min_rows": GATE_MIN_ROWS,
                   "floor": GATE_FLOOR},
            "both_at_chance": at_chance, "verdict": verdict}


def score(runs: list[dict], *, sealed: bool, ident: dict | None = None, seal=None) -> dict:
    """Exactly one run of each arm at each of seeds 0-2, every run made by this sealed runner, card and package (and,
    sealed, under this seal), one torch version, and A1's gate readouts present; otherwise NOT SCORED. DID NOT TRAIN
    wins over every other outcome. A smoke (any run off the card's settings) or an unsealed directory or run labels
    whatever verdict comes out, DID NOT TRAIN included, and a labelled verdict is never the card's."""
    by = {(r["arm"], r["seed"]): r for r in runs}
    blockers = []
    if len(by) != len(runs) or sorted(by) != sorted((arm, s) for arm in ARMS for s in CARD_SEEDS):
        blockers.append(f"the card needs exactly one run of each arm at seeds {CARD_SEEDS}, these are {sorted(by)}")
    if len({json.dumps(r.get("identity"), sort_keys=True) for r in runs}) != 1:
        blockers.append("the runs come from different code (runner, card or package hash)")
    elif ident is not None and runs and runs[0].get("identity") != ident:
        blockers.append("the runs were made by other code than the current runner, card and package")
    if sealed and any(r.get("seal") != seal for r in runs):
        blockers.append("runs made under another seal or in another directory")
    if len({r["settings"].get("torch") for r in runs}) > 1:
        blockers.append("runs made under different torch versions")
    missing = [f"A1-s{r['seed']}" for r in runs if r["arm"] == "A1" and "gates_own" not in r]
    if missing:
        blockers.append(f"gate readouts missing for {missing}")
    labels = []
    if not sealed or not all(r.get("sealed") for r in runs):
        labels.append("UNSEALED")
    if any({k: r["settings"].get(k) for k in CARD_SETTINGS} != CARD_SETTINGS for r in runs):
        labels.append("SMOKE, not the card's settings")
    prefix = "".join(f"{label}: " for label in labels)
    if not all(r["finite"] for r in runs):            # first, whatever else is wrong; still labelled
        verdict = prefix + "DID NOT TRAIN"
        if blockers:
            verdict += " (and NOT SCORED: " + "; ".join(blockers) + ")"
        return {"verdict": verdict, "non_finite": sorted(f"{r['arm']}-s{r['seed']}" for r in runs if not r["finite"])}
    if blockers:
        return {"verdict": prefix + "NOT SCORED: " + "; ".join(blockers)}
    result = judge([by[("A0", s)] for s in CARD_SEEDS], [by[("A1", s)] for s in CARD_SEEDS])
    result["seeds"] = list(CARD_SEEDS)
    result["verdict"] = prefix + result["verdict"]
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--steps", type=int, default=CARD_SETTINGS["steps"])
    parser.add_argument("--visits", type=int, default=CARD_SETTINGS["visits"])
    parser.add_argument("--seeds", type=int, nargs="+", default=list(CARD_SEEDS), choices=list(CARD_SEEDS))
    parser.add_argument("--arms", nargs="+", default=list(ARMS), choices=list(ARMS))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--unsealed", action="store_true", help="plumbing runs without a seal, labelled UNSEALED")
    parser.add_argument("--score", action="store_true", help="train nothing; score the runs and write result.json")
    args = parser.parse_args()
    torch.set_num_threads(1)
    settings = {"steps": args.steps, "visits": args.visits, "torch": torch.__version__}
    args.out.mkdir(parents=True, exist_ok=True)
    ident = identity()
    sealed = check_seal(args.out, ident, args.unsealed)
    seal = seal_hash(args.out)
    if sealed and not args.score and {k: settings[k] for k in CARD_SETTINGS} != CARD_SETTINGS:
        raise SystemExit(f"{args.out} is sealed: it takes only the card's settings {CARD_SETTINGS}")
    log_file = (args.out / "log.txt").open("a")

    def log(line: str) -> None:
        print(line, flush=True)
        log_file.write(line + "\n")
        log_file.flush()

    if args.score:                                   # the only writer of result.json
        runs = [json.loads(p.read_text()) for p in sorted(args.out.glob("A*-s*.json"))]
        result = score(runs, sealed=sealed, ident=ident, seal=seal)
        write_json(args.out / "result.json", {"identity": ident, "sealed": sealed, "score": result, "runs": runs})
        if "mean_d" in result:
            log(f"A1 vs A0: d {[round(x, 4) for x in result['d']]} mean {result['mean_d']:+.4f} "
                f"(2SE {result['lower']:+.4f}..{result['upper']:+.4f}) {result['seeds_positive']}/{len(result['d'])} "
                f"positive; G1 {result['G1']['ok']} G2 {result['G2']['ok']} G3 {result['G3']['ok']} -> "
                f"{result['verdict']}")
        else:
            log(result["verdict"])
        return
    log(f"R2 stage 0 start {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} arms {args.arms} seeds {args.seeds} "
        f"settings {settings} {'sealed' if sealed else 'UNSEALED'}")
    for seed in args.seeds:
        for arm in args.arms:
            path = args.out / f"{arm}-s{seed}.json"
            if path.exists():
                saved = json.loads(path.read_text())
                if saved.get("settings") != settings or saved.get("identity") != ident or \
                        saved.get("sealed") != sealed or saved.get("seal") != seal:
                    raise SystemExit(f"{path} was made with other settings, code or seal; use a new --out")
                log(f"{arm} s{seed}: reusing {path.name}")
                continue
            result, model = run(arm, seed, settings, ident, sealed, seal)
            write_json(path, result)                 # saved before anything can fail on its values
            log(describe(result))
            if arm == "A1":
                try:
                    result.update(gates(result, model))
                except Exception as error:           # the trained run stays saved; scoring reports the gap
                    result["gates_error"] = f"{type(error).__name__}: {error}"
                    log(f"{arm} s{seed}: gate readout failed: {result['gates_error']}")
                write_json(path, result)
    log(f"R2 stage 0 end {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}; score with --score")


if __name__ == "__main__":
    main()
