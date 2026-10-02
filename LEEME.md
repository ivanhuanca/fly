# Mosca de escritorio

Aplicacion para Windows con una interfaz para controlar moscas animadas en ventanas transparentes, siempre visibles, que no reciben clics ni toman el foco.

- Inicia la aplicacion con doble clic en `iniciar_mosca.bat`.
- Cambia la cantidad (de 0 a 20), el tamano y el sprite (`1.png`, `2.png` o `3.png`); se aplican en vivo.
- Pulsa `Pausar` en la interfaz o `Ctrl+Alt+F8` para pausar o reanudar.
- Cierra la ventana de control para ocultarla en la bandeja. Haz doble clic en el icono para mostrarla de nuevo.
- Usa el menu del icono para mostrar los controles, pausar o salir; `Ctrl+Alt+F9` tambien cierra la aplicacion.
- Requiere Python para Windows con Tkinter. Instala las dependencias con `python -m pip install -r requirements.txt`.
- Para crear el EXE con PyInstaller, usa `MoscasEscritorio.spec`; incluye el icono de bandeja y su backend de Windows.