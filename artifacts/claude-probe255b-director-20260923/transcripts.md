# Director probe 255b transcripts (side by side, no judging)

Fresh daemon per dialog; stored triples sorted after every turn.

## D1

### D1 turn 0 (reply SAME, stored SAME)

- user: Ana's boss is Tobin.
- 138m reply: Saved: Ana's boss is Tobin.
- 255b reply: Saved: Ana's boss is Tobin.
- 138m stored: [["Ana", "boss", "Tobin"]]
- 255b stored: [["Ana", "boss", "Tobin"]]

### D1 turn 1 (reply DIFF, stored SAME)

- user: whos anas boss tho
- 138m reply: I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."
- 255b reply: I couldn't save that as a fact. I don't know that kind of sentence yet. Could you say it another way? For example: "Kim's boss is Lee."
- 138m stored: [["Ana", "boss", "Tobin"]]
- 255b stored: [["Ana", "boss", "Tobin"]]

### D1 turn 2 (reply SAME, stored SAME)

- user: who is ana's bos
- 138m reply: I don't know Ana's bos.
- 255b reply: I don't know Ana's bos.
- 138m stored: [["Ana", "boss", "Tobin"]]
- 255b stored: [["Ana", "boss", "Tobin"]]

## D2

### D2 turn 0 (reply SAME, stored SAME)

- user: My name is Corla.
- 138m reply: Saved: your name is Corla.
- 255b reply: Saved: your name is Corla.
- 138m stored: [["USER", "name", "Corla"]]
- 255b stored: [["USER", "name", "Corla"]]

### D2 turn 1 (reply DIFF, stored SAME)

- user: whats my nmae?
- 138m reply: I didn't understand that question — could you say it another way?
- 255b reply: I didn't understand that. Could you say it another way?
- 138m stored: [["USER", "name", "Corla"]]
- 255b stored: [["USER", "name", "Corla"]]

### D2 turn 2 (reply SAME, stored SAME)

- user: Do u know what im called
- 138m reply: Your name is Corla.
- 255b reply: Your name is Corla.
- 138m stored: [["USER", "name", "Corla"]]
- 255b stored: [["USER", "name", "Corla"]]

## D3

### D3 turn 0 (reply DIFF, stored SAME)

- user: How many turns have we had?
- 138m reply: We have had 1 turns.
- 255b reply: We have had one turn.
- 138m stored: []
- 255b stored: []

### D3 turn 1 (reply DIFF, stored SAME)

- user: Have you slept?
- 138m reply: No. I have slept 0 times.
- 255b reply: No. I haven't slept yet.
- 138m stored: []
- 255b stored: []

### D3 turn 2 (reply DIFF, stored SAME)

- user: How many facts do you know?
- 138m reply: I know 0 facts you taught me. I also hold 0 web row, which I do not believe.
- 255b reply: You haven't taught me any facts yet. I don't hold any web rows.
- 138m stored: []
- 255b stored: []

## D4

### D4 turn 0 (reply DIFF, stored SAME)

- user: Did you ask me to clarify anything?
- 138m reply: I didn't understand that question — could you say it another way?
- 255b reply: I didn't understand that. Could you say it another way?
- 138m stored: []
- 255b stored: []

### D4 turn 1 (reply DIFF, stored SAME)

- user: How many questions have you answered?
- 138m reply: I have answered 0 questions.
- 255b reply: I haven't answered any questions yet.
- 138m stored: []
- 255b stored: []

### D4 turn 2 (reply SAME, stored SAME)

- user: Tell me about yesterday.
- 138m reply: I don't know anyone called yesterday.
- 255b reply: I don't know anyone called yesterday.
- 138m stored: []
- 255b stored: []

## D5

### D5 turn 0 (reply SAME, stored SAME)

- user: Pim's city is Oslo.
- 138m reply: Saved: Pim's city is Oslo.
- 255b reply: Saved: Pim's city is Oslo.
- 138m stored: [["Pim", "city", "Oslo"]]
- 255b stored: [["Pim", "city", "Oslo"]]

