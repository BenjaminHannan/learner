# 0.2d-G results (written Mon Sep 28 00:11:08 UTC 2026): G is in the build's notes slot, and the build's note step writes exactly the notes G was scored on

Checks and pass marks: design/v3/30-modes/02d-gates-ADDENDUM-52.md, committed in ee96d8f04 before any check ran. The
build file is scripts/claude_e2e02d_g.py (harness arm `claude_e2e02d_g:build_02d_g`). This proves the wiring only.
Whether G helps the whole build is judged later by the build's own memory row, after the seal.

## Verdicts (shown)
| Check | Pass mark (fixed in advance) | Result | |
|---|---|---|---|
| W1 same path | the build's note step and claude_rd378_write.py give identical notes (text, cites, when) on 504 of 504 G5 turns, same card and dtype | 504 of 504 identical (raw output identical on 504 of 504) | **PASS** |
| W2 pointers | every note row points at the raw user turn it was written on; recall returns heard rows only (stub writer in the selftest, real G on the 14 chat dialogs) | stub: 4 of 4 note rows. Real G: 108 note rows on 99 of 99 user turns all point right; 99 of 99 heard rows right; recall gave 0 non-heard rows in 1,470 over 207 queries (774 reached through a note) | **PASS** |
| W2b (added) | the build's whole turn path writes the CLI's notes on 99 of 99 chat user turns | 99 of 99 notes equal; 99 of 99 note row texts equal | **PASS** |
| W3 nothing else moved | claude_e2e02d.py's selftest passes with the file unchanged; the new selftest passes | claude_e2e02d.py sha256 4870333c... unchanged; 20/20; the new file's selftest 25/25, which includes 0.2d and 0.2d-G side by side with the same replies, talker input, fact book, heard rows and per-turn log except time; checks.py 6/6. Passed in the cloud session and again on the rental | **PASS** |
| Merge (report only) | rebuilt model.safetensors = a0fb1c9b... | a0fb1c9bd663b00b1470d515ae0c38a8dd3ed7d1cfdead70325137312300d1ed, **matches** bit for bit (tokenizer.json matches the adapter's too) | |

W1 passed on its only real run (attempt 3). No wiring fix was needed, so the run-to-run noise check (a second CLI
run) did not trigger. A blind recount by a separate script (not checks.py) re-read w1_cli.jsonl, w1_build.jsonl and
the rental's notes_G.jsonl. It got 504 of 504 on text, cites and when; 504 of 504 on whole note objects; and 504 of 504
on raw text, both for CLI vs build and for build vs rental.

## Report-only rows (shown; vast3/w1.json, w2.json, timing.json)
| Row | Result |
|---|---|
| Notes that match the rental's scored notes (rd-378g vast/g5/notes_G.jsonl) | **504 of 504 turns** identical, raw text too. Same card model (RTX 5090), same stack, same merged sha |
| Notes per turn (all 43 dialogs) | 0.730 (368 notes on 504 turns; 304 of 504 turns have a note), as RESULTS-G5 reported for G |
| Notes per turn (14 chat dialogs) | 1.091 (108 notes on 99 user turns; 87 of 99 turns have a note) |
| Unparsed turns | 0 of 504 (0 of 99 through the build's turn path) |
| Notes citing an earlier turn (N2) | 102 of 368 overall. In the chats: 8 of 108, and all 8 also cite their own turn. The extra offsets are -2 (6 notes, the user's previous turn), -6 (1) and -1 (1, a talker reply). rd-378g's scored store would also have pointed those 8 at the earlier turns; the build points each note only at its own turn, as the prompt asked |
| Writer time per turn, RTX 5090, bf16, 504 turns | median 331 ms, p90 551 ms (build's note step); the CLI 333 / 558 ms. rd-378g's own rental, a different 5090 host: 884 / 1,455 ms |
| The build's time per turn, 8 turns (2 chat dialogs x 4 user turns) | without G (N0): median 348 ms, p90 570 ms. With G: median 860 ms, p90 1,263 ms. G's own step: median 429 ms, p90 672 ms |

The timing row uses stand-ins, fixed in ADDENDUM-52: a stub reader (lis-320's weights were not on the rental) and the
base MiniCPM5-1B as the talker, standing in for LFM2.5-1.2B because no other model download was allowed.
- Suggested: in the real build, where the reader is also a 1B model call, G adds about 0.3-0.7 s per turn on a 5090.
  The slowdown factor will be smaller than the 2.5x seen here, because the reader's time is missing from this row.
- Untested: the real reader and talker were not timed.

## How it ran (shown)
- One rental job, three attempts. The job was started from Ben's Mac, because G's adapter is only there; the Mac sent
  a copy and its folder was only read. Queue files: handoff/queue/rent-e2e02dg-1.md, -2.md and -3.md. Kit:
  kit/mac.sh and kit/box.sh. Mac replies: runs/.
- All three attempts rented an RTX 5090, and each was destroyed only after its copy-back matched the rental's manifest
  file by file. I re-checked every copy on main: 3 of 3, 9 of 9 and 23 of 23 files. No instance labelled
  claude-e2e02dg is left (vast API, 00:10 UTC).

| Attempt | Instance, host | Ended | Spent |
|---|---|---|---|
| 1 (pin ee96d8f04) | 53058679, host 483833 | the host timed out reading download.pytorch.org (pip install torch), before any check; vast/ | $0.08 |
| 2 (pin d57d1904a: more patient download, skip host 483833) | 53061137, host 406325 | torch installed, pins and all 6 adapter files matched, then the selftests stopped: my packing list left out design/v3/60-listener (relation-names.txt, read by claude_lis300_compiler); vast2/ | $0.04 |
| 3 (pin 32b700b63: sends it; the exact rental tree was first rebuilt and tested in the cloud session) | 53062886, host 406325 | DONE: every step, every check; vast3/ | $0.08 |
| Total | | | **$0.20** of the $4 cap |

- Neither fix touched a check: ADDENDUM-52, claude_e2e02d_g.py and checks.py are byte-identical from ee96d8f04 to
  32b700b63. Only the setup (pip timeouts) and the file list changed.
- Attempt 3's stack: torch 2.11.0+cu128 (from download.pytorch.org/whl/cu128), transformers 5.17.0, peft 0.21.0,
  bf16, RTX 5090 (driver 580.105.08). The base was openbmb/MiniCPM5-1B at 87179e5c, the only model downloaded. G's
  adapter is stored in fp32, and the merge used peft's default loading.
- Pins checked on the rental (vast3/pins.txt):
  - claude_e2e02d.py sha256 = the one ADDENDUM-52 names;
  - claude_rd378_write.py and claude_rd378_common.py match rd-378g's SEAL;
  - all 6 adapter files match SEAL-run;
  - the rental notes file matches SEAL-run's W/g5_G.jsonl.
- "RD378G-SEAL 13 of 14" there only means one sealed rd-378g file was not sent. It is not a mismatch.
- Before renting, the runner code was dry-run in the cloud session with a fake writer whose note is the whole prompt
  (dryrun_fake_writer.py/.txt). The build's turn path handed G the same prompt text as claude_rd378_write.py on
  99 of 99 chat turns, and the note step did the same on 504 of 504 turns. That says nothing about G itself.
- The G5 dialogs were test input only. Nothing was trained.

## What this means
- Shown: 0.2d-G's note step runs the exact G that rd-378g scored. The rebuilt weights match a0fb1c9b bit for bit, and
  on the 43 G5 dialogs it writes the same notes as the scoring run, byte for byte. Through the build's own turn path
  on the chat dialogs it writes the CLI's notes on 99 of 99 turns. Every note points at the raw user turn it came from,
  and recall only ever returns raw user turns.
- Shown: a 5090 with this stack rebuilds G reproducibly. So the machine that runs the seal can rebuild G with
  `python -B scripts/claude_e2e02d_g.py merge ...` and the build's sha check (NOTES_SHA02D) will accept it.
- The disclosure every use of G carries (rd-378g ADDENDUM-K): G is a search aid only, "trained on ungraded GLM and
  Luna notes; G's unsupported share 49.2% vs R's 50.9% on fresh dialogs", "no less true than the rd-378 writer". About
  half of each writer's notes were judged unsupported, so no note is offered as true. Answers read raw lines only.
- Two known differences from the setup G was scored in (ADDENDUM-52):
  - N2: pointers go to the turn written on, not to the cited turns. This affects 8 of 108 chat notes' extra pointers.
  - The date line comes from "today is ..." rather than LoCoMo's session dates.
  - Untested: whether either one changes search results.
- Not shown here: whether G helps the whole build. That is the build's memory row, after the seal.
