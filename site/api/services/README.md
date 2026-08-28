# Services (logique métier)

Couche **services** : règles métier, agrégations, enrichissements — sans HTTP ni SQL brut (sauf via `requetes/`).

| Module | Rôle | Statut |
|--------|------|--------|
| `meilleurs.py` | Top buteurs/passeurs, fallback saison, messages LDC | Implémenté |
| `analyse.py` | Analyse de rencontre | Wrapper → `analyse_rencontre.py` |
| `calibration.py` | Agrégats calibration | Wrapper → `calibration.py` |
| `calibrateur.py` | Infos calibrateur | Wrapper → `calibrateur.py` |
| `historique_analyses.py` | Prévisions figées | Wrapper → `historique_analyses.py` |
| `elo.py` | ClubElo | Wrapper → `elo_clubs.py` |
| `cotes.py` | Cotes marché | Wrapper → `cotes.py` |
| `communaute.py` | Communauté | Wrapper → `communaute.py` |
| `forum.py` | Forum | Wrapper → `forum.py` |
| `ia_analyse.py` | Analyse narrative IA | Wrapper → `ia_analyse.py` |

**Règle :** pas de `APIRouter` ni de dépendance FastAPI `Request`/`Response` ici.
