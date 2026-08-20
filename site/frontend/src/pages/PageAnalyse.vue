<script setup>
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  chargerAccueil,
  chargerAnalyse,
  chargerEquipesAnalyse,
  chargerProchainsMatchs,
} from "../services/api.js";

const MOIS = [
  "janvier",
  "février",
  "mars",
  "avril",
  "mai",
  "juin",
  "juillet",
  "août",
  "septembre",
  "octobre",
  "novembre",
  "décembre",
];

const route = useRoute();
const routeur = useRouter();

const championnats = ref([
  "Premier League",
  "La Liga",
  "Bundesliga",
  "Serie A",
  "Ligue 1",
  "Ligue des champions",
]);
const saisons = ref([]);
const equipes = ref([]);
const championnat = ref(route.query.championnat || "La Liga");
const saison = ref(route.query.saison || "");
const club = ref(route.query.equipe || route.query.domicile || "");
const domicile = ref(route.query.domicile || "");
const exterieur = ref(route.query.exterieur || "");
const data = ref(null);
const erreur = ref("");
const chargement = ref(false);
const matchsEquipe = ref([]);
const matchsLigue = ref([]);

async function chargerSaisons() {
  const meta = await chargerAccueil();
  saisons.value = meta.saisons;
  if (meta.championnats && meta.championnats.length) {
    championnats.value = meta.championnats.map((item) => item.nom);
  }
  if (!saison.value) {
    saison.value = meta.saisons[0] || "2026-2027";
  }
}

async function chargerListe() {
  if (!championnat.value || !saison.value) return;
  const liste = await chargerEquipesAnalyse(championnat.value, saison.value);
  equipes.value = liste.equipes || [];
}

async function chargerSuggestions() {
  if (!championnat.value || !saison.value) return;
  try {
    const resultat = await chargerProchainsMatchs(
      championnat.value,
      saison.value,
      club.value || "",
    );
    if (resultat.equipe && resultat.equipe !== club.value) {
      club.value = resultat.equipe;
    }
    matchsEquipe.value = resultat.matchs_equipe || [];
    matchsLigue.value = resultat.matchs_ligue || [];
  } catch (e) {
    matchsEquipe.value = [];
    matchsLigue.value = [];
  }
}

async function lancerAnalyse() {
  if (!domicile.value || !exterieur.value || domicile.value === exterieur.value) {
    data.value = null;
    return;
  }
  erreur.value = "";
  chargement.value = true;
  try {
    data.value = await chargerAnalyse(
      championnat.value,
      saison.value,
      domicile.value,
      exterieur.value,
    );
    routeur.replace({
      path: "/match",
      query: {
        championnat: championnat.value,
        saison: saison.value,
        domicile: domicile.value,
        exterieur: exterieur.value,
        ...(club.value ? { equipe: club.value } : {}),
      },
    });
  } catch (e) {
    data.value = null;
    erreur.value = e.message;
  } finally {
    chargement.value = false;
  }
}

function choisirMatch(match) {
  domicile.value = match.domicile;
  exterieur.value = match.exterieur;
}

function choisirAncienMatch(match) {
  if (match.saison) {
    saison.value = match.saison;
  }
  domicile.value = match.domicile;
  exterieur.value = match.exterieur;
}

function surChoixClub() {
  data.value = null;
  domicile.value = "";
  exterieur.value = "";
  erreur.value = "";
  routeur.replace({
    path: "/match",
    query: {
      championnat: championnat.value,
      saison: saison.value,
      ...(club.value ? { equipe: club.value } : {}),
    },
  });
}

function formaterDate(iso) {
  if (!iso || iso.length < 10) return iso || "";
  const jour = Number(iso.slice(8, 10));
  const mois = Number(iso.slice(5, 7));
  const annee = iso.slice(0, 4);
  if (!mois || mois < 1 || mois > 12) return iso;
  return `${jour} ${MOIS[mois - 1]} ${annee}`;
}

watch(
  () => [
    route.query.championnat,
    route.query.saison,
    route.query.domicile,
    route.query.exterieur,
    route.query.equipe,
  ],
  ([c, s, d, e, eq]) => {
    if (c) championnat.value = c;
    if (s) saison.value = s;
    domicile.value = d || "";
    exterieur.value = e || "";
    club.value = eq || d || "";
    if (!d || !e) data.value = null;
  },
);

