# Validation des entrées client

Tous les corps JSON (`POST` / `PATCH` / `PUT`) et les paramètres de requête sensibles (`GET`) passent par des modèles Pydantic v2 dans ce dossier (`modeles/`).

> **Note :** le dossier `schemas/` reste un alias de compatibilité ; les nouveaux imports doivent utiliser `modeles`.

Règles appliquées :

- `extra='forbid'` sur les corps : rejette les champs inattendus (évite l'injection de données parasites).
- Longueurs max alignées sur les colonnes SQLite et constantes métier.
- `str_strip_whitespace` + refus des chaînes vides pour les champs obligatoires.
- Regex pseudo, e-mail, saison, code ligue ; énumérations pour pronostics, réactions, votes 1/N/2.
- `model_validator` pour la cohérence métier (ex. pronostic score vs 1X2, équipes distinctes).
- Requêtes SQL inchangées : paramètres liés (`?`), jamais de concaténation de valeurs utilisateur.

Les gestionnaires (`gestionnaires/`) importent ces modèles ; la logique métier (anti-spam, rate limit, sessions) reste dans `services/`.
