#!/usr/bin/env python3
"""0.2 candidate: gram-360 arm (scripts/claude_e2e360.py:build_360) + ep-382 episodic memory (month-end line,
2026-09-25). New file only; one change on top of the 336b G arm.

What ep-382 adds (design/v3/30-modes/382-memory-store-interface.md; store by the Benchmarks thread):
  heard382   every user turn is kept word for word in <state_dir>/memory382 (source "heard", speaker "user"),
             with said_at = the last date the chat stated ("DATE: ...", "today is ...") and logged_at = wall clock.
             It is written AFTER the turn is answered, so a question never retrieves itself.
  answer382  when the agent's final reply abstains or asks to rephrase and the turn is a question, recall() pulls
             the K382 most relevant heard (and note) rows and the base 1B answers from them alone. Every sample
             must pass 338's guards in strict mode with the retrieved rows as the known words: each capitalised
             word and number in the answer must appear in the question or the rows; G5 extends that to each
             sentence's first word (338's G3 skips it, so "Paris." would pass). A sample that abstains is
             not used. If none passes, the agent's own reply stays (fail closed).
Nothing here writes the notebook (checked every turn); the notebook stays the exact layer and is asked first.
Layer order: 330a_334 -> rec360 -> cre333d -> think299b -> chat338b -> answer382 -> vary330c -> gram360
             -> heard382 -> turnlog323.
The store module is claude_ep382_store_v2 unless EP382_STORE names another (fixed in the seal before a run).
Counters: loop.ep382_stats.

  python -B scripts/claude_twinb_wrap.py scripts/claude_e2e336_run.py --bank BANK \
      --arm claude_e2e382:build_382 --name E --model <reader dir> --gen-model <MiniCPM5-1B dir> --out OUT
"""
from __future__ import annotations

import importlib
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

K382 = 10
N382 = 4
STORE382 = os.environ.get("EP382_STORE", "claude_ep382_store_v2")
SYSTEM382 = ("You are a helpful and honest assistant. Below are things the user said in earlier conversations, "
             "each with the date it was said when known. Answer the user's question using only these. Answer "
             "briefly and directly. If they do not contain the answer, say you don't know. Never make anything up.")
DATE382 = re.compile(r"^\s*(?:date\s*:|today is|today's date is)\s*(?P<d>[^\n]{3,60}?)\s*(?:\n|$)", re.I)
QSENT = re.compile(r"[^.!?\n]*\?")
CAP382 = re.compile(r"\b([A-Z][a-z]+|\d+)\b")
STARTERS382 = {"the", "you", "your", "yours", "it", "its", "i", "yes", "no", "she", "he", "they", "we", "that",
               "this", "there", "in", "on", "at", "a", "an", "according", "based", "sure", "sorry", "maybe",
               "probably", "from", "about", "around", "after", "before", "during", "last", "next", "her", "his",
               "their", "my", "our", "when", "where", "what", "who", "which", "because", "so", "and", "but", "or",
               "they're", "it's", "that's", "one", "some", "both", "not", "never", "always", "then", "once"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _markers():
    import claude_e2e336_score as S
    return [m for m in S.ABSTAIN_MARKERS + S.CLARIFY_MARKERS]


def abstains(reply: str) -> bool:
    low = reply.lower()
    return any(m in low for m in _markers())


def query_of(text: str) -> str:
    """The last question sentence in the turn, else the whole turn."""
    qs = [q.strip() for q in QSENT.findall(text) if q.strip()]
    return qs[-1] if qs else text.strip()


def g5_unsupported(c: str, known: set[str]) -> bool:
    """338's G3 skips each sentence's first word, so a one-word answer ("Paris.") is never checked. Here every
    capitalised word and number must be in the question or the rows, or be a common sentence starter."""
    import claude_cre333_agent as C
    return any(t.lower() not in known and t not in C.ALLOW and t.lower() not in STARTERS382
               for t in CAP382.findall(c))


def _rows_block(rows: list[dict]) -> str:
    out = []
    for i, r in enumerate(rows, 1):
        when = f" [{r['said_at']}]" if r.get("said_at") else ""
        out.append(f"{i}.{when} {r['text']}")
    return "\n".join(out)


def install_answer382(loop, gen, store, k: int = K382, n: int = N382) -> None:
    import claude_chat338_agent as C38
    import claude_chat338b_agent as C38B
    inner = loop.turn
    loop.ep382_stats = {"turns": 0, "tried": 0, "no_rows": 0, "replaced": 0, "all_failed": 0, "abstained": 0,
                        "G1": 0, "G2": 0, "G3": 0, "G4": 0, "G5": 0}

    def answer382(text: str) -> list[str]:
        loop.ep382_stats["turns"] += 1
        ev0 = len(loop.nb.events)
        parts = inner(text)
        reply = " ".join(p for p in (parts or []) if p)
        if not (abstains(reply) and C38B.is_question(text) and len(loop.nb.events) == ev0
                and getattr(loop, "lis314_confirming", None) is None):
            return parts
        loop.ep382_stats["tried"] += 1
        rows = store.recall(query_of(text), k=k)
        if not rows:
            loop.ep382_stats["no_rows"] += 1
            return parts
        known = C38._words([text] + [r["text"] for r in rows] + [r.get("said_at") or "" for r in rows])
        msgs = [{"role": "system", "content": SYSTEM382 + "\n\n" + _rows_block(rows)},
                {"role": "user", "content": text}]
        for c in gen.sample_chat(msgs, n):
            c = C38.trim(c)
            g = C38.guard(c, text, known, strict=True) or ("G5" if g5_unsupported(c, known) else None)
            if g is not None:
                loop.ep382_stats[g] += 1
                continue
            if abstains(c):
                loop.ep382_stats["abstained"] += 1
                continue
            if len(loop.nb.events) != ev0:
                raise RuntimeError("382: answer phase wrote to the notebook")
            loop.ep382_stats["replaced"] += 1
            loop.ep382_last_rows = [r["id"] for r in rows]
            return [c]
        loop.ep382_stats["all_failed"] += 1
        return parts

    answer382.__name__ = "answer382"
    loop.turn = answer382


def install_heard382(loop, store) -> None:
    inner = loop.turn
    state = {"said_at": None, "turn": sum(1 for r in store.rows if r["source"] == "heard")}

    def heard382(text: str) -> list[str]:
        out = inner(text)
        m = DATE382.match(text)
        if m:
            state["said_at"] = m.group("d").strip()
        state["turn"] += 1
        store.remember(text, source="heard", speaker="user", turn_ids=[state["turn"]], said_at=state["said_at"],
                       logged_at=_now())
        return out

    heard382.__name__ = "heard382"
    loop.turn = heard382


def build_382(state_dir, args):
    import claude_chat338_agent as C38
    import claude_chat338b_agent as C38B
    import claude_cre333b_agent as C333B
    import claude_cre333d_agent as C333D
    import claude_e2e330_arms as A
    import claude_e2e330c as E330C
    import claude_gram360 as GR
    import claude_nb323_turnlog as NB
    import claude_think299b_agent as T299B
    import claude_vary330c as VARY
    ST = importlib.import_module(STORE382)
    if args.gen_model not in A._GEN:
        A._GEN[args.gen_model] = C333B.Gen333b(args.gen_model)
    one_b = A._GEN[args.gen_model]
    if args.gen_model not in E330C._G338B:
        E330C._G338B[args.gen_model] = C38.Gen338(share=one_b)
    store = ST.MemoryStore(state_dir)
    loop = A.build_330a_334(state_dir, args)
    GR.record_inner360(loop)
    C333D.install_creative333d(loop, E330C._G338B[args.gen_model])
    T299B.install_think299b(loop, one_b)
    C38B.install_chat338b(loop, E330C._G338B[args.gen_model])
    install_answer382(loop, E330C._G338B[args.gen_model], store)
    VARY.install_vary330c(loop)
    GR.install_gram360(loop)
    install_heard382(loop, store)
    NB.install_turnlog323(loop, str(Path(state_dir) / E330C.TURNLOG330C))
    loop.store382 = store
    loop.layers330c = ["330a_334", "rec360", "cre333d", "think299b", "chat338b", "answer382", "vary330c",
                       "gram360", "heard382", "turnlog323"]
    return loop
