# mu-404 and mu-403: one rental, two single-change tests on the 0.2c stack WITH the reader

"Making things up about you" thread, written 2026-09-26 ~15:00 UTC, fixed before the run. DEV data only.
Follows mu-402 (artifacts/claude-mu402-20260926/VERIFY.md): the sleep adapter is not shown to cause 0.2c's made-up
claims about the user (S1: X 26 vs plain T 16), and with no reader at all the joined build made up less than the plain
1B (75 vs 102 flags). 0.2c's chat and creative prompts also carry the notebook's facts about the user
(claude_cre333_agent.context_facts keeps every "user" fact, up to 40); mu-402's rig had none.

## Arms (scripts/claude_mu404.py; code, panel and these marks sealed in SEAL.sha256.txt)
All arms: claude_e2e02c:build_02c as frozen (SEAL-code), the real lis-319 reader (--model, READER_SHA
e688e1b2...6a76 checked by scripts/claude_readersha_wrap.py), sleep adapter NOT loaded (0.2d keeps it off chat),
torch and random seeded per turn as in mu-402, panel devchat/ here (80 fresh dev chats, 446 turns, names N-Z).
- R: control, build_r.
- F: R with notebook facts removed from every 1B writer prompt (context_facts returns nothing to chat 338 and
  creative 333d). One change. Test **mu-404**.
- P: R with the mu-403 fix (MU403_FIX in claude_mu404.py). One change. Test **mu-403**. Which fix was fixed before
  any margin was computed (scripts/claude_mu403_auc.py, 01b448cfc): AUC >= 0.65 of the 1B's self-check margin on
  mu-402's judged chat replies -> "ground" (the 1B ranks its own 4 chat samples, least-assuming first, via
  scripts/claude_pick403.py on chat 338b only; guards unchanged); below -> "sysline" (one sentence added to chat
  338's system prompt: claude_mu403.VARIANT_LINE). The AUC result and the chosen fix are recorded in AUC.md here.
- T: plain 1B twin (claude_twinb), report only and mark M4.

## Judging (scripts/claude_mu404_judge.py)
Claims: every (arm, conversation) packet read by two blind Opus judges with mu-402's JUDGE-claims.md unchanged
(copied here), arms mixed and shuffled; C = flags summed over the two judges. Pair: P vs R per conversation, two blind
judges with mu-402's JUDGE-pair.md unchanged. Each judge works in its own private folder. Blind recount before
reporting.

## mu-404 marks (does removing notebook facts from the 1B prompt cut made-up claims?)
- V404 (validity): R's log "mu404: facts" shows >= 40 context_facts calls that returned at least one fact.
  Otherwise INCONCLUSIVE (the panel did not put facts in front of the 1B).
- N1: C_R - C_F >= 10 and C_F <= 0.67 x C_R.
- N2: per conversation, R has more flags than F more often than fewer; exact one-sided sign test p <= 0.05.
- PASS = V404, N1, N2. Proved wrong: C_F >= C_R.
- PASS means: shown on dev chats that the notebook facts in the prompt drive made-up claims; the fix goes to how
  facts are given to the 1B (only facts the turn is about, with who-said-what), owned here; its format is agreed
  with Answering from memory (y1w's notebook-first injection) and Trustworthy notes before anything is built, so the
  build keeps one fact-injection format. The claims rubric already flags "gets wrong what the user said", so a trade
  of made-up facts for wrong facts cannot pass N1 or M1.
  FAIL without proved wrong: facts are not shown to be the cause; next suspect luck/panel mix (0.2c's S1 was
  unseeded). Proved wrong: look at F1 (delivered history) next.

## mu-403 marks (does the fix cut made-up claims without hurting chat?)
- V403 (validity): for "ground", mu403's pick totals line in P's log shows the first sample changed in >= 15% of
  scored chat calls; for "sysline", >= a third of P's replies differ from R's (the line only reaches turns where
  chat 338 calls the 1B; later turns differ through the history). Otherwise INCONCLUSIVE.
- CHOSEN FIX (15:12 UTC, before sealing): "sysline". AUC 0.537 < 0.65 (AUC.md here).
- M1: C_R - C_P >= 10 and C_P <= 0.67 x C_R.
- M2: per conversation, R more flags than P more often than fewer; exact one-sided sign test p <= 0.05.
- M3 (no harm): over both pair judges, P losses - P wins <= 16 (of 160).
- M4 (S1's own bar): C_P <= C_T.
- PASS = V403, M1-M4. Proved wrong: C_P >= C_R.
- PASS: the fix is a candidate for 0.2d's chat path (joins only on its own verified PASS, then the combined no-harm
  gate); Everyday chat's ch-405 may add its score on top of it. FAIL on M3 only: it cuts claims but costs chat
  quality; next is a gentler version (for "ground": only reorder when the margin gap is large). FAIL on M1/M2: the
  fix is too weak; the other variant is next.

## Predictions (before the run)
- P404.1: mu-404 PASS, 45%.
- P404.2: C_R > C_T (with facts, the build makes up more than the plain 1B), 50%.
- P403.1: mu-403 PASS, 35%.
- P403.2: M3 fails (the fix makes chat blander), 30%.

## Budget
One rental through the Director from Ben's $2 for this thread ($0.36 spent on mu-402): cap $1.00 for this task.
Judges and recount: Opus agents in the thread, $0.
