# The clip-on patch

Construction description; learning benefits remain **untested**.

The ordinary core adds the embedded puzzle to its working state, applies two
width-256 transformer blocks, and normalizes the result. The patch arm reduces
each block's MLP width from 1,024 to 896. Its recurrent update is

`h_next = F(h, x) + 0.25 * sigmoid(gate([embed(x), h])) * B A h`.

A has shape 8 by 256 and B has shape 256 by 8. These 4,096 persistent
coefficients belong to the learner, not a particular puzzle. Working state h
starts at zero for each puzzle. In particular, the patch has no effect in round
one; it first changes reasoning from round two onward. No kind label is passed
to the embedding, gate, writer, or recurrent core.

After a support correction, the writer receives the mean hidden activation at
answer slots and the mean `(one_hot(correct) - predicted_probabilities)`
projected through the answer head's weight matrix. Each of eight learned rank
slots offsets that activity vector. A shared 512-to-128-to-512 MLP produces
one proposed A row and one proposed B column per slot. This is a correction
signal, not a stored answer string. Queries have no target argument.

Writer outputs use tanh, scaled by `1/sqrt(8*256)`. Each write uses
`A = 0.9*A + 0.1*A_proposal` and the same rule for B, with a defensive bound
at that same coefficient limit. Thus each factor's Frobenius norm is at most
one, and the patch's operator norm is at most 0.25. The low-rank product itself
is linear; there is no extra tanh on `B A h`. The normalized ordinary core and
this gain bound prevent the patch alone from causing unbounded recurrence.

The writer MLP has 131,712 parameters, the rank slots 2,048, and the gate 513.
The reduced block MLPs save 131,328 parameters. Including the persistent patch,
the net is 7,041 coefficients larger than our loop control. CHECKS.md gives
the complete table and numerical evidence, without claiming learning success.

The caller explicitly carries a PatchState across supports and kind changes.
No method changes ordinary parameters during a write. During practice, the
outer optimizer credits the last two writes only through different query and
retention examples. During the requested few-example ladder, ordinary weights
must remain frozen. That race awaits its external sealed protocol.
