# Gestionnaires (routes FastAPI)

Couche **gestionnaires** : endpoints HTTP (`APIRouter`), validation via `modeles/`, délégation à `services/` et `requetes/`.

| Module | Routes | Statut |
|--------|--------|--------|
| `accueil.py` | `GET /api/accueil` | Migré (helpers encore dans `serveur.py`) |
| `meilleurs.py` | `GET /api/meilleurs` | Migré (service + requêtes) |
| `stats_modele.py` | `GET /api/stats-modele` | Migré |
| `classement.py` | `GET /api/classement`, `/api/elo`, `/api/calendrier`, `/api/prochains_matchs` | Migré |
| `equipes.py` | `GET /api/equipe`, `/api/equipes-analyse` | Migré |
| `joueurs.py` | `GET /api/joueur`, `/api/recherche` | Migré |
| `analyse.py` | `GET /api/analyse-rencontre`, `/api/analyse-rencontre/ia` | Migré |
| `cotes.py` | Routes cotes | Alias → `cotes.py` |
| `communaute.py` | Routes communauté | Alias → `communaute.py` |
| `forum.py` | Routes forum | Alias → `forum.py` |

Les anciens modules racine (`stats_modele.py`, `cotes.py`, etc.) restent des points d'entrée de compatibilité.
