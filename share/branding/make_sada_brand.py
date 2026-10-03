#!/usr/bin/env python3
"""Generate Sada's brand assets (app icon, document icon, splash, About banner,
installer images) from code, so the artwork can be regenerated or adjusted.

Requirements (dev machine only): Python 3 with uharfbuzz, fonttools and Pillow,
rsvg-convert, and the fonts Inter Display (Latin) and Noto Kufi Arabic (Arabic).
Both fonts are under the SIL Open Font License; text is converted to outlines.

Usage:  python3 share/branding/make_sada_brand.py   (run from the repository root)
"""

import io
import math
import os
import subprocess
import sys
import tempfile

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

FONT_LATIN = "/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf"
FONT_LATIN_REGULAR = "/usr/share/fonts/opentype/inter/InterDisplay-Regular.otf"
FONT_ARABIC = "/usr/share/fonts/truetype/noto/NotoKufiArabic-Bold.ttf"

# Palette (matches src/app/configs/dark.cfg)
GRAPHITE_TOP = "#34383E"
GRAPHITE_BOTTOM = "#15171A"
AMBER_LIGHT = "#FFC15A"
AMBER = "#F2A33A"
AMBER_DEEP = "#F2763A"


# --------------------------------------------------------------------------
# Text to outlines
# --------------------------------------------------------------------------
class ShapedText:
    def __init__(self, text, font_path, size, rtl=False):
        self.size = size
        blob = hb.Blob.from_file_path(font_path)
        face = hb.Face(blob)
        font = hb.Font(face)
        self.upem = face.upem
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        if rtl:
            buf.direction = "rtl"
        hb.shape(font, buf, {"kern": True, "liga": True})
        self.infos = buf.glyph_infos
        self.positions = buf.glyph_positions
        self.tt = TTFont(font_path)
        self.glyph_set = self.tt.getGlyphSet()
        self.glyph_order = self.tt.getGlyphOrder()
        self.width = sum(p.x_advance for p in self.positions) * size / self.upem

    def path(self, x, y):
        """SVG path data with the text's left edge at x and baseline at y."""
        scale = self.size / self.upem
        pen = SVGPathPen(self.glyph_set)
        cursor = 0
        for info, pos in zip(self.infos, self.positions):
            name = self.glyph_order[info.codepoint]
            gx = x + (cursor + pos.x_offset) * scale
            gy = y - pos.y_offset * scale
            tpen = TransformPen(pen, (scale, 0, 0, -scale, gx, gy))
            self.glyph_set[name].draw(tpen)
            cursor += pos.x_advance
        return pen.getCommands()


def text_path(text, font, size, x, y, fill, rtl=False, anchor="start", opacity=1.0):
    st = ShapedText(text, font, size, rtl)
    if anchor == "middle":
        x -= st.width / 2
    elif anchor == "end":
        x -= st.width
    return f'<path d="{st.path(x, y)}" fill="{fill}" fill-opacity="{opacity}"/>', st.width


# --------------------------------------------------------------------------
# The mark: a sound source and its fading echoes
# --------------------------------------------------------------------------
def arc_path(cx, cy, r, half_angle_deg):
    a = math.radians(half_angle_deg)
    x1, y1 = cx + r * math.cos(-a), cy + r * math.sin(-a)
    x2, y2 = cx + r * math.cos(a), cy + r * math.sin(a)
    return f"M{x1:.2f},{y1:.2f} A{r:.2f},{r:.2f} 0 0 1 {x2:.2f},{y2:.2f}"


def mark_group(x, y, size, small=False, with_tile=True, uid="m"):
    """The Sada mark drawn in a size x size box at (x, y)."""
    s = size / 1024.0
    parts = [f'<g transform="translate({x:.2f},{y:.2f}) scale({s:.5f})">']
    if with_tile:
        parts.append(
            f'<rect x="32" y="32" width="960" height="960" rx="224" fill="url(#{uid}bg)"/>'
            f'<rect x="36" y="36" width="952" height="952" rx="220" fill="none" '
            f'stroke="#FFFFFF" stroke-opacity="0.07" stroke-width="8"/>')
    # A short waveform (the sound) followed by its fading echoes
    if small:
        cx, cy = 406, 512
        bar_w, bars = 92, [(cx - 120, 230), (cx, 420), (cx + 120, 270)]
        arcs = [(330, 96, 1.0)]
        half = 52
    else:
        cx, cy = 358, 512
        bar_w, bars = 60, [(cx - 80, 190), (cx, 360), (cx + 80, 240)]
        arcs = [(272, 64, 1.0), (390, 56, 0.55)]
        half = 50
    for bx, bh in bars:
        parts.append(f'<rect x="{bx - bar_w / 2:.1f}" y="{cy - bh / 2:.1f}" width="{bar_w}" height="{bh}" '
                     f'rx="{bar_w / 2:.1f}" fill="url(#{uid}amber)"/>')
    for r, w, op in arcs:
        parts.append(f'<path d="{arc_path(cx, cy, r, half)}" fill="none" stroke="url(#{uid}amber)" '
                     f'stroke-width="{w}" stroke-linecap="round" stroke-opacity="{op}"/>')
    parts.append("</g>")
    return "".join(parts)


