# PAQUETE FIX — Optimización de duración, Shorts, descripciones y veto de audio

Fecha: 31-ago-2026

## Qué corrige este paquete

1. **Bloquea mejor** temas vetados de audio/frecuencias/ASMR/ruido blanco/432Hz/528Hz/741Hz.
2. **Exige videos largos más extensos**:
   - mínimo duro: **16 minutos reales**
   - meta élite: **29+ minutos**
3. **Evita publicar largos demasiado cortos**:
   - si la narración real queda por debajo de 16 min, la corrida se aborta
   - así no vuelve a subirse otro largo de 8 minutos por error
4. **Acorta y endurece los Shorts**:
   - menos beats
   - cierre más corto
   - tope duro de duración
5. **Portada del Short visible por varios frames al inicio**:
   - ya no solo un flash corto
   - se mantiene ~2.2s al comienzo
   - también mejora la miniatura extraída
6. **Limpia las descripciones futuras**:
   - deja de depender del párrafo spammy del LLM
   - construye una descripción más humana y creíble
7. **Sube el objetivo por defecto** del config.example a **29 min**.

## Archivos incluidos

- `orchestrator.py`
- `agents/scriptwriter.py`
- `agents/shorts_creator.py`
- `agents/viral_strategist.py`
- `agents/equipo_portadas.py`
- `config/config.example.yaml`
- `TEXTOS_SUGERIDOS_VIDEO_ACTUAL.md`

## Cómo subirlo a GitHub

1. Descomprime este paquete.
2. Entra a tu repo local o a la carpeta que vas a subir manualmente a GitHub.
3. **Copia y reemplaza** los archivos respetando la misma estructura de carpetas.
4. Verifica que **NO** viajes secretos ni archivos privados.
5. Sube el contenido al repo.
6. Espera la próxima corrida.

## Qué deberías ver en la próxima corrida

- si el tema viene disfrazado como `432Hz`, `528 hz`, `white noise`, `asmr`, `binaural`, etc., debe quedar vetado
- si el largo no alcanza 16 min reales de narración, no debe publicarse
- el Short debe salir bastante más corto y con mejor loop
- la portada del Short debe verse al principio durante más tiempo
- la descripción del largo debe sentirse humana, no rellena de keywords raras

## Nota importante

Este paquete **no contiene secretos**.
