# Restricted Java-source frontend

## Purpose and boundary

`frontend/JavaReflectionExtractor.java` is a producer-side bridge from a deliberately restricted
Java source fragment to the finite certificate language. It uses the public javac tree API to
parse source without type attribution or an Android classpath. The bridge is fail-closed: a
syntactically confirmed reflection operation is either emitted with finite expressions or emitted
as a rejection with a stable reason. Ordinary methods merely named `getMethod`, `loadClass`,
`getField` or `newInstance` are ignored unless the receiver is syntactically known as a
`Class<?>` or `ClassLoader` value.

The bridge does **not** establish whole-program Java or Android reflection completeness. It does
not model heap-built strings, callbacks, native code, custom class loaders, statement-level path
conditions, exceptions, initialization, access checks, overload resolution, invocation effects or
classpath construction. Accepted events establish only the lookup identity expression at the
source location under the relation below.

## Accepted source fragment

The extractor recognizes these operations when their receiver and arguments are accepted:

- `Class.forName(name)`;
- `this.getClassLoader().loadClass(name)` and equivalent direct `getClassLoader()` syntax;
- `Class.newInstance()` on a class value created by an accepted class lookup;
- `getConstructor`, `getConstructors`;
- `getMethod`, `getDeclaredMethod`, `getMethods`, `getDeclaredMethods`;
- `getField`, `getDeclaredField`, `getFields`, `getDeclaredFields`.

Finite string expressions are literals, straight-line local aliases, `+`, `String.concat`, and
`condition ? left : right`. Conditions are Boolean literals, Boolean method parameters,
straight-line aliases, `!`, `&&`, `||` and equal-sort equality. Parameter-type signatures contain
only syntactic class literals, including an explicitly empty class array. The frontend records
loader identity, class expression, member expression, normalized signature, source offsets, line
and column.

javac may fold Java constant string expressions while constructing the parse tree. A source
expression such as `"setIme" + "i"` may therefore be emitted as the literal `"setImei"`; this is
compiler-AST normalization, not a post-hoc value guess.

## Fail-closed and nonreflection controls

| Control | Required result |
|---|---|
| `StringBuilder` / heap-built class name | `unsupported_class_name_expression` |
| unrestricted `String` parameter used as a class name | `unsupported_class_name_expression` |
| custom loader receiver | `unsupported_loader_receiver` |
| class value not created by an accepted lookup | `unresolved_class_receiver` |
| dynamic parameter-type expression | `unsupported_parameter_type_expression` |
| reflection inside statement-level branch/loop | `unsupported_control_context` |
| class-name local reassigned under control flow | `unsupported_class_name_expression` |
| ordinary same-named methods on non-Class receivers | no reflection events |

A reflection expression in an unsupported control context is not promoted to an unconditional
site. Bindings assigned inside a branch or loop are invalidated before a later site. This keeps
source control flow outside the theorem instead of approximating it unsoundly.

## Source-to-model relation

Let `rho` map accepted Boolean method parameters to external coordinates. Define `J[e]_rho` for
the accepted javac expression tree and `F[T(e)]_rho` for the generated finite DAG node:

- a string or Boolean literal translates to the same literal;
- a Boolean parameter translates to its named external coordinate;
- aliases translate to their previously accepted binding;
- `!`, `&&`, `||`, equal-sort `==`, concatenation and conditional expressions translate
  homomorphically to `not`, `and`, `or`, `eq`, `cat` and `ite`;
- loader and normalized signature are finite string literals.

**Expression preservation.** For every accepted expression `e` and every Boolean assignment
`rho`, `J[e]_rho = F[T(e)]_rho`.

The proof is structural induction on the accepted expression. Literals and parameters are
immediate. Each inductive case applies the same typed operation to induction-hypothesis equal
operands. Straight-line aliases are substituted by their previously accepted binding. Unsupported
constructs have no translation and therefore cannot falsify the claim.

**Event preservation.** For an accepted source event with loader `l`, class expression `c`, member
expression `m` and signature `s`, evaluation of the generated finite site at `rho` yields exactly
`(l, J[c]_rho, J[m]_rho, s)`. This follows from expression preservation for `c` and `m` and literal
equality for `l` and `s`.

Combining event preservation with factorized-certificate exactness yields a conditional lifting
statement: if the supplied finite target table is the intended table for an accepted event, an
accepted certificate reports exactly the table-membership outcome for every frontend assignment.
The checked direct-dispatch lowering then preserves the finite outcome trace and selected table
index. This still does not prove that the table is a complete JVM classpath or that arbitrary Java
receiver, argument, exception, initialization and heap behavior is preserved.

## Executable frontend evidence

### Pinned public sources

Nine unmodified Java files from `serval-snt-uni-lu/DroidRA` at commit
`b766a32a23178a54d095fb0a473e6ec77aad2166` are redistributed under their upstream LGPL 2.1
terms in `third_party/droidra-reflection-sources/`. Before extraction, the artifact recomputes each
Git blob SHA-1. `frontend/public-gold.json` locks event order, source position, operation, loader,
normalized expression and target identity.

The run checks nine blob identities and 29 accepted events. All 29 events match the inventory and
no event in the pinned sources is rejected. P012--P040 are built from the extracted expression
records; the gold file is never used as program input. P001--P011 remain labeled manual
DroidBench projections because those source bytes are not redistributed in this package.

### Finite expression pilot

`SupportedFinite.java` exercises two Boolean coordinates, local aliases, concatenation, a
conditional class name and a conditional member name. Its two accepted events are translated and
checked over all four assignments each, for eight event-assignment checks.

### Actual Java reflection probe

`RuntimeFinite.java` is self-contained. For each of four Boolean worlds, the artifact compiles and
executes the class, performs actual `Class.forName` and `Class.getMethod` calls, and compares the
runtime-resolved class and member with the two extracted finite identities. All eight class/member
identity comparisons match; the method parameter is also checked as `java.lang.String`.

### Direct-call runtime pilot

`RuntimeInvoke.java` extends the identity probe with one reflective method invocation. The artifact
builds the factorized certificate and checked direct-dispatch DAG, renders a Java method containing
only Boolean branches and concrete constructor/method calls, and compiles that method beside the
reflective implementation. For each of four Boolean worlds and three payload strings, both versions
return the same value, giving 12 checked invocation results. The renderer deliberately accepts only
the pilot's default-loader, zero-argument-constructor and one-String-argument convention. The general
finite trace theorem is in `docs/dispatch.md`; this executable check is not a whole-Java rewrite
theorem.

### Rejection and false-positive controls

Seven negative source files verify the stable rejection reasons in the table above.
`UnrelatedMethods.java` contains ordinary same-named methods and must emit an empty event list.
The current control inventory therefore contains ten source files: one positive finite pilot, one
runtime source used for identity and direct-call probes, seven rejection controls and one
nonreflection control.

## Trust boundary

The Java parser, extractor implementation, source bytes and source-to-model assumptions are part
of the frontend trust boundary. The finite certificate producer remains untrusted.
`rrc/factor_checker.py` independently validates every generated finite assignment, and
`rrc/dispatch_checker.py` independently validates every lowered action; neither validates javac,
Java typing or the frontend theorem. The static gold inventory detects source/extractor drift but
is not used to construct finite programs.
