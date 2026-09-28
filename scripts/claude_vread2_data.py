#!/usr/bin/env python3
"""vread2 data (vector-reader thread, 2026-09-28): the fresh Luna rows (chunks 11-13) and the owner-name copies.

The fresh set is built with the unchanged vread data code (scripts/claude_vread_data.py, imported, not edited): the
same clean, seeds and code checks run over chunks 1..13 joined in chunk order, exactly as vread ran them over 1..10
(the only thing set here is the chunk list). The kept rows of dialogs from chunks 11, 12 and 13 are the fresh set.
Chunks 1-10 must give back vread's 13,891 kept rows (same ids), and no fresh dialog may be in vread's pack. Cards and
pointers come from claude_vread_data.cards_for, and a row with an unmapped card is dropped, as in vread.
The fresh set is never trained on; it is read once per checkpoint and scored once.

Owner copies (the one change of arm B): for a card whose owner is a name, its copies are every whole-word, exact-case
occurrence of the owner text in the prompt's turn, previous reply and earlier-turn lines
(claude_vread_data.occurrences, the label search's own pattern) whose tokens decode to exactly that text. The label's
own pointer (the newest copy) is always one of them.

  python -B scripts/claude_vread2_data.py build --out artifacts/claude-vread2-20260928/data --tokenizer DIR_OR_ID
  python -B scripts/claude_vread2_data.py unpack --data artifacts/claude-vread2-20260928/data --out DIR --tokenizer DIR
  python -B scripts/claude_vread2_data.py selftest
Prints counts only.
"""
from __future__ import annotations

import argparse
import gzip
import json
import lzma
import sys
import tempfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))
import claude_vread_data as VD  # noqa: E402  (read only)

FRESH_CHUNKS = (11, 12, 13)
VREAD_PACK = REPO / "artifacts/claude-vread-20260927/data"


# ---------------- copies ----------------
def copies(text, prompt, regions, offs, n_prefix=1):
    """sorted token spans (s, e) of every whole-word exact copy of `text` in the prompt regions"""
    out = set()
    for a, b in regions:
        for c0, c1 in VD.occurrences(text, prompt, a, b):
            ts = VD.token_span(offs, c0, c1, n_prefix)
            if ts and VD.decode_span(prompt, offs, ts[0], ts[1], n_prefix) == text:
                out.add(tuple(ts))
    return sorted(out)


def row_regions(row):
    p, regions = VD.prompt_regions(row["turn"], row.get("prev_reply", ""),
                                   [tuple(h) for h in row.get("history") or []])
    assert p == row["prompt"], row["id"]
    return regions


def owner_copies(row, offs):
    """per gold card: None for owner "me", else the list of copies of its owner name (label pointer included)"""
    regions = row_regions(row)
    out = []
    for c in row["cards"]:
        if c["owner_ptr"] == "ME":
            out.append(None)
            continue
        cp = copies(c["owner"], row["prompt"], regions, offs)
        assert tuple(c["owner_ptr"]["tokens"]) in cp, (row["id"], c["owner"])
        out.append(cp)
    return out


# ---------------- build ----------------
def build(a):
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(a.tokenizer, revision=VD.MODEL_REV if a.tokenizer == VD.MODEL_ID else None)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    VD.CHUNKS = list(range(1, max(FRESH_CHUNKS) + 1))
    with tempfile.TemporaryDirectory() as tmp:
        raw, kept, pins, info = VD.load_kept(tmp)
    fresh_dialogs = set()
    for k in FRESH_CHUNKS:
        b = VD.git_show(f"{VD.LUNA}/chunk{k}/raw.new.jsonl.gz")
        fresh_dialogs |= {json.loads(x)["dialog_id"] for x in gzip.decompress(b).decode().splitlines() if x.strip()}
    vcompact, vdia = VD.read_pack(VREAD_PACK)
    vread_ids = {x[0] for x in vcompact}
    seed_dialog = lambda rid: VD.dialog_of(rid)[len("glm320-"):]  # noqa: E731
    old = [r for r in kept if seed_dialog(r["id"]) not in fresh_dialogs]
    new = [r for r in kept if seed_dialog(r["id"]) in fresh_dialogs]
    assert {r["id"] for r in old} == vread_ids, "chunks 1-10 do not give back vread's kept rows"
    leak = len({seed_dialog(r["id"]) for r in new} & set(vdia))
    assert leak == 0
    dialogs = {r["dialog_id"]: [[t["user"], t.get("reply_before", "")] for t in r["parsed"]["turns"]]
               for r in raw if (r.get("parsed") or {}).get("turns")}
    c, fam = Counter(), Counter()
    compact = []
    for r in new:
        cards, ntok, idsha, unmapped = VD.cards_for(r, tok)
        c["rows"] += 1
        c["cards"] += len(cards)
        if unmapped:
            c["rows_dropped_unmapped"] += 1
            c["cards_in_dropped_rows"] += len(cards)
            continue
        c["rows_fresh"] += 1
        c["cards_fresh"] += len(cards)
        fam[r["family"]] += 1
        compact.append([r["id"], "fresh", r["family"], r["frame"]])
    used = sorted({seed_dialog(x[0]) for x in compact})
    dia = {d: dialogs[d] for d in used}
    xz = lambda obj: lzma.compress(json.dumps(obj, ensure_ascii=False, sort_keys=True,  # noqa: E731
                                              separators=(",", ":")).encode(), preset=9)
    (out / "dialogs.json.xz").write_bytes(xz(dia))
    (out / "rows.json.xz").write_bytes(xz(compact))
    full = VD.expand(*VD.read_pack(out), tok)
    by_id = {r["id"]: r for r in new}
    for r in full:
        assert all(r[k] == by_id[r["id"]][k] for k in VD.LORA_KEYS), r["id"]
    gold = gold_counts(full, tok)
    ntoks = sorted(x["n_tokens"] for x in full)
    summary = {"inputs_sha256": pins, "build_chunks_1_13": info, "fresh_chunks": list(FRESH_CHUNKS),
               "counts": dict(sorted(c.items())), "fresh_by_family": dict(sorted(fam.items())),
               "fresh_dialogs": len(used), "chunks_1_10_rows_equal_vread": True,
               "fresh_dialogs_in_vread_pack": leak, "gold": gold,
               "files_sha256": files_sha(full), "tokens_median": ntoks[len(ntoks) // 2], "tokens_max": ntoks[-1],
               "tokenizer": f"{VD.MODEL_ID}@{VD.MODEL_REV}",
               "pack_sha256": {p.name: VD.sha256_bytes(p.read_bytes()) for p in sorted(out.glob("*.xz"))}}
    (out / "build.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("counts", "fresh_dialogs", "fresh_dialogs_in_vread_pack", "gold",
                                              "tokens_median", "tokens_max")}, indent=1))


