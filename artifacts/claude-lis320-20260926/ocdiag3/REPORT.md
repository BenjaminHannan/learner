# ocdiag3: can opencode ask GLM 5.3 Flash for less thinking? (lis320-ocdiag3)

VERDICT: `--variant low` parsed 4 of 4 dialogs with a median wall time of 12.5 s
(5, 10, 15, 15 s) and step_finish reasoning tokens of 0-9 per call, versus the
default-thinking ocdiag B runs on the same 4 prompts (88 s, 112 s, 263 s-class,
one 300 s timeout; output-token usage up to 7609 where shown, with no reasoning
field in the default streams). Low-thinking is roughly an order of magnitude
faster and fully parseable, so long thinking explains ocdiag's 88-263 s calls
and the ~106 s pre-text silence.

## Setup (step 1)
- origin/main rev: ac4237274dc37e737ba85149e4583c01a1f737ce
- opencode version: 1.18.32
- seeds: origin/builder-outbox pilot3 seeds.jsonl, 60 lines
- prompts: scripts/claude_lis320_glm.py --dry-run, sizes 4448 / 4756 / 5108 / 5283
  chars for 00004 / 00001 / 00000 / 00002 (identical to ocdiag's sizes)
- WAIT: 000-lis320-ocdiag-mac and 001-lis320-ocdiag2-mac both show .done +
  .pushed in the queue dir and no running process; no wait needed
- GLM calls used: 4 (budget: at most 12). Time used ~10 min of 60 min cap
- No reader, no rental, no BensPC, no OpenRouter. Mac CPU only

## Flags (step 2, help text only, never config)
`opencode run --help` lines describing --variant and --thinking (verbatim):
```
      --variant      model variant (provider-specific reasoning effort, e.g., high, max, minimal)
                                                                                            [string]
      --thinking     show thinking blocks                                                  [boolean]
```
(`--thinking` is display-only, not a thinking control, so it was not used.)
`opencode models --help` output (verbatim, complete):
```
opencode models [provider]

list all available models

Positionals:
  provider  provider ID to filter models by                                                 [string]

Options:
  -h, --help        show help                                                              [boolean]
  -v, --version     show version number                                                    [boolean]
      --print-logs  print logs to stderr                                                   [boolean]
      --log-level   log level                   [string] [choices: "DEBUG", "INFO", "WARN", "ERROR"]
      --pure        run without external plugins                                           [boolean]
      --verbose     use more verbose model output (includes metadata like costs)           [boolean]
      --refresh     refresh the models cache from models.dev                               [boolean]
```
`opencode models --verbose opencode-go` variant names shown for
opencode-go/glm-5.3-flash (names only): low, high, max
(full block: low -> reasoningEffort low; high -> reasoningEffort high;
max -> reasoningEffort max; capabilities.reasoning true).
Decision: V1 = --variant low (the only sub-default thinking setting).
V2 skipped: no second lower-thinking variant exists. No-variant default runs
were not repeated here; the default baseline is ocdiag's B runs (same prompts).

## Calls (step 4)
One at a time, each in a fresh empty temp dir, stdin </dev/null, 300 s watchdog
by exact PID (no call overran; all temp dirs removed after use):
`opencode run --model opencode-go/glm-5.3-flash --format json
--title lis320diag3-low-$ID --variant low "$(cat p_$ID.txt)"`

## Per-call results (step 5)
Columns: V | id | 1-min load before | exit | wall s | ms step_start->first text |
in/out/reasoning/total tokens (step_finish) | cost | text chars | parse non-None

- low | s320-321-00004 | 30.66 | 0 | 15 | 11288 | 15607/326/9/15942 | 0.00251 | 1126 | true
- low | s320-321-00001 | 25.97 | 0 | 5 | 1207 | 15651/324/0/15975 | 0.00251 | 1041 | true
- low | s320-321-00000 | 26.35 | 0 | 10 | 3897 | 15795/314/0/16109 | 0.00253 | 1065 | true
- low | s320-321-00002 | 24.82 | 0 | 15 | 9608 | 15834/412/7/16253 | 0.00258 | 1447 | true

Notes:
- parse = scripts/claude_lis320_glm.parse(text, n_turns) is not None, with text
  = concatenated text events and n_turns from seeds.jsonl (6/8/7/8). 4 of 4 true
- every stream has exactly 3 events (step_start, text, step_finish); no tool
  calls, no error events; stderr empty (0 bytes) on all 4 calls
- median wall s = 12.5; median step_start->first-text = 6.75 s
  (vs ~106 s of pre-text silence at default thinking in ocdiag)
- default baseline (ocdiag B, same prompts, --format json, no variant):
  00001 exit 0 in 112 s, 00000 exit 0 in 88 s, 00004 timeout at 300 s;
  session usage out=6767 / 303 / 7609 with no reasoning-token field shown
  (00002: 3 events, parse ok). Reasoning tokens at default are not shown
  anywhere in ocdiag's streams, hence "where shown" comparison only

## Cleanup (step 6, as 000 step 5, titles lis320diag3-)
- session list from worktree root before: 9 total, 0 with prefix (run sessions
  are not listed globally; deleted by id from this task's own output files)
- deleted by id, one per command: 4 sessions (ses_f20573bd1ffeCY3wQX2JJyEj2t,
  ses_f2056f117ffeDDDoTi75yi62LP, ses_f2056d620ffefUsx9pKSGbnLVo,
  ses_f2056a424ffe2iM9qSBqOpFqWl), all reported deleted, exit 0
- after: worktree root list 9 total / 0 with prefix; fresh temp dir list
  9 total / 0 with prefix. The other 9 sessions (other agents' mimo tasks)
  untouched. Deleted-from-worktree count 0 (none listed there), by-id count 4
- temp dirs: all 4 per-call dirs removed; $D removed after copy (confirmed gone)

## Redaction
- Lines dropped by the rule in the task spec before repo copy: 1
  (the basic-auth-flag help line in run_help.txt). See REDACTED_COUNT.txt
- Real filesystem paths in copied files: 0. A first copy pass made
  3 false-positive path substitutions inside this section's own wording;
  reworded here so the final files hold no such tokens
- Token COUNTS kept (allowed)
