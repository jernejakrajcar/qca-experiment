#!/bin/sh
# Repeat all experiments (E1-E4) and draw the figures.
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

# E4: centre cell (id 8) of the published majority gate
for T in 1K 10K; do
    echo "== e4-published-$T"
    python3 scripts/run_sweep.py --engine COHERENCE_VECTOR \
        --options "experiments/sim-options/coherence-$T.txt" \
        --base experiments/published-majority-use.qca --cells 8 \
        --out "experiments/results/e4-published-$T.csv"
done

python3 scripts/plot_tolerance.py
python3 scripts/plot_circuit.py
python3 scripts/compare_published.py
