# Boleta electrónica ante el SII — por qué es otro proyecto

**Fecha:** 2026-09-22 · **Estado:** no comprometido, pendiente de que el cliente decida
**Decide:** el cliente, con presupuesto aparte.

Este documento existe para que la conversación sobre boletas se tenga **antes** de prometer nada, y
no después. No describe trabajo planificado: describe lo que habría que hacer, lo que cuesta, lo que
rompe del sistema actual, y qué necesitamos saber para poder presupuestarlo.

Lo que sí está comprometido —cierre de caja, usuarios por empleado y medios de pago— va aparte, en
`docs/PREGUNTAS-CIERRE-Y-USUARIOS.md`. **Los dos temas no deberían mezclarse en la misma
conversación**: uno es una mejora del sistema que ya existe; el otro cambia qué es el sistema.

---

## 1. Un malentendido que conviene aclarar primero

En la conversación apareció la idea de **"impresoras fiscales certificadas"**. En Chile **no existe
ese régimen**. Las impresoras fiscales homologadas son de Argentina, Brasil y Venezuela.

Chile tomó el camino contrario: desde 2014 usa **documentos tributarios electrónicos (DTE)**, que
son archivos XML firmados digitalmente y enviados al SII, impresos —si se imprimen— en impresoras
corrientes. La boleta electrónica es obligatoria desde 2021 para quien emite boletas.

Esto importa porque significa que lo que el cliente tiene hoy es casi seguro una de tres cosas, y
hay que averiguar cuál:

1. **Impresoras térmicas de tickets corrientes** (ESC/POS). Es el caso más probable y el más fácil.
2. **Un equipo atado a un proveedor de boleta electrónica que ya contrató.** Si es esto, la mitad
   del trabajo ya está hecha y hay que integrarse con ese proveedor, no empezar de cero.
3. **El comprobante que imprime la propia máquina de Mercado Pago**, que es un *voucher de pago*,
   **no una boleta**. Confundir los dos es muy común.

**Nada de lo que sigue se puede presupuestar sin saber cuál de las tres es.**

---

## 2. Cómo funcionaría, si se hiciera

El camino sensato no es hablar con el SII directamente, sino con un **proveedor de API de
facturación electrónica** que haga el trabajo pesado. En Chile hay varios (LibreDTE, que además es
de código abierto; SimpleAPI; OpenFactura de Haulmer; entre otros).

El flujo sería este:

1. **El cliente compra su certificado digital.** Un archivo `.pfx` de un proveedor acreditado, a
   nombre del representante legal. Del orden de 20 a 40 mil pesos al año.
2. **El cliente se inscribe en el SII** como emisor de boleta electrónica, en la modalidad de
   *Sistema de Facturación de Mercado* (es decir, usando software de un tercero certificado).
3. **Se carga el certificado en el panel del proveedor.** A partir de ahí, el proveedor puede firmar
   documentos legalmente a nombre de la empresa del cliente.
4. **Se descargan del SII los folios autorizados (CAF)** y se cargan en el proveedor. Son los
   números de boleta que se pueden usar.
5. **El POS, al cobrar, manda una petición al proveedor** con los datos de la venta. El proveedor
   arma el XML, lo firma y devuelve el folio asignado y el timbre electrónico (el código de barras
   PDF417 que va impreso).
6. **El POS imprime el ticket** con ese timbre, y el cliente se lleva su boleta.
7. **Certificación y paso a producción**: antes de emitir boletas reales hay un trámite con el SII,
   con folios de prueba y un ambiente separado. Luego se descargan los folios reales y se cambia de
   ambiente.

En lo técnico, la parte que nos toca es la más pequeña de todas: una petición HTTP con JSON, que en
Python se hace con la biblioteca estándar, igual que ya hace `src/tienda_pos/red/cliente.py` para
hablar entre las dos cajas. **Sin dependencias nuevas.**

**Eso es justamente lo engañoso de esta funcionalidad: la parte fácil se ve, y la difícil no.**

---

## 3. Lo que hay que verificar antes de creerse el plan de arriba

Tres cosas que hay que confirmar con el proveedor y con el SII, no dar por supuestas:

- **Quién certifica.** Si nuestro POS arma un JSON y el proveedor genera y firma el DTE, el cliente
  debería inscribirse bajo la certificación del proveedor y **no** pasar el set de pruebas completo
  del SII. Pregunta literal al proveedor: *"¿mi cliente se inscribe bajo la certificación de ustedes
  o necesita certificación propia?"*. Si la respuesta es la segunda, **el proyecto es varias veces
  más grande** y hay que replantearlo entero.
