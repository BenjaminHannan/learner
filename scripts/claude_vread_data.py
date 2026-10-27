#!/usr/bin/env python3
"""vread data (vector-reader thread, 2026-09-27): the sealed rows for the vector reader vs LoRA reader test.

Inputs (read-only, unchanged code):
  - Luna chats chunks 1..10: origin/builder-outbox:artifacts/claude-lis320-20260926/full-luna/chunkK/raw.new.jsonl.gz,
    joined in chunk order and cleaned by scripts/claude_lis320_resume_clean.clean (as ADDENDUM-11 does);
  - seeds: scripts/claude_lis320_seed_cr.py --seed 324 --n 6000 --ask-back (the chunk jobs' command line); the sha256 must
    equal chunk 1's SEEDS.sha256.txt;
  - kept rows: scripts/claude_lis320_check_we3.py (unchanged code checks and code labels).
Split: dev = claude_lis320_build.is_dev(row id, 10.0) (sha256 of the dialog id; whole dialogs on one side).
Calibration slice (vector reader only: layer and save bar): train dialogs with sha256("vread-cal:" + dialog) % 1000 < 100.

Cards: each code label fact with mode ASSERT / CORRECT / FORMER becomes a card (owner, rel, value, state current /
correction / former); every other mode is "no fact". Owner "me" -> the ME slot; any other owner and every value -> a
pointer to one exact whole-word span of the prompt the LoRA reader sees (claude_lis319_common.build_prompt_hist), searched
in the turn, then the previous reply, then the earlier turns newest first. A span is exact when the tokens it covers
decode (prompt[start of first token : end of last token].strip()) to the label string itself. A row with any card that
has no exact span is dropped from BOTH arms.

  python -B scripts/claude_vread_data.py build --out artifacts/claude-vread-20260927/data --tokenizer DIR_OR_ID
  python -B scripts/claude_vread_data.py unpack --data artifacts/claude-vread-20260927/data --out DIR
      (on the rental: rebuilds {train,cal,dev}.jsonl for the LoRA arm and *.cards.jsonl, checking every sha256)
  python -B scripts/claude_vread_data.py selftest
Prints counts only.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import lzma
import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))

LUNA = "artifacts/claude-lis320-20260926/full-luna"
CHUNKS = list(range(1, 11))
SEEDS_SHA = "9d17c5fe3e6171e0cb0ab87390d0144e325903de54200ef60f074302a29678d2"
DEV_PCT = 10.0
CAL_PER_MILLE = 100
STATES = {"ASSERT": "current", "CORRECT": "correction", "FORMER": "former"}
STATE_IDS = ["current", "correction", "former"]
MODEL_ID = "openbmb/MiniCPM5-1B"
MODEL_REV = "87179e5c1f455ef22e6223592d2d61351b525bfc"


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def dialog_of(row_id):
    return row_id.rsplit("-t", 1)[0]


def is_cal(dialog):
    return int(hashlib.sha256(("vread-cal:" + dialog).encode()).hexdigest()[:8], 16) % 1000 < CAL_PER_MILLE


# ---------------- spans ----------------
def prompt_regions(turn, prev_reply, history):
    """(prompt, [(start, end) regions in search order: turn, prev reply, history lines newest first])"""
    from claude_lis319_common import build_prompt_hist, history_block, SYSTEM
    p = build_prompt_hist(turn, prev_reply, history)
    hb = history_block(history)
    h0 = len(SYSTEM) + len("\nEarlier chat:\n")
    assert p[h0:h0 + len(hb)] == hb
    prev = str(prev_reply or "").strip()
    p0 = h0 + len(hb) + len("\nAssistant said: ")
    t = str(turn).strip()
    t0 = len(p) - len("\nFrame: ") - len(t)
    assert p[t0:t0 + len(t)] == t and p[t0 - len("\nUser said: "):t0] == "\nUser said: "
    regions = [(t0, t0 + len(t))]
    if prev:
        assert p[p0:p0 + len(prev)] == prev
        regions.append((p0, p0 + len(prev)))
    if list(history or []):
        lines, pos = [], h0
        for ln in hb.split("\n"):
            lines.append((pos, pos + len(ln)))
            pos += len(ln) + 1
        regions += lines[::-1]
    return p, regions


def occurrences(needle, text, a, b):
    """char spans of whole-word occurrences of needle (exact case) in text[a:b]; the compiler's pattern (a trailing
    's / s is allowed after the word, but is not part of the span)."""
    pat = r"(?<![A-Za-z0-9])(" + re.escape(needle.strip()) + r")(?:'s|’s|s)?(?![A-Za-z0-9])"
    return [(a + m.start(1), a + m.end(1)) for m in re.finditer(pat, text[a:b])]


