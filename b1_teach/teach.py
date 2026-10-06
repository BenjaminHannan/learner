"""B1 TEACH: LFM2.5-1.2B-Instruct writes practice items and answers them; a self-check filter and an overlap guard decide what is kept.

Spec: design/thinker-first-split-2026-10-05.md section 6 (Test B1, "B1 data spec"). Nothing else writes training rows.

Stages (resumable; every stage appends to jsonl files under --out and skips ids already there):
  write   -> out/writes_r{R}.jsonl   (teacher writes passage, paraphrase, short question + answer, yes/no question; temp 0.9)
  answer  -> out/answers_r{R}.jsonl  (teacher answers each question from the passage and again from the paraphrase; greedy)
  filter  -> out/teach_200k.jsonl + out/teach_report.json  (self-check + overlap guard + yes/no balance + quota per kind)
  all     -> rounds of write+answer until every kind has its quota, then filter.

A kept ROW is one (passage, paraphrase, question, answer) item with a single question, the same flat schema gen_control.py writes.
Per kind the quota is 1667 short-answer rows + 1667 yes/no rows (834 Yes, 833 No) = 3334 -> 200,004, trimmed to 200,000.
"""
import argparse, json, math, os, random, re, sys, time, unicodedata
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_english as GE
from kinds import KINDS, SPARES

MODEL, REVISION = "LiquidAI/LFM2.5-1.2B-Instruct", "0f604ada3f766f9f257460c4c9f0b5d6f69d431b"
TOTAL = 200000

# ---------------------------------------------------------------- overlap guard (spec: dropped on any hit, counted per kind)
BAD_Q = ["how many", "how much", "where", "why", "when", "what time", "which way", "how long", "come from", "use to", "used for",
         "what for", "cost", "price", "pay", "said", "say", "tell", "told", "asked"]
WEATHER = set("rain rains rained raining rainy snow snows snowed snowing snowy sun sunny sunshine sunlight wind winds windy cloud clouds "
              "cloudy storm storms stormy fog foggy hot hotter cold colder".split())
ATTR_Q = [r"\bwhat colou?rs?\b", r"\bwhich colou?rs?\b", r"\bhow (big|large|small|tall|wide|heavy)\b", r"\bwhat (shape|size|material)\b",
          r"\bmade (of|from|out of)\b", r"\bwhat is it made\b", r"\bwhat colou?r\b"]
# pure function words that sit in the R3/R5/R6 answer list ("at the park", "from the shop"); not content answers, so not blocked
EXEMPT = set("at for from is it i you be will may might can were up down onto during because against along behind near maybe according".split())
ARTICLES = {"the", "a", "an"}


def norm(s):
    s = unicodedata.normalize("NFC", s).lower().replace("’", "'").replace("‘", "'").strip()
    return re.sub(r"[.!?,;:]+$", "", re.sub(r"\s+", " ", s)).strip()


def toks(s):
    return re.findall(r"[a-z0-9$']+", norm(s).replace("-", " "))


BLOCK = None


def blocklist():
    global BLOCK
    if BLOCK is None:
        BLOCK = {w for w in GE.fresh_blocklist(GE.BLOCK_R6) if w not in EXEMPT}
    return BLOCK


def ascii_clean(t):
    return t.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"').replace("\u2013", "-").replace("\u2014", "-")


def contract_ok(passage, para, q, canon):
    """Student-side contract (custom reader/talker thread): ASCII, len(panel) + 1 + len(question) <= 208, answer <= 32 chars."""
    if not all(t.isascii() for t in (passage, para, q, canon)):
        return False
    return max(len(passage), len(para)) + 1 + len(q) <= 208 and len(canon) <= 32


