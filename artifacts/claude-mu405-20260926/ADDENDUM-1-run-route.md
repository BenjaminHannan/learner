# mu-405 ADDENDUM-1: which run is registered (written 2026-09-26 18:54:47 UTC by date -u, before any output is read)

- The one registered run is the CPU run in the thread's cloud container, launched 2026-09-26 18:48:43 UTC
  (run/started.txt): sealed code, panel, facts and marks unchanged from 132260303 (sha256 -c 13/13 OK just before
  launch), arms N, K, W, H in that order, output in artifacts/claude-mu405-20260926/run/.
- Why the route changed: Ben 18:42 UTC said the vast money was gone (the rental was held at 18:43, 17da998d3), so the
  thread moved the run to free CPU. Ben 18:47 then restored a $30 pool; the Thread manager agreed at 18:54 that the CPU
  run stands and a rental would be a duplicate.
- The rental rent-mu405 had already launched at 18:44 UTC as vast instance 52799415 before the hold landed. The
  Director queued 000-stop-mu405 (179e22260) to stop it and destroy that instance with nothing copied back. Whatever
  that rental wrote is never read or scored. If any mu-405 run files ever appear on builder-outbox, they are ignored.
- Deviations of the registered run from the rental plan: CPU float32 instead of GPU bf16 (every arm on the same
  machine, so the comparison stays fair); torch 2.14.0+cpu, transformers 5.17.0 (run/started.txt). The marks, the
  judge text and the scorer are unchanged.
