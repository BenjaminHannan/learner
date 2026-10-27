# Exp 110 pass marks — RED TEAM round 2 of the loop102 agent (sealed before the registered wave)

62 NEW cases (none of the 64 redteam98 cases re-used: different sentences,
names, relations, shapes) in 10 families x6 (pronoun P, disagreeing-teachers
T, re-teach R, forget-re-teach F, never-taught N, long-input L, unicode U,
case-typo M, self-question S) plus daemon-abuse D x8 (empty, 1 MB, binary,
200-file burst, deleted-mid-read, 150 KB whitespace, emoji, NUL byte). Each
case carries its exact sealed expectation (store X / answer X / clarify /
refuse / no write). Every case runs through a REAL loop102 daemon subprocess
via its mailbox; verdicts OK / BUG / HARNESS-ERROR per family; severity per
BUG (critical = wrong fact stored or wrong answer given confidently;
high = crash/lost reply; medium = unhelpful but safe); one reproducer per
BUG under repro/. Every case reported, never averaged. A registered FAIL is
recorded as FAIL, never re-run into a pass. Claims never exceed evidence.

- B1: all 62 sealed cases executed exactly once each; verdict counts
  OK + BUG + HARNESS-ERROR sum to 62 in every family table.
- B2: every BUG verdict has a one-file reproducer under
  artifacts/fable-redteam110-20260921/repro/ that replays it through a real
  loop102 daemon subprocess.
- B3: per-family OK / BUG / HARNESS-ERROR counts reported (10 families);
  severity counts over all BUGs reported (critical / high / medium).
- B4: whole registered wave finishes in < 30 min wall-clock on the Mac CPU.

Deviations locked before the run: (a) hearsay clarifies ("Do you know that
yourself ...") are checked with contains, not the abstain-bit list, which
does not cover that sentence; (b) split-clarifies ("... split that?") and
"Was that a question?" likewise checked with contains; (c) vanish
(delete-mid-read) is implemented as stop-daemon/plant/delete/reboot so the
deletion is deterministic, not a race; (d) D2/D6 payloads are expanded at
export time (1 MB of "x"; 150 KB of whitespace) so the sealed cases.json
holds the exact bytes; (e) burst200 expands to 100 bench teaches + 100 asks
in the runner, deterministically from the sealed op.

Environment: Mac CPU, offline, OMP_NUM_THREADS=1 MKL_NUM_THREADS=1,
`uv run --offline --no-project --python 3.12 --with torch --with numpy
python -B scripts/fable_redteam110_runner.py --run`.
Daemon per case: same prefix plus `python -B scripts/fable_loop102_agent.py
--daemon --dir <case-root> --config
artifacts/fable-loop102-20260921/loop102-config.json --idle-seconds 3600`.
