# Decisiones técnicas

Registro de las decisiones que son caras de revertir, con su justificación y sus
consecuencias. Si una decisión cambia, se añade una entrada nueva en lugar de reescribir la
anterior: el historial de por qué se pensó algo vale tanto como la conclusión.

Formato: **Contexto → Decisión → Consecuencias**.

---

## D-001 — Aplicación de escritorio, no web

**Fecha:** 2026-09-09 · **Estado:** aceptada · **Decide:** Santiago

**Contexto.** El cliente no especificó plataforma. Una aplicación web habría sido más rápida
de construir y más fácil de mostrar, pero exige abrir un navegador y escribir una dirección.

**Decisión.** Aplicación de escritorio para Windows. El usuario hace doble clic en un acceso
directo y el programa arranca. Sin navegador y sin `localhost`.

**Consecuencias.** Se descartan los stacks web. Aparece la necesidad de empaquetar un
ejecutable y de distribuirlo. A cambio, la experiencia es la de un programa de verdad, que es
justo lo que un dueño de tienda espera ver. Queda pendiente decidir con el cliente si además
debe arrancar solo al encender el computador.

---

## D-002 — Python 3.11 + PySide6 (Qt 6)

**Fecha:** 2026-09-09 · **Estado:** aceptada · **Decide:** Santiago

**Contexto.** Hacía falta una tecnología de escritorio Windows que se viera profesional, que
Santiago pudiera mantener y que permitiera construir rápido. Se evaluaron CustomTkinter
(demasiado pobre en tablas y manejo de foco, y en un POS la tabla del carrito y el teclado
*son* el producto), C# con WPF (excelente, pero fuera de la zona cómoda) y Electron o Tauri
(HTML por dentro, contradice D-001).

**Decisión.** Python 3.11 con PySide6.

**Consecuencias.** Interfaz nativa con buen manejo de teclado y tablas. El ejecutable pesará
entre 60 y 90 MB. Algunos antivirus marcan falsos positivos en ejecutables de PyInstaller;
hay que probarlo antes de la demo.

**Nota de licencia — importante si esto se vende.** PySide6 es LGPL, lo que permite
distribuirlo dentro de software propietario. PyQt6 es GPL y exigiría comprar una licencia
comercial. Es un motivo adicional, y no menor, para PySide6.

---

## D-003 — SQLite local, sin ORM

**Fecha:** 2026-09-09 · **Estado:** aceptada · **Decide:** Santiago

**Contexto.** Un solo PC, sin red, catálogo de cientos de productos, prototipo que debe
arrancar sin instalar nada.

**Decisión.** SQLite mediante el módulo `sqlite3` de la biblioteca estándar, en modo WAL y con
`foreign_keys=ON`. Acceso a datos tras una capa de repositorios, con SQL explícito y sin ORM.

**Consecuencias.** Cero dependencias de base de datos, cero instalación, un único archivo que
se puede copiar como respaldo. El SQL explícito mantiene el control y hace el ejecutable más
liviano. **Límite conocido:** SQLite no sirve para varias cajas escribiendo a la vez sobre la
red. Si el cliente pide multipuesto, hay que migrar a un servidor; por eso el acceso a datos
está aislado en `repositories/`, para que ese cambio no toque la lógica de negocio.

**Actualización del 2026-09-13.** El cliente pidió que el sistema funcione en dos PC, así que ese
límite conocido dejó de ser hipotético. **Lo relativo al número de cajas queda superado por
`D-015`**, que resuelve el multipuesto sin abandonar SQLite: un único proceso servidor es dueño del
archivo y las cajas le hablan a él. El resto de esta decisión —SQLite, sin ORM, SQL explícito tras
la capa de repositorios— sigue vigente, y el aislamiento en `repositories/` que se previó aquí es
justamente lo que abarata aquel cambio.

---

## D-004 — El dinero se guarda en enteros

**Fecha:** 2026-09-09 · **Estado:** aceptada

**Contexto.** El peso chileno no usa decimales, y la coma flotante acumula errores de
redondeo que producen totales como 999,99999.

**Decisión.** Todos los importes se almacenan y se calculan como enteros de CLP. Nunca `float`.
El formato para mostrar vive en `utils/money.py`.

**Consecuencias.** Los totales siempre cuadran. Si algún día se necesita una moneda con
decimales, se guardaría en la unidad menor (centavos) manteniendo el entero.

---

## D-005 — Las líneas de venta guardan copia del precio y del nombre

**Fecha:** 2026-09-09 · **Estado:** aceptada

**Contexto.** Si una venta solo guardara una referencia al producto, cambiar un precio hoy
reescribiría el valor de todas las ventas del pasado.

**Decisión.** Cada línea de venta almacena una copia del código, del nombre y del precio
unitario vigentes en el momento de la venta, además de la referencia al producto.

**Consecuencias.** El historial de ventas es inmutable y auditable. Se duplican unos pocos
datos, lo cual es intencionado: en registros históricos, la desnormalización es la solución
correcta, no un descuido.

---

## D-006 — Alcance del cierre de venta: sin pagos ni comprobantes

**Fecha:** 2026-09-09 · **Estado:** aceptada · **Decide:** Santiago

**Contexto.** El cliente solo pidió consultar precios. Registrar medios de pago o emitir
boletas electrónicas abre obligaciones legales y técnicas enormes (certificado digital,
integración con el SII, responsabilidad tributaria).

**Decisión.** La venta se cierra con su total y queda registrada, descontando stock. Sin
medios de pago, sin cálculo de vuelto, sin ticket impreso y sin boleta electrónica.

**Consecuencias.** El prototipo demuestra el flujo completo sin convertirse en un sistema
sujeto a normativa. En la demo debe decirse abiertamente que no emite boletas.

---

## D-007 — Acceso por PIN con roles de cajero y administrador

**Fecha:** 2026-09-09 · **Estado:** aceptada · **Decide:** Santiago

**Contexto.** Un cajero teclea decenas de veces por hora; una contraseña larga en cada turno
es fricción pura. Pero dejar los precios editables por cualquiera es un riesgo real de negocio.

**Decisión.** PIN corto para operar la caja. Las acciones peligrosas (editar precios, editar o
eliminar productos, ver reportes) exigen rol de administrador. El PIN se almacena con
`hashlib.scrypt` y salt, de la biblioteca estándar. Nunca en texto plano.

**Consecuencias.** Protege lo que importa sin estorbar la operación. No es seguridad de grado
bancario, y no pretende serlo: un PIN de cuatro dígitos protege frente a un empleado
distraído, no frente a un atacante con acceso físico al disco.

---

## D-008 — Sin trazabilidad de movimientos de inventario (deuda técnica consciente)

**Fecha:** 2026-09-09 · **Estado:** aceptada

**Contexto.** Llevar un registro de cada movimiento de stock (entradas, salidas, ajustes,
mermas) es lo correcto en un sistema de inventario serio, pero multiplica el trabajo.

