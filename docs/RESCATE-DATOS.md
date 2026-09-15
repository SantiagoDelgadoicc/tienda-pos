# Rescate de los datos del sistema anterior

**Para qué sirve este documento.** El cliente tenía su catálogo completo —productos, cantidad,
precio de compra, precio de venta y familia— en un programa instalado en un PC que hoy no
enciende. Esos datos valen más que cualquier funcionalidad que podamos programar: son años de
trabajo suyo, y recargarlos a mano cuesta horas. Esta guía es el procedimiento para recuperarlos.

**Está escrita para ejecutarse sin saber todavía qué le pasa al PC ni en qué formato están los
datos.** Cada paso dice qué hacer, qué se espera obtener y qué hacer si falla.

**La regla que gobierna todo lo demás:** ese disco no se toca para nada que no sea leerlo. Nada de
reinstalar Windows, nada de formatear, nada de "reparar el arranque". El objetivo es sacar los
archivos, no dejar el PC funcionando.

---

## Paso 0 — Preguntar antes de tocar nada

Puede que no haga falta rescatar nada. Antes de mover un tornillo, preguntarle al cliente:

- ¿Tiene alguna copia en un **pendrive**, un disco externo o un correo con un adjunto?
- ¿Le pasó alguna vez la lista de productos a **su contador**, a un proveedor o a un familiar?
- ¿Tiene un **listado impreso** de precios, aunque esté desactualizado? Sirve como punto de partida.
- ¿Cómo se llamaba el programa? ¿Qué decía su pantalla de **"Acerca de"**? ¿Quién se lo vendió o se
  lo instaló? Esa persona puede tener el instalador y saber dónde guardaba los datos.
- ¿El programa tenía un botón de **respaldo o copia de seguridad**? ¿Dónde dejaba el archivo?
- ¿El programa estaba **en red con otro PC** de la tienda? Si es así, puede que exista una copia
  viva en el otro equipo, y además explicaría por qué se quedaba pegado (ver D-015 en
  `docs/DECISIONES.md`).

**Salida esperada:** el nombre del programa anterior, y la respuesta a si existe o no una copia.

**Si hay copia:** saltar al paso 4.

---

## Paso 1 — Diagnóstico del PC

"No enciende" puede significar cinco cosas distintas, y solo una de ellas es mala. Lo que hay que
observar, en este orden:

| Síntoma | Qué significa normalmente |
|---|---|
| Ni luces ni ventiladores, silencio total | Fuente de poder o cable. **El disco está intacto.** |
| Enciende, los ventiladores giran, pantalla negra sin logo | Placa, RAM o tarjeta de video. **El disco está intacto.** |
| Llega al logo del fabricante y se queda ahí, o reinicia solo | Windows dañado. **El disco casi seguro está intacto.** |
| Pantallazo azul repetido | Windows o un controlador. El disco, probablemente bien. |
| Chasquidos o zumbido rítmico, y la BIOS no detecta el disco | **Este es el caso malo.** Disco averiado. |

Comprobaciones baratas antes de dar nada por perdido: otro cable de poder, otro monitor y otro
cable de video, desconectar todos los periféricos, cambiar la pila de la placa (CMOS), sacar y
volver a poner la memoria RAM.

**Lo importante que hay que transmitirle al cliente:** *"no enciende" casi nunca significa "datos
perdidos"*. En un PC de escritorio lo que se rompe con más frecuencia es la fuente de poder, y el
disco sale entero. Conviene decírselo pronto, porque probablemente lleve semanas dándolos por
perdidos.

**Salida esperada:** saber si el disco es accesible o no.

---

## Paso 2 — Rutas de rescate, por orden de coste

### Ruta A — Sacar el disco y leerlo en otro PC *(la preferida)*

Funciona en todos los casos salvo el del disco averiado, e incluso sirve si el PC está
completamente muerto.

1. Abrir el equipo y localizar el disco. En un escritorio es una caja metálica de 3,5"; en un
   portátil suele estar bajo una tapa, o bajo el teclado en los muy antiguos.
2. Identificar el conector **antes de comprar nada**:
   - **SATA** (lo habitual desde 2005): adaptador SATA→USB o carcasa externa, unos 10–25 USD.
   - **IDE / PATA** (cable ancho y plano, anterior a 2005): adaptador IDE→USB, más caro y más raro.
   - **M.2 NVMe** (una tarjeta pequeña atornillada a la placa): **necesita otra carcasa distinta**,
     la de SATA no sirve. Comprobarlo antes de ir a la tienda.
3. Conectarlo por USB a un PC sano. Windows lo monta como una unidad más.
4. **No arrancar desde ese disco.** Solo leerlo.
5. Si Windows niega el acceso a la carpeta de usuario, hay que tomar posesión de la carpeta:
   clic derecho → Propiedades → Seguridad → Opciones avanzadas → Cambiar propietario.

