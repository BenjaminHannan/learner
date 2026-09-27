Sun Sep 27 11:07:01 UTC 2026
job 159-claude-sleep-358s-bo-collect
rsn-358s pass (collect), kit 84917d07bb51fdc69e6993559f490a14989ffdbf, start 2026-09-27T11:07:04Z
kit on BensPC matches 84917d07bb51fdc69e6993559f490a14989ffdbf
SEAL 19 19
DISK 5
GPU 332  16303
MARKER BUSY: queue job 158-claude-sleep-358spc-finish since 2026-09-27T09:42:53Z - do not use this GPU until this file is gone 
TESTSDIR 1
WDIR 1
PY 0 0
RUN loop-s9 log=1 dir=1 final=1 tests=0 evallog=0 train_proc=0 eval_proc=0
SHA loop-s9 30b43b4ffe9de370aa7b61f7547bb1e1f9fe0e6fe78496606747bc345bf710e5
LAST loop-s9 {"step": 60000, "ce": 0.0095, "exact": 0.9846, "halt_bce": 0.0111, "lr": 0.0, "min": 150.0, "exact_by_kind": {"grids4": 0.957, "grids5": 0.942, "numbers3": 1.0, "numbers4": 1.0, "sums1": 1.0, "sums2": 1.0, "sums3": 1.0, "sums4": 1.0}, "dev"
MIN loop-s9 150.0
RUN plain-s9 log=1 dir=1 final=1 tests=0 evallog=0 train_proc=0 eval_proc=0
SHA plain-s9 615d732413cd2dbe7fb59cdf94da937afe2c1e84d612a7cd5c1f1f8cd8de93fa
LAST plain-s9 {"step": 60000, "ce": 0.0002, "exact": 0.9996, "halt_bce": 0.0, "lr": 0.0, "min": 126.7, "exact_by_kind": {"grids4": 1.0, "grids5": 0.998, "numbers3": 1.0, "numbers4": 1.0, "sums1": 1.0, "sums2": 1.0, "sums3": 1.0, "sums4": 1.0}, "dev": {"s
MIN plain-s9 126.7
RUN loop-s10 log=1 dir=1 final=1 tests=0 evallog=0 train_proc=0 eval_proc=0
SHA loop-s10 83b44ac19e7653d48353a351f66892b2f2f95a738a288624bc00ffa9a4cefb5e
LAST loop-s10 {"step": 60000, "ce": 0.0147, "exact": 0.9793, "halt_bce": 0.0116, "lr": 0.0, "min": 149.5, "exact_by_kind": {"grids4": 0.964, "grids5": 0.908, "numbers3": 1.0, "numbers4": 1.0, "sums1": 1.0, "sums2": 1.0, "sums3": 1.0, "sums4": 0.999}, "de
MIN loop-s10 149.5
RUN plain-s10 log=0 dir=0 final=0 tests=0 evallog=0 train_proc=0 eval_proc=0
RUN loop-s11 log=0 dir=0 final=0 tests=0 evallog=0 train_proc=0 eval_proc=0
RUN plain-s11 log=0 dir=0 final=0 tests=0 evallog=0 train_proc=0 eval_proc=0
RUN loop-s12 log=0 dir=0 final=0 tests=0 evallog=0 train_proc=0 eval_proc=0
RUN plain-s12 log=0 dir=0 final=0 tests=0 evallog=0 train_proc=0 eval_proc=0
END-STATE
NOTE: sealed loop-s9 final.pt 30b43b4ffe9de370aa7b61f7547bb1e1f9fe0e6fe78496606747bc345bf710e5 (before any eval)
COPY loop-s9 30b43b4ffe9de370aa7b61f7547bb1e1f9fe0e6fe78496606747bc345bf710e5
NOTE: BensPC copy premonition-models/rsn358s/loop-s9/final.pt sha256 ok
NOTE: Mac copy ~/premonition-models/rsn358s/loop-s9/final.pt sha256 ok
NOTE: sealed plain-s9 final.pt 615d732413cd2dbe7fb59cdf94da937afe2c1e84d612a7cd5c1f1f8cd8de93fa (before any eval)
COPY plain-s9 615d732413cd2dbe7fb59cdf94da937afe2c1e84d612a7cd5c1f1f8cd8de93fa
NOTE: BensPC copy premonition-models/rsn358s/plain-s9/final.pt sha256 ok
NOTE: Mac copy ~/premonition-models/rsn358s/plain-s9/final.pt sha256 ok
NOTE: sealed loop-s10 final.pt 83b44ac19e7653d48353a351f66892b2f2f95a738a288624bc00ffa9a4cefb5e (before any eval)
COPY loop-s10 83b44ac19e7653d48353a351f66892b2f2f95a738a288624bc00ffa9a4cefb5e
NOTE: BensPC copy premonition-models/rsn358s/loop-s10/final.pt sha256 ok
NOTE: Mac copy ~/premonition-models/rsn358s/loop-s10/final.pt sha256 ok
rsn-358s run state at 2026-09-27T11:12:55Z (pass collect, kit 84917d07bb51fdc69e6993559f490a14989ffdbf)
loop-s9: FINISHED 30b43b4ffe9de370aa7b61f7547bb1e1f9fe0e6fe78496606747bc345bf710e5 minutes 150.0; not evaluated
plain-s9: FINISHED 615d732413cd2dbe7fb59cdf94da937afe2c1e84d612a7cd5c1f1f8cd8de93fa minutes 126.7; not evaluated
loop-s10: FINISHED 83b44ac19e7653d48353a351f66892b2f2f95a738a288624bc00ffa9a4cefb5e minutes 149.5; not evaluated
plain-s10: NOT STARTED; not evaluated
loop-s11: NOT STARTED; not evaluated
plain-s11: NOT STARTED; not evaluated
loop-s12: NOT STARTED; not evaluated
plain-s12: NOT STARTED; not evaluated
PASS-END collect 2026-09-27T11:12:55Z
06:47:58 stalled-go3 158-claude-sleep-358spc-finish opencode/muse-spark-1.3-contributor-free (no output in 15 min; resume 3/6 in 600 s)
06:53:35 go5 157-claude-sleep-358spc-collect opencode/muse-spark-1.3-contributor-free
06:57:58 go4 158-claude-sleep-358spc-finish opencode/muse-spark-1.3-contributor-free
07:08:36 stalled-go5 157-claude-sleep-358spc-collect opencode/muse-spark-1.3-contributor-free (no output in 15 min; resume 5/6 in 600 s)
rc=0
