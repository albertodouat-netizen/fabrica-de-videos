# Ajustes de publicación y Shorts aplicados

Fecha: 2026-09-14

## Decisión de publicación

Se mantiene la lógica de fondo que tú prefieres:

- día con largo: **largo + Short**
- día siguiente: **otro Short del largo anterior**
- luego vuelve a entrar un **nuevo largo**

## Cómo queda recomendado

### Días con largo
- **Video largo:** 2:30 pm Colombia
- **Short del mismo tema:** 5:30 pm Colombia

¿Por qué así?
Porque si el Short sale unas horas después, el largo ya está publicado y el
puente Short -> largo funciona mejor.

### Días sin largo
- **Short de seguimiento del largo más reciente:** 2:30 pm Colombia

Así cada largo puede tener:
1. un Short el mismo día
2. otro Short al día siguiente

---

## Mejoras aplicadas al sistema

### 1) Shorts más útiles y menos vacíos
Antes varios Shorts quedaban demasiado cortos.

Ahora:
- el Short independiente apunta a **32-44 segundos**
- el Short derivado del largo permite más contenido útil
- se amplió la cantidad de beats
- se exige al menos una acción o solución práctica clara

### 2) Mejor redirección al video largo
Se reforzó el puente con varios cambios:
- el cierre hablado ahora dice **entra a mi perfil** y **mira el video largo**
- la tarjeta final del Short ahora muestra mejor esa instrucción
- la descripción del Short también lo dice más claro
- el comentario del Short ya no entierra el enlace: ahora abre directo con el link al largo
- en días sin largo, el sistema prioriza hacer el Short del **largo más reciente**

### 3) Pedir likes además de suscripción
Ahora el sistema también pide:
- suscripción
- like
- comentario
- compartir

Pero sin sorteos ni trucos prohibidos.

### 4) Más énfasis en evidencia y utilidad
Se reforzó que el mensaje visible diga:
- información clara
- respaldo científico real
- soluciones prácticas
- nada de promesas milagrosas

### 5) Dos voces en videos largos
Se añadió modo opcional para largos:
- voz femenina
- voz masculina
- alternancia por capítulo

Objetivo:
que el largo no suene tan plano.

En Shorts esta alternancia se apaga sola para no romper el ritmo.

---

## Archivos tocados

- `agents/short_independiente.py`
- `agents/shorts_creator.py`
- `agents/engagement_cta.py`
- `agents/promocion_cruzada.py`
- `agents/voice.py`
- `agents/publisher.py`
- `orchestrator.py`
- `config/config.example.yaml`

---

## Resumen muy simple

La estrategia queda así:

- **los largos no se paran**
- **los Shorts siguen diarios**
- **los Shorts ahora dejan más valor útil**
- **el puente hacia el largo queda más claro**
- **se pide like además de suscripción**
- **el largo puede sonar con dos voces para evitar monotonía**
