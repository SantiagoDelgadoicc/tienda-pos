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
