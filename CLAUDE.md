# CLAUDE.md — Contexto y reglas del proyecto

## 1. Qué es esto

Prototipo de un sistema de punto de venta (POS) para una tienda pequeña.
El objetivo de esta etapa **no es entregar el sistema definitivo**, sino construir algo
lo bastante convincente como para que el cliente decida contratar el desarrollo real.

## 2. Contexto del cliente

Lo único que el cliente dijo, literalmente:

> "Quiero un sistema de tienda que lea el código de barras de un producto y despliegue su precio."

No entregó ninguna otra especificación. Esto es fundamental: **casi todo lo que hay en este
repositorio más allá de "escanear → mostrar precio" es una decisión nuestra, no un requisito
del cliente.** Cualquiera que trabaje aquí debe mantener esa distinción viva.

## 3. Trazabilidad de requisitos

Se clasifica todo requisito en una de estas cuatro categorías, y nunca se asciende de
categoría en silencio:

### 3.1 Confirmado por el cliente
- Leer un código de barras e identificar el producto.
- Mostrar el precio de ese producto.

### 3.2 Decidido por Santiago (dueño del proyecto)
- Alcance: POS con venta e inventario mínimo, no solo consulta de precios.
- Usuario principal: cajero en el mostrador.
- Aplicación de **escritorio Windows**. Explícitamente **no web**: el cliente abre un acceso
  directo y el programa arranca. Sin navegador ni `localhost`.
- Entrada manual del código además de la pistola lectora.
- La venta se cierra con total y queda registrada. Sin medios de pago, sin vuelto, sin
  comprobante impreso y sin boleta electrónica.
- Funcionamiento local en un solo PC, sin red ni internet.
- Stack: Python + PySide6 (Qt) + SQLite.
- Acceso con PIN de cajero y modo administrador.
- Venta solo por unidad (nada a granel ni por peso).
- Rubro asumido para el catálogo demo: almacén / minimarket.
- Reportes mínimos: ventas del día.
- Descuento manual aplicable a la venta.

### 3.3 Supuestos (a validar, no confirmados por nadie)
- Moneda: peso chileno (CLP), sin decimales.
- El precio mostrado ya incluye IVA.
- Un solo local y una sola caja.
- Catálogo de cientos de productos, no de decenas de miles.
- El cliente dispone de una pistola lectora USB estándar (HID).
- El PC de la tienda usa Windows 10 u 11.

### 3.4 Pendiente de confirmar
Todo lo recogido en `docs/PREGUNTAS-CLIENTE.md`. Ese documento se lleva a la reunión.

## 4. Reglas de trabajo

1. **No inventar requisitos.** Si algo no está en 3.1 o 3.2, es supuesto o recomendación, y
   se marca como tal. Una recomendación no se convierte en requisito sin aprobación explícita.
2. **Decisiones importantes las aprueba Santiago**: arquitectura, base de datos, tecnología
   principal, infraestructura, seguridad, autenticación, modelo de datos, APIs, hardware,
   integraciones, cambios grandes de UX, costes, escalabilidad y deuda técnica significativa.
   Para ellas se usa el formato `HUMAN DECISION REQUIRED` con opciones, pros, contras,
   riesgos, recomendación e impacto.
3. **Autonomía** en lo local, mecánico, reversible y de bajo riesgo que sea coherente con el
   diseño ya aprobado.
4. **Una funcionalidad no está terminada porque funcione en el caso normal.** Hay que cubrir
   el error, el vacío y el caso límite.
5. **No modificar en silencio decisiones de la planificación.** Si cambia algo de `docs/PLAN.md`
   o de `docs/DECISIONES.md`, se dice.
6. Idioma: español, en código y en documentación. Se admiten términos técnicos en inglés
   cuando son el estándar.

## 5. Arquitectura

Aplicación de escritorio monopuesto, sin red.

- **Python 3.11+**
- **PySide6 (Qt 6)** para la interfaz. Se eligió sobre PyQt6 porque su licencia LGPL permite
  vender el producto como software propietario.
- **SQLite** con el módulo `sqlite3` de la biblioteca estándar, en modo WAL y con
  `foreign_keys=ON`. Sin ORM: para este tamaño, SQL explícito tras una capa de repositorios
  da más control, menos dependencias y un ejecutable más limpio.
- **pytest** para pruebas.
- **PyInstaller** para generar `TiendaPOS.exe`.

### Capas

Las dependencias van en una sola dirección: `ui → services → repositories → db`.

```
main.py                   punto de entrada del ejecutable (y de --verificar)
src/tienda_pos/
  app.py                  arranque: registro, errores, respaldo, base, sesión, ventana
  __main__.py             permite `python -m tienda_pos`
  config.py               rutas de datos, constantes
  db/                     conexión, esquema, migraciones, datos demo, respaldos
  domain/                 modelos y errores del negocio
  repositories/           acceso a datos, un módulo por entidad
  services/               lógica de negocio (NO importa Qt)
  ui/                     todo lo que sabe de Qt
  utils/                  dinero, códigos de barras, lector, sonido, registro
tools/                    construir, icono, capturas, acceso directo
tests/                    185 pruebas
```

**Regla dura: `services/` y `domain/` no importan nada de Qt.** Así la lógica de negocio se
prueba sin abrir una ventana, y una futura interfaz distinta (web, móvil) reutilizaría el núcleo.

### Dónde viven los datos

`%LOCALAPPDATA%\TiendaPOS\` contiene la base de datos, los respaldos y los logs.
Nunca dentro de `Archivos de Programa`: Windows bloquea la escritura ahí.

## 6. Convenciones de código

- Nombres de módulos, funciones y variables **en español**, en `snake_case`.
- Clases en `PascalCase`.
- Type hints en toda función pública.
- Docstrings breves en las funciones de servicio, explicando el *porqué* cuando no sea obvio.
- `dataclasses` para los modelos de dominio.
- **El dinero se representa siempre con enteros de CLP.** Nunca `float`: acumula errores y
  produce totales como 999,99999. Ver `utils/money.py`.
- **Las líneas de venta guardan copia del precio y del nombre** del producto en el momento de
  la venta. Cambiar un precio mañana no debe reescribir el historial de ayer.
- SQL en mayúsculas para las palabras reservadas, con parámetros `?`. Nunca concatenar valores
  dentro de una consulta.
- Toda operación que modifique varias tablas va dentro de una transacción.

## 7. Comandos

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt   # requirements.txt son solo las de ejecución

python main.py                        # ejecutar
python main.py --verificar            # arrancar sin interfaz y comprobar que todo va bien
pytest                                # pruebas (185, unos 20 s)
pytest --cov=tienda_pos               # con cobertura

python tools/construir.py             # empaquetar el .exe
python tools/crear_acceso_directo.py  # acceso directo en el escritorio
python tools/capturas.py              # regenerar docs/img/*.png
python tools/icono.py                 # regenerar el icono
```

## 8. Documentos vivos

| Archivo | Contenido |
|---|---|
| `docs/PLAN.md` | Fases, tareas, criterios de aceptación. Se actualiza al avanzar. |
| `docs/PREGUNTAS-CLIENTE.md` | Preguntas de negocio para la reunión con el cliente. |
| `docs/DECISIONES.md` | Decisiones técnicas importantes con su justificación. |
| `docs/GUION-DEMO.md` | Guion paso a paso de la demostración. |
| `docs/MANUAL-USUARIO.md` | Manual para quien opera la caja. |
| `docs/TECNICA.md` | Documentación técnica e instrucciones de compilación. |
