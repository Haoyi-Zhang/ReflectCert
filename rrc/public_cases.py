"""Pinned public reflection cases.

P001--P011 remain hand-audited finite projections because their upstream source is
not redistributed here.  P012--P040 are constructed from exact LGPL-licensed Java
source by the fail-closed javac-AST bridge and checked against a pinned event gold
inventory.  Neither population is an APK execution or whole-program claim.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .fixtures import Builder

DROIDBENCH_COMMIT = "a57fa6f42f278591695672f1aa8b37c275139370"
DROIDRA_COMMIT = "b766a32a23178a54d095fb0a473e6ec77aad2166"


@dataclass(frozen=True)
class PublicSpec:
    app: str
    repository: str
    commit: str
    path: str
    source_sha: str
    operation: str
    loader: str
    class_name: str
    member: str
    signature: str
    expression: str = "literal"
    note: str = ""
    extraction_mode: str = "manual finite projection"
    local_path: str = ""
    source_line: int = 0
    source_column: int = 0
    class_expr_json: str = ""
    member_expr_json: str = ""


# Forty modeled operations from the thirteen reflection benchmark apps that form
# the public DroidRA/DroidBench lineage.  Repeated target identities are retained
# when distinct source operations (for example field write and field read) exercise
# different provenance obligations.
SPECS: tuple[PublicSpec, ...] = (
    PublicSpec("Reflection1", "secure-software-engineering/DroidBench", DROIDBENCH_COMMIT,
               "projects/Reflection/Reflection1/app/src/main/java/de/ecspride/MainActivity.java",
               "b38e8c097d3a163df652accc47c7f34bc28dd493", "Class.forName", "default",
               "de.ecspride.ConcreteClass", "<class>", "()"),
    PublicSpec("Reflection1", "secure-software-engineering/DroidBench", DROIDBENCH_COMMIT,
               "projects/Reflection/Reflection1/app/src/main/java/de/ecspride/MainActivity.java",
               "b38e8c097d3a163df652accc47c7f34bc28dd493", "Class.newInstance", "default",
               "de.ecspride.ConcreteClass", "<init>", "()"),
    PublicSpec("Reflection2", "secure-software-engineering/DroidBench", DROIDBENCH_COMMIT,
               "projects/Reflection/Reflection2/app/src/main/java/de/ecspride/MainActivity.java",
               "65937509bb72012a57d8470e79b5ebb3bfe15e3a", "Class.forName", "default",
               "de.ecspride.ConcreteClass", "<class>", "()"),
    PublicSpec("Reflection2", "secure-software-engineering/DroidBench", DROIDBENCH_COMMIT,
               "projects/Reflection/Reflection2/app/src/main/java/de/ecspride/MainActivity.java",
               "65937509bb72012a57d8470e79b5ebb3bfe15e3a", "method reached through reflective instance",
               "default", "de.ecspride.ConcreteClass", "foo", "()",
               note="downstream member target, not a java.lang.reflect.Method lookup"),
    PublicSpec("Reflection3", "secure-software-engineering/DroidBench", DROIDBENCH_COMMIT,
               "projects/Reflection/Reflection3/app/src/main/java/de/ecspride/MainActivity.java",
               "18df34d37e75c4a4612dfc594cae5d655e684dca", "Class.forName", "default",
               "de.ecspride.ReflectiveClass", "<class>", "()"),
    PublicSpec("Reflection3", "secure-software-engineering/DroidBench", DROIDBENCH_COMMIT,
               "projects/Reflection/Reflection3/app/src/main/java/de/ecspride/MainActivity.java",
               "18df34d37e75c4a4612dfc594cae5d655e684dca", "Class.newInstance", "default",
               "de.ecspride.ReflectiveClass", "<init>", "()"),
    PublicSpec("Reflection3", "secure-software-engineering/DroidBench", DROIDBENCH_COMMIT,
               "projects/Reflection/Reflection3/app/src/main/java/de/ecspride/MainActivity.java",
               "18df34d37e75c4a4612dfc594cae5d655e684dca", "Class.getMethod", "default",
               "de.ecspride.ReflectiveClass", "setImei", "(String)", "concat"),
    PublicSpec("Reflection3", "secure-software-engineering/DroidBench", DROIDBENCH_COMMIT,
               "projects/Reflection/Reflection3/app/src/main/java/de/ecspride/MainActivity.java",
               "18df34d37e75c4a4612dfc594cae5d655e684dca", "Class.getMethod", "default",
               "de.ecspride.ReflectiveClass", "getImei", "()"),
    PublicSpec("Reflection4", "secure-software-engineering/DroidBench", DROIDBENCH_COMMIT,
               "projects/Reflection/Reflection4/app/src/main/java/de/ecspride/MainActivity.java",
               "a06fdc94039384115ba5352c6ed349e5636e8b1b", "Class.forName", "default",
               "de.ecspride.ConcreteClass", "<class>", "()"),
    PublicSpec("Reflection4", "secure-software-engineering/DroidBench", DROIDBENCH_COMMIT,
               "projects/Reflection/Reflection4/app/src/main/java/de/ecspride/MainActivity.java",
               "a06fdc94039384115ba5352c6ed349e5636e8b1b", "member reached through reflective instance",
               "default", "de.ecspride.ConcreteClass", "foo", "(Context)",
               note="downstream member target after reflective instantiation"),
    PublicSpec("Reflection4", "secure-software-engineering/DroidBench", DROIDBENCH_COMMIT,
               "projects/Reflection/Reflection4/app/src/main/java/de/ecspride/MainActivity.java",
               "a06fdc94039384115ba5352c6ed349e5636e8b1b", "member reached through reflective instance",
               "default", "de.ecspride.ConcreteClass", "bar", "(String)",
               note="downstream member target after reflective instantiation"),
    PublicSpec("Reflection5", "serval-snt-uni-lu/DroidRA", DROIDRA_COMMIT,
               "benchmark-apps/eclipse-projects/Reflection_Reflection5/src/lu/uni/snt/reflection5/MainActivity.java",
               "3cc3637fcb5d4480db75b22ecf0b601042ad1594", "Class.forName", "default",
               "lu.uni.snt.reflection5.ConcreteClass", "<class>", "()"),
    PublicSpec("Reflection5", "serval-snt-uni-lu/DroidRA", DROIDRA_COMMIT,
               "benchmark-apps/eclipse-projects/Reflection_Reflection5/src/lu/uni/snt/reflection5/MainActivity.java",
               "3cc3637fcb5d4480db75b22ecf0b601042ad1594", "Class.getConstructor", "default",
               "lu.uni.snt.reflection5.ConcreteClass", "<init>", "(String)"),
    PublicSpec("Reflection6", "serval-snt-uni-lu/DroidRA", DROIDRA_COMMIT,
               "benchmark-apps/eclipse-projects/Reflection_Reflection6/src/lu/uni/snt/reflection6/MainActivity.java",
               "31dcc408714b010dce891b559aeaa9920b9292dc", "Class.forName", "default",
               "lu.uni.snt.reflection6.ConcreteClass", "<class>", "()"),
    PublicSpec("Reflection6", "serval-snt-uni-lu/DroidRA", DROIDRA_COMMIT,
               "benchmark-apps/eclipse-projects/Reflection_Reflection6/src/lu/uni/snt/reflection6/MainActivity.java",
               "31dcc408714b010dce891b559aeaa9920b9292dc", "Class.getConstructors", "default",
               "lu.uni.snt.reflection6.ConcreteClass", "<constructors>", "[]"),
    PublicSpec("Reflection7", "serval-snt-uni-lu/DroidRA", DROIDRA_COMMIT,
               "benchmark-apps/eclipse-projects/Reflection_Reflection7/src/lu/uni/snt/reflection7/MainActivity.java",
               "637858279624eb5dd9e3308b7c18952a8edefc6d", "Class.forName", "default",
               "lu.uni.snt.reflection7.ConcreteClass", "<class>", "()"),
    PublicSpec("Reflection7", "serval-snt-uni-lu/DroidRA", DROIDRA_COMMIT,
               "benchmark-apps/eclipse-projects/Reflection_Reflection7/src/lu/uni/snt/reflection7/MainActivity.java",
               "637858279624eb5dd9e3308b7c18952a8edefc6d", "Class.getConstructor", "default",
               "lu.uni.snt.reflection7.ConcreteClass", "<init>", "(String)"),
    PublicSpec("Reflection7", "serval-snt-uni-lu/DroidRA", DROIDRA_COMMIT,
               "benchmark-apps/eclipse-projects/Reflection_Reflection7/src/lu/uni/snt/reflection7/MainActivity.java",
               "637858279624eb5dd9e3308b7c18952a8edefc6d", "Class.getMethod", "default",
               "lu.uni.snt.reflection7.ConcreteClass", "setImei", "(String)", "concat"),
    PublicSpec("Reflection7", "serval-snt-uni-lu/DroidRA", DROIDRA_COMMIT,
               "benchmark-apps/eclipse-projects/Reflection_Reflection7/src/lu/uni/snt/reflection7/MainActivity.java",
               "637858279624eb5dd9e3308b7c18952a8edefc6d", "Class.getMethod", "default",
               "lu.uni.snt.reflection7.ConcreteClass", "getImei", "()"),
    PublicSpec("Reflection8", "serval-snt-uni-lu/DroidRA", DROIDRA_COMMIT,
               "benchmark-apps/eclipse-projects/Reflection_Reflection8/src/lu/uni/snt/reflection8/MainActivity.java",
               "93793b309606e4ae09c0184f89c0684496c54a84", "ClassLoader.loadClass", "app",
               "lu.uni.snt.reflection8.ConcreteClass", "<class>", "()"),
    PublicSpec("Reflection8", "serval-snt-uni-lu/DroidRA", DROIDRA_COMMIT,
               "benchmark-apps/eclipse-projects/Reflection_Reflection8/src/lu/uni/snt/reflection8/MainActivity.java",
               "93793b309606e4ae09c0184f89c0684496c54a84", "Class.newInstance", "app",
               "lu.uni.snt.reflection8.ConcreteClass", "<init>", "()"),
    PublicSpec("Reflection9", "serval-snt-uni-lu/DroidRA", DROIDRA_COMMIT,
               "benchmark-apps/eclipse-projects/Reflection_Reflection9/src/lu/uni/snt/reflection9/MainActivity.java",
               "a135998b103c496d08ed1af7fccbbd2694d8297f", "ClassLoader.loadClass", "app",
               "lu.uni.snt.reflection9.ConcreteClass", "<class>", "()"),
    PublicSpec("Reflection9", "serval-snt-uni-lu/DroidRA", DROIDRA_COMMIT,
               "benchmark-apps/eclipse-projects/Reflection_Reflection9/src/lu/uni/snt/reflection9/MainActivity.java",
               "a135998b103c496d08ed1af7fccbbd2694d8297f", "Class.newInstance", "app",
               "lu.uni.snt.reflection9.ConcreteClass", "<init>", "()"),
    PublicSpec("Reflection9", "serval-snt-uni-lu/DroidRA", DROIDRA_COMMIT,
               "benchmark-apps/eclipse-projects/Reflection_Reflection9/src/lu/uni/snt/reflection9/MainActivity.java",
               "a135998b103c496d08ed1af7fccbbd2694d8297f", "Class.getField", "app",
               "lu.uni.snt.reflection9.ConcreteClass", "imei", "String"),
    PublicSpec("Reflection9", "serval-snt-uni-lu/DroidRA", DROIDRA_COMMIT,
               "benchmark-apps/eclipse-projects/Reflection_Reflection9/src/lu/uni/snt/reflection9/MainActivity.java",
               "a135998b103c496d08ed1af7fccbbd2694d8297f", "Class.getMethod", "app",
               "lu.uni.snt.reflection9.ConcreteClass", "getImei", "()"),
    PublicSpec("Reflection10", "serval-snt-uni-lu/DroidRA", DROIDRA_COMMIT,
               "benchmark-apps/eclipse-projects/Reflection_Reflection10/src/lu/uni/snt/reflection10/MainActivity.java",
               "66465d88d8b3fe933f7e5a269ae3b270b092c4d1", "ClassLoader.loadClass", "app",
               "lu.uni.snt.reflection10.ConcreteClass", "<class>", "()"),
    PublicSpec("Reflection10", "serval-snt-uni-lu/DroidRA", DROIDRA_COMMIT,
               "benchmark-apps/eclipse-projects/Reflection_Reflection10/src/lu/uni/snt/reflection10/MainActivity.java",
               "66465d88d8b3fe933f7e5a269ae3b270b092c4d1", "Class.getConstructor", "app",
               "lu.uni.snt.reflection10.ConcreteClass", "<init>", "(String)"),
    PublicSpec("Reflection10", "serval-snt-uni-lu/DroidRA", DROIDRA_COMMIT,
               "benchmark-apps/eclipse-projects/Reflection_Reflection10/src/lu/uni/snt/reflection10/MainActivity.java",
               "66465d88d8b3fe933f7e5a269ae3b270b092c4d1", "Class.getField", "app",
               "lu.uni.snt.reflection10.ConcreteClass", "imei", "String"),
    PublicSpec("Reflection11", "serval-snt-uni-lu/DroidRA", DROIDRA_COMMIT,
               "benchmark-apps/eclipse-projects/Reflection_Reflection11/src/lu/uni/snt/reflection11/InFlowActivity.java",
               "7f6e104166f3f860dfdc98e0c7a79d7f1dc8ef46", "Class.forName", "default",
               "lu.uni.snt.reflection11.ReflectiveClass", "<class>", "()"),
    PublicSpec("Reflection11", "serval-snt-uni-lu/DroidRA", DROIDRA_COMMIT,
               "benchmark-apps/eclipse-projects/Reflection_Reflection11/src/lu/uni/snt/reflection11/InFlowActivity.java",
               "7f6e104166f3f860dfdc98e0c7a79d7f1dc8ef46", "Class.newInstance", "default",
               "lu.uni.snt.reflection11.ReflectiveClass", "<init>", "()"),
    PublicSpec("Reflection11", "serval-snt-uni-lu/DroidRA", DROIDRA_COMMIT,
               "benchmark-apps/eclipse-projects/Reflection_Reflection11/src/lu/uni/snt/reflection11/InFlowActivity.java",
               "7f6e104166f3f860dfdc98e0c7a79d7f1dc8ef46", "Class.getMethod", "default",
               "lu.uni.snt.reflection11.ReflectiveClass", "setImei", "(String)", "concat"),
    PublicSpec("Reflection11", "serval-snt-uni-lu/DroidRA", DROIDRA_COMMIT,
               "benchmark-apps/eclipse-projects/Reflection_Reflection11/src/lu/uni/snt/reflection11/InFlowActivity.java",
               "7f6e104166f3f860dfdc98e0c7a79d7f1dc8ef46", "Class.getMethod", "default",
               "lu.uni.snt.reflection11.ReflectiveClass", "getImei", "()"),
    PublicSpec("Reflection12", "serval-snt-uni-lu/DroidRA", DROIDRA_COMMIT,
               "benchmark-apps/eclipse-projects/Reflection_Reflection12/src/lu/uni/snt/reflection12/MainActivity.java",
               "7466d42a589fff30cf12ffaeeee6c90bbfda985d", "Class.forName", "default",
               "lu.uni.snt.reflection12.ConcreteClass", "<class>", "()"),
    PublicSpec("Reflection12", "serval-snt-uni-lu/DroidRA", DROIDRA_COMMIT,
               "benchmark-apps/eclipse-projects/Reflection_Reflection12/src/lu/uni/snt/reflection12/MainActivity.java",
               "7466d42a589fff30cf12ffaeeee6c90bbfda985d", "Class.getConstructor", "default",
               "lu.uni.snt.reflection12.ConcreteClass", "<init>", "(String)"),
    PublicSpec("Reflection12", "serval-snt-uni-lu/DroidRA", DROIDRA_COMMIT,
               "benchmark-apps/eclipse-projects/Reflection_Reflection12/src/lu/uni/snt/reflection12/MainActivity.java",
               "7466d42a589fff30cf12ffaeeee6c90bbfda985d", "Class.getField for write", "default",
               "lu.uni.snt.reflection12.ConcreteClass", "imei", "String",
               note="same identity as the later read, retained as a distinct source operation"),
    PublicSpec("Reflection12", "serval-snt-uni-lu/DroidRA", DROIDRA_COMMIT,
               "benchmark-apps/eclipse-projects/Reflection_Reflection12/src/lu/uni/snt/reflection12/MainActivity.java",
               "7466d42a589fff30cf12ffaeeee6c90bbfda985d", "Class.getField for read", "default",
               "lu.uni.snt.reflection12.ConcreteClass", "imei", "String",
               note="same identity as the earlier write, retained as a distinct source operation"),
    PublicSpec("Reflection13", "serval-snt-uni-lu/DroidRA", DROIDRA_COMMIT,
               "benchmark-apps/eclipse-projects/Reflection_Reflection13/src/lu/uni/snt/reflection13/MainActivity.java",
               "a00c927dbc826681e515443d8d5a550b82fd4ed3", "Class.forName", "default",
               "lu.uni.snt.reflection13.ConcreteClass", "<class>", "()"),
    PublicSpec("Reflection13", "serval-snt-uni-lu/DroidRA", DROIDRA_COMMIT,
               "benchmark-apps/eclipse-projects/Reflection_Reflection13/src/lu/uni/snt/reflection13/MainActivity.java",
               "a00c927dbc826681e515443d8d5a550b82fd4ed3", "Class.getConstructor", "default",
               "lu.uni.snt.reflection13.ConcreteClass", "<init>", "(String)"),
    PublicSpec("Reflection13", "serval-snt-uni-lu/DroidRA", DROIDRA_COMMIT,
               "benchmark-apps/eclipse-projects/Reflection_Reflection13/src/lu/uni/snt/reflection13/MainActivity.java",
               "a00c927dbc826681e515443d8d5a550b82fd4ed3", "Class.getFields", "default",
               "lu.uni.snt.reflection13.ConcreteClass", "<fields>", "[]"),
    PublicSpec("Reflection13", "serval-snt-uni-lu/DroidRA", DROIDRA_COMMIT,
               "benchmark-apps/eclipse-projects/Reflection_Reflection13/src/lu/uni/snt/reflection13/MainActivity.java",
               "a00c927dbc826681e515443d8d5a550b82fd4ed3", "Class.getField", "default",
               "lu.uni.snt.reflection13.ConcreteClass", "imei", "String"),
)

assert len(SPECS) == 40


def _string_node(builder: Builder, value: str, expression: str) -> int:
    if expression == "concat" and len(value) > 1:
        # The public source uses "setIme" + "i".  Keeping the construction in
        # the finite input distinguishes string construction from a pre-folded literal.
        return builder.node("cat", builder.lit(value[:-1]), builder.lit(value[-1]))
    if expression == "alias":
        return builder.node("alias", builder.lit(value))
    return builder.lit(value)


def make_case(spec: PublicSpec) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    builder = Builder()
    loader = _string_node(builder, spec.loader, "literal")
    class_name = _string_node(builder, spec.class_name, "literal")
    member = _string_node(builder, spec.member, spec.expression)
    signature = _string_node(builder, spec.signature, "literal")
    key = [spec.loader, spec.class_name, spec.member, spec.signature]
    # A same-class decoy ensures target-table membership is checked rather than
    # every constructed identity being accepted by construction.
    decoy = [spec.loader, spec.class_name, spec.member + "$decoy", spec.signature]
    builder.probe(class_ref=class_name, method=member, loader=loader, signature=signature)
    builder.table([key, decoy])
    program = builder.finish()
    expected = [{"feasible": True, "outcomes": [{"kind": "target", "key": key}]}]
    return program, expected


def all_public() -> list[tuple[str, str, dict[str, Any], list[dict[str, Any]], PublicSpec]]:
    output = []
    # P001--P011 are the retained DroidBench manual projections.
    for index, spec in enumerate(SPECS[:11], start=1):
        program, expected = make_case(spec)
        label = f"manual public projection: {spec.app} {spec.operation}"
        output.append((f"P{index:03d}", label, program, expected, spec))

    # P012--P040 are generated from exact Java source after blob and gold checks.
    from .java_frontend import public_source_cases
    import json
    for extracted in public_source_cases():
        spec = PublicSpec(
            app=extracted.app,
            repository=extracted.repository,
            commit=extracted.commit,
            path=extracted.upstream_path,
            source_sha=extracted.source_sha,
            operation=extracted.kind,
            loader=extracted.loader,
            class_name=extracted.class_name,
            member=extracted.member,
            signature=extracted.signature,
            expression="javac AST",
            note="exact redistributed source; accepted event matched pinned gold inventory",
            extraction_mode="automatic javac AST extraction",
            local_path=extracted.local_path,
            source_line=extracted.line,
            source_column=extracted.column,
            class_expr_json=json.dumps(extracted.class_expr, sort_keys=True, separators=(",", ":")),
            member_expr_json=json.dumps(extracted.member_expr, sort_keys=True, separators=(",", ":")),
        )
        label = f"source-extracted public case: {spec.app} {spec.operation}"
        output.append((extracted.case, label, extracted.program, extracted.expected_rows, spec))
    if len(output) != 40 or [case for case, *_ in output] != [f"P{i:03d}" for i in range(1, 41)]:
        raise AssertionError("public case inventory")
    return output


def provenance_rows() -> list[dict[str, str]]:
    rows = []
    for case, _, _, _, spec in all_public():
        rows.append({
            "case": case,
            "app": spec.app,
            "repository": spec.repository,
            "commit": spec.commit,
            "path": spec.path,
            "source_sha": spec.source_sha,
            "operation": spec.operation,
            "modeled_loader": spec.loader,
            "modeled_class": spec.class_name,
            "modeled_member": spec.member,
            "modeled_signature": spec.signature,
            "expression": spec.expression,
            "extraction_mode": spec.extraction_mode,
            "redistributed_local_path": spec.local_path,
            "source_line": str(spec.source_line) if spec.source_line else "",
            "source_column": str(spec.source_column) if spec.source_column else "",
            "class_expr_json": spec.class_expr_json,
            "member_expr_json": spec.member_expr_json,
            "projection_note": spec.note or "finite identity/string projection only",
        })
    return rows
