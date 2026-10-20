# Bid C card: width on the B2 creative model (DRAFT, UNSEALED, 2026-10-20)

**Status: draft for sealing. NOT sealed. Nothing books against it.**
- The bid choice (Bid C) and the axis call (depth-first, 2(b) not taken) reached this session as a coordinator relay of Ben's general "unblock them" instruction, not as Ben's words in this session. They are recorded here as **relayed, pending Ben's in-session confirmation**.
- Sealing = committing this file with the open rulings below filled in, then quoting its commit hash before any run.

Labels: **shown** = read from code or results (fact sheet of 10-20, citations in the session record); **suggested** = this card's choice, open to ruling.

## 1. The question and the one change

**Question:** with nothing else changed, does a wider B2 creative model find more right answers on held-out puzzle kinds after the creative sleep?

**One change: width.**
- Base: fixed B2, d256 / 4 heads, 3,302,481 params.
- Wide: fixed B2, d384 / 6 heads, 7,223,071 params. **2.21× non-embedding** (2.205, CPU count, shown); 2.19× total.
- Every wording uses the measured multiple, never "2×".
- The 2.22× figure (Q53) is Bid A's `tool` model. B2's own measured multiple is 2.21×.

**Held fixed (shown, the C2b recipe):**
- the parent recipe (`--model ledger --cfg '{"copy":true}' --steps 24000 --batch 256 --lr 1e-3 --bf16`);
- the warm-up (2,048 add/mult rows, 4 visits, lr 3e-4);
- N′ (stepping-stone sleep, 2,048 rows, 4 visits, lr 3e-4);
- the DEV temperature rule (grid 0.5–6.0);
- the nights: 2 per arm, lr 1e-3, 32 visits, batch 64 = 16 skills + 16 warm + 32 night records, fresh AdamW per night;
- creative `--seed 0`, as in C2b.

All the creative-stage lrs were set at 3M and stay fixed (one change). The C8 analogue is not available in the creative code, which is a known confound (§6).

## 2. Rulings needed before sealing (open)

| # | Ruling | Default this card proposes |
|---|---|---|
| R1 | **Which fixed B2.** Both arms need the 9-register / 8-letter GEN bug fixed. | **(A) custom_io B2 plus a ported `caps.py`** (the 8a-G import-fixed overlay, sha 3da2dfbb) with a minimal caps JSON: `max_ans 35`, `n_reg 36`, everything else at today's values. Smallest change, and the ledger code needs no edit. (B), the 8a-G `src-b3` B2, changes loops and workspace too, so it is not one change. |
| R2 | **The test.** The sealed C2b test (sha 2bdadb18…) **was opened and scored on 10-16**, and the roadmap says "opened once". | **A fresh sealed test, "C2c"**, drawn by the same generator on the same five held-out kinds (about 512 rows, about 102 per kind), with the seed named in a commit before generation (the HO2 / VAL pattern). The old test is not re-read. Re-reading it needs Ben's explicit ruling. |
| R3 | **Arms.** c2b.py always builds and scores all five arms (N′, W, R, H, M); dropping H and M needs code edits. | **Run all five, read only N′, W and R.** No creative-code change beyond §5. H and M are printed as report-only. |
| R4 | **Bars.** Any bar change goes to Ben. | The house form in §3, sized from Bid C's own sigma_d. |

## 3. Readout and pre-registered marks (house form)

**Unit:** the seed-index i (paired parents P_i at both widths). Every statistic is over seed-indices, never over questions or replicates (house rule; `custom_io/pilot_bars.py`, review head a2a83f9f0).

**Headroom kinds (fixed now, from the C2b record):** kinds where base W first-try was < 50%: **affine (1.5%), double_add (16.7%), sq_plus (14.4%)**. Square (94.7%) and last_digit (69.1%) are near ceiling for search, so they are report-only.

**Primary contrast:** d_i = W first-try on the headroom kinds (points)_wide − (same)_base.
**Co-headline (report):** pooled (W−N′)_wide − (W−N′)_base.

