"""Step 7: per-arm night files from the shared day logs + the tagger output. Runs in the container (needs a tokenizer for token counts only).
Shared by A+, B and B-sft every night: fact sentences (paraphrases of Ben's answers/corrections + the day's background facts) and corrected-action SFT
on tagged regret turns. Only the slice (15% of the night's token-passes) differs:
  B      DPO pairs   regret: chosen = pre-written one-line question naming the slot with its 2 likeliest values, rejected = the guessed action
                     annoyance: chosen = the direct correct action (answer made visible in memory), rejected = the question the model asked
  B-sft  SFT on the chosen sides only
  A+     extra fact paraphrases + corrected-action SFT on the same events
A+ and B-sft are padded with more of their own items until their total token-passes are within tolerance of B's (compute_ledger asserts it).
  python -m sleep2.askonce.build_night_data --diary DIR --tags TAGS.jsonl --tokenizer tiny:/path|HF_ID --out DIR
"""
import argparse
import math
import os
import re
import zlib
from pathlib import Path

from . import compute_ledger as CL
from .config import (ANCHOR_W, DATA, LEDGER_TOL, N_ANCHOR, SLICE_FRAC, SYSTEM, jdump, jl_read, jl_write, jload, night_opt_steps, night_scale, norm, n_nights, shrink)
from .slot_memory import memory_from_diary
from .tagger import groups
from .tools_mock import parse_reply
from .world import Persona, act_text, fact_messages, first_messages, general_messages, load_requests, render

SHARED_PARA = 4
FACT_PROMPT_MSGS = [{"role": "system", "content": "You are Ben's assistant. You keep notes about Ben."}, {"role": "user", "content": "Write down one fact you know about Ben."}]
END = "<|ifm|im_end|>"


def crc(*p):
    return zlib.crc32("|".join(map(str, p)).encode())


def fact_item(bos, text):
    return {"kind": "sft", "prompt": render(FACT_PROMPT_MSGS, True, bos), "target": text + END, "src": "fact"}


def sft_action(bos, user_content, action_text, src):
    return {"kind": "sft", "prompt": render([{"role": "system", "content": SYSTEM}, {"role": "user", "content": user_content}], True, bos), "target": action_text + END, "src": src}


def memory_has_answer(mem_part, s):
    t = norm(mem_part)
    if s["kind"] in ("contact", "meeting", "file"):
        return norm(s["value"]) in t
    if norm(s["ref"]) not in t:
        return False
    if s["kind"] == "duration":
        return bool(re.search(rf"(?<!\d){re.escape(s['value'])}(?!\d)", t))
    return ("send" in t or "sent" in t) if s["value"] == "send_email" else ("draft" in t)


def user_content_with_answer(persona, req, orig_user, slot_id, prior_entries):
    """Annoyance prompts: make the already-known answer visible in [Memory] (the BM25 hit that defines the annoyance). None if no entry exists."""
    s = persona.slot(slot_id)
    head, rest = orig_user.split("[Lookup]", 1)
    if memory_has_answer(head, s):
        return orig_user
    hit = next(((d, t) for (d, _, ref, t) in prior_entries if norm(ref) == norm(s["ref"])), None)
    if hit is None:
        return None
    mem = head.replace("[Memory]\n", "").strip()
    lines = [] if mem == "none" else mem.split("\n")
    lines = [f"- (day {hit[0]}) {hit[1]}"] + lines
    return "[Memory]\n" + "\n".join(lines[:3]) + "\n[Lookup]" + rest


