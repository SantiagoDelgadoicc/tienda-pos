# Documentación técnica

Para quien vaya a mantener o continuar este código. El *porqué* de las decisiones está en
[DECISIONES.md](DECISIONES.md); las reglas de trabajo, en [../CLAUDE.md](../CLAUDE.md).

---

## 1. Qué es

Aplicación de escritorio para Windows: punto de venta monopuesto, sin red y sin internet.
Python 3.11 + PySide6 (Qt 6) + SQLite, empaquetada con PyInstaller.

## 2. Poner en marcha el entorno

```bash
git clone https://github.com/SantiagoDelgadoicc/tienda-pos.git
cd tienda-pos
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
```

Ejecutar:

```bash
python main.py
```

`python -m tienda_pos` también funciona si el paquete está instalado (`pip install -e .`).

## 3. Pruebas

```bash
pytest
```

369 pruebas, alrededor de un minuto. No necesitan pantalla: las de interfaz usan la plataforma
`offscreen` de Qt, que `tests/conftest.py` activa automáticamente.

```bash
pytest --cov=tienda_pos --cov-report=term-missing   # con cobertura
pytest tests/test_venta.py -v                       # un archivo
pytest -k descuento                                 # por nombre
```

Los archivos de prueba, y qué cubre cada uno:

| Archivo | Cubre |
|---|---|
| `test_utils.py` | Formato de dinero y códigos de barras |
| `test_db.py` | Esquema, migraciones, transacciones, datos de ejemplo |
| `test_catalogo.py` | Búsqueda por código y por nombre, permisos, alta y baja |
| `test_venta.py` | Carrito, descuentos de venta y de producto, cierre transaccional |
| `test_auth.py` | PIN, hash con sal, permisos |
| `test_ui.py` | Pantalla de venta y de consulta, teclado y celdas de acción |
| `test_ui_admin.py` | Descuento, catálogo, informes, autorización |
| `test_preferencias.py` | Archivo de preferencias y paletas de los temas |
| `test_ui_configuracion.py` | Rueda de configuración y cambio de tema en caliente |
| `test_robustez.py` | Respaldos, registro, errores, detección de lector |
| `test_rendimiento.py` | Búsqueda con 5.000 productos y uso del índice |

## 4. Estructura

```
main.py                     punto de entrada (y --verificar, --demo, --reiniciar-admin)
src/tienda_pos/
  app.py                    arranque: log, errores, respaldo, base, sesión, ventana
  config.py                 rutas de datos y constantes
  db/
    schema.sql              esquema
    connection.py           conexión y transacciones
    migrations.py           versionado con PRAGMA user_version
    inicio.py               abrir_base_datos(): punto único de entrada
    seed.py                 catálogo de ejemplo
    respaldo.py             copias automáticas
  domain/                   modelos y errores (sin dependencias)
  repositories/             acceso a datos, un módulo por entidad
  services/                 lógica de negocio (NO importa Qt)
  ui/                       todo lo que sabe de Qt
  utils/                    dinero, códigos, lector, sonido, registro
tools/                      construir, icono, capturas, acceso directo
```

**La regla que sostiene el diseño:** las dependencias van en una sola dirección,
`ui → services → repositories → db`, y `services/` no importa Qt. Por eso la lógica de
negocio se prueba sin abrir una ventana, y una interfaz distinta en el futuro (web, móvil)
podría reutilizar el núcleo entero.

## 5. Base de datos

SQLite en `%LOCALAPPDATA%\TiendaPOS\tienda.db`, en modo WAL y con `foreign_keys = ON`.

| Tabla | Contenido |
|---|---|
| `producto` | Catálogo. Baja lógica con `activo` |
| `usuario` | Nombre, rol, PIN con hash scrypt y sal propia |
| `venta` | Cabecera: folio, fecha, subtotal, descuento, total |
| `venta_linea` | Detalle, con **copia** del código, nombre y precio del momento, y el descuento de la línea |
| `codigo_no_encontrado` | Códigos escaneados que no están en el catálogo |
| `meta` | Pares clave/valor |

Dos cosas que hay que respetar al tocar esto:

- **Los importes son enteros de CLP.** Nunca `float`. Ver `utils/money.py`.
- **Las líneas de venta guardan copia del precio.** Cambiar un precio hoy no debe alterar el
  valor de las ventas de ayer.

### Migraciones

