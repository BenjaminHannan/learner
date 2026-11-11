# far-transfer-opus-2026-10-12 (claude-opus-5-5, effort xhigh, normal API)

Returned 2026-10-12 09:46 AM ET; stop_reason: end_turn; input 3,678 tokens, output 50,775 tokens; cost $1.03 at list prices; 534 s. Served by claude-opus-5-5. Prompt: api-far-transfer-2026-10-12-v1.md

# Why the spreadsheet model learns only the joins it practised

**Labels:** **[shown]** = follows directly from your numbers. **[suggested]** = my inference, consistent with the numbers but not isolated. **[untested]** = nobody has measured it.

---

## 1. Explaining the pattern

### What the numbers say, ordered by how much of the test's structure was practised

| What practice contained | F4 / transfer result | Status |
|---|---|---|
| The test's own forms (L1) | 69 (add-on) / 89 (every weight) | [shown] |
| The test's layout, but new kind pairs (L3, L5, L6) | 10–57 | [shown] |
| A new layout whose two ingredients each appeared elsewhere. L5 had `K*J` (star joining two calls) and `(K)+(J)` (bracketed calls); `(K)*(J)` combines them. | 36.7 every weight, 13.6 rank-64, 5.2 rank-8 | [shown] |
| A new layout whose ingredients never appeared (L3: only `+`, no brackets) | 0.5–0.9 | [shown] |
| Self-practice data (L2, L4, L8). In L8, 0.0% of rows had two calls side by side. | 2–4 | [shown] |

The model recombines ingredients it has practised, partially. It does not invent an ingredient it never practised. Fit is never the problem: every arm learns its own joins at 37–97% **[shown]**.

### Ranked explanations

| # | Explanation | Status | Evidence |
|---|---|---|---|
| 1 | **Data.** Practice lacks the test's structural ingredients: two complete call-chains whose results are both held and then combined, `*` as the top-level join, and bracket groups as operands. | **shown** | Same model and budget: L1 scores 69–89, L2/L4/L8 score 2–4. L3 → L5 takes the unseen layout from 0.5 to 36.7. L4's join step glued mostly digits, giving "call + constant", not "call + call". |
| 2 | **Where updates can go.** A low-rank add-on transfers to new *layouts* worse than full training, but better to new *pairs*. | that it matters: **shown**; why: **suggested** | Unseen layout: 5.2 / 13.6 / 36.7. New pairs: 9.8 / 56.9 / 28.3. The anti-forgetting guard cuts the layout score to 9.3. Full training's layout transfer came with changes that also damaged old skills (90 → 37), though the guard also slowed learning overall, so this is confounded. |
| 3 | **Local reader.** Each character's features see about ±4 characters, so "where piece J starts" is encoded as local strings like `)+M` versus `))*(`. A new layout gives the thinker unfamiliar features. | **suggested** | Fits L3 → L5. Also fits why full training (which can retune the reader) transfers layouts better, *if* the add-on doesn't touch the reader (missing fact). |
| 4 | **Binding shortcut.** L8 formulas seem to hold one range, so "find the range" never had to become "find the range of the piece I'm in". | **suggested** | Follows from L8's forms. Checkable for free (see D3 below). |
| 5 | **Rows per form.** | not the self-practice cause: **shown**; affects fit: **suggested** | L8 fit 156 layouts at about 38 rows each to 78–91%. A real night keeps about 1 joined draft in 700, so in the actual loop "rows per form" is near zero, which is really a validity problem. If F4's halves are equal, L5's practised `K+J` half was about 55, against L1's 89, which suggests fewer rows per layout cost fit. |
| 6 | **Teacher forcing / compounding errors.** | **untested** | — |
| 7 | **Per-round op head.** | **untested**, unlikely | L1 runs joined plans at 89%. |
| 8 | **16 number slots.** | not binding on F4: **shown**; binding on far: **suggested** | F4 needs at most 8 grid values plus 5 reference digits, so at most 13 runs (assuming 2 columns). Far needs 3 columns × 6 rows = 18 values before any reference digit. |
| 9 | **Model size.** | fit and pair transfer: **shown** not limiting; layout transfer: **untested** | — |

### Is this "no compositional generalisation at 3M"?

No.
- Partial recombination is **shown**: new pairs reach 57%, and a new layout reaches 37% when its parts were practised.
- What fails is practice that never contains the parts. That is cheaper to fix: the practice maker must produce them.
- The harder limit is real: robust transfer to genuinely new structures is weak (best 36.7) **[shown]**, and whether size fixes it is **[untested]**.
- Practical consequence **[suggested]**: put composition into the practice maker's rules, or into a splitting tool. Ask the model only to master the finite set of moves those rules produce.

### Free diagnostics (evaluation only, minutes on CPU)

- **D1. Failure anatomy.** On the L5 (every weight) and L8 checkpoints, find the first wrong round on each failed F4 item. Classify it:
  - wrong op,
  - operand copied from the *other* range,
  - final combine using the wrong result slot.
  
  Repeat with the gold tape as prefix. If per-round accuracy is high but end-to-end is low, explanation #6 (compounding) is the cause.
