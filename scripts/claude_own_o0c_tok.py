"""own-O0c tokenizer trainer (plan 01-own-ear-mouth-plan.md, Task 2.1).

Trains an 8,192-token byte-level BPE with CASE KEPT, using the `tokenizers`
library when it is installed offline. If `tokenizers` is not importable it
reports that fact on stdout and exits with code 2 (the pipeline then stops
before step 3 of the O0c task, per the brief).

No lower-casing, no Unicode normalisation: names and the typo guard need the
original case. Byte-level pre-tokenizer => full coverage, <unk> unused.

Run with:
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with tokenizers \
      python -B scripts/claude_own_o0c_tok.py --train-files a.txt b.txt \
      --out tokenizer.json
"""

import argparse
import json
import sys

VOCAB_SIZE = 8192
SPECIAL_TOKENS = ["<pad>", "<unk>", "<s>", "</s>", "<SEP>", "<ME>", "<WE>"]


def train_bpe(train_files, out_path, vocab_size=VOCAB_SIZE):
    try:
        from tokenizers import Tokenizer
        from tokenizers.models import BPE
        from tokenizers.trainers import BpeTrainer
        from tokenizers.pre_tokenizers import ByteLevel
        from tokenizers.decoders import ByteLevel as ByteLevelDecoder
    except ImportError:
        print(
            "REPORT: `tokenizers` library is not installed offline; "
            "cannot train the 8,192-token byte-level BPE. "
            "Stopping before step 3 per the O0c brief."
        )
        return 2
    tok = Tokenizer(BPE(unk_token="<unk>"))
    # No normalizer: CASE KEPT (names, typo guard).
    tok.pre_tokenizer = ByteLevel(add_prefix_space=False)
    tok.decoder = ByteLevelDecoder()
    trainer = BpeTrainer(
        vocab_size=vocab_size,
        min_frequency=2,
        special_tokens=list(SPECIAL_TOKENS),
        show_progress=False,
    )
    tok.train(list(train_files), trainer)
    tok.save(out_path)
    info = {
        "vocab_size": tok.get_vocab_size(),
        "requested": vocab_size,
        "case": "kept (no normalizer)",
        "pre_tokenizer": "ByteLevel(add_prefix_space=False)",
        "special_tokens": list(SPECIAL_TOKENS),
        "unk_id": tok.token_to_id("<unk>"),
        "train_files": list(train_files),
    }
    print(json.dumps(info, indent=1))
    # Case check: 'Mira' and 'mira' must be different token sequences.
    a = tok.encode("Mira").ids
    b = tok.encode("mira").ids
    print("case_check Mira=%s mira=%s distinct=%s" % (a, b, a != b))
    if a == b:
        print("FAIL: case was not kept", file=sys.stderr)
        return 1
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--train-files", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--vocab-size", type=int, default=VOCAB_SIZE)
    args = ap.parse_args(argv)
    if args.vocab_size != 8192:
        print("note: non-standard vocab size %d" % args.vocab_size)
    return train_bpe(args.train_files, args.out, args.vocab_size)


if __name__ == "__main__":
    raise SystemExit(main())
