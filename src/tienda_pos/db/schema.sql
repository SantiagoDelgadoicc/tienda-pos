-- Esquema de la base de datos de Tienda POS.
-- Los importes son SIEMPRE enteros de CLP (ver D-004 en docs/DECISIONES.md).
-- Las fechas se guardan como texto ISO-8601 en hora local.

CREATE TABLE IF NOT EXISTS producto (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo_barras   TEXT    NOT NULL UNIQUE,
    nombre          TEXT    NOT NULL,
    precio_clp      INTEGER NOT NULL CHECK (precio_clp >= 0),
    stock           INTEGER NOT NULL DEFAULT 0,
    activo          INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
    creado_en       TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    actualizado_en  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- El índice de codigo_barras lo crea la restricción UNIQUE.
-- Este otro acelera la búsqueda por nombre, que es el recurso del cajero cuando el
-- código de barras está roto o el producto no lo tiene impreso.
CREATE INDEX IF NOT EXISTS idx_producto_nombre ON producto (nombre);
CREATE INDEX IF NOT EXISTS idx_producto_activo ON producto (activo);

CREATE TABLE IF NOT EXISTS usuario (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre      TEXT    NOT NULL UNIQUE,
    rol         TEXT    NOT NULL CHECK (rol IN ('cajero', 'admin')),
    pin_hash    TEXT    NOT NULL,
    salt        TEXT    NOT NULL,
    activo      INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
    creado_en   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS venta (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    folio           INTEGER NOT NULL UNIQUE,
    usuario_id      INTEGER REFERENCES usuario (id),
    fecha_hora      TEXT    NOT NULL,
    subtotal_clp    INTEGER NOT NULL CHECK (subtotal_clp >= 0),
    descuento_clp   INTEGER NOT NULL DEFAULT 0 CHECK (descuento_clp >= 0),
    total_clp       INTEGER NOT NULL CHECK (total_clp >= 0),
    estado          TEXT    NOT NULL DEFAULT 'completada'
                            CHECK (estado IN ('completada', 'anulada'))
);

CREATE INDEX IF NOT EXISTS idx_venta_fecha ON venta (fecha_hora);

-- Las líneas guardan una COPIA del código, el nombre y el precio del momento de la venta.
-- Es desnormalización deliberada: cambiar un precio mañana no debe reescribir el valor de
-- las ventas de ayer (ver D-005).
CREATE TABLE IF NOT EXISTS venta_linea (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    venta_id        INTEGER NOT NULL REFERENCES venta (id) ON DELETE CASCADE,
    producto_id     INTEGER REFERENCES producto (id),
    codigo_barras   TEXT    NOT NULL,
    nombre          TEXT    NOT NULL,
    precio_unit_clp INTEGER NOT NULL CHECK (precio_unit_clp >= 0),
    cantidad        INTEGER NOT NULL CHECK (cantidad > 0),
    subtotal_clp    INTEGER NOT NULL CHECK (subtotal_clp >= 0)
);

CREATE INDEX IF NOT EXISTS idx_linea_venta ON venta_linea (venta_id);

-- Códigos escaneados que no están en el catálogo. Sirven para que el dueño vea al final
-- del día qué productos le faltan por cargar.
CREATE TABLE IF NOT EXISTS codigo_no_encontrado (
    codigo      TEXT    PRIMARY KEY,
    intentos    INTEGER NOT NULL DEFAULT 1,
    primera_vez TEXT    NOT NULL,
    ultima_vez  TEXT    NOT NULL,
    resuelto    INTEGER NOT NULL DEFAULT 0 CHECK (resuelto IN (0, 1))
);

CREATE TABLE IF NOT EXISTS meta (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
);
