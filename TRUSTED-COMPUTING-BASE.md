# Trusted Computing Base and Adversary Model

## Security goal

A consumer must not use a reflection target profile, missing-target explanation, or direct-dispatch action merely because the producer emitted it. The consumer accepts it only after the corresponding checker validates the artifact against the source-bound finite semantics.

## Trusted components

1. The finite-language semantic specification and the declared class/member table.
2. The independent checker implementation for the artifact being consumed.
3. The parser/serialization layer, integer/string primitives, Python runtime, operating system, and cryptographic hash implementation used by the release gate.
4. For source-derived cases, javac parsing/type-tree behavior and the explicit frontend acceptance predicate.

The producer, reduction heuristics, deletion order used for witnesses, benchmark generator, cached results, and paper tables are **not** trusted.

## Attacker capabilities exercised by tests

- modify source-binding hashes or identifiers;
- redirect a decision edge or alter a shared terminal;
- change a dispatch leaf while retaining a syntactically valid object;
- delete a necessity witness or substitute a non-matching world;
- inject malformed, unreachable, unordered, duplicate, or cyclic graph records;
- change public-source provenance, blob hashes, reflection-log expectations, or result summaries;
- introduce a checker-to-producer import dependency.

## Non-goals

The design is not a sandbox for malicious native code, a proof of the host language/runtime, a verifier for the completeness of a whole Java classpath, or a defense against a compromised compiler/OS. Resource-exhaustion limits are interface policy and are checked separately from semantic validity.
