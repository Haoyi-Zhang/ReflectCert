# Restricted Java-source frontend

## Purpose and boundary

`frontend/JavaReflectionExtractor.java` is a producer-side bridge from a deliberately restricted
Java source fragment to the finite certificate language. It uses the public javac tree API without
type attribution or an Android classpath. The bridge is fail-closed: a syntactically identified
reflection-looking operation is either emitted with finite expressions and any required API-identity
premise, or emitted as a rejection with a stable reason. A rejection is not interpreted as an empty
or complete target set.

The bridge does **not** establish whole-program Java or Android reflection completeness. It does
not model heap-built strings, arbitrary statement control flow, native code, custom class loaders,
exceptions, initialization, access checks, overload resolution, invocation effects, or classpath
construction. Accepted events establish only the finite lookup identity expression at the recorded
source location under the syntax and identity premises below.

## Accepted source fragment

The default API whitelist recognizes fully qualified `java.lang.Class.forName(name)`. For exact
pinned sources, two optional audit policies may additionally accept:

- simple `Class.forName(name)`, provided an external audit establishes that `Class` resolves to
  `java.lang.Class` and no lexical `Class` shadow is declared; and
- unqualified or `this.getClassLoader().loadClass(name)`, provided an external audit establishes
  that the getter denotes the application loader and no source method shadows `getClassLoader`.

These premises are written into every accepted event. An arbitrary object getter, a custom loader
variable, a shadowed `Class.forName`, or a source-defined `getClassLoader` is rejected. After an
accepted class lookup, the bridge recognizes `Class.newInstance`, `getConstructor`,
`getConstructors`, `getMethod`, `getDeclaredMethod`, `getMethods`, `getDeclaredMethods`,
`getField`, `getDeclaredField`, `getFields`, and `getDeclaredFields` when their arguments remain in
the fragment.

Finite string expressions are literals, simple straight-line local aliases, `+`, `String.concat`,
and `condition ? left : right`. Conditions are Boolean literals, Boolean method parameters,
straight-line Boolean aliases, `!`, `&&`, `||`, and primitive-boolean `==`/`!=`. Java `String ==` and `!=`
are reference comparisons and are **not** translated to finite content equality. A recognized use is
rejected as `unsupported_string_reference_equality`.

Only local declarations and simple `=` bindings are modeled. Compound assignments such as `+=`,
`&=`, and `|=` invalidate the affected binding. A binding written in an `if`, loop, or `switch`
is invalidated before a later reflection use because this bridge does not model the join. Dynamic
parameter-type expressions are rejected; accepted signatures use syntactic class literals or an
explicit empty class array. javac may fold constant string expressions in its parse tree, so
`"setIme" + "i"` may be emitted as the literal `"setImei"`; this is compiler-AST normalization,
not a post-hoc value guess.

## Fail-closed controls

| Pattern | Required result |
|---|---|
| `StringBuilder` / heap-built class name | `unsupported_class_name_expression` |
| unrestricted `String` parameter as a class name | `unsupported_class_name_expression` |
| Java string reference equality in a reflection guard | `unsupported_string_reference_equality` |
| `+=` or Boolean compound assignment feeding reflection | `unsupported_compound_assignment` |
| binding written by branch/loop state merge | `unsupported_control_state_merge` |
| binding written by `switch`/switch expression | `unsupported_switch_state_merge` |
| custom loader variable | `unsupported_loader_receiver` |
| arbitrary/custom loader getter | `unaudited_loader_getter` or `shadowed_application_loader_getter` |
| shadowed simple `Class.forName` | `shadowed_class_api_receiver` |
| unaudited simple `Class.forName` | `unaudited_class_api_receiver` |
| class value not created by an accepted lookup | `unresolved_class_receiver` |
| dynamic parameter-type expression | `unsupported_parameter_type_expression` |
| reflection expression inside unsupported statement control | `unsupported_control_context` |
| ordinary same-named method on a nonreflection receiver | no reflection event |

The extractor scans unsupported branches only to locate reflection-looking operations and stable
rejection reasons. It never lets a last-scanned branch become the binding after the join. This is
why `switch`, compound assignment, and control-flow writes are invalidated rather than approximated.

## Source-to-model relation

Let `rho` map accepted Boolean method parameters to external coordinates. Define `J[e]_rho` for an
accepted javac expression and `F[T(e)]_rho` for the generated finite DAG node:

