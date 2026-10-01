#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import argparse, ast, csv, json, re, subprocess, sys, os

def check(cond, name, detail, out):
    out.append({'name':name,'status':'pass' if cond else 'fail','detail':detail})

def bib_keys(text): return re.findall(r'@\w+\s*\{\s*([^,\s]+)\s*,',text,re.I)
def cite_keys(text):
    ans=[]
    for m in re.finditer(r'\\cite(?!style\b)\w*\s*(?:\[[^\]]*\]\s*)*\{([^}]*)\}',text): ans += [x.strip() for x in m.group(1).split(',') if x.strip()]
    return ans

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--artifact-root',default='.'); ap.add_argument('--project-root'); ap.add_argument('--strict-online',action='store_true'); a=ap.parse_args()
    art=Path(a.artifact_root).resolve(); project=Path(a.project_root).resolve() if a.project_root else (art.parent if (art.parent/'paper').exists() else None)
    out=[]
    required=['README.md','verify_inputs.py','reproduce.py','compare_results.py','tests','results/measured']
    for r in required: check((art/r).exists(),f'required:{r}',r,out)
    licenses=[p for p in art.iterdir() if p.is_file() and p.name.lower().startswith(('license','copying'))]
    check(bool(licenses),'artifact-license-present',str([p.name for p in licenses]),out)
    # Python syntax.
    bad=[]
    for p in art.rglob('*.py'):
        if any(x in p.parts for x in ['results','__pycache__']): continue
        try: ast.parse(p.read_text(encoding='utf-8'))
        except Exception as e: bad.append(f'{p.relative_to(art)}: {e}')
    check(not bad,'python-syntax','; '.join(bad) or 'all parsed',out)
    # Checker independence: any module whose stem contains checker/check must not import producer/generator/lowerer modules.
    violations=[]
    forbidden=('producer','generator','lowerer')
    for p in art.rglob('*.py'):
        if not (('checker' in p.stem.lower()) or re.match(r'check_(certificate|dispatch|witness|factor|flat)', p.stem.lower())): continue
        try: tree=ast.parse(p.read_text(encoding='utf-8'))
        except Exception: continue
        for n in ast.walk(tree):
            names=[]
            if isinstance(n,ast.Import): names=[x.name for x in n.names]
            elif isinstance(n,ast.ImportFrom): names=[n.module or '']
            for name in names:
                if any(f in name.lower() for f in forbidden): violations.append(f'{p.relative_to(art)} -> {name}')
    check(not violations,'checker-import-independence','; '.join(violations) or 'no forbidden imports',out)
    # No caches/nested archives/private absolute home paths.
    badpack=[]
    for p in art.rglob('*'):
        rel=str(p.relative_to(art))
        if p.name=='__pycache__' or p.suffix in {'.pyc','.pyo','.zip','.7z','.rar'}: badpack.append(rel)
        if p.is_file() and p.stat().st_size < 10_000_000 and p.suffix.lower() in {'.py','.md','.tex','.json','.csv','.sh','.txt'}:
            t=p.read_text(encoding='utf-8',errors='ignore')
            if re.search(r'/(Users|home)/[^/\s]+/',t) or ''.join(('/mnt','/data/')) in t: badpack.append(rel+':private-path')
    check(not badpack,'package-hygiene','; '.join(badpack) or 'clean',out)
    # Public provenance is intentionally stratified: 29 automatic source events and
    # 11 labeled manual finite projections.  The gate prevents either stratum from
    # being silently relabeled and requires the evidence fields used by each claim.
    provenance=art/'docs'/'public-provenance.csv'
    provenance_issues=[]; automatic=[]; manual=[]
    if not provenance.exists():
        provenance_issues.append('missing docs/public-provenance.csv')
    else:
        with provenance.open(newline='',encoding='utf-8') as f:
            rows=list(csv.DictReader(f))
        ids=[r.get('case','') for r in rows]
        if len(rows)!=40: provenance_issues.append(f'rows={len(rows)} expected=40')
        if len(set(ids))!=len(ids): provenance_issues.append('duplicate case identifiers')
        if sorted(ids)!=[f'P{i:03d}' for i in range(1,41)]: provenance_issues.append('case identifiers are not P001--P040')
        for r in rows:
            mode=(r.get('extraction_mode') or '').strip().lower()
            if mode=='automatic javac ast extraction':
                automatic.append(r)
                required_auto=('repository','commit','path','source_sha','operation',
                               'redistributed_local_path','source_line','source_column',
                               'class_expr_json','member_expr_json','projection_note')
                missing=[k for k in required_auto if not (r.get(k) or '').strip()]
                if missing: provenance_issues.append(f"{r.get('case')}: automatic missing {missing}")
            elif mode=='manual finite projection':
                manual.append(r)
                required_manual=('repository','commit','path','source_sha','operation','projection_note')
                missing=[k for k in required_manual if not (r.get(k) or '').strip()]
                if missing: provenance_issues.append(f"{r.get('case')}: manual missing {missing}")
                if (r.get('redistributed_local_path') or '').strip():
                    provenance_issues.append(f"{r.get('case')}: manual record unexpectedly claims redistributed source")
            else:
                provenance_issues.append(f"{r.get('case')}: unknown extraction_mode={mode!r}")
        if len(automatic)!=29 or len(manual)!=11:
            provenance_issues.append(f'automatic/manual={len(automatic)}/{len(manual)} expected=29/11')
    check(not provenance_issues,'public-provenance-strata',
          '; '.join(provenance_issues) or f'{len(automatic)} automatic; {len(manual)} manual',out)
    # Measured results and comparator inputs.
    measured=art/'results'/'measured'
    files=[p for p in measured.rglob('*') if p.is_file()] if measured.exists() else []
    check(len(files)>0,'measured-results-present',f'{len(files)} files',out)
    # Paper checks when adjacent.
    if project:
        paper=project/'paper'; tex=paper/'main.tex'; bib=paper/'references.bib'; pdf=paper/'main.pdf'; log=paper/'main.log'
        check(tex.exists() and bib.exists(),'paper-source-present','paper',out)
        if tex.exists() and bib.exists():
            tt=tex.read_text(encoding='utf-8',errors='ignore'); bb=bib.read_text(encoding='utf-8',errors='ignore')
            bk=bib_keys(bb); ck=cite_keys(tt)
            check(len(bk)>=55,'reference-count',f'{len(bk)} bibliography entries',out)
            check(not(set(ck)-set(bk)),'citation-keys-present',str(sorted(set(ck)-set(bk))),out)
            check(not(set(bk)-set(ck)),'all-bibliography-cited',str(sorted(set(bk)-set(ck))),out)
            dois=[x.lower().strip() for x in re.findall(r'\bdoi\s*=\s*[\{"]([^\}"]+)',bb,re.I)]
            dup=sorted({x for x in dois if dois.count(x)>1})
            check(not dup,'duplicate-doi',str(dup),out)
            check('anonymous' in tt.lower() and 'review' in tt.lower(),'anonymous-review-options','document class/options inspected',out)
            cheats=re.findall(r'(?:\\fontsize|\\usepackage(?:\[[^]]*\])?\{geometry\}|\\geometry\{|\\addtolength\s*\{\\(?:textwidth|textheight|oddsidemargin|evensidemargin)|\\setlength\s*\{\\(?:textwidth|textheight)|\\linespread\s*\{|\\renewcommand\s*\{\\baselinestretch)',tt,re.I)
            check(not cheats,'no-page-limit-formatting-cheats',str(cheats),out)
        if pdf.exists():
            try:
                pi=subprocess.check_output(['pdfinfo',str(pdf)],text=True); m=re.search(r'^Pages:\s+(\d+)',pi,re.M); pages=int(m.group(1)) if m else -1
            except Exception: pages=-1
            check(19<=pages<=22,'pdf-page-range',f'{pages} physical pages',out)
            try:
                pf=subprocess.check_output(['pdffonts',str(pdf)],text=True); rows=[x for x in pf.splitlines()[2:] if x.strip()]; bad=[]
                for row in rows:
                    mm=re.search(r'\s+(yes|no)\s+(yes|no)\s+(yes|no)\s+\d+\s+\d+\s*$',row,re.I)
                    if (not mm) or mm.group(1).lower()!='yes': bad.append(row)
            except Exception as e: bad=[str(e)]
            check(not bad,'pdf-fonts-embedded',f'{len(rows) if "rows" in locals() else 0} fonts',out)
        if log.exists():
            lt=log.read_text(encoding='utf-8',errors='ignore')
            issues=[]
            regex_checks=[r'undefined references',r'Citation .* undefined',r'There were undefined references']
            for pat in regex_checks:
                if re.search(pat,lt,re.I): issues.append(pat)
            for literal in [r'Overfull \hbox',r'Overfull \vbox']:
                if literal in lt: issues.append(literal)
            check(not issues,'latex-log-clean',str(issues),out)
    overall='pass' if all(x['status']=='pass' for x in out) else 'fail'
    report={'schema':'rrc-release-audit-v1','overall_status':overall,'artifact_root':'.','checks':out}
    dest=art/'results'/'release-audit.json'; dest.parent.mkdir(parents=True,exist_ok=True); dest.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'overall_status':overall,'checks':len(out),'failed':[x['name'] for x in out if x['status']=='fail']}))
    return 0 if overall=='pass' else 1
if __name__=='__main__': raise SystemExit(main())
