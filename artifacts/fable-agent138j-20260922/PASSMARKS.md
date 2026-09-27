# PASSMARKS — Exp 138j: MERGE LAYER C onto loop138i (Muse)

Agent: `scripts/fable_loop138j_agent.py` (+ `scripts/fable_fix138j_*.py`
drivers, `scripts/fable_fix138j_comparem.py` compare helper). Config:
`artifacts/fable-agent138j-20260922/loop138j-config.json`. Base:
loop138i (no 155 — checked in its MRO). Port order (outside-in, per
`design/v3/30-modes/138j-merge-layer-c-muse.md`): turn: 189b repeat
check > 138g-body turn with the 187 gate on the notebook-missed path >
188 swap applied last; ears: 180b > 193 > About164b > Reverse190b >
Reverse190 > Negate154f > Replace154g > Loop138iEars; _act:
Replace154g + Negate154f outside the 138i chain; tick (outside-in):
180b display > 164b safety > CorrectReply192 > 138i chain. Loop155
stays OUT (MRO + module scan in every M1 run).

Director decision (one wording for every replacement): 192 answers
"Updated: Kim's boss is Lee (it was Sam)."; in 138j EVERY replacement
uses 192's template, including 154g's one-value replace ("Updated:
Omar's language is Farsi (it was Urdu).") and the confirmation after
the user names one value. 154g's 2+-value question stays as sealed.
Stored facts stay identical to 154g's own agent (verified per row:
state_ok + writes_ok on every 154g diff; pet-replace rows store exactly
154g-own's triples).

## M1 — each piece's own sealed case file on loop138j
Bar: verdict + reply + stored facts identical to that piece's own
agent, except the cross-piece classes below (all piloted pre-seal;
pilots in scratch138j-pilot/, final code). Reply-only classes move the
reply text only (stored [] both sides or identical triples);
stored-marked rows name the stored difference.
- 180b (42/44): X05 statement trap "mark my words." takes 188's
  fallback (reply-only). X11 "say toms boss is lee." say-echo renders
  canonical "Tom's boss is lee." (193 fixed the possessive inside the
  echo turn; 0 writes both).
- 193 (33/40): Q12 "What is the city of Kofis boss?" now answered
  "Kofi's boss's city is Accra." (193 x 174 of-chain; 138h could not).
  X02/X03/X04/X05/X10/X14 statement traps take 188's fallback
  (reply-only).
- 164b (49/50): D08 takes 188's fallback (reply-only).
- 189 (36/38): S19 "Who made you?" takes 187's maker reply (specific
  handler before generic paths); S20 "Say that again." echoes it
  (repeat follows the base turn).
- 189b (42/44): B25 "Who made you?" takes 187's maker reply; B26
  "Repeat that please." echoes it.
- 190 (63/70): C0b/C0c explicit "Actually,..." corrects take 192's
  Updated template (reply-only; stored identical). E1-E5 unknown-value
  reverse asks take 190b's whose-wording (the 190b piece, verified by
  its own file). C4 reply == live own-190 (sealed-expect order drift
  present on both sides, not a 138j move).
- 190b (45/46): S13 "Actually, Pip's coach is Soren." takes 192's
  Updated template (reply-only; stored identical).
- 187b (24/34): T01/T02 ("What is my name", "Who am I") take the
  173/166-lineage "I don't know your name yet."; T03 ("Who is my boss")
  takes "I don't know your boss yet." (187b was built on 138g; the
  138i base understands user asks now). U01-U07 statement traps take
  188's fallback (reply-only).
- 192 (38/40 + store): n18 "Mia's friend is Ann." multi-adds "Saved:
  Mia's friend is Ann. (I also have Zoe.)" (friend is multi-valued on
  the 138i base via 154e; 167e-own change-prompted) and n19 "yes" finds
  no pending question ("I wasn't waiting for an answer."). Stored:
  138j keeps [Zoe, Ann] per base multi semantics; 192-own keeps [Zoe]
  then replaces. Listed 154e-composition (not reply-only).
