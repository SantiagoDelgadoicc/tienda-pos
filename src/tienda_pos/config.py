"""Configuración global: rutas de datos y constantes del sistema.

Las rutas se resuelven en tiempo de ejecución y no al importar el módulo, para que las
pruebas puedan redirigirlas mediante la variable de entorno TIENDA_POS_HOME.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

#: Nombre de la carpeta de datos y del ejecutable. No cambia aunque cambie el rótulo del
#: negocio: cambiarlo dejaría al programa sin encontrar la base de datos ya instalada.
NOMBRE_APP = "TiendaPOS"

#: Lo que se ve en la barra lateral, en el título de la ventana y en los diálogos.
NOMBRE_COMERCIAL = "Punto y Fama"
RUBRO_COMERCIAL = "Botillería y market"

#: Nombre del ejecutable y del acceso directo. Es cosa distinta de NOMBRE_APP: este se
#: puede cambiar sin consecuencias, aquel no.
NOMBRE_EJECUTABLE = "PuntoYFamaCaja"

VERSION = "0.1.0"

#: Cuántos respaldos automáticos se conservan antes de borrar el más antiguo.
RESPALDOS_A_CONSERVAR = 7

#: Además de esos, se guarda el último respaldo de cada uno de estos días hacia atrás. Hace
#: falta porque se respalda al abrir y al cerrar: siete copias eran solo tres o cuatro días, y
#: un error que se descubre el lunes suele venir de la semana anterior (fase 22).
RESPALDOS_DIAS = 30

#: Longitud mínima y máxima del PIN de acceso.
PIN_LONGITUD_MIN = 4
PIN_LONGITUD_MAX = 8

#: Hora a la que empieza el "día" de la tienda en los informes: ventas del día y cierre.
#: **Pendiente de la pregunta H10.** En una botillería se vende pasada la medianoche, y si el
#: dueño cuenta la noche del viernes como del viernes, un corte a las 00:00 le parte la noche en
#: dos cierres y nunca le cuadrará con su cuaderno. Con 6, por ejemplo, el día iría de 06:00 a
#: 06:00. Es lo único que hay que cambiar: las consultas y el día que se muestra por defecto lo
#: leen de aquí.
HORA_CORTE_DIA = 0

#: Largo del PIN que genera el sistema al dar de alta a un empleado o al darle uno nuevo.
#: Cuatro cifras, como los que la tienda usa hoy: el cliente pidió una clave por empleado, no
#: una clave difícil, y un PIN que no se recuerda acaba escrito en un papel pegado a la caja.
#: Lo que sí aporta el sistema es que no sea `1234`.
LONGITUD_PIN_GENERADO = 4

#: Si es False, una venta que dejaría el stock en negativo se rechaza.
#: Se deja como constante y no como opción de interfaz porque cambiarlo es una decisión
#: de negocio del cliente, no del cajero. Ver D-009 en docs/DECISIONES.md.
#:
#: **True desde el 2026-09-25** (Santiago, añadido a D-009): las cantidades del catálogo de la
#: tienda no están contadas, y una caja que se niega a cobrar lo que el cliente tiene en la mano
#: es peor que un stock que queda en negativo. El negativo avisa de que falta cargar mercadería.
PERMITIR_STOCK_NEGATIVO = True

#: Longitud máxima aceptada para un código de barras leído.
CODIGO_LONGITUD_MAX = 32

#: Tope del peso de una línea vendida por peso (D-037): 50 kg. Un tope, y no un límite del
#: negocio: sirve para que un cero de más al teclear los gramos no cobre una fortuna.
GRAMOS_MAX_POR_LINEA = 50_000

#: Recargo por cajetilla de cigarros pagada con débito o crédito (fase 26, D-040), mientras el
#: administrador no fije otro. Lo pidió el cliente el 2026-10-10: $500 por cajetilla.
RECARGO_CIGARRO_DEFECTO_CLP = 500

#: Tope del recargo por cajetilla: protege de un cero de más al cambiarlo.
RECARGO_CIGARRO_MAXIMO_CLP = 10_000

#: Prefijo de los códigos internos que el sistema da a un producto por peso sin código de
#: barras, como el pan (D-037). El 2 inicial es el que el estándar EAN reserva para uso
#: interno de cada tienda, así que no choca con ningún código de fábrica.
PREFIJO_CODIGO_INTERNO = "2"

# --------------------------------------------------------------------------- red (D-015)

#: Puerto en el que escucha el servidor. Por encima de 1024 para no necesitar privilegios, y
#: fuera de los rangos habituales para no chocar con nada que el cliente tenga instalado.
PUERTO_SERVIDOR = 8477

#: Segundos que la caja espera una respuesta antes de darla por perdida. El criterio de la
#: fase 13 es avisar en menos de 3 s; este límite es la mitad, de modo que quede margen para
#: mostrar el aviso. En una red local sana la ida y vuelta son 1–2 ms: esta espera solo ocurre
#: cuando la red está realmente caída. Ver D-024.
TIEMPO_LIMITE_RED_S = 1.5

#: Tiempo límite del sondeo de estado, más corto que el de una operación: sirve para pintar el
#: indicador de conexión y no debe hacer esperar a nadie.
TIEMPO_LIMITE_SONDEO_S = 0.8

#: Cuánto espera la caja secundaria, al arrancar, a que la principal esté lista antes de
#: preguntarle nada a nadie. Cubre el caso de cada mañana: se encienden los dos equipos a la
#: vez y la secundaria llega antes de que la principal haya terminado de abrir el programa.
#: Noventa segundos dan de sobra para un arranque de Windows con el programa en el inicio.
ESPERA_SERVIDOR_AL_ARRANCAR_S = 90.0


def directorio_recursos() -> Path:
    """Carpeta de los archivos que acompañan al programa: logotipo, icono.

    No son datos del usuario y no viven en `%LOCALAPPDATA%`: viajan con el ejecutable. Al
    empaquetar con PyInstaller quedan en la carpeta temporal que este monta al arrancar, y
    cuyo camino deja en `sys._MEIPASS`.
    """
    empaquetado = getattr(sys, "_MEIPASS", None)
    if empaquetado:
        return Path(empaquetado) / "assets"
    return Path(__file__).resolve().parents[2] / "assets"


def archivo_configuracion_red() -> Path:
    """Dónde se guarda si este PC es servidor o caja secundaria, y a quién apunta.

    Va en un archivo aparte de `preferencias.json` a propósito: las preferencias son del
    gusto de quien usa el equipo (tema, sonido) y se pueden borrar sin consecuencias; esto es
    configuración de instalación, y borrarlo deja la caja secundaria sin saber dónde está su
    servidor. Se puede editar a mano, que es lo que pide D-015 al exigir que el modo se cambie
    sin reinstalar.
    """
    return directorio_datos() / "red.json"


def directorio_datos() -> Path:
    r"""Carpeta donde viven la base de datos, los respaldos y los logs.

    En Windows es %LOCALAPPDATA%\TiendaPOS. Nunca se usa la carpeta del programa porque
    Windows bloquea la escritura dentro de "Archivos de Programa".
    """
    personalizado = os.environ.get("TIENDA_POS_HOME")
    if personalizado:
        return Path(personalizado)

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / NOMBRE_APP

    # Linux y macOS: solo relevante para desarrollo y para la ejecución de pruebas.
    return Path.home() / f".{NOMBRE_APP.lower()}"


def ruta_base_datos() -> Path:
    return directorio_datos() / "tienda.db"


def directorio_respaldos() -> Path:
    return directorio_datos() / "backups"


def directorio_logs() -> Path:
    return directorio_datos() / "logs"


def asegurar_directorios() -> None:
    """Crea las carpetas de datos si no existen. Es idempotente."""
    for carpeta in (directorio_datos(), directorio_respaldos(), directorio_logs()):
        carpeta.mkdir(parents=True, exist_ok=True)
