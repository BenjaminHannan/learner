"""Core of the generated skills curriculum: split rules, item context, family registry.

Every item is made by a program, carries the structured facts it was built from (`meta`), and is checkable
by a second program (`verify.py`). Nothing here reads any eval, gold, reserved or blind file.

HOLD-OUT RULES (all decided by SHA-256 of SPLIT_SEED + a stable key, so they never depend on draw order):
  answer   numeric answers whose hash falls under ANSWER_FRAC are never trained on (per family)
  frame    in every pool of sentence pieces, the last ceil-ish 20% by hash rank are never trained on
  vocab    same for names, nouns, real words and the syllables used to build made-up words
  variant  each family's structural variants: the last by hash rank (when a family has 3 or more) is held out
  family   a few whole skill families are never in train (see registry flags)
"""
import hashlib
import math
import random
import re

SPLIT_SEED = 20261003_77  # written down before any generation; change it and every split changes
ANSWER_FRAC = 0.15
FRAME_FRAC = 0.20
VOCAB_FRAC = 0.20
MAX_TOKENS_EST = 62  # estimated; inputs are capped at 64 tokens including EOS (real count checked by token_report.py)


def _h(*parts):
    s = "|".join(str(p) for p in (SPLIT_SEED,) + parts)
    return int.from_bytes(hashlib.sha256(s.encode()).digest()[:8], "big") / 2**64


_rank_cache = {}


def held_by_rank(kind, pool_key, value, pool, frac, min_pool):
    """True if `value` is among the held-out share of `pool` (ranked by hash)."""
    n = len(pool)
    if n < min_pool:
        return False
    key = (kind, pool_key, n)
    if key not in _rank_cache:
        order = sorted(pool, key=lambda v: _h(kind, pool_key, v))
        k = max(1, int(round(frac * n)))
        _rank_cache[key] = set(order[n - k:])
    return value in _rank_cache[key]


def answer_held(family, answer):
    return _h("answer", family, answer) < ANSWER_FRAC


# ---------------------------------------------------------------- vocab pools
NAMES = ["Ana", "Bo", "Cy", "Dax", "Eli", "Fay", "Gus", "Hana", "Ivo", "Jun", "Kai", "Lena", "Milo", "Nia", "Omar",
         "Pia", "Quin", "Rosa", "Sam", "Tess", "Uma", "Vic", "Wren", "Xavi", "Yara", "Zed", "Abe", "Bea", "Cal",
         "Dee", "Ed", "Flo", "Gil", "Hal", "Ida", "Jo", "Kit", "Lou", "Mae", "Ned", "Ola", "Pat", "Ray", "Sue",
         "Tom", "Una", "Val", "Walt", "Yul", "Zoe"]
NOUNS = ["apples", "marbles", "coins", "books", "pencils", "stickers", "shells", "cards", "badges", "pebbles",
         "keys", "cups", "plates", "stamps", "beads", "balloons", "lanterns", "nails", "scarves", "seeds",
         "tickets", "bottles", "boxes", "coats", "hats", "eggs", "pears", "plums", "rings", "tiles"]
WORDS = ["river", "stone", "lamp", "cloud", "bread", "chair", "tiger", "window", "forest", "garden", "pillow",
         "rocket", "candle", "mirror", "ladder", "barrel", "violin", "anchor", "button", "carpet", "dragon",
         "engine", "feather", "guitar", "hammer", "island", "jacket", "kettle", "lemon", "magnet", "needle",
         "onion", "pepper", "quilt", "ribbon", "saddle", "turtle", "umbrella", "valley", "wagon", "yogurt",
         "zipper", "bridge", "castle", "desert", "falcon", "harbor", "meadow", "pocket", "spider"]
SYLLABLES = ["ba", "ko", "lu", "mi", "ne", "pa", "ro", "su", "ti", "vo", "za", "fe", "gi", "hu", "jo", "ke", "la",
             "mo", "nu", "pe", "ra", "se", "tu", "vi", "wo", "xe", "yu", "zi", "do", "ha"]
CAT_WORDS = ["blip", "zorn", "fen", "glorp", "mib", "tarn", "quop", "drax", "vell", "snib", "hoom", "pliv", "krel",
             "yarp", "wumb", "jolt", "nask", "brim", "tosk", "frell"]
