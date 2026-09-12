# Revisión breve: por qué hoy salió un Short de otro tema

Fecha: 2026-09-12

## Respuesta corta

**Hoy NO se ejecutó la ruta de video largo + Short derivado.**

Lo que pasó hoy fue esto:
1. GitHub corrió dos veces la fábrica:
   - `34682193130` a las **03:01** Colombia
   - `34688361641` a las **05:24** Colombia
2. En las dos corridas, el paso de **video largo + Short** quedó **saltado**.
3. En vez de eso, el sistema ejecutó la ruta:
   - **`Short independiente (días sin video largo)`**
4. Por eso salió un Short de **otro tema** y no un Short del mismo tema del último largo.

---

## Evidencia exacta de GitHub

En las dos corridas de hoy:
- paso 8 `Ejecutar el equipo de agentes (video largo + Short + publicación)` = **skipped**
- paso 13 `Short independiente (días sin video largo)` = **success**
- paso 14 `Verificar que la corrida de Short independiente produjo resultado real` = **success**

Eso significa que **hoy el sistema decidió que NO tocaba largo**.

---

## Qué Short salió hoy

Short público detectado hoy:
- **`uVLUd4vG1mU`**
- Título: **`El Dato Que No Conocías De Error Que Lo Agrava #salud #VideoCorto`**
- Publicación pública: **2026-09-12 14:30 Colombia**
- Enlace al largo dentro de la descripción: **`pwxKRTKTXqM`**
  - largo relacionado: **`Remedio Natural Para Insomnio, El Error Que Lo Agrava`**

O sea:

> el Short de hoy salió enlazado a un largo viejo de insomnio, no al largo más reciente del clúster antiinflamación.

---

## La causa real

Encontré una falla lógica en el candado que decide si hoy toca largo o no.

### Cómo debería funcionar
- el sistema está configurado para hacer **video largo cada 2 días**
- los días intermedios hace **Short independiente**

### El problema
El candado está leyendo el campo:
- `ultima_ejecucion`

como si siempre significara:
- **último video largo**

Pero eso ya no es verdad.

Ese campo también se actualiza cuando se publica un:
- **Short independiente**

Entonces pasa esto:
1. se publica un Short independiente
2. `ultima_ejecucion` queda con la fecha de hoy
3. al día siguiente, el candado cree que “ya hubo largo reciente”
4. vuelve a saltarse el largo
5. publica otro Short independiente

### Prueba clara
En el estado público actual vi esto:
- `ultimo_largo_confirmado` = **2026-09-09**
- `ultima_ejecucion` = **2026-09-12**

Eso demuestra que:
- el último **largo real** fue el **9 de septiembre**
- pero el candado está mirando una fecha más nueva causada por Shorts

---

## Conclusión simple

**No fue que hoy el sistema “eligió mal” por casualidad.**

Lo que ocurrió es esto:

> **el candado bloqueó el largo por error, y por eso entró la ruta de Short independiente.**

Y como los Shorts independientes rotan entre largos anteriores del canal,
**hoy escogió un tema viejo** (`pwxKRTKTXqM`) en vez de acompañar al largo más reciente.

---

## Qué ya preparé para corregirlo

Preparé un hotfix local para que el candado mire primero:
- `ultimo_largo_confirmado.fecha`

y no confunda Shorts con largos.

Con ese ajuste, hoy el sistema habría reconocido correctamente que:
- el último largo confirmado fue el **9 de septiembre**
- así que **sí tocaba largo** el **12 de septiembre**

---

## Resultado final en una frase

**Hoy salió un Short de otro tema porque la lógica que decide si toca video largo quedó confundiendo la fecha del último Short con la del último largo.**
