# HOTFIX listo para subir a GitHub

## Qué corrige este paquete
Este paquete corrige el error real que tumbó la corrida manual más reciente:

- Error visto en GitHub Actions: `NameError: name 're' is not defined`
- Archivo afectado: `orchestrator.py`
- Solución aplicada: se agregó `import re` al inicio del archivo.

## Importante
Este hotfix **sí corrige el bug del código**.

Pero la corrida también mostró otro problema aparte:

- YouTube Data API devolvió errores `429` por **quota/search quota exceeded**.

Eso significa que, aunque suba este hotfix, conviene volver a ejecutar cuando la cuota de la API ya se haya recuperado, o usando una clave/proyecto con cuota disponible.

---

## Qué trae este paquete
Este paquete contiene:

- `orchestrator.py`  ← archivo corregido
- `INSTRUCCIONES.md` ← esta guía

---

## Dónde va el archivo en GitHub
El archivo corregido debe quedar en esta ruta del repositorio:

- `orchestrator.py`

Es decir: va en la **raíz** del repositorio, reemplazando el archivo actual.

Repositorio:

- `https://github.com/albertodouat-netizen/fabrica-de-videos`

---

## Cómo subirlo paso a paso

### Opción simple: reemplazar el archivo desde la web de GitHub
1. Descargue este paquete ZIP.
2. Descomprímalo.
3. Entre a su repositorio:
   - `https://github.com/albertodouat-netizen/fabrica-de-videos`
4. Verifique que esté en la rama `main`.
5. Abra el archivo actual `orchestrator.py`.
6. Pulse el ícono del lápiz **Edit this file**.
7. Borre todo el contenido del archivo actual.
8. Abra el `orchestrator.py` de este paquete en su computador.
9. Copie todo.
10. Péguelo completo en GitHub.
11. Baje hasta abajo.
12. En el cuadro de mensaje escriba algo como:
    - `Hotfix: agregar import re en orchestrator`
13. Pulse **Commit changes**.

---

## Cómo comprobar que sí quedó bien subido
Después del commit:

1. Abra otra vez este enlace:
   - `https://github.com/albertodouat-netizen/fabrica-de-videos/blob/main/orchestrator.py`
2. Revise el inicio del archivo.
3. Debe verse una línea así:

```python
import re
```

Si esa línea aparece en los imports de arriba, el hotfix quedó subido.

---

## Cuándo volver a ejecutar
Como también hubo error de cuota de YouTube API, lo recomendable es:

1. Subir primero este hotfix.
2. Esperar a que la cuota de la API vuelva a estar disponible.
3. Luego lanzar una nueva corrida manual.

---

## Cómo lanzar la corrida manual
1. Entre aquí:
   - `https://github.com/albertodouat-netizen/fabrica-de-videos/actions`
2. Abra el workflow:
   - `fabrica_videos.yml`
3. Pulse **Run workflow**.
4. Elija la rama `main`.
5. Ejecútelo.

---

## Qué resultado esperar
Después de este hotfix pueden pasar 2 cosas:

### Caso 1: sale bien
Perfecto. Eso confirma que el bug `import re` era el bloqueo principal.

### Caso 2: vuelve a fallar
También sirve, porque ahora el sistema ya está mostrando el fallo real en rojo.
En ese caso me envía la captura o el log y yo le preparo el siguiente arreglo.

---

## Resumen corto
Haga esto en este orden:

1. Suba el `orchestrator.py` de este paquete.
2. Verifique que tenga `import re`.
3. Espere cuota disponible de YouTube API.
4. Lance una nueva corrida manual.
5. Si falla, me manda la captura y yo le doy el siguiente paquete ya listo.
