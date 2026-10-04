#!/usr/bin/env python3
"""Mechanical checks for the matched journal manuscript and finite artifact.

Passing this gate does not assert current portal-rule confirmation, author approval,
external publication, or acceptance. These are reported separately and remain open.
"""
from __future__ import annotations
import argparse,ast,json,re,subprocess
from pathlib import Path
from verify_bibliography import verify


def main() -> int:
    p=argparse.ArgumentParser();p.add_argument('--artifact-root',default='.')
    p.add_argument('--project-root');a=p.parse_args()
    root=Path(a.artifact_root).resolve()
    project=Path(a.project_root).resolve() if a.project_root else (root.parent if (root.parent/'paper').exists() else None)
    checks=[]
    def check(name, condition, detail):
        checks.append({'name':name,'status':'pass' if condition else 'fail','detail':detail})
    for name in ['README.md','LICENSE','verify_inputs.py','reproduce.py','compare_results.py',
                 'journal_analysis.py','compare_journal.py','rrc/witness_checker.py','tests','results/measured','results/journal']:
        check('required:'+name,(root/name).exists(),name)
    parse_errors=[]
    for path in sorted(root.rglob('*.py')):
        if 'results' in path.relative_to(root).parts: continue
        try: ast.parse(path.read_text())
        except SyntaxError as e: parse_errors.append(str(path.relative_to(root))+':'+str(e))
    check('python-syntax',not parse_errors,parse_errors)
    forbidden={'producer','generated','fixtures','factor','dispatch','missing_witness'}
    violations=[]
    for name in ['checker','factor_checker','dispatch_checker','witness_checker']:
        path=root/'rrc'/f'{name}.py'
        for node in ast.walk(ast.parse(path.read_text())):
            mods=[]
            if isinstance(node,ast.Import): mods=[x.name for x in node.names]
            elif isinstance(node,ast.ImportFrom): mods=[node.module or '']
            for mod in mods:
                if set(mod.split('.')) & forbidden: violations.append(name+' -> '+mod)
    check('checker-import-independence',not violations,violations)
    hygiene=[]
    for path in root.rglob('*'):
        if path.name=='__pycache__' or path.suffix.lower() in {'.pyc','.pyo','.zip','.7z','.rar','.ttf','.otf','.pfb'}:
            hygiene.append(str(path.relative_to(root)))
        if path.is_file() and path.suffix.lower() in {'.py','.md','.tex','.json','.csv','.sh','.txt'}:
            text=path.read_text(errors='replace')
            if re.search(r'/(Users|home)/[^/\s]+/',text) or ''.join(('/mnt','/data/')) in text:
                hygiene.append(str(path.relative_to(root))+':private-path')
    check('package-hygiene',not hygiene,hygiene)
    try:
        kwargs={}
        if project: kwargs={'tex_path':project/'paper/main.tex','canonical_path':root/'docs/references.bib'}
        refs=verify(project/'paper/references.bib' if project else root/'docs/references.bib',
                    root/'docs/bibliography-audit.csv',root/'docs/literature.csv',**kwargs)
        check('reference-closure',refs['entries']==66 and refs['unique_dois']==60,refs)
    except Exception as e: check('reference-closure',False,str(e))
    try:
        summary=json.loads((root/'results/measured/deterministic-summary.json').read_text())
        expected={'case_count':664,'authored_fixtures':24,'generated_cases':600,
                  'manual_public_projections':11,'source_extracted_public_cases':29,
                  'assignments':32139,'flat_bytes_total':14279992,'factor_bytes_total':3329807,
                  'dispatch_bytes_total':1389323,'missing_target_witnesses':1826,
                  'witness_target_base_pairs':913,'witness_unique_within_case':1259,
                  'witness_duplicate_records':567,'public_witness_records':80,
                  'public_witness_unique_within_case':40,'factor_smaller_cases':511,'factor_larger_cases':153}
        mismatch={k:{'actual':summary.get(k),'expected':v} for k,v in expected.items() if summary.get(k)!=v}
        check('fixed-corpus-and-denominators',not mismatch,mismatch or expected)
        bundles=list((root/'results/measured/certificates').glob('*.json'))
        check('complete-bundle-inventory',len(bundles)==664,len(bundles))
    except Exception as e:check('fixed-corpus-and-denominators',False,str(e))
    try:
        j=json.loads((root/'results/journal/summary.json').read_text())
        check('journal-membership-oracle',j['target_presence_oracle']['tables']==6654 and
              j['target_presence_oracle']['checked_order_records']==35222 and
              j['target_presence_oracle']['mismatches']==0,j['target_presence_oracle'])
        check('journal-bridge-controls',j['additional_bridge_controls']['jvm_executions']==2 and
              j['additional_bridge_controls']['rejected_events']==4,j['additional_bridge_controls'])
        check('journal-sharing-accounting',j['sharing']['per_root_reduced_nodes']==47973 and
              j['sharing']['shared_nodes']==29056,j['sharing'])
        transport=j['transport']
        check('journal-transport-compression',
              transport['flat_gzip_bytes']==855047 and
              transport['factor_gzip_bytes']==588640 and
              transport['dispatch_gzip_bytes']==372385 and
              transport['gzip_smaller']==371 and
              transport['gzip_larger']==292 and
              transport['gzip_equal']==1,
              transport)
        check('journal-stage-cost-inventory',len(j['stage_costs'])==6,j['stage_costs'])
        check('journal-trust-surface-inventory',len(j['trust_surface'])==8,j['trust_surface'])
        public=[x for x in j['strata'] if x['population'].endswith('public')]
        check('public-expansions-retained',sum(x['larger'] for x in public)==40,public)
    except Exception as e:check('journal-evidence',False,str(e))
    if project:
        check('project-root-contract',{x.name for x in project.iterdir()}=={'paper','artifact','README.md'},
              sorted(x.name for x in project.iterdir()))
        paper=project/'paper';source=(paper/'main.tex').read_text()
        check('journal-format',r'\documentclass[manuscript,screen,review]{acmart}' in source and
              r'\acmJournal{TOSEM}' in source and 'Anonymous Author' not in source,'named manuscript review draft')
        authors=json.loads((paper/'AUTHOR-METADATA.json').read_text())['authors']
        found=re.findall(r'\\author\{([^}]+)\}',source)
        check('supplied-author-order',found==[r['name'] for r in authors],found)
        check('supplied-author-emails',re.findall(r'\\email\{([^}]+)\}',source)==[r['email'] for r in authors],
              [r['email'] for r in authors])
        check('honest-scope-limits','not whole-classpath completeness' in source and
              'minimum-cardinality' in source and 'manual projections' in source,
              'scope boundaries present; external-use declarations are separate')
        for fname in ['stratum-ratios.csv','sharing-stages.csv']:
            check('plot-data:'+fname,(paper/'data'/fname).read_bytes()==(root/'results/journal'/fname).read_bytes(),fname)
        if (paper/'main.pdf').exists():
            info=subprocess.check_output(['pdfinfo',str(paper/'main.pdf')],text=True)
            pages=int(re.search(r'^Pages:\s+(\d+)',info,re.M).group(1))
            check('conservative-page-budget',0<pages<=45,{'physical_pages':pages,
                 'basis':'internal conservative budget; current TOSEM limit not independently confirmed'})
            fonts=subprocess.check_output(['pdffonts',str(paper/'main.pdf')],text=True).splitlines()[2:]
            bad=[]
            for row in fonts:
                if not row.strip():continue
                m=re.search(r'\s+(yes|no)\s+(yes|no)\s+(yes|no)\s+\d+\s+\d+\s*$',row)
                if not m or m.group(1)!='yes':bad.append(row)
            check('embedded-fonts',not bad,{'font_records':len(fonts),'bad':bad})
        else:check('paper-pdf',False,'build main.pdf first')
        if (paper/'main.log').exists():
            log=(paper/'main.log').read_text(errors='replace')
            bad=[x for x in [r'Overfull \hbox',r'Overfull \vbox','undefined references'] if x in log]
            if re.search(r'Citation .* undefined',log):bad.append('undefined citation')
            check('latex-layout-and-references',not bad,bad)
    success=all(c['status']=='pass' for c in checks)
    report={'mechanical_status':'pass' if success else 'fail','overall_status':'pass' if success else 'fail',
            'submission_ready':False,
            'publication_conditions':'current portal rules, author/affiliation confirmations, correspondence and artifact deposit remain unconfirmed',
            'metadata_warnings':['institution-level cities were sourced from official public pages but still require author confirmation; corresponding author, consent, overlap declarations, and artifact URL remain unset'],
            'checks':checks}
    (root/'results/release-audit.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'mechanical_status':report['mechanical_status'],'checks':len(checks),
                      'failed':[c['name'] for c in checks if c['status']=='fail'],'submission_ready':False}))
    return 0 if success else 1
if __name__=='__main__':raise SystemExit(main())
