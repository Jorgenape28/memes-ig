#!/usr/bin/env python3
"""
memegen.py — Genera un meme "selfie + notificaciones de WhatsApp" (formato 4:5, 1080x1350).

Uso:
  python3 memegen.py spec.json salida.jpg

spec.json:
{
  "photo": "ruta/a/la/foto.jpg",
  "focus_y": 0.35,                 # punto focal vertical del recorte (0 arriba, 1 abajo)
  "top": 520, "width": 800, "card_h": 150, "gap": 18,   # layout opcional
  "notifications": [
    {"name": "Prestamista", "msg": "Me paga hoy o lo estallo.", "time": "11:28 a.m.",
     "avatar": "ruta/avatar.jpg" | null, "type": "text" | "audio" | "photo" | "doc",
     "badge": "whatsapp" }
  ]
}
"""
import base64
import html
import json
import os
import sys
import tempfile

from playwright.sync_api import sync_playwright

W, H = 1080, 1350

WA_PATH = ("M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 "
           "1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297"
           "-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149"
           "-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297"
           "-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625"
           ".712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198"
           "-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 "
           "01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 "
           "5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 "
           "4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 "
           "11.821 0 00-3.48-8.413Z")

# Silueta por defecto (estilo iOS/WhatsApp: círculo gris con persona blanca)
SILHOUETTE_SVG = """<svg viewBox='0 0 100 100' xmlns='http://www.w3.org/2000/svg'>
<circle cx='50' cy='50' r='50' fill='#dfe3e8'/>
<circle cx='50' cy='38' r='17' fill='#fff'/>
<path d='M18 92c4-20 17-30 32-30s28 10 32 30z' fill='#fff'/>
</svg>"""


def data_uri(path):
    ext = os.path.splitext(path)[1].lower()
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp", "svg": "image/svg+xml"}.get(ext.strip("."), "image/jpeg")
    with open(path, "rb") as f:
        return f"data:{mime};base64," + base64.b64encode(f.read()).decode()


def svg_uri(svg):
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


def msg_html(n):
    t = n.get("type", "text")
    msg = html.escape(n.get("msg", ""))
    if t == "audio":
        dur = html.escape(n.get("duration", "0:32"))
        return (f"<span class='ico mic'><svg viewBox='0 0 24 24'><path d='M12 15a4 4 0 0 0 4-4V6a4 4 0 0 0-8 0v5a4 4 0 0 0 4 4zm6-4a6 6 0 0 1-12 0H4a8 8 0 0 0 7 7.93V22h2v-3.07A8 8 0 0 0 20 11z'/></svg></span>"
                f"Audio ({dur})")
    if t == "photo":
        return (f"<span class='ico cam'><svg viewBox='0 0 24 24'><path d='M9 3 7.2 5H4a2 2 0 0 0-2 2v11a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-3.2L15 3zm3 5.5A4.5 4.5 0 1 1 7.5 13 4.5 4.5 0 0 1 12 8.5z'/></svg></span>"
                f"Foto{(' ' + msg) if msg else ''}")
    if t == "doc":
        return (f"<span class='ico doc'><svg viewBox='0 0 24 24'><path d='M6 2h8l6 6v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2zm7 1.5V9h5.5z'/></svg></span>"
                f"{msg}")
    if t == "missed":
        return (f"<span class='ico missed'><svg viewBox='0 0 24 24'><path d='M6.6 10.8a15 15 0 0 0 6.6 6.6l2.2-2.2a1 1 0 0 1 1-.25 11.4 11.4 0 0 0 3.6.57 1 1 0 0 1 1 1V20a1 1 0 0 1-1 1A17 17 0 0 1 3 4a1 1 0 0 1 1-1h3.5a1 1 0 0 1 1 1 11.4 11.4 0 0 0 .57 3.6 1 1 0 0 1-.25 1z'/></svg></span>"
                f"Llamada perdida")
    return msg


