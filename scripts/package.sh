#!/usr/bin/env bash
# Builds the zip that gets uploaded to the Chrome Web Store.
# Ships only what the extension needs at runtime — no README, LICENSE, scripts or VCS metadata,
# since anything extra is one more thing for review to ask about.
set -euo pipefail

cd "$(dirname "$0")/.."
version=$(grep -o '"version": *"[^"]*"' manifest.json | head -1 | cut -d'"' -f4)
out="dist/imagedimensions-extension-${version}.zip"

mkdir -p dist
rm -f "$out"
zip -r -q "$out" manifest.json popup.html popup.css popup.js icons

echo "$out"
unzip -l "$out"