El esquema se versiona con `PRAGMA user_version`. Para publicar una versión nueva: subir
`VERSION_ESQUEMA` en `db/migrations.py` y registrar la función correspondiente en
`_MIGRACIONES`. **Nunca se edita una migración ya publicada:** puede haber bases de datos
instaladas que ya la aplicaron.

No se usa `executescript` porque hace un COMMIT implícito y rompería la atomicidad de cada
migración; el script se trocea con `sqlite3.complete_statement`.

Versiones publicadas:

| Versión | Cambio |
|---|---|
| 1 | Esquema inicial (`db/schema.sql`) |
| 2 | `venta_linea.descuento_clp`, para el descuento aplicado a un solo producto (D-012) |

## 6. Construir el ejecutable

```bash
python tools/icono.py                    # genera assets/punto_y_fama.ico
python tools/construir.py                # dist/PuntoYFamaCaja/PuntoYFamaCaja.exe
python tools/construir.py --unico        # un solo dist/PuntoYFamaCaja.exe
python tools/crear_acceso_directo.py     # acceso directo en el escritorio
```

Resultado: unos 114 MB en carpeta, arranque medido en 0,93 s.

Se distribuye en carpeta y no como archivo único porque el formato de archivo único se
descomprime en una carpeta temporal en cada arranque y añade dos o tres segundos.

**Comprobar el paquete en un equipo ajeno:**

```bash
PuntoYFamaCaja.exe --verificar
```

Arranca el sistema completo sin mostrar nada, mide el tiempo y escribe
`%LOCALAPPDATA%\TiendaPOS\autocomprobacion.txt`. Devuelve 0 si todo fue bien. **No siembra datos de
ejemplo** (desde el 2026-09-24): se ejecuta en el PC de la tienda, y sembrar ahí el catálogo de
muestra es como acabó mezclado con el real.

**Las otras dos opciones del ejecutable** (D-032):

| Opción | Para qué | Dónde |
|---|---|---|
| `--demo` | En una base **vacía**, carga los 65 productos y los dos usuarios de ejemplo, con los PIN publicados en el manual. Sobre una base con datos no hace nada. | Solo en el equipo de demostraciones. **Nunca en un acceso directo de la tienda.** |
| `--reiniciar-admin` | Recupera un administrador cuando nadie recuerda el PIN: pide el nombre, le genera un PIN nuevo (lo crea si no existe) y lo enseña. Respaldo previo y constancia en el registro, sin el PIN. | Solo en el PC que guarda la base. En la caja secundaria se niega. |

Sin `--demo`, una instalación nueva arranca vacía y pide crear al administrador: **nunca se entra
sin usuario**. `--reiniciar-admin` funciona con diálogos y no por consola porque el ejecutable se
construye sin ella.

**Protocolo entre cajas.** Versión 1, dos cajas (fase 13) · 2, administración de usuarios
(fase 15) · 3, cada venta dice de qué caja viene (fase 16) · **4**, y con qué se pagó
(fase 17). **Esquema de la base: 5** (`venta.caja`, `venta.medio_pago`). Sube también cuando solo se añaden operaciones: así una actualización a medias
se detecta al arrancar y no en mitad de una pantalla. Hay que actualizar las dos cajas a la vez.

**Antivirus:** algunos marcan como sospechosos los ejecutables de PyInstaller. Conviene
probarlo en el equipo del cliente antes de la demostración.

## 7. Otras herramientas

```bash
python tools/capturas.py     # regenera docs/img/*.png
```

En Windows usa la plataforma nativa de Qt a propósito: con `offscreen` no se cargan las
fuentes del sistema y todo el texto sale como cajas vacías.

## 8. Detalles que conviene conocer antes de tocar la interfaz

- **El foco vive en el campo de escaneo.** Toda acción termina llamando a
  `enfocar_escaneo()`. Si se pierde el foco, el siguiente disparo de la pistola se pierde.
- **Qt oculta el texto de ayuda de un `QLineEdit` centrado que tiene el foco.** Por eso la
  instrucción de la pantalla de consulta es una etiqueta aparte y no un `placeholder`.
- **Las etiquetas no pintan fondo** (`QLabel { background: transparent }` en la hoja de
  estilos). Sin esa regla, cada texto se ve como una caja gris sobre las tarjetas blancas.
- **Qt centra las cabeceras de tabla por defecto.** `ui/tablas.py` las alinea con sus datos.
- **La comprobación de permisos vive en `services/`**, no en la interfaz. Ocultar un botón no
  es control de acceso.
