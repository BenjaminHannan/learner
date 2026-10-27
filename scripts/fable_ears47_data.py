#!/usr/bin/env python3
"""Rung 2 of design 47 -- frame golds, panels, relation classes, training pool.

    python fable_ears47_data.py --build   # panels + class list into the artifact dir
    python fable_ears47_data.py --report  # counts used to seal PASSMARKS.md
    python fable_ears47_data.py --pool OUT.jsonl   # mixed training pool

Frame schema (Ben's spec 47): act in {STATE, ASK, RETRACT, UNSURE, NO_FACT}; relation =
WebRED train relations + our closed 40 + OPEN + UNSURE; subject/object char-span pointers;
direction FORWARD iff subject starts at/before object; confidence = min over heads at decode.

Rung-1 example -> frame gold (registered interpretations, sealed in PASSMARKS):
  teach/correct (always 1 hop) -> STATE   ask (1 hop) -> ASK   ask (>=2 hops) -> UNSURE
  forget -> RETRACT   quote/hearsay/hypo/negation -> NO_FACT   smalltalk -> NO_FACT
  unsure/multi/leftover/gibberish/pronoun -> UNSURE
  person, alias -> UNSURE (not expressible in the frame schema; abstain)
  trap.stmtq (gold ask, 1 hop) -> ASK
Relation class: known key -> that class; open nouns -> OPEN.
Additive only: imports fable_ears45_* and fable_listening_english READ-ONLY; the hearsay
marker list is extended additively in THIS process (never editing the source file).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fable_listening_english as LE            # read-only (+ additive marker append below)
import fable_ears45_data as D                   # read-only

# ---------------------------------------------------------------- additive hearsay markers
# fable_listening_english's list lacks these (doc 48 repo map).  Extended ADDITIVELY here.
EXTENDED_HEARSAY = (" rumour has it ", " word is ", " supposedly ", " allegedly ",
                    " people say ")


def extend_markers() -> None:
    base = list(LE.REPORTED_SPEECH_MARKERS)          # may be a tuple; rebind additively
    for m in EXTENDED_HEARSAY:
        if m not in base:
            base.append(m)
    LE.REPORTED_SPEECH_MARKERS = base


extend_markers()

_LOAD_ALL = None
_PANEL_CACHE: dict = {}


def load_all_cached():
    global _LOAD_ALL
    if _LOAD_ALL is None:
        _LOAD_ALL = D.load_all()
    return _LOAD_ALL


def snapshot_dir(explicit: str | None = None) -> str:
    if explicit:
        return explicit
    from huggingface_hub import snapshot_download
    return snapshot_download("allenai/scibert_scivocab_uncased",
                             allow_patterns=["*.json", "*.txt", "*.bin"])

ARTIFACT = Path(__file__).resolve().parent.parent / "artifacts" / "fable-ears47-20260921"
WEBRED = Path(__file__).resolve().parent.parent / "data" / "open" / "webred" / "frames"
FORMAT = "fable-ears47/rung2/1"
MAX_LEN = 96
MAX_SPAN_WP = 12                 # wordpieces, subject/object span cap
ACTS = ["STATE", "ASK", "RETRACT", "UNSURE", "NO_FACT"]
ACT_INDEX = {a: i for i, a in enumerate(ACTS)}
DIR_FORWARD, DIR_REVERSE = 0, 1
POOL_SEED = 47100
POOL_SYNTH = 60000
NEWREL_N = 1500
PERSON_CLASSES = set(D.PERSON_KEYS) | {"mother", "father", "child", "sibling", "spouse",
                                       "place of birth", "educated at"}


# --------------------------------------------------------------------- relation classes
def webred_meta() -> dict:
    return json.loads((WEBRED / "relations.json").read_text(encoding="utf-8"))


def build_classes() -> dict:
    """closed list = WebRED train relations + our 40 keys + OPEN + UNSURE (spec 47 §2)."""
    meta = webred_meta()
    held = set(meta["heldout"])
    train_rels = {r for r in meta["counts"] if r not in held}
    assert len(train_rels) == 481, len(train_rels)
    closed40 = set(D.ALL_KEYS)
    rels = sorted(train_rels | closed40)
    classes = rels + ["OPEN", "UNSURE"]
    return {"classes": classes,
            "OPEN": len(classes) - 2, "UNSURE": len(classes) - 1,
            "n": len(classes),
            "webred_train": sorted(train_rels),
            "closed40": sorted(closed40),
            "heldout": sorted(held),
            "closed_map": meta["closed_map"]}


CLASSES = build_classes()
REL_INDEX = {r: i for i, r in enumerate(CLASSES["classes"])}
OPEN_I, UNSURE_I = CLASSES["OPEN"], CLASSES["UNSURE"]
N_REL = CLASSES["n"]


def rel_class(key: str | None) -> int:
    if key is None:
        return UNSURE_I
    return REL_INDEX.get(key, OPEN_I)


# ------------------------------------------------------------------------- gold frames
def _dir_of(subj_chars, obj_chars) -> int:
    if not subj_chars or not obj_chars:
        return DIR_FORWARD
    return DIR_FORWARD if subj_chars[0] <= obj_chars[0] else DIR_REVERSE


def gold_from_synth(ex: dict) -> dict:
    """rung-1 generated example -> registered frame gold (see module docstring)."""
    act = ex["act"]
    fam = ex["family"]
    slots = ex.get("slots") or {}
    hops = ex.get("hop_keys") or []
    if act in ("teach", "correct"):
        new_act, representable = "STATE", True
    elif act == "ask":
        representable = len(hops) == 1
        new_act = "ASK" if representable else "UNSURE"
    elif act == "forget":
        new_act, representable = "RETRACT", True
    elif act == "quote":
        new_act, representable = "NO_FACT", False
    elif act == "smalltalk":
        new_act, representable = "NO_FACT", False
    elif act in ("unsure", "multi"):
        new_act, representable = "UNSURE", False
    elif act == "person":
        new_act, representable = "UNSURE", False      # schema cannot express person-ness
    elif act == "alias":
        new_act, representable = "UNSURE", False      # schema cannot express aliases
    else:
        new_act, representable = "UNSURE", False
    if fam == "trap.leftover":
        new_act, representable = "UNSURE", False
    g = {"act": new_act, "rel": None, "subj": None, "obj": None, "dir": DIR_FORWARD,
         "rep": representable}
    if not representable:
        g["rel"] = "UNSURE"
        return g
    key = hops[0] if hops else None
    g["rel"] = key if key in REL_INDEX else "OPEN"
    g["subj"] = list(slots["SUBJ"]) if "SUBJ" in slots else None
    if new_act == "STATE":
        g["obj"] = list(slots["VAL"]) if "VAL" in slots else None
        if g["subj"] is None or g["obj"] is None:
            g.update(act="UNSURE", rep=False, rel="UNSURE", subj=None, obj=None)
            return g
    g["dir"] = _dir_of(g["subj"], g["obj"])
    return g


def gold_from_webred(row: dict) -> dict:
    if not row["positive"]:
        return {"act": "NO_FACT", "rel": "UNSURE", "subj": None, "obj": None,
                "dir": DIR_FORWARD, "rep": False}
    rel = row["relation"]
    g = {"act": "STATE", "rel": rel if rel in REL_INDEX else "OPEN",
         "subj": list(row["subj"]), "obj": list(row["obj"]),
         "dir": _dir_of(row["subj"], row["obj"]), "rep": True}
    return g


# ------------------------------------------------------------------------- char spans
def char_span_to_wp(chspans, max_len, s, e):
    """gold char span -> (start_wp, end_wp) indices inside the WordPiece sequence.

    chspans: per-token (char_start, char_end) from WordPiece.encode, index 0 = [CLS].
    Returns None when the span is not fully covered (truncation / empty overlap).
    """
    last = max_len - 1                          # [SEP] sits at len(ids)-1; caller clamps
    start = end = None
    for i in range(1, len(chspans) - 1):        # skip CLS and SEP
        a, b = chspans[i]
        if b <= s or a >= e:
            continue
        if b - a == 0:
            continue
        if start is None:
            start = i
        end = i
    if start is None or end is None or start > end:
        return None
    return [start, end]


# ------------------------------------------------------------------------------ panels
def synth_panel(name: str) -> list[dict]:
    if name in _PANEL_CACHE:
        return _PANEL_CACHE[name]
    rows = D.make_panel(load_all_cached()[3], name)
    out = []
    for ex in rows:
        out.append({**ex, "source": "synth", "gold47": gold_from_synth(ex)})
    _PANEL_CACHE[name] = out
    return out


def row_text(row: dict) -> str:
    return row.get("text") or row.get("utterance") or ""


def strip_rung1_sha(rows) -> str:
    """Hash under rung-1 FORMAT with gold47/source stripped (identity vs ears45 shas)."""
    h = hashlib.sha256(D.FORMAT.encode())
    for r in rows:
        rr = {k: v for k, v in r.items() if k not in ("gold47", "source")}
        h.update(("\n" + json.dumps(rr, sort_keys=True, ensure_ascii=False)).encode())
    return h.hexdigest()


def _webred_rows(path: Path):
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            yield json.loads(line)


def webred_panel(name: str, rows: list[dict]) -> list[dict]:
    out = []
    for i, r in enumerate(rows):
        out.append({"n": i + 1, "source": "webred", "text": r["text"],
                    "positive": r["positive"], "relation": r["relation"],
                    "relation_id": r.get("relation_id"),
                    "subj_chars": r["subj"], "obj_chars": r["obj"],
                    "subj_name": r.get("subj_name"), "obj_name": r.get("obj_name"),
                    "family": "webred." + ("pos" if r["positive"] else "neg"),
                    "gold47": gold_from_webred(r)})
    return out


def newrel_panel() -> list[dict]:
    """1500 held-out-relation positives, hash-ranked (deterministic), spec 47 §6."""
    held = set(CLASSES["heldout"])
    cands = [r for r in _webred_rows(WEBRED / "heldout.jsonl")
             if r["positive"] and r["relation"] in held]
    cands.sort(key=lambda r: hashlib.sha256(
        (FORMAT + "|newrel|" + r["text"]).encode()).hexdigest())
    return webred_panel("wnewrel", cands[:NEWREL_N])


def panel_sha(rows) -> str:
    h = hashlib.sha256(FORMAT.encode())
    for r in rows:
        h.update(("\n" + json.dumps(r, sort_keys=True, ensure_ascii=False)).encode())
    return h.hexdigest()


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    shas = {}
    for name in ("cal", "t_seen", "t_new", "t_far", "t_trap", "t_hard"):
        rows = synth_panel(name)
        p = out_dir / f"{name}.json"
        p.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        shas[name] = file_sha(p)
    dev = [r for r in _webred_rows(WEBRED / "dev.jsonl")]
    neg = [r for r in dev if not r["positive"]]
    pos = [r for r in dev if r["positive"]]
    closed_map = CLASSES["closed_map"]
    wclosed = [r for r in pos if r["relation"] in closed_map]
    for name, rows in (("wneg", neg), ("wpos", pos), ("wclosed", wclosed),
                       ("wnewrel", newrel_panel())):
        p = out_dir / f"{name}.json"
        p.write_text(json.dumps(rows if name == "wnewrel" else
                                webred_panel(name, rows),
                                ensure_ascii=False, indent=1), encoding="utf-8")
        shas[name] = file_sha(p)
    (out_dir.parent / "relation_classes.json").write_text(
        json.dumps(CLASSES, indent=1), encoding="utf-8")
    return shas


# ------------------------------------------------------------------------- train pool
def _wp_encode(tok, text, max_len=MAX_LEN):
    ids, chspans = tok.encode(text, max_len)
    return ids, chspans


def synth_pool_rows(tok, rng: random.Random, n=POOL_SYNTH):
    split, pools, lex, gen = load_all_cached()
    prng = random.Random(POOL_SEED)                # same pool sentences as rung 1
    out = []
    while len(out) < n:
        fam = D._pick_family(prng, {f.family for f in split.frames("train")})
        hops = None
        if fam.startswith("ask."):
            r, acc = prng.random(), 0.0
            for h, w in D.ASK_HOPS:
                acc += w
                if r <= acc:
                    hops = h
                    break
            hops = hops or 1
        try:
            ex = gen.sample(prng, "train", "train", "train", False, [fam], False, hops)
        except (KeyError, IndexError):
            continue
        if len(D.tokenise(ex["utterance"])) > D.MAX_TOKENS:
            continue
        g = gold_from_synth(ex)
        text = ex["utterance"]
        # additive training-only hearsay augmentation: prepend an extended marker to a
        # statement and the gold becomes NO_FACT (the sentence no longer states it).
        # Glue is a single space so padded " marker " matches flags_of and LE's guard.
        if g["act"] == "STATE" and rng.random() < 0.10:
            marker = rng.choice(EXTENDED_HEARSAY).strip()
            text = marker + " " + text
            g = {"act": "NO_FACT", "rel": "UNSURE", "subj": None, "obj": None,
                 "dir": DIR_FORWARD, "rep": False}
        out.append({"text": text, "source": "synth", "gold47": g})
    return out


def webred_pool_rows():
    for r in _webred_rows(WEBRED / "train.jsonl"):
        yield {"text": r["text"], "source": "webred", "gold47": gold_from_webred(r),
               "subj_chars": r["subj"], "obj_chars": r["obj"],
               "positive": r["positive"], "relation": r["relation"]}


def flags_of(u: str) -> list[int]:
    return [int(LE._has_correction_cue(u)),
            int(bool(re.search(r"\b(not|never|no longer|isn't|isn’t|doesn't|doesn’t|"
                                r"wasn't|wasn’t)\b", u.casefold()))),
            int(bool(re.match(r"^\s*(if\b|suppose\b|imagine\b|were\b)", u.casefold()))),
            int(any(m in f" {u.casefold()} " for m in LE.REPORTED_SPEECH_MARKERS)),
            int(LE._has_first_person(u)), int(LE._has_second_person(u))]


def encode_row(row: dict, tok):
    """-> tensors-ready dict or None when the gold span is unreachable or too wide."""
    utt = row_text(row)
    ids, chspans = _wp_encode(tok, utt)
    g = row["gold47"]
    a = ACT_INDEX[g["act"]]
    rel = rel_class(g["rel"])
    subj = obj = None
    if g["subj"]:
        subj = char_span_to_wp(chspans, MAX_LEN, g["subj"][0], g["subj"][1])
    if g["obj"]:
        obj = char_span_to_wp(chspans, MAX_LEN, g["obj"][0], g["obj"][1])
    if g["rep"]:
        if subj is None or (g["act"] == "STATE" and obj is None):
            return None
        if subj and subj[1] - subj[0] + 1 > MAX_SPAN_WP:
            return None
        if g["act"] == "STATE" and obj and obj[1] - obj[0] + 1 > MAX_SPAN_WP:
            return None
    else:
        subj = obj = None
    if subj and obj:
        # direction is recomputed from the CONVERTED token positions so that gold and
        # decode always compare the same quantity (spec 47: FORWARD iff subj <= obj).
        d = DIR_FORWARD if chspans[subj[0]][0] <= chspans[obj[0]][0] else DIR_REVERSE
    else:
        d = DIR_FORWARD
    return {"ids": ids, "act": a, "rel": rel,
            "subj": subj or [0, 0], "obj": obj or [0, 0], "dir": d,
            "flags": flags_of(utt), "source": row.get("source", "synth"),
            "text": utt, "chspans": chspans}


# --------------------------------------------------------------------------------- CLI
def report(snapshot: str | None = None):
    print(f"relation classes: {N_REL} = 481 webred + closed40 union + OPEN + UNSURE")
    print(f"  OPEN={OPEN_I} UNSURE={UNSURE_I}  closed_map={CLASSES['closed_map']}")
    RUNG1 = ("cal", "t_seen", "t_new", "t_far", "t_trap", "t_hard")
    for name in RUNG1:
        rows = synth_panel(name)
        n_state = sum(1 for r in rows if r["gold47"]["act"] == "STATE")
        n_ask = sum(1 for r in rows if r["gold47"]["act"] == "ASK")
        n_retract = sum(1 for r in rows if r["gold47"]["act"] == "RETRACT")
        n_nf = sum(1 for r in rows if r["gold47"]["act"] == "NO_FACT")
        n_un = sum(1 for r in rows if r["gold47"]["act"] == "UNSURE")
        unrep = sum(1 for r in rows if not r["gold47"]["rep"])
        print(f"{name:8s} n={len(rows):5d} STATE={n_state:5d} ASK={n_ask:4d} "
              f"RETRACT={n_retract:3d} NO_FACT={n_nf:4d} UNSURE={n_un:4d} "
              f"unrep={unrep:4d} sha={panel_sha(rows)[:16]} "
              f"strip1={strip_rung1_sha(rows)[:16]}")
    print("strip-rung1 full (must match rung-1 PASSMARKS where panels are identical):")
    for name in RUNG1:
        print(f"  {name:8s} {strip_rung1_sha(synth_panel(name))}")
    dev = list(_webred_rows(WEBRED / "dev.jsonl"))
    pos = [r for r in dev if r["positive"]]
    neg = [r for r in dev if not r["positive"]]
    cm = CLASSES["closed_map"]
    wclosed = [r for r in pos if r["relation"] in cm]
    print(f"wneg n={len(neg)}  wpos n={len(pos)}  wclosed n={len(wclosed)}  "
          f"wnewrel n={NEWREL_N}")
    import math as _m
    n_seen_state = sum(1 for r in synth_panel("t_seen") if r["gold47"]["act"] == "STATE")
    n_new_state = sum(1 for r in synth_panel("t_new") if r["gold47"]["act"] == "STATE")
    print(f"need_exec thresholds: SEEN >= {_m.ceil(0.90 * n_seen_state)} "
          f"(0.90 x N_STATE={n_seen_state})  NEW >= {_m.ceil(0.65 * n_new_state)} "
          f"(0.65 x N_STATE={n_new_state})")
    from fable_ears47_encoder import load as enc_load
    _, tok, _ = enc_load(snapshot_dir(snapshot))
    drop = tot = 0
    span_wps = []
    for r in webred_pool_rows():
        tot += 1
        e = encode_row(r, tok)
        if e is None:
            drop += 1
        else:
            for key in ("subj", "obj"):
                sp = e[key]
                if sp[1] > sp[0]:
                    span_wps.append(sp[1] - sp[0] + 1)
    print(f"webred train rows={tot} dropped (spans beyond len {MAX_LEN} "
          f"or >{MAX_SPAN_WP} wp)={drop} ({drop / max(tot, 1):.2%})")
    for name in ("t_seen", "t_new", "t_trap", "t_hard"):
        rows = synth_panel(name)
        d = sum(1 for r in rows if encode_row(r, tok) is None)
        print(f"{name}: unscorable after wp mapping = {d}")
    for name in ("wneg", "wpos", "wclosed", "wnewrel"):
        rows = json.loads((ARTIFACT / "panels" / f"{name}.json").read_text(
            encoding="utf-8"))
        d = sum(1 for r in rows if encode_row(r, tok) is None)
        print(f"{name}: unscorable after wp mapping = {d}/{len(rows)}")
    if span_wps:
        span_wps.sort()
        print(f"webred train span wp: n={len(span_wps)} max={span_wps[-1]} "
              f"p99={span_wps[int(0.99 * (len(span_wps) - 1))]} "
              f">12wp={sum(1 for s in span_wps if s > MAX_SPAN_WP)}")


def make_pool(out: Path, qwen: Path | None = None, snapshot: str | None = None):
    from fable_ears47_encoder import load as enc_load
    _, tok, _ = enc_load(snapshot_dir(snapshot))
    rng = random.Random(POOL_SEED + 7)
    kept = drop = 0
    with open(out, "w", encoding="utf-8") as fh:
        for row in synth_pool_rows(tok, rng):
            e = encode_row(row, tok)
            if e is None:
                drop += 1
                continue
            e.pop("chspans", None)
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
            kept += 1
        for row in webred_pool_rows():
            e = encode_row(row, tok)
            if e is None:
                drop += 1
                continue
            e.pop("chspans", None)
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
            kept += 1
        if qwen and qwen.exists():
            for line in open(qwen, encoding="utf-8"):
                row = json.loads(line)
                e = encode_row(row, tok)
                if e is None:
                    drop += 1
                    continue
                e.pop("chspans", None)
                fh.write(json.dumps(e, ensure_ascii=False) + "\n")
                kept += 1
    print(f"pool kept={kept} dropped={drop} -> {out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--pool", type=str, default=None)
    ap.add_argument("--qwen", type=str, default=None)
    ap.add_argument("--snapshot", type=str, default=None)
    a = ap.parse_args()
    if a.build:
        shas = build(ARTIFACT / "panels")
        for k, v in shas.items():
            print(f"{k:10s} {v}")
    if a.report:
        report(a.snapshot)
    if a.pool:
        make_pool(Path(a.pool), Path(a.qwen) if a.qwen else None, a.snapshot)


if __name__ == "__main__":
    main()
