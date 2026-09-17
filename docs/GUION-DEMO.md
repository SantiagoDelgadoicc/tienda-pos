# Guion de la demostración

**Para qué sirve:** llevar escrito lo que vas a hacer delante del cliente, con los códigos
exactos, para no improvisar. Una demo que se traba buscando qué escanear transmite lo
contrario de lo que se quiere transmitir.

**Duración objetivo:** 8 a 10 minutos de demostración, y el resto de la reunión para
escucharle a él. Lo importante de esta reunión no es lo que le muestres: es lo que él diga
cuando lo vea.

---

## Antes de empezar

- [ ] Ejecutar `PuntoYFamaCaja.exe --verificar` en el equipo donde harás la demo y comprobar que
      el informe dice `RESULTADO: CORRECTO`. Se hace en dos segundos y evita el escenario de
      descubrir un problema con el cliente delante.
- [ ] Abrir el programa una vez y hacer una venta de prueba, para que el catálogo demo esté
      cargado y el sistema "caliente".
- [ ] **Borrar esa venta de prueba**: cierra el programa y borra
      `%LOCALAPPDATA%\TiendaPOS\tienda.db` para arrancar limpio. Un informe del día con
      ventas fantasma genera preguntas que no aportan nada.
- [ ] Llevar los códigos de abajo impresos o en el teléfono.
- [ ] Si tienes una pistola lectora, probarla antes. Si no, no pasa nada: se teclean los
      códigos, y conviene decirlo abiertamente al empezar.
- [ ] Llevar `PREGUNTAS-CLIENTE.md` a mano.

## Códigos para la demostración

| Producto | Código | Precio |
|---|---|---|
| Bebida Cola 1.5 L | `7801234000001` | $2.290 |
| Leche Entera 1 L | `7801234000100` | $1.290 |
| Arroz Grado 2 1 kg | `7801234000193` | $1.590 |
| Café Instantáneo 170 g | `7801234000308` | $5.490 |
| Papas Fritas 250 g | `7801234000353` | $2.790 |
| Pan de Molde Blanco 500 g | `7801234000445` | $2.190 |
| Papel Higiénico 4 rollos | `7801234000520` | $2.990 |
| Fósforos caja | `7801234000612` | $490 |
| **Código que no existe** | `7790000000017` | — |

Accesos: **Administrador** PIN `1234` · **Cajero** PIN `1111`.

---

## Paso 1 — Lo que pidió (1 minuto)

Empieza por su frase, no por la tuya.

> "Usted me pidió un sistema que lea el código de barras y muestre el precio. Esto es
> exactamente eso."

Pulsa **F2** para entrar en la consulta de precio y escanea (o teclea) `7801234000353`.

Aparece **Papas Fritas 250 g · $2.790** en letras enormes.

Escanea `7801234000308`. Aparece **Café Instantáneo 170 g · $5.490**.

**Qué decir:** que la pantalla se limpia sola a los 15 segundos, para que el precio de un
cliente no quede en pantalla cuando llegue el siguiente. Y que la letra es así de grande a
propósito, para que se lea desde el otro lado del mostrador.

**No sigas hasta que él reaccione.** Si dice "esto es justo lo que quería", ya sabes que el
resto de la demo es un extra. Si dice "sí, pero además necesito…", acabas de descubrir el
requisito más importante del proyecto.

## Paso 2 — Cuando el código no existe (1 minuto)

Sigue en la pantalla de consulta. Escanea `7790000000017`.

Aparece **Producto no encontrado** con el código en rojo.

**Qué decir:** que este es el error más frecuente en una caja real, y que por eso tiene su
propia pantalla en vez de un mensaje técnico. Que el código queda anotado en una lista de
pendientes para que él lo cargue después, sin tener que acordarse.

Es un buen momento para preguntarle: *"¿todos sus productos traen código de barras?"*

## Paso 3 — Una venta completa (3 minutos)

Pulsa **Esc** para volver a la pantalla de venta.