def guard_hits(passage, para, q, ans):
    """-> list of reasons this row overlaps the 12 held-out kinds (empty = clean)."""
    hits, B = [], blocklist()
    qn = " " + " ".join(toks(q)) + " "
    if any(f" {p} " in qn for p in BAD_Q):
        hits.append("question_word")
    if (WEATHER & set(toks(passage + " " + para + " " + q))):
        hits.append("weather")
    if any(re.search(p, norm(q)) for p in ATTR_Q):
        hits.append("attribute_question")
    caps = {w.lower() for t in (passage, para, q) for w in re.findall(r"[A-Z][a-z]+", t)}      # names (and sentence starts)
    if caps & B:
        hits.append("blocked_name")
    ans_words = {w.replace("'s", "") for w in toks(ans)} - ARTICLES - {"yes", "no"}
    if ans_words & B:
        hits.append("blocked_answer_word")
    return hits


# ---------------------------------------------------------------- prompts
FIRST = """Ada Ben Cal Dina Eli Fay Gus Hana Ivan Jade Kai Lena Milo Nora Omar Pia Quin Rosa Sami Tara Uma Vera Wade Xena Yuri Zoe
Alma Boris Cleo Dmitri Elsa Felix Greta Hugo Ines Jonas Katya Leo Maya Nico Olga Pavel Rita Sven Tilly Ursa Viktor Wanda Yara Zeke
Aldo Bea Cyrus Daisy Emil Flora Gideon Hattie Isaac Joan Kofi Lila Marcus Nadia Oscar Petra Ravi Sasha Theo Una Vince Willa Yosef Zara
Abel Brynn Caleb Dora Ezra Freya Glen Hilda Ilya Juno Kirk Lotte Mateo Nell Orla Perry Reza Sunny Tomas Ulla Vlad Winnie Yusuf Zelda
Ansel Bettina Colm Delia Enzo Fenella Gareth Honor Idris Jocelyn Kasper Lucia Magnus Nuala Orson Philippa Rufus Sybil Tobias Valeria""".split()
THINGS = """kite drum bell clock ring badge card map letter parcel bag scarf glove hat jacket blanket pillow rug chair bench shelf crate
trunk marker ruler notebook folder lantern hammer wrench ladder shovel rake hose pot tray vase pitcher jug apple pear lemon melon
onion loaf cookie muffin pie puzzle doll ball marble whistle compass mirror ribbon needle statue globe medal trophy camera radio
violin guitar towel sponge soap pumpkin turnip peach plum cherry walnut raisin tractor wagon sled canoe raft balloon rocket garden
bridge fountain gate fence tower castle cave meadow orchard pond harbor village museum library theater cabin tunnel lighthouse
puppy kitten pony goat sheep hen rabbit parrot turtle squirrel owl fox beetle goldfish""".split()

WRITER = """You write practice items for a children's reading test. Each item has a one-sentence passage, a paraphrase of it, one short-answer question and one yes/no question.

Kind of item: {desc}.

Write exactly these six lines and nothing else:
PASSAGE: <one plain sentence>
PARAPHRASE: <the same facts in different words or word order>
QUESTION: <a question whose answer is a short phrase copied from the passage>
ANSWER: <that short phrase>
YESNO: <a yes/no question about the passage>
YESNO_ANSWER: <Yes or No>

Rules:
- The passage is one sentence of 8 to 22 words, in simple common words, with only the facts it states.
- The paraphrase keeps every fact and adds none. The short answer must appear word for word in the paraphrase too.
- The short answer is 1 to 5 words that appear in the passage.
- The yes/no answer must be {yn}, according to the passage.
- Do not mention weather. Start the short-answer question with Who, What, Which or Whose (never Where, When, Why or How).
- Use the name {names} and mention a {thing} somewhere.

{examples}
Now write a new item of this kind. It must be different from the examples."""


def example_block(ex):
    out = []
    for i, (p, pa, q, a, yq, ya) in enumerate(ex, 1):
        out.append(f"Example {i}\nPASSAGE: {p}\nPARAPHRASE: {pa}\nQUESTION: {q}\nANSWER: {a}\nYESNO: {yq}\nYESNO_ANSWER: {ya}")
    return "\n\n".join(out) + "\n"


def writer_messages(kind, desc, ex, rng):
    names = rng.sample(NAMES(), 2)
    yn = rng.choice(["Yes", "No"])
    txt = WRITER.format(desc=desc, yn=yn, names=f"{names[0]} (and the name {names[1]} if a second person is needed)", thing=rng.choice(THINGS), examples=example_block(ex))
    return [{"role": "user", "content": txt}], yn


