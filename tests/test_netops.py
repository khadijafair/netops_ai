import unittest
from unittest.mock import patch
from diagnosis.rca import analyze_link
from remediation.policy import recommend


class TestRCA(unittest.TestCase):
    def setUp(self):
        self.link = {'routers': ['R2', 'R3'],
                     'interfaces': {'R2': 'eth1', 'R3': 'eth0'}}
        self.interfaces = {
            'R2': {'eth1': {'admin_up': True, 'operstate': 'UNKNOWN',
                            'addresses': ['10.0.23.1/30']}},
            'R3': {'eth0': {'admin_up': True, 'operstate': 'UNKNOWN',
                            'addresses': ['10.0.23.2/30']}},
        }

    def test_healthy_interfaces_do_not_prove_root_cause(self):
        result = analyze_link(self.link, self.interfaces)
        self.assertEqual(result['probable_cause'], 'ospf_or_link_connectivity_problem')
        self.assertFalse(result['root_cause_confirmed'])

    def test_admin_down(self):
        self.interfaces['R2']['eth1']['admin_up'] = False
        self.assertEqual(analyze_link(self.link, self.interfaces)['probable_cause'],
                         'interface_administratively_down')

    def test_ip_mismatch(self):
        self.interfaces['R3']['eth0']['addresses'] = ['10.0.99.2/30']
        self.assertEqual(analyze_link(self.link, self.interfaces)['probable_cause'],
                         'ip_configuration_mismatch')

    def test_incomplete_diagnostics_block_remediation(self):
        self.assertFalse(recommend({'analysis_complete': False})['approved'])

    def test_remediation_never_auto_executes(self):
        report = {'analysis_complete': True, 'incidents': [
            {'incident_key': 'ospf-link:R2-R3',
             'rca': {'probable_cause': 'interface_administratively_down'}}]}
        result = recommend(report)
        self.assertFalse(result['approved'])
        self.assertFalse(result['actions'][0]['executed'])


if __name__ == '__main__':
    unittest.main()
