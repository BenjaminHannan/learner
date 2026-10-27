# rd-378L addendum E: retry after an environment failure (written 2026-09-26 15:21 UTC, before any note or score)

First try: rent-rd378L (commit 698c9aefc, rental 52757951, ~$0.69) wrote NO notes and scored nothing. Cause, checked
in the job's traceback and in transformers 5.17.0's source (image_utils.py imports torchvision only when
is_torchvision_available()): the job installed torch 2.11.0 over the rental image's torch 2.8.0 but left the image's
torchvision 0.23.0, built for torch 2.8; it fails to load ("operator torchvision::nms does not exist"), and
transformers' lazy imports then fail for every model class (LlamaConfig) and for peft (the job's ledger line blames
peft 0.21.0 itself; that is not right: peft 0.21.0 with transformers 5.17.0 and no torchvision imports and merges
fine, claude_rd378L_rebuild.py selftest). The writer did reach the rental with the right hash (Mac copy, dbcc8db5...).

The retry changes only the environment: after installing torch 2.11.0, torchvision and torchaudio are uninstalled
(nothing in this job uses images or audio), and an import check must pass before anything runs. Same commit's code,
same writer and hash rule (addendum D), same data, same commands, marks L1-L3 and the proved-wrong clause unchanged.
It shares one rental with rd-379q (sealed at 1ff783b75), each in its own process on the same GPU, to save money.
