#!/usr/bin/env python3
"""H5 (Director helper, 2026-09-28): the glue between reader, reasoner and talker for the first joined test, with MOCKED models
so the plumbing runs on a CPU box with no torch. Design and the learned/scaffold table: artifacts/claude-dir-h5-e2e-glue-20260928/GLUE.md.

What is real here: the interface formats (schemas), the S7 gate (claude_lis300_compiler.check_fact when importable), the token
grid format of the square (constants copied from claude_rsn358a_envs.py:33-40), S1 parse, S2 check, H1 note, G2 serializer, G3
provenance, the ablation switches (noR, noRd, scaf, JC) and the log row the scorer reads.
What is MOCK (stand-ins so wiring can be tested; none is a learned part and none says anything about model quality):
  MockReader    reads the DEV-PLUMBING key=value turns of claude_dir_h5_panel.py; returns a lis-320-shaped frame + confidences
  MockCopier    stands in for gr-9 L9 with a layout-blind cell extractor, returning L9's output shape
  MockSolver    a backtracking search with LoopSolver's signature solve(puz) -> (grid, rounds)
  MockTalker    parses the fixed blocks in its system text; it has Talker.reply's signature; it is NOT a language model
  MockStore     word-overlap recall standing in for store v4 (BM25 + frozen MiniLM)
Real models drop in by matching the signatures: Reader319.read(turn, prev, history) -> (frame, confs, raw, ms);
Copier5.copy(text) -> {"raw","grid","complete"}; LoopSolver.solve(puz) -> (grid, rounds); Talker.reply(system, msgs, max_new) -> str.

  python -B scripts/claude_dir_h5_glue.py selftest
  python -B scripts/claude_dir_h5_glue.py rehearse --panel DIR --out DIR      (mock arms over a DEV panel; writes arm_*.jsonl)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

# ---- token grid constants: scripts/claude_rsn358a_envs.py:33-40 (copied; selftest cross-checks when that module imports)
BLANK, MASK, SYM = 0, 1, 12
KIND_CONSTANT = None               # kind-free nets (rsn-358u line): the loader forces env index FIXED_ENV=0 for every item (claude_rsn358u_run.py:33-41), so the request carries no kind
HIST_PAIRS = 6                     # claude_e2e02d.HIST_PAIRS
THRESHOLD = 0.995                  # lis-320's gate (S7)
NOTEBOOK_K = 6

# ---- fixed frames the talker sees (SCAFFOLD, disclosed; the talker is untrained, so these are instructions, not training text)
INSTRUCTION = ("You are a friendly personal assistant chatting with one user. Answer their questions only from what they have told "
               "you in this chat. If they never told you something, say \"I don't know\" and do not guess. Keep replies short.")
FACTS_HEAD = "Facts saved from earlier messages, oldest first (each line ends with the user's own words):\n"
TURNS_HEAD = "Earlier messages from the user, oldest first:\n"
SOLVED_HEAD = "\n\nReasoner result for the number square in the last message (checked):\n"          # H1, claude_e2e02d.py:240-246
UNSOLVED = "\n\nReasoner result for the number square in the last message: no square fits its clues."


# ------------------------------------------------------------------------------------------------ interface contracts
def is_grid(g, s=None):
    return (isinstance(g, list) and g and all(isinstance(r, list) and len(r) == len(g) and all(isinstance(v, int) for v in r) for r in g)
            and (s is None or len(g) == s))


def check_frame(fr, confs):
    """I1  reader out (lis-320 / Reader319.read): {"act": str, "facts": [{"owner","rel","value","mode"}]} and one confidence per fact"""
    return (isinstance(fr, dict) and isinstance(fr.get("act"), str) and isinstance(fr.get("facts", []), list)
            and all(isinstance(f, dict) and {"owner", "rel", "value"} <= set(f) for f in fr.get("facts", []))
            and isinstance(confs, list) and len(confs) == len(fr.get("facts", [])) and all(0.0 <= c <= 1.0 for c in confs))


def check_copy(c):
    """I2  square reader out (gr-9 L9 / Copier5.copy): raw is 'none' or s lines of s cells (digit or _) separated by single spaces"""
    if not (isinstance(c, dict) and {"raw", "grid", "complete"} <= set(c)):
        return False
    if c["grid"] is None:
        return True
    return is_grid(c["grid"]) and 3 <= len(c["grid"]) <= 9 and all(0 <= v <= len(c["grid"]) for r in c["grid"] for v in r)


def check_request(rq):
    """I3  glue -> reasoner: token grid in claude_rsn358a_envs' vocabulary. Clue v -> SYM+v-1, blank -> MASK; two legend rows (blank row, SYM..SYM+s-1)"""
    if not (isinstance(rq, dict) and {"size", "grid", "tokens", "slot", "legend", "env"} <= set(rq)):
        return False
    s = rq["size"]
    rows = s + (2 if rq["legend"] else 0)
    return (is_grid(rq["grid"], s) and len(rq["tokens"]) == rows and all(len(r) == s for r in rq["tokens"]) and len(rq["slot"]) == rows
            and all(rq["tokens"][r][c] == (SYM + rq["grid"][r][c] - 1 if rq["grid"][r][c] else MASK) for r in range(s) for c in range(s))
            and all(rq["slot"][r][c] == (0 if rq["grid"][r][c] else 1) for r in range(s) for c in range(s))
            and (not rq["legend"] or (rq["tokens"][s] == [BLANK] * s and rq["tokens"][s + 1] == [SYM + k for k in range(s)])))


