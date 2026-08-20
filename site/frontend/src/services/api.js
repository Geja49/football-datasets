async function getJson(url) {
  const reponse = await fetch(url);
  if (!reponse.ok) {
    throw new Error("Impossible de charger les données");
  }
  return reponse.json();
}

export function chargerAccueil() {
  return getJson("/api/accueil");
}

export function chargerClassement(championnat, saison) {
  const params = new URLSearchParams({ championnat, saison });
  return getJson(`/api/classement?${params}`);
}

export function chargerCalendrier(championnat, saison) {
  const params = new URLSearchParams({ championnat, saison });
  return getJson(`/api/calendrier?${params}`);
}

export function chargerEquipe(championnat, saison, equipe) {
  const params = new URLSearchParams({ championnat, saison, equipe });
  return getJson(`/api/equipe?${params}`);
}

export function chargerJoueur(nom, championnat) {
  const params = new URLSearchParams({ nom });
  if (championnat) params.set("championnat", championnat);
  return getJson(`/api/joueur?${params}`);
}

export function rechercher(q) {
  return getJson(`/api/recherche?${new URLSearchParams({ q })}`);
}

export function chargerEquipesAnalyse(championnat, saison) {
  const params = new URLSearchParams({ championnat, saison });
  return getJson(`/api/equipes-analyse?${params}`);
}

export function chargerProchainsMatchs(championnat, saison, equipe) {
  const params = new URLSearchParams({ championnat, saison });
  if (equipe) params.set("equipe", equipe);
  return getJson(`/api/prochains_matchs?${params}`);
}

export function chargerAnalyse(championnat, saison, domicile, exterieur) {
  const params = new URLSearchParams({ championnat, saison, domicile, exterieur });
  return getJson(`/api/analyse-rencontre?${params}`);
}

export function chargerMeilleurs(championnat, saison, type) {
  const params = new URLSearchParams({ championnat, saison, type });
  return getJson(`/api/meilleurs?${params}`);
}