def night_material(n, diary, tags, persona, phr, reqs, bos):
    """Everything night n can use, before budgeting: one pass of shared items (facts + corrected actions) and the slice candidates."""
    from .slot_memory import entries_from_diary_rows
    rows = diary[n]
    gs = groups(rows)
    day_tags = [t for t in tags if t["day"] == n]
    ns = night_scale()
    regret = shrink(sorted((t for t in day_tags if t["type"] == "regret"), key=lambda t: t["req_id"]), ns)
    annoy = shrink(sorted((t for t in day_tags if t["type"] == "annoyance"), key=lambda t: t["req_id"]), ns)
    prior_entries = [e for dd in sorted(diary) if dd < n for e in entries_from_diary_rows(diary[dd])]
    learned = []  # slots Ben answered or corrected today
    for (d_, k_, ref_, t_) in entries_from_diary_rows(rows):
        sid = persona.ref_to_slot.get(norm(ref_))
        if sid and sid not in learned:
            learned.append(sid)
    learned = shrink(learned, ns)
    fact_ids = [r["meta"]["fact_id"] for r in shrink([r for r in rows if r["meta"].get("kind") == "fact"], ns)]

    def shared_pass(k):
        """k-th pass over the shared items: fact paraphrases rotate through the 8 pre-written ones, corrected actions are the same."""
        out = []
        for sid in learned:
            ps = phr["slots"][sid]["paraphrases"]
            out += [fact_item(bos, ps[(SHARED_PARA * k + j) % len(ps)]) for j in range(SHARED_PARA)]
        for fid in fact_ids:
            ps = phr["facts"][fid]
            out += [fact_item(bos, ps[(SHARED_PARA * k + j) % len(ps)]) for j in range(SHARED_PARA)]
        for t in regret:
            out.append(sft_action(bos, gs[t["req_id"]][0]["meta"]["prompt_user"], act_text(reqs[t["req_id"]]["gold"]), "corr_action"))
        return out
    pairs, chosen_sft, topup = [], [], []
    dropped = set()  # regret events whose original [Memory] already showed the answer: a copy failure, not 'should have asked'; out of the slice for ALL arms
    for t in regret + annoy:
        req, g = reqs[t["req_id"]], gs[t["req_id"]]
        move_row = next(x for x in g if x["role"] == "assistant")
        orig_user = g[0]["meta"]["prompt_user"]
        sid = persona.ref_to_slot.get(norm(t["slot_ref"] or ""))
        sys_user = lambda u: render([{"role": "system", "content": SYSTEM}, {"role": "user", "content": u}], True, bos)  # noqa: E731
        if t["type"] == "regret":
            if not sid:
                continue
            if memory_has_answer(orig_user.split("[Lookup]")[0], persona.slot(sid)):
                dropped.add(t["req_id"])
                continue
            qs = phr["slots"][sid]["questions"]
            q = "ASK " + qs[crc(t["req_id"], sid) % len(qs)]
            pairs.append({"kind": "pair", "prompt": sys_user(orig_user), "chosen": q + END, "rejected": move_row["text"].strip() + END, "src": "regret", "slot": sid, "req_id": t["req_id"]})
            chosen_sft.append(sft_action(bos, orig_user, q, "chosen_q") | {"slot": sid, "req_id": t["req_id"]})
            topup.append(sft_action(bos, orig_user, act_text(req["gold"]), "topup_action") | {"slot": sid, "req_id": t["req_id"]})
        else:
            prompt_user = user_content_with_answer(persona, req, orig_user, sid, prior_entries) if sid else orig_user
            if prompt_user is None:
                continue
            act = act_text(req["gold"])
            pairs.append({"kind": "pair", "prompt": sys_user(prompt_user), "chosen": act + END, "rejected": move_row["text"].strip() + END, "src": "annoyance", "slot": sid, "req_id": t["req_id"]})
            chosen_sft.append(sft_action(bos, prompt_user, act, "chosen_act") | {"slot": sid, "req_id": t["req_id"]})
            topup.append(sft_action(bos, prompt_user, act, "topup_action") | {"slot": sid, "req_id": t["req_id"]})
    pairs.sort(key=lambda x: crc("order", x["req_id"]))  # deterministic, not biased to early request ids
    topup_facts = []
    for t in regret + annoy:
        sid = persona.ref_to_slot.get(norm(t["slot_ref"] or ""))
        if sid and t["req_id"] not in dropped:
            ps = phr["slots"][sid]["paraphrases"]
            topup_facts += [fact_item(bos, ps[j]) | {"src": "topup_fact", "slot": sid} for j in range(len(ps))]
    return {"shared_pass": shared_pass, "pairs": pairs, "chosen_sft": chosen_sft, "topup": topup, "topup_facts": topup_facts,
            "n_regret_dropped_memory_has_answer": len(dropped), "n_regret": len(regret), "n_annoy": len(annoy), "n_learned": len(learned)}


