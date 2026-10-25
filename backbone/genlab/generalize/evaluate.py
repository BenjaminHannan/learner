"""Breakdown evaluator for the generalization gap (design/generalize/PASSMARKS.md).

Scores one D checkpoint on every probe directory plus `validation` and `dev`, with the SAME metric as the V1 run's
final evaluation (`premonition.train.validate`: greedy answer, exact match through `judge`; the label-free v2 cache),
and writes JSON and a markdown table: per-set accuracy, per-question breakdowns (depth, qtype, number of rule
families, R8 involved, style status, name answer, knowable) and the gap attribution
    drop(X) = acc(P0) - acc(PX),   G = acc(P0) - acc(validation).

  python3 -m generalize.evaluate CKPT --root DATA_ROOT [--probes PROBE_ROOT] [--out DIR] [--b2 B2.pt]
                                 [--extra-loops K] [--max-visits N] [--sets dev,validation,P0,...]

DATA_ROOT holds train/ (the name detector is fitted on it), dev/ and validation/ as `v1/split_dirs.py` lays them out.
PROBE_ROOT (default DATA_ROOT) holds the probe directories of `generalize.probes` (found by their manifests).
CKPT is either a v1 arm `D-final.pt` (with a "bridge": needs --b2, the creative parent, exactly as v1/sealed_read.py)
or a D-only checkpoint (a dict with "model" and "config"). The sealed `test` split is never listed or opened.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

import torch

REPO = Path(__file__).resolve().parent.parent
DEFAULT_TOKENIZER = REPO / "data/tokenizer/premonition-tok-v2.json"
MAX_TOKENS, MAX_VISITS = 55_000, 48          # v1.run.make_eval_batches
FORBIDDEN = ("test",)                         # sealed
PROBE_ORDER = ("P0", "Pname", "Pword", "Pstyle", "Pdepth", "Prule", "Pall")
DIMENSIONS = ("depth", "qtype", "n_families", "r8", "style_status", "name_answer", "knowable")


class PlainBudget:
    """What `premonition.data` needs of a Budget (root and atomic_write) without scanning the tree."""

    def __init__(self, root: os.PathLike) -> None:
        self.root = Path(root).resolve()

    def atomic_write(self, relative: str, size: int, writer: Callable) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(f"{path.name}.tmp-{os.getpid()}")
        with open(temp, "wb") as handle:
            writer(handle)
        os.replace(temp, path)
        return path


# ------------------------------------------------------------------------------------------------ checkpoints
def load_d(path: os.PathLike, device: str = "cpu", b2: Optional[str] = None,
           creative_loader: Optional[Callable[[str, str], Any]] = None) -> tuple[Any, dict[str, Any]]:
    """(model in eval mode, info). A bridge checkpoint needs `b2`; the bridge is attached with frozen summaries."""
    from premonition.model import PremonitionMini
    from premonition.train import mini_config_from
    saved = torch.load(path, map_location=device, weights_only=False)
    if not isinstance(saved, Mapping) or "model" not in saved or "config" not in saved:
        raise ValueError(f"{path} is not a D checkpoint: expected a dict with 'model' and 'config' (v1 D-final.pt or D-only)")
    model = PremonitionMini(mini_config_from(saved["config"])).to(device)
    model.load_state_dict(saved["model"])
    info: dict[str, Any] = {"kind": "d-only", "arm": saved.get("arm"), "steps": saved.get("steps")}
    if saved.get("bridge") is not None:
        if not b2:
            raise SystemExit(f"REFUSED: {path} carries a bridge (a v1 arm D-final.pt). Its D was trained with the creative "
                             f"parent attached; pass --b2 PATH to the creative B2 checkpoint (as v1/sealed_read.py does).")
        from v1.joint import Bridge
        if creative_loader is None:
            from v1 import run as vrun
            creative_loader = lambda p, dev: vrun.load_creative(p, dev)[0]
        creative = creative_loader(b2, device)
        bridge = Bridge(model.config.d_model, creative.d).to(device).attach(model, creative)
        bridge.load_state_dict({k: v for k, v in saved["bridge"].items() if not k.startswith(("_d.", "_c."))})
        bridge.frozen_ctx = True
        info.update(kind="bridge", b2=str(b2))
        model.__dict__["_bridge_keepalive"] = bridge
    model.eval()
    return model, info


# ------------------------------------------------------------------------------------------------ data
def discover(root: os.PathLike, extra_root: Optional[os.PathLike] = None) -> dict[str, Path]:
    """Evaluation directories by name: dev and validation under `root`, probes (by manifest) under `extra_root`/`root`."""
    found: dict[str, Path] = {}
    for base in dict.fromkeys(Path(r) for r in (root, extra_root) if r):
        for child in sorted(base.iterdir()):
            if not (child / "manifest.json").is_file() or child.name in FORBIDDEN or not any(child.glob("shard-*.txt")):
                continue
            manifest = json.loads((child / "manifest.json").read_text(encoding="utf-8"))
            if manifest.get("split") == "test" or manifest.get("axes", {}) and "test" in manifest["axes"].values():
                continue
            if child.name in ("dev", "validation") or "probe" in manifest:
                found.setdefault(child.name, child)
    return found


def ordered(names: Sequence[str]) -> list[str]:
    head = [n for n in ("dev", "validation") if n in names]
    probes = [n for n in PROBE_ORDER if n in names]
    rest = sorted(n for n in names if n not in head and n not in probes)
    return head + probes + rest


def question_meta(directory: Path) -> dict[str, dict[str, Any]]:
    meta: dict[str, dict[str, Any]] = {}
    for shard in sorted(directory.glob("shard-*.jsonl")):
        for line in shard.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                if row.get("kind", "question") == "question":
                    meta[row["id"]] = row
    return meta


def derive(row: Mapping[str, Any], styles: Mapping[str, str], names: frozenset) -> dict[str, Any]:
    fams = list(row.get("families") or [])
    return {
        "depth": str(row.get("depth")), "qtype": row.get("base_qtype", row.get("qtype")),
        "n_families": str(min(len(fams), 2)) if len(fams) < 2 else "2+", "r8": "R8" in fams,
        "style_status": styles.get(row.get("style"), "none") if row.get("style") else "none",
        "name_answer": str(row.get("answer")) in names, "knowable": bool(row.get("knowable", True)),
    }


# ------------------------------------------------------------------------------------------------ scoring
@torch.no_grad()
def score_cache(model: Any, cache: Any, tokenizer: Any, *, max_visits: Optional[int] = None, extra_loops: int = 0,
                device: str = "cpu", max_tokens: int = MAX_TOKENS, max_batch_visits: int = MAX_VISITS) -> dict[str, dict[str, Any]]:
    """question id -> {correct, loops, prediction}, batched and judged exactly as `premonition.train.validate` does."""
    from learnlab import step1
    from premonition import data as pdata
    from premonition.train import judge
    chosen = list(range(min(max_visits, len(cache)) if max_visits else len(cache)))
    groups = pdata.length_batches(cache.lengths[chosen].tolist(), max_tokens, max_visits=max_batch_visits)
    stops = sorted(step1.stop_ids(tokenizer)[0])
    kwargs = {"extra_loops": extra_loops} if extra_loops else {}
    out: dict[str, dict[str, Any]] = {}
    for group in groups:
        batch = pdata.collate(cache, [chosen[i] for i in group]).to(device)
        if batch.q_visit.shape[0] == 0:
            continue
        answers = model.answer(batch, stop=stops, **kwargs)
        correct, texts = judge(answers, batch, tokenizer=tokenizer, stop=stops, eos=model.config.eos_id)
        for qid, ok, text, loops in zip(batch.question_ids, correct, texts, answers.loops.tolist()):
            out[qid] = {"correct": bool(ok), "loops": int(loops), "prediction": text}
    return out


def tabulate(scores: Mapping[str, Mapping[str, Any]], meta: Mapping[str, Mapping[str, Any]], styles, names) -> dict[str, Any]:
    n = len(scores)
    correct = sum(s["correct"] for s in scores.values())
    cells: dict[str, dict[str, list[int]]] = {d: defaultdict(lambda: [0, 0]) for d in DIMENSIONS}
    for qid, s in scores.items():
        for dim, value in derive(meta[qid], styles, names).items():
            cell = cells[dim][str(value)]
            cell[0] += s["correct"]
            cell[1] += 1
    key = lambda v: (0, int(v)) if v.lstrip("-").isdigit() else (1, v)
    return {
        "questions": n, "correct": correct, "accuracy": correct / n if n else None,
        "loops_mean": sum(s["loops"] for s in scores.values()) / n if n else None,
        "breakdown": {dim: {v: {"n": c[1], "correct": c[0], "accuracy": c[0] / c[1]} for v, c in sorted(cells[dim].items(), key=lambda kv: key(kv[0]))}
                      for dim in DIMENSIONS},
    }


def attribution(sets: Mapping[str, Mapping[str, Any]]) -> Optional[dict[str, Any]]:
    """PASSMARKS.md: drop(X) = acc(P0) - acc(PX), G = acc(P0) - acc(validation); bottleneck if drop >= G/2."""
    if "P0" not in sets or "validation" not in sets:
        return None
    p0, val = sets["P0"]["accuracy"], sets["validation"]["accuracy"]
    gap = p0 - val
    drops = {}
    for name in ("Pname", "Pword", "Pstyle", "Pdepth", "Prule"):
        if name in sets:
            d = p0 - sets[name]["accuracy"]
            drops[name] = {"acc": sets[name]["accuracy"], "drop": d, "share_of_gap": d / gap if gap > 0 else None,
                           "bottleneck": bool(gap > 0 and d >= gap / 2), "reaches_quarter": bool(gap > 0 and d >= gap / 4)}
    out = {"acc_P0": p0, "acc_validation": val, "G": gap, "drops": drops,
           "sum_of_drops": sum(v["drop"] for v in drops.values()),
           "bottlenecks": [k for k, v in drops.items() if v["bottleneck"]]}
    if "Pall" in sets:
        out["acc_Pall"] = sets["Pall"]["accuracy"]
        out["Pall_minus_validation"] = sets["Pall"]["accuracy"] - val
    if gap <= 0:
        out["verdict"] = "no gap (G <= 0): nothing to attribute"
    elif out["bottlenecks"]:
        out["verdict"] = "bottleneck: " + ", ".join(out["bottlenecks"])
    elif not any(v["reaches_quarter"] for v in drops.values()):
        out["verdict"] = "WRONG-IF triggered: no single drop reaches G/4 (gap spread evenly or an interaction)"
    else:
        out["verdict"] = "no single bottleneck (no drop >= G/2); at least one drop reaches G/4"
    return out


# ------------------------------------------------------------------------------------------------ markdown
def _pct(cell: Optional[Mapping[str, Any]]) -> str:
    return "-" if not cell or not cell["n"] else f"{100 * cell['accuracy']:.1f} ({cell['n']})"


def to_markdown(report: Mapping[str, Any]) -> str:
    sets = report["sets"]
    names = list(sets)
    lines = [f"# Generalization breakdown: {report['checkpoint']}", "",
             f"kind {report['info']['kind']}; extra loops {report['extra_loops']}; max visits {report['max_visits']}", "",
             "## Accuracy per set", "", "| set | questions | accuracy % | mean loops |", "|---|---|---|---|"]
    for n in names:
        s = sets[n]
        acc = "-" if s["accuracy"] is None else f"{100 * s['accuracy']:.2f}"
        lines.append(f"| {n} | {s['questions']} | {acc} | {s['loops_mean']:.2f} |" if s["questions"] else f"| {n} | 0 | - | - |")
    att = report.get("attribution")
    if att:
        lines += ["", "## Gap attribution", "",
                  f"acc(P0) {100 * att['acc_P0']:.2f}, acc(validation) {100 * att['acc_validation']:.2f}, "
                  f"G = {100 * att['G']:.2f} points", "",
                  "| probe | acc % | drop (points) | share of G | >= G/2 | >= G/4 |", "|---|---|---|---|---|---|"]
        for k, v in att["drops"].items():
            share = "-" if v["share_of_gap"] is None else f"{100 * v['share_of_gap']:.0f}%"
            lines.append(f"| {k} | {100 * v['acc']:.2f} | {100 * v['drop']:.2f} | {share} | {v['bottleneck']} | {v['reaches_quarter']} |")
        lines += ["", f"sum of single drops {100 * att['sum_of_drops']:.2f} points. Verdict: **{att['verdict']}**"]
        if "acc_Pall" in att:
            lines.append(f"Pall {100 * att['acc_Pall']:.2f} vs validation {100 * att['acc_validation']:.2f} "
                         f"(difference {100 * att['Pall_minus_validation']:+.2f}).")
    for dim in DIMENSIONS:
        values = sorted({v for n in names if sets[n]["questions"] for v in sets[n]["breakdown"][dim]},
                        key=lambda v: (0, int(v)) if v.lstrip("-").isdigit() else (1, v))
        lines += ["", f"## By {dim} (accuracy % (questions))", "", "| " + dim + " | " + " | ".join(names) + " |",
                  "|---|" + "---|" * len(names)]
        for v in values:
            lines.append(f"| {v} | " + " | ".join(_pct(sets[n]["breakdown"][dim].get(v)) if sets[n]["questions"] else "-" for n in names) + " |")
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------------------------------------ driver
def evaluate(checkpoint: os.PathLike, root: os.PathLike, *, probes_root: Optional[os.PathLike] = None,
             b2: Optional[str] = None, extra_loops: int = 0, max_visits: Optional[int] = None,
             sets: Optional[Sequence[str]] = None, tokenizer_path: os.PathLike = DEFAULT_TOKENIZER, device: str = "cpu",
             workers: int = 1, log: Callable[[str], None] = print,
             creative_loader: Optional[Callable[[str, str], Any]] = None) -> dict[str, Any]:
    from learnlab.tokenizer import Tokenizer
    from learnlab.village.names import all_names
    from learnlab.village.scheduler import style_assignment
    from premonition import data as pdata, preprocess
    root = Path(root).resolve()
    if not (root / "train").is_dir():
        raise SystemExit(f"{root}/train is missing: the name detector is fitted on the TRAIN directory")
    model, info = load_d(checkpoint, device, b2, creative_loader)
    tok = Tokenizer.load(Path(tokenizer_path))
    if model.config.vocab_size != tok.vocab_size:
        raise SystemExit(f"checkpoint vocab {model.config.vocab_size} != tokenizer vocab {tok.vocab_size} ({tokenizer_path})")
    dirs = discover(root, probes_root)
    wanted = ordered([n for n in dirs if sets is None or n in sets])
    for n in sets or ():
        if n in FORBIDDEN:
            raise SystemExit("the sealed test split is never evaluated here")
        if n not in dirs:
            log(f"note: set {n!r} not found under {root}{'' if not probes_root else ' or ' + str(probes_root)}; skipped")
    if not wanted:
        raise SystemExit("no evaluation sets found")
    detector = pdata.name_detector(PlainBudget(root.parent), root.name, workers=workers, log=log)   # fitted on TRAIN only
    styles, names = style_assignment(), frozenset(all_names())
    out_sets: dict[str, Any] = {}
    for name in wanted:
        directory = dirs[name]
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        split = "train" if name == "dev" else manifest.get("split") or None
        base = PlainBudget(directory.parent.parent)   # caches live in <root>/premonition-v2-*/<name>.pt, as v1/dtrain.py
        cache = pdata.load_or_build(base, directory.parent.name, name, tok, detector, split=split, workers=workers,
                                    regime=preprocess.LABEL_FREE, log=log)
        started = time.perf_counter()
        scores = score_cache(model, cache, tok, max_visits=max_visits, extra_loops=extra_loops, device=device)
        meta = question_meta(directory)
        out_sets[name] = {**tabulate(scores, meta, styles, names), "directory": str(directory), "split_label": split,
                          "seconds": time.perf_counter() - started}
        out_sets[name]["probe"] = {k: manifest.get(k) for k in ("probe", "switched", "seed", "axes", "knobs", "families") if k in manifest}
        log(f"{name}: {out_sets[name]['questions']} questions, accuracy {100 * (out_sets[name]['accuracy'] or 0):.2f}%")
    report = {"checkpoint": str(checkpoint), "info": info, "extra_loops": extra_loops, "max_visits": max_visits,
              "root": str(root), "probes_root": str(probes_root) if probes_root else None,
              "tokenizer": str(tokenizer_path), "sets": out_sets, "attribution": attribution(out_sets)}
    return report


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("checkpoint")
    ap.add_argument("--root", required=True, help="data root with train/, dev/, validation/")
    ap.add_argument("--probes", default=None, help="directory holding the probe dirs (default: --root)")
    ap.add_argument("--out", default=None, help="output directory (default: ./generalize-out)")
    ap.add_argument("--b2", default=None, help="creative B2 checkpoint (required for a v1 arm D-final.pt with a bridge)")
    ap.add_argument("--extra-loops", type=int, default=0, help="keep thinking this many loops after the first HALT")
    ap.add_argument("--max-visits", type=int, default=None, help="score only the first N visits of each set (quick run)")
    ap.add_argument("--sets", default=None, help="comma list, e.g. dev,validation,P0,Pdepth")
    ap.add_argument("--tokenizer", default=str(DEFAULT_TOKENIZER))
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--workers", type=int, default=1)
    a = ap.parse_args(argv)
    report = evaluate(a.checkpoint, a.root, probes_root=a.probes, b2=a.b2, extra_loops=a.extra_loops, max_visits=a.max_visits,
                      sets=[s for s in a.sets.split(",") if s] if a.sets else None, tokenizer_path=a.tokenizer,
                      device=a.device, workers=a.workers)
    out = Path(a.out or "generalize-out")
    out.mkdir(parents=True, exist_ok=True)
    stem = Path(a.checkpoint).stem + (f"-loops{a.extra_loops}" if a.extra_loops else "")
    (out / f"{stem}.json").write_text(json.dumps(report, indent=1, default=float) + "\n")
    md = to_markdown(report)
    (out / f"{stem}.md").write_text(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
