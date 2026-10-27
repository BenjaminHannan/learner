#!/usr/bin/env python3
"""dir-s5 (2026-09-29): can the plain 1.2B talker (LFM2.5-1.2B-Instruct) read the right notes? Marks:
artifacts/claude-dir-s5-lme-20260929/PASSMARKS.md. Inference only; nothing trains. New file.

Uses only the 100 dev questions listed in dev100.ids.txt (scripts/claude_dir_s5_slice.py). The other 400 are never
kept, read or scored. Arms (same model, same system prompt, same greedy decoding; only the material differs):
  closed  no material                      oracle  the evidence sessions only, in full
  raw10   top-10 retrieved rounds          notes10 the same 10 rounds, each turned into one short fact note by the
                                                   same model (the note writer never sees the question)
  plain   the latest whole-haystack text that fits the window (the plain long-context twin)
Retrieval: the stack's frozen MiniLM-L6-v2 (fable_self122_train), cosine, a round = one user turn + the next assistant
turn, first 128 word pieces, query = the question. Scoring, two readings of every answer (see PASSMARKS): AUTO
(normalised containment / abstention phrases) and JUDGE (the same model as a yes/no judge, gated by a calibration).
Question, answer and reply text stay in WORK (outside the repository); OUT gets counts and per-question 0/1 flags only.

  python -B scripts/claude_dir_s5_run.py selftest
  python -B scripts/claude_dir_s5_run.py run --data DATA.json --model LFM_DIR --work WORK --out OUT
"""
import hashlib, json, math, re, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ART = HERE.parent / "artifacts" / "claude-dir-s5-lme-20260929"
DATA_SHA = "d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442"
ARMS = ["closed", "oracle", "raw10", "notes10", "plain"]
TOPK, WINDOW, MAX_NEW = 10, 24000, 64
SYSTEM = ("You answer a question about the user's past chats with an assistant. Use only the material given. "
          "Reply with one short sentence. If the material does not say, reply exactly: I don't know.")
NOTE_SYSTEM = ("Write one short note (one line, at most 30 words) of the facts about the user in the chat exchange "
               "below. Keep dates, names, numbers, places and things the user has or did. If it holds no facts about "
               "the user, write: none.")
ABS_PAT = re.compile(r"(don'?t know|do not know|not mentioned|no information|not enough information|cannot (find|answer|say)|"
                     r"can'?t (find|answer|say)|unable to|not provided|did(n'?t| not) (mention|say|specify)|isn'?t (mentioned|stated)|"
                     r"not (stated|specified|available|clear)|no record|not sure|unknown)", re.I)
NUMW = {w: str(i) for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve".split())}
STOP = set("a an the of to in on at and or is was were are be been it its for with by from that this as".split())


def norm(s):
    s = re.sub(r"[^a-z0-9 ]", " ", str(s).lower().replace("'", ""))
    return " ".join(NUMW.get(w, w) for w in s.split())


def auto_correct(qid, gold, reply):
    """AUTO reading. Returns 1, 0, or None (not scorable: gold longer than 12 words and not an abstention)."""
    if qid.endswith("_abs"):
        return int(bool(ABS_PAT.search(reply)))
    g = norm(gold)
    gt = [w for w in g.split() if w not in STOP]
    if len(g.split()) > 12 or not gt:
        return None
    r = norm(reply)
    if g in r:
        return 1
    rt = set(r.split())
    return int(len(gt) <= 5 and all(w in rt for w in gt))


def mcnemar_p(a, b):
    """Exact two-sided McNemar on paired 0/1 lists: p that the discordant split is this uneven."""
    x = sum(1 for u, v in zip(a, b) if u and not v)
    y = sum(1 for u, v in zip(a, b) if v and not u)
    n = x + y
    if n == 0:
        return 1.0, x, y
    k = min(x, y)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n), x, y


