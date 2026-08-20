<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { aujourdhuiIso, formaterDate } from "../dates.js";
import { chargerAccueil } from "../services/api.js";

const routeur = useRouter();
const championnats = ref([]);
const saisons = ref([]);
const saison = ref("");
const jour = ref("");
const matchsJour = ref([]);
const buteurs = ref([]);
const erreur = ref("");
const aujourd = aujourdhuiIso();

const classesCartes = {
  "Premier League": "carte-pl",
  "La Liga": "carte-laliga",
  Bundesliga: "carte-bundesliga",
  "Serie A": "carte-seriea",
  "Ligue 1": "carte-ligue1",
  "Ligue des champions": "carte-ldc",
};

onMounted(async () => {
  try {
    const data = await chargerAccueil();
    championnats.value = data.championnats;
    saisons.value = data.saisons;
    saison.value = data.saisons[0] || "";
    jour.value = data.jour || "";
    matchsJour.value = data.matchs_jour || [];
    buteurs.value = data.buteurs || [];
  } catch (e) {
    erreur.value = e.message;
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
    <div class="grille">
      <router-link
        v-for="champ in championnats"
        :key="champ.nom"
        class="carte cliquable"
        :class="classesCartes[champ.nom]"
        :to="{ path: `/championnat/${encodeURIComponent(champ.nom)}`, query: { saison } }"
      >
        <p class="tag">{{ champ.nom === "Ligue des champions" ? "Coupe d'Europe" : "Championnat" }}</p>
        <h2>{{ champ.nom }}</h2>
        <p class="doux">Classement + calendrier</p>
      </router-link>
    </div>

    <div class="bloc" v-if="jour">
      <h2>{{ jour === aujourd ? "Matchs du jour" : "Prochains matchs" }}</h2>
      <p v-if="jour !== aujourd" class="doux">{{ formaterDate(jour) }}</p>
      <p v-if="!matchsJour.length" class="doux">Aucun match à cette date.</p>
      <article
        v-for="match in matchsJour"
        :key="match.championnat + match.domicile + match.exterieur"
        class="carte-match"
        :class="match.joue ? 'match-joue' : 'match-avenir'"
        @click="ouvrirMatch(match)"
      >
        <div class="heure-match">
          {{ match.heure || (match.joue ? "FT" : "—") }}
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
          <strong v-else class="versus">vs</strong>
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

    <div class="bloc" v-if="buteurs.length">
      <h2>Meilleurs buteurs</h2>
      <div class="grille">
        <div
          v-for="ligue in buteurs"
          :key="ligue.championnat"
          class="carte"
          :class="classesCartes[ligue.championnat]"
        >
          <p class="tag">{{ ligue.championnat }}</p>
          <p class="doux">{{ ligue.saison }}</p>
          <ol class="liste-buteurs">
            <li
              v-for="joueur in ligue.joueurs"
              :key="joueur.joueur"
              @click="ouvrirJoueur(joueur.joueur, ligue.championnat)"
            >
              <span class="joueur-cellule">
                <img
                  v-if="joueur.url_photo"
                  :src="joueur.url_photo"
                  :alt="joueur.joueur"
                  class="portrait-mini"
                />
                {{ joueur.joueur }}
              </span>
              <span class="buteurs-buts">{{ joueur.buts }}</span>
            </li>
          </ol>
          <p v-if="!ligue.joueurs.length" class="doux">Pas encore de stats.</p>
        </div>
      </div>
    </div>
  </div>
</template>
