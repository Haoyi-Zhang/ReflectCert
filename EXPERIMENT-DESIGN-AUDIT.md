# Experiment-Design Audit

## Unit of analysis

The primary unit is one bounded reflection-resolution instance. Each instance declares its Boolean environment coordinates, string expressions, class/member table, sites, and complete finite-world semantics. Per-case metrics are retained before aggregation; a certificate bundle is not split into pseudo-independent observations.

## Strata

Results are reported separately for boundary fixtures, deterministic generated programs, and pinned public-source programs. Synthetic generation exercises combinations in the declared language; it is not evidence about real-world prevalence. Public-source cases establish that the source bridge handles concrete reflection idioms; they are not a population sample of Java or Android applications.

## Research questions and estimands

1. **Checkability:** Does the independent checker accept valid bundles and reject targeted semantic/structural corruption? Estimand: complete pass/reject counts over the frozen corpus and mutation suite.
2. **Representation:** Under the fixed declared variable order, how many bytes and decision nodes are used by flat, per-root-reduced, and globally shared representations? Estimands: per-case ratios, distribution summaries, and counts where sharing loses.
3. **Explanations:** Are returned missing-target witnesses sufficient and inclusion-minimal? Estimand: exhaustive agreement with a separate oracle on bounded models, plus necessity-world checks.
4. **Consumption:** Does the checked direct-dispatch trace equal the finite reflective action trace? Estimand: event-by-event equality over every finite world, plus JVM probes under the stated calling convention.
5. **Source bridge:** Do javac-tree events agree with pinned source, upstream reflection logs where available, and local JVM execution? Estimand: event identity and rejection-reason counts.

## Baselines

The string-set and constant-propagation baselines are deliberately small and reproducible. They answer how much precision is lost when correlation is discarded, not whether this prototype outperforms every production analyzer. Nearest reflection systems solve different end-to-end problems and do not emit the same source-bound certificate interface; the paper therefore compares guarantees and interfaces rather than manufacturing an incompatible runtime race.

## Statistical treatment

The finite semantic outputs are deterministic and exhaustively checked within each instance. The artifact reports full counts, medians, geometric means where ratios are meaningful, tails, and negative cases. It does not attach p-values or confidence intervals to a fixed, non-random corpus. Runtime and RSS are descriptive host measurements and are excluded from deterministic equality.

## Exclusions and stopping rules

- Unsupported Java constructs fail closed with stable reasons and remain visible as negative controls.
- No case is removed because factorization loses or a witness is non-unique.
- A full regeneration completes all frozen cases; resume checkpoints are operational, not an adaptive stopping rule.
- The corpus size and generators are fixed in the input manifests before the reported run.

## Reproducibility controls

- pinned source revisions and blob hashes;
- deterministic input reconstruction;
- multiple Python hash seeds;
- clean-extraction full regeneration;
- structural comparison of bundles rather than timestamps;
- repeated PDF text/render comparison;
- machine-readable claim, code, reference, venue, and visual audits.

## Residual validity threats

The corpus is bounded and microbenchmark-heavy; the frontend is a declared Java subset; the class table is supplied; exact finite enumeration is exponential in environment bits; variable ordering is fixed rather than optimized; and the JVM probes do not cover initialization, access-control, exception, concurrency, or Android lifecycle equivalence. These limitations constrain the claims and are not corrected by a larger synthetic sample.
