#!/usr/bin/python3
"""Local-only PostScript-to-Brother USB bridge. See README for limitations."""
import json
import os
import socketserver
import subprocess
import sys

CONFIG = os.environ.get('BROTHER_BRIDGE_CONFIG', os.path.expanduser('~/Library/Application Support/Brother-T226-Bridge/config.json'))
with open(CONFIG, encoding='utf-8') as f:
    config = json.load(f)


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        try:
            data = self.rfile.read(128 * 1024 * 1024 + 1)
            if not data:
                return
            if len(data) > 128 * 1024 * 1024:
                raise ValueError('Job exceeds 128 MiB limit')
            converted = subprocess.run(
                [config['docker'], 'run', '--rm', '-i', '--network', 'none',
                 '--platform', 'linux/amd64', 'brother-t226-macos-bridge:local',
                 '1', 'mac', 'Brother USB', '1', 'PageSize=' + config['paper']],
                input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
            if converted.returncode or not converted.stdout:
                raise RuntimeError('Conversion failed: ' + converted.stderr.decode(errors='replace')[-1000:])
            env = dict(os.environ, DEVICE_URI=config['usb_uri'])
            sent = subprocess.run(
                ['/usr/libexec/cups/backend/usb', '1', 'mac', 'Brother USB', '1', ''],
                input=converted.stdout, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                env=env, timeout=300)
            if sent.returncode:
                raise RuntimeError('USB failed: ' + sent.stderr.decode(errors='replace')[-1000:])
            print('Job sent to USB', flush=True)
        except Exception as e:
            print('Job failed: ' + str(e), file=sys.stderr, flush=True)


class Server(socketserver.TCPServer):
    allow_reuse_address = True


if __name__ == '__main__':
    with Server(('127.0.0.1', config['port']), Handler) as server:
        server.serve_forever()
