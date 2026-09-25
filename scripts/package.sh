#!/usr/bin/env bash
# Builds the store zip for one target.
#
#   ./scripts/package.sh chrome    -> dist/imagedimensions-extension-<v>-chrome.zip   (Chrome + Edge)
#   ./scripts/package.sh firefox   -> dist/imagedimensions-extension-<v>-firefox.zip  (AMO)
#
# Both targets ship the same popup.html/css/js and icons; only the manifest differs, and the Firefox
# one is written into the zip as `manifest.json`. That is the point: a change to popup.js is in both
# packages or neither.
#
# Ships only what the extension needs at runtime — no README, LICENSE, scripts or VCS metadata, since
# anything extra is one more thing for review to ask about.
#
# Edge takes the CHROME package unchanged (same MV3 manifest, no browser_specific_settings).
set -euo pipefail

cd "$(dirname "$0")/.."

target="${1:-chrome}"
case "$target" in
  chrome)  manifest="manifest.json" ;;
  firefox) manifest="manifest.firefox.json" ;;
  *) echo "Usage: $0 <chrome|firefox>" >&2; exit 1 ;;
esac

# Store field limits, checked here rather than discovered after an upload. Each number below is the
# STRICTER of the two stores, so a package that passes is submittable to either:
#   name        45   (AMO; Chrome allows 75)
#   description 132  (Chrome; AMO is far more generous)
# AMO has also required data_collection_permissions since 2025-11-03 and rejects the upload without
# it. This extension makes no network requests at all, so the honest declaration is "none".
python3 - "$manifest" "$target" <<'PY'
import json, sys
path, target = sys.argv[1], sys.argv[2]
m = json.load(open(path))
bad = []
for field, limit in (("name", 45), ("description", 132)):
    if len(m.get(field, "")) > limit:
        bad.append(f"  {field}: {len(m[field])} characters, limit {limit}\n    {m[field]}")
if target == "firefox":
    d = (m.get("browser_specific_settings", {}).get("gecko", {})
          .get("data_collection_permissions") or {})
    if not d.get("required"):
        bad.append("  browser_specific_settings.gecko.data_collection_permissions.required is missing"
                   "\n    AMO rejects the upload without it. Declare what the extension transmits.")
if bad:
    sys.exit(f"{path} would be rejected by a store:\n" + "\n".join(bad))
PY

version=$(python3 -c "import json,sys;print(json.load(open('$manifest'))['version'])")
out="dist/imagedimensions-extension-${version}-${target}.zip"

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT

cp "$manifest" "$stage/manifest.json"
cp popup.html popup.css popup.js "$stage/"
cp -r icons "$stage/icons"

mkdir -p dist
rm -f "$out"
(cd "$stage" && zip -r -q "$OLDPWD/$out" .)

echo "$out"
unzip -l "$out"
