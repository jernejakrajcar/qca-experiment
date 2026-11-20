#!/bin/sh
# Build batch_sim from QCADesigner-E sources with the fixes in batch_sim.patch.
# Usage: build_batch_sim.sh <QCADesigner-E/QCADesignerE/src> <patch> <output binary>
set -e
SRC_DIR="$1"; PATCH="$2"; OUT="$3"
cd "$SRC_DIR"
patch -p0 < "$PATCH"
SRC="fileio.c fileio_helpers.c custom_widgets.c simulation.c simulation_data.c \
bistable_simulation.c coherence_vector.c coherence_vector_energy.c design.c \
objects/QCADCell.c objects/QCADCompoundDO.c objects/QCADDesignObject.c \
objects/QCADDOContainer.c objects/QCADLabel.c objects/QCADLayer.c objects/QCADRuler.c \
objects/QCADStretchyObject.c objects/QCADSubstrate.c exp_array.c objects/object_helpers.c \
hsl2rgb.c generic_utils.c graph_dialog_widget_data.c main_batch_sim.c"
gcc -O2 -w -I. -I.. -DSTDIO_FILEIO -DPACKAGE=\"QCADesigner\" -DVERSION=\"2.2\" \
    -DGETTEXT_PACKAGE=\"QCADesigner\" -DPACKAGE_DATA_DIR=\"/usr/share\" \
    -DPACKAGE_SOURCE_DIR=\".\" -DSTDC_HEADERS=1 -DHAVE_UNISTD_H=1 \
    $(pkg-config --cflags glib-2.0 gobject-2.0) $SRC -o "$OUT" \
    $(pkg-config --libs glib-2.0 gobject-2.0 gthread-2.0) -lm
