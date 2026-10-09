"""Sealed check, step 1: cache reader states for the four eval sets (source_text and paraphrase variants of every question) and a TEST-kinds sample."""
import sys, json, os
sys.path.insert(0, '.'); sys.path.insert(0, 'diag')
import common as C, prep_states as P
OUT = '/Users/ben-hannan/talker_gap_cache/sealed'; os.makedirs(OUT, exist_ok=True)
SETS = ['FRESH-EN-R3', 'GEN-HELDOUT-R4', 'NEW-KINDS-R5', 'NEW-KINDS2-R6']
eg = P.load_eg()
for name in SETS:
    d = json.load(open(f'diag/eval_sets/{name}.json'))
    rows = []
    for ex in d['examples']:
        for var, text in (('src', ex['source_text']), ('para', ex['paraphrase'])):
            for qi, q in enumerate(ex['questions']):
                rows.append(C.make_row(dict(id=f"{name}/{ex['id']}/{qi}/{var}", kind=f"{name}:{ex['family']}", type=q['type'],
                                            source_text=text, question=q['question'], canonical_answer=q['canonical_answer'],
                                            accepted_answers=q['accepted_answers'])))
    print(name, len(rows), 'rows;', sum(1 for r in rows if r['type'] == 'short_answer' and r['gold_words']), 'short answers found in passage of',
          sum(1 for r in rows if r['type'] == 'short_answer'))
    P.write_split(eg, name, rows, OUT)
sp = C.build_splits()
rows = [C.make_row(r) for r in C.sample_rows(sp['test'], 3000, 'test')]
print('TEST', len(rows))
P.write_split(eg, 'TEST', rows, OUT)
