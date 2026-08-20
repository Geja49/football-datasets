<script setup>
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import CalendrierMatchs from "../composants/CalendrierMatchs.vue";
import { chargerAccueil, chargerCalendrier, chargerClassement, chargerMeilleurs } from "../services/api.js";

const route = useRoute();
const routeur = useRouter();
const championnat = computed(() => route.params.championnat);
const saisons = ref([]);
const saison = ref(route.query.saison || "");
const classement = ref([]);
const programme = ref([]);
const formatClassement = ref("ligue");
const onglet = ref("classement");
const meilleurs = ref([]);
const erreur = ref("");

async function charger() {
  erreur.value = "";
  try {
    if (!saison.value) {
      const meta = await chargerAccueil();
      saisons.value = meta.saisons;
      saison.value = meta.saisons[0];
    } else if (!saisons.value.length) {
      saisons.value = (await chargerAccueil()).saisons;
    }
    const [dataClassement, dataCalendrier] = await Promise.all([
      chargerClassement(championnat.value, saison.value),
      chargerCalendrier(championnat.value, saison.value),
    ]);
    if (dataClassement.saisons && dataClassement.saisons.length) {
      saisons.value = dataClassement.saisons;
      if (!saisons.value.includes(saison.value)) {
        saison.value = saisons.value[0];
        return;
      }
    }
    classement.value = dataClassement.classement;
    formatClassement.value = dataClassement.format || "ligue";
    programme.value = dataCalendrier.programme || [];
  } catch (e) {
    erreur.value = e.message;
  }
}

watch([championnat, saison], charger, { immediate: true });

async function chargerClassementJoueurs() {
  if (onglet.value !== "buteurs" && onglet.value !== "passeurs") {
    return;
  }
  if (!saison.value || !championnat.value) {
    return;
  }
  const type = onglet.value === "buteurs" ? "buts" : "passes";
  const ligue = championnat.value;
  const annee = saison.value;
  meilleurs.value = [];
  try {
    const data = await chargerMeilleurs(ligue, annee, type);
    if (onglet.value !== (type === "buts" ? "buteurs" : "passeurs")) {
      return;
    }
    if (championnat.value !== ligue || saison.value !== annee) {
      return;
    }
    meilleurs.value = data.joueurs || [];
  } catch (e) {
    if (championnat.value === ligue && saison.value === annee) {
      meilleurs.value = [];
    }
  }
}

watch([championnat, saison, onglet], chargerClassementJoueurs);

function ouvrirEquipe(equipe) {
  routeur.push({
    path: `/championnat/${encodeURIComponent(championnat.value)}/equipe/${encodeURIComponent(equipe)}`,
    query: { saison: saison.value },
  });
}

function ouvrirJoueur(nom) {
  routeur.push({
    path: `/joueur/${encodeURIComponent(nom)}`,
    query: { championnat: championnat.value },
  });
}

function zone(rang) {
  if (formatClassement.value === "phase_de_ligue") {
    if (rang <= 8) return "zone-ldc";
    if (rang <= 24) return "zone-barrages";
    return "zone-hors-course";
  }
  const total = classement.value.length;
  if (rang <= 4) return "zone-ldc";
  if (total && rang >= total - 2) return "zone-rel";
  return "";
}

function analyserMatch(match) {
  routeur.push({
    path: "/match",
    query: {
      championnat: championnat.value,
      saison: saison.value,
      domicile: match.domicile,
      exterieur: match.exterieur,
    },
  });
}

function serieForme(serie) {
  return [...(serie || [])].reverse();
}
</script>

