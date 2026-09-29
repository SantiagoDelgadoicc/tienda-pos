"""Movimiento: duraciones, curvas y las animaciones que comparten las pantallas.

Una caja no es una web. El cajero no mira la pantalla para disfrutarla, sino para confirmar
de reojo que lo que hizo entró. Así que aquí solo se anima lo que **explica un cambio**: qué
línea del carrito acaba de moverse, que el aviso es nuevo y no el de antes, hacia dónde se
fue el menú. Nada se anima por adorno, y nada retrasa nunca el escaneo ni el foco. Ver D-029
y la sección «Movimiento» de `docs/DESIGN.md`.

Tres reglas que cumple todo lo de este módulo:

- **El estado cambia al instante; solo el dibujo se anima.** Quien pregunte si la barra está
  plegada o si el aviso está visible obtiene la respuesta final desde el primer momento, así
  que la lógica —y las pruebas— no dependen del reloj.
- **Todo se puede interrumpir.** Una pistola dispara varias veces por segundo; una animación
  que haya que esperar a que termine sería un cuello de botella.
- **Se puede apagar.** La preferencia `animaciones` de la rueda de configuración (F9) deja la
  caja como era antes: todo aparece y desaparece de golpe.

No importa nada de los servicios: es interfaz pura.
"""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPoint, QVariantAnimation
from PySide6.QtWidgets import QGraphicsOpacityEffect, QWidget

# Duraciones, en milisegundos. Pocas y con nombre, igual que los radios: una duración nueva
# se justifica, no se elige a ojo en la pantalla que la necesita.
ENTRADA_MS = 150      # algo aparece
SALIDA_MS = 200       # algo se va: un poco más lenta, para que se note adónde
PULSO_MS = 220        # un aviso que ya estaba se renueva
BARRA_MS = 180        # la barra lateral se pliega o se despliega
DESTELLO_MS = 700     # la línea del carrito que acaba de cambiar
DIALOGO_MS = 120      # una ventana de diálogo se abre
SACUDIDA_MS = 320     # un PIN incorrecto
#: Cuánto se desplaza la ventana en la sacudida. Lo justo para verse sin marear.
SACUDIDA_PX = 9

#: Lo que entra desacelera: llega rápido y se asienta. Lo que sale acelera: se despide sin
#: hacerse esperar. Son las dos curvas del programa, y no hay más.
CURVA_ENTRADA = QEasingCurve.Type.OutCubic
CURVA_SALIDA = QEasingCurve.Type.InCubic

#: La preferencia del equipo. La fija la ventana al aplicar las preferencias.
habilitado = True
#: Apagado forzoso, por encima de la preferencia. Lo usan las pruebas, igual que el sonido:
#: aplicar unas preferencias con las animaciones encendidas no debe volver a encenderlas.
_suprimido = False


def activo() -> bool:
    """Indica si hay que animar o aplicar los cambios de golpe."""
    return habilitado and not _suprimido


def suprimir(suprimido: bool = True) -> None:
    global _suprimido
    _suprimido = suprimido


def animacion(
    padre: QObject,
    duracion: int,
    curva: QEasingCurve.Type = CURVA_ENTRADA,
) -> QVariantAnimation:
    """Crea una animación de números reutilizable, con la duración y la curva indicadas.

    Se reutiliza en vez de crear una nueva por cada cambio: así interrumpirla es solo
    `stop()` y volver a arrancarla desde donde esté, sin animaciones huérfanas peleándose
    por el mismo widget.
    """
    anim = QVariantAnimation(padre)
    anim.setDuration(duracion)
    anim.setEasingCurve(curva)
    return anim


