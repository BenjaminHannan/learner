#!/usr/bin/env python3
"""K2 names-question probe (Sleep-B addendum 11b follow-up): which way of asking makes IFM/K2-Horizon-3.7B answer the names re-read question correctly?

Sleep-B's names pass (sleepb.Brain.names_pass) asks, for pairs of candidate names in one chat message, how they are related (a relation in 1 to 4 words, or "no"). K2 answers "no" every time with its
think block closed at once, and the 11b fix (open the low-effort block, 256 tokens) produced 0 thinking tokens. This script asks the SAME questions under several prompt formats, on the base model
(no LoRA, the way names_pass runs), on the Week-1 world (never Week-2, the test world), and scores each against the world's ground truth.

Questions: Brain.tag(d) for each day (days 1-3), then Brain.names_pass(d) run with its prompt builder wrapped to record the (message, name, name) triples it asks and its generator stubbed out (nothing is
generated, no item is added): the questions are exactly the ones names_pass asks, with the items the tagger made so far. Truth: a pair is "linked" when sleepb.gt_match finds it among the ground-truth
(subject, object) pairs of the week (current and old values, the helper Brain.diagnostics uses); "linked_turn" is the stricter test against the facts the diary marks as mentioned in that very message.
Variants (greedy, base model, --gen-bs per batch, the same questions in each):
  off       today's prompt (names_prompt, think block closed at once), answer at most 12 tokens
  yesno_lp  "... Answer yes or no." with thinking off; one forward pass, no generation; yes iff the best of yes / Yes / " yes" ... beats the best of no / No / " no" ... in next-token log-probability
  quote     the original question, but first the exact words of the message that link the two names: `Evidence: "<words>"` / `Relation: <1 to 4 words, or no>`; thinking off, 48 tokens; no Relation line = no
  low       the 11b two-stage path: open <ifm|think_faster>, at most 256 thinking tokens (stop at the close tag or end of turn), then the close tag is appended (forced when capped) and the answer (12 tokens)
  medium    the same with <ifm|think_fast> (reasoning_effort="medium")
  high      the same with <ifm|think> (reasoning_effort="high", the template default), 256 thinking tokens, forced close if capped
  high512   as high with 512 thinking tokens
Per variant: n, yes, yes_correct, no_correct, accuracy, mean thinking tokens, capped (thinking blocks the model did not close itself), wall seconds, 5 example rows. Nothing here changes the other files'
behaviour (Lang.think_eos only gained an optional effort argument).

  python3 backbone/sleep/brain/k2_names_probe.py --out out/k2probe/probe.json      # the box (run_box.sh K2PROBE); writes probe.json, probe_rows.json, probe.log
  python3 backbone/sleep/brain/k2_names_probe.py --smoke --out /tmp/x/probe.json   # CPU: tiny random K2 (real tokenizer + remote code), small caps, garbage answers: plumbing only
"""
from __future__ import annotations

import argparse
import contextlib
import json
import re
import sys
import time
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
for _p in (HERE, HERE.parent, HERE.parent.parent):  # sleepb.py (here), sleep1.py / facts.py (backbone/sleep), train.py (backbone)
    sys.path.insert(0, str(_p))
import torch  # noqa: E402
import sleepb  # noqa: E402
from sleep1 import K2_END, K2_THINK_OPEN, K2_THINK_SHUT, Lang  # noqa: E402
from sleepb import K2_REPO, K2_REV, KINDS, Brain, Diary, check_week, gt_match, names_prompt, norm, parse_rel  # noqa: E402
from train import K2_TYPE, load_model  # noqa: E402

ARM = "ab_ob_b4_nb"  # the K2 arm (in NAMES_ARMS; tag_prompt as every arm but ab_ob_tag2)
SYSTEM = "You extract facts from chat messages."  # names_prompt's system line
THINK = {"low": ("low", 256), "medium": ("medium", 256), "high": ("high", 256), "high512": ("high", 512)}  # variant -> (reasoning_effort, thinking tokens max)
VARIANTS = ["off", "yesno_lp", "quote", *THINK]
YES_STR, NO_STR = ("yes", " yes", "Yes", " Yes", "YES", " YES"), ("no", " no", "No", " No", "NO", " NO")  # first tokens compared by yesno_lp (max over case / leading space)


