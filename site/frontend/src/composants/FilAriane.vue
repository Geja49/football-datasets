<script setup>
import { computed } from "vue";
import { useRoute } from "vue-router";
import { lireContexteRoute } from "../contexteNavigation.js";

const route = useRoute();

const miettes = computed(() => {
  const ctx = lireContexteRoute(route);
  const liste = [{ libelle: "Accueil", to: "/" }];
  const querySaison = ctx.saison ? { saison: ctx.saison } : {};

  if (ctx.championnat) {
    liste.push({
      libelle: ctx.championnat,
      to: {
        path: `/championnat/${encodeURIComponent(ctx.championnat)}`,
        query: querySaison,
      },
    });
  }

  if (ctx.championnat && ctx.equipe && route.path !== "/cotes") {
    liste.push({
      libelle: ctx.equipe,
      to: {
        path: `/championnat/${encodeURIComponent(ctx.championnat)}/equipe/${encodeURIComponent(ctx.equipe)}`,
        query: querySaison,
      },
    });
  }

  if (String(route.path).endsWith("/analyser")) {
    liste.push({ libelle: "Choisir un match", to: null });
  }

  if (route.path === "/match") {
    liste.push({ libelle: "Analyse", to: null });
  }

  if (route.path === "/cotes") {
    liste.push({ libelle: "Cotes", to: null });
  }

  if (ctx.joueur) {
    liste.push({ libelle: ctx.joueur, to: null });
  }

  return liste;
});
</script>

<template>
  <nav class="fil-ariane" aria-label="Fil d'Ariane">
    <template v-for="(miette, index) in miettes" :key="miette.libelle + index">
      <span v-if="index > 0" class="separateur-ariane" aria-hidden="true">/</span>
      <span v-if="index === miettes.length - 1" class="actuel" aria-current="page">
        {{ miette.libelle }}
      </span>
      <router-link v-else-if="miette.to" :to="miette.to">
        {{ miette.libelle }}
      </router-link>
      <span v-else>{{ miette.libelle }}</span>
    </template>
  </nav>
</template>
