# far-transfer-fable-2026-10-12 (claude-fable-5-1, effort xhigh, normal API)

Returned 2026-10-12 09:39 AM ET; stop_reason: end_turn; input 3,709 tokens, output 22,121 tokens; cost $1.14 at list prices; 324 s. Prompt: api-far-transfer-2026-10-12.md

## 0. One-paragraph diagnosis

**Shown by your data:** the model learns whatever join forms it is fed (L1: 89% full / 69% rank-8 on the test's own forms; L8: 91% on its own 156 glued forms). **Shown:** the self-practice loop almost never feeds it the test's structure (L8: 0.0% rows with two calls side by side; the A10 edit kills ~9,999/10,000 composed drafts; L8's joins survived 1 in 700). **Shown:** transfer to an *unpractised* form is real but weak, and only appears when several layouts were practised *and* the trainable capacity is large (L3 0.5 → L5 36.7 → L6 13.6 at rank 64 vs 5.2 at rank 8). So this is mostly a practice-distribution problem plus an adapter-rank problem, with a modest genuine ceiling on zero-shot composition at this size.

## 1. Ranked explanations

| # | Explanation | Label | Evidence / cheap check |
|---|---|---|---|
| 1 | **Selection by survival.** The maker never produces the test's structure because edits break composed drafts, and the tool's `?` discards them. | **shown** | L8 0.0%; L2/L4 forms dominated by "cell glued to a range call"; 9,999/10,000 killed. L1 proves the form is learnable when supplied. |
| 2 | **Rank-8 add-on is too small to carry a new skill across forms.** | **shown** | L5 vs L6: unseen layout 5.2 → 13.6, new pairs 9.8 → 56.9; L1: 69 vs 89. The nightly loop runs at rank 8, so its ceiling with *perfect* data is ~70. |
| 3 | **Layout variety is what makes the join rule abstract.** One layout → the model keys on surface strings; five → it recombines brackets × `*` into `(K)*(J)` at 37 (full weights). | **shown** (effect) / **suggested** (mechanism) | L3 → L5. The mechanism I'd bet on: the conv reader (window 5 × 2 blocks ≈ 9 chars) hands the thinker n-gram-like features, so `)*(` is a *new feature* unless `)+(` and `*` were both seen. |
| 4 | **The missing structure is specific:** two multi-call chains, then one call whose two operands are both tape results (ADD r1 r2). L8's joins are mostly "prompt number + latest result". | **suggested** | Check without training: split your F4 log by pair type (range+range vs range+cell) and by *first-error position*. If K and J chains are right and the final call's operands are wrong, this is it. **Missing fact:** whether pre-training contains calls on two earlier results; if plentiful, this drops to rank 6. |
| 5 | **Rows per form.** L1 ≈ 3,000/layout → 89; L5 ≈ 1,200 → ~55 on the practised half; L8 ≈ 38/layout. | **suggested** | Fits the numbers; not isolated. |
| 6 | **Teacher-forcing error compounding** over 3–7 calls. | **untested** | Measure per-call accuracy with gold prefix vs own prefix. |
| 7 | **16 number slots.** Not the F4 cause (near prompts need ≤ 13 runs) but likely the far cause: a 6×3 grid alone has 18 digit runs, so later cells are reachable only char-by-char. | **suggested** | **Missing fact:** digit-run count of a far prompt. If ≤ 16, drop this. |
| 8 | **Per-round op head.** Join needs only ADD/MUL; not limiting. | **suggested** | — |
| 9 | **Model size.** | **untested** | Lowest priority: 3M hits 89 when shown the form and fits 156 own layouts at 91. Size might lift the 37 → higher (see §4). |

**Verdict:** not "no compositional generalisation at 3M". It is "no composition from *one* practised layout, weak composition from *several*, and a loop that never practises the structure at all." The first two parts are the real 3M ceiling; the third is cheap to fix.

## 2. Is L9 fair?

**Fair parts:** pieces and symbols come only from the help page; "whole formula" is defined by the tool (replace by `1` → answers `1` with no steps), which is domain-agnostic; the tool is the only filter; postfix forms that the tool will reject are included, which shows the list wasn't trimmed to the test.

**Smuggled part:** the 6 templates were written by you with F4 in view, and two of them *are* F4's forms. With equal quota per (form, symbol), L9 ≈ L1 with help-page pieces. So a pass (which I expect, given L1/L6 — unless the grids stay on the help page's 3-row single-digit grid; **missing fact**) tells you "a generator that only needs the help page can teach F4," not "the loop invents it."

**Bigger issue (shown by you):** L9 is not a test of the self-practice loop, because the A10 edit step would destroy its ring. Report L9 as *generator learnability* and run a separate L10 = this generator inside the real nightly loop.

**Where the line is.** Fair = (i) vocabulary (pieces, symbols, wrappers) extracted from the help page by a rule written before looking at the test; (ii) the tool is the only filter; (iii) the same rule would work on any other help page. Smuggled = template lists, quotas or filters chosen because the test uses them. Practical check: would your rule produce the same 6 forms if F4 used `K-J` and `(K)/(J)`? If yes, fair.

## 3. Three changes, one at a time (run each at rank 64 — see change 3)

**Change 1 — edit the leaves, join last, repair instead of discard.**
Mechanism: take two drafts that have *already* passed editing and the tool on the same grid; join them with one help-page symbol in one of the help page's own infix shapes (`X+Y`, `X-Y`, `X/Y`, wrapped `(X)`). If `?`, redraw only the symbol/order (≤ 5 tries) before discarding. Keep as a "join row" only if the composite's tool working contains both pieces' workings plus one extra call (tool-only structure check, no domain knowledge). Also put composites in the stop-rule quiz, or the loop stops before practising them.
Pass marks: composite keep-rate ≥ 10% (from 0.01%); ≥ 30% of kept rows pass the structure check; after the usual run, 2 seeds, F4 ≥ 25, near ≥ 40.
Proved wrong if: keep-rate and structure marks are met but F4 < 8 — then form isn't the problem; run the first-error probe from §1 row 4.

**Change 2 — equal quota across join shapes derived from the help page.**
Mechanism: abstract every infix expression in the help page into a template with holes; fill quota per template by redrawing until met, so the tool's rejection bias doesn't leave only the easiest shape. Rationale: L3 → L5.
Pass marks: on one shape deliberately withheld from practice (e.g. `(K)+(J)`), ≥ 15; practised shapes ≥ 40.
Proved wrong if: withheld ≤ 5 while practised ≥ 40 → variety doesn't buy transfer in the loop; only a splitter or a bigger model remains.

**Change 3 — nightly add-on rank 8 → 64** (training side, **shown** effect).
Pass: with changes 1+2, ≥ 10 points over rank 8, old skills within 2 points (L6 shows no forgetting). Proved wrong if gain < 5.

## 4. Bigger model or a splitting tool?

The splitter's payoff needs no training: F4 ≈ p(K) × p(J) × p(ADD two results) ≈ 0.7 × 0.7 × ~0.95 ≈ 45–50 on near, using your single-kind scores (**suggested**). It is a legitimate outside tool, but then the *system* joins, the model doesn't — say so in any write-up. Neither option fixes far if the 16-slot cap holds.

**The one test that tells them apart:** run the L5 protocol (5 layouts, `(K)*(J)` held out, full weights) on the 10M checkpoint (~9 h CPU). Marks fixed now: unseen layout ≥ 60 → size genuinely buys composition, scale; 35–45 → size is not the lever, use change 1 (cheapest) or the splitter. I would run change 1 first anyway: 3 h, and it tests the diagnosed cause directly.

## 5. Plain-language summary

Your model is a good copier, not a bad learner: whatever formula shapes it practises, it learns (up to ~90%). The problem is that its practice-maker almost never produces the test's shape — two separate calculations, then one call that adds or multiplies their results — because the editing step breaks such drafts and the tool throws them away. Fix that first: edit each small piece, check it, *then* glue two checked pieces together, and retry a different symbol instead of discarding. Also raise the nightly add-on from rank 8 to 64; your tests show rank 8 can't carry a new skill across shapes. Give the loop several join shapes, not one, because the model only generalises when it has seen variety. L9 proves a help-page-only generator can teach the join, but not that the loop invents it. A bigger model is worth one test; a splitting tool would work but means the model isn't doing the joining.
