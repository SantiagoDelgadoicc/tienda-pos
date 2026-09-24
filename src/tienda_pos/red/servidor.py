"""El proceso que es dueño de la base de datos (D-015).

Expone la superficie de `services/` por HTTP con JSON (`D-023`). Cada petición es una
operación completa y por tanto una única transacción: no se exponen los repositorios, que es
lo que haría falta para que una operación se partiera en varios viajes.

**Atiende de una petición en una, a propósito.** `HTTPServer` es de un solo hilo y aquí eso es
una virtud, no una limitación: conserva la invariante de `db/connection.py` de una sola
conexión, y hace imposible que dos cajas se pisen dentro de una transacción. Para dos cajas
sobra de largo — cada operación dura milisegundos.
"""

from __future__ import annotations

import json
import logging
import sys
import threading
from datetime import date
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

from .. import config
from ..db.migrations import VERSION_ESQUEMA
from ..domain.errors import ErrorDominio
from ..domain.models import Rol, Usuario
from ..services.venta import Carrito
from . import protocolo
from .sesion import SesionLocal

_logger = logging.getLogger(__name__)

_RUTA_API = "/api/"
_RUTA_ESTADO = "/api/estado"


class _Manejador(BaseHTTPRequestHandler):
    """Traduce peticiones HTTP en llamadas a la sesión local.

    El servidor guarda la sesión en `servidor.sesion`, que este manejador lee. No se guarda
    nada por conexión: cada petición se resuelve entera y se olvida.
    """

    protocol_version = "HTTP/1.1"
    server_version = f"TiendaPOS/{config.VERSION}"

    # ------------------------------------------------------------------ HTTP

    def do_GET(self) -> None:  # noqa: N802 (nombre impuesto por BaseHTTPRequestHandler)
        """Solo el sondeo de estado. Es GET para poder mirarlo desde el navegador.

        Ese detalle no es capricho: el día que la caja 2 no conecte, el diagnóstico se hace
        abriendo esta dirección en el navegador del propio local (`D-023`).
        """
        if self.path.rstrip("/") != _RUTA_ESTADO.rstrip("/"):
            self._responder(404, {"error": {"tipo": "NoEncontrado", "mensaje": "Ruta desconocida"}})
            return
        self._responder(200, {"resultado": self._estado()})

    def do_POST(self) -> None:  # noqa: N802
        if not self.path.startswith(_RUTA_API):
            self._responder(404, {"error": {"tipo": "NoEncontrado", "mensaje": "Ruta desconocida"}})
            return

        operacion = self.path[len(_RUTA_API) :].strip("/")
        try:
            argumentos = self._leer_cuerpo()
        except ValueError as exc:
            self._responder(400, {"error": {"tipo": "DatosInvalidos", "mensaje": str(exc)}})
            return

        metodo = _OPERACIONES.get(operacion)
        if metodo is None:
            self._responder(
                404,
                {"error": {"tipo": "NoEncontrado", "mensaje": f"Operación '{operacion}' desconocida"}},
            )
            return

        try:
            resultado = metodo(self.server.sesion, argumentos)  # type: ignore[attr-defined]
        except ErrorDominio as exc:
            # Un error del dominio no es un fallo del servidor: es el negocio diciendo que no.
            # Viaja con su tipo para que la caja pueda volver a levantarlo tal cual.
            self._responder(200, {"error": protocolo.de_error(exc)})
        except Exception:
            # Cualquier otra cosa sí es un fallo nuestro. Se registra entero aquí, donde está
            # el log, y a la caja le llega un mensaje que se pueda enseñar a un cajero.
            _logger.exception("Fallo atendiendo la operación %s", operacion)
            self._responder(
                500,
                {
                    "error": {
                        "tipo": "ErrorServidor",
                        "mensaje": "El servidor tuvo un problema. Avise al encargado.",
                    }
                },
            )
        else:
            self._responder(200, {"resultado": resultado})

    # ------------------------------------------------------------------ utilidades

    def _estado(self) -> dict[str, Any]:
        return {
            "version_protocolo": protocolo.VERSION_PROTOCOLO,
            "version_esquema": VERSION_ESQUEMA,
            "version_app": config.VERSION,
        }

    def _leer_cuerpo(self) -> dict[str, Any]:
        longitud = int(self.headers.get("Content-Length") or 0)
        if longitud <= 0:
            return {}
        crudo = self.rfile.read(longitud)
        try:
            datos = json.loads(crudo.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("El cuerpo de la petición no es JSON válido.") from exc
        if not isinstance(datos, dict):
            raise ValueError("El cuerpo de la petición debe ser un objeto JSON.")
        return datos

    def _responder(self, codigo: int, cuerpo: dict[str, Any]) -> None:
        crudo = json.dumps(cuerpo, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(crudo)))
        self.end_headers()
        self.wfile.write(crudo)

    def log_message(self, formato: str, *args: Any) -> None:
        """Manda el registro de acceso al log de la aplicación, no a la consola.

        Por defecto `BaseHTTPRequestHandler` escribe en stderr, que en un ejecutable de
        PyInstaller sin consola no va a ninguna parte.
        """
        _logger.debug("%s - %s", self.address_string(), formato % args)


