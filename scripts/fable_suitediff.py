#!/usr/bin/env python3
"""Exp 214 SHARED SUITE-DIFF TOOL (harness only; no agent change).

ONE tool replacing the 40+ per-merge copies (scripts/fable_fix<N>_suites.py
+ fable_fix<N>_marksdiff.py). It loads ANY loop agent generically (the
module's DEFAULT_CONFIG* + build_agent* + *Daemon), runs the frozen suites
in-process with the SAME judges as scripts/fable_fix138i_suites.py, and
compares each case against the SEALED rows of the named base.

Suites + judges (all imported read-only; only runtime attribute patching,
never file edits):
  rt136       fable_fix139b_redteam136.run_case139b (mailbox, stored triples)
  rt143       fable_redteam143_run.run_case (mailbox, teach+question)
  sessions152 fable_session152_run.run_session + judge (mailbox sessions)
  bench       fable_bench121_run.run_item (scorer v2) or
              fable_fix172b_benchv3.run_item_v3, auto-picked per split by
              the sealed base rows' schema ("confirms" key -> v3);
              4 splits (new_121_4hop, old_s2fresh_4hop, edit200,
              bench132_4hop)
  marks123    stock CLI scripts/fable_marks123_all.py, fast subset only
              (p4, q1, bench, rt81 -- no subprocess-per-case or soak suites)

Per-suite output in --out: a rows file (replies + stored triples per case)
and a diff report listing every moved case classed as new WRONG,
new WRONG-WRITE, new junk write, or reply-only move, plus one summary line.

Bases: 138h -> artifacts/fable-agent138h-20260922/
        138i -> artifacts/fable-agent138i-20260922/
(Base rows are found by filename search under the base dir, so both the
flat 138h layout and the 138i g1bench/g2frozen layout work; both
JSON-array and JSONL rows files are accepted.)

Run (Mac CPU, offline, one suite at a time; only AFTER PASSMARKS sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_suitediff.py \\
    --agent scripts/fable_loop138i_agent.py \\
    --config artifacts/fable-agent138i-20260922/loop138i-config.json \\
    --base 138i --out <dir> [--only rt136|rt143|sessions152|bench|marks123|all]
"""

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

ROOT = SCRIPTS.parent

BASE_DIRS = {
    "138h": ROOT / "artifacts" / "fable-agent138h-20260922",
    "138i": ROOT / "artifacts" / "fable-agent138i-20260922",
}

WRONGish = ("WRONG-WRITE", "WRONG-ANSWER", "WRONG-REPLY", "WRONG", "BUG",
            "wrong")

SUITES = ["rt136", "rt143", "sessions152", "bench", "marks123"]

# bench splits: (tag, path-or-marker, base filename fragments)
BENCH_SPLITS = (
    ("new_121_4hop", "DATA_NEW", ("new_121_4hop",)),
    ("old_s2fresh_4hop", "DATA_OLD", ("old_s2fresh_4hop", "s2fresh_4hop")),
    ("edit200", str(ROOT / "data" / "open" / "bench65"
                    / "fable_edit_200.jsonl"), ("edit200",)),
    ("bench132_4hop", str(ROOT / "data" / "open" / "bench132"
                          / "fable_edit132_4hop.jsonl"), ("bench132_4hop",)),
)

# marks123 fast subset (in-process suites only; rt110 needs a subprocess per
# case, p2 needs kill9 bursts, p3 needs loop96 runners, soak/sleep are slow)
MARKS123_SUBSET = ["p4", "q1", "bench", "rt81"]


# ------------------------------------------------------------------ loading

