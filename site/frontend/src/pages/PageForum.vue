<script setup>
import { onMounted, ref } from "vue";
import { CLASSES_CARTES, LOGOS_CARTES } from "../championnats.js";
import ChargementPage from "../composants/ChargementPage.vue";
import { chargerEspacesForum } from "../services/api.js";

const espaces = ref([]);
const erreur = ref("");
const chargement = ref(true);

onMounted(async () => {
  try {
    const reponse = await chargerEspacesForum();
    espaces.value = reponse.espaces || [];
  } catch (e) {
    erreur.value = e.message;
  } finally {
    chargement.value = false;
  }
});
</script>

<template>
  <section class="hero hero-analyse">
    <div class="hero-inner">
      <header class="entete-analyse">
        <p class="sur-titre-analyse">Communauté</p>
        <h1 class="titre-analyse">Forum</h1>
        <p class="intro-analyse">
          Discutez par championnat — lecture libre, connexion requise pour poster.
        </p>
      </header>
    </div>
  </section>

  <div class="page page-forum">
    <p v-if="erreur" class="erreur">{{ erreur }}</p>
    <ChargementPage v-if="chargement" message="Chargement du forum" />

    <ul v-else class="liste-espaces-forum">
      <li v-for="espace in espaces" :key="espace.championnat">
        <router-link
          class="carte-espace-forum"
          :class="CLASSES_CARTES[espace.championnat]"
          :to="`/forum/${encodeURIComponent(espace.championnat)}`"
        >
          <img
            v-if="LOGOS_CARTES[espace.championnat]"
            class="logo-espace-forum"
            :src="LOGOS_CARTES[espace.championnat]"
            :alt="espace.championnat"
            width="40"
            height="40"
          />
          <div class="texte-espace-forum">
            <strong>{{ espace.championnat }}</strong>
            <span class="doux petit">
              {{ espace.nb_sujets }}
              sujet{{ espace.nb_sujets > 1 ? "s" : "" }}
            </span>
          </div>
        </router-link>
      </li>
    </ul>
  </div>
</template>
