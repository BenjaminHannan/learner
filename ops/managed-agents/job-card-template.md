# Job card template

Save a filled copy on BensPC as `C:\Users\benja\pc-jobs\<job>.md` when a long job starts, and move it to
`C:\Users\benja\pc-jobs\done\` when the job ends. The pc-operator reads every card in `pc-jobs` on each check and takes
only the actions a card spells out. Keep each line short; `log:` must be one full Windows path on its own line.

```
job: g1-3m-s400
owner: Whole-model roadmap thread (Gate G1)
gpu: yes
started: 2026-10-08 7:08 PM ET
log: C:\Users\benja\<run folder>\stdout.log
stall_minutes: 20
alive: a python process whose command line contains <unique part of the command>
done_when: the log prints <final line>, or <result file> exists
on_spill: shared GPU memory over 1024 MiB -> stop the exact PID, double --grad-accum (max 16), relaunch with: <exact command>
on_crlf: hash or MANIFEST mismatch on a data file -> <exact fix command>, then relaunch with: <exact command>
on_crash: report only
max_restarts: 2
next: when done, start <next queue item command> and write its card, or "nothing"
never: change seeds, data, marks or any setting not named above
```
