# Brother DCP-T226 por USB en macOS

Puente **experimental** para imprimir desde el diálogo de macOS sin exportar manualmente a PDF ni usar iPrint&Scan. Usa Docker para ejecutar el controlador oficial de Brother para Linux y envía el resultado a la impresora por USB.

## Estado y limitaciones

- Se ha probado la conversión del controlador y una impresión directa por USB en macOS 26 con Apple Silicon. **La impresión completa desde una aplicación aún no está confirmada**.
- Docker Desktop debe estar abierto y el usuario que instaló el puente debe tener la sesión iniciada.
- La cola de macOS envía el documento al puente local; puede marcarlo como completado **antes** de que Docker o USB finalicen. Un fallo posterior aparece en el log, no necesariamente en la cola. No hay reintentos automáticos.
- El tamaño de papel se fija durante la instalación (Letter o A4); las opciones de la ventana de impresión, incluida la cantidad de copias, color y tamaño, pueden no trasladarse correctamente. Comprueba el resultado antes de imprimir documentos importantes.
- El puerto `127.0.0.1:45828` solo escucha en el propio Mac, pero otros usuarios o procesos locales pueden enviar trabajos sin autenticación. No usar en un equipo compartido sin considerar esto.
- Las páginas se procesan en memoria; límite de entrada: 128 MiB. No se guardan copias de documentos deliberadamente.
- Solución no oficial, no afiliada a Brother. El driver y su licencia pertenecen a Brother; no se incluyen en este repositorio.

## Requisitos

- macOS con DCP-T226 conectada y encendida por USB. CUPS y su backend USB deben estar disponibles.
- Docker Desktop instalado y abierto; soporte para contenedores Linux `amd64` (emulación en Apple Silicon).
- `python3`, `curl`, `tar` y permisos para añadir impresoras en macOS.
- Internet para descargar el controlador oficial y construir la imagen Docker. El instalador solicita aceptar la licencia de Brother.

## Instalar

```bash
git clone https://github.com/DevNeonix/brother-dcp-t226-macos-usb.git
cd brother-dcp-t226-macos-usb
bash install.sh
```

Elige **Brother DCP-T226 USB Bridge** en `⌘ + P`. No selecciona automáticamente una impresora predeterminada ni modifica otras colas. El servicio se inicia al entrar en la sesión.

## Diagnóstico

```bash
lpstat -p Brother_T226_Bridge -v
tail -f "$HOME/Library/Logs/brother-t226-macos-bridge.log"
docker info
```

Comprueba que Docker Desktop esté abierto, el cable conectado y que la cola corresponda a esta impresora. Si la impresora se sustituyó, la URI USB con su número de serie puede cambiar: hay que reinstalar el puente.

## Desinstalar

Esto elimina únicamente la cola, el servicio y los archivos creados por este proyecto. La imagen Docker se conserva salvo que ejecutes la última línea.

```bash
lpadmin -x Brother_T226_Bridge
launchctl bootout "gui/$(id -u)" "$HOME/Library/LaunchAgents/local.brother-t226-macos-bridge.plist"
rm "$HOME/Library/LaunchAgents/local.brother-t226-macos-bridge.plist"
rm -r "$HOME/Library/Application Support/Brother-T226-Bridge"
# Opcional:
docker image rm brother-t226-macos-bridge:local
```

El log en `~/Library/Logs/brother-t226-macos-bridge.log` se conserva. No se elimina ninguna impresora ajena al proyecto.
