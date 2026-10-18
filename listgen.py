#!/usr/bin/env python3
"""
listgen.py — Reel de «lista» estilo Instagram: fondo (foto o clip) desenfocado y oscurecido + texto blanco
redondeado con borde negro, centrado, que aparece línea por línea. Sin audio (Jorge pone la música en la app).

Uso:
  python3 listgen.py spec.json salida.mp4 [--video clip.mp4]

spec.json:
{
  "photo": "fotos/x.jpg",          # fondo (o --video)
  "blur": 12, "dark": 0.6,          # desenfoque (px) y oscurecido (0-1) del fondo
  "width": 1000,                    # ancho del bloque de texto
  "duration": 13.0,
  "blocks": [                       # cada bloque aparece en el segundo t
    {"text": "La gente jura que…", "size": 58, "t": 0.4, "gap": 44},
    {"text": "$5.000.000 Arriendo", "size": 52, "t": 2.6, "gap": 6}
  ]
}
"""
import html
import io
import json
import os
import re
import subprocess
import sys
import tempfile

from PIL import Image, ImageFilter
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reelgen import video_frames, W, H, FPS  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "fonts")
EMOJI_RE = re.compile("([\U0001F1E6-\U0001F1FF\U0001F300-\U0001FAFF☀-➿⭐⬆↔-↪]+️?)")


def font_face():
    f900 = "file://" + os.path.join(FONT_DIR, "nunito-latin-900-normal.woff2")
    fext = "file://" + os.path.join(FONT_DIR, "nunito-latin-ext-900-normal.woff2")
    return (f"@font-face{{font-family:'Nunito';font-weight:900;src:url('{f900}') format('woff2');}}"
            f"@font-face{{font-family:'NunitoExt';font-weight:900;src:url('{fext}') format('woff2');}}")


def mark_emoji(text):
    esc = html.escape(text)
    return EMOJI_RE.sub(r"<span class='e'>\1</span>", esc)


def render_blocks(blocks, width=1000):
    imgs = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": width + 40, "height": 1400}, device_scale_factor=1)
        for b in blocks:
            size = int(b.get("size", 52))
            stroke = b.get("stroke", max(2.0, size / 22))
            page_html = f"""<!doctype html><html><head><meta charset='utf-8'><style>
              {font_face()}
              html,body{{margin:0;padding:0;background:transparent;}}
              #b{{width:{width}px;padding:2px 0;text-align:center;font-family:'Nunito','NunitoExt','Inter',sans-serif;font-weight:900;
                  font-size:{size}px;line-height:1.18;color:#fff;letter-spacing:.2px;
                  -webkit-text-stroke:{stroke}px #000;paint-order:stroke fill;
                  text-shadow:0 2px 2px rgba(0,0,0,.55), 0 4px 14px rgba(0,0,0,.45);}}
              .e{{-webkit-text-stroke:0;font-family:'Noto Color Emoji';text-shadow:none;}}
            </style></head><body><div id='b'>{mark_emoji(b['text'])}</div></body></html>"""
            with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
                f.write(page_html); tmp = f.name
            page.goto("file://" + tmp); page.wait_for_timeout(150)
            png = page.query_selector("#b").screenshot(omit_background=True)
            os.unlink(tmp)
            imgs.append(Image.open(io.BytesIO(png)).convert("RGBA"))
        browser.close()
    return imgs


def bg_from_photo(photo_path, blur=12, dark=0.6, zoom=1.12):
    photo = Image.open(photo_path).convert("RGB")
    pw, ph = photo.size
    bw, bh = int(W * zoom), int(H * zoom)
    scale = max(bw / pw, bh / ph)
    big = photo.resize((int(pw * scale) + 1, int(ph * scale) + 1), Image.LANCZOS)
    x0, y0 = (big.width - bw) // 2, (big.height - bh) // 2
    big = big.crop((x0, y0, x0 + bw, y0 + bh)).filter(ImageFilter.GaussianBlur(blur))
    return Image.eval(big, lambda v: int(v * dark))


def alpha_scaled(img, a):
    if a >= 1:
        return img
    c = img.copy(); c.putalpha(Image.eval(img.split()[3], lambda v: int(v * a))); return c


def build(spec, out_path, video_path=None):
    dur = float(spec.get("duration", 13.0))
    total = int(dur * FPS)
    width = int(spec.get("width", 1000))
    blocks = spec["blocks"]
    imgs = render_blocks(blocks, width)
    gaps = [int(b.get("gap", 6)) for b in blocks]
    stack_h = sum(im.height for im in imgs) + sum(gaps[:-1])
    y = int(spec.get("top", (H - stack_h) // 2))
    ys = []
    for im, g in zip(imgs, gaps):
        ys.append(y); y += im.height + g
    x0 = (W - width) // 2

    if video_path:
        src = video_frames(video_path, total, float(spec.get("video_start", 0)))
        blur = int(spec.get("blur", 12)); dark = float(spec.get("dark", 0.6))
        frames = (Image.eval(f.filter(ImageFilter.GaussianBlur(blur)) if blur > 0 else f, lambda v: int(v * dark)) for f in src)
    else:
        big = bg_from_photo(spec["photo"], int(spec.get("blur", 12)), float(spec.get("dark", 0.6)))
        def _frames():
            for i in range(total):
                p = i / max(1, total - 1)
                x = int((big.width - W) * p); yy = (big.height - H) // 2
                yield big.crop((x, yy, x + W, yy + H))
        frames = _frames()

    tmpdir = tempfile.mkdtemp(); raw = os.path.join(tmpdir, "frames.rgb")
    with open(raw, "wb") as fh:
        for i, frame in enumerate(frames):
            t = i / FPS
            fr = frame.convert("RGBA")
            for b, im, yb in zip(blocks, imgs, ys):
                tb = float(b.get("t", 0))
                if t < tb:
                    continue
                p = min(1.0, (t - tb) / 0.28)
                fr.alpha_composite(alpha_scaled(im, p), (x0, yb + int((1 - p) * 18)))
            fh.write(fr.convert("RGB").tobytes())
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", raw,
                    "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.1", "-an", "-movflags", "+faststart", out_path], check=True)
    os.unlink(raw); os.rmdir(tmpdir)
    return out_path, stack_h


if __name__ == "__main__":
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    video = sys.argv[sys.argv.index("--video") + 1] if "--video" in sys.argv else None
    path, h = build(spec, sys.argv[2], video)
    print(path, f"stack {h}px")
