# 🤖 Fábrica de Videos de YouTube — Equipo de Agentes IA (100% Gratis)

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
