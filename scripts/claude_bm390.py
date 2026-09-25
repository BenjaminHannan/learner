#!/usr/bin/env python3
"""bm-390: Premonition 0.1 against plain same-size models on public benchmarks
(public-benchmarks thread, 2026-09-25; plan design/v3/30-modes/390-public-bench-plan.md,
marks artifacts/claude-bm390-20260925/PASSMARKS.md).

New file only. It never edits agent code. Public data is downloaded at pinned revisions and
checked against artifacts/claude-bm390-20260925/data-manifest.json; nothing here was tuned on it.

Subcommands
  fetch    --data DIR
      Download LoCoMo (snap-research/locomo @3eb6f2c), MMLU-Redux-2.0 (57 subjects) and the GSM8K
      test split, check every sha256, and write the two seeded general samples (seed 390, 300 each;
      MMLU-Redux keeps only rows whose error_type is "ok"). Prints counts only.
  locomo   --data DIR --arm SPEC --name NAME --out DIR [--convs ids] [--limit-q N]
  general  --data DIR --task mmlu|gsm8k --arm SPEC --name NAME --out DIR [--limit N]

Arm SPEC
  agent:<module:function>  a Premonition-style agent, built as function(state_dir, args) exactly like the
                           336 runner does (e.g. agent:claude_e2e330c:build_330c with --model READER
                           --gen-model BASE). LoCoMo: it reads every turn in order as a chat turn, sleeps
                           once after each session (the 336 runner's end_day), then each question is asked
                           in a fresh copy of the state it had after reading (questions never see each other).
                           General tests: a fresh empty state per question.
  plain:<model_dir>        a plain chat model, thinking off, greedy, the whole conversation in one prompt
                           (the LoCoMo repo's own chat-template baseline, task_eval/hf_llm_utils.py run_llama).
  closed:<model_dir>       the same plain model with no conversation at all (contamination check).
  bm25:<model_dir>         the same plain model given only the 10 turns BM25 ranks highest for the question
                           (the "is it just a search engine?" baseline).

Text every arm sees (LoCoMo): the repo's CONV_START_PROMPT, then for each session "DATE: <date>" and
"CONVERSATION:" and each turn as '<speaker> said, "<text>"' plus '\\n and shared <caption>.' when the turn
has a photo caption, then the repo's QA_PROMPT with the question. Category 2 questions get the repo's date
hint, category 5 questions the repo's (a)/(b) choice with "No information available" as one option (order
fixed per question id by seed 390). Plain arms get this as one prompt; agents get the same strings, one
turn at a time. Deviations from the repo's baseline code (all registered): greedy decoding instead of
temperature 0.4 sampling, sessions in time order (the repo's builder puts the newest session first),
speaker order from speaker_a / speaker_b (the repo uses an unordered set), category 5 uses the
adversarial_answer field (the current data file has no answer field for 444 of the 446 category 5 items).

Output: <out>/<bench>_<name>[.part<N>].jsonl, one row per question: qid, category (LoCoMo), reply, ms, plus
arm details. LoCoMo agent arms also write locomo_<name>_reading[.part<N>].jsonl (one row per conversation) and,
with --also-bare, locomo_<name>_bare[.part<N>].jsonl: the same questions without the repo's "write a short
answer" wrapper, asked from the same saved state (report only; never a headline number).
Question and gold text are never copied into outputs; the scorer joins on qid.
"""
from __future__ import annotations

import argparse
import copy
import gc
import hashlib
import importlib
import json
import math
import os
import random
import re
import shutil
import sys
import tempfile
import time
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
if os.name == "nt":
    sys.path.insert(0, str(SCRIPTS / "winshim"))

EXP = ROOT / "artifacts" / "claude-bm390-20260925"
MANIFEST = EXP / "data-manifest.json"
SEED = 390
N_GENERAL = 300

LOCOMO_URL = ("https://raw.githubusercontent.com/snap-research/locomo/"
              "3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376/data/locomo10.json")
