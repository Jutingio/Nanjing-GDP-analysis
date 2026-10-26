"""Validate explicit project inputs without modifying source data or original assets."""
import argparse
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from project_config import load_config, validate_inputs, output_path, sha256, input_path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--config', default='config/nanjing.json')
parser.add_argument('--schema-only', action='store_true')
args = parser.parse_args()
config = load_config(args.config)
if args.schema_only:
    print('CONFIG_VALID', config['city']['id'])
else:
    result = validate_inputs(config)
    result['inputs'] = {k: {'path': v, 'sha256': sha256(input_path(config, k))}
                        for k, v in config['paths'].items() if k != 'output'}
    dest = output_path(config, 'input-validation.json')
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print('INPUTS_VALID', json.dumps({k: v for k, v in result.items() if k != 'inputs'}))
