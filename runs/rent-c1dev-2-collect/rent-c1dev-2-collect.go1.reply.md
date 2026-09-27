Sun Sep 27 16:51:53 UTC 2026
job rent-c1dev-2-collect
c1-dev vast collect, kit d0072550e7756cbfb99a184f3c891faf78049463, job rent-c1dev-2-collect, 2026-09-27T16:51:57Z
guard pid(s): none; live claude-everydaychat-c1dev instances: 
2026-09-27T15:25:02Z ok: 2026-09-27T15:19:55Z ARM Q start | bytes 478381 | gpu 22% | spent $0.73
2026-09-27T15:30:05Z ok: 2026-09-27T15:19:55Z ARM Q start | bytes 522595 | gpu 22% | spent $0.76
2026-09-27T15:35:12Z ok: 2026-09-27T15:19:55Z ARM Q start | bytes 566439 | gpu 22% | spent $0.79
2026-09-27T15:40:16Z ok: 2026-09-27T15:19:55Z ARM Q start | bytes 612204 | gpu 21% | spent $0.83
2026-09-27T15:45:24Z GUARD DONE
2026-09-27T15:45:39Z COPY-CHECK: 18 of 18 files arrived and match the rental's manifest (chat rows: D=336 T=336 Q=336 L=336)
2026-09-27T15:46:09Z DESTROYED 52972843 (confirmed gone), spent so far $0.87
2026-09-27T15:46:09Z GUARD-END DONE, spent $0.87
guard: END DONE spent 0.87
# c1-dev vast run record (handoff/kit/c1devv, job rent-c1dev-2-collect, kit d0072550e7756cbfb99a184f3c891faf78049463, written 2026-09-27T16:51:59Z)

**COMPLETE: all 4 arms have 336 rows over 60 conversations.** Counts only, no verdict: the Everyday chat thread scores it (PLAN.md, ADDENDUM-2-vast.md). Every line
below is copied by the script, never retyped. The replies are in the chat files and are not quoted here.

## Card and money

- Card: RTX_4090, 81.4 TFLOPS, $0.402/h, 202 TFLOPS per $/h (estimate 102 min); guard: END DONE spent 0.87
- Rentals (id, $/h, created, gone; epoch seconds):
    52972843 0.402 1790520744 1790523969
- Spent by the kit's own count (GPU $/h x hours plus each started host's download at its $/GB): $0.87. The Director's ledger is the record.

## V1 (first two log lines; logD also has the c1dev settings line)

- V1 D OK
- V1 T OK
- V1 Q OK
- V1 L OK

- c1dev line in logD: c1dev: talker = claude_e2e02d.Talker; W_PLACE02D=system; MAX_NEW02D=160; HIST_PAIRS=6; SLEEP02D=off; reader = none; reasoner = none

## Rows per arm (expected 336 rows, 60 conversations)

    D rows=336 conversations=60; T rows=336 conversations=60; Q rows=336 conversations=60; L rows=336 conversations=60

## Steps (W/steps.txt, UTC)

    D start 2026-09-27T14:56:18Z
    D rc=0 end 2026-09-27T15:08:13Z
    T start 2026-09-27T15:08:13Z
COLLECTED: COMPLETE: all 4 arms have 336 rows over 60 conversations
rc=0
