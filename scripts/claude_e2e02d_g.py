#!/usr/bin/env python3
"""0.2d-G: the 0.2d build with rd-378g's note writer G in the notes slot (design/v3/30-modes/02d-gates-ADDENDUM-52.md).
New file only. It imports scripts/claude_e2e02d.py (the unsealed 0.2d draft, pinned by other seals, not edited) and
replaces ONE step, the note step. DRAFT until 0.2d's seal, like claude_e2e02d.

The one change (ADDENDUM-52 fills ADDENDUM-20's notes slot; rd-378g verified PASS G1-G5 at 9d7a51c0f):
  before  N0 (claude_e2e02d): each fact the reader saves is also stored as a note row "owner relation value".
  after   G (NOTES02D) writes the note rows. On every user turn it gets the inputs rd-378g used: kind "chat", the date
          line (the build's said_at, D15), the earlier turns of this session (the user's turns and the talker's
          replies, oldest first; build_nprompt keeps the last 6) and the new turn, in one greedy call of
          claude_rd378_write.NoteWriter (the code G was scored with). Each note is stored as a note row that points at
          the raw user turn it was written on (turn_ids = [that turn], store v4). A turn whose output does not parse
          stores no note and is counted.
Everything else is claude_e2e02d as it is: the reader, the fact book (still fed by the reader's saved facts, F1), the
W input, the reasoner, the talker, and recall returning raw user turns only (store v4: a note is only a pointer).
N0 leaves the path. It comes back only as the fallback if the slot is ever emptied (NOTES02D = "").

What G is (rd-378g ADDENDUM-K's fixed wording): a search aid only, "trained on ungraded GLM and Luna notes; G's
unsupported share 49.2% vs R's 50.9% on fresh dialogs" (R = the rd-378 writer). Its G5 PASS means "no less true than
the rd-378 writer": the blind judges called about half of each writer's notes unsupported, so no G note is offered as
true. Answers read raw lines only. Search with G's notes (rd-378g G1, LoCoMo 5-9 practice): an evidence line in the
top 10 for 577 of 772 questions, against 489 with no notes and 585 with R's notes.

Hand-written parts this file adds (disclosed, each with what it stands in for):
  N1  a note row's text is G's note text plus its "when" in brackets, as rd-378g's scored store indexed it
      (claude_rd378L_recall.py:108-109). Report only, without it: 581 of 772 (rd-378g vast/notes_confirm_whenoff.json)
  N2  a note row points at the turn it was written on. G also writes cites (offsets to earlier turns); they are kept
      in memory (last_notes) for the checks but are not pointers here (rd-378g's scored store pointed at the cited
      turns; in a chat an offset of -1 is usually the talker's reply, which the store does not hold)

Slot: NOTES02D is G's merged model dir on this machine (E2E02D_NOTES moves it; it cannot fill an empty slot). The
weights are checked against NOTES_SHA02D before loading (fail closed). Rebuild them from the base and G's adapter with
  python -B scripts/claude_e2e02d_g.py merge --base <MiniCPM5-1B@87179e5c dir> --adapter <G's adapter dir> --out DIR
(rd-378g's trainer merge: base in bf16 on CUDA, fp32 elsewhere; peft merge_and_unload; the base's tokenizer).

Harness: scripts/claude_e2e336_run.py --arm claude_e2e02d_g:build_02d_g --model LIS320 --gen-model LFM (as 0.2d)
Logs: claude_e2e02d's per-turn log, unchanged, plus <state>/e2e02dg_notes.jsonl (counts only: notes, unparsed,
write_ms, n0_dropped), also to $E2E02D_LOG_DIR/<state dir name>.notes.jsonl when that is set.
  python -B scripts/claude_e2e02d_g.py selftest     (wiring only: stub reader, talker, solver and writer; no model
                                                      loaded; it says nothing about model quality)
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_e2e02d as B  # noqa: E402

# ---- the notes slot (ADDENDUM-52) ----
NOTES02D = "~/premonition-models/rd378g-merged"   # G's merged model dir; "" = slot empty, N0 fallback (ADDENDUM-20)
NOTES_SHA02D = "a0fb1c9bd663b00b1470d515ae0c38a8dd3ed7d1cfdead70325137312300d1ed"  # G merged model.safetensors
NOTES_ADAPTER02D = {     # G's adapter (rd-378g vast/SEAL-run.sha256.txt; the Mac copy matches, vast/COLLECT.txt)
    "README.md": "8443ad44b3ceac7a87bd9c33eb48bb592cbedf787347ec071fd651a84d3a5e20",
    "adapter_config.json": "ae8df4275c6cfe1b782ee55d4469113d19a02eeea5dd86fadcec7cfbd3ebbb03",
    "adapter_model.safetensors": "b1c69db46666e6dc68f41de760f6541a9174c4fbb92a26040b0edb208b064998",
    "chat_template.jinja": "7451a05cf1e28a79d97d7c0bc951028c0b1915119bf9046acd06a0e3d931f47c",
    "tokenizer.json": "3e065a558a034185fe299917b398685c1facd0169a9eea1e629eb30c171fed81",
    "tokenizer_config.json": "bd4a5446624eb938cd57c97b0be1914372a433df17efaac052aabed57ac3b26b",
}
NOTES_BASE02D = "openbmb/MiniCPM5-1B@87179e5c1f455ef22e6223592d2d61351b525bfc"
NOTES_KIND02D = "chat"   # the build hears a chat: rd-378g's kind "chat" (User / Assistant lines)
NOTES_LOG02D = "e2e02dg_notes.jsonl"
DISCLOSE02D = ("trained on ungraded GLM and Luna notes; G's unsupported share 49.2% vs R's 50.9% on fresh dialogs",
               "no less true than the rd-378 writer")


def notes_dir() -> str:
    """G's merged model dir on this machine: NOTES02D, moved by E2E02D_NOTES; "" when the slot is empty."""
    if not NOTES02D:
        return ""
    return os.path.expanduser(os.environ.get("E2E02D_NOTES") or NOTES02D)


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


