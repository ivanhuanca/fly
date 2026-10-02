# Moscas de escritorio: historial y prompt de creacion

Este documento registra como evoluciono la aplicacion y contiene un prompt reutilizable para reconstruirla o continuar desarrollandola en otro agente de codigo.

## Historial paso a paso

1. **Sprite inicial.** El proyecto comenzo con `sprite_fly.png`, una imagen RGBA en una cuadricula 6x6 de 36 poses. Los cuadros 0-17 muestran a la mosca aseandose y los cuadros 18-35 caminando.
2. **Primera animacion.** Se uso Python con Tkinter para mostrar un cuadro a la vez, mover la mosca hacia destinos aleatorios y alternar entre caminar y asearse cada cierto tiempo. Se agregaron los atajos `Ctrl+Alt+F8` para pausar y `Ctrl+Alt+F9` para salir.
3. **Ventana de escritorio.** La mosca se dibujo en una ventana sin bordes, transparente y siempre visible. Los estilos Win32 `WS_EX_TRANSPARENT`, `WS_EX_TOOLWINDOW` y `WS_EX_NOACTIVATE` permiten pasar los clics al escritorio y evitan robar el foco.
4. **Correccion del recorte y la transparencia.** Tkinter interpreto el PNG con dimensiones logicas afectadas por el escalado de Windows, por lo que se cambio el procesamiento a Pillow. Los cuadros se recortan directamente de los pixeles RGBA originales y se dividen usando limites proporcionales; esto tambien admite atlas cuyas dimensiones no sean divisibles exactamente entre seis.
5. **Limpieza de manchas.** El atlas tenia pixeles oscuros semitransparentes fuera de la silueta. En cada cuadro reducido se pone a cero el alfa menor que 17 y se eliminan componentes conectados de menos de cuatro pixeles. Las 36 poses se comprobaron para conservar la silueta.
6. **Giro al caminar.** La direccion se calcula desde el vector entre la posicion actual y el destino. Se usan 16 orientaciones, se reserva margen transparente suficiente para no recortar las diagonales y se guardan en una cache las rotaciones ya generadas.
7. **Varios atlas.** Se incorporaron `1.png`, `2.png` y `3.png`, cada uno con 36 celdas utilizables. El recorte proporcional admite, por ejemplo, que `2.png` mida 2048x2048 mientras los otros miden 1254x1254.
8. **Panel de control en vivo.** La aplicacion paso a una ventana raiz de control que administra una ventana transparente independiente por mosca. El panel permite elegir entre 0 y 20 moscas, el tamano entre 24 y 128 px en incrementos de 4, y el sprite. Las moscas existentes se actualizan sin reiniciar la aplicacion.
9. **Bandeja del sistema.** Se agrego `pystray` y el icono `fly.ico`. Cerrar el panel lo oculta sin detener la simulacion. El icono permite mostrar los controles, pausar o reanudar y salir. Un doble clic en el icono vuelve a mostrar el panel.
10. **Distribucion.** Pillow y pystray se declaran en `requirements.txt`. `MoscasEscritorio.spec` incluye los tres atlas, `fly.ico` y el backend Windows `pystray._win32`; PyInstaller genera una aplicacion de una sola pieza y sin consola.

## Prompt reutilizable

