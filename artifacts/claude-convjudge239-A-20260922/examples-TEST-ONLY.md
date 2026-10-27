# TEST-ONLY verbatim examples (Judge A, exp 239, agent 138i)

Do not show this file to builders; do not tune on it. Format: conv/turn — user -> reply.

## 1. All-purpose fallback (124 replies)
- c239-02/0 — "Hello there." -> "I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way?"
- c239-04/1 — "I work at Quillstone." -> same fallback (nothing stored)

## 2. Teach not stored
- c239-01/3 — "i have a dog called Pepper" -> "You never told me your name, so I do not know it." (nothing stored)
- c239-03/2 — "She lives in Corvale." -> fallback
- c239-06/1 — "My brother is Casimir and he lives in Thornwick." -> "I can take one fact at a time — could you split that?"
- c239-26/5 — "OK, remember that my gym is called Ironleaf." -> fallback

## 3. Stored fact not recalled
- c239-01/5 — name Tobin stored; "and what's my name?" -> "You never told me your name, so I do not know it."
- c239-04/4 — [USER boss Delphine Ashgrove] + [Delphine city Eskerby]; "Where does my boss live?" -> fallback
- c239-14/5 — full chain stored; "Where does Fennimore's sister live?" -> fallback
- c239-25/6 — [USER father Gideon]; "is my dad called Gideon?" -> fallback

## 4. "anyone called my <relation>"
- c239-01/4 — "what's my dog's name?" -> "I don't know anyone called my dog."
- c239-15/6 — uncle stored; "What's my uncle's name?" -> "I don't know anyone called my uncle."

## 5. Name hijack
- c239-02/1 — "What's your name?" -> "You never told me your name, so I do not know it."
- c239-02/2 — "Who made you?" -> same
- c239-25/5 — "whats my mom's name" -> same (mother Rosamund stored)

## 6. Bad writes (value keeps "called"/"named")
- c239-03/1 — "My daughter is called Maribel." -> stored [USER, daughter, "called Maribel"]
- c239-07/1 — "my freind is called Anouk" -> "Saved: your freind is called Anouk." stored [USER, freind, "called Anouk"]
- c239-11/3, c239-15/1, c239-27/1 — same pattern

## 7. Social misfires
- c239-01/1 — "how's it going?" -> "Right now I am back in LISTENING mode, waiting for your next turn."
- c239-08/8 — "Cheers." -> fallback
- c239-01/0 — "hey" -> "Hi! Teach me like "Tom's boss is Ann." Ask me like "Who is Tom's boss?""

## 8. Out-of-scope not politely declined
- c239-05/2 — "Tell me a joke." -> fallback
- c239-26/1 — "Can you set an alarm for 7am?" -> fallback

## 9. Corrections ignored
- c239-22/6 — "Actually I moved to Castleburn." -> fallback

## 10. Favourites misroute
- c239-20/2 — "Alright. My favourite colour is green." -> "I do not have favourites."
- c239-16/5 — "What colour is my car?" -> "I do not have favourites."

## 11/12. Robotic phrasing and strays
- c239-04/3 — "Delphine lives in Eskerby." -> "Saved: Delphine's city is Eskerby."
- c239-17/5 — "who teaches me math?" -> "No. Every taught fact came from you."
- c239-29/5 — "Are you sure you aren't just guessing?" -> "I didn't understand that. I only know current facts and I can't do 'not' -- could you say it without that part?"

## Good turns (for contrast)
- c239-14/4 — "Who is my neighbour's sister?" -> "Your neighbour's sister is Tamsin."
- c239-26/4 — "What CAN you help with?" -> capability list (correct, jargon-heavy)
- c239-11/6 — "How old is Barnaby?" -> "You never taught me their age, so I do not know it."
