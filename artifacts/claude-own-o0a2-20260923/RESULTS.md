# own-O0a2 RESULTS (registered run, once, 2026-09-23)

Verdict: PASS on the bar (Pown0a2.1), PASS on the zero-save check (Pown0a2.2).

Question: does the ONE diagnosis-driven change (v1: plurals/possessives of
the relation name/alias, plus each relation's own teach-template fixed
words, count as a relation cue) lift oracle coverage from the registered
FAIL of own-O0a (184/272 = 67.6%, bar 85%) over the bar, on 300 FRESH turns
(the old 300 found the diagnosis, so they cannot test the fix)?

## Marks table (integer counts, ACD = ASSERT/CORRECT/DENY gold facts)

| Mark | Rule | WE | Writable / ACD | % | Bar | Result |
|---|---|---|---|---|---|---|
| Pown0a2.1 | v1 | not allowed | 252 / 281 | 89.7 | >= 85% | PASS |
| Pown0a2.1 | v1 | allowed | 262 / 281 | 93.2 | report | — |
| Pown0a2.2 | v0 | not allowed | 0 / 114 nosave | — | = 0 | PASS |
| Pown0a2.2 | v0 | allowed | 0 / 114 nosave | — | = 0 | PASS |
| Pown0a2.2 | v1 | not allowed | 0 / 114 nosave | — | = 0 | PASS |
| Pown0a2.2 | v1 | allowed | 0 / 114 nosave | — | = 0 | PASS |
| Pown0a2.2 | licensed | not allowed | 0 / 114 nosave | — | = 0 | PASS |
| Pown0a2.2 | licensed | allowed | 0 / 114 nosave | — | = 0 | PASS |
| Pown0a2.3 | v0 | not allowed | 92 / 281 | 32.7 | report | — |
| Pown0a2.3 | v0 | allowed | 98 / 281 | 34.9 | report | — |
| Pown0a2.3 | licensed | not allowed | 259 / 281 | 92.2 | report | — |
| Pown0a2.3 | licensed | allowed | 269 / 281 | 95.7 | report | — |

Prediction check: Pown0a2.1 predicted ~252/281 — exactly 252/281.
Pown0a2.2 predicted 0 in all 6 columns — 0 in all 6. Learned-licensed
predicted 259/269 — exactly 259/269. v0 predicted ~120/130, got 92/98
(report-only; see deviations D1).

Moves: v1 fixes 160 of the 189 v0 misses (WE not allowed), leaving 29.
Learned-licensed fixes 7 more (the residual no-cue class), leaving 22
(12 with WE allowed).

## Every non-writable ACD fact under v1, WE not allowed (29)

WE-owner (10; all writable with WE allowed):
o0a2-s157 "Our dog is Pip." (WE,dog,Pip); o0a2-s158 "Our cat is Moss."
(WE,cat,Moss); o0a2-s159 "Our cousins are Dara and Kito." x2 (WE,cousin,.);
o0a2-s160 "Our hometown is Essel." (WE,hometown,Essel); o0a2-s161 "Our dogs
are Pip and Zib." x2 (WE,dog,.); o0a2-s162 "Our mom is Lena." (WE,mother,
Lena); o0a2-m022 "Our hometown is Essel. Where are you from?"
(WE,hometown,Essel,ASSERT); o0a2-m029 "Our dog is Pip. Should we get a cat?"
(WE,dog,Pip,ASSERT).

typo (5; value not a literal span, needs asking — by design):
o0a2-s163 "Mira's dog is Pipp." (Mira,dog,Pip); o0a2-s164 "My mom is Lenn."
(ME,mother,Lena); o0a2-s165 "Tal works at Halvvo." (Tal,employer,Halvo);
o0a2-s166 "Ada lives in Linna." (Ada,city,Lina); o0a2-s167 "Bo's sister is
Leea." (Bo,sister,Lea).

relation-OTHER (5; never writable — by design): o0a2-s168 "Mira's aura is
blue." (Mira,OTHER:aura,blue); o0a2-s169 "My blicket is red."
(ME,OTHER:blicket,red); o0a2-s170 "Tal's zog is fast." (Tal,OTHER:zog,fast);
o0a2-s171 "Ada's mentor-spirit is Nib." (Ada,OTHER:mentor-spirit,Nib);
o0a2-s172 "Oren's gloof is heavy." (Oren,OTHER:gloof,heavy).

no-relation-cue (7; the residual class even v1 cannot cover):
o0a2-s173 "Pip is Mira's." (Mira,dog,Pip); o0a2-s174 "Mira's Pip won the
prize." (Mira,dog,Pip); o0a2-s175 "Give Pip a treat, Mira's little star."
(Mira,dog,Pip); o0a2-s178 "Sef is living in Rook." (Sef,city,Rook —
"living in" is not the template's "lives in"); o0a2-s179 "Tal works hard at
Halvo." (Tal,employer,Halvo — "works ... at" not contiguous); o0a2-s180 "My
children are Sora and Tino." x2 (ME,child,. — "children" is not child+s/es).

owner-not-span (2; pronoun with the name only in the previous reply):
o0a2-s176 "He lives in Rook." (Bo,city,Rook; prev "Bo is looking for a
flat."); o0a2-s177 "She works at Halvo." (Ada,employer,Halvo; prev "Ada
needs a job.").

## Deviations

- D1: v0 ceiling predicted ~120/281 (WE not allowed), measured 92/281
  (32.7%). Reason: the fresh dev set is denser in plural/verb wordings than
  own-O0a's (by design — it must contain the cases v1 claims to fix), so v0
  misses more here (167 no-cue of 281) than on O0a's set (59 of 272).
  Report-only mark; no bar touched, no re-run, no post-seal change.
- D2: none other. One run only. Seals re-verified after the run
  (SEAL.sha256.txt + SEAL-data.sha256.txt: all 4 files OK). No TEST-ONLY
  panel opened. No other agent's folder opened. Fictional names only.
  v0 column computed by importing scripts/claude_own_o0a_compiler.py
  read-only (same toks/has_span/cue expression, never executed, never edited).

## What it means (plain high-school English)

The single fix works on new sentences it never saw: letting plurals
("sisters", "kids", "bosses") and the table's own verb phrases
("lives in", "works at", "was born in") count as naming the relation moves
automatic coverage from 32.7% to 89.7% on fresh turns, clearing the 85% bar
that v0 failed. Nothing that should ask instead got auto-saved: all 114
question/check/suppose/plan/reported facts stayed non-writable under every
rule, and typos, unknown relations and pronouns still need asking.

## What it doesn't mean

It does not mean a trained reader reaches 89.7% — this is the ceiling with
a perfect reader (oracle gold fed in); a real ear still has to find the
spans and modes. It does not fix cue-less facts ("Pip is Mira's."),
inflections ("living in", "works hard at"), irregular plurals
("children"), typos, or pronouns — 7 such facts remain even under v1, and
only the backup design (no cue needed) covers those, at 92.2%/95.7%.