watch([championnat, saison], async () => {
  await chargerListe();
  const noms = new Set(equipes.value.map((item) => item.equipe));
  if (domicile.value && !noms.has(domicile.value)) domicile.value = "";
  if (exterieur.value && !noms.has(exterieur.value)) exterieur.value = "";
  await chargerSuggestions();
  if (domicile.value && exterieur.value) {
    await lancerAnalyse();
  }
});

watch(club, () => {
  chargerSuggestions();
});

watch([domicile, exterieur], () => {
  if (domicile.value && exterieur.value && domicile.value !== exterieur.value) {
    lancerAnalyse();
  }
});

chargerSaisons().then(async () => {
  await chargerListe();
  await chargerSuggestions();
  if (domicile.value && exterieur.value) {
    await lancerAnalyse();
  }
});

const pred = computed(() => (data.value && data.value.prediction) || {});
const suggestionsVisibles = computed(() => !data.value);
const matchJoue = computed(() => {
  const bloc = data.value && data.value.match_joue;
  return bloc && bloc.joue ? bloc : null;
});
const confrontations = computed(() => (data.value && data.value.confrontations) || null);

function largeur(pct) {
  return { width: `${pct || 0}%` };
}

function couple(a, b) {
  if (a == null && b == null) return "—";
  return `${a ?? "—"} – ${b ?? "—"}`;
}
</script>