<template>
  <section class="hero">
    <div class="hero-inner">
      <router-link to="/" class="doux">← Ligues</router-link>
      <h1 class="titre-hero">{{ championnat }}</h1>
      <div class="ligne-haut">
        <p class="doux">{{ saison }}</p>
        <select v-model="saison">
          <option v-for="item in saisons" :key="item" :value="item">{{ item }}</option>
        </select>
        <router-link
          class="bouton-analyse"
          :to="{ path: '/match', query: { championnat, saison } }"
        >
          Analyser un match
        </router-link>
      </div>
    </div>
  </section>
  <div class="page">
    <p v-if="erreur" class="erreur">{{ erreur }}</p>
    <template v-else>
      <div class="onglets">
        <button
          type="button"
          class="onglet"
          :class="{ actif: onglet === 'classement' }"
          @click="onglet = 'classement'"
        >
          Classement
        </button>
        <button
          type="button"
          class="onglet"
          :class="{ actif: onglet === 'calendrier' }"
          @click="onglet = 'calendrier'"
        >
          Calendrier
        </button>
        <button
          type="button"
          class="onglet"
          :class="{ actif: onglet === 'buteurs' }"
          @click="onglet = 'buteurs'"
        >
          Buteurs
        </button>
        <button
          type="button"
          class="onglet"
          :class="{ actif: onglet === 'passeurs' }"
          @click="onglet = 'passeurs'"
        >
          Passeurs
        </button>
      </div>

      <template v-if="onglet === 'classement'">
        <p v-if="!classement.length" class="doux">
          Aucun match joué pour {{ championnat }} en {{ saison }}.
        </p>
        <p v-if="classement.length && formatClassement === 'phase_de_ligue'" class="legende-classement">
          <span class="legende-ldc"><i></i> 1-8 : huitièmes</span>
          <span class="legende-barrages"><i></i> 9-24 : barrages</span>
          <span class="legende-hors"><i></i> 25-36 : éliminés</span>
        </p>
        <table v-if="classement.length">
          <thead>
            <tr>
              <th>#</th>
              <th>Club</th>
              <th class="droit">Pts</th>
              <th class="droit">J</th>
              <th class="droit">V</th>
              <th class="droit">N</th>
              <th class="droit">D</th>
              <th class="droit">BP</th>
              <th class="droit">BC</th>
              <th class="droit">Diff</th>
              <th>Forme</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="ligne in classement"
              :key="ligne.equipe"
              class="cliquable"
              :class="zone(ligne.rang)"
              @click="ouvrirEquipe(ligne.equipe)"
            >
              <td>{{ ligne.rang }}</td>
              <td>
                <span class="equipe-ligne">
                  <img
                    v-if="ligne.url_logo"
                    :src="ligne.url_logo"
                    :alt="ligne.equipe"
                    class="blason"
                  />
                  {{ ligne.equipe }}
                </span>
              </td>
              <td class="droit pts">{{ ligne.pts }}</td>
              <td class="droit">{{ ligne.j }}</td>
              <td class="droit">{{ ligne.v }}</td>
              <td class="droit">{{ ligne.n }}</td>
              <td class="droit">{{ ligne.d }}</td>
              <td class="droit">{{ ligne.bp }}</td>
              <td class="droit">{{ ligne.bc }}</td>
              <td class="droit">{{ ligne.diff }}</td>
              <td>
                <span class="forme forme-classement">
                  <span
                    v-for="(lettre, i) in serieForme(ligne.forme)"
                    :key="i"
                    :class="'pastille pastille-' + lettre"
                  >{{ lettre }}</span>
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </template>

      <template v-else-if="onglet === 'calendrier'">
        <p v-if="!programme.length" class="doux">
          Pas encore de calendrier pour {{ championnat }} en {{ saison }}.
        </p>
        <CalendrierMatchs
          v-else
          :matchs="programme"
          @ouvrir-equipe="ouvrirEquipe"
          @analyser="analyserMatch"
        />
      </template>

      <template v-else-if="onglet === 'buteurs' || onglet === 'passeurs'">
        <p v-if="!meilleurs.length" class="doux">
          Pas encore de stats joueurs pour {{ championnat }} en {{ saison }}.
        </p>
        <table v-else>
          <thead>
            <tr>
              <th>#</th>
              <th>Joueur</th>
              <th>Club</th>
              <th class="droit">M</th>
              <th class="droit">Min</th>
              <th v-if="onglet === 'buteurs'" class="droit">Buts</th>
              <th v-if="onglet === 'buteurs'" class="droit">xG</th>
              <th v-if="onglet === 'passeurs'" class="droit">PD</th>
              <th v-if="onglet === 'passeurs'" class="droit">xA</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(joueur, index) in meilleurs"
              :key="joueur.joueur + joueur.equipe"
              class="cliquable"
              @click="ouvrirJoueur(joueur.joueur)"
            >
              <td>{{ index + 1 }}</td>
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
              <td>{{ joueur.equipe }}</td>
              <td class="droit">{{ joueur.matchs }}</td>
              <td class="droit">{{ joueur.minutes }}</td>
              <td v-if="onglet === 'buteurs'" class="droit pts">{{ joueur.buts }}</td>
              <td v-if="onglet === 'buteurs'" class="droit">{{ joueur.xg }}</td>
              <td v-if="onglet === 'passeurs'" class="droit pts">{{ joueur.passes_decisives }}</td>
              <td v-if="onglet === 'passeurs'" class="droit">{{ joueur.xa }}</td>
            </tr>
          </tbody>
        </table>
      </template>
    </template>
  </div>
</template>
