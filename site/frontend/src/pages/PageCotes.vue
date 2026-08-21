<script setup>
import { computed, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { definirExtraNavigation, viderExtraNavigation } from "../contexteNavigation.js";
import { formaterDate } from "../dates.js";
import { chargerCotes } from "../services/api.js";

const route = useRoute();
const routeur = useRouter();
const matchs = ref([]);
const competitions = ref([]);
const message = ref("");
const cleConfiguree = ref(false);
const erreur = ref("");
const chargement = ref(false);
const filtre = ref(typeof route.query.championnat === "string" ? route.query.championnat : "");

function dateLocale(match) {
  if (match.commence_at) {
    const instant = new Date(match.commence_at);
    if (!Number.isNaN(instant.getTime())) {
      const mois = String(instant.getMonth() + 1).padStart(2, "0");
      const jour = String(instant.getDate()).padStart(2, "0");
      return `${instant.getFullYear()}-${mois}-${jour}`;
    }
  }
  return match.date || "";
}

function heureLocale(match) {
  if (match.commence_at) {
    const instant = new Date(match.commence_at);
    if (!Number.isNaN(instant.getTime())) {
      return instant.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
    }
  }
  return match.heure || "—";
}

function texteCote(valeur) {
  if (valeur == null || valeur === "") return "—";
  const nombre = Number(valeur);
  if (Number.isNaN(nombre)) return "—";
  return nombre.toFixed(2).replace(".", ",");
}

function cotesAffichees(match) {
  return match.cotes && match.cotes.moyenne ? match.cotes.moyenne : null;
}

async function charger() {
  erreur.value = "";
  chargement.value = true;
  try {
    const data = await chargerCotes();
    matchs.value = data.matchs || [];
    competitions.value = data.competitions || [];
    message.value = data.message || "";
    cleConfiguree.value = Boolean(data.cle_configuree);
    if (filtre.value && !competitions.value.includes(filtre.value)) {
      filtre.value = "";
    }
  } catch (e) {
    erreur.value = e.message;
    matchs.value = [];
  } finally {
    chargement.value = false;
  }
}

charger();

watch(
  () => route.query.championnat,
  (nom) => {
    filtre.value = typeof nom === "string" ? nom : "";
  },
);

watch(
  filtre,
  (nom) => {
    definirExtraNavigation({
      championnat: nom,
      saison: "",
      equipe: "",
    });
  },
  { immediate: true },
);

onUnmounted(viderExtraNavigation);

function choisirFiltre(nom) {
  const suivant = filtre.value === nom ? "" : nom;
  filtre.value = suivant;
  routeur.replace({
    path: "/cotes",
    query: suivant ? { championnat: suivant } : {},
  });
}

const matchsFiltres = computed(() => {
  if (!filtre.value) return matchs.value;
  return matchs.value.filter((match) => match.championnat === filtre.value);
});

const groupes = computed(() => {
  const parLigue = new Map();
  for (const match of matchsFiltres.value) {
    const liste = parLigue.get(match.championnat) || [];
    liste.push(match);
    parLigue.set(match.championnat, liste);
  }
  const resultat = [];
  const ordre = competitions.value.length
    ? competitions.value
    : [...parLigue.keys()];
  for (const nom of ordre) {
    const liste = parLigue.get(nom);
    if (!liste || !liste.length) continue;
    const parDate = new Map();
    for (const match of liste) {
      const jour = dateLocale(match);
      const duJour = parDate.get(jour) || [];
      duJour.push(match);
      parDate.set(jour, duJour);
    }
    resultat.push({
      championnat: nom,
      jours: [...parDate.entries()].map(([date, items]) => ({ date, matchs: items })),
    });
  }
  return resultat;
});
</script>

<template>
  <section class="hero">
    <div class="hero-inner">
      <h1 class="titre-hero">Cotes — matchs à venir</h1>
      <p class="doux">
        Cotes 1-N-2 des rencontres pas encore jouées. Informations uniquement,
        ce n’est pas un service de pari.
      </p>
    </div>
  </section>
  <div class="page">
    <p v-if="erreur" class="erreur">{{ erreur }}</p>
    <p v-else-if="chargement" class="doux">Chargement des cotes…</p>
    <template v-else>
      <p v-if="message" class="bloc-recit">{{ message }}</p>

      <div class="filtres-calendrier" role="group" aria-label="Filtrer par compétition">
        <button
          type="button"
          :class="{ actif: !filtre }"
          @click="choisirFiltre('')"
        >
          Toutes
        </button>
        <button
          v-for="nom in competitions"
          :key="nom"
          type="button"
          :class="{ actif: filtre === nom }"
          @click="choisirFiltre(nom)"
        >
          {{ nom }}
        </button>
      </div>

      <p v-if="!groupes.length" class="doux">
        Aucun match à venir pour le moment.
      </p>

      <div v-for="groupe in groupes" :key="groupe.championnat" class="bloc">
        <h2>{{ groupe.championnat }}</h2>
        <div v-for="jour in groupe.jours" :key="groupe.championnat + jour.date" class="jour-calendrier">
          <p class="libelle-jour">{{ formaterDate(jour.date) }}</p>
          <article v-for="match in jour.matchs" :key="match.commence_at + match.domicile + match.exterieur" class="carte-cote">
            <div class="entete-cote">
              <span>{{ heureLocale(match) }}</span>
            </div>
            <p class="noms-cote">{{ match.domicile }} — {{ match.exterieur }}</p>
            <div class="ligne-cotes" v-if="cotesAffichees(match)">
              <span class="puce-cote">
                <em>1</em>{{ texteCote(cotesAffichees(match).domicile) }}
              </span>
              <span class="puce-cote">
                <em>N</em>{{ texteCote(cotesAffichees(match).nul) }}
              </span>
              <span class="puce-cote">
                <em>2</em>{{ texteCote(cotesAffichees(match).exterieur) }}
              </span>
            </div>
            <p v-else-if="cleConfiguree" class="doux petit">Cotes non disponibles</p>
            <ul v-if="match.bookmakers && match.bookmakers.length" class="liste-bookmakers">
              <li v-for="book in match.bookmakers" :key="book.nom">
                {{ book.nom }}
                · 1 {{ texteCote(book.domicile) }}
                · N {{ texteCote(book.nul) }}
                · 2 {{ texteCote(book.exterieur) }}
              </li>
            </ul>
          </article>
        </div>
      </div>
    </template>
  </div>
</template>
