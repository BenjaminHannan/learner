"""Ask the Claude API for word-problem TEMPLATES only (never answers). Spend-capped, concurrent, resumable.

Usage: python gen_templates.py --out DIR --calls N [--target 2600] [--budget 25] [--workers 8]
Raw API outputs go to DIR/raw_calls.jsonl, parsed candidates to DIR/candidates.jsonl, spend to DIR/spend.json.
The API key is read from env LEARNER_ANTHROPIC_API_KEY and is never printed or written.
"""
import argparse, json, os, random, sys, threading, time
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core

MODEL = "claude-sonnet-5-5"
PRICE_IN, PRICE_OUT = 3.0, 15.0  # USD per million tokens (assumed Sonnet pricing)
URL = "https://api.anthropic.com/v1/messages"
MAX_TOKENS = 9000
RESERVE = MAX_TOKENS * PRICE_OUT / 1e6 + 0.02  # worst-case cost of one call

TOPICS = ["school supplies", "bakery and baking", "farm and garden", "sports teams", "library and books",
          "travel and trains", "toy store", "pet shop", "music and band", "art class", "cooking and recipes",
          "construction and building", "science fair", "movie theater", "fundraising and money", "packing and boxes",
          "birthday parties", "hiking and camping", "fishing and boating", "classroom seating", "post office and mail",
          "orchards and fruit stands", "bicycle shop", "weather station", "museum visits", "video game arcade",
          "gardening club", "bus routes", "coin and sticker collections", "restaurant orders", "factory production",
          "swimming pool and gym", "photography club", "recycling drive", "bookstore sales", "zoo and aquarium",
          "marching band and parade", "tool shed and workshop", "candy shop", "village market"]
NOUNS = ("marbles ribbons lanterns pencils tickets cookies seeds shells bricks balloons postcards crayons apples "
         "buttons stamps beads kites jars towels coins cards puzzles trophies tiles bottles flags seats pies "
         "oranges notebooks helmets candles blankets trays cups stickers rocks leaves feathers medals nails "
         "shirts hats magnets planks carrots pumpkins eggs batteries maps tents lamps bowls spoons scarves "
         "trading-cards guitar-picks paint-tubes buses boats bikes lockers shelves crates barrels").split()
STYLES = ["start with the question-giving context then ask the question last",
          "put a time-order story (first, then, later) before the question",
          "state a rate or per-unit amount (each box holds, every row has) then ask for a total",
          "describe a comparison (more than / fewer than / twice as many) before the question",
          "describe splitting equally among groups, then ask a follow-up total or remainder-free share",
          "describe buying and selling or spending and earning",
          "describe a collection that grows, then shrinks",
          "ask the question in the middle-stated form 'How many ... in all?' / 'How much ... left?' / 'How much ... altogether?'"]
NAMES = "Mira Tobin Lena Oskar Priya Jonas Alba Kenji Rosa Dmitri Nia Felix Ines Caleb Yuna Marek Sade Hugo Tamsin Rafi Odalys Bruno Keiko Anselm".split()

SYSTEM = ("You write arithmetic word-problem TEMPLATES for a training corpus. You never compute final numeric answers; "
          "code does that later. Output only a JSON array, no prose, no code fences.")


def build_prompt(seed, n=20):
    r = random.Random(seed)
    topic = TOPICS[seed % len(TOPICS)]
    mix = [1, 2, 3, 4]
    w = [r.randint(2, 6) for _ in mix]
    tot = sum(w)
    counts = [max(1, round(n * x / tot)) for x in w]
    counts[-1] += n - sum(counts)
    nouns = ", ".join(r.sample(NOUNS, 6))
    names = ", ".join(r.sample(NAMES, 8))
    styles = r.sample(STYLES, 3)
    return f"""Write {n} different word-problem templates. Topic: "{topic}" (set "topic" to exactly "{topic.replace(' ', '_')}").
Step-count mix for this batch: {counts[0]} templates with 1 step, {counts[1]} with 2 steps, {counts[2]} with 3 steps, {counts[3]} with 4 steps.
Seed {seed}. Try to feature some of these objects: {nouns}. Possible first names (fictional only, use any others you like): {names}.
Wording styles to spread across the batch: {'; '.join(styles)}. Vary the setting, sentence order, vocabulary and the form of the question; do not reuse a sentence frame between templates.

Each template is a JSON object:
{{"text": "...{{a}}...{{b}}... question?", "slots": {{"a": [lo, hi], "b": [lo, hi]}}, "divisible": [["a","b"]], "answer": "expr over slots", "steps": ["expr","expr"], "n_steps": 2, "topic": "...", "unit": "word"}}

Rules (templates violating them are discarded):
- text: 1-4 sentences, fictional first names only, no distractor facts, every number is a slot written {{name}} (lowercase letters); NO digits anywhere else in the text (write 'twice', 'half', 'a dozen' as words only if the expression uses the right constant). It must end with a question mark and use every slot. Make the question unambiguous with exactly one integer answer.
- slots: integer ranges [lo, hi] with lo >= 2 and hi <= 5000 (keep answers well under 100000); realistic for the setting.
- answer and steps use only + - * and // (exact integer division) on slot names, small integer constants (0-1000), and in steps the previous results s1, s2, s3.
- steps: an ordered list of n_steps strings; EACH step is exactly ONE binary operation whose operands are slots, constants, or earlier results (like "a + b", "s1 - c", "s2 * 3"). The last step's value must equal the answer expression. Every slot must appear in some step and every s_k must be used by a later step. n_steps is between 1 and 4 and equals len(steps).
- answer: one expression over slot names that equals the last step's value (e.g. "(a + b) - c").
- Division: use '//' only when exact. Declare slot pairs ["x","y"] in "divisible" meaning x is always a multiple of y (then x // y is exact); sample x as a multiple of y automatically. Such x range must be wide enough to contain multiples of y. Intermediates (s1 // c) must be exact too, so prefer divisible slot pairs.
- All values and intermediates must stay nonnegative integers (subtract only when the first operand is larger: make ranges guarantee it, e.g. subtracted slot range is entirely below the starting slot range).
- "unit": the singular/plural noun counted by the answer.
Return the JSON array only."""


