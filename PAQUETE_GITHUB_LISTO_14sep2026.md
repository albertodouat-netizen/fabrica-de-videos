# Paquete completo listo para cargar en GitHub
**Fecha:** 14-sep-2026

Este paquete está pensado para que lo subas a GitHub **sin confundirte** y **sin subir archivos basura o secretos**.

---

## 1) Qué incluye este paquete

### Archivos NUEVOS que sí debes subir
- `agents/control_calidad_idioma.py`
- `agents/estrategia_audiencia.py`
- `scripts/detectar_short_pendiente.py`
- `ANALISIS_ESTATISTICAS_Y_DECISIONES_14sep2026.md`
- `PAQUETE_FINAL_HORARIOS_ALGORITMO_SEO_14sep2026.md`
- `.gitignore`

### Archivos MODIFICADOS que sí debes subir
- `.github/workflows/fabrica_videos.yml`
- `orchestrator.py`
- `scripts/verificar_si_ya_publico_hoy.py`
- `agents/shorts_creator.py`
- `agents/short_independiente.py`
- `agents/engagement_cta.py`
- `agents/promocion_cruzada.py`
- `agents/scriptwriter.py`
- `agents/equipo_portadas.py`
- `agents/thumbnail.py`
- `agents/viral_strategist.py`
- `config/config.example.yaml`

---

## 2) Qué mejoras contiene

### Publicación y calendario
- Generación automática desde **3:00 am Colombia**.
- Publicación del **video largo** a **19:30 UTC** = **2:30 pm Colombia**.
- Publicación del **Short del día siguiente / independiente / rescate** a **19:00 UTC** = **2:00 pm Colombia**.
- Publicación del **Short del mismo día** a **21:00 UTC** = **4:00 pm Colombia**.
- Lógica para detectar si ya se publicó el largo del día.
- Lógica para detectar si falta el **Short derivado** y publicar **solo ese Short pendiente**.

### SEO / viral / empaque
- Mejoras de títulos para evitar repetir siempre las mismas fórmulas.
- Mejoras para priorizar **mujeres 55+ / 65+**.
- Reglas más fuertes de gancho, retención y puente **Short -> largo**.
- Mejoras en portadas para mostrar más imagen, menos texto repetido y más relación con el tema.
- Reforzado el enfoque de información **real, científica y práctica**.

### Idioma y CTAs
- Corrección de frases públicas para usar **me gusta** en vez de **like**.
- Nuevo control para detectar anglicismos visibles en textos públicos.
- Shorts y largos más consistentes en español natural.

### Política de duración
- Largos orientados a mínimo **16 minutos** y objetivo **29+ minutos** cuando aplique.

---

## 3) Verificación técnica ya hecha

Se verificó compilación Python en los archivos clave del sistema y **pasó sin errores**.

---

## 4) Archivo importante que debes entender

En este repo **no existe**:
- `config/config.yaml`

Sí existe:
- `config/config.example.yaml`

### ¿Qué significa?
Los horarios nuevos ya quedaron bien puestos en el archivo ejemplo, pero debes confirmar en producción si el sistema:
1. usa directamente `config/config.example.yaml`, o
2. genera otro `config/config.yaml` fuera de este repo.

---

## 5) Cómo subirlo a GitHub — opción fácil por web

## Método A: subir desde la página de GitHub
1. Abre tu repositorio en GitHub.
2. Entra a la rama donde quieras guardar los cambios.
3. Usa **Add file** -> **Upload files**.
4. Sube **solo** los archivos listados en las secciones 1 y 2.
5. No subas carpetas como `__pycache__` ni archivos de `output/`.
6. Escribe este mensaje de commit:

### Título del commit
`feat: paquete final de horarios, shorts pendientes, SEO y control de idioma`

### Descripción del commit
`Se ajusta el calendario de publicación, se agrega rescate de Short pendiente, se mejora SEO y empaque para audiencia femenina 55+, se corrigen CTAs públicos al español natural y se añaden documentos finales de estrategia.`

7. Haz clic en **Commit changes**.

---

## 6) Cómo subirlo a GitHub — opción por comandos

Si prefieres copiar y pegar comandos:

```bash
git add .gitignore \
  .github/workflows/fabrica_videos.yml \
  orchestrator.py \
  scripts/detectar_short_pendiente.py \
  scripts/verificar_si_ya_publico_hoy.py \
  agents/control_calidad_idioma.py \
  agents/estrategia_audiencia.py \
  agents/engagement_cta.py \
  agents/promocion_cruzada.py \
  agents/scriptwriter.py \
  agents/short_independiente.py \
  agents/shorts_creator.py \
  agents/equipo_portadas.py \
  agents/thumbnail.py \
  agents/viral_strategist.py \
  config/config.example.yaml \
  ANALISIS_ESTATISTICAS_Y_DECISIONES_14sep2026.md \
  PAQUETE_FINAL_HORARIOS_ALGORITMO_SEO_14sep2026.md \
  PAQUETE_GITHUB_LISTO_14sep2026.md

git commit -m "feat: paquete final de horarios, shorts pendientes, SEO y control de idioma"

git push origin main
```

> Si tu rama no es `main`, cambia `main` por el nombre real de tu rama.

---

## 7) Qué NO debes subir

No subas esto:
- `__pycache__/`
- `agents/__pycache__/`
- `output/`
- `config/token.json`
- `config/client_secret.json`
- `config/config.yaml` (si tiene secretos locales)
- cualquier `.env`
- videos, audios o archivos temporales de prueba

Para ayudarte con eso, ya te dejé creado este archivo:
- `.gitignore`

---

## 8) Orden recomendado para subirlo

Sube en este orden:
1. `.gitignore`
2. archivos de lógica del sistema
3. archivos de estrategia / docs finales

Más simple todavía:
- si vas a subir todo el repo, primero asegúrate de que GitHub **no incluya** `output/`, `__pycache__/` ni secretos.

---

## 9) Archivo principal para leer antes de subir

Lee primero este archivo:
- `PAQUETE_FINAL_HORARIOS_ALGORITMO_SEO_14sep2026.md`

Y usa este como guía para la subida:
- `PAQUETE_GITHUB_LISTO_14sep2026.md`

---

## 10) Mi recomendación final

Si quieres hacer una subida limpia y segura, sube **solo** los archivos de este paquete, no todos los cambios sueltos del repositorio.

Así te evitas:
- subir cachés,
- subir pruebas,
- subir resultados temporales,
- o mezclar cambios viejos con este paquete final.
