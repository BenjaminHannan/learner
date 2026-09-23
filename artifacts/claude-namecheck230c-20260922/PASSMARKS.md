# Exp 230c pass marks — the name check fails closed (sealed before the registered runs)

Base: loop230b (scripts/claude_loop230b_agent.py, sealed in artifacts/claude-namecheck230b-20260922),
wrapped read-only. Diagnosis (230b-r FAIL, r230b-038): "Is it Wystane Borrick, my name?" kept 230's
"Yes. Your name is Wystane Morrick." because asked_name could not extract the name.

ONE CHANGE (scripts/claude_loop230c_agent.py): on a reply line that starts "Yes. Your name is ",
Yes/No is given only when asked_name extracted a name (230b's comparison, unchanged). If no name
was extracted AND the turn holds any word outside the closed list COMMON_WORDS (a possible name),
the line becomes "Your name is <stored>." (no prefix). Turns made only of common words (e.g.
"Do you remember my name?") keep 230b's reply. The pattern list is not widened. Only
"Yes. Your name is " lines are touched, so routing and relation yes/no are unchanged. Reply-only;
never writes. 228 guard: install_srcguard228() at import; SrcGuardMixin228 first in Loop230cDaemon.

Mac CPU, offline, OMP/MKL=1, fresh temp notebooks, one run at a time, `uptime` before each
registered run. Any change to a sealed file after the seal = FAIL.
Expected 230c reply per turn (scripts/claude_namecheck230c_marks.py expected()), from the live
230b reply on the same turns: a "Yes. Your name is " line loses "Yes. " iff asked_name is None and
may_name_something is True; otherwise byte-identical.

M1 blind panel artifacts/claude-namecheckpanel230c-20260922 (panel.jsonl 54 lines: id, family,
setup, question, expect, gold_name, note; base230b.jsonl: id, base_reply, base_setup_replies,
stored, base_yes). Schema is checked first by scripts/claude_namecheck230c_score.py load_panel. Any
missing or unexpected file, field, family, label, count or id -> SCHEMA-MISMATCH, exit 3, run VOID.
The panel seal is checked from the repo root. Run once:
`marks.py --panel <dir> <rows>`, then `score.py --panel <rows> <score>`. Each item runs live 230b
and live 230c from fresh temp notebooks (setup turns + question).
 - M1a: 0 replies starting "Yes" on NO, NOT_YES and NOT_TOLD items.
 - M1b: 0 replies starting "No" (regex ^No\b) on YES and NOT_NO items.
 - M1c: every NO item's reply is exactly "No. Your name is <stored>." (director bar 12/12, i.e.
   all NO items).
 - M1d: every YES item with base_yes true still starts "Yes". YES items with base_yes false are
   reported, not scored.
 - M1e: every UNCHANGED item is byte-identical to its base230b base_reply.
 - M1f: 0 writes on the question turn.
 Predicted moves: only items whose 230b reply is "Yes. Your name is …" on a turn with an
 unextracted possible name ("Is it X, my name?" shapes), which become "Your name is …".
 Ids are unknown (blind). Named risk: a NO item whose name 230b cannot extract gets
 "Your name is …", which fails M1c. Fail-closed turns it into a non-Yes, not a "No".
M2 dev (dev-cases.json, 22 cases, each with an exact wanted reply): 22/22, every turn follows
 expected(), notebooks identical to 230b, 0 question writes. Predicted moves by id: exactly
 e01 (Is it Wystane Borrick, my name?), e04 (Is it Wystane Morrick, my name?), e10 (Is my name
 Quenby or Ottilie?), e22 (Is it Quenby, my name?). e02 "My name is Wystane Borrick, right?" and
 e03 "Am I Wystane Borrick?" are unchanged. Relation yes/no e20/e21 are byte-identical.
M3 frozen suites: sessions152, bench, marks123 with --base-dir artifacts/claude-namecheck230b-20260922;
 rt136, rt143 with --base 138i, plus score.py --rt vs 230b's saved rt rows. PASS iff 0 new WRONG,
 WRONG-WRITE or junk, GATE clean, and every move predicted by id. Predicted moves: none.
M4 sleep smoke (seed 1, idle 30) identical to smoke230b.json except agent/config/label/seconds.
M5 median added time per dev question turn (230c - 230b) <= +5 ms.
Verdict PASS iff M1a-f and M2-M5 all pass.
Pilots (pre-seal, final code): M2 22/22, moves e01, e04, e10, e22; M3 0 moves on all five, 0 vs 230b
 rt rows, GATE clean; M4 identical; M5 -0.04 ms. Scorer self-tested on a fake panel (schema OK;
 an extra field gives exit 3). The real panel directory appeared before this seal and was NOT
 opened.
