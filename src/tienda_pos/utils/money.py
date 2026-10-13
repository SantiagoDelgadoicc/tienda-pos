"""Manejo de dinero en pesos chilenos.

Todo importe se representa como un entero de CLP. Nunca se usa coma flotante: acumula
errores de redondeo y produce totales como 999,99999 que hacen que el cliente pierda la
confianza en el sistema. Ver D-004 en docs/DECISIONES.md.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

# Separador de miles usado en Chile.
_SEPARADOR_MILES = "."


def formatear_clp(monto: int, con_simbolo: bool = True) -> str:
    """Convierte 1234567 en '$1.234.567'.

    Los montos negativos se muestran con el signo delante del símbolo: '-$1.200'.
    """
    negativo = monto < 0
    texto = f"{abs(int(monto)):,}".replace(",", _SEPARADOR_MILES)
    if con_simbolo:
        texto = f"${texto}"
    return f"-{texto}" if negativo else texto


def parsear_clp(texto: str) -> int:
    """Convierte lo que escribe una persona ('$1.200', '1200', '1.200') en 1200.

    Acepta el símbolo, los puntos de miles y los espacios, porque un cajero apurado
    escribe de cualquiera de esas formas.

    Raises:
        ValueError: si el texto no contiene un número entero válido.
    """
    limpio = texto.strip().replace("$", "").replace(_SEPARADOR_MILES, "").replace(" ", "")
    limpio = limpio.replace(" ", "")  # espacio duro, frecuente al copiar y pegar
    if not limpio:
        raise ValueError("El monto está vacío")
    negativo = limpio.startswith("-")
    if negativo:
        limpio = limpio[1:]
    if not limpio.isdigit():
        raise ValueError(f"'{texto}' no es un monto válido")
    valor = int(limpio)
    return -valor if negativo else valor


def porcentaje_de(monto: int, porcentaje: float) -> int:
    """Calcula un porcentaje de un monto, redondeando al peso más cercano.

    Se usa Decimal en lugar de float para que el redondeo sea el que espera una persona
    (la mitad siempre hacia arriba) y no el que decide el hardware.
    """
    resultado = (Decimal(int(monto)) * Decimal(str(porcentaje)) / Decimal(100)).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    )
    return int(resultado)


def precio_por_gramos(precio_kilo_clp: int, gramos: int) -> int:
    """Lo que cuestan `gramos` de un producto que se vende a `precio_kilo_clp` el kilo.

    Al peso más cercano, la mitad hacia arriba, y en enteros: $7.990 el kilo por 350 g son
    $2.796,5, que se cobran $2.797. Sin `float`, por lo mismo que el resto del dinero.
    """
    return (int(precio_kilo_clp) * int(gramos) + 500) // 1000


def gramos_por_monto(precio_kilo_clp: int, monto_clp: int) -> int:
    """Los gramos que hay que dar cuando el cliente pide "deme $2.000 de pan" (fase 27).

    Es la cuenta al revés de `precio_por_gramos`, que sigue siendo la que fija lo que se cobra:
    la línea guarda gramos, no pesos. Por eso no siempre se llega al monto justo. A $2.990 el
    kilo cada gramo vale casi $3, y entre 668 g ($1.997) y 669 g ($2.000) no hay nada. Se
    elige el peso cuyo precio queda más cerca de lo pedido; si un precio justo existe, es ese.
    Entre dos igual de cerca, el que se acerca más a la proporción exacta. Devuelve 0 si el
    monto o el precio del kilo no son positivos.
    """
    precio_kilo_clp, monto_clp = int(precio_kilo_clp), int(monto_clp)
    if precio_kilo_clp <= 0 or monto_clp <= 0:
        return 0
    ideal = (monto_clp * 1000 * 2 + precio_kilo_clp) // (precio_kilo_clp * 2)  # redondeado
    candidatos = [g for g in (ideal - 1, ideal, ideal + 1) if g >= 1]
    return min(
        candidatos,
        key=lambda g: (
            abs(precio_por_gramos(precio_kilo_clp, g) - monto_clp),
            abs(g * precio_kilo_clp - monto_clp * 1000),
        ),
    )


def formatear_peso(gramos: int) -> str:
    """Un peso para leerlo en la caja: "350 g" hasta el kilo, "1,25 kg" desde ahí.

    Los kilos van con coma decimal, como se escriben en Chile, y sin ceros de sobra.
    """
    gramos = int(gramos)
    if abs(gramos) < 1000:
        return f"{gramos} g"
    kilos = f"{gramos / 1000:.3f}".rstrip("0").rstrip(".")
    return f"{kilos.replace('.', ',')} kg"
