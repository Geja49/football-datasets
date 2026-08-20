<script setup>
import { ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { rechercher } from "./services/api.js";
import { appliquerTheme, nomTheme } from "./themes.js";

const route = useRoute();
const routeur = useRouter();
const terme = ref("");
const resultats = ref(null);
let delai = null;

watch(
  () => nomTheme(route),
  (nom) => appliquerTheme(nom),
  { immediate: true },
);

function surSaisie() {
  clearTimeout(delai);
  if (terme.value.trim().length < 2) {
    resultats.value = null;
    return;
  }
  delai = setTimeout(async () => {
    resultats.value = await rechercher(terme.value.trim());
  }, 250);
}

function allerJoueur(nom) {
  resultats.value = null;
  terme.value = "";
  routeur.push(`/joueur/${encodeURIComponent(nom)}`);
}

function allerEquipe(item) {
  resultats.value = null;
  terme.value = "";
  routeur.push({
    path: `/championnat/${encodeURIComponent(item.championnat)}/equipe/${encodeURIComponent(item.equipe)}`,
    query: { saison: item.saison },
  });
}
</script>

<template>
  <header class="bandeau">
    <router-link class="logo" to="/">Stats foot</router-link>
    <router-link
      class="lien-analyse"
      :to="{
        path: '/match',
        query: route.params.championnat
          ? { championnat: route.params.championnat, saison: route.query.saison }
          : {},
      }"
    >
      Analyser un match
    </router-link>
    <div>
      <input
        class="recherche"
        v-model="terme"
        placeholder="Joueur, club…"
        @input="surSaisie"
      />
      <div class="resultats" v-if="resultats">
        <a
          v-for="joueur in resultats.joueurs"
          :key="joueur.joueur + joueur.saison"
          href="#"
          @click.prevent="allerJoueur(joueur.joueur)"
        >
          {{ joueur.joueur }} — {{ joueur.equipe }} ({{ joueur.saison }})
        </a>
        <a
          v-for="equipe in resultats.equipes"
          :key="equipe.equipe + equipe.saison"
          href="#"
          @click.prevent="allerEquipe(equipe)"
        >
          {{ equipe.equipe }} — {{ equipe.championnat }}
        </a>
      </div>
    </div>
  </header>
  <main class="contenu">
    <router-view />
  </main>
</template>
