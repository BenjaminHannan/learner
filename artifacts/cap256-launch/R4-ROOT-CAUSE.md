# capability256 r4 preflight failure: root cause (2026-09-30)

r4 (job sol-cloud-capability256-v1-s0-loop-train-r4, 20:50:26 to 20:52:39 UTC) stopped at
`resource_inventory` with "uncertain GPU process owner blocks exclusive-resource gate".
It never invoked the runner, made 0 model calls and did 0 optimizer updates. The PC has no
`run-capability256-v1/seed*/` output from r1 through r4.

The old gate (MAC-LAUNCH-v4.py) allowed a desktop GPU client only if nvidia-smi reported its
per-process memory as exactly `N/A`. NVIDIA driver 591.86 on BensPC prints `[N/A]`, with
brackets. So every desktop client counted as an unknown owner. A read-only replay of the old
rule on the PC (20 samples, 2 s apart, 2026-09-30 ~21:10 UTC) flagged all 31 clients every
time, including dwm.exe, explorer.exe, chrome.exe and claude.exe. The reminder server and Manim
were not on the GPU. The old failure receipt also dropped the list of flagged PIDs.

Fix: scripts/cap256_launch/pc_guard.py decides ownership from the interpreter, parent and
command line, not from the memory string. It blocks duplicate runners and Premonition or
model-server GPU holders, and still blocks when GPU memory is at or above 3000 MiB. Other
apps are allowed and listed in GUARD.json. Tests: tests/test_cap256_launch.py.
