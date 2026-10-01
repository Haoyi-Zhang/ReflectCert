# Reflection-resolution certificates

This standalone artifact implements a bounded proof-carrying reflection-resolution study. It
contains a finite source language, a flat reference certificate, a shared reduced ordered MTBDD
certificate, independently implemented certificate and direct-dispatch checkers,
analyzer-relative missing-target witnesses, a restricted fail-closed Java-source bridge, exact
public inputs, tests, measured results, and an offline bibliography audit.

The contract is deliberately narrower than a production Java analyzer. A checker receives the
finite source separately from an untrusted certificate, validates its DAG and every modeled
assignment, and reconstructs exact per-world, may-target, and robust-target summaries. An
untrusted lowerer turns accepted outcomes into a Boolean direct-dispatch DAG whose leaves select
one table entry or a non-invocation outcome; another checker independently replays the complete
finite action trace. A separate witness checker validates that an omitted exact target survives
every matching feasible world and that every retained external coordinate is necessary.

## Established results

The frozen campaign contains exactly 664 cases:

| Population | Cases | Role |
|---|---:|---|
| Boundary fixtures | 24 | Semantics, counterexamples, stress, and an independent closed-form row oracle |
| Deterministic generated programs | 600 | Structured aliases, conditionals, choices, and lookups |
| Manual pinned-source projections | 11 | DroidBench operations whose source is not redistributed here |
| Java-source-extracted cases | 29 | Events extracted from nine exact DroidRA Java files |

The final measured results are:

- 32,139 complete Boolean assignments;
- 14,279,992 flat-certificate bytes and 3,329,807 factorized-certificate bytes;
- 1,389,323 direct-dispatch bytes, 11,019 total dispatch nodes, and 66 nodes at maximum;
- 78,705 independently replayed site actions: 49,891 invocations, 3,019 lookup errors,
  9,362 skipped sites, and 16,433 infeasible sites;
- 1,826 checked witness records for 913 selected target/base pairs; within-case canonical
  deduplication leaves 1,259 distinct records and 567 duplicates, with 3,555 selected coordinates,
  maximum width five, and 346 forward/reverse alternative pairs;
- 511 cases smaller and 153 larger under factorization; median flat/factorized ratio 1.794,
  geometric mean 1.959, and maximum 27.324;
- 1,105 additional string-set targets and 3,976 additional constant-only targets, with no exact
  finite target dropped;
- 7,186 exhaustive oracle tables, 36,992 feasible anchors, 213,952 deletion orders, and zero
  disagreement with the independent characterization;
- five seeded certificate/dispatch/witness faults rejected, plus an invoke-all counterexample;
- 60 unit-test methods passing.

The Java bridge adds bounded source evidence:

- nine redistributed Java files match their pinned Git blob SHA-1 identities;
- 29 accepted reflection events match an audited source-position and normalized-expression
  inventory that is not used to construct the finite programs;
- a self-contained Java runtime probe checks `Class.forName` and `getMethod` identities over four
  Boolean worlds (eight class/member comparisons);
- a generated direct-call method and the reflective method return the same result for four worlds
  and three payloads (12 invocation comparisons);
- seven original unsupported-source controls fail closed, while one ordinary class whose methods
  merely have reflection-like names emits no event;
- four adversarial Java sources execute in nine JVM runs and expose string reference equality,
  compound/switch state updates, and shadowed/custom API identity; all seven implicated
  reflection-looking events are rejected.

These are bounded results. They do not prove that the finite table covers a JVM classpath, that
arbitrary Java/Android reflection is handled, or that direct-call replacement generally preserves
receiver/argument evaluation, initialization, access, exceptions, side effects, and returns.

## Requirements

- Python 3.11 or newer, using only the standard library;
- a full JDK 17 or newer with `javac` and `java` (the extractor compiles with `--release 17`);
- a POSIX-like shell for the commands below.

No network, GPU, external solver, model API, Android SDK, device, service, or private input is
required. Exact reproduction compares scientific outputs, not interpreter/JDK version strings or
host timing.

## Reproduce the complete campaign

Run from this repository root with a fresh output directory:

```sh
export PYTHONDONTWRITEBYTECODE=1
python -m unittest discover -s tests -v
python verify_inputs.py
python reproduce.py --output results/reproduced
python compare_results.py results/measured results/reproduced
```

`verify_inputs.py` reconstructs all 664 inputs, compares all 24 boundary fixtures against a
closed-form oracle that imports neither the fixture builder nor producer/checker code, reruns the
Java frontend and bridge-risk programs, verifies source blobs and public provenance, runs the
lookup/direct-call probes, and checks the 59-entry bibliography audit. `reproduce.py` runs the complete finite campaign, frontend controls, Java probes, oracle,
fault controls, and bibliography check. It writes each completed case atomically; an interrupted
campaign may resume with:

```sh
python reproduce.py --output results/reproduced --resume
```

`compare_results.py` excludes host-dependent time and RSS but requires equality of deterministic
case/summary, bibliography, frontend, negative-control and oracle records, plus all 664 complete
evidence bundles. The retained uninterrupted measured run used 36.30 cumulative user+system CPU
seconds for the driver and completed Java children, 26.12 wall seconds, and 140,912 KiB maximum
resident set.