**Decisión.** En el prototipo, el stock es un simple contador en la tabla de productos que se
descuenta al vender.

**Consecuencias.** **Esto es deuda técnica, y está registrada como tal.** Si el cliente quiere
saber por qué su stock no cuadra, hará falta una tabla de movimientos. El cambio es aditivo y
no rompe lo construido, pero implica trabajo. Ver la pregunta A3 en `PREGUNTAS-CLIENTE.md`.

**Actualización del 2026-09-13. Deuda saldada: ver `D-018`.** El cliente confirmó que llevaba
cantidades en su sistema anterior, y con dos cajas descontando del mismo stock la pregunta "¿por
qué no me cuadra?" pasa de molestia a llamada de soporte. Se añade la tabla de movimientos que
aquí se anticipó. Esta entrada se conserva porque la decisión original —no construirla mientras el
inventario no estuviera confirmado— era correcta con la información que había entonces.

---

## D-009 — Una venta sin stock suficiente se rechaza

**Fecha:** 2026-09-09 · **Estado:** aceptada

**Contexto.** Al cerrar una venta, el sistema comprueba el stock contra la base de datos. Si
no alcanza, hay dos posturas defendibles: bloquear la venta, o permitirla y dejar el stock en
negativo. Muchos puntos de venta reales hacen lo segundo, porque el inventario casi nunca está
perfectamente al día y bloquear una venta por un dato desactualizado enfada al cliente que
está esperando en la caja.

**Decisión.** Se bloquea, con un mensaje que dice el producto, cuánto queda y cuánto se pide.
El comportamiento está en la constante `PERMITIR_STOCK_NEGATIVO` de `config.py`.

**Consecuencias.** El prototipo demuestra control de inventario de verdad, que es lo que se
quiere enseñar. El catálogo de ejemplo tiene stock generoso, así que la demostración no se
topa con el bloqueo. **Es una decisión de negocio disfrazada de detalle técnico:** si el
cliente dice que prefiere vender igual, se cambia una constante. Está en la pregunta A3 de
`PREGUNTAS-CLIENTE.md`.

---

## D-010 — El ejecutable se distribuye en carpeta, no como archivo único

**Fecha:** 2026-09-09 · **Estado:** aceptada

**Contexto.** PyInstaller puede generar un solo `.exe` o una carpeta con el ejecutable y sus
dependencias. El archivo único es mucho más cómodo de enviar.

**Decisión.** Se distribuye la carpeta, con un acceso directo en el escritorio que apunta al
ejecutable. La opción `--unico` de `tools/construir.py` sigue disponible.

**Consecuencias.** El archivo único se descomprime en una carpeta temporal en cada arranque y
añade entre dos y tres segundos, lo que incumpliría el criterio de aceptación de abrir en
menos de tres segundos. Medido con la carpeta: **0,93 s**. A cambio, instalar significa copiar
una carpeta en lugar de un archivo. Para enviar el prototipo por correo, el archivo único
sigue siendo la mejor opción.

---

## D-011 — El programa incluye su propia comprobación de arranque

**Fecha:** 2026-09-09 · **Estado:** aceptada

**Contexto.** Antes de una demostración hace falta saber si el ejecutable funciona en el
equipo del cliente. Hacer una venta a mano para comprobarlo es lento y deja datos de prueba
en la base.

**Decisión.** `TiendaPOS.exe --verificar` arranca el sistema entero sin mostrar nada, mide el
tiempo y escribe un informe en la carpeta de datos, devolviendo 0 si todo fue bien.

**Consecuencias.** Se puede validar la instalación en segundos, y ante un problema el informe
dice qué falló en lugar de dejar una ventana que no aparece. La misma función se ejecuta como
prueba automatizada, así que no es código muerto que solo se usa a mano.

---

## D-012 — El descuento puede aplicarse a un producto o a la venta entera

**Fecha:** 2026-09-11 · **Estado:** aceptada

**Contexto.** Hasta ahora el descuento era siempre de la venta completa. En una tienda pequeña
eso no alcanza: el pan del día anterior, el envase abollado o el producto próximo a vencer se
rebajan uno a uno. Aplicarlo al total daría el importe correcto hoy, pero dejaría una venta
imposible de explicar mañana, cuando nadie recuerde de qué producto era la rebaja.

**Decisión.** Cada línea del carrito puede llevar su propio descuento, por monto o por
porcentaje, además del descuento de la venta. Ambos conviven:

- `venta.subtotal_clp` sigue siendo el importe **bruto**, sin descuentos.
- El descuento de la venta se calcula sobre lo que queda **después** de los de línea. Si no,
  dos descuentos del 100% dejarían un total negativo.
- `venta.descuento_clp` es la suma de ambos, así que el significado del campo no cambia para
  nada de lo ya construido (informes incluidos).

**Consecuencias.** Obliga a un cambio en el modelo de datos: la tabla `venta_linea` gana una
columna `descuento_clp` (migración de esquema 2, aditiva, con valor 0 para las ventas ya
registradas, que es exactamente lo que ocurrió en ellas). El subtotal de la línea se sigue
guardando en bruto, de modo que el detalle de una venta antigua explica precio, cantidad y
rebaja por separado. **Este cambio de modelo de datos se hizo para atender una petición
explícita, y se anota aquí en lugar de pasar en silencio.**

---

## D-013 — Preferencias del equipo en un archivo JSON, no en la base de datos

**Fecha:** 2026-09-11 · **Estado:** aceptada

**Contexto.** El tema, el sonido y la confirmación de cobro son ajustes de la instalación, no
datos del negocio. Guardarlos en la base de datos habría obligado a una tabla, una migración y
un repositorio, y a depender de que la base abra para saber de qué color pintar la ventana de
acceso, que aparece antes.

**Decisión.** Un `preferencias.json` junto a la base de datos, leído por
`services/preferencias.py`. Un archivo ausente, ilegible o escrito por otra versión nunca
impide arrancar: se vuelve a los valores de fábrica y se registra el aviso.

**Consecuencias.** Se leen antes de crear la primera ventana, de modo que el tema ya está
puesto cuando se pide el PIN. No se sincronizan entre equipos, cosa que hoy no hace falta
porque el sistema es monopuesto. Si algún día hay varias cajas, estos ajustes deberían seguir
siendo locales: el tema lo elige quien mira esa pantalla.

---

## D-014 — Las acciones de cada línea son celdas, no botones

**Fecha:** 2026-09-11 · **Estado:** aceptada

**Contexto.** Copiar el código y subir o bajar la cantidad se pedían como botones dentro de
cada fila del carrito. La primera versión los puso como widgets incrustados en la tabla
(`setCellWidget`).

**Decisión.** Se usan celdas normales con un símbolo (⧉, −, +) y un `cellClicked` que despacha
la acción.

