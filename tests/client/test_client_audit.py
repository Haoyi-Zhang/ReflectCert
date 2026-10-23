"""Owned finite claim-import and CLI regressions; no third-party execution."""
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest

from rrc.client_audit import FORMAT, audit_claim, main
from rrc.factor import produce_factorized
from rrc.schema import Invalid


class ClientAuditTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[2]
        self.record = json.loads((root/'inputs/F01.json').read_text())
        self.p = self.record['program']
        self.cert = produce_factorized(self.p)
        self.target = ['L','A','f','()']
        self.claim = {'format':FORMAT, 'program':copy.deepcopy(self.p), 'sites':[[self.target]]}

    def test_exact_and_extra_claims(self):
        self.assertEqual(audit_claim(self.p,self.cert,self.claim)['omitted_targets'],0)
        self.claim['sites'][0].append(['L','B','f','()'])
        result = audit_claim(self.p,self.cert,self.claim)
        self.assertEqual((result['omitted_targets'],result['outside_exact_targets']),(0,1))

    def test_missing_with_extra_keeps_original_and_witness(self):
        self.claim['sites'] = [[['L','B','f','()']]]
        result = audit_claim(self.p,self.cert,self.claim)
        self.assertEqual((result['omitted_targets'],result['outside_exact_targets']),(1,1))
        row = result['sites'][0]
        self.assertEqual(row['supplied_targets'],self.claim['sites'][0])
        self.assertEqual(row['checked_witnesses'][0]['claimed_targets'],[])
        self.assertEqual(row['checked_witnesses'][0]['target'],self.target)

    def test_site_coverage_and_duplicates(self):
        for sites in ([], [[],[]], [[self.target,self.target]]):
            with self.subTest(sites=sites), self.assertRaises(Invalid):
                audit_claim(self.p,self.cert,dict(self.claim, sites=sites))

    def test_malformed_identity_fields(self):
        for target in ([True,'A','f','()'], ['L','A','f'], ['L','é','f','()'], ['L','A'*49,'f','()']):
            with self.subTest(target=target), self.assertRaises(Invalid):
                audit_claim(self.p,self.cert,dict(self.claim, sites=[[target]]))

    def test_source_binding(self):
        self.claim['program']['nodes'][0]['value'] = 1
        with self.assertRaisesRegex(Invalid,'binding'):
            audit_claim(self.p,self.cert,self.claim)

    def test_certificate_semantics_not_trusted(self):
        self.cert['program']['nodes'][0]['value'] = False
        with self.assertRaises(Invalid):
            audit_claim(self.p,self.cert,self.claim)

    def test_no_mutation(self):
        before = copy.deepcopy((self.p,self.cert,self.claim))
        audit_claim(self.p,self.cert,self.claim)
        self.assertEqual(before,(self.p,self.cert,self.claim))

    def test_cli_distinguishes_missing_invalid_and_cover(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name,value in [('source',self.record),('certificate',self.cert),('claim',self.claim)]:
                (root/(name+'.json')).write_text(json.dumps(value))
            argv = [value for name in ['source','certificate','claim'] for value in ['--'+name,str(root/(name+'.json'))]]
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(argv),0)
                self.claim['sites'] = [[]]
                (root/'claim.json').write_text(json.dumps(self.claim))
                self.assertEqual(main(argv),1)
                self.claim['program'] = {}
                (root/'claim.json').write_text(json.dumps(self.claim))
                self.assertEqual(main(argv),2)


if __name__ == '__main__':
    unittest.main()
