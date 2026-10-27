# 146 — Refused-correction doubt (Muse)

## Problem

Two sightings, one class. bench132-4hop-022: the edit teach "Charles M. Schulz is
famous for The Protocols of the Elders of Zion" is refused ("could you split that?"),
the old fact (Schulz, notable_work) = Peanuts stands, and the 4-hop question answers
Washington, D.C. — stale and confident. Exp 139: the value-span guard refused
"... United Kingdom of Great Britain and Ireland" teaches and 11 bench chains went
correct -> wrong: some via the old citizenship (full stale walk), most via a
truncated question frame (the N-hop composer walks the post-edit chain, stops where
the refused hop is missing, and answers the refusal subject itself).

## Design: one mixin, no edits

`Doubt146Mixin` stacks outermost on loop129b (loop146) and on loop139 (loop146b),
at ears-hear and loop-_act/_ask levels. No existing file is edited.

**Recording.** hear() pre-parses with the existing parsers only
(B73.hear_teach_template, B92.hear_teach92, FakeEars teach/correct — the chain's own
teach detectors, same preprocessing order as Loop121Ears: correction prefix, forget
shapes, qualifier strip; "?" turns skipped). After super().hear(), a clarify outcome
with a parsed triple whose subject resolves (OK/AMBIGUOUS) records (subject,
relation). Chit-chat/opinions ("Mira is great", "I think Peanuts is great") never
parse, so never doubt. _act() does the same for act-level clarify refusals using the
action's own (name, relation), and clears the doubt on successful writes (Saved: new
value, or "I already have that." repeat). CONFLICT (kind write, not clarify) neither
records nor clears; forget is untouched.

**Answering.** hear() screens ask actions with _walk_hit(): mirror the reasoner walk
over entity IDs; fire on traversal of a doubted (subject, relation). Truncation rule:
a walk ending at a doubted-subject sink also fires when the doubted relation is
question-mentioned (existing B73/B92 cue lists) or the question mentions relations
beyond the walked frame (the intended walk continues past the refusal gap — covers
paraphrases like "calls home" that compose full frames on complete chains but leave
no cue). Reply: "You told me something new about S's R that I could not store. I
can take one fact at a time — could you say it again as one fact?" (scorer-abstain
phrase, underscore-free for q4). _ask() repeats the traversal check for non-ears
asks (pending picks).

**Storage.** `DoubtStore146`: doubts146.json in the daemon dir (next to state.json
and notebook/), atomic temp-write + fsync + replace, stale temps swept, loaded per
build so kill-9/restart preserves doubts. Never weights; never touches facts.

## Evidence

D1 11/11 abstain, 0 worse; D2 exactly the 2 predicted wrong->abstain moves, 0 new
wrong/lost; D3 31/32 (one sealed expectation mis-authored: an opinion correctly
clarifies); D4 all suites identical except 4 hearsay-veto moves (see below).

## Boundaries and the D4 lesson

The sealed rule records on F1-hearsay refusals (quoted contradictions parse with
known subjects), giving hearsay a veto over standing answers (p2 A2/A6/A8, rt110
T4). The loop screens hearsay before teach parsing; a follow-up one-change should
exempt it. CONFLICT/forget/sleep paths are deliberately out of scope.

## Reuse and plugs

Parsers, cue lists, notebook resolve/current/triples, scorer contract, bench and
marks123 harnesses are all imported read-only. The mixin composes with sibling
mixins (139-guard inside, doubt outside). Adapter note: none needed — replies are
plain clarifies through FakeMouth.

## Questions for Ben

None. Defaults taken: hearsay follows the sealed literal rule (recorded; caused the
D4 FAIL, diagnosed); forget does not clear doubts; ambiguous subjects may record
(their questions already abstain).
