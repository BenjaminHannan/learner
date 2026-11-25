# PROBLEM-7 World Model — Ranked Ideas & Next Steps (For Ben)

**Date:** 2026-11-24  
**Status:** Proposals ONLY. **No** code edited, **no** training or tests started. Waiting for Ben's call.  
**Scale note (`shown`):** Everything below is for the small ~2.5M-active laptop practice brain (`P7toy`) on the 2D Minecraft-like game (Crafter, 16×16 pictures), to prove the mechanism cheaply before touching the ~50M or ~500M brain. All model parts below are **100% learned** (zero hand-written rules, zero game-cheat shortcuts, world model trained strictly on real game transitions).

---

## Plain-English Quick Recap (Before the Ideas)

Think of the model's "world model" like a **game crystal ball**: you show it the screen, tell it which button you press ("walk left"), and ask it to draw what the screen will look like **1 step ahead**, **3 steps ahead**, and **5 steps ahead**.

We grade it on three simple checks in **16 brand-new unseen worlds**:
1. **Beat the lazy guess:** A lazy guesser just says *"nothing changes"* (or fades slightly toward the average picture). We divide the crystal ball's picture error by the lazy guesser's error — lower is better:
   - **1 step ahead:** must be **0.80 or lower** (at least 20% better than the lazy guess).
   - **3 steps ahead:** must be **0.90 or lower**.
   - **5 steps ahead:** must be **0.95 or lower**.
2. **Prove it actually cares which button was pressed ("button scramble"):** We keep the exact same starting screens, mix up which button presses go where inside each world, and re-run the crystal ball. If it truly uses the button, lying about the button must make its error **at least 1.25× worse at 1 step** and **at least 1.10× worse at 5 steps**, in **at least 12 of 16 unseen worlds**.
3. **No blurry cheating ("anti-collapse"):** Its predicted changes can't be way too tiny, way too noisy (must stay within **0.25× to 2×** of how much the real screen changes per button), or repeat the same couple of shapes over and over (must have at least half the real variety of patterns).

### What Our Audit Just Uncovered (Why the Last 4 Tries Failed)
- **The game data is NOT the problem (`shown`):** A super dumb 1-line math formula (one separate linear formula per button on raw pixels) ALREADY gets **0.50 at 1 step**, **0.58 at 3 steps**, and **0.63 at 5 steps** — smashing all three marks! Walking buttons make up 71% of the game and shift the whole screen clearly.
- **The exact same "buried whisper" bug from today's Problem-1 breakthrough is choking the world model (`shown`):** Earlier today, the two-fact memory test jumped from ~7% to **99%** after finding that giant starting offsets drowned out the real signal by 100×–1,000×. Here, the brain's notepad has the **exact same bug** (a giant fixed background number `1.36` drowning out a tiny `0.02` picture signal — **68 times quieter!**), AND the button press gets drowned out the exact same way!
- **Why Try #6 specifically failed (`shown`):** Try #6 froze the main brain so imagining wouldn't wreck seeing, and tacked on a small new guessing layer. That new layer actually *did* start noticing the button in **all 16 out of 16 unseen worlds** (a tiny +4% to +9% effect!), **but it was handcuffed in two ways:** (1) it was only allowed to look at **one notepad row at a time** — it literally couldn't move a tree from the right side of the screen to the left side when you press "walk left"! And (2) the frozen main brain had only ever practiced *remembering* static screens, never *shifting* them when a button is pressed!
- **Bonus catch — our grading ruler has a hidden math trap (`shown`):** Because Try #6 draws a *whole* picture from scratch using a slightly fuzzy math reader (`0.042` blur), even a **100% perfect crystal ball** would look 5× too noisy on "do nothing" steps (`0.042` blur vs `0.008` real change) and automatically **FAIL** the 2× spread rule! And the practice data stopped before nighttime (`125` steps) while the test ran into the dark (`250` steps).

