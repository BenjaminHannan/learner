# Chat weak spots, exp 260 base (2026-09-23)

Measurement only. 12 fresh dialogs (90 turns, fictional names), each run on a
fresh daemon loaded exactly as `scripts/claude_openers260_run.py` does
(`M.load_agent("scripts/claude_loop260_agent.py")`, config
`artifacts/claude-openers260-20260922/loop260-config.json`, `M.make_daemon`,
turns via `d.process_file`, triples via
`fable_loop90_agent.notebook_triples` before/after each turn). Raw rows plus
one operator mark per turn live in `dialogs.json`. No code was changed; these
are leads for later sealed experiments, not fixes.

## Counts per mark per theme (integers; rows sum to 90 turns)

| theme (dialog) | turns | OK | WRONG SAVE | MISSED SAVE | WRONG ANSWER | UNTRUE REPLY | BAD ENGLISH | CRASH |
|---|---|---|---|---|---|---|---|---|
| 1 teach then ask back (t01) | 8 | 7 | 0 | 0 | 1 | 0 | 0 | 0 |
| 2 two-hop (t02) | 8 | 5 | 0 | 1 | 2 | 0 | 0 | 0 |
| 3 backwards (t03) | 8 | 8 | 0 | 0 | 0 | 0 | 0 | 0 |
| 4 corrections (t04) | 8 | 4 | 0 | 2 | 1 | 0 | 1 | 0 |
| 5 forgetting (t05) | 8 | 3 | 0 | 1 | 4 | 0 | 0 | 0 |
| 6 never taught (t06) | 7 | 6 | 0 | 0 | 1 | 0 | 0 | 0 |
| 7 small talk (t07) | 6 | 5 | 0 | 0 | 1 | 0 | 0 | 0 |
| 8 about itself (t08) | 6 | 4 | 0 | 0 | 1 | 1 | 0 | 0 |
| 9 casual typing (t09) | 7 | 0 | 0 | 3 | 4 | 0 | 0 | 0 |
| 10 long/compound (t10) | 8 | 3 | 0 | 3 | 2 | 0 | 0 | 0 |
| 11 tricky meaning (t11) | 9 | 3 | 0 | 2 | 4 | 0 | 0 | 0 |
| 12 restart (t12) | 7 | 4 | 0 | 1 | 1 | 0 | 1 | 0 |
| TOTAL | 90 | 52 | 0 | 13 | 22 | 1 | 2 | 0 |

Note: t07-t0 "hey whats up" is marked WRONG ANSWER (casual greeting treated
as an unparseable question); the table above keeps that mark under
WRONG ANSWER. Zero crashes and zero wrong saves in all 90 turns.

## 10 clearest failures, ranked by surprise

1. t08-t1 (UNTRUE REPLY). Turn: "What can you do?" Reply: "I can: save what
   you teach me in my notebook; answer questions from my notes, following one
   or two steps; correct a fact or forget one when you ask; say I do not know
   instead of guessing; tell you where each fact came from; hold web text in
   quarantine without believing it." The rows disprove the boast: two-step
   questions fail (t02-t3) and forget commands fail (t05-t2, t05-t5).
2. t02-t3 (WRONG ANSWER). Turn: "Where does Ana's boss live?" Reply: "I
   didn't understand that question — could you say it another way?" Both
   links were stored verbatim two turns earlier (Ana/boss/Tobin,
   Tobin/city/Lima), yet the two-hop question is declined as unparseable.
3. t04-t5 (BAD ENGLISH). Turn: "What is Ana's cat called?" Reply: "I don't
   know Ana's cat called." The sentence is malformed, and it claims ignorance
   while Ana/cat/Moss is stored. Same template recurs at t12-t4 ("I don't
   know Rosa's dog called." with Rosa/dog/Pip stored), so it is systematic.
4. t05-t2 (WRONG ANSWER). Turn: "Forget where Ana lives." Reply: "I don't
   know anyone called where Ana." The forget command is parsed as a person
   lookup; nothing is removed, and Ana/city/Quito is still answered at t05-t3.
   Sibling at t05-t5: "Forget everything about Ana." -> "I don't know anyone
   called everything about."
5. t09-t1 (WRONG ANSWER). Turn: "whats anas city" Reply: "I couldn't save
   that as a fact. I don't know that shape yet. Could you say it another way,
   like "Kim's boss is Lee."" A question is answered with a save-error; the
   missing apostrophe flips question handling into save handling. All 7
   casual-typing turns fail (0 OK).
6. t04-t4 (MISSED SAVE). Turn: "Ana's cat is Fig, not Moss." Reply: "I can
   take one fact at a time — could you split that?" The "X, not Y" correction
   shape is refused, so stale Moss survives; the next turn then claims
   ignorance of the cat (see #3).
7. t11-t4 (WRONG ANSWER). Turn: "Ana lives in Quito, doesn't she" Reply: "Did
   you mean "Quito, doesn't"? Please say it again without the extra words."
   A tag-check without "?" is misparsed and the user is told to drop words.
8. t01-t7 (WRONG ANSWER). Turn: "Thanks, that's all!" Reply: "I didn't
   understand that well enough to save it — could you say it another way?" A
   closing pleasantry is read as a fact that failed to save (bare "Thanks!"
   and "cool thanks!" elsewhere get "You're welcome!").
9. t07-t0 (WRONG ANSWER). Turn: "hey whats up" Reply: "I didn't understand
   that question — could you say it another way?" The most ordinary greeting
   in the set is treated as a broken question.
10. t10-t0 (MISSED SAVE). Turn: "My name is Dawn and I live in Leeds." Reply:
    "I couldn't save that as a fact. I don't know that shape yet. Could you
    say it another way, like "Kim's boss is Lee."" Two facts joined by "and"
    store nothing at all, so the next two turns ("What is my name?", "Where do
    I live?") both miss.

## 5 things that work well

1. Plain teach-then-ask-back is near perfect (t01: 7/8; every save exact,
   every ask-back answered from store). The core loop is solid for clean
   single-fact turns.
2. Backwards questions are flawless (t03: 8/8), including reverse lookup
   ("Whose boss is Tobin?" -> "Ana's boss is Tobin.") and a two-answer
   listing ("Who lives in Lima?" -> "Ana's city is Lima. Marco's city is
   Lima.").
3. Plain "No,..." corrections replace cleanly (t04-t1: "No, Ana lives in
   Lima." -> "Updated: Ana's city is Lima (it was Quito)."), and opener
   stripping works ("Okay so Ana lives in Lima." saved exactly).
4. Honest ignorance instead of hallucination: four unknown-Zara questions get
   "I don't know anyone called Zara." (t06), and the pretend scenario
   "Imagine Ana lived in Rome." gets "OK, I'll treat that as pretend, so I
   won't save it." with nothing stored (t11-t0/t1).
5. Memory survives a mid-dialog rebuild (t12: Rosa/city/Turin and
   Rosa/dog/Pip both present after the restart row and answered correctly),
   and across all 90 turns there are zero wrong saves and zero crashes: the
   notebook never banks a fact the user did not state.