- **Nada de widgets dentro de una tabla que se redibuja.** Qt no destruye los que quedan en
  filas eliminadas y flotan sobre la tabla. Las acciones por fila del carrito son celdas con
  un símbolo más `cellClicked` (D-014).
- **Ningún color se escribe a mano en una pantalla.** Todos salen de `ui/estilos.py`, sea por
  la hoja de estilos o leyendo `estilos.actual`; si no, el tema oscuro no los alcanza.
- **La apariencia sigue el sistema de `docs/DESIGN.md`** (D-026): lienzo de piedra cálida,
  tarjetas blancas, filete de 1 px como recurso estructural y cinco radios —16 tarjeta, 12
  anidado y campo grande, 8 detalle, cápsula para botones y fichas—. Un tamaño o un radio
  fuera de esa escala rompe el sistema: si hace falta uno nuevo, se añade a `estilos.py` y se
  justifica, no se escribe suelto en una pantalla.
- **Dos colores y ninguno más**, cada uno con su significado y con su forma de aplicarse
  (D-027). **Rojo**: dónde estoy, dónde está el foco y lo que cancela o borra; siempre en
  lavado, filete o texto, **nunca relleno**. **Verde**: salió bien y adelante; es el único
  que va relleno. Un color nuevo, o uno de los dos usado para otra cosa, deja al cajero sin
  poder leer la pantalla de reojo.
- **El nombre del ejecutable y el de la carpeta de datos son cosas distintas.**
  `NOMBRE_EJECUTABLE` se puede cambiar; `NOMBRE_APP` no, porque es el nombre de
  `%LOCALAPPDATA%\TiendaPOS` y cambiarlo deja al programa sin su base de datos.
- **Los recursos que viajan con el programa** (el logotipo) se buscan con
  `config.directorio_recursos()`, que resuelve tanto en desarrollo como dentro del
  ejecutable empaquetado. `tools/construir.py` mete `assets/` en el paquete.
- **Las pantallas no pintan su propio título.** Lo pone la cabecera de `main_window`, a partir
  de `_CABECERAS`. Una pantalla nueva añade ahí su entrada y su clave en la barra lateral.
- **Los iconos se dibujan, no se cargan** (`ui/iconos.py`). Son mapas de píxeles ya pintados,
  así que un cambio de tema no los alcanza: quien los use tiene que repintarlos en su
  `repintar()`. Es la misma regla que ya regía para los colores fijados celda a celda.
- **No existe el `border-radius: 999px`.** Qt no recorta un radio enorme: si pasa de la
  mitad del alto del control, dibuja las esquinas **rectas**. Las cápsulas usan los tres
  radios de `estilos.py` (`RADIO_PILDORA`, `_ALTA`, `_BAJA`), todos por debajo de la mitad
  del alto del control al que se aplican. Ver D-028.
- **Las animaciones pasan por `ui/movimiento.py`** y siguen la sección «Movimiento» de
  `docs/DESIGN.md`. El estado cambia al instante y solo el dibujo se anima, así que la lógica
  no espera a nadie. Dos trampas de Qt: un widget admite **un solo** `QGraphicsEffect` (las
  tarjetas ya gastan el suyo en la sombra, así que no se les puede poner un fundido), y un
  efecto de opacidad quita el ClearType al texto, por eso `Fundido` lo enciende solo mientras
  dura la animación. Las pruebas corren con `movimiento.suprimir()`; las que miran el
  movimiento lo encienden con la fixture `con_movimiento`. Ver D-029.
- **Un aviso que se oculta solo usa un temporizador propio y reiniciable**, nunca
  `QTimer.singleShot`. Con `singleShot`, cada aviso deja vivo el temporizador del anterior y
  el mensaje nuevo se esconde cuando le toca al viejo. Ver `venta_view._avisar`.
- **Nada que aparezca y desaparezca solo puede vivir encima de la tabla del carrito.** Al
  mostrarse empuja la tabla y al ocultarse la sube, y eso es un salto en cada escaneo. El
  aviso vive en el hueco de la columna de totales por eso; ver `venta_view._aviso`.
- **Las sombras son un efecto gráfico**, no una regla de la hoja de estilos: Qt no entiende
  `box-shadow`. `estilos.aplicar_sombra()` las pone, y solo en tarjetas de contenido — sobre
  una tabla que se repinta en cada escaneo cuesta caro.
