# Tent Scraper

Prototype Python pour collecter des fiches de tentes, extraire leurs caractéristiques avec Claude Code CLI et les envoyer vers NocoDB. Le dépôt existant reste privé.

## Fonctionnement présent dans le code

`main.py` charge `brands.json`, ouvre Chromium avec Playwright, cherche les liens de produits, développe les éléments interactifs et sauvegarde leur HTML. Les images sont téléchargées avec httpx. `extractor.py` appelle `claude -p` pour produire du JSON ; `nocodb.py` crée ou complète une table puis insère ou met à jour les lignes selon marque et modèle.

Stack : Python ≥ 3.12, Playwright, httpx, python-dotenv, Claude Code CLI et API REST NocoDB. Ce projet fournit une ligne de commande, pas une interface graphique.

## Installation et utilisation

Avec un accès autorisé au dépôt, cloner ou télécharger ses sources depuis GitHub. Installer Python ≥ 3.12 et uv, puis, depuis la racine :

```sh
uv venv --python 3.12
uv pip install --python .venv/bin/python playwright httpx python-dotenv pytest pytest-mock respx
.venv/bin/python -m playwright install chromium
.venv/bin/python -m pytest -q
```

Le packaging déclaré vise un dossier `src` absent : le wheel construit ne contient que ses métadonnées, sans les modules applicatifs. Les commandes ci-dessus utilisent directement les modules du dépôt.

Pour une exécution réelle, installer et authentifier séparément Claude Code CLI, copier `.env.example` vers `.env` et renseigner localement `NOCODB_URL`, `NOCODB_API_KEY`, `NOCODB_PROJECT_ID`. Vérifier `brands.json` et les chemins de sortie avant `.venv/bin/python main.py`. Cette commande accède au réseau, appelle Claude et écrit dans NocoDB ; elle n'a pas été lancée pendant cette vérification.

## Limites connues

- Les chemins sont codés en dur : HTML `/tmp/html`, JSON `/tmp/extracted`, images `/data/images`, journal `scrape.log`. `/data/images` exige un emplacement accessible ; le paramètre `html_dir` du pipeline ne change pas le chemin du scraper.
- La découverte de liens n'impose pas le même domaine et les sélecteurs sont génériques. La couverture réelle dépend de chaque site.
- L'extraction reprend tous les HTML du dossier, y compris les anciennes collectes. La séparation marque/modèle se fait au premier underscore et l'URL fournie à Claude est vide dans `extract_all`.
- Le JSON n'est pas validé par un schéma métier ; les valeurs et conversions générées doivent être contrôlées. Les champs dynamiques ajoutent des colonnes, mais leurs valeurs restent regroupées dans `any_extra_fields`.
- Claude peut transmettre le contenu des pages à son service. NocoDB reçoit les données extraites et le JSON brut. Ne pas déposer de clés, pages privées ou données personnelles dans les sources.

Les tests simulés passent ; ni la qualité d'une collecte réelle, ni Claude, ni la compatibilité avec une instance NocoDB ne sont certifiés. Voir [VERIFICATION.md](VERIFICATION.md). Aucune capture ni application téléchargeable n'est fournie : les sources constituent le livrable.
