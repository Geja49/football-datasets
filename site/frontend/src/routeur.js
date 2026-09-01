import { createRouter, createWebHistory } from "vue-router";

const Accueil = () => import("./pages/Accueil.vue");
const PageAnalyse = () => import("./pages/PageAnalyse.vue");
const PageChampionnat = () => import("./pages/PageChampionnat.vue");
const PageChoisirMatch = () => import("./pages/PageChoisirMatch.vue");
const PageComparer = () => import("./pages/PageComparer.vue");
const PageConditions = () => import("./pages/PageConditions.vue");
const PageAuthAnimee = () => import("./pages/PageAuthAnimee.vue");
const PageCotes = () => import("./pages/PageCotes.vue");
const PageEquipe = () => import("./pages/PageEquipe.vue");
const PageGlossaire = () => import("./pages/PageGlossaire.vue");
const PageJoueur = () => import("./pages/PageJoueur.vue");
const PageMesPronos = () => import("./pages/PageMesPronos.vue");
const PageClassementPronos = () => import("./pages/PageClassementPronos.vue");
const PagePronosJournee = () => import("./pages/PagePronosJournee.vue");
const PageLigues = () => import("./pages/PageLigues.vue");
const PageForum = () => import("./pages/PageForum.vue");
const PageForumChampionnat = () => import("./pages/PageForumChampionnat.vue");
const PageForumSujet = () => import("./pages/PageForumSujet.vue");
const PageNotifications = () => import("./pages/PageNotifications.vue");
const PageMonProfil = () => import("./pages/PageMonProfil.vue");
const PageModeration = () => import("./pages/PageModeration.vue");
const PageSolo = () => import("./pages/PageSolo.vue");
const PageBilanPronos = () => import("./pages/PageBilanPronos.vue");
const PageIntrouvable = () => import("./pages/PageIntrouvable.vue");

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: Accueil },
    { path: "/cotes", component: PageCotes },
    { path: "/match", component: PageAnalyse },
    { path: "/connexion", component: PageAuthAnimee },
    { path: "/inscription", component: PageAuthAnimee },
    { path: "/mes-pronos", component: PageMesPronos },
    { path: "/nos-pronos", redirect: "/mes-pronos" },
    { path: "/classement-pronos", component: PageClassementPronos },
    { path: "/pronos-journee", component: PagePronosJournee },
    { path: "/ligues", component: PageLigues },
    { path: "/ligue/:code", component: PageLigues },
    { path: "/notifications", component: PageNotifications },
    { path: "/mon-profil", component: PageMonProfil },
    { path: "/moderation", component: PageModeration },
    { path: "/solo", component: PageSolo },
    { path: "/bilan-pronos", component: PageBilanPronos },
    { path: "/forum", component: PageForum },
    { path: "/forum/sujet/:id", component: PageForumSujet },
    { path: "/forum/:championnat", component: PageForumChampionnat },
    { path: "/conditions", component: PageConditions },
    { path: "/glossaire", component: PageGlossaire },
    { path: "/comparer", component: PageComparer },
    { path: "/championnat/:championnat", component: PageChampionnat },
    {
      path: "/championnat/:championnat/equipe/:equipe/analyser",
      component: PageChoisirMatch,
    },
    {
      path: "/championnat/:championnat/equipe/:equipe",
      component: PageEquipe,
    },
    { path: "/joueur/:joueur", component: PageJoueur },
    { path: "/:pathMatch(.*)*", name: "introuvable", component: PageIntrouvable },
  ],
});
