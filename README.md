# Vpliv premika celic na majoritetna vrata QCA

Seminarska naloga, skupina 12 (Jerneja Krajcar, Amar Mehić, Anže Vidmar).

Celice majoritetnih vrat QCA premikamo po korakih 0,25 nm v štirih smereh in
s simulatorjem QCADesigner-E preverjamo, pri katerem premiku vrata ne delujejo
več pravilno. Poskuse ponovimo z bistabilnim modelom, z modelom koherentnega
vektorja pri 1 K in 10 K ter z modelom, ki računa disipacijo energije.

## Ponovitev rezultatov

Potrebujete le [Docker](https://www.docker.com/products/docker-desktop/).
Vse ukaze poženite v korenu repozitorija.

```bash
# 1. okolje: Ubuntu, Python in popravljen batch_sim (prvič traja nekaj minut)
docker build -t qca-sim -f tools/Dockerfile tools

# 2. vsi poskusi (E1–E3) in vse slike
docker run --rm -v "$PWD":/repo qca-sim sh scripts/run_all.sh
```

Če `git status` po zagonu ne pokaže sprememb v `experiments/results/`, ste
dobili enake rezultate kot mi.

En sam poskus, npr. samo sredinska celica (id 2) pri 10 K:

```bash
docker run --rm -v "$PWD":/repo qca-sim python3 scripts/run_sweep.py \
    --engine COHERENCE_VECTOR --options experiments/sim-options/coherence-10K.txt \
    --cells 2 --out experiments/results/test.csv
```

**Windows:** v PowerShellu namesto `"$PWD":/repo` napišite `"${PWD}:/repo"`.
**Mac z Apple Silicon:** slika teče prek emulacije x86, zato je počasnejša.

## Poskusi

| Poskus | Model | Rezultat |
|---|---|---|
| E1 | bistabilni | `experiments/results/e1-bistable.csv` |
| E2 | koherentni vektor, 1 K in 10 K | `experiments/results/e2-coherence-*.csv` |
| E3 | koherentni vektor z energijo, 1 K | `experiments/results/e3-energy-1K.csv` |

Vsaka vrstica v CSV je ena simulacija: celica, smer, premik, `status`
(`ok`, `fail` ali `overlap`, ko bi se celica dotaknila soseda), izhod, vhod, ki
mu izhod sledi ob napaki, in pri E3 disipacija energije v eV na urin cikel.

Nastavitve simulatorja so v `experiments/sim-options/`, slike in tabela za
poročilo pa v `experiments/figures/`.

## Struktura

| Pot | Vsebina |
|---|---|
| `experiments/majority-voter-base.qca` | osnovno vezje (5 celic) |
| `scripts/run_sweep.py` | premiki celic, simulacija in preverjanje izhoda |
| `scripts/prepare_batch.py` | priprava datoteke `.qca` za `batch_sim` |
| `scripts/move_cell.py`, `analyze_qca.py` | premik in branje celic v datoteki `.qca` |
| `scripts/plot_tolerance.py`, `plot_circuit.py` | slike in tabela za poročilo |
| `tools/` | Dockerfile in popravki za `batch_sim` |
| `test/`, `generated/` | prvi ročni poskusi (glej poročilo, *Kaj ni delovalo*) |

## Popravki simulatorja

Uporabljamo QCADesigner-E (commit `3bc9030`) s štirimi popravki v
`tools/batch_sim.patch`: izbira modela z energijo, branje periode ure in
vhodov, registracija tipov objektov in zaokroževanje položajev celic pri
seštevanju energije. Bistabilni model in koherentni vektor dajo s popravki
enake rezultate kot izvirni `batch_sim`.
