# HANDS practice gym

Nine deterministic, randomized browser task families: named buttons, text entry
and submit, dropdowns, popup dismissal, slider dragging, links, menu selection,
checkboxes, and two-field forms. They run inside local HTML pages in real
headless Chromium on Windows and macOS. No desktop inputs, recordings, external
websites, Glim changes, or game processes are involved.

The observation is a screenshot resized to 320×180, a 192×192 screenshot crop
around the last mouse point, the instruction's signed 64-token hash, and twelve
zero proprioception values. The policy never receives DOM state, reward-check
metadata, target coordinates, task IDs, or test oracle selectors. The environment
uses DOM state only for automatic rewards. Test oracle selectors prove that each
task is solvable; they are not training data.

## Install and run

Use Python 3.10–3.12 for PyTorch compatibility. Browser workers alone need only
`requirements.txt`; CUDA training also needs `requirements-train.txt`. In this directory:

```sh
python -m venv .venv
# Windows: use .\venv\Scripts\python.exe instead of python below.
python -m pip install -r requirements-train.txt
python -m playwright install chromium
python -m hands_gym.train --seeds 11 22 33 --updates 200 --envs 8 --eval-episodes 16
```

On BensPC the existing environment is `C:\Users\benja\hands-gym\venv`.
The default training device is CUDA. `--device cpu` supports smoke checks only.
`--native-checkpoint PATH` accepts a strict NativeActionPolicy state dictionary;
without it the starting policy is freshly initialized. `--resume-checkpoint PATH`
continues from a gym state dictionary with a fresh optimizer; it is mutually
exclusive with native initialization. Checkpoints stay in this
gym; no production policy is promoted or overwritten.

The HANDS CNN, overview/detail projections, 512-unit GRUCell and original native
action heads match `src/night-learn/pixel_model.py`. The gym adds categorical
24×14 start/end position heads and a scalar baseline. This supplies exploration
for PPO; it is **not** a drop-in production native-action checkpoint. The original
sigmoid position and scroll heads are retained for native checkpoint loading;
the PPO run learns kind, start/end cells, and keyboard logits. Scroll amplitude
is currently fixed. GRU state resets each observation in this first experiment.
Actions are click, drag, key or scroll dictionaries. Coordinates are normalized
until the browser adapter converts them to pixels. Gym keyboard codes are ASCII
plus 128=Enter, 129=Backspace, 130=Tab, 131=Escape; these are gym vocabulary IDs,
not a claim about macOS hardware key codes. There are no task-specific action
masks or scripted motor sequences.

PPO uses GAE, a value baseline, clipped ratios, gradient clipping, small batches,
and an entropy bonus. The initial curriculum emphasizes closing popups. The last
30% mixes in other families. All seven requested families have independent
held-out measurements, including zeros. A short run is a proof that reward can
improve this policy, not a claim that all seven families have been mastered.
The slider is a DOM pointer control with fixed geometry on both operating
systems, and success requires a drag event as well as the target value.
Evaluation uses paired stochastic action RNG and fixed high-range task seeds,
disjoint from training's low-range task seeds. Different runs use independent
initialization, training, and evaluation seeds. `curve.json` records training
success and throughput; `result.json` records held-out baseline/final numbers.

To audit frozen initial/final policies and record native-action traces:

```sh
python -m hands_gym.evaluate --run runs/proof --output runs/audit --episodes 32
```

The audit writes per-episode JSONL with layout seed, instruction, native actions,
terminal success state, and initial/final screenshot hashes. It does not fit any
weights. Use `--device cpu` to audit without taking the GPU lease.

## Checks

From `desk/` on macOS:

```sh
HANDS_GYM_BROWSER_TESTS=1 src/hands-gym/.venv/bin/python test/hands-gym.test.py
```

On BensPC the deployed test is `test_hands_gym.py`:

```powershell
$env:HANDS_GYM_BROWSER_TESTS='1'
.\venv\Scripts\python.exe test_hands_gym.py
```

The suite checks rewards/timeouts, repeatability and randomization, stochastic
policy gradients, screenshot transport, all nine tasks with actual coordinate
mouse/keyboard input, and a loopback remote worker. Mac browser checks validate
the gym, not the Premonition Mac app.

## GPU ownership

`gpu_gate.Lease` refuses foreign CUDA clients, elevated GPU activity or large
existing allocation, and atomically creates `GPU-OWNER.json` in this directory.
Windows WDDM reports graphics clients as compute clients; only explicitly listed
normal desktop applications are exempt. Do not delete another live owner's
lease. Coordinate with HANDS-PC: inspect `nvidia-smi`, wait while it trains, and
never start a second GPU job. Browser-only workers use `--disable-gpu`.
No stale lease is removed automatically, no PID is killed, and paused jobs are
never resumed. The short proof saves `latest.pt` every ten PPO updates.

## Extra workers and Bedwars later

`python -m hands_gym.env_server --host 127.0.0.1 --port 8765` starts CPU browser
workers. Use an SSH tunnel for another machine; the transport has no auth and
should stay on loopback. `--remote-endpoints 127.0.0.1:8765` in the trainer uses
one of its `--envs` slots remotely; repeat endpoints for several environments.
The reset protocol carries the episode horizon. JSON screenshots support up to
2 MiB messages. The loopback integration test exercises the actual transport.
No remote endpoint is configured for the proof, and Brick's PC is never used.

`interfaces.PracticeEnvironment` is the extension boundary for a future Bedwars
adapter: reset produces screenshot observations and an instruction, step accepts
a native action and returns observation/reward/done/info. No Minecraft dependency
or launch logic is present.

`pc.py` is a Mac-side transport helper. It uses the SSH alias `benspc-lan`,
PowerShell UTF-16LE EncodedCommand and Python source over stdin. It logs the
actual command/source, stdout, stderr and exit code to the requested local file.
