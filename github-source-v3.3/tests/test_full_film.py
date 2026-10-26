import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import v3_core

class FullFilmTests(unittest.TestCase):
    def test_cached_card_changes_with_the_visible_district(self):
        fn=getattr(v3_core,'cache_state',None)
        self.assertTrue(callable(fn),'Full-film cached layer selection is missing')
        codes=['320114','320102','320106']
        for second,code in [(25,codes[0]),(34,codes[1]),(42,codes[2])]:
            state=fn(second,codes)
            self.assertEqual(state['focusFile'],f'focus_{code}.png')
            self.assertEqual(state['detail'],1)
        for second in [0,20,30,38,46,60]:
            self.assertIsNone(fn(second,codes)['focusFile'])
    def test_loop_control_frame_has_same_display_state_as_start(self):
        fn=getattr(v3_core,'cache_state',None)
        self.assertTrue(callable(fn),'Full-film cached layer selection is missing')
        self.assertEqual(fn(0,['A','B','C']),fn(60,['A','B','C']))

if __name__=='__main__':unittest.main()
