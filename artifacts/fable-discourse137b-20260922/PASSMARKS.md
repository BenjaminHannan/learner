# Exp 137b PASSMARKS — discourse-glued multi-word names, sealed before run

Agent: `scripts/fable_loop137b_agent.py` (Loop137bEars / Loop137bAgentLoop /
Loop137bMouth / Loop137bDaemon, build_agent137b, DEFAULT_CONFIG137B) +
`scripts/fable_fix137b_discourse.py` (closed 24-word list, abbreviation
rule) + drivers `scripts/fable_fix137b_probe.py`,
`scripts/fable_fix137b_bench.py`, `scripts/fable_fix137b_junk.py`,
`scripts/fable_fix137b_redteam143.py`, `scripts/fable_fix137b_sessions.py`.
Config: `artifacts/fable-discourse137b-20260922/loop137b-config.json`.
137's 2–4 token rule: `scripts/fable_fix137_names.py:123-127`, called from
`scripts/fable_loop138b_agent.py:142-169`.
Seeded here before any registered run; hashed to SEAL.sha256.txt together
with the config, probe, and drivers. Ledger P137b.1–P137b.7 appended
pre-run. Ledger `artifacts/fable-predictions-ledger.md` is append-only and
owned by the coordinator; only P137b prediction lines are added.

Environment: Mac CPU only, offline, `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`,
`uv run --offline --no-project --python 3.12 --with torch --with numpy python -B …`.
Every seed/case reported, never averaged. A registered FAIL stays FAIL
(recorded as FAIL with one diagnosis note; no silent re-runs). Claims never
exceed evidence. Any code edit after the seal (including scorer/driver
scripts) is reported and the affected marks re-run in the open; no rule
changes after the seal. Soak/rt110 flakes under heavy load are a known
mailbox race: re-run that suite once in the open and report both.

## Marks

- T1: `… python -B scripts/fable_fix137b_probe.py` (56 cases, in-process
  fresh loops). Bar: 56/56 OK — D 28/28 discourse-led twins equal bare
  twins exactly (reply + write); T 12/12 titles identical to loop138b;
  R 16/16 real names identical to loop138b. 0 wrong writes (no write
  whose subject/value triggers the discourse rule).
- T2: same run, sealed C089/C122 texts through loop137b. Bar: both store
  junk-free triples (`[Tom, boss, Ann]`, 0 junk writes); replies
  `Saved: Tom's boss is Ann.`; sealed redteam136 verdicts remain
  WRONG-WRITE (the nowrite expectation) with clean subjects.
- G1: `… python -B scripts/fable_fix137b_bench.py` (bench121 new/old/
  edit200/bench132, 800 items, `fable_bench121_run` by import; compare
  per-item verdict AND reply with `fable_bench121_loop138b_*_rows.jsonl`).
  Bar: 0 new wrong, 0 verdict moves, 0 reply moves (only scanned trigger
  is the abbreviation "A. A. Milne", exempt by rule).
- G2: `… python -B scripts/fable_marks123_all.py --agent
  scripts/fable_loop137b_agent.py --config
  artifacts/fable-discourse137b-20260922/loop137b-config.json --out
  artifacts/fable-discourse137b-20260922/marks137b --workers 4`.
  Bar: every suite per-case identical to
  `artifacts/fable-agent138b-20260922/marks138b`, except the SLEEP SKIP
  reason string names the new agent file (verdict identical). Scanned:
  bench/p4/rt110 sources 0 discourse-initial turns; rt81 3x "Actually"
  (137-parse None, base teaches clean); p2 2x "Actually" (same); Q1
  "Please forget Mira city" (forget-shaped, untouched).
- G3: `… fable_fix137b_junk.py` (redteam136 + cases150 + f1 + cases139b
  vs sealed loop138b rows), `… fable_fix137b_redteam143.py` (vs sealed
  `redteam143-loop138b.json`), `… fable_fix137b_sessions.py` (vs sealed
  `sessions152-loop138b.json`). Bar: 0 new WRONG/junk writes, every move
  predicted. Predicted moves: redteam136 C089/C122 keep verdict
  WRONG-WRITE but store `[Tom, boss, Ann]` (junk 2→0; all other 143
  cases byte-identical, C090/C105 stay OK); 143 zero moves (0 triggers
  scanned); sessions zero verdict/reply moves (14 discourse-initial turns
  all lowercase-or-base-handled); cases150/f1/cases139b zero moves.
- G4: each registered run < 25 min wall-clock Mac CPU (< 1500 s);
  daemon wrappers accept idle_seconds (default 30.0).

## Predicted ledger (P137b.1–P137b.7, in ledger before any run)

P137b.1 T1 56/56; P137b.2 T2 junk-free both; P137b.3 G1 0 moves/0 new
wrong; P137b.4 G2 per-case identical except SLEEP reason names new file;
P137b.5 G3 redteam136 C089/C122 clean-store moves only, 143/sessions/
150/f1/139b zero moves, junk 0; P137b.6 G4 every run < 1500 s;
P137b.7 title-edge exploratory: "Hey Jude's director ..." and
"Mary Ann's favorite movie is Hey Jude." strip (Jude) where loop138b
keeps (Hey Jude) — disclosed, outside sealed suites.
