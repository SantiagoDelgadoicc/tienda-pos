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

239 pruebas, unos 35 segundos. No necesitan pantalla: las de interfaz usan la plataforma
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
main.py                     punto de entrada (y --verificar)
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
python tools/icono.py                    # genera assets/tienda_pos.ico
python tools/construir.py                # dist/TiendaPOS/TiendaPOS.exe (recomendado)
python tools/construir.py --unico        # un solo dist/TiendaPOS.exe
python tools/crear_acceso_directo.py     # acceso directo en el escritorio
```

Resultado: unos 114 MB en carpeta, arranque medido en 0,93 s.

Se distribuye en carpeta y no como archivo único porque el formato de archivo único se
descomprime en una carpeta temporal en cada arranque y añade dos o tres segundos.

**Comprobar el paquete en un equipo ajeno:**

```bash
TiendaPOS.exe --verificar
```

Arranca el sistema completo sin mostrar nada, mide el tiempo y escribe
`%LOCALAPPDATA%\TiendaPOS\autocomprobacion.txt`. Devuelve 0 si todo fue bien.

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

## 11. ¿Se puede hacer un instalador? (valoración, no compromiso)

Sí, y con el empaquetado actual es trabajo acotado. Nada de lo que sigue está hecho ni
decidido: es la respuesta a una pregunta de viabilidad.

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