MMLU_URL = "https://huggingface.co/datasets/edinburgh-dawg/mmlu-redux-2.0/resolve/{rev}/{subject}/data-00000-of-00001.arrow"
GSM8K_URL = "https://huggingface.co/datasets/openai/gsm8k/resolve/{rev}/main/test-00000-of-00001.parquet"

# ---- LoCoMo repo text, verbatim (task_eval/hf_llm_utils.py @3eb6f2c) ----
CONV_START_PROMPT = ("Below is a conversation between two people: {} and {}. The conversation takes place over "
                     "multiple days and the date of each conversation is wriiten at the beginning of the "
                     "conversation.\n\n")
QA_PROMPT = ("\nBased on the above conversations, write a short answer for the following question in a few "
             "words. Do not write complete and lengthy sentences. Answer with exact words from the "
             "conversations whenever possible.\n\nQuestion: {}\n")
LOCOMO_SYSTEM = ("You are a helpful, respectful and honest assistant whose job is to understand the following "
                 "conversation and answer questions based on the conversation. If you don't know the answer to "
                 "a question, please don't share false information.")
CAT2_SUFFIX = " Use DATE of CONVERSATION to answer with an approximate date."
CAT5_TEMPLATE = " (a) {} (b) {}. Select the correct answer by writing (a) or (b)."
NO_INFO = "No information available"
ANS_TOKENS = 50                       # the repo's ANS_TOKENS_PER_QUES

# ---- fixed here, before any run ----
CLOSED_SYSTEM = "You are a helpful assistant."
CLOSED_PROMPT = "Answer the following question in a few words.\n\nQuestion: {}\n"
BM25_K = 10
GENERAL_SYSTEM = "You are a helpful assistant."
MMLU_PROMPT = ("The following is a multiple choice question about {subject}. Answer with the letter of the "
               "correct option only.\n\n{question}\n{options}\nAnswer:")
GSM8K_PROMPT = ("Solve this math problem. Show brief working, then end with a line of the form "
                "\"The answer is N.\" where N is a number.\n\n{question}")
MAX_NEW = {"mmlu": 16, "gsm8k": 512}


# ======================================================================= data
def _sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _get(url: str, dest: Path, want: str) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists() or _sha(dest) != want:
        for attempt in range(4):
            try:
                urllib.request.urlretrieve(url, dest)
                break
            except Exception:  # noqa: BLE001
                if attempt == 3:
                    raise
                time.sleep(2 ** (attempt + 1))
    got = _sha(dest)
    if got != want:
        raise SystemExit(f"DATA-MISMATCH {dest.name}: sha256 {got} != pinned {want}")


def _read_arrow(path: Path):
    import pyarrow as pa
    with open(path, "rb") as fh:
        return pa.ipc.open_stream(fh).read_all().to_pylist()


def fetch(data: Path) -> None:
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    _get(LOCOMO_URL, data / "locomo10.json", man["locomo10_sha256"])
    for subject, sha in sorted(man["mmlu_redux_files"].items()):
        _get(MMLU_URL.format(rev=man["mmlu_redux_revision"], subject=subject),
             data / "mmlu" / f"{subject}.arrow", sha)
    _get(GSM8K_URL.format(rev=man["gsm8k_revision"]), data / "gsm8k_test.parquet", man["gsm8k_test_sha256"])

    ok = []
    for subject in sorted(man["mmlu_redux_files"]):
        for i, row in enumerate(_read_arrow(data / "mmlu" / f"{subject}.arrow")):
            if row["error_type"] == "ok":
                ok.append({"qid": f"mmlu/{subject}/{i}", "subject": subject, "question": row["question"],
                           "choices": list(row["choices"]), "gold": "ABCD"[int(row["answer"])]})
    mm = random.Random(SEED).sample(ok, N_GENERAL)
    import pyarrow.parquet as pq
    gs = pq.read_table(data / "gsm8k_test.parquet").to_pylist()
    gitems = [{"qid": f"gsm8k/test/{i}", "question": r["question"],
               "gold": r["answer"].split("####")[-1].strip().replace(",", "")} for i, r in enumerate(gs)]
    gg = random.Random(SEED).sample(gitems, N_GENERAL)
    for name, rows in (("mmlu300.jsonl", mm), ("gsm8k300.jsonl", gg)):
        (data / name).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    lc = json.loads((data / "locomo10.json").read_text(encoding="utf-8"))
    cats = Counter(q["category"] for c in lc for q in c["qa"])
    print(json.dumps({"fetch": "OK", "locomo_convs": len(lc), "locomo_qa": sum(cats.values()),
                      "locomo_by_category": dict(sorted(cats.items())), "mmlu_ok_rows": len(ok),
                      "mmlu_sample": len(mm), "gsm8k_rows": len(gitems), "gsm8k_sample": len(gg),
                      "mmlu300_sha256": _sha(data / "mmlu300.jsonl"),
                      "gsm8k300_sha256": _sha(data / "gsm8k300.jsonl")}), flush=True)


