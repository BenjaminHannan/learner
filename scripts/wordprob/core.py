"""Template validation, safe expression evaluation, instantiation, dedupe for wordprob-v1.

No eval(): expressions are parsed with `ast`, whitelisted, and evaluated by a tiny interpreter.
Answers always come from this code, never from the LLM.
"""
import ast
import hashlib
import random
import re

MAX_VAL = 100000
OPS = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.FloorDiv: "/"}
SLOT_RE = re.compile(r"\{([a-z][a-z0-9_]*)\}")
STEP_RE = re.compile(r"^s[1-4]$")


class Bad(Exception):
    pass


def parse_expr(src, allowed_names):
    """Parse src into an ast.Expression; raise Bad unless it only uses + - * // ints and allowed names."""
    if not isinstance(src, str) or len(src) > 200:
        raise Bad("expr_type")
    try:
        tree = ast.parse(src.strip(), mode="eval")
    except SyntaxError:
        raise Bad("expr_syntax")
    for node in ast.walk(tree):
        if isinstance(node, (ast.Expression, ast.Load)):
            continue
        if isinstance(node, ast.BinOp) and type(node.op) in OPS:
            continue
        if type(node) in OPS:
            continue
        if isinstance(node, ast.Constant) and type(node.value) is int and 0 <= node.value <= 1000:
            continue
        if isinstance(node, ast.Name) and node.id in allowed_names:
            continue
        raise Bad("expr_node_" + type(node).__name__)
    return tree


def evaluate(node, env):
    """Evaluate a whitelisted tree. Raises Bad on inexact division, zero div, or overflow."""
    if isinstance(node, ast.Expression):
        return evaluate(node.body, env)
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        return env[node.id]
    if isinstance(node, ast.BinOp):
        a, b = evaluate(node.left, env), evaluate(node.right, env)
        t = type(node.op)
        if t is ast.Add:
            r = a + b
        elif t is ast.Sub:
            r = a - b
        elif t is ast.Mult:
            r = a * b
        elif t is ast.FloorDiv:
            if b == 0 or a % b != 0:
                raise Bad("inexact_div")
            r = a // b
        else:
            raise Bad("op")
        if r < 0 or r > MAX_VAL:
            raise Bad("range")
        return r
    raise Bad("node")


COMMON_CAPS = set("the a an if each every how what on at in after before then when there for one two three four "
                  "five six seven eight nine ten it he she they his her their its this that these those some "
                  "during while with without by to of and but or so as from over under about all both many "
                  "how much last next first second third later now today yesterday tomorrow once twice".split())


def masked_words(text):
    """Word tokens; digits, {slots} and capitalised names become '#'/'@' (stops name-swap near-dups)."""
    t = SLOT_RE.sub(" # ", text)
    t = re.sub(r"\d[\d,\.]*", " # ", t)
    out = []
    for w in re.findall(r"#|[A-Za-z][A-Za-z']*", t):
        if w == "#":
            out.append(w)
        elif w[0].isupper() and w.lower() not in COMMON_CAPS:
            out.append("@")
        else:
            out.append(w.lower())
    return out


def ngrams(words, n):
    return {" ".join(words[i:i + n]) for i in range(len(words) - n + 1)}


def template_id(t):
    key = re.sub(r"\s+", " ", t["text"].strip().lower()) + "|" + t["answer"].replace(" ", "")
    return "t_" + hashlib.sha1(key.encode()).hexdigest()[:12]