**Consecuencias.** Qt no destruye los widgets incrustados cuando la tabla pierde filas: al
cobrar una venta y empezar la siguiente quedaban botones flotando sobre filas que ya no
existían, y un clic en ellos actuaba sobre un carrito inexistente. Se comprobó en las capturas
generadas por `tools/capturas.py`. Con celdas no hay widgets que se queden atrás, la tabla se
redibuja entera en cada escaneo sin coste y el teclado sigue siendo la vía principal: las
flechas hacen lo mismo que los símbolos.

---

## D-015 — Multipuesto: un PC hace de servidor, no una carpeta compartida

**Fecha:** 2026-09-13 · **Estado:** aceptada · **Decide:** Santiago

**Contexto.** El cliente dijo que el sistema debe funcionar en dos PC. Eso desmonta el supuesto de
"una sola caja" sobre el que se construyó `D-003`. Además contó que su sistema anterior **se le
quedaba pegado**, lo que es un dato técnico disfrazado de queja: la forma barata y habitual de
hacer "dos PC" es dejar la base de datos en una carpeta compartida de la red, y ese es
precisamente el arreglo que produce cuelgues.

Se evaluaron tres caminos.

**A — SQLite sobre una carpeta compartida por red.** Coste casi cero. Pero SQLite **no soporta el
modo WAL sobre red** (WAL necesita memoria compartida, que un recurso SMB no ofrece), de modo que
habría que volver al diario clásico; y el bloqueo de archivos por SMB es notoriamente poco fiable,
que es la causa clásica tanto de los bloqueos como de la corrupción de la base. Es, con toda
probabilidad, lo que hacía el sistema del que el cliente quiere escapar. **Rechazada.**

**B — Un proceso servidor, dueño único del archivo.** Un único proceso abre `tienda.db`. Las dos
interfaces —la del propio PC servidor y la de la segunda caja— le piden a él por la red local.
Estimado en 4–6 días.

**C — PostgreSQL o MariaDB en el PC principal.** Concurrencia resuelta por un motor maduro, sin
escribir servidor. Pero el instalador pasa de unos 40 MB a unos 300 y tiene que encadenar la
instalación de un servicio con credenciales y puerto; hay que reescribir el SQL de los repositorios
al dialecto nuevo; y el respaldo deja de ser "copiar un archivo" para pasar a ser `pg_dump`. Es
decir, empeora justo lo otro que el cliente pidió mejorar, que es la instalación. Estimado en
6–9 días.

**Decisión.** Opción **B**. Un proceso servidor que es el dueño exclusivo de la base de datos. La
caja principal hace también de servidor, sin hardware adicional.

Condiciones de diseño, que son las que evitan repetir el defecto del sistema anterior:

1. El servidor es un proceso propio, no un hilo dentro de la interfaz.
2. **La interfaz Qt nunca se bloquea esperando la red.** Toda llamada lleva un tiempo límite corto
   y un estado visible de "reconectando". Una ventana congelada es, literalmente, la queja del
   cliente.
3. La caja secundaria comprueba la **versión del esquema** al conectar y se niega a trabajar contra
   un servidor de versión distinta. Con dos PC, las versiones se desincronizan solas.
4. **Sin modo desconectado con sincronización posterior.** Dos cajas vendiendo el mismo stock sin
   verse generan conflictos que no se resuelven bien. Si el servidor no responde, la caja
   secundaria no vende y lo dice claramente; la caja principal sigue funcionando siempre.
5. Los respaldos se ejecutan solo en el servidor. Las preferencias siguen siendo locales (`D-013`).

**Consecuencias.** Desaparece el problema de concurrencia de SQLite, porque **solo hay un proceso
escritor**: los mecanismos de bloqueo entre procesos, que son los que fallan sobre red, dejan de
usarse. Se conserva el respaldo como "copiar un archivo", que era la ventaja principal de `D-003`,
y no se instala ningún motor de base de datos.

El corte va **a nivel de servicio, no de repositorio**, y el código ya está partido por ahí: todas
las funciones de `services/` tienen la forma `(conexion, …) -> objeto de dominio` y ninguna importa
Qt, de modo que cada operación sigue siendo una sola transacción del lado del servidor. El folio
único y la revalidación de stock se resuelven solos por ser transaccionales; el docstring de
`cerrar_venta` ya anticipaba este escenario cuando decía que la comprobación de stock contra la
base "el día que haya dos cajas será imprescindible". El `Carrito` es puro y sigue viviendo en
memoria en la caja; se serializa entero al cobrar.

Lo que se pierde: si el PC servidor se apaga, la segunda caja no vende. Queda como decisión de
coste del cliente si conviene un mini-PC dedicado como servidor; con esta arquitectura es un cambio
de configuración, no de código.

**Supera a `D-003`** en lo relativo al número de cajas. El resto de `D-003` —SQLite, sin ORM, SQL
explícito tras repositorios— sigue vigente.

---

## D-016 — La familia es una tabla, no un texto en el producto

**Fecha:** 2026-09-13 · **Estado:** **retirada el 2026-09-14** · **Decide:** Santiago

> **Retirada el 2026-09-14.** El cliente comunicó que la familia no le interesa, pese a haber dicho
> el 2026-09-13 que su sistema anterior la guardaba. No se implementa: no hay tabla `familia` ni
> `producto.familia_id`, y se retira el informe de ventas por familia. La pregunta G6 deja de tener
> objeto.
>
> El razonamiento de abajo se conserva sin tocar, porque si el cliente cambia de opinión la
> decisión de diseño ya está tomada y sigue siendo válida: el día que se reactive, es tabla y no
> texto libre, por los motivos que están escritos ahí.

**Contexto.** El cliente guardaba una "familia" por producto en su sistema anterior. La forma
rápida de añadirlo sería una columna de texto libre en `producto`.

**Decisión.** Tabla `familia` con nombre único, y `producto.familia_id` que la referencia y admite
nulo.

**Consecuencias.** El texto libre degenera siempre en "Licor", "licores", "LICOR " y "Licores " como
cuatro familias distintas, y entonces el informe por familia deja de servir, que es justo para lo
que existe el campo. Con una tabla, renombrar una familia es una operación y no toca ni un producto.
El nulo se admite a propósito: al importar el catálogo del cliente habrá productos sin clasificar, y
eso no puede impedir la importación. **Pendiente de confirmar con el cliente qué entiende él por
"familia"**: lo interpretamos como categoría de producto, pero podría ser marca, proveedor o grupo
de impuesto. Ver el bloque G de `PREGUNTAS-CLIENTE.md`.

---

## D-017 — El costo se guarda en el producto y se copia en la línea de venta

**Fecha:** 2026-09-13 · **Estado:** **retirada el 2026-09-14** · **Decide:** Santiago

