# 119h code hashes (director, 2026-09-22 12:49)

The seal (SEAL.sha256.txt) covers PASSMARKS.md only, as in 119f/119g. These are the code files at acceptance, identical to the prefixes the agent printed right after sealing (transcript line 827) and to the copies staged on BensPC (certutil SHA256 checked for data/train/score/bat):

| file | sha256 |
|---|---|
| scripts/fable_ears119h_data.py | 93413c6d1926b7a8693d989bc5462bb64d8b108dc7cbb74a1a63385d553cfea1 |
| scripts/fable_ears119h_train.py | cbdbbc719ce68b3591e989dec9b74cd916dbb9c08313b06c2b4180d49f8c7089 |
| scripts/fable_ears119h_score.py | 67b166fc58d83f2edba27ddf517b516cc95659a2263a04b4622e46de1feda9cc |
| scripts/fable_ears119h_smoke.py | 20ebe7686e2b8d1423945faf16b1b811e69be22e5cd0b70705de5115e92d4d09 |
| scripts/fable_ears119h_wave.bat | 697f5290e4379c90b9387471264921c6c8a91e8835f5bd81268205079020116d |
| artifacts/fable-ears119h-20260922/scp119h.txt | 1dbc67587d25ddf012df0d2db47110da24501e6ce4a3ea9cf1bcbefacf827169 |
| design/v3/30-modes/119h-ears-build-muse.md | 8ddd5dead35d81dce2e27dc86f9b52414dce0566fb3500f256be7897d31470e3 |

Staging deviation (director): scp119h.txt says to mirror the whole C:\Users\benja\ears119g folder. I mirrored only repo\ plus panel94.jsonl and panel94b.jsonl, so the 119g checkpoints (runs\) are NOT in ears119h. If a 119h seed failed to train, the scorer must not silently find a 119g model there. The bat, scripts and inputs are unchanged. Wave launched 12:48:43.

Data-quality note (found in my spot-check of 20 generated sentences; not changed, since the build is sealed): birth and death dates are drawn independently, so some brackets have death before birth ("(1833-1827)", "(2 June 1938 - 28 February 1874)"). Position still tells birth from death, which is the cue real sentences use, so this is not expected to affect the occupation question. Fix it in the next generator revision if this line continues. The build doc also omits the 20 example sentences the brief asked for; my sample is on the board.