def check_schema(t):
    """Static checks. Returns normalised template dict or raises Bad(reason)."""
    if not isinstance(t, dict):
        raise Bad("schema")
    try:
        text = t["text"]
        slots = t["slots"]
        answer = t["answer"]
        steps = t["steps"]
    except KeyError:
        raise Bad("schema_missing")
    if not isinstance(text, str) or not isinstance(slots, dict) or not isinstance(steps, list):
        raise Bad("schema")
    text = text.strip()
    if not (40 <= len(text) <= 700) or not text.endswith("?"):
        raise Bad("text_shape")
    if re.search(r"\d", SLOT_RE.sub("", text)):
        raise Bad("digit_in_text")
    if re.search(r"[{}]", SLOT_RE.sub("", text)):
        raise Bad("stray_brace")
    if not 1 <= len(steps) <= 4:
        raise Bad("step_count")
    if "n_steps" in t and t["n_steps"] != len(steps):
        raise Bad("step_count_mismatch")
    if not slots or len(slots) > 6:
        raise Bad("slot_count")
    norm_slots = {}
    for k, rng in slots.items():
        if not re.fullmatch(r"[a-z][a-z0-9_]*", k) or STEP_RE.match(k):
            raise Bad("slot_name")
        if (not isinstance(rng, list) or len(rng) != 2 or not all(type(x) is int for x in rng)
                or rng[0] < 2 or rng[1] < rng[0] or rng[1] > MAX_VAL):
            raise Bad("slot_range")
        norm_slots[k] = (rng[0], rng[1])
    used_in_text = SLOT_RE.findall(text)
    if set(used_in_text) != set(norm_slots):
        raise Bad("slot_text_mismatch")
    # every slot must appear in text exactly... at least once (checked) and in some step
    parsed_steps = []
    for i, s in enumerate(steps):
        names = set(norm_slots) | {"s%d" % j for j in range(1, i + 1)}
        tree = parse_expr(s, names)
        body = tree.body
        if not (isinstance(body, ast.BinOp) and isinstance(body.left, (ast.Name, ast.Constant))
                and isinstance(body.right, (ast.Name, ast.Constant))):
            raise Bad("step_not_single_op")
        parsed_steps.append(tree)
    ans_tree = parse_expr(answer, set(norm_slots))
    step_names = set()
    for tr in parsed_steps:
        step_names |= {n.id for n in ast.walk(tr) if isinstance(n, ast.Name)}
    if not set(norm_slots) <= step_names:
        raise Bad("slot_unused")
    for j in range(1, len(steps)):  # each intermediate consumed later
        if "s%d" % j not in step_names:
            raise Bad("step_unused")
    div = t.get("divisible", []) or []
    if not isinstance(div, list) or len(div) > 3:
        raise Bad("divisible")
    for p in div:
        if not (isinstance(p, list) and len(p) == 2 and p[0] in norm_slots and p[1] in norm_slots and p[0] != p[1]):
            raise Bad("divisible")
    topic = re.sub(r"[^a-z0-9_]+", "_", str(t.get("topic", "misc")).lower()).strip("_") or "misc"
    out = {"text": text, "slots": {k: list(v) for k, v in norm_slots.items()}, "divisible": div,
           "answer": answer.strip(), "steps": [s.strip() for s in steps], "n_steps": len(steps),
           "topic": topic, "unit": str(t.get("unit", ""))[:30]}
    out["id"] = template_id(out)
    return out, parsed_steps, ans_tree


