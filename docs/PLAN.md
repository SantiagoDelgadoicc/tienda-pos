# Plan de trabajo — Prototipo Tienda POS

Documento vivo. Se actualiza a medida que avanzamos.
`[ ]` pendiente · `[x]` completado

**Estado:** las fases 0 a 7 están cerradas y el prototipo ya se presentó. Las fases 8 a 14 son la
segunda etapa, abierta tras la primera reunión con el cliente.

> **Advertencia de plazo de la primera etapa, que se cumplió:** un POS completo, empaquetado y
> documentado en una semana es ambicioso. Por eso las fases están ordenadas de forma que
> **al terminar la Fase 2 ya existe una demo presentable**. Si el tiempo se agota, se corta
> en la fase que sea y lo entregado sigue siendo coherente y estable.

---

## Fase 0 — Repositorio y documentación base

- [x] Crear repositorio privado `SantiagoDelgadoicc/tienda-pos`
- [x] Inicializar git en `C:\Projects\Prototipo` y crear la estructura de carpetas
- [x] `.gitignore` (entornos, `__pycache__`, `dist/`, bases de datos, logs)
- [x] `README.md`
- [x] `CLAUDE.md` con contexto, trazabilidad de requisitos, arquitectura y convenciones
- [x] `docs/PLAN.md`
- [x] `docs/PREGUNTAS-CLIENTE.md`
- [x] `docs/DECISIONES.md`
- [x] Primer commit y push

**Criterio de aceptación:** el repositorio existe, tiene su primer commit y los documentos
son comprensibles para alguien ajeno al proyecto.

---

## Fase 1 — Núcleo de datos y negocio (sin interfaz)

