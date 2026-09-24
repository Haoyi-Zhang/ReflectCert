# Certificate-guided finite direct dispatch

## Purpose

After a factorized certificate has been accepted, `rrc/dispatch.py` lowers each finite lookup
site into a shared ordered Boolean decision DAG. Its leaves contain only one of four actions:

- `infeasible`;
- `skipped`;
- `lookup_error(key)`;
- `invoke(target_index)`.

The resulting object contains no reflective name construction and performs no target-table search
at execution time. `target_index` refers to the source-bound table stored in the object. The
transformer is untrusted; `rrc/dispatch_checker.py` independently validates the submitted object
against the original finite source over every admitted assignment.

## Schema

A direct-dispatch object has exactly:

```
format, program, bit_order, diagram, roots
```

`format` is `certificate-guided-direct-dispatch`. `program` must equal the independently supplied
source and `bit_order` must be external coordinates followed by internal choices. The diagram is a
topologically serialized reduced ordered DAG shared by all sites. A terminal contains exactly one
action. A branch contains `(var, low, high)`; children precede the branch, differ, and any branch
child tests a later coordinate. Duplicate actions, duplicate branches, dead nodes, malformed
lookup-error keys, and out-of-range target indices are rejected.

## Independent replay obligation

For every Boolean assignment, the checker evaluates the finite source without importing the
transformer, factorized-certificate evaluator, or DAG builder. For each site it computes the
expected finite outcome and compares it with the action obtained by walking the submitted dispatch
root. A target outcome with identity `program.table[i]` must be represented as `invoke(i)`; the
other three outcomes must retain their exact kind and, for a lookup error, its exact key.

Consequently, acceptance establishes complete finite outcome-trace equality. If the source yields
a target at a site, the dispatcher selects exactly one matching target-table entry. If the source
yields no invocation, the dispatcher preserves the corresponding infeasible, skipped, or
lookup-error event. The execution helper invokes at most the selected thunk for each site; it does
not invoke all may targets.

## Conditional call-level statement

The finite theorem identifies *which* target operation is selected. It does not by itself model
receivers, arguments, return values, exceptions, initialization, access control, or heap effects.
Call-level observational equivalence follows only when the thunk at each target-table index is
itself observationally equivalent to the corresponding reflective lookup and invocation under the
same surrounding state. Establishing that premise for arbitrary Java or Android programs remains
outside this artifact.

The artifact nevertheless includes a narrow executable sanity check. It parses one self-contained
Java source with two Boolean coordinates, builds and checks its dispatcher, renders a direct Java
method from the accepted DAG, and compares the direct method with actual reflection for all four
worlds and three payload strings. All 12 return-value comparisons must match. This pilot validates
one calling convention; it is not a whole-Java transformation theorem.

## Evidence and controls

The 664-case campaign retains one checked dispatch object per case. Across the frozen corpus the
checker replays every site outcome for every assignment, including target, lookup-error, skipped,
and infeasible leaves. Negative controls mutate source binding and terminal actions and submit
unreduced or unreachable nodes. A separate deliberately incorrect `invoke_all` baseline shows why
replacing a reflective site by calls to every may target does not preserve a per-assignment trace.

The CLI bundles the factorized certificate, direct-dispatch object, and any missing-target
witnesses. Checking is staged: the factorized certificate is accepted first, the dispatch object is
then replayed independently against the same source, and only then are omission witnesses checked.
