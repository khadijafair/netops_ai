"""Decision support only. Never changes router configurations."""


def recommend(report):
    if not report.get('analysis_complete'):
        return {'approved': False, 'reason': 'incomplete_diagnostics', 'actions': []}
    actions = []
    for incident in report.get('incidents', []):
        rca = incident.get('rca', {})
        cause = rca.get('probable_cause')
        actions.append({
            'incident_key': incident.get('incident_key'),
            'cause': cause,
            'suggested_action': {
                'interface_administratively_down': 'review_interface_admin_state',
                'ip_configuration_mismatch': 'review_addressing_against_source_of_truth',
            }.get(cause, 'collect_additional_evidence'),
            'requires_human_approval': True,
            'executed': False,
        })
    return {'approved': False, 'reason': 'manual_approval_required', 'actions': actions}
