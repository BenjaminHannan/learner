"""Sheet-1 write-up helper: print the questions the best sheet flipped vs the baseline (both directions), with gold, both
answers and the end of both replies, for the pre-registered read-through. Usage: python3 tricks/sheet1_flips.py OUT_DIR [--n 20]"""
import argparse, json
from pathlib import Path

HERE = Path(__file__).parent

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("out"); ap.add_argument("--n", type=int, default=20); ap.add_argument("--chars", type=int, default=600)
    a = ap.parse_args()
    out = Path(a.out)
    res = json.loads((out / "result_sheet1.json").read_text())
    q = {r["id"]: r for r in json.loads((HERE / "sheet1_data.json").read_text())["test"]}
    rows = lambda i: {r["id"]: r for r in map(json.loads, (out / f"rows_{i}_test.jsonl").read_text().splitlines())}
    b, base = res["best"]["index"], rows(0)
    best = rows(b)
    print(f"best = {b} {res['best']['name']}; diff {res['primary']['diff_points']:+.1f}, verdict {res['verdict']}")
    for kind in ("wrong_to_right", "right_to_wrong"):
        ids = res["flips"][kind]
        print(f"\n######## {kind}: {len(ids)} (showing {min(a.n, len(ids))})")
        for k in ids[:a.n]:
            print(f"\n=== {k}  gold={q[k]['gold']}  baseline={base[k]['pred']}  best={best[k]['pred']}  tools {base[k]['tool_calls']}->{best[k]['tool_calls']}")
            print("Q:", q[k]["q"])
            print("-- baseline end:", base[k]["text"][-a.chars:].replace("\n", " "))
            print("-- best end:", best[k]["text"][-a.chars:].replace("\n", " "))

if __name__ == "__main__":
    main()