def copy_bin(n):
    return "1" if n == 1 else "2" if n == 2 else "3+"


def gold_counts(full, tok):
    """gold-only counts for the validity mark: backref cards and their owner-name copy counts"""
    g = Counter()
    for r in full:
        offs = tok(r["prompt"], add_special_tokens=False, return_offsets_mapping=True)["offset_mapping"]
        cps = owner_copies(r, offs)
        for c, cp in zip(r["cards"], cps):
            g["cards"] += 1
            if cp is not None:
                g[f"named_owner_cards_copies_{copy_bin(len(cp))}"] += 1
            if r["family"] == "backref":
                g["backref_cards"] += 1
                g[f"backref_cards_copies_{'me' if cp is None else copy_bin(len(cp))}"] += 1
                g[f"backref_cards_state_{c['state']}"] += 1
    return dict(sorted(g.items()))


def files_sha(full):
    return {"fresh.jsonl": VD.sha256_bytes(VD.side_text(full, "fresh", True).encode()),
            "fresh.cards.jsonl": VD.sha256_bytes(VD.side_text(full, "fresh", False).encode())}


def unpack(a):
    from transformers import AutoTokenizer
    data = Path(a.data)
    info = json.loads((data / "build.json").read_text())
    for n, h in info["pack_sha256"].items():
        assert VD.sha256_bytes((data / n).read_bytes()) == h, n
    tok = AutoTokenizer.from_pretrained(a.tokenizer, revision=VD.MODEL_REV if a.tokenizer == VD.MODEL_ID else None)
    full = VD.expand(*VD.read_pack(data), tok)
    assert files_sha(full) == info["files_sha256"]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "fresh.cards.jsonl").write_text(VD.side_text(full, "fresh", False), encoding="utf-8")
    print(json.dumps({"unpack_fresh": len(full), "sha256_ok": True}))


def selftest():
    class Tok:
        bos_token_id = 0

        def __call__(self, s, add_special_tokens=False, return_offsets_mapping=True):
            import re
            offs = [(m.start(), m.end()) for m in re.finditer(r"\s?[A-Za-z]+|\s?[^A-Za-z\s]|\n", s)]
            return {"input_ids": list(range(1, len(offs) + 1)), "offset_mapping": offs}
    from claude_lis319_common import build_prompt_hist
    hist = [("my sister Mira is a nurse", "Mira sounds great"), ("Mira's boss is Tovan", "ok"), ("Miras cat", "")]
    row = {"id": "glm320-x-t4", "turn": "she moved to Velbrook", "prev_reply": "cool", "history": hist,
           "frame": {"act": "STATE", "facts": [{"owner": "Mira", "rel": "city", "value": "Velbrook",
                                                "mode": "ASSERT"}], "ask": None}}
    row["prompt"] = build_prompt_hist(row["turn"], row["prev_reply"], hist)
    t = Tok()
    cards, _, _, un = VD.cards_for(row, t)
    assert not un
    row["cards"] = cards
    offs = t(row["prompt"])["offset_mapping"]
    cp = owner_copies(row, offs)[0]
    # copies: "sister Mira", "Mira sounds", "Mira's boss", "Miras cat" (the trailing s is allowed but not in the span)
    texts = [VD.decode_span(row["prompt"], offs, s, e, 1) for s, e in cp]
    assert texts == ["Mira"] * len(cp) and len(cp) == 3, (texts, cp)   # "Miras" is one token here: no exact span
    assert tuple(cards[0]["owner_ptr"]["tokens"]) == max(cp)            # the label is the newest copy
    assert copy_bin(1) == "1" and copy_bin(2) == "2" and copy_bin(5) == "3+"
    print("vread2 data selftest ok: all whole-word copies found, label pointer is the newest, partial token skipped")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "unpack", "selftest"])
    ap.add_argument("--out")
    ap.add_argument("--data")
    ap.add_argument("--tokenizer", default=VD.MODEL_ID)
    a = ap.parse_args()
    if a.cmd == "selftest":
        return selftest()
    return {"build": build, "unpack": unpack}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
