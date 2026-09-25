"""Pruebas de la fase 16: cada venta sabe en qué caja se hizo.

El cliente pidió un cierre diario **por caja**, y hasta la migración 4 ninguna venta lo sabía.
El punto frágil de todo esto está en la red: la venta de la caja secundaria la escribe el
servidor, y si firmara con su propio nombre el cierre mentiría sin que nada avise. Esa es la
prueba que más importa de este archivo (`TestCajaPorLaRed`).
"""

from __future__ import annotations

import json
import socket
import sqlite3

import pytest

from tienda_pos.db import migrations
from tienda_pos.db.connection import transaccion
from tienda_pos.db.inicio import abrir_base_datos
from tienda_pos.db.migrations import VERSION_ESQUEMA, aplicar_migraciones
from tienda_pos.domain.models import Rol
from tienda_pos.red import config_red, protocolo
from tienda_pos.red.config_red import LARGO_MAX_NOMBRE_CAJA, ConfiguracionRed, Modo
from tienda_pos.repositories import ventas as repo_ventas
from tienda_pos.services import auth
from tienda_pos.services import venta as servicio_venta

from .conftest import abrir_cajas


def _carrito(producto):
    carrito = servicio_venta.Carrito()
    carrito.agregar(producto)
    return carrito


class TestMigracion:
    def test_una_base_de_la_version_3_gana_la_caja_sin_tocar_nada_mas(self, tmp_path) -> None:
        """El caso real: la tienda ya tiene ventas cuando llega esta versión."""
        antigua = sqlite3.connect(tmp_path / "v3.db")
        antigua.row_factory = sqlite3.Row
        migrations._crear_esquema_inicial(antigua)
        migrations._descuento_por_linea(antigua)
        migrations._intento_de_cobro(antigua)
        antigua.execute("PRAGMA user_version = 3")
        antigua.execute(
            "INSERT INTO venta (folio, fecha_hora, subtotal_clp, descuento_clp, total_clp, "
            "intento_id) VALUES (7, '2026-09-20 21:15:00', 4580, 0, 4580, 'abc')"
        )
        antigua.commit()
        antes = dict(antigua.execute("SELECT * FROM venta").fetchone())

        assert aplicar_migraciones(antigua) == VERSION_ESQUEMA
        despues = dict(antigua.execute("SELECT * FROM venta").fetchone())

        # No se sabe en qué caja se hizo, y no se inventa. Y ninguna columna que ya existía
        # cambia (las posteriores, como el medio de pago, tienen su propia prueba).
        assert despues["caja"] is None
        assert {columna: despues[columna] for columna in antes} == antes
        antigua.close()

    def test_el_indice_del_cierre_existe(self, conexion) -> None:
        indices = {f["name"] for f in conexion.execute("PRAGMA index_list(venta)")}
        assert "idx_venta_dia_caja" in indices


class TestVentaConCaja:
    def test_la_venta_guarda_su_caja(self, conexion, productos) -> None:
        venta = servicio_venta.cerrar_venta(conexion, _carrito(productos["leche"]), caja="Caja 1")
        assert venta.caja == "Caja 1"
        assert repo_ventas.obtener(conexion, venta.id).caja == "Caja 1"

    def test_sin_caja_queda_sin_caja(self, conexion, productos) -> None:
        venta = servicio_venta.cerrar_venta(conexion, _carrito(productos["leche"]))
        assert repo_ventas.obtener(conexion, venta.id).caja is None

    def test_la_caja_se_lee_tambien_en_las_ventas_del_dia(self, conexion, productos) -> None:
        servicio_venta.cerrar_venta(conexion, _carrito(productos["leche"]), caja="Mostrador")
        assert [v.caja for v in repo_ventas.del_dia(conexion)] == ["Mostrador"]

    def test_un_reintento_con_otra_caja_devuelve_la_venta_original(self, conexion, productos) -> None:
        # Caso real: la caja 2 reintenta un cobro y entre medias alguien renombró red.json.
        # La venta ya ocurrió: gana la que se guardó, y no se crea otra.
        primera = servicio_venta.cerrar_venta(
            conexion, _carrito(productos["leche"]), intento_id="x1", caja="Caja 2"
        )
        repetida = servicio_venta.cerrar_venta(
            conexion, _carrito(productos["leche"]), intento_id="x1", caja="Renombrada"
        )
        assert repetida.id == primera.id and repetida.caja == "Caja 2"
        assert len(repo_ventas.del_dia(conexion)) == 1


class TestNombreDeLaCaja:
    """Nada relacionado con el nombre de la caja puede impedir cobrar: es un dato de informe."""

    @staticmethod
    def _escribir(ruta, **datos) -> None:
        ruta.write_text(json.dumps(datos), encoding="utf-8")

    def test_se_lee_de_red_json(self, tmp_path) -> None:
        self._escribir(tmp_path / "red.json", modo="servidor", nombre_caja="Mostrador")
        assert config_red.cargar(tmp_path / "red.json").caja == "Mostrador"

    def test_sin_nombre_se_usa_el_del_pc(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr(config_red.platform, "node", lambda: "PC-CAJA-DOS")
        self._escribir(tmp_path / "red.json", modo="caja", servidor_host="192.168.1.10")
        assert config_red.cargar(tmp_path / "red.json").caja == "PC-CAJA-DOS"

    def test_sin_red_json_tambien_hay_nombre(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr(config_red.platform, "node", lambda: "MI-PC")
        assert config_red.cargar(tmp_path / "no-existe.json").caja == "MI-PC"

    def test_si_ni_el_pc_tiene_nombre_se_llama_caja(self, monkeypatch) -> None:
        monkeypatch.setattr(config_red.platform, "node", lambda: "")
        assert ConfiguracionRed().caja == "Caja"

    def test_no_se_deriva_del_modo(self, monkeypatch) -> None:
        # Si el nombre saliera del modo, cambiar el modo partiría en dos las ventas del mismo PC.
        monkeypatch.setattr(config_red.platform, "node", lambda: "PC-1")
        assert ConfiguracionRed(modo=Modo.SERVIDOR).caja == ConfiguracionRed(modo=Modo.SUELTO).caja

    @pytest.mark.parametrize(
        ("escrito", "queda"),
        [
            ("  Caja   1  ", "Caja 1"),
            ("Mostrador\tprincipal", "Mostrador principal"),
            ("x" * 300, "x" * LARGO_MAX_NOMBRE_CAJA),
            (12, "12"),
            (None, ""),
        ],
    )
    def test_se_normaliza_lo_que_alguien_escribio_a_mano(self, tmp_path, escrito, queda) -> None:
        self._escribir(tmp_path / "red.json", modo="servidor", nombre_caja=escrito)
        assert config_red.cargar(tmp_path / "red.json").nombre_caja == queda

    def test_se_guarda_y_se_recupera(self, tmp_path) -> None:
        ruta = tmp_path / "red.json"
        assert config_red.guardar(ConfiguracionRed(modo=Modo.SERVIDOR, nombre_caja="Bodega"), ruta)
        assert config_red.cargar(ruta).caja == "Bodega"

    def test_un_red_json_de_antes_sigue_abriendo(self, tmp_path, monkeypatch) -> None:
        # Es el que tienen hoy las dos cajas de la tienda: sin la clave nueva.
        monkeypatch.setattr(config_red.platform, "node", lambda: "PC-1")
        self._escribir(tmp_path / "red.json", modo="servidor", servidor_host="", puerto=8765)
        cargada = config_red.cargar(tmp_path / "red.json")
        assert cargada.modo is Modo.SERVIDOR and cargada.caja == "PC-1"


class TestProtocolo:
    def test_la_caja_va_y_vuelve(self, conexion, productos) -> None:
        venta = servicio_venta.cerrar_venta(conexion, _carrito(productos["leche"]), caja="Caja 2")
        assert protocolo.a_venta(protocolo.de_venta(venta)).caja == "Caja 2"

    def test_un_mensaje_sin_caja_no_rompe(self, conexion, productos) -> None:
        venta = servicio_venta.cerrar_venta(conexion, _carrito(productos["leche"]))
        datos = protocolo.de_venta(venta)
        del datos["caja"]
        assert protocolo.a_venta(datos).caja is None


def _puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestCajaPorLaRed:
    @pytest.fixture
    def tienda(self):
        """La principal se llama "Principal" y hace de servidor. Devuelve lo necesario."""
        from tienda_pos.red.cliente import SesionRemota
        from tienda_pos.red.servidor import ServidorTienda
        from tienda_pos.red.sesion import SesionLocal

        conexion = abrir_base_datos(":memory:", con_datos_demo=True, compartida_entre_hilos=True)
        with transaccion(conexion):
            cajera = auth.crear_usuario(conexion, "Marta", Rol.CAJERO, "5706")
        principal = SesionLocal(conexion, caja="Principal")
        abrir_cajas(conexion, cajera, "Principal", "Secundaria")
        puerto = _puerto_libre()
        with ServidorTienda(principal, host="127.0.0.1", puerto=puerto):
            yield {
                "conexion": conexion,
                "principal": principal,
                "cajera": cajera,
                "remota": lambda caja: SesionRemota("127.0.0.1", puerto, caja=caja),
            }
        conexion.close()

    @staticmethod
    def _carrito_demo(sesion):
        from tienda_pos.db.seed import codigo_demo

        carrito = servicio_venta.Carrito()
        carrito.agregar(sesion.consultar_por_codigo(codigo_demo(0)))
        return carrito

    def test_la_venta_de_la_secundaria_queda_a_nombre_de_la_secundaria(self, tienda) -> None:
        # **La prueba que protege el punto más frágil.** El servidor escribe la venta, pero la
        # hizo la otra caja: si firmara con "Principal", el cierre mentiría sin avisar.
        secundaria = tienda["remota"]("Secundaria")
        venta = secundaria.cerrar_venta(self._carrito_demo(secundaria), tienda["cajera"], "r1")
        assert venta.caja == "Secundaria"
        assert repo_ventas.obtener(tienda["conexion"], venta.id).caja == "Secundaria"

    def test_la_venta_de_la_principal_queda_a_nombre_de_la_principal(self, tienda) -> None:
        principal = tienda["principal"]
        venta = principal.cerrar_venta(self._carrito_demo(principal), tienda["cajera"], "l1")
        assert venta.caja == "Principal"

    def test_una_peticion_sin_caja_queda_sin_caja_y_no_con_la_del_servidor(self, tienda) -> None:
        anonima = tienda["remota"](None)
        venta = anonima.cerrar_venta(self._carrito_demo(anonima), tienda["cajera"], "a1")
        assert repo_ventas.obtener(tienda["conexion"], venta.id).caja is None

    def test_las_dos_cajas_vendiendo_quedan_separadas(self, tienda) -> None:
        secundaria = tienda["remota"]("Secundaria")
        principal = tienda["principal"]
        principal.cerrar_venta(self._carrito_demo(principal), tienda["cajera"], "p1")
        secundaria.cerrar_venta(self._carrito_demo(secundaria), tienda["cajera"], "s1")
        secundaria.cerrar_venta(self._carrito_demo(secundaria), tienda["cajera"], "s2")

        cajas = [v.caja for v in repo_ventas.del_dia(tienda["conexion"])]
        assert sorted(cajas) == ["Principal", "Secundaria", "Secundaria"]


class TestFichaDeLaCaja:
    def test_la_ficha_del_usuario_dice_en_que_caja_se_esta(self, app, conexion) -> None:
        # Dos PC con el mismo nombre mezclan el cierre sin avisar; con el nombre siempre a la
        # vista, se nota el primer día.
        from tienda_pos.domain.models import Usuario
        from tienda_pos.red.sesion import SesionLocal
        from tienda_pos.ui.main_window import VentanaPrincipal

        ventana = VentanaPrincipal(SesionLocal(conexion, caja="Mostrador"))
        ventana.establecer_usuario(Usuario(id=1, nombre="Marta", rol=Rol.CAJERO))
        assert ventana.barra_lateral.etiqueta_rol.text() == "Cajero · Mostrador"
        assert "Mostrador" in ventana.barra_lateral._ficha.toolTip()
        ventana.close()
