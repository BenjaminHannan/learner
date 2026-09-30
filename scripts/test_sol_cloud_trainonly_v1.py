"""Numeric structural scaffolding only; these temporary rows are never training."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import sol_cloud_trainonly_v1 as admission


class MetadataBeforeContentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / '1.json'
        self.sources = {
            '1': {'origin': 'human-authored', 'sha256': '1' * 64},
            '2': {'origin': 'human-authored', 'sha256': '2' * 64},
        }

    def row(self, identity, split, source):
        return {'id': identity, 'split': split, 'source_path': source,
                'source_sha256': source * 64, 'content_key': identity,
                'question': '7', 'context': '11', 'answer_text': '1',
                'target_text': '1', 'source_span': [0, 1]}

    def test_reserved_invalid_utf8_never_decoded(self):
        permitted = json.dumps(self.row('1', 'train', '1')).encode()
        reserved = json.dumps(self.row('2', 'dev', '2')).encode()
        reserved = reserved.replace(b'"question": "7"', b'"question": "\xff"')
        self.path.write_bytes(b'[' + permitted + b',' + reserved + b']')
        selected, audit = admission.scan_metadata(self.path, {'1'}, self.sources)
        self.assertEqual(len(selected), 1)
        self.assertEqual(audit['reserved_rows_skipped_before_text_decode'], 1)
        self.assertEqual(audit['decoded_text_fields_first_pass'], 0)
        scan = admission.ByteScanner(self.path)
        self.addCleanup(scan.close)
        self.assertEqual(scan.decode(selected[0][1]['question'], 'question'), '7')

    def test_all_reserved_text_and_unknown_nested_values_are_not_decoded(self):
        permitted = self.row('1', 'train', '1')
        reserved = self.row('2', 'dev', '2')
        permitted['9'] = {'8': '99'}
        reserved['9'] = {'8': ['99', {'7': '99'}]}
        reserved_bytes = json.dumps(reserved).encode()
        for key in admission.TEXT_FIELDS:
            old = ('"%s": "%s"' % (key, reserved[key])).encode()
            reserved_bytes = reserved_bytes.replace(old, ('"%s": "' % key).encode() + b'\xff"')
        permitted_bytes = json.dumps(permitted).encode().replace(b'"99"', b'"\xff"')
        reserved_bytes = reserved_bytes.replace(b'"99"', b'"\xff"')
        self.path.write_bytes(b'[' + permitted_bytes + b',' + reserved_bytes + b']')
        decoded = []
        original = admission.ByteScanner.decode

        def guarded_decode(scanner, span, field, *args):
            self.assertIn(field, admission.METADATA_FIELDS + ('__key__',))
            decoded.append(field)
            return original(scanner, span, field, *args)

        with patch.object(admission.ByteScanner, 'decode', guarded_decode):
            selected, audit = admission.scan_metadata(self.path, {'1'}, self.sources)
        self.assertEqual(len(selected), 1)
        self.assertEqual(audit['decoded_text_fields_first_pass'], 0)
        self.assertFalse(set(decoded) & set(admission.TEXT_FIELDS))

    def test_unknown_train_identity_rejected_before_text_decode(self):
        encoded = json.dumps([self.row('2', 'train', '2')]).encode()
        encoded = encoded.replace(b'"question": "7"', b'"question": "\xff"')
        self.path.write_bytes(encoded)
        with self.assertRaisesRegex(ValueError, 'allowlist'):
            admission.scan_metadata(self.path, {'1'}, self.sources)

    def test_reserved_document_overlap_rejected_before_text_decode(self):
        encoded = json.dumps([self.row('1', 'train', '1'), self.row('2', 'dev', '1')]).encode()
        encoded = encoded.replace(b'"question": "7"', b'"question": "\xff"')
        self.path.write_bytes(encoded)
        with self.assertRaisesRegex(ValueError, 'overlap'):
            admission.scan_metadata(self.path, {'1'}, self.sources)

    def test_reserved_passage_key_overlap_rejected_before_text_decode(self):
        permitted, reserved = self.row('1', 'train', '1'), self.row('2', 'dev', '2')
        reserved['content_key'] = permitted['content_key']
        self.path.write_text(json.dumps([permitted, reserved]))
        with self.assertRaisesRegex(ValueError, 'overlap'):
            admission.scan_metadata(self.path, {'1'}, self.sources)

    def test_duplicate_key_rejected(self):
        self.path.write_bytes(b'[{"id":"1","id":"2"}]')
        scan = admission.ByteScanner(self.path)
        self.addCleanup(scan.close)
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            list(scan.objects())

    def test_offsets_handle_escaped_delimiters_and_utf8(self):
        value = [{"1": '7\\"[{},]é', '2': {'3': [1, True, None]}}]
        self.path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
        scan = admission.ByteScanner(self.path)
        self.addCleanup(scan.close)
        objects = list(scan.objects())
        self.assertEqual(scan.decode(objects[0][1]['1'], '1'), value[0]['1'])
        self.assertEqual(scan.decode(objects[0][1]['2'], '2'), value[0]['2'])

    def test_bad_pin_fails_before_json_decode(self):
        self.path.write_bytes(b'\xff')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            admission._read_pinned(self.path, '0' * 64)

    def test_external_manifest_pin_required(self):
        with self.assertRaisesRegex(ValueError, 'manifest'):
            admission.load_packet(self.path, '0' * 64)


class ReleasedPacketTests(unittest.TestCase):
    def released(self):
        receipt = json.loads((admission.OWN / 'BUILD-RECEIPT.json').read_text())
        return receipt, admission.ROOT / receipt['packet']['path'], admission.ROOT / receipt['manifest']['path']

    @unittest.skipUnless((admission.OWN / 'BUILD-RECEIPT.json').is_file(), 'packet not yet built')
    def test_runtime_opens_only_packet_and_manifest(self):
        receipt, packet, manifest = self.released()
        allowed = {packet.resolve(), manifest.resolve()}
        original_open = Path.open
        opened = []

        def controlled_open(path, *args, **kwargs):
            self.assertIn(path.resolve(), allowed)
            opened.append(path.resolve())
            return original_open(path, *args, **kwargs)

        with patch.object(Path, 'open', controlled_open):
            rows, registry = admission.human_rows(
                packet=packet, manifest=manifest,
                expected_packet_sha256=receipt['packet']['sha256'],
                expected_manifest_sha256=receipt['manifest']['sha256'])
        self.assertEqual(len(rows), 512)
        self.assertEqual(set(opened), allowed)
        self.assertTrue(all(r['split'] == 'train' for r in rows))
        self.assertTrue(all(r['target_text'] in r['context'] for r in rows))
        self.assertEqual(registry['verification_status'], 'verified-human-origin')

    @unittest.skipUnless((admission.OWN / 'BUILD-RECEIPT.json').is_file(), 'packet not yet built')
    def test_human_field_source_and_origin_tampering_rejected_even_with_new_outer_pins(self):
        _, packet_path, manifest_path = self.released()
        original_packet = json.loads(packet_path.read_text())
        original_manifest = json.loads(manifest_path.read_text())
        mutations = {
            'target': lambda r: r.update(target_text=r['context']),
            'source': lambda r: r.update(source_sha256='0' * 64, source_hash='0' * 64),
            'origin': lambda r: r.update(model_authored_text_included=True),
            'provenance': lambda r: r['provenance'].update(official_train_sha256='0' * 64),
        }
        with tempfile.TemporaryDirectory() as tmp:
            p, m = Path(tmp) / '1.json', Path(tmp) / '2.json'
            for name, mutate in mutations.items():
                with self.subTest(name=name):
                    packet, manifest = copy.deepcopy(original_packet), copy.deepcopy(original_manifest)
                    mutate(packet['rows'][0])
                    row = packet['rows'][0]
                    manifest['row_canonical_sha256'][row['id']] = admission.canonical_sha(row)
                    p.write_text(json.dumps(packet), encoding='utf-8')
                    manifest['packet_sha256'] = admission.sha(p)
                    m.write_text(json.dumps(manifest), encoding='utf-8')
                    with self.assertRaises(ValueError):
                        admission.load_packet(p, admission.sha(p), m, admission.sha(m))

    @unittest.skipUnless((admission.OWN / 'BUILD-RECEIPT.json').is_file(), 'packet not yet built')
    def test_copied_original_metadata_tampering_cannot_claim_old_pins(self):
        _, _, manifest_path = self.released()
        original = json.loads(manifest_path.read_text())
        annotations = copy.deepcopy(original)
        annotations['authorized_TRAIN_annotations'][0]['official_answer_offsets'][0]['answer_start'] += 1
        with self.assertRaisesRegex(ValueError, 'annotation metadata'):
            admission._verify_original_metadata(annotations)
        registry = copy.deepcopy(original)
        source = next(iter(registry['registry']['sources'].values()))
        source['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'registry metadata'):
            admission._verify_original_metadata(registry)


if __name__ == '__main__':
    unittest.main()
