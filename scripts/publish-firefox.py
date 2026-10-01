#!/usr/bin/env python3
"""
Upload the extension to addons.mozilla.org.

Adapted from ../../domainintel.app/extension/publish-firefox.py, which does the same job for that
product. Two differences, both because this add-on did not exist on AMO yet:

  * `--create` submits the FIRST listed version, which is a different endpoint from later ones
    (POST /addons/addon/ rather than POST /addons/addon/<slug>/versions/). A listed first version
    also has required metadata — name, summary, categories and a licence — and the API does take all
    of it. ⚠️ CORRECTED 2026-10-01: **nothing about an AMO listing needs the dashboard.** The long
    description, homepage, support URL and email all go through a PATCH to the add-on, and the
    screenshots through --previews, so Chrome's "the package is scriptable, the listing is not" split
    does NOT apply here. The 0.2.1 listing went public with an empty description because this script
    did not set one, not because it could not.
  * `--previews` uploads the store screenshots, which the dashboard otherwise wants by hand.

    python3 scripts/publish-firefox.py --status
    python3 scripts/publish-firefox.py --create dist/imagedimensions-extension-0.2.0-firefox.zip
    python3 scripts/publish-firefox.py --upload dist/imagedimensions-extension-0.3.0-firefox.zip
    python3 scripts/publish-firefox.py --previews

⚠️ Credentials are AMO_JWT_ISSUER / AMO_JWT_SECRET in extension/.env (gitignored). They are
ACCOUNT-level keys shared with the DomainIntel add-on on the same Mozilla account, so issuing a new
pair at https://addons.mozilla.org/en-US/developers/addon/api/key/ silently breaks that one too.
Copy the existing pair; do not generate.

⚠️ The JWT is valid for five minutes at most and AMO rejects a longer exp, so every request below
mints a fresh one rather than reusing a token.
"""

import argparse
import base64
import hashlib
import hmac
import json
import mimetypes
import os
import pathlib
import secrets
import sys
import time
import urllib.error
import urllib.request

API = "https://addons.mozilla.org/api/v5"
SLUG = "imagedimensions"
HERE = pathlib.Path(__file__).resolve().parent.parent
ENV = HERE / ".env"

# What the dashboard would otherwise ask for on a first listed submission.
NAME = "ImageDimensions — Image Size Auditor"
SUMMARY = (
    "See every image's real size versus the size it's displayed at, on any page — including pages "
    "a scanner can't reach."
)
# ⚠️ PLAIN TEXT ONLY. AMO's API ESCAPES html in this field rather than honouring it: a description
# sent with <b> and <ul> came back storing &lt;b&gt;, so the public page showed the tags as
# literal text (2026-10-01). The dashboard's rich editor is not the same path. Newlines ARE
# preserved, so structure it the way the Chrome listing does — caps for headings, • for bullets.
# ⚠️ And never seed this constant from a read-back: AMO returns the stored, escaped form, so
# round-tripping it escapes the escapes (3,480 chars became 5,408 on the first attempt).
DESCRIPTION = """Every image on a page has two sizes: the pixels in the file, and the pixels the browser actually draws. When the first is much larger than the second, the visitor downloads weight they never see — and it is invisible until you go looking.

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

The same measurement is available as a hosted scanner, an MCP server for AI coding agents, and a CLI with a GitHub Action for failing a build on oversized images. See imagedimensions.com"""

# Slugs from GET /api/v5/addons/categories/. DomainIntel uses the same first one.
CATEGORIES = ["web-development"]
LICENSE = "MIT"  # extension/LICENSE is MIT, and the source is public.
HOMEPAGE = "https://imagedimensions.com"
# Screenshots already generated for the Chrome listing; AMO takes the same files.
PREVIEWS = [
    ("store/screenshot-1-audit.png", "The audit: every image on the page, worst overshoot first."),
    ("store/screenshot-2-reveal.png", "Clicking a row scrolls to that image and rings it."),
    ("store/screenshot-3-clean.png", "A page whose images are all sized sensibly."),
]


def creds():
    issuer = os.environ.get("AMO_JWT_ISSUER")
    secret = os.environ.get("AMO_JWT_SECRET")
    if not (issuer and secret) and ENV.exists():
        for line in ENV.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            v = v.strip().strip('"').strip("'")
            if k.strip() == "AMO_JWT_ISSUER" and not issuer:
                issuer = v
            elif k.strip() == "AMO_JWT_SECRET" and not secret:
                secret = v
    if not issuer or not secret:
        sys.exit("AMO_JWT_ISSUER / AMO_JWT_SECRET not found in the environment or extension/.env")
    return issuer, secret


