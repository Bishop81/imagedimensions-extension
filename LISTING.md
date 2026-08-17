# Chrome Web Store listing — copy/paste source

Everything the Developer Dashboard asks for, in the order it asks. Fields are marked
**[required]** / [optional]. Character limits are the Store's own.

Upload package: `dist/imagedimensions-extension-0.2.0.zip` (run `./scripts/package.sh`).

> ✅ Nothing is outstanding. The privacy policy the Store requires is live at
> `imagedimensions.com/privacy` (built 2026-08-17), with an extension-specific section at
> `#extension`.

---

## Store listing tab

### Name **[required]** — max 75 chars

```
ImageDimensions — Image Size Auditor
```

*(35 chars. Matches `manifest.json` exactly; the Store uses the manifest value, so change both or
neither.)*

---

### Summary **[required]** — max 132 chars

```
See every image's real size versus the size it's displayed at — on any page, including localhost and pages behind a login.
```

*(122 chars.)*

---

### Description **[required]** — max 16,000 chars

```
Every image on a page has two sizes: the pixels in the file, and the pixels the browser actually draws. When the first is much larger than the second, the visitor downloads weight they never see — and it is invisible until you go looking.

ImageDimensions shows you both numbers for every image on the page you are on, sorted worst first.

WHAT YOU GET

• Every image measured — the file's real pixel size next to the size it was drawn at
• A multiplier showing how much was wasted, so a 3000×2000 file in a 250×167 slot reads plainly as 144×
• CSS background images included — roughly a fifth of the images on a typical page, and most audits skip them entirely
• Click any row to scroll straight to that image and highlight it on the page

WHY NOT JUST USE A WEBSITE SCANNER

Hosted scanners load your page in a headless browser somewhere else. That means they cannot see anything behind a login, anything protected by a bot filter, or anything running on localhost or a staging domain — which is exactly where you are working when the problem is still cheap to fix.

This runs in your browser, on the page in front of you.

IT MEASURES AGAINST YOUR ACTUAL DISPLAY

A 400×400 image in a 200×200 slot is wasteful on a standard display and exactly right on a retina one. A headless scanner cannot tell the difference, because it does not have a screen. This extension knows your real device pixel ratio, so it will not flag a correctly-served retina image — and it will flag one that is oversized even after retina is accounted for.

PRIVACY

No account. No network requests. No analytics. No storage. Nothing about the pages you visit leaves your machine, because nothing is ever sent anywhere.

It asks for two permissions and no more: permission to read the current tab when you click the icon, and permission to run the measurement on that click. There are no host permissions, so it has no standing access to any site.

The source is public: github.com/Bishop81/imagedimensions-extension

FROM THE MAKERS OF IMAGEDIMENSIONS.COM

The same measurement is available as a hosted scanner, an MCP server for AI coding agents, and a CLI with a GitHub Action for failing a build on oversized images. See imagedimensions.com
```

---

### Category **[required]**

```
Developer Tools
```

### Language **[required]**

```
English (United States)
```

---

## Graphic assets tab

### Store icon **[required]** — 128×128 PNG

```
extension/icons/icon128.png
```

### Screenshots **[required]** — at least 1, up to 5. 1280×800 or 640×400 PNG/JPEG

Committed in `store/`, already cropped to exactly 1280×800. These are real renders of the real popup
over a demo page — not mockups — so they stay honest if the UI changes:

| File | Shows |
|---|---|
| `store/screenshot-1-audit.png` | The popup over a real page, worst-offender list visible |
| `store/screenshot-2-reveal.png` | A row clicked — the image ringed on the page |
| `store/screenshot-3-clean.png` | The all-clear state on a well-optimised page |

### Small promo tile [optional] — 440×280 PNG

```
store/promo-440x280.png
```

*(Optional, but the Store shows a generic placeholder without it.)*

### Marquee promo tile [optional] — 1400×560 PNG

Skip. Only used if the Store ever features the extension editorially.

---

