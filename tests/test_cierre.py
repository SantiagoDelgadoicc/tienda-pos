"""Pruebas de la fase 18: el cierre diario por caja (D-035), sin interfaz.

Lo que pidió el cliente, por caja y por día: cuánto se vendió en efectivo, en débito y en
crédito, qué empleado vendió cuánto, y la lista de ventas con sus productos. Lo que más se cuida
aquí es que **las tres sumas cuadren** —por medio, por empleado y el total—, que cada caja vea
solo lo suyo aunque el servidor escriba las ventas de las dos, y que el día de la tienda sea el
mismo rango en el cierre y en las ventas del día, también el día que cambie la hora de corte.
"""

from __future__ import annotations

import json
import socket
from datetime import date, datetime

import pytest

from tienda_pos import config
from tienda_pos.db.connection import transaccion
from tienda_pos.db.inicio import abrir_base_datos
from tienda_pos.domain.models import CierreCaja, MedioPago, Producto, Rol
from tienda_pos.red import protocolo
from tienda_pos.repositories import productos as repo_productos
from tienda_pos.repositories import ventas as repo_ventas
from tienda_pos.services import auth, reportes
from tienda_pos.services import venta as servicio_venta

#: Un día cualquiera de la tienda, para no depender de la hora a la que corren las pruebas.
DIA = date(2026, 9, 18)


@pytest.fixture
def surtido(conexion) -> dict[str, Producto]:
    """Dos productos con stock de sobra: aquí se vende muchas veces y no se prueba el stock."""
    definiciones = {
        "pisco": Producto(codigo_barras="7801234100016", nombre="Pisco 35° 1 L", precio_clp=6990, stock=500),
        "hielo": Producto(codigo_barras="7801234100023", nombre="Hielo 2 kg", precio_clp=1500, stock=500),
    }
    with transaccion(conexion):
        for producto in definiciones.values():
            repo_productos.crear(conexion, producto)
    return definiciones


@pytest.fixture
def empleados(conexion):
    """Dos cajeras que venden en la misma caja el mismo día: el caso literal del cliente."""
    with transaccion(conexion):
        return (
            auth.crear_usuario(conexion, "Marta", Rol.CAJERO, "5706"),
            auth.crear_usuario(conexion, "Rosa", Rol.CAJERO, "8342"),
        )


def _vender(
    conexion,
    surtido,
    *,
    caja: str | None,
    usuario=None,
    medio: MedioPago | None = MedioPago.EFECTIVO,
    cuando: datetime | None = None,
    pisco: int = 1,
    hielo: int = 0,
):
    """Cobra una venta y la lleva a la hora que se diga.

    Pasa por el servicio de verdad, para que la venta tenga sus líneas, su folio y su total
    como las de la tienda; la hora se corrige después, porque el servicio pone la del reloj.
    """
    carrito = servicio_venta.Carrito()
    for _ in range(pisco):
        carrito.agregar(surtido["pisco"])
    for _ in range(hielo):
        carrito.agregar(surtido["hielo"])
    venta = servicio_venta.cerrar_venta(conexion, carrito, usuario, caja=caja, medio_pago=medio)
    cuando = cuando or datetime.combine(DIA, datetime.min.time()).replace(hour=12)
    with transaccion(conexion):
        conexion.execute(
            "UPDATE venta SET fecha_hora = ? WHERE id = ?",
            (cuando.strftime("%Y-%m-%d %H:%M:%S"), venta.id),
        )
    venta.fecha_hora = cuando
    return venta


def _a_las(hora: int, minuto: int = 0, segundo: int = 0, dia: date = DIA) -> datetime:
    return datetime(dia.year, dia.month, dia.day, hora, minuto, segundo)


