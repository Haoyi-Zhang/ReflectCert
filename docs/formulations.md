# Formulation comparison and lock decision

Eight materially different formulations were attacked before the current question was locked.

| Formulation | Guarantee | Mechanism | Decisive falsifier/evidence | Decision |
|---|---|---|---|---|
| Constant-only targets | Sound coarse overapproximation | Constant propagation with top expansion | 3,976 extra finite identities | Baseline only |
| Independent string sets | Sound fieldwise overapproximation | Union-based finite value sets | 1,105 extra identities from lost correlations | Baseline only |
| Complete flat certificate | Exact finite semantics | One record per assignment | A legal stress family needs at least 19,456,000 quoted-string bytes, beyond the 16 MiB interface | Retained semantic baseline |
| Shared MTBDD certificate | Exact finite semantics with sharing | One reduced ordered multi-terminal DAG for all certified functions | 511 cases shrink and 153 expand; worst case remains exponential | Selected representation contribution |
| Per-target membership proofs | Each listed target is possible | One witness assignment per target | Cannot exclude an unreported target | Rejected as completeness evidence |
| Unique least missing-dependency slice | Canonical explanation | Intersection/least-set conjecture | Two incomparable minimal witnesses and 13,696 exhaustive multi-minimum bases | Refuted |
| Subset-minimal retention witness | Every matching world retains the omitted target and every fixed fact is necessary | Greedy deletion plus one necessity world per retained coordinate | 1,826 checked witnesses and exhaustive hitting-set agreement | Selected explanation contribution |
| Certificate-guided direct dispatch | Exact finite target/non-invocation action trace | Lower accepted outcomes to an ordered Boolean action DAG and independently replay every assignment | 78,705 accepted events, five seeded faults rejected, invoke-all counterexample, and 12 bounded Java return matches | Selected bounded transformation; general Java lifting excluded |

The locked result is intentionally bounded: a source-bound exact finite target-profile
certificate, checked outcome-only direct dispatch, and independently checkable subset-minimal
missing-target retention witnesses. The project does not claim a new decision-diagram algorithm,
a new general explanation theory, classpath completeness, or a whole-program Java rewrite theorem.
Its proposed novelty is the reflection-resolution acceptance contract, the separation of complete
target evidence from analyzer-relative omission evidence, and the measured positive and negative
boundaries of factorization and finite lowering.

The lock remains an internal research judgment rather than independent peer review. The strongest
remaining threat is that reviewers may view the interface as an incremental composition of
proof-carrying validation, decision diagrams, and established explanation methods. The paper
therefore states those ancestors and the Java/application lifting obligations directly.
