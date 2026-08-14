# ImageDimensions — Chrome extension

Audits every image on the page you are currently looking at: the file's real pixel size versus the
size the browser actually drew it at, with the wasteful ones flagged.

## Why this exists

The hosted scanner loads a page in a headless browser. That means it cannot reach:

- anything behind a login
- sites with bot protection
- `localhost` and staging environments

Roughly **10% of scans fail silently** for those reasons, and staging/localhost is our own audience's
most common case — developers checking work in progress. The extension measures the page as *you*
are seeing it, which is a capability the website structurally cannot have.

## Install (unpacked, for development)

1. Open `chrome://extensions`
2. Turn on **Developer mode** (top right)
3. **Load unpacked** → select this `extension/` folder
4. Pin the icon and open any page with images

## How it measures

Identical in shape to the site and the MCP server — **area overshoot**, oversized above 4× — with one
deliberate improvement.

The hosted scanner runs headless at `devicePixelRatio` 1, so it can only compare the file's pixels to
rendered *CSS* pixels. A 400×400 file in a 200×200 slot therefore reads as exactly 4×, even though on
a 2× display that is textbook-correct retina serving.

Running in a real browser, the extension knows the actual device pixel ratio and compares against the
pixels the display genuinely needs. The same image reads **1.0× on a retina screen** and **4.0× on a
1× screen** — and both are true.

> Building this extension is what exposed a threshold bug elsewhere: the site, `mcp-server` and `cli`
> all used `>= 4`, which flags a perfectly-served retina image as oversized. Fixed 2026-08-14 — the
> threshold is now strictly `> 4` everywhere (mcp-server 0.1.2, cli 0.1.1), and the published field
> study was corrected from 48.2% to **46.9%**. The extension needed no change; it already divides by
> the real DPR. The site still compares against CSS pixels, so its per-image verdict remains the
> conservative one — this extension is the more accurate reading for any single page.

CSS background images are included — they are about 20% of images on a typical page and most audits
miss them entirely.

## Permissions, and what is deliberately absent

| Permission | Why |
|---|---|
| `activeTab` | Read the current tab, only when you click the icon |
| `scripting` | Inject the measurement function on that click |

There are **no host permissions**, no background page, no storage, no analytics and no network
requests. Nothing about the pages you visit leaves your machine — which is both the honest design and
the fastest path through Web Store review.

## Known limits

- Chrome blocks injection into `chrome://` pages, `view-source:` and the Web Store. The popup says so
  rather than showing an empty result.
- Images still loading report no intrinsic size. Let the page settle and press **Re-check**.
- CSS backgrounds are capped at 60 per page, and each intrinsic-size probe times out after 2.5s.
- The list shows the worst 60 images.

## Not in this version

Conversion is deliberately absent. Manifest V3 forbids remote code, so the jSquash WASM codecs would
have to be bundled into the popup — significant weight for a surface that renders for a few hundred
milliseconds. If installs justify it, the better shape is a right-click action on a single image
rather than a second copy of the site's converters.

## Packaging for the Chrome Web Store

```bash
./scripts/package.sh
```

Writes `dist/imagedimensions-extension-<version>.zip`, containing only the runtime files — no README,
LICENSE, scripts or VCS metadata, since anything extra is one more thing for review to ask about. Bump
`version` in `manifest.json` first; the Web Store rejects a re-upload of an existing version number.

## Related

Same measurement, other surfaces:

- [imagedimensions-mcp](https://github.com/Bishop81/imagedimensions-mcp) — MCP server
- [imagedimensions-cli](https://github.com/Bishop81/imagedimensions-cli) — CLI and GitHub Action
- [imagedimensions.com](https://imagedimensions.com) — the hosted scanner

## License

MIT — see [LICENSE](LICENSE).