# ======================================================================= LoCoMo text
def sessions(item: dict) -> list[tuple[str, list[dict]]]:
    conv = item["conversation"]
    nums = sorted(int(k.split("_")[1]) for k in conv
                  if re.fullmatch(r"session_\d+", k) and isinstance(conv[k], list))
    return [(conv[f"session_{n}_date_time"], conv[f"session_{n}"]) for n in nums]


def turn_text(t: dict) -> str:
    s = t["speaker"] + ' said, "' + t["text"] + '"' + "\n"
    if "blip_caption" in t:
        s += " and shared %s." % t["blip_caption"]
    return s


def start_text(item: dict) -> str:
    conv = item["conversation"]
    return CONV_START_PROMPT.format(conv["speaker_a"], conv["speaker_b"])


def full_context(conv: dict, drop_first: int = 0) -> str:
    """Whole conversation in time order, the repo's per-turn format; drop_first turns removed (only when a
    model's context is too short; counted in the output)."""
    out = start_text(conv)
    seen = 0
    for date, turns in sessions(conv):
        body = ""
        for t in turns:
            seen += 1
            if seen <= drop_first:
                continue
            body += turn_text(t) + "\n"
        if body:
            out += "\nDATE: " + date + "\n" + "CONVERSATION:\n" + body
    return out


def question_text(conv_id: str, idx: int, qa: dict) -> str:
    q = qa["question"]
    if qa["category"] == 2:
        return q + CAT2_SUFFIX
    if qa["category"] == 5:
        adv = qa.get("adversarial_answer", qa.get("answer"))
        if random.Random(f"{SEED}:{conv_id}:{idx}").random() < 0.5:
            return q + CAT5_TEMPLATE.format(NO_INFO, adv)
        return q + CAT5_TEMPLATE.format(adv, NO_INFO)
    return q


def cat5_options(conv_id: str, idx: int, qa: dict) -> dict:
    adv = qa.get("adversarial_answer", qa.get("answer"))
    if random.Random(f"{SEED}:{conv_id}:{idx}").random() < 0.5:
        return {"a": NO_INFO, "b": adv}
    return {"a": adv, "b": NO_INFO}


def load_locomo(data: Path, convs: str) -> list[dict]:
    lc = json.loads((data / "locomo10.json").read_text(encoding="utf-8"))
    want = [x for x in convs.split(",") if x]
    return [c for c in lc if not want or c["sample_id"] in want]


# ======================================================================= plain models
_PLAIN: dict = {}


def plain_model(model_dir: str):
    if model_dir not in _PLAIN:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        tok = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True)
        dev = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.bfloat16 if dev == "cuda" else torch.float32
        model = AutoModelForCausalLM.from_pretrained(model_dir, dtype=dtype, trust_remote_code=True).to(dev).eval()
        cfg = model.config
        ctx = int(getattr(cfg, "max_position_embeddings", 0) or getattr(getattr(cfg, "text_config", cfg),
                                                                       "max_position_embeddings", 32768))
        _PLAIN[model_dir] = (tok, model, dev, ctx)
    return _PLAIN[model_dir]


