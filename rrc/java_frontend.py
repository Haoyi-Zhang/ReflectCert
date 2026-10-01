"""Restricted javac-AST bridge into the finite reflection certificate language.

The bridge is intentionally syntactic and fail-closed.  It accepts only source
expressions represented by ``frontend/JavaReflectionExtractor.java`` and checks
all redistributed public sources against a pinned human-audited gold inventory
before constructing finite inputs.  The Java extractor is a producer-side
component; acceptance of a target certificate still depends on the independent
finite checker.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import hashlib
import itertools
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any, Iterable, Mapping

from .schema import MAX_EXTERNAL, MAX_STRING, Invalid, strict_equal, validate

ARTIFACT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_ROOT = ARTIFACT_ROOT / "frontend"
GOLD_PATH = FRONTEND_ROOT / "public-gold.json"
EXTRACTOR_SOURCE = FRONTEND_ROOT / "JavaReflectionExtractor.java"
SOURCE_ROOT = ARTIFACT_ROOT / "third_party" / "droidra-reflection-sources"
FRONTEND_FORMAT = "rrc-java-front-v1"
GOLD_FORMAT = "rrc-java-front-gold-v1"


class FrontendError(Invalid):
    """The source is malformed, unsupported, or inconsistent with pinned evidence."""


@dataclass(frozen=True)
class ExtractedCase:
    case: str
    app: str
    repository: str
    commit: str
    upstream_path: str
    source_sha: str
    local_path: str
    kind: str
    loader: str
    class_name: str
    member: str
    signature: str
    line: int
    column: int
    class_expr: dict[str, Any]
    member_expr: dict[str, Any]
    program: dict[str, Any]
    expected_rows: list[dict[str, Any]]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise FrontendError(message)


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    payload = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    return hashlib.sha1(payload).hexdigest()  # nosec - Git object identity, not security use


def _load_gold() -> dict[str, Any]:
    try:
        value = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise FrontendError("cannot read frontend gold inventory") from exc
    _require(type(value) is dict and value.get("format") == GOLD_FORMAT, "frontend gold format")
    _require(value.get("extractor_policy") == {
        "audit_simple_java_lang_class": True,
        "audit_this_application_loader": True,
    }, "frontend gold extractor policy")
    events = value.get("events")
    _require(type(events) is list and events, "frontend gold events")
    cases = [event.get("case") for event in events if type(event) is dict]
    _require(len(cases) == len(events) and len(cases) == len(set(cases)), "frontend gold case IDs")
    return value


def _source_paths(gold: Mapping[str, Any]) -> list[Path]:
    paths: list[Path] = []
    seen: set[str] = set()
    for event in gold["events"]:
        rel = event["local_path"]
        if rel not in seen:
            seen.add(rel)
            path = (ARTIFACT_ROOT / rel).resolve()
            try:
                path.relative_to(ARTIFACT_ROOT.resolve())
            except ValueError as exc:
                raise FrontendError("frontend source escapes artifact root") from exc
            _require(path.is_file(), f"missing frontend source: {rel}")
            paths.append(path)
    return paths


def run_extractor(paths: Iterable[Path], *, audit_simple_java_lang_class: bool = False,
                  audit_this_application_loader: bool = False) -> dict[str, Any]:
    """Compile and run the Java extractor in a temporary directory."""
    paths = [Path(path).resolve() for path in paths]
    _require(bool(paths), "no Java sources supplied")
    javac = shutil.which("javac")
    java = shutil.which("java")
    _require(javac is not None and java is not None, "a full JDK with javac and java is required")
    _require(EXTRACTOR_SOURCE.is_file(), "missing Java extractor source")
    with tempfile.TemporaryDirectory(prefix="rrc-java-front-") as temp:
        build = Path(temp) / "classes"
        build.mkdir()
        compiled = subprocess.run(
            [javac, "-encoding", "UTF-8", "-d", str(build), str(EXTRACTOR_SOURCE)],
            cwd=ARTIFACT_ROOT,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if compiled.returncode != 0:
            raise FrontendError("javac failed: " + compiled.stderr.strip())
        policy_flags = []
        if audit_simple_java_lang_class:
            policy_flags.append("--audit-simple-java-lang-class")
        if audit_this_application_loader:
            policy_flags.append("--audit-this-application-loader")
        completed = subprocess.run(
            [java, "-cp", str(build), "JavaReflectionExtractor", *policy_flags, *map(str, paths)],
            cwd=ARTIFACT_ROOT,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if completed.returncode != 0:
            message = completed.stderr.strip() or completed.stdout.strip()
            raise FrontendError("Java extraction failed: " + message)
    try:
        report = json.loads(completed.stdout)
    except ValueError as exc:
        raise FrontendError("Java extractor emitted invalid JSON") from exc
    _require(type(report) is dict and report.get("format") == FRONTEND_FORMAT,
             "Java extractor format")
    _require(report.get("policy") == {
        "audit_simple_java_lang_class": audit_simple_java_lang_class,
        "audit_this_application_loader": audit_this_application_loader,
    }, "Java extractor policy")
    _require(report.get("parse_errors") == [], "Java parser reported errors")
    _require(type(report.get("files")) is list, "Java extractor files")
    return report


def _report_by_relative_path(report: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for file_record in report["files"]:
        _require(type(file_record) is dict and type(file_record.get("path")) is str,
                 "Java extractor file record")
        path = Path(file_record["path"]).resolve()
        try:
            rel = path.relative_to(ARTIFACT_ROOT.resolve()).as_posix()
        except ValueError as exc:
            raise FrontendError("Java extractor returned an unexpected path") from exc
        _require(rel not in output, "duplicate Java extractor path")
        output[rel] = file_record
    return output


def _normalized_event(event: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        "status", "kind", "loader", "class_expr", "class_constant",
        "member_expr", "member_constant", "signature", "assumptions", "offset", "end_offset",
        "line", "column",
    )
    return {key: event.get(key) for key in keys}


def _gold_event(event: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": "accepted",
        "kind": event["kind"],
        "loader": event["loader"],
        "class_expr": event["class_expr"],
        "class_constant": event["class"],
        "member_expr": event["member_expr"],
        "member_constant": event["member"],
        "signature": event["signature"],
        "assumptions": event.get("assumptions", []),
        "offset": event["offset"],
        "end_offset": event["end_offset"],
        "line": event["line"],
        "column": event["column"],
    }


def _collect_inputs(expr: Any, output: set[str]) -> None:
    _require(type(expr) is dict and type(expr.get("op")) is str, "frontend expression")
    op = expr["op"]
    if op == "lit":
        _require(set(expr) == {"op", "value"} and type(expr["value"]) in (str, bool),
                 "frontend literal")
        return
    if op == "input":
        _require(set(expr) == {"op", "name"} and type(expr["name"]) is str and expr["name"],
                 "frontend input")
        output.add(expr["name"])
        return
    arity = {"alias": 1, "not": 1, "and": 2, "or": 2, "eq": 2, "cat": 2, "ite": 3}.get(op)
    _require(arity is not None and set(expr) == {"op", "args"}, "frontend expression operation")
    args = expr["args"]
    _require(type(args) is list and len(args) == arity, "frontend expression arity")
    for arg in args:
        _collect_inputs(arg, output)


def _eval_expr(expr: Mapping[str, Any], environment: Mapping[str, bool]) -> str | bool:
    op = expr["op"]
    if op == "lit":
        return expr["value"]
    if op == "input":
        _require(expr["name"] in environment, "unbound frontend input")
        return environment[expr["name"]]
    args = [_eval_expr(arg, environment) for arg in expr["args"]]
    if op == "alias":
        return args[0]
    if op == "not":
        _require(type(args[0]) is bool, "frontend not sort")
        return not args[0]
    if op == "and":
        _require(all(type(arg) is bool for arg in args), "frontend and sort")
        return args[0] and args[1]
    if op == "or":
        _require(all(type(arg) is bool for arg in args), "frontend or sort")
        return args[0] or args[1]
    if op == "eq":
        _require(type(args[0]) is type(args[1]) and type(args[0]) in (str, bool),
                 "frontend equality sort")
        return args[0] == args[1]
    if op == "cat":
        _require(all(type(arg) is str for arg in args), "frontend concatenation sort")
        return args[0] + args[1]
    if op == "ite":
        _require(type(args[0]) is bool and type(args[1]) is type(args[2]), "frontend conditional sort")
        return args[1] if args[0] else args[2]
    raise FrontendError("unsupported frontend expression")


class _ProgramBuilder:
    def __init__(self, external: list[str]):
        _require(len(external) <= MAX_EXTERNAL, "frontend external-coordinate bound")
        self.program: dict[str, Any] = {
            "external": external,
            "choices": [],
            "nodes": [],
            "feasible": 0,
            "table": [],
            "sites": [],
        }
        self.input_nodes = {name: self.add({"op": "input", "index": index})
                            for index, name in enumerate(external)}
        self.true = self.add({"op": "lit", "value": True})
        self.program["feasible"] = self.true

    def add(self, node: dict[str, Any]) -> int:
        index = len(self.program["nodes"])
        self.program["nodes"].append(node)
        return index

    def expression(self, expr: Mapping[str, Any]) -> int:
        op = expr["op"]
        if op == "lit":
            return self.add({"op": "lit", "value": expr["value"]})
        if op == "input":
            return self.input_nodes[expr["name"]]
        args = [self.expression(arg) for arg in expr["args"]]
        return self.add({"op": op, "args": args})


def compile_event(event: Mapping[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Translate one accepted source event into the finite checker language."""
    _require(event.get("status") == "accepted", "cannot compile a rejected frontend event")
    inputs: set[str] = set()
    _collect_inputs(event["class_expr"], inputs)
    _collect_inputs(event["member_expr"], inputs)
    external = sorted(inputs)
    builder = _ProgramBuilder(external)
    loader = builder.add({"op": "lit", "value": event["loader"]})
    class_node = builder.expression(event["class_expr"])
    member_node = builder.expression(event["member_expr"])
    signature = builder.add({"op": "lit", "value": event["signature"]})
    builder.program["sites"].append({
        "guard": builder.true,
        "loader": loader,
        "class": class_node,
        "method": member_node,
        "signature": signature,
    })

    exact_keys: list[list[str]] = []
    expected_rows: list[dict[str, Any]] = []
    for bits in itertools.product((False, True), repeat=len(external)):
        environment = dict(zip(external, bits))
        class_name = _eval_expr(event["class_expr"], environment)
        member = _eval_expr(event["member_expr"], environment)
        _require(type(class_name) is str and type(member) is str, "frontend string result")
        key = [event["loader"], class_name, member, event["signature"]]
        _require(all(len(value.encode("ascii")) <= MAX_STRING for value in key),
                 "frontend target string bound")
        if key not in exact_keys:
            exact_keys.append(key)
        expected_rows.append({"feasible": True, "outcomes": [{"kind": "target", "key": key}]})
    # The product over zero inputs contains exactly one assignment.
    _require(bool(exact_keys), "frontend event has no assignments")
    seed = exact_keys[0]
    suffix = "$decoy"
    member = seed[2]
    if len((member + suffix).encode("ascii")) <= MAX_STRING:
        decoy_member = member + suffix
    else:
        decoy_member = "<missing>"
    decoy = [seed[0], seed[1], decoy_member, seed[3]]
    if decoy not in exact_keys:
        exact_keys.append(decoy)
    builder.program["table"] = exact_keys
    return validate(builder.program), expected_rows


