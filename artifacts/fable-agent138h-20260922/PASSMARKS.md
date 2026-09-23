# Exp 138h PASSMARKS — merge layer B part 1 (5 text fixes onto loop138g), sealed before run

Agent: `scripts/fable_loop138h_agent.py` (Loop138hEars / Loop138hAgentLoop /
Loop138hDaemon, build_agent138h, DEFAULT_CONFIG138H). Subclasses the frozen
loop138g stack; every rule body imported read-only, no existing file edited.
Ears outer→inner: Typo165 > ValueScreen167b > Verb167 > Name173 > Me166 >
Plural162b > Loop138gEars (preserves every sealed relative order; Typo
outermost so fixed text re-enters). Loop _act: 173 namecheck > 138g tail
chain. _listening_tick: 173/166 reply rendering, then 166c display pass.
turn(): 138g 168 shape + a raw-USER backstop (this file only: scrub residual
raw USER key unless the turn itself mentions USER literally — pilot-found
A22 leak fix; O13 literal-USER control stays raw).
Config: `artifacts/fable-agent138h-20260922/loop138h-config.json`.
Design: `design/v3/30-modes/138h-merge-layer-b1-muse.md`.
Drivers (new, sealed): `scripts/fable_fix138h_m1pieces.py` (M1),
`scripts/fable_fix138h_m2.py` (M2), `scripts/fable_fix138h_suites.py`
(M4+G1+G3). G2 runner: stock `scripts/fable_marks123_all.py` (new args only).
173b NOT ported: `artifacts/fable-username173b-20260922/SEAL.sha256.txt`
exists but there is NO RESULTS.md saying PASS, so per the brief the 173
base is ported. 166b NOT ported (superseded by 166c). 155 stays OUT
(driver prints MRO + module scan). Ledger P138h.1–P138h.8 appended pre-run.
Sealed files hashed to SEAL.sha256.txt: this file, the agent file, the
config, the 3 drivers.

Environment: Mac CPU only, offline, `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`,
`uv run --offline --no-project --python 3.12 --with torch --with numpy python -B …`.
Every seed/case reported, never averaged. A registered FAIL stays FAIL with
one diagnosis note. No rule changes after the seal. Open pilots (same
drivers, same paths; three-way per-turn drives vs own-agent live and vs
loop138g live) enumerated every move below; the registered runs re-run
everything after the seal. Heavy suites run one at a time.

Shared reply texts: R-CLARIFY = "I do not know that from what you taught me.
I have no record of it, so I will not guess. I didn't understand that, I
don't know — could you say it another way?"; HEARSAY = "Do you know that
yourself, or did you hear it somewhere? I only save facts you tell me
directly."; HYPO = "OK, I'll treat that as pretend, so I won't save it.";
SELF-NAME = "You never told me your name, so I do not know it."

## In / out of this build

IN (5, mixin only, never the base chain): 162b Plural162bMixin.hear;
165 Typo165Mixin.hear (outside 162b and outside 167b/167); 166 Me166Mixin.hear
+ 166c display-case _listening_tick (helpers read-only) + the underlying
me166 reply rendering (else USER leaks raw); 173 Name173Mixin.hear +
_act/_answer_namecheck + _listening_tick name rewrite (173, not 173b);
167 Verb167Mixin.hear with ValueScreen167bMixin.hear OUTSIDE it.
OUT: 173b delta (no PASS seal); 166b (superseded); 155 (no class, no module).

## Marks

