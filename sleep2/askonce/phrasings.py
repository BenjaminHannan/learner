"""Step 3: Haiku (Batches) pre-writes every piece of text the GPU jobs need, so the Kaggle runs never call the API.
Per training/silent slot: 3 answer phrasings, 3 correction phrasings, 2 chosen-side questions (naming the slot with the 2 most likely values),
8 fact paraphrases. Per background fact: 8 paraphrases. Plus 200 general prompts (100 KL-anchor, 100 general-ask-rate eval).
"""
import random
import re
import sys

from .batches import parse_json, req, run_batch
from .config import DATA, HAIKU, N_ANCHOR, N_GENERAL, SEED_WORLD, jdump, norm, sha256_file
from .requests_gen import label_name
from .world import Persona

N_ANS, N_COR, N_Q, N_PARA = 3, 3, 2, 8


def value_in(text, s):
    t = norm(text)
    k, v = s["kind"], s["value"]
    if k == "duration":
        return bool(re.search(rf"(?<!\d){re.escape(v)}(?!\d)", t))
    if k == "mode":
        return ("send" in t or "sent" in t) if v == "send_email" else ("draft" in t)
    return norm(v) in t


def option_in(text, s, c):
    t = norm(text)
    if s["kind"] == "duration":
        return bool(re.search(rf"(?<!\d){re.escape(c['value'])}(?!\d)", t))
    if s["kind"] == "mode":
        return ("send" in t) if c["value"] == "send_email" else ("draft" in t)
    return norm(c["value"]) in t or (len(label_name(c["label"])) > 3 and norm(label_name(c["label"])) in t)


def two_options(s):
    true = next(c for c in s["candidates"] if c["value"] == s["value"])
    other = next(c for c in s["candidates"] if c["value"] != s["value"])
    return true, other


def slot_prompt(s):
    true, other = two_options(s)
    return (f"Fictional test world. Ben talks to his assistant. Slot: Ben's reference '{s['ref']}' ({s['kind']}). The TRUE value is {true['value']} "
            f"({true['label']}). The most likely WRONG alternative is {other['value']} ({other['label']}).\n"
            f"Write JSON {{\"answers\": [{N_ANS} different short replies Ben types when the assistant asks him which one he means; EACH must state the true value "
            f"{true['value']} exactly (for send/draft: the word send or draft; for minutes: the number) and must NOT mention any action such as sending, drafting, sharing, opening or scheduling], "
            f"\"corrections\": [{N_COR} different short messages Ben types AFTER the assistant guessed wrong, correcting it; EACH must state the true value exactly and must NOT mention any action such as sending, drafting, sharing, opening or scheduling], "
            f"\"questions\": [{N_Q} different ONE-line questions the assistant asks, naming '{s['ref']}' and offering exactly the two options "
            f"{true['value']} ({true['label']}) and {other['value']} ({other['label']}) in either order; under 30 words; no 'ASK' prefix], "
            f"\"paraphrases\": [{N_PARA} different plain statements of the fact '{s['ref']} = {true['value']} ({true['label']})', phrased as the assistant's memory notes; "
            f"EACH names '{s['ref']}' and states the true value exactly]}}. Return only the JSON.")


def check_slot(out, s):
    why = []
    true, other = two_options(s)
    for key, n in (("answers", N_ANS), ("corrections", N_COR), ("questions", N_Q), ("paraphrases", N_PARA)):
        arr = out.get(key)
        if not isinstance(arr, list) or len(arr) < n:
            return [f"{key} count"]
        out[key] = [str(x).strip() for x in arr[:n]]
    for x in out["answers"] + out["corrections"] + out["paraphrases"]:
        if not value_in(x, s):
            why.append("value missing: " + x[:50])
    if s["kind"] != "mode":  # Ben's replies must not name an action (they would contradict the tool of the request)
        for x in out["answers"] + out["corrections"]:
            if re.search(r"\b(send|sent|sending|draft|drafts|share|shared|email|emails)\b", x.lower()):
                why.append("names an action: " + x[:40])
    for x in out["paraphrases"]:
        if norm(s["key_token"]) not in norm(x):
            why.append("ref missing in paraphrase")
    for x in out["questions"]:
        if norm(s["key_token"]) not in norm(x) and norm(s["ref"]) not in norm(x):
            why.append("question lacks ref")
        if not (option_in(x, s, true) and option_in(x, s, other)):
            why.append("question lacks the two options")
        if x.upper().startswith("ASK") or len(x.split()) > 40 or "\n" in x:
            why.append("question format")
    return why