def b64(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=")


def token():
    issuer, secret = creds()
    now = int(time.time())
    header = b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = b64(json.dumps({
        "iss": issuer,
        "jti": secrets.token_hex(16),
        "iat": now,
        "exp": now + 60,
    }, separators=(",", ":")).encode())
    signing_input = header + b"." + payload
    sig = b64(hmac.new(secret.encode(), signing_input, hashlib.sha256).digest())
    return (signing_input + b"." + sig).decode()


def call(url, *, method="GET", body=None, content_type=None, tolerate=()):
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"JWT {token()}")
    if content_type:
        req.add_header("Content-Type", content_type)
    try:
        with urllib.request.urlopen(req, timeout=180) as res:
            raw = res.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode()
        if e.code in tolerate:
            return {"_http_error": e.code, "_detail": detail}
        hint = "  (check AMO_JWT_ISSUER / AMO_JWT_SECRET)" if e.code == 401 else ""
        sys.exit(f"HTTP {e.code} {method} {url}{hint}\n{detail}")


def multipart(fields, files):
    boundary = "----imagedimensions" + secrets.token_hex(16)
    out = bytearray()
    for k, v in fields.items():
        out += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
    for k, path in files.items():
        p = pathlib.Path(path)
        ctype = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
        out += (
            f"--{boundary}\r\n"
            f"Content-Disposition: form-data; name=\"{k}\"; filename=\"{p.name}\"\r\n"
            f"Content-Type: {ctype}\r\n\r\n"
        ).encode()
        out += p.read_bytes() + b"\r\n"
    out += f"--{boundary}--\r\n".encode()
    return bytes(out), f"multipart/form-data; boundary={boundary}"


def _t(value):
    """
    Read a translated field. ⚠️ AMO wraps OUTBOUND links in {"url": {...}, "outgoing": {...}} rather
    than returning a plain translated string, so homepage and support_url read as empty if you treat
    them like name or summary — which made a set field look like a failed write on 2026-10-01.
    """
    if isinstance(value, dict):
        if "url" in value and isinstance(value["url"], dict):
            value = value["url"]
        return value.get("en-US") or next(iter(value.values()), "")
    return value or ""


def status():
    d = call(f"{API}/addons/addon/{SLUG}/", tolerate=(404,))
    if d.get("_http_error") == 404:
        print(f"  no add-on at slug '{SLUG}' yet — credentials work only if this says 404, not 401")
        return None
    name = d.get("name") or {}
    print(f"  slug      {d.get('slug')}")
    print(f"  name      {name.get('en-US') or next(iter(name.values()), '?')}")
    print(f"  status    {d.get('status')}")
    print(f"  url       {d.get('url')}")
    print(f"  cats      {d.get('categories')}")
    print(f"  desc      {len(_t(d.get('description')))} chars")
    print(f"  homepage  {_t(d.get('homepage')) or '(empty)'}")
    print(f"  support   {_t(d.get('support_url')) or '(empty)'}  {_t(d.get('support_email'))}")
    print(f"  previews  {len(d.get('previews') or [])}")
    cur = d.get("current_version") or {}
    print(f"  version   {cur.get('version') or '(none public yet)'}")
    for f in cur.get("files") or []:
        print(f"    file    {f.get('status')}  signed={f.get('is_mozilla_signed_extension')}")
    return d


def push_package(zip_path):
    """Upload and wait for AMO's asynchronous validation. Returns the upload uuid."""
    p = pathlib.Path(zip_path)
    if not p.exists():
        sys.exit(f"no such file: {p}")
    body, ctype = multipart({"channel": "listed"}, {"upload": str(p)})
    print(f"uploading {p.name} ({p.stat().st_size} bytes)")
    up = call(f"{API}/addons/upload/", method="POST", body=body, content_type=ctype)
    uuid = up.get("uuid")
    print(f"  upload uuid {uuid}")

    for _ in range(60):
        if up.get("processed"):
            break
        time.sleep(5)
        up = call(f"{API}/addons/upload/{uuid}/")
    if not up.get("processed"):
        sys.exit("validation did not finish in five minutes; check the dashboard")

    v = up.get("validation") or {}
    print(f"  valid={up.get('valid')}  errors={v.get('errors')}  warnings={v.get('warnings')}")
    for m in (v.get("messages") or []):
        if m.get("type") in ("error", "warning"):
            print(f"    {m.get('type').upper()} {m.get('message')}")
    if not up.get("valid"):
        sys.exit("package rejected by validation; nothing was submitted")
    return uuid


