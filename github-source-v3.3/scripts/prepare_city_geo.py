"""Prepare supplied WGS84 district polygons for the V3 city adapter. No downloads."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from project_config import load_config,input_path,read_json,sha256
from city_geometry import prepare_geometry

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--config',required=True)
    args=parser.parse_args();cfg=load_config(args.config)
    if cfg['city']['id']=='nanjing':raise ValueError('Existing Nanjing inputs are preserved; use a new city config')
    outputs=[input_path(cfg,k) for k in ('prepared_geo','city_geojson')]
    if any(p.exists() for p in outputs):raise FileExistsError('Prepared outputs already exist; use new paths to preserve inputs')
    collection=read_json(input_path(cfg,'district_geojson'))
    result,city=prepare_geometry(collection,cfg['geometry']['originLonLat'],cfg['geometry']['boundaryYear'])
    data=read_json(input_path(cfg,'snapshot'))
    from v3_core import validate_snapshot
    validate_snapshot(data)
    if data['period']!=cfg['city']['period']:raise ValueError('Snapshot/config year mismatch')
    if not set(data['selection']['codes'])<={d['code'] for d in result['districts']}:raise ValueError('Selected districts are missing from GeoJSON')
    city_raw=json.dumps(city,ensure_ascii=False).encode('utf-8')
    import hashlib
    result['project'].update(district_geojsonSha256=sha256(input_path(cfg,'district_geojson')),city_geojsonSha256=hashlib.sha256(city_raw).hexdigest())
    for p in outputs:p.parent.mkdir(parents=True,exist_ok=True)
    outputs[1].write_bytes(city_raw);outputs[0].write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
    print('CITY_GEOMETRY_READY',cfg['city']['id'],len(result['districts']))

if __name__=='__main__':main()