def check_result(rs):
    """I4  reasoner out: filled grid (ints 1..s) and the number of rounds used. 'stop' says which stop rule ended it."""
    return isinstance(rs, dict) and is_grid(rs.get("grid")) and isinstance(rs.get("rounds"), int) and rs.get("stop") in ("steady3", "learned", "mock")


def check_verdict(v):
    """I5  S2: the code check of the result against the copied square"""
    return isinstance(v, dict) and v.get("status") in ("checked", "failed_check", "clash", "no_grid") and "grid" in v


THOUGHT_KINDS = {"fact", "solution", "no_solution", "recall_turn"}


def check_thought(t):
    """I6  the shared currency handed to the talker. src: which stage produced it. source_text: the user's own words, verbatim."""
    return (isinstance(t, dict) and t.get("src") in ("reader", "reasoner", "notebook") and t.get("kind") in THOUGHT_KINDS
            and isinstance(t.get("turn"), int) and isinstance(t.get("body"), dict)
            and (t.get("source_turn") is None or isinstance(t.get("source_turn"), int))
            and (t.get("source_text") is None or isinstance(t.get("source_text"), str)))


# ------------------------------------------------------------------------------------------------ glue pieces
def gate(frame, confs, turn, prev, threshold=THRESHOLD):
    """S7 (SCAFFOLD inside the learned reader's path): a fact is kept only if the lis-300 compiler finds it structurally writable
    and its confidence >= threshold (scripts/claude_lis319_fullclaim.py:48-54)."""
    import claude_lis300_compiler as CMP
    out = []
    for i, f in enumerate((frame or {}).get("facts") or []):
        if isinstance(f, dict) and CMP.check_fact(f, turn, prev) is None and (confs[i] if i < len(confs) else 0.0) >= threshold:
            out.append(f)
    return out


def to_request(grid, legend=True):
    """S1 (SCAFFOLD, mechanical): the copied square -> the reasoner's token grid. Mirrors claude_rsn358b2_bridge.item_of."""
    s = len(grid)
    tokens = [[SYM + v - 1 if v else MASK for v in row] for row in grid]
    slot = [[0 if v else 1 for v in row] for row in grid]
    if legend:
        tokens += [[BLANK] * s, [SYM + k for k in range(s)]]
        slot += [[0] * s, [0] * s]
    return {"size": s, "grid": [row[:] for row in grid], "tokens": tokens, "slot": slot, "legend": legend, "env": KIND_CONSTANT}


