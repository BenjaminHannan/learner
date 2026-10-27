# 120b — Talker mouth raw-decode bugs: diagnosis + one-change fix (Muse)

Follow-up to exp 120. The director's sealed GPU fine-tune (seed 12002,
470 steps, loss 3.01 -> 0.044 in 19 s) scores O1 PASS, O2 486/500, O3 250/250,
O6 FAIL: 313/500 raw decodes unfaithful (bar <= 50). This doc diagnoses all 500
with the director's checkpoint on the Mac CPU (no model change) and proposes
ONE change.

## STEP 1 — diagnosis (scripts/fable_talker120b_diagnose.py, diag-full.json)

Method: re-decode all 500 held-out records with
artifacts/claude-talker120-run-20260922/fable_talker120_ckpt_last.pt via
fable_talker120_mouth.TalkerMouth by import. Buckets (operational rules):
- boundary junk = raw's first content char is ":" or lowercase (every training
  template starts uppercase — a lowercase/colon start is always a fragment);
- truncation = a status-required word (OK/SAVED: owner chain + answer;
  UNKNOWN/FORGOT: subject + surface relation; CLARIFY: name + choice names;
  ABSTAIN: none) with no whole-word match (`word(?![a-z])`, so "Amos" matches
  "Amos's" but not "Amosos's", "Farah" misses "Fara").

Bucket table: (diag-full.json, 500/500 records, 313 unfaithful reproduced exactly)

| status | faithful | boundary-only | truncation-only | both | other | total |
|---|---|---|---|---|---|---|
| OK | 162 | 15 | 0 | 73 | 0 | 250 |
| UNKNOWN | 0 | 36 | 0 | 14 | 0 | 50 |
| ABSTAIN | 6 | 44 | 0 | 0 | 0 | 50 |
| CLARIFY | 0 | 22 | 0 | 28 | 0 | 50 |
| SAVED | 19 | 5 | 10 | 16 | 0 | 50 |
| FORGOT | 0 | 42 | 0 | 8 | 0 | 50 |
| ALL | 187 | 164 | 10 | 139 | 0 | 500 |

Junk starts: "ing"-family 131, ":" 88, "s" 82, misc fragments 2
("ingrmate", "ingrasmate", "ingr", "sin" — all lowercase non-starts).
UNKNOWN/FORGOT/CLARIFY have ZERO faithful raws: their sentences open with
"I/Sorry/Which", whose first token was never supervised, so step 0 always
emits junk. OK often survives step 0 (argmax lands on the name piece) but
loses multi-piece names mid-sentence. All 10 truncation-only cases are SAVED
("Saved:" starts clean; the answer name mangles later).

## Causes

(a) Prompt check: decode prompt ids == training serialisation ids on 500/500
(prompt_mismatch = 0) — decoding is faithful to training; the bug is IN the
training, scripts/fable_talker120_train.py:150-151:
` tgt_mask = (pos > pre) & ...` excludes position `pre`, i.e. the FIRST target
token never gets loss (mask audit: first_target_covered = false; 23 of 24
target tokens masked). At decode step 0 the mixture is unsupervised: p_gen
saturates to 1.0, attention is diffuse (top weight on a bare space piece), and
greedy emits vocab junk ("ing", ":", "s"). The rest of the sentence then
conditions on junk and continues coherently — hence ": Berta's ...",
"ing, I don't know ...", "ing've forgotten ...". (Exp 120's smoke already
fixed two off-by-ones in the causal and target masks; this third one — the
loss mask boundary — was missed.)
(b) Truncation is largely INDEPENDENT: forcing the reference's first token
(12 junk cases) repairs the tail in only ~1/3. Held-out names are 3–4 BPE
pieces (Farah = F+ar+a+h, Ashford = As+h+for+d, Gideon = G+ide+on,
Mabel = M+a+b+el) while train names are short; the copy head emits the first
1–2 pieces then drifts ("Fara", "Gide", "Ma", "Ash", "Umarar",
"Ximenaenaenain"), and copy attention at name steps is misplaced (top weight
on unrelated prefix pieces while emitting function words). Leaked
prefix-marker words ("Sten source", "Vita source") are the same head emitting
serialize vocabulary ("source", "end"-region) instead of copying.

## STEP 2 — ONE change (targets the boundary bucket, present in ~all misses)

Fix the loss-mask boundary in a frozen copy of the trainer
(scripts/fable_talker120b_train.py, sha256
bd7515d7805922a9ac635ba2330206d105c3838a7a00aa82267b066d8967a2a9):
`pos > pre` -> `pos >= pre`, nothing else. Retrain recipe identical to exp 120
(5 epochs, bs 32, ctx 256, lr 1e-4 cosine+warmup, bf16, seed 12002, resume from
the finished exp-101 checkpoint). CPU smoke 100 steps (seed 12001, same smoke
ckpt as exp 120): first20-mean 5.5061 -> last20-mean 3.7325, loss falls;
mask check on 50 train pairs: new mask covers position `pre` 50/50, old drops
it 50/50. The director runs the GPU job. One-line GPU command (BensPC,
after syncing fable_talker120b_train.py + fable_talker101_model.py + data +
tokenizer to C:\Users\benja\talker101\, same pre-checks as exp 120):
`ssh benspc "powershell.exe -NoProfile -NonInteractive -Command \"Invoke-CimMethod Win32_Process -MethodName Create -Arguments @{CommandLine='cmd /c cd /d C:\\Users\\benja\\talker101 & py -3.10 fable_talker120b_train.py --device cuda --ckpt full_run\\fable_talker101_ckpt_last.pt --tok fable_talker101_tokenizer.json --data fable-talker120-data --out fable-talker120b-ft --epochs 5 --bs 32 --ctx 256 --lr 1e-4 --seed 12002 > fable_talker120b_ft.log 2>&1'}\""`
then score on the Mac with scripts/fable_talker120_score.py against the new
checkpoint (O1–O6).

Expected effect (honest): boundary-only misses -> ~0; "both" cases shrink to
their truncation remainder; truncation-only persists (copy-head data problem,
needs its own experiment). O6 may still FAIL after this one change — a FAIL
stays FAIL with this note.

## What it means / What it does not mean

What it means: the 313 misses are two trained-in defects, the larger one a
one-character mask bug with file:line, fixable by retraining with zero recipe
change otherwise. What it does not mean: no decode-side tweak can supervise a
position the loss never saw — re-scoring this checkpoint cannot pass O6; and
the mask fix alone does not promise O6 either, since multi-piece copying is a
separate weakness.
