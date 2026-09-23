# RESULTS — own-O0d ear model code + trainer: FAIL (one diagnosed bug, fix reported but NOT applied)

Sealed files unchanged after the seal (shasum -c: 4/4 OK). No re-seal, no re-run.
Registered test ran once: scripts/claude_own_o0d_test.py (12 s wall clock on the Mac CPU).

## Marks table (integer counts)

| Mark | Bar | Result | Verdict |
|---|---|---|---|
| Pown0d.1 all unit tests pass | every unit test passes | 5/8 pass (bpe-trains, word-ids, hungarian-optimal, forward-shapes, relation-table-153 pass; bpe-roundtrip, mask-blocks-cuts, decode-whole-word-only fail) | FAIL |
| Pown0d.2 audited ear count within 0.5% of 32,850,051 | diff <= 0.005, exact number reported | total 32,850,051, diff 0.000000; all 7 parts match plan §7.1 exactly (embeddings 4,194,304; encoder 25,174,528; slot_layer 1,052,672; pointers 1,572,864; question_pointers 524,288; classifiers 329,859; special_tokens 1,536) | PASS |
| Pown0d.3 kill test identical | sha256 equal at step 60 | kill landed on ckpt_step30, resumed to step 60, A=054dbec63839 B=054dbec63839 | PASS |
| Pown0d.4 0 non-whole-word spans decodable (fuzz 10,000) | 0 | 11,418 non-whole-word decodings / 10,000 draws (span + owner checks) | FAIL |

Smoke (not a mark, reported as run): frame smoke 120 steps, loss 1.3347 -> 0.3635 (falls).
MLM pilot 15 steps ran to completion. Hungarian matcher gap vs brute force 0.00e+00 (20 seeds).

## Every move
Unit checks 5 pass / 3 fail as above; audit exact; kill byte-identical; fuzz fails;
smoke loss falls; MLM pilot runs. No TEST-ONLY panel touched. Toy data only (fictional
names, generated in-task). Relation table read read-only (153 relations confirmed).

## Deviations
None from task order. Two properties of the sealed code are wrong (see diagnosis);
the fixes are reported below and were NOT applied (seal stands, verdict FAIL).

## Diagnosis (one note)
Root cause of all 3 unit failures + the fuzz failure: `ByteBPE.word_start_end`
(sealed scripts/claude_own_o0d_model.py) clears `end[i-1]` at word BOUNDARIES
(`word_ids[i] != word_ids[i-1]`, where token i-1 really is a word end) and never
clears it MID-word (equal ids). So `valid_span_mask` admits nearly every (start,end)
pair (e.g. single-word "sister-in-law", 7 tokens: mask sum 7 instead of 1), and the
decoder — which correctly trusts the mask — returns word-cutting spans. Separately,
`ByteBPE.decode` joins token bytes without spaces ("Mira'sDOGisPip."), so round-trip
fails; decode needs the word ids to re-insert spaces. The independent checker
`is_whole_word_span` itself is correct — that is why it caught the bad decodings.

## Reported (NOT applied) fix diff
```diff
         for i in range(1, n):
             if word_ids[i] == word_ids[i - 1]:
                 start[i] = False
-            else:
-                end[i - 1] = False
+                end[i - 1] = False  # mid-word: previous token is not a word end
+            # else: token i-1 really ends a word; end[i-1] stays True
```
```diff
-    def decode(self, ids):
-        return b"".join(self.vocab[i] for i in ids).decode("utf-8", errors="replace")
+    def decode(self, ids, word_ids=None):
+        # words regrouped by word_ids and joined with single spaces; ids alone
+        # cannot locate the spaces (BPE never merges across them)
+        ...
```
This is a sealed-model-code fix, not a driver-only fix, so it needs a director
re-rule / new task: it was not applied and nothing was re-run.

## What it means (plain high-school English)
The ear's size math is exactly right (32,850,051, same as the plan down to the last
number), training with kill-and-resume works perfectly, and the matching logic is
optimal. But the part that promises "the ear can only point at whole words" is broken
by one flipped condition, so right now it CAN point at half-words. Nothing about this
run says anything about how well the ear reads English — only the tiny smoke loss
falling, which is expected on toy data.

## What it doesn't mean
It doesn't mean the pointer design is wrong, or the plan's counts are wrong, or any
outside data leaked in. It is one small coding bug with big effects, plus a missing
spaces-in-decode detail. Both are fixable in a follow-up task.
