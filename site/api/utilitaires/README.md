# Utilitaires

Helpers légers partagés entre modules. **Source canonique encore à la racine** (`correspondances.py`, `alias_equipes.py`, `avatars.py`) ; ce dossier centralise les imports pour la migration.

| Module racine | Rôle |
|---------------|------|
| `correspondances.py` | Normalisation noms équipes / joueurs |
| `alias_equipes.py` | Alias openfootball → Understat |
| `avatars.py` | Catalogue et validation avatars communauté |

Usage : `from utilitaires.correspondances import normaliser` (ou import direct racine, les deux fonctionnent).
