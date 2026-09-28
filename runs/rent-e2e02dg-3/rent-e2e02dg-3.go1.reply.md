0.2d-G rental job (ADDENDUM-52), pin 32b700b63fb213105fdc23fe7cac741444885526, results artifacts/claude-e2e02dg-20260927/vast3, skip hosts '483833', spent before $0.12, money stop $2.00, 2026-09-27T23:56:26Z
2026-09-27T23:56:28Z G's adapter on the Mac: /Users/ben-hannan/premonition-models/rd378g-vast-adapter, adapter_model.safetensors sha256 matches SEAL-run
2026-09-27T23:56:29Z credit $24.74
offers (5090; id $/h host card TFLOPS GPU-RAM-MB):
45043239 0.469 406325 RTX_5090 108.1 32607
52925149 0.47 467312 RTX_5090 107.6 32607
44614428 0.473 410852 RTX_5090 109.1 32607
2026-09-27T23:56:31Z CARD rental 1: instance 53062886 (offer 45043239, host 406325): RTX_5090, 108.1 TFLOPS, 32607 MB GPU RAM, $0.469/h (5090)
launched
2026-09-27T23:58:02Z box.sh launched on 53062886; time cap 55 min; money stop $2.00
  2026-09-27T23:58:02Z HOST nproc 16 disk 40G free; GPU NVIDIA GeForce RTX 5090, 32607, 580.105.08, 12.0
  2026-09-27T23:59:34Z TORCH torch 2.11.0+cu128 12.8 True NVIDIA GeForce RTX 5090 transformers 5.17.0 peft 0.21.0 torchvision None
  2026-09-28T00:00:09Z MERGE1 a0fb1c9bd663b00b1470d515ae0c38a8dd3ed7d1cfdead70325137312300d1ed (want a0fb1c9bd663b00b1470d515ae0c38a8dd3ed7d1cfdead70325137312300d1ed) adapter dtypes F32
  2026-09-28T00:05:08Z W1 PASS 504 of 504 turns equal; report only: build vs rental 504 of 504 
2026-09-28T00:06:18Z finished on the rental: yes; copying back W/
2026-09-28T00:06:25Z copy-back checked: 23 of 23 files match the rental's manifest
2026-09-28T00:06:37Z DESTROYED 53062886 (confirmed gone), spent $0.08
SUMMARY END DESTROYED finished=yes copyback=23/23 spent 0.08 (earlier attempts $0.12)
2026-09-27T23:58:02Z START
2026-09-27T23:58:02Z HOST nproc 16 disk 40G free; GPU NVIDIA GeForce RTX 5090, 32607, 580.105.08, 12.0
2026-09-27T23:59:20Z TORCH-SOURCE download.pytorch.org/whl/cu128
2026-09-27T23:59:34Z TORCH torch 2.11.0+cu128 12.8 True NVIDIA GeForce RTX 5090 transformers 5.17.0 peft 0.21.0 torchvision None
2026-09-28T00:00:02Z BASE /root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc
E2E02D 4870333c7ad562f5635b09b7b92629f6fd26cb30b9de5e0f3779891de33a3929 want 4870333c7ad562f5635b09b7b92629f6fd26cb30b9de5e0f3779891de33a3929
RD378G-SEAL 13 of 14
WRITER scripts/claude_rd378_common.py: OK scripts/claude_rd378_write.py: OK 
ADAPTER README.md OK
ADAPTER adapter_config.json OK
ADAPTER adapter_model.safetensors OK
ADAPTER chat_template.jinja OK
ADAPTER tokenizer.json OK
ADAPTER tokenizer_config.json OK
RENTAL-NOTES dc49c788d63424620aff80c1ae25383ff45b7c81ec90bc0ab76f584bba73b6e1 vs dc49c788d63424620aff80c1ae25383ff45b7c81ec90bc0ab76f584bba73b6e1
2026-09-28T00:00:03Z SELFTESTS E2E02D-WIRING-SELFTEST PASS 20/20 E2E02DG-WIRING-SELFTEST PASS 25/25 E2E02DG-CHECKS-SELFTEST PASS 6/6 
2026-09-28T00:00:09Z MERGE1 a0fb1c9bd663b00b1470d515ae0c38a8dd3ed7d1cfdead70325137312300d1ed (want a0fb1c9bd663b00b1470d515ae0c38a8dd3ed7d1cfdead70325137312300d1ed) adapter dtypes F32
2026-09-28T00:05:08Z W1 PASS 504 of 504 turns equal; report only: build vs rental 504 of 504 
2026-09-28T00:05:52Z W2 PASS (99 of 99 turns' pointers ok; recall 0 non-heard rows in 1470); W2b PASS (99 of 99)
2026-09-28T00:06:09Z timing: median turn ms without G 348.1 with G 859.5
2026-09-28T00:06:09Z DONE
tree removed: /var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.RnawjzY5X8
rc=0
