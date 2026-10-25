"""Execute the catalogue's actual JavaScript connection and filter functions."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ConnectionUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / 'index.html').read_text()
        node = shutil.which('node')
        if not node:
            raise RuntimeError('Node is required to execute connection UI regression tests')
        cls.node = node
        match = re.search(r'<script>\s*(.*?)</script>', cls.html, re.S)
        assert match is not None
        script = match.group(1)
        cls.functions = script[script.index('function normalize('):script.index('function render(')]
        cls.functions += script[script.index('function methodLabel('):script.index('function openEntry(')]

    def js(self, expression, records=None, filter_value='all', query=''):
        records = records or []
        setup = (
            'const records=' + json.dumps(records) + ';'
            'const search={value:' + json.dumps(query) + '};'
            'const filter={value:' + json.dumps(filter_value) + '};'
            'const index=records.map(record=>({record,text:normalize(record.name)}));'
        )
        result = subprocess.run(
            [self.node, '-e', self.functions + setup + 'console.log(JSON.stringify(' + expression + '));'],
            capture_output=True, text=True, check=True,
        )
        return json.loads(result.stdout)

    @staticmethod
    def record(name='Example', classes=(), **overrides):
        result = dict(name=name, display_name=name, aliases=[], standards=[],
                      local_option=False, cloud_option=False,
                      methods=[{'iot_class': value} for value in classes])
        result.update(overrides)
        return result

    def test_calculated_and_assumed_state_have_distinct_meanings(self):
        for kind, row_label, method_label in [
                ('calculated', 'Virtual / calculated', 'Virtual / calculated'),
                ('assumed_state', 'State feedback limited · connection unverified',
                 'State feedback limited')]:
            with self.subTest(kind=kind):
                record = self.record(classes=[kind])
                self.assertEqual(self.js('connection(records[0])[0]', [record]), row_label)
                self.assertEqual(self.js('methodLabel(records[0].methods[0])', [record]), method_label)

    def test_virtual_filter_separates_virtual_only_methods_from_review(self):
        records = [self.record('Calculated', ['calculated']),
                   self.record('Assumed', ['assumed_state']),
                   self.record('Both virtual', ['calculated', 'assumed_state']),
                   self.record('Unknown'), self.record('Unspecified', ['']),
                   self.record('Partly unknown', ['calculated', '']),
                   self.record('Local', ['local_push'], local_option=True),
                   self.record('Cloud', ['cloud_polling'], cloud_option=True),
                   self.record('Mixed routes', ['calculated', 'local_push'], local_option=True)]
        self.assertEqual(self.js('filtered().map(r=>r.name)', records, 'virtual'),
                         ['Calculated'])
        self.assertEqual(self.js('filtered().map(r=>r.name)', records, 'review'),
                         ['Assumed', 'Both virtual', 'Partly unknown', 'Unknown', 'Unspecified'])
        self.assertEqual(self.js('filtered().map(r=>r.name)', records, 'virtual', 'calculated'),
                         ['Calculated'])
        select = re.search(r'<select id="connection-filter">(.*?)</select>', self.html, re.S)
        assert select is not None
        self.assertIn('<option value="virtual">Virtual / calculated</option>', select.group(1))

    def test_existing_routes_and_standards_keep_their_labels(self):
        cases = [({'local_option': True}, ['Local option documented', 'local']),
                 ({'cloud_option': True}, ['Cloud option documented', 'cloud']),
                 ({'local_option': True, 'cloud_option': True}, ['Local & cloud options', 'mixed']),
                 ({'standards': ['Zigbee']}, ['Standards-based · model check', ''])]
        for overrides, label in cases:
            with self.subTest(overrides=overrides):
                self.assertEqual(self.js('connection(records[0])', [self.record(**overrides)]), label)
        records = [self.record('Local', ['local_push'], local_option=True),
                   self.record('Cloud', ['cloud_polling'], cloud_option=True),
                   self.record('Both', ['local_push', 'cloud_polling'], local_option=True, cloud_option=True)]
        self.assertEqual(self.js('filtered().map(r=>r.name)', records, 'local'), ['Both', 'Local'])
        self.assertEqual(self.js('filtered().map(r=>r.name)', records, 'cloud'), ['Both', 'Cloud'])
        self.assertEqual(self.js('filtered().length', records), len(records))

    def test_virtual_labels_take_precedence_over_metadata_booleans_and_standards(self):
        for kind, label in [('calculated', 'Virtual / calculated')]:
            for local, cloud in [(False, False), (True, False), (False, True), (True, True)]:
                with self.subTest(kind=kind, local=local, cloud=cloud):
                    record = self.record(classes=[kind], local_option=local,
                                         cloud_option=cloud, standards=['Zigbee'])
                    self.assertEqual(self.js('connection(records[0])', [record]), [label, 'virtual'])
                    self.assertEqual(self.js('filtered().length', [record], 'review'), 0)
                    self.assertEqual(self.js('filtered().length', [record], 'virtual'), 1)

    def test_virtual_records_with_preserved_route_flags_are_excluded_from_route_filters(self):
        for methods in [[{'iot_class': 'calculated'}], [{'connection_scope': 'virtual'}]]:
            for local, cloud in [(True, False), (False, True), (True, True)]:
                with self.subTest(methods=methods, local=local, cloud=cloud):
                    record = self.record(methods=methods, local_option=local, cloud_option=cloud)
                    self.assertEqual(self.js('connection(records[0])', [record]),
                                     ['Virtual / calculated', 'virtual'])
                    for route in ['local', 'cloud']:
                        with self.subTest(route=route):
                            self.assertEqual(self.js('filtered().length', [record], route), 0)
                    self.assertEqual(self.js('filtered().length', [record], 'virtual'), 1)

    def test_assumed_state_uses_documented_routes_or_remains_in_review(self):
        for local, cloud, label in [
                (False, False, ['State feedback limited · connection unverified', '']),
                (True, False, ['Local option documented', 'local']),
                (False, True, ['Cloud option documented', 'cloud']),
                (True, True, ['Local & cloud options', 'mixed'])]:
            with self.subTest(local=local, cloud=cloud):
                record = self.record(classes=['assumed_state', 'assumed_state'],
                                     local_option=local, cloud_option=cloud, standards=['Zigbee'])
                self.assertFalse(self.js('isVirtual(records[0])', [record]))
                self.assertEqual(self.js('connection(records[0])', [record]), label)
                self.assertEqual(self.js('filtered().length', [record], 'review'),
                                 int(not local and not cloud))
                self.assertEqual(self.js('filtered().length', [record], 'virtual'), 0)

    def test_method_connection_scope_is_distinct_from_registry_scope(self):
        for scope in ['local', 'cloud', 'virtual']:
            for iot_class in ['', 'assumed_state', 'calculated']:
                with self.subTest(scope=scope, iot_class=iot_class):
                    record = self.record(methods=[{'iot_class': iot_class,
                                                  'connection_scope': scope,
                                                  'scope': 'hacs'}])
                    virtual = iot_class == 'calculated' or scope == 'virtual'
                    self.assertEqual(self.js('isVirtual(records[0])', [record]), virtual)
                    self.assertEqual(self.js('filtered().length', [record], 'virtual'), int(virtual))
                    self.assertEqual(self.js('filtered().length', [record], 'review'), int(not virtual))
                    label = ('Virtual / calculated' if virtual else
                             'Documented local connection' if scope == 'local' else
                             'Documented cloud connection')
                    self.assertEqual(self.js('methodLabel(records[0].methods[0])', [record]), label)
        for scope in ['local', 'cloud', 'virtual']:
            with self.subTest(registry_scope=scope):
                record = self.record(methods=[{'scope': scope, 'iot_class': 'assumed_state'}])
                self.assertFalse(self.js('isVirtual(records[0])', [record]))
                self.assertEqual(self.js('methodLabel(records[0].methods[0])', [record]),
                                 'State feedback limited')
                self.assertEqual(self.js('filtered().length', [record], 'review'), 1)
        mixed_methods = [{'iot_class': 'calculated'}, {'connection_scope': 'virtual'}]
        mixed = self.record(methods=mixed_methods)
        self.assertTrue(self.js('isVirtual(records[0])', [mixed]))
        mixed_methods.append({'connection_scope': 'local'})
        self.assertFalse(self.js('isVirtual(records[0])', [mixed]))

    def test_platform_has_separate_label_and_filter_without_route_claims(self):
        for classes in [[], ['assumed_state'], ['calculated']]:
            for local, cloud in [(False, False), (True, False), (False, True), (True, True)]:
                with self.subTest(classes=classes, local=local, cloud=cloud):
                    record = self.record(classes=classes, connection_scope='platform',
                                         local_option=local, cloud_option=cloud)
                    self.assertEqual(self.js('connection(records[0])', [record]),
                                     ['Platform / provider-dependent', 'platform'])
                    for filter_value in ['review', 'local', 'cloud', 'virtual']:
                        self.assertEqual(self.js('filtered().length', [record], filter_value), 0)
                    self.assertEqual(self.js('filtered().length', [record], 'platform'), 1)
        records = [self.record('Sensor platform', connection_scope='platform'),
                   self.record('Unknown'), self.record('Calculated', ['calculated']),
                   self.record('Hardware', integration_type='hardware'),
                   self.record('System', integration_type='system')]
        self.assertEqual(self.js('filtered().map(r=>r.name)', records, 'platform'), ['Sensor platform'])
        self.assertEqual(self.js('filtered().map(r=>r.name)', records, 'review'),
                         ['Hardware', 'System', 'Unknown'])
        self.assertEqual(self.js('filtered().map(r=>r.name)', records, 'platform', 'sensor'),
                         ['Sensor platform'])
        select = re.search(r'<select id="connection-filter">(.*?)</select>', self.html, re.S)
        assert select is not None
        self.assertIn('<option value="platform">Platform / provider-dependent</option>', select.group(1))

    def test_connection_explanation_is_below_controls(self):
        controls_end = self.html.index('<div class="directory-tools">')
        results_start = self.html.index('<div id="catalogue-list"')
        explanation = self.html[controls_end:results_start]
        self.assertIn('Labels reflect documented connection routes, not installation tests.', explanation)
        self.assertIn('A local route can still require online setup or extra hardware.', explanation)

    def test_unverified_label_matches_filter_and_row(self):
        record = self.record()
        self.assertEqual(self.js('connection(records[0])[0]', [record]), 'Connection type unverified')
        select = re.search(r'<select id="connection-filter">(.*?)</select>', self.html, re.S)
        assert select is not None
        self.assertIn('<option value="review">Connection type unverified</option>', select.group(1))
        self.assertNotIn('Needs a connection check', select.group(1))


if __name__ == '__main__':
    unittest.main()
