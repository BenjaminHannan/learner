# 150c — Closed-class-subject guard (Muse)

Sibling of exp 150 (hedge/reporting/filler subject guard) and exp 150b
(clause-in-subject guard), stacked on loop150. One rule, one file, no
existing file edited.

## The bug

Director probe 03:40, confirmed on loop150 and loop138: idioms and chat
sentences with "'s" are stored as facts about non-entities. "What's done is
done." saves (What, done, done). "Today's weather is nice." saves (Today,
weather, nice). The notebook gains entities "What" and "Today" that no
question should ever resolve to.

## Parse path (Step 1)

The "'s" teaches go through the FakeEars possessive split:
scripts/fable_agent_loop.py:96 (the `_STATEMENT` regex takes left/right of
"is"), :102 (`_chain` splits the left span on `'s`), :134-147
(`FakeEars.hear` builds `teach` with name=parts[0], so "What's done" yields
name "What", relation "done"). The loop chain reaches it via
scripts/fable_loop90_agent.py:184-190 (FakeStage passes non-clarify actions
through once Bench73Stage misses at :140-146). Nothing validates the
subject span. Exp 150's guard
(scripts/fable_fix150_subjectguard.py:152-163) only screens
hedge/reporting openers and lowercase-lead shapes, so a capitalised
closed-class subject ("What", "Today") passes untouched.

## The one change

`scripts/fable_fix150c_closedclass.py` (`ClosedClass150CMixin`, stacked onto
loop150 in `scripts/fable_loop150c_agent.py` at both levels: ears `hear()`
and loop `_act()` just before the write): refuse -- reply "I didn't
understand that. Could you say it another way?", 0 writes -- any
teach/correct whose subject, after the loop's own normalisation
(whitespace-collapse plus the exp-129 trailing-punct strip), is WHOLLY a
closed-class word or phrase (sealed set: 8 wh-words, 24 pronouns, 9 deictic
time words, "here"/"there"; full list with reasons in PASSMARKS.md).

The reply is the loop's own total-miss message
(scripts/fable_agent_loop.py:148, scripts/fable_loop90_agent.py:291-292),
reused, nothing invented. The guard never rewrites; values, relation keys
and forget/ask/clarify paths are untouched.

## Why whole-subject, not substring

Capitalised names that merely contain a closed-class word must still teach,
so the screen compares the whole normalised subject: "Tomorrowland" is not
"tomorrow", "Nobody Knows" is not "nobody", "Who Framed Roger Rabbit" is
not "who", "It Follows" is not "it". Seventeen such titles/names are in the
sealed probe. Three brief-literal multi-word possessive titles ("Nobody
Knows's author is Ann" and kin) are already nowrite on loop150 via the
pre-existing FakeEars one-word-names rule, so the guard never sees them
(verified, documented, not probed).

## Known collision

The Beatles song "Yesterday" is exactly a closed-class word, so its two
bench teaches in item bench103-s2fresh-4hop-004 refuse by design. This is
the whole-subject rule working as specified -- case cannot distinguish the
song from the time word -- and the single predicted G1 move. Question for
Ben: if song/book titles that collide exactly with closed-class words
matter, that needs a name table, which is a separate experiment, not a
tweak to this guard.

## Verification

72-case sealed probe (48 closed-class refuses to 0 writes, 24 must-writes
to exact triples), exp-150 cases re-run identical, bench/marks123/sessions
identical except the one predicted item, every run under 25 minutes.
Results: artifacts/fable-subject150c-20260922/RESULTS.md.
