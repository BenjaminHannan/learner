# Why EmbeddingGemma made B2 worse (10-06, 8:15 PM ET)

> **Superseded in part (2026-10-09).** The Short answer below is out of date; see the note above it. Current design:
> architecture/FINISHED-MODEL-2026-10-09.md.

Ben asked: Gemma was trained by Google and is about 100x bigger than B2's reader, so how did it make the model worse?
Labels: **shown** = measured; **suggested** = reasoned from measurements; **untested** = a guess.
Code and raw numbers: branch `claude/custom-reader-talker-4x309r`, commit a9a39f3a0. The probe is `custom_io/diag_eg.py` and its output is
`custom_io/results/eg-diag/DIAG.json`. Runs are in `custom_io/results/40-egw-s200`, `41-egw-s201` and `42-eg-s200`.
Every arm here is compared with plain B2 trained on the same rented 5090 and the same seed (B2V).

## Update (1:45 AM ET 10-07): the window was the cause, and Gemma on top of it beats B2

Each arm against plain B2 trained on its seed (rented 5090s), 2 seeds; numbers are shown, from `custom_io/results/RESULTS-EG2.md` on the branch.

| arm | what it is | pooled-5 change (seed 200 / 201) | cipher_map (200 / 201) | marks |
|---|---|---|---|---|
| R0 | B2 with its +-4 window removed, no Gemma | -6.8 / -6.3 | 12.5 / 2.5 | diagnostic: "the window matters" |
| EGR | Gemma plus each letter, no window | -0.3 / -2.7 | 5 / 2.5 | fail |
| EGE | Gemma added before B2's window | **+1.6 / +2.1** | 97.5 / 95 | fail 2 of 5 (variant +1.7 vs +3; zero-round score 18% on seed 200 vs 5) |
| EGK | EGE with Gemma feeding only the thinker | +1.0 / crashed twice | 100 / - | fail (unstable) |

- **Shown:** removing the window is what lost the cipher. Gemma did not hide anything the thinker needed once the window stayed.
- **Shown:** EGE beats plain B2 on both seeds with every test split up on average (new wording +3.6, new words +2.7).
- **Wrong (my guess):** that EGE's zero-round score came from its answer-writer reading Gemma directly. EGK blocks that path and still
  scores 13.7% with zero rounds; plain B2 itself ranges 1.4 to 6.8 across seeds.
- **Next:** a fresh 6-seed test of EGE against plain B2 (seeds 202-207), marks fixed first in PASS-MARKS.md addendum 15, staged on the PC.
- **Result (added 2026-10-09):** EGE beat plain B2 by +2.67 pooled-5 on 6 of 6 fresh seeds and failed only the zero-round leak mark
  (6.59 against a 4.62 limit). See custom_io/results/39-pc-ege-confirm/RESULTS-EG2.md and PASS-MARKS.md addendum 23.

## Correction (9:10 PM ET 10-06): the letter explanation is wrong as stated

