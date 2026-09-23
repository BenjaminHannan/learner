#!/usr/bin/env python3
"""Exp 92 dev diagnosis (NOT a registered run): classifies English-arm
question-compose misses on S1-S3 without scoring against gold."""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from fable_bench92_english_arm import hear_teach92, _relation_mentions92
import fable_bench73_english_arm as B73

out_lines = []
cause = Counter()
shown = {}
for split in ["fable_edit92_s1_3hop", "fable_edit92_s2_4hop",
              "fable_edit92_s3_multiedit"]:
    for line in (ROOT / "data" / "open" / "bench92" / f"{split}.jsonl"
                 ).open(encoding="utf-8"):
        it = json.loads(line)
        triples = [t for t in (hear_teach92(t["sentence_en"])
                               for t in it["taught"]) if t]
        if it["id"] == "bench92-s1-3hop-019":
            out_lines.append("019 triples: %r" % (triples,))
            out_lines.append("019 gold: %r" % (it["gold"],))
        ents = []
        for s, _, o in triples:
            ents.extend([s, o])
        ment = B73._entity_mentions(it["question"], ents)
        if len(ment) == 1:
            rels = []
            c = ment[0]
            for _ in range(8):
                outs = [(r, o) for (s, r, o) in triples if s == c]
                uniq = list(dict.fromkeys(r for r, _ in outs))
                if len(uniq) != 1:
                    break
                rels.append(uniq[0])
                c = [o for (r, o) in outs if r == uniq[0]][-1]
            mentioned = _relation_mentions92(it["question"])
            missing = [r for r in rels if r not in mentioned]
            key = "G:" + ",".join(missing) if missing else "ok"
            cause[key] += 1
            if key != "ok" and key not in shown and len(shown) < 25:
                shown[key] = (it["id"], it["question"], rels)
        else:
            cause["ment!=1(%d)" % len(ment)] += 1
            key = "ment!=1(%d)" % len(ment)
            if key not in shown:
                shown[key] = (it["id"], it["question"], ment[:3])
out_lines.append("CAUSE: %r" % (dict(cause),))
for k, v in shown.items():
    out_lines.append("%s | %r" % (k, v))
(ROOT / "artifacts" / "fable-bench92-20260921" / "dev_diagnose.txt"
 ).write_text("\n".join(out_lines) + "\n", encoding="utf-8")
print("wrote dev_diagnose.txt")
