#!/usr/bin/env python3
"""
Upload a new ImageDimensions version to Microsoft Edge Add-ons.

The Edge counterpart to publish.py (Chrome) and publish-firefox.py (AMO). Three
stores, three APIs, three auth schemes, so three files.

    python3 extension/scripts/publish-edge.py --check
    python3 extension/scripts/publish-edge.py --upload extension/domainintel-extension-1.0.3-chrome.zip
    python3 extension/scripts/publish-edge.py --upload <zip> --publish

  --check    prove the credentials work without changing anything. See the note
             on how, below: Edge gives no plain read-only endpoint, so this is
             less obvious than AMO's --status.
  --upload   push the package into the DRAFT submission and wait for Edge to
             finish validating it. Nothing is public and no review starts.
  --publish  submit the draft for certification. Separate flag on purpose, the
             same way publish.py separates it for Chrome.

Edge takes the CHROME package unchanged: same MV3 manifest, no
browser_specific_settings. Do not upload the Firefox zip here.

Credentials are EDGE_STORE_KEY and EDGE_CLIENT_ID in extension/.env (gitignored), both
issued together in Partner Center. v1.1 wants them as two headers:

    Authorization: ApiKey <EDGE_STORE_KEY>
    X-ClientID:    <EDGE_CLIENT_ID>

⚠️ Listing text, assets, search terms and the compliance form are NOT settable
here, exactly as on the other two stores. extension/EDGE-LISTING.txt holds them.
"""

import argparse
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request

API = "https://api.addons.microsoftedge.microsoft.com/v1"
PRODUCT_ID = "972209ad-8e7b-4060-846e-af79f666ff28"  # Partner Center, created 2026-10-01
ENV = pathlib.Path(__file__).resolve().parent.parent / ".env"


def creds():
    key = os.environ.get("EDGE_STORE_KEY")
    client = os.environ.get("EDGE_CLIENT_ID")
    if (not key or not client) and ENV.exists():
        for line in ENV.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            v = v.strip().strip('"').strip("'")
            if k.strip() == "EDGE_STORE_KEY" and not key:
                key = v
            elif k.strip() == "EDGE_CLIENT_ID" and not client:
                client = v
    missing = [n for n, v in (("EDGE_STORE_KEY", key), ("EDGE_CLIENT_ID", client)) if not v]
    if missing:
        sys.exit(
            "missing in the environment and .env: " + ", ".join(missing) + "\n"
            "  Both are issued together in Partner Center under the extension's API credentials.\n"
            "  The key is a ~40 character token; the client id is a GUID. They are different values."
        )
    return key, client


def call(path, *, method="GET", body=None, content_type=None):
    key, client = creds()
    req = urllib.request.Request(API + path, data=body, method=method)
    req.add_header("Authorization", "ApiKey " + key)
    req.add_header("X-ClientID", client)
    if content_type:
        req.add_header("Content-Type", content_type)
    try:
        with urllib.request.urlopen(req, timeout=300) as res:
            raw = res.read().decode()
            return res.status, dict(res.headers), (json.loads(raw) if raw.strip() else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            parsed = json.loads(raw) if raw.strip() else {}
        except ValueError:
            parsed = {"raw": raw[:400]}
        return e.code, dict(e.headers), parsed


def check():
    """
    Prove the credentials without changing anything.

    Edge exposes no plain "describe my product" GET the way AMO does, so there is
    nothing to simply read back. What works instead is asking for an operation
    that cannot exist: a well-formed but nonexistent operation id.

        wrong credentials -> 401/403, the request never reaches the product
        right credentials -> 404, authenticated and told the operation is unknown

    So a 404 here is the SUCCESS case. It is read-only and creates no draft, which
    matters because the obvious alternative, POSTing an empty package, would.
    """
    bogus = "00000000-0000-0000-0000-000000000000"
    status, _, body = call(f"/products/{PRODUCT_ID}/submissions/operations/{bogus}")
    if status in (401, 403):
        print(f"  HTTP {status} — credentials REJECTED")
        print(f"  {json.dumps(body)[:300]}")
        return 1
    if status == 404:
        print(f"  HTTP 404 on a nonexistent operation — credentials ACCEPTED")
        print(f"  product {PRODUCT_ID}")
        return 0
    print(f"  HTTP {status} — unexpected, neither an auth rejection nor the expected 404")
    print(f"  {json.dumps(body)[:300]}")
    print("  Treat this as UNVERIFIED rather than as either answer.")
    return 1


def wait(path, what):
    """Edge validates asynchronously; poll the operation rather than assume it passed."""
    for _ in range(80):
        status, _, body = call(path)
        state = (body or {}).get("status")
        if state and state != "InProgress":
            return state, body
        time.sleep(15)
    sys.exit(f"{what}: still InProgress after 20 minutes; check Partner Center")


def upload(zip_path, publish=False):
    p = pathlib.Path(zip_path)
    if not p.exists():
        sys.exit(f"no such file: {p}")
    if "firefox" in p.name:
        sys.exit(f"{p.name} looks like the Firefox package. Edge takes the CHROME zip.")

    print(f"uploading {p.name} ({p.stat().st_size} bytes)")
    status, headers, body = call(f"/products/{PRODUCT_ID}/submissions/draft/package",
                                 method="POST", body=p.read_bytes(),
                                 content_type="application/zip")
    if status not in (200, 202):
        sys.exit(f"upload rejected: HTTP {status}\n{json.dumps(body)[:400]}")
    op = headers.get("Location") or (body or {}).get("operationID")
    print(f"  operation {op}")

    state, body = wait(f"/products/{PRODUCT_ID}/submissions/draft/package/operations/{op}", "package")
    print(f"  package validation: {state}")
    if state != "Succeeded":
        for m in (body or {}).get("errors") or []:
            print(f"    {m}")
        sys.exit("package did not validate; nothing was submitted")

    if not publish:
        print("Draft updated. Nothing is public and no review has started.")
        print("Re-run with --publish to submit it for certification.")
        return

    notes = json.dumps({"notes": "See the reviewer notes in extension/EDGE-LISTING.txt."})
    status, headers, body = call(f"/products/{PRODUCT_ID}/submissions",
                                 method="POST", body=notes.encode(),
                                 content_type="application/json")
    if status not in (200, 202):
        sys.exit(f"publish rejected: HTTP {status}\n{json.dumps(body)[:400]}")
    op = headers.get("Location") or (body or {}).get("operationID")
    state, body = wait(f"/products/{PRODUCT_ID}/submissions/operations/{op}", "publish")
    print(f"  submission: {state}")
    if state != "Succeeded":
        sys.exit(json.dumps(body)[:400])
    print("Submitted for certification.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="prove the credentials, change nothing")
    ap.add_argument("--upload", metavar="ZIP", help="upload the Chrome package into the draft")
    ap.add_argument("--publish", action="store_true", help="with --upload, submit for certification")
    a = ap.parse_args()

    if a.check:
        sys.exit(check())
    elif a.upload:
        upload(a.upload, publish=a.publish)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
