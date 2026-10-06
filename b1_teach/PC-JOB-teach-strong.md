# PC job: B1 TEACH-strong (teacher = a stronger model through Ben's OpenCode Go API; separate arm, official 1.2B B1 unchanged)

Ben accepted the OpenCode terms risk (6 Oct, bulk generation). API calls only, no GPU, so it runs beside the 1.2B TEACH job.
Needs `OPENCODE_API_KEY` set in the environment on the machine that runs this (Ben sets it, never in chat or on a command line).

1. Same repo checkout as PC-JOB-teach.md (branch claude/b1-teach-gen-data), folder b1_teach.
2. List models first and pick the DeepSeek V4 Flash id: `python -c "import os,urllib.request,json;r=urllib.request.Request('https://opencode.ai/zen/go/v1/models',headers={'Authorization':'Bearer '+os.environ['OPENCODE_API_KEY']});print(urllib.request.urlopen(r).read().decode()[:3000])"`
3. Pilot (about 30 cents): `python teach.py --out C:\Users\benja\b1_teach_strong_pilot --backend api --api-model <id> --per-kind 40 --max-rounds 1 --workers 6 --max-per-min 300`
   then `python teach.py --out C:\Users\benja\b1_teach_strong_pilot --stage filter` and report teach_report.json (kept per kind, drops). Stop here and report.
4. Full run (only after the pilot looks sane): same command without --per-kind/--max-rounds, `--out C:\Users\benja\b1_teach_strong_out --max-per-min 600 --workers 10`, logging to a file.
   It stops by itself (exit code 3, "API STOP") on any 429/402/403/quota error or at 45M tokens; progress is saved; rerun the same command later to resume. Do not retry in a loop.
   Limits on the $10 plan: $12 per 5 hours, $30 per week, $60 per month, per model sub-limits. Expect the full run to take about a day or two of limits, not hours.
5. Output: teach_200k.jsonl + teach_report.json in the out folder; then export.py as for the 1.2B arm, named teach_strong.jsonl.
