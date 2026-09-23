A demo evening with the loop117 assistant

How to read this: Ben speaks, the Agent answers. After each turn, one line explains what happened, in plain words.

Act 1. Starting from nothing.

Ben: Who is Mira's mother?
Agent: I don't know anyone called Mira.
It did not know, so it honestly said so.

Ben: Who is Keir's boss?
Agent: I don't know anyone called Keir.
It did not know, so it honestly said so.

Act 2. Ben teaches eight facts.

Ben: Mira's mother is Ana.
Agent: Saved: Mira's mother is Ana.
It wrote this fact in its notebook.

Ben: Ana's city is Porto.
Agent: Saved: Ana's city is Porto.
It wrote this fact in its notebook.

Ben: Mira's city is Lisbon.
Agent: Saved: Mira's city is Lisbon.
It wrote this fact in its notebook.

Ben: Mira's boss is Keir.
Agent: Saved: Mira's boss is Keir.
It wrote this fact in its notebook.

Ben: Keir's city is Bern.
Agent: Saved: Keir's city is Bern.
It wrote this fact in its notebook.

Ben: Mira is married to Theo
Agent: Saved: Mira's spouse is Theo.
It wrote this fact in its notebook.

Ben: Theo was created by Wren
Agent: Saved: Theo's creator is Wren.
It wrote this fact in its notebook.

Ben: Wren is a citizen of Norway
Agent: Saved: Wren's country of citizenship is Norway.
It wrote this fact in its notebook.

Act 3. Questions that join facts together.

Ben: What is Mira's mother's city?
Agent: Mira's mother's city is Porto.
It answered from its notes.

Ben: What is Mira's spouse's creator's country of citizenship?
Agent: Mira's spouse's creator's country of citizenship is Norway.
It answered from its notes.

Ben: Ivy is married to Owen
Agent: Saved: Ivy's spouse is Owen.
It wrote this fact in its notebook.

Ben: Owen was created by Petra
Agent: Saved: Owen's creator is Petra.
It wrote this fact in its notebook.

Ben: Petra is a citizen of Peru
Agent: Saved: Petra's country of citizenship is Peru.
It wrote this fact in its notebook.

Ben: The official language of Peru is Quechua
Agent: Saved: Peru's official language is Quechua.
It wrote this fact in its notebook.

[Director's note: this agent has no N-hop composer, so the four-hop question is not supported by this agent and is skipped here -- never faked.]

Ben: What is Mira's mother's city?
Agent: Mira's mother's city is Porto.
It answered from its notes.

Act 4. Forgetting one fact, then learning it again.

Ben: Where is Mira's city?
Agent: Mira's city is Lisbon.
It answered from its notes.

Ben: Forget Mira's city.
Agent: Forgotten: Mira's city.
It crossed this fact out of its notebook.

Ben: Where is Mira's city?
Agent: I don't know Mira's city.
It did not know, so it honestly said so.

Ben: Mira's city is Lisbon.
Agent: Saved: Mira's city is Lisbon.
It wrote this fact in its notebook.

Ben: Where is Mira's city?
Agent: Mira's city is Lisbon.
It answered from its notes.

Act 5. A wrong lesson the agent refuses.

Ben: Mira's city is Oslo.
Agent: I have Mira's city as Lisbon. Do you want me to change it to Oslo?
It refused to overwrite what Ben taught it, and said why.

Ben: Where is Mira's city?
Agent: Mira's city is Lisbon.
It answered from its notes.

Act 6. The agent talks about itself.

Ben: How many facts do you know?
Agent: I didn't understand that. Could you say it another way?
It did not understand, so it asked Ben to say it another way.

Ben: What did I teach you last?
Agent: I didn't understand that. Could you say it another way?
It did not understand, so it asked Ben to say it another way.

Ben: What is Tom's favourite number?
Agent: I don't know anyone called Tom.
It did not know, so it honestly said so.

Act 7. Overnight learning (live sleep).

[Director's note: this agent's sleeper has no word-episode feed (exp-104 style), so no new word can be installed overnight; the probes below check it honestly says so.]

Ben: Nora's mother is Ada.
Agent: (I dropped my earlier question.) Saved: Nora's mother is Ada.
It wrote this fact in its notebook.

Ben: Ada's mother is June.
Agent: Saved: Ada's mother is June.
It wrote this fact in its notebook.

Ben: Leo's mother is Mia.
Agent: Saved: Leo's mother is Mia.
It wrote this fact in its notebook.

Ben: Mia's mother is Zoe.
Agent: Saved: Mia's mother is Zoe.
It wrote this fact in its notebook.

Ben: June's city is Lyon.
Agent: Saved: June's city is Lyon.
It wrote this fact in its notebook.

Ben: Zoe's city is Nice.
Agent: Saved: Zoe's city is Nice.
It wrote this fact in its notebook.

Ben: Who is Nora's maternal grandmother?
Agent: I don't know Nora's maternal grandmother.
It did not know, so it honestly said so.

Ben: Who is Leo's maternal grandmother?
Agent: I don't know Leo's maternal grandmother.
It did not know, so it honestly said so.

Ben: Who is Rex's maternal grandmother?
Agent: I don't know anyone called Rex.
It did not know, so it honestly said so.

Act 8. How it compares with earlier measurements.

Earlier, the loop113b assistant faced 200 short edit questions: it answered 150 correctly, properly passed on 50, and got 0 wrong; on 200 long four-step questions it got 145 right, passed on 50, and got 5 wrong. Those numbers are read from its score file, not typed here.
A small open-weight model, asked the same kind of two-step questions 200 times with no notebook, got 52 right just by reading the question, 38 right with retrieved text, and 1 right after extra training. Those numbers are read from its results file, not typed here.
A third panel existed at run time and was read from its row files: fable_bench125_smollm_incontext_fable_edit_200_rows.jsonl: 200 rows, 52 correct, 148 wrong; fable_bench125_smollm_incontext_s2fresh_4hop_rows.jsonl: 200 rows, 52 correct, 148 wrong; fable_bench125_smollm_raglite_fable_edit_200_rows.jsonl: 200 rows, 41 correct, 159 wrong; fable_bench125_smollm_raglite_s2fresh_4hop_rows.jsonl: 200 rows, 33 correct, 167 wrong.

This conversation took 7 seconds.