- M1 (m1pieces driver; piece's own probe judge, base arm = own agent except
  166c-B/C where the base arm is loop166 per sealed design; frozen rows
  compared too): every unlisted case identical (verdict+reply+stored+asks).
  Listed interactions (pilot-verified per-turn: each turn is either
  own-agent-identical or 138g-identical; stored likewise; zero OTHER turns):
  - R1 mouth-render (Saved multiword labels render spaces, stored identical;
    162b rows verdict OK, 167b rows judge WRONG-REPLY on the case-exact
    underscore): 162b P16,P17,P18,P19,P20,P21,W19,W20,W21,W22,W23,W24,O05
    ("Saved: <owner>'s headquarters location|official language|chief
    executive officer is <V>."); 167b M16–M22,T03,T07,T11,T15 ("Saved: <X>'s
    place of birth is <V>.").
  - R2 unclaimed-clarify wording (R-CLARIFY, 0 writes; 165 G02/G04/G09/C04
    keep verdict OK since the mark is contained): 162b
    N01,N02,N05,N06,N09,N10,N11; 165 G01,G02(ask),G03(T1),G04(ask),G05(T1),
    G06(T1),G07(T2),G08,G09(ask),G10(T1),G11(T1),C03,C04(ask),C08,C12;
    167b D01–D16,N01–N10; 166c A03,A04,A05,A06,A07,A09,A10,O09,O10,O14,O15,O16;
    166c-B O05,O06; 166c-C E02(T1+ask),E05(ask),E06(ask),E07(T1: "I have no
    opinions." is 168-grounded, 138g-identical),E08(ask); 173-t1
    A03–A07,A09,A10,O09,O10,O14,O15,O16; 173-t1b L01,L04–L11,O05.
    165-G12 → HEARSAY (138g-identical).
  - R3 168-grounded self (138g-identical): 166c A01,A02,A08; 166c-B O01,O02;
    173-t1 A01,A02,A08; 173-t1b O01 → SELF-NAME. 173-t1b L02 → "I do not have
    feelings. I am plain software: a notebook, a lookup loop, and fixed
    rules."; L03 → "I have no opinions."
  - R4 138g-path saves (singular/multi-word shapes the 162 chain vetoes;
    138g-identical incl. stored): 162b N03 ("Saved: The Guardian's editor is
    Kath Viner.", [[The Guardian,editor,Kath Viner]]), N04 ("Saved: The
    Hobbit's birthplace is Oxford.", [[The Hobbit,birthplace,Oxford]]),
    N07 ("Saved: The Hobbit's uncle is Bilbo.", [[The Hobbit,uncle,Bilbo]]),
    N08 ("Saved: The Hobbit's captain is Aragorn.",
    [[The Hobbit,captain,Aragorn]]); 162b W04 MISSED (R-CLARIFY, no write:
    singular TheName shape with no 138g save); 166c O08 / 166c-B O10 /
    173-t1 O08 ("Saved: Mary Jane's mother is Rita.",
    [[Mary Jane,mother,Rita]]); 166c-C E03 (+ "Saved: Zib United's captain
    is Tom.", [[USER,team,zib],[Zib United,captain,Tom]]), E04 (+ "Saved:
    Dune Part Two's director is Ana.", [[USER,movie,dune],[Dune Part
    Two,director,Ana]]); chained "X of Y" asks behave as 138g (teaches all
    save, stored == piece): 162b C1-ask2 → "I don't know anyone called the
    spouse of The Hobbit."; C2-ask1 → "I don't know anyone called The
    Beatles' founder.", C2-ask2 → R-CLARIFY; C3-ask1 → "I don't know anyone
    called The Supremes' founder.", C3-ask2 → R-CLARIFY.
  - R5 entity-count-only (replies+stored+asks byte-identical to own agent;
    138h mints no value-entity where the 150 chain does; verdict NEW-ENTITY
    vs OK): 166c O03, 166c-B O07, 166c-C E01.
  - CAP-verify rows (166c-B C01–C12, 166c-C T01–T08): verdict OK with base
    arm loop166; Title-case display fires byte-identical to 166c.
  - 173 name rows (all S/R/P/U t1b rows; me rows everywhere): identical to
    loop173. O13 literal-USER control identical (raw key kept: turn mentions
    USER literally, scrub gate exempts).
- M2 (m2 driver): 139e clean (65/65, 0 wrong writes); 137e fail-set exactly
  {T1-O-01,T1-O-02,T1-O-03,T1-O-16,T1-O-17,T1b-E06} with 138g-identical
  reply+stored ("Saved: <lead> Kim's boss is Lee.", [[<lead> Kim,boss,Lee]]);
  158c fail-set exactly {O03,O04,O05,O06,O07,O08,O10} 138g-identical
  (O03/O04/O05/O07/O08 R-CLARIFY; O06 "I do not have favourites."; O10 "You
  did, in turn 6.") + O01 improvement ("Sue's city is Leeds.", 0 writes ==
  sealed reply158c, via the verb twin); 168 fail-set exactly {A10, B-ask
  "What is my name?" → "I don't know your name yet.", A22 → "I am unsure
  about: your name (never taught)."}; 138f pieces at bar except 156b-N11 →
  "I have no opinions." (sealed 138g exempt, 0 writes).
- M4 (suites driver): the 7 cases byte-identical (verdict+reply+stored) to
  loop138b (C124/C127/C129/C142/C10/C21/M3); per-case vs loop138g rows
  identical EXCEPT one predicted move: sessions152 S4-pets-identity turn 1
  ("my dog is biscuit") UNHELPFUL→OK ("Saved: your dog is biscuit.",
  +[[USER,dog,biscuit]]; session judge OK). rt136 136/6/3, cases150 57/57,
  f1 46/46, cases139b 101/101, rt143 0 moves (M3 identical), sessions
  166/14 (one move). 0 new WRONG / WRONG-WRITE / junk writes anywhere vs
  138b or 138g.
- G1 (suites driver `--only bench`): bench121 4 splits per-item vs sealed
  138g rows: 0 verdict moves, 0 new wrong (194/2/4, 198/2/0, 150/50/0,
  196/3/1).
- G2 (`scripts/fable_marks123_all.py --agent scripts/fable_loop138h_agent.py
  --config artifacts/fable-agent138h-20260922/loop138h-config.json --out
  artifacts/fable-agent138h-20260922/marks138h --workers 4`): every suite
  per-case vs sealed marks138g EXCEPT: rt81 O_user-02 observed-text move
  (verdict UNCLEAR kept: "I don't know your mother yet.") + O_user-03
  UNCLEAR→BUG ("Saved: your city is Lisbon.", +[[USER,city,Lisbon]],
  byte-identical to loop166 sealed); p3-l2 O_user-02 (reply text) +
  O_user-03 (saves; stale nowrite-label wrong_write flag; l2 sub-pass F,
  all other p3 sub-suites as 138g); rt110 P1+P3 OK→BUG (verb saves "Mira's
  city is Oslo." + answer; byte-identical to loop167 sealed); sleep SKIP
  reason names fable_loop138h_agent.py (verdict identical). p4 P4-09 nonpass
  kept; rt81 bug count 1 (O_user-03 only); p3 l5z1 FAIL kept; l6
  pass/correct/wrong kept (replied_before_kill timing-volatile, reported
  not predicted).
- G3 (suites driver `--only g3`, 5 pairs, fresh loop each, teach then ask):
  G3h-1a/b R-CLARIFY + [] ("drummer" outside the 162b inventory, same as
  loop162b); G3h-2a "Saved: Tom's boss is Lee." + [[Tom,boss,Lee]], G3h-2b
  "tom's boss is Lee." + same stored; G3h-3a "Saved: your sister is Ada." +
  [[USER,sister,Ada]], G3h-3b "Your sister is Ada." + same; G3h-4a
  SELF-NAME + [] ("Juno" is dictionary-word, not name-shaped — same as
  loop173), G3h-4b "I don't know your name yet." + []; G3h-5a "Saved:
  Kwame's city is Accra." + [[Kwame,city,Accra]], G3h-5b "Kwame's city is
  Accra." + same. 10/10.
- G4: every registered run < 1500 s wall-clock (pilot: m1 ~30 s, m2 ~17 s,
  junk/rt143/sessions small, bench ~60 s, g3 ~2 s, marks wave ~269 s).

## Predicted fault lines (part of the seal; FAILs stay FAIL)

- F1: any move beyond the enumerated sets (M1 classes R1–R5 + CAP rows;
  M2 6+7+1+3+1; M4 1; G1 0; G2 rt81 2 + p3-l2 2 + rt110 2 + sleep rename;
  G3 10/10).
- F2: any new WRONG / WRONG-WRITE / junk write vs loop138b on any suite
  (S4's [[USER,dog,biscuit]] and O_user-03's [[USER,city,Lisbon]] are sealed
  166-rule teaches, not wrong; P4-09-style clean stores likewise).
- F3: mailbox-race flakes (empty-read clarifies, lost teaches, l6
  kill-counters, rt110 daemon log races) under parallel-agent load:
  recorded, re-run once in the open, both reported.
- F4: any raw-USER leak (O13 must stay raw-138g-identical; A22 must render
  "your").
