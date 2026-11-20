import importlib.util
import os
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location('dashboard', os.path.join(os.path.dirname(__file__), '..', 'dashboard.py'))
dashboard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dashboard)


class DashboardTest(unittest.TestCase):
    def test_status_distinguishes_usb_timeout(self):
        outputs = [(0, '29'), (0, 'state = running'), (None, ''),
                   (0, 'printer available'), (0, ''), (0, '')]
        with mock.patch.object(dashboard, 'command', side_effect=outputs):
            state = dashboard.status()
        self.assertTrue(state['docker'])
        self.assertTrue(state['service'])
        self.assertIsNone(state['usb'])
        self.assertEqual(state['pending'], 0)
        self.assertFalse(state['usb_backend_active'])

    def test_status_detects_usb(self):
        outputs = [(0, '29'), (0, 'state = running'),
                   (0, 'direct usb://Brother/DCP-T226?serial=example'),
                   (0, 'printer available'), (0, 'job 1\njob 2'), (0, '')]
        with mock.patch.object(dashboard, 'command', side_effect=outputs):
            state = dashboard.status()
        self.assertTrue(state['usb'])
        self.assertEqual(state['pending'], 2)


if __name__ == '__main__':
    unittest.main()