def clash_of(grid):
    s = len(grid)
    for line in list(grid) + [list(c) for c in zip(*grid)]:
        cl = [v for v in line if v]
        if len(cl) != len(set(cl)):
            return True
    return False


def is_solution(puz, grid):
    """S2 (SCAFFOLD): claude_rsn358b2_bridge.is_solution"""
    s = len(puz)
    full = set(range(1, s + 1))
    if grid is None or any(puz[r][c] and puz[r][c] != grid[r][c] for r in range(s) for c in range(s)):
        return False
    return all(set(grid[r]) == full for r in range(s)) and all({grid[r][c] for r in range(s)} == full for c in range(s))


def verdict_of(req, result):
    if clash_of(req["grid"]):
        return {"status": "clash", "grid": None, "rounds": result["rounds"] if result else None}
    if result is None:
        return {"status": "no_grid", "grid": None, "rounds": None}
    ok = is_solution(req["grid"], result["grid"])
    return {"status": "checked" if ok else "failed_check", "grid": result["grid"] if ok else None, "rounds": result["rounds"]}


def thoughts_from_reader(facts, turn_no, turn_text):
    """reader facts -> I6 thoughts; each fact carries the turn it came from and that turn word for word (the notebook's pointer)"""
    return [{"src": "reader", "kind": "fact", "turn": turn_no,
             "body": {"owner": f["owner"], "rel": f["rel"], "value": f["value"], "mode": f.get("mode", "ASSERT")},
             "source_turn": turn_no, "source_text": turn_text} for f in facts]


def thought_from_verdict(v, turn_no):
    if v["status"] == "checked":
        return {"src": "reasoner", "kind": "solution", "turn": turn_no, "body": {"grid": v["grid"], "rounds": v["rounds"]},
                "source_turn": turn_no, "source_text": None}
    return {"src": "reasoner", "kind": "no_solution", "turn": turn_no, "body": {"status": v["status"]}, "source_turn": turn_no, "source_text": None}


def serialize(thoughts, w_turns):
    """G2 (SCAFFOLD, a text template with no decisions): thoughts -> the talker's system-message tail. Facts and raw turns are shown in
    time order, never merged and never superseded by code: which fact is newest is the talker's business (F1 stays out)."""
    parts = ""
    facts = sorted((t for t in thoughts if t["kind"] == "fact"), key=lambda t: t["turn"])
    if facts:
        parts += "\n\n" + FACTS_HEAD + "".join('- turn %d: %s | %s | %s | said: "%s"\n' % (
            t["turn"], t["body"]["owner"], t["body"]["rel"], t["body"]["value"], t["source_text"]) for t in facts)
    if w_turns:
        parts += "\n\n" + TURNS_HEAD + "".join('User said, "%s"\n' % x["text"] for x in w_turns)
    for t in thoughts:
        if t["kind"] == "solution":
            parts += SOLVED_HEAD + "\n".join(" ".join(map(str, r)) for r in t["body"]["grid"])
        elif t["kind"] == "no_solution":
            parts += UNSOLVED
    return INSTRUCTION + parts


def provenance(reply, thoughts, w_turns, chat_turns):
    """G3 / S6 (SCAFFOLD, allowed by Ben's list): attach a source only if it is a verbatim substring of a user turn of this chat AND
    holds a value the reply states. Returns (sources, unsupported_flag_inputs)."""
    def wb(text, needle):
        return needle and re.search(r"(?<![A-Za-z0-9])" + re.escape(needle) + r"(?![A-Za-z0-9])", text, re.I) is not None
    out = []
    cands = [(t["body"]["value"], t["source_text"]) for t in thoughts if t["kind"] == "fact"] + [(None, x["text"]) for x in w_turns]
    for val, src in cands:
        if src and src not in out and any(src in u for u in chat_turns):
            stated = [v for v, s in cands if s == src and v] if val is None else [val]
            if any(wb(reply, v) for v in stated) or (val is None and any(wb(reply, v) for v in {c[0] for c in cands if c[0]} if wb(src, v))):
                out.append(src)
    return out


