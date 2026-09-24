#!/usr/bin/env python3
"""own-M1v grammar grading kit: 300 real replies + 40 planted-error canaries, shuffled, for blind graders.

build: python claude_own_m1v_grade_kit.py build --dev-out OUT.jsonl --kit DIR   (fills with the mouth layer printer)
  DIR/items.jsonl   {"item", "reply"}                  (what graders see: filled reply text only)
  DIR/key.json      item -> {"kind": "real"|"canary", "src": dev row index, "error": ...}   (graders never see)
score: python claude_own_m1v_grade_kit.py score --kit DIR --grades G1.jsonl G2.jsonl [--tiebreak G3.jsonl]
  grader files: {"item", "verdict": "OK"|"ERROR", "note"}
  prints canary catches per grader, flagged real replies (both / one), and the error count used for Pm1v.4.
Deterministic (seed 331). Canaries are made from spoken replies NOT among the 300 graded ones.
"""
import argparse, json, random, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_own_mouth_layer import fill_natural, leak_check  # noqa: E402

SEED = 331


KINDS = ["drop 'is'", "is->are", "wrong wh-word", "dropped possessive 's", "doubled word", "swapped words",
         "broken contraction"]


def _corrupt(text, rng, want=None):
    """One planted grammar error; returns (new_text, kind) or None if no rule applies.
    `want` = preferred kind (round-robin in build, so the 40 canaries mix all kinds)."""
    rules = []
    if re.search(r"\bis\b", text):
        rules.append(("drop 'is'", lambda t: re.sub(r"\bis\b ", "", t, count=1)))
        rules.append(("is->are", lambda t: re.sub(r"\bis\b", "are", t, count=1)))
    if re.search(r"\b(who|where|what)\b", text):
        sw = {"who": "where", "where": "who", "what": "who"}
        rules.append(("wrong wh-word", lambda t: re.sub(r"\b(who|where|what)\b", lambda m: sw[m.group(1)], t, count=1)))
    if re.search(r"\w's\b", text):
        rules.append(("dropped possessive 's", lambda t: re.sub(r"(\w)'s\b", r"\1", t, count=1)))
    words = text.split()
    if len(words) >= 4:
        i = rng.randrange(1, len(words) - 1)
        while words[i].lower().strip(".,!?") in ("that", "had", "very", "really") and i > 1:
            i -= 1  # doubling these can stay grammatical
        rules.append(("doubled word", lambda t, i=i: " ".join(t.split()[:i + 1] + [t.split()[i]] + t.split()[i + 1:])))
        rules.append(("swapped words", lambda t, i=i: " ".join(t.split()[:i] + [t.split()[i + 1], t.split()[i]] + t.split()[i + 2:])))
    if re.search(r"\b(I've|I'm|don't|I'll)\b", text):
        rules.append(("broken contraction", lambda t: re.sub(r"\b(I've|I'm|don't|I'll)\b",
                                                             lambda m: {"I've": "I has", "I'm": "I is", "don't": "doesn't",
                                                                        "I'll": "I wills"}[m.group(1)], t, count=1)))
    rng.shuffle(rules)
    rules.sort(key=lambda kf: kf[0] != want)
    for kind, f in rules:
        new = f(text)
        if new != text:
            return new, kind
    return None


def build(a):
    rows = [json.loads(l) for l in Path(a.dev_out).read_text(encoding="utf-8").splitlines() if l.strip()]
    # graded text = the winning raw reply filled by the layer's printer (plain relation nouns, not "favorite_food")
    spoken, leaks = [], 0
    for i, r in enumerate(rows):
        if not r.get("reply"):
            continue
        raw = r["raw"][r["tries"] - 1] if "raw" in r else r["reply"]
        leaks += bool(leak_check(raw, r["record"]))
        spoken.append((i, fill_natural(raw, r["record"])))
    rng = random.Random(SEED)
    rng.shuffle(spoken)
    real, pool = spoken[:300], spoken[300:]
    canaries = []
    for i, text in pool:
        c = _corrupt(text, rng, want=KINDS[len(canaries) % len(KINDS)])
        if c:
            canaries.append((i, c[0], c[1]))
        if len(canaries) == 40:
            break
    items = [("real", i, t, None) for i, t in real] + [("canary", i, t, k) for i, t, k in canaries]
    rng.shuffle(items)
    kit = Path(a.kit)
    kit.mkdir(parents=True, exist_ok=True)
    key = {}
    with open(kit / "items.jsonl", "w", encoding="utf-8") as fh:
        for n, (kind, i, t, err) in enumerate(items):
            item = f"g{n:03d}"
            fh.write(json.dumps({"item": item, "reply": t}, ensure_ascii=False) + "\n")
            key[item] = {"kind": kind, "src": i, "error": err}
    (kit / "key.json").write_text(json.dumps(key, indent=0))
    print(json.dumps({"real": len(real), "canaries": len(canaries), "items": len(items),
                      "spoken": len(spoken), "spoken_with_literal_leak": leaks}))


def _load(p):
    return {g["item"]: g for g in (json.loads(l) for l in Path(p).read_text().splitlines() if l.strip())}


def score(a):
    key = json.loads((Path(a.kit) / "key.json").read_text())
    gs = [_load(p) for p in a.grades]
    tb = _load(a.tiebreak) if a.tiebreak else {}
    out = {}
    for n, g in enumerate(gs):
        missing = [k for k in key if k not in g]
        caught = sum(1 for k, v in key.items() if v["kind"] == "canary" and g.get(k, {}).get("verdict") == "ERROR")
        out[f"grader{n + 1}"] = {"canaries_caught": caught, "canaries": sum(v["kind"] == "canary" for v in key.values()),
                                 "missing_items": len(missing)}
    both, one, one_items = 0, 0, []
    for k, v in key.items():
        if v["kind"] != "real":
            continue
        flags = sum(g.get(k, {}).get("verdict") == "ERROR" for g in gs[:2])
        if flags == 2:
            both += 1
        elif flags == 1:
            one += 1
            one_items.append(k)
    tb_err = sum(tb.get(k, {}).get("verdict") == "ERROR" for k in one_items)
    out.update({"real_flagged_by_both": both, "real_flagged_by_one": one, "one_flag_items": one_items,
                "tiebreak_confirmed": tb_err if tb else None,
                "errors_counted": both + (tb_err if tb else 0),
                "tiebreak_needed": bool(one_items) and not tb})
    print(json.dumps(out, indent=1))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--dev-out", required=True)
    b.add_argument("--kit", required=True)
    s = sub.add_parser("score")
    s.add_argument("--kit", required=True)
    s.add_argument("--grades", nargs=2, required=True)
    s.add_argument("--tiebreak")
    a = ap.parse_args()
    build(a) if a.cmd == "build" else score(a)


if __name__ == "__main__":
    main()
