/** Couleurs officielles approximatives (primaire / secondaire) pour le thème sombre. */

function hexVersRgb(hex) {
  const h = hex.replace("#", "");
  return [
    parseInt(h.slice(0, 2), 16),
    parseInt(h.slice(2, 4), 16),
    parseInt(h.slice(4, 6), 16),
  ];
}

function rgbVersHex(r, g, b) {
  return `#${[r, g, b].map((v) => v.toString(16).padStart(2, "0")).join("")}`;
}

function melangerCouleurs(c1, c2, ratio) {
  const [r1, g1, b1] = hexVersRgb(c1);
  const [r2, g2, b2] = hexVersRgb(c2);
  const t = Math.min(1, Math.max(0, ratio));
  return rgbVersHex(
    Math.round(r1 * (1 - t) + r2 * t),
    Math.round(g1 * (1 - t) + g2 * t),
    Math.round(b1 * (1 - t) + b2 * t),
  );
}

export function paletteClub(primaire, secondaire = primaire) {
  const fondBase = "#070b12";
  const carteBase = "#121a28";
  const lisibleBase = "#1c2738";
  const ligneBase = "#243044";
  return {
    accent: primaire,
    bandeau: melangerCouleurs(primaire, fondBase, 0.88),
    fond: melangerCouleurs(primaire, fondBase, 0.93),
    fondCarte: melangerCouleurs(primaire, carteBase, 0.14),
    fondLisible: melangerCouleurs(primaire, lisibleBase, 0.2),
    ligne: melangerCouleurs(primaire, ligneBase, 0.28),
    hero: `linear-gradient(115deg, ${melangerCouleurs(primaire, fondBase, 0.92)} 0%, ${melangerCouleurs(secondaire, fondBase, 0.78)} 55%, ${primaire} 150%)`,
  };
}

/** Noms tels qu’en base (joueurs.csv / matchs). */
const COULEURS_CLUBS = {
  // Premier League
  Arsenal: paletteClub("#EF0107", "#9C824A"),
  "Aston Villa": paletteClub("#670E36", "#95BFE5"),
  Bournemouth: paletteClub("#DA291C", "#000000"),
  Brentford: paletteClub("#E30613", "#FFB81C"),
  Brighton: paletteClub("#0057B8", "#FFCD00"),
  Chelsea: paletteClub("#034694", "#EE242C"),
  Coventry: paletteClub("#009EE0", "#007A33"),
  "Crystal Palace": paletteClub("#1B458F", "#C4122E"),
  Everton: paletteClub("#003399", "#FFFFFF"),
  Fulham: paletteClub("#000000", "#CC0000"),
  Hull: paletteClub("#F5971D", "#000000"),
  Ipswich: paletteClub("#003090", "#FFFFFF"),
  Leeds: paletteClub("#FFCD00", "#1D428A"),
  Liverpool: paletteClub("#C8102E", "#00B2A9"),
  "Manchester City": paletteClub("#6CABDD", "#1C2C5B"),
  "Manchester United": paletteClub("#DA291C", "#FBE122"),
  "Newcastle United": paletteClub("#241F20", "#FFFFFF"),
  "Nottingham Forest": paletteClub("#DD0000", "#FFFFFF"),
  Sunderland: paletteClub("#EB172B", "#FFFFFF"),
  Tottenham: paletteClub("#132257", "#FFFFFF"),
  // La Liga
  Alaves: paletteClub("#0054A6", "#FFFFFF"),
  "Athletic Club": paletteClub("#EE2523", "#FFFFFF"),
  "Atletico Madrid": paletteClub("#CB3524", "#272E61"),
  Barcelona: paletteClub("#A50044", "#004D98"),
  "Celta Vigo": paletteClub("#8AC3EE", "#E52521"),
  "Deportivo La Coruna": paletteClub("#005BAC", "#FFFFFF"),
  Elche: paletteClub("#008835", "#FFFFFF"),
  Espanyol: paletteClub("#007FC8", "#FFFFFF"),
  Getafe: paletteClub("#005999", "#FFFFFF"),
  Levante: paletteClub("#005999", "#C8102E"),
  Malaga: paletteClub("#009EE0", "#FFFFFF"),
  Osasuna: paletteClub("#D91A21", "#0A346F"),
  "Racing Santander": paletteClub("#008000", "#FFFFFF"),
  "Rayo Vallecano": paletteClub("#E53027", "#FFFFFF"),
  "Real Betis": paletteClub("#00954C", "#FFFFFF"),
  "Real Madrid": paletteClub("#FEBE10", "#00529F"),
  "Real Sociedad": paletteClub("#0067B1", "#FFFFFF"),
  Sevilla: paletteClub("#D01012", "#FFFFFF"),
  Valencia: paletteClub("#EE3524", "#F7B500"),
  Villarreal: paletteClub("#FFE667", "#005187"),
  // Ligue 1
  Angers: paletteClub("#000000", "#FFFFFF"),
  Auxerre: paletteClub("#003DA5", "#FFFFFF"),
  Brest: paletteClub("#D71920", "#FFFFFF"),
  "Le Havre": paletteClub("#009EE0", "#FFFFFF"),
  "Le Mans": paletteClub("#CE1126", "#FDB913"),
  Lens: paletteClub("#D71920", "#FDB913"),
  Lille: paletteClub("#E30613", "#242066"),
  Lorient: paletteClub("#F58113", "#000000"),
  Lyon: paletteClub("#003DA5", "#DA0812"),
  Marseille: paletteClub("#2FAEE0", "#FFFFFF"),
  Monaco: paletteClub("#E30613", "#FFFFFF"),
  Nice: paletteClub("#D71920", "#000000"),
  "Paris FC": paletteClub("#002654", "#DA0812"),
  "Paris Saint Germain": paletteClub("#004170", "#DA0812"),
  Rennes: paletteClub("#E30613", "#000000"),
  Strasbourg: paletteClub("#009EE0", "#FFFFFF"),
  Toulouse: paletteClub("#582C83", "#FFFFFF"),
  Troyes: paletteClub("#006CB5", "#FFFFFF"),
  // Serie A
  "AC Milan": paletteClub("#FB090B", "#000000"),
  Atalanta: paletteClub("#1E71B8", "#000000"),
  Bologna: paletteClub("#A21C26", "#003DA5"),
  Cagliari: paletteClub("#A21C26", "#003DA5"),
  Como: paletteClub("#004A99", "#FFFFFF"),
  Fiorentina: paletteClub("#482E92", "#FFFFFF"),
  Frosinone: paletteClub("#F7E017", "#003DA5"),
  Genoa: paletteClub("#A21C26", "#003DA5"),
  Inter: paletteClub("#010E80", "#000000"),
  Juventus: paletteClub("#000000", "#FFFFFF"),
  Lazio: paletteClub("#87D8F7", "#FFFFFF"),
  Lecce: paletteClub("#FFD700", "#E30613"),
  Monza: paletteClub("#E30613", "#FFFFFF"),
  Napoli: paletteClub("#009EE0", "#FFFFFF"),
  "Parma Calcio 1913": paletteClub("#F7E017", "#003DA5"),
  Roma: paletteClub("#8E1F2F", "#F7B500"),
  Sassuolo: paletteClub("#008000", "#000000"),
  Torino: paletteClub("#8E1F2F", "#FFFFFF"),
  Udinese: paletteClub("#000000", "#FFFFFF"),
  Venezia: paletteClub("#000000", "#F7B500"),
  // Bundesliga (clubs fréquents)
  "Bayern Munich": paletteClub("#DC052D", "#0066B2"),
  "Borussia Dortmund": paletteClub("#FDE100", "#000000"),
  "RB Leipzig": paletteClub("#DD0741", "#FFFFFF"),
  "Bayer Leverkusen": paletteClub("#E32221", "#000000"),
  "Borussia M.Gladbach": paletteClub("#000000", "#FFFFFF"),
  "Eintracht Frankfurt": paletteClub("#E1000F", "#000000"),
  Wolfsburg: paletteClub("#65B32E", "#FFFFFF"),
  Freiburg: paletteClub("#E30613", "#000000"),
  Hoffenheim: paletteClub("#1961AA", "#FFFFFF"),
  Stuttgart: paletteClub("#E32221", "#FFFFFF"),
  "Werder Bremen": paletteClub("#009933", "#FFFFFF"),
  Augsburg: paletteClub("#BA3733", "#006633"),
  "Union Berlin": paletteClub("#EB1923", "#F7B500"),
  "Mainz 05": paletteClub("#C3141D", "#FFFFFF"),
  "FC Cologne": paletteClub("#ED1C24", "#FFFFFF"),
};

