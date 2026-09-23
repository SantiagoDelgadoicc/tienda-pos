# CLAUDE.md — Contexto y reglas del proyecto

## 1. Qué es esto

Prototipo de un sistema de punto de venta (POS) para una tienda pequeña.
El objetivo de esta etapa **no es entregar el sistema definitivo**, sino construir algo
lo bastante convincente como para que el cliente decida contratar el desarrollo real.

El prototipo ya se presentó y la conversación siguió. Desde el 2026-09-13 hay una **segunda etapa**
con requisitos que sí vienen del cliente: rendimiento, dos cajas, migrar su catálogo antiguo e
instalador. Ver las fases 8 a 14 de `docs/PLAN.md`.

## 2. Contexto del cliente

### Lo que dijo al principio, literalmente

> "Quiero un sistema de tienda que lea el código de barras de un producto y despliegue su precio."

No entregó ninguna otra especificación. Esto es fundamental: **casi todo lo que hay en este
repositorio más allá de "escanear → mostrar precio" es una decisión nuestra, no un requisito
del cliente.** Cualquiera que trabaje aquí debe mantener esa distinción viva.

### Primera reunión (2026-09-13)

Vio el prototipo y contó cosas que no sabíamos. En resumen:

- Su sistema anterior **se le quedaba pegado**.
- En ese sistema guardaba, por producto, **cantidad, precio de compra, precio de venta y familia**.
- Quiere **conservar esos datos**, pero el PC donde estaban no enciende.
- El sistema debe funcionar en **dos PC**.
- Quiere una **instalación mejor**.
- Mencionó **LocalShop** y preguntó si se puede hacer algo parecido.

Cuidado con esta reunión: dio **contexto, no respuestas**. Las preguntas de los bloques A a F de
`docs/PREGUNTAS-CLIENTE.md` siguen sin contestar, y varias de las cosas que damos hoy por
requisitos son en realidad interpretaciones nuestras de comentarios suyos. Están marcadas como
tales en 3.3.

Sobre LocalShop conviene saber qué es antes de prometer nada: un **servicio chileno por
suscripción, en la nube**, con catálogo precargado de miles de productos y **boleta electrónica ante
el SII**. Nada de eso está en nuestro alcance, y dos de esas tres cosas contradicen decisiones ya
tomadas (D-001 y D-006). Lo que le atrajo, según lo hablado, fue lo completo que se ve.

## 3. Trazabilidad de requisitos

Se clasifica todo requisito en una de estas cuatro categorías, y nunca se asciende de
categoría en silencio:

### 3.1 Confirmado por el cliente

De la primera conversación:

- Leer un código de barras e identificar el producto.
- Mostrar el precio de ese producto.

De la reunión del 2026-09-13:

- El sistema anterior se le quedaba pegado. → **El rendimiento es un requisito, no un lujo** (D-022).
- Ese sistema guardaba por producto: cantidad, precio de compra, precio de venta y "familia".
  *(2026-09-14: el cliente aclaró que de esos cuatro solo le interesan la **cantidad** y el
  **precio de venta**. Ver "Retirado" en 3.3.)*
- Existe un catálogo previo suyo que quiere conservar.
- El sistema debe funcionar en dos PC (D-015).
- La instalación debe ser mejor que copiar una carpeta (D-020).

### 3.2 Decidido por Santiago (dueño del proyecto)

- Alcance: POS con venta e inventario mínimo, no solo consulta de precios.
- Usuario principal: cajero en el mostrador.
- Aplicación de **escritorio Windows**. Explícitamente **no web**: el cliente abre un acceso
  directo y el programa arranca. Sin navegador ni `localhost`.
- Entrada manual del código además de la pistola lectora.
- La venta se cierra con total y queda registrada. Sin medios de pago, sin vuelto, sin
  comprobante impreso y sin boleta electrónica.
- Stack: Python + PySide6 (Qt) + SQLite.
- Acceso con PIN de cajero y modo administrador.
- Funcionamiento **sin internet**. *(Lo que decía antes esta línea —"local en un solo PC, sin red"—
  queda superado por D-015: sigue sin internet, pero ahora hay una red local entre las dos cajas.)*
- Venta solo por unidad (nada a granel ni por peso).
- Rubro asumido para el catálogo demo: almacén / minimarket.
- Reportes mínimos: ventas del día.
- Descuento manual aplicable a la venta entera o a un producto concreto.
- Tema claro y tema oscuro, elegibles desde una pantalla de configuración (F9), junto con el
  sonido, la confirmación de cobro y la barra de atajos. Se guardan en `preferencias.json`,
  dentro de la carpeta de datos.
- **La apariencia sigue el sistema visual de `docs/DESIGN.md`** desde el 2026-09-17 (D-026 y
  D-027): navegación en barra lateral plegable, lienzo de piedra cálida y tarjetas blancas.
  **Dos colores y ninguno más**: **rojo** (el del logotipo) para dónde estoy, dónde está el
  foco y lo que cancela o borra, siempre en lavado o filete; **verde** para lo que salió bien
  y lo que confirma, que es el único que va relleno.
- **Movimiento breve y con propósito** desde el 2026-09-23 (D-029): destello verde en la línea
  del carrito que cambia, fundido del aviso de escaneo y plegado animado de la barra lateral.
  Además: fundido del precio en la consulta y de los diálogos, y sacudida del PIN incorrecto.
  Se apaga desde F9. Las reglas están en la sección «Movimiento» de `docs/DESIGN.md`.
