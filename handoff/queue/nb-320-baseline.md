COMMON RULES (the notebook thread, Claude, wrote this task on 2026-09-23). Same COMMON RULES block as handoff/queue/talk-f0-base.md: read its first 14 lines and follow them in full (additive only, fictional names, never the repo-root notebook/, uv run python, report format, getting files with git show origin/main:<path>).
GPU: no (Mac CPU only).
TIME CAP: 180 minutes in total. macOS has no `timeout`, so run long steps in the background and kill their exact PID if they overrun.
DISK: the 1,000,000-fact notebook is about 400 MB. Check `df -g /` first and stop if free disk is under 5 GB. Keep every test notebook under /tmp/nb320/ (never inside the repo) and delete /tmp/nb320/ at the end.

YOUR TASK: builder for nb-320, a REPORT-ONLY baseline of the current notebook storage at three sizes. Read design/v3/30-modes/320-notebook-compact.md first. No agent code changes. Artifacts go in artifacts/claude-nb320-20260923/.

WHAT IS MEASURED: the store model 292 uses, `FixedIndexedLoopNotebook` in scripts/fable_fix220_restartindex.py. Its contract API is `.nb` (class FixedIndexedContractNotebook; methods in scripts/fable_notebook_contract.py: declare_relation, new_entity, assert_fact(correction=..., raw=...), retract, ask(name, [relations]), current). Read those files; never edit them.

1. RUNNER. Write scripts/claude_nb320_scale.py. It must take `--factory module:attr`, a callable that takes a notebook directory and returns an object with the contract API. The default is a function in your runner: `open_baseline(root)`, which returns `FixedIndexedLoopNotebook(root).nb`. nb-321 will reuse this runner unchanged with its own factory, so keep all backend-specific code in the factory.

2. WORKLOAD (deterministic; seed 3200; sizes N = 20,000 / 100,000 / 1,000,000 FACT writes).
- People: N/10 entities. Each has a fictional two-part name built from syllable lists you write, like "Talvo Brenick". Names must be unique and must never be real famous people.
- Relations: take the relation names from the o0b data (below). Declare 30 as functional and the rest as multi-valued.
- Values: 50% another entity, 50% a literal. Literals are fictional place/thing words built from syllables.
- Operations, in order:
  - 85% teach: a new fact through assert_fact(event_id, "listening", "taught", ...). Never teach a second value for a functional (subject, relation) that already has one.
  - 10% correction: pick an active functional fact and assert a different value with correction=True.
  - 5% forget: retract an active fact with actor "listening".
- Keep your own ground-truth dictionary of what every (subject, relation) should answer after each operation. Record every Result status and count the ones you did not expect.
- raw sentences must be realistic, varied English, not one template. Build them from the o0b generator data:
  - `git fetch -q origin builder-outbox`
  - `git show origin/builder-outbox:artifacts/claude-own-o0b-20260923/train-00.jsonl.gz` (and train-01).
  - Use only rows with family "tell", act "STATE", count 1, one fact, mode "ASSERT", and owner_kind "NAME" (about 1,880 per file).
  - Take the row's turn text and replace its owner span and value span with this operation's subject name and value text. The spans are character offsets: `facts[0].owner` and `facts[0].value_span`.
  - For corrections, prefix the result with one of 10 correction openers you write ("Actually, ", "No wait, ", ...).
  - Never use the "binding" family (it is mislabelled).
- Write the workload once per size to /tmp/nb320/workload-<N>.jsonl, then replay the same file into each backend.

3. MEASURES, per size, each in a FRESH process:
- (a) Write: facts per second with the real fsync. Include the total wall time.
- (b) Disk: bytes of every file in the notebook dir. Report bytes per FACT write and bytes per event. Also report the gzip -9 and xz -9 sizes of events.jsonl, as a reference only.
- (c) Cold open: the time for the factory to open the finished dir. Run it 3 times, each in a new process, and report the median.
- (d) Peak memory of the open-and-probe process. On macOS ru_maxrss is in BYTES.
- (e) Recall probes:
  - 2,000 one-hop asks: 60% plain taught, 20% corrected (must give the new value), 10% forgotten (must give MISSING_FACT), 10% never taught (must give MISSING_FACT).
  - 1,000 two-hop asks, where the first hop's value is an entity.
  - Use ask(name, [relations]) and score every probe against the ground truth: right / wrong value / missing-but-should-answer / answered-but-should-not.
  - Latency p50, p99 and max, in ms, for one-hop and for two-hop.
- (f) Only at 20,000: crash and tamper tests.
  - Crash: 30 child processes each write facts and append each event_id to an ack file, fsynced, only after assert_fact returns. Kill each with SIGKILL at a random moment. Then reopen and count: acknowledged-but-lost, duplicates, failed opens, torn tails (repair with repair_torn_tail() if needed).
  - Tamper: 20 copies of the finished notebook. In each, change one byte at a random offset inside the log, excluding the final line. Count how many are caught by opening the store (which runs fable_fix77_core.verify_full).
- Caps:
  - If the 1,000,000 size passes 90 minutes of writing, or memory goes above 8 GB, stop that size.
  - Report it as DID NOT FINISH, with how many facts were written and the rate so far, then probe what exists.
- Record `uptime` load before each timing step. Timings on a busy Mac are noisy, so say so.

4. SEAL: write artifacts/claude-nb320-20260923/PASSMARKS.md. This is report-only, so it has no pass bars. List the exact measures above and the workload seed. Then seal (shasum -a 256 of the runner, the workload generator and PASSMARKS.md into SEAL.sha256.txt) BEFORE the registered run. Run once.

5. OUTPUT:
- artifacts/claude-nb320-20260923/results.json, with every number.
- RESULTS.md: result first, integer counts, a table per size, every unexpected status and every wrong recall listed.
- Five sample event lines from the 20k log, so the director can see the byte layout.
- Never push a notebook, a workload file or anything over 5 MB.

PUSH: artifacts/claude-nb320-20260923 scripts/claude_nb320_scale.py scripts/claude_nb320_workload.py