# ------------------------------------------------------------------------------------------------ mock models (plumbing only)
class MockReader:
    """Reads only DEV-PLUMBING 'fact owner=.. rel=.. value=..' lines. Returns a lis-320-shaped frame (mode ASSERT/CORRECT)."""
    PAT = re.compile(r"\[DEV-PLUMBING\] fact owner=(?P<o>.+?) rel=(?P<r>\S+) value=(?P<v>.+?)(?: mode=(?P<m>\w+))?(?: pronoun=\S*)?$")

    def read(self, turn, prev_reply="", history=None):
        m = self.PAT.match(turn.strip())
        if not m:
            return {"act": "CHAT", "facts": []}, [], "", 1.0
        mode = m.group("m") or "ASSERT"
        f = {"owner": m.group("o"), "rel": m.group("r"), "value": m.group("v"), "mode": mode}
        return {"act": mode, "facts": [f]}, [0.999], "", 1.0


class MockCopier:
    """stand-in for gr-9 L9, plumbing only: a tolerant layout-blind cell extractor (NOT the hand parser read_latin, which reads only
    row/bare/comma/pipe layouts). Output shape = Copier5.copy: {"raw","grid","complete"}"""
    LABEL = re.compile(r"^\s*(?:row\s*\d+\s*[-:.)]?|r\d+\s*:|\d+\s*\)|[A-Z]\s*:|\d+\s*\|)\s*", re.I)

    def copy(self, text):
        cells = []
        for line in text.splitlines():
            if line.startswith("[DEV-PLUMBING]"):
                cells.append(None)
                continue
            cells.append(re.findall(r"_|\d+", self.LABEL.sub("", line)))
        for s in range(9, 2, -1):
            run = []
            best = None
            for c in cells + [None]:
                if c is not None and len(c) == s:
                    run.append(c)
                else:
                    if len(run) >= s:
                        best = run[-s:]
                    run = []
            if best:
                grid = [[0 if x == "_" else int(x) for x in row] for row in best]
                if all(v <= s for r in grid for v in r):
                    return {"raw": "\n".join(" ".join("_" if v == 0 else str(v) for v in r) for r in grid), "grid": grid, "complete": True}
        return {"raw": "none", "grid": None, "complete": True}


class MockSolver:
    """stand-in for LoopSolver: exhaustive search, returns (grid, rounds). On a clash it returns the clues unchanged."""

    def solve(self, puz):
        s = len(puz)
        g = [r[:] for r in puz]

        def ok(r, c, v):
            return all(g[r][j] != v for j in range(s) if j != c) and all(g[i][c] != v for i in range(s) if i != r)

        def go():
            for r in range(s):
                for c in range(s):
                    if g[r][c] == 0:
                        for v in range(1, s + 1):
                            if ok(r, c, v):
                                g[r][c] = v
                                if go():
                                    return True
                                g[r][c] = 0
                        return False
            return True
        return (g if go() else [r[:] for r in puz]), 3


class MockStore:
    """word-overlap recall standing in for store v4; keeps every user turn verbatim (source 'heard')"""

    def __init__(self):
        self.rows = []

    def remember(self, text, source, turn):
        self.rows.append({"text": text, "source": source, "turn": turn})

    @staticmethod
    def _tok(t):
        return {w for w in re.findall(r"[a-z0-9]+", t.lower().replace("dev", " ")) if w not in {"plumbing", "ask", "fact", "owner", "rel", "value", "kind"}}

    def recall(self, query, k=NOTEBOOK_K, source="heard"):
        q = self._tok(query.replace("me", "user"))
        scored = [(len(q & self._tok(r["text"].replace(" me ", " user "))), r["turn"], r) for r in self.rows if r["source"] == source]
        top = sorted((x for x in scored if x[0] > 0), key=lambda x: (-x[0], -x[1]))[:k]
        return sorted((x[2] for x in top), key=lambda r: r["turn"])


