# Trusted boundary

## Finite acceptance

The consumer independently supplies a finite source and its ordered target table. These define
the requested contract. Schema validation does not prove that the table covers a JVM classpath.
The trusted specification distinguishes external worlds from internal choices, four outcome
kinds, per-world sets, may sets, and robust possibility (forall external / exists internal).

Acceptance trusts Python, JSON parsing/serialization and primitive operations, shared schema
utilities, and the specific checker implementation. `rrc/checker.py`, `rrc/factor_checker.py`,
`rrc/dispatch_checker.py`, and `rrc/witness_checker.py` are separately implemented acceptance
paths. They do not invoke producer evaluation, diagram construction, lowering, or retention
helpers. The witness checker requires an already checked summary; it is not a checker for
arbitrary unvalidated summaries.

Production algorithms, generators, deletion orders, cached results, diagram heuristics, paper
tables, and client omission claims are not evidence of correctness by themselves. Structural
source equality is not a cryptographic attestation, and no release-hash mechanism is claimed.
Independence means implementation/dependency separation, not independent authorship or Coq proof.

## Optional Java bridge

The bridge additionally trusts javac parsing, the extractor, a related normal query-entry state,
non-null ASCII value premises, intended API/loader binding, and consistent query normalization.
A whitelist is not type attribution. Simplified signature tokens can merge distinct qualified
types, and enumeration markers do not represent actual returned member arrays. Additional
injectivity/coverage obligations are required to interpret tokens as concrete JVM members.

The bridge rejects known reference-equality, compound/state-merge, and API-shadow hazards.
Neither syntactic acceptance nor the existing controls prove whole-program reachability,
classpath completeness, arbitrary unsupported-feature detection, or Java/Android execution
preservation. Direct dispatch preserves finite action identity only. Arguments, effects,
initialization, access, exceptions, return values, and concurrency require separate obligations.

## Fault checks and resource limits

The seeded tests alter source fields, terminal values, direct-action leaves, and necessity
records. Tests also cover structural graph errors and checker dependency isolation. Malformed
witness-coordinate tests reject a Boolean identifier and a non-hashable coordinate.

The design is not a sandbox, a verified parser/runtime, or a general resource-exhaustion defense.
Schema, serialized-byte, and node limits are separate admission policies. The mathematical
existence result is conditional on a representation fitting those limits.

## Descriptive implementation inventory

`results/journal/trust-surface.csv` counts nonblank, non-comment source lines for the shared schema,
flat/factorized/direct/witness acceptance paths, untrusted producer/lowerer paths, and the optional
Java bridge. The shared schema plus four finite acceptance paths total 644 significant source
lines. This inventory is intended to make the partition inspectable; it is not a proof that the
code is correct, minimal, easy to review, or free of parser/runtime defects.