class Spend:
    def __init__(self, path, budget):
        self.path, self.budget = path, budget
        self.lock = threading.Lock()
        self.inp = self.out = self.calls = 0
        self.reserved = 0.0
        if os.path.exists(path):
            d = json.load(open(path))
            self.inp, self.out, self.calls = d["input_tokens"], d["output_tokens"], d["calls"]

    @property
    def usd(self):
        return self.inp * PRICE_IN / 1e6 + self.out * PRICE_OUT / 1e6

    def try_reserve(self):
        with self.lock:
            if self.usd + self.reserved + RESERVE > self.budget:
                return False
            self.reserved += RESERVE
            return True

    def settle(self, usage):
        with self.lock:
            self.reserved -= RESERVE
            if usage:
                self.inp += usage.get("input_tokens", 0)
                self.out += usage.get("output_tokens", 0)
                self.calls += 1
                json.dump({"input_tokens": self.inp, "output_tokens": self.out, "calls": self.calls,
                           "usd": round(self.usd, 4), "model": MODEL, "price_in_per_m": PRICE_IN,
                           "price_out_per_m": PRICE_OUT}, open(self.path, "w"))


def parse_array(text):
    s = text.find("[")
    if s < 0:
        return []
    dec, i, out = json.JSONDecoder(), s + 1, []
    while True:
        while i < len(text) and text[i] in " \n\r\t,":
            i += 1
        if i >= len(text) or text[i] != "{":
            break
        try:
            obj, i = dec.raw_decode(text, i)
        except json.JSONDecodeError:
            break  # truncated tail
        out.append(obj)
    return out


def call_api(prompt, key, temperature=1.0, system=SYSTEM):
    body = {"model": MODEL, "max_tokens": MAX_TOKENS, "temperature": temperature, "system": system,
            "messages": [{"role": "user", "content": prompt}]}
    hdr = {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
    err = None
    for attempt in range(6):
        try:
            r = requests.post(URL, headers=hdr, json=body, timeout=300)
            if r.status_code == 200:
                return r.json()
            err = "http %d" % r.status_code
            if r.status_code in (400, 401, 403, 404):
                if r.status_code == 400 and "temperature" in r.text and "temperature" in body:
                    body.pop("temperature")
                    continue
                raise RuntimeError(err + " " + r.text[:200])
        except requests.RequestException as e:
            err = type(e).__name__
        time.sleep(min(60, 2 ** attempt + random.random()))
    raise RuntimeError("giving up: " + str(err))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--calls", type=int, required=True)
    ap.add_argument("--start-seed", type=int, default=None)
    ap.add_argument("--budget", type=float, default=25.0)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--target", type=int, default=2600)
    ap.add_argument("--per-call", type=int, default=20)
    a = ap.parse_args()
    key = os.environ["LEARNER_ANTHROPIC_API_KEY"]
    os.makedirs(a.out, exist_ok=True)
    sp = Spend(os.path.join(a.out, "spend.json"), a.budget)
    cpath, rpath = os.path.join(a.out, "candidates.jsonl"), os.path.join(a.out, "raw_calls.jsonl")
    seed0 = a.start_seed
    if seed0 is None:
        seed0 = sum(1 for _ in open(rpath)) if os.path.exists(rpath) else 0
    wl = threading.Lock()
    acc = core.Acceptor(load_old())
    n_cand = 0
    if os.path.exists(cpath):
        for line in open(cpath):
            acc.add(json.loads(line)["t"])
            n_cand += 1
    stop = threading.Event()

    def work(seed):
        if stop.is_set() or not sp.try_reserve():
            return seed, None, "skipped"
        usage = None
        try:
            resp = call_api(build_prompt(seed, a.per_call), key)
            usage = resp.get("usage")
            text = "".join(b.get("text", "") for b in resp.get("content", []) if b.get("type") == "text")
            return seed, (resp, text), None
        except Exception as e:
            return seed, None, str(e)[:200]
        finally:
            sp.settle(usage)

    done = 0
    with ThreadPoolExecutor(a.workers) as ex:
        futs = [ex.submit(work, seed0 + i) for i in range(a.calls)]
        for f in as_completed(futs):
            seed, res, err = f.result()
            if res is None:
                print("seed", seed, err, flush=True)
                continue
            resp, text = res
            items = parse_array(text)
            with wl:
                with open(rpath, "a") as rf:
                    rf.write(json.dumps({"seed": seed, "stop": resp.get("stop_reason"), "usage": resp.get("usage"),
                                         "n": len(items)}) + "\n")
                with open(cpath, "a") as cf:
                    for it in items:
                        cf.write(json.dumps({"seed": seed, "t": it}) + "\n")
                        acc.add(it)
            done += 1
            print("seed %d parsed %d accepted_total %d spend $%.2f" % (seed, len(items), len(acc.accepted), sp.usd), flush=True)
            if len(acc.accepted) >= a.target:
                stop.set()
    print("done calls=%d accepted=%d spend=$%.2f rej=%s" % (done, len(acc.accepted), sp.usd, acc.rejections))


def load_old():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    p = os.path.join(root, "artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/QUESTION-COUNT-PACKET-v1.jsonl")
    return [json.loads(l)["question"] for l in open(p)]


if __name__ == "__main__":
    main()
