import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix

BASE = Path(__file__).resolve().parent
DATA = BASE / "results/dataset.csv"
MODELS = BASE / "models"
MODELS.mkdir(exist_ok=True)

FEATURES = [
    "neighbor_count",
    "missing_neighbors",
    "ospf_route_count",
    "interface_up",
    "ping_success",
    "ping_latency_ms",
]

df = pd.read_csv(DATA)
df["fault_family"] = df["scenario"].str.replace(
    r"_\d+$", "", regex=True
)

normal = df[df.label == 0].copy()
faults = df[df.label == 1].copy()

# Test sur une famille de panne non vue à l'entraînement.
# Normal : séparation temporelle approximative.
normal_train = normal.iloc[:int(len(normal)*0.7)]
normal_test = normal.iloc[int(len(normal)*0.7):]

families = sorted(faults.fault_family.unique())
held_out = families[-1]

fault_train = faults[faults.fault_family != held_out]
fault_test = faults[faults.fault_family == held_out]

train = pd.concat([normal_train, fault_train])
test = pd.concat([normal_test, fault_test])

X_train = train[FEATURES].fillna(0)
y_train = train.label
X_test = test[FEATURES].fillna(0)
y_test = test.label

results = {
    "train_samples": len(train),
    "test_samples": len(test),
    "held_out_fault": held_out,
    "features": FEATURES,
}

rf = RandomForestClassifier(
    n_estimators=200,
    class_weight="balanced",
    random_state=42,
    min_samples_leaf=2,
)
rf.fit(X_train, y_train)
rf_pred = rf.predict(X_test)

results["random_forest"] = classification_report(
    y_test, rf_pred,
    labels=[0,1],
    target_names=["normal","fault"],
    output_dict=True,
    zero_division=0,
)
results["random_forest_confusion_matrix"] = (
    confusion_matrix(y_test, rf_pred, labels=[0,1]).tolist()
)

iso = IsolationForest(
    n_estimators=200,
    contamination=0.1,
    random_state=42,
)
iso.fit(normal_train[FEATURES].fillna(0))
iso_pred = (
    iso.predict(X_test) == -1
).astype(int)

results["isolation_forest"] = classification_report(
    y_test, iso_pred,
    labels=[0,1],
    target_names=["normal","fault"],
    output_dict=True,
    zero_division=0,
)

joblib.dump(rf, MODELS / "random_forest.joblib")
joblib.dump(iso, MODELS / "isolation_forest.joblib")

(MODELS / "features.json").write_text(
    json.dumps(FEATURES, indent=2)
)
(BASE / "results/evaluation_v2.json").write_text(
    json.dumps(results, indent=2)
)

print("=== ML V2 ===")
print("Famille de panne réservée au test :", held_out)
print("Train :", len(train), "| Test :", len(test))

for name in ["random_forest", "isolation_forest"]:
    metrics = results[name]
    print(
        name,
        "| Precision:", round(metrics["fault"]["precision"],3),
        "| Recall:", round(metrics["fault"]["recall"],3),
        "| F1:", round(metrics["fault"]["f1-score"],3),
    )

print("Modèles sauvegardés dans ml_v2/models/")
