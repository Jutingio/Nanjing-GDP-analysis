import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from project_config import read_json
from v3_core import validate_snapshot
try:
    import jsonschema
except ImportError:
    jsonschema = None


class SchemaTests(unittest.TestCase):
    @unittest.skipUnless(jsonschema, 'Install requirements-dev.txt to check JSON Schema')
    def test_current_and_template_configs_match_schema(self):
        schema = read_json(ROOT / 'config/project.schema.json')
        jsonschema.Draft202012Validator.check_schema(schema)
        for name in ['nanjing', 'example']:
            jsonschema.validate(read_json(ROOT / f'config/{name}.json'), schema)
        bad = read_json(ROOT / 'config/example.json')
        bad['render']['samples'] = 0
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(bad, schema)

    @unittest.skipUnless(jsonschema, 'Install requirements-dev.txt to check JSON Schema')
    def test_snapshot_and_synthetic_example_match_schema(self):
        schema = read_json(ROOT / 'data/schemas/snapshot.schema.json')
        jsonschema.Draft202012Validator.check_schema(schema)
        for path in ['data/snapshot.json', 'data/examples/snapshot.json']:
            data = read_json(ROOT / path)
            jsonschema.validate(data, schema)
            validate_snapshot(data)

    def test_published_gdp_difference_is_not_redistributed(self):
        from decimal import Decimal
        data = read_json(ROOT / 'data/nanjing-gdp-boards-2024.json')
        values = data['boards']
        total = sum((Decimal(str(v)) for v in values.values()), Decimal(0))
        self.assertEqual(total, Decimal('18479.96'))
        self.assertEqual(Decimal(str(data['cityTotal'])) - total, Decimal('20.85'))


if __name__ == '__main__':
    unittest.main()