PLACES = ["box", "bag", "drawer", "shelf", "basket", "jar", "tray", "cupboard", "locker", "crate"]
COLORS = ["red", "blue", "green", "yellow", "purple", "orange", "black", "white", "pink", "brown"]


class Ctx:
    """One item's random source plus a record of which held-out pieces it touched."""

    def __init__(self, family, rng, diff):
        self.family, self.rng, self.diff = family, rng, diff
        self.flags = {"frame": False, "vocab": False, "variant": False}

    # pieces of sentences -------------------------------------------------
    def pick(self, slot, options):
        o = self.rng.choice(options)
        if held_by_rank("frame", f"{self.family}/{slot}", o, options, FRAME_FRAC, 5):
            self.flags["frame"] = True
        return o

    def _vocab(self, kind, pool):
        v = self.rng.choice(pool)
        if held_by_rank("vocab", kind, v, pool, VOCAB_FRAC, 5):
            self.flags["vocab"] = True
        return v

    def name(self):
        return self._vocab("names", NAMES)

    def names(self, k):
        out = []
        while len(out) < k:
            n = self.name()
            if n not in out:
                out.append(n)
        return out

    def noun(self):
        return self._vocab("nouns", NOUNS)

    def word(self):
        return self._vocab("words", WORDS)

    def words(self, k):
        out = []
        while len(out) < k:
            w = self.word()
            if w not in out:
                out.append(w)
        return out

    def catword(self):
        return self._vocab("catwords", CAT_WORDS)

    def place(self):
        return self._vocab("places", PLACES)

    def color(self):
        return self._vocab("colors", COLORS)

    def madeup(self, nsyl=None):
        nsyl = nsyl or self.rng.choice((2, 2, 3))
        return "".join(self._vocab("syllables", SYLLABLES) for _ in range(nsyl))

    def variant(self, variants):
        v = self.rng.choice(variants)
        if held_by_rank("variant", self.family, v, variants, 0.34, 3):
            self.flags["variant"] = True
        return v

    def difficulty_int(self, lo, hi):
        """Operand size grows with diff: diff 0 -> small end, 2 -> full range."""
        top = lo + (hi - lo) * (self.diff + 1) // 3
        return self.rng.randint(lo, max(lo, top))


# ---------------------------------------------------------------- registry
FAMILIES = {}


def family(fid, level, variants, doc, heldout_family=False, answer_open=True, parse_check=None, layout=False):
    def deco(fn):
        FAMILIES[fid] = {"id": fid, "level": level, "variants": list(variants), "doc": doc, "fn": fn,
                         "heldout_family": heldout_family, "answer_open": answer_open, "parse_check": parse_check, "layout": layout}
        return fn
    return deco


def est_tokens(text):
    """Conservative estimate for the LFM2.5 tokenizer (checked on 12,000 rows: it never came out below the real count
    once it passed 62). A number costs one space token plus one token per 3 digits; words cost 1 to 3. The real count
    comes from token_report.py with the pinned tokenizer file."""
    n = 1  # EOS
    for t in re.findall(r"\d+|[A-Za-z']+|[^\sA-Za-z\d]", text):
        if t.isdigit():
            n += 1 + math.ceil(len(t) / 3)
        elif len(t) <= 4:
            n += 1
        elif len(t) <= 7:
            n += 2
        else:
            n += 3
    return n


OPENERS = ["Solve this.", "Here is a puzzle.", "Think it through.", "Quick one:", "Read carefully.", "Work this out.",
           "Try this problem.", "A small challenge:", "Question time.", "Please help with this.", "Let's see.", "Next problem:"]
CLOSERS = ["Answer with just the result.", "Reply with the answer only.", "Keep it short.", "Give only the answer.",
           "No explanation needed.", "Just the answer, please.", "Be brief.", "State the result only."]
LAYOUTS = ["facts_first", "question_first", "labeled", "labeled_q_first"]


def _split_q(prompt):
    parts = re.split(r"(?<=[.?])\s+", prompt.strip())
    if len(parts) < 2 or not parts[-1].endswith("?"):
        return None
    return " ".join(parts[:-1]), parts[-1]