## Inspect the Java-source bridge

The extractor parses source with the public javac tree API and requires no Android classpath:

```sh
tmpdir="$(mktemp -d)"
javac --release 17 -encoding UTF-8 -d "$tmpdir" frontend/JavaReflectionExtractor.java
java -cp "$tmpdir" JavaReflectionExtractor \
  third_party/droidra-reflection-sources/Reflection7/MainActivity.java
rm -rf "$tmpdir"
```

The JSON report lists accepted and rejected events with source locations and normalized finite
expressions. The accepted grammar, rejection reasons, source relation, and Java-level lifting
boundary are specified in `docs/frontend.md`. The audit inventory detects drift; it does not feed
target identities into the source-to-model construction.

## Produce and check one evidence bundle

The finite CLI consumes an already constructed bounded input record:

```sh
export PYTHONDONTWRITEBYTECODE=1
python -m rrc produce \
  --source inputs/F06.json \
  --output results/f06-evidence.json \
  --base 0 --site 0 --target-number 0

python -m rrc check \
  --source inputs/F06.json \
  --evidence results/f06-evidence.json
```

The bundle contains a factorized certificate, a direct-dispatch DAG, and zero or more omission
witnesses. The producer and lowerer are not trusted. `check` independently validates source
equality, bit order, DAG topology, ordering, reduction, uniqueness, reachability, every source
expression/outcome, reconstructed summaries, every dispatch action, and every witness.

## Verify the bibliography independently of LaTeX

```sh
python verify_bibliography.py \
  --bib docs/references.bib \
  --audit docs/bibliography-audit.csv \
  --literature docs/literature.csv
```

The verifier requires at least 55 complete scholarly records, unique keys and DOI values, and an
exact one-to-one match with the audit and literature inventories. The paper build additionally
checks all 59 manuscript citation keys and byte equality with the canonical standalone copy.

## Repository map

- `rrc/`: finite semantics, producers, independent checkers, direct dispatch, baselines, oracle,
  witnesses, and Java-to-finite bridge;
- `frontend/`: javac extractor, audited inventory, positive/negative controls, and runtime pilots;
- `third_party/droidra-reflection-sources/`: nine exact upstream Java files and LGPL 2.1 notice;
- `inputs/`: 24 fixtures, 600 generated inputs, and 40 pinned-source cases;
- `tests/`: 60 unit-test methods, including mutation, independent fixture gold, bibliography, frontend, runtime, bridge-risk, and direct-dispatch controls;
- `results/measured/`: frozen measured records and 664 checked evidence bundles;
- `docs/model.md`, `docs/proofs.md`, `docs/frontend.md`, and `docs/dispatch.md`: schema,
  arguments, source bridge, and dispatch contract;
- `docs/public-provenance.csv`: per-case repository, commit, path, blob, extraction mode, and
  source position;
- `docs/references.bib`, `docs/bibliography-audit.csv`, and `docs/literature.csv`: canonical
  bibliography and metadata/provenance inventory;
- `claim_evidence_ledger.csv` and `external_resources.csv`: claim and resource traceability.

## Trust boundary and admission bounds

The finite source validator and two independent checkers, Python runtime, javac/JVM, and host are
trusted. Certificate/direct-dispatch/witness producers, case generator, analyzer claim, and public
mapping are not. The Java parser/extractor and any recorded pinned-source API-identity premises form an additional
frontend boundary; the finite checkers do not validate general Java typing, source name resolution,
or classpath coverage.

The finite language admits at most eight external bits, four internal-choice bits, 64 expression
nodes, eight sites, 256 four-string target identities, and 48-byte ASCII strings. Source records
are capped at 128 KiB, evidence at 16 MiB, and decision DAGs at 131,072 nodes. The checkers
enumerate every admitted assignment. These limits define the theorem scope rather than tunable
performance defaults.

## Scope boundaries

The artifact does not model heap-built names, arbitrary loops/callbacks, native code, encrypted or
network-delivered names, custom loaders, access control, class initialization, general exceptions,
overload resolution, arbitrary invocation effects, Android lifecycle semantics, or whole-program
Java rewrite equivalence. Source constructs outside the declared fragment are rejected rather
than approximated.

The 29 automatic public cases establish extraction and event-identity evidence only. Their finite
tables include extracted identities and explicit decoys; they do not establish classpath
completeness or application-scale precision. The 11 DroidBench cases remain marked manual
projections.

## License

Original artifact code and documentation are distributed under the MIT license in `LICENSE`.
Exact DroidRA source files under `third_party/` retain their upstream LGPL 2.1 terms and notices;
review that directory before redistribution or modification.

## Release gate

`python release_gate.py --artifact-root .` performs structural, provenance, checker-independence, bibliography-inventory (when the paper is adjacent), result, and packaging checks and writes `results/release-audit.json`. See `ARTIFACT-EVALUATION.md`, `EXPERIMENT-DESIGN-AUDIT.md`, `TRUSTED-COMPUTING-BASE.md`, and `REPRODUCIBILITY.md` before interpreting a passing result.
