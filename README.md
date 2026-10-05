# Collecte de fiches produit pour un catalogue de tentes

## Le projet en quelques mots

Je travaille sur un outil qui rassemble les informations de fiches produit pour préparer un catalogue de matériel. Il vise à éviter de recopier manuellement chaque caractéristique et à faciliter les comparaisons.

Le prototype collecte des pages, prépare des caractéristiques structurées, télécharge des images et organise leur transfert vers une base de données. Les informations extraites doivent être contrôlées avant utilisation.

## Comment le découvrir

Cette fiche explique le fonctionnement sans installation. Le projet ne possède pas d'écran de démonstration : il s'utilise par commandes et demande plusieurs services configurés. Télécharger le ZIP ne fournit donc pas une application prête à ouvrir.

Les essais existants utilisent des réponses simulées. Une collecte complète sur des sites réels reste à vérifier.

## Détails pour reprendre le projet

<details>
<summary>Fonctionnement, installation et limites techniques</summary>

## En bref

**Ce que c’est :** un outil en ligne de commande pour collecter des fiches de tentes.

**À quoi il sert :** parcourir des pages autorisées, extraire leurs caractéristiques dans un format structuré, télécharger les images et préparer une synchronisation NocoDB.

**Ce qui a été réalisé :** collecte Playwright, extraction JSON via Claude Code CLI, téléchargement httpx et logique d’insertion ou de mise à jour NocoDB.

**Technologies :** Python 3.12+, Playwright, Chromium, httpx, python-dotenv, Claude Code CLI et API REST NocoDB.

Le dépôt fournit une ligne de commande, pas une interface graphique. Les services réels demandent une configuration et une validation séparées.

## Fonctionnement présent dans le code

`main.py` charge `brands.json`, ouvre Chromium avec Playwright, cherche les liens de produits, développe les éléments interactifs et sauvegarde leur HTML. Les images sont téléchargées avec httpx. `extractor.py` appelle `claude -p` pour produire du JSON ; `nocodb.py` crée ou complète une table puis insère ou met à jour les lignes selon marque et modèle.

Les détails d’installation et de fonctionnement restent documentés ci-dessous.

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

## Dépôt et téléchargement

[Voir le dépôt](https://github.com/cpointis96-hue/tente-scraperv2) · [Télécharger les sources ZIP](https://github.com/cpointis96-hue/tente-scraperv2/archive/HEAD.zip). Le ZIP contient les sources, sans service configuré.

</details>
