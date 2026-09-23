Building your QA checker and blind typing panel — gathering specs and verifying the setup.
I've mapped the experiment specs — now I'll create the 100-turn casual typing panel before examining any existing code.
Panel sealed. Now verifying the exp 264 build (read-only).
VERDICT FIRST:
- Exp 270 (my build): DONE + SEALED. Blind casual-typing TEST-ONLY panel written: 100/100 turns, self-checks pass, seal verifies. No runs, nothing tuned, no panel ever opened.
- Exp 264 (builder slot in my order): already sealed AND registered by the concurrent worker in this same worktree before I arrived. I verified instead of duplicating: seal 23/23 OK, imports are read-only wrappers, ledger P264.1–P264.9 present, registered verdict FAIL. I created zero 264 files and zero ledger lines, because creating them would collide with that seal.

MARKS TABLE 1 — my 270 panel (integer counts, checked by make_panel.py):

| Check | Bar | Got | Pass? |
|---|---|---|---|
| Total turns | 100 | 100 | yes |
| casual family | 40 | 40 | yes |
| casual_q family | 15 | 15 | yes |
| lower_trap family | 15 | 15 | yes |
| clean family | 30 | 30 | yes |
| ids sequential t270-001..t270-100, family-block order | 100/100 | 100 | yes |
| duplicate turns | 0 | 0 | yes |
| casual all-lowercase, 0 apostrophes | 40/40, 0 | 40, 0 | yes |
| casual no final punctuation | >= 30 | 32 (8 end with a period, the "both" variation) | yes |
| casual_q lowercase, 0 "?" marks, gold ASK | 15/15 | 15 | yes |
| lower_trap lowercase + decoy word present | 15/15 | 15 | yes |
| lower_trap gold [] (pure trap) | — | 8 | n/a (report only) |
| lower_trap gold = only the real fact | — | 7 | n/a (report only) |
| clean capitalised; 20 TEACH end ".", 10 ASK end "?" | 20 + 10 | 20 + 10 | yes |
| TEACH frames / ASK frames / empty gold | — | 67 / 25 / 8 (= 100) | n/a |
| clear:false flags | — | 3 (t270-059 "frank", t270-062 "robin", t270-063 "mark"-idiom; name-reading defensible) | n/a |
| seal files hashed + panel lines | 2 files, 100 lines | 2, 100 | yes |

MARKS TABLE 2 — exp 264 registered result (sealed builder's numbers, verified by me, read-only):

| Mark | Bar | Got | Pass? |
|---|---|---|---|
| M1 no_save saves <= 1 | <= 1 | 2 | NO |
| M2 wrong saves <= 1 | <= 1 | 5 | NO |
| M3 TEACH recall >= 85% and >= B+30 | 85%+ | 81/125 = 64.8% (B 1.6%, diff +63.2) | NO |
| M3b held back <= 12% | <= 12% | 38/125 = 30.4% | NO |
| M4 ASK recall >= 90% | >= 90% | 37/40 = 92.5% | yes |
| M5 median <= 800 ms | <= 800 | median 880.1, p90 1826.8, max 2664.2 | NO |
| M6 frames byte-identical in A_brake | exact | 0 mismatches | yes |
| Overall | — | FAIL | FAIL |

EVERY MOVE (what I actually did):
1. Checked `uptime` + `df -g /`: load ~60, disk 13 GB free (over the 3 GB floor). Light work only, no heavy runs.
2. Read OPUS-RULES.txt, design 264 doc, 261 brief, earpanel264-spec (via `git show origin/main:`).
3. Wrote the 270 panel BEFORE reading any code: new file artifacts/claude-typepanel270-20260923/make_panel.py (items held by hand in the file).
4. Ran it with /usr/bin/python3: self-checks OK, wrote panel.jsonl (100 lines).
5. Sealed from repo root: `shasum -a 256 panel.jsonl make_panel.py > SEAL.sha256.txt` (2 lines).
6. For 264: read 261b PASSMARKS + 264 PASSMARKS/RESULTS (category-level, allowed); re-ran `shasum -c` on the 264 seal (all OK); grepped 264 scripts for import lines only (they wrap 261/261b modules read-only, no copies). Never opened any TEST-ONLY panel item (no 257/261/261b/235 panels, no reading94, no natural/table panels). Never edited, deleted, committed, or pushed anything.

MISSES / DEVIATIONS (every one):
1. Dual-role read overlap: the 270 writer brief said "read ONLY earpanel264-spec", but the same order required the 264 builder reads (design doc, 261 brief, 261b artifacts). I read both sets. Blindness held in the way that matters: the panel was written and sealed before I read a single line of code content (only script filenames were ever listed), and I never opened any test panel, result detail, or training data.
2. No new 264 scripts and no P264.n ledger lines from me: the concurrent worker had already sealed 264 (23 files), appended P264.1–P264.9, run every arm once, and written RESULTS (FAIL). Additive-only + seal rules forbid me from adding files to their sealed dir or re-predicting their experiment, so I verified and reported instead of duplicating.
3. "PUSH: artifacts/claude-typepanel270-20260923": OPUS-RULES forbids commits/PRs/pushes, so PUSH = files left in place, sealed, uncommitted. No git operations performed.
4. 264 predictions P264.3/P264.4 ranges missed by 0.2/0.4 (64.8 vs 65–78; 30.4 vs 20–30) — the sealed builder's record, not mine; reported as-is.

WHAT IT MEANS (plain high-school English):
- The 270 panel is ready for whoever scores it: 40 sloppy-typed facts, 15 sloppy questions, 15 traps where an ordinary word looks like a name, and 30 clean controls that must come through unchanged. The answer key uses correct capitalisation, so the scorer can tell whether the system fixes casing or gets fooled by words like "rose" and "may".
- Exp 264's idea (ask three questions instead of one yes/no) failed its bar: it traded 13 true facts to remove 1 wrong save (94 hits/6 wrongs vs 81 hits/5 wrongs), holds back ~30 of every 100 true facts, and is too slow (880 ms vs 800 ms). Questions-answering and no-invention (M4, M6) passed.

WHAT IT DOESN'T MEAN:
- My 270 self-checks passing does not mean the panel is certified or that any system passes it — it is an unrun TEST-ONLY panel; the scorer's verdict comes later.
- 264 failing does not mean the ear got worse (ear alone read 95/125; the YES/NO arm reads 94/125 on the same harder panel) and does not mean a tweak would save it (no threshold exists; holds come from three agreeing questions, not one number).
- My verifying 264 does not make me its builder and does not re-open its FAIL: 261/261b stay FAIL, 264 is FAIL, and no sealed file was touched.
