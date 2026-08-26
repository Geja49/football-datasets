<script setup>
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { CHAMPIONNATS_DEFAUT } from "../championnats.js";
import DiagrammeDensites from "../composants/DiagrammeDensites.vue";
import DiagrammeRadar from "../composants/DiagrammeRadar.vue";
import {
  AXES_JOUEUR,
  PLAFONDS_JOUEUR,
  axesComparaisonLigue,
  axesDepuisEquipe,
  axesDepuisJoueur,
  fusionnerComparaisonDirecte,
  histogrammeLocal,
  nombre,
} from "../composants/axesDiagramme.js";
import {
  chargerAccueil,
  chargerEquipe,
  chargerEquipesAnalyse,
  chargerJoueur,
  rechercher,
} from "../services/api.js";

const route = useRoute();
const routeur = useRouter();

const mode = ref(route.query.type === "clubs" ? "clubs" : "joueurs");
const nomA = ref(route.query.a || "");
const nomB = ref(route.query.b || "");
const championnat = ref(route.query.championnat || "Premier League");
const saison = ref(route.query.saison || "");
const saisons = ref([]);
const equipes = ref([]);
const suggestionsA = ref([]);
const suggestionsB = ref([]);
const dataA = ref(null);
const dataB = ref(null);
const chargement = ref(false);
const erreur = ref("");

async function assurerMeta() {
  const meta = await chargerAccueil();
  saisons.value = meta.saisons || [];
  if (!saison.value && saisons.value.length) {
    saison.value = saisons.value[0];
  }
}

async function chargerListeEquipes() {
  if (mode.value !== "clubs" || !championnat.value || !saison.value) return;
  try {
    const data = await chargerEquipesAnalyse(championnat.value, saison.value);
    equipes.value = (data.equipes || []).map((e) => e.equipe || e).filter(Boolean);
  } catch {
    equipes.value = [];
  }
}

let delaiA = null;
let delaiB = null;

function surSaisieA() {
  clearTimeout(delaiA);
  const q = nomA.value.trim();
  if (q.length < 2) {
    suggestionsA.value = [];
    return;
  }
  delaiA = setTimeout(async () => {
    const r = await rechercher(q);
    suggestionsA.value = (r.joueurs || []).slice(0, 8);
  }, 220);
}

function surSaisieB() {
  clearTimeout(delaiB);
  const q = nomB.value.trim();
  if (q.length < 2) {
    suggestionsB.value = [];
    return;
  }
  delaiB = setTimeout(async () => {
    const r = await rechercher(q);
    suggestionsB.value = (r.joueurs || []).slice(0, 8);
  }, 220);
}

function choisirJoueur(cote, nom) {
  if (cote === "a") {
    nomA.value = nom;
    suggestionsA.value = [];
  } else {
    nomB.value = nom;
    suggestionsB.value = [];
  }
  synchroniserUrl();
}

function synchroniserUrl() {
  const query = {
    type: mode.value,
    ...(nomA.value ? { a: nomA.value } : {}),
    ...(nomB.value ? { b: nomB.value } : {}),
  };
  if (mode.value === "clubs") {
    query.championnat = championnat.value;
    if (saison.value) query.saison = saison.value;
  }
  routeur.replace({ path: "/comparer", query });
}

function choisirMode(valeur) {
  mode.value = valeur;
  dataA.value = null;
  dataB.value = null;
  synchroniserUrl();
}

async function comparer() {
  erreur.value = "";
  if (!nomA.value.trim() || !nomB.value.trim()) {
    erreur.value = "Choisissez deux noms à comparer.";
    return;
  }
  if (nomA.value.trim().toLowerCase() === nomB.value.trim().toLowerCase()) {
    erreur.value = "Les deux sélections doivent être différentes.";
    return;
  }
  synchroniserUrl();
  chargement.value = true;
  try {
    if (mode.value === "joueurs") {
      const [a, b] = await Promise.all([
        chargerJoueur(nomA.value.trim()),
        chargerJoueur(nomB.value.trim()),
      ]);
      dataA.value = a;
      dataB.value = b;
    } else {
      await assurerMeta();
      const [a, b] = await Promise.all([
        chargerEquipe(championnat.value, saison.value, nomA.value.trim()),
        chargerEquipe(championnat.value, saison.value, nomB.value.trim()),
      ]);
      dataA.value = a;
      dataB.value = b;
    }
  } catch (e) {
    dataA.value = null;
    dataB.value = null;
    erreur.value = e.message || "Comparaison impossible";
  } finally {
    chargement.value = false;
  }
}

