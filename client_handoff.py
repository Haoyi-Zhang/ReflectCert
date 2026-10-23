"""Replay finite-claim handoff on actual owned JVM observations, not seeded deletion."""
from pathlib import Path
import argparse
import json

from rrc.client_audit import FORMAT, audit_claim
from rrc.factor import produce_factorized
from rrc.factor_checker import check_factorized
from rrc.java_frontend import (FRONTEND_ROOT, compile_event, run_extractor, runtime_probe_record)
from rrc.schema import require, strict_equal


def replay():
    report = run_extractor([FRONTEND_ROOT/'fixtures/RuntimeFinite.java'])
    event = report['files'][0]['events'][1]
    program, _ = compile_event(event)
    require(program['external'] == ['h','k'], 'pilot coordinate identity')
    certificate = produce_factorized(program)
    checked = check_factorized(program, certificate)['summary']
    runtime = runtime_probe_record()
    audits = []
    supplied = set()
    for prefix, row in enumerate(runtime['rows'], 1):
        # The JVM supplies class/member/signature; the loader is the owned pilot's
        # separately audited application-loader label, not inferred from a name.
        require(row['parameter'] == 'java.lang.String', 'pilot signature')
        supplied.add((event['loader'],row['class'],row['member'],event['signature']))
        claim = {'format':FORMAT,'program':program,'sites':[[list(t) for t in sorted(supplied)]]}
        audited = audit_claim(program,certificate,claim)
        audits.append({'sampled_worlds':prefix,'claim':claim,'audit':audited})
    expected = [2,2,1,0]
    require([r['audit']['omitted_targets'] for r in audits] == expected, 'pilot omissions')
    require(all(r['audit']['outside_exact_targets'] == 0 for r in audits), 'pilot extra targets')
    return {'population':'one owned two-coordinate Java pilot; not a public application or third-party analyzer',
            'worlds':len(runtime['rows']), 'identity_checks':runtime['identity_checks'],
            'exact_targets':len(checked['may'][0]), 'runtime':runtime, 'prefix_audits':audits}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--compare',type=Path)
    args = parser.parse_args()
    require(not args.output.exists(), 'choose a fresh output')
    result = replay()
    if args.compare:
        require(strict_equal(json.loads(args.compare.read_text(encoding='utf-8')),result), 'handoff replay differs')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({'worlds':result['worlds'],'exact_targets':result['exact_targets'],
                      'prefix_omissions':[r['audit']['omitted_targets'] for r in result['prefix_audits']]}))


if __name__ == '__main__':
    main()