_names = None


def NAMES():
    global _names
    if _names is None:
        B = blocklist()
        _names = [n for n in FIRST if n.lower() not in B]
    return _names


SUFFIX = {"short": "\nAnswer with a short phrase only.", "yn": "\nAnswer Yes or No only."}
# fixed shots (hand-written, same in every call): the answer is the fewest words copied from the text
SHOTS = {"short": [("Mara carried the heavy basket to the market.", "What did Mara carry?", "the heavy basket"),
                   ("The tall boy near the gate waved at Pim.", "Who waved at Pim?", "the tall boy"),
                   ("Wes put the green book on the top shelf.", "What did Wes put on the shelf?", "the green book")],
         "yn": [("Lila fed the goats before she milked the cow.", "Did Lila milk the cow first?", "No"),
                ("Ross wore a long scarf to the fair.", "Did Ross wear a scarf?", "Yes")]}


def answer_messages(text, question, kind):
    msgs = []
    for t, q, a in SHOTS[kind]:
        msgs += [{"role": "user", "content": f"{t}\n{q}{SUFFIX[kind]}"}, {"role": "assistant", "content": a}]
    return msgs + [{"role": "user", "content": f"{text}\n{question}{SUFFIX[kind]}"}]


FIELDS = ["PASSAGE", "PARAPHRASE", "QUESTION", "ANSWER", "YESNO", "YESNO_ANSWER"]


def parse_item(txt):
    txt = txt.strip()
    if not re.match(r"\**PASSAGE", txt):
        txt = "PASSAGE: " + txt            # the model usually continues after an implied "PASSAGE:" label
    d = {}
    parts = re.split(r"\**\b(PASSAGE|PARAPHRASE|QUESTION|ANSWER|YESNO_ANSWER|YESNO)\b\**\s*:", txt)
    for k, v in zip(parts[1::2], parts[2::2]):
        if k not in d:
            d[k] = v.strip().strip("*").strip()
    if not all(k in d for k in FIELDS):
        return None
    if not (d["QUESTION"].endswith("?") and d["YESNO"].endswith("?")):
        return None
    if not (4 <= len(d["PASSAGE"].split()) <= 30 and 4 <= len(d["PARAPHRASE"].split()) <= 34):
        return None
    if norm(d["YESNO_ANSWER"]) not in ("yes", "no"):
        return None
    return d


# ---------------------------------------------------------------- generation backend
class Backend:
    """chat(list of message-lists, max_new, temperature) -> list of strings. vLLM if installed, else HF transformers (bf16)."""

    def __init__(self, kind="auto", batch=128, gpu_util=0.35):
        self.batch = batch
        if kind in ("auto", "vllm"):
            try:
                from vllm import LLM
                self.vllm = LLM(MODEL, revision=REVISION, dtype="bfloat16", max_model_len=2048, gpu_memory_utilization=gpu_util, enable_prefix_caching=True)
                self.kind = "vllm"; return
            except Exception as e:
                if kind == "vllm":
                    raise
                print("vllm not usable, falling back to transformers:", repr(e)[:100], flush=True)
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.torch = torch
        self.dev = "cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu")
        dt = torch.bfloat16 if self.dev != "cpu" else torch.float32
        self.tok = AutoTokenizer.from_pretrained(MODEL, revision=REVISION, padding_side="left")
        self.lm = AutoModelForCausalLM.from_pretrained(MODEL, revision=REVISION, dtype=dt).to(self.dev).eval()
        self.kind = "hf"; self.ntok = 0

    def chat(self, msgs, max_new, temperature=0.0, top_p=0.95, on_batch=None):
        if self.kind == "vllm":
            from vllm import SamplingParams
            sp = SamplingParams(temperature=temperature, top_p=top_p if temperature else 1.0, max_tokens=max_new)
            outs = self.vllm.chat(msgs, sp, use_tqdm=False)
            res = [o.outputs[0].text for o in outs]
            if on_batch:
                on_batch(list(range(len(res))), res)
            return res
        torch = self.torch
        prompts = [self.tok.apply_chat_template(m, add_generation_prompt=True, tokenize=False) for m in msgs]
        order = sorted(range(len(prompts)), key=lambda i: len(prompts[i]))
        res = [None] * len(prompts)
        for s in range(0, len(order), self.batch):
            idx = order[s:s + self.batch]
            enc = self.tok([prompts[i] for i in idx], return_tensors="pt", padding=True, add_special_tokens=False).to(self.dev)
            with torch.inference_mode():
                g = self.lm.generate(**enc, max_new_tokens=max_new, do_sample=temperature > 0, temperature=temperature or None,
                                     top_p=top_p if temperature else None, pad_token_id=self.tok.pad_token_id)
            outs = self.tok.batch_decode(g[:, enc["input_ids"].shape[1]:], skip_special_tokens=True)
            self.ntok += int((g[:, enc["input_ids"].shape[1]:] != self.tok.pad_token_id).sum())
            for i, o in zip(idx, outs):
                res[i] = o
            if on_batch:
                on_batch(idx, [res[i] for i in idx])
        return res


