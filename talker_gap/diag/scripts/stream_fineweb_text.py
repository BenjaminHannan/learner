# Stream raw FineWeb-Edu text back out of the tok32k shard (tokens_0000.bin + tokens_0000.idx.npy).
# Doc i = tokens idx[i]:idx[i+1] (last doc ends at end of .bin). Each doc starts with <|bos|> (id 0) then a <web> tag (id 11).
# Usage: stream_fineweb_text.py <max_chars> [--show N]   -> prints doc/char counts; never writes the text to disk.
import sys, time, numpy as np
from tokenizers import Tokenizer
TOK = '/Users/ben-hannan/Desktop/projects/desmos-llm/tokenizer/tok32k/tokenizer.json'
BIN = '/Users/ben-hannan/desmos-data/tok32k/fineweb_edu/tokens_0000.bin'
IDX = '/Users/ben-hannan/desmos-data/tok32k/fineweb_edu/tokens_0000.idx.npy'

def docs(tok, t, idx, ends, start=0):
    for i in range(start, len(idx)):
        yield i, tok.decode(t[idx[i]:ends[i]].astype(np.int64).tolist(), skip_special_tokens=False)

def main():
    max_chars = int(sys.argv[1]); tok = Tokenizer.from_file(TOK)
    idx = np.load(IDX); t = np.memmap(BIN, dtype=np.uint16, mode='r')
    ends = np.append(idx[1:], t.shape[0])
    t0 = time.time(); chars = 0; n = 0
    for i, s in docs(tok, t, idx, ends):
        chars += len(s); n += 1
        if chars >= max_chars: break
    print({'docs_read': n, 'chars': chars, 'tokens_used': int(ends[n-1]), 'seconds': round(time.time()-t0, 1),
           'chars_per_token': round(chars / int(ends[n-1]), 3), 'last_doc_index': n-1})
    # round-trip check on the first 3 docs: does re-encoding the decoded text give back the same ids?
    for i in range(3):
        ids = t[idx[i]:ends[i]].astype(np.int64).tolist(); s = tok.decode(ids, skip_special_tokens=False)
        re_ids = tok.encode(s, add_special_tokens=False).ids
        print('roundtrip doc', i, 'ids_len', len(ids), 'reencoded_len', len(re_ids), 'exact_match', re_ids == ids)
main()