> **Retirada el 2026-09-14.** El cliente comunicó que el precio de compra no le interesa, pese a
> haber dicho el 2026-09-13 que su sistema anterior lo guardaba. No se implementa: no hay
> `producto.costo_clp` ni `venta_linea.costo_unit_clp`, y **con ello desaparece cualquier informe
> de margen o de ganancia**, porque sin el costo no se pueden calcular. La pregunta G7 deja de
> tener objeto.
>
> **Riesgo asumido, y conviene que quede escrito.** El costo es el único dato que permite responder
> "¿cuánto gané?". Añadir la columna más adelante es trivial; lo caro es el dato, porque obligaría a
> teclear el precio de compra de todo el catálogo producto por producto. Si al cargar el catálogo
> resulta que los precios de compra están a mano, captúrense en el CSV aunque el programa todavía
> no los use: cuesta una columna y evita esa recarga.
>
> El razonamiento de abajo se conserva sin tocar: si el costo vuelve, vuelve con la copia en la
> línea de venta, por los motivos que están escritos ahí.

**Contexto.** El sistema anterior del cliente guardaba precio de compra además de precio de venta.
Hasta ahora solo teníamos `precio_clp`, y la pregunta E4 anticipaba que el margen exigiría este
dato.

**Decisión.** `producto.costo_clp` con el último costo conocido, y `venta_linea.costo_unit_clp` con
el costo vigente en el momento de vender.

**Consecuencias.** Es el mismo razonamiento de `D-005` aplicado al costo: si mañana el proveedor
sube el precio, el margen de las ventas de ayer no debe reescribirse. Sin esa copia, cualquier
informe de ganancia pasada se recalcularía con costos de hoy y daría números falsos, que además
parecerían plausibles, que es lo peor que puede hacer un informe. Se guarda el último costo y no un
promedio ponderado: el promedio es más correcto contablemente, pero exige un histórico de compras
que hoy no existe, y para decidir un precio de venta el último costo es el dato útil.

---

## D-018 — Movimientos de inventario

**Fecha:** 2026-09-13 · **Estado:** aceptada · **Decide:** Santiago

> **Nota del 2026-09-14.** Esta decisión **no cae** con la retirada de `D-016` y `D-017`. Estaba en
> la misma fase del plan solo porque también toca el modelo de datos, no porque compartiera motivo:
> no es un atributo del producto, no lo pidió el cliente y no depende ni de la familia ni del costo.
> Lo que el cliente sí mantiene es la cantidad, y con dos cajas descontando del mismo stock la
> trazabilidad gana importancia en vez de perderla.

**Contexto.** `D-008` aceptó deliberadamente no llevar trazabilidad de stock, dejando el stock como
un simple contador, y lo registró como deuda técnica a saldar si el cliente daba importancia al
inventario. Le da importancia: guardaba cantidades en su sistema anterior, y ahora además habrá dos
cajas descontando del mismo stock.

**Decisión.** Tabla `movimiento_inventario` con producto, fecha y hora, tipo (`venta`, `ingreso`,
`ajuste`, `anulacion`, `carga_inicial`), cantidad con signo, stock resultante, usuario y venta de
origen cuando la haya. El stock del producto solo cambia emitiendo un movimiento, dentro de la
misma transacción.

**Consecuencias.** Se puede responder a "¿por qué no me cuadra el stock?", que con una sola caja era
una molestia y con dos pasa a ser una llamada de soporte recurrente. Guardar el stock resultante
además de la cantidad es redundante a propósito: permite detectar un descuadre comparando el
histórico con el contador, en lugar de confiar en que la suma cuadre. La tabla crece con las
ventas, lo que es irrelevante para el tamaño de este negocio.

**Salda la deuda de `D-008`.**

---

## D-019 — La importación es solo CSV, con la biblioteca estándar

**Fecha:** 2026-09-13 · **Estado:** aceptada · **Decide:** Santiago

**Contexto.** Hay que cargar el catálogo rescatado del sistema anterior, y hoy no existe ninguna
vía de importación. El formato natural para un dueño de tienda es Excel.

**Decisión.** Se importa y se exporta CSV, con el módulo `csv` de la biblioteca estándar. No se
lee `.xlsx`.

**Consecuencias.** Cero dependencias nuevas y cero peso añadido al ejecutable; leer `.xlsx`
obligaría a `openpyxl`. Excel guarda como CSV en dos clics, así que el coste para el cliente es
nulo, y la instrucción cabe en una línea del manual. A cambio hay que tratar a mano lo que
`openpyxl` daría resuelto: la codificación Windows-1252 frente a UTF-8 —los sistemas antiguos
rompen las tildes y la eñe—, el separador `;` que usa el Excel en español, y los miles con punto
con el decimal en coma.

La importación son **dos pasos separados**: analizar, que devuelve fila por fila si es alta,
actualización o error sin tocar la base; y aplicar, que escribe todo en una sola transacción. Un
importador que escribe mientras lee deja el catálogo a medias cuando falla en la fila 800, y ese es
el momento en que el cliente pierde la confianza en el sistema.

Se exporta además de importar, aunque nadie lo haya pedido: le da al cliente la propiedad de sus
propios datos, y es el argumento directo frente al encierro de un servicio por suscripción.

---

## D-020 — Instalador con Inno Setup, con modo servidor y modo caja

**Fecha:** 2026-09-13 · **Estado:** aceptada · **Decide:** Santiago

**Contexto.** El cliente pidió mejorar la instalación, que hoy consiste en copiar una carpeta a
mano. La viabilidad ya estaba valorada en `TECNICA.md` §11, con Inno Setup como opción sensata para
un local de uno o dos PC. Con `D-015` aparece un requisito nuevo: hay dos instalaciones distintas.

**Decisión.** Un `.iss` de Inno Setup que pregunte el modo de instalación —servidor y caja, o caja
secundaria—, pida la dirección del servidor en el segundo caso y cree la regla de cortafuegos en el
primero.

