#!/bin/sh
# Repeat all experiments (E1-E3) and draw the figures.
# Run inside the qca-sim Docker image from the repository root:
#   docker run --rm -v "$PWD":/repo qca-sim sh scripts/run_all.sh
set -e

sweep() {
    echo "== $3"
    python3 scripts/run_sweep.py --engine "$1" \
        --options "experiments/sim-options/$2.txt" \
        --out "experiments/results/$3.csv"
}

sweep BISTABLE                bistable      e1-bistable
sweep COHERENCE_VECTOR        coherence-1K  e2-coherence-1K
sweep COHERENCE_VECTOR        coherence-10K e2-coherence-10K
sweep COHERENCE_VECTOR_ENERGY energy-1K     e3-energy-1K

python3 scripts/plot_tolerance.py
python3 scripts/plot_circuit.py