# ------------------------------------------------------------------ prompts (names_prompt itself is reused for off / low / medium / high)
def yesno_prompt(L, text, a, b):  # yesno_lp: names_prompt's framing, a yes / no question, thinking off
    return L.render(SYSTEM, f"Message from Sam:\n\"{text}\"\n\nDoes this message say how \"{a}\" and \"{b}\" are related? Answer yes or no.")


def quote_prompt(L, text, a, b):  # quote: names_prompt's question, evidence first, then the relation; thinking off
    u = (f"Message from Sam:\n\"{text}\"\n\nDoes this message say how \"{a}\" and \"{b}\" are related? First copy the exact words of the message that link the two names (or write none). "
         f"Then give the relation in 1 to 4 words (for example: works at, lives in, is the mentor of, owns the boat), or no if the message does not say how they are related. "
         f"Reply in exactly this form:\nEvidence: \"<words>\"\nRelation: <1 to 4 words, or no>")
    return L.render(SYSTEM, u)


def parse_quote(txt):  # the last "Relation:" line (or tail of a line) -> parse_rel of what follows; no such line = None (no)
    m = re.findall(r"relation\s*:[ \t]*(.*)", str(txt or ""), re.I)
    return parse_rel(m[-1]) if m else None


def effort_lang(L, effort):  # names_prompt only calls .render / .render_think(system, user): a view of L whose think-open render is at `effort`
    return SimpleNamespace(render=L.render, render_think=lambda sy, u: L.render_think(sy, u, effort))


def strip_close(txt, close):  # sleepb.strip_think for any close tag: (thinking without trailing close tag / im_end, whether the model closed the block itself)
    txt, closed = str(txt or "").strip(), False
    while txt.endswith(close) or txt.endswith(K2_END):
        closed |= txt.endswith(close)
        txt = txt[:-len(close if txt.endswith(close) else K2_END)].rstrip()
    return txt, closed


# ------------------------------------------------------------------ questions
def collect(brain, d):
    """The (turn, name, name) questions names_pass(d) asks, through the real code: names_prompt records its arguments, the generator answers "" (no model call, no item added)."""
    got, real = [], sleepb.names_prompt

    def rec(L, text, a, b, think=False, **kw):  # (names_pass passes effort= on K2 since addendum 11c)
        got.append((text, a, b))
        return real(L, text, a, b, think=think, **kw)
    sleepb.names_prompt, brain.gen = rec, lambda prompts, max_new, **kw: [""] * len(prompts)
    try:
        st = brain.names_pass(d)
    finally:
        sleepb.names_prompt = real
        brain.__dict__.pop("gen", None)  # back to the bound method
    assert st["pairs"] == len(got), (st, len(got))
    by_text = {t["text"]: t for t in brain.diary.turns if t["day"] == d}
    gmap, allp = {g[0]: g for g in brain.G}, [p for g in brain.G for p in g[2] + g[3]]  # ground truth per item id; every (subject, object) pair of the week (current + old values)
    qs = []
    for text, a, b in got:
        t = by_text[text]
        tp = [p for m in t.get("mentions", []) for p in gmap[m][2] + gmap[m][3]]
        qs.append({"day": d, "turn": t["i"], "text": text, "a": a, "b": b, "linked": gt_match(a, b, allp), "linked_turn": gt_match(a, b, tp)})
    return qs, st


# ------------------------------------------------------------------ variants: each returns [{"yes": bool, "rel", "ans", "think", "think_tokens", "closed"}] per question, plus extras
def run_off(brain, L, qs):
    raw = brain.gen([names_prompt(L, q["text"], q["a"], q["b"]) for q in qs], 12)
    return [{"yes": (r := parse_rel(x)) is not None, "rel": r, "ans": x, "think": "", "think_tokens": 0, "closed": True} for x in raw], {}


def run_quote(brain, L, qs, max_new):
    raw = brain.gen([quote_prompt(L, q["text"], q["a"], q["b"]) for q in qs], max_new)
    rows = [{"yes": (r := parse_quote(x)) is not None, "rel": r, "ans": x, "think": "", "think_tokens": 0, "closed": True} for x in raw]
    return rows, {"max_new": max_new, "no_relation_line": sum(not re.search(r"relation\s*:", x, re.I) for x in raw)}


