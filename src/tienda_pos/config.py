"""Configuración global: rutas de datos y constantes del sistema.

Las rutas se resuelven en tiempo de ejecución y no al importar el módulo, para que las
pruebas puedan redirigirlas mediante la variable de entorno TIENDA_POS_HOME.
"""

from __future__ import annotations

import os
from pathlib import Path

NOMBRE_APP = "TiendaPOS"
NOMBRE_COMERCIAL = "Tienda POS"
VERSION = "0.1.0"

#: Cuántos respaldos automáticos se conservan antes de borrar el más antiguo.
RESPALDOS_A_CONSERVAR = 7

#: Longitud mínima y máxima del PIN de acceso.
PIN_LONGITUD_MIN = 4
PIN_LONGITUD_MAX = 8

#: Si es False, una venta que dejaría el stock en negativo se rechaza.
#: Se deja como constante y no como opción de interfaz porque cambiarlo es una decisión
#: de negocio del cliente, no del cajero. Ver D-009 en docs/DECISIONES.md.
PERMITIR_STOCK_NEGATIVO = False

#: Longitud máxima aceptada para un código de barras leído.
CODIGO_LONGITUD_MAX = 32

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
    """Carpeta donde viven la base de datos, los respaldos y los logs.

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
