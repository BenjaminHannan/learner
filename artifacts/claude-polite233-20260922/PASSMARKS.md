# Exp 233 PASSMARKS — polite negative questions (sealed before any registered run; panel not yet opened)

Base: loop223 (scripts/fable_loop223_agent.py, config
artifacts/fable-cantdo223-20260922/loop223-config.json).
Agent: scripts/claude_loop233_agent.py, config
artifacts/claude-polite233-20260922/loop233-config.json.
THE ONE CHANGE: Loop233AgentLoop.turn rewrites a "?" turn that starts with
a polite negative frame (can't/cannot/couldn't/won't/wouldn't/don't you,
do you not; optional please/just; then tell me/know/remind me/say) to the
plain question it contains, iff it parses and the rewritten question has
no negation word; the plain question then goes through the unchanged
loop223 turn(). Every other turn: loop223 turn() with the original text.
Design note: design/v3/30-modes/233-polite-opus.md.

Runner/scorer (sealed): scripts/claude_polite233_run.py. Per case, fresh
loop223 daemon and fresh loop233 daemon in isolated scratch dirs (order
alternates per case), setup turns then the question. Definitions are in
the runner docstring: right, wrong value, honest abstain, q-write,
identical (reply and stored triples), per-case pass.

Dev cases: artifacts/claude-polite233-20260922/dev233.jsonl (63, written
by me, fictional names; 23 polite_taught, 12 polite_untaught, 16
true_negation, 12 negated_statement).
Dev pilot (pre-seal): 62/63 pass; 0 wrong (both agents); 0 q-writes;
polite_taught right 22/23 (223: 0/23); untaught abstain 12/12 (223: 1/12);
true_negation 16/16 identical; negated_statement 12/12 identical. The one
miss D21 "Couldn't you say where Jessamy's boss lives?" rewrites to
"Where does Jessamy's boss live?", which the base itself does not read
(honest abstain, not a wrong value). Latency: median per-case diff
-7.7 ms (rewritten polite questions skip the screen/route path).

Suites pilot (pre-seal) vs 223's registered rows (rt136/rt143 rows copied
unchanged from artifacts/fable-cantdo223-20260922/reg-rt136|reg-rt143 into
artifacts/claude-polite233-20260922/base223/ under file names the
suitediff finder matches; sessions152, bench, marks123 via --base-dir
artifacts/fable-cantdo223-20260922): 0 moves on all five, GATE clean.
Sleep smoke pilot: sleeps=1 installed=1 episodes=20 probes=5/5 wrong=0
abst=0 broken=abstain taught=50/50 ow=0 (same as 223's registered smoke).

## Marks
- M1 panel (artifacts/claude-politepanel233-20260922/panel.jsonl, 60
  items, opened only after this seal; its own SEAL checked first):
  (a) 0 wrong values on the 233 side; (b) 0 question writes on the 233
  side; (c) polite_taught right(233) >= right(223) + 15; (d)
  polite_untaught: 100% honest abstain on the 233 side; (e) every
  true_negation and negated_statement item identical (reply byte-equal
  and stored triples equal) to 223. Any one failing -> M1 FAIL.
  Items with expect=no_value in the polite families count as honest
  abstain if the reply abstains; they cannot be "right".
- M2 dev: >= 95% of the 63 dev cases pass (>= 60/63).
- M3 suites: scripts/fable_suitediff218.py on rt136, rt143 (base
  artifacts/claude-polite233-20260922/base223), sessions152, bench,
  marks123 (base artifacts/fable-cantdo223-20260922): 0 new WRONG, 0 new
  WRONG-WRITE, 0 new junk write, 0 lost OK; predicted moves: none (0 on
  every suite; no suite item starts with a polite negative frame in the
  pilot). Any move not predicted -> FAIL (flake rule from OPUS-RULES:
  reported as it is, then the item run alone 5 times).
- M4 sleep smoke: scripts/fable_sleepsmoke206.py on loop233 gives
  sleeps=1 installed=1 probes=5/5 wrong=0 broken=abstain taught=50/50
  ow=0.
- M5 latency: on the registered panel run, median over items of
  (233 question-turn ms - 223 question-turn ms) <= +5 ms, AND the same
  median restricted to true_negation + negated_statement items <= +5 ms.

Verdict PASS iff M1-M5 all pass. A FAIL is reported as FAIL with one
diagnosis note; no silent re-runs; every panel item listed.
Env: Mac CPU, offline, OMP_NUM_THREADS=1 MKL_NUM_THREADS=1, uv run
--offline --no-project --python 3.12 --with torch --with numpy python -B;
one heavy run at a time; load checked (< 60) before each registered run.

Sealed files: this PASSMARKS.md, scripts/claude_loop233_agent.py,
scripts/claude_polite233_run.py, artifacts/claude-polite233-20260922/
loop233-config.json, artifacts/claude-polite233-20260922/dev233.jsonl,
artifacts/claude-polite233-20260922/base223/reg-rt136/redteam136-rows-223.json,
artifacts/claude-polite233-20260922/base223/reg-rt143/redteam143-rows-223.json,
design/v3/30-modes/233-polite-opus.md.
