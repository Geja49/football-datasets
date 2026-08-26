<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import FilAriane from "./composants/FilAriane.vue";
import MentionJeuResponsable from "./composants/MentionJeuResponsable.vue";
import Raccourcis from "./composants/Raccourcis.vue";
import { extraNavigation } from "./contexteNavigation.js";
import { chargerUtilisateurConnecte, chargerMatchsSansProno, deconnecterUtilisateur, rechercher } from "./services/api.js";
import { appliquerTheme, nomTheme } from "./themes.js";

const route = useRoute();
const routeur = useRouter();
const terme = ref("");
const resultats = ref(null);
const utilisateur = ref(null);
const nbMatchsSansProno = ref(0);
/** @type {import('vue').Ref<'stats' | 'communaute' | 'compte' | null>} */
const menuOuvert = ref(null);
let delai = null;

async function chargerRappelsPronos() {
  if (!utilisateur.value) {
    nbMatchsSansProno.value = 0;
    return;
  }
  try {
    const reponse = await chargerMatchsSansProno();
    nbMatchsSansProno.value = reponse.nb || 0;
  } catch {
    nbMatchsSansProno.value = 0;
  }
}

function fermerMenus() {
  menuOuvert.value = null;
}

function basculerMenu(id) {
  menuOuvert.value = menuOuvert.value === id ? null : id;
}

function surClicDocument(evenement) {
  if (!(evenement.target instanceof Element)) return;
  if (!evenement.target.closest(".nav-groupe")) {
    fermerMenus();
  }
}

function surToucheDocument(evenement) {
  if (evenement.key === "Escape" && menuOuvert.value) {
    const id = menuOuvert.value;
    fermerMenus();
    document.getElementById(`bouton-nav-${id}`)?.focus();
  }
}

function surToucheBoutonMenu(evenement, id) {
  if (evenement.key === "ArrowDown") {
    evenement.preventDefault();
    if (menuOuvert.value !== id) basculerMenu(id);
    requestAnimationFrame(() => {
      document
        .querySelector(`#menu-nav-${id} [role="menuitem"]`)
        ?.focus();
    });
  }
}

onMounted(async () => {
  document.addEventListener("click", surClicDocument);
  document.addEventListener("keydown", surToucheDocument);
  try {
    const reponse = await chargerUtilisateurConnecte();
    utilisateur.value = reponse.utilisateur;
    await chargerRappelsPronos();
  } catch {
    utilisateur.value = null;
    nbMatchsSansProno.value = 0;
  }
});

onUnmounted(() => {
  document.removeEventListener("click", surClicDocument);
  document.removeEventListener("keydown", surToucheDocument);
});

async function seDeconnecter() {
  fermerMenus();
  await deconnecterUtilisateur();
  utilisateur.value = null;
  nbMatchsSansProno.value = 0;
  if (route.path === "/match") {
    routeur.go(0);
  }
}

watch(
  () => nomTheme(route),
  (nom) => appliquerTheme(nom),
  { immediate: true },
);

watch(
  () => [route.path, route.query],
  () => fermerMenus(),
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
      onglet: "calendrier",
    },
  };
});

const lienCotes = computed(() => ({
  path: "/cotes",
  query: championnatActif.value ? { championnat: championnatActif.value } : {},
}));

const statsActif = computed(
  () =>
    route.path === "/" ||
    route.path === "/match" ||
    route.path === "/comparer" ||
    route.path === "/cotes" ||
    route.query.onglet === "calendrier",
);

const communauteActif = computed(
  () =>
    route.path === "/classement-pronos" ||
    route.path === "/pronos-journee" ||
    route.path === "/mes-pronos" ||
    route.path === "/nos-pronos" ||
    route.path === "/ligues" ||
    route.path.startsWith("/ligue/"),
);

