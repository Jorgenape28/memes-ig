# Tarea programada · Memes IG (martes y viernes, 8:52 a. m. Bogotá)

Creada el 16-oct-2026 a las 20:22 (id trig_01RF6ScAX2cKeJoq6EepN13c) con el «listo» de Jorge. Primera corrida: martes 20 de octubre, 8:52 a. m.
**Cambio del 16-oct (20:00):** Jorge quiere aprobar cada meme. La tarea solo PROPONE: genera el siguiente meme, lo sube al repo y se lo manda a Jorge; se publica (un anuncio en cada conjunto: Mujeres 120252917300730220 y Todos 120252917534040220) únicamente cuando Jorge responde «publica».
Cron: `CRON_TZ=America/Bogota 52 8 * * 2,5` · notificación push · no requiere el Mac.

## Instrucción de cada corrida

Eres el asistente de Jorge Andrés Peña (jps2abogados@gmail.com). Encargo del 16 de octubre de 2026: publicar memes de «situaciones absurdas» (selfie seria de Jorge + notificaciones de WhatsApp apiladas) como anuncios de Instagram, es decir dark posts que NO aparecen en la cuadrícula de @jorgenape28, una o dos veces por semana, pagando la pauta con Windsor.ai. Jorge pidió «cero uso de las manos»: haz todo tú y escríbele solo lo esencial, en español, de tú.

DATOS FIJOS
- Repositorio GitHub público Jorgenape28/memes-ig: memegen.py, banco.json, estado.json, fotos/, out/. Todo archivo de out/ queda público en https://raw.githubusercontent.com/Jorgenape28/memes-ig/main/out/<archivo>
- Meta vía Windsor (connector "facebook"): cuenta 911008968626641, página 279376278597962, instagram_user_id 17841400796794613. Campaña 120252917299480220 (OUTCOME_TRAFFIC). Conjunto 120252917300730220 (COP 20.000/día, Colombia 18-45, solo Instagram, VISIT_INSTAGRAM_PROFILE, destino INSTAGRAM_PROFILE). Creados en pausa el 16-oct.
- Rotación: cada anuncio vive 14 días; máximo 4 activos; el presupuesto es del conjunto.

PASOS
1) add_repo (Jorgenape28/memes-ig, push) y `git clone --depth 1 https://github.com/Jorgenape28/memes-ig /home/claude/memes-ig`. Leer estado.json y banco.json.
2) Elegir meme: si no hay anuncios publicados, usar lunes-abogado (ya renderizado). Si no, el siguiente «renderizado»; si no queda, el primer «pendiente»: generar con `python3 memegen.py spec.json out/AAAA-MM-DD_<slug>.jpg` usando una selfie distinta a la anterior, y revisar el jpg con Read.
3) Commit y push (user.name "Jorge Andrés Peña", user.email jps2abogados@gmail.com). Verificar con `gh api repos/Jorgenape28/memes-ig/contents/out`.
4) Windsor execute_action create_ad (ver README para el objeto creative: object_story_spec con page_id, instagram_user_id, link_data con picture = URL raw, link = perfil de Instagram, call_to_action VIEW_INSTAGRAM_PROFILE; opt-out de mejoras automáticas). status "active". Si «Ningún método de pago» (1359188): avisar a Jorge (https://business.facebook.com/billing_hub/payment_settings/?asset_id=911008968626641) y terminar.
5) Activar campaña y conjunto si siguen en pausa (enable_campaign, enable_adset). Pausar anuncios con más de 14 días (pause_ad).
6) Actualizar estado.json y banco.json; commit y push.
7) Martes: Windsor get_data (facebook, cuenta 911008968626641, last_7d, fields date, ad_id, ad_name, spend, impressions, reach, instagram_profile_visits, clicks) → gasto, alcance, visitas al perfil y costo por visita por anuncio (referencia: COP 123 por visita en la promoción anterior).
8) Mensaje a Jorge en 4-6 líneas: meme publicado (slug + enlace), id del anuncio, qué se pausó, y los martes el resumen semanal. Si falló algo, 2 líneas con la causa.

REGLAS: sin cambios de presupuesto ni segmentación sin OK de Jorge; solo anuncios (nunca publicar en el perfil); sin groserías, drogas, marcas ni logos reales; si el banco se agota, inventar 4 escenarios nuevos en el mismo estilo y añadirlos antes de publicar; si Windsor falla por autorización o plan vencido, avisar en una línea y terminar.
