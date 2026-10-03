"""Check real token lengths against the pipeline caps (input 64 incl. EOS, target 48 incl. EOS).

python -m skills_curriculum.token_report --tokenizer /path/to/tokenizer.json --rows train.jsonl [--frames-out frames.jsonl]
The tokenizer is LiquidAI/LFM2.5-1.2B-Instruct (public file tokenizer.json, revision 0f604ada...). Needs `pip install tokenizers`.
--frames-out writes pipeline-style rows: learner_text, target_text, input_ids, labels (both with EOS appended as id eos_id).
"""
import argparse
import json
import sys

INPUT_CAP, TARGET_CAP = 64, 48


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tokenizer", required=True)
    ap.add_argument("--rows", nargs="+", required=True)
    ap.add_argument("--frames-out")
    ap.add_argument("--eos-id", type=int, default=7)  # id 7 ends the labels in the pinned TRAIN-FRAMES-v2 file
    a = ap.parse_args()
    from tokenizers import Tokenizer
    tk = Tokenizer.from_file(a.tokenizer)
    n = over_in = over_out = 0
    max_in = max_out = 0
    fo = open(a.frames_out, "w") if a.frames_out else None
    for path in a.rows:
        for line in open(path):
            r = json.loads(line)
            ids = tk.encode(r["prompt"], add_special_tokens=False).ids + [a.eos_id]
            lab = tk.encode(r["answer"], add_special_tokens=False).ids + [a.eos_id]
            n += 1
            max_in, max_out = max(max_in, len(ids)), max(max_out, len(lab))
            over_in += len(ids) > INPUT_CAP
            over_out += len(lab) > TARGET_CAP
            if fo:
                fo.write(json.dumps({"id": r["id"], "family": r["family"], "learner_text": r["prompt"], "target_text": r["answer"],
                                     "input_ids": [ids], "labels": [lab]}) + "\n")
    print(json.dumps({"rows": n, "max_input_with_EOS": max_in, "max_target_with_EOS": max_out,
                      "over_input_cap": over_in, "over_target_cap": over_out}))
    return 1 if (over_in or over_out) else 0


if __name__ == "__main__":
    sys.exit(main())
