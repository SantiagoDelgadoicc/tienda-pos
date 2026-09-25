# Despliegue en la tienda

**Cómo está montado el sistema en el local del cliente, por qué está montado así, y cómo
se mantiene.**

Este documento describe una instalación **real y en producción**, no un plan. Todo lo que
está aquí se ejecutó en la tienda y quedó funcionando el 2026-09-15.

Complementa a los otros documentos, no los repite:

| Documento | Para qué |
|---|---|
| `TECNICA.md` | Cómo se compila y cómo está hecho por dentro |
| `MANUAL-USUARIO.md` | Cómo se opera la caja |
| `DECISIONES.md` | Por qué se tomó cada decisión técnica |
| **`DESPLIEGUE-TIENDA.md`** | **Cómo quedó instalado y cómo se mantiene** |

---

> **Aviso del 2026-09-17.** Este documento describe la instalación hecha con
> `TiendaPOS.exe`. Desde D-027 el ejecutable se llama **`PuntoYFamaCaja.exe`**. Actualizar la
> tienda no es copiar la carpeta nueva encima: hay que rehacer los accesos directos de los dos
> PC, porque los actuales apuntan a un archivo que ya no existirá. La carpeta de datos
> (`%LOCALAPPDATA%\TiendaPOS`) **no cambia** y no hay que tocarla.

## 1. Ficha de la instalación

```
PC 1  (principal)      192.168.50.1     tiene la base de datos y hace de servidor
PC 2  (secundaria)     192.168.50.2     no tiene base: se la pide al PC 1
Puerto                 8477
Enlace                 cable de red directo, ~30 m por el techo
```

| | Ruta |
|---|---|
| Programa | `C:\TiendaPOS\` (el `.exe` más la carpeta `_internal`) |
| Datos | `%LOCALAPPDATA%\TiendaPOS\` |
| Base de datos | `%LOCALAPPDATA%\TiendaPOS\tienda.db` — **solo en el PC 1** |
| Configuración de red | `%LOCALAPPDATA%\TiendaPOS\red.json` — en los dos, con contenido distinto |
| Respaldos | `%LOCALAPPDATA%\TiendaPOS\backups\` |
| Registro | `%LOCALAPPDATA%\TiendaPOS\logs\tienda_pos.log` |

Versión del esquema de base de datos: **3**. Versión del protocolo de red: **1**.

Los dos equipos abren el programa solos al encender, mediante un acceso directo en la
carpeta de Inicio de Windows.

---

## 2. De dónde viene esta instalación

El cliente pidió originalmente **una sola cosa**: *"quiero un sistema de tienda que lea el
código de barras de un producto y despliegue su precio"*. Todo lo demás son decisiones
nuestras, y conviene no olvidarlo (ver `CLAUDE.md`, punto 3).

En la reunión del **2026-09-13** aportó la información que dio forma a este despliegue:

- Su sistema anterior **se le quedaba pegado**. Es una queja de usuario, pero es también un
  dato técnico: la forma barata y habitual de hacer "dos PC" es dejar la base de datos en
  una carpeta compartida de red, y ese arreglo es exactamente el que produce cuelgues.
- El sistema debe funcionar en **dos PC**.
- Tenía un catálogo en un computador que ya no enciende.
- Mencionó **LocalShop**, un servicio chileno por suscripción, y preguntó si se podía hacer
  algo parecido. **Se lo habían ofrecido y no lo compró.** No rechazó la funcionalidad:
  rechazó la mensualidad.

Ese último punto explica la forma del producto entregado: **pago único, sin suscripción, sin
internet, y el sistema sigue funcionando aunque el desarrollador desaparezca.** Es lo que
LocalShop no le podía dar.

### Lo que el cliente retiró

El **2026-09-14** comunicó que la **familia** y el **precio de compra** de los productos no
le interesan, pese a haber dicho el día anterior que su sistema anterior los guardaba. Las
decisiones `D-016` y `D-017` quedaron **retiradas**, y con ellas cualquier informe de margen.

Queda anotado el riesgo: el costo es el único dato que permite responder *"¿cuánto gané?"*, y
recuperarlo más adelante significa teclear el catálogo entero otra vez.

---

## 3. Cómo funciona el montaje

```
        PC 1  (principal)                      PC 2  (secundaria)
   ┌─────────────────────────┐            ┌─────────────────────────┐
   │  Interfaz (Qt)          │            │  Interfaz (Qt)          │
   │        ↓                │            │        ↓                │
   │  SesionLocal            │            │  SesionRemota           │
   │        ↓                │            │        │                │
   │  services/              │            │        │                │
   │        ↓                │            │        │                │
   │  tienda.db  ←── servidor HTTP ───────────── HTTP/JSON          │
   │                         │  cable     │   puerto 8477           │
   └─────────────────────────┘            └─────────────────────────┘
