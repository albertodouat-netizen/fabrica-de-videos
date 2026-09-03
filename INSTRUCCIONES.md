# HOTFIX listo — corrige el fallo del rescate del Short pendiente

## Qué pasó
La corrida manual nueva sí detectó correctamente que había un **Short derivado pendiente** del video largo de cortisol.

Pero falló por este error:

- `TypeError: crear_short() got an unexpected keyword argument 'titulo_short_override'`

## Causa real
Había una **mezcla de versiones** en GitHub:

- `orchestrator.py` ya estaba actualizado
- pero `agents/shorts_creator.py` seguía en una versión anterior

Entonces el orquestador nuevo intentó usar una función del Short que el archivo viejo todavía no tenía.

---

## Qué corrige este paquete
Este paquete corrige eso de dos formas:

### 1) Actualiza `agents/shorts_creator.py`
Sube la versión correcta y completa del creador de Shorts.

### 2) Refuerza `orchestrator.py`
Ahora quedó **compatible** con versiones viejas y nuevas del creador de Shorts.

En palabras simples:
si alguna vez vuelve a quedar un archivo mezclado, el sistema ya no debería romperse tan fácil por ese desfase.

---

## Archivos que trae este paquete
Suba estos 2 archivos al repositorio:

- `orchestrator.py`
- `agents/shorts_creator.py`

Repositorio:
- `https://github.com/albertodouat-netizen/fabrica-de-videos`

---

## Cómo subirlo paso a paso

### Archivo 1
- Ruta: `orchestrator.py`
- Reemplace el archivo actual por el de este paquete

### Archivo 2
- Ruta: `agents/shorts_creator.py`
- Reemplace el archivo actual por el de este paquete

### Commit
Use este mensaje:

```text
Hotfix: sincronizar shorts_creator con rescate de short pendiente
```

---

## Qué hacer después
Después de subir estos 2 archivos:

1. Vaya a **GitHub > Actions**
2. Abra el workflow **Fabrica de Videos YouTube (100% gratis y automatico)**
3. Pulse **Run workflow**
4. Elija la rama `main`
5. Ejecútelo

---

## Qué debe pasar ahora
Como ya existe un largo de cortisol sin Short, el sistema debe hacer esto:

1. detectar el Short derivado pendiente
2. reintentar solo ese Short faltante
3. no crear otro video largo
4. no publicar un Short independiente mientras exista ese pendiente

---

## Qué debe mirar en la corrida
Debe ver pasos como estos:

- `Detectar si hay Short derivado pendiente`
- `Reintentar Short derivado pendiente (si existe)`
- `Verificar que el Short derivado pendiente produjo resultado real`

Si esos pasos salen bien, entonces se recuperó el Short faltante del cortisol.

---

## Importante
En la captura también apareció un aviso de traducción `429` de Google Translate.
Eso **no fue la causa principal del fallo**.
El bloqueo real fue el desfase entre:

- `orchestrator.py`
- `agents/shorts_creator.py`

---

## Resumen corto
Haga esto:

1. suba estos 2 archivos
2. haga commit
3. corra **Run workflow**
4. me manda el resultado
