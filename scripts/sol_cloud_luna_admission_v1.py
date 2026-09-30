#!/usr/bin/env python3
"""Proposed typed admission boundary; no downloaded Luna schema is assumed.

Import-safe stdlib only. Test fixtures are never training eligible. A caller must
pin a confirmed schema, source/audit bytes and an explicit source-origin release
before admitting real records. No tokenizer, network, model or optimizer loads.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
from typing import Callable, Mapping, Sequence

SCHEMA = 'sol.cloud.luna.proposed-admission.v1'
AUDIT_SCHEMA = 'sol.cloud.luna.proposed-numeric-audit.v1'
TOKENIZER_SHA256 = 'df1d8d5ec5d091b460562ffd545e4a5e91d17d4a0db7ebe733be34ed374377bd'
ORIGINS = frozenset(('synthetic-wordproblem', 'human-TRAIN', 'numeric-test-fixture'))
ROW_KEYS = frozenset(('event_id', 'source_row_id', 'question',
                     'numeric_answer', 'source_sha256', 'origin', 'audit_id'))
AUDIT_KEYS = frozenset(('audit_id', 'source_row_id', 'source_sha256', 'origin',
                       'question_sha256', 'numeric_answer',
                       'independent_answer', 'question_only_verified',
                       'wording_unambiguous', 'adjudication', 'input_complete',
                       'audit_material_sha256', 'independent_answer_commit_sha256',
                       'independent_answer_committed_before_tree'))
HEX = re.compile(r'[0-9a-f]{64}\Z')
NUMBER = re.compile(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]*[1-9])?\Z')


def text_sha(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def canonical_sha(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def digest(value) -> str:
    if type(value) is not str or HEX.fullmatch(value) is None:
        raise ValueError('exact lowercase SHA256 required')
    return value


def numeric_text(value) -> str:
    if type(value) is not str or NUMBER.fullmatch(value) is None or value == '-0':
        raise ValueError('canonical finite integer/decimal literal required; no prose/formula/code')
    if not Decimal(value).is_finite():
        raise ValueError('finite numeric target required')
    return value


@dataclass(frozen=True)
class Policy:
    """Trusted caller metadata, never inferred from a candidate row."""
    released_sources: Mapping[str, str]
    expected_audit_material_sha256: str
    schema_confirmed: bool = False
    real_data_release: bool = False
    fixture_only: bool = True

    def validate(self):
        digest(self.expected_audit_material_sha256)
        for source, origin in self.released_sources.items():
            digest(source)
            if origin not in ORIGINS:
                raise ValueError('unknown source origin')
        if not self.schema_confirmed:
            raise ValueError('actual source schema is unconfirmed; admission blocked before content access')
        if not self.fixture_only and not self.real_data_release:
            raise ValueError('explicit real-data source release absent')
        if self.fixture_only and any(v != 'numeric-test-fixture' for v in self.released_sources.values()):
            raise ValueError('fixture policy cannot admit human or synthetic production records')
        if not self.fixture_only and any(v == 'numeric-test-fixture' for v in self.released_sources.values()):
            raise ValueError('test fixtures can never be training data')
        if any(v == 'human-TRAIN' for v in self.released_sources.values()):
            raise ValueError('human TRAIN uses its existing verified loader; no synthetic gate relabeling')


@dataclass(frozen=True)
class QuestionInput:
    """The entire new synthetic reader input surface; no dictionary is accepted."""
    question: str

    def __post_init__(self):
        if type(self.question) is not str or not self.question.strip():
            raise ValueError('complete nonempty question string required')


@dataclass(frozen=True)
class OutOfBandSource:
    """Exact JSON copy for verification/lineage, never accepted by model_question."""
    source_record_json: str
    source_record_sha256: str


def project_source_question(source: dict) -> tuple[QuestionInput, OutOfBandSource]:
    """Projection only, not admission of any real unknown-schema Luna record.

    Legitimate operation trees/answers/review fields are preserved out of band.
    Only the explicit question key is copied to the input DTO. A future separately
    confirmed source-schema adapter must run verification before using this.
    """
    if type(source) is not dict:
        raise ValueError('source JSON object required')
    dto = QuestionInput(source.get('question'))
    raw = json.dumps(source, sort_keys=True, separators=(',', ':'),
                     ensure_ascii=False, allow_nan=False)
    return dto, OutOfBandSource(raw, hashlib.sha256(raw.encode()).hexdigest())


def model_question(value: QuestionInput) -> str:
    if type(value) is not QuestionInput:
        raise TypeError('model boundary accepts QuestionInput only; whole rows/audits rejected')
    return value.question


@dataclass(frozen=True)
class Admitted:
    event_id: str
    source_row_id: str
    question: str
    numeric_answer: str
    source_sha256: str
    origin: str
    audit_id: str
    audit_material_sha256: str
    fixture_only: bool

    def model_input(self) -> str:
        # No IDs, answers, provenance, operation trees or audits enter the reader.
        return model_question(self.input_dto())

    def input_dto(self) -> QuestionInput:
        return QuestionInput(self.question)

    def logging_metadata(self) -> dict:
        return {'event_id': self.event_id, 'source_row_id': self.source_row_id,
                'question_sha256': text_sha(self.question), 'origin': self.origin,
                'source_sha256': self.source_sha256, 'audit_id': self.audit_id,
                'audit_material_sha256': self.audit_material_sha256,
                'fixture_only': self.fixture_only}

    def target_text(self) -> str:
        # EOS is appended as a token by token_audit; no explanation is appended.
        return self.numeric_answer

    def event_sha256(self) -> str:
        return canonical_sha(self.__dict__)


def admit(row: dict, audit: dict, policy: Policy) -> Admitted:
    policy.validate()
    if type(row) is not dict or set(row) != ROW_KEYS:
        raise ValueError('closed candidate row schema required; audit/code/tree/rationale fields rejected')
    if type(audit) is not dict or set(audit) != AUDIT_KEYS:
        raise ValueError('closed independent numeric verification receipt required')
    for key in ('event_id', 'source_row_id', 'question', 'audit_id'):
        if type(row[key]) is not str or not row[key].strip():
            raise ValueError('nonempty exact string required: ' + key)
    source = digest(row['source_sha256'])
    if (type(row['origin']) is not str or row['origin'] not in ORIGINS
            or policy.released_sources.get(source) != row['origin']):
        raise ValueError('source hash/origin is not explicitly released; synthetic cannot be relabeled human')
    for key in ('audit_id', 'source_row_id', 'source_sha256', 'origin'):
        if type(audit[key]) is not str or audit[key] != row[key]:
            raise ValueError('independent audit identity differs: ' + key)
    if (digest(audit['question_sha256']) != text_sha(row['question'])
            or digest(audit['audit_material_sha256']) != policy.expected_audit_material_sha256):
        raise ValueError('exact question/audit provenance differs')
    expected = numeric_text(row['numeric_answer'])
    if (numeric_text(audit['numeric_answer']) != expected
            or numeric_text(audit['independent_answer']) != expected):
        raise ValueError('numeric target and independent adjudication disagree')
    if (audit['question_only_verified'] is not True
            or audit['wording_unambiguous'] is not True
            or audit['input_complete'] is not True
            or audit['adjudication'] != 'verified-match'
            or audit['independent_answer_committed_before_tree'] is not True):
        raise ValueError('unverified, ambiguous, incomplete or mismatched outcome')
    commit = canonical_sha({'source_row_id': row['source_row_id'],
                            'question_sha256': text_sha(row['question']),
                            'independent_answer': audit['independent_answer']})
    if digest(audit['independent_answer_commit_sha256']) != commit:
        raise ValueError('prose-only answer commitment differs; numeric/tree consistency is insufficient')
    return Admitted(**row, audit_material_sha256=policy.expected_audit_material_sha256,
                    fixture_only=policy.fixture_only)


def safe_path(path, approved_root) -> Path:
    """Reject protected paths and symlink escapes before hashing/opening bytes."""
    candidate, root = Path(path).absolute(), Path(approved_root).absolute()
    protected = ('uncle-questions', 'readpanel320', 'dev100', 'stop88', 'sealed', 'blind')
    for checked in (candidate, candidate.resolve()):
        if any(term in part.casefold() for part in checked.parts for term in protected):
            raise ValueError('protected path rejected before content access')
    if not candidate.resolve().is_relative_to(root.resolve()):
        raise ValueError('path outside explicit approved fixture/data root')
    if any(p.is_symlink() for p in (candidate, *candidate.parents)):
        raise ValueError('symlink sources rejected before content access')
    return candidate


def pinned_json(path, expected_sha256, approved_root):
    expected = digest(expected_sha256)
    p = safe_path(path, approved_root)
    raw = p.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('external byte pin differs; decoder not called')
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate JSON key is ambiguous')
            result[key] = value
        return result
    def reject_constant(value):
        raise ValueError('nonfinite JSON literal rejected: ' + value)
    return json.loads(raw.decode('utf-8'), object_pairs_hook=unique_object,
                      parse_constant=reject_constant)


def load_proposed_packet(packet_path, packet_sha256, audit_path, audit_sha256,
                         approved_root, policy: Policy) -> list[Admitted]:
    # In particular, unknown real ZIP schema is blocked before either read.
    policy.validate()
    for p in (packet_path, audit_path):
        safe_path(p, approved_root)
    packet = pinned_json(packet_path, packet_sha256, approved_root)
    audits = pinned_json(audit_path, audit_sha256, approved_root)
    if type(packet) is not dict or set(packet) != {'schema', 'rows'} or packet['schema'] != SCHEMA:
        raise ValueError('proposed normalized packet schema required; raw Luna schema not assumed')
    if type(audits) is not dict or set(audits) != {'schema', 'rows'} or audits['schema'] != AUDIT_SCHEMA:
        raise ValueError('independent audit receipt packet schema differs')
    if type(packet['rows']) is not list or type(audits['rows']) is not list:
        raise ValueError('rows must be lists')
    by = {}
    for audit in audits['rows']:
        if type(audit) is not dict or type(audit.get('audit_id')) is not str:
            raise ValueError('typed independent audit identity required')
        if audit['audit_id'] in by:
            raise ValueError('duplicate independent audit ID')
        by[audit['audit_id']] = audit
    catalog = EventCatalog()
    for row in packet['rows']:
        if type(row) is not dict or row.get('audit_id') not in by:
            raise ValueError('matching independently pinned audit is absent')
        catalog.ingest(admit(row, by[row['audit_id']], policy))
    return list(catalog.rows.values())


@dataclass(frozen=True)
class CounterBinding:
    encode: Callable[[str], Sequence[int]]
    eos_token_id: int
    tokenizer_sha256: str
    actual_shipped_tokenizer: bool
    fixture_only: bool


def bind_shipped_tokenizer(tokenizer, tokenizer_json_path, approved_snapshot,
                           expected_sha256=TOKENIZER_SHA256) -> CounterBinding:
    """Bind an already-loaded offline tokenizer; this function never loads one.

    The caller supplies the actual shipped instance. Name/path and exact original
    tokenizer.json must match. CPU tests use explicitly separate fixture counters.
    """
    if digest(expected_sha256) != TOKENIZER_SHA256:
        raise ValueError('shipped tokenizer provenance pin differs')
    path = safe_path(tokenizer_json_path, approved_snapshot)
    if path.name != 'tokenizer.json' or hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha256:
        raise ValueError('shipped tokenizer bytes differ')
    if Path(tokenizer.name_or_path).resolve() != Path(approved_snapshot).resolve():
        raise ValueError('loaded tokenizer instance does not name the approved offline snapshot')
    if type(tokenizer.eos_token_id) is not int or tokenizer.eos_token_id < 0:
        raise ValueError('actual EOS token ID required')
    return CounterBinding(lambda text: tokenizer.encode(text, add_special_tokens=False),
                          tokenizer.eos_token_id, expected_sha256, True, False)


def _ids(counter: CounterBinding, text: str) -> list[int]:
    ids = counter.encode(text)
    if type(ids) not in (list, tuple) or any(type(x) is not int or x < 0 for x in ids):
        raise ValueError('counter must return exact nonnegative tokenizer token IDs')
    return list(ids)


def token_audit(row: Admitted, counter: CounterBinding, max_question=48,
                max_context=512, max_target=64) -> dict:
    if (max_question, max_context, max_target) != (48, 512, 64):
        raise ValueError('shipped input caps cannot be silently changed')
    if type(counter.eos_token_id) is not int or counter.eos_token_id < 0:
        raise ValueError('exact nonnegative EOS token ID required')
    if counter.fixture_only != row.fixture_only:
        raise ValueError('fixture counter cannot qualify real data')
    if not row.fixture_only and (counter.actual_shipped_tokenizer is not True
                                or counter.tokenizer_sha256 != TOKENIZER_SHA256):
        raise ValueError('actual pinned shipped tokenizer required; no character proxy')
    q, target = _ids(counter, row.model_input()), _ids(counter, row.target_text())
    if not q or not target:
        raise ValueError('nonempty question/target tokenization required')
    if len(q) > max_question or len(target) + 1 > max_target:
        raise ValueError('complete input/target exceeds fixed token budget; no truncation/crop/drop')
    return {'event_id': row.event_id, 'event_sha256': row.event_sha256(),
            'question_ids': q + [counter.eos_token_id], 'notebook_ids': [],
            'target_ids': target + [counter.eos_token_id],
            'question_tokens_before_EOS': len(q), 'notebook_tokens': 0,
            'target_tokens_including_EOS': len(target) + 1,
            'input_fields': ['question'], 'target_scope': 'verified-numeric-answer+EOS',
            'input_complete': True, 'question_truncated': False, 'context_truncated': False,
            'target_truncated': False, 'operation_tree_input': False, 'audit_input': False,
            'rationale_input': False, 'code_input': False, 'facts_input': False,
            'proposed_answer_input': False, 'IDs_input': False, 'template_ID_input': False,
            'tokenizer_sha256': counter.tokenizer_sha256,
            'actual_shipped_tokenizer': counter.actual_shipped_tokenizer,
            'fixture_only': row.fixture_only, 'actual_user_day': False,
            'training_eligible': not row.fixture_only and counter.actual_shipped_tokenizer is True}


def batch_token_audit(rows: Sequence[Admitted], counter: CounterBinding) -> dict:
    """Complete count receipt; any rejection blocks the whole proposed batch.

    Failed records remain represented. This function never returns a silently
    filtered training batch. Token IDs live in out-of-band audit receipts only.
    """
    results, failures = [], []
    for row in rows:
        try:
            results.append(token_audit(row, counter))
        except ValueError as error:
            failures.append({'event_id': row.event_id, 'event_sha256': row.event_sha256(),
                             'reason': str(error), 'record_retained': True})
    return {'schema': 'sol.cloud.luna.proposed-token-audit.v1', 'source_records': len(rows),
            'complete_token_pass_records': len(results), 'rejected_records': len(failures),
            'all_inputs_complete_without_truncation': bool(rows) and not failures,
            'input_fields': ['question'], 'notebook_tokens': 0,
            'operation_tree_input': False, 'facts_input': False, 'audit_input': False,
            'proposed_answer_input': False, 'code_input': False, 'rationale_input': False,
            'IDs_input': False, 'template_ID_input': False,
            'actual_shipped_tokenizer': counter.actual_shipped_tokenizer,
            'tokenizer_sha256': counter.tokenizer_sha256,
            'training_batch_eligible': bool(rows) and not failures
                and all(r['training_eligible'] for r in results),
            'results': results, 'failures': failures,
            'actual_user_day': False, 'optimizer_calls': 0}


class EventCatalog:
    """Admission identity contract only; no optimizer or durable-job guarantees."""
    def __init__(self):
        self.rows: dict[str, Admitted] = {}

    def ingest(self, row: Admitted) -> bool:
        old = self.rows.get(row.event_id)
        if old is not None:
            if old.event_sha256() != row.event_sha256():
                raise ValueError('duplicate source event ID with changed bytes/provenance')
            return False
        self.rows[row.event_id] = row
        return True

    def exposure_visits(self, requested: Sequence[tuple[str, str]]) -> dict:
        visits = {}
        for visit_id, event_id in requested:
            if type(visit_id) is not str or not visit_id or event_id not in self.rows:
                raise ValueError('exact visit identity and admitted source event required')
            if visit_id in visits and visits[visit_id] != event_id:
                raise ValueError('duplicate visit ID points at a different event')
            visits[visit_id] = event_id
        return {'unique_source_events': len(self.rows), 'unique_exposure_visits': len(visits),
                'visits_per_event': dict(Counter(visits.values())),
                'visit_bindings': [{'visit_id': k, 'event_id': v,
                                    'event_sha256': self.rows[v].event_sha256()}
                                   for k, v in visits.items()],
                'optimizer_application_guarantee': 'UNIMPLEMENTED; metadata only'}