def _ids(tok, system: str, user: str):
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    return tok.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True, enable_thinking=False,
                                   return_dict=True, return_tensors="pt")


def strip_think(text: str) -> str:
    if "</think>" in text:
        text = text.split("</think>")[-1]
    return text.replace("<think>", "").strip()


def generate(model_dir: str, system: str, user: str, max_new: int) -> tuple[str, int]:
    import torch
    tok, model, dev, _ = plain_model(model_dir)
    enc = _ids(tok, system, user).to(dev)
    n = int(enc["input_ids"].shape[1])
    with torch.no_grad():
        out = model.generate(**enc, max_new_tokens=max_new, do_sample=False,
                             pad_token_id=tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id)
    return strip_think(tok.decode(out[0][n:], skip_special_tokens=True)), n


def fit_context(model_dir: str, conv: dict, qprompt: str) -> tuple[str, int]:
    """Whole conversation if it fits the model's context (with room for the answer), else drop the
    earliest turns until it does. Returns (user text, turns dropped)."""
    tok, _, _, ctx = plain_model(model_dir)
    drop = 0
    total = sum(len(t) for _, t in sessions(conv))
    while True:
        user = full_context(conv, drop) + "\n\n" + qprompt
        n = int(_ids(tok, LOCOMO_SYSTEM, user)["input_ids"].shape[1])
        if n + ANS_TOKENS <= ctx or drop >= total:
            return user, drop
        drop += max(1, int((n + ANS_TOKENS - ctx) / 40))


# ---- BM25 (Okapi, k1 1.5, b 0.75; fixed here) ----
def _toks(s: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", s.lower())


def bm25_context(conv: dict, query: str, k: int = BM25_K) -> str:
    items = []
    for si, (date, turns) in enumerate(sessions(conv)):
        for ti, t in enumerate(turns):
            items.append((si, ti, date, turn_text(t), _toks(t["text"] + " " + t.get("blip_caption", ""))))
    n = len(items)
    avg = sum(len(x[4]) for x in items) / max(1, n)
    df = Counter(w for x in items for w in set(x[4]))
    q = _toks(query)
    scored = []
    for x in items:
        tf = Counter(x[4])
        s = 0.0
        for w in q:
            if w not in tf:
                continue
            idf = math.log(1 + (n - df[w] + 0.5) / (df[w] + 0.5))
            s += idf * tf[w] * 2.5 / (tf[w] + 1.5 * (0.25 + 0.75 * len(x[4]) / avg))
        scored.append((s, x))
    top = sorted(scored, key=lambda z: (-z[0], z[1][0], z[1][1]))[:k]
    top = sorted((x for _, x in top), key=lambda x: (x[0], x[1]))
    out = start_text(conv)
    cur = None
    for si, ti, date, text, _ in top:
        if si != cur:
            out += "\nDATE: " + date + "\n" + "CONVERSATION:\n"
            cur = si
        out += text + "\n"
    return out


# ======================================================================= agents
def resolve_builder(spec: str):
    mod, _, fn = spec.partition(":")
    if not fn:
        raise SystemExit(f"bm390: agent arm {spec!r} must be 'module:function'")
    return getattr(importlib.import_module(mod), fn)


def agent_args(args) -> argparse.Namespace:
    return argparse.Namespace(model=args.model, gen_model=args.gen_model, mouth_model=args.mouth_model,
                              skip_preflight=args.skip_preflight)


def preflight(args) -> None:
    if args.skip_preflight:
        return
    try:
        import fable_self122 as S122
        S122.route122("what is your name?")
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"MISSING-CACHE: the self122 MiniLM router did not load ({exc!r}); nothing was run.")


