# Reproducibility Contract

A run is reproducible when the reconstructed inputs, source provenance, certificate/dispatch/witness objects, and deterministic summaries match the frozen records. Wall time, CPU time, RSS, filesystem ordering, PDF timestamps, and temporary compiler paths are not equality keys.

## Levels

1. **Smoke:** unit tests, input verification, one fixture through producer and checker.
2. **Deterministic replay:** all frozen inputs through the independent checkers.
3. **Full regeneration:** regenerate every bundle and compare to `results/measured`.
4. **Paper audit:** rebuild the PDF, verify page contract, references, fonts, warnings, and numerical claims.

`release_gate.py` automates structural checks. The full experiment remains a separate command so that a gate cannot silently substitute cached data for regeneration.
