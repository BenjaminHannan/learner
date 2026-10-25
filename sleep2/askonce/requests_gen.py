"""Step 2: the request stream for days 1-7. CODE decides every item's composition and gold (slots, tool, literals) from the persona;
Sonnet (Batches) only WRITES the natural message for each spec. Code validates each text (reference word present, no leaked values,
literals present) and re-requests failures. Then asserts the leakage rule (new-ambiguity slots never in days 1-5 text) and freezes.
(Named requests_gen.py, not requests.py, so it cannot shadow the `requests` library.)
"""
import random
import re
import sys

from .batches import parse_json, req, run_batch
from .config import (DATA, DAYS_TRAIN, EVAL_H, EVAL_R, N_SILENT_ITEMS, PER_DAY, SEED_WORLD, SONNET, jl_read, jl_write, norm, sha256_file)
from .tools_mock import KEY_ARGS
from .world import CONTACT_ARG, TOOLS_FOR, Persona

DUR_LIT = [30, 45, 60]


def label_name(label):
    return label.split(" (")[0].strip()


def usable_extras(P, day):
    """Extra emails/paths/events usable as literals; for days 1-5 those containing a held-out word are dropped (they would leak a new slot)."""
    if day > DAYS_TRAIN:
        return P.extras
    av = avoid_words(P)
    return {k: [e for e in v if not any(re.search(rf"(?<![a-z0-9]){w}(?![a-z0-9])", norm(e["value"])) or w in norm(e["value"]) for w in av)] for k, v in P.extras.items()}


def make_spec(rng, P, tool, sid, split, day, ex_state):
    """One request spec with gold. sid=None -> fully specified (every key arg literal)."""
    ex = usable_extras(P, day)
    pick = lambda k: ex[k][ex_state[k] % len(ex[k])]["value"]  # noqa: E731

    def nxt(k):
        v = pick(k)
        ex_state[k] += rng.randint(1, 3)
        return v
    args, arg_slots, lits = {}, {}, {}
    s = P.slot(sid) if sid else None
    kind = s["kind"] if s else None
    if kind == "mode":
        tool = s["value"]
    for a in KEY_ARGS[tool]:
        if s and kind == "contact" and a == CONTACT_ARG[tool]:
            args[a] = [s["value"]] if a == "attendees" else s["value"]
            arg_slots[a] = sid
        elif s and kind == "meeting" and a == "event_id":
            args[a], arg_slots[a] = s["value"], sid
        elif s and kind == "duration" and a == "duration_min":
            args[a], arg_slots[a] = int(s["value"]), sid
        elif s and kind == "file" and a == "path":
            args[a], arg_slots[a] = s["value"], sid
        else:  # literal stated in the message
            if a in ("to", "with"):
                v = nxt("emails")
            elif a == "attendees":
                v = [nxt("emails")]
            elif a == "duration_min":
                v = rng.choice(DUR_LIT)
            elif a == "event_id":
                v = nxt("events")
            else:
                v = nxt("paths")
            args[a], lits[a] = v, v
    if kind == "mode":
        arg_slots["tool"] = sid
    return {"tool": tool, "slots": [sid] if sid else [], "underspecified": bool(sid), "split": split, "day": day,
            "gold": {"tool": tool, "args": args}, "arg_slots": arg_slots, "literals": lits}


def intent(spec, P):
    t, g = spec["tool"], spec["gold"]["args"]
    ref = None
    kind = None
    if spec["slots"]:
        s = P.slot(spec["slots"][0])
        ref, kind = s["ref"], s["kind"]
    lit = spec["literals"]
    if spec["underspecified"]:
        who = f"the person/thing Ben calls '{ref}'"
        base = {
            "send_email": f"Ben wants to send an email to {who}.", "draft_email": f"Ben wants an email to {who} prepared.",
            "create_event": f"Ben wants to create a calendar event with {who}." if kind == "contact" else "Ben wants to create a calendar event",
            "move_event": f"Ben wants to move/reschedule {who} to a new time.", "open_file": f"Ben wants to open {who}.",
            "share_file": f"Ben wants to share a file with someone" if kind == "file" else f"Ben wants to share a file with {who}.",
        }[t]
        if kind == "mode":
            base = f"Ben wants to email an address (given below) in the group he calls '{ref}'. Do NOT say whether to send it now or just draft it."
        if kind == "duration":
            base = f"Ben wants to schedule a calendar event of the kind he calls '{ref}'. Do NOT mention how long it is."
        if kind == "file" and t == "share_file":
            base = f"Ben wants to share {who} with someone (address given below)."
        if kind == "file" and t == "open_file":
            base = f"Ben wants to open {who}."
        return base
    return {"send_email": "Ben wants an email SENT now.", "draft_email": "Ben wants an email saved as a DRAFT (say 'draft').",
            "create_event": "Ben wants to create a calendar event.", "move_event": "Ben wants to move an event to a new time.",
            "open_file": "Ben wants to open a file.", "share_file": "Ben wants to share a file with someone."}[t]


