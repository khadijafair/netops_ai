import unittest
from aiops.pipeline import FEATURES, vector
from aiops.label_incident import parse_utc

class TestNormalizedAIOps(unittest.TestCase):
    def test_topology_invariant(self):
        def row(full, expected):
            return dict(full_neighbors=full, expected_neighbors=expected, neighbor_deficit=expected-full, scrape_success=1.0)
        self.assertEqual(vector(row(1, 1)), vector(row(2, 2)))
    def test_missing_neighbor_is_distinct(self):
        healthy = dict(full_neighbors=2, expected_neighbors=2, neighbor_deficit=0, scrape_success=1)
        faulty = dict(full_neighbors=1, expected_neighbors=2, neighbor_deficit=1, scrape_success=1)
        self.assertNotEqual(vector(healthy), vector(faulty))
    def test_timezone_required(self):
        with self.assertRaises(ValueError):
            parse_utc('2026-10-15T12:00:00')
