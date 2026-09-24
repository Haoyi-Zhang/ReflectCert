from __future__ import annotations
import copy
import tempfile
import unittest
from pathlib import Path
from rrc.schema import Invalid, load_json, validate
from rrc.producer import produce, observation_certificate
from rrc.checker import check, check_observation
from rrc.fixtures import all_fixtures, Builder
from rrc.baselines import string_sets, dispatch_table, invoke_all
from rrc.factor import produce_factorized, serialized_bytes
from rrc.factor_checker import check_factorized
from rrc.dispatch import produce_direct_dispatch, execute_direct_dispatch
from rrc.dispatch_checker import check_direct_dispatch
from rrc.missing_witness import produce_missing_target_witness, check_missing_target_witness

FIXTURES = {name: p for name, _, p in all_fixtures()}

class CertificateTests(unittest.TestCase):
    def setUp(self):
        self.p = copy.deepcopy(FIXTURES["F06"])
        self.c = produce(self.p)
    def test_all_but_largest_fixture(self):
        for name, p in FIXTURES.items():
            if name == "F24": continue  # Largest source checked in measured pilot.
            with self.subTest(name=name):
                c = produce(p); checked = check(p, c)
                self.assertEqual(checked["summary"], c["summary"])
                for world in checked["summary"]["worlds"]:
                    for s in range(len(p["sites"])):
                        self.assertTrue(check_observation(checked, observation_certificate(c, s, world["index"])))
    def test_assignment_omission(self):
        self.c["rows"].pop()
        with self.assertRaisesRegex(Invalid, "coverage"): check(self.p, self.c)
    def test_assignment_duplication(self):
        self.c["rows"][-1] = copy.deepcopy(self.c["rows"][0])
        with self.assertRaises(Invalid): check(self.p, self.c)
    def test_wrong_node(self):
        self.c["rows"][0]["values"][0] = True
        with self.assertRaisesRegex(Invalid, "derivation"): check(self.p, self.c)
    def test_wrong_target(self):
        self.c["rows"][0]["outcomes"][0]["key"][1] = "Z"
        with self.assertRaises(Invalid): check(self.p, self.c)
    def test_wrong_aggregate(self):
        self.c["summary"]["may"][0].pop()
        with self.assertRaisesRegex(Invalid, "aggregation"): check(self.p, self.c)
    def test_program_binding(self):
        self.c["program"]["table"][0][0] = "OTHER"
        with self.assertRaisesRegex(Invalid, "binding"): check(self.p, self.c)
    def test_feasibility_tamper(self):
        self.c["rows"][1]["feasible"] = True
        with self.assertRaises(Invalid): check(self.p, self.c)
    def test_boolean_integer_confusion(self):
        self.c["rows"][0]["values"][0] = 0
        with self.assertRaises(Invalid): check(self.p, self.c)
    def test_boolean_row_index(self):
        self.c["rows"][0]["index"] = False
        with self.assertRaises(Invalid): check(self.p, self.c)
    def test_observation_insufficient(self):
        checked = check(self.p,self.c)
        e = observation_certificate(self.c,0,0)
        e["selected"]=[]; e["necessity"]=[]
        with self.assertRaises(Invalid): check_observation(checked,e)
    def test_observation_redundant(self):
        checked = check(self.p,self.c)
        e = {"base":0,"site":0,"selected":[0,1],"necessity":[{"removed":0,"world":3},{"removed":1,"world":3}]}
        with self.assertRaises(Invalid): check_observation(checked,e)
    def test_observation_witness_omission(self):
        checked = check(self.p,self.c); e=observation_certificate(self.c,0,0); e["necessity"]=[]
        with self.assertRaises(Invalid): check_observation(checked,e)
    def test_no_least_slice(self):
        e1=observation_certificate(self.c,0,0); e2=observation_certificate(self.c,0,0,True)
        self.assertEqual({tuple(e1["selected"]),tuple(e2["selected"])},{(0,),(1,)})
    def test_trace_not_target_set(self):
        p=FIXTURES["F08"]; c=produce(p); checked=check(p,c)
        self.assertEqual(checked["summary"]["worlds"][0]["targets"], checked["summary"]["worlds"][1]["targets"])
        self.assertNotEqual(c["rows"][0]["outcomes"],c["rows"][2]["outcomes"])
        self.assertEqual(observation_certificate(c,0,0)["selected"],[])
    def test_nonrelational_overapproximation(self):
        p=FIXTURES["F04"]; c=produce(p)
        self.assertEqual(len(c["summary"]["may"][0]),2)
        self.assertEqual(len(string_sets(p)[0]),4)
    def test_loader_identity(self):
        p=FIXTURES["F10"]; c=produce(p); check(p,c)
        self.assertEqual(len(c["summary"]["may"][0]),2)
        self.assertEqual(len({tuple(t[1:]) for t in c["summary"]["may"][0]}),1)
    def test_dispatch_and_bad_rewrite(self):
        p=FIXTURES["F03"]; c=produce(p); check(p,c); d=dispatch_table(c)
        self.assertTrue(all(d[r["index"]] == r["outcomes"] for r in c["rows"]))
        self.assertNotEqual(invoke_all(c["summary"]["may"][0]), c["rows"][0]["outcomes"])
    def test_empty_worlds_not_vacuous_robust_claim(self):
        c=produce(FIXTURES["F15"]); s=check(FIXTURES["F15"],c)["summary"]
        self.assertEqual(s["worlds"],[]); self.assertEqual(s["robust"],[None])
    def test_unsupported_primitive(self):
        self.p["nodes"][0] = {"op":"network_name"}
        with self.assertRaisesRegex(Invalid,"unsupported"): validate(self.p)
    def test_forward_reference(self):
        self.p["nodes"][0] = {"op":"alias","args":[0]}
        with self.assertRaises(Invalid): validate(self.p)
    def test_choice_constrained_feasibility(self):
        p=copy.deepcopy(FIXTURES["F08"]); p["feasible"]=1
        with self.assertRaisesRegex(Invalid,"internal choices"): validate(p)
    def test_width_limit(self):
        b=Builder(); c=b.node("cat",b.lit("a"*24),b.lit("b"*25)); b.probe(c); b.table()
        with self.assertRaises(Invalid): b.finish()
    def test_invalid_sort(self):
        p=copy.deepcopy(FIXTURES["F01"]); p["sites"][0]["class"]=0
        with self.assertRaises(Invalid): validate(p)
    def test_constant_join_retains_equal_branches(self):
        p = FIXTURES["F16"]
        self.assertEqual(string_sets(p, True), produce(p)["summary"]["may"])
    def test_cli_checker_binds_source_first(self):
        from rrc.__main__ import BUNDLE_FORMAT, verify_bundle
        factor = produce_factorized(self.p)
        summary = check_factorized(self.p, factor)["summary"]
        target = summary["may"][0][0]
        base = next(world["index"] for world in summary["worlds"] if target in world["targets"][0])
        witness = produce_missing_target_witness(summary, 0, target, summary["may"][0][1:], base)
        direct = produce_direct_dispatch(self.p, factor)
        bundle = {"format": BUNDLE_FORMAT, "factorized_certificate": factor,
                  "direct_dispatch": direct, "missing_target_witnesses": [witness]}
        self.assertEqual(verify_bundle(self.p, bundle)["summary"], summary)
        bundle["factorized_certificate"]["roots"]["values"].pop()
        with self.assertRaises(Invalid):
            verify_bundle(self.p, bundle)

    def test_bundle_has_no_silent_unknown_fields(self):
        from rrc.__main__ import BUNDLE_FORMAT, verify_bundle
        factor = produce_factorized(self.p)
        with self.assertRaises(Invalid):
            verify_bundle(self.p, {"format": BUNDLE_FORMAT, "factorized_certificate": factor,
                                   "direct_dispatch": produce_direct_dispatch(self.p, factor),
                                   "missing_target_witnesses": [], "trusted": True})
    def test_valid_source_can_exceed_serialized_certificate_cap(self):
        from rrc.schema import MAX_CERT_BYTES
        word = "A" * 48
        p = {"external": [f"h{i}" for i in range(8)], "choices": [f"r{i}" for i in range(4)],
             "nodes": [{"op": "lit", "value": True}] + [{"op": "lit", "value": word} for _ in range(63)],
             "feasible": 0, "table": [[word] * 4],
             "sites": [{"guard": 0, "loader": 1, "class": 1, "method": 1, "signature": 1} for _ in range(8)]}
        validate(p)
        # Every row serializes 63 long node values and 8 four-field target identities.
        # Count only those quoted strings, omitting all other JSON structure: a lower bound.
        lower_bound = (1 << 12) * (63 + 8 * 4) * (48 + 2)
        self.assertEqual(lower_bound, 19456000)
        self.assertGreater(lower_bound, MAX_CERT_BYTES)
    def test_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"input.json"; path.write_text('{"a":1,"a":2}')
            with self.assertRaises(Invalid): load_json(path,128)
    def test_byte_bound(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"input.json"; path.write_bytes(b" "*129)
            with self.assertRaises(Invalid): load_json(path,128)

    def test_factorized_certificate_matches_flat_semantics(self):
        for name, p in FIXTURES.items():
            with self.subTest(name=name):
                factor = produce_factorized(p)
                checked = check_factorized(p, factor)
                self.assertEqual(checked["summary"], produce(p)["summary"])

    def test_factorized_source_binding_and_terminal_tamper(self):
        factor = produce_factorized(self.p)
        bad = copy.deepcopy(factor)
        bad["program"]["table"][0][0] = "OTHER"
        with self.assertRaisesRegex(Invalid, "binding"):
            check_factorized(self.p, bad)
        bad = copy.deepcopy(factor)
        terminal = next(node for node in bad["diagram"]["nodes"] if node["kind"] == "terminal" and node["value"] is False)
        terminal["value"] = True
        with self.assertRaises(Invalid):
            check_factorized(self.p, bad)

    def test_factorized_order_and_reduction_checks(self):
        factor = produce_factorized(self.p)
        bad = copy.deepcopy(factor)
        branch = next(node for node in bad["diagram"]["nodes"] if node["kind"] == "branch")
        branch["high"] = branch["low"]
        with self.assertRaisesRegex(Invalid, "unreduced"):
            check_factorized(self.p, bad)

    def test_factorized_admits_flat_byte_counterexample(self):
        from rrc.schema import MAX_CERT_BYTES
        word = "A" * 48
        p = {"external": [f"h{i}" for i in range(8)], "choices": [f"r{i}" for i in range(4)],
             "nodes": [{"op": "lit", "value": True}] + [{"op": "lit", "value": word} for _ in range(63)],
             "feasible": 0, "table": [[word] * 4],
             "sites": [{"guard": 0, "loader": 1, "class": 1, "method": 1, "signature": 1} for _ in range(8)]}
        validate(p)
        factor = produce_factorized(p)
        self.assertLess(serialized_bytes(factor), MAX_CERT_BYTES)
        self.assertEqual(check_factorized(p, factor)["assignments"], 1 << 12)

    def test_direct_dispatch_matches_source_all_fixtures(self):
        for name, program in FIXTURES.items():
            with self.subTest(name=name):
                certificate = produce_factorized(program)
                dispatch = produce_direct_dispatch(program, certificate)
                replay = check_direct_dispatch(program, dispatch)
                self.assertEqual(replay["assignments"], 1 << (len(program["external"]) + len(program["choices"])))
                self.assertEqual(replay["trace_events"], replay["assignments"] * len(program["sites"]))

    def test_direct_dispatch_rejects_source_and_target_tamper(self):
        certificate = produce_factorized(self.p)
        dispatch = produce_direct_dispatch(self.p, certificate)
        bad = copy.deepcopy(dispatch)
        bad["program"]["table"][0][0] = "OTHER"
        with self.assertRaisesRegex(Invalid, "source binding"):
            check_direct_dispatch(self.p, bad)
        bad = copy.deepcopy(dispatch)
        terminal = next(node for node in bad["diagram"]["nodes"]
                        if node["kind"] == "terminal" and node["action"]["kind"] == "invoke")
        terminal["action"] = {"kind": "lookup_error", "key": ["Z", "Z", "Z", "Z"]}
        with self.assertRaisesRegex(Invalid, "trace mismatch"):
            check_direct_dispatch(self.p, bad)

    def test_direct_dispatch_rejects_unreduced_and_unreachable_nodes(self):
        dispatch = produce_direct_dispatch(self.p, produce_factorized(self.p))
        bad = copy.deepcopy(dispatch)
        branch = next(node for node in bad["diagram"]["nodes"] if node["kind"] == "branch")
        branch["high"] = branch["low"]
        with self.assertRaisesRegex(Invalid, "unreduced"):
            check_direct_dispatch(self.p, bad)
        bad = copy.deepcopy(dispatch)
        bad["diagram"]["nodes"].append({"kind": "terminal", "action": {"kind": "skipped"}})
        with self.assertRaises(Invalid):
            check_direct_dispatch(self.p, bad)

    def test_direct_dispatch_executes_only_selected_target(self):
        program = FIXTURES["F03"]
        dispatch = produce_direct_dispatch(program, produce_factorized(program))
        self.assertTrue(check_direct_dispatch(program, dispatch))
        calls = []
        callees = [lambda index=index: calls.append(index) or f"result-{index}"
                   for index in range(len(program["table"]))]
        width = len(program["external"]) + len(program["choices"])
        for number in range(1 << width):
            bits = [bool(number & (1 << (width - position - 1))) for position in range(width)]
            before = len(calls)
            trace = execute_direct_dispatch(dispatch, bits, callees)
            invokes = [event for event in trace if event["kind"] == "invoke"]
            self.assertEqual(len(calls) - before, len(invokes))
            self.assertEqual([event["target"] for event in invokes], calls[before:])

    def test_direct_dispatch_preserves_noninvocation_outcomes(self):
        for name in ("F07", "F11", "F15"):
            with self.subTest(name=name):
                program = FIXTURES[name]
                dispatch = produce_direct_dispatch(program, produce_factorized(program))
                replay = check_direct_dispatch(program, dispatch)
                self.assertEqual(replay["trace_events"], replay["invocations"] + replay["lookup_errors"] +
                                 replay["skipped"] + replay["infeasible"])

    def test_missing_target_retention_witness(self):
        p = FIXTURES["F06"]
        summary = check(p, produce(p))["summary"]
        target = summary["may"][0][0]
        base = next(world["index"] for world in summary["worlds"] if target in world["targets"][0])
        evidence = produce_missing_target_witness(summary, 0, target, summary["may"][0][1:], base)
        self.assertTrue(check_missing_target_witness(summary, evidence))
        bad = copy.deepcopy(evidence)
        bad["necessity"] = []
        with self.assertRaises(Invalid):
            check_missing_target_witness(summary, bad)

    def test_generated_specification_oracle_sample(self):
        from rrc.generated import all_generated
        for name, p, expected in all_generated()[::73]:
            with self.subTest(name=name):
                rows = produce(p)["rows"]
                actual = [{"feasible": row["feasible"], "outcomes": row["outcomes"]} for row in rows]
                self.assertEqual(actual, expected)

    def test_generated_witnesses_include_conjunctions_and_alternatives(self):
        from rrc.generated import all_generated
        from rrc.missing_witness import produce_missing_target_witness
        generated = {name: p for name, p, _ in all_generated()}

        conjunction_summary = check_factorized(
            generated["G001"], produce_factorized(generated["G001"]))["summary"]
        target = conjunction_summary["may"][0][0]
        base = next(world["index"] for world in conjunction_summary["worlds"]
                    if target in world["targets"][0])
        conjunction = produce_missing_target_witness(
            conjunction_summary, 0, target, conjunction_summary["may"][0][1:], base)
        self.assertEqual(len(conjunction["selected"]), 4)

        alternative_summary = check_factorized(
            generated["G002"], produce_factorized(generated["G002"]))["summary"]
        guarded = alternative_summary["may"][0][0]
        all_true = max(world["index"] for world in alternative_summary["worlds"]
                       if guarded in world["targets"][0])
        forward = produce_missing_target_witness(alternative_summary, 0, guarded, [], all_true)
        reverse = produce_missing_target_witness(alternative_summary, 0, guarded, [], all_true, reverse=True)
        self.assertEqual({tuple(forward["selected"]), tuple(reverse["selected"])}, {(0, 1), (2, 3)})

if __name__ == "__main__": unittest.main()
