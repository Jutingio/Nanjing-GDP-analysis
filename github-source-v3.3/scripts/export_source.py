"""Export only reviewable source and source metadata; never copies private binary assets."""
import argparse,hashlib,json,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit_publication import scan_text


def collect_sources(root=ROOT):
    root=Path(root).resolve()
    candidates=[root/name for name in ['.gitignore','.gitattributes','README.md','CITATION.cff','LICENSE']]
    candidates.extend(root.glob('requirements*.txt'))
    for folder in ['src','scripts','tests','config','docs','.github']:
        candidates.extend((root/folder).rglob('*'))
    candidates.extend(root/'data'/name for name in ['snapshot.json','culture-sources.json','verified-table-values.json','nanjing-gdp-boards-2024.json'])
    for folder in ['data/schemas','data/examples']:candidates.extend((root/folder).rglob('*'))
    candidates.extend(root/'assets'/name for name in ['boundary-metadata.json','download-manifest.json'])
    candidates.append(root/'output/README.md')
    selected=[]
    for path in candidates:
        if not path.is_file():continue
        rel=path.relative_to(root).as_posix()
        if '__pycache__' in path.parts or path.name.endswith('.local.json') or path.name.startswith('.env'):continue
        if path.suffix not in ('.py','.md','.json','.yml','.yaml','.txt','.cff') and path.name not in ('.gitignore','.gitattributes','LICENSE'):continue
        if path.is_symlink() or not path.resolve().is_relative_to(root):raise ValueError('Source symlink outside export: '+rel)
        if path.stat().st_size>2_000_000:raise ValueError('Unexpectedly large source file: '+rel)
        for finding in scan_text(path.read_text(encoding='utf-8',errors='strict')):
            raise ValueError(f"Source review required: {rel}:{finding['line']} {finding['kind']}")
        selected.append(rel)
    return sorted(set(selected))


def export_source(destination,root=ROOT):
    root=Path(root).resolve();destination=Path(destination).resolve()
    if not destination.is_relative_to(root/'output'):raise ValueError('Export destination must be inside project output/')
    selected=collect_sources(root);destination.parent.mkdir(parents=True,exist_ok=True)
    manifest={'kind':'source-only','files':[{'path':name,'sha256':hashlib.sha256((root/name).read_bytes()).hexdigest()} for name in selected],
              'licenseStatus':'See docs/licensing.md; third-party assets are not included',
              'reproduction':'Run the offline synthetic demo or prepare licensed inputs for a real city'}
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as archive:
        for name in selected:archive.write(root/name,name)
        archive.writestr('SOURCE-MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    return len(selected)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',default='output/github-source.zip')
    args=p.parse_args();dest=Path(args.output);dest=dest if dest.is_absolute() else ROOT/dest
    print('SOURCE_EXPORTED',export_source(dest),str(dest.relative_to(ROOT)))
