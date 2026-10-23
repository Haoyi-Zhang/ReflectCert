"""Audit separately supplied resolver claims against checked finite semantics.

The certificate producer is not called here. A caller supplies the finite source, its
certificate and a complete site-indexed claim independently. Results concern
that finite source/table, never unmodeled JVM targets or analyzer soundness.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .factor_checker import check_factorized
from .missing_witness import produce_missing_target_witness
from .witness_checker import check_missing_target_witness
from .schema import (Invalid, MAX_CERT_BYTES, MAX_INPUT_BYTES, MAX_TABLE,
                     exact_keys, load_json, require, strict_equal, text, validate)

FORMAT = 'reflection-client-claim'


def audit_claim(program, certificate, claim):
    validate(program)
    exact_keys(claim, {'format', 'program', 'sites'}, 'client claim')
    require(claim['format'] == FORMAT, 'client claim format')
    require(strict_equal(claim['program'], program), 'client source binding')
    sites = claim['sites']
    require(type(sites) is list and len(sites) == len(program['sites']), 'client site coverage')
    for row in sites:
        require(type(row) is list and len(row) <= MAX_TABLE, 'client target count')
        for target in row:
            require(type(target) is list and len(target) == 4, 'client target identity')
            for field in target:
                text(field, 'client target')
        require(row == sorted(row) and len({tuple(t) for t in row}) == len(row),
                'client target canonical form')
    summary = check_factorized(program, certificate)['summary']
    rows = []
    for site, supplied in enumerate(sites):
        exact = summary['may'][site]
        exact_keys_set = {tuple(t) for t in exact}
        supplied_keys = {tuple(t) for t in supplied}
        # Keep raw claims and extras. A witness needs only the exact-domain
        # projection; its omission is also an omission from the original claim.
        projected = [t for t in supplied if tuple(t) in exact_keys_set]
        missing = [t for t in exact if tuple(t) not in supplied_keys]
        extras = [t for t in supplied if tuple(t) not in exact_keys_set]
        witnesses = []
        for target in missing:
            base = next(w['index'] for w in summary['worlds'] if target in w['targets'][site])
            evidence = produce_missing_target_witness(summary, site, target, projected, base)
            check_missing_target_witness(summary, evidence)
            witnesses.append(evidence)
        rows.append({'site':site, 'supplied_targets':supplied, 'exact_targets':exact,
                     'outside_exact_targets':extras, 'omitted_targets':missing,
                     'checked_witnesses':witnesses})
    omitted = sum(len(r['omitted_targets']) for r in rows)
    extra = sum(len(r['outside_exact_targets']) for r in rows)
    return {'status':'omissions' if omitted else 'covers_finite_targets',
            'scope':'separately supplied finite program and target table',
            'omitted_targets':omitted, 'outside_exact_targets':extra, 'sites':rows}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--certificate', type=Path, required=True)
    parser.add_argument('--claim', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        record = load_json(args.source, MAX_INPUT_BYTES)
        exact_keys(record, set(record) if type(record) is dict else set(), 'source record')
        require(set(record) in ({'label','program'}, {'label','program','expected_rows'}), 'source fields')
        certificate = load_json(args.certificate, MAX_CERT_BYTES)
        claim = load_json(args.claim, MAX_INPUT_BYTES)
        result = audit_claim(record['program'], certificate, claim)
        print(json.dumps(result, sort_keys=True, separators=(',', ':'), allow_nan=False))
        return 1 if result['omitted_targets'] else 0
    except (Invalid, OSError, ValueError) as exc:
        print(json.dumps({'status':'invalid', 'reason':str(exc)}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