# ---------------------------------------------------------------- stages
def read_jsonl(p):
    return [json.loads(l) for l in open(p)] if Path(p).exists() else []


def append_jsonl(p, rows):
    with open(p, "a") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def stage_write(be, out, R, per_kind, kinds, seed):
    p = out / f"writes_r{R}.jsonl"
    done = {r["id"] for r in read_jsonl(p)}
    jobs = []
    for name, desc, ex in kinds:
        for i in range(per_kind[name]):
            iid = f"{name}-r{R}-{i}"
            if iid in done:
                continue
            msgs, yn = writer_messages(name, desc, ex, random.Random(f"{seed}|{iid}"))
            jobs.append((iid, name, yn, msgs))
    print(f"write r{R}: {len(jobs)} to do ({len(done)} done)", flush=True)
    CH = 4096 if be.kind == "hf" else 20000                     # chunk so progress is saved
    t0 = time.time()
    for s in range(0, len(jobs), CH):
        ch = jobs[s:s + CH]
        txt = be.chat([j[3] for j in ch], max_new=130, temperature=0.9)
        append_jsonl(p, [{"id": j[0], "kind": j[1], "yn_target": j[2], "raw": t} for j, t in zip(ch, txt)])
        print(f"  wrote {s + len(ch)}/{len(jobs)} {time.time() - t0:.0f}s", flush=True)


def stage_answer(be, out, R):
    wp, ap = out / f"writes_r{R}.jsonl", out / f"answers_r{R}.jsonl"
    done = {r["id"] for r in read_jsonl(ap)}
    todo = []
    for w in read_jsonl(wp):
        if w["id"] in done:
            continue
        it = parse_item(w["raw"])
        if it is None:
            append_jsonl(ap, [{"id": w["id"], "kind": w["kind"], "parsed": False, "raw": w["raw"]}]); continue
        todo.append((w, it))
    print(f"answer r{R}: {len(todo)} items to answer", flush=True)
    CH = 2048 if be.kind == "hf" else 20000
    t0 = time.time()
    for s in range(0, len(todo), CH):
        ch = todo[s:s + CH]
        msgs = []
        for w, it in ch:
            for key in ("PASSAGE", "PARAPHRASE"):
                for qk, sk in (("QUESTION", "short"), ("YESNO", "yn")):
                    msgs.append(answer_messages(it[key], it[qk], sk))
        outs = be.chat(msgs, max_new=14, temperature=0.0)
        rows = []
        for k, (w, it) in enumerate(ch):
            o = [x.strip().splitlines()[0].strip() if x.strip() else "" for x in outs[4 * k:4 * k + 4]]
            rows.append({"id": w["id"], "kind": w["kind"], "parsed": True, "yn_target": w["yn_target"], "item": it,
                         "ans": {"short_passage": o[0], "yn_passage": o[1], "short_paraphrase": o[2], "yn_paraphrase": o[3]}})
        append_jsonl(ap, rows)
        print(f"  answered {s + len(ch)}/{len(todo)} {time.time() - t0:.0f}s", flush=True)


