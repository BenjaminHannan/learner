{"job": "sol-translator-human-v4-s0-pc", "seed": 0, "utc": "2026-09-30T04:05:33Z", "stage": "TRAIN", "package_sha256": "f3211f2a3ec426e345f896f21dd30291e474e8ad357fb3a39e5cb89e6b864259", "seal_sha256": "f2ced550e6f7ab743e2f471ae359ecfaf1b7cbd5dc76fd999140b6d986d4d6da", "resume": false, "no_dev_scoring": true, "precision_policy": "full frozen FP32 LFM including embedding/head; reader/core FP32; actual tensor dtypes/VRAM recorded"}

{"status": "FAILED before TRAIN", "seed": 0, "error_type": "ValueError", "error": "frozen model hash mismatch", "source_sha256": "d5f09b1dfbc65e4e018081be71305e7440468d869114f2205e2565a3e646a085", "wrapper_sha256": "e74bf7dce402c0862e0d2ddcf6cb9b68c9b6db820aa42ac1ae48ca0bb8682684", "probe_sha256": "e61b292892669f8175129dc0afa9ec6e9507db396072efc13d35dba21f7813ff", "optimizer_steps": 0, "precision": "FULL FP32; no BF16 fallback", "wall_seconds": 2.0}
Traceback (most recent call last):
  File "C:\Users\benja\sol-translator-human-v4\scripts\sol_translator_pc_preflight_v4.py", line 41, in <module>
    p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--source',required=True);p.add_argument('--seed',required=True,type=int,choices=(0,1));p.add_argument('--out',required=True);p.add_argument('--device',default='cuda');run(p.parse_args())
  File "C:\Users\benja\sol-translator-human-v4\scripts\sol_translator_pc_preflight_v4.py", line 25, in run
    lm,tok,_=load_local_lm(p,pp,a.device)
  File "C:\Users\benja\sol-translator-human-v4\scripts\sol_translator_english_v3.py", line 133, in load_local_lm
    raise ValueError('frozen model hash mismatch')
ValueError: frozen model hash mismatch
{"returncode": 1, "seed": 0, "wall_seconds": 5.172000000005937, "paths_and_hashes": {"artifacts\\sol-translator-20260929\\ground-v3-s0\\LAUNCH.json": "b727152fffda62c0b93c8b198b91532011f594be14f5996cfb987a9866701f7d", "artifacts\\sol-translator-20260929\\ground-v3-s0\\LFM-provenance.json": "ec5d42dc87c2f2d8a25168de33b5c8324c8f777f75e7c1b69b8c6205fe97bee8", "artifacts\\sol-translator-20260929\\ground-v3-s0\\MEMORY-FAILURE.json": "8de467598e48d7aa1252b8beccbbd894c8709121a5a8445441ced31c80e6e6c9"}, "stage": "TRAIN only; no DEV scored", "first_weight_estimate": "use measured DURABLE-TRAIN-WEIGHTS stdout; no speculative success", "sleep_updates": 0}
Traceback (most recent call last):
  File "<stdin>", line 12, in <module>
  File "C:\Users\benja\sol-translator-human-v4\scripts\sol_translator_deploy_v4.py", line 35, in run
    subprocess.run([sys.executable,'-B','scripts/sol_translator_pc_preflight_v4.py','--model',lm,'--source',str(own/f'seed-sources/qualified-source-s{a.seed}.pt'),'--seed',str(a.seed),'--out',str(work),'--device','cuda'],check=True,env=env,timeout=350)
  File "C:\Users\benja\AppData\Local\Programs\Python\Python310\lib\subprocess.py", line 526, in run
    raise CalledProcessError(retcode, process.args,
subprocess.CalledProcessError: Command '['C:\\Users\\benja\\lis300\\venv\\Scripts\\python.exe', '-B', 'scripts/sol_translator_pc_preflight_v4.py', '--model', 'C:/Users/benja/.cache/huggingface/hub/models--LiquidAI--LFM2.5-1.2B-Instruct/snapshots/0f604ada3f766f9f257460c4c9f0b5d6f69d431b', '--source', 'C:\\Users\\benja\\sol-translator-human-v4\\artifacts\\sol-translator-20260929\\seed-sources\\qualified-source-s0.pt', '--seed', '0', '--out', 'C:\\Users\\benja\\sol-translator-human-v4\\artifacts\\sol-translator-20260929\\ground-v3-s0', '--device', 'cuda']' returned non-zero exit status 1.
rc=1
