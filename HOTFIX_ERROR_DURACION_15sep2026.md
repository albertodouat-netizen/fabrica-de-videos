# Hotfix: error de duración mínima en GitHub Actions
**Fecha:** 15-sep-2026

## Causa exacta confirmada
El archivo `resultado_corrida.json` de la corrida fallida mostró este error:

`RuntimeError: La narración real quedó en 4.7 min, por debajo del mínimo duro de 16 min. Se aborta para no subir otro largo demasiado corto.`

## Qué estaba mal en el código
En `agents/scriptwriter.py`, el sistema intentaba extender el guion si quedaba corto.

Pero había un problema:
- si la extensión fallaba o detectaba que el guion seguía siendo demasiado corto,
- ese error se atrapaba,
- se mostraba solo como aviso,
- y el pipeline seguía igual hasta narrar todo.

Resultado:
- se perdían 6 a 11 minutos de ejecución,
- se gastaba cuota/tiempo,
- y recién al final el orquestador abortaba por duración real insuficiente.

## Qué corrige este hotfix
Ahora `agents/scriptwriter.py` hace esto:
1. **si el control de duración lanza un error real, lo respeta y aborta temprano**;
2. **si no se pudo extender/verificar y el guion sigue por debajo del mínimo duro, aborta antes de narrar**;
3. **hace una última verificación determinista final antes de narrar**.

## Efecto práctico
Con este hotfix:
- el sistema fallará **mucho antes**,
- el error saldrá **más claro**,
- y no perderás tantos minutos en una corrida inviable.

## Importante
Este hotfix **mejora el diagnóstico y evita perder tiempo**, pero la raíz de fondo sigue siendo que el proveedor de guion devolvió un largo demasiado corto o no logró extenderlo lo suficiente.

O sea:
- **ya sabemos exactamente por qué falló**,
- y **ya evitamos que vuelva a fallar tarde**,
- pero si quieres que además falle menos por contenido corto, el siguiente paso sería reforzar aún más la generación/expansión del guion.

## Archivo modificado
- `agents/scriptwriter.py`