def load_agent(agent_script: str):
    spec = importlib.util.spec_from_file_location(
        "fable_suitediff_agent_under_test", agent_script)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    default_cfg = None
    for name in sorted(dir(mod)):
        if name.startswith("DEFAULT_CONFIG"):
            default_cfg = getattr(mod, name)
            break
    if default_cfg is None:
        raise RuntimeError(f"no DEFAULT_CONFIG* in {agent_script}")
    build_fn = None
    for name in sorted(dir(mod)):
        if name.startswith("build_agent") and callable(getattr(mod, name)):
            build_fn = getattr(mod, name)
            break
    daemon_cls = None
    for name in sorted(dir(mod)):
        obj = getattr(mod, name)
        if isinstance(obj, type) and name.endswith("Daemon"):
            if daemon_cls is None:
                daemon_cls = obj
            if name.startswith("Loop"):
                daemon_cls = obj
                break
    if daemon_cls is None:
        raise RuntimeError(f"no *Daemon class in {agent_script}")
    return mod, daemon_cls, build_fn, default_cfg


def load_base_cfg(config_path: str) -> dict:
    return json.loads(Path(config_path).read_text(encoding="utf-8"))


def make_daemon(daemon_cls, base_cfg: dict, root: Path):
    cfg = copy.deepcopy(base_cfg)
    cfg["state_dir"] = str(root)
    cfg["sleep_threshold"] = 100000
    return daemon_cls(root, cfg=cfg, idle_seconds=3600.0)


def mailbox_daemon_cls(daemon_cls):
    """Adapt any (root, cfg, idle_seconds) daemon to the (root, cfg)
    constructor the bench121/rt143 runners call."""

    class Adapted(daemon_cls):  # type: ignore[valid-type,misc]
        def __init__(self, root, cfg=None, idle_seconds: float = 3600.0):
            super().__init__(root, cfg=cfg, idle_seconds=idle_seconds)

    Adapted.__name__ = getattr(daemon_cls, "__name__", "AdaptedDaemon")
    return Adapted


# ------------------------------------------------------------ base row files

def load_rows_any(path: Path):
    """Load a rows file in JSON-array OR JSONL format. Returns a list, or
    the parsed object (dicts with 'rows' values are unwrapped by callers)."""
    text = path.read_text(encoding="utf-8")
    stripped = text.strip()
    if not stripped:
        return []
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            return json.loads(stripped)
        except ValueError:
            pass
    return [json.loads(line) for line in stripped.splitlines()
            if line.strip()]


def unwrap_rows(obj) -> list:
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        if isinstance(obj.get("rows"), list):
            return obj["rows"]
        if isinstance(obj.get("cases"), list):
            return obj["cases"]
    raise ValueError(f"cannot unwrap rows from {type(obj)}")


def find_base_file(base_dir: Path, frags: tuple[str, ...],
                   exclude: tuple[str, ...] = ()) -> Path | None:
    cands = [p for p in sorted(base_dir.rglob("*.json*"))
             if all(f in p.name for f in frags)
             and not any(e in str(p) for e in exclude)
             and "scratch" not in str(p) and "-tmp" not in str(p)]
    # prefer rows/report files over summaries
    for p in cands:
        if "rows" in p.name or "report" in p.name or "loop138" in p.name:
            return p
    return cands[0] if cands else None


def find_base_file_any(base_dir: Path,
                       frag_options: tuple[tuple[str, ...], ...],
                       exclude: tuple[str, ...] = ()) -> Path | None:
    for frags in frag_options:
        hit = find_base_file(base_dir, frags, exclude=exclude)
        if hit is not None:
            return hit
    return None


# --------------------------------------------------------------- move tutors

def is_new_wrong(base_verdict: str, new_verdict: str) -> bool:
    return (base_verdict not in WRONGish) and (new_verdict in WRONGish)


def classify_reply_move(base: dict, new: dict, suite: str) -> dict:
    """Class a moved case: new WRONG-WRITE / new WRONG / new junk write /
    reply-only move. Returns {'class': ..., 'detail': ...}."""
    bv, nv = base.get("verdict"), new.get("verdict")
    if is_new_wrong(bv, nv) and nv == "WRONG-WRITE":
        return {"class": "new WRONG-WRITE",
                "detail": f"{bv} -> {nv}"}
    if is_new_wrong(bv, nv):
        return {"class": "new WRONG",
                "detail": f"{bv} -> {nv}"}
    bw = base.get("stored", base.get("fact_writes", base.get("writes", [])))
    nw = new.get("stored", new.get("fact_writes", new.get("writes", [])))
    if (nw not in (None, [], 0)) and (nw != bw) and not bw:
        return {"class": "new junk write",
                "detail": f"writes {bw!r} -> {nw!r}"[:200]}
    if (nw != bw) and (bv in WRONGish or nv in WRONGish):
        return {"class": "new junk write",
                "detail": f"writes {bw!r} -> {nw!r}"[:200]}
    return {"class": "reply-only move",
            "detail": f"verdict {bv}->{nv}, no new wrong/junk"}