```text
Actua como agente de programacion senior y crea o continua una aplicacion de escritorio para Windows llamada "Moscas de escritorio". Implementa el codigo en el espacio de trabajo; no te limites a dar instrucciones. Primero inspecciona los archivos actuales y conserva cualquier cambio existente que no sea necesario modificar.

Objetivo
Crear una aplicacion ligera con Python que anime varias moscas sobre el escritorio. Cada mosca debe caminar por la pantalla, orientarse hacia su direccion de movimiento y detenerse de vez en cuando para asearse. Las ventanas de las moscas deben ser transparentes, estar siempre encima, no recibir clics y no robar el foco.

Archivos y recursos
- `fly.py`: aplicacion y logica de animacion.
- `1.png`, `2.png`, `3.png`: atlas RGBA de 6x6, con 36 cuadros cada uno; cuadros 0-17 para aseo y 18-35 para caminar.
- `fly.ico`: icono para la bandeja y para el ejecutable.
- `requirements.txt`: Pillow y pystray.
- `MoscasEscritorio.spec`: configuracion de PyInstaller para Windows.
- `iniciar_mosca.bat`: inicio sin ventana de consola cuando existe `.venv\\Scripts\\pythonw.exe`.
- `LEEME.md`: instrucciones breves de uso y compilacion.

Arquitectura y comportamiento
1. Usa un unico `tk.Tk()` como panel de control y un `tk.Toplevel()` sin bordes por cada mosca. Todas las moscas comparten un solo bucle de eventos Tk; no crees una instancia `Tk` por mosca.
2. Configura cada overlay con color-key transparente `#010203`, `-topmost`, `-toolwindow` y estilos Win32 de clic pasante y no activacion. Aplica los estilos Win32 despues de que la ventana este mapeada para que Tk no los sobrescriba.
3. Abre cada atlas con Pillow en RGBA. Calcula los limites de cada celda proporcionalmente con `round(columna * ancho / 6)` y su equivalente para filas; no presupongas que ancho y alto son divisibles exactamente entre seis.
4. Reduce cada cuadro a un tamano base configurable. Limpia ruido de alfa: convierte alfa menor que 17 en cero y elimina componentes conectados aislados de menos de cuatro pixeles. Conserva el color y el alfa de la silueta.
5. Reserva un lienzo cuadrado de `ceil(tamano * sqrt(2))` para los giros. Rota con Pillow y resampling de calidad, relleno transparente y 16 direcciones. Calcula el rumbo desde el norte con `atan2(dx, -dy)` y cachea las imagenes rotadas.
6. La mosca camina hacia destinos aleatorios dentro de la pantalla. Usa movimiento basado en tiempo transcurrido para que la velocidad no dependa de la frecuencia de refresco. Anima las 18 poses de caminar y, cada cierto intervalo aleatorio, reproduce las 18 poses de aseo antes de volver a caminar.
7. El panel debe permitir en vivo: cantidad de 0 a 20, tamano de 24 a 128 px en pasos de 4, y tipo de sprite `1.png`, `2.png` o `3.png`. Cambiar cantidad crea o destruye solo las ventanas necesarias; cambiar tamano o atlas actualiza todas las moscas existentes sin reiniciar la aplicacion.
8. Agrega una bandeja real de Windows con `pystray`, usando `fly.ico`. Cerrar el panel lo oculta en la bandeja, no termina la simulacion. El doble clic en el icono restaura el panel. El menu contiene mostrar controles, pausar/reanudar y salir. El icono debe detenerse y todos los callbacks/overlays deben limpiarse al salir.
9. Conserva los atajos globales `Ctrl+Alt+F8` para pausa/reanudacion y `Ctrl+Alt+F9` para salir. No reserves ni consumas esas teclas en las demas aplicaciones.
10. Muestra errores utiles si falta un atlas, el icono o una dependencia. Mantiene la interfaz independiente de los overlays y permite seguir controlandola desde la bandeja.

Dependencias y empaquetado
- Declara `Pillow>=11` y `pystray>=0.19.5` en `requirements.txt`.
- En `MoscasEscritorio.spec`, agrega `1.png`, `2.png`, `3.png` y `fly.ico` a `datas`, incluye `pystray._win32` en `hiddenimports`, activa `console=False` y establece `fly.ico` como icono del EXE.
- El comando de compilacion es `python -m PyInstaller --noconfirm --clean MoscasEscritorio.spec`.
- El EXE debe ser `onefile`, no abrir una consola, encontrar los recursos al ejecutarse y mostrar el icono de bandeja.

Validacion de aceptacion
- Carga los 36 cuadros de cada uno de los tres atlas, incluidas hojas con dimensiones no divisibles entre seis.
- Verifica que todas las poses conservan la silueta y no muestran manchas aisladas ni cuadros negros.
- Comprueba los cuatro rumbos cardinales y las 16 orientaciones, sin recortar las diagonales.
- Cambia cantidad, tamano y atlas en vivo; prueba los limites 0 y 20.
- Comprueba que ocultar/restaurar el panel conserva las moscas; que la pausa y salida funcionan desde panel, atajos y bandeja.
- Comprueba que los overlays siguen transparentes, topmost, click-through y no activables.
- Ejecuta diagnosticos/sintaxis y compila el EXE con el `.spec`. No sobrescribas artefactos existentes para una compilacion de prueba: usa rutas temporales.

Entrega cambios pequenos y coherentes con la implementacion existente. Actualiza `LEEME.md` cuando cambie el uso o el empaquetado, ejecuta comprobaciones enfocadas despues de editar y resume que se cambio y que pruebas se ejecutaron.
```

## Estructura y controles actuales

- `DesktopFly` administra el panel, las moscas, la bandeja y el bucle comun.
- `FlySprite` administra el estado y la ventana de una mosca individual.
- `Ctrl+Alt+F8` o el menu de bandeja pausa/reanuda.
- Cerrar el panel lo oculta; doble clic en el icono lo restaura.
- `Ctrl+Alt+F9` o la opcion "Salir" cierra la aplicacion y elimina las ventanas.
- Para probar el EXE sin sobrescribir la distribucion existente: `python -m PyInstaller --noconfirm --workpath build-tray-test --distpath dist-tray-test MoscasEscritorio.spec`.