@lru_cache(maxsize=1)
def public_frontend_evidence() -> dict[str, Any]:
    """Run, pin-check, and gold-check the redistributed public Java sources."""
    gold = _load_gold()
    paths = _source_paths(gold)
    blob_results: list[dict[str, Any]] = []
    expected_by_path: dict[str, list[dict[str, Any]]] = {}
    for event in gold["events"]:
        expected_by_path.setdefault(event["local_path"], []).append(event)
    for rel, events in expected_by_path.items():
        path = ARTIFACT_ROOT / rel
        expected_hashes = {event["blob_sha1"] for event in events}
        _require(len(expected_hashes) == 1, "conflicting frontend blob identities")
        actual = git_blob_sha1(path)
        expected = next(iter(expected_hashes))
        _require(actual == expected, f"frontend source blob mismatch: {rel}")
        blob_results.append({"local_path": rel, "expected_blob_sha1": expected,
                             "actual_blob_sha1": actual, "matched": True})

    report = run_extractor(
        paths,
        audit_simple_java_lang_class=True,
        audit_this_application_loader=True,
    )
    by_path = _report_by_relative_path(report)
    _require(set(by_path) == set(expected_by_path), "frontend source inventory mismatch")

    comparisons: list[dict[str, Any]] = []
    cases: list[ExtractedCase] = []
    accepted_total = 0
    rejected_total = 0
    for rel, expected_events in expected_by_path.items():
        actual_events = by_path[rel].get("events")
        _require(type(actual_events) is list, "frontend event list")
        accepted_total += sum(event.get("status") == "accepted" for event in actual_events)
        rejected_total += sum(event.get("status") == "rejected" for event in actual_events)
        _require(len(actual_events) == len(expected_events), f"frontend event count mismatch: {rel}")
        for expected, actual in zip(expected_events, actual_events):
            normalized = _normalized_event(actual)
            locked = _gold_event(expected)
            _require(strict_equal(normalized, locked), f"frontend gold mismatch: {expected['case']}")
            program, expected_rows = compile_event(actual)
            comparisons.append({
                "case": expected["case"],
                "local_path": rel,
                "line": actual["line"],
                "column": actual["column"],
                "kind": actual["kind"],
                "assumptions": actual.get("assumptions", []),
                "matched": True,
            })
            cases.append(ExtractedCase(
                case=expected["case"],
                app=expected["app"],
                repository=expected["repository"],
                commit=expected["commit"],
                upstream_path=expected["upstream_path"],
                source_sha=expected["blob_sha1"],
                local_path=rel,
                kind=actual["kind"],
                loader=actual["loader"],
                class_name=actual["class_constant"],
                member=actual["member_constant"],
                signature=actual["signature"],
                line=actual["line"],
                column=actual["column"],
                class_expr=actual["class_expr"],
                member_expr=actual["member_expr"],
                program=program,
                expected_rows=expected_rows,
            ))
    _require(accepted_total == len(gold["events"]), "frontend accepted-event total")
    _require(rejected_total == 0, "pinned public source unexpectedly rejected")
    _require([case.case for case in cases] == [event["case"] for event in gold["events"]],
             "frontend case ordering")
    return {
        "format": FRONTEND_FORMAT,
        "source_files": len(paths),
        "gold_events": len(gold["events"]),
        "accepted_events": accepted_total,
        "rejected_events": rejected_total,
        "gold_matches": len(comparisons),
        "blob_matches": len(blob_results),
        "blob_checks": blob_results,
        "comparisons": comparisons,
        "cases": tuple(cases),
    }