- 154f (86/90): n77 "Say Rana's language is not Tamil." and n88
  "Pretend Rana's boss is not Lee." take the layer-A pretend path
  (older base; 0 writes both). n80/n81 multi-hop negations take 188's
  fallback (reply-only; 154f owns single-hop only by design).
- 154g (76/91): 15 reply-only Updated rows (state_ok + writes_ok on all;
  stored == 154g-own): one-value replaces n2/n4/n6/n10/n13/n15/n18/n21;
  pending-answer confirmations n26/n29/n35/n40/n45/n48; n77 single-valued
  boss correction ("No, Eli's boss is Lee." → "Updated: Eli's boss is
  Lee (it was Sam).", 192 tick on the functional key).
- 188 (36/40): S03 "Kwame was born in Paris." now SAVES
  "Saved: Kwame's place of birth is Paris." (167d born→birthplace is
  understood now; stored [[Kwame,birthplace,Paris]]). Q01 "Where does
  Kim live?" takes the 167 verb-city unknown reply "I don't know
  anyone called Kim.". Q05 "Who is my sister?" takes "I don't know
  your sister yet." (166). H09 "What is my name?" takes "I don't know
  your name yet." (173).
- MRO check every M1 run: no 155 class, no fable_loop155 module.

## M2 — 138i's M1/M2/G3 cases on loop138j
Bar: identical to loop138i except the predicted moves below (piloted).
M2-M1 (138i M1 jobs, joined vs sealed m1-138i rows; inherited ids move
with the same got): 154d new n33 (188). 167d X01-X04/X07-X10 move to
188's fallback (X05/X06 stay question-fallback: 188 is
statement-shaped only). 167e n32 moves to 188's fallback. 171b new
I08/T1-C01 (192 Updated, stored identical). 172b-t1 new n26/n34
(192 Updated on yes-to-change; stored single replace verified).
172b-t1c new n3/n7/n11/n15/n19/n23 ("yes." → Updated) and
n50/n53/n56/n59/n62/n65 ("Actually,..." verb corrections → Updated).
173b new t1-F08/t1-F09 (192 Updated on mother/father; stored identical).
174 new n36 (188) and n37 "what is the city of zara's boss?" (180b
restores "Zara" casing in the unknown reply; stored [] both).
M2-A (vs sealed m2-138i A diffs): 165 T02-T28 (even ids) verdict OK,
Saved replies identical, ask replies render canonical casing
("Mira's boss is Kim." for "Who is miras boss?" — 180b/193
normalisation; answers still Kim). 166c F08/F09 (192 Updated on
mother/father). 166c-B L01/L04-L08 ask/second-mention replies render
canonical casing ("Wug's toy is ball." etc.); L02 stores the canonical
display ("Zib" entity holds the color; 138i stored lowercase "zib"
via the 166c path — same fact, 180b input-normalisation first).
173-t1 F08/F09 (192). 173-t1b R1/R3/R4 name re-teaches: change-prompt
kept, yes-to-change answers Updated (judge-literal WRONG-REPLY vs its
Saved expectation; stored names identical).
M2-B (vs sealed m2-138i B rows): 137e +T1-N-07/T1-O-07/T1b-E08/T1b-E09
(188). 139e O11/O13/O15 "yes." confirmations → Updated (192;
stored equal). 142 identical. 146d PASS. 150b X01 (188; nowrite kept).
153 P01/P02/P04/P05/P06/P07/M01/M04/M09 reverse asks take 190's
forward-style wording ("Tom's boss is Bob." for 153's "Bob is the boss
of Tom."; stored identical — 190-own already answers this way on 138g).
156b: P01/P02/P04 ("sorry" variants) echo "I haven't said anything
yet." (189b repeat, noprev); N03/N05/N07/N08/N09/N12/N14/N20/N23/N24/
N28/N29/N32 take 188's fallback; N17 "who are you" takes 187's
identity reply; N11 identical to sealed (inherited). 157
T07/T10/C05/C09/C12/C14/C16 take 188's fallback (stored [] both).
158 N08 "Tell me about Tess" takes 164b's unknown reply "I don't know
anyone called Tess." (stored [] both). 158c +S21 "Sue's city is Leeds."
(180b restores "Sue" casing; wrote 0 both). 159 T08 stores "red Ball"
(180b token-casing inside the phrase value; byte-identical to
loop180b-own reply + stored; honest broken-chain answer kept).
168 identical.
M2-G3 (cases138i-g3.json): 6/6 identical replies + stored.

## G1 — bench under protocol v3 (confirming user), loop138j arm
Bar: 0 verdict moves, 0 new wrong vs loop138i's sealed v3 rows
(g1bench/fable_benchv3_loop138i_*_rows.jsonl). Predicted: none —
piloted 800/800 identical (new_121_4hop 187/9/4, old_s2fresh_4hop
195/5/0, edit200 149/51/0, bench132_4hop 191/9/0).

## G2 — frozen suites
Bar per-case identical to loop138i except predicted; 0 new WRONG /
WRONG-WRITE / junk writes.
- redteam136 (145): 33 reply-form moves (QF→188 fallback, verdicts
  unchanged incl. 2 MISSED/MISSED; stored [] identical everywhere):
  C063-C071 C073/C074 C080/C081 C083-C085 C087/C088 C092/C093 C097/C098
  C106 C115 C124 C127 C129 C131 C133 C137/C138 C141/C142. 0 new wrong
  (6 pre-existing WRONG-WRITE identical).
- redteam143 (124): Q1-Q7 HARNESS-ERROR (frozen teach gate takes literal
  "Saved:"; teach-3 is an explicit "Actually,..." correction so 192
  answers Updated, tripping the gate). Stored facts verified correct
  and identical to 138i; Q3/Q5/Q7 questions verified byte-identical
  in-process (Q3's 4-hop answer tracks the correction). 0 new wrong.
- sessions152: 16 moves, 0 new wrong, 0 new writes. 188 reply-form:
  S2n8 ("I think Kip Dune's city is Reno."), S3n6 ("no wait, it's
  denver", UNHELPFUL→UNHELPFUL), S6n14 ("no Vera's city is Quito").
  192 Updated: S3n7 ("Actually, Rao's city is Denver." → "Updated:
  Rao's city is Denver (it was seattle)."), S6n16 ("Actually, Vera's
  city is Quito." → "Updated: Vera's city is Quito (it was Lima).").
  187 identity (UNHELPFUL→OK): S2n10, S4n8 ("who are you"). 180b
  canonical-casing answers: S2n7/n13/n18/n23, S5n4/n5/n6/n10/n13
  ("rosa's friend is Tess." → "Rosa's friend is Tess.", etc.).
- marks123 (stock CLI, no confirming user) per-case vs marks138i:
  p2/p4/rt110/q4/bench-report/bench-rows(400/400)/l1/l2/l3/l4/l5z2/l6-functional
  0 moves. rt81 10 moves: B_corrections-02/B_corrections-05/H_norm-04/
  L_selfref-04/P_contra-03 → Updated with facts_delta 1 (judge-literal
  UNCLEAR; replacements correct); B_corrections-04/F_pronoun-03/
  K_json-01/K_json-02/Q_quote-01 → 188 fallback with 0 writes (judge
  wording bucket only). q1 m5_reply "Mira's city is Lisbon." (180b
  canonicalises shouted MIRA; F5+M5 verdicts stay OK). sleep SKIP
  reason differs only by agent filename (volatile, 156c precedent).
  soak wrong 40 (all "Actually, SoakP*'s city is SoakW*." corrections
  → Updated; lost/doubled/audits identical). p3-l5z1 idx25-32/34: 7
  reply-only 192 rows (idx25 city, idx26/27/31/32 job, idx30 city,
  idx34 father) + idx28/29 pet 1-value replaces storing exactly
  154g-own's triples ([Pebble]/[Ash] alone vs 138i's add). p3-l6
  replied_before_kill ±1 (timing-volatile kill race; correct 200,
  wrong 0, chain_ok on all seeds both sides). rt110 re-run once in the
  open (known startup mailbox race): both numbers reported in
  RESULTS.md. 0 new WRONG/WRONG-WRITE/junk writes throughout.

## G3 — director pairs, fresh loop each (frozen pre-seal, cases138j-g3.json)
Bar: exact replies as below (b byte-identical to loop192-own live
pre-seal; rest composed, pieces named):
(a) "Oda's boss is Kim." => "Saved: Oda's boss is Kim."; "Kim's city is
Lagos." => "Saved: Kim's city is Lagos."; "what is odas boss's city?"
=> "Oda's boss's city is Lagos." (180b + 193 + base two-hop)
(b) "Kim's boss is Sam." => "Saved: Kim's boss is Sam."; "No, Kim's
boss is Lee." => "Updated: Kim's boss is Lee (it was Sam)." (192)
(c) "Omar speaks Urdu." => "Saved: Omar's language is Urdu."; "No,
Omar's language is Farsi." => "Updated: Omar's language is Farsi (it
was Urdu)."; "What is Omar's language?" => "Omar's language is Farsi."
(167d verb + 154g replace + 192 template)
(d) "Omar speaks Urdu." => "Saved: Omar's language is Urdu."; "Omar
speaks Hindi." => "Saved: Omar's language is Hindi. (I also have
Urdu.)"; "Omar's language is not Hindi." => "OK, Omar's language is
not Hindi. I still have Urdu." (167d + 154e multi + 154f)
(e) "Kim's boss is Lee." => "Saved: Kim's boss is Lee."; "Kim works at
Acme." => "Saved: Kim's employer is Acme."; "Tell me about Kim." =>
"Kim's boss is Lee. Kim's employer is Acme." (167d + 164b)
(f) "Kim's boss is Lee." => "Saved: Kim's boss is Lee."; "Who is Kim's
boss?" => "Kim's boss is Lee."; "Come again?" => "Kim's boss is Lee."
(189b echo)
(g) "Kim's city is Lima." => "Saved: Kim's city is Lima."; "Who lives
in Lima?" => "Kim's city is Lima." (190/190b)
(h) "My name is Juno." => "Saved: your name is Juno."; "Tell me about
me." => "Your name is Juno." (173b + 164b)
(i) "What are you?" => "I am plain software you are teaching: a
notebook, a lookup loop, and fixed rules. I can only tell you what you
taught me." (187b); "The weather was nice yesterday." => "I couldn't
save that as a fact. I don't know that shape yet. Could you say it
another way, like "Kim's boss is Lee."" with 0 writes (188)

## G4 — 170 index identity on loop138j itself
Bar: S2-fresh 1000 turns, every reply + notebook facts-sha + event
count identical with index on vs off (off arm: FABLE138J_INDEX=off
subprocess). Piloted: 0 reply diffs, facts equal, events 1129/1129.

## Common rules
Seal: shasum -a 256 PASSMARKS.md + cases138j-g3.json + agent code +
config > SEAL.sha256.txt BEFORE any registered run. Ledger P138j.n
appended before the run. Fictional names only. Bench = base agent's
driver (v3 protocol for G1; marks123's own bench suite stays stock).
Each run < 25 min Mac CPU (OMP_NUM_THREADS=1 MKL_NUM_THREADS=1, uv
offline py3.12); daemon wrappers use idle_seconds=3600. Heavy suites
one at a time. Never write to the repo-root notebook/. Post-seal
code/config/case change => registered FAIL; driver-only fix reported
with diff, affected marks re-run in the open.