def _cuadra(cierre: CierreCaja) -> None:
    """Las tres cifras del cierre tienen que coincidir. Es la comprobación que haría el dueño
    con su cuaderno, y la que D-035 promete por construcción."""
    assert sum(f.total_clp for f in cierre.por_medio) == cierre.total_clp
    assert sum(f.total_clp for f in cierre.por_empleado) == cierre.total_clp
    assert sum(f.ventas for f in cierre.por_medio) == cierre.cantidad_ventas
    assert sum(f.ventas for f in cierre.por_empleado) == cierre.cantidad_ventas
    assert sum(f.articulos for f in cierre.por_empleado) == cierre.articulos
    assert cierre.total_clp == sum(v.total_clp for v in cierre.ventas)


class TestCierreVacio:
    def test_una_caja_sin_ventas_da_ceros_y_no_falla(self, conexion) -> None:
        cierre = reportes.cierre_de_caja(conexion, DIA, "Caja 1")

        assert cierre.dia == DIA and cierre.caja == "Caja 1"
        assert cierre.ventas == [] and cierre.cajas_del_dia == []
        assert (cierre.total_clp, cierre.cantidad_ventas, cierre.articulos) == (0, 0, 0)
        assert cierre.por_empleado == []
        _cuadra(cierre)

    def test_los_tres_medios_salen_aunque_esten_en_cero(self, conexion) -> None:
        # "Débito $0" también es información: que no aparezca haría pensar que falta algo.
        cierre = reportes.cierre_de_caja(conexion, DIA, "Caja 1")
        assert [(f.medio_pago, f.ventas, f.total_clp) for f in cierre.por_medio] == [
            (MedioPago.EFECTIVO, 0, 0),
            (MedioPago.DEBITO, 0, 0),
            (MedioPago.CREDITO, 0, 0),
        ]

    def test_sin_dia_es_el_dia_de_la_tienda(self, conexion) -> None:
        assert reportes.cierre_de_caja(conexion, None, "Caja 1").dia == reportes.dia_comercial()


class TestCadaCajaLoSuyo:
    def test_dos_cajas_el_mismo_dia(self, conexion, surtido, empleados) -> None:
        marta, rosa = empleados
        _vender(conexion, surtido, caja="Caja 1", usuario=marta, pisco=1)
        _vender(conexion, surtido, caja="Caja 1", usuario=marta, pisco=2)
        _vender(conexion, surtido, caja="Caja 2", usuario=rosa, hielo=3, pisco=0)

        uno = reportes.cierre_de_caja(conexion, DIA, "Caja 1")
        dos = reportes.cierre_de_caja(conexion, DIA, "Caja 2")

        assert {v.caja for v in uno.ventas} == {"Caja 1"}
        assert {v.caja for v in dos.ventas} == {"Caja 2"}
        assert (uno.cantidad_ventas, uno.total_clp) == (2, 3 * 6990)
        assert (dos.cantidad_ventas, dos.total_clp) == (1, 3 * 1500)
        # Juntas, las dos cajas son el día entero de la tienda: ni se pierde ni se repite nada.
        dia = repo_ventas.resumen_del_dia(conexion, DIA)
        assert uno.total_clp + dos.total_clp == dia["total_clp"]
        assert uno.cantidad_ventas + dos.cantidad_ventas == dia["cantidad_ventas"]
        assert uno.cajas_del_dia == dos.cajas_del_dia == ["Caja 1", "Caja 2"]

    def test_una_caja_que_no_vendio_ese_dia_no_ve_las_de_la_otra(self, conexion, surtido) -> None:
        _vender(conexion, surtido, caja="Caja 2")
        cierre = reportes.cierre_de_caja(conexion, DIA, "Caja 1")
        assert cierre.ventas == []
        assert cierre.cajas_del_dia == ["Caja 2"]

    def test_las_ventas_sin_caja_solo_salen_en_su_grupo(self, conexion, surtido) -> None:
        # Las anteriores a la fase 16 no saben de qué caja son (D-033): ni se reparten ni se
        # le cargan a la principal.
        antigua = _vender(conexion, surtido, caja=None, pisco=2)
        _vender(conexion, surtido, caja="Caja 1")

        sin_caja = reportes.cierre_de_caja(conexion, DIA, None)
        caja_1 = reportes.cierre_de_caja(conexion, DIA, "Caja 1")

        assert [v.id for v in sin_caja.ventas] == [antigua.id]
        assert antigua.id not in {v.id for v in caja_1.ventas}
        # La caja "sin caja" va al final de la lista, detrás de las que tienen nombre.
        assert sin_caja.cajas_del_dia == ["Caja 1", None]

    def test_el_nombre_de_la_caja_se_compara_tal_cual(self, conexion, surtido) -> None:
        # Si los dos PC se llamaran casi igual, son dos cajas. No se adivina que son la misma.
        _vender(conexion, surtido, caja="Caja 1")
        _vender(conexion, surtido, caja="caja 1")
        assert reportes.cierre_de_caja(conexion, DIA, "Caja 1").cantidad_ventas == 1