def public_source_cases() -> tuple[ExtractedCase, ...]:
    return public_frontend_evidence()["cases"]


def frontend_result_record() -> dict[str, Any]:
    evidence = public_frontend_evidence()
    return {key: value for key, value in evidence.items() if key != "cases"}



def runtime_probe_record() -> dict[str, Any]:
    """Compare extracted finite identities with actual local Java reflection.

    The probe is self-contained and uses only classes declared in RuntimeFinite.java.
    It exercises the accepted Boolean/string fragment over all four assignments and
    reports one comparison for the class-lookup event and one for the member-lookup
    event in each assignment.
    """
    source = FRONTEND_ROOT / "fixtures" / "RuntimeFinite.java"
    _require(source.is_file(), "missing runtime frontend probe")
    report = run_extractor([source])
    events = report["files"][0]["events"]
    _require(len(events) == 2 and all(event.get("status") == "accepted" for event in events),
             "runtime frontend probe extraction")
    _require([event.get("kind") for event in events] == ["Class.forName", "Class.getMethod"],
             "runtime frontend probe event order")

    javac = shutil.which("javac")
    java = shutil.which("java")
    _require(javac is not None and java is not None, "a full JDK with javac and java is required")
    rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="rrc-java-runtime-") as temp:
        build = Path(temp) / "classes"
        build.mkdir()
        compiled = subprocess.run(
            [javac, "-encoding", "UTF-8", "-d", str(build), str(source)],
            cwd=ARTIFACT_ROOT,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if compiled.returncode != 0:
            raise FrontendError("runtime probe javac failed: " + compiled.stderr.strip())
        for h, k in itertools.product((False, True), repeat=2):
            completed = subprocess.run(
                [java, "-cp", str(build), "RuntimeFinite", str(h).lower(), str(k).lower()],
                cwd=ARTIFACT_ROOT,
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            if completed.returncode != 0:
                message = completed.stderr.strip() or completed.stdout.strip()
                raise FrontendError("runtime reflection probe failed: " + message)
            fields = completed.stdout.rstrip("\n").split("\t")
            _require(len(fields) == 3, "runtime reflection probe output")
            actual_class, actual_member, actual_parameter = fields
            environment = {"h": h, "k": k}
            expected_class_0 = _eval_expr(events[0]["class_expr"], environment)
            expected_class_1 = _eval_expr(events[1]["class_expr"], environment)
            expected_member = _eval_expr(events[1]["member_expr"], environment)
            _require(actual_class == expected_class_0 == expected_class_1,
                     "runtime class identity mismatch")
            _require(actual_member == expected_member, "runtime member identity mismatch")
            _require(actual_parameter == "java.lang.String" and events[1]["signature"] == "(String)",
                     "runtime signature identity mismatch")
            rows.append({
                "assignment": [h, k],
                "class": actual_class,
                "member": actual_member,
                "parameter": actual_parameter,
                "matched": True,
            })
    return {
        "format": "rrc-java-runtime-probe-v1",
        "source": source.relative_to(ARTIFACT_ROOT).as_posix(),
        "events": 2,
        "assignments": len(rows),
        "identity_checks": len(rows) * 2,
        "rows": rows,
    }


def bridge_risk_record() -> dict[str, Any]:
    """Execute the four source-level bridge regressions and require fail-closed extraction.

    These programs are independent Java executions, not finite-backend tests.  They show why
    reference equality, compound updates, switch-carried state, and name-only API recognition
    cannot be admitted by the syntactic bridge.  The fixed extractor must reject all seven
    reflection-looking events while the Java programs still execute with their native meaning.
    """
    root = FRONTEND_ROOT / "bridge_risks"
    paths = sorted(root.glob("*.java"))
    _require([path.name for path in paths] == [
        "ApiIdentityRisk.java",
        "CompoundAssignmentRisk.java",
        "ReferenceEqualityRisk.java",
        "SwitchBindingRisk.java",
    ], "bridge-risk source inventory")
    report = run_extractor(paths)
    by_name = {Path(record["path"]).name: record for record in report["files"]}
    expected_rejections = {
        "ApiIdentityRisk.java": [
            "shadowed_class_api_receiver",
            "shadowed_application_loader_getter",
            "unaudited_loader_getter",
        ],
        "CompoundAssignmentRisk.java": [
            "unsupported_compound_assignment",
            "unsupported_compound_assignment",
        ],
        "ReferenceEqualityRisk.java": ["unsupported_string_reference_equality"],
        "SwitchBindingRisk.java": ["unsupported_switch_state_merge"],
    }
    rejection_rows: list[dict[str, Any]] = []
    for name, reasons in expected_rejections.items():
        events = by_name[name]["events"]
        actual = [event.get("reason") for event in events if event.get("status") == "rejected"]
        _require(actual == reasons, f"bridge-risk rejection mismatch: {name}")
        _require(all(event.get("status") == "rejected" for event in events),
                 f"bridge-risk event accepted: {name}")
        rejection_rows.append({"source": name, "reasons": reasons, "matched": True})

    javac = shutil.which("javac")
    java = shutil.which("java")
    _require(javac is not None and java is not None, "a full JDK with javac and java is required")
    executions = [
        ("ReferenceEqualityRisk", ["false"], "false\ttrue\tReferenceDifferent"),
        ("ReferenceEqualityRisk", ["true"], "false\ttrue\tReferenceDifferent"),
        ("CompoundAssignmentRisk", ["false", "false"], "B\tB"),
        ("CompoundAssignmentRisk", ["false", "true"], "B\tB"),
        ("CompoundAssignmentRisk", ["true", "false"], "A\tB"),
        ("CompoundAssignmentRisk", ["true", "true"], "A\tA"),
        ("SwitchBindingRisk", ["false"], "B"),
        ("SwitchBindingRisk", ["true"], "A"),
        ("ApiIdentityRisk", [], "ShadowTarget\tLoaderTarget\tLoaderTarget"),
    ]
    runtime_rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="rrc-java-bridge-risks-") as temp:
        build = Path(temp) / "classes"
        build.mkdir()
        compiled = subprocess.run(
            [javac, "-encoding", "UTF-8", "-d", str(build), *map(str, paths)],
            cwd=ARTIFACT_ROOT,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if compiled.returncode != 0:
            raise FrontendError("bridge-risk javac failed: " + compiled.stderr.strip())
        for main_class, arguments, expected in executions:
            completed = subprocess.run(
                [java, "-cp", str(build), main_class, *arguments],
                cwd=ARTIFACT_ROOT,
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            if completed.returncode != 0:
                message = completed.stderr.strip() or completed.stdout.strip()
                raise FrontendError(f"bridge-risk execution failed ({main_class}): {message}")
            actual = completed.stdout.rstrip("\n")
            _require(actual == expected, f"bridge-risk runtime mismatch: {main_class} {arguments}")
            runtime_rows.append({
                "class": main_class,
                "arguments": arguments,
                "output": actual,
                "matched": True,
            })
    return {
        "format": "rrc-java-bridge-risk-v1",
        "source_files": len(paths),
        "runtime_executions": len(runtime_rows),
        "rejected_events": sum(len(reasons) for reasons in expected_rejections.values()),
        "string_reference_equality_executions": 2,
        "compound_assignment_executions": 4,
        "switch_executions": 2,
        "api_identity_executions": 1,
        "rejections": rejection_rows,
        "runtime": runtime_rows,
    }


def frontend_control_record() -> dict[str, Any]:
    """Run the supported-expression pilot and seven fail-closed source controls."""
    fixture_root = FRONTEND_ROOT / "fixtures"
    paths = sorted(fixture_root.glob("*.java"))
    _require(len(paths) == 10, "frontend control inventory")
    report = run_extractor(paths)
    by_name = {Path(record["path"]).name: record for record in report["files"]}
    _require(set(by_name) == {path.name for path in paths}, "frontend control source inventory")
    expected_rejections = {
        "UnsupportedHeap.java": "unsupported_class_name_expression",
        "UnsupportedInput.java": "unsupported_class_name_expression",
        "UnsupportedLoader.java": "unsupported_loader_receiver",
        "UnsupportedReceiver.java": "unresolved_class_receiver",
        "UnsupportedParameter.java": "unsupported_parameter_type_expression",
        "UnsupportedControl.java": "unsupported_control_context",
        "UnsupportedReassignment.java": "unsupported_control_state_merge",
    }
    rejection_rows: list[dict[str, Any]] = []
    for name, reason in expected_rejections.items():
        rejected = [event for event in by_name[name]["events"] if event.get("status") == "rejected"]
        _require(len(rejected) == 1 and rejected[0].get("reason") == reason,
                 f"frontend rejection control failed: {name}")
        rejection_rows.append({"source": name, "reason": reason, "matched": True})

    _require(by_name["UnrelatedMethods.java"]["events"] == [],
             "unrelated reflection-like methods must be ignored")

    supported = by_name["SupportedFinite.java"]["events"]
    _require(len(supported) == 2 and all(event.get("status") == "accepted" for event in supported),
             "supported frontend pilot")
    assignment_checks = 0
    accepted_rows: list[dict[str, Any]] = []
    from .producer import produce
    from .factor import produce_factorized
    from .factor_checker import check_factorized
    for event in supported:
        program, expected = compile_event(event)
        rows = produce(program)["rows"]
        actual = [{"feasible": row["feasible"], "outcomes": row["outcomes"]} for row in rows]
        _require(strict_equal(actual, expected), "frontend expression-preservation pilot")
        checked = check_factorized(program, produce_factorized(program))
        assignment_checks += checked["assignments"]
        accepted_rows.append({
            "kind": event["kind"],
            "external_coordinates": len(program["external"]),
            "assignments": checked["assignments"],
            "exact_targets": len(checked["summary"]["may"][0]),
        })
    return {
        "format": "rrc-java-front-controls-v1",
        "control_sources": len(paths),
        "supported_events": len(supported),
        "supported_assignment_checks": assignment_checks,
        "rejection_controls": len(rejection_rows),
        "ignored_nonreflection_controls": 1,
        "runtime_probe": runtime_probe_record(),
        "direct_call_probe": direct_call_probe_record(),
        "bridge_risks": bridge_risk_record(),
        "accepted": accepted_rows,
        "rejected": rejection_rows,
    }


def _render_direct_java_method(dispatch: Mapping[str, Any], method_name: str = "dispatch") -> str:
    """Render the checked runtime pilot dispatcher as direct Java calls.

    This deliberately narrow renderer supports the self-contained pilot's default-loader,
    zero-argument constructors and one-String-argument methods.  The general finite
    preservation claim is established by ``dispatch_checker``; this renderer is only an
    executable Java sanity check for that restricted calling convention.
    """
    from .dispatch_checker import check_direct_dispatch

    program = dispatch["program"]
    checked = check_direct_dispatch(program, dispatch)
    _require(len(dispatch["roots"]) == 1 and checked["trace_events"] == checked["assignments"],
             "direct Java pilot requires one site")
    bit_order = dispatch["bit_order"]
    _require(all(name.isidentifier() for name in bit_order), "direct Java pilot input names")
    nodes = dispatch["diagram"]["nodes"]

    def render(node_id: int, indent: str) -> list[str]:
        node = nodes[node_id]
        if node["kind"] == "terminal":
            action = node["action"]
            _require(action["kind"] == "invoke", "direct Java pilot requires total invocation")
            key = program["table"][action["target"]]
            loader, class_name, member, signature = key
            _require(loader == "default" and signature == "(String)",
                     "direct Java pilot target convention")
            _require(all(part.isidentifier() for part in class_name.replace("$", ".").split(".")),
                     "direct Java pilot class name")
            _require(member.isidentifier(), "direct Java pilot member name")
            source_class = class_name.replace("$", ".")
            return [f"{indent}return new {source_class}().{member}(value);"]
        name = bit_order[node["var"]]
        lines = [f"{indent}if ({name}) {{"]
        lines.extend(render(node["high"], indent + "    "))
        lines.append(f"{indent}}} else {{")
        lines.extend(render(node["low"], indent + "    "))
        lines.append(f"{indent}}}")
        return lines

    parameters = ", ".join([f"boolean {name}" for name in bit_order] + ["String value"])
    body = [f"    static String {method_name}({parameters}) {{"]
    body.extend(render(dispatch["roots"][0], "        "))
    body.append("    }")
    return "\n".join(body)


def direct_call_probe_record() -> dict[str, Any]:
    """Compare generated direct Java calls with actual reflection on 12 executions."""
    from .dispatch import produce_direct_dispatch
    from .dispatch_checker import check_direct_dispatch
    from .factor import produce_factorized

    source = FRONTEND_ROOT / "runtime" / "RuntimeInvoke.java"
    _require(source.is_file(), "missing direct-call runtime probe")
    report = run_extractor([source])
    accepted = [event for event in report["files"][0]["events"] if event.get("status") == "accepted"]
    method_events = [event for event in accepted if event.get("kind") == "Class.getMethod"]
    _require(len(method_events) == 1, "direct-call runtime member event")
    program, expected = compile_event(method_events[0])
    certificate = produce_factorized(program)
    dispatch = produce_direct_dispatch(program, certificate)
    replay = check_direct_dispatch(program, dispatch)
    _require(replay["assignments"] == 4 and replay["invocations"] == 4,
             "direct-call runtime finite replay")
    generated_method = _render_direct_java_method(dispatch)
    direct_source = "\n".join([
        "final class RuntimeInvokeDirect {",
        generated_method,
        "",
        "    public static void main(String[] args) {",
        "        if (args.length != 3) {",
        "            throw new IllegalArgumentException(\"expected two Boolean arguments and one value\");",
        "        }",
        "        System.out.println(dispatch(Boolean.parseBoolean(args[0]), Boolean.parseBoolean(args[1]), args[2]));",
        "    }",
        "}",
        "",
    ])

    javac = shutil.which("javac")
    java = shutil.which("java")
    _require(javac is not None and java is not None, "a full JDK with javac and java is required")
    payloads = ("value", "edge-0", "")
    rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="rrc-java-direct-") as temp:
        temp_path = Path(temp)
        generated = temp_path / "RuntimeInvokeDirect.java"
        generated.write_text(direct_source, encoding="utf-8")
        build = temp_path / "classes"
        build.mkdir()
        compiled = subprocess.run(
            [javac, "-encoding", "UTF-8", "-d", str(build), str(source), str(generated)],
            cwd=ARTIFACT_ROOT,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if compiled.returncode != 0:
            raise FrontendError("direct-call probe javac failed: " + compiled.stderr.strip())
        for h, k in itertools.product((False, True), repeat=2):
            for payload in payloads:
                arguments = [str(h).lower(), str(k).lower(), payload]
                reflective = subprocess.run(
                    [java, "-cp", str(build), "RuntimeInvoke", *arguments],
                    cwd=ARTIFACT_ROOT,
                    capture_output=True,
                    text=True,
                    timeout=20,
                    check=False,
                )
                direct = subprocess.run(
                    [java, "-cp", str(build), "RuntimeInvokeDirect", *arguments],
                    cwd=ARTIFACT_ROOT,
                    capture_output=True,
                    text=True,
                    timeout=20,
                    check=False,
                )
                if reflective.returncode != 0 or direct.returncode != 0:
                    raise FrontendError("direct-call runtime execution failed")
                reflective_value = reflective.stdout.rstrip("\n")
                direct_value = direct.stdout.rstrip("\n")
                _require(reflective_value == direct_value, "direct-call runtime mismatch")
                rows.append({
                    "assignment": [h, k],
                    "payload": payload,
                    "reflective": reflective_value,
                    "direct": direct_value,
                    "matched": True,
                })
    return {
        "format": "rrc-java-direct-call-probe",
        "source": source.relative_to(ARTIFACT_ROOT).as_posix(),
        "accepted_events": len(accepted),
        "selected_event": "Class.getMethod",
        "assignments": 4,
        "payloads": len(payloads),
        "invocation_checks": len(rows),
        "generated_source_lines": len(direct_source.splitlines()),
        "finite_trace_events": replay["trace_events"],
        "rows": rows,
    }
