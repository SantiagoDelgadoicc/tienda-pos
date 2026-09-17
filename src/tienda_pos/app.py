"""Arranque de la aplicación.

Orden de inicio, y el motivo de cada paso:

1. Registro de sucesos, para que cualquier fallo posterior quede documentado.
2. Manejador global de errores, para que nada cierre la aplicación por sorpresa.
3. Respaldo de la base de datos, antes de tocarla.
4. Apertura y migración de la base.
5. Acceso con PIN.
6. Ventana principal.
"""

from __future__ import annotations

import logging
import sys
import time

from PySide6.QtWidgets import QApplication, QMessageBox

from . import config
from .db.inicio import abrir_base_datos
from .db.respaldo import cerrar_limpiamente, crear_respaldo
from .red import config_red
from .red.cliente import ServidorNoDisponible, SesionRemota, VersionIncompatible
from .red.config_red import Modo
from .red.sesion import Sesion, SesionLocal
from .red.servidor import ServidorTienda
from .ui import errores, estilos
from .ui.main_window import VentanaPrincipal

_logger = logging.getLogger(__name__)

# Centinela para distinguir "canceló el acceso" de "no hay usuarios configurados".
_CANCELADO = object()


def _crear_aplicacion() -> QApplication:
    """Crea la QApplication ya vestida con las preferencias guardadas.

    El tema se aplica aquí y no en la ventana principal porque el diálogo de acceso aparece
    antes que ella: si no, el PIN se pediría siempre sobre fondo claro y la aplicación
    cambiaría de color a mitad del arranque.
    """
    from .services import preferencias as servicio_preferencias
    from .utils import sonido

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(config.NOMBRE_COMERCIAL)
    app.setApplicationVersion(config.VERSION)
    app.setOrganizationName(config.NOMBRE_APP)

    preferidas = servicio_preferencias.cargar()
    estilos.aplicar(app, preferidas.tema)
    sonido.habilitado = preferidas.sonido
    return app


def _iniciar_sesion(sesion: Sesion):
    """Pide el PIN al arrancar.

    Si la base no tiene usuarios (una instalación limpia sin datos de ejemplo) se entra sin
    sesión, para que el sistema no quede inutilizable antes de poder crear el primero.
    """
    from .ui.login_dialog import DialogoLogin

    if not sesion.listar_usuarios():
        _logger.warning("No hay usuarios configurados: se entra sin sesión")
        return None

    usuario = DialogoLogin.pedir(sesion)
    if usuario is None:
        return _CANCELADO

    _logger.info("Sesión iniciada: %s (%s)", usuario.nombre, usuario.rol)
    return usuario


def verificar() -> int:
    """Comprobación de arranque, sin interfaz visible ni intervención de nadie.

    Existe para poder responder con hechos a la pregunta "¿esto funciona en el computador
    del cliente?" antes de la demostración: arranca todo el sistema, crea la base, monta la
    ventana y mide cuánto tarda. Devuelve 0 si todo fue bien.

    El resultado se escribe en un archivo además de devolverse como código de salida, porque
    el ejecutable se construye sin consola y no habría dónde leerlo.
    """
    import time

    from .utils.logging_setup import configurar

    inicio = time.perf_counter()
    informe = config.directorio_datos() / "autocomprobacion.txt"
    lineas: list[str] = []

    try:
        config.asegurar_directorios()
        configurar()
        app = _crear_aplicacion()

        conexion = abrir_base_datos()
        from .repositories import productos as repo_productos

        lineas.append(f"Productos en el catálogo: {repo_productos.contar(conexion)}")

        ventana = VentanaPrincipal(SesionLocal(conexion))
        ventana.mostrar_venta()
        app.processEvents()
        ventana.close()
        conexion.close()

        transcurrido = time.perf_counter() - inicio
        lineas.append(f"Arranque completo en {transcurrido:.2f} s")
        lineas.append("RESULTADO: CORRECTO")
        codigo = 0
    except Exception as error:  # noqa: BLE001 - es una comprobación: interesa cualquier fallo
        _logger.exception("La autocomprobación falló")
        lineas.append(f"RESULTADO: FALLO · {error!r}")
        codigo = 1

    informe.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return codigo


