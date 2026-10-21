"""Assertion-enabled and assertion-disabled executions must share a safe bridge."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from rrc.java_frontend import run_extractor


class AssertionScopeTests(unittest.TestCase):
    def extract(self, body, *, execute=False):
        source='public final class AssertionScope { public static void main(String[] args) throws Exception {'+body+'}}'
        with tempfile.TemporaryDirectory(prefix='rrc-assert-scope-') as folder:
            path=Path(folder)/'AssertionScope.java'
            path.write_text(source,encoding='utf-8')
            subprocess.run([shutil.which('javac') or 'javac','--release','17','-encoding','UTF-8',
                            '-d',folder,str(path)],check=True,capture_output=True,timeout=60)
            report=run_extractor([path])
            runtime={}
            if execute:
                for mode in ('-da','-ea'):
                    result=subprocess.run([shutil.which('java') or 'java',mode,'-cp',folder,'AssertionScope'],
                                          check=True,capture_output=True,text=True,timeout=20)
                    runtime[mode]=result.stdout.strip()
        self.assertEqual(report['parse_errors'],[])
        return report['files'][0]['events'],runtime

    def test_condition_assignment_does_not_escape_assertion_mode(self):
        events,runtime=self.extract(
            'boolean selected=false; assert selected=true;'
            'System.out.println(java.lang.Class.forName(selected ? "java.lang.String" : "java.lang.Integer").getName());',
            execute=True)
        self.assertEqual(runtime,{'-da':'java.lang.Integer','-ea':'java.lang.String'})
        self.assertEqual([(e['status'],e.get('reason')) for e in events],
                         [('rejected','unsupported_assert_state_merge')])

    def test_string_assignment_does_not_escape_assertion_mode(self):
        events,runtime=self.extract(
            'String name="java.lang.Integer"; assert (name="java.lang.String").length()>0;'
            'System.out.println(java.lang.Class.forName(name).getName());',execute=True)
        self.assertEqual(runtime,{'-da':'java.lang.Integer','-ea':'java.lang.String'})
        self.assertEqual([(e['status'],e.get('reason')) for e in events],
                         [('rejected','unsupported_assert_state_merge')])

    def test_detail_assignment_invalidates_dependent_binding(self):
        events,_=self.extract('String name="java.lang.Integer"; assert false : (name="java.lang.String");'
                              'java.lang.Class.forName(name);')
        self.assertEqual([(e['status'],e.get('reason')) for e in events],
                         [('rejected','unsupported_assert_state_merge')])

    def test_queries_in_assert_condition_and_detail_are_controlled(self):
        for body in ('assert java.lang.Class.forName("java.lang.String") != null;',
                     'assert false : java.lang.Class.forName("java.lang.String");'):
            with self.subTest(body=body):
                events,_=self.extract(body)
                self.assertEqual([(e['status'],e.get('reason')) for e in events],
                                 [('rejected','unsupported_control_context')])

    def test_read_only_assertion_preserves_unmodified_binding(self):
        events,_=self.extract('boolean selected=false; assert !selected;'
                              'java.lang.Class.forName(selected ? "java.lang.String" : "java.lang.Integer");')
        self.assertEqual([(e['status'],e.get('class_constant')) for e in events],
                         [('accepted','java.lang.Integer')])

    def test_later_unconditional_assignment_restores_known_binding(self):
        events,_=self.extract('boolean selected=false; assert selected=true; selected=false;'
                              'java.lang.Class.forName(selected ? "java.lang.String" : "java.lang.Integer");')
        self.assertEqual([(e['status'],e.get('class_constant')) for e in events],
                         [('accepted','java.lang.Integer')])


if __name__=='__main__':unittest.main()
