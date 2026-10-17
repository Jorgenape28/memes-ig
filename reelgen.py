#!/usr/bin/env python3
"""
reelgen.py — Convierte un meme de notificaciones en un reel vertical (1080x1920, 30 fps, H.264 + audio).

Uso:
  python3 reelgen.py spec.json salida.mp4 [--video clip.mp4]

spec.json es el mismo formato que memegen.py ({"photo": ..., "notifications": [...]}).
Si se pasa --video, el fondo es ese clip (se recorta/escala a 9:16 y se usan sus primeros N segundos);
si no, se usa la foto con un zoom lento y fondo desenfocado.

Tiempos: cada notificación entra a partir de t0 con intervalo `gap` (segundos) y suena un «ding».
"""
import base64
import html
import json
import math
import os
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image, ImageFilter
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from memegen import WA_PATH, SILHOUETTE_SVG, data_uri, svg_uri, msg_html  # noqa: E402

W, H = 1080, 1920
FPS = 30
CARD_W = 860


def card_html(n):
    av = n.get("avatar")
    if av and os.path.exists(av):
        av_uri = data_uri(av)
    elif n.get("initials"):
        col = n.get("color", "#2f6fed")
        ini = html.escape(n["initials"][:2])
        av_uri = svg_uri(f"<svg viewBox='0 0 100 100' xmlns='http://www.w3.org/2000/svg'><circle cx='50' cy='50' r='50' fill='{col}'/><text x='50' y='50' dy='.36em' text-anchor='middle' font-family='Inter, Arial, sans-serif' font-weight='700' font-size='44' fill='#fff'>{ini}</text></svg>")
    else:
        av_uri = svg_uri(SILHOUETTE_SVG)
    badge = f"<span class='badge'><svg viewBox='0 0 24 24'><path d='{WA_PATH}' fill='#fff'/></svg></span>" if n.get("badge", "whatsapp") == "whatsapp" else ""
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>
  html,body{{margin:0;padding:0;background:transparent;}}
  .card{{width:{CARD_W}px;min-height:160px;border-radius:42px;background:rgba(246,246,248,.90);
        box-shadow:0 12px 34px rgba(0,0,0,.28), inset 0 0 0 1px rgba(255,255,255,.5);
        display:flex;align-items:center;padding:18px 38px 18px 32px;box-sizing:border-box;
        font-family:'Inter Display','Inter',-apple-system,'SF Pro Display','Helvetica Neue',Arial,sans-serif;}}
  .av{{position:relative;width:92px;height:92px;flex:0 0 92px;margin-right:28px;}}
  .av img{{width:92px;height:92px;border-radius:50%;object-fit:cover;display:block;}}
  .badge{{position:absolute;right:-6px;bottom:-4px;width:40px;height:40px;border-radius:50%;background:#25D366;display:flex;align-items:center;justify-content:center;box-shadow:0 0 0 3px rgba(246,246,248,.95);}}
  .badge svg{{width:25px;height:25px;}}
  .body{{flex:1;min-width:0;}}
  .row{{display:flex;align-items:baseline;justify-content:space-between;}}
  .name{{font-size:40px;font-weight:700;color:#111;letter-spacing:-.3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}}
  .time{{font-size:27px;color:#6b6b70;margin-left:18px;white-space:nowrap;font-weight:500;}}
  .msg{{font-size:35px;color:#1c1c1e;margin-top:4px;line-height:1.22;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;word-break:break-word;}}
  .ico{{display:inline-block;width:34px;height:34px;margin-right:8px;vertical-align:-6px;}} .ico svg{{width:34px;height:34px;}}
  .mic svg{{fill:#1fb55f;}} .cam svg{{fill:#5a5a60;}} .doc svg{{fill:#5a5a60;}} .missed svg{{fill:#e03b3b;}}
</style></head><body><div class='card' id='card'>
  <div class='av'><img src='{av_uri}'/>{badge}</div>
  <div class='body'><div class='row'><span class='name'>{html.escape(n['name'])}</span><span class='time'>{html.escape(n.get('time',''))}</span></div>
  <div class='msg'>{msg_html(n)}</div></div></div></body></html>"""


def render_cards(notifications):
    cards = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": CARD_W + 80, "height": 400}, device_scale_factor=1)
        for n in notifications:
            with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
                f.write(card_html(n)); tmp = f.name
            page.goto("file://" + tmp); page.wait_for_timeout(250)
            el = page.query_selector("#card")
            png = el.screenshot(omit_background=True)
            os.unlink(tmp)
            img = Image.open(__import__("io").BytesIO(png)).convert("RGBA")
            cards.append(img)
        browser.close()
    return cards


def ding(sr=44100, dur=0.55):
    """Campanita corta tipo notificación (dos tonos con caída)."""
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    env = np.exp(-t * 7.0)
    s = 0.55 * np.sin(2 * np.pi * 1318.5 * t) * env + 0.45 * np.sin(2 * np.pi * 1760.0 * t) * np.exp(-t * 9.0)
    s[: int(sr * 0.004)] *= np.linspace(0, 1, int(sr * 0.004))
    return (s / np.max(np.abs(s)) * 0.6).astype(np.float32)


def ease_out_back(x, s=1.4):
    return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2


def make_bg_frames_from_photo(photo_path, total_frames, zoom=0.07, anchor="center"):
    photo = Image.open(photo_path).convert("RGB")
    pw, ph = photo.size
    # fondo desenfocado 9:16
    scale = max(W / pw, H / ph)
    bg = photo.resize((int(pw * scale) + 2, int(ph * scale) + 2), Image.LANCZOS)
    bx, by = (bg.width - W) // 2, (bg.height - H) // 2
    bg = bg.crop((bx, by, bx + W, by + H)).filter(ImageFilter.GaussianBlur(40))
    bg = Image.eval(bg, lambda v: int(v * 0.62))
    # foto nítida a lo ancho, centrada; zoom lento hacia su centro
    base_w = W
    base_h = int(ph * (W / pw))
    for i in range(total_frames):
        z = 1 + zoom * (i / max(1, total_frames - 1))
        fw, fh = int(base_w * z), int(base_h * z)
        fr = photo.resize((fw, fh), Image.BILINEAR)
        cx, cy = fw // 2, int(fh * 0.42)
        left, top = cx - W // 2, cy - min(fh, H) // 2
        left = max(0, min(left, fw - W)); top = max(0, min(top, max(0, fh - min(fh, H))))
        crop = fr.crop((left, top, left + W, top + min(fh, H)))
        frame = bg.copy()
        y_off = {"center": (H - crop.height) // 2, "bottom": H - crop.height, "top": 0}[anchor]
        frame.paste(crop, (0, y_off))
        yield frame


def build(spec, out_path, video_path=None, t0=0.9, gap=1.25, hold=2.6, bg_seconds=None):
    notes = spec["notifications"]
    cards = render_cards(notes)
    n = len(notes)
    duration = t0 + gap * (n - 1) + hold
    total = int(duration * FPS)

    # posiciones: pila centrada verticalmente alrededor del 62 % de la altura
    gap_px = 22
    stack_h = sum(c.height for c in cards) + gap_px * (n - 1)
    top0 = int(H * 0.60) - stack_h // 2
    ys = []
    y = top0
    for c in cards:
        ys.append(y); y += c.height + gap_px
    x0 = (W - CARD_W) // 2

    if video_path:
        frames = video_frames(video_path, total)
    else:
        frames = make_bg_frames_from_photo(spec["photo"], total)

    tmpdir = tempfile.mkdtemp()
    raw = os.path.join(tmpdir, "frames.rgb")
    with open(raw, "wb") as fh:
        for i, frame in enumerate(frames):
            t = i / FPS
            fr = frame.convert("RGBA")
            for k, c in enumerate(cards):
                tk = t0 + gap * k
                if t < tk:
                    continue
                p = min(1.0, (t - tk) / 0.42)
                e = ease_out_back(p)
                dy = int((1 - e) * -90)
                alpha = min(1.0, p / 0.35)
                layer = c if alpha >= 1 else Image.eval(c.split()[3], lambda v: int(v * alpha))
                if alpha < 1:
                    cc = c.copy(); cc.putalpha(layer); layer = cc
                else:
                    layer = c
                fr.alpha_composite(layer, (x0, ys[k] + dy))
            fh.write(fr.convert("RGB").tobytes())

    # audio: dings en los tiempos de entrada
    sr = 44100
    audio = np.zeros(int(duration * sr) + sr, dtype=np.float32)
    d = ding(sr)
    for k in range(n):
        s = int((t0 + gap * k) * sr)
        audio[s:s + len(d)] += d
    audio = np.clip(audio[: int(duration * sr)], -1, 1)
    wav = os.path.join(tmpdir, "audio.wav")
    import wave, struct
    with wave.open(wav, "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
        wf.writeframes((audio * 32767).astype(np.int16).tobytes())

    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", raw,
           "-i", wav,
           "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.1",
           "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", "-shortest", out_path]
    subprocess.run(cmd, check=True)
    os.unlink(raw); os.unlink(wav); os.rmdir(tmpdir)
    return out_path, duration


def video_frames(video_path, total):
    """Frames 9:16 de un clip (escala y recorta al centro), en bucle si es más corto."""
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", video_path], capture_output=True, text=True).stdout.strip().split(",")
    vw, vh = int(probe[0]), int(probe[1])
    scale = max(W / vw, H / vh)
    sw, sh = int(vw * scale + 1), int(vh * scale + 1)
    cmd = ["ffmpeg", "-loglevel", "error", "-stream_loop", "-1", "-i", video_path, "-vf", f"scale={sw}:{sh},crop={W}:{H}", "-r", str(FPS), "-frames:v", str(total), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    size = W * H * 3
    while True:
        buf = proc.stdout.read(size)
        if len(buf) < size:
            break
        yield Image.frombytes("RGB", (W, H), buf)
    proc.stdout.close(); proc.wait()


if __name__ == "__main__":
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    out = sys.argv[2]
    video = None
    if "--video" in sys.argv:
        video = sys.argv[sys.argv.index("--video") + 1]
    path, dur = build(spec, out, video)
    print(path, f"{dur:.1f}s")
