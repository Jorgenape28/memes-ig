# memes-ig — creativos para anuncios de Instagram (@jorgenape28)

Memes de "situaciones absurdas": selfie seria + notificaciones de WhatsApp apiladas.
Se publican **solo como anuncios** (dark posts) en la cuenta publicitaria personal de Jorge,
con la identidad de @jorgenape28. **No aparecen en la cuadrícula del perfil.**

## Archivos
- `memegen.py` — generador (HTML → captura con Chromium/Playwright). 1080×1350 (4:5).
- `banco.json` — banco de escenarios (`estado`: pendiente / renderizado / publicado).
- `estado.json` — ids de Meta (cuenta, página, IG), campaña, conjunto y anuncios publicados.
- `fotos/` — selfies de Jorge (cara seria). Entre más variadas, mejor.
- `out/` — memes renderizados `AAAA-MM-DD_slug.jpg`. Sirven como URL pública para Meta:
  `https://raw.githubusercontent.com/Jorgenape28/memes-ig/main/out/<archivo>`
- `avatares/` — fotos de perfil ficticias para las notificaciones (opcional).

## Formato oficial: REEL (desde el 16-oct)
```
python3 reelgen.py spec.json out/AAAA-MM-DD_slug_reel.mp4            # con foto (zoom lento)
python3 reelgen.py spec.json out/AAAA-MM-DD_slug_reel.mp4 --video clip.mp4   # con un clip de Jorge
ffmpeg -sseof -0.5 -i out/X_reel.mp4 -frames:v 1 -q:v 2 out/X_reel_cover.jpg  # portada
```
Anuncio en video (Windsor): `create_ad_video` con la URL raw del mp4 → `video_id`; luego `create_ad` con
`creative.object_story_spec.video_data` = {video_id, image_url (portada raw), message, call_to_action VIEW_INSTAGRAM_PROFILE} más page_id e instagram_user_id.

## Generar un meme (imagen fija, solo portada)
```
python3 memegen.py spec.json out/2026-10-20_slug.jpg
```
`spec.json` = `{"photo": "fotos/x.jpg", "focus_y": 0.35, "notifications": [...]}` (ver `banco.json`).
Tipos de notificación: `text` (por defecto), `audio` (`duration`), `photo`, `doc`, `missed`.
Avatar: `avatar` (ruta), o `initials` + `color`, o nada (silueta).

## Campaña (creada 16-oct-2026, activa)
- Campaña 120252917299480220 · objetivo: visitas al perfil (proxy de seguidores).
- Conjunto «Mujeres 24-40» 120252917300730220 · COP 14.000/día (70 %).
- Conjunto «Todos 20-45» 120252917534040220 · COP 6.000/día (30 %).
- Cada meme se publica como un anuncio en cada conjunto. Nada se publica sin el OK de Jorge.

## Publicar como anuncio (Windsor.ai → Meta Ads, cuenta 911008968626641)
1. Subir el jpg a `out/` y hacer push (queda público en raw.githubusercontent.com).
2. `execute_action(connector="facebook", account="911008968626641", action="create_ad", params={...})`
   con `creative.object_story_spec` = `page_id` 279376278597962, `instagram_user_id` 17841400796794613,
   `link_data` con `picture` = URL raw, `link` = https://www.instagram.com/jorgenape28/, `message` = texto.
3. Dejar el anuncio en pausa hasta revisar; `enable_ad` para activarlo.
4. Registrar en `estado.json` y marcar el escenario como `publicado` en `banco.json`.