**S** = max(sigma_d measured at the gate, floor 3.0). The floor is the C2b between-parent sd of W−N, 3.15 rounded down. It is a floor, not a bar.

| Verdict | Condition (all must hold) |
|---|---|
| **SIZE (width helps)** | mean d ≥ max(10, 2·S) **and** d_i > 0 on every seed-index (worst-seed check) **and** no headroom kind's mean d < −2 (per-kind check) **and** the guards below hold |
| **NOT SIZE (width ruled out at this power)** | mean d < max(5, S) **after the horizon extension**: a KILL is horizon-locked (§4) |
| **UNRESOLVED (designed)** | sigma_d > 6 at the cap of n = 10, or neither verdict reached. The tripwire is 6 and not v2's 4 because C2b's single-size spread already implies sigma_d ≥ about 4.5 if parents don't correlate across widths (suggested). |
| **GUARD FAIL (overrides)** | skills harm > 2 points on any parent at either width (N′ minus W, pooled-5 chain families; the live harm guard), **or** the wide practised check (256 fresh add/mult, reach@32) more than 2 points below base |

- **Seed buying:** tranches of 2 seed-indices until SE(d) ≤ 2.0, cap n = 10.
- **Printed beside every result:** the model-free blind baseline per kind (right at 1k / 6k / 50k candidates), N′ per width, and the by-kind table.
- **The result that would prove the size framing wrong:** after the extension, mean d < max(5, S) with SE ≤ 2.0. Width at 2.21× then does not move headroom-kind first-try by even max(5, S) points.
- **Also wrong:** if base N′ already scores within 5 points of base W on the headroom kinds (the sleep, not size, is spent), the contrast is uninformative and is reported as such.

## 4. Seeds, tranches, venue

**Seeds:** parent seed P_i = 700 + i (701–705 first), the same at both widths. Calibration P_0 = 700 (never in the verdict). Purchases use 706–710. The creative seed is 0 for all, as in C2b. The extension is pre-named on indices 1 and 2.

| Tranche | Contents | Gate after |
|---|---|---|
| Cal | P_0 at both widths: parent plus the full creative stage. Measures time per stage on BensPC and checks the caps port loads | Runs end to end; parent DEV recorded |
| A | Indices 1–3 at both widths | **Sigma gate:** compute sigma_d (n = 3, reported, not used as a verdict); size the tranche-B purchase |
| B | Indices 4–5, then purchases in 2s to SE ≤ 2.0, cap 10 | Verdict check against §3 |
| Ext (only if a KILL reading) | Indices 1–2: parents retrained at 48k updates at both widths, then the creative stage | The KILL stands only if it holds here |

**Venue: BensPC, $0 (preferred).**
- Parents go as a `custom_io/queue_local/NN-pc-bidc.txt` queue.
- The creative stage goes as a `creative/MAC-JOB`-style card, run with `python3 -m creative.c2b`.
- From the record (shown): 24k-update parents took 59–253 min, shared three ways. The creative-stage time is **not recorded** (only an untested estimate of 3–3.5 h per parent), so Cal measures it.
- **No Vast portion is planned.** If BensPC can't take it, a Vast bid with a hard stop goes to the coordinator first.

## 5. Code that must pass review before Cal (drafts, none written yet)

1. Port `custom_io/g8a/caps.py` (overlay 3da2dfbb) and the 6-line `--caps` flag into `custom_io/train.py`, plus `caps-bidc.json`.
2. `creative/c2b.py`: call `caps.apply` before `load_parent` in train and score, because caps are module globals and checkpoints won't load otherwise. Expose `--parents` and `--caps` on the CLI. Add a test-path argument for C2c.
3. A C2c generation script, with the seed named in a commit before it runs.

## 6. Known confounds (named, not neutralised)

- **lr transfer:** the creative-stage lrs were set at 3M and are held fixed. There is no C8 log in the creative code.
- **Data ceiling:** the headroom-kind restriction and the printed blind baseline address it; square and last_digit are report-only.
- **Training length:** handled by the horizon-locked extension.
- **Sleep temperature** is re-picked per parent by the frozen DEV rule, so it can differ by width. It is recorded per parent.
