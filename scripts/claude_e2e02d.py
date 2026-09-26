#!/usr/bin/env python3
"""0.2d: the new minimal joined build (Month-end, 2026-09-26; design/v3/30-modes/02d-gates-ADDENDUM-24.md, -26, -27).
New file only. It imports none of build_02c's layers: no 292t rule agent, no templates, no question reader, no
screens or guards, no creative regex, no length rules. DRAFT until sealed; the slots below are set once at the seal,
after H-A (358b3), H-B (sleep) and H-R (lis-320) each have a verified PASS (ADDENDUM-18), and never after.

Ben's design, one path on every user turn:
  reader    lis-320 (the lis-319 reader code, --model = lis-320's merged weights) reads the turn with the last 6
            (user, reply) pairs. A fact is saved only by lis-320's gate rule, nothing else: the lis-300 compiler's
            structural check passes and its confidence is >= 0.995 (claude_lis319_fullclaim.saved_facts, the rule
            H-R is scored on). Saved facts go to the fact book (one value per owner + relation, the newest wins, as
            0.2c's notebook doorway did: mechanical storage, disclosed) and, as note N0 (ADDENDUM-20), to the recall
            store as a pointer to the raw turn it came from.
  notebook  recall store v4 (claude_ep382_store_v4; ADDENDUM-23): every user turn as a heard row, plus N0 notes.
            Notes are only pointers: recall returns raw user turns.
  reasoner  the rsn-358b3 loop net. The grid reaches it through the disclosed code reader read_latin (P1; gr-1, the
            learned reader, is owed), and it stops by its disclosed stop rule (P3). Code checks the net's square against
            the square it read. The result goes to the talker as input; the reasoner never writes the reply.
  talker    plain MiniCPM5-1B, greedy, enable_thinking off, the 336 plain twin's system line. The W input (y1f's L1
            form, mu-405's W arm) is on every turn: every earlier user turn, oldest first, when they fit in
            CTX_CHARS02D characters, else the store's top K02D for this turn, oldest first. The last 6 (user, reply)
            pairs of this session are the chat messages.
  sleep     whatever recipe passes H-B, in its own form (SLEEP02D): an adapter, error-gated nights (dl-8) or a separate
            store with a switch (ADDENDUM-32); trained by the nights of a separate sleep run on code-made number puzzles
            (Z1, disclosed), loaded at start as 0.2c did. No slot value exists until H-B passes; e2e_end_day only makes
            sure everything is on disk.
Hand-written parts on this path, each disclosed scaffolding with the learned part it stands in for:
  P1  read_latin, the code grid reader (learned: gr-1, owed by Sleep research)
  P3  the loop net's stop rule, 3 steady rounds (learned: a stop head, owed)
  C1  the code check of the net's square against the square read (learned: the reasoner's own confidence, owed)
  H1  the hand-off to the talker (reasoner_note): the checked square, or "no square fits", as plain data in one fixed
      frame in the talker's system input. It adds no reasoning; it is the reasoner-to-talker interface, which Ben's
      design makes learned (the talker trained to read the reasoner's output, owed). Without it the net cannot reach
      the reply.
  D15 the date line read by ep-382's pattern DATE382 ("today is ..."; audit D15, borderline), used only to stamp
      store rows (learned: the reader reading dates, owed)
  F1  the fact book keeps one value per owner + relation, newest wins (0.2c's notebook rule; learned: the reader's
      CORRECT mode deciding supersession, owed)
  N0  a note's text is owner + relation + value joined by spaces (ADDENDUM-20 fallback; learned: rd-378g's writer)
  W   the whole-chat / top-k switch at CTX_CHARS02D characters (mechanical length limit, as y1w)
Not here (ADDENDUM-24/27): stock lines, templates, the 292t question reader, lookup "reasoner", declines, think299,
chat338 and its length rules, vary330c, gram360, confirm rows, lis-313b/314b/315/316, B10/B20 screens, W1 trigger,
D1 creative regex, D2 context_facts, D3 k1a guards. "I don't know" (DOUBT02D) is chosen at the seal: y1t if it has a
verified PASS, else no doubt step at all (ADDENDUM-29), with S1/H3 reported, not claimed.

Harness: scripts/claude_e2e336_run.py --arm claude_e2e02d:build_02d --model LIS320 --gen-model BASE
         (args.max_new, when a runner sets it, overrides the twin's 160; row A's runner passes the rivals' cap)
Each turn is logged to <state>/e2e02d_log.jsonl (counts and ids only), and also to $E2E02D_LOG_DIR/<state dir name>.jsonl
when that is set. D0 (ADDENDUM-26) counts come from those logs (scripts/claude_e2e02d_d0.py).
  python -B scripts/claude_e2e02d.py selftest          (wiring check only: stub reader, talker and solver, no model
                                                         loaded, slots empty; it says nothing about model quality)
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

# ---- slots, set once at the seal (ADDENDUM-18: all three headline gates verified PASS first) ----
READER_SHA02D = ""       # sha256 of lis-320's merged model.safetensors
REASONER02D = ""         # 358b3's sealed loop-net checkpoint path (relative to the repo root)
LEGEND02D = True         # 358b3's input form (358i nets read a legend row)
SLEEP02D = ""            # the H-B recipe's adapter file; "" = sleep off (row B's control arm)
DOUBT02D = ""            # "y1t" or "y1g" (ADDENDUM-24); "" = none (DEV only)
# ---- fixed settings ----
THRESHOLD02D = 0.995     # lis-320's gate threshold (H-R)
HIST_PAIRS = 6           # reader history and talker chat window, as lis-319
CTX_CHARS02D = 12000     # W input read whole up to this many characters (y1w/y1f)
K02D = 20                # store rows when the whole chat does not fit (y1w)
RECALL_MODE02D = "fused" # store v4 ranking (BM25 + frozen MiniLM); the no-model selftest uses "bm25"
MAX_NEW02D = 160         # the 336 plain twin's cap
LOG02D = "e2e02d_log.jsonl"
FACTS02D = "facts02d.json"
USER = "USER"            # how "me" facts are stored (0.2c's notebook, 336 scorer's USER_OWNERS)
THINK = re.compile(r"<think>.*?(</think>|$)", re.S)


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ------------------------------------------------------------------------------------------------ fact book
class FactBook:
    """Saved facts, readable by the 336 harness (fable_loop90_agent.notebook_triples: facts, entities, active; events).
    One active value per (owner, relation); a new value supersedes the old one. Kept in <state>/facts02d.json."""

    def __init__(self, state_dir):
        self.path = Path(state_dir) / FACTS02D
        self.facts: dict[str, dict] = {}
        self.entities: dict[str, str] = {}
        self._active: set[str] = set()
        self.events: list[dict] = []
        if self.path.exists():
            d = json.loads(self.path.read_text(encoding="utf-8"))
            self.facts, self.entities, self._active = d["facts"], d["entities"], set(d["active"])

    def active(self, fact_id: str) -> bool:
        return fact_id in self._active

    def _eid(self, name: str) -> str:
        for e, n in self.entities.items():
            if n == name:
                return e
        e = f"e{len(self.entities) + 1}"
        self.entities[e] = name
        return e

    def save(self, owner: str, rel: str, value: str, turn_no: int) -> str:
        name = USER if owner.strip().lower() == "me" else owner
        eid = self._eid(name)
        op = "teach"
        for fid in sorted(self._active):
            f = self.facts[fid]
            if f["subject"] == eid and f["relation"] == rel:
                if f["value"]["literal"] == value:
                    return "same"
                self._active.discard(fid)
                op = "correct"
        fid = f"f{len(self.facts) + 1}"
        self.facts[fid] = {"fact_id": fid, "subject": eid, "relation": rel, "value": {"literal": value},
                           "source": "taught", "turn": turn_no}
        self._active.add(fid)
        self.events.append({"op": op, "fact_id": fid, "subject": name, "relation": rel, "value": value})
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"facts": self.facts, "entities": self.entities,
                                   "active": sorted(self._active)}, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self.path)
        return op


# ------------------------------------------------------------------------------------------------ parts
_CACHE: dict = {}


def reader_for(model: str):
    if not model:
        raise SystemExit("0.2d: --model (lis-320's merged reader) is required")
    if ("reader", model) not in _CACHE:
        if READER_SHA02D:
            import hashlib
            got = hashlib.sha256((Path(model) / "model.safetensors").read_bytes()).hexdigest()
            if got != READER_SHA02D:
                raise SystemExit(f"READER-SHA-MISMATCH: {got} != {READER_SHA02D}")
        import claude_lis319_read as R
        _CACHE[("reader", model)] = R.Reader319(model)
    return _CACHE[("reader", model)]


def solver_for(ckpt: str, legend: bool):
    if ("solver", ckpt) not in _CACHE:
        import torch
        import claude_rsn358b2_bridge as B
        _CACHE[("solver", ckpt)] = B.LoopSolver(ckpt, legend, "cuda" if torch.cuda.is_available() else "cpu")
    return _CACHE[("solver", ckpt)]


class Talker:
    """The plain 1B as the 336 twin loads it; the sleep adapter (SLEEP02D) is added once per process."""

    def __init__(self, model_dir: str):
        import claude_e2e336_twin as TW
        self.tok, self.model, self.dev = TW._load(model_dir)
        if SLEEP02D:
            raise SystemExit("0.2d: SLEEP02D is set but no H-B recipe has a loader yet (set at the seal)")

    def reply(self, system: str, msgs: list[dict], max_new: int) -> str:
        import torch
        full = [{"role": "system", "content": system}] + msgs
        try:
            prompt = self.tok.apply_chat_template(full, tokenize=False, add_generation_prompt=True,
                                                  enable_thinking=False)
        except TypeError:
            prompt = self.tok.apply_chat_template(full, tokenize=False, add_generation_prompt=True)
        ids = self.tok(prompt, return_tensors="pt").to(self.dev)
        with torch.no_grad():
            out = self.model.generate(**ids, max_new_tokens=max_new, do_sample=False,
                                      pad_token_id=self.tok.eos_token_id)
        self.hit_max = int(out.shape[1] - ids["input_ids"].shape[1] >= max_new)
        text = self.tok.decode(out[0][ids["input_ids"].shape[1]:], skip_special_tokens=True)
        return THINK.sub("", text.split("\nUser:")[0]).strip()


def talker_for(model_dir: str):
    if not model_dir:
        raise SystemExit("0.2d: --gen-model (plain MiniCPM5-1B) is required")
    if ("talker", model_dir) not in _CACHE:
        _CACHE[("talker", model_dir)] = Talker(model_dir)
    return _CACHE[("talker", model_dir)]


# ------------------------------------------------------------------------------------------------ talker input
def w_rows(store, text: str) -> tuple[list[dict], str]:
    """Every earlier user turn when they fit, else the store's top K02D for this turn; oldest first either way."""
    heard = [r for r in store.rows if r.get("source") == "heard"]
    if not heard:
        return [], "none"
    if sum(len(r["text"]) for r in heard) <= CTX_CHARS02D:
        rows, how = heard, "whole"
    else:
        rows, how = store.recall(text, k=K02D, mode=RECALL_MODE02D), "top_k"
    return sorted(rows, key=lambda r: (min(r.get("turn_ids") or [0]), r.get("id", ""))), how