def spec_to_prompt_item(i, spec, P):
    extra = {"never_use_these_words": avoid_words(P)} if spec["day"] <= DAYS_TRAIN else {}
    return {**extra, "i": i, "intent": intent(spec, P), "must_state_exactly": {k: v for k, v in spec["literals"].items()},
            "must_include_word": (P.slot(spec["slots"][0])["key_token"] if spec["slots"] else None),
            "mode": "refer to the unknown entity only by the reference word (never write ITS address/path/id/length), but still write every must_state_exactly value, which belongs to other parts of the request" if spec["underspecified"] else "state every value in must_state_exactly literally"}


def avoid_words(P):
    """Words of held-out (new-ambiguity) slots that days 1-5 text must not contain: key tokens and the long reference words."""
    from .persona import _avoid
    out = set()
    for sid in P.by_split["new"]:
        out |= _avoid(P.slot(sid))
    return sorted(out)


def check_text(spec, text, P):
    """Returns '' if the text is acceptable, otherwise a short reason."""
    t = norm(text)
    if spec["day"] <= DAYS_TRAIN:
        for w in avoid_words(P):
            if re.search(rf"(?<![a-z0-9]){re.escape(w)}(?![a-z0-9])", t):
                return f"uses held-out word {w}"
    if not (6 <= len(t) <= 400):
        return "length"
    for a, v in spec["literals"].items():
        if a == "duration_min":
            if not re.search(rf"\b{v}\s*-?\s*(min|minute)", t):
                return f"literal {a}"
        else:
            vv = v[0] if isinstance(v, list) else v
            if norm(vv) not in t:
                return f"literal {a}"
    if spec["underspecified"]:
        s = P.slot(spec["slots"][0])
        if not re.search(rf"\b{re.escape(norm(s['key_token']))}", t):
            return "missing reference word"
        for c in s["candidates"]:
            if s["kind"] in ("contact", "meeting", "file"):
                if norm(c["value"]) in t or (len(label_name(c["label"])) > 4 and norm(label_name(c["label"])) in t):
                    return "leaks a candidate"
        if s["kind"] == "duration" and re.search(r"\b\d+\s*-?\s*(min|minute|hour|hr)", t):
            return "states a length"
        if s["kind"] == "mode" and re.search(r"\b(send|sent|sending|draft|drafts)\b", t):
            return "states send/draft"
    else:
        if spec["tool"] == "send_email" and not re.search(r"\bsend|\bsent", t):
            return "explicit send missing"
        if spec["tool"] == "draft_email" and "draft" not in t:
            return "explicit draft missing"
    return ""


def build_specs(P, seed=SEED_WORLD):
    rng = random.Random(seed + 1)
    ex_state = {"emails": 0, "paths": 0, "events": 0}
    specs = []
    train_pool = [sid for sid in P.by_split["train"] + P.by_split["silent"]]
    rng.shuffle(train_pool)
    half = [train_pool[:20], train_pool[20:40]]
    use_count = {}

    def tool_for(sid):
        k = use_count.get(sid, 0)
        use_count[sid] = k + 1
        ts = TOOLS_FOR[P.slot(sid)["kind"]]
        return ts[(k + hash_str(sid)) % len(ts)]

    for day in range(1, DAYS_TRAIN + 1):
        sl = list(half[(day - 1) % 2])
        rng.shuffle(sl)
        items = [make_spec(rng, P, tool_for(sid), sid, "train", day, ex_state) for sid in sl]
        items += [make_spec(rng, P, rng.choice(sorted(KEY_ARGS)), None, "train", day, ex_state) for _ in range(PER_DAY - len(sl))]
        rng.shuffle(items)
        specs += items

    def eval_items(split, n, slot_list, day, underspec=True):
        out = []
        order = []
        while len(order) < n:
            ch = list(slot_list)
            rng.shuffle(ch)
            order += ch
        for sid in order[:n]:
            if underspec:
                out.append(make_spec(rng, P, tool_for(sid), sid, split, day, ex_state))
        return out

    normal = P.by_split["train"]
    for split, n in EVAL_H.items():
        specs += eval_items(split, n, normal, 6) if split == "H_know" else eval_items(split, n, P.by_split["new"], 6) if split == "H_new" else \
            [make_spec(rng, P, rng.choice(sorted(KEY_ARGS)), None, split, 6, ex_state) for _ in range(n)]
    for split, n in EVAL_R.items():
        specs += eval_items(split, n, normal, 7) if split == "R_know" else eval_items(split, n, P.by_split["new"], 7) if split == "R_new" else \
            [make_spec(rng, P, rng.choice(sorted(KEY_ARGS)), None, split, 7, ex_state) for _ in range(n)]
    specs += eval_items("silent", N_SILENT_ITEMS, P.by_split["silent"], 7)
    counters = {}
    for sp in specs:
        counters[sp["split"]] = counters.get(sp["split"], 0) + 1
        sp["req_id"] = f"{sp['split']}-{counters[sp['split']]:03d}"
    return specs


def hash_str(s):
    return sum(ord(c) * (i + 1) for i, c in enumerate(s))


