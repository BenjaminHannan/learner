# mu-405 run on the thread's CPU (registered run: run2/, ADDENDUM-2), written 2026-09-26 22:37:34 UTC by date -u

## started.txt
    Sat Sep 26 19:18:49 UTC 2026
    torch 2.14.0+cpu transformers 5.17.0 threads 4
    restart of the registered run (ADDENDUM-2)

## exits.txt
    N exit 0 20:00:54
    K exit 0 20:42:09
    W exit 0 21:22:17
    H exit 0 22:36:09

## Last JSON line of each log
    {"arm": "N", "items": 60, "rows_session2": 300, "rows_all": 300, "ask_right": 0, "ms_median": 5793.4}
    {"arm": "K", "items": 60, "rows_session2": 300, "rows_all": 300, "ask_right": 3, "ms_median": 6510.4}
    {"arm": "W", "items": 60, "rows_session2": 300, "rows_all": 300, "ask_right": 4, "ms_median": 5837.4}
    {"arm": "H", "items": 60, "rows_session2": 300, "rows_all": 505, "ask_right": 1, "ms_median": 6407.4}

## Tracebacks per log
    N 0
    K 0
    W 0
    H 0

## sha256
    d3466d7242db1784962120bbc7390ce8d1d277c5320d7a7211dd785b422b0884  artifacts/claude-mu405-20260926/run2/talk_H.jsonl
    1d5be8086d5f57d438577125e2a2fac7a571251e5a932eb68053fc48aaeb182a  artifacts/claude-mu405-20260926/run2/talk_K.jsonl
    1ed656f1749beeb4eabee778b6e32c213c7d3dfda3de1376cae815573293df76  artifacts/claude-mu405-20260926/run2/talk_N.jsonl
    3a6a73409645e29ab9a88e4af7edf2911af56cb372facdc19fb29c3223aa7ce5  artifacts/claude-mu405-20260926/run2/talk_W.jsonl

## Deviations from the rental plan (handoff/held/rent-mu405.md)
- CPU float32 in the thread's cloud container instead of a GPU in bf16; torch 2.14.0+cpu, transformers 5.17.0,
  4 threads; arms run one after another (N, K, W, H), not at the same time. Every arm ran on the same machine.
- The first CPU attempt was cut at 19:02:05 UTC by a container restart (ADDENDUM-2); no reply existed; run2/ is the
  restart. The duplicate rental was destroyed with no output (ADDENDUM-1, ADDENDUM-2).
- Arm H ran partly alongside an unregistered smoke of mu-405b (22:00-22:11 UTC, killed by its own time cap, no output);
  greedy decoding, so only its speed was affected.

## Verdict
V405b failed (asks right N 0, K 3, W 4 of 60): Q1 and Q2 INCONCLUSIVE (VERIFY-V405b.md, blind recount matched).
H (report only): asks right 1 of 60 with both sessions as real chat history.
