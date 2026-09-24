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

VERSION_ESQUEMA = 4

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


# Versión de destino -> función que lleva la base desde la versión anterior hasta ella.
_MIGRACIONES: dict[int, Callable[[sqlite3.Connection], None]] = {
    1: _crear_esquema_inicial,
    2: _descuento_por_linea,
    3: _intento_de_cobro,
    4: _caja_de_la_venta,
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
