"""Full leakage scan (prereg: 'grep over all day-1..5 text'). Collects EVERY piece of text a model sees or is trained on in days 1-5 and looks for the
words of the held-out (new-ambiguity) slots: key token, reference phrase, distinctive reference words, candidate values and candidate names.
Sources: SYSTEM prompts, rendered day 1-5 prompts incl. the [Lookup] block, request text, gold actions, the answers / corrections / questions /
paraphrases of train + silent slots (they become memory lines and night-file targets), background facts and their paraphrases, anchor prompts.
  python -m sleep2.askonce.leakscan            # scans the frozen data, prints hits, exit 1 if any are not in ACCEPTED"""
import re
import sys

from .config import ANNOY_PREFIX, CORR_PREFIX, DATA, DAYS_TRAIN, FULLSPEC_REPLY, GENERAL_SYSTEM, N_ANCHOR, SYSTEM, jl_read, jload, norm

from .world import Persona, act_text, first_messages

GENERIC = {"emails", "email", "messages", "message", "meeting", "meetings", "appointments", "sessions", "notes", "that", "this", "with", "from", "have", "your", "the"}
FACT_SYSTEM = ["You are Ben's assistant. You keep notes about Ben.", "Write down one fact you know about Ben."]
# Hits we knowingly keep after the fixes (listed in DEVIATIONS.md). Format: (new_slot_id, needle). Empty = zero tolerated.
ACCEPTED = set()


def label_name(label):
    return label.split(" (")[0].strip()


def needles(P, sid):
    s = P.slot(sid)
    n = {s["key_token"], s["ref"]}
    n |= {w for w in re.findall(r"[a-z0-9]+", norm(s["ref"])) if len(w) >= 7 and w not in GENERIC}  # same cut-off as persona._avoid
    if s["kind"] in ("contact", "meeting", "file"):
        n |= {c["value"] for c in s["candidates"]}
        n |= {label_name(c["label"]) for c in s["candidates"] if len(label_name(c["label"])) > 3}
    return {x for x in n if x}


def visible_text(P, phr, requests):
    """-> [(source, text)] over everything model-visible in days 1-5 (and night-file targets, which are built from the same pieces)."""
    out = [("system", SYSTEM), ("system", GENERAL_SYSTEM)] + [("fact-prompt", t) for t in FACT_SYSTEM]
    out += [("prefix", t) for t in list(ANNOY_PREFIX) + list(CORR_PREFIX) + list(FULLSPEC_REPLY)]
    for r in requests:
        if r["day"] > DAYS_TRAIN:
            continue
        m = first_messages(P, r, [])
        out += [(f"prompt:{r['req_id']}", m[1]["content"]), (f"gold:{r['req_id']}", act_text(r["gold"]))]
    for sid, s in P.slots.items():
        if s["split"] == "new":
            continue  # never shown in days 1-5 (checked by the scan itself via the request prompts above)
        for k in ("answers", "corrections", "questions", "paraphrases"):
            out += [(f"phr:{sid}:{k}", t) for t in phr["slots"][sid][k]]
    for fid, f in P.facts.items():
        out += [(f"fact:{fid}", f["statement"])] + [(f"fact-para:{fid}", t) for t in phr["facts"][fid]]
    out += [("anchor", t) for t in phr["general"][:N_ANCHOR]]
    return out


def scan(P, texts):
    """-> sorted list of (new_slot_id, needle, source, snippet)."""
    hits = []
    normed = [(src, norm(t)) for src, t in texts]
    for sid in P.by_split["new"]:
        for nd in needles(P, sid):
            rx = re.compile(rf"(?<![a-z0-9]){re.escape(norm(nd))}(?![a-z0-9])")
            for src, t in normed:
                m = rx.search(t)
                if m:
                    hits.append((sid, nd, src, t[max(0, m.start() - 30): m.end() + 30]))
    return sorted(hits)


def full_leak_check(P, phr, requests):
    """Hits not covered by ACCEPTED."""
    return [h for h in scan(P, visible_text(P, phr, requests)) if (h[0], h[1]) not in ACCEPTED]


if __name__ == "__main__":
    P = Persona.load()
    hits = full_leak_check(P, jload(DATA / "phrasings.json"), jl_read(DATA / "requests.jsonl"))
    seen = set()
    for sid, nd, src, snip in hits:
        print(f"{sid:12s} {nd!r:30s} {src:40s} ...{snip}...")
        seen.add((sid, nd))
    print(len(hits), "hits;", len(seen), "distinct (slot, word) pairs")
    sys.exit(1 if hits else 0)
