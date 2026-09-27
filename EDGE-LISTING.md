# Microsoft Edge Add-ons — what Chris has to do, and what is already done

Edge takes the **Chrome package unchanged** — same MV3 manifest, no `browser_specific_settings`. The
only thing standing between us and a third store listing is that **the Update API can only push to a
product that already exists**, and only a human in Partner Center can create one.

Everything below that is not marked **[CHRIS]** is already built and waiting in this repo.

---

## [CHRIS] The five steps only you can do

**1. Sign in to Partner Center and open the Microsoft Edge program.**
`https://partner.microsoft.com/dashboard/microsoftedge/overview` — the Edge extension program is free
and has no $5 fee, unlike Chrome. If the account has never been registered for the Edge program it
asks once for a publisher display name; use the same one the Chrome listing shows.

**2. Create the extension: "New extension" → upload the package.**

```
extension/dist/imagedimensions-extension-0.2.1-chrome.zip
```

Not the `-firefox` zip — that one carries the Gecko block Edge has no use for.

**3. Fill the listing.** Every field is written out below, ready to paste. Nothing needs composing.

**4. Submit for certification.** Review is usually a few days, similar to Chrome.

**5. Send me the Product ID.** It is the GUID in the address bar once the extension exists
(`.../microsoftedge/extensions/<product-id>/...`). With that, publishing future versions is one
scripted command and never needs the dashboard again — the same way Chrome and Firefox now work.

---

## Paste-ready listing

**Name** — identical to the manifest, which Edge reads for itself:

```
ImageDimensions — Image Size Auditor
```

**Short description** (Edge's summary field):

```
See every image's real size versus the size it's displayed at — on any page, including localhost and pages behind a login.
```

**Description** — use the long description from `LISTING.md` verbatim. It needs no Chrome-specific
edits: it never names Chrome except in the source URL, and the privacy claims are true on Edge too.

**Category:** `Developer Tools`
**Language:** `English (United States)`
**Website:** `https://imagedimensions.com`
**Support / contact:** `https://imagedimensions.com/contact`
**Privacy policy:** `https://imagedimensions.com/privacy`

**Search terms** (Edge allows up to 7 — Chrome has no equivalent field, so these are new):

```
image dimensions · image size checker · oversized images · web performance · responsive images · image audit · devtools
```

**Privacy questionnaire.** Answer **no data collected**. That is literally true and matches what the
Firefox manifest declares (`data_collection_permissions: {required: ["none"]}`): the extension makes
no network requests, stores nothing and has no analytics. If the form asks whether the extension uses
remote code, the answer is also no — everything it runs ships inside the package.

---

## Graphic assets — all four are in `extension/store/`

| Edge field | File | Size | Notes |
|---|---|---|---|
| Store logo **[required]** | `store/edge-logo-300.png` | 300×300 | ⚠️ **Not** `store-icon-128.png` — see below |
| Screenshots **[required]** | `store/screenshot-1-audit.png`, `-2-reveal.png`, `-3-clean.png` | 1280×800 | Same files Chrome and Firefox use |
| Small promotional tile [optional] | `store/promo-440x280.png` | 440×280 | Already exists |
| Large promotional tile [optional] | — | 1400×560 | Not made; skip it, it is optional and only used if Microsoft features the extension |

⚠️ **The logo and the Chrome store icon are different files on purpose.** Chrome's store icon expects
artwork inside a 96×96 area with 16px of transparent padding, because the Store draws its own frame
around it. Edge's logo is full-bleed. Swapping them gets a double frame on one store and a floating
mark on the other.

`edge-logo-300.png` is generated, not hand-drawn: `./scripts/make-edge-assets.sh` rasterises the
site's `favicon.svg` — the same geometry the toolbar icons were redrawn from — at 300px and asserts
the output size. Re-run it if the mark ever changes; never rescale the PNG.

📌 One thing you may notice and should decide for yourself: the mark's height-ruler ticks sit just
outside the blue square, on transparency, so on a white store card they read as faint marks at the
right edge. That is exactly how the icon looks in the browser toolbar today and how the live Chrome
listing looks, so it ships consistent. Changing it is a redesign of the mark, not a store-asset fix.

---

## Credentials — probably already work, confirmable only after step 5

`.env` in this folder carries `EDGE_CLIENT_ID` and `EDGE_STORE_KEY`, copied from the DomainIntel
extension, which publishes to Edge today. Probed 2026-09-26 against the Edge API: both a known product
and a nonexistent one answer **404, not 401**, so the key pair authenticates fine at the account level.

**What that does not prove** is authorisation for a *new* product, because an unauthorised product and
a missing one look the same from outside. Once the product exists, `--check` against its real id
settles it in one call. If it comes back 401, generate a fresh pair in Partner Center under the Edge
program's **Publish API** section — ⚠️ but check first whether issuing new credentials invalidates
DomainIntel's, the way Mozilla's API keys do.

---

## After the product exists — what I do, not you

Publishing is then a copy of `../../domainintel.app/extension/publish-edge.py` with the new product id:

```bash
python3 scripts/publish-edge.py --check                                        # prove the credentials
python3 scripts/publish-edge.py --upload dist/imagedimensions-extension-<v>-chrome.zip
python3 scripts/publish-edge.py --upload <zip> --publish                       # submit for certification
```

Same split as the other two stores: the package is scriptable, the listing prose is not.
