import { createRouter, createWebHistory } from "vue-router";
import Accueil from "./pages/Accueil.vue";
import PageAnalyse from "./pages/PageAnalyse.vue";
import PageChampionnat from "./pages/PageChampionnat.vue";
import PageEquipe from "./pages/PageEquipe.vue";
import PageJoueur from "./pages/PageJoueur.vue";

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: Accueil },
    { path: "/match", component: PageAnalyse },
    { path: "/championnat/:championnat", component: PageChampionnat },
    {
      path: "/championnat/:championnat/equipe/:equipe",
      component: PageEquipe,
    },
    { path: "/joueur/:joueur", component: PageJoueur },
  ],
});
