# Planifier la mise à jour des données

Les sources du projet (football-data.co.uk, Understat, openfootball…) **ne sont pas live**.
Elles publient souvent avec **1 à 2 jours de retard**. Ce guide explique comment
**rafraîchir automatiquement** la base locale `donnees/football.db` — pas comment
afficher un score minute par minute.

## Ce que « à jour » veut dire ici

| Besoin | Réaliste avec ce projet ? | Comment |
|--------|---------------------------|---------|
| Matchs / stats à jour chaque jour ou toutes les heures | Oui (quasi temps réel) | Relancer `mettre_a_jour.py` ou `surveiller_sources.py` |
| Score live pendant le match | Non avec football-data | Clé API payante + endpoint live / websockets |
| xG / stats avancées live | Non en open data | Hors périmètre (pas de scrape FBref / Sofascore) |

Commande manuelle (≈ 10 min) à la racine du dépôt :

```bash
python scripts/mettre_a_jour.py
```

Ce script enchaîne déjà (non bloquant) :

1. `enregistrer_analyses.py` — prévisions / résultats dans `analyses.db`
2. `boucle_amelioration.py` — figer / juger / calibrer Solo selon le jour

Puis recharger le site (ex. localhost:5173).

---

## Boucle d’amélioration Solo (automatique)

Une **seule** tâche planifiée 1–2× / jour (ou toutes les 6 h) suffit.
`boucle_amelioration.py` décide selon **l’heure locale** du PC :

| Quand | Action | Idempotent |
|-------|--------|------------|
| Jeudi ≥ 18 h ou vendredi | Figer les marchés Solo du weekend (si pas déjà figé) | Oui |
| Chaque passage | Juger les matchs joués sans verdict | Oui |
| Après juger | Réentraîner le calibrateur si ≥ 20 matchs | Oui / skip |

Suivi hit-rate : `donnees/modeles/bilan_solo.json` (suggestion de seuils en log si hit-rate très faible — **aucun changement magique** des seuils Solo).

```bash
python scripts/boucle_amelioration.py
python scripts/boucle_amelioration.py --forcer-figer
python scripts/boucle_amelioration.py --skip-calibrateur
```

Pas besoin d’une tâche « vendredi 12 h » dédiée : la logique jour dans la boucle suffit
dès que le planificateur tourne au moins une fois le vendredi (ou jeudi soir).

Le script planifié Windows (`mettre-a-jour-planifie.ps1.example`) enchaîne
`surveiller_sources.py --une-fois` → `enregistrer_analyses.py` → **`boucle_amelioration.py`**
(même si aucune source n’a changé — indispensable pour figer le vendredi).

---

## Option A — PC Windows (Task Scheduler)

Idéal chez soi : mise à jour **1–2× / jour** (ou toutes les 6 heures).

### 1. Script d’exemple

Copier `deploy/mettre-a-jour-planifie.ps1.example` vers
`deploy/mettre-a-jour-planifie.ps1`, puis adapter le chemin du projet.

### 2. Créer la tâche (interface)

1. Ouvrir **Planificateur de tâches** → Créer une tâche.
2. Déclencheur : quotidien, répéter toutes les **6 heures** pendant 1 jour
   (ou 2 déclencheurs : matin + soir — assez pour figer le vendredi).
3. Action : démarrer un programme
   - Programme : `powershell.exe`
   - Arguments :
     `-NoProfile -ExecutionPolicy Bypass -File "C:\Users\sekei\football-datasets\deploy\mettre-a-jour-planifie.ps1"`
4. Cocher « Exécuter même si l’utilisateur n’est pas connecté » si le PC reste allumé.
5. Condition : décocher « Démarrer uniquement sur alimentation secteur » si laptop.

### 3. Variante en une ligne (PowerShell admin)

Adapter le chemin, puis :

```powershell
$projet = "C:\Users\sekei\football-datasets"
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
  -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$projet\deploy\mettre-a-jour-planifie.ps1`""