def mark_defs(uid="m"):
    return (f'<linearGradient id="{uid}bg" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{GRAPHITE_TOP}"/><stop offset="1" stop-color="{GRAPHITE_BOTTOM}"/>'
            f'</linearGradient>'
            f'<linearGradient id="{uid}amber" gradientUnits="userSpaceOnUse" x1="200" y1="200" x2="800" y2="820">'
            f'<stop offset="0" stop-color="{AMBER_LIGHT}"/><stop offset="1" stop-color="{AMBER_DEEP}"/>'
            f'</linearGradient>')


def echo_decoration(cx, cy, radii, stroke, opacity, half=60):
    out = []
    for i, r in enumerate(radii):
        op = opacity * (1.0 - i / (len(radii) + 1))
        out.append(f'<path d="{arc_path(cx, cy, r, half)}" fill="none" stroke="{AMBER}" '
                   f'stroke-width="{stroke}" stroke-linecap="round" stroke-opacity="{op:.3f}"/>')
    return "".join(out)


def svg(width, height, body, defs=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}"><defs>{defs}</defs>{body}</svg>')


def graphite_bg(width, height, uid="pg"):
    defs = (f'<linearGradient id="{uid}" x1="0" y1="0" x2="0.35" y2="1">'
            f'<stop offset="0" stop-color="#2D3035"/><stop offset="1" stop-color="#131518"/></linearGradient>')
    return defs, f'<rect width="{width}" height="{height}" fill="url(#{uid})"/>'


# --------------------------------------------------------------------------
# Assets
# --------------------------------------------------------------------------
def app_icon_svg(small=False):
    return svg(1024, 1024, mark_group(0, 0, 1024, small=small), mark_defs())


def doc_icon_svg():
    # A page with a folded corner carrying the mark
    page = ('<path d="M220,64 H640 L840,264 V912 Q840,960 792,960 H220 Q172,960 172,912 V112 Q172,64 220,64 Z" '
            'fill="#F4F5F7" stroke="#C9CDD2" stroke-width="12"/>'
            '<path d="M640,64 V216 Q640,264 688,264 H840" fill="#DADDE1" stroke="#C9CDD2" stroke-width="12" '
            'stroke-linejoin="round"/>')
    body = page + mark_group(266, 420, 440, small=True)
    return svg(1024, 1024, body, mark_defs())


def splash_svg():
    w, h = 800, 380
    bg_defs, bg = graphite_bg(w, h)
    body = [bg, echo_decoration(560, 190, [140, 230, 320, 410, 500], 22, 0.10)]
    body.append(mark_group(38, 74, 112))
    p, wlat = text_path("Sada", FONT_LATIN, 76, 170, 146, "#FFFFFF")
    body.append(p)
    p, _ = text_path("صدى", FONT_ARABIC, 52, 170 + wlat + 26, 144, AMBER, rtl=True)
    body.append(p)
    p, _ = text_path("Professional audio editor", FONT_LATIN_REGULAR, 21, 172, 184, "#FFFFFF", opacity=0.78)
    body.append(p)
    p, _ = text_path("Based on Audacity", FONT_LATIN_REGULAR, 15, 172, 210, "#FFFFFF", opacity=0.5)
    body.append(p)
    return svg(w, h, "".join(body), bg_defs + mark_defs())


def about_banner_svg():
    w, h = 1440, 288
    bg_defs, bg = graphite_bg(w, h)
    body = [bg, echo_decoration(1080, 144, [150, 260, 370, 480, 590], 26, 0.10)]
    body.append(mark_group(72, 60, 168))
    p, wlat = text_path("Sada", FONT_LATIN, 110, 270, 168, "#FFFFFF")
    body.append(p)
    p, _ = text_path("صدى", FONT_ARABIC, 76, 270 + wlat + 36, 166, AMBER, rtl=True)
    body.append(p)
    p, _ = text_path("Professional audio editor  ·  Based on Audacity", FONT_LATIN_REGULAR, 30, 274, 222,
                     "#FFFFFF", opacity=0.7)
    body.append(p)
    return svg(w, h, "".join(body), bg_defs + mark_defs())


def wix_banner_svg():
    w, h = 986, 116
    body = [f'<rect width="{w}" height="{h}" fill="#FFFFFF"/>', mark_group(876, 16, 84)]
    return svg(w, h, "".join(body), mark_defs())


