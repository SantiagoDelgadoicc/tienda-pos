# Preguntas al cliente — cierre de caja, usuarios y medios de pago

**Fecha:** 2026-09-22 · *Actualizado el 2026-09-23 con el bloque H1 del efectivo.* · **Para:** la próxima reunión con el cliente
**Alcance:** lo que el cliente pidió el 2026-09-18 y que **sí entra** en este proyecto.

La boleta electrónica, las impresoras y el cajón de dinero **no están en este documento**. Van
aparte, en `docs/BOLETA-ELECTRONICA-SII.md`, porque son otro proyecto y conviene no mezclarlos en la
misma conversación.

---

> **Actualización del 2026-09-24.** El cliente contestó una parte por WhatsApp el 2026-09-23. Las
> respuestas están en la columna de la derecha, con lo que se decidió a partir de ellas. Siguen
> abiertas, por orden de lo que cuestan: **H10** (medianoche), **H8** (nombre de las cajas), la
> ambigüedad de **H1b** (retiros) y el resto del bloque del arqueo, que condicionan la fase 19.

## 1. De dónde salen estas preguntas

El 2026-09-18 el cliente pidió tres cosas:

1. **Un usuario por empleado, con clave única.** En una misma caja pueden vender varios empleados el
   mismo día.
2. **Cierre diario por caja**, donde se vea qué empleados vendieron en esa caja y qué ventas fueron.
3. **Registrar el medio de pago**: efectivo o la máquina de Mercado Pago. Los dos se registran.

Esas tres son requisitos suyos y están en la categoría *Confirmado por el cliente* de `CLAUDE.md`.
Lo que sigue son las preguntas que hacen falta para construirlas sin adivinar, más las que ya
estaban pendientes de antes y que ahora se vuelven urgentes.

---

## 2. Lo que se está construyendo hoy, para que no haya sorpresas

Antes de preguntar conviene decir en voz alta qué se está haciendo, porque varias de estas
decisiones se tomaron por nosotros y el cliente tiene derecho a desmentirlas:

- El cierre diario es **un informe que se calcula al pedirlo**. Se puede mirar las veces que haga
  falta. **No cierra nada, no bloquea la caja y no cuenta el dinero del cajón.** *Esto es
  precisamente lo que H1 pone en duda: si cuentan el efectivo, este punto decae entero.*
- **No hay turnos.** El empleado entra con su clave y cada venta queda a su nombre; el cierre
  agrupa por caja y desglosa por empleado. No se abre ni se cierra ningún turno.
- El medio de pago **lo marca el cajero en pantalla** antes de cobrar. El sistema no habla con la
  máquina de Mercado Pago.
- Al dar de alta a un empleado, **el sistema le genera una clave al azar** y la muestra una sola
  vez. Hay que anotarla.
- Actualizar esto **obliga a una visita a la tienda** con los dos computadores parados un rato,
  porque la caja secundaria no puede vender hasta que ambas estén al día.

Si alguna de esas cinco frases le suena mal al cliente, eso es más valioso que cualquier respuesta
de la tabla de abajo.

---

## 3. Las preguntas que bloquean trabajo

Si la conversación se corta, estas tres tienen que estar contestadas.