class Fundido(QObject):
    """Hace aparecer y desaparecer un widget con un fundido, y lo hace parpadear si ya está.

    El efecto de opacidad **solo se activa mientras dura la animación**. Con él puesto, Qt
    dibuja el widget en una imagen intermedia y el texto pierde el suavizado ClearType: se ve
    un punto más borroso. Un aviso que se queda cinco segundos en pantalla merece verse
    nítido.

    Ojo: un widget admite un solo efecto gráfico, así que esto no sirve para las tarjetas,
    que ya llevan su sombra (`estilos.aplicar_sombra`).
    """

    def __init__(self, widget: QWidget) -> None:
        super().__init__(widget)
        self._widget = widget
        self._efecto = QGraphicsOpacityEffect(widget)
        self._efecto.setEnabled(False)
        widget.setGraphicsEffect(self._efecto)

        self._anim = animacion(self, ENTRADA_MS)
        self._anim.valueChanged.connect(self._efecto.setOpacity)
        self._anim.finished.connect(self._terminar)
        #: Lo que se está haciendo ahora: "entrar", "salir", "pulso" o None.
        self._fase: str | None = None

    @property
    def saliendo(self) -> bool:
        return self._fase == "salir"

    def mostrar(self) -> None:
        """Muestra el widget. Si ya estaba a la vista, lo hace parpadear para que se note
        que lo que dice es nuevo."""
        ya_visible = self._widget.isVisible() and not self.saliendo
        self._widget.show()
        if not activo():
            self._detener(opacidad=1.0)
            return

        desde = self._opacidad_actual() if self._fase else (1.0 if ya_visible else 0.0)
        self._anim.stop()
        self._efecto.setEnabled(True)
        if ya_visible and self._fase != "entrar":
            # El pulso baja y vuelve a subir. Es lo que distingue «otro producto» de «el mismo
            # aviso de antes», que de otro modo son idénticos si el texto se parece.
            self._fase = "pulso"
            self._anim.setDuration(PULSO_MS)
            self._anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
            self._anim.setStartValue(desde)
            self._anim.setKeyValueAt(0.4, 0.35)
            self._anim.setEndValue(1.0)
        else:
            self._fase = "entrar"
            self._reiniciar_claves()
            self._anim.setDuration(ENTRADA_MS)
            self._anim.setEasingCurve(CURVA_ENTRADA)
            self._anim.setStartValue(desde)
            self._anim.setEndValue(1.0)
        self._efecto.setOpacity(desde)
        self._anim.start()

    def ocultar(self) -> None:
        """Esconde el widget con un fundido. `isVisible()` sigue siendo cierto hasta que
        termina, pero `saliendo` ya lo dice."""
        if not self._widget.isVisible() or self.saliendo:
            return
        if not activo():
            self._detener(opacidad=1.0)
            self._widget.hide()
            return

        desde = self._opacidad_actual() if self._fase else 1.0
        self._anim.stop()
        self._fase = "salir"
        self._reiniciar_claves()
        self._anim.setDuration(SALIDA_MS)
        self._anim.setEasingCurve(CURVA_SALIDA)
        self._anim.setStartValue(desde)
        self._anim.setEndValue(0.0)
        self._efecto.setEnabled(True)
        self._efecto.setOpacity(desde)
        self._anim.start()

    def ocultar_ya(self) -> None:
        """Esconde sin fundido, cortando lo que estuviera en curso."""
        self._detener(opacidad=1.0)
        self._widget.hide()

    # ------------------------------------------------------------------ interno

    def _opacidad_actual(self) -> float:
        valor = self._anim.currentValue()
        return float(valor) if valor is not None else self._efecto.opacity()

    def _reiniciar_claves(self) -> None:
        # Las claves intermedias del pulso sobreviven a setStartValue/setEndValue; hay que
        # borrarlas o la siguiente entrada heredaría el bache del 40 %.
        self._anim.setKeyValues([])

    def _terminar(self) -> None:
        fase = self._fase
        self._detener(opacidad=1.0)
        if fase == "salir":
            self._widget.hide()

    def _detener(self, opacidad: float) -> None:
        self._anim.stop()
        self._fase = None
        self._efecto.setOpacity(opacidad)
        self._efecto.setEnabled(False)


