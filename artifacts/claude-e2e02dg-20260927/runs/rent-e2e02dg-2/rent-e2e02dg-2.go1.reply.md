0.2d-G rental job (ADDENDUM-52), pin d57d1904a656f664c2e19a196956b324f6e0fde7, results artifacts/claude-e2e02dg-20260927/vast2, skip hosts '483833', spent before $0.08, money stop $2.00, 2026-09-27T23:45:26Z
2026-09-27T23:45:28Z G's adapter on the Mac: /Users/ben-hannan/premonition-models/rd378g-vast-adapter, adapter_model.safetensors sha256 matches SEAL-run
2026-09-27T23:45:28Z credit $24.88
offers (5090; id $/h host card TFLOPS GPU-RAM-MB):
50134978 0.469 406325 RTX_5090 108.1 32607
52549114 0.47 467312 RTX_5090 107.6 32607
43165161 0.513 410852 RTX_5090 108.1 32607
2026-09-27T23:45:31Z CARD rental 1: instance 53061137 (offer 50134978, host 406325): RTX_5090, 108.1 TFLOPS, 32607 MB GPU RAM, $0.469/h (5090)
launched
2026-09-27T23:48:12Z box.sh launched on 53061137; time cap 55 min; money stop $2.00
  2026-09-27T23:48:12Z HOST nproc 16 disk 40G free; GPU NVIDIA GeForce RTX 5090, 32607, 595.58.03, 12.0
  2026-09-27T23:49:21Z TORCH-SOURCE download.pytorch.org/whl/cu128
  2026-09-27T23:49:32Z TORCH torch 2.11.0+cu128 12.8 True NVIDIA GeForce RTX 5090 transformers 5.17.0 peft 0.21.0 torchvision None
2026-09-27T23:50:32Z finished on the rental: yes; copying back W/
2026-09-27T23:50:38Z copy-back checked: 9 of 9 files match the rental's manifest
2026-09-27T23:50:51Z DESTROYED 53061137 (confirmed gone), spent $0.04
SUMMARY END DESTROYED finished=yes copyback=9/9 spent 0.04 (earlier attempts $0.08)
2026-09-27T23:48:12Z START
2026-09-27T23:48:12Z HOST nproc 16 disk 40G free; GPU NVIDIA GeForce RTX 5090, 32607, 595.58.03, 12.0
2026-09-27T23:49:21Z TORCH-SOURCE download.pytorch.org/whl/cu128
2026-09-27T23:49:32Z TORCH torch 2.11.0+cu128 12.8 True NVIDIA GeForce RTX 5090 transformers 5.17.0 peft 0.21.0 torchvision None
2026-09-27T23:49:59Z BASE /root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc
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
2026-09-27T23:49:59Z SELFTESTS E2E02DG-CHECKS-SELFTEST PASS 6/6 
2026-09-27T23:49:59Z FAILED a selftest failed (W/selftests.txt)
tree removed: /var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.pJ3rjwBB0j
rc=0