const ALIAS_CLUBS = {
  PSG: "Paris Saint Germain",
  "Paris SG": "Paris Saint Germain",
  "Paris Saint-Germain": "Paris Saint Germain",
  "FC Barcelona": "Barcelona",
  "Man City": "Manchester City",
  "Man United": "Manchester United",
  "Man Utd": "Manchester United",
  "Atlético Madrid": "Atletico Madrid",
  "Atletico de Madrid": "Atletico Madrid",
  "Athletic Bilbao": "Athletic Club",
  "Inter Milan": "Inter",
  "Internazionale": "Inter",
  "AC Fiorentina": "Fiorentina",
  "AS Monaco": "Monaco",
  "Olympique Lyon": "Lyon",
  "Olympique Lyonnais": "Lyon",
  "Olympique Marseille": "Marseille",
  "OM": "Marseille",
  Spurs: "Tottenham",
  "Newcastle Utd": "Newcastle United",
  "Nott'm Forest": "Nottingham Forest",
  "Nottingham For.": "Nottingham Forest",
};

export function couleursPourClub(nomEquipe) {
  if (!nomEquipe) return null;
  const direct = COULEURS_CLUBS[nomEquipe];
  if (direct) return direct;
  const alias = ALIAS_CLUBS[nomEquipe];
  if (alias && COULEURS_CLUBS[alias]) return COULEURS_CLUBS[alias];
  return null;
}

export function estPageEquipe(route) {
  return Boolean(
    route.params.equipe &&
      /\/equipe\//.test(route.path) &&
      !route.path.endsWith("/analyser"),
  );
}

/** Essaie plusieurs noms (équipe + alias API) jusqu’à trouver une palette. */
export function resoudrePaletteClub(...noms) {
  for (const nom of noms.flat().filter(Boolean)) {
    const palette = couleursPourClub(nom);
    if (palette) return palette;
  }
  return null;
}

/** Variables CSS à appliquer sur le conteneur `.page-equipe`. */
export function variablesCssClub(palette) {
  if (!palette) return null;
  return {
    "--accent": palette.accent,
    "--bandeau": palette.bandeau,
    "--fond": palette.fond,
    "--fond-carte": palette.fondCarte,
    "--fond-lisible": palette.fondLisible,
    "--ligne": palette.ligne,
    "--hero": palette.hero,
  };
}
