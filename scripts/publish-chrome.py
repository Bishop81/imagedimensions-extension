#!/usr/bin/env python3
"""
Create, upload and publish the ImageDimensions Chrome extension.

Modelled on overwatch/chrome_extension_publish.py, which does the same job for
the accessibility-scanner extension. Same service account, same publisher. This
file exists separately so domainintel's release tooling lives with domainintel.

    overwatch/.venv/bin/python extension/scripts/publish-chrome.py --status
    overwatch/.venv/bin/python extension/scripts/publish-chrome.py --create --zip <path>
    overwatch/.venv/bin/python extension/scripts/publish-chrome.py --zip <path>
    overwatch/.venv/bin/python extension/scripts/publish-chrome.py --zip <path> --publish

  --create   makes a NEW store item from the zip (first release only) and prints
             the item id, which then goes in ITEM below. Uses the v1.1 endpoint:
             v2 has no insert.
  --zip      uploads a draft. Nothing public changes and NO review is triggered.
  --publish  pushes the draft live. IRREVERSIBLE — the only undo is shipping
             another version on top. Deliberately a separate flag.

⚠️ The listing text, screenshots and category CANNOT be set through any API.
They are dashboard-only, and the dashboard cannot be browser-automated (Chrome
returns "The extensions gallery cannot be scripted" to every extension). Paste
them from extension/LISTING.md.

⚠️ The draft is ATOMIC: package + listing text are one unit. Pressing Submit in
the dashboard sends whichever package is in the draft to review along with the
text, so for a release that changes both, upload the draft and let the dashboard
Submit ship both. --publish is only for code with no listing change.

Run it with overwatch's venv, which has google-auth installed.
"""

import argparse
import json
import sys
import urllib.error
import urllib.request

import google.auth.transport.requests as gart
from google.oauth2 import service_account

# The same service account used for GA4/GSC, added as a user on the Web Store
# publisher account. Service accounts do work for this API.
KEY_FILE = "/home/chris/Documents/Dev/projects/personal/active/innergrowth/inner-growth-api-6cadc0a7164d.json"
PUBLISHER = "75541173-4e4d-4ea2-812c-943b28b0391c"

# The live listing, published 2026-08-19. The id is the one in the Web Store URL. Same publisher
# as the accessibility-scanner and ImageDimensions items, which is why the service account can see it.
ITEM = "blmapabdbdadckppfcigonibooalipkh"

BASE = "https://chromewebstore.googleapis.com/v2"
UPLOAD = "https://chromewebstore.googleapis.com/upload/v2"
# Item creation only exists on the older API.
V1_UPLOAD = "https://www.googleapis.com/upload/chromewebstore/v1.1/items"

RW_SCOPE = "https://www.googleapis.com/auth/chromewebstore"
RO_SCOPE = "https://www.googleapis.com/auth/chromewebstore.readonly"


def token(scope):
    creds = service_account.Credentials.from_service_account_file(KEY_FILE, scopes=[scope])
    creds.refresh(gart.Request())
    return creds.token


def call(url, *, scope, method="GET", body=None, content_type="application/json", extra_headers=None):
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", f"Bearer {token(scope)}")
    for k, v in (extra_headers or {}).items():
        req.add_header(k, v)
    if body is not None:
        req.add_header("Content-Type", content_type)
        req.data = body
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            raw = r.read().decode()
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:1500]
        raise SystemExit(f"HTTP {e.code} from {url}\n{detail}")


def require_item():
    if not ITEM:
        sys.exit("ITEM is not set. Run --create first, then put the returned id in ITEM.")


def create(zip_path):
    """Create a brand new store item from a package. First release only."""
    with open(zip_path, "rb") as fh:
        payload = fh.read()
    print(f"\n  creating a NEW item from {zip_path} ({len(payload):,} bytes)")
    res = call(V1_UPLOAD, scope=RW_SCOPE, method="POST", body=payload,
               content_type="application/zip",
               extra_headers={"x-goog-api-version": "2"})
    print(f"  response  : {json.dumps(res)[:600]}")
    item_id = res.get("id")
    if item_id:
        print(f"\n  ITEM ID   : {item_id}")
        print("  Put that in ITEM at the top of this file.")
        print("  Nothing is public: it is an unlisted draft until the store")
        print("  listing and privacy tabs are filled in and Submit is pressed.")
    return res


def status():
    require_item()
    return call(f"{BASE}/publishers/{PUBLISHER}/items/{ITEM}:fetchStatus", scope=RO_SCOPE)


def version_of(rev):
    for ch in rev.get("distributionChannels") or []:
        if ch.get("crxVersion"):
            return ch["crxVersion"]
    return "?"


def blocked(st):
    """Any revision in review blocks both package uploads and listing submissions.

    Scans every *ItemRevisionStatus key rather than a hardcoded list: the pending
    one arrives as submittedItemRevisionStatus, not the draft* key you would
    guess, and a hardcoded guard silently does nothing.
    """
    for key, value in (st or {}).items():
        if not key.endswith("ItemRevisionStatus") or not isinstance(value, dict):
            continue
        state = (value.get("state") or "").upper()
        if "PENDING" in state or "REVIEW" in state or "IN_PROGRESS" in state:
            return f"{key[: -len('ItemRevisionStatus')]} is {value.get('state')} (v{version_of(value)})"
    return None


def show(st):
    for key, value in (st or {}).items():
        if key.endswith("ItemRevisionStatus") and isinstance(value, dict):
            label = key[: -len("ItemRevisionStatus")]
            print(f"  {label:<10}: {value.get('state')}  v{version_of(value)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", help="path to the packaged extension .zip")
    ap.add_argument("--create", action="store_true",
                    help="create a NEW store item from the zip (first release only)")
    ap.add_argument("--publish", action="store_true",
                    help="push the uploaded draft LIVE to all users (irreversible)")
    ap.add_argument("--status", action="store_true", help="show status and exit")
    args = ap.parse_args()

    print("=" * 70)
    print("IMAGEDIMENSIONS EXTENSION — create / upload / publish")
    print("=" * 70)

    if args.create:
        if not args.zip:
            sys.exit("--create needs --zip <path>.")
        create(args.zip)
        return

    st = status()
    show(st)

    if args.status:
        return

    if not args.zip:
        sys.exit("Nothing to do: pass --zip <path> (or --status).")

    pending = blocked(st)
    if pending:
        sys.exit(f"\nRefusing to upload: {pending}. The store blocks new packages, "
                 "AND new listing-text submissions, until it clears.")

    with open(args.zip, "rb") as fh:
        payload = fh.read()
    print(f"\n  uploading : {args.zip} ({len(payload):,} bytes)")
    res = call(f"{UPLOAD}/publishers/{PUBLISHER}/items/{ITEM}:upload",
               scope=RW_SCOPE, method="POST", body=payload,
               content_type="application/zip")
    print(f"  upload    : {json.dumps(res)[:400]}")

    if not args.publish:
        print("\n  Draft updated. Nothing is live yet.")
        return

    print("\n  publishing to all users…")
    res = call(f"{BASE}/publishers/{PUBLISHER}/items/{ITEM}:publish",
               scope=RW_SCOPE, method="POST", body=json.dumps({}).encode())
    print(f"  publish   : {json.dumps(res)[:400]}")


if __name__ == "__main__":
    main()
