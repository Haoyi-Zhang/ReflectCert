# Proof arguments and counterexamples

These are mathematical arguments for the declared finite model, its restricted
source-to-model bridge, and its checked finite direct-dispatch lowering. They are not
proof-assistant developments and do not establish a whole-program Java semantics or a
general Java/Android invocation transformation.

## P0. Restricted frontend expression and event preservation

The accepted javac expression fragment is homomorphic on string and Boolean literals, Boolean
parameters, simple straight-line aliases, negation, conjunction, disjunction, **Boolean** equality,
string concatenation, and conditionals. Java `String ==`/`!=` is reference equality, so it has no
content-equality translation and is rejected. Compound assignments and values written through an
`if`, loop, or `switch` join also have no translation; the extractor invalidates the binding and
rejects any later reflection use instead of reusing a stale or last-scanned value.

Structural induction gives equal source-fragment and finite-DAG values for every Boolean
assignment. Literals and parameters are immediate; aliases substitute a previously accepted
binding; each remaining constructor applies the same typed operation to induction-hypothesis equal
operands. Unsupported syntax contributes no induction case.

Event identity has one additional premise. Fully qualified `java.lang.Class.forName` is
whitelisted. Simple `Class.forName` and unqualified or `this.getClassLoader()` are accepted only
when a pinned-source audit premise identifies the former as `java.lang.Class` and the latter as the
application loader; that premise is written into the event. Lexical shadows, arbitrary getters, and
custom loader variables are rejected. Under the recorded premise, loader and normalized signature
are literal-preserving, so each accepted event yields the same four-field identity in the source
fragment and generated finite site.

The executable evidence checks two accepted events over all four Boolean assignments, eight actual
runtime lookup identities, and 12 reflective/direct returns. Seven original exclusion controls and
one same-name nonreflection control test fail-closed classification. Four independent adversarial
Java programs add nine JVM executions and seven rejected reflection-looking events covering string
reference equality, compound assignment, `switch` state, shadowed `Class.forName`, and custom
loader getters.

This theorem is conditional on javac parsing, the stated syntax, and any recorded API-identity
premise. It does not establish classpath/table completeness, access checks, initialization,
invocation behavior, or a general Java rewrite theorem. Rejection by the bridge does not affect the
finite-backend theorems, which start from an already fixed finite source and target table.

## P1. Pointwise factorized-certificate exactness

For an admitted source, the checker first validates source equality, bit order, root
arity, DAG topology, reduction, ordering, uniqueness, and reachability. It then enumerates
every Boolean assignment in the fixed order. Its recursive evaluator computes the unique
value of each acyclic typed expression. For every expression root, the checker traverses
the submitted diagram under the same assignment and requires strict equality. It performs
the same comparison for feasibility and each site's complete outcome object.

Therefore, acceptance implies that every certified function equals the source semantics
at every modeled assignment. This argument does not depend on diagram reduction;
reduction is a format/canonicality condition that prevents gratuitous duplicates and dead
structure.

## P2. Exact aggregation

External bits precede internal choice bits, and feasibility cannot depend on internal
choices. Thus all assignments belonging to one external world form one fixed block and
share feasibility. For each feasible world and site, the checker inserts exactly the keys
whose independently evaluated outcomes are `target`. The resulting set equals the
existential profile over internal choices. Union and intersection over those reconstructed
profiles yield the exact may and robust sets. Equality with the submitted summary is
checked last. Hence an accepted certificate cannot establish aggregate completeness by
listing only positive examples.

## P3. Certificate existence and size boundary

Every finite source function has a complete truth table. Recursively splitting the table
in the fixed bit order yields an ordered multi-terminal decision tree; replacing equal
terminals and equal `(variable, low, high)` subgraphs yields a reduced DAG. Consequently,
an in-memory certificate exists for every valid finite source. This does not imply a
polynomial bound. Ordered decision diagrams can be exponential, and serialized evidence
must separately satisfy the node and byte admission limits.

A maximal-width constant-string source demonstrates why the flat format is not a universal
wire format. Counting only quoted 48-byte strings in 4,096 rows gives a lower bound of
19,456,000 bytes, exceeding the 16 MiB cap, while the shared factorized certificate is
456,563 bytes and checks all assignments. This is a representation separation for one
bounded family, not a worst-case compression theorem.

## P4. Missing-target retention soundness

Fix a feasible base world `b`, site `s`, possible target `t`, and selected external
coordinates `S`. The checker scans every feasible world `w` that agrees with `b` on `S`
and requires `t` in `Profile_s(w)`. Therefore acceptance directly implies the retention
predicate. Since `b` itself matches and contains `t`, the universal statement is not
vacuously true.

## P5. Necessity worlds imply subset-minimality