def token_span(offsets, c0, c1, n_prefix):
    """token indices (s, e) covering chars [c0, c1); offsets are for the prompt tokens only (n_prefix tokens precede)"""
    s = e = None
    for i, (a, b) in enumerate(offsets):
        if s is None and a <= c0 < b:
            s = i
        if a < c1 <= b:
            e = i
            break
    if s is None or e is None or e < s:
        return None
    return s + n_prefix, e + n_prefix


def decode_span(prompt, offsets, s, e, n_prefix):
    return prompt[offsets[s - n_prefix][0]:offsets[e - n_prefix][1]].strip()


def find_pointer(needle, prompt, regions, offsets, n_prefix):
    for a, b in regions:
        for c0, c1 in occurrences(needle, prompt, a, b):
            ts = token_span(offsets, c0, c1, n_prefix)
            if ts and decode_span(prompt, offsets, ts[0], ts[1], n_prefix) == needle:
                return {"chars": [c0, c1], "tokens": list(ts), "region": regions.index((a, b))}
    return None


def cards_for(row, tok):
    """(cards, n_tokens, ids_sha, unmapped list); cards in the frame's fact order"""
    p, regions = prompt_regions(row["turn"], row.get("prev_reply", ""), [tuple(h) for h in row.get("history") or []])
    assert p == row["prompt"], row["id"]
    enc = tok(p, add_special_tokens=False, return_offsets_mapping=True)
    ids = [tok.bos_token_id] + enc["input_ids"]
    offs = enc["offset_mapping"]
    cards, unmapped = [], []
    for f in row["frame"]["facts"]:
        st = STATES.get(f["mode"])
        if st is None:
            continue
        c = {"owner": f["owner"], "rel": f["rel"], "value": f["value"], "state": st}
        if f["owner"] == "me":
            c["owner_ptr"] = "ME"
        else:
            c["owner_ptr"] = find_pointer(f["owner"], p, regions, offs, 1)
            if c["owner_ptr"] is None:
                unmapped.append(("owner", f["owner"]))
        c["value_ptr"] = find_pointer(f["value"], p, regions, offs, 1)
        if c["value_ptr"] is None:
            unmapped.append(("value", f["value"]))
        cards.append(c)
    return cards, len(ids), sha256_bytes(json.dumps(ids).encode()), unmapped


# ---------------- build ----------------
def git_show(path):
    return subprocess.run(["git", "-C", str(REPO), "show", f"origin/builder-outbox:{path}"], check=True,
                          capture_output=True).stdout


