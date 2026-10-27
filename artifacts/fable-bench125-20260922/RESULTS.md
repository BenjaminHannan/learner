# Exp 125 RESULTS — same-metric table: borrowed SmolLM2-360M vs joined-up agent

Registered run 2026-09-22, Mac CPU, offline, OMP/MKL=1, HF_HUB_OFFLINE=1,
`uv run --offline --no-project --python 3.12 --with torch --with numpy
--with transformers python -B scripts/fable_bench125_run.py --run`.
One scorer for every cell: exp-113 scorer v2 (answer value = text after
final " is "/" are ", exact normalised match vs gold+aliases = correct;
abstain = the loop's own decline forms on word boundaries) plus a
"contains gold" column. SmolLM2 Fable-Edit rows RE-SCORED from exp-66
saved answers (no re-run); SmolLM2 4-hop rows FRESH (same prompts, greedy
<= 16 tokens, cached model files, no downloads); loop rows READ from
existing JSONs, NOT re-run. Full 200+200, no --limit. 727.1 s wall-clock.

## Table (arm x split x correct / abstain / wrong / contains-gold, n=200 each)

| arm | split | correct | abstain | wrong | contains-gold |
|---|---|---|---|---|---|
| smollm-incontext | fable_edit_200 | 52 | 0 | 148 | 67 |
| smollm-raglite | fable_edit_200 | 41 | 0 | 159 | 58 |
| smollm-incontext | s2fresh_4hop | 52 | 0 | 148 | 57 |
| smollm-raglite | s2fresh_4hop | 33 | 0 | 167 | 38 |
| loop102 (read) | fable_edit_200 | 150 | 50 | 0 | 150 |
| loop102 (read) | s2fresh_4hop | 0 | 70 | 130 | 5 |
| loop113 (read) | fable_edit_200 | 150 | 50 | 0 | 150 |
| loop113 (read) | s2fresh_4hop | 145 | 50 | 5 | 146 |
| loop113b (read) | fable_edit_200 | 150 | 50 | 0 | 150 |
| loop113b (read) | s2fresh_4hop | 145 | 50 | 5 | 146 |

JSON: `fable_bench125_summary.json`. Row JSONLs per arm x split in this folder.

## Marks

| Mark | Result |
|---|---|
| C1 v2-correct on exp-66 in-context Fable-Edit answer items within ±3 of contains-gold 67 | FAIL (52 vs 67, diff -15: free-text answers mention gold without exact-matching it, and v2 extraction only rescues gold-after-"is" phrasing) |
| C2 wall-clock < 30 min, no subset | PASS (727.1 s; mid-run slowdown ~140-180 items suggests thermal throttle, still < half budget) |

## Verbatim 4-hop examples, smollm-incontext

1. CORRECT `bench103-s2fresh-4hop-001` Q: "What language is officially spoken in the country where the creator of the spouse of Derek Shepherd is a citizen?" gold Arabic — A: "Arabic".
2. CORRECT `bench103-s2fresh-4hop-003` Q: "In what city, which is the capital of a country, is the director of the original broadcaster of Jimmy Kimmel Live! a citizen?" gold Charleroi — A: "Charleroi".
3. WRONG `bench103-s2fresh-4hop-002` gold Alwernia — A: "The capital of the country that created the sport connected to the position played by R" (cut at 16 tokens).
4. WRONG `bench103-s2fresh-4hop-004` gold Tirana — A: "Yesterday is performed by The Beatles." (answers a bridge fact, not the question).
5. ABSTAIN: none exists — SmolLM2 never emits the loop's decline forms, and "unknown" is not a v2 abstain phrase, so all 148 non-exact are wrong. Substitute 3rd WRONG `bench103-s2fresh-4hop-006` gold French — A: "Arabic".

## Verbatim 4-hop examples, smollm-raglite

1. CORRECT `bench103-s2fresh-4hop-001` (same Q as above) — A: "Arabic".
2. CORRECT `bench103-s2fresh-4hop-009` Q: "What is the capital city of the country whose citizen is the spouse of the author of The Sandman?" gold Prague — A: "Prague".
3. WRONG `bench103-s2fresh-4hop-002` gold Alwernia — A: "The capital of the country that created the sport connected to the position play" (truncated echo of the question).
4. WRONG `bench103-s2fresh-4hop-003` gold Charleroi — A: "Russian Empire" (confident wrong guess).
5. ABSTAIN: none exists (same reason). Substitute 3rd WRONG `bench103-s2fresh-4hop-004` gold Tirana — A: "Alimentum".

## What it means

Same questions, same scorer: on Fable-Edit-200 the notebook agent is
perfect (200/200 right behaviour, 0 wrong) while the borrowed 360M model
gets 52/200 exact (in-context) with 148 wrong; on fresh 4-hop the fixed
agent (loop113/b: 145/50/5) beats SmolLM2 in-context (52/0/148), and
top-3 retrieval hurts the 4-hop score (33 vs 52) because 3 of 8 sentences
drop bridge facts.

## What it does not mean

Not a public leaderboard: a 360M general model vs a purpose-built
notebook agent on the agent's home turf. SmolLM2's 52/200 on 4-hop
(celebrity entities) likely includes pretraining leakage, not 4-hop
reasoning — taught-vs-known is not separated here. Its 0 abstains are a
scorer-form mismatch (v2 abstain = the loop's decline wording), not proof
it never hedges: it says "unknown", which v2 counts as wrong on
gold-empty items.

## Deviations

None from the brief: sealed PASSMARKS before running (SEAL.sha256.txt),
predictions P125.1–P125.6 in the ledger before running, no existing file
edited, no commits, no installs, Mac CPU only, every case reported.

## Questions for Ben

None. Conservative default taken: applied scorer v2 byte-for-byte even
where it punishes SmolLM2's "unknown" phrasing, and said so above.

## Reproduce

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 HF_HUB_OFFLINE=1; uv run
--offline --no-project --python 3.12 --with torch --with numpy
--with transformers python -B scripts/fable_bench125_run.py --run
