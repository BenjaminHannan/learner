#!/usr/bin/env python3
"""Pinned human TRAIN packet admission without decoding reserved corpus text.

The one-time builder structurally scans mixed pairs as bytes.  It decodes only
identity/split/source metadata until all reserved exclusions are established.
Runtime admission opens the standalone TRAIN packet and its manifest only.
No Torch, optimizer, inference, queue execution, or raw official dataset access.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / 'artifacts/sol-translator-20260929/corpus'
ANNOTATIONS = ROOT / 'artifacts/sol-translator-20260929/ANSWER-V11-ANNOTATIONS.json'
OWN = ROOT / 'artifacts/sol-cloud-trainonly-20260930'
SCHEMA = 'sol.cloud.train-only.v1'
PINS = {
    'registry_sha256': '4919ab717006169a93a7da4c20a972d9b8844165cbf2b74850373f30d34dc539',
    'pairs_sha256': '97ded0da22d53a34c94d172736fb6658fbee6c3367469cb3eab96714902d6cc5',
    'annotation_manifest_sha256': 'b663fb6d548c41ce881974ffe0f588f45d9faf14371388e1a45af38636ad61f6',
    'official_train_sha256': '3527663986b8295af4f7fcdff1ba1ff3f72d07d61a20f487cb238a6ef92fd955',
}
METADATA_FIELDS = ('id', 'split', 'source_path', 'source_sha256', 'content_key')
TEXT_FIELDS = ('question', 'context', 'answer_text', 'target_text')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def text_sha(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode('utf-8')).hexdigest()


class ByteScanner:
    """Seekable 64KiB byte scanner; skipped string values are never decoded."""
    def __init__(self, path):
        self.stream = Path(path).open('rb')
        self.pos = 0
        self.base = -1
        self.buffer = b''
        self.decoded_fields = []

    def close(self):
        self.stream.close()

    def byte(self):
        if not self.base <= self.pos < self.base + len(self.buffer):
            self.stream.seek(self.pos)
            self.base = self.pos
            self.buffer = self.stream.read(65536)
        return self.buffer[self.pos - self.base] if self.buffer else None

    def whitespace(self):
        while self.byte() in (9, 10, 13, 32):
            self.pos += 1

    def expect(self, value):
        self.whitespace()
        if self.byte() != value:
            raise ValueError('invalid structural JSON at byte %d' % self.pos)
        self.pos += 1

    def string(self):
        self.expect(34)
        while True:
            b = self.byte()
            if b is None or b < 32:
                raise ValueError('invalid structural JSON string at byte %d' % self.pos)
            self.pos += 1
            if b == 34:
                return
            if b == 92:
                if self.byte() is None:
                    raise ValueError('unterminated escape')
                self.pos += 1

    def skip(self, depth=0):
        if depth > 64:
            raise ValueError('JSON nesting cap')
        self.whitespace()
        b = self.byte()
        if b == 34:
            self.string()
        elif b in (91, 123):
            end = 93 if b == 91 else 125
            object_value = b == 123
            self.pos += 1
            self.whitespace()
            if self.byte() == end:
                self.pos += 1
                return
            while True:
                if object_value:
                    self.string()
                    self.expect(58)
                self.skip(depth + 1)
                self.whitespace()
                if self.byte() == end:
                    self.pos += 1
                    return
                self.expect(44)
        else:
            start = self.pos
            while self.byte() is not None and self.byte() not in (9, 10, 13, 32, 44, 93, 125):
                self.pos += 1
                if self.pos - start > 64:
                    raise ValueError('JSON literal cap')
            if self.pos == start:
                raise ValueError('missing JSON value')

    def raw(self, span):
        begin, end = span
        self.stream.seek(begin)
        data = self.stream.read(end - begin)
        if len(data) != end - begin:
            raise ValueError('source changed during scan')
        return data

    def decode(self, span, field, cap=65536):
        if span[1] - span[0] > cap:
            raise ValueError('JSON field byte cap: ' + field)
        self.decoded_fields.append(field)
        return json.loads(self.raw(span).decode('utf-8'))

    def objects(self):
        self.expect(91)
        self.whitespace()
        if self.byte() == 93:
            self.pos += 1
        else:
            while True:
                self.whitespace()
                begin = self.pos
                self.expect(123)
                fields = {}
                self.whitespace()
                if self.byte() != 125:
                    while True:
                        self.whitespace()
                        key_begin = self.pos
                        self.string()
                        key = self.decode((key_begin, self.pos), '__key__', 256)
                        if not isinstance(key, str) or key in fields:
                            raise ValueError('duplicate/invalid JSON object key')
                        self.expect(58)
                        self.whitespace()
                        value_begin = self.pos
                        self.skip()
                        fields[key] = (value_begin, self.pos)
                        self.whitespace()
                        if self.byte() == 125:
                            break
                        self.expect(44)
                self.expect(125)
                yield (begin, self.pos), fields
                self.whitespace()
                if self.byte() == 93:
                    self.pos += 1
                    break
                self.expect(44)
        self.whitespace()
        if self.byte() is not None:
            raise ValueError('trailing JSON data')


def scan_metadata(path, approved_ids, registered_sources):
    """First pass: content remains encoded, including every reserved record."""
    scan = ByteScanner(path)
    selected = []
    reserved_ids, reserved_sources, reserved_keys = set(), set(), set()
    seen = set()
    counts = {'train': 0, 'dev': 0}
    try:
        for span, fields in scan.objects():
            if any(k not in fields for k in METADATA_FIELDS + TEXT_FIELDS + ('source_span',)):
                raise ValueError('missing mixed-source field')
            meta = {key: scan.decode(fields[key], key, 1024) for key in METADATA_FIELDS}
            if (any(not isinstance(meta[k], str) for k in METADATA_FIELDS)
                    or meta['split'] not in counts or meta['id'] in seen):
                raise ValueError('invalid/duplicate source identity metadata')
            seen.add(meta['id'])
            source = registered_sources.get(meta['source_path'], {})
            if source.get('origin') != 'human-authored' or source.get('sha256') != meta['source_sha256']:
                raise ValueError('unregistered source metadata')
            counts[meta['split']] += 1
            if meta['split'] == 'dev':
                reserved_ids.add(meta['id'])
                reserved_sources.add(meta['source_path'])
                reserved_keys.add(meta['content_key'])
                continue
            if meta['id'] not in approved_ids:
                raise ValueError('TRAIN ID absent from authorized annotation allowlist')
            selected.append((span, fields, meta))
        if reserved_ids & approved_ids:
            raise ValueError('reserved identity overlaps annotation allowlist')
        if {x[2]['id'] for x in selected} != approved_ids:
            raise ValueError('annotation allowlist coverage differs')
        if any(m['source_path'] in reserved_sources or m['content_key'] in reserved_keys
               for _, _, m in selected):
            raise ValueError('reserved source/passages overlap TRAIN')
        return selected, {
            'metadata_counts': counts,
            'reserved_rows_skipped_before_text_decode': len(reserved_ids),
            'reserved_source_paths': sorted(reserved_sources),
            'reserved_identity_set_sha256': canonical_sha(sorted(reserved_ids)),
            'reserved_content_key_set_sha256': canonical_sha(sorted(reserved_keys)),
            'decoded_text_fields_first_pass': sum(x in TEXT_FIELDS for x in scan.decoded_fields),
        }
    finally:
        scan.close()


def _row_admission(row, sources, annotation):
    if row.get('split') != 'train' or row.get('origin') != 'verified-human-TRAIN-fixture':
        raise ValueError('packet row is not admitted human TRAIN')
    if row.get('actual_user_day') is not False or row.get('model_authored_text_included') is not False:
        raise ValueError('fixture origin flags differ')
    if any(not isinstance(row.get(key), str) or not row[key] for key in
           ('id', 'question', 'context', 'answer_text', 'target_text', 'evidence_text')):
        raise ValueError('human field absent')
    if row['target_text'] != row['answer_text'] or row['answer_text'] != annotation['answer_text']:
        raise ValueError('target differs from existing human annotation')
    for key in ('question', 'context'):
        if (text_sha(row[key]) != annotation[key + '_sha256']
                or row[key + '_sha256'] != annotation[key + '_sha256']):
            raise ValueError('official HUMAN ' + key + ' hash mismatch')
    if row['accepted_human_answers'] != annotation['accepted_human_answers']:
        raise ValueError('accepted human annotation mismatch')
    if row['official_answer_offsets'] != annotation['official_answer_offsets']:
        raise ValueError('official answer offsets mismatch')
    accepted = set(annotation['accepted_human_answers'])
    if row['answer_text'] not in accepted or not accepted:
        raise ValueError('target not accepted HUMAN answer')
    for answer in annotation['official_answer_offsets']:
        offset, text = answer['answer_start'], answer['text']
        if (type(offset) is not int or offset < 0 or text not in accepted
                or row['context'][offset:offset + len(text)] != text):
            raise ValueError('verbatim official HUMAN answer span mismatch')
    if row['evidence_text'] not in row['context'] or row['answer_text'] not in row['evidence_text']:
        raise ValueError('evidence is not verbatim HUMAN context')
    source = sources.get(row['source_path'], {})
    if source.get('origin') != 'human-authored' or source.get('sha256') != row['source_sha256']:
        raise ValueError('source registry origin/hash mismatch')
    if row['source_hash'] != row['source_sha256'] or row['source_ref'] != row['source_path']:
        raise ValueError('source aliases differ')
    if (row['source_path'] in row['provenance']['reserved_source_paths']
            or any(row['provenance'].get(k) != v for k, v in PINS.items())
            or row['annotation_manifest_sha256'] != PINS['annotation_manifest_sha256']):
        raise ValueError('reserved source or original source pin mismatch')
    if row['source_span'] != row['evidence_span'] or len(row['source_span']) != 2:
        raise ValueError('evidence source span mismatch')
    begin, end = row['source_span']
    if type(begin) is not int or type(end) is not int or not 0 <= begin < end:
        raise ValueError('invalid evidence source byte offsets')
    for key, digest in row['field_sha256'].items():
        if key not in ('question', 'context', 'answer_text', 'target_text', 'evidence_text') or text_sha(row[key]) != digest:
            raise ValueError('human field hash mismatch')
    if set(row['field_sha256']) != {'question', 'context', 'answer_text', 'target_text', 'evidence_text'}:
        raise ValueError('incomplete field hashes')


def build_packet(output=OWN):
    """Build once from released TRAIN512, preserving all old sources/seals."""
    registry_path, pairs_path = CORPUS / 'registry.json', CORPUS / 'pairs.json'
    if sha(registry_path) != PINS['registry_sha256'] or sha(pairs_path) != PINS['pairs_sha256']:
        raise ValueError('original registry/pairs pins changed')
    if sha(ANNOTATIONS) != PINS['annotation_manifest_sha256']:
        raise ValueError('authorized TRAIN annotation manifest pin changed')
    registry = json.loads(registry_path.read_text(encoding='utf-8'))
    annotations = json.loads(ANNOTATIONS.read_text(encoding='utf-8'))
    if (registry.get('verification_status') != 'verified-human-origin'
            or registry.get('official_dev_or_test_accessed') is not False
            or registry.get('raw_training_sha256') != PINS['official_train_sha256']
            or annotations['official_train_sha256'] != PINS['official_train_sha256']
            or annotations['pairs_sha256'] != PINS['pairs_sha256']):
        raise ValueError('human-origin source lineage differs')
    byid = {r['id']: r for r in annotations['rows']}
    if len(byid) != 512 or len(annotations['rows']) != 512:
        raise ValueError('exact authorized TRAIN512 allowlist required')
    selected, exclusions = scan_metadata(pairs_path, set(byid), registry['sources'])
    if exclusions['metadata_counts'] != registry['counts'] or exclusions['decoded_text_fields_first_pass'] != 0:
        raise ValueError('registry counts or metadata-before-content invariant differs')
    scan = ByteScanner(pairs_path)
    rows = []
    try:
        for span, fields, meta in selected:
            human = {key: scan.decode(fields[key], key) for key in TEXT_FIELDS}
            evidence = human.pop('target_text')
            bound = byid[meta['id']]
            row = dict(meta, **human, target_text=bound['answer_text'], evidence_text=evidence,
                       source_span=scan.decode(fields['source_span'], 'source_span', 128),
                       accepted_human_answers=bound['accepted_human_answers'],
                       official_answer_offsets=bound['official_answer_offsets'],
                       question_sha256=bound['question_sha256'], context_sha256=bound['context_sha256'],
                       origin='verified-human-TRAIN-fixture', actual_user_day=False,
                       model_authored_text_included=False,
                       annotation_manifest_sha256=PINS['annotation_manifest_sha256'])
            row.update(source_ref=row['source_path'], source_hash=row['source_sha256'],
                       evidence_span=row['source_span'])
            row['field_sha256'] = {key: text_sha(row[key]) for key in
                                   ('question', 'context', 'answer_text', 'target_text', 'evidence_text')}
            row['provenance'] = {
                **PINS,
                'pairs_record_byte_span': list(span),
                'pairs_record_raw_sha256': hashlib.sha256(scan.raw(span)).hexdigest(),
                'pairs_field_byte_spans': {key: list(fields[key]) for key in TEXT_FIELDS},
                'pairs_field_raw_sha256': {key: hashlib.sha256(scan.raw(fields[key])).hexdigest() for key in TEXT_FIELDS},
                'source_evidence_span_unit': 'UTF-8 bytes in original registered human source',
                'official_answer_span_unit': 'Unicode code points in verbatim context',
                'reserved_source_paths': exclusions['reserved_source_paths'],
            }
            _row_admission(row, registry['sources'], bound)
            rows.append(row)
    finally:
        scan.close()
    if sha(pairs_path) != PINS['pairs_sha256']:
        raise ValueError('mixed source changed during admission')
    packet = {
        'schema': SCHEMA, 'actual_user_day': False,
        'model_authored_text_included': False, 'reserved_text_decoded': False,
        'source_pins': PINS, 'rows': rows,
    }
    manifest = {
        'schema': SCHEMA + '.manifest', 'source_pins': PINS,
        'registry': registry, 'authorized_TRAIN_annotations': annotations['rows'],
        'exclusion_audit': exclusions, 'TRAIN_rows': len(rows),
        'row_canonical_sha256': {r['id']: canonical_sha(r) for r in rows},
        'actual_user_day': False, 'model_authored_text_included': False,
        'raw_official_corpus_opened': False, 'human_source_documents_opened': False,
        'stop88_identity_metadata': 'unavailable; no independent overlap certificate; restricted to explicitly released existing TRAIN512',
        'claims': 'source admission and fixture engineering only; no semantics, generalization, live-user learning or activation qualification',
    }
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    packet_path, manifest_path = output / 'TRAIN-PACKET.json', output / 'TRAIN-MANIFEST.json'
    if packet_path.exists() or manifest_path.exists():
        raise ValueError('preserve packet: additive new version required')
    encoded = json.dumps(packet, ensure_ascii=False, indent=2) + '\n'
    packet_path.write_text(encoded, encoding='utf-8')
    manifest['packet_sha256'] = sha(packet_path)
    manifest['packet_bytes'] = packet_path.stat().st_size
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    receipt = {
        'packet': {'path': str(packet_path.relative_to(ROOT)), 'sha256': sha(packet_path), 'bytes': packet_path.stat().st_size},
        'manifest': {'path': str(manifest_path.relative_to(ROOT)), 'sha256': sha(manifest_path)},
        'loader': {'path': str(Path(__file__).relative_to(ROOT)), 'sha256': sha(__file__), 'module': 'sol_cloud_trainonly_v1'},
        'TRAIN_rows': len(rows), 'reserved_rows_text_decoded': 0,
        'actual_user_day': False, 'optimizer_updates': 0, 'source_pins': PINS,
        'exclusion_audit': exclusions,
    }
    (output / 'BUILD-RECEIPT.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    return receipt


def _read_pinned(path, digest):
    if not isinstance(digest, str) or len(digest) != 64:
        raise ValueError('external SHA256 pin required')
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError('pinned standalone artifact hash mismatch')
    return json.loads(raw.decode('utf-8'))


def _verify_original_metadata(manifest):
    """Reconstitute byte-identical permitted metadata to verify legacy pins.

    This checks copied registry/annotation contents, rather than accepting a
    claim about their original hashes.  No original files need to be reopened.
    """
    registry_bytes = (json.dumps(manifest['registry'], indent=2) + '\n').encode('utf-8')
    if hashlib.sha256(registry_bytes).hexdigest() != PINS['registry_sha256']:
        raise ValueError('copied original registry metadata differs')
    annotations = {
        'stage': 'PRE-RUN official HUMAN TRAIN answer-annotation binding; no model text',
        'official_train_sha256': PINS['official_train_sha256'],
        'pairs_sha256': PINS['pairs_sha256'],
        'license': 'CC-BY-SA-4.0',
        'source_url': 'https://rajpurkar.github.io/SQuAD-explorer/dataset/train-v1.1.json',
        'rows': manifest['authorized_TRAIN_annotations'],
    }
    annotation_bytes = (json.dumps(annotations, indent=2, ensure_ascii=False) + '\n').encode('utf-8')
    if hashlib.sha256(annotation_bytes).hexdigest() != PINS['annotation_manifest_sha256']:
        raise ValueError('copied original TRAIN annotation metadata differs')


def load_packet(path, expected_sha256, manifest_path=None, manifest_sha256=None):
    """Return admitted TRAIN rows; never open legacy mixed/raw/document files.

    Callers must supply both external digests.  Content decoding occurs only
    after the complete standalone file's external SHA256 matches the seal.
    """
    if manifest_path is None or manifest_sha256 is None:
        raise ValueError('external manifest path and SHA256 pin required')
    manifest = _read_pinned(manifest_path, manifest_sha256)
    if (manifest.get('schema') != SCHEMA + '.manifest' or manifest.get('source_pins') != PINS
            or manifest.get('packet_sha256') != expected_sha256
            or manifest.get('TRAIN_rows') != 512
            or manifest.get('actual_user_day') is not False
            or manifest.get('model_authored_text_included') is not False):
        raise ValueError('standalone manifest provenance differs')
    _verify_original_metadata(manifest)
    packet = _read_pinned(path, expected_sha256)
    if (packet.get('schema') != SCHEMA or packet.get('source_pins') != PINS
            or packet.get('actual_user_day') is not False
            or packet.get('model_authored_text_included') is not False
            or packet.get('reserved_text_decoded') is not False):
        raise ValueError('standalone packet provenance differs')
    rows = packet['rows']
    approved = {r['id']: r for r in manifest['authorized_TRAIN_annotations']}
    if len(rows) != 512 or len(approved) != 512 or len({r['id'] for r in rows}) != 512:
        raise ValueError('exact standalone TRAIN512 identity count required')
    if {r['id'] for r in rows} != set(approved):
        raise ValueError('standalone packet identity allowlist differs')
    registry = manifest['registry']
    excluded_sources = set(manifest['exclusion_audit']['reserved_source_paths'])
    for row in rows:
        if row['source_path'] in excluded_sources:
            raise ValueError('reserved document in standalone packet')
        if canonical_sha(row) != manifest['row_canonical_sha256'].get(row['id']):
            raise ValueError('standalone row digest differs')
        _row_admission(row, registry['sources'], approved[row['id']])
    return rows


def human_rows(corpus=None, *, packet=None, manifest=None,
               expected_packet_sha256=None, expected_manifest_sha256=None):
    """Night-loader compatibility; ``corpus`` must be the new packet directory."""
    directory = Path(corpus) if corpus is not None else OWN
    packet = Path(packet) if packet is not None else directory / 'TRAIN-PACKET.json'
    manifest = Path(manifest) if manifest is not None else directory / 'TRAIN-MANIFEST.json'
    rows = load_packet(packet, expected_packet_sha256, manifest, expected_manifest_sha256)
    metadata = _read_pinned(manifest, expected_manifest_sha256)
    return rows, metadata['registry']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['build', 'check'])
    parser.add_argument('--output', type=Path, default=OWN)
    parser.add_argument('--packet', type=Path)
    parser.add_argument('--packet-sha256')
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--manifest-sha256')
    args = parser.parse_args()
    if args.action == 'build':
        print(json.dumps(build_packet(args.output), indent=2))
    else:
        rows = load_packet(args.packet, args.packet_sha256, args.manifest, args.manifest_sha256)
        print(json.dumps({'TRAIN_rows': len(rows), 'actual_user_day': False,
                          'reserved_rows_text_decoded': 0, 'optimizer_updates': 0}))


if __name__ == '__main__':
    main()
