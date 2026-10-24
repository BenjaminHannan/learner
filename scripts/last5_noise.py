"""Last-5-eval mean +- SD of dev accuracy per arm (the end-snapshot noise band; reporting only).
  python scripts/last5_noise.py [DIR ...]      default: design/v1/results2/full and /floor"""
import json, statistics, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def last_n(path: Path, n: int = 5) -> dict:
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    rows = [r for r in rows if r["step"] > 0][-n:]
    acc = [100 * r["accuracy"] for r in rows]
    return {"steps": [r["step"] for r in rows], "acc": acc, "mean": statistics.mean(acc),
            "sd": statistics.stdev(acc) if len(acc) > 1 else float("nan")}


def main(argv):
    dirs = [Path(d) for d in argv] or [ROOT / "design/v1/results2" / x for x in ("full", "floor")]
    for d in dirs:
        r = last_n(d / "dev_evals.jsonl")
        print(f"{d.name}: last {len(r['acc'])} evals (steps {r['steps'][0]}..{r['steps'][-1]}) "
              f"mean {r['mean']:.2f} +- {r['sd']:.2f} (sample SD) pts; values {[round(x, 1) for x in r['acc']]}")


if __name__ == "__main__":
    main(sys.argv[1:])