def build_html(spec):
    photo = data_uri(spec["photo"])
    focus_y = float(spec.get("focus_y", 0.35)) * 100
    top = int(spec.get("top", 520))
    width = int(spec.get("width", 800))
    card_h = int(spec.get("card_h", 150))
    gap = int(spec.get("gap", 18))
    left = (W - width) // 2
    cards = []
    for n in spec["notifications"]:
        av = n.get("avatar")
        if av and os.path.exists(av):
            av_uri = data_uri(av)
        elif n.get("initials"):
            col = n.get("color", "#2f6fed")
            ini = html.escape(n["initials"][:2])
            av_uri = svg_uri(f"<svg viewBox='0 0 100 100' xmlns='http://www.w3.org/2000/svg'><circle cx='50' cy='50' r='50' fill='{col}'/><text x='50' y='50' dy='.36em' text-anchor='middle' font-family='Inter, Arial, sans-serif' font-weight='700' font-size='44' fill='#fff'>{ini}</text></svg>")
        else:
            av_uri = svg_uri(SILHOUETTE_SVG)
        badge = n.get("badge", "whatsapp")
        badge_html = ""
        if badge == "whatsapp":
            badge_html = f"<span class='badge'><svg viewBox='0 0 24 24'><path d='{WA_PATH}' fill='#fff'/></svg></span>"
        cards.append(f"""
        <div class='card'>
          <div class='av'><img src='{av_uri}'/>{badge_html}</div>
          <div class='body'>
            <div class='row'><span class='name'>{html.escape(n['name'])}</span><span class='time'>{html.escape(n.get('time',''))}</span></div>
            <div class='msg'>{msg_html(n)}</div>
          </div>
        </div>""")
    cards_html = "\n".join(cards)
    return f"""<!doctype html><html><head><meta charset='utf-8'>
<style>
  html,body{{margin:0;padding:0;width:{W}px;height:{H}px;overflow:hidden;background:#000;}}
  .wrap{{position:relative;width:{W}px;height:{H}px;overflow:hidden;}}
  .photo{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:50% {focus_y}%;}}
  .stack{{position:absolute;left:{left}px;top:{top}px;width:{width}px;display:flex;flex-direction:column;gap:{gap}px;}}
  .card{{min-height:{card_h}px;padding-top:18px;padding-bottom:18px;border-radius:40px;background:rgba(246,246,248,.82);
        backdrop-filter:blur(34px) saturate(1.4);-webkit-backdrop-filter:blur(34px) saturate(1.4);
        box-shadow:0 10px 30px rgba(0,0,0,.22), inset 0 0 0 1px rgba(255,255,255,.45);
        display:flex;align-items:center;padding:0 36px 0 30px;box-sizing:border-box;
        font-family:'Inter Display','Inter',-apple-system,'SF Pro Display','Helvetica Neue',Arial,sans-serif;}}
  .av{{position:relative;width:86px;height:86px;flex:0 0 86px;margin-right:26px;}}
  .av img{{width:86px;height:86px;border-radius:50%;object-fit:cover;display:block;}}
  .badge{{position:absolute;right:-6px;bottom:-4px;width:38px;height:38px;border-radius:50%;background:#25D366;
          display:flex;align-items:center;justify-content:center;box-shadow:0 0 0 3px rgba(246,246,248,.9);}}
  .badge svg{{width:24px;height:24px;}}
  .body{{flex:1;min-width:0;}}
  .row{{display:flex;align-items:baseline;justify-content:space-between;}}
  .name{{font-size:37px;font-weight:700;color:#111;letter-spacing:-.3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}}
  .time{{font-size:25px;color:#6b6b70;margin-left:18px;white-space:nowrap;font-weight:500;}}
  .msg{{font-size:32px;color:#1c1c1e;margin-top:4px;line-height:1.22;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;word-break:break-word;}}
  .msg .ico{{vertical-align:-6px;}}
  .ico{{display:inline-block;width:32px;height:32px;margin-right:8px;}}
  .ico svg{{width:32px;height:32px;}}
  .mic svg{{fill:#1fb55f;}} .cam svg{{fill:#5a5a60;}} .doc svg{{fill:#5a5a60;}} .missed svg{{fill:#e03b3b;}}
</style></head><body><div class='wrap'>
  <img class='photo' src='{photo}'/>
  <div class='stack'>{cards_html}</div>
</div></body></html>"""


def render(spec, out_path):
    page_html = build_html(spec)
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(page_html)
        tmp = f.name
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        page.goto("file://" + tmp)
        page.wait_for_timeout(400)
        if out_path.lower().endswith((".jpg", ".jpeg")):
            page.screenshot(path=out_path, type="jpeg", quality=92, clip={"x": 0, "y": 0, "width": W, "height": H})
        else:
            page.screenshot(path=out_path, type="png", clip={"x": 0, "y": 0, "width": W, "height": H})
        browser.close()
    os.unlink(tmp)
    return out_path


if __name__ == "__main__":
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    print(render(spec, sys.argv[2]))
