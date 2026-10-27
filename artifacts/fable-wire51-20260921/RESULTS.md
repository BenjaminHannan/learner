# Experiment 51 — Wiring the real parts (2026-09-21)

**PASS**, all marks, predictions P224–P227 all TRUE (ledger SCORE PASS 5/5).
Marks were written to `PASSMARKS.md` and sealed (`SEAL.sha256.txt`) before the
registered `--replay 3` run; selftest 27/27 immediately before the wave.

## Marks (integer counts, every run reported, never averaged)

| Mark | need | run 1 | run 2 | run 3 |
|---|---|---|---|---|
| turns | 40 | 40 | 40 | 40 |
| taught_rows | 13 | 13 | 13 | 13 |
| active / superseded | 12 / 1 | 12 / 1 | 12 / 1 | 12 / 1 |
| wrong_writes | 0 | 0 | 0 | 0 |
| missing_writes | 0 | 0 | 0 | 0 |
| unexpected_entities | 0 | 0 | 0 | 0 |
| questions | 15 | 15 | 15 | 15 |
| correct_answers | 12 | 12 | 12 | 12 |
| wrong_answers | 0 | 0 | 0 | 0 |
| abstentions / missed | 3 / 0 | 3 / 0 | 3 / 0 | 3 / 0 |
| two_hop_correct | 6 | 6 | 6 | 6 |
| traps no-write | 5 | 5 | 5 | 5 |
| smalltalk no-write | 5 | 5 | 5 | 5 |
| sleeps | 2 | 2 | 2 | 2 |
| reasoner_backend | fable_reasoner50 | ✓ | ✓ | ✓ |
| ears english* | 40 | 40 | 40 | 40 |
| bridge_failures | 0 | 0 | 0 | 0 |
| router_runs (44 x-check) | 0* | 0 | 0 | 0 |
| word_lookups | 0* | 0 | 0 | 0 |
| sleep audit violations | 0 of 6 | 0 | 0 | 0 |
| recipe attempted | False | False | False | False |

\* Expected under the documented deviations below — not failures.

Every sleep (2 per run × 3 runs): `accepted=true`, `audit.violations=[]`,
`recipe.attempted=false, queued=0` ("0 word episodes (< 8); kept queued").

## What this means

- The glue loop's four slots (ears / reasoner / sleeper / thinker) plus the
  mouth are all **real** code: English ears → frame → listening write, or
  reasoner50 answer → template mouth, with a hash-chained `decisions.jsonl`
  and kill-safe resume. Ben can run one process and talk to it.
- Correctness under adversarial content: 5 hearsay traps and 5 small-talk
  turns wrote nothing; the ambiguous teach held pending until `pick`; all 3
  unanswerable questions abstained (unknown entity, broken chain, rejected
  parse); 6/6 two-hop answers correct in every run.
- Sleep is wired the registered way: fires only at the fixed log threshold
  (20), runs the deterministic audit (0 violations across all 6 sleep calls),
  and invokes the Exp-46 recipe only when ≥8 word episodes are queued — here
  0 were, so it correctly did nothing.

## What this does NOT mean

- **Not a learned-language demo end-to-end.** The Qwen bridge is a placeholder
  (Ben's ruling): ears used it for parsing only. No personal facts were
  searched or trained on.
- **No sleep install happened** (word_lookups=0): the English parser rejects
  "Kai's maternal grandmother" as a surface/path mismatch *before* the
  reasoner sees it, so no word episode was ever queued. The Exp-46 recipe
  path is wired and gated but unexercised in this script — agent 5
  (`fable_livesleep52`) owns mining real episodes.
- **Router cross-check runs=0**: with reasoner50 preferred (the brief's
  instruction when agent 3's module appears), the Exp-44 neural router is
  never loaded, so there is nothing to cross-check. The 44-wrap fallback is
  verified separately in selftest (`prefer50=False` still answers).

## Deviations from plan

1. **13 taught rows, not 15.** 12 teaching statements + the post-pick fact
   = 13; the correction supersedes one (12 active). The CREATE and AMBIG
   turns deliberately write no fact until pick. Composition check enforces 13.
2. **Echo-confirmation off by default** (`echo_confirm=False`, `--echo` to
   enable): with echo on, scripted writes double-prompted and broke scoring.
3. **word_lookups=0 / maternal-grandmother abstention via ears**, not via
   reasoner MISSING_FACT: English validator rejects the surface form
   ("relation path/surface lengths differ"); accepted abstention phrase
   matches the run output.
4. **router_runs=0** as above (reasoner50 preference).
5. **sleeps=2** (threshold 20): once after turn 20 (before questions block
   completes log) and once after turn 40.

## Predictions (ledger P224–P227, written before the wave)

P224 TRUE (3/3 exact marks). P225 TRUE (backend reasoner50 3/3; 44-fallback
selftest green). P226 TRUE (english 40, bridge_failures 0). P227 TRUE
(2/2 sleeps clean, recipe not attempted). **4/4 TRUE.**

## Reproduce (exact command)

```bash
uv run --offline --no-project --python 3.12 --with torch --with numpy \
  python -B scripts/fable_wire51_run.py --selftest
uv run --offline --no-project --python 3.12 --with torch --with numpy \
  python -B scripts/fable_wire51_run.py --replay 3 --ears auto \
  --report artifacts/fable-wire51-20260921/replay-report.json
# interactive:
uv run --offline --no-project --python 3.12 --with torch --with numpy \
  python -B scripts/fable_wire51_run.py \
  --state-dir artifacts/fable-wire51-20260921/agent
```

Requires the Qwen bridge at `http://127.0.0.1:18081` for ears `--ears auto`
(or pass `--ears fake` offline; selftest is fully offline).

## Artifacts

- `scripts/fable_wire51_adapters.py` — slot adapters (EnglishEars,
  NotebookReasoner, HardGate46Sleeper, TemplateMouth, NotebookThinker).
- `scripts/fable_wire51_run.py` — Runner, DecisionLog, score_turn, replay,
  REPL, `--selftest`, `--replay N`, `--once`, `--turns`.
- `scripts/fable_wire51_script40.py` — 40-turn script + composition check.
- `PASSMARKS.md`, `SEAL.sha256.txt`, `replay-report.json`, `smoke-report.json`,
  `runs/cold-{1,2,3}/decisions.jsonl` (hash-chained event logs).