**Consecuencias.** El punto que suele arruinar un instalador ya estaba resuelto: el programa nunca
escribe en su propia carpeta, así que puede vivir en `Archivos de Programa`. Al desinstalar **no se
borran los datos** de `%LOCALAPPDATA%\TiendaPOS\`, y se avisa dónde quedaron. La configuración del
modo es lo único que el instalador escribe fuera del ejecutable, y debe poder cambiarse después sin
reinstalar, porque el día que el cliente cambie de PC servidor no va a querer reinstalar las dos
cajas.

---

## D-021 — Firma de código: pendiente

**Fecha:** 2026-09-13 · **Estado:** **pendiente de Santiago**

**Contexto.** Sin un certificado de firma, Windows SmartScreen muestra "editor desconocido" la
primera vez que se ejecuta el instalador. El cliente puede pasar el aviso, pero es lo primero que
ve en la entrega.

**Opciones.** Firmar, con coste anual de certificado; o no firmar y explicar el aviso en el manual
de instalación.

**Consecuencias.** No bloquea nada y se puede decidir el día de la entrega, pero conviene decidirlo
antes de presupuestar. Se anota aquí para que no aparezca como sorpresa.

---

## D-022 — El rendimiento se mide, no se supone

**Fecha:** 2026-09-13 · **Estado:** aceptada · **Decide:** Santiago

**Contexto.** El cliente cambió de sistema porque **se le quedaba pegado**. Esa es la queja concreta
que trae, y es la única que se puede perder sin que nadie lo note hasta el día de la instalación:
con el catálogo de demostración de sesenta productos todo va rápido.

**Decisión.** Criterios de rendimiento medidos, con un catálogo sintético de 20.000 productos y
pruebas que fallen si no se cumplen: del escaneo al precio en pantalla, menos de 150 ms; búsqueda
por nombre, menos de 200 ms; arranque, menos de 3 s (hoy 0,93 s).

**Consecuencias.** Hay dos sitios ya identificados que pueden no aguantar: `buscar_por_nombre` usa
`LIKE '%texto%'`, que no puede aprovechar ningún índice y recorre la tabla entera, y `listar()` trae
el catálogo completo a memoria para pintarlo. Con sesenta productos ninguno de los dos es un
problema y con veinte mil puede que tampoco, porque SQLite es rápido; el punto de la decisión no es
suponerlo en ninguna de las dos direcciones. Si los umbrales se cumplen, no se cambia nada y queda
una prueba de regresión que avisará el día que alguien los rompa. Si no se cumplen, hay margen de
sobra (FTS5, paginación de la tabla) antes de tener que tocar la arquitectura.

Los números medidos se publican en `TECNICA.md`, porque además de servirnos a nosotros son la
respuesta que el cliente quiere oír.

---

## D-023 — El transporte entre caja y servidor es HTTP con JSON, sobre la biblioteca estándar

**Fecha:** 2026-09-14 · **Estado:** aceptada · **Decide:** Santiago

**Contexto.** `D-015` decidió *que* hubiera un proceso servidor dueño de la base, pero no *cómo* le
habla la caja secundaria. Se evaluaron tres transportes.

**A — HTTP con JSON, usando `http.server` y `http.client`.** Sin dependencias nuevas, se depura con
un navegador o con `curl`, los tiempos límite ya vienen resueltos en la biblioteca, y el sondeo de
estado de conexión es un endpoint más.

**B — Socket TCP crudo con JSON por líneas.** Conexión persistente y latencia mínima, pero el
encuadre de mensajes, la reconexión y la concurrencia los escribimos nosotros. **Rechazada por el
riesgo, no por el esfuerzo:** los fallos de lectura parcial se manifiestan como cuelgues, que es
exactamente el defecto del que el cliente huye.

**C — XML-RPC.** También de la biblioteca estándar y mapea funciones casi 1:1, pero con XML verboso,
tipos limitados y siendo una tecnología que nadie va a querer mantener. **Rechazada.**

**Decisión.** Opción **A**.

El aviso de la documentación de Python sobre `http.server` —"no apto para producción"— se refiere a
exponerlo a internet hostil. Aquí atiende a dos clientes en una red local sin salida a internet
(`D-001`), y el servidor se ata explícitamente a la interfaz de la red local. No se abre ningún
puerto hacia fuera.

**Consecuencias.** El instalador no engorda: sigue siendo Python empaquetado y nada más, que era
media razón de `D-015` para descartar PostgreSQL. Se gana algo que no es evidente hasta que hace
falta: **el día que el cliente llame diciendo que la caja 2 no conecta, el diagnóstico se hace desde
el navegador del propio local**, sin herramientas ni depurador. La sobrecarga de HTTP por llamada es
de milisegundos en una LAN, irrelevante frente al umbral de 150 ms de `D-022`.

El servidor expone la superficie de `services/`, nunca la de `repositories/`, para que cada
operación siga siendo una única transacción. Son 13 operaciones.

---

## D-024 — La interfaz llama al servidor de forma bloqueante, con tiempo límite corto

**Fecha:** 2026-09-14 · **Estado:** aceptada · **Decide:** Santiago

**Contexto.** La condición 2 de `D-015` es que la ventana no se congele nunca esperando la red, y el
criterio de aceptación de la fase 13 exige avisar en menos de 3 segundos. Hay dos formas de
conseguirlo, y la diferencia entre ellas es el grueso del coste de la fase.

**A — Llamada bloqueante con tiempo límite de ~1,5 s y estado visible de reconexión.** Los 13 sitios
de llamada conservan su forma actual: `try / except DominioError → diálogo`.

**B — Hilo trabajador y respuesta por señales de Qt.** La ventana no se detiene jamás, pero hay que
reescribir los 13 sitios y **todo su manejo de errores**: la excepción deja de llegar por `except` y
pasa a llegar más tarde por una señal, lo que cambia el flujo de cada pantalla.

**Decisión.** Opción **A**, con el tiempo límite como constante en `config.py`.

**Consecuencias.** En una red local sana la ida y vuelta son 1–2 ms, de modo que la espera solo
ocurre cuando la red está realmente caída — que es justo cuando el cajero necesita enterarse. El
criterio de los 3 segundos se cumple por construcción, porque el límite es la mitad. Y **la caja
principal no se ve afectada en ningún caso**: es el servidor, y habla consigo misma.

Lo que se acepta a cambio: con la red rota, la ventana queda quieta hasta 1,5 s antes de mostrar el
aviso. Es un congelamiento acotado y explicable, no el indefinido del sistema anterior.

Si algún día se demuestra que molesta, se pasa a B pantalla por pantalla sin rehacer el transporte:
`D-023` y esta decisión son independientes.

**Queda pendiente y es la parte delicada:** un tiempo límite en el **cobro** deja a la caja sin saber
si la venta se registró. Reintentar la duplicaría; no reintentar la perdería. Se resuelve haciendo
`cerrar_venta` idempotente —identificador único del intento, generado en la caja y guardado por el
servidor, de modo que un reintento devuelva la venta original en lugar de crear otra— y eso exige
una columna nueva en `venta`. Ver la fase 13 de `docs/PLAN.md`.

---

## D-025 — La interfaz adopta un sistema visual acromático

**Fecha:** 2026-09-17 · **Estado:** ~~aceptada~~ **superada el mismo día por D-026** · **Decide:** Santiago

> Duró unas horas. Santiago la revisó y no le convenció: el acromatismo dejaba el aviso de
> producto agregado sin su verde —que es el del logotipo— y el resultado se parecía
> demasiado a lo anterior repintado. Se conserva la entrada porque el razonamiento de abajo
> sigue explicando de dónde salen varias cosas que D-026 mantiene.

**Contexto.** Hasta ahora la apariencia era una decisión tomada sobre la marcha: azul para lo
interactivo, verde para el total y para el éxito, rojo para el error, naranja para el descuento, y
los tamaños elegidos uno a uno. Funcionaba, pero no había ningún criterio escrito al que remitirse
cuando apareciera una pantalla nueva, y eso significa que cada pantalla nueva volvía a inventar.

Santiago aportó `docs/DESIGN.md`: el sistema visual de shadcn/ui, descrito token a token —pila de
tres grises, filete de 1 px, escala tipográfica con interletrado, cuatro radios y nada más.

**Decisión.** Adoptarlo como el sistema visual del programa, con tres desviaciones declaradas:

1. **El precio de la pantalla de consulta conserva sus 110 px.** El sistema topa el tamaño de
   display en 48 px, que es un tope de página web. Ese precio es lo único que el cliente pidió y
   tiene que leerse desde el otro lado del mostrador. Lo que sí adopta es el tratamiento: peso 600 y
   -0,05 em de interletrado.
2. **Los campos llevan filete en reposo y anillo de tinta al recibir el foco.** El sistema los deja
   sin borde y con un anillo gris claro, porque en una web viven dentro de una tarjeta blanca; aquí
   varios se apoyan sobre el lienzo, que es del mismo gris que su relleno, y sin filete
   desaparecen. El anillo de tinta, además, hace visible dónde va a caer el disparo de la pistola.
3. **Hay tema oscuro,** que el documento no cubre. Se deriva invirtiendo la pila de grises.

**Consecuencias.** La más visible es que **el sistema es acromático**: desaparecen el azul, el verde
y el naranja, y el rojo queda reservado a lo destructivo y al error.

- El total pasa de verde a negro sobre blanco. Se gana contraste —de 4,9:1 a 19:1— y se pierde el
  color como señal.
- El botón de cobrar pasa de verde a negro. Sigue siendo el único elemento de la pantalla con
  inversión de tono, así que sigue siendo inconfundible.
- **Lo que sí se pierde: el aviso de "producto agregado" ya no es verde.** Queda como una tarjeta de
  papel con texto en tinta, y se distingue del error porque el error es lo único con color. Un
  cajero que hoy reconoce "verde = bien, rojo = mal" por el rabillo del ojo va a tener que leer.
  Está anotado para preguntarlo en la próxima reunión: es de las cosas que solo se saben usando la
  caja de verdad. Si molesta, la salida es un icono, no recuperar el verde.

Todo esto vive en `ui/estilos.py`, que sigue siendo el único archivo con colores. Cambiar de sistema
otra vez es reescribir ese archivo y las medidas de dos o tres pantallas, no tocar la lógica.


---

## D-026 — Barra lateral, marca del negocio y tres colores con significado

**Fecha:** 2026-09-17 · **Estado:** aceptada · **Decide:** Santiago

**Contexto.** D-025 cambió los colores y poco más: la estructura siguió siendo la misma barra
superior con cuatro pantallas detrás de teclas de función. Santiago lo vio y el diagnóstico fue
exacto: *"solo le cambiaste los colores"*. Aportó dos cosas nuevas —una referencia de interfaz con
barra lateral y `docs/DESIGN.md` reescrito sobre el sistema de Seline Analytics— y una corrección:
**el aviso de producto agregado tiene que ser verde, porque el verde es el del negocio.**

**Decisión.** Tres cambios, y el primero es estructural, no de pintura.

**1. Barra lateral en lugar de barra superior.** Una columna de 236 px con la marca arriba, las
secciones agrupadas en *Caja* y *Administración*, la ficha del usuario abajo, y configuración y
cambio de usuario al pie. La ventana pasa a ser un armazón: barra lateral, cabecera que dice en qué
pantalla se está, y la pantalla. **Las pantallas dejan de pintar su propio título**, que ahora lo
pone la cabecera; por eso todas empiezan a la misma altura.

Con la barra, *Volver* sobra en catálogo e informes —era el tercer camino a la misma pantalla,
junto a Esc y la entrada *Venta*— y se retira. La consulta de precio conserva el suyo: es la
pantalla que se usa de cara al cliente.

**2. La marca del negocio entra en el programa.** `NOMBRE_COMERCIAL` pasa de "Tienda POS" a
**Punto y Fama**, con "Botillería y market" debajo. `NOMBRE_APP` **no cambia**: es el nombre de la
carpeta de datos, y tocarlo dejaría al programa sin encontrar la base ya instalada en la tienda.

**3. Tres colores, tres significados.** En vez del acento único que pide el documento:

| Color | Qué dice | Dónde |
|---|---|---|
| **Verde** | salió bien | producto agregado, total, botón de cobrar, precio en consulta |
| **Azul** | dónde estoy y qué puedo tocar | entrada activa del menú, foco, botón que confirma un diálogo |
| **Rojo** | se pierde o falló | cancelar venta, dar de baja, código no encontrado |

**Consecuencias.**

- `DESIGN.md` dice literalmente que añadir verde rompe el sistema. Se desoye a conciencia: un
  cajero necesita distinguir "lo agregué" de "no existe" sin leer, y el verde es el del logotipo.
  Lo que sí se respeta es la disciplina: **tres colores y ninguno más**, cada uno con un
  significado, y nada de color decorativo.
- Aparecen dos módulos nuevos. `ui/iconos.py` dibuja los iconos con QPainter en vez de traer una
  biblioteca o archivos de imagen: pesan nada, se colorean con la paleta —cosa que un PNG no hace—
  y no hay nada que empaquetar. `ui/barra_lateral.py` es la columna.
- El logotipo de la barra es **un sustituto dibujado**, no el logotipo real. Cuando haya un archivo,
  se carga en su lugar sin tocar nada más: quien lo pide solo pide un mapa de píxeles cuadrado.
- Una prueba cambió de sitio, no de intención: la sesión ya no está en una barra superior, así que
  `test_la_barra_superior_muestra_al_usuario` pasa a mirar la ficha de la barra lateral.
- Las sombras se pintan con `QGraphicsDropShadowEffect` y solo en las tarjetas de contenido. Qt no
  entiende `box-shadow`, y un efecto gráfico sobre una tabla que se repinta en cada escaneo sale
  caro justo donde el rendimiento es un requisito (D-022).

**Lo que sigue sin resolver.** Ni Inter ni Roobert están instaladas, así que la tipografía cae en
Segoe UI. Aguanta la escala, pero la voz del documento es de otra fuente. Empaquetar Inter con el
ejecutable es media hora de trabajo y una decisión de licencia que no está tomada.


---

## D-027 — El rojo de la marca, la barra plegable y el nombre del ejecutable

**Fecha:** 2026-09-17 · **Estado:** aceptada · **Decide:** Santiago

**Contexto.** D-026 gustó, y de esa revisión salieron cinco peticiones concretas. Van juntas
porque tocan lo mismo —la identidad del programa— y porque separarlas en cinco entradas no
aportaría nada.

**Decisiones.**

**1. El rojo del logotipo sustituye al azul como color de realce.** Con esto el sistema baja de
tres colores a **dos**, y cada uno pasa a tener también una regla de *cómo* se aplica, que es lo
que evita confundir el menú con un botón de borrar:

| Color | Qué dice | Cómo se aplica |
|---|---|---|
| **Rojo** `#BE1E2D` | dónde estoy, dónde está el foco, y lo que cancela o borra | lavado, filete o texto. **Nunca relleno** |
| **Verde** `#15803D` | salió bien, y adelante | es el único que va relleno: cobrar, guardar, entrar |

