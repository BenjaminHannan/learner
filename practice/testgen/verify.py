"""Parse, verify (run solvers), dedupe, select. usage: python -m practice.testgen.verify [--test raw1,raw2] [--pool raw3]
Writes practice/data/{test100.jsonl,test100.sha256,sonnet_pool.jsonl,testgen_stats.json}."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from practice.grade import is_correct, normalize  # noqa: E402
from sleep2.askonce.batches import parse_json  # noqa: E402

DATA = ROOT / "practice" / "data"
KINDS = ["grid", "number", "word", "logic", "sequence", "cipher", "ascii_picture"]
MAXP, MAXA = 3000, 200


def run_solver(code, timeout=20):
    with tempfile.TemporaryDirectory() as d:
        try:
            r = subprocess.run([sys.executable, "-I", "-c", code], cwd=d, capture_output=True, text=True, timeout=timeout,
                               env={"PATH": "/usr/bin:/bin", "HOME": d})
        except subprocess.TimeoutExpired:
            return None
        return r.stdout if r.returncode == 0 else None


def parse_and_check(cid, text):
    """Returns (record or None, reason)."""
    try:
        o = parse_json(text)
        assert isinstance(o, dict)
        for k in ("kind", "prompt", "answer", "answer_type", "solver"):
            assert k in o and (o[k] is not None), k
    except Exception:
        return None, "parse"
    kind = cid.rsplit("-", 1)[-1]
    o["kind"] = kind
    o["answer"] = str(o["answer"]).strip()
    o["prompt"] = str(o["prompt"]).strip()
    at = o["answer_type"]
    if at not in ("int", "str", "grid"):
        return None, "answer_type"
    if len(o["prompt"]) > MAXP:
        return None, "prompt_long"
    if len(o["answer"]) > MAXA or not o["answer"]:
        return None, "answer_long"
    if at == "int" and normalize(o["answer"], "int") is None:
        return None, "int_form"
    if at == "grid":
        rows = normalize(o["answer"], "grid")
        if not rows or len(rows) > 10 or any(len(r) > 10 or not r.isdigit() for r in rows) or len({len(r) for r in rows}) != 1:
            return None, "grid_form"
    if len(o["answer"]) > 2:
        pl = o["prompt"].lower()
        a = o["answer"].lower()
        if a in pl or (at == "grid" and "".join(normalize(o["answer"], "grid")) in re.sub(r"\s", "", pl) and False):
            return None, "leak"
    out = run_solver(o["solver"])
    if out is None or not out.strip():
        return None, "solver_fail"
    if not is_correct(out, o["answer"], at):
        return None, "mismatch"
    return o, "ok"


def shingles(t, n=8):
    w = re.sub(r"[^a-z0-9 ]", " ", t.lower()).split()
    return {" ".join(w[i:i + n]) for i in range(max(1, len(w) - n + 1))}


def jacc(a, b):
    return len(a & b) / max(1, len(a | b))


def normp(t):
    return " ".join(re.sub(r"[^a-z0-9]", " ", t.lower()).split())


def load_set(raws, which):
    recs, stats = [], {"requested": Counter(), "parsed": Counter(), "verified": Counter(), "fail": Counter()}
    for r in raws:
        d = json.loads((DATA / f"raw_{which}_{r}.json").read_text())
        for cid, text in sorted(d.items()):
            kind = cid.rsplit("-", 1)[-1]
            stats["requested"][kind] += 1
            o, why = parse_and_check(cid, text)
            if why != "parse":
                stats["parsed"][kind] += 1
            if o is None:
                stats["fail"][why] += 1
                continue
            stats["verified"][kind] += 1
            o["src"] = cid
            recs.append(o)
    return recs, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", default="b1")
    ap.add_argument("--pool", default="b1")
    a = ap.parse_args()
    test, ts = load_set(a.test.split(","), "test")
    pool, ps = load_set(a.pool.split(","), "pool")

    # dedupe within test (keep first), then pool against test and itself
    kept_t, seen, sh = [], set(), []
    for o in test:
        n, s = normp(o["prompt"]), shingles(o["prompt"])
        if n in seen or any(jacc(s, x) > 0.5 for x in sh):
            continue
        seen.add(n); sh.append(s); kept_t.append(o)
    kept_p, dropped_p = [], 0
    psh = []
    for o in pool:
        n, s = normp(o["prompt"]), shingles(o["prompt"])
        if n in seen or any(jacc(s, x) > 0.5 for x in sh + psh):
            dropped_p += 1
            continue
        seen.add(n); psh.append(s); kept_p.append(o)

    # select exactly 100 balanced, spreading difficulty
    by = defaultdict(list)
    for o in kept_t:
        by[o["kind"]].append(o)
    quota = {k: 0 for k in KINDS}
    while sum(quota.values()) < min(100, len(kept_t)):
        progressed = False
        for k in sorted(KINDS, key=lambda k: quota[k]):
            if quota[k] < len(by[k]) and sum(quota.values()) < 100:
                quota[k] += 1; progressed = True
        if not progressed:
            break
    chosen = []
    for k in KINDS:
        lst = by[k]
        order = {"easy": 0, "medium": 1, "hard": 2}
        lst = sorted(lst, key=lambda o: order.get(o.get("difficulty"), 1))
        # take evenly across difficulty ordering
        if quota[k]:
            idx = sorted({round(i * (len(lst) - 1) / max(1, quota[k] - 1)) for i in range(quota[k])}) if quota[k] > 1 else [0]
            pick = [lst[i] for i in idx]
            rest = [o for o in lst if o not in pick]
            while len(pick) < quota[k]:
                pick.append(rest.pop(0))
            chosen += pick
    chosen.sort(key=lambda o: (KINDS.index(o["kind"]), o["src"]))
    # interleave order by deterministic hash so ids don't encode kind
    chosen.sort(key=lambda o: hashlib.sha256(o["src"].encode()).hexdigest())

    def row(i, o, pre):
        return {"id": f"{pre}{i:03d}", "kind": o["kind"], "difficulty": o.get("difficulty", "medium"), "title": o.get("title", ""),
                "prompt": o["prompt"], "answer": o["answer"], "answer_type": o["answer_type"], "solver": o["solver"], "src": o["src"]}

    tr = [row(i, o, "t") for i, o in enumerate(chosen)]
    pr = [row(i, o, "s") for i, o in enumerate(kept_p)]
    tj = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in tr)
    (DATA / "test100.jsonl").write_text(tj)
    (DATA / "test100.sha256").write_text(hashlib.sha256(tj.encode()).hexdigest() + "  test100.jsonl\n")
    (DATA / "sonnet_pool.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in pr))
    spend = json.loads((DATA / "spend.json").read_text()) if (DATA / "spend.json").exists() else {}
    stats = {
        "test": {"requested": dict(ts["requested"]), "parsed": dict(ts["parsed"]), "verified": dict(ts["verified"]), "fail_reasons": dict(ts["fail"]),
                 "kept_after_dedupe": dict(Counter(o["kind"] for o in kept_t)), "kept": dict(Counter(r["kind"] for r in tr)),
                 "n_kept": len(tr), "difficulty": dict(Counter(r["difficulty"] for r in tr))},
        "pool": {"requested": dict(ps["requested"]), "parsed": dict(ps["parsed"]), "verified": dict(ps["verified"]), "fail_reasons": dict(ps["fail"]),
                 "dropped_overlap": dropped_p, "kept": dict(Counter(r["kind"] for r in pr)), "n_kept": len(pr)},
        "spend": spend,
    }
    (DATA / "testgen_stats.json").write_text(json.dumps(stats, indent=1, sort_keys=True))
    print(json.dumps({k: stats[k] for k in ("test", "pool")}, indent=1))
    print("spend", spend.get("total_usd"))


if __name__ == "__main__":
    main()
