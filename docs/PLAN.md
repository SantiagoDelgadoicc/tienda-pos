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
| 19 | Modo arqueo, activable | pendiente |
| 20 | Documentación y manual | pendiente |

### Cómo retomar (estado al 2026-09-24)

**Dónde está todo:** rama `diseño`. 494 pruebas en verde. Esquema de la base en la versión 5 y
protocolo entre cajas en la 5. El `.exe` del escritorio está construido en la fase 15: hay que
reconstruirlo (`python tools/construir.py`) para ver las fases 16 a 18.

**Lo siguiente es la fase 19**, el modo arqueo. Antes de construirla hay que cerrar lo que el
cliente no ha contestado del dinero del cajón (abajo, y en la propia fase): cambia las tablas de
la migración 6. Después, la 20.

**Pendiente del cliente** (detalle en `docs/PREGUNTAS-CIERRE-Y-USUARIOS.md`):

- **H10, la medianoche.** Si venden pasada la medianoche, ¿de qué día son esas ventas? Responderla
  es cambiar `config.HORA_CORTE_DIA`. Es la que puede salir cara si se olvida.
- **H8, cómo se llaman las cajas.** Se escribe en `red.json` de cada PC el día de la visita.
- Si los retiros "se anotan" (sí) o "si se anotan" (condicional), y los detalles del arqueo (H1c,
  H1d): condicionan la fase 19.
- H3 (otros medios, fiado), H11 (anular ventas), H9, H4 (quién ve el cierre), H5 (imprimirlo),
  D1 (quién cambia precios), y si quiere que se calcule el vuelto.
- A las dos semanas de uso: ¿se marcan bien débito y crédito? Si no, se funden en "tarjeta".

**Pendiente en la tienda** (una sola visita, con las dos cajas paradas; procedimiento en
`docs/DESPLIEGUE-TIENDA.md`, "Actualizar a la versión con un usuario por empleado"): actualizar los
dos PC a la vez, crear los usuarios de los empleados, PIN nuevo para `Administrador`, baja de
`Cajero`, `nombre_caja` distinto en el `red.json` de cada PC, y comprobar la resolución de pantalla
de los equipos (D-031: todo el margen del carrito se midió a 1600 de ancho).

**Pendiente de Santiago:** abrir el PR de `diseño` a `main` (`gh` no está autenticado en este
equipo), y la boleta electrónica, que es otro proyecto y espera a que el cliente conteste qué hace
hoy con sus boletas (`docs/BOLETA-ELECTRONICA-SII.md`).


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

## Fase 19 — Modo arqueo, activable · pendiente

El dinero del cajón **detrás de un interruptor**, porque el cliente no contestó claro si quiere
cuadrar el efectivo (dijo que cuentan la plata en un cuaderno, y que "si se anotan todos los retiros
en efectivo", que puede ser un sí o un condicional). Decidido por Santiago el 2026-09-23.

**El interruptor no ahorra trabajo, lo aumenta:** hay que construir el arqueo entero igual, más el
modo, más probar y documentar los dos caminos.

- **Desactivado** (por defecto): el cierre es el de la fase 18, sin nada del cajón.
- **Activado**: apertura con fondo inicial, conteo al cerrar, diferencia, registro guardado de
  quién cerró, y **pantalla de entradas y salidas de efectivo** (retiros para pagar a un
  proveedor, sencillo que se agrega). Sin esa pantalla el arqueo muestra diferencia todos los días
  y se deja de mirar a las dos semanas.

Diseño ya pensado:

- **El interruptor va en la tabla `meta`, no en `preferencias.json`.** Es configuración del
  negocio y arrastra datos que comparten las dos cajas; si una lo tuviera activado y la otra no, los
  datos quedarían a medias. `meta` ya existe y no necesita migración. Solo administrador, con
  confirmación, en la pantalla F9.
- **Activarlo exige un punto de partida**: abre directamente la apertura de caja (cuánto efectivo
  hay ahora). **Desactivarlo no borra nada**; si se reactiva, el informe tiene que decir que hubo un
  hueco sin declarar, en vez de fingir continuidad.
- Tablas nuevas (migración 6): aperturas/cierres de caja con fondo, conteo, diferencia, quién y
  cuándo; y movimientos de efectivo con monto, motivo, quién y caja.
- El efectivo esperado = fondo inicial + ventas en efectivo − retiros + ingresos. **El vuelto no
  entra en la cuenta**: sale del mismo cajón y el neto es el total de la venta.
- Las dos cajas leen siempre el mismo valor del interruptor, servido por el servidor.

Pendiente del cliente: quién cuenta el dinero y qué se hace hoy si no cuadra (H1d); si el fondo
inicial es fijo o se arrastra (H1c); si cada caja se cuenta por separado.

## Fase 20 — Documentación y manual · pendiente

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