PROMPT = ("Ben (a busy high-schooler) texts his email/calendar/files assistant. For each item below write ONE short, casual, natural message "
          "(5-30 words) in Ben's voice for the given intent. Vary the wording, tone and sentence shape between items; invent harmless details "
          "(topic, time like 'tomorrow') but never invent addresses, file paths, event ids or lengths of time unless listed in must_state_exactly.\n"
          "Everything in must_state_exactly must be copied CHARACTER FOR CHARACTER into the message: whole file paths with every folder (never just the file name), "
          "whole email addresses (never just a name), event ids as written, and lengths as digits followed by 'minutes' (write '45 minutes', never 'forty-five' or 'an hour').\n"
          "Follow each item's 'mode' and 'must_include_word' exactly. Return ONLY a JSON list [{\"i\": <number>, \"text\": \"...\"}].\n\nItems:\n")


def prompt_for(items):
    import json
    return PROMPT + "\n".join(json.dumps(x, ensure_ascii=False) for x in items)


def generate_texts(specs, P, chunk=24, rounds=4, label="requests", cache=None):
    """cache: path of a json {req_id: text} that is read first and updated after every round (a re-run only pays for what is missing)."""
    from .config import jdump, jload
    import os
    texts, reasons = {}, {}
    cached = jload(cache) if cache and os.path.exists(cache) else {}
    for i, sp in enumerate(specs):
        t = cached.get(sp["req_id"])
        if t and not check_text(sp, t, P) and norm(t) not in {norm(v) for v in texts.values()}:
            texts[i] = t
    pending = [i for i in range(len(specs)) if i not in texts]
    for rnd in range(rounds):
        if not pending:
            break
        reqs, plan = [], {}
        for ci in range(0, len(pending), chunk):
            ids = pending[ci:ci + chunk]
            items = [spec_to_prompt_item(i, specs[i], P) for i in ids]
            if rnd:
                for it in items:
                    it["retry_note"] = f"previous attempt rejected: {reasons.get(it['i'], '?')}; obey the rules strictly"
            cid = f"{label}-r{rnd}-c{ci // chunk}"
            reqs.append(req(cid, SONNET, prompt_for(items), 8000))
            plan[cid] = ids
        out, _ = run_batch(reqs, f"{label}-round{rnd}")
        new_pending = []
        for cid, ids in plan.items():
            got = {}
            try:
                arr = parse_json(out[cid])
                arr = [arr] if isinstance(arr, dict) else arr
                got = {int(x["i"]): x["text"] for x in arr if isinstance(x, dict) and "i" in x and "text" in x}
            except Exception as e:
                print("chunk parse failed", cid, e, file=sys.stderr)
            for i in ids:
                why = "no text" if i not in got else check_text(specs[i], got[i], P)
                if not why and norm(got[i]) in {norm(v) for v in texts.values()}:
                    why = "duplicate text"
                if why:
                    reasons[i] = why
                    new_pending.append(i)
                else:
                    texts[i] = got[i].strip()
        pending = new_pending
        if cache:
            jdump(cache, {specs[i]["req_id"]: t for i, t in texts.items()})
        jdump(DATA / "requests_failures.json", {specs[i]["req_id"]: {"why": reasons.get(i), "spec": specs[i]} for i in pending})
        print(f"[{label}] round {rnd}: {len(texts)}/{len(specs)} accepted", flush=True)
    return texts, pending, reasons


def leak_check(rows, P):
    """Leakage rule: new-ambiguity slots must never appear in days 1-5 text (reference word, key token, any candidate value or name)."""
    train_text = norm(" \n ".join(r["text"] for r in rows if r["day"] <= DAYS_TRAIN))
    bad = []
    for sid in P.by_split["new"]:
        s = P.slot(sid)
        needles = {s["key_token"], s["ref"]}
        if s["kind"] in ("contact", "meeting", "file"):
            needles |= {c["value"] for c in s["candidates"]} | {label_name(c["label"]) for c in s["candidates"] if len(label_name(c["label"])) > 3}
        for n in needles:
            if re.search(rf"(?<![a-z0-9]){re.escape(norm(n))}(?![a-z0-9])", train_text):
                bad.append((sid, n))
    return bad


def main():
    P = Persona.load()
    specs = build_specs(P)
    texts, pending, reasons = generate_texts(specs, P, cache=DATA / "requests_texts_cache.json")
    rows = []
    for i, sp in enumerate(specs):
        if i in texts:
            sp = dict(sp)
            sp["text"] = texts[i]
            rows.append(sp)
    if pending:
        raise SystemExit(f"{len(pending)} specs without acceptable text after retries: {[(specs[i]['req_id'], reasons[i]) for i in pending[:8]]}")
    bad = leak_check(rows, P)
    if bad:
        raise SystemExit(f"LEAK: new-ambiguity slot text appears in days 1-5: {bad[:10]}")
    jl_write(DATA / "requests.jsonl", rows)
    (DATA / "requests.sha256").write_text(sha256_file(DATA / "requests.jsonl") + "  requests.jsonl\n")
    print("requests frozen:", len(rows))


if __name__ == "__main__":
    main()