def rows_text(grid) -> str:
    return "\n".join(" ".join(str(v) for v in row) for row in grid)


def reasoner_note(res: dict | None) -> str:
    """H1 (disclosed): the reasoner's result as data for the talker, nothing more."""
    if res is None:
        return ""
    if res["ok"]:
        return "\n\nReasoner result for the number square in the last message (checked):\n" + rows_text(res["grid"])
    return "\n\nReasoner result for the number square in the last message: no square fits its clues."


def system_text(rows: list[dict], note: str) -> str:
    import claude_e2e336_twin as TW
    import claude_y1f_layout as Y
    w = ("\n\n" + Y.L1_HEAD + "".join('User said, "' + r["text"] + '"\n' for r in rows)) if rows else ""
    return TW.SYSTEM + note + w


# ------------------------------------------------------------------------------------------------ the agent
class Agent02d:
    def __init__(self, state_dir, reader, talker, solver, store, max_new: int = MAX_NEW02D):
        import claude_e2e382 as E382
        self.dir = Path(state_dir)
        self.nb = FactBook(state_dir)
        self.store = store
        self._read = reader.read            # kept as a bound method only (no weights as plain attributes)
        self._talk = talker
        self._solve = solver
        self.max_new = max_new
        self.pairs: list[tuple[str, str]] = []
        heard = [r for r in store.rows if r["source"] == "heard"]
        self.turn_no = len(heard)
        self.said_at = heard[-1].get("said_at") if heard else None
        self.date_re = E382.DATE382
        self.logs = [self.dir / LOG02D]
        if os.environ.get("E2E02D_LOG_DIR"):        # the 336 runner deletes state dirs; D0 reads this copy
            keep = Path(os.environ["E2E02D_LOG_DIR"])
            keep.mkdir(parents=True, exist_ok=True)
            self.logs.append(keep / f"{self.dir.name}.jsonl")

    def _reason(self, text: str) -> dict | None:
        import claude_puzzle_reader as P
        import claude_rsn358b2_bridge as B
        g = P.read_latin(text)
        if g is None:
            return None
        if self._solve is None:
            raise SystemExit("0.2d: a grid turn arrived but REASONER02D is unset (set at the seal)")
        grid, rounds = self._solve.solve(g["grid"])
        return {"size": g["size"], "clash": g["clash"], "grid": grid, "rounds": rounds,
                "ok": (not g["clash"]) and B.is_solution(g["grid"], grid)}

    def turn(self, text: str) -> list[str]:
        import claude_lis319_fullclaim as FC
        t0 = time.time()
        m = self.date_re.match(text)
        if m:
            self.said_at = m.group("d").strip()
        prev = self.pairs[-1][1] if self.pairs else ""
        frame, confs, _raw, read_ms = self._read(text, prev, self.pairs[-HIST_PAIRS:])
        facts = FC.saved_facts({"turn": text, "prev_reply": prev}, {"frame": frame, "conf": confs}, THRESHOLD02D)
        rows, how = w_rows(self.store, text)
        res = self._reason(text)
        msgs = []
        for u, a in self.pairs[-HIST_PAIRS:]:
            msgs += [{"role": "user", "content": u}, {"role": "assistant", "content": a}]
        msgs.append({"role": "user", "content": text})
        reply = self._talk.reply(system_text(rows, reasoner_note(res)), msgs, self.max_new)
        self.turn_no += 1
        self.store.remember(text, source="heard", speaker="user", turn_ids=[self.turn_no], said_at=self.said_at,
                            logged_at=_now())
        ops = []
        for f in facts:
            owner, rel, val = str(f.get("owner", "")), str(f.get("rel", "")), str(f.get("value", ""))
            ops.append(self.nb.save(owner, rel, val, self.turn_no))
            self.store.remember(f"{owner} {rel} {val}", source="note", speaker="user", turn_ids=[self.turn_no],
                                said_at=self.said_at, logged_at=_now())
        self.pairs.append((text, reply))
        row = {"turn": self.turn_no, "saved": len(facts), "ops": ops, "w": how, "w_rows": len(rows),
               "grid": res is not None, "reasoner_called": res is not None,
               "solved": bool(res and res["ok"]), "clash": bool(res and res["clash"]),
               "rounds": res["rounds"] if res else None, "hit_max": getattr(self._talk, "hit_max", 0),
               "empty_reply": not reply.strip(), "read_ms": round(read_ms, 1),
               "ms": round((time.time() - t0) * 1000, 1)}
        for path in self.logs:
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(row) + "\n")
        return [reply]

    def e2e_end_day(self) -> None:
        """Nights run in the separate sleep run (see SLEEP02D); the fact book and store are already on disk."""
        return None


