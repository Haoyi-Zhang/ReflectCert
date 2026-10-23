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

The finite results are:

- 32,139 complete Boolean assignments;
- 14,279,992 flat-certificate bytes and 3,329,807 factorized-certificate bytes;
- deterministic gzip-9 totals of 855,047 flat bytes and 588,640 factorized bytes; under this codec 371 factorized objects are smaller, 292 larger, and one tied;
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
- the retained Linux/JDK run passes 96 unit-test methods without skips; the earlier
  68-test result remains a historical record. Current outputs are in `results/current/`.

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

## Import separately supplied client results

`python -B -m rrc.client_audit --source INPUT --certificate CERTIFICATE --claim CLAIM`
accepts a standalone factorized certificate and a separate finite client claim.
The claim has fields `format` (`reflection-client-claim`), `program` (the exact separately
supplied finite program), and `sites` (one sorted, duplicate-free list of four-string
target identities per site, including empty lists). The importer checks the certificate,
reports every omitted exact target and every claimed identity outside the exact finite set,
and independently checks a retention/minimality witness for each omission. Extra identities
remain in the report; the witness uses their exact-domain projection. These are finite-domain
comparisons, not JVM soundness verdicts. Exit codes are 0 for coverage, 1 for an omission,
and 2 for invalid inputs.

```sh
python -B -m unittest discover -s tests/client -v
python -O -B -m unittest discover -s tests/client -v
python -B client_handoff.py --output results/handoff-reproduced.json --compare results/client-handoff.json
```

The last command actually compiles and executes the owned `RuntimeFinite.java` pilot over
its four Boolean worlds. Its class/member outputs supply the client claims: after one,
two, three and four observed worlds, respectively, two, two, one and zero finite targets
remain unobserved. Repeating a world that supplies the same identity does not improve target
coverage. No target is deleted from the exact may set to construct these claims. This small
dynamic-observation handoff is separate from the original 913 constructed target/base pairs;
it is not an independent analyzer bug, a new public multi-configuration application, or a
representative reflection workload. The 40 public one-world cases and their expansions remain.

## Requirements

- Python 3.11 or newer, using only the standard library;
- a full JDK 17 or newer with `javac` and `java` (the extractor compiles with `--release 17`);
- a POSIX-like shell for the commands below.

No network, GPU, external solver, model API, Android SDK, device, service, or private input is
required. Exact reproduction compares scientific outputs, not interpreter/JDK version strings or
host timing.

The portable equality regression can be run separately:

```sh
python -B -m unittest discover -s tests -p test_strict_equal.py -v
```

Its six owned finite tests compare strict equality with the canonical-JSON definition,
including mixed types, subclasses, non-finite values and serialization errors. Exact
built-in Booleans and same-type ASCII strings use direct comparison; other values retain
canonical serialization. Non-ASCII strings stay on that path because an astral character
and its explicit surrogate pair can have the same JSON encoding. The tests also exercise
an owned source, independent expected rows, and certificate/dispatch/witness mutations.
They do not run Java or the complete campaign and establish no measured speedup.

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
lookup/direct-call probes, and checks the 66-entry bibliography audit. `reproduce.py` runs the complete finite campaign, frontend controls, Java probes, oracle,
fault controls, and bibliography check. It writes each completed case atomically; an interrupted
campaign may resume with:

```sh
python reproduce.py --output results/reproduced --resume
```

`compare_results.py` excludes host-dependent time and RSS but requires equality of deterministic
case/summary, bibliography, frontend, negative-control and oracle records, plus all 664 complete
evidence bundles. The retained uninterrupted measured run used 37.21 cumulative user+system CPU
seconds for the driver and completed Java children, 26.40 wall seconds, and 140,884 KiB maximum
resident set.

## Adaptive transport and same-information comparison

