Starting the report-only run — reading the rules and design first.
The referenced spec files aren't in this checkout — I'll pull them from the main branch.
I've got the contract and the store model. Setting up the work plan now.
Writes are fast (~16k/sec). Checking retract scaling at larger n before committing to the workload pattern.
Now the runner:
Cleaning up a leftover awkward expression in `crashchild`:
Smoke test with a tiny workload before sealing:
Seal written before the registered run. Now generating workloads:
20k write done: 6,081 facts/s, zero unexpected statuses. Cold opens and disk next:
One-hop perfect; 52 two-hop wrongs need investigation:
My one-liner bug (pickle opened in text mode). Retrying:
Still only 3 kills — checking whether those kills landed mid-write or during startup:
Suspicious — verifying what the clean-finished children actually wrote:
All children show exactly 20 acks — something stopped them early. Inspecting directly:
Fixed. Resealing and running the valid crash test:
All 30 killed mid-write, zero anomalies. Confirming kill-point spread:
Genuine mid-write kills. Now the tamper test:
Tamper 20/20 caught. Running the 100k size while the 1M workload generates:
1M write launched (15:27:47, 90-min cap → 16:57:47). Verifying the 100k two-hop wrongs while it runs:
Byte layout looks right. Checking 1M progress:
Memory 2.4GB and climbing — watching it. Drafting the report body with 20k/100k numbers while 1M runs:
Draft done. Monitoring the 1M run:
All numbers confirmed. Waiting on the 1M forget phase:
ETA now coincides with the cap — watching closely:
90-minute cap reached (158 events short of full completion). Stopping per the preregistered rule:
Assembling results.json while compression runs:
Filling the RESULTS.md placeholders — §4 (1M outcome) first:
Correcting the xz figure I can't know yet:
Now the final results.json:
Final verification, seal check, and size check:
Seal matches, all artifacts tiny. Cleaning up /tmp/nb320 and committing:
artifacts/ is gitignored but prior results were force-added. Staging exactly the tasked paths:
VERDICT: nb-320 baseline is exact but does not scale to 1M as built. 20k and 100k finished clean (0 unexpected statuses in 114,000 writes, 4,000/4,000 one-hop probes right, 30/30 mid-write SIGKILLs survived, 20/20 tamper flips caught). The 1M size is DID NOT FINISH — stopped at 90.3 min by the preregistered cap with 999,889/1,000,000 ops done. The cliff is the forget path: each retract re-indexes a ~1M-entry Python list (~100 ms), so 50k forgets ≈ 83 min of writing and every cold open replays the same cost (1.8 s at 20k → 59 s at 100k → ~2 h projected at 1M). Bytes per fact are flat (~465 B per FACT write, ~400 B per event). Commit ae3e5f02f holds the runner, workload generator, PASSMARKS.md, SEAL.sha256.txt, results.json, RESULTS.md. `git push` is blocked by this environment's policy — the commit is local and needs a push from outside.

Marks table (integer counts):

| check | 20k | 100k | 1M |
|---|---|---|---|
| fact writes SAVED / expected | 19,000/19,000 | 95,000/95,000 | 950,000/950,000 |
| unexpected write statuses | 0 | 0 | n/a (stopped pre-dump) |
| one-hop probes right / total | 2,000/2,000 | 2,000/2,000 | not run |
| two-hop probes right / total | 948/1,000 | 934/1,000 | not run |
| wrong-value / missing / answered-should-not / other | 0/0/0/0 | 0/0/0/0 | — |
| crash: acked-but-lost / dups / failed opens / torn | 0/0/0/0 (30 killed) | — | — |
| tamper flips caught / copies | 20/20 | — | — |

Every move: read contract + index + o0b schema; wrote workload generator (seed 3200, 3,754 tell/STATE templates, 77 relations, 30 functional) and pluggable runner (`--factory`, default `open_baseline`); sealed; generated 3 workloads to /tmp/nb320; 20k write (3.1 s, 6,081/s) → disk 8.83 MB → 3 cold opens (median 1.77 s) → probe (140 MB peak, one-hop p50 0.0045 ms) → gzip/xz refs → crash → tamper; 100k write (37.8 s, 2,516/s) → disk 44.37 MB → opens (median 59.14 s) → probe (566 MB peak) → refs; 1M write in background (killed at 90.3 min, 1,099,966/1,100,077 events, final line parses, RSS 1.0–3.2 GB); assembled results.json + RESULTS.md; deleted /tmp/nb320; committed.

Every miss/deviation: (1) 52 + 66 two-hop "wrongs" are probe-sampler artifacts — each verified equal to the contract-correct hop-1 multi join (118/118); store right in all 6,000 probes; runner left sealed. (2) Runner resealed 3× pre-1M, crash-driver only (missing-file guard; wait-for-first-ack before kill; multi-valued crash relation after finding the child wrote only ~41 events via CONFLICTs); workload generator byte-identical throughout; 4 void crash attempts reported, only the valid 30-kill run counts. (3) Probe seeds used were 20200/101000, not the preregistered 3200+N formula — deterministic, recorded. (4) xz refs via Python lzma (system xz binary broken); 1M probes/open skipped (projected ~2 h open, beyond total budget). (5) No file pushed over 5 MB (largest artifact 29 KB); notebooks/workloads lived only in /tmp/nb320, now deleted. (6) `git push` denied by environment — commit ae3e5f02f is local only.

What it means / doesn't mean, in plain high-school English: the notebook is a perfect librarian with instant recall (microseconds) and total honesty — nothing stored is ever lost, misremembered, or faked, crashes lose nothing, and any edit to history is detected. But forgetting is implemented by reshuffling the whole card catalog, so a million-fact notebook can't finish writing its forgets in 90 minutes and can't reopen in reasonable time. Squeezing bytes per fact (nb-321) is worth doing, but the reshuffle-on-forget must also be fixed before 1M facts on a laptop is real. None of this changes chat-answer quality — that was already shown to come from the reader, not storage — and every timing here was measured on a heavily loaded Mac (load 50–125), so read seconds as noisy, rankings as solid.