def auto_repeat(mats, length_fn, n_opt, a_len, cap=20):
    """Passes over the shared items per night, one number for all nights and arms: big enough that ALL of a typical night's pairs fit in the 15% slice."""
    need = []
    for m in mats.values():
        once = sum(CL.total([CL.item_units(i, length_fn)]) for i in m["shared_pass"](0))
        pu = sum(CL.total([CL.item_units(i, length_fn)]) for i in m["pairs"])
        anchor = CL.anchor_units(n_opt, a_len)
        anchor = anchor["train"] + anchor["ref"]
        if once > 0:
            need.append(max(1.0, (pu * (1 - SLICE_FRAC) / SLICE_FRAC - anchor) / once))
    need.sort()
    return int(min(cap, max(1, math.ceil(need[len(need) // 2])))) if need else 1


def build(diary_dir, tags, tokenizer, out_dir, persona=None, phr=None, requests=None, nights=None, log=print, repeat=None):
    persona = persona or Persona.load()
    phr = phr or jload(DATA / "phrasings.json")
    reqs = {r["req_id"]: r for r in (requests or load_requests())}
    bos = tokenizer.bos_token or ""
    out_dir = Path(out_dir)
    diary = {}
    for p in sorted(Path(diary_dir).glob("day*.jsonl"), key=lambda p: int(re.findall(r"\d+", p.name)[0])):
        diary[int(re.findall(r"\d+", p.name)[0])] = jl_read(p)

    def length_fn(prompt, target):
        return min(1024, len(tokenizer(prompt, add_special_tokens=False).input_ids) + len(tokenizer(target, add_special_tokens=False).input_ids))

    anchors = [render(general_messages(p), True, bos) for p in phr["general"][:N_ANCHOR]]
    a_len = int(sum(len(tokenizer(a, add_special_tokens=False).input_ids) for a in anchors) / len(anchors))
    n_opt = night_opt_steps()
    nn = list(range(1, (nights or n_nights()) + 1))
    mats = {n: night_material(n, diary, tags, persona, phr, reqs, bos) for n in nn}
    rep = repeat or int(os.environ.get("ASKONCE_REPEAT", "0")) or auto_repeat(mats, length_fn, n_opt, a_len)
    log(f"shared passes per night (repeat) = {rep}")
    plan = {}
    scan_texts = set()
    for n in nn:
        m = mats[n]
        shared = [i for k in range(rep) for i in m["shared_pass"](k)]
        base = CL.night_ledger(shared, [], n_opt, a_len, length_fn, 0)
        target = SLICE_FRAC / (1 - SLICE_FRAC) * (base["shared"] + base["anchor"])
        b_items, used = [], 0
        for pr in m["pairs"]:
            u = CL.total([CL.item_units(pr, length_fn)])
            if used + u > target:  # the slice never exceeds 15% of the night
                continue
            b_items.append(pr)
            used += u
        calls = sum(1 for x in b_items if x["src"] == "regret")
        ids = {x["req_id"] for x in b_items}

        def fill(cands, need):
            out, u, i = [], 0, 0
            while cands and u < need and i < 50000:
                it = cands[i % len(cands)]
                out.append(it)
                u += CL.total([CL.item_units(it, length_fn)])
                i += 1
            return out
        slots_in_slice = {x["slot"] for x in b_items}
        aplus_pool = [c for c in m["topup"] if c["req_id"] in ids] + [f for f in m["topup_facts"] if f["slot"] in slots_in_slice]
        arms = {"B": b_items, "B-sft": fill([c for c in m["chosen_sft"] if c["req_id"] in ids], used), "A+": fill(aplus_pool, used)}
        per_arm = {a: CL.night_ledger(shared, items, n_opt, a_len, length_fn, calls) for a, items in arms.items()}
        sp = CL.assert_equal(per_arm, LEDGER_TOL, f"night {n}")
        for a, items in arms.items():
            jl_write(out_dir / "nights" / a / f"night{n}.jsonl", shared + items)
            for it in shared + items:
                scan_texts.update([it["prompt"], it.get("target") or it["chosen"]])
        plan[n] = {"n_regret_dropped_memory_has_answer": m["n_regret_dropped_memory_has_answer"], "per_arm": per_arm, "spread": round(sp, 4), "n_regret_tagged": m["n_regret"], "n_annoy_tagged": m["n_annoy"], "n_learned_slots": m["n_learned"],
                   "slice_target": round(target), "n_pairs_in_B": len(b_items), "n_pairs_available": len(m["pairs"]), "repeat": rep,
                   "B_slice_share": round(per_arm["B"]["slice"] / per_arm["B"]["total"], 4)}
        log(f"night {n}: shared={len(shared)} items, regret={m['n_regret']} (dropped, memory had answer: {m['n_regret_dropped_memory_has_answer']}) annoy={m['n_annoy']}, B pairs={len(b_items)}/{len(m['pairs'])}, "
            f"slice={100 * plan[n]['B_slice_share']:.1f}%, spread={100 * sp:.2f}%")
    # leakage guard on what is actually trained on (prompts incl. [Lookup]/[Memory], targets). Model-written text (memory 'asked ...' lines) can add hits; they are recorded, not fatal.
    from .leakscan import scan
    leaks = [list(h[:3]) + [h[3][:80]] for h in scan(persona, [("night-file", t) for t in sorted(scan_texts)])]
    if leaks:
        log(f"WARNING: {len(leaks)} new-slot words in the night files: {leaks[:5]}")
    jdump(out_dir / "plan.json", {"leak_hits_in_night_files": leaks, "nights": plan, "n_opt_steps": n_opt, "anchor_len": a_len, "tol": LEDGER_TOL, "slice_frac": SLICE_FRAC, "repeat": rep})
    jl_write(out_dir / "anchors.jsonl", [{"prompt": a} for a in anchors])
    build_eval_inputs(persona, diary_dir, bos, out_dir, requests=list(reqs.values()), log=log)
    return plan


def build_eval_inputs(persona, diary_dir, bos, out_dir, requests=None, log=print):
    """Eval prompts for days 6-7 with the FINAL slot memory (days 1-5) inside, identical for every arm; plus fact questions."""
    mem = memory_from_diary(diary_dir)
    refs_in_mem = {norm(r) for (_, _, r, _) in [(0, 0, e[2], 0) for e in mem.db.execute("select day, kind, ref, text from m").fetchall()]}
    rows = []
    for r in (requests or load_requests()):
        if r["day"] < 6:
            continue
        ml = mem.retrieve(r["text"] + " " + " ".join(persona.slot(s)["ref"] for s in r["slots"]))
        msgs = first_messages(persona, r, ml)
        know_eff = bool(r["slots"]) and all(norm(persona.slot(s)["ref"]) in refs_in_mem for s in r["slots"])
        rows.append({"req_id": r["req_id"], "split": r["split"], "prompt": render(msgs, True, bos), "gold": r["gold"], "slots": r["slots"],
                     "underspecified": r["underspecified"], "knowable_effective": know_eff, "memory": ml, "text": r["text"], "day": r["day"]})
    jl_write(out_dir / "eval_inputs.jsonl", rows)
    qs = []
    for s in persona.slots.values():
        qs.append({"id": s["slot_id"], "q": s["recall_q"], "a": s["recall_a"], "taught": norm(s["ref"]) in refs_in_mem})
    for f in persona.facts.values():
        qs.append({"id": f["fact_id"], "q": f["recall_q"], "a": f["recall_a"], "taught": True})
    jdump(out_dir / "fact_questions.json", qs)
    eff = {sp: sum(1 for x in rows if x["split"] == sp and x["knowable_effective"]) for sp in ("H_know", "R_know")}
    log(f"eval inputs: {len(rows)} items; knowable slots actually in memory: {eff}")
    jdump(out_dir / "eval_stats.json", {"knowable_effective": eff, "n": len(rows)})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--diary", required=True)
    ap.add_argument("--tags", required=True)
    ap.add_argument("--tokenizer", default="IFM/K2-Horizon-3.7B")
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-events", type=float, default=5.0, help="gate after job 1: mean tagged regret+annoyance events per night (prereg Step 0 threshold)")
    ap.add_argument("--force", action="store_true", help="build the files even when the gate fails (they are NOT to be sent to job 2 then)")
    a = ap.parse_args()
    from .model_io import get_tokenizer
    plan = build(a.diary, jl_read(a.tags), get_tokenizer(a.tokenizer), a.out)
    ev = sum(v["n_regret_tagged"] + v["n_annoy_tagged"] for v in plan.values()) / max(1, len(plan))
    print(f"tagged events per night (mean): {ev:.1f}")
    if ev < a.min_events:
        msg = f"GATE FAILED: {ev:.1f} tagged events per night on average (< {a.min_events}); too few pairs for the test to have power. Do not run job 2."
        if not a.force:
            raise SystemExit(msg)
        print("WARNING (forced):", msg)


if __name__ == "__main__":
    main()
