#!/usr/bin/env python3
"""
quotegen.py — Reel «me convenció»: foto/clip de Jorge serio + texto grande (la excusa del cliente) + remate abajo.
Sin audio (Jorge pone la música en la app).

Uso:
  python3 quotegen.py spec.json salida.mp4 [--video clip.mp4]

spec.json:
{
  "photo": "fotos/x.jpg",
  "label": "Cliente:",
  "quote": "Doctor, yo no me robé la moto. Estaba sola y me dio pesar.",
  "punch": "No sé ustedes, pero a mí me convenció.",
  "duration": 9.0
}
"""
import html
import io
import json
import os
import subprocess
import sys
import tempfile

from PIL import Image
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reelgen import make_bg_frames_from_photo, video_frames, ease_out_back, W, H, FPS  # noqa: E402


def render_block(inner_html, width=960):
    page_html = f"""<!doctype html><html><head><meta charset='utf-8'><style>
      html,body{{margin:0;padding:0;background:transparent;}}
      #b{{width:{width}px;font-family:'Inter Display','Inter',-apple-system,'Helvetica Neue',Arial,sans-serif;color:#fff;
          text-shadow:0 2px 6px rgba(0,0,0,.75), 0 0 28px rgba(0,0,0,.55);}}
      .label{{display:inline-block;background:#ffd400;color:#111;font-weight:800;font-size:40px;padding:8px 22px;border-radius:14px;text-shadow:none;margin-bottom:22px;letter-spacing:.5px;}}
      .quote{{font-weight:800;font-size:78px;line-height:1.12;letter-spacing:-1px;}}
      .punch{{font-weight:700;font-size:58px;line-height:1.15;background:rgba(0,0,0,.55);padding:22px 30px;border-radius:22px;display:inline-block;text-shadow:none;}}
    </style></head><body><div id='b'>{inner_html}</div></body></html>"""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": width + 40, "height": 1200}, device_scale_factor=1)
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
            f.write(page_html); tmp = f.name
        page.goto("file://" + tmp); page.wait_for_timeout(200)
        png = page.query_selector("#b").screenshot(omit_background=True)
        browser.close(); os.unlink(tmp)
    return Image.open(io.BytesIO(png)).convert("RGBA")


def alpha_scaled(img, a):
    if a >= 1:
        return img
    c = img.copy(); c.putalpha(Image.eval(img.split()[3], lambda v: int(v * a))); return c


def build(spec, out_path, video_path=None):
    dur = float(spec.get("duration", 9.0))
    total = int(dur * FPS)
    top = render_block(f"<div class='label'>{html.escape(spec.get('label', 'Cliente:'))}</div><div class='quote'>{html.escape(spec['quote'])}</div>")
    punch = render_block(f"<div class='punch'>{html.escape(spec['punch'])}</div>")
    t_top, t_punch = 0.5, float(spec.get("punch_at", dur - 2.8))
    frames = video_frames(video_path, total) if video_path else make_bg_frames_from_photo(spec["photo"], total, zoom=0.08, anchor=spec.get("anchor", "bottom"))
    tmpdir = tempfile.mkdtemp(); raw = os.path.join(tmpdir, "frames.rgb")
    with open(raw, "wb") as fh:
        for i, frame in enumerate(frames):
            t = i / FPS
            fr = frame.convert("RGBA")
            # oscurecer un poco arriba y abajo para legibilidad
            if i == 0:
                grad = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                px = grad.load()
                for y in range(H):
                    a = 0
                    if y < 700: a = int(170 * (1 - y / 700))
                    elif y > H - 600: a = int(120 * ((y - (H - 600)) / 600))
                    for x in range(0, W):
                        px[x, y] = (0, 0, 0, a)
            fr.alpha_composite(grad)
            if t >= t_top:
                p = min(1.0, (t - t_top) / 0.45); e = ease_out_back(p, 1.2)
                fr.alpha_composite(alpha_scaled(top, min(1, p / 0.3)), ((W - top.width) // 2, int(spec.get('quote_y', 90) + (1 - e) * 40)))
            if t >= t_punch:
                p = min(1.0, (t - t_punch) / 0.4)
                fr.alpha_composite(alpha_scaled(punch, min(1, p / 0.3)), ((W - punch.width) // 2, int(spec.get('punch_y', H - 420) - punch.height // 2 + (1 - p) * 30)))
            fh.write(fr.convert("RGB").tobytes())
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", raw,
                    "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.1", "-an", "-movflags", "+faststart", out_path], check=True)
    os.unlink(raw); os.rmdir(tmpdir)
    return out_path


if __name__ == "__main__":
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    video = sys.argv[sys.argv.index("--video") + 1] if "--video" in sys.argv else None
    print(build(spec, sys.argv[2], video))
