"""Run the arms on the frozen items. Writes results/recallread/{arm}_{seed}.jsonl under --out (one row per item; baseline arms D0/D2/D3/D4
have no LoRA and are written once as {arm}_s0.jsonl, which stats.py reuses for both seeds).

  python -m sleep2.recallread.run_eval --frozen DIR --out DIR --adapter 1=PATH --adapter 2=PATH [--arms ...] [--limit 20] [--splits ...]
  python -m sleep2.recallread.run_eval --fake ...     # CPU smoke with a fake model (no GPU, no weights)
Resume-safe: a finished {arm}_{seed}.jsonl is skipped; files are written atomically after each arm.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from collections import defaultdict
from pathlib import Path

from . import arms as A
from .alias_table import AliasTable, load_table
from .index import Index
from .world import K2_MODEL, K2_REVISION, load_world, user_turns

DEFAULT_SPLITS = ("twohop_nat", "twohop_gap", "W_nat", "onehop", "never")


def select_rows(items, splits, limit):
    rows = [r for r in items["rows"] if r["split"] in splits]
    if limit:  # stratified smoke: first `limit` of each split
        seen = defaultdict(int)
        out = []
        for r in rows:
            if seen[r["split"]] < limit:
                seen[r["split"]] += 1
                out.append(r)
        rows = out
    return rows


def build_env(frozen: Path, runner, w_deleted):
    turns = user_turns(load_world(frozen / "week2.json"))
    full = Index(turns, name="full")
    wi = Index(turns, exclude=w_deleted, name="W")
    af = load_table(frozen / "alias_table_full.json") if (frozen / "alias_table_full.json").exists() else AliasTable([])
    aw = load_table(frozen / "alias_table_W.json") if (frozen / "alias_table_W.json").exists() else AliasTable([])
    return A.Env(runner.render, runner.gen, runner.count_tokens, full, wi, af, aw)


class FakeRunner:
    """CPU stand-in: whitespace 'tokens', answers 'unknown', keys echo a capitalised word of the prompt. For plumbing smoke tests only."""
    def render(self, system, user):
        return f"<sys>{system}</sys><user>{user}</user>"

    def count_tokens(self, text):
        return len(text.split())

    def gen(self, prompts, max_new, adapter=None):
        outs = []
        for p in prompts:
            if "Keys" in p[-80:]:
                txt = "my sister -> Maya; Maya -> dentist"
            else:
                txt = "unknown"
            pieces = txt.split(" ")
            pieces = [pieces[0]] + [" " + x for x in pieces[1:]]
            outs.append(A.GenOut(txt, pieces, [-0.5] * len(pieces), len(p.split()), min(len(pieces), max_new)))
        return outs


def write_jsonl(path: Path, rows):
    tmp = path.with_suffix(".tmp")
    tmp.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frozen", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--adapter", action="append", default=[], help="SEED=PATH (repeatable)")
    ap.add_argument("--arms", nargs="+", default=list(A.ALL_ARMS))
    ap.add_argument("--splits", nargs="+", default=list(DEFAULT_SPLITS))
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--fake", action="store_true")
    a = ap.parse_args()
    frozen, out = Path(a.frozen), Path(a.out) / "results" / "recallread"
    out.mkdir(parents=True, exist_ok=True)
    items = json.loads((frozen / "items.json").read_text())
    rows = select_rows(items, a.splits, a.limit)
    adapters = {s: p for s, p in (x.split("=", 1) for x in a.adapter)}
    runner = FakeRunner() if a.fake else __import__("sleep2.recallread.model", fromlist=["Runner"]).Runner({f"s{s}": p for s, p in adapters.items()})
    env = build_env(frozen, runner, set(items["w_deleted_turns"]))
    seeds = sorted(adapters) or (["1", "2"] if a.fake else [])
    jobs = [(arm, "0") for arm in a.arms if arm in A.BASE_ARMS] + [(arm, s) for s in seeds for arm in a.arms if arm in A.LORA_ARMS]
    # R before RD3 / R_tau (R_tau replays R's keys)
    jobs.sort(key=lambda j: (j[1] != "0", j[1], A.ALL_ARMS.index(j[0])))
    log = open(out / "run_eval.log", "a")
    for arm, s in jobs:
        f = out / f"{arm}_{'s0' if s == '0' else s}.jsonl"
        if f.exists():
            print("skip", f.name)
            continue
        t0 = time.time()
        lora = None if s == "0" else f"s{s}"
        if arm == "R_tau":
            rp = out / f"R_{s}.jsonl"
            r_res = [json.loads(l) for l in rp.read_text().splitlines()]
            tune = A.tune_tau(rows, env, lora, r_res)
            res = A.run_arm("R_tau", rows, env, lora, {"tau": tune["tau"], "replay": {x["row_id"]: x for x in r_res}})
            (out / f"R_tau_{s}.tune.json").write_text(json.dumps(tune))
        else:
            res = A.run_arm(arm, rows, env, lora)
        for r in res:
            r["seed"] = s
        write_jsonl(f, res)
        msg = f"{arm} seed {s}: {len(res)} rows in {time.time() - t0:.0f}s, em {sum(r['em'] for r in res) / max(len(res), 1):.3f}"
        print(msg, flush=True)
        log.write(msg + "\n")
        log.flush()
    # ledger check, once R and D3 exist for a seed
    for s in seeds:
        rf, df = out / f"R_{s}.jsonl", out / "D3_s0.jsonl"
        if rf.exists() and df.exists():
            r_res = [json.loads(l) for l in rf.read_text().splitlines()]
            d_res = [json.loads(l) for l in df.read_text().splitlines()]
            (out / f"ledger_R_vs_D3_{s}.json").write_text(json.dumps(A.assert_equal_budget(r_res, d_res)))
    (out / "run_meta.json").write_text(json.dumps(dict(model=K2_MODEL, revision=K2_REVISION, splits=a.splits, limit=a.limit, rows=len(rows),
                                                      items_sha=(frozen / "items.sha256").read_text().split()[0])))


if __name__ == "__main__":
    main()
