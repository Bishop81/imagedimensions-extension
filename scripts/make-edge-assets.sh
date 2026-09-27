#!/usr/bin/env bash
# Renders the one store asset Microsoft Edge Add-ons requires that Chrome does not:
# a 300x300 store logo.
#
#   ./scripts/make-edge-assets.sh
#
# Everything else carries over from store/ unchanged — Edge takes the same 1280x800
# screenshots Chrome already needed, and the 440x280 promotional tile is already there.
#
# Rendered from the SITE's favicon.svg, which is the geometric source the toolbar icons were
# drawn from (see d6f2549). Rasterising the vector keeps the mark identical to the one in the
# browser and gives clean edges at 300px; upscaling icon128.png would soften them.
#
# ⚠️ Edge's logo is full-bleed, unlike Chrome's store icon, which the Store expects to carry
# 16px of transparent padding inside a 128px canvas (store/store-icon-128.png). Do not
# substitute one for the other: on Chrome a full-bleed icon gets double-framed, and on Edge a
# padded one floats in its own tile.
set -euo pipefail

cd "$(dirname "$0")/.."
SVG="../image-dimensions-service/public/favicon/favicon.svg"
OUT="store/edge-logo-300.png"

[ -f "$SVG" ] || { echo "missing source: $SVG" >&2; exit 1; }

inkscape "$SVG" --export-type=png --export-filename="$OUT" \
  --export-width=300 --export-height=300 --export-background-opacity=0 2>/dev/null

# Assert the result rather than trusting the flags: a wrong size is rejected at upload, after
# the listing has been filled in by hand.
python3 - "$OUT" <<'PY'
import struct, sys
p = sys.argv[1]
w, h = struct.unpack('>II', open(p, 'rb').read(24)[16:24])
if (w, h) != (300, 300):
    sys.exit(f"{p} came out {w}x{h}, expected 300x300")
print(f"{p}  {w}x{h}")
PY