def rounds_of(item):
    """[(session_id, date, order, text, has_answer)] one per user turn (+ the assistant turn after it)."""
    out = []
    for sid, date, sess in zip(item["haystack_session_ids"], item["haystack_dates"], item["haystack_sessions"]):
        i = 0
        while i < len(sess):
            t = sess[i]
            txt, ha = "User: " + t["content"] if t["role"] == "user" else "Assistant: " + t["content"], bool(t.get("has_answer"))
            if t["role"] == "user" and i + 1 < len(sess) and sess[i + 1]["role"] == "assistant":
                txt += "\nAssistant: " + sess[i + 1]["content"]
                ha = ha or bool(sess[i + 1].get("has_answer"))
                i += 1
            out.append((sid, date, len(out), txt, ha))
            i += 1
    return out


def session_text(sess):
    return "\n".join(("User: " if t["role"] == "user" else "Assistant: ") + t["content"] for t in sess)


def build_material(arm, item, rnds, top, notes):
    """List of material blocks in time order (dropped from the front if too long, by the caller)."""
    if arm == "closed":
        return []
    if arm == "oracle":
        ans = set(item["answer_session_ids"])
        return [f"[Chat on {d}]\n{session_text(s)}" for sid, d, s in
                zip(item["haystack_session_ids"], item["haystack_dates"], item["haystack_sessions"]) if sid in ans]
    if arm == "plain":
        return [f"[Chat on {d}]\n{session_text(s)}" for d, s in zip(item["haystack_dates"], item["haystack_sessions"])]
    idx = sorted(top)                                    # time order
    if arm == "raw10":
        return [f"[Chat on {rnds[i][1]}]\n{rnds[i][3]}" for i in idx]
    return [f"[Note, chat on {rnds[i][1]}] {notes[i]}" for i in idx]


def user_prompt(blocks, item):
    mat = "\n\n".join(blocks) if blocks else "(none)"
    return f"Material:\n{mat}\n\nCurrent date: {item['question_date']}\nQuestion: {item['question']}\nAnswer:"


JUDGE = {
    "default": "I will give you a question, a correct answer, and a response from a model. Answer yes if the response contains the correct answer, otherwise no. If the response only contains a subset of the information required by the answer, answer no.",
    "temporal-reasoning": "I will give you a question, a correct answer, and a response from a model. Answer yes if the response contains the correct answer, otherwise no. Do not penalize off-by-one errors for the number of days. If the response only contains a subset of the information required, answer no.",
    "knowledge-update": "I will give you a question, a correct answer, and a response from a model. Answer yes if the response contains the correct answer, otherwise no. If the response also lists an older outdated answer as long as the updated answer is given, answer yes.",
    "single-session-preference": "I will give you a question, a rubric for the desired personalized response, and a response from a model. Answer yes if the response satisfies the rubric (it need not cover every point but must use the user's personal information correctly), otherwise no.",
    "abstention": "I will give you an unanswerable question, an explanation, and a response from a model. Answer yes if the model correctly says the question cannot be answered from what it knows, otherwise no.",
}


def judge_prompt(qtype, qid, question, gold, reply):
    key = "abstention" if qid.endswith("_abs") else qtype
    lab = "Rubric" if key == "single-session-preference" else ("Explanation" if key == "abstention" else "Correct Answer")
    return JUDGE.get(key, JUDGE["default"]), f"Question: {question}\n{lab}: {gold}\nModel Response: {reply}\n\nAnswer (yes or no):"


def load_dev(data):
    if hashlib.sha256(Path(data).read_bytes()).hexdigest() != DATA_SHA:
        raise SystemExit("DATA-SHA-MISMATCH")
    seal = (ART / "SEAL-slice.sha256.txt").read_text().split()[0]
    txt = (ART / "dev100.ids.txt").read_text()
    if hashlib.sha256(txt.encode()).hexdigest() != seal:
        raise SystemExit("SEAL-MISMATCH dev100.ids.txt")
    ids = [l.split("\t")[0] for l in txt.strip().split("\n")]
    keep = {x["question_id"]: x for x in json.loads(Path(data).read_text(encoding="utf-8")) if x["question_id"] in set(ids)}
    assert len(keep) == 100
    return [keep[i] for i in ids]


