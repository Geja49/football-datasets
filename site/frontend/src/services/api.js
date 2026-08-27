const cacheMemoire = new Map();
const DUREE_CACHE_MS = 90_000;
const enCours = new Map();

async function getJson(url, { cache = true } = {}) {
  if (cache) {
    const entree = cacheMemoire.get(url);
    if (entree && Date.now() - entree.quand < DUREE_CACHE_MS) {
      return entree.donnees;
    }
    if (enCours.has(url)) {
      return enCours.get(url);
    }
  }
  const promesse = (async () => {
    const reponse = await fetch(url);
    if (!reponse.ok) {
      let message = "Impossible de charger les données";
      try {
        const corps = await reponse.json();
        if (typeof corps.detail === "string") {
          message = corps.detail;
        }
      } catch {
        /* corps non JSON */
      }
      throw new Error(message);
    }
    const donnees = await reponse.json();
    if (cache) {
      cacheMemoire.set(url, { quand: Date.now(), donnees });
    }
    return donnees;
  })();
  if (cache) {
    enCours.set(url, promesse);
    try {
      return await promesse;
    } finally {
      enCours.delete(url);
    }
  }
  return promesse;
}

export function chargerAccueil() {
  return getJson("/api/accueil");
}

export function chargerClassement(championnat, saison, { elo = false } = {}) {
  const params = new URLSearchParams({ championnat, saison });
  if (elo) params.set("elo", "1");
  return getJson(`/api/classement?${params}`);
}

export function chargerElo(equipe, { forcer = false } = {}) {
  const params = new URLSearchParams({ equipe });
  if (forcer) params.set("forcer", "1");
  return getJson(`/api/elo?${params}`, { cache: false });
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
  return getJson(`/api/recherche?${new URLSearchParams({ q })}`, { cache: false });
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
  return getJson(`/api/analyse-rencontre?${params}`, { cache: false });
}

export function chargerMeilleurs(championnat, saison, type) {
  const params = new URLSearchParams({ championnat, saison, type });
  return getJson(`/api/meilleurs?${params}`);
}

export function chargerCotes() {
  return getJson("/api/cotes", { cache: false });
}

export function prechargerLien(destination) {
  if (!destination || typeof destination !== "object") return;
  const chemin = destination.path || "";
  const query = destination.query || {};
  const saison = query.saison;
  const parties = chemin.split("/").filter(Boolean);
  if (parties[0] !== "championnat" || !parties[1]) return;
  const championnat = decodeURIComponent(parties[1]);
  if (parties[2] === "equipe" && parties[3] && saison) {
    chargerEquipe(championnat, saison, decodeURIComponent(parties[3])).catch(() => {});
    return;
  }
  if (!saison) return;
  if (query.onglet === "calendrier") {
    chargerCalendrier(championnat, saison).catch(() => {});
  } else if (query.onglet === "buteurs") {
    chargerMeilleurs(championnat, saison, "buts").catch(() => {});
  } else if (query.onglet === "passeurs") {
    chargerMeilleurs(championnat, saison, "passes").catch(() => {});
  } else {
    chargerClassement(championnat, saison).catch(() => {});
  }
}

async function envoyerJson(url, options = {}) {
  const reponse = await fetch(url, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!reponse.ok) {
    let message = "Requête impossible";
    try {
      const corps = await reponse.json();
      if (typeof corps.detail === "string") {
        message = corps.detail;
      }
    } catch {
      /* corps non JSON */
    }
    throw new Error(message);
  }
  if (reponse.status === 204) return null;
  return reponse.json();
}

export function chargerUtilisateurConnecte() {
  return envoyerJson("/api/communaute/moi");
}

export function inscrireUtilisateur(donnees) {
  return envoyerJson("/api/communaute/inscription", {
    method: "POST",
    body: JSON.stringify(donnees),
  });
}

export function connecterUtilisateur(donnees) {
  return envoyerJson("/api/communaute/connexion", {
    method: "POST",
    body: JSON.stringify(donnees),
  });
}

export function deconnecterUtilisateur() {
  return envoyerJson("/api/communaute/deconnexion", { method: "POST" });
}

export function chargerCommentairesMatch(championnat, saison, domicile, exterieur) {
  const params = new URLSearchParams({ championnat, saison, domicile, exterieur });
  return envoyerJson(`/api/communaute/commentaires?${params}`);
}