### Which Past Ideas Are Closed Under the "3 Clean Misses" Rule
- **CLOSED (4 misses):** Training the raw unmodified brain + simple change-drawing hand from scratch (Step 1: 3 tiny misses + 1 normal-size miss).
- **CLOSED (3 misses):** Training an **unfrozen** buried brain against a **frozen** high-gain math reader (Steps 3, 4, and 5 — it's a Catch-22: any tiny brain tweak breaks the math reader and wrecks seeing).
- **1 of 3 misses (pause until the free X-ray!):** Freezing the main brain and adding separate imagination layers (Step 6 = 1st miss).
- **0 of 3 misses (NEVER TRIED YET):**
  1. **Un-choking the shared brain** (the Problem-1 signal-path fix + announcing the button to every row + clean joint training).
  2. **A separate small visual crystal ball** (DreamerV3-style escape hatch, kept in reserve).

---

## Ranked Ideas (Cheapest & Highest-Leverage First)

---

### Rank 1 — 2-Minute Free "X-Ray" on Saved Weights *(Do This First — Zero Training!)*

- **What changes:** Nothing trained, no weights edited. Run one short read-only diagnostic script on the **already-saved** Step-2 memory brain and Step-6 imagination brain using the existing Crafter recordings. (Expands the lead's planned check into 4 exact measurements.)
  1. **Button hearing check:** Does the frozen brain's internal state even wiggle when we change the button press (compared to how much it wiggles across different screens)?
  2. **Notepad capacity check:** Fit a fast closed-form math formula (10 seconds, per button) straight from the saved Step-2 notepad to the next screen *and* to the next notepad, and also from the frozen trunk's hidden state (comparing shared vs. per-button vs. one-row-at-a-time formulas).
  3. **Ruler trap check:** Measure a *perfect-memory oracle* (real next notepad fed into Step 6's reader) on the per-button spread rule, comparing whole-picture decoding vs. change-only decoding (`current screen + reader(next) - reader(now)`), and split daytime (`t < 125`) vs. unseen nighttime (`t >= 125`).
  4. **Door & noise check:** Print how wide the frozen slow-memory door opens during imagining vs. reading, and compare the `0.2` training smudge against real 1-step movement.
- **Why it helps (ELI5):** Before building a new engine, open the hood and check if gas is even reaching the cylinders. In 2 minutes for free, this tells us **which** single fix to run next (Rank 3 vs. Rank 4) with zero guesswork.
- **Cheapest test:** ~2 minutes on M3 CPU (no MPS lock needed, no training).
- **Fixed decision marks (set in advance):**
  - If the **per-button math formula on the saved Step-2 notepad** gets **1-step error <= 0.70** of the lazy guess, while the **one-row-at-a-time frozen-trunk formula stays > 0.90** → proves the notepad *already holds the world*, and Step 6 only failed because the frozen trunk + row-blind head couldn't mix buttons across rows.
  - If **even the per-button formula on the Step-2 notepad misses (> 0.85)** (even though raw pixels get `0.504`) → proves the Step-2 notepad lost dynamic details, so **skip Rank 4** and go straight to **Rank 3** (un-choke and retrain the shared brain).
  - If the **perfect oracle fails the 2× spread rule on "do nothing"** under whole-picture decoding while passing under change-only decoding → confirms Rank 2's ruler fix is mandatory before any scored run.
- **What would prove our diagnosis wrong:** If the frozen trunk's hidden state *already* reacts strongly to the button AND a single shared linear readout on it already scores `<= 0.80` — that would mean the frozen trunk wasn't the bottleneck at all, and Step 6 only stalled from training noise / optimizer settings.
- **Honest odds:** **95%** chance of giving a crisp, decisive fork in 2 minutes.

---

### Rank 2 — Fix the 3 Broken Yardsticks *(5-Minute Hygiene Prerequisite Before Any New Scored Run)*

- **What changes (grading & recording fairness only — zero change to model rules):**
  1. **Fix the whole-picture blur trap in scoring:** When using a frozen reader, score predicted change as `reader(imagined_next) - reader(current)` (so `imagined_frame = current_frame + reader(imagined_next) - reader(current)` — still 100% decoded through the frozen reader from only the starting frame!), and evaluate the `0.25–2×` spread check weighted by button frequency (or on buttons that actually move the screen) so predicting "nothing happens on do-nothing" isn't punished for random mob jitter.
  2. **Match daytime & nighttime in the data:** Re-record training worlds with `250`-step episodes (matching the `250`-step test worlds, still 100% separate world seeds `0–159` vs `1000–1015`), and report scores on *both* the new split and the original held-out split so we never move goalposts silently.
  3. **Fix minor scorer bugs:** Enforce `proves_wrong`, fix the `PARTIAL` condition, key worlds by ID, shuffle individual steps instead of chunks, and save `imagine_scale` properly.
- **Why it helps (ELI5):** Right now our ruler is bent — a **100% perfect crystal ball** would fail the spread check on "do nothing", a **completely dead** crystal ball (Step 5) passed the pattern-variety check by accident, and the test happens in the dark when practice was only in the daytime. Straightening the ruler takes 5 minutes and stops false fails and false passes.
- **Cheapest test:** ~3 minutes on CPU (re-score saved Step 5 & Step 6 checkpoints + record matched train split).
- **Fixed pass marks (sanity check):** On saved Step 5 (which outputs literally zero change), fake pattern variety drops from `107` to `1` and `copy_ness` drops from `0.605` to `0.000`; a perfect-memory oracle scores `std_ratio ≈ 1.0` and `<= 0.15` 1-step error.
- **What would prove this wrong:** If nighttime turns out to add `< 3%` error on held-out — harmless, still clean to know.
- **Honest odds:** **99%** chance of fixing the ruler (and **0%** chance of making Step 6 pass on its own — this is strictly prep for Rank 3 / Rank 4).

---

### Rank 3 — Un-Choke the Shared Brain (Port Problem-1's 99% Fix + Announce the Button to Every Row + Clean Joint Training) *(Best Shot at Keeping One Shared Brain!)*

- **What changes (in a P7 experimental copy — canonical core untouched!):**
  - Instead of patching a frozen buried brain behind a fragile math reader, fix the **exact same signal-burial bug** that unlocked Problem 1 today (7% → 99%) and train seeing + imagining cleanly together:
    1. **Quiet the giant starting offsets** (`src_emb`, `age_lin`, `row_type_emb`, `row_pos_emb` small at `0.02`, `init_rows` at `0.05`, `out_proj` at `0.1`) so the actual game screen is loud and clear on the notepad instead of a 1% whisper.
    2. **Announce the button over the intercom to all 64 rows:** Give every notepad row a learned scale-and-shift (`FiLM`) from the button embedding at the start of imagining, instead of whispering the button from 1 tiny row out of 66. Now all 64 rows *and* all 16 specialist MoE experts immediately know which button was pressed!
    3. **Keep imagination updates safe and bounded:** Match normal thinking's `focus`, put a `0.15` floor on the slow-memory door (Problem-1's fix so memory never slams shut), and bound updates so 5-step dreams can't explode.
    4. **Escape the frozen-ridge Catch-22:** Train seeing (redraw current screen) and imagining (draw real next screen, 1 step ahead only) **jointly** using one clean learned pixel reader with **per-row LayerNorm + linear skip** (no BatchNorm collapse, no frozen `1/sd` explosion!), detaching the starting notepad on the imagination loss so imagining can never wreck seeing.
  - *(Strict one-knob discipline: we can test (1)+(2)+(4) first with `noise=0`, and only add a tiny start-smudge or discrete snapping later if 1-step passes and 3/5-step drifts!)*
- **Why it helps (ELI5):** Remember why Problem 1 suddenly went from 7% to 99% today? The brain wasn't dumb — its ears were plugged with giant static noise, its memory door slammed shut, and its drawing hand couldn't hear a whisper. Right now the world model has the **exact same ear plugs**, PLUS we were whispering the button press from the back of a 66-person room while forbidding the main brain from learning how buttons move the world! Unplugging the ears, putting the button on the room intercom, and letting the brain practice seeing and imagining together with a steady drawing hand fixes all four clogs at once.
- **Cheapest test:** ~15–20 minutes on M3 MPS (`P7toy`, 2.5M active params, 3,000 steps, strictly 1-step real transitions, seed 42).
- **Fixed pass marks (held-out unseen worlds, with Rank 2's clean ruler):**
  - Real-screen memory: `<= 0.70` (target `<= 0.25`) of lazy baseline.
  - Prediction error vs. lazy baseline: **1 step `<= 0.80`**, **3 steps `<= 0.90`**, **5 steps `<= 0.95`**.
  - Button-scramble: **>= 1.25× worse at 1 step** and **>= 1.10× worse at 5 steps** in **>= 12 of 16 unseen worlds**.
  - Anti-collapse: spread `0.25–2×` of real change (cleanly measured on predicted change) and pattern variety `>= half` of real.
  - Stretch check (reported): beat the 1-line linear-per-button formula (`0.504 / 0.580 / 0.631`) to prove it learns walls, trees, and collisions, not just rigid screen shifts.
- **Result that proves it wrong:** **1-step error stays `>= 0.85` OR 1-step button-scramble stays `< 1.10×`** even with clear un-buried inputs, intercom button broadcast, and clean joint training. That would prove the shared 64-row attention+MoE brain struggles with spatial game physics at this scale (not just a wiring bug), pointing directly to Rank 6.
- **Honest odds:** **PASS (all of 1, 3, and 5 steps): 35% | PARTIAL (1 step passes cleanly, 3 or 5 steps drift): 45% | FAIL: 20%.** *(80% chance of breaking out of "nothing changes" and passing at least 1 step!)*

---

### Rank 4 — Upgrade Step 6's Frozen-Brain Head Into a Cross-Row Button-Driven Block *(Only If Rank 1 X-Ray Passes & Ben Wants Zero Risk to Reading)*

- **What changes (1 swap inside `imagine_head6.py` — main reading brain stays 100% frozen, strike 2/3 of the frozen-brain line):**
  - Keep the Step-2 memory brain 100% glued in place.
  - Replace Step 6's **one-row-at-a-time** guessing layer (which ran *after* the frozen trunk and *before* the frozen `0.12` slow-memory door) with **one small learned cross-row block** (1 attention layer across the 64 rows + learned button `FiLM` scale-and-shift, small non-zero output init, bypassing the frozen trunk and frozen door) reading directly from the **volume-leveled** current notepad `(board - mean) / std`, and adding its predicted change back in `std` units.
  - Also turn on the pixel loss from step 0 (remove the useless 100-step delay) and shrink start-noise from `0.2` to `0.05` so noise stops drowning out real moves.
- **Why it helps (ELI5):** Try #6 forced 64 teammates sitting in separate soundproof booths to guess how the picture moves — nobody could pass a tree from booth #5 to booth #4! Giving imagination one small open room where all 64 notepad rows can talk to each other right after hearing the button — *and* turning up the volume on the notepad before they talk — lets it shift the whole screen cleanly without ever touching the frozen seeing brain.
- **Cheapest test:** ~10–12 minutes on M3 MPS (much faster than Step 6 because we don't backprop through the frozen trunk!).
- **Fixed pass marks:** Same pinned marks as Rank 3 (1/3/5-step error `<= 0.80 / 0.90 / 0.95`, button-scramble `>= 1.25×` / `>= 1.10×` in `>= 12/16` worlds, anti-collapse passes, frozen seeing memory unchanged).
- **Result that proves it wrong:** **1-step error stays `>= 0.90` OR 1-step button-scramble `< 1.15×`** even after Rank 1's X-ray showed the Step-2 notepad has the info — proving SGD through the frozen ridge reader is too poorly conditioned (drop frozen-ridge training and move to Rank 3 or Rank 6).
- **Honest trade-off:** Because this bypasses the frozen MoE trunk during imagining, it is halfway to a separate imagination module (it still shares the *notepad format*, just not the MoE trunk weights).
- **Honest odds *(if Rank 1 X-ray passes)*:** **PASS: 30% | PARTIAL (1 step passes, 3–5 drift): 45% | FAIL: 25%.**

---

### Rank 5 — Multi-Step Stability Fix *(Run ONLY If Rank 3 or Rank 4 Scores `PARTIAL`: 1-Step Works, 3–5 Steps Wobble)*

- **What changes (choose ONE if 1 step ahead passes cleanly and 3–5 steps still drift):**
  - **Option 5A (100% strictly 1-step real transitions, no rule change):** Snap the fast visual notepad rows onto a small grid of clean discrete levels (**Lego-brick snapping / FSQ**: smooth squash + rounded clean steps) so tiny step-1 smudges get wiped clean instead of snowballing into blurry mush by step 5.
  - **Option 5B (Requires Ben's explicit yes on the rule wording):** During training, let the model take just **1 extra imagined step** (2 steps total) while still grading **100% against the REAL game screen at step 2** — never against its own made-up pictures.
- **Why it helps (ELI5):** Right now, even a great 1-step crystal ball has never practiced looking at its own slightly smudged step-1 guess to predict step 2 (like making a photocopy of a photocopy). Lego-brick snapping cleans up tiny smudges automatically; 2-step real-screen practice teaches it directly how to recover from a tiny wobble while still grading strictly against reality.
- **Cheapest test:** ~15–20 minutes on M3 MPS on top of the passing 1-step model from Rank 3 or Rank 4.
- **Fixed pass marks:** Keep all 1-step marks passing AND bring **3-step error `<= 0.90`**, **5-step error `<= 0.95`**, and **5-step button-scramble `>= 1.10×` in `>= 12/16` unseen worlds**.
- **Result that proves it wrong:** 5-step error stays `> 1.0` or 5-step button-scramble `< 1.05×` even with snapping / 2-step real-screen practice → proves the 64-row whiteboard itself is too unstable for open-loop video dreams, triggering Rank 6.
- **Honest odds *(given a passing 1-step model)*:**
  - Option 5A (Lego-brick snapping): **PASS: 35% | PARTIAL: 45% | FAIL: 20%.**
  - Option 5B (2-step real-screen practice, if Ben approves): **PASS: 65% | PARTIAL: 25% | FAIL: 10%.**

---

### Rank 6 — Separate Compact Visual Crystal Ball *(Honest Escape Hatch & Benchmark Control, DreamerV3-Style)*

- **What changes:** Instead of forcing the 64-row word/reasoning whiteboard to double as a 2D pixel-grid video simulator, build one small (~2M-parameter) dedicated learned visual world model (tiny image encoder → small discrete state updated by button presses → tiny image decoder, trained strictly on the exact same 20,000 real Crafter transitions). The main thinking brain reads its visual state as a sense (just like it already reads borrowed eyes and ears!), and the policy practices inside its frozen dreams.
- **Why it helps (ELI5):** Human brains don't use the exact same brain area to do algebra and to imagine a bouncing ball — we have a specialized visual-imagination part that talks to our thinking part. A tiny 2D grid network naturally understands "shift the whole picture left when I press left" and uses discrete building blocks so 5-step dreams stay crisp (the exact design that already solved Crafter in published DreamerV3 research, `[from memory, unchecked]`).
- **Rule note:** Per the owner rules, keep the shared brain unless evidence shows it can't do the job while a matched-size separate world model passes on the same data. So run this **either** right after the clean un-choked shared brain (Rank 3/4/5) misses, **or** sooner only if Ben explicitly wants a side-by-side benchmark control now.
- **Cheapest test:** ~20 minutes on M3 MPS on the exact same `train.npz` / `heldout.npz` split and exact same marks.
- **Fixed pass marks:** Pass ALL marks (1/3/5-step error `<= 0.80 / 0.90 / 0.95`, button-scramble `>= 1.25×` & `>= 1.10×` in `>= 12/16` worlds, anti-collapse) **AND** beat the 1-line linear-per-button baseline (`< 1.0×` of `0.504 / 0.580 / 0.631` on moved steps, proving real obstacle/interaction physics).
- **Result that proves it wrong:** Even a small spatial world model misses `<= 0.80` or `1.25×` scramble on this dataset → proves the `16×16` blurry frames themselves (not the model design) are the wall.
- **Honest odds:** **PASS: 70% | PARTIAL: 20% | FAIL: 10%.**

---

### Rank 7 *(Later Upgrade Only — After 16×16 Passes)* — Sharper `64×64` Frames (`8×8` Patches) + "Which Button Was Pressed?" Helper Quiz

- **What changes:** Switch from blurry `16×16` pooled frames to crisp native `64×64` frames split into `8×8` = **64 patches** (exact 1-to-1 match with the 64 board rows!), and optionally add a small "guess which real button caused this real screen change" helper loss.
- **Why wait:** Our audit proved `16×16` ALREADY lets a dumb linear model score `0.504 / 0.580 / 0.631`, so blurry pictures are **not** what's blocking us today. Upgrading resolution *after* the model works on `16×16` avoids changing two things at once, and directly prepares for Minecraft/Bedwars (where facing direction, hotbar icons, and bridge edges matter — and the button-guesser doubles as the YouTube-video learner in `MODEL-IDEAS-AND-DESIGN.md` #24!).
- **Honest odds *(once 16×16 passes)*:** **60%** chance of improving non-move action predictions (`do`, `place`, crafting) without hurting move predictions.

---

## Recommended Path (Waiting for Ben's Decision)

1. **First (2 min, zero training):** Run **Rank 1 (the 4-question X-ray)** so we know for sure whether the saved Step-2 notepad holds the dynamics and confirm the ruler bug in numbers.
2. **Second (5 min, zero model change):** Apply **Rank 2 (straighten the ruler + matched 250-step train split)** so no working model gets falsely failed on `noop` spread or unseen nighttime.
3. **Third (one clean ~15–20 min run, Ben's choice of fork):**
   - **Recommended:** **Rank 3** (un-choke the shared brain using today's Problem-1 99% recipe + intercom button broadcast + clean joint reader) — highest honest shot (**80%** to pass at least 1 step, **35%** full 5-step pass) at keeping the **true single shared brain**.
   - **Alternative A (if X-ray passes & you want reading 100% frozen):** **Rank 4** (cross-row button-driven imagination block on the standardized frozen notepad).
   - **Alternative B (if 4 shared-trunk misses are enough and you want the fastest path to Minecraft dreaming):** Authorize **Rank 6** (separate ~2M visual crystal ball feeding the shared brain — **70%** full pass odds).
4. **Fourth (only if Step 3 gets `PARTIAL`):** Apply **Rank 5** (Lego-brick snapping, or ask Ben about 2-step real-screen practice).