The optional transport accepts either complete certificate format, choosing by actual
gzip-9 frame length rather than assuming diagrams are smaller. The five-byte frame,
bounded decompression, and existing semantic checkers are specified in `docs/model.md`.
Assignment-local diagram reuse retains all root comparisons and source checks; it does
not skip assignments or trust production. The historical checker mode remains unchanged.

```sh
python -B -m unittest discover -s tests -p test_transport.py -v
python -B -m rrc.transport produce --source inputs/F06.json --wire results/f06.rrc
python -B -m rrc.transport check --source inputs/F06.json --wire results/f06.rrc
python -B transport_benchmark.py --output results/transport-reproduced.json --repeats 3
```

`transport_benchmark.py` uses the fixed 664 finite inputs and their retained expected
outcomes without running Java. It checks all 32,139 assignments and both traversal modes.
The task includes all expression values, feasibility, complete outcomes and aggregation;
outcome-only dispatch is not substituted for the richer certificate. Total bytes count
the separately supplied compact program once, the complete source-bound certificate,
and five framing bytes per case. Test gold, network protocol overhead and disk I/O are
excluded. Timings measure construction once per case and use three encode/receive
repetitions with rotated receiver order. Reported totals sum per-case medians plus actual
construction costs; they are stage-accounted local observations, not network latency.

The current token-builder observations on CPython 3.12.14 under Windows are in
`results/construction-resources/transport.json`:

| Complete evidence path | Total bytes | Receiver wall s | Accounted total wall s |
|---|---:|---:|---:|
| Flat JSON | 15,021,818 | 1.491 | 1.972 |
| Flat gzip | 1,596,873 | 1.500 | 2.324 |
| Factorized JSON | 4,071,633 | 1.907 | 3.439 |
| Factorized gzip | 1,330,466 | 1.924 | 3.495 |
| Factorized gzip, node reuse | 1,330,466 | 1.840 | 3.410 |
| Adaptive gzip, node reuse | 1,306,393 | 1.802 | 4.186 |

Adaptive selection uses flat for 293 cases and factorized for 371, including flat for all
40 public one-world cases. Its 567,887 wire bytes plus 738,506 separately supplied source
bytes save 18.2% against flat gzip total bytes, but its total wall observation is higher
because it builds both representations. Assignment-local reuse reduces fresh node
evaluations from 4,223,861 to 1,888,566, with unchanged source work. The small observed
timing difference is not a controlled or statistically established speedup; Windows
process CPU observations are coarse for small cases. Factorized public payloads still expand
after gzip, so adaptive transport selects flat evidence for them. Historical Windows transport
observations remain separately stored; this finite transport run executes no Java bridge.

## Token-vector construction and isolated resource comparison

`rrc/factor.py` canonicalizes each root-vector cell once and memoizes recursive
subvectors as construction-only integer tokens. It preserves the original terminal/branch
allocation order and complete certificate bytes; checkers and wire formats are unchanged.
Distinct token values are snapshotted, and eager vectors plus exponential memo storage remain.
The argument is in `docs/proofs.md` P1c.

```sh
python -B -m unittest discover -s tests -p test_factor_tokens.py -v
python -B factor_construction_benchmark.py --output results/factor-construction-reproduced.json --repeats 3
```

The benchmark compares the pre-token builder, current builder, and flat gzip with one
complete-evidence path live per process. It checks all 664 retained complete certificate and
direct-dispatch objects for byte identity, validates independent expected rows and all 32,139
assignments, replays 78,705 actions and checks 1,826 retained witnesses. The 6 construction tests
also enumerate every ternary value vector at widths 0--3, compare with recursive construction,
and cover strict canonical equality, caller mutation, nonzero starting variables and bounds.

