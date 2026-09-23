# Exp 269 RESULTS: 265's arm A plus the text-level group-owner check (builder, 2026-09-23)

## Result: registered run INCOMPLETE (blocked) -- no verdict

The blind panel sealed before my seal and both seals verify, arm B ran once
on all 100 turns, but the BensPC GPU host went unreachable (SSH + ping 100%
loss) at ~02:30 local, after the dev wave and before the registered ear
wave. I polled the host for ~120 minutes (02:30-04:30 local) with zero
contact. The registered ear arms (A, A265, A261b) never ran, so M1-M8 have
no numbers and there is no PASS/FAIL. This is reported as INCOMPLETE, not
FAIL: nothing ran twice, nothing was re-sealed, no sealed file changed.

Predictions P269.1-P269.8 stand as written; P269.9 below records the block.

## What ran, with integer counts

- Panel seal: `shasum -c` from the repo root 2/2 OK (panel.jsonl +
  make_panel.py). Never opened before my seal.
- My seal: 15/15 OK after all runs (rechecked at the end; no post-seal
  edits to any sealed file).
- Strict schema check: passed, 100 lines, ids o269-001..o269-100, families
  group_owner 30 / mixed 15 / first_person 20 / named 15 / non_owner_we 20.
  No SCHEMA-MISMATCH, no VOID.
- Arm B (138i + 228, registered, run ONCE on all 100 turns, local CPU):
  per family TEACH hit/gold, wrong, saved, turns-with-wrong:

| Family | n | B hit/gold | B wrong | B saved | B turns_wrong |
|---|---|---|---|---|---|
| group_owner | 30 | 0/0 | 0 | 0 | 0 |
| mixed | 15 | 0/15 | 0 | 0 | 0 |
| first_person | 20 | 12/20 | 0 | 12 | 0 |
| named | 15 | 13/15 | 0 | 13 | 0 |
| non_owner_we | 20 | 0/20 | 0 | 0 | 0 |
| ALL | 100 | 25/70 | 0 | 25 | 0 |

  B abstains everywhere outside first_person/named (0 saves on 65 turns),
  same pattern as 265's panel. B recall on this panel: 25/70 = 35.7% TEACH
  (report-only; the M3 bar math needs arm A, which never ran).

## What did not run (every miss listed)

- Registered ear inference on BensPC (panel269_turns.json, 100 turns): 0/100.
- Registered checker queries (prompt B): 0.
- Arms A, A265, A261b on the panel: 0 runs each (0 re-runs; nothing to re-run).
- Registered score: not produced (the scorer needs apreds + pyes).
- M1-M8: no numbers. P269.1-P269.7 predictions are unresolved.
- llama-server stop: could not be performed (host unreachable). Server PID
  26480 (Qwen3.8-27B-UD-IQ4_XS, 265's exact flags) was left running on
  BensPC with the model resident (~13.7 GB VRAM at last sighting 02:2x).
  Exact PID recorded here for cleanup. pythonw 13036 and all other BensPC
  processes were never touched (no contact at all during the outage).

## Timeline (all local; UTC = local + 4)

- Dev wave complete on BensPC ~02:26 (121-turn infer median 123.2 ms,
  66 beamed, ckpt sha ok; 162 checker queries, 0 fallbacks, median 282.7 ms).
- PASSMARKS written, seal 15/15 OK, ledger P269.1-P269.8 appended ~02:35.
- Panel seal 2/2 OK ~02:36 (panel had sealed at ~01:47, before my seal).
- Panel turns extracted (schema OK, 100 turns) ~02:37.
- ~02:30-02:40: SSH to BensPC starts timing out (was fine minutes earlier).
- Arm B registered run (local): 100/100 items, once, ~02:40-02:45.
- ~02:45-04:30: SSH + ping polled every 8-10 min, 100% failure throughout
  (~120 min total). tailscale CLI unusable on this Mac (broken x86 binary).
- Seals rechecked 15/15 + 2/2 OK at close.

## Deviations

- D1-D7 from PASSMARKS carry over unchanged (D2's 120-min poll budget was
  spent on host recovery instead of the panel seal, which was already
  present; D3's final server stop is pending host recovery).
- D8 (new): registered GPU wave never started due to host network outage;
  no arm ran more than once (B once; ear arms zero times); verdict
  INCOMPLETE by blockage, not by measurement. Resume path: when BensPC is
  reachable, scp panel269_turns.json, run 257-infer (cuda, --expect-sha
  55284dec..., --tau 9.3), qbuild panel mode, verify/reuse llama-server PID
  26480 (or restart with sealed flags if dead), run checker, scp back
  preds+pyes, score with the sealed scorer (theta 0.25), then stop the
  server by exact PID and confirm nvidia-smi idle. No re-seal needed (sealed
  files unchanged); arm B must NOT be re-run (already ran once).

## What it means (plain English)

The homework (dev) is done and looks good: the new text check asks on all
68 group-worded dev turns and falsely asks on 0 of 53 control turns, and the
safety properties hold by construction. But the final exam (the blind
panel) could not be given to three of the four students because the GPU
computer fell off the network and stayed off for two hours. The fourth
student (arm B) took the exam: it answered 25 of 70 facts right, made zero
wrong saves, and skipped everything with "we/our" wording. No verdict on
the new check is possible until the GPU computer comes back.

## What it doesn't mean

It does not mean the check failed: it never got to run on the panel. It
does not mean the panel is bad: its seal and schema check out. It does not
mean dev was wasted: all dev numbers, the seal, and arm B's run stay valid,
and the registered ear wave can resume without redoing anything. It does
not mean arm B passed or failed anything: B has no bars, and its numbers
are baseline only.