class TestEmpleados:
    def test_dos_empleados_en_la_misma_caja(self, conexion, surtido, empleados) -> None:
        marta, rosa = empleados
        _vender(conexion, surtido, caja="Caja 1", usuario=marta, pisco=1, cuando=_a_las(9))
        _vender(conexion, surtido, caja="Caja 1", usuario=rosa, pisco=2, hielo=1, cuando=_a_las(15))
        _vender(conexion, surtido, caja="Caja 1", usuario=marta, hielo=2, pisco=0, cuando=_a_las(10))

        cierre = reportes.cierre_de_caja(conexion, DIA, "Caja 1")
        filas = [(f.nombre, f.ventas, f.articulos, f.total_clp) for f in cierre.por_empleado]

        # De más a menos vendido: es lo que el dueño mira primero.
        assert filas == [
            ("Rosa", 1, 3, 2 * 6990 + 1500),
            ("Marta", 2, 3, 6990 + 2 * 1500),
        ]
        _cuadra(cierre)

    def test_las_ventas_sin_usuario_forman_su_propia_fila(self, conexion, surtido, empleados) -> None:
        marta, _ = empleados
        _vender(conexion, surtido, caja="Caja 1", usuario=marta)
        _vender(conexion, surtido, caja="Caja 1", usuario=None, pisco=3)

        cierre = reportes.cierre_de_caja(conexion, DIA, "Caja 1")
        sin_usuario = [f for f in cierre.por_empleado if f.usuario_id is None]

        assert len(sin_usuario) == 1
        assert (sin_usuario[0].nombre, sin_usuario[0].ventas) == (None, 1)
        assert sin_usuario[0].total_clp == 3 * 6990
        _cuadra(cierre)

    def test_un_empleado_dado_de_baja_sigue_apareciendo_con_sus_ventas(
        self, conexion, surtido, empleados, admin
    ) -> None:
        # La baja no borra sus ventas (fase 15), y el cierre de ese día tiene que seguir
        # diciendo quién las hizo.
        marta, _ = empleados
        _vender(conexion, surtido, caja="Caja 1", usuario=marta)
        auth.desactivar_usuario(conexion, admin, marta.id)
        filas = reportes.cierre_de_caja(conexion, DIA, "Caja 1").por_empleado
        assert [f.nombre for f in filas] == ["Marta"]