EGR seed 200 (Gemma plus each letter's own code, no window), trained on box A against B2V_s200: pooled-5 **-0.26**, and its cipher_map in_dist
is **5.0** (B2V 100). The check written into addendum 12 before any EGR score existed said cipher_map below 50 on either seed means the
letter explanation is wrong, so point 1 below is **proved wrong** as the cause of the cipher losses. The probe numbers (23% vs 99.9%) are
still measured facts; they just do not explain the loss. **Suggested** instead: every losing arm (EGO, EGM, EGW, EGR) also has
`reader_layers: 0`, so none has B2's +-4-letter window, which binds "f" to "=1" before the thinker. R0 (window removed, no Gemma) and EGE
(window kept, Gemma added) test this; they run on rented 5090s (addendum 13, results about 11:15 PM ET). EGR's other changes on seed 200,
in_dist exact: list_index 62.5 to 97.5, order_chain 45 to 75, table_calc 75 to 100; seq_cycle 87.5 to 72.5, digits_parity 97.5 to 85.

> **Superseded in part (2026-10-09).** Do not use the Short answer below. Its point 1 ('Gemma hides the letters') and its closing line
> (give the thinker both, EGR) were proved wrong: the cipher loss came from removing the letter window, and EGR failed (cipher_map 5.0).
> The finished reader keeps the window and puts Gemma in front of it (EGE). Points 2 to 4 are still measured facts. Current design:
> architecture/FINISHED-MODEL-2026-10-09.md, section 2 and section 7 Q3 (Ben: 'Keep').

## Short answer

1. **Gemma hides the letters (shown).** It turns each word piece into one "meaning" vector, and every letter in the piece gets that same vector.
   B2's reader passes each letter through untouched. Many of our tasks need the exact letters: ciphers, letter and digit questions, and
   writing out answers never seen in training.
2. **Gemma helps where meaning matters (shown).** Every Gemma arm gained a lot on the "who is taller / older" chains and on table maths.
3. **EGW's wide thinker made it worse again (shown).** It is 7x bigger but got the same 24,000 updates at the same learning rate. It fit its own
   training data only half as well as the small-thinker Gemma arm.
4. **Not a wiring bug (shown).** Gemma is frozen and in eval mode, with no trainable parameter. Padding does not change its states (largest change
   0.0005 on states of size about 88), and its vectors match the reference ones taken when it was built (cos 0.99996 or better).

So this is not "a custom reader beats Google". It is "the raw letters beat a summary of the meaning" on tasks that need letters. The fix is to give
the thinker both, and that arm (EGR) is training now.

## Evidence

### Every arm without letters loses the cipher task (seed 200, exact %, shown)

| task | plain B2 | EGW (768 thinker) | EGM (2-layer adapter) | EGO (1-layer adapter) |
|---|---|---|---|---|
| cipher_map ("Code: f=1, c=5 ... write daa as numbers") | 100 | 2.5 | 2.5 | 10 |
| order_chain ("who is the oldest?") | 45 | 87.5 | 75 | 72.5 |
| table_calc | 75 | 95 | 100 | 97.5 |
| pooled-5 change vs plain B2 | | -3.39 | -1.18 | -0.73 |
| training loss at the end | 0.017 | 0.109 | 0.060 | 0.057 |

Seed 201, EGW only (EGM and EGO land later): cipher_map 100 to 0, pooled-5 -5.30. Device check: plain B2 on the 5090 minus plain B2 on the PC is
+0.48 / +0.12, so the machine is not the cause.

### How much spelling Gemma's vectors keep (2,040 training questions, held-out 25%, shown)

| read the letter back from... | all letters | letters in cipher questions |
|---|---|---|
| B2's reader output, simple (linear) read | 99.9% | 99.7% |
| Gemma's vector, simple (linear) read | 23.0% | 27.5% |
| Gemma's vector + told where the letter sits in its word piece, 2-layer read | 97.4% | 96.3% |

99.6% of letters sit inside multi-letter word pieces. The letters are still in there, but only a nonlinear decoder that is also told the
letter's place in its piece gets them back. B2's thinker gets neither hint, and it only learns from right or wrong answers.
**Suggested:** that is why it never learned the cipher in 24,000 updates. Its leftover training loss is almost all in the talker that writes
answers letter by letter (gen loss 0.08 vs 0.003).

### No Gemma layer keeps the letters (1,360 training questions, linear read of letters, shown; added 8:15 PM ET)

| layer | 0 (input) | 3 | 6 | 9 | 12 | 15 | 18 | 21 | 24 (last) |
|---|---|---|---|---|---|---|---|---|---|
| linear read | 26.3 | 24.3 | 23.0 | 22.6 | 22.8 | 24.1 | 24.9 | 25.0 | 22.6 |
| linear read + place in the piece | 56.8 | 53.0 | 50.6 | 47.4 | 48.3 | 50.5 | 50.9 | 50.7 | 49.2 |

The letters are already lost at Gemma's input, where each word piece is one token, so the cause is the word pieces, not depth. Reading a middle
layer won't help; giving the thinker the letters will (`custom_io/results/eg-diag/LAYERS.json`).

### Ruled out (shown)

- **Telling the same word from different words.** Gemma does this better than B2's reader (AUC 0.95 vs 0.82 over 268k word pairs). On the
  matching tasks, a repeated word's nearest earlier word is the same word 74% of the time for Gemma vs 83% for B2. This is a small effect, not
  the main cause.
- **Wiring.** See point 4 above.

## What I'd change (one change at a time)

- **EGR, running now (addendum 6/12):** Gemma's vector plus each letter's own code, with no +-4 window. It is judged against plain B2 on the same
  box with the marks fixed in addendum 6, and it lands about 10 PM ET. The letter explanation is **proved wrong if** EGR's cipher_map stays
  below 50 on either seed (written into addendum 12 before any EGR score existed).
- **Untested:** if EGR passes, a wider thinker deserves a longer training budget and a lower learning rate, not the same 24k updates at 1e-3.