_CACHE: dict = {}


def writer_for(model_dir: str, want_sha: str = NOTES_SHA02D):
    """G, loaded only when its merged weights match want_sha (fail closed; the check runs before any model code)."""
    if not model_dir:
        raise SystemExit("0.2d-G: the notes slot has no model dir")
    p = Path(model_dir) / "model.safetensors"
    if not p.is_file():
        raise SystemExit(f"0.2d-G: no G model at {p} (rebuild it: claude_e2e02d_g.py merge)")
    if (model_dir, want_sha) not in _CACHE:
        got = sha256_file(p)
        if got != want_sha:
            raise SystemExit(f"NOTES-SHA-MISMATCH: {got} != {want_sha}")
        import claude_rd378_write as W
        _CACHE[(model_dir, want_sha)] = W.NoteWriter(model_dir)
    return _CACHE[(model_dir, want_sha)]


def writer_for_slot():
    d = notes_dir()
    return writer_for(d) if d else None


# ------------------------------------------------------------------------------------------------ the note step
def earlier_turns(pairs) -> list[dict]:
    """This session's earlier turns as rd-378g's writer reads a chat: user turn, talker reply, oldest first."""
    out = []
    for u, a in pairs:
        out += [{"speaker": "user", "text": u}, {"speaker": "assistant", "text": a}]
    return out


def write_notes(write, kind: str, date, earlier: list, latest: dict):
    """G's note step on one turn: one call with rd-378g's inputs. -> (notes or None when unparsed, raw, ms)."""
    return write(kind, date or "", earlier, latest)


def note_row_text(n: dict) -> str:
    """N1: the note's text plus its "when" in brackets, as rd-378g's scored store indexed it."""
    when = f" ({n['when']})" if n.get("when") else ""
    return n["text"] + when


