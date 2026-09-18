"""Restore the bundled frozen observations for offline analysis."""
import gzip,shutil
from pathlib import Path
root=Path(__file__).resolve().parents[1]
destination=root/'data'/'processed';destination.mkdir(parents=True,exist_ok=True)
for source in (root/'sample').glob('*'):
    if source.suffix=='.gz':
        with gzip.open(source,'rb') as incoming,(destination/source.stem).open('wb') as outgoing:shutil.copyfileobj(incoming,outgoing)
    elif source.suffix=='.json':shutil.copyfile(source,destination/source.name)
print('Frozen sample restored to',destination)
