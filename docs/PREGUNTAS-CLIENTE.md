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

**Estado al 2026-09-13:** ya hubo una primera reunión, pero **las preguntas de los bloques A a F
siguen sin responder**. Esa conversación dio contexto —el sistema anterior, las dos cajas, los
datos que quiere rescatar— y no respuestas; la columna de la derecha sigue vacía a propósito. El
**bloque G**, al final, recoge lo que salió de ahí y es por donde conviene empezar la próxima vez.

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
| E4 | ¿Le interesa saber cuánto gana por producto, o solo cuánto vende? | Para el margen habría que registrar también el precio de compra. **El 2026-09-14 dijo que ese dato no le interesa (D-017 retirada), así que hoy la respuesta es "solo cuánto vende".** Sigue en la lista porque es de las cosas en las que un dueño cambia de opinión al ver los primeros informes, y entonces conviene que ya lo hayamos hablado. | 2026-09-14: no le interesa el precio de compra |

---

## Bloque F — Proyecto

| # | Pregunta | Por qué importa | Respuesta |
|---|---|---|---|
| F1 | ¿Para cuándo necesitaría tenerlo funcionando de verdad en la tienda? | Define el alcance de la primera versión real. | |
| F2 | ¿Qué presupuesto tiene en mente? | Evita diseñar algo que no puede pagar, o quedarse corto en algo que sí podría. | |
| F3 | Si tuviera que quedarse con una sola función, ¿cuál sería? | Obliga a priorizar y revela qué le duele de verdad. | |
| F4 | ¿Está usando algún sistema hoy? ¿Qué le molesta de él? | Si viene de otro sistema, sus quejas son el mejor mapa de requisitos que existe. | |

---

## Bloque G — Sistema anterior, migración y dos cajas *(añadido el 2026-09-13)*

Después de la primera reunión. El cliente contó tres cosas nuevas —que su sistema anterior se le
quedaba pegado, que guardaba cantidad, precio de compra, precio de venta y familia, y que necesita
dos PC— y mencionó LocalShop. Estas preguntas convierten esos comentarios en requisitos, o los
descartan.

**Actualización del 2026-09-14.** Dos ya se cerraron, y en sentido negativo: la **familia** y el
**precio de compra** no le interesan. G6 y G7 quedan tachadas y D-016 y D-017 retiradas. Conviene
saber que esta respuesta llegó de rebote y no en una reunión: si en la próxima conversación el tema
vuelve a salir, merece la pena confirmarlo mirándole a la cara antes de dar el catálogo por cerrado.

### Sobre el sistema anterior

| # | Pregunta | Por qué importa | Respuesta |
|---|---|---|---|
| G1 | ¿Cómo se llamaba el programa que usaba y desde cuándo lo tenía? ¿Quién se lo instaló? | Determina en qué formato están los datos y, por tanto, si se pueden abrir. Quien lo instaló puede tener el instalador y saber dónde guardaba. | |
| G2 | Cuando se quedaba pegado, ¿en qué momento exactamente? ¿Al abrirlo, al buscar un producto, al cobrar, o siempre? ¿Fue empeorando con el tiempo? | **La pregunta más útil de este bloque.** Si se pegaba al buscar, era la base de datos; si empeoró con los años, era el volumen; si se pegaba al cobrar y había otro PC, era la red. Cada respuesta señala una causa distinta, y sabiendo cuál es podemos demostrar que la nuestra no la tiene. | |
| G3 | ¿Cuántos productos tenía cargados, más o menos? | Define contra qué tamaño hay que medir el rendimiento. Hoy medimos contra 20.000 por precaución. | |
| G4 | ¿El programa hacía copias de seguridad? ¿Sabe dónde las dejaba? ¿Tiene alguna en un pendrive o se la pasó a alguien? | Si existe una copia, el rescate del PC sobra. Es lo primero que hay que preguntar. | |
| G5 | ¿Ese programa estaba conectado con otro computador de la tienda? | Si compartían la base por la red, ahí está la explicación del cuelgue, y además puede quedar una copia viva en el otro equipo. | |

### Sobre los datos que guardaba

