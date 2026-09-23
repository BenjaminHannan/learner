# 54 — Demo script (10 minutes, Mac, $0)

Audience: uncle and dad. One terminal, one screen. No GPU, no network needed for the run.

## Setup (once, before they sit down)

```bash
cd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
```

## Beat 1 — the mode self-test (≈30 s)

```bash
uv run --offline --no-project --python 3.12 python -B scripts/fable_modes54_scheduler.py --selftest
```

**Say:** “This is the brain’s traffic controller. Thirty-four scripted situations. Ours: 34 out of 34. A silly baseline that only ever ‘thinks’: fails 30 of them. You can see it refuse to listen, refuse to work, refuse to sleep.”

Point at the last block: S1–S5 all PASS.

## Beat 2 — teach it a family story (≈4 min)

```bash
uv run --offline --no-project --python 3.12 --with torch --with numpy \
  python -B scripts/fable_modes54_demo.py --out artifacts/fable-modes54-20260921
```

The terminal prints every line Ben “says” and Fable’s reply, tagged with the current mode.

**Walk through (script order):**

1. Three people, then mother/city/colour facts → “Saved.”
2. Q1 “Who is Mira’s mother?” → **Ana.** Q2 mother’s city → **Porto.**
3. `correct Mira city = Paris` → Q3 → **Paris.**
4. A quote “Tom lives in Rome” → refused: “I didn’t save that.” Q4 → **I don’t know Tom’s city.** Q5 job → **I don’t know.**
5. Second `person Mira` → “Which one?” → pick E0004. Q6 ambiguous → **asks, doesn’t guess.** Alias Mira1 → **Paris.**
6. Q8 favourite colour → still ambiguous + wrong relation key → misses. “This is where the little neural net can beat it.”

## Beat 3 — the self-question (≈1 min)

After Q9 the full self-report prints: what it knows (by source tag: taught / inferred / proposed / sleep-derived), how it knows (each row’s origin + LISTENING turn), what it’s unsure about, and the mode log (THINKING → LISTENING → CREATIVE → WORK → SLEEP → THINKING).

**Say:** “It can only answer this from its own notebook tags and its own mode log. The neural net scores zero here by construction.”

## Beat 4 — the scoreboard (≈2 min)

Bottom of the same output:

- Notebook **8/9**
- Baseline seeds 5401 / 5402 / 5403: **8/9 each** (104k params, ~3 s train)
- D5 byte-identical story lines: True; D6 all five modes: PASS
- One parked question for Ben: J-stuck ran 11 creative rounds, gave up, asked.

**Say:** “Tie on the eight content questions — it wins Q8, we win the self-report. Nobody swept. Same story text on both sides.”

## Close

Open `artifacts/fable-modes54-20260921/RESULTS.md` if they want the marks table. Leave the parked question up for live Q&A: “What should I do with the stuck job?”
