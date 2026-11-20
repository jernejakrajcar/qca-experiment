# Okolje za simulacije: QCADesigner-E batch_sim s popravki (tools/batch_sim.patch),
# Python in matplotlib. Na Apple Silicon teče prek emulacije x86-64.
#   docker build -t qca-sim -f tools/Dockerfile tools
#   docker run --rm -v "$PWD":/repo qca-sim python3 scripts/run_sweep.py ...
FROM --platform=linux/amd64 ubuntu:24.04
RUN apt-get update && apt-get install -y --no-install-recommends \
        git ca-certificates python3 python3-matplotlib \
        gcc libc6-dev pkg-config libglib2.0-dev patch \
    && rm -rf /var/lib/apt/lists/*
ARG QCAD_COMMIT=3bc90302bddacebfff838c74fb91cc56500387ea
COPY batch_sim.patch build_batch_sim.sh /tmp/
RUN git clone https://github.com/FSillT/QCADesigner-E.git /opt/QCADesigner-E \
    && git -C /opt/QCADesigner-E checkout -q "$QCAD_COMMIT" \
    && sh /tmp/build_batch_sim.sh /opt/QCADesigner-E/QCADesignerE/src /tmp/batch_sim.patch /usr/local/bin/batch_sim
WORKDIR /repo
