"""Download the pinned official UCI archive, with atomic replacement and SHA checks."""
from pathlib import Path
import hashlib
import json
import urllib.request
from .config import ROOT


def sha256(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        while chunk:=f.read(1024*1024):h.update(chunk)
    return h.hexdigest()


def main():
    manifest=json.loads((ROOT/'source-manifest.json').read_text())
    target=ROOT/'data/raw/online-retail.zip';target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists() and sha256(target)==manifest['archive_sha256']:
        print('Pinned UCI source already present.');return
    if target.exists():raise RuntimeError('Existing source checksum differs; inspect rather than overwrite')
    temp=target.with_suffix('.download')
    urllib.request.urlretrieve(manifest['download_url'],temp)
    if sha256(temp)!=manifest['archive_sha256']:
        temp.unlink();raise RuntimeError('UCI download checksum changed; review source version')
    temp.replace(target);print('Official UCI source downloaded and checksum verified.')


if __name__=='__main__':main()