- **El formato exacto del JSON.** Cada proveedor tiene el suyo, y ninguno es el XML crudo del SII.
  Hay detalles que muerden: en boleta el precio del ítem va **con IVA incluido** (al revés que en
  factura), hay campos obligatorios que no son evidentes, y el desglose de totales tiene reglas
  propias. Sale de la documentación del proveedor, no de un ejemplo genérico.
- **Qué pasa con el reporte al SII.** Cada boleta se informa al SII al emitirse. Quién lo hace, con
  qué frecuencia y qué ocurre si falla es responsabilidad del proveedor, pero hay que verlo escrito.

---

## 4. Por qué esto es otro proyecto, y no una funcionalidad más

Esta es la parte importante del documento.

### 4.1 Obliga a tener internet, y el sistema está diseñado para no tenerlo

Toda la arquitectura actual asume que **no hay internet**. Es una decisión tomada a conciencia
(D-001), y la solución de las dos cajas es una red local entre ellas, no una conexión a la nube
(D-015). La boleta electrónica necesita internet permanente.

Y entonces hay que responder a una pregunta que hoy no existe: **¿qué pasa cuando se cae internet un
sábado por la tarde?**

- ¿El cajero no puede cobrar?
- ¿Se cobra y la boleta queda en una cola, y el cliente se va sin su boleta?
- ¿Se emite en contingencia y se regulariza después?

Ninguna de las tres es gratis, ninguna es obvia, y las tres son trabajo. **Este es el punto donde el
proyecto deja de ser el que es hoy.**

### 4.2 Cada error pasa a tener consecuencias tributarias

Hoy, si el sistema se equivoca en una venta, se corrige y ya está. Con boletas, un error es un
documento tributario mal emitido, y eso se arregla ante el SII.

Un ejemplo concreto y real: el sistema ya reintenta cobros automáticamente cuando la red local falla
(D-024), porque es mejor reintentar que perder una venta. Con boletas, un reintento mal manejado
**emite dos boletas legales por una sola venta**. Lo que hoy es una comodidad pasa a ser un riesgo,
y hay que rediseñarlo.

### 4.3 Anular una venta deja de ser borrar una fila

Una boleta emitida no se borra. Se anula con una **nota de crédito electrónica**, que es otro tipo
de documento, con sus propios folios y su propio flujo. Hoy el sistema no anula nada en absoluto.
Esto por sí solo casi duplica el alcance de "emitir boletas".

### 4.4 Aparecen dos numeraciones que no son la misma

El sistema ya tiene su propio número de venta. El folio del SII es otro número distinto, asignado
desde los folios autorizados. Van a convivir y no se pueden confundir nunca. Es trabajo y es
disciplina.

### 4.5 Cambia la relación de soporte

Si el sistema deja de emitir boletas un sábado, el problema es **tributario del cliente**, y la
llamada llega a nosotros. Es una responsabilidad distinta a la de un programa que anota ventas, y
hay que hablarla antes de aceptarla: qué soporte hay, en qué horario, y qué pasa cuando falla algo
que no depende de nosotros —el proveedor, internet, el SII—.

### 4.6 Añade un gasto mensual permanente

El sistema actual se paga una vez y funciona. Esto añade certificado digital anual y, casi seguro,
una cuota del proveedor de la API. **Es exactamente el modelo de LocalShop**, que es lo que el
cliente dijo que le llamaba la atención. Vale la pena que lo sepa: si lo que le gustaba era esto, la
conversación es otra.

---

## 5. Lo que esto tiene de bueno

Para no pintar solo el lado caro:

- La parte de código que nos toca es pequeña y limpia, y encaja bien en la arquitectura actual.
- Si el cliente ya tiene un proveedor contratado, buena parte del trámite está hecho y el trabajo
  baja mucho.
- Es la funcionalidad que hace que el sistema se vea "completo" al lado de LocalShop.
- Y se puede probar barato: el ambiente de certificación de los proveedores es gratis, y una prueba
  de concepto diría en una tarde cuánto trabajo real hay. **Esa prueba es lo más sensato que se
  puede hacer antes de presupuestar.**

---

## 6. Lo que necesitamos que el cliente responda

