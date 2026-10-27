# Exp 230b-r pass marks — same 230b code, fresh blind panel, M1(c) re-defined (sealed before the run)

Diagnosis-driven follow-up to registered FAIL 230b (director ruling). In 230b, M1(c) counted
every YES item. The one miss (n230b-027 "My name's Sorrel, right?") never had "Yes" on 230.

NO CODE CHANGE. scripts/claude_loop230b_agent.py, its config, dev cases, the 230b marks driver
and the 230b scorer stay byte-identical to artifacts/claude-namecheck230b-20260922/SEAL.sha256.txt.
Their hashes are repeated in this folder's SEAL.

Run (once, after checking the panel seal from the repo root; `uptime` first):
  marks.py (230b driver, unchanged) --panel --panel-dir artifacts/claude-namecheckpanel230br-20260922
      artifacts/claude-namecheck230br-20260922/panel-rows.json
  (live 230 and live 230b each run once per item, in a fresh temp workdir)
  scripts/claude_namecheck230br_score.py <that rows file> artifacts/claude-namecheck230br-20260922/panel-score.json

M1 (fresh blind panel artifacts/claude-namecheckpanel230br-20260922). PASS iff all of:
 (a) false "Yes" = 0 (230b reply starts "Yes" when expect is NO, or no name is stored, or
     asked_name differs from the stored name);
 (b) every NO item whose base230 reply starts "Yes. Your name is " is now exactly
     "No. Your name is <stored>.";
 (c) NEW: every YES item with base_yes true (panel field; if it is missing, base230 reply starts
     "Yes") still starts "Yes" on 230b. Bar 100%. YES items with base_yes false are reported,
     not scored;
 (d) every UNCHANGED item is byte-identical to its base230 reply;
 (e) question writes = 0.
Other labels (e.g. NOT_TOLD) are reported, and they count toward (a) and (e).
Predicted moves: only NO items whose base is "Yes. Your name is ..." (ids unknown; blind).
Named risk: a NO phrasing that asked_name does not cover but 230 answers "Yes" would fail (a).

M2-M5 are reused from 230b (the code SHAs match): M2 dev 31/31, moves d01-d11; M3 0 moves on
sessions152/bench/marks123/rt136/rt143, GATE clean; M4 smoke identical to 230; M5 +0.035 ms.
Verdict PASS iff M1 (a)-(e) pass and the code SHAs still match at the end.
Self-test before the seal (not evidence): the scorer on 230b's old panel rows gives (c) 10/10
with 1 reported.
