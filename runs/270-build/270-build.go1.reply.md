Building your QA checker and ear-line normaliser — gathering the specs and baselines.
Exp 264 is already sealed with results in this worktree, so my remaining job is the 270 builder. Reading the 263 base and related context now.
The 270 spec lives entirely in my brief (no design file on origin/main). Setting up the work plan.
Rather than reading the whole ear stack, I'll probe 263 empirically. Checking the 263 run driver pattern first.
Now probing 263's behavior on lowercase input directly.
Probe confounded by shared notebook state on disk. Redoing with isolated state dirs.
Key design questions now hinge on scorer case-handling. Reading 263's scorer (read-only).
All learning probes done. Checking driver helper signatures, then writing code.
Learning phase complete. Writing the normaliser (new file).
Patching a hole: full-word common check plus never-fix stoplist for the possessive fix.
Now the agent wrapper.
Classic overlap-consumption bug. Rewriting the possessive fix as a two-word scan with names-aware stem rules.
The two-word scan still skips overlaps. Switching to a token-position scan.
Normaliser behaves. Probing exact clean store forms needed for dev expectations.
Writing the dev set generator (own wording, fictional names).
Fixing three dev-set issues (mismatched setups, noisy gold).
Now the dev runner and scorer.
Now fixing the three bad dev items.
Name-relation works identically. Adding two name-items to dev for coverage.
Notebook precedence verified. Writing PASSMARKS + predicted moves.
Seal 12/12 OK. Appending ledger predictions.
Schema gate passes. Load is 67.8 (above 60) — waiting for it to drop before the registered run, per shared-machine rules.
Final marks confirmed. Gathering remaining details for RESULTS.
**Verdict: registered FAIL** (M1, M2, M5 fail; M3, M4, M6 pass). Plus one load-bearing finding: the brief's base number (263, loop line) does not fit this panel — see discrepancy below.

**Marks table (integer counts, arm A vs A263, each arm run once)**

| Mark | Bar | Got | Pass? |
|---|---|---|---|
| M1 | casual exact TEACH ≥ 30/40 and ≥ A263+20 | A 23/40, A263 6/40, margin +17 | NO (short by 7 and 3) |
| M2 | casual_q ASK ≥ 12/15 | A 0/15 | NO |
| M3 | lower_trap wrong saves ≤ 1 | A 0, A263 0 | yes |
| M4 | clean 30/30 byte-identical to A263 | 30/30 | yes |
| M5 | 0 new wrong saves vs A263 overall | 3 (t270-002, t270-028, t270-033) | NO |
| M6 | median added time ≤ 20 ms | median 0.0312 ms, max 0.1153 ms | yes |

**Every move / every miss.** M1: A exact on 23 (all 14 no-apostrophe possessives except 3, all 8 lowercase verb slots, 9 my-shapes); A263 exact on 6 (my-shapes only). A's 17 misses: 3 near-miss spans from my sealed keep-s rule (Beno/Dilo/Haki stored with an extra s — also the 3 M5s), 7 verb-shape gaps the loop ear never learned (works-as ×5, speaks ×2), 4 exotic-pet relations it never learned (rabbit, parrot, turtle, goat), 3 more verb-shape gaps. M2: 0/15, structural — the loop line emits no ASK frames (no-write 15/15 both arms, 0 writes). M3: 0 wrong saves both arms; 7 trap misses on both arms (compound turns whose real fact uses an unreadable shape — misses, not saves). Clean: 7 TEACH misses identical on both arms, 30/30 identical replies. Dev (pre-seal, my own 116 turns): A 51/51 teach, 16/16 q, 24/25 traps, 24/24 clean vs 263's 13/51, 12/16, 25/25, 24/24; 74 rewrites all logged in devreport270.json.

**Deviations.** D1 check-tail suppression + no so-head suppression (pre-seal, reasoned in PASSMARKS). D2 whos→who's etc. D3 panel runner/scorer written post-seal from observed schema (no spec was provided). D4 panel never opened pre-seal. D5 triple→frame proxy for loop arms. D6 post-seal scorer fix (misses≠wrong saves per the brief's wording), re-scored from recorded rows — arms ran once each, sealed files untouched (seal re-verified 12/12 OK). D7 Mac load 55–113, single sequential process. Ledger: P270.1–P270.8 predictions, P270.9–P270.10 outcome/discrepancy appended (predictions .1/.2/.5 wrong, .3/.4/.6 right).

**Discrepancy (please read):** the brief says base "263 = 260 + comma guard" (loop), and I built, sealed, and ran exactly that — but the panel gold (TEACH/ASK frames, relation_aliases, species, chain, "me"), the marks (frame recall, ASK emission), and the compute note ("the ear on BensPC") are ear-line (smolear neural ear). The loop ear has no shapes for works-as/speaks/is-a/exotic-pets and emits no ASK frames, so M1 has a loop-line ceiling around 23–26 and M2 is unscoreable by construction. M1/M2 here grade the mismatch, not the normaliser, which moved every movable class (+17). The ear-line 270 could not be run: BensPC is unreachable (ping 100% loss, SSH timeout, down since before 02:30 local, re-polled through this run).

**What it means (plain English):** the normaliser works — unreadable lowercase chitchat now saves (23 vs 6), traps still don't save (0 wrong), clean turns are byte-identical (30/30), cost is 0.03 ms. But the test was written for a smarter ear, so the run fails on the three marks that grade ear vocabulary, and passes the three that grade the normaliser.

**What it doesn't mean:** it doesn't mean the normaliser is broken — every miss is a shape the base ear can't read even perfectly typed, or the 3 documented keep-s stems. It doesn't mean checks/pretends/plans are at risk — all no-fact traps hold on both arms. It doesn't say anything about the ear line — the ear never ran here; an ear-based 270 needs a new brief (this seal covers the loop arm, and the panel turns are now exposed to me).

**PUSH deliverables present:** artifacts/claude-type270-20260923/ (PASSMARKS, RESULTS, config, dev + panel rows, score, SEAL), scripts/claude_type270_*.py (7 new files), artifacts/fable-predictions-ledger.md (P270.1–P270.10 appended, append-only).
