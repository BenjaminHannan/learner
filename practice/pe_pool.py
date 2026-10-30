"""Project Euler practice pool (run on the Mac; this needs projecteuler.net and raw.githubusercontent.com, both reachable from the Mac only).
Problem text: https://projecteuler.net/minimal=N (N = 1..100). Answers: a public answer list (lucky-bai/projecteuler-solutions Solutions.md); the answers are only
used by the grader (and the web leak filter). Problems that need a downloaded file or a picture are skipped. Output: practice/data/pe_pool.jsonl
  python -m practice.pe_pool [--n 100] [--out practice/data/pe_pool.jsonl]
Never raises on network trouble when called through `build(..., soft=True)` (the Mac run continues without PE)."""
import argparse
import json
import re
import time
import urllib.request
from pathlib import Path

from .web import html_to_text

ANS_URL = "https://raw.githubusercontent.com/lucky-bai/projecteuler-solutions/master/Solutions.md"
PROB_URL = "https://projecteuler.net/minimal={n}"
OUT = Path(__file__).resolve().parent / "data" / "pe_pool.jsonl"
SKIP_PAT = re.compile(r"right click|text file|\.txt|resources/|<img|download|\.png|\.gif", re.I)


def get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (practice-1M research script)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def parse_answers(md):
    """Accepts 'Problem 1: 233168', '1. 233168', '1: 233168', '| 1 | 233168 |' (integer answers only)."""
    out = {}
    for m in re.finditer(r"(?m)^[\s|*>-]*(?:Problem\s+)?(\d{1,3})\s*(?:[:.)\-|]|\s\|)+\s*(-?\d+)\s*\|?\s*$", md):
        out.setdefault(int(m.group(1)), m.group(2))
    return out


def clean_problem(raw):
    t = html_to_text(raw.replace("$", ""))  # keep the maths readable without LaTeX dollars
    t = re.sub(r"\\(?:dots|ldots)", "...", t)
    t = re.sub(r"\\(?:times|cdot)", "*", t)
    t = re.sub(r"\\(?:le|leq)\b", "<=", t)
    t = re.sub(r"\\(?:lt)\b", "<", t)
    t = re.sub(r"\\[a-zA-Z]+", "", t)
    t = t.replace("{", "").replace("}", "").replace("^", "^")
    return re.sub(r"[ \t]+", " ", t).strip()


def build(n=100, out=OUT, sleep=1.0, fetch=get, log=print, soft=False):
    try:
        ans = parse_answers(fetch(ANS_URL))
        if len(ans) < min(20, n):
            raise RuntimeError(f"answer list parsed only {len(ans)} answers")
        rows = []
        for k in range(1, n + 1):
            if k not in ans:
                continue
            try:
                raw = fetch(PROB_URL.format(n=k))
            except Exception as e:  # noqa: BLE001
                log(f"pe {k}: fetch failed {e!r}")
                continue
            time.sleep(sleep)
            if SKIP_PAT.search(raw):
                log(f"pe {k}: skipped (needs a file or picture)")
                continue
            text = clean_problem(raw)
            if not (40 <= len(text) <= 2500):
                continue
            prompt = (f"Project Euler problem {k}. {text}\n\nGive the exact integer answer. You can write and run Python to compute it.")
            rows.append({"id": f"pe-{k}", "source": "projecteuler", "kind": "euler", "title": f"Project Euler problem {k}", "prompt": prompt,
                         "answer": ans[k], "answer_type": "int"})
        if not rows:
            raise RuntimeError("no problems fetched")
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        log(f"pe_pool: wrote {len(rows)} problems to {out}")
        return rows
    except Exception as e:  # noqa: BLE001
        log(f"pe_pool failed: {e!r}")
        if soft:
            return []
        raise


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    build(a.n, a.out)
