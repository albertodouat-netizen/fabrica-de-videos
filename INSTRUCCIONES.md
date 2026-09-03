# PAQUETE LISTO — rescate del Short faltante del video largo

Este paquete está hecho para corregir exactamente este problema:

- el video largo **sí** quedó publicado
- pero su **Short derivado no quedó publicado**
- en este caso concreto: el largo de **cortisol** quedó sin su Short

---

## Qué hace este paquete
Trae una mejora nueva para que el sistema haga esto:

### 1) Detectar un largo publicado sin Short
Si encuentra un video largo publicado que quedó con `short_id` vacío, lo marca como pendiente.

### 2) Reintentar SOLO el Short faltante
Ya no toca volver a generar otro video largo.

### 3) Priorizar ese rescate antes de un Short independiente
O sea:
- primero intenta sacar el **Short faltante del largo**
- solo si no hay ningún faltante, entonces publica el **Short independiente normal**

### 4) Dejar evidencia clara en GitHub Actions
Ahora el workflow muestra pasos específicos para eso.

---

## Este paquete sirve también para el caso actual del cortisol
Sí.

Este paquete está pensado para que, después de subirlo y lanzar una corrida manual:

- el sistema detecte que el largo de cortisol ya existe
- vea que ese largo no tiene `short_id`
- e intente crear/publicar **solo ese Short faltante**

---

## Archivos que debe subir al repositorio
Suba estos archivos exactamente en estas rutas:

- `orchestrator.py`
- `scripts/verificar_resultado_corrida.py`
- `scripts/detectar_short_pendiente.py`
- `.github/workflows/fabrica_videos.yml`

Repositorio:
- `https://github.com/albertodouat-netizen/fabrica-de-videos`

---

## Cómo subirlo paso por paso

### Paso 1
Descargue el ZIP y descomprímalo.

### Paso 2
Abra su repositorio GitHub.

### Paso 3
Suba/reemplace estos 4 archivos uno por uno:

#### Archivo 1
- Ruta: `orchestrator.py`

#### Archivo 2
- Ruta: `scripts/verificar_resultado_corrida.py`

#### Archivo 3
- Ruta: `scripts/detectar_short_pendiente.py`

#### Archivo 4
- Ruta: `.github/workflows/fabrica_videos.yml`

### Paso 4
Haga el commit con un mensaje como este:

```text
Rescate: reintentar short faltante de largo publicado
```

---

## Qué debe hacer después de subirlo
Después de subir el paquete, haga una corrida manual.

### Pasos
1. Entre a:
   - `https://github.com/albertodouat-netizen/fabrica-de-videos/actions`
2. Abra el workflow:
   - `Fabrica de Videos YouTube (100% gratis y automatico)`
3. Pulse **Run workflow**
4. Elija la rama `main`
5. Pulse **Run workflow** otra vez

---

## Qué debería pasar en esta corrida
Como hoy ya existe el largo de cortisol, el sistema **no debería crear otro largo**.

Debería hacer esto:

1. detectar que ya hubo largo
2. detectar que hay un **Short derivado pendiente**
3. intentar publicar **solo el Short faltante del cortisol**
4. no publicar el Short independiente mientras exista ese faltante

---

## Cómo reconocer en GitHub que sí hizo lo correcto
En la corrida deberían aparecer pasos como estos:

- `Detectar si hay Short derivado pendiente`
- `Reintentar Short derivado pendiente (si existe)`
- `Verificar que el Short derivado pendiente produjo resultado real`

Si ve esos pasos, el paquete quedó funcionando.

---

## Resultado esperado
### Si sale bien
Debe quedar:
- el largo de cortisol ya publicado
- y ahora también su **Short faltante** publicado

### Si falla
No pasa nada: me manda la captura del error y yo le preparo el siguiente arreglo.

---

## Resumen corto
Haga esto en este orden:

1. Suba los 4 archivos del paquete
2. Haga commit
3. Lance **Run workflow**
4. El sistema debe intentar recuperar el **Short faltante del cortisol**
5. Si falla, me manda captura
