Your M1 mouth build is queued — importing the sealed code and renting GPU.
Sealed spec confirmed. Now checking rental rules, ledger, and training code.
Ledger is clear (no rental spend recorded; $30 cap stands). Checking vast.ai account state read-only.
Account: credit $6.39, 0 instances running. Searching for RTX 5090 on-demand offers.
8 single-RTX 5090 offers available. Getting the cheapest.
Verifying the code seal against origin/main blobs (worktree checkout predates the seal commit, so checking the sealed blobs directly).
Seal verified 5/5 OK. Preparing the remote bundle.
Bundle staged. Attempting the rental (offer 19602471, $0.2129/h, ceiling $4.00/3h).
Offer already taken. Retrying with next-cheapest offers in order.
Rented: contract 52276394 (RTX 5090, $0.6096/h). Start ~18:28Z, 3h deadline 21:28Z. Waiting for boot.
Instance is broken host-side (CDI device error, never booted). Destroying and re-renting a different offer.
Second instance rented (contract 52276603, $0.4676/h). Waiting for boot.
Same host-side CDI failure. Destroying and trying another host.
Search cache is stale amid high churn. Fetching fresh and renting immediately in one pass.
Rented contract 52276877 ($0.4704/h). Waiting for boot.
Still initializing (image pull can take a while). Polling.
Host state is "running" (container still pulling/starting). Continuing to poll.