- **Un widget que lleva fondo o radio necesita su `objectName` desde que se construye.** Qt
  calcula el relleno y el radio la primera vez que poliza el widget; si entonces no hay regla
  por id, cambiar el `objectName` después recolorea pero deja la geometría de un widget pelado.
  Le pasaba al mensaje de la pantalla de venta, que salía pegado al borde y sin esquinas.
- **Un `QWidget` suelto dentro de una tarjeta pinta el color del lienzo,** porque lo hereda de
  la regla `QWidget`. Los que solo agrupan otros widgets se declaran transparentes; ver
  `QWidget#filaDescuento`.
- **El desplegable de un `QComboBox` es o cuadrado o invisible.** Cualquier regla sobre
  `::drop-down` quita el marco cuadrado que rompe el radio de cápsula, pero se lleva la flecha
  por delante. Por eso existe `ui/widgets/desplegable.py`, que la pinta a mano con el color
  del tema.
- **Un cambio de tema repinta la hoja de estilos completa,** pero no los colores que una
  pantalla haya fijado celda a celda: por eso `VentanaPrincipal.aplicar_tema()` llama a
  `vista_venta.repintar()`.
- **Las teclas del carrito se interceptan en el campo de escaneo** con un `eventFilter`, y
  solo cuando está vacío (salvo ↑ y ↓). Si hay un código a medio escribir, las flechas siguen
  siendo del campo.

## 9. Dónde están los datos en ejecución

