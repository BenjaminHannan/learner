#!/usr/bin/env python3
"""bm-398c: the 1B translates, a calendar computes (benchmarks thread, 2026-09-26). Plan and marks:
artifacts/claude-bm398c-20260926/PLAN.md. Development measurement on LoCoMo ("after using LoCoMo for development");
nothing is trained. No question, answer, evidence or reply text is printed: counts only.

bm-398d's 58 date questions (category 2 of its 297). Given only the right lines, the plain 1B and Qwen3.5-2B (whole
chat) were each right on 10. In Ben's design the reader only translates and the reasoner uses tools such as a clock.
Here the 1B does not answer: it copies two things from the chat, the date written above the message that says when
it happened and the time words in that message. A calendar tool turns them into a date. Sending date questions to the
calendar by their category is disclosed test scaffolding: the learned router that should make that choice is owed.

Arms (the blind check judges all three together):
  G   bm-398d's replies: the 1B answers from the right lines (reused, sha256 pinned; CPU fp32).
  GC  the same right lines, laid out the same way; the 1B translates, the calendar answers.
  Q2  Qwen3.5-2B from the whole chat (bm-390 run2's replies). Report only: it reads the whole chat, not the lines.
The whole-chat arms (1B with and without the calendar) take about 3 minutes a prompt on this CPU, so they are left
to a later GPU run if GC passes.

  run      python -B scripts/claude_bm398c_clock.py run --data DATA --g G.jsonl --model DIR --out OUT [--limit N]
  prep     python -B scripts/claude_bm398c_clock.py prep --data DATA --g G.jsonl --runs OUT --q2 Q2DIR --work WORK
  jscore   python -B scripts/claude_bm398c_clock.py jscore --data DATA --work WORK
  score    python -B scripts/claude_bm398c_clock.py score --data DATA --g G.jsonl --runs OUT --q2 Q2DIR --out score.json
  selftest
The calendar's phrase list was written from ordinary English before any LoCoMo evidence line was read for this test.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import random
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_bm390 as B  # noqa: E402
import claude_bm398d_evidence as D  # noqa: E402
from claude_bm398n_notes import mcnemar_p  # noqa: E402

G_SHA = "593466f6edaaf828b51aed24b68933c62cac17b65fcb78c3db09bc90cf847a9f"
ARMS = ["G", "GC", "Q2"]
N_ITEMS, TRANSLATE_TOKENS = 58, 40
JUDGE_SEED, BATCH, X1_N = 3996, 58, 20
C1_MIN_GAIN, C1_MAX_P, C2_MAX_EXTRA_D = 8, 0.05, 3
TRANSLATE = ("\nDo not answer the question below. Instead, copy two things from the conversation above, on two "
             "lines:\nDATE: the date written above the message that says when it happened\nWHEN: the words in that "
             "message that say when it happened, or \"same day\" if it has none\n\nQuestion: {}\n")
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december"]
DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
NUM = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
       "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "a couple of": 2, "couple of": 2, "couple": 2}
VAGUE = ("a few", "few", "several", "some", "a couple")


def _jsonl(p) -> list[dict]:
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def fmt(d: dt.date) -> str:
    return f"{d.day} {MONTHS[d.month - 1].capitalize()} {d.year}"


def month_shift(d: dt.date, k: int) -> tuple[int, int]:
    m = d.year * 12 + (d.month - 1) + k
    return m // 12, m % 12 + 1


def parse_anchor(text: str) -> dt.date | None:
    m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\.?,?\s+(\d{4})", text or "")
    if not m:
        return None
    name = m.group(2).lower()
    mon = next((i + 1 for i, x in enumerate(MONTHS) if x.startswith(name[:3]) and len(name) >= 3), None)
    try:
        return dt.date(int(m.group(3)), mon, int(m.group(1))) if mon else None
    except ValueError:
        return None


def _count(word: str) -> int | None:
    w = word.strip()
    if w.isdigit():
        return int(w)
    return NUM.get(w)


def calendar(anchor: dt.date, when: str) -> tuple[str, bool]:
    """(answer, read). The clock tool: a time phrase said on the anchor day -> a date. read is False when the phrase
    is not one it knows; the answer then keeps the phrase with its anchor."""
    w = " " + re.sub(r"[^a-z0-9 ]", " ", (when or "").lower()) + " "
    w = re.sub(r"\s+", " ", w)
    nums = r"(\d+|a|an|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|a couple of|couple of)"
    if " day before yesterday " in w:
        return fmt(anchor - dt.timedelta(days=2)), True
    if " yesterday " in w or " last night " in w:
        return fmt(anchor - dt.timedelta(days=1)), True
    if " tomorrow " in w:
        return fmt(anchor + dt.timedelta(days=1)), True
    for v in VAGUE:
        for unit, word in (("day", "days"), ("week", "weeks"), ("month", "months"), ("year", "years")):
            if f" {v} {word} ago " in w or f" {v} {word} back " in w:
                return f"{v} {word} before {fmt(anchor)}", True
    m = re.search(rf" {nums} (day|days|week|weeks|month|months|year|years) (ago|back|before) ", w)
    if m:
        n = _count(m.group(1))
        unit = m.group(2).rstrip("s")
        if n is not None:
            if unit == "day":
                return fmt(anchor - dt.timedelta(days=n)), True
            if unit == "week":
                return ("the week before " if n == 1 else f"{n} weeks before ") + fmt(anchor), True
            if unit == "month":
                y, mo = month_shift(anchor, -n)
                return f"{MONTHS[mo - 1].capitalize()} {y}", True
            return str(anchor.year - n), True
    if " last weekend " in w or " past weekend " in w or " over the weekend " in w or " this weekend " in w:
        return f"the weekend before {fmt(anchor)}", True
    for i, day in enumerate(DAYS):
        if f" next {day} " in w:
            ahead = (i - anchor.weekday()) % 7 or 7
            return fmt(anchor + dt.timedelta(days=ahead)), True
        if f" {day} " in w or f" {day}s " in w:
            back = (anchor.weekday() - i) % 7 or 7
            return fmt(anchor - dt.timedelta(days=back)), True
    if " last week " in w or " past week " in w or " the other week " in w:
        return f"the week before {fmt(anchor)}", True
    if " next week " in w:
        return f"the week after {fmt(anchor)}", True
    if " this week " in w:
        return f"the week of {fmt(anchor)}", True
    if " last month " in w or " past month " in w:
        y, mo = month_shift(anchor, -1)
        return f"{MONTHS[mo - 1].capitalize()} {y}", True
    if " next month " in w:
        y, mo = month_shift(anchor, 1)
        return f"{MONTHS[mo - 1].capitalize()} {y}", True
    if " this month " in w:
        return f"{MONTHS[anchor.month - 1].capitalize()} {anchor.year}", True
    if " last year " in w or " past year " in w:
        return str(anchor.year - 1), True
    if " next year " in w:
        return str(anchor.year + 1), True
    if " this year " in w:
        return str(anchor.year), True
    yr = re.search(r" (19\d\d|20\d\d) ", w)
    mon = next((i + 1 for i, x in enumerate(MONTHS) if f" {x} " in w), None)
    if yr and mon:
        return f"{MONTHS[mon - 1].capitalize()} {yr.group(1)}", True
    if yr:
        return yr.group(1), True
    if mon:
        y = anchor.year if mon <= anchor.month else anchor.year - 1
        return f"{MONTHS[mon - 1].capitalize()} {y}", True
    for x in (" same day ", " today ", " this morning ", " this afternoon ", " this evening ", " tonight ",
              " earlier today ", " just now ", " right now ", " now "):
        if x in w:
            return fmt(anchor), True
    phrase = (when or "").strip().strip('"').strip()
    return (f"{phrase}, said on {fmt(anchor)}" if phrase else fmt(anchor)), False


def translation(reply: str) -> tuple[str, str]:
    date, when = "", ""
    for line in reply.splitlines():
        s = line.strip().strip("*").strip()
        if s.upper().startswith("DATE:") and not date:
            date = s[5:].strip()
        elif s.upper().startswith("WHEN:") and not when:
            when = s[5:].strip().strip('"').strip()
    return date, when


def clock_reply(reply: str) -> tuple[str, dict]:
    date, when = translation(reply)
    anchor = parse_anchor(date)
    if anchor is None:
        return "I don't know", {"date_read": False, "when_read": False}
    ans, read = calendar(anchor, when)
    return ans, {"date_read": True, "when_read": read}


def items58(data: Path) -> tuple[list[str], dict]:
    kept, info = D.sample(data)
    qs = [q for q in kept if info[q][2]["category"] == 2]
    if len(qs) != N_ITEMS:
        raise SystemExit("bm398c: expected 58 date questions in bm-398d's sample")
    return qs, info


def run(a) -> int:
    qs, info = items58(Path(a.data))
    if hashlib.sha256(Path(a.g).read_bytes()).hexdigest() != G_SHA:
        raise SystemExit("bm398c: G replies are not bm-398d's")
    g = {r["qid"]: r for r in _jsonl(a.g)}
    if a.limit:
        qs = qs[: a.limit]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    fh = {"GC": (out / "locomo_GC.jsonl").open("w", encoding="utf-8")}
    t_all = time.time()
    for n, q in enumerate(qs):
        conv, i, qa, gold = info[q]
        items = D.items_of(conv)
        lines = D.context(conv, items, gold)
        if sorted(set(g[q]["turns"])) != sorted(set(gold)):
            raise SystemExit("bm398c: G's lines are not the evidence lines")
        jobs = [("GC", lines + "\n\n" + TRANSLATE.format(qa["question"]), TRANSLATE_TOKENS, True)]
        for arm, user, cap, clock in jobs:
            t0 = time.time()
            raw, ntok = B.generate(a.model, B.LOCOMO_SYSTEM, user, cap)
            row = {"qid": q, "category": 2, "reply": raw, "ms": round((time.time() - t0) * 1000, 1),
                   "prompt_tokens": ntok}
            if clock:
                row["translation"] = raw
                row["reply"], row["tool"] = clock_reply(raw)
            fh[arm].write(json.dumps(row, ensure_ascii=False) + "\n")
            fh[arm].flush()
        if (n + 1) % 10 == 0:
            print(f"[bm398c] {n + 1}/{len(qs)} seconds={time.time() - t_all:.0f}", flush=True)
    for arm in ("GC",):
        fh[arm].close()
        f = out / f"locomo_{arm}.jsonl"
        rows = _jsonl(f)
        tool = Counter((r["tool"]["date_read"], r["tool"]["when_read"]) for r in rows if "tool" in r)
        print(f"wrote locomo_{arm}.jsonl rows={len(rows)} sha256={hashlib.sha256(f.read_bytes()).hexdigest()} "
              f"tool={dict((f'date{int(k[0])}_when{int(k[1])}', v) for k, v in sorted(tool.items()))}", flush=True)
    print(json.dumps({"questions": len(qs), "seconds": round(time.time() - t_all)}), flush=True)
    return 0


def replies(a, qs: list[str]) -> dict:
    if hashlib.sha256(Path(a.g).read_bytes()).hexdigest() != G_SHA:
        raise SystemExit("bm398c: G replies are not bm-398d's")
    rep = {"G": {r["qid"]: r["reply"] for r in _jsonl(a.g)}}
    rep["GC"] = {r["qid"]: r["reply"] for r in _jsonl(Path(a.runs) / "locomo_GC.jsonl")}
    rep["Q2"] = D._replies(Path(a.q2))
    miss = {k: sum(q not in v for q in qs) for k, v in rep.items()}
    if any(miss.values()):
        raise SystemExit(f"bm398c: missing replies {miss}")
    return rep


def score(a) -> int:
    import claude_bm390_score as SC
    qs, _info = items58(Path(a.data))
    rep = replies(a, qs)
    res = {}
    for arm in ARMS:
        s = SC.score_locomo(Path(a.data), [{"qid": q, "reply": rep[arm][q]} for q in qs])["summary"]
        res[arm] = {k: s[k] for k in ("cat2_f1", "cat1to4_abstain", "cat1to4_confident_wrong", "cat1to4_half_right")}
    for arm in ("GC",):
        tool = Counter()
        for r in _jsonl(Path(a.runs) / f"locomo_{arm}.jsonl"):
            tool["date_read"] += r["tool"]["date_read"]
            tool["when_read"] += r["tool"]["when_read"]
        res[arm]["tool"] = dict(tool)
    Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res))
    return 0


def latin(qs: list[str], rng: random.Random) -> dict[str, list[tuple[str, str]]]:
    k = len(ARMS)
    groups = {f"L{g}": [(q, ARMS[(n + g) % k]) for n, q in enumerate(qs)] for g in range(k)}
    groups["X1"] = [(q, ARMS[n % k]) for n, q in enumerate(qs[:X1_N])]
    for g in groups:
        rng.shuffle(groups[g])
    return groups


def prep(a) -> int:
    import claude_bm397_judge as J
    qs, info = items58(Path(a.data))
    rep = replies(a, qs)
    work = Path(a.work)
    (work / "batches").mkdir(parents=True, exist_ok=True)
    (work / "labels").mkdir(parents=True, exist_ok=True)
    key, batches, counter = {}, [], 0
    for g, pairs in latin(qs, random.Random(JUDGE_SEED)).items():
        its = []
        for q, arm in pairs:
            conv, _i, qa, gold = info[q]
            items = D.items_of(conv)
            counter += 1
            iid = f"c{counter:04d}"
            key[iid] = {"qid": q, "arm": arm}
            ev = "\n".join(f"[{items[p][1]}] " + B.turn_text(items[p][2]) for p in gold)
            its.append({"item": iid, "question": qa["question"], "gold_answer": J._gold(qa), "evidence": ev,
                        "reply": rep[arm][q]})
        (work / "batches" / f"{g}01.jsonl").write_text(
            "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in its), encoding="utf-8")
        batches.append(f"{g}01")
    (work / "key.json").write_text(json.dumps({"qids": qs, "items": key}), encoding="utf-8")
    print(json.dumps({"questions": len(qs), "items": len(key), "batches": batches}))
    return 0


def verdict(by: dict, qs: list[str]) -> dict:
    full = [q for q in qs if set(by[q]) == set(ARMS)]
    res = {"questions": len(qs), "fully_judged": len(full)}
    for arm in ARMS:
        c = Counter(by[q][arm] for q in full)
        res[arm] = {"A": c["A"], "D": c["D"], "E": c["E"], "labels": dict(sorted(c.items()))}

    def pair(x: str, y: str) -> dict:
        g = sum(by[q][x] == "A" and by[q][y] != "A" for q in full)
        lo = sum(by[q][x] != "A" and by[q][y] == "A" for q in full)
        return {"A": res[x]["A"] - res[y]["A"], "gained": g, "lost": lo, "mcnemar_p": round(mcnemar_p(g, lo), 5)}

    res["GC-G"] = pair("GC", "G")
    res["GC-Q2_report_only"] = pair("GC", "Q2")
    d = res["GC-G"]
    res["C1"] = d["A"] >= C1_MIN_GAIN and d["gained"] > d["lost"] and d["mcnemar_p"] < C1_MAX_P
    res["C2"] = res["GC"]["D"] <= res["G"]["D"] + C2_MAX_EXTRA_D
    res["proved_wrong"] = d["A"] <= 0
    res["verdict"] = "PASS" if res["C1"] and res["C2"] else "FAIL"
    res["table_G_to_GC"] = dict(sorted(Counter(f"{by[q]['G']}->{by[q]['GC']}" for q in full).items()))
    return res


def jscore(a) -> int:
    work = Path(a.work)
    k = json.loads((work / "key.json").read_text(encoding="utf-8"))
    main, rel = {}, {}
    for f in sorted((work / "labels").glob("*.jsonl")):
        sink = rel if f.stem.startswith("X") else main
        for r in _jsonl(f):
            lab = str(r["label"]).strip().upper()[:1]
            if not lab or lab not in "ABCDE":
                raise SystemExit(f"bm398c jscore: bad label in {f.name}")
            sink[r["item"]] = lab
    by = defaultdict(dict)
    for iid, lab in main.items():
        m = k["items"][iid]
        by[m["qid"]][m["arm"]] = lab
    res = verdict(by, k["qids"])
    mk = {(k["items"][i]["qid"], k["items"][i]["arm"]): lab for i, lab in main.items()}
    pr = [(mk.get((k["items"][i]["qid"], k["items"][i]["arm"])), lab) for i, lab in rel.items()]
    pr = [p for p in pr if p[0] is not None]
    res["relabel_agree"] = f"{sum(x == y for x, y in pr)}/{len(pr)}"
    print(json.dumps(res))
    return 0


def selftest(a) -> int:
    ok = {}
    mon = dt.date(2023, 5, 8)  # a Monday
    cases = {
        "yesterday": "7 May 2023", "the day before yesterday": "6 May 2023", "last night": "7 May 2023",
        "last Saturday": "6 May 2023", "on Friday": "5 May 2023", "last Monday": "1 May 2023",
        "next Tuesday": "9 May 2023", "3 days ago": "5 May 2023", "two days ago": "6 May 2023",
        "a few days ago": "a few days before 8 May 2023", "last week": "the week before 8 May 2023",
        "two weeks ago": "2 weeks before 8 May 2023", "a week ago": "the week before 8 May 2023",
        "last weekend": "the weekend before 8 May 2023", "last month": "April 2023",
        "three months ago": "February 2023", "next month": "June 2023", "last year": "2022",
        "two years ago": "2021", "in 2021": "2021", "in March 2022": "March 2022", "in December": "December 2022",
        "same day": "8 May 2023", "this morning": "8 May 2023", "tomorrow": "9 May 2023",
    }
    bad = [k for k, v in cases.items() if calendar(mon, k) != (v, True)]
    ok[f"calendar reads {len(cases)} phrases"] = not bad
    ok["unknown phrase keeps its anchor"] = calendar(mon, "back in the day") == ("back in the day, said on 8 May 2023",
                                                                                  False)
    ok["anchor from a session date"] = (parse_anchor("1:56 pm on 8 May, 2023") == mon
                                        and parse_anchor("8 May 2023") == mon and parse_anchor("May 8") is None)
    ok["translation lines"] = translation("DATE: 1:56 pm on 8 May, 2023\nWHEN: \"last week\"") == (
        "1:56 pm on 8 May, 2023", "last week")
    ok["clock reply"] = clock_reply("DATE: 8 May, 2023\nWHEN: yesterday")[0] == "7 May 2023"
    ok["no date: don't know"] = clock_reply("WHEN: yesterday") == ("I don't know",
                                                                   {"date_read": False, "when_read": False})
    qs = [f"conv-{c}#{i}" for c in (1, 2) for i in range(29)]
    groups = latin(qs, random.Random(JUDGE_SEED))
    ok["each group holds every question once"] = all(sorted(q for q, _ in groups[f"L{g}"]) == sorted(qs)
                                                     for g in range(3))
    ok["each question's arms in different groups"] = all(
        len({dict(groups[f"L{g}"])[q] for g in range(3)}) == 3 for q in qs)
    by = {q: {"G": "D", "GC": "A" if n % 3 else "D", "Q2": "A"} for n, q in enumerate(qs)}
    v = verdict(by, qs)
    ok["a clear gain passes"] = v["verdict"] == "PASS" and v["GC-G"]["A"] == 38
    by2 = {q: {**by[q], "G": "A", "GC": "D"} for q in qs}
    v2 = verdict(by2, qs)
    ok["a loss fails, proved wrong, and C2 catches the extra wrong"] = (v2["verdict"] == "FAIL" and v2["proved_wrong"]
                                                                       and not v2["C2"])
    for k, x in ok.items():
        print(("PASS " if x else "FAIL ") + k + ("" if x or k != f"calendar reads {len(cases)} phrases" else f" {bad}"))
    print("BM398C-SELFTEST " + ("PASS" if all(ok.values()) else "FAIL") + f" {sum(ok.values())}/{len(ok)}")
    return 0 if all(ok.values()) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "prep", "jscore", "score", "selftest"])
    for x in ("data", "g", "model", "out", "runs", "q2", "work"):
        ap.add_argument("--" + x, default="")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    return {"run": run, "prep": prep, "jscore": jscore, "score": score, "selftest": selftest}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
