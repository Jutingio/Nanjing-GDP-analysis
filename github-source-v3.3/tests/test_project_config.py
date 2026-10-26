import copy
import importlib.util
import sys
import unittest
import uuid
from contextlib import contextmanager
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))


@contextmanager
def test_directory():
    # Python 3.13's Windows private TemporaryDirectory ACL conflicts with restricted tokens.
    parent = (ROOT / 'output/test-tmp').resolve()
    folder = parent / uuid.uuid4().hex
    folder.mkdir(parents=True)
    try:
        yield folder
    finally:
        if folder.resolve().parent != parent:
            raise ValueError('Unexpected test directory')
        for path in folder.iterdir():
            path.unlink()
        folder.rmdir()


class ProjectConfigTests(unittest.TestCase):
    def api(self):
        self.assertIsNotNone(importlib.util.find_spec('project_config'), 'Configuration loader is missing')
        import project_config
        return project_config

    def resources(self, api):
        config = api.load_config()
        missing = [k for k in api.PATH_KEYS if k != 'output' and not api.input_path(config,k).is_file()]
        if missing:
            self.skipTest('Local inputs not distributed: '+', '.join(missing))
        return config

    def test_current_nanjing_inputs(self):
        api = self.api()
        config = self.resources(api)
        result = api.validate_inputs(config)
        self.assertEqual(result['selected'], ['320114', '320102', '320106'])
        self.assertEqual(result['gdp'], 18500.81)
        self.assertEqual(result['camera_frames'], 1801)

    def test_example_validates_without_private_assets(self):
        api = self.api()
        config = api.load_config(ROOT / 'config/example.json')
        self.assertEqual(config['city']['id'], 'example')
        self.assertTrue(config['template'])
        with self.assertRaisesRegex(ValueError, 'template'):
            api.validate_inputs(config)

    def test_unsafe_paths_and_layout_rejected(self):
        api = self.api()
        config = api.load_config()
        for value in ['../outside.json', 'C:/private/file', '/etc/file', 'assets/../../file']:
            bad = copy.deepcopy(config)
            bad['paths']['snapshot'] = value
            with self.assertRaises(ValueError):
                api.validate_config(bad)
        bad = copy.deepcopy(config)
        bad['render']['fps'] = 24
        with self.assertRaises(ValueError):
            api.validate_config(bad)

    def test_wrong_year_and_missing_geometry_rejected(self):
        api = self.api()
        config = self.resources(api)
        bad = copy.deepcopy(config)
        bad['city']['period'] = '2023'
        with self.assertRaisesRegex(ValueError, 'period'):
            api.validate_inputs(bad)
        bad = copy.deepcopy(config)
        bad['paths']['district_geojson'] = 'data/missing.geojson'
        with self.assertRaises(FileNotFoundError):
            api.validate_inputs(bad)

    def test_camera_config_changes_are_used(self):
        api = self.api()
        config = self.resources(api)
        original = api.camera_samples(config)
        altered = copy.deepcopy(config)
        altered['camera']['mode'] = 'track'
        altered['camera']['location_offset'] = [1, 2, 3]
        altered['camera']['lens_scale'] = 2
        changed = api.camera_samples(altered)
        self.assertEqual(changed[0]['location'], [v + d for v, d in zip(original[0]['location'], [1, 2, 3])])
        self.assertEqual(changed[0]['lens'], original[0]['lens'] * 2)

    def test_stale_hud_is_rejected_after_rebuild(self):
        api = self.api()
        check = getattr(api, 'validate_hud_cache', None)
        self.assertTrue(callable(check), 'HUD provenance validation missing')
        (ROOT / 'output/test-tmp').mkdir(parents=True,exist_ok=True)
        with test_directory() as folder:
            root = Path(folder)
            blend = root / 'scene.blend'; blend.write_bytes(b'first scene')
            layer = root / 'always.png'; layer.write_bytes(b'first layer')
            config = {'city': 'A'}
            manifest = {'sourceBlendSha256': api.sha256(blend), 'config': config,
                        'layers': {'always.png': api.sha256(layer)}}
            (root / 'hud-manifest.json').write_text(json.dumps(manifest))
            self.assertEqual(check(root, blend, config), manifest)
            layer.write_bytes(b'stale layer')
            with self.assertRaisesRegex(ValueError, 'HUD'):check(root, blend, config)
            layer.write_bytes(b'first layer')
            blend.write_bytes(b'rebuilt scene with changed statistics')
            with self.assertRaisesRegex(ValueError, 'HUD'):
                check(root, blend, config)

    def test_invalid_geometry_and_credits_rejected(self):
        api = self.api()
        config = api.load_config()
        for key, value in [('sceneUnit', 'feet'), ('originLonLat', [181, 91]),
                           ('presentationOffsetM', float('nan'))]:
            bad = copy.deepcopy(config);bad['geometry'][key] = value
            with self.assertRaises(ValueError):api.validate_config(bad)
        bad = copy.deepcopy(config);del bad['credits']
        with self.assertRaises(ValueError):api.validate_config(bad)

    def test_scene_config_mismatch_rejected(self):
        api = self.api()
        check = getattr(api, 'validate_scene_config', None)
        self.assertTrue(callable(check), 'Scene/config validator missing')
        config = api.load_config()
        self.assertTrue(check(json.dumps(config), config))
        bad = copy.deepcopy(config);bad['city']['period'] = '2023'
        with self.assertRaisesRegex(ValueError, 'config'):
            check(json.dumps(config), bad)

    def test_particle_sequence_mutation_rejected(self):
        api = self.api()
        check = getattr(api, 'validate_particle_sequence', None)
        self.assertTrue(callable(check), 'Particle provenance validation missing')
        import hashlib
        (ROOT / 'output/test-tmp').mkdir(parents=True,exist_ok=True)
        with test_directory() as folder:
            root = Path(folder)
            frame = root / 'particle_000001.png';frame.write_bytes(b'frame')
            digest = hashlib.sha256(hashlib.sha256(b'frame').digest()).hexdigest()
            manifest = {'frames': 1, 'sequenceSha256': digest}
            check(root, manifest)
            frame.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'Particle'):
                check(root, manifest)


if __name__ == '__main__':
    unittest.main()
