"""Step 6: tag the day's diary. REGRET = assistant committed (ACT) without asking and Ben corrected within 3 turns.
ANNOYANCE = assistant asked something whose answer was already in the request / diary, or Ben said 'obviously' / 'just do it'.
Rule pass (regexes + BM25 'answer already known' check) plus an optional Haiku Batches pass (one request per day). Never reads the oracle files.
  python -m sleep2.askonce.tagger DIARY_DIR OUT_JSONL [--haiku] [--days 1 2 3]
"""
import json
import re
import sys
from pathlib import Path

from .config import HAIKU, jl_read, jl_write, norm
from .slot_memory import SlotMemory

CORR_RE = re.compile(r"\b(no|nope|wrong|not that|that's not|thats not|actually|i meant|i said|should be|should have been|isn't|is not|incorrect|mistake|instead)\b", re.I)
ANNOY_RE = re.compile(r"\b(obviously|just do it|already told|i told you|already said|right there|in my message|in my request|already in)\b", re.I)
VALUE_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+|/[\w./-]{3,}|\bev-[a-z0-9]+\b", re.I)


def groups(rows):
    g = {}
    for r in rows:
        g.setdefault(r["req_id"], []).append(r)
    return {k: sorted(v, key=lambda x: x["turn"]) for k, v in g.items() if not k.startswith("fact-")}


def build_prior(prior_rows):
    """Index of earlier-day user answers/corrections + the set of refs Ben already answered or corrected."""
    mem, refs = SlotMemory(), set()
    for gid, g in groups(prior_rows).items():
        req = g[0]
        said = [x for x in g[1:] if x["role"] == "user" and x["text"]]
        for x in said:
            mem.add(req["day"], "u", "", x["text"])
        if said:
            refs.update(norm(r) for r in req["meta"].get("lookup_refs", []))
    return mem, refs


def rule_tags(day_rows, prior_rows):
    mem, known_refs = build_prior(prior_rows)
    out = []
    for rid, g in groups(day_rows).items():
        req, move1 = g[0], next((x for x in g if x["role"] == "assistant"), None)
        if move1 is None:
            continue
        refs = req["meta"].get("lookup_refs", [])
        slot_ref = refs[0] if refs else None
        m = move1["meta"].get("move")
        users_after = [x for x in g if x["role"] == "user" and x["turn"] > move1["turn"] and x["text"]]
        if m == "ACT":
            for x in users_after:
                if x["turn"] <= move1["turn"] + 3 and CORR_RE.search(x["text"]):
                    out.append({"day": req["day"], "req_id": rid, "type": "regret", "slot_ref": slot_ref, "evidence": x["text"][:120], "source": "rule"})
                    break
        elif m == "ASK" and users_after:
            ans = users_after[0]["text"]
            why = None
            if ANNOY_RE.search(ans):
                why = "annoyed reply"
            elif slot_ref and norm(slot_ref) in known_refs:
                why = "slot already answered on an earlier day"
            else:
                vals = VALUE_RE.findall(ans)
                if vals and mem.hit_with_values(vals, req["day"]):
                    why = "answer string already in diary"
            if why:
                out.append({"day": req["day"], "req_id": rid, "type": "annoyance", "slot_ref": slot_ref, "evidence": why, "source": "rule"})
    return out


def transcript(g):
    lines = []
    for x in g:
        if x["meta"].get("kind") in ("tool_result", "ack"):
            continue
        who = "BEN" if x["role"] == "user" else "ASSISTANT"
        lines.append(f"{who}: {x['text']}")
    return "\n".join(lines)


HAIKU_PROMPT = ("You label turns of a personal-assistant log. For each numbered exchange decide ONE label:\n"
                "regret = the assistant ran a tool (ACT) without asking and Ben then corrected it;\n"
                "annoyance = the assistant ASKed something Ben had already told it (earlier in the exchange text, in his request, or he sounds annoyed: obviously / just do it);\n"
                "none = anything else.\nReturn ONLY JSON {\"labels\": {\"<id>\": \"regret|annoyance|none\", ...}}.\n\n")


def haiku_tags(day_rows_by_day, label="tagger"):
    from .batches import parse_json, req, run_batch
    reqs, plan = [], {}
    for day, rows in day_rows_by_day.items():
        gs = groups(rows)
        ids = list(gs)
        for ci in range(0, len(ids), 40):
            chunk = ids[ci:ci + 40]
            body = "\n\n".join(f"### {i}\n{transcript(gs[i])}" for i in chunk)
            cid = f"{label}-d{day}-c{ci // 40}"
            reqs.append(req(cid, HAIKU, HAIKU_PROMPT + body, 4000))
            plan[cid] = (day, chunk, gs)
    out, _ = run_batch(reqs, label)
    tags = []
    for cid, (day, chunk, gs) in plan.items():
        try:
            lab = parse_json(out[cid])["labels"]
        except Exception as e:
            print("haiku tagger parse failed", cid, e, file=sys.stderr)
            continue
        for rid in chunk:
            l = lab.get(rid)
            if l in ("regret", "annoyance"):
                refs = gs[rid][0]["meta"].get("lookup_refs", [])
                tags.append({"day": day, "req_id": rid, "type": l, "slot_ref": refs[0] if refs else None, "evidence": "haiku", "source": "haiku"})
    return tags


def merge(rule, haiku):
    seen, out = set(), []
    for t in rule + haiku:
        k = (t["req_id"], t["type"])
        if k not in seen:
            seen.add(k)
            out.append(t)
    return out


def tag_all(diary_dir, days=None, use_haiku=False):
    diary_dir = Path(diary_dir)
    files = sorted(diary_dir.glob("day*.jsonl"), key=lambda p: int(re.findall(r"\d+", p.name)[0]))
    by_day = {int(re.findall(r"\d+", p.name)[0]): jl_read(p) for p in files}
    tags = []
    for d in sorted(by_day):
        if days and d not in days:
            continue
        prior = [r for dd in sorted(by_day) if dd < d for r in by_day[dd]]
        tags += rule_tags(by_day[d], prior)
    if use_haiku:
        tags = merge(tags, haiku_tags({d: r for d, r in by_day.items() if not days or d in days}))
    return tags


if __name__ == "__main__":
    a = sys.argv[1:]
    use_h = "--haiku" in a
    a = [x for x in a if x != "--haiku"]
    tags = tag_all(a[0], use_haiku=use_h)
    jl_write(a[1], tags)
    print(json.dumps({"n": len(tags), "regret": sum(t["type"] == "regret" for t in tags), "annoyance": sum(t["type"] == "annoyance" for t in tags)}))
