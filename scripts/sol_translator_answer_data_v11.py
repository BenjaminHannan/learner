"""Verbatim HUMAN annotation binding; no model text and no inference routing."""
import hashlib,json
from pathlib import Path
from sol_translator_grounding_v6 import human_rows as evidence_rows
from sol_translator_provenance import sha
ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'artifacts/sol-translator-20260929/ANSWER-V11-ANNOTATIONS.json'
def human_rows(corpus):
    original,registry=evidence_rows(corpus) # Verify unchanged source/evidence/official annotations first.
    manifest=json.loads(MANIFEST.read_text(encoding='utf-8'))
    if manifest['pairs_sha256']!=sha(Path(corpus)/'pairs.json') or manifest['official_train_sha256']!=sha(Path(corpus)/'train-v1.1.json'):raise ValueError('annotation source pins')
    records={r['id']:r for r in manifest['rows']};result=[]
    for row in original:
        if row['split']!='train':continue
        bound=records[row['id']]
        if bound['answer_text']!=row['answer_text'] or bound['context_sha256']!=hashlib.sha256(row['context'].encode()).hexdigest() or bound['question_sha256']!=hashlib.sha256(row['question'].encode()).hexdigest():raise ValueError('annotation binding drift')
        result.append(dict(row,evidence_text=row['target_text'],target_text=row['answer_text'],accepted_human_answers=bound['accepted_human_answers'],context_sha256=bound['context_sha256'],annotation_manifest_sha256=sha(MANIFEST)))
    if len(result)!=512 or len(records)!=512:raise ValueError('exact TRAIN512 annotation count')
    return result,registry
