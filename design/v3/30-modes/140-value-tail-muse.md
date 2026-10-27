# 140 — value-tail cleaner (single-change fix for redteam136 W4 + W7 + W8)

## Problem

Red team 136 found three stored-junk classes on loop129b with one shared
root: value tails are cleaned too little, or too early with the wrong tool.

- W4: the exp-129 sanitizer strips only `.!?;:` — emoji/symbol runs survive
  (`Rome 😀`, `Bob ❤️`). `scripts/fable_fix129_punct.py:119`.
- W7: only paired quotes are stripped — an unmatched trailing `"` survives
  (`Peru."`). `scripts/fable_fix129_punct.py:104`.
- W8: FakeEars does `value.rstrip(".")` BEFORE the abbreviation-aware
  sanitizer, so `Washington, D.C..` loses its content dot and stores
  `Washington, D.C`. `scripts/fable_agent_loop.py:136`.

## Design (one change, additive only)

`scripts/fable_fix140_tail.py` holds a MIXIN (`ValueTailMixin`) plus the two
functions it wraps, so tonight's integration (exp 138) can stack it onto
another loop class without importing loop140:

- `clean_span`: 129's strip-then-restore, extended. After whitespace
  normalisation and wrapping-quote removal, it greedily drops trailing
  sentence punctuation, symbol/emoji runs (Unicode So/Sk/Sm/Sc/Cf, variation
  selectors, ZWJ), unmatched bracket closers, and unmatched trailing quote
  chars, in any order — then restores ONE `.` after abbreviation-shaped
  tokens exactly like 129 (internal dot, single initial, honorific/street/
  corporate list). Stripping only removes trailing characters, so internal
  symbols (`Either/Or`, `A/UX`) are byte-identical.
- `TailFakeEars(FakeEars)`: the possessive-path override. Same parse, but
  the raw value goes through `clean_span` instead of `rstrip(".")`. Guard
  signals are preserved: empty spans and spans carrying `?`, `;`, or >6
  words keep the old rstrip result verbatim, so the exp-91/121 screens fire
  exactly as on the base loop (this was missing in run-1 and regressed 2
  cases; see RESULTS.md D1).
- `sanitize_action(s)` / `sanitize_triple`: name+value cleaned, relation
  keys and non-teach actions untouched, empty-after-strip left as-is.

`scripts/fable_loop140_agent.py` is the thin wrapper: `Loop140Ears`
sanitizes outgoing teach/correct, `Loop140AgentLoop._act` sanitizes again
pre-write (covers the inner-chain delegate path), and `build_agent140`
swaps every plain `FakeEars` under the ears wrappers for `TailFakeEars`
(notebook never descended into). `Loop140Daemon` + `--daemon` entry mirror
loop129b; the mailbox is unchanged.

## Why this shape

Cleaning at three levels (ears-out, pre-write, possessive source) is the
same defence the 129 patch used; the new bit is fixing W8 AT THE SOURCE,
because once `rstrip` eats the abbreviation dot no downstream sanitizer can
recover it. Keeping guard-visible signals intact is the subtle constraint:
the cleaner must run after guards conceptually, even where it physically
runs before them (inside the chain). The `?`/`;`/word-count preservation
rule encodes exactly that.

## Evidence (registered)

T1 43/44 (1 probe-design FAIL, identical on base) + 5/5 subject checks; T2
focus 5/5 exact with 119/119 prior-OK kept; marks123 0 verdict moves and
600/600 bench rows byte-identical vs loop129b; 425 s wall (< 1500 s).
Untouched classes (W1/W2/W3/W5/W6) still fail exactly as sealed.

## For exp 138 (stacking)

Subclass `ValueTailMixin` alongside the next fix; call
`sanitize_actions` on outgoing teach/correct and `sanitize_action` in
`_act`. Keep `TailFakeEars` as the innermost FakeEars — its guard-signal
rule must survive any reordering, or C077/C138-style regressions return.