def create(zip_path):
    uuid = push_package(zip_path)
    payload = {
        "slug": SLUG,
        "name": {"en-US": NAME},
        "summary": {"en-US": SUMMARY},
        "categories": CATEGORIES,
        "homepage": {"en-US": HOMEPAGE},
        "default_locale": "en-US",
        "version": {"upload": uuid, "license": LICENSE},
    }
    d = call(f"{API}/addons/addon/", method="POST",
             body=json.dumps(payload).encode(), content_type="application/json")
    print(f"  created {d.get('slug')}  status={d.get('status')}  url={d.get('url')}")
    print("Queued for review. Now run --listing and --previews: a listing published with an empty "
          "description is the failure mode this script had on its first use.")
    return d


def upload(zip_path):
    uuid = push_package(zip_path)
    ver = call(f"{API}/addons/addon/{SLUG}/versions/", method="POST",
               body=json.dumps({"upload": uuid}).encode(), content_type="application/json")
    print(f"  version {ver.get('version')} created, channel {ver.get('channel')}")
    print("Queued for review. Listing text stays as the dashboard has it.")


LISTING = {
    "description": {"en-US": DESCRIPTION},
    "homepage": {"en-US": HOMEPAGE},
    "support_url": {"en-US": "https://imagedimensions.com/contact"},
    # ⚠️ Every text field here is translated, support_email included. A bare string is a 400.
    "support_email": {"en-US": "hello@imagedimensions.com"},
}


def listing():
    """Set the prose fields. Safe to re-run; AMO overwrites rather than appending."""
    call(f"{API}/addons/addon/{SLUG}/", method="PATCH",
         body=json.dumps(LISTING).encode(), content_type="application/json")
    d = call(f"{API}/addons/addon/{SLUG}/")
    print(f"  desc      {len(_t(d.get('description')))} chars")
    print(f"  homepage  {_t(d.get('homepage')) or '(empty)'}")
    print(f"  support   {_t(d.get('support_url')) or '(empty)'}  {_t(d.get('support_email'))}")


def previews():
    """
    Upload the store screenshots and caption them.

    Two things learned the hard way against the live API, both silent:

      * A caption sent as a multipart field is ACCEPTED and then not stored — the add-on comes back
        with `caption: {}`. Sent as a bare string it is rejected outright ("You must provide an
        object of {lang-code:value}"), and as `caption[en-US]` it returns 201 and stores nothing. The
        only form that sticks is a JSON PATCH to the preview after it exists.
      * Preview writes are throttled hard, and the lockout is long: a handful of uploads in a row
        earned "Expected available in 3382 seconds". So this paces itself, and reports the wait
        rather than dying on a traceback.

    Idempotent by position, not by caption, because captions read back empty until they are patched.
    """
    d = call(f"{API}/addons/addon/{SLUG}/", tolerate=(404,))
    have = d.get("previews") or []
    ids = [pv.get("id") for pv in have]
    print(f"  {len(have)} preview(s) already on the listing")

    for i, (rel, _caption) in enumerate(PREVIEWS):
        if i < len(ids):
            continue
        p = HERE / rel
        if not p.exists():
            sys.exit(f"missing screenshot: {p}")
        if i:
            time.sleep(25)
        body, ctype = multipart({}, {"image": str(p)})
        r = call(f"{API}/addons/addon/{SLUG}/previews/", method="POST",
                 body=body, content_type=ctype, tolerate=(429,))
        if r.get("_http_error") == 429:
            print(f"  throttled before {rel}: {r.get('_detail')}")
            return
        ids.append(r.get("id"))
        print(f"  uploaded {rel} as {r.get('id')}")

    for pid, (rel, caption) in zip(ids, PREVIEWS):
        time.sleep(4)
        r = call(f"{API}/addons/addon/{SLUG}/previews/{pid}/", method="PATCH",
                 body=json.dumps({"caption": {"en-US": caption}}).encode(),
                 content_type="application/json", tolerate=(429,))
        if r.get("_http_error") == 429:
            print(f"  throttled before captioning {pid}: {r.get('_detail')}")
            return
        print(f"  {pid} caption -> {json.dumps(r.get('caption'))}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true", help="authenticate and show what AMO holds")
    ap.add_argument("--create", metavar="ZIP", help="FIRST submission: create the add-on from this package")
    ap.add_argument("--upload", metavar="ZIP", help="later submissions: add a version to the listed channel")
    ap.add_argument("--listing", action="store_true", help="set description, homepage and support links")
    ap.add_argument("--previews", action="store_true", help="upload the store screenshots")
    a = ap.parse_args()

    if a.status:
        status()
    elif a.create:
        create(a.create)
    elif a.upload:
        upload(a.upload)
    elif a.listing:
        listing()
    elif a.previews:
        previews()
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
