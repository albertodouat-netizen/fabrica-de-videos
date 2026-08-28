# 🤖 Fábrica de Videos de YouTube — Equipo de Agentes IA (100% Gratis)

## 🔧 AUDITORÍA CORRIDA 27-ago (4h46m, "falló") + 3 CORRECCIONES (28-ago-2026)
LO PRIMERO: el video SÍ se generó y SÍ se subió. La corrida de anoche
publicó "Dormir con Lluvia de Tres Minutos" (largo 19:21 + Short) como
PRIVADOS PROGRAMADOS para hoy 19:30 UTC (la función de hora pico
funcionando a la perfección). La ✗ roja fue solo del paso de guardar
respaldo. Hallazgos y correcciones:
1. **Error real: "Artifact storage quota has been hit"** — guardábamos el
   VIDEO COMPLETO (200-500 MB) de cada corrida por 14 días y los 500 MB
   gratis de GitHub se agotaron. Ahora solo se respaldan memoria +
   miniatura + logs (KBs), 5 días. (El video vive en YouTube; no hace
   falta duplicarlo en GitHub.)
2. **4h46m de corrida**: causa principal = DOBLE codificación (cada
   capítulo se renderizaba a .mp4 y luego el video entero se
   RE-codificaba al unirlo). Ahora la unión es ffmpeg concat con copia de
   streams (segundos) y la música se mezcla re-codificando SOLO el audio.
   Probado en vivo con mini-render: duración y mezcla correctas.
   Estimación nueva de corrida completa: ~1h-1h30 (antes 4h46m).
3. **El tema violó el espíritu de la cuarentena**: "lluvia para dormir"
   es contenido de SONIDOS (primo de música/sonidos, borrado 2 veces).
   El filtro no lo cazaba: faltaban términos (rain, lluvia, white noise,
   ruido blanco, binaural, olas...) y los términos de 2 palabras no se
   detectaban (comparaba palabra a palabra). Ambos corregidos y probados:
   "lluvia/ruido blanco/white noise" ahora vetados; "remedios para dormir"
   y "magnesio" siguen libres.
   ⚠️ DECISIÓN DEL USUARIO: los 2 videos programados de hoy son de
   sonidos de lluvia. Opciones: (a) borrarlos antes de las 19:30 UTC
   para que nunca se publiquen, o (b) dejarlos salir y evaluar.


## 🚀 3 MEJORAS DE CRECIMIENTO (pedidas por el usuario, 21-ago-2026)
1. **Comentarios interactivos**: los comentarios cruzados ya no son solo un
   link. Ahora abren conversación con preguntas concretas sobre el tema
   ("¿Te ha pasado que...?", "¿Conoces otras alternativas para...?",
   "¿Cuál consejo vas a probar primero?"). 7 plantillas rotativas +
   extractor de tema del título (limpia conectores). Cada respuesta de un
   espectador = señal de interacción (y el Agente 30 responde).
