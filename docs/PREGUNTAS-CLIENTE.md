# Preguntas para el cliente

**Para qué sirve este documento:** el cliente solo dijo *"quiero un sistema de tienda que lea
el código de barras de un producto y despliegue su precio"*. Todo lo demás lo decidimos
nosotros por necesidad. Estas son las preguntas cuya respuesta puede cambiar el producto, el
esfuerzo o el precio del desarrollo.

**Cómo usarlo:** llévalo a la demostración. Están redactadas en lenguaje de negocio, para
preguntarlas en voz alta sin tecnicismos. Anota las respuestas en la columna de la derecha.

**Consejo:** no las preguntes todas de corrido. Muestra primero el prototipo, deja que
reaccione, y ve intercalando las preguntas del **Bloque A** según lo que él mismo comente.
Las de los bloques C y D solo si la conversación avanza hacia un desarrollo real.

---

## Bloque A — Críticas (cambian el producto)

Si estas se responden mal, construimos el sistema equivocado.

| # | Pregunta | Por qué importa | Respuesta |
|---|---|---|---|
| A1 | ¿Quién va a usar el sistema en el día a día: usted, un empleado en la caja, o el cliente que consulta el precio solo? | Define toda la interfaz. Un cliente consultando precios necesita letras enormes y cero botones; un cajero necesita rapidez y teclado. | |
| A2 | ¿Lo que necesita es solo consultar precios, o también quiere registrar las ventas? | Es la diferencia entre un visor de precios y un punto de venta completo. Cambia el esfuerzo por un factor de tres. | |
| A3 | ¿Quiere llevar control de cuánto stock le queda de cada producto? | El inventario es la funcionalidad que más se pide después del precio, y la que más trabajo añade. | |
| A4 | ¿Qué vende exactamente su tienda? | Un almacén, una tienda de ropa y una ferretería necesitan modelos de producto distintos. La ropa, por ejemplo, obliga a manejar tallas y colores. | |
| A5 | ¿Vende algo por peso o a granel, o todo va por unidad? | El granel obliga a manejar precio por kilo, cantidades con decimales y las etiquetas especiales de la balanza. Es bastante más trabajo. | |
| A6 | ¿Cuántos productos distintos maneja, aproximadamente? | Doscientos productos y veinte mil no se administran igual: cambia la forma de cargarlos y de buscarlos. | |

---

## Bloque B — Operación (cambian el uso diario)

| # | Pregunta | Por qué importa | Respuesta |
|---|---|---|---|
| B1 | ¿Tiene ya una pistola lectora de códigos de barras? ¿De qué tipo? | Damos por supuesto que tiene una USB estándar. Si no la tiene, hay que presupuestarla o usar la cámara de un teléfono. | |
| B2 | ¿Todos sus productos traen código de barras de fábrica, o hay algunos sin código? | Si vende cosas sin código (productos propios, sueltos), hay que imprimir etiquetas o buscar por nombre. | |
| B3 | ¿Dónde tiene hoy la lista de sus productos y sus precios? ¿En un cuaderno, en Excel, en otro sistema, o en su cabeza? | Determina si podemos importar los datos en minutos o si hay que cargarlos a mano uno por uno. Es de las cosas que más tiempo consume. | |
| B4 | ¿Quién cambia los precios y con qué frecuencia? | Define si hace falta una pantalla de administración cómoda o basta con algo básico. | |
| B5 | ¿Tiene ofertas, promociones o descuentos? ¿Cómo funcionan? (2x1, descuento por cantidad, precio especial a ciertos clientes) | Las promociones son de lo que más complica un sistema de precios. Es mejor saberlo antes que después. | |
| B6 | Cuando escanea algo que el sistema no reconoce, ¿qué preferiría que pasara? | Es el error más frecuente en la vida real de una caja. Hoy lo mostramos con un aviso claro y lo dejamos anotado. | |
| B7 | ¿Cuántas cajas o puestos habrá? ¿Uno solo o varios? | Un solo PC es simple y barato. Varias cajas trabajando a la vez obliga a un servidor y cambia la arquitectura entera. | |
| B8 | ¿Necesita entregar algún comprobante o boleta al cliente? | Un ticket impreso es fácil. Una boleta electrónica válida ante el SII es un proyecto en sí mismo, con certificado digital y responsabilidad legal. | |

