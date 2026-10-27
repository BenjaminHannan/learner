#!/usr/bin/env python3
"""Fallback for when result files cannot be copied off the Vast boxes: rebuild minimal result files from the instance labels.

  python backbone/think/from_label.py --out out/think_label "LABEL0" "LABEL1" ...      labels as CLI arguments
  python backbone/think/from_label.py --out out/think_label --vast                      read them live (python3 backbone/vast.py status)
  python backbone/think/summarize.py out/think_label                                   then summarise as usual

A label is written by label_report.py every 5 minutes: "{box label}|{arm}_s{seed}:k=v,k=v;{arm}_s{seed}:...", percent with one decimal,
cut at 1000 characters. The keys are the ones think1.label_nums() builds:
  validation tags: v = "main", p1 = "pass1", vr = "main_repeat", every other tag verbatim (L0 L1 L2 L4 L8 L12 L16 L24, swap8, mean8,
                   rep1_8, gatesoff8, ref0)
  dev tags:        d = "main", otherwise "d" + the tag (dp1 = pass1, dvr = main_repeat, dL0 dL1 dL8 ...)
Arm t and t1 have no "main": think1.tags_for gives t the tags L0..L12 (+ L16, L24, lesions) and t1 / tw the tags L0, L1, L8 / L1; summarize.HEAD
maps each arm to the tag that is its headline (t: L8, t1 and tw: L1, the others: main), so no arm-specific rule is needed here.

The files carry "source": "label", the accuracies rounded to 0.1 point, and no per-row hits, so summarize.py prints point estimates only.
A label at the 1000-character cap was cut somewhere: the last key=value pair is dropped (a cut value like "v=6" looks valid), and
entries after the cut are simply absent. A real result file for the same arm and seed always wins in summarize.py.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

CAP = 1000
ARMS = ("a", "b", "aplus", "bplus", "t", "t1", "tw")
ENTRY = re.compile(r"^(%s)_s(\d+)$" % "|".join(ARMS))
SHORT = {"v": ("validation", "main"), "p1": ("validation", "pass1"), "vr": ("validation", "main_repeat"),
         "d": ("dev", "main"), "dp1": ("dev", "pass1"), "dvr": ("dev", "main_repeat")}
LONG = {"p1": "pass1", "vr": "main_repeat"}  # think1.label_nums names, for the tag after a dev "d"


def split_key(k):
    """label key -> (split, tag). Inverse of think1.label_nums()."""
    if k in SHORT:
        return SHORT[k]
    if k.startswith("d") and len(k) > 1:
        return "dev", LONG.get(k[1:], k[1:])
    return "validation", k


def parse_label(text, cap=CAP):
    """One label string -> (box label, {(arm, seed): {key: percent}}, notes).

    If len(text) >= cap the label was truncated: the last key=value pair is dropped (unless the text ends on a separator, in which case the
    last pair is complete). An entry left with no keys by that is dropped, and so is a cut-off name."""
    notes = []
    box, sep, body = text.partition("|")
    if not sep:
        return text, {}, [f"no '|' in label {text[:60]!r}: nothing to parse"]
    cut = len(text) >= cap
    if cut:
        if body.endswith((",", ";")):
            body = body[:-1]
            notes.append(f"{box}: label is at the {cap}-character cap (ended on a separator); later entries may be missing")
        else:
            head, _, last = body.rpartition(";")           # the last entry, possibly cut anywhere
            name, colon, kv = last.partition(":")
            if not colon:                                   # the cut fell inside an entry name
                body, what = head, f"entry {last!r}"
            elif "," in kv:                                 # drop only the last pair
                keep, _, pair = kv.rpartition(",")
                body, what = (head + ";" if head else "") + f"{name}:{keep}", f"{name} pair {pair!r}"
            else:                                           # the entry's only pair was cut: keep the name, no keys
                body, what = (head + ";" if head else "") + f"{name}:", f"{name} pair {kv!r}"
            notes.append(f"{box}: label is at the {cap}-character cap; dropped the cut-off {what}; later entries may be missing")
    out = {}
    entries = [e for e in body.split(";") if e]
    for i, e in enumerate(entries):
        name, colon, kv = e.partition(":")
        m = ENTRY.match(name)
        if not m:
            notes.append(f"{box}: entry {name!r} is not a Think-1 arm_sSEED name; skipped")
            continue
        nums = {}
        for p in kv.split(","):
            if not p:
                continue
            k, eq, v = p.partition("=")
            try:
                if not eq or not k:
                    raise ValueError
                nums[k] = float(v)
            except ValueError:
                notes.append(f"{box}: {name}: could not read {p!r}; skipped")
        if cut and i == len(entries) - 1 and not nums:
            continue  # its only keys were cut off (not an aborted run)
        out[(m.group(1), int(m.group(2)))] = nums
    return box, out, notes


def result_file(arm, seed, nums, box=""):
    """The minimal result a label stands for: eval.{split}.{tag} = {acc (fraction), n: None}, no hits, source 'label'."""
    ev = {"validation": {}, "dev": {}}
    for k, v in nums.items():
        split, tag = split_key(k)
        ev[split][tag] = {"acc": round(v / 100, 6), "n": None}
    r = {"arm": arm, "seed": seed, "source": "label", "box": box, "aborted": None, "eval": ev, "label_nums": nums,
         "note": "rebuilt from a Vast instance label by from_label.py: accuracies rounded to 0.1 point, no per-row hits"}
    if not nums:  # think1.py writes label_nums={} only for an aborted run (label_nums is filled after the eval)
        r["aborted"] = "label shows an empty summary (aborted run; the reason is not in the label)"
    return r


def merge(parsed):
    """[(box, {key: nums}, notes)] -> ({key: (box, nums)}, notes). On a clash the entry with more keys wins (a later label wins a tie)."""
    best, notes = {}, []
    for box, entries, ns in parsed:
        notes += ns
        for key, nums in entries.items():
            old = best.get(key)
            if old is not None:
                clash = sorted(k for k in set(old[1]) & set(nums) if old[1][k] != nums[k])
                notes.append(f"{key[0]} seed {key[1]} is in two labels ({old[0]}, {box})" + (f"; values differ for {clash}" if clash else ""))
                if len(nums) < len(old[1]):
                    continue
            best[key] = (box, nums)
    return best, notes


def write_all(labels, out):
    parsed = [parse_label(t) for t in labels]
    best, notes = merge(parsed)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for (arm, seed), (box, nums) in sorted(best.items()):
        p = out / f"result_{arm}_s{seed}.json"
        p.write_text(json.dumps(result_file(arm, seed, nums, box), indent=1))
        paths.append(p)
    return paths, notes


def vast_labels(text=None):
    """Labels from the output of `vast.py status` (lines: id label gpu status dph hours h). The label is everything after the id up to the
    end of the first whitespace-free run after '|' (label_report writes no spaces after the '|'), so its length can be checked against the cap."""
    if text is None:
        r = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / "vast.py"), "status"], capture_output=True, text=True, timeout=120)
        if r.returncode:
            raise SystemExit(f"vast.py status failed: {r.stderr[-300:]}")
        text = r.stdout
    out = []
    for line in text.splitlines():
        head, _, rest = line.strip().partition(" ")
        bar = rest.find("|")
        if bar < 0:
            continue
        end = bar + 1
        while end < len(rest) and not rest[end].isspace():
            end += 1
        out.append(rest[:end])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("labels", nargs="*", help="label strings, as shown in the Vast instance list")
    ap.add_argument("--vast", action="store_true", help="read the labels live with vast.py status")
    ap.add_argument("--out", default="out/think_label", help="directory for result_{arm}_s{seed}.json (default out/think_label)")
    a = ap.parse_args(argv)
    labels = list(a.labels) + (vast_labels() if a.vast else [])
    if not labels:
        ap.error("give label strings or --vast")
    paths, notes = write_all(labels, a.out)
    for n in notes:
        print("note:", n)
    for p in paths:
        print("wrote", p)
    if not paths:
        print("no Think-1 entries found in the labels")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