2. **Publicación programada en hora pico** (idea del usuario: "crear el
   video temprano y publicarlo a la hora indicada"): implementado con la
   función NATIVA de YouTube (status.publishAt): el video se sube PRIVADO
   y YouTube lo hace público exacto a las 19:30 UTC. Activable con
   publicacion.programar_para_hora_pico (ya en true). Los comentarios
   cruzados de videos programados se ENCOLAN (YouTube no acepta
   comentarios en privados) y el paso diario los publica cuando el video
   ya es público. Probado: calcula bien el publishAt y respeta apagado.
3. **Puente Short→largo reforzado** (dato real: Shorts con 27-710 vistas
   vs largos con 3-8): el cierre hablado del Short ahora es un
   CLIFFHANGER específico del tema + instrucción concreta de navegación
   ("toca mi foto de perfil, es el video más reciente") — los
   espectadores de Shorts no leen descripciones, hay que decírselo con la
   voz. Aplica al Short derivado y al independiente. Se suma a lo ya
   hecho: playlist compartida + link en primer comentario.
   ⚠️ TAREA MANUAL OPCIONAL (30 seg/video, la API no lo permite): en la
   app de YouTube → tu Short → editar → "Vídeo relacionado" → elegir el
   video largo. Es el botón nativo que SÍ es tocable dentro del Short.

## 🔧 AUDITORÍA DEL VIDEO "MAGNESIO" + 8 CORRECCIONES (21-ago-2026)
Primer video con el arsenal completo (-8mFy8Vdqns): funcionaron intro con
logo, música Jamendo (primera vez), portada real del estudio x3, FLUX,
referencias correctas y publicación efectiva de largo+Short. Defectos
reales encontrados (usuario + auditoría con storyboards) y corregidos:

1. **Duración 7:43 (mínimo 15)**: la extensión abortaba con UNA ronda pobre.
   Ahora rota de cerebro (mistral→gemini→groq→openrouter→nvidia) y solo
   aborta tras 3 rondas pobres consecutivas; max_intentos 8→12.
2. **Short SIN imágenes (degradado verde)**: la carpeta de visuales del
   largo se borraba ANTES de crear el Short. Ahora sobrevive hasta después
   y crear_short() rescata cualquier beat con "_fallback" usando visuales
   REALES del largo.
3. **Mujer con 3 brazos**: la verificación Gemini ahora también rechaza
   deformidades anatómicas (brazos/manos/dedos de más, caras deformes) y
   texto inventado en etiquetas.
4. **Frascos "Citirato de Magnisim"**: prompt de imagen exige ABSOLUTELY NO
   TEXT / etiquetas en blanco / envases genéricos.
5. **Imágenes repetidas en distintos minutos**: el reuso de visuales ahora
   tiene memoria (prefiere no-reusados, máximo 2 reusos por visual).
6. **Loops**: el boomerang ya no se repite N veces en beats largos: una
   sola pasada ida+vuelta + fotograma final congelado.
7. **Música rock ("Hope" de Jimi Sobara, género real rock+guitarra
   eléctrica)**: tags nuevos SOLO relajantes (meditation/relaxing/piano/
   calm/soft/ambient) + filtro por géneros reales de musicinfo (prohibidos
   rock/metal/electro...) e instrumentos (guitarra eléctrica/batería).
   Verificado en vivo: ahora elige "My Freedom" (filmscore, piano+cuerdas).
   Volumen de fondo 10%→6% (pedido: "bájale un poco").
8. **Descripción con párrafo duplicado**: viral_strategist ya no repite el
   resumen cuando está contenido en el primer bloque.
9. **Link del Short al largo**: investigado y confirmado que YouTube
   BLOQUEA por diseño los links tocables en descripciones de Shorts
   (anti-spam) y que el botón oficial "video relacionado" NO es
   configurable por API. Solución triple automatizada: (a) URLs completas
   con https://www. en comentario fijado (ahí SÍ son tocables), (b) el
   Short entra a la MISMA playlist que el largo (al terminar, YouTube
   prioriza contenido del canal/playlist en el feed), (c) CTA verbal =
   "video completo en el primer comentario".


## 🛡️ ARSENAL COMPLETO INTEGRADO (19-ago-2026, noche) — el sistema queda blindado
El usuario consiguió y verificó (todas probadas EN VIVO) las llaves del arsenal:
Jamendo, Mistral, OpenRouter, Cloudflare (token + account), Pixabay y NVIDIA.
Cerebras quedó DESCARTADO (ahora exige tarjeta de crédito, verificado en vivo).

Qué se integró (todo probado en vivo con las llaves reales):
1. **`agents/llm_cascada.py` (nuevo)**: cascada universal de 5 cerebros
   Groq → Gemini → Mistral Large → OpenRouter (4 modelos :free) → NVIDIA
   (102 modelos). La usan: guionista (guion + extensión), Short
   independiente, respondedor de comentarios y revisor de relevancia
   científica. PROBADO: simulé Groq y Gemini muertos a la vez (el desastre
   del 19-ago) y la cascada respondió con Mistral sin pestañear.
2. **Música de fondo POR FIN ACTIVA** (`agents/musica.py`): filtro de
   Jamendo corregido (ccnc=false + ccnd=false del lado del servidor: solo
   licencias CC-BY / BY-SA, seguras incluso cuando el canal se monetice),
   rotación de tags si uno no tiene pistas (probado: 'corporate' devuelve
   0), y filtro anti-fuera-de-contexto (la primera prueba eligió "Happy
   Holiday Christmas" para un video de salud; ahora se descartan pistas
   navideñas/festivas por nombre).
3. **Imágenes premium** (`agents/visuals.py` → `_generar_imagen_cloudflare`):
   Cloudflare Workers AI como proveedor PREFERIDO antes de Pollinations.
   FLUX.1 Schnell para paisaje (1024x1024 + recorte central a 16:9, la API
   rechaza width/height — verificado) y SDXL nativo para Shorts verticales
   (720x1280 probado). ~230 imágenes/día gratis. Escenas con personas
   siguen pasando por la verificación Gemini (fallan cerradas).
4. **Voz premium en la intro** (`agents/voice.py` → `_sintetizar_intro_gemini`):
   la intro de marca se narra con Gemini TTS (voz Charon, o Kore para
   audiencia femenina) con dirección de actuación ("voz cálida de locutor
   latino de bienestar"). 1 llamada por video = cuota mínima. Si falla,
   edge-tts como siempre (nunca bloquea).
5. **Agente 35 "Vigía de Recursos"** (`scripts/vigia_recursos.py` +
   `.github/workflows/vigia_recursos.yml`): cada lunes 12:00 UTC prueba EN
   VIVO los 12 recursos del arsenal; si hay falla crítica (0 cerebros, 0
   fuentes de imágenes, sin voz) el workflow falla a propósito → correo de
   GitHub. Primera corrida real: 11/12 vivos (Gemini 503 temporal).
6. **`scripts/verificar_secretos.py`**: al inicio de cada corrida imprime
   qué llaves llegaron desde GitHub Secrets (sin revelar valores) para
   detectar nombres mal escritos de inmediato.

## 🚨 EMERGENCIA REPARADA: video genérico del 19-ago-2026 (auditoría con evidencia)
Qué pasó (verificado en vivo con la API de YouTube y las APIs de IA):
- El video del 19-ago ("Cambios Simples Para Tu Salud Natural, Alternativa,")
  duró **3m07s**, con título cortado, guion 100% de plantilla local, sin tema
  real, sin intro de marca y con referencias científicas que NO tenían nada
  que ver (un estudio de derrames cerebrales y otro de tumores cerebrales).
- Causa raíz #1: **Groq eliminó el modelo `llama-3.3-70b-versatile`**
  (la API devolvió 404 `model_not_found`, comprobado en vivo). El guionista,
  el Short independiente, el respondedor de comentarios y el refinador de
  relevancia científica quedaron rotos al mismo tiempo.
- Causa raíz #2: la cuota diaria gratuita de **Gemini estaba agotada (429)**
  a la hora de la corrida, así que el respaldo tampoco funcionó.
- Resultado: el pipeline cayó a `_plantilla_local()` y PUBLICÓ el video
  genérico en público.

Reparaciones aplicadas (todas probadas en vivo):
1. **Selección dinámica de modelo Groq** (`agents/utils.modelo_groq`): antes
   de cada llamada se consulta qué modelos EXISTEN hoy en la cuenta y se usa
   el mejor disponible (preferencia actual: `openai/gpt-oss-120b`, verificado
   funcionando). Si Groq vuelve a eliminar un modelo, el sistema se adapta
   solo, sin tocar código.
2. **Gemini actualizado** a `gemini-flash-latest` (alias que Google mantiene
   siempre apuntando al modelo vigente; `gemini-2.5-flash` seguía vivo pero
   los alias `-latest` sobreviven a las descontinuaciones).
3. **La plantilla local ya NO publica**: si Gemini y Groq fallan a la vez,
   la corrida se aborta a propósito con error claro. Es mejor no publicar un
   día (el cron de respaldo de las 21:45 UTC y el del día siguiente lo
   reintentan) que publicar un video genérico que daña la reputación del
   canal y activa la política de "contenido inauténtico" de YouTube.

⚠️ ACCIÓN MANUAL PENDIENTE DEL USUARIO: borrar los 2 videos del 19-ago
(`a51jM40d8c0` largo y `Wx9IMctsbB0` Short) — son de plantilla genérica.

## 🚀 Actualización: publicación pública y tráfico interno entre videos
Por decisión explícita del dueño del canal:
- **Los videos se publican SIEMPRE en público** (`publicacion.privacidad_default: "public"`
  en `config.example.yaml`), de forma 100% autónoma vía el cron diario de
  GitHub Actions. Ya no hay un paso de revisión manual antes de que el
  video quede visible para todo el mundo: si algo sale mal en un video, se
  entera el público al mismo tiempo que tú. Puedes revisar los logs/artefactos
  de cada corrida en la pestaña "Actions" de GitHub para detectarlo rápido.
- **Tráfico orgánico entre tus propios videos** (`agents/promocion_cruzada.py`):
  además del enlace en la descripción ("🔎 TAMBIÉN TE PUEDE INTERESAR") y los
  comentarios cruzados entre el video largo y su Short, ahora cada video
  largo menciona EN VOZ ALTA (y con una tarjeta en pantalla) un video
  relacionado ya publicado del canal, cerca del final, justo antes del
  llamado final a suscribirse. Si todavía no hay otros videos publicados
  (por ejemplo, el primer día), esto simplemente no aparece, sin romper nada.

Sistema multiagente que automatiza el proceso completo descrito en el video
"Cómo Monetizar un Canal de YouTube en 5 Días", pero **sin pagar ninguna
herramienta** (Viralyt, ElevenLabs, CapCut Pro, Canva Pro, etc. quedan
reemplazadas por alternativas gratuitas equivalentes).

```
TrendScout → Guionista (+ EstrategaViral) → Narrador → VisualScout → EditorVideo → Packaging → Publicador → Analista
 (nicho)      (guion en beats, IA)           (voz)     (1 clip real   (ffmpeg,      (miniatura)  (YouTube +   (métricas)
                                                        por beat)      cortes rápidos)             índice)
```

## 🧩 Qué agente reemplaza a qué herramienta de pago

| Herramienta de pago (video original) | Reemplazo 100% gratis usado aquí            |
|---------------------------------------|------------------------------------------------|
| Viralyt (buscar nichos/ideas)         | `agents/trend_scout.py` con YouTube Data API (capa gratuita) |
| ChatGPT Plus (guion)                  | `agents/scriptwriter.py` con Gemini/Groq (capas gratuitas) o plantilla local sin IA |
| ElevenLabs (voz)                      | `agents/voice.py` con **edge-tts** (gratis, sin cuenta) |
| Stock de video de pago                | `agents/visuals.py` con Pexels/Pixabay (gratis), un recurso real por CADA beat |
| CapCut (edición)                      | `agents/video_editor.py` con MoviePy + FFmpeg (gratis, open source) |
| Canva (miniatura)                     | `agents/thumbnail.py` con Pillow (gratis, local) |
| Editor de retención / consultor viral | `agents/viral_strategist.py` (reglas basadas en investigación real de edición YouTube) |
| Subida manual                         | `agents/publisher.py` con YouTube Data API (gratis) |
| VidIQ/TubeBuddy (métricas)            | `agents/analytics.py` con YouTube Analytics API (gratis) |

### 🎬 Agente 9: Estratega Viral (retención de audiencia)
Encapsula reglas reales de edición y guionismo de YouTube (no improvisadas):
- El gancho debe prometer valor concreto en los primeros 5-15 segundos, sin
  muletillas de relleno ("hola a todos, bienvenidos de nuevo...").
- El guion se estructura en **beats** cortos (1-2 frases + 1 palabra clave
  visual específica y filmable cada uno), lo que permite cortes visuales
  cada 3-9 segundos en vez de sostener un mismo plano aburrido por minutos.
- El texto narrable es 100% texto plano (solo letras, puntos y comas): nada
  de asteriscos, guiones, numerales ni marcas de tiempo que el sintetizador
  de voz pudiera leer en voz alta por error.
- Nunca se repite el mismo recurso visual dos veces en el mismo video.
- Se prioriza siempre metraje/foto REAL (nunca ilustraciones ni dibujos);
  si el guion pide por error algo tipo "diagrama" o "animación", un filtro
  de seguridad lo detecta y lo reemplaza automáticamente.
- Al publicar, arma una descripción con resumen llamativo + índice de
  capítulos con tiempos REALES (calculados de la duración del audio, no
  inventados) + hashtags + disclaimer.

### 🔎 Agente 10: Verificador de Coherencia (QA)
Después de que VisualScout elige un recurso para cada beat, este agente
extrae un fotograma real y le pregunta a Gemini Vision (gratis) qué tan
bien representa la frase que se está narrando en ese momento (0-10). Si la
coincidencia es baja, pide automáticamente un recurso alternativo. Nunca
bloquea el pipeline: si se agota la cuota gratuita de verificación a mitad
de un video, se detiene con seguridad y conserva los recursos ya elegidos.

### 📱 Agente 11: Creador de Shorts
Genera un YouTube Short vertical (9:16, ~45-60s) a partir del gancho y los
primeros beats más atractivos del video largo, con subtítulos incrustados
grandes (los Shorts se ven mayormente sin sonido) y una tarjeta final de
llamada a la acción hacia el video completo. Se publica por separado, con
su propio título/descripción enlazando al video largo.

### 📝 Agente 12: Subtítulos
Genera un archivo .srt con los tiempos EXACTOS de cada beat (reconstruidos
igual que el video final) y lo sube como closed-caption oficial vía la
YouTube Data API. Mejora el SEO (YouTube indexa cada palabra hablada) y la
retención (mucha gente ve con el sonido apagado).

### 📚 Agente 13: Gestor de Playlists
Agrupa automáticamente cada video nuevo en una playlist del mismo nicho.
Cuando termina un video, YouTube sugiere el siguiente de la misma playlist,
lo que aumenta el watch time de sesión (una señal que el algoritmo premia).

### 🎵 Agente 14: Música de fondo
Agrega una pista instrumental de fondo (volumen bajo) usando Jamendo,
filtrando automáticamente solo licencias que permiten uso comercial (nunca
usa pistas "No Comercial", ya que el canal se va a monetizar), y agrega el
crédito correspondiente en la descripción.

### 🔔 Agente 22: Llamados a suscripción garantizados (inicio/mitad/final)
`agents/suscripcion_cta.py` inserta SIEMPRE, en código (no depende de que
la IA se acuerde), 3 momentos pidiendo la suscripción: justo después del
gancho inicial, en el capítulo central del video, y al final. Cada uno usa
una frase distinta elegida al azar de varias opciones (para que el canal
no se sienta repetitivo) y muestra una **tarjeta gráfica** (campana +
"SUSCRÍBETE", sin ninguna persona real ni generada). El Short reutiliza el
mismo guion pero SIN estos 3 llamados (ya tiene su propia tarjeta final,
que también invita a suscribirse) para no sentirse repetitivo en 45 segundos.

📌 **Historial (auditoría agosto 2026)**: este canal tuvo brevemente una
presentadora fija generada con IA para estos 3 momentos, pensada para dar
un "rostro humano" y reconocimiento de marca. Se QUITÓ por decisión del
dueño del canal al descubrir que YouTube aclaró (16-jul-2026) que los
canales con "personas de IA" en temas sensibles como salud pueden perder
la monetización. El canal es ahora 100% sin rostro por precaución.

### 🔬 Agente 27: Citas Científicas en Pantalla
`agents/citas_cientificas.py` responde a un pedido explícito del dueño del
canal: que la información se sienta respaldada de verdad, no solo "por
dentro" (verificada contra Europe PMC/NCBI, ver Agente 17) sino también
**percibida** por quien ve el video. Igual que los llamados a suscripción,
esto se garantiza en CÓDIGO, no se le deja solo a la IA:

- Si el Investigador Científico (Agente 17) encontró estudios reales sobre
  el tema del video, se insertan 1-2 frases que mencionan en voz alta,
  de forma natural, el nombre real de la revista y el año reales
  ("esto lo confirma un estudio publicado en la revista X, en 2023").
  Nunca se inventa un hallazgo nuevo: solo se comunica que el estudio real
  existe (lo mismo que ya se citaba, antes en silencio, solo en la
  descripción).
- Esa frase usa como imagen de fondo una toma real de documentos/artículos
  científicos (portada de revista, persona leyendo un estudio, papeles de
  laboratorio) en vez de una escena sin relación con lo que se dice.
- Se dibuja un pequeño recuadro en pantalla (mismo estilo que las cifras
  verificadas, ver Agente 24 `callout_cifras.py`) con el texto "ESTUDIO
  REAL" y el nombre de la revista/año, para reforzarlo visualmente.
- El estudio queda garantizado en la lista de referencias con enlace real
  y verificado en la descripción de YouTube (antes esto solo pasaba si
  una cifra puntual del guion coincidía palabra por palabra con el
  estudio; ahora también pasa cuando la mención es más general).
- Si no hay ningún estudio real disponible para el tema, no se inventa
  nada: el video simplemente no incluye estas citas (mejor no citar que
  citar algo sin verificar).

### 🎯 Búsqueda científica de precisión (auditoría con video real, 14-ago-2026)
Al revisar el video real publicado ese día se descubrió que la descripción
NO traía referencias científicas. Causa raíz encontrada con pruebas en
vivo: se buscaba en Europe PMC con el título EN ESPAÑOL del video, y la
base (que está en inglés) devolvía estudios de revistas hispanas sin
ninguna relación con el tema. `agents/investigacion_cientifica.py` ahora:

1. **Traduce el tema a inglés** (endpoint gratuito de Google Translate,
   sin API key) antes de buscar.
2. Busca con **palabras clave en inglés** + `HAS_ABSTRACT:y`.
3. Aplica un **filtro de relevancia en 3 capas**: palabras clave del tema
   presentes en el título/resumen, lista negra de campos ajenos (IA,
   agricultura, animales, industria alimentaria...), y señales de estudio
   de salud humana (pacientes, ensayo clínico, dieta, etc.).
4. Un **revisor IA** (1 llamada a Gemini, con Groq de respaldo) lee los
   candidatos y confirma cuáles tratan DIRECTAMENTE el tema. Es tarea de
   lectura, no de generación: no puede inventar estudios.
5. Si nada pasa el filtro, pide al LLM una **consulta médica experta en
   inglés** (p.ej. `(lutein OR zeaxanthin) AND "visual acuity"` para un
   video de visión) y reintenta una vez.
6. Si aún así no hay estudios relevantes, el video va **sin citas** (mejor
   que citar una revista que no habla del tema, lo que destruiría la
   credibilidad).

Probado en vivo: para "Alimentos Para La Visión" ahora devuelve estudios
reales de luteína/carotenoides y función visual en humanos (Journal of
Ophthalmology, BMJ Open...), en vez de papers sin relación.

### 📵 El banner SUSCRÍBETE ya no aparece durante el gancho (misma auditoría)
Extrayendo fotogramas del video real publicado se comprobó que el banner
de suscripción salía en pantalla durante los primeros ~15 segundos (el
CTA de inicio era el primer beat del capítulo 1 y la voz del gancho se
narra encima de ese beat). Eso es uno de los "asesinos de retención"
documentados: pedir suscripción antes de dar valor.
`agents/suscripcion_cta.py` ahora inserta el CTA de inicio DESPUÉS de los
2 primeros beats de contenido (~20-30 segundos), sin tocar los CTA de
mitad y final.

### 🩹 Correcciones de la auditoría del Short real (14-ago-2026, tarde)
Descargando y revisando fotograma por fotograma el Short publicado ese día
se encontraron y corrigieron 3 defectos reales:

1. **La voz narraba jerga interna de SEO**: se oía literalmente «La keyword
   principal 'alimentos para la visión' es crucial...». Nuevo filtro
   determinista `_quitar_lenguaje_meta()` en `agents/scriptwriter.py`:
   elimina 'keyword', 'palabra clave', 'SEO' y similares de TODO texto
   narrable, venga del LLM que venga.
2. **Texto interno visible en pantalla**: el fondo de último recurso
   (`_generar_fondo_local` en `agents/visuals.py`) escribía la palabra
   clave de búsqueda en la imagen; como es texto interno (a veces en inglés
   o recortado), el espectador veía cosas como "eating healthy foo..." o
   "...iendo y señalando con el dedo". Ahora ese fondo es un degradado
   limpio SIN texto (el subtítulo de la narración ya comunica).
   Además la keyword del beat final del Short ahora está en inglés para
   que los bancos de stock sí encuentren metraje real.
3. **Imagen congelada ~20 segundos al final del Short**: cuando el audio
   duraba más que la suma de cortes al máximo permitido, TODO el sobrante
   se botaba en el último corte. Ahora `_ajustar_duraciones_a_ritmo()`
   (en `agents/video_editor.py`) reparte el sobrante proporcionalmente
   entre todos los cortes.

### 🎬 Agente 31: Short independiente diario + humanización (16-ago-2026)
Estrategia de crecimiento acordada con el usuario: los días SIN video
largo (frecuencia: largo cada 2 días), se publica UN Short con **contenido
completo y propio** — no un teaser recortado:

- **Alineado a un video largo YA publicado** (rotación por el menos usado):
  el tema sale del largo, pero el guion es nuevo (otro ángulo, otro dato).
  El comentario del Short enlaza a ese video largo (link clicable real,
  verificado por API con `<a href>`).
- **4 formatos rotativos** (dato sorprendente / mito vs verdad / top 3 /
  consejo práctico), nunca el mismo dos días seguidos, con cierres
  variados (al largo / a suscribirse / curiosidad / pregunta). Duración
  objetivo variable (22-42s). Temperatura alta del LLM para máxima
  variación entre Shorts (defensas anti-"contenido inauténtico").
- **Humanización del guion**: reglas de oralidad en el prompt (pregunta
  retórica, una expresión coloquial natural, frases cortas de habla real,
  prohibido lenguaje de folleto).
- **Humanización de la voz** (`agents/voice.py`): variación aleatoria de
  velocidad por video (±2%) — los narradores humanos no graban siempre a
  la misma velocidad exacta; la uniformidad perfecta es señal de "voz
  sintética sin edición".
- Con verificación científica cuando hay estudios + filtro de seguridad
  médica. Si no hay LLM disponible, NO publica relleno de plantilla.
- Candado propio del día (el cron de respaldo no duplica el Short).
- Integrado en el workflow: corre solo cuando el candado dice que no toca
  video largo. Probado en vivo: guion generado con estudio real de
  probióticos, formato mito-vs-verdad, corregido por seguridad médica.
- Corrección adicional a `agents/seguridad_medica.py`: el reemplazo de
  frases de riesgo ahora sustituye la ORACIÓN completa (antes podía dejar
  frases enredadas, visto en prueba real).

### 💬 Agente 30: Respondedor de comentarios (estrategia de visualizaciones, 16-ago-2026)
La interacción (comentarios/respuestas) es una de las señales principales
que usa el algoritmo para recomendar videos. `agents/responde_comentarios.py`:

- En cada corrida diaria (incluso los días sin publicación) lee los
  comentarios de los últimos videos del canal REAL (no solo de la memoria
  local) y responde a los espectadores.
- Respuestas generadas con Groq (breves, cálidas, específicas del
  comentario), con plantilla amable de respaldo si el LLM no está
  disponible. Pasan también por el filtro de seguridad médica.
- REGLA YMYL: si el comentario pide consejo médico personalizado
  (síntomas, dosis, "puedo dejar mi medicamento"), responde con empatía y
  remite al médico. Nunca da consejo personalizado.
- Ignora spam (enlaces, WhatsApp/Telegram), los comentarios del propio
  canal (cross-promo) y los ya respondidos (registro en data/estado.json
  + verificación en vivo de respuestas previas).
- Máximo 10 respuestas por corrida (ritmo humano, no ráfaga de bot).
- Probado en vivo: reconoció correctamente que los 4 comentarios actuales
  del canal son propios y no respondió ninguno.
- Integrado como paso propio en el workflow (corre aunque no toque
  publicar video, con continue-on-error para nunca bloquear nada).

### 🔧 Auditoría profunda de los 5 defectos del video "Remedios Naturales Insomnio" (18-ago-2026, noche)
El usuario reportó 5 problemas en el video de 11m40s. Causa raíz y corrección de cada uno:

1. **Duración 11m40s (< 15 min)** → la constante PALABRAS_POR_MINUTO_HABLADO
   estaba en 140 (estimación de manual), pero midiendo el video REAL la voz
   narra ~180 palabras/min. Recalibrada a 185 + margen del 8% sobre el
   mínimo: el guion de 15 min ahora exige ~2997 palabras (antes 2100).
2. **Espacios sin imágenes** → Pollinations devolvía 429 en ráfagas de ~50
   peticiones. Triple defensa: pausa de 2s entre peticiones + espera
   creciente ante 429 (5s/10s) + 4º intento con el modelo "turbo" (cola
   distinta, verificado en vivo). Y NUEVO penúltimo recurso: si aun así no
   hay imagen, se REUTILIZA un visual real ya descargado del mismo video
   (una escena repetida es mejor que un degradado vacío de 20s).
3. **Imágenes desincronizadas de la voz** → _ajustar_duraciones_a_ritmo
   comprimía cortes largos a 9s y regalaba el sobrante a otros cortes,
   corriendo TODOS los visuales respecto a su voz desde ese punto.
   REESCRITO: cada visual dura EXACTAMENTE lo que dura su beat de audio
   (medido del MP3 real); solo ajuste proporcional fino por redondeos.
   Probado: desvío 0 ms. (subtitulos.py y shorts usan la misma función →
   también quedan sincronizados.)
4. **Videos repetidos "en loop"** → un clip de stock de 4s en un beat de
   12s se repetía 3 veces de corrido. Ahora: si el clip cubre ≥60% del
   beat, una sola pasada + último fotograma sostenido; si es más corto,
   efecto "boomerang" (ida + reversa, continuo, sin salto visible).
5. **Menciones de investigación sin portada** → se citaban estudios SIN
   acceso abierto (sin PDF legal que mostrar). Ahora: si hay al menos un
   estudio de acceso abierto, SOLO se citan esos (cada mención tendrá su
   portada real en pantalla); si no hay ninguno, se usa el visual de
   documento genérico y el log lo explica.

### ⏳ Ventanas de tiempo para repetir temas (ajuste del usuario, 19-ago-2026)
El usuario precisó la política: "los videos siguientes deben ser diferentes
a los publicados, pero después de un tiempo se puede publicar un video
similar (no del tema exacto)". Implementado con ventanas de tiempo:

- **Temas normales — 90 días**: un tema que comparte conceptos con un video
  del canal solo se bloquea mientras ese video tenga <90 días. Después, el
  tema queda LIBERADO para revisitarse con otro ángulo (lo que hacen los
  canales grandes). Los títulos del canal ahora se leen CON su fecha de
  publicación para calcular la edad real.
- **Música/sonidos/mantras — cuarentena de 180 días** (no veto eterno):
  corre desde el último incidente (18-ago-2026, segundo borrado). Desde
  ~feb-2027, una idea de música (p. ej. una noticia sobre musicoterapia)
  podría volver a considerarse, pasando igual por el anti-repetidos.
- Probado con 8 casos (incluye: magnesio con video de 100 días → liberado;
  setas con video de 5 días → bloqueado; música → cuarentena; y simulación
  de cuarentena vencida → elegible): 8/8 correctos.
- Bug corregido en la misma sesión: palabras cortas del canal ("tu")
  coincidían como subcadena en palabras nuevas ("TUrmeric") y bloqueaban
  temas genuinamente nuevos.

### 🚫 Por qué se repitió "música relajante" OTRA VEZ y doble corrección definitiva (18-ago-2026, noche)
El robot volvió a elegir tema de música/relajación pese al filtro
anti-repetidos del día anterior. Causa raíz encontrada y demostrada con
prueba en vivo: **las ideas del buscador de tendencias vienen EN INGLÉS**
("Relaxing Music To Relieve Stress...") y los títulos del canal están EN
ESPAÑOL ("Música Relajante Para...") → la comparación por palabras daba
CERO coincidencias y todo pasaba como "nuevo". Doble corrección:

1. **Filtro bilingüe por CONCEPTOS**: mapa de ~16 grupos de términos
   equivalentes ES/EN (música/music/mantra, estrés/stress/anxiety,
   setas/mushroom/hongo, intestino/gut/microbiome...). Si la idea y un
   título del canal comparten 2+ conceptos centrales, es repetida sin
   importar el idioma. Probado: "Relaxing Music To Relieve Stress" vs
   "Música Relajante Para Reducir El Estrés" → REPETIDO ✓.
2. **VETO PERMANENTE al tema música/sonidos/mantras/frecuencias/ASMR**:
   el usuario borró ese tipo de video DOS veces (música relajante y
   Gayatri Mantra); el canal es de salud natural con evidencia, no de
   música ambiental. Ninguna idea con ese concepto central vuelve a
   elegirse. Probado con 10 casos (6 vetados, 4 permitidos): 10/10.

### 🎵 Agente 33: Música de meditación en la intro (19-ago-2026)
La intro de marca ahora lleva música relajante de fondo bajo la voz:

- **Doble vía, siempre gratis**: pista de meditación de Jamendo (si hay
  client_id) o, como respaldo garantizado, un **pad ambiental sintetizado
  localmente** (progresión C-Am-F-G con armónicos suaves, ataque lento,
  fundidos de entrada/salida) — 100% original, generado matemáticamente,
  sin copyright de terceros y sin depender de internet.
- Mezclado al 22% de volumen bajo la voz, SOLO durante el beat de intro
  (medido en render real: el pad suena en la intro y calla después).
- La mezcla se hace en la pista de audio del capítulo (no en el sub-clip,
  cuyo audio se descarta al montar la narración).
- HALLAZGO de esta sesión: `jamendo_client_id` sigue con el placeholder
  ("OBTENER_GRATIS_AQUI"), así que TODOS los videos hasta ahora salieron
  sin música de fondo general. Si se desea música en todo el video,
  crear el client_id gratis en https://devportal.jamendo.com/ y añadirlo
  como secret JAMENDO_CLIENT_ID en GitHub. Mientras tanto, la intro SÍ
  tendrá siempre su música (pad local).

### 🎬 Agente 32: Intro de marca con logo (pedido del usuario, 19-ago-2026)
El video largo ahora abre con una presentación de marca de ~10 segundos:

- **Tarjeta visual con el LOGO REAL del canal** (descargado de YouTube a
  assets/logo_canal.jpg): logo circular con halo sobre degradado verde de
  marca + "SALUD NATURAL DIARIA" + "Información real, respaldada por
  estudios científicos" + "Fuentes enlazadas en la descripción".
- **Voz con promesa impactante** (4 variantes rotativas anti-plantilla),
  las 3 ideas en ~10s: bienvenida + promesa de credibilidad científica
  ("aquí no repetimos rumores...") + invitación a suscribirse.
- **Orden final del arranque** (verificado con prueba integrada):
  1. Intro de marca (logo + promesa + suscripción)
  2. Gancho del video (reordenado: ahora es un beat después de la intro;
     antes voice.py lo narraba primero y habría quedado al revés)
  3. Primer golpe de contenido
  4. Mención de la investigación científica base (la primera cita
     científica ahora va SIEMPRE temprana, en el capítulo 1)
- Por qué esta intro no mata la retención (el riesgo de los "bumpers"):
  dura ~10s, la voz da la promesa de valor DESDE el primer segundo (no es
  un logo mudo) y el texto es gancho de credibilidad, no saludo genérico.
- Excluida de: QA de coherencia, miniatura base y mini-guion del Short.

### 📈 Primer análisis con datos REALES de audiencia (19-ago-2026)
Estadísticas reales de los primeros 28 días (YouTube Analytics del usuario):

- **Un Short independiente llegó a 710 vistas** (65% del tráfico total del
  canal): el algoritmo SÍ distribuye los Shorts del canal. Pero su
  retención fue débil (33%, deslizaban a los ~9s) — era el Short con
  fondos degradados vacíos que la auditoría del 18-ago corrigió.
- El Short con mejor arranque retuvo 63,5% (excelente para Shorts).
- Los largos aún tienen muestra mínima (3-8 vistas), pero "Setas Ostra"
  logró 41,5% de porcentaje visto — señal temprana buena para un largo.
- Lección aplicada: nueva "REGLA DE LOS PRIMEROS 3 SEGUNDOS" en el prompt
  del Short independiente (el primer beat debe romper una creencia o doler,
  nunca abrir con contexto; datos: 710 personas llegaron, 66% se fue en
  segundos por un arranque débil + visuales vacíos).

### 🎬 Auditoría de producción del 18-ago-2026 (defectos vistos por el usuario en el video real)
El usuario revisó el video largo "Gayatri Mantra" (19m44s) y su Short y
reportó 4 defectos. Auditoría con storyboards reales del video publicado +
reproducción de cada bug en código:

1. **"Almohadilla, terror, short" narrado al final** ✅ CORREGIDO
   Causa: la mención cruzada narra el título del video recomendado; ese
   título era un Short con "😱 #Shorts" y el beat se agrega DESPUÉS de la
   sanitización del guionista (nadie lo limpiaba). Doble corrección:
   `promocion_cruzada.py` limpia el título antes de narrarlo (fuera
   hashtags/emojis) y `utils.limpiar_texto_para_voz()` ahora elimina TODOS
   los emojis (antes solo quitaba #, y edge-tts leía el emoji en voz alta).
2. **Espacios sin imagen (fondos degradados vacíos)** ✅ CORREGIDO
   Causa: cada imagen IA requiere verificación de seguridad con Gemini,
   pero la cuota (16/día) se agota con ~50 beats por video; sin
   verificación disponible, TODAS las imágenes IA se descartaban "por
   precaución" → degradado vacío. Corrección: **verificación selectiva**  —
   escenas SIN personas (comida, plantas, paisajes, objetos: riesgo NSFW
   ~cero) se aceptan sin verificación; escenas CON personas siguen
   exigiendo verificación real (la seguridad manda). Probado en vivo:
   escena de té sin persona aceptada; escena con persona sin Gemini
   disponible, descartada.
3. **Imágenes que coinciden con palabras pero no con la IDEA** ✅ CORREGIDO
   (ej. real: "la calma que causa el sonido" mostraba hojas). Triple
   corrección: (a) nueva REGLA DE ORO DEL VISUAL en el prompt del
   guionista con ese ejemplo real ("si alguien ve la escena SIN audio,
   ¿entiende de qué se habla?"); (b) umbral de relevancia del stock subido
   de 0.34 a 0.50 (si el stock no coincide en ≥50% de las palabras, se
   genera imagen IA a medida); (c) el prompt de imagen IA ya no fuerza
   "persona en cocina" en escenas sin personas (causaba composiciones
   incoherentes en escenas de objetos/plantas).
4. **Imágenes IA horizontales en Shorts verticales** ✅ CORREGIDO
   Se generaban siempre en 1280x720 aunque el Short es 9:16; ahora el
   tamaño sigue la orientación (720x1280 para Shorts).

### 🔎 Auditoría del 17-ago-2026: el "video largo perdido" y el filtro anti-repetidos
Reconstrucción con evidencia real (API + RSS + correo de alerta del usuario):

1. El 16-ago a las 8:00am el vigilante v1 envió una FALSA alarma (memoria
   local congelada en el 9-ago). El usuario, correctamente, lanzó un "Run
   workflow" manual.
2. Esa corrida SÍ publicó video largo (v4YH_bZELF0, "Música Relajante") +
   su Short a las ~9:40am. PERO el tema era una REPETICIÓN de "Música
   Relajante" (la memoria vieja no recordaba los temas ya usados) y ese
   video largo fue borrado después (ya no existe en YouTube), dejando a su
   Short huérfano.
3. El 17-ago la corrida normal funcionó EXACTAMENTE como fue diseñada: el
   candado v2 detectó "largo publicado ayer 16 → no toca" y publicó el
   Short independiente (Setas Ostra, formato dato-sorprendente, enlazado
   al largo real de setas que sí existe). No fue un fallo: fue la
   frecuencia cada-2-días operando (el largo del 16, aunque luego borrado,
   contaba como publicado ese día en el RSS al momento de la corrida...
   y tras el borrado, el último largo visible pasó a ser el del 15, por lo
   que el 17 igualmente tocaba largo pero la corrida ya había pasado).

Correcciones aplicadas:
- **Filtro anti-repetidos contra el canal REAL** (`orchestrator.py`):
  antes de elegir tema, lee los títulos ya publicados en el canal y
  descarta ideas que coincidan en ≥50% de sus palabras clave. Probado con
  7 casos (música/setas/intestino repetidos vs magnesio/ayuno/cúrcuma
  nuevos): 7/7 correctos. Esto elimina de raíz las repeticiones de tema
  aunque la memoria local esté desactualizada.
- **Short huérfano del 16-ago reparado por API**: su descripción y su
  comentario ahora apuntan al video largo de música real (NYlWbbAxh7s).

### 🔧 Falsa alarma del vigilante corregida: ahora mira el canal REAL (16-ago-2026, tarde)
La mañana del 16-ago el vigilante envió una alerta cuando el canal SÍ
estaba publicando. Causa raíz: leía `data/estado.json` (la memoria local),
que quedó congelada en el 9-ago cuando un push de la memoria falló, aunque
las corridas siguientes publicaron bien. Diagnóstico y corrección:

- **Vigilante v2** (`scripts/vigilante_publicaciones.py`): ahora consulta
  el **feed RSS público del canal de YouTube** (fuente de verdad real, sin
  API key ni cuota) y solo usa la memoria local como respaldo. Verificado
  en vivo: reconoce el Short publicado hoy y responde "todo en orden".
- **Candado de frecuencia v2** (`scripts/verificar_si_ya_publico_hoy.py`):
  mismo cambio; identifica el último video LARGO real (excluye títulos
  con #Shorts) y decide con esa fecha. Sin esta corrección, la memoria
  vieja habría dado luz verde al largo TODOS los días, rompiendo la
  frecuencia de 1 cada 2 días.
- Bug adicional encontrado y corregido en la misma sesión: en el feed de
  YouTube `<published>` viene ANTES de `<media:title>` dentro de cada
  `<entry>`; un regex secuencial cruzaba entradas y desfasaba fechas por
  un día. Ahora se parsea cada `<entry>` por separado.

### 🔔 Vigilante de publicaciones: alerta al celular/correo si el robot no publica (16-ago-2026)
Pedido del usuario: "¿cómo me entero si GitHub se salta la publicación?".
Solución 100% gratis usando las notificaciones nativas de GitHub:

- Nuevo workflow `vigilante.yml`: corre todos los días a las 8:00 am
  (Colombia), una hora MUY distinta de las corridas de publicación, y
  ejecuta `scripts/vigilante_publicaciones.py`.
- El script revisa la memoria del robot: si la última publicación tiene
  más de 3 días (frecuencia de 2 días + 1 de gracia), el workflow
  **termina en error a propósito** → GitHub envía automáticamente un
  correo al dueño del repo ("Vigilante de publicaciones: failed") y una
  notificación push si tiene la app de GitHub en el celular.
- Si todo está en orden, termina en verde y no molesta.
- Probado con 4 escenarios (1, 3, 4 y 7 días sin publicar): 4/4
  correctos (alerta exactamente cuando debe).

Para recibir las alertas (1 minuto, una sola vez):
1. **Correo**: GitHub → foto de perfil → Settings → Notifications →
   en "Actions" dejar activado el aviso de workflows fallidos por email
   (suele venir activado por defecto).
2. **Celular (recomendado)**: instalar la app **GitHub** (Android/iPhone),
   iniciar sesión, y permitir notificaciones. Los fallos de workflows
   llegan como notificación push.

### 📅 Tres ajustes de estrategia pedidos por el dueño del canal (16-ago-2026)
1. **3-5 citas científicas distribuidas por TODO el video** (antes máx. 2):
   la primera poco después de la introducción, otras a la mitad y la
   última cerca del cierre (`agents/citas_cientificas.py` reparte las
   posiciones uniformemente entre capítulos). Probado: con 5 estudios en
   un guion de 8 capítulos caen en los capítulos 2, 3, 5, 7 y 8. TODAS
   las frases mencionan que el enlace está en la descripción.
2. **Frecuencia: 1 video cada 2 días** (antes diario): decisión preventiva
   contra el perfil de "producción en masa" de la política de contenido
   inauténtico. El cron corre a diario, pero el candado
   (`scripts/verificar_si_ya_publico_hoy.py`, `DIAS_ENTRE_VIDEOS = 2`)
   solo deja publicar si pasaron ≥2 días desde el último video. Probado
   con 4 escenarios (hoy/ayer/hace 2 días/hace 3): todos correctos.
   Ventaja extra: la cuota diaria de Gemini rinde el doble por video.
3. **Contacto comercial para marcas en cada descripción**: línea "🤝
   ¿Representas una marca de salud/bienestar...?" con el correo del canal,
   la puerta de entrada estándar para patrocinios antes de AdSense.

### 🛡️ Agente 29: Seguridad Médica + investigación de riesgo de penalización (16-ago-2026)
Investigación completa (políticas oficiales + casos reales) sobre si publicar
1 video IA diario puede hacer que penalicen o cierren el canal. Hallazgos:

**Lo que NO cierra el canal (pero quita monetización):**
- Política de "contenido inauténtico" (renombrada así el 15-jul-2025):
  contenido producido en masa/repetitivo/con plantilla. Se aplica a nivel
  de CANAL. En enero 2026 YouTube terminó 16 canales "AI slop" (35M subs,
  4.700M vistas, ~$10M/año) — pero eran granjas industriales de decenas de
  videos diarios idénticos. Hubo daño colateral documentado: un canal de
  historias bíblicas (588K subs) y uno educativo legítimo desmonetizados.
- Señales que YouTube busca: misma estructura en todos los videos, misma
  voz sintética sin edición, visuales de plantilla, volumen imposible de
  producir con criterio humano.
- **1 video/día NO es el problema** (canales humanos publican diario);
  el problema es que todos los videos "se vean iguales".

**Lo que SÍ puede cerrar un canal de salud (strikes → terminación):**
- La política de DESINFORMACIÓN MÉDICA: afirmar que algo "cura"
  enfermedades, sugerir sustituir tratamientos médicos, contradecir a la
  OMS (ejemplos oficiales de YouTube: "el ajo cura el cáncer", "vitamina C
  en vez de radioterapia").
- Falta de divulgación de contenido sintético realista en temas de salud.

**Ajustes aplicados:**
1. **Nuevo `agents/seguridad_medica.py` (Agente 29)**: última línea de
   defensa determinista. Revisa gancho, beats, título y descripción y
   corrige automáticamente promesas de cura ("cura el cáncer" → "puede
   apoyar el bienestar en...") y sugerencias de abandonar tratamientos
   (→ "siempre como complemento y nunca en reemplazo de lo que te indique
   tu médico"). Probado con 10 casos: 10/10 correctos, sin falsos
   positivos. Integrado al final de `generar_guion()`.
2. **Regla 10 "SEGURIDAD MÉDICA ABSOLUTA"** en las reglas del guionista
   (el LLM recibe la prohibición explícita con ejemplos).
3. **Variedad anti-plantilla**: las frases fijas de CTA de suscripción
   (inicio/mitad/final) y de citas científicas pasaron de 4 a 8 variantes
   cada una, reduciendo el patrón repetitivo entre videos diarios.

**Factores que ya nos protegían** (verificados en esta revisión): guion
único por video con investigación científica propia, keyword y visuales
distintos por tema, duración variable, divulgación de IA en descripción,
voz rotativa entre 4 narradores, disclaimer médico obligatorio.

### ⏰ Corrida perdida del 15-ago-2026: causa real y doble corrección
El 15-ago no se publicó video. Diagnóstico con el log real de GitHub:

1. **La corrida del 14-ago terminó "failed" PERO el video SÍ se publicó**:
   falló únicamente el último paso ("Recordar ideas ya usadas"), porque el
   usuario subió un paquete de actualización MIENTRAS el robot corría, y el
   `git push` de la memoria fue rechazado ("fetch first"). Corregido en el
   workflow: ahora hace `git pull --rebase` + 3 reintentos antes de push.
   ⚠️ Consecuencia real de ese fallo: `data/estado.json` no se guardó, así
   que el robot puede repetir la idea del día anterior una vez (se
   autocorrige en la siguiente corrida exitosa).
2. **El 15-ago GitHub se saltó el cron de las 19:30** (limitación
   documentada de GitHub Actions: los horarios programados no están
   garantizados y en horas de carga se saltan). Corregido con un **cron de
   respaldo a las 21:45 UTC** + un **candado anti-duplicados**
   (`scripts/verificar_si_ya_publico_hoy.py`): si el horario principal ya
   publicó hoy, la corrida de respaldo termina en segundos sin generar
   nada. Probado en ambos casos (con y sin publicación previa).

### 🔬 Agente 28: Portada REAL del estudio en pantalla (auditoría élite 14-ago-2026)
Resultado de una auditoría brutal pedida por el dueño del canal: hasta esa
fecha, la "toma del documento" en las citas científicas era metraje de
stock genérico (una persona leyendo papeles cualesquiera), NO el estudio
citado. `agents/portada_estudio.py` lo corrige de verdad:

- Con el PMID del estudio citado consulta Europe PMC; si el artículo es de
  **acceso abierto**, descarga el **PDF oficial** y renderiza su **primera
  página real** (título, autores, revista, DOI visibles).
- Compone una escena 16:9 estilo documental: la portada real con sombra
  sobre fondo oscuro + franja "ESTUDIO CIENTÍFICO REAL" con revista y año.
- Esa imagen reemplaza el stock en el beat de cita científica
  (`agents/visuals.py`), y el recuadro "ESTUDIO REAL" del editor no se
  dibuja encima (la portada ya trae su propia franja).
- `agents/citas_cientificas.py` ahora **prioriza estudios de acceso
  abierto** al elegir qué citar (son los que tienen portada mostrable).
- Si el estudio no es de acceso abierto, se usa el visual genérico de
  siempre: mostrar un PDF sin licencia no es una opción.
- Probado en vivo con 3 estudios reales distintos (PDFs de 0.7-2 MB,
  portadas renderizadas correctamente).
- Requiere `pymupdf` (añadido a requirements.txt).

### 📋 Resultado de la auditoría élite (14-ago-2026) — honestidad total
1. **Referencias en videos publicados**: los 8 videos del canal hasta esa
   fecha NO tienen ningún enlace PubMed en la descripción (verificado por
   API). Causa raíz: la búsqueda científica en español contra una base en
   inglés (corregida ese mismo día, pendiente de validar en la próxima
   corrida real).
2. **Link del Short**: los enlaces en descripciones de Shorts NO son
   clicables — limitación oficial de YouTube, no un bug nuestro. El enlace
   clicable real va en el comentario automático. La descripción del Short
   ahora dice claramente "el video completo está en el PRIMER COMENTARIO".
3. **Tarjetas y pantallas finales ("ventanitas")**: la API pública de
   YouTube NO permite configurarlas (limitación conocida de la
   plataforma). El video ya incluye una tarjeta visual renderizada de
   "video relacionado" + enlaces en descripción y comentario. Para añadir
   las tarjetas nativas de verdad (opcional, 30 segundos por video, desde
   el celular): YouTube Studio → video → Editar → Tarjetas → Añadir video
   → elegir el video anterior → Guardar. Y para la pantalla final: Editar
   → Pantalla final → plantilla con 1 video + botón de suscripción.

### 🖼️ Miniaturas de máximo 3 palabras + Shorts más cortos (14-ago-2026)
- `agents/thumbnail.py`: el texto de la miniatura pasó de 5 palabras a
  **máximo 3, sin repetidas** (recomendación del grupo de grandes
  creadores citado por la experta ex-YouTube; la miniatura real del
  14-ago decía "ALIMENTOS VISIÓN MEJORA VISIÓN ESTOS", redundante).
- `agents/shorts_creator.py`: `MAX_BEATS_SHORT` bajó de 4 a 2 → Shorts de
  ~25-35s que se ven completos y se repiten (mejor swipe rate y % visto,
  las 2 métricas que deciden si YouTube recomienda un Short).
- `agents/scriptwriter.py`: los nombres de capítulo ahora se piden como
  **búsquedas reales long-tail** ("Cómo tomar magnesio para dormir" en vez
  de "Guía práctica") — los timestamps posicionan búsquedas concretas.
- `agents/scriptwriter.py`: la descripción ahora teje **frases reales del
  autocompletado público de YouTube** ("frases de audiencias similares"),
  excluyendo nombres de otros creadores. Probado en vivo: para "alimentos
  para la visión" devuelve "alimentos para recuperar la visión", "alimentos
  buenos para la vision", "alimentos para la vista"...

### 🎣 Gancho reforzado con datos reales de retención (auditoría agosto 2026)
`agents/viral_strategist.py` fue actualizado con una investigación real
sobre qué hace que alguien se quede viendo un video en sus primeros
segundos (ver sección de más abajo con las fuentes y cifras exactas). En
resumen: ahora el guion sigue una estructura obligatoria de 3 fases en los
primeros 15 segundos (interrupción de patrón → promesa concreta → gancho
de compromiso), evita los "7 asesinos de retención" más comunes, y pide
que el primer visual del video sea el más llamativo y específico de todo
el guion (nunca una escena genérica).

### 🧠 Resiliencia: cascada de proveedores de IA
El Guionista ya no depende de un solo proveedor: si Gemini falla o se
satura (cuota agotada, sobrecarga temporal), prueba automáticamente con
Groq, luego con Ollama local, y solo si todos fallan usa la plantilla local
sin IA. Así un límite temporal de un solo proveedor gratuito no baja la
calidad de todo el video.

**Costo total en dinero: $0.** Lo único que "cuesta" es tu tiempo de configurar
llaves gratuitas una sola vez (15-20 minutos) y la autorización única de
YouTube (obligatoria por seguridad de la plataforma, no se puede evitar).

---

## ✅ Ya probado y funcionando en este entorno

Ya ejecuté el pipeline completo de punta a punta **con llaves reales** (YouTube
Data API + Gemini + Pexels): generó un guion 100% original de 9 capítulos con
IA, lo narró con voz real, descargó video de stock real, lo editó y produjo
un video final de ~9 minutos con audio (`output/video/EJEMPLO_video_real_con_tus_APIs.mp4`)
y su miniatura (`output/thumbnails/EJEMPLO_real_miniatura.png`) con un
fotograma real extraído del propio video. Todo sin publicarlo (modo prueba),
para que lo revises antes de conectarlo a tu canal real.

### Notas técnicas de esta puesta a punto (por si corres esto en una máquina modesta)
- El editor de video renderiza **capítulo por capítulo** y cierra cada clip
  antes de pasar al siguiente, para no agotar la memoria RAM en videos largos
  con muchos clips de stock (probado y corregido en un entorno con solo 2GB
  de RAM). Si tu máquina tiene más RAM, no necesitas cambiar nada.
- Los clips de Pexels se piden en resolución moderada (~960-1280px de ancho)
  a propósito: 1080p no mejora el RPM y sí duplica el tiempo/memoria de render.
- El modelo de Gemini usado es `gemini-2.5-flash` (rápido y dentro de la capa
  gratuita). Si en el futuro Google libera un modelo nuevo, actualízalo en
  `agents/scriptwriter.py`.

---

## 🔑 Paso 1: Consigue tus llaves gratuitas (una sola vez)

### 1. YouTube Data API (para investigar nichos y publicar)
1. Ve a https://console.cloud.google.com/ → crea un proyecto nuevo (gratis).
2. "APIs & Services" → "Library" → busca **YouTube Data API v3** → Enable.
3. "Credentials" → "Create Credentials" → **API key** → cópiala.
4. Pégala en `config/config.yaml` en `apis.youtube_api_key`.
5. Cuota gratuita: 10,000 unidades/día → de sobra para 4 videos/semana.

### 2. Guion con IA (elige una, ambas son gratis)
- **Gemini** (recomendado): https://aistudio.google.com/app/apikey → copiar key → `apis.gemini_api_key`.
- **Groq** (Llama 3, muy rápido): https://console.groq.com/keys → `apis.groq_api_key`.
- Si no configuras ninguna, el sistema usa una plantilla local automática (sin IA) para que nunca se rompa el proceso.

### 3. Voz — **no requiere nada**, ya funciona (Microsoft Edge TTS gratis).

### 4. Banco de video/imágenes gratis
- Pexels: https://www.pexels.com/api/ → `apis.pexels_api_key`.
- Pixabay (respaldo): https://pixabay.com/api/docs/ → `apis.pixabay_api_key`.
- Si no configuras ninguna, se generan fondos automáticos localmente (funciona, pero es menos vistoso).

### 4.b Respaldo de IA para el guion (opcional pero recomendado)
- Groq (Llama 3, gratis): https://console.groq.com/keys → `apis.groq_api_key`.
- Si Gemini se satura o agota su cuota gratuita del día, el sistema prueba
  automáticamente con Groq antes de usar la plantilla local sin IA.

### 4.c Música de fondo (opcional)
- Jamendo: https://devportal.jamendo.com/ → crea una cuenta → crea una
  "aplicación" → copia el "Client ID" → `apis.jamendo_client_id`.
- Solo se usan pistas con licencia que permite uso comercial (se filtra
  automáticamente). Si no la configuras, el video se genera igual, sin música.

### 5. Autorización de tu canal de YouTube (para publicar automáticamente)
1. En Google Cloud Console: "Credentials" → "Create Credentials" → **OAuth client ID** → tipo **Desktop app**.
2. Descarga el JSON → guárdalo como `config/client_secret.json`.
3. En tu computadora (no en la nube) ejecuta una sola vez:
   ```bash
   pip install -r requirements.txt
   python3 setup_youtube_auth.py
   ```
4. Se abrirá tu navegador, inicias sesión con la cuenta dueña del canal y aceptas.
5. Se genera `config/token.json`. Esa es la llave que el robot reutilizará **para siempre**, sin volver a pedirte nada.

> ⚠️ Esta autorización manual y única **no es una limitación del sistema**: es
> el único punto de verificación humana que exige la propia plataforma para
> evitar bots maliciosos. Después de este paso, todo el resto es 100% automático.

> 🔁 **Si ya habías autorizado tu canal antes de la versión con subtítulos**,
> los permisos cambiaron (se agregó el scope `youtube.force-ssl`, necesario
> para subir subtítulos). Vuelve a ejecutar `python3 setup_youtube_auth.py`
> una sola vez más para renovar el permiso; de lo contrario todo sigue
> funcionando igual, solo que sin subir subtítulos automáticamente.

---

## ▶️ Paso 2: Probarlo localmente

```bash
cd yt_agent_system
pip install -r requirements.txt

# Genera 1 video completo pero SIN subirlo (modo seguro de prueba)
python3 orchestrator.py --videos 1 --no-publicar

# Cuando confíes en el resultado, publícalo también (queda como "privado" por defecto)
python3 orchestrator.py --videos 1
```

Los videos quedan en `output/video/`, miniaturas en `output/thumbnails/`.
Revisa el primero MANUALMENTE antes de pasar a automatización 100% desatendida.

---

## ☁️ Paso 3: Automatización 100% en la nube y gratis (sin tu PC encendida)

Se incluye un workflow listo de **GitHub Actions** (gratis: ~2,000 min/mes en
repos privados, ilimitado en públicos) en
`.github/workflows/fabrica_videos.yml`. Corre automáticamente **4 veces por
semana** (Lunes, Miércoles, Viernes y Domingo) sin que tengas que hacer nada:
genera el video largo, lo publica, sube subtítulos, lo agrega a una playlist,
y genera + publica el Short.

### Cómo activarlo (sin usar la terminal, con la web de GitHub)

**1. Crea una cuenta y un repositorio en GitHub** (gratis)
   - Ve a https://github.com/ → crea una cuenta si no tienes.
   - Click en el botón verde **"New"** (o el "+" arriba a la derecha → "New repository").
   - Ponle un nombre, por ejemplo `fabrica-de-videos`.
   - Puede ser **Private** (recomendado) o Public. Click en **"Create repository"**.

**2. Sube los archivos del proyecto**
   - En la página de tu repo recién creado, click en **"uploading an existing file"**.
   - Arrastra ahí TODA la carpeta `yt_agent_system` que descargaste (todos los
     archivos y subcarpetas).
   - ⚠️ **Verifica que NO se suban estos 3 archivos** (no deberían aparecer si
     usaste la carpeta tal cual te la entregué, porque el `.gitignore` los
     excluye cuando usas git normal; pero si subes por arrastre manual en la
     web, revisa tú mismo que NO estén: `config/client_secret.json`,
     `config/token.json`, `config/config.yaml` con tus llaves reales dentro).
     Sí debe subirse `config/config.example.yaml` (ese no tiene llaves reales).
   - Click en **"Commit changes"**.

**3. Configura los "Secrets" (las llaves, pero guardadas de forma segura)**
   - En tu repo → pestaña **Settings** → menú izquierdo **Secrets and
     variables → Actions** → botón **"New repository secret"**.
   - Crea uno por uno estos secretos (nombre exacto a la izquierda, valor a la derecha):

   | Nombre del secreto | Valor |
   |---|---|
   | `YOUTUBE_API_KEY` | tu llave de YouTube Data API |
   | `GEMINI_API_KEY` | tu llave de Gemini |
   | `GROQ_API_KEY` | tu llave de Groq (si la tienes) |
   | `PEXELS_API_KEY` | tu llave de Pexels |
   | `PIXABAY_API_KEY` | tu llave de Pixabay (si la tienes) |
   | `JAMENDO_CLIENT_ID` | tu client_id de Jamendo (si lo tienes) |
   | `CLIENT_SECRET_B64` | resultado de `base64 -w0 config/client_secret.json` |
   | `TOKEN_JSON_B64` | resultado de `base64 -w0 config/token.json` |

   Para los últimos dos, en tu computadora con esos archivos, corre en la terminal:
   ```bash
   base64 -w0 config/client_secret.json
   base64 -w0 config/token.json
   ```
   Copia todo el texto que aparece (es largo, una sola línea) y pégalo como
   el valor del secreto correspondiente.

**4. Actívalo**
   - Ve a la pestaña **"Actions"** de tu repo.
   - Si aparece un botón para habilitar Actions, dale click.
   - Busca el workflow **"Fabrica de Videos YouTube"** → botón **"Run workflow"**
     para probarlo ya mismo, o simplemente espera: el cron programado lo hará
     solo Lunes/Miércoles/Viernes/Domingo.

El robot recuerda automáticamente qué ideas ya usó (`data/estado.json`, se
actualiza con un commit automático) para no repetir contenido.

> 🔁 Recuerda: si acabas de agregar el permiso de subtítulos
> (`youtube.force-ssl`), vuelve a ejecutar `setup_youtube_auth.py` en tu
> computadora, y actualiza el secreto `TOKEN_JSON_B64` en GitHub con el nuevo
> resultado de `base64 -w0 config/token.json`.

---

## 🧠 Cómo decide qué video hacer (resume la estrategia del video analizado)

1. **Nicho**: definido una vez en `config/config.yaml` (por defecto: salud y
   bienestar, el mismo nicho de ejemplo que mencionaron en el video).
2. **TrendScout** busca en YouTube (mercado en inglés = más datos) videos de
   canales pequeños (<250k subs) con muchas más vistas que suscriptores
   (el "outlier score" — exactamente el criterio que explicaba Eric con Viralyt).
3. **Guionista** toma el ángulo/tema (NO el texto) del video ganador y escribe
   un guion 100% original en español, evitando así el "copy-paste" que puede
   generar strikes de derechos de autor o penalización de YouTube por
   contenido duplicado/reciclado.
4. **Narrador + VisualScout + EditorVideo** arman el video final (10-18 min,
   igual que recomendaba el video para maximizar RPM).
5. **Packaging** genera título llamativo + miniatura de alto contraste.
6. **Publicador** sube el video (por defecto como "privado" para que tú
   revises antes — puedes cambiarlo a "public" en `config.yaml` cuando confíes
   en la calidad del sistema).
7. **Analista** (opcional, una vez tengas videos publicados) consulta qué
   ideas funcionaron mejor para retroalimentar futuras elecciones de tema.

---

## ⚠️ Límites reales que debes conocer (para que "automático" no te sorprenda)

1. **YouTube exige monetizar con reglas humanas**: 1,000 suscriptores + 4,000
   horas de reproducción (o 10M vistas en Shorts en 90 días). Ningún sistema,
   de pago o gratis, puede saltarse ese requisito — solo acelerar cómo se
   llega ahí con buen contenido y constancia.
2. **Política de "contenido repetitivo/reciclado"**: desde 2023 YouTube
   desmonetiza canales que solo reempaquetan contenido ajeno sin aporte
   propio. Por eso el Guionista genera texto original y no traduce/copia — pero
   la responsabilidad de mantener valor añadido real es tuya como operador
   del canal.
3. **Los recursos "gratis" tienen límites de cuota** (ej. YouTube API: 10,000
   unidades/día, Gemini/Groq: límites de peticiones por minuto). Para 4
   videos/semana sobra por mucho, pero no sirve para publicar 50 videos/día.
4. **Calidad vs. costo $0**: sin pagar herramientas premium, el video se ve
   bien pero no idéntico a producciones con IA de pago (voces más
   expresivas, b-roll más específico, avatares con rostro). Es un excelente
   punto de partida gratuito, escalable después si genera ingresos.
5. **Nunca compartas tus llaves ni `token.json` públicamente.**
6. Revisa los **Términos de Servicio de YouTube** y las leyes de tu país sobre
   contenido generado por IA y monetización antes de operar a gran escala.

---

## 📁 Estructura del proyecto

```
yt_agent_system/
├── config/
│   ├── config.yaml            <- tu configuración y llaves (NO subir con datos reales)
│   └── config.example.yaml    <- plantilla de referencia
├── agents/
│   ├── trend_scout.py         <- Agente 1: investigación de nicho/ideas
│   ├── scriptwriter.py        <- Agente 2: guion con IA gratuita
│   ├── voice.py                <- Agente 3: narración (edge-tts, gratis)
│   ├── visuals.py              <- Agente 4: banco de video/imágenes gratis
│   ├── video_editor.py         <- Agente 5: ensamblado final (moviepy/ffmpeg)
│   ├── thumbnail.py            <- Agente 6: miniatura (pillow)
│   ├── publisher.py            <- Agente 7: subida a YouTube
│   └── analytics.py            <- Agente 8: métricas para mejorar
├── orchestrator.py              <- El "jefe" que ejecuta todo el flujo
├── setup_youtube_auth.py        <- Autorización única de tu canal
├── requirements.txt
└── .github/workflows/fabrica_videos.yml   <- automatización 100% gratis en la nube
```
