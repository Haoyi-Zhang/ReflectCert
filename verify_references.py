#!/usr/bin/env python3
from pathlib import Path
import argparse,re,json,urllib.request,urllib.parse,time,unicodedata

def parse_bib(text):
    starts=list(re.finditer(r'@(\w+)\s*\{\s*([^,\s]+)\s*,',text,re.I)); out=[]
    for i,m in enumerate(starts):
        block=text[m.start():(starts[i+1].start() if i+1<len(starts) else len(text))]
        def fld(n):
            q=re.search(r'\b'+re.escape(n)+r'\s*=\s*(?:\{((?:[^{}]|\{[^{}]*\})*)\}|"([^"]*)")',block,re.I|re.S)
            return re.sub(r'\s+',' ',(q.group(1) or q.group(2) or '')).strip() if q else ''
        out.append({'type':m.group(1),'key':m.group(2),'title':fld('title'),'author':fld('author'),'year':fld('year'),'venue':fld('booktitle') or fld('journal'),'doi':fld('doi').lower().strip(),'url':fld('url')})
    return out

def cites(tex):
    out=[]
    for m in re.finditer(r'\\cite\w*\s*(?:\[[^\]]*\]\s*)*\{([^}]*)\}',tex): out += [x.strip() for x in m.group(1).split(',') if x.strip()]
    return out

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
    paper=Path(a.paper_root).resolve(); entries=parse_bib((paper/'references.bib').read_text(encoding='utf-8')); ck=cites((paper/'main.tex').read_text(encoding='utf-8'))
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
        if not e['doi'] and not e['url']: local.append('no DOI or URL')
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
