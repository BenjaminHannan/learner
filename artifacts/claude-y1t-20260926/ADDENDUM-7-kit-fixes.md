# y1t addendum 7: three fixes to the BensPC runner before it runs (Answering-from-memory thread, 2026-09-27 11:47 UTC, before any y1t training run; sealed in SEAL-y1t-add7.sha256.txt)

ADDENDUM-6's kit (15a952c79) never ran. Rereading the BensPC patterns tested on the real machine (the job
173-rv390-358i2-pc-d) showed two things the kit should match, and the disk floor was higher than the run needs. Only handoff/kit/y1tpc/pass.sh and
remote/boy1t.sh change. The experiment and ADDENDUM-6's five points stay the same.

1. **Mac locale.** pass.sh now sets LC_ALL=C (and COPYFILE_DISABLE=1). The tested job does the same, because macOS
   `cut` failed with "Illegal byte sequence" on BensPC output.
2. **Git Bash call.** The helper is called as `"C:\Program Files\Git\bin\bash.exe" C:/Users/benja/y1t/tree/...`, the
   path form the tested job uses, instead of /c/Users/....
3. **Disk floor 6 GB, not 10.** The run writes about 2.2 GB (the merged model is about 2.1 GB, as recorded for earlier
   merged 1B models). Starting at 6 GB or more leaves Ben's 3 GB BensPC floor (his 01:30 UTC choice, "Lower to 3 GB")
   free afterwards. The extra copy of tr/merged into premonition-models/y1t is made only if 3 GB would still be free
   after it. Otherwise it stays in the tree at C:\Users\benja\y1t\tree\tr\merged, and the run notes say so. The old 10 GB came from
   benspc-y1t.md and allowed for both copies. Nothing is deleted to make room.
