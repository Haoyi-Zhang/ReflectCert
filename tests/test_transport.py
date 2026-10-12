"""Owned finite controls for transport and assignment-local DAG reuse."""
from __future__ import annotations

import copy
import gzip
import unittest
from unittest.mock import patch

from rrc.checker import check
from rrc.factor import produce_factorized
from rrc.factor_checker import check_factorized
from rrc.fixtures import all_fixtures
from rrc.producer import produce
from rrc.schema import Invalid
from rrc.transport import MAGIC, accept, choose, decode, encode, produce_transport


class TransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures = {name: p for name, _, p in all_fixtures()}

    def test_all_fixture_roundtrips_and_reuse(self):
        for name, program in self.fixtures.items():
            with self.subTest(case=name):
                flat, factor = produce(program), produce_factorized(program)
                expected = check(program, flat)["summary"]
                old = check_factorized(program, factor)
                reused = check_factorized(program, factor, reuse_diagram=True)
                self.assertEqual(old["summary"], reused["summary"])
                self.assertEqual(old["semantic_steps"], reused["semantic_steps"])
                self.assertLessEqual(reused["diagram_steps"], old["diagram_steps"])
                for representation, cert in (("flat", flat), ("factor", factor)):
                    for compressed in (False, True):
                        wire = encode(cert, representation, compressed=compressed)
                        self.assertEqual(accept(program, wire)["checked"]["summary"], expected)

    def test_choice_uses_actual_bytes_and_flat_tie(self):
        for name in ("F01", "F24"):
            p = self.fixtures[name]
            flat = encode(produce(p), "flat", compressed=True)
            factor = encode(produce_factorized(p), "factor", compressed=True)
            chosen = produce_transport(p)
            self.assertEqual(chosen, choose(flat, factor))
            self.assertEqual(len(chosen), min(len(flat), len(factor)))
        self.assertEqual(choose(b"flat", b"fact"), b"flat")
        self.assertEqual(choose(None, b"factor"), b"factor")
        with self.assertRaises(Invalid):
            choose(None, None)

    def test_gzip_does_not_admit_over_cap_flat_json(self):
        p = self.fixtures["F24"]
        # Factor JSON fits this reduced admission cap; flat JSON does not, even
        # though its gzip payload would fit. Admission is on decoded evidence.
        with patch("rrc.transport.MAX_CERT_BYTES", 150000):
            wire = produce_transport(p)
            self.assertEqual(decode(wire)[0], "factor")
            self.assertEqual(accept(p, wire)["checked"]["assignments"], 4096)

    def test_reuse_still_checks_each_root_and_summary(self):
        p = self.fixtures["F06"]
        factor = produce_factorized(p)
        mutations = []
        bad = copy.deepcopy(factor)
        bad["roots"]["values"][0] = bad["roots"]["feasible"]
        mutations.append(bad)
        bad = copy.deepcopy(factor)
        next(n for n in bad["diagram"]["nodes"] if n["kind"] == "terminal"
             and n["value"] is False)["value"] = 0
        mutations.append(bad)
        bad = copy.deepcopy(factor)
        bad["program"]["table"].reverse()
        mutations.append(bad)
        bad = copy.deepcopy(factor)
        bad["summary"]["may"][0].pop()
        mutations.append(bad)
        for bad in mutations:
            for reuse in (False, True):
                with self.assertRaises(Invalid):
                    check_factorized(p, bad, reuse_diagram=reuse)

    def test_transport_does_not_trust_tag_or_producer(self):
        p = self.fixtures["F06"]
        flat = produce(p)
        with self.assertRaises(Invalid):
            accept(p, encode(flat, "factor", compressed=True))
        flat["rows"][0]["values"][0] = 0
        with self.assertRaises(Invalid):
            accept(p, encode(flat, "flat", compressed=True))

    def test_frame_crc_truncation_and_trailing_data(self):
        wire = encode(produce(self.fixtures["F01"]), "flat", compressed=True)
        corrupted = bytearray(wire)
        corrupted[-8] ^= 1
        for bad in (wire[:4], b"XXXX" + wire[4:], MAGIC + b"?" + wire[5:],
                    wire[:-1], bytes(corrupted), wire + b"extra", wire + wire[5:]):
            with self.subTest(length=len(bad)), self.assertRaises(Invalid):
                decode(bad)

    def test_duplicate_nonfinite_and_depth_admission(self):
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}'):
            for tag, payload in ((b"f", raw), (b"F", gzip.compress(raw, mtime=0))):
                with self.assertRaises(Invalid):
                    decode(MAGIC + tag + payload)
        # A host may parse this depth; it is still not an admitted certificate.
        raw = b'[' * 2000 + b']' * 2000
        with self.assertRaises(Invalid):
            accept(self.fixtures["F01"], MAGIC + b"F" + gzip.compress(raw, mtime=0))
        with patch("rrc.schema.json.loads", side_effect=RecursionError), self.assertRaises(Invalid):
            decode(MAGIC + b"f" + b"{}")

    def test_compressed_and_decompressed_caps(self):
        with patch("rrc.transport.MAX_CERT_BYTES", 128):
            for tag, payload in ((b"f", b" " * 129),
                                 (b"F", gzip.compress(b" " * 129, mtime=0))):
                with self.assertRaises(Invalid):
                    decode(MAGIC + tag + payload)
            with self.assertRaises(Invalid):
                encode({"long": "a" * 129}, "flat", compressed=True)
        with patch("rrc.transport.MAX_WIRE_BYTES", 10):
            with self.assertRaises(Invalid):
                decode(MAGIC + b"f" + b" " * 6)


if __name__ == "__main__":
    unittest.main()
