# PASSMARKS — Experiment 137 (multi-word possessive subjects, Muse)

Sealed 2026-09-22 BEFORE the registered run. Registered FAIL is recorded as
FAIL, never re-run into a pass. Base loop: loop129b
(scripts/fable_loop129b_agent.py, config
artifacts/fable-fix129-20260922/loop129b-config.json).

## Sealed file hashes (sha256, taken before any run)

- 940f48d784d9c5333b72315f536b7f659ea543cb7307de20d49df0ff24dd9cb9  artifacts/fable-fix137-20260922/fable_fix137_n1_cases.json (42 teaches + 42 questions, written before anything ran)
- 18ae968d3fcf7b367a9b36c45d0f6ea70b55ff41894426d6f48e70262ce30956  artifacts/fable-fix137-20260922/fable_fix137_n2_traps.json (18 traps, written before anything ran)
- 1f9765f0c5ad916e36c7b5177a0e1bea7de1a06da786a45d1e69fac6fcdb46f9  artifacts/fable-fix137-20260922/loop137-config.json
- 250cdfc93ede43bb895d50ce7ecaa7aaca2576fe7696f727865e3ed88ed6fb3e  scripts/fable_fix137_names.py (mixin)
- 371b88c7b466d70b2dc077d520fcb3d11a285ba5347538c333599e96f17a920a  scripts/fable_loop137_agent.py (wrapper)
- 3ad6fced4904c0d857a29c8e8aaa23f7740336ca764ada8815a3df17a9057a8f  scripts/fable_fix137_probe.py (N1/N2 runner)
- ca42e727d403147a8b7758bbf4fecd2da2d058920110663c1f5804eea9c695c1  scripts/fable_fix137_bench.py (bench arm)

## Marks

- N1 (fresh probe, 42 teaches with 2-4-token subjects across mother/father/city/boss/friend/employer + 42 matching questions, one fresh daemon): PASS iff >= 38/42 (90%) stored exactly (subject, relation, value) AND >= 38/42 questions answered with the taught value AND 0 wrong writes (wrong subject split, value junk, relation swap). Every seed/case reported, never averaged.
- N2 (18 sealed traps: lowercase phrases, non-name leads, ALL-CAPS, packed facts, double possessive, question-marked teach, missing 's, possessive-in-value, lowercase/digit tokens, empty value, 5-token subject, 7-word value): PASS iff 0 wrong writes. Clarify/refuse replies recorded.
- N3a (marks123): PASS iff every suite verdict identical between loop137 and loop129b (base run into the same artifact dir, verdicts diffed).
- N3b (bench): PASS iff per-item verdicts identical loop137 vs loop129b on all three splits (edit200 / old_s2fresh_4hop / new_121_4hop). Any difference explained.
- N4: PASS iff the whole registered wave (probe + marks123 x2 + bench) runs < 25 min wall-clock on Mac CPU with OMP_NUM_THREADS=1 MKL_NUM_THREADS=1. (If marks123 alone exceeds the box budget, N4 is reported per-phase honestly; N1/N2/N3 verdicts stand on their own bars.)

## Predictions (ledger P137.1-P137.7, appended before the run)

- P137.1 N1 stores >= 38/42 and answers >= 38/42 with 0 wrong writes. p=0.80.
- P137.2 the question side needs no change (FakeEars question branch has no one-word guard). p=0.85.
- P137.3 N2 0 wrong writes on 18/18 traps. p=0.85.
- P137.4 marks123 suite verdicts identical 137 vs 129b. p=0.90.
- P137.5 bench per-item identical on all three splits. p=0.85.
- P137.6 base loop129b stores 0/42 N1 teaches (director claim reproduces). p=0.90.
- P137.7 whole wave < 25 min Mac CPU. p=0.90.

## Reproduce (Mac CPU, offline; only after this seal)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix137_probe.py --run
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix137_bench.py --run
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop137_agent.py --config artifacts/fable-fix137-20260922/loop137-config.json --out artifacts/fable-fix137-20260922/marks123-137 --workers 4
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop129b_agent.py --config artifacts/fable-fix129-20260922/loop129b-config.json --out artifacts/fable-fix137-20260922/marks123-base --workers 4