class TestMedios:
    def test_cada_medio_suma_lo_suyo(self, conexion, surtido, empleados) -> None:
        marta, rosa = empleados
        _vender(conexion, surtido, caja="Caja 1", usuario=marta, medio=MedioPago.EFECTIVO, pisco=1)
        _vender(conexion, surtido, caja="Caja 1", usuario=rosa, medio=MedioPago.DEBITO, pisco=2)
        _vender(conexion, surtido, caja="Caja 1", usuario=marta, medio=MedioPago.DEBITO, hielo=1, pisco=0)
        _vender(conexion, surtido, caja="Caja 1", usuario=rosa, medio=MedioPago.CREDITO, hielo=2, pisco=0)

        cierre = reportes.cierre_de_caja(conexion, DIA, "Caja 1")
        assert [(f.medio_pago, f.ventas, f.total_clp) for f in cierre.por_medio] == [
            (MedioPago.EFECTIVO, 1, 6990),
            (MedioPago.DEBITO, 2, 2 * 6990 + 1500),
            (MedioPago.CREDITO, 1, 2 * 1500),
        ]
        _cuadra(cierre)

    def test_sin_registrar_solo_aparece_si_hay_ventas_asi_y_al_final(self, conexion, surtido) -> None:
        _vender(conexion, surtido, caja="Caja 1", medio=MedioPago.CREDITO)
        assert [f.medio_pago for f in reportes.cierre_de_caja(conexion, DIA, "Caja 1").por_medio] == [
            MedioPago.EFECTIVO, MedioPago.DEBITO, MedioPago.CREDITO,
        ]

        # Una venta de antes de la fase 17: no se sabe con qué se pagó, y no se supone efectivo.
        _vender(conexion, surtido, caja="Caja 1", medio=None, pisco=2)
        cierre = reportes.cierre_de_caja(conexion, DIA, "Caja 1")
        assert [(f.medio_pago, f.ventas, f.total_clp) for f in cierre.por_medio] == [
            (MedioPago.EFECTIVO, 0, 0),
            (MedioPago.DEBITO, 0, 0),
            (MedioPago.CREDITO, 1, 6990),
            (None, 1, 2 * 6990),
        ]
        _cuadra(cierre)

    def test_las_tres_sumas_cuadran_en_un_dia_revuelto(self, conexion, surtido, empleados) -> None:
        # Todo mezclado a la vez: dos empleados, alguien sin usuario, los cuatro "medios" y una
        # venta con descuento. Si alguna de las tres cifras se calculara por su lado, aquí se
        # despegaría.
        marta, rosa = empleados
        medios = [MedioPago.EFECTIVO, MedioPago.DEBITO, MedioPago.CREDITO, None]
        usuarios = [marta, rosa, None]
        for i in range(12):
            _vender(
                conexion, surtido, caja="Caja 1", usuario=usuarios[i % 3], medio=medios[i % 4],
                pisco=i % 3, hielo=1 + i % 2, cuando=_a_las(8 + i),
            )
        carrito = servicio_venta.Carrito()
        carrito.agregar(surtido["pisco"])
        carrito.aplicar_descuento_monto(990)
        servicio_venta.cerrar_venta(conexion, carrito, rosa, caja="Caja 1")

        cierre = reportes.cierre_de_caja(conexion, reportes.dia_comercial(), "Caja 1")
        cierre_dia = reportes.cierre_de_caja(conexion, DIA, "Caja 1")
        assert cierre.cantidad_ventas == 1 and cierre.total_clp == 6000
        assert cierre_dia.cantidad_ventas == 12
        _cuadra(cierre)
        _cuadra(cierre_dia)


class TestQueEntra:
    def test_las_anuladas_no_cuentan(self, conexion, surtido) -> None:
        buena = _vender(conexion, surtido, caja="Caja 1")
        anulada = _vender(conexion, surtido, caja="Caja 1", pisco=5)
        solo_anulada = _vender(conexion, surtido, caja="Caja 2")
        with transaccion(conexion):
            conexion.execute(
                "UPDATE venta SET estado = 'anulada' WHERE id IN (?, ?)", (anulada.id, solo_anulada.id)
            )

        cierre = reportes.cierre_de_caja(conexion, DIA, "Caja 1")
        assert [v.id for v in cierre.ventas] == [buena.id]
        assert cierre.total_clp == 6990
        # Una caja cuyo único movimiento fue una anulada no vendió ese día.
        assert cierre.cajas_del_dia == ["Caja 1"]

    def test_cada_venta_trae_sus_productos(self, conexion, surtido) -> None:
        # Lo pidió el cliente: "la lista de las ventas con los productos de cada una".
        _vender(conexion, surtido, caja="Caja 1", pisco=2, hielo=1)
        _vender(conexion, surtido, caja="Caja 1", pisco=0, hielo=4)

        ventas = reportes.cierre_de_caja(conexion, DIA, "Caja 1").ventas
        productos = sorted(
            [(linea.nombre, linea.cantidad) for linea in venta.lineas] for venta in ventas
        )
        assert productos == [
            [("Hielo 2 kg", 4)],
            [("Pisco 35° 1 L", 2), ("Hielo 2 kg", 1)],
        ]

    def test_de_la_mas_reciente_a_la_mas_antigua(self, conexion, surtido) -> None:
        temprano = _vender(conexion, surtido, caja="Caja 1", cuando=_a_las(9, 15))
        tarde = _vender(conexion, surtido, caja="Caja 1", cuando=_a_las(21, 40))
        medio = _vender(conexion, surtido, caja="Caja 1", cuando=_a_las(14))
        ids = [v.id for v in reportes.cierre_de_caja(conexion, DIA, "Caja 1").ventas]
        assert ids == [tarde.id, medio.id, temprano.id]