<template>
  <section class="hero">
    <div class="hero-inner">
      <router-link to="/" class="doux">← Ligues</router-link>
      <h1 class="titre-hero">Analyse de match</h1>
      <p class="doux">Forces, faiblesses et scénario statistique — pas un pronostic de paris.</p>
      <div class="ligne-haut" style="margin-top: 18px">
        <label>
          Championnat
          <select v-model="championnat">
            <option v-for="item in championnats" :key="item" :value="item">{{ item }}</option>
          </select>
        </label>
        <label>
          Saison
          <select v-model="saison">
            <option v-for="item in saisons" :key="item" :value="item">{{ item }}</option>
          </select>
        </label>
        <label>
          Club
          <select v-model="club" @change="surChoixClub">
            <option value="">Choisir un club…</option>
            <option v-for="item in equipes" :key="'c' + item.equipe" :value="item.equipe">
              {{ item.equipe }}
            </option>
          </select>
        </label>
      </div>
      <p class="doux" style="margin-top: 12px">Ou deux équipes au choix :</p>
      <div class="ligne-haut">
        <label>
          Domicile
          <select v-model="domicile">
            <option value="">Choisir…</option>
            <option v-for="item in equipes" :key="'d' + item.equipe" :value="item.equipe">
              {{ item.equipe }}
            </option>
          </select>
        </label>
        <label>
          Extérieur
          <select v-model="exterieur">
            <option value="">Choisir…</option>
            <option v-for="item in equipes" :key="'e' + item.equipe" :value="item.equipe">
              {{ item.equipe }}
            </option>
          </select>
        </label>
      </div>
    </div>
  </section>

  <div class="page">
    <p v-if="erreur" class="erreur">{{ erreur }}</p>
    <p v-if="chargement" class="doux">Calcul en cours…</p>

    <template v-if="suggestionsVisibles">
      <div class="bloc" v-if="club">
        <h2>Prochains matchs de {{ club }}</h2>
        <p v-if="!matchsEquipe.length" class="doux">
          Pas de match à venir pour {{ club }} en {{ saison }}.
        </p>
        <ul v-else class="liste-suggestions">
          <li v-for="match in matchsEquipe" :key="match.date + match.domicile + match.exterieur">
            <button type="button" class="suggestion-match" @click="choisirMatch(match)">
              <span class="suggestion-date">{{ formaterDate(match.date) }}</span>
              <span class="suggestion-heure">{{ match.heure || "—" }}</span>
              <span class="suggestion-lieu">{{ match.lieu }}</span>
              <span class="equipe-ligne">
                <img
                  v-if="match.lieu === 'Domicile' ? match.url_logo_exterieur : match.url_logo_domicile"
                  :src="match.lieu === 'Domicile' ? match.url_logo_exterieur : match.url_logo_domicile"
                  :alt="match.adversaire"
                  class="blason"
                />
                {{ match.adversaire }}
              </span>
            </button>
          </li>
        </ul>
      </div>
      <div class="bloc" v-else>
        <p class="doux">Choisissez un club pour voir ses 8 prochains matchs, ou cliquez un match de la ligue.</p>
      </div>

      <div class="bloc" v-if="matchsLigue.length">
        <h2>Prochaine journée</h2>
        <ul class="liste-suggestions">
          <li v-for="match in matchsLigue" :key="'l' + match.date + match.domicile + match.exterieur">
            <button type="button" class="suggestion-match" @click="choisirMatch(match)">
              <span class="suggestion-date">{{ formaterDate(match.date) }}</span>
              <span class="suggestion-heure">{{ match.heure || "—" }}</span>
              <span class="equipe-ligne">
                <img
                  v-if="match.url_logo_domicile"
                  :src="match.url_logo_domicile"
                  :alt="match.domicile"
                  class="blason"
                />
                {{ match.domicile }}
              </span>
              <span class="doux">–</span>
              <span class="equipe-ligne">
                <img
                  v-if="match.url_logo_exterieur"
                  :src="match.url_logo_exterieur"
                  :alt="match.exterieur"
                  class="blason"
                />
                {{ match.exterieur }}
              </span>
            </button>
          </li>
        </ul>
      </div>
    </template>

    <p v-else-if="domicile === exterieur" class="erreur">Choisissez deux équipes différentes.</p>

    <template v-if="data">
      <p class="mention">{{ data.avertissement }} Saison des moyennes : {{ data.saison_ligue }}.</p>

      <div class="grille-analyse">
        <article
          class="carte-equipe"
          v-for="(cote, rang) in [data.domicile, data.exterieur]"
          :key="cote.nom + rang"
        >
          <header class="entete-equipe">
            <img v-if="cote.url_logo" :src="cote.url_logo" :alt="cote.nom" class="blason-grand" />
            <div>
              <p class="tag">{{ rang === 0 ? "Domicile" : "Extérieur" }}</p>
              <h2>{{ cote.nom }}</h2>
              <p class="doux">
                xG {{ cote.saison_xg }} · {{ cote.nb_matchs_xg }} matchs
                {{ rang === 0 ? "à domicile" : "à l'extérieur" }}
              </p>
              <p class="forme">
                Forme {{ cote.forme.resume }}
                <span v-for="(lettre, i) in cote.forme.serie" :key="i" :class="'pastille pastille-' + lettre">
                  {{ lettre }}
                </span>
              </p>
              <p class="doux">
                5 derniers : {{ cote.forme.buts_pour }} buts pour,
                {{ cote.forme.buts_contre }} contre
              </p>
            </div>
          </header>
          <p class="chiffres-xg">
            <strong>{{ cote.xg_marques ?? "—" }}</strong> xG marqués ·
            <strong>{{ cote.xg_encaisses ?? "—" }}</strong> xG encaissés
          </p>
          <h3>Forces</h3>
          <ul class="liste-points">
            <li v-for="phrase in cote.forces" :key="phrase" class="point-force">{{ phrase }}</li>
          </ul>
          <h3>Faiblesses</h3>
          <ul class="liste-points">
            <li v-for="phrase in cote.faiblesses" :key="phrase" class="point-faiblesse">{{ phrase }}</li>
          </ul>
        </article>
      </div>

      <div class="bloc carte-scenario" v-if="matchJoue">
        <h2>Ce qui s'est passé</h2>
        <p class="doux">{{ formaterDate(matchJoue.date) }}</p>
        <p class="score-gros">
          {{ data.domicile.nom }} {{ matchJoue.buts_domicile }} – {{ matchJoue.buts_exterieur }}
          {{ data.exterieur.nom }}
        </p>
        <div class="cartes-stats">
          <div class="carte-stat">
            <span>xG</span>
            <strong class="valeur-couple">{{ couple(matchJoue.xg_domicile, matchJoue.xg_exterieur) }}</strong>
          </div>
          <div class="carte-stat">
            <span>Tirs</span>
            <strong class="valeur-couple">{{ couple(matchJoue.tirs_domicile, matchJoue.tirs_exterieur) }}</strong>
          </div>
          <div class="carte-stat">
            <span>Cadrés</span>
            <strong class="valeur-couple">{{ couple(matchJoue.tirs_cadres_domicile, matchJoue.tirs_cadres_exterieur) }}</strong>
          </div>
          <div class="carte-stat">
            <span>Jaunes</span>
            <strong class="valeur-couple">{{ couple(matchJoue.jaunes_domicile, matchJoue.jaunes_exterieur) }}</strong>
          </div>
          <div class="carte-stat">
            <span>Rouges</span>
            <strong class="valeur-couple">{{ couple(matchJoue.rouges_domicile, matchJoue.rouges_exterieur) }}</strong>
          </div>
        </div>
      </div>

      <div class="bloc carte-scenario">
        <h2>{{ matchJoue ? "Ce qui pouvait se passer" : "Ce qui peut se passer" }}</h2>
        <p class="doux">{{ pred.texte }}</p>
        <div class="cartes-stats">
          <div class="carte-stat">
            <span>xG prévu domicile</span>
            <strong>{{ pred.xg_prevu_domicile }}</strong>
          </div>
          <div class="carte-stat">
            <span>xG prévu extérieur</span>
            <strong>{{ pred.xg_prevu_exterieur }}</strong>
          </div>
          <div class="carte-stat">
            <span>Score le plus probable</span>
            <strong>{{ pred.score_plus_probable }}</strong>
          </div>
        </div>
        <div class="bloc-1n2">
          <div class="ligne-1n2">
            <span>{{ data.domicile.nom }} {{ pred.p_victoire_domicile }} %</span>
            <span>Nul {{ pred.p_nul }} %</span>
            <span>{{ data.exterieur.nom }} {{ pred.p_victoire_exterieur }} %</span>
          </div>
          <div class="barre-1n2" role="img" :aria-label="'Probabilités 1N2'">
            <div class="seg-1" :style="largeur(pred.p_victoire_domicile)"></div>
            <div class="seg-n" :style="largeur(pred.p_nul)"></div>
            <div class="seg-2" :style="largeur(pred.p_victoire_exterieur)"></div>
          </div>
        </div>
        <h3>Scores les plus fréquents</h3>
        <ul class="liste-scores">
          <li v-for="item in pred.scores_frequents" :key="item.score">
            <span class="score-gros">{{ item.score }}</span>
            <span class="doux">{{ item.pct }} %</span>
          </li>
        </ul>
      </div>

      <div class="bloc carte-scenario" v-if="confrontations">
        <h2>Confrontations</h2>
        <p v-if="!confrontations.nb" class="doux">
          Pas encore de match entre ces deux clubs dans cette compétition.
        </p>
        <template v-else>
          <div class="ligne-1n2">
            <span>{{ data.domicile.nom }} {{ confrontations.victoires_domicile }}</span>
            <span>Nuls {{ confrontations.nuls }}</span>
            <span>{{ data.exterieur.nom }} {{ confrontations.victoires_exterieur }}</span>
          </div>
          <ul class="liste-suggestions">
            <li
              v-for="match in confrontations.matchs"
              :key="match.date + match.domicile + match.exterieur"
            >
              <button type="button" class="suggestion-match" @click="choisirAncienMatch(match)">
                <span class="suggestion-date">{{ formaterDate(match.date) }}</span>
                <span class="doux">{{ match.saison }}</span>
                <span>{{ match.domicile }}</span>
                <span class="score-gros">{{ match.score }}</span>
                <span>{{ match.exterieur }}</span>
              </button>
            </li>
          </ul>
        </template>
      </div>

      <div class="bloc" v-if="matchsEquipe.length">
        <h2>Autres matchs de {{ club || domicile }}</h2>
        <ul class="liste-suggestions">
          <li v-for="match in matchsEquipe" :key="'a' + match.date + match.domicile + match.exterieur">
            <button type="button" class="suggestion-match" @click="choisirMatch(match)">
              <span class="suggestion-date">{{ formaterDate(match.date) }}</span>
              <span class="suggestion-lieu">{{ match.lieu }}</span>
              <span>{{ match.adversaire }}</span>
            </button>
          </li>
        </ul>
      </div>
    </template>
  </div>
</template>
