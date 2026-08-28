<script setup>
import { computed, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { CHAMPIONNATS_DEFAUT } from "../championnats.js";
import AvatarUtilisateur from "../composants/AvatarUtilisateur.vue";
import { formaterPseudoAffichage } from "../formaterPseudo.js";
import { formaterDate, formaterHeureLocale } from "../dates.js";
import {
  chargerAccueil,
  chargerAnalyse,
  chargerStatsModele,
  chargerCommentairesMatch,
  chargerEquipesAnalyse,
  chargerPronosticMatch,
  chargerProchainsMatchs,
  chargerSondageMatch,
  chargerUtilisateurConnecte,
  deconnecterUtilisateur,
  deposerPronostic,
  publierCommentaireMatch,
  signalerCommentaireMatch,
  supprimerCommentaireMatch,
  basculerReactionCommentaire,
  voterSondageMatch,
} from "../services/api.js";
import { definirExtraNavigation, viderExtraNavigation } from "../contexteNavigation.js";
import ChargementPage from "../composants/ChargementPage.vue";
import BlocSondage from "../composants/BlocSondage.vue";

const route = useRoute();
const routeur = useRouter();

const championnats = ref([...CHAMPIONNATS_DEFAUT]);
const saisons = ref([]);
const equipes = ref([]);
const championnat = ref(route.query.championnat || "La Liga");
const saison = ref(route.query.saison || "");
const club = ref(route.query.equipe || route.query.domicile || "");
const domicile = ref(route.query.domicile || "");
const exterieur = ref(route.query.exterieur || "");
const data = ref(null);
const erreur = ref("");
const chargement = ref(false);
const matchsEquipe = ref([]);
const matchsLigue = ref([]);
const utilisateur = ref(null);
const commentaires = ref([]);
const nouveauCommentaire = ref("");
const erreurCommentaire = ref("");
const messageCommentaire = ref("");
const chargementCommentaires = ref(false);
const envoiCommentaire = ref(false);
const reponseParentId = ref(null);
const texteReponse = ref("");
const TYPES_REACTION = [
  { cle: "pouce", libelle: "👍" },
  { cle: "coeur", libelle: "❤️" },
];
const pronostic = ref(null);
const commenceAtMatch = ref("");
const matchDejaJoueProno = ref(false);
const typePronostic = ref("score");
const butsDomicileProno = ref(0);
const butsExterieurProno = ref(0);
const resultat1x2Prono = ref("1");
const erreurPronostic = ref("");
const messagePronostic = ref("");
const chargementPronostic = ref(false);
const envoiPronostic = ref(false);
const sondageMatch = ref(null);
const chargementSondage = ref(false);
const envoiSondageMatch = ref(false);
const erreurSondage = ref("");
const statsModele = ref(null);

async function chargerStatsPrecision() {
  if (!saison.value) return;
  try {
    statsModele.value = await chargerStatsModele(saison.value, championnat.value);
  } catch {
    statsModele.value = null;
  }
}

const metriquesPrecision = computed(() => {
  const bloc = statsModele.value;
  if (!bloc || !bloc.disponible) return null;
  const m = bloc.metriques || {};
  if (!m.nb_matchs) return null;
  return m;
});

function formaterPctPrecision(val) {
  if (val == null || val === "") return "—";
  return `${Number(val).toFixed(1).replace(".", ",")} %`;
}

function formaterNombrePrecision(val, decimales = 3) {
  if (val == null || val === "") return "—";
  return Number(val).toFixed(decimales).replace(".", ",");
}

async function chargerSaisons() {
  const meta = await chargerAccueil();
  saisons.value = meta.saisons;
  if (meta.championnats && meta.championnats.length) {
    championnats.value = meta.championnats.map((item) => item.nom);
  }
  if (!saison.value) {
    saison.value = meta.saisons[0] || "2026-2027";
  }
}

async function chargerListe() {
  if (!championnat.value || !saison.value) return;
  const liste = await chargerEquipesAnalyse(championnat.value, saison.value);
  equipes.value = liste.equipes || [];
  await chargerStatsPrecision();
}

async function chargerSuggestions() {
  if (!championnat.value || !saison.value) return;
  try {
    const resultat = await chargerProchainsMatchs(
      championnat.value,
      saison.value,
      club.value || "",
    );
    if (resultat.equipe && resultat.equipe !== club.value) {
      club.value = resultat.equipe;
    }
    matchsEquipe.value = resultat.matchs_equipe || [];
    matchsLigue.value = resultat.matchs_ligue || [];
  } catch (e) {
    matchsEquipe.value = [];
    matchsLigue.value = [];
  }
}

async function lancerAnalyse() {
  if (!domicile.value || !exterieur.value || domicile.value === exterieur.value) {
    data.value = null;
    return;
  }
  erreur.value = "";
  chargement.value = true;
  try {
    data.value = await chargerAnalyse(
      championnat.value,
      saison.value,
      domicile.value,
      exterieur.value,
    );
    await chargerCommentaires();
    await chargerPronostic();
    await chargerSondageCommunautaire();
    routeur.replace({
      path: "/match",
      query: {
        championnat: championnat.value,
        saison: saison.value,
        domicile: domicile.value,
        exterieur: exterieur.value,
        ...(club.value ? { equipe: club.value } : {}),
      },
    });
  } catch (e) {
    data.value = null;
    erreur.value = e.message;
  } finally {
    chargement.value = false;
  }
}

function choisirMatch(match) {
  domicile.value = match.domicile;
  exterieur.value = match.exterieur;
}

function choisirAncienMatch(match) {
  if (match.saison) {
    saison.value = match.saison;
  }
  domicile.value = match.domicile;
  exterieur.value = match.exterieur;
}

function surChoixClub() {
  data.value = null;
  domicile.value = "";
  exterieur.value = "";
  erreur.value = "";
  routeur.replace({
    path: "/match",
    query: {
      championnat: championnat.value,
      saison: saison.value,
      ...(club.value ? { equipe: club.value } : {}),
    },
  });
}

watch(
  () => [
    route.query.championnat,
    route.query.saison,
    route.query.domicile,
    route.query.exterieur,
    route.query.equipe,
  ],
  ([c, s, d, e, eq]) => {
    if (c) championnat.value = c;
    if (s) saison.value = s;
    domicile.value = d || "";
    exterieur.value = e || "";
    club.value = eq || d || "";
    if (!d || !e) data.value = null;
  },
);

watch([championnat, saison], async () => {
  await chargerListe();
  const noms = new Set(equipes.value.map((item) => item.equipe));
  if (domicile.value && !noms.has(domicile.value)) domicile.value = "";
  if (exterieur.value && !noms.has(exterieur.value)) exterieur.value = "";
  await chargerSuggestions();
  if (domicile.value && exterieur.value) {
    await lancerAnalyse();
  }
});

watch(club, () => {
  chargerSuggestions();
});

watch(
  [championnat, saison, club],
  () => {
    definirExtraNavigation({
      championnat: championnat.value,
      saison: saison.value,
      equipe: club.value,
    });
  },
  { immediate: true },
);

onUnmounted(viderExtraNavigation);

watch([domicile, exterieur], () => {
  if (domicile.value && exterieur.value && domicile.value !== exterieur.value) {
    lancerAnalyse();
  }
});

watch(utilisateur, () => {
  if (data.value) {
    chargerPronostic();
    chargerSondageCommunautaire();
  }
});

chargerSaisons().then(async () => {
  await chargerListe();
  await chargerSuggestions();
  await chargerSession();
  if (domicile.value && exterieur.value) {
    await lancerAnalyse();
  }
});

const pred = computed(() => (data.value && data.value.prediction) || {});
const suggestionsVisibles = computed(() => !data.value);
const matchJoue = computed(() => {
  const bloc = data.value && data.value.match_joue;
  return bloc && bloc.joue ? bloc : null;
});
const matchAVenir = computed(() => {
  const bloc = data.value && data.value.match_a_venir;
  return bloc || null;
});
const pronosticPossible = computed(() => {
  if (!utilisateur.value || matchJoue.value) return false;
  if (matchDejaJoueProno.value) return false;
  const instant = commenceAtMatch.value || (matchAVenir.value && matchAVenir.value.commence_at);
  if (!instant) return false;
  return new Date(instant).getTime() > Date.now();
});
const pronosticVerrouille = computed(() => {
  if (matchJoue.value || matchDejaJoueProno.value) return true;
  if (pronostic.value && pronostic.value.verrouille) return true;
  const instant = commenceAtMatch.value || (matchAVenir.value && matchAVenir.value.commence_at);
  if (!instant) return false;
  return new Date(instant).getTime() <= Date.now();
});
const confrontations = computed(() => (data.value && data.value.confrontations) || null);
const scenarios = computed(() => pred.value.scenarios || []);
const cartons = computed(() => pred.value.cartons || null);
const comparaisonPrevisions = computed(() => {
  const bloc = pred.value.comparaison;
  return bloc && bloc.lignes && bloc.lignes.length ? bloc.lignes : [];
});
const pointsBilan = computed(() => {
  const bloc = pred.value.bilan;
  return bloc && Array.isArray(bloc.points) ? bloc.points : [];
});
const previsionFigeeMeta = computed(() => {
  const bloc = data.value && data.value.prevision_figee;
  if (!bloc || !bloc.genere_le) return null;
  return bloc;
});
const labelPrevisionFigee = computed(() => {
  const meta = previsionFigeeMeta.value;
  if (!meta || !meta.genere_le) return "";
  const brut = String(meta.genere_le);
  const jour = brut.slice(0, 10);
  if (/^\d{4}-\d{2}-\d{2}$/.test(jour)) {
    const [y, m, d] = jour.split("-");
    return `Prévision enregistrée le ${d}/${m}/${y}`;
  }
  return `Prévision enregistrée le ${brut}`;
});
const recit = computed(() => pred.value.recit || []);
const lectureMarche = computed(() => {
  const bloc = data.value && data.value.lecture_marche;
  return bloc && bloc.disponible ? bloc : null;
});

function largeur(pct) {
  return { width: `${pct || 0}%` };
}

function formaterStatMatch(valeur, decimales = 0) {
  if (valeur == null || valeur === "") return "—";
  const nombre = Number(valeur);
  if (Number.isNaN(nombre)) return "—";
  if (decimales > 0) return nombre.toFixed(decimales).replace(".", ",");
  return String(Math.round(nombre));
}

function partsStatMatch(dom, ext) {
  const a = dom == null || dom === "" || Number.isNaN(Number(dom)) ? null : Number(dom);
  const b = ext == null || ext === "" || Number.isNaN(Number(ext)) ? null : Number(ext);
  if (a == null && b == null) return { dom: 50, ext: 50 };
  const va = a ?? 0;
  const vb = b ?? 0;
  const total = va + vb;
  if (total === 0) return { dom: 50, ext: 50 };
  return { dom: (va / total) * 100, ext: (vb / total) * 100 };
}

function styleBarreStat(dom, ext, cote) {
  const parts = partsStatMatch(dom, ext);
  const pct = cote === "dom" ? parts.dom : parts.ext;
  return { width: `${Math.max(pct, pct > 0 ? 6 : 0)}%` };
}

function construireLignesStats(source, definitions) {
  if (!source) return [];
  return definitions
    .map(({ libelle, cleDom, cleExt, decimales = 0 }) => ({
      libelle,
      dom: source[cleDom],
      ext: source[cleExt],
      decimales,
    }))
    .filter((ligne) => ligne.dom != null || ligne.ext != null);
}

const DEFINITIONS_STATS_JOUE = [
  { libelle: "Occasions (xG)", cleDom: "xg_domicile", cleExt: "xg_exterieur", decimales: 1 },
  { libelle: "Buts mi-temps", cleDom: "buts_domicile_mt", cleExt: "buts_exterieur_mt" },
  { libelle: "Tirs", cleDom: "tirs_domicile", cleExt: "tirs_exterieur" },
  { libelle: "Tirs cadrés", cleDom: "tirs_cadres_domicile", cleExt: "tirs_cadres_exterieur" },
  { libelle: "Corners", cleDom: "corners_domicile", cleExt: "corners_exterieur" },
  { libelle: "Fautes", cleDom: "fautes_domicile", cleExt: "fautes_exterieur" },
  { libelle: "Cartons jaunes", cleDom: "jaunes_domicile", cleExt: "jaunes_exterieur" },
  { libelle: "Cartons rouges", cleDom: "rouges_domicile", cleExt: "rouges_exterieur" },
];

const lignesStatsMatch = computed(() => construireLignesStats(matchJoue.value, DEFINITIONS_STATS_JOUE));

const lignesStatsPrevues = computed(() => {
  if (matchJoue.value) return [];
  const lignes = [];
  if (pred.value.xg_prevu_domicile != null && pred.value.xg_prevu_exterieur != null) {
    lignes.push({
      libelle: "Occasions prévues (xG)",
      dom: pred.value.xg_prevu_domicile,
      ext: pred.value.xg_prevu_exterieur,
      decimales: 1,
    });
  }
  if (cartons.value) {
    if (cartons.value.jaunes_domicile != null || cartons.value.jaunes_exterieur != null) {
      lignes.push({
        libelle: "Cartons jaunes prévus",
        dom: cartons.value.jaunes_domicile,
        ext: cartons.value.jaunes_exterieur,
        decimales: 1,
      });
    }
    if (cartons.value.rouges_domicile != null || cartons.value.rouges_exterieur != null) {
      lignes.push({
        libelle: "Cartons rouges prévus",
        dom: cartons.value.rouges_domicile,
        ext: cartons.value.rouges_exterieur,
        decimales: 2,
      });
    }
  }
  return lignes;
});

function texteCote(valeur) {
  if (valeur == null || valeur === "") return "—";
  const nombre = Number(valeur);
  if (Number.isNaN(nombre)) return "—";
  return nombre.toFixed(2).replace(".", ",");
}

function resumeCartons(forme) {
  if (!forme || !forme.nb_avec_cartons) return "";
  const jaunes = forme.jaunes ?? 0;
  const rouges = forme.rouges ?? 0;
  const motJaune = jaunes === 1 ? "jaune" : "jaunes";
  const motRouge = rouges === 1 ? "rouge" : "rouges";
  return `${jaunes} ${motJaune}, ${rouges} ${motRouge}`;
}

function lienConnexionMatch() {
  return {
    path: "/connexion",
    query: {
      retour: route.fullPath,
    },
  };
}

function formaterDateCommentaire(iso) {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString("fr-FR", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

async function chargerSession() {
  try {
    const reponse = await chargerUtilisateurConnecte();
    utilisateur.value = reponse.utilisateur;
  } catch {
    utilisateur.value = null;
  }
}

async function chargerCommentaires() {
  if (!domicile.value || !exterieur.value || domicile.value === exterieur.value) {
    commentaires.value = [];
    return;
  }
  chargementCommentaires.value = true;
  erreurCommentaire.value = "";
  try {
    const reponse = await chargerCommentairesMatch(
      championnat.value,
      saison.value,
      domicile.value,
      exterieur.value,
    );
    commentaires.value = reponse.commentaires || [];
  } catch (e) {
    commentaires.value = [];
    erreurCommentaire.value = e.message;
  } finally {
    chargementCommentaires.value = false;
  }
}

async function envoyerCommentaire() {
  erreurCommentaire.value = "";
  messageCommentaire.value = "";
  envoiCommentaire.value = true;
  try {
    await publierCommentaireMatch({
      championnat: championnat.value,
      saison: saison.value,
      domicile: domicile.value,
      exterieur: exterieur.value,
      contenu: nouveauCommentaire.value,
    });
    await chargerCommentaires();
    nouveauCommentaire.value = "";
    messageCommentaire.value = "Commentaire publié.";
  } catch (e) {
    erreurCommentaire.value = e.message;
  } finally {
    envoiCommentaire.value = false;
  }
}

function ouvrirReponse(id) {
  if (!utilisateur.value) return;
  reponseParentId.value = reponseParentId.value === id ? null : id;
  texteReponse.value = "";
}

async function envoyerReponse(parentId) {
  erreurCommentaire.value = "";
  messageCommentaire.value = "";
  envoiCommentaire.value = true;
  try {
    await publierCommentaireMatch({
      championnat: championnat.value,
      saison: saison.value,
      domicile: domicile.value,
      exterieur: exterieur.value,
      contenu: texteReponse.value,
      commentaire_parent_id: parentId,
    });
    reponseParentId.value = null;
    texteReponse.value = "";
    messageCommentaire.value = "Réponse publiée.";
    await chargerCommentaires();
  } catch (e) {
    erreurCommentaire.value = e.message;
  } finally {
    envoiCommentaire.value = false;
  }
}

function appliquerReactionsSiId(item, reponse) {
  if (item.id === reponse.commentaire_id) {
    return {
      ...item,
      reactions: reponse.reactions || item.reactions,
      mes_reactions: reponse.mes_reactions || [],
      nb_reactions: reponse.nb_reactions,
      utilisateur_a_reagi: reponse.utilisateur_a_reagi,
    };
  }
  return {
    ...item,
    reponses: (item.reponses || []).map((r) => appliquerReactionsSiId(r, reponse)),
  };
}

async function signalerCommentaire(id) {
  erreurCommentaire.value = "";
  messageCommentaire.value = "";
  try {
    await signalerCommentaireMatch(id);
    messageCommentaire.value = "Signalement envoyé. Merci.";
  } catch (e) {
    erreurCommentaire.value = e.message;
  }
}

async function supprimerCommentaire(id) {
  erreurCommentaire.value = "";
  messageCommentaire.value = "";
  try {
    await supprimerCommentaireMatch(id);
    await chargerCommentaires();
    messageCommentaire.value = "Commentaire supprimé.";
  } catch (e) {
    erreurCommentaire.value = e.message;
  }
}

async function basculerReaction(id, typeReaction = "pouce") {
  if (!utilisateur.value) return;
  erreurCommentaire.value = "";
  try {
    const reponse = await basculerReactionCommentaire(id, typeReaction);
    commentaires.value = commentaires.value.map((item) =>
      appliquerReactionsSiId(item, reponse),
    );
  } catch (e) {
    erreurCommentaire.value = e.message;
  }
}

function aReagi(item, typeReaction) {
  return (item.mes_reactions || []).includes(typeReaction);
}

function nbReaction(item, typeReaction) {
  return (item.reactions && item.reactions[typeReaction]) || 0;
}

async function chargerPronostic() {
  if (!domicile.value || !exterieur.value || domicile.value === exterieur.value) {
    pronostic.value = null;
    return;
  }
  commenceAtMatch.value = (matchAVenir.value && matchAVenir.value.commence_at) || "";
  matchDejaJoueProno.value = false;
  if (!utilisateur.value) {
    pronostic.value = null;
    return;
  }
  chargementPronostic.value = true;
  erreurPronostic.value = "";
  try {
    const reponse = await chargerPronosticMatch(
      championnat.value,
      saison.value,
      domicile.value,
      exterieur.value,
    );
    pronostic.value = reponse.pronostic;
    matchDejaJoueProno.value = Boolean(reponse.match_deja_joue);
    if (reponse.commence_at) {
      commenceAtMatch.value = reponse.commence_at;
    }
    if (pronostic.value) {
      typePronostic.value = pronostic.value.type_pronostic;
      if (pronostic.value.type_pronostic === "score") {
        butsDomicileProno.value = pronostic.value.buts_domicile ?? 0;
        butsExterieurProno.value = pronostic.value.buts_exterieur ?? 0;
      } else {
        resultat1x2Prono.value = pronostic.value.resultat_1x2 || "1";
      }
    }
  } catch (e) {
    pronostic.value = null;
    erreurPronostic.value = e.message;
  } finally {
    chargementPronostic.value = false;
  }
}

async function envoyerPronostic() {
  erreurPronostic.value = "";
  messagePronostic.value = "";
  envoiPronostic.value = true;
  try {
    const corps = {
      championnat: championnat.value,
      saison: saison.value,
      domicile: domicile.value,
      exterieur: exterieur.value,
      type_pronostic: typePronostic.value,
    };
    if (typePronostic.value === "score") {
      corps.buts_domicile = Number(butsDomicileProno.value);
      corps.buts_exterieur = Number(butsExterieurProno.value);
    } else {
      corps.resultat_1x2 = resultat1x2Prono.value;
    }
    const reponse = await deposerPronostic(corps);
    pronostic.value = reponse.pronostic;
    messagePronostic.value = pronostic.value.verrouille
      ? "Pronostic enregistré (verrouillé)."
      : "Pronostic enregistré.";
  } catch (e) {
    erreurPronostic.value = e.message;
  } finally {
    envoiPronostic.value = false;
  }
}

async function chargerSondageCommunautaire() {
  if (!domicile.value || !exterieur.value || domicile.value === exterieur.value) {
    sondageMatch.value = null;
    return;
  }
  chargementSondage.value = true;
  erreurSondage.value = "";
  try {
    const reponse = await chargerSondageMatch(
      championnat.value,
      saison.value,
      domicile.value,
      exterieur.value,
    );
    sondageMatch.value = reponse.sondage;
  } catch (e) {
    sondageMatch.value = null;
    erreurSondage.value = e.message;
  } finally {
    chargementSondage.value = false;
  }
}

async function voterSondageCommunautaire(choix) {
  if (!utilisateur.value) {
    erreurSondage.value = "Connectez-vous pour voter.";
    return;
  }
  envoiSondageMatch.value = true;
  erreurSondage.value = "";
  try {
    const reponse = await voterSondageMatch({
      championnat: championnat.value,
      saison: saison.value,
      domicile: domicile.value,
      exterieur: exterieur.value,
      choix,
    });
    sondageMatch.value = reponse.sondage;
  } catch (e) {
    erreurSondage.value = e.message;
  } finally {
    envoiSondageMatch.value = false;
  }
}

function libelleOptionSondage(option) {
  if (!data.value) return option.libelle;
  if (option.choix === "1") return `${data.value.domicile.nom} gagne`;
  if (option.choix === "2") return `${data.value.exterieur.nom} gagne`;
  return "Match nul";
}

const optionsSondageAffichees = computed(() => {
  if (!sondageMatch.value) return [];
  return (sondageMatch.value.options || []).map((option) => ({
    ...option,
    libelle: libelleOptionSondage(option),
  }));
});

async function seDeconnecter() {
  await deconnecterUtilisateur();
  utilisateur.value = null;
}
</script>

<template>
  <section class="hero hero-analyse">
    <div class="hero-inner">
      <header class="entete-analyse">
        <p class="sur-titre-analyse">Scénario statistique</p>
        <h1 class="titre-analyse">Analyse de match</h1>
        <p class="intro-analyse">
          Forces, faiblesses et scénario statistique — pas un pronostic de paris.
        </p>
      </header>

      <section class="filtres-analyse bloc-analyse-section bloc-analyse-section-hero" aria-label="Choisir un match">
        <h2 class="titre-section-analyse">Choisir un match</h2>
        <div class="rangee-filtres">
          <label class="champ-filtre">
            Championnat
            <select v-model="championnat">
              <option v-for="item in championnats" :key="item" :value="item">{{ item }}</option>
            </select>
          </label>
          <label class="champ-filtre">
            Saison
            <select v-model="saison">
              <option v-for="item in saisons" :key="item" :value="item">{{ item }}</option>
            </select>
          </label>
          <label class="champ-filtre champ-filtre-large">
            Club
            <select v-model="club" @change="surChoixClub">
              <option value="">Choisir un club…</option>
              <option v-for="item in equipes" :key="'c' + item.equipe" :value="item.equipe">
                {{ item.equipe }}
              </option>
            </select>
          </label>
        </div>

        <p class="separateur-filtres">Ou deux équipes au choix</p>

        <div class="rangee-filtres rangee-equipes">
          <label class="champ-filtre champ-filtre-large">
            Domicile
            <select v-model="domicile">
              <option value="">Choisir…</option>
              <option v-for="item in equipes" :key="'d' + item.equipe" :value="item.equipe">
                {{ item.equipe }}
              </option>
            </select>
          </label>
          <span class="versus-filtre" aria-hidden="true">contre</span>
          <label class="champ-filtre champ-filtre-large">
            Extérieur
            <select v-model="exterieur">
              <option value="">Choisir…</option>
              <option v-for="item in equipes" :key="'e' + item.equipe" :value="item.equipe">
                {{ item.equipe }}
              </option>
            </select>
          </label>
        </div>
      </section>
    </div>
  </section>

  <div class="page">
    <p v-if="erreur" class="erreur">{{ erreur }}</p>

    <section
      v-if="metriquesPrecision"
      class="bloc-analyse-section bloc-precision-modele"
      aria-label="Précision du modèle"
    >
      <h2 class="titre-section-analyse">Précision du modèle</h2>
      <p class="doux intro-section-analyse">
        {{ championnat }} — {{ saison }} · {{ metriquesPrecision.nb_matchs }} match(s) évalué(s)
      </p>
      <p class="doux note-precision-modele">
        Basé uniquement sur les prévisions figées avant le match (hors backfill rétroactif).
      </p>
      <div class="grille-precision-modele">
        <div class="carte-stat">
          <span>Issue 1X2</span>
          <strong>{{ formaterPctPrecision(metriquesPrecision.pct_issue_1x2) }}</strong>
        </div>
        <div class="carte-stat">
          <span>Score exact</span>
          <strong>{{ formaterPctPrecision(metriquesPrecision.pct_score_exact) }}</strong>
        </div>
        <div class="carte-stat">
          <span>Brier (moy.)</span>
          <strong>{{ formaterNombrePrecision(metriquesPrecision.brier_moyen, 4) }}</strong>
        </div>
        <div class="carte-stat">
          <span>MAE xG</span>
          <strong>{{ formaterNombrePrecision(metriquesPrecision.mae_xg_moyen, 2) }}</strong>
        </div>
        <div
          v-if="metriquesPrecision.pct_btts != null"
          class="carte-stat"
        >
          <span>BTTS</span>
          <strong>{{ formaterPctPrecision(metriquesPrecision.pct_btts) }}</strong>
        </div>
        <div
          v-if="metriquesPrecision.pct_o25 != null"
          class="carte-stat"
        >
          <span>Over 2,5</span>
          <strong>{{ formaterPctPrecision(metriquesPrecision.pct_o25) }}</strong>
        </div>
      </div>
    </section>

    <ChargementPage
      v-if="chargement"
      message="Calcul du scénario"
    />

    <template v-if="suggestionsVisibles">
      <section class="bloc-analyse-section" v-if="club">
        <h2 class="titre-section-analyse">Prochains matchs de {{ club }}</h2>
        <p v-if="!matchsEquipe.length" class="doux">
          Pas de match à venir pour {{ club }} en {{ saison }}.
        </p>
        <ul v-else class="liste-suggestions">
          <li v-for="match in matchsEquipe" :key="match.date + match.domicile + match.exterieur">
            <button type="button" class="suggestion-match" @click="choisirMatch(match)">
              <span class="suggestion-date">{{ formaterDate(match.date) }}</span>
              <span class="suggestion-heure">{{ formaterHeureLocale(match) }}</span>
              <span class="suggestion-lieu">{{ match.lieu }}</span>
              <span class="equipe-ligne">
                <img
                  v-if="match.lieu === 'Domicile' ? match.url_logo_exterieur : match.url_logo_domicile"
                  :src="match.lieu === 'Domicile' ? match.url_logo_exterieur : match.url_logo_domicile"
                  :alt="match.adversaire"
                  class="blason"
                />
                {{ match.adversaire }}
              </span>
            </button>
          </li>
        </ul>
      </section>
      <section class="bloc-analyse-section" v-else>
        <h2 class="titre-section-analyse">Par où commencer ?</h2>
        <p class="doux">Choisissez un club pour voir ses 8 prochains matchs, ou cliquez un match de la ligue.</p>
      </section>

      <section class="bloc-analyse-section" v-if="matchsLigue.length">
        <h2 class="titre-section-analyse">Prochaine journée</h2>
        <ul class="liste-suggestions">
          <li v-for="match in matchsLigue" :key="'l' + match.date + match.domicile + match.exterieur">
            <button type="button" class="suggestion-match" @click="choisirMatch(match)">
              <span class="suggestion-date">{{ formaterDate(match.date) }}</span>
              <span class="suggestion-heure">{{ formaterHeureLocale(match) }}</span>
              <span class="equipe-ligne">
                <img
                  v-if="match.url_logo_domicile"
                  :src="match.url_logo_domicile"
                  :alt="match.domicile"
                  class="blason"
                />
                {{ match.domicile }}
              </span>
              <span class="doux">–</span>
              <span class="equipe-ligne">
                <img
                  v-if="match.url_logo_exterieur"
                  :src="match.url_logo_exterieur"
                  :alt="match.exterieur"
                  class="blason"
                />
                {{ match.exterieur }}
              </span>
            </button>
          </li>
        </ul>
      </section>
    </template>

    <p v-else-if="domicile === exterieur" class="erreur">Choisissez deux équipes différentes.</p>

    <template v-if="data">
      <p class="mention">Saison des moyennes : {{ data.saison_ligue }}.</p>

      <section class="bloc-analyse-section" aria-label="Profils des équipes">
        <h2 class="titre-section-analyse">Profils des équipes</h2>
        <div class="grille-analyse">
        <article
          class="carte-equipe"
          v-for="(cote, rang) in [data.domicile, data.exterieur]"
          :key="cote.nom + rang"
        >
          <header class="entete-equipe">
            <img v-if="cote.url_logo" :src="cote.url_logo" :alt="cote.nom" class="blason-grand" />
            <div>
              <p class="tag">{{ rang === 0 ? "Domicile" : "Extérieur" }}</p>
              <h2>{{ cote.nom }}</h2>
              <p class="doux">
                xG {{ cote.saison_xg }} · {{ cote.nb_matchs_xg }} matchs
                {{ rang === 0 ? "à domicile" : "à l'extérieur" }}
              </p>
              <p class="forme">
                Forme {{ cote.forme.resume }}
                <span v-for="(lettre, i) in cote.forme.serie" :key="i" :class="'pastille pastille-' + lettre">
                  {{ lettre }}
                </span>
              </p>
              <p class="doux">
                5 derniers : {{ cote.forme.buts_pour }} buts pour,
                {{ cote.forme.buts_contre }} contre
                <template v-if="resumeCartons(cote.forme)">
                  · {{ resumeCartons(cote.forme) }}
                </template>
              </p>
              <p class="doux" v-if="cote.jaunes != null">
                Saison {{ cote.saison_xg }} :
                {{ cote.jaunes }} jaunes / match
                <template v-if="cote.rouges != null">
                  · {{ cote.rouges }} rouges / match
                </template>
              </p>
            </div>
          </header>
          <p class="chiffres-xg">
            <strong>{{ cote.xg_marques ?? "—" }}</strong> occasions créées (xG) ·
            <strong>{{ cote.xg_encaisses ?? "—" }}</strong> occasions concédées (xG)
          </p>
          <h3>Forces</h3>
          <ul class="liste-points">
            <li v-for="phrase in cote.forces" :key="phrase" class="point-force">{{ phrase }}</li>
          </ul>
          <h3>Faiblesses</h3>
          <ul class="liste-points">
            <li v-for="phrase in cote.faiblesses" :key="phrase" class="point-faiblesse">{{ phrase }}</li>
          </ul>
        </article>
        </div>
      </section>

      <section v-if="matchJoue" class="bloc-analyse-section" aria-label="Résultat du match">
        <h2 class="titre-section-analyse">Résultat du match</h2>
        <p class="doux date-resultat-match">{{ formaterDate(matchJoue.date) }}</p>

        <div class="entete-resultat-match">
          <div class="equipe-resultat equipe-resultat-dom">
            <img
              v-if="data.domicile.url_logo"
              :src="data.domicile.url_logo"
              :alt="data.domicile.nom"
              class="blason-resultat"
            />
            <span class="nom-equipe-resultat">{{ data.domicile.nom }}</span>
          </div>
          <p class="score-match-final" :aria-label="`Score final : ${matchJoue.buts_domicile} à ${matchJoue.buts_exterieur}`">
            <span class="score-chiffre">{{ matchJoue.buts_domicile }}</span>
            <span class="score-separateur" aria-hidden="true">–</span>
            <span class="score-chiffre">{{ matchJoue.buts_exterieur }}</span>
          </p>
          <div class="equipe-resultat equipe-resultat-ext">
            <span class="nom-equipe-resultat">{{ data.exterieur.nom }}</span>
            <img
              v-if="data.exterieur.url_logo"
              :src="data.exterieur.url_logo"
              :alt="data.exterieur.nom"
              class="blason-resultat"
            />
          </div>
        </div>

        <section
          v-if="lignesStatsMatch.length"
          class="stats-match"
          aria-label="Statistiques du match"
        >
          <div
            v-for="ligne in lignesStatsMatch"
            :key="ligne.libelle"
            class="ligne-stat-match"
          >
            <span class="valeur-stat valeur-stat-dom">
              {{ formaterStatMatch(ligne.dom, ligne.decimales) }}
            </span>
            <div class="centre-stat-match">
              <span class="libelle-stat-match">{{ ligne.libelle }}</span>
              <div
                class="barre-stat-match"
                role="img"
                :aria-label="`${ligne.libelle} : ${formaterStatMatch(ligne.dom, ligne.decimales)} contre ${formaterStatMatch(ligne.ext, ligne.decimales)}`"
              >
                <div class="seg-stat-dom" :style="styleBarreStat(ligne.dom, ligne.ext, 'dom')"></div>
                <div class="seg-stat-ext" :style="styleBarreStat(ligne.dom, ligne.ext, 'ext')"></div>
              </div>
            </div>
            <span class="valeur-stat valeur-stat-ext">
              {{ formaterStatMatch(ligne.ext, ligne.decimales) }}
            </span>
          </div>
        </section>
        <p v-else class="doux">Statistiques détaillées indisponibles pour ce match.</p>
      </section>

      <section
        v-if="comparaisonPrevisions.length"
        class="bloc-analyse-section"
        aria-label="Prévisions vs réalité"
      >
        <h2 class="titre-section-analyse">Prévisions vs réalité</h2>
        <div class="comparaison-previsions-reel">
          <div class="enveloppe-tableau">
            <table class="table-comparaison-previsions">
              <thead>
                <tr>
                  <th>Statistique</th>
                  <th class="droit">Dom. prévu</th>
                  <th class="droit">Dom. réel</th>
                  <th class="droit">Ext. prévu</th>
                  <th class="droit">Ext. réel</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="ligne in comparaisonPrevisions" :key="ligne.statistique">
                  <th scope="row">{{ ligne.statistique }}</th>
                  <td class="droit">{{ formaterStatMatch(ligne.prevu_domicile, ligne.decimales) }}</td>
                  <td class="droit">{{ formaterStatMatch(ligne.reel_domicile, ligne.decimales) }}</td>
                  <td class="droit">{{ formaterStatMatch(ligne.prevu_exterieur, ligne.decimales) }}</td>
                  <td class="droit">{{ formaterStatMatch(ligne.reel_exterieur, ligne.decimales) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <section class="bloc-analyse-section" aria-label="Résumé du scénario">
        <h2 class="titre-section-analyse">
          {{ matchJoue ? "Ce qui était prévu" : "Résumé du scénario" }}
        </h2>
        <p v-if="labelPrevisionFigee" class="badge-prevision-figee">{{ labelPrevisionFigee }}</p>
        <p v-if="pred.phrase_elo" class="doux phrase-elo-analyse">{{ pred.phrase_elo }}</p>
        <p class="doux" v-if="pred.texte">{{ pred.texte }}</p>

        <div
          v-if="pointsBilan.length"
          class="bilan-analyse"
          aria-label="Bilan de la prévision"
        >
          <h3>Bilan</h3>
          <ul>
            <li v-for="(point, index) in pointsBilan" :key="index">{{ point }}</li>
          </ul>
        </div>

        <div class="resume-analyse resume-analyse-compact" aria-label="Score le plus probable">
          <div class="cartes-stats cartes-stats-resume">
            <div class="carte-stat carte-stat-large">
              <span>Score le plus probable</span>
              <strong>{{ pred.score_plus_probable }}</strong>
            </div>
          </div>
        </div>
      </section>

      <section class="bloc-analyse-section" aria-label="Probabilités">
        <h2 class="titre-section-analyse">Probabilités</h2>
        <div class="bloc-1n2">
          <div class="ligne-1n2">
            <span>{{ data.domicile.nom }} {{ pred.p_victoire_domicile }} %</span>
            <span>Nul {{ pred.p_nul }} %</span>
            <span>{{ data.exterieur.nom }} {{ pred.p_victoire_exterieur }} %</span>
          </div>
          <div class="barre-1n2" role="img" :aria-label="'Probabilités 1N2'">
            <div class="seg-1" :style="largeur(pred.p_victoire_domicile)"></div>
            <div class="seg-n" :style="largeur(pred.p_nul)"></div>
            <div class="seg-2" :style="largeur(pred.p_victoire_exterieur)"></div>
          </div>
        </div>
        <div class="cartes-stats grille-probabilites">
          <div class="carte-stat">
            <span>Les deux marquent</span>
            <strong>{{ pred.p_les_deux_marquent }} %</strong>
          </div>
          <div class="carte-stat">
            <span>Plus de 2 buts</span>
            <strong>{{ pred.p_plus_de_2_buts }} %</strong>
          </div>
          <template v-if="cartons">
            <div class="carte-stat">
              <span>Jaunes prévus</span>
              <strong>{{ cartons.jaunes_match }}</strong>
              <p class="doux petit">
                {{ cartons.jaunes_domicile }} – {{ cartons.jaunes_exterieur }}
                (moy. ligue {{ cartons.moyenne_championnat }})
              </p>
            </div>
            <div class="carte-stat">
              <span>Rouges prévus</span>
              <strong>{{ cartons.rouges_match }}</strong>
              <p class="doux petit">
                au moins un rouge : {{ cartons.p_au_moins_un_rouge }} %
              </p>
            </div>
          </template>
        </div>
      </section>

      <section
        v-if="lignesStatsPrevues.length"
        class="bloc-analyse-section"
        aria-label="Statistiques prévues"
      >
        <h2 class="titre-section-analyse">Statistiques comparatives prévues</h2>
        <div
          class="stats-match stats-match-prevues"
          aria-label="Statistiques prévues"
        >
          <div
            v-for="ligne in lignesStatsPrevues"
            :key="ligne.libelle"
            class="ligne-stat-match ligne-stat-prevue"
          >
            <span class="valeur-stat valeur-stat-dom">
              {{ formaterStatMatch(ligne.dom, ligne.decimales) }}
            </span>
            <div class="centre-stat-match">
              <span class="libelle-stat-match">{{ ligne.libelle }}</span>
              <div
                class="barre-stat-match"
                role="img"
                :aria-label="`${ligne.libelle} : ${formaterStatMatch(ligne.dom, ligne.decimales)} contre ${formaterStatMatch(ligne.ext, ligne.decimales)}`"
              >
                <div class="seg-stat-dom" :style="styleBarreStat(ligne.dom, ligne.ext, 'dom')"></div>
                <div class="seg-stat-ext" :style="styleBarreStat(ligne.dom, ligne.ext, 'ext')"></div>
              </div>
              <div class="legendes-xg-prevu">
                <span>{{ data.domicile.nom }}</span>
                <span>{{ data.exterieur.nom }}</span>
              </div>
            </div>
            <span class="valeur-stat valeur-stat-ext">
              {{ formaterStatMatch(ligne.ext, ligne.decimales) }}
            </span>
          </div>
        </div>
      </section>

      <section
        v-if="recit.length || lectureMarche"
        class="bloc-analyse-section"
        aria-label="Analyse narrative"
      >
        <h2 class="titre-section-analyse">Lecture du match</h2>
        <div class="grille-scenario grille-scenario-recit">
          <div class="colonne-scenario">
            <div class="bloc-recit" v-if="recit.length">
              <h3>Le récit du match</h3>
              <p v-for="(paragraphe, i) in recit" :key="'r' + i">{{ paragraphe }}</p>
            </div>
            <div class="bloc-recit lecture-marche" v-if="lectureMarche">
              <h3>Lecture du marché</h3>
              <div class="ligne-cotes" v-if="lectureMarche.cotes">
                <span class="puce-cote">
                  <em>1</em>{{ texteCote(lectureMarche.cotes.domicile) }}
                </span>
                <span class="puce-cote">
                  <em>N</em>{{ texteCote(lectureMarche.cotes.nul) }}
                </span>
                <span class="puce-cote">
                  <em>2</em>{{ texteCote(lectureMarche.cotes.exterieur) }}
                </span>
              </div>
              <p>{{ lectureMarche.texte }}</p>
            </div>
          </div>
        </div>
      </section>

      <section
        v-if="scenarios.length"
        class="bloc-analyse-section"
        aria-label="Scénarios possibles"
      >
        <h2 class="titre-section-analyse">Comment le match peut tourner</h2>
        <ul class="liste-scenarios">
          <li v-for="item in scenarios" :key="item.cle" class="carte-scenario-detail">
            <h4>{{ item.titre }}</h4>
            <p>{{ item.texte }}</p>
            <p class="doux petit" v-if="item.chiffre">{{ item.chiffre }}</p>
            <p class="doux petit" v-else-if="item.pct != null">{{ item.pct }} %</p>
          </li>
        </ul>
      </section>

      <section
        v-if="pred.scores_frequents && pred.scores_frequents.length"
        class="bloc-analyse-section"
        aria-label="Scores les plus fréquents"
      >
        <h2 class="titre-section-analyse">Scores les plus probables</h2>
        <ul class="liste-scores">
          <li v-for="item in pred.scores_frequents" :key="item.score">
            <div class="ligne-score-pct">
              <span class="score-gros">{{ item.score }}</span>
              <span class="doux">{{ item.pct }} %</span>
            </div>
            <span class="commentaire-score" v-if="item.commentaire">{{ item.commentaire }}</span>
          </li>
        </ul>
      </section>

      <section class="bloc-analyse-section" v-if="confrontations" aria-label="Confrontations directes">
        <h2 class="titre-section-analyse">Confrontations directes</h2>
        <p v-if="!confrontations.nb" class="doux">
          Pas encore de match entre ces deux clubs dans cette compétition.
        </p>
        <template v-else>
          <div class="ligne-1n2">
            <span>{{ data.domicile.nom }} {{ confrontations.victoires_domicile }}</span>
            <span>Nuls {{ confrontations.nuls }}</span>
            <span>{{ data.exterieur.nom }} {{ confrontations.victoires_exterieur }}</span>
          </div>
          <ul class="liste-suggestions">
            <li
              v-for="match in confrontations.matchs"
              :key="match.date + match.domicile + match.exterieur"
            >
              <button type="button" class="suggestion-match" @click="choisirAncienMatch(match)">
                <span class="suggestion-date">{{ formaterDate(match.date) }}</span>
                <span class="doux">{{ match.saison }}</span>
                <span>{{ match.domicile }}</span>
                <span class="score-gros">{{ match.score }}</span>
                <span>{{ match.exterieur }}</span>
              </button>
            </li>
          </ul>
        </template>
      </section>

      <section class="bloc-analyse-section zone-communaute" aria-label="Pronostic et communauté">
        <h2 class="titre-section-analyse">Pronostic &amp; communauté</h2>
      <div class="bloc bloc-pronostics" v-if="data && utilisateur">
        <header class="entete-bloc">
          <h3 class="titre-sous-section-communaute">Mon pronostic privé</h3>
        </header>

        <p v-if="chargementPronostic" class="doux">Chargement du pronostic…</p>
        <p v-if="erreurPronostic" class="erreur">{{ erreurPronostic }}</p>
        <p v-if="messagePronostic" class="message-ok">{{ messagePronostic }}</p>

        <div v-if="pronosticVerrouille && pronostic" class="carte-prono-existant">
          <p class="doux">Votre pronostic (verrouillé)</p>
          <p class="score-gros">{{ pronostic.libelle }}</p>
          <p class="doux petit">
            {{ pronostic.type_pronostic === "score" ? "Score exact" : "1X2" }}
            · déposé le {{ formaterDateCommentaire(pronostic.cree_le) }}
          </p>
          <p v-if="pronostic.evaluation" class="doux">
            Score réel : {{ pronostic.evaluation.score_reel }}
            —
            <strong :class="pronostic.evaluation.exact ? 'texte-exact' : 'texte-rate'">
              {{ pronostic.evaluation.exact ? "Exact" : "Raté" }}
            </strong>
          </p>
        </div>

        <p v-else-if="matchJoue || matchDejaJoueProno" class="doux">
          Match terminé — pronostic non disponible.
        </p>

        <p v-else-if="!matchAVenir && !commenceAtMatch" class="doux">
          Horaire du match inconnu — pronostic indisponible pour l'instant.
        </p>

        <form
          v-else-if="pronosticPossible"
          class="formulaire-pronostic"
          @submit.prevent="envoyerPronostic"
        >
          <fieldset class="groupe-type-prono">
            <legend class="doux">Type de pronostic</legend>
            <label class="case-a-cocher">
              <input v-model="typePronostic" type="radio" value="score" />
              Score exact
            </label>
            <label class="case-a-cocher">
              <input v-model="typePronostic" type="radio" value="1x2" />
              Résultat 1X2
            </label>
          </fieldset>

          <div v-if="typePronostic === 'score'" class="rangee-score-prono">
            <label class="champ-filtre">
              {{ data.domicile.nom }}
              <input
                v-model.number="butsDomicileProno"
                type="number"
                min="0"
                max="15"
                required
              />
            </label>
            <span class="versus-filtre" aria-hidden="true">–</span>
            <label class="champ-filtre">
              {{ data.exterieur.nom }}
              <input
                v-model.number="butsExterieurProno"
                type="number"
                min="0"
                max="15"
                required
              />
            </label>
          </div>

          <div v-else class="groupe-1x2">
            <label class="case-a-cocher">
              <input v-model="resultat1x2Prono" type="radio" value="1" />
              {{ data.domicile.nom }} gagne
            </label>
            <label class="case-a-cocher">
              <input v-model="resultat1x2Prono" type="radio" value="N" />
              Match nul
            </label>
            <label class="case-a-cocher">
              <input v-model="resultat1x2Prono" type="radio" value="2" />
              {{ data.exterieur.nom }} gagne
            </label>
          </div>

          <p v-if="pronostic && !pronosticVerrouille" class="doux">
            Vous pouvez modifier votre pronostic avant le coup d'envoi.
          </p>

          <button type="submit" class="bouton-principal" :disabled="envoiPronostic">
            {{ envoiPronostic ? "Enregistrement…" : pronostic ? "Mettre à jour" : "Déposer mon pronostic" }}
          </button>
        </form>

        <p v-else-if="pronosticVerrouille && !pronostic" class="doux">
          Coup d'envoi passé — dépôt de pronostic fermé.
        </p>

        <p class="doux">
          <router-link to="/mes-pronos">Voir tous nos pronostics</router-link>
        </p>
      </div>

      <div class="bloc bloc-pronostics" v-else-if="data && !utilisateur && !matchJoue">
        <header class="entete-bloc">
          <h3 class="titre-sous-section-communaute">Mon pronostic privé</h3>
        </header>
        <p class="doux">
          <router-link :to="lienConnexionMatch()">Connectez-vous</router-link>
          pour déposer un pronostic privé avant le coup d'envoi.
        </p>
      </div>

      <div class="bloc bloc-sondage-match" v-if="data">
        <header class="entete-bloc">
          <h3 class="titre-sous-section-communaute">Sondage du match</h3>
        </header>
        <p v-if="chargementSondage" class="doux">Chargement du sondage…</p>
        <p v-if="erreurSondage" class="erreur">{{ erreurSondage }}</p>
        <BlocSondage
          v-if="sondageMatch"
          :question="sondageMatch.question"
          :options="optionsSondageAffichees"
          :a-vote="sondageMatch.a_vote"
          :mon-cle="sondageMatch.mon_choix"
          :nb-votes-total="sondageMatch.nb_votes_total"
          :connecte="Boolean(utilisateur)"
          :envoi="envoiSondageMatch"
          :disclaimer="sondageMatch.disclaimer || ''"
          cle-option="choix"
          @voter="voterSondageCommunautaire"
        />
        <p class="doux petit">
          Distinct de votre pronostic privé — un avis rapide 1 / N / 2.
        </p>
      </div>

      <div class="bloc bloc-commentaires" v-if="data">
        <header class="entete-bloc">
          <h3 class="titre-sous-section-communaute">Commentaires</h3>
        </header>

        <p v-if="chargementCommentaires" class="doux">Chargement des commentaires…</p>
        <p v-if="erreurCommentaire" class="erreur">{{ erreurCommentaire }}</p>
        <p v-if="messageCommentaire" class="message-ok">{{ messageCommentaire }}</p>

        <ul v-if="commentaires.length" class="liste-commentaires">
          <li v-for="item in commentaires" :key="item.id" class="carte-commentaire">
            <header class="entete-commentaire">
              <span class="auteur-commentaire">
                <AvatarUtilisateur
                  :pseudo="item.pseudo"
                  :avatar-id="item.avatar_id"
                  :taille="28"
                />
                <strong>{{ formaterPseudoAffichage(item.pseudo) }}</strong>
              </span>
              <time class="doux petit">{{ formaterDateCommentaire(item.cree_le) }}</time>
            </header>
            <p class="texte-commentaire">{{ item.contenu }}</p>
            <div class="actions-commentaire">
              <button
                v-for="typeR in TYPES_REACTION"
                :key="typeR.cle"
                type="button"
                class="bouton-reaction"
                :class="{ actif: aReagi(item, typeR.cle) }"
                :disabled="!utilisateur"
                :title="
                  utilisateur
                    ? aReagi(item, typeR.cle)
                      ? 'Retirer la réaction'
                      : `Réagir ${typeR.libelle}`
                    : 'Connectez-vous pour réagir'
                "
                @click="basculerReaction(item.id, typeR.cle)"
              >
                <span aria-hidden="true">{{ typeR.libelle }}</span>
                <span class="compteur-reaction">{{ nbReaction(item, typeR.cle) }}</span>
              </button>
              <button
                v-if="utilisateur"
                type="button"
                class="lien-action"
                @click="ouvrirReponse(item.id)"
              >
                {{ reponseParentId === item.id ? "Annuler" : "Répondre" }}
              </button>
              <button
                v-if="utilisateur"
                type="button"
                class="lien-action"
                @click="signalerCommentaire(item.id)"
              >
                Signaler
              </button>
              <button
                v-if="utilisateur && utilisateur.est_admin"
                type="button"
                class="lien-action lien-danger"
                @click="supprimerCommentaire(item.id)"
              >
                Supprimer
              </button>
            </div>

            <form
              v-if="reponseParentId === item.id"
              class="formulaire-reponse"
              @submit.prevent="envoyerReponse(item.id)"
            >
              <label class="champ-filtre">
                Votre réponse
                <textarea
                  v-model="texteReponse"
                  rows="2"
                  maxlength="500"
                  required
                  placeholder="Votre réponse…"
                ></textarea>
              </label>
              <button type="submit" class="bouton-principal" :disabled="envoiCommentaire">
                {{ envoiCommentaire ? "Envoi…" : "Publier la réponse" }}
              </button>
            </form>

            <ul v-if="item.reponses?.length" class="liste-reponses">
              <li
                v-for="reponse in item.reponses"
                :key="reponse.id"
                class="carte-commentaire carte-reponse"
              >
                <header class="entete-commentaire">
                  <span class="auteur-commentaire">
                    <AvatarUtilisateur
                      :pseudo="reponse.pseudo"
                      :avatar-id="reponse.avatar_id"
                      :taille="24"
                    />
                    <strong>{{ formaterPseudoAffichage(reponse.pseudo) }}</strong>
                  </span>
                  <time class="doux petit">{{ formaterDateCommentaire(reponse.cree_le) }}</time>
                </header>
                <p class="texte-commentaire">{{ reponse.contenu }}</p>
                <div class="actions-commentaire">
                  <button
                    v-for="typeR in TYPES_REACTION"
                    :key="typeR.cle"
                    type="button"
                    class="bouton-reaction"
                    :class="{ actif: aReagi(reponse, typeR.cle) }"
                    :disabled="!utilisateur"
                    @click="basculerReaction(reponse.id, typeR.cle)"
                  >
                    <span aria-hidden="true">{{ typeR.libelle }}</span>
                    <span class="compteur-reaction">{{ nbReaction(reponse, typeR.cle) }}</span>
                  </button>
                  <button
                    v-if="utilisateur"
                    type="button"
                    class="lien-action"
                    @click="signalerCommentaire(reponse.id)"
                  >
                    Signaler
                  </button>
                  <button
                    v-if="utilisateur && utilisateur.est_admin"
                    type="button"
                    class="lien-action lien-danger"
                    @click="supprimerCommentaire(reponse.id)"
                  >
                    Supprimer
                  </button>
                </div>
              </li>
            </ul>
          </li>
        </ul>
        <p v-else-if="!chargementCommentaires" class="doux message-vide-communaute">
          Aucun commentaire pour ce match. Soyez le premier à réagir.
        </p>

        <form
          v-if="utilisateur"
          class="formulaire-commentaire"
          @submit.prevent="envoyerCommentaire"
        >
          <label class="champ-filtre">
            Votre commentaire
            <textarea
              v-model="nouveauCommentaire"
              rows="3"
              maxlength="500"
              required
              placeholder="Partagez votre lecture du match…"
            ></textarea>
          </label>
          <button type="submit" class="bouton-principal" :disabled="envoiCommentaire">
            {{ envoiCommentaire ? "Envoi…" : "Publier" }}
          </button>
        </form>

        <p v-else class="doux">
          <router-link :to="lienConnexionMatch()">Connectez-vous</router-link>
          pour commenter, ou
          <router-link to="/inscription">créez un compte</router-link>.
        </p>

        <p v-if="utilisateur" class="doux session-utilisateur">
          Connecté en tant que <strong>{{ formaterPseudoAffichage(utilisateur.pseudo) }}</strong>
          <button type="button" class="lien-action" @click="seDeconnecter">Se déconnecter</button>
        </p>
      </div>
      </section>

      <section class="bloc-analyse-section" v-if="matchsEquipe.length" aria-label="Autres matchs">
        <h2 class="titre-section-analyse">Autres matchs de {{ club || domicile }}</h2>
        <ul class="liste-suggestions">
          <li v-for="match in matchsEquipe" :key="'a' + match.date + match.domicile + match.exterieur">
            <button type="button" class="suggestion-match" @click="choisirMatch(match)">
              <span class="suggestion-date">{{ formaterDate(match.date) }}</span>
              <span class="suggestion-lieu">{{ match.lieu }}</span>
              <span>{{ match.adversaire }}</span>
            </button>
          </li>
        </ul>
      </section>
    </template>
  </div>
</template>
