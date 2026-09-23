"""Correction-tail panel 258: run the 252b base on panel.jsonl and write base252b.jsonl.

Run from the repo root:
  OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 uv run --offline --no-project --python 3.12 --with torch --with numpy \
      python -B artifacts/claude-corrtail258-20260922/run_base.py <fresh scratch work dir>
Each dialog runs in its own fresh work dir, one session: setup turns, then turn, then followup.
Drives the agent and reads stored triples the same way as the director's probe runner.
"""
import json, re, shutil, sys
from pathlib import Path

sys.path.insert(0, "scripts")
import fable_marks123_all as M
import fable_notebook_contract as C
import fable_loop90_agent as L90

HERE = Path(__file__).resolve().parent
AGENT = "scripts/claude_loop252b_agent.py"
CONFIG = "artifacts/claude-correct252b-20260922/loop252b-config.json"
FIELDS = ["id", "setup_replies", "stored_after_setup", "turn_reply", "stored_after_turn",
          "followup_reply", "stored_after_followup", "base_right", "base_wrong_value", "base_false_claim"]


# ---------------- scoring (spec rules) ----------------
def key(t):
    return tuple(str(x).lower() for x in t)


def tset(ts):
    return {key(t) for t in ts}


def word_in(v, text):
    return re.search(r"(?<!\w)" + re.escape(v) + r"(?!\w)", text, re.IGNORECASE) is not None


def score(item, row):
    sa, st, sf = tset(row["stored_after_setup"]), tset(row["stored_after_turn"]), tset(row["stored_after_followup"])
    es, eg = tset(item["expect_store"]), tset(item["expect_gone"])
    store_ok = es <= st and not (eg & st) and st <= (sa | es)
    junk = (not st <= (sa | es)) or (not sf <= (sa | es))
    fr = row["followup_reply"]
    gone_vals = [g[2] for g in item["expect_gone"]]
    if item["gold_followup"] is not None:
        parts = [p.strip() for p in item["gold_followup"].split(";")]
        followup_ok = all(p.lower() in fr.lower() for p in parts) and not \
            fr.lower().startswith(("i don't know", "i do not know"))
    else:
        followup_ok = not any(word_in(v, fr) for v in gone_vals)
    wrong_value = any(word_in(v, fr) for v in gone_vals)
    followup_write = sf != st
    tg = item["target"]
    tr = row["turn_reply"]
    false_claim = bool(tg is not None and key(tg) in sa and key(tg) in st
                       and ("don't have" in tr.lower() or "do not have" in tr.lower())
                       and word_in(tg[2], tr))
    right = store_ok and followup_ok and not followup_write and not false_claim
    if item["family"] == "unstored_tail" and ("removed" in tr.lower() or "updated" in tr.lower()):
        right = False
    return dict(right=right, wrong_value=wrong_value, false_claim=false_claim, junk=junk,
                store_ok=store_ok, followup_ok=followup_ok, followup_write=followup_write)


# ---------------- driver ----------------
def triples(d, root):
    nb = d.loop.nb if hasattr(d, "loop") else C.Notebook(root / "notebook")
    return [[str(x) for x in t] for t in L90.notebook_triples(nb)]


def run_item(dcls, base, root, item):
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    d = M.make_daemon(dcls, base, root)
    n = [0]

    def say(t):
        f = root / "inbox" / f"m{n[0]:02d}.txt"
        f.write_text(t)
        d.process_file(f)
        rep = (root / "outbox" / f"m{n[0]:02d}.txt").read_text().strip()
        n[0] += 1
        return rep

    setup_replies = [say(t) for t in item["setup"]]
    s1 = triples(d, root)
    tr = say(item["turn"])
    s2 = triples(d, root)
    fr = say(item["followup"])
    s3 = triples(d, root)
    return dict(setup_replies=setup_replies, stored_after_setup=s1, turn_reply=tr,
                stored_after_turn=s2, followup_reply=fr, stored_after_followup=s3)


def main():
    work = Path(sys.argv[1])
    items = [json.loads(l) for l in open(HERE / "panel.jsonl")]
    mod, dcls, _, _ = M.load_agent(AGENT)
    base = M.load_base_cfg(CONFIG)
    rows, problems = [], []
    for k, it in enumerate(items):
        r = run_item(dcls, base, work / f"d{k:03d}", it)
        sc = score(it, r)
        right = True if it["family"] == "keep" else sc["right"]
        if it["family"] == "keep" and not sc["right"]:
            problems.append(f"{it['id']}: keep fields do not match base behaviour")
        row = {"id": it["id"], **r, "base_right": right, "base_wrong_value": sc["wrong_value"],
               "base_false_claim": sc["false_claim"]}
        assert list(row) == FIELDS
        rows.append((row, sc))
        # writer acceptance checks
        if r["stored_after_setup"] != it["stated_facts"]:
            problems.append(f"{it['id']}: stated_facts != stored_after_setup")
        for t, rep in zip(it["setup"], r["setup_replies"]):
            if not t.rstrip().endswith("?") and not rep.startswith("Saved:"):
                problems.append(f"{it['id']}: a setup teach was not saved")
        if "ctx" in it["note"].split("tags:")[-1].split():
            last = r["setup_replies"][-1]
            hits = [v for _, _, v in r["stored_after_setup"] if word_in(v, last)]
            if hits != [it["target"][2]]:
                problems.append(f"{it['id']}: ctx reply states {len(hits)} stored values / not the target")
        if it["family"] == "control" and not sc["right"]:
            problems.append(f"{it['id']}: control not base_right")
    with open(HERE / "base252b.jsonl", "w") as fh:
        for row, _ in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    fams = []
    for it in items:
        if it["family"] not in fams:
            fams.append(it["family"])
    for f in fams:
        sel = [(row, sc) for (row, sc), it in zip(rows, items) if it["family"] == f]
        print(f"{f:18s} n={len(sel):2d} base_right={sum(r['base_right'] for r, _ in sel):2d} "
              f"wrong_value={sum(r['base_wrong_value'] for r, _ in sel):2d} "
              f"false_claim={sum(r['base_false_claim'] for r, _ in sel):2d} "
              f"junk={sum(s['junk'] for _, s in sel):2d}")
    print("ACCEPTANCE:", "OK" if not problems else "PROBLEMS")
    for p in problems:
        print("  ", p)


if __name__ == "__main__":
    main()