Escanea seguido: `7801234000001`, `7801234000001` (el mismo dos veces), `7801234000100`,
`7801234000445`, `7801234000612`.

**Qué mostrar:**
- Que el mismo producto escaneado dos veces se agrupa en una línea con cantidad 2, en vez de
  aparecer repetido.
- Que el total se actualiza solo, en grande, a la derecha.
- Que no se ha tocado el ratón ni una vez.

Pulsa la **flecha derecha** para sumar otra unidad a la línea seleccionada, y la **izquierda**
para volver a bajarla (se arrepintió el cliente). Las mismas acciones están como **+** y **−**
en cada línea, para quien prefiera el ratón.

Pulsa **F12** para cobrar, confirma, y muestra el mensaje **Venta N° 1 registrada**.

## Paso 4 — Un descuento (2 minutos)

Escanea `7801234000308` y `7801234000193`.

Pulsa **F4**, deja marcado *a toda la venta*, elige *porcentaje*, escribe `10` y aplica.

**Qué decir:** que el descuento se puede hacer por monto ("te lo dejo en cinco mil") o por
porcentaje ("te hago el diez"), porque en una tienda se usan las dos formas.

Ahora selecciona una de las dos líneas, pulsa **F4** otra vez y marca *solo a este producto*.
Descuenta `500`.

**Qué mostrar:** que la rebaja aparece en la columna **Desc.** de esa línea, y que el panel de
la derecha dice que el descuento viene de la venta y de los productos.

**Qué decir:** que así queda registrado **de qué producto** era la rebaja, y que mañana, al
mirar esa venta, se puede explicar. Es el caso del pan del día anterior o del envase abollado.

Cobra con **F12**.

## Paso 4b — El aspecto del programa (30 segundos, opcional)

Pulsa **F9** y cambia el tema a *oscuro*. La pantalla entera cambia al instante.

**Qué decir:** que es para locales con poca luz o turnos de noche, y que desde ahí también se
apaga el pitido o la confirmación al cobrar. **No es un requisito del cliente**: se muestra
solo si pregunta por la apariencia. Vuelve al tema claro antes de seguir.

## Paso 5 — Su negocio, no solo la caja (2 minutos)

Pulsa **F8**. Como estás como cajero, el sistema pide el PIN de administrador: entra con
`1234`.

**Qué mostrar:** el total vendido del día, cuántas ventas, cuántos artículos, y el detalle de
cada venta al seleccionarla.

**Qué decir:** que hoy muestra el día, y que si le interesa se puede ampliar a la semana, al
mes, o a qué productos se venden más. **No prometas que ya lo hace.**

Pulsa **F7** para mostrar el catálogo: 65 productos, filtro por nombre o código, y edición de
precios. Muestra el botón **Códigos pendientes**: ahí está el código del Paso 2.

## Paso 6 — Cerrar y escuchar (el resto de la reunión)

> "Esto es un prototipo. Funciona de verdad, pero está hecho para que usted lo vea y me diga
> qué le falta y qué le sobra."

Y entonces saca `PREGUNTAS-CLIENTE.md` y empieza por el **Bloque A**.

---

## Lo que NO debes prometer

Dilo tú antes de que lo pregunte. Un prototipo honesto genera más confianza que uno que
promete de más:

- **No emite boletas ni facturas** y no está conectado al SII.
- **No registra medios de pago** ni calcula vuelto.
- **No funciona en varias cajas a la vez.**
- **No maneja productos por peso ni a granel.**
- Los productos y precios que se ven son **un catálogo de ejemplo**, no los suyos.

## Si algo se cae en medio de la demo

El programa está hecho para no cerrarse: un error muestra un aviso y la caja sigue abierta.
Si aparece ese aviso, no lo escondas. Di que el sistema registró el problema en su archivo de
sucesos y sigue funcionando, y continúa. Un sistema que aguanta un error delante del cliente
demuestra más que uno que no falla porque no se le exigió nada.

Si el programa no abriera, la salida es ejecutar `PuntoYFamaCaja.exe --verificar` y leer el
informe: dice exactamente qué falló.