def locomo_agent(builder, aargs, conv: dict, limit_q: int, rows: list, reading: list,
                 bare_rows: list | None = None) -> None:
    import claude_e2e336_run as R
    cid = conv["sample_id"]
    work = Path(tempfile.mkdtemp(prefix=f"bm390-{cid}-"))
    state, snap = work / "state", work / "snap"
    state.mkdir()
    try:
        agent = builder(str(state), aargs)
        t0 = time.time()
        nturns = checks = 0
        texts = [start_text(conv).strip()]
        sess = sessions(conv)
        for si, (date, turns) in enumerate(sess):
            texts_s = ["DATE: " + date + "\nCONVERSATION:"] + [turn_text(t).rstrip("\n") for t in turns]
            if si == 0:
                texts_s = texts + texts_s
            for text in texts_s:
                reply, _, _ = R.one(agent, text)
                nturns += 1
                checks += int(R.is_confirm(reply))
            R.end_day(agent)                       # one sleep per session (a session is one day)
        tri = R.triples(agent)
        del agent
        gc.collect()
        shutil.copytree(state, snap)
        reading.append({"conv": cid, "turns_fed": nturns, "sessions": len(sess), "sleeps": len(sess),
                        "check_questions_asked": checks, "stored_triples_after_reading":
                        (len(tri) if tri is not None else None), "reading_s": round(time.time() - t0, 1)})
        for i, qa in enumerate(conv["qa"][: limit_q or None]):
            variants = [(rows, QA_PROMPT.format(question_text(cid, i, qa)).strip())]
            if bare_rows is not None:        # report-only: the question without the repo's answer-style wrapper
                variants.append((bare_rows, question_text(cid, i, qa)))
            for sink, text in variants:
                _reset(state, snap)
                agent = builder(str(state), aargs)
                reply, ms, new = R.one(agent, text)
                sink.append({"qid": f"{cid}#{i}", "category": qa["category"], "reply": reply, "ms": round(ms, 1),
                             "question_turn_writes": len(new)})
                del agent
                gc.collect()
        print(f"[bm390] {cid} turns={nturns} questions={min(len(conv['qa']), limit_q or 10**9)}", flush=True)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _reset(state: Path, snap: Path) -> None:
    """Put back the saved after-reading state. Windows cannot delete a file that is still open, so retry
    after garbage collection before giving up with a clear error."""
    for attempt in range(5):
        gc.collect()
        try:
            if state.exists():
                shutil.rmtree(state)
            shutil.copytree(snap, state)
            return
        except OSError as exc:
            if attempt == 4:
                raise SystemExit(f"STATE-RESET-FAILED ({exc!r}): could not restore the saved state; nothing more run.")
            time.sleep(1 + attempt)


def general_agent(builder, aargs, text: str) -> tuple[str, float]:
    import claude_e2e336_run as R
    work = Path(tempfile.mkdtemp(prefix="bm390-gen-"))
    try:
        agent = builder(str(work), aargs)
        reply, ms, _ = R.one(agent, text)
        del agent
        gc.collect()
        return reply, ms
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ======================================================================= runners
def run_locomo(args) -> None:
    kind, _, target = args.arm.partition(":")
    convs = load_locomo(Path(args.data), args.convs)
    rows: list[dict] = []
    reading: list[dict] = []
    bare: list[dict] | None = [] if args.also_bare else None
    if kind == "agent":
        preflight(args)
        builder = resolve_builder(target)
        aargs = agent_args(args)
        for conv in convs:
            locomo_agent(builder, aargs, conv, args.limit_q, rows, reading, bare)
    elif kind in ("plain", "closed", "bm25"):
        for conv in convs:
            cid = conv["sample_id"]
            for i, qa in enumerate(conv["qa"][: args.limit_q or None]):
                qtext = question_text(cid, i, qa)
                t0 = time.time()
                drop = 0
                if kind == "plain":
                    user, drop = fit_context(target, conv, QA_PROMPT.format(qtext))
                    reply, n = generate(target, LOCOMO_SYSTEM, user, ANS_TOKENS)
                elif kind == "bm25":
                    user = bm25_context(conv, qtext) + "\n\n" + QA_PROMPT.format(qtext)
                    reply, n = generate(target, LOCOMO_SYSTEM, user, ANS_TOKENS)
                else:
                    reply, n = generate(target, CLOSED_SYSTEM, CLOSED_PROMPT.format(qtext), ANS_TOKENS)
                rows.append({"qid": f"{cid}#{i}", "category": qa["category"], "reply": reply,
                             "ms": round((time.time() - t0) * 1000, 1), "prompt_tokens": n, "turns_dropped": drop})
            print(f"[bm390] {cid} {kind} questions={min(len(conv['qa']), args.limit_q or 10**9)}", flush=True)
    else:
        raise SystemExit(f"bm390: unknown arm kind {kind!r}")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    _write(out / fname("locomo", args.name, args.part), rows)
    if reading:
        _write(out / fname("locomo", args.name + "_reading", args.part), reading)
    if bare is not None:
        _write(out / fname("locomo", args.name + "_bare", args.part), bare)
    print(f"wrote {fname('locomo', args.name, args.part)} rows={len(rows)} convs={len(convs)}"
          + (f" bare={len(bare)}" if bare is not None else ""), flush=True)