def write_rows_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False,
                                         sort_keys=True) for r in rows)
                    + "\n", encoding="utf-8")


# ------------------------------------------------------------------- suites

def run_rt136(out: Path, work: Path, daemon_cls, base_cfg: dict,
              base_dir: Path) -> dict:
    import fable_fix139b_redteam136 as R136  # noqa: E402 (judge, read-only)
    t0 = time.time()

    def new_daemon(root: Path):
        return make_daemon(daemon_cls, base_cfg, root)

    R136.new_daemon139b = new_daemon  # type: ignore[method-assign]
    cases = json.loads((ROOT / "artifacts" / "fable-redteam136-20260922"
                        / "cases136.json").read_text(encoding="utf-8"))
    if isinstance(cases, dict):
        cases = cases.get("cases", cases)
    workroot = work / "work-rt136"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    rows = [R136.run_case139b(row, workroot) for row in cases]
    write_rows_jsonl(out / "rt136-rows.json", rows)
    base_path = find_base_file(base_dir, ("redteam136",))
    if base_path is None:
        raise RuntimeError(f"no sealed redteam136 rows under {base_dir}")
    b_by_id = {r["id"]: r for r in unwrap_rows(load_rows_any(base_path))}
    moves = []
    for r in rows:
        b = b_by_id.get(r["id"])
        if b is None:
            moves.append({"id": r["id"], "class": "MISSING-BASE",
                          "detail": "no sealed row"})
            continue
        if (r["verdict"] != b["verdict"]
                or str(r.get("reply", "")).strip()
                != str(b.get("reply", "")).strip()
                or r.get("stored") != b.get("stored")):
            cls = classify_reply_move(b, r, "rt136")
            moves.append({"id": r["id"], "class": cls["class"],
                          "detail": cls["detail"],
                          "base_verdict": b["verdict"],
                          "new_verdict": r["verdict"],
                          "base_reply": str(b.get("reply", ""))[:140],
                          "new_reply": str(r.get("reply", ""))[:140]})
    return finish_suite(out, "rt136", rows, moves, t0,
                        counter=dict(Counter(r["verdict"] for r in rows)),
                        base_rows=str(base_path))


def run_rt143(out: Path, work: Path, daemon_cls, base_cfg: dict,
              base_dir: Path) -> dict:
    import fable_redteam143_run as R143  # noqa: E402 (judge, read-only)
    t0 = time.time()
    R143.Loop132Daemon = mailbox_daemon_cls(daemon_cls)  # type: ignore[method-assign]  # noqa: E501
    R143.DEFAULT_CONFIG132 = copy.deepcopy(base_cfg)  # type: ignore[method-assign]  # noqa: E501
    suite = json.loads(R143.CASES_PATH.read_text(encoding="utf-8"))
    markers = suite["abstain_markers"]
    scratch = work / "scratch143"
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True)
    rows = [R143.run_case(case, scratch / case["id"], markers)
            for case in suite["cases"]]
    (out / "rt143-rows.json").write_text(
        json.dumps({"seconds": 0, "rows": rows}, indent=1,
                   ensure_ascii=False), encoding="utf-8")
    base_path = find_base_file(base_dir, ("redteam143",))
    if base_path is None:
        raise RuntimeError(f"no sealed redteam143 rows under {base_dir}")
    b_by_id = {r["id"]: r for r in unwrap_rows(load_rows_any(base_path))}
    moves = []
    for r in rows:
        b = b_by_id.get(r["id"])
        if b is None:
            moves.append({"id": r["id"], "class": "MISSING-BASE",
                          "detail": "no sealed row"})
            continue
        if (r["verdict"] != b["verdict"]
                or str(r.get("reply", "")).strip()
                != str(b.get("reply", "")).strip()):
            cls = classify_reply_move(b, r, "rt143")
            moves.append({"id": r["id"], "class": cls["class"],
                          "detail": cls["detail"],
                          "base_verdict": b["verdict"],
                          "new_verdict": r["verdict"],
                          "base_reply": str(b.get("reply", ""))[:140],
                          "new_reply": str(r.get("reply", ""))[:140]})
    return finish_suite(out, "rt143", rows, moves, t0,
                        counter=dict(Counter(r["verdict"] for r in rows)),
                        base_rows=str(base_path))


