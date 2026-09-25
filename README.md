# ImageDimensions — browser extension

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

## Install

**[Get it on the Chrome Web Store](https://chromewebstore.google.com/detail/imagedimensions-%E2%80%94-image-s/blmapabdbdadckppfcigonibooalipkh)** — published 2026-08-19.

## Install unpacked (for development)

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

## Finding an image on the page

Click any row and the page scrolls that image to the centre of the view and rings it for a couple of
seconds — amber if it is oversized, blue if it is fine. A filename and a pixel count tell you an
image is wrong; they do not tell you *which* image it is on a long page, and that is the gap this
closes.

It works for images inside nested scroll containers (both the page and the container scroll) and for
sticky or fixed elements, because the ring re-reads the element's position every frame rather than
being drawn once. When a jump cannot land, the reason appears in place of the summary line:

| Reason | What happened |
|---|---|
| *That image has left the page* | The element was removed since the audit — a carousel advanced, or a framework re-rendered |
| *That image is hidden right now* | It is still in the DOM but has no box to point at |
| *The page has changed* | The page navigated, so the measurement no longer applies. Press **Re-check** |

The page's own DOM is never modified: the measured elements are held in the extension's isolated
world, and the ring is a single overlay that removes itself.

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

## Packaging

```bash
./scripts/package.sh chrome     # dist/imagedimensions-extension-<v>-chrome.zip   (Chrome AND Edge)
./scripts/package.sh firefox    # dist/imagedimensions-extension-<v>-firefox.zip  (AMO)
```

Each zip contains only the runtime files — no README, LICENSE, scripts or VCS metadata, since anything
extra is one more thing for review to ask about. Bump `version` in **both** manifests first; every
store rejects a re-upload of an existing version number.

The script also checks the two fields a store silently rejects on: `name` ≤ 45 characters (AMO's
limit, stricter than Chrome's 75) and `description` ≤ 132 (Chrome's, stricter than AMO's), so a
package that builds is submittable to either.

## Firefox

One source, two manifests. `manifest.firefox.json` adds `browser_specific_settings.gecko`, and
`package.sh` writes whichever manifest was selected into the zip as `manifest.json`, so the two
packages cannot drift — a change to `popup.js` is in both or neither.

**The namespace fix is a one-line alias, not a polyfill.** `popup.js` opens with
`const api = globalThis.browser ?? chrome`. Firefox exposes `browser.*` returning promises while
keeping `chrome.*` callback-based, so an awaited `chrome.tabs.query()` there resolves to `undefined`
and destructuring it throws. Chrome and Edge do not define `browser` at all, and their MV3 `chrome.*`
already returns promises. This extension makes exactly two extension-API calls, both promise-shaped,
so `webextension-polyfill` would be weight for nothing.

**`strict_min_version` is 115**, an ESR. `data_collection_permissions` (required by AMO since
2025-11-03; ours declares `none`, because nothing leaves the device) is newer than that, so
`web-ext lint` warns twice that the key is unsupported at 115. Those two warnings are the deliberate
trade: the key is simply ignored by older Firefox, whereas raising the floor to 140 would drop ESR
users to keep a linter quiet.

**Verified in real Firefox 156, not just in the linter:** the package installs as a temporary add-on
through geckodriver, and `measurePage()` — read out of `popup.js`, not copied — returns correct
natural and rendered sizes when run against a live page in Gecko. What is *not* automatable is the
popup's own click path, because `activeTab` needs a real user gesture on the toolbar button. Check
that by hand after install: click the icon on any ordinary page and confirm rows appear.

## Publishing

Three stores, three APIs, so one script each. Packages are automatable; **listing prose and
screenshots mostly are not** — `LISTING.md` holds the text to paste.

```bash
python3 scripts/publish-firefox.py --status                  # what AMO holds
python3 scripts/publish-firefox.py --upload dist/<v>-firefox.zip
python3 scripts/publish-firefox.py --previews                # screenshots + captions

../../overwatch/.venv/bin/python scripts/publish-chrome.py --status
../../overwatch/.venv/bin/python scripts/publish-chrome.py --zip dist/<v>-chrome.zip
../../overwatch/.venv/bin/python scripts/publish-chrome.py --zip dist/<v>-chrome.zip --publish
```

- **AMO** takes name, summary, categories, licence and screenshots through the API; only the long
  description is dashboard-only. Credentials are `AMO_JWT_ISSUER` / `AMO_JWT_SECRET` in
  `extension/.env` (gitignored). ⚠️ They are **account-level and shared with the DomainIntel add-on**,
  so generating a new pair breaks that one too. Copy the existing pair, never regenerate.
- **Chrome** authenticates with the same Google service account used for GA4/GSC. `--zip` updates a
  draft and changes nothing public; `--publish` is separate and effectively irreversible.
- **Edge** takes the Chrome package unchanged, but needs a `PRODUCT_ID` that only exists once the
  product has been created in Partner Center by hand. See `../../domainintel.app/extension/publish-edge.py`.

## Related

Same measurement, other surfaces:

- [imagedimensions-mcp](https://github.com/Bishop81/imagedimensions-mcp) — MCP server
- [imagedimensions-cli](https://github.com/Bishop81/imagedimensions-cli) — CLI and GitHub Action
- [imagedimensions.com](https://imagedimensions.com) — the hosted scanner

## License

MIT — see [LICENSE](LICENSE).
