#!/usr/bin/env python3
from pathlib import Path
import argparse,json,hashlib,sys

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--project-root',default='.'); ap.add_argument('--manifest',default='release-manifest.json'); a=ap.parse_args()
    root=Path(a.project_root).resolve(); m=Path(a.manifest); m=m if m.is_absolute() else Path.cwd()/m
    data=json.loads(m.read_text()); issues=[]
    for r in data['files']:
        p=root/r['path']
        if not p.is_file(): issues.append(r['path']+':missing'); continue
        if p.stat().st_size!=r['bytes']: issues.append(r['path']+':size')
        if sha(p)!=r['sha256']: issues.append(r['path']+':sha256')
    listed={r['path'] for r in data['files']}
    print(json.dumps({'status':'pass' if not issues else 'fail','files':len(listed),'issues':issues}))
    return 0 if not issues else 1
if __name__=='__main__': raise SystemExit(main())
