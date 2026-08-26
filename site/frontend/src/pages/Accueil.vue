<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import {
  CLASSES_CARTES,
  CODES_CARTES,
  LOGOS_CARTES,
  libelleTypeCompetition,
} from "../championnats.js";
import PortraitJoueur from "../composants/PortraitJoueur.vue";
import { aujourdhuiIso, formaterDate, formaterHeureLocale } from "../dates.js";
import { chargerAccueil, chargerMatchsSansProno, chargerUtilisateurConnecte } from "../services/api.js";

defineOptions({ name: "Accueil" });

const routeur = useRouter();
const championnats = ref([]);
const saisons = ref([]);
const saison = ref("");
const jour = ref("");
const matchsJour = ref([]);
const buteurs = ref([]);
const passeurs = ref([]);
const erreur = ref("");
const utilisateur = ref(null);
const nbMatchsSansProno = ref(0);
const aujourd = aujourdhuiIso();

const classesCartes = CLASSES_CARTES;
const codesCartes = CODES_CARTES;
const logosCartes = LOGOS_CARTES;

function libelleType(nom) {
  return libelleTypeCompetition(nom);
}

onMounted(async () => {
  try {
    const data = await chargerAccueil();
    championnats.value = data.championnats;
    saisons.value = data.saisons;
    saison.value = data.saisons[0] || "";
    jour.value = data.jour || "";
    matchsJour.value = data.matchs_jour || [];
    buteurs.value = data.buteurs || [];
    passeurs.value = data.passeurs || [];
  } catch (e) {
    erreur.value = e.message;
  }
  try {
    const session = await chargerUtilisateurConnecte();
    utilisateur.value = session.utilisateur;
    const rappels = await chargerMatchsSansProno();
    nbMatchsSansProno.value = rappels.nb || 0;
  } catch {
    utilisateur.value = null;
    nbMatchsSansProno.value = 0;
  }
});

function score(match) {
  if (!match.joue) return "";
  if (match.buts_domicile == null || match.buts_exterieur == null) return "";
  return `${match.buts_domicile} – ${match.buts_exterieur}`;
}

function ouvrirMatch(match) {
  routeur.push({
    path: "/match",
    query: {
      championnat: match.championnat,
      saison: match.saison,
      domicile: match.domicile,
      exterieur: match.exterieur,
    },
  });
}

function ouvrirJoueur(nom, ligue) {
  routeur.push({
    path: `/joueur/${encodeURIComponent(nom)}`,
    query: { championnat: ligue },
  });
}
</script>

