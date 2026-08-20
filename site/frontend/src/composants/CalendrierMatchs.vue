<script setup>
import { computed, ref } from "vue";
import { aujourdhuiIso, cleMois, formaterDate, titreMois } from "../dates.js";

const props = defineProps({
  matchs: { type: Array, default: () => [] },
  equipeFocus: { type: String, default: "" },
  afficherTirs: { type: Boolean, default: false },
});

const emit = defineEmits(["ouvrir-equipe", "analyser"]);

const filtre = ref("tous");
const aujourd = aujourdhuiIso();

const matchsFiltres = computed(() => {
  if (filtre.value === "joues") return props.matchs.filter((m) => m.joue);
  if (filtre.value === "avenir") return props.matchs.filter((m) => !m.joue);
  return props.matchs;
});

const prochain = computed(() => props.matchs.find((m) => !m.joue) || null);

const groupes = computed(() => {
  const liste = [];
  let moisCourant = null;
  let jourCourant = null;
  for (const match of matchsFiltres.value) {
    const mois = cleMois(match.date);
    if (!moisCourant || moisCourant.cle !== mois) {
      moisCourant = { cle: mois, titre: titreMois(match.date), jours: [] };
      liste.push(moisCourant);
      jourCourant = null;
    }
    if (!jourCourant || jourCourant.date !== match.date) {
      jourCourant = { date: match.date, libelle: formaterDate(match.date), matchs: [] };
      moisCourant.jours.push(jourCourant);
    }
    jourCourant.matchs.push(match);
    if (prochain.value && memesMatchs(match, prochain.value)) {
      jourCourant.estProchain = true;
    }
    if (match.date === aujourd) {
      jourCourant.estAujourdhui = true;
    }
  }
  return liste;
});

const totaux = computed(() => ({
  tous: props.matchs.length,
  joues: props.matchs.filter((m) => m.joue).length,
  avenir: props.matchs.filter((m) => !m.joue).length,
}));

function memesMatchs(a, b) {
  return a.date === b.date && a.domicile === b.domicile && a.exterieur === b.exterieur;
}

function score(match) {
  if (!match.joue) return "";
  if (match.buts_domicile == null || match.buts_exterieur == null) return "";
  return `${match.buts_domicile} – ${match.buts_exterieur}`;
}

function tirs(match) {
  if (!props.afficherTirs || !match.joue || match.tirs_domicile == null) return "";
  return `${match.tirs_domicile}–${match.tirs_exterieur} tirs`;
}

function texteXg(match) {
  if (match.xg_domicile == null || match.xg_exterieur == null) return "";
  return `xG ${match.xg_domicile} – ${match.xg_exterieur}`;
}

function estFocus(nom) {
  return props.equipeFocus && nom === props.equipeFocus;
}

function surMatch(match) {
  emit("analyser", match);
}

function ouvrir(nom, event) {
  event.stopPropagation();
  emit("ouvrir-equipe", nom);
}
</script>

<template>
  <div v-if="!matchs.length" class="doux">Aucun match dans ce calendrier.</div>
  <div v-else class="calendrier">
    <div class="calendrier-barre">
      <div class="filtres-calendrier">
        <button type="button" :class="{ actif: filtre === 'tous' }" @click="filtre = 'tous'">
          Tous ({{ totaux.tous }})
        </button>
        <button type="button" :class="{ actif: filtre === 'joues' }" @click="filtre = 'joues'">
          Joués ({{ totaux.joues }})
        </button>
        <button type="button" :class="{ actif: filtre === 'avenir' }" @click="filtre = 'avenir'">
          À venir ({{ totaux.avenir }})
        </button>
      </div>
      <a v-if="prochain" class="lien-prochain" href="#match-prochain">Prochain match</a>
    </div>

    <p v-if="!matchsFiltres.length" class="doux">Aucun match dans ce filtre.</p>

    <section v-for="mois in groupes" :key="mois.cle" class="mois-calendrier">
      <h2>{{ mois.titre }}</h2>
      <div v-for="jour in mois.jours" :key="jour.date" class="jour-calendrier">
        <p class="libelle-jour">
          {{ jour.libelle }}
          <span v-if="jour.estAujourdhui" class="pastille-jour">Aujourd’hui</span>
          <span v-else-if="jour.estProchain" class="pastille-jour">Prochain</span>
        </p>
        <article
          v-for="match in jour.matchs"
          :key="match.date + match.domicile + match.exterieur"
          class="carte-match"
          :class="{
            'match-avenir': !match.joue,
            'match-joue': match.joue,
            'match-prochain': prochain && memesMatchs(match, prochain),
          }"
          :id="prochain && memesMatchs(match, prochain) ? 'match-prochain' : undefined"
          @click="surMatch(match)"
        >
          <div class="heure-match">{{ match.heure || (match.joue ? "FT" : "—") }}</div>
          <button type="button" class="club-match club-domicile" :class="{ focus: estFocus(match.domicile) }" @click="ouvrir(match.domicile, $event)">
            <span>{{ match.domicile }}</span>
            <img v-if="match.url_logo_domicile" :src="match.url_logo_domicile" :alt="match.domicile" class="blason" />
          </button>
          <div class="milieu-match">
            <strong v-if="match.joue" class="score-match">{{ score(match) }}</strong>
            <strong v-else class="versus">vs</strong>
            <small v-if="tirs(match)">{{ tirs(match) }}</small>
            <small v-if="texteXg(match)">{{ texteXg(match) }}</small>
            <small v-if="!match.joue" class="hint-analyse">Analyser</small>
            <small v-else class="hint-analyse">Fiche</small>
          </div>
          <button type="button" class="club-match club-exterieur" :class="{ focus: estFocus(match.exterieur) }" @click="ouvrir(match.exterieur, $event)">
            <img v-if="match.url_logo_exterieur" :src="match.url_logo_exterieur" :alt="match.exterieur" class="blason" />
            <span>{{ match.exterieur }}</span>
          </button>
        </article>
      </div>
    </section>
  </div>
</template>
