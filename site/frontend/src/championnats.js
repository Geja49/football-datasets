/** Liste et métadonnées UI partagées pour les compétitions. */

export const CHAMPIONNATS_DEFAUT = [
  "Premier League",
  "La Liga",
  "Bundesliga",
  "Serie A",
  "Ligue 1",
  "Ligue des champions",
];

export const CLASSES_CARTES = {
  "Premier League": "carte-pl",
  "La Liga": "carte-laliga",
  Bundesliga: "carte-bundesliga",
  "Serie A": "carte-seriea",
  "Ligue 1": "carte-ligue1",
  "Ligue des champions": "carte-ldc",
};

export const CODES_CARTES = {
  "Premier League": "PL",
  "La Liga": "LL",
  Bundesliga: "BL",
  "Serie A": "SA",
  "Ligue 1": "L1",
  "Ligue des champions": "UCL",
};

/** Chemins locaux (public/) — pas de scrape sites officiels. */
export const LOGOS_CARTES = {
  "Premier League": "/logos-championnats/premier-league.png",
  "La Liga": "/logos-championnats/la-liga.png",
  Bundesliga: "/logos-championnats/bundesliga.png",
  "Serie A": "/logos-championnats/serie-a.png",
  "Ligue 1": "/logos-championnats/ligue-1.png",
  "Ligue des champions": "/logos-championnats/ligue-des-champions.png",
};

export function libelleTypeCompetition(nom) {
  return nom === "Ligue des champions" ? "Coupe d'Europe" : "Championnat";
}
