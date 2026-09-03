# PAQUETE LISTO — hotfix + menos riesgo de cuota + horario 3:00 am

Este paquete ya viene preparado para que usted solo reemplace archivos en GitHub.

## Qué corrige este paquete
Trae 3 cosas importantes juntas:

### 1) Corrige el error que tumbó la última corrida
Se arregló en `orchestrator.py`:

- error visto: `NameError: name 're' is not defined`
- arreglo aplicado: se agregó `import re`

### 2) Reduce el riesgo de volver a gastar demasiada cuota en búsquedas
Se mejoró `agents/trend_scout.py`:

- antes podía recorrer demasiadas búsquedas del config
- ahora pone un **tope duro de seguridad por corrida**
- ahora **se detiene apenas ya tiene suficientes candidatos**
- ahora si detecta `429` / `quota exceeded`, **deja de golpear la API**

En palabras simples:
**ya no se pone a insistir tantas veces cuando la cuota está baja o agotada**.

### 3) Deja confirmado el arranque automático temprano
Se incluye `.github/workflows/fabrica_videos.yml` con el horario:

- inicio principal: **3:00 am Colombia**
- respaldo: **5:15 am Colombia**
- publicación sigue preparada para las **2:30 pm**

---

## Archivos que trae este paquete
Debe subir exactamente estos archivos en estas rutas del repositorio:

- `orchestrator.py`
- `agents/trend_scout.py`
- `.github/workflows/fabrica_videos.yml`

Repositorio:

- `https://github.com/albertodouat-netizen/fabrica-de-videos`

---

## Cómo subirlo paso a paso

### Paso 1: descargar y descomprimir
1. Descargue este ZIP.
2. Descomprímalo en su computador.
3. Abra la carpeta descomprimida.

### Paso 2: entrar al repositorio
1. Abra este enlace:
   - `https://github.com/albertodouat-netizen/fabrica-de-videos`
2. Verifique que arriba diga rama `main`.

### Paso 3: subir `orchestrator.py`
1. En el repo, abra el archivo `orchestrator.py`.
2. Pulse el ícono del lápiz **Edit this file**.
3. Borre todo lo que está allí.
4. Abra el `orchestrator.py` de este paquete en su computador.
5. Copie todo.
6. Péguelo completo en GitHub.
7. Todavía no haga el commit final si va a cambiar los otros archivos también.

### Paso 4: subir `agents/trend_scout.py`
1. En el repo, entre a la carpeta `agents`.
2. Abra `trend_scout.py`.
3. Pulse **Edit this file**.
4. Borre todo.
5. Abra el `trend_scout.py` de este paquete.
6. Copie todo.
7. Péguelo completo en GitHub.

### Paso 5: subir `.github/workflows/fabrica_videos.yml`
1. En el repo, entre a la carpeta `.github`.
2. Luego entre a `workflows`.
3. Abra `fabrica_videos.yml`.
4. Pulse **Edit this file**.
5. Borre todo.
6. Abra el `fabrica_videos.yml` de este paquete.
7. Copie todo.
8. Péguelo completo en GitHub.

### Paso 6: hacer el commit
1. Baje al final de la página en GitHub.
2. En el mensaje del commit escriba esto:

```text
Hotfix: import re + control de cuota + horario 3am
```

3. Pulse **Commit changes**.

---

## Cómo revisar que sí quedó bien

### Revisión 1: `orchestrator.py`
Abra:
- `https://github.com/albertodouat-netizen/fabrica-de-videos/blob/main/orchestrator.py`

Arriba, en los imports, debe aparecer:

```python
import re
```

### Revisión 2: `trend_scout.py`
Abra:
- `https://github.com/albertodouat-netizen/fabrica-de-videos/blob/main/agents/trend_scout.py`

Debe verse una parte parecida a esta:

```python
MAX_BUSQUEDAS_YOUTUBE_POR_CORRIDA = 6
```

### Revisión 3: workflow
Abra:
- `https://github.com/albertodouat-netizen/fabrica-de-videos/blob/main/.github/workflows/fabrica_videos.yml`

Debe verse esta línea:

```yaml
- cron: "0 8 * * *"
```

Eso significa 3:00 am Colombia.

---

## Muy importante sobre la cuota
Este paquete **reduce el riesgo** y mejora el comportamiento cuando la cuota está baja.

Pero hay que decirlo claro:
**ningún paquete puede inventar cuota nueva si la cuota diaria ya está agotada**.

Entonces lo correcto es:

1. Subir este paquete.
2. Esperar a que la cuota diaria de YouTube API se recupere.
3. Luego lanzar la corrida manual.

---

## Cómo lanzar la prueba manual
1. Abra:
   - `https://github.com/albertodouat-netizen/fabrica-de-videos/actions`
2. Entre al workflow de la fábrica.
3. Pulse **Run workflow**.
4. Elija la rama `main`.
5. Ejecútelo.

---

## Qué debería pasar después
Lo esperado ahora es esto:

- ya no debe caerse por el bug de `import re`
- la búsqueda de tendencias ya no debe insistir tanto cuando la cuota esté mal
- el sistema mantiene el arranque temprano de 3:00 am

Si aun así falla por otro motivo real, eso también sirve, porque ahora el sistema ya está mostrando el error real en rojo.

Usted solo me manda la captura y yo le preparo el siguiente paquete.

---

## Resumen corto
Haga esto en este orden:

1. Suba los 3 archivos de este paquete.
2. Haga el commit.
3. Espere cuota disponible.
4. Lance **Run workflow**.
5. Si falla, me manda la captura y yo sigo.
