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