*El riesgo, anotado:* un anillo rojo alrededor de un campo de texto es, en casi todo el software,
la señal de "este dato está mal". Aquí significa "aquí va a caer el disparo de la pistola". Se
acepta porque el campo de escaneo está enfocado el 99% del tiempo y nunca muestra un error a la
vez, pero es lo primero que hay que mirar cuando alguien use la caja de verdad.

**2. La barra lateral se pliega a una tira de iconos** con Ctrl+B o con su botón. El estado se
guarda en `preferencias.json` —plegarla una vez tiene que bastar— pero **no aparece en la rueda de
configuración**: es un gesto, no un ajuste que nadie vaya a buscar en un formulario. Por eso el
diálogo de configuración tiene que arrastrar el valor al guardar, o desplegaría la barra por su
cuenta cada vez que alguien cambiara el tema.

**3. La tipografía sube un escalón.** El cuerpo pasa de 14 a 15 px y los pesos suben de 500 a
600–700 donde hay jerarquía. El gris del texto secundario se oscurece de `#78716C` a `#57534E`: el
del documento se lee bien en una web y se pierde en un mostrador con luz de tubo.

Efecto colateral que hubo que corregir: con la letra más grande, a 1280 px de ancho la columna del
producto se quedaba sin sitio y los nombres salían cortados. Se recortó de la barra lateral (244 →
232), de la tarjeta de totales (320 → 300) y del relleno de las celdas.

