# Proof arguments and counterexamples

These are mathematical arguments for the declared finite model, its restricted
source-to-model bridge, and its checked finite direct-dispatch lowering. They are not
proof-assistant developments and do not establish a whole-program Java semantics or a
general Java/Android invocation transformation.

## P0. Restricted frontend expression and event preservation

For the accepted javac expression fragment, translation is homomorphic on literals, Boolean
parameters, straight-line aliases, negation, conjunction, disjunction, equal-sort equality,
concatenation and conditionals. Structural induction gives equal source-fragment and finite-DAG
values for every Boolean assignment. Loader and normalized signature are literal-preserving.
Therefore each accepted event yields the same four-field identity in the source fragment and
generated finite site. Unsupported names, loaders, receivers, parameter types and statement-level
control contexts have no translation and are emitted as explicit rejections. Syntactic receiver
typing prevents ordinary same-named methods from being treated as reflection. The detailed grammar
and assumptions are in `docs/frontend.md`.

The executable evidence checks two accepted events over all four Boolean assignments, executes
actual self-contained Java `Class.forName`/`getMethod` lookups over those four assignments, and
checks seven fail-closed plus one same-name negative control. These finite checks attack the
implementation; the theorem itself remains the structural argument above.

This theorem is conditional on javac parsing and the stated syntactic fragment. It does not
establish classpath/table completeness, access checks, initialization, invocation behavior or a
general Java rewrite theorem. The separate direct-dispatch result below starts only after a finite
source and target table have been fixed.

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

## P10. Public projections and Java non-claims

A source file path, immutable commit, blob identifier, and manually mapped operation show
where a finite identity originated. They do not prove that the mapping is complete or
semantics-preserving for Java. No theorem above lifts through an unspecified frontend.
Such a theorem would require a concrete translation relation and coverage assumptions for
class loading, lookup, heap/string behavior, control flow, and failures. The current
checker can only validate the finite source it is given.
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