| # | Pregunta | Por qué importa | Respuesta |
|---|---|---|---|
| H1 | **Damos por hecho que cuentan la plata del cajón al cerrar y la anotan en un cuaderno.** ¿Es así? | **La más cara del documento, y desde el 2026-09-23 la respuesta probable es que sí.** Si cuentan, el cierre deja de ser un informe calculado y pasa a ser un registro guardado: fondo inicial, conteo real, diferencia y quién cerró. Es una fase entera más, no un ajuste. **Pedir una foto de una página del cuaderno**: las columnas que ya anotan a mano son la especificación, dicha en sus palabras y probada por el uso. | **Sí cuentan** en un cuaderno. **Si quiere que el sistema cuadre el cajón, no lo dijo claro** (respondió "exacto, algo que diga ventas en efectivo y en débito y crédito"). → Santiago: el arqueo es un **modo activable** (fase 19). *2026-09-23* |
| H1b | Durante el día, ¿**sacan o meten plata** del cajón? Pagar al proveedor, mandar a comprar, sacar para depositar, agregar sencillo. | **Es la que decide si el arqueo sirve para algo.** Si sacan plata y el sistema no lo sabe, el cierre muestra diferencia todos los días, el dueño deja de mirarlo en dos semanas, y entonces ya no detecta el caso que importa: que falte plata de verdad. Si la respuesta es sí, hace falta además una pantalla de entradas y salidas de efectivo, y eso es parte del mismo trabajo, no un extra. | Escribió *"Si se anotan todos los retiros en efectivo"*: sin tilde puede ser "sí, se anotan" o un condicional. **Confirmar.** *2026-09-23* |
| H1c | ¿Con cuánta plata empieza el día la caja? ¿Queda sencillo de un día para otro o lo pone alguien cada mañana? ¿Es siempre el mismo monto? | Define si el fondo inicial se teclea cada día, se arrastra del cierre anterior o es una constante. Cambia la pantalla de apertura. | |
| H1d | ¿Quién cuenta el dinero, y qué hacen hoy si no cuadra? | El sistema tiene que hacer lo que ya hacen ellos, no inventar un procedimiento. Define si la diferencia se anota y se sigue, si exige una nota, o si bloquea algo. | |
| H1e | ¿Quiere que el sistema **calcule el vuelto**? | Retira la parte de D-006 que dice "sin cálculo de vuelto". **Ojo con el razonamiento**: el vuelto NO afecta al arqueo, porque entra y sale del mismo cajón y el neto es el total de la venta. Es comodidad para quien atiende, sobre todo alguien nuevo, no un dato contable. Vale la pena decírselo así al cliente, porque suele ser justo lo que le preocupa. | Sin respuesta. No se ha construido. |
| H2 | La máquina de Mercado Pago, ¿le sirve que el cajero **marque en pantalla** si fue efectivo o máquina, o esperaba que el sistema hable solo con la máquina? | Que el sistema hable con la máquina necesita internet permanente y la API de Mercado Pago, y el sistema hoy funciona a propósito sin internet. Marcar a mano es una tecla. Conviene que lo oiga de nosotros antes de que se lo imagine de otra forma. | Sin respuesta directa. Se construyó **a mano**, con tres botones y F11 (D-034). |
| H10 | ¿A qué hora cierra la tienda? Si venden **pasada la medianoche**, esas ventas ¿son del día que termina o del que empieza? | En una botillería esto no es teórico. Hoy el informe corta a las 00:00, así que una venta de la 01:30 del sábado aparecería en el cierre del sábado y no en el del viernes. Se arregla ahora con una constante; después hay que rehacer las consultas. | **Sin respuesta.** Queda preparado: cambiar `config.HORA_CORTE_DIA` (D-035). |

---

## 4. Las que salen baratas ahora y caras después

| # | Pregunta | Por qué importa | Respuesta |
|---|---|---|---|
| H3 | Aparte de efectivo y la máquina, ¿cobra de **alguna otra forma**? ¿Transferencia, débito por separado, **fiado** a clientes conocidos? | Añadir un medio más adelante es barato, pero conviene saber la lista completa antes de escribir la pantalla de cobro. Ojo con el fiado: **no es un medio de pago, es una deuda**, y llevar cuentas de clientes es funcionalidad nueva, no una opción más en un botón. | En parte: quiere **débito y crédito separados** (D-034). Otros medios y fiado, sin respuesta. *2026-09-23* |
| H8 | ¿Cómo quiere que se llamen las dos cajas en los informes? ¿"Caja 1" y "Caja 2", "Mostrador" y "Bodega"? | Hay que escribirlo en los dos PC el día de la instalación. **Si los dos terminan con el mismo nombre, el informe mezcla las ventas de ambas sin avisar**, y no hay forma de detectarlo mirando los datos. | **Sin respuesta.** Hay que decidirlo antes de la visita. |
| H11 | ¿Alguna vez hay que **anular** una venta ya cobrada? ¿Con qué frecuencia y quién debería poder hacerlo? | Hoy el sistema no anula nada. Si es algo que pasa a diario, el cierre del día tiene que reflejarlo y hace falta decidir quién tiene permiso. También enlaza con la boleta electrónica, donde anular es bastante más caro. | |

