# Reproducibility Contract

A run is reproducible when reconstructed inputs, source provenance, certificate/dispatch/witness
objects, and deterministic summaries match the frozen records. Wall time, CPU time, RSS,
filesystem ordering, PDF timestamps, and temporary compiler paths are not equality keys.

## Levels

1. **Smoke:** unit tests, input verification, and one fixture through producer and checker.
2. **Deterministic replay:** all frozen inputs through the independent checkers.
3. **Full regeneration:** regenerate every bundle and compare it with `results/measured`.
4. **Journal analysis:** recompute stratum, sharing, sensitivity, generic-compression,
   trust-surface, and retained stage-cost reports.
5. **Paper audit:** rebuild both PDF views and verify references, fonts, warnings, numerical claims,
   and rendered-page integrity.

The validated one-command artifact route is:

```sh
sh run_release_gate.sh
```

The wrapper sets `PYTHONDONTWRITEBYTECODE=1`, removes only Python bytecode caches before and after
execution, runs 68 unit tests, verifies all inputs, reproduces and compares the 664 evidence
bundles, recomputes all journal analyses, compares every deterministic field, checks the six-stage timing
inventory without requiring host-identical CPU values, and finally runs the structural release gate. Cache cleanup prevents a successful test run from making a later package-hygiene check fail.

To inspect the stages separately:

```sh
export PYTHONDONTWRITEBYTECODE=1
python -m unittest discover -s tests -v
python verify_inputs.py
python reproduce.py --output results/reproduced
python compare_results.py results/measured results/reproduced
python journal_analysis.py --measured results/reproduced --output results/journal-reproduced
python compare_journal.py results/journal results/journal-reproduced
python release_gate.py --artifact-root .
```

An interrupted campaign may resume with `reproduce.py --resume`. The additional target-presence
oracle and Java controls remain separate from the 664-case population. Deterministic gzip uses
level 9 and `mtime=0` over the exact compact JSON objects; decompression recovers the same checked
JSON, but no claim is made for other codecs or network envelopes. Source-line counts are descriptive
review-surface measurements, not assurance metrics. Retained stage timings are single-host
observations and are not compared with external tools.

The Dockerfile is only a convenience recipe. No container engine is available in the validated
execution environment, so no Docker image build or container-portability claim is part of the
measured evidence. Local clean-extraction commands are the verified route.
