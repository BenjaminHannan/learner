# Frame spec notes for lis-301 (clarifications, 2026-09-23)

These notes add no new format. They write down conventions that frame-spec.md implies but does not state, so that data writers, key writers and blind labellers agree. They apply to lis-301 data, the lis-301 dev relabel and panel 301.

1. **Direction.** A fact reads as "owner's rel is value".
   - "Oren founded Halvo" and "Halvo was founded by Oren" are both (Halvo, founder, Oren).
   - "Yola wrote Star Rain" is (Star Rain, author, Yola).
   - "Peta painted Blue Lake" is (Blue Lake, painter, Peta).
   - "Tavi teaches Sora" is (Sora, teacher, Tavi).
   - "Halvo was founded in Dren" is (Halvo, location_of_formation, Dren).
2. **Unknown relations.** A relation word that is not in relation-names.txt (for example "blicket" or "mentor-spirit") gets `rel: "other"`. Never map it to a near relation name.
3. **Typos are kept as typed**, in owners and values alike. "My mom is Lenn" gives value "Lenn", even when a similar name was mentioned before.
4. **Reported speech.** Any claim the speaker passes on from someone or something else gets mode REPORTED. This covers "X said", "X told me", "I heard", "apparently", "the letter says", "according to X", and "rumor is". The act is STATE when the turn has no other act.
5. **Ambiguous pronouns.** When a pronoun could refer to two or more people named in the turn or the previous reply, the fact keeps the pronoun as its owner, as typed, with mode UNCLEAR. If that is the turn's only fact, the act is UNCLEAR. A pronoun with exactly one possible referent is resolved to that name.
6. **Mixed turns.** In a turn that states a fact and then asks a question, the stated facts keep their own modes. The asked fact is listed with mode QUESTION, and `ask` is filled in. The act is the act of the first clause.