class NoteSlot:
    """The store as claude_e2e02d.Agent02d sees it. Every read and every heard row pass straight through; right after
    a heard row is written, G's note step runs for that turn; the base note step's N0 rows are counted and dropped."""

    def __init__(self, store, on_heard, on_n0):
        self._store, self._on_heard, self._on_n0 = store, on_heard, on_n0

    def __getattr__(self, name):
        return getattr(self._store, name)

    def remember(self, text, *, source, **kw):
        if source == "note":
            self._on_n0()
            return None
        rid = self._store.remember(text, source=source, **kw)
        if source == "heard":
            self._on_heard(text, kw)
        return rid


class Agent02dG(B.Agent02d):
    """claude_e2e02d.Agent02d with the note step replaced by G. writer=None (slot empty) = Agent02d exactly (N0)."""

    def __init__(self, state_dir, reader, talker, solver, store, writer, max_new: int = B.MAX_NEW02D):
        self._write = writer.write if writer is not None else None   # a bound method only, as the base keeps the reader
        self._raw_store = store
        self._cur: dict = {}
        self.last_notes = None
        if writer is not None:
            store = NoteSlot(store, self._note_step, self._n0)
        super().__init__(state_dir, reader, talker, solver, store, max_new)
        self.notes_logs = [self.dir / NOTES_LOG02D]
        if os.environ.get("E2E02D_LOG_DIR"):
            keep = Path(os.environ["E2E02D_LOG_DIR"])
            keep.mkdir(parents=True, exist_ok=True)
            self.notes_logs.append(keep / f"{self.dir.name}.notes.jsonl")

    def _n0(self) -> None:
        self._cur["n0_dropped"] = self._cur.get("n0_dropped", 0) + 1

    def _note_step(self, text: str, kw: dict) -> None:
        notes, _raw, ms = write_notes(self._write, NOTES_KIND02D, kw.get("said_at"), earlier_turns(self.pairs),
                                      {"speaker": "user", "text": text})
        for n in notes or []:
            self._raw_store.remember(note_row_text(n), source="note", speaker=kw.get("speaker", "user"),
                                     turn_ids=list(kw["turn_ids"]), said_at=kw.get("said_at"), logged_at=B._now())
        self.last_notes = notes
        self._cur.update(notes=len(notes or []), unparsed=notes is None, write_ms=round(ms, 1))

    def turn(self, text: str) -> list[str]:
        if self._write is None:
            return super().turn(text)
        self._cur = {"n0_dropped": 0}
        self.last_notes = None
        out = super().turn(text)
        row = {"turn": self.turn_no, "notes": self._cur.get("notes", 0), "unparsed": self._cur.get("unparsed", False),
               "write_ms": self._cur.get("write_ms"), "n0_dropped": self._cur["n0_dropped"]}
        for path in self.notes_logs:
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(row) + "\n")
        return out


def build_02d_g(state_dir, args):
    import importlib
    writer = writer_for_slot()          # checked first: a wrong G stops the run before any other model loads
    store = importlib.import_module("claude_ep382_store_v4").MemoryStore(state_dir)
    solver = B.solver_for(str(B.SCRIPTS.parent / B.REASONER02D), B.LEGEND02D) if B.REASONER02D else None
    return Agent02dG(state_dir, B.reader_for(getattr(args, "model", "")), B.talker_for(getattr(args, "gen_model", "")),
                     solver, store, writer, int(getattr(args, "max_new", 0) or B.MAX_NEW02D))


