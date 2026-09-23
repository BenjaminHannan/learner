# Exp 161 PASSMARKS — grounded self card (sealed before any registered run)

Agent: `scripts/fable_loop161_agent.py` (Loop161AgentLoop / build_agent161 /
Loop161Daemon / DEFAULT_CONFIG161) wrapping `scripts/fable_loop138_agent.py`
read-only; the only behavior change vs loop138 is the L2 self step, which
serves `scripts/fable_selfcard161.py` (SelfCard161) instead of the frozen
router plus the baked table. Serving rule unchanged: the notebook always
wins; only a notebook-missed turn reaches the card; a card DECLINE serves
the loop138 decline text verbatim (HONEST_DECLINE + suffix).
Config: `artifacts/fable-selfcard161-20260922/loop161-config.json`.
Seeded here before any registered run; hashed to SEAL.sha256.txt.

Environment: Mac CPU only, offline, `export OMP_NUM_THREADS=1
MKL_NUM_THREADS=1`, `uv run --offline --no-project --python 3.12 --with
torch --with numpy python -B ...`. Every seed/case reported, never
averaged. Runs are deterministic (no sampling); "seeds" below are panel
cases / bench items / suite cases, each reported. A registered FAIL stays
FAIL. Any code edit after the seal is reported and the affected marks
re-run in the open.

## Intent mapping (route127 family -> self-card intent)

C1->count_facts C2->count_people C3->last C4->first C5->provenance
C6->count_web C7->web_belief C8->count_sleep C9->sleep_learned
C10->sleep_derived C11->forgotten C12->count_forgotten C13->corrections
C14->corrections_count C15->confirm C16->mode C17->last_turn C18->count_turns
C19->count_answers C20->count_writes C21->count_clarify C22->unsure
C23->dontknow C24->cap_can C25->cap_cannot C26->speakers_any C27->web_source
C28->count_guesses C29->count_rules C30->trail D1->favourite D2->feelings
D3->past D4->future D5->reasons D6->speakers D7->opinion D8->username (my) /
identity (your) D9->age_you (my) / age_me (you) / age_them (named person)
D10->dream OOS/DECLINE->DECLINE. Second vs first person is read from the
asked text (your/you -> the agent; my/I -> the user); every other name is
resolved against live notebook state, never baked in. Content answers fire
only when the card can ground them (provenance/confirm need a live fact;
trail needs a walk ending in a plain value); otherwise the card DECLINEs.

## Marks

- S1 (script `scripts/fable_selfcard161_marks.py::mark_s1`): panel proper
  nouns = capitalised tokens (len>=2, minus "I") appearing
  NON-sentence-initially in the exp-99 canonical 40 + exp-100 blind 80 +
  panels 105/114/122/127 + train122/heldout122 question texts. Code tokens =
  same-shape tokens of `scripts/fable_selfcard161.py`. Bar: every
  intersection is in the frozen allow-list below; in particular zero panel
  person/place names appear. Allow-list (generic intent/template words
  only): BELIEVE CAN COUNT FACT FACTS Like PEOPLE SLEEP TEACH UNKNOWN What.
- S2 (same script `::mark_s2`): sealed panel `cases161.json` (69 cases, 21
  shared questions x 3 notebook states A=empty, B=5 fresh teaches, C=5
  teaches + 1 correction, plus 6 state-specific; all entity names fresh,
  absent from every panel above) through `SelfCard161.answer_self` direct
  on live loop161 state (teaches enter via loop.turn; answers log no turns).
  Each answer is scored against live state (counts/turns/values from the
  snapshot; declines need plain-words markers) and scanned: every number
  must be a live-state int, every capitalised word a live-state name or a
  frozen generic starter (I You Your My No Yes Only Nothing None Right Just
  We The A Every Like). Bar: <= 2 wrong AND 0 hallucinations.
- S3 (same script `::mark_s3`): the sealed exp-127 blind panel (100) through
  the loop161 turn path after the exact exp-99 session (20 teaches, 2
  corrections, 1 doorway forget, 3 asks, 1 quarantined web row), scored with
  `fable_self100_runner.score` against the live post-turn snapshot (same
  scorer as loop138 A3). Bar: <= 6 wrong (loop138 A3 count); each wrong
  reported with routed intent + scorer note.
- S4 (same script `::mark_s4`): bench121-new 200 questions, fresh loop161
  per item, teaches replayed, question through loop.turn. Bar: 0 content
  answers served by the card (DECLINE servings counted separately).
- S5a (`scripts/fable_loop161_bench.py`): bench121-new + bench103-old-fresh
  + bench65-edit200 (600 items) by mailbox daemon import-swap, per-item
  verdict AND reply compared to the sealed loop138 rows. Bar: identical
  except predicted self-path turns (below); every move carries in-process
  replay evidence of notebook-miss + card routing with the same reply.
- S5b (`scripts/fable_marks123_all.py --agent scripts/fable_loop161_agent.py
  --config artifacts/fable-selfcard161-20260922/loop161-config.json --out
  artifacts/fable-selfcard161-20260922/marks161`, then
  `scripts/fable_loop161_marksdiff.py` vs sealed marks138): every suite
  per-case reply AND verdict identical to sealed loop138 except predicted
  self-path turns (below). Bar: 0 moves outside the predicted set.
- S6: every registered run above < 25 min wall-clock Mac CPU
  (OMP/MKL=1; parallel processes allowed).

## Predicted self-path turns (pre-run; from in-process replays + sealed rows)

- Bench: bench121-new item 165 only: loop138 served route127 content
  (scored wrong), loop161 serves the decline text (abstain). All other 599
  items byte-identical replies and verdicts (decline servings are
  text-identical; the card contents on 0 items).
- marks123 rt110: P1/P3 step-0 reply moves (Self99 C30-fallback ->
  decline text; verdicts stay OK, no panel names in either reply); S1
  step-0 reply move ("web row" -> "web rows"; verdict stays BUG); S4
  step-1 OK->BUG (packed ask+teach answered as count instead of declined;
  0 writes hold). All other rt110 cases byte-identical.
- marks123 p2: D3/D5/D6/E8/G1 step reply moves (Self99 hardcoded
  opinion/future lines -> decline text; verdicts stay OK). All other p2
  cases identical.
- marks123 rt81: I_edges/M_hops/O_user one reply move each (Self99
  hardcoded lines -> decline text; write-count verdicts unchanged).
- marks123 q1/q4/p3/p4/bench/soak/sleep: no moves (soak passes 0/0/0
  internally like loop138).
