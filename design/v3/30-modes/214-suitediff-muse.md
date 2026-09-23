# 214 — Shared suite-diff tool (Muse): one harness, no more copies

## Problem
Every merge/piece copied 200-550 lines into its own `fable_fix<N>_suites.py`
+ `fable_fix<N>_marksdiff.py` (40+ copies) to rerun frozen suites and compare
per case against a sealed base. The copies drifted, cost agent time, and
caused grading slips.

## Design (`scripts/fable_suitediff.py`, new file, harness only)
- **Generic agent load** (import, never edit): `DEFAULT_CONFIG*` as config
base, `build_agent*` (kept for parity), `*Daemon` (Loop-preferred) for all
mailbox runs. Per case: fresh temp `state_dir`, `sleep_threshold = 100000`,
`idle_seconds = 3600.0` — exactly as the existing drivers do.
- **Same judges, read-only**: rt136 via `fable_fix139b_redteam136.run_case139b`
(runtime-patched daemon factory), rt143 via `fable_redteam143_run.run_case`
(runtime-patched `Loop132Daemon`/`DEFAULT_CONFIG132`), sessions152 via
`fable_session152_run.run_session` + `judge`, bench via
`fable_bench121_run.run_item` (scorer v2) or `fable_fix172b_benchv3.run_item_v3`.
Only module attributes are patched at runtime; no suite/judge file is edited.
- **Bench protocol auto-detect**: per split, if the sealed base rows carry a
"confirms" key the v3 driver reruns them, else v2. This is what makes one
tool reproduce both the 138h (v2-sealed) and 138i (v3-sealed) bench bases.
- **Base discovery**: `--base 138h|138i` maps to the sealed artifact dir;
rows files are found by filename search (flat and g1bench/g2frozen layouts)
and parsed as JSON-array or JSONL.
- **Diff classes per moved case**: new WRONG, new WRONG-WRITE, new junk
write (stored/writes appear where base had none), or reply-only move
(verdict/writes equal, text differs). Exit code 1 iff any new wrong/junk.
- **marks123**: stock CLI `fable_marks123_all.py` as a subprocess with
`--suites p4,q1,bench,rt81` (in-process suites only), diffed per case id
against the sealed marks reports + bench rows. rt110/p2/p3/soak/sleep are
excluded for time and documented in the output.
- **Output per suite** in `--out`: rows file (replies + stored triples) +
diff JSON listing every moved case + one summary line; `SUITEDIFF-SUMMARY.json`
collects the lines.

## The one-line usage future pieces will copy
```
python -B scripts/fable_suitediff.py --agent <scripts/fable_loopXXX_agent.py> --config <config json> --base <138h|138i> --out <dir> [--only rt136|rt143|sessions152|bench|marks123|all]
```

## Verification (registered, sealed first)
V1 loop138i-vs-138i: 0 moves on all suites (145+124+180 turns+800 bench+
marks subset). V2 loop138h-vs-138h: 0 moves. V3 scratch wrapper
(`wrap214_boss.py`, appends " (test)" to boss-turn replies): exactly the 13
pre-predicted rt136 ids, all reply-only, 0 elsewhere. V4: four suites ~34 s
(138i) / ~51 s (138h), far under 900 s. Verdict PASS.

## Limits
The tool checks reproduction against a base, not correctness; a shared base
error would reproduce silently. One rare pre-seal bench flake (1/5 pilots)
suggests mild nondeterminism in one s2fresh item — worth a future look, but
out of scope for a harness-only change.