def ejecutar() -> int:
    """Punto de entrada. Devuelve el código de salida del proceso."""
    from .utils.logging_setup import configurar

    config.asegurar_directorios()
    configurar()
    errores.instalar()

    app = _crear_aplicacion()

    red = config_red.cargar()
    _logger.info("Modo de funcionamiento: %s", red.modo)

    if red.modo is Modo.CAJA:
        return _ejecutar_como_caja(app, red)
    return _ejecutar_con_base_local(app, red)


def _ejecutar_con_base_local(app: QApplication, red: config_red.ConfiguracionRed) -> int:
    """Modo suelto y modo servidor: este PC es dueño de la base de datos.

    La única diferencia entre los dos es si además se levanta el servidor para que otra caja
    pueda conectarse. La interfaz es idéntica y habla con una `SesionLocal` en ambos casos,
    de modo que **la caja principal nunca depende de la red**, ni siquiera de la suya.
    """
    # El respaldo se hace antes de abrir la base: si el archivo estuviera dañado, al menos
    # queda una copia del estado previo a que este arranque lo toque. Solo aquí: en modo caja
    # no hay base propia, y los respaldos son cosa del servidor (condición 5 de D-015).
    crear_respaldo()

    try:
        conexion = abrir_base_datos(compartida_entre_hilos=red.modo is Modo.SERVIDOR)
    except Exception as error:  # noqa: BLE001 - aquí sí queremos atrapar cualquier cosa
        # Sin base de datos no hay nada que hacer, pero el usuario merece saber por qué en
        # lugar de ver una ventana que nunca aparece.
        _logger.exception("No se pudo abrir la base de datos")
        QMessageBox.critical(
            None,
            "No se pudo iniciar",
            "No fue posible abrir la base de datos.\n\n"
            f"{error}\n\nUbicación: {config.ruta_base_datos()}",
        )
        return 1

    sesion = SesionLocal(conexion)
    servidor: ServidorTienda | None = None

    if red.modo is Modo.SERVIDOR:
        try:
            servidor = ServidorTienda(sesion, puerto=red.puerto)
            servidor.iniciar()
        except OSError as error:
            # El puerto ocupado casi siempre significa que el programa ya está abierto. Se
            # avisa y se sigue: esta caja tiene que poder vender igual, aunque la segunda se
            # quede sin servicio. Dejar de vender por esto sería mucho peor que el problema.
            servidor = None
            _logger.exception("No se pudo abrir el puerto %s", red.puerto)
            QMessageBox.warning(
                None,
                "La segunda caja no podrá conectarse",
                f"No se pudo abrir el puerto {red.puerto}.\n\n{error}\n\n"
                "Esta caja funciona con normalidad, pero la segunda no podrá conectarse "
                "hasta resolverlo. Compruebe que el programa no esté ya abierto.",
            )

    codigo = 0
    try:
        usuario = _iniciar_sesion(sesion)
        if usuario is _CANCELADO:
            # Cerró la ventana de acceso: se sale sin ruido, sin ventana huérfana.
            return 0

        ventana = VentanaPrincipal(sesion)
        ventana.establecer_usuario(usuario)
        ventana.show()
        ventana.mostrar_venta()

        codigo = app.exec()
    finally:
        if servidor is not None:
            servidor.detener()
        # Respaldo también AL CERRAR, y no solo al arrancar. El respaldo de arranque copia el
        # estado *anterior* a la sesión que empieza: quien abre el programa, carga su catálogo
        # entero y cierra, se queda con cero respaldos de ese trabajo —y en el primer arranque
        # de todos ni siquiera hay base que copiar. Es justo el día que más duele.
        crear_respaldo()
        cerrar_limpiamente(conexion)
        conexion.close()

    _logger.info("Aplicación cerrada con código %s", codigo)
    return codigo


