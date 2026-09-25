"""Versionado del esquema de la base de datos.

Se usa `PRAGMA user_version`, un entero que SQLite guarda dentro del propio archivo. Es
suficiente para un producto monopuesto y evita añadirle a un prototipo la dependencia de un
sistema de migraciones completo.

Para publicar una versión nueva: subir VERSION_ESQUEMA y registrar su función en
_MIGRACIONES. Nunca se edita una migración ya publicada, porque puede haber bases de datos
en la calle que ya la aplicaron.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path

VERSION_ESQUEMA = 7

_RUTA_ESQUEMA = Path(__file__).with_name("schema.sql")


def _version_actual(conexion: sqlite3.Connection) -> int:
    return int(conexion.execute("PRAGMA user_version").fetchone()[0])


def _sentencias(script: str) -> list[str]:
    """Trocea un script SQL en sentencias individuales.

    No se usa `executescript` porque hace un COMMIT implícito antes de ejecutar, lo que
    rompe la transacción explícita que envuelve cada migración y dejaría la base a medio
    migrar si algo fallara. `complete_statement` decide dónde termina cada sentencia sin
    confundirse con los punto y coma que aparezcan dentro de un texto.
    """
    sentencias: list[str] = []
    acumulado = ""
    for linea in script.splitlines(keepends=True):
        acumulado += linea
        if sqlite3.complete_statement(acumulado):
            sentencias.append(acumulado.strip())
            acumulado = ""
    if acumulado.strip():
        sentencias.append(acumulado.strip())

    # Un trozo formado solo por comentarios o líneas en blanco no es una sentencia y SQLite
    # lo rechazaría. Ocurre cuando el archivo termina con un comentario.
    return [s for s in sentencias if _tiene_sql(s)]


def _tiene_sql(fragmento: str) -> bool:
    return any(
        linea.strip() and not linea.strip().startswith("--") for linea in fragmento.splitlines()
    )


def _crear_esquema_inicial(conexion: sqlite3.Connection) -> None:
    for sentencia in _sentencias(_RUTA_ESQUEMA.read_text(encoding="utf-8")):
        conexion.execute(sentencia)


def _descuento_por_linea(conexion: sqlite3.Connection) -> None:
    """Añade el descuento aplicado a cada línea de venta.

    Hasta ahora el descuento solo existía a nivel de venta. Al permitir descontar un
    producto concreto hace falta guardar cuánto se descontó en cada línea, o el detalle de
    una venta antigua no se podría explicar. Las ventas ya registradas quedan con 0, que es
    exactamente lo que ocurrió en ellas.
    """
    conexion.execute(
        "ALTER TABLE venta_linea ADD COLUMN descuento_clp INTEGER NOT NULL DEFAULT 0"
    )


def _intento_de_cobro(conexion: sqlite3.Connection) -> None:
    """Añade el identificador del intento de cobro, que hace idempotente `cerrar_venta`.

    Con dos cajas (D-015), un cobro puede agotar su tiempo límite sin que la caja llegue a
    saber si el servidor lo registró. Reintentar a ciegas duplicaría la venta; no reintentar
    la perdería. Las dos cosas son inaceptables en una caja, así que la caja genera un
    identificador por intento y el servidor lo usa para reconocer un reintento.

    El índice es UNIQUE, que es lo que convierte la garantía en una regla de la base y no en
    una comprobación que alguien pueda olvidar. En SQLite los NULL no colisionan entre sí en
    un índice único, de modo que las ventas ya registradas se quedan como están y la
    migración no reescribe ni una fila.
    """
    conexion.execute("ALTER TABLE venta ADD COLUMN intento_id TEXT")
    conexion.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_venta_intento ON venta (intento_id)"
    )


def _caja_de_la_venta(conexion: sqlite3.Connection) -> None:
    """Añade en qué caja se hizo cada venta (fase 16).

    El cliente pidió un cierre diario **por caja**, y hasta aquí ninguna venta sabía de cuál
    venía. Es texto y no una clave hacia una tabla de cajas: la caja es una propiedad de la
    instalación, no de la base compartida, y se guarda el nombre que la caja tenía **en el
    momento de vender**, igual que la línea guarda el nombre del producto (D-005).

    Las ventas anteriores se quedan en NULL. No sabemos dónde se hicieron, y rellenarlas sería
    inventar un dato que el dueño leería como cierto: el informe las muestra aparte, como
    "sin caja registrada". El índice empieza por la fecha porque el cierre siempre filtra por
    día, y el texto ISO permite comparar su prefijo.
    """
    conexion.execute("ALTER TABLE venta ADD COLUMN caja TEXT")
    conexion.execute("CREATE INDEX IF NOT EXISTS idx_venta_dia_caja ON venta (fecha_hora, caja)")


def _medio_de_pago(conexion: sqlite3.Connection) -> None:
    """Añade con qué pagó el cliente cada venta (fase 17): efectivo, débito o crédito.

    **Sin `CHECK`**, a diferencia de `rol` y `estado`, y a propósito: en SQLite un `CHECK`
    añadido con `ALTER TABLE` no se puede cambiar sin reconstruir la tabla, y la lista de medios
    es justo lo que el cliente todavía puede cambiar —transferencia, fiado—. La validación vive
    en el servicio, y la lectura tolera un valor que no conozca en lugar de romper el cierre.
    Quien añada un medio nuevo debe subir igualmente `VERSION_ESQUEMA`, para que una versión
    anterior no llegue a leerlo.

    Las ventas anteriores quedan en NULL, "no registrado". No se rellenan con efectivo: sería
    inventar un dato que el dueño leería como real.
    """
    conexion.execute("ALTER TABLE venta ADD COLUMN medio_pago TEXT")


def _arqueo_de_caja(conexion: sqlite3.Connection) -> None:
    """Añade el arqueo de caja (fase 19, D-036): turnos, salidas y entradas de efectivo.

    Un **turno** se abre con el efectivo que hay en el cajón y se cierra contándolo. El índice
    único parcial garantiza en la propia base que una caja no tenga dos turnos abiertos a la vez,
    aunque las dos cajas pidan abrir en el mismo instante. Al cerrar se guarda el esperado de ese
    momento: es lo que se comparó con lo contado, y no debe cambiar si mañana algo se recalcula.

    Los **movimientos** no se borran ni se editan: un retiro anotado mal se compensa con otro. El
    tipo va sin `CHECK`, por lo mismo que el medio de pago (fase 17): la lista es de las que el
    cliente puede ampliar, y el servicio es quien la valida. Su
    `intento_id` es único, igual que el de la venta, para que un reintento por la red no anote dos
    veces el mismo retiro (D-024).

    `venta.turno_id` queda en NULL en las ventas anteriores: no se abrieron con arqueo, y
    asignarlas a un turno sería inventar de qué cajón salió el dinero.
    """
    conexion.execute(
        """
        CREATE TABLE turno_caja (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            caja                TEXT    NOT NULL,
            abierto_en          TEXT    NOT NULL,
            abierto_por         INTEGER NOT NULL REFERENCES usuario (id),
            apertura_clp        INTEGER NOT NULL CHECK (apertura_clp >= 0),
            intento_apertura    TEXT    UNIQUE,
            cerrado_en          TEXT,
            cerrado_por         INTEGER REFERENCES usuario (id),
            esperado_clp        INTEGER,
            contado_clp         INTEGER CHECK (contado_clp IS NULL OR contado_clp >= 0),
            nota                TEXT
        )
        """
    )
    conexion.execute(
        "CREATE UNIQUE INDEX idx_turno_abierto ON turno_caja (caja) WHERE cerrado_en IS NULL"
    )
    conexion.execute("CREATE INDEX idx_turno_abierto_en ON turno_caja (abierto_en)")
    conexion.execute(
        """
        CREATE TABLE movimiento_efectivo (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            turno_id    INTEGER NOT NULL REFERENCES turno_caja (id),
            tipo        TEXT    NOT NULL,
            monto_clp   INTEGER NOT NULL CHECK (monto_clp > 0),
            motivo      TEXT    NOT NULL DEFAULT '',
            usuario_id  INTEGER NOT NULL REFERENCES usuario (id),
            fecha_hora  TEXT    NOT NULL,
            intento_id  TEXT    UNIQUE
        )
        """
    )
    conexion.execute("CREATE INDEX idx_movimiento_turno ON movimiento_efectivo (turno_id)")
    conexion.execute("ALTER TABLE venta ADD COLUMN turno_id INTEGER REFERENCES turno_caja (id)")
    conexion.execute("CREATE INDEX idx_venta_turno ON venta (turno_id)")


def _venta_por_peso(conexion: sqlite3.Connection) -> None:
    """Añade la venta por peso (D-037): productos con precio por kilo, líneas con gramos.

    `producto.por_peso` en 0 para todo lo que ya existía: se vendía por unidad y así sigue.
    `venta_linea.gramos` en NULL en las ventas anteriores, que son todas por unidad. Una línea
    por peso guarda `cantidad` 1, así que contar artículos sigue siendo sumar `cantidad`.
    """
    conexion.execute(
        "ALTER TABLE producto ADD COLUMN por_peso INTEGER NOT NULL DEFAULT 0 "
        "CHECK (por_peso IN (0, 1))"
    )
    conexion.execute(
        "ALTER TABLE venta_linea ADD COLUMN gramos INTEGER CHECK (gramos IS NULL OR gramos > 0)"
    )


# Versión de destino -> función que lleva la base desde la versión anterior hasta ella.
_MIGRACIONES: dict[int, Callable[[sqlite3.Connection], None]] = {
    1: _crear_esquema_inicial,
    2: _descuento_por_linea,
    3: _intento_de_cobro,
    4: _caja_de_la_venta,
    5: _medio_de_pago,
    6: _arqueo_de_caja,
    7: _venta_por_peso,
}


def aplicar_migraciones(conexion: sqlite3.Connection) -> int:
    """Lleva la base de datos hasta la última versión del esquema.

    Devuelve la versión resultante. Es idempotente: si ya está al día, no hace nada.

    Raises:
        RuntimeError: si el archivo viene de una versión más nueva del programa. Es
            preferible negarse a abrirlo antes que corromper los datos del cliente.
    """
    version = _version_actual(conexion)
    if version > VERSION_ESQUEMA:
        raise RuntimeError(
            f"La base de datos usa la versión de esquema {version}, más nueva que la que "
            f"entiende este programa ({VERSION_ESQUEMA}). Actualice la aplicación."
        )

    while version < VERSION_ESQUEMA:
        siguiente = version + 1
        migracion = _MIGRACIONES[siguiente]
        # Cada migración es atómica: si falla a la mitad, la base queda en la versión previa
        # y no en un estado intermedio imposible de diagnosticar.
        conexion.execute("BEGIN IMMEDIATE")
        try:
            migracion(conexion)
            conexion.execute(f"PRAGMA user_version = {siguiente}")
        except BaseException:
            conexion.execute("ROLLBACK")
            raise
        else:
            conexion.execute("COMMIT")
        version = siguiente

    return version
