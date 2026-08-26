<script setup>
import { computed, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import CalendrierMatchs from "../composants/CalendrierMatchs.vue";
import PortraitJoueur from "../composants/PortraitJoueur.vue";
import { definirExtraNavigation, viderExtraNavigation } from "../contexteNavigation.js";
import { chargerAccueil, chargerCalendrier, chargerClassement, chargerMeilleurs } from "../services/api.js";

defineOptions({ name: "PageChampionnat" });

const route = useRoute();
const routeur = useRouter();
const championnat = computed(() => route.params.championnat);
const saisons = ref([]);
const saison = ref(route.query.saison || "");
const classement = ref([]);
const programme = ref([]);
const formatClassement = ref("ligue");
const mentionSources = ref("");
const eloMeta = ref({ disponible: false, message: "" });
const ONGLET_VALIDES = ["classement", "calendrier", "buteurs", "passeurs"];
const onglet = ref(
  ONGLET_VALIDES.includes(route.query.onglet)
    ? route.query.onglet
    : "classement",
);
const meilleurs = ref([]);
const messageMeilleurs = ref("");
const saisonMeilleurs = ref("");
const chargement = ref(false);
const erreur = ref("");
let cleClassement = "";
let cleCalendrier = "";
let cleMeilleurs = "";
let generationChargement = 0;

async function assurerSaisons() {
  if (!saison.value) {
    const meta = await chargerAccueil();
    saisons.value = meta.saisons;
    saison.value = meta.saisons[0];
  } else if (!saisons.value.length) {
    saisons.value = (await chargerAccueil()).saisons;
  }
}

async function chargerClassementSeul() {
  const cle = `${championnat.value}|${saison.value}`;
  if (cle === cleClassement && classement.value.length) {
    return;
  }
  const avecElo = championnat.value !== "Ligue des champions";
  const data = await chargerClassement(championnat.value, saison.value, {
    elo: avecElo,
  });
  if (data.saisons && data.saisons.length) {
    saisons.value = data.saisons;
    if (!saisons.value.includes(saison.value)) {
      saison.value = saisons.value[0];
      return;
    }
  }
  classement.value = data.classement;
  formatClassement.value = data.format || "ligue";
  mentionSources.value = data.mention_sources || "";
  eloMeta.value = data.elo || { disponible: false, message: "" };
  cleClassement = cle;
}

async function chargerCalendrierSeul() {
  const cle = `${championnat.value}|${saison.value}`;
  if (cle === cleCalendrier && programme.value.length) {
    return;
  }
  const data = await chargerCalendrier(championnat.value, saison.value);
  programme.value = data.programme || [];
  if (data.saisons && data.saisons.length) {
    saisons.value = data.saisons;
  }
  if (data.mention_sources) {
    mentionSources.value = data.mention_sources;
  }
  cleCalendrier = cle;
}

async function chargerSelonOnglet() {
  if (!championnat.value) return;
  erreur.value = "";
  const ongletActuel = onglet.value;
  if (ongletActuel === "buteurs" || ongletActuel === "passeurs") {
    return;
  }
  const generation = ++generationChargement;
  chargement.value = true;
  try {
    await assurerSaisons();
    if (generation !== generationChargement) return;
    if (onglet.value === "classement") {
      await chargerClassementSeul();
    } else if (onglet.value === "calendrier") {
      await chargerCalendrierSeul();
    }
  } catch (e) {
    if (generation === generationChargement) {
      erreur.value = e.message;
    }
  } finally {
    if (generation === generationChargement) {
      chargement.value = false;
    }
  }
}

watch([championnat, saison, onglet], chargerSelonOnglet, { immediate: true });

watch(
  () => route.query.onglet,
  (nom) => {
    if (ONGLET_VALIDES.includes(nom) && nom !== onglet.value) {
      onglet.value = nom;
    }
  },
);

watch(
  [championnat, saison],
  () => {
    cleClassement = "";
    cleCalendrier = "";
    cleMeilleurs = "";
    definirExtraNavigation({
      championnat: championnat.value,
      saison: saison.value,
      equipe: "",
    });
  },
  { immediate: true },
);

onUnmounted(viderExtraNavigation);

function choisirOnglet(nom) {
  onglet.value = nom;
  const query = {
    ...route.query,
    ...(saison.value ? { saison: saison.value } : {}),
    onglet: nom,
  };
  delete query.vue;
  routeur.replace({ query });
}

async function chargerClassementJoueurs() {
  if (onglet.value !== "buteurs" && onglet.value !== "passeurs") {
    return;
  }
  if (!championnat.value) {
    return;
  }
  const generation = ++generationChargement;
  chargement.value = true;
  erreur.value = "";
  try {
    await assurerSaisons();
    if (generation !== generationChargement) return;
    if (!saison.value) {
      return;
    }
    const type = onglet.value === "buteurs" ? "buts" : "passes";
    const ligue = championnat.value;
    const annee = saison.value;
    const cle = `${ligue}|${annee}|${type}`;
    if (cle === cleMeilleurs && meilleurs.value.length) {
      return;
    }
    const data = await chargerMeilleurs(ligue, annee, type);
    if (generation !== generationChargement) return;
    if (onglet.value !== (type === "buts" ? "buteurs" : "passeurs")) {
      return;
    }
    if (championnat.value !== ligue || saison.value !== annee) {
      return;
    }
    meilleurs.value = data.joueurs || [];
    messageMeilleurs.value = data.message || "";
    if (data.mention_sources) {
      mentionSources.value = data.mention_sources;
    }
    saisonMeilleurs.value = data.saison_utilisee || annee;
    cleMeilleurs = cle;
  } catch (e) {
    if (generation === generationChargement) {
      meilleurs.value = [];
      messageMeilleurs.value = "";
        erreur.value = e.message;
    }
  } finally {
    if (generation === generationChargement) {
      chargement.value = false;
    }
  }
}

watch([championnat, saison, onglet], chargerClassementJoueurs, { immediate: true });

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
          @click="choisirOnglet('classement')"
        >
          Classement
        </button>
        <button
          type="button"
          class="onglet"
          :class="{ actif: onglet === 'calendrier' }"
          @click="choisirOnglet('calendrier')"
        >
          Calendrier
        </button>
        <button
          type="button"
          class="onglet"
          :class="{ actif: onglet === 'buteurs' }"
          @click="choisirOnglet('buteurs')"
        >
          Buteurs
        </button>
        <button
          type="button"
          class="onglet"
          :class="{ actif: onglet === 'passeurs' }"
          @click="choisirOnglet('passeurs')"
        >
          Passeurs
        </button>
      </div>

      <p v-if="mentionSources" class="mention">{{ mentionSources }}</p>

      <p v-if="chargement" class="doux">Chargement…</p>

      <template v-if="onglet === 'classement'">
        <p v-if="!chargement && !classement.length" class="doux">
          Aucun match joué pour {{ championnat }} en {{ saison }}.
        </p>
        <p v-if="classement.length && formatClassement === 'phase_de_ligue'" class="legende-classement">
          <span class="legende-ldc"><i></i> 1-8 : huitièmes</span>
          <span class="legende-barrages"><i></i> 9-24 : barrages</span>
          <span class="legende-hors"><i></i> 25-36 : éliminés</span>
        </p>
        <p v-if="eloMeta.message && !eloMeta.disponible" class="doux">{{ eloMeta.message }}</p>
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
              <th v-if="eloMeta.disponible" class="droit">Elo</th>
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
              <td v-if="eloMeta.disponible" class="droit">
                {{ ligne.elo != null ? ligne.elo : "—" }}
              </td>
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
        <p v-if="!chargement && !programme.length" class="doux">
          Pas encore de calendrier pour {{ championnat }} en {{ saison }}.
        </p>
        <CalendrierMatchs
          v-else-if="programme.length"
          :matchs="programme"
          @ouvrir-equipe="ouvrirEquipe"
          @analyser="analyserMatch"
        />
      </template>

      <template v-else-if="onglet === 'buteurs' || onglet === 'passeurs'">
        <p v-if="messageMeilleurs" class="doux">{{ messageMeilleurs }}</p>
        <p v-else-if="!chargement && !meilleurs.length" class="doux">
          Aucun {{ onglet === 'buteurs' ? 'buteur' : 'passeur' }} pour
          {{ championnat }} en {{ saison }}.
        </p>
        <table v-if="meilleurs.length">
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
              :key="joueur.joueur + joueur.equipe + (saisonMeilleurs || '')"
              class="cliquable"
              @click="ouvrirJoueur(joueur.joueur)"
            >
              <td>{{ index + 1 }}</td>
              <td>
                <span class="joueur-cellule">
                  <PortraitJoueur
                    :nom="joueur.joueur"
                    :url-photo="joueur.url_photo"
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