- a string or Boolean literal translates to the same literal;
- a Boolean parameter translates to its named external coordinate;
- a straight-line alias translates to its previously accepted binding;
- `!`, `&&`, `||`, primitive-boolean equality, string concatenation, and conditional expressions translate
  homomorphically to `not`, `and`, `or`, `eq`, `cat`, and `ite`;
- loader and normalized signature are finite literals, under any recorded API-identity premise.

**Expression preservation.** For every accepted expression `e` and Boolean assignment `rho`,
`J[e]_rho = F[T(e)]_rho`. The proof is structural induction. String reference equality, compound
assignment, and statement-control joins are outside the grammar, so they provide no induction case
and cause rejection.

**Event preservation.** For an accepted event with loader `l`, class expression `c`, member
expression `m`, signature `s`, and satisfied recorded identity premises, finite evaluation yields
exactly `(l, J[c]_rho, J[m]_rho, s)`. The API premise is separate from the expression induction: it
identifies which source declaration the syntactic call denotes.

Combining event preservation with factorized-certificate exactness gives a conditional lifting
statement: if the supplied target table is the intended finite table for an accepted event, an
accepted certificate reports exactly its table-membership outcome for every frontend assignment.
The finite backend theorems do not depend on this bridge and are not weakened by a source rejection.
The result still does not prove complete JVM classpath coverage or arbitrary Java receiver,
argument, exception, initialization, and heap behavior.

## Executable frontend evidence

### Pinned public sources

Nine unmodified Java files from `serval-snt-uni-lu/DroidRA` at commit
`b766a32a23178a54d095fb0a473e6ec77aad2166` are redistributed under their upstream LGPL 2.1
terms. Before extraction, the artifact recomputes each Git blob SHA-1. `frontend/public-gold.json`
locks event order, source position, operation, expression, target identity, and the audit premise
used for simple `Class` or application-loader syntax.

The run checks nine blob identities and 29 accepted events. All 29 match the inventory and no event
in the pinned sources is rejected. P012--P040 are built from extracted records; the gold file is
never used as program input. P001--P011 remain explicitly labeled manual DroidBench projections.

### Finite expression and Java runtime pilots

`SupportedFinite.java` exercises two Boolean coordinates, aliases, concatenation, and conditional
class/member names. Its two events are checked over all four assignments, for eight event-assignment
checks. `RuntimeFinite.java` then executes actual `Class.forName` and `Class.getMethod` calls in the
same four worlds and matches eight runtime identities. `RuntimeInvoke.java` compares one reflective
method invocation with generated direct Java calls for four worlds and three payloads, giving 12
matching returns under the pilot's explicit calling convention.

### Independent bridge-risk executions

Four additional Java programs are compiled and executed independently of the finite producer:

- `ReferenceEqualityRisk.java` runs twice and prints reference equality `false`, content equality
  `true`, and the reference-inequality branch for dynamically concatenated strings;
- `CompoundAssignmentRisk.java` runs all four Boolean inputs and demonstrates the effects of
  string `+=` and Boolean compound assignment;
- `SwitchBindingRisk.java` runs both inputs and demonstrates the value used after `switch`; and
- `ApiIdentityRisk.java` executes a shadowed `Class.forName`, a source-defined
  `this.getClassLoader`, and an arbitrary holder getter.

The nine JVM executions must match their frozen outputs, and the extractor must reject all seven
reflection-looking events with the reasons above. These are actual runtime checks of the hazards,
not claims that rejected syntax has been modeled.

### Original rejection and false-positive controls

Seven negative source files verify heap/input names, custom loader variables, unresolved class
receivers, dynamic parameter types, unsupported statement control, and control-flow reassignment.
`UnrelatedMethods.java` contains ordinary same-named methods and emits no event. The original
control inventory has ten source files; the four bridge-risk programs are a separate adversarial
inventory.

## Trust boundary

The Java parser, extractor, source bytes, and any recorded API-identity audit premise are part of
the frontend trust boundary. The finite producer remains untrusted. `rrc/factor_checker.py` and
`rrc/dispatch_checker.py` independently validate the generated finite objects, but neither
validates javac, Java name resolution, or the source-to-model theorem. The static gold inventory
detects source/extractor drift and records premises; it is not used to construct finite programs.