### D5 turn 1 (reply DIFF, stored SAME)

- user: where Pim live at
- 138m reply: I didn't understand that question — could you say it another way?
- 255b reply: I didn't understand that. Could you say it another way?
- 138m stored: [["Pim", "city", "Oslo"]]
- 255b stored: [["Pim", "city", "Oslo"]]

### D5 turn 2 (reply SAME, stored SAME)

- user: Where does Pim live?
- 138m reply: Pim's city is Oslo.
- 255b reply: Pim's city is Oslo.
- 138m stored: [["Pim", "city", "Oslo"]]
- 255b stored: [["Pim", "city", "Oslo"]]

## D6

### D6 turn 0 (reply DIFF, stored SAME)

- user: Who talked to you besides me?
- 138m reply: I didn't understand that question — could you say it another way?
- 255b reply: I didn't understand that. Could you say it another way?
- 138m stored: []
- 255b stored: []

### D6 turn 1 (reply SAME, stored SAME)

- user: whats ur name
- 138m reply: You never told me your name, so I do not know it.
- 255b reply: You never told me your name, so I do not know it.
- 138m stored: []
- 255b stored: []

### D6 turn 2 (reply SAME, stored SAME)

- user: Tobin's dog is Rufus.
- 138m reply: Saved: Tobin's dog is Rufus.
- 255b reply: Saved: Tobin's dog is Rufus.
- 138m stored: [["Tobin", "dog", "Rufus"]]
- 255b stored: [["Tobin", "dog", "Rufus"]]

### D6 turn 3 (reply DIFF, stored SAME)

- user: rufus belongs to who
- 138m reply: I couldn't save that as a fact. I don't know that shape yet. Could you say it another way, like "Kim's boss is Lee."
- 255b reply: I couldn't save that as a fact. I don't know that kind of sentence yet. Could you say it another way? For example: "Kim's boss is Lee."
- 138m stored: [["Tobin", "dog", "Rufus"]]
- 255b stored: [["Tobin", "dog", "Rufus"]]

## D7

### D7 turn 0 (reply SAME, stored SAME)

- user: Kell's teacher is Mara.
- 138m reply: Saved: Kell's teacher is Mara.
- 255b reply: Saved: Kell's teacher is Mara.
- 138m stored: [["Kell", "teacher", "Mara"]]
- 255b stored: [["Kell", "teacher", "Mara"]]

### D7 turn 1 (reply DIFF, stored SAME)

- user: Mara teaches who?
- 138m reply: I didn't understand that question — could you say it another way?
- 255b reply: I didn't understand that. Could you say it another way?
- 138m stored: [["Kell", "teacher", "Mara"]]
- 255b stored: [["Kell", "teacher", "Mara"]]

### D7 turn 2 (reply DIFF, stored SAME)

- user: who's kell's teachr
- 138m reply: I didn't understand that question — could you say it another way?
- 255b reply: I didn't understand that. Could you say it another way?
- 138m stored: [["Kell", "teacher", "Mara"]]
- 255b stored: [["Kell", "teacher", "Mara"]]

## D8

### D8 turn 0 (reply DIFF, stored SAME)

- user: Have you stored any web rows?
- 138m reply: I didn't understand that question — could you say it another way?
- 255b reply: I didn't understand that. Could you say it another way?
- 138m stored: []
- 255b stored: []

### D8 turn 1 (reply DIFF, stored SAME)

- user: Hello!
- 138m reply: Hi! Teach me like "Tom's boss is Ann." Ask me like "Who is Tom's boss?"
- 255b reply: Hi! I'm Premonition. You can teach me a fact, for example: "Tom's boss is Ann." Then you can ask me about it, for example: "Who is Tom's boss?"
- 138m stored: []
- 255b stored: []

### D8 turn 2 (reply DIFF, stored SAME)

- user: How many times have you slept?
- 138m reply: I didn't understand that question — could you say it another way?
- 255b reply: I didn't understand that. Could you say it another way?
- 138m stored: []
- 255b stored: []
