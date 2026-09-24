"""Ventana de configuración: la rueda dentada de la barra superior.

Aquí solo entran ajustes que cambian cómo se ve o cómo suena el programa en este equipo.
Todo lo que afecte al dinero o a los datos (permitir stock negativo, precios, usuarios) se
queda fuera a propósito: son decisiones del dueño de la tienda, no del turno de caja, y una
casilla en un diálogo es demasiado fácil de marcar sin querer.

El tema y el tamaño de letra se aplican en cuanto se eligen, sin esperar a Aceptar, porque un
color o un tamaño hay que verlos para decidirlos. Si se cancela, se devuelve lo que había.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .. import config
from ..services.preferencias import (
    TAMANO_GRANDE,
    TAMANO_MUY_GRANDE,
    TAMANO_NORMAL,
    TEMA_CLARO,
    TEMA_OSCURO,
    Preferencias,
)
from ..services import preferencias as servicio_preferencias
from . import dialogos, movimiento
from .widgets.desplegable import Desplegable

_logger = logging.getLogger(__name__)

_NOMBRE_TEMA = {TEMA_CLARO: "Claro", TEMA_OSCURO: "Oscuro"}
_NOMBRE_TAMANO = {
    TAMANO_NORMAL: "Normal",
    TAMANO_GRANDE: "Grande",
    TAMANO_MUY_GRANDE: "Muy grande",
}


class DialogoConfiguracion(QDialog):
    """Ajustes de la instalación.

    Recibe `al_previsualizar_tema` y `al_previsualizar_letra` para poder pintar el tema y el
    tamaño de letra mientras se eligen. El diálogo no guarda nada por su cuenta: devuelve las
    preferencias elegidas y quien lo abrió decide qué hacer con ellas.
    """

    def __init__(
        self,
        preferencias: Preferencias,
        padre: QWidget | None = None,
        al_previsualizar_tema: Callable[[str], None] | None = None,
        al_previsualizar_letra: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(padre)
        movimiento.aparecer_al_abrir(self)
        self.setWindowTitle("Configuración")
        self.setMinimumWidth(460)

        self._originales = Preferencias(**vars_de(preferencias))
        self._previsualizar = al_previsualizar_tema
        self._previsualizar_letra = al_previsualizar_letra

        columna = QVBoxLayout(self)
        columna.setContentsMargins(26, 24, 26, 20)
        columna.setSpacing(14)

        titulo = QLabel("Configuración")
        titulo.setObjectName("tituloPantalla")
        columna.addWidget(titulo)

        subtitulo = QLabel("Estos ajustes se guardan en este equipo.")
        subtitulo.setObjectName("subtitulo")
        columna.addWidget(subtitulo)

        formulario = QFormLayout()
        formulario.setSpacing(10)

        self.combo_tema = Desplegable()
        for clave in (TEMA_CLARO, TEMA_OSCURO):
            self.combo_tema.addItem(_NOMBRE_TEMA[clave], clave)
        self.combo_tema.setCurrentIndex(self.combo_tema.findData(preferencias.tema))
        self.combo_tema.currentIndexChanged.connect(self._cambiar_tema)
        formulario.addRow("Tema", self.combo_tema)

        self.combo_letra = Desplegable()
        for clave in (TAMANO_NORMAL, TAMANO_GRANDE, TAMANO_MUY_GRANDE):
            self.combo_letra.addItem(_NOMBRE_TAMANO[clave], clave)
        self.combo_letra.setCurrentIndex(self.combo_letra.findData(preferencias.tamano_texto))
        self.combo_letra.setToolTip(
            "Agranda letras y números en todo el programa, para leer la pantalla desde el "
            "otro lado del mostrador."
        )
        self.combo_letra.currentIndexChanged.connect(self._cambiar_letra)
        formulario.addRow("Tamaño de letra", self.combo_letra)

        columna.addLayout(formulario)

        self.casilla_sonido = QCheckBox("Avisar con un sonido al escanear")
        self.casilla_sonido.setChecked(preferencias.sonido)
        self.casilla_sonido.setToolTip(
            "El pitido confirma que el producto entró sin tener que mirar la pantalla."
        )
        columna.addWidget(self.casilla_sonido)

        self.casilla_confirmar = QCheckBox("Pedir confirmación antes de cobrar")
        self.casilla_confirmar.setChecked(preferencias.confirmar_cobro)
        self.casilla_confirmar.setToolTip(
            "Desactívelo solo si el cajero tiene mucha práctica: sin confirmación, una venta "
            "se cierra con una sola tecla."
        )
        columna.addWidget(self.casilla_confirmar)

        self.casilla_atajos = QCheckBox("Mostrar la barra de atajos abajo")
        self.casilla_atajos.setChecked(preferencias.mostrar_atajos)
        columna.addWidget(self.casilla_atajos)

        self.casilla_animaciones = QCheckBox("Animar los cambios en pantalla")
        self.casilla_animaciones.setChecked(preferencias.animaciones)
        self.casilla_animaciones.setToolTip(
            "Fundidos cortos en avisos y ventanas, un destello en la línea que cambia y el "
            "menú que se recoge. Apáguelo si el equipo va lento o si prefiere que todo sea "
            "inmediato."
        )
        columna.addWidget(self.casilla_animaciones)

        columna.addWidget(self._tarjeta_sistema())

        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botones.button(QDialogButtonBox.StandardButton.Ok).setText("Guardar")
        botones.button(QDialogButtonBox.StandardButton.Ok).setObjectName("botonAccion")
        botones.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        columna.addWidget(botones)

    # ------------------------------------------------------------------ construcción

    def _tarjeta_sistema(self) -> QWidget:
        """Datos que siempre hacen falta cuando algo va mal: versión y dónde están los datos."""
        tarjeta = QFrame()
        tarjeta.setObjectName("tarjeta")
        interior = QVBoxLayout(tarjeta)
        interior.setContentsMargins(16, 14, 16, 14)
        interior.setSpacing(6)

        version = QLabel(f"{config.NOMBRE_COMERCIAL} {config.VERSION}")
        version.setObjectName("subtitulo")
        interior.addWidget(version)

        ruta = QLabel(str(config.directorio_datos()))
        ruta.setObjectName("subtitulo")
        ruta.setWordWrap(True)
        ruta.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        interior.addWidget(ruta)

        fila = QHBoxLayout()
        fila.addStretch()
        boton = QPushButton("Abrir carpeta de datos")
        boton.clicked.connect(self._abrir_carpeta)
        fila.addWidget(boton)
        interior.addLayout(fila)
        return tarjeta

    # ------------------------------------------------------------------ acciones

    def _cambiar_tema(self) -> None:
        if self._previsualizar is not None:
            self._previsualizar(self.tema)

    def _cambiar_letra(self) -> None:
        if self._previsualizar_letra is not None:
            self._previsualizar_letra(self.tamano_texto)

    def _abrir_carpeta(self) -> None:
        """Abre la carpeta de datos en el explorador de archivos.

        Es lo primero que se pide por teléfono cuando hay que recuperar un respaldo o mandar
        un registro, y dictarle la ruta a alguien que no sabe qué es %LOCALAPPDATA% no
        funciona.
        """
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        carpeta = config.directorio_datos()
        try:
            config.asegurar_directorios()
        except OSError:
            _logger.warning("No se pudo crear la carpeta de datos", exc_info=True)

        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(carpeta))):
            dialogos.mostrar_error(
                self, f"No se pudo abrir la carpeta.\n\nEstá en:\n{carpeta}"
            )

    def reject(self) -> None:
        # Cancelar debe deshacer también la previsualización del tema y de la letra; si no,
        # el ajuste quedaría aplicado pero sin guardar, y volvería al reiniciar sin explicación.
        if self._previsualizar is not None and self.tema != self._originales.tema:
            self._previsualizar(self._originales.tema)
        if (
            self._previsualizar_letra is not None
            and self.tamano_texto != self._originales.tamano_texto
        ):
            self._previsualizar_letra(self._originales.tamano_texto)
        super().reject()

    # ------------------------------------------------------------------ resultado

    @property
    def tema(self) -> str:
        return self.combo_tema.currentData()

    @property
    def tamano_texto(self) -> str:
        return self.combo_letra.currentData()

    @property
    def preferencias(self) -> Preferencias:
        """Lo elegido en el diálogo, listo para guardarse."""
        return Preferencias(
            tema=self.tema,
            sonido=self.casilla_sonido.isChecked(),
            confirmar_cobro=self.casilla_confirmar.isChecked(),
            mostrar_atajos=self.casilla_atajos.isChecked(),
            animaciones=self.casilla_animaciones.isChecked(),
            tamano_texto=self.tamano_texto,
            # El plegado no se elige aquí, pero se arrastra: si no, guardar cualquier ajuste
            # desplegaría la barra por su cuenta.
            barra_lateral_plegada=self._originales.barra_lateral_plegada,
        ).normalizar()

    # ------------------------------------------------------------------ uso

    @staticmethod
    def abrir(
        preferencias: Preferencias,
        padre: QWidget | None = None,
        al_previsualizar_tema: Callable[[str], None] | None = None,
        al_previsualizar_letra: Callable[[str], None] | None = None,
    ) -> Preferencias | None:
        """Muestra el diálogo y guarda el resultado. Devuelve None si se canceló."""
        dialogo = DialogoConfiguracion(
            preferencias, padre, al_previsualizar_tema, al_previsualizar_letra
        )
        if not dialogo.exec():
            return None

        elegidas = dialogo.preferencias
        if not servicio_preferencias.guardar(elegidas):
            dialogos.mostrar_error(
                padre,
                "Los ajustes se aplicaron, pero no se pudieron guardar en el disco.\n"
                "Volverán a los anteriores al reiniciar el programa.",
            )
        return elegidas


def vars_de(preferencias: Preferencias) -> dict:
    """Copia los campos de unas preferencias. `vars()` no sirve con dataclasses de slots."""
    from dataclasses import asdict

    return asdict(preferencias)
