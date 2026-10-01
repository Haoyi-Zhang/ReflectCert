#!/bin/sh
set -eu
export PYTHONDONTWRITEBYTECODE=1
python -m unittest discover -s tests -v
python verify_inputs.py
python reproduce.py --output results/reproduced --resume
python compare_results.py results/measured results/reproduced
python release_gate.py --artifact-root .