def apply_layout(prompt, layout):
    sp = _split_q(prompt)
    if sp is None or layout == "facts_first":
        return prompt
    facts, q = sp
    return {"question_first": f"{q} {facts}", "labeled": f"Facts: {facts} Question: {q}",
            "labeled_q_first": f"Question: {q} Facts: {facts}"}[layout]


def undo_layout(prompt, layout):
    if layout == "question_first":
        m = re.match(r"([^.?]*\?) (.*)$", prompt)
        return f"{m[2]} {m[1]}" if m else prompt
    if layout == "labeled":
        m = re.match(r"Facts: (.*) Question: (.*)$", prompt)
        return f"{m[1]} {m[2]}" if m else prompt
    if layout == "labeled_q_first":
        m = re.match(r"Question: (.*?\?) Facts: (.*)$", prompt)
        return f"{m[2]} {m[1]}" if m else prompt
    return prompt


def make_item(fid, seed, index, diff, force_variant=None):
    for attempt in range(60):
        it = _make_item(fid, seed, index, diff, force_variant, attempt)
        if not _ambiguous(it):
            return it
    raise RuntimeError(f"could not make an unambiguous {fid} item")


def _make_item(fid, seed, index, diff, force_variant, attempt):
    """Make one item. Returns the full record with hold-out flags; caller decides keep/reject."""
    fam = FAMILIES[fid]
    rng = random.Random(f"{seed}|{fid}|{index}" + (f"|{attempt}" if attempt else ""))
    ctx = Ctx(fid, rng, diff)
    variant = force_variant or ctx.variant(fam["variants"])
    out = fam["fn"](ctx, variant)
    ans = str(out["answer"])
    layout = "facts_first"
    if fam["layout"] and _split_q(out["prompt"]):
        layout = rng.choice(LAYOUTS)
        if held_by_rank("variant", "layouts", layout, LAYOUTS, 0.34, 3):
            ctx.flags["variant"] = True
        out["prompt"] = apply_layout(out["prompt"], layout)
    wrap = {"pre": "", "post": ""}
    if rng.random() < 0.5:
        wrap["pre"] = rng.choice(OPENERS)
        if held_by_rank("frame", "wrap_open", wrap["pre"], OPENERS, FRAME_FRAC, 5):
            ctx.flags["frame"] = True
    if rng.random() < 0.3:
        wrap["post"] = rng.choice(CLOSERS)
        if held_by_rank("frame", "wrap_close", wrap["post"], CLOSERS, FRAME_FRAC, 5):
            ctx.flags["frame"] = True
    out["prompt"] = " ".join(x for x in (wrap["pre"], out["prompt"], wrap["post"]) if x)
    flags = dict(ctx.flags)
    flags["answer"] = bool(fam["answer_open"]) and answer_held(fid, ans)
    flags["family"] = fam["heldout_family"]
    item = {
        "id": f"{fid}-{seed}-{index}",
        "family": fid, "level": fam["level"], "variant": variant, "layout": layout, "wrap": wrap, "diff": diff,
        "prompt": out["prompt"], "answer": ans,
        "accepted": [str(a) for a in out.get("accepted", [ans])],
        "steps": out.get("steps", []), "slots": [str(s) for s in out.get("slots", [])],
        "meta": out.get("meta", {}), "flags": flags,
    }
    item["est_tokens"] = est_tokens(item["prompt"])
    return item


def _ambiguous(item):
    """Induction families: reject items where more than one simple rule fits the examples but gives different answers."""
    from . import verify
    f = verify.AMBIG.get(item["family"])
    if f is None:
        return False
    w = item["wrap"]
    t = item["prompt"]
    if w["pre"]:
        t = t[len(w["pre"]) + 1:]
    if w["post"]:
        t = t[:-(len(w["post"]) + 1)]
    return f(undo_layout(t, item["layout"]))


def split_of(flags):
    """Primary label. 'train' means no held-out piece was touched."""
    for k in ("family", "variant", "frame", "vocab", "answer"):
        if flags.get(k):
            return "heldout_" + k
    return "train"


def only_flag(flags, k):
    """True if exactly flag k is raised (isolates one kind of shift)."""
    return flags.get(k) and not any(v for kk, v in flags.items() if kk != k and kk != "family") and not flags.get("family")