def run_sessions(out: Path, work: Path, daemon_cls, base_cfg: dict,
                 base_dir: Path) -> dict:
    import fable_session152_run as S152R  # noqa: E402 (judge, read-only)
    t0 = time.time()
    sessions_out: dict = {}
    for s in S152R.S152.SESSIONS:
        root = work / "work-sessions" / s["id"]
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True)
        daemon = make_daemon(daemon_cls, base_cfg, root)
        turns = S152R.run_session(daemon, root, s)
        sessions_out[s["id"]] = [{**t, "verdict": j["verdict"],
                                  "why": j["why"]}
                                 for t in turns
                                 for j in [S152R.judge(t)]]
    (out / "sessions152-rows.json").write_text(
        json.dumps(sessions_out, indent=1, ensure_ascii=False),
        encoding="utf-8")
    base_path = find_base_file(base_dir, ("sessions152",))
    if base_path is None:
        raise RuntimeError(f"no sealed sessions152 rows under {base_dir}")
    out_base = load_rows_any(base_path)
    if isinstance(out_base, list):
        raise RuntimeError("sessions base must be a {session: turns} object")
    moves = []
    counts_new: Counter = Counter()
    counts_base: Counter = Counter()
    for sid, turns in sessions_out.items():
        for t, b in zip(turns, out_base.get(sid, [])):
            counts_new[t["verdict"]] += 1
            counts_base[b["verdict"]] += 1
            if (t["verdict"] != b["verdict"]
                    or str(t.get("reply", "")).strip()
                    != str(b.get("reply", "")).strip()
                    or (t.get("fact_writes") or 0)
                    != (b.get("fact_writes") or 0)):
                tb = {"verdict": b["verdict"], "stored": [],
                      "fact_writes": b.get("fact_writes", 0)}
                tn = {"verdict": t["verdict"], "stored": [],
                      "fact_writes": t.get("fact_writes", 0)}
                cls = classify_reply_move(tb, tn, "sessions152")
                moves.append({"id": f"{sid}#{t['n']}",
                              "class": cls["class"],
                              "detail": cls["detail"],
                              "base_verdict": b["verdict"],
                              "new_verdict": t["verdict"],
                              "text": str(t["text"])[:100],
                              "base_reply": str(b.get("reply", ""))[:120],
                              "new_reply": str(t.get("reply", ""))[:120]})
    return finish_suite(out, "sessions152", sessions_out, moves, t0,
                        counter={"new": dict(counts_new),
                                 "base": dict(counts_base)},
                        base_rows=str(base_path))


