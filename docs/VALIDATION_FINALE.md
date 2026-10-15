# NetOps-AI — Validation et limites (15 octobre 2026)

## Démonstration réelle validée
- Topologie GNS3 / FRRouting : R1–R2–R3 ; OSPF sain avant test (FULL 1/2/1).
- Injection contrôlée : `R2 eth1` administrativement DOWN, lien R2–R3 interrompu.
- RCA : `interface_administratively_down` identifié ; composantes `[R1,R2]` et `[R3]` ; LAN séparés.
- Récupération : playbook Ansible exécuté avec approbation explicite, sauvegarde de configuration et vérification administrative.
- Postcontrôle : OSPF FULL 1/2/1 rétabli ; RCA `healthy`.
- Trace : `logs/fault-drill-20261015T182003Z` (conserver les logs de démonstration).

## Limites honnêtes
- Le scénario ne prouve pas la détection d'une panne physique ou de toutes les catégories de panne.
- La vérification de connectivité bout en bout des deux LAN n'a pas été démontrée par un ping PC1→PC2 dans cette trace.
- La capture des alertes Prometheus/Alertmanager pendant ce test n'est pas établie par les sorties fournies.
- Le rollback Ansible en cas d'échec de postvalidation n'a pas été testé en conditions réelles.
- Isolation Forest a marqué 324/324 observations saines comme anomalies avec un score ~ -7.77e-16 : modèle non concluant, aucune métrique de précision/F1 revendiquée.
- Les tests unitaires locaux ne prouvent pas encore que le workflow GitHub Actions a réussi sur GitHub.

## Avant publication
1. Capturer une image du graphe GNS3 et des dashboards Grafana.
2. Exporter une preuve d'alerte et de résolution avec horodatage lors d'un prochain test planifié.
3. Vérifier les dépendances CI et le workflow GitHub Actions après push.
4. Documenter le lancement des services, les variables d'environnement et les commandes de tests.
5. Ne jamais committer `.venv`, `*.db`, tokens, secrets ou volumes persistants.