def load_kept(tmp):
    import claude_lis320_resume_clean as RC
    import claude_lis320_check as C
    import claude_lis320_check_we3 as W3
    pins, rows = {}, []
    for k in CHUNKS:
        b = git_show(f"{LUNA}/chunk{k}/raw.new.jsonl.gz")
        pins[f"chunk{k}/raw.new.jsonl.gz"] = sha256_bytes(b)
        rows += [json.loads(x) for x in gzip.decompress(b).decode("utf-8").splitlines() if x.strip()]
    s1 = git_show(f"{LUNA}/chunk1/SEEDS.sha256.txt").decode().strip()
    assert s1 == SEEDS_SHA, s1
    raw, rc = RC.clean(rows)
    seeds_p = Path(tmp) / "seeds.jsonl"
    subprocess.run([sys.executable, "-B", str(HERE / "claude_lis320_seed_cr.py"), "--seed", "324", "--n", "6000",
                    "--ask-back", "--avoid-names", str(REPO / "artifacts/claude-lis320-20260926/avoid_names_dev.txt"),
                    "--avoid-hashes", str(REPO / "artifacts/claude-lis320-20260926/avoid_test.sha256"),
                    "--out", str(seeds_p)], check=True, capture_output=True)
    pins["seeds.jsonl"] = sha256_bytes(seeds_p.read_bytes())
    assert pins["seeds.jsonl"] == SEEDS_SHA, pins["seeds.jsonl"]
    W3.install()
    kept, drops, c, fam = C.check_all(C.load(seeds_p), raw)
    pins["raw_clean.jsonl"] = sha256_bytes("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in raw).encode())
    pins["kept.jsonl"] = sha256_bytes("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in kept).encode())
    return raw, kept, pins, {"resume_clean": rc, "check_kept": c["kept"], "check_turns": c["turns"],
                             "check_dialogs": c["dialogs"], "kept_by_family": dict(sorted(fam.items()))}


def build(a):
    from transformers import AutoTokenizer
    from claude_lis320_build import is_dev
    from claude_lis300_common import frame_text
    tok = AutoTokenizer.from_pretrained(a.tokenizer, revision=MODEL_REV if a.tokenizer == MODEL_ID else None)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        raw, kept, pins, info = load_kept(tmp)
    dialogs = {r["dialog_id"]: [[t["user"], t.get("reply_before", "")] for t in r["parsed"]["turns"]]
               for r in raw if (r.get("parsed") or {}).get("turns")}
    c, fam_side, un_kinds = Counter(), Counter(), Counter()
    compact = []
    for r in kept:
        d = dialog_of(r["id"])[len("glm320-"):]      # the seed's dialog id (row ids are glm320-<dialog>-t<k>)
        side = "dev" if is_dev(r["id"], DEV_PCT) else ("cal" if is_cal(dialog_of(r["id"])) else "train")
        cards, ntok, idsha, unmapped = cards_for(r, tok)
        c["rows"] += 1
        c["label_cards"] += len(cards)
        c["label_facts"] += len(r["frame"]["facts"])
        if unmapped:
            c["rows_dropped_unmapped"] += 1
            c["cards_in_dropped_rows"] += len(cards)
            c["unmapped_fields"] += len(unmapped)
            for kind, _ in unmapped:
                un_kinds[kind] += 1
            fam_side[f"dropped:{side}:{r['family']}"] += 1
            continue
        c[f"rows_{side}"] += 1
        c[f"cards_{side}"] += len(cards)
        fam_side[f"{side}:{r['family']}"] += 1
        assert r["target"] == frame_text(r["frame"]) and r["src"] == "glm320"
        compact.append([r["id"], side, r["family"], r["frame"]])
    c = Counter({k: v for k, v in c.items() if v})
    sides = {}
    for rid, side, _, _ in compact:
        sides.setdefault(side, set()).add(dialog_of(rid))
    leak = len(sides.get("dev", set()) & (sides.get("train", set()) | sides.get("cal", set())))
    assert leak == 0
    used = sorted({dialog_of(x[0])[len("glm320-"):] for x in compact})
    dia = {d: dialogs[d] for d in used}
    xz = lambda obj: lzma.compress(json.dumps(obj, ensure_ascii=False, sort_keys=True,  # noqa: E731
                                              separators=(",", ":")).encode(), preset=9)
    (out / "dialogs.json.xz").write_bytes(xz(dia))
    (out / "rows.json.xz").write_bytes(xz(compact))
    full = expand(json.loads(lzma.decompress((out / "rows.json.xz").read_bytes())),
                  json.loads(lzma.decompress((out / "dialogs.json.xz").read_bytes())), tok)
    by_id = {r["id"]: r for r in kept}
    for r in full:                                    # the pack rebuilds every kept row exactly
        assert all(r[k] == by_id[r["id"]][k] for k in LORA_KEYS), r["id"]
    ntoks = sorted(x["n_tokens"] for x in full)
    summary = {"inputs_sha256": pins, "build": info, "counts": dict(sorted(c.items())),
               "unmapped_by_field": dict(un_kinds), "by_side_family": dict(sorted(fam_side.items())),
               "dialogs": {s: len(v) for s, v in sorted(sides.items())}, "dev_dialogs_in_train_or_cal": leak,
               "files_sha256": side_files_sha(full), "tokens_median": ntoks[len(ntoks) // 2], "tokens_max": ntoks[-1],
               "tokenizer": f"{MODEL_ID}@{MODEL_REV}",
               "pack_sha256": {p.name: sha256_bytes(p.read_bytes()) for p in sorted(out.glob("*.xz"))}}
    (out / "build.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("counts", "unmapped_by_field", "dialogs", "dev_dialogs_in_train_or_cal",
                                              "tokens_median", "tokens_max")}, indent=1))


# ---------------- rebuild the row files (both arms) ----------------
LORA_KEYS = ("id", "prompt", "target", "src", "family", "turn", "prev_reply", "frame", "history")


def expand(compact, dia, tok):
    """full rows (lis-320 row fields + side + cards) from the compact pack; prompt from build_prompt_hist,
    history exactly as claude_lis320_check.check_turn builds it"""
    from claude_lis319_common import build_prompt_hist
    from claude_lis300_common import frame_text, canon_frame
    out = []
    for rid, side, fam, frame in compact:
        frame = canon_frame(frame)                    # the pack stores keys sorted; rows keep the canonical order
        turns = dia[dialog_of(rid)[len("glm320-"):]]
        i = int(rid.rsplit("-t", 1)[1]) - 1
        u, rb = turns[i][0].strip(), (turns[i][1] or "").strip()
        history = [(turns[j][0].strip(), (turns[j + 1][1] or "").strip()) for j in range(i)]
        r = {"id": rid, "prompt": build_prompt_hist(u, rb, history), "target": frame_text(frame), "src": "glm320",
             "family": fam, "turn": u, "prev_reply": rb, "frame": frame, "history": [list(h) for h in history]}
        cards, ntok, idsha, unmapped = cards_for(r, tok)
        assert not unmapped, rid
        out.append(dict(r, side=side, cards=cards, n_tokens=ntok, ids_sha=idsha))
    return out