- **D2. Same plan, new surface.** Run the L1 checkpoint (trained on `K+J` and `(K)*(J)`) on `(K)+(J)` and `K*J`. These produce identical calls to the trained layouts; only the brackets change. A large drop supports #3.
- **D3. Pair-type split.** Split the L8 checkpoint's F4 score by pair type: range+range, range+cell, cell+cell. If range+cell is much higher, #4 is the cause.
- **D4. Census.** For any practice maker, before training, count the rows containing each F4 ingredient. L8's 0.0% would have been caught for free.

---

## 2. Is L9 fair?

**It is a fair test of one hypothesis, but not a test of the loop, and it partly smuggles the test's grammar.**

**It bypasses the loop [shown].** A10 edits break about 9,999 of 10,000 such drafts, so a real night would not contain these rows. L9 answers "would this data teach F4?", like L1 does. It does not answer "can the loop make this data?"

**Signs of smuggling:**
- Both F4 layouts appear verbatim among the six forms (`P+Q` and `(P)*(Q)`). The test is therefore in-distribution, so L9 measures fit, not transfer.
- The help page's own two-argument composition is a function call: `MOD(A2,B2)` and `IF(A1>B1,A2,B2)`. That shape is absent from the six forms, while the test's shape is present. That asymmetry is what designer knowledge looks like.
- The postfix forms add few or no rows if the tool rejects them, so they don't balance this out.
- The forms were designed after L1–L8 revealed what F4 needs.
- The pass mark of 25 is low for in-distribution forms (L1 at rank 8 got 69). Passing shows the data isn't useless, not that it matches the generator.

**Not smuggled:**
- Detecting a whole formula by replacing it with `1` uses only the tool.
- The symbols are taken from the page.
- The tool decides which drafts are accepted.

### Where the line is: four checks

1. **Operations, not forms.** The designer writes generic operations: cut a piece, plug a piece in, wrap in brackets, swap. The forms come out of applying them to the page.
2. **Traceability.** Every ingredient can be traced to the help page or to a tool verdict.
3. **Portability.** The same code, applied unchanged to a different tool's help page, still makes sensible practice.
4. **Fixed in advance.** The rules are fixed before test results influence them. Report how often the test's exact forms appear, and why.

There is a grey zone. "Pieces can be plugged into holes" is itself an assumption. It is acceptable because the page displays it: `A1+B2*2` nests a product inside a sum, and `ABS(A1-B1)` nests a difference inside a call. State that assumption openly.

---

## 3. Three changes, one at a time

**Which branch, based on L9:**
- **L9 ≥ 25:** do changes 1 → 2 → 3.
- **L9 ≤ 8:** look at D1 first. Suspect that L9's joins keep the help page's fixed references (`A1:A3`) on 3-row, single-digit grids **[suggested; missing fact]**. Then run change 2 first, as a direct test.
- **In between:** let the per-layout split decide.

Changes 1 and 2 are outside tools the model calls. Change 3 is the model's own choice.

### Change 1: a "holes and pieces" practice maker, replacing L9's listed forms

**How it works:**
- A piece is a *value piece* if replacing it with `1` leaves a formula the tool accepts.
- Holes can be any value piece, including compound ones like `B2*2`.
- Any value piece the tool accepts on its own is also a host formula (for example `=B2*2`).
- Fill 1–2 holes per draft (siblings allowed, depth at most 2) with value pieces from the page, bare or bracketed. Keep what the tool runs.
- Use equal quota per number of calls, not per layout.

**Why it should work:**
- It produces the test's shapes by rule:
  - filling `A1` and `B2*2` in `A1+B2*2` gives `SUM(..)+MAX(..)`;
  - filling both holes of `=B2*2` gives `(MIN(..))*(A2+B1*2)`.
- It also produces shapes the test never uses, like `MOD(SUM(..),MAX(..))`. That is evidence of genericity.
- L8 probably filled one leaf at a time, which would explain its 0.0% **[suggested; missing fact]**.

**Run:** the direct-test protocol at rank 64, in two arms.
- **Arm A:** the maker as described.
- **Arm B:** the same, with every top-level `(·)*(·)` row removed.

Publish the census before training.

