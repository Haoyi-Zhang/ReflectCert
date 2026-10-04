"""Small local JVM controls for expression-state and qualified-name boundaries."""
from __future__ import annotations
from pathlib import Path
import subprocess
import tempfile
from typing import Any
from .java_frontend import ARTIFACT_ROOT, run_extractor


def journal_bridge_record() -> dict[str, Any]:
    root = ARTIFACT_ROOT / "frontend" / "journal_controls"
    sources = sorted(root.glob("*.java"))
    if len(sources) != 2:
        raise AssertionError("expected two journal bridge-control files")
    expected = {
        "JournalBridgeControls": [
            "conditional,false,java.lang.Integer",
            "short-circuit,false,java.lang.Integer",
            "exception,false,java.lang.String",
            "conditional,true,java.lang.String",
            "short-circuit,true,java.lang.String",
            "exception,true,java.lang.Integer"],
        "QualifiedApiShadow": ["qualified-shadow,java.lang.String"],
    }
    runtime = []
    with tempfile.TemporaryDirectory(prefix="rrc-journal-bridge-") as temp:
        subprocess.run(["javac", "--release", "17", "-encoding", "UTF-8", "-d", temp,
                        *map(str, sources)], check=True, capture_output=True, text=True, timeout=60)
        for name, gold in expected.items():
            completed = subprocess.run(["java", "-cp", temp, name], check=True,
                                       capture_output=True, text=True, timeout=30)
            rows = completed.stdout.splitlines()
            if rows != gold:
                raise AssertionError(f"runtime mismatch for {name}: {rows!r}")
            runtime.append({"program": name, "stdout": rows, "expected_stdout": gold, "matched": True})
    report = run_extractor(sources)
    reasons = {
        "JournalBridgeControls.java": ["unsupported_expression_state_merge",
            "unsupported_expression_state_merge", "unsupported_exception_state_merge"],
        "QualifiedApiShadow.java": ["shadowed_qualified_class_api_receiver"],
    }
    rejection_rows = []
    for file_record in report["files"]:
        name = Path(file_record["path"]).name
        events = file_record["events"]
        if [e.get("reason") for e in events] != reasons[name] or any(e["status"] != "rejected" for e in events):
            raise AssertionError(f"expected fail-closed decisions for {name}")
        rejection_rows.append({"source": f"frontend/journal_controls/{name}",
                               "reasons": reasons[name], "matched": True})
    return {"source_files": len(sources), "jvm_executions": len(runtime),
            "observed_output_rows": sum(len(r["stdout"]) for r in runtime),
            "rejected_events": sum(len(r["reasons"]) for r in rejection_rows),
            "runtime": runtime, "rejections": rejection_rows}