const compteActif = computed(
  () => route.path === "/connexion" || route.path === "/inscription",
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
  <div class="entete-site">
    <header class="bandeau">
      <router-link class="logo" to="/" aria-label="Stats Foot — Accueil">
        <img
          class="logo-marque"
          src="/logo-stats-foot.png"
          alt="Stats Foot"
          width="220"
          height="48"
        />
      </router-link>
      <nav class="nav-bandeau" aria-label="Navigation principale">
        <div
          class="nav-groupe"
          :class="{ ouvert: menuOuvert === 'stats' }"
        >
          <button
            id="bouton-nav-stats"
            type="button"
            class="bouton-nav-groupe"
            :class="{ actif: statsActif }"
            :aria-expanded="menuOuvert === 'stats'"
            aria-haspopup="true"
            aria-controls="menu-nav-stats"
            @click.stop="basculerMenu('stats')"
            @keydown="surToucheBoutonMenu($event, 'stats')"
          >
            Stats
            <span class="fleche-nav" aria-hidden="true">▾</span>
          </button>
          <div
            v-show="menuOuvert === 'stats'"
            id="menu-nav-stats"
            class="menu-nav-deroulant"
            role="menu"
            aria-labelledby="bouton-nav-stats"
            @click.stop
          >
            <router-link
              class="lien-menu-nav"
              role="menuitem"
              to="/"
              :class="{ actif: route.path === '/' }"
            >
              Ligues
            </router-link>
            <router-link
              class="lien-menu-nav"
              role="menuitem"
              :to="lienAnalyse"
              :class="{ actif: route.path === '/match' }"
            >
              Analyser
            </router-link>
            <router-link
              class="lien-menu-nav"
              role="menuitem"
              to="/comparer"
              :class="{ actif: route.path === '/comparer' }"
            >
              Comparer
            </router-link>
            <router-link
              class="lien-menu-nav"
              role="menuitem"
              :to="lienCalendrier"
              :class="{ actif: route.query.onglet === 'calendrier' }"
            >
              Calendrier
            </router-link>
            <router-link
              class="lien-menu-nav"
              role="menuitem"
              :to="lienCotes"
              :class="{ actif: route.path === '/cotes' }"
            >
              Cotes
            </router-link>
          </div>
        </div>

        <div
          class="nav-groupe"
          :class="{ ouvert: menuOuvert === 'communaute' }"
        >
          <button
            id="bouton-nav-communaute"
            type="button"
            class="bouton-nav-groupe"
            :class="{ actif: communauteActif }"
            :aria-expanded="menuOuvert === 'communaute'"
            aria-haspopup="true"
            aria-controls="menu-nav-communaute"
            @click.stop="basculerMenu('communaute')"
            @keydown="surToucheBoutonMenu($event, 'communaute')"
          >
            Communauté
            <span
              v-if="utilisateur && nbMatchsSansProno > 0"
              class="badge-nav-pronos"
              :title="`${nbMatchsSansProno} match(s) à pronostiquer bientôt`"
            >
              {{ nbMatchsSansProno > 9 ? "9+" : nbMatchsSansProno }}
            </span>
            <span class="fleche-nav" aria-hidden="true">▾</span>
          </button>
          <div
            v-show="menuOuvert === 'communaute'"
            id="menu-nav-communaute"
            class="menu-nav-deroulant"
            role="menu"
            aria-labelledby="bouton-nav-communaute"
            @click.stop
          >
            <router-link
              class="lien-menu-nav"
              role="menuitem"
              to="/classement-pronos"
              :class="{ actif: route.path === '/classement-pronos' }"
            >
              Classement
            </router-link>
            <router-link
              v-if="utilisateur"
              class="lien-menu-nav"
              role="menuitem"
              to="/pronos-journee"
              :class="{ actif: route.path === '/pronos-journee' }"
            >
              Journée
            </router-link>
            <router-link
              v-if="utilisateur"
              class="lien-menu-nav lien-nav-pronos"
              role="menuitem"
              to="/mes-pronos"
              :class="{ actif: route.path === '/mes-pronos' || route.path === '/nos-pronos' }"
            >
              Nos pronos
              <span
                v-if="nbMatchsSansProno > 0"
                class="badge-nav-pronos"
                :title="`${nbMatchsSansProno} match(s) à pronostiquer bientôt`"
              >
                {{ nbMatchsSansProno > 9 ? "9+" : nbMatchsSansProno }}
              </span>
            </router-link>
            <router-link
              v-if="utilisateur"
              class="lien-menu-nav"
              role="menuitem"
              to="/ligues"
              :class="{ actif: route.path === '/ligues' || route.path.startsWith('/ligue/') }"
            >
              Ligues privées
            </router-link>
          </div>
        </div>

        <div
          class="nav-groupe nav-groupe-compte"
          :class="{ ouvert: menuOuvert === 'compte' }"
        >
          <router-link
            v-if="!utilisateur"
            class="bouton-nav-groupe lien-nav-compte-direct"
            to="/connexion"
            :class="{ actif: compteActif }"
          >
            Connexion
          </router-link>
          <template v-else>
            <button
              id="bouton-nav-compte"
              type="button"
              class="bouton-nav-groupe"
              :aria-expanded="menuOuvert === 'compte'"
              aria-haspopup="true"
              aria-controls="menu-nav-compte"
              @click.stop="basculerMenu('compte')"
              @keydown="surToucheBoutonMenu($event, 'compte')"
            >
              <span class="pseudo-nav">{{ utilisateur.pseudo }}</span>
              <span class="fleche-nav" aria-hidden="true">▾</span>
            </button>
            <div
              v-show="menuOuvert === 'compte'"
              id="menu-nav-compte"
              class="menu-nav-deroulant menu-nav-compte"
              role="menu"
              aria-labelledby="bouton-nav-compte"
              @click.stop
            >
              <button
                type="button"
                class="lien-menu-nav lien-menu-action"
                role="menuitem"
                @click="seDeconnecter"
              >
                Déconnexion
              </button>
            </div>
          </template>
        </div>
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
    <router-view v-slot="{ Component }">
      <keep-alive :include="['Accueil', 'PageChampionnat']">
        <component :is="Component" />
      </keep-alive>
    </router-view>
  </main>
  <footer class="pied-site" role="contentinfo">
    <p class="pied-site-ligne">
      <span class="pied-site-liens">
        <router-link to="/glossaire">Comprendre les stats</router-link>
        <span class="pied-site-sep" aria-hidden="true">·</span>
        <router-link to="/conditions">Conditions d'utilisation</router-link>
      </span>
      <span class="pied-site-sep" aria-hidden="true">·</span>
      <span class="pied-site-hebergement">Stats Foot — hébergé au Canada</span>
    </p>
    <MentionJeuResponsable />
  </footer>
</template>
