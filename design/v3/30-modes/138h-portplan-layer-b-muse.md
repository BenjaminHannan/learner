# 138h port plan — merge layer B onto layer A (analysis only)

Base: loop138f (8 kept pieces; 155 inverted frames, 154 yes/no, 138c serve
removed). Layer A (scripts/fable_loop138g_agent.py, running now): 139e tail
guard, 137c hypo + 137d frames + 137e hearsay unify, 158c wh-city (adapted
target), 168 grounded-self turn; 157c and 160c LEFT OUT (no clean port).
Layer B ports the mixins below onto loop138g → loop138h. No seal, no
registered runs, no agents built here; all verdicts below are predictions
from the sealed pieces' own docs/results, not new claims.

## 0. Cross-cutting facts (checked in source, not assumed)

- The 139b→150→162→162b chain does NOT contain 155. Loop155
  (scripts/fable_loop155_agent.py:43) imports L150 and adds
  InvertedFrame155Mixin in its own ears only; loop162
  (scripts/fable_loop162_agent.py:39-46) imports F135+T162+L150 and is
  merely "in the style of" loop155. Porting 162b-chain mixins therefore
  cannot drag 155's inverted frames back. 155 stays OUT.
- 154b/154c import `SINGLE_VALUED_154` from scripts/fable_fix154_yesno.py
  (scripts/fable_fix154b_multival.py:34-36). That is an inert frozenset;
  importing it does NOT install YesNo154Mixin.hear (the removed yes/no
  answerer). 154c needs the table, never the removed behaviour.
- Every ears mixin below is cooperative (`super().hear()` delegation or
  post-process); composition is by MRO order, no file edits.

## 1–11. Per-piece ports

