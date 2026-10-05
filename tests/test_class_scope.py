from pathlib import Path
import tempfile
import unittest

from rrc.java_frontend import run_extractor


class ClassScopeTests(unittest.TestCase):
    def extract(self, source):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Scope.java"
            path.write_text(source, encoding="utf-8")
            report = run_extractor([path])
        self.assertEqual(report["parse_errors"], [])
        return report["files"][0]["events"]

    def test_local_class_field_does_not_replace_outer_local(self):
        events = self.extract('''class Scope {
            void inspect() throws Exception {
                String name = "java.lang.String";
                class Inner { String name = "java.lang.Integer"; }
                java.lang.Class.forName(name);
            }
        }''')
        self.assertEqual([(e["status"], e["class_constant"]) for e in events],
                         [("accepted", "java.lang.String")])

    def test_anonymous_class_field_does_not_replace_outer_local(self):
        events = self.extract('''class Scope {
            void inspect() throws Exception {
                String name = "java.lang.String";
                Object inner = new Object() { String name = "java.lang.Integer"; };
                java.lang.Class.forName(name);
            }
        }''')
        self.assertEqual([(e["status"], e["class_constant"]) for e in events],
                         [("accepted", "java.lang.String")])

    def test_class_initializer_is_not_a_method_local_context(self):
        events = self.extract('''class Scope {
            static { java.lang.Class.forName("java.lang.String"); }
            void inspect() throws Exception {
                java.lang.Class.forName("java.lang.Integer");
            }
        }''')
        self.assertEqual(events[0]["status"], "rejected")
        self.assertEqual(events[0]["reason"], "unsupported_class_context")
        self.assertEqual(events[1]["status"], "accepted")
        self.assertEqual(events[1]["class_constant"], "java.lang.Integer")


if __name__ == "__main__":
    unittest.main()
