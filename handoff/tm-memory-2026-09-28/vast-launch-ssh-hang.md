---
name: vast-launch-ssh-hang
description: vast kits must launch the rental run as `cd X && { setsid nohup ... & } ; echo launched`; without braces ssh never returns and the Mac guard never starts
metadata:
  type: feedback
  modified: 2026-09-27T14:46:06.951Z
---
`$SS "cd /root/r && setsid nohup bash drive.sh > log 2>&1 < /dev/null & echo launched"` puts the whole `cd && setsid` list in the background. Its subshell keeps ssh's stdout open until drive.sh ends, so ssh blocks for the whole run. Reproduced: 8.0 s for an 8 s job, 0.005 s with braces.

**Why:** 358u's vast start (kit sleep358uv/vstart.sh:55) stuck at "launched" (~14:04 UTC 09-27). $G/state was never written and the guard never started, so there was no money/time stop and no copy-back or destroy, and the collect job could not restart the guard. The same line was in the 358t v3 and 358s kits. Reported to the TM and Director 14:37 UTC by Everyday chat.

**How to apply:** in any vast kit, launch with braces (`{ setsid nohup ... & } ;`). Write the guard's state before any long remote call. Dry-run the start against a fake ssh that runs commands locally and check that it returns promptly while the fake run is still going. Related: [[thread-manager-spending]], [[everyday-chat-line]].
