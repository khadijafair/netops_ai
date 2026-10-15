import json
from diagnosis.rca import analyze
from remediation.policy import recommend


def preflight():
    report = analyze()
    plan = recommend(report)

    if not report["analysis_complete"]:
        status = "BLOCKED_INCOMPLETE_DATA"
    elif report["network_status"] == "healthy":
        status = "NO_REMEDIATION_NEEDED"
    else:
        status = "AWAITING_MANUAL_APPROVAL"

    return {
        "status": status,
        "network_status": report["network_status"],
        "incidents": report["incidents"],
        "proposed_actions": plan["actions"],
        "execution_authorized": False,
    }


if __name__ == "__main__":
    print(json.dumps(preflight(), indent=2))
