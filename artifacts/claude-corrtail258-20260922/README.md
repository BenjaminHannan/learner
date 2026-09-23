# Correction-tail panel 258 (TEST-ONLY)

TEST-ONLY. Do not read items, tune on them, or copy wordings from them. Builders read only through their sealed scorers.

Written blind by the panel writer on 2026-09-22 against the director's fixed schema (80 items, 8 families).
Base: scripts/claude_loop252b_agent.py with artifacts/claude-correct252b-20260922/loop252b-config.json.
Each dialog: fresh work dir, one session: setup turns, turn, followup.

Families (counts): that_denial 12, that_correction 12, pure_denial_that 10, other_tail_denial 10,
keep 8, question_tail 6, unstored_tail 6, control 16.

Base on this panel (base_right / wrong_value / false_claim / junk-write items):
- that_denial        0/12, 12, 4, 1
- that_correction    0/12, 12, 0, 0
- pure_denial_that   2/10,  7, 0, 1
- other_tail_denial  1/10,  9, 1, 0
- keep               8/8 (by construction), 0, 0, 0
- question_tail      6/6,   0, 0, 0
- unstored_tail      6/6,   0, 0, 0
- control           16/16,  0, 0, 0

Quotas: lowercase / first-person per cause family = 4/2, 3/3, 3/2, 3/2; apostrophe-less items 9;
that_correction 6 contextual + 6 explicit; wordings not taken from the spec examples per family:
10/12, 10/12, 9/10, 7/10, 8/8, 4/6, 6/6, 15/16; 11 relations.
Writer acceptance: all setup teaches saved exactly; stated_facts equal the base store; every contextual
setup reply states exactly one stored value (the disputed one); controls 16/16 right. Cause families not filtered.
No item was replaced. The base run was repeated and was byte-identical.

Files: panel.jsonl, base252b.jsonl, make_panel.py (items + self-checks), run_base.py (driver + spec scoring), SEAL.sha256.txt.