def run_bench(out: Path, work: Path, daemon_cls, base_cfg: dict,
              base_dir: Path, only: str = "all") -> dict:
    import fable_bench121_run as B  # noqa: E402 (scorer v2, read-only)
    t0 = time.time()
    B.Loop121Daemon = mailbox_daemon_cls(daemon_cls)  # type: ignore[method-assign]  # noqa: E501
    splits = []
    for stag, pathmark, frags in BENCH_SPLITS:
        if only != "all" and stag not in only.split(","):
            continue
        path = B.DATA_NEW if pathmark == "DATA_NEW" else (
            B.DATA_OLD if pathmark == "DATA_OLD" else Path(pathmark))
        splits.append((stag, path, frags))
    workroot = work / "scratch-bench121"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    summary: dict = {"seconds": 0.0, "splits": {}}
    all_moves: list = []
    for stag, path, frags in splits:
        items = [json.loads(line) for line in
                 Path(str(path)).read_text(encoding="utf-8").splitlines()
                 if line.strip()]
        cfg = copy.deepcopy(base_cfg)
        cfg["sleep_threshold"] = 100000
        base_path = find_base_file_any(
            base_dir, (frags, (stag.split("_")[0], "rows")),
            exclude=("marks",))
        if base_path is None:
            raise RuntimeError(f"no sealed bench rows for {stag} "
                               f"under {base_dir}")
        base_sample = unwrap_rows(load_rows_any(base_path))
        proto = "v3" if base_sample and "confirms" in base_sample[0] \
            else "v2"
        if proto == "v3":
            import fable_fix172b_benchv3 as V3  # noqa: E402 (v3 driver)
            rows = [V3.run_item_v3(it, workroot / stag,
                                   copy.deepcopy(cfg),
                                   mailbox_daemon_cls(daemon_cls), "v3")
                    for it in items]
        else:
            rows = [B.run_item(it, workroot / stag, copy.deepcopy(cfg))
                    for it in items]
        summary["splits"][stag] = {"proto": proto}
        (out / f"bench-{stag}-rows.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        s_by_id = {r["id"]: r for r in unwrap_rows(load_rows_any(base_path))}
        moves = []
        for r in rows:
            s = s_by_id.get(r["id"])
            if s is None:
                moves.append({"id": r["id"], "class": "MISSING-BASE",
                              "detail": "no sealed row"})
                continue
            if (r["verdict"] != s["verdict"]
                    or str(r.get("reply", "")).strip()
                    != str(s.get("reply", "")).strip()):
                cls = classify_reply_move(s, r, "bench")
                moves.append({"id": r["id"], "class": cls["class"],
                              "detail": cls["detail"],
                              "base_verdict": s["verdict"],
                              "new_verdict": r["verdict"],
                              "base_reply": str(s.get("reply", ""))[:120],
                              "new_reply": str(r.get("reply", ""))[:120]})
        cell = {"n": len(rows),
                "correct": sum(1 for r in rows if r["verdict"] == "correct"),
                "abstain": sum(1 for r in rows if r["verdict"] == "abstain"),
                "wrong": sum(1 for r in rows if r["verdict"] == "wrong")}
        summary["splits"][stag] = {**cell, "proto": proto,
                                   "base_rows": str(base_path),
                                   "n_moves": len(moves)}
        all_moves.extend({**m, "split": stag} for m in moves)
        print(f"bench {stag}: {cell} moves={len(moves)}", flush=True)
    return finish_suite(out, "bench", summary, all_moves, t0,
                        counter={k: {kk: v[kk] for kk in
                                      ("correct", "abstain", "wrong")}
                                 for k, v in summary["splits"].items()})


def _marks_case_key(rep: dict, row: dict) -> tuple:
    rid = row.get("id", "?")
    if "agent_verdict" in row:
        return (rid, row.get("agent_verdict"),
                str(row.get("agent_final", ""))[:160])
    if "verdict" in row and "reply" in row:
        return (rid, row.get("verdict"), str(row.get("reply", ""))[:160])
    if "verdict" in row and "observed" in row:
        return (rid, row.get("verdict"), str(row.get("observed", ""))[:160])
    if row.get("pass") is not None:
        return (rid, bool(row.get("pass")),
                str(row.get("replies", row.get("reply", "")))[:160])
    return (rid, json.dumps(row, sort_keys=True)[:160])


def run_marks123(out: Path, agent_script: str, config_path: str,
                 base_dir: Path) -> dict:
    t0 = time.time()
    mout = out / "marks123"
    mout.mkdir(parents=True, exist_ok=True)
    env = dict(__import__("os").environ, OMP_NUM_THREADS="1",
               MKL_NUM_THREADS="1")
    cmd = [sys.executable, "-B", str(SCRIPTS / "fable_marks123_all.py"),
           "--agent", str(Path(agent_script).resolve()),
           "--config", str(Path(config_path).resolve()),
           "--out", str(mout), "--suite", "all",
           "--suites", ",".join(MARKS123_SUBSET), "--workers", "1"]
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env,
                          cwd=str(ROOT))
    print(proc.stdout[-3000:], flush=True)
    if proc.returncode not in (0, 1):
        print(proc.stderr[-2000:], flush=True)
        raise RuntimeError(f"marks123 driver failed rc={proc.returncode}")
    base_marks = None
    for cand in sorted(base_dir.rglob("fable_marks123_summary.json")):
        if "scratch" not in str(cand) and "-tmp" not in str(cand):
            base_marks = cand.parent
            break
    if base_marks is None:
        for cand in sorted(base_dir.iterdir()):
            if cand.is_dir() and cand.name.startswith("marks"):
                base_marks = cand
                break
    if base_marks is None:
        raise RuntimeError(f"no sealed marks dir under {base_dir}")
    moves: list = []
    compared: list = []
    report_files = ["p4-report.json", "q1-report.json", "bench-report.json",
                    "rt81-report.json"]
    for rf in report_files:
        new_p, base_p = mout / rf, base_marks / rf
        if not new_p.exists() or not base_p.exists():
            continue
        new = json.loads(new_p.read_text(encoding="utf-8"))
        base = json.loads(base_p.read_text(encoding="utf-8"))
        n_rows = unwrap_rows(new["rows"]) if "rows" in new else (
            new.get("cases") or [])
        b_rows = unwrap_rows(base["rows"]) if "rows" in base else (
            base.get("cases") or [])
        if n_rows and b_rows and isinstance(n_rows[0], dict):
            b_by_id = {r.get("id"): r for r in b_rows}
            n = 0
            for r in n_rows:
                b = b_by_id.get(r.get("id"))
                if b is None or _marks_case_key(new, r) != _marks_case_key(
                        base, b):
                    n += 1
                    moves.append({"id": f"{rf}:{r.get('id')}",
                                  "class": "reply-only move"
                                  if b is not None else "MISSING-BASE",
                                  "detail": ("no sealed row" if b is None
                                             else "report row differs"),
                                  "base_verdict": (b.get("agent_verdict",
                                                         b.get("verdict"))
                                                   if b else None),
                                  "new_verdict": r.get("agent_verdict",
                                                       r.get("verdict"))})
            compared.append(f"{rf}:{len(n_rows)}rows")
        else:
            flat_n = {k: v for k, v in new.items()
                      if k not in ("seconds", "rows", "cases", "detail",
                                   "wrong_detail")}
            flat_b = {k: v for k, v in base.items()
                      if k not in ("seconds", "rows", "cases", "detail",
                                   "wrong_detail")}
            compared.append(f"{rf}:summary")
            if json.dumps(flat_n, sort_keys=True) != json.dumps(
                    flat_b, sort_keys=True):
                moves.append({"id": rf, "class": "reply-only move",
                              "detail": "summary fields differ"})
    for tag in ("fable_edit_200", "s2fresh_4hop"):
        new_p = mout / f"bench-rows-{tag}.jsonl"
        base_p = base_marks / f"bench-rows-{tag}.jsonl"
        if not (new_p.exists() and base_p.exists()):
            continue
        n_rows = [json.loads(l) for l in new_p.read_text(
            encoding="utf-8").splitlines() if l.strip()]
        b_rows = [json.loads(l) for l in base_p.read_text(
            encoding="utf-8").splitlines() if l.strip()]
        b_by_id = {r["id"]: r for r in b_rows}
        n = 0
        for r in n_rows:
            b = b_by_id.get(r["id"])
            if b is None or r["verdict"] != b["verdict"] or str(
                    r.get("reply", "")).strip() != str(
                        b.get("reply", "")).strip():
                n += 1
                cls = classify_reply_move(b or {}, r, "marks123-bench") \
                    if b else {"class": "MISSING-BASE", "detail": "no row"}
                moves.append({"id": f"bench-{tag}:{r['id']}",
                              "class": cls["class"],
                              "detail": cls["detail"],
                              "base_verdict": b["verdict"] if b else None,
                              "new_verdict": r["verdict"]})
        compared.append(f"bench-{tag}:{len(n_rows)}rows")
    return finish_suite(out, "marks123",
                        {"compared": compared,
                         "subset": MARKS123_SUBSET,
                         "log_tail": proc.stdout[-1500:]}, moves, t0,
                        counter={"compared": compared},
                        base_rows=str(base_marks))


