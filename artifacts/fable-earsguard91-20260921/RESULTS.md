# Exp 91 RESULTS — FakeEars guard (Muse, 2026-09-22)

## Result

PASS on all four sealed marks. A thin wrapper, `GuardedEars`, sits between
the user and FakeEars and turns the two silent wrong writes from red-team-81
into plain clarifications. No existing file was edited; the fix is additive
only (`scripts/fable_earsguard91*.py`).

## What was wrong

FakeEars (test scaffolding inside `scripts/fable_agent_loop.py`, also used by
the persistent daemon) silently wrote bad rows: `"Mira's city is Lisbon?"`
was saved with value `"Lisbon?"`, and `"Mira's city is Lisbon and Mira's pet
is a cat."` was saved as one literal `"Lisbon and Mira's pet is a cat"` while
the pet fact vanished. A person talking to the daemon tonight could hit both.

## The fix

`GuardedEars(inner)` implements the Ears protocol. It calls the inner ears,
then screens each teach/correct write: a value containing `?` becomes
"Was that a question?"; a value packing a second fact (another `X's <word>
is`, a second is/are, ` and <Name>'s`, or `;`) or longer than 6 words becomes
"I can take one fact at a time — could you split that?". Everything else
passes through byte-for-byte unchanged.

## Marks (integer counts)

| id | bar | got |
|----|-----|-----|
| G1 reproducers clarify, 0 writes | 2/2 | 2/2, writes 0 — PASS |
| G2 74 red-team cases re-run; changed listed; none a wrong write | list + 0 | changed 5/74, wrong writes 0 — PASS |
| G3 60 acceptance turns | 60/60, 0 wrong | 60/60, 0 wrong — PASS |
| G4 daemon74 selftest with guard | exit 0, seeds 1–3 | exit 0, D1–D4 PASS ×3 — PASS |

G2 changed cases (exactly as predicted): D_q_vs_s-01 (now asks "Was that a
question?"), E_double-01 (now asks to split), plus their honest follow-ons
D_q_vs_s-02, E_double-02, E_double-03, which now say "I don't know anyone
called Mira" because nothing was (wrongly) written at step 1. No case gained
a write; the 6000-char literal still saves, single-word values all pass.

G4 per seed: D1 50/50 correct 0 wrong; D2 200/200 0 wrong 0 dupes chain clean;
D3 100 turns in 0.28–0.32 s; D4 STOP in 0.05–0.06 s exit 0 — seeds 1, 2, 3.

## What it means

Nobody talking to the daemon tonight can silently store a "Lisbon?" value or
a packed conjunction literal; both now get a plain question back, and every
normal one-fact sentence works exactly as before.

## What it does not mean

This is a bandage on scaffolding, not real ears: it cannot split "tell me
both facts" into two saves (it asks the user to split instead), and genuine
multi-word values over 6 words will also be asked to split. The real ears
agent still owns proper parsing.

## Deviations

None. One registered run, no re-runs.

## Reproduce

    export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
    uv run --offline --no-project --python 3.12 --with torch --with numpy \
        python -B scripts/fable_earsguard91_run.py --out artifacts/fable-earsguard91-20260921

## Launch the daemon with the guard

    export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
    uv run --offline --no-project --python 3.12 --with torch --with numpy \
        python -B scripts/fable_earsguard91_daemon.py --dir DIR

Design: `design/v3/30-modes/91-fakeears-guard-muse.md`. Predictions P91.1–P91.4
all TRUE (Brier 0.0025, 0.04, 0.0225, 0.01).
