import ast
import copy
import unittest
from pathlib import Path
from unittest.mock import patch

import ghostlab_registry as registry
from ghostlab_policy import default_ghostlab_blueprint, validate_ghostlab_blueprint


class GhostLabRegistryTest(unittest.TestCase):
    def test_all_schemas_validate_defaults_and_reject_forged_policy(self):
        for key in registry.TEMPLATES:
            with self.subTest(template=key):
                definition = registry.get_template(key)
                blueprint = default_ghostlab_blueprint(key)
                self.assertTrue(validate_ghostlab_blueprint(key, blueprint)['valid'])
                self.assertNotIn('?', definition['icon'])
                self.assertFalse(registry.template_available(key, 'runtime'))
                for name, field in definition['fields'].items():
                    if not field['editable']:
                        forged = dict(blueprint, **{name: 'forged'})
                        self.assertFalse(validate_ghostlab_blueprint(key, forged)['valid'])

    def test_unregistered_and_planned_templates_are_not_available(self):
        for key in ('unknown', *registry.PLANNED_CONTRACTS):
            for action in ('creation', 'publication', 'runtime'):
                self.assertFalse(registry.template_available(key, action))
            self.assertFalse(validate_ghostlab_blueprint(key, {'notes': 'hello'})['valid'])

    def test_new_definition_uses_generic_schema_without_other_lists(self):
        definition = registry.get_template('system_log_reader')
        definition.update(id='test_definition', source_tool_id=None,
                          fields={'amount': {'type': 'number', 'default': 2,
                                  'minimum': 1, 'maximum': 3, 'integer': True, 'editable': True}})
        with patch.dict(registry.TEMPLATES, test_definition=definition):
            self.assertEqual(default_ghostlab_blueprint('test_definition'), {'amount': 2})
            self.assertTrue(validate_ghostlab_blueprint('test_definition', {'amount': 2})['valid'])
            self.assertIn('test_definition', [t['id'] for t in registry.public_templates()])
            for value in (True, 1.5, 4, float('nan'), float('inf')):
                self.assertFalse(validate_ghostlab_blueprint('test_definition', {'amount': value})['valid'])
            self.assertFalse(registry.template_available('test_definition', 'runtime'))

    def test_switches_are_independent_and_runtime_flag_is_not_executor(self):
        item = registry.get_template('system_log_reader')
        item.update(creation_enabled=False, publication_enabled=True, runtime_enabled=True)
        with patch.dict(registry.TEMPLATES, system_log_reader=item):
            self.assertFalse(registry.template_available(item['id'], 'creation'))
            self.assertTrue(registry.template_available(item['id'], 'publication'))
            self.assertFalse(registry.template_available(item['id'], 'runtime'))
            self.assertNotIn(item['id'], [t['id'] for t in registry.public_templates()])

    def test_legacy_contract_compatibility_and_unknown_versions(self):
        artifact = dict(template_id='system_log_reader', schema_version=1,
                        policy_version=1, runtime_contract='system_logs')
        self.assertTrue(registry.artifact_compatible(artifact, 'system_log_reader'))
        for field, value in (('contract_version', 99), ('schema_version', 99),
                             ('policy_version', 99), ('presentation_id', 'injected')):
            self.assertFalse(registry.artifact_compatible(dict(artifact, **{field: value}), 'system_log_reader'))

    def test_copies_do_not_mutate_registry(self):
        before = copy.deepcopy(registry.TEMPLATES)
        registry.get_template('system_log_reader')['fields'].clear()
        registry.public_templates()[0]['fields'].clear()
        self.assertEqual(before, registry.TEMPLATES)

    def test_every_system_tool_requires_explicit_assignment(self):
        # Parse source without importing run.py or opening a database.
        path = Path(__file__).resolve().parents[1] / 'run.py'
        tree = ast.parse(path.read_text(encoding='utf-8'))
        node = next(n for n in tree.body if isinstance(n, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == 'PRO_SYSTEM_TOOLS' for t in n.targets))
        tools = ast.literal_eval(node.value)
        registry.validate_pro_tool_assignments(tools)
        with self.assertRaises(ValueError):
            registry.validate_pro_tool_assignments(tools + [{'id': 'forgotten'}])
