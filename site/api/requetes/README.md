# Requêtes (accès données)

Couche **requêtes** : SQL paramétré (`?`) isolé de la logique HTTP et métier.

| Module | Rôle |
|--------|------|
| `connexion.py` | Ouverture SQLite, `lignes_dict`, chemins `football.db` |
| `joueurs.py` | Top buteurs/passeurs, saison avec effectifs |
| `matchs.py` | Matchs, calendrier, confrontations, xG, recherche équipes |
| `equipes.py` | Sites équipes, effectifs, couverture défense |
| `analyses.py` | Lectures `analyses.db` (wrapper `historique_analyses`) |
| `communaute.py` | Placeholder — SQL encore dans `communaute.py` |
| `forum.py` | Placeholder — SQL encore dans `forum.py` |

**Règle :** pas de `HTTPException`, pas de validation Pydantic ici — uniquement lecture/écriture base.
