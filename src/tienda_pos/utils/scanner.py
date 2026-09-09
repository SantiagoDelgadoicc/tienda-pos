"""Distinguir una pistola lectora de alguien escribiendo.

Una pistola USB se comporta como un teclado: "escribe" los dígitos a una velocidad que
ninguna persona alcanza y normalmente termina con Enter. Pero no todas vienen configuradas
para enviar ese Enter, y en ese caso el código se queda en el campo esperando a que alguien
lo pulse, lo que da la impresión de que el lector no funciona.

Este detector mide el tiempo entre pulsaciones. Si la ráfaga es imposible para una persona,
la entrada se puede confirmar sola y el lector funciona sin configurar nada.

Es una clase pura, sin Qt, para poder probarla con tiempos simulados.
"""

from __future__ import annotations

import time

#: Milisegundos por debajo de los cuales una pulsación no puede ser humana. Un mecanógrafo
#: muy rápido ronda los 100 ms entre teclas; una pistola está entre 5 y 15 ms.
UMBRAL_MS = 25

#: Mínimo de caracteres antes de fiarse del diagnóstico. Con dos o tres pulsaciones, un
#: golpe de suerte al teclear podría parecer una ráfaga.
MINIMO_CARACTERES = 8


class DetectorLector:
    """Observa la cadencia de escritura de un campo y decide su origen."""

    def __init__(self, umbral_ms: int = UMBRAL_MS, minimo: int = MINIMO_CARACTERES) -> None:
        self._umbral_ms = umbral_ms
        self._minimo = minimo
        self._intervalos: list[float] = []
        self._ultimo: float | None = None

    def registrar(self, momento: float | None = None) -> None:
        """Anota una pulsación. `momento` en segundos; por defecto, ahora."""
        momento = time.monotonic() if momento is None else momento
        if self._ultimo is not None:
            self._intervalos.append((momento - self._ultimo) * 1000)
        self._ultimo = momento

    def reiniciar(self) -> None:
        self._intervalos.clear()
        self._ultimo = None

    @property
    def caracteres(self) -> int:
        return len(self._intervalos) + 1 if self._ultimo is not None else 0

    @property
    def intervalo_medio_ms(self) -> float:
        if not self._intervalos:
            return float("inf")
        return sum(self._intervalos) / len(self._intervalos)

    @property
    def es_lector(self) -> bool:
        """True si la entrada vino de una pistola y no de un teclado humano.

        Se exige que *todos* los intervalos estén por debajo del umbral, no solo la media:
        una persona escribiendo con una pausa larga en medio podría promediar bajo y aun así
        no ser un lector.
        """
        if self.caracteres < self._minimo:
            return False
        return all(intervalo < self._umbral_ms for intervalo in self._intervalos)