| # | Pregunta | Por qué importa | Respuesta |
|---|---|---|---|
| H7 | ¿Necesita que el sistema **emita boleta válida ante el SII**, o eso lo resuelve por otro lado? | Es la pregunta que decide si este documento se archiva o se convierte en un presupuesto. Está sin responder desde la primera reunión (era la G16). | |
| H7b | **Y hoy, ¿cómo entrega la boleta?** ¿Tiene algo contratado, usa el portal del SII, o entrega el comprobante de la máquina Mercado Pago? | **La que de verdad aclara el panorama.** La boleta electrónica es obligatoria desde 2021, así que si él ya emite, *ya tiene algo funcionando*, y saber qué es cambia el proyecto entero. Integrarse con un proveedor que ya tiene es mucho más barato que empezar de cero. | |
| H6 | Las impresoras que tiene, ¿de **qué marca y modelo** son? ¿Puede mandar una foto del aparato y de los cables de atrás? | Sin esto no se puede prometer nada de impresión. La foto de los cables importa tanto como el modelo: el cajón de dinero normalmente cuelga de la impresora por un cable que parece de teléfono, y eso decide si abrirlo cuesta veinte líneas o es imposible. Y si hay que imprimir boletas, la impresora tiene que poder con el código PDF417. | |
| H13 | ¿Tiene ya **certificado digital** (firma electrónica) a nombre de la empresa? ¿Y el RUT con inicio de actividades y giro al día? | Son requisitos previos del cliente, no nuestros. Si no los tiene, el trámite lo hace él y tiene sus tiempos. | |
| H14 | ¿Cuántas boletas emite al día, más o menos? | Define qué plan de proveedor necesita y cuánto cuesta al mes. | |
| H15 | ¿Le importa pagar una **cuota mensual permanente** por esto? | Contrasta con el modelo actual, que se paga una vez. Enlaza con la G18, que sigue sin responder. | |
| H16 | Si se cae internet en plena venta, ¿qué prefiere: **no poder cobrar**, o cobrar y entregar la boleta después? | Es la decisión de diseño más cara de todo esto, y es suya, no nuestra. | |

---

## 7. La decisión, planteada como es

El cliente tiene tres caminos, y conviene presentárselos así de claros:

**A. No hacer nada por ahora.** El sistema registra ventas, y las boletas las sigue emitiendo por
donde las emite hoy. Coste cero. Es la opción por defecto y es perfectamente razonable si lo que
tiene hoy le funciona.

**B. Imprimir un vale interno, sin valor tributario.** Un papelito con los productos y el total, que
además serviría para abrir el cajón de dinero automáticamente al cobrar. Barato, funciona sin
internet, no toca nada del SII. **Cubre la parte de "quiero que se imprima algo y se abra el cajón"
sin meterse en lo tributario.** Si lo que el cliente quiere es la sensación de un POS completo, esto
le da casi todo por casi nada.

**C. Boleta electrónica de verdad.** Todo lo de este documento. Presupuesto aparte, gasto mensual
permanente, internet obligatorio y una conversación seria sobre soporte y responsabilidad.

**Nuestra recomendación:** empezar por **B** si tiene impresoras térmicas corrientes, y no tocar
**C** hasta saber la respuesta a H7b. Hay bastantes posibilidades de que el cliente ya tenga
resuelta la boleta y lo que realmente quiera sea que le impriman el detalle y se le abra el cajón.

---

## 8. Compromiso actual

**Ninguno.** Este documento no compromete trabajo. Mientras no haya una decisión explícita del
cliente y un presupuesto aparte, el sistema **no emite boletas, no está conectado al SII y no
imprime nada**, tal como está escrito en D-006 y en la nota de "lo que no se debe prometer" de
`docs/PREGUNTAS-CLIENTE.md`.

Si el cliente elige **C**, el primer paso no es programar: es la prueba de concepto contra el
ambiente de certificación de un proveedor, que es gratis y contesta en una tarde lo que este
documento solo puede estimar.

---

### Nota sobre la exactitud de este documento

Lo de arriba se apoya en cómo funciona el sistema de DTE chileno a día de hoy, y la normativa del
SII cambia. **Antes de presupuestar hay que verificar los requisitos vigentes en sii.cl y en la
documentación del proveedor que se elija.** Los costes mencionados son órdenes de magnitud, no
cotizaciones.