- [x] `config.py`: rutas de datos en `%LOCALAPPDATA%\TiendaPOS\`
- [x] `utils/money.py`: formato y aritmética de CLP en enteros
- [x] `db/schema.sql`: esquema completo
- [x] `db/connection.py`: conexión única, PRAGMAs (WAL, `foreign_keys`), transacciones
- [x] `db/migrations.py`: versionado del esquema con `PRAGMA user_version`
- [x] `db/seed.py`: catálogo demo de minimarket (~60 productos con EAN-13 válidos)
- [x] `domain/models.py` y `domain/errors.py`
- [x] `repositories/`: productos, ventas, usuarios
- [x] `services/catalogo.py`: búsqueda por código exacto y por nombre parcial
- [x] `services/venta.py`: carrito, agrupación de repetidos, descuento, totales y cierre
      transaccional con descuento de stock
- [x] `services/auth.py`: PIN con hash y salt, roles
- [x] Pruebas `pytest` de todo lo anterior

**Criterio de aceptación:** las pruebas pasan, incluyendo código inexistente, stock
insuficiente, descuento mayor que el total y fallo a mitad del cierre de venta, que debe
revertir por completo sin dejar datos a medias.

---

## Fase 2 — Interfaz de venta y consulta de precio ← primera demo presentable

- [x] Ventana principal, gestión del foco y atajos de teclado
- [x] Campo de escaneo, tabla del carrito y totales
- [x] Pantalla de consulta de precio (F2), tipografía grande
- [x] Diálogo de código no encontrado
- [x] Cierre de venta con confirmación

**Criterio de aceptación:** tecleando códigos (equivalente exacto a lo que envía la pistola)
se puede consultar un precio, armar un carrito y cerrar una venta, sin que nada se rompa.

---

## Fase 3 — Administración, acceso e informe del día

- [x] Diálogo de PIN al iniciar y modo administrador
- [x] Alta, edición y baja lógica de productos (solo administrador)
- [x] Descuento manual sobre la venta (monto o porcentaje)
- [x] Pantalla de ventas del día: listado, total y detalle
- [x] Stock visible en la ficha del producto

**Criterio de aceptación:** un administrador da de alta un producto, lo escanea, lo vende,
lo ve reflejado en el informe del día y comprueba el stock descontado.

---

## Fase 4 — Robustez

- [x] Manejador global de excepciones con diálogo legible; la aplicación no se cierra
- [x] Logging rotativo
- [x] Respaldo automático de la base al iniciar, con retención de los últimos 7
- [x] Sonidos distintos para éxito y error
- [x] Validación del formato del código y detección pistola/teclado
- [x] Pruebas de los caminos de error

**Criterio de aceptación:** provocar errores a propósito (base bloqueada, código con basura,
cierre forzado a mitad de venta) no pierde datos ni cierra el programa.

---

## Fase 5 — Empaquetado

- [x] PyInstaller → `TiendaPOS.exe`
- [x] Creación de la base y de los datos demo en el primer arranque
- [x] Icono propio y acceso directo en el escritorio
- [x] Prueba en carpeta limpia, en un equipo sin Python

**Criterio de aceptación:** doble clic en el acceso directo y el programa abre en menos de
3 segundos sin entorno de desarrollo instalado.

---

## Fase 6 — Documentación y demo

- [x] `docs/MANUAL-USUARIO.md` con capturas
- [x] `docs/TECNICA.md`
- [x] `docs/GUION-DEMO.md`
- [x] `docs/PREGUNTAS-CLIENTE.md` finalizado
- [x] README actualizado

**Criterio de aceptación:** alguien ajeno instala, ejecuta y realiza una venta guiándose
solo por la documentación.

---

## Fase 7 — Mejoras pedidas por Santiago (2026-09-11)

- [x] Descuento aplicable a un producto además de a la venta entera (D-012, migración 2)
- [x] Botón de copiar el código de barras en cada línea del carrito
- [x] Subir y bajar la cantidad de una línea, con el ratón y con el teclado (↑ ↓ ← → + −)
- [x] Rueda de configuración (F9): tema, sonido, confirmación de cobro, barra de atajos
- [x] Tema oscuro, aplicable sin reiniciar (D-013)
- [x] Manual, documentación técnica y capturas al día

**Criterio de aceptación:** un cajero arma una venta, cambia cantidades, descuenta un producto
y cobra sin tocar el ratón; y el tema elegido sigue puesto al volver a abrir el programa.

No confirmado por el cliente: **todo lo de esta fase**. Son decisiones de Santiago, como el
resto del punto 3.2 de `CLAUDE.md`.

### Fase 7.1 — Movimiento (2026-09-23, D-029)

- [x] Sección «Movimiento» en `docs/DESIGN.md`: duraciones, curvas y qué no se anima
- [x] Destello verde en la línea del carrito que entra o suma una unidad
- [x] Fundido de entrada y salida del aviso de escaneo, y parpadeo al renovarse
- [x] Plegado animado de la barra lateral, sin que los iconos cambien de altura
- [x] Preferencia *Animar los cambios en pantalla* en F9
- [x] Segunda tanda: sacudida del PIN incorrecto, fundido del precio en la consulta y de la
      apertura de los diálogos
- ~~Despliegue animado de la tarjeta de subtotal~~ *descartado:* ver D-029

**Criterio de aceptación:** ninguna animación retrasa un escaneo ni el foco, todas se
interrumpen, y con la preferencia apagada la caja se comporta exactamente como antes.

También decisión de Santiago, no del cliente.

---

## Segunda etapa — tras la primera reunión con el cliente (2026-09-13)

El cliente vio el prototipo y aportó información que hasta ahora no teníamos. Lo relevante:

- Su sistema anterior **se le quedaba pegado**. Es su queja concreta, y convierte el rendimiento en
  un requisito medible en vez de en una aspiración (D-022).
- En ese sistema tenía, por producto, **cantidad, precio de compra, precio de venta y familia**.
  Hoy solo existen el precio de venta y el stock. *(2026-09-14: el cliente retiró la familia y el
  precio de compra. Se quedan cantidad y precio de venta, o sea lo que ya había. D-016 y D-017
  quedan retiradas.)*
- Quiere **conservar esos datos**, pero el PC donde estaban no enciende. Ver `RESCATE-DATOS.md`.
- El sistema debe funcionar en **dos PC**. Esto desmonta el supuesto de "una sola caja" con el que
  se construyeron las siete fases anteriores (D-015).
- Quiere una **instalación mejor** que copiar una carpeta (D-020).
- Mencionó **LocalShop** y preguntó si se puede hacer algo parecido. LocalShop es un servicio
  chileno por suscripción, en la nube, con catálogo precargado y boleta electrónica ante el SII.
  Según lo hablado, lo que le atrajo fue lo completo que se ve, no la nube ni el SII —pero eso hay
  que confirmarlo, porque si pide boleta electrónica es otro proyecto. Ver el bloque G de
  `PREGUNTAS-CLIENTE.md`.

**Ya estaba hecho, y solo hay que confirmárselo:** el stock baja al vender, dentro de la misma
transacción que registra la venta, y la venta se rechaza si no alcanza (D-009).

Las fases están ordenadas para que lo que se puede enseñar llegue antes que lo caro e invisible. La
fase 13 es la más costosa y la que más código toca, y por eso va después de las que cambian el
modelo de datos: da igual portar cinco funciones más que cinco menos.

### Orden de ejecución revisado el 2026-09-14

Los números de fase se conservan para no romper las referencias, pero **el orden en que se abordan
cambia**. Dos hechos nuevos lo justifican: el cliente ya designó el PC principal y está por cargar
el catálogo, pero **todavía no vende**; y al retirar la familia y el precio de compra, la fase 9
deja de ser bloqueante, que era el único motivo para ponerla primero.

1. **Fase 10 — importación CSV.** Es lo que hace falta esta semana: es la diferencia entre teclear
   el catálogo entero y abrirlo de un archivo.
2. **Fase 13 — las dos cajas.** Ya sin nada que la bloquee. Mientras solo carguen catálogo no
   hace falta, pero tiene que estar antes de que empiecen a vender.
3. **Fase 12 — usuarios.** Antes de vender de verdad: los PIN de fábrica están publicados en el
   manual.
4. **Fase 9 — trazabilidad de inventario.** Recortada a D-018 y sin prisa.
5. **Fase 11 y fase 14** cuando toquen.

La fase 8 sigue por delante de todo lo que dependa del catálogo real: mientras no se sepa si los
datos del PC viejo se rescatan o hay que teclearlos, no se sabe cuánto trabajo es cargarlo.

**Mientras tanto, sin escribir código:** que carguen en una planilla y no en el programa —dos
personas pueden llenarla en paralelo sin ningún problema de sincronización— y que el catálogo se
cargue **solo en el PC principal** si lo meten directo al sistema. Cargar en los dos vuelve a crear
el problema de bases divergentes, y esta vez con los datos de verdad.

---

## Fase 8 — Rescate de los datos del cliente ← lo urgente

No es programación. Es ejecutar `docs/RESCATE-DATOS.md` y no se puede escribir el importador de
verdad hasta saber en qué formato están los datos.

- [ ] Paso 0: preguntar si ya existe una copia (pendrive, correo, contador, listado impreso)
- [ ] Paso 1: diagnosticar el PC y decidir la ruta de rescate
- [ ] Paso 2 y 3: obtener los archivos y copiarlos en bloque a un disco sano
- [ ] Paso 4: identificar el formato y exportarlo a CSV en UTF-8
- [ ] Paso 5: normalizar al CSV de importación
- [ ] Avisar al cliente de que las cantidades habrá que contarlas físicamente igualmente

**Criterio de aceptación:** existe un CSV normalizado con el catálogo real del cliente, o la
constancia escrita de que hay que recargarlo a mano y cuánto costaría (paso 6 de la guía).

---

## Fase 9 — Trazabilidad de inventario (D-018)

**Recortada el 2026-09-14.** Era "modelo de datos ampliado (D-016, D-017, D-018)". El cliente retiró
la familia y el precio de compra, así que se cae todo lo que dependía de ellos: la tabla `familia`,
`producto.familia_id`, `producto.costo_clp`, `venta_linea.costo_unit_clp`, la pantalla de familias y
los informes de margen y de ventas por familia. Queda D-018, que nunca dependió de esos campos.

**Deja de ser bloqueante.** El motivo para hacerla antes que nada era evitar que el catálogo se
cargara sin familia ni costo y hubiera que reabrir producto por producto. Sin esos campos, ese
retrabajo no existe: el catálogo se puede cargar contra el esquema de hoy.

Migración 3: subir `VERSION_ESQUEMA`, registrar la función en `_MIGRACIONES` y no tocar jamás las
migraciones ya publicadas.

- [ ] Tabla `movimiento_inventario`, y el stock deja de cambiar sin emitir un movimiento. Hoy hay
      dos vías que lo cambian: `venta.py::cerrar_venta` vía `descontar_stock`, y
      `catalogo.py::actualizar_producto`, que **sobreescribe el número a pelo**. La segunda es el
      agujero: llega mercadería, alguien edita el stock y no queda rastro de qué entró ni de quién
      fue.
- [ ] `producto.stock_minimo` (hoy el umbral está fijo en `_STOCK_BAJO = 5` en `productos_view.py`,
      igual para el pan que para el whisky)
- [ ] Generar un movimiento `carga_inicial` para el catálogo ya existente dentro de la propia
      migración, o el histórico arranca con un salto inexplicable
- [ ] Pantalla de ingreso de mercadería, que sube stock y deja movimiento
- [ ] Historial de movimientos de un producto, que es para lo que existe todo esto
- [ ] Decidir y dejar escrito qué pasa con `db/schema.sql`: hoy está congelado como v1 y ya no
      refleja la base real, porque le falta la columna que añadió la migración 2. Recomendación:
      mantenerlo congelado y ponerle una cabecera que lo diga.

**Criterio de aceptación:** una base ya existente migra sin perder nada; el stock no se puede
cambiar por ninguna vía sin dejar rastro; ante un descuadre se puede abrir un producto y leer de
dónde salió cada unidad.

---

## Fase 10 — Importación y exportación CSV (D-019)

Dos pasos separados: **analizar**, que no toca la base y devuelve fila por fila si es alta,
actualización o error; y **aplicar**, que escribe todo en una sola transacción.

Columnas: `codigo_barras,nombre,precio_venta,stock`.

*(2026-09-14: eran `codigo_barras,nombre,familia,precio_venta,precio_compra,stock`. Se quitan las
dos columnas retiradas por el cliente. **Si el importador encuentra `familia` o `precio_compra` en
el archivo, las ignora sin dar error**: el CSV que el cliente o el rescate produzcan puede traerlas,
y un archivo con columnas de más no es un archivo inválido.)*

- [ ] Servicio de importación con sus dos pasos
- [ ] Pantalla con vista previa: cuántas altas, cuántas actualizaciones, qué filas fallan y por qué
- [ ] Exportación del catálogo a CSV
- [ ] Casos límite, que aquí son la mitad del trabajo: codificación Windows-1252 frente a UTF-8;
      separador `;` frente a `,`; miles con punto y decimal con coma; códigos repetidos dentro del
      propio archivo; productos sin código de barras; stock negativo; archivo vacío; archivo sin
      cabecera; archivo de 20.000 filas

**Criterio de aceptación:** el CSV de la fase 8 entra sin perder ni una fila, y volver a importarlo
actualiza en lugar de duplicar.

---

## Fase 11 — Rendimiento demostrable (D-022)

- [ ] Generador de catálogo sintético de 20.000 productos
- [ ] Pruebas con umbral que falle: escaneo → precio en pantalla < 150 ms; búsqueda por nombre
      < 200 ms; arranque < 3 s
- [ ] Revisar los dos puntos ya identificados: la búsqueda por nombre usa `LIKE '%texto%'`, que no
      puede usar índice, y el listado del catálogo lo trae entero a memoria
- [ ] Publicar los números medidos en `TECNICA.md`

**Criterio de aceptación:** los umbrales se cumplen con 20.000 productos y hay una prueba que
avisará el día que alguien los rompa. Si no se cumplen, se arregla antes de cerrar la fase.

---

## Fase 12 — Gestión de usuarios · *absorbida por la fase 15 el 2026-09-24*

> Se hizo dentro de la fase 15 (D-032), cuando el cliente pidió un usuario por empleado. La
> segunda casilla cambió de forma: en lugar de obligar a cambiar el PIN de fábrica, el PIN lo
> genera el sistema. La tercera pasa a la fase 18, que es el cierre por empleado.

Es el hueco que ya estaba pendiente antes de esta reunión. La lógica existe y está probada
(`services/auth.py::cambiar_pin`), pero no está conectada a ninguna pantalla. Con dos cajas y dos
personas atendiendo deja de ser opcional: hay que saber quién vendió qué, y los PIN de hoy están
publicados en el manual.

- [x] Pantalla de usuarios: crear, cambiar el PIN, dar de baja *(fase 15)*
- [x] ~~Obligar a cambiar el PIN de fábrica la primera vez~~ → el PIN lo genera el sistema *(D-032)*
- [x] Ventas del día por cajero → *hecho en la fase 18*, en el cierre de caja

**Criterio de aceptación:** se puede poner el sistema en una tienda sin que ningún PIN publicado en
la documentación sirva para entrar.

---

## Fase 13 — Dos cajas (D-015) ← la fase cara

**Cómo, decidido el 2026-09-14:** el transporte es **HTTP con JSON sobre la biblioteca estándar**
(D-023) y la interfaz llama **de forma bloqueante con tiempo límite corto**, sin hilos trabajadores
(D-024).

**Superficie que cruza la red: 13 operaciones.** Catálogo 7, venta 1, acceso 2, reportes 3. El
`Carrito` es puro, vive en memoria en la caja y solo se serializa entero al cobrar.

### Arreglos previos, útiles con o sin red

- [x] **Envolver en `services/` las llamadas que la interfaz hacía al repositorio.** `login_dialog`
      llamaba a `repo_usuarios.listar` y `reportes_view` a tres funciones de `repo_ventas`. Ahora
      pasan por `auth.listar_usuarios` y por el nuevo `services/reportes.py`. *(2026-09-14)*
- [x] **Eliminar el N+1 del informe del día.** Pedía las líneas de cada venta dentro del bucle: una
      ida y vuelta por venta. Ahora `reportes.ventas_del_dia` las trae en dos consultas, mediante
      `repo_ventas.lineas_de_varias`. *(2026-09-14)*
- [x] **Hacer `cerrar_venta` idempotente.** Migración 3: `venta.intento_id` con índice único. La
      caja genera un identificador al cobrar y lo reutiliza si reintenta; el servidor devuelve la
      venta original en lugar de crear otra. Las ventas antiguas quedan en NULL y la migración no
      reescribe ni una fila. *(2026-09-14)*

### La fase propiamente dicha

- [x] `Sesion` en `red/sesion.py`, con `SesionLocal` y `SesionRemota`. `ui/` ya no importa
      `sqlite3` en ningún sitio. *(2026-09-14)*
- [x] Servidor en `red/servidor.py`: HTTP + JSON, expone las 12 operaciones de `services/`, atiende
      de una en una. *(2026-09-14)*
- [x] Autenticación por PIN validada en el servidor *(2026-09-14)*
- [x] Comprobación de versión de esquema y de protocolo al conectar *(2026-09-14)*
- [x] Tiempo límite en todas las llamadas (`TIEMPO_LIMITE_RED_S = 1.5`) y `esta_conectada()` para
      el indicador *(2026-09-14)*
- [x] Modo configurable en `red.json`, editable con el Bloc de notas, sin reinstalar *(2026-09-14)*
- [x] Pruebas de dos cajas concurrentes: dos cobros simultáneos sobre el mismo stock, 10 cobros
      concurrentes sin repetir folio, reintento idempotente por red, caída del servidor
      *(2026-09-14, ejecutadas a mano — ver abajo)*
- [ ] **Indicador de conexión en la ventana**, que use `sesion.esta_conectada()`. Es lo único de la
      condición 2 de D-015 que falta: el tiempo límite ya está, pero el cajero todavía no ve el
      estado hasta que una operación falla.
- [ ] **Llevar las pruebas manuales a `tests/`** como pruebas de pytest, y añadirlas a la suite.
      *(2026-09-24: ya existe `tests/test_red.py`, con un servidor real, para las operaciones de
      usuarios de la fase 15. Las de concurrencia siguen siendo manuales.)*
- [x] **Probar en los dos PC reales.** Instalado y funcionando en la tienda desde el 2026-09-15:
      dos equipos unidos por cable directo, catálogo único, verificado incluido el reinicio de
      ambos. Ver `docs/DESPLIEGUE-TIENDA.md`.
- [x] Desactivar la carga de datos demo en instalaciones reales *(2026-09-24, D-032: ahora solo
      con `--demo`, y `--verificar` tampoco siembra ya nada)*
      (`abrir_base_datos(con_datos_demo=False)`). En la tienda los 65 productos de ejemplo se
      mezclaron con el catálogo real y hubo que separarlos a mano.

**Criterio de aceptación:** dos cajas cobrando el mismo producto a la vez no descuadran el stock ni
repiten folio; desenchufar el cable de red durante una venta muestra un aviso claro en menos de 3
segundos y no pierde el carrito; la caja principal sigue vendiendo aunque la secundaria esté
apagada.

---

## Fase 14 — Instalador (D-020)

- [ ] `.iss` de Inno Setup con selección de modo: servidor y caja, o caja secundaria
- [ ] Dirección del servidor pedida en el modo caja secundaria
- [ ] Regla de cortafuegos en el modo servidor
- [ ] Desinstalación que **no borra** `%LOCALAPPDATA%\TiendaPOS\` y avisa dónde quedaron los datos
- [ ] Probado en un Windows limpio, en los dos modos

**Criterio de aceptación:** dos PC quedan funcionando ejecutando un instalador en cada uno y
respondiendo preguntas, sin copiar carpetas a mano ni editar archivos de configuración.

---

## Tercera etapa — lo que pidió el cliente el 2026-09-18

El 2026-09-18 el cliente pidió un usuario por empleado, un cierre diario por caja y registrar el
medio de pago. El 2026-09-23 contestó por WhatsApp: el cierre con efectivo, débito y crédito por
separado y la lista de ventas con sus productos; letra más grande, color y su logotipo. No contestó
claro si quiere cuadrar el efectivo del cajón. Ver 3.1 en `CLAUDE.md`.

Boleta electrónica, impresoras y cajón de dinero **quedan fuera**: es otro proyecto, explicado en
`docs/BOLETA-ELECTRONICA-SII.md`. Las preguntas pendientes están en
`docs/PREGUNTAS-CIERRE-Y-USUARIOS.md`.

| Fase | Qué | Estado |
|---|---|---|
| — | Rojo y logotipo de la marca (D-030) · tamaño de letra ajustable (D-031) | ✅ 2026-09-24 |
| 15 | Usuarios por empleado y sesión obligatoria (D-032) | ✅ 2026-09-24 |
| 16 | Identidad de caja (D-033) | ✅ 2026-09-24 |
| 17 | Medio de pago: efectivo, débito y crédito (D-034) | ✅ 2026-09-24 |
| 18 | Informe de cierre diario por caja (D-035) | ✅ 2026-09-24 |
| 19 | Arqueo de caja, siempre activo (D-036) | ✅ 2026-09-24 |
| 20 | Documentación y manual | manual hecho; faltan guion y README |
| 21 | Venta por peso (D-037) | ✅ 2026-09-25 |
| 22 | Errores encontrados antes de la visita | ✅ 2026-09-25 |
| 23 | La caja principal se congelaba en la tienda | ✅ 2026-09-26 |
| 24 | Los cajeros pueden crear productos (D-038) | **siguiente** |

### Cómo retomar (estado al 2026-10-10)

**Dónde está todo:** rama `diseño`, todo subido a GitHub. `main` tiene hasta la fase 22 (PR #10,
fusionado); la fase 23 está en el **PR #11**, abierto. **720 pruebas en verde.** Esquema de la base
en la **versión 7**, protocolo entre cajas en la **9**.

**La tienda está en producción con esta versión** desde la visita del **2026-09-26**: los dos PC
actualizados, usuarios por empleado creados con el dueño, cierre por caja, arqueo y venta por peso.
Ese día la caja principal se congelaba al moverse entre pantallas; se arregló en el momento (fase
23) y el dueño confirmó que ya no pasa. El detalle de la instalación está en
`docs/DESPLIEGUE-TIENDA.md`, secciones 1 y 11.

**El cliente pagó** el trabajo de esta etapa (comprobante de transferencia recibido por WhatsApp
el 2026-10-01; Santiago debe confirmar que llegó a su cuenta). El manual en PDF se le entregó por
WhatsApp. Lo acordado en septiembre sigue: un mes de marcha blanca para fallas, y lo nuevo se
cotiza aparte.

**Las fases 24 y 25 están construidas** (más abajo): cualquier empleado administra los productos
sin PIN (D-038); y, pedido en la tienda el 2026-10-10, un campo para buscar por nombre al lado del
código y la ventana del vuelto en efectivo (D-039). Se llevan con `ACTUALIZAR-ESTE-PC.bat` **en los
dos PC a la vez** (protocolo 9; la base no se toca).

**Cómo se trabaja con la tienda:**

- Para depurar, lo primero es el registro del PC 1, `%LOCALAPPDATA%\TiendaPOS\logs\tienda_pos.log`:
  fue lo que resolvió el congelamiento.
- El catálogo real tiene **unos 2.000 productos**. Toda pantalla nueva se prueba con un catálogo de
  ese tamaño y entrando más de una vez (`tablas.rellenar` para volver a llenar tablas).
- El kit del pendrive está en `E:\PUNTO-Y-FAMA` (la carpeta `INSTALACION\` más
  `dist\PuntoYFamaCaja\`). Tras copiarlo, se compara archivo por archivo.

**Pendiente del cliente** (detalle en `docs/PREGUNTAS-CIERRE-Y-USUARIOS.md`):

- H1d: quién cuenta al cerrar y qué hacen si no cuadra. Mientras tanto, la diferencia se anota y
  no bloquea nada.
- H3 (otros medios, fiado), H11 (anular ventas), H9, H4 (quién ve el cierre), H5 (imprimirlo).
  *El vuelto lo pidió el 2026-10-10 (D-039).*
- ¿Se marcan bien débito y crédito tras dos semanas de uso? Si no, se funden en "tarjeta".
- La boleta electrónica, que es otro proyecto (`docs/BOLETA-ELECTRONICA-SII.md`).

**Pendiente de Santiago:** fusionar el PR #11; confirmar el pago; cerrar la fase 20 (faltan
`GUION-DEMO.md` y `README.md`).

**Mejoras anotadas, sin pedir:** que el programa se niegue a abrirse dos veces en el mismo PC (hoy
solo avisa de que el puerto está ocupado); soltar también las ventanas de Productos, Descuento,
Efectivo, Usuarios y Configuración, que siguen sin destruirse al cerrar (fase 25: son de uso
ocasional, y leen sus campos después de cerrarse, así que cada una pide su cambio y su prueba); la trazabilidad del stock (fase 9, D-018), que hace más
falta ahora que cualquier cajero cambia precios y stock.

---

## Fase 15 — Usuarios por empleado y sesión obligatoria (D-032) ✅

Absorbe la fase 12.

- [x] Pantalla de usuarios: alta, PIN nuevo, dar de baja, reactivar; desde las dos cajas
- [x] El PIN lo genera el sistema y se enseña una sola vez; nunca sale `1111` ni `1234`
- [x] No darse de baja a uno mismo ni al último administrador; reactivar a quien vuelve
- [x] Nunca se entra sin usuario: primer administrador en una base vacía; cobrar sin usuario se niega
- [x] `--demo` para demostraciones; sin él, una base vacía no se llena con datos de ejemplo
- [x] `--reiniciar-admin` para rescatar al administrador, solo en el PC de la base
- [x] Protocolo entre cajas a la versión 2
- [x] Nombre de usuario repetido: error legible en lugar del de SQLite
- [ ] **En la tienda:** nuevo PIN para `Administrador` y baja de `Cajero` (`DESPLIEGUE-TIENDA.md`)

**Criterio de aceptación:** no existe forma de llegar a la pantalla de venta sin usuario
identificado, ningún PIN publicado en la documentación sirve en una instalación nueva, y un
administrador que olvida su PIN puede recuperar la tienda sin llamar a nadie. **Cumplido**, salvo
la tienda ya instalada, que conserva los PIN de fábrica hasta la visita.

---

## Fase 16 — Identidad de caja (D-033) ✅

- [x] Migración 4: `venta.caja`, texto; las ventas anteriores quedan sin caja
- [x] El nombre sale de `red.json` (`nombre_caja`) o, sin él, del nombre del PC; nunca del modo
- [x] Viaja en la petición y el servidor usa ese: probado contra un servidor real
- [x] Siempre a la vista en la ficha del usuario; protocolo a la versión 3
- [ ] **En la tienda:** escribir `nombre_caja` en el `red.json` de cada PC (pregunta H8)

**Criterio de aceptación:** una venta hecha en la caja secundaria queda registrada como de la
caja secundaria, aunque la haya escrito el servidor. **Cumplido.**

Cada venta guarda en qué caja se hizo. Hoy no lo sabe nadie: `red.json` no tiene nombre de caja.
El dato **viaja en la petición** de la secundaria: si el servidor pusiera el suyo, todas las ventas
de la caja 2 saldrían como de la 1. Las ventas anteriores quedan sin caja, no se inventa.
Migración de esquema. Pendiente de la pregunta H8: cómo se llaman las cajas.

## Fase 17 — Medio de pago (D-034) ✅

- [x] Migración 5: `venta.medio_pago`, sin `CHECK`; las ventas anteriores, sin registrar
- [x] Tres botones sobre el de cobrar y F11 que los recorre; vuelve a efectivo tras cada venta
- [x] Un color por medio, el mismo en el cobro y en las ventas del día; efectivo sin color
- [x] Columna "Medio" en las ventas del día; protocolo a la versión 4
- [ ] **Con el cliente, a las dos semanas:** ¿se marcan bien débito y crédito?

**Criterio de aceptación:** el cajero registra una venta con tarjeta sin tocar el ratón. **Cumplido.**

Efectivo, débito y crédito, separados como pidió el cliente. Lo marca el cajero con una tecla que
cicla, siempre visible y sin estorbar el cobro con F12. Vuelve a efectivo tras cada venta.
Modifica D-006. Revisar con el cliente a las dos semanas si débito y crédito se marcan bien.

## Fase 18 — Informe de cierre diario por caja (D-035) ✅

- [x] `CierreCaja` en el dominio, con los totales por medio y por empleado **derivados de la lista
      de ventas**: suma por medio = suma por empleado = total por construcción, y por la red viaja
      una sola cosa
- [x] El día de la tienda es un rango con hora de corte (`config.HORA_CORTE_DIA`, pregunta H10),
      leída en cada llamada. **Las ventas del día usan el mismo rango y el mismo "hoy"**
      (`reportes.dia_comercial`, ya no `date.today()`)
- [x] `del_dia_de_caja` —con `caja IS ?`, que sirve para el grupo sin caja— y `cajas_del_dia`;
      operación `cierre_de_caja` por la red. **Protocolo a la versión 5**
- [x] Pruebas del backend (`tests/test_cierre.py`, 32): caja sin ventas, dos cajas el mismo día,
      ventas sin caja y sin usuario, **dos empleados en la misma caja**, anuladas fuera, las tres
      sumas cuadran en un día revuelto, bordes del día con corte 0 y con corte 6, `dia_comercial`,
      ida y vuelta por el protocolo y, contra un servidor real, la secundaria pidiendo el cierre
      de la principal
- [x] Pantalla conectada: entrada "Cierre de caja" en la barra lateral (sin tecla), cabecera que
      dice caja, día y ventas, y un botón **"Cierre de caja"** en las ventas del día. Solo
      administrador
- [x] Pruebas de la pantalla (`tests/test_ui_cierre.py`, 33)
- [x] Mirada renderizada a 1600×1000, a 1366×768 y a 1080×680, con letra normal y "Muy grande",
      en los dos temas. Captura `docs/img/14-cierre.png`
- [x] D-035, `CLAUDE.md` y `TECNICA.md` al día. **El manual, en la fase 20**

**Criterio de aceptación:** el dueño ve, en una pantalla, cuánto se vendió en esa caja en efectivo,
en débito y en crédito, qué empleado vendió cuánto, y los productos de cada venta. **Cumplido.**

Cambios respecto a lo planificado, todos menores y reversibles:

- **Icono propio, `registradora`**, en vez de `caja`: ese es una caja de cartón, el stock, y al lado
  de "Cierre de caja" se leía como el inventario.
- **"Ver productos" va junto al título de la lista de ventas**, con el botón sin marco de las
  cabeceras, y no en la fila del día y la caja: allí, a 1080 de ancho, el texto salía cortado.
- **Si el cierre no carga** (por ejemplo, la otra caja sin red), la pantalla se vacía y lo dice, en
  vez de dejar las cifras de la vez anterior debajo del día nuevo.
- El árbol de ventas dibuja él mismo la columna de la flecha: con la hoja de estilos, el filete
  entre filas se cortaba antes de la flecha, y darle estilo a esa columna hace que Qt no la dibuje.

Arreglos de paso, fuera de la pantalla: el carril de las barras de desplazamiento salía rayado en
el tema oscuro, en cualquier lista larga (`estilos.py`); las entradas de la barra lateral sin
tecla decían "()" al pasar el ratón; `tools/capturas.py` fallaba con una carpeta de destino fuera
del proyecto, y ahora hace las capturas en una caja con nombre, como las de verdad.

**Límite conocido:** por debajo de unos 1300 de ancho los nombres de empleado se abrevian ("Marta
…"). El nombre entero sale al pasar el ratón, y plegar la barra lateral (Ctrl+B) devuelve sitio.
A 1366×768 cabe todo, también con "Muy grande". Se suma a comprobar la resolución de los PC en la
visita a la tienda.

## Fase 19 — Arqueo de caja, siempre activo (D-036) ✅

*Rehecha el 2026-09-24.* El cliente aclaró por WhatsApp que **anota todos los retiros**, que saca
plata seguido de cada caja (ej. $150.000 de la caja dos) y paga en efectivo a algunos proveedores
desde la caja, y que quiere hacerlo en el sistema para tener cifras exactas. Con eso el arqueo es
requisito suyo, y **Santiago quita el interruptor**: si existiera, un cajero podría apagarlo.

Lo que se deja de hacer respecto al diseño del 2026-09-23: el interruptor en `meta`, su pantalla
en F9, el "hueco sin declarar" al reactivarlo y probar los dos caminos.

Diseño:

- **Turno de caja**: se abre con el efectivo que hay en el cajón y se cierra contándolo. Es por
  caja, no por empleado: los empleados entran y salen con su clave dentro de una caja abierta. No
  depende del día —una caja abierta a las 23:00 y cerrada a la 01:00 es un solo turno—, así que
  la pregunta de la medianoche (H10) no le afecta. Una sola caja abierta a la vez por nombre de
  caja, con un índice único parcial en la base.
- **No se cobra con la caja cerrada.** Lo impide la sesión, del lado del servidor, no un botón:
  la caja secundaria tampoco puede saltárselo. Al intentarlo se ofrece abrirla ahí mismo, y al
  arrancar el programa se propone abrirla si está cerrada.
- **Cada venta guarda en qué turno se hizo** (`venta.turno_id`), y eso decide cuánto efectivo
  debería haber, sin comparar horas entre dos PC.
- **Salidas y entradas de efectivo**: *retiro* (el dueño saca plata; **solo con PIN de
  administrador**), *pago a proveedor* (lo anota el cajero, con el nombre del proveedor, y queda
  a su nombre), *ingreso* (sencillo que se agrega). Nunca se borran.
- **Debería haber** = efectivo al abrir + ventas en efectivo del turno + ingresos − retiros −
  pagos. **El vuelto no entra**: sale del mismo cajón y el neto es el total de la venta.
- **Conteo a ciegas** (aprobado por Santiago): quien
  cierra escribe lo que contó sin ver cuánto debería haber. El esperado y la diferencia los ve
  solo el administrador, y el servidor ni siquiera se los manda a un cajero. Al cerrar se guarda
  el esperado de ese momento, lo contado, la diferencia, quién y una nota opcional. No bloquea
  nada (H1d sin respuesta).
- **Monto sugerido de apertura**, en `meta`, lo fija el administrador. Se propone al abrir; quien
  abre escribe lo que de verdad hay.
- Pantalla **Efectivo**, en la sección CAJA de la barra lateral, para cualquier empleado: estado
  de la caja, las salidas y entradas del turno, y los botones. El administrador ve además la
  cuenta del esperado y los cierres anteriores con su diferencia.
- Por la red viaja todo con identificador de intento, como el cobro (D-024): un reintento no
  anota dos veces un retiro.

- [x] Migración 6: `turno_caja` (con índice único parcial: una caja abierta por nombre),
      `movimiento_efectivo` y `venta.turno_id`. **Esquema a la versión 6**
- [x] Dominio (`TurnoCaja`, `MovimientoEfectivo`, `TipoMovimiento`), `repositories/arqueo.py` y
      `services/arqueo.py` con sus reglas; error nuevo `CajaCerrada`
- [x] La venta toma el turno abierto de su caja dentro de su transacción; `SesionLocal` —que es
      también el servidor— no cobra con la caja cerrada
- [x] Siete operaciones nuevas (26 en total), **protocolo a la versión 6**
- [x] Pantalla **Efectivo** en la sección CAJA, diálogo de montos, apertura al cobrar y al arrancar
- [x] Pruebas: `tests/test_arqueo.py` (64, servicio y red contra un servidor real) y
      `tests/test_ui_efectivo.py` (25). La ventana de las pruebas trabaja ahora en "Caja 1", abierta
- [x] Mirada a 1600×1000, 1366×768 y 1080×680, normal y "Muy grande", en los dos temas.
      Captura `docs/img/15-efectivo.png`. `DESPLIEGUE-TIENDA.md` con los pasos de la visita

**Criterio de aceptación:** al cerrar una caja, el administrador ve cuánto debería haber en el
cajón —con los retiros y pagos del día descontados— y cuánto se contó, y ningún cajero puede
anotar un retiro, cobrar con la caja sin abrir ni apagar el arqueo. **Cumplido.**

Notas de la construcción:

- **"Debería haber" va en el color del texto, no en el verde de los totales**: no es algo que
  "salió bien". En negativo va en rojo: en un cajón es imposible, y señala una salida mal anotada.
- **La cuenta se enseña como en un cuaderno**: una tarjeta con los cuatro renglones y otra con el
  resultado. Cinco tarjetas en fila no cabían a 1080 con la letra más grande.
- Una fuga encontrada por las pruebas: la pantalla guardaba un método de la ventana y eso hacía un
  ciclo que impedía liberarla al cerrarla; cada cambio de tema tardaba más que el anterior. Va por
  referencia débil.
- `tools/capturas.py` abre las dos cajas al empezar: si no, el primer cobro esperaría un clic.

**Límite conocido:** a 1080×680 con "Muy grande", las dos tablas quedan con una fila visible cada
una (se desplazan). Falta alto, no ancho; a 1366×768 se ve todo.

**Conteo a ciegas aprobado por Santiago** el 2026-09-24 (D-036, punto 7). Si algún día se quiere
quitar, basta con devolver el esperado a cualquier usuario en `services/arqueo.py::_visible_para`.

## Fase 20 — Documentación y manual · manual hecho, falta el resto

**2026-09-25: el manual está hecho**, como PDF para entregar al cliente:
`docs/Manual-de-usuario-Punto-y-Fama.pdf`, generado desde `docs/manual/manual.html` con
`python tools/manual_pdf.py`, con las capturas regeneradas ese día. Cubre todo lo de abajo
salvo la nota de los nombres de caja, que es de instalación y está en `LEEME-PRIMERO.txt`. Ya no
publica ningún PIN. `MANUAL-USUARIO.md` queda como puntero al PDF. **Falta:** `GUION-DEMO.md`
(arrancar con `--demo`) y `README.md`.

Lo que se pedía, para contrastar:

Decidido: **un solo manual**, el que ya existe, **escrito al final** con todo hecho. Lo que hay que
tocar en `docs/MANUAL-USUARIO.md`:

- Sección 1: publica `1111` y `1234`. Sacarlos a un recuadro "solo para la demostración (`--demo`)".
- Sección 12: dice "No permite crear usuarios ni cambiar los PIN", que ya es falso.
- Vender: el medio de pago y F11. Atajos: F11.
- Apartados nuevos: Usuarios (alta, PIN que se enseña una vez, PIN nuevo, baja y reactivar, que la
  baja no borra sus ventas); Cierre del día (qué es cada número, y que no cierra nada); el tamaño de
  letra en F9.
- Nota: cada caja firma con su nombre, y dos nombres iguales mezclan el cierre.

También: `docs/GUION-DEMO.md` (arrancar con `--demo`), `README.md`, y revisar que las capturas de
`docs/img/` estén al día.

---

## Fase 21 — Venta por peso (D-037) ✅

*2026-09-25.* Pedida por el cliente: pan, pollo y jamón a precio por kilo, con los gramos
tecleados en la caja.

- [x] Migración 7: `producto.por_peso` y `venta_linea.gramos`. **Esquema a la versión 7**
- [x] Precio al peso más cercano, en enteros; tope de 50 kg por línea
- [x] Carrito: pedir gramos, sumar al reescanear, volver a pesar, quitar; viaja por la red
- [x] Cobro: el servidor decide si es por peso; stock en gramos que no impide vender
- [x] Código interno para productos sin código (`2000001`...)
- [x] **Protocolo a la versión 7**
- [x] Pantallas: ventana del peso con el precio en vivo, líneas con "350 g" y "$7.990/kg",
      formulario de producto con "Se vende por peso", consulta, búsqueda e informes
- [x] "Cierre de caja" pasa a "Ventas por caja" (Santiago)
- [x] Pruebas: 53 nuevas; migración de una base de la tienda de la versión 3 a la 7
- [x] Capturas 16 a 18 y sección 6 del manual

**Criterio de aceptación:** el pan sin código se vende buscándolo por nombre y tecleando los
gramos, el jamón escaneado igual, el precio es exacto al peso, y todo lo que se vendía por unidad
sigue igual. **Cumplido.** Queda por ver en la tienda cómo pesan hoy: si la balanza imprime
etiquetas con código, leerlas es un paso más (D-037, punto 9).

---

## Fase 22 — Errores encontrados antes de la visita (2026-09-25)

Revisión completa del código la víspera de instalar en la tienda. Las 641 pruebas estaban en verde
y la migración de una base como la de la tienda (versión 3) a la 7 recorre todas las pantallas sin
fallos; lo que sigue lo encontró la lectura del código y se reprodujo con un script antes de
tocarlo.

**Graves: alteran datos sin avisar.**

- [x] **1. En la caja 2 se puede perder una venta entera.** Si un cobro agota el tiempo límite
      pero el servidor sí lo registró, y el cajero cancela la venta (F6) o cambia de usuario, el
      identificador del intento de cobro (D-024) sigue guardado y se reutiliza con el cliente
      siguiente. El servidor lo toma por un reintento y devuelve la venta anterior: la nueva no se
      registra, el stock no baja y la pantalla anuncia el folio y el total de la anterior.
      `ui/venta_view.py`, `cancelar_venta` y `cobrar`.
      *Arreglo:* el intento se olvida al empezar una venta nueva (cobrada, cancelada o por cambio
      de usuario) y cuando el servidor contesta que no; solo se conserva tras un cobro **sin
      respuesta**, que es el único que pudo registrarse. Si en el reintento la venta registrada
      no es lo que hay en pantalla porque el carrito cambió, se avisa al cajero. Y cancelar tras
      un cobro sin respuesta avisa de que ese cobro pudo quedar registrado.
- [x] **2. Editar un producto pisa su stock con el de cuando se abrió la pantalla.** La lista de
      Productos se carga al entrar, y guardar un cambio de precio escribe también ese stock viejo:
      lo que vendieron las cajas entre medio desaparece. Si el stock ya era negativo y cambió,
      cambiar solo el precio da "El stock no puede ser negativo". `ui/productos_view.py`,
      `services/catalogo.py::actualizar_producto`.
      *Arreglo:* el formulario manda el stock solo si se tocó; sin él, el servicio conserva el de
      la base, leído dentro de la transacción. Editar y "Stock" parten del producto tal como está
      en la base al pulsarlos, no del de la lista. **Protocolo a la versión 8**: el stock puede
      viajar vacío, y un servidor de la 7 fallaría con eso.

**Medio.**

- [x] **3. El conteo a ciegas se puede saltar.** Tras "Ver las cuentas" con el PIN del dueño en el
      PC del cajero, "Debería haber" queda a la vista, y "Actualizar" lo refresca, hasta salir de
      la pantalla. Y si con las cuentas a la vista cierra la caja el cajero, al dueño no se le
      enseña la diferencia. `ui/efectivo_view.py`.
      *Arreglo:* las cuentas vistas con un PIN prestado se ocultan solas a los dos minutos, y hay
      un botón "Ocultar las cuentas" para hacerlo antes. Al administrador que opera su propia
      caja no se le ocultan. Si la cajera cierra con el dueño mirando, él ve la diferencia.
      Manual actualizado (sección de Efectivo) y PDF regenerado.

**Menores.**

- [x] 4. Ajustar stock con un stock negativo: "−1" sobre −3 salta a 0 y dice "Entran 3 unidades".
      *Arreglo:* restar ya no baja de cero ni del negativo que había; un negativo se puede subir
      hacia cero (el servicio lo acepta, precisado en D-009); Enter guarda también sobre un
      negativo; y "Entra 1 unidad" en singular.
- [x] 5. Descuento a un producto por peso: la opción dice "(1 unidad)" en vez de los gramos.
- [x] 6. El stock por unidad puede quedar negativo (D-009, hoy) pero el de peso se corta en 0; y el
      manual, al decir que el peso "nunca impide vender", da a entender que la unidad sí.
      *Arreglo:* la diferencia **se mantiene**, porque la decidió D-037 (punto 5); queda
      explicada en D-009. El manual dice ahora que la falta de stock nunca impide vender, y que
      el negativo avisa de que falta cargar mercadería.
- [x] 7. Siete respaldos, uno al abrir y otro al cerrar: cubren tres o cuatro días.
      *Arreglo:* se guardan los 7 más recientes y, además, el último de cada uno de los últimos
      30 días (`config.RESPALDOS_DIAS`).
- [x] 8. `CLAUDE.md` da D-018 como en pie ("el stock no cambia sin dejar rastro"), pero la fase 9
      no está hecha. No prometerlo en la visita. *Corregido en `CLAUDE.md`.*

---

## Fase 23 — La caja principal se congelaba en la tienda (2026-09-26)

El día de la instalación, en el PC 1: tras cambiar de un cajero a un administrador y moverse por
la barra lateral, el programa quedó en "No responde". El registro de la tienda mostró la causa:
ocho `AttributeError: '_AparicionDeVentana' object has no attribute '_anim'` seguidos, en
`ui/movimiento.py`, justo antes de que hubiera que cerrarlo.

**Causa.** El filtro que funde cada diálogo al abrirse (`_AparicionDeVentana`) solo lo sujetaba
Qt, como hijo de su ventana; desde Python no lo sujetaba nadie. Cuando el recolector de Python
limpiaba, podía vaciarle el estado mientras Qt le seguía mandando eventos, y cada evento
reventaba. El manejador global abría un aviso de error por cada uno, uno dentro de otro, y la
caja se congelaba. Depende de cuándo recolecta Python, por eso salió tras once minutos de uso y
no en las pruebas.

- [x] Los filtros de aparición quedan sujetos desde Python (`movimiento._apariciones`) y se
      sueltan al destruirse su ventana
- [x] Red de seguridad: un filtro sin estado deja pasar el evento sin fundido, en vez de fallar
- [x] El delegado del destello del carrito tenía el mismo riesgo y se sujeta en la vista
- [x] El aviso de "Ocurrió un error" no se abre dentro de otro: con uno abierto, el resto solo
      se anota en el registro
- [x] 5 pruebas nuevas, que fallan con el código anterior

**Segunda vuelta, el mismo día: seguía congelándose, también sin animaciones**, al cambiar
mucho de pantalla. La causa de verdad era otra, y solo se ve con el catálogo de la tienda
(unos 2.000 productos): **entrar por segunda vez a Productos tardaba 127 segundos**; la primera,
0,09. Al volver a llenar una tabla que ya tenía filas, con columnas en `ResizeToContents`, Qt
volvía a medir la columna entera tras cada celda reemplazada. Con los 65 productos de ejemplo
no se notaba. "Ventas del día" tenía lo mismo, en menor medida: más de 2 segundos con 150 ventas.

- [x] `tablas.rellenar`: vacía la tabla y para el dibujo antes de llenarla. Productos y Ventas
      del día pasan a unos 0,06 s por entrada, vuelta tras vuelta, con 2.000 productos y 400
      ventas. Las demás tablas tienen pocas filas y se dejan como estaban
- [x] **El programa tardaba 13 s en aparecer en el PC 1**: `HTTPServer` le pregunta al DNS el
      nombre del equipo, y en la tienda, con dirección fija y sin DNS, esperaba a que la
      consulta se agotara. Se le daba doble clic otra vez y quedaron **cuatro programas abiertos**
      a la vez. El servidor ya no pregunta
- [x] **En Windows, dos programas podían escuchar en el mismo puerto** (`SO_REUSEADDR`), así que
      el aviso de "el programa ya está abierto" nunca salía. Ahora el segundo falla al abrir el
      puerto y lo dice
- [x] 3 pruebas más, que fallan con el código anterior

---

## Fase 24 — Cualquier empleado administra los productos (D-038) ✅

*2026-10-05.* Pedida por el cliente el 2026-10-01: "Al ingresar productos al sistema lo puede hacer
cualquier usuario." La primera redacción dejaba precio, stock y bajas con PIN; **Santiago la cambió
antes de construirla: el cajero hace en Productos todo lo que hacía el administrador.** Ver D-038.

- [x] `services/auth.exigir_sesion`: basta un usuario con sesión. La usa también el arqueo, que
      tenía su propia copia
- [x] `services/catalogo.py`: crear, actualizar, dar de baja y códigos pendientes, con
      `exigir_sesion` en lugar de `exigir_admin`
- [x] F7 entra a Productos sin PIN, con el usuario de la caja; si se cambia de usuario (F10), la
      pantalla pasa al nuevo
- [x] Protocolo a la **versión 9**: no cambia ningún mensaje, pero un servidor de la 8 les negaría
      Productos a los cajeros de la secundaria
- [x] Pruebas: el cajero hace todo, en el servicio y por la red; sin sesión, nada; F7 no pide PIN.
      Las de "un cajero que cancela no entra" pasan a Usuarios, que sigue siendo del administrador
- [x] Manual (`docs/manual/manual.html`): tabla de permisos, sección 14 y F7
- [x] PDF del manual regenerado (`python tools/manual_pdf.py`)
- [ ] `.exe`, kit del pendrive comprobado archivo por archivo, y actualizar **los dos PC a la vez**
      (protocolo 9)

**Riesgo aceptado:** sin la fase 9 (D-018) no queda rastro de quién cambió un precio o un stock.

**Criterio de aceptación:** un cajero crea, edita, ajusta stock y da de baja productos sin que
nadie ponga su PIN, en cualquiera de las dos cajas; sin sesión no se puede, ni llamando al servidor
directamente. **Cumplido** en código y pruebas; falta llevarlo a la tienda.

---

## Fase 25 — Buscar por nombre al lado del código, y el vuelto en efectivo (D-039) ✅

*2026-10-10.* Pedidas por el cliente ese día, en la tienda. Ver D-039.

- [x] Campo **"Por nombre"** al lado del código: la lista sale al escribir, con el primero
      marcado; flechas y Enter. F3 lleva ahí. El foco vuelve al código después de agregar
- [x] Un código escrito o escaneado en el campo del nombre se agrega como código
- [x] **Error encontrado al construirla:** con un solo resultado, el Enter de la lista llegaba
      también al campo y el producto entraba dos veces. Arreglado y con prueba
- [x] `services/venta.calcular_vuelto`: pago justo, no alcanza ("Faltan $500"), montos absurdos
- [x] **Ventana del vuelto** en efectivo, en lugar de la confirmación: Enter vacío es pago justo,
      no deja cobrar si no alcanza, pide revisar un vuelto de $20.000 o más. Al reintentar un
      cobro fallido, trae escrito el monto. El aviso dice el vuelto durante 30 s
- [x] Textos de ayuda de los dos campos medidos para que quepan a 1280 px con letra muy grande
- [x] **Ventanas que no se destruían.** Al revisar las capturas salió que cada ventana abierta con
      `.pedir()` —peso, y ahora vuelto— quedaba viva y oculta hasta cerrar el programa, con su
      fundido enganchado. Con el vuelto serían cientos por caja y por día. `dialogos.ejecutar_y_soltar`
      las destruye al cerrar: vuelto, peso, confirmar, avisos y código no encontrado. Con prueba
- [x] Pruebas (`tests/test_ui_nombre_y_vuelto.py`), con teclas de verdad para el Enter
- [x] Manual: secciones 5, 6, 7, 8, 15 y teclas; capturas y PDF regenerados (mismas 19 páginas)
- [x] `.exe` y kit del pendrive (`E:\PUNTO-Y-FAMA`), comprobado archivo por archivo (2026-10-10)
- [ ] Instalar en los dos PC con `ACTUALIZAR-ESTE-PC.bat`

**Sin cambios de base ni de protocolo:** el monto recibido no se guarda.

**Criterio de aceptación:** el pan se agrega escribiendo "pan" y Enter, sin abrir ventanas; en
efectivo se ve el vuelto antes de cobrar; con tarjeta no cambia nada. **Cumplido** en código y
pruebas.

---

## Decisiones pendientes

Resueltas en esta etapa: **instalador** → D-020 · **segunda caja** → D-015 · **trazabilidad de
inventario** → D-018.

Siguen abiertas:

- [ ] **Arranque automático al encender el PC.** Recomendación: **no** por defecto. Secuestra el
      equipo, complica las actualizaciones y estorba si el PC se usa para otra cosa. Se deja acceso
      directo en el escritorio; si el cliente insiste, se activa en un minuto. *Matiz nuevo:* en el
      PC servidor sí tiene sentido que el servicio arranque solo, porque si no, la segunda caja
      depende de que alguien abra el programa en el primero.
- [ ] **Impresora de tickets.** Fuera del alcance hasta saber si el cliente tiene una.
- [ ] **Respaldo en dispositivo externo.** Depende de cuán críticos considere sus datos. Con dos
      PC gana peso: todo vive en uno solo de los dos.
- [ ] **Firma de código** (D-021). Tiene coste anual y es decisión de Santiago.
- [ ] **PC servidor dedicado.** Si la caja principal hace de servidor, apagarla deja muda a la
      segunda. Un mini-PC lo resuelve, pero es un coste del cliente. Con D-015 es un cambio de
      configuración, no de código.
- [ ] **Boleta electrónica ante el SII.** No está pedida y D-006 la excluye deliberadamente. Se
      anota aquí porque LocalShop la tiene y el cliente lo nombró: si resulta que era eso lo que le
      gustaba, hay que decir claramente que es otro proyecto, con certificado digital y
      responsabilidad tributaria.

---

## Sugerencias propuestas, no confirmadas

1. **Modo de carga rápida por teclado** para el peor caso del rescate: pistola → nombre → precio de
   venta → stock → Enter, sin tocar el ratón. Unas 2 horas para 300 productos entre dos personas.
   *Recomendada:* es el seguro de vida de la fase 8, y con dos campos menos por producto que antes
   del 2026-09-14 es aún más rápida.
2. **Toma de inventario físico** asistida: recorrer la tienda escaneando y anotando la cantidad
   real, y que el sistema genere los movimientos de ajuste. Va a hacer falta al menos una vez,
   porque las cantidades importadas estarán desfasadas. *Recomendada.*
3. **Catálogo demo con productos reales del cliente.** Sigue sin hacerse, y ahora es casi gratis: en
   cuanto haya CSV de importación, cargar veinte de sus productos cambia la reunión.
4. ~~**Sugerencia de precio de venta** a partir del costo y un margen objetivo.~~ *Descartada el
   2026-09-14:* dependía del precio de compra, que el cliente retiró (D-017).
