<script setup>
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { chargerEquipe } from "../services/api.js";

const route = useRoute();
const routeur = useRouter();
const championnat = computed(() => route.params.championnat);
const equipe = computed(() => route.params.equipe);
const saison = computed(() => route.query.saison || "2026-2027");
const data = ref({ joueurs: [], matchs: [], site: {} });
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

function ouvrirJoueur(nom) {
  routeur.push({
    path: `/joueur/${encodeURIComponent(nom)}`,
    query: { championnat: championnat.value },
  });
}

function score(match) {
  if (!match.joue) return "—";
  if (match.buts_domicile == null || match.buts_exterieur == null) return "—";
  return `${match.buts_domicile} - ${match.buts_exterieur}`;
}

function ouvrirEquipe(nom) {
  if (!nom || nom === equipe.value) return;
  routeur.push({
    path: `/championnat/${encodeURIComponent(championnat.value)}/equipe/${encodeURIComponent(nom)}`,
    query: { saison: saison.value },
  });
}

function analyserMatch(match) {
  if (match.joue) return;
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
        <router-link
          :to="{ path: `/championnat/${encodeURIComponent(championnat)}`, query: { saison } }"
          class="doux"
        >
          ← {{ championnat }}
        </router-link>
        <h1 class="titre-hero">{{ equipe }}</h1>
        <p class="doux">{{ saison }}<span v-if="data.site && data.site.stade"> · {{ data.site.stade }}</span></p>
        <router-link
          class="bouton-analyse"
          :to="{
            path: '/match',
            query: { championnat, saison, equipe, domicile: equipe },
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
            <th class="droit">xG</th>
            <th class="droit">xA</th>
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
            <td class="droit">{{ joueur.xg }}</td>
            <td class="droit">{{ joueur.xa }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="bloc" v-if="data.matchs.length">
      <h2>Calendrier</h2>
      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Heure</th>
            <th>Domicile</th>
            <th class="droit">Score</th>
            <th>Extérieur</th>
            <th class="droit">Tirs</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="match in data.matchs"
            :key="match.date + match.domicile + match.exterieur"
            :class="{ 'match-avenir': !match.joue, cliquable: !match.joue }"
            @click="analyserMatch(match)"
          >
            <td>{{ match.date }}</td>
            <td>{{ match.heure || "—" }}</td>
            <td>
              <a
                href="#"
                class="equipe-ligne"
                @click.prevent.stop="ouvrirEquipe(match.domicile)"
              >
                {{ match.domicile }}
              </a>
            </td>
            <td class="droit score-gros">{{ score(match) }}</td>
            <td>
              <a
                href="#"
                class="equipe-ligne"
                @click.prevent.stop="ouvrirEquipe(match.exterieur)"
              >
                {{ match.exterieur }}
              </a>
            </td>
            <td class="droit">
              <template v-if="match.joue && match.tirs_domicile != null">
                {{ match.tirs_domicile }} - {{ match.tirs_exterieur }}
              </template>
              <span v-else class="doux">—</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
