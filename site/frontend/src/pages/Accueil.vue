<script setup>
import { onMounted, ref } from "vue";
import { chargerAccueil } from "../services/api.js";

const championnats = ref([]);
const saisons = ref([]);
const saison = ref("");
const erreur = ref("");

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
  } catch (e) {
    erreur.value = e.message;
  }
});
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
  </div>
</template>
