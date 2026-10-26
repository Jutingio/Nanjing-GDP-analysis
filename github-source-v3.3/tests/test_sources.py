import unittest,json,hashlib,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class SourceTests(unittest.TestCase):
    def test_saved_source_hashes_and_transcribed_first_column(self):
        data=json.loads((ROOT/'data/snapshot.json').read_text(encoding='utf-8'))
        for source in data['sources']:
            path=ROOT/source['rawFile']
            if not path.is_file():self.skipTest('Source extracts are not in the public source package')
            raw=path.read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),source['sha256'])
            if source['id'] not in data['cityTotals']:continue
            lines=[re.sub(r'^L\d+:\s*','',s).strip() for s in raw.decode('utf-8').splitlines()]
            table={}
            for a,b in zip(lines,lines[1:]):
                name=re.sub(r'\s+','',a)
                if (name=='全市' or name.endswith('区')) and re.fullmatch(r'\d+(\.\d+)?',b):table[name]=float(b)
            metric=source['id'];self.assertEqual(table['全市'],data['cityTotals'][metric]['value'])
            for row in data['regions']:
                with self.subTest(metric=metric,region=row['name']):self.assertEqual(table[row['name']],row['values'][metric])
if __name__=='__main__':unittest.main()
