Building lis-311 on base 292 — loading specs and staging the work.
Base 292 and plug-in 310 mapped — now checking test cases and the real-model setup.
Weights verified against the recorded hash — now confirming the reader pieces and test setup.
MPS works and deps resolve offline — checking load and ledger format.
Compiler path logic confirmed — now writing the 311 agent.
Simplifying a convoluted block I just wrote:
Now the try-out driver (stub equivalents + 30-turn real run):
Fixing the adaptive-yes bookkeeping (dead drain loop + flag):
Piloting the stub suite:
The Reader module itself needs extracting too — adding it to the deps:
Piloting the server pre-seal (will reset state before the registered check):
Server pilot passes with the real model — resetting state and sealing.
Sealed — running the registered stub suite:
Stub registered: 10/10. Checking resources before the real 30-turn run:
