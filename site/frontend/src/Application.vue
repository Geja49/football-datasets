<script setup>
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import FilAriane from "./composants/FilAriane.vue";
import Raccourcis from "./composants/Raccourcis.vue";
import { extraNavigation } from "./contexteNavigation.js";
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

const championnatActif = computed(
  () =>
    route.params.championnat ||
    route.query.championnat ||
    extraNavigation.championnat ||
    "",
);
const saisonActive = computed(
  () => route.query.saison || extraNavigation.saison || "",
);

const lienAnalyse = computed(() => ({
  path: "/match",
  query: championnatActif.value
    ? {
        championnat: championnatActif.value,
        ...(saisonActive.value ? { saison: saisonActive.value } : {}),
      }
    : {},
}));

const lienCalendrier = computed(() => {
  if (!championnatActif.value) return "/";
  return {
    path: `/championnat/${encodeURIComponent(championnatActif.value)}`,
    query: {
      ...(saisonActive.value ? { saison: saisonActive.value } : {}),
      vue: "calendrier",
    },
  };
});

const lienCotes = computed(() => ({
  path: "/cotes",
  query: championnatActif.value ? { championnat: championnatActif.value } : {},
}));

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
  <div class="entete-site">
    <header class="bandeau">
      <router-link class="logo" to="/">Stats foot</router-link>
      <nav class="nav-bandeau" aria-label="Navigation principale">
        <router-link class="lien-nav" to="/" :class="{ actif: route.path === '/' }">
          Ligues
        </router-link>
        <router-link
          class="lien-nav"
          :to="lienAnalyse"
          :class="{ actif: route.path === '/match' }"
        >
          Analyser
        </router-link>
        <router-link
          class="lien-nav"
          :to="lienCalendrier"
          :class="{ actif: route.query.vue === 'calendrier' }"
        >
          Calendrier
        </router-link>
        <router-link
          class="lien-nav"
          :to="lienCotes"
          :class="{ actif: route.path === '/cotes' }"
        >
          Cotes
        </router-link>
      </nav>
      <div class="boite-recherche">
        <svg
          class="icone-recherche"
          viewBox="0 0 24 24"
          width="18"
          height="18"
          aria-hidden="true"
        >
          <circle
            cx="11"
            cy="11"
            r="7"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          />
          <path
            d="M20 20l-4-4"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
          />
        </svg>
        <input
          id="champ-recherche"
          class="recherche"
          v-model="terme"
          placeholder="Joueur, club…"
          aria-label="Rechercher un joueur ou un club"
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
    <div class="barre-navigation">
      <FilAriane />
      <Raccourcis />
    </div>
  </div>
  <main class="contenu">
    <router-view />
  </main>
</template>
