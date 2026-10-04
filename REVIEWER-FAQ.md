# Reviewer FAQ

## Is the work only a new reflection resolver?

No. The bounded resolver is intentionally simple. The research object is a source-bound, independently checkable interface that carries complete finite target profiles, direct-dispatch actions, and minimal missing-target explanations. The paper limits the claim to that interface.

## Why not compare wall-clock time with SOLAR, Ripple, DroidRA, or TamiFlex?

Those systems infer targets in different languages, environments, and program corpora and do not emit the same certificate. A raw runtime ranking would conflate frontend coverage, classpath construction, analysis precision, and the new validation layer. The submission instead compares supported reflection features and guarantees, and uses reproducible correlation-discarding baselines for the finite model. This is a limitation, not a claim of superiority.

## Why use synthetic programs?

They systematically cover the bounded language and make exhaustive oracle comparison possible. They are reported in a separate stratum. Pinned public Java sources, upstream logs, and JVM executions address source realism, but the work still does not claim population representativeness.

## Is the checker truly independent?

The checker modules do not import producer, generator, lowerer, or witness-construction modules; a static dependency test enforces this. Independence is not absolute: parsers, serialization, the language specification, Python/JVM, and the operating system remain trusted and are listed explicitly.

## Does “minimal” mean smallest?

It means inclusion-minimal. The artifact proves sufficiency and supplies a necessity world for every retained coordinate. It also contains examples with multiple incomparable witnesses and separates cardinality optimality from the implemented guarantee.

## Does direct dispatch preserve arbitrary Java behavior?

No such theorem is claimed. The checker proves equality of finite action identities. JVM probes cover a declared calling convention; broader observational equivalence requires additional assumptions and evidence.

## Are 66 reference records present merely to satisfy a count?

The release gate requires every entry to be cited, rejects duplicate DOI values and missing keys, and emits structural and online metadata audits. The human authors must still verify that every citation supports the sentence in which it appears.

## Does generic compression explain the reported size reduction?

Partly. On exact compact JSON the aggregate flat/factorized ratio is 4.29, but deterministic
gzip-9 reduces it to 1.45; only 371 of 664 factorized objects remain smaller, 292 are larger, and
one ties. The manuscript reports both regimes. The certificate's semantic benefit is structured,
source-bound sharing with independently checked roots, not a claim that it always beats an
ordinary compressor or every wire envelope.

## Is the checker demonstrably small or fast?

The artifact publishes descriptive source-line counts for the shared schema, four checker paths,
producers/lowerers, and optional Java bridge, plus retained per-stage CPU observations. These
numbers improve auditability but are not assurance measures or cross-tool benchmarks. The finite
checker still exhaustively enumerates assignments and remains exponential in declared width.
