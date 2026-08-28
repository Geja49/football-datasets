# API FastAPI — arborescence en couches

Point d'entrée : `serveur.py` (`uvicorn site.api.serveur:app`).

## Structure cible

```
site/api/
├── serveur.py              # App FastAPI, CORS, montage routeurs, helpers en migration
├── modeles/                # Pydantic — validation entrées/sorties (ex-schemas/)
├── schemas/                # Alias → modeles/
├── services/               # Logique métier (wrappers + règles)
├── requetes/               # Accès SQLite — SQL paramétré isolé
├── gestionnaires/          # Routes FastAPI (APIRouter)
├── utilitaires/            # Helpers légers (alias, correspondances, avatars)
├── tests/
│
├── communaute.py           # Module historique (routeur → gestionnaires/communaute)
├── forum.py
├── cotes.py
├── analyse_rencontre.py
├── calibration.py, calibrateur.py, historique_analyses.py
├── elo_clubs.py, ia_analyse.py
├── alias_equipes.py, correspondances.py, avatars.py
├── photos_joueurs.py, sites_officiels.py, stats_modele.py
└── requirements*.txt, pytest.ini
```

## Couches (de haut en bas)

| Couche | Dossier | Responsabilité |
|--------|---------|----------------|
| Gestionnaires | `gestionnaires/` | HTTP : routes, codes statut, corps JSON |
| Services | `services/` | Règles métier, agrégations, enrichissements |
| Requêtes | `requetes/` | `SELECT` / `INSERT` paramétrés sur SQLite |
| Modèles | `modeles/` | Schémas Pydantic (`extra='forbid'`, validateurs) |
| Utilitaires | `utilitaires/` | Normalisation noms, avatars (réexports racine) |

Flux typique : **gestionnaire** → **service** → **requêtes** → base ; validation via **modèles**.

## État de la migration

| Zone | Statut |
|------|--------|
| `modeles/` + alias `schemas/` | Fait |
| `gestionnaires/accueil`, `meilleurs`, `stats_modele` | Fait |
| `gestionnaires/classement`, `equipes`, `joueurs`, `analyse` | Fait (routes extraites de `serveur.py`) |
| `gestionnaires/communaute`, `forum`, `cotes` | Alias vers modules racine |
| `requetes/connexion`, `joueurs`, `matchs`, `equipes` | Fait (SQL matchs/équipes extrait) |
| `requetes/analyses` | Wrapper `historique_analyses` |
| `requetes/communaute`, `forum` | Placeholders (SQL encore dans modules racine) |
| `services/*` | Wrappers réexport (migration progressive) |
| `serveur.py` | Allégé : plus de routes HTTP directes, helpers métier restants |
| `communaute.py` / `forum.py` | À découper (2000+ lignes) |

## Routes par gestionnaire

| Gestionnaire | Endpoints |
|--------------|-----------|
| `accueil.py` | `GET /api/accueil` |
| `meilleurs.py` | `GET /api/meilleurs` |
| `classement.py` | `GET /api/classement`, `/api/elo`, `/api/calendrier`, `/api/prochains_matchs` |
| `equipes.py` | `GET /api/equipe`, `/api/equipes-analyse` |
| `joueurs.py` | `GET /api/joueur`, `/api/recherche` |
| `analyse.py` | `GET /api/analyse-rencontre`, `/api/analyse-rencontre/ia` |
| `stats_modele.py` | `GET /api/stats-modele` |
| `cotes.py` | Routes cotes (depuis `cotes.py`) |
| `communaute.py` | Routes communauté (depuis `communaute.py`) |
| `forum.py` | Routes forum (depuis `forum.py`) |

## Compatibilité

- `schemas/` → alias vers `modeles/` (`from schemas import …` continue de fonctionner).
- `stats_modele.py` → réexporte `gestionnaires.stats_modele`.
- Imports racine inchangés : `from analyse_rencontre import analyser_rencontre`, etc.
- `serveur.py` expose toujours les helpers (`calculer_classement`, `ouvrir_base`, …) pour les tests et `gestionnaires/accueil`.

## Migration progressive (suite)

1. Extraire le SQL de `communaute.py` / `forum.py` vers `requetes/`.
2. Déplacer la logique métier de `serveur.py` vers `services/` (classement, fiche équipe, radar).
3. Remplacer les wrappers `services/*` par du code déplacé depuis les modules racine.
4. Déplacer physiquement `correspondances.py` etc. dans `utilitaires/`.

Ordre recommandé par endpoint : **requêtes** → **service** → **gestionnaire** ; lancer `pytest` à chaque étape.

## Tests

```bash
cd site/api
pip install -r requirements-tests.txt
pytest
```
