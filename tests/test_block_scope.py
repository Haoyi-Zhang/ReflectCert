"""Benign JLS block/for scopes; fields remain outside the finite bridge."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from rrc.java_frontend import ARTIFACT_ROOT, run_extractor


class BlockScopeTests(unittest.TestCase):
    def extract(self, body, *, main=""):
        source = """final class Scope {
            static String name = "java.lang.Integer";
            static boolean gate = false;
            static java.lang.Class<?> owner = java.lang.Integer.class;
            static ClassLoader loader = null;
            static void inspect(boolean h) throws Exception {
        """ + body + "\n}\n" + main + "\n}\n"
        with tempfile.TemporaryDirectory(prefix="rrc-block-scope-") as directory:
            path = Path(directory) / "Scope.java"
            path.write_text(source, encoding="utf-8")
            # Type-check each benign fixture, not merely its parser tree.
            subprocess.run(
                [shutil.which("javac") or "javac", "--release", "17", "-encoding", "UTF-8",
                 "-d", directory, str(path)],
                cwd=ARTIFACT_ROOT, check=True, capture_output=True, text=True, timeout=60,
            )
            report = run_extractor([path])
            stdout = None
            if main:
                completed = subprocess.run(
                    [shutil.which("java") or "java", "-cp", directory, "Scope"],
                    cwd=ARTIFACT_ROOT, check=True, capture_output=True, text=True, timeout=20,
                )
                stdout = completed.stdout.strip()
        self.assertEqual(report["parse_errors"], [])
        return report["files"][0]["events"], stdout

    def assert_decisions(self, body, expected):
        events, _ = self.extract(body)
        actual = [(event["status"], event.get("class_constant") if event["status"] == "accepted"
                   else event["reason"]) for event in events]
        self.assertEqual(actual, expected)

    def test_expired_block_local_then_field_matches_jvm_boundary(self):
        events, stdout = self.extract(
            '{ String name = "java.lang.String"; }\n'
            'System.out.println(java.lang.Class.forName(name).getName());',
            main='public static void main(String[] args) throws Exception { inspect(false); }',
        )
        self.assertEqual(stdout, "java.lang.Integer")
        self.assertEqual([(e["status"], e.get("reason")) for e in events],
                         [("rejected", "unsupported_class_name_expression")])

    def test_local_shadows_field_only_inside_block(self):
        self.assert_decisions(
            '{ String name = "java.lang.String"; java.lang.Class.forName(name); }\n'
            'java.lang.Class.forName(name);',
            [("accepted", "java.lang.String"), ("rejected", "unsupported_class_name_expression")],
        )

    def test_nested_blocks_expire_at_the_declaring_block(self):
        self.assert_decisions(
            '{ String name = "java.lang.String"; { java.lang.Class.forName(name); }'
            ' java.lang.Class.forName(name); } java.lang.Class.forName(name);',
            [("accepted", "java.lang.String"), ("accepted", "java.lang.String"),
             ("rejected", "unsupported_class_name_expression")],
        )

    def test_sibling_blocks_have_separate_declarations(self):
        self.assert_decisions(
            '{ String name = "java.lang.String"; java.lang.Class.forName(name); }'
            '{ String name = "java.lang.Long"; java.lang.Class.forName(name); }'
            'java.lang.Class.forName(name);',
            [("accepted", "java.lang.String"), ("accepted", "java.lang.Long"),
             ("rejected", "unsupported_class_name_expression")],
        )

    def test_later_local_declaration_does_not_inherit_expired_local(self):
        self.assert_decisions(
            '{ String name = "java.lang.String"; }'
            'String name = "java.lang.Long"; java.lang.Class.forName(name);',
            [("accepted", "java.lang.Long")],
        )

    def test_field_before_local_declaration_is_not_the_later_local(self):
        self.assert_decisions(
            'java.lang.Class.forName(name); String name = "java.lang.String";'
            'java.lang.Class.forName(name);',
            [("rejected", "unsupported_class_name_expression"), ("accepted", "java.lang.String")],
        )

    def test_qualified_field_is_not_shadowed_by_local(self):
        self.assert_decisions(
            'String name = "java.lang.String"; java.lang.Class.forName(Scope.name);'
            'java.lang.Class.forName(name);',
            [("rejected", "unsupported_class_name_expression"), ("accepted", "java.lang.String")],
        )

    def test_value_copied_to_outer_local_survives_source_local_expiry(self):
        self.assert_decisions(
            'String result = "java.lang.Integer"; { String name = "java.lang.String"; result = name; }'
            'java.lang.Class.forName(result);',
            [("accepted", "java.lang.String")],
        )

    def test_basic_for_initializer_local_expires(self):
        self.assert_decisions(
            'for (String name = "java.lang.String"; name.isEmpty(); name = "java.lang.Long") {}'
            'java.lang.Class.forName(name);',
            [("rejected", "unsupported_class_name_expression")],
        )

    def test_enhanced_for_local_does_not_leak(self):
        self.assert_decisions(
            'for (String name : new String[] {"java.lang.String"}) {}'
            'java.lang.Class.forName(name);',
            [("rejected", "unsupported_class_name_expression")],
        )

    def test_outer_local_assignment_survives_block_exit(self):
        self.assert_decisions(
            'String name = "java.lang.String"; { name = "java.lang.Integer"; }'
            'java.lang.Class.forName(name);',
            [("accepted", "java.lang.Integer")],
        )

    def test_outer_parameter_assignment_survives_block_exit(self):
        self.assert_decisions(
            '{ h = true; } java.lang.Class.forName(h ? "java.lang.String" : "java.lang.Integer");',
            [("accepted", "java.lang.String")],
        )

    def test_outer_control_invalidation_survives_block_exit(self):
        self.assert_decisions(
            'String name = "java.lang.String"; { if (h) name = "java.lang.Integer"; }'
            'java.lang.Class.forName(name);',
            [("rejected", "unsupported_control_state_merge")],
        )

    def test_expired_boolean_local_cannot_supply_field_condition(self):
        self.assert_decisions(
            '{ boolean gate = true; }'
            'java.lang.Class.forName(gate ? "java.lang.String" : "java.lang.Integer");',
            [("rejected", "unsupported_class_name_expression")],
        )

    def test_field_assignment_after_expired_local_is_not_local(self):
        self.assert_decisions(
            '{ String name = "java.lang.String"; } name = "java.lang.Long";'
            'java.lang.Class.forName(name);',
            [("rejected", "unsupported_field_assignment")],
        )

    def test_expired_class_handle_and_type_do_not_identify_field(self):
        self.assert_decisions(
            '{ java.lang.Class<?> owner = java.lang.Class.forName("java.lang.String");'
            ' owner.getMethod("length"); } owner.getMethod("intValue");',
            [("accepted", "java.lang.String"), ("accepted", "java.lang.String")],
        )

    def test_expired_unaudited_class_type_does_not_identify_field(self):
        self.assert_decisions(
            '{ Class<?> owner = java.lang.String.class; owner.getMethod("length"); }'
            'owner.getMethod("intValue");',
            [("rejected", "unaudited_class_receiver")],
        )

    def test_expired_loader_type_does_not_identify_field(self):
        self.assert_decisions(
            '{ ClassLoader loader = null; loader.loadClass("java.lang.String"); }'
            'loader.loadClass("java.lang.Integer");',
            [("rejected", "unsupported_loader_receiver")],
        )

    def test_unsupported_reason_does_not_leak_from_expired_local(self):
        self.assert_decisions(
            '{ String name = "java.lang.String"; name += "Suffix"; }'
            'java.lang.Class.forName(name);',
            [("rejected", "unsupported_class_name_expression")],
        )


if __name__ == "__main__":
    unittest.main()