class TestBordesDelDia:
    def test_con_corte_a_medianoche(self, conexion, surtido) -> None:
        dentro = [
            _vender(conexion, surtido, caja="Caja 1", cuando=_a_las(0, 0, 0)),
            _vender(conexion, surtido, caja="Caja 1", cuando=_a_las(23, 59, 59)),
        ]
        _vender(conexion, surtido, caja="Caja 1", cuando=_a_las(23, 59, 59, dia=date(2026, 9, 17)))
        _vender(conexion, surtido, caja="Caja 1", cuando=_a_las(0, 0, 0, dia=date(2026, 9, 19)))

        ids = {v.id for v in reportes.cierre_de_caja(conexion, DIA, "Caja 1").ventas}
        assert ids == {v.id for v in dentro}

    def test_con_corte_a_las_seis_la_noche_es_del_dia_anterior(
        self, conexion, surtido, monkeypatch
    ) -> None:
        # La pregunta H10: en una botillería la noche del viernes sigue siendo viernes.
        monkeypatch.setattr(config, "HORA_CORTE_DIA", 6)
        viernes = DIA
        sabado = date(2026, 9, 19)
        del_viernes = [
            _vender(conexion, surtido, caja="Caja 1", cuando=_a_las(6, 0, 0)),
            _vender(conexion, surtido, caja="Caja 1", cuando=_a_las(23, 30)),
            _vender(conexion, surtido, caja="Caja 1", cuando=_a_las(1, 30, dia=sabado)),
            _vender(conexion, surtido, caja="Caja 1", cuando=_a_las(5, 59, 59, dia=sabado)),
        ]
        del_jueves = _vender(conexion, surtido, caja="Caja 1", cuando=_a_las(5, 59, 59))
        del_sabado = _vender(conexion, surtido, caja="Caja 1", cuando=_a_las(6, 0, 0, dia=sabado))

        assert {v.id for v in reportes.cierre_de_caja(conexion, viernes, "Caja 1").ventas} == {
            v.id for v in del_viernes
        }
        assert [v.id for v in reportes.cierre_de_caja(conexion, date(2026, 9, 17), "Caja 1").ventas] == [
            del_jueves.id
        ]
        assert [v.id for v in reportes.cierre_de_caja(conexion, sabado, "Caja 1").ventas] == [
            del_sabado.id
        ]

    def test_las_ventas_del_dia_usan_el_mismo_rango_que_el_cierre(
        self, conexion, surtido, monkeypatch
    ) -> None:
        # Si una pantalla contara la noche como del viernes y la otra como del sábado, el dueño
        # tendría dos cifras distintas para el mismo día.
        monkeypatch.setattr(config, "HORA_CORTE_DIA", 6)
        _vender(conexion, surtido, caja="Caja 1", cuando=_a_las(22))
        _vender(conexion, surtido, caja="Caja 2", cuando=_a_las(2, dia=date(2026, 9, 19)), pisco=2)
        _vender(conexion, surtido, caja="Caja 2", cuando=_a_las(7, dia=date(2026, 9, 19)), pisco=4)

        cierres = [reportes.cierre_de_caja(conexion, DIA, caja) for caja in ("Caja 1", "Caja 2")]
        resumen = reportes.resumen_del_dia(conexion, DIA)
        ventas_del_dia = reportes.ventas_del_dia(conexion, DIA)

        assert sum(c.total_clp for c in cierres) == resumen["total_clp"] == 3 * 6990
        assert sorted(v.id for c in cierres for v in c.ventas) == sorted(v.id for v in ventas_del_dia)
        assert cierres[0].cajas_del_dia == ["Caja 1", "Caja 2"]

    @pytest.mark.parametrize(
        ("corte", "ahora", "dia"),
        [
            (0, datetime(2026, 9, 19, 1, 30), date(2026, 9, 19)),
            (6, datetime(2026, 9, 19, 1, 30), date(2026, 9, 18)),
            (6, datetime(2026, 9, 19, 5, 59, 59), date(2026, 9, 18)),
            (6, datetime(2026, 9, 19, 6, 0), date(2026, 9, 19)),
            (6, datetime(2026, 9, 19, 23, 59), date(2026, 9, 19)),
            # A primera hora del mes y del año también retrocede bien.
            (6, datetime(2027, 1, 1, 3, 0), date(2026, 12, 31)),
        ],
    )
    def test_dia_comercial(self, monkeypatch, corte, ahora, dia) -> None:
        monkeypatch.setattr(config, "HORA_CORTE_DIA", corte)
        assert reportes.dia_comercial(ahora) == dia

    def test_el_rango_del_dia_empieza_en_la_hora_de_corte(self, monkeypatch) -> None:
        assert repo_ventas.rango_del_dia(DIA) == ("2026-09-18 00:00:00", "2026-09-19 00:00:00")
        monkeypatch.setattr(config, "HORA_CORTE_DIA", 6)
        assert repo_ventas.rango_del_dia(DIA) == ("2026-09-18 06:00:00", "2026-09-19 06:00:00")


