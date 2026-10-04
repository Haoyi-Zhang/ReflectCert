#!/bin/sh
set -eu
export PYTHONDONTWRITEBYTECODE=1

clean_python_caches() {
    find . -type d -name '__pycache__' -prune -exec rm -rf {} +
    find . -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
}

scratch="$(mktemp -d)"
cleanup() {
    clean_python_caches
    rm -rf "$scratch"
}
clean_python_caches
trap cleanup EXIT HUP INT TERM

# The three independent read-heavy gates are safe to run concurrently: they share no output
# except read-only sources. Reproduction is the sole writer of results/reproduced. This keeps the
# one-command clean-extraction route within four CPU cores while preserving separate logs.
python reproduce.py --output results/reproduced --resume >"$scratch/reproduce.log" 2>&1 &
pid_reproduce=$!
python -m unittest discover -s tests -v >"$scratch/tests.log" 2>&1 &
pid_tests=$!
python verify_inputs.py >"$scratch/inputs.log" 2>&1 &
pid_inputs=$!

status=0
wait "$pid_reproduce" || status=1
wait "$pid_tests" || status=1
wait "$pid_inputs" || status=1
cat "$scratch/reproduce.log"
cat "$scratch/tests.log"
cat "$scratch/inputs.log"
if [ "$status" -ne 0 ]; then
    echo "one or more independent release stages failed" >&2
    exit 1
fi

python compare_results.py results/measured results/reproduced
python journal_analysis.py --measured results/reproduced --output results/journal-reproduced
python compare_journal.py results/journal results/journal-reproduced
clean_python_caches
python release_gate.py --artifact-root .
