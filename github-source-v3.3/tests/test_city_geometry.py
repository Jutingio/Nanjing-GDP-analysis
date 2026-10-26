import importlib.util
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
GEO=importlib.util.find_spec('shapely') is not None and importlib.util.find_spec('pyproj') is not None


@unittest.skipUnless(GEO,'Install requirements-geo.txt for city geometry tests')
class CityGeometryTests(unittest.TestCase):
    def api(self):
        self.assertIsNotNone(importlib.util.find_spec('city_geometry'),'City geometry preparation is missing')
        import city_geometry
        return city_geometry

    def feature(self,code,x,hole=False):
        rings=[[[x,30],[x+.1,30],[x+.1,30.1],[x,30.1],[x,30]]]
        if hole:rings.append([[x+.02,30.02],[x+.02,30.04],[x+.04,30.04],[x+.04,30.02],[x+.02,30.02]])
        return {'type':'Feature','properties':{'regionCode':code,'name':code},'geometry':{'type':'Polygon','coordinates':rings}}

    def test_prepare_other_coordinates_with_holes(self):
        api=self.api()
        result,city=api.prepare_geometry({'type':'FeatureCollection','features':[self.feature('A',110,True),self.feature('B',110.1),self.feature('C',110.2)]},[110.15,30.05],2024)
        self.assertEqual([d['code'] for d in result['districts']],['A','B','C'])
        self.assertEqual(result['project']['originLonLat'],[110.15,30.05])
        self.assertIn(city['type'],('Polygon','MultiPolygon'))
        for district in result['districts']:
            self.assertLess(district['triangulationErrorM2'],.1)
            self.assertTrue(district['faces'])
            self.assertLess(abs(district['anchor'][0]),30)
        self.assertEqual(len(result['districts'][0]['lines']),2)

    def test_duplicate_overlapping_and_wrong_crs_rejected(self):
        api=self.api()
        for features in [[self.feature('A',110),self.feature('A',110.1)],
                         [self.feature('A',110),self.feature('B',110.05)]]:
            with self.assertRaises(ValueError):api.prepare_geometry({'type':'FeatureCollection','features':features},[110,30],2024)
        with self.assertRaises(ValueError):api.prepare_geometry({'type':'FeatureCollection','features':[self.feature('A',110)],'crs':{'type':'name','properties':{'name':'EPSG:3857'}}},[110,30],2024)

    def test_origin_is_local_and_camera_loops(self):
        api=self.api()
        frame=api.LocalFrame(12,45)
        self.assertLess(max(abs(v) for v in frame.to_scene(12,45)),1e-8)
        self.assertGreater(frame.to_scene(12.01,45)[0],0)
        self.assertEqual(api.camera_state(0,[12,45],200000),api.camera_state(60,[12,45],200000))
        self.assertEqual(api.camera_state(25,[12,45],200000)['lon'],12)

    def test_coarse_triangles_stay_above_the_globe(self):
        api=self.api()
        feature=self.feature('A',12)
        feature['geometry']['coordinates']=[[[12,45],[13,45],[13,46],[12,46],[12,45]]]
        result,_=api.prepare_geometry({'type':'FeatureCollection','features':[feature]},[12.5,45.5],2024)
        from pyproj import Transformer
        reverse=Transformer.from_crs(4978,4979,always_xy=True)
        local=api.LocalFrame(12.5,45.5);district=result['districts'][0]
        for face in district['faces']:
            center=[sum(district['vertices'][v][i] for v in face)/3*1000 for i in range(3)]
            ecef=[local.origin[i]+sum(local.rows[j][i]*center[j] for j in range(3)) for i in range(3)]
            self.assertGreater(reverse.transform(*ecef)[2],0)

    def test_polygon_z_and_redundant_shared_vertices(self):
        api=self.api();a=self.feature('A',110);b=self.feature('B',110.1)
        a['geometry']['coordinates'][0].insert(2,[110.1,30.05])
        for feature in [a,b]:
            feature['geometry']['coordinates']=[[[x,y,0] for x,y in ring] for ring in feature['geometry']['coordinates']]
        result,_=api.prepare_geometry({'type':'FeatureCollection','features':[a,b]},[110.05,30.05],2024)
        self.assertEqual(len(result['districts']),2)
