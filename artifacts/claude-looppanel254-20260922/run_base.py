"""Run the base agent 138l over panel 254 and write base138l.jsonl (writer's scoring per spec).

Run from the repo root:
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy python -B \
      artifacts/claude-looppanel254-20260922/run_base.py <fresh scratch work dir>
Each dialog gets its own fresh work dir (<work>/<id>); setup turns, then turn, then followup.
"""
import json, re, shutil, sys
from pathlib import Path

sys.path.insert(0, "scripts")
import fable_marks123_all as M
import fable_notebook_contract as C
import fable_loop90_agent as L90

HERE = Path(__file__).resolve().parent
AGENT = "scripts/claude_loop138l_agent.py"
CONFIG = "artifacts/claude-merge138l-20260922/loop138l-config.json"
FAMS = {"teach_varied": 30, "ask_varied": 30, "both_varied": 20, "casual": 20,
        "backwards": 15, "chain": 15, "no_save": 20, "control": 10}
PANEL_FIELDS = ["id", "family", "setup", "turn", "followup", "gold_store", "gold_answer", "must_not", "note"]
FIRST = {"i", "me", "my", "myself", "mine", "user"}


def ent(x):
    x = str(x).strip().strip(".,;:!?\"'()[]").strip().lower()
    x = re.sub(r"^(the|a|an)\s+", "", x)
    return "me" if x in FIRST else x


def rel(x):
    return re.sub(r"[_\-\s]+", "_", str(x).strip().lower())


def matches(t, g):
    s, r, v = t
    return (ent(s) == ent(g["subject"]) and ent(v) == ent(g["value"])
            and rel(r) in {rel(g["relation"])} | {rel(a) for a in g["relation_aliases"]})


def whole(v, text):
    return re.search(r"(?<!\w)" + re.escape(v) + r"(?!\w)", text or "", re.I) is not None


def kind(row):
    if row["family"] in ("teach_varied",):
        return "T"
    if row["family"] in ("casual", "control"):
        return row["note"].split(":")[0]
    if row["family"] == "no_save":
        return "N"
    return "A"


def score(row, rec):
    after_setup = [tuple(x) for x in rec["stored_after_setup"]]
    after_turn = [tuple(x) for x in rec["stored_after_turn"]]
    replies = [rec["turn_reply"], rec["followup_reply"]]
    wrong = any(whole(m, x) for m in row["must_not"] for x in replies if x)
    if row["family"] == "no_save":
        return (sorted(after_turn) == sorted(after_setup)) and not wrong, wrong
    gold = row["gold_store"]
    store_ok = all(any(matches(t, g) for t in after_turn) for g in gold)
    new = [t for t in after_turn if t not in after_setup]
    store_ok = store_ok and all(any(matches(t, g) for g in gold) for t in new)
    scored = rec["followup_reply"] if kind(row) == "T" else rec["turn_reply"]
    scored = scored or ""
    if row["gold_answer"]:
        parts = [p.strip().lower() for p in row["gold_answer"].split(";")]
        low = scored.strip().lower()
        answer_ok = all(p in low for p in parts) and not (low.startswith("i don't know") or low.startswith("i do not know"))
    else:
        answer_ok = not any(whole(m, scored) for m in row["must_not"])
    fw = rec["stored_after_followup"] is not None and sorted(tuple(x) for x in rec["stored_after_followup"]) != sorted(after_turn)
    return store_ok and answer_ok and not wrong and not fw, wrong


def load_panel():
    p = HERE / "panel.jsonl"
    if not p.exists():
        print("SCHEMA-MISMATCH: panel.jsonl missing"); sys.exit(3)
    rows = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
    ok = len(rows) == 160 and all(list(r.keys()) == PANEL_FIELDS for r in rows)
    ok = ok and all(sum(r["family"] == f for r in rows) == n for f, n in FAMS.items())
    ok = ok and [r["id"] for r in rows] == [f"l254-{i:03d}" for i in range(1, 161)]
    if not ok:
        print("SCHEMA-MISMATCH: panel.jsonl"); sys.exit(3)
    return rows


def triples(d, root):
    nb = d.loop.nb if hasattr(d, "loop") else C.Notebook(root / "notebook")
    return [list(x) for x in L90.notebook_triples(nb)]


def main():
    work = Path(sys.argv[1])
    rows = load_panel()
    mod, dcls, _, _ = M.load_agent(AGENT)
    base = M.load_base_cfg(CONFIG)
    out = []
    for row in rows:
        root = work / row["id"]
        shutil.rmtree(root, ignore_errors=True); root.mkdir(parents=True)
        d = M.make_daemon(dcls, base, root)
        k = [0]

        def say(text):
            f = root / "inbox" / f"m{k[0]:02d}.txt"; f.write_text(text); d.process_file(f)
            rep = (root / "outbox" / f"m{k[0]:02d}.txt").read_text().strip(); k[0] += 1
            return rep
        setup_replies = [say(t) for t in row["setup"]]
        s_setup = triples(d, root)
        turn_reply = say(row["turn"])
        s_turn = triples(d, root)
        fu_reply, s_fu = None, None
        if row["followup"] is not None:
            fu_reply = say(row["followup"])
            s_fu = triples(d, root)
        rec = {"stored_after_setup": s_setup, "stored_after_turn": s_turn, "turn_reply": turn_reply,
               "followup_reply": fu_reply, "stored_after_followup": s_fu}
        right, wrong = score(row, rec)
        out.append({"id": row["id"], "setup_replies": setup_replies, "stored_after_setup": s_setup,
                    "turn_reply": turn_reply, "stored_after_turn": s_turn, "followup_reply": fu_reply,
                    "base_right": bool(right), "base_wrong_value": bool(wrong)})
    with open(HERE / "base138l.jsonl", "w") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    # summary + writer acceptance check (setup teaches saved exactly as gold says)
    for fam in FAMS:
        rs = [o for o, r in zip(out, rows) if r["family"] == fam]
        print(f"{fam:13s} base_right {sum(o['base_right'] for o in rs)}/{len(rs)} wrong_value {sum(o['base_wrong_value'] for o in rs)}")
    bad = []
    for o, r in zip(out, rows):
        if r["family"] in ("ask_varied", "backwards", "chain", "no_save") or (r["family"] == "control" and r["setup"]):
            st = [tuple(x) for x in o["stored_after_setup"]]
            ok = all(any(matches(t, g) for t in st) for g in r["gold_store"]) and \
                all(any(matches(t, g) for g in r["gold_store"]) for t in st)
            if not ok:
                bad.append(r["id"])
    print("setup-not-saved-as-gold:", bad)


if __name__ == "__main__":
    main()