For every `i` in `S`, the certificate supplies a feasible world `w_i` that agrees with
`b` on `S \ {i}` but omits `t`. Therefore `S \ {i}` does not retain `t`. Retention is
monotone under adding fixed coordinates: if a set fails, every subset also fails because
it admits at least the same counterexample world. Since deleting each single member of
`S` fails, no strict subset of `S` can retain `t`. Thus `S` is inclusion-minimal.

This proof does not establish minimum cardinality. The producer's deletion order may
select any one of several incomparable minimal sets.

## P6. Greedy deletion terminates with a subset-minimal witness

The producer starts with all external coordinates, which retains any target present in
the base world. It removes a coordinate only when retention still holds. The set strictly
shrinks on every removal, so the process terminates. At termination, every remaining
coordinate failed a removal test in the current or a larger set. Monotonicity ensures the
recorded final necessity condition, and the producer materializes an explicit necessity
world for independent checking. Different deletion orders may terminate at different
minimal sets.

## P7. No unique least witness

Consider four external bits and a target retained exactly when `(h0 and h1) or (h2 and
h3)` is true, with an all-true base. `{0,1}` and `{2,3}` are both sufficient and
subset-minimal. Neither contains the other, and their intersection is insufficient.
There is no unique least witness under set inclusion. The generated family and exhaustive
oracle instantiate this counterexample.

## P7b. Greedy subset-minimality does not imply minimum cardinality

Use base `000` and let the target be absent exactly in worlds `101` and `110`. Relative to
the base, their difference edges are `{0,2}` and `{0,1}`. The inclusion-minimal hitting sets,
and therefore the inclusion-minimal retention sets, are exactly `{0}` and `{1,2}`. Forward
deletion order `0,1,2` first removes coordinate 0 and terminates at `{1,2}`. Reverse order
`2,1,0` removes 2 and then 1 and terminates at `{0}`. Both sets satisfy retention and have an
explicit necessity world for every retained coordinate, but their cardinalities differ. The
artifact enumerates every subset and checks both witnesses. Thus the greedy construction is
correct for inclusion minimality but makes no minimum-cardinality guarantee.

## P8. Changed execution is not changed target profile

Internal choices can produce different row-level outcomes while their existential union
within each external world is identical. Therefore observing two distinct assignments or
traces does not imply different target profiles. Explanations must be defined over the
checked semantic object of interest, not merely over execution inequality.

## P9. One-deletion minimality of a changed support is a different predicate

A support that changes one chosen row after every individual deletion can still contain a
strict subset that changes the aggregate profile once feasibility and existential internal
choice are considered. The exhaustive oracle records 2,432 such model/anchor/support
instances. This finite count corroborates the explicit counterexample; it is not the
proof of the distinction.

## P10. Public-source strata and Java non-claims

The public evidence has two distinct strata. P012--P040 are generated from 29 accepted events in
nine exact pinned Java files under the P0 syntax and recorded API-identity premises. P001--P011 are
explicit manual finite projections whose repository, commit, path, blob, and mapped operation give
provenance but no source-to-model theorem. Neither stratum proves target-table or classpath
completeness, Android behavior, or whole-application semantics. The finite checker validates only
the source it is given; P0 adds an event-identity relation only for accepted syntax and its stated
premises.
## P11. Finite direct-dispatch trace preservation

For a valid finite source and accepted factorized certificate, the untrusted transformer evaluates
each accepted outcome root on every assignment and replaces `target(key)` by `invoke(i)` where the
source table entry at `i` equals `key`; the other outcomes retain their exact action. The independent
dispatch checker does not import that evaluator or builder. It validates source binding, bit order,
ordered/reduced/reachable DAG structure and action well-formedness, then independently re-evaluates
the source on every assignment. At each site it requires the walked action to equal the source
outcome under the target-index encoding. Therefore acceptance implies equality of the complete
finite outcome trace for every assignment and site.

If execution receives a thunk table indexed by the same source-bound target table, exactly the
selected thunk is invoked at a target leaf and no thunk is invoked at an infeasible, skipped or
lookup-error leaf. This rules out the deliberately incorrect `invoke_all` transformation. The
finite statement does not establish equivalence of arbitrary Java callees; receiver and argument
evaluation, access, initialization, exceptions, side effects and return values are premises of any
whole-language lifting.

## P12. Bounded Java call pilot

The self-contained runtime pilot has two Boolean coordinates and one `getMethod`/`invoke` site with
a fixed zero-argument constructor and one-String-argument method convention. The artifact builds and
checks the finite dispatcher, renders a Java direct-call method from its accepted DAG, compiles both
versions, and compares them for all four coordinate assignments and three payload strings. The 12
return values agree. This is executable evidence for that concrete calling convention, not the
proof of P11 and not a general Java transformation theorem.

