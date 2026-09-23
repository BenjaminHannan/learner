"""Run base 138m on the openpanel260 panel -> base138m.jsonl (80 rows).
One fresh notebook per item (and a second fresh one for plain_turn), turns sent in order,
stored triples read after each stage, the way the probe runner dialog_nb.py drives agents.
Usage (repo root):
  OMP_NUM_THREADS=1 uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B artifacts/claude-openpanel260-20260922/run_base.py <scratch workdir> [out.jsonl] [plainlog.jsonl]
"""
import sys, json, shutil, string
from pathlib import Path

sys.path.insert(0, "scripts")
import fable_marks123_all as M
import fable_notebook_contract as C
import fable_loop90_agent as L90

HERE = Path(__file__).resolve().parent
AGENT = "scripts/claude_loop138m_agent.py"
CONFIG = "artifacts/claude-merge138m-20260922/loop138m-config.json"
PANEL = HERE / "panel.jsonl"
BAD_GREET = ["save", "understand", "couldn't", "could not", "don't know", "not sure"]

def norm(s):
    return s.lower().strip(string.punctuation + string.whitespace)

def ntrip(t):
    return tuple(norm(x) for x in t)

class Session:
    def __init__(self, dcls, base, root):
        shutil.rmtree(root, ignore_errors=True); root.mkdir(parents=True)
        self.root = root; self.d = M.make_daemon(dcls, base, root); self.n = 0
    def send(self, text):
        f = self.root / "inbox" / f"m{self.n:02d}.txt"; f.write_text(text); self.d.process_file(f)
        rep = (self.root / "outbox" / f"m{self.n:02d}.txt").read_text().strip(); self.n += 1
        return rep
    def stored(self):
        nb = self.d.loop.nb if hasattr(self.d, "loop") else C.Notebook(self.root / "notebook")
        return sorted([list(x) for x in L90.notebook_triples(nb)])

def score(it, row):
    fam = it["family"]
    setup = {ntrip(t) for t in row["stored_after_setup"]}
    exp = {ntrip(t) for t in it["expect_store"]}
    turn = {ntrip(t) for t in row["stored_after_turn"]}
    fol = {ntrip(t) for t in row["stored_after_followup"]}
    junk = bool((turn | fol) - setup - exp)
    store_ok = exp <= turn and not (turn - setup - exp)
    is_q = fam in ("opener_question", "greeting_question") or (fam == "control" and not it["followup"])
    qwrite = (is_q and turn != setup) or (bool(it["followup"]) and fol != turn)
    scored = row["followup_reply"] if it["followup"] else row["turn_reply"]
    reply_ok = it["gold"] == "" or norm(it["gold"]) in scored.lower()
    if fam in ("opener_teach", "junk_guard", "name_trap") or (fam == "control" and it["followup"]):
        right = store_ok and reply_ok and not junk and not qwrite
    elif fam in ("opener_question", "greeting_question") or fam == "control":
        right = reply_ok and not qwrite and not junk
    elif fam == "bare_greeting":
        r = row["turn_reply"].lower()
        right = turn == setup and fol == setup and not any(b in r for b in BAD_GREET)
    else:
        raise SystemExit(f"unknown family {fam}")
    # control: byte-identical to base holds trivially when this IS the base run
    return right, junk

def main():
    work = Path(sys.argv[1]).resolve()
    out = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else HERE / "base138m.jsonl"
    plainlog = Path(sys.argv[3]).resolve() if len(sys.argv) > 3 else None
    mod, dcls, _, _ = M.load_agent(AGENT); base = M.load_base_cfg(CONFIG)
    items = [json.loads(l) for l in PANEL.read_text().splitlines() if l.strip()]
    rows, plains = [], []
    for it in items:
        s = Session(dcls, base, work / it["id"])
        setup_replies = [s.send(t) for t in it["setup"]]
        sa = s.stored()
        tr = s.send(it["turn"]); st = s.stored()
        fr = s.send(it["followup"]) if it["followup"] else ""
        sf = s.stored()
        shutil.rmtree(work / it["id"], ignore_errors=True)
        pr, pstored = "", None
        if it["plain_turn"]:
            p = Session(dcls, base, work / (it["id"] + "-plain"))
            for t in it["setup"]:
                p.send(t)
            pbefore = p.stored(); pr = p.send(it["plain_turn"]); pafter = p.stored()
            pstored = [t for t in pafter if t not in pbefore]
            shutil.rmtree(work / (it["id"] + "-plain"), ignore_errors=True)
        row = dict(id=it["id"], setup_replies=setup_replies, stored_after_setup=sa, turn_reply=tr,
                   stored_after_turn=st, followup_reply=fr, stored_after_followup=sf, plain_reply=pr)
        row["base_right"], row["base_junk"] = score(it, row)
        rows.append(row)
        plains.append(dict(id=it["id"], family=it["family"], plain_turn=it["plain_turn"],
                           plain_reply=pr, plain_new_triples=pstored))
        print(f'{it["id"]} {it["family"]:17s} right={row["base_right"]!s:5} junk={row["base_junk"]!s:5} '
              f'turn={tr!r} fu={fr!r} +{[t for t in st if t not in sa]}', flush=True)
    with out.open("w") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    if plainlog:
        with plainlog.open("w") as fh:
            for r in plains:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows)} rows to {out}")

if __name__ == "__main__":
    main()
