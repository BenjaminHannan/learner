Sun Sep 27 18:39:04 UTC 2026
job rent-c1dl-2-collect
c1-dl vast collect, kit 19af6d2942ca75cc659d3cf5c2f3e41ce8c34fbb, job rent-c1dl-2-collect, 2026-09-27T18:39:07Z
guard pid(s): none; live claude-everydaychat-c1dl instances: 
2026-09-27T18:12:43Z CHECKS-OK
2026-09-27T18:12:43Z ARM DL start
2026-09-27T18:13:04Z arm DL started on 53004719; spent so far $0.19
2026-09-27T18:13:19Z no ssh answer (1), status 
2026-09-27T18:18:24Z GUARD DONE
2026-09-27T18:18:29Z COPY-CHECK: 12 of 12 files arrived and match the rental's manifest (chat rows: DL=336)
2026-09-27T18:18:42Z DESTROYED 53004719 (confirmed gone), spent so far $0.23
2026-09-27T18:18:42Z GUARD-END DONE, spent $0.23
guard: END DONE spent 0.23
# c1-dl vast run record (handoff/kit/c1dlv, job rent-c1dl-2-collect, kit 19af6d2942ca75cc659d3cf5c2f3e41ce8c34fbb, written 2026-09-27T18:39:09Z)

**COMPLETE: arm DL has 336 rows over 60 conversations.** Counts only, no verdict: the Everyday chat thread scores it (PLAN.md) against c1-dev's T, Q and L chats. Every line
below is copied by the script, never retyped. The replies are in the chat files and are not quoted here.

## Card and money

- Card: RTX_4090, 81.4 TFLOPS, $0.428/h, 190 TFLOPS per $/h (estimate 32 min); guard: END DONE spent 0.23
- Rentals (id, $/h, created, gone; epoch seconds):
    53001665 0.126 1790530566 1790531180
    53003253 0.106 1790531183 1790531736
    53004719 0.428 1790531739 1790533122
- Spent by the kit's own count (GPU $/h x hours plus each started host's download at its $/GB): $0.23. The Director's ledger is the record.

## V1 (first two log lines; logDL also has the c1dev settings line)

- V1 DL OK

- c1dev line in logDL: c1dev: talker = claude_e2e02d.Talker; W_PLACE02D=system; MAX_NEW02D=160; HIST_PAIRS=6; SLEEP02D=off; reader = none; reasoner = none

## Rows per arm (expected 336 rows, 60 conversations)

    DL rows=336 conversations=60

## Steps (W/steps.txt, UTC)

    DL start 2026-09-27T18:12:43Z
    DL rc=0 end 2026-09-27T18:15:47Z

Minutes per arm: DL 3.1; 
COLLECTED: COMPLETE: arm DL has 336 rows over 60 conversations
rc=0