class MockTalker:
    """NOT a language model. Parses the fixed blocks of its system text and the plumbing 'ask' in the last user message, so a test can see
    whether information really travelled reader -> notebook -> serializer -> talker. Signature = claude_e2e02d.Talker.reply."""
    hit_max = 0
    ASK = re.compile(r"ask owner=(?P<o>.+?) rel=(?P<r>\S+)")

    def reply(self, system, msgs, max_new):
        last = msgs[-1]["content"]
        m = self.ASK.search(last)
        if "ask kind=" in last or "ask kind" in last:
            if "no square fits" in system:
                return "That square has no solution."
            if SOLVED_HEAD.strip() in system:
                rows = system.split("(checked):\n", 1)[1].strip().splitlines()
                return "Here it is:\n" + "\n".join(r for r in rows if re.fullmatch(r"[\d ]+", r.strip()))
            return "I can't work that square out."
        if m:
            o, r = m.group("o"), m.group("r")
            key_o = {"me": "USER"}.get(o, o)
            hits = []
            for line in system.splitlines():                               # saved facts and raw turns are both readable
                fm = re.match(r"- turn (\d+): (.+?) \| (.+?) \| (.+?) \| said:", line)
                if fm and fm.group(2) == key_o and fm.group(3) == r:
                    hits.append((int(fm.group(1)), fm.group(4)))
                rm = re.match(r'User said, "\[DEV-PLUMBING\] fact owner=(.+?) rel=(\S+) value=(.+?)(?: mode=\w+)?(?: pronoun=\S*)?"$', line)
                if rm and rm.group(1) in (o, key_o) and rm.group(2) == r:
                    hits.append((-1, rm.group(3)))
            if hits:
                return "It is %s." % sorted(hits)[-1][1]
            return "I don't know."
        return "OK."


# ------------------------------------------------------------------------------------------------ the agent (G1-G4 wired)
class AgentH5:
    """One arm of the joined test. Flags: noR (reasoner note removed), noRd (reader notes and thought lines removed: raw turns only),
    scaf (the hand parser finds the square instead of L9). The models are passed in, so real ones drop in by signature."""

    def __init__(self, reader, copier, solver, talker, store, noR=False, noRd=False, scaf=False, max_new=160):
        self.reader, self.copier, self.solver, self.talker, self.store = reader, copier, solver, talker, store
        self.noR, self.noRd, self.scaf, self.max_new = noR, noRd, scaf, max_new
        self.pairs, self.turn_no, self.chat = [], 0, []
        self.facts_saved = []                                           # reader-saved thoughts (the notebook's notes)

    def _square(self, text):
        if self.scaf:
            import claude_puzzle_reader as P
            g = P.read_latin(text)
            return {"raw": "hand", "grid": g["grid"] if g else None, "complete": True}
        return self.copier.copy(text)

    def turn(self, text):
        t0 = time.time()
        self.turn_no += 1
        prev = self.pairs[-1][1] if self.pairs else ""
        frame, confs, _raw, read_ms = self.reader.read(text, prev, self.pairs[-HIST_PAIRS:])
        assert check_frame(frame, confs), "I1 broken"
        facts = gate(frame, confs, text, prev)
        cp = self._square(text)
        assert check_copy(cp), "I2 broken"
        thoughts, called, verdict = [], False, None
        if cp["grid"] is not None and not self.noR:
            req = to_request(cp["grid"])
            assert check_request(req), "I3 broken"
            if clash_of(req["grid"]):
                res = None                                              # a clash is not sent to the net; the check reports it
            else:
                g, rounds = self.solver.solve(req["grid"])
                res = {"grid": g, "rounds": rounds, "stop": "mock"}
                assert check_result(res), "I4 broken"
            called = res is not None
            verdict = verdict_of(req, res)
            assert check_verdict(verdict), "I5 broken"
            thoughts.append(thought_from_verdict(verdict, self.turn_no))
        # notebook: what the talker sees. noRd: raw turns only (recall over turns), no reader thoughts
        query = text
        w_turns = self.store.recall(query, k=NOTEBOOK_K, source="heard")
        if not self.noRd:
            note_rows = self.store.recall(query, k=NOTEBOOK_K, source="note")
            byturn = {t["turn"]: t for t in self.facts_saved}
            for r in note_rows:
                if r["turn"] in byturn:
                    thoughts.append(byturn[r["turn"]])
            w_turns = [x for x in w_turns if x["turn"] not in {t["turn"] for t in thoughts if t["kind"] == "fact"}]
        assert all(check_thought(t) for t in thoughts), "I6 broken"
        system = serialize(thoughts, w_turns)
        msgs = []
        for u, a in self.pairs[-HIST_PAIRS:]:
            msgs += [{"role": "user", "content": u}, {"role": "assistant", "content": a}]
        msgs.append({"role": "user", "content": text})
        reply = self.talker.reply(system, msgs, self.max_new)
        sources = provenance(reply, [t for t in thoughts if t["kind"] == "fact"], w_turns, self.chat + [text]) if not self.noRd or w_turns else []
        # after the reply: keep the turn word for word, keep the reader's facts as pointers to it
        self.store.remember(text, "heard", self.turn_no)
        self.chat.append(text)
        new = thoughts_from_reader(facts, self.turn_no, text)
        for th in new:
            self.store.remember("%s %s %s" % (th["body"]["owner"].replace("me", "USER") if th["body"]["owner"] == "me" else th["body"]["owner"],
                                              th["body"]["rel"], th["body"]["value"]), "note", self.turn_no)
        for th in new:
            if th["body"]["owner"] == "me":
                th["body"]["owner"] = "USER"
        self.facts_saved += new
        self.pairs.append((text, reply))
        self.last = {"reasoner_called": called, "l9_grid": cp["grid"] is not None, "sources": sources, "verdict": verdict,
                     "saved": len(facts), "read_ms": read_ms, "ms": round((time.time() - t0) * 1000, 2)}
        return reply