def counts(flags):
    return sum(f for f in flags if f is not None), sum(f is not None for f in flags)


def report(items, res, gate, out):
    """res[arm] = {'auto': [0/1/None]*100, 'judge': [0/1]*100}. Writes RESULT-counts.json and prints the verdict."""
    R = {}
    for rd in ("auto", "judge"):
        R[rd] = {a: counts(res[a][rd]) for a in res}
    pairs = {}
    for rd in ("auto", "judge"):
        def paired(a, b):
            ix = [i for i in range(len(items)) if res[a][rd][i] is not None and res[b][rd][i] is not None]
            return mcnemar_p([res[a][rd][i] for i in ix], [res[b][rd][i] for i in ix])
        pairs[rd] = {"notes_vs_raw": paired("notes10", "raw10"), "raw_vs_oracle": paired("raw10", "oracle"),
                     "oracle_vs_plain": paired("oracle", "plain")}
    verdict = {}
    for rd in ("auto", "judge"):
        n = R[rd]["oracle"][1]
        o, rw, no, cb = R[rd]["oracle"][0], R[rd]["raw10"][0], R[rd]["notes10"][0], R[rd]["closed"][0]
        p2, _, _ = pairs[rd]["notes_vs_raw"]
        # marks are written for n = 100; when AUTO cannot score some questions the bars are scaled by n/100 (rounded up)
        s = n / 100
        verdict[rd] = {"n": n, "oracle": o, "raw10": rw, "notes10": no, "closed": cb,
                       "P1_oracle_ge_50pct": o >= math.ceil(50 * s), "P2_notes_minus_raw_ge_10pct": (no - rw) >= math.ceil(10 * s) and p2 < 0.05,
                       "W1_oracle_lt_30pct": o < 30 * s, "W2_raw_beats_oracle": rw > o, "contamination_closed_gt_10pct": cb > 10 * s}
    json.dump({"counts": R, "mcnemar": pairs, "verdict": verdict, "judge_gate": gate}, open(Path(out) / "RESULT-counts.json", "w"), indent=1)
    return R, pairs, verdict


def selftest():
    assert norm("Twenty-two, I don't know") == "twenty 2 i dont know"
    assert auto_correct("q1", "Seven", "You have 7 cats.") == 1 and auto_correct("q1", "seven cats", "two cats") == 0
    assert auto_correct("q2_abs", "You did not mention it", "I don't know.") == 1
    assert auto_correct("q2_abs", "x", "It is Paris.") == 0
    assert auto_correct("q3", " ".join(["w"] * 13), "w") is None
    p, x, y = mcnemar_p([1] * 12 + [0] * 3, [0] * 12 + [1] * 3)
    assert (x, y) == (12, 3) and abs(p - 0.03516) < 1e-3, p
    it = {"haystack_session_ids": ["a", "b"], "haystack_dates": ["d1", "d2"], "answer_session_ids": ["b"], "question": "Q?",
          "question_date": "d3", "haystack_sessions": [[{"role": "user", "content": "u1"}, {"role": "assistant", "content": "a1"}],
                                                        [{"role": "user", "content": "u2", "has_answer": True}, {"role": "assistant", "content": "a2"}, {"role": "user", "content": "u3"}]]}
    r = rounds_of(it)
    assert [x[3] for x in r] == ["User: u1\nAssistant: a1", "User: u2\nAssistant: a2", "User: u3"] and [x[4] for x in r] == [False, True, False]
    assert build_material("oracle", it, r, [], {}) == ["[Chat on d2]\nUser: u2\nAssistant: a2\nUser: u3"]
    assert build_material("raw10", it, r, [2, 0], {})[0].startswith("[Chat on d1]")
    assert build_material("notes10", it, r, [1], {1: "n"}) == ["[Note, chat on d2] n"]
    assert user_prompt([], it).startswith("Material:\n(none)")
    assert judge_prompt("x", "z_abs", "q", "g", "r")[0] == JUDGE["abstention"]
    d = ART / "dev100.ids.txt"
    if d.exists():
        assert len(d.read_text().strip().split("\n")) == 100
    print("selftest ok")


