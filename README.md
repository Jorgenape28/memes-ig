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

## Generar un meme
```
python3 memegen.py spec.json out/2026-10-20_slug.jpg
```
`spec.json` = `{"photo": "fotos/x.jpg", "focus_y": 0.35, "notifications": [...]}` (ver `banco.json`).
Tipos de notificación: `text` (por defecto), `audio` (`duration`), `photo`, `doc`, `missed`.
Avatar: `avatar` (ruta), o `initials` + `color`, o nada (silueta).

## Publicar como anuncio (Windsor.ai → Meta Ads, cuenta 911008968626641)
1. Subir el jpg a `out/` y hacer push (queda público en raw.githubusercontent.com).
2. `execute_action(connector="facebook", account="911008968626641", action="create_ad", params={...})`
   con `creative.object_story_spec` = `page_id` 279376278597962, `instagram_user_id` 17841400796794613,
   `link_data` con `picture` = URL raw, `link` = https://www.instagram.com/jorgenape28/, `message` = texto.
3. Dejar el anuncio en pausa hasta revisar; `enable_ad` para activarlo.
4. Registrar en `estado.json` y marcar el escenario como `publicado` en `banco.json`.
