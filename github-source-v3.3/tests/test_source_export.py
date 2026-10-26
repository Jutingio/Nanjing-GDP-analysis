import importlib.util
import sys
import unittest
from pathlib import Path
from test_project_config import test_directory

ROOT=Path(__file__).resolve().parents[1]


class SourceExportTests(unittest.TestCase):
    def api(self):
        path=ROOT/'scripts/export_source.py'
        self.assertTrue(path.is_file(),'Safe source export is missing')
        spec=importlib.util.spec_from_file_location('export_source',path)
        api=importlib.util.module_from_spec(spec);spec.loader.exec_module(api)
        return api

    def test_export_excludes_originals_secrets_and_generated_assets(self):
        api=self.api()
        with test_directory() as root:
            # Cleanup helper expects flat paths, so keep fixtures flat except actual source dirs.
            files={'README.md':'example','src/a.py':'print(1)','config/demo.local.json':'{}',
                   'config/example.json':'{}','data/generated-demo/base.blend':'binary',
                   'assets/photo.jpg':'binary','.env':'secret','render/movie.mp4':'binary'}
            for name,text in files.items():
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
            self.assertEqual(api.collect_sources(root),['README.md','config/example.json','src/a.py'])
            for name in files:(root/name).unlink()
            for p in sorted((p for p in root.rglob('*') if p.is_dir()),key=lambda p:len(p.parts),reverse=True):p.rmdir()

    def test_source_token_is_rejected_without_echoing_value(self):
        api=self.api()
        with test_directory() as root:
            token='ghp_'+'a'*36
            (root/'README.md').write_text(token)
            with self.assertRaisesRegex(ValueError,'github-token') as result:api.collect_sources(root)
            self.assertNotIn(token,str(result.exception))