def contains(hay, needle):
    h, n = toks(hay), toks(needle)
    while n and n[0] in ARTICLES:
        n = n[1:]
    return bool(n) and any(h[i:i + len(n)] == n for i in range(len(h) - len(n) + 1))


def judge(a):
    """One answered item -> (list of candidate rows, list of (reason, 1) drop reasons)."""
    it, an, kind = ({k: ascii_clean(v) for k, v in a["item"].items()}, {k: ascii_clean(v) for k, v in a["ans"].items()}, a["kind"])
    rows, drops = [], []
    for typ, qk, ka, kb in (("short_answer", "QUESTION", "short_passage", "short_paraphrase"), ("yes_no", "YESNO", "yn_passage", "yn_paraphrase")):
        q, x, y = it[qk], norm(an[ka]), norm(an[kb])
        if not x or x != y:
            drops.append(typ + ":answers_differ"); continue
        if typ == "yes_no":
            if x not in ("yes", "no"):
                drops.append(typ + ":not_yes_no"); continue
            if x != norm(it["YESNO_ANSWER"]):
                drops.append(typ + ":writer_label_differs"); continue     # extra self-check: also agrees with the writer's own label
            canon, acc = x.capitalize(), [x.capitalize()]
        else:
            if x in ("yes", "no") or len(x.split()) > 8:
                drops.append(typ + ":bad_short"); continue
            if not contains(it["PASSAGE"], x):
                drops.append(typ + ":answer_not_in_passage"); continue
            canon = an[ka].strip().rstrip(".")
            core = " ".join(t for i, t in enumerate(canon.split()) if not (i == 0 and t.lower() in ARTICLES))
            acc = list(dict.fromkeys([canon, core]))
        if not contract_ok(it["PASSAGE"], it["PARAPHRASE"], q, canon):
            drops.append(typ + ":contract"); continue
        hits = guard_hits(it["PASSAGE"], it["PARAPHRASE"], q, canon)
        drops.append("selfpass")
        if hits:
            drops += [f"{typ}:guard:{h}" for h in hits] + ["guard_row"]; continue
        rows.append({"id": a["id"] + ("-s" if typ == "short_answer" else "-y"), "kind": kind, "source_text": it["PASSAGE"], "paraphrase": it["PARAPHRASE"],
                     "question": q, "type": typ, "canonical_answer": canon, "accepted_answers": acc})
    return rows, drops


def collect(out, kinds_names):
    """Judge every answered item in every round. -> (candidates by kind, stats by kind)."""
    cands, stats, seen = defaultdict(list), defaultdict(Counter), set()
    for ap in sorted(out.glob("answers_r*.jsonl")):
        for a in read_jsonl(ap):
            k = a["kind"]
            stats[k]["written"] += 1
            if not a["parsed"]:
                stats[k]["unparsed"] += 1; continue
            rows, drops = judge(a)
            for d in drops:
                stats[k][d if d in ("selfpass", "guard_row") else "drop:" + d] += 1
            for r in rows:
                key = (norm(r["source_text"]), norm(r["question"]))
                if key in seen:
                    stats[k]["drop:duplicate"] += 1; continue
                seen.add(key); cands[k].append(r)
    return cands, stats


def quota_state(cands):
    st = {}
    for name, c in cands.items():
        st[name] = Counter(r["type"] if r["type"] == "short_answer" else r["canonical_answer"] for r in c)
    return st


QUOTA = {"short_answer": 1667, "Yes": 834, "No": 833}


def unmet(cands, names):
    out = {}
    for n in names:
        c = Counter(r["type"] if r["type"] == "short_answer" else r["canonical_answer"] for r in cands.get(n, []))
        out[n] = {k: max(0, v - c[k]) for k, v in QUOTA.items()}
    return out


