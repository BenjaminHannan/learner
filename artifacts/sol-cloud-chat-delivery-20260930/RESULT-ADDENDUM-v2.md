The installed **user launcher** was also tested directly at **2026-09-30 11:35:00.913809 UTC**:

```cmd
C:\Users\benja\sol-cloud-chat-delivery-v1\CHAT.cmd --verify-only
```

It exited 0, printed “Sleep and training are disabled” and `verified: true`, and produced no stderr. The recorded launcher and CLI hashes match the frozen package. This checks the installed command and checkpoint/source admission; `--verify-only` performs **zero model calls and zero optimizer updates**. The earlier three actual model replies and their limits remain in the unchanged [RESULT-v1.md](RESULT-v1.md).

The optional metadata phase of this collection job failed later at its cache guard. That failure is preserved separately and occurred after the successful launcher check. It does not turn the recorded launcher result into a failed model delivery. No model run was repeated. Sleep remains disabled; general conversational quality remains unqualified.

The immutable source outbox is `8f55477f4c35fd1592bcd7808e0cbe7dd324407a`. [LAUNCHER-RESULT.json](launcher-verify-v2/cloud-pinned/LAUNCHER-RESULT.json) SHA256: `2d6bb19ef77b5c5973c77dc942a16c102c7efeed9ec1eb6aee78c3f4ae50805d`. The independent installed-command recount receipt is pinned at `9f8c740ffd84d9ffb34619e53b7134a891b6510321ba23f8f98853847ae777e1`.
