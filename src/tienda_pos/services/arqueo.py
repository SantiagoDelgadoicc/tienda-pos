"""Arqueo de caja: abrir, anotar lo que entra y sale del cajón, y cerrar contando (fase 19).

Lo pidió el cliente el 2026-09-24: anota todos los retiros "porque si no le robarían un montón",
saca plata seguido de cada caja, paga en efectivo a algunos proveedores desde ella, y quiere que
el sistema le dé cifras exactas. Las reglas están en D-036; las que protegen contra el robo viven
aquí y no en la pantalla, porque en modo red la pantalla está en otro PC:

- **un retiro exige administrador**; un pago a proveedor lo anota cualquiera, a su nombre;
- **el conteo es a ciegas**: a quien no es administrador no se le devuelve cuánto debería haber,
  ni se le manda por la red;
- nada de lo anotado se borra ni se edita.

Todos los errores son de los que viajan por la red con su texto (`red/protocolo.py`).
"""

from __future__ import annotations

import sqlite3
from datetime import datetime

from ..db.connection import escribir_meta, leer_meta, transaccion
from ..domain.errors import CajaCerrada, DatosInvalidos, PermisoDenegado
from ..domain.models import MovimientoEfectivo, TipoMovimiento, TurnoCaja, Usuario
from ..repositories import arqueo as repo_arqueo
from .auth import exigir_admin, exigir_sesion
from ..utils.money import formatear_clp

#: Clave de `meta` del monto que se propone al abrir una caja. Es del negocio y no del PC: las
#: dos cajas proponen lo mismo.
CLAVE_MONTO_SUGERIDO = "monto_apertura_sugerido"

#: Tope de cualquier monto del arqueo. No es una regla del negocio sino una red contra el dedo
#: que se queda pegado: $100.000.000 en una botillería es un error de tecleo, no un retiro.
MONTO_MAXIMO_CLP = 99_999_999

#: Largo máximo del motivo y de la nota: caben el nombre de un proveedor y una frase.
LARGO_MAXIMO_TEXTO = 120

#: Cuántos turnos anteriores enseña la pantalla al administrador.
TURNOS_RECIENTES = 30


def _ahora() -> datetime:
    return datetime.now().replace(microsecond=0)


def _exigir_caja(caja: str | None) -> str:
    # En una instalación real la caja siempre tiene nombre (D-033). Si no lo tiene, no hay a qué
    # cajón atribuir el dinero, y se dice en vez de inventarlo.
    if not caja:
        raise DatosInvalidos("Esta caja no tiene nombre. Revise `nombre_caja` en red.json.")
    return caja


def _validar_monto(monto: object, que: str, *, puede_ser_cero: bool) -> int:
    if isinstance(monto, bool) or not isinstance(monto, int):
        raise DatosInvalidos(f"{que} debe ser un monto en pesos, sin decimales.")
    minimo = 0 if puede_ser_cero else 1
    if monto < minimo:
        raise DatosInvalidos(
            f"{que} no puede ser negativo." if puede_ser_cero else f"{que} debe ser mayor que cero."
        )
    if monto > MONTO_MAXIMO_CLP:
        raise DatosInvalidos(f"{que} es demasiado grande: revise que no sobre un cero.")
    return monto


def _limpiar_texto(texto: str | None) -> str:
    texto = " ".join((texto or "").split())
    if len(texto) > LARGO_MAXIMO_TEXTO:
        raise DatosInvalidos(f"El texto es demasiado largo: como máximo {LARGO_MAXIMO_TEXTO} letras.")
    return texto


def _completar(
    conexion: sqlite3.Connection, turno: TurnoCaja, usuario: Usuario | None
) -> TurnoCaja:
    """Carga los movimientos y, **solo para un administrador**, lo que permite saber cuánto
    debería haber. Para cualquier otro, esas cifras salen en None (D-036, conteo a ciegas)."""
    turno.movimientos = repo_arqueo.movimientos_de(conexion, turno.id)
    return _visible_para(conexion, turno, usuario)


def _visible_para(
    conexion: sqlite3.Connection, turno: TurnoCaja, usuario: Usuario | None
) -> TurnoCaja:
    if usuario is not None and usuario.es_admin:
        turno.ventas_efectivo_clp, turno.ventas_efectivo = repo_arqueo.ventas_en_efectivo(
            conexion, turno.id
        )
    else:
        turno.ventas_efectivo_clp = turno.ventas_efectivo = None
        turno.esperado_al_cerrar_clp = None
    return turno


