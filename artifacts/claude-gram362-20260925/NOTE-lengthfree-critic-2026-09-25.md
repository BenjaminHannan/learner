# Note: can the 1B judge its own chat grammar once length is taken out? (grammar thread, 2026-09-25 ~20:00 UTC)

Report only, not a registered experiment. Asked because Fix sleep wants a checker for chat practice at night, and
gram-362's critic mostly learned "shorter is safer" (VERIFY-362.md). CPU, no new model, no test panel touched.

Data: gram-362's training set only (train/: 320 prompts x 4 drafts = 1,280 MiniCPM5-1B drafts, label = clean by both
blind graders, 945 clean). Features from scripts/claude_gram362_train.py (12 word-probability stats; hidden state at
layers -8 and -1). Length removed by regressing every feature on log tokens and keeping the residual. Logistic
regression, 5 folds by prompt, seed 3621.

| Critic | prompts whose top pick is clean (of 320) | same-length pair accuracy | correlation of score with length |
|---|---|---|---|
| first draft (today) | 241 | - | - |
| stats (gram-362's critic) | 266 | 0.567 | -0.61 |
| stats, length removed | 251-252 | 0.557-0.571 | 0.0 |
| hidden state, length removed | 254-261 | 0.507-0.591 | 0.12-0.30 |
| stats + hidden, length removed | 256-260 | 0.527-0.591 | 0.12-0.29 |
| perfect picker | 311 | - | - |

Same-length pair accuracy: for pairs of drafts to the same prompt, one clean and one not, within a few tokens of each
other, how often the critic scores the clean one higher (0.5 = coin flip). Mean draft length 66.8 tokens.

What it says: with length out, the 1B's own signals tell a clean draft from a broken one of the same length only a
little better than a coin (0.51 to 0.59). Most of gram-362's gain came from preferring short drafts.

What it means for sleep: a self-signal critic is not a safe night checker for chat. Used as a reward, it would teach
the model to write shorter and emptier replies, not cleaner ones. Chat practice at night should use labels made by
day (two blind graders on the 1B's own drafts, as gram-362's train/ set) or no chat grammar reward at all.
Chat grammar itself stays stopped at 90% (Ben, 11:02 UTC).
