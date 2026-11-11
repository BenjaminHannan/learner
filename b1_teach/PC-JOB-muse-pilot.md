# Job: Muse Spark contributor-tier pilot for TEACH-strong (API only, no GPU; run on the Mac or PC, whichever has the key)

Ben chose the contributor tier (6 Oct): $0.10 in / $0.20 out per 1M tokens, Meta may train on our prompts and replies (invented children's sentences only).
Needs env `LLM_API_KEY` (Meta developer API or OpenRouter key; never printed or committed) and `LLM_BASE` (OpenAI-style base URL ending /v1; default https://openrouter.ai/api/v1).
Model id: the contributor variant, e.g. `muse-spark-1.3-contributor` (check `GET $LLM_BASE/models` for the exact id).
Same checkout as the other jobs (branch claude/b1-teach-gen-data, folder b1_teach, pull latest).

Pilot (cap $0.45 is built in; it stops itself at the cap or after --pilot-calls):
 for N in 10 25 50:
   python teach_packed.py --out <dir>\pilot_n$N --model <id> --price-in 0.10 --price-out 0.20 --per-kind 100 --write-n $N --verify-m 40 --workers 4 --max-usd 0.15 --only owner_possession,event_ordering,pronoun_reference,caretaker,if_then
   python teach.py --out <dir>\pilot_n$N --stage filter --only owner_possession,event_ordering,pronoun_reference,caretaker,if_then
 Report for each N: cost.json, "write calls with block count != N", items parsed, kept rows per kind (teach_report.json), and the top drop reasons.
Stop on any 429/402/403 (the script does). Do NOT run the full job; it needs Ben's yes after the projection.