### Ruta B — Arrancar el PC con un pendrive de Linux

Sirve si el PC enciende pero no llega a Windows, y evita abrir el equipo.

1. En otro PC, crear un pendrive de arranque con Ubuntu o Linux Mint (con Rufus, o con el creador
   oficial). Alternativa en Windows: Hiren's BootCD PE.
2. Arrancar el PC enfermo desde el pendrive eligiendo la opción **"Probar" / "Try without
   installing"**. Nunca "Instalar".
3. El disco de Windows se ve como una carpeta más. Copiar lo del paso 3 a un segundo pendrive o a
   un disco externo.

### Ruta C — Llevarlo a un técnico

Ruta perfectamente válida, **pero con la instrucción por escrito y por adelantado**:

> *Solo copiar los datos a un pendrive. No formatear, no reinstalar Windows, no "dejarlo como
> nuevo". Los archivos importan más que el computador.*

Este es el riesgo real de esta ruta, y no es el hardware. Un técnico que recibe un PC que no
arranca asume por defecto que su trabajo es dejarlo arrancando, y la forma rápida de conseguirlo es
reinstalar Windows encima. Ese es el único escenario en que se pierden datos que estaban
perfectamente sanos.

### Ruta D — Disco físicamente averiado

Si el disco hace chasquidos o la BIOS no lo ve, las rutas anteriores no sirven. Queda un
laboratorio de recuperación de datos: caro (varios cientos de dólares) y sin garantía de resultado.

**Es una decisión de coste del cliente, no nuestra.** Hay que planteársela en esos términos: lo que
cuesta la recuperación frente a las horas que cuesta recargar el catálogo a mano (paso 6). Para
unos cientos de productos, casi siempre gana recargar a mano.

---

## Paso 3 — Qué copiar

No hay que buscar un archivo concreto: todavía no sabemos cómo se llama. Se copia en bloque y se
investiga después, con calma, sobre la copia.

Carpetas, por orden de probabilidad:

