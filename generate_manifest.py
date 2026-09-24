#!/usr/bin/env python3
from pathlib import Path
import argparse,hashlib,json

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',default='.'); ap.add_argument('--output',default='release-manifest.json'); a=ap.parse_args()
    root=Path(a.root).resolve(); out=Path(a.output); out=out if out.is_absolute() else root/out
    skip={'release-manifest.json','results/release-audit.json'}
    rows=[]
    for p in sorted(root.rglob('*')):
        if not p.is_file(): continue
        rel=str(p.relative_to(root))
        if rel in skip or any(x in p.parts for x in ['__pycache__','results/reproduced','results/audit_reproduced','results/determinism_seed42']): continue
        if p.suffix in {'.pyc','.pyo'}: continue
        rows.append({'path':rel,'bytes':p.stat().st_size,'sha256':sha(p)})
    out.write_text(json.dumps({'schema':'rrc-artifact-manifest-v2','scope':'artifact-root','files':rows},indent=2)+'\n')
    print(json.dumps({'files':len(rows),'output':str(out)}))
if __name__=='__main__': main()
