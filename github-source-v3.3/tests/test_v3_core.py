import unittest, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from v3_core import share_pct, stage, select_regions, validate_snapshot

class V3Tests(unittest.TestCase):
    def test_city_denominator_not_local_max(self):
        self.assertEqual(share_pct(50, 200), 25)
        self.assertEqual(share_pct(0, 200), 0)
        self.assertAlmostEqual(share_pct(3181.14,18500.81),17.19459850676808)
    def test_invalid_percent_never_silently_zero(self):
        for value,total in [(None,200),(3,0),(3,-1),(-1,200),(300,200),(float('nan'),2)]:
            with self.subTest(value=value,total=total), self.assertRaises(ValueError): share_pct(value,total)
    def test_one_district_after_intro(self):
        selected=['A','B','C']
        for t in [0,6,12,18,20]: self.assertIsNone(stage(t,selected)['focus'])
        for t in [22,25,28.9]:
            state=stage(t,selected);self.assertEqual(state['focus'],'A');self.assertEqual(state['detail'],1)
        self.assertEqual(stage(32,selected)['focus'],'B')
        self.assertEqual(stage(40,selected)['focus'],'C')
        self.assertIsNone(stage(50,selected)['focus'])
    def test_reproducible_unique_selection(self):
        a=select_regions(list('ABCDEFGHI'),20260911)
        self.assertEqual(a,select_regions(list('ABCDEFGHI'),20260911))
        self.assertEqual(len(set(a)),3)
    def test_mixed_year_rejected(self):
        with self.assertRaises(ValueError):
            validate_snapshot({'period':'2024','cityTotals':{'gdp':{'period':'2025','value':100}},'regions':[]})

if __name__=='__main__': unittest.main()