def fname(bench: str, name: str, part: str) -> str:
    return f"{bench}_{name}" + (f".part{part}" if part else "") + ".jsonl"


def _write(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def general_prompt(task: str, item: dict) -> str:
    if task == "mmlu":
        opts = "\n".join(f"{'ABCD'[j]}. {c}" for j, c in enumerate(item["choices"]))
        return MMLU_PROMPT.format(subject=item["subject"].replace("_", " "), question=item["question"], options=opts)
    return GSM8K_PROMPT.format(question=item["question"])


def run_general(args) -> None:
    kind, _, target = args.arm.partition(":")
    items = [json.loads(x) for x in (Path(args.data) / f"{args.task}300.jsonl").read_text(encoding="utf-8").splitlines()
             if x.strip()][: args.limit or None]
    rows = []
    if kind == "agent":
        preflight(args)
        builder = resolve_builder(target)
        aargs = agent_args(args)
    for it in items:
        text = general_prompt(args.task, it)
        if kind == "agent":
            reply, ms = general_agent(builder, aargs, text)
        elif kind == "plain":
            t0 = time.time()
            reply, _ = generate(target, GENERAL_SYSTEM, text, MAX_NEW[args.task])
            ms = (time.time() - t0) * 1000
        else:
            raise SystemExit(f"bm390: general arms are agent or plain, not {kind!r}")
        rows.append({"qid": it["qid"], "reply": reply, "ms": round(ms, 1)})
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    _write(out / fname(args.task, args.name, args.part), rows)
    print(f"wrote {fname(args.task, args.name, args.part)} rows={len(rows)}", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["fetch", "locomo", "general"])
    ap.add_argument("--data", required=True)
    ap.add_argument("--arm", default="")
    ap.add_argument("--name", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--task", default="", choices=["", "mmlu", "gsm8k"])
    ap.add_argument("--convs", default="", help="comma-separated LoCoMo sample ids (default all 10)")
    ap.add_argument("--part", default="", help="output part label when one arm is split over processes")
    ap.add_argument("--also-bare", action="store_true",
                    help="agent arms: also ask each LoCoMo question without the answer-style wrapper (report only)")
    ap.add_argument("--limit-q", type=int, default=0, help="smoke tests only: first N questions per conversation")
    ap.add_argument("--limit", type=int, default=0, help="smoke tests only: first N general items")
    ap.add_argument("--model", default="", help="agent arms: reader dir")
    ap.add_argument("--gen-model", default="", help="agent arms: base MiniCPM5-1B dir")
    ap.add_argument("--mouth-model", default="")
    ap.add_argument("--skip-preflight", action="store_true", help="smoke tests with a stubbed router only")
    args = ap.parse_args()
    if args.cmd == "fetch":
        fetch(Path(args.data))
        return 0
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    if not (args.arm and args.name and args.out):
        raise SystemExit("bm390: --arm, --name and --out are required")
    if args.cmd == "locomo":
        run_locomo(args)
    else:
        if not args.task:
            raise SystemExit("bm390: general needs --task mmlu|gsm8k")
        run_general(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