**4. El ejecutable pasa a llamarse `PuntoYFamaCaja.exe`** y lleva el icono de la marca.
`NOMBRE_APP` **sigue siendo `TiendaPOS`**: es el nombre de la carpeta de datos, y cambiarlo dejaría
al programa instalado en la tienda sin encontrar su base de datos.

*Cuidado con esto:* en la tienda hay accesos directos que apuntan a `TiendaPOS.exe`. Actualizar esa
instalación no es copiar la carpeta nueva encima: hay que rehacer los accesos directos, y si algún
día el servicio arranca solo, también esa entrada. Ver `docs/DESPLIEGUE-TIENDA.md`.

**5. El stock se ajusta desde una ventana propia.** Antes, corregir una cantidad obligaba a abrir el
formulario completo del producto y pasar por el código de barras, el nombre y el precio. Ahora hay
un botón **Stock** que abre solo el número, con saltos de ±1 y ±10 y un resumen de cuántas unidades
entran o salen.

No es una capacidad nueva —editar el stock a mano ya se podía— sino un camino más corto para lo que
más se repite en una tienda: contar mercadería y cuadrar el sistema. Por dentro llama al mismo
`actualizar_producto` de siempre, pasándole el código, el nombre y el precio que el producto ya
tenía, así que **no hace falta tocar el protocolo de red** (D-023).

*Lo que sigue sin existir* es el rastro de por qué cambió una cantidad. Eso es D-018 y la fase 9, y
este atajo lo hace más urgente: cuanto más fácil sea corregir el stock a mano, más ajustes habrá sin
explicación. Cuando llegue la fase 9, este diálogo es el primer sitio que tiene que generar un
movimiento.

**Consecuencias.** Diez pruebas nuevas cubren el plegado —incluido que guardar el tema no lo
deshaga— y el ajuste de stock, con sus bordes: sin selección no abre, el campo vacío vale la
cantidad actual, los saltos no bajan de cero y guardar la misma cantidad no llama al servicio. La
suite pasa de 239 a 250.

**Lo que sigue pendiente.** El logotipo de la barra lateral y del icono es **la marca dibujada**, no
el archivo del cliente: el círculo rojo con su tallo, que es la parte que sobrevive a 16 píxeles.
En cuanto exista `assets/logo.png`, tanto la interfaz como `tools/icono.py` lo usan sin tocar
código.


---

## D-028 — Ajustes del panel de venta, y dos fallos que salieron al mirarlo de cerca

**Fecha:** 2026-09-17 · **Estado:** aceptada · **Decide:** Santiago

**Contexto.** Revisando la pantalla de venta, Santiago señaló tres cosas: el fondo no se distinguía
de las tarjetas, el panel de totales "se veía muy cuadrado", y el aviso de producto agregado a veces
duraba un instante y parecía un fallo de pintado. Las tres tenían causa, y dos de ellas eran errores
de verdad, no cuestión de gusto.

**1. El lienzo pasa de `#FAFAF9` a `#F1EFEC`.** Con el tono del documento, el papel blanco de las
tarjetas y el fondo quedaban a un punto de distancia y los recuadros solo se veían por su filete de
1 px. Sigue leyéndose como papel cálido, que es lo que el sistema pide, pero ahora hay un escalón.

**2. Las cápsulas estaban cuadradas, y era un fallo.** Todos los controles redondos usaban
`border-radius: 999px`, el truco habitual de "ponlo enorme y que lo recorte el motor". **Qt no hace
eso: en cuanto el radio pasa de la mitad del alto del control, se rinde y dibuja las esquinas
rectas.** Afectaba a todos los botones, al buscador del catálogo y a las fichas.

Se sustituye por tres radios reales, uno por altura, siempre por debajo de la mitad del alto para
que Qt no vuelva a rendirse si el control crece: `RADIO_PILDORA` 20, `RADIO_PILDORA_ALTA` 26 para el
botón de cobrar y `RADIO_PILDORA_BAJA` 14 para las fichas.

**3. El panel de totales se parte en dos tarjetas.** Una sola, estirada a todo el alto, dejaba un
hueco blanco enorme entre el título y las cifras. Arriba queda lo que se va sumando —subtotal y
descuento, en renglones de recibo con el rótulo a la izquierda y la cifra a la derecha— y abajo lo
que se cobra: el total y las cuatro acciones. El hueco deja de ser un vacío y pasa a ser la
separación entre dos cosas distintas.

**Con el carrito vacío, la tarjeta de arriba no se muestra.** Una tarjeta que solo dice
"SUBTOTAL $0" no informa de nada. El botón de cobrar, en cambio, **no se mueve nunca**: el cajero lo
busca sin mirar, y una acción que cambia de sitio según el estado es una acción que se falla.

**4. El aviso de producto agregado se acortaba solo, y también era un fallo.** Cada aviso programaba
un `QTimer.singleShot` nuevo **sin cancelar el anterior**. Escanear un producto a los 4,8 segundos
del anterior dejaba vivo el temporizador del primero, que escondía el mensaje del segundo 200 ms
después de aparecer. Parecía un problema de pintado y era un temporizador de más — exactamente el
tipo de cosa que hace desconfiar de un sistema en una demostración.

Ahora hay **un solo temporizador**, propiedad de la vista, que se reinicia en cada aviso. Cinco
segundos desde el último mensaje, siempre.

