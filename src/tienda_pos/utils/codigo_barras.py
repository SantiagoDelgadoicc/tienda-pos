"""Validación y normalización de códigos de barras.

Una pistola lectora se comporta como un teclado: escribe los dígitos y pulsa Enter. Por eso
lo que llega aquí puede traer espacios, saltos de línea o caracteres sueltos si el lector
falló a mitad de la lectura.
"""

from __future__ import annotations

from ..config import CODIGO_LONGITUD_MAX


def normalizar(codigo: str) -> str:
    """Limpia lo que llega del lector o del teclado.

    Quita espacios, saltos de línea y guiones. No valida: solo deja el código en la forma
    canónica con la que se consulta la base de datos.
    """
    return codigo.strip().replace(" ", "").replace("-", "").replace("\n", "").replace("\r", "")


def es_valido(codigo: str) -> bool:
    """Un código utilizable es alfanumérico, no vacío y de longitud razonable.

    Deliberadamente permisivo: además de los EAN-13 de fábrica, muchas tiendas usan códigos
    internos cortos para sus productos propios. Rechazar esos códigos por no ser estándar
    sería negarle al cliente la mitad de su catálogo.
    """
    limpio = normalizar(codigo)
    if not limpio or len(limpio) > CODIGO_LONGITUD_MAX:
        return False
    return limpio.isalnum()


def digito_verificador_ean13(doce_digitos: str) -> int:
    """Calcula el decimotercer dígito de un EAN-13 a partir de los doce primeros.

    Se usa para generar códigos de ejemplo que sean válidos de verdad: si en la demo se
    escaneara un código inventado con una pistola real, no leería nada.
    """
    if len(doce_digitos) != 12 or not doce_digitos.isdigit():
        raise ValueError("Se requieren exactamente 12 dígitos")
    suma = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(doce_digitos))
    return (10 - suma % 10) % 10


def generar_ean13(doce_digitos: str) -> str:
    """Devuelve el EAN-13 completo, con su dígito verificador."""
    return doce_digitos + str(digito_verificador_ean13(doce_digitos))


def es_ean13(codigo: str) -> bool:
    """Indica si el código es un EAN-13 con dígito verificador correcto."""
    limpio = normalizar(codigo)
    if len(limpio) != 13 or not limpio.isdigit():
        return False
    return digito_verificador_ean13(limpio[:12]) == int(limpio[12])
