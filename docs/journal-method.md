# Journal investigation contract

## Four research questions

RQ1 asks what exact finite result and action selection a consumer can accept without trusting
production. RQ2 measures representation tradeoffs and separates per-root reduction from global
sharing. RQ3 characterizes retention, minimality, candidate selection, and record multiplicity.
RQ4 connects the finite model to a conditional Java-source interpretation and executable controls.

The source grammar, table, width limits, fixed 664 inputs, and public provenance are retained.
The field `public_source_apps=13` is not a count of 40 independent applications. Nine redistributed
DroidRA files supply 29 automatic events; eleven projections come from four further public apps.

## Oracle meanings

The 7,186-table oracle preserves a complete label at a base and compares every deletion order.
Its changed-support results are not minimum-cardinality retention evidence.

`target_presence_oracle.py` instead enumerates all ternary maps (infeasible, absent, present) at
widths 0--3: 6,654 tables, 17,611 target-present bases, and 35,222 forward/reverse records.
The expected minimal family is fixed by direct subset enumeration, checked by a separate
transversal construction, and then used to check the production witnesses. There are 6,768
base/table pairs with multiple minima and 1,152 with different-cardinality minima. These bounded
checks have zero mismatches. They are not mechanized general proofs or extra application cases.

## Witness workload

Each synthetic client claim is Q = exact May minus t. Use all target/base candidates when at most
two are available; otherwise use the canonical first and last. Prefer differing forward/reverse
selected sets, then larger resulting sets, then lexicographically greatest target, then smaller
base index. Keep both orders. This is diagnostic stress selection, not random sampling.

The original counts remain 1,826 records, 913 selected site/target/base pairs, 1,259 canonical
within-case distinct records, and 567 repeats. Public cases give 80 records but 40 distinct empty
witnesses. Record counts must not be relabeled analyzer defects or independent observations.

## Representation and sensitivity

`journal_analysis.py` reads the existing checked bundles. Separate full-tree node slots are
derived as roots * (2^(width+1)-1); per-root reduced counts sum reachable-node cardinalities;
global sharing takes their union. Totals are 2,470,187 / 47,973 / 29,056. The additional cross-root
reduction is 18,917 nodes (39.43%). These are not serialized flat JSON node counts or runtimes.

On raw compact JSON, all 40 one-world public cases expand. The boundary group has 22 expansions
and two improvements; the generated group has 91 expansions and 509 improvements. A deterministic
gzip-9 baseline (`mtime=0`) applies the same codec to both exact JSON objects. The aggregate
flat/factorized ratio falls from 4.29 to 1.45; 371 factorized objects are smaller, 292 larger, and
one ties, with a 1.03 median ratio. All public cases still expand. This comparison isolates some
repeated-syntax savings but is codec-specific and does not change the checked semantics.

Sensitivity removes F24, trims six observations from each raw-ratio tail, and leaves out each
frozen generated family. It is explicitly post hoc and descriptive, with no retuning, p-values,
application-population inference, or claim that generator bias has disappeared. The trust-surface
inventory counts significant source lines, and stage-cost summaries reuse retained CPU observations;
neither is a correctness metric or cross-tool performance comparison.

## Additional source controls

Two self-contained programs run in two JVM processes and emit seven expected lines. The
extractor rejects four events for conditional/short-circuit state merges, exception-state merge,
and qualified-name shadowing. These supplement, not replace, the inherited four risk sources,
nine JVM runs, and seven rejected events. Runtime processes, output lines, source files, and
events are different denominators.
