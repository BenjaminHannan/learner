"""Persona / request records, prompt construction and K2 chat rendering. Pure Python (no torch)."""
import random
import re

from .config import DATA, GENERAL_SYSTEM, KINDS, SYSTEM, jload, jl_read, norm

IM_START, IM_END = "<|ifm|im_start|>", "<|ifm|im_end|>"
THINK_EMPTY = "<ifm|think>\n</ifm|think>"
SLOT_PREFIX = {"contact": "contact", "meeting": "meeting", "duration": "duration", "file": "file", "mode": "mode"}
ARG_OF = {"meeting": "event_id", "duration": "duration_min", "file": "path", "mode": "tool"}
CONTACT_ARG = {"send_email": "to", "draft_email": "to", "create_event": "attendees", "share_file": "with"}
TOOLS_FOR = {"contact": ["send_email", "draft_email", "create_event", "share_file"], "meeting": ["move_event"],
             "duration": ["create_event"], "file": ["open_file", "share_file"], "mode": ["send_email", "draft_email"]}


def slot_id(kind, i):
    return f"{kind}_{i:02d}"


class Persona:
    def __init__(self, d):
        self.d = d
        self.slots = {s["slot_id"]: s for s in d["slots"]}
        self.facts = {f["fact_id"]: f for f in d["facts"]}
        self.extras = d["extras"]
        self.by_split = {}
        for s in d["slots"]:
            self.by_split.setdefault(s["split"], []).append(s["slot_id"])
        self.ref_to_slot = {norm(s["ref"]): s["slot_id"] for s in d["slots"]}

    @classmethod
    def load(cls, path=None):
        return cls(jload(path or DATA / "persona.json"))

    def slot(self, sid):
        return self.slots[sid]

    def candidates(self, sid):
        """Display order of a slot's candidate values: fixed per slot (seeded by slot id), true value not first by construction."""
        s = self.slots[sid]
        c = list(s["candidates"])
        random.Random("cand-" + sid).shuffle(c)
        return c


def validate_persona(d):
    """Schema check; returns list of problems (empty = ok)."""
    bad = []
    slots = d.get("slots", [])
    if len(slots) != sum(KINDS.values()):
        bad.append(f"expected {sum(KINDS.values())} slots, got {len(slots)}")
    ids, refs, toks, vals = set(), set(), set(), set()
    for s in slots:
        for k in ("slot_id", "kind", "split", "ref", "key_token", "value", "candidates", "recall_q", "recall_a"):
            if k not in s or s[k] in (None, "", []):
                bad.append(f"{s.get('slot_id')} missing {k}")
        if s.get("slot_id") in ids:
            bad.append("dup slot id " + str(s.get("slot_id")))
        ids.add(s.get("slot_id"))
        if norm(s.get("ref", "")) in refs:
            bad.append("dup ref " + s.get("ref", ""))
        refs.add(norm(s.get("ref", "")))
        if norm(s.get("key_token", "")) in toks:
            bad.append("dup key_token " + s.get("key_token", ""))
        toks.add(norm(s.get("key_token", "")))
        cv = [c["value"] for c in s.get("candidates", [])]
        if s.get("value") not in cv:
            bad.append(f"{s.get('slot_id')} true value not among candidates")
        if len(set(map(norm, cv))) != len(cv) or len(cv) < 2:
            bad.append(f"{s.get('slot_id')} candidates must be >=2 distinct")
        if s.get("kind") in ("contact", "meeting", "file"):
            for v in cv:
                if norm(v) in vals:
                    bad.append(f"value reused across slots: {v}")
                vals.add(norm(v))
        if s.get("split") not in ("train", "new", "silent"):
            bad.append(f"{s.get('slot_id')} bad split")
    if len(d.get("facts", [])) != 40:
        bad.append(f"expected 40 facts, got {len(d.get('facts', []))}")
    for f in d.get("facts", []):
        for k in ("fact_id", "statement", "recall_q", "recall_a"):
            if not f.get(k):
                bad.append(f"fact {f.get('fact_id')} missing {k}")
    ex = d.get("extras", {})
    for k, n in (("emails", 12), ("paths", 8), ("events", 6)):
        if len(ex.get(k, [])) < n:
            bad.append(f"extras.{k} needs >= {n}")
    return bad


# ----------------------------------------------------------------------------- prompts
def lookup_block(persona, slot_ids):
    lines = []
    for sid in slot_ids:
        s = persona.slot(sid)
        cs = persona.candidates(sid)
        if s["kind"] == "mode":
            body = " | ".join(c["value"] for c in cs)
        elif s["kind"] == "duration":
            body = " | ".join(c["value"] + " min" for c in cs)
        else:
            body = "  ".join(f"{i + 1}) {c['value']} = {c['label']}" for i, c in enumerate(cs))
        lines.append(f"'{s['ref']}': {body}")
    return lines


def user_block(persona, req_text, slot_ids, memory_lines):
    mem = "\n".join(memory_lines) if memory_lines else "none"
    look = "\n".join(lookup_block(persona, slot_ids)) if slot_ids else "none"
    return f"[Memory]\n{mem}\n[Lookup]\n{look}\n[Request]\n{req_text}"


def first_messages(persona, req, memory_lines):
    slot_ids = req["slots"] if req.get("underspecified") else []
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user_block(persona, req["text"], slot_ids, memory_lines)}]


def general_messages(prompt):
    return [{"role": "system", "content": GENERAL_SYSTEM}, {"role": "user", "content": prompt}]


def fact_messages(q):
    return [{"role": "system", "content": "You are Ben's assistant. Answer with only the fact, as short as possible."}, {"role": "user", "content": q}]


def render(messages, add_gen=True, bos=""):
    """K2 no-think chat format (identical to skillsleep/templates/k2_nothink.jinja; verified against the real tokenizer in tests)."""
    out = [bos]
    for m in messages:
        if m["role"] == "assistant":
            out.append(f"{IM_START}assistant\n{THINK_EMPTY}{m['content']}{IM_END}")
        else:
            out.append(f"{IM_START}{m['role']}\n{m['content']}{IM_END}")
    if add_gen:
        out.append(f"{IM_START}assistant\n{THINK_EMPTY}")
    return "".join(out)


def act_text(action):
    import json
    return "ACT " + json.dumps({"tool": action["tool"], "args": dict(sorted(action["args"].items()))}, ensure_ascii=False)


def load_requests(split=None, day=None, path=None):
    rows = jl_read(path or DATA / "requests.jsonl")
    return [r for r in rows if (split is None or r["split"] == split) and (day is None or r["day"] == day)]


def words(s):
    return re.findall(r"[a-z0-9@._/-]+", norm(s))
