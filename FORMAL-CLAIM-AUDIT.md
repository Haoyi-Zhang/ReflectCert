# Formal-Claim Audit

This document separates mathematical statements, executable validation, and assumptions. The implementation is not presented as a mechanically verified proof assistant development.

## Semantic domain

For a source-bound instance `I`, let `W(I)` be its finite set of Boolean worlds. Evaluation produces, for every site and world, exactly one profile: infeasible, skipped, lookup error, or an ordered finite target identity. Aggregates such as may-target and robust-target sets are functions of these profiles, not additional analyzer guesses.

## Certificate theorem

**Statement.** If the certificate checker accepts `(I, C)`, every root represented by `C` evaluates to the independently recomputed finite semantics for every world in `W(I)`, and the certified aggregate target sets equal the aggregates of those profiles.

**Proof obligations checked by code.** Source binding; variable order; node well-formedness; acyclicity/topological order; reduction constraints; terminal uniqueness; root reachability; per-world expression and lookup equality; aggregate recomputation.

**Assumptions.** Correct finite-language specification, declared class/member table, parser/runtime, and checker implementation. Acceptance does not prove that the finite instance is a complete abstraction of an arbitrary Java program.

## Witness theorem

For a baseline world `w`, target `t`, and retained coordinate set `S`, the checker validates:

1. every feasible world agreeing with `w` on `S` retains `t`; and
2. for each `s` in `S`, a feasible necessity world agrees on `S \ {s}` but does not retain `t`.

**Consequence.** `S` is sufficient and no strict subset obtained by removing any retained coordinate is sufficient; by monotonicity of agreement constraints, `S` is inclusion-minimal.

**Not implied.** Uniqueness or minimum cardinality. One explicit table has incomparable
single-coordinate minima; another has minima `{0}` and `{1,2}`, and the two checked deletion
orders return the different cardinalities. These counterexamples are preserved as first-class
results.

## Direct-dispatch theorem

**Statement.** If the dispatch checker accepts `(I, C, D)`, evaluation of `D` in every finite world yields the same action identity—invoke target, lookup error, skipped, or infeasible—as the checked profile in `C`.

**Assumptions.** The action identity is the semantic boundary. General Java observational equivalence additionally requires receiver, arguments, initialization, access control, exceptions, return values, heap effects, concurrency, and framework behavior to be related. The runtime probes validate only their explicit calling convention.

## Decision-diagram properties

For a fixed coordinate order, reduction and unique-table sharing preserve the represented total functions. The node ablation distinguishes full trees, per-root reduction, and cross-root sharing. The artifact does not claim an optimal variable order, minimum byte serialization, or a new decision-diagram canonicity theorem.

## Complexity

Complete finite-world checking is exponential in the number of environment coordinates and polynomial in the source and graph size per world. This cost is intentional for bounded, independently checkable certificates. Factorization reduces transport and repeated structure; it does not remove worst-case finite enumeration from the checker.

## Independence boundary

Producer algorithms, deletion orders, graph reduction heuristics, cached results, and paper tables are outside the trusted base. Static dependency tests prevent checker modules from importing producer/generator/lowerer implementations. Shared language/runtime primitives remain an explicit TCB item.
