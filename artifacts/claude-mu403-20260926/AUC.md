# mu-403 fix choice: does the 1B's own self-check spot made-up claims? (DEV, report only)

Written 2026-09-26 15:12 UTC. Script and bar: scripts/claude_mu403_auc.py (bar committed 01b448cfc before any margin was
computed). Data: mu-402's 804 chat-path replies (arms A and B, 402 each) with the two blind judges' flags
(artifacts/claude-mu402-20260926/judge). Margins: auc/margins402.jsonl (base MiniCPM5-1B on CPU in the cloud
container; logit "yes" minus logit "no" to "does the reply claim or assume something about the user that the user
did not write?"). Arm T was stopped after 11 replies (report only, not needed for the decision).

## Result: AUC 0.537 (bar 0.65) -> the fix is the system line
| set | AUC | flagged | unflagged |
|---|---|---|---|
| A + B, flagged by either judge (the decision) | 0.537 | 94 | 710 |
| A + B, flagged by both judges | 0.511 | 70 | 710 |
| A only | 0.509 | 51 | 351 |
| B only | 0.570 | 43 | 359 |
| feelings turns | 0.450 | 37 | 153 |
| advice turns | 0.474 | 27 | 183 |
| followup turns | 0.699 | 15 | 105 |

- Shown (these 804 replies): the 1B's yes/no self-check barely separates replies the judges flagged from the rest
  (0.54, where 0.5 is chance), and on feelings and advice turns, where most made-up claims are, it is at or below
  chance. A picker using it would mostly shuffle samples at random.
- So mu-403's arm P uses the fallback fixed in advance: one sentence added to chat 338's system prompt
  (claude_mu403.VARIANT_LINE): "Only say things about the user that they actually told you in this chat. Do not guess
  their feelings, plans, situation or past; if something matters and you don't know it, ask."
- The shared picker (scripts/claude_pick403.py) stays: it only reorders by whatever score a thread brings, and
  Creative answers in chat's k1c score is unaffected by this result. Everyday chat's ch-405 can no longer stack on a
  grounding score; it would stand alone.
- Untested: a bigger or trained checker (for example a small head trained on judged replies) might have signal; that
  would be its own test with its own training data (the model's own graded drafts, never Claude-written text).
