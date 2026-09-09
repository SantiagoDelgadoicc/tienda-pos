# Plan de trabajo — Prototipo Tienda POS

Documento vivo. Se actualiza a medida que avanzamos.
`[ ]` pendiente · `[x]` completado

**Plazo objetivo:** demostración al cliente esta semana.

> **Advertencia de plazo asumida conscientemente:** un POS completo, empaquetado y
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
- [ ] Primer commit y push

**Criterio de aceptación:** el repositorio existe, tiene su primer commit y los documentos
son comprensibles para alguien ajeno al proyecto.

---

## Fase 1 — Núcleo de datos y negocio (sin interfaz)

- [ ] `config.py`: rutas de datos en `%LOCALAPPDATA%\TiendaPOS\`
- [ ] `utils/money.py`: formato y aritmética de CLP en enteros
- [ ] `db/schema.sql`: esquema completo
- [ ] `db/connection.py`: conexión única, PRAGMAs (WAL, `foreign_keys`), transacciones
- [ ] `db/migrations.py`: versionado del esquema con `PRAGMA user_version`
- [ ] `db/seed.py`: catálogo demo de minimarket (~60 productos con EAN-13 válidos)
- [ ] `domain/models.py` y `domain/errors.py`
- [ ] `repositories/`: productos, ventas, usuarios
- [ ] `services/catalogo.py`: búsqueda por código exacto y por nombre parcial
- [ ] `services/venta.py`: carrito, agrupación de repetidos, descuento, totales y cierre
      transaccional con descuento de stock
- [ ] `services/auth.py`: PIN con hash y salt, roles
- [ ] Pruebas `pytest` de todo lo anterior

**Criterio de aceptación:** las pruebas pasan, incluyendo código inexistente, stock
insuficiente, descuento mayor que el total y fallo a mitad del cierre de venta, que debe
revertir por completo sin dejar datos a medias.

---

## Fase 2 — Interfaz de venta y consulta de precio ← primera demo presentable

- [ ] Ventana principal, gestión del foco y atajos de teclado
- [ ] Campo de escaneo, tabla del carrito y totales
- [ ] Pantalla de consulta de precio (F2), tipografía grande
- [ ] Diálogo de código no encontrado
- [ ] Cierre de venta con confirmación

**Criterio de aceptación:** tecleando códigos (equivalente exacto a lo que envía la pistola)
se puede consultar un precio, armar un carrito y cerrar una venta, sin que nada se rompa.

---

## Fase 3 — Administración, acceso e informe del día

- [ ] Diálogo de PIN al iniciar y modo administrador
- [ ] Alta, edición y baja lógica de productos (solo administrador)
- [ ] Descuento manual sobre la venta (monto o porcentaje)
- [ ] Pantalla de ventas del día: listado, total y detalle
- [ ] Stock visible en la ficha del producto

**Criterio de aceptación:** un administrador da de alta un producto, lo escanea, lo vende,
lo ve reflejado en el informe del día y comprueba el stock descontado.

---

## Fase 4 — Robustez

- [ ] Manejador global de excepciones con diálogo legible; la aplicación no se cierra
- [ ] Logging rotativo
- [ ] Respaldo automático de la base al iniciar, con retención de los últimos 7
- [ ] Sonidos distintos para éxito y error
- [ ] Validación del formato del código y detección pistola/teclado
- [ ] Pruebas de los caminos de error

**Criterio de aceptación:** provocar errores a propósito (base bloqueada, código con basura,
cierre forzado a mitad de venta) no pierde datos ni cierra el programa.

---

## Fase 5 — Empaquetado

- [ ] PyInstaller → `TiendaPOS.exe`
- [ ] Creación de la base y de los datos demo en el primer arranque
- [ ] Icono propio y acceso directo en el escritorio
- [ ] Prueba en carpeta limpia, en un equipo sin Python

**Criterio de aceptación:** doble clic en el acceso directo y el programa abre en menos de
3 segundos sin entorno de desarrollo instalado.

---

## Fase 6 — Documentación y demo

- [ ] `docs/MANUAL-USUARIO.md` con capturas
- [ ] `docs/TECNICA.md`
- [ ] `docs/GUION-DEMO.md`
- [ ] `docs/PREGUNTAS-CLIENTE.md` finalizado
- [ ] README actualizado

**Criterio de aceptación:** alguien ajeno instala, ejecuta y realiza una venta guiándose
solo por la documentación.

---

## Decisiones pendientes

- [ ] **Arranque automático al encender el PC.** Recomendación: **no** por defecto. Secuestra
      el equipo, complica las actualizaciones y estorba si el PC se usa para otra cosa.
      Se deja acceso directo en el escritorio; si el cliente insiste, se activa en un minuto.
- [ ] **Impresora de tickets.** Fuera del prototipo hasta saber si el cliente tiene una.
- [ ] **Respaldo en dispositivo externo.** Depende de cuán críticos considere sus datos.
- [ ] **Segunda caja / multipuesto.** Obligaría a pasar de SQLite local a un servidor. Es la
      decisión más cara de revertir; no se toca sin petición explícita del cliente.
- [ ] **Trazabilidad de inventario.** Hoy el stock es un contador, sin tabla de movimientos.
      Deuda técnica consciente y documentada.

---

## Sugerencias propuestas, no confirmadas

1. **Registro de códigos no encontrados.** Guardar lo que se escanea y no está en el catálogo,
   para que el dueño vea al final del día qué le falta cargar. Barato y demuestra que
   entendimos su operación. *Recomendada.*
2. **Guion de demo escrito.** Pasos exactos y códigos concretos, para no improvisar delante
   del cliente. *Muy recomendada.*
3. **Catálogo demo con productos reales del cliente.** Si se averigua qué vende, cargar 20 de
   sus productos cambia por completo la reacción en la reunión. *Recomendada.*
