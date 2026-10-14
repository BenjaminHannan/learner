"""Word lists: entity names, common predicate words, nonsense-word builder."""

_NAMES = """aaron abby adam alan alex alice amy andy anna anne april ben beth bill bob brad brian bruce
carl carol cathy chad chris clara cody dan dana dave dawn dean diana dina don drew earl ed ella emma
eric erin eva evan fay finn fred gail gary gina glen grace greg hank hannah harry heidi helen henry
holly hugo ian ida iris ivan jack jade jake james jane jason jean jeff jenny jill jim joan joe john
jose joy judy julia kate kay keith ken kim kurt kyle lara larry laura leo lily lisa liz lou luke lynn
mae mark mary matt max maya mike mia nate neil nick nina noah nora olga omar owen pam pat paul pete
quinn ralph ray rick rita rob rosa ruth ryan sam sara scott sean seth tara ted tim tina todd tom tony
troy uma vera vic walt wendy will zack zoe dylan""".split()

_COMMON = """big small red blue cold hot happy sad fast slow tall short old young loud quiet soft hard
round flat sweet sour dark bright heavy light clean dirty rich poor wet dry strong weak kind rude brave
shy smart wise calm wild tame sharp dull thin thick warm cool new safe green yellow purple orange pink
brown gray white black empty full tidy messy lucky proud tired busy lazy funny silly gentle fierce
honest polite famous hungry thirsty sleepy fancy plain rough smooth steady shiny rusty dusty cozy rare
common early late apple tiger river stone cloud doctor farmer pilot teacher robot wizard dragon knight
sailor puppy kitten bridge castle garden rocket pirate""".split()

_SYL = """wum pus tar vle blo zik fen dro mor nax plib snor glim kra vop yuf jun flo trin bax zor mip wug pif rax tep zun lub vem tom fra nid kel dax fop gri lek mub nof pex""".split()

ENTITIES = [w for w in _NAMES if len(w) <= 5]  # short names
COMMON_WORDS = [w for w in _COMMON if len(w) <= 6]
assert len(set(ENTITIES)) == len(ENTITIES) >= 120
assert not set(ENTITIES) & set(COMMON_WORDS) and len(set(COMMON_WORDS)) == len(COMMON_WORDS)


def nonsense_word(rng):
    """Two random syllables, 3-6 letters, e.g. 'wumpus', 'tarvle'."""
    while True:
        w = rng.choice(_SYL) + rng.choice(_SYL)
        if 3 <= len(w) <= 6:
            return w
