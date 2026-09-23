# RESULTS — own-O0d2 diagnosis-driven follow-up: PASS (5/5 marks)

Registered run once: scripts/claude_own_o0d2_test.py (10 s wall clock on the
Mac CPU, 1-minute load ~47 at start). New files only; no sealed o0d file
edited; no TEST-ONLY panel touched; toy data only (fictional names).

## Marks table (integer counts)

| Mark | Bar | Result | Verdict |
|---|---|---|---|
| Pown0d2.1 all 8 unit tests pass | 8/8 pass | 8/8 pass (bpe-trains, bpe-roundtrip, word-ids, mask-blocks-cuts, decode-whole-word-only, hungarian-optimal, forward-shapes, relation-table-153) | PASS |
| Pown0d2.2 audit still exactly 32,850,051 | diff <= 0.005, exact number reported | total 32,850,051, diff 0.000000; all 7 parts match plan S7.1 exactly (embeddings 4,194,304; encoder 25,174,528; slot_layer 1,052,672; pointers 1,572,864; question_pointers 524,288; classifiers 329,859; special_tokens 1,536) | PASS |
| Pown0d2.3 kill test identical | sha256 equal at step 60 | kill landed on ckpt_step30, resumed to step 60, A=054dbec63839 B=054dbec63839 (same hashes as o0d, trainer path unchanged) | PASS |
| Pown0d2.4 fuzz 10,000 random-logit draws: 0 non-whole-word spans decoded | 0 | 0 non-whole-word decodings / 10,000 draws (span + owner checks) | PASS |
| Pown0d2.5 o0d smoke (toy frames, <= 10 min) loss still falls | mean(last 10%) < mean(first 10%) | 120 steps, early 1.3347 late 0.3635 (falls; identical to o0d smoke 1.3347 -> 0.3635), 2 s wall | PASS |

MLM pilot 15 steps ran to completion (reported, not a mark). Hungarian
matcher gap vs brute force 0.00e+00 (20 seeds).

## Every move

Unit checks 8/8 pass (the 3 o0d failures — bpe-roundtrip, mask-blocks-cuts,
decode-whole-word-only — now pass); audit exact; kill byte-identical with
hashes matching the o0d run; fuzz 0/10,000; smoke loss falls; MLM pilot runs.
No TEST-ONLY panel touched. Toy data only (fictional names, generated
in-task). Relation table read read-only (153 relations confirmed).

## The ONE change (model diff vs sealed scripts/claude_own_o0d_model.py)

Only two method bodies differ; everything else byte-identical (full
`diff -u` output below; architecture, parameter counts, training code
untouched):

```diff
-    def decode(self, ids):
-        return b"".join(self.vocab[i] for i in ids).decode("utf-8", errors="replace")
+    def decode(self, ids, word_ids=None):
+        if word_ids is None or len(word_ids) != len(ids):
+            return b"".join(self.vocab[i] for i in ids).decode("utf-8", errors="replace")
+        # words regrouped by word_ids and joined with single spaces; ids alone
+        # cannot locate the spaces (BPE never merges across them)
+        words = []
+        cur = []
+        cur_w = None
+        for tok_id, w in zip(ids, word_ids):
+            if w != cur_w:
+                if cur:
+                    words.append(b"".join(cur))
+                cur = [self.vocab[tok_id]]
+                cur_w = w
+            else:
+                cur.append(self.vocab[tok_id])
+        if cur:
+            words.append(b"".join(cur))
+        return b" ".join(words).decode("utf-8", errors="replace")
```

```diff
         for i in range(1, n):
             if word_ids[i] == word_ids[i - 1]:
                 start[i] = False
-            else:
-                end[i - 1] = False
+                end[i - 1] = False  # mid-word: previous token is not a word end
+            # else: token i-1 really ends a word; end[i-1] stays True
```

Test pointer-swaps (scripts/claude_own_o0d2_test.py vs the sealed o0d
test): model import -> claude_own_o0d2_model; trainer import -> the
claude_own_o0d2_train shim; ART dir -> claude-own-o0d2-20260923; both
subprocess train calls -> scripts/claude_own_o0d2_train.py; round-trip check
passes word ids (`tok.decode(*tok.encode(s))`); fuzz reference mask built
with the corrected rule (the o0d copy of that rule carried the same flipped
condition as the bug). Train shim (scripts/claude_own_o0d2_train.py):
aliases `claude_own_o0d_model` to the o0d2 model module, then imports the
sealed o0d trainer unchanged and re-exports its entry points; not one
trainer line copied or edited.

## Deviations

D1: fuzz reference mask and round-trip call updated as above (required to
test the fix rather than re-test the old bug; documented in the test
docstring). D2: predictions were appended to the ledger before the run
(Pown0d2.1–5, 5 lines) and PASSMARKS.md recorded before the run, per the
registration protocol. No other deviations from task order.

## What it means (plain high-school English)

The one flipped condition was the whole problem: now the ear can only point
at whole words again (0 bad spans out of 10,000 random tries, and the 3
failing checks pass), spaces come back when decoding, and nothing else moved
— same size down to the last number (32,850,051), same kill-and-resume
hashes as o0d, same falling practice loss. The pointer promise holds.

## What it doesn't mean

It doesn't mean the ear reads English well — only that it can no longer
cheat by pointing at half-words. That was a code fix, not a training result.
How well it reads real sentences is still untested and needs the later
stages (pretraining, frame training, blind panels).
