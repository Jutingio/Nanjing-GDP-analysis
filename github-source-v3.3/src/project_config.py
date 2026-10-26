"""Portable project inputs; stdlib only, safe to import outside Blender."""
import copy
import hashlib
import json
import math
import os
import re
import sys
from pathlib import Path, PureWindowsPath

ROOT = Path(__file__).resolve().parents[1]
PATH_KEYS = ('snapshot', 'culture', 'prepared_geo', 'district_geojson', 'city_geojson',
             'base_blend', 'font', 'earth_texture', 'photo', 'camera_track', 'output')


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def relative_path(value):
    if not isinstance(value, str) or not value or '\\' in value or ':' in value:
        raise ValueError('Paths must use project-relative forward slashes')
    path = Path(value)
    if path.is_absolute() or PureWindowsPath(value).is_absolute() or '..' in path.parts:
        raise ValueError('Path escapes project')
    resolved = (ROOT / path).resolve()
    if not resolved.is_relative_to(ROOT):
        raise ValueError('Path escapes project through symlink')
    return resolved


def finite(value):
    return not isinstance(value, bool) and isinstance(value, (float, int)) and math.isfinite(value)


def validate_config(config):
    required = {'schemaVersion','template','city','paths','baseSha256','camera','render','credits','geometry'}
    if not isinstance(config, dict) or set(config) != required:
        raise ValueError('Missing or unknown config fields')
    for key in ('city','paths','camera','render','credits','geometry'):
        if not isinstance(config[key], dict):raise ValueError('Invalid config block: '+key)
    if config.get('schemaVersion') != 1 or not isinstance(config.get('template'), bool):
        raise ValueError('Unsupported config schema')
    for key in ('id', 'name', 'kicker', 'period'):
        if not isinstance(config['city'].get(key), str) or not config['city'][key].strip():
            raise ValueError('Missing city field: ' + key)
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]*',config['city']['id']):
        raise ValueError('city.id must be a simple lowercase slug')
    for key in ('footer','assets'):
        if not isinstance(config['credits'].get(key),str) or not config['credits'][key].strip():
            raise ValueError('Missing credits: '+key)
    geometry = config['geometry']
    if geometry.get('sceneUnit') != 'km' or geometry.get('status') != 'overview_only':
        raise ValueError('Geometry requires km scene units and overview_only status')
    origin = geometry.get('originLonLat')
    if not isinstance(origin,list) or len(origin)!=2 or not all(map(finite,origin)) or not -180<=origin[0]<=180 or not -90<=origin[1]<=90:
        raise ValueError('Invalid geometry ENU origin')
    if not finite(geometry.get('presentationOffsetM')) or type(geometry.get('boundaryYear')) is not int:
        raise ValueError('Invalid geometry offset or boundary year')
    if len(config['city']['period']) != 4 or not config['city']['period'].isdigit():
        raise ValueError('Invalid period')
    for key in PATH_KEYS:
        relative_path(config['paths'][key])
    output = relative_path(config['paths']['output'])
    if not output.is_relative_to(ROOT / 'output') or output == ROOT / 'output':
        raise ValueError('Outputs must be below output/<project>')
    for key in PATH_KEYS:
        if key != 'output' and relative_path(config['paths'][key]).is_relative_to(output):
            raise ValueError('Input cannot be inside output directory')
    render = config['render']
    # The existing HUD and cache choreography are authored against this contract.
    if (render['width'], render['height'], render['fps'], render['duration']) != (1920, 1080, 30, 60):
        raise ValueError('V3 layout requires 1920x1080, 30 fps, 60 seconds; use scale for output size')
    if render['engine'] != 'BLENDER_EEVEE':
        raise ValueError('V3 supports BLENDER_EEVEE only')
    for key, upper in [('scale', 100), ('samples', 4096), ('hud_samples', 4096)]:
        value = render[key]
        if type(value) is not int or not 1 <= value <= upper:
            raise ValueError('Invalid render parameter: ' + key)
    camera = config['camera']
    if camera['mode'] not in ('preserve', 'track'):
        raise ValueError('Invalid camera mode')
    if len(camera['location_offset']) != 3 or not all(map(finite, camera['location_offset'])):
        raise ValueError('Invalid camera offset')
    if not finite(camera['lens_scale']) or camera['lens_scale'] <= 0:
        raise ValueError('Invalid lens scale')
    if camera['mode'] == 'preserve' and (camera['location_offset'] != [0, 0, 0] or camera['lens_scale'] != 1):
        raise ValueError('Set camera mode to track before changing the camera')
    if not isinstance(config.get('baseSha256'), str) or not re.fullmatch('[a-f0-9]{64}',config['baseSha256']):
        raise ValueError('baseSha256 must identify the matching base scene')
    return True


def load_config(path=None):
    path = Path(path or os.environ.get('CITY_FILM_CONFIG', ROOT / 'config/nanjing.json'))
    if not path.is_absolute():
        path = ROOT / path
    config = read_json(path)
    validate_config(config)
    return config