---

## 5. Las que definen cómo se usa

| # | Pregunta | Por qué importa | Respuesta |
|---|---|---|---|
| H9 | ¿Cuántas personas atienden? ¿Entran y salen empleados con frecuencia? | Define si dar de baja a un usuario es rutina o excepción, y cuánto hay que cuidar esa pantalla. Si rota gente a menudo, crear y dar de baja usuarios tiene que ser muy fácil. | |
| H4 | ¿Quién debe poder **ver el cierre** del día: solo usted, o también quien está atendiendo? | Hoy está planificado como pantalla de administrador. Cambiarlo es trivial, pero hay que decidirlo, no suponerlo. | |
| H5 | El cierre del día, ¿le basta **verlo en pantalla** o necesita imprimirlo? | Si hay que imprimirlo, puede valer una impresora normal o un PDF, que es mucho más fácil que una térmica de tickets. Enlaza con el documento del SII pero **no depende de él**. | |
| H12 | Cuando un empleado olvide su clave, ¿prefiere poder **reiniciarla usted mismo** o que lo llamemos a nosotros? | Está planificado que el administrador genere una clave nueva desde la pantalla de usuarios. Es la respuesta esperada, pero conviene confirmarla. | Decidido por Santiago: el administrador genera un PIN nuevo desde Usuarios (D-032). |

---

## 6. Las que siguen pendientes desde antes y ahora sí importan

Estas ya estaban en `docs/PREGUNTAS-CLIENTE.md` sin responder. Con lo que pidió el 2026-09-18 dejan
de ser opcionales.

| # | Pregunta | Por qué importa | Respuesta |
|---|---|---|---|
| D1 | ¿Un empleado puede **cambiar precios**, o eso solo usted? | Define qué acciones exigen clave de administrador. Hoy el sistema ya distingue cajero y administrador, pero la línea exacta la pone él. | |
| D3 | ¿Le interesa saber **cuánto vendió cada empleado**? | Ya está medio contestada por lo que pidió, pero vale confirmarla mirándole a la cara: es lo que justifica toda la fase de usuarios. | |
| G13 | ¿Quién atiende la segunda caja: usted, un empleado, los dos? | Enlaza con D1 y D3. Si atiende alguien más, el cierre por caja cobra todo su sentido; si es su oficina, quizá no. | |

---

## 7. Lo que hay que decirle, no preguntarle

Tres frases para decir en voz alta en la misma reunión, para que no se las imagine:

- **El cierre que vamos a construir no cierra nada.** Es un informe que puede mirar las veces que
  quiera. No bloquea la caja ni cuadra el cajón — salvo que conteste que sí a H1, que es lo
  probable, y entonces hablamos de otra cosa y de otro presupuesto.
- **El sistema no emite boletas ni está conectado al SII**, y hoy funciona a propósito sin internet.
  Si eso es lo que quiere, está en el otro documento y es otro presupuesto.
- **Esta actualización obliga a una visita a la tienda**, con los dos computadores parados un rato.
  Hay que acordar cuándo: con la tienda cerrada o entre horas.

---

## 8. Qué pasa después de la reunión

- Si **H1 es "sí, cuento el efectivo"** (lo probable) → hay que rediseñar el cierre antes de construirlo. Parar y
  volver a planificar.
- Si **H1 es "no"** y las demás vienen contestadas → se puede empezar por la pantalla de usuarios,
  que no depende de ninguna respuesta y es lo primero del plan.
- **H8 (nombres de las cajas)** hay que decidirlo antes de la visita, porque se escribe en los dos
  PC ese mismo día.
- Todo lo que quede sin responder se anota como tal. Una pregunta sin respuesta es una respuesta:
  significa que lo que construyamos ahí es **supuesto nuestro**, y va a la sección 3.3 de
  `CLAUDE.md` como tal, no a la de requisitos.
