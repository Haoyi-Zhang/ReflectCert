#!/usr/bin/env python3
from pathlib import Path
import argparse,re,json,urllib.request,urllib.parse,time,unicodedata
from verify_bibliography import parse_bib as parse_bib_file, citation_keys

def parse_bib(path: Path):
    parsed = parse_bib_file(path)
    out=[]
    for key, fields in parsed.items():
        out.append({
            'type': fields.get('entry_type',''),
            'key': key,
            'title': fields.get('title',''),
            'author': fields.get('author',''),
            'year': fields.get('year',''),
            'venue': fields.get('booktitle') or fields.get('journal',''),
            'doi': fields.get('doi','').lower().strip(),
            'url': fields.get('url','').strip(),
            'pages': fields.get('pages','').strip(),
        })
    return out

def cites(tex_path: Path):
    return sorted(citation_keys(tex_path))

def tokens(s):
    s=unicodedata.normalize('NFKD',re.sub(r'[{}\\$]',' ',s.lower()))
    return {x for x in re.findall(r'[a-z0-9]+',s) if len(x)>1 and x not in {'the','a','an','of','for','and','in','on','to','with'}}

def sim(a,b):
    x,y=tokens(a),tokens(b); return len(x&y)/max(1,len(x|y))

def get_json(url,timeout=12):
    req=urllib.request.Request(url,headers={'User-Agent':'RRC-bibliography-audit/1.0 (contact: artifact@example.invalid)','Accept':'application/json'})
    with urllib.request.urlopen(req,timeout=timeout) as r: return json.load(r)

def head_ok(url,timeout=12):
    req=urllib.request.Request(url,headers={'User-Agent':'RRC-bibliography-audit/1.0'},method='HEAD')
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r: return int(r.status),r.geturl()
    except Exception:
        req=urllib.request.Request(url,headers={'User-Agent':'RRC-bibliography-audit/1.0'})
        with urllib.request.urlopen(req,timeout=timeout) as r: return int(r.status),r.geturl()

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--paper-root',default='../paper'); ap.add_argument('--output',default='results/reference-audit.json'); ap.add_argument('--online',action='store_true'); ap.add_argument('--strict-online',action='store_true'); a=ap.parse_args()
    paper=Path(a.paper_root).resolve(); entries=parse_bib(paper/'references.bib'); ck=cites(paper/'main.tex')
    keys=[e['key'] for e in entries]; dois=[e['doi'] for e in entries if e['doi']]
    issues=[]
    if len(entries)<55: issues.append(f'only {len(entries)} entries')
    if len(keys)!=len(set(keys)): issues.append('duplicate keys')
    dups=sorted({d for d in dois if dois.count(d)>1})
    if dups: issues.append('duplicate DOI: '+','.join(dups))
    missing=sorted(set(ck)-set(keys)); uncited=sorted(set(keys)-set(ck))
    if missing: issues.append('missing cited keys: '+','.join(missing))
    if uncited: issues.append('uncited bibliography entries: '+','.join(uncited))
    records=[]
    for e in entries:
        r=dict(e); r['structural_status']='pass'; local=[]
        
        if not e['title'] or not e['author'] or not e['year']: local.append('missing core field')
        if e['type'].lower() in {'article','inproceedings','conference','incollection'} and not e['venue']: local.append('missing venue')
        if e['year'] and not re.fullmatch(r'(19|20)\d{2}',e['year']): local.append('implausible year')
        r['identifier_status']='doi' if e['doi'] else ('url' if e['url'] else 'bibliographic-record')
        r['structural_issues']=local
        if local: r['structural_status']='fail'; issues += [e['key']+': '+x for x in local]
        if a.online or a.strict_online:
            if e['doi']:
                try:
                    msg=get_json('https://api.crossref.org/works/'+urllib.parse.quote(e['doi'],safe=''))['message']
                    rt=(msg.get('title') or [''])[0]; score=sim(e['title'],rt)
                    r.update({'online_status':'resolved','resolved_title':rt,'title_similarity':round(score,3),'resolved_publisher':msg.get('publisher',''),'resolved_type':msg.get('type','')})
                    if score<0.18: issues.append(e['key']+f': low Crossref title similarity {score:.3f}')
                except Exception as ex:
                    r.update({'online_status':'unavailable','online_error':type(ex).__name__+': '+str(ex)[:200]})
                    if a.strict_online: issues.append(e['key']+': DOI unresolved')
            elif e['url']:
                try:
                    code,final=head_ok(e['url']); r.update({'online_status':'resolved-url','http_status':code,'final_url':final})
                    if code>=400: issues.append(e['key']+f': URL HTTP {code}')
                except Exception as ex:
                    r.update({'online_status':'unavailable','online_error':type(ex).__name__+': '+str(ex)[:200]})
                    if a.strict_online: issues.append(e['key']+': URL unresolved')
        else: r['online_status']='not-run'
        records.append(r)
    report={'schema':'rrc-reference-audit-v2','generated_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'entries':len(entries),'distinct_cited_keys':len(set(ck)),'doi_entries':len(dois),'no_doi_entries':len(entries)-len(dois),'issues':issues,'status':'pass' if not issues else 'fail','records':records}
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'entries':len(entries),'doi':len(dois),'issues':len(issues)}))
    return 0 if not issues else 1
if __name__=='__main__': raise SystemExit(main())