class TestProtocolo:
    def test_ida_y_vuelta(self, conexion, surtido, empleados) -> None:
        marta, _ = empleados
        _vender(conexion, surtido, caja="Caja 1", usuario=marta, medio=MedioPago.DEBITO, hielo=2)
        _vender(conexion, surtido, caja="Caja 1", usuario=None, medio=None)
        _vender(conexion, surtido, caja=None)
        original = reportes.cierre_de_caja(conexion, DIA, "Caja 1")

        # Pasando por texto, como por la red: si algo no fuera JSON, fallaría aquí.
        vuelta = protocolo.a_cierre(json.loads(json.dumps(protocolo.de_cierre(original))))

        assert (vuelta.dia, vuelta.caja, vuelta.cajas_del_dia) == (DIA, "Caja 1", ["Caja 1", None])
        assert [v.id for v in vuelta.ventas] == [v.id for v in original.ventas]
        assert [[(l.nombre, l.cantidad) for l in v.lineas] for v in vuelta.ventas] == [
            [(l.nombre, l.cantidad) for l in v.lineas] for v in original.ventas
        ]
        assert vuelta.por_medio == original.por_medio
        assert vuelta.por_empleado == original.por_empleado
        assert vuelta.total_clp == original.total_clp

    def test_el_grupo_sin_caja_viaja_como_nulo(self, conexion, surtido) -> None:
        _vender(conexion, surtido, caja=None)
        datos = json.loads(json.dumps(protocolo.de_cierre(reportes.cierre_de_caja(conexion, DIA, None))))
        assert datos["caja"] is None
        assert protocolo.a_cierre(datos).caja is None

    def test_los_totales_no_viajan(self, conexion, surtido) -> None:
        # Se recalculan al otro lado de las mismas ventas: no puede llegar una cifra que no
        # cuadre con la lista que llega con ella.
        _vender(conexion, surtido, caja="Caja 1")
        datos = protocolo.de_cierre(reportes.cierre_de_caja(conexion, DIA, "Caja 1"))
        assert set(datos) == {"dia", "caja", "ventas", "cajas_del_dia"}

    def test_un_mensaje_incompleto_da_un_cierre_vacio(self) -> None:
        cierre = protocolo.a_cierre({"dia": "2026-09-18"})
        assert (cierre.dia, cierre.caja, cierre.ventas, cierre.cajas_del_dia) == (DIA, None, [], [])


