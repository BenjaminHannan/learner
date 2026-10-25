"""CPU smoke helpers: a tiny random Llama + tokenizer built locally (no download), and a scripted stand-in policy for the day logs
(a random model emits gibberish, so the ASK / ACT / correction / annoyance code paths would otherwise never run)."""
import re
import zlib

from .config import DATA, jl_read
from .model_io import make_tiny
from .world import Persona, act_text, load_requests


def tiny_corpus(extra=()):
    rows = jl_read(DATA / "requests.jsonl") if (DATA / "requests.jsonl").exists() else []
    txt = [r["text"] for r in rows] + list(extra)
    txt += ["ACT {\"tool\": \"send_email\", \"args\": {\"to\": \"a@b.com\"}}", "ASK Which one do you mean?", "[Memory] [Lookup] [Request] none", "0123456789 ABCD."]
    return txt * 3


def make_tiny_model(path, extra=()):
    return "tiny:" + make_tiny(path, tiny_corpus(extra))


def scripted_gen(persona, requests):
    """gen(prompts, max_new, temperature, seed): behaves like a mediocre assistant. Fully specified -> mostly the right ACT (sometimes an
    unnecessary ASK); underspecified with the answer in memory -> right ACT; otherwise 50% ASK naming the reference, 50% a wrong guess.
    After an ASK + answer it acts on the answer (right 90% of the time)."""
    by_text = {r["text"]: r for r in requests}

    def one(prompt, seed):
        m = re.search(r"\[Request\]\n(.*?)<\|ifm\|im_end\|>", prompt, re.S)
        r = by_text.get(m.group(1)) if m else None
        if r is None:
            return "OTHER"
        h = zlib.crc32(f"{r['req_id']}|{seed}".encode()) % 100
        after_answer = prompt.count("<|ifm|im_start|>assistant") > 1
        if not r["underspecified"]:
            return ("ASK Which one do you mean?" if h < 12 else act_text(r["gold"])) if not after_answer else act_text(r["gold"])
        sid = r["slots"][0]
        s = persona.slot(sid)
        mem = prompt.split("[Lookup]")[0]
        known = s["value"].lower() in mem.lower() if s["kind"] not in ("mode", "duration") else (s["ref"].lower() in mem.lower())
        if after_answer or known:
            if h < 90:
                return act_text(r["gold"])
        elif h < 50:
            return f"ASK Which {s['ref']} do you mean, {s['candidates'][0]['value']} or {s['candidates'][1]['value']}?"
        wrong = next(c for c in persona.candidates(sid) if c["value"] != s["value"])
        g = dict(r["gold"], args=dict(r["gold"]["args"]))
        for a, sl in r["arg_slots"].items():
            if sl == sid:
                if a == "tool":
                    g["tool"] = "draft_email" if s["value"] == "send_email" else "send_email"
                else:
                    g["args"][a] = [wrong["value"]] if a == "attendees" else (int(wrong["value"]) if a == "duration_min" else wrong["value"])
        return act_text(g)

    def gen(prompts, max_new, temperature, seed):
        return [one(p, seed) for p in prompts]
    return gen
