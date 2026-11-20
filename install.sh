#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
[[ $(uname -s) == Darwin ]] || { echo 'Este instalador requiere macOS.' >&2; exit 1; }
command -v docker >/dev/null || { echo 'Instala y abre Docker Desktop primero.' >&2; exit 1; }
docker info >/dev/null 2>&1 || { echo 'Docker Desktop no está en marcha.' >&2; exit 1; }
command -v python3 >/dev/null || { echo 'Se requiere python3.' >&2; exit 1; }

echo 'El instalador descarga el controlador oficial de Brother. Revisa su licencia:'
echo 'https://support.brother.com/g/b/downloadend.aspx?c=in&lang=en&prod=dcpt226_all&os=128&dlid=dlf105585_000&flang=4&type3=10283'
read -r -p '¿Aceptas la licencia de Brother y deseas continuar? [s/N] ' answer
[[ "$answer" == [sSyY] ]] || exit 1

if lpstat -p Brother_T226_Bridge >/dev/null 2>&1; then
  echo 'La cola Brother_T226_Bridge ya existe. No se modificará.' >&2
  exit 1
fi
uri=$(lpinfo -v | awk '/^direct usb:\/\/Brother\/DCP-T226\?/ {print $2; exit}')
[[ -n "$uri" ]] || { echo 'Conecta y enciende la DCP-T226 por USB.' >&2; exit 1; }
if lsof -nP -iTCP:45828 -sTCP:LISTEN >/dev/null 2>&1; then
  echo 'El puerto local 45828 está ocupado.' >&2; exit 1
fi
if lsof -nP -iTCP:45829 -sTCP:LISTEN >/dev/null 2>&1; then
  echo 'El puerto local 45829 está ocupado.' >&2; exit 1
fi
read -r -p 'Papel predeterminado [Letter/A4] (Letter): ' paper
paper=${paper:-Letter}
[[ "$paper" == Letter || "$paper" == A4 ]] || { echo 'Selecciona Letter o A4.' >&2; exit 1; }

tmp=$(mktemp -d "${TMPDIR:-/tmp}/brother-t226.XXXXXX")
trap 'rm -rf "$tmp"' EXIT
curl -fL 'https://download.brother.com/welcome/dlf105585/dcpt226pdrv-3.5.0-1.i386.deb' -o "$tmp/driver.deb"
(cd "$tmp" && tar -xf driver.deb && tar -xf data.tar.gz)
cp Dockerfile "$tmp/Dockerfile"
docker build --platform linux/amd64 -t brother-t226-macos-bridge:local "$tmp"

dir="$HOME/Library/Application Support/Brother-T226-Bridge"
plist="$HOME/Library/LaunchAgents/local.brother-t226-macos-bridge.plist"
dashboard_plist="$HOME/Library/LaunchAgents/local.brother-t226-dashboard.plist"
[[ ! -e "$plist" && ! -e "$dashboard_plist" && ! -e "$dir" ]] || { echo 'La configuración del puente ya existe; no se sobrescribirá.' >&2; exit 1; }
mkdir -p "$dir" "$HOME/Library/LaunchAgents" "$HOME/Library/Logs"
cp bridge.py "$dir/bridge.py"
cp dashboard.py "$dir/dashboard.py"
sed '/^\*cupsFilter:/d' "$tmp/opt/brother/Printers/dcpt226/cupswrapper/brother_dcpt226_printer_en.ppd" > "$dir/printer.ppd"
python3 - "$dir" "$plist" "$dashboard_plist" "$uri" "$paper" "$(command -v docker)" <<'PY'
import json, os, plistlib, sys
directory, plist, dashboard_plist, uri, paper, docker = sys.argv[1:]
with open(os.path.join(directory, 'config.json'), 'w') as f:
    json.dump({'usb_uri': uri, 'paper': paper, 'docker': docker, 'port': 45828}, f)
log = os.path.expanduser('~/Library/Logs/brother-t226-macos-bridge.log')
with open(plist, 'wb') as f:
    plistlib.dump({'Label': 'local.brother-t226-macos-bridge', 'ProgramArguments': ['/usr/bin/python3', os.path.join(directory, 'bridge.py')], 'RunAtLoad': True, 'KeepAlive': True, 'StandardErrorPath': log, 'StandardOutPath': log}, f)
with open(dashboard_plist, 'wb') as f:
    plistlib.dump({'Label': 'local.brother-t226-dashboard', 'ProgramArguments': ['/usr/bin/python3', os.path.join(directory, 'dashboard.py')], 'RunAtLoad': True, 'KeepAlive': True}, f)
PY
launchctl bootstrap "gui/$(id -u)" "$plist"
launchctl bootstrap "gui/$(id -u)" "$dashboard_plist"
lpadmin -p Brother_T226_Bridge -D 'Brother DCP-T226 USB Bridge' -v 'socket://127.0.0.1:45828' -P "$dir/printer.ppd" -E
echo 'Instalada: Brother DCP-T226 USB Bridge. Docker Desktop debe estar abierto.'
echo 'Prueba desde una aplicación; revisa el log si no imprime.'
echo 'Panel local: http://127.0.0.1:45829/'
