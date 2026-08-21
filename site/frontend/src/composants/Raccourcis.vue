<script setup>
import { computed } from "vue";
import { useRoute } from "vue-router";
import { lireContexteRoute } from "../contexteNavigation.js";

const route = useRoute();

const liens = computed(() => {
  const ctx = lireContexteRoute(route);
  const querySaison = ctx.saison ? { saison: ctx.saison } : {};
  const liste = [];

  if (ctx.championnat) {
    liste.push({
      libelle: "Championnat",
      to: {
        path: `/championnat/${encodeURIComponent(ctx.championnat)}`,
        query: { ...querySaison, vue: "classement" },
      },
    });
  }

  if (ctx.championnat && ctx.equipe) {
    liste.push({
      libelle: "Équipe",
      to: {
        path: `/championnat/${encodeURIComponent(ctx.championnat)}/equipe/${encodeURIComponent(ctx.equipe)}`,
        query: querySaison,
      },
    });
  }

  if (ctx.championnat) {
    liste.push({
      libelle: "Calendrier",
      to: {
        path: `/championnat/${encodeURIComponent(ctx.championnat)}`,
        query: { ...querySaison, vue: "calendrier" },
      },
    });
    liste.push({
      libelle: "Classement",
      to: {
        path: `/championnat/${encodeURIComponent(ctx.championnat)}`,
        query: { ...querySaison, vue: "classement" },
      },
    });
  }

  liste.push({
    libelle: "Analyse",
    to: {
      path: "/match",
      query: {
        ...(ctx.championnat ? { championnat: ctx.championnat } : {}),
        ...querySaison,
        ...(ctx.equipe ? { equipe: ctx.equipe, domicile: ctx.equipe } : {}),
      },
    },
  });

  liste.push({ libelle: "Recherche", action: "recherche" });
  return liste;
});

function allerRecherche() {
  const champ = document.getElementById("champ-recherche");
  if (champ) champ.focus();
}

function estActif(lien) {
  if (!lien.to) return false;
  const path = typeof lien.to === "string" ? lien.to : lien.to.path;
  if (route.path !== path) return false;
  const vue = typeof lien.to === "object" ? lien.to.query && lien.to.query.vue : "";
  if (vue) {
    return (route.query.vue || "classement") === vue;
  }
  return true;
}
</script>

<template>
  <nav class="raccourcis" aria-label="Raccourcis">
    <template v-for="lien in liens" :key="lien.libelle">
      <button
        v-if="lien.action === 'recherche'"
        type="button"
        class="puce-raccourci"
        @click="allerRecherche"
      >
        Recherche
      </button>
      <router-link
        v-else
        class="puce-raccourci"
        :class="{ actif: estActif(lien) }"
        :to="lien.to"
      >
        {{ lien.libelle }}
      </router-link>
    </template>
  </nav>
</template>
