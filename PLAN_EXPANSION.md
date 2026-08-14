# Plan de expansión a más canales (confirmado por Alberto, 14-ago-2026)

## Decisión
Crear una PLANTILLA REPLICABLE para abrir nuevos canales automatizados,
**solo cuando el canal actual (Salud Natural Diaria) esté rodando estable
unos días** — no antes. Escalar lento y con calidad, nunca en masa
(riesgo real: YouTube penaliza redes de canales producidos en masa y puede
cerrar TODOS los canales vinculados, incluido el que ya funciona).

## Qué incluirá la plantilla cuando se construya
1. Repositorio plantilla ("fábrica base") listo para clonar por canal.
2. Un solo archivo de configuración por canal: nicho, estilo, voz,
   horario, idioma — todo lo demás idéntico.
3. Checklist paso a paso en español (30-60 min por canal, UNA sola vez):
   - Crear canal en YouTube (mismo Gmail u otro).
   - Verificar teléfono (máx ~2 canales/año por número).
   - Proyecto Google Cloud + APIs + pantalla de consentimiento.
   - Autorización OAuth (clic humano obligatorio, no automatizable).
   - Pegar secrets en GitHub del nuevo repo.
4. Reglas anti-"granja de contenido": estilos, voces, miniaturas y
   horarios DIFERENTES por canal; nichos distintos; nada de contenido
   duplicado entre canales.

## Criterios para considerar "estable" el canal actual
- [ ] Corrida diaria de las 14:30 (hora Colombia) sale sin errores varios días seguidos.
- [ ] Videos largos ~15-20 min de forma consistente.
- [ ] Referencias científicas REALES y relevantes en la descripción.
- [ ] Cita científica visible en el video (voz + toma de documento + recuadro ESTUDIO REAL).
- [ ] Shorts sin defectos (sin jerga interna narrada, sin texto interno en
      pantalla, sin imagen congelada al final).
- [ ] Sin incidentes de contenido visual inapropiado.

## Pendientes que siguen en pausa (decisión del usuario)
- Afiliados/referidos reales ("eso lo hacemos luego").
- Expansión a otro idioma (anotado para después).

## Estado
- 14-ago-2026: usuario cargó paquete_ACTUALIZACION_precision_cientifica.zip
  y luego se le entregó paquete_ACTUALIZACION_calidad_short.zip (correcciones
  del Short: jerga SEO narrada, texto interno en pantalla, imagen congelada).
  Falta confirmar que este último también fue subido a GitHub.
- Próxima verificación: revisar el video del día siguiente (después de las
  14:30 hora Colombia) fotograma por fotograma y por API.