def _esperar_al_servidor(sesion: SesionRemota, red: config_red.ConfiguracionRed) -> bool:
    """Espera a que la caja principal esté disponible, con una barra que se puede cancelar.

    El caso que resuelve es el de todas las mañanas: se encienden los dos PC a la vez y la
    caja secundaria llega antes de que la principal haya terminado de arrancar. Esperar un
    poco convierte ese arranque en algo que no necesita a nadie, que es justo el objetivo.

    Devuelve True si conectó. Si se agota la espera o el cajero cancela, devuelve False y el
    que llama se encarga de preguntar qué hacer.
    """
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QProgressDialog

    limite = time.monotonic() + config.ESPERA_SERVIDOR_AL_ARRANCAR_S

    dialogo = QProgressDialog(
        f"Conectando con la caja principal ({red.servidor_host})…\n\n"
        "Si acaba de encender los equipos, espere unos segundos.",
        "Cancelar",
        0,
        0,
    )
    dialogo.setWindowTitle(config.NOMBRE_COMERCIAL)
    dialogo.setWindowModality(Qt.WindowModality.ApplicationModal)
    # Que no aparezca y desaparezca en el caso normal, que es conectar a la primera.
    dialogo.setMinimumDuration(1200)

    try:
        while time.monotonic() < limite:
            try:
                sesion.comprobar_compatibilidad()
                return True
            except VersionIncompatible:
                # No se arregla esperando. Se deja al bucle de fuera, que lo explica.
                return False
            except ServidorNoDisponible:
                pass

            QApplication.processEvents()
            if dialogo.wasCanceled():
                return False
    finally:
        dialogo.close()

    return False


def _conectar_reintentando(sesion: SesionRemota, red: config_red.ConfiguracionRed) -> bool:
    """Intenta conectar con la caja principal, ofreciendo reintentar. Devuelve si lo logró.

    Existe por un problema de la vida real y no de diseño: al abrir la tienda por la mañana,
    la caja secundaria se enciende antes de que alguien haya abierto el programa en la
    principal. Sin esto, el cajero recibe un error, el programa se cierra, y tiene que volver
    a lanzarlo cuando la otra caja esté lista. Con esto, deja el aviso en pantalla, avisa al
    encargado y pulsa "Reintentar" cuando la principal ya esté abierta.

    Una versión incompatible **no** se reintenta: no se arregla esperando, se arregla
    actualizando los dos equipos (condición 3 de D-015).
    """
    # Primero se espera en silencio: si las dos cajas se encienden a la vez, la principal
    # tarda unos segundos en tener el programa abierto y el servidor escuchando. Sin esta
    # espera, la secundaria mostraría un error justo en el arranque normal de cada mañana,
    # y el objetivo es que encender el PC baste para trabajar.
    if _esperar_al_servidor(sesion, red):
        return True

    while True:
        try:
            sesion.comprobar_compatibilidad()
            return True
        except VersionIncompatible as error:
            _logger.error("Versiones incompatibles: %s", error)
            QMessageBox.critical(None, "Las dos cajas tienen versiones distintas", str(error))
            return False
        except ServidorNoDisponible as error:
            _logger.warning("Sin conexión con el servidor: %s", error)
            respuesta = QMessageBox.warning(
                None,
                "La caja principal no responde",
                f"{error}\n\n"
                f"Se busca en: {red.servidor_host}:{red.puerto}\n\n"
                "Compruebe que el programa esté abierto en la caja principal y que este "
                "equipo tenga red. Después pulse Reintentar.",
                QMessageBox.StandardButton.Retry | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Retry,
            )
            if respuesta != QMessageBox.StandardButton.Retry:
                return False


def _ejecutar_como_caja(app: QApplication, red: config_red.ConfiguracionRed) -> int:
    """Caja secundaria: aquí no hay base de datos, todo se le pide al servidor.

    La compatibilidad se comprueba **antes** de mostrar nada (condición 3 de D-015): trabajar
    contra un servidor de otra versión es la forma silenciosa de corromper datos. Y si no se
    puede conectar, se dice claramente y no se abre la caja, porque vender sin ver el stock
    real descuadraría el inventario (condición 4: sin modo desconectado).
    """
    if not red.servidor_host:
        QMessageBox.critical(
            None,
            "Falta configurar la caja principal",
            "Este equipo está configurado como caja secundaria, pero no se indicó la "
            "dirección de la caja principal.\n\nRevise el archivo:\n"
            f"{config.archivo_configuracion_red()}",
        )
        return 1

    sesion = SesionRemota(red.servidor_host, red.puerto)
    if not _conectar_reintentando(sesion, red):
        return 1

    _logger.info("Conectada a la caja principal en %s:%s", red.servidor_host, red.puerto)

    usuario = _iniciar_sesion(sesion)
    if usuario is _CANCELADO:
        return 0

    ventana = VentanaPrincipal(sesion)
    ventana.establecer_usuario(usuario)
    ventana.show()
    ventana.mostrar_venta()

    codigo = app.exec()
    _logger.info("Aplicación cerrada con código %s", codigo)
    return codigo