def jc_reply(truth_row):
    """J-C (ceiling, validity only): the panel's TRUE puzzle goes straight to the reasoner; no reader, no talker. Needs the truth file,
    so it is run by the scorer's owner, never by a model runner; the reply is the checked grid as plain rows."""
    req = to_request(truth_row["puzzle"])
    g, rounds = MockSolver().solve(req["grid"])
    v = verdict_of(req, {"grid": g, "rounds": rounds, "stop": "mock"})
    return ("\n".join(" ".join(map(str, r)) for r in v["grid"])) if v["status"] == "checked" else "no square fits"


# ------------------------------------------------------------------------------------------------ rehearsal over a DEV panel
def rehearse(panel: Path, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    turns = [json.loads(x) for x in (panel / "turns.jsonl").read_text().splitlines() if x.strip()]
    truth = [json.loads(x) for x in (panel / "answers.jsonl").read_text().splitlines() if x.strip()]
    lives = {}
    for t in turns:
        lives.setdefault(t["life_id"], []).append(t)
    arms = {"J_s13": {}, "Jscaf_s13": {"scaf": True}, "JnoR_s13": {"noR": True}, "JnoRd_s13": {"noRd": True}}
    for name, flags in arms.items():
        rows = []
        for lid, ts in lives.items():
            ag = AgentH5(MockReader(), MockCopier(), MockSolver(), MockTalker(), MockStore(), **flags)
            for t in ts:
                reply = ag.turn(t["text"])
                rows.append({"id": t["id"], "reply": reply, "hit_max": 0, "reasoner_called": ag.last["reasoner_called"],
                             "l9_grid": ag.last["l9_grid"], "sources": ag.last["sources"], "s6_removed": False, "ms": ag.last["ms"]})
        (out / ("arm_%s.jsonl" % name)).write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
        (out / ("meta_%s.json" % name)).write_text(json.dumps({"crashes": 0, "models": {"MOCK": {"sha256": "0" * 64, "revision": "mock"}}}))
    by = {r["id"]: r for r in truth}
    rows = []
    for tr in truth:
        if tr["item"] in ("solve5", "solve6", "solve7"):
            rows.append({"id": tr["id"], "reply": jc_reply(tr), "hit_max": 0, "reasoner_called": True, "l9_grid": None, "sources": None,
                         "s6_removed": False, "ms": 0})
    (out / "arm_JC_s13.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (out / "meta_JC_s13.json").write_text(json.dumps({"crashes": 0, "models": {"MOCK": {"sha256": "0" * 64, "revision": "mock"}}}))
    return list(arms) + ["JC_s13"]


# ------------------------------------------------------------------------------------------------ selftest
def selftest():
    import tempfile
    import claude_dir_h5_panel as PN
    import claude_dir_h5_score as SC
    ok = {}
    try:
        import claude_rsn358a_envs as E
        ok["token constants equal claude_rsn358a_envs"] = (E.BLANK, E.MASK, E.SYM) == (BLANK, MASK, SYM)
    except Exception as e:
        print("note: claude_rsn358a_envs not importable (%s); constants not cross-checked" % type(e).__name__)
    g = [[1, 0, 3], [0, 3, 0], [3, 0, 2]]
    rq = to_request(g)
    ok["I3 request is well formed"] = check_request(rq) and rq["tokens"][0] == [SYM, MASK, SYM + 2] and rq["tokens"][4] == [SYM, SYM + 1, SYM + 2]
    ok["I3 request rejects a wrong token"] = not check_request(dict(rq, tokens=[[0] * 3] * 5))
    s2 = MockSolver().solve([[1, 0, 0], [0, 0, 0], [0, 0, 0]])[0]
    ok["S2 accepts a real solution, rejects a broken clue"] = is_solution([[1, 0, 0], [0, 0, 0], [0, 0, 0]], s2) and not is_solution([[2, 0, 0], [0, 0, 0], [0, 0, 0]], s2)
    ok["clash is reported, not solved"] = verdict_of(to_request([[1, 1, 0], [0, 0, 0], [0, 0, 0]]), None)["status"] == "clash"
    ok["I2 accepts 'none' and a grid"] = check_copy({"raw": "none", "grid": None, "complete": True}) and check_copy(MockCopier().copy("1 _ 3\n_ 3 _\n3 _ 2"))
    fr, cf, _, _ = MockReader().read("[DEV-PLUMBING] fact owner=me rel=sister value=Zorvan")
    ok["I1 frame from the mock reader is well formed"] = check_frame(fr, cf)
    ok["S7 gate keeps a span-backed fact"] = len(gate(fr, cf, "[DEV-PLUMBING] fact owner=me rel=sister value=Zorvan", "")) == 1
    ok["S7 gate drops a low-confidence fact"] = gate(fr, [0.9], "[DEV-PLUMBING] fact owner=me rel=sister value=Zorvan", "") == []
    fr2, cf2, _, _ = MockReader().read("[DEV-PLUMBING] fact owner=he rel=employer value=Kelm Works")
    ok["S7 gate drops a pronoun owner (the known backref failure, kept honest)"] = gate(fr2, cf2, "[DEV-PLUMBING] fact owner=he rel=employer value=Kelm Works", "") == []
    th = thoughts_from_reader(gate(fr, cf, "[DEV-PLUMBING] fact owner=me rel=sister value=Zorvan", ""), 3, "[DEV-PLUMBING] fact owner=me rel=sister value=Zorvan")
    ok["I6 thought from a reader fact is well formed"] = all(check_thought(t) for t in th)
    txt = serialize(th, [])
    ok["G2 serializer shows the fact and the user's own words"] = "turn 3: me | sister | Zorvan" in txt and "said: \"[DEV-PLUMBING]" in txt
    # agent, one life by hand
    ag = AgentH5(MockReader(), MockCopier(), MockSolver(), MockTalker(), MockStore())
    ag.turn("[DEV-PLUMBING] fact owner=me rel=sister value=Zorvan")
    r = ag.turn("[DEV-PLUMBING] ask owner=me rel=sister")
    ok["fact travels reader -> notebook -> serializer -> talker"] = r == "It is Zorvan."
    ok["source is the user's own turn, verbatim"] = ag.last["sources"] == ["[DEV-PLUMBING] fact owner=me rel=sister value=Zorvan"]
    r = ag.turn("[DEV-PLUMBING] ask owner=me rel=doctor")
    ok["nothing told -> talker says I don't know, no source"] = r == "I don't know." and ag.last["sources"] == []
    ag.turn("[DEV-PLUMBING] fact owner=me rel=sister value=Nelbrun mode=CORRECT")
    ok["newest of two told values wins in the talker (time order, no code rule)"] = ag.turn("[DEV-PLUMBING] ask owner=me rel=sister") == "It is Nelbrun."
    sq = "[DEV-PLUMBING] ask kind=solve\n1 _ 3\n_ 3 _\n3 _ 2"
    r = ag.turn(sq)
    ok["square: L9 -> request -> reasoner -> check -> note -> talker retells rows"] = ag.last["reasoner_called"] and "1 2 3" in r and ag.last["verdict"]["status"] == "checked"
    ok["non-square turn: reasoner not called"] = (ag.turn("[DEV-PLUMBING] smalltalk topic=food") == "OK.") and not ag.last["reasoner_called"]
    ag2 = AgentH5(MockReader(), MockCopier(), MockSolver(), MockTalker(), MockStore(), noR=True)
    ok["ablation noR: grid seen, reasoner not called, talker cannot retell"] = ag2.turn(sq) == "I can't work that square out." and not ag2.last["reasoner_called"]
    ag3 = AgentH5(MockReader(), MockCopier(), MockSolver(), MockTalker(), MockStore(), noRd=True)
    ag3.turn("[DEV-PLUMBING] fact owner=me rel=sister value=Zorvan")
    ok["ablation noRd: raw turns still reach the talker (cannot be worse than raw retrieval)"] = ag3.turn("[DEV-PLUMBING] ask owner=me rel=sister") == "It is Zorvan."
    clash = "[DEV-PLUMBING] ask kind=solve\n1 1 _\n_ 3 _\n3 _ 2"
    ok["clash square: no reasoner call, 'no solution' note"] = AgentH5(MockReader(), MockCopier(), MockSolver(), MockTalker(), MockStore()).turn(clash) == "That square has no solution."
    # rehearsal over the DEV sample and the scorer in rehearsal mode
    with tempfile.TemporaryDirectory() as td:
        d = Path(td) / "p"
        PN.cmd_make(argparse.Namespace(mode="dev", profile="dev6", out=str(d), truth_dir=None, seeds_file=None))
        names = rehearse(d, d)
        rep = SC.evaluate(d, rehearsal=True)
        s = rep["summary"]
        ok["rehearsal wrote all mock arms"] = set(names) <= set(rep["arms_found"])
        ok["scorer reads the glue's log rows (rehearsal counts)"] = s["J_s13"]["solve56_n"] == 4
        print("  mock arms, counts only (plumbing, not model quality):")
        for a in names:
            print("   ", a, {k: v for k, v in s[a].items() if k in ("solve56_right", "solve56_n", "solve7_right", "ans_right", "ans_n", "never_idk", "look_reasoner_called")})
        ok["mock J solves every 5/6 square (mock L9 is layout-blind)"] = s["J_s13"]["solve56_right"] == s["J_s13"]["solve56_n"] > 0
        ok["Jscaf (hand parser) reads fewer squares than J on exotic layouts"] = s["Jscaf_s13"]["solve56_right"] < s["J_s13"]["solve56_right"]
        ok["mock JnoR solves none (reasoner removed)"] = s["JnoR_s13"]["solve56_right"] == 0
        ok["mock J-C solves every 5/6 item"] = s["JC_s13"]["solve56_right"] == s["JC_s13"]["solve56_n"]
    for k, v in ok.items():
        print(("PASS " if v else "FAIL ") + k)
    print("selftest: %d of %d checks pass" % (sum(ok.values()), len(ok)))
    if not all(ok.values()):
        raise SystemExit(1)


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("selftest")
    r = sp.add_parser("rehearse")
    r.add_argument("--panel", required=True)
    r.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.cmd == "selftest":
        selftest()
    else:
        print("wrote arms:", rehearse(Path(a.panel), Path(a.out)))


if __name__ == "__main__":
    main()
