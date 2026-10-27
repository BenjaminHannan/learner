# run_s0_benspc.ps1 -- S0 on BensPC (RTX 5070 Ti, Windows 11, PowerShell 5.1).
#
# This is the corrected form of README-S0.md section 3's PowerShell block.  Three things
# in that block are wrong for this machine and are fixed here:
#
#   1. `$py = "$repo\.venv\Scripts\python.exe"` does not exist on BensPC.  The interpreter
#      that has torch+CUDA is the system Python 3.10.9 at
#      C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe
#      (torch 2.11.0+cu128, sm_120 in the arch list, bf16 supported).  Nothing is installed.
#   2. The block never creates `$out`, and `--json "$out\throughput.json"` fails if the
#      folder is missing.
#   3. `kill-test` is documented as the GPU kill/resume test, but `kill_test()` in
#      fable_talker24_train.py hard-codes `--device cpu` in its `common` list, so the
#      built-in test can never touch the GPU.  A second, explicit CUDA kill/resume arm is
#      added below; the built-in CPU one is kept as well.
#
# It also assumes the one-line source patch to `perturb_gist` in fable_talker24_model.py
# (see S0-REPORT.md, "What was changed"): without it every CUDA run dies at step 1 with
# "Expected a 'cuda' device type for generator but found 'cpu'".
#
# Nothing here installs anything, touches ScoutLlamaServer, or starts a long run.

$ErrorActionPreference = "Continue"
$repo = "C:\Users\benja\talker24"
$py   = "C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe"
$art  = "$repo\artifacts\fable-talker24-20260920"
$out  = "$art\s0"
New-Item -ItemType Directory -Force -Path $out | Out-Null

$common = @("--device","cuda","--preset","S","--micro-batch","64",
            "--shards","$art\shards","--dialogues","$art",
            "--checkpoint-minutes","2","--checkpoint-steps","500","--log-every","25")

function Step($name) { Write-Output ""; Write-Output ("=== " + $name + " === " + (Get-Date -Format o)) }

Step "0 sizes"
& $py -B "$repo\scripts\fable_talker24_model.py" sizes

Step "1 autoencode S, 11 min"
& $py -B "$repo\scripts\fable_talker24_train.py" train --stage autoencode `
      --steps 1000000 --max-minutes 11 --out "$out\autoencode" @common
Write-Output "exit=$LASTEXITCODE"

Step "2 GRU-mouth side arm, 3 min"
& $py -B "$repo\scripts\fable_talker24_train.py" train --stage autoencode --gru-mouth `
      --steps 1000000 --max-minutes 3 --out "$out\autoencode-gru" @common
Write-Output "exit=$LASTEXITCODE"

Step "3 slots, 3 min"
& $py -B "$repo\scripts\fable_talker24_train.py" train --stage slots `
      --steps 1000000 --max-minutes 3 --out "$out\slots" @common
Write-Output "exit=$LASTEXITCODE"

Step "4 thinker through the frozen mouth, 3 min"
& $py -B "$repo\scripts\fable_talker24_train.py" train --stage thinker `
      --steps 1000000 --max-minutes 3 --out "$out\thinker" @common
Write-Output "exit=$LASTEXITCODE"

Step "5a kill test (built-in; CPU only -- kill_test() hard-codes --device cpu)"
& $py -B "$repo\scripts\fable_talker24_train.py" kill-test --out "$out\kill" `
      --preset tiny --steps 40 --die-at 18 --micro-batch 8
Write-Output "exit=$LASTEXITCODE"

Step "5b kill test on CUDA (the same three runs, --device cuda)"
$kc = @("--preset","tiny","--stage","autoencode","--steps","40","--seed","5",
        "--micro-batch","8","--checkpoint-steps","5","--log-every","10","--device","cuda")
Remove-Item -Recurse -Force "$out\kill-gpu" -ErrorAction SilentlyContinue
& $py -B "$repo\scripts\fable_talker24_train.py" train --out "$out\kill-gpu\uninterrupted" @kc
Write-Output "exit_A=$LASTEXITCODE"
& $py -B "$repo\scripts\fable_talker24_train.py" train --out "$out\kill-gpu\killed" --die-at 18 @kc
Write-Output "exit_B_killed=$LASTEXITCODE"
& $py -B "$repo\scripts\fable_talker24_train.py" train --out "$out\kill-gpu\killed" @kc
Write-Output "exit_B_resumed=$LASTEXITCODE"

Step "6a S0 model marks"
& $py -B "$repo\scripts\fable_talker24_train.py" eval `
      --checkpoint "$out\autoencode\final.pt" --n 512 --device cuda `
      --shards "$art\shards" --dialogues "$art" --json "$out\s0-marks.json"
Write-Output "exit=$LASTEXITCODE"

Step "6b the four section 3.4 interventions"
& $py -B "$repo\scripts\fable_talker24_interventions.py" report `
      --checkpoint "$out\autoencode\final.pt" --stage S0 --json "$out\interventions.json"
Write-Output "exit=$LASTEXITCODE"

Step "7 throughput M / L / XL at the design's batch 32 x length 48"
& $py -B "$repo\scripts\fable_talker24_train.py" bench --presets M L XL `
      --steps 20 --batch 32 --length 48 --device cuda --json "$out\throughput.json"
Write-Output "exit=$LASTEXITCODE"

Step "done"
nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv
