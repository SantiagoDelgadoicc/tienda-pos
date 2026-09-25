"""Pruebas de los caminos que no deberían ocurrir nunca.

Una funcionalidad no está terminada porque funcione en el caso normal. Aquí se prueba lo que
pasa cuando falla el disco, cuando la base es de solo lectura, cuando el respaldo no se puede
crear y cuando salta un error que nadie previó.
"""

from __future__ import annotations

import logging
import sqlite3
import time
from pathlib import Path

import pytest

from tienda_pos.db.connection import conectar, transaccion
from tienda_pos.db.inicio import abrir_base_datos
from tienda_pos.db.respaldo import crear_respaldo, listar_respaldos
from tienda_pos.db.seed import cargar_datos_demo
from tienda_pos.repositories import productos as repo_productos
from tienda_pos.utils import logging_setup
from tienda_pos.utils.scanner import DetectorLector


@pytest.fixture
def base_en_disco(tmp_path: Path) -> Path:
    """Una base de datos real en disco, con datos, para probar los respaldos."""
    ruta = tmp_path / "datos" / "tienda.db"
    conexion = abrir_base_datos(ruta, con_datos_demo=False)
    with transaccion(conexion):
        cargar_datos_demo(conexion)
    conexion.close()
    return ruta


class TestRespaldos:
    def test_crea_una_copia_utilizable(self, base_en_disco, tmp_path) -> None:
        carpeta = tmp_path / "backups"
        respaldo = crear_respaldo(base_en_disco, carpeta)

        assert respaldo is not None and respaldo.exists()

        # Lo que importa de un respaldo no es que exista, sino que se pueda abrir y tenga
        # los datos dentro.
        copia = conectar(respaldo)
        assert repo_productos.contar(copia) > 0
        copia.close()

    def test_sin_base_de_datos_no_falla(self, tmp_path) -> None:
        assert crear_respaldo(tmp_path / "no-existe.db", tmp_path / "backups") is None

    def test_conserva_solo_los_ultimos(self, base_en_disco, tmp_path) -> None:
        carpeta = tmp_path / "backups"
        for _ in range(5):
            crear_respaldo(base_en_disco, carpeta, conservar=3)
            # Los nombres llevan la hora con segundos: sin esperar, se pisarían entre sí.
            time.sleep(1.05)

        assert len(listar_respaldos(carpeta)) == 3

    def test_guarda_ademas_el_ultimo_de_cada_dia(self, tmp_path) -> None:
        """Fase 22: dos respaldos por día (abrir y cerrar) no pueden dejar solo tres días."""
        from tienda_pos.db.respaldo import _limpiar_antiguos

        carpeta = tmp_path / "backups"
        carpeta.mkdir()
        for dia in range(1, 11):  # diez días, con respaldo al abrir y al cerrar
            for hora in ("090000", "210000"):
                (carpeta / f"tienda-202609{dia:02d}-{hora}.db").write_bytes(b"x")

        _limpiar_antiguos(carpeta, conservar=4, dias=7)

        nombres = [archivo.name for archivo in listar_respaldos(carpeta)]
        # Los cuatro más recientes, y el último de cada uno de los siete días más recientes.
        assert nombres[:4] == [
            "tienda-20260910-210000.db",
            "tienda-20260910-090000.db",
            "tienda-20260909-210000.db",
            "tienda-20260909-090000.db",
        ]
        assert nombres[4:] == [f"tienda-202609{d:02d}-210000.db" for d in range(8, 3, -1)]

    def test_un_fallo_al_respaldar_no_impide_arrancar(
        self, base_en_disco, tmp_path, monkeypatch, caplog
    ) -> None:
        # Se simula un disco lleno en mitad de la copia. sqlite3.Connection es un tipo de C
        # inmutable y no admite parches, así que se sustituye la función que la crea.
        from tienda_pos.db import respaldo as modulo

        class ConexionQueFalla:
            def backup(self, destino, **kwargs):
                raise sqlite3.OperationalError("disco lleno simulado")

            def close(self):
                pass

        monkeypatch.setattr(modulo, "conectar", lambda ruta: ConexionQueFalla())

        with caplog.at_level(logging.ERROR):
            resultado = crear_respaldo(base_en_disco, tmp_path / "backups")

        assert resultado is None
        assert "No se pudo crear el respaldo" in caplog.text
        # No debe quedar un archivo a medias haciéndose pasar por un respaldo válido.
        assert listar_respaldos(tmp_path / "backups") == []

    def test_los_respaldos_se_ordenan_del_mas_nuevo_al_mas_viejo(
        self, base_en_disco, tmp_path
    ) -> None:
        carpeta = tmp_path / "backups"
        crear_respaldo(base_en_disco, carpeta)
        time.sleep(1.05)
        reciente = crear_respaldo(base_en_disco, carpeta)

        assert listar_respaldos(carpeta)[0] == reciente


class TestBaseDeDatosHostil:
    def test_se_niega_a_abrir_una_version_mas_nueva(self, tmp_path) -> None:
        ruta = tmp_path / "futura.db"
        conexion = abrir_base_datos(ruta, con_datos_demo=False)
        conexion.execute("PRAGMA user_version = 99")
        conexion.close()

        with pytest.raises(RuntimeError, match="más nueva"):
            abrir_base_datos(ruta, con_datos_demo=False)

    def test_una_base_corrupta_da_un_error_claro(self, tmp_path) -> None:
        ruta = tmp_path / "rota.db"
        ruta.write_bytes(b"esto no es una base de datos de SQLite" * 10)

        with pytest.raises(sqlite3.DatabaseError):
            abrir_base_datos(ruta, con_datos_demo=False)

    def test_crea_la_carpeta_si_no_existe(self, tmp_path) -> None:
        ruta = tmp_path / "una" / "carpeta" / "nueva" / "tienda.db"
        conexion = abrir_base_datos(ruta, con_datos_demo=False)
        conexion.close()
        assert ruta.exists()

    def test_una_transaccion_interrumpida_no_deja_datos_a_medias(self, conexion, productos) -> None:
        with pytest.raises(sqlite3.IntegrityError):
            with transaccion(conexion):
                repo_productos.crear(
                    conexion,
                    type(productos["leche"])(
                        codigo_barras="7809999999999", nombre="Nuevo", precio_clp=100, stock=1
                    ),
                )
                # Precio negativo: la restricción CHECK del esquema lo rechaza.
                conexion.execute(
                    "INSERT INTO producto (codigo_barras, nombre, precio_clp) VALUES (?, ?, ?)",
                    ("7808888888888", "Imposible", -5),
                )

        assert repo_productos.obtener_por_codigo(conexion, "7809999999999") is None


class TestRegistroDeSucesos:
    def test_escribe_en_la_carpeta_indicada(self, tmp_path) -> None:
        logging_setup.reiniciar_para_pruebas()
        try:
            archivo = logging_setup.configurar(carpeta=tmp_path / "logs")
            logging.getLogger("prueba").warning("mensaje de prueba")

            assert archivo.exists()
            assert "mensaje de prueba" in archivo.read_text(encoding="utf-8")
        finally:
            logging_setup.reiniciar_para_pruebas()

    def test_configurar_dos_veces_no_duplica_los_mensajes(self, tmp_path) -> None:
        logging_setup.reiniciar_para_pruebas()
        try:
            archivo = logging_setup.configurar(carpeta=tmp_path / "logs")
            logging_setup.configurar(carpeta=tmp_path / "logs")
            logging.getLogger("prueba").warning("una sola vez")

            contenido = archivo.read_text(encoding="utf-8")
            assert contenido.count("una sola vez") == 1
        finally:
            logging_setup.reiniciar_para_pruebas()


class TestDetectorDeLector:
    def _teclear(self, detector: DetectorLector, cantidad: int, intervalo_ms: float) -> None:
        momento = 100.0
        for _ in range(cantidad):
            detector.registrar(momento)
            momento += intervalo_ms / 1000

    def test_reconoce_una_rafaga_de_pistola(self) -> None:
        detector = DetectorLector()
        self._teclear(detector, 13, intervalo_ms=8)
        assert detector.es_lector

    def test_no_confunde_a_una_persona_escribiendo(self) -> None:
        detector = DetectorLector()
        self._teclear(detector, 13, intervalo_ms=120)
        assert not detector.es_lector

    def test_no_se_fia_de_pocas_pulsaciones(self) -> None:
        # Tres teclas rapidísimas pueden ser un golpe de suerte al teclear.
        detector = DetectorLector()
        self._teclear(detector, 3, intervalo_ms=5)
        assert not detector.es_lector

    def test_una_sola_pausa_larga_descarta_el_lector(self) -> None:
        # La media seguiría siendo baja, pero una pistola no se detiene a mitad del código.
        detector = DetectorLector()
        detector.registrar(100.0)
        for i in range(1, 12):
            detector.registrar(100.0 + i * 0.008)
        detector.registrar(101.0)  # un segundo de pausa

        assert not detector.es_lector

    def test_reiniciar_lo_deja_como_nuevo(self) -> None:
        detector = DetectorLector()
        self._teclear(detector, 13, intervalo_ms=8)
        detector.reiniciar()

        assert detector.caracteres == 0
        assert not detector.es_lector


class TestManejadorGlobalDeErrores:
    def test_registra_el_error_y_no_lo_relanza(self, caplog, monkeypatch) -> None:
        from tienda_pos.ui import errores

        errores.reiniciar_contador()
        # Sin QApplication no se muestra diálogo; aquí solo se comprueba el registro.
        monkeypatch.setattr(errores, "_puede_mostrar_dialogo", lambda: False)

        try:
            raise ValueError("algo se rompió")
        except ValueError as error:
            with caplog.at_level(logging.CRITICAL):
                errores.manejar_excepcion(type(error), error, error.__traceback__)

        assert "Error no controlado" in caplog.text
        assert "algo se rompió" in caplog.text

    def test_deja_de_molestar_tras_varios_errores_seguidos(self) -> None:
        from tienda_pos.ui import errores

        errores.reiniciar_contador()
        permitidos = [errores._puede_mostrar_dialogo() for _ in range(6)]

        assert permitidos[: errores._MAX_DIALOGOS] == [True] * errores._MAX_DIALOGOS
        assert not any(permitidos[errores._MAX_DIALOGOS :])


class TestAutocomprobacion:
    def test_arranca_el_sistema_completo_y_da_correcto(self, app, tmp_path, monkeypatch) -> None:
        """La misma comprobación que se ejecuta sobre el .exe en el equipo del cliente."""
        from tienda_pos import app as modulo_app

        monkeypatch.setenv("TIENDA_POS_HOME", str(tmp_path / "datos"))
        logging_setup.reiniciar_para_pruebas()
        try:
            codigo = modulo_app.verificar()
        finally:
            logging_setup.reiniciar_para_pruebas()

        assert codigo == 0
        informe = (tmp_path / "datos" / "autocomprobacion.txt").read_text(encoding="utf-8")
        assert "RESULTADO: CORRECTO" in informe
        # Sin datos de ejemplo: la comprobación se ejecuta en el PC de la tienda, y sembrar ahí
        # el catálogo de muestra es como se mezcló con el real.
        assert "Productos en el catálogo: 0" in informe

    def test_informa_del_fallo_en_lugar_de_reventar(self, app, tmp_path, monkeypatch) -> None:
        from tienda_pos import app as modulo_app

        monkeypatch.setenv("TIENDA_POS_HOME", str(tmp_path / "datos"))

        def no_abre(*args, **kwargs):
            raise sqlite3.OperationalError("base inaccesible simulada")

        monkeypatch.setattr(modulo_app, "abrir_base_datos", no_abre)
        logging_setup.reiniciar_para_pruebas()
        try:
            codigo = modulo_app.verificar()
        finally:
            logging_setup.reiniciar_para_pruebas()

        assert codigo == 1
        informe = (tmp_path / "datos" / "autocomprobacion.txt").read_text(encoding="utf-8")
        assert "RESULTADO: FALLO" in informe
