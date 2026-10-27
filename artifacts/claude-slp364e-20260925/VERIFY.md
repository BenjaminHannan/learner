# slp-364e verification (blind recount by a separate Opus agent, 2026-09-25 ~11:05 UTC)

Recounted from results.json with its own script (not score()): V2 17/20 faults rejected (missed 16, 38, 39), V1 9/20;
honest rejected 0/20; main log + sandbox 40/40; honest replies identical 20/20; caught only by new rules 2 (18, 28,
both F); 0 errors; no reason list was cut. Verdicts: P364e.1 FAIL, P364e.6 FAIL, the other four pass; not proved
wrong. Only F and Z fired among the new rules; Y and E never fired. Seals 11/11 OK. Commit order clean (marks 07:54 ->
dev disclosure 08:09 -> bench 10:24 -> results 10:58); no bar changed after registration.
Disagreements on numbers: none. Claims reaching past this run's data were narrowed in RESULTS.md (the cross-run
"notebook safe on every night tested" and "best gate so far"). "4 workers" is from the command line, not the data.