def finish_suite(out: Path, suite: str, payload, moves: list,
                 t0: float, counter: dict, base_rows: str = "") -> dict:
    seconds = round(time.time() - t0, 1)
    classes = Counter(m["class"] for m in moves)
    n_new_wrong = int(classes.get("new WRONG", 0))
    n_new_ww = int(classes.get("new WRONG-WRITE", 0))
    n_junk = int(classes.get("new junk write", 0))
    line = (f"{suite}: n_moves={len(moves)} "
            f"(new WRONG={n_new_wrong}, new WRONG-WRITE={n_new_ww}, "
            f"new junk={n_junk}, reply-only="
            f"{int(classes.get('reply-only move', 0))}) "
            f"seconds={seconds}")
    print(line, flush=True)
    rep = {"suite": suite, "summary_line": line, "n_moves": len(moves),
           "class_counts": dict(classes), "moves": moves,
           "new_wrong": n_new_wrong, "new_wrong_write": n_new_ww,
           "new_junk": n_junk, "counter": counter, "seconds": seconds,
           "base_rows": base_rows}
    (out / f"{suite}-diff.json").write_text(
        json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")
    return rep


# --------------------------------------------------------------------- main

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 214 shared suite-diff")
    ap.add_argument("--agent", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--base", required=True, choices=["138h", "138i"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", default="all",
                    help="comma list of rt136,rt143,sessions152,bench,"
                         "marks123 (or all)")
    ap.add_argument("--bench-only", default="all")
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="suitediff-work-"))
    _, daemon_cls, _, _ = load_agent(args.agent)
    base_cfg = load_base_cfg(args.config)
    base_dir = BASE_DIRS[args.base]
    want = SUITES if args.only == "all" else args.only.split(",")
    for s in want:
        if s not in SUITES:
            print(f"unknown suite {s}", flush=True)
            return 2
    t0 = time.time()
    reps: dict = {}
    rc = 0
    for s in want:
        t1 = time.time()
        if s == "rt136":
            reps[s] = run_rt136(out, work, daemon_cls, base_cfg, base_dir)
        elif s == "rt143":
            reps[s] = run_rt143(out, work, daemon_cls, base_cfg, base_dir)
        elif s == "sessions152":
            reps[s] = run_sessions(out, work, daemon_cls, base_cfg, base_dir)
        elif s == "bench":
            reps[s] = run_bench(out, work, daemon_cls, base_cfg, base_dir,
                                args.bench_only)
        elif s == "marks123":
            reps[s] = run_marks123(out, args.agent, args.config, base_dir)
        print(f"done {s} in {round(time.time() - t1, 1)}s", flush=True)
        if reps[s]["new_wrong"] or reps[s]["new_wrong_write"] \
                or reps[s]["new_junk"]:
            rc = 1
    shutil.rmtree(work, ignore_errors=True)
    summary = {"agent": args.agent, "config": args.config,
               "base": args.base, "suites": want,
               "summary_lines": [reps[s]["summary_line"] for s in want],
               "rc": rc, "seconds": round(time.time() - t0, 1)}
    (out / "SUITEDIFF-SUMMARY.json").write_text(
        json.dumps(summary, indent=1, ensure_ascii=False), encoding="utf-8")
    for line in summary["summary_lines"]:
        print(line, flush=True)
    print(f"TOTAL seconds={summary['seconds']} rc={rc}", flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
