# 168 — Self-grounded canned replies on loop138b (design)

## Problem

Director probe 07:31 on loop138b (fresh notebook, nothing taught):
"What city is the best?" and "Is Rome better than Milan?" answer
"I have no opinions. Oslo and Paris are only values you taught me.";
"What's your favourite colour?" answers "I do not have favourites. I can
only tell you Mira's colour is green, because you taught me that."
Neither fact was ever taught — false claims about the user's own
teaching. "Where did the web row come from?" on a notebook with no web
filings crashes the turn (IndexError, `self.web_filings[0]`).

Mechanism: loop138's `self_answer_from_live_state`
(`scripts/fable_loop138_agent.py`, lines 188–210) maps a self-intent to a
canonical panel question (`S105.CANONICAL[intent]`) and calls
`fable_self99`'s `answer_self`, whose canned replies
(`scripts/fable_self99.py`, lines 413–598) hard-code panel entities and
values. Step-1 census (file:line → class):

- names-fixed-fact: 569–571 favourite (Mira/colour/green), 587–589
  opinion (Oslo/Paris), 578–580 prediction (Mira), 584–586 Tom-told
  (Tom), 592–593 age (Mira), 437–443 who-taught (Oslo→Paris correction),
  481–490 are-you-sure (Mira/Paris).
- depends-on-state (reads live state; 3 crash when empty): 420–467
  counts/first/last (C3/C4 IndexError when nothing taught), 444–462
  web/sleep counts, 465–470 forgotten (IndexError when none), 471–516
  corrections/counters/mode, 517–553 unsure/besides-me, 554–557 web row
  (IndexError when none), 558–567 proposals/rules/mother-trail, 575–596
  yesterday/dreams, 437/481 resolve paths (KeyError when Mira unknown).
- plain (never touched): 449–451 belief rule, 543–547 capability sheet,
  572–574 feelings, 581–583 why, 590–591 my-name, 597–598 fallback.

## The one change

`scripts/fable_fix168_ground.py` wraps (never edits) the base answerer.
`grounded_self_answer` builds the same Self99 facade over the loop's live
state, calls the untouched `answer_self` on the same canonical question,
then `ground_reply` rewrites ONLY these exact strings, gated on intent:

- D1 favourite → kept iff active taught fact Mira/colour == green, else
  "I do not have favourites."
- D7 opinion → kept iff Oslo AND Paris are both active taught values,
  else "I have no opinions."
- D4 prediction → kept iff Mira is a known entity, else "I cannot
  predict."
- D6 Tom → kept iff Tom known, else "Nobody besides you has spoken to
  me. All N turns are yours."
- D9 age → "their"-version iff Mira unknown; live age iff taught; else
  base.
- C5 who-taught → NO_RECORD iff Mira/city unknown; grounded correction
  iff city ≠ Paris; "You did, in turn N." iff no Oslo→Paris correction;
  else base.
- C15 are-you-sure → plain iff Mira's city unknown; else base.
- C27/C11/C3/C4 empty → "I haven't filed anything from the web." /
  "I haven't forgotten anything you taught me." / "You haven't taught me
  anything yet." (crash net also maps any IndexError/KeyError to these
  or "I have no record of that, so I do not know it.").

`scripts/fable_loop168_agent.py` subclasses loop138b: `turn()` is
loop138's body verbatim with the single swapped call; `_act`/ears/mouth/
reasoner/sleeper/daemon-settle inherited; `Loop168Daemon` only rebuilds
with `build_agent168` and takes `idle_seconds`.

## Why grounding keeps everything else identical

The wrapper returns the base string untouched for every unlisted
intent/branch, so notebook answers, DECLINEs, counts, capability text,
and all state-read replies are byte-identical by construction. Moves can
only occur where the sealed base reply is one of the guarded strings on
an ungrounded notebook: predicted G2/G3 moves are enumerated in
PASSMARKS.md (rt81/p3-l2 opinion+prediction edges; redteam143 J8/K9/O5
misrouted opinion replies — verdicts unchanged since neither string
carries an abstain marker).

## What it does not do

No router change (misroutes still reach the answerer, now harmlessly
grounded); no notebook/teach/sleep change; age-when-taught answers from
the notebook rather than declining. Known edge: C5 "You did, in turn N."
without the correction clause when Paris was taught directly — honest
but less specific; accepted.

## Reproduce

Seal: `shasum -a 256 ... > SEAL.sha256.txt` (see RESULTS.md), ledger
P168.1–7 pre-run. Then probe, bench, marks123, regress drivers per
PASSMARKS.md (one heavy suite at a time, each < 25 min).