**Pass:**
- Arm A: F4 ≥ 25.
- Arm B: the `K+J` half ≥ 40 and the held-out `(K)*(J)` half ≥ 20 (beating L6's 13.6).

**Proved wrong if:**
- Arm A ≤ 8 while L9 passed. L9's success then depended on the listed forms.
- Arm B's held-out half ≤ 8. Joining is then learned per layout, so rely on full coverage (Arm A) or a splitting tool.

### Change 2: edit the grid first, the pieces second, join last (in the real nightly loop)

**How it works:**
- **(a) Find the shared part.** Diff the help examples. The part all 10 share is the grid; the part that differs is the question. This is generic.
- **(b) Edit the grid.** Use A10 edits. Keep a new grid if the tool still runs at least half of the unedited questions on it.
- **(c) Build a pool.** Edit each question alone against the new grid until the tool accepts it. This gives a pool of pieces known to be valid.
- **(d) Join pool pieces.** Use change 1's operations. The only new failures come from the join's own arithmetic: a `-` going negative or a `/` not being exact.
- **(e) Repair instead of discarding.** When the tool says `?`, find the smallest piece whose replacement by `1` fixes the draft, and redraw only that piece (up to 5 tries).

**Fix before running (day-1 census):**
- composed drafts survive at least 1 in 5 (now about 1 in 10,000);
- joined rows are at least 25% of the night's rows;
- at least 3 grid heights appear, and 2-digit values appear.

**Run:** domain mode, 2 seeds, rank-64 add-on. Rank alone can't explain an F4 jump: L8's data at rank 64 gave 4.3 **[shown]**.

**Pass:**
- F4 ≥ 25 on both seeds;
- near ≥ 40;
- old skills unchanged with the add-on off.

**Proved wrong if:**
- The census passes but F4 ≤ 8. The loop then dilutes the joined rows: check rows actually trained, the replay share, and the stop rule.
- The census fails. Keeping joins valid then needs knowledge the tool can't give, so go to the splitting tool.

### Change 3: the model chooses its practice

**How it works:**
- Each night, sample candidates and group them by shape: number of calls, depth, top symbol, grid rows, range length, column.
- The model tries them without training.
- The next night's quota goes to groups where its success is between 10% and 70%. Mastered and hopeless groups get little.
- This counters domination by one form, like L2's `=A1+PRODUCT` **[shown]**, and walks the model toward far.

**Pass:** at equal total rows, far-with-joins ≥ 8 on both seeds (now 0–2), and F4 no more than 5 points below change 2.

**Proved wrong if:** far ≤ 3. First suspect: operands past slot 16. Check whether far items' needed numbers fall beyond the first 16 digit runs.

---

## 4. Bigger model or splitting tool?

**I'd measure the splitting tool first, because it is free to estimate.**

**The single test: a join-gap audit**, evaluation only, on the current domain-mode and L8 checkpoints. For each F4 item and each far item with joins, record:
- **W:** the model gets the whole formula right.
- **P:** the model gets both pieces right when each is asked alone on the same grid.
- **T:** P is true *and* the model gets the recombination right (for example `=151+92`, built from its own piece answers). T is exactly what the splitter would score.

**How to read it:**
- **T − W ≥ 15 and T ≥ 25.** Joining is the bottleneck. The splitter fixes it now, and a bigger model isn't needed for joins.
- **T small because P is small.** The pieces are the bottleneck. Neither the splitter nor join practice will help. That is where a 10M test belongs, run on single far factors.

**Predictions [suggested]:**
- F4: T ≈ 15–30, from pieces at near-level 40–57%, against W = 1.4.
- Far: T ≲ 10, since single far factors sit at 19–32%.

So the splitter likely helps joins but not far.

**Caveats on the splitter:**
- It changes your claim: the model learns the pieces, and code does the joining.
- If the spreadsheet tool is unavailable at deployment, the splitter must be purely syntactic (bracket matching plus the top-level operator).

**If you do test 10M:** use the L5 protocol at rank 64. Count scale as helping only if the unseen layout reaches at least 30 (against 13.6); count it as not helping if it scores 18 or less.

---

## Missing facts, and how each would change the answer

1. **D1 results (failure anatomy).** These decide between explanations #3, #4 and #6.
2. **Whether the add-on adapts the reader or embeddings.** If it doesn't, #3 strengthens, and adding it there becomes a cheap knob.
3. **What the "place" code encodes.** If it encodes bracket depth, #3 weakens.
4. **F4 split by layout and pair type for every test, and whether L5 also held out pairs.** This confirms or kills my estimate of about 55 for L5's practised half.
5. **Whether L9 varies grids and references, and which symbols were accepted.** If references stay `A1:A3`, a failed L9 says nothing about joins.
6. **What the 6,000 single-kind rows were in L2, L4, L8 and L9.**
7. **Whether L8 filled sibling or compound holes.** If it did, my explanation of its 0.0% is wrong.
8. **Digit-run counts in far items.** These show whether the 16-slot limit is a ceiling for far.
9. **Which tools are available at deployment,** and **the 10M model's runtime and architecture.**

---

## Plain-language summary (142 words)

Your model can combine things, a bit: after practising five ways of joining two formulas, it got a new sixth way right about a third of the time. What it can't do is invent a kind of join it never practised. Your self-practice never made the test's kind (two whole formulas side by side), so it scored near zero. That is mostly a practice-maker problem, which is cheaper to fix than model size. L9 checks whether that join, once supplied, is learnable. But its join patterns were picked knowing the test, so it doesn't prove the loop invents them. Next: generate joins with a general "cut a piece out, plug a piece in" rule. Change the grid before joining so drafts stay valid. And measure for free how much a formula-splitting tool would help before spending hours on a bigger model.