# --------------------------------------------------------------------------- operaciones


def _usuario(argumentos: dict[str, Any]) -> Usuario | None:
    """Reconstruye el usuario que dice ser quien llama.

    **Esto no es autenticación**: el usuario ya se autenticó con su PIN contra el servidor
    (`autenticar`), y lo que viaja aquí es solo quién dijo ser después. En una red local
    cerrada y sin salida a internet es proporcionado, igual que el PIN de cuatro dígitos de
    `D-007`. Si algún día la red deja de ser de confianza, aquí es donde va un testigo de
    sesión firmado por el servidor.
    """
    datos = argumentos.get("usuario")
    return protocolo.a_usuario(datos) if datos else None


def _consultar_por_codigo(sesion: SesionLocal, a: dict[str, Any]) -> dict[str, Any]:
    producto = sesion.consultar_por_codigo(a["codigo"], a.get("registrar_faltante", True))
    return protocolo.de_producto(producto)


def _buscar_por_nombre(sesion: SesionLocal, a: dict[str, Any]) -> list[dict[str, Any]]:
    return [protocolo.de_producto(p) for p in sesion.buscar_por_nombre(a["texto"])]


def _listar_productos(sesion: SesionLocal, a: dict[str, Any]) -> list[dict[str, Any]]:
    productos = sesion.listar_productos(a.get("incluir_inactivos", False))
    return [protocolo.de_producto(p) for p in productos]


def _crear_producto(sesion: SesionLocal, a: dict[str, Any]) -> dict[str, Any]:
    producto = sesion.crear_producto(
        _usuario(a), a["codigo"], a["nombre"], a["precio_clp"], a.get("stock", 0)
    )
    return protocolo.de_producto(producto)


def _actualizar_producto(sesion: SesionLocal, a: dict[str, Any]) -> dict[str, Any]:
    producto = sesion.actualizar_producto(
        _usuario(a), a["producto_id"], a["codigo"], a["nombre"], a["precio_clp"], a["stock"]
    )
    return protocolo.de_producto(producto)


def _desactivar_producto(sesion: SesionLocal, a: dict[str, Any]) -> None:
    sesion.desactivar_producto(_usuario(a), a["producto_id"])
    return None


def _codigos_pendientes(sesion: SesionLocal, a: dict[str, Any]) -> list[dict[str, Any]]:
    return [protocolo.de_codigo_pendiente(c) for c in sesion.codigos_pendientes(_usuario(a))]


def _cerrar_venta(sesion: SesionLocal, a: dict[str, Any]) -> dict[str, Any]:
    carrito = Carrito.desde_dict(a["carrito"])
    # **La caja es la de la petición, no la de este servidor.** Es el error más fácil de cometer
    # al tocar esto: sin `caja=`, `SesionLocal` firmaría la venta con el nombre del servidor y
    # todas las ventas de la caja secundaria saldrían en el cierre como hechas en la principal,
    # sin ningún error que avise. Si la petición no trae caja, la venta queda sin caja.
    venta = sesion.cerrar_venta(carrito, _usuario(a), a.get("intento_id"), caja=a.get("caja"))
    return protocolo.de_venta(venta)


def _listar_usuarios(sesion: SesionLocal, a: dict[str, Any]) -> list[dict[str, Any]]:
    return [protocolo.de_usuario(u) for u in sesion.listar_usuarios()]


def _autenticar(sesion: SesionLocal, a: dict[str, Any]) -> dict[str, Any]:
    return protocolo.de_usuario(sesion.autenticar(a["nombre"], a["pin"]))


def _listar_para_administrar(sesion: SesionLocal, a: dict[str, Any]) -> list[dict[str, Any]]:
    usuarios = sesion.listar_para_administrar(_usuario(a), a.get("incluir_inactivos", False))
    return [protocolo.de_usuario(u) for u in usuarios]


def _alta_usuario(sesion: SesionLocal, a: dict[str, Any]) -> dict[str, Any]:
    usuario, pin = sesion.alta_usuario(_usuario(a), a["nombre"], Rol(a["rol"]))
    return {"usuario": protocolo.de_usuario(usuario), "pin": pin}