def run_think(brain, L, qs, effort, cap):  # the 11b path at `effort`: stage 1 thinks (cap tokens, stops at the close tag / end of turn), stage 2 = stage-1 prompt + thinking + ONE close tag, then the answer (12 tokens)
    close, Le = K2_THINK_SHUT[effort], effort_lang(L, effort)
    p1 = [names_prompt(Le, q["text"], q["a"], q["b"], think=True) for q in qs]
    assert all(p.endswith(K2_THINK_OPEN[effort]) and close not in p for p in p1), p1[0][-80:]
    th = [strip_close(x, close) for x in brain.gen(p1, cap, eos=L.think_eos(effort))]
    p2 = [p + x + close for p, (x, _) in zip(p1, th)]
    assert all(p.endswith(close) and p.count(close) == 1 and K2_END not in p[len(q):] for p, q in zip(p2, p1)), [p[-80:] for p in p2[:2]]  # one close tag, no end of turn after the thinking
    raw = brain.gen(p2, 12)
    others = [c for e, c in K2_THINK_SHUT.items() if c != close]
    rows = [{"yes": (r := parse_rel(x)) is not None, "rel": r, "ans": x, "think": t, "think_tokens": len(L.ids(t)), "closed": c} for (t, c), x in zip(th, raw)]
    return rows, {"effort": effort, "think_max": cap, "closed_by_model": sum(c for _, c in th), "other_close_tag_in_thinking": sum(any(o in t for o in others) for t, _ in th), "stage2_prompt_tail": p2[0][-70:]}


@torch.no_grad()
def run_yesno_lp(L, model, qs, bs):  # one forward pass per batch; the next-token log-probs after the (thinking-off) prompt
    prompts = [yesno_prompt(L, q["text"], q["a"], q["b"]) for q in qs]
    yes, no = sorted({L.ids(s)[0] for s in YES_STR}), sorted({L.ids(s)[0] for s in NO_STR})
    order, sc = sorted(range(len(prompts)), key=lambda i: len(prompts[i])), [None] * len(prompts)
    for s0 in range(0, len(order), bs):
        idx = order[s0:s0 + bs]
        seqs = [L.ids(prompts[i]) for i in idx]
        ids, mask = L.pad_right(seqs)
        logits = model(input_ids=ids, attention_mask=mask).logits
        for r, i in enumerate(idx):
            lp = logits[r, len(seqs[r]) - 1].float().log_softmax(-1)
            sc[i] = (float(lp[yes].max()), float(lp[no].max()))
    rows = [{"yes": y > n, "rel": None, "ans": "yes" if y > n else "no", "think": "", "think_tokens": 0, "closed": True, "lp_yes": round(y, 3), "lp_no": round(n, 3), "margin": round(y - n, 3)} for y, n in sc]
    return rows, {"yes_token_ids": yes, "no_token_ids": no, "prompt_tail": prompts[0][-90:]}


# ------------------------------------------------------------------ scoring
def auc(pos, neg):  # P(a random linked pair scores above a random unlinked one), ties count half
    return None if not pos or not neg else round(sum((p > n) + 0.5 * (p == n) for p in pos for n in neg) / (len(pos) * len(neg)), 4)


def summarize(qs, rows, secs, extra):
    n, yes = len(qs), sum(r["yes"] for r in rows)
    ok = lambda key: (sum(r["yes"] and q[key] for q, r in zip(qs, rows)), sum(not r["yes"] and not q[key] for q, r in zip(qs, rows)))  # noqa: E731
    (yc, nc), (yct, nct) = ok("linked"), ok("linked_turn")
    n_lin, n_lin_t = sum(q["linked"] for q in qs), sum(q["linked_turn"] for q in qs)
    lin = [i for i, q in enumerate(qs) if q["linked"]]
    pick = lin[:3] + [i for i, q in enumerate(qs) if not q["linked"]][:2]
    pick += [i for i in range(n) if i not in pick][:5 - len(pick)]
    s = {"n": n, "yes": yes, "yes_rate": round(yes / max(n, 1), 4), "yes_correct": yc, "no_correct": nc, "accuracy": round((yc + nc) / max(n, 1), 4),
         "n_linked": n_lin, "n_unlinked": n - n_lin, "precision": round(yc / yes, 4) if yes else None, "recall": round(yc / n_lin, 4) if n_lin else None,
         "yes_correct_turn": yct, "no_correct_turn": nct, "accuracy_turn": round((yct + nct) / max(n, 1), 4), "n_linked_turn": n_lin_t,
         "think_tokens_mean": round(sum(r["think_tokens"] for r in rows) / max(n, 1), 1), "capped": sum(not r["closed"] for r in rows), "wall_seconds": round(secs, 1), **extra,
         "examples": [{"pair": [qs[i]["a"], qs[i]["b"]], "linked": qs[i]["linked"], "day": qs[i]["day"], "text": qs[i]["text"][:160], "thinking": rows[i]["think"][:300], "answer": rows[i]["ans"][:300],
                       "yes": rows[i]["yes"], "relation": rows[i]["rel"]} for i in pick]}
    if rows and "margin" in rows[0]:  # yesno_lp: does the margin separate linked from unlinked pairs at any threshold?
        m = [r["margin"] for r in rows]
        s.update(auc=auc([m[i] for i in lin], [m[i] for i, q in enumerate(qs) if not q["linked"]]), margin_mean_linked=round(sum(m[i] for i in lin) / max(len(lin), 1), 3),
                 margin_mean_unlinked=round(sum(m[i] for i, q in enumerate(qs) if not q["linked"]) / max(n - len(lin), 1), 3))
    return s