**Y el aviso cambia de sitio.** Estaba bajo el campo de escaneo, que es su sitio natural, pero ahí
empujaba el carrito hacia abajo al aparecer y lo subía al desvanecerse: la tabla daba un salto en
cada producto. Pasa al hueco de la columna de totales, justo encima del botón de cobrar, donde crece
hacia arriba contra un espacio que ya estaba vacío. Así **no se mueve nada** —ni el carrito ni el
botón de cobrar— y de paso el aviso queda al lado del total, que es lo otro que el cajero mira al
terminar de pasar un producto. Lo que se pierde es ancho: un nombre largo ocupa dos líneas.

**5. El total, al mayor tamaño que quepa.** Sube de 48 a **62 px**, que es lo máximo que admite un
total de seis cifras —$480.000— en los 256 px útiles de la tarjeta; a 66 px ya se sale. Está medido
con `QFontMetrics`, no elegido a ojo.

Como el tamaño depende del texto y no del tema, se aplica sobre la etiqueta y no desde la hoja de
estilos, y con una escalera de reserva: una venta de siete cifras baja un escalón en vez de salirse
del borde. Dos trampas que costó ver:

- La fuente con la que se mide hay que **armarla entera** —familia, peso e interletrado— en lugar de
  partir de la que tenga puesta la etiqueta. Si se parte de ella, la medida arrastra el tamaño
  anterior y la elección sale distinta según cuál fuera el total previo.
- El estilo propio de la etiqueta lleva también el color, así que un cambio de tema no lo alcanza:
  hay que rehacerlo desde `repintar()`.

**Consecuencias.** Ocho pruebas nuevas: que el detalle aparece con el primer producto y se va al
cancelar, que el cobro no se mueve con el carrito vacío, que un aviso nuevo reinicia la cuenta atrás
en lugar de heredarla, que un error sustituye al aviso de éxito, que el tamaño del total no depende
del anterior y que el verde sobrevive al cambio de tema. La suite pasa de 250 a 258.

El fallo del radio estaba desde D-026 y el del temporizador desde la fase 2, o sea desde la primera
versión de la pantalla de venta. Ninguno lo habría detectado una prueba: el primero es estética y el
segundo depende de la cadencia con la que se escanee. Los dos aparecieron mirando la pantalla con
calma, que es el argumento para seguir generando capturas con `tools/capturas.py`.


---

## D-029 — Movimiento breve y con propósito

**Fecha:** 2026-09-23 · **Estado:** aceptada · **Decide:** Santiago

**Contexto.** Santiago pidió pulir el diseño con animaciones: cosas que aparecen y desaparecen, y
una barra lateral que no se pliegue de golpe. Esto **revierte una decisión escrita**: el
docstring de `BarraLateral.plegar` decía *"No se anima. Una transición de 200 ms es agradable
en una web y un estorbo en una caja"*. El argumento era bueno y sigue siéndolo a medias: una
animación que haya que esperar sí es un estorbo. Lo que no lo es es una que acompaña un cambio
que ya ocurrió.

**Decisión.** Se anima, con tres reglas que resuelven la objeción de antes:

1. **El estado cambia al instante; solo el dibujo tarda.** `esta_plegada`, la visibilidad del
   aviso y el contenido del carrito son definitivos en el momento de la acción.
2. **Todo se interrumpe.** Un Ctrl+B a medio plegado da la vuelta desde donde esté; un escaneo
   durante el fundido de salida del aviso lo cancela.
3. **Se puede apagar** desde F9 (*Animar los cambios en pantalla*, encendida de fábrica). Es
   una preferencia más en `preferencias.json` (D-013).

Primera tanda, las tres que explican algo:

| Qué | Cómo | Por qué |
|---|---|---|
| Línea del carrito que entra o suma | destello verde de 700 ms | la selección gris no distingue «acaba de pasar» de «ya estaba» |
| Aviso de escaneo | fundido de entrada y salida; parpadeo si se renueva | dos productos seguidos daban dos avisos idénticos |
| Barra lateral | ancho animado en 180 ms, desacelerando | que se lea como un cajón que se cierra, no como un salto |

Las duraciones, las curvas y la lista de lo que **no** se anima están en la sección
«Movimiento» de `docs/DESIGN.md`, que pasa a ser la referencia para cualquier animación nueva.

**Consecuencias.**

- Módulo nuevo, `ui/movimiento.py`, con las duraciones con nombre y un `Fundido` reutilizable.
- **Un cambio visible de la barra plegada:** los rótulos de sección (*CAJA*, *ADMINISTRACIÓN*) y
  el nombre del negocio conservan su sitio aunque estén ocultos. Antes, al plegar, los iconos
  subían unos 25 px porque los rótulos desaparecían del layout; con el ancho animado ese salto
  vertical habría quedado a la vista. Ahora los iconos están a la misma altura en los dos
  estados y la tira plegada tiene un hueco donde iban los rótulos.
- **Dos trampas de Qt** que condicionan lo que se puede animar. Un widget admite **un solo**
  efecto gráfico, y las tarjetas ya gastan el suyo en la sombra (D-026): no se les puede poner
  un fundido. Y un efecto de opacidad quita el ClearType al texto; por eso el fundido del aviso
  lo enciende solo mientras dura la animación.
- **Rendimiento (D-022).** El destello repinta solo la franja de su fila, no la tabla. El
  plegado reajusta la tabla del carrito en cada fotograma durante 180 ms; con carritos de
  decenas de líneas no se nota, y se apaga con la preferencia si en el PC de la tienda sí.
- **Pruebas.** La suite corre con `movimiento.suprimir()`, igual que el sonido, para no depender
  del reloj. Diecisiete pruebas nuevas en `tests/test_ui_movimiento.py` lo encienden y
  comprueban las tres reglas, más que los iconos no cambien de altura al plegar. La suite pasa
  de 258 a 275.

**Segunda tanda, el mismo día.** Santiago dio por buena la primera y pidió seguir:

- **PIN incorrecto:** la ventana de acceso se sacude (320 ms, 9 px, amortiguada). Se mueve la
  ventana y no el campo porque el campo vive en un layout que se recoloca al aparecer el
  mensaje de error. Un segundo error a mitad de sacudida reinicia desde el sitio original.
- **Consulta de precio:** el resultado entra con fundido y parpadea si ya había otro precio.
  Limpiar es inmediato.
- **Diálogos:** todos se abren con un fundido de 120 ms, enganchado ventana a ventana
  (`movimiento.aparecer_al_abrir`) y no con un filtro sobre toda la aplicación, que vería pasar
  cada evento del programa. El cierre no se anima.
- **Descartado: el despliegue de la tarjeta de subtotal.** Tiene sombra y no admite otro
  efecto; animar su altura aplastaba el contenido; y aparece en el mismo instante que el
  destello y el aviso. Queda anotado en «Qué no se anima» de `DESIGN.md`.

Nueve pruebas más; la suite pasa de 275 a 284. Ninguna de estas animaciones es un requisito
del cliente: todo esto es decisión de Santiago (3.2).