# --------------------------------------------------------------------------- consultas


def turno_abierto(
    conexion: sqlite3.Connection, caja: str | None, usuario: Usuario | None
) -> TurnoCaja | None:
    """El turno abierto de la caja, con sus movimientos. None si la caja está cerrada."""
    if not caja:
        return None
    turno = repo_arqueo.turno_abierto(conexion, caja)
    return _completar(conexion, turno, usuario) if turno else None


def turnos_recientes(
    conexion: sqlite3.Connection, admin: Usuario | None, limite: int = TURNOS_RECIENTES
) -> list[TurnoCaja]:
    """Los últimos turnos de todas las cajas, con su resultado. Solo administradores."""
    exigir_admin(admin, "ver los cierres de caja")
    turnos = repo_arqueo.turnos_recientes(conexion, limite)
    movimientos = repo_arqueo.movimientos_de_varios(conexion, [t.id for t in turnos])
    for turno in turnos:
        turno.movimientos = movimientos.get(turno.id, [])
        _visible_para(conexion, turno, admin)
    return turnos


def monto_sugerido(conexion: sqlite3.Connection) -> int | None:
    """El monto que se propone al abrir una caja, o None si el administrador no fijó ninguno."""
    valor = leer_meta(conexion, CLAVE_MONTO_SUGERIDO)
    try:
        return int(valor) if valor not in (None, "") else None
    except ValueError:
        return None


def fijar_monto_sugerido(
    conexion: sqlite3.Connection, admin: Usuario | None, monto_clp: int | None
) -> None:
    """Fija el monto que se propone al abrir. None lo quita. Solo administradores."""
    exigir_admin(admin, "cambiar el monto sugerido de apertura")
    if monto_clp is not None:
        _validar_monto(monto_clp, "El monto sugerido", puede_ser_cero=True)
    with transaccion(conexion):
        escribir_meta(conexion, CLAVE_MONTO_SUGERIDO, "" if monto_clp is None else str(monto_clp))


# --------------------------------------------------------------------------- abrir y cerrar


def abrir_turno(
    conexion: sqlite3.Connection,
    caja: str | None,
    usuario: Usuario | None,
    apertura_clp: int,
    intento_id: str | None = None,
) -> TurnoCaja:
    """Abre la caja con el efectivo que hay en el cajón.

    Con `intento_id`, un reintento por la red devuelve el turno ya abierto en vez de fallar.

    Raises:
        DatosInvalidos: monto inválido, o la caja ya está abierta.
    """
    usuario = exigir_sesion(usuario, "abrir la caja")
    caja = _exigir_caja(caja)
    apertura_clp = _validar_monto(apertura_clp, "El efectivo de apertura", puede_ser_cero=True)

    if intento_id:
        ya_abierto = repo_arqueo.turno_por_intento(conexion, intento_id)
        if ya_abierto is not None:
            return _completar(conexion, ya_abierto, usuario)

    try:
        with transaccion(conexion):
            abierto = repo_arqueo.turno_abierto(conexion, caja)
            if abierto is not None:
                raise DatosInvalidos(
                    f"La caja {caja} ya está abierta desde las {abierto.abierto_en:%H:%M}, "
                    f"por {abierto.abierto_por_nombre or 'otro usuario'}."
                )
            turno_id = repo_arqueo.insertar_turno(
                conexion, caja, _ahora(), usuario.id, apertura_clp, intento_id
            )
    except sqlite3.IntegrityError:
        # Dos aperturas a la vez: el índice único dejó pasar solo una. Si era este mismo
        # intento, la caja quedó abierta como se pidió.
        if intento_id:
            ganador = repo_arqueo.turno_por_intento(conexion, intento_id)
            if ganador is not None:
                return _completar(conexion, ganador, usuario)
        raise DatosInvalidos(f"La caja {caja} ya está abierta.") from None

    return _completar(conexion, repo_arqueo.obtener_turno(conexion, turno_id), usuario)


