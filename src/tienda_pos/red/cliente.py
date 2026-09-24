"""La sesión de la caja secundaria: las mismas operaciones, pero por la red.

Aquí vive lo que `D-024` decidió: cada llamada bloquea con un tiempo límite corto y, si la red
no responde, levanta `ServidorNoDisponible` en lugar de quedarse esperando. La interfaz la trata
como cualquier otro error del dominio, que es lo que evita reescribir las pantallas.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from datetime import date
from typing import Any

from .. import config
from ..db.migrations import VERSION_ESQUEMA
from ..domain.errors import ErrorDominio
from ..domain.models import (
    CierreCaja,
    CodigoNoEncontrado,
    MedioPago,
    Producto,
    Rol,
    Usuario,
    Venta,
)
from ..services.venta import Carrito
from . import protocolo
from .sesion import Sesion

_logger = logging.getLogger(__name__)


class ServidorNoDisponible(ErrorDominio):
    """No se pudo hablar con el servidor.

    Hereda de `ErrorDominio` a propósito: para el cajero esto no es un fallo del programa sino
    una circunstancia con la que tiene que lidiar, igual que un stock insuficiente, y debe
    verlo como un mensaje claro y no como un diálogo de error técnico.
    """

    def __init__(self, detalle: str = "") -> None:
        self.detalle = detalle
        super().__init__(
            "No hay conexión con la caja principal. Avise al encargado y espere a que "
            "vuelva; mientras tanto no se puede cobrar en esta caja."
        )


class VersionIncompatible(ErrorDominio):
    """El servidor y esta caja no hablan la misma versión.

    Es la condición 3 de `D-015`: con dos PC las versiones se desincronizan solas, y trabajar
    contra un servidor de versión distinta es la forma de corromper datos sin enterarse.
    """

    def __init__(self, propia: int, del_servidor: int) -> None:
        self.propia = propia
        self.del_servidor = del_servidor
        super().__init__(
            f"Esta caja usa la versión {propia} y la caja principal la "
            f"{del_servidor}. Hay que actualizar las dos al mismo programa antes de seguir."
        )


class SesionRemota(Sesion):
    """Habla con el servidor de la caja principal.

    No mantiene estado entre llamadas ni reintenta por su cuenta —salvo en el cobro, donde el
    reintento es seguro gracias al identificador de intento—, porque un reintento automático
    sobre una operación que escribe es justamente lo que duplica ventas.
    """

    def __init__(
        self,
        host: str,
        puerto: int | None = None,
        tiempo_limite: float | None = None,
        caja: str | None = None,
    ) -> None:
        self._host = host
        self._caja = caja
        self._puerto = puerto or config.PUERTO_SERVIDOR
        self._tiempo_limite = tiempo_limite or config.TIEMPO_LIMITE_RED_S
        self._base = f"http://{host}:{self._puerto}"

    # ------------------------------------------------------------------ estado

    def descripcion(self) -> str:
        return f"Caja principal en {self._host}"

    def esta_conectada(self) -> bool:
        """Sondeo corto para pintar el indicador de conexión. Nunca lanza."""
        try:
            self._estado(config.TIEMPO_LIMITE_SONDEO_S)
        except Exception:
            return False
        return True

    def comprobar_compatibilidad(self) -> None:
        """Se llama al conectar, antes de dejar operar.

        Raises:
            ServidorNoDisponible, VersionIncompatible
        """
        estado = self._estado(self._tiempo_limite)
        del_servidor = int(estado.get("version_esquema", -1))
        if del_servidor != VERSION_ESQUEMA:
            raise VersionIncompatible(VERSION_ESQUEMA, del_servidor)

        protocolo_servidor = int(estado.get("version_protocolo", -1))
        if protocolo_servidor != protocolo.VERSION_PROTOCOLO:
            raise VersionIncompatible(protocolo.VERSION_PROTOCOLO, protocolo_servidor)

    def _estado(self, tiempo_limite: float) -> dict[str, Any]:
        peticion = urllib.request.Request(f"{self._base}/api/estado", method="GET")
        return self._enviar(peticion, tiempo_limite)

    # ------------------------------------------------------------------ transporte

    def _llamar(self, operacion: str, argumentos: dict[str, Any] | None = None) -> Any:
        cuerpo = json.dumps(argumentos or {}, ensure_ascii=False).encode("utf-8")
        peticion = urllib.request.Request(
            f"{self._base}/api/{operacion}",
            data=cuerpo,
            method="POST",
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        return self._enviar(peticion, self._tiempo_limite)

    def _enviar(self, peticion: urllib.request.Request, tiempo_limite: float) -> Any:
        try:
            with urllib.request.urlopen(peticion, timeout=tiempo_limite) as respuesta:
                crudo = respuesta.read()
        except urllib.error.HTTPError as exc:
            # El servidor contestó, pero con un código de error. Su cuerpo trae el detalle.
            crudo = exc.read()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            # No hubo respuesta: red caída, servidor apagado o demasiado lento. Es el caso que
            # D-024 acota con el tiempo límite, y el único que el cajero ve como "sin conexión".
            _logger.warning("Sin respuesta del servidor: %s", exc)
            raise ServidorNoDisponible(str(exc)) from exc

        try:
            datos = json.loads(crudo.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ServidorNoDisponible("El servidor respondió algo ininteligible.") from exc

        if "error" in datos:
            protocolo.levantar_error(datos["error"])
        return datos.get("resultado")

    # ------------------------------------------------------------------ catálogo

    def consultar_por_codigo(self, codigo: str, registrar_faltante: bool = True) -> Producto:
        datos = self._llamar(
            "consultar_por_codigo",
            {"codigo": codigo, "registrar_faltante": registrar_faltante},
        )
        return protocolo.a_producto(datos)

    def buscar_por_nombre(self, texto: str) -> list[Producto]:
        return [protocolo.a_producto(d) for d in self._llamar("buscar_por_nombre", {"texto": texto})]

    def listar_productos(self, incluir_inactivos: bool = False) -> list[Producto]:
        datos = self._llamar("listar_productos", {"incluir_inactivos": incluir_inactivos})
        return [protocolo.a_producto(d) for d in datos]

    def crear_producto(
        self, usuario: Usuario | None, codigo: str, nombre: str, precio_clp: int, stock: int
    ) -> Producto:
        datos = self._llamar(
            "crear_producto",
            {
                "usuario": protocolo.de_usuario(usuario) if usuario else None,
                "codigo": codigo,
                "nombre": nombre,
                "precio_clp": precio_clp,
                "stock": stock,
            },
        )
        return protocolo.a_producto(datos)

    def actualizar_producto(
        self,
        usuario: Usuario | None,
        producto_id: int,
        codigo: str,
        nombre: str,
        precio_clp: int,
        stock: int,
    ) -> Producto:
        datos = self._llamar(
            "actualizar_producto",
            {
                "usuario": protocolo.de_usuario(usuario) if usuario else None,
                "producto_id": producto_id,
                "codigo": codigo,
                "nombre": nombre,
                "precio_clp": precio_clp,
                "stock": stock,
            },
        )
        return protocolo.a_producto(datos)

    def desactivar_producto(self, usuario: Usuario | None, producto_id: int) -> None:
        self._llamar(
            "desactivar_producto",
            {
                "usuario": protocolo.de_usuario(usuario) if usuario else None,
                "producto_id": producto_id,
            },
        )

    def codigos_pendientes(self, usuario: Usuario | None) -> list[CodigoNoEncontrado]:
        datos = self._llamar(
            "codigos_pendientes",
            {"usuario": protocolo.de_usuario(usuario) if usuario else None},
        )
        return [protocolo.a_codigo_pendiente(d) for d in datos]

    # ------------------------------------------------------------------ venta

    def cerrar_venta(
        self,
        carrito: Carrito,
        usuario: Usuario | None,
        intento_id: str | None = None,
        *,
        medio_pago: MedioPago | None = MedioPago.EFECTIVO,
    ) -> Venta:
        """Cobra.

        `intento_id` es lo que hace seguro reintentar: si la primera petición llegó pero su
        respuesta se perdió, el servidor reconoce el intento y devuelve la misma venta en vez
        de cobrar dos veces (`D-024`). Quien llama debe reutilizar el mismo identificador al
        reintentar, y generar uno nuevo solo para una venta nueva.
        """
        datos = self._llamar(
            "cerrar_venta",
            {
                "carrito": carrito.a_dict(),
                "usuario": protocolo.de_usuario(usuario) if usuario else None,
                "intento_id": intento_id,
                # Esta caja dice quién es: el servidor no puede saberlo, no guarda estado por
                # conexión, y la IP cambia sola.
                "caja": self._caja,
                "medio_pago": str(medio_pago) if medio_pago else None,
            },
        )
        return protocolo.a_venta(datos)

    # ------------------------------------------------------------------ acceso

    def listar_usuarios(self) -> list[Usuario]:
        return [protocolo.a_usuario(d) for d in self._llamar("listar_usuarios")]

    def autenticar(self, nombre: str, pin: str) -> Usuario:
        return protocolo.a_usuario(self._llamar("autenticar", {"nombre": nombre, "pin": pin}))

    # ------------------------------------------------------------------ usuarios

    @staticmethod
    def _admin(admin: Usuario | None) -> dict[str, Any] | None:
        return protocolo.de_usuario(admin) if admin else None

    def listar_para_administrar(
        self, admin: Usuario | None, incluir_inactivos: bool = False
    ) -> list[Usuario]:
        datos = self._llamar(
            "listar_para_administrar",
            {"usuario": self._admin(admin), "incluir_inactivos": incluir_inactivos},
        )
        return [protocolo.a_usuario(d) for d in datos]

    def alta_usuario(self, admin: Usuario | None, nombre: str, rol: Rol) -> tuple[Usuario, str]:
        datos = self._llamar(
            "alta_usuario", {"usuario": self._admin(admin), "nombre": nombre, "rol": str(rol)}
        )
        return protocolo.a_usuario(datos["usuario"]), datos["pin"]

    def reiniciar_pin(self, admin: Usuario | None, usuario_id: int) -> str:
        datos = self._llamar(
            "reiniciar_pin", {"usuario": self._admin(admin), "usuario_id": usuario_id}
        )
        return datos["pin"]

    def desactivar_usuario(self, admin: Usuario | None, usuario_id: int) -> None:
        self._llamar(
            "desactivar_usuario", {"usuario": self._admin(admin), "usuario_id": usuario_id}
        )

    def reactivar_usuario(self, admin: Usuario | None, usuario_id: int) -> str:
        datos = self._llamar(
            "reactivar_usuario", {"usuario": self._admin(admin), "usuario_id": usuario_id}
        )
        return datos["pin"]

    # ------------------------------------------------------------------ reportes

    def resumen_del_dia(self, dia: date | None = None) -> dict[str, int]:
        return self._llamar("resumen_del_dia", {"dia": protocolo.de_fecha(dia)})

    def ventas_del_dia(self, dia: date | None = None) -> list[Venta]:
        datos = self._llamar("ventas_del_dia", {"dia": protocolo.de_fecha(dia)})
        return [protocolo.a_venta(d) for d in datos]

    def cierre_de_caja(self, dia: date | None, caja: str | None) -> CierreCaja:
        """Una sola petición con todo: ventas con sus líneas y la lista de cajas del día."""
        return protocolo.a_cierre(
            self._llamar("cierre_de_caja", {"dia": protocolo.de_fecha(dia), "caja": caja})
        )
