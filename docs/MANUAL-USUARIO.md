# Manual de usuario

El manual que se entrega al cliente es el PDF
**[Manual-de-usuario-Punto-y-Fama.pdf](Manual-de-usuario-Punto-y-Fama.pdf)**: 18 páginas A4, con
las capturas del programa, escrito para quien atiende la caja y, en su segunda parte, para el
dueño.

Se escribe en [manual/manual.html](manual/manual.html) y se genera con

```bash
python tools/manual_pdf.py
```

Si cambió la interfaz, antes hay que regenerar las capturas con `python tools/capturas.py`. El
índice y los números de página se calculan solos al generar el PDF.

**Lo que el manual no dice, a propósito:** ningún PIN. Desde D-032 cada empleado tiene el suyo,
generado por el sistema, y los de la demostración (`--demo`) no sirven en la tienda. Tampoco
explica la instalación: eso está en `INSTALACION/LEEME-PRIMERO.txt` y en `DESPLIEGUE-TIENDA.md`.