def template_check(L):  # stage 2 (prompt + thinking + close tag + answer + im_end) against the chat template's own rendering of that turn, per effort; the off render against the empty think block
    msgs, out = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": "U"}], {}
    for eff, fld in (("low", "think_faster"), ("medium", "think_fast"), ("high", "think")):
        try:
            want = L.tok.apply_chat_template(msgs + [{"role": "assistant", "content": "no", fld: "abc def"}], tokenize=False)
            out[eff] = want == L.render_think(SYSTEM, "U", eff) + "abc def" + K2_THINK_SHUT[eff] + "no" + K2_END
        except Exception as e:  # a template without that field: report, do not stop the probe
            out[eff] = repr(e)[:150]
    out["off"] = L.render(SYSTEM, "U").endswith("<ifm|think>\n</ifm|think>")
    return out


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", required=True, help="result JSON; the per-question rows go to <stem>_rows.json and the log to <stem>.log next to it")
    ap.add_argument("--model", default=K2_REPO)
    ap.add_argument("--revision", default=K2_REV, help="model repo revision (default: the sha Sleep-B pins)")
    ap.add_argument("--week", default=str(HERE / "data" / "week1.json"), help="the Week-1 world (week2 is the test world and is refused)")
    ap.add_argument("--days", default=None, help="comma-separated days to tag and ask about (default 1,2,3)")
    ap.add_argument("--variants", default=",".join(VARIANTS), help="comma-separated subset of " + ",".join(VARIANTS))
    ap.add_argument("--gen-bs", type=int, default=32, help="sleepb's default")
    ap.add_argument("--max-q", type=int, default=0, help="keep at most this many questions, evenly strided (0 = all; smoke: 12)")
    ap.add_argument("--quote-max", type=int, default=48, help="new tokens of the quote variant")
    ap.add_argument("--smoke", action="store_true", help="CPU: tiny random K2 with the real tokenizer and remote code (sleepb --smoke --model IFM/K2-Horizon-3.7B), small caps; the answers are garbage")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    if "week2" in Path(args.week).name:
        ap.error("--week must be the Week-1 world, not week2 (the test world)")
    variants = [v for v in args.variants.split(",") if v]
    if bad := [v for v in variants if v not in VARIANTS]:
        ap.error(f"unknown variants {bad}")
    days = [int(x) for x in (args.days or "1,2,3").split(",")]
    think = {v: (e, min(c, 12) if args.smoke else c) for v, (e, c) in THINK.items()}
    quote_max = min(args.quote_max, 16) if args.smoke else args.quote_max
    max_q = args.max_q or (12 if args.smoke else 0)
    if args.smoke:
        args.gen_bs = 4
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    logf = open(out.with_suffix(".log"), "a")

    def log(m):
        print(m, flush=True)
        logf.write(m + "\n")
        logf.flush()
    t0 = time.time()
    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() and not args.smoke else "cpu")
    lm, tok = load_model(args, device, torch.bfloat16 if device.type == "cuda" else torch.float32)
    L = Lang(tok, args.smoke, device, k2=lm.config.model_type == K2_TYPE)
    assert L.k2, f"{args.model} is not a K2-Horizon model"
    lm.disable_adapter = contextlib.nullcontext  # Brain.gen runs the base inside pm.disable_adapter(): a plain model has no adapter to disable
    week = json.loads(Path(args.week).read_text())
    check_week(week)
    diary = Diary(week)
    leak = {norm(x) for x in week.get("test_strings_norm", [])} | {norm(t["q"]) for k in KINDS for t in week["tests"][k]}
    bargs = argparse.Namespace(arm=ARM, smoke=args.smoke, gen_bs=args.gen_bs, seed=args.seed, max_dream_items=160, rem_chains=30, rem_gist=30)  # what Brain.__init__ / tag / names_pass read
    brain = Brain(L, lm, bargs, week, diary, leak, [], [], 0.0, log)  # replay / ARC stand-ins: the tagging and names pass use neither
    brain.raw = {}
    res = {"model": args.model, "revision": args.revision, "smoke": args.smoke, "device": str(device), "week": args.week, "arm": ARM, "gen_bs": args.gen_bs, "days": days, "think_variants": think,
           "template_check": template_check(L), "partial": True}
    log(f"[k2probe] model {args.model}@{args.revision[:10] if args.revision else None} device {device} week {args.week} days {days} gen_bs {args.gen_bs} variants {variants}; template check {res['template_check']}")
    if not all(v is True for v in res["template_check"].values()):
        log("[k2probe] WARNING: the chat template no longer renders a finished turn the way stage 2 builds it; read the stage-2 prompts before trusting the thinking variants")

    qs, res["tag"], res["names_pass_dry"] = [], {}, {}
    for d in days:  # tag day d (items accumulate across days, as in a night), then the questions names_pass(d) would ask
        t1 = time.time()
        res["tag"][str(d)] = brain.tag(d)
        qd, st = collect(brain, d)
        res["names_pass_dry"][str(d)] = {k: st[k] for k in ("candidates", "turns", "turns_ge2", "pairs")}
        qs += qd
        log(f"[k2probe] day {d}: tag {res['tag'][str(d)]}; names questions {len(qd)} ({sum(q['linked'] for q in qd)} linked by a true fact); {time.time() - t1:.0f}s")
    if max_q and len(qs) > max_q:
        qs = qs[::max(len(qs) // max_q, 1)][:max_q]
    res["n_questions"], res["n_linked"], res["n_linked_turn"] = len(qs), sum(q["linked"] for q in qs), sum(q["linked_turn"] for q in qs)
    res["baseline_accuracy"] = {"always_yes": round(res["n_linked"] / max(len(qs), 1), 4), "always_no": round(1 - res["n_linked"] / max(len(qs), 1), 4)}  # most names questions are about linked pairs: read yes_correct and no_correct, not accuracy alone
    log(f"[k2probe] {len(qs)} questions, {res['n_linked']} linked by a true fact of the week ({res['n_linked_turn']} by a fact marked in that message), {len(qs) - res['n_linked']} not; always-yes accuracy {res['baseline_accuracy']['always_yes']}")
    res["variants"], rows_all = {}, {"questions": qs}

    def dump(final=False):
        res["partial"], res["wall_seconds"] = not final, round(time.time() - t0, 1)
        out.write_text(json.dumps(res, indent=1))
        out.with_name(out.stem + "_rows.json").write_text(json.dumps(rows_all, indent=1))
    dump()
    for v in variants:
        t1 = time.time()
        if v == "off":
            rows, extra = run_off(brain, L, qs)
        elif v == "yesno_lp":
            rows, extra = run_yesno_lp(L, lm, qs, max(args.gen_bs // 2, 1))
        elif v == "quote":
            rows, extra = run_quote(brain, L, qs, quote_max)
        else:
            rows, extra = run_think(brain, L, qs, *think[v])
        s = res["variants"][v] = summarize(qs, rows, time.time() - t1, extra)
        rows_all[v] = rows
        log(f"[k2probe] {v:9s} n={s['n']} yes={s['yes']} ({s['yes_rate']:.0%}) yes_correct={s['yes_correct']}/{s['n_linked']} no_correct={s['no_correct']}/{s['n_unlinked']} acc={s['accuracy']:.3f} "
            f"think_mean={s['think_tokens_mean']} capped={s['capped']} wall={s['wall_seconds']:.0f}s" + (f" auc={s['auc']}" if "auc" in s else ""))
        dump()
    dump(True)
    log(f"[k2probe] done in {time.time() - t0:.0f}s -> {out}")


if __name__ == "__main__":
    main()