1. **`C:\<NombreDelPrograma>\`** — los puntos de venta antiguos se instalan en la raíz de `C:` y
   guardan ahí mismo su base de datos. Es el primer sitio donde mirar.
2. `C:\Program Files\` y `C:\Program Files (x86)\` — la carpeta del programa.
3. **`C:\ProgramData\`** — carpeta oculta; hay que activar "mostrar elementos ocultos". Es donde
   guardan los datos los programas algo más modernos.
4. `C:\Users\<usuario>\AppData\Local\` y `C:\Users\<usuario>\AppData\Roaming\` — también ocultas.
5. `C:\Users\<usuario>\Documents\` y el Escritorio — ahí acaban los respaldos manuales y los Excel
   del dueño.

Después, un barrido del disco entero por extensión, que es lo que atrapa la base de datos aunque
esté en un sitio inesperado:

```
.mdb  .accdb        Access
.fdb  .gdb          Firebird / Interbase
.db   .sqlite       SQLite
.sdf                SQL Server Compact
.dbf  .cdx  .fpt    dBase / FoxPro
.dat  .bak          formatos propietarios y respaldos
.csv  .xls  .xlsx   listados y exportaciones
```

Anotar también el **nombre y la versión del programa**, y copiar su instalador si aparece: si los
datos están en un formato cerrado, el propio programa puede ser la única forma de abrirlos (paso 4,
último recurso).

**Salida esperada:** una carpeta en un disco sano con todo lo anterior. A partir de aquí, el disco
viejo se guarda y no se vuelve a tocar.

---

## Paso 4 — Identificar el formato y sacarlo a CSV

Con la copia a salvo, se mira qué hay. Árbol de decisión por extensión:

| Extensión | Qué es | Cómo se abre |
|---|---|---|
| `.mdb` / `.accdb` | **Access.** El caso más frecuente en puntos de venta antiguos | Access, el driver ODBC gratuito "Microsoft Access Database Engine", o `mdbtools` |
| `.fdb` / `.gdb` | Firebird / Interbase | IBExpert o FlameRobin. Usuario habitual `SYSDBA`, clave `masterkey` |
| `.dbf` | dBase / FoxPro. Viene con `.cdx` y `.fpt` al lado | `dbfread` en Python, o LibreOffice Base |
| `.sdf` | SQL Server Compact | Necesita el runtime de SQL Server Compact, hoy descatalogado |
| `.db` / `.sqlite` | SQLite | Cualquier visor. Caso trivial |
| `.dat` u otro | Formato propietario, posiblemente cifrado | Ver abajo |

**Si el formato es propietario o está cifrado**, el último recurso es el propio programa:
instalarlo en un PC sano, apuntarlo a los datos rescatados y usar **su** función de exportar o de
imprimir listados. Puede fallar si la licencia estaba atada al hardware del PC viejo; aun así,
imprimir a PDF el listado de productos desde el programa y transcribirlo sigue siendo más rápido
que recorrer la tienda entera con la pistola.

**Dos trampas que hay que evitar sí o sí:**

- **La codificación.** Los sistemas antiguos guardan en Windows-1252 o Latin-1, no en UTF-8. Si se
  exporta sin convertir, todas las tildes y las eñes salen rotas (`Jabón` → `JabÃ³n`) y hay que
  corregir el catálogo producto por producto. **Al exportar, forzar UTF-8.**
- **Los precios.** Vienen como texto con separador de miles (`1.290`) o con decimal en coma
  (`1290,00`). Hay que convertirlos a entero de CLP explícitamente, no confiar en que el importador
  lo adivine.

**Salida esperada:** un archivo por tabla, en CSV y en UTF-8. Sin normalizar todavía.

---

## Paso 5 — Normalizar al formato de importación

El sistema importa un CSV con estas columnas exactas (ver la fase 10 de `docs/PLAN.md`):

```csv
codigo_barras,nombre,precio_venta,stock
7802900000017,Leche entera 1 L,1290,24
```

*(Actualizado el 2026-09-14: eran `codigo_barras,nombre,familia,precio_venta,precio_compra,stock`.
El cliente retiró la familia y el precio de compra —D-016 y D-017—, así que el sistema ya no tiene
dónde ponerlos.* **Aun así, si el archivo rescatado los trae, no los borre:** *guárdelos en el CSV.
El importador ignora las columnas que no conoce, no cuesta nada conservarlas, y si el cliente
cambia de opinión el dato ya está. Recuperarlo después significa teclear el catálogo entero otra
vez.)*

Reglas de conversión:

- **Precios:** entero de CLP, sin puntos, comas ni símbolo de peso. `$1.290` → `1290`.
- **Códigos:** sin espacios ni guiones. Si traen ceros a la izquierda, se conservan: son parte del
  código.
- **Productos sin código de barras:** se les genera uno interno. El estándar EAN-13 reserva los
  códigos que empiezan por `2` para uso dentro del propio local, así que no chocan nunca con un
  producto de fábrica.
- **Stock negativo:** a 0, dejando constancia en el informe de importación. Un stock negativo en el
  sistema viejo es un descuadre suyo, no un dato que valga la pena conservar.
- **Familias y precio de compra:** el sistema ya no los usa (D-016 y D-017, retiradas). Si vienen en
  el archivo de origen, se arrastran al CSV sin tocarlos y el importador los ignora. No se pierde
  nada por conservarlos y se pierde el catálogo entero por descartarlos.

**Salida esperada:** un único CSV listo para importar.

---

## Paso 6 — Plan B: recarga manual

Si el rescate falla, no es el fin del proyecto. Con un modo de carga rápida —solo teclado: pistola
→ nombre → precio de venta → stock → Enter— la carga a mano es perfectamente viable, y desde el
2026-09-14 con dos campos menos por producto:

- Unos 15–20 segundos por producto con dos personas, una dictando y otra escaneando.
- Para un catálogo de unos 300 productos, alrededor de **2 horas**.
- **Cargar primero los 50 productos que más rotan.** Con eso la caja puede abrir el mismo día, y el
  resto se completa sobre la marcha: cada código que se escanee y no exista queda anotado en la
  lista de códigos pendientes que el sistema ya lleva.

Dicho de otro modo: el peor caso cuesta una tarde, no el proyecto. Conviene decírselo al cliente
para que la decisión sobre el laboratorio de recuperación (ruta D) se tome con ese número delante.

---

## Advertencia que hay que darle al cliente en cualquier caso

**Aunque el rescate salga perfecto, las cantidades estarán equivocadas.** El PC lleva tiempo
apagado y la tienda siguió vendiendo. Los precios y los nombres se importan tal cual;
el stock no: hay que **contarlo físicamente una vez** al poner el sistema en marcha.

Es mejor decirlo antes de importar que después, cuando el cliente vea números que no le cuadran y
concluya que el sistema nuevo también falla.

---

## Resumen operativo

| Paso | Acción | Sin qué no se puede seguir |
|---|---|---|
| 0 | Preguntar si ya existe una copia | — |
| 1 | Diagnosticar el PC | — |
| 2 | Rescatar el disco (ruta A, B, C o D) | Adaptador USB o pendrive de arranque |
| 3 | Copiar en bloque y barrer por extensión | Disco accesible |
| 4 | Identificar el formato y exportar a CSV en UTF-8 | La copia del paso 3 |
| 5 | Normalizar al CSV de importación | El CSV del paso 4 |
| 6 | *(solo si 2–5 fallan)* recarga manual | Nada; siempre es posible |