def run(a):
    import torch
    import claude_bm390 as B
    import fable_self122_train as T
    work, out = Path(a["work"]), Path(a["out"])
    work.mkdir(parents=True, exist_ok=True); out.mkdir(parents=True, exist_ok=True)
    items = load_dev(a["data"])
    if a.get("limit"):
        items = items[:int(a["limit"])]          # smoke only; the real run has all 100
    N = len(items)
    tok, model, dev, ctx = B.plain_model(a["model"])
    torch.manual_seed(0)
    gen = lambda system, user, n: B.generate(a["model"], system, user, n)
    ntok = lambda s: len(tok(s, add_special_tokens=False)["input_ids"])
    t0 = time.time()
    # ---- retrieval
    enc, wp, _ = T.load_encoder(T.resolve_snapshot(None))
    import torch.nn.functional as F
    def embed(texts):
        o = []
        with torch.no_grad():
            for i in range(0, len(texts), 64):
                ids, mask, _ = wp.batch(texts[i:i + 64], 128)
                h = enc(ids, mask); m = mask.unsqueeze(-1).float()
                o.append(F.normalize((h * m).sum(1) / m.sum(1).clamp_min(1e-6), dim=1))
        return torch.cat(o)
    tops, rnds_all, rec = [], [], {"sess_hit": 0, "ans_round_hit": 0, "ans_round_n": 0}
    for it in items:
        rn = rounds_of(it); rnds_all.append(rn)
        S = embed([x[3] for x in rn]) @ embed([it["question"]]).T
        top = S.squeeze(1).argsort(descending=True)[:TOPK].tolist()
        tops.append(top)
        ans = set(it["answer_session_ids"])
        rec["sess_hit"] += int(any(rn[i][0] in ans for i in top))
        ar = [i for i, x in enumerate(rn) if x[4]]
        rec["ans_round_hit"] += int(bool(ar) and any(i in top for i in ar)); rec["ans_round_n"] += int(bool(ar))
    print(f"retrieval done {time.time() - t0:.0f}s", rec, flush=True)
    # ---- notes (question-blind), cached
    nf = work / "notes.json"
    notes = json.loads(nf.read_text()) if nf.exists() else {}
    for qi, (it, rn, top) in enumerate(zip(items, rnds_all, tops)):
        for i in top:
            k = f"{qi}:{i}"
            if k not in notes:
                txt = rn[i][3]
                ids = tok(txt, add_special_tokens=False)["input_ids"]
                if len(ids) > 1500:
                    txt = tok.decode(ids[:1500])
                notes[k] = gen(NOTE_SYSTEM, f"Chat on {rn[i][1]}:\n{txt}", 60)[0].split("\n")[0].strip()
        nf.write_text(json.dumps(notes))
    print(f"notes done {time.time() - t0:.0f}s", flush=True)
    # ---- answers
    af = work / "answers.json"
    ans = json.loads(af.read_text()) if af.exists() else {}
    meta = {}
    for qi, it in enumerate(items):
        for arm in ARMS:
            k = f"{qi}:{arm}"
            nt = {i: notes[f"{qi}:{i}"] for i in tops[qi]}
            blocks = build_material(arm, it, rnds_all[qi], tops[qi], nt)
            dropped = 0
            while blocks and ntok("\n\n".join(blocks)) > WINDOW:
                blocks = blocks[1:]; dropped += 1
            if k not in ans:
                while True:
                    try:
                        ans[k] = gen(SYSTEM, user_prompt(blocks, it), MAX_NEW)[0]
                        break
                    except torch.cuda.OutOfMemoryError:      # a very long prompt: drop the earliest quarter, note it
                        torch.cuda.empty_cache()
                        cut = max(1, len(blocks) // 4)
                        blocks = blocks[cut:]; dropped += cut
                        if not blocks:
                            raise
            meta[k] = {"blocks_dropped": dropped}
        af.write_text(json.dumps(ans))
        if qi % 10 == 9 or qi == N - 1:
            print(f"answers {qi + 1}/{N} {time.time() - t0:.0f}s", flush=True)
    # determinism: 10 oracle prompts again
    same = 0
    for qi in range(min(10, N)):
        blocks = build_material("oracle", items[qi], rnds_all[qi], tops[qi], {})
        while blocks and ntok("\n\n".join(blocks)) > WINDOW:
            blocks = blocks[1:]
        same += int(gen(SYSTEM, user_prompt(blocks, items[qi]), MAX_NEW)[0] == ans[f"{qi}:oracle"])
    # ---- judge (one shot: first word yes/no), plus calibration
    def judge(qi, reply, gold=None):
        it = items[qi]
        s, u = judge_prompt(it["question_type"], it["question_id"], it["question"], it["answer"] if gold is None else gold, reply)
        return int(gen(s, u, 3)[0].strip().lower().startswith("yes"))
    cal_right = [judge(qi, str(items[qi]["answer"])) for qi in range(N)]
    cal_wrong = []
    for qi, it in enumerate(items):
        same_type = [j for j in range(N) if j != qi and items[j]["question_type"] == it["question_type"] and items[j]["question_id"].endswith("_abs") == it["question_id"].endswith("_abs")]
        other = items[same_type[(qi * 7) % len(same_type)]] if same_type else items[(qi + 1) % N]
        cal_wrong.append(judge(qi, str(other["answer"])))
    gate = {"right_judged_yes": sum(cal_right), "wrong_judged_yes": sum(cal_wrong), "n": N,
            "passes": sum(cal_right) >= 90 and sum(cal_wrong) <= 10, "determinism_same_of_10": same}
    print("judge gate", gate, flush=True)
    res = {arm: {"auto": [], "judge": []} for arm in ARMS}
    for qi, it in enumerate(items):
        for arm in ARMS:
            r = ans[f"{qi}:{arm}"]
            res[arm]["auto"].append(auto_correct(it["question_id"], str(it["answer"]), r))
            res[arm]["judge"].append(judge(qi, r))
    R, pairs, verdict = report(items, res, gate, out)
    flags = [{"id": it["question_id"], "type": it["question_type"], **{f"{arm}_{rd}": res[arm][rd][qi] for arm in ARMS for rd in ("auto", "judge")},
              **{f"{arm}_dropped": meta[f"{qi}:{arm}"]["blocks_dropped"] for arm in ARMS}} for qi, it in enumerate(items)]
    (out / "flags.jsonl").write_text("\n".join(json.dumps(f) for f in flags) + "\n")
    bytype = {}
    for qi, it in enumerate(items):
        for arm in ARMS:
            for rd in ("auto", "judge"):
                v = res[arm][rd][qi]
                if v is not None:
                    c = bytype.setdefault(it["question_type"], {}).setdefault(f"{arm}_{rd}", [0, 0]); c[0] += v; c[1] += 1
    (out / "by-type.json").write_text(json.dumps(bytype, indent=1))
    (out / "retrieval.json").write_text(json.dumps({**rec, "n": N, "topk": TOPK, "minutes": round((time.time() - t0) / 60, 1),
                                                    "torch": torch.__version__, "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu"}))
    print(json.dumps({"counts": R, "mcnemar": pairs, "verdict": verdict}, indent=1))


if __name__ == "__main__":
    if sys.argv[1] == "selftest":
        selftest()
    else:
        import argparse
        ap = argparse.ArgumentParser(); ap.add_argument("cmd"); ap.add_argument("--data"); ap.add_argument("--model")
        ap.add_argument("--work"); ap.add_argument("--out"); ap.add_argument("--limit", type=int, default=0)
        run(vars(ap.parse_args()))