| # | Pregunta | Por qué importa | Respuesta |
|---|---|---|---|
| ~~G6~~ | ~~Cuando dice "familia", ¿a qué se refiere?~~ | **Cerrada el 2026-09-14: el cliente dijo que la familia no le interesa.** D-016 retirada. | No le interesa |
| ~~G7~~ | ~~El precio de compra, ¿para qué lo usaba?~~ | **Cerrada el 2026-09-14: el cliente dijo que el precio de compra no le interesa.** D-017 retirada, y con ella todo informe de margen. | No le interesa |
| G7b | Al cargar el catálogo, ¿tiene los precios de compra a mano? | **Vale la pena preguntarlo aunque haya dicho que no le interesan.** No es por la funcionalidad: la columna se añade mañana en un minuto, pero el dato no. Si los precios están a la vista mientras cargan, anotarlos en el CSV cuesta una columna; si más adelante pregunta cuánto gana, la alternativa es teclear el costo de todo el catálogo otra vez. | |
| G8 | La cantidad que mostraba el sistema, ¿le cuadraba con lo que tenía en la bodega? | Si nunca le cuadró, el problema no era el sistema sino el proceso, y hay que hablar de toma de inventario antes que de software. | |
| G9 | ¿Recibe la mercadería con factura o guía de despacho? | Define cómo debe ser la pantalla de ingreso de stock: por documento o producto a producto. | |
| G10 | ¿Hace inventario físico? ¿Cada cuánto? | Va a hacer falta al menos una vez al arrancar, porque las cantidades que importemos estarán desfasadas. Saber si ya es una costumbre suya cambia cómo se lo planteamos. | |

### Sobre las dos cajas

| # | Pregunta | Por qué importa | Respuesta |
|---|---|---|---|
| G11 | Los dos computadores, ¿van a estar vendiendo al mismo tiempo, o uno es el mostrador y el otro la oficina? | **Es la pregunta más cara del documento.** Dos cajas simultáneas obligan a que un PC haga de servidor y a rehacer cómo se comunican las pantallas con los datos. "Caja más oficina" se resuelve con bastante menos. Estamos asumiendo lo primero. | |
| G12 | ¿Están en la misma sala? ¿Hay red por cable entre ellos, o wifi? | El cable es fiable; el wifi de una tienda, no siempre. Afecta directamente a que la caja se sienta rápida. | |
| G13 | ¿Quién atiende la segunda caja: usted, un empleado, los dos? | Enlaza con D1 y D3. Si atiende alguien más, hace falta la pantalla de usuarios y saber quién vendió qué. | |
| G14 | Si uno de los dos computadores se apaga o falla, ¿qué necesita que pase? ¿Que el otro siga vendiendo igual? | Define si basta con que la caja principal sea también el servidor, o si conviene un tercer equipo pequeño dedicado a guardar los datos. Es un coste, y es suyo. | |

### Sobre LocalShop y el modelo de negocio

| # | Pregunta | Por qué importa | Respuesta |
|---|---|---|---|
| G15 | De LocalShop, ¿qué fue lo que le gustó? ¿Lo llegó a usar o lo vio en una demostración? | LocalShop es un servicio en la nube que se paga todos los meses, trae un catálogo de productos precargado y emite boleta electrónica ante el SII. Son tres cosas muy distintas, y solo una de ellas es barata de copiar. | |
| G16 | ¿Necesita emitir boleta electrónica válida ante el SII? | Si la respuesta es sí, **es otro proyecto**: certificado digital, folios y responsabilidad tributaria. Hay que decirlo antes de presupuestar, no después. | |
| G17 | ¿Necesita ver las ventas desde el teléfono o desde su casa? | Hoy el sistema es local y no usa internet, a propósito. Salir a la nube cambia la arquitectura y añade un coste mensual permanente. | |
| G18 | ¿Prefiere pagar una vez por el sistema, o pagar una cuota mensual? | Lo nuestro se paga una vez y funciona sin internet; un servicio en la nube se paga siempre pero no hay que mantenerlo. Es una conversación honesta que conviene tener pronto. | |

---

## Nota sobre lo que NO se le debe prometer

Actualizado tras la reunión del 2026-09-13. Lo que sigue sin hacer, dicho en voz alta:

- El sistema **no emite boletas ni facturas** y no está conectado al SII. Si esto es lo que le
  gustaba de LocalShop, hay que decírselo en la misma frase en que se menciona.
- **No registra medios de pago** ni calcula vuelto.
- **Todavía no funciona en dos cajas.** Está planificado (fase 13) y decidido cómo hacerlo (D-015),
  pero hoy no existe. Es la promesa más fácil de dar por error en una conversación.
- **No maneja productos por peso.**
- **No tiene familias ni precio de compra, y ya no se van a hacer.** El cliente los retiró el
  2026-09-14 (D-016 y D-017). Si los vuelve a mencionar, es un cambio de alcance y hay que
  tratarlo como tal, no darlo por hecho.
- **Los datos de su sistema anterior no están rescatados** hasta que estén rescatados. No prometer
  la migración antes de haber abierto el archivo: hasta el paso 4 de `RESCATE-DATOS.md` no se sabe
  siquiera en qué formato están.
- Los productos que se ven son un **catálogo de ejemplo**, no los suyos.

Conviene decirlo abiertamente. Un prototipo honesto genera más confianza que uno que promete de más
y decepciona después.