- El programa se rotula con el nombre del negocio, **Punto y Fama · Botillería y market**, y
  el ejecutable es `PuntoYFamaCaja.exe`. El nombre de la carpeta de datos (`TiendaPOS`) no
  cambia con ellos: ahí está la base de datos de la tienda.

Añadido tras la reunión del 2026-09-13:

- El multipuesto se resuelve con **un proceso servidor dueño del archivo**, no con la base en una
  carpeta compartida de red (D-015).
- Criterios de rendimiento **medidos**, con catálogo sintético de 20.000 productos (D-022).
- **Movimientos de inventario**: el stock no cambia sin dejar rastro (D-018). Sigue en pie tras la
  retirada de D-016 y D-017: no es un atributo del producto y no depende de ninguno de los dos.
- Importación y exportación **solo CSV**, con la biblioteca estándar (D-019).

### 3.3 Supuestos (a validar, no confirmados por nadie)

- Moneda: peso chileno (CLP), sin decimales.
- El precio mostrado ya incluye IVA.
- Catálogo de cientos de productos, no de decenas de miles.
- El cliente dispone de una pistola lectora USB estándar (HID).
- El PC de la tienda usa Windows 10 u 11.

**Interpretaciones nuestras de lo que dijo el cliente.** Esto es lo más fácil de ascender de
categoría por accidente, así que va aparte y explícito:

- Que **"dos PC" significa dos cajas vendiendo a la vez**. El cliente dijo que debía funcionar en
  dos computadores; "caja más oficina" también encaja con esa frase y sale mucho más barato. Se
  está construyendo para lo primero. Pregunta G11.
- Que el **descuento de stock al vender** lo pidió él. En la conversación apareció como propuesta
  de Santiago. Ya está implementado desde la fase 1 (`services/venta.py`, D-009), así que basta
  con confirmárselo.
- Que de LocalShop le gustó **lo completo que se ve**, y no la nube ni la boleta electrónica.
  Preguntas G15 a G17. Si fuera lo segundo, es otro proyecto.

**Retirado el 2026-09-13:** "un solo local y una sola caja". El cliente lo desmintió.

**Retirado el 2026-09-14:** la **familia** y el **precio de compra** del producto. El 2026-09-13 el
cliente contó que su sistema anterior guardaba cantidad, precio de compra, precio de venta y
familia, y de ahí salieron D-016 y D-017. El 2026-09-14 comunicó que esos dos atributos no le
interesan. Ambas decisiones quedan **retiradas**, y con ellas las preguntas G6 y G7 y **todo informe
de margen o ganancia**, que sin el costo no se puede calcular. Del producto se guardan cantidad y
precio de venta, que es lo que ya había.

*Cuidado con esta retirada:* es una interpretación que viaja en la misma dirección que las demás,
pero hacia abajo. Lo que llegó fue "esos atributos no interesan"; lo que no sabemos es si eso salió
del cliente pensándolo o de una respuesta rápida. Si algún día pregunta cuánto gana, el costo hace
falta y el catálogo ya estará cargado sin él. Ver el riesgo anotado en D-017.

### 3.4 Pendiente de confirmar

Todo lo recogido en `docs/PREGUNTAS-CLIENTE.md`, que sigue sin responder de los bloques A a F, más
el bloque G añadido tras la reunión. Ese documento se lleva a la reunión.

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

Aplicación de escritorio, sin internet. **Hoy monopuesto; la fase 13 la convierte en dos cajas
sobre la red local, con un proceso servidor dueño de la base de datos** (D-015). La regla de capas
de abajo es justamente lo que hace viable ese cambio.

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
    estilos.py            paletas, radios, sombras y la hoja de estilos entera
    barra_lateral.py      la navegación
    iconos.py             los iconos, dibujados con QPainter
    movimiento.py         duraciones, curvas y animaciones compartidas
  utils/                  dinero, códigos de barras, lector, sonido, registro
tools/                    construir, icono, capturas, acceso directo
tests/                    284 pruebas
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
pytest                                # pruebas (284, unos 40 s)
pytest --cov=tienda_pos               # con cobertura

python tools/construir.py             # empaquetar PuntoYFamaCaja.exe
python tools/crear_acceso_directo.py  # acceso directo en el escritorio
python tools/capturas.py              # regenerar docs/img/*.png
python tools/icono.py                 # regenerar el icono
```

## 8. Documentos vivos

| Archivo | Contenido |
|---|---|
| `docs/PLAN.md` | Fases, tareas, criterios de aceptación. Se actualiza al avanzar. |
| `docs/DESPLIEGUE-TIENDA.md` | **Cómo está instalado el sistema en la tienda y cómo se mantiene.** |
| `docs/RESCATE-DATOS.md` | Cómo recuperar el catálogo del sistema anterior del cliente. |
| `docs/PREGUNTAS-CLIENTE.md` | Preguntas de negocio para la reunión con el cliente. |
| `docs/DECISIONES.md` | Decisiones técnicas importantes con su justificación. |
| `docs/DESIGN.md` | Sistema visual: colores, tipografía, espaciado, radios y componentes. |
| `docs/GUION-DEMO.md` | Guion paso a paso de la demostración. |
| `docs/MANUAL-USUARIO.md` | Manual para quien opera la caja. |
| `docs/TECNICA.md` | Documentación técnica e instrucciones de compilación. |
