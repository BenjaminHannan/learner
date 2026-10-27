# 55 — Demo addendum: what Ben says aloud for Q10 and Q11

Run after the modes54 beats (DEMO-SCRIPT.md). One command:

```bash
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy \
  python -B scripts/fable_demo55_advantage.py --out artifacts/fable-demo55-20260921
```

(~40 seconds. The screen prints every line Ben says and Fable's reply, then the two scoreboards.)

## Beat Q10 — "many facts, two hops" (≈2 min of talking)

As the 120 lines scroll: **"Same doorway as before — I'm just talking to it in
English. Forty people; each one gets a mother, a boss, and a city. That's 120 facts.
No tricks, and look at the bottom: zero wrong writes — every line it saved is exactly
the line I said."*

Then the 20 questions scroll (boss-of-mother, mother-of-boss, mother's city):

**"Every one of these needs two hops. Who's the boss of Ada's mother? It has to look
up Ada's mother, then look up *her* boss. Notebook: 20 out of 20."*

Point at the baseline columns:

**"This little transformer — same 100-odd thousand parameters as before — we trained
it on the exact same 120 sentences, same 600 training steps, same budget rule as the
last demo. It scored zero. It can write more 'teach Ada mother -> Bo' lines, but it
can't answer a single question about them. The facts live in a notebook it can look
at; the net tries to keep them in its weights, and at this size it can't."*

If someone pushes (be ready — this is the honest part):

**"Fair question: if we instead drill it on the questions themselves, it can parrot
them — in an earlier run it memorized all 20 and tied us. So it's not 'neural nets
are dumb.' It's: weights alone don't hold 120 facts you can reason over; a notebook
plus a hop loop does. And it cost us nothing — the notebook answered in
milliseconds."*

## Beat Q11 — "learn after training" (≈1 min)

As the 5 new lines print: **"Training is over — the net is frozen, weights locked.
Now five brand-new people: Kip, Lark, Moth, Nyx, Opal. I say five sentences. The
notebook just writes them down."*

Then the 5 questions:

**"Notebook: 5 out of 5. It learned after training, from one sentence each. The
frozen net: zero. Same story text in its prompt, but a frozen net can't learn from a
sentence — there's nowhere to write it. We also gave it *fair time*: we fine-tuned it
for at least as long as the notebook took — the whole notebook beat was about a
millisecond, the net's cheapest step is slower than that — and it still scored zero."*

## Close

**"So: 20 out of 20 against 0 out of 20 on content now, plus 5 out of 5 after
training. Same script, same budget, every seed reported. The one place it beat us
before was the colour question in the first demo — that's still true and still in the
results. Full table's in RESULTS.md."*
