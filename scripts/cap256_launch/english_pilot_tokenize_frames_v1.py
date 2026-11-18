"""G0: native tokenizer pin run for the English pilot (CPU only, no GPU, no network).

Loads the local LFM2.5 tokenizer (local_files_only), records tokenizer file
hashes, builds all 96 TRAIN frames with the v2 serializer (no truncation; any
frame over 64 input / 48 target tokens incl. EOS stops the run and lists every
violation), and writes the frames v2 document with exclusive create. Optionally
checks the inputs-only fresh file against the 64-token input contract and prints
counts only (never the text).

Not run on the Mac: the pinned tokenizer files live on BensPC.
"""
import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import english_pilot_common_v1 as common  # noqa: E402
import english_pilot_runtime_v1 as runtime  # noqa: E402

TOKENIZER_FILES = ('tokenizer.json', 'tokenizer_config.json', 'special_tokens_map.json')


def tokenizer_identity(model_dir, tokenizer):
    model_dir = Path(model_dir)
    files = {name: common.digest(model_dir / name) for name in TOKENIZER_FILES if (model_dir / name).is_file()}
    if 'tokenizer.json' not in files:
        raise ValueError('local tokenizer.json required')
    return {'files_sha256': files, 'class': type(tokenizer).__name__, 'vocab_size': len(tokenizer),
            'bos_token_id': tokenizer.bos_token_id, 'eos_token_id': tokenizer.eos_token_id,
            'add_special_tokens': False}


def build_frames_document(tokenizer, identity, bank, bank_sha256, serializer):
    frames = serializer.build_all_frames(tokenizer, bank)
    document = serializer.frames_document(frames, bank_sha256, identity)
    serializer.validate_frames_document(document, bank, bank_sha256)
    return document


def fresh_length_counts(tokenizer, inputs_path):
    """Counts only; raises nothing so every violation is counted."""
    import eval_english_fresh_windows_v1 as fresh
    items, _ = fresh.load_fresh_inputs(inputs_path)
    lengths = [len(tokenizer.encode(i['learner_text'], add_special_tokens=False)) + 1 for i in items]
    return {'fresh_inputs': len(items), 'max_with_EOS': max(lengths),
            'over_64_with_EOS': sum(n > common.INPUT_CAP_WITH_EOS for n in lengths)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', required=True)
    ap.add_argument('--model-dir', required=True)
    ap.add_argument('--bank', required=True)
    ap.add_argument('--out', required=True, help='new frames v2 JSON (exclusive create)')
    ap.add_argument('--fresh-inputs', help='inputs-only fresh file (counts printed only)')
    args = ap.parse_args()
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(args.model_dir, local_files_only=True)
    bank_path = Path(args.bank)
    if common.digest(bank_path) != runtime.BANK_SHA256:
        raise ValueError('pinned v3 TRAIN bank required')
    serializer = runtime.load_serializer(args.root)
    identity = tokenizer_identity(args.model_dir, tokenizer)
    document = build_frames_document(tokenizer, identity, common.read_json(bank_path), runtime.BANK_SHA256, serializer)
    sha = common.write_new_json(args.out, document)
    report = {'frames_sha256_file': sha, 'frames': len(document['frames']),
              'max_input_with_EOS': max(len(f['input_ids'][0]) for f in document['frames']),
              'max_target_with_EOS': max(len(f['labels'][0]) for f in document['frames']),
              'tokenizer_identity': identity}
    if args.fresh_inputs:
        report['fresh'] = fresh_length_counts(tokenizer, args.fresh_inputs)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
