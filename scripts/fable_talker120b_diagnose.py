#!/usr/bin/env python3
"""Experiment 120b STEP 1 — diagnose the 313 unfaithful raw decodes.

Re-decodes all 500 held-out records with the director's seed-12002 checkpoint
on the Mac CPU (imports TalkerMouth/brake_check/serialize/Codec from
fable_talker120_mouth; no model change), then buckets every unfaithful raw
decode:

  boundary-only     raw starts with a junk prefix (":" / "ing" fragment) and
                    every gold name/answer is intact as a whole word
  truncation-only   no junk prefix, but a gold name/answer is missing/mangled
  both              junk prefix AND a missing/mangled gold name/answer
  other             neither (e.g. leaked prefix-marker words like "source")

Plus, per record: (a) token-by-token check that the decode prompt equals the
training serialisation; (b) which target positions the training loss mask
covers; (c) tokenizer pieces of the gold names; (d) for truncation cases, the
copy head's top-attended prefix tokens at the first wrong step.

Usage (Mac):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B scripts/fable_talker120b_diagnose.py \
    --data artifacts/fable-talker120-20260922/data \
    --ckpt artifacts/claude-talker120-run-20260922/fable_talker120_ckpt_last.pt \
    --tok artifacts/fable-talker101-20260921/fable_talker101_tokenizer.json \
    --out artifacts/fable-talker120b-20260922/diag.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from fable_talker120_mouth import (  # noqa: E402
    Codec,
    TalkerMouth,
    brake_check,
    serialize,
)

JUNK_RE = re.compile(r"\s*([^A-Za-z\s])")


def junk_flag(raw: str) -> tuple[bool, str]:
    """Boundary junk: the first content char is ':' or a lowercase letter.
    Every training template starts uppercase, so a lowercase/colon start is a
    fragment from the unsupervised first decode step, never a valid start."""
    m = re.match(r"\s*(.)", raw or "", re.DOTALL)
    if not m:
        return True, "empty"
    ch = m.group(1)
    if ch == ":":
        return True, ":"
    if ch.islower():
        frag = re.match(r"\s*([a-z]+)", raw or "").group(1)
        return True, frag
    return False, ""


def required_words(rec: dict) -> list[str]:
    """Words the sentence MUST contain, given the status template slots
    (fable_talker120_data.render): owner chain + answer for OK/SAVED,
    subject + surface relation for UNKNOWN/FORGOT, name + choice names for
    CLARIFY, none for ABSTAIN. Intermediate hop chains are NOT rendered for
    UNKNOWN/FORGOT/CLARIFY and must not count as truncation."""
    status = rec.get("status")
    fields = rec.get("fields") or {}
    items: list[str] = []
    if status in ("OK", "SAVED"):
        items = [str(rec.get("name", ""))] + \
            [str(r).replace("_", " ") for r in (rec.get("relations") or [])] + \
            [str(fields.get("answer", ""))]
    elif status in ("UNKNOWN", "FORGOT"):
        items = [str(fields.get("subject", "")),
                 str(fields.get("relation", "")).replace("_", " ")]
    elif status == "CLARIFY":
        items = [str(fields.get("name", "")),
                 str(fields.get("choices", ""))]
    out: list[str] = []
    for g in items:
        out.extend(w for w in re.findall(r"[A-Za-z]{3,}", g))
    return out


def gold_items(rec: dict) -> list[str]:
    out: list[str] = []
    if rec.get("name"):
        out.append(str(rec["name"]))
    for r in rec.get("relations") or []:
        out.append(str(r).replace("_", " "))
    for key in ("answer", "subject", "relation", "value", "name", "choices"):
        val = (rec.get("fields") or {}).get(key)
        if val is None or val == "":
            continue
        if isinstance(val, (list, tuple)):
            out.extend(str(i) for i in val)
        else:
            out.append(str(val).replace("_", " "))
    # split choices "A (E0001), B (E0002)" into bare names too
    extra: list[str] = []
    for g in out:
        extra.extend(re.findall(r"[A-Za-z]+", g))
    return [g for g in out if g] + extra


def trunc_flag(raw: str, rec: dict) -> tuple[bool, list[str]]:
    """True if some REQUIRED word (>=3 letters) has no whole-word match in raw.
    Whole-word = not followed by another lowercase letter, so "Amos" matches
    "Amos's" but NOT "Amosos's" (mangled), and "Farah" misses "Fara"."""
    missing: list[str] = []
    seen: set[str] = set()
    for w in required_words(rec):
        wl = w.lower()
        if wl in seen:
            continue
        seen.add(wl)
        if not re.search(r"(?i)" + re.escape(w) + r"(?![a-z])", raw):
            missing.append(w)
    return (len(missing) > 0, missing)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--tok", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-new", type=int, default=32)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--attn-cases", type=int, default=8,
                    help="how many truncation cases get copy-attention probes")
    args = ap.parse_args(argv)

    rows = [json.loads(x) for x in
            (Path(args.data) / "heldout.jsonl").read_text(encoding="utf-8")
            .splitlines() if x]
    if args.limit is not None:
        rows = rows[:args.limit]

    import torch

    torch.set_num_threads(1)
    mouth = TalkerMouth(args.ckpt, args.tok)
    model, codec = mouth._load()

    # (a) prompt-vs-training check on every record: decode prompt ids must
    # equal codec.encode(serialize(record)) used by fable_talker120_train.
    # encode_pair (train.py:43-51) builds ids = pre + tgt with
    # tgt = encode(" " + sentence) + [eos].
    prompt_mismatch = 0
    # (b) mask audit on one OK pair: which target positions get loss under
    # train.py:150-151  tgt_mask = (pos > pre) & (pos <= len).
    mask_report: dict = {}
    buckets = {"boundary-only": 0, "truncation-only": 0, "both": 0, "other": 0}
    records_out: list[dict] = []
    junk_prefixes: dict[str, int] = {}
    other_examples: list[dict] = []
    trunc_examples: list[dict] = []
    t0 = time.time()
    for i, row in enumerate(rows):
        rec = row["record"]
        pre = codec.encode(serialize(rec))
        cur = list(pre)
        if cur != pre:
            prompt_mismatch += 1
        raw, pgs = mouth._decode_raw(rec, args.max_new)
        ok, reason = brake_check(raw, rec) if raw else (False, "empty")
        entry: dict = {"idx": i, "status": rec["status"], "raw": raw,
                       "reference": row.get("reference"),
                       "brake_ok": ok, "brake_reason": reason}
        if i == 0:
            # mask audit with this record's reference sentence
            from fable_talker120_train import encode_pair  # noqa

            ids, plen = encode_pair(codec, rec, row["reference"], 256)
            T = len(ids)
            masked = [p for p in range(1, T)
                      if (p > plen) and (p <= len(ids))]
            mask_report = {
                "prefix_len": plen, "seq_len": len(ids),
                "first_target_index": plen,
                "first_target_covered": plen in masked,
                "masked_positions": masked[:8],
                "n_masked": len(masked),
                "n_target_tokens": len(ids) - plen,
            }
        if not ok:
            junk, frag = junk_flag(raw or "")
            if junk:
                junk_prefixes[frag] = junk_prefixes.get(frag, 0) + 1
            tr, missing = trunc_flag(raw or "", rec)
            if junk and not tr:
                b = "boundary-only"
            elif tr and not junk:
                b = "truncation-only"
            elif junk and tr:
                b = "both"
            else:
                b = "other"
            buckets[b] += 1
            entry["bucket"] = b
            entry["junk"] = junk
            entry["missing_gold"] = missing
            if b == "other" and len(other_examples) < 25:
                other_examples.append(
                    {"idx": i, "status": rec["status"], "raw": raw,
                     "reference": row.get("reference"), "reason": reason})
            if tr and len(trunc_examples) < 25:
                trunc_examples.append(
                    {"idx": i, "status": rec["status"], "raw": raw,
                     "reference": row.get("reference"),
                     "missing": missing})
        records_out.append(entry)
        if (i + 1) % 100 == 0:
            print(json.dumps({"done": i + 1, "buckets": buckets,
                              "seconds": round(time.time() - t0, 1)}),
                  flush=True)

    # (d) copy-attention probes on the first few truncation cases
    attn_probes: list[dict] = []
    for ex in trunc_examples[:args.attn_cases]:
        rec = rows[ex["idx"]]["record"]
        pre_ids = codec.encode(serialize(rec))
        pre_toks = [codec.id2tok.get(t, "?") for t in pre_ids]
        cur = list(pre_ids)
        gold_words = ex["missing"]
        # step greedily until the raw diverges from containing gold, or 12 steps
        steps: list[dict] = []
        with torch.inference_mode():
            for s in range(12):
                x = torch.tensor(cur, dtype=torch.long).unsqueeze(0)
                out = model(x)
                logits = out["logits"][0, -1]
                pv = torch.softmax(logits, dim=-1)
                pg = float(out["p_gen"][0, -1, 0])
                attn = out["copy_attn"][0, -1, :len(cur)]
                mix = pg * pv.clone()
                cw = (1.0 - pg) * attn
                for k, tid in enumerate(cur):
                    mix[int(tid)] += float(cw[k])
                nxt = int(torch.argmax(mix).item())
                top = torch.topk(attn, min(3, len(cur)))
                steps.append({
                    "step": s, "p_gen": round(pg, 3),
                    "emit": codec.decode([nxt]),
                    "top_attn": [
                        {"tok": pre_toks[i] if i < len(pre_toks)
                         else codec.decode([cur[i]]),
                         "w": round(float(w), 3)}
                        for i, w in zip(top.indices.tolist(),
                                        top.values.tolist())],
                })
                if nxt == codec.eos:
                    break
                cur.append(nxt)
        attn_probes.append({"idx": ex["idx"], "missing": gold_words,
                            "prefix_tail": pre_toks[-8:], "steps": steps})

    # (e) first-token counterfactual: force the reference's first target token,
    # then continue greedy. If the tail becomes faithful, mid-sentence
    # mangling is downstream of the unsupervised first step (one training
    # bug); if not, truncation is an independent defect.
    force_fixed = force_total = 0
    force_examples: list[dict] = []
    junk_cases = [e for e in records_out
                  if not e["brake_ok"] and e.get("junk")]
    for e in junk_cases[:12]:
        row = rows[e["idx"]]
        rec = row["record"]
        try:
            first_tok = codec.encode(" " + row["reference"])[0]
        except Exception:  # noqa
            continue
        cur = codec.encode(serialize(rec)) + [first_tok]
        new: list[int] = [first_tok]
        with torch.inference_mode():
            for _ in range(args.max_new - 1):
                x = torch.tensor(cur, dtype=torch.long).unsqueeze(0)
                out = model(x)
                logits = out["logits"][0, -1]
                pv = torch.softmax(logits, dim=-1)
                pg = float(out["p_gen"][0, -1, 0])
                attn = out["copy_attn"][0, -1, :len(cur)]
                mix = pg * pv.clone()
                cw = (1.0 - pg) * attn
                for k, tid in enumerate(cur):
                    mix[int(tid)] += float(cw[k])
                nxt = int(torch.argmax(mix).item())
                if nxt == codec.eos:
                    break
                cur.append(nxt)
                new.append(nxt)
                if len(cur) >= 508:
                    break
        forced = codec.decode(new).strip().split("\n")[0].strip()
        good, _ = brake_check(forced, rec)
        force_total += 1
        force_fixed += int(good)
        if len(force_examples) < 8:
            force_examples.append(
                {"idx": e["idx"], "raw": e["raw"], "forced": forced,
                 "faithful": good, "reference": row.get("reference")})

    # (c) tokenizer pieces of every distinct missing gold name
    codec2 = codec
    pieces: dict[str, list[str]] = {}
    for ex in trunc_examples:
        for w in ex["missing"]:
            if w not in pieces:
                for ctx in (" " + w, " " + w + "'s", w):
                    try:
                        ids = codec2.encode(ctx)
                        toks = [codec2.id2tok[i] for i in ids]
                    except Exception as e:  # noqa
                        toks = [f"ERR {e}"]
                    pieces.setdefault(w, []).append({"ctx": ctx, "toks": toks})

    result = {
        "records": len(rows),
        "unfaithful": sum(buckets.values()),
        "buckets": buckets,
        "junk_prefixes": junk_prefixes,
        "prompt_mismatch": prompt_mismatch,
        "mask_report": mask_report,
        "pieces": pieces,
        "other_examples": other_examples,
        "trunc_examples": trunc_examples,
        "attn_probes": attn_probes,
        "force_fixed": force_fixed,
        "force_total": force_total,
        "force_examples": force_examples,
        "records": records_out,
        "seconds": round(time.time() - t0, 2),
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items()
                      if k not in ("other_examples", "trunc_examples",
                                   "attn_probes", "pieces",
                                   "force_examples", "records")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
