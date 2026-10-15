import unittest
from aiops.quality import assess


class TestAIOpsQuality(unittest.TestCase):
    def test_constant_scores_are_not_validated(self):
        result = assess({'test_samples': 324, 'test_score_min': -7.7e-16,
                         'test_score_max': -7.7e-16, 'ground_truth_available': False})
        self.assertEqual(result['status'], 'insufficient_variability')
        self.assertFalse(result['usable_for_automated_decisions'])

    def test_no_ground_truth_not_validated(self):
        result = assess({'test_samples': 324, 'test_score_min': -0.2,
                         'test_score_max': 0.2, 'ground_truth_available': False})
        self.assertEqual(result['status'], 'unvalidated_no_ground_truth')


if __name__ == '__main__':
    unittest.main()