def script_config():
    # Consume just our argument, leaving each existing entry point's CLI intact.
    if '--config' in sys.argv:
        i = sys.argv.index('--config')
        if i + 1 == len(sys.argv):
            raise ValueError('--config requires a file')
        path = sys.argv[i + 1]
        del sys.argv[i:i + 2]
        return load_config(path)
    return load_config()


def input_path(config, key):
    return relative_path(config['paths'][key])


def output_path(config, rel=''):
    root = input_path(config, 'output')
    path = (root / rel).resolve()
    if not path.is_relative_to(root):
        raise ValueError('Output escapes configured directory')
    return path


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def camera_samples(config):
    track = read_json(input_path(config, 'camera_track'))
    samples = copy.deepcopy(track['samples'])
    if track['rotation_mode'] != 'QUATERNION' or len(samples) != 1801:
        raise ValueError('Camera track must contain all 1801 quaternion frames')
    for frame, sample in enumerate(samples, 1):
        if sample['frame'] != frame:
            raise ValueError('Camera frame order mismatch')
        for key, count in [('location', 3), ('rotation_quaternion', 4)]:
            if len(sample[key]) != count or not all(map(finite, sample[key])):
                raise ValueError('Invalid camera vector')
        if not all(finite(sample[key]) and sample[key] > 0 for key in ('lens', 'clip_start', 'clip_end')):
            raise ValueError('Invalid camera scalar')
        if sample['clip_end'] <= sample['clip_start']:
            raise ValueError('Invalid camera clipping range')
        sample['location'] = [a + b for a, b in zip(sample['location'], config['camera']['location_offset'])]
        sample['lens'] *= config['camera']['lens_scale']
    return samples


def validate_inputs(config):
    from v3_core import validate_snapshot
    validate_config(config)
    if config['template']:
        raise ValueError('Example template requires real city inputs before building')
    for key in PATH_KEYS:
        if key != 'output' and not input_path(config, key).is_file():
            raise FileNotFoundError(config['paths'][key])
    if sha256(input_path(config, 'base_blend')) != config['baseSha256']:
        raise ValueError('Base scene hash does not match config')
    data = read_json(input_path(config, 'snapshot'))
    validate_snapshot(data)
    if data['period'] != config['city']['period']:
        raise ValueError('Config/data period mismatch')
    geo = read_json(input_path(config, 'prepared_geo'))
    metadata = geo.get('project',{})
    for key in ('originLonLat','sceneUnit','boundaryYear'):
        if metadata.get(key)!=config['geometry'][key]:
            raise ValueError('Prepared geometry metadata mismatch: '+key)
    for key in ('district_geojson','city_geojson'):
        if metadata.get(key+'Sha256')!=sha256(input_path(config,key)):
            raise ValueError('Prepared geometry / GeoJSON hash mismatch')
    codes = {d['code'] for d in geo['districts']}
    features = read_json(input_path(config, 'district_geojson'))['features']
    boundary_codes = {str(f['properties']['regionCode']) for f in features}
    if not set(data['selection']['codes']) <= codes or codes != boundary_codes:
        raise ValueError('Selected regions / prepared geometry / GeoJSON mismatch')
    for source in data['sources']:
        if sha256(relative_path(source['rawFile'])) != source['sha256']:
            raise ValueError('Statistical source hash mismatch: ' + source['id'])
    culture = read_json(input_path(config, 'culture'))
    if sha256(input_path(config, 'photo')) != culture['photo']['sha256']:
        raise ValueError('Photo hash mismatch')
    return {'selected': data['selection']['codes'], 'gdp': data['cityTotals']['gdp']['value'],
            'districts': len(codes), 'camera_frames': len(camera_samples(config))}


def input_fingerprints(config):
    return {key: sha256(input_path(config,key)) for key in PATH_KEYS if key!='output'}


def validate_scene_config(serialized, config):
    if json.loads(serialized)!=config:
        raise ValueError('Scene and current config differ; rebuild first')
    return True


def validate_hud_cache(directory, blend, config):
    directory = Path(directory)
    manifest = read_json(directory/'hud-manifest.json')
    if manifest['sourceBlendSha256']!=sha256(blend) or manifest['config']!=config:
        raise ValueError('HUD belongs to another scene/config; regenerate all layers')
    if not manifest.get('layers'):raise ValueError('HUD manifest has no layers')
    for name,digest in manifest['layers'].items():
        if Path(name).name!=name or sha256(directory/name)!=digest:
            raise ValueError('HUD layer hash mismatch')
    return manifest


def validate_particle_sequence(directory, manifest):
    digest=hashlib.sha256()
    for frame in range(1,manifest['frames']+1):
        digest.update(bytes.fromhex(sha256(Path(directory)/f'particle_{frame:06d}.png')))
    if digest.hexdigest()!=manifest['sequenceSha256']:
        raise ValueError('Particle sequence hash mismatch; regenerate sequence')
