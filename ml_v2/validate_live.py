import json
from pathlib import Path

source = Path("ml_v2/results/live_predictions.json")
data = json.loads(source.read_text())

expected_interfaces = {
    "R1": 4, "R2": 3, "R3": 4,
    "R4": 4, "R5": 4, "R6": 4,
}

results = []

print("\n=== VALIDATION ML + REGLES RESEAU ===")

for item in data:
    router = item["router"]
    m = item["metrics"]
    prediction = item["prediction"]

    reasons = []

    if m["missing_neighbors"] > 0:
        reasons.append("Voisin OSPF manquant")

    if m["interface_up"] < expected_interfaces[router]:
        reasons.append("Interface inactive")

    if m["ping_success"] == 0:
        reasons.append("Connectivite indisponible")

    ml_alert = prediction["anomaly"]
    confirmed = bool(reasons)

    if confirmed:
        status = "INCIDENT RESEAU"
    elif ml_alert:
        status = "ML SUSPECT - A VERIFIER"
    else:
        status = "NORMAL"

    result = {
        "router": router,
        "status": status,
        "ml_score": prediction["fault_probability"],
        "ml_alert": ml_alert,
        "network_evidence": reasons,
        "remediation_authorized": False,
    }
    results.append(result)

    print(
        f"{router}: {status} | "
        f"ML={result['ml_score']:.3f} | "
        f"preuves={reasons or 'aucune'}"
    )

output = Path("ml_v2/results/validated_predictions.json")
output.write_text(json.dumps(results, indent=2))

print("\nResultats :", output)
print("Aucune remediation automatique declenchee.")