function saisonRadarJoueur(data) {
  const lignes = data?.saisons || [];
  if (!lignes.length) return null;
  const annee = lignes[0].saison;
  const candidates = lignes.filter((l) => l.saison === annee);
  return [...candidates].sort((a, b) => nombre(b.minutes) - nombre(a.minutes))[0];
}

function reperesJoueur(data) {
  if (data?.reperes?.axes?.length) return data.reperes;
  const lignes = data?.saisons || [];
  if (!lignes.length) return null;
  return {
    axes: AXES_JOUEUR.map((def) => {
      const plafond = Math.max(
        ...lignes.map((l) => nombre(l[def.cle])),
        PLAFONDS_JOUEUR[def.cle] || 1,
      );
      return {
        cle: def.cle,
        libelle: def.libelle,
        plafond,
        histogramme: histogrammeLocal(
          lignes.map((l) => nombre(l[def.cle])),
          plafond,
        ),
      };
    }),
  };
}

const axesA = computed(() => {
  if (!dataA.value) return [];
  if (mode.value === "joueurs") {
    const ligne = saisonRadarJoueur(dataA.value);
    return ligne ? axesDepuisJoueur(ligne, reperesJoueur(dataA.value)) : [];
  }
  const matchs = (dataA.value.matchs || []).filter(
    (m) => m.joue && m.buts_domicile != null,
  );
  return axesDepuisEquipe(
    matchs.length ? matchs : dataA.value.matchs_radar || [],
    dataA.value.equipe || nomA.value,
    dataA.value.alias_equipe || [],
    dataA.value.reperes,
  );
});

const axesB = computed(() => {
  if (!dataB.value) return [];
  if (mode.value === "joueurs") {
    const ligne = saisonRadarJoueur(dataB.value);
    return ligne ? axesDepuisJoueur(ligne, reperesJoueur(dataB.value)) : [];
  }
  const matchs = (dataB.value.matchs || []).filter(
    (m) => m.joue && m.buts_domicile != null,
  );
  return axesDepuisEquipe(
    matchs.length ? matchs : dataB.value.matchs_radar || [],
    dataB.value.equipe || nomB.value,
    dataB.value.alias_equipe || [],
    dataB.value.reperes,
  );
});

const axesFusion = computed(() =>
  fusionnerComparaisonDirecte(axesA.value, axesB.value),
);

const polygoneB = computed(() => axesComparaisonLigue(axesFusion.value));

const libelleA = computed(() =>
  mode.value === "joueurs" ? nomA.value || "Joueur A" : nomA.value || "Club A",
);
const libelleB = computed(() =>
  mode.value === "joueurs" ? nomB.value || "Joueur B" : nomB.value || "Club B",
);

const championnats = CHAMPIONNATS_DEFAUT;

watch(
  () => route.query,
  (q) => {
    mode.value = q.type === "clubs" ? "clubs" : "joueurs";
    nomA.value = q.a || "";
    nomB.value = q.b || "";
    if (q.championnat) championnat.value = q.championnat;
    if (q.saison) saison.value = q.saison;
  },
  { immediate: true },
);

watch([mode, championnat, saison], async () => {
  if (mode.value === "clubs") {
    await assurerMeta();
    await chargerListeEquipes();
  }
}, { immediate: true });

watch(
  () => [route.query.a, route.query.b, route.query.type, route.query.championnat, route.query.saison],
  () => {
    if (route.query.a && route.query.b) comparer();
  },
  { immediate: true },
);
</script>