def _puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestPorLaRed:
    @pytest.fixture
    def dos_cajas(self):
        """Un servidor de verdad, que es la caja "Principal", y la "Secundaria" conectada a él."""
        from tienda_pos.red.cliente import SesionRemota
        from tienda_pos.red.servidor import ServidorTienda
        from tienda_pos.red.sesion import SesionLocal

        conexion = abrir_base_datos(":memory:", con_datos_demo=True, compartida_entre_hilos=True)
        with transaccion(conexion):
            marta = auth.crear_usuario(conexion, "Marta", Rol.CAJERO, "5706")
            rosa = auth.crear_usuario(conexion, "Rosa", Rol.CAJERO, "8342")
        principal = SesionLocal(conexion, caja="Principal")
        puerto = _puerto_libre()
        with ServidorTienda(principal, host="127.0.0.1", puerto=puerto):
            yield principal, SesionRemota("127.0.0.1", puerto, caja="Secundaria"), marta, rosa
        conexion.close()

    @staticmethod
    def _cobrar(sesion, usuario, intento: str, medio: MedioPago, *indices: int):
        from tienda_pos.db.seed import codigo_demo

        carrito = servicio_venta.Carrito()
        for indice in indices:
            carrito.agregar(sesion.consultar_por_codigo(codigo_demo(indice)))
        return sesion.cerrar_venta(carrito, usuario, intento, medio_pago=medio)

    def test_desde_la_secundaria_se_ve_el_cierre_de_la_principal(self, dos_cajas) -> None:
        principal, secundaria, marta, rosa = dos_cajas
        en_principal = [
            self._cobrar(principal, marta, "p1", MedioPago.EFECTIVO, 0, 1),
            self._cobrar(principal, rosa, "p2", MedioPago.CREDITO, 2),
        ]
        en_secundaria = self._cobrar(secundaria, rosa, "s1", MedioPago.DEBITO, 3)

        visto_de_lejos = secundaria.cierre_de_caja(None, "Principal")
        visto_de_cerca = principal.cierre_de_caja(None, "Principal")

        assert sorted(v.id for v in visto_de_lejos.ventas) == sorted(v.id for v in en_principal)
        assert en_secundaria.id not in {v.id for v in visto_de_lejos.ventas}
        assert visto_de_lejos.por_medio == visto_de_cerca.por_medio
        assert visto_de_lejos.por_empleado == visto_de_cerca.por_empleado
        assert visto_de_lejos.cajas_del_dia == ["Principal", "Secundaria"]
        assert all(v.lineas for v in visto_de_lejos.ventas)
        _cuadra(visto_de_lejos)

    def test_la_secundaria_ve_lo_suyo_con_sus_empleados(self, dos_cajas) -> None:
        principal, secundaria, marta, rosa = dos_cajas
        self._cobrar(principal, marta, "p1", MedioPago.EFECTIVO, 0)
        uno = self._cobrar(secundaria, marta, "s1", MedioPago.DEBITO, 1)
        dos = self._cobrar(secundaria, rosa, "s2", MedioPago.EFECTIVO, 2)

        cierre = secundaria.cierre_de_caja(None, "Secundaria")

        assert cierre.dia == reportes.dia_comercial()
        assert sorted(v.id for v in cierre.ventas) == sorted([uno.id, dos.id])
        assert sorted(f.nombre for f in cierre.por_empleado) == ["Marta", "Rosa"]
        _cuadra(cierre)
