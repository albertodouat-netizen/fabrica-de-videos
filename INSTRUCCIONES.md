# PAQUETE 3 — Auditoría + blindaje de idioma y portadas

Fecha: 03-sep-2026

## ¿Para qué sirve este paquete?
Este paquete corrige 2 problemas que encontré al revisar el canal públicamente:

1. **Mezcla español/inglés** en descripciones y textos visibles.
2. **Portadas demasiado centradas en personas**, en vez de mostrar con fuerza el tema real.

Además, dentro del paquete va una **auditoría escrita** del canal y un **script** para repetir la auditoría en el futuro.

---

## Qué trae este paquete

### Archivos de código corregidos
- `agents/control_calidad_idioma.py`
- `agents/scriptwriter.py`
- `agents/viral_strategist.py`
- `agents/shorts_creator.py`
- `agents/short_independiente.py`
- `agents/equipo_portadas.py`
- `agents/thumbnail.py`
- `agents/promocion_cruzada.py`
- `agents/publisher.py`
- `scripts/auditar_canal_publico.py`

### Evidencia de la revisión
- `AUDITORIA_MINUCIOSA_IDIOMA_PORTADAS_03sep2026.md`
- `evidencia_publica/AUDITORIA_PUBLICA.md`
- `evidencia_publica/metadata.json`
- `evidencia_publica/english_audit.json`
- `evidencia_publica/contactsheet_videos.jpg`
- `evidencia_publica/contactsheet_shorts.jpg`

---

## Qué corrige exactamente

### 1) Idioma
- ya no se toman sugerencias SEO en inglés para meterlas tal cual en el texto visible;
- el guionista ahora tiene una regla dura: **todo lo visible y narrado debe quedar en español**;
- si una descripción sale contaminada, el publicador la reconstruye en español antes de subir;
- las referencias científicas públicas ya no muestran el título del estudio en inglés dentro de la descripción;
- los Shorts pasan a usar `#VideoCorto` en la descripción en vez de `#Shorts`.

### 2) Portadas
- la portada ahora debe priorizar el **tema** como protagonista;
- si el tema tiene un objeto concreto, bebida, suplemento, alimento o parte del cuerpo, eso va primero;
- se evita el patrón de “solo una cara/persona” cuando el tema permite algo mejor;
- se reemplaza el uso visible de palabras inglesas como `STOP` en el texto de portada;
- incluso el generador de respaldo dejó de pedir automáticamente una persona sonriente.

---

## Cómo instalarlo en GitHub (paso a paso, muy simple)

### Opción A — la más fácil
1. Descarga el archivo ZIP:
   - `paquete_AUDITORIA_IDIOMA_PORTADAS_03sep2026.zip`
2. Descomprímelo en tu computador.
3. Entra a tu repositorio de GitHub.
4. Sube **reemplazando** los archivos con el mismo nombre.
5. Haz el commit.

### Opción B — arrastrar carpeta por carpeta
Copia al repo exactamente estas rutas:
- `agents/...`
- `scripts/auditar_canal_publico.py`
- `AUDITORIA_MINUCIOSA_IDIOMA_PORTADAS_03sep2026.md`
- carpeta `evidencia_publica/`

---

## Cómo comprobar que quedó bien
Después de subirlo:

1. Ejecuta manualmente GitHub Actions una vez.
2. Cuando termine una corrida nueva, revisa:
   - que la descripción no tenga frases en inglés metidas dentro del texto normal;
   - que la portada no diga `STOP` ni muestre solo una persona si el tema permite algo más claro;
   - que el tema principal sí se vea (ejemplo: reloj 3:00 am para cortisol, magnesio visible para magnesio, bebida visible para circulación).

---

## Cómo repetir la auditoría más adelante
Si quieres volver a revisar el canal con evidencia automática, usa:

```bash
python3 -m pip install yt-dlp requests pillow
python3 scripts/auditar_canal_publico.py --canal https://www.youtube.com/@SaludNaturalDiaria
```

Eso te dejará una carpeta con:
- miniaturas descargadas,
- metadata,
- lista de posibles mezclas español/inglés,
- hojas de contacto para revisar visualmente.

---

## Hallazgo importante de esta revisión
Durante esta auditoría pública ya apareció un **Short de cortisol** en el canal:
- `ps4F295cmXU`

O sea: **el Short faltante parece ya existir públicamente**.

---

## Archivo principal para leer primero
Abre este:
- `AUDITORIA_MINUCIOSA_IDIOMA_PORTADAS_03sep2026.md`

Ahí te dejé, en palabras simples:
- qué encontré,
- cuáles videos están mal,
- cuáles están mejor,
- y qué conviene arreglar primero.
