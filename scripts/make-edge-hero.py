#!/usr/bin/env python3
"""
Renders the large promotional tile Microsoft Edge Add-ons asks for: 1400x560.

    python3 scripts/make-edge-hero.py

Optional on the form, and the widest surface Edge gives, so it is worth having rather than
leaving blank.

The right-hand card is a restrained copy of what the popup actually shows — a row per image,
the file's own size next to the size it was drawn at, and the overshoot as a multiple. That is
the product, so the tile needs no slogan to explain it.

⚠️ Every multiplier is COMPUTED from the two sizes beside it at render time, never typed. The
portfolio rule exists because a card once carried a hand-written contrast figure that the colours
it displayed did not match. If you change a row's numbers, the badge follows automatically; if you
are tempted to type one, you have found the bug this guards against.

Palette and type are the site's own: gray-50 ground, white cards, gray-200 rules, blue-600 for
the mark, amber for a warning badge.
"""
import pathlib
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).resolve().parent.parent
OUT = HERE / "store"
LOGO = OUT / "edge-logo-300.png"

SIZE = (1400, 560)
GRAY50 = (249, 250, 251)
WHITE = (255, 255, 255)
GRAY200 = (229, 231, 235)
GRAY400 = (156, 163, 175)
GRAY600 = (75, 85, 99)
GRAY900 = (17, 24, 39)
BLUE600 = (37, 99, 235)
AMBER_BG = (254, 243, 199)
AMBER_FG = (146, 64, 14)
OK_BG = (243, 244, 246)
OK_FG = (55, 65, 81)

# (filename, natural w, natural h, rendered w, rendered h). The badge is derived from these.
ROWS = [
    ("hero-banner.jpg", 3000, 2000, 250, 167),
    ("product-01.png", 1600, 1600, 400, 400),
    ("team-photo.webp", 800, 600, 400, 300),
]
OVERSIZED_AT = 4  # same threshold as popup.js


def font(size, bold=False):
    """A real font file, found rather than assumed: PIL's default is unreadably small."""
    name = "DejaVuSans-Bold" if bold else "DejaVuSans"
    try:
        path = subprocess.run(["fc-match", "-f", "%{file}", name],
                              capture_output=True, text=True, timeout=10).stdout.strip()
        if path:
            return ImageFont.truetype(path, size)
    except Exception:
        pass
    for p in (f"/usr/share/fonts/truetype/dejavu/{name}.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSans-%s.ttf"
              % ("Bold" if bold else "Regular")):
        if pathlib.Path(p).exists():
            return ImageFont.truetype(p, size)
    sys.exit("no usable TrueType font found; install fonts-dejavu")


def rounded(draw, box, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def main():
    if not LOGO.exists():
        sys.exit(f"missing {LOGO} — run ./scripts/make-edge-assets.sh first")

    img = Image.new("RGB", SIZE, GRAY50)
    d = ImageDraw.Draw(img)

    # ---- left: mark, wordmark, one sentence -------------------------------------------
    mark = Image.open(LOGO).convert("RGBA").resize((104, 104), Image.LANCZOS)
    img.paste(mark, (80, 120), mark)

    f_brand = font(46, True)
    d.text((200, 138), "ImageDimensions", font=f_brand, fill=GRAY900)

    f_head = font(34, True)
    d.text((80, 276), "Every image's real size,", font=f_head, fill=GRAY900)
    d.text((80, 320), "next to the size it is drawn at.", font=f_head, fill=GRAY900)

    f_body = font(23)
    d.text((80, 390), "On the page you are looking at — including pages", font=f_body, fill=GRAY600)
    d.text((80, 422), "behind a login and on localhost.", font=f_body, fill=GRAY600)

    # ---- right: a card shaped like the popup's own result list --------------------------
    card = (760, 120, 1320, 440)
    rounded(d, card, 16, WHITE, GRAY200, 2)

    f_label = font(18, True)
    d.text((796, 152), "IMAGES ON THIS PAGE", font=f_label, fill=GRAY400)

    f_name = font(21)
    f_nums = font(20)
    f_badge = font(21, True)

    y = 196
    for name, nw, nh, rw, rh in ROWS:
        ratio = (nw * nh) / (rw * rh)          # area overshoot, as popup.js computes it
        over = ratio > OVERSIZED_AT
        label = f"{ratio:.1f}\u00d7" if ratio < 10 else f"{round(ratio)}\u00d7"

        thumb = (796, y, 796 + 44, y + 44)
        rounded(d, thumb, 6, GRAY200)

        d.text((856, y - 2), name, font=f_name, fill=GRAY900)
        d.text((856, y + 24), f"{nw}\u00d7{nh}", font=f_nums, fill=GRAY600)
        arrow_x = 856 + d.textlength(f"{nw}\u00d7{nh}", font=f_nums) + 10
        d.text((arrow_x, y + 24), "→", font=f_nums, fill=GRAY400)
        d.text((arrow_x + 26, y + 24), f"{rw}\u00d7{rh}", font=f_nums, fill=GRAY600)

        bw = d.textlength(label, font=f_badge) + 26
        bx = card[2] - 36 - bw
        rounded(d, (bx, y + 4, bx + bw, y + 40), 8, AMBER_BG if over else OK_BG)
        d.text((bx + 13, y + 11), label, font=f_badge, fill=AMBER_FG if over else OK_FG)

        y += 76

    img.save(OUT / "edge-hero-1400x560.png")

    w, h = Image.open(OUT / "edge-hero-1400x560.png").size
    if (w, h) != SIZE:
        sys.exit(f"came out {w}x{h}, expected {SIZE[0]}x{SIZE[1]}")
    print(f"store/edge-hero-1400x560.png  {w}x{h}")
    for name, nw, nh, rw, rh in ROWS:
        print(f"   derived: {name} {nw}x{nh} -> {rw}x{rh} = {(nw*nh)/(rw*rh):.2f}x")


if __name__ == "__main__":
    main()