export function publierCommentaireMatch(donnees) {
  return envoyerJson("/api/communaute/commentaires", {
    method: "POST",
    body: JSON.stringify(donnees),
  });
}

export function signalerCommentaireMatch(commentaireId, motif = "") {
  return envoyerJson(`/api/communaute/commentaires/${commentaireId}/signaler`, {
    method: "POST",
    body: JSON.stringify({ motif }),
  });
}

export function supprimerCommentaireMatch(commentaireId) {
  return envoyerJson(`/api/communaute/commentaires/${commentaireId}`, {
    method: "DELETE",
  });
}

export function chargerDisclaimerPronostics() {
  return envoyerJson("/api/communaute/pronostics/disclaimer");
}

export function chargerMesPronostics() {
  return envoyerJson("/api/communaute/pronostics/mes-pronos");
}

export function chargerPronosticMatch(championnat, saison, domicile, exterieur) {
  const params = new URLSearchParams({ championnat, saison, domicile, exterieur });
  return envoyerJson(`/api/communaute/pronostics?${params}`);
}

export function deposerPronostic(donnees) {
  return envoyerJson("/api/communaute/pronostics", {
    method: "POST",
    body: JSON.stringify(donnees),
  });
}

export function chargerClassementPronos(championnat, saison) {
  const params = new URLSearchParams({ championnat, saison });
  return getJson(`/api/communaute/classement?${params}`, { cache: false });
}

export function chargerProfilPublic(pseudo) {
  return getJson(`/api/communaute/profil/${encodeURIComponent(pseudo)}`, {
    cache: false,
  });
}

export function chargerConfigCommunaute() {
  return getJson("/api/communaute/config", { cache: false });
}

export function connecterGoogle(idToken) {
  return envoyerJson("/api/communaute/connexion/google", {
    method: "POST",
    body: JSON.stringify({ id_token: idToken }),
  });
}

export function basculerReactionCommentaire(commentaireId, typeReaction = "pouce") {
  return envoyerJson(`/api/communaute/commentaires/${commentaireId}/reactions`, {
    method: "POST",
    body: JSON.stringify({ type_reaction: typeReaction }),
  });
}

export function chargerReactionsCommentaire(commentaireId) {
  return envoyerJson(`/api/communaute/commentaires/${commentaireId}/reactions`);
}

export function chargerMatchsSansProno() {
  return envoyerJson("/api/communaute/pronostics/sans-prono");
}

export function chargerJourneesPronos(championnat, saison) {
  const params = new URLSearchParams({ championnat, saison });
  return envoyerJson(`/api/communaute/pronostics/journees?${params}`);
}

export function chargerPronosJournee(championnat, saison, journee) {
  const params = new URLSearchParams({ championnat, saison, journee });
  return envoyerJson(`/api/communaute/pronostics/journee?${params}`);
}

export function chargerMesLigues() {
  return envoyerJson("/api/communaute/ligues");
}

export function creerLiguePrivee(nom) {
  return envoyerJson("/api/communaute/ligues", {
    method: "POST",
    body: JSON.stringify({ nom }),
  });
}

export function rejoindreLiguePrivee(codeInvitation) {
  return envoyerJson("/api/communaute/ligues/rejoindre", {
    method: "POST",
    body: JSON.stringify({ code_invitation: codeInvitation }),
  });
}

export function chargerLiguePrivee(code) {
  return envoyerJson(`/api/communaute/ligues/${encodeURIComponent(code)}`);
}

export function chargerClassementLigue(code, championnat, saison, journee = "") {
  const params = new URLSearchParams({ championnat, saison });
  if (journee) params.set("journee", journee);
  return envoyerJson(
    `/api/communaute/ligues/${encodeURIComponent(code)}/classement?${params}`,
  );
}

export function majProfilCommunaute(donnees) {
  return envoyerJson("/api/communaute/moi/profil", {
    method: "PATCH",
    body: JSON.stringify(donnees),
  });
}

export function chargerCatalogueAvatars() {
  return envoyerJson("/api/communaute/avatars");
}

export function chargerNotifications() {
  return envoyerJson("/api/communaute/notifications");
}

export function chargerCompteNotifications() {
  return envoyerJson("/api/communaute/notifications/compte");
}

export function marquerNotificationLue(notificationId) {
  return envoyerJson(`/api/communaute/notifications/${notificationId}/lue`, {
    method: "POST",
  });
}