The local summary is `results/factor-construction-20261014-summary.json`, and complete case/pass
records are retained in `results/construction-resources/construction.json.gz`.
A reproduction writes these full records to its fresh output. It uses CPython 3.12.14 on Windows and three rotated
fresh-process timing passes per path, plus one separate allocation-profiled pass. Pipeline stages
include input-record read/parse (including test gold where present), construction, source and
certificate serialization, gzip/framing, decoding and full acceptance with node reuse. Source
transfer excludes test gold. Stage totals exclude orchestration, process startup and network;
disk read is included. On Windows the raw `peak_rss_bytes` field records peak working set,
including interpreter/imports/native allocations; tracing starts after imports and measures Python
allocations. Allocation-profiled times are not used for speed comparisons.

| Complete path | Total bytes | Pipeline wall s | Pipeline CPU s | Peak working set MiB | Traced peak MiB |
|---|---:|---:|---:|---:|---:|
| Flat gzip | 1,596,873 | 2.445 | 2.422 | 52.42 | 23.19 |
| Factor gzip, string memo | 1,330,466 | 4.768 | 4.766 | 59.63 | 28.33 |
| Factor gzip, token memo | 1,330,466 | 3.540 | 3.500 | 43.45 | 14.24 |

Construction-only canonical calls fall from 2,375,230 to 1,244,215, and encoded characters
from 19,069,997 to 8,425,746. Construction wall totals are 2.684 and 1.490 s; source/certificate
serialization plus gzip totals are 0.106 and 0.103 s. Per-case median construction time increases
in 9 cases and complete-path time in 21. Token construction still uses more total CPU than
flat gzip. These are bounded single-host observations, not guaranteed savings or new Java/native
analyzer validation. The 4.29 raw and 1.45 gzip representation ratios, all public-case expansions,
and historical Linux/Windows records are retained separately. The current adaptive measurements
above use the token builder and their own accounting protocol. Host metadata and the memory-field
interpretation are in `results/construction-resources/environment.json`.

## Inspect the Java-source bridge

The repository's `.github/workflows/scientific-checks.yml` runs a fresh
scientific check on pushes or manual dispatch on Ubuntu with Python 3.12 and
Temurin 21. It copies the artifact repository into an isolated `RUNNER_TEMP` work area, runs the full
unit suite, input and bibliography checks, and regenerates all 664 bundles without
`--resume`. It retains generated results and each stage's stdout/stderr as a
workflow artifact, including available partial outputs on failure, with a
30-minute job timeout.
The entire scientific stage sequence shares a 20-minute timeout, with TERM followed
by KILL after at most 30 seconds and a 22-minute step guard. Logs are initialized
before tool setup; the combined raw experiment output and actual pipeline exit
codes are retained along with stage logs. The upload step uses `always()` so an
ordinary experiment failure or internal timeout does not skip available evidence.
It checks the standalone artifact bibliography; manuscript bibliography
alignment and PDF compilation remain part of paper integration.

After the campaign comparison, its journal commands use a fresh results subdirectory:

```sh
python journal_analysis.py --measured results/reproduced --output results/journal-reproduced
python compare_journal.py results/journal results/journal-reproduced --current-source-surface
```

`--current-source-surface` validates both the new JSON and CSV source counts
against `journal_analysis.trust_surface()` on the current checkout. It reports
these descriptive counts separately from the retained baseline and still compares
all other deterministic journal outcomes. Without that option the original exact
source-count comparison remains in force. Frozen campaign/journal records are
not rewritten to claim a post-repair run. The manuscript surface table describes
current source counts; it is not a new Java validation result.

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

The verifier requires at least 55 complete scholarly or normative records, unique keys and DOI values, and an
exact one-to-one match with the audit and literature inventories. The paper build additionally
checks all 66 manuscript citation keys and byte equality with the canonical standalone copy.

## Repository map

- `rrc/`: finite semantics, producers, independent checkers, direct dispatch, baselines, oracle,
  witnesses, and Java-to-finite bridge;
- `frontend/`: javac extractor, audited inventory, positive/negative controls, and runtime pilots;
- `third_party/droidra-reflection-sources/`: nine exact upstream Java files and LGPL 2.1 notice;
- `inputs/`: 24 fixtures, 600 generated inputs, and 40 pinned-source cases;
- `tests/`: mutation, independent fixture gold, bibliography, frontend, runtime,
  bridge-risk, block-scope, journal-comparison, and direct-dispatch controls; discover
  the current inventory with `python -m unittest discover -s tests -v`;
