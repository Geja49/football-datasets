# Déployer Stats Foot sur un serveur à la maison

Guide pragmatique pour rendre le site accessible sur Internet depuis une machine
chez vous (PC / mini-PC / Raspberry Pi / NAS Linux).

## Architecture cible

```
Internet → (routeur 80/443 OU tunnel) → Nginx (HTTPS + SPA)
                                      → proxy /api et /photos → uvicorn :8001
                                      → fichiers site/frontend/dist
```

- **1 seul worker uvicorn** (SQLite ne gère pas bien l’écriture multi-processus).
- Front et API sur **la même origine HTTPS** (recommandé) : cookies de session simples.
- API écoute uniquement en **127.0.0.1:8001** (jamais exposée directement).

## Prérequis

- Linux (Ubuntu 22.04+ / Debian 12+ recommandé)
- Domaine (optionnel mais fortement conseillé pour Let’s Encrypt)
- Accès `sudo`
- Ports **80** et **443** joignables depuis Internet **ou** un tunnel (Cloudflare / Tailscale)

## Checklist réseau (ordre)

1. **IP publique** : vérifiez que votre FAI ne vous met pas en CGNAT
   (`curl ifconfig.me` depuis le serveur ≠ IP privée 100.64.x.x souvent).
2. **DNS** : enregistrement A (ou AAAA) du domaine → IP publique du routeur.
3. **Routeur** : port forwarding TCP **80** et **443** → IP LAN du serveur.
4. **Pare-feu serveur** : autoriser SSH + 80/443 (ex. `ufw`).
5. Si CGNAT / FAI bloque les ports entrants → **Cloudflare Tunnel** ou **Tailscale Funnel**
   (pas besoin d’ouvrir le routeur).

## Variables `.env` production

Copier `.env.exemple` → `.env` à la racine du dépôt, puis au minimum :

```env
ENVIRONNEMENT=production
COOKIE_SECURE=1
# Même origine Nginx : laisser vide, ou lister le domaine si front séparé
ORIGINES_CORS=https://statsfoot.votredomaine.fr
EMAIL_ADMIN_COMMUNAUTE=vous@exemple.fr
GOOGLE_CLIENT_ID=   # si OAuth Google : origines JS = https://votre-domaine
```

Redémarrer le service après toute modification de `.env`.

## Installation rapide

Les fichiers `deploy/*.example` sont des **modèles** : adapter chemins et domaine.

### 1. Paquets

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nginx certbot \
  python3-certbot-nginx git ufw
# Node.js LTS 20+ pour builder le front
```

### 2. Projet + venv

```bash
sudo useradd --system --home /opt/statsfoot --shell /usr/sbin/nologin statsfoot || true
sudo mkdir -p /opt/statsfoot
# cloner ou copier le dépôt dans /opt/statsfoot, chown statsfoot
cd /opt/statsfoot
sudo -u statsfoot python3 -m venv .venv
sudo -u statsfoot .venv/bin/pip install -r site/api/requirements.txt
sudo -u statsfoot cp .env.exemple .env
# éditer .env (COOKIE_SECURE=1, etc.)
sudo -u statsfoot .venv/bin/python scripts/creer_base.py
```

### 3. Build frontend

```bash
cd /opt/statsfoot/site/frontend
sudo -u statsfoot npm ci
sudo -u statsfoot npm run build
```

### 4. systemd (API)

```bash
sudo cp deploy/statsfoot.service.example /etc/systemd/system/statsfoot.service
# adapter chemins / utilisateur
sudo systemctl daemon-reload
sudo systemctl enable --now statsfoot
sudo systemctl status statsfoot
```

Important : `--workers 1` et `WorkingDirectory` = racine du dépôt.

### 5. Nginx

```bash
sudo cp deploy/nginx-statsfoot.conf.example /etc/nginx/sites-available/statsfoot
# remplacer statsfoot.example.com et /opt/statsfoot
sudo ln -sf /etc/nginx/sites-available/statsfoot /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### 6. HTTPS

**Option A — Domaine public + ports ouverts (recommandé)**

```bash
sudo certbot --nginx -d statsfoot.votredomaine.fr
sudo certbot renew --dry-run
```

**Option B — Cloudflare Tunnel** (CGNAT / pas de ports)

- Installer `cloudflared`, créer un tunnel vers `http://127.0.0.1:80` (Nginx)
  ou directement vers uvicorn + servir le front autrement.
- HTTPS terminé chez Cloudflare ; derrière le tunnel, forcez quand même
  `COOKIE_SECURE=1` si les navigateurs voient HTTPS.

**Option C — Tailscale**

- Accès privé au LAN via Tailscale ; Funnel pour un accès public limité.
- Adapté « amis / famille », moins « site grand public ».

### 7. Pare-feu

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

### 8. Vérifications

```bash
curl -sI "https://VOTRE_DOMAINE/api/accueil" | head
curl -s "https://VOTRE_DOMAINE/api/communaute/config"
# Connexion navigateur : cookie session_communaute avec Secure ; HttpOnly ; SameSite=Lax
```

## Données à jour (pas « live »)

Les CSV open data ont souvent **1–2 jours de retard**. Pour rafraîchir
automatiquement `football.db` (Task Scheduler Windows, cron Linux, limites API),
voir **`deploy/planifier-mise-a-jour.md`**.

## Sauvegardes automatiques

```bash
sudo mkdir -p /var/backups/statsfoot
sudo cp deploy/sauvegarder-bases.sh.example /opt/statsfoot/deploy/sauvegarder-bases.sh
sudo chmod +x /opt/statsfoot/deploy/sauvegarder-bases.sh
# tester une fois
sudo /opt/statsfoot/deploy/sauvegarder-bases.sh
```

Crontab (root ou utilisateur dédié) :

```cron
30 3 * * * /opt/statsfoot/deploy/sauvegarder-bases.sh >> /var/log/statsfoot-backup.log 2>&1
```

La copie fichier suffit pour démarrer (1 worker). Sous forte charge, préférer
`sqlite3 donnees/communaute.db ".backup '/chemin/copie.db'"`.

## Points d’attention (home lab)

| Sujet | Risque / action |
|--------|------------------|
| IP dynamique | Utiliser un DNS dynamique (DuckDNS, Cloudflare API…) |
| CGNAT FAI | Port forwarding impossible → Tunnel Cloudflare / Tailscale |
| Pare-feu Windows/routeur | Ouvrir 80/443 vers la bonne machine LAN |
| SQLite | Toujours `--workers 1` ; sauvegardes quotidiennes |
| Mises à jour | `git pull` + rebuild front + `systemctl restart statsfoot` |
| Google OAuth | Origines JS = URL HTTPS exacte du site |
| Exposition publique | Rate limit connexion/inscription déjà côté API ; garder Nginx à jour |

## Script modèle

Voir aussi `deploy/install.sh.example` (sections commentées à exécuter une par une).
