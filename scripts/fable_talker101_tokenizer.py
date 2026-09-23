"""Exp 101: train a 4,096-token byte-level BPE on the TRAIN split only, then encode.

Train text = a fixed-seed sample of train stories EXCLUDING the sealed val
indices. Writes tokenizer.json, train.bin / val.bin (uint16 token ids, stories
joined with EOS), and token_counts.json. Requires `tokenizers` (offline cache).
"""
import argparse, json, os
import numpy as np

VOCAB = 4096
SEED = 101
N_TRAIN_SAMPLE = 200_000  # stories used to fit BPE merges (train-only)


def story_iter(data_dir, files, row_counts, want_global, batch_cols=("story",)):
    import pyarrow.parquet as pq
    want = set(int(i) for i in want_global)
    g0 = 0
    for f, n in zip(files, row_counts):
        if g0 + n <= min(want) or g0 > max(want):
            g0 += n
            continue
        t = pq.read_table(os.path.join(data_dir, f), columns=list(batch_cols))
        stories = t.column("story").to_pylist()
        for i, s in enumerate(stories):
            if g0 + i in want:
                yield s
        g0 += n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data/open/simplestories")
    ap.add_argument("--out-dir", default="artifacts/fable-talker101-20260921")
    args = ap.parse_args()
    from tokenizers import Tokenizer
    from tokenizers.models import BPE
    from tokenizers.trainers import BpeTrainer
    from tokenizers.pre_tokenizers import ByteLevel
    from tokenizers.decoders import ByteLevel as ByteLevelDec

    files = [f"train-{i:05d}-of-00007.parquet" for i in range(7)]
    import pyarrow.parquet as pq
    counts = [pq.ParquetFile(os.path.join(args.data_dir, f)).metadata.num_rows for f in files]
    total = sum(counts)
    val_idx = np.load(os.path.join(args.out_dir, "fable_talker101_val_idx.npy"))
    val_set = set(int(i) for i in val_idx)

    rng = np.random.default_rng(SEED)
    cand = np.array([i for i in range(total) if i not in val_set])
    # BPE fit sample: deterministic strided pick over shuffled candidates
    shuff = rng.permutation(len(cand))
    fit_idx = np.sort(cand[shuff[:N_TRAIN_SAMPLE]])

    tok = Tokenizer(BPE(unk_token="<unk>"))
    tok.pre_tokenizer = ByteLevel(add_prefix_space=False)
    tok.decoder = ByteLevelDec()
    trainer = BpeTrainer(vocab_size=VOCAB, special_tokens=["<eos>", "<unk>"],
                         show_progress=False)
    tok.train_from_iterator(story_iter(args.data_dir, files, counts, fit_idx),
                            trainer=trainer, length=int(len(fit_idx)))
    tok.save(os.path.join(args.out_dir, "fable_talker101_tokenizer.json"))
    eos = tok.token_to_id("<eos>")
    assert tok.get_vocab_size() == VOCAB, tok.get_vocab_size()

    def encode_to_bin(idxs, name):
        path = os.path.join(args.out_dir, name)
        # growable memmap via temp .npy then convert: simpler to accumulate in lists per file chunk
        out = open(path, "wb")
        n_tok, n_story = 0, 0
        arr16 = np.zeros(1 << 20, dtype=np.uint16)
        pos = 0

        def flush():
            nonlocal pos
            out.write(arr16[:pos].tobytes())
            pos = 0

        import pyarrow.parquet as pq2
        want = sorted(int(i) for i in idxs)
        ptr, g0 = 0, 0
        for f, n in zip(files, counts):
            while ptr < len(want) and want[ptr] < g0:
                ptr += 1
            lo = ptr
            while ptr < len(want) and want[ptr] < g0 + n:
                ptr += 1
            if ptr == lo:
                g0 += n
                continue
            local = [w - g0 for w in want[lo:ptr]]
            t = pq2.read_table(os.path.join(args.data_dir, f), columns=["story"])
            stories = t.column("story").to_pylist()
            for li in local:
                ids = tok.encode(stories[li]).ids + [eos]
                for v in ids:
                    if pos == len(arr16):
                        flush()
                    arr16[pos] = v
                    pos += 1
                n_tok += len(ids)
                n_story += 1
            g0 += n
        flush()
        out.close()
        return n_story, n_tok

    train_idx = np.array(sorted(set(range(total)) - val_set))
    ntr_s, ntr_t = encode_to_bin(train_idx, "fable_talker101_train.bin")
    nv_s, nv_t = encode_to_bin(val_idx, "fable_talker101_val.bin")
    info = {"vocab": VOCAB, "eos": eos, "bpe_fit_stories": int(len(fit_idx)),
            "train_stories": ntr_s, "train_tokens": ntr_t,
            "val_stories": nv_s, "val_tokens": nv_t}
    json.dump(info, open(os.path.join(args.out_dir, "fable_talker101_token_counts.json"), "w"), indent=2)
    print(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()
