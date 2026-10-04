# Vérification — 4 octobre 2026

Source initiale : `9f7d206`. Branche de préparation : `prepare/portfolio-documentation`.

| Vérification | Résultat |
| --- | --- |
| `.venv/bin/python -m pytest -q` | 33 tests réussis en 6,43 s ; fixtures locales, appels Claude simulés, API httpx simulée |
| `.venv/bin/python -m compileall -q main.py scraper.py extractor.py nocodb.py` | Réussite |
| `uv build --wheel --out-dir /private/tmp/codex-tent-wheel` | Réussite technique ; wheel incomplet, ne contient aucun module applicatif |
| `unzip -l /private/tmp/codex-tent-wheel/tent_scraper-0.1.0-py3-none-any.whl` | Seulement METADATA, WHEEL, RECORD (567 octets au total) |
| Scraping réel, Claude réel, NocoDB réel | Non exécutés |
| Captures | Sans objet pour cette CLI ; aucune capture fabriquée |

Les tests importent `main.py`, qui configure un journal local ; `scrape.log` est ignoré. Aucun fichier d'environnement privé n'a été consulté. La revue porte sur le code et des données synthétiques, pas sur des données personnelles.

Le backend wheel cible `src`, alors que les modules se trouvent à la racine. Le build a d'abord échoué sur la résolution DNS de PyPI dans le bac à sable, puis a réussi avec accès réseau, mais son archive ne distribue pas l'application. Le code applicatif et cette configuration restent inchangés ; la notice propose l'installation directe des dépendances. Les autres limites sont détaillées dans README.md.
