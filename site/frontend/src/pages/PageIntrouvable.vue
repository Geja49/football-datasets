<script setup>
import { useRoute, useRouter } from "vue-router";

const route = useRoute();
const routeur = useRouter();
</script>

<template>
  <section class="hero hero-compact">
    <div class="hero-inner">
      <p class="sur-titre-analyse">Erreur 404</p>
      <h1 class="titre-analyse">Page introuvable</h1>
      <p class="intro-analyse">
        L'adresse <code class="code-chemin">{{ route.fullPath }}</code> n'existe pas ou a été déplacée.
      </p>
    </div>
  </section>

  <div class="page page-etroite page-introuvable">
    <p class="doux">
      Retournez à l'accueil pour parcourir les championnats, ou utilisez la barre de recherche en haut de page.
    </p>
    <div class="actions-introuvable">
      <button type="button" class="bouton-principal" @click="routeur.push('/')">
        Accueil
      </button>
      <button type="button" class="bouton-secondaire" @click="routeur.back()">
        Page précédente
      </button>
    </div>
  </div>
</template>
