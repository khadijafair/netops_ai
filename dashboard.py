import json
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="NetOps AI",
    page_icon="🌐",
    layout="wide"
)

st.title("🌐 NetOps AI")
st.caption("Network Monitoring & Automated Diagnostics")

report_file = Path(__file__).parent / "diagnostic_report.json"

if not report_file.exists():
    st.error("Rapport introuvable. Exécute network_analyzer.py.")
    st.stop()

with report_file.open() as file:
    report = json.load(file)

df = pd.DataFrame(report)

healthy = (df["severity"] == "OK").sum()
alerts = (df["severity"] != "OK").sum()

routers = set(df["source"]) | set(df["target"])

col1, col2, col3 = st.columns(3)

col1.metric("Routeurs", len(routers))
col2.metric("Liens dirigés OK", f"{healthy}/{len(df)}")
col3.metric("Alertes", int(alerts))

st.divider()

st.subheader("État des connexions")

display = df[
    [
        "source",
        "target",
        "interface_state",
        "ospf_full",
        "ping",
        "severity",
        "diagnosis"
    ]
].copy()

display.columns = [
    "Source",
    "Destination",
    "Interface",
    "OSPF FULL",
    "Ping",
    "Sévérité",
    "Diagnostic"
]

st.dataframe(display, width="stretch", hide_index=True)

st.subheader("Diagnostic réseau")

if alerts == 0:
    st.success("Toutes les connexions surveillées sont opérationnelles.")
else:
    for item in report:
        if item["severity"] != "OK":
            st.warning(
                f"{item['source']} → {item['target']} : "
                f"{item['diagnosis']}"
            )

if st.button("Actualiser l'affichage"):
    st.rerun()

st.caption(
    "Les données proviennent du dernier rapport JSON. "
    "Ce bouton ne relance pas la collecte réseau."
)