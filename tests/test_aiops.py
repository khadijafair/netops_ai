import unittest
from unittest.mock import patch
from aiops.pipeline import FEATURES, METRICS, fetch


class TestAIOps(unittest.TestCase):
    def test_features_are_consistent(self):
        self.assertEqual(len(FEATURES), 3)
        self.assertEqual(len(METRICS), 3)

    def test_invalid_collection_window(self):
        with self.assertRaises(ValueError):
            fetch(hours=0)
        with self.assertRaises(ValueError):
            fetch(step=1)
