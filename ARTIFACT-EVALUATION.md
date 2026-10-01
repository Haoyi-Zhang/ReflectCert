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
- online reference checks may be `not-run` in an offline environment, but structural reference checks remain mandatory.

## Badge-oriented checklist

- **Available:** source, tests, raw results, provenance, licenses, and paper are in one archive.
- **Functional:** the smoke and full workflows execute from a clean extraction without private paths.
- **Reusable:** schemas, TCB, limitations, extension points, negative controls, and machine-readable manifests are documented.
- **Reproduced:** deterministic outputs are compared structurally rather than by timing or PDF metadata.

## Resource expectations

The exact runtime depends on the host JVM, Python, filesystem, and CPU. The frozen run metadata are evidence about one environment, not a performance guarantee. The largest finite case enumerates 4,096 worlds and is intentionally retained as a boundary test.
