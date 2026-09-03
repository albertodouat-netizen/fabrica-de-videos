# PAQUETE UPDATE COMPLETO GITHUB (03-sep-2026)

Este paquete es para el **repo actual**:
- `albertodouat-netizen/fabrica-de-videos`

## Súbelo COMPLETO
No subas solo una parte.

Debes reemplazar exactamente estos archivos en GitHub:

1. `.github/workflows/fabrica_videos.yml`
2. `orchestrator.py`
3. `agents/short_independiente.py`
4. `scripts/verificar_resultado_corrida.py`
5. `data/estado.json`

---

## Por qué este paquete es completo
Porque hoy el repo quedó mezclado:
- partes del workflow sí se actualizaron
- partes del orquestador no quedaron bien sincronizadas
- y `data/estado.json` quedó regresado a una memoria vieja

Este paquete deja todo alineado otra vez.

---

## Qué corrige

### 1. GitHub ya no debería mostrar "success" falso
Si falla la publicación real, el workflow debe quedar en rojo.

### 2. Se valida el resultado real de la corrida
Se usa:
- `scripts/verificar_resultado_corrida.py`
- `output/resultado_corrida.json`

### 3. Se fortalece el candado
Si el largo sí alcanza a subirse, queda checkpoint en memoria para que la corrida de respaldo no duplique trabajo.

### 4. Se corrige la memoria pública
`data/estado.json` queda restaurado con los videos confirmados recientes y sin volver a una versión vieja.

---

## Muy importante sobre `data/estado.json`
Este archivo en el repo público quedó mal y por eso también debe reemplazarse.

No omitas este archivo en la subida.

---

## Cómo subirlo

1. Abre el repo en GitHub.
2. Entra a cada ruta correspondiente.
3. Reemplaza los archivos por los de este paquete.
4. Haz commit a `main`.

Si usas **Upload files** por web:
- sube el contenido respetando EXACTAMENTE las carpetas:
  - `.github/workflows/`
  - `agents/`
  - `scripts/`
  - `data/`

---

## Qué hacer inmediatamente después de subirlo

1. Lanza una corrida manual desde **Actions**.
2. Mira si pasa una de estas dos cosas:
   - publica de verdad
   - o falla en rojo con error visible

Eso ya será mejor que seguir teniendo éxitos falsos.

---

## Qué verificar después de subirlo

### En GitHub
Debe existir el paso:
- `Verificar que la corrida larga produjo publicación real`

Y también:
- `Verificar que la corrida de Short independiente produjo resultado real`

### En el repo
Debe existir:
- `scripts/verificar_resultado_corrida.py`

### En `data/estado.json`
Deben volver a aparecer registros recientes del largo y shorts confirmados.

---

## Recomendación
Sube este paquete completo y no mezcles archivos de otros paquetes encima.
