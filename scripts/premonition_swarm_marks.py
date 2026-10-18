"""Swarm screen readout (design/swarm/BOX-SPEC.md): every mark of RUNCARD-S0 or RUNCARD-S1 from the runner's JSON.

    python -B scripts/premonition_swarm_marks.py --card S0 --dir OUTPUTS --out MARKS-S0.json
    python -B scripts/premonition_swarm_marks.py --card S1 --dir OUTPUTS --out MARKS-S1.json

Input files in --dir: `c0.json`, `train-{arm}-s{seed}.json`, `eval-{arm}-s{seed}.json` and, for S1,
`eval-S1-s{seed}-{lesion}.json`; seeds 0, 1, 2. Writes the JSON and, next to it, the human `.md` (one table row
per mark, then one VERDICT line).

Cell membership. `premonition.exp1.slice_report` puts a scored item in decision cell `name` exactly when `name`
is in the item's `slices` list (`slices.SliceTags.slices()`: an excluded item, i.e. a repeat or leak-class one, is
in "excluded" only, so no decision cell holds it). The readout rebuilds every decision cell, every per-depth cell
and the `changed` cell from the items, and ASSERTS hits and n against the file's own `summary.decision_cells`,
`summary.per_depth` and `summary.cells`. Any mismatch is VOID (schema).

Pure Python (no torch): the constants below are checked against the library by the unit tests.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from fractions import Fraction
import json
import math
from pathlib import Path
import sys
from typing import Any, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from learnlab.metrics import paired_greater_pvalue  # noqa: E402

DECISION_CELLS = ("overall", "near", "far", "far_deep", "multi_hop")      # premonition.slices.DECISION_SLICES
DEPTHS = (1, 2, 3, 4, 5, 6)                                               # premonition.slices.DEPTHS
ALPHA = 0.01                                                              # learnlab.policy.ALPHA
MARGIN = Fraction(3, 100)                                                 # learnlab.policy.MIN_EFFECT
MIN_ITEMS = 100                                                           # learnlab.policy.MIN_ITEMS
SECONDS_TOL = 0.02                                                        # M5: train seconds within T +- 2%
COLLAPSE_COS, COLLAPSE_OVERLAP = 0.95, 0.8                                # premonition.swarm
ASK_FLOOR, FETCH_FLOOR = 0.05, 0.10                                       # M3 desk usage
SEEDS = (0, 1, 2)
LESIONS = ("board", "notes", "cards")
EXPECTED_SWARM = {"D1": None,
                  "S0": dict(thinkers=4, swarm_board=False, swarm_rounds=4, board_cards=16),
                  "S1": dict(thinkers=4, swarm_board=True, swarm_rounds=4, board_cards=16)}
COLLAPSED_TEXT = "COLLAPSED: the desks are copies"
BOARD_COLLAPSED_TEXT = "the board collapsed the desks"
CARD_ARMS = {"S0": ("D1", "S0"), "S1": ("D1", "S0", "S1")}


# ------------------------------------------------------------------ small helpers
def num(value: Any) -> float:
    """A JSON number, or NaN for None / "nan" / "inf" strings (exp1.jsonable writes non-finite floats as text)."""
    try:
        out = float(value)
    except (TypeError, ValueError):
        return math.nan
    return out


def finite(value: Any) -> bool:
    return math.isfinite(num(value))


def pct(value: Optional[float]) -> str:
    return "n/a" if value is None else f"{100 * value:.1f}"


def points(value: Optional[Fraction]) -> str:
    return "n/a" if value is None else f"{100 * float(value):+.2f}"


def is_collapsed(cos: float, overlap: float) -> bool:
    return bool(cos > COLLAPSE_COS and overlap > COLLAPSE_OVERLAP)


# ------------------------------------------------------------------ loading
@dataclass
class Eval:
    path: str
    arm: str
    seed: int
    lesion: Optional[str]
    split: str
    tag: Any
    tokenizer_sha: Any
    items: dict[str, tuple[int, tuple[str, ...]]]
    cells: dict[str, tuple[int, int]]                 # name -> (hits, n), recomputed from the items
    swarm: Optional[dict[str, Any]]

    def cell(self, name: str) -> tuple[int, int]:
        return self.cells.get(name, (0, 0))


@dataclass
class Context:
    directory: Path
    seeds: tuple[int, ...]
    min_items: int
    seconds_tol: float
    card: str = ""
    void: list[str] = field(default_factory=list)          # VOID reasons (schema, validity, missing files)
    insufficient: list[str] = field(default_factory=list)
    checked_pairs: set = field(default_factory=set)
    evals: dict[tuple[str, int, Optional[str]], Eval] = field(default_factory=dict)
    trains: dict[tuple[str, int], dict[str, Any]] = field(default_factory=dict)
    c0: Optional[dict[str, Any]] = None


def read_json(ctx: Context, name: str) -> Optional[dict[str, Any]]:
    path = ctx.directory / name
    if not path.is_file():
        ctx.void.append(f"missing: file {name}")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        ctx.void.append(f"schema: {name} is not valid JSON ({error})")
        return None


def expected_mini(arm: str) -> dict[str, Any]:
    swarm = EXPECTED_SWARM[arm]
    return {"thinkers": 1, "swarm_board": False} if swarm is None else {
        "thinkers": swarm["thinkers"], "swarm_board": swarm["swarm_board"]}


def load_eval(ctx: Context, arm: str, seed: int, lesion: Optional[str]) -> Optional[Eval]:
    name = f"eval-{arm}-s{seed}" + (f"-{lesion}" if lesion else "") + ".json"
    report = read_json(ctx, name)
    if report is None:
        return None
    problems: list[str] = []
    try:
        split = report["split"]
        items_raw = report["items"][split]
        directory = report["directories"][split]
        summary = directory["summary"]
        tag, sha = report["data"]["tag"], report["tokenizer"]["sha256"]
    except (KeyError, TypeError) as error:
        ctx.void.append(f"schema: {name} lacks {error}")
        return None
    if report.get("lesion") != lesion:
        problems.append(f"lesion is {report.get('lesion')!r}, expected {lesion!r}")
    if split != "validation":
        problems.append(f"split is {split!r}, not 'validation'")
    ckpt = str(report.get("checkpoint", "")).rstrip("/\\")
    if not ckpt.endswith(f"{arm}-s{seed}"):
        problems.append(f"checkpoint {ckpt!r} is not the {arm}-s{seed} checkpoint")
    mini = (report.get("config") or {}).get("mini") or {}
    for key, want in expected_mini(arm).items():
        if mini.get(key) != want:
            problems.append(f"checkpoint config {key} = {mini.get(key)!r}, expected {want!r} for {arm}")
    items: dict[str, tuple[int, tuple[str, ...]]] = {}
    for row in items_raw:
        try:
            rid, correct, slices_, decision = row["id"], row["correct"], tuple(row["slices"]), row["decision"]
        except (KeyError, TypeError) as error:
            problems.append(f"item without {error}")
            break
        if rid in items:
            problems.append(f"duplicate item id {rid}")
        if bool(decision) != ("overall" in slices_):
            problems.append(f"item {rid}: decision flag {decision!r} disagrees with its slices {list(slices_)}")
        items[rid] = (int(bool(correct)), slices_)
    names = list(DECISION_CELLS) + [f"depth_{d}" for d in DEPTHS] + ["changed"]
    cells: dict[str, tuple[int, int]] = {}
    for cell in names:
        members = [hit for hit, slices_ in items.values() if cell in slices_]
        cells[cell] = (sum(members), len(members))

    def check(label: str, theirs: Any, mine: tuple[int, int]) -> None:
        hits, n = mine
        want_acc = hits / n if n else None
        if (not isinstance(theirs, dict) or theirs.get("n") != n or theirs.get("hits") != hits
                or theirs.get("accuracy") != want_acc):
            problems.append(f"cell {label}: file says {theirs and {k: theirs.get(k) for k in ('n', 'hits', 'accuracy')}}"
                            f", recomputed hits {hits} n {n} accuracy {want_acc}")

    for cell in DECISION_CELLS:
        check(cell, (summary.get("decision_cells") or {}).get(cell), cells[cell])
    for depth in DEPTHS:
        check(f"depth_{depth}", (summary.get("per_depth") or {}).get(str(depth)), cells[f"depth_{depth}"])
    all_cells = summary.get("cells") or {}
    if "changed" in all_cells or cells["changed"][1]:
        check("changed", all_cells.get("changed"), cells["changed"])
    if summary.get("items") != len(items):
        problems.append(f"summary.items {summary.get('items')} != {len(items)} items")
    swarm = (directory.get("retrieval") or {}).get("swarm")
    if arm != "D1":
        need = ("ask_rate", "fetch_count", "register_cos", "fetch_overlap", "collapsed", "silent_desks")
        if not isinstance(swarm, dict) or any(key not in swarm for key in need):
            problems.append("directories.validation.retrieval.swarm is missing or incomplete")
            swarm = None
    if problems:
        ctx.void.append(f"schema: {name}: " + "; ".join(problems[:6]) + (" ..." if len(problems) > 6 else ""))
    found = Eval(path=name, arm=arm, seed=seed, lesion=lesion, split=split, tag=tag, tokenizer_sha=sha,
                 items=items, cells=cells, swarm=swarm)
    ctx.evals[(arm, seed, lesion)] = found
    return found


def load_train(ctx: Context, arm: str, seed: int) -> Optional[dict[str, Any]]:
    report = read_json(ctx, f"train-{arm}-s{seed}.json")
    if report is not None:
        ctx.trains[(arm, seed)] = report
    return report


# ------------------------------------------------------------------ paired comparisons
def check_pair(ctx: Context, a: Eval, b: Eval) -> None:
    key = tuple(sorted([a.path, b.path]))
    if key in ctx.checked_pairs:
        return
    ctx.checked_pairs.add(key)
    if set(a.items) != set(b.items):
        only_a, only_b = len(set(a.items) - set(b.items)), len(set(b.items) - set(a.items))
        ctx.void.append(f"schema: {a.path} vs {b.path}: item id sets differ ({only_a} only in the first, {only_b} only "
                        "in the second)")
        return
    differ = [i for i in a.items if a.items[i][1] != b.items[i][1]]
    if differ:
        ctx.void.append(f"schema: {a.path} vs {b.path}: {len(differ)} items have different slices (e.g. {differ[0]})")


@dataclass
class Comparison:
    cell: str
    complete: bool                        # every wanted seed's pair was available
    seeds: list[dict[str, Any]]
    n: int = 0
    delta: Optional[Fraction] = None      # pooled mean(x) - mean(y)
    p: Optional[float] = None             # paired p-value for x > y, pooled
    positive: int = 0
    negative: int = 0

    def row(self) -> dict[str, Any]:
        return {"cell": self.cell, "complete": self.complete, "n_pooled": self.n,
                "delta_points": None if self.delta is None else 100 * float(self.delta), "p": self.p,
                "seeds_positive": self.positive, "seeds_negative": self.negative,
                "per_seed": [{**s, "delta_points": None if s["delta"] is None else 100 * float(s["delta"]),
                              "delta": None if s["delta"] is None else float(s["delta"])} for s in self.seeds]}


def compare(ctx: Context, x_key: tuple[str, Optional[str]], y_key: tuple[str, Optional[str]], cell: str
            ) -> Comparison:
    """Pooled and per-seed paired comparison of x against y on `cell`, items matched by id within a seed."""
    out = Comparison(cell=cell, complete=True, seeds=[])
    pooled_x: list[int] = []
    pooled_y: list[int] = []
    for seed in ctx.seeds:
        a = ctx.evals.get((x_key[0], seed, x_key[1]))
        b = ctx.evals.get((y_key[0], seed, y_key[1]))
        if a is None or b is None:
            out.complete = False
            continue
        check_pair(ctx, a, b)
        ids = sorted(i for i in a.items if i in b.items and cell in a.items[i][1])
        xs, ys = [a.items[i][0] for i in ids], [b.items[i][0] for i in ids]
        n = len(ids)
        delta = Fraction(sum(xs) - sum(ys), n) if n else None
        out.seeds.append({"seed": seed, "n": n, "x_hits": sum(xs), "y_hits": sum(ys),
                          "x_acc": sum(xs) / n if n else None, "y_acc": sum(ys) / n if n else None,
                          "delta": delta})
        pooled_x += xs
        pooled_y += ys
    out.n = len(pooled_x)
    if out.n:
        out.delta = Fraction(sum(pooled_x) - sum(pooled_y), out.n)
        out.p = float(paired_greater_pvalue(pooled_x, pooled_y, margin=0.0))
    out.positive = sum(1 for s in out.seeds if s["delta"] is not None and s["delta"] > 0)
    out.negative = sum(1 for s in out.seeds if s["delta"] is not None and s["delta"] < 0)
    if len(out.seeds) < len(ctx.seeds) or any(s["n"] == 0 for s in out.seeds):
        out.complete = False
    return out


# ------------------------------------------------------------------ marks
def mark(name: str, title: str, status: str, bar: str, value: str, detail: Optional[dict[str, Any]] = None
         ) -> dict[str, Any]:
    """status: pass / fail / not computable / info."""
    return {"mark": name, "title": title, "status": status, "computed": status != "not computable",
            "bar": bar, "value": value, "detail": detail or {}}


def gain_mark(name: str, title: str, comp: Comparison, label: str) -> dict[str, Any]:
    """M1-style: pooled delta >= 3.0 points, p < alpha, and positive on >= 2 of 3 seeds."""
    bar = f"{label} >= +3.0 pts pooled, p < {ALPHA}, positive on >= 2 of {len(SEEDS)} seeds"
    if not comp.complete or comp.delta is None or comp.p is None:
        return mark(name, title, "not computable", bar, "a seed's pair is missing or its cell is empty", comp.row())
    ok = comp.delta >= MARGIN and comp.p < ALPHA and comp.positive >= 2
    value = (f"{points(comp.delta)} pts pooled (n {comp.n}), p {comp.p:.4g}, per seed "
             + ", ".join(points(s["delta"]) for s in comp.seeds))
    return mark(name, title, "pass" if ok else "fail", bar, value, comp.row())


def slip_mark(ctx: Context, name: str, title: str, x: tuple[str, Optional[str]], y: tuple[str, Optional[str]],
              label: str) -> dict[str, Any]:
    """DEV slip, per seed, never averaged: x slips on a cell when x < y - 3.0 pts; fails on >= 2 of 3 seeds."""
    bar = f"{label}: near slips on < 2 seeds AND overall slips on < 2 seeds (slip = below by more than 3.0 pts)"
    detail: dict[str, Any] = {}
    slips: dict[str, int] = {}
    for cell in ("near", "overall"):
        a = ctx.evals
        rows = []
        for seed in ctx.seeds:
            ea, eb = a.get((x[0], seed, x[1])), a.get((y[0], seed, y[1]))
            if ea is None or eb is None:
                rows.append({"seed": seed, "missing": True})
                continue
            check_pair(ctx, ea, eb)
            (xh, xn), (yh, yn) = ea.cell(cell), eb.cell(cell)
            if not xn or not yn or xn != yn:
                rows.append({"seed": seed, "n_x": xn, "n_y": yn, "empty_or_unequal": True})
                if not xn or not yn:
                    ctx.insufficient.append(f"{cell} cell is empty in seed {seed} ({x[0]} {xn}, {y[0]} {yn} items)")
                continue
            slip = Fraction(xh, xn) < Fraction(yh, yn) - MARGIN
            rows.append({"seed": seed, "n": xn, "x_acc": xh / xn, "y_acc": yh / yn,
                         "delta_points": 100 * (xh / xn - yh / yn), "slip": slip})
        detail[cell] = rows
        slips[cell] = sum(1 for r in rows if r.get("slip"))
        if any("slip" not in r for r in rows):
            return mark(name, title, "not computable", bar, f"{cell}: a seed is missing or its cell is empty", detail)
        small = [r["n"] for r in rows if r["n"] < ctx.min_items]
        if small:
            detail[f"{cell}_below_min_items"] = small
    ok = slips["near"] < 2 and slips["overall"] < 2
    value = (f"near slips on {slips['near']}/{len(ctx.seeds)} seeds, overall slips on {slips['overall']}/"
             f"{len(ctx.seeds)} seeds")
    return mark(name, title, "pass" if ok else "fail", bar, value, detail)


def usage_per_seed(ctx: Context, arm: str) -> list[dict[str, Any]]:
    rows = []
    for seed in ctx.seeds:
        e = ctx.evals.get((arm, seed, None))
        swarm = None if e is None else e.swarm
        if not swarm:
            rows.append({"seed": seed, "missing": True})
            continue
        ask, fetch = [num(v) for v in swarm["ask_rate"]], [num(v) for v in swarm["fetch_count"]]
        ok = (all(v >= ASK_FLOOR for v in ask) and all(math.isfinite(v) for v in fetch)
              and min(fetch) >= FETCH_FLOOR * max(fetch))
        rows.append({"seed": seed, "ask_rate": ask, "fetch_count": fetch, "ok": ok})
    return rows


def usage_mark(ctx: Context, name: str, title: str, arm: str) -> dict[str, Any]:
    bar = (f"every desk ask_rate >= {ASK_FLOOR} and min fetch_count >= {FETCH_FLOOR} x max, on >= 2 of "
           f"{len(ctx.seeds)} seeds")
    rows = usage_per_seed(ctx, arm)
    if any(r.get("missing") for r in rows):
        return mark(name, title, "not computable", bar, "a seed has no swarm diagnostics", {"seeds": rows})
    good = sum(1 for r in rows if r["ok"])
    value = f"ok on {good}/{len(ctx.seeds)} seeds"
    return mark(name, title, "pass" if good >= 2 else "fail", bar, value, {"seeds": rows})


def diversity_rows(ctx: Context, arm: str) -> list[dict[str, Any]]:
    rows = []
    for seed in ctx.seeds:
        e = ctx.evals.get((arm, seed, None))
        swarm = None if e is None else e.swarm
        if not swarm:
            rows.append({"seed": seed, "missing": True})
            continue
        cos, overlap = num(swarm["register_cos"]), num(swarm["fetch_overlap"])
        collapsed = is_collapsed(cos, overlap)
        if bool(swarm.get("collapsed")) != collapsed:
            ctx.void.append(f"schema: {e.path}: collapsed flag {swarm.get('collapsed')!r} disagrees with register_cos "
                            f"{cos} / fetch_overlap {overlap}")
        rows.append({"seed": seed, "fetch_overlap": overlap, "register_cos": cos,
                     "ask_rate": [num(v) for v in swarm["ask_rate"]],
                     "fetch_count": [num(v) for v in swarm["fetch_count"]],
                     "silent_desks": swarm.get("silent_desks"), "collapsed": collapsed})
    return rows


def diversity_mark(ctx: Context, name: str, title: str, arm: str) -> tuple[dict[str, Any], Optional[bool]]:
    """Prints fetch_overlap, register_cos, ask_rate[4], fetch_count[4], silent_desks per seed; collapsed on
    >= 2 of 3 seeds gives COLLAPSED. Returns (mark, collapsed)."""
    bar = (f"info; collapsed (register_cos > {COLLAPSE_COS} and fetch_overlap > {COLLAPSE_OVERLAP}) on >= 2 of "
           f"{len(ctx.seeds)} seeds -> '{COLLAPSED_TEXT}'")
    rows = diversity_rows(ctx, arm)
    if any(r.get("missing") for r in rows):
        return mark(name, title, "not computable", bar, "a seed has no swarm diagnostics", {"seeds": rows}), None
    count = sum(1 for r in rows if r["collapsed"])
    collapsed = count >= 2
    parts = [f"s{r['seed']}: overlap {r['fetch_overlap']:.3f} cos {r['register_cos']:.3f} ask "
             f"{[round(v, 2) for v in r['ask_rate']]} fetch {[round(v, 2) for v in r['fetch_count']]} "
             f"silent {r['silent_desks']}" for r in rows]
    value = f"collapsed on {count}/{len(ctx.seeds)} seeds; " + " | ".join(parts)
    return mark(name, title, "fail" if collapsed else "pass", bar, value, {"seeds": rows, "collapsed": collapsed}), \
        collapsed


def validity_mark(ctx: Context, name: str, title: str, arms: Sequence[str]) -> dict[str, Any]:
    """M5 (S0) / M6 (S1) validity: train status, train seconds within T +- 2%, finite loss, one data tag and one
    tokenizer digest, the run asked for T. Failures are VOID reasons."""
    bar = (f"every train completed, train_seconds within T +- {100 * ctx.seconds_tol:g}% (T from c0.json), "
           "loop_mismatches = 0, final loss finite, one data tag and one tokenizer sha256")
    problems: list[str] = []
    detail: dict[str, Any] = {"runs": []}
    T = num((ctx.c0 or {}).get("T"))
    if not (T > 0):
        problems.append("validity: c0.json has no usable T")
    tags: dict[Any, list[str]] = {}
    shas: dict[Any, list[str]] = {}
    if ctx.c0:
        tags.setdefault(ctx.c0.get("tag"), []).append("c0.json")
        shas.setdefault(ctx.c0.get("tokenizer_sha256"), []).append("c0.json")
    for arm in arms:
        for seed in ctx.seeds:
            report = ctx.trains.get((arm, seed))
            label = f"train-{arm}-s{seed}"
            if report is None:
                problems.append(f"missing: {label}.json")
                continue
            seconds = num(report.get("train_seconds"))
            loss = num((report.get("final") or {}).get("loss"))
            history_bad = [r.get("step") for r in report.get("history") or []
                           if "loss" in r and r["loss"] is not None and not finite(r["loss"])]
            run = {"run": label, "status": report.get("status"), "train_seconds": seconds, "steps": report.get("steps"),
                   "final_loss": loss, "loop_mismatches": report.get("loop_mismatches"), "seconds_budget": report.get("seconds_budget"),
                   "stop": report.get("stop")}
            detail["runs"].append(run)
            if report.get("status") != "completed":
                problems.append(f"validity: {label} status {report.get('status')!r}")
            if not math.isfinite(seconds):
                problems.append(f"seconds: {label} has no train_seconds in the report")
            elif T > 0 and abs(seconds - T) > ctx.seconds_tol * T:
                problems.append(f"seconds: {label} train_seconds {seconds:.2f} is {100 * (seconds / T - 1):+.2f}% from T {T:g}")
            if report.get("loop_mismatches") != 0:
                problems.append(f"validity: {label} loop_mismatches {report.get('loop_mismatches')!r}, expected 0")
            if not math.isfinite(loss) or history_bad:
                problems.append(f"validity: {label} final loss {loss} / non-finite logged loss at steps {history_bad}")
            if T > 0 and report.get("seconds_budget") != T and num(report.get("seconds_budget")) != T:
                problems.append(f"validity: {label} trained with seconds_budget {report.get('seconds_budget')}, T is {T:g}")
            if report.get("swarm") != EXPECTED_SWARM[arm]:
                problems.append(f"validity: {label} swarm config {report.get('swarm')!r}, expected {EXPECTED_SWARM[arm]!r}")
            tags.setdefault((report.get("data") or {}).get("tag"), []).append(label)
            shas.setdefault((report.get("tokenizer") or {}).get("sha256"), []).append(label)
    for key, e in ctx.evals.items():
        tags.setdefault(e.tag, []).append(e.path)
        shas.setdefault(e.tokenizer_sha, []).append(e.path)
    if len(tags) != 1:
        problems.append(f"validity: data tags differ across files: { {str(k): v[:2] for k, v in tags.items()} }")
    if len(shas) != 1:
        problems.append(f"validity: tokenizer sha256 differs across files: { {str(k)[:12]: v[:2] for k, v in shas.items()} }")
    detail.update(T=T, tags=sorted(map(str, tags)), tokenizer_sha256=sorted(str(k)[:16] for k in shas),
                  note="card M5 (10-18): loop_mismatches = 0 replaces gold_missing, which train_d does not log")
    ctx.void.extend(problems)
    value = "valid" if not problems else f"{len(problems)} problems: " + "; ".join(problems[:3])
    return mark(name, title, "pass" if not problems else "fail", bar, value, detail)


def cells_mark(ctx: Context, name: str, title: str) -> dict[str, Any]:
    bar = f"far_deep has >= {ctx.min_items} items in every eval file (else INSUFFICIENT)"
    counts = {e.path: e.cell("far_deep")[1] for e in ctx.evals.values()}
    short = {path: n for path, n in counts.items() if n < ctx.min_items}
    if short:
        ctx.insufficient.append(f"far_deep below {ctx.min_items} items in {len(short)} of {len(counts)} eval files "
                                f"(smallest {min(counts.values())}, largest {max(counts.values())})")
    value = f"far_deep n: min {min(counts.values(), default=0)}, max {max(counts.values(), default=0)} over {len(counts)} files"
    return mark(name, title, "pass" if not short else "fail", bar, value, {"far_deep_items": counts})


# ------------------------------------------------------------------ information rows
def cell_table(ctx: Context, arm: str, lesion: Optional[str] = None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for cell in list(DECISION_CELLS) + [f"depth_{d}" for d in DEPTHS] + ["changed"]:
        hits = n = 0
        per_seed = []
        for seed in ctx.seeds:
            e = ctx.evals.get((arm, seed, lesion))
            if e is None:
                continue
            h, k = e.cell(cell)
            hits, n = hits + h, n + k
            per_seed.append({"seed": seed, "hits": h, "n": k, "acc": h / k if k else None})
        out[cell] = {"hits": hits, "n": n, "acc": hits / n if n else None, "per_seed": per_seed}
    return out


def steps_info(ctx: Context) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for arm in CARD_ARMS[ctx.card]:
        steps = [ctx.trains[(arm, s)].get("steps") for s in ctx.seeds if (arm, s) in ctx.trains]
        params = [ctx.trains[(arm, s)].get("parameters") for s in ctx.seeds if (arm, s) in ctx.trains]
        out[arm] = {"steps": steps, "parameters": sorted(set(params)),
                    "mean_steps": sum(steps) / len(steps) if steps and all(isinstance(v, int) for v in steps) else None}
    base = out.get("D1", {}).get("mean_steps")
    for arm, row in out.items():
        row["steps_over_D1"] = row["mean_steps"] / base if base and row["mean_steps"] is not None else None
    return out


# ------------------------------------------------------------------ the two cards
def line(text: str) -> str:
    return f"VERDICT: {text}"


def void_text(ctx: Context) -> str:
    reasons = list(dict.fromkeys(ctx.void))
    kinds = sorted({reason.split(":", 1)[0] for reason in reasons})
    return f"VOID ({', '.join(kinds)}): " + "; ".join(r.split(": ", 1)[-1] for r in reasons[:4])


def s0_card(ctx: Context) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    marks: list[dict[str, Any]] = []
    gain = compare(ctx, ("S0", None), ("D1", None), "far_deep")
    m1 = gain_mark("M1", "join (promote): far_deep, S0 - D1", gain, "S0 - D1")
    m2 = slip_mark(ctx, "M2", "DEV slip (guard): near / overall, S0 vs D1", ("S0", None), ("D1", None), "S0 vs D1")
    m3 = usage_mark(ctx, "M3", "desk usage (guard), S0", "S0")
    m4, collapsed = diversity_mark(ctx, "M4", "diversity (guard), S0", "S0")
    m5 = validity_mark(ctx, "M5", "matching (validity)", CARD_ARMS["S0"])
    m6 = cells_mark(ctx, "M6", "cells")
    marks += [m1, m2, m3, m4, m5, m6]
    kill = bool(gain.delta is not None and (gain.delta <= 0 or gain.negative >= 2))
    kill_value = ("not computable" if gain.delta is None else
                  f"pooled {points(gain.delta)} pts, negative on {gain.negative}/{len(ctx.seeds)} seeds")
    marks.append(mark("KILL", "kill condition: pooled <= 0 or S0 < D1 on >= 2 of 3 seeds",
                      "not computable" if gain.delta is None else ("fail" if kill else "pass"),
                      "pooled S0 - D1 <= 0 OR negative on >= 2 of 3 seeds (a KILL is shown as fail)", kill_value,
                      {"kill": kill}))
    guard_fail = [m["mark"] for m in (m2, m3) if m["status"] == "fail"]
    text = COLLAPSED_TEXT if collapsed else None
    if ctx.void:
        verdict, reason = "VOID", void_text(ctx)
    elif ctx.insufficient:
        verdict, reason = "INSUFFICIENT", "INSUFFICIENT: " + "; ".join(ctx.insufficient)
    elif any(not m["computed"] for m in marks):
        verdict, reason = "VOID", "VOID (schema): not computable: " + ", ".join(
            m["mark"] for m in marks if not m["computed"])
    elif kill:
        verdict, reason = "KILL", "KILL: S0 does not beat D1 on far_deep (" + kill_value + "); the swarm line stops"
    elif guard_fail:
        names = {"M2": "DEV slip", "M3": "USAGE-COLLAPSE"}
        verdict, reason = "FAIL", "FAIL (" + ", ".join(f"{g} {names[g]}" for g in guard_fail) + ")"
    elif m1["status"] == "pass" and not collapsed:
        verdict, reason = "PROMOTE", "PROMOTE to S1"
    elif m1["status"] == "pass":
        verdict, reason = "HOLD", "HOLD: M1 passes but the desks collapsed"
    else:
        verdict, reason = "HOLD", "HOLD: gain between 0 and 3 points, or not significant"
    if text and verdict not in ("VOID", "INSUFFICIENT") and text not in reason:
        reason += f" ({text})"
    elif text and text not in reason:
        reason += f" [{text}]"
    info = {"steps": steps_info(ctx), "cells": {arm: cell_table(ctx, arm) for arm in CARD_ARMS["S0"]},
            "kill_condition": kill}
    return marks, {"verdict": verdict, "line": line(reason)}, info


def s1_card(ctx: Context) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    marks: list[dict[str, Any]] = []
    gain = compare(ctx, ("S1", None), ("S0", None), "far_deep")
    m1 = gain_mark("M1", "communication adds: far_deep, S1 - S0", gain, "S1 - S0")
    board = compare(ctx, ("S1", None), ("S1", "board"), "far_deep")
    m2 = gain_mark("M2", "board is used: S1 intact - S1 lesion=board on far_deep", board, "intact - lesion")
    m3 = slip_mark(ctx, "M3", "DEV slip vs D1 (guard): near / overall, S1 vs D1", ("S1", None), ("D1", None), "S1 vs D1")
    m4 = usage_mark(ctx, "M4", "desk usage (guard), S1", "S1")
    m5, s1_collapsed = diversity_mark(ctx, "M5", "diversity (guard), S1", "S1")
    _, s0_collapsed = diversity_mark(ctx, "M5b", "diversity, S0 (reference)", "S0")
    s0_rows, s1_rows = diversity_rows(ctx, "S0"), diversity_rows(ctx, "S1")
    shift = {}
    if not any(r.get("missing") for r in s0_rows + s1_rows):
        shift = {"register_cos_S1_minus_S0": [b["register_cos"] - a["register_cos"] for a, b in zip(s0_rows, s1_rows)],
                 "fetch_overlap_S1_minus_S0": [b["fetch_overlap"] - a["fetch_overlap"] for a, b in zip(s0_rows, s1_rows)],
                 "ask_rate_S1_minus_S0": [[y - x for x, y in zip(a["ask_rate"], b["ask_rate"])]
                                          for a, b in zip(s0_rows, s1_rows)]}
    m5["detail"]["S0_reference_collapsed"] = s0_collapsed
    m5["detail"]["S1_minus_S0"] = shift
    board_collapsed = bool(s1_collapsed) and s0_collapsed is False
    if m5["computed"]:
        m5["status"] = "fail" if board_collapsed else ("info" if s1_collapsed else "pass")
    if shift:
        m5["value"] += " || S1 - S0 register_cos per seed " + ", ".join(f"{v:+.3f}" for v in shift["register_cos_S1_minus_S0"])
    m6 = validity_mark(ctx, "M6", "validity", CARD_ARMS["S1"])
    cells = cells_mark(ctx, "M6b", "cells")
    marks += [m1, m2, m3, m4, m5, m6, cells]
    kill = bool(gain.delta is not None and (gain.delta <= 0 or gain.negative >= 2))
    kill_value = ("not computable" if gain.delta is None else
                  f"pooled {points(gain.delta)} pts, negative on {gain.negative}/{len(ctx.seeds)} seeds")
    marks.append(mark("KILL-COMM", "pooled S1 - S0 <= 0 or S1 < S0 on >= 2 of 3 seeds",
                      "not computable" if gain.delta is None else ("fail" if kill else "pass"),
                      "a KILL-COMM is shown as fail", kill_value, {"kill": kill}))
    guard_fail = [m["mark"] for m in (m2, m3, m4) if m["status"] == "fail"]
    names = {"M2": "BOARD-UNUSED", "M3": "DEV slip", "M4": "USAGE-COLLAPSE"}
    if ctx.void:
        verdict, reason = "VOID", void_text(ctx)
    elif ctx.insufficient:
        verdict, reason = "INSUFFICIENT", "INSUFFICIENT: " + "; ".join(ctx.insufficient)
    elif any(not m["computed"] for m in marks):
        verdict, reason = "VOID", "VOID (schema): not computable: " + ", ".join(
            m["mark"] for m in marks if not m["computed"])
    elif kill:
        verdict, reason = "KILL-COMM", "KILL-COMM: S1 does not beat S0 on far_deep (" + kill_value + ")"
    elif guard_fail:
        verdict, reason = "FAIL", "FAIL (" + ", ".join(f"{g} {names[g]}" for g in guard_fail) + ")"
    elif m1["status"] == "pass" and not board_collapsed:
        verdict, reason = "PASS", "PASS (communication adds and is used)"
    elif m1["status"] == "pass":
        verdict, reason = "HOLD", f"HOLD: M1 passes but {BOARD_COLLAPSED_TEXT}"
    else:
        verdict, reason = "HOLD", "HOLD: gain between 0 and 3 points, or not significant"
    if board_collapsed and BOARD_COLLAPSED_TEXT not in reason:
        reason += f" ({BOARD_COLLAPSED_TEXT})"
    if s1_collapsed and COLLAPSED_TEXT not in reason:
        reason += f" [{COLLAPSED_TEXT}]"
    info_rows: dict[str, Any] = {}
    for lesion in ("notes", "cards"):
        info_rows[f"lesion_{lesion}_drop"] = compare(ctx, ("S1", None), ("S1", lesion), "far_deep").row()
    info_rows["lesion_board_drop"] = board.row()
    info_rows["S1_vs_D1_far_deep"] = compare(ctx, ("S1", None), ("D1", None), "far_deep").row()
    info_rows["S0_vs_D1_far_deep"] = compare(ctx, ("S0", None), ("D1", None), "far_deep").row()
    info_rows["depth_and_changed_cells"] = {arm: {k: v for k, v in cell_table(ctx, arm).items()
                                                  if k.startswith("depth_") or k == "changed"}
                                            for arm in CARD_ARMS["S1"]}
    info = {"steps": steps_info(ctx), "cells": {arm: cell_table(ctx, arm) for arm in CARD_ARMS["S1"]},
            "information": info_rows, "board_collapsed_the_desks": board_collapsed, "kill_comm": kill}
    return marks, {"verdict": verdict, "line": line(reason)}, info


# ------------------------------------------------------------------ run and report
def run(card: str, directory: str, *, seeds: Sequence[int] = SEEDS, min_items: int = MIN_ITEMS,
        seconds_tol: float = SECONDS_TOL, note: str = "") -> dict[str, Any]:
    ctx = Context(directory=Path(directory), seeds=tuple(seeds), min_items=min_items, seconds_tol=seconds_tol,
                  card=card)
    ctx.c0 = read_json(ctx, "c0.json")
    for arm in CARD_ARMS[card]:
        for seed in ctx.seeds:
            load_train(ctx, arm, seed)
            load_eval(ctx, arm, seed, None)
    if card == "S1":
        for seed in ctx.seeds:
            for lesion in LESIONS:
                load_eval(ctx, "S1", seed, lesion)
    marks, verdict, info = (s0_card if card == "S0" else s1_card)(ctx)
    ctx.void[:] = list(dict.fromkeys(ctx.void))
    ctx.insufficient[:] = list(dict.fromkeys(ctx.insufficient))
    return {"card": card, "directory": str(directory), "note": note, "seeds": list(ctx.seeds),
            "min_items": min_items, "seconds_tol": seconds_tol, "T": (ctx.c0 or {}).get("T"),
            "verdict": verdict["verdict"], "verdict_line": verdict["line"],
            "void_reasons": ctx.void, "insufficient_reasons": ctx.insufficient,
            "marks": marks, "marks_computed": {m["mark"]: m["computed"] for m in marks},
            "information": info}


def render(result: dict[str, Any]) -> str:
    rows = [f"# Swarm screen readout, card {result['card']}", ""]
    if result["note"]:
        rows += [f"**{result['note']}**", ""]
    rows += [f"directory `{result['directory']}`; seeds {result['seeds']}; T = {result['T']}; far_deep minimum "
             f"{result['min_items']} items; seconds tolerance {100 * result['seconds_tol']:g}%", "",
             "| mark | what | status | bar | value |", "|---|---|---|---|---|"]
    for m in result["marks"]:
        rows.append(f"| {m['mark']} | {m['title']} | {m['status']} | {m['bar']} | {m['value'].replace('|', '/')} |")
    rows += ["", result["verdict_line"], ""]
    if result["void_reasons"]:
        rows += ["VOID reasons:"] + [f"- {r}" for r in result["void_reasons"]] + [""]
    if result["insufficient_reasons"]:
        rows += ["INSUFFICIENT reasons:"] + [f"- {r}" for r in result["insufficient_reasons"]] + [""]
    info = result["information"]
    rows += ["## Information (not marks)", ""]
    rows += ["Steps in T, per arm (mean over seeds):", ""]
    rows += ["| arm | steps per seed | mean | over D1 | parameters |", "|---|---|---|---|---|"]
    for arm, row in info["steps"].items():
        ratio = "n/a" if row["steps_over_D1"] is None else f"{row['steps_over_D1']:.3f}"
        rows.append(f"| {arm} | {row['steps']} | {row['mean_steps']} | {ratio} | {row['parameters']} |")
    rows += ["", "Pooled accuracy % (hits/n) over seeds, validation:", ""]
    arms = list(info["cells"])
    cells = list(next(iter(info["cells"].values())))
    rows += ["| cell | " + " | ".join(arms) + " |", "|---|" + "---|" * len(arms)]
    for cell in cells:
        rows.append(f"| {cell} | " + " | ".join(
            f"{pct(info['cells'][a][cell]['acc'])} ({info['cells'][a][cell]['hits']}/{info['cells'][a][cell]['n']})"
            for a in arms) + " |")
    if "information" in info:
        rows += ["", "S1 information rows (pooled paired differences, far_deep):", ""]
        for key in ("lesion_board_drop", "lesion_notes_drop", "lesion_cards_drop", "S1_vs_D1_far_deep",
                    "S0_vs_D1_far_deep"):
            row = info["information"][key]
            delta = "n/a" if row["delta_points"] is None else f"{row['delta_points']:+.2f}"
            p = "n/a" if row["p"] is None else f"{row['p']:.4g}"
            rows.append(f"- {key}: {delta} pts (n {row['n_pooled']}, p {p}, seeds positive {row['seeds_positive']})")
    rows.append("")
    return "\n".join(rows)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--card", choices=("S0", "S1"), required=True)
    parser.add_argument("--dir", required=True, help="folder holding the runner's JSON files")
    parser.add_argument("--out", required=True, help="MARKS-<card>.json; the .md is written beside it")
    parser.add_argument("--min-items", type=int, default=MIN_ITEMS, help="far_deep items needed per eval file (M6)")
    parser.add_argument("--seeds", default=",".join(map(str, SEEDS)))
    parser.add_argument("--seconds-tol", type=float, default=SECONDS_TOL)
    parser.add_argument("--note", default="", help="a line printed at the top of the .md (e.g. DRY RUN)")
    args = parser.parse_args(argv)
    result = run(args.card, args.dir, seeds=[int(s) for s in args.seeds.split(",")], min_items=args.min_items,
                 seconds_tol=args.seconds_tol, note=args.note)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=1, default=str) + "\n", encoding="utf-8")
    out.with_suffix(".md").write_text(render(result), encoding="utf-8")
    print(render(result))
    print(f"wrote {out} and {out.with_suffix('.md')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
