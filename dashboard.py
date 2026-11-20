#!/usr/bin/python3
"""Read-only local dashboard for the Brother USB bridge."""
import json
import os
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

PORT = 45829
PROFILE = os.environ.get('BROTHER_DASHBOARD_PROFILE', 'standard')
PROFILES = {
    'standard': ('local.brother-t226-macos-bridge', 'Brother_T226_Bridge', 45828),
    'legacy': ('local.brother-t226-bridge', 'Brother_T226_USB', 45827),
}
LABEL, QUEUE, BRIDGE_PORT = PROFILES[PROFILE]


def command(args, timeout=8):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return None, ''


def status():
    docker_path = '/usr/local/bin/docker'
    if PROFILE == 'standard':
        try:
            with open(os.path.expanduser('~/Library/Application Support/Brother-T226-Bridge/config.json'), encoding='utf-8') as f:
                docker_path = json.load(f)['docker']
        except (OSError, ValueError, KeyError):
            pass
    docker = command([docker_path, 'info', '--format', '{{.ServerVersion}}'])
    service = command(['/bin/launchctl', 'print', 'gui/' + str(os.getuid()) + '/' + LABEL])
    usb = command(['/usr/sbin/lpinfo', '-v'])
    queue = command(['/usr/bin/lpstat', '-p', QUEUE])
    jobs = command(['/usr/bin/lpstat', '-o', QUEUE])
    backend = command(['/bin/ps', '-ax', '-o', 'command='])
    return {
        'docker': docker[0] == 0,
        'service': service[0] == 0 and 'state = running' in service[1],
        'usb': None if usb[0] != 0 else any(line.startswith('direct usb://Brother/DCP-T226?') for line in usb[1].splitlines()),
        'queue': queue[0] == 0,
        'queue_detail': queue[1] if queue[0] == 0 else 'Cola no disponible',
        'pending': len(jobs[1].splitlines()) if jobs[0] == 0 and jobs[1] else 0 if jobs[0] == 0 else None,
        'usb_backend_active': None if backend[0] is None else any('/usr/libexec/cups/backend/usb 1 mac Brother USB 1' in line for line in backend[1].splitlines()),
        'bridge_port': BRIDGE_PORT,
        'queue_name': QUEUE,
    }


PAGE = '''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Brother USB · Estado</title><style>
body{font:16px -apple-system,BlinkMacSystemFont,sans-serif;background:#f3f5f9;color:#182032;margin:0}main{max-width:760px;margin:48px auto;padding:0 20px}h1{margin-bottom:4px}p{line-height:1.5;color:#48556c}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px}.card{background:white;border:1px solid #e0e5ed;border-radius:12px;padding:18px}.value{font-size:19px;font-weight:650;margin-top:8px}.ok{color:#087f54}.bad{color:#b43d2d}.unknown{color:#8a6200}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}button{border:0;border-radius:8px;background:#1f56d8;color:white;padding:10px 16px;cursor:pointer}.note{border-left:3px solid #e3aa31;padding-left:14px}
</style></head><body><main><h1>Brother DCP-T226</h1><p>Estado local del puente de impresión USB</p><div class="grid" id="cards"></div><p class="note">La cola de macOS puede indicar que un trabajo terminó antes de que llegue a la impresora. No reenvíes un documento solo porque la cola esté vacía.</p><div class="card"><strong>Cola de macOS</strong><pre id="queue">Consultando…</pre></div><p id="updated"></p><button id="refresh">Actualizar</button></main><script>
const cards=document.getElementById('cards');function card(label,value){let c=document.createElement('div');c.className='card';let t=document.createElement('div');t.textContent=label;let v=document.createElement('div');v.className='value '+(value===true?'ok':value===false?'bad':'unknown');v.textContent=value===true?'Disponible':value===false?'No disponible':'Sin confirmar';c.append(t,v);cards.append(c)}
async function update(){try{let r=await fetch('/status',{cache:'no-store'});if(!r.ok)throw Error();let s=await r.json();cards.replaceChildren();card('Servicio del puente',s.service);card('Docker',s.docker);card('Brother por USB',s.usb);card('Cola de impresión',s.queue);document.getElementById('queue').textContent=s.queue_detail+'\\nTrabajos pendientes en macOS: '+(s.pending===null?'desconocido':s.pending)+'\\nOperación USB activa: '+(s.usb_backend_active===null?'desconocido':s.usb_backend_active?'sí':'no')+'\\nPuerto local del puente: '+s.bridge_port;document.getElementById('updated').textContent='Actualizado: '+new Date().toLocaleTimeString()}catch(e){document.getElementById('updated').textContent='No se pudo consultar el estado.'}}document.getElementById('refresh').onclick=update;update();setInterval(update,15000);
</script></body></html>'''


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.headers.get('Host') not in ('localhost:' + str(PORT), '127.0.0.1:' + str(PORT)):
            self.send_error(403)
            return
        path = urlsplit(self.path).path
        if path == '/':
            body, content_type = PAGE.encode(), 'text/html; charset=utf-8'
        elif path == '/status':
            body, content_type = json.dumps(status()).encode(), 'application/json; charset=utf-8'
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


if __name__ == '__main__':
    ThreadingHTTPServer(('127.0.0.1', PORT), Handler).serve_forever()
