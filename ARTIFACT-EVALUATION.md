# Artifact Evaluation Guide

## Claims supported by the artifact

The artifact supports four independently checkable claims: exact finite target-profile checking; factorized transport with complete finite-world checking; inclusion-minimal missing-target witnesses; and checked direct-dispatch traces. It also contains a bounded javac-tree source bridge and provenance-locked public microbenchmarks.

## Recommended evaluation sequence

```bash
export PYTHONDONTWRITEBYTECODE=1
python -m unittest discover -s tests -v
python verify_inputs.py
python reproduce.py --output results/reproduced
python compare_results.py results/measured results/reproduced
python journal_analysis.py --measured results/reproduced --output results/journal-reproduced
python compare_journal.py results/journal results/journal-reproduced
python release_gate.py --artifact-root .
```

For an interrupted full run, repeat `reproduce.py` with `--resume`. Deterministic comparison intentionally ignores wall-clock time and peak memory.

## Expected evidence

- the unit suite ends in `OK`;
- input reconstruction reports no drift;
- the result comparator reports all certificate bundles matched;
- the release gate writes `results/release-audit.json` with `overall_status: pass`;
- public-source reconstruction reports the declared split exactly: 29 source-extracted cases and 11 explicitly labeled manual finite projections;
- no manual case is relabeled as automatic, and every automatic case carries pinned source, blob, location, expression, and audit-premise fields;
- online reference checks may be `not-run` in an offline environment, but structural reference checks remain mandatory;
- `results/journal/transport-summary.json` reports 855,047 gzip flat bytes, 588,640 gzip factorized bytes, and the 371/292/1 smaller/larger/tied split;
- `results/journal/trust-surface.csv` and `stage-costs.csv` are descriptive inventories and must not be interpreted as proofs or cross-tool speed comparisons.

## Artifact properties (no badge awarded)

- **Available:** source, tests, raw results, provenance, licenses, and paper are in one archive.
- **Functional:** the smoke and full workflows execute from a clean extraction without private paths.
- **Reusable:** schemas, TCB, limitations, extension points, negative controls, and machine-readable validation reports are documented.
- **Reproduced:** deterministic outputs are compared structurally rather than by timing or PDF metadata.

## Resource expectations

The exact runtime depends on the host JVM, Python, filesystem, and CPU. The frozen run metadata are evidence about one environment, not a performance guarantee. The largest finite case enumerates 4,096 full external/internal assignments and is intentionally retained as a boundary test.

The 68 tests and both comparison commands assess executable consistency. Mechanical acceptance
does not certify author approval, current portal-rule confirmation, external archiving, or peer review.
