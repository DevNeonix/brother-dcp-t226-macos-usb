import importlib.util
import json
import os
import socket
import tempfile
import threading
import unittest
from unittest import mock

with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
    json.dump({'docker': 'docker', 'paper': 'Letter', 'port': 0, 'usb_uri': 'usb://test'}, f)
    config_path = f.name
os.environ['BROTHER_BRIDGE_CONFIG'] = config_path
spec = importlib.util.spec_from_file_location('bridge', os.path.join(os.path.dirname(__file__), '..', 'bridge.py'))
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)
os.unlink(config_path)


class BridgeTest(unittest.TestCase):
    def test_converts_and_sends_to_usb(self):
        conversion = mock.Mock(returncode=0, stdout=b'brother-data', stderr=b'')
        usb = mock.Mock(returncode=0, stderr=b'')
        with mock.patch.object(bridge.subprocess, 'run', side_effect=[conversion, usb]) as run:
            with bridge.Server(('127.0.0.1', 0), bridge.Handler) as server:
                thread = threading.Thread(target=server.handle_request)
                thread.start()
                with socket.create_connection(server.server_address) as client:
                    client.sendall(b'%!PS test')
                    client.shutdown(socket.SHUT_WR)
                thread.join(timeout=5)
                self.assertFalse(thread.is_alive())
        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args_list[0].kwargs['input'], b'%!PS test')
        self.assertEqual(run.call_args_list[1].kwargs['input'], b'brother-data')
        self.assertEqual(run.call_args_list[1].kwargs['env']['DEVICE_URI'], 'usb://test')

    def test_empty_job_does_not_run_driver(self):
        with mock.patch.object(bridge.subprocess, 'run') as run:
            with bridge.Server(('127.0.0.1', 0), bridge.Handler) as server:
                thread = threading.Thread(target=server.handle_request)
                thread.start()
                with socket.create_connection(server.server_address) as client:
                    client.shutdown(socket.SHUT_WR)
                thread.join(timeout=5)
                self.assertFalse(thread.is_alive())
        run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