<template>
  <section class="hero">
    <div class="hero-inner">
      <h1 class="titre-hero">Comparer</h1>
      <p class="doux">
        Même lecture que vs moyenne ligue : radar (plein / pointillé) et densités.
      </p>
    </div>
  </section>
  <div class="page">
    <div class="bloc">
      <div class="onglets">
        <button
          type="button"
          class="onglet"
          :class="{ actif: mode === 'joueurs' }"
          @click="choisirMode('joueurs')"
        >
          Deux joueurs
        </button>
        <button
          type="button"
          class="onglet"
          :class="{ actif: mode === 'clubs' }"
          @click="choisirMode('clubs')"
        >
          Deux clubs
        </button>
      </div>

      <div v-if="mode === 'clubs'" class="ligne-haut">
        <select v-model="championnat" @change="synchroniserUrl">
          <option v-for="c in championnats" :key="c" :value="c">{{ c }}</option>
        </select>
        <select v-model="saison" @change="synchroniserUrl">
          <option v-for="s in saisons" :key="s" :value="s">{{ s }}</option>
        </select>
      </div>

      <div class="grille-comparer">
        <label class="champ-comparer">
          <span>{{ mode === 'joueurs' ? 'Joueur A' : 'Club A' }}</span>
          <template v-if="mode === 'joueurs'">
            <input v-model="nomA" type="search" autocomplete="off" @input="surSaisieA" @change="synchroniserUrl" />
            <ul v-if="suggestionsA.length" class="liste-suggestions">
              <li v-for="j in suggestionsA" :key="'a-' + j.joueur">
                <button type="button" @click="choisirJoueur('a', j.joueur)">
                  {{ j.joueur }} · {{ j.equipe }}
                </button>
              </li>
            </ul>
          </template>
          <select v-else v-model="nomA" @change="synchroniserUrl">
            <option value="">Choisir…</option>
            <option v-for="e in equipes" :key="'a-' + e" :value="e">{{ e }}</option>
          </select>
        </label>
        <label class="champ-comparer">
          <span>{{ mode === 'joueurs' ? 'Joueur B' : 'Club B' }}</span>
          <template v-if="mode === 'joueurs'">
            <input v-model="nomB" type="search" autocomplete="off" @input="surSaisieB" @change="synchroniserUrl" />
            <ul v-if="suggestionsB.length" class="liste-suggestions">
              <li v-for="j in suggestionsB" :key="'b-' + j.joueur">
                <button type="button" @click="choisirJoueur('b', j.joueur)">
                  {{ j.joueur }} · {{ j.equipe }}
                </button>
              </li>
            </ul>
          </template>
          <select v-else v-model="nomB" @change="synchroniserUrl">
            <option value="">Choisir…</option>
            <option v-for="e in equipes" :key="'b-' + e" :value="e">{{ e }}</option>
          </select>
        </label>
      </div>

      <button type="button" class="bouton-analyse" @click="comparer">Comparer</button>
      <p v-if="chargement" class="doux">Chargement…</p>
      <p v-if="erreur" class="erreur">{{ erreur }}</p>
    </div>

    <div class="bloc" v-if="axesFusion.length && !chargement">
      <h2>{{ libelleA }} vs {{ libelleB }}</h2>
      <p class="doux">
        <template v-if="mode === 'joueurs'">
          Profil de saison récente (buts, xG, passes, xA, tirs, minutes).
        </template>
        <template v-else>
          Moyennes par match et forme (même saison / championnat).
        </template>
      </p>
      <div class="grille-diagrammes">
        <div class="cadre-diagramme">
          <p class="titre-cadre">Radar</p>
          <DiagrammeRadar
            :axes="axesFusion"
            :comparaison="polygoneB"
            :libelle-sujet="libelleA"
            :libelle-comparaison="libelleB"
          />
        </div>
        <div class="cadre-diagramme">
          <p class="titre-cadre">Densités</p>
          <DiagrammeDensites :lignes="axesFusion" :libelle-sujet="libelleA" :libelle-comparaison="libelleB" />
        </div>
      </div>
      <table class="table-vs-ligue">
        <thead>
          <tr>
            <th>Métrique</th>
            <th class="droit">{{ libelleA }}</th>
            <th class="droit">{{ libelleB }}</th>
            <th>Écart</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="axe in axesFusion" :key="'cmp-' + axe.cle">
            <td>{{ axe.libelle }}</td>
            <td class="droit pts">{{ axe.texte }}</td>
            <td class="droit">{{ axe.texteLigue || "—" }}</td>
            <td class="ecart-cellule">{{ axe.texteEcart || "—" }}</td>
          </tr>
        </tbody>
      </table>
      <p class="doux">
        <router-link
          v-if="mode === 'joueurs'"
          :to="`/joueur/${encodeURIComponent(nomA)}`"
        >Fiche {{ libelleA }}</router-link>
        <template v-if="mode === 'joueurs'"> · </template>
        <router-link
          v-if="mode === 'joueurs'"
          :to="`/joueur/${encodeURIComponent(nomB)}`"
        >Fiche {{ libelleB }}</router-link>
        <router-link
          v-if="mode === 'clubs'"
          :to="{
            path: `/championnat/${encodeURIComponent(championnat)}/equipe/${encodeURIComponent(nomA)}`,
            query: { saison },
          }"
        >Fiche {{ libelleA }}</router-link>
        <template v-if="mode === 'clubs'"> · </template>
        <router-link
          v-if="mode === 'clubs'"
          :to="{
            path: `/championnat/${encodeURIComponent(championnat)}/equipe/${encodeURIComponent(nomB)}`,
            query: { saison },
          }"
        >Fiche {{ libelleB }}</router-link>
      </p>
    </div>
  </div>
</template>