# ------------------------------------------------------------------------------------------------ rebuild G
def merge(base: str, adapter: str, out: str, autocast: bool = True) -> dict:
    """Rebuild G's merged model as rd-378g's trainer made it (claude_lis300_train.py --merge): the base in bf16 on CUDA
    (fp32 elsewhere), G's adapter on top, peft merge_and_unload, save_pretrained(safe_serialization=True) and the base's
    tokenizer. The adapter files are checked against NOTES_ADAPTER02D first (fail closed)."""
    for name, want in NOTES_ADAPTER02D.items():
        f = Path(adapter) / name
        got = sha256_file(f) if f.is_file() else "missing"
        if got != want:
            raise SystemExit(f"ADAPTER-SHA-MISMATCH {name}: {got} != {want}")
    import peft
    import torch
    import transformers
    from peft import PeftModel
    from safetensors import safe_open
    from transformers import AutoModelForCausalLM, AutoTokenizer
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.bfloat16 if dev == "cuda" else torch.float32
    with safe_open(str(Path(adapter) / "adapter_model.safetensors"), "pt") as fh:
        adapter_dtypes = sorted({str(fh.get_slice(k).get_dtype()) for k in fh.keys()})
    tok = AutoTokenizer.from_pretrained(base)
    model = AutoModelForCausalLM.from_pretrained(base, dtype=dtype).to(dev)
    model = PeftModel.from_pretrained(model, adapter, autocast_adapter_dtype=autocast)
    model.eval()
    merged = model.merge_and_unload()
    Path(out).mkdir(parents=True, exist_ok=True)
    merged.save_pretrained(out, safe_serialization=True)
    tok.save_pretrained(out)
    got = sha256_file(Path(out) / "model.safetensors")
    rep = {"device": dev, "gpu": torch.cuda.get_device_name(0) if dev == "cuda" else None, "dtype": str(dtype),
           "autocast_adapter_dtype": autocast, "adapter_dtypes": adapter_dtypes, "torch": torch.__version__,
           "transformers": transformers.__version__, "peft": peft.__version__, "merged_sha256": got,
           "matches_NOTES_SHA02D": got == NOTES_SHA02D,
           "tokenizer_json_matches_adapter": sha256_file(Path(out) / "tokenizer.json")
           == NOTES_ADAPTER02D["tokenizer.json"]}
    print(json.dumps(rep))
    return rep


