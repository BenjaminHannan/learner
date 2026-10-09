---
name: vast-copy-from-stopped-box
description: How to get files off a STOPPED Vast box whose GPU is taken (restart refused): box-to-box copy_direct to a tiny helper box that prints the file to its log
metadata:
  type: reference
---

Worked 10-08 (custom reader/talker thread, T1SD_s201 checkpoint part off stopped box 54759829):
- Restarting a stopped box can fail with `resources_unavailable` ("state change queued") when someone else rented its GPU.
- Vast still copies files OUT of a stopped box: `PUT /api/v0/commands/copy_direct/` with {"client_id": "me", "src_id": OLD, "dst_id": HELPER, "src_path": "/job/res/", "dst_path": "/root/in/"} returned success and the helper showed "Done receiving copy" within a minute. Any container path works.
- Helper: cheapest reliable offer (~$0.06/h), image ubuntu:22.04, runtype args, a bash loop that waits for the file under /root/in, then prints it as RBEGIN|name|sha|size|job/run|k|n + base64 R| lines + REND (custom_io/box/ck_export.sh format) so `custom_io/box/vast.py collectck --id HELPER --out ... --want job/run` reassembles it. Script kept in the thread's scratchpad as cpy_dest.sh (not in repo).
- Then check the file's sha against the source's own record, destroy helper and old box.
Ben's standing rule (7:11 AM ET 10-08): a stopped box holding something we need -> move it off, then delete the box, without asking.
