# PAQUETE FIX — Inicio 3:00 am Colombia + publicación 2:30 pm

Fecha: 01-sep-2026

## Objetivo de este fix
Hacer que la fábrica empiece mucho más temprano para darle toda la madrugada y la mañana a la generación, pero manteniendo la publicación exacta a las **2:30 pm Colombia** mediante `publishAt`.

## Lo que cambia

### 1) Nuevo horario del workflow
- **Corrida principal:** `08:00 UTC` = **3:00 am Colombia**
- **Corrida de respaldo:** `10:15 UTC` = **5:15 am Colombia**
- **Publicación programada:** se mantiene en `19:30 UTC` = **2:30 pm Colombia**

### 2) Más margen real de ejecución
- `timeout-minutes` sube de **300** a **360**
- `PRESUPUESTO_MINUTOS` sube de **90** a **240**

### 3) Se evita solapamiento entre corridas
Se agrega `concurrency` al workflow:
- si la corrida de las 3:00 am sigue viva cuando llega la de respaldo,
  la segunda **no corre al mismo tiempo**
- queda en cola y arranca solo cuando termine la primera

### 4) Se corrige el candado de doble publicación
Antes, si un video quedaba **privado/programado**, no aparecía todavía en el RSS público de YouTube y la corrida de respaldo podía creer que "no hay video hoy".

Ahora el candado cruza:
- el **RSS público** del canal
- la **memoria local** del robot (`ultima_ejecucion`)

Así también detecta videos ya generados/subidos hoy aunque sigan privados o programados.

## Limitación real que debes conocer
GitHub Actions **NO permite tiempo ilimitado**.
Aunque ahora la generación arranca a las 3:00 am, el job sigue teniendo un tope duro de **6 horas**.

Este paquete deja la configuración así:
- hasta **4 horas** de trabajo pesado antes del modo apurado
- alrededor de **2 horas de colchón** para render + subida

Eso es lo más sólido para que llegue listo a las 2:30 pm sin volver a chocar tan fácil con el límite del job.

## Archivos incluidos
- `.github/workflows/fabrica_videos.yml`
- `scripts/verificar_si_ya_publico_hoy.py`

## Cómo subirlo
1. Descomprime el zip.
2. Copia los archivos respetando exactamente sus rutas.
3. Súbelos a GitHub.
4. Verifica luego en el repo público que el cron quedó así:
   - `0 8 * * *`
   - `15 10 * * *`
5. Espera la próxima corrida.

## Qué deberías ver después
- La generación arranca a las **3:00 am Colombia**.
- Si GitHub se salta esa corrida, hay respaldo a las **5:15 am Colombia**.
- No debería arrancar otra corrida larga encima de la primera.
- Si el primer largo ya quedó programado/privado, la de respaldo debe frenarse.
- La publicación debe seguir saliendo a las **2:30 pm Colombia**.