`%LOCALAPPDATA%\TiendaPOS\`:

```
tienda.db              base de datos
preferencias.json      tema, sonido y demás ajustes del equipo
backups/               copias automáticas (las 7 últimas)
logs/tienda_pos.log    registro rotativo (5 archivos de 1 MB)
autocomprobacion.txt   resultado del último --verificar
```

Para desarrollo y pruebas, la variable de entorno `TIENDA_POS_HOME` redirige toda esa
carpeta, de modo que nunca se toquen los datos reales:

```bash
TIENDA_POS_HOME=C:\temp\pruebas python main.py
```

## 10. Lo que falta para ser un producto

Deuda técnica y límites conocidos, para que nadie los descubra por sorpresa:

- **Sin trazabilidad de inventario.** El stock es un contador que baja al vender; no hay tabla
  de movimientos, así que no se puede responder "¿por qué no me cuadra el stock?".
- **Monopuesto.** SQLite local no sirve para varias cajas escribiendo a la vez sobre la red.
  El cambio está aislado en `repositories/`, pero implica un servidor.
- **Sin medios de pago ni documentos tributarios.** Deliberado: ver D-006.
- **Sin venta por peso.** El modelo asume unidades enteras.
- **No hay gestión de usuarios.** Los dos usuarios de ejemplo se crean en `db/seed.py` la
  primera vez que arranca el programa, y sus PIN están publicados en el manual. La lógica para
  cambiar un PIN existe y está probada (`services/auth.py::cambiar_pin`), pero **no está
  conectada a ninguna pantalla**: hoy, cambiar un PIN obliga a editar `seed.py` y borrar la
  base. Es la primera pieza que falta para una instalación real, y lo único del sistema que se
  documenta como "hágalo" sin que se pueda hacer.
- **Sin actualización automática.** Actualizar significa reemplazar la carpeta a mano.

**Estado al 2026-09-13.** Todo lo anterior sigue siendo cierto **hoy**, pero ya no es una lista de
límites aceptados: tras la primera reunión con el cliente, cuatro de estos puntos pasaron a estar
decididos y planificados. Ninguno está hecho todavía.

| Límite | Deja de serlo en |
|---|---|
| Sin trazabilidad de inventario | Fase 9 (D-018) |
| Monopuesto | Fase 13 (D-015): un proceso servidor dueño de la base, no la base en una carpeta compartida |
| No hay gestión de usuarios | Fase 12 |
| Instalación copiando una carpeta | Fase 14 (D-020) |

Se añaden dos límites nuevos, que la reunión sacó a la luz:

- **Sin precio de compra ni familias.** El cliente los tenía en su sistema anterior, pero el
  2026-09-14 dijo que no le interesan. D-016 y D-017 quedan retiradas y no se implementan. Sin
  costo no hay informe de margen ni de ganancia.
- **Los datos demo se cargan en el primer arranque con la base vacía**, y en la instalación real
  de la tienda eso mezcló 65 productos inventados con el catálogo del cliente. Se separaron con
  `tools/limpiar_demo.py`. Para una instalación real conviene arrancar con
  `abrir_base_datos(con_datos_demo=False)`. Ver `docs/DESPLIEGUE-TIENDA.md`.
- **Sin importación de datos.** No hay forma de cargar un catálogo que no sea a mano, producto por
  producto. Fase 10 (D-019), y `docs/RESCATE-DATOS.md` para el catálogo concreto de este cliente.

Siguen sin planificar: la venta por peso, los medios de pago y los documentos tributarios, y la
actualización automática.

## 11. El instalador

Sí se puede, y con el empaquetado actual es trabajo acotado. Lo que sigue se escribió como
valoración de viabilidad; la actualización del final de esta sección recoge lo que ya está
decidido. Nada de ello está construido todavía.

**Por qué es viable hoy.** El punto que suele arruinar un instalador ya está resuelto: el
programa **nunca escribe en su propia carpeta**. La base de datos, los respaldos, los logs y
las preferencias viven en `%LOCALAPPDATA%\TiendaPOS\`, así que el ejecutable puede instalarse
en `Archivos de Programa` —que es de solo lectura para el usuario— sin que nada falle. Lo que
falta es empaquetar `dist/TiendaPOS/` y crear accesos directos, que es exactamente lo que hace
un instalador.

**Herramientas posibles:**

| Opción | Qué da | Coste |
|---|---|---|
| **Inno Setup** | `TiendaPOS-setup.exe` con asistente, acceso directo, entrada en "Agregar o quitar programas" y desinstalador. Un archivo `.iss` de unas 40 líneas | Gratis |
| **NSIS** | Lo mismo, más flexible y más áspero de escribir | Gratis |
| **WiX / MSI** | Paquete `.msi`, que es lo que exige una empresa para instalar por directiva de grupo | Gratis, pero más trabajo |

Para un local con uno o dos PC, **Inno Setup** es la opción sensata; el `.msi` solo tiene
sentido si algún día hay un departamento de sistemas.

**Lo que habría que decidir además del instalador en sí:**

- **Firma de código.** Sin un certificado, Windows SmartScreen avisa de "editor desconocido"
  en la primera ejecución. El cliente puede pasar el aviso, pero da mala impresión en una
  entrega. Un certificado tiene coste anual y es una decisión de Santiago.
- **Actualizaciones.** Un instalador que reemplaza la versión anterior es fácil; uno que
  busque actualizaciones solo, no, y requeriría un servidor.
- **Qué hacer con los datos al desinstalar.** Lo correcto es **no borrarlos** y avisar dónde
  quedaron.

**Esfuerzo estimado:** alrededor de un día para el instalador funcionando y probado en un
Windows limpio, sin contar la firma de código.


---

### Actualización del 2026-09-13: ya no es solo una valoración

El cliente pidió expresamente mejorar la instalación, así que esto pasó de "valoración" a decisión
tomada (**D-020**) y a la fase 14 de `docs/PLAN.md`. Se mantiene **Inno Setup**.

Lo que cambia respecto a lo escrito arriba es que ahora hay **dos instalaciones distintas**, porque
el sistema va a funcionar en dos cajas (D-015). El instalador tiene que preguntar de cuál se trata:

| Modo | Qué instala | Qué pregunta |
|---|---|---|
| **Servidor y caja** | El programa y el proceso servidor, en el PC que guarda la base de datos | Nada más; abre el puerto en el cortafuegos |
| **Caja secundaria** | Solo el programa | La dirección del PC servidor |

Tres detalles que conviene no olvidar cuando se escriba el `.iss`:

- **El modo tiene que poder cambiarse después sin reinstalar.** El día que el cliente cambie el PC
  servidor no va a querer reinstalar las dos cajas.
- **La regla de cortafuegos** hay que crearla en el modo servidor. Si no, la segunda caja no
  conecta y el síntoma es un tiempo de espera agotado sin explicación, que es exactamente el tipo
  de fallo que hace desconfiar de un sistema.
- **Al desinstalar no se borran los datos** de `%LOCALAPPDATA%\TiendaPOS\`, y se avisa dónde
  quedaron.

**Esfuerzo revisado:** el día estimado arriba cubre el instalador sencillo. Los dos modos, la
configuración del servidor y la regla de cortafuegos añaden aproximadamente otro medio día, y hay
que probarlo en dos equipos, no en uno.
