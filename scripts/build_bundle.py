"""Package the verified snapshot with original minute observations for offline reuse."""
import gzip,hashlib,json,shutil,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sample=root/'sample';sample.mkdir(exist_ok=True)
for source in (root/'data'/'processed').glob('*'):
    if source.suffix=='.jsonl':
        with source.open('rb') as incoming,(sample/(source.name+'.gz')).open('wb') as destination:
            with gzip.GzipFile(filename='',fileobj=destination,mode='wb',mtime=0) as outgoing:shutil.copyfileobj(incoming,outgoing)
    elif source.suffix=='.json':shutil.copyfile(source,sample/source.name)
provenance=[]
for source in sorted((root/'data'/'cache').glob('*.json')):
    d=json.loads(source.read_text());provenance.append({k:d[k] for k in ('url','fetched_at','sha256')})
(root/'outputs'/'provenance.json').write_text(json.dumps(provenance,indent=2))
files=[p for p in root.rglob('*') if p.is_file() and not any(x in {'data','__pycache__','.git','.venv'} for x in p.relative_to(root).parts) and p.name!='bundle_manifest.json']
manifest={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}
manifest_path=root/'bundle_manifest.json';manifest_path.write_text(json.dumps(manifest,indent=2));files.append(manifest_path)
archive=root.parent/'kalshi-sports-intelligence.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in sorted(files):z.write(p,Path(root.name)/p.relative_to(root))
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
print(json.dumps({'archive':str(archive),'bytes':archive.stat().st_size,'files':len(files),'source_requests':len(provenance)},indent=2))
