# Tienda POS — prototipo

Prototipo de sistema de punto de venta para una tienda pequeña (almacén / minimarket).
Aplicación de **escritorio Windows**: el usuario abre un acceso directo y el programa arranca.
No es una aplicación web y no requiere internet.

El núcleo es lo que pidió el cliente: **código de barras → producto → precio**.
Alrededor de eso, el prototipo demuestra una venta completa e inventario mínimo.

## Estado

En desarrollo. Ver [docs/PLAN.md](docs/PLAN.md) para el avance por fases.

## Requisitos

- Windows 10 u 11
- Python 3.11 o superior (solo para desarrollo; el ejecutable final no lo necesita)

## Ejecutar en desarrollo

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m tienda_pos
```

## Pruebas

```bash
pytest
```

## Documentación

| Documento | Para qué sirve |
|---|---|
| [CLAUDE.md](CLAUDE.md) | Contexto, reglas y convenciones del proyecto |
| [docs/PLAN.md](docs/PLAN.md) | Fases, hitos, tareas y criterios de aceptación |
| [docs/PREGUNTAS-CLIENTE.md](docs/PREGUNTAS-CLIENTE.md) | Preguntas de negocio pendientes para la reunión con el cliente |
| [docs/DECISIONES.md](docs/DECISIONES.md) | Decisiones técnicas importantes y su justificación |

## Aviso

Este es un **prototipo de demostración**. No emite boletas ni facturas, no está conectado al
SII, no registra medios de pago y no funciona en varias cajas simultáneas.
