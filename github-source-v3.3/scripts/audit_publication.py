"""Read-only, redacted publication inventory. Never stages, deletes or rewrites history."""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
TEXT = {'.py', '.md', '.txt', '.json', '.toml', '.yaml', '.yml', '.cff', '.log', '.ini', '.cfg', '.csv'}
PATTERNS = {
    'private-key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'github-token': re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b'),
    'aws-access-id': re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    'api-token': re.compile(r'\bsk-[A-Za-z0-9_-]{24,}\b'),
    'credential-assignment': re.compile(r'''(?i)(?:api[_-]?key|access[_-]?token|password|secret)\s*[:=]\s*["'][^"'\s]{8,}["']'''),
    'personal-path': re.compile(r'(?:[A-Za-z]:[/\\]+Users[/\\]+[^/\\\s"\']+|/(?:Users|home)/[^/\s"\']+)'),
}


def scan_text(text):
    return [{'kind': kind, 'line': text.count('\n', 0, match.start()) + 1}
            for kind, regex in PATTERNS.items() for match in regex.finditer(text)]


def git(*args):
    return subprocess.run(['git', '-C', str(ROOT), *args], capture_output=True, check=False)


def audit():
    inventory = []; findings = []
    for path in ROOT.rglob('*'):
        if not path.is_file() or '.git' in path.relative_to(ROOT).parts:
            continue
        rel = path.relative_to(ROOT).as_posix(); size = path.stat().st_size
        if path.suffix.lower() in TEXT and size <= 5_000_000:
            for hit in scan_text(path.read_text(encoding='utf-8', errors='replace')):
                findings.append(dict(path=rel, **hit))
        if size >= 10 * 1024 * 1024 or path.suffix.lower() in {'.blend', '.mp4', '.mov'}:
            inventory.append({'path': rel, 'bytes': size})
    present = git('rev-parse', '--show-toplevel')
    history = {'status': 'no-git-repository', 'blobsScanned': 0, 'findings': [], 'unscannedBlobs': []}
    if present.returncode == 0:
        # Do not accidentally audit an unrelated parent repository.
        top = Path(present.stdout.decode().strip()).resolve()
        if top != ROOT:
            history['status'] = 'parent-repository-not-audited'
        else:
            objects = git('rev-list', '--objects', '--all', '--reflog')
            if objects.returncode:
                history['status'] = 'history-command-failed'
            else:
                history['status'] = 'scanned-reachable-and-reflog-blobs'
                for row in objects.stdout.decode('utf-8', errors='replace').splitlines():
                    oid, _, name = row.partition(' ')
                    if git('cat-file', '-t', oid).stdout.strip() != b'blob':continue
                    size = int(git('cat-file', '-s', oid).stdout)
                    if size > 5_000_000:
                        history['unscannedBlobs'].append({'oid': oid, 'path': name, 'bytes': size});continue
                    raw = git('cat-file', 'blob', oid).stdout
                    if b'\x00' in raw:
                        history['unscannedBlobs'].append({'oid': oid, 'path': name, 'binary': True});continue
                    history['blobsScanned'] += 1
                    history['findings'].extend(dict(oid=oid, path=name, **hit) for hit in scan_text(raw.decode('utf-8', errors='replace')))
    return {'history': history, 'findings': findings, 'largeOrMediaFiles': inventory,
            'limitations': ['Heuristic scan; not a proof of absence of secrets.',
                'Binary contents, oversized text and unreachable Git objects need separate review.',
                'License clearance is not inferred from absence of matches.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='output/publication-audit.json')
    args = parser.parse_args()
    report = audit(); dest = ROOT / args.output; dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'history': report['history']['status'], 'findings': len(report['findings']),
                      'largeOrMediaFiles': len(report['largeOrMediaFiles'])}))
