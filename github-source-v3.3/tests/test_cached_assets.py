import unittest
from pathlib import Path
from PIL import Image
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
class CachedAssetTests(unittest.TestCase):
    def test_permanent_hud_does_not_contain_timed_panels(self):
        path=ROOT/'output/nanjing/render/hud-cache/always.png'
        if not path.is_file():self.skipTest('Native cached assets have not been exported')
        a=np.array(Image.open(path).convert('RGBA'))[...,3]
        self.assertTrue(np.any(a[:100]>0),'Header unexpectedly empty')
        self.assertFalse(np.any(a[123:383,34:314]>0),'Intro panel leaked into permanent HUD')
        self.assertFalse(np.any(a[153:378,642:927]>0),'District panel leaked into permanent HUD')
if __name__=='__main__':unittest.main()
