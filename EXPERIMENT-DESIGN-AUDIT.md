# Experiment design audit

The primary unit is one admitted finite source. The fixed 664 cases consist of 24 boundary,
600 generated, 11 manual public, and 29 automatic public events. Assignments and site actions
are nested within cases and are not independent application samples.

The expectation layers are distinct: a separate closed-form oracle defines 4,149 boundary rows;
compact field/guard specifications define generated expectations; manual public operations have
provenance; automatic events have source blobs and a separate gold inventory. The complete-label
and target-presence oracles check different predicates. See `docs/journal-method.md` for all
counts and generation/selection rules.

The two local abstraction baselines test loss of correlation, not competitiveness against SOLAR,
Ripple, DroidRA, Seneca, DLCDroid, or a solver implementation. No external analyzer defects are
measured. The witness workload deliberately deletes a target and prefers diagnostic complexity.
Both deletion orders and duplicate records remain in the raw evidence.

Representation is measured in two transport regimes. Raw values are exact compact UTF-8 JSON
bytes. A deterministic gzip-9 baseline (`mtime=0`) measures how much of the raw advantage a
standard compressor also captures. Every expansion and the single compressed tie are retained.
The result is codec-specific: it does not imply a universal compressed-wire advantage. Node sharing
is a structural accounting analysis of the same functions, not a runtime ablation of other
libraries. Per-stage CPU summaries reuse the retained single-host measurements and are descriptive,
not comparative benchmarks.

Post-hoc deterministic sensitivity checks disclose their selections and make no population
inference. There is no learned model, but corpus construction, operation selection, one-assignment
public cases, and fixed variable order create real design bias. Generated/public/boundary strata,
negative results, leave-one-family-out checks, and the generic-compression baseline reduce but do
not eliminate that bias.

The complete main reproduction and separate journal-analysis commands must both be run.
Scientific comparisons exclude only the explicitly environment-sensitive main timing fields;
all journal outputs except the explicitly host-sensitive stage-cost values are compared exactly.
The stage inventory and case count are compared, while its CPU values remain retained observations. Unsupported constructions
remain visible as negative controls. Current journal rules and human author approvals are not
established by passing executable tests.
