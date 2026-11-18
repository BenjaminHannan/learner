"""Sheet-1 data: fixed train/test split of the 300 GSM-Hard rows used by tricks1 (see sheet1.py). Runs on CPU."""
import argparse, json, random
from pathlib import Path
import tricks1

SAVED = "/mnt/project-files/results/tricks1/small/rows_s_py_gsmh.jsonl"
OUT = Path(__file__).parent / "sheet1_data.json"

def split_rows(rows, seed=1, n_train=100):
    """Shuffle the ids with Random(seed); first n_train are train, the rest test. Each split keeps the original row order."""
    ids = [r["id"] for r in rows]
    random.Random(seed).shuffle(ids)
    tr = set(ids[:n_train])
    return [r for r in rows if r["id"] in tr], [r for r in rows if r["id"] not in tr]

def check_saved(rows, saved):
    want = [json.loads(l)["id"] for l in Path(saved).open() if l.strip()]
    got = [r["id"] for r in rows]
    if got != want:
        raise SystemExit(f"FAIL: build_sets ids differ from {saved} (got {len(got)}, saved {len(want)}, first diff at "
                         f"{next((i for i, (a, b) in enumerate(zip(got, want)) if a != b), min(len(got), len(want)))})")

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--saved", default=SAVED); ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    rows = tricks1.build_sets(seed=0)["gsmh"]
    assert len(rows) == 300, len(rows)
    check_saved(rows, a.saved)
    tr, te = split_rows(rows)
    Path(a.out).write_text(json.dumps({"seed": 1, "train": tr, "test": te}))
    print(f"[data] train={len(tr)} test={len(te)} ids match {a.saved} -> {a.out}")

if __name__ == "__main__":
    main()