def build_02d(state_dir, args):
    import importlib
    store = importlib.import_module("claude_ep382_store_v4").MemoryStore(state_dir)
    solver = solver_for(str(SCRIPTS.parent / REASONER02D), LEGEND02D) if REASONER02D else None
    return Agent02d(state_dir, reader_for(getattr(args, "model", "")),
                    talker_for(getattr(args, "gen_model", "")), solver, store,
                    int(getattr(args, "max_new", 0) or MAX_NEW02D))


# ------------------------------------------------------------------------------------------------ selftest
def selftest() -> None:
    import tempfile
    import claude_ep382_store_v4 as V4
    global RECALL_MODE02D
    RECALL_MODE02D = "bm25"
    ok = {}

    import claude_lis300_compiler as CMP
    rel = sorted(CMP.REL_NAMES)[0]

    class StubReader:
        def read(self, turn, prev="", hist=None):
            low = turn.lower()
            if "my dog is" in low:
                v = turn.rstrip(".").split()[-1]
                conf = 0.9 if low.startswith("maybe") else 0.999
                return ({"act": "ASSERT", "facts": [{"owner": "me", "rel": rel, "value": v, "mode": "ASSERT"}]},
                        [conf], "", 1.0)
            return ({"act": "CHAT", "facts": []}, [], "", 1.0)

    class StubTalker:
        hit_max = 0

        def __init__(self):
            self.seen = []

        def reply(self, system, msgs, max_new):
            self.seen.append((system, msgs, max_new))
            return "ok " + msgs[-1]["content"][:10]

    class StubSolver:
        def solve(self, puz):
            import itertools
            s = len(puz)
            for perm in itertools.permutations(range(1, s + 1)):
                g = [[perm[(r + c) % s] for c in range(s)] for r in range(s)]
                if all(not puz[r][c] or puz[r][c] == g[r][c] for r in range(s) for c in range(s)):
                    return g, 3
            return [row[:] for row in puz], 48

    with tempfile.TemporaryDirectory() as d:
        tk, sv = StubTalker(), StubSolver()

        def mk():
            return Agent02d(d, StubReader(), tk, sv, V4.MemoryStore(d))

        a = mk()
        r1 = a.turn("Today is May 3, 2023.\nhello there")
        ok["reply returned"] = r1 == ["ok Today is M"]
        ok["first turn: no W rows"] = "User said" not in tk.seen[-1][0]
        a.turn("My dog is Pip.")
        ok["confident fact saved as USER"] = [(a.nb.entities[f["subject"]], f["value"]["literal"])
                                              for f in a.nb.facts.values()] == [(USER, "Pip")]
        a.turn("maybe my dog is Rex")
        ok["below threshold not saved"] = len(a.nb.facts) == 1
        ok["W input holds earlier turns only"] = ('User said, "My dog is Pip."' in tk.seen[-1][0]
                                                  and 'User said, "maybe' not in tk.seen[-1][0])
        a.turn("My dog is Bo.")
        import fable_loop90_agent as L90
        ok["newest value wins"] = sorted(L90.notebook_triples(a.nb)) == [(USER, rel, "Bo")]
        ok["events logged"] = [e["op"] for e in a.nb.events] == ["teach", "correct"]
        ok["notes point at raw turns"] = all(r["source"] == "heard" for r in a.store.recall("dog", k=9, mode="bm25"))
        a.turn("Can you finish this number square?\n1 2 _\n_ 3 1\n3 _ 2")
        ok["reasoner result reaches the talker"] = "1 2 3\n2 3 1\n3 1 2" in tk.seen[-1][0]
        a.turn("Finish this one:\n1 1 _\n_ 3 1\n3 _ 2")
        ok["clash square: no finished square offered"] = "no square fits" in tk.seen[-1][0]
        a.turn("thanks")
        ok["non-grid turn: no reasoner note"] = "Reasoner result" not in tk.seen[-1][0]
        ok["chat window <= 6 pairs + turn"] = len(tk.seen[-1][1]) == 2 * min(HIST_PAIRS, 6) + 1
        # restart from the same state dir
        b = mk()
        ok["facts survive restart"] = sorted(L90.notebook_triples(b.nb)) == [(USER, rel, "Bo")]
        ok["turn count and date survive restart"] = b.turn_no == 7 and b.said_at == "May 3, 2023."
        b.turn("hi again")
        ok["after restart the W input has day-1 turns"] = 'User said, "My dog is Bo."' in tk.seen[-1][0]
        log = [json.loads(x) for x in (Path(d) / LOG02D).read_text().splitlines()]
        ok["log: every turn, grid turns counted"] = len(log) == 8 and sum(r["reasoner_called"] for r in log) == 2
        # W falls back to the store when the chat does not fit
        big = "word " * 3000
        b.turn(big)
        b.turn("anything about dogs?")
        ok["too long: store top-k used"] = json.loads((Path(d) / LOG02D).read_text().splitlines()[-1])["w"] == "top_k"
    for name, v in ok.items():
        print(("PASS " if v else "FAIL ") + name)
    print("E2E02D-WIRING-SELFTEST " + ("PASS" if all(ok.values()) else "FAIL") + f" {sum(ok.values())}/{len(ok)}")
    if not all(ok.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    if sys.argv[1:] == ["selftest"]:
        selftest()
    else:
        print(__doc__)