---

## Bloque C — Entorno y equipos

| # | Pregunta | Por qué importa | Respuesta |
|---|---|---|---|
| C1 | ¿Qué computador usará? ¿Qué versión de Windows tiene? | El prototipo está pensado para Windows 10 u 11. | |
| C2 | ¿Tiene internet estable en la tienda? | Si no lo tiene, el sistema debe funcionar sin conexión. Hoy funciona completamente sin internet. | |
| C3 | ¿Prefiere abrir el programa con un acceso directo, o que se abra solo al encender el computador? | El arranque automático es cómodo pero deja el equipo dedicado al sistema. **Nuestra recomendación es el acceso directo**, y activar el arranque automático solo si lo pide. | |
| C4 | ¿Tiene impresora? ¿De tickets o normal? | Determina si tiene sentido implementar el comprobante impreso. | |
| C5 | ¿Le preocupa perder la información si el computador falla? ¿Quiere copias de seguridad automáticas en un pendrive o en la nube? | Hoy hacemos copias automáticas en el mismo equipo. Protegerse ante el robo o la avería del PC requiere algo más. | |

---

## Bloque D — Usuarios, seguridad y control

| # | Pregunta | Por qué importa | Respuesta |
|---|---|---|---|
| D1 | ¿Trabajará alguien más aparte de usted? | Si hay empleados, conviene distinguir quién hizo cada venta. | |
| D2 | ¿Quiere que un empleado pueda cambiar precios, o solo usted? | Es la razón por la que el prototipo incluye un PIN de administrador. | |
| D3 | ¿Le interesa saber cuánto vendió cada empleado, o en qué turno? | Añade control, pero también complejidad. Solo si le aporta valor real. | |

---

## Bloque E — Información del negocio

| # | Pregunta | Por qué importa | Respuesta |
|---|---|---|---|
| E1 | ¿Qué le gustaría saber de su negocio que hoy no sabe? | La pregunta más valiosa de todas. Suele revelar el problema real, que casi nunca es el que el cliente pidió al principio. | |
| E2 | ¿Necesita ver cuánto vendió en el día, en la semana o en el mes? | Define la profundidad de los reportes. El prototipo hoy solo muestra el día. | |
| E3 | ¿Quiere saber qué productos se venden más y cuáles no se mueven? | Es de las funciones que más valoran los dueños de tienda, y es relativamente barata de añadir. | |
| E4 | ¿Le interesa saber cuánto gana por producto, o solo cuánto vende? | Para el margen habría que registrar también el precio de compra, que es un dato que hoy no pedimos. | |

---

## Bloque F — Proyecto

| # | Pregunta | Por qué importa | Respuesta |
|---|---|---|---|
| F1 | ¿Para cuándo necesitaría tenerlo funcionando de verdad en la tienda? | Define el alcance de la primera versión real. | |
| F2 | ¿Qué presupuesto tiene en mente? | Evita diseñar algo que no puede pagar, o quedarse corto en algo que sí podría. | |
| F3 | Si tuviera que quedarse con una sola función, ¿cuál sería? | Obliga a priorizar y revela qué le duele de verdad. | |
| F4 | ¿Está usando algún sistema hoy? ¿Qué le molesta de él? | Si viene de otro sistema, sus quejas son el mejor mapa de requisitos que existe. | |

---

## Nota sobre lo que NO se le debe prometer en la demo

- El prototipo **no emite boletas ni facturas** y no está conectado al SII.
- **No registra medios de pago** ni calcula vuelto.
- **No funciona en varias cajas a la vez.**
- **No maneja productos por peso.**
- Los datos que se ven son un **catálogo de ejemplo**, no los suyos.

Conviene decirlo abiertamente. Un prototipo honesto genera más confianza que uno que promete
de más y decepciona después.