FACT_PROMPT = ("Fictional test world. Write JSON {{\"paraphrases\": [{n} different plain one-sentence statements of this fact, as an assistant's memory notes, "
               "each containing the exact string '{a}']}} for the fact: {st} Return only the JSON.")
GEN_PROMPT = ("Write JSON {{\"prompts\": [60 varied prompts a person might type to a general chatbot: trivia, explanations, math word problems, short coding tasks, "
              "writing requests, advice, translations. Each a few words to two sentences, fully specified and clear (no missing details). Theme seed: {theme}. "
              "Nothing about email, calendar or files.]}} Return only the JSON.")
THEMES = ["science and nature", "history and geography", "math and logic", "coding and computers", "writing and language", "health, cooking and daily life"]


def main():
    P = Persona.load()
    slots = [P.slot(i) for i in P.by_split["train"] + P.by_split["silent"]]
    result = {"slots": {}, "facts": {}, "general": []}
    pending = {f"slot__{s['slot_id']}": slot_prompt(s) for s in slots}
    pending.update({f"fact__{f['fact_id']}": FACT_PROMPT.format(n=N_PARA, a=f["recall_a"], st=f["statement"]) for f in P.facts.values()})
    gen_reqs = {f"gen__{i}": GEN_PROMPT.format(theme=t) for i, t in enumerate(THEMES)}
    pending.update(gen_reqs)
    for rnd in range(4):
        if not pending:
            break
        out, _ = run_batch([req(k, HAIKU, v, 6000) for k, v in pending.items()], f"phrasings-r{rnd}")
        nxt = {}
        for k, v in pending.items():
            try:
                o = parse_json(out[k])
                if k.startswith("slot__"):
                    s = P.slot(k[6:])
                    why = check_slot(o, s)
                    if why:
                        raise ValueError("; ".join(why[:2]))
                    result["slots"][s["slot_id"]] = {key: o[key] for key in ("answers", "corrections", "questions", "paraphrases")}
                elif k.startswith("fact__"):
                    f = P.facts[k[6:]]
                    ps = [str(x).strip() for x in o["paraphrases"][:N_PARA]]
                    if len(ps) < N_PARA or any(norm(f["recall_a"]) not in norm(x) for x in ps):
                        raise ValueError("fact paraphrase")
                    result["facts"][f["fact_id"]] = ps
                else:
                    result["general"] += [str(x).strip() for x in o["prompts"]]
            except Exception as e:
                print("retry", k, str(e)[:100], file=sys.stderr)
                nxt[k] = v + "\nIMPORTANT: your previous attempt broke the rules; follow every requirement exactly."
        pending = nxt
    if pending:
        raise SystemExit(f"{len(pending)} phrasing items failed: {list(pending)[:5]}")
    seen, gen = set(), []
    for g in result["general"]:
        if norm(g) not in seen and not re.search(r"email|calendar|\bfile\b|meeting", norm(g)) and 3 <= len(g.split()) <= 60:
            seen.add(norm(g))
            gen.append(g)
    if len(gen) < N_ANCHOR + N_GENERAL:
        raise SystemExit(f"only {len(gen)} usable general prompts")
    random.Random(SEED_WORLD).shuffle(gen)
    result["general"] = gen[:N_ANCHOR + N_GENERAL]
    jdump(DATA / "phrasings.json", result)
    (DATA / "phrasings.sha256").write_text(sha256_file(DATA / "phrasings.json") + "  phrasings.json\n")
    print("phrasings frozen")


if __name__ == "__main__":
    main()
