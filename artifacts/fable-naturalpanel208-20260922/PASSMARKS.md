# Exp 208 — FRESH NATURAL-ENGLISH PANEL (baseline, no agent change)

Goal: one number that tracks what Ben actually experiences when he chats
with the assistant. Baseline on loop138i
(`scripts/fable_loop138i_agent.py` + `artifacts/fable-agent138i-20260922/loop138i-config.json`).

## Sealed files (do not edit after seal)

- `panel208.json` — 100 turns in 20 dialogs (D01–D20 × 5), fictional names only.
  Expected behaviour per turn: SAVE / ANSWER / ABSTAIN / ASK / CHAT, plus the
  expected fact or answer substring and what counts as a bad write.
- `rubric208.md` — classes OK / wrong / unhelpful / bad write; G1 vs G2 rules.

## N1 — panel + rubric sealed before any run

PASS iff `SEAL.sha256.txt` verifies (`shasum -a 256 -c SEAL.sha256.txt`)
and the seal timestamp predates the first registered run log.

## N2 — counts per class, overall and per category

- Overall counts of OK / wrong / unhelpful / bad write (G2 rules).
- Per-category counts for: teach, ask, correction, small talk, self,
  out-of-scope, typo.
- Every turn graded twice: G1 automatic (stored facts vs expected, answer
  substring) and G2 own reading; G1/G2 agreement reported.
- Every turn reported (run log keeps all 100 replies); never averaged away.

## N3 — the 10 most common failure shapes, one example each

Failure shape = short pattern label (e.g. "stale value wins after
correction", "typo teach dropped", "untaught guess instead of abstain",
"chat stored as fact", "pronoun attached to wrong person", "abstain after
teach", "two-fact message half stored", "out-of-scope stored", "echo reply",
"wrong relation slot"). List top 10 by count with one example turn id each.

## Verdict

Baseline: no accuracy bar. Verdict VALID iff N1 + N2 + N3 hold.
Any post-seal edit to panel, rubric, agent code or config makes the
registered verdict FAIL.

## Reproduce

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_naturalpanel208_driver.py --agent scripts/fable_loop138i_agent.py --config artifacts/fable-agent138i-20260922/loop138i-config.json --panel artifacts/fable-naturalpanel208-20260922/panel208.json --out artifacts/fable-naturalpanel208-20260922/run138i.jsonl
