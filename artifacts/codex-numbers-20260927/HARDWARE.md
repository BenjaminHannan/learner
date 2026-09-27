# Local execution record

SHOWN: MacBook Pro Mac15,7; Apple M3 Pro, 12 CPU cores, 36 GB memory. PyTorch 2.11.0 in an experiment-local arm64 Python 3.12 environment reports MPS built and available. No model weights were downloaded; the downloaded package was the PyTorch software runtime and its dependencies. Runs use MPS float32, with no autocast cache. CUDA, rentals, BensPC and the 1B model are not used.

Before each GPU job, the launcher checks the local process table for competing Python/ML training/inference jobs. The initial check found none. Ordinary display/compositor processes remain running; no process owned by another task is stopped. GPU utilization from ioreg includes display work and is not treated as evidence of model training by itself.

The unregistered benchmark used generated training puzzles only. 15 timed optimizer steps after warmup: width64/batch64 0.0286 sec; width128/batch64 0.0314 sec; width128/batch128 0.0433 sec. These are short throughput measurements, not accuracy evidence or guaranteed sustained runtime. Raw values: diagnostics/throughput.json.

Usage checked before work: 81% remaining; after setup: 80% remaining. The experiment stops if account usage falls below 20% remaining, as instructed.
