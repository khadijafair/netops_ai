import json
import subprocess
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.metrics import classification_report, confusion_matrix

BASE = Path("ml_v2")
RESULTS = BASE / "results"
MODELS = BASE / "models"

df = pd.read_csv(RESULTS / "dataset.csv")

# Corriger le comptage erroné des interfaces.
# Tous les adaptateurs GNS3 étaient actifs hors panne.
ADAPTERS = {
    "R1": 4, "R2": 3, "R3": 4,
    "R4": 4, "R5": 4, "R6": 4,
}

FAULT_ENDPOINT = {
    "R2_R3": "R2",
    "R1_R4": "R1",
    "R5_R6": "R5",
    "R2_R5": "R2",
}

df["fault_family"] = df["scenario"].str.replace(
    r"_\d+$", "", regex=True
)

def corrected_interfaces(row):
    total = ADAPTERS[row["router"]]
    if row["label"] == 1:
        if FAULT_ENDPOINT.get(row["fault_family"]) == row["router"]:
            return total - 1
    return total

df["interface_up"] = df.apply(corrected_interfaces, axis=1)

# Nouvelle cible : panne directement observable sur ce routeur.
# Les routeurs non affectés ne sont plus automatiquement étiquetés.
df["local_fault"] = (
    (df["missing_neighbors"] > 0) |
    (df["interface_up"] < df["router"].map(ADAPTERS)) |
    (df["ping_success"] == 0)
).astype(int)

FEATURES = [
    "neighbor_count",
    "missing_neighbors",
    "ospf_route_count",
    "interface_up",
    "ping_success",
    "ping_latency_ms",
]

df.to_csv(RESULTS / "dataset_corrected.csv", index=False)

# Réserver toute la famille R5_R6 au test.
held_out = "R5_R6"

normal = df[df["label"] == 0]
faults = df[df["label"] == 1]

# Séparer les instants normaux par blocs de collecte.
normal_groups = sorted(normal["scenario"].unique())
cut = max(1, int(len(normal_groups) * 0.7))

normal_train = normal[normal["scenario"].isin(normal_groups[:cut])]
normal_test = normal[normal["scenario"].isin(normal_groups[cut:])]

train = pd.concat([
    normal_train,
    faults[faults["fault_family"] != held_out]
])
test = pd.concat([
    normal_test,
    faults[faults["fault_family"] == held_out]
])

X_train = train[FEATURES]
y_train = train["local_fault"]
X_test = test[FEATURES]
y_test = test["local_fault"]

rf = RandomForestClassifier(
    n_estimators=200,
    min_samples_leaf=2,
    class_weight="balanced",
    random_state=42
)
rf.fit(X_train, y_train)

iso = IsolationForest(
    n_estimators=200,
    contamination=0.1,
    random_state=42
)
iso.fit(normal_train[FEATURES])

results = {}

for name, pred in [
    ("random_forest", rf.predict(X_test)),
    ("isolation_forest", (iso.predict(X_test) == -1).astype(int))
]:
    report = classification_report(
        y_test, pred,
        labels=[0, 1],
        target_names=["normal", "fault"],
        output_dict=True,
        zero_division=0
    )
    results[name] = {
        "precision": report["fault"]["precision"],
        "recall": report["fault"]["recall"],
        "f1": report["fault"]["f1-score"],
        "confusion_matrix": confusion_matrix(
            y_test, pred, labels=[0, 1]
        ).tolist()
    }

# Réentraîner sur toutes les observations pour le prototype live.
final_rf = RandomForestClassifier(
    n_estimators=200,
    min_samples_leaf=2,
    class_weight="balanced",
    random_state=42
)
final_rf.fit(df[FEATURES], df["local_fault"])

joblib.dump(final_rf, MODELS / "random_forest.joblib")
joblib.dump(iso, MODELS / "isolation_forest.joblib")

(MODELS / "features.json").write_text(
    json.dumps(FEATURES, indent=2)
)

(RESULTS / "evaluation_corrected.json").write_text(
    json.dumps(results, indent=2)
)

print("=== ML V2 CORRIGE ===")
print("Observations :", len(df))
print("Pannes locales :", int(df["local_fault"].sum()))
print("Train :", len(train), "| Test :", len(test))

for name, metrics in results.items():
    print(
        name,
        "| Precision:", round(metrics["precision"], 3),
        "| Recall:", round(metrics["recall"], 3),
        "| F1:", round(metrics["f1"], 3)
    )

print("\nModèle final sauvegardé.")
print("ATTENTION : étiquettes dérivées des mêmes métriques.")
print("Ces scores ne constituent pas une validation indépendante.")