class _AparicionDeVentana(QObject):
    """Filtro de eventos que funde una ventana al mostrarse. Ver `aparecer_al_abrir`."""

    def __init__(self, ventana: QWidget) -> None:
        super().__init__(ventana)
        self._ventana = ventana
        self._anim = animacion(self, DIALOGO_MS)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.valueChanged.connect(ventana.setWindowOpacity)
        ventana.installEventFilter(self)

    def eventFilter(self, objeto, evento) -> bool:  # noqa: N802 - lo nombra Qt
        # Red de seguridad (fase 23): si Python llegara a vaciar el estado de este objeto
        # mientras Qt lo sigue llamando, el evento pasa sin fundido. Antes eso era un
        # AttributeError en cada evento, un aviso de error encima de otro, y la caja congelada.
        anim = self.__dict__.get("_anim")
        ventana = self.__dict__.get("_ventana")
        if anim is None or ventana is None:
            return False
        tipo = evento.type()
        if tipo == QEvent.Type.Show and activo():
            ventana.setWindowOpacity(0.0)
            anim.stop()
            anim.start()
        elif tipo == QEvent.Type.Hide:
            # Una ventana que se cierra a medio fundido no puede volver a abrirse
            # transparente: se deja entera al esconderse.
            anim.stop()
            ventana.setWindowOpacity(1.0)
        return False


#: Los filtros de aparición vivos, sujetos desde Python (fase 23). Sin esto solo los sujetaba
#: Qt, como hijos de su ventana, y el recolector de Python podía vaciarles el estado mientras Qt
#: les seguía mandando eventos: en la tienda, tras un rato de uso, eso congeló la caja. Cada uno
#: sale de aquí cuando su ventana se destruye.
_apariciones: set[_AparicionDeVentana] = set()


def aparecer_al_abrir(ventana: QWidget) -> None:
    """Hace que la ventana se abra con un fundido corto cada vez que se muestra.

    Solo la entrada. Al cerrar, la ventana desaparece en el acto: quien cierra un diálogo
    quiere volver a la caja, y el foco no puede esperar a que termine un fundido.

    Se engancha ventana a ventana, y no con un filtro sobre toda la aplicación, porque ese
    filtro vería pasar cada evento del programa —cada repintado, cada tecla de la pistola—
    solo para buscar los pocos que abren un diálogo.
    """
    filtro = _AparicionDeVentana(ventana)
    _apariciones.add(filtro)
    ventana.destroyed.connect(lambda *_: _apariciones.discard(filtro))


def sacudir(ventana: QWidget) -> None:
    """Sacude la ventana de lado a lado: el gesto universal de «no».

    Es para el PIN incorrecto, donde el cajero está mirando el teclado numérico y no el
    diálogo: el movimiento se percibe de reojo, un mensaje en rojo no. Mueve la ventana
    entera y no el campo porque el campo vive en un layout, y el mensaje de error que se
    muestra a la vez obliga a recolocarlo a mitad de la sacudida.
    """
    if not activo() or not ventana.isVisible():
        return
    anterior = getattr(ventana, "_sacudida", None)
    if anterior is not None:
        # Un segundo error a mitad de sacudida vuelve a empezar desde el sitio original, no
        # desde donde la dejó la primera, o la ventana acabaría corrida.
        anterior.stop()
        origen = anterior.origen
    else:
        origen = ventana.pos()

    anim = animacion(ventana, SACUDIDA_MS, QEasingCurve.Type.Linear)
    anim.origen = origen
    # Cuatro vaivenes que se amortiguan, y de vuelta al punto de partida.
    for paso, factor in enumerate((0, -1, 1, -0.7, 0.7, -0.35, 0.35, 0)):
        anim.setKeyValueAt(paso / 7, origen + QPoint(round(SACUDIDA_PX * factor), 0))
    anim.valueChanged.connect(ventana.move)
    anim.finished.connect(lambda: setattr(ventana, "_sacudida", None))
    ventana._sacudida = anim
    anim.start()