<template>
  <section class="hero">
    <div class="hero-inner">
      <p class="tag">Saison {{ saison }}</p>
      <h1 class="titre-hero">Championnats et Ligue des champions</h1>
        <p class="doux">Classement, calendrier et analyse de match.</p>
      <div class="ligne-haut" style="margin-top: 18px">
        <label>
          Saison
          <select v-model="saison">
            <option v-for="item in saisons" :key="item" :value="item">{{ item }}</option>
          </select>
        </label>
      </div>
    </div>
  </section>
  <div class="page">
    <p v-if="erreur" class="erreur">{{ erreur }}</p>

    <aside
      v-if="utilisateur && nbMatchsSansProno > 0"
      class="bandeau-rappel-pronos"
      role="status"
    >
      <p>
        <strong>{{ nbMatchsSansProno }}</strong>
        match{{ nbMatchsSansProno > 1 ? "s" : "" }} à pronostiquer dans les 7 prochains jours.
        <router-link to="/mes-pronos">Voir nos pronos</router-link>
      </p>
    </aside>

    <section class="bloc-competitions" aria-label="Compétitions">
      <header class="entete-competitions">
        <p class="tag-section">Compétitions</p>
        <h2 class="titre-section-competitions">Choisir une ligue</h2>
      </header>
      <div class="grille grille-competitions">
        <router-link
          v-for="champ in championnats"
          :key="champ.nom"
          class="tuile-competition cliquable"
          :class="classesCartes[champ.nom]"
          :to="{ path: `/championnat/${encodeURIComponent(champ.nom)}`, query: { saison } }"
        >
          <img
            v-if="logosCartes[champ.nom]"
            class="logo-championnat"
            :src="logosCartes[champ.nom]"
            alt=""
            width="88"
            height="88"
            loading="lazy"
            aria-hidden="true"
          />
          <span v-else class="tuile-code" aria-hidden="true">{{ codesCartes[champ.nom] || "" }}</span>
          <div class="tuile-contenu">
            <p class="tag">{{ libelleType(champ.nom) }}</p>
            <h2 class="tuile-titre">{{ champ.nom }}</h2>
            <p class="tuile-action">Classement + calendrier</p>
          </div>
        </router-link>
      </div>
    </section>

    <div class="bloc bloc-matchs-jour" v-if="jour">
      <header class="entete-matchs-jour">
        <p class="tag-section">Calendrier</p>
        <h2 class="titre-section-matchs">
          {{ jour === aujourd ? "Matchs du jour" : "Prochains matchs" }}
        </h2>
        <p v-if="jour !== aujourd" class="doux">{{ formaterDate(jour) }}</p>
      </header>
      <p v-if="!matchsJour.length" class="doux">Aucun match à cette date.</p>
      <div class="liste-matchs-jour">
      <article
        v-for="match in matchsJour"
        :key="match.championnat + match.domicile + match.exterieur"
        class="carte-match"
        :class="match.joue ? 'match-joue' : 'match-avenir'"
        @click="ouvrirMatch(match)"
      >
        <div class="heure-match">
          {{ formaterHeureLocale(match) }}
        </div>
        <div class="club-match club-domicile">
          <span>{{ match.domicile }}</span>
          <img
            v-if="match.url_logo_domicile"
            :src="match.url_logo_domicile"
            :alt="match.domicile"
            class="blason"
          />
        </div>
        <div class="milieu-match">
          <strong v-if="match.joue" class="score-match">{{ score(match) }}</strong>
          <template v-else>
            <strong class="versus">vs</strong>
            <button
              type="button"
              class="bouton-analyse bouton-analyse-milieu"
              @click.stop="ouvrirMatch(match)"
            >
              Analyser
            </button>
          </template>
          <small class="ligue-match">{{ match.championnat }}</small>
        </div>
        <div class="club-match club-exterieur">
          <img
            v-if="match.url_logo_exterieur"
            :src="match.url_logo_exterieur"
            :alt="match.exterieur"
            class="blason"
          />
          <span>{{ match.exterieur }}</span>
        </div>
      </article>
      </div>
    </div>

    <section class="bloc bloc-buteurs" v-if="buteurs.length" aria-label="Meilleurs buteurs">
      <header class="entete-buteurs">
        <p class="tag-section">Statistiques</p>
        <h2 class="titre-section-buteurs">Meilleurs buteurs</h2>
      </header>
      <div class="grille grille-buteurs">
        <router-link
          v-for="ligue in buteurs"
          :key="ligue.championnat"
          class="carte carte-buteur cliquable"
          :class="classesCartes[ligue.championnat]"
          :to="{
            path: `/championnat/${encodeURIComponent(ligue.championnat)}`,
            query: {
              ...(ligue.saison ? { saison: ligue.saison } : {}),
              onglet: 'buteurs',
            },
          }"
        >
          <div class="carte-buteur-entete">
            <p class="tag carte-buteur-ligue">{{ ligue.championnat }}</p>
            <p class="carte-buteur-saison">{{ ligue.saison || "Pas encore de stats" }}</p>
          </div>
          <ol v-if="ligue.joueurs.length" class="liste-buteurs">
            <li
              v-for="(joueur, rang) in ligue.joueurs"
              :key="joueur.joueur"
              @click.prevent.stop="ouvrirJoueur(joueur.joueur, ligue.championnat)"
            >
              <span class="rang-buteur" aria-hidden="true">{{ rang + 1 }}</span>
              <span class="joueur-cellule">
                <PortraitJoueur
                  :nom="joueur.joueur"
                  :url-photo="joueur.url_photo"
                  classe-css="portrait-buteur"
                />
                <span class="nom-buteur">{{ joueur.joueur }}</span>
              </span>
              <span class="buteurs-buts">{{ joueur.buts }}</span>
            </li>
          </ol>
          <p v-else class="carte-buteur-vide">Pas encore de stats.</p>
        </router-link>
      </div>
    </section>

    <section class="bloc bloc-passeurs" v-if="passeurs.length" aria-label="Meilleurs passeurs">
      <header class="entete-passeurs">
        <p class="tag-section">Statistiques</p>
        <h2 class="titre-section-passeurs">Meilleurs passeurs</h2>
      </header>
      <div class="grille grille-passeurs">
        <router-link
          v-for="ligue in passeurs"
          :key="ligue.championnat"
          class="carte carte-passeur cliquable"
          :class="classesCartes[ligue.championnat]"
          :to="{
            path: `/championnat/${encodeURIComponent(ligue.championnat)}`,
            query: {
              ...(ligue.saison ? { saison: ligue.saison } : {}),
              onglet: 'passeurs',
            },
          }"
        >
          <div class="carte-passeur-entete">
            <p class="tag carte-passeur-ligue">{{ ligue.championnat }}</p>
            <p class="carte-passeur-saison">{{ ligue.saison || "Pas encore de stats" }}</p>
          </div>
          <ol v-if="ligue.joueurs.length" class="liste-passeurs">
            <li
              v-for="(joueur, rang) in ligue.joueurs"
              :key="joueur.joueur"
              @click.prevent.stop="ouvrirJoueur(joueur.joueur, ligue.championnat)"
            >
              <span class="rang-passeur" aria-hidden="true">{{ rang + 1 }}</span>
              <span class="joueur-cellule">
                <PortraitJoueur
                  :nom="joueur.joueur"
                  :url-photo="joueur.url_photo"
                  classe-css="portrait-passeur"
                />
                <span class="nom-passeur">{{ joueur.joueur }}</span>
              </span>
              <span class="passeurs-pd">{{ joueur.passes_decisives }}</span>
            </li>
          </ol>
          <p v-else class="carte-passeur-vide">Pas encore de stats.</p>
        </router-link>
      </div>
    </section>
  </div>
</template>