$declencheur = New-ScheduledTaskTrigger -Once -At (Get-Date).Date `
  -RepetitionInterval (New-TimeSpan -Hours 6) `
  -RepetitionDuration (New-TimeSpan -Days 3650)
Register-ScheduledTask -TaskName "StatsFoot-MiseAJour" `
  -Action $action -Trigger $declencheur -Description "MAJ football.db + boucle Solo"
```

### Surveillance intelligente (recommandé si le PC reste allumé)

Au lieu d’un cron aveugle, laisser tourner la surveillance (contrôle toutes les **20 min**,
collecte seulement si une source a changé) :

```bash
python scripts/surveiller_sources.py
```

Une seule passe (pour Task Scheduler) :

```bash
python scripts/surveiller_sources.py --une-fois
```

**Important** : si vous n’utilisez que `surveiller_sources` en boucle, ajoutez aussi un
appel périodique à `boucle_amelioration.py` (comme dans le `.ps1.example`), sinon le
figeage vendredi ne tourne que lorsqu’une source change.

---

## Option B — GitHub Actions (déjà présent)

Fichier : `.github/workflows/recolter-donnees-du-jour.yml`

- Cron quotidien **03:00 UTC** (+ lancement manuel `workflow_dispatch`)
- Collecte 5 championnats + LDC, sauve le JSON du jour dans `rapports/donnees/`
- **Ne régénère pas** `donnees/football.db` sur votre PC

Utile pour historiser / partager. Pour le site local, il faut encore lancer
`mettre_a_jour.py` (ou option A) sur la machine qui sert l’API.

---

## Option C — API-Football / The Odds API (clé)

| Clé | Rôle actuel | Live score ? |
|-----|-------------|--------------|
| `CLE_API_FOOTBALL` (`.env`) | Fixtures/scores récents (Big 5 + Super Lig + LDC si quota) + stats joueurs (`collecter_api_football.py`), free ~100 req/j, rotation + cache. Free = saisons historiques (souvent 2022–2024) ; saison courante → plan Pro | Non (fenêtre J−14 / J+21, pas de polling minute) |
| The Odds API | Cotes des matchs à venir (API site) | Non (cotes, pas minute-by-minute) |

Obtenir la clé : [dashboard.api-football.com](https://dashboard.api-football.com/register) → API Key → `.env` (`CLE_API_FOOTBALL=`). Sans clé : skip propre.

Pour du **vrai live** (score minute-par-minute) : abonnement + module dédié côté API —
hors flux open data / free tier actuel.

---

## Option Linux (serveur / Raspberry Pi)

Cron 2× / jour (collecte + boucle Solo) :

```cron
0 8,18 * * * cd /opt/statsfoot && .venv/bin/python scripts/mettre_a_jour.py >> /var/log/statsfoot-maj.log 2>&1
```

Ou surveillance + boucle (recommandé) :

```cron
*/30 * * * * cd /opt/statsfoot && .venv/bin/python scripts/surveiller_sources.py --une-fois >> /var/log/statsfoot-surveillance.log 2>&1 && .venv/bin/python scripts/boucle_amelioration.py >> /var/log/statsfoot-boucle.log 2>&1
```

---

## Limites à garder en tête

- **Sauvegarde** : inclure `donnees/analyses.db` et `donnees/modeles/` dans les backups
  (voir `deploy/sauvegarder-bases.sh.example`).
- **football-data.co.uk** : résultats souvent publiés avec **1–2 jours** de retard →
  même avec un cron horaire, le match d’hier soir peut manquer jusqu’à publication.
- Understat / openfootball : mises à jour irrégulières, pas live.
- Ne pas lancer deux collectes en parallèle (`surveiller_sources.py` pose déjà un verrou).
- ClubElo / free APIs : peuvent être down ou quota limité — la collecte continue sans elles.
- La boucle Solo **ne bloque jamais** `mettre_a_jour.py` en cas d’échec.