# ------------------------------------------------------------------------------------------------ selftest
def selftest() -> None:
    import tempfile
    import claude_ep382_store_v4 as V4
    import claude_lis300_compiler as CMP
    import fable_loop90_agent as L90
    global NOTES02D
    mode0 = B.RECALL_MODE02D
    B.RECALL_MODE02D = "bm25"
    ok = {}
    rel = sorted(CMP.REL_NAMES)[0]

    class StubReader:        # claude_e2e02d's selftest reader: "my dog is X" saved at 0.999, "maybe ..." at 0.9
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
            self.seen.append((system, [dict(m) for m in msgs], max_new))
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

    class StubWriter:        # stands in for G: a note on any dog or vet turn, unparsed on "gibberish", else no note
        def __init__(self):
            self.calls = []

        def write(self, kind, date, earlier, latest):
            self.calls.append((kind, date, [dict(t) for t in earlier], dict(latest)))
            low = latest["text"].lower()
            if "gibberish" in low:
                return None, "not json", 2.0
            if "dog" in low or "vet" in low:
                return ([{"text": "Note on: " + latest["text"][:24], "cites": [0, -2],
                          "when": "yesterday" if "yesterday" in low else None}], "{}", 2.0)
            return [], '{"notes": []}', 1.0

    turns = ["Today is May 3, 2023.\nhello there", "My dog is Pip.", "maybe my dog is Rex", "gibberish words here",
             "Yesterday the vet saw Pip.", "My dog is Bo.",
             "Can you finish this number square?\n1 2 _\n_ 3 1\n3 _ 2", "thanks"]

    def heard_of(agent):
        return [r for r in agent.store.rows if r["source"] == "heard"]

    def notes_of(agent):
        return [r for r in agent.store.rows if r["source"] == "note"]

    with tempfile.TemporaryDirectory() as d:
        da, dg = Path(d) / "a", Path(d) / "g"
        da.mkdir()
        dg.mkdir()
        ta, tg, w = StubTalker(), StubTalker(), StubWriter()
        a = B.Agent02d(da, StubReader(), ta, StubSolver(), V4.MemoryStore(da))
        g = Agent02dG(dg, StubReader(), tg, StubSolver(), V4.MemoryStore(dg), w)
        ra, rg, got_notes = [], [], []
        for t in turns:
            ra.append(a.turn(t))
            rg.append(g.turn(t))
            got_notes.append(g.last_notes)
        # W3: nothing else moved (0.2d and 0.2d-G side by side on the same turns, same stubs)
        ok["W3 same replies"] = ra == rg
        ok["W3 the talker saw the same input on every turn"] = ta.seen == tg.seen and len(tg.seen) == len(turns)
        ok["W3 fact book as 0.2d's (the reader's saved facts)"] = (a.nb.facts == g.nb.facts and a.nb.events == g.nb.events
                                                                  and sorted(L90.notebook_triples(g.nb)) == [(B.USER, rel, "Bo")])
        key = ("id", "text", "source", "speaker", "turn_ids", "said_at")
        ok["W3 heard rows as 0.2d's"] = ([tuple(r[k] for k in key) for r in heard_of(a)]
                                         == [tuple(r[k] for k in key) for r in heard_of(g)])
        la = [json.loads(x) for x in (da / B.LOG02D).read_text().splitlines()]
        lg = [json.loads(x) for x in (dg / B.LOG02D).read_text().splitlines()]
        ok["W3 0.2d's per-turn log unchanged but for time"] = ([{k: v for k, v in r.items() if k != "ms"} for r in la]
                                                               == [{k: v for k, v in r.items() if k != "ms"} for r in lg])
        # the one change: N0 rows out, G rows in
        n0 = [r["text"] for r in notes_of(a)]
        nl = [json.loads(x) for x in (dg / NOTES_LOG02D).read_text().splitlines()]
        ok["N0 rows gone (counted as dropped)"] = (len(n0) == 2 and not set(n0) & {r["text"] for r in notes_of(g)}
                                                   and sum(r["n0_dropped"] for r in nl) == len(n0))
        ok["G called once per user turn"] = len(w.calls) == len(turns)
        want_inputs, pairs = [], []
        for t, r in zip(turns, rg):
            want_inputs.append(("chat", "May 3, 2023.", earlier_turns(pairs), {"speaker": "user", "text": t}))
            pairs.append((t, r[0]))
        ok["G gets kind chat, the date line, the earlier turns (user and replies) and the new turn"] = w.calls == want_inputs
        heard_g = {tuple(r["turn_ids"]): r for r in heard_of(g)}
        ptr = [tuple(r["turn_ids"]) in heard_g and len(r["turn_ids"]) == 1
               and w.calls[r["turn_ids"][0] - 1][3]["text"] == heard_g[tuple(r["turn_ids"])]["text"]
               and r["said_at"] == heard_g[tuple(r["turn_ids"])]["said_at"] for r in notes_of(g)]
        ok["W2 every note row points at the raw user turn it was written on"] = len(ptr) == 4 and all(ptr)
        want_rows = [(k + 1, note_row_text(n)) for k, ns in enumerate(got_notes) for n in (ns or [])]
        ok["note rows = G's notes (text + when), cites kept in memory"] = (
            [(r["turn_ids"][0], r["text"]) for r in notes_of(g)] == want_rows
            and any(x.endswith("Pi (yesterday)") for _, x in want_rows)
            and got_notes[1] == [{"text": "Note on: My dog is Pip.", "cites": [0, -2], "when": None}])
        ok["unparsed turn: no note, counted"] = (nl[3]["unparsed"] is True and nl[3]["notes"] == 0
                                                 and not [r for r in notes_of(g) if r["turn_ids"] == [4]]
                                                 and sum(r["unparsed"] for r in nl) == 1)
        queries = [r["text"] for r in notes_of(g)] + turns + ["dog", "vet", "Pip"]
        hits = [g.store.recall(q, k=10, mode="bm25") for q in queries]
        ok["W2 recall returns heard rows only"] = all(h["source"] == "heard" for hs in hits for h in hs)
        ok["W2 a note reaches its raw turn (via)"] = any(h.get("via") for hs in hits for h in hs)
        ok["notes log: one row per turn, counts only"] = (len(nl) == len(turns) and all(
            set(r) == {"turn", "notes", "unparsed", "write_ms", "n0_dropped"} for r in nl))
        ok["G kept as a bound method only"] = all(v is not w for v in vars(g).values())
        # restart from the same state dir: turn count and date survive; the session's earlier turns do not (as the
        # base reader's window after a restart)
        w2 = StubWriter()
        g2 = Agent02dG(dg, StubReader(), tg, StubSolver(), V4.MemoryStore(dg), w2)
        g2.turn("my dog is Fig")
        ok["restart: turn count, date and pointers continue"] = (
            g2.turn_no == len(turns) + 1 and w2.calls[0][:3] == ("chat", "May 3, 2023.", [])
            and notes_of(g2)[-1]["turn_ids"] == [len(turns) + 1]
            and len((dg / NOTES_LOG02D).read_text().splitlines()) == len(turns) + 1)
        # the W top-k fallback reads the store (notes are pointers there): the talker still sees raw user lines only
        g2.turn("word " * 3000)
        g2.turn("anything about my dog?")
        lastlog = json.loads((dg / B.LOG02D).read_text().splitlines()[-1])
        ok["W top-k: raw lines only reach the talker"] = (lastlog["w"] == "top_k" and not any(
            r["text"] in tg.seen[-1][0] for r in notes_of(g2)))
        # slot empty: exactly 0.2d (N0 rows back)
        dz = Path(d) / "z"
        dz.mkdir()
        tz = StubTalker()
        z = Agent02dG(dz, StubReader(), tz, StubSolver(), V4.MemoryStore(dz), None)
        for t in turns:
            z.turn(t)
        ok["slot empty: N0 fallback, rows as 0.2d's"] = ([r["text"] for r in notes_of(z)] == n0 and tz.seen == ta.seen
                                                         and not (dz / NOTES_LOG02D).exists())
        keep, env0 = NOTES02D, os.environ.get("E2E02D_NOTES")
        os.environ["E2E02D_NOTES"] = str(Path(d) / "elsewhere")
        ok["E2E02D_NOTES moves the slot"] = notes_dir() == str(Path(d) / "elsewhere")
        NOTES02D = ""
        ok["an empty slot stays empty (env cannot fill it)"] = notes_dir() == "" and writer_for_slot() is None
        NOTES02D = keep
        if env0 is None:
            os.environ.pop("E2E02D_NOTES", None)
        else:
            os.environ["E2E02D_NOTES"] = env0
        # fail closed before any model code runs
        fake = Path(d) / "fakeg"
        fake.mkdir()
        (fake / "model.safetensors").write_bytes(b"not G")

        def refused(fn, *args, want=""):
            try:
                fn(*args)
            except SystemExit as e:
                return want in str(e)
            return False
        ok["wrong G weights refused"] = refused(writer_for, str(fake), want="NOTES-SHA-MISMATCH")
        ok["missing G refused"] = refused(writer_for, str(Path(d) / "none"), want="no G model")
        ok["wrong adapter refused before merging"] = refused(merge, str(fake), str(fake), str(Path(d) / "m"),
                                                             want="ADAPTER-SHA-MISMATCH")
        ok["no model code loaded"] = "claude_rd378_write" not in sys.modules and "peft" not in sys.modules
    doc = __doc__ or ""
    ok["header carries ADDENDUM-K's wording"] = (all(" ".join(p.split()) in " ".join(doc.split()) for p in DISCLOSE02D)
                                                 and "trustworthy" not in doc.lower())
    B.RECALL_MODE02D = mode0
    for name, v in ok.items():
        print(("PASS " if v else "FAIL ") + name)
    print("E2E02DG-WIRING-SELFTEST " + ("PASS" if all(ok.values()) else "FAIL") + f" {sum(ok.values())}/{len(ok)}")
    if not all(ok.values()):
        raise SystemExit(1)


def main() -> None:
    import argparse
    if sys.argv[1:] == ["selftest"]:
        selftest()
        return
    ap = argparse.ArgumentParser(description="0.2d-G tools")
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("merge", help="rebuild G's merged model from the base and G's adapter")
    m.add_argument("--base", required=True)
    m.add_argument("--adapter", required=True)
    m.add_argument("--out", required=True)
    m.add_argument("--no-autocast", action="store_true", help="load the adapter without peft's fp32 upcast")
    a = ap.parse_args()
    if a.cmd == "merge":
        merge(a.base, a.adapter, a.out, autocast=not a.no_autocast)


if __name__ == "__main__":
    main()