```

**Hay una sola base de datos y vive en el PC 1.** El PC 2 no guarda nada: cada vez que
necesita un precio, un producto o registrar una venta, se lo pide al PC 1 por la red.

Consecuencias de ese diseño, y todas son deliberadas:

- **Un precio cambiado en un PC se ve en el otro al instante.** No hay sincronización que
  pueda fallar, porque no hay dos copias que sincronizar.
- **El PC 1 nunca depende de la red.** Tiene la base al lado. Vende siempre, aunque el PC 2
  esté apagado o el cable se corte.
- **Si el PC 1 está apagado, el PC 2 no puede vender**, y lo dice con claridad. Es a
  propósito (condición 4 de `D-015`): vender sin poder ver el stock real descuadra el
  inventario, y dos cajas vendiendo a ciegas generan conflictos que no se resuelven bien.

La superficie que cruza la red son **12 operaciones**, todas declaradas en `_OPERACIONES`
dentro de `red/servidor.py`. Lo que no esté ahí no se puede pedir por la red.

Detalle de implementación que importa para el soporte: **el servidor expone la capa de
servicios, nunca la de repositorios**. Así cada petición de red es una operación completa y
por tanto una única transacción, y no un trozo de consulta que podría quedarse a medias.

---

## 4. Por qué cable y no wifi

Los dos equipos tienen wifi por un adaptador USB, así que el wifi era posible. Se eligió
cable directo, y las razones ordenadas por peso:

| | Cable directo | Wifi |
|---|---|---|
| ¿La dirección cambia sola? | **Nunca** | Sí, si el router la reasigna |
| ¿Depende del router del local? | **No** | Sí, y de su contraseña |
| Cortes y latencia | **Ninguno** | Los del wifi |
| Listo al encender | **Sí** | No siempre |

Lo decisivo fue **no depender de nadie**. Con cable no hace falta entrar al router, ni
conocer su contraseña, ni confiar en que respete una reserva de dirección. El día que el
router cambie la IP del PC 1 —y algún día lo hará— la caja 2 dejaría de conectar sin que
nadie hubiera tocado nada, y el mensaje de error no diría que el problema es ese.

**El wifi de los dos equipos no se tocó.** El cable es una segunda red, privada, solo entre
las dos cajas. Sin puerta de enlace, a propósito: poner una haría que Windows intentara
salir a internet por ese cable y rompería el wifi.

**Las direcciones son fijas** (`192.168.50.1` y `192.168.50.2`) porque en un cable directo
no hay router que las reparta. Sin direcciones fijas, Windows acabaría inventándose una
`169.254.x.x`, tardaría casi un minuto y cambiaría cada vez.

Si el cable fallara algún día, existe `PLAN-B-WIFI.bat` en el kit. Funciona, pero peor, y
obliga a reservar la dirección en el router.

---

## 5. El kit del pendrive

Todo el despliegue y el mantenimiento se hacen **desde un pendrive, con doble clic**. No
hace falta Python, ni consola, ni saber nada del proyecto. Esta fue la parte que mejor
funcionó en la tienda y es la que conviene conservar.

Contenido del pendrive:

```
TiendaPOS\                        el programa completo (~114 MB, .exe + _internal)
tienda.db                         copia del catálogo
INSTRUCCIONES.txt                 el mismo procedimiento, en texto plano
PASO-1-RESPALDAR.bat              PC 1 · solo copia, no cambia nada
PASO-2-ACTUALIZAR-PROGRAMA.bat    los dos · NO toca ninguna base de datos
PASO-3-PC1-PRINCIPAL.bat          PC 1 · IP fija, cortafuegos, modo servidor, arranque solo
PASO-4-PC2-SECUNDARIA.bat         PC 2 · IP fija, modo caja, arranque solo
PLAN-B-WIFI.bat                   si el cable falla
PROBAR-CONEXION.bat               PC 2 · comprueba si el PC 1 responde
DIAGNOSTICO.bat                   cualquiera · dice qué papel cree que juega el equipo
VER-MI-IP.bat                     muestra la dirección del equipo
_red_cable.ps1                    detecta la tarjeta de cable y le pone la IP fija
```

Los archivos viven en `INSTALACION/` dentro del repositorio. Para armar el pendrive:

```bash
python tools/construir.py
```

y después copiar `dist\TiendaPOS\` y el contenido de `INSTALACION\` a la raíz del pendrive.
En Windows conviene usar `robocopy` en vez de `cp`, que falla al escribir archivos grandes
en unidades extraíbles.

### Principios con los que están escritos

Estos scripts tocan la única cosa irreemplazable que tiene el cliente, así que siguen reglas
estrictas:

1. **Separar lo que toca datos de lo que no.** `PASO-2` actualiza el programa y **nunca**
   toca la base de datos. Eso permite actualizar el sistema sin ningún riesgo.
2. **Respaldar antes que nada.** `PASO-1` es lo primero y solo copia.
3. **Nada se borra, todo se aparta.** El catálogo de ejemplo del PC 2 se renombra a
   `tienda-NO-USAR.db`; una base anterior en el PC 1 se guarda como `tienda-ANTERIOR.db`.
4. **Pedir permisos de administrador solos.** Los pasos 3 y 4 se relanzan elevados sin que
   nadie tenga que acordarse del clic derecho.
5. **Decir qué comprobar después de cada paso**, y qué hacer si no cuadra.
6. **Finales de línea CRLF.** Un `.bat` con finales de línea de Unix falla de formas
   silenciosas, sobre todo con `goto` y con bloques `if (...)`. Lo garantiza `.gitattributes`.

---

## 6. Instalar o actualizar desde el pendrive

### Actualizar el programa (lo habitual)

Es la operación más frecuente y la más segura. En cada equipo:

1. Cerrar Tienda POS
2. Enchufar el pendrive
3. Doble clic en **`PASO-2-ACTUALIZAR-PROGRAMA.bat`**
4. Abrir el programa

**No toca la base de datos.** Si la versión nueva trae una migración de esquema, se aplica
sola en el primer arranque del PC 1.

> Actualizar **los dos equipos**. La caja secundaria comprueba la versión al conectar y se
> niega a trabajar si no coincide (condición 3 de `D-015`). Es deliberado: trabajar contra un
> servidor de otra versión es la forma silenciosa de corromper datos.

### Actualizar a la versión con un usuario por empleado (fase 15)

*Añadido el 2026-09-24.* Es la primera actualización que cambia cómo se entra, así que no basta
con los cuatro pasos de arriba. Hacerla con el dueño delante: es él quien tiene que crear los
usuarios de sus empleados.

**Antes de ir.** Tener decididos con el cliente los nombres de las personas que atienden.

**En la tienda, con las dos cajas paradas:**

1. **Actualizar los dos PC en la misma visita.** Cambian el protocolo entre cajas y el esquema
   de la base: la secundaria se niega a trabajar contra una principal sin actualizar, y lo dice al
   arrancar. La base se migra sola en el primer arranque del PC 1 (hacer antes un respaldo).
2. Abrir el PC 1 y entrar como **`Administrador`** con el PIN de siempre.
3. Ir a **Usuarios** (barra lateral, sección Administración) y, con **Nuevo usuario**, dar de alta
   a cada empleado. El sistema genera cada PIN y lo enseña **una sola vez**: que cada uno lo
   anote en el momento.
4. Seleccionar a **`Administrador`** y pulsar **PIN nuevo**. El suyo está publicado en el manual
   desde el principio, y mientras siga valiendo cualquiera puede entrar como administrador.
5. Seleccionar a **`Cajero`**, el usuario genérico, y pulsar **Dar de baja**. Sus ventas siguen a
   su nombre en los informes; lo único que cambia es que ya no se puede entrar con él.
6. **Poner nombre a cada caja** (fase 16). En la carpeta de datos de cada PC, abrir `red.json`
   con el Bloc de notas y añadir la línea `"nombre_caja": "Caja 1"` —o el nombre que diga el
   cliente, pregunta H8—, con **nombres distintos** en los dos PC. Es el nombre con que cada caja
   firma sus ventas en el cierre: si los dos se llamaran igual, sus ventas se mezclarían sin
   aviso. Sin esa línea se usa el nombre del PC, que funciona pero no se lee bien.
7. Comprobar en el PC 2 que cada empleado entra con su PIN, y que **al pie de la barra lateral**
   de cada caja aparece su nombre (por ejemplo "Cajero · Caja 2").
8. **Arqueo de caja** (fase 19, D-036). Desde esta versión **no se cobra con la caja cerrada**.
   - Con el dueño, fijar el **monto de apertura**: en **Efectivo**, abajo, "Cierres anteriores" →
     **Cambiar**. Es el monto con que se propone abrir cada caja; el cliente dijo que lo dejaría
     preparado cada mañana si el sistema se lo indica.
   - Abrir cada caja contando el cajón: el programa lo propone al arrancar, y si se deja para
     después, lo vuelve a pedir en el primer cobro.
   - Enseñarle al dueño a anotar un **retiro** (pide su PIN y queda a su nombre) y a los
     empleados un **pago a proveedor** (con el nombre del proveedor, queda a su nombre).
   - Al cerrar, quien cuenta **no ve cuánto debería haber**; el dueño lo ve en Efectivo con su
     PIN, "Ver las cuentas". Decírselo en voz alta, para que nadie crea que es un fallo.

**Lo que no hay que hacer:**

- **No poner `--demo` en ningún acceso directo de la tienda.** Esa opción es para demostraciones:
  en una base vacía carga los productos de ejemplo y los dos usuarios con PIN publicados. Sobre
  la base de la tienda, que no está vacía, no haría nada; pero en una instalación desde cero sí,
  y es exactamente como se mezclaron los 65 productos de ejemplo la primera vez.
- No borrar usuarios de la base a mano. La baja es lógica a propósito: las ventas los referencian.

**Si alguien olvida el PIN:** lo arregla el administrador desde Usuarios, con **PIN nuevo**.

**Si el que olvida el PIN es el único administrador:** en el **PC 1**, abrir una ventana de
comandos en la carpeta del programa y ejecutar

```
PuntoYFamaCaja.exe --reiniciar-admin
```

Pide el nombre del administrador, le genera un PIN nuevo (lo crea si no existe) y lo enseña.
Hace un respaldo antes de tocar nada y deja constancia en el registro. **En el PC 2 no funciona
a propósito**: la base está en el PC 1, y rescatar un administrador por la red sería dejar la
puerta abierta a cualquiera del mismo cable.

### Instalación desde cero

**En el PC 1:**

| Paso | Qué hace | Qué comprobar |
|---|---|---|
| Cerrar el programa | | |
| `PASO-1-RESPALDAR.bat` | Copia el catálogo al pendrive | Lista los archivos copiados |
| `PASO-2-ACTUALIZAR-PROGRAMA.bat` | Copia el programa | Acceso directo en el escritorio |
| *Enchufar el cable de red* | | Luces en los dos conectores |
| `PASO-3-PC1-PRINCIPAL.bat` | IP fija, cortafuegos, modo servidor, arranque automático | Dice "PC 1 LISTO" |
| Abrir el programa | | **Que estén todos los productos** |

Dejar el programa abierto y pasar al otro equipo.

**En el PC 2:**

| Paso | Qué hace | Qué comprobar |
|---|---|---|
| `PASO-2-ACTUALIZAR-PROGRAMA.bat` | Copia el programa | |
| `PASO-4-PC2-SECUNDARIA.bat` | IP fija, modo caja, aparta el demo, arranque automático | Prueba la conexión y lo dice |
| Abrir el programa | | Pide el PIN |

**En el PC 2 no se copia ningún `tienda.db`.** Si se le pone uno, se acaba con dos catálogos
distintos, que es justo lo que este montaje evita.

### Reponer el catálogo en el PC 1

Solo si hiciera falta restaurar. **Con el programa cerrado:**

```
del "%LOCALAPPDATA%\TiendaPOS\tienda.db-wal" "%LOCALAPPDATA%\TiendaPOS\tienda.db-shm"
copy /Y "E:\tienda.db" "%LOCALAPPDATA%\TiendaPOS\tienda.db"
```

⚠️ **El borrado de los dos primeros archivos no es opcional.** Son restos del catálogo
anterior; si se quedan junto a un `tienda.db` nuevo, SQLite intenta aplicarles los cambios de
otro archivo y **corrompe la base**. Si dice "no se encuentra el archivo", perfecto: no había
restos.

---

## 7. El día a día

```
PC 1:  se enciende → Tienda POS se abre solo → pide el PIN
PC 2:  se enciende → Tienda POS se abre solo → espera al PC 1 → pide el PIN
```

**No importa cuál se encienda primero.** La caja secundaria espera hasta **90 segundos**
(`ESPERA_SERVIDOR_AL_ARRANCAR_S`) a que la principal esté lista, mostrando un cartel que se
puede cancelar. Solo si se agota esa espera aparece un diálogo con un botón de reintentar.

Lo único manual es escribir el PIN, y no se puede quitar: es lo que permite saber quién
vendió qué.

**El efectivo** (fase 19): cada caja se abre por la mañana con el efectivo que tiene y se cierra
al final contándolo, en la pantalla **Efectivo**. Entre medias, cada retiro del dueño y cada pago
a proveedor se anota ahí. Una caja cerrada no cobra: al intentarlo, ofrece abrirla. Si se cambia
de turno a mitad de día, se cierra y se vuelve a abrir con lo que quede en el cajón.

### Reglas para quien atiende

- **El PC 1 tiene que estar encendido** para que el PC 2 pueda vender. No es un fallo.
- Si el PC 2 dice que no hay conexión, lo primero es mirar si el PC 1 está encendido y con
  el programa abierto.
- **No desenchufar el cable** que une las dos máquinas.

### Condiciones del equipo principal

- **Suspensión desactivada.** Si el PC 1 se duerme, la caja 2 deja de vender.
- Si Windows pide contraseña al encender, **el arranque automático no se dispara hasta que
  alguien inicia sesión**. No es un fallo del programa, pero rompe el "encender y trabajar".

---

## 8. Cuando algo falla

| Síntoma | Qué ejecutar |
|---|---|
| El PC 2 no conecta | `PROBAR-CONEXION.bat` en el PC 2 |
| El PC 2 muestra productos inventados | `DIAGNOSTICO.bat` en el PC 2 |
| El cable dejó de funcionar | `PLAN-B-WIFI.bat` en los dos |
| Cualquier otra cosa | `DIAGNOSTICO.bat` en ambos, y revisar los registros |

### La comprobación que hay que hacer siempre primero

Desde el navegador del PC 2:

```
http://192.168.50.1:8477/api/estado
```

Tiene que responder un JSON con las versiones. **Si eso no funciona, nada más va a
funcionar**, y el problema es de red o de cortafuegos, no del programa.

Que ese endpoint sea `GET` y se pueda mirar desde un navegador cualquiera **no es casualidad**:
es parte de `D-023`, precisamente para poder diagnosticar desde el propio local sin
herramientas.

> **Ojo con el `ping`.** Windows lo bloquea por defecto. Si el ping falla pero la dirección de
> arriba responde, **está todo bien**. Por eso `PROBAR-CONEXION.bat` prueba las dos cosas y
> avisa de que la que importa es la segunda.

### Ver productos de ejemplo en el PC 2

Significa una cosa concreta: **ese equipo no está leyendo `red.json`**, así que arranca en
modo suelto, se crea su propia base y carga el catálogo demo. Se arregla volviendo a
ejecutar `PASO-4-PC2-SECUNDARIA.bat`.

---

## 9. Respaldos, y el asunto del WAL

El programa copia la base **al abrir y al cerrar**, y conserva las 7 últimas en
`%LOCALAPPDATA%\TiendaPOS\backups\`.

Que el respaldo se haga también al cerrar se añadió por un caso real de esta instalación: el
respaldo solo corría al arrancar, copiando el estado *anterior* a la sesión que empezaba. El
resultado fue que quien cargó el catálogo entero en una sola sesión larga se quedó con **cero
copias de ese trabajo**.

> **Estos respaldos están en el mismo disco.** No sirven si el disco se rompe. Conviene copiar
> esa carpeta a un pendrive cada cierto tiempo.

### Copiar la base de datos a mano

**Cerrar el programa primero. Siempre.**

SQLite funciona en modo WAL: lo que se escribe vive en `tienda.db-wal` hasta que se integra
en el archivo principal. Con el programa abierto, **copiar solo `tienda.db` produce una base
vacía que parece un respaldo**. Medido en esta instalación:

| | `tienda.db` | `tienda.db-wal` | Copiar solo el `.db` da |
|---|---|---|---|
| Programa abierto | 4 KB | 918 KB | `no such table: producto` |
| Tras cerrar bien | 73 KB | 0 KB | el catálogo completo |

Al cerrar, `cerrar_limpiamente()` integra el WAL y deja el `.db` autocontenido. A partir de
ahí, copiarlo a un pendrive es seguro aunque quien lo haga no sepa nada de esto.

Si hay que copiar con el programa abierto —no debería ocurrir— hay que llevarse **los tres
archivos juntos**: `.db`, `-wal` y `-shm`. Es lo que hace `PASO-1-RESPALDAR.bat`.

---

## 10. Lo que NO está entregado

Importante que esté escrito, porque es fácil darlo por incluido:

| Falta | Consecuencia práctica |
|---|---|
| **Gestión de usuarios** (fase 12) | Las dos personas entran con la misma cuenta. **El informe por cajero no distingue quién vendió** |
| Importación CSV (fase 10) | El catálogo solo se carga a mano |
| Movimientos de inventario (fase 9) | No se puede explicar un descuadre de stock |
| Rendimiento medido (fase 11) | Sin verificar con catálogo grande |
| Instalador (fase 14) | Se instala con los scripts de `INSTALACION/` |
| Boleta electrónica (SII) | Fuera de alcance por `D-006`. Es otro proyecto |
| Indicador de conexión permanente | Lo último de la condición 2 de `D-015`. Hoy avisa cuando falla, pero no muestra el estado de forma continua |

**Los PIN siguen siendo los de fábrica** (`1234` y `1111`), publicados en
`MANUAL-USUARIO.md`. Mientras no exista la pantalla de usuarios, se pueden cambiar con
`tools/cambiar_pin.py`, que necesita Python y por tanto no se puede ejecutar en la tienda.

Como la base de datos es una sola, **cambiar un PIN en el PC 1 afecta a las dos cajas al
instante**: no hay nada que sincronizar.

---

## 11. Lo que salió mal durante el despliegue

Se deja por escrito porque ninguno de estos problemas era visible desde el escritorio, y
volverían a aparecer en la siguiente instalación.

**El catálogo de ejemplo se mezcló con el real.** El programa carga 65 productos inventados
la primera vez que arranca con la base vacía. Cuando la tienda empezó a cargar los suyos
encima, quedaron 111 productos de los cuales 65 eran ficticios. Se resolvió con
`tools/limpiar_demo.py`, que funciona en seco por defecto y se niega a borrar un producto de
ejemplo que alguien haya llegado a vender.

*Lección:* en una instalación real, la carga de datos demo debería desactivarse
(`abrir_base_datos(con_datos_demo=False)`).

**Un precio con los campos intercambiados.** Un producto quedó con precio 30 y stock 1500,
cuando casi todos los demás tenían stock 30. Se detectó comparando contra el patrón del resto
del catálogo, no a ojo. Una vista previa de importación habría evitado que entrara.

**La conexión SQLite no se puede usar desde otro hilo.** El servidor corre en un hilo de
fondo, así que habría fallado en la primera consulta desde la caja 2. Se resolvió serializando
los accesos con un cerrojo en `SesionLocal`, y `conectar()` solo levanta la comprobación de
`sqlite3` cuando esa garantía existe.

**N+1 en el informe del día.** Pedía las líneas de cada venta dentro del bucle: en local es
invisible, por red son 200 idas y vueltas para un día de 200 ventas. Ahora son dos consultas.

**El cobro no era idempotente.** Si una petición de cobro agota su tiempo límite, la caja no
sabe si la venta se registró; reintentar la duplicaría y no reintentar la perdería. Se añadió
`venta.intento_id` con índice único (migración 3).

**El pendrive se desconectó dos veces** a mitad de copiar los 114 MB del programa. Conviene
verificar el número de archivos en origen y destino después de copiar.

---

## 12. Tiempo del despliegue

Dos visitas, en días distintos:

| Visita | Horario | Trabajo |
|---|---|---|
| Primera | 9:00 – 14:00 | Montaje de los dos equipos, carga del catálogo |
| Segunda | 9:30 – 12:00 | Cable de ~30 m por el techo, configuración de red, pruebas |
| | **7,5 h** | |

La segunda visita incluyó la prueba que de verdad cierra el despliegue: **apagar los dos
equipos y encenderlos de nuevo**, empezando por el secundario, para comprobar que el arranque
automático, la IP fija y la regla del cortafuegos sobreviven a un reinicio.

Esa prueba es obligatoria. Que todo funcione al terminar de instalar no garantiza que
funcione al día siguiente.
