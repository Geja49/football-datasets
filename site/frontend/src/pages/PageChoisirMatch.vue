<script setup>
import { computed, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { definirExtraNavigation, viderExtraNavigation } from "../contexteNavigation.js";
import { formaterDate } from "../dates.js";
import { chargerEquipe } from "../services/api.js";

const route = useRoute();
const routeur = useRouter();
const championnat = computed(() => route.params.championnat);
const equipe = computed(() => route.params.equipe);
const saison = computed(() => route.query.saison || "2026-2027");
const nomEquipe = ref("");
const matchs = ref([]);
const erreur = ref("");
const chargement = ref(false);

async function charger() {
  erreur.value = "";
  chargement.value = true;
  try {
    const data = await chargerEquipe(championnat.value, saison.value, equipe.value);
    nomEquipe.value = data.equipe || equipe.value;
    matchs.value = data.matchs || [];
  } catch (e) {
    erreur.value = e.message;
    nomEquipe.value = equipe.value;
    matchs.value = [];
  } finally {
    chargement.value = false;
  }
}

watch(
  [championnat, equipe, saison],
  () => {
    definirExtraNavigation({
      championnat: championnat.value,
      equipe: equipe.value,
      saison: saison.value,
    });
    charger();
  },
  { immediate: true },
);

onUnmounted(viderExtraNavigation);

function estCetteEquipe(nom) {
  return nom === equipe.value || nom === nomEquipe.value;
}

const aVenir = computed(() => matchs.value.filter((match) => !match.joue));
const joues = computed(() =>
  matchs.value
    .filter((match) => match.joue)
    .slice()
    .reverse()
    .slice(0, 10),
);

function lieu(match) {
  return estCetteEquipe(match.domicile) ? "Domicile" : "Extérieur";
}

function adversaire(match) {
  return estCetteEquipe(match.domicile) ? match.exterieur : match.domicile;
}

function logoAdversaire(match) {
  return estCetteEquipe(match.domicile)
    ? match.url_logo_exterieur
    : match.url_logo_domicile;
}

function score(match) {
  if (!match.joue) return "";
  if (match.buts_domicile == null || match.buts_exterieur == null) return "";
  return `${match.buts_domicile} – ${match.buts_exterieur}`;
}

function ouvrirAnalyse(match) {
  routeur.push({
    path: "/match",
    query: {
      championnat: championnat.value,
      saison: saison.value,
      equipe: nomEquipe.value || equipe.value,
      domicile: match.domicile,
      exterieur: match.exterieur,
      date: match.date,
    },
  });
}

const lienEquipe = computed(() => ({
  path: `/championnat/${encodeURIComponent(championnat.value)}/equipe/${encodeURIComponent(equipe.value)}`,
  query: { saison: saison.value },
}));
</script>

<template>
  <section class="hero">
    <div class="hero-inner">
      <h1 class="titre-hero">Choisir un match — {{ nomEquipe || equipe }}</h1>
      <p class="doux">{{ championnat }} · {{ saison }}</p>
      <p class="doux">Cliquez un match pour ouvrir l’analyse.</p>
      <router-link class="bouton-analyse" :to="lienEquipe">Retour à la fiche</router-link>
    </div>
  </section>
  <div class="page">
    <p v-if="erreur" class="erreur">{{ erreur }}</p>
    <p v-else-if="chargement" class="doux">Chargement du calendrier…</p>
    <p v-else-if="!matchs.length" class="doux">
      Pas encore de matchs pour {{ nomEquipe || equipe }} en {{ saison }}.
    </p>

    <template v-else>
      <div class="bloc">
        <h2>À venir</h2>
        <p v-if="!aVenir.length" class="doux">
          Pas de match programmé pour {{ nomEquipe || equipe }} en {{ saison }}.
        </p>
        <ul v-else class="liste-suggestions">
          <li
            v-for="match in aVenir"
            :key="'a' + match.date + match.domicile + match.exterieur"
          >
            <button type="button" class="suggestion-match" @click="ouvrirAnalyse(match)">
              <span class="suggestion-date">{{ formaterDate(match.date) }}</span>
              <span class="suggestion-heure">{{ match.heure || "—" }}</span>
              <span class="suggestion-lieu">{{ lieu(match) }}</span>
              <span class="equipe-ligne">
                <img
                  v-if="logoAdversaire(match)"
                  :src="logoAdversaire(match)"
                  :alt="adversaire(match)"
                  class="blason"
                />
                {{ adversaire(match) }}
              </span>
            </button>
          </li>
        </ul>
      </div>

      <div class="bloc" v-if="joues.length">
        <h2>Matchs récents</h2>
        <ul class="liste-suggestions">
          <li
            v-for="match in joues"
            :key="'j' + match.date + match.domicile + match.exterieur"
          >
            <button type="button" class="suggestion-match" @click="ouvrirAnalyse(match)">
              <span class="suggestion-date">{{ formaterDate(match.date) }}</span>
              <span class="suggestion-heure">{{ score(match) || "FT" }}</span>
              <span class="suggestion-lieu">{{ lieu(match) }}</span>
              <span class="equipe-ligne">
                <img
                  v-if="logoAdversaire(match)"
                  :src="logoAdversaire(match)"
                  :alt="adversaire(match)"
                  class="blason"
                />
                {{ adversaire(match) }}
              </span>
            </button>
          </li>
        </ul>
      </div>
    </template>
  </div>
</template>