def draw(t, rng):
    """Draw slot values honouring divisibility constraints. Raises Bad if impossible."""
    sl = {k: tuple(v) for k, v in t["slots"].items()}
    vals = {}
    dividends = {p[0]: p[1] for p in t["divisible"]}
    if len(dividends) != len(t["divisible"]) or set(dividends) & set(dividends.values()):
        raise Bad("divisible_cycle")
    for k in sl:
        if k not in dividends:
            vals[k] = rng.randint(*sl[k])
    for k, d in dividends.items():
        lo, hi = sl[k]
        dv = vals[d]
        a, b = -(-lo // dv), hi // dv
        if a > b:
            raise Bad("divisible_empty")
        vals[k] = rng.randint(a, b) * dv
    return vals


def run(t, parsed_steps, vals):
    """Return (list of step results, list of step operand tuples) or raise Bad."""
    env = dict(vals)
    results, ops = [], []
    for i, tr in enumerate(parsed_steps):
        body = tr.body
        l, r = evaluate(body.left, env), evaluate(body.right, env)
        v = evaluate(tr, env)
        results.append(v)
        ops.append((l, OPS[type(body.op)], r))
        env["s%d" % (i + 1)] = v
    return results, ops


def scratchpad(results, ops):
    parts = ["%d %s %d = %d." % (l, o, r, v) for (l, o, r), v in zip(ops, results)]
    parts.append("Answer: %d" % results[-1])
    return " ".join(parts)


def instance(t, parsed_steps, ans_tree, vals):
    """Full instance or raise Bad. Answer comes from the answer expression and must equal last step."""
    results, ops = run(t, parsed_steps, vals)
    ans = evaluate(ans_tree, vals)
    if ans != results[-1] or ans < 1:
        raise Bad("steps_do_not_compose" if ans != results[-1] else "answer_nonpositive")
    q = SLOT_RE.sub(lambda m: str(vals[m.group(1)]), t["text"])
    return {"question": q, "answer": ans, "scratchpad": scratchpad(results, ops),
            "steps": ["%d %s %d = %d" % (l, o, r, v) for (l, o, r), v in zip(ops, results)]}


def jaccard(a, b):
    return len(a & b) / max(1, len(a | b))


class Acceptor:
    """Deterministic, order-dependent template acceptance pipeline."""

    def __init__(self, old_questions):
        self.old8 = set()
        for q in old_questions:
            self.old8 |= ngrams(masked_words(q), 8)
        self.accepted = {}      # id -> template
        self.sets = []          # 3-gram sets by index
        self.index = {}         # trigram -> list of idx
        self.rejections = {}

    def _rej(self, r):
        self.rejections[r] = self.rejections.get(r, 0) + 1
        return r

    def add(self, cand):
        """Return None if accepted else reason string."""
        try:
            t, ps, at = check_schema(cand)
        except Bad as e:
            return self._rej(str(e))
        if t["id"] in self.accepted:
            return self._rej("duplicate_id")
        rng = random.Random(t["id"])
        try:
            ok = 0
            for _ in range(50):
                try:
                    instance(t, ps, at, draw(t, rng))
                    ok += 1
                except Bad as e:
                    if str(e) in ("divisible_cycle", "divisible_empty"):
                        raise
                    if str(e) == "steps_do_not_compose":
                        return self._rej("steps_do_not_compose")
            if ok < 45:
                return self._rej("low_valid_rate")
            comp = 0
            for _ in range(20):  # compose check on valid draws
                for _try in range(20):
                    try:
                        instance(t, ps, at, draw(t, rng))
                        comp += 1
                        break
                    except Bad as e:
                        if str(e) == "steps_do_not_compose":
                            return self._rej("steps_do_not_compose")
            if comp < 20:
                return self._rej("low_valid_rate")
        except Bad as e:
            return self._rej(str(e))
        w = masked_words(t["text"])
        if ngrams(w, 8) & self.old8:
            return self._rej("leak_8gram")
        g = ngrams(w, 3)
        cands = set()
        for x in g:
            cands.update(self.index.get(x, ()))
        for i in cands:
            if jaccard(g, self.sets[i]) > 0.7:
                return self._rej("near_duplicate")
        idx = len(self.sets)
        self.sets.append(g)
        for x in g:
            self.index.setdefault(x, []).append(idx)
        self.accepted[t["id"]] = t
        return None


def split_of(tid, salt):
    h = int(hashlib.sha256((salt + "|" + tid).encode()).hexdigest(), 16) % 100
    return "train" if h < 80 else ("dev" if h < 90 else "heldout_template")


def make_instances(t, n, seed_salt=""):
    ok, ps, at = check_schema(t)
    rng = random.Random("inst|" + seed_salt + t["id"])
    seen, out, tries = set(), [], 0
    while len(out) < n and tries < n * 30:
        tries += 1
        try:
            v = draw(ok, rng)
            key = tuple(sorted(v.items()))
            if key in seen:
                continue
            inst = instance(ok, ps, at, v)
        except Bad:
            continue
        seen.add(key)
        out.append(inst)
    return out