def cerrar_turno(
    conexion: sqlite3.Connection,
    caja: str | None,
    usuario: Usuario | None,
    turno_id: int,
    contado_clp: int,
    nota: str | None = None,
) -> TurnoCaja:
    """Cierra un turno con lo que se contó en el cajón.

    Guarda el esperado de ese momento, lo contado, quién y la nota. **No bloquea nada ni exige
    explicación** si no cuadra (H1d, sin respuesta). Cerrar dos veces devuelve el primer cierre:
    es un reintento, no un segundo conteo.

    Un cajero solo cierra la caja en la que está; un administrador, cualquiera, por si el PC de
    la otra no enciende.

    Raises:
        DatosInvalidos, PermisoDenegado
    """
    usuario = exigir_sesion(usuario, "cerrar la caja")
    contado_clp = _validar_monto(contado_clp, "El efectivo contado", puede_ser_cero=True)
    nota = _limpiar_texto(nota) or None

    with transaccion(conexion):
        turno = repo_arqueo.obtener_turno(conexion, turno_id)
        if turno is None:
            raise DatosInvalidos("Esa caja no existe o ya no está abierta. Actualice la pantalla.")
        if turno.abierto:
            if turno.caja != caja and not usuario.es_admin:
                raise PermisoDenegado(f"cerrar la caja {turno.caja} desde otro equipo")
            turno.movimientos = repo_arqueo.movimientos_de(conexion, turno.id)
            turno.ventas_efectivo_clp, turno.ventas_efectivo = repo_arqueo.ventas_en_efectivo(
                conexion, turno.id
            )
            repo_arqueo.cerrar_turno(
                conexion, turno.id, _ahora(), usuario.id, turno.esperado_clp, contado_clp, nota
            )

    return _completar(conexion, repo_arqueo.obtener_turno(conexion, turno_id), usuario)


# --------------------------------------------------------------------------- movimientos


def _validar_tipo(tipo: TipoMovimiento | str) -> TipoMovimiento:
    try:
        return TipoMovimiento(tipo)
    except ValueError:
        raise DatosInvalidos(f"Tipo de movimiento desconocido: {tipo}.") from None


def registrar_movimiento(
    conexion: sqlite3.Connection,
    caja: str | None,
    usuario: Usuario | None,
    tipo: TipoMovimiento | str,
    monto_clp: int,
    motivo: str = "",
    intento_id: str | None = None,
) -> MovimientoEfectivo:
    """Anota una salida o entrada de efectivo en el turno abierto de la caja.

    `usuario` es quien la hace y a cuyo nombre queda. En un retiro tiene que ser administrador:
    es el dueño sacando plata, y es la única salida que un cajero no puede anotar.

    Raises:
        DatosInvalidos, PermisoDenegado, CajaCerrada
    """
    usuario = exigir_sesion(usuario, "anotar una salida o entrada de efectivo")
    caja = _exigir_caja(caja)
    tipo = _validar_tipo(tipo)
    if tipo is TipoMovimiento.RETIRO:
        exigir_admin(usuario, "anotar un retiro de efectivo")
    monto_clp = _validar_monto(monto_clp, "El monto", puede_ser_cero=False)
    motivo = _limpiar_texto(motivo)
    if tipo is TipoMovimiento.PAGO_PROVEEDOR and not motivo:
        raise DatosInvalidos("Escriba a qué proveedor se le pagó.")

    if intento_id:
        ya_anotado = repo_arqueo.movimiento_por_intento(conexion, intento_id)
        if ya_anotado is not None:
            return ya_anotado

    try:
        with transaccion(conexion):
            turno_id = repo_arqueo.id_turno_abierto(conexion, caja)
            if turno_id is None:
                raise CajaCerrada(caja)
            movimiento_id = repo_arqueo.insertar_movimiento(
                conexion, turno_id, tipo, monto_clp, motivo, usuario.id, _ahora(), intento_id
            )
    except sqlite3.IntegrityError:
        if intento_id:
            ganador = repo_arqueo.movimiento_por_intento(conexion, intento_id)
            if ganador is not None:
                return ganador
        raise

    return repo_arqueo.obtener_movimiento(conexion, movimiento_id)


def describir_diferencia(diferencia_clp: int) -> str:
    """"Cuadra", "Faltan $3.000" o "Sobran $500": como lo diría el dueño."""
    if diferencia_clp == 0:
        return "Cuadra"
    if diferencia_clp < 0:
        return f"Faltan {formatear_clp(-diferencia_clp)}"
    return f"Sobran {formatear_clp(diferencia_clp)}"
