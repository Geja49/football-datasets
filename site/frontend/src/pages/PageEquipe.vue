<script setup>
import { computed, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import CalendrierMatchs from "../composants/CalendrierMatchs.vue";
import DiagrammeDensites from "../composants/DiagrammeDensites.vue";
import DiagrammeRadar from "../composants/DiagrammeRadar.vue";
import { axesDepuisEquipe } from "../composants/axesDiagramme.js";
import { definirExtraNavigation, viderExtraNavigation } from "../contexteNavigation.js";
import { chargerEquipe } from "../services/api.js";

const route = useRoute();
const routeur = useRouter();
const championnat = computed(() => route.params.championnat);
const equipe = computed(() => route.params.equipe);
const saison = computed(() => route.query.saison || "2026-2027");
const data = ref({
  joueurs: [],
  matchs: [],
  matchs_radar: [],
  alias_equipe: [],
  buts: null,
  site: {},
  defense: {
    disponible: false,
    message: "",
    totaux: null,
    joueurs: [],
    gardiens: [],
  },
});
const erreur = ref("");

async function charger() {
  erreur.value = "";
  try {
    data.value = await chargerEquipe(championnat.value, saison.value, equipe.value);
  } catch (e) {
    erreur.value = e.message;
  }
}

watch([championnat, equipe, saison], charger, { immediate: true });

watch(
  [championnat, equipe, saison],
  () => {
    definirExtraNavigation({
      championnat: championnat.value,
      equipe: equipe.value,
      saison: saison.value,
    });
  },
  { immediate: true },
);

onUnmounted(viderExtraNavigation);

function ouvrirJoueur(nom) {
  routeur.push({
    path: `/joueur/${encodeURIComponent(nom)}`,
    query: { championnat: championnat.value },
  });
}

function ouvrirEquipe(nom) {
  if (!nom || nom === equipe.value) return;
  routeur.push({
    path: `/championnat/${encodeURIComponent(championnat.value)}/equipe/${encodeURIComponent(nom)}`,
    query: { saison: saison.value },
  });
}

const axesEquipe = computed(() =>
  axesDepuisEquipe(
    data.value.matchs_radar?.length ? data.value.matchs_radar : data.value.matchs,
    equipe.value,
    data.value.alias_equipe,
  ),
);

const butsEquipe = computed(() => data.value.buts || null);

function analyserMatch(match) {
  routeur.push({
    path: "/match",
    query: {
      championnat: championnat.value,
      saison: saison.value,
      equipe: equipe.value,
      domicile: match.domicile,
      exterieur: match.exterieur,
    },
  });
}
</script>

<template>
  <section class="hero">
    <div class="hero-inner fiche-club">
      <img
        v-if="data.site && data.site.url_logo"
        :src="data.site.url_logo"
        :alt="equipe"
        class="blason-grand"
      />
      <div>
        <h1 class="titre-hero">{{ equipe }}</h1>
        <p class="doux">{{ saison }}<span v-if="data.site && data.site.stade"> · {{ data.site.stade }}</span></p>
        <div
          v-if="butsEquipe && (butsEquipe.matchs_championnat || butsEquipe.matchs_ldc)"
          class="cartes-stats cartes-buts"
        >
          <div class="carte-stat">
            <span>{{ butsEquipe.libelle_championnat }}</span>
            <strong>{{ butsEquipe.championnat }}</strong>
          </div>
          <div class="carte-stat">
            <span>Ligue des champions</span>
            <strong>{{ butsEquipe.ligue_des_champions }}</strong>
          </div>
          <div class="carte-stat">
            <span>Total</span>
            <strong>{{ butsEquipe.total }}</strong>
          </div>
        </div>
        <router-link
          class="bouton-analyse"
          :to="{
            path: `/championnat/${encodeURIComponent(championnat)}/equipe/${encodeURIComponent(equipe)}/analyser`,
            query: { saison },
          }"
        >
          Analyser un match
        </router-link>
      </div>
    </div>
  </section>
  <div class="page">
    <p v-if="erreur" class="erreur">{{ erreur }}</p>
    <p v-else-if="!data.joueurs.length && !data.matchs.length" class="doux">
      Pas encore de données pour {{ equipe }} en {{ saison }}.
    </p>

    <div class="bloc" v-if="axesEquipe.length">
      <h2>Forces de l’équipe</h2>
      <p class="doux">
        Moyennes par match (buts, xG, tirs), forme sur 5 matchs, solidité et xG encaissés (inversés).
        <template v-if="butsEquipe && (butsEquipe.matchs_championnat || butsEquipe.matchs_ldc)">
          Buts : championnat + Ligue des champions
          ({{ butsEquipe.matchs_championnat }} + {{ butsEquipe.matchs_ldc }} matchs).
        </template>
      </p>
      <div class="grille-diagrammes">
        <div class="cadre-diagramme">
          <p class="titre-cadre">Radar</p>
          <DiagrammeRadar :axes="axesEquipe" />
        </div>
        <div class="cadre-diagramme">
          <p class="titre-cadre">Densités</p>
          <DiagrammeDensites :lignes="axesEquipe" />
        </div>
      </div>
    </div>

    <div class="bloc" v-if="data.joueurs.length">
      <h2>Effectif</h2>
      <table>
        <thead>
          <tr>
            <th>Joueur</th>
            <th>Poste</th>
            <th class="droit">M</th>
            <th class="droit">Min</th>
            <th class="droit">Buts</th>
            <th class="droit">PD</th>
            <th class="droit">Tirs</th>
            <th class="droit">xG</th>
            <th class="droit">xA</th>
            <th class="droit">PClés</th>
            <th class="droit">J</th>
            <th class="droit">R</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="joueur in data.joueurs"
            :key="joueur.joueur"
            class="cliquable"
            @click="ouvrirJoueur(joueur.joueur)"
          >
            <td>
              <span class="joueur-cellule">
                <img
                  v-if="joueur.url_photo"
                  :src="joueur.url_photo"
                  :alt="joueur.joueur"
                  class="portrait-mini"
                />
                {{ joueur.joueur }}
              </span>
            </td>
            <td>{{ joueur.poste }}</td>
            <td class="droit">{{ joueur.matchs }}</td>
            <td class="droit">{{ joueur.minutes }}</td>
            <td class="droit pts">{{ joueur.buts }}</td>
            <td class="droit">{{ joueur.passes_decisives }}</td>
            <td class="droit">{{ joueur.tirs }}</td>
            <td class="droit">{{ joueur.xg }}</td>
            <td class="droit">{{ joueur.xa }}</td>
            <td class="droit">{{ joueur.passes_cles }}</td>
            <td class="droit">{{ joueur.carton_jaune }}</td>
            <td class="droit">{{ joueur.carton_rouge }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="bloc">
      <h2>Contribution défensive</h2>
      <p class="doux">{{ data.defense && data.defense.message }}</p>
      <template v-if="data.defense && data.defense.disponible && data.defense.totaux">
        <div class="cartes-stats">
          <div class="carte-stat">
            <span>Tacles</span>
            <strong>{{ data.defense.totaux.tacles }}</strong>
          </div>
          <div class="carte-stat">
            <span>Tacles réussis</span>
            <strong>{{ data.defense.totaux.tacles_reussis }}</strong>
          </div>
          <div class="carte-stat">
            <span>Interceptions</span>
            <strong>{{ data.defense.totaux.interceptions }}</strong>
          </div>
          <div class="carte-stat">
            <span>Blocs</span>
            <strong>{{ data.defense.totaux.blocs }}</strong>
          </div>
          <div class="carte-stat">
            <span>Dégagements</span>
            <strong>{{ data.defense.totaux.degagements }}</strong>
          </div>
          <div class="carte-stat">
            <span>Duels</span>
            <strong>{{ data.defense.totaux.duels }}</strong>
          </div>
          <div v-if="data.defense.totaux.a_recoveries" class="carte-stat">
            <span>Recoveries</span>
            <strong>{{ data.defense.totaux.recoveries }}</strong>
          </div>
          <div v-if="data.defense.totaux.a_pressions" class="carte-stat">
            <span>Pressions</span>
            <strong>{{ data.defense.totaux.pressions }}</strong>
          </div>
        </div>
        <table v-if="data.defense.joueurs.length" class="table-defense">
          <thead>
            <tr>
              <th>Joueur</th>
              <th class="droit">M</th>
              <th class="droit">Tacles</th>
              <th class="droit">Réussis</th>
              <th class="droit">Interc.</th>
              <th class="droit">Blocs</th>
              <th class="droit">Dég.</th>
              <th class="droit">Duels</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="ligne in data.defense.joueurs"
              :key="ligne.joueur"
              class="cliquable"
              @click="ouvrirJoueur(ligne.joueur)"
            >
              <td>{{ ligne.joueur }}</td>
              <td class="droit">{{ ligne.matchs }}</td>
              <td class="droit">{{ ligne.tacles }}</td>
              <td class="droit">{{ ligne.tacles_reussis }}</td>
              <td class="droit">{{ ligne.interceptions }}</td>
              <td class="droit">{{ ligne.blocs }}</td>
              <td class="droit">{{ ligne.degagements }}</td>
              <td class="droit">{{ ligne.duels }}</td>
            </tr>
          </tbody>
        </table>
        <div v-if="data.defense.gardiens.length" class="gardiens-defense">
          <h3>Gardiens</h3>
          <p class="doux">
            Arrêts et xG des tirs subis (StatsBomb, ce n’est pas un PSxG).
          </p>
          <table>
            <thead>
              <tr>
                <th>Gardien</th>
                <th class="droit">M</th>
                <th class="droit">Arrêts</th>
                <th class="droit">xG subis</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="gardien in data.defense.gardiens"
                :key="gardien.joueur"
                class="cliquable"
                @click="ouvrirJoueur(gardien.joueur)"
              >
                <td>{{ gardien.joueur }}</td>
                <td class="droit">{{ gardien.matchs }}</td>
                <td class="droit">{{ gardien.arrets }}</td>
                <td class="droit">{{ gardien.xg_tirs_subis }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </div>

    <div class="bloc" v-if="data.matchs.length">
      <h2>Calendrier</h2>
      <CalendrierMatchs
        :matchs="data.matchs"
        :equipe-focus="equipe"
        afficher-tirs
        @ouvrir-equipe="ouvrirEquipe"
        @analyser="analyserMatch"
      />
    </div>
  </div>
</template>