- `results/measured/`: frozen measured records and 664 checked evidence bundles;
- `docs/model.md`, `docs/proofs.md`, `docs/frontend.md`, and `docs/dispatch.md`: schema,
  arguments, source bridge, and dispatch contract;
- `docs/public-provenance.csv`: per-case repository, commit, path, blob, extraction mode, and
  source position;
- `docs/references.bib`, `docs/bibliography-audit.csv`, and `docs/literature.csv`: canonical
  bibliography and metadata/provenance inventory;
- `claim_evidence_ledger.csv` and `external_resources.csv`: claim and resource traceability.

## Trust boundary and admission bounds

The finite source validator, flat/factorized/dispatch/witness acceptance implementations, and
Python runtime form the finite trust boundary. The witness checker requires an already accepted
complete summary. Certificate/direct-dispatch/witness producers, case generator, and client claim
are not trusted as evidence of finite semantics. The Java parser/extractor and any recorded pinned-source API-identity premises form an additional
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

`sh run_release_gate.sh` is the validated clean route. It performs unit tests, input verification, full reproduction, journal recomputation, comparisons, cache cleanup, and structural release checks. The final structural step writes `results/release-audit.json`. See `ARTIFACT-EVALUATION.md`, `EXPERIMENT-DESIGN-AUDIT.md`, `TRUSTED-COMPUTING-BASE.md`, and `REPRODUCIBILITY.md` before interpreting a passing result.

## Journal analysis and source boundaries

This artifact accompanies the ACM TOSEM-oriented named manuscript. The original 664 finite
programs and their certificate/dispatch/witness results are preserved. All 40 public cases remain
explicitly split into 29 automatic events and 11 manual projections; there is no claim that all
are automatic or that these are large applications.

Run the additional deterministic analyses after reproducing the main campaign:

```sh
python journal_analysis.py --measured results/reproduced --output results/journal-reproduced
python compare_journal.py results/journal results/journal-reproduced --current-source-surface
```

This checks 6,654 target-presence tables separately from the inherited 7,186 complete-label
tables. It also compiles and runs two additional Java controls, checks four rejected events,
computes cross-root node accounting, reports per-stratum and post-hoc sensitivity results,
compares exact compact JSON with deterministic gzip-9 transport, inventories the implementation
trust surface, and summarizes retained per-stage CPU observations. The journal output contains 15 machine-readable files. All deterministic fields are compared exactly; retained per-stage CPU values are host observations, so comparison checks the six-stage inventory and 664-case denominator rather than requiring identical timings.
These analyses add no cases to the main population and perform no tuning, random-sample inference,
external analyzer comparison, or human study.

`rrc/witness_checker.py` is a separate acceptance implementation, importing only trusted syntax
utilities. The producer's retention predicate is not in this acceptance path. The bridge now
invalidates writes in conditional expressions, short-circuit operands, and exception-state joins,
and detects lexical `java` namespace shadowing. Casts are not erased to obtain accepted values.
Theorem 1 relates string contents through an abstraction, under entry-state and API/normalization
premises. Simplified type tokens and enumeration markers do not prove JVM member resolution.

Read `docs/journal-method.md`, `docs/frontend.md`, and `TRUSTED-COMPUTING-BASE.md` before treating
an accepted finite object as evidence about a concrete program. The publication checklist is
separate from executable scientific validation; no author approval or submission is asserted.

## Manuscript diagrams

The model and protocol schematics are drawn directly in Python as vector PDFs
with embedded STIX fonts. They encode the stated relationships, not measured
performance. To regenerate them with Python 3.9+ and Matplotlib:

```sh
python -B figures/draw_schematics.py --output figures
```
