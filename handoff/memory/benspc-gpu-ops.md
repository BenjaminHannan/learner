---
name: benspc-gpu-ops
description: "How the Qwen llama-server on BensPC respawns, how it was stopped, how to restore it, and how to run PowerShell/Python over SSH without quoting breakage"
metadata: 
  node_type: memory
  type: reference
  originSessionId: daf7c42e-d7f3-43b9-ae1e-ebd0fe3a6e26
  modified: 2026-09-18T11:17:35.488Z
---

- The Qwen3.8-27B `llama-server.exe` (port 8081, ~14 GB VRAM) is launched by `C:\llama\serve-8081.bat`, a `goto loop` restart wrapper (15 s delay) started by scheduled task `ScoutLlamaServer` (ONLOGON). Killing only the server PID is useless: it respawns within ~15 s.
- 2026-09-18: with Ben's authorization, stopped the cmd.exe running serve-8081.bat and then the Qwen server; GPU went to ~15.3 GB free. It stays down until next logon. Restore with `schtasks /run /tn ScoutLlamaServer` on BensPC.
- 2026-09-18 (later): at Ben's request, **disabled** the ScoutLlamaServer task so Qwen no longer autostarts at logon (frees the GPU for training). Re-enable with `Enable-ScheduledTask -TaskName ScoutLlamaServer` (then `schtasks /run /tn ScoutLlamaServer` to start it now).
- SSH quoting: send PowerShell as `powershell.exe -NoProfile -NonInteractive -EncodedCommand <base64 UTF-16LE>`. Windows PowerShell 5.1 strips double quotes from native-exe args, so pass Python code via stdin (`$code | & python.exe -B -`), not `-c`.
- BensPC env (measured 2026-09-18): Python 3.10.9, torch 2.11.0+cu128, cuDNN 9.19, RTX 5070 Ti sm_120 present in arch list.

Related: [[gpt-bridge-serial-only]]
- **Fast Qwen config for batch jobs (measured 2026-09-18):** `C:\llama-b10679\llama-server.exe -m C:\Users\benja\.lmstudio\models\Qwen3.8-27B\Qwen3.8-27B-UD-IQ4_XS.gguf --host 127.0.0.1 --port 8081 -c 16384 -ngl 99 -fa 1 --cache-type-k q8_0 --cache-type-v q8_0 --spec-type draft-mtp --spec-draft-n-max 2 --parallel 1 -t 6` gives ~69 tok/s single stream (88 aggregate with 2 client threads) on ~1,100-token prompts, and 0.16 s per short yes/no check. The autostart config (q4_0 V cache, `--parallel 4`) collapsed to ~5 tok/s per slot on the same prompts. Start it detached via `Invoke-CimMethod Win32_Process Create` with `cmd /c ... >> C:\llama\server-8081-premonition.log`, and reach it from the Mac with `ssh -N -L 18081:127.0.0.1:8081 benspc` (the Tailscale link drops sometimes, so wrap it in a restart loop). Stop it before GPU training: it uses ~15 GB of VRAM.
- **VRAM spill signature (seen 2026-09-22, exp 235).** When a training run creeps to ~15.9 of 16.3 GB, Windows WDDM spills into shared system RAM over PCIe. The run doesn't crash; it just crawls. The signs are nvidia-smi showing "100 %" utilisation at only ~78 W (real compute draws 250 W+), with step time jumping 4x (0.59 → 2.4 s/step). Fix: the same effective batch via a smaller micro-batch plus gradient accumulation. SmolLM2-360M full fine-tune: micro-batch 16 × 2 gives a 10.8 GB peak and 0.25 s/step. Check `nvidia-smi --query-gpu=memory.used,power.draw --format=csv` early in every GPU run.
