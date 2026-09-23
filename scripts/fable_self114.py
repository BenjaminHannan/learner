#!/usr/bin/env python3
"""114 -- registered single-change follow-up to exp 105 (self-question router).

Exp 105 blind result: 43 correct / 51 decline / 6 WRONG on 100 questions.
Diagnosis (WRONGS.md): 5 of the 6 WRONGs were questions about someone else
("How many facts does Tom know?"), the future ("How many facts will you
know by the end of today?"), or policy/capability ("When you forget ... is
it gone-gone?", "which sources do you trust...", "Can you forget on
request?") -- answered with present-state content for a neighboring intent.
The 6th (Q003 "individuals" -> facts-count) is a synonym gap this change
does NOT address.

THE ONE CHANGE: a scope guard in front of the scored router. Everything
else -- normalisation, keyword tables, thresholds, margin, answer bodies,
decline sentence -- is inherited untouched from scripts/fable_self105.py
(imported read-only, never edited). The guard declines (with the identical
HONEST_DECLINE sentence) when the question's subject is not the agent, when
it is about the future or a hypothetical, or when it asks about a
policy/capability rather than a present count/list:

  FUTURE: token in {will, shall, tomorrow, next, future, predict, tonight,
    soon, eventually, gonna} or bigram {"go to", "about to"}.
  HYPOTHETICAL: token in {suppose, imagine, pretend, hypothetical} or the
    bigram "what if". (Bare "if"/"would" deliberately excluded: exp-100 Q14
    and exp-105 Q048 are CORRECT existing-intent questions containing them.)
  THIRD PARTY: token "tom" (the canonical other mind; post-normalisation,
    so "Tom"/"Tom's" all match); any standalone third-person pronoun
    {he, him, his, she, her, hers, they, them, their, theirs}; a
    capitalised non-first raw token outside the session allowlist together
    with a knowledge verb (covers "How many facts does Alice know?"); a
    raw 's-possessive on a non-allow capitalised name outside contraction
    bases (covers "Where does Alice's mother live?").
  POLICY/CAPABILITY: token "standard" (either number); token "sources"
    (plural only -- singular "source" is the live C27 web-row question);
    "trust" together with "source"; "forget" together with a capability
    marker {can, could, will, would, ever, gone, somewhere, keep, still,
    request, erase, erased, entirely, allow, allowed, able, usually,
    normally, often} (history forms "what have you forgotten" pass);
    (can|could|will|would) together with "fix"; standalone "gone".

Tuning data ONLY: exp 99's 40 canonicals + exp 100's 80 + the exp-105 panel
(now DEV). The exp-114 fresh panel is never opened before the freeze seal.

Run (Mac CPU, offline; only AFTER PASSMARKS sealed + ledger P114.*):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_self114.py --devcheck
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_self105 as S105  # noqa: E402 (read-only; wrapped, never edited)

HONEST_DECLINE = S105.HONEST_DECLINE

# ------------------------------------------------------------- guard tables
FUTURE_TOKS = {"will", "shall", "tomorrow", "next", "future", "predict",
               "tonight", "soon", "eventually", "gonna"}
FUTURE_BIGRAMS = {"go to", "about to"}
HYP_TOKS = {"suppose", "imagine", "pretend", "hypothetical"}
HYP_BIGRAMS = {"what if"}

THIRD_DENY = {"tom"}
THIRD_PRON = {"he", "him", "his", "she", "her", "hers", "they", "them",
              "their", "theirs"}
# Names/places taught in the frozen exp-99 session (entities + cities) plus
# the teacher and the net: questions about these stay routable.
ALLOW_NAMES = {"mira", "ana", "kai", "leo", "pia", "paris", "oslo",
               "porto", "rome", "internet", "ben"}
CONTRACTION_BASES = {"what", "that", "it", "there", "here", "where", "who",
                     "how", "when", "why", "this"}

POLICY_STANDARD = {"standard", "standards"}
FORGET_CAP = {"can", "could", "will", "would", "ever", "gone", "somewhere",
              "keep", "still", "request", "erase", "erased", "entirely",
              "allow", "allowed", "able", "usually", "normally", "often"}
FIX_MODAL = {"can", "could", "will", "would"}

_CAP_RE = re.compile(r"\b([A-Z][a-z]{2,}|[A-Z]{2,})\s+"
                      r"(know|knows|knew|think|thinks|thought|believe|"
                      r"believes|remember|remembers|learn|learns|learned|"
                      r"forget|forgets|forgot)\b")
_AUX_RE = re.compile(r"\b(does|do|did)\s+([A-Z][a-z]{2,}|[A-Z]{2,})\s+"
                     r"(know|think|believe|remember|learn|forget)\b")
_POSS_RE = re.compile(r"([A-Z][a-z]{2,})'s\b")


def scope_guard(question: str) -> tuple[bool, str]:
    """Return (decline, reason). Frozen at seal time. Reason "" if routable."""
    s, toks = S105.normalise(question)
    tset = set(toks)
    pairs = set(zip(toks, toks[1:]))

    if tset & FUTURE_TOKS:
        return True, f"future-token:{sorted(tset & FUTURE_TOKS)[0]}"
    hit = sorted(" ".join(p) for p in pairs if " ".join(p) in FUTURE_BIGRAMS)
    if hit:
        return True, f"future-bigram:{hit[0]}"
    if tset & HYP_TOKS:
        return True, f"hypothetical:{sorted(tset & HYP_TOKS)[0]}"
    hit = sorted(" ".join(p) for p in pairs if " ".join(p) in HYP_BIGRAMS)
    if hit:
        return True, f"hypothetical-bigram:{hit[0]}"

    if tset & THIRD_DENY:
        return True, "third-party-name:tom"
    if tset & THIRD_PRON:
        return True, f"third-party-pronoun:{sorted(tset & THIRD_PRON)[0]}"
    for m in _POSS_RE.finditer(str(question)):
        name = m.group(1).lower()
        if name not in ALLOW_NAMES and name not in CONTRACTION_BASES:
            return True, f"third-party-possessive:{m.group(1)}"
    raw = str(question)
    m = _CAP_RE.search(raw) or _AUX_RE.search(raw)
    if m:
        name = m.group(1) if m.re is _CAP_RE else m.group(2)
        if name.lower() not in ALLOW_NAMES:
            return True, f"third-party-knower:{name}"

    if tset & POLICY_STANDARD:
        return True, "policy:standards"
    if "sources" in tset:
        return True, "policy:sources"
    if "trust" in tset and "source" in tset:
        return True, "policy:trust-sources"
    if "forget" in tset and (tset & FORGET_CAP):
        return True, (f"policy:forget-capability:"
                       f"{sorted(tset & FORGET_CAP)[0]}")
    if (tset & FIX_MODAL) and "fix" in tset:
        return True, "policy:fix-capability"
    if "gone" in tset:
        return True, "policy:gone"
    return False, ""


def route114(question: str) -> tuple[str, dict]:
    """Scope guard in front of the frozen 105 scored router."""
    decline, reason = scope_guard(question)
    if decline:
        _, toks = S105.normalise(question)
        return "DECLINE", {"guard": reason, "tokens": toks}
    intent, info = S105.route(question)
    info = dict(info)
    info["guard"] = "pass"
    return intent, info


class Self114Agent(S105.Self105Agent):
    """Exp-105 agent with the scope guard. Answer bodies inherited intact."""

    def answer_self(self, question: str) -> str:
        decline, _ = scope_guard(question)
        if decline:
            return HONEST_DECLINE
        return super().answer_self(question)


# ------------------------------------------------------------- dev checking
def devcheck() -> int:
    """Dev ONLY (exp99-40 + exp100-80 + exp105-panel-100). Never the 114 panel."""
    import shutil  # noqa: E402

    import fable_self100_runner as R100  # noqa: E402 (read-only scoring)

    from pathlib import Path as _P  # noqa: E402

    repo = _P(__file__).resolve().parent.parent
    state = SCRIPTS / "scratchpad" / "fable_self114" / "devcheck_state"
    if state.exists():
        shutil.rmtree(state)
    agent = Self114Agent(str(state))
    agent.run_session()
    s = agent.snapshot()

    checked = agent.check_all()
    s1, s2 = checked["correct"], len(checked["hallucinations"])
    s3 = sum(1 for p in checked["per_question"]
             if p["id"].startswith("D") and p["pass"])
    print(f"exp99: S1 {s1}/40 S2 hallucinations={s2} S3 {s3}/10", flush=True)

    gate = {"n_taught": 19, "n_entities": 6, "n_quarantine": 1,
            "n_superseded": 2, "n_forgotten": 1, "sleeps": 0, "turns": 26}
    gate_ok = all(s[k] == v for k, v in gate.items())
    wrong100, c100 = 0, 0
    for qid, intent, text in R100.BLIND:
        ans = agent.answer_self(text)
        verdict, note = R100.score(agent, qid, intent, ans, s)
        wrong100 += verdict == "WRONG"
        c100 += (qid <= "Q60" and verdict == "CORRECT")
        d, reason = scope_guard(text)
        flag = ""
        if d:
            _, old = S105.route(text)
            flag = f" [guard:{reason} old-route:{old}]"
        print(f"{qid}({intent}): {verdict} ({note}){flag}", flush=True)
    print(f"exp100-80: WRONG={wrong100} rephrasing-CORRECT={c100}/60 "
          f"gate={gate_ok}", flush=True)

    import json as _json  # noqa: E402

    panel = _json.loads((repo / "artifacts" / "fable-self105panel-20260921"
                         / "panel.json").read_text(encoding="utf-8"))
    wrong105, c105, decl105 = [], 0, 0
    for q in panel["questions"]:
        qid, group, intent, text = (q["id"], q["group"], q["intent"],
                                   q["question"])
        cls = intent if group == "existing" else (
            "NEW" if group == "new" else "D0")
        ans = agent.answer_self(text)
        verdict, note = R100.score(agent, qid, cls, ans, s)
        c105 += (group == "existing" and verdict == "CORRECT")
        decl105 += verdict == "DECLINE"
        d, reason = scope_guard(text)
        if verdict == "WRONG":
            wrong105.append((qid, group, intent, text, ans))
        print(f"105 {qid}({group}/{intent}): {verdict} guard={d}:{reason} "
              f"({note})", flush=True)
    print(f"105-panel rescore (dev, unregistered): WRONG={len(wrong105)} "
          f"existing-CORRECT={c105}/70 DECLINE={decl105}/100", flush=True)
    for qid, group, intent, text, ans in wrong105:
        print(f"  STILL-WRONG {qid}({group}/{intent}) Q={text} A={ans}",
              flush=True)

    ok = gate_ok and s1 == 40 and s2 == 0 and s3 == 10 and wrong100 == 0
    print("DEVCHECK " + ("PASS" if ok else "FAIL"), flush=True)
    return 0 if ok else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 114 scope-guarded router")
    parser.add_argument("--devcheck", action="store_true")
    parser.add_argument("--route", default=None,
                        help="print the routed intent for one question")
    args = parser.parse_args(argv)
    if args.route is not None:
        intent, info = route114(args.route)
        print(f"{intent} {info}")
        return 0
    if args.devcheck:
        return devcheck()
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