### (1) 162b plural possessives — LOW risk
- One change: `Plural162bMixin.hear`, scripts/fable_fix162b_plural.py:99
  (class :88). Claims plural "'s" teaches ("The Beatles' drummer is
  Ringo"), delegates all singulars to super.
- Base chain beyond 138f: 139b value guard + 150 SubjectGuard150 + 135
  officeholder guard + 162 TheName162 + 162b Plural. 138f has NONE of
  these (it has the different 150b clause guard). Port the MIXIN ONLY —
  do not port the chain (that would drag the 139b/150/135/162 teach
  surface, each with its own sealed behaviour).
- Collisions: hear only; none inside 138f/138g (no plural stage).
- Re-run: case file artifacts/fable-plural162b-20260922/cases162b.json vs
  frozen artifacts/fable-plural162b-20260922/probe162b-loop162b.json;
  plus redteam136-loop162b.json, redteam143-loop162b.json,
  sessions152-loop162b.json, marks162b-diff.json.
- Predict: plural teaches write; singular/'s/office/ask byte-identical to
  138g. Interaction: plural VALUES that are name-shaped hit the 171
  screen (clarify, no write) — predict before running.

### (2) 165 missing-apostrophe typos — LOW-MED risk
- One change: `Typo165Mixin.hear`, scripts/fable_fix165_typo.py:164
  (class :154). Rewrites "toms boss"→"tom's boss" only when the stripped
  name is a known alias and gates hold (:79-109), then delegates.
- Base chain beyond 138f: 162b (all of §1's chain). 138f has none of it.
  Port mixin only.
- Collisions: hear only. Must sit OUTSIDE Plural162b (sealed order in
  scripts/fable_loop165_agent.py:42: Typo165Mixin + Loop162bEars) so the
  rewrite re-enters the possessive path. No 138f/138g collision.
- Re-run: artifacts/fable-typo165-20260922/cases165.json vs frozen
  probe165-loop165.json; plus redteam136/143-loop165.json,
  sessions152-loop165.json, marks165-diff.json.
- Predict: typo teaches/asks behave as their apostrophe twins; unknown or
  ambiguous stripped names fall through untouched. Interaction: a typo
  rewrite landing on a 173/166-claimed shape delegates inward normally —
  no special casing needed.

### (3) 166c USER "me" + display case — LOW risk
- Two parts, both render/write-free: (a) `Me166Mixin.hear`,
  scripts/fable_fix166_me.py:196 (class :182) — "my <R> is <V>" teaches
  and "my <chain>" asks with name=USER_KEY ("USER", :49); (b) 166c
  display-case fix is NOT ears at all: `Loop166cAgentLoop._listening_tick`,
  scripts/fable_loop166c_agent.py:147 (helpers :58-141) — rewrites
  stored-lowercase displays to Title-case in replies only; notebook
  append-only, identity/matching/writes exactly loop166's.
- Base chain beyond 138f: 166 = 162b chain + Me166 (§1 chain + USER
  entity). 138f has none. Port Me166Mixin + the 166c _listening_tick
  override only. (166b capitalised-surface variant is superseded by 166c;
  do not port 166b.)
- Collisions: hear (cooperative, outside 162b per sealed
  scripts/fable_loop166_agent.py:49); _listening_tick has NO rival on
  138g (168 overrides turn, not _listening_tick). None with other B
  pieces.
- Re-run: artifacts/fable-me166c-20260922/cases166c.json vs frozen
  probe166c-loop166c.json + probe166c-B.json + probe166c-C.json; plus
  redteam136/143-loop166c.json, sessions152-loop166c.json,
  marks166c-diff.json.
- Predict: "my …" teaches write under USER; display-case affects reply
  text only from the Title-case turn on. Interaction: 173 name teaches
  also write under USER — same entity, different relations (name vs
  <R>), no overwrite (taught facts never overwritten by design).

### (4) 173 user's own name (173b PENDING — hold) — MED risk
- One change: `Name173Mixin.hear`, scripts/fable_fix173_username.py:324
  (class :315). Name statements/questions, stored-name-headed possessives,
  "Is X …?" checks. 173b (scripts/fable_fix173b_username.py: word-names
  count as names) is RUNNING, has no loop agent and no seal — port 173
  only; gate 173b re-entry on its seal.
- Base chain beyond 138f: 166 (§3 chain). Port mixin only.
- Collisions: hear outside Me166 (sealed scripts/fable_loop173_agent.py:52).
  PARTIAL-PORT WARNING: loop173 also overrides `_act` (:87),
  `_answer_namecheck` (:92) and `_listening_tick` (:108, name reply
  rewrite). Port hear + `_act`/`_answer_namecheck`; if _listening_tick is
  skipped, name replies render via base (capability loss, document it).
  173's `_act` vs 171's `_act`: 171 screens NAME relations — a 173 name
  teach with a description value ("My name is the boss") hits 171's
  clarify; put 171 INSIDE 173 is irrelevant (_act backstop runs
  innermost-first anyway) — just predict the case.
- Re-run: artifacts/fable-username173-20260922/cases173.json vs frozen
  probe173-t1.json + probe173-t1b.json; plus redteam136/143-loop173.json,
  sessions152-loop173.json, marks173-diff.json.
- Predict: name statements set USER name via teach (conflict →
  change-prompt, never silent supersede); "I'm <word-name>" stays
  conservative until 173b seals.

### (5) 167b verb facts (with 167) — MED risk
- Two mixins, sealed nested order (scripts/fable_loop167b_agent.py:46):
  `Verb167Mixin.hear` (scripts/fable_fix167_verb.py:212, class :202 —
  verb turn → possessive twin, delegated) inside
  `ValueScreen167bMixin.hear` (scripts/fable_fix167b_valuescreen.py:158,
  class :148 — name-shaped objects rebuilt clean, description/tail-only
  objects → loop167's own clarify, no write).
- Base chain beyond 138f: 162b chain (§1). Port both mixins only,
  preserving ValueScreen-OUTSIDE-Verb.
- Collisions: hear only; order vs 165/173/166: verb shapes ("Kwame lives
  in Accra") are disjoint from typo/name/me frames, so relative order
  among them only matters for double-claims — keep 167b>167 adjacent and
  outside 165 (typo rewrite of a verb subject, e.g. "kwames …", must
  re-enter through the verb stage: verb OUTSIDE typo is wrong; put
  165-outside-167? Sealed 165 delegates to super().hear(fixed) so the
  fixed text re-enters everything inside 165. If Verb is inside Typo, a
  typo'd verb subject gets fixed then verb-claimed. ORDER: 165 outside
  167b/167.) No 138f/138g collision (no verb stage).
- Re-run: artifacts/fable-verb167b-20260922/cases167b.json vs frozen
  probe167b-loop167b.json; plus redteam136-loop167b.json,
  redteam143-loop167b.json, sessions152-loop167b.json, marks167b-diff.json.
- Predict: verb twins write/answer as their possessive forms (hence flow
  through 154c multi logic and 171 screens — predict a verb teach on an
  allow-listed relation adds rather than prompts). Description-object
  verbs clarify with no write.

### (6) 160c two-hop corrections — CANNOT PORT (see §12)

### (7) 154c multi-valued allow-list — MED-HIGH risk
- Port as two new wrappers (Loop154cEars/Loop154cAgentLoop are full
  classes on the 138b lineage, not bare mixins): (a) ears pre-scan =
  scripts/fable_loop154c_agent.py:85 hear (correct-not / forget-one on
  MULTI_VALUED_154C allow-list,
  scripts/fable_fix154c_allowlist.py:37-60, else fall through to
  L138b-hear byte-identical); (b) `_act` router = :131 (multi-teach add,
  correct-multi, forget-one, allow-listed ask listing) with L138b-direct
  calls adapted to cooperative super() so the 138g chain (doubt/150b)
  stays in the path.
- Base chain beyond 138f: 154b handlers (which 154c inherits verbatim)
  + allow-list gate. 138f has neither; it also lacks 154b's assumed
  150-subject/139b-value screens — but 154c's hear re-checks
  V139b+S150 screens inline (:95-100), so the port is self-contained
  given read-only imports. Needs ONLY the SINGLE_VALUED_154 table (§0),
  never the removed 154 mixin.
- Collisions: hear pre-scan must sit OUTSIDE the 138g tail guard (claims
  correct-not shapes first); _act outside Tail139e (multi-add appends
  "(I also have …)" after 139e value screening — order: 139e clarifies
  bad values before multi-add sees them). No method rival in other B
  pieces (172 is a post-process outside 154c, §8).
- Re-run: artifacts/fable-multival154c-20260922/probe154c_cases.jsonl vs
  frozen work-probe154c/ + probe154c/ dirs, trigger_scan154c.json,
  bench154c_diff.json, marks154c.
- Predict: re-teach on allow-listed relations ADDS (no change-prompt);
  deny-listed relations (boss/capital/…) keep 138g change-prompt
  byte-identical; correct-not/forget-one work only on allow-list.

### (8) 172b copula re-teach asks — MED risk, gated on seal + §7
- One change: `downgrade172` + `Loop172Ears.hear`,
  scripts/fable_loop172_agent.py:86-119 (class :103; `_act` :129 is an
  explicit passthrough). Copula/verb-shape re-teaches on non-allow keys
  without an explicit correction prefix downgrade to the possessive
  change-prompt path; allow-listed + explicit corrections byte-identical
  to 154c. 172b is the v3 case set built on this (RUNNING — gate on seal;
  fall back to the sealed 172-old behaviour if v3 unsealed).
- Base chain beyond 138f: 154c (§7). Port as ears post-process OUTSIDE
  the 154c port (sealed: Loop172Ears extends Loop154cEars).
- Collisions: hear only; none with 138f/138g or other B pieces (disjoint
  trigger: non-allow copula re-teach).
- Re-run: artifacts/fable-copula172b-20260922/probe172b_t1_cases.jsonl,
  probe172b_t1b_cases.jsonl, probe172b_t1c_cases.jsonl vs frozen
  work-t1/, work-t1b/, work-t1c/ + bench172b_*_summary.json,
  g2-compare.json, marks172b.
- Predict: "X is Y's <non-allow-R>" re-teach → change-prompt wording
  identical to possessive path; allow-listed copula re-teach adds (154c).

### (9) 170 speed index — LOW behaviour risk, process-global
- One change: `install_index170()`,
  scripts/fable_fix170_compose.py:622 (called once at
  scripts/fable_loop170_agent.py:38-40) — rebinds scanning leaves
  process-locally (L90 triples, B92/B73 mentions, WM149 spans, Q132,
  L113, L148b screen). No ears/_act/turn override (Loop170Ears/Loop are
  138d subclasses, :48-54). Sealed claim is byte-identity + latency only.
- Base chain beyond 138f: none behavioural (138d-based; 138f IS 138d
  minus three pieces — the index leaves exist on both). Install after all
  imports, last, once.
- Collisions: none (no method overridden; module-attribute rebind only).
- Re-run: artifacts/fable-speed170-20260922/cases-s1-asks.json,
  cases-s2-fresh.json (+ cases-s2-15k.json if the 15k scope ruling lifts —
  it is OUT of scope per 138f doc) vs frozen s1/, s2/, s1.log, s2.log.
- Predict: byte-identical replies, lower per-turn scan cost. Interaction:
  none predicted with any B mixin (leaves only).

### (10) 171 name-shaped values — LOW-MED risk
- One change: `NameVal171Mixin` (hear :179 + `_act` :183),
  scripts/fable_fix171_nameval.py:170. `guard_actions` post-process
  (super-first) + loop-level re-check before write. Fires ONLY on
  NAME_KEYS relations with description values (first word in WORDS() /
  determiner / place-time adverb, :117-127) → sealed clarify (:129-136).
- Base chain beyond 138f: none (138d-based standalone mixin). Port as-is.
- Collisions: _act rival is 154c's _act — order 171 INSIDE 154c (171
  closest to 138g): 154c multi-add output re-passes 171's screen on the
  way out? _act MRO runs outermost-first: 154c._act handles multi keys
  and calls super → 171._act screens NAME_KEYS (disjoint key sets:
  MULTI_VALUED_154C vs NAME_KEYS — verify disjoint at port time; any
  overlap is a predict-first case). 171 hear-guard + _act backstop also
  cover outer mixins' self-built teaches (162b/166/173 build actions
  directly, bypassing 171's hear — the _act backstop catches them).
- Re-run: artifacts/fable-nameval171-20260922/cases171.json vs frozen
  probe171.json + f1-loop171.json; plus redteam136/143-loop171.json,
  sessions152-loop171.json, marks171, junk171-suites.json,
  probe139b-loop171.json, probe150-loop171.json.
- Predict: description values on name relations clarify, no write;
  everything else untouched. Interaction: 173 name teaches with
  description values clarify (see §4).

### (11) 171b — HOLD unless sealed
- `NameVal171BMixin` (hear :136 + `_act` :140),
  scripts/fable_fix171b_nameval.py:127 (extends 171 with title-case
  nameform check). RUNNING. Port stacked OUTSIDE 171 iff its PASSMARKS
  seal lands; else port 171 only.
- Re-run (if sealed): artifacts/fable-nameval171b-20260922/cases171b.json
  vs frozen probe171b.json + probe171b_T1.json.

## 12. Proposed MRO for loop138h (outer → inner)

Ears: ValueScreen167b > Verb167 > Typo165 > Name173 > Me166 > Plural162b >
Copula172-downgrade > Multival154c > NameVal171b? > NameVal171 >
Loop138gEars (Frame137g > WhCity158c > Tail139e > Loop138fEars…).
Why: preserves every sealed relative order (167b>167 per loop167b:46;
165>162b per loop165:42; 173>166 per loop173:52; Me166>162b per
loop166:49; 172>154c per loop172:103; 171 innermost-B so delegation twins
pass its hear screen, with its _act backstop covering self-built outer
actions). Loop _act: 171b? > 171 > 154c(+172 passthrough) > Tail139e(A) >
Doubt146b > Subject150B > 138b. _listening_tick: 166c display-case only.
turn: 168 (layer A) only — no rival. Reasoner/notebook/sleep/daemon:
138g unchanged. 170's install_index170() called once after imports.

## 13. Cannot be ported cleanly

- 160c (TwoHop160cMixin._act, scripts/fable_fix160c_twohp.py:152):
  resolves only against `_chain160c` written by its own _listening_tick
  AND conceptually against 160b's `_last_stated160b` bare-correction
  memory (scripts/fable_fix160b_laststated.py:131-160). 138f/138g have no
  160/160b machinery (no bare_correct tag, no last-stated memory) — the
  interceptor has nothing to intercept. Same ruling as layer A: porting
  alone is a no-op; porting 160+160b+160c drags the whole bare-correction
  feature (unrelated base-chain piece with its own reply-text widening).
  OUT for 138h; re-formulate as a 138h-native bare-correction experiment.
- 173b, 171b, 172b deltas: hold for seals (port their bases: 173, 171,
  172-on-154c). 173 loop _listening_tick name-reply rewrite: port
  hear+_act first; render parity is optional polish, not correctness.

## 14. Run order (each wave < 30 min, Mac CPU, temp dirs only)

W1 probes 162b+165+166c (tiny) → W2 167b → W3 171(+171b if sealed) →
W4 154c T1b/T1c → W5 172b T1/T1b/T1c (needs W4 green) → W6 173 T1/T1b →
W7 170 S1 then S2 (split; 15k excluded per scope) → W8 full suites last
(marks123, redteam136/143, sessions152, bench121). Gate rule: a wave that
moves any frozen expectation stops the line — file the deviation, do not
re-run into a pass. Ledger predictions P138h.<n> appended before each
wave; every seed/case reported, never averaged.

What it means: layer B can start stacking the moment 138g lands, with
orders, gates and re-run lists fixed in advance.
What it does not mean: none of the above is verified on the merged stack
— every prediction here must still pass its sealed re-run on loop138h.
