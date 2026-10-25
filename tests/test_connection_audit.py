import importlib.util
import json
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('audit', Path(__file__).resolve().parents[1] / 'scripts/audit_connections.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

class ManifestEvidenceTests(unittest.TestCase):
    def test_serialize_catalogue_roundtrips_html_parser_payload_without_less_than(self):
        data = {'<!--<script>': ['<!--<script>', '</script><script>alert(1)</script>', 'é < > &']}
        self.assertTrue(callable(getattr(audit, 'serialize_catalogue', None)))
        encoded = audit.serialize_catalogue(data)
        self.assertNotIn('<', encoded)
        self.assertIn(r'\u003c', encoded)
        self.assertEqual(json.loads(encoded), data)

    def test_declared_class_requires_matching_domain(self):
        self.assertEqual(audit.verified_class({'status': 'ok', 'domain': 'light', 'manifest': {'domain': 'light', 'iot_class': 'local_polling'}}), 'local_polling')
        self.assertIsNone(audit.verified_class({'status': 'ok', 'domain': 'light', 'manifest': {'domain': 'other', 'iot_class': 'local_polling'}}))
        self.assertIsNone(audit.verified_class({'status': 'ok', 'domain': 'light', 'manifest': {'domain': 'light', 'description': 'API LAN Bluetooth'}}))
        self.assertIsNone(audit.verified_class({'status': 'unavailable', 'domain': 'light', 'manifest': {'domain': 'light', 'iot_class': 'cloud_push'}}))

    def test_apply_evidence_preserves_existing_route_and_adds_documented_local(self):
        record = {'domain': 'lamp', 'local_option': False, 'cloud_option': True, 'methods': [{'url': 'https://github.com/a/b', 'iot_class': ''}, {'url': 'https://example.com', 'iot_class': 'cloud_push'}]}
        evidence = {'repository': 'a/b', 'domain': 'lamp', 'status': 'ok', 'url': 'https://raw.githubusercontent.com/a/b/HEAD/custom_components/lamp/manifest.json', 'sha256': 'abc', 'checked_at': '2026-10-25', 'manifest': {'domain': 'lamp', 'iot_class': 'local_polling'}}
        self.assertEqual(audit.apply_evidence([record], [evidence]), 1)
        self.assertTrue(record['local_option'])
        self.assertTrue(record['cloud_option'])
        self.assertEqual(record['methods'][0]['connection_evidence']['url'], evidence['url'])
        self.assertEqual(record['methods'][1]['iot_class'], 'cloud_push')
        self.assertEqual(audit.apply_evidence([record], [evidence]), 0)

    def test_reviewed_docs_classify_only_exact_method_without_guessing_polling(self):
        record = {'id': 'brand:test', 'domain': 'test', 'local_option': False, 'cloud_option': False, 'methods': [{'url': 'https://example.com/local', 'iot_class': ''}, {'url': 'https://example.com/other', 'iot_class': ''}]}
        row = {'record_id': 'brand:test', 'method_url': 'https://example.com/local', 'connection_scope': 'local', 'source_url': 'https://example.com/docs', 'evidence': 'Connects to the device LAN IP address.'}
        self.assertEqual(audit.apply_reviewed_docs([record], [row]), 1)
        self.assertTrue(record['local_option'])
        self.assertFalse(record['cloud_option'])
        self.assertEqual(record['methods'][0]['connection_scope'], 'local')
        self.assertFalse(record['methods'][0]['iot_class'])
        self.assertNotIn('connection_scope', record['methods'][1])
        self.assertEqual(audit.apply_reviewed_docs([record], [row]), 0)

    def test_abstract_platform_does_not_imply_local_or_cloud(self):
        record = {'id': 'core:sensor', 'domain': 'sensor', 'local_option': False, 'cloud_option': False, 'methods': [{'iot_class': ''}]}
        row = {'id': 'core:sensor', 'source_url': 'https://example.com/manifest.json', 'manifest': {'domain': 'sensor', 'integration_type': 'entity'}}
        self.assertEqual(audit.apply_platform_evidence([record], [row]), 1)
        self.assertEqual(record['connection_scope'], 'platform')
        self.assertFalse(record['local_option'])
        self.assertFalse(record['cloud_option'])
        other = dict(record, id='core:other', domain='other')
        other.pop('connection_scope')
        self.assertEqual(audit.apply_platform_evidence([other], [row]), 0)
        self.assertNotIn('connection_scope', other)

if __name__ == '__main__':
    unittest.main()
