"""Second-judge agreement: python -m bensweek.agree runs/<id> --n 40 [--model claude-opus-5-5]"""
import argparse
import random
import sys
from pathlib import Path

from .grade import judge
from .run import collect_results, wjson


def cohen_kappa(pairs):
    n = len(pairs)
    if not n:
        return None
    po = sum(a == b for a, b in pairs) / n
    pa = sum(a == "PASS" for a, _ in pairs) / n
    pb = sum(b == "PASS" for _, b in pairs) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return None if pe == 1 else round((po - pe) / (1 - pe), 3)


def agree_run(run_dir, n=40, model="claude-opus-5-5", seed=0, client=None, poll=25, sleep=None, log=print):
    run_dir = Path(run_dir)
    graded = [(r, c) for r in collect_results(run_dir) for c in r["checks"]
              if c["type"] == "rubric" and c.get("verdict")]
    random.Random(seed).shuffle(graded)
    sample = graded[:n]
    verdicts = judge(run_dir, sample, model, client, poll, sleep, log)
    rows, pairs = [], []
    for (r, c), (v, why, _) in zip(sample, verdicts):
        rows.append({"task_id": r["task_id"], "rubric": c["check"]["rubric"], "judge1": c["verdict"],
                     "reason1": c.get("reason", ""), "judge2": v, "reason2": why})
        if v:
            pairs.append((c["verdict"], v))
    agreement = round(sum(a == b for a, b in pairs) / len(pairs), 3) if pairs else None
    out = {"n": len(rows), "compared": len(pairs), "agreement": agreement, "kappa": cohen_kappa(pairs),
           "judge2": model, "rows": rows}
    wjson(run_dir / "agree.json", out)
    esc = lambda s: str(s).replace("|", "\\|").replace("\n", " ")
    md = [f"# Judge agreement spot check", "",
          f"Second judge: {model}. Compared {len(pairs)} of {len(rows)} sampled rubric checks. "
          f"Agreement: {agreement}. Cohen's kappa: {out['kappa']}.", "",
          "Disagreements are marked DIFF.", "",
          "| | task | rubric | judge 1 | judge 2 |", "|---|---|---|---|---|"]
    for x in sorted(rows, key=lambda x: x["judge1"] == x["judge2"]):
        flag = "" if x["judge1"] == x["judge2"] else "DIFF"
        md.append(f"| {flag} | {x['task_id']} | {esc(x['rubric'])} | {x['judge1']}: {esc(x['reason1'])} | {x['judge2']}: {esc(x['reason2'])} |")
    (run_dir / "spotcheck.md").write_text("\n".join(md) + "\n")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="bensweek.agree")
    ap.add_argument("run_dir")
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--model", default="claude-opus-5-5")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--poll", type=int, default=25)
    a = ap.parse_args(argv)
    o = agree_run(a.run_dir, a.n, a.model, a.seed, poll=a.poll)
    print(f"agreement {o['agreement']} kappa {o['kappa']} over {o['compared']} checks; see spotcheck.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