export function marquerToutesNotificationsLues() {
  return envoyerJson("/api/communaute/notifications/lues", {
    method: "POST",
  });
}

export function deposerPronosticsLot(pronostics) {
  return envoyerJson("/api/communaute/pronostics/lot", {
    method: "POST",
    body: JSON.stringify({ pronostics }),
  });
}

export function chargerMessagesLigue(code) {
  return envoyerJson(`/api/communaute/ligues/${encodeURIComponent(code)}/messages`);
}

export function publierMessageLigue(code, contenu) {
  return envoyerJson(`/api/communaute/ligues/${encodeURIComponent(code)}/messages`, {
    method: "POST",
    body: JSON.stringify({ contenu }),
  });
}

export function chargerSignalementsAdmin(statut = "ouvert") {
  const params = new URLSearchParams({ statut });
  return envoyerJson(`/api/communaute/admin/signalements?${params}`);
}

export function traiterSignalementAdmin(signalementId, statut = "traite") {
  return envoyerJson(`/api/communaute/admin/signalements/${signalementId}/traiter`, {
    method: "POST",
    body: JSON.stringify({ statut }),
  });
}

export function chargerEspacesForum() {
  return envoyerJson("/api/forum");
}

export function chargerSujetsForum(championnat) {
  return envoyerJson(
    `/api/forum/${encodeURIComponent(championnat)}/sujets`,
  );
}

export function creerSujetForum(championnat, titre, contenu) {
  return envoyerJson(
    `/api/forum/${encodeURIComponent(championnat)}/sujets`,
    {
      method: "POST",
      body: JSON.stringify({ titre, contenu }),
    },
  );
}

export function chargerSujetForum(sujetId) {
  return envoyerJson(`/api/forum/sujets/${sujetId}`);
}

export function publierMessageForum(sujetId, contenu, messageParentId = null) {
  const corps = { contenu };
  if (messageParentId != null) {
    corps.message_parent_id = messageParentId;
  }
  return envoyerJson(`/api/forum/sujets/${sujetId}/messages`, {
    method: "POST",
    body: JSON.stringify(corps),
  });
}

export function modifierSujetForum(sujetId, titre) {
  return envoyerJson(`/api/forum/sujets/${sujetId}`, {
    method: "PATCH",
    body: JSON.stringify({ titre }),
  });
}

export function modifierMessageForum(messageId, contenu) {
  return envoyerJson(`/api/forum/messages/${messageId}`, {
    method: "PATCH",
    body: JSON.stringify({ contenu }),
  });
}

export function supprimerMessageForum(messageId) {
  return envoyerJson(`/api/forum/messages/${messageId}`, {
    method: "DELETE",
  });
}

export function supprimerSujetForum(sujetId) {
  return envoyerJson(`/api/forum/sujets/${sujetId}`, {
    method: "DELETE",
  });
}

export function signalerMessageForum(messageId, motif = "") {
  return envoyerJson(`/api/forum/messages/${messageId}/signaler`, {
    method: "POST",
    body: JSON.stringify({ motif }),
  });
}

export function basculerReactionMessageForum(messageId, typeReaction = "pouce") {
  return envoyerJson(`/api/forum/messages/${messageId}/reactions`, {
    method: "POST",
    body: JSON.stringify({ type_reaction: typeReaction }),
  });
}

export function creerSondageForum(sujetId, question, options) {
  return envoyerJson(`/api/forum/sujets/${sujetId}/sondage`, {
    method: "POST",
    body: JSON.stringify({ question, options }),
  });
}

export function voterSondageForum(sondageId, optionId) {
  return envoyerJson(`/api/forum/sondages/${sondageId}/votes`, {
    method: "POST",
    body: JSON.stringify({ option_id: optionId }),
  });
}

export function supprimerSondageForum(sondageId) {
  return envoyerJson(`/api/forum/sondages/${sondageId}`, {
    method: "DELETE",
  });
}

export function chargerSondageMatch(championnat, saison, domicile, exterieur) {
  const params = new URLSearchParams({
    championnat,
    saison,
    domicile,
    exterieur,
  });
  return envoyerJson(`/api/communaute/sondage-match?${params}`);
}

export function voterSondageMatch(donnees) {
  return envoyerJson("/api/communaute/sondage-match", {
    method: "POST",
    body: JSON.stringify(donnees),
  });
}
