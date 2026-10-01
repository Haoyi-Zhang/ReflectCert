# Finite reflection contract and certificate schemas

## Source record

Each input JSON document is an object with `label` and `program`. Deterministic generated and
public-case records additionally contain `expected_rows`, an independently constructed truth table
used only by the campaign. The 24 boundary inputs deliberately do not embed their gold rows: an
independent closed-form oracle in `rrc/fixture_gold.py` imports neither the fixture builder nor any
producer/checker and is compared exactly during input verification, unit tests, and reproduction.
P012--P040 are
regenerated from exact Java-source frontend events; P001--P011 are labeled manual finite
projections. Source records are limited to 128 KiB
before parsing, duplicate JSON keys are rejected, and JSON booleans are distinguished
from integers.

A `program` has exactly six fields: `external`, `choices`, `nodes`, `feasible`, `table`,
and `sites`.

- `external` declares up to eight Boolean coordinates representing facts that an
  explanation may fix.
- `choices` declares up to four Boolean coordinates existentially quantified inside one
  external world.
- `nodes` is a topologically ordered typed expression DAG with at most 64 nodes.
- `feasible` identifies a Boolean node whose syntactic dependencies contain no internal
  choice coordinate.
- `table` contains up to 256 distinct four-string identities
  `(loader, class, member, signature)`.
- `sites` contains one to eight guarded lookups, each referencing four string nodes.

Names and literal strings are bounded ASCII. Expression operations are Boolean/string
literals, inputs, aliases, negation, conjunction, disjunction, equal-sort equality,
concatenation, and typed conditionals. This equality is an operator of the already-declared finite
DSL; it is not a translation of Java `String ==`, which the source bridge rejects. References must point backward. Static string
width is at most 48 bytes. Unsupported operations fail closed.

## Quantifier order

Let `h` range over external coordinates and `r` over internal choices. A world `h` is
feasible exactly when `F(h)` is true. For each site `s`, evaluating `(h,r)` yields one of
`infeasible`, `skipped`, `lookup_error(key)`, or `target(key)`. A world's target profile
contains every target reached by some internal choice:

```
Profile_s(h) = { t | exists r . outcome_s(h,r) = target(t) }.
```

`May_s` is the union over feasible worlds. `Robust_s` is the intersection over feasible
worlds and is represented as null when there are no feasible worlds. “Robust” therefore
means possible in every feasible external world, not inevitable on every execution.

## Flat reference certificate

The flat format stores the complete source, one row per assignment, all node values,
feasibility, outcomes, and the aggregate summary. It is retained as an independently
checked semantic baseline. It can exceed the 16 MiB JSON limit even for a syntactically
valid maximal-width source, so it is not the primary CLI format.

## Factorized certificate

A factorized certificate has exactly:

```
format, program, bit_order, diagram, roots, summary
```

`format` is `factorized-target-certificate`. `program` is a literal copy of the supplied
source. `bit_order` must equal external coordinates followed by internal choices.
`diagram.nodes` is a topologically serialized reduced ordered MTBDD shared by every
expression value, feasibility, and site outcome. Terminals are unique by canonical JSON
value. A branch has `(var, low, high)`, both children precede it, `low != high`, and any
branch child tests a strictly later variable. Duplicate branches and unreachable nodes
are rejected. `roots` contains one root per expression, one feasibility root, and one
outcome root per site.

The checker independently evaluates the source at every assignment and compares every
root value. It then reconstructs `summary` rather than trusting the producer's aggregate.
The maximum accepted serialized evidence document is 16 MiB and the diagram limit is
131,072 nodes.

## Certificate-guided direct dispatch

A direct-dispatch object has exactly:

```
format, program, bit_order, diagram, roots
```

Its format tag is `certificate-guided-direct-dispatch`. The source and bit order are bound in the
same way as the factorized certificate. Its shared ordered DAG has one root per site and terminal
actions `infeasible`, `skipped`, `lookup_error(key)`, or `invoke(target_index)`. The independent
dispatch checker validates source binding, topology, ordering, reduction, uniqueness, reachability
and action fields, then evaluates the source and replays every site action on every assignment.
`invoke(i)` is accepted only when source evaluation yields the table identity at index `i`. The
complete schema, finite preservation statement and Java pilot boundary are in `docs/dispatch.md`.

## Missing-target witness

A witness has exactly:

```
site, claimed_targets, target, base, selected, necessity
```

`target` must be in the exact may set but absent from the canonical `claimed_targets`.
`base` identifies a feasible world whose profile contains `target`. `selected` is a
sorted set of external coordinate indices. The retention predicate requires every
feasible world matching the base on `selected` to contain `target` at the selected site.
For each selected coordinate, `necessity` identifies a matching feasible world after
that coordinate is removed that does not contain the target. The checker validates the
universal retention predicate by scanning the complete world summary and checks every
necessity world.

## CLI evidence bundle

The CLI bundle has exactly:

```
format, factorized_certificate, direct_dispatch, missing_target_witnesses
```

Its format tag is `reflection-resolution-evidence`. Unknown fields are rejected. The checker first
validates the source-bound factorized certificate, then independently replays the direct-dispatch
object against the same source, and only then checks witnesses. The campaign's retained per-case
files contain the same three scientific objects; `reproduce.py` invokes the underlying checkers
directly and compares all deterministic bundles.


## Java-source frontend record

The producer-side frontend output uses format `rrc-java-front-v1`. Each file record carries
its parsed path, package, and ordered event list. An accepted event contains source offsets,
line/column, operation kind, loader literal, class and member expression ASTs, optional
constant values, and a normalized signature. A rejected event contains the same source
position, an operation kind, and an explicit reason. The expression AST uses the same
finite operators as the JSON source but refers to Boolean inputs by name until
`rrc/java_frontend.py` assigns deterministic external-coordinate indices. The complete
accepted grammar, relation, and rejection table are in `docs/frontend.md`.