## Additional fields

### Official URL / Homepage [optional]

```
https://imagedimensions.com
```

### Support URL **[required]**

```
https://imagedimensions.com/contact
```

### Mature content **[required]**

```
No
```

---

## Privacy practices tab

This is the tab that gets submissions rejected. Answer it exactly as below — every claim here is
literally true of the code, which is what makes it safe to say.

### Single purpose description **[required]**

```
This extension audits the images on the web page the user is currently viewing. For each image it reports the file's intrinsic pixel dimensions alongside the dimensions the browser rendered it at, and flags images whose file is substantially larger than the space it is displayed in. Clicking a result scrolls that image into view and highlights it.
```

### Permission justifications **[required]**

**`activeTab`**

```
Used to read the images of the page the user is currently viewing. Access is granted by Chrome only for the tab the user is on and only when the user clicks the extension's toolbar icon. The extension requests no host permissions, so it has no access to any site unless the user explicitly invokes it on that tab.
```

**`scripting`**

```
Used to run the measurement function in the active tab when the user clicks the toolbar icon. The injected function reads each image's naturalWidth/naturalHeight and its rendered bounding box, plus the element's computed background-image, and returns those measurements to the popup. A second function is injected only when the user clicks a result: it scrolls that element into view and draws a temporary highlight, which it then removes. Neither function modifies the page's content.
```

**Remote code — "Are you using remote code?"**

```
No, I am not using remote code
```

*True: everything executes from files inside the package. No `eval`, no injected `<script src>`, no
CDN, no WASM fetched at runtime.*

### Data usage **[required]**

Tick **nothing**. The extension collects none of the disclosure categories:

| Category | Collected? |
|---|---|
| Personally identifiable information | No |
| Health information | No |
| Financial and payment information | No |
| Authentication information | No |
| Personal communications | No |
| Location | No |
| Web history | No |
| User activity | No |
| Website content | No |

Then tick all three certifications — each is true:

- I do not sell or transfer user data to third parties, outside of the approved use cases
- I do not use or transfer user data for purposes that are unrelated to my item's single purpose
- I do not use or transfer user data to determine creditworthiness or for lending purposes

> **On "Website content":** the extension *reads* image dimensions from the page in order to display
> them, but it does not **collect** them — nothing is transmitted, persisted, or retained past the
> popup closing. The disclosure asks about collection. If a reviewer queries it, that sentence is the
> answer, and the public source backs it up.

### Privacy policy URL **[required]**

```
https://imagedimensions.com/privacy#extension
```

✅ **Live.** Built 2026-08-17. The page covers the website and the extension, with the
extension-specific section anchored at `#extension` — that is the part a reviewer needs, and the
anchor drops them straight on it.

It states, accurately and checkably: the extension collects, transmits, stores and shares nothing;
makes no network requests; has no analytics, telemetry, cookies, storage or account; requests only
`activeTab` and `scripting` with **no host permissions**; and links the public source so none of it
has to be taken on trust.

⚠️ **Keep it true.** Every claim on that page was checked against the code the day it was written. If
the extension ever gains a network call, storage, or a permission, the policy has to change in the
same commit — a stale privacy policy is a written claim that is no longer true, which is worse than
having none.

## Distribution tab

| Field | Value |
|---|---|
| Visibility | **Public** |
| Distribution | All regions |
| Pricing | Free |

---

## Pre-submit checklist

- [ ] `manifest.json` version bumped (currently **0.2.0**) — the Store rejects a re-upload of an existing version
- [ ] `./scripts/package.sh` run, uploading `dist/imagedimensions-extension-0.2.0.zip`
- [ ] Privacy policy URL resolves (see blocker above)
- [ ] Screenshots are exactly 1280×800 or 640×400
- [ ] Support URL resolves
- [ ] After it goes live: add the listing URL to `ORGANIZATION_SAME_AS` in
      `image-dimensions-service/src/lib/organization.ts`, next to the GitHub and npm entries