def wix_dialog_svg():
    w, h = 986, 624
    bg_defs, bg = graphite_bg(324, h)
    bg_defs += '<clipPath id="leftpanel"><rect width="324" height="624"/></clipPath>'
    body = [f'<rect width="{w}" height="{h}" fill="#F7F7F7"/>', bg,
            '<g clip-path="url(#leftpanel)">' + echo_decoration(-40, 312, [180, 280, 380], 18, 0.08) + '</g>']
    body.append(mark_group(102, 196, 120))
    p, wlat = text_path("Sada", FONT_LATIN, 54, 162, 384, "#FFFFFF", anchor="middle")
    body.append(p)
    p, _ = text_path("صدى", FONT_ARABIC, 40, 162, 440, AMBER, rtl=True, anchor="middle")
    body.append(p)
    return svg(w, h, "".join(body), bg_defs + mark_defs())


# --------------------------------------------------------------------------
# Output helpers
# --------------------------------------------------------------------------
def write(path, text):
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(text)
    return full


def rasterize(svg_text, width, height):
    with tempfile.NamedTemporaryFile("w", suffix=".svg", delete=False, encoding="utf-8") as f:
        f.write(svg_text)
        tmp = f.name
    try:
        png = subprocess.run(["rsvg-convert", "-w", str(width), "-h", str(height), tmp],
                             check=True, capture_output=True).stdout
    finally:
        os.unlink(tmp)
    return Image.open(io.BytesIO(png)).convert("RGBA")


def save_png(img, path):
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    img.save(full, optimize=True)


def main():
    big = app_icon_svg(small=False)
    small = app_icon_svg(small=True)
    doc = doc_icon_svg()

    write("share/branding/sada_icon.svg", big)
    write("share/branding/sada_icon_small.svg", small)
    write("share/branding/sada_document_icon.svg", doc)
    write("share/icons/AppIcon/AppIcon.icon/Assets/Audacity.svg", big)
    write("share/icons/AupIcon/AU4_AupIcon.svg", doc)

    # App icon PNGs and ICO/ICNS (small sizes use the simplified mark)
    sizes = [16, 24, 32, 48, 64, 96, 128, 256, 512]
    icon_imgs = {}
    for s in sizes:
        icon_imgs[s] = rasterize(small if s <= 32 else big, s, s)
        save_png(icon_imgs[s], f"share/icons/AppIcon/AU4_AppIcon_{s}x{s}.png")
    ico_sizes = [16, 24, 32, 48, 64, 96, 128, 256]
    base = icon_imgs[256]
    base.save(os.path.join(ROOT, "share/icons/AppIcon/AU4_AppIcon.ico"), format="ICO",
              sizes=[(s, s) for s in ico_sizes],
              append_images=[icon_imgs[s] for s in ico_sizes if s != 256])
    icon_imgs[512].save(os.path.join(ROOT, "share/icons/AppIcon/AU4_AppIcon.icns"), format="ICNS")

    # Document (project file) icon
    doc_imgs = {s: rasterize(doc, s, s) for s in [16, 24, 32, 48, 64, 96, 128, 256, 512]}
    save_png(doc_imgs[512], "share/icons/AupIcon/AU4_AupIcon_512x512.png")
    doc_imgs[256].save(os.path.join(ROOT, "share/icons/AupIcon/AU4_AupIcon.ico"), format="ICO",
                       sizes=[(s, s) for s in ico_sizes],
                       append_images=[doc_imgs[s] for s in ico_sizes if s != 256])
    doc_imgs[512].save(os.path.join(ROOT, "share/icons/AupIcon/AU4_AupIcon.icns"), format="ICNS")

    # Full logo
    save_png(rasterize(big, 2048, 2048), "share/icons/audacity_logo_full.png")

    # Splash (kept as SVG; rendered by Qt at startup)
    write("src/appshell/resources/LoadingScreen.svg", splash_svg())

    # About banner
    save_png(rasterize(about_banner_svg(), 1440, 288), "src/appshell/resources/AboutBanner.png")

    # Installer images
    save_png(rasterize(wix_banner_svg(), 986, 116), "buildscripts/packaging/Windows/Installer/installer_banner_wix.png")
    save_png(rasterize(wix_dialog_svg(), 986, 624), "buildscripts/packaging/Windows/Installer/installer_background_wix.png")

    # Previews for review (not shipped)
    prev = os.environ.get("SADA_BRAND_PREVIEW_DIR")
    if prev:
        os.makedirs(prev, exist_ok=True)
        rasterize(splash_svg(), 800, 380).save(os.path.join(prev, "splash.png"))
        rasterize(wix_dialog_svg(), 986, 624).save(os.path.join(prev, "wix_dialog.png"))
        sheet = Image.new("RGBA", (16 + 24 + 32 + 48 + 64 + 128 + 256 + 9 * 16, 260), (40, 44, 50, 255))
        x = 8
        for s in [16, 24, 32, 48, 64, 128, 256]:
            sheet.alpha_composite(icon_imgs[s], (x, 2))
            x += s + 16
        sheet.save(os.path.join(prev, "icons.png"))
        doc_imgs[256].save(os.path.join(prev, "doc256.png"))
    print("Sada brand assets written")


if __name__ == "__main__":
    sys.exit(main())
