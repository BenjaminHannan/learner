# bm-390 amendment: Windows line endings (benchmarks thread, 2026-09-25, registered before any run on real items)

The sealed files (SEAL-code.sha256.txt, 8 lines; the 336b seal, 229 lines) are unchanged. This note adds one
difference to how bm-390 is launched on BensPC. Nothing about the marks, arms, data, prompts or scoring changes.

## What happened
bm-390's first attempt on BensPC stopped at its smoke test on made-up data (RESULTS-benspc.md on builder-outbox):
TurnLog323Corrupt "read-back mismatch" on the agent's first turn. The sealed turn log
(scripts/claude_nb323_turnlog.py, `_append`) and the notebook (scripts/fable_notebook_contract.py, `_append`)
append each line in text mode, then read the last bytes back in binary mode and expect exactly line + "\n".
Windows text mode writes "\n" as "\r\n", so both checks fail there. Linux never translates (336 and 336b ran this
agent on Linux rentals). The rental for bm-390 was refused (vast.ai balance below zero), so the run stays on BensPC.

## The one difference
Every bm-390 command on BensPC starts with `python -B scripts/claude_winnl_wrap.py`. On Windows it wraps `open`
(builtins.open and io.open) so that a text-mode open for writing that does not choose a newline gets newline="",
which writes "\n" as "\n": byte for byte what Linux writes. Text reads, binary opens and opens that choose their
own newline are untouched. Off Windows it changes nothing. It applies to every arm (P and the plain arms), so all
arms run under the same conditions. It changes the bytes of files written on Windows (no "\r"), never what a model
reads or computes.

## Evidence (Linux, Windows line endings simulated by scripts/claude_winnl_test.py)
Unit test (`python -B scripts/claude_winnl_test.py unit`), real sealed classes, WINNL-UNIT PASS:
```
{"sim_windows": true, "fix": false, "turnlog": "TurnLog323Corrupt: turnlog323: read-back mismatch", "notebook": "LogCorrupt: read-back mismatch", "files": 2, "crlf_in_files": 2}
{"sim_windows": true, "fix": true, "turnlog": "ok lines=2 torn=False", "notebook": "ok events=2 torn=False", "files": 2, "crlf_in_files": 0}
{"sim_windows": false, "fix": false, "turnlog": "ok lines=2 torn=False", "notebook": "ok events=2 torn=False", "files": 2, "crlf_in_files": 0}
winnl: not Windows, nothing changed | UNTOUCHED
PASS without the fix, simulated Windows fails like BensPC
PASS with the fix, simulated Windows passes
PASS plain Linux passes
PASS file bytes with the fix equal plain Linux bytes
PASS the wrapper changes nothing off Windows
WINNL-UNIT PASS
```
The notebook fails the same way as the turn log, so fixing the turn log alone would have stopped the run at the
first saved fact.

End to end, the registered smoke command on the made-up smoke chat (stand-in reader = the base 1B on CPU, so the
replies mean nothing; only "does it run, and does it do the same thing" is tested):

| Run (same smoke command, CPU, OMP 4) | Exit | Result |
|---|---|---|
| simulated Windows, no fix | 1 | TurnLog323Corrupt: turnlog323: read-back mismatch on the first turn (the BensPC traceback) |
| simulated Windows, with the fix | 0 | wrote locomo_P.jsonl rows=5 bare=5; sleep log 2 rows, both checkpoint_exists true; 0 "\r\n" in its files; 893 s |
| plain Linux, through the real wrapper (no-op) | 0 | the same counts; 0 "\r\n"; 899 s |

Between the last two runs, the reading row, both sleep rows and all 5 question-only (P_bare) replies were
identical. All 5 P replies (the question inside the LoCoMo answer prompt) differed. That is not the fix: 0.1's
chat and creative reply paths sample (do_sample=True with no seed; scripts/claude_chat338_agent.py:210,
scripts/claude_cre333b_agent.py:38), and this torch seeds every process at random (two fresh processes printed
initial seeds 13788659073533309628 and 13388878523457040565). An earlier plain Linux smoke of the same sealed code
(no wrapper at all; its thread count may have differed) also gave a different first P reply.

## Clarification this test found (not a change)
PASSMARKS says "greedy decoding" for the arms. That is true for T, Rb, C, Q2 and L12 (the harness decodes greedily),
but 0.1's own chat and creative replies are sampled, as sealed. P's numbers are therefore one
draw: a re-run would give somewhat different replies. The paired bootstrap covers which questions were asked, not
this reply-to-reply variation. VERIFY will say so. Nothing is re-seeded, because that would change the sealed build.

## Checks on BensPC (in handoff/held/001-bench-bm390w.md)
The smoke on BensPC with the wrapper must pass (exit 0, rows=5, 2 sleep rows with checkpoint_exists true) and every
file it writes must contain 0 "\r\n" before any real item runs. Every registered command's first printed line
must be the wrapper's Windows line. Known gap: BensPC runs Python 3.10, where pathlib keeps its own reference to
io.open, so Path.write_text is not covered there (the Linux test ran Python 3.11, where it is). The only byte-exact
data written that way is the turn log's torn-tail repair, which a fresh run never needs; if it ever ran, the next
check would fail loudly (TurnLog323Corrupt), never silently.