def stage_filter(out, kinds_names, spares_used):
    cands, stats = collect(out, kinds_names)
    final, report = [], {"kinds": {}, "spares_used": spares_used}
    rng = random.Random(20261005)
    for n in kinds_names:
        c = cands.get(n, [])
        rng.shuffle(c)
        take = []
        cnt = Counter()
        for r in c:
            k = r["type"] if r["type"] == "short_answer" else r["canonical_answer"]
            if cnt[k] < QUOTA[k]:
                cnt[k] += 1; take.append(r)
        final += take
        s = stats[n]
        report["kinds"][n] = {"written": s["written"], "unparsed": s["unparsed"], "candidates": len(c), "kept": len(take), "kept_by_type": dict(cnt),
                              "drops": {k[5:]: v for k, v in sorted(s.items()) if k.startswith("drop:")}}
    rng.shuffle(final)
    final = final[:TOTAL]
    with open(out / "teach_200k.jsonl", "w") as f:
        for r in final:
            f.write(json.dumps(r) + "\n")
    report["total_kept"] = len(final)
    report["type_counts"] = dict(Counter(r["type"] if r["type"] == "short_answer" else r["canonical_answer"] for r in final))
    report["teacher"] = {"model": MODEL, "revision": REVISION}
    (out / "teach_report.json").write_text(json.dumps(report, indent=1))
    print("kept", len(final), report["type_counts"], flush=True)
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--stage", choices=["write", "answer", "filter", "all"], default="all")
    ap.add_argument("--round", type=int, default=0)
    ap.add_argument("--per-kind", type=int, default=0, help="items to write per kind in the first round (0 = auto)")
    ap.add_argument("--max-rounds", type=int, default=8)
    ap.add_argument("--only", default="", help="comma list of kind names (smoke test)")
    ap.add_argument("--backend", default="auto")
    ap.add_argument("--batch", type=int, default=128)
    ap.add_argument("--gpu-util", type=float, default=0.35)
    ap.add_argument("--seed", type=int, default=5002)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    spares_used = json.loads((out / "spares.json").read_text()) if (out / "spares.json").exists() else {}
    spare_by = {k[0]: k for k in SPARES}
    kinds = [spare_by[spares_used[k[0]]] if k[0] in spares_used else k for k in KINDS if not a.only or k[0] in a.only.split(",")]
    names = [k[0] for k in kinds]
    if a.stage == "filter":
        stage_filter(out, names, spares_used); return
    be = Backend(a.backend, a.batch, a.gpu_util)
    print("backend", be.kind, flush=True)
    if a.stage in ("write", "answer"):
        R = a.round
        if a.stage == "write":
            stage_write(be, out, R, {n: a.per_kind or 1500 for n in names}, kinds, a.seed)
        else:
            stage_answer(be, out, R)
        return
    for R in range(a.max_rounds):
        cands, stats = collect(out, names)
        if R == 1 and not a.only:        # after round 0: a kind losing more than half its self-check-passing rows to the guard is swapped for a spare
            free = [k for k in SPARES if k[0] not in spares_used.values()]
            for k in list(kinds):
                st = stats[k[0]]
                if st["selfpass"] >= 100 and st["guard_row"] > 0.5 * st["selfpass"] and free and k[0] in {x[0] for x in KINDS}:
                    sp = free.pop(0); spares_used[k[0]] = sp[0]
                    kinds[kinds.index(k)] = sp; names = [x[0] for x in kinds]
                    print(f"SPARE: {k[0]} lost {st['guard_row']}/{st['selfpass']} to the guard -> {sp[0]}", flush=True)
            (out / "spares.json").write_text(json.dumps(spares_used))
            cands, stats = collect(out, names)
        need = unmet(cands, names)
        todo = {n: sum(need[n].values()) for n in names}
        if not any(todo.values()):
            break
        # items needed ~ unmet short-answer rows / observed keep rate (first round: 2000 per kind)
        per = {}
        for n in names:
            if todo[n] == 0:
                per[n] = 0; continue
            per[n] = a.per_kind if (R == 0 and a.per_kind) else (2000 if R == 0 else min(1500, max(150, int(todo[n] * 0.7))))
        stage_write(be, out, R, per, kinds, a.seed)
        stage_answer(be, out, R)
    stage_filter(out, names, spares_used)


if __name__ == "__main__":
    main()