def _reiniciar_pin(sesion: SesionLocal, a: dict[str, Any]) -> dict[str, str]:
    return {"pin": sesion.reiniciar_pin(_usuario(a), a["usuario_id"])}


def _desactivar_usuario(sesion: SesionLocal, a: dict[str, Any]) -> None:
    sesion.desactivar_usuario(_usuario(a), a["usuario_id"])
    return None


def _reactivar_usuario(sesion: SesionLocal, a: dict[str, Any]) -> dict[str, str]:
    return {"pin": sesion.reactivar_usuario(_usuario(a), a["usuario_id"])}


def _resumen_del_dia(sesion: SesionLocal, a: dict[str, Any]) -> dict[str, int]:
    return sesion.resumen_del_dia(protocolo.a_fecha(a.get("dia")))


def _ventas_del_dia(sesion: SesionLocal, a: dict[str, Any]) -> list[dict[str, Any]]:
    ventas = sesion.ventas_del_dia(protocolo.a_fecha(a.get("dia")))
    return [protocolo.de_venta(v) for v in ventas]


#: El contrato, en un solo sitio. Lo que no esté aquí no se puede pedir por la red.
_OPERACIONES = {
    "consultar_por_codigo": _consultar_por_codigo,
    "buscar_por_nombre": _buscar_por_nombre,
    "listar_productos": _listar_productos,
    "crear_producto": _crear_producto,
    "actualizar_producto": _actualizar_producto,
    "desactivar_producto": _desactivar_producto,
    "codigos_pendientes": _codigos_pendientes,
    "cerrar_venta": _cerrar_venta,
    "listar_usuarios": _listar_usuarios,
    "autenticar": _autenticar,
    "listar_para_administrar": _listar_para_administrar,
    "alta_usuario": _alta_usuario,
    "reiniciar_pin": _reiniciar_pin,
    "desactivar_usuario": _desactivar_usuario,
    "reactivar_usuario": _reactivar_usuario,
    "resumen_del_dia": _resumen_del_dia,
    "ventas_del_dia": _ventas_del_dia,
}


# --------------------------------------------------------------------------- arranque


class _Servidor(HTTPServer):
    """`HTTPServer` con la sesión local colgada, para que el manejador la alcance."""

    daemon_threads = False

    def __init__(self, direccion: tuple[str, int], sesion: SesionLocal) -> None:
        super().__init__(direccion, _Manejador)
        self.sesion = sesion

    def handle_error(self, request: object, client_address: object) -> None:
        """Que una caja que corta la conexión no llene el registro de tracebacks.

        Pasa de forma rutinaria: la caja secundaria agota su tiempo límite (`D-024`) y cierra
        el socket mientras el servidor todavía está escribiendo la respuesta. No es un fallo
        del servidor, es el funcionamiento normal de un tiempo límite. Por defecto,
        `socketserver` vuelca el traceback completo a stderr, y en un registro de tienda eso
        sepulta los errores que sí importan.
        """
        excepcion = sys.exc_info()[1]
        if isinstance(excepcion, (ConnectionError, TimeoutError)):
            _logger.debug("La caja %s cortó la conexión: %s", client_address, excepcion)
            return
        _logger.exception("Fallo atendiendo a %s", client_address)


class ServidorTienda:
    """Envoltorio que arranca el servidor en un hilo de fondo y lo para al cerrar.

    El hilo es solo para que la interfaz de la caja principal siga respondiendo: **las
    peticiones se siguen atendiendo de una en una**, porque el bucle de `HTTPServer` es único.
    """

    def __init__(self, sesion: SesionLocal, host: str = "", puerto: int | None = None) -> None:
        self._puerto = puerto or config.PUERTO_SERVIDOR
        # host vacío = todas las interfaces, que en la práctica es la de la red local. No se
        # abre nada hacia internet: eso depende del router, y D-015 es explícito en que la
        # instalación no debe reenviar este puerto.
        self._servidor = _Servidor((host, self._puerto), sesion)
        self._hilo = threading.Thread(
            target=self._servidor.serve_forever, name="servidor-tienda", daemon=True
        )

    @property
    def puerto(self) -> int:
        return self._puerto

    def iniciar(self) -> None:
        self._hilo.start()
        _logger.info("Servidor escuchando en el puerto %s", self._puerto)

    def detener(self) -> None:
        self._servidor.shutdown()
        self._servidor.server_close()
        self._hilo.join(timeout=5)
        _logger.info("Servidor detenido")

    def __enter__(self) -> ServidorTienda:
        self.iniciar()
        return self

    def __exit__(self, *_excepcion: object) -> None:
        self.detener()