def side_text(full, side, lora):
    rs = [r for r in full if r["side"] == side]
    return "".join(json.dumps({k: r[k] for k in LORA_KEYS} if lora else r, ensure_ascii=False) + "\n" for r in rs)


def side_files_sha(full):
    return {f"{side}{'' if lora else '.cards'}.jsonl": sha256_bytes(side_text(full, side, lora).encode())
            for side in ("train", "cal", "dev") for lora in (True, False)}


def read_pack(data):
    data = Path(data)
    load = lambda n: json.loads(lzma.decompress((data / n).read_bytes()).decode())  # noqa: E731
    return load("rows.json.xz"), load("dialogs.json.xz")


def unpack(a):
    """write OUT/{train,cal,dev}.jsonl (the LoRA arm's rows) and OUT/{train,cal,dev}.cards.jsonl; every sha256 checked"""
    from transformers import AutoTokenizer
    data = Path(a.data)
    build_info = json.loads((data / "build.json").read_text())
    for n, h in build_info["pack_sha256"].items():
        assert sha256_bytes((data / n).read_bytes()) == h, n
    tok = AutoTokenizer.from_pretrained(a.tokenizer, revision=MODEL_REV if a.tokenizer == MODEL_ID else None)
    compact, dia = read_pack(data)
    full = expand(compact, dia, tok)
    got = side_files_sha(full)
    assert got == build_info["files_sha256"], (got, build_info["files_sha256"])
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for side in ("train", "cal", "dev"):
        (out / f"{side}.jsonl").write_text(side_text(full, side, True), encoding="utf-8")
        (out / f"{side}.cards.jsonl").write_text(side_text(full, side, False), encoding="utf-8")
    print(json.dumps({"unpack": {s: sum(r["side"] == s for r in full) for s in ("train", "cal", "dev")},
                      "sha256_ok": True}))


def selftest():
    class Tok:   # whitespace-ish tokenizer with a leading-space convention like the real one
        bos_token_id = 0

        def __call__(self, s, add_special_tokens=False, return_offsets_mapping=True):
            offs = [(m.start(), m.end()) for m in re.finditer(r"\s?[A-Za-z]+|\s?[^A-Za-z\s]|\n", s)]
            return {"input_ids": list(range(1, len(offs) + 1)), "offset_mapping": offs}
    from claude_lis319_common import build_prompt_hist
    hist = [("my sister Mira is a nurse", "nice"), ("my boss is Tovan", "ok")]
    row = {"id": "glm320-x-t3", "turn": "she moved to Velbrook", "prev_reply": "cool", "history": hist,
           "frame": {"act": "STATE", "facts": [{"owner": "Mira", "rel": "city", "value": "Velbrook", "mode": "ASSERT"},
                                               {"owner": "me", "rel": "city", "value": "Velbrook", "mode": "PLAN"}],
                     "ask": None}}
    row["prompt"] = build_prompt_hist(row["turn"], row["prev_reply"], hist)
    cards, n, _, un = cards_for(row, Tok())
    assert not un and len(cards) == 1, (cards, un)
    c = cards[0]
    assert c["owner_ptr"]["region"] >= 2 and c["value_ptr"]["region"] == 0, c
    enc = Tok()(row["prompt"])
    for ptr, want in ((c["owner_ptr"], "Mira"), (c["value_ptr"], "Velbrook")):
        assert decode_span(row["prompt"], enc["offset_mapping"], *ptr["tokens"], 1) == want
    row2 = dict(row, turn="anas boss is Kel", frame={"act": "STATE", "facts": [
        {"owner": "ana", "rel": "boss", "value": "Kel", "mode": "ASSERT"}], "ask": None})
    row2["prompt"] = build_prompt_hist(row2["turn"], row2["prev_reply"], hist)
    _, _, _, un2 = cards_for(row2, Tok())
    assert un2 == [("owner", "ana")], un2     # "anas" is one token here: no exact span for "ana"
    assert is_cal("x") in (True, False)
    print("vread data selftest ok: history owner and turn value pointed exactly; a span inside a token is unmapped")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "unpack", "selftest"])
    ap.add_argument("--out")
    ap.add_argument("--data")
    ap.add_argument("--tokenizer", default=MODEL_ID)
    a = ap.parse_args()
    if a.cmd == "selftest":
        return selftest()
    return {"build": build, "unpack": unpack}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
